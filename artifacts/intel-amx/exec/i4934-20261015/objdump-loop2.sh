#!/usr/bin/env bash
# objdump-loop2.sh <runtron binary> <label>: like objdump-loop.sh, but only the apply_page_range instantiations of the
# qwen-3-4b plugin with the 32-head, 8-KV-head, 128-dimension geometry (the issue's cells). Per instantiation it prints
# the size, the number of vpdpbf16ps (the VDPBF16PS instruction of qk_group and the dotter), of 512-bit zmm loads and
# stores, of vpbroadcastd (qk_group's query-pair broadcast) and of vextract/vshuf (the dotter's horizontal reduce).
# It also locates the live-mask loop: the basic block that holds a `shl`/`or` on the live mask and ends in a backward
# jump, printed with its instruction count. Read-only. Runs on delphi-3bda.
# Usage: bash objdump-loop2.sh /var/tmp/jhan/tron-i4934/gen/runtron fix
set -u
BIN=${1:?runtron binary}; LABEL=${2:?label}
OUT=/home/jhan/workspace/intel-AMX/exec/results/i4934-20261015/objdump2/$LABEL
mkdir -p "$OUT"
nm -C --defined-only -S "$BIN" 2>/dev/null | grep -E ' [tTwW] .*apply_page_range<' | grep 'qwen_3_4b' | grep -F 'attention_geometry{32ul, tron::kv_geometry{8ul, 128ul}' > "$OUT/symbols-full.txt"
awk '{print $1, $2}' "$OUT/symbols-full.txt" > "$OUT/symbols.txt"
sed 's/^[0-9a-f]* [0-9a-f]* [tTwW] //' "$OUT/symbols-full.txt" > "$OUT/symbol-names.txt"
n=$(wc -l < "$OUT/symbols.txt"); echo "$n qwen-3-4b apply_page_range<32/8/128> instantiations in $BIN"
i=0
while read -r addr size; do
  i=$((i + 1))
  start=$((16#$addr)); stop=$((start + 16#$size))
  f="$OUT/inst-$i.s"
  objdump -d --no-show-raw-insn -C --start-address=$start --stop-address=$stop "$BIN" > "$f" 2>/dev/null
  dp=$(grep -c 'vpdpbf16ps' "$f"); ld=$(grep -cE 'vmovdq[au](64|32) .*,%zmm' "$f"); st=$(grep -cE 'vmovdq[au](64|32) %zmm' "$f")
  bc=$(grep -c 'vpbroadcastd' "$f"); red=$(grep -cE 'vextract|vshuf' "$f")
  name=$(sed -n "${i}p" "$OUT/symbol-names.txt" | grep -oE 'make_llm_executor<[^>]*>' | head -1 | cut -c1-90)
  echo "inst-$i size=$((16#$size)) insns=$(grep -cE '^ +[0-9a-f]+:' "$f") vpdpbf16ps=$dp zmm_loads=$ld zmm_stores=$st vpbroadcastd=$bc reduce=$red  $name"
done < "$OUT/symbols.txt"
echo "dumps in $OUT"
