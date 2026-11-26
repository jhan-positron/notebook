import re
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read().split('\n')
n = 0
out = []
for i, line in enumerate(B):
    for m in re.finditer(r'mesh', line, flags=re.I):
        n += 1
        s, e = m.start(), m.end()
        pre = line[max(0, s-70):s]
        post = line[e:e+60]
        out.append(f"{i+1:4d} c{s:<5d} ...{pre}[[{line[s:e]}]]{post}...")
print(n)
open('meshocc.txt','w',encoding='utf-8').write('\n'.join(out))
