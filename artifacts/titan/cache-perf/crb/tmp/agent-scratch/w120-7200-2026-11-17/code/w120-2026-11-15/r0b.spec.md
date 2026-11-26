# `r0b.spec` explained, line by line

- Source file: `w120-2026-11-15/r0b.spec` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 10 lines, 2015 bytes).
- sha256 of the source when this page was built: `011de2c15a2e226a962c891d7d5c1ae73eeb33456b37e52e579bb22117395967`.

## Short version: purpose

`r0b.spec` is a spec file of the 120-thread investigation: 10 lines of the form `tag|arguments`, one runner process per line. The first three processes run six read kernels with 120 threads and three different sets of core counters. The other seven run five read kernels in seven thread layouts on the two meshes, without counters.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Common stop**: a stop rule of the runners: all threads have one common deadline. Each thread ends its interval at its first clock read at or after that deadline.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Tag**: the name of a process. The script `rx.sh` writes the output of the process to the file `TAG.csv`.
- **Layout**: the number of threads on mesh 0 and on mesh 1. "64 plus 56" means 64 threads on mesh 0 and 56 threads on mesh 1.
- **`read_nop64`, `read_nop96`, `read_nop128`**: the `asmread` loop with 64, 96 or 128 `nop` instructions after the 8 loads of each 256 B. A `nop` is an instruction that does nothing.
- **`read_1pl`**: a read kernel with one load per 64 B line: four loads of 16 B per 256 B.

## Main flow

1. Read one line as one process. The text before the first `|` is the tag. The rest of the line holds the arguments of the runner, as the function `main` of the runner source reads them (line 1).
2. `--threads` and `--cpus` give the number of threads and the CPU of each thread. The digits of a tag such as `L6432` repeat the layout (lines 4 to 10).
3. `--bytes` gives the size of the buffer that each thread owns and reads. `256M` means 256 MiB.
4. `--stop common` and `--min-ms` give the timing of an interval. The main thread sets one start time and one stop time for all threads. Each thread reads its buffer in chunks of 2 MiB, reads the clock after each chunk and stops at the first clock reading at or after the stop time.
5. `--start common` makes each thread begin at the first byte of its buffer.
6. `--seq` gives the kernels: one timed interval per kernel, in the order of the list. `--rounds` gives the number of times that the whole sequence runs.
7. `--count`, `--pmu-type` and `--events` turn on the core counters (lines 1 to 3). Each thread counts the named events during each interval. An event is written `name=code`. The runner uses the name as the head of a column and gives the code and the number of `--pmu-type` to Linux.

## Behavior a reader must know

- The file holds no command. It has the form that the script `rx.sh` reads: `rx.sh` starts one process per line, in the order of the file, and limits each process to the CPUs 0 to 119.
- The launch record of the result folder `w120-R0b-20261115T170342Z` holds 10 launch lines with the tags and the arguments of this file. Its `env.txt` names the binary `bwx11` [Ref1].
- By the runner source, the runner times each interval itself. Before each interval every thread runs the kernel once over its whole buffer without timing.
- By the runner source, the runner prints for each thread its bytes and its own time, from its start to its last clock reading. The total rate that it prints for an interval is the bytes of all threads divided by the longest time of a thread.
- The names `l1d_refill_prf` and `l2d_refill_prf` of line 3 do not fit their codes [Ref2].

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/r0b.spec` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (10 lines, 2015 bytes, sha256 `011de2c15a2e226a962c891d7d5c1ae73eeb33456b37e52e579bb22117395967`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `cA\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128,read_1pl --count --pmu-type 11 --events cycles=0x11,inst=0x08,bus_access=0x19,l2d_cache=0x16,l3d_refill=0x2a,l3d_cache=0x2b` | Process `cA`: 120 threads, six read kernels, the first of three sets of core counters. `--threads 120 --cpus 0-63,64-119`: thread number i is pinned to entry i of the list. So 64 threads run on mesh 0 (CPUs 0 to 63) and 56 on mesh 1 (CPUs 64 to 119). `--bytes 256M`: 256 MiB per thread. `--stop common --start common --min-ms 4000`: all threads stop at one common time, 4000 ms after the common start, and each thread begins at the first byte of its buffer. `--rounds 1`: the sequence runs once. `--seq`: 6 kernels, one interval each: `oldread`, `asmread`, `read_nop64`, `read_nop96`, `read_nop128`, `read_1pl`. `--count --pmu-type 11 --events`: each thread counts 6 events, written `name=code`: `cycles` (processor cycles), `inst` (instructions executed), `bus_access` (bus accesses), `l2d_cache` (accesses to the level 2 data cache), `l3d_refill` (refills of the level 3 data cache), `l3d_cache` (accesses to the level 3 data cache) [Ref2]. |
| 2 | `cB\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128,read_1pl --count --pmu-type 11 --events inst_spec=0x1b,l2d_alloc=0x20,l3d_alloc=0x29,ll_cache_rd=0x36,remote_access=0x31,l2d_wb=0x18` | Process `cB`: the same threads, timing and kernels as line 1, with the second set of six events: `inst_spec` (operations executed speculatively), `l2d_alloc` (allocations in the level 2 data cache without a refill), `l3d_alloc` (the same for the level 3 data cache), `ll_cache_rd` (read accesses to the last cache level), `remote_access` (accesses to another socket), `l2d_wb` (write-backs from the level 2 data cache) [Ref2]. |
| 3 | `cC\|--threads 120 --cpus 0-63,64-119 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128,read_1pl --count --pmu-type 11 --events l1d_hwprf=0x8154,l2d_hwprf=0x8155,l1d_refill_hwprf=0x81bc,l2d_refill_hwprf=0x81bd,l1d_refill_prf=0x8145,l2d_refill_prf=0x8146` | Process `cC`: the same threads, timing and kernels as line 1, with the third set of six events: `l1d_hwprf` and `l2d_hwprf` (hardware prefetches of the level 1 and of the level 2 data cache), `l1d_refill_hwprf` and `l2d_refill_hwprf` (refills of these two caches by a hardware prefetch), `l1d_refill_prf` and `l2d_refill_prf`. The last two names do not fit their codes. In the table of the Arm events [Ref2] the code `0x8145` is `L1I_CACHE_HWPRF`, a hardware prefetch of the level 1 instruction cache. The code `0x8146` is `L1D_CACHE_REFILL_PRFM`, a refill of the level 1 data cache by a software prefetch. |
| 4 | `L5656\|--threads 112 --cpus 0-55,64-119 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L5656`: the layout 56 plus 56. `--threads 112 --cpus 0-55,64-119`: 56 threads on mesh 0 (CPUs 0 to 55) and 56 on mesh 1 (CPUs 64 to 119). `--seq`: 5 kernels: `oldread`, `asmread`, `read_nop64`, `read_nop96`, `read_nop128`. The line has no `--count`, so no event is counted. The other arguments are those of line 1: 256 MiB per thread, the common stop after 4000 ms, one round. |
| 5 | `L6432\|--threads 96 --cpus 0-63,64-95 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L6432`: the layout 64 plus 32. `--threads 96 --cpus 0-63,64-95`: 64 threads on mesh 0 (CPUs 0 to 63) and 32 on mesh 1 (CPUs 64 to 95). The kernels and the other arguments are those of line 4. |
| 6 | `L6444\|--threads 108 --cpus 0-63,64-107 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L6444`: the layout 64 plus 44. `--threads 108 --cpus 0-63,64-107`: 64 threads on mesh 0 (CPUs 0 to 63) and 44 on mesh 1 (CPUs 64 to 107). The kernels and the other arguments are those of line 4. |
| 7 | `L4848\|--threads 96 --cpus 0-47,64-111 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L4848`: the layout 48 plus 48. `--threads 96 --cpus 0-47,64-111`: 48 threads on mesh 0 (CPUs 0 to 47) and 48 on mesh 1 (CPUs 64 to 111). The kernels and the other arguments are those of line 4. |
| 8 | `L3232\|--threads 64 --cpus 0-31,64-95 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L3232`: the layout 32 plus 32. `--threads 64 --cpus 0-31,64-95`: 32 threads on mesh 0 (CPUs 0 to 31) and 32 on mesh 1 (CPUs 64 to 95). The kernels and the other arguments are those of line 4. |
| 9 | `L6400\|--threads 64 --cpus 0-63 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L6400`: mesh 0 alone. `--threads 64 --cpus 0-63`: 64 threads on the CPUs 0 to 63, and no thread on mesh 1. The kernels and the other arguments are those of line 4. |
| 10 | `L0056\|--threads 56 --cpus 64-119 --bytes 256M --stop common --start common --min-ms 4000 --rounds 1 --seq oldread,asmread,read_nop64,read_nop96,read_nop128` | Process `L0056`: mesh 1 alone. `--threads 56 --cpus 64-119`: 56 threads on the CPUs 64 to 119, and no thread on mesh 0. The kernels and the other arguments are those of line 4. |

## References

- [Ref1] test data: the files `launches.txt` and `env.txt` in the folder `tests/2026-11-15-whole-chip-read-drop/w120-R0b-20261115T170342Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`.
- [Ref2] external source: Linux source tree, file `tools/perf/pmu-events/arch/arm64/common-and-microarch.json`. It lists the common Arm counter events with code, name and a short description.
