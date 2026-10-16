#!/usr/bin/env python3
"""attn_forward.py <trace.pftrace>: attention time per decode forward, per worker thread.

A decode forward is a 'forward' slice shorter than 200 ms (the prefill forwards are longer). For every
decode forward: the number of 'Attention Ready' + 'Attention Pending' slices inside it, their sum, the
per-thread sums (one attention worker = one thread) and the largest per-thread sum (a lower bound of the
attention critical path), plus 'attention: join' sums. Prints the means over the decode forwards.
Run with: uvx --from perfetto python -I attn_forward.py FILE
"""
import statistics
import sys
from perfetto.trace_processor import TraceProcessor

tp = TraceProcessor(trace=sys.argv[1])
fw = [(r.ts, r.dur) for r in tp.query("select ts, dur from slice where name = 'forward' and dur < 200000000 order by ts")]
print(f"# {sys.argv[1]}: {len(fw)} decode forwards, mean {statistics.mean(d for _, d in fw) / 1e3:.1f} us")
rows = []
for ts, dur in fw:
    q = tp.query(f"""
      select s.name as name, t.tid as tid, count(*) as n, sum(s.dur) as sum
      from slice s join thread_track tt on s.track_id = tt.id join thread t using(utid)
      where s.name in ('Attention Ready', 'Attention Pending', 'attention: join') and s.ts >= {ts} and s.ts < {ts + dur}
      group by s.name, t.tid""")
    per = {}
    for r in q:
        per.setdefault(r.name, {})[r.tid] = (r.n, r.sum)
    rec = {'dur': dur}
    for name in ('Attention Ready', 'Attention Pending', 'attention: join'):
        d = per.get(name, {})
        rec[name] = (sum(v[0] for v in d.values()), sum(v[1] for v in d.values()), max((v[1] for v in d.values()), default=0), len(d))
    rows.append(rec)
if not rows:
    sys.exit(0)
print(f"{'span':18s} {'n/forward':>10s} {'sum us/forward':>15s} {'max thread us':>14s} {'threads':>8s}")
for name in ('Attention Ready', 'Attention Pending', 'attention: join'):
    print(f"{name:18s} {statistics.mean(r[name][0] for r in rows):10.1f} {statistics.mean(r[name][1] for r in rows) / 1e3:15.1f} "
          f"{statistics.mean(r[name][2] for r in rows) / 1e3:14.1f} {statistics.mean(r[name][3] for r in rows):8.1f}")
print(f"forward mean {statistics.mean(r['dur'] for r in rows) / 1e3:.1f} us, median {statistics.median(r['dur'] for r in rows) / 1e3:.1f} us over {len(rows)} decode forwards")
