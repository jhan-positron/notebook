#!/bin/bash
D=/home/jhan/workspace/intel-AMX/exec/3b35-inspect-20261112
echo "## host $(hostname) $(date -u +%FT%TZ)"
echo "## cpuid leaf 0x16 / 7 on 4 cpus"
for c in 0 71 72 287; do echo "cpu $c: $(taskset -c $c python3 $D/cpu-firmware-cpuid-user.py | grep -E 'leaf 0x(16|07 sub  [01])' | tr '\n' ';')"; done
echo "## tsx config"; grep -E 'CONFIG_X86_INTEL_TSX' /boot/config-$(uname -r)
echo "## dmesg (non-root)"; dmesg 2>&1 | grep -iE 'microcode|intel_idle|tsx|ACPI: .*_CST|cpuidle' | head -20
echo "## journalctl -k non-root"; timeout 20 journalctl -k -b --no-pager 2>&1 | grep -iE 'microcode|intel_idle|tsx|DMI:' | head -20
echo "## clocksource"; cat /sys/devices/system/clocksource/clocksource0/current_clocksource /sys/devices/system/clocksource/clocksource0/available_clocksource
echo "## thermal throttle"; cat /sys/devices/system/cpu/cpu*/thermal_throttle/package_throttle_count 2>/dev/null | sort -n | uniq -c | tail -4; cat /sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_count 2>/dev/null | sort -n | uniq -c | tail -4
echo "## rapl"; for z in /sys/class/powercap/intel-rapl:?; do echo "$z name=$(cat $z/name) enabled=$(cat $z/enabled 2>&1) c0=$(cat $z/constraint_0_name 2>&1):$(cat $z/constraint_0_power_limit_uw 2>&1):win$(cat $z/constraint_0_time_window_us 2>&1) c1=$(cat $z/constraint_1_name 2>&1):$(cat $z/constraint_1_power_limit_uw 2>&1) max0=$(cat $z/constraint_0_max_power_uw 2>&1)"; done
echo "## intel-microcode pkg"; dpkg -l intel-microcode 2>&1 | tail -1; ls /lib/firmware/intel-ucode/06-ad-01* 2>&1
echo "## acpi_cpufreq/hwp flags"; grep -m1 '^flags' /proc/cpuinfo | tr ' ' '\n' | grep -E '^hwp|^ida$|^arat$|^pts$|^epb$' | tr '\n' ' '; echo
echo "## acpi processor power"; ls /sys/devices/system/cpu/cpu0/ | tr '\n' ' '; echo; cat /sys/devices/system/cpu/cpu0/acpi_cppc/highest_perf /sys/devices/system/cpu/cpu0/acpi_cppc/nominal_perf /sys/devices/system/cpu/cpu0/acpi_cppc/guaranteed_perf /sys/devices/system/cpu/cpu0/acpi_cppc/lowest_nonlinear_perf 2>&1 | tr '\n' ' '; echo
cat /sys/devices/system/cpu/cpu*/acpi_cppc/highest_perf | sort | uniq -c
echo "## c6 residency sum"; awk '{s+=$1} END{print "C6 us total", s}' /sys/devices/system/cpu/cpu*/cpuidle/state3/time; awk '{s+=$1} END{print "C6P us total", s}' /sys/devices/system/cpu/cpu*/cpuidle/state4/time; awk '{s+=$1} END{print "C1E us total", s}' /sys/devices/system/cpu/cpu*/cpuidle/state2/time; cat /proc/uptime
echo "## sudo"; sudo -n true 2>&1; echo rc=$?
echo "## udev positron rules (who sets cpu settings)"; grep -liE 'cpuidle|cstate|cpu_dma' /etc/udev/rules.d/* /etc/systemd/system/*.service /etc/rc.local /etc/sysctl.d/* 2>/dev/null
