#!/usr/bin/env bash
# 01_inspect.sh -- read-only system snapshot. Run before/after the suite.
set -u

read_file() {
  local path="$1"
  if [ -r "$path" ]; then
    cat "$path"
  else
    echo "(missing: $path)"
  fi
}

show_file() {
  local label="$1"
  local path="$2"
  printf "%s=" "$label"
  read_file "$path"
}

show_cmd() {
  local cmd="$1"
  shift
  if command -v "$cmd" >/dev/null 2>&1; then
    "$cmd" "$@"
  else
    echo "($cmd not installed)"
  fi
}

summarize_policy_file() {
  local name="$1"
  local values
  values=$(for path in /sys/devices/system/cpu/cpufreq/policy*/"$name"; do
    [ -r "$path" ] && cat "$path"
  done)

  echo "$name:"
  if [ -n "$values" ]; then
    printf "%s\n" "$values" | sort | uniq -c | sed 's/^/  /'
  else
    echo "  (not exposed)"
  fi
}

show_sysctl() {
  local name="$1"
  local path="/proc/sys/${name//./\/}"
  show_file "$name" "$path"
}

show_cpu_idle_states() {
  local cpu="$1"
  local state

  if [ ! -d "/sys/devices/system/cpu/cpu${cpu}/cpuidle" ]; then
    echo "cpu${cpu}: cpuidle not exposed"
    return
  fi

  echo "cpu${cpu}:"
  for state in /sys/devices/system/cpu/cpu"${cpu}"/cpuidle/state*; do
    [ -d "$state" ] || continue
    printf "  %s" "$(basename "$state")"
    for field in name desc latency residency disable; do
      [ -r "$state/$field" ] && printf " %s=%s" "$field" "$(cat "$state/$field")"
    done
    printf "\n"
  done
}

NODE_ONLINE=$(cat /sys/devices/system/node/online)
NODE_POSSIBLE=$(cat /sys/devices/system/node/possible)
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS="$HERE/../results"

case "$NODE_ONLINE" in
  0-5) RESULTS="$RESULTS/snc3" ;;
  0-1) RESULTS="$RESULTS/snc-off" ;;
  *)
    echo "!!! unexpected node/online=$NODE_ONLINE possible=$NODE_POSSIBLE"
    exit 1
    ;;
esac

mkdir -p "$RESULTS"
STAMP=$(date +%Y%m%d_%H%M)
HOST=$(hostname)
LOG="$RESULTS/inspect_${HOST}_${STAMP}.log"
exec > >(tee -a "$LOG") 2>&1

hr() { printf '\n========== %s ==========\n' "$1"; }

hr META
date
hostname
uname -a
echo "script=$0"

hr "OS release"
read_file /etc/os-release

hr "kernel command line"
read_file /proc/cmdline

hr "uptime / load / users"
uptime
w -h

hr "DMI / BIOS"
for item in \
  bios_vendor bios_version bios_date \
  sys_vendor product_name product_version product_family product_sku \
  board_vendor board_name board_version; do
  show_file "$item" "/sys/class/dmi/id/$item"
done
if command -v dmidecode >/dev/null 2>&1; then
  if sudo -n dmidecode -t bios -t system -t baseboard 2>/dev/null |
      grep -E '^[[:space:]]*(Vendor|Version|Release Date|Manufacturer|Product Name|SKU Number|Family):' |
      sed 's/^[[:space:]]*//'
  then
    :
  else
    echo "(dmidecode skipped: sudo -n dmidecode unavailable)"
  fi
else
  echo "(dmidecode not installed)"
fi

hr lscpu
lscpu | grep -iE 'Architecture|CPU\(s\)|On-line|Vendor ID|Model name|CPU family|Model:|Stepping|Socket|Core|Thread|NUMA|L1|L2|L3|MHz|Scaling|Virtualization'

hr "CPU microcode"
awk '/^microcode[[:space:]]*:/{print; exit}' /proc/cpuinfo

hr "SMT / CPU online state"
show_file smt_control /sys/devices/system/cpu/smt/control
show_file smt_active /sys/devices/system/cpu/smt/active
show_file cpu_online /sys/devices/system/cpu/online
show_file cpu_offline /sys/devices/system/cpu/offline
show_file cpu_isolated /sys/devices/system/cpu/isolated
show_file cpu_nohz_full /sys/devices/system/cpu/nohz_full

hr "CPU frequency policy summary"
for field in \
  scaling_driver scaling_governor scaling_min_freq scaling_max_freq scaling_cur_freq \
  cpuinfo_min_freq cpuinfo_max_freq cpuinfo_cur_freq energy_performance_preference \
  energy_performance_bias; do
  summarize_policy_file "$field"
done

hr "Intel pstate / boost"
for path in \
  /sys/devices/system/cpu/intel_pstate/status \
  /sys/devices/system/cpu/intel_pstate/no_turbo \
  /sys/devices/system/cpu/intel_pstate/turbo_pct \
  /sys/devices/system/cpu/intel_pstate/num_pstates \
  /sys/devices/system/cpu/intel_pstate/hwp_dynamic_boost \
  /sys/devices/system/cpu/intel_pstate/max_perf_pct \
  /sys/devices/system/cpu/intel_pstate/min_perf_pct \
  /sys/devices/system/cpu/cpufreq/boost; do
  [ -e "$path" ] && show_file "$(basename "$(dirname "$path")")/$(basename "$path")" "$path"
done

hr "CPU idle / C-states"
show_file cpuidle_current_driver /sys/devices/system/cpu/cpuidle/current_driver
show_file cpuidle_current_governor /sys/devices/system/cpu/cpuidle/current_governor
show_cpu_idle_states 0
show_cpu_idle_states 24
show_cpu_idle_states 72

hr "uncore frequency"
if [ -d /sys/devices/system/cpu/intel_uncore_frequency ]; then
  for domain in /sys/devices/system/cpu/intel_uncore_frequency/*; do
    [ -d "$domain" ] || continue
    echo "$(basename "$domain"):"
    for field in initial_min_freq_khz initial_max_freq_khz min_freq_khz max_freq_khz current_freq_khz; do
      [ -r "$domain/$field" ] && printf "  %s=%s\n" "$field" "$(cat "$domain/$field")"
    done
  done
else
  echo "(intel_uncore_frequency sysfs not exposed)"
fi

hr "powercap / RAPL"
if [ -d /sys/class/powercap ]; then
  for zone in /sys/class/powercap/intel-rapl:*; do
    [ -d "$zone" ] || continue
    printf "%s" "$(basename "$zone")"
    [ -r "$zone/name" ] && printf " name=%s" "$(cat "$zone/name")"
    [ -r "$zone/enabled" ] && printf " enabled=%s" "$(cat "$zone/enabled")"
    printf "\n"
    for field in "$zone"/constraint_*_power_limit_uw "$zone"/constraint_*_time_window_us; do
      [ -r "$field" ] && printf "  %s=%s\n" "$(basename "$field")" "$(cat "$field")"
    done
  done
else
  echo "(powercap sysfs not exposed)"
fi

hr "NUMA online/possible"
echo "online=$NODE_ONLINE possible=$NODE_POSSIBLE"

hr "numactl --hardware"
show_cmd numactl --hardware

hr "ACPI distance matrix"
for n in /sys/devices/system/node/node*/distance; do
  [ -r "$n" ] && echo "$n: $(cat "$n")"
done

hr "NUMA balancing"
show_sysctl kernel.numa_balancing
show_sysctl kernel.numa_balancing_promote_rate_limit_MBps

hr "memory / THP"
grep -E '^(MemTotal|MemFree|MemAvailable|HugePages_|Hugepagesize|AnonHugePages|ShmemHugePages|FileHugePages|PageTables):' /proc/meminfo
for path in \
  /sys/kernel/mm/transparent_hugepage/enabled \
  /sys/kernel/mm/transparent_hugepage/defrag \
  /sys/kernel/mm/transparent_hugepage/shmem_enabled \
  /sys/kernel/mm/transparent_hugepage/use_zero_page; do
  [ -e "$path" ] && show_file "$(basename "$(dirname "$path")")/$(basename "$path")" "$path"
done

hr "hugepages"
for h in /sys/kernel/mm/hugepages/hugepages-*; do
  [ -d "$h" ] || continue
  printf "%s:" "$(basename "$h")"
  for field in nr_hugepages free_hugepages resv_hugepages surplus_hugepages; do
    [ -r "$h/$field" ] && printf " %s=%s" "$field" "$(cat "$h/$field")"
  done
  printf "\n"
done

hr "buddyinfo"
read_file /proc/buddyinfo

hr "resctrl"
mount | grep resctrl || echo "(not mounted)"
if [ -d /sys/fs/resctrl/info/L3 ]; then
  show_file num_closids /sys/fs/resctrl/info/L3/num_closids
  show_file cbm_mask /sys/fs/resctrl/info/L3/cbm_mask
  show_file min_cbm_bits /sys/fs/resctrl/info/L3/min_cbm_bits
  show_file shareable_bits /sys/fs/resctrl/info/L3/shareable_bits
  [ -r /sys/fs/resctrl/schemata ] && { echo "root schemata:"; cat /sys/fs/resctrl/schemata; }
fi

hr "perf / security knobs"
show_sysctl kernel.perf_event_paranoid
show_sysctl kernel.kptr_restrict
show_sysctl kernel.nmi_watchdog
show_file rdpmc /sys/devices/cpu/rdpmc

hr "CPU vulnerability mitigations"
for vuln in /sys/devices/system/cpu/vulnerabilities/*; do
  [ -r "$vuln" ] && echo "$(basename "$vuln"): $(cat "$vuln")"
done

hr end
date
echo "saved $LOG"
