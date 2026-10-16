#!/usr/bin/env bash
set -euo pipefail

out="${1:?usage: collect_policy_snapshot.sh OUT_FILE}"
shift || true
cpus=("${@:-24 48 72 96}")

{
  echo "timestamp=$(date -Is)"
  echo
  echo "== lscpu model/flags =="
  lscpu | awk '/^(Architecture|CPU\(s\)|Thread\(s\) per core|Core\(s\) per socket|Socket\(s\)|NUMA node\(s\)|Model name|Flags|Vulnerability Tsx async abort):/'
  echo
  echo "== intel_pstate =="
  for p in \
    /sys/devices/system/cpu/intel_pstate/status \
    /sys/devices/system/cpu/intel_pstate/no_turbo \
    /sys/devices/system/cpu/intel_pstate/max_perf_pct \
    /sys/devices/system/cpu/intel_pstate/min_perf_pct \
    /sys/devices/system/cpu/intel_pstate/hwp_dynamic_boost; do
    if [[ -r "$p" ]]; then
      printf '%s=' "$p"
      cat "$p"
    fi
  done
  echo
  echo "== cpufreq policy for selected CPUs =="
  for cpu in "${cpus[@]}"; do
    base="/sys/devices/system/cpu/cpu${cpu}/cpufreq"
    echo "-- cpu${cpu} --"
    for f in \
      scaling_driver scaling_governor scaling_cur_freq scaling_min_freq scaling_max_freq \
      cpuinfo_min_freq cpuinfo_max_freq base_frequency energy_performance_preference \
      energy_performance_available_preferences; do
      if [[ -r "$base/$f" ]]; then
        printf '%s=' "$f"
        cat "$base/$f"
      fi
    done
  done
  echo
  echo "== CPU socket/core/node mapping for selected CPUs =="
  if lscpu -e=CPU,SOCKET,NODE,CORE,ONLINE,MAXMHZ,MINMHZ >/dev/null 2>&1; then
    cpu_set="$(printf '%s ' "${cpus[@]}")"
    lscpu -e=CPU,SOCKET,NODE,CORE,ONLINE,MAXMHZ,MINMHZ \
      | awk -v cpus="$cpu_set" '
          BEGIN {
            n = split(cpus, a, " ");
            for (i = 1; i <= n; ++i) wanted[a[i]] = 1;
          }
          NR == 1 || wanted[$1]
        '
  fi
  echo
  echo "== cpuidle/C-state policy for selected CPUs =="
  for cpu in "${cpus[@]}"; do
    base="/sys/devices/system/cpu/cpu${cpu}/cpuidle"
    [[ -d "$base" ]] || continue
    echo "-- cpu${cpu} --"
    for state in "$base"/state*; do
      [[ -d "$state" ]] || continue
      name="$(cat "$state/name" 2>/dev/null || basename "$state")"
      disable="$(cat "$state/disable" 2>/dev/null || echo "unknown")"
      latency="$(cat "$state/latency" 2>/dev/null || echo "unknown")"
      residency="$(cat "$state/residency" 2>/dev/null || echo "unknown")"
      echo "$(basename "$state") name=$name disable=$disable latency_us=$latency target_residency_us=$residency"
    done
  done
  for p in \
    /sys/module/intel_idle/parameters/max_cstate \
    /sys/module/processor/parameters/max_cstate \
    /dev/cpu_dma_latency; do
    if [[ -e "$p" ]]; then
      if [[ -r "$p" && ! -c "$p" ]]; then
        printf '%s=' "$p"
        cat "$p" 2>/dev/null || true
      else
        ls -l "$p" 2>/dev/null || true
      fi
    fi
  done
  echo
  echo "== uncore frequency =="
  find /sys/devices/system/cpu/intel_uncore_frequency -maxdepth 3 -type f 2>/dev/null \
    | sort \
    | while read -r f; do
        if [[ -r "$f" ]]; then
          printf '%s=' "$f"
          cat "$f" 2>/dev/null || true
        fi
      done
  echo
  echo "== RAPL =="
  find /sys/class/powercap -maxdepth 3 -type f 2>/dev/null \
    | sort \
    | while read -r f; do
        case "$f" in
          */name|*/enabled|*/constraint_*_power_limit_uw|*/constraint_*_time_window_us|*/energy_uj|*/max_energy_range_uj)
            if [[ -r "$f" ]]; then
              printf '%s=' "$f"
              cat "$f" 2>/dev/null || true
            fi
            ;;
        esac
      done
  echo
  echo "== perf/tsx event availability =="
  perf list rtm_retired 2>/dev/null || true
  perf list tx_mem 2>/dev/null || true
  echo
  echo "== independent MSR reads via turbostat =="
  echo "lockdown=$(cat /sys/kernel/security/lockdown 2>/dev/null || true)"
  if command -v sudo >/dev/null 2>&1 && command -v turbostat >/dev/null 2>&1; then
    cpu_csv="$(IFS=,; echo "${cpus[*]}")"
    sudo -n /usr/bin/turbostat --quiet --cpu "$cpu_csv" \
      --add msr0x1ad,u64,cpu,raw,MSR_1AD \
      --add msr0x1ae,u64,cpu,raw,MSR_1AE \
      --add msr0x1a0,u64,cpu,raw,MSR_1A0 \
      --add msr0x770,u64,cpu,raw,MSR_770 \
      --add msr0x774,u64,cpu,raw,MSR_774 \
      --show CPU,MSR_1AD,MSR_1AE,MSR_1A0,MSR_770,MSR_774 sleep 1 2>&1 || true
  fi
  echo
  echo "== kernel perf_event_paranoid =="
  /usr/sbin/sysctl kernel.perf_event_paranoid 2>/dev/null || true
} > "$out"
