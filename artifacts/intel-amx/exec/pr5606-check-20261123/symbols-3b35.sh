#!/usr/bin/env bash
# pr5606-check-20261123 symbol check for the one-definition rule. Runs ON delphi-3b35. Builds nothing in place.
# The one-definition rule of C++: every copy of an inline function or template instance in one program must
# come from the same source text. In the option-OFF tree at S2 the test's own object file is compiled with
# -DTRON_AMX_DISPATCH and everything it links is compiled without.
#
# What it does in the tree of OPT (default off), which must be at STATE (default S2):
#   1. saves the link line of gen/t_amx_dispatch_dtype (`ninja -C gen -t commands t_amx_dispatch_dtype | tail -1`),
#   2. runs the same link command a second time with two changes: the output goes to
#      gen/keep/t_amx_dispatch_dtype.maplink and lld (the linker) writes its map to gen/keep/ (-Wl,-Map=).
#      The map names the object file that each symbol of the binary comes from. The script checks that the
#      second binary has the sha256 of gen/t_amx_dispatch_dtype,
#   3. runs symbols.py (see its header) on the object files and static libraries of the link line.
# Usage (on 3b35): [OPT=off STATE=S2] bash symbols-3b35.sh
# Record: exec/results/pr5606-check-20261123/symbols-<opt>-<state>.txt and symbols-<opt>-<state>/.
set -u
OPT=${OPT:-off}
STATE=${STATE:-S2}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
WT=$(wt_of "$OPT") || exit 1
SHA=$(sha_of "$STATE") || exit 1
TAG=$OPT-$STATE
OUT=$RES/symbols-$TAG.txt
DIR=$RES/symbols-$TAG
mkdir -p "$DIR"
{
  echo "# symbol check of $WT/gen/t_amx_dispatch_dtype on $(hostname), $(ts); state $STATE = commit $SHA"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || { echo "the tree is at $(git -C "$WT" rev-parse HEAD), not at $SHA"; exit 1; }
  [ -z "$(dirty_of "$WT")" ] || { echo "the tree has changes"; exit 1; }
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt"); tools: $(nm --version | head -1); $(ld.lld-19 --version 2>/dev/null | head -1)"
  cd "$WT" >/dev/null 2>&1 || exit 1
  $PIN ninja -C gen -t commands t_amx_dispatch_dtype | tail -1 >"$DIR/link-line.txt"
  n=$(grep -o -- ' -o t_amx_dispatch_dtype ' "$DIR/link-line.txt" | wc -l)
  [ "$n" = 1 ] || { echo "the link line holds ' -o t_amx_dispatch_dtype ' $n times, wanted 1"; exit 1; }
  sed 's| -o t_amx_dispatch_dtype | -o keep/t_amx_dispatch_dtype.maplink -Wl,-Map=keep/t_amx_dispatch_dtype.map |' "$DIR/link-line.txt" >"$DIR/link-line-with-map.txt"
  ( cd gen >/dev/null 2>&1 && $PIN sh -c "$(cat "$DIR/link-line-with-map.txt")" ) >"$DIR/relink.log" 2>&1
  echo "second link with -Wl,-Map: exit $?"
  A=$(sha256sum gen/t_amx_dispatch_dtype | cut -c1-64); B=$(sha256sum gen/keep/t_amx_dispatch_dtype.maplink | cut -c1-64)
  echo "sha256 of gen/t_amx_dispatch_dtype: $A"
  echo "sha256 of the second link:          $B ($([ "$A" = "$B" ] && echo "same binary, so the map describes gen/t_amx_dispatch_dtype" || echo "DIFFERENT binary"))"
  cp gen/keep/t_amx_dispatch_dtype.map "$DIR/linker-map.txt"
  echo "linker map: $(wc -l <"$DIR/linker-map.txt") lines, saved as $DIR/linker-map.txt"
  echo
  $PIN python3 "$HERE/symbols.py" "$WT/gen" "$DIR/link-line.txt" "$DIR/linker-map.txt" "$WT/gen/t_amx_dispatch_dtype" "$DIR"
  echo
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
