#!/usr/bin/env bash
# prep.sh - one login, no root: record the machine state, build ASCT's probe variant of the memory benchmark
# binary from ASCT's own source tarball with ASCT's own flags (src/core/config/ubench.json), resolve the counter
# event codes, save the machine code of the read loops, and run a 3-process smoke test on CPU 2.
# Writes only under ~/cache-perf. CPUs 0-119 only.
set -u
M=/tmp/positron-perf.RUNNING
[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }
W=$HOME/cache-perf/asct-20261116
out=$HOME/cache-perf/results/asct-prep-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out
cd $W || exit 2
PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin
{
  echo "utc $(date -u +%FT%TZ)"; echo "kernel $(uname -r)"; echo "loadavg $(cat /proc/loadavg)"; echo "users $(who | wc -l)"; who
  echo "nproc $(nproc) online $(cat /sys/devices/system/cpu/online) isolated $(cat /sys/devices/system/cpu/isolated)"
  echo "shell affinity $(taskset -pc $$ | sed 's/.*: //')"
  echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"
  echo "thp enabled $(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag $(cat /sys/kernel/mm/transparent_hugepage/defrag)"
  grep -H . /sys/devices/system/node/node*/hugepages/hugepages-*kB/free_hugepages
  echo "numa nodes $(ls -d /sys/devices/system/node/node[0-9]* | wc -l)"
  echo "governor cpu2 $(cat /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor 2>/dev/null) cpu41 $(cat /sys/devices/system/cpu/cpu41/cpufreq/scaling_governor 2>/dev/null)"
  echo "sysreg dir: $(ls -d /sys/kernel/sysreg 2>&1)"
  echo "pmu units: $(ls /sys/bus/event_source/devices/ | tr '\n' ' ')"
  echo "core pmu type $(cat /sys/bus/event_source/devices/armv8_pmuv3_0/type)"
  echo "numactl $(command -v numactl || echo none) venv-numactl $(ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null || echo none)"
  echo "gcc $(gcc --version | head -1)"; echo "perf $(perf --version)"
  echo "sudo without password: $(sudo -n true 2>/dev/null && echo yes || echo no)"
  echo "cmdline $(cat /proc/cmdline)"
  ps -eo user,pcpu,comm --sort=-pcpu | head -6
} > $out/env.txt 2>&1
# build the probe variant and, as a check of the build recipe, the plain variant
SD=$HOME/asct/asct-0.7.1+77461b3/asct-0.7.1+77461b3.tar.gz
sha256sum $SD > $out/sha.txt
rm -rf build && mkdir build && tar --no-same-owner -xzf $SD -C build
L=$W/build/asct-0.7.1+77461b3/extern/infra-microbenchmarks/loaded-latency
DP=$W/build/asct-0.7.1+77461b3/extern/dietperf
{
  cd $L
  make clean EXE=loaded-latency-asct-probe-sve.bin
  make EXE=loaded-latency-asct-probe-sve.bin CFLAGS="-DASCT -DUSE_PROBE -DHAS_SVE -march=armv8.2-a+sve -I$DP" && cp loaded-latency-asct-probe-sve.bin $W/
  make clean EXE=loaded-latency-asct-probe-sve.bin
  make EXE=loaded-latency-asct-sve.rebuild.bin CFLAGS="-DASCT -DHAS_SVE -march=armv8.2-a+sve" && cp loaded-latency-asct-sve.rebuild.bin $W/
  cd $W
} > $out/build.txt 2>&1
PROBE=$W/loaded-latency-asct-probe-sve.bin
sha256sum $PLAIN $PROBE $W/loaded-latency-asct-sve.rebuild.bin >> $out/sha.txt 2>&1
# machine code of the two read loops in each binary; addresses removed so that the texts can be compared
for b in $PLAIN $PROBE $W/loaded-latency-asct-sve.rebuild.bin; do
  n=$(basename $b)
  objdump -d --no-show-raw-insn $b | awk '/^[0-9a-f]+ <(my_read|my_read_no_nops_rep_64b|run_bw_repetitions)>:/{p=1} p{print} p&&/^$/{p=0}' > $out/listing.$n.txt
  sed -E 's/^ *[0-9a-f]+:\s*//; s/[0-9a-f]+ <([a-z_0-9]+)\+0x[0-9a-f]+>/<\1+off>/g; s/^[0-9a-f]+ </</' $out/listing.$n.txt > $out/listing.$n.noaddr.txt
done
cmp -s $out/listing.$(basename $PLAIN).noaddr.txt $out/listing.loaded-latency-asct-sve.rebuild.bin.noaddr.txt && echo "read loops: installed plain == rebuilt plain" >> $out/sha.txt || echo "read loops: installed plain DIFFERS from rebuilt plain" >> $out/sha.txt
objdump -d --no-show-raw-insn $PLAIN | awk '/<my_read_no_nops_rep_64b>:/{p=1} p{print} p&&/^$/{p=0}' | grep -c . >> $out/sha.txt
# event codes
perf list --details > $out/perf-list-details.txt 2>&1
python3 resolve_events.py events.txt events.codes > $out/resolve.txt 2>&1
cp events.codes $out/
# smoke test on CPU 2: plain, then probe with set A and set B, 1 MiB
NUMA=$(command -v numactl || ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)
ARGS="--duration 0.25 --delay-seconds 0 --bw-cpu 2 --bw-buflen 1048576 --bw-fine-delay 0 --bw-write=0 --bw-cacheline-bytes 64"
[ -e $M ] && { echo "marker: stop"; exit 3; }
taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PLAIN $ARGS > $out/smoke.plain.out 2>&1; echo "rc plain $?" >> $out/smoke.txt
while IFS='|' read -r s evs; do
  [ -z "$evs" ] && continue
  codes=$(echo "$evs" | tr ',' '\n' | cut -d= -f2 | paste -sd,)
  mkdir -p $out/smoke.$s.d
  DIETPERF_OUTDIR=$out/smoke.$s.d DIETPERF_PMUv3=$codes taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PROBE $ARGS > $out/smoke.probe.$s.out 2>&1 < /dev/null; echo "rc probe $s $? codes $codes" >> $out/smoke.txt
done < events.codes
# two threads with the probe variant: one counter file per thread is expected
mkdir -p $out/smoke.two.d
DIETPERF_OUTDIR=$out/smoke.two.d DIETPERF_PMUv3=0x11,0x8 taskset -c 0-119 $PROBE --duration 0.25 --delay-seconds 0 --bw-cpu 2 --bw-cpu 66 --bw-buflen 1048576 --bw-fine-delay 3 --bw-write=0 --bw-cacheline-bytes 64 > $out/smoke.two.out 2>&1 < /dev/null; echo "rc two-thread probe $? files $(ls $out/smoke.two.d | wc -l)" >> $out/smoke.txt
# a 4 KiB-page or 2 MiB-page buffer? AnonHugePages of a 64 MiB run, read while it runs
taskset -c 0-119 $PLAIN --duration 1 --delay-seconds 0 --bw-cpu 2 --bw-buflen 67108864 --bw-fine-delay 0 --bw-write=0 --bw-cacheline-bytes 64 > $out/smoke.thp.out 2>&1 &
p=$!; sleep 1.2; grep -E "AnonHugePages|Rss" /proc/$p/smaps_rollup > $out/smoke.thp.smaps 2>&1; wait $p
echo "done $out"
cat $out/env.txt; cat $out/sha.txt; tail -3 $out/build.txt; cat $out/resolve.txt; cat $out/smoke.txt
grep -h "Total Bandwidth (MB/sec)\|tid = " $out/smoke.*.out; for d in $out/smoke.*.d; do echo "== $(basename $d)"; cat $d/* 2>&1 | head -16; done; cat $out/smoke.thp.smaps
wc -l $out/listing.*.txt
