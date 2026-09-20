import re, sys
for path in sys.argv[1:]:
    lines = open(path, errors='replace').read().splitlines()
    start = next(i for i,l in enumerate(lines) if '== Running performance tests ==' in l)
    end = next(i for i,l in enumerate(lines) if i > start and '== Running MMLU Pro ==' in l)
    perf = lines[start:end]
    idx = [i for i,l in enumerate(perf) if '== Benchmarking' in l] + [len(perf)]
    print('=====', path)
    for k in range(len(idx)-1):
        seg = perf[idx[k]:idx[k+1]]
        name = re.search(r'== Benchmarking (\S+) ==', seg[0]).group(1)
        avg_idx = [i for i,l in enumerate(seg) if 'Running averages' in l]
        if len(avg_idx) < 2: continue
        # Done lines between 2nd-to-last and last Running averages = last iteration
        last = seg[avg_idx[-2]+1:avg_idx[-1]+1]
        first = seg[:avg_idx[0]+1]
        def vals(block):
            out=[]
            for l in block:
                m = re.search(r'Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)\s+\S*\s*(\S+) tokens', l)
                if m: out.append((float(m.group(2)), int(m.group(1)), m.group(4)))
            return out
        lv = vals(last); fv = vals(first)
        print(f"{k+1:2d} {name:40s} last-iter n={len(lv):2d} TPS sorted={sorted(v[0] for v in lv)} TTFT={[v[1] for v in lv]} tokens={sorted(set(v[2] for v in lv))}")
        print(f"   {'':40s} first-iter n={len(fv):2d} TPS sorted={sorted(v[0] for v in fv)}")
