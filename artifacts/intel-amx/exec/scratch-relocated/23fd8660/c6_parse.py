import re, statistics as st
path='nightly-genoa-35682128668.log'
lines=open(path,encoding='utf-8',errors='replace').read().splitlines()
# independent bounds: the "Running round (1/10)" right after the 03:42:14 config, up to and including the 10th "Running averages"
start=None
for i,l in enumerate(lines):
    if i>=1608 and 'Running round (1/10)' in l:
        start=i; break
end=None; n_avg=0
for j in range(start,len(lines)):
    if 'Running averages' in lines[j]:
        n_avg+=1
        if n_avg==10: end=j; break
seg=lines[start:end+1]
print('segment lines', start+1, '->', end+1, 'count', len(seg))
done=re.compile(r"Done \(TTFT=(\d+), ([\d.]+) / ([\d.]+) TPS\)")
tps=[];ttft=[];caps=set()
other=[]
for l in seg:
    m=done.search(l)
    if m:
        ttft.append(int(m.group(1))); tps.append(float(m.group(2))); caps.add(m.group(3))
    elif 'Running' not in l:
        other.append(l[:200])
print('n Done', len(tps), 'cap values', caps)
print('mean %.5f  pstdev %.5f  stdev(sample) %.5f  min %.2f  max %.2f' % (st.mean(tps), st.pstdev(tps), st.stdev(tps), min(tps), max(tps)))
s=sorted(tps); n=len(s)
print('p05 (index int(0.05n)=%d) %.2f ; p05 nearest-rank ceil(0.05n)=%d -> %.2f' % (int(0.05*n), s[int(0.05*n)], -(-5*n//100), s[-(-5*n//100)-1]))
print('TTFT mean %.2f ms  min %d  max %d  median %d' % (st.mean(ttft), min(ttft), max(ttft), st.median(ttft)))
print('rounded: mean TPS 1dp = %.1f ; 2dp = %.2f ; sd 3dp = %.3f ; TTFT s 1dp = %.1f' % (round(st.mean(tps),1), round(st.mean(tps),2), round(st.pstdev(tps),3), round(st.mean(ttft)/1000,1)))
print('non-Done, non-Running lines in segment:', len(other))
for o in other[:20]: print('   ', o)
# per-round counts
cnt=0; rounds=[]
for l in seg:
    if done.search(l): cnt+=1
    if 'Running averages' in l: rounds.append(cnt); cnt=0
print('Done per round', rounds)
# errors anywhere between config and next config
errs=[l[:200] for l in lines[1608:end+40] if re.search(r'ERROR|Traceback|Exception|failed|timeout', l, re.I)]
print('error-like lines in/after segment:', len(errs)); [print('   ',e) for e in errs[:10]]
