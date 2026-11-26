import glob,re
R='/home/jhan/workspace/titan/cache-perf/asimov/results'
for f in sorted(glob.glob(R+'/membench-jibin-0*/results/*/*latency-dram-*.csv')):
    if 'slc' in f or 'tlb' in f or 'walk' in f or 'small' in f: continue
    hdr=''
    for ln,line in enumerate(open(f),1):
        line=line.rstrip()
        if line.startswith('# latency:'): hdr=' '.join(re.findall(r'(?:cpu|fresh|flush|sparse|seq|cme|loads)=\S+',line))
        p=line.split(',')
        if len(p)>=6 and p[0]=='dram' and p[2]=='best' and int(p[1]) in (8388608,16777216,33554432):
            print(f"{f.replace(R+'/','')}:{ln} | {line} | {hdr}")
