#!/usr/bin/env bash
# pr5022-final-20261119: compare the 4-head AMX kernels of main with the 4-head instantiations of the final tree.
# Runs ON delphi-3b35 after objcmp-3b35.sh (it reuses its flags.txt and its out-final listing). Compile only,
# pinned to our CPUs. Main (3bea58b788) has plain functions, the final tree has templates, so the symbol names
# differ. Before the compare, the function's own name is replaced by SELF and the name of a per-thread variable
# by TLSVAR. Output: exec/results/pr5022-final-20261119/objcmp/main-vs-final-4head.txt
set -u
OC=/home/jhan/workspace/intel-AMX/exec/results/pr5022-final-20261119/objcmp
TU=src/tron/kernels/amx_attn.cpp
PIN="nice -n10 taskset -c 96-143"
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
mapfile -t FLAGS <"$OC/flags.txt"
O=$OC/out-main; mkdir -p "$O"
( cd "$OC/src-main" >/dev/null 2>&1 && $PIN clang++-19 "${FLAGS[@]}" -c $TU -o "$O/amx_attn.o" 2>"$O/compile.err" ) || { echo "compile of main failed: $(head -3 "$O/compile.err")"; exit 1; }
$PIN llvm-objdump-19 -d -r --no-show-raw-insn --no-leading-addr "$O/amx_attn.o" >"$O/amx_attn.dis"
python3 - "$OC" <<'PY' | tee "$OC/main-vs-final-4head.txt"
import difflib, re, sys
oc = sys.argv[1]
def functions(path):
    out, cur = {}, None
    for line in open(path):
        line = line.rstrip('\n'); m = re.match(r'^<(.+)>:$', line)
        if m: cur = m.group(1); out[cur] = []; continue
        if cur is None or not line.strip() or line.startswith('Disassembly of section'): continue
        out[cur].append(line.strip())
    return out
def norm(lines, name):
    keep = []
    for x in lines:
        x = x.replace(name, 'SELF')
        x = re.sub(r'(R_X86_64_TLS\w+)\s+\S+?(-0x[0-9a-f]+)?$', r'\1 TLSVAR\2', x)
        keep.append(x)
    return keep
fm, ff = functions(f'{oc}/out-main/amx_attn.dis'), functions(f'{oc}/out-final/amx_attn.dis')
print('# 4-head AMX kernels: main 3bea58b788 (plain functions) vs the final tree (instantiations for 4 heads)')
print('# compiled on delphi-3b35 with the command of the final build (objcmp/flags.txt), clang 19.1.7')
print(f'{"instr main":>11} {"instr final":>12} {"only main":>10} {"only final":>11}  function')
for base in ('pack_q_group_128x4', 'qk_rowmajor_128x4', 'weights_times_v_128x4'):
    km = next(k for k in fm if re.search(rf'amx_attn_h128g4\d+{base}E', k))
    kf = next(k for k in ff if re.search(rf'amx_attn_h128g4\d+{base}ILm4E', k))
    a, b = norm(fm[km], km), norm(ff[kf], kf)
    d = list(difflib.unified_diff(a, b, lineterm='', n=0))
    minus = [x for x in d if x.startswith('-') and not x.startswith('---')]; plus = [x for x in d if x.startswith('+') and not x.startswith('+++')]
    ia = sum('R_X86_64' not in x for x in a); ib = sum('R_X86_64' not in x for x in b)
    print(f'{ia:>11} {ib:>12} {len(minus):>10} {len(plus):>11}  {base}')
    for x in d[2:]:
        print('      ' + x[:150])
PY
