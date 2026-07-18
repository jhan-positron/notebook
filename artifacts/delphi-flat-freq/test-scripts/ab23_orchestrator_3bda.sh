#!/bin/bash
# ab23_orchestrator_3bda.sh — coordinator-placement A/B on aa8 (2x2 item-1
# follow-up): stock (main on worker core 24/96) vs dedicated (main moved to
# boosted spare 15/87 via app-cores lowest-core swap; worker set identical).
# Window: 02:50-04:05 UTC (before nightly ~04:25). Marker choreography with
# the 3af6 client daemon in /scratch/jhan/ab23/.
set -u
AB=/scratch/jhan/ab23
mkdir -p "$AB/results"
log(){ echo "$(date -u '+%F %T') $*" >> "$AB/journal.log"; }
DROPDIR=/etc/systemd/system/rinzler@.service.d
ISST="sudo -n /opt/intel-speed-select/intel-speed-select"
AA8=/var/tmp/jhan/ef-inv/tron-29924aa8

hard_stop(){
  local now=$(date -u +%H%M)
  if [ "$now" -ge 405 ] && [ "$now" -lt 1130 ]; then
    log "HARD STOP — restore and abort"; touch "$AB/ALL_DONE"; restore_all; exit 1
  fi
}

restore_all(){
  log "RESTORE begin"
  sudo -n systemctl stop "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  sleep 5
  sudo -n rm -f "$DROPDIR/ab23.conf" 2>/dev/null
  sudo -n systemctl daemon-reload
  for f in /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && rm -f "$f" 2>/dev/null; done
  $ISST --cpu 15,87,159,231 core-power assoc --clos 3 >/dev/null 2>&1
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.1-8b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' \
    http://localhost:8080/api/config > /dev/null; sleep 3
  curl -s -X PATCH -H "Content-Type: application/json" \
    -d '{"inference":{"engines":{"default":{"models":[{"shape":"llama-3.2-3b-instruct-fast"},{"shape":"llama-3.1-8b-instruct-good"},{"shape":"llama-3.3-70b-instruct-good"}],"tensor_parallelism":2,"count":4}}}}' \
    http://localhost:8080/api/config > /dev/null
  sleep 20
  [ "$(pgrep -x rinzler | wc -l)" -eq 0 ] && sudo -n systemctl start "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  bash /scratch/jhan/p43/p43_worker_toggle.sh fast >> "$AB/journal.log" 2>&1
  log "RESTORE done"
}

set_arm(){
  local ARM="$1"   # stock | dedic
  log "set_arm $ARM"
  sudo -n systemctl stop "rinzler@0" "rinzler@1" "rinzler@2" "rinzler@3" 2>/dev/null
  sleep 8
  for f in /dev/hugepages/slice-*-of-8; do [ -e "$f" ] && rm -f "$f" 2>/dev/null; done
  if [ "$ARM" = "dedic" ]; then
    printf '[Service]\nExecStart=\nExecStart=/scratch/jhan/ab23/rz_wrapper.sh\n' | sudo -n tee "$DROPDIR/ab23.conf" > /dev/null
  else
    printf '[Service]\nExecStart=\nExecStart=/usr/bin/taskset -c ${CPUAFFINITY} %s/gen/rinzler $RZ_CLI_ARGS\n' "$AA8" | sudo -n tee "$DROPDIR/ab23.conf" > /dev/null
  fi
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
  sleep 10
  # placement evidence: which threads sit on 15/24/87/96
  ps -eLo pid,tid,comm,psr --no-headers | awk '$4==15||$4==24||$4==87||$4==96' | grep -v idle > "$AB/results/placement_$ARM.txt" 2>/dev/null
  log "set_arm $ARM done; placement snapshot saved"
}

run_cell(){
  local NAME="$1" SEED="$2"
  hard_stop
  log "run $NAME (seed=$SEED)"
  echo "seed_offset=$SEED" > "$AB/REQ_$NAME"
  for i in $(seq 1 90); do
    [ -f "$AB/DONE_$NAME" ] && log "run $NAME done" && return 0
    sleep 10
  done
  log "run $NAME TIMEOUT"; return 1
}

# ---- main ----
# IMMEDIATE MODE (2026-07-16): user reclaimed the box; start now, no
# overnight wait. hard_stop still guards the nightly window.
log "ab23 orchestrator armed (pid $$); immediate mode"
for i in $(seq 1 10); do
  BUSY=$(pgrep -cf "[t]alos|Runner.Worker" 2>/dev/null | head -1)
  [ "${BUSY:-0}" -eq 0 ] && break
  log "gate busy, waiting"; sleep 30
done
hard_stop
log "window open"
# boost the dedicated spare cores for the whole session (harmless to stock arm)
$ISST --cpu 15,87,159,231 core-power assoc --clos 0 >/dev/null 2>&1
bash /scratch/jhan/p43/p43_worker_toggle.sh fast >> "$AB/journal.log" 2>&1

SEED=6000
for rep in 4 5 6 7 8 9 10 11 12 13; do
  set_arm stock
  run_cell "stock_r$rep" "$SEED"; SEED=$((SEED+100))
  set_arm dedic
  run_cell "dedic_r$rep" "$SEED"; SEED=$((SEED+100))
done

touch "$AB/ALL_DONE"
restore_all
log "ab23 COMPLETE"
