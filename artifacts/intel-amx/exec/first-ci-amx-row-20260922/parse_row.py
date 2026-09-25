import re, sys, json, statistics as st
def parse(path, model, users, plen):
    lines = open(path, encoding='utf-8', errors='replace').read().splitlines()
    # find config block: n_users=<users> followed within 6 lines by model=... and prompt_length=plen
    starts = []
    for i, l in enumerate(lines):
        if f"n_users={users}," in l:
            blk = "\n".join(lines[i:i+12])
            if f"model='{model}'" in blk and f"prompt_length={plen}," in blk:
                starts.append(i)
    if not starts: return None
    i0 = starts[-1]
    # end: next "n_users=" config line or "Provisioning"/"Running round (1/" of another config
    i1 = len(lines)
    for j in range(i0+12, len(lines)):
        if re.search(r"n_users=\d+,", lines[j]) or "provision" in lines[j].lower() and "Running round" not in lines[j]:
            i1 = j; break
    seg = lines[i0:i1]
    tps = []; ttft = []; rounds = []; per_round = []; cur = []
    for l in seg:
        m = re.search(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)", l)
        if m: ttft.append(int(m.group(1))); tps.append(float(m.group(2))); cur.append(float(m.group(2)))
        m = re.search(r"Running averages: TTFT=(\d+), TPS=([\d.]+)", l)
        if m: rounds.append((int(m.group(1)), float(m.group(2)))); per_round.append(round(st.mean(cur), 3)) if cur else None; cur = []
    ts = [re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)", l) for l in seg]
    ts = [t.group(1) for t in ts if t]
    engines = [l for l in seg if "inference engines are running" in l or "upstreams are healthy" in l]
    pre = [l for l in lines[max(0,i0-60):i0] if "engines are running" in l or "upstreams" in l or "skip" in l.lower() or "provision" in l.lower()]
    s = sorted(tps)
    p05 = s[int(0.05*len(s))] if s else None
    return dict(file=path, config_line=i0+1, n_samples=len(tps), tps_mean=st.mean(tps), tps_sd=st.pstdev(tps), tps_min=min(tps), tps_max=max(tps), p05=p05,
                ttft_mean_ms=st.mean(ttft), ttft_min=min(ttft), ttft_max=max(ttft), round_running_avgs=rounds, per_round_means=per_round, first_ts=ts[0], last_ts=ts[-1],
                engine_lines=[e.split('\t')[-1][:160] for e in engines], pre_lines=[e.split('\t')[-1][:200] for e in pre][-8:])
out = {}
out['3bda'] = parse('nightly-35683952944.log', 'llama-3.1-8b-instruct-good-tp2', 32, 4096)
out['genoa'] = parse('nightly-genoa-35682128668.log', 'llama-3.1-8b-instruct-good-tp2', 32, 4096)
out['3bda_8u'] = parse('nightly-35683952944.log', 'llama-3.1-8b-instruct-good-tp2', 8, 1024)
json.dump(out, open('nightly_rows.json','w'), indent=1)
for k,v in out.items():
    print(k, {kk:(round(vv,3) if isinstance(vv,float) else vv) for kk,vv in v.items() if kk not in ('round_running_avgs','engine_lines','pre_lines')})
    print('  rounds:', v['round_running_avgs'])
    print('  engines:', v['engine_lines'][:3]); print('  pre:', v['pre_lines'])
