# rinzler start/stop helpers for the more-testing campaign. Source this file.
# rz_start ARM PORT TP LOGFILE MODEL [MODEL...]  -> 0 when /v1/models lists every model
# rz_stop                                        -> stops the process started by rz_start
TRON=~/workspace/tron-amx
RZ_PID=""
RZ_PORT_CUR=""
RZ_HP_BEFORE=""

rz_sysargs() {  # $1 = tp
  case $1 in
    2) echo "--instance 0,4 --devices 10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59 --dev-cores 3,4 --numa 0 --nr_hugepages 128" ;;
    4) echo "--instance 0,2 --devices 38:00.0,3b:00.0,10:00.0,13:00.0 --app-cores 151-152,24-29,48-53,153-154,30-35,54-59,155-156,36-41,60-65,157-158,42-47,66-71 --dev-cores 3,4,5,6 --numa 0 --nr_hugepages 256" ;;
    *) return 1 ;;
  esac
}

rz_start() {
  local arm=$1 port=$2 tp=$3 logf=$4; shift 4
  local models=("$@") margs=() bin sysargs m
  for m in "${models[@]}"; do margs+=(--model "$m"); done
  sysargs=$(rz_sysargs "$tp") || { echo "rz_start: bad tp $tp"; return 1; }
  case $arm in
    off|canon) bin=$TRON/gen/rinzler.canon ;;
    mirror)    bin=$TRON/gen/rinzler.mirror ;;
    *) echo "rz_start: bad arm $arm"; return 1 ;;
  esac
  mkdir -p /var/tmp/jhan/rz-fuse/$port
  RZ_HP_BEFORE=$(ls /dev/hugepages 2>/dev/null | sort | tr '\n' ' ')
  RZ_PORT_CUR=$port
  # Same environment platformd gives production engines, plus the arm's
  # switches. USE_HW_ATTN=0 = CPU attention for every model (AMX can only
  # engage there). The off arm sets the kill switch to exactly "1"; the
  # other arms unset it so a leaked value cannot disable AMX silently.
  # PATH is left alone on purpose: libfuse execs `fusermount3` from PATH, and
  # /usr/bin/fusermount3 (Ubuntu) honours user_allow_other in /etc/fuse.conf,
  # while /opt/positron/bin/fusermount3 looks for /usr/local/etc/fuse.conf
  # (absent here) and refuses allow_other for a non-root user (smoke 17:50Z).
  local envc=(env -u TRON_AMX_DISABLE USE_HW_ATTN=0 RZ_FUSE_MOUNT_PATH=/var/tmp/jhan/rz-fuse/$port
              RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0)
  [ "$arm" = off ] && envc+=(TRON_AMX_DISABLE=1)
  # Production engines run under systemd with no memlock limit; an interactive
  # user shell is capped (rinzler logged "hugepages capped by ulimit constraints
  # to 188 of 256" in the smoke run), so lift the limit for this shell and its
  # children (jhan has passwordless sudo on this host).
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || echo "rz_start: could not raise memlock limit"
  echo "rz_start arm=$arm tp=$tp port=$port bin=$(basename "$bin") models=${models[*]} memlock=$(ulimit -l) $(date -u +%FT%TZ)"
  (cd "$TRON" && "${envc[@]}" taskset -c 1,145 "$bin" "${margs[@]}" --port "$port" $sysargs \
      --hugepage_file /dev/hugepages/amx-mt-$port >"$logf" 2>&1) &
  RZ_PID=$!
  # health: every model id listed by /v1/models, then one warm-up completion
  local deadline=$(( $(date +%s) + 1800 )) ok
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
  # The taskset/env wrapper is our child; the rinzler binary is its child.
  pkill -TERM -x 'rinzler(\.canon|\.mirror)?' 2>/dev/null; sleep 2
  pkill -KILL -x 'rinzler(\.canon|\.mirror)?' 2>/dev/null
  [ -n "$RZ_PORT_CUR" ] && fusermount3 -u /var/tmp/jhan/rz-fuse/$RZ_PORT_CUR 2>/dev/null
  # remove only the hugepage files that appeared during this run and are unmapped
  for f in $(ls /dev/hugepages 2>/dev/null | sort); do
    case " $RZ_HP_BEFORE " in *" $f "*) continue ;; esac
    if fuser -s "/dev/hugepages/$f" 2>/dev/null; then echo "rz_stop: $f still mapped - left in place"; else rm -f "/dev/hugepages/$f"; fi
  done
  rm -f /dev/hugepages/amx-mt-* 2>/dev/null
  echo "rz_stop: done $(date -u +%FT%TZ); $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
  RZ_PID=""; RZ_PORT_CUR=""
}
