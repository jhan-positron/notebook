# bwx: deviations from specification v1, and what only a CRB build can verify

## Short version

`bwx` (the scratch benchmark of Parts B and C) is written and its harness was run on the development machine with stand-in kernels. It has never been compiled for AArch64. This file lists 24 deviations from specification v1 with their reasons, 3 known limits, the local checks, and 12 things that only a build on CRB can verify. Deviations 21 to 24 and the known limits were added after the review of 2026-11-13.

## Words used here

- **Specification v1**: sections B.1 to B.8 of `handoff.md` [Ref1].
- **CRB**: the Arm test machine. **Development machine**: the x86-64 server where this folder is.
- **Stand-in**: a plain C loop that replaces a NEON or asm kernel when the compiler target is not AArch64. It touches the same bytes. Its speed means nothing.
- **PAD**: the number of zero bytes placed between a 64 B boundary and the start of a kernel function.
- **HEAD**: the number of bytes between the start of a kernel function and the start of its loop.
- **LOOP**: the planned offset of a loop start modulo 64.
- **A/A copy**: the same source under a second name (`asmread2`, `asmwrite2`, `asmcopy2`, `oldread2`).
- **probe.txt**: the objdump listings of `bw_new` and `bw_old` of 2026-11-13 [Ref2].
- **smaps lookup**: the search for the buffer in `/proc/self/smaps` (B.6).
- **est.**: an estimate, not a measurement.

## Files

| File | What it is |
|---|---|
| `bwx.c` | The benchmark: 21 kernels, command line, rows I/T/P/C, both stop methods, start offsets, page state, counters. |
| `bwx_selftest.c` | The self-test. `bwx.c` includes it. It runs as `bwx --selftest`. |
| `build.sh` | For CRB: builds 4 binaries, runs 4 self-tests, writes `listing.txt`, `offsets.tsv`, `build.txt`. |
| `check_listing.py` | For the development machine: the acceptance test of B.7 on `listing.txt`. |

`run_bwx.sh` and the other files in this folder were written by another agent. Their deviations are in `DEVIATIONS-scripts.md`.

## Deviations

### Loop placement (B.7)

1. **Directive.** The pad is `.pushsection .text`, `.p2align 6`, `.fill N, 1, 0`, `.popsection`. Specification v1 gives `.text`, `.p2align 6`, `.skip N, 0`.
   - Reason 1: gcc does not record a section change that a file-level asm statement makes. `.pushsection` and `.popsection` leave the section as gcc expects it.
   - Reason 2: `.skip 0, 0` gave the assembler warning ".space repeat count is zero, ignored" on the development machine. `.fill 0, 1, 0` gives none.
2. **Macros.** Each kernel has a macro `PAD_<name>`. For the six kernels with a planned offset, `PAD = (LOOP - HEAD) mod 64`. The build can set `-DHEAD_<name>=N` or `-DPAD_<name>=N`. The default HEAD values (4 B, or 20 B for a kernel that saves d8 to d15) come from probe.txt. They are a guess for `asmcopy_c`, `asmcopy_c_add` (4 B) and `asmcopy_c_reg` (20 B), because no listing of these exists yet.
3. **Other kernels.** Specification v1 says to record the offset that the build gives. I chose a default PAD that equals the function start modulo 64 in `bw_new` (new C and asm kernels) or in `bw_old` (old kernels). So the loops should land where they are in those binaries. The nop variants and `read_sparse` take the PAD of `asmread`. An A/A copy takes the PAD of its original.
4. **Step B3 is three more binaries**, not six more functions: `bwx_o0`, `bwx_o36`, `bwx_o52` (`-DB3_OFFSET=0|36|52`). In them `copy`, `asmcopy` and `asmcopy2` are at the offset. `asmcopy_c*` stay at 52.

### Kernels (B.1)

5. **The asm kernels are macro bodies** (`DEF_ASMREAD`, `DEF_ASMWRITE`, `DEF_ASMCOPY`), so that an A/A copy is the same source. `asmread` and `asmread2` contain `.rept 0 ... .endr`, which must give no instruction. The listing check confirms or rejects this.
6. **`asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg` bind their pointers to x0, x1, x2** with register variables. Reason: the loop text then equals the listing "bw_new k_copy" without a dependence on the register choice of gcc.
7. **Loop end of the three `asmcopy_c*` kernels** is `cmp end, s` and `b.hi`, as in the C loop. Specification v1 does not name the loop end for `_add` and `_reg`. I kept the one of the C loop, so that each variant changes one thing.
8. **Calls go through a table of function pointers** (`kernels[]`, `call()`), not through a `switch` with direct calls as in `bandwidth.c`. Reason: 21 kernels and calls on a part of a buffer. Cost: one indirect call per pass (`--stop pass`) or per 2 MiB (`--stop common`).
9. **Stand-ins.** On a target that is not AArch64, every NEON and asm kernel is a plain C loop. The header line and the self-test print "STAND-IN". The old kernels are the same C source on both targets.

### Command line and rows (B.2, B.3)

10. **`--seq` is required.** There is no default sequence. New option `--list` prints the kernel names (used by `build.sh`). New option `--selftest`.
11. **Added comment lines.** After the header line of `bandwidth.c`: one line `# bwx: ...` with the options, and one line per row type with its column names. `round` and `pos` both count from 0. The first page reading of a multi-thread process has `round` 0 and `pos` -1.
12. **Added line `# page_read,<round>,<pos>,<ms> ms`** after each page reading of the main thread. Reason: B.6 asks to measure this time.
13. **Row order.** One-thread process: P, I, T, C (the P reading is taken before the interval). Multi-thread process: I, T, C, P (the P reading is taken after the interval).
14. **The write value** is `v + pass number` in `pass` mode, as in `bandwidth.c`, and `v + chunk number` in `common` mode.

### Start offsets and page state (B.5, B.6)

15. **Entry sizes that B.5 does not cover.** n is the entry size divided by 2 MiB, rounded down. An entry below 2 MiB has n = 0 and starts at offset 0.
16. **Buffer length.** The buffer length is `--bytes` rounded up to 2 MiB, as in `bandwidth.c`. The smaps lookup uses this rounded length, so `kB_total` is the rounded size.
17. **`mprotect` failure.** The program prints a message and continues. The P rows then show `NA`. Specification v1 does not say what to do.

### Counters (B.8)

18. **No event code is built in.** `--count` needs `--pmu-type N` and `--events NAME=CODE,...` (codes may be `0x..`). Without the two options, `bwx` reads the environment variables `BWX_PMU_TYPE` and `BWX_EVENTS`, because `run_bwx.sh` in this folder passes them that way. A code without a name gets the name of its position: cycles, instructions, l1d_refill, l2d_refill, ll_miss_rd. Without type or events, `bwx --count` exits with status 2.
19. **Order of the readings.** Start: counter group, CPU time, clock. End: clock, CPU time, counter group. Specification v1 gives the place of the group and says "the same two points" for the CPU time. The group leader is the first event that opens. An event that does not open prints `NA`. If no event opens, `enabled_ns` and `running_ns` print `NA`.

### Self-test, build, check

20. **Self-test.** It is a mode of `bwx`, so it runs the machine code of the binary that is timed. Checks beyond `selftest.c`:
    - each read kernel must fault when one page of a 3-page range is made `PROT_NONE` (each of the 3 pages in turn);
    - `oldread` and `oldread2` must return the sum of all words.
    - Limit: for the other read kernels this proves that every page is touched, not every byte.

### Added after the review of 2026-11-13

21. **One more barrier after each page reading (B.6).** In a process with more than one thread, every worker waits on the barrier a second time after the end barrier of an interval, until the main thread has read the page state. The same holds for the first reading: the workers pass the barrier twice before the first warm-up pass. Specification v1 gives one barrier before the first reading and none after a reading.
    - Reason: B.6 says that the warm-up pass of an interval lies between the reading and the timed part. Without the second barrier the workers started the warm-up pass while the main thread still printed rows and read `/proc/self/smaps`.
    - Check: a traced build with 8 threads and 100 intervals. Before the change, 800 of 800 warm-up passes started before the reading of the interval before them. After the change, 0 of 800.
    - Cost: the workers sleep while the main thread prints the I, T and C rows and reads the page state. This time lies between two intervals, not inside one. The line `# page_read` gives the reading time.
    - A process with one thread is unchanged.
22. **`bwx` keeps itself on CPUs 0 to 119.** At its start the main thread removes every CPU above 119 from the allowed set of the process (`sched_setaffinity`). Workers inherit this set. `--cpus` rejects a CPU above 119 with exit status 2. If no permitted CPU is left, `bwx` exits with status 2. The limit is the macro `MAX_USE_CPU`. Another machine can build with `-DMAX_USE_CPU=N`.
    - Reason: without it, a `bwx` call typed by hand on CRB (outside `run_bwx.sh` and its `taskset`) could run its main thread, or a worker without `--cpus`, on CPU 126 or 127. `--cpus 126,127` was accepted.
    - Check: a build with `-DMAX_USE_CPU=15` on the development machine (32 CPUs). Main thread and unpinned worker: allowed list 0-15. With `--cpus 3`: worker 3, main thread 0-15. `--cpus 16`: exit 2. Under `taskset -c 20-25`: exit 2, also for `--selftest`.
    - The worker without `--cpus` still exists (`bandwidth.c` has it). It is confined to CPUs 0 to 119 and prints cpu -1.
23. **Strict numbers.** `--threads`, `--rounds`, `--pmu-type` and `BWX_PMU_TYPE` must be whole numbers in a range (threads 1 to 4096, rounds 1 to 1000000, type 0 to 2147483647). `--min-ms` must be a number above 0. A size that rounds to 0 bytes is rejected (`--bytes` and `@SIZE`). A bad value ends the program with status 2. Before, `atoi`, `atof` and `atol` turned a bad value into 0 without a message. A PMU type that was not a number became type 0, and the raw codes were then counted as generic Linux events under the column names of the core events.
24. **`build.sh` has `EXTRA_<binary>`** (for example `EXTRA_bwx_o0="-DPAD_copy=60"`). It adds compiler options to one of the four builds, after `EXTRA`. Reason: `-DPAD_copy=N` in `EXTRA` replaces the pad of every build, also the `B3_OFFSET` pads of the three B3 builds. So `EXTRA` can carry `-DHEAD_<name>=N`, and a PAD of `copy`, `asmcopy` or `asmcopy2` for one build goes into `EXTRA_<binary>`. `build.txt` records all five variables.

### Known limits (no code change)

- **The main thread shares a CPU with a worker in every run with 120 threads.** The process may use CPUs 0 to 119 only, and the 120 workers are pinned to all of them. So the main thread has no CPU of its own. A reviewer measured this on the development machine with 8 workers on 8 CPUs and 300 intervals: 3.3 to 3.6 s of wall time, against 2.5 to 2.7 s with one spare CPU (3 runs each, load 7.8 to 9.1). The suggested fix was to pin the main thread to CPU 120 to 123. I did not do this, because the handoff allows CPUs 0 to 119 only. What stays valid, from the code: with `--stop common` the main thread sets the common start only after it runs, so a delayed main thread makes the workers wait longer and does not shorten the 2 ms lead. With `--stop pass` the main thread wakes at the start barrier and runs for a short time on the CPU of one worker inside that worker's timed interval. Insufficient data: the size of this effect on CRB. The `late` flags and the end skew of the short run of step 2 of the handoff would show it. A run with fewer than 120 threads has spare CPUs, and the main thread is then not pinned to one.
- **`read_sparse` will have its loop at another offset than the other read variants (est., not measured).** `PAD_read_sparse` equals `PAD_asmread`, so the function starts at 0 modulo 64. `read_sparse` uses q0 to q7 only, so gcc saves no d8 to d15. Its loop then starts 4 B after the function start (est., as `k_asmwrite` in probe.txt), at 4 modulo 64. `asmread`, `asmread2` and `read_nopN` save d8 to d15 and have the loop 20 B after the start, at 20 modulo 64. Specification v1 only asks to record these offsets, so this is no deviation. If equal loop offsets are wanted in step B5, build with `EXTRA="-DPAD_read_sparse=16"` and confirm 20 in `offsets.tsv`. In either case report the offsets of all B5 kernels from `offsets.tsv` next to the B5 result.
- **`check_listing.py` is stricter than B.7 and still does not see everything.** See the list below.

Smaller points of `build.sh` and `check_listing.py` that the specification does not give:

- `build.sh` runs under `taskset -c 0-119`. `BWX_CPUS` changes the list. `BWX_MARKER` replaces the marker path and exists only to test the marker check. `EXTRA` adds compiler options to all 4 builds.
- Both scripts define the loop as the range from the target of the first backward branch of the function to that branch.
- `check_listing.py` requires the four binaries `bwx`, `bwx_o0`, `bwx_o36`, `bwx_o52`. A listing that lacks one fails. `--binaries a,b` names another list. Before the review of 2026-11-13 the list was taken from the listing, so a listing with `bwx` alone passed.
- `check_listing.py` also checks code outside the loop. B.7 names the loop bodies only, so this is stricter than specification v1:
  - For `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`, the four A/A copies and the three old kernels, the whole function must equal the function in probe.txt (branch targets as distances from the function start). If gcc 14.2.0 gives one of them another prologue in `bwx.c` than in `bandwidth.c`, this check fails although the loop is equal. The output then prints both texts side by side, and the lead decides.
  - For `asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg`, `read_nopN` and `read_sparse`, the function must have exactly one backward branch.
  - For every kernel that uses q8 to q15 (`asmread`, `asmread2`, `read_nopN`, `asmcopy`, `asmcopy2`, `asmcopy_c_reg`), the four `stp` of d8 to d15 must stand before the loop and the four `ldp` after it.
  - Not checked: the rest of the code outside the loop of the five kernels that have no listing in probe.txt (for example the end computation of `asmcopy_c_add`). The self-test with guard pages checks what these kernels do to memory. It does not check d8 to d15. Read these functions in `listing.txt` by eye on the first CRB build.
- `check_listing.py` builds the expected loops of `asmcopy_c_add`, `asmcopy_c_reg`, `read_nopN` and `read_sparse` from the reference loops of probe.txt. For `read_sparse` it expects the registers x0 and x1 of `asmread`.

## What I checked on the development machine

System load during these checks: 7.4 (1-minute load average, 32 CPUs). Compiler: gcc 11.4.0, x86-64, with the flags of `build.sh`. All kernels except the old ones were stand-ins.

| Check | Result |
|---|---|
| Compile with the flags of `build.sh` | 0 warnings, 4 binaries. |
| Self-test | 162 checks pass, exit 0. With a copy that leaves the last word: exit 1. With a read that skips one page: exit 1. With a write of one word too many: SIGSEGV after the line `call,oldwrite,4096`. |
| Placement | Function starts modulo 64 equal PAD for all 21 kernels in all 4 binaries (`nm`). `-DPAD_copy=12`, `-DHEAD_asmcopy=8` and `EXTRA` take effect. |
| Row formats | 64 runs under `timeout`: 1 and 4 threads, `--stop pass|common`, `--start common|offset`, `--rounds 1|2`, 4 sequences (with `@SIZE`, copy, `--two-buffers`, `--no-thp`). A validator script checked field counts, decimals, row counts, row order, total bytes, passes, `t_sched_s`. 0 errors. |
| Start protocol | 900 intervals with 16 threads in `common` mode and 600 in `pass` mode ended without deadlock (6.2 s for the first). 6 threads on 2 CPUs also ended. |
| Ranges | A traced build showed the call ranges of each thread. They match B.4 and B.5 for `pass` and `common` with `--start offset`, at 16 MiB and at 6 MiB. |
| smaps lookup | Every P row had numbers (8192 kB of 8192 kB huge at 8 MiB). A build with a lookup that cannot match printed `NA,NA`. |
| Page reading time | 16 buffers: mean 0.54 ms, largest 31 ms, over 901 readings. This says nothing about 240 buffers on CRB. |
| Counters | With `--pmu-type 0` (generic hardware events of Linux): C rows with numbers, and `NA` for an event that does not open. Environment variables work. |
| `build.sh` | Exit 3 with a marker file and no file written. Exit 4 with a broken kernel. Exit 0 otherwise, with `listing.txt` and `offsets.tsv`. |
| `check_listing.py` | A synthetic AArch64 listing made from probe.txt passes (84 rows). Six changed listings each fail with exit 1: wrong offset, A/A offset, A/A address, changed instruction, missing nop, missing kernel. |

Checks after the changes of the review of 2026-11-13. System load: 5.6 to 7.9 (1-minute load average, 32 CPUs). Compiler and flags as above.

| Check | Result |
|---|---|
| `build.sh` (local, `BWX_CPUS=0-31`) | Exit 0, 0 compiler messages, 4 binaries, 4 self-tests with `failures=0` (162 checks each). With `EXTRA_bwx_o0="-DPAD_copy=12"`: `k_copy` starts at 12 modulo 64 in `bwx_o0` and at 32, 32 and 48 in `bwx`, `bwx_o36` and `bwx_o52`. |
| Row formats | 64 runs (1 and 4 threads, `--stop pass|common`, `--start common|offset`, `--rounds 1|2`, 4 sequences). The validator script of the first check found 0 errors in each. All 64 ended with status 0. |
| Order of page reading and warm-up | Deviation 21: 0 of 800 warm-up passes started before the reading of the interval before (before the change: 800 of 800). |
| Start protocol | 900 intervals with 16 threads in `common` mode (8.3 s) and 600 in `pass` mode (2.8 s) ended with status 0 and all rows. 6 threads on 2 CPUs ended. In the `common` run 961 of 14400 thread starts were `late` (loaded machine). |
| Thread sanitizer | `-fsanitize=thread`, 12 option mixes (1, 6 and 5-on-2-CPU threads, both stop methods, both start modes, 6-entry sequence, `--two-buffers`, `--count`): 0 race reports, all exit 0. |
| Page reading time | 16 buffers: mean 0.56 ms, largest 38 ms, over 901 readings. |
| Counters | `BWX_PMU_TYPE=0 BWX_EVENTS=0,1,3,0x99`, 2 threads: 8 C rows with numbers and `NA` for the event that does not open. |
| Bad values | 12 calls with a bad number, size, PMU type or CPU: each exit 2 with a message. 3 calls with good values: exit 0. |
| CPU limit | Deviation 22, build with `-DMAX_USE_CPU=15`: results as listed there. |
| `check_listing.py` | The synthetic good listing passes (84 rows `ok`, exit 0). 29 of the 31 listings of the reviewer's generator now fail with exit 1; the 2 that pass are the good listing and a `read` that starts at 16 modulo 64 (no offset is planned for `read`). The 5 cases that passed before now fail: no save of d8 to d15 in `asmread`, none in `asmcopy_c_reg`, a second loop in `read`, a wrong end computation in `copy`, a listing with `bwx` alone. 3 more changed listings fail: a second backward branch in `read_sparse` and in `asmcopy_c_add`, a missing `ldp d12, d13` in `read_nop4`. |

Two local observations that are not explained:

- In the 900-interval `common` run, 1007 of 14400 thread starts were `late` (largest 72.8 ms). The machine was loaded and the main thread is not pinned. Whether 2 ms of lead is enough for 120 threads on CRB is not known.
- In 1 of 48 C rows, one counter (generic event 3, cache misses) showed a difference near 2^47. The other values of the row were normal. I did not find the cause. The B.8 test at 32 KiB on CRB is the check for the real PMU.

The x86 binaries and listings were removed from this folder after the checks.

## What only a build on CRB can verify

1. **That `bwx.c` compiles for AArch64 at all.** The development machine has no AArch64 gcc and no clang. The asm strings, the `.rept` blocks, the register variables and the NEON code were never assembled.
2. **Warnings of gcc 14.2.0.** gcc 11.4.0 gave none on x86.
3. **Loop bodies.** Whether gcc gives `read`, `write`, `copy`, `oldread`, `oldwrite`, `oldcopy` the loops of probe.txt in this file, with the added flags `-fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`.
4. **HEAD values.** Whether the loops start 4 B or 20 B after the function start. If gcc aligns a loop of a C kernel, HEAD can change with the function start, and the three B3 builds can then need different pads. Then set `PAD_<name>` per build.
5. **Loop offsets** of all kernels (`offsets.tsv`), and the planned ones (36, 52, and 0, 36, 52 in the B3 builds).
6. **A/A copies** have their own address with gcc 14 on AArch64. On x86 they have.
7. **Self-test of the real kernels**, in all 4 binaries.
8. **`build.sh` and `check_listing.py` on a real listing.** They were tested on x86 objdump text and on a synthetic listing only. This includes the new whole-function comparison: whether gcc 14.2.0 gives the unchanged kernels the same code outside the loop in `bwx.c` as in `bandwidth.c` is not known.
9. **Counters without root** (`perf_event_paranoid` 2): the PMU type, the 5 codes, whether 5 events fit in one group, and the test of 11 instructions per 256 B.
10. **smaps lookup on CRB** (kernel, THP "always"), and the reading time with 240 buffers.
11. **`late` flags and end skew** with 120 threads, and whether 2 ms of lead is enough.
12. **Memory**: each buffer maps 4 MiB more than `--bytes` as `PROT_NONE` guard space. It uses address space, not memory (est.).

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/handoff.md`, sections B.1 to B.9.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c` (base) and `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/` (`bandwidth.orig.c`, `selftest.c`, `run_kernels.sh`).
