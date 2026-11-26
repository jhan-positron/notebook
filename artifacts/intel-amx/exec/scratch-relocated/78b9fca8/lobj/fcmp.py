#!/usr/bin/env python3
"""Per-function compare of two object files (objdump -d -r, addresses stripped).
Usage: fcmp.py a.o b.o"""
import difflib, re, subprocess, sys
def functions(path):
    txt = subprocess.run(['objdump', '-d', '-r', '--no-show-raw-insn', path], capture_output=True, text=True).stdout
    out, cur = {}, None
    for line in txt.split('\n'):
        m = re.match(r'^[0-9a-f]+ <(.+)>:$', line)
        if m:
            cur = m.group(1); out[cur] = []; continue
        if cur is None or not line.strip() or line.startswith('Disassembly of section'):
            continue
        l = re.sub(r'^\s*[0-9a-f]+:\s*', '', line)           # leading address
        l = re.sub(r'\s+#.*$', '', l)                        # trailing address comments
        l = re.sub(r'\b[0-9a-f]+ <([^>+]+)(\+0x[0-9a-f]+)?>', r'<\1\2>', l)  # absolute branch targets
        out[cur].append(l.strip())
    return out
a, b = functions(sys.argv[1]), functions(sys.argv[2])
tot = 0
for n in sorted(set(a) | set(b)):
    la, lb = a.get(n), b.get(n)
    short = re.sub(r'^_ZN4tron15amx_attn_h128g4', '', n)[:70]
    if la is None or lb is None:
        print(f'{"-" if la is None else len(la):>6} {"-" if lb is None else len(lb):>6}  ONLY IN ONE  {short}'); tot += 1; continue
    d = [x for x in difflib.unified_diff(la, lb, lineterm='', n=0) if x[:1] in '+-' and x[:3] not in ('+++', '---')]
    print(f'{len(la):>6} {len(lb):>6}  {"identical" if not d else "DIFF %d lines" % len(d):<14} {short}')
    if d:
        tot += 1
        for x in d[:12]: print('         ', x)
print('functions that differ:', tot)
