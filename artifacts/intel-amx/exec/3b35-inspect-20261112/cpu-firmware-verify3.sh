#!/bin/bash
echo "## host $(hostname) $(date -u +%FT%TZ)"
echo "## ucode file header (rev at bytes 4-7, date 8-11, sig 12-15)"; od -A d -t x4 -N 48 /lib/firmware/intel-ucode/06-ad-01
echo "## package_throttle_count per package (cpu0, cpu72)"; for c in 0 72 143 144; do echo "cpu$c pkg=$(cat /sys/devices/system/cpu/cpu$c/topology/physical_package_id) $(grep -H . /sys/devices/system/cpu/cpu$c/thermal_throttle/* | sed 's|.*/||' | tr '\n' ' ')"; done
echo "## distribution package_throttle_count"; cat /sys/devices/system/cpu/cpu*/thermal_throttle/package_throttle_count | sort -n | uniq -c
echo "## core_throttle_count: n cpus nonzero, sum, max"; cat /sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_count | awk '{if($1>0)n++; s+=$1; if($1>m)m=$1} END{print n+0, s, m}'
echo "## core_throttle_total_time_ms sum,max"; cat /sys/devices/system/cpu/cpu*/thermal_throttle/core_throttle_total_time_ms 2>/dev/null | awk '{s+=$1; if($1>m)m=$1} END{print s, m}'
echo "## package temps"; for z in /sys/class/thermal/thermal_zone*; do echo "$(cat $z/type) $(cat $z/temp 2>/dev/null)"; done | head; for h in /sys/class/hwmon/hwmon*; do n=$(cat $h/name); [ "$n" = coretemp ] && echo "coretemp $(cat $h/temp1_label): now=$(cat $h/temp1_input) max=$(cat $h/temp1_max) crit=$(cat $h/temp1_crit)"; done
cat /proc/uptime
