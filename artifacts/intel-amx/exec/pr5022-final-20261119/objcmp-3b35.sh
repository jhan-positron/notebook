#!/usr/bin/env bash
# pr5022-final-20261119 object compare. Runs ON delphi-3b35 after build-3b35.sh TAG=final.
# Compile only, pinned to our CPUs (96-143, low priority). Needs no AMX hardware, no FPGA card, no huge page.
#
# Question: does the AMX kernel file (src/tron/kernels/amx_attn.cpp) compile to the same instructions at
#   5061623a34  the commit the PR's performance numbers were measured at,
#   4c4b7b8864  the reviewed head, and
#   final       the prepared final tree (reviewed head merged with main, plus the review edits)?
#
# Method: each tree is an export that holds only h/ and the kernel file (exec/results/<name>/objcmp/src-<tag>).
# All three are compiled with the command the final build recorded for this file in gen/compile_commands.json.
# Only two things differ from that command: the tree's own h/ is used, and the paths are relative to the export
# root, so file names inside the object do not differ between trees. Third-party and generated headers come from
# the final build tree for all three. The object the final build itself produced is compared as a fourth input
# (tag "built"), and the kernel functions inside the linked gen/runtron are compared with it (tag "linked").
# Usage (on 3b35): bash objcmp-3b35.sh
# Log: exec/logs/pr5022-final-20261119-objcmp.log. Marker: exec/results/pr5022-final-20261119/objcmp.done.
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
NAME=pr5022-final-20261119
RES=$EXEC/results/$NAME
OC=$RES/objcmp
LOG=$EXEC/logs/$NAME-objcmp.log
WT=/var/tmp/jhan/b35-pr5022-final
TU=src/tron/kernels/amx_attn.cpp
TAGS='5061623a34 4c4b7b8864 final'
PIN="nice -n10 taskset -c 96-143"
mkdir -p "$OC" "$EXEC/logs"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
mark() { echo "$1" >"$RES/objcmp.done"; echo "=== objcmp finished $(ts): $1 ==="; }
fail() { mark "failed: $*"; exit 1; }
[ "$(hostname)" = delphi-3b35 ] || { echo "this script runs on delphi-3b35 only"; exit 1; }
rm -f "$RES/objcmp.done"
echo "=== objcmp started $(ts) pid $$ on $(hostname) ==="
[ "$(cat "$RES/build-final.done" 2>/dev/null)" = ok ] || fail "build-final.done is not ok"
for t in $TAGS; do [ -f "$OC/src-$t/$TU" ] && [ -d "$OC/src-$t/h" ] || fail "export missing: $OC/src-$t"; done

# The recorded command, as a list of arguments, with the tron tree's own paths made relative.
python3 - "$WT" "$TU" >"$OC/flags.txt" <<'EOF' || fail "cannot read the compile command"
import json, shlex, sys
wt, tu = sys.argv[1:3]
entry = next(e for e in json.load(open(f'{wt}/gen/compile_commands.json')) if e['file'] == f'{wt}/{tu}')
args, out, skip = shlex.split(entry['command']), [], 0
for i, a in enumerate(args[1:]):
    if skip: skip -= 1; continue
    if a in ('-o', '-c'): skip = 1; continue                 # output and input are given by the script
    if a.startswith('-fmacro-prefix-map='): continue          # paths are relative already
    if a == f'-I{wt}/h': a = '-Ih'                            # the tree's own headers
    out.append(a)
print('\n'.join(out))
EOF
mapfile -t FLAGS <"$OC/flags.txt"
{
  echo "host: $(hostname)   date: $(ts)"
  echo "compiler: $(clang++-19 --version | head -1)"
  echo "flags: ${FLAGS[*]}"
  echo "source of the flags: $WT/gen/compile_commands.json, entry for $TU"
} >"$OC/build-info.txt"
for t in $TAGS; do
  O=$OC/out-$t; mkdir -p "$O"
  ( cd "$OC/src-$t" && $PIN clang++-19 "${FLAGS[@]}" -c $TU -o "$O/amx_attn.o" 2>"$O/compile.err" ) || fail "compile failed for $t: $(head -3 "$O/compile.err")"
  $PIN llvm-objdump-19 -d -r --no-show-raw-insn --no-leading-addr "$O/amx_attn.o" >"$O/amx_attn.dis"
  $PIN llvm-nm-19 -S --defined-only "$O/amx_attn.o" >"$O/amx_attn.nm"
  echo "$t: object $(stat -c %s "$O/amx_attn.o") bytes, warnings $(grep -c 'warning:' "$O/compile.err"), text symbols $(grep -c ' [TtWw] ' "$O/amx_attn.nm"), sha256 of $TU $(sha256sum "$OC/src-$t/$TU" | cut -c1-16)"
done | tee -a "$OC/build-info.txt"
# The object the final build itself produced.
B=$OC/out-built; mkdir -p "$B"
BUILT=$WT/gen/src/tron/CMakeFiles/tron.dir/kernels/amx_attn.cpp.o
[ -f "$BUILT" ] || fail "no $BUILT"
cp -p "$BUILT" "$B/amx_attn.o"
$PIN llvm-objdump-19 -d -r --no-show-raw-insn --no-leading-addr "$B/amx_attn.o" >"$B/amx_attn.dis"
$PIN llvm-nm-19 -S --defined-only "$B/amx_attn.o" >"$B/amx_attn.nm"
echo "built: object $(stat -c %s "$B/amx_attn.o") bytes (from $BUILT), text symbols $(grep -c ' [TtWw] ' "$B/amx_attn.nm")" | tee -a "$OC/build-info.txt"
# The kernel functions inside the linked runtron: every text symbol of the built object, by its mangled name.
L=$OC/out-linked; mkdir -p "$L"
awk '$3 ~ /^[TtWw]$/ {print $4}' "$B/amx_attn.nm" | sort -u >"$L/symbols.txt"
$PIN llvm-objdump-19 -d --no-show-raw-insn --no-leading-addr --disassemble-symbols="$(paste -sd, "$L/symbols.txt")" "$WT/gen/runtron" >"$L/amx_attn.dis" 2>"$L/objdump.err"
echo "linked: $(grep -c '^<.*>:$' "$L/amx_attn.dis") of $(wc -l <"$L/symbols.txt") symbols found in gen/runtron (sha256 $(sha256sum "$WT/gen/runtron" | cut -c1-16))" | tee -a "$OC/build-info.txt"
python3 "$EXEC/$NAME/objcmp-compare.py" "$OC" || fail "compare script failed"
cat "$OC/objcmp.txt"
mark ok
