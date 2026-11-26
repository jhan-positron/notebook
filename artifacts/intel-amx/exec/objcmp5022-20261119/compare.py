#!/usr/bin/env python3
"""Compare the per-function disassembly and the thin-LTO IR of two builds of amx_attn.cpp.
Usage: compare.py <results dir> <tag A> <tag B>.  Writes <results dir>/objcmp.txt and prints it."""
import difflib, re, subprocess, sys
res, a, b = sys.argv[1:4]

def functions(path):
    """llvm-objdump -d -r --no-leading-addr output -> {symbol: [instruction or relocation lines]}"""
    out, cur = {}, None
    for line in open(path):
        line = line.rstrip('\n')
        m = re.match(r'^<(.+)>:$', line)
        if m:
            cur = m.group(1); out[cur] = []; continue
        if cur is None or not line.strip() or line.startswith('Disassembly of section'):
            continue
        out[cur].append(line.strip())
    return out

def demangle(names):
    try:
        p = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True)
        return dict(zip(names, p.stdout.split('\n')))
    except Exception:
        return {n: n for n in names}

fa, fb = functions(f'{res}/out-{a}/amx_attn.dis'), functions(f'{res}/out-{b}/amx_attn.dis')
names = sorted(set(fa) | set(fb))
dm = demangle(names)
lines = [f'# per-function compare of amx_attn.o (no LTO): {a} vs {b}', '# ' + open(f'{res}/build-info.txt').read().replace('\n', '\n# ').rstrip('# ')]
lines.append(f'{"instr " + a:>18} {"instr " + b:>18} {"only in A":>10} {"only in B":>10}  function')
total_diff = 0
for n in names:
    la, lb = fa.get(n), fb.get(n)
    if la is None or lb is None:
        lines.append(f'{"-" if la is None else len(la):>18} {"-" if lb is None else len(lb):>18} {"":>10} {"":>10}  {dm[n][:150]}   <-- only in one build')
        total_diff += 1; continue
    d = list(difflib.unified_diff(la, lb, lineterm='', n=0))
    minus = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
    plus = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
    total_diff += minus + plus
    # count instruction lines only (relocation lines carry "R_X86_64")
    ia = sum(1 for x in la if 'R_X86_64' not in x); ib = sum(1 for x in lb if 'R_X86_64' not in x)
    lines.append(f'{ia:>18} {ib:>18} {minus:>10} {plus:>10}  {dm[n][:150]}')
    if d:
        open(f'{res}/diff-{len(lines)}.txt', 'w').write(dm[n] + '\n' + '\n'.join(d) + '\n')
lines.append(f'# functions compared: {len(names)}; differing lines in total: {total_diff}')

def ir_body(path):
    keep = []
    for line in open(path):
        if line.startswith(('; ModuleID', 'source_filename')):
            continue
        keep.append(line.rstrip('\n'))
    return keep
ia, ib = ir_body(f'{res}/out-{a}/amx_attn.ll'), ir_body(f'{res}/out-{b}/amx_attn.ll')
d = list(difflib.unified_diff(ia, ib, lineterm='', n=0))
minus = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
plus = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
lines.append(f'# thin-LTO bitcode as text (whole module, ModuleID and source_filename lines dropped): {len(ia)} vs {len(ib)} lines, only in A {minus}, only in B {plus}')
if d:
    open(f'{res}/diff-ir.txt', 'w').write('\n'.join(d) + '\n')
text = '\n'.join(lines) + '\n'
open(f'{res}/objcmp.txt', 'w').write(text)
print(text)
