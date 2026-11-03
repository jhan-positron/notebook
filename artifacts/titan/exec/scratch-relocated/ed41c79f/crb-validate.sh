#!/bin/bash
# Wait for Jeremy's Sat 06:00-07:30 UTC block to end, then validate the Asimov tools on CRB.
set -u
while [ "$(date -u +%H%M)" -lt 0735 ]; do sleep 60; done
H=jhan@192.168.2.45
echo "start $(date -u)"
if ssh -o BatchMode=yes $H 'test -e /tmp/positron-perf.RUNNING'; then echo "RUNNING marker present, aborting"; exit 3; fi
ssh -o BatchMode=yes $H 'mkdir -p ~/cache-perf/asimov' && scp -q /home/jhan/workspace/titan/cache-perf/asimov/{common.h,latency.c,bandwidth.c,Makefile,run_asimov.sh,README.md} $H:~/cache-perf/asimov/ || exit 2
ssh -o BatchMode=yes $H 'set -e; cd ~/cache-perf/asimov
test -e /tmp/positron-perf.RUNNING && { echo RUNNING; exit 3; }
echo "## build with Jesse flags"; if ! make -B CC=gcc 2>&1; then echo "## static build failed, retry -march=native"; make -B CC=gcc CFLAGS="-O2 -march=native" 2>&1; fi
file latency bandwidth | sed "s/,.*linked/ linked/"
T=~/cache-perf/asimov-results/$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $T
echo "## quick plan under taskset 0-119 (cpus 3,5)"
taskset -c 0-119 sh run_asimov.sh --quick --out $T 2>&1 | tail -5
echo "## perf + flush sanity on cpu 3"
taskset -c 0-119 ./latency --cpu 3 --perf --loads 64K --reps 2 --sizes 16K,1M,8M 2>&1 | tee $T/sanity-perf.csv
taskset -c 0-119 ./latency --cpu 3 --perf --flush --reps 2 --sizes 1M,64M 2>&1 | tee $T/sanity-flush.csv
taskset -c 0-119 ./latency --cpu 3 --perf --fresh 3 --sizes 8M,64M 2>&1 | tee $T/sanity-fresh.csv
taskset -c 0-119 ./bandwidth --threads 1 --cpus 3 --bytes 32K --kernel all --passes 256 --reps 2 2>&1 | tee $T/sanity-bw.csv
taskset -c 0-119 ./bandwidth --threads 1 --cpus 3 --bytes 32K --kernel ldr16 --passes 256 --reps 2 2>&1 | grep -v "^#" | tee -a $T/sanity-bw.csv
taskset -c 0-119 ./bandwidth --threads 1 --cpus 3 --bytes 32K --kernel str16 --passes 256 --reps 2 2>&1 | grep -v "^#" | tee -a $T/sanity-bw.csv
taskset -c 0-119 ./bandwidth --threads 1 --cpus 3 --bytes 1M --kernel read --flush-before --passes 1 --reps 2 2>&1 | tail -3 | tee $T/sanity-bwflush.csv
echo "## results in $T"; ls $T'
RC=$?
mkdir -p /home/jhan/workspace/titan/cache-perf/asimov/crb-validation && scp -q -r "$H:~/cache-perf/asimov-results/*" /home/jhan/workspace/titan/cache-perf/asimov/crb-validation/ 2>/dev/null
echo "done rc=$RC $(date -u)"
