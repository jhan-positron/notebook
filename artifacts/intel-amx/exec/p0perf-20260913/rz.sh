# rinzler start/stop helpers for the p0perf-20260913 campaign: up to TWO engines at once on
# our half of delphi-3bda, placed exactly like the nightly CI's own engines on socket 1.
# Fork of exec/p0perf-20260911/rz.sh. Changes against the Friday version:
#   1. several engines at once: rz_launch starts one engine in the background and records
#      its pid by port; rz_ready waits for one engine's health; rz_stop_all stops every
#      engine this shell started (and, as a fallback, any orphan of OURS matched by the
#      absolute binary path and one of our two ports).
#   2. placements per ENGINE KEY, copied from the nightly's platformd-generated unit files:
#        4  = tp4 engine, --instance 1,2, cards 90/93/b9/bc  (seen live 2026-09-13 06:11 UTC in
#             /etc/rinzler/instance-1.env: same RZ_CLI_ARGS, CPUAFFINITY=73,217,74,218)
#        2a = tp2 engine, --instance 2,4, cards 90/93      (first half of the tp4 lists)
#        2b = tp2 engine, --instance 3,4, cards b9/bc      (second half of the tp4 lists)
#      The 2a/2b core lists and their launcher cores (73,217 / 74,218) are DERIVED from the
#      tp4 file by halving; the platformd files for a tp2 model were not readable when this
#      was written (see the campaign header; correct here if a paste shows otherwise).
#   3. a third arm, fpga = the nightly's current default: USE_HW_ATTN unset, so the ingested
#      qwen model runs attention on the FPGA from query position 127 on (the engagement point,
#      h/tron/models/hw_attn_config.hpp); positions 0-126 of every sequence stay on CPU
#      attention, so the arm ALSO sets TRON_AMX_DISABLE=1 to keep that software share on the
#      AVX path, as the nightly's main package (which has no AMX code) has it.
# Kept from Friday: production environment (TRON_USE_SPECULATION=0, RZ_FUSE_MOUNT_PRESCOPED=1,
# RZ_ENABLE_SAVE_TOKENS=1, taskset launcher cores), `env -u SYSTEM_CONFIG` (the login
# environment exports "--instance 1,2" and tron applies it AFTER the command line), exec so the
# recorded pid is the rinzler itself, the campaign flock fd closed in the child, health
# timeout 600 s, stale FUSE mount detached first, owner + fuser test before removing hugepage
# files. PATH is left alone on purpose (fusermount3 trap, round 1).
# Source this file.
#   engine_sysargs KEY        -> placement arguments        engine_port KEY -> 13100 | 13101
#   engine_affinity KEY       -> launcher taskset cores     engine_users TP -> users per engine
#   rz_launch ARM KEY LOGFILE MODEL   -> starts one engine (no wait); 0 when the process is up
#   rz_ready KEY MODEL                -> 0 when /v1/models lists the model and a warm-up answered
#   rz_stop_all                       -> stops every engine started here, cleans mounts and files
RZ_BIN=${RZ_BIN:-/var/tmp/jhan/tron-p0perf13/gen/rinzler.p0perf13}
# Our rinzler by absolute path AND one of our ports: another rinzler started from the same file is left alone.
OUR_RZ_RE='^/var/tmp/jhan/tron-p0perf13/gen/rinzler[.]p0perf13 .*--port 1310[01]( |$)'
declare -A RZ_PIDS=()
declare -A RZ_LOGS=()
RZ_HP_BEFORE=""
RZ_HP_SNAPPED=""   # set once the /dev/hugepages listing was taken (the listing itself may be empty)

engine_sysargs() {  # $1 = engine key
  case $1 in
    2a) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    2b) echo "--instance 3,4 --devices b9:00.0,bc:00.0 --app-cores 227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 77,78 --numa 1 --nr_hugepages 128" ;;
    4)  echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}
engine_affinity() {  # launcher cores (production: taskset -c $CPUAFFINITY rinzler ...)
  case $1 in 2a) echo 73,217 ;; 2b) echo 74,218 ;; 4) echo 73,217,74,218 ;; *) return 1 ;; esac
}
engine_port() { case $1 in 2a|4) echo 13100 ;; 2b) echo 13101 ;; *) return 1 ;; esac; }
engine_keys() { case $1 in 2) echo "2a 2b" ;; 4) echo "4" ;; *) return 1 ;; esac; }   # $1 = tp -> the engines of that layout
engine_users() { case $1 in 2) echo 2 ;; 4) echo 4 ;; *) return 1 ;; esac; }          # $1 = tp -> the nightly's 8 users over 4 / 2 engines

arm_env() {  # $1 = arm -> the env words that set the arm (printed one per line)
  case $1 in
    off)  printf '%s\n' USE_HW_ATTN=0 TRON_AMX_DISABLE=1 ;;
    on)   printf '%s\n' USE_HW_ATTN=0 ;;
    fpga) printf '%s\n' TRON_AMX_DISABLE=1 ;;   # USE_HW_ATTN stays unset (FPGA attention); the kill switch keeps the CPU share (positions 0-126) on AVX, as main has it
    *) return 1 ;;
  esac
}

rz_launch() {  # ARM KEY LOGFILE MODEL
  local arm=$1 key=$2 logf=$3 model=$4 sysargs port cores
  sysargs=$(engine_sysargs "$key") || { echo "rz_launch: bad key $key"; return 1; }
  port=$(engine_port "$key"); cores=$(engine_affinity "$key")
  case $arm in off|on|fpga) ;; *) echo "rz_launch: bad arm $arm"; return 1 ;; esac
  [ -x "$RZ_BIN" ] || { echo "rz_launch: binary missing $RZ_BIN"; return 1; }
  # a mount left behind by a SIGKILL makes the next rinzler fail to mount; after a SIGKILL the
  # endpoint answers stat with ENOTCONN, so mountpoint -q would say "no": detach unconditionally.
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$port 2>/dev/null
  mkdir -p /var/tmp/jhan/rz-fuse/$port
  [ -n "$RZ_HP_SNAPPED" ] || { RZ_HP_BEFORE=$(ls /dev/hugepages 2>/dev/null | sort | tr '\n' ' '); RZ_HP_SNAPPED=1; }
  # Same environment platformd gives production engines (instance-1.env of 2026-09-13), plus the
  # arm's switches. USE_HW_ATTN and TRON_AMX_DISABLE are first REMOVED, then set per arm.
  # TRON_LOG_LEVEL / SPDLOG_LEVEL are pinned to what the login environment exports (debug), the
  # same as round 1, G1 and Friday ran.
  local envc=(env -u TRON_AMX_DISABLE -u USE_HW_ATTN -u SYSTEM_CONFIG
              TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug
              RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$port
              RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  local w; while read -r w; do [ -n "$w" ] && envc+=("$w"); done < <(arm_env "$arm")
  # Production engines run under systemd with no memlock limit; an interactive user shell is
  # capped (round 1: "hugepages capped by ulimit constraints to 188 of 256").
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "rz_launch: could not raise memlock limit"
  echo "rz_launch arm=$arm key=$key port=$port cores=$cores bin=$RZ_BIN model=$model memlock=$(ulimit -l) $(date -u +%FT%TZ)"
  # exec: the background job IS the env -> taskset -> rinzler chain, so the pid is rinzler.
  # The child closes the inherited campaign flock fd first: an orphaned rinzler (after a kill -9 of
  # the campaign) must not keep the flock; `exec {VAR}>&-` needs the variable set, hence the guard.
  (cd "$(dirname "$RZ_BIN")/.." || exit 1
   [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
   exec "${envc[@]}" taskset -c "$cores" "$RZ_BIN" --model "$model" --port "$port" $sysargs \
      --hugepage_file /dev/hugepages/amx-p0perf13-$port >"$logf" 2>&1) &
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
    # every launched engine must still be alive: a dead sibling ends the cell now, not after this engine's load
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
  # Fallback for an orphaned rinzler of OURS (absolute binary path and one of our ports).
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2
  pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  for port in 13100 13101; do fusermount3 -uz /var/tmp/jhan/rz-fuse/$port 2>/dev/null; done
  # Remove only the hugepage files that appeared since the first launch, are OURS and are unmapped.
  # The owner test comes first: as jhan, fuser cannot read another user's /proc/<pid>/maps, so it
  # reports a live slice file of rinzler@N (user positron) or of Bill's engine as free, and the
  # 775 root:positron directory would let rm unlink it under the running process (verified 2026-09-08).
  for f in $(ls /dev/hugepages 2>/dev/null | sort); do
    case " $RZ_HP_BEFORE " in *" $f "*) continue ;; esac
    [ -O "/dev/hugepages/$f" ] || { echo "rz_stop_all: $f belongs to $(stat -c %U "/dev/hugepages/$f" 2>/dev/null || echo '?'), left alone"; continue; }
    if fuser -s "/dev/hugepages/$f" 2>/dev/null; then echo "rz_stop_all: $f still mapped - left in place"; else rm -f "/dev/hugepages/$f"; fi
  done
  for f in /dev/hugepages/amx-p0perf13-*; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f"; done
  echo "rz_stop_all: done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
  RZ_PIDS=(); RZ_LOGS=(); RZ_HP_BEFORE=""; RZ_HP_SNAPPED=""
}
