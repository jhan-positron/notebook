#!/usr/bin/env bash
set -euo pipefail

label="${1:?usage: run_ci32u_with_sidecars.sh LABEL RUN_DIR}"
run_dir="${2:?usage: run_ci32u_with_sidecars.sh LABEL RUN_DIR}"

repo="${TRON_REPO:-/home/jhan/workspace/tron}"
ISST="${ISST:-/home/jhan/workspace/intel-vs-amd/speed-select/workspace/flat_freq/20260623_codex_preserved_tmp/intel-speed-select-v6.8/intel-speed-select}"
ANCHORS="${ANCHORS:-24 48 72 96}"
COOLDOWN_SEC="${COOLDOWN_SEC:-30}"
SIDECAR_CPUSET="${SIDECAR_CPUSET:-0,144}"

logs_dir="$run_dir/logs"
bench_dir="$run_dir/benchmarks"
state_dir="$run_dir/state"
summary_dir="$run_dir/summaries"
script_dir="$run_dir/scripts"
out_dir="$bench_dir/${label}_benchmark_run"
stats_dir="$out_dir/stats"

mkdir -p "$logs_dir" "$bench_dir" "$state_dir" "$summary_dir" "$out_dir" "$stats_dir"

thread_shape="$bench_dir/${label}_thread_freq_shape.csv"
freq_shape="$bench_dir/${label}_freq_all_cpus.csv"
status_file="$bench_dir/${label}_status.txt"
turbostat_file="$bench_dir/${label}_turbostat.log"
perf_file="$bench_dir/${label}_perf_stat.csv"
perf_events_file="$bench_dir/${label}_perf_events.txt"
run_stdout="$logs_dir/${label}_benchmark_stdout.log"
run_stderr="$logs_dir/${label}_benchmark_stderr.log"
policy_before="$state_dir/${label}_policy_before.log"
policy_after="$state_dir/${label}_policy_after.log"
tsx_log="$state_dir/${label}_tsx_evidence.log"
summary_json="$summary_dir/${label}_ci_metrics.json"
summary_txt="$summary_dir/${label}_ci_metrics.txt"

cpu_list="
24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47
48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63 64 65 66 67 68 69 70 71
72 73 74 75 76 77 78 79 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95
96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111 112 113 114 115 116 117 118 119
168 169 170 171 172 173 174 175 176 177 178 179 180 181 182 183 184 185 186 187 188 189 190 191
192 193 194 195 196 197 198 199 200 201 202 203 204 205 206 207 208 209 210 211 212 213 214 215
216 217 218 219 220 221 222 223 224 225 226 227 228 229 230 231 232 233 234 235 236 237 238 239
240 241 242 243 244 245 246 247 248 249 250 251 252 253 254 255 256 257 258 259 260 261 262 263
"

cpu_role() {
  local cpu="$1"
  if (( cpu >= 24 && cpu <= 47 )) || (( cpu >= 168 && cpu <= 191 )); then
    printf 'domain0_anchor24'
  elif (( cpu >= 48 && cpu <= 71 )) || (( cpu >= 192 && cpu <= 215 )); then
    printf 'domain1_anchor48'
  elif (( cpu >= 72 && cpu <= 95 )) || (( cpu >= 216 && cpu <= 239 )); then
    printf 'domain2_anchor72'
  elif (( cpu >= 96 && cpu <= 119 )) || (( cpu >= 240 && cpu <= 263 )); then
    printf 'domain3_anchor96'
  else
    printf 'other'
  fi
}

thread_kind() {
  case "$1" in
    *TX*) printf 'tx' ;;
    *RX*) printf 'rx' ;;
    *Main*) printf 'main' ;;
    *work_queue*) printf 'work_queue' ;;
    *worker*) printf 'app_worker' ;;
    *) printf 'other' ;;
  esac
}

extract_instance() {
  local args="$1"
  if [[ "$args" =~ --instance[[:space:]]+([0-9]+,[0-9]+) ]]; then
    local instance="${BASH_REMATCH[1]}"
    printf '%s' "${instance/,/\/}"
  else
    printf 'unknown'
  fi
}

build_perf_events() {
  local events=(
    task-clock
    cycles
    instructions
    ref-cycles
    context-switches
    cpu-migrations
    branches
    branch-misses
  )
  local maybe=(
    rtm_retired.start
    rtm_retired.commit
    rtm_retired.aborted
    tx_mem.abort_conflict
    tx_mem.abort_capacity
  )
  for ev in "${maybe[@]}"; do
    if /usr/bin/perf list "$ev" 2>/dev/null | rg -q "(^|[[:space:]])${ev//./\\.}([[:space:]]|$)"; then
      events+=("$ev")
    fi
  done
  IFS=,
  printf '%s' "${events[*]}"
}

sample_loop() {
  local watched_pid="$1"
  local sample_idx=0
  printf 'sample_epoch,sample_idx,pid,tid,cpu,pcpu,thread_name,thread_kind,instance,cpu_role,scaling_cur_khz\n' > "$thread_shape"
  printf 'sample_epoch,sample_idx,cpu,cpu_role,scaling_cur_khz\n' > "$freq_shape"
  while kill -0 "$watched_pid" 2>/dev/null; do
    local now
    now="$(date +%s)"
    for cpu in $cpu_list; do
      local freq_path="/sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_cur_freq"
      local freq=""
      [[ -r "$freq_path" ]] && freq="$(cat "$freq_path")"
      printf '%s,%s,%s,%s,%s\n' "$now" "$sample_idx" "$cpu" "$(cpu_role "$cpu")" "$freq" >> "$freq_shape"
    done

    ps -eLo pid=,tid=,psr=,pcpu=,comm=,args= |
      awk '/gen\/runtron/ { print }' |
      while read -r pid tid cpu pcpu comm args; do
        local freq_path="/sys/devices/system/cpu/cpu${cpu}/cpufreq/scaling_cur_freq"
        local freq=""
        [[ -r "$freq_path" ]] && freq="$(cat "$freq_path")"
        printf '%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s\n' \
          "$now" "$sample_idx" "$pid" "$tid" "$cpu" "$pcpu" "$comm" \
          "$(thread_kind "$comm")" "$(extract_instance "$args")" "$(cpu_role "$cpu")" "$freq" >> "$thread_shape"
      done
    sample_idx=$((sample_idx + 1))
    sleep 1
  done
}

stop_sidecar() {
  local pid="${1:-}"
  [[ -n "$pid" ]] || return 0
  if kill -0 "$pid" 2>/dev/null; then
    local pids="$pid"
    local frontier="$pid"
    local next children leaves
    while [[ -n "$frontier" ]]; do
      next=""
      for p in $frontier; do
        children="$(pgrep -P "$p" 2>/dev/null || true)"
        if [[ -n "$children" ]]; then
          pids="$pids $children"
          next="$next $children"
        fi
      done
      frontier="$next"
    done
    leaves=""
    for p in $pids; do
      children="$(pgrep -P "$p" 2>/dev/null || true)"
      [[ -z "$children" ]] && leaves="$leaves $p"
    done
    # turbostat/perf flush cleanly when their sleep child exits normally.
    [[ -n "$leaves" ]] && sudo -n /usr/bin/kill -TERM $leaves 2>/dev/null || true
    sleep 1
    sudo -n /usr/bin/kill -INT $pids 2>/dev/null || kill -INT $pids 2>/dev/null || true
    sleep 1
    sudo -n /usr/bin/kill -TERM $pids 2>/dev/null || kill -TERM $pids 2>/dev/null || true
    wait "$pid" 2>/dev/null || true
  fi
}

{
  echo "label=$label"
  echo "run_dir=$run_dir"
  echo "repo=$repo"
  echo "started_epoch=$(date +%s)"
  echo "cooldown_sec=$COOLDOWN_SEC"
  echo "sidecar_cpuset=$SIDECAR_CPUSET"
  echo "anchors=$ANCHORS"
} > "$status_file"

"$script_dir/collect_policy_snapshot.sh" "$policy_before" $cpu_list

{
  echo "timestamp=$(date -Is)"
  echo "== lscpu TSX flags =="
  lscpu | sed -n '/^Flags:/p;/^Vulnerability Tsx async abort:/p'
  echo
  echo "TSX/RTM annotation:"
  echo "This platform exposes waitpkg and tsxldtrk but not rtm/hle in lscpu flags."
  echo "RTM/HLE transactional execution is therefore expected unavailable; RTM counters are collected only as platform evidence and may be absent or zero."
  echo
  echo "== run logs will be searched for RTM support after run =="
  echo
  echo "== perf list RTM/TX_MEM =="
  /usr/bin/perf list rtm_retired 2>/dev/null || true
  /usr/bin/perf list tx_mem 2>/dev/null || true
} > "$tsx_log"

perf_events="$(build_perf_events)"
printf '%s\n' "$perf_events" > "$perf_events_file"
sudo -n /usr/sbin/sysctl kernel.perf_event_paranoid=-1 >> "$status_file" 2>&1 || true

taskset -c "$SIDECAR_CPUSET" sudo -n /usr/bin/turbostat --quiet --interval 1 --out "$turbostat_file" sleep 86400 &
turbostat_pid="$!"

taskset -c "$SIDECAR_CPUSET" sudo -n /usr/bin/perf stat -a -I 1000 -x, -o "$perf_file" -e "$perf_events" sleep 86400 &
perf_pid="$!"

sample_pid=""
rc=0
trap 'stop_sidecar "$sample_pid"; stop_sidecar "$turbostat_pid"; stop_sidecar "$perf_pid"' EXIT

if (( COOLDOWN_SEC > 0 )); then
  echo "Instrumented idle/settle window for ${COOLDOWN_SEC}s before $label"
  echo "idle_settle_started_epoch=$(date +%s)" >> "$status_file"
  sleep "$COOLDOWN_SEC"
  echo "idle_settle_finished_epoch=$(date +%s)" >> "$status_file"
fi

cmd="unset SYSTEM_CONFIG; unset RZ_FUSE_MOUNT_PRESCOPED; export RZ_FUSE_MOUNT_PATH='$stats_dir'; mkdir -p '$stats_dir'; cd '$repo' && python3 bin/ci/benchmark_run.py -m llama-3.2-3b-instruct-fast -tp 2 -spl 800 -pl 199 -l 335 -p 32 -i 4 -c 144 -f 8 --isolated-iterations 5 --repeats 1 --output-dir '$out_dir'"
echo "command=sg positron -c $cmd" >> "$status_file"
echo "benchmark_started_epoch=$(date +%s)" >> "$status_file"

sg positron -c "$cmd" > "$run_stdout" 2> "$run_stderr" &
bench_pid="$!"

sample_loop "$bench_pid" &
sample_pid="$!"
taskset -pc "$SIDECAR_CPUSET" "$sample_pid" >> "$status_file" 2>&1 || true

wait "$bench_pid" || rc="$?"
echo "benchmark_finished_epoch=$(date +%s)" >> "$status_file"
echo "benchmark_exit_code=$rc" >> "$status_file"

stop_sidecar "$sample_pid"
sample_pid=""
stop_sidecar "$turbostat_pid"
stop_sidecar "$perf_pid"
trap - EXIT

"$script_dir/collect_policy_snapshot.sh" "$policy_after" $cpu_list

{
  echo
  echo "== run logs RTM support search =="
  rg -n "INIT: Intel RTM \\(TSX\\) supported|RTM|TSX" "$out_dir" "$run_stdout" "$run_stderr" 2>/dev/null || true
} >> "$tsx_log"

python3 "$script_dir/summarize_ci32u_run.py" "$out_dir" "$summary_json" > "$summary_txt" 2>&1 || {
  summarize_rc="$?"
  echo "summary_exit_code=$summarize_rc" >> "$status_file"
  cat "$summary_txt"
  exit "$rc"
}

cat "$summary_txt"
echo "finished_epoch=$(date +%s)" >> "$status_file"
exit "$rc"
