import re, sys, json, statistics as st
import numpy as np
def rows(path):
    L = open(path, encoding='utf-8', errors='replace').read().splitlines()
    out = []; cur = None
    for i, l in enumerate(L):
        m = re.search(r"n_users=(\d+),", l)
        if m:
            blk = "\n".join(L[i:i+14])
            mm = re.search(r"model='([^']+)'", blk); pl = re.search(r"prompt_length=(\d+),", blk); gl = re.search(r"generate_length=(\d+)", blk)
            if mm:
                cur = dict(line=i+1, users=int(m.group(1)), model=mm.group(1), prompt=int(pl.group(1)) if pl else None, gen=int(gl.group(1)) if gl else None, tps=[], ttft=[])
                out.append(cur)
            continue
        if cur is None: continue
        d = re.search(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)", l)
        if d: cur['tps'].append(float(d.group(2))); cur['ttft'].append(int(d.group(1)))
    res = []
    for r in out:
        if not r['tps']: continue
        res.append(dict(model=r['model'], users=r['users'], prompt=r['prompt'], gen=r['gen'], n=len(r['tps']), tps=float(np.mean(r["tps"])), sd=round(st.pstdev(r['tps']),3), mn=min(r['tps']), ttft=round(st.mean(r['ttft'])), line=r['line']))
    return res
nights = {'3bda-0922':'nightly-35683952944.log','3bda-0923':'nightly-35815209295.log','genoa-0922':'nightly-genoa-35682128668.log','genoa-0923':'nightly-genoa-35813240282.log'}
R = {k: rows(v) for k,v in nights.items()}
json.dump(R, open('all_rows.json','w'), indent=1)
for mach in ('3bda','genoa'):
    a = {(r['model'],r['users'],r['prompt']): r for r in R[mach+'-0922']}
    b = {(r['model'],r['users'],r['prompt']): r for r in R[mach+'-0923']}
    print(f"== {mach}: 09-22 vs 09-23  (TPS mean over Done samples; n samples)")
    for k in list(a)+[k for k in b if k not in a]:
        x=a.get(k); y=b.get(k)
        fx = f"{x['tps']:8.2f} n{x['n']:<4d} ttft{x['ttft']:6d}" if x else " "*26
        fy = f"{y['tps']:8.2f} n{y['n']:<4d} ttft{y['ttft']:6d}" if y else " "*26
        d = f"{100*(y['tps']/x['tps']-1):+6.2f}%" if x and y else ""
        print(f"{k[0][:36]:36s} u{k[1]:<3d} p{str(k[2]):5s} | {fx} | {fy} | {d}")
