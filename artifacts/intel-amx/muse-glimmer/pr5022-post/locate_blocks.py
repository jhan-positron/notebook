#!/usr/bin/env python3
"""For each code block of the replies to be posted: where its first and last line stand in the pushed head.
Prints the sentence before the block, so that a stated line range can be compared. Usage: locate_blocks.py <md dir>"""
import os, re, sys
md = sys.argv[1]
FINAL = '/home/jhan/workspace/ai-runs/pr5022-final/tron'
files = ['h/tron/kernels/amx_attn_iface.hpp', 'h/tron/kernels/amx_attn_transpose.hpp', 'h/tron/models/self_attention.hpp',
         'README.ci.md', 'src/tron/CMakeLists.txt', 'src/tron/kernels/amx_attn.cpp', 't/CMakeLists.txt',
         't/t_amx_dispatch_dtype.cpp', 't/t_amx_numerics.cpp', 't/t_llama_unit.cpp', 'config/test-benchmarks.json']
norm = lambda x: re.sub(r'\s+', ' ', x).strip()
src = {f: [norm(l) for l in open(os.path.join(FINAL, f), errors='replace').read().split('\n')] for f in files}
def find(q):
    hits = []
    for f, lines in src.items():
        for i, l in enumerate(lines, 1):
            if q and q == l: hits.append((f, i))
    return hits
names = ['COMBINED'] + [f'I{i}' for i in range(1, 27)]
for n in names:
    t = open(os.path.join(md, n + '.md')).read()
    for m in re.finditer(r'^(`{3,})(\w*)\n(.*?)\n\1\s*$', t, re.S | re.M):
        lang, body = m.group(2), m.group(3)
        before = t[:m.start()].strip().split('\n')[-1][-110:]
        lines = [l for l in body.split('\n') if norm(l) and norm(l) != '...' and not l.startswith(('---', '+++', '@@', '// t/'))]
        if lang == 'diff': lines = [l[1:] for l in lines if not l.startswith('-')]
        first, last = find(norm(lines[0])), find(norm(lines[-1]))
        fmt = lambda h: ', '.join(f'{f.split("/")[-1]}:{i}' for f, i in h[:3]) or 'no whole-line match'
        print(f'{n:8} "...{before}"\n         first line -> {fmt(first)} | last line -> {fmt(last)}')
