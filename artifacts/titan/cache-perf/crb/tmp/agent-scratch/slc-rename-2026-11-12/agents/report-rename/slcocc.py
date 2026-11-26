import re
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read().split('\n')
A = open('/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html', encoding='utf-8').read().split('\n')
n = 0
out = []
for i, line in enumerate(B):
    for m in re.finditer(r'SLC|slc|system level cache|System Level Cache|\bL3\b', line):
        n += 1
        s, e = m.start(), m.end()
        pre = line[max(0, s-55):s]
        post = line[e:e+45]
        out.append(f"{i+1:4d} ...{pre}[[{line[s:e]}]]{post}...")
print(n, "after;", sum(len(re.findall(r'SLC|slc|system level cache|System Level Cache|\bL3\b', l)) for l in A), "before")
open('slcocc.txt','w',encoding='utf-8').write('\n'.join(out))
