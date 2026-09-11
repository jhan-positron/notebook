#!/usr/bin/env bash
# AMD test: does the AMX-enabled runtron take the AVX path on AMD EPYC (andoria-06, second half)?
# Words: runtron = tron's command-line tool; AMX = Intel matrix instructions (absent on AMD);
# available() = tron's runtime AMX probe (CPUID -> XCR0 -> arch_prctl); the amxprobe shim logs the
# arch_prctl call the probe makes when CPUID and XCR0 pass; arm on = TRON_AMX_DISABLE unset,
# arm off = TRON_AMX_DISABLE=1 (the kill switch). USE_HW_ATTN=0 = attention on the CPU, where the
# AMX dispatch lives. --instance 1,2 = the second half of the machine (FPGA cards 4-7).
set -o pipefail
WT=~/workspace/tron-amx; BIN=$WT/gen-amd/runtron
OUT=~/workspace/intel-AMX/exec/logs/amd-amx-20260911; mkdir -p $OUT /var/tmp/jhan
SHIM=/var/tmp/jhan/amxprobe-andoria06.so
PROMPT=~/workspace/intel-AMX/exec/t1-prompt.txt
H=$(hostname); ts() { date -u +%FT%TZ; }
echo "=== $H $(ts) head=$(git -C $WT rev-parse --short=10 HEAD)"
echo "--- CPU"; lscpu | grep -E "Model name" | sed -E 's/\s+/ /g'; grep -o -w -E "amx_[a-z0-9]+" /proc/cpuinfo | sort -u | tr '\n' ' '; echo "(amx flags above; empty = none)"
echo "--- binary"; ls -la $BIN | cut -c1-100; grep -o "TRON_AMX_DISPATCH:BOOL=[A-Z]*" $WT/gen-amd/CMakeCache.txt
echo "AMX tile instructions in the binary (objdump count of tdpbf16ps): $(objdump -d --no-show-raw-insn $BIN 2>/dev/null | grep -c -w tdpbf16ps)"
echo "AMX kernel symbols: $(nm -C $BIN 2>/dev/null | grep -c 'amx_attn_h128g4::')"
echo "--- hugepage files before"; ls -la /dev/hugepages | tail -n +2 | cut -c1-110
cd $WT
for arm in on off; do
  rm -f $OUT/$H-$arm.probe $OUT/$H-$arm.tokens
  ENVX=(env -u SYSTEM_CONFIG -u TRON_AMX_DISABLE USE_HW_ATTN=0 LD_PRELOAD=$SHIM AMXPROBE_FILE=$OUT/$H-$arm.probe)
  [ $arm = off ] && ENVX+=(TRON_AMX_DISABLE=1)
  t0=$(date +%s)
  timeout 600 "${ENVX[@]}" $BIN stream-generate-text --instance 1,2 --fuse-mount /var/tmp/jhan/fuse-amx-$arm \
    -m ingested-qwen-3-4b-instruct-2507-tp2 -f $PROMPT --prompt-length 256 -l 32 --temperature 0 \
    --pay-for-determinism --output-token-file $OUT/$H-$arm.tokens > $OUT/$H-$arm.log 2>&1
  rc=$?
  echo "=== $H arm=$arm rc=$rc in $(( $(date +%s) - t0 )) s"
  echo "probe file ($OUT/$H-$arm.probe):"; sort $OUT/$H-$arm.probe 2>/dev/null | uniq -c
  grep -m1 -E "HW attention (dis|en)abled" $OUT/$H-$arm.log | sed -E "s/.*\] //" | cut -c1-140
  grep -m1 -E "Generating .* took" $OUT/$H-$arm.log | sed -E "s/.*\] //" | cut -c1-140
  grep -i -m3 -E "error|fail|illegal|SIGILL" $OUT/$H-$arm.log | cut -c1-160
done
echo "--- tokens on vs off"; cmp $OUT/$H-on.tokens $OUT/$H-off.tokens && echo "IDENTICAL" || echo "DIFFER"
echo "--- hugepage files after"; ls -la /dev/hugepages | tail -n +2 | cut -c1-110
echo "=== done $(ts)"
