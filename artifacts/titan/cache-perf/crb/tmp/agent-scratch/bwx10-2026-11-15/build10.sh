#!/usr/bin/env bash
# build10.sh - on CRB: build bwx10, run its self-test, print the digests, and
# save the machine code of every kernel (design tackle-8mb.md, "Fixed setup":
# a build whose listing differs from the accepted one is rejected).
# It is build8.sh for bwx10.c, with three additions: the branch-target check
# covers timed_sequence_hot() too, the machine code of both timed functions is
# saved in seq-listing.txt, and build.txt holds the placement of the timed
# path in bwx10 and in the accepted bwx8.
# Usage: build10.sh
# The compiler flags are the flags of build8.sh. There is no EXTRA.
# Output, all in the folder of this script (on CRB: ~/cache-perf/bwx10-20261115/):
#   bwx10                the binary
#   build.txt            host, load, compiler, flags, compiler messages, sha256
#   selftest-bwx10.txt   output of "bwx10 --selftest"
#   listing.txt          "=== bwx10 <kernel> ===" and the objdump text of function k_<kernel>
#   offsets.tsv          binary, kernel, function, start, loop_start, loop_mod64 (addresses in hex)
#   seq-listing.txt      the objdump text of timed_sequence and timed_sequence_hot (for reading; no script uses it)
# Then, on the development machine: check_listing10.py listing.txt offsets.tsv
# Exit status: 0 done; 3 marker file present; 4 the self-test failed; 5 the build failed;
#   6 a timed sequence of the trial mode reaches a function that is not allowed there.
# Writes only in its own folder. No sudo. Runs on CPUs 0-119 only (BWX_CPUS changes the list).
# It reads one file outside its folder, if it exists: the accepted binary of bwx8
# (BWX8_BIN, default ../bwx8-20261114/bwx8), with nm only. It does not run it.
set -euo pipefail
MARKER=${BWX_MARKER:-/tmp/positron-perf.RUNNING}   # BWX_MARKER: only for a test of this check
check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }
check_marker
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c "${BWX_CPUS:-0-119}" "$0" "$@"; fi
SRC=$(cd "$(dirname "$0")" && pwd)
CC=${CC:-gcc}
CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4"
b=bwx10
B="$SRC/build.txt"
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who | wc -l)"
  echo "## cc=$($CC --version | head -1)"
  echo "## CFLAGS=$CFLAGS"
  echo "## compiler messages:"
} > "$B"
# shellcheck disable=SC2086
$CC $CFLAGS -o "$SRC/$b" "$SRC/bwx10.c" >> "$B" 2>&1 || { echo "build of $b failed: $B" >&2; cat "$B" >&2; exit 5; }
echo "## compiler messages end" >> "$B"

check_marker
if "$SRC/$b" --selftest > "$SRC/selftest-$b.txt" 2>&1; then
  echo "## selftest $b exit=0 $(tail -1 "$SRC/selftest-$b.txt")" >> "$B"
else
  echo "## selftest $b exit=$?" >> "$B"; echo "selftest of $b failed: $SRC/selftest-$b.txt" >&2; tail -3 "$SRC/selftest-$b.txt" >&2; exit 4
fi

# Machine code of every kernel. The loop start is the target of the first
# branch of the function that goes backward to an address inside it.
: > "$SRC/listing.txt"
printf 'binary\tkernel\tfunction\tstart\tloop_start\tloop_mod64\n' > "$SRC/offsets.tsv"
check_marker   # the next line runs the binary again
for k in $("$SRC/$b" --list); do
  fn=k_$k
  text=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b" | sed -n '/>:$/,/^$/p')
  { echo "=== $b $k ==="; echo "$text"; echo; } >> "$SRC/listing.txt"
  start=$(sed -n '1s/^0*\([0-9a-f]\+\) .*/\1/p' <<< "$text"); loop=NA; mod=NA
  while read -r addr rest; do
    addr=${addr%:}
    if [[ $rest =~ ([0-9a-f]+)\ \<$fn(\+0x[0-9a-f]+)?\> ]]; then
      tgt=${BASH_REMATCH[1]}
      if (( 16#$tgt < 16#$addr && 16#$tgt >= 16#$start )); then loop=$tgt; mod=$(( 16#$tgt % 64 )); break; fi
    fi
  done < <(tail -n +2 <<< "$text" | grep -E '^ *[0-9a-f]+:')
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$b" "$k" "$fn" "$start" "$loop" "$mod" >> "$SRC/offsets.tsv"
done

# Branch targets of timed_sequence() and of timed_sequence_hot() that lie
# outside the function (design, Stage 1 item 4: no warm-up, page read, output
# or barrier can enter the timed path). Allowed: clock_gettime, the kernels
# (an indirect call), tcount (the counter read of count "read") and the
# stack-guard failure. A helper that is not inlined shows as its own name and
# is rejected. Both functions are listed before the script decides.
: > "$SRC/seq-listing.txt"
seq_fail=0
for fn in timed_sequence timed_sequence_hot; do
  code=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b")
  { echo "=== $b $fn ==="; sed -n '/>:$/,/^$/p' <<< "$code"; echo; } >> "$SRC/seq-listing.txt"
  seq_calls=$(awk -v self="$fn" '
    $1 !~ /^[0-9a-f]+:$/ { next }
    /[ \t](call|jmp)q?[ \t]+\*/ || $2 == "blr" || $2 == "br" { print "(indirect)"; next }
    $2 ~ /^(callq?|jmpq?|j[a-z]+|bl|b|b\.[a-z]+|cbn?z|tbn?z)$/ && $NF ~ /^<.*>$/ {
      t = $NF; gsub(/^<|>$|\+0x[0-9a-f]+>$|@plt/, "", t); if (t != self) print t }' <<< "$code" | LC_ALL=C sort | uniq -c | awk '{ printf "%s%s=%s", (NR > 1 ? " " : ""), $2, $1 }')
  echo "## $fn branch targets: ${seq_calls:-none}" >> "$B"
  seq_bad=$(tr ' ' '\n' <<< "$seq_calls" | sed 's/=[0-9]*$//' | grep -vxE 'clock_gettime|\(indirect\)|tcount|__stack_chk_fail' || true)
  if [[ -n $seq_bad || $seq_calls != *"clock_gettime="* || $seq_calls != *"(indirect)="* ]]; then
    echo "$fn of $b: branch targets '${seq_calls:-none}'; not allowed or missing: ${seq_bad:-clock_gettime or the kernel call}" >&2; seq_fail=1
  fi
done
if (( seq_fail )); then exit 6; fi

# Placement of the timed path: the start modulo 64 of call(), read_smaps(),
# tcount() and the two timed functions (a function that gcc inlined everywhere
# has no symbol and is left out). bwx10.c pads after its new kernels so that
# the functions from call() to timed_sequence() start where they start in
# bwx8, modulo 64. This is a record, not a gate: a difference does not stop
# the build.
placement() {
  local out
  out=$(nm "$1" 2>/dev/null | awk '$3 ~ /^(call|read_smaps|tcount|timed_sequence|timed_sequence_hot)$/ { print $3, $1 }' | LC_ALL=C sort |
    while read -r name addr; do printf '%s=%d ' "$name" $(( 16#$addr % 64 )); done)
  echo "${out% }"
}
BWX8_BIN=${BWX8_BIN:-$SRC/../bwx8-20261114/bwx8}
p10=$(placement "$SRC/$b")
echo "## placement $b (start modulo 64): ${p10:-none}" >> "$B"
if [[ -f $BWX8_BIN ]]; then
  p8=$(placement "$BWX8_BIN")
  echo "## placement bwx8 (start modulo 64): ${p8:-none}" >> "$B"
  # timed_sequence_hot exists in bwx10 only; it sorts last
  if [[ -n $p8 && $(sed 's/ timed_sequence_hot=[0-9]*$//' <<< "$p10") == "$p8" ]]; then
    echo "## placement up to timed_sequence against bwx8: same" >> "$B"
  else
    echo "## placement up to timed_sequence against bwx8: DIFFERS" >> "$B"
  fi
else
  echo "## placement against bwx8: not compared (no file $BWX8_BIN)" >> "$B"
fi

{
  echo "## sha256:"
  (cd "$SRC" && sha256sum bwx10.c bwx10_selftest.c build10.sh $b listing.txt offsets.tsv seq-listing.txt)
  echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)"
} >> "$B"
cat "$B"
echo "## offsets.tsv:"
cat "$SRC/offsets.tsv"
