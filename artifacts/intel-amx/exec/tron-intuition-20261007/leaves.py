import json,os,re,glob,statistics as st
R="/home/jhan/workspace/intel-AMX/exec/results/attnstats-20261002"
# tsc_hz + workers per run from exit reports
hz={}; wk={}
cur=None
for line in open(f"{R}/exit-reports.txt"):
    if line.startswith("## "): cur=line[3:].strip()
    m=re.search(r'\[attn-stats\] model .*?: (\{.*\})',line)
    if m and cur:
        d=json.loads(m.group(1)); hz[cur]=d["tsc_hz"]; wk[cur]=(d["n_workers"],d["active_workers"],d["n_layers"],d["kv_mul"],d["head_size"])
runs=sorted(os.listdir(f"{R}/leaves"))
for run in runs:
    L=f"{R}/leaves/{run}"
    if not os.path.exists(f"{L}/decode_like_forwards"): continue
    f=json.load(open(f"{L}/decode_like_forwards")); t=json.load(open(f"{L}/decode_like_totals"))
    z=hz[run]; nw,aw,nl,kvm,hs=wk[run]
    if "busy_cycles" not in t: print("\n=== "+run+" totals leaf lacks busy_cycles; keys:",list(t)[:6]); continue
    T1=f["wall_cycles"]/f["forwards"]/z*1e3
    print(f"\n=== {run}  n_workers={nw} active={aw} layers={nl} kv_mul={kvm} head={hs} snapshot forwards={f['forwards']} attn_workers={f['n_attn_workers_min']}-{f['n_attn_workers_max']}")
    print(f"  T1 {T1:.2f} ms/forward (snapshot); totals: T2/job {t['busy_cycles']/t['attn_jobs']/z*1e6:.1f} us, T5/job {t['join_wait_cycles']/t['attn_jobs']/z*1e6:.1f} us, T4/period {t['period_cycles_w0']/t['period_count_w0']/z*1e6:.1f} us, T3/job(w0) {t['wall_cycles_w0']/t['period_count_w0']/z*1e6:.1f} us(approx, /periods)")
    rows=[]
    for i in range(nl):
        d=json.load(open(f"{L}/decode_like_layer_{i}"))
        jobs=d["attn_jobs"]; pc=d["period_count_w0"]
        T2=d["busy_cycles"]/jobs/z*1e6 if jobs else 0
        T5=d["join_wait_cycles"]/jobs/z*1e6 if jobs else 0
        T4=d["period_cycles_w0"]/pc/z*1e6 if pc else 0
        # worker 0 jobs ~ periods (one job per layer per forward when one minibatch); use forwards count from jobs/active workers
        fw=jobs/f["n_attn_workers_min"]
        T3=d["wall_cycles_w0"]/fw/z*1e6 if fw else 0
        keys=(d["ready_amx_k_tokens"]+d["pending_amx_k_tokens"], d["ready_avx_k_tokens"]+d["pending_avx_k_tokens"], d["fpga_k_tokens"])
        rows.append((i,T4,T3,T2,T5,keys,jobs,pc))
    # group even/odd for gptoss, else all
    def summ(sel,label):
        if not sel: return
        T4=st.mean(r[1] for r in sel); T3=st.mean(r[2] for r in sel); T2=st.mean(r[3] for r in sel); T5=st.mean(r[4] for r in sel)
        k=[sum(r[5][j] for r in sel)/len(sel) for j in range(3)]
        print(f"  {label}: layers={len(sel)} T4(period) {T4:.1f} us | T3(w0 wall) {T3:.1f} | T2(busy) {T2:.1f} | T5(join) {T5:.1f} | T3-T2 (waits) {T3-T2:.1f} | T4-T3 (not in attention) {T4-T3:.1f} | keys/layer amx/avx/fpga {k[0]:.0f}/{k[1]:.0f}/{k[2]:.0f}")
    if "gptoss" in run:
        summ([r for r in rows if r[0]%2==0],"even (sliding window, CPU)"); summ([r for r in rows if r[0]%2==1],"odd (full attention, card)")
    else:
        summ(rows,"all layers")
        summ(rows[1:-1],"layers 1..n-2")
    print("  first 3 layers:", [(r[0],round(r[1]),round(r[2]),round(r[3],1),round(r[4],1)) for r in rows[:3]], " last:", [(r[0],round(r[1]),round(r[2]),round(r[3],1),round(r[4],1)) for r in rows[-2:]])
