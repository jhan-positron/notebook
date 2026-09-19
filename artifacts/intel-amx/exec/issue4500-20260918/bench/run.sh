#!/usr/bin/env bash
# Build and run bench_k_vnni on delphi-3bda, socket-1 spare cores (87 = main, 88 = worker; the l8bload
# client used 87-95; the production engines use 96-143, 223-230 and dev cores 75-78). nice 19.
set -u
B=/home/jhan/workspace/intel-AMX/exec/issue4500-20260918/bench
OUT=/home/jhan/workspace/intel-AMX/exec/results/issue4500-20260918/bench
mkdir -p "$OUT" /var/tmp/jhan/i4500-bench
BIN=/var/tmp/jhan/i4500-bench/bench_k_vnni
clang++-19 -O3 -std=c++20 -march=native -pthread "$B/bench_k_vnni.cpp" -o "$BIN" || exit 1
echo "# bench_k_vnni $(date -u +%FT%TZ) host $(hostname) $(clang++-19 --version | head -1); load $(cut -d' ' -f1-3 /proc/loadavg)" | tee "$OUT/bench.txt"
for rows in 2304 1152 576; do          # 8 / 4 / 2 users x 8 KV heads x 36 layers
  for layout in "" "--rowmajor"; do
    for w in "" "--no-worker"; do
      for rep in 1 2 3; do
        echo "== rows=$rows layout=${layout:-vnni} ${w:-with-worker} rep=$rep" | tee -a "$OUT/bench.txt"
        nice -n 19 "$BIN" --rows $rows --steps 64 --main 87 --worker 88 $layout $w 2>&1 | tee -a "$OUT/bench.txt"
      done
    done
  done
done
echo "# done $(date -u +%FT%TZ)" | tee -a "$OUT/bench.txt"
