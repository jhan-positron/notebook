#!/bin/bash
echo "## uncore dirs"; ls /sys/devices/system/cpu/intel_uncore_frequency/ | tr '\n' ' '; echo
for d in /sys/devices/system/cpu/intel_uncore_frequency/*/; do echo "$(basename $d): $(for f in $d*; do [ -f $f ] && echo -n "$(basename $f)=$(cat $f 2>&1) "; done)"; done 2>&1 | sort | head -40
echo "## lsmod names"; lsmod | awk 'NR>1{print $1}' | sort | tr '\n' ' '; echo
echo "## nvme / block"; lsblk -d -o NAME,MODEL,SIZE,ROTA 2>&1
echo "## cpuidle driver/governor"; cat /sys/devices/system/cpu/cpuidle/current_driver /sys/devices/system/cpu/cpuidle/current_governor
echo "## cpu0 cpuidle states"; for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do echo "$(cat $s/name) latency=$(cat $s/latency) residency=$(cat $s/residency) disable=$(cat $s/disable)"; done
echo "## energy_perf"; cat /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference | sort | uniq -c; cat /sys/devices/system/cpu/cpu*/power/energy_perf_bias 2>&1 | sort | uniq -c
echo "## memlock limits conf"; grep -v '^#' /etc/security/limits.conf /etc/security/limits.d/* 2>&1 | grep -v ':$' | head
echo "## hugepage sizes"; ls /sys/kernel/mm/hugepages/; cat /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
echo "## tme/mktme"; ls /sys/kernel/mm/ 2>&1 | tr '\n' ' '; echo
echo "## SRAT/HMAT sizes"; ls -l /sys/firmware/acpi/tables | awk '{print $5, $9}' | tr '\n' ' '; echo
echo "## mlx / nic count"; ls /sys/class/net | tr '\n' ' '; echo
echo "## hwmon nvme+mlx temps"; for h in /sys/class/hwmon/hwmon*; do n=$(cat $h/name); [ "$n" = coretemp ] && echo "$n $(cat $h/temp1_label) $(cat $h/temp1_input)"; done
echo "## thermal zones"; for z in /sys/class/thermal/thermal_zone*; do echo "$(cat $z/type 2>&1) $(cat $z/temp 2>&1)"; done 2>&1 | head
echo "## cooling devices count"; ls /sys/class/thermal | grep -c cooling
echo "## intel_powerclamp/idle inject"; ls /sys/devices/system/cpu/cpu0/ | tr '\n' ' '; echo
echo "## hfi / itmt"; cat /proc/sys/kernel/sched_itmt_enabled 2>&1
echo "## cpu capacity asym"; cat /sys/devices/system/cpu/cpu*/cpu_capacity 2>/dev/null | sort | uniq -c
echo "## prefer core"; cat /sys/devices/system/cpu/intel_pstate/hwp_dynamic_boost
