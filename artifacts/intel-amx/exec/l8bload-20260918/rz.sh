# rinzler start/stop helpers for the l8bload-20260918 campaign (fork of exec/p0perf-20260913/rz.sh):
# TWO engines at once on OUR half of delphi-3bda (socket 1, cards 90/93 and b9/bc), placed exactly
# like the nightly's own tp2 engines. The placements below are the platformd-generated RZ_CLI_ARGS
# of /etc/rinzler/instance-2.env and instance-3.env as snapshotted on 2026-09-18 16:28 UTC
# (exec/results/ci-mimic-20260918/target-pass1/perf.json), not derived by halving any more.
# Changes against the 09-13 file:
#   1. RZ_BIN = the rinzler of the ci-mimic TARGET deb (2026.09.18-29a8a547, AMX kernels + VNNI K
#      compiled), extracted with dpkg-deb -x into /var/tmp/jhan/ci-mimic-20260918/root (its RUNPATH
#      is $ORIGIN, so libversion.so resolves next to it; libfuse3 comes from /opt/positron/lib).
#   2. arms: off = TRON_AMX_DISABLE=1 (kill switch), on = variable unset. USE_HW_ATTN is REMOVED from
#      the environment and never set: llama-3.1-8b is a hand-written plugin, and with the variable
#      unset tron keeps hardware attention off for it ("default off for this model"), which is exactly
#      the nightly's mode. No fpga arm.
#   3. hugepage files /dev/hugepages/amx-l8bload-<port>.
# Kept: production environment (TRON_USE_SPECULATION=0, RZ_FUSE_MOUNT_PRESCOPED=1, RZ_ENABLE_SAVE_TOKENS=1,
# taskset launcher cores), `env -u SYSTEM_CONFIG`, exec so the recorded pid is the rinzler itself, the
# campaign flock fd closed in the child, health timeout 600 s, stale FUSE mount detached first, owner +
# fuser test before removing hugepage files. PATH left alone (fusermount3 trap, round 1).
# Source this file.
RZ_BIN=${RZ_BIN:-/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler}
# Our rinzler by absolute path AND one of our ports: another rinzler started from the same file is left alone.
OUR_RZ_RE='^/var/tmp/jhan/ci-mimic-20260918/root/opt/positron/bin/rinzler .*--port 1310[01]( |$)'
declare -A RZ_PIDS=()
declare -A RZ_LOGS=()
RZ_HP_BEFORE=""
RZ_HP_SNAPPED=""

engine_sysargs() {  # $1 = engine key (a = instance 2,4 on cards 90/93; b = instance 3,4 on cards b9/bc)
  case $1 in
    a) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    b) echo "--instance 3,4 --devices b9:00.0,bc:00.0 --app-cores 227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 77,78 --numa 1 --nr_hugepages 128" ;;
    *) return 1 ;;
  esac
}
engine_affinity() { case $1 in a) echo 73,217 ;; b) echo 74,218 ;; *) return 1 ;; esac; }   # platformd CPUAFFINITY of instance-3.env / instance-2.env
engine_port() { case $1 in a) echo 13100 ;; b) echo 13101 ;; *) return 1 ;; esac; }
ENGINE_KEYS="a b"

arm_env() {  # $1 = arm -> extra env words (one per line); USE_HW_ATTN stays unset in both arms
  case $1 in
    off) printf '%s\n' TRON_AMX_DISABLE=1 ;;
    on)  ;;
    *) return 1 ;;
  esac
}

rz_launch() {  # ARM KEY LOGFILE MODEL
  local arm=$1 key=$2 logf=$3 model=$4 sysargs port cores
  sysargs=$(engine_sysargs "$key") || { echo "rz_launch: bad key $key"; return 1; }
  port=$(engine_port "$key"); cores=$(engine_affinity "$key")
  case $arm in off|on) ;; *) echo "rz_launch: bad arm $arm"; return 1 ;; esac
  [ -x "$RZ_BIN" ] || { echo "rz_launch: binary missing $RZ_BIN"; return 1; }
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$port 2>/dev/null
  mkdir -p /var/tmp/jhan/rz-fuse/$port
  [ -n "$RZ_HP_SNAPPED" ] || { RZ_HP_BEFORE=$(ls /dev/hugepages 2>/dev/null | sort | tr '\n' ' '); RZ_HP_SNAPPED=1; }
  local envc=(env -u TRON_AMX_DISABLE -u USE_HW_ATTN -u SYSTEM_CONFIG
              TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug
              RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$port
              RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  local w; while read -r w; do [ -n "$w" ] && envc+=("$w"); done < <(arm_env "$arm")
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "rz_launch: could not raise memlock limit"
  echo "rz_launch arm=$arm key=$key port=$port cores=$cores bin=$RZ_BIN model=$model memlock=$(ulimit -l) $(date -u +%FT%TZ)"
  (cd "$(dirname "$RZ_BIN")" || exit 1
   [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
   exec "${envc[@]}" taskset -c "$cores" "$RZ_BIN" --model "$model" --port "$port" $sysargs \
      --hugepage_file /dev/hugepages/amx-l8bload-$port >"$logf" 2>&1) &
  RZ_PIDS[$port]=$!
  RZ_LOGS[$port]=$logf
  return 0
}

rz_ready() {  # KEY MODEL -> 0 when /v1/models lists the model and one warm-up completion answered
  local key=$1 model=$2 port pid deadline p
  port=$(engine_port "$key"); pid=${RZ_PIDS[$port]:-}
  [ -n "$pid" ] || { echo "rz_ready: no engine launched on port $port"; return 1; }
  deadline=$(( $(date +%s) + ${RZ_HEALTH_SEC:-600} ))
  while :; do
    for p in "${RZ_PIDS[@]}"; do
      kill -0 "$p" 2>/dev/null || { echo "rz_ready: rinzler pid $p exited early (waiting on port $port)"; for f in "${RZ_LOGS[@]}"; do echo "== tail $f"; tail -20 "$f" 2>/dev/null; done; return 1; }
    done
    curl -s -m 5 "http://127.0.0.1:$port/v1/models" | grep -q "\"$model\"" && break
    [ "$(date +%s)" -ge "$deadline" ] && { echo "rz_ready: health timeout on port $port"; tail -20 "${RZ_LOGS[$port]:-/dev/null}" 2>/dev/null; return 1; }
    sleep 5
  done
  curl -s -m 120 "http://127.0.0.1:$port/v1/chat/completions" -H 'Content-Type: application/json' \
    -d "{\"model\":\"$model\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello.\"}],\"max_tokens\":8}" \
    | head -c 300; echo
  echo "rz_ready: port $port ready $(date -u +%FT%TZ)"
  return 0
}

rz_stop_all() {
  local port pid f
  for port in "${!RZ_PIDS[@]}"; do
    pid=${RZ_PIDS[$port]}
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
      kill -TERM "$pid" 2>/dev/null
      for _ in $(seq 1 60); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
      kill -0 "$pid" 2>/dev/null && { echo "rz_stop_all: SIGKILL port $port"; kill -KILL "$pid" 2>/dev/null; sleep 2; }
      wait "$pid" 2>/dev/null
    fi
  done
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2
  pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  for port in 13100 13101; do fusermount3 -uz /var/tmp/jhan/rz-fuse/$port 2>/dev/null; done
  # Remove only hugepage files that appeared since the first launch, are OURS and are unmapped
  # (owner test first: fuser cannot read another user's maps; verified 2026-09-08).
  for f in $(ls /dev/hugepages 2>/dev/null | sort); do
    case " $RZ_HP_BEFORE " in *" $f "*) continue ;; esac
    [ -O "/dev/hugepages/$f" ] || { echo "rz_stop_all: $f belongs to $(stat -c %U "/dev/hugepages/$f" 2>/dev/null || echo '?'), left alone"; continue; }
    if fuser -s "/dev/hugepages/$f" 2>/dev/null; then echo "rz_stop_all: $f still mapped - left in place"; else rm -f "/dev/hugepages/$f"; fi
  done
  for f in /dev/hugepages/amx-l8bload-*; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f"; done
  echo "rz_stop_all: done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
  RZ_PIDS=(); RZ_LOGS=(); RZ_HP_BEFORE=""; RZ_HP_SNAPPED=""
}
