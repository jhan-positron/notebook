#!/usr/bin/env python3
"""Read a pr4trace-20261015 Perfetto trace and report the convert_k_blocks span.

Words used here: pass = one scheduler forward() call (span "forward" with the
argument n_token_jobs; 1024 = a prefill pass of one user's prompt, 8 = one
decode step of 8 users); convert_k_blocks = the span of convert_pending_k_blocks
(PR #4901, main thread, at the forward end) with the argument blocks = the
number of queued blocks it converts.

Per trace the script prints every convert_k_blocks span (its pass index, pass
kind, duration, blocks, per-block time), then the mean decode pass duration and
the share of a decode pass the conversion costs when it runs.
"""
import sys
from perfetto.trace_processor import TraceProcessor

def main(path):
    tp = TraceProcessor(trace=path)
    q = lambda s: list(tp.query(s))
    passes = q("""select s.ts ts, s.dur dur, a.int_value ntj from slice s
                  left join args a on a.arg_set_id = s.arg_set_id and a.key like '%n_token_jobs'
                  where s.name = 'forward' order by s.ts""")
    conv = q("""select s.ts ts, s.dur dur, a.int_value blocks, t.name tname from slice s
                left join args a on a.arg_set_id = s.arg_set_id and a.key like '%blocks'
                join thread_track tt on s.track_id = tt.id join thread t on tt.utid = t.utid
                where s.name = 'convert_k_blocks' order by s.ts""")
    print(f"{path}")
    print(f"  forward passes in the trace: {len(passes)} "
          f"(prefill {sum(1 for p in passes if (p.ntj or 0) > 8)}, decode {sum(1 for p in passes if (p.ntj or 0) <= 8)})")
    dec = [p.dur for p in passes if (p.ntj or 0) <= 8]
    dec_mean = sum(dec) / len(dec) if dec else 0
    print(f"  decode pass: mean {dec_mean/1e6:.3f} ms over {len(dec)} passes")
    print(f"  convert_k_blocks spans: {len(conv)}")
    print(f"  {'pass':>5} {'kind':>7} {'blocks':>6} {'us':>9} {'us/block':>9} {'% of decode pass':>17} thread")
    tot_us = 0.0; tot_blocks = 0
    for c in conv:
        # the pass that contains the span, or the one that ended just before it
        idx = None; kind = "?"
        for i, p in enumerate(passes):
            if p.ts <= c.ts <= p.ts + p.dur:
                idx = i + 1; kind = "prefill" if (p.ntj or 0) > 8 else "decode"; break
        if idx is None:
            before = [i for i, p in enumerate(passes) if p.ts + p.dur <= c.ts]
            if before:
                i = before[-1]; idx = f"{i+1}+"; kind = "prefill" if (passes[i].ntj or 0) > 8 else "decode"
        us = c.dur / 1e3; b = c.blocks or 0
        tot_us += us; tot_blocks += b
        share = (c.dur / dec_mean * 100) if dec_mean else float('nan')
        print(f"  {str(idx):>5} {kind:>7} {b:>6} {us:>9.1f} {(us/b if b else float('nan')):>9.2f} {share:>16.2f}% {c.tname}")
    if conv:
        print(f"  total: {tot_us:.1f} us over {tot_blocks} blocks = {tot_us/tot_blocks if tot_blocks else float('nan'):.2f} us/block; "
              f"mean span {tot_us/len(conv):.1f} us = {tot_us/len(conv)/ (dec_mean/1e3) * 100 if dec_mean else float('nan'):.2f} % of a mean decode pass")

if __name__ == "__main__":
    for p in sys.argv[1:]:
        main(p)
