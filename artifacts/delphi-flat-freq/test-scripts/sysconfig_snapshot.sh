#!/bin/bash
# sysconfig_snapshot.sh — capture every machine/software knob known (or
# suspected) to move inference perf, in ONE diff-friendly text file.
# Motivation: the July-3 2026 clamped-decode anomaly became permanently
# unexplainable because no record of the era's host state exists. Diff
# two snapshots to explain a future repro failure in minutes.
# Usage: sysconfig_snapshot.sh [outfile]
#   default: /scratch/jhan/sysconfig_snapshots/<host>_<utc>.txt
# READ-ONLY. Safe to run any time, including during benchmarks/nightly.
set -u
HOST=$(hostname -s)
OUT="${1:-/scratch/jhan/sysconfig_snapshots/${HOST}_$(date -u +%Y%m%d_%H%M%S).txt}"
mkdir -p "$(dirname "$OUT")"
ISST=/opt/intel-speed-select/intel-speed-select
sec(){ echo; echo "===== $1 ====="; }
{
echo "host: $HOST   captured: $(date -u '+%F %T') UTC   boot: $(uptime -s)"

sec "kernel + cmdline (tsx=, hugepages=, isolcpus=...)"
uname -r
cat /proc/cmdline

sec "bios + microcode"
sudo -n dmidecode -s bios-version 2>/dev/null
sudo -n dmidecode -s bios-release-date 2>/dev/null
grep -m1 microcode /proc/cpuinfo
grep -m1 "model name" /proc/cpuinfo

sec "cpu feature flags of interest (rtm = TSX/RTM available)"
grep -m1 -o "\brtm\b" /proc/cpuinfo || echo "rtm ABSENT"
grep -m1 -o "\bhle\b" /proc/cpuinfo || echo "hle absent"

sec "frequency control: isst feature state"
sudo -n $ISST core-power info 2>&1 | grep -viE "^$|executing" | head -20
sudo -n $ISST perf-profile info 2>&1 | grep -iE "clos|enable|priority|level" | head -30

sec "frequency control: per-cpu CLOS association (the tron112 shape)"
sudo -n $ISST --cpu 0-287 core-power get-assoc 2>&1 | grep -E "cpu-|clos:" | paste - - | sort -t- -k2 -n

sec "uncore frequency (per package)"
for d in /sys/devices/system/cpu/intel_uncore_frequency/package_*; do
  [ -d "$d" ] || continue
  echo "$(basename $d): min=$(cat $d/min_freq_khz 2>/dev/null) max=$(cat $d/max_freq_khz 2>/dev/null) initial_min=$(cat $d/initial_min_freq_khz 2>/dev/null) initial_max=$(cat $d/initial_max_freq_khz 2>/dev/null)"
done

sec "scaling driver / governor / cpuidle"
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_driver 2>/dev/null
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null
for s in /sys/devices/system/cpu/cpu0/cpuidle/state*; do
  echo "$(cat $s/name): disable=$(cat $s/disable)"
done

sec "RAPL power limits"
for r in /sys/class/powercap/intel-rapl:*; do
  [ -e "$r/name" ] || continue
  echo "$(cat $r/name): limit0=$(cat $r/constraint_0_power_limit_uw 2>/dev/null) limit1=$(cat $r/constraint_1_power_limit_uw 2>/dev/null)"
done

sec "memory config (DIMM speeds)"
sudo -n dmidecode -t 17 2>/dev/null | grep -E "^\s+(Speed|Configured Memory Speed):" | sort | uniq -c

sec "numa + hugepages + THP"
grep -E "HugePages_Total|HugePages_Free|Hugepagesize" /proc/meminfo
for n in /sys/devices/system/node/node*/hugepages/hugepages-1048576kB; do
  echo "$(dirname $n | xargs dirname | xargs basename): total=$(cat $n/nr_hugepages) free=$(cat $n/free_hugepages)"
done
cat /sys/kernel/mm/transparent_hugepage/enabled
ls -la /dev/hugepages/ 2>/dev/null | awk "NR>1{print \$NF, \$5}" | sort | head -20

sec "boot freq service config"
cat /etc/default/intel-speed-select-state 2>/dev/null

sec "tron / platform software versions"
dpkg -l 2>/dev/null | grep -iE "tron|positron|platformd" | awk "{print \$2, \$3}" | sort
strings /opt/positron/bin/rinzler 2>/dev/null | grep -m2 -E "^v?2026\.[0-9]+\.[0-9]+-[0-9a-f]{8}" | sort -u
md5sum /opt/positron/config/resource-map.yaml /opt/positron/bin/../config/resource-map.yaml 2>/dev/null | sort -u

sec "platformd inference config"
curl -s -m 5 http://localhost:8080/api/config 2>/dev/null | python3 -m json.tool 2>/dev/null | grep -vE "^\s*$" | head -60

sec "rinzler instance envs (md5 + key lines)"
for f in /etc/rinzler/instance-*.env; do
  [ -e "$f" ] || continue
  echo "$f md5=$(sudo -n md5sum "$f" 2>/dev/null | cut -d" " -f1)"
  sudo -n grep -E "CPUAFFINITY|TRON_USE_SPECULATION|app-cores|dev-cores" "$f" 2>/dev/null | sed "s/^/  /"
done

sec "FPGA pcie link status (degraded link = silent perf loss)"
for bdf in $(lspci -d 1ed9: -D 2>/dev/null; lspci -D 2>/dev/null | grep -i "processing accel" | cut -d" " -f1); do
  st=$(sudo -n lspci -vv -s "$bdf" 2>/dev/null | grep -m1 "LnkSta:")
  echo "$bdf $st"
done | sort -u

sec "login-shell env landmines (what a user shell would inject)"
bash -lc 'echo "SYSTEM_CONFIG=${SYSTEM_CONFIG:-<unset>}"; echo "TRON_LOG_LEVEL=${TRON_LOG_LEVEL:-<unset>}"; echo "SPDLOG_LEVEL=${SPDLOG_LEVEL:-<unset>}"; echo "TRON_NO_RTM=${TRON_NO_RTM:-<unset>}"; echo "TRON_USE_ARENA_ALLOCATOR=${TRON_USE_ARENA_ALLOCATOR:-<unset>}"; echo "memlock=$(ulimit -l)"' 2>/dev/null

sec "engine runtime provenance (current serving processes)"
for p in $(pgrep -x rinzler | head -4); do
  echo "pid $p: $(ps -o lstart= -p $p)"
done
sudo -n journalctl -u rinzler@0 --no-pager 2>/dev/null | grep -E "Intel RTM|arena allocator|Pinning application" | tail -6
} > "$OUT" 2>&1
echo "snapshot: $OUT ($(wc -l < "$OUT") lines)"
