import statistics, sys
from perfetto.trace_processor import TraceProcessor
path='/home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918/traces/prefill-only__m3__base__tp2__8u__catA.perfetto-trace'
tp=TraceProcessor(trace=path)
def q(sql): return list(tp.query(sql))
passes=q("""select s.id id, s.ts ts, s.dur dur, a.int_value ntj, t.name tname from slice s
            join args a on a.arg_set_id = s.arg_set_id and a.key = 'debug.n_token_jobs'
            join thread_track tt on s.track_id = tt.id join thread t using(utid)
            where s.name = 'forward' order by s.ts""")
print("forward passes:", len(passes))
for p in passes: print(f"  pass ts={p.ts} dur_ms={p.dur/1e6:.3f} n_token_jobs={p.ntj} thread={p.tname}")
names=q("select name, count(*) n, sum(dur) d from slice group by name order by d desc limit 40")
print("top spans by total dur (ms):")
for r in names: print(f"  {r.name!r:40} n={r.n:7} sum_ms={r.d/1e6:.2f}")
# per prefill pass: sums of key spans in window, split main vs workers
KEY=["Save K","Save V","Attention Pending","Attention Ready","attention: hw wait","attention: join","launch_hw_attn","prep_hw_attn","wait_coop_gof","gof_rodeo","gof_populate","xfer_gof","prepare_for_dma","construct_hw_plan","Free scratchpads","assemble attention plan"]
for p in passes:
    if p.ntj is None or p.ntj <= 8: continue
    print(f"== prefill pass dur_ms={p.dur/1e6:.3f} ntj={p.ntj}")
    for nm in KEY:
        rows=q(f"""select t.utid utid, count(*) n, sum(s.dur) d from slice s join thread_track tt on s.track_id=tt.id join thread t using(utid)
                   where s.name = '{nm}' and s.ts >= {p.ts} and s.ts < {p.ts+p.dur} group by t.utid""")
        if not rows: continue
        tot=sum(r.d for r in rows); n=sum(r.n for r in rows); mx=max(r.d for r in rows)
        print(f"   {nm!r:28} n={n:6} sum_ms={tot/1e6:9.3f} threads={len(rows):3} max_thread_ms={mx/1e6:8.3f}")
