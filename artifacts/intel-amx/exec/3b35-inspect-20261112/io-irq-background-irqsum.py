import sys,re,collections
f=sys.argv[1]
lines=open(f,errors='replace').read().split('\n')
hdr=[l for l in lines if l.strip().startswith('CPU0')][0]
ncpu=len(hdr.split())
node0=set(list(range(0,72))+list(range(144,216)))
agg=collections.defaultdict(lambda:[0,0,0])
for l in lines:
    m=re.match(r'\s*(\S+):\s+(.*)',l)
    if not m or l.startswith('#'): continue
    parts=m.group(2).split()
    nums=[]
    for p in parts[:ncpu]:
        if p.isdigit(): nums.append(int(p))
        else: break
    if len(nums)<ncpu: 
        continue
    desc=' '.join(parts[ncpu:])
    name=m.group(1)
    if name.isdigit():
        d=desc.split()
        key=d[-1] if d else '?'
        key=re.sub(r'[-@]?\d+(@pci.*)?$','',key)   # fold queue numbers
        key=re.sub(r'\d+','N',key)
    else: key=name
    s0=sum(n for i,n in enumerate(nums) if i in node0); s1=sum(nums)-s0
    a=agg[key]; a[0]+=s0; a[1]+=s1; a[2]+=1
tot=sum(a[0]+a[1] for a in agg.values())
print(f"{'source':28s} {'lines':>6s} {'socket0':>16s} {'socket1':>16s} {'total':>16s}")
for k,a in sorted(agg.items(), key=lambda x:-(x[1][0]+x[1][1]))[:22]:
    print(f"{k:28s} {a[2]:6d} {a[0]:16d} {a[1]:16d} {a[0]+a[1]:16d}")
dev=[(k,a) for k,a in agg.items() if a[2]>0 and not k.isupper()]
