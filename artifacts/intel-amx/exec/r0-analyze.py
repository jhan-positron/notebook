#!/usr/bin/env python3
"""P0a router-chain trace analysis (router/02-option-c-plan.md sec 3 +
exec/results/router/G0-preregistration.md). v3 after adversarial review.

Per MoE layer and per decode step:
  (a-stall)     driving-thread "start_reading linear_channel_5" slice duration
                (the logits wait; same channel name in every layer of this
                generated file) — THE G0 variable (pre-registered).
  dispatch      "launch mlp_router_weight_launcher" slice duration.
  await_deps    "await deps mlp_router_weight_launcher" slice duration.
  (b) parts     topk bounds, wait-indices, build routing, first expert prep,
                first expert tx_launch submission (T7).
  M(s)          decode tokens per step from the per-layer "expert token
                counts" instant (sum of counts / topk) — the pre-registered
                definition.
  T_step(s)     inter-step interval from layer-0 router launches.

Step alignment: the per-layer unique key is the ROUTING channel suffix
("start_reading routing_channel", "_1", ..., "_23"); leading launches are
trimmed until the suffix matches the first-layer (unsuffixed) form, and every
step must repeat the same suffix sequence (fail loud otherwise).

NOT computed here (stated deferral, printed at runtime): C(s), g(s) and the
bootstrap CI belong to the G0 report step (they need P0b data); (a-roundtrip)
(launch -> RX completion via the flow chain) is deferred — the flow edges
connect consecutive hops, not launch->rx directly, and labels are per-layer;
extracting it correctly needs a recursive chain walk (review Blocker 2).

Usage:
  r0-analyze.py --trace F --layers 24 [--topk 4] [--users N] [--warmup 8]
      [--json OUT.json] [--debug]
"""
import argparse
import bisect
import collections
import json
import statistics
import sys

from perfetto.trace_processor import TraceProcessor

LAUNCH = "launch mlp_router_weight_launcher"
AWAIT = "await deps mlp_router_weight_launcher"
BUILD_ROUTING = "build routing"
MOE_MATMUL = "MoE matmul"
ROUTING_READ = "start_reading routing_channel"
LOGITS_READ_PREFIX = "start_reading linear_channel"


class TsList:
    """Sorted-by-ts slice list with bisect lookup."""

    def __init__(self, rows):
        self.rows = sorted(rows, key=lambda r: r.ts)
        self.ts = [r.ts for r in self.rows]

    def first_in(self, lo, hi):
        i = bisect.bisect_left(self.ts, lo)
        if i < len(self.rows) and self.rows[i].ts < hi:
            return self.rows[i]
        return None

    def all_in(self, lo, hi):
        i = bisect.bisect_left(self.ts, lo)
        j = bisect.bisect_left(self.ts, hi)
        return self.rows[i:j]

    def last_at_or_before(self, t):
        i = bisect.bisect_right(self.ts, t)
        return self.rows[i - 1] if i else None


def q(tp, sql):
    return list(tp.query(sql))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trace", required=True)
    ap.add_argument("--layers", type=int, required=True)
    ap.add_argument("--topk", type=int, default=4)
    ap.add_argument("--users", type=int, default=None,
                    help="config user count; steps with M > users are "
                         "discarded as prefill contamination (pre-reg rule)")
    ap.add_argument("--warmup", type=int, default=8)
    ap.add_argument("--json", default=None)
    ap.add_argument("--debug", action="store_true")
    args = ap.parse_args()
    L = args.layers

    print("# deferral note: C(s), g(s), bootstrap CI computed at the G0 "
          "report step; (a-roundtrip) deferred (flow chain walk, review "
          "Blocker 2) — the gate variable (a-stall) is extracted here.")

    tp = TraceProcessor(trace=args.trace)

    name_filter = """(
           s.name = '{launch}' OR s.name = '{await_}'
        OR s.name GLOB 'start_writing topk_snd*'
        OR s.name GLOB 'start_reading topk_snd*'
        OR s.name GLOB 'start_reading linear_channel*'
        OR s.name GLOB 'start_reading routing_channel*'
        OR s.name GLOB 'wait indices topk_snd*'
        OR s.name = '{build}' OR s.name = '{moe}'
        OR s.name GLOB 'kernel_add_topk_softmax*'
    )""".format(launch=LAUNCH, await_=AWAIT, build=BUILD_ROUTING, moe=MOE_MATMUL)
    rows = q(tp, """
        SELECT s.id, s.ts, s.dur, s.name, t.utid
        FROM slice s
        JOIN thread_track tt ON s.track_id = tt.id
        JOIN thread t USING (utid)
        WHERE %s AND s.dur >= 0
        ORDER BY s.ts
    """ % name_filter)
    if not rows:
        print("FATAL: no matching slices in trace"); sys.exit(2)

    all_launches = [r for r in rows if r.name == LAUNCH]
    if not all_launches:
        print("FATAL: no '%s' slices — wrong binary or tracing off" % LAUNCH)
        sys.exit(2)
    utid_counts = collections.Counter(r.utid for r in all_launches)
    drv = utid_counts.most_common(1)[0][0]
    dropped = len(all_launches) - utid_counts[drv]
    print("# launch-carrying threads: %d; launches on driving thread %s: %d; "
          "dropped from other threads: %d" %
          (len(utid_counts), drv, utid_counts[drv], dropped))
    if dropped > 0.02 * len(all_launches):
        print("FATAL: >2%% of launches on non-driving threads — model "
              "assumption broken"); sys.exit(2)
    launches = [r for r in all_launches if r.utid == drv]

    drv_rows = [r for r in rows if r.utid == drv]
    stalls = TsList([r for r in drv_rows if r.name.startswith(LOGITS_READ_PREFIX)])
    anchors = TsList([r for r in drv_rows
                      if r.name.startswith("start_writing topk_snd")])
    topk_reads = TsList([r for r in drv_rows
                         if r.name.startswith("start_reading topk_snd")])
    routing_reads = TsList([r for r in drv_rows
                            if r.name.startswith(ROUTING_READ)])
    awaits = TsList([r for r in drv_rows if r.name == AWAIT])
    wait_idx = TsList([r for r in drv_rows
                       if r.name.startswith("wait indices topk_snd")])
    builds = TsList([r for r in drv_rows if r.name == BUILD_ROUTING])
    moes = TsList([r for r in drv_rows if r.name == MOE_MATMUL])
    trace_end = max(r.ts + r.dur for r in rows)

    # --- alignment by routing-channel suffix ---------------------------------
    def routing_suffix_after(i):
        hi = launches[i + 1].ts if i + 1 < len(launches) else trace_end
        rr = routing_reads.first_in(launches[i].ts, hi)
        return rr.name[len(ROUTING_READ):] if rr else None

    first_suffixes = [routing_suffix_after(i) for i in range(min(L, len(launches)))]
    if "" not in first_suffixes:
        print("FATAL: no unsuffixed routing_channel read in the first %d "
              "launches — cannot align (suffixes: %s)" % (L, first_suffixes))
        sys.exit(2)
    best_off = first_suffixes.index("")
    if best_off:
        print("# trimmed %d leading launches (capture started mid-step)" % best_off)
    launches = launches[best_off:]
    n_steps_raw = len(launches) // L
    if n_steps_raw < args.warmup + 5:
        print("FATAL: only %d full steps (L=%d)" % (n_steps_raw, L)); sys.exit(2)
    launches = launches[: n_steps_raw * L]

    def suffix_at(i):
        # i indexes the TRIMMED launches list
        hi = launches[i + 1].ts if i + 1 < len(launches) else trace_end
        rr = routing_reads.first_in(launches[i].ts, hi)
        return rr.name[len(ROUTING_READ):] if rr else None

    canonical = None
    for s in range(n_steps_raw):
        seq = [suffix_at(s * L + l) for l in range(L)]
        if canonical is None:
            canonical = seq
        elif seq != canonical:
            print("FATAL: step %d routing-suffix sequence differs from step 0 "
                  "— alignment broken (%s... vs %s...)"
                  % (s, seq[:3], canonical[:3]))
            sys.exit(2)

    if args.debug:
        print("# offset=%d steps=%d canonical suffixes: %s ..."
              % (best_off, n_steps_raw, canonical[:4]))

    # topk kernel name per layer (first-occurrence order from aligned step 0)
    topk_rows = [r for r in rows if r.name.startswith("kernel_add_topk_softmax")
                 and not r.name.endswith("first wait")]
    topk_names_ordered, seen = [], set()
    for r in sorted(topk_rows, key=lambda r: r.ts):
        if r.ts >= launches[0].ts and r.name not in seen:
            seen.add(r.name); topk_names_ordered.append(r.name)
        if len(topk_names_ordered) == L:
            break
    topk_by_name = {nm: TsList([r for r in topk_rows if r.name == nm])
                    for nm in topk_names_ordered}
    # helper-side logits wait: "<topk kernel> first wait" (per helper); its max
    # per layer window shows the consumer-observed arrival delay even when the
    # driving thread never blocks (the hidden part of the round trip).
    fw_rows = [r for r in rows if r.name.startswith("kernel_add_topk_softmax")
               and r.name.endswith("first wait")]
    fw_by_name = {nm: TsList([r for r in fw_rows if r.name == nm + " first wait"])
                  for nm in topk_names_ordered}

    # --- M via "expert token counts" instants (pre-registered definition) ----
    counts_by_ts = TsList([])
    try:
        crows = q(tp, """
            SELECT s.ts AS ts, s.dur AS dur, a.string_value AS sv,
                   s.id AS id, s.name AS name, 0 AS utid
            FROM slice s JOIN args a ON s.arg_set_id = a.arg_set_id
            WHERE s.name = 'expert token counts' AND a.key LIKE '%counts'
              AND a.string_value IS NOT NULL
        """)
        counts_by_ts = TsList(crows)
        print("# expert-token-counts instants: %d" % len(crows))
    except Exception as e:
        print("# WARN: expert-token-counts query failed (%s); M unavailable" % e)

    def m_from_counts(lo, hi):
        vals = []
        for r in counts_by_ts.all_in(lo, hi):
            try:
                total = sum(int(x) for x in str(r.sv).split(",") if x.strip())
                vals.append(total / args.topk)
            except ValueError:
                pass
        return vals

    # --- expert tx_launch submissions (T7) ------------------------------------
    tx_expert = TsList([])
    try:
        txrows = q(tp, """
            SELECT s.ts AS ts, s.dur AS dur, s.id AS id, s.name AS name,
                   0 AS utid, a.string_value AS sv
            FROM slice s JOIN args a ON s.arg_set_id = a.arg_set_id
            WHERE s.name GLOB '*tx_launch' AND a.key LIKE '%label'
              AND a.string_value LIKE 'mlp_experts%'
        """)
        tx_expert = TsList(txrows)
        print("# expert tx_launch events: %d" % len(txrows))
    except Exception as e:
        print("# WARN: tx_launch query failed (%s); T7 submission unavailable" % e)

    # --- per (step, layer) extraction -----------------------------------------
    steps = []
    logits_channels = set()
    for s in range(n_steps_raw):
        step = {"A_stall": 0.0, "A_corr": 0.0, "layers": []}
        t0 = launches[s * L].ts
        t1 = launches[(s + 1) * L].ts if s + 1 < n_steps_raw else None
        step["T_step"] = (t1 - t0) if t1 else None
        m_vals = []
        for l in range(L):
            la = launches[s * L + l]
            la_end = la.ts + max(la.dur, 0)
            nxt = launches[s * L + l + 1].ts if s * L + l + 1 < len(launches) else trace_end
            rec = {"dispatch": la.dur}
            aw = awaits.last_at_or_before(la.ts)
            # pairing guard: the await block closes right before the launch
            rec["await_deps"] = aw.dur if aw and (la.ts - (aw.ts + aw.dur)) < 50_000 else None
            a = anchors.first_in(la_end, nxt)
            sr = stalls.first_in(a.ts if a else la_end, nxt)
            rec["stall"] = sr.dur if sr else None
            if sr:
                logits_channels.add(sr.name)
            tkl = topk_by_name.get(topk_names_ordered[l]) if l < len(topk_names_ordered) else None
            if tkl:
                tks = tkl.all_in(la.ts, nxt)
                if tks:
                    rec["topk_start"] = min(r.ts for r in tks)
                    rec["topk_end"] = max(r.ts + r.dur for r in tks)
            fwl = fw_by_name.get(topk_names_ordered[l]) if l < len(topk_names_ordered) else None
            if fwl:
                fws = fwl.all_in(la.ts, nxt)
                if fws:
                    rec["helper_first_wait_max"] = max(r.dur for r in fws)
                    rec["helper_entry_off"] = min(r.ts for r in fws) - la.ts
            tr = topk_reads.first_in(la_end, nxt)
            # the corrected serial-block slice (pre-reg DEVIATION section):
            # the driving thread blocks here for the topk OUTPUT, whose
            # critical input is the router round trip
            rec["stall_topk_read"] = tr.dur if tr else None
            wi = wait_idx.first_in(la.ts, nxt)
            rec["wait_indices"] = wi.dur if wi else None
            br = builds.first_in(la.ts, nxt)
            rec["build_routing"] = br.dur if br else None
            mm = moes.first_in(la.ts, nxt)
            if mm:
                rec["first_prep_start"] = mm.ts
            tx = tx_expert.first_in(la.ts, nxt)
            if tx:
                rec["first_tx_submission"] = tx.ts
                rec["c_dispatch_to_tx"] = tx.ts - la.ts
            m_vals.extend(m_from_counts(la.ts, nxt))
            step["layers"].append(rec)
            if rec["stall"] is not None:
                step["A_stall"] += rec["stall"]
            for k in ("stall", "stall_topk_read", "wait_indices"):
                if rec.get(k) is not None:
                    step["A_corr"] += rec[k]
        step["M"] = statistics.mean(m_vals) if m_vals else None
        step["M_max"] = max(m_vals) if m_vals else None
        steps.append(step)

    if len(logits_channels) != 1:
        print("FATAL: logits stall matched %d distinct channel names %s — "
              "window extraction suspect" % (len(logits_channels),
                                             sorted(logits_channels)[:4]))
        sys.exit(2)
    print("# logits channel (all layers): %s" % next(iter(logits_channels)))

    kept = steps[args.warmup:]
    pref_dropped = 0
    if args.users is not None:
        n0 = len(kept)
        kept = [st for st in kept
                if st["M_max"] is None or st["M_max"] <= args.users + 0.01]
        pref_dropped = n0 - len(kept)
        if pref_dropped:
            print("# discarded %d steps with M > users=%d (prefill "
                  "contamination, pre-reg rule)" % (pref_dropped, args.users))
    full = [st for st in kept
            if st["T_step"] and all(rec["stall"] is not None
                                    and rec.get("stall_topk_read") is not None
                                    for rec in st["layers"])]
    print("steps: raw=%d kept=%d full-coverage=%d"
          % (n_steps_raw, len(kept), len(full)))
    if not full:
        print("FATAL: no fully-covered steps"); sys.exit(2)

    A = [st["A_stall"] for st in full]
    AC = [st["A_corr"] for st in full]
    T = [st["T_step"] for st in full]
    frac = [a / t for a, t in zip(A, T)]
    Ms = [st["M"] for st in full if st["M"] is not None]

    def us(ns):
        return ns / 1000.0

    def pctl(v, p):
        vs = sorted(v); i = max(0, min(len(vs) - 1, int(p / 100.0 * len(vs))))
        return vs[i]

    print("A_stall (all-%d-layer sum, per step): mean=%.1fus p50=%.1fus p95=%.1fus"
          % (L, us(statistics.mean(A)), us(pctl(A, 50)), us(pctl(A, 95))))
    print("A_corr (stall+topk_read+wait_idx, all-layer sum): mean=%.1fus "
          "p50=%.1fus p95=%.1fus" % (us(statistics.mean(AC)), us(pctl(AC, 50)),
                                     us(pctl(AC, 95))))
    eo = [rec["helper_entry_off"] for st in full for rec in st["layers"]
          if rec.get("helper_entry_off") is not None]
    if eo:
        print("helper kernel-entry offset after launch: mean=%.2fus p95=%.2fus"
              % (us(statistics.mean(eo)), us(pctl(eo, 95))))
    tkr = [rec["stall_topk_read"] for st in full for rec in st["layers"]
           if rec.get("stall_topk_read") is not None]
    if tkr:
        print("stall_topk_read per layer: mean=%.2fus p95=%.2fus"
              % (us(statistics.mean(tkr)), us(pctl(tkr, 95))))
    print("T_step: mean=%.1fus p50=%.1fus" % (us(statistics.mean(T)), us(pctl(T, 50))))
    print("A_stall/T_step: mean=%.4f (%.2f%%) p95=%.4f"
          % (statistics.mean(frac), 100 * statistics.mean(frac), pctl(frac, 95)))
    if Ms:
        print("M per step: mean=%.2f min=%.1f max=%.1f (from expert-token-counts/topk)"
              % (statistics.mean(Ms), min(Ms), max(Ms)))
    lay_stall = [statistics.mean([us(st["layers"][l]["stall"]) for st in full])
                 for l in range(L)]
    print("per-layer stall us (mean over steps): min=%.2f max=%.2f layer0=%.2f"
          % (min(lay_stall), max(lay_stall), lay_stall[0]))
    for k in ("await_deps", "dispatch", "wait_indices", "build_routing"):
        vals = [rec[k] for st in full for rec in st["layers"] if rec.get(k) is not None]
        if vals:
            print("%s: mean=%.2fus p95=%.2fus"
                  % (k, us(statistics.mean(vals)), us(pctl(vals, 95))))
    hw = [rec["helper_first_wait_max"] for st in full for rec in st["layers"]
          if rec.get("helper_first_wait_max") is not None]
    if hw:
        print("helper first-wait (consumer-observed logits delay), max/layer: "
              "mean=%.2fus p95=%.2fus" % (us(statistics.mean(hw)), us(pctl(hw, 95))))
    cvals = [rec["c_dispatch_to_tx"] for st in full for rec in st["layers"]
             if rec.get("c_dispatch_to_tx") is not None]
    if cvals:
        print("segment(c) dispatch->first expert tx submission: mean=%.2fus p95=%.2fus"
              % (us(statistics.mean(cvals)), us(pctl(cvals, 95))))

    if args.json:
        out = {
            "trace": args.trace, "layers": L, "steps_raw": n_steps_raw,
            "offset": best_off, "warmup_discarded": args.warmup,
            "prefill_dropped": pref_dropped, "steps_used": len(full),
            "A_stall_ns": A, "A_corr_ns": AC, "T_step_ns": T, "frac": frac,
            "M": [st["M"] for st in full],
            "per_layer_stall_us_mean": lay_stall,
            "logits_channel": next(iter(logits_channels)),
            "per_step_layers": [[dict(rec) for rec in st["layers"]] for st in full],
        }
        with open(args.json, "w") as f:
            json.dump(out, f)
        print("wrote %s" % args.json)


if __name__ == "__main__":
    main()
