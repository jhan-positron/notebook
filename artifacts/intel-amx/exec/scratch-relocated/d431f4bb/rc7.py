import json, math, statistics as st
S=json.load(open('/home/jhan/workspace/intel-AMX/exec/results/q4b-rt8u-20260922/summary.json'))
cells={(c['cell'],c['attn'],c['arm']):c for c in S['cells']}
def g(cell,attn,arm): return cells[(cell,attn,arm)]
order=['q3-4b-tp2-8u-p1024','q3-4b-tp2-8u-p2048','q3-4b-tp2-8u-p4096','q3-4b-tp2-8u-p8192','q3-4b-tp2-2u-p4096','q3-4b-tp2-2u-p8192']
print("== recompute means/sd from reps ==")
maxrel=0
for c in S['cells']:
    tps=[r['tps_per_user'] for r in c['reps']]; tt=[r['ttft_s'] for r in c['reps']]
    m,s=st.mean(tps),st.stdev(tps); mt,stt=st.mean(tt),st.stdev(tt)
    maxrel=max(maxrel, s/m, stt/mt)
    ok = abs(m-c['tps_mean'])<1e-6 and abs(s-c['tps_sd'])<1e-6 and abs(mt-c['ttft_mean'])<1e-6 and abs(stt-c['ttft_sd'])<1e-6
    print(f"{c['cell']} {c['attn']:4s} {c['arm']:5s} tps {m:7.2f}+/-{s:.2f} ttft {mt:7.3f}+/-{stt:.3f} n={c['n']} ok={ok} hbm={c['hbm_lose_per_rep']}")
print("max sd/mean =", maxrel*100, "%")
print("\n== FPGA vs CPU, AMX build ==")
for cell in order:
    a=g(cell,'cpu','canon'); b=g(cell,'fpga','canon')
    print(cell, f"prefill {a['ttft_mean']:.2f}/{b['ttft_mean']:.2f} = {a['ttft_mean']/b['ttft_mean']:.3f}x  decode {b['tps_mean']:.2f}/{a['tps_mean']:.2f} = {b['tps_mean']/a['tps_mean']:.2f}x")
print("\n== AMX vs AVX (canon vs base) per attention, from means and from paired ==")
paired={(p['cell'],p['attn']):p for p in S['paired']}
for attn in ['cpu','fpga']:
    for cell in order:
        a=g(cell,attn,'base'); b=g(cell,attn,'canon'); p=paired[(cell,attn)]
        # recompute paired from reps
        dt=[bb['ttft_s']-aa['ttft_s'] for aa,bb in zip(a['reps'],b['reps'])]
        dp=[bb['tps_per_user']-aa['tps_per_user'] for aa,bb in zip(a['reps'],b['reps'])]
        tt=st.mean(dt)/(st.stdev(dt)/math.sqrt(3)); tp=st.mean(dp)/(st.stdev(dp)/math.sqrt(3))
        print(f"{attn} {cell}: prefill {100*(b['ttft_mean']/a['ttft_mean']-1):+.2f}% ({1000*(b['ttft_mean']-a['ttft_mean']):+.0f} ms) ratio {a['ttft_mean']/b['ttft_mean']:.2f}x decode {100*(b['tps_mean']/a['tps_mean']-1):+.2f}%  paired t ttft {tt:+.1f} (file {p['ttft_s']['t']:+.1f}) tps {tp:+.1f} (file {p['tps']['t']:+.1f})")
print("\nn_rt_records", S['n_rt_records'], "excluded", len(S['excluded']['failed_or_stopped']), "complete runs", sum(c['n'] for c in S['cells']))
print("shards 8u p8192 with 256 gen:", 8*math.ceil((8192+256)/1024), "with 1536 gen:", 8*math.ceil((8192+1536)/1024), "prompt only:", 8*8)
for n in [64,72,80]:
    print(n,"shards x 144 MiB =", n*144, "MiB =", n*144*2**20/1e9, "GB =", n*144/1024, "GiB")
# time window
import re
starts=[]
for l in open('/home/jhan/workspace/intel-AMX/exec/results/q4b-rt8u-20260922/rt-results.txt'):
    m=re.search(r'^### runtron .* (\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ) ',l)
    if m: starts.append(m.group(1))
print("record starts: first", starts[0], "second", starts[1], "last", starts[-1], "count", len(starts))
