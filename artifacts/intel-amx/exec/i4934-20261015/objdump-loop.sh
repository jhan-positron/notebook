#!/usr/bin/env bash
# objdump-loop.sh <runtron binary> <label>: dump the disassembly of every apply_page_range instantiation of a build-tree
# runtron (RelWithDebInfo keeps the symbols) into $OUT/<label>/ and print per instantiation: size, the number of
# vpdpbf16ps (the VDPBF16PS instruction of qk_group and the dotter), of 512-bit loads (vmovdqa64/vmovdqu64 zmm) and of
# vpdpbf16ps-free basic blocks that end in a backward jump (loop candidates). Read-only. Runs on delphi-3bda.
# Usage: bash objdump-loop.sh /var/tmp/jhan/tron-i4934/gen/runtron fix
set -u
BIN=${1:?runtron binary}; LABEL=${2:?label}
OUT=/home/jhan/workspace/intel-AMX/exec/results/i4934-20261015/objdump/$LABEL
mkdir -p "$OUT"
# The symbols: apply_page_range<geometry, ...> instantiations (demangled names carry the geometry values).
nm -C --defined-only -S "$BIN" 2>/dev/null | grep -E ' [tTwW] .*apply_page_range<' | awk '{print $1, $2, $3}' > "$OUT/symbols.txt"
nm -C --defined-only -S "$BIN" 2>/dev/null | grep -E ' [tTwW] .*apply_page_range<' | sed 's/^[0-9a-f]* [0-9a-f]* [tTwW] //' > "$OUT/symbol-names.txt"
n=$(wc -l < "$OUT/symbols.txt"); echo "$n apply_page_range instantiations in $BIN"
i=0
while read -r addr size kind; do
  i=$((i + 1))
  start=$((16#$addr)); stop=$((start + 16#$size))
  f="$OUT/inst-$i.s"
  objdump -d --no-show-raw-insn -C --start-address=$start --stop-address=$stop "$BIN" > "$f" 2>/dev/null
  dp=$(grep -c 'vpdpbf16ps' "$f"); ld=$(grep -cE 'vmovdq[au]64 .*,%zmm' "$f"); st=$(grep -cE 'vmovdq[au]64 %zmm' "$f")
  name=$(sed -n "${i}p" "$OUT/symbol-names.txt" | cut -c1-140)
  echo "inst-$i size=$((16#$size)) vpdpbf16ps=$dp zmm_loads=$ld zmm_stores=$st  $name"
done < "$OUT/symbols.txt"
echo "dumps in $OUT"
