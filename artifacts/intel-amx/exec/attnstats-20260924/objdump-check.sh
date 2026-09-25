#!/usr/bin/env bash
# objdump-check.sh (runs ON delphi-3bda, light: reads two binaries): compare the apply_page_range
# instantiations of the base runtron (main 66c7bb8db1) and the head runtron (branch): symbol sizes,
# instruction counts and lock-prefixed instructions (an atomic read-modify-write on x86). The off-state
# contract of the attention path stats says the hooks add no atomic and no memory traffic per visit.
# Output: $RES/objdump-check.txt. Usage: bash objdump-check.sh [BASE_BIN HEAD_BIN]
set -u
RES=/home/jhan/workspace/intel-AMX/exec/results/attnstats-20260924
BASE=${1:-/var/tmp/jhan/tron-attn-base/gen/runtron.attnbase}
HEAD=${2:-/var/tmp/jhan/tron-attn-head/gen/runtron.attnhead}
OUT=$RES/objdump-check.txt
PIN="taskset -c 72-75 nice -n 15"
{
  echo "# objdump check $(date -u +%FT%TZ): base=$BASE head=$HEAD"
  for bin in "$BASE" "$HEAD"; do
    echo "## $bin"
    echo "### apply_page_range instantiations: count and total bytes (nm -S, demangled names filtered)"
    $PIN nm -C -S --defined-only "$bin" 2>/dev/null | grep -F 'apply_page_range<' | awk '{n++; s+=strtonum("0x"$2)} END {printf "instantiations=%d total_bytes=%d\n", n, s}'
    echo "### the five largest instantiations: bytes, instructions, lock-prefixed instructions, rdtsc, xadd"
    $PIN nm -C -S --defined-only "$bin" 2>/dev/null | grep -F 'apply_page_range<' | awk '{name=$4; for (i=5;i<=NF;i++) name=name" "$i; print $1, $2, name}' | sort -k2,2r | head -5 | while read -r addr size name; do
      start=$((16#$addr)); stop=$((start + 16#$size))
      dis=$($PIN objdump -d --no-show-raw-insn --start-address=$start --stop-address=$stop "$bin" 2>/dev/null)
      insns=$(grep -cE '^\s*[0-9a-f]+:\s' <<<"$dis")
      locks=$(grep -cE '^\s*[0-9a-f]+:\s+lock ' <<<"$dis")
      rdtsc=$(grep -cE '\brdtsc\b' <<<"$dis")
      xadd=$(grep -cE '\bxadd\b' <<<"$dis")
      printf "%8d bytes  %7d insns  %3d lock  %3d rdtsc  %3d xadd  %s\n" "$((16#$size))" "$insns" "$locks" "$rdtsc" "$xadd" "${name:0:150}"
    done
    echo "### run_attention_job instantiations: bytes, rdtsc count (T3/T4 add one rdtsc per job only when on)"
    $PIN nm -C -S --defined-only "$bin" 2>/dev/null | grep -F 'run_attention_job<' | awk '{name=$4; for (i=5;i<=NF;i++) name=name" "$i; print $1, $2, name}' | sort -k2,2r | head -3 | while read -r addr size name; do
      start=$((16#$addr)); stop=$((start + 16#$size))
      dis=$($PIN objdump -d --no-show-raw-insn --start-address=$start --stop-address=$stop "$bin" 2>/dev/null)
      printf "%8d bytes  %7d insns  %3d rdtsc  %s\n" "$((16#$size))" "$(grep -cE '^\s*[0-9a-f]+:\s' <<<"$dis")" "$(grep -cE '\brdtsc\b' <<<"$dis")" "${name:0:150}"
    done
  done
  echo "# done $(date -u +%FT%TZ)"
} >"$OUT" 2>&1
cat "$OUT"
