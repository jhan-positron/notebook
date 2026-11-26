#!/usr/bin/env python3
"""backport.py CHILD LINE... - copy the rows of CHILD (lines LINE...) to the equal lines of the file that CHILD
takes its rows from, when the two source lines are equal. The line tokens are moved. Main session only.
With --dry it only prints what it would do."""
import difflib, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl

args = [a for a in sys.argv[1:] if a != '--dry']
dry = '--dry' in sys.argv
child = args[0]
lines = [int(x) for x in args[1:]]
m = lbl.manifest()
parent = m[child]['seed_from']
A = lbl.source_lines(m[parent]['src'])[0]
B = lbl.source_lines(m[child]['src'])[0]
b2a = {}
for i, j, n in difflib.SequenceMatcher(None, A, B, autojunk=False).get_matching_blocks():
    for k in range(n):
        b2a[j + k + 1] = i + k + 1
errs = []
own_c, seed_c, _ = lbl.load_ann(child, errs)
merged_c = dict(seed_c); merged_c.update(own_c)
changes = {}
for b in lines:
    if b not in b2a:
        print('line %d of %s has no equal line in %s: skipped' % (b, child, parent)); continue
    a = b2a[b]
    text = merged_c[b]
    ok = True
    def rep(mm):
        global ok
        x = int(mm.group(1)); y = int(mm.group(2)) if mm.group(2) else None
        if x not in b2a or (y is not None and y not in b2a):
            ok = False; return mm.group(0)
        return '{L%d}' % b2a[x] if y is None else '{L%d-%d}' % (b2a[x], b2a[y])
    new = ''.join(pc[2] if pc[0] == 'code' else lbl.TOKEN_RE.sub(rep, pc[1]) for pc in lbl.spans(text))
    if not ok:
        print('line %d: a line token has no equal line in %s: skipped' % (b, parent)); continue
    changes[a] = new
done = set()
for path in lbl.ann_paths(parent):
    L = open(path, encoding='utf-8').read().split('\n')
    ch = False
    for i, l in enumerate(L):
        mm = re.match(r'^(\d+): ', l)
        if mm and int(mm.group(1)) in changes:
            a = int(mm.group(1))
            if l != '%d: %s' % (a, changes[a]):
                print('%s line %d\n   old: %s\n   new: %s' % (parent, a, l[len(mm.group(0)):][:230], changes[a][:230]))
                L[i] = '%d: %s' % (a, changes[a]); ch = True
            done.add(a)
    if ch and not dry:
        open(path + '.tmp', 'w', encoding='utf-8').write('\n'.join(L)); os.replace(path + '.tmp', path)
miss = sorted(set(changes) - done)
if miss:
    print('no own row in %s for the lines %s (rows from a seed there: not changed)' % (parent, miss))
print('%s: %d rows %s' % (parent, len(done), 'would be replaced' if dry else 'replaced'))
