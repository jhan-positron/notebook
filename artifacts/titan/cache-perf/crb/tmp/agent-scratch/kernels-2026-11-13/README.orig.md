# cache-perf bench

Short version: `latency` measures load-to-use latency of one dependent load
per cache level with a random pointer chase. `bandwidth` measures streaming
read, write and copy throughput with pinned pthreads. `run_crb.sh` runs the
whole plan on CRB (the 128-core aarch64 server; only CPUs 0-119 may be used)
and `summarize.py` turns the results into markdown tables.

Sizes use K/M/G = 1024, 1024^2, 1024^3 bytes.

## Files

- `latency.c` - single thread, pointer chase over a random cycle (Sattolo's
  algorithm: a shuffle that produces one cycle through every 64 B line).
  Prints `size_bytes,rep,loads,ns_per_load` and a `best` line per size.
- `bandwidth.c` - T pthreads, each pinned to a CPU from `--cpus`, each with
  its own first-touched buffer. Kernels: read (16-accumulator sum), write
  (store a runtime value), copy (dst[i] = src[i]), and the aarch64-only asm
  kernels asmread, asmwrite, asmcopy (see below; `--kernel asmall` runs the
  three, `--kernel all` stays read,write,copy). Prints
  `kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps`
  and a `best` line per kernel.
- `Makefile` - `make` builds both; `make clean` removes them.
- `run_crb.sh` - the CRB measurement plan (CPUs 0-119 only, latency on CPU 3).
  The script re-executes itself under `taskset -c 0-119`, so every child runs
  inside that mask. `--quick` runs a tiny version for a smoke test;
  `CPUS=0-7 ./run_crb.sh --quick` limits the CPU list (default `CPUS=0-119`;
  values outside 0-119 are refused).
- `summarize.py` - reads a results directory and prints markdown tables.

## asm kernels

The asm kernels (asmread, asmwrite, asmcopy) are hand-written AArch64 loops in
`bandwidth.c`. Each iteration moves 256 B with eight `ldp`/`stp` instructions
on 16 B q registers, then one add, one compare and one branch. They exist
because the compiler's read loop issues 8 adds per 8 loads and reaches 24 B/cycle
on CRB; the asm kernels issue only loads/stores, so their only limit is the
core's load/store pipes. They need `--bytes` to be a multiple of 256 and are
refused on non-aarch64 hosts (exit 2).

## Build on CRB

    cd bench && make          # gcc 14, -O3 -march=native, no external libraries

## Run on CRB

    ./run_crb.sh              # refuses to start and exits 3 if /tmp/positron-perf.RUNNING exists
    ./summarize.py ~/cache-perf/results/<UTC timestamp> --ghz 2.8

Results are written to `$HOME/cache-perf/results/<UTC timestamp>/`:
`latency.csv`, `latency-perfrun-{short,long}.csv` and
`latency-perf-<size>-{short,long}.csv` (perf stat counters for two one-rep
runs per size: "short" times exactly 2 cycles, "long" times at least 1 s and
6 cycles), `bandwidth.csv`, `sysinfo.txt`, `log.txt`.

## Reading the output

- Latency: `ns_per_load` = elapsed / loads. `best` = minimum over reps.
  Cycles = ns x 2.8 GHz. The levels summary picks L1 from 16K-32K, L2 from
  256K-1M, L3 from 8M-64M, DRAM from 1G-2G.
- Bandwidth: GB = 1e9 bytes. `aggregate_GBps` = sum of bytes over all threads
  / the slowest thread's elapsed time. Copy counts read + write bytes.
  The levels summary reports the best aggregate per regime (32K = L1,
  1M = L2, 8M = L3, 1G and 256M = DRAM per thread) and the 1-thread value.
  Copy uses two buffers per thread, so in the L3 regime its thread list is
  shorter (up to 7 threads x 16 MiB = 112 MiB) than read/write's (up to 14
  threads x 8 MiB = 112 MiB).

## Caveats

- The pointer chase measures the latency of dependent loads with the
  prefetcher defeated (random order, one outstanding load). It is the
  best-case load-to-use latency at that footprint, not an average under load.
- Refills/load come from two perf runs per size with identical setup
  (permutation build, warm-up) and different timed-load counts. The summary
  divides the difference of the counts by the difference of the loads, so the
  setup cancels and the value is the rate of the timed chase alone.
- Both programs ask for transparent huge pages with `madvise(MADV_HUGEPAGE)`;
  `--no-thp` asks for `MADV_NOHUGEPAGE` instead (needed on CRB, where THP is
  "always"). `latency` prints the process's `AnonHugePages` after first
  touch; 0 kB means the kernel gave 4 KiB pages and TLB walks are part of
  the measured latency for large sizes.
- In the L1 and L2 regimes the copy kernel's two buffers together equal the
  cache size exactly (2 x 32 KiB = 64 KiB, 2 x 1 MiB = 2 MiB), so a few sets
  also hold stack or static data; the effect is under about 1%.
- Each bandwidth pass pays a fixed cost outside the vector loop (call,
  accumulator setup, reduction, sink store). At 32 KiB per pass this is a
  few percent, so the L1-regime bandwidth is a lower bound by that much.
- Arm cores may detect a long run of full-line stores with no loads (the
  write kernel) and switch to write-streaming mode, which bypasses L1/L2
  allocation. If write at 32K on 1 thread is far below read at 32K, check
  with `perf stat -e l1d_cache_refill,l2d_cache_refill -- ./bandwidth
  --threads 1 --cpus 3 --bytes 32K --kernel write`: refills near bytes/64 per
  pass mean streaming mode is active and the L1/L2 write numbers are
  L3-bound.
- Bandwidth threads check the clock after at least 8 MiB of work, not after
  every pass, so clock reads do not distort small-buffer results.
- Runs are only meaningful on an idle machine with a fixed clock. The script
  refuses to run while another team's marker file exists.
