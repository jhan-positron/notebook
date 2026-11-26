#!/usr/bin/env python3
"""gdn-20261120: where one forward pass of Qwen3.5 4B spends its wall time, from a Perfetto trace.

Words used here:
- tron: the inference program. runtron: its command-line tool. Perfetto: the trace recorder built into tron.
- forward pass (span "forward"): one scheduler step. A pass with as many token jobs as users is a decode step.
  A pass with more token jobs is a prefill pass (prompt chunk).
- GDN: GatedDeltaNet, the recurrent layer type. Span "GatedDeltaNet" = the host-CPU work of one GDN operation on one
  worker thread (h/tron/models/gdn_execution.hpp run_gdn_operation).
- main thread: the thread that owns the "forward" span.

The script prints, per pass kind (prefill, decode):
  1. the mean wall time of a pass,
  2. for every span name: the wall time it covers on the MAIN thread inside the pass (union of its slices, so nested
     or repeated slices are not counted twice), and the CPU time summed over ALL threads,
  3. per GDN operation: main-thread wall time and the number of threads that ran it.
Output: text on stdout and a JSON file next to the trace (<trace>.summary.json).
Usage: analyze_trace.py <trace file> <users>
"""
import json
import sys
from collections import defaultdict

from perfetto.trace_processor import TraceProcessor


def union_ns(intervals):
    """Total length of the union of [start, end) intervals."""
    total = 0
    cur_s = cur_e = None
    for s, e in sorted(intervals):
        if cur_e is None or s > cur_e:
            if cur_e is not None:
                total += cur_e - cur_s
            cur_s, cur_e = s, e
        else:
            cur_e = max(cur_e, e)
    if cur_e is not None:
        total += cur_e - cur_s
    return total


def main(path, users):
    tp = TraceProcessor(trace=path)
    q = lambda s: list(tp.query(s))
    passes = q("""select s.id id, s.ts ts, s.dur dur, tt.utid utid from slice s
                  join thread_track tt on s.track_id = tt.id
                  where s.name = 'forward' and s.dur > 0 order by s.ts""")
    if not passes:
        print("no 'forward' span in the trace"); return 1
    # token jobs per pass: the 'forward args' instant or an argument of the forward span itself
    ntj = {}
    for r in q("""select s.ts ts, a.key key, a.int_value v from slice s join args a on a.arg_set_id = s.arg_set_id
                  where (s.name = 'forward args' or s.name = 'forward') and a.key like '%token_jobs'"""):
        ntj[r.ts] = r.v
    main_utid = passes[0].utid
    def pass_jobs(p):
        best = None
        for ts, v in ntj.items():
            if p.ts <= ts <= p.ts + p.dur:
                best = v
        return best
    kinds = []
    for p in passes:
        n = pass_jobs(p)
        kinds.append(("decode" if (n is not None and n <= users) else "prefill", n))
    slices = q("""select s.ts ts, s.dur dur, s.name name, s.depth depth, tt.utid utid, s.arg_set_id arg from slice s
                  join thread_track tt on s.track_id = tt.id where s.dur > 0 order by s.ts""")
    gdn_op = {}
    for r in q("""select s.id id, s.ts ts, tt.utid utid, a.int_value v from slice s
                  join thread_track tt on s.track_id = tt.id
                  join args a on a.arg_set_id = s.arg_set_id
                  where s.name = 'GatedDeltaNet' and a.key like '%operation'"""):
        gdn_op[(r.ts, r.utid)] = r.v
    summary = {"trace": path, "users": users, "passes": len(passes), "kinds": {}}
    for kind in ("prefill", "decode"):
        idx = [i for i, k in enumerate(kinds) if k[0] == kind]
        if not idx:
            continue
        # skip the first pass of each kind (warm-up: first touch of buffers)
        use = idx[1:] if len(idx) > 2 else idx
        tot_wall = sum(passes[i].dur for i in use)
        main_iv = defaultdict(list); cpu = defaultdict(int); threads = defaultdict(set)
        op_main = defaultdict(list); op_threads = defaultdict(set); op_cpu = defaultdict(int)
        thr_gdn = defaultdict(int)                    # utid -> GDN slice time inside the used passes
        op_span = defaultdict(lambda: [None, None])   # (pass index, op) -> [earliest start, latest end] over all threads
        op_longest = defaultdict(int)                 # (pass index, op) -> longest single slice (the busiest worker)
        gdn_slices = 0
        spans = [(passes[i].ts, passes[i].ts + passes[i].dur) for i in use]
        j = 0
        for s in slices:
            while j < len(spans) and spans[j][1] <= s.ts:
                j += 1
            if j >= len(spans):
                break
            if s.ts < spans[j][0]:
                continue
            e = min(s.ts + s.dur, spans[j][1])
            cpu[s.name] += e - s.ts
            threads[s.name].add(s.utid)
            if s.utid == main_utid:
                main_iv[s.name].append((s.ts, e))
            if s.name == "GatedDeltaNet":
                op = gdn_op.get((s.ts, s.utid), -1)
                op_cpu[op] += e - s.ts; op_threads[op].add(s.utid)
                thr_gdn[s.utid] += e - s.ts
                sp = op_span[(j, op)]
                sp[0] = s.ts if sp[0] is None else min(sp[0], s.ts)
                sp[1] = e if sp[1] is None else max(sp[1], e)
                op_longest[(j, op)] = max(op_longest[(j, op)], e - s.ts)
                gdn_slices += 1
                if s.utid == main_utid:
                    op_main[op].append((s.ts, e))
        n = len(use)
        jobs = [kinds[i][1] for i in use]
        print(f"\n== {kind}: {n} passes used (of {len(idx)}), token jobs per pass {sorted(set(jobs))}, "
              f"mean pass wall {tot_wall / n / 1e6:.3f} ms ==")
        print(f"{'span':38} {'main wall ms/pass':>18} {'% of pass':>10} {'all-thread CPU ms/pass':>23} {'threads':>8}")
        rows = []
        for name in cpu:
            mw = union_ns(main_iv[name]) if name in main_iv else 0
            rows.append((mw, name))
        ksum = {"passes_used": n, "mean_pass_ms": tot_wall / n / 1e6, "token_jobs": sorted(set(jobs)), "spans": {}, "gdn_ops": {}}
        for mw, name in sorted(rows, reverse=True)[:40]:
            print(f"{name[:38]:38} {mw / n / 1e6:18.3f} {100.0 * mw / tot_wall:9.1f}% {cpu[name] / n / 1e6:23.3f} {len(threads[name]):8d}")
            ksum["spans"][name] = {"main_wall_ms_per_pass": mw / n / 1e6, "pct_of_pass": 100.0 * mw / tot_wall,
                                   "cpu_ms_per_pass": cpu[name] / n / 1e6, "threads": len(threads[name])}
        if op_cpu:
            print(f"-- GatedDeltaNet per operation ({kind}) --")
            print(f"{'op':>4} {'main wall us/pass':>18} {'all-thread CPU us/pass':>23} {'threads':>8}")
            for op in sorted(op_cpu):
                mw = union_ns(op_main[op]) if op in op_main else 0
                print(f"{op:4d} {mw / n / 1e3:18.1f} {op_cpu[op] / n / 1e3:23.1f} {len(op_threads[op]):8d}")
                ksum["gdn_ops"][str(op)] = {"main_wall_us_per_pass": mw / n / 1e3, "cpu_us_per_pass": op_cpu[op] / n / 1e3,
                                            "threads": len(op_threads[op])}
        if op_span:
            # wall span of an operation = from the first worker's start to the last worker's end; the output of the
            # operation becomes readable only then, so this span is the operation's share of the pass's critical path
            span_total = sum(v[1] - v[0] for v in op_span.values())
            longest_total = sum(op_longest.values())
            n_ops = len({op for (_, op) in op_span})
            jobs_per_pass = sum(j for j in jobs if j) / max(1, len([j for j in jobs if j]))
            ksum["gdn"] = {
                "ops": n_ops,
                "wall_span_ms_per_pass": span_total / n / 1e6,
                "wall_span_pct_of_pass": 100.0 * span_total / tot_wall,
                "busiest_worker_ms_per_pass": longest_total / n / 1e6,
                "cpu_ms_per_pass": sum(op_cpu.values()) / n / 1e6,
                "slices_per_pass_per_op": gdn_slices / n / max(1, n_ops),
                "token_jobs_per_pass": jobs_per_pass,
                # one step = one token of one key-head group (1 key head + 2 value heads): CPU time / (16 groups x token jobs x ops)
                "cpu_us_per_group_step": sum(op_cpu.values()) / n / 1e3 / max(1.0, 16.0 * jobs_per_pass * n_ops),
            }
            # per thread: one step = one token of one key-head group; a thread runs (16 x chains / threads) groups per operation
            names = {r.utid: r.name for r in q("select utid, name from thread")}
            n_thr = len(thr_gdn)
            steps_per_thread_per_pass = 16.0 * jobs_per_pass * n_ops / max(1, n_thr)
            per_thread = sorted(((names.get(u) or str(u)), v / n / 1e3 / steps_per_thread_per_pass) for u, v in thr_gdn.items())
            ksum["gdn"]["per_thread_step_us"] = {k: v for k, v in per_thread}
            vals = sorted(v for _, v in per_thread)
            ksum["gdn"]["slowest_thread_step_us"] = vals[-1]
            ksum["gdn"]["median_thread_step_us"] = vals[len(vals) // 2]
            print(f"-- GDN per thread ({kind}), us per group step: " + ", ".join(f"{k}={v:.2f}" for k, v in per_thread))
            g = ksum["gdn"]
            print(f"-- GDN summary ({kind}): {g['ops']} ops; wall span {g['wall_span_ms_per_pass']:.3f} ms/pass = {g['wall_span_pct_of_pass']:.1f} % of the pass; "
                  f"busiest worker {g['busiest_worker_ms_per_pass']:.3f} ms/pass; CPU {g['cpu_ms_per_pass']:.3f} ms/pass over {g['slices_per_pass_per_op']:.1f} workers; "
                  f"{g['cpu_us_per_group_step']:.2f} us per group step ({g['token_jobs_per_pass']:.0f} token jobs/pass)")
        summary["kinds"][kind] = ksum
    with open(path + ".summary.json", "w") as f:
        json.dump(summary, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 8))
