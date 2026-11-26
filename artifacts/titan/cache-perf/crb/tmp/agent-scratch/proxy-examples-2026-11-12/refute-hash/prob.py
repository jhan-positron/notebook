import csv
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/full/'
base=[int(c['pfn_hex'],16)*4096 for c in csv.DictReader(open(R+'chunks.csv'))]
par=lambda x: bin(x).count('1')&1
d=[(b^base[0])>>21 for b in base[1:]]
img_all={tuple(par(m&x) for x in d) for m in range(1<<16)}
img_even={tuple(par(m&x) for x in d) for m in range(1<<16) if m&0x5555==0}  # bits 22,24.. = odd indices
print('patterns reachable by any linear mask',len(img_all),'of',2**15,'; by even-only mask',len(img_even))
print('P(random 15-bit pattern fits even-only)=1/%d ; P(given linear-consistent)=1/%d'%(2**15//len(img_even),len(img_all)//len(img_even)))
print('physically adjacent consecutive chunks',[c for c in range(15) if base[c+1]==base[c]+(1<<21)])
