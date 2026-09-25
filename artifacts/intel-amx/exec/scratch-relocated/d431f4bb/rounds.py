import re, json, datetime, statistics
R="/home/jhan/workspace/intel-AMX/exec/results/q4b-fpga-20260921"
C=json.load(open("/home/jhan/workspace/intel-AMX/exec/prefill-amx-vs-fpga-20260921/hbm-exhaustion-cells.json"))
def parse(tag):
    cells={}; cur=None; k=0; prev_t=0; prev_p=0
    for line in open(f"{R}/{tag}/driver.log", errors="replace"):
        m=re.search(r"== Benchmarking \S+_p(\d+) ==", line)
        if m: cur=int(m.group(1)); cells[cur]=[]; prev_t=0; prev_p=0; k=0; continue
        m=re.search(r"\[(\d\d/\w+/\d{4} \d\d:\d\d:\d\d) UTC\].*Running averages: TTFT=(\d+), TPS=([\d.]+)", line)
        if m and cur is not None:
            k+=1; t=float(m.group(2)); p=float(m.group(3))
            ts=datetime.datetime.strptime(m.group(1),"%d/%b/%Y %H:%M:%S").replace(tzinfo=datetime.timezone.utc).timestamp()
            cells[cur].append(dict(k=k, ttft_round=k*t-(k-1)*prev_t, tps_round=k*p-(k-1)*prev_p, ts=ts, run_ttft=t, run_tps=p))
            prev_t=t; prev_p=p
    return cells
A=parse("fpgabase-pass1"); B=parse("fpgacanon-pass1")
hb={(c['tag'],c['prompt']):c for c in C['cells']}
for p in (2048, 4096, 7168, 8192):
    print(f"\n=== prompt {p}: per-round TTFT ms (from running averages), fpgabase vs fpgacanon")
    ca=hb[("fpgabase-pass1",p)]; cb=hb[("fpgacanon-pass1",p)]
    print(f"    fpgabase cell {ca['lose']} warnings, fpgacanon cell {cb['lose']} warnings")
    print(f"{'round':>5s} {'base TTFT':>10s} {'canon TTFT':>11s} {'delta%':>7s} | {'base TPS':>8s} {'canon TPS':>9s} {'delta%':>7s} | round end offset (s) base/canon")
    for ra, rb in zip(A[p], B[p]):
        d=100*(rb['ttft_round']-ra['ttft_round'])/ra['ttft_round']
        dp=100*(rb['tps_round']-ra['tps_round'])/ra['tps_round']
        print(f"{ra['k']:5d} {ra['ttft_round']:10.0f} {rb['ttft_round']:11.0f} {d:+7.1f} | {ra['tps_round']:8.1f} {rb['tps_round']:9.1f} {dp:+7.1f} | {ra['ts']-ca['t_start']:5.0f} / {rb['ts']-cb['t_start']:5.0f}")
    print(f"  final running mean TTFT: base {A[p][-1]['run_ttft']:.0f}, canon {B[p][-1]['run_ttft']:.0f}; TPS base {A[p][-1]['run_tps']:.1f} canon {B[p][-1]['run_tps']:.1f}")
# check ttfts_ms order vs round-1 running average
for tag,cells in (("fpgabase-pass1",A),("fpgacanon-pass1",B)):
    d=json.load(open(f"{R}/{tag}/perf.json"))
    for r in d['raw']:
        if r['prompt_length'] in (8192,):
            tt=r['ttfts_ms']
            print(tag, "p8192 first-8 mean", statistics.mean(tt[:8]), "round-1 running avg", cells[8192][0]['run_ttft'], "| last-8 mean", statistics.mean(tt[-8:]), "round-10 per-round", round(cells[8192][-1]['ttft_round']))
