#!/usr/bin/env bash
# pr5606-check-20261123: compare the dispatch test of the option-OFF tree with the one of the option-ON tree.
# Runs ON delphi-3b35. Read-only for both trees. Both trees must be at S2 and built.
#
# Why: in the ON tree the library tron is compiled with -DTRON_AMX_DISPATCH, like the test's own object. In the
# OFF tree only the test's own object is. If the two test binaries hold the same instructions, the missing
# define in the libraries changes nothing that this test executes.
# Part 1: the test's own object file of both trees (objdump -dr: instructions and relocation targets).
# Part 2: the linked binary gen/t_amx_dispatch_dtype of both trees: the instruction listing with addresses masked
#         (bincmp.py), and the loaded sections byte by byte (secthash.py).
# Part 3: the symbol sizes of both trees (symbols-compare.py; symbols-3b35.sh must have run for both trees).
# Part 4: the output of the plain test runs of both trees (tests-3b35.sh must have run for both trees).
# Usage (on 3b35): bash bincmp-3b35.sh        Record: exec/results/pr5606-check-20261123/bincmp-off-on-S2.txt
set -u
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
A=$(wt_of off); B=$(wt_of on)
OBJ=gen/t/CMakeFiles/t_amx_dispatch_dtype.dir/t_amx_dispatch_dtype.cpp.o
OUT=$RES/bincmp-off-on-S2.txt
T=$RES/tests
mkdir -p "$T"
{
  echo "# compare of t_amx_dispatch_dtype, option-OFF tree against option-ON tree, on $(hostname), $(ts)"
  for w in "$A" "$B"; do
    echo "# $w: HEAD $(git -C "$w" rev-parse HEAD), $(grep -E '^TRON_AMX_DISPATCH:' "$w/gen/CMakeCache.txt"), changes outside gen: $(dirty_of "$w" | wc -l) lines"
    [ "$(git -C "$w" rev-parse HEAD)" = "$S2" ] || { echo "$w is not at S2"; exit 1; }
  done
  echo
  echo "== part 1: the test's own object file ($OBJ)"
  for w in "$A" "$B"; do
    echo "  $w: $(stat -c %s "$w/$OBJ") bytes, sha256 of the file $(sha256sum "$w/$OBJ" | cut -c1-16), sha256 of 'objdump -dr --no-show-raw-insn' without the file-name line $($PIN objdump -dr --no-show-raw-insn "$w/$OBJ" | grep -v 'file format' | sha256sum | cut -c1-16)"
  done
  echo
  echo "== part 2: the linked binary gen/t_amx_dispatch_dtype"
  $PIN objdump -d --no-show-raw-insn "$A/gen/t_amx_dispatch_dtype" >"$T/bincmp-off.dis.tmp"
  $PIN objdump -d --no-show-raw-insn "$B/gen/t_amx_dispatch_dtype" >"$T/bincmp-on.dis.tmp"
  echo "  A = OFF tree, sha256 of the binary $(sha256sum "$A/gen/t_amx_dispatch_dtype" | cut -c1-16), $(stat -c %s "$A/gen/t_amx_dispatch_dtype") bytes"
  echo "  B = ON tree,  sha256 of the binary $(sha256sum "$B/gen/t_amx_dispatch_dtype" | cut -c1-16), $(stat -c %s "$B/gen/t_amx_dispatch_dtype") bytes"
  $PIN python3 "$HERE/bincmp.py" "$T/bincmp-off.dis.tmp" "$T/bincmp-on.dis.tmp" | sed 's/^/  /'
  rm -f "$T/bincmp-off.dis.tmp" "$T/bincmp-on.dis.tmp"
  echo "  loaded sections, byte by byte (secthash.py):"
  $PIN python3 "$HERE/secthash.py" "$A/gen/t_amx_dispatch_dtype" "$B/gen/t_amx_dispatch_dtype" | cut -c1-260 | sed 's/^/    /'
  echo "  section sizes (size -A), rows that differ between the two binaries:"
  diff <(size -A "$A/gen/t_amx_dispatch_dtype" | awk 'NR>2{print $1, $2}') <(size -A "$B/gen/t_amx_dispatch_dtype" | awk 'NR>2{print $1, $2}') | grep '^[<>]' | sed 's/^/    /' | head -20
  echo "  (end of the section rows)"
  echo
  echo "== part 3: symbol sizes"
  if [ -e "$RES/symbols-off-S2/defs.tsv" ] && [ -e "$RES/symbols-on-S2/defs.tsv" ]; then
    python3 "$HERE/symbols-compare.py" "$RES/symbols-off-S2/defs.tsv" "$RES/symbols-on-S2/defs.tsv" | sed 's/^/  /'
  else
    echo "  defs.tsv of one tree is missing: run symbols-3b35.sh for OPT=off and OPT=on first"
  fi
  echo
  echo "== part 4: the output of the plain test runs (tests/off-S2-dispatch.log against tests/on-S2-dispatch.log)"
  # masked: the time stamp of each line, the tree name, cycle counters, the clock frequency, the random seed, durations
  norm() { sed -E 's/^\[[0-9-]+ [0-9:.]+\] //; s/b35-pr5606-(off|on)/b35-pr5606-X/g; s/"([a-z_]*cycles[a-z_]*|tsc_hz)":[0-9]+/"\1":N/g; s/Randomness seeded to: [0-9]+/Randomness seeded to: N/; s/TSC frequency stable at [0-9]+/TSC frequency stable at N/; s/offset:[0-9]+,-?[0-9]+/offset:N/g; s/^[0-9.]+ s: /T s: /' "$1"; }
  echo "  lines: OFF tree $(wc -l <"$T/off-S2-dispatch.log"), ON tree $(wc -l <"$T/on-S2-dispatch.log"); lines that differ after masking: $(diff <(norm "$T/off-S2-dispatch.log") <(norm "$T/on-S2-dispatch.log") | grep -c '^[<>]')"
  diff <(norm "$T/off-S2-dispatch.log") <(norm "$T/on-S2-dispatch.log") | grep '^[<>]' | head -6 | cut -c1-200 | sed 's/^/    /'
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
