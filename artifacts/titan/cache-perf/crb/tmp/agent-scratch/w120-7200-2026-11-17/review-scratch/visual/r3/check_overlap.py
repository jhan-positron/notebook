# check_overlap.py - text/text, text/mark and text/viewBox collisions in every visible figure svg, in viewBox units.
# Text box: x extent from the anchor and the computed text length that Chrome reported; y extent = baseline - 0.78 fs to baseline + 0.22 fs.
import json,sys
V='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3/work/'
def tb(t):
    x=float(t['x']); y=float(t['y']); fs=float(t['fs']); cl=t['cl']
    a=t['anchor'] or 'start'
    x0 = x if a=='start' else (x-cl if a=='end' else x-cl/2)
    return (x0, y-0.78*fs, x0+cl, y+0.22*fs)
def inter(a,b,pad=0):
    return min(a[2],b[2])-max(a[0],b[0])>pad and min(a[3],b[3])-max(a[1],b[1])>pad
for w in sys.argv[1:]:
    m=json.load(open(V+f'measure-{w}.json'))
    for s in m['svgs']:
        if not s['vis']: continue
        vb=[float(v) for v in s['viewBox'].split()]
        T=s['texts']; B=[tb(t) for t in T]
        print(f'== width {w} svg {s["i"]} {s["cls"]} viewBox {vb} texts {len(T)} marks {len(s["marks"])}')
        n=0
        for i in range(len(T)):
            b=B[i]
            if b[0]<0.5 or b[2]>vb[2]-0.5 or b[1]<0 or b[3]>vb[3]:
                print('  CLIP', repr(T[i]['s']), [round(v,1) for v in b]); n+=1
            for j in range(i+1,len(T)):
                if inter(b,B[j],0.3):
                    print('  TEXT/TEXT', repr(T[i]['s']), [round(v,1) for v in b], '<>', repr(T[j]['s']), [round(v,1) for v in B[j]]); n+=1
        for k in s['marks']:
            mb=(k['cx']-k['r']-1.1, k['cy']-k['r']-1.1, k['cx']+k['r']+1.1, k['cy']+k['r']+1.1)
            for i in range(len(T)):
                if inter(B[i],mb,0.2):
                    print('  TEXT/MARK', repr(T[i]['s']), [round(v,1) for v in B[i]], 'mark', k['cx'],k['cy'],k['fill'],k['stroke']); n+=1
        print('  collisions:', n)
        fss=sorted(set(float(t['fs']) for t in T)); print('  font sizes (viewBox units):', fss, 'scale', round((s['rect'][2]-s['rect'][0])/vb[2],3))
