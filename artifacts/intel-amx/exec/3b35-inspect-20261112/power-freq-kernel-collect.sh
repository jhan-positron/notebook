#!/bin/bash
# Read-only collector for the power-freq-kernel dimension. Writes only under $D.
D=/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112
h=$(hostname -s)
o() { echo "$D/power-freq-kernel-$h-$1.txt"; }
C=/sys/devices/system/cpu
{ date -u; uptime; uname -a; cat /proc/version; echo; cat /etc/os-release; echo; ldd --version | head -1; dpkg -l libc6 linux-image-$(uname -r) 2>/dev/null | grep ^ii; echo "boot:"; uptime -s; } > $(o kernel-os) 2>&1
cat /proc/cmdline > $(o cmdline) 2>&1
cp /boot/config-$(uname -r) $(o bootconfig) 2>&1 || echo "unreadable" > $(o bootconfig)
{
echo "## scaling_driver"; cat $C/cpu*/cpufreq/scaling_driver | sort | uniq -c
echo "## scaling_governor"; cat $C/cpu*/cpufreq/scaling_governor | sort | uniq -c
echo "## intel_pstate"; for f in status no_turbo min_perf_pct max_perf_pct hwp_dynamic_boost turbo_pct num_pstates; do echo "$f: $(cat $C/intel_pstate/$f 2>&1)"; done
echo "## EPP"; cat $C/cpu*/cpufreq/energy_performance_preference 2>&1 | sort | uniq -c
echo "## EPB"; cat $C/cpu*/power/energy_perf_bias 2>&1 | sort | uniq -c
for f in cpuinfo_max_freq cpuinfo_min_freq base_frequency scaling_max_freq scaling_min_freq; do echo "## $f"; cat $C/cpu*/cpufreq/$f 2>&1 | sort | uniq -c; done
echo "## online/smt"; cat $C/online $C/smt/active $C/smt/control
echo "## node cpulists"; for n in /sys/devices/system/node/node*; do echo "$n: $(cat $n/cpulist)"; done
echo "## package of cpu72 cpu0"; cat $C/cpu0/topology/physical_package_id $C/cpu72/topology/physical_package_id
echo "## scaling_cur_freq socket1 (MHz, rounded to 100) histogram"
for c in $C/cpu[0-9]*; do p=$(cat $c/topology/physical_package_id); [ "$p" = 1 ] && cat $c/cpufreq/scaling_cur_freq; done | awk '{printf "%d\n", int($1/100000+0.5)*100}' | sort -n | uniq -c
echo "## scaling_cur_freq socket0 histogram"
for c in $C/cpu[0-9]*; do p=$(cat $c/topology/physical_package_id); [ "$p" = 0 ] && cat $c/cpufreq/scaling_cur_freq; done | awk '{printf "%d\n", int($1/100000+0.5)*100}' | sort -n | uniq -c
echo "## uncore"; for d in $C/intel_uncore_frequency/*; do echo "$(basename $d): $(for f in min_freq_khz max_freq_khz initial_min_freq_khz initial_max_freq_khz current_freq_khz domain_id package_id fabric_cluster_id elc_low_threshold_percent elc_high_threshold_percent elc_high_threshold_enable elc_floor_freq_khz; do [ -r $d/$f ] && printf '%s=%s ' $f "$(cat $d/$f 2>&1)"; done)"; done
echo "## cpuidle"; cat $C/cpuidle/current_driver $C/cpuidle/current_governor 2>&1
for s in $C/cpu0/cpuidle/state*; do echo "$(basename $s): name=$(cat $s/name) desc=$(cat $s/desc) disable=$(cat $s/disable) latency=$(cat $s/latency) residency=$(cat $s/residency) usage=$(cat $s/usage) time=$(cat $s/time)"; done
echo "## cpuidle disable count across all cpus (state:disable count)"
for s in 0 1 2 3 4; do [ -e $C/cpu0/cpuidle/state$s ] && echo "state$s: $(cat $C/cpu*/cpuidle/state$s/disable | sort | uniq -c | tr '\n' ' ')"; done
echo "## intel_idle params"; grep -H . /sys/module/intel_idle/parameters/* 2>&1
echo "## pm_qos"; ls -l /dev/cpu_dma_latency 2>&1
} > $(o freq) 2>&1
{
for u in tuned irqbalance thermald power-profiles-daemon cpupower intel-speed-select-state ondemand cpufrequtils tlp; do echo "$u: active=$(systemctl is-active $u 2>&1) enabled=$(systemctl is-enabled $u 2>&1)"; done
echo "## tuned-adm"; (command -v tuned-adm && tuned-adm active) 2>&1; cat /etc/tuned/active_profile 2>&1
echo "## powerprofilesctl"; (command -v powerprofilesctl && powerprofilesctl get) 2>&1
echo "## iss boot service"; systemctl cat intel-speed-select-state.service 2>&1 | head -40; systemctl status intel-speed-select-state.service --no-pager 2>&1 | head -15
echo "## /etc/default/intel-speed-select-state"; cat /etc/default/intel-speed-select-state 2>&1
echo "## isst binaries"; ls -l /opt/intel-speed-select/ /dev/isst_interface 2>&1; command -v intel-speed-select intel-speed-select-state 2>&1
echo "## sudo -n -l"; sudo -n -l 2>&1 | head -30
echo "## sysctl"; for k in kernel.perf_event_paranoid kernel.kptr_restrict kernel.numa_balancing kernel.nmi_watchdog kernel.sched_autogroup_enabled vm.swappiness vm.nr_hugepages vm.zone_reclaim_mode kernel.randomize_va_space kernel.timer_migration; do echo "$k = $(cat /proc/sys/${k//./\/} 2>&1)"; done
echo "## THP"; grep -H . /sys/kernel/mm/transparent_hugepage/enabled /sys/kernel/mm/transparent_hugepage/defrag /sys/kernel/mm/transparent_hugepage/khugepaged/defrag 2>&1
echo "## clocksource"; cat /sys/devices/system/clocksource/clocksource0/current_clocksource
echo "## vulnerabilities"; grep -H . /sys/devices/system/cpu/vulnerabilities/* 2>&1
echo "## tools"; for t in perf cpuid numactl turbostat cpupower x86_energy_perf_policy rdmsr intel-speed-select; do p=$(command -v $t 2>/dev/null); echo "$t: ${p:-MISSING}"; done
perf --version 2>&1 | head -2; cpuid --version 2>&1 | head -1; numactl --version 2>&1 | head -1; turbostat --version 2>&1 | head -1
dpkg -l 2>/dev/null | grep -E 'linux-tools|linux-cloud-tools|^ii  cpuid|^ii  numactl|msr-tools|intel-microcode|^ii  tuned|irqbalance|thermald|power-profiles' | awk '{print $1,$2,$3}'
echo "## microcode"; grep -m1 microcode /proc/cpuinfo; grep -m1 'model name' /proc/cpuinfo
echo "## flags amx"; grep -m1 flags /proc/cpuinfo | tr ' ' '\n' | grep -E 'amx|avx512_fp16|avx512_bf16' | tr '\n' ' '; echo
echo "## msr module/dev"; ls -l /dev/cpu/0/msr 2>&1; lsmod | grep -E '^msr|isst|intel_uncore_frequency|intel_rapl|tpmi' 
echo "## rapl"; for z in /sys/class/powercap/intel-rapl:[0-9]; do echo "$z name=$(cat $z/name) pl1_uw=$(cat $z/constraint_0_power_limit_uw 2>&1) pl2_uw=$(cat $z/constraint_1_power_limit_uw 2>&1) enabled=$(cat $z/enabled 2>&1)"; done
echo "## installed kernels"; ls /boot | grep -E '^(vmlinuz|config)-'
echo "## kernel changelog local"; ls -l /usr/share/doc/linux-image-$(uname -r)/ /usr/share/doc/linux-modules-$(uname -r)/ 2>&1
} > $(o services-tools) 2>&1
echo done $h; ls -l $D | grep "power-freq-kernel-$h"
