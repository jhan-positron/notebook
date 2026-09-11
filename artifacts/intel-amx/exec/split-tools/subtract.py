#!/usr/bin/env python3
"""Delete verified concern regions from files of the rebased tree R by TEXT match.

Regions are (file, lo-hi) line ranges of the PR head 60d66d9c04 (hunks.csv).
For each region the head text block is located in the target file; it must
occur exactly once, else the region is reported and nothing is changed.
Usage: subtract.py <repo> <head-rev> <concern-regex> [--apply] [--only file]
Writes nothing unless --apply. Prints one line per region: OK / MISSING / MULTI.
"""
import csv,re,sys,subprocess,collections
repo=sys.argv[1]; head=sys.argv[2]; pat=re.compile(sys.argv[3]); apply='--apply' in sys.argv
only=None
if '--only' in sys.argv: only=sys.argv[sys.argv.index('--only')+1]
CSV=os.path.join(os.path.dirname(os.path.abspath(__file__)),"concern-map-hunks.csv")
rows=[r for r in csv.DictReader(open(CSV)) if pat.search(r['concern']) and (only is None or r['file']==only)]
byfile=collections.defaultdict(list)
for r in rows:
    lo,hi=(r['region'].split('-')+[None])[:2]; lo=int(lo); hi=int(hi) if hi else lo
    byfile[r['file']].append((lo,hi,r['concern'],r['why']))
def headlines(f):
    return subprocess.run(['git','-C',repo,'show',f'{head}:{f}'],capture_output=True,text=True).stdout.split('\n')
status=collections.Counter()
for f,regs in byfile.items():
    hl=headlines(f)
    path=f'{repo}/{f}'
    try: cur=open(path).read().split('\n')
    except FileNotFoundError:
        print(f'SKIP {f}: not in tree'); continue
    # locate ascending with a moving cursor (duplicated text resolves to the
    # next occurrence in file order, as in the head file), then delete bottom-up
    regs.sort(key=lambda x:x[0])
    cursor=0; found=[]
    for lo,hi,c,why in regs:
        block=hl[lo-1:hi]; n=len(block)
        hits=[i for i in range(cursor,len(cur)-n+1) if cur[i:i+n]==block]
        if hits:
            i=hits[0]; found.append((i,n)); cursor=i+n
            status['OK']+=1; print(f'OK      {f}:{lo}-{hi} -> R:{i+1}{"" if len(hits)==1 else " (first of %d after cursor)"%len(hits)} [{c}] {why[:50]}')
        else:
            status['MISSING']+=1; print(f'MISSING {f}:{lo}-{hi} [{c}] first={block[0][:60]!r}')
    for i,n in sorted(found,reverse=True):
        del cur[i:i+n]
    if apply: open(path,'w').write('\n'.join(cur))
print('SUMMARY',dict(status), 'apply' if apply else 'dry-run')
