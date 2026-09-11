# rinzler start/stop helpers for the p0perf-20260911 campaign (our half of delphi-3bda).
# Fork of exec/g1-20260908/rz.sh (which forked round 1's exec/more-testing-r1/rz.sh).
# Changes against the G1 version:
#   1. placement = OUR half of the machine (2026-09-06 half-split with Bill): cards
#      90:00.0 93:00.0 b9:00.0 bc:00.0 = FPGA slices 4-7 = socket 1 = cpus 72-143,216-287.
#      tp2 = --instance 2,4 (slices 4-5, cards 90/93), tp4 = --instance 1,2 (slices 4-7).
#      The core lists are round 1's socket-0 lists + 72 (socket 1 mirrors socket 0), and
#      the tp4 line is byte-for-byte the placement the nightly CI's own rinzler uses on
#      socket 1 (seen live 2026-09-11: --instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,
#      bc:00.0 --app-cores 223-224,... --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256).
#   2. one binary, rinzler.p0perf (jhan-amx-p0 head, TRON_AMX_DISPATCH=ON); the AMX-off
#      arm is that binary with TRON_AMX_DISABLE=1 (the kill switch), the AMX-on arm is the
#      same binary with the variable unset.
#   3. the launcher shell is pinned to socket-1 cores 73,217 (G1 used 1,145 on socket 0).
# Kept from G1: `env -u SYSTEM_CONFIG` (the login environment exports "--instance 1,2" and
# tron applies it AFTER the command line), exec so RZ_PID is the rinzler itself, the
# fallback kill matches only OUR binary by absolute path + port, health timeout 600 s,
# stale FUSE mount detached first, owner + fuser test before removing hugepage files.
# Source this file.
#   half_sysargs TP                                -> the placement arguments for tp2 / tp4
#   rz_start ARM PORT TP LOGFILE MODEL [MODEL...]  -> 0 when /v1/models lists every model
#   rz_stop                                        -> stops the process started by rz_start
RZ_BIN=${RZ_BIN:-/var/tmp/jhan/tron-p0perf/gen/rinzler.p0perf}
# Our rinzler by absolute path AND our port: another rinzler started from the same file is left alone.
OUR_RZ_RE='^/var/tmp/jhan/tron-p0perf/gen/rinzler[.]p0perf .*--port 13100( |$)'
RZ_PID=""
RZ_PORT_CUR=""
RZ_HP_BEFORE=""

half_sysargs() {  # $1 = tp
  case $1 in
    2) echo "--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128" ;;
    4) echo "--instance 1,2 --devices 90:00.0,93:00.0,b9:00.0,bc:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131,227-228,108-113,132-137,229-230,114-119,138-143 --dev-cores 75,76,77,78 --numa 1 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}

rz_start() {
  local arm=$1 port=$2 tp=$3 logf=$4; shift 4
  local models=("$@") margs=() sysargs m
  for m in "${models[@]}"; do margs+=(--model "$m"); done
  sysargs=$(half_sysargs "$tp") || { echo "rz_start: bad tp $tp"; return 1; }
  case $arm in off|on) ;; *) echo "rz_start: bad arm $arm"; return 1 ;; esac
  [ -x "$RZ_BIN" ] || { echo "rz_start: binary missing $RZ_BIN"; return 1; }
  # a mount left behind by a SIGKILL would make the next rinzler fail to mount; after a SIGKILL the
  # endpoint answers stat with ENOTCONN, so mountpoint -q would say "no": detach unconditionally.
  fusermount3 -uz /var/tmp/jhan/rz-fuse/$port 2>/dev/null
  mkdir -p /var/tmp/jhan/rz-fuse/$port
  RZ_HP_BEFORE=$(ls /dev/hugepages 2>/dev/null | sort | tr '\n' ' ')
  RZ_PORT_CUR=$port
  # Same environment platformd gives production engines, plus the arm's switch.
  # USE_HW_ATTN=0 = CPU attention (AMX can only engage there; unset, the ingested qwen
  # model would default to FPGA attention). TRON_LOG_LEVEL / SPDLOG_LEVEL are pinned to
  # what the login environment exports (debug), the same as round 1 and G1 ran.
  # PATH is left alone on purpose (fusermount3 trap, see round 1's rz.sh).
  local envc=(env -u TRON_AMX_DISABLE -u SYSTEM_CONFIG USE_HW_ATTN=0
              TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug
              RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$port
              RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  [ "$arm" = off ] && envc+=(TRON_AMX_DISABLE=1)
  # Production engines run under systemd with no memlock limit; an interactive user shell is
  # capped (round 1: "hugepages capped by ulimit constraints to 188 of 256").
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "rz_start: could not raise memlock limit"
  echo "rz_start arm=$arm tp=$tp port=$port bin=$RZ_BIN models=${models[*]} memlock=$(ulimit -l) $(date -u +%FT%TZ)"
  # exec: the background job IS the env -> taskset -> rinzler chain, so RZ_PID is rinzler.
  # the background subshell closes the inherited campaign flock fd first: an orphaned rinzler (after a kill -9 of the
  # campaign) must not keep the flock; `exec {VAR}>&-` needs the variable set, hence the guard (review 2026-09-11, C10)
  (cd "$(dirname "$RZ_BIN")/.." || exit 1
   [ -n "${CAMPAIGN_LOCK_FD:-}" ] && exec {CAMPAIGN_LOCK_FD}>&-
   exec "${envc[@]}" taskset -c 73,217 "$RZ_BIN" "${margs[@]}" --port "$port" $sysargs \
      --hugepage_file /dev/hugepages/amx-p0perf-$port >"$logf" 2>&1) &
  RZ_PID=$!
  # health: every model id listed by /v1/models, then one warm-up completion per model
  local deadline=$(( $(date +%s) + ${RZ_HEALTH_SEC:-600} )) ok
  while :; do
    if ! kill -0 "$RZ_PID" 2>/dev/null; then echo "rz_start: rinzler exited early"; tail -20 "$logf"; return 1; fi
    ok=1
    for m in "${models[@]}"; do
      curl -s -m 5 "http://127.0.0.1:$port/v1/models" | grep -q "\"$m\"" || ok=0
    done
    [ "$ok" = 1 ] && break
    [ "$(date +%s)" -ge "$deadline" ] && { echo "rz_start: health timeout"; tail -20 "$logf"; return 1; }
    sleep 5
  done
  for m in "${models[@]}"; do
    curl -s -m 120 "http://127.0.0.1:$port/v1/chat/completions" -H 'Content-Type: application/json' \
      -d "{\"model\":\"$m\",\"messages\":[{\"role\":\"user\",\"content\":\"Say hello.\"}],\"max_tokens\":8}" \
      | head -c 300; echo
  done
  echo "rz_start: ready $(date -u +%FT%TZ)"
  return 0
}

rz_stop() {
  local f
  if [ -n "$RZ_PID" ] && kill -0 "$RZ_PID" 2>/dev/null; then
    kill -TERM "$RZ_PID" 2>/dev/null
    for _ in $(seq 1 60); do kill -0 "$RZ_PID" 2>/dev/null || break; sleep 1; done
    kill -0 "$RZ_PID" 2>/dev/null && { echo "rz_stop: SIGKILL"; kill -KILL "$RZ_PID" 2>/dev/null; sleep 2; }
    wait "$RZ_PID" 2>/dev/null
  fi
  # Fallback for an orphaned rinzler of OURS (matched by its absolute binary path and port).
  pkill -TERM -u jhan -f "$OUR_RZ_RE" 2>/dev/null; sleep 2
  pkill -KILL -u jhan -f "$OUR_RZ_RE" 2>/dev/null
  [ -n "$RZ_PORT_CUR" ] && fusermount3 -uz /var/tmp/jhan/rz-fuse/$RZ_PORT_CUR 2>/dev/null
  # Remove only the hugepage files that appeared during this run, are OURS and are unmapped. The owner
  # test comes first: as jhan, fuser cannot read another user's /proc/<pid>/maps, so it reports a live
  # slice file of rinzler@N (user positron) or of Bill's engine as free, and the 775 root:positron
  # directory (no sticky bit; jhan is in group positron) would let rm unlink it under the running
  # process (verified 2026-09-08).
  for f in $(ls /dev/hugepages 2>/dev/null | sort); do
    case " $RZ_HP_BEFORE " in *" $f "*) continue ;; esac
    [ -O "/dev/hugepages/$f" ] || { echo "rz_stop: $f belongs to $(stat -c %U "/dev/hugepages/$f" 2>/dev/null || echo '?'), left alone"; continue; }
    if fuser -s "/dev/hugepages/$f" 2>/dev/null; then echo "rz_stop: $f still mapped - left in place"; else rm -f "/dev/hugepages/$f"; fi
  done
  for f in /dev/hugepages/amx-p0perf-*; do [ -e "$f" ] && [ -O "$f" ] && ! fuser -s "$f" 2>/dev/null && rm -f "$f"; done
  echo "rz_stop: done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
  RZ_PID=""; RZ_PORT_CUR=""
}
