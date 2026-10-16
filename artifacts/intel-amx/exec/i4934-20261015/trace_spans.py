#!/usr/bin/env python3
"""trace_spans.py <trace.pftrace> [--forwards]: per-span statistics of a tron Perfetto trace.

Prints, for the spans named below, the count, the mean / min / max duration in microseconds and the
sum, plus per-forward numbers for the conversion span (its 'blocks' argument and its duration).
Run with: uvx --from perfetto python -I trace_spans.py FILE
"""
import sys
from perfetto.trace_processor import TraceProcessor

SPANS = ['convert_k_blocks', 'Save K', 'Save V', 'forward', 'Attention Ready', 'Attention Pending',
         'waiting_for_logits']


def main():
    path = sys.argv[1]
    per_forward = '--forwards' in sys.argv
    tp = TraceProcessor(trace=path)
    print(f"# {path}")
    for name in SPANS:
        q = tp.query(f"""
            select count(*) as n, avg(dur) as mean_ns, min(dur) as min_ns, max(dur) as max_ns, sum(dur) as sum_ns
            from slice where name = '{name}'""")
        for r in q:
            if r.n == 0:
                print(f"{name:20s} n=0")
                continue
            print(f"{name:20s} n={r.n:7d} mean={r.mean_ns/1e3:10.1f} us min={r.min_ns/1e3:9.1f} us "
                  f"max={r.max_ns/1e3:10.1f} us sum={r.sum_ns/1e6:10.3f} ms")
    # The conversion span per forward: duration and the 'blocks' argument.
    q = tp.query("""
        select s.ts as ts, s.dur as dur, a.int_value as blocks
        from slice s left join args a on a.arg_set_id = s.arg_set_id and a.key like '%blocks'
        where s.name = 'convert_k_blocks' order by s.ts""")
    rows = [(r.ts, r.dur, r.blocks) for r in q]
    if rows:
        import statistics
        durs = [d for _, d, _ in rows]
        blocks = [b for _, _, b in rows if b is not None]
        print(f"convert_k_blocks per forward: n={len(rows)} dur mean={statistics.mean(durs)/1e3:.1f} us "
              f"median={statistics.median(durs)/1e3:.1f} us max={max(durs)/1e3:.1f} us; blocks "
              f"mean={statistics.mean(blocks) if blocks else 0:.1f} max={max(blocks) if blocks else 0}")
        if per_forward:
            for ts, dur, b in rows:
                print(f"  ts={ts} dur={dur/1e3:.1f} us blocks={b}")
    # Save K per forward: the sum of the main thread's Save K spans between consecutive forwards is
    # printed as the per-forward total when --forwards is given.
    if per_forward:
        q = tp.query("""
            select f.ts as fts, f.dur as fdur,
                   (select sum(k.dur) from slice k where k.name = 'Save K' and k.ts >= f.ts and k.ts < f.ts + f.dur) as savek_ns,
                   (select count(*) from slice k where k.name = 'Save K' and k.ts >= f.ts and k.ts < f.ts + f.dur) as savek_n
            from slice f where f.name = 'forward' order by f.ts""")
        for r in q:
            sk = (r.savek_ns or 0) / 1e3
            print(f"forward ts={r.fts} dur={r.fdur/1e3:.1f} us  Save K n={r.savek_n} sum={sk:.1f} us")


if __name__ == '__main__':
    main()
