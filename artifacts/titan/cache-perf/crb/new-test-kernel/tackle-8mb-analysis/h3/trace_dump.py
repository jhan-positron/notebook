#!/usr/bin/env python3
"""trace_dump.py <S4.csv>...: print each sustained process as one line of window rates (GB/s, 1 decimal),
with the launch time, so that level switches can be read by eye."""
import sys
def procs(path):
    cur=None
    for line in open(path):
        line=line.rstrip('\n')
        if line.startswith('-- step'):
            f=line.split()
            cur={'hdr':line,'tag':f[f.index('tag')+1],'utc':f[f.index('utc')+1],'W':[],'P':[],'M':{}}
            yield_list.append(cur)
        elif cur is None: continue
        elif line.startswith('W,'):
            p=line.split(','); cur['W'].append((int(p[3]),int(p[6]),int(p[7]),int(p[8])))
        elif line.startswith('M,'):
            p=line.split(',',2); cur['M'][p[1]]=p[2]
        elif line.startswith('P,') or line.startswith('E,'):
            cur['P'].append(line)
for path in sys.argv[1:]:
    yield_list=[]
    procs(path)
    for c in yield_list:
        print(c['tag'], c['utc'], 'cpu', c['M'].get('cpu'))
        for l in c['P']: print('   ',l)
        r=[b/(e-s) for _,b,s,e in c['W']]
        for i in range(0,len(r),25):
            print('   %5.1fs '%(c['W'][i][2]/1e9)+' '.join('%4.1f'%x for x in r[i:i+25]))
