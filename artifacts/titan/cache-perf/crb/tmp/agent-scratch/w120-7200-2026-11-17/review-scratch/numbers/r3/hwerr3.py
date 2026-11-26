import re, datetime as dt
D='/home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117'
recs=[]  # (time, lineno, id, severity)
lines=open(D+'/h-5.txt').read().split('\n')
cur=None
for no,l in enumerate(lines,1):
    m=re.match(r'(\S+) ubuntu kernel: \{(\d+)\}\[Hardware Error\]: (.*)$', l)
    if not m: continue
    t=dt.datetime.fromisoformat(m.group(1)).replace(tzinfo=None)
    if m.group(3).startswith('Hardware error from APEI'):
        cur={'t':t,'line':no,'id':int(m.group(2)),'sev':None}; recs.append(cur)
    elif m.group(3).startswith('event severity:') and cur is not None and cur['sev'] is None:
        cur['sev']=m.group(3).split(': ')[1].strip()
import collections
print(len(recs), collections.Counter(r['sev'] for r in recs))
def win(a,b,label):
    a=dt.datetime.fromisoformat(a); b=dt.datetime.fromisoformat(b)
    rr=[r for r in recs if a<=r['t']<=b]
    print(label, a, b, len(rr), [(str(r['t'])[11:], r['line'], r['sev']) for r in rr])
win('2026-11-17T02:05:54','2026-11-17T02:06:56','L-1 a6456')
win('2026-11-15T18:51:45','2026-11-15T18:53:40','L-2 p1nop')
win('2026-11-15T18:53:45','2026-11-15T18:55:50','L-2 p2add')
win('2026-11-15T20:33:04','2026-11-15T20:34:18','L-3 thp')
win('2026-11-15T20:34:43','2026-11-15T20:35:12','L-4 st1')
win('2026-11-15T20:35:17','2026-11-15T20:35:46','L-4 st2')
win('2026-11-15T20:35:52','2026-11-15T20:36:21','L-4 st3')
win('2026-11-13T18:17:21','2026-11-13T20:58:43','A-1 first launch .. launch after last A-3')
win('2026-11-13T18:17:21','2026-11-13T18:18:40','A-1')
win('2026-11-13T20:50:55','2026-11-13T20:51:36','A-2')
win('2026-11-13T20:58:16','2026-11-13T20:58:43','A-3')
win('2026-11-15T18:54:51','2026-11-15T18:54:55','lowest asmread interval')
# B7/C3/B5 not checked
print('first rec', recs[0]['t'], 'last', recs[-1]['t'])
