#!/bin/bash
# Read-only verifier for the power-freq-kernel dimension. Writes only under $D.
D=/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112
h=$(hostname -s); C=/sys/devices/system/cpu
{
echo "## date/uptime"; date -u; uptime; uname -a; uptime -s
echo "## cmdline"; cat /proc/cmdline
echo "## config"; grep -E 'CONFIG_X86_INTEL_TSX_MODE|CONFIG_HZ=|CONFIG_PREEMPT_DYNAMIC|CONFIG_NUMA_BALANCING|CONFIG_TRANSPARENT_HUGEPAGE_MADVISE|CONFIG_X86_AMX|CONFIG_NO_HZ_FULL=|CONFIG_X86_INTEL_PSTATE' /boot/config-$(uname -r); md5sum /boot/config-* 2>&1
echo "## tsx flags"; grep -m1 flags /proc/cpuinfo | tr ' ' '\n' | grep -E '^(rtm|hle|tsxldtrk|amx_tile|amx_bf16|amx_int8)$' | tr '\n' ' '; echo; echo "cpus with rtm: $(grep -c -E '^flags.* rtm( |$)' /proc/cpuinfo)"
echo "## microcode"; grep microcode /proc/cpuinfo | sort | uniq -c; cat $C/cpu0/microcode/version 2>&1; grep -m1 -E 'cpu family|^model\s|stepping' /proc/cpuinfo; grep -E 'cpu family|^model\s|stepping' /proc/cpuinfo | sort | uniq -c; ls -l /lib/firmware/intel-ucode/06-ad-01 2>&1; od -A d -t x4 -N 16 /lib/firmware/intel-ucode/06-ad-01 2>&1
echo "## cpuidle default_status"; for s in $C/cpu0/cpuidle/state*; do echo "$(basename $s) $(cat $s/name) disable=$(cat $s/disable) default_status=$(cat $s/default_status 2>&1)"; done
echo "state3 disable counts: $(cat $C/cpu*/cpuidle/state3/disable | sort | uniq -c | tr '\n' ' ')  state4: $(cat $C/cpu*/cpuidle/state4/disable | sort | uniq -c | tr '\n' ' ')"
echo "state3 default_status counts: $(cat $C/cpu*/cpuidle/state3/default_status | sort | uniq -c | tr '\n' ' ')"
echo "## acpi_cppc highest_perf / nominal / guaranteed (count per value)"; for f in highest_perf nominal_perf guaranteed_perf lowest_perf; do echo "$f: $(cat $C/cpu*/acpi_cppc/$f 2>&1 | sort | uniq -c | tr '\n' ' ')"; done
echo "## cpus by highest_perf"; for c in $C/cpu[0-9]*; do echo "$(cat $c/acpi_cppc/highest_perf 2>/dev/null) ${c##*cpu}"; done | sort -n -k1,1 -k2,2 | awk '{a[$1]=a[$1]" "$2} END{for(k in a) print k":"a[k]}'
echo "## cur freq samples (cpu:MHz >=2600)"; for i in 1 2; do for c in $C/cpu[0-9]*; do f=$(cat $c/cpufreq/scaling_cur_freq); [ $f -ge 2600000 ] && printf '%s:%d ' ${c##*cpu} $((f/1000)); done; echo; sleep 1; done
echo "## count cpus > 2750 MHz and their ids"; for c in $C/cpu[0-9]*; do f=$(cat $c/cpufreq/scaling_cur_freq); [ $f -gt 2750000 ] && printf '%s ' ${c##*cpu}; done; echo
echo "## governor/driver/pstate"; cat $C/cpu*/cpufreq/scaling_governor | sort | uniq -c; cat $C/cpu*/cpufreq/scaling_driver | sort | uniq -c; grep -H . $C/intel_pstate/* 2>&1
echo "## thermal throttle"; echo "core_throttle_count sum: $(cat $C/cpu*/thermal_throttle/core_throttle_count 2>/dev/null | awk '{s+=$1} END{print s}')"; echo "package_throttle_count cpu0/cpu72: $(cat $C/cpu0/thermal_throttle/package_throttle_count $C/cpu72/thermal_throttle/package_throttle_count 2>&1 | tr '\n' ' ')"
echo "## grub.cfg tsx"; ls -l /boot/grub/grub.cfg; grep -c 'tsx=on' /boot/grub/grub.cfg 2>&1; grep -m3 -E '^\s+linux\s' /boot/grub/grub.cfg 2>&1
echo "## installed kernels"; ls /boot | grep -E '^vmlinuz-'; dpkg -l 'linux-image-*' 2>/dev/null | grep ^ii | awk '{print $2,$3}'
echo "## tools"; for t in perf cpuid numactl turbostat rdmsr intel-speed-select taskset hwloc-ls lstopo; do echo "$t: $(command -v $t 2>/dev/null || echo MISSING)"; done; ls -l /dev/cpu/0/msr /dev/isst_interface 2>&1; lsmod | grep -E '^msr|^isst'
echo "## sudo"; sudo -n -l 2>&1 | tail -n +5 | cut -c1-200; sudo -n true 2>&1; id
echo "## platformd"; dpkg -l platformd 2>/dev/null | grep ^ii | awk '{print $2,$3}'; systemctl cat platformd.service 2>&1 | head -30; ls -l /usr/bin/positron-* /etc/sudoers.d/ 2>&1 | head -20
echo "## top cpu users"; ps -eo user:12,pid,pcpu,nlwp,psr,comm --sort=-pcpu | head -8
echo "## perf paranoid"; cat /proc/sys/kernel/perf_event_paranoid
} > $D/power-freq-kernel-$h-verify.txt 2>&1
