#!/usr/bin/env bash
# step0_inspect.sh -- system characterization for Xeon-6 / EPYC L3 study
# Run as: bash step0_inspect.sh 2>&1 | tee inspect_$(hostname)_$(date +%Y%m%d).log
# Some sections need root; the script will note what was skipped.

set +e  # keep going even if a tool is missing
hr() { printf '\n========== %s ==========\n' "$1"; }

hr "META"
date
hostname
uname -a
[ -r /etc/os-release ] && cat /etc/os-release
id

hr "CPU (lscpu)"
lscpu

hr "CPU (lscpu --extended) - per-logical-CPU topology"
lscpu --extended

hr "/proc/cpuinfo (model name + flags, 1st CPU only)"
awk '/^processor/{p=$3} p==0 && (/^model name/||/^cpu MHz/||/^cache size/||/^physical id/||/^siblings/||/^core id/||/^cpu cores/||/^flags/)' /proc/cpuinfo

hr "CPU vulnerabilities / mitigations"
grep -H . /sys/devices/system/cpu/vulnerabilities/* 2>/dev/null

hr "CPU frequency scaling"
for f in /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor \
         /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver \
         /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_min_freq \
         /sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq \
         /sys/devices/system/cpu/intel_pstate/status \
         /sys/devices/system/cpu/intel_pstate/no_turbo \
         /sys/devices/system/cpu/cpufreq/boost; do
  [ -r "$f" ] && printf '%s = %s\n' "$f" "$(cat "$f")"
done

hr "Cache topology (per CPU0)"
for d in /sys/devices/system/cpu/cpu0/cache/index*; do
  [ -d "$d" ] || continue
  printf -- '--- %s ---\n' "$d"
  for k in level type size coherency_line_size ways_of_associativity \
           number_of_sets shared_cpu_list; do
    [ -r "$d/$k" ] && printf '  %s = %s\n' "$k" "$(cat "$d/$k")"
  done
done

hr "NUMA (numactl --hardware)"
command -v numactl >/dev/null && numactl --hardware || echo "numactl not installed"

hr "NUMA distance matrix (raw)"
[ -r /sys/devices/system/node/node0/distance ] && \
  for n in /sys/devices/system/node/node*/distance; do
    printf '%s : %s\n' "$n" "$(cat "$n")"
  done

hr "NUMA: cpus per node"
for n in /sys/devices/system/node/node*; do
  [ -r "$n/cpulist" ] && printf '%s cpulist = %s\n' "$(basename "$n")" "$(cat "$n/cpulist")"
done

hr "Memory (free -h)"
free -h

hr "Memory (DMI / dmidecode) -- needs root; per-DIMM"
if command -v dmidecode >/dev/null; then
  sudo -n dmidecode -t memory 2>/dev/null | \
    awk '/^Memory Device$/,/^$/' | \
    grep -E 'Size:|Speed:|Configured (Memory )?Speed:|Type:|Manufacturer:|Part Number:|Locator:|Rank:' \
    | head -200
  echo "--- DMI system / baseboard ---"
  sudo -n dmidecode -t system 2>/dev/null | grep -E 'Manufacturer:|Product Name:|Version:' | head
  sudo -n dmidecode -t baseboard 2>/dev/null | grep -E 'Manufacturer:|Product Name:' | head
else
  echo "dmidecode not installed"
fi

hr "Hugepages"
grep -E 'Huge|Hugepagesize' /proc/meminfo
for f in /sys/kernel/mm/transparent_hugepage/enabled \
         /sys/kernel/mm/transparent_hugepage/defrag; do
  [ -r "$f" ] && printf '%s = %s\n' "$f" "$(cat "$f")"
done
for d in /sys/devices/system/node/node*/hugepages/hugepages-*; do
  [ -d "$d" ] || continue
  printf '%s nr=%s free=%s\n' "$d" \
    "$(cat "$d/nr_hugepages" 2>/dev/null)" \
    "$(cat "$d/free_hugepages" 2>/dev/null)"
done

hr "Kernel cmdline"
cat /proc/cmdline

hr "Kernel version / scheduler"
uname -r
[ -r /sys/kernel/debug/sched_features ] && sudo -n cat /sys/kernel/debug/sched_features 2>/dev/null
sysctl -a 2>/dev/null | grep -E 'kernel.numa_balancing|vm.zone_reclaim_mode|vm.swappiness'

hr "IRQ affinity summary"
if [ -r /proc/interrupts ]; then
  awk 'NR==1 || /eth|enp|ens|nvme|mlx|ice/' /proc/interrupts | head -40
fi

hr "Storage / NIC (one-liners)"
command -v lsblk >/dev/null && lsblk -d -o NAME,SIZE,MODEL,ROTA 2>/dev/null
command -v lspci >/dev/null && lspci 2>/dev/null | grep -iE 'ether|network|nvme|memory controller|host bridge' | head

hr "Container / VM detection"
command -v systemd-detect-virt >/dev/null && systemd-detect-virt
[ -r /proc/1/cgroup ] && head -5 /proc/1/cgroup
[ -r /sys/class/dmi/id/sys_vendor ] && printf 'sys_vendor=%s\n' "$(cat /sys/class/dmi/id/sys_vendor)"
[ -r /sys/class/dmi/id/product_name ] && printf 'product_name=%s\n' "$(cat /sys/class/dmi/id/product_name)"

hr "MCE / EDAC (errors that could skew perf)"
[ -d /sys/devices/system/edac ] && \
  find /sys/devices/system/edac -name 'ue_count' -o -name 'ce_count' 2>/dev/null | \
  while read f; do printf '%s = %s\n' "$f" "$(cat "$f")"; done
command -v mcelog >/dev/null && sudo -n mcelog --client 2>/dev/null | head -20

hr "Compilers + perf tools available"
for t in gcc clang make cmake numactl hwloc-info likwid-topology \
         perf taskset chrt nproc dmidecode lscpu lstopo; do
  if command -v "$t" >/dev/null; then
    printf '%-20s %s\n' "$t:" "$($t --version 2>&1 | head -1)"
  else
    printf '%-20s NOT INSTALLED\n' "$t:"
  fi
done

hr "hwloc topology (if available)"
command -v lstopo-no-graphics >/dev/null && lstopo-no-graphics --no-io 2>/dev/null | head -100

hr "DONE"
date
