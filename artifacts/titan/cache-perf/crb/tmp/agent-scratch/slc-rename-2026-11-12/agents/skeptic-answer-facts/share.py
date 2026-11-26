import sys,re,collections
def parse(path):
    blocks=[]; cur=None
    for i,l in enumerate(open(path).read().split('\n'),1):
        if l.startswith('-- '):
            cur={'hdr':l,'line':i,'rows':[],'perf':[]}
            blocks.append(cur)
        elif cur is not None:
            p=l.split(',')
            if len(p)>=7 and p[0] and p[0][0].isalpha() and p[3].isdigit():
                cur['rows'].append((i,p))
            elif len(p)>=5 and p[2].startswith('arm_cmn') :
                cur['perf'].append((i,p))
            elif len(p)>=5 and re.match(r'^\d',p[0]) and '/' in p[2]:
                cur['perf'].append((i,p))
    return blocks
for path in sys.argv[1:]:
    print('==',path)
    B=parse(path)
    # idle block
    idle={}
    for b in B:
        if 'background' in b['hdr'] or 'idle' in b['hdr']:
            for i,p in b['perf']:
                idle[p[2]]=(int(p[0]),int(p[3]))
    # pair short/long
    by=collections.defaultdict(dict)
    for b in B:
        m=re.match(r'-- (\S+) (short|long) events (\S+) args (.*)',b['hdr'])
        if not m: continue
        by[(m.group(1),m.group(3))][m.group(2)]=b
    for (case,ev),d in by.items():
        if 'short' not in d or 'long' not in d: continue
        s,l=d['short'],d['long']
        if not s['rows'] or not l['rows']: continue
        sb=int(s['rows'][0][1][4]); lb=int(l['rows'][0][1][4])
        lines=(lb-sb)/64
        out=[]
        for (i1,p1),(i2,p2) in zip(s['perf'],l['perf']):
            assert p1[2]==p2[2]
            dc=int(p2[0])-int(p1[0])
            out.append('%s: %.4f/line (csv %d,%d; pct %s,%s)'%(p1[2].split('/')[1]+'@'+p1[2].split('/')[0][-1],dc/lines,i1,i2,p1[4],p2[4]))
        print(case, 'bytes lines %d,%d'%(s['rows'][0][0],l['rows'][0][0]), 'rate short %s long %s'%(s['rows'][0][1][6],l['rows'][0][1][6]))
        for o in out: print('    ',o)
