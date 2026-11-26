import sys, difflib, re
A = open('/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html', encoding='utf-8').read().split('\n')
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read().split('\n')
changed = [i for i in range(min(len(A), len(B))) if A[i] != B[i]]
CTX = 90
n = 0
out = []
for i in changed:
    a, b = A[i], B[i]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    ops = [op for op in sm.get_opcodes() if op[0] != 'equal']
    out.append(f"===== LINE {i+1}  (len before {len(a)}, after {len(b)}; {len(ops)} raw ops)")
    # merge ops that are close together (within 12 chars) to give readable hunks
    merged = []
    for tag, i1, i2, j1, j2 in ops:
        if merged and i1 - merged[-1][1] <= 12:
            merged[-1][1] = i2; merged[-1][3] = j2
        else:
            merged.append([i1, i2, j1, j2])
    for (i1, i2, j1, j2) in merged:
        n += 1
        pre = a[max(0, i1-CTX):i1]
        post = a[i2:i2+CTX]
        out.append(f"  [{n}] col {i1}")
        out.append(f"     ctx-before: ...{pre}")
        out.append(f"     OLD: «{a[i1:i2]}»")
        out.append(f"     NEW: «{b[j1:j2]}»")
        out.append(f"     ctx-after : {post}...")
print(n, "hunks")
open('segdiff.txt', 'w', encoding='utf-8').write('\n'.join(out))
