#!/usr/bin/env python3
"""Per-function compare of the AMX kernel object between trees. Usage: objcmp-compare.py <objcmp dir>.

Inputs: <dir>/out-<tag>/amx_attn.dis for the tags 5061623a34, 4c4b7b8864, final, built (llvm-objdump -d -r
--no-show-raw-insn --no-leading-addr of an object file) and <dir>/out-linked/amx_attn.dis (the same functions
disassembled from the linked gen/runtron). Writes <dir>/objcmp.txt, and one diff file per differing function.

Two kinds of compare:
  exact   object against object: instruction and relocation lines must be equal as text.
  masked  object against linked binary: the linker fills in addresses, so these are masked on both sides before
          the compare: relocation lines, the displacement of rip-relative operands, and the target of a call or
          of a branch that leaves the function. A branch inside the function keeps its offset. Padding after the
          last instruction (int3 or nop, which the linker puts between functions) is dropped.
"""
import difflib, glob, os, re, subprocess, sys

oc = sys.argv[1]
PAIRS = [('5061623a34', 'final', 'exact'), ('4c4b7b8864', 'final', 'exact'), ('5061623a34', '4c4b7b8864', 'exact'),
         ('final', 'built', 'exact'), ('built', 'linked', 'masked')]

def functions(path):
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

def masked(lines, name):
    keep = []
    for i, x in enumerate(lines):
        if 'R_X86_64' in x:
            continue                                          # relocation line: only in the object
        relocated = i + 1 < len(lines) and 'R_X86_64' in lines[i + 1]
        x = re.sub(r'\s*#.*$', '', x)                         # objdump's own comments
        x = re.sub(r'(-?0x[0-9a-f]+)?\(%rip\)', 'D(%rip)', x) # rip-relative data reference
        m = re.match(r'^(j\w+|call\w*)\s+0x[0-9a-f]+ <(.+?)(\+0x[0-9a-f]+)?>$', x)
        if m:
            op, sym, off = m.groups()
            inside = sym == name and not relocated and not op.startswith('call')
            x = f'{op} {off or "+0x0"}' if inside else f'{op} TARGET'
        keep.append(x)
    while keep and re.match(r'^(int3|nop\w*(\s.*)?|data16\s.*|cs\s+nop.*|xchgw\s+%ax, %ax)$', keep[-1]):
        keep.pop()                                            # padding between functions
    return keep

def demangle(names):
    try:
        p = subprocess.run(['c++filt'], input='\n'.join(names), capture_output=True, text=True)
        return dict(zip(names, p.stdout.split('\n')))
    except Exception:
        return {n: n for n in names}

def short(name):
    """A readable name: the function with its group size, without the parameter list."""
    m = re.search(r'amx_attn_h128g4::(?:\(anonymous namespace\)::)?(\w+)(?:<(\d+)ul?>)?', name)
    if m:
        return m.group(1) + (f'<{m.group(2)}>' if m.group(2) else '')
    m = re.search(r'amx_attn_h128g4(\d+)(\w+?)ILm(\d+)E', name)   # mangled template name that c++filt left alone
    if m:
        return f'{m.group(2)[:int(m.group(1))]}<{m.group(3)}>'
    return name[:60]

for stale in glob.glob(f'{oc}/diff-*.txt'):
    os.remove(stale)
dis = {t: functions(f'{oc}/out-{t}/amx_attn.dis') for t in {p[0] for p in PAIRS} | {p[1] for p in PAIRS}}
lines = ['# per-function compare of src/tron/kernels/amx_attn.cpp', '# ' + open(f'{oc}/build-info.txt').read().rstrip('\n').replace('\n', '\n# ')]
summary = []
for a, b, kind in PAIRS:
    fa, fb = dis[a], dis[b]
    names = sorted(set(fa) | set(fb)) if kind == 'exact' else sorted(fa)
    dm = demangle(names)
    lines += ['', f'## {a} vs {b} ({kind} compare)', f'{"instr " + a:>18} {"instr " + b:>18} {"only in A":>10} {"only in B":>10}  function']
    same = differ = missing = 0
    for n in names:
        la, lb = fa.get(n), fb.get(n)
        if la is None or lb is None:
            lines.append(f'{"-" if la is None else len(la):>18} {"-" if lb is None else len(lb):>18} {"":>10} {"":>10}  {short(dm[n])}   <-- only in one input')
            missing += 1; continue
        ca, cb = (masked(la, n), masked(lb, n)) if kind == 'masked' else (la, lb)
        d = list(difflib.unified_diff(ca, cb, lineterm='', n=0))
        minus = sum(1 for x in d if x.startswith('-') and not x.startswith('---'))
        plus = sum(1 for x in d if x.startswith('+') and not x.startswith('+++'))
        ia = sum(1 for x in la if 'R_X86_64' not in x); ib = sum(1 for x in lb if 'R_X86_64' not in x)
        lines.append(f'{ia:>18} {ib:>18} {minus:>10} {plus:>10}  {short(dm[n])}')
        if d:
            differ += 1
            open(f'{oc}/diff-{a}-vs-{b}-{short(dm[n]).replace("<", "_").replace(">", "")}.txt', 'w').write(dm[n] + '\n' + '\n'.join(d) + '\n')
        else:
            same += 1
    summary.append(f'# {a} vs {b} ({kind}): {len(names)} functions, {same} identical, {differ} differ, {missing} only in one input')
    lines.append(summary[-1])
lines += ['', '# summary'] + summary
text = '\n'.join(lines) + '\n'
open(f'{oc}/objcmp.txt', 'w').write(text)
print('\n'.join(summary))
