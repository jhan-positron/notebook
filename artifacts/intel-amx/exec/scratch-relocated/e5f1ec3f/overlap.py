#!/usr/bin/env python3
# For every line PR 5047 REMOVES (present at a5697f86d3, the PR 4956 head = PR 5047 base), ask git blame at a5697f86d3
# which commit introduced it. If that commit is in the PR 4956 range (76bb0bf3f4..a5697f86d3) the removed line is
# PR 4956 code; otherwise it is pre-existing main code. Also count ADDED lines per file.
import subprocess, re, sys, collections
REPO='/home/jhan/workspace/ai-runs/tron-main-ro'
BASE='a5697f86d3'; HEAD='ade89a9d9c'; MB='76bb0bf3f4'
def run(*a): return subprocess.run(['git','-C',REPO]+list(a),capture_output=True,text=True).stdout
pr4956 = set(run('rev-list', f'{MB}..{BASE}').split())
pr4956_short = {c[:10] for c in pr4956}
diff = run('diff','-U0',f'{BASE}..{HEAD}')
cur=None; removed=collections.defaultdict(list); added=collections.Counter()
old_line=None
for ln in diff.splitlines():
    if ln.startswith('--- '): continue
    if ln.startswith('+++ b/'): cur=ln[6:]; continue
    if ln.startswith('+++ '): continue
    m=re.match(r'^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',ln)
    if m: old_line=int(m.group(1)); continue
    if ln.startswith('-') and cur: removed[cur].append(old_line); old_line+=1; continue
    if ln.startswith('+') and cur: added[cur]+=1; continue
print(f"{'file':40s} {'removed':>7s} {'of which PR4956':>15s} {'pre-existing':>12s} {'added':>6s}")
tot=[0,0,0,0]
for f in sorted(set(list(removed)+list(added))):
    lines=removed.get(f,[])
    n4956=0; npre=0; pre_examples=[]
    if lines:
        blame=run('blame','-l','--line-porcelain',BASE,'--',f)
        # map line number -> commit
        commit_of={}; cur_commit=None
        for b in blame.splitlines():
            m=re.match(r'^([0-9a-f]{40}) (\d+) (\d+)',b)
            if m: cur_commit=m.group(1); lineno=int(m.group(3)); commit_of[lineno]=cur_commit
        for L in lines:
            c=commit_of.get(L)
            if c in pr4956: n4956+=1
            else:
                npre+=1
                pass
    print(f"{f:40s} {len(lines):7d} {n4956:15d} {npre:12d} {added.get(f,0):6d}")
    tot[0]+=len(lines); tot[1]+=n4956; tot[2]+=npre; tot[3]+=added.get(f,0)
    if pre_examples:
        # show the pre-existing removed lines with their text
        src=run('show',f'{BASE}:{f}').splitlines()
        for L,c in pre_examples:
            txt=src[L-1] if L-1 < len(src) else ''
            print(f"    pre-existing removed {f}:{L} (blame {c}): {txt.strip()[:110]}")
print(f"{'TOTAL':40s} {tot[0]:7d} {tot[1]:15d} {tot[2]:12d} {tot[3]:6d}")
