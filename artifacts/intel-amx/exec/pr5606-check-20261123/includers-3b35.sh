#!/usr/bin/env bash
# pr5606-check-20261123: which linked objects were compiled from a source that includes the dispatch header?
# Runs ON delphi-3b35. Read-only. symbols-3b35.sh must have run for the same tree (it saves the linker map).
#
# Why: the define TRON_AMX_DISPATCH changes the text of h/tron/models/self_attention.hpp. The one-definition
# rule of C++ is only in question when two objects of ONE linked program were compiled from that header with
# and without the define. ninja (the build tool) records the headers each object was compiled from
# (`ninja -t deps`). The linker map names the objects that gave at least one section to the binary.
# Usage (on 3b35): [OPT=off STATE=S2] bash includers-3b35.sh
# Record: exec/results/pr5606-check-20261123/includers-<opt>-<state>.txt
set -u
OPT=${OPT:-off}
STATE=${STATE:-S2}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
WT=$(wt_of "$OPT") || exit 1
SHA=$(sha_of "$STATE") || exit 1
MAP=$RES/symbols-$OPT-$STATE/linker-map.txt
OUT=$RES/includers-$OPT-$STATE.txt
HDR=h/tron/models/self_attention.hpp
{
  echo "# objects compiled from $HDR in $WT on $(hostname), $(ts); state $STATE = commit $SHA"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || { echo "the tree is not at $SHA"; exit 1; }
  [ -e "$MAP" ] || { echo "no linker map $MAP: run symbols-3b35.sh first"; exit 1; }
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt")"
  LIST=$( ( cd "$WT" >/dev/null 2>&1 && $PIN ninja -C gen -t deps 2>/dev/null ) | awk -v h="$HDR" '/^[^ ].*: #deps/{obj=$1; sub(/:$/,"",obj)} index($0, h){print obj}' | sort -u)
  echo "objects with recorded dependencies in this tree: $( ( cd "$WT" >/dev/null 2>&1 && $PIN ninja -C gen -t deps 2>/dev/null ) | grep -c ': #deps')"
  echo "objects compiled from the header: $(echo "$LIST" | grep -c .)"
  n_linked=0
  for o in $LIST; do
    base=$(basename "$o")
    case $o in
      src/tron/CMakeFiles/tron.dir/*) label="src/tron/libtron.a($base)" ;;
      *) label=$o ;;
    esac
    n=$(grep -c -F "$label:(" "$MAP" || true)
    def=$(python3 - "$WT" "$o" <<'EOF'
import json, sys
tree, obj = sys.argv[1], sys.argv[2]
for e in json.load(open(tree + "/gen/compile_commands.json")):
    cmd = e.get("command") or " ".join(e.get("arguments", []))
    if (e.get("output") or "") == obj or (" -o " + obj + " ") in cmd:
        print(cmd.split().count("-DTRON_AMX_DISPATCH"))
        break
else:
    print("?")
EOF
)
    [ "$n" -gt 0 ] && n_linked=$((n_linked + 1))
    echo "  $o: compiled with the define $def time(s); sections it gives to gen/t_amx_dispatch_dtype: $n"
  done
  echo "objects compiled from the header that are part of gen/t_amx_dispatch_dtype: $n_linked"
  echo "# finished $(ts)"
} >"$OUT" 2>&1
cat "$OUT"
