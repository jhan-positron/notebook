#!/usr/bin/env bash
# glimmer-20261016 build1 (runs ON delphi-3bda, detached): wait for build0 to finish, move /var/tmp/jhan/tron-g16 to the
# amended head SHA and rebuild the same targets incrementally (our half, nice 10, -j20). Usage: SHA=<full sha> bash build1.sh
# Log: exec/logs/glimmer-20261016-build1.log   Marker: exec/results/glimmer-20261016/build.done (ok|failed) = the final build.
set -u
SHA=${SHA:?}
EXEC=/home/jhan/workspace/intel-AMX/exec
LOG=$EXEC/logs/glimmer-20261016-build1.log
RES=$EXEC/results/glimmer-20261016
REPO=/home/jhan/workspace/tron
WT=/var/tmp/jhan/tron-g16
OUR_CPUS=72-143,216-287
NIX=/home/jhan/.nix-profile/bin/nix
TARGETS="runtron t_amx_numerics t_amx_dispatch_dtype t_llama_unit"
mkdir -p "$RES"
exec >>"$LOG" 2>&1
ts() { date -u +%FT%TZ; }
fail() { echo "$(ts) FAILED: $*"; echo failed >"$RES/build.done"; exit 1; }
rm -f "$RES/build.done"
echo "=== build1 started $(ts) sha=$SHA ==="
w=0; while [ ! -f "$RES/build0.done" ]; do [ $w = 0 ] && echo "$(ts) waiting for build0.done"; w=1; sleep 30; done
echo "$(ts) build0.done = $(cat "$RES/build0.done")"
git -C "$REPO" cat-file -e "$SHA^{commit}" || fail "$SHA not visible in $REPO"
git -C "$WT" checkout -q --detach "$SHA" || fail "checkout $SHA"
[ "$(git -C "$WT" rev-parse HEAD)" = "$SHA" ] || fail "$WT is not at $SHA"
grep -q "pack_group_heads" "$WT/t/t_amx_dispatch_dtype.cpp" || fail "amended test content missing in the worktree"
cd "$WT" || fail cd
t0=$(date +%s)
nice -n10 taskset -c $OUR_CPUS "$NIX" develop --accept-flake-config --command bash -c "cmake --build gen --target $TARGETS -j20 2>&1 | grep -E 'error|FAILED|warning: ' | head -40; echo \"build rc=\${PIPESTATUS[0]}\""
echo "$(ts) build wall=$(( $(date +%s) - t0 ))s"
ok=1
for t in $TARGETS; do [ -x "gen/$t" ] || { echo "$(ts) missing gen/$t"; ok=0; }; done
if [ $ok = 1 ]; then
  cp gen/runtron gen/runtron.g16 && sha256sum gen/runtron.g16
  echo "tdpbf16ps count: $(objdump -d gen/runtron.g16 | grep -c tdpbf16ps)"
  echo "TRON_ATTN_STATS strings: $(strings gen/runtron.g16 | grep -c TRON_ATTN_STATS)"
  echo "kernel instantiations:"; nm -C gen/runtron.g16 | grep -E 'amx_attn_h128g4::(pack_q_group_128x4|qk_rowmajor_128x4|weights_times_v_128x4)<' | sed 's/^/  /'
  echo "__tls_get_addr calls in the linked runtron: $(objdump -d gen/runtron.g16 | grep -c '__tls_get_addr')"
  echo "vshuff32x4 / vshuff64x2 in qk<16>: $(objdump -d --no-show-raw-insn -C gen/runtron.g16 | awk '/<tron::amx_attn_h128g4::qk_rowmajor_128x4<16ul>/{f=1} f&&/^$/{f=0} f' | grep -cE 'vshuff(32x4|64x2)')"
  echo "vshuff32x4 / vshuff64x2 in qk<4>:  $(objdump -d --no-show-raw-insn -C gen/runtron.g16 | awk '/<tron::amx_attn_h128g4::qk_rowmajor_128x4<4ul>/{f=1} f&&/^$/{f=0} f' | grep -cE 'vshuff(32x4|64x2)')"
  grep -E "^TRON_(AMX_DISPATCH|K_VNNI):" gen/CMakeCache.txt | tr '\n' ' '; echo
  echo ok >"$RES/build.done"; echo "$(ts) ok"
else
  echo failed >"$RES/build.done"
fi
echo "=== build1 finished $(ts) ==="
