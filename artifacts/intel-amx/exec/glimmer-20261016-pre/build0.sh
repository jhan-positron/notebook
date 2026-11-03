#!/usr/bin/env bash
# glimmer-20261016 pre-build (runs ON delphi-3bda, detached, our half only, nice 10, -j20 as agreed with the td-20261016
# session): build runtron + the three AMX test binaries of branch jhan-amx-kvmul16 in a 3bda-local worktree of the shared
# repo. Same recipe as exec/td-20261016/build-variant.sh. Usage (on 3bda): SHA=<full sha> bash build0.sh
# Log: exec/logs/glimmer-20261016-build0.log   Marker: exec/results/glimmer-20261016/build0.done (ok|failed)
set -u
SHA=${SHA:?}
EXEC=/home/jhan/workspace/intel-AMX/exec
LOG=$EXEC/logs/glimmer-20261016-build0.log
RES=$EXEC/results/glimmer-20261016
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-g16
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
TARGETS="runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
mkdir -p "$RES"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
fail() { echo "$(ts) FAILED: $*"; echo failed >"$RES/build0.done"; exit 1; }
rm -f "$RES/build0.done"
echo "=== build0 started $(ts) on $(hostname) sha=$SHA ==="
if [ ! -d "$WT" ]; then
  git -C "$REPO" cat-file -e "$SHA^{commit}" || fail "$SHA not visible in $REPO"
  git -C "$REPO" worktree add --detach "$WT" "$SHA" || fail "worktree add"
fi
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || fail "$WT is not at $SHA"
# content check on the build host (NFS attribute-cache trap does not apply: local disk), but confirm the edit is present
grep -q "GROUP_HEADS_16" "$WT/h/tron/kernels/amx_attn_iface.hpp" || fail "GROUP_HEADS_16 missing in the worktree header"
[ -d "$WT/ingest/traces" ] || cp -r /var/tmp/jhan/tron-pr4/ingest/traces "$WT/ingest/" || fail "traces copy"
[ -d "$WT/ingest/traces/ingested-meta-models-Muse-Glimmer-30B" ] || fail "Glimmer trace missing"
cd "$WT" || fail cd
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c "cmake --preset native -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON 2>&1 | tail -3; echo configure rc=\${PIPESTATUS[0]}"
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c "cmake --build gen --target $TARGETS -j20 2>&1 | grep -E 'error|FAILED|warning: ' | head -40; echo \"build rc=\${PIPESTATUS[0]}\""
echo "$(ts) build wall=$(( $(date +%s) - t0 ))s"
ok=1
for t in $TARGETS; do [ -x "gen/$t" ] || { echo "$(ts) missing gen/$t"; ok=0; }; done
if [ $ok = 1 ]; then
  cp gen/runtron gen/runtron.g16 && sha256sum gen/runtron.g16
  echo "tdpbf16ps count: $(objdump -d gen/runtron.g16 | grep -c tdpbf16ps)"
  echo "TRON_ATTN_STATS strings: $(strings gen/runtron.g16 | grep -c TRON_ATTN_STATS)"
  echo "kernel instantiations:"; nm -C gen/runtron.g16 | grep -E 'amx_attn_h128g4::(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)<' | sed 's/^/  /'
  grep -E "^TRON_(AMX_DISPATCH|K_VNNI):" gen/CMakeCache.txt | tr '\n' ' '; echo
  echo ok >"$RES/build0.done"; echo "$(ts) ok"
else
  echo failed >"$RES/build0.done"
fi
echo "=== build0 finished $(ts) ==="
