#!/usr/bin/env python3
"""patch_rows.py - replace one exact piece of text in the row of one line of one key (main session).
Input on stdin: lines KEY<TAB>LINE<TAB>OLD<TAB>NEW."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl
ok = bad = 0
for raw in sys.stdin.read().split('\n'):
    if not raw.strip():
        continue
    key, line, old, new = raw.split('\t')
    line = int(line)
    hit = False
    for path in lbl.ann_paths(key):
        L = open(path, encoding='utf-8').read().split('\n')
        for i, l in enumerate(L):
            if l.startswith('%d: ' % line):
                if l.count(old) != 1:
                    print('NOT FOUND once: %s line %d: %r' % (key, line, old)); bad += 1; hit = True; break
                L[i] = l.replace(old, new)
                open(path + '.tmp', 'w', encoding='utf-8').write('\n'.join(L)); os.replace(path + '.tmp', path)
                ok += 1; hit = True; break
        if hit:
            break
    if not hit:
        print('NO OWN ROW: %s line %d' % (key, line)); bad += 1
print('%d rows changed, %d problems' % (ok, bad))
