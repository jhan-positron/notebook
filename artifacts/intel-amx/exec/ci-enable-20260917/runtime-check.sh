#!/usr/bin/env bash
# ci-enable-20260917/runtime-check.sh: run ON delphi-3bda, our half only (socket 1, cards 90/93).
#
# Question: does the rinzler binary inside the .deb built from the AMX-enabled "deb" preset
# use AMX at run time with qwen3-4b, and does the kill switch turn it off?
#
# Words used here: rinzler = the production server binary (the .deb ships it; the nightly runs
# it); AMX = Intel matrix instructions; TRON_AMX_DISABLE=1 = the run-time kill switch;
# USE_HW_ATTN=0 = attention on the CPU (the only place the AMX kernels run); "default" =
# neither variable set, which is how the nightly runs the ingested qwen model (attention on the
# FPGA from query position 127 on, positions 0-126 on the CPU); the probe = tron's one-time
# AMX check, visible as the system call arch_prctl(0x1023, 18) (logged by the amxprobe shim);
# EXE.AMX_BUSY = the CPU counter "cycles in which the AMX unit is busy" (perf raw event
# cpu/event=0xb7,umask=0x02 on Granite Rapids), validated on this host on 2026-09-17: 20 M tile
# multiplies -> 320 M busy cycles, a scalar loop -> 0, the production rinzler without AMX
# code -> 0 in 3 s; usable only in per-process mode (-p PID; system-wide mode counts on idle
# cores).
#
# Arms (one engine each, started and stopped in turn):
#   cpu-on   USE_HW_ATTN=0                        expect: probe line "= 0", AMX_BUSY > 0
#   cpu-off  USE_HW_ATTN=0 TRON_AMX_DISABLE=1     expect: no probe line, AMX_BUSY = 0
#   default  (both unset, the nightly's setting)  reports what happens; not a pass/fail arm
# Evidence per arm: /proc/PID/exe and the "Version:" banner (which binary served), the probe
# file, perf stat of EXE.AMX_BUSY over the request window and over an idle window, the
# answers and rough speed of 3 requests (single user, prompt about 1000 tokens, 160 new
# tokens; speed includes the prompt phase, so it is a rough number, not a TPS measurement).
#
# Machine rules honoured: CI lease must be clear; another person (not Bill: our half is not
# his) must be idle; campaign flock; our half only (--instance 2,4, cards 90:00.0,93:00.0,
# socket-1 cores, 128 hugepages of the 256 free ones); the production unit rinzler@N on the
# other half is left alone; `env -u SYSTEM_CONFIG` on the engine (the login environment
# exports "--instance 1,2", which tron applies AFTER the command line).
set -u
EXEC=/home/jhan/workspace/intel-AMX/exec
WT=${WT:-/var/tmp/jhan/tron-ci-enable}
OUT=${OUT:-/var/tmp/jhan/ci-enable-out}          # local disk: rinzler logs are large at debug level
RES=${RES:-$EXEC/results/ci-enable-20260917}     # NFS: summaries and small files
ROOT=${ROOT:-/var/tmp/jhan/ci-enable-root}       # the .deb extracted here
SHIM=/var/tmp/jhan/amxprobe-3bda.so
MODEL=${MODEL:-ingested-qwen-3-4b-instruct-2507-tp2}
PORT=13100
NEW_TOKENS=${NEW_TOKENS:-160}
PERF_EVENT='cpu/event=0xb7,umask=0x02,name=exe_amx_busy/'
ts() { date -u +%FT%TZ; }
say() { echo "$(ts) $*"; }
mkdir -p "$OUT" "$RES"
exec > >(tee -a "$RES/runtime-check.log") 2>&1
say "=== runtime-check start host=$(hostname) model=$MODEL"

# ---------- the package ----------
DEB=$(ls -1 "$WT"/gen-deb/tron_*_amd64.deb 2>/dev/null | head -1)
[ -f "$DEB" ] || { say "ABORT: no .deb under $WT/gen-deb"; exit 1; }
say "deb: $DEB ($(stat -c %s "$DEB") bytes) sha256 $(sha256sum "$DEB" | cut -c1-64)"
rm -rf "$ROOT"; mkdir -p "$ROOT"; dpkg-deb -x "$DEB" "$ROOT" || { say "ABORT: dpkg-deb -x failed"; exit 1; }
RZ_BIN=$ROOT/opt/positron/bin/rinzler
[ -x "$RZ_BIN" ] || { say "ABORT: $RZ_BIN missing"; exit 1; }
say "package rinzler: $(stat -c %s "$RZ_BIN") bytes sha256 $(sha256sum "$RZ_BIN" | cut -c1-64)"
say "binary check: TRON_AMX_DISABLE text $(strings "$RZ_BIN" | grep -c -x TRON_AMX_DISABLE) (expect 1); AMX instructions $(objdump -d --no-show-raw-insn "$RZ_BIN" | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)') (expect about 86); nm symbols: $(nm -C --defined-only "$RZ_BIN" 2>&1 | grep -c amx_attn) (stripped -> 0)"
say "installed package for comparison: $(dpkg -l tron | tail -1 | awk '{print $3}'): TRON_AMX_DISABLE text $(strings /opt/positron/bin/rinzler | grep -c -x TRON_AMX_DISABLE), AMX instructions $(objdump -d --no-show-raw-insn /opt/positron/bin/rinzler | grep -c -E '(tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease)')"

# ---------- machine guards (our half) ----------
source "$EXEC/lib-guard.sh"
export GUARD_EXCLUDE_USERS="jhan nobody positron packer bill"
if ci_lease_busy; then say "ABORT: CI lease busy"; exit 2; fi
if other_user_active; then say "ABORT: another person is active (see GUARD line)"; exit 2; fi
exec {LOCK_FD}>/var/tmp/jhan/3bda-campaign.lock
flock -n "$LOCK_FD" || { say "ABORT: campaign flock held by another session"; exit 2; }
pgrep -u jhan -x 'runtron(\.[a-z0-9]+)?' >/dev/null && { say "ABORT: a runtron of ours is running"; exit 2; }
pgrep -u jhan -f -- "--port $PORT( |$)" >/dev/null && { say "ABORT: something of ours already listens on port $PORT"; exit 2; }
free_hp=$(awk '/^HugePages_Free/ {print $2}' /proc/meminfo)
[ "$free_hp" -ge 128 ] || { say "ABORT: only $free_hp free hugepages (need 128)"; exit 2; }
say "guards: lease clear, nobody else active, flock taken, $free_hp free hugepages; production units: $(systemctl list-units 'rinzler@*' --no-legend --plain 2>/dev/null | awk '{print $1":"$3}' | tr '\n' ' ')(left alone, other half)"
[ -x "$SHIM" ] || { say "ABORT: shim $SHIM missing"; exit 1; }

# ---------- one engine on our half (placement = the nightly's socket-1 tp2 engine, first half of the tp4 lists) ----------
SYSARGS="--instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 --dev-cores 75,76 --numa 1 --nr_hugepages 128"
LAUNCH_CORES=73,217
CLIENT_CORES=87-95
HP_FILE=/dev/hugepages/ci-enable-$PORT
FUSE_DIR=/var/tmp/jhan/rz-fuse/$PORT
RZ_PID=""
PROMPT_FILE=$OUT/prompt.txt
# a prompt of about 1000 tokens: the 132-word text of exec/t1-prompt.txt repeated, so the
# context spans well over a dozen 64-token KV pages when decoding starts
python3 - "$EXEC/t1-prompt.txt" "$PROMPT_FILE" <<'PY'
import sys
t = open(sys.argv[1]).read().strip()
body = ("\n\n".join([t] * 6))
open(sys.argv[2], "w").write("Read the following text carefully, then summarise it in five sentences.\n\n" + body)
PY
say "prompt: $(wc -w < "$PROMPT_FILE") words"

rz_start() {  # ARM -> starts the engine, sets RZ_PID
  local arm=$1 logf=$OUT/$arm.rinzler.log probe=$OUT/$arm.probe
  rm -f "$probe"
  fusermount3 -uz "$FUSE_DIR" 2>/dev/null; mkdir -p "$FUSE_DIR"
  local envc=(env -u TRON_AMX_DISABLE -u USE_HW_ATTN -u SYSTEM_CONFIG
              TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug
              RZ_FUSE_MOUNT_PATH=$FUSE_DIR RZ_FUSE_MOUNT_PRESCOPED=1 RZ_ENABLE_SAVE_TOKENS=1 TRON_USE_SPECULATION=0
              LD_LIBRARY_PATH=$ROOT/opt/positron/lib LD_PRELOAD=$SHIM AMXPROBE_FILE=$probe)
  case $arm in
    cpu-on)  envc+=(USE_HW_ATTN=0) ;;
    cpu-off) envc+=(USE_HW_ATTN=0 TRON_AMX_DISABLE=1) ;;
    default) ;;
    *) say "rz_start: bad arm $arm"; return 1 ;;
  esac
  sudo -n prlimit --pid $$ --memlock=unlimited:unlimited 2>/dev/null || say "rz_start: could not raise memlock limit"
  say "rz_start arm=$arm port=$PORT bin=$RZ_BIN memlock=$(ulimit -l)"
  (cd "$ROOT/opt/positron" || exit 1
   exec {LOCK_FD}>&-
   exec "${envc[@]}" taskset -c "$LAUNCH_CORES" "$RZ_BIN" --model "$MODEL" --port "$PORT" $SYSARGS \
      --hugepage_file "$HP_FILE" >"$logf" 2>&1) &
  RZ_PID=$!
  local deadline=$(( $(date +%s) + 600 ))
  while :; do
    kill -0 "$RZ_PID" 2>/dev/null || { say "rz_start: rinzler exited early"; tail -30 "$logf"; return 1; }
    curl -s -m 5 "http://127.0.0.1:$PORT/v1/models" | grep -q "\"$MODEL\"" && break
    [ "$(date +%s)" -ge "$deadline" ] && { say "rz_start: health timeout"; tail -30 "$logf"; return 1; }
    sleep 5
  done
  say "rz_start: engine up, pid $RZ_PID exe=$(readlink /proc/$RZ_PID/exe)"
  grep -m1 -E "Version:" "$logf" | sed -E 's/.*(Version:.*)/\1/' | cut -c1-120
  grep -m1 -E "HW attention (dis|en)abled" "$logf" | sed -E 's/.*\] //' | cut -c1-160 || true
  return 0
}
rz_stop() {
  [ -n "$RZ_PID" ] || return 0
  kill -TERM "$RZ_PID" 2>/dev/null
  for _ in $(seq 1 60); do kill -0 "$RZ_PID" 2>/dev/null || break; sleep 1; done
  kill -0 "$RZ_PID" 2>/dev/null && { say "rz_stop: SIGKILL"; kill -KILL "$RZ_PID" 2>/dev/null; sleep 2; }
  wait "$RZ_PID" 2>/dev/null
  fusermount3 -uz "$FUSE_DIR" 2>/dev/null
  # tron names its hugepage files by slice (slice-4-of-8, slice-5-of-8 for --instance 2,4), not by
  # the --hugepage_file argument. The first run (2026-09-17 19:46 UTC) left those two files behind
  # (128 pages held until removed by hand). Remove every slice file that is ours and unmapped.
  local f
  for f in "$HP_FILE" /dev/hugepages/slice-*-of-8; do
    [ -e "$f" ] && [ -O "$f" ] || continue
    if fuser -s "$f" 2>/dev/null; then say "rz_stop: $f still mapped, left in place"; else rm -f "$f" && say "rz_stop: removed $f"; fi
  done
  say "rz_stop: done; $(grep -E '^HugePages_Free' /proc/meminfo | xargs)"
  RZ_PID=""
}
trap 'rz_stop' EXIT

ask() {  # $1 tag -> one chat completion; prints "tokens seconds tok/s" and stores the answer
  local tag=$1 t0 t1 resp ntok
  t0=$(date +%s.%N)
  resp=$(python3 - "$PROMPT_FILE" "$MODEL" "$NEW_TOKENS" <<'PY' | taskset -c "$CLIENT_CORES" curl -s -m 600 "http://127.0.0.1:$PORT/v1/chat/completions" -H 'Content-Type: application/json' -d @-
import json, sys
p = open(sys.argv[1]).read()
print(json.dumps({"model": sys.argv[2], "messages": [{"role": "user", "content": p}], "max_tokens": int(sys.argv[3]), "temperature": 0}))
PY
)
  t1=$(date +%s.%N)
  printf '%s\n' "$resp" >"$OUT/$tag.json"
  ntok=$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("usage",{}).get("completion_tokens","?"))' "$OUT/$tag.json" 2>/dev/null || echo "?")
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d["choices"][0]["message"]["content"][:160].replace("\n"," "))' "$OUT/$tag.json" >"$OUT/$tag.answer" 2>/dev/null || echo "(no answer: $(head -c 200 "$OUT/$tag.json"))" >"$OUT/$tag.answer"
  python3 -c "t=$t1-$t0; n='$ntok'; print(f'{n} tokens in {t:.2f} s = {(int(n)/t if n.isdigit() else 0):.1f} tok/s (prompt phase included)')"
}

perf_window() {  # $1 file $2 seconds -> perf stat on the engine for that long, in the background (pid in PERF_PID)
  sudo -n perf stat -e "$PERF_EVENT" -e cycles -e instructions -x, -p "$RZ_PID" -o "$1" -- sleep "$2" &
  PERF_PID=$!
}
perf_read() {  # $1 file -> "exe_amx_busy=N cycles=M"
  awk -F, '$3=="exe_amx_busy"{a=$1} $3=="cycles"{c=$1} END{printf "exe_amx_busy=%s cycles=%s", a, c}' "$1"
}

SUMMARY=$RES/summary.tsv
echo -e "arm\tprobe_line\tamx_busy_idle10s\tcycles_idle10s\tamx_busy_requests\tcycles_requests\treq1\treq2\treq3\texe\tversion" >"$SUMMARY"
for arm in cpu-on cpu-off default; do
  say "===== arm $arm ====="
  rz_start "$arm" || { say "arm $arm: engine failed to start"; rz_stop; echo -e "$arm\tSTART-FAILED" >>"$SUMMARY"; continue; }
  exe=$(readlink /proc/$RZ_PID/exe); ver=$(grep -m1 -o -E "Version: [^ ]+" "$OUT/$arm.rinzler.log" | head -1)
  say "warm-up request:"; ask "$arm.warmup"
  say "idle window 10 s (no requests):"; perf_window "$OUT/$arm.perf-idle" 10; wait "$PERF_PID"; idle=$(perf_read "$OUT/$arm.perf-idle"); say "  $idle"
  say "request window: 3 requests inside a 90 s perf stat window"
  perf_window "$OUT/$arm.perf-req" 90
  r1=$(ask "$arm.r1"); say "  r1: $r1"
  r2=$(ask "$arm.r2"); say "  r2: $r2"
  r3=$(ask "$arm.r3"); say "  r3: $r3"
  say "  waiting for the perf window to close"; wait "$PERF_PID"; req=$(perf_read "$OUT/$arm.perf-req"); say "  $req"
  say "  answer (first 160 chars): $(cat "$OUT/$arm.r1.answer")"
  probe_line=$(grep -h "arch_prctl" "$OUT/$arm.probe" 2>/dev/null | head -1); [ -n "$probe_line" ] || probe_line="(no arch_prctl line; shim loaded: $(grep -c 'loaded in pid' "$OUT/$arm.probe" 2>/dev/null || echo 0) lines)"
  say "  probe: $probe_line"
  grep -c -i -E "illegal|SIGILL|abort|terminate" "$OUT/$arm.rinzler.log" | sed 's/^/  crash words in the engine log: /'
  idle_busy=${idle#exe_amx_busy=}; idle_busy=${idle_busy%% *}; idle_cyc=${idle##*cycles=}
  req_busy=${req#exe_amx_busy=}; req_busy=${req_busy%% *}; req_cyc=${req##*cycles=}
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$arm" "$probe_line" "$idle_busy" "$idle_cyc" "$req_busy" "$req_cyc" "$r1" "$r2" "$r3" "$exe" "$ver" >>"$SUMMARY"
  rz_stop
done
say "answers identical cpu-on vs cpu-off (r1)? $(cmp -s <(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["choices"][0]["message"]["content"])' "$OUT/cpu-on.r1.json") <(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["choices"][0]["message"]["content"])' "$OUT/cpu-off.r1.json") && echo yes || echo no) (not proof either way: AMX and AVX results differ in the last bit)"
cp -f "$OUT"/*.probe "$OUT"/*.perf-* "$OUT"/*.answer "$RES"/ 2>/dev/null
for arm in cpu-on cpu-off default; do grep -E "HW attention|Version:|amxprobe|AMX|amx" "$OUT/$arm.rinzler.log" | head -12 >"$RES/$arm.rinzler-lines.txt" 2>/dev/null; done
say "=== runtime-check done; summary:"; cat "$SUMMARY"
