#!/usr/bin/env bash
# pr5606-check-20261123: record which compile commands carry -DTRON_AMX_DISPATCH. Runs ON delphi-3b35. Read-only.
# It reads gen/compile_commands.json of the build tree (see compile-commands.py), asks ninja (the build tool)
# whether the AMX kernel file is a build input, and looks for an object file of the kernel in gen.
# Usage (on 3b35): OPT=off|on STATE=S0|S1|S2 bash compile-commands-3b35.sh
# Record: exec/results/pr5606-check-20261123/compile-commands-<opt>-<state>.txt
set -u
OPT=${OPT:?OPT=off|on is required}
STATE=${STATE:?STATE=S0|S1|S2 is required}
. /home/jhan/workspace/intel-AMX/exec/pr5606-check-20261123/common.sh
only_3b35
WT=$(wt_of "$OPT") || exit 1
SHA=$(sha_of "$STATE") || exit 1
OUT=$RES/compile-commands-$OPT-$STATE.txt
{
  echo "# compile commands of $WT on $(hostname), $(ts); state $STATE = commit $SHA"
  [ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || echo "WARNING: the tree is at $(git -C "$WT" rev-parse HEAD), not at $SHA"
  echo "# option: $(grep -E '^TRON_AMX_DISPATCH:' "$WT/gen/CMakeCache.txt"); compile_commands.json written $(date -u -r "$WT/gen/compile_commands.json" +%FT%TZ)"
  $PIN python3 "$HERE/compile-commands.py" "$WT"
  echo "ninja build statements that name amx_attn: $( ( cd "$WT" >/dev/null 2>&1 && $PIN ninja -C gen -t targets all 2>/dev/null ) | grep -c 'amx_attn' || true)"
  echo "object files of the kernel in gen (find gen -name '*amx_attn*.o'): $(find "$WT/gen" -name '*amx_attn*.o' | wc -l)"
  echo "members of gen/src/tron/libtron.a whose name contains amx_attn: $(ar t "$WT/gen/src/tron/libtron.a" 2>/dev/null | grep -c amx_attn || true)"
} >"$OUT" 2>&1
cat "$OUT"
