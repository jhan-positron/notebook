#!/usr/bin/env bash
# build.sh - on CRB: build bwx and the three builds of step B3, run the
# self-test of each, print the digests, and save the machine code of every
# kernel (handoff.md, B.7 "Acceptance test").
# Usage: build.sh            (optional environment: EXTRA="-DHEAD_copy=8 -DPAD_read=16 ...")
#   EXTRA goes to all four builds. EXTRA_<binary> goes to one build only, after EXTRA, for example
#   EXTRA_bwx_o0="-DPAD_copy=60". Use it for a PAD of copy, asmcopy or asmcopy2: -DPAD_copy=N in EXTRA
#   would replace the pad of every build, also the B3_OFFSET pads of bwx_o0, bwx_o36 and bwx_o52.
# Output, all in the folder of this script:
#   bwx                      copy loop at 36, asmcopy loop at 52 modulo 64 (as planned in bwx.c)
#   bwx_o0 bwx_o36 bwx_o52   -DB3_OFFSET=0|36|52: the loops of copy, asmcopy, asmcopy2 at that offset
#   build.txt                host, load, compiler, flags, compiler messages, sha256
#   selftest-<binary>.txt    output of "<binary> --selftest"
#   listing.txt              "=== <binary> <kernel> ===" and the objdump text of function k_<kernel>
#   offsets.tsv              binary, kernel, function, start, loop_start, loop_mod64 (addresses in hex)
# Then, on the development machine: check_listing.py listing.txt
# Exit status: 0 done; 3 marker file present; 4 a self-test failed; 5 a build failed.
# Writes only in its own folder. No sudo. Runs on CPUs 0-119 only (BWX_CPUS changes the list).
set -euo pipefail
MARKER=${BWX_MARKER:-/tmp/positron-perf.RUNNING}   # BWX_MARKER: only for a test of this check
check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }
check_marker
if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c "${BWX_CPUS:-0-119}" "$0" "$@"; fi
SRC=$(cd "$(dirname "$0")" && pwd)
CC=${CC:-gcc}
CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4"
EXTRA=${EXTRA:-}
BINS="bwx bwx_o0 bwx_o36 bwx_o52"
B="$SRC/build.txt"
{
  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who | wc -l)"
  echo "## cc=$($CC --version | head -1)"
  echo "## CFLAGS=$CFLAGS"
  echo "## EXTRA=$EXTRA"
  for b in $BINS; do v=EXTRA_$b; echo "## $v=${!v:-}"; done
  echo "## compiler messages:"
} > "$B"
for b in $BINS; do
  def=""; [[ $b == bwx_o* ]] && def="-DB3_OFFSET=${b#bwx_o}"
  # shellcheck disable=SC2086
  one=EXTRA_$b
  $CC $CFLAGS $def $EXTRA ${!one:-} -o "$SRC/$b" "$SRC/bwx.c" >> "$B" 2>&1 || { echo "build of $b failed: $B" >&2; cat "$B" >&2; exit 5; }
done
echo "## compiler messages end" >> "$B"

for b in $BINS; do
  check_marker
  if "$SRC/$b" --selftest > "$SRC/selftest-$b.txt" 2>&1; then
    echo "## selftest $b exit=0 $(tail -1 "$SRC/selftest-$b.txt")" >> "$B"
  else
    echo "## selftest $b exit=$?" >> "$B"; echo "selftest of $b failed: $SRC/selftest-$b.txt" >&2; tail -3 "$SRC/selftest-$b.txt" >&2; exit 4
  fi
done

# Machine code of every kernel. The loop start is the target of the first
# branch of the function that goes backward to an address inside it.
: > "$SRC/listing.txt"
printf 'binary\tkernel\tfunction\tstart\tloop_start\tloop_mod64\n' > "$SRC/offsets.tsv"
for b in $BINS; do
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
done
{
  echo "## sha256:"
  (cd "$SRC" && sha256sum bwx.c bwx_selftest.c build.sh $BINS listing.txt offsets.tsv)
  echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)"
} >> "$B"
cat "$B"
echo "## offsets.tsv:"
cat "$SRC/offsets.tsv"
