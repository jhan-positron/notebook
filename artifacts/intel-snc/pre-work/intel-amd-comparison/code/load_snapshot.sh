#!/usr/bin/env bash
# load_snapshot.sh -- capture a snapshot of system load + state.
# Run BEFORE and AFTER each sweep session to verify the system was
# quiet during measurements.
#
# Output: written automatically to
#   load_snapshot_<host>_<YYYYMMDD>_<HHMM>.log
# in the current working directory. Both invocations (pre/post)
# produce their own timestamped file; no redirection needed.
#
# Read-only: makes no system changes.

set -u

OUT="load_snapshot_$(hostname)_$(date +%Y%m%d_%H%M).log"
echo "writing snapshot to $OUT" >&2
exec > "$OUT"

hr() { printf "\n========== %s ==========\n" "$1"; }

echo "Hostname:   $(hostname)"
echo "Timestamp:  $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Uptime:     $(uptime)"

hr "Load average + 1-second CPU snapshot"
echo "/proc/loadavg:"
cat /proc/loadavg
echo
echo "vmstat 1 3:  (3 samples, 1s apart; first sample averages since boot)"
vmstat 1 3 2>/dev/null || echo "(vmstat not available)"

hr "/proc/stat — first vs second sample (1s apart)"
read u1 n1 s1 i1 _ < <(head -1 /proc/stat | awk '{print $2,$3,$4,$5,$6}')
sleep 1
read u2 n2 s2 i2 _ < <(head -1 /proc/stat | awk '{print $2,$3,$4,$5,$6}')
total=$(( (u2-u1) + (n2-n1) + (s2-s1) + (i2-i1) ))
if [ "$total" -gt 0 ]; then
    pct_user=$(( 100*(u2-u1)/total ))
    pct_sys=$(( 100*(s2-s1)/total ))
    pct_idle=$(( 100*(i2-i1)/total ))
    echo "Total CPU over the 1-second window:"
    echo "  user=${pct_user}%  sys=${pct_sys}%  idle=${pct_idle}%"
else
    echo "(could not compute deltas; very short window)"
fi

hr "Top 15 CPU-using processes"
ps -eo pid,user,pcpu,pmem,comm --sort=-pcpu | head -16

hr "Memory state (/proc/meminfo highlights)"
grep -E '^(MemTotal|MemFree|MemAvailable|Buffers|Cached|HugePages_Total|HugePages_Free|Hugepagesize):' /proc/meminfo

hr "Hugepage pool state"
for hp in /sys/kernel/mm/hugepages/hugepages-*; do
    size=$(basename "$hp" | sed 's/hugepages-//')
    nr=$(cat "$hp/nr_hugepages" 2>/dev/null || echo "?")
    free=$(cat "$hp/free_hugepages" 2>/dev/null || echo "?")
    echo "  $size: nr=$nr free=$free"
done

hr "CPU frequency state (sample first 4 + last cpu)"
NCPU=$(nproc)
for cpu in 0 1 2 3 $((NCPU-1)); do
    fcur="/sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_cur_freq"
    fgov="/sys/devices/system/cpu/cpu$cpu/cpufreq/scaling_governor"
    cur=$(cat $fcur 2>/dev/null || echo "?")
    gov=$(cat $fgov 2>/dev/null || echo "?")
    if [ "$cur" != "?" ]; then
        cur_mhz=$((cur/1000))
        echo "  cpu$cpu: ${cur_mhz} MHz  governor=$gov"
    fi
done

hr "Thermal state (first few zones, if exposed)"
for zone in /sys/class/thermal/thermal_zone[0-4]; do
    [ -d "$zone" ] || continue
    type=$(cat "$zone/type" 2>/dev/null || echo "?")
    temp_mc=$(cat "$zone/temp" 2>/dev/null || echo "0")
    temp_c=$((temp_mc / 1000))
    echo "  $(basename $zone) $type : ${temp_c}°C"
done

hr "Hardware errors since boot (dmesg)"
err_count=$(dmesg 2>/dev/null | grep -iE 'mce|machine.check|hardware error|edac' | wc -l)
echo "MCE/EDAC/hardware-error log lines: $err_count"
if [ "$err_count" -gt 0 ]; then
    echo "(first 5 lines)"
    dmesg 2>/dev/null | grep -iE 'mce|machine.check|hardware error|edac' | head -5
fi

hr "Quiescence verdict"
# Simple heuristic: idle > 95% and load1 < 1.0 = quiet system
load1=$(awk '{print $1}' /proc/loadavg)
load1_int=$(echo "$load1" | awk '{print int($1*10)}')   # ×10
idle_ok=$([ "${pct_idle:-0}" -ge 95 ] && echo 1 || echo 0)
load_ok=$([ "$load1_int" -le 10 ] && echo 1 || echo 0)
if [ "$idle_ok" -eq 1 ] && [ "$load_ok" -eq 1 ]; then
    echo "VERDICT: SYSTEM IS QUIET. Idle=${pct_idle}%, load1=$load1."
    echo "         Measurements should not be contaminated by background load."
else
    echo "VERDICT: SYSTEM IS NOT FULLY QUIET."
    echo "         idle=${pct_idle}% (need ≥95%)"
    echo "         load1=$load1 (need ≤1.0)"
    echo "         Inspect 'Top 15 CPU-using processes' above."
fi

echo
echo "=== end of snapshot ==="
