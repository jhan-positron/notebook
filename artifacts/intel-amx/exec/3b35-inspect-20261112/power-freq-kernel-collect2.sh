#!/bin/bash
D=/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112
h=$(hostname -s); C=/sys/devices/system/cpu
{
echo "## id"; id
echo "## positron iss / platformd"; ls -l /usr/bin/positron-intel-speed-select /usr/local/sbin/intel-speed-select-state /usr/bin/intel-speed-select 2>&1
dpkg -S /usr/bin/positron-intel-speed-select /usr/bin/intel-speed-select 2>&1
dpkg -l 2>/dev/null | grep -i -E 'platformd|positron' | awk '{print $1,$2,$3}'
systemctl list-units --no-pager --all 2>/dev/null | grep -i -E 'speed|platformd|cstate|c-state|idle|freq|power' 
echo "## file type of positron-intel-speed-select"; file /usr/bin/positron-intel-speed-select 2>&1
echo "## grep cstate/cpuidle writers"; grep -l -s -E 'cpuidle|C6|cstate' /usr/local/sbin/* /etc/systemd/system/*.service /etc/rc.local /etc/default/intel-speed-select-state /etc/tmpfiles.d/* /etc/sysfs.conf /etc/sysfs.d/* /etc/udev/rules.d/* 2>&1
echo "## dmesg_restrict"; cat /proc/sys/kernel/dmesg_restrict
echo "## per-cpu cur freq >= 2600 MHz, 3 samples 1 s apart (cpu:MHz)"
for i in 1 2 3; do for c in $C/cpu[0-9]*; do f=$(cat $c/cpufreq/scaling_cur_freq); [ $f -ge 2600000 ] && printf '%s:%d ' ${c##*cpu} $((f/1000)); done; echo; sleep 1; done
echo "## per-cpu C6 residency: cpus with nonzero C6/C6P usage"; n=0; for c in $C/cpu[0-9]*; do [ "$(cat $c/cpuidle/state3/usage)" != 0 ] && n=$((n+1)); done; echo "cpus with C6 usage>0: $n"
echo "## acpi pstate / hwp flags"; grep -m1 flags /proc/cpuinfo | tr ' ' '\n' | grep -E '^(hwp|hwp_.*|ida|arat|pln|pts|epb|hfi|tsx.*|rtm|hle|nonstop_tsc|constant_tsc|art|tsc_known_freq)$' | tr '\n' ' '; echo
echo "## bugs"; grep -m1 bugs /proc/cpuinfo
echo "## tsx sysfs"; cat $C/vulnerabilities/tsx_async_abort
echo "## grub default"; grep -v '^#' /etc/default/grub 2>&1 | grep -v '^$'; ls /etc/default/grub.d/ 2>&1; grep -H -v '^#' /etc/default/grub.d/* 2>&1 | grep -v ':$'
echo "## sysctl.d"; ls /etc/sysctl.d/ 2>&1
echo "## hugepages"; grep -i -E 'huge|MemTotal' /proc/meminfo; cat /sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
} > $D/power-freq-kernel-$h-extra.txt 2>&1
cat $D/power-freq-kernel-$h-extra.txt
