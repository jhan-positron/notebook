#!/usr/bin/env bash
# Single-attention phase campaign (2026-09-01): per-token phase timers inside the
# attention hot loop (QK / softmax / PV / state update / joins / barrier waits),
# exported as kvwait stamps 7606+ by worker 0, three arms (canonical AMX,
# arena-mirror AMX, kill switch = AVX), 1u, ctx {256,2048,8192} x 2 reps x 256 tokens.
# Build stage: both arm binaries built here from the committed measurement branch
# (tron-fence-amx, jhan-amx-fence) in gen/, one reconfigure per arm, gen header
# re-stamped by the patcher after each configure. Binaries stay in gen/ (RUNPATH is
# $ORIGIN-relative). Run ON delphi-3bda:
#   nohup bash ~/workspace/intel-AMX/exec/single-attn-20260901/run-single-attn.sh &
set -u
EXEC=~/workspace/intel-AMX/exec
HERE=$EXEC/single-attn-20260901
DIR=$EXEC/results/single-attn-20260901; OUT=$DIR/single-attn.txt
LOG=$EXEC/logs/single-attn-20260901.log; MARKER=$EXEC/logs/single-attn-20260901.done
WT=~/workspace/tron-fence-amx
PATCHER=$EXEC/fence-20260831/patch-gen-stamps.py
EXTRACT=$HERE/extract-sa.py
GENHDR=$WT/gen/src/tron/h/tron/plugins/qwen_3_4b_instruct_2507.hpp
MODEL=ingested-qwen-3-4b-instruct-2507-tp2
EXPECT_COMMIT=${EXPECT_COMMIT:-}   # set by the launcher: the jhan-amx-fence commit that carries the phase probe
mkdir -p "$DIR" "$EXEC/logs"
[ -s "$OUT" ] && mv "$OUT" "$OUT.prev.$(date -u +%Y%m%dT%H%M%SZ)"
exec >>"$LOG" 2>&1; rm -f "$MARKER"
source "$EXEC/lib-guard.sh"
RUNPID=0; GUARDED=0
trap '[ -e "$MARKER" ] || { [ "$RUNPID" -gt 0 ] && kill -TERM "$RUNPID" 2>/dev/null; sleep 2; rm -f /dev/hugepages/amx-sa* 2>/dev/null; [ "$GUARDED" = 1 ] && campaign_guard_release 2>/dev/null; echo aborted >"$MARKER"; }' EXIT
echo "=== single-attn start $(date -u +%FT%TZ) ==="
if ci_lease_busy; then echo guard-refused-lease >"$MARKER"; exit 1; fi
if rinzler_active; then echo guard-refused-rinzler >"$MARKER"; exit 1; fi
if ! campaign_guard_acquire; then echo guard-refused >"$MARKER"; exit 1; fi
GUARDED=1

# --- Stage B: provenance + NFS content check (edit made on another host) ---
cd "$WT" || { echo no-worktree >"$MARKER"; exit 1; }
HEAD=$(git rev-parse HEAD)
if [ -n "$EXPECT_COMMIT" ] && [ "$HEAD" != "$EXPECT_COMMIT" ]; then echo "HEAD $HEAD != expected $EXPECT_COMMIT"; echo wrong-commit >"$MARKER"; exit 1; fi
if [ -n "$(git status --porcelain -- h src)" ]; then echo "worktree dirty:"; git status --porcelain -- h src; echo dirty-worktree >"$MARKER"; exit 1; fi
# the probe must be visible ON THIS HOST before building (NFS attribute-cache trap, 2026-08-31)
for i in $(seq 1 20); do grep -q "namespace attn_phase" h/tron/models/self_attention.hpp && break; sleep 15; done
grep -q "namespace attn_phase" h/tron/models/self_attention.hpp || { echo probe-not-visible >"$MARKER"; exit 1; }
sync; sleep 5
{ echo "### commit $HEAD  $(date -u +%FT%TZ)"; sha256sum h/tron/models/self_attention.hpp "$PATCHER"; } >>"$OUT"

# --- Stage C: build both arms (mirror first, then canonical), re-stamping the gen header after each configure ---
NIX="PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c"
build_arm() { # name mirror_flag
  local name=$1 flag=$2 t0; t0=$(date -u +%s)
  echo "### build $name (TRON_AMX_K_MIRROR=$flag) start $(date -u +%FT%TZ)" >>"$OUT"
  env PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
    "set -o pipefail; cmake --preset cross-avx512 -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=$flag -DCMAKE_CXX_FLAGS= >/dev/null" \
    || { echo reconfig-failed-$name >"$MARKER"; exit 1; }
  python3 "$PATCHER" || { echo gen-patch-failed-$name >"$MARKER"; exit 1; }
  for tag in 7601 7603 7604 7605; do grep -q "site $tag" "$GENHDR" || { echo "gen header lacks site $tag"; echo stamps-missing-$name >"$MARKER"; exit 1; }; done
  grep -q "sites 7606" "$GENHDR" && grep -q "probe_reset" "$GENHDR" || { echo "gen header lacks the 7606-7627 export or probe_reset"; echo stamps-missing-$name >"$MARKER"; exit 1; }
  env PATH=/nix/var/nix/profiles/default/bin:$PATH nice -n10 nix develop --command bash -c \
    "set -o pipefail; cmake --build gen --target runtron -j96 2>&1 | tail -3" \
    || { echo build-failed-$name >"$MARKER"; exit 1; }
  grep -q "TRON_AMX_K_MIRROR:BOOL=$flag" gen/CMakeCache.txt || { echo cache-flag-mismatch-$name >"$MARKER"; exit 1; }
  cp gen/runtron "gen/runtron.$name"
  timeout 15 "gen/runtron.$name" --help >/dev/null 2>&1 || { echo "binary wont exec: $name"; echo binary-wont-exec-$name >"$MARKER"; exit 1; }
  echo "### build $name done in $(( $(date -u +%s) - t0 )) s" >>"$OUT"
}
build_arm samirror ON
build_arm sacanon OFF
sha256sum gen/runtron.samirror gen/runtron.sacanon >>"$OUT"
cmp -s gen/runtron.samirror gen/runtron.sacanon && { echo "IDENTICAL-BINARIES"; echo identical-binaries >"$MARKER"; exit 1; }

stop_now() { local tmo=${1:-0} now prep; now=$(date -u +%s)
  prep=$(date -u -d "03:30" +%s); [ "$prep" -le "$now" ] && prep=$(date -u -d "tomorrow 03:30" +%s)
  [ $((now+tmo+300)) -ge "$prep" ] && { echo CLOCK-STOP; return 0; }
  ci_took_dut && { echo CI-TOOK-DUT; return 0; }
  rinzler_active && { echo RINZLER-BACK; return 0; }; return 1; }
COMMON="--instance 0,4 --devices 10:00.0,13:00.0 \
  --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 \
  --numa 0 --hugepage_file /dev/hugepages/amx-sa --nr_hugepages 128 -o"
run_cell() { # arm ctx rep tmo len
  local arm=$1 ctx=$2 rep=$3 tmo=$4 len=$5 bin envset rc
  local kv=$DIR/kvwait-$arm-c$ctx-r$rep.bin rlog=$DIR/cell-$arm-c$ctx-r$rep.log
  case $arm in canon)   bin=$WT/gen/runtron.sacanon;  envset="env -u TRON_AMX_DISABLE";;
               mirror)  bin=$WT/gen/runtron.samirror; envset="env -u TRON_AMX_DISABLE";;
               disable) bin=$WT/gen/runtron.samirror; envset="env TRON_AMX_DISABLE=1";; esac
  echo "### model=$MODEL arm=$arm ctx=$ctx len=$len users=1 rep=$rep kv=$(basename $kv) bin=$(basename $bin)"
  $envset USE_HW_ATTN=0 TRON_ATTN_PHASE=1 TRON_KVWAIT_FILE=$kv timeout "$tmo" "$bin" stream-generate-text -m "$MODEL" $COMMON \
    --prompt-length "$ctx" -l "$len" -u 1 >"$rlog" 2>&1 &
  RUNPID=$!; wait "$RUNPID"; rc=$?; RUNPID=0
  grep -E "Parsing the prompt took|average tok/s" "$rlog"
  [ "$rc" -ne 0 ] && echo "RUN-FAILED rc=$rc"
  [ -s "$kv" ] || echo "KVWAIT-EMPTY $kv"
}
STOPPED=0
{ stop_now 300 && { echo window-closed >"$MARKER"; exit 1; }
  # smoke: every arm must emit all stamps incl. the new phase stamps, and the AMX
  # arms must report AMX-path units > 0 while the kill switch reports exactly 0.
  for arm in mirror canon disable; do
    run_cell $arm 256 0 300 8
    python3 "$EXTRACT" --check --arm $arm $DIR/kvwait-$arm-c256-r0.bin || { echo "SMOKE-FAILED arm=$arm"; echo smoke-failed >"$MARKER"; exit 1; }
  done
  echo "### smoke ok $(date -u +%FT%TZ)"
  for rep in 1 2; do
    for ctx in 256 2048 8192; do
      for arm in canon mirror disable; do
        stop_now 900 && { STOPPED=1; break 3; }
        run_cell "$arm" "$ctx" "$rep" 900 256
      done
    done
    echo "### rep $rep complete $(date -u +%FT%TZ)"
  done
} >>"$OUT" 2>&1
rm -f /dev/hugepages/amx-sa* 2>/dev/null || true
campaign_guard_release; GUARDED=0
if [ "$STOPPED" = 1 ]; then echo stopped-early >"$MARKER"
elif grep -qE "RUN-FAILED|KVWAIT-EMPTY|SMOKE-FAILED" "$OUT"; then echo check-output >"$MARKER"
else echo ok >"$MARKER"; fi
echo "=== single-attn end $(date -u +%FT%TZ) marker=$(cat $MARKER) ==="
