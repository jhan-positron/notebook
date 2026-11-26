#!/usr/bin/env python3
"""Check that every line of every code block in the replies to be posted occurs in the pushed head (or, for a
removed diff line, in the reviewed commit), or in the PR description draft. Usage: check_quotes.py <md dir>"""
import glob, os, re, subprocess, sys
md = sys.argv[1]
FINAL = '/home/jhan/workspace/ai-runs/pr5022-final/tron'
OLD = '/home/jhan/workspace/ai-runs/pr5022-isaac/tron-head'
BODY = '/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-body-round2.final.md'   # the description to be posted
files = ['changelog.d/5022.changed.md', 'config/test-benchmarks.json', 'h/tron/kernels/amx_attn_iface.hpp',
         'h/tron/kernels/amx_attn_transpose.hpp', 'h/tron/models/self_attention.hpp', 'README.ci.md',
         'src/tron/CMakeLists.txt', 'src/tron/kernels/amx_attn.cpp', 't/CMakeLists.txt', 't/t_amx_dispatch_dtype.cpp',
         't/t_amx_numerics.cpp', 't/t_llama_unit.cpp']
norm = lambda x: re.sub(r'\s+', ' ', x).strip()
def load(root):
    txt = ''
    for f in files:
        p = os.path.join(root, f)
        if os.path.exists(p): txt += '\n' + open(p, errors='replace').read()
    return norm(txt)
final = load(FINAL) + ' ' + norm(open(BODY).read()); old = load(OLD)
names = ['COMBINED'] + [f'I{i}' for i in range(1, 27)]
miss = 0; total = 0
for n in names:
    t = open(os.path.join(md, n + '.md')).read()
    for m in re.finditer(r'^(`{3,})(\w*)\n(.*?)\n\1\s*$', t, re.S | re.M):
        lang, body = m.group(2), m.group(3)
        for line in body.split('\n'):
            raw = line
            src = final
            if lang == 'diff':
                if line.startswith(('---', '+++', '@@')): continue
                if line.startswith('-'): src = old
                line = line[1:]
            q = norm(line)
            if not q or q == '...' or q.startswith('// t/'): continue
            total += 1
            if q not in src:
                miss += 1; print(f'{n}: NOT FOUND ({"reviewed commit" if src is old else "final head"}): {raw.strip()[:150]}')
print(f'{total} quoted lines checked, {miss} not found')
