import sys
from perfetto.trace_processor import TraceProcessor
tp = TraceProcessor(trace=sys.argv[1])
print("# threads with Save K / convert / forward spans (thread name, count, sum ms)")
q = tp.query("""
  select s.name as name, t.name as tname, t.tid as tid, count(*) as n, sum(s.dur)/1e6 as ms, avg(s.dur)/1e3 as mean_us
  from slice s join thread_track tt on s.track_id = tt.id join thread t using(utid)
  where s.name in ('Save K','Save V','convert_k_blocks','forward','waiting_for_logits') group by s.name, t.tid order by s.name, n desc""")
for r in q:
    print(f"{r.name:18s} thread={str(r.tname):24s} tid={r.tid} n={r.n} sum={r.ms:.1f} ms mean={r.mean_us:.1f} us")
print("# top 12 span names by total duration")
q = tp.query("select name, count(*) as n, sum(dur)/1e6 as ms from slice group by name order by ms desc limit 14")
for r in q: print(f"  {r.name[:60]:60s} n={r.n} sum={r.ms:.0f} ms")
# per decode forward: which spans run on the main thread between consecutive forwards (the forward span's thread)
q = tp.query("""
  select s.name as name, count(*) as n, sum(s.dur)/1e6 as ms from slice s join thread_track tt on s.track_id = tt.id
  where tt.utid = (select tt2.utid from slice f join thread_track tt2 on f.track_id = tt2.id where f.name='forward' limit 1)
  group by s.name order by ms desc limit 15""")
print("# spans on the forward thread (main)")
for r in q: print(f"  {r.name[:60]:60s} n={r.n} sum={r.ms:.0f} ms")
