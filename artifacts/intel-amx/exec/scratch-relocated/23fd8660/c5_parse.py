import re, sys, statistics
L = sys.argv[1]
lines = open(L, errors='replace').read().split('\n')
# find config blocks: lines containing n_users=
cfg_idx = [i for i,l in enumerate(lines) if 'n_users=' in l]
print("config lines:", [(i+1, lines[i][:120]) for i in cfg_idx][:20])
# locate the 32-user llama block starting at/after line 1211
start = None
for i in cfg_idx:
    if i+1 >= 1205 and 'n_users=32' in lines[i]:
        start = i; break
print("32u block starts line", start+1)
end = len(lines)
for i in cfg_idx:
    if i > start:
        end = i; break
print("32u block ends before line", end+1)
done = re.compile(r'Done \(TTFT=([0-9.]+)[^,]*,\s*([0-9.]+)\s*/\s*([0-9.]+)\s*TPS')
tps=[]; ttft=[]; goals=set(); ts=[]
for i in range(start, end):
    m = done.search(lines[i])
    if m:
        ttft.append(float(m.group(1))); tps.append(float(m.group(2))); goals.add(m.group(3))
        t = re.match(r'(\S+\s+\S+)', lines[i]); ts.append(lines[i][:30])
print("Done samples:", len(tps), "goal strings:", goals)
print("first sample line:", ts[0] if ts else None, " last:", ts[-1] if ts else None)
print("TPS mean %.3f  pop sd %.3f  sample sd %.3f  min %.2f  max %.2f  median %.3f" % (statistics.mean(tps), statistics.pstdev(tps), statistics.stdev(tps), min(tps), max(tps), statistics.median(tps)))
s=sorted(tps); print("p05 %.3f p95 %.3f" % (s[int(0.05*len(s))], s[int(0.95*len(s))-1]))
print("TTFT mean %.1f ms min %.0f max %.0f" % (statistics.mean(ttft), min(ttft), max(ttft)))
ra = [ (i+1, lines[i][:200]) for i in range(start,end) if 'Running averages' in lines[i]]
print("Running averages lines:", len(ra))
for x in ra: print(x)
# final summary lines in block
for i in range(start,end):
    if re.search(r'(TPS|tps).*(mean|average|slowest|min)', lines[i], re.I) and 'Done' not in lines[i] and 'Running' not in lines[i]:
        print(i+1, lines[i][:200])
