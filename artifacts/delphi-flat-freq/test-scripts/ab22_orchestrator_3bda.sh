#!/bin/bash
# ab22_orchestrator_3bda.sh — completes the 2x2 (build x shape) through the
# talos serving path on 3bda: the 0bf row (3 shape-interleaved pairs) plus
# an aa8-source verification pair. Laptop-independent; coordinates with the
# 3af6 client daemon via NFS markers in /scratch/jhan/ab22/.
# Window: waits for 11:35 UTC (nightly ends ~11:20), hard-stops 13:40 UTC
# (GitHub CI handoff 14:00). Restores stock binary + trio + tron112 at end.
set -u
AB=/scratch/jhan/ab22
mkdir -p "$AB/results"
log(){ echo "$(date -u '+%F %T') $*" >> "$AB/journal.log"; }
DROPDIR=/etc/systemd/system/rinzler@.service.d

restore_all(){
  log "RESTORE begin"
  sudo -n systemctl stop "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  sleep 5
  sudo -n rm -f "$DROPDIR/ab22.conf" 2>/dev/null
  sudo -n systemctl daemon-reload
  for f in /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && rm -f "$f" 2>/dev/null; done
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.1-8b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' \
    http://localhost:8080/api/config > /dev/null; sleep 3
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.2-3b-instruct-fast"},{"shape":"llama-3.1-8b-instruct-good"},{"shape":"llama-3.3-70b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' \
    http://localhost:8080/api/config > /dev/null
  sleep 20
  [ "$(pgrep -x rinzler | wc -l)" -eq 0 ] && sudo -n systemctl start "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  bash /scratch/jhan/p43/p43_worker_toggle.sh fast >> "$AB/journal.log" 2>&1
  for i in $(seq 1 30); do
    R=$(curl -s -m 3 http://localhost/v1/models 2>/dev/null | grep -c llama)
    [ "$R" -ge 1 ] && log "RESTORE: trio serving" && break; sleep 15
  done
  log "RESTORE done"
}

hard_stop_check(){
  local now=$(date -u +%H%M)
  if [ "$now" -ge 1340 ] && [ "$now" -lt 1430 ]; then
    log "HARD STOP window reached — restoring and aborting"
    touch "$AB/ALL_DONE"; restore_all; log "ABORTED-PARTIAL"; exit 1
  fi
}

swap_build(){
  local BUILD_DIR="$1" BUILD_TAG="$2"
  log "swap_build -> $BUILD_TAG ($BUILD_DIR)"
  sudo -n systemctl stop "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  sleep 8
  for f in /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && rm -f "$f" 2>/dev/null; done
  sudo -n mkdir -p "$DROPDIR"
  printf '[Service]\nExecStart=\nExecStart=/usr/bin/taskset -c ${CPUAFFINITY} %s/gen/rinzler $RZ_CLI_ARGS\n' "$BUILD_DIR" | sudo -n tee "$DROPDIR/ab22.conf" > /dev/null
  sudo -n systemctl daemon-reload
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.1-8b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' \
    http://localhost:8080/api/config > /dev/null; sleep 3
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"ingested-gpt-oss-120b"}],"tensor_parallelism":4,"count":2}}}}' \
    http://localhost:8080/api/config > /dev/null
  for i in $(seq 1 40); do
    R=$(curl -s -m 3 http://localhost/v1/models 2>/dev/null | grep -c gpt-oss)
    [ "$R" -ge 1 ] && break; sleep 12
  done
  FP=$(curl -s -m 60 -X POST -H "Content-Type: application/json" \
    -d '{"model":"ingested-gpt-oss-120b-tp4","messages":[{"role":"user","content":"hi"}],"max_tokens":2}' \
    http://localhost:13000/v1/chat/completions | grep -o "prz_[^\"]*")
  log "swap_build $BUILD_TAG fingerprint: $FP"
  case "$FP" in *"$BUILD_TAG"*) return 0;; *) log "FINGERPRINT MISMATCH — abort"; touch "$AB/ALL_DONE"; restore_all; exit 1;; esac
}

run_cell(){
  local NAME="$1" SEED="$2" CAPTURE="$3"
  hard_stop_check
  log "run $NAME (seed_offset=$SEED capture=$CAPTURE) requested"
  echo "seed_offset=$SEED" > "$AB/REQ_$NAME"
  if [ "$CAPTURE" = "yes" ]; then
    ( sleep 75; /scratch/jhan/flat_freq_tests/scripts/ci_workload_profile.sh --any > "$AB/results/capture_$NAME.log" 2>&1 ) &
  fi
  for i in $(seq 1 90); do
    [ -f "$AB/DONE_$NAME" ] && log "run $NAME done" && return 0
    sleep 10
  done
  log "run $NAME TIMED OUT"; return 1
}

# ---- main ----
log "orchestrator armed (pid $$); waiting for 11:35 UTC"
TARGET=$(date -ud "$(date -u +%F) 11:35:00" +%s)
NOW=$(date +%s)
[ "$TARGET" -gt "$NOW" ] && sleep $((TARGET - NOW))
# gates
for i in $(seq 1 20); do
  BUSY=$(pgrep -cf "[t]alos|Runner.Worker" 2>/dev/null | head -1)
  [ "${BUSY:-0}" -eq 0 ] && break
  log "gate: CI still busy, waiting"; sleep 60
done
hard_stop_check
log "window open — starting 2x2 second row"

# 0bf row: 3 shape-interleaved pairs (clamp, fast)
swap_build /var/tmp/jhan/ef-inv/tron-198650bf 198650bf
SEED=3000
for rep in 1 2 3; do
  CAP=no; [ "$rep" = "2" ] && CAP=yes
  bash /scratch/jhan/p43/p43_worker_toggle.sh clamp >> "$AB/journal.log" 2>&1
  run_cell "0bf_clamp_r$rep" "$SEED" "$CAP"; SEED=$((SEED+100))
  bash /scratch/jhan/p43/p43_worker_toggle.sh fast >> "$AB/journal.log" 2>&1
  run_cell "0bf_fast_r$rep" "$SEED" "$CAP"; SEED=$((SEED+100))
done

# aa8 source-build verification pair
swap_build /var/tmp/jhan/ef-inv/tron-29924aa8 29924aa8
bash /scratch/jhan/p43/p43_worker_toggle.sh clamp >> "$AB/journal.log" 2>&1
run_cell "aa8src_clamp_r1" "$SEED" no; SEED=$((SEED+100))
bash /scratch/jhan/p43/p43_worker_toggle.sh fast >> "$AB/journal.log" 2>&1
run_cell "aa8src_fast_r1" "$SEED" no

touch "$AB/ALL_DONE"
restore_all
log "orchestrator COMPLETE"
