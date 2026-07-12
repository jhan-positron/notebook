#!/usr/bin/env bash
# 12_latency_vs_socket_bw.sh -- Test 12: single-core DRAM latency while
# whole-socket DRAM bandwidth is being driven by the Test 11 load shape.
#
# Test 11 answers: "What throughput does the socket reach?"
# Test 12 answers: "What latency does one DRAM pointer-chase victim see while
# that throughput load is active?"
#
# Background load is intentionally the Test 11 shape:
#   bw_multi --local, socket-0 cores, 64 MiB/thread, 4K pages, same memory-rich
#   node-first core order, same N sweep, read + rmw.
#
# Victim probes:
#   saturated_core     - victim shares a CPU with an active bw_multi worker
#   remote_unused_core - victim uses a same-socket remote core not yet reached
#                        by the Test 11 prefix, when one exists
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BW="$HERE/../bin/bw_multi"
PTR="$HERE/../bin/ptr_chase"
RESULTS="$HERE/../results"

SNC=$(cat /sys/devices/system/node/online)
case "$SNC" in
  0-5) MODE=SNC3; RESULTS="$RESULTS/snc3" ;;
  0-1) MODE=SNC-OFF; RESULTS="$RESULTS/snc-off" ;;
  *)
    echo "!!! unexpected node/online=$SNC possible=$(cat /sys/devices/system/node/possible)"
    exit 1
    ;;
esac
mkdir -p "$RESULTS"

STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
OUT="$RESULTS/latency_vs_socket_bw_${HOST}_${STAMP}.csv"
LOG="$RESULTS/latency_vs_socket_bw_${HOST}_${STAMP}.log"

# Defaults keep the background alive long enough for one 1 GiB victim probe.
# Override from the environment for debugging, e.g. POINTS="1 72" BG_SECS=8.
POINTS="${POINTS:-1 2 4 8 12 16 24 32 40 48 56 64 72}"
PATTERNS="${PATTERNS:-read rmw}"
BG_SIZE="${BG_SIZE:-64M}"
BG_HP="${BG_HP:-none}"
BG_ITERS="${BG_ITERS:-1}"
BG_SECS="${BG_SECS:-30}"
SETTLE_SECS="${SETTLE_SECS:-2}"
VICTIM_WS="${VICTIM_WS:-1G}"
if [ -z "${VICTIM_HP_LIST:-}" ]; then
  VICTIM_HP_LIST="${VICTIM_HP:-none} 1g"
fi
VICTIM_HP_LIST=$(printf '%s\n' $VICTIM_HP_LIST | awk '!seen[$0]++ { out = out ? out " " $0 : $0 } END { print out }')
VICTIM_ITERS="${VICTIM_ITERS:-3}"
VICTIM_MIN_SECS="${VICTIM_MIN_SECS:-0.25}"
VICTIM_PATTERN="${VICTIM_PATTERN:-read}"

echo "snc_mode,bg_pattern,bg_nthreads,bg_cpus,bg_agg_GBps,victim_role,victim_cpu,victim_mem_node,victim_ws,hugepage,victim_pattern,median_ns,min_ns,max_ns,mean_ns,stddev_ns,notes" > "$OUT"
exec > >(tee -a "$LOG") 2>&1

cleanup() {
  local pids
  pids=$(jobs -pr || true)
  if [ -n "$pids" ]; then
    kill $pids 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "===== 12_latency_vs_socket_bw $(date) mode=$MODE (online=$SNC possible=$(cat /sys/devices/system/node/possible)) ====="
echo "CSV: $OUT"
echo "method: Test11 background bw_multi --local, $BG_SIZE/thread, hugepage=$BG_HP, BG_SECS=$BG_SECS, points={$POINTS}, patterns={$PATTERNS}"
echo "victim: ptr_chase --size $VICTIM_WS --hugepage {$VICTIM_HP_LIST} --iters $VICTIM_ITERS --min-walk-secs $VICTIM_MIN_SECS pattern=$VICTIM_PATTERN"

if [ ! -x "$BW" ] || [ ! -x "$PTR" ]; then
  echo "!!! missing executable(s): $BW or $PTR"
  exit 1
fi

declare -A NODE_FREE NODE_CPUS CPU_NODE
declare -A BASELINE_DONE

for nd in /sys/devices/system/node/node*; do
  n=$(basename "$nd" | sed 's/node//')
  cl=$(cat "$nd/cpulist")
  cores=$(python3 - "$cl" <<'PY'
import sys
out = []
for part in sys.argv[1].split(','):
    if not part:
        continue
    if '-' in part:
        a, b = part.split('-')
        out.extend(c for c in range(int(a), int(b) + 1) if c < 72)
    else:
        c = int(part)
        if c < 72:
            out.append(c)
print(','.join(str(c) for c in sorted(out)))
PY
)
  [ -z "$cores" ] && continue
  free=$(awk '/MemFree/{print $4}' "$nd/meminfo")
  NODE_FREE[$n]=$free
  NODE_CPUS[$n]=$cores
  IFS=',' read -ra node_cpu_arr <<< "$cores"
  for c in "${node_cpu_arr[@]}"; do
    CPU_NODE[$c]=$n
  done
  echo "  node$n: socket-0 cores=[$cores] free=$((free/1024)) MB"
done

ORDER_NODES=$(for n in "${!NODE_FREE[@]}"; do echo "${NODE_FREE[$n]} $n"; done | sort -rn | awk '{print $2}')
ORDERED=""
for n in $ORDER_NODES; do
  ORDERED="${ORDERED:+$ORDERED,}${NODE_CPUS[$n]}"
done
IFS=',' read -ra CPUARR <<< "$ORDERED"

NMAX=${#CPUARR[@]}
if [ "$NMAX" -le 0 ]; then
  echo "!!! no socket-0 cores discovered"
  exit 1
fi

SAT_CPU=${CPUARR[0]}
SAT_NODE=${CPU_NODE[$SAT_CPU]}

echo "  Test11 core add-order (memory-rich node first): $ORDERED"
echo "  total socket-0 cores available: $NMAX"
echo "  selected saturated victim CPU: $SAT_CPU (node $SAT_NODE, first Test11-prefix CPU, active for every N)"

csv_row() {
  local mode="$1" pat="$2" n="$3" cpus="$4" bg="$5" role="$6" vcpu="$7" vnode="$8" ws="$9" hp="${10}" vpat="${11}" med="${12}" mn="${13}" mx="${14}" mean="${15}" sd="${16}" notes="${17}"
  printf '%s,%s,%s,"%s",%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,"%s"\n' \
    "$mode" "$pat" "$n" "$cpus" "$bg" "$role" "$vcpu" "$vnode" "$ws" "$hp" "$vpat" \
    "$med" "$mn" "$mx" "$mean" "$sd" "$notes" >> "$OUT"
}

prefix_cpus() {
  local n="$1"
  local old_ifs="$IFS"
  IFS=,
  echo "${CPUARR[*]:0:$n}"
  IFS="$old_ifs"
}

find_remote_unused_cpu() {
  local n="$1"
  local sat_node="$2"
  local i c
  for ((i=n; i<NMAX; i++)); do
    c=${CPUARR[$i]}
    if [ "${CPU_NODE[$c]}" != "$sat_node" ]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

run_probe_under_bg() {
  local pat="$1" n="$2" cpus="$3" role="$4" victim_cpu="$5" victim_node="$6" victim_hp="$7" role_note="$8"
  local bg_out bg_err ptr_out ptr_err bg_pid bg_rc ptr_rc bg_live_before bg_live_after bg_agg notes med mn mx mean sd
  bg_out=$(mktemp)
  bg_err=$(mktemp)
  ptr_out=$(mktemp)
  ptr_err=$(mktemp)
  notes="$role_note"

  local bg_cmd=("$BW" --cpus "$cpus" --local --size-per-thread "$BG_SIZE" --hugepage "$BG_HP" --pattern "$pat" --iters "$BG_ITERS" --min-walk-secs "$BG_SECS" --csv)
  echo ">>> N=$n bg_pattern=$pat role=$role"
  echo "    Test11 background command: ${bg_cmd[*]}"
  echo "    victim cpu=$victim_cpu node=$victim_node hugepage=$victim_hp"

  "${bg_cmd[@]}" >"$bg_out" 2>"$bg_err" &
  bg_pid=$!
  sleep "$SETTLE_SECS"

  bg_live_before=1
  if ! kill -0 "$bg_pid" 2>/dev/null; then
    bg_live_before=0
    notes="${notes};background_exited_before_probe"
  fi

  local ptr_cmd=("$PTR" --cpu "$victim_cpu" --mem-node "$victim_node" --size "$VICTIM_WS" --hugepage "$victim_hp" --iters "$VICTIM_ITERS" --min-walk-secs "$VICTIM_MIN_SECS" --csv)
  if [ "$VICTIM_PATTERN" = "rmw" ]; then
    ptr_cmd+=(--rmw)
  fi
  "${ptr_cmd[@]}" >"$ptr_out" 2>"$ptr_err"
  ptr_rc=$?

  bg_live_after=1
  if ! kill -0 "$bg_pid" 2>/dev/null; then
    bg_live_after=0
    notes="${notes};background_finished_during_probe"
  fi

  wait "$bg_pid"
  bg_rc=$?

  bg_agg=$(awk -F, 'NF>=8 {print $8; found=1} END{if(!found) print ""}' "$bg_out")
  if [ -z "$bg_agg" ]; then
    bg_agg=""
    notes="${notes};missing_bg_csv"
  fi
  if [ "$bg_rc" -ne 0 ]; then
    notes="${notes};bg_failed_rc_${bg_rc}"
  fi

  if [ "$ptr_rc" -eq 0 ] && [ -s "$ptr_out" ]; then
    med=$(awk -F, 'NF>=11 {print $7; found=1} END{if(!found) print ""}' "$ptr_out")
    mn=$(awk -F, 'NF>=11 {print $8; found=1} END{if(!found) print ""}' "$ptr_out")
    mx=$(awk -F, 'NF>=11 {print $9; found=1} END{if(!found) print ""}' "$ptr_out")
    mean=$(awk -F, 'NF>=11 {print $10; found=1} END{if(!found) print ""}' "$ptr_out")
    sd=$(awk -F, 'NF>=11 {print $11; found=1} END{if(!found) print ""}' "$ptr_out")
  else
    med=""; mn=""; mx=""; mean=""; sd=""
    notes="${notes};ptr_failed_rc_${ptr_rc}"
    echo "    ptr_chase failed rc=$ptr_rc"
    sed 's/^/      ptr: /' "$ptr_err" | tail -40
  fi

  if [ "$bg_rc" -ne 0 ]; then
    echo "    background failed rc=$bg_rc"
    sed 's/^/      bg: /' "$bg_err" | tail -40
  fi
  if [ "$bg_live_before" -eq 0 ] || [ "$bg_live_after" -eq 0 ]; then
    echo "    NOTE: $notes"
  fi

  csv_row "$MODE" "$pat" "$n" "$cpus" "$bg_agg" "$role" "$victim_cpu" "$victim_node" "$VICTIM_WS" "$victim_hp" "$VICTIM_PATTERN" "$med" "$mn" "$mx" "$mean" "$sd" "$notes"
  echo "    bg_agg=${bg_agg:-NA} GB/s victim_median=${med:-NA} ns notes=$notes"

  rm -f "$bg_out" "$bg_err" "$ptr_out" "$ptr_err"
}

run_victim_baseline_once() {
  local role="$1" victim_cpu="$2" victim_node="$3" victim_hp="$4" role_note="$5"
  local key ptr_out ptr_err ptr_rc notes med mn mx mean sd
  key="${role}:${victim_cpu}:${victim_node}:${victim_hp}"
  if [ -n "${BASELINE_DONE[$key]+x}" ]; then
    return 0
  fi
  BASELINE_DONE[$key]=1

  ptr_out=$(mktemp)
  ptr_err=$(mktemp)
  notes="baseline_no_background;${role_note}"

  echo ">>> baseline bg_nthreads=0 role=$role"
  echo "    victim cpu=$victim_cpu node=$victim_node hugepage=$victim_hp"

  local ptr_cmd=("$PTR" --cpu "$victim_cpu" --mem-node "$victim_node" --size "$VICTIM_WS" --hugepage "$victim_hp" --iters "$VICTIM_ITERS" --min-walk-secs "$VICTIM_MIN_SECS" --csv)
  if [ "$VICTIM_PATTERN" = "rmw" ]; then
    ptr_cmd+=(--rmw)
  fi
  "${ptr_cmd[@]}" >"$ptr_out" 2>"$ptr_err"
  ptr_rc=$?

  if [ "$ptr_rc" -eq 0 ] && [ -s "$ptr_out" ]; then
    med=$(awk -F, 'NF>=11 {print $7; found=1} END{if(!found) print ""}' "$ptr_out")
    mn=$(awk -F, 'NF>=11 {print $8; found=1} END{if(!found) print ""}' "$ptr_out")
    mx=$(awk -F, 'NF>=11 {print $9; found=1} END{if(!found) print ""}' "$ptr_out")
    mean=$(awk -F, 'NF>=11 {print $10; found=1} END{if(!found) print ""}' "$ptr_out")
    sd=$(awk -F, 'NF>=11 {print $11; found=1} END{if(!found) print ""}' "$ptr_out")
  else
    med=""; mn=""; mx=""; mean=""; sd=""
    notes="${notes};ptr_failed_rc_${ptr_rc}"
    echo "    baseline ptr_chase failed rc=$ptr_rc"
    sed 's/^/      ptr: /' "$ptr_err" | tail -40
  fi

  csv_row "$MODE" "none" "0" "" "0" "$role" "$victim_cpu" "$victim_node" "$VICTIM_WS" "$victim_hp" "$VICTIM_PATTERN" "$med" "$mn" "$mx" "$mean" "$sd" "$notes"
  echo "    baseline_median=${med:-NA} ns notes=$notes"

  rm -f "$ptr_out" "$ptr_err"
}

for pat in $PATTERNS; do
  echo "===== background pattern=$pat ====="
  for n in $POINTS; do
    if [ "$n" -gt "$NMAX" ]; then
      echo "  skip N=$n: only $NMAX socket-0 cores"
      continue
    fi

    cpus=$(prefix_cpus "$n")

    for victim_hp in $VICTIM_HP_LIST; do
      run_victim_baseline_once "saturated_core" "$SAT_CPU" "$SAT_NODE" "$victim_hp" "victim_shares_cpu_with_background_worker"
      run_probe_under_bg "$pat" "$n" "$cpus" "saturated_core" "$SAT_CPU" "$SAT_NODE" "$victim_hp" "victim_shares_cpu_with_background_worker"
    done

    if remote_cpu=$(find_remote_unused_cpu "$n" "$SAT_NODE"); then
      remote_node=${CPU_NODE[$remote_cpu]}
      echo "    selected remote-unused victim CPU: $remote_cpu (node $remote_node)"
      for victim_hp in $VICTIM_HP_LIST; do
        run_victim_baseline_once "remote_unused_core" "$remote_cpu" "$remote_node" "$victim_hp" "unused_same_socket_remote_core"
        run_probe_under_bg "$pat" "$n" "$cpus" "remote_unused_core" "$remote_cpu" "$remote_node" "$victim_hp" "unused_same_socket_remote_core"
      done
    else
      reason="no_unused_same_socket_remote_core_remains_at_N_${n}"
      echo "    remote-unused victim unavailable: $reason"
      for victim_hp in $VICTIM_HP_LIST; do
        csv_row "$MODE" "$pat" "$n" "$cpus" "" "remote_unused_core" "" "" "$VICTIM_WS" "$victim_hp" "$VICTIM_PATTERN" "" "" "" "" "" "$reason"
      done
    fi
  done
done

echo "===== done $(date) ====="
echo "CSV: $OUT"
