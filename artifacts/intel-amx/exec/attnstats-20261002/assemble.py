#!/usr/bin/env python3
"""Assemble attn-stats-compare.md = final_prose.md with gen_compare.py's tables at the GEN_TABLE_n placeholders."""
import re, sys, shutil, os
gen_path, prose_path, out = sys.argv[1], sys.argv[2], sys.argv[3]
gen = open(gen_path).read()
def section(prefix):
    m = re.search(r'^## ' + re.escape(prefix) + r'.*?$', gen, re.M)
    start = m.end() + 1
    nxt = gen.find('\n## ', start)
    return gen[start: nxt if nxt > 0 else len(gen)].strip('\n')
def table_only(block):
    lines = block.split('\n'); idx = [i for i, l in enumerate(lines) if l.startswith('|')]
    return '\n'.join(lines[idx[0]:idx[-1] + 1])
prose = open(prose_path).read()
s1 = section('1. What ran')
prose = re.sub(r'^GEN_TABLE_1$', lambda m: "Geometry, attention mode and throughput per cell (from the exit-report header lines and the runtron logs):\n\n" + table_only(s1) + "\n\n" + s1[s1.find('HW attention line and HBM warnings'):], prose, flags=re.M)
for n, pre in ((2, '2. K tokens'), (3, '3. Kill-switch'), (4, '4. Token jobs'), (5, '5. Per-layer'), (6, '6. Time')):
    prose = re.sub(r'^GEN_TABLE_%d$' % n, lambda m, pre=pre: section(pre), prose, flags=re.M)
assert 'GEN_TABLE' not in prose
if os.path.exists(out):
    shutil.copy(out, out + '.prev')
open(out, 'w').write(prose)
print(len(prose.split('\n')), 'lines ->', out)
