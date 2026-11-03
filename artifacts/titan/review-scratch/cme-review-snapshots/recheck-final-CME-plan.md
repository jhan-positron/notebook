# Asimov CME load and store test (phase F of cache-mem-perf): context, design, code and data

Written 2026-11-02 by Jibin Han's Claude session for review by codex. Review comments go to
`codex-review-CME-plan.md`; each round's responses are appended here in numbered sections.

**Short version.** Bill Baumann asked for the C1-Nano cache statistics again with the CME, the
DSU's Arm C1-SME2 matrix unit, doing the loads and stores, on one core. Phase F adds that to
`run_asimov.sh`: the same chains, footprints and flush rules as phases A, B and D, run through the
CME in streaming SVE mode, so the matched rows (section 2.1) compare line for line with their
C1-Nano twins. The code builds with Jesse's flags, its kernels pass a self-test under QEMU 11 with
SME2, and nothing has run on the emulator yet. Section 8 holds the round 1 review responses.

## Words used here

- CME: Compute Matrix Engine, Positron's name for the Arm C1-SME2 unit (Arm code name Griffin).
  One per DSU (two-core cluster), shared by the DSU's two cores. It executes SME and SME2
  instructions and, in streaming mode, every SVE load and store.
- Streaming mode: the CPU state entered with `SMSTART SM` in which SVE instructions run on the CME
  at the streaming vector length. `SMSTART` and `SMSTOP` zero the Z and P registers.
- SVL: streaming vector length, 64 B on Asimov (the RTL's `CME_SVL = 512`). The core's own SVE
  vector length is 16 B.
- CME L1: the CME's own 64 KB, 4-way data cache with 64 B lines and a hardware prefetcher
  (Arm C1-SME2 TRM 107831 section 6). A CME load goes CME L1, then the DSU L3 (256 KiB), then the
  mesh (SLC, OCM, DRAM). The core's L1 and L2 are not on that path.
- Chase: a dependent pointer walk; elapsed time per hop is the load-to-use latency.
- Fresh chain, flushed: as in README.md. A fresh chain was never walked before its one timed pass; a
  flushed row has every line cleaned and invalidated (`DC CIVAC`) from all caches before the pass.
- DUP/LASTB control (printed as `cme-roundtrip`): a chain of `DUP` (general register into a Z
  register) then `LASTB` (back) hops in streaming mode, with no memory access. It shares the
  register return path with a CME chase hop. It is a control row, not a measured component of a
  chase hop: `DUP` and `LD1D` use different CME resources, and no calibration here says their
  non-memory costs are equal.
- CME counters: C1-SME2 PMU events read through the core PMU with `perf_event_open`:
  `CME_CYCLES` 0x3246 (clock cycles of the CME, on its own clock), `CME_L1D_CACHE_REFILL_INNER`
  0x327D (CME L1 refills served from a cache inside the cluster, the DSU L3),
  `CME_L1D_CACHE_REFILL_OUTER` 0x327E (refills served from outside the cluster: SLC, OCM, DRAM).
  Names and numbers from TRM 107831 chapter 12; asimov-bench opens CME events the same way.
- Coverage (`perf_cov`): the counter group's running time over its enabled time. 1.0 means the
  counters covered the whole timed walk; anything else means the kernel multiplexed the group and
  the counts are invalid.
- Run 1, run 2: the first emulator run of this test suite (2026-10-31) and the pushed revision
  `8ae533c` that waits for its run. Phase F is a change on top of `8ae533c`.
- asimov-bench: positron-ai/asimov-bench, where Jacob Geldbach's team keeps its own CME bench
  (`presilicon-perf/cme-perf`, branch `feature/cme-perf-pr3`) and its October 2026 results.
- QEMU user mode: `qemu-aarch64` running one static AArch64 program on an x86 host. It checks that
  the instructions do what the code expects. Its timings mean nothing.

## 1. Context

### 1.1 The request

Bill (Slack, 2026-11-02): "get similar statistics from the CME as well as the C1 Nano ... Just loading
registers and writing them back." Jibin confirmed the setup: one test core; Jesse's image runs the
kernel on CPUs 0 and 1 and the test on CPU 2 with CPU 3 offline, so the DSU-1 CME is not shared.

### 1.2 What already exists

- Our suite (run 2, `8ae533c`): `latency` (pointer chase, fresh and flushed chains, core PMU refill
  counts) and `bandwidth` (read, write, copy streams) over DRAM footprints from 4 KiB to 32 MiB and
  the five OCM regions, from CPU 2. Run 1 measured on the core: L1 2.00 ns, L2 6.07 ns, SLC 23 to
  24 ns, DRAM 52.3 ns, OCM 18.8 to 23.2 ns; one-core read 9 to 10 GB/s beyond L2, write 32 GB/s.
- Jacob's team (asimov-bench, GA13 runs 3969, 4045, 4065 in October, RTL `a10181848`): a chase
  through the CME at 21.56 ns from the CME L1 (16 KiB ring), 26.60 ns from the DSU L3 (128 KiB),
  34.8 ns from OCM; one CME reading DRAM at 34.5 GB/s with hardware prefetch alone, 22.1 GB/s from
  its OCM window; per-instruction costs (fmopa 2 cycles, ld1h x4 2.03, st1h x2 3.0).
  Sources: `/scratch/jgeldbach/cme-perf-for-jibin/02-results-so-far.md` and the bench's
  `chase.S` and `stream.S`, whose instruction forms this code reuses.
- Not covered by either: a footprint sweep of the CME chase from 4 KiB to 32 MiB, CME stores and
  copies to cacheable memory, the single-vector forms, the OCM rows through the CME, and a
  side-by-side with the core at the same footprints. That is phase F.

### 1.3 Constraints that shape the code

- Jesse builds with GCC 14.2 `-O2 -mcpu=cortex-a520 -static` and runs `run_asimov.sh` as root.
  The SME instructions sit in a separate assembly file with its own `.arch` directive, so the C
  files and the compiler flags do not change.
- Streaming mode rules: no system call inside a streaming span (a system call clears streaming
  mode and its Z and P state); a signal is survived (the handler runs outside streaming mode and
  the return restores the state) but its handler time lands in the elapsed time, so a span is
  intended uninterrupted, not guaranteed; no Advanced SIMD (the CME has no FA64); the first
  `SMSTART` of a thread traps to the kernel once; `d8` to `d15` and `FPCR` must be saved around
  the span.
- The CME power unit must be in dynamic mode before the first streaming instruction, or the core
  stalls forever. The SCP firmware of run 1 (`scp-v0.34.0`) arms it on every core-on
  (`asimov_system_enable_cme_dynamic`, present since commit `32658a4c`), and Jacob's runs on the
  same kind of image used the CME, so this holds on Jesse's image.
- No emulator run for this work until Jibin says so (his rule of 2026-11-02). Verification uses the
  x86 host build, the CRB (an Arm server with GCC 14.2 but no SME) and QEMU user mode.

## 2. Design

### 2.1 Questions and the rows that answer them

| # | Question | Row (all from CPU 2, CPU 3 offline) | C1-Nano twin |
|---|---|---|---|
| 1 | What does a register chain through the CME cost with no memory access? | `cme-roundtrip`: DUP + LASTB hops, 64 K hops, 3 reps, at the start of every `--cme` latency file | none; a control read beside the chase rows (see section 2.2 item 4) |
| 2 | Load-to-use latency through the CME by footprint: CME L1 (64 KB), DSU L3 (256 KiB), SLC, DRAM | `latency --cme --perf` repeated chase at 4 KiB to 384 KiB; fresh chains at 512 KiB to 32 MiB; fresh + flush at 8 MiB under the mesh counters | phase A, same sizes and options (phase A's flushed row is not under the mesh counters) |
| 3 | OCM latency through the CME, per region and all five | `latency --cme --perf --mem ocm --sparse --fresh 8 --flush`, 256 KiB per region (64 hops per pass) and 1.25 MiB (320), under the mesh counters; the dense `--fresh 3 --flush` all-five row as the control (section 11; this row supersedes the dense per-region rows of the first draft) | phase B, CPU 2 rows of the same run, now sparse too |
| 4 | Throughput of one core's read, write and copy loops through the CME, 256 B per instruction | `bandwidth --cme --kernel all` at 16 KiB, 48 KiB, 96 KiB, 160 KiB, 256 KiB, 1 MiB, 2 MiB, 32 MiB per buffer | phase D at 16 KiB, 48 KiB, 96 KiB, 256 KiB, 2 MiB, 32 MiB; 160 KiB and 1 MiB have no twin |
| 5 | Do the single-vector (64 B) forms stream as fast as the four-vector forms? | `bandwidth --cme --kernel ldr16` and `str16` at 16 KiB, 2 MiB, 32 MiB | none (phase D's `ldr16`/`str16` exist only for SPM); the comparison is with row 4, as whole-kernel throughput |
| 6 | What does one kernel call cost (SMSTART, register save, SMSTOP)? | `bandwidth --cme --bytes 1K --passes 4096`, read and write | none; a control for rows 4 and 5 at small footprints |
| 7 | OCM read and write through the CME | `bandwidth --cme --mem ocm` read per region, read all five, write all five, flushed before, under the mesh counters | phase D OCM rows |

The matched subset is rows 2, 3, 4 (six of the eight footprints) and 7. Rows 1, 5, 6 and the
160 KiB and 1 MiB bandwidth rows are CME-only.

Where a CME chase's lines came from is read from the two refill-source counters per load. They
count CME L1 refills by source, demand and prefetch alike (the TRM does not limit them to demand
loads), and are reported as refill-source counts. Whether the chase rows' refills are demand
refills is a hypothesis: a repeated random chain can be learned by a prefetcher (run 1 measured
that on the core), and a fresh chain removes the learned walk but not the possibility. Both
near 0 means the CME L1 served the loads;
`cme_l1d_refill_inner` near 1 means a cache inside the cluster did (on this DSU that is the L3,
or the partner core's L2, which is idle with CPU 3 offline); `cme_l1d_refill_outer` near 1
means the lines came from outside the cluster. Outside the cluster, OCM against SLC against
DRAM is not separated by any per-walk counter here: `cmncount` counts the mesh over the whole
command (buffer fill, chain building, warm-up walks, timed walks and teardown), so its counts
corroborate the traffic of the command and cannot be matched to one timed walk. The OCM rows'
home-node counts show that the command's traffic went to the expected node; for SLC against
DRAM at a given footprint the attribution is Insufficient data, with the footprint against the
3.75 MiB of unlocked SLC and the latency step as the stated hypothesis.

### 2.2 Method decisions

1. **Same harness, new engine.** `--cme` is an option of the existing `latency` and `bandwidth`
   programs, not a new program. The chain builder, the fresh and flush logic, the buffers (huge
   pages, OCM regions) and the reps are unchanged. What differs between a CME row and its twin:
   the unit that executes the loads and stores; the kernel loop (a chase hop is `LD1D` + `LASTB`
   against a scalar `LDR`; a stream pass is `LD1B`/`ST1B` of four vectors with a fold against
   `LDP`/`STP` of 16 B pairs); one `SMSTART`/`SMSTOP` per kernel call; and the counter set
   (CME refill-source events against core refills). The CSV layout differs by one column:
   every counted row, CME or core, now carries `perf_cov`.
2. **Instruction forms are the asimov-bench forms.** Chase: `LD1D {z0.d}, p0/z, [x0]` with a
   one-element predicate, then `LASTB x0, p0, z0.d` (their `chase.S`). Stream: `LD1B` of four
   vectors with `[x0, #k, mul vl]` offsets, four per KiB (their `stream.S`). Stores use the matching
   `ST1B` of four vectors. So their 21.56 ns and 26.60 ns per chase hop and their 34.5 GB/s read
   stream are the nearest prior numbers for our rows, measured on a different image (RTL
   `a10181848`, SCP `scp-v0.40.0`) and, for the stream, with a four-accumulator fold against our
   sixteen; they are reference points, not expected equalities.
3. **One streaming span per call.** Each kernel does `SMSTART SM`, its whole loop, `SMSTOP SM`.
   The timer and the counter reads are outside the span (they are system calls). The first
   `SMSTART` of the thread traps once; every timed path has an untimed warm-up call before it
   (`latency` already walks each chain twice before timing; `run_roundtrip` does one untimed call;
   `bandwidth` runs one warm-up pass per rep).
4. **The DUP/LASTB control is its own row, and stays a control.** Jacob's 21.56 ns per chase hop
   from the CME L1 is about 43 cycles, ten times the core's L1 latency; which parts of a hop
   make up that time is not separated by any row here. The control row has the same register
   return path and no load. Both raw timings are reported; "chase minus DUP/LASTB control" is reported as a derived number with
   that name, not as the memory latency. The hypothesis that the CME rows sit a roughly constant
   offset above the core rows at the mesh levels is tested by the paired rows, not assumed.
5. **Read kernels fold everything they load, one accumulator per load register.** Every loaded
   vector is XORed into its own accumulator (z16 to z31 for the four-vector reader, z16 to z23 for
   the single-vector one), so an accumulator is updated once per loop pass and the EOR latency
   (4 cycles in the LLVM C1-Nano model) never chains within a pass. In `bandwidth` the fold goes
   to a volatile sink; in `cme_test` it is compared with a scalar XOR of the buffer, which is how
   the first bug was caught. A read row is the throughput of this whole loop (loads, fold, loop
   control, one SMSTART/SMSTOP per pass); it is not presented as the CME's load bandwidth
   ceiling. Jacob's `stream.S` folds the same way with four accumulators, so his 34.5 GB/s is the
   nearest prior number for row 4.
6. **Stores write a constant.** `cme_write4` and `cme_write1` store a value every 8 B, like the
   core's `k_write`. No read of the destination, so a write row is a pure store stream.
7. **Footprints.** The CME sweep keeps every phase A and D size so the twins line up, and adds
   160 KiB and 1 MiB to the bandwidth rows. The sizes are per buffer; read and write touch one
   buffer, copy touches two (source and destination), so a copy row's working set is twice its
   size. The intended regimes, by capacity only (bandwidth rows have no refill counters, and a
   chase row at the same footprint says nothing about a sequential stream's service source, so
   the level that served a bandwidth row stays a hypothesis): read and write at 16 KiB and
   48 KiB inside the 64 KB CME L1, at 96 KiB to 256 KiB
   inside the 256 KiB DSU L3, 1 MiB and 2 MiB inside the 3.75 MiB of SLC left after the OCM lock,
   32 MiB in DRAM; copy at 16 KiB (32 KiB touched) inside the CME L1, 48 KiB to 96 KiB (96 to
   192 KiB) inside the DSU L3, 160 KiB to 1 MiB (320 KiB to 2 MiB) inside the unlocked SLC,
   2 MiB (4 MiB touched) beyond the nominal 3.75 MiB of unlocked SLC with its service
   unresolved, 32 MiB in DRAM. The chase rows touch one buffer.
8. **Flush rules carry over.** `DC CIVAC` from the core cleans and invalidates a line everywhere in
   the coherent system, the CME L1 included (Jacob's chase cleans the same way). The flushed
   8 MiB CME row is the intended DRAM reference: on the core, run 1 showed that the flush removes
   DRAM-backed lines from the SLC too; through the CME the row's outside-cluster source (SLC or
   DRAM) is not proven by any counter here, only `cme_l1d_refill_outer` near 1 per load is.
9. **CPU 3 stays offline.** The two cores of a DSU share one CME. Phase F is its own script,
   `run_cme.sh` (section 13), which takes CPU 3 offline before its rows and brings it back after
   them; `run_all.sh` runs it after the cache suite.
10. **Gate and self-description.** The script runs phase F only when `/proc/cpuinfo` lists
    `sme2`; each `--cme` program checks the SME and SME2 hwcaps and that `RDSVL` returns 64 and
    exits 2 with a `# cme:` line otherwise. A missing row then says why.
11. **CME counter set and validity.** `--perf` with `--cme` opens cycles plus `CME_CYCLES`,
    `CME_L1D_CACHE_REFILL_INNER` and `CME_L1D_CACHE_REFILL_OUTER` in one group. The column names
    come from the open set, so the CSV header says which set it holds. Every counted row carries
    `perf_cov`; a row whose group failed to open, whose reset/enable/disable ioctl failed, whose
    read came back short, or whose running time is below its enabled time prints `-` in every
    counter column and a `# perf: ... invalid: <reason>` line. Such a row keeps its timing and
    gets no cache attribution (Insufficient data).
12. **Per-call cost control.** Each bandwidth pass is one kernel call with its own SMSTART,
    register save and SMSTOP; a 16 KiB row with 256 passes pays 256 of them per rep. The 1 KiB,
    4096-pass rows give an upper bound on that cost: elapsed / 4096 is one call with 1 KiB of
    data, fold and loop work included, so it is not the entry and exit cost itself. Reported
    bandwidth is complete-call throughput. If the bound is small against a 16 KiB call, that
    limited conclusion is stated; otherwise the per-call overhead stays unresolved, and no
    small-footprint difference is assigned to the instruction width or the store path.

### 2.3 Not done, on purpose

- No matrix arithmetic (FMOPA and friends). Bill asked for loads and stores; the compute rates are
  already measured by asimov-bench (one FMOPA per 2.04 cycles, half-matmul).
- No `RPRFM` rows. The hardware prefetcher is on by default and asimov-bench found 0 to 7 % from
  `RPRFM`; the twin rows on the core have no software prefetch either.
- No two-core or five-CME rows. Jibin set one core; Jacob measured the five-CME stream.
- No SPM rows. The SPM driver is still absent on Jesse's image.
- No change to phases A to E. Their rows and options are the run 2 rows.

## 3. Code

All files in `~/workspace/titan/cache-perf/asimov/` (the copy that goes to
`~/workspace/ai-runs/asimov-repo/cache-mem-perf/` at commit time). Line counts and changed-line
counts are against `8ae533c`.

### 3.1 `cme_kern.S` (new, 251 lines)

Eight AAPCS64 functions under `.arch armv9.3-a+sve2+sme2`. Two macros, `SM_ENTER` and `SM_LEAVE`,
push `d8` to `d15` and `FPCR`, enter streaming mode, and the reverse.

| Function | Loop body | Bytes per instruction |
|---|---|---|
| `cme_svl()` | `RDSVL x0, #1` (legal outside streaming mode) | |
| `cme_chase(p, hops)` | `LD1D {z0.d}, p0/z, [x0]`; `LASTB x0, p0, z0.d`; `SUBS`; `B.NE` (p0 = `PTRUE p0.d, VL1`) | 8 B read per hop |
| `cme_roundtrip(x, n)` | `MOV z0.d, x0` (DUP); `LASTB x0, p0, z0.d`; `SUBS`; `B.NE` | none |
| `cme_read4(p, bytes)` | four `LD1B {z0-z3 ... z12-z15}, pn8/z, [x0, #0/4/8/12, mul vl]`, 16 `EOR`, one per load register into z16 to z31, `ADD x0, #1024`; after the loop the 16 accumulators are combined, then `EORV` and `FMOV` return the fold | 256 |
| `cme_write4(p, bytes, v)` | four `ST1B {z0-z3}, pn8, [x0, #k, mul vl]` of a DUP'd v | 256 |
| `cme_copy4(d, s, bytes)` | four `LD1B` from s, four `ST1B` to d, per KiB | 256 + 256 |
| `cme_read1(p, bytes)` | eight `LD1B {zk.b}, p0/z, [x0, #k, mul vl]`, eight `EOR` into z16 to z23, `ADD x0, #512` | 64 |
| `cme_write1(p, bytes, v)` | eight `ST1B {z0.b}, p0, [x0, #k, mul vl]` | 64 |

`bytes` must be a multiple of 1024 (`bandwidth` enforces it). The multi-vector forms need SME2;
the chase, the round trip and the single-vector forms need only SME.

### 3.2 `common.h` (118 changed lines)

- Declarations of the eight kernels for AArch64, and inline stand-ins returning 0 for a non-Arm
  host build, so `make` on x86 still works.
- `require_cme()`: `getauxval(AT_HWCAP2)` must have `HWCAP2_SME` (bit 23) and `HWCAP2_SME2`
  (bit 37), and `cme_svl()` must return 64; otherwise print `# cme: ...` and exit 2.
- `perf_open_set(g, raw, names)` generalizes the one fixed group; `perf_open()` keeps the core set
  (0x03, 0x17, 0xA2) and `perf_open_cme()` opens 0x3246, 0x327D, 0x327E. `struct perfgrp` carries
  the column names of the open set, the errno of a failed counter ioctl and the enabled and
  running times of the last read.
- The group is opened with `PERF_FORMAT_TOTAL_TIME_ENABLED | TOTAL_TIME_RUNNING`. `perf_start`
  and `perf_stop` record a failed reset, enable or disable. The kernel returns the enabled and
  running times as lifetime totals (`PERF_EVENT_IOC_RESET` clears counts, not times), so
  `perf_read` takes the row's coverage as the change since the previous read and moves that
  baseline on every complete read, valid or not. It returns 1 only when the group is open, no
  ioctl failed, the read returned the whole record with the expected event count, and the row's
  running time equals its enabled time; otherwise 0 with the reason. These checks apply to the
  core set of phases A and B as well.

### 3.3 `latency.c` (99 changed lines)

- `--cme`: `chase()` calls `cme_chase()` instead of the C pointer loop; mode labels get a `cme-`
  prefix (`cme-repeat`, `cme-fresh1`, `cme-flushed`, `cme-best`); `--perf` opens the CME set; the
  header line prints `cme=1` and the counter column names of the open set plus `perf_cov`.
- `print_counters()`: per-load values and the coverage for a valid read, or `-` in every column
  and a `# perf: counters of the row above are invalid: <reason>` line.
- `run_roundtrip()`: before the sizes, `--reps` timed calls of `cme_roundtrip(x, --loads)` after one
  untimed call, printed as rows with size 0 and mode `cme-roundtrip`, plus `cme-roundtrip-best`.
  It runs in every `--cme` invocation (nine commands in phase F).
- Everything else (chain building, fresh and flush logic, OCM buffers) is untouched.

### 3.4 `bandwidth.c` (37 changed lines)

- `--cme`: `pass()` routes read, write, copy to `cme_read4`, `cme_write4`, `cme_copy4` and
  `ldr16`, `str16` to `cme_read1`, `cme_write1`; the read folds go to a volatile sink; kernel
  names in the rows get a `cme-` prefix; bytes must be a multiple of 1024; each worker thread
  calls `require_cme()` after pinning.

### 3.5 `cme_test.c` (new, 105 lines)

Checks every kernel against a scalar reference on a 64 KiB buffer: round trip returns its input
after 1 and 1,000 hops; the chase reaches the same address as a C walk after 100 hops, with the
pointer in word 0 and in word 2 of the line (as `--fresh` chains store it); both read kernels'
folds equal the scalar XOR over 64 KiB and over 1 KiB; both write kernels set every word and leave
the guard past the end untouched; copy makes the destination equal and leaves its guard; a second
read pass folds the same. `--sme1` skips the SME2-only kernels for a machine with SME but not
SME2. Exit 0 on pass, 1 on failure, 2 without SME2.

### 3.5a `perf_cov_test.c` (new, 58 lines)

Host test of the per-row coverage: opens the core group, crowds the task with twelve more
groups so the kernel multiplexes, times a walk (must come back invalid, "multiplexed"), closes
the extra groups and times another walk (must come back valid). It fails if coverage were
cumulative over the group's lifetime. Needs an Arm machine with a PMU; run with
`make perf_cov_test && taskset -c 2 ./perf_cov_test`.

### 3.6 `Makefile`, `run_asimov.sh`, `README.md`, `est_chip_time.py`

- `Makefile` links `cme_kern.S` into `latency`, `bandwidth` and `cme_test` when
  `$(CC) -dumpmachine` contains `aarch64`, so the x86 host build and Jesse's cross or native build
  both work without options.
- `run_cme.sh` (phase F; section 13 moved it out of `run_asimov.sh`): gated on `sme2` in
  `/proc/cpuinfo`, with the rows of section 2.1 (the flushed 8 MiB CME row and the OCM rows
  under `cmncount`, the two per-call cost rows); `--dry-run` prints every measurement command
  and runs nothing (it assumes OCM and SME2 present). `run_asimov.sh` keeps phases 0, A, B, D, E,
  C; `lib_run.sh` holds what they share; `run_all.sh` runs both.
- `est_chip_time.py` (new, 164 lines): reads the dry-run output and counts, per command, exactly
  what the programs do (hops, control hops, chain builds, fills, flush lines, bytes, kernel calls,
  launches), then applies labelled per-hop, per-byte and per-launch assumptions. Section 4.4 is its
  output.
- `README.md` (70 changed lines): phase F rows in "What each phase measures", the words CME,
  streaming mode, SVL, CME counters and the control, the new files, the gate and the streaming
  rules (system calls clear the state; a signal is survived but contaminates the time), the
  `perf_cov` column and invalid rows in "Output format", `--dry-run`, and the chip-time
  paragraph.

## 4. Data collection and output

### 4.1 Files phase F writes (in `results/<UTC time>/`)

| File | Program and options | Rows |
|---|---|---|
| `cme-latency-dram-small.csv` | `latency --cme --cpu 2 --perf --loads 64K --reps 3 --sizes 4K..384K` | 3 `cme-roundtrip` rows + best, then per size 3 `cme-repeat` rows + `cme-best` |
| `cme-latency-dram-large.csv` | `--fresh 3 --sizes 512K..32M` | per size `cme-fresh1`, `cme-fresh2`, `cme-best` |
| `cme-latency-dram-flushed.csv` | `--fresh 3 --flush --sizes 8M` under `cmncount` | the same, flushed; mesh counts under label `cme-dram-flushed-8M-cpu2` |
| `cme-latency-ocm-region<r>.csv`, `cme-latency-ocm-all5.csv` | `--mem ocm --sparse --fresh 8 --flush` under `cmncount` | per file 7 `cme-fresh<k>` rows + `cme-best` (64 or 320 hops each), plus the mesh counts in `cmn-counts.csv` with labels `cme-ocm-region<r>-cpu2`, `cme-ocm-all5-cpu2` |
| `cme-latency-ocm-all5-dense.csv` | `--mem ocm --fresh 3 --flush`, 1.25 MiB, under `cmncount` (label `cme-ocm-all5-dense-cpu2`) | the dense control: 2 `cme-fresh<k>` rows + `cme-best` of 20,480 hops |
| every `--cme` latency file | | starts with the `cme-roundtrip` rows (3 + best) and the `cme-call` rows (3 + best, 64 one-hop calls per rep) |
| `cme-bandwidth-dram-1core.csv` | `bandwidth --cme --kernel all` at 8 footprints; `ldr16`, `str16` at 3 | per kernel and size 3 reps + best, kernel names `cme-read`, `cme-write`, `cme-copy`, `cme-ldr16`, `cme-str16` |
| `cme-bandwidth-call-cost.csv` | `bandwidth --cme --bytes 1K --passes 4096`, `read` and `write` | 3 reps + best each; elapsed / 4096 is the per-call cost with 1 KiB of data |
| `cme-bandwidth-ocm-region<r>.csv`, `cme-bandwidth-ocm-all5.csv`, `cme-bandwidth-ocm-write.csv` | `bandwidth --cme --mem ocm --flush-before` under `cmncount` | as phase D's OCM rows, labels `cme-ocm-read-region<r>`, `cme-ocm-read-all5`, `cme-ocm-write-all5` |

Every row is also in `all.txt` after its command line, and every command line with its uptime stamp
in `log.txt`, as in run 2.

### 4.2 Row formats

`latency` rows: `mem,size_bytes,mode,rep,loads,ns_per_load[,cycles_per_load,cme_cycles_per_load,cme_l1d_refill_inner_per_load,cme_l1d_refill_outer_per_load,perf_cov]`.
The counter columns are present when the group opened; the header names them; a row whose
counters are invalid has `-` in each and a `# perf:` comment line after it. A `cme-roundtrip`
row has `size_bytes` 0.

`bandwidth` rows are unchanged: `mem,kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps`
with the `cme-` kernel names. The header comment carries `cme=1`.

### 4.3 How the data will be read

1. **Side-by-side latency table** per footprint: core best (phase A) against CME best (phase F),
   both raw, with the `cme-roundtrip` control beside them and "chase minus DUP/LASTB control" as a
   derived column named that way. Hypothesis from Jacob's numbers, to be tested by the pairs: about
   21 ns flat up to 48 KiB, a step near 64 KiB (CME L1 edge), about 27 ns to 256 KiB (DSU L3), then
   SLC and DRAM steps a roughly constant offset above the core's. His runs were on RTL
   `a10181848` with SCP `scp-v0.40.0`; Jesse's image is RTL `0d9e214` with SCP `scp-v0.34.0`, so
   his numbers are reference points, not expected equalities.
2. **Level attribution** from the inner and outer refill-source counters per load (valid rows
   only), against the core's three refill counters per load in the twin row: CME L1, inside the
   cluster, outside the cluster. Beyond the cluster, OCM is known by its address and its home-node
   counts; SLC against DRAM is Insufficient data (section 2.1), stated as a hypothesis from the
   footprint and the latency step.
3. **OCM**: per-region CME latency against the same run's phase B rows from CPU 2 (run 1's 18.8 to
   23.2 ns are history: a different chain policy with measured prefetch contamination), with the
   home-node request counts checking that the traffic went to the expected node.
4. **Bandwidth table**: CME read, write, copy against the core's at the six shared footprints; the
   256 B and 64 B forms against each other; the per-call cost bound beside the 16 KiB rows. All as
   complete-kernel throughput, with the level that served each row an intended regime, not a
   measured fact. Prior number: Jacob's 34.5 GB/s for one CME reading DRAM with the
   same load form and a four-accumulator fold. No prior CME write number; the core does 32 GB/s.
5. **Acceptance rules** before any number is used:
   - every `--cme` program printed `cme=1` and no `# cme:` refusal; otherwise the row is absent and
     the reason is in `all.txt`;
   - a counted row is used for attribution only with `perf_cov` 1.0000 and no `# perf:` line;
     otherwise its timing is used and its attribution is Insufficient data;
   - event sanity: the 4 KiB to 48 KiB `cme-repeat` rows show both refills near 0 per load, the
     `cme-roundtrip` rows show 0 refills, the flushed 8 MiB row shows `cme_l1d_refill_outer` near 1
     per load; a CME event set that fails these is not used for attribution anywhere. The
     whole-command mesh counts of the flushed row (`hns_cache_miss_all`, `hns_mc_reqs_local_all`)
     are corroborating traffic evidence and no acceptance rule rests on them;
   - `cme_cycles_per_load` against `cycles_per_load`: the CME and the core are both at 2 GHz on
     this image (Jesse), so a ratio near 1 says the CME was allocated to CPU 2 for the walk; the
     two count different clocks over the same window and are compared only as that ratio;
   - the OCM rows' mesh counts land on the expected home node.

### 4.4 Chip time (est.)

Counts are exact, from `sh run_cme.sh --dry-run | python3 est_chip_time.py` (phase F) and
`sh run_all.sh --dry-run | python3 est_chip_time.py` (the whole suite; section 13); seconds
are estimates from the assumptions in that script, each labelled there with its source (run 1
rows, asimov-bench rows, or est.).

| Phase F item | Exact count | Assumption | Time (est.) |
|---|---:|---|---:|
| Commands; `cmncount` helper launches; launches | 33; 15; 48 | 14 ms per launch (run 1, est.) | 0.672 s |
| Chase hops (warm-up and timed) | 7,925,888 | 22 ns CME L1, 27 ns DSU L3 (asimov-bench), 45 ns SLC and 75 ns DRAM (est.), 35 ns OCM | 0.45 s |
| DUP/LASTB control hops (1 warm-up + 3 reps, 10 commands) plus the 64 one-hop `cme-call` calls x 3 reps each | 2,623,360 (of which 1,920 one-hop calls) | 5 ns per hop (est.) plus 50 ns per call (est.); the empty brackets and timer reads are not counted | 0.013 s |
| Chain lines built; buffer fill stores (8 B) | 4,153,920; 30,229,248 | 10 ns per line, 0.3 ns per store (est.) | 0.05 s |
| `DC CIVAC` lines | 774,144 | 7 ns per line (run 1, est.) | 0.005 s |
| Bandwidth bytes, timed; warm-up; kernel calls (one per pass per OCM segment) | 1,914,175,488; 673,290,240; 31,173 | 34.5 GB/s read (asimov-bench), 30 write and 25 copy (est.); 50 ns per call (est.) | 0.09 s |
| **Phase F total** | | | **1.29 s** (0.61 s work + 0.67 s launches) |

These counts are the section 11 row set (sparse OCM rows plus the dense control); the first
draft's 32 commands and 46 launches are superseded. The whole run with phases B and F sparse:
100 commands, 66 helper launches, 166 launches; 1.79 s of work and 2.32 s of launches (est.),
about 4.1 s of chip time, about 3.2 h of wall time at 2,779 s per chip second. The launch cost is the largest single assumption and nothing in the run measures it:
`helper_elapsed_ns` spans the helper from its `main` entry to its exit: the child's whole
lifetime from before `fork` through `execvp` to exit (so the child's loading is inside it) and
the counter setup, read and teardown, but not the loading of the helper itself before its
`main`; neither lifetime isolates a launch cost, and the uncounted commands and the shell have
no timing at all. The 14 ms per launch is run 1's whole-run time minus its measured work, spread
over its commands, and stays an allowance.

## 5. Verification done

| Check | Where | Result |
|---|---|---|
| Host build with the stand-ins, `run_asimov.sh --quick` | x86 agent host | builds; phase F reported skipped (no `sme2` in cpuinfo) |
| Build with Jesse's flags; `objdump` shows the eight `cme_*` symbols and 18 `smstart`/`smstop` | CRB, GCC 14.2, binutils 2.42 | builds, no warnings |
| `latency --cme`, `bandwidth --cme`, `cme_test` on a machine without SME | CRB (Neoverse V3AE) | each prints `# cme: SME2 not supported` and exits 2 |
| `run_asimov.sh --quick` | CRB | phases A, D, E run; F skipped with the reason line |
| `cme_test --sme1` (chase, round trip, 64 B read and write) | QEMU 8.2 on the CRB, `-cpu max,sme-default-vector-length=64` | first run: 3 failures (the read fold covered one vector in eight); after the fix: PASS; PASS again after the round 1 accumulator change |
| `cme_test` (all eight kernels) | QEMU 11.1.3 user mode on the x86 host (Debian `qemu-user` 11.1.3 extracted, SME2 present, SVL 64) | PASS, 0 failures, before and after the round 1 accumulator change |
| `latency --cme` with `--perf`, `--fresh 3`, `--flush`; `bandwidth --cme` with every kernel name and the 1 KiB call-cost row; `latency` without `--cme` | QEMU 11.1.3 | CSV rows in the expected format; perf reported unavailable (QEMU has no PMU); timings meaningless |
| `latency --perf` with the core set, valid-counter path | CRB, native | rows carry `perf_cov` 1.0000 and sane refill counts |
| `perf_cov_test`: a multiplexed row followed by a quiet row | CRB, native, pinned to CPU 2 | PASS: crowded row rejected (`multiplexed`, 3.70 ms running of 14.30 ms enabled), the next row accepted with running equal to enabled |
| `sh run_asimov.sh --dry-run` and `est_chip_time.py` | x86 host | 95 commands listed, 32 with `--cme`; section 4.4 |

Not verified: anything about timing, the CME counter events (whether the kernel accepts 0x3246,
0x327D, 0x327E in one group with cycles; asimov-bench opens twelve CME events in one group on the
same kernel), the OCM path through the CME, and the chip-time estimate. All need the emulator.

## 6. Open items and risks for the reviewer

1. **The chase through the CME at tiny sizes.** With `--loads 64K` and a 4 KiB ring, the CME L1
   serves every hop; the row measures a complete hop with an L1 hit. The `cme-roundtrip` control
   sits beside it; the two are not subtracted into a memory latency (section 2.2 item 4).
2. **CME counter group.** If the kernel refuses one of the three raw events, `perf_open_set` prints
   the event and leaves the group closed, and the rows come without counter columns; a group that
   opens but is multiplexed or fails an ioctl prints `-` rows with the reason. Nothing fails. The
   sysinfo step does not list the core PMU's events because the image has no `perf` tool; the
   C1-SME2 TRM's event list is the reference. Whether the kernel schedules 0x3246, 0x327D and
   0x327E with cycles in one group is unverified; asimov-bench opens twelve CME events in one
   group on the same kernel.
3. **`DC CIVAC` and the CME L1.** The flush rows assume a core `DC CIVAC` invalidates the CME L1
   copy. The CME is a coherent requester on the DSU (it has its own L1 with coherency requests,
   TRM 107831 section 6), and Jacob's chase cleaned with `DC CIVAC` and then read OCM at 34.8 ns,
   above his L3 figure, which is consistent. Not proven on our rows.
4. **Page sizes.** The DRAM rows use 2 MiB pages, the OCM rows 4 KiB pages, as in run 2, so an
   OCM-against-SLC comparison carries a translation asymmetry, for the CME rows as for the core
   rows. On the CME path a demand load's address arrives already translated by the host core
   (TRM 107831 chapter 5), so that asymmetry is the core's; the CME's own TLB serves its
   prefetcher, which asks the host core for translations it needs. Whether the prefetcher acts
   on a chase is not measured here.
5. **The `cme-` prefix on labels instead of a new column.** Chosen so the run 2 CSV layout and the
   report scripts stay as they are. A reader must match `cme-repeat` to `repeat`.
6. **Phase F position.** It is `run_cme.sh`, run by `run_all.sh` after the cache suite, with its
   own CPU 3 offline window. It adds 48 launches and about 1.3 s of chip time (est.). Jibin
   decided (section 13): one `run_all.sh` for Jesse, both suites in one results directory.
7. **Store rate anomaly.** asimov-bench saw back-to-back `st1h` at 3 cycles each where the RTL
   says 1. Our `cme-write` rows at 16 KiB will show whether 256 B stores stream at the CME L1 or
   stall; no row isolates the cause.

## 7. Files to read, in order

1. `cme_kern.S` (the kernels), `cme_test.c` (what is proven about them).
2. `common.h` (search `cme`), `latency.c` (search `cme`), `bandwidth.c` (search `cme`).
3. `run_cme.sh` (phase F), `run_all.sh`, `lib_run.sh`, `run_asimov.sh` phase B rows; `README.md`
   phase F rows and words.
4. `cme-survey.html` sections 2, 4 and 9 for the CME facts and the prior measurements, and
   `/scratch/jgeldbach/cme-perf-for-jibin/02-results-so-far.md` for Jacob's numbers.

## 8. Codex review round 1 (codex-review-CME-plan.md) and what changed

Each comment, what I did, and where. Code and plan edits are in place; the sections above read
as revised.

| # | Comment | Response | Changed |
|---|---|---|---|
| R1 | The fold's dependency chains cap the readers (16 cycles per KiB with 4 accumulators, 32 with 2); the no-cost claim is unsupported; a width difference cannot be assigned to the load width | Agreed. Each load register now has its own accumulator (16 in `cme_read4`, 8 in `cme_read1`), so one accumulator is updated once per loop pass and no EOR chains inside a pass; the per-pass recurrence is then 4 cycles against 8 cycles of loads per KiB in the four-vector loop and 8 cycles of loads per 512 B in the single-vector loop. The "does not slow" claim is gone; a read row is the throughput of the whole kernel, and the width comparison is stated as whole-kernel against whole-kernel with the fold difference named. `cme_test` passes after the change (QEMU 11, and `--sme1` on QEMU 8.2) | `cme_kern.S` header, `cme_read4`, `cme_read1`; plan 2.2 item 5, 2.1 row 5, 3.1, 4.3 item 4; README phase F rows |
| R2 | The DUP/LASTB chain is not a measured component of the chase; no calibration supports "floor" or "memory part" | Agreed. The row is now called the DUP/LASTB control everywhere; both raw timings are reported; the derived number is named "chase minus DUP/LASTB control"; the constant-offset expectation is a hypothesis tested by the paired rows | plan Words, 2.1 row 1, 2.2 item 4, 4.3 item 1, 6 item 1; `latency.c` comments; README words and phase F row |
| R3 | `REFILL_RD` and `BUS_REQ_RD` cannot tell the cluster cache from the mesh; use `REFILL_INNER` 0x327D and `REFILL_OUTER` 0x327E; say what evidence accepts a flushed row as outside the cluster | Agreed. The CME set is now cycles, `CME_CYCLES`, `REFILL_INNER`, `REFILL_OUTER`. The flushed 8 MiB CME row now runs under `cmncount`, so its evidence is `refill_outer` near 1 per load plus `hns_cache_miss_all` rising by about one per load; OCM rows keep their home-node counts; the OCM-keeps-data against DRAM-invalidated distinction is kept. Beyond the cluster, levels without a counted row at that footprint are labelled hypotheses | `common.h` `perf_open_cme`; `run_asimov.sh` flushed row; plan Words, 2.1 attribution paragraph, 4.3 items 2 and 5; README words and phase F rows |
| R4 | Define acceptance rules; the reader substitutes zeros, ioctl errors are unchecked, no enabled/running times | Agreed and implemented. The group requests `TOTAL_TIME_ENABLED` and `TOTAL_TIME_RUNNING`; `perf_start`/`perf_stop` record ioctl failures; `perf_read` returns valid only when the group is open, no ioctl failed, the record is complete with the expected event count and running equals enabled. A row with invalid counters prints `-` columns and a `# perf: ... invalid: <reason>` line; every counted row carries `perf_cov`. This applies to the core set of phases A and B too (a format change for run 2's latency files: one added column). Acceptance rules, event sanity controls and the `CME_CYCLES` wording are in 4.3 item 5. Verified natively on the CRB for the core set (`perf_cov` 1.0000) | `common.h` perf functions, `latency.c` `print_counters`; plan 2.2 item 11, 4.2, 4.3 item 5, 6 item 2; README output format |
| R5 | The budget's own parts sum to about 1 s, not 0.5 s; count from the script; include warm-ups, controls in every command, builds, flushes, helpers; label the launch assumption | Agreed. `run_asimov.sh --dry-run` now prints every command, and `est_chip_time.py` counts hops, control hops, chain lines, fills, flush lines, bytes, kernel calls and launches exactly from that list and applies labelled assumptions. Phase F: 32 commands, 14 helper launches, 46 launches, 8.0 M chase hops, 2.36 M control hops (the control runs in all nine `--cme` latency commands, now stated), 1.91 GB timed plus 0.67 GB warm-up, 31,041 kernel calls; 1.26 s (est.), of which 0.64 s is the 14 ms launch assumption. Whole run 4.0 s (est.), about 3 h wall. Codex's counts (30 commands, 13 helpers, 1.889 GB) were for the plan's previous row list; the two added call-cost rows and the flushed row under `cmncount` account for the differences | `run_asimov.sh --dry-run`, `est_chip_time.py` (new); plan 3.6, 4.4, 6 item 6; README build section and chip-time paragraph |
| R6 | Copy has two buffers; 48 KiB copy is 96 KiB of data; state per-buffer and combined sizes and call the levels intended regimes | Agreed. Per-buffer sizes and copy's doubled working set are stated, with the intended regime of each kernel and size, to be confirmed by the counters | plan 2.2 item 7, 2.1 row 4; README phase F bandwidth row |
| R7 | Every pass pays SMSTART, register save and SMSTOP; define reported bandwidth as complete-call throughput and add a transition-cost control | Agreed. Two rows added: 1 KiB read and 1 KiB write calls, 4096 passes, 3 reps; elapsed / 4096 bounds the per-call cost. Bandwidth is defined as complete-call throughput and small-footprint results are not assigned to width or the store path without that control. Keeping several passes inside one span was not done: it would change the kernels' interface and the C-level pass loop that the core rows use | `run_asimov.sh` call-cost rows; plan 2.1 row 6, 2.2 item 12, 4.1, 4.3 item 4; README phase F row |
| R8 | "Every row has a twin" overstates; compare OCM with this run's phase B, not run 1; record image differences; a signal does not drop streaming state (sigreturn restores it) but contaminates time | Agreed on all four. The matched subset is defined (rows 2, 3, 4 at six footprints, 7); OCM compares with the same run's phase B; Jacob's RTL `a10181848` and SCP `scp-v0.40.0` against Jesse's `0d9e214` and `scp-v0.34.0` are recorded beside the cross-run comparison; the signal wording now says a system call clears the state, a signal is survived but its handler time lands in the elapsed time, and the span is intended uninterrupted, not guaranteed | plan Short version, 2.1, 4.3 items 1 and 3; README gate paragraph |

Verification after the round: x86 host build and `--quick`; CRB build with Jesse's flags, no
warnings; `latency --perf` on the CRB with the core set (valid path, `perf_cov` 1.0000);
`cme_test` PASS under QEMU 11.1.3 and `--sme1` PASS under QEMU 8.2; `latency --cme` and
`bandwidth --cme` (including the 1 KiB call-cost row) produce rows under QEMU 11; `sh -n` on the
script; the dry-run lists 95 commands.

## 9. Codex review round 2 and what changed

R1 and R2 are closed. The rest:

| # | Comment | Response | Changed |
|---|---|---|---|
| R3 | `cmncount` counts the mesh over the whole command, so a per-timed-load mesh rule is unsupported; use `REFILL_OUTER` for outside-cluster evidence and keep SLC against DRAM as Insufficient data; INNER and OUTER are refill-source events, not demand-only, and INNER is not uniquely the L3 | Agreed. The mesh acceptance rule is removed; the whole-command mesh counts are corroborating traffic evidence only; outside-cluster evidence is `cme_l1d_refill_outer` per load; SLC against DRAM at a footprint is Insufficient data with the footprint and latency step as the hypothesis. The counters are described as refill-source counts, demand and prefetch alike, with INNER read as the DSU L3 or the idle partner core's L2 | plan 2.1 attribution paragraph, 4.3 items 2 and 5; README counters word and phase F flushed row; `run_asimov.sh` flushed-row comment |
| R4 | `IOC_RESET` keeps the enabled and running times, so the coverage was cumulative; compare deltas and move the baseline after rejected rows too; verify a partial row followed by a full row | Agreed and implemented: `perf_read` takes the row's times as the change since the previous read and moves the baseline on every complete read, valid or not. `perf_cov_test.c` (new) reproduces the review's scenario on the CRB: a crowded row is rejected as multiplexed (3.70 ms running of 14.30 ms enabled) and the next quiet row is accepted. The coverage is per row | `common.h` `perf_read`, `struct perfgrp`; `perf_cov_test.c`, `Makefile`; plan 3.2, 3.5a, 5 |
| R5 | Count one kernel call per OCM segment per pass (31,173, not 31,041); `helper_elapsed_ns` does not measure the launch cost; say what stays unmeasured | Agreed. The estimator counts calls per segment (31,173 now, time unchanged to three places). The claim that `helper_elapsed_ns` measures the launch cost is withdrawn: it spans the helper from `main` entry to exit, the loading of the helper and of the child before `main`, the uncounted commands and the shell have no timing, and the 14 ms per launch stays an allowance | `est_chip_time.py`; plan 4.4 table and text; README chip-time paragraph; `run_asimov.sh` header |
| R6 | The 2 MiB copy row touches 4 MiB, beyond the 3.75 MiB of unlocked SLC; bandwidth rows have no refill counters | Agreed. The regimes are stated by capacity only, the 2 MiB copy row is marked beyond the nominal unlocked SLC with its service unresolved, and the copy rows from 160 KiB to 1 MiB are placed in the unlocked SLC. No bandwidth row claims a measured service level | plan 2.2 item 7, 4.3 item 4 |
| R7 | The 1 KiB control includes data, fold and loop work; use it as an upper bound, not a subtraction | Agreed. The control is an upper bound and sensitivity check; if small against a 16 KiB call that limited conclusion is stated, otherwise the overhead stays unresolved and no small-footprint difference is assigned to width or the store path | plan 2.2 item 12, 4.3 item 4; README phase F row |
| R8 | Six remaining claims: signal wording in 1.3; "plumbing unchanged" and "directly comparable" in 2.2; the causal "most of a hop is not the cache"; old events in section 5; old budgets in README and the script; the script's "every row has a twin" and old event names | All six corrected: 1.3 uses the restored-on-return wording; 2.2 item 1 lists what differs (unit, kernel loop, per-call entry and exit, counter set, the added `perf_cov` column) and item 2 calls Jacob's numbers image-qualified reference points; the causal sentence in item 4 is removed; section 5 names 0x327D and 0x327E; README and the script carry the 4 s (est.) budget with the launch allowance named; the phase F comment names the matched subset and the refill-source events | plan 1.3, 2.2 items 1, 2, 4, 5; README lines 6 to 9 and chip-time paragraph; `run_asimov.sh` header and phase F comment |
| R9 | Demand-load addresses arrive translated by the host core; the CME's TLB belongs to its prefetcher | Agreed. Open item 4 now says the page-size asymmetry is the core's translation, the CME's TLB serves its prefetcher (TRM chapter 5), and a random chase gives the prefetcher little to do | plan 6 item 4 |

Verification after the round: x86 host build; CRB build with Jesse's flags, no warnings;
`perf_cov_test` PASS on the CRB; `latency --perf` core set rows valid with `perf_cov` 1.0000;
`cme_test` PASS under QEMU 11.1.3 and `--sme1` PASS under QEMU 8.2; `sh -n` on the script;
the dry-run and the estimator rerun (31,173 kernel calls; totals unchanged).

### 9.1 Round 2 addendum (the coverage test) and what changed

| Comment | Response | Changed |
|---|---|---|
| `perf_cov_test.c` left its stack groups uninitialized, so the new baseline fields were indeterminate; initialize them in the test or in `perf_open_set` | Both. `perf_open_set` now zeroes the whole group before opening (fds, errno, baseline), so every caller starts clean, and the test zero-initializes its groups as well | `common.h` `perf_open_set`; `perf_cov_test.c` |
| The crowded-row check accepted unrelated errors and could pass without enough groups; an unavailable setup must skip, not pass | The test now skips (exit 2) when fewer than six extra groups open, and the crowded row passes only when it is rejected with the reason `multiplexed` and its running time below its enabled time; the printed rows show which path ran | `perf_cov_test.c` |

Rerun on the CRB after the change, pinned to CPU 2, three times: the crowded row is rejected as
`multiplexed` with running 0.68 to 3.71 ms of 14.3 ms enabled, the quiet row is accepted with
running equal to enabled; build without warnings. The emulator will exercise the same code with
the CME set.

## 10. Codex review round 3 and what changed

| # | Comment | Response | Changed |
|---|---|---|---|
| R3 | Do not read the refill-source counts as demand refills on the grounds that the chain is random; repeated random chains can be learned | Agreed. The counts are reported as refill-source counts; demand-only is a stated hypothesis, with run 1's learned-chain evidence as the reason it is not assumed | plan 2.1 attribution paragraph; 6 item 4 |
| R4 | Finish the test correction: initialize the stack groups, require the `multiplexed` reason, record the outcome | Done in section 9.1 (written after round 3's review began): `perf_open_set` zeroes the group, the test zero-initializes its groups, skips with exit 2 below six extra groups, and passes only when the crowded row is rejected as `multiplexed` with running below enabled. Rerun on the CRB three times after the change: PASS each time, running 0.68 to 3.72 ms of 14.3 ms enabled on the crowded row, build without warnings | `common.h`, `perf_cov_test.c`; plan 9.1, 5 |
| R5 | `helper_elapsed_ns` includes the child's loading (fork through execvp to exit) and excludes the helper's own loading; neither isolates launch cost | Agreed; the sentence now says exactly that | plan 4.4 |
| R6 | A chase row at the same footprint does not measure a stream's service source; keep the capacity labels as hypotheses | Agreed; the exception is removed and the bandwidth regimes are hypotheses by capacity only | plan 2.2 item 7 |

No code changed in this round beyond section 9.1's test and group initialization. Builds and
tests as in 9.1.

### 10.1 Round 3 follow-up (R8 / R3 wording) and what changed

| Location | Was | Now |
|---|---|---|
| README, streaming mode word | a system call or a signal drops the state | a system call clears it; a signal is survived with its handler time in the elapsed time |
| README, CME chase row | the CME counters say which level served it | the refill-source counters say CME L1, inside or outside the cluster; the outside level is a hypothesis from the footprint |
| plan 2.2 item 8 | flushed CME rows stand for DRAM | the flushed 8 MiB CME row is the intended DRAM reference; its outside-cluster source is unproven, only `refill_outer` near 1 is evidence |

## 11. Run 2 result: the per-region prefetch defect, and the sparse chain

Run 2 (`results/membench-jibin-002`, received 2026-11-02) met every criterion except one, which
phase F inherits because its OCM rows reuse the same chains.

**The defect.** The 256 KiB per-region OCM rows (`--fresh 3 --flush`, 4,096 lines, 4 KiB pages)
count 1.1143 to 1.4468 L2 refills and 0.7627 to 0.9500 L3 read refills per load over their 40
timed passes (20 files: CPUs 2, 4, 6, 8, regions 0 to 4, two passes each), and in 19 of 20 files
the faster of the two passes is the one with fewer L3 refills [latency-ocm-region*-cpu*.csv;
Jesse's README line 66]. The eight all-five passes (1.25 MiB) count 1.0003 to 1.0006 L2 and
1.0007 to 1.0011 L3 refills per load, the two 8 MiB flushed DRAM passes 1.0001 L2 refills per
load in both and 1.0002 then 1.0001 L3 refills per load.
The reading, a hypothesis consistent with these counts but not proven by them: on the small rows
a prefetcher brings in lines beside the missed ones, every line of every page is a chain member,
the 256 KiB buffer fits in L2 plus L3 (384 KiB), so the chain later finds 5 to 24 % of its lines
already there. A fresh chain changes the order of the walk, not the set of lines, so it cannot
remove this.

**The mitigation.** `latency --sparse`: chain c's members are line 8c + 4 of every 4 KiB page, one
line per page per chain, different lines for different chains. No member has a member as a
neighbour and a pass visits each page once, so a line fetched beside a member is not a member and
a page gives a page-based prefetcher one touch per pass. It is an experimental mitigation for the
reuse of adjacent lines; the counters cannot show that no member was prefetched, so demand-only
OCM latency stays Insufficient data where that distinction matters, and the sparse rows are read
beside their dense controls. A pass is bytes / 4096 hops (64 per 256 KiB region, 320 over all
five); `--fresh 8` gives seven timed passes. Sizes must be multiples of 8 KiB (the core chase
loop now handles any hop count, round 4 R12); the flush still covers every line of the buffer.

**Short passes.** A sparse per-region timing is the complete-call elapsed time of a 64-hop walk
divided by 64; the pure per-hop cost is not resolved. Three things bound what a short pass
carries: `# bracket_overhead_ns=` (median of 32 empty timed brackets, the two clock reads), the
new `cme-call` rows (64 complete one-hop `cme_roundtrip` calls timed together, per call: the
register save, SMSTART, the predicate setup, one register hop, SMSTOP, the restore and the C
loop around them, not separated; a 64-hop CME chase pass pays the same entry and exit once, so
the short pass is read beside this row, not corrected by it), and the quantization of a 64-hop
row: 1/64 ns per 1 ns of clock step and 1/64 refill per counted event (1/320 on the all-five
rows). The empty bracket measures the timer interval only: it contains no `chase()` call,
dispatch, loop setup or return, so the core chase call's own cost stays unresolved and no
control bounds it. The 65,536-hop `cme-roundtrip` row is not subtracted from anything.

**Rows changed.** The fix is in the shared `latency.c`, so it applies to the core rows and the
CME rows alike. Phase B's 20 per-region rows (CPUs 2, 4, 6, 8) and its four all-five rows, and
phase F's five per-region CME rows and its all-five row, use `--sparse --fresh 8 --flush`; the
dense all-five row (`--fresh 3 --flush`, 1.25 MiB, the row whose counters were clean in run 2)
stays beside each sparse all-five row as the control (`latency-ocm-all5-dense-cpu<c>.csv`,
`cme-latency-ocm-all5-dense.csv`). The run 2 session (asimov-04) confirmed the same reading of
the defect independently, asked for exactly this phase B change, and edits neither file in
parallel. The run now has 100 commands, 166 launches, 4.1 s (est.); phase F 33 commands, 48
launches, 1.29 s (est.).

**How the sparse rows will be read.** Diagnostic comparisons, no hard acceptance claim: the
seven sparse passes' spread (within-sparse repeatability, with the 1/64 quantization in mind) is
reported separately from the agreement of the sparse median with the dense all-five mean (the
dense pair's spread in run 2 was 0.007 to 0.057 ns per hop by core, too tight to serve as a
tolerance for 64-hop rows); the refill counts per hop are reported with their 1/64 or 1/320
step. A sparse row whose counts or times sit far from its dense control is reported with both
numbers, not discarded.

**A caveat from the CRB.** On the CRB's Neoverse V3AE core, the sparse 256 KiB chase counts 3.8 to
7.3 L2 refills per hop and runs at 145 to 158 ns per hop, against 1.00 and 28.9 ns for the dense
chain: that core fetches several lines around a missed line, all wasted on a sparse chain, and
the wasted traffic slows the demand loads. Whether the C1-Nano does the same is not known: its
dense counts near 1.00 per hop cannot rule it out, because in a dense chain a prefetched line
replaces a later demand refill and the total stays near one per hop (round 4 R10). The
sparse-against-dense all-five pair on Asimov is the test; if the sparse rows come back slow with
high refill counts, the dense rows remain the numbers of record and the sparse rows are reported
as the experiment that failed. The CRB numbers are a warning about the method, not an Asimov
measurement.

Verification: x86 mechanics (chains build and walk, sizes 256 KiB and 1.25 MiB, 64 and 320
hops); CRB build with Jesse's flags and the counter comparison above; QEMU 11 `--cme --sparse`
run produces the rows; `sh -n` on the script; the dry-run and the estimator rerun.

## 12. Codex review round 4 (section 11) and what changed

| # | Comment | Response | Changed |
|---|---|---|---|
| R10 | Dense refill counts near 1.00 cannot show that the Nano does not prefetch on first touch (a prefetch replaces a later demand refill); the counters cannot show that no member was prefetched; label the run 2 explanation a hypothesis | Agreed on all three. The sparse chain is described as an experimental mitigation for adjacent-line reuse; the first-touch exclusion is withdrawn; demand-only OCM latency is Insufficient data where it matters; the run 2 reading is a hypothesis consistent with the counts; the sparse rows are read beside their dense controls | plan 11 (three paragraphs), 2.1 row 3; README sparse word, phase B and F rows; `latency.c` and `run_asimov.sh` comments |
| R11 | The empty bracket does not cover the streaming entry and exit of a 64-hop call; the dense pair's spread is not a tolerance; state the 1/64 quantization | Agreed. New `cme-call` rows (64 one-hop calls timed together, per call) bound the fixed cost of a CME chase call; sparse timings are complete-call time over hop count with the per-hop cost unresolved; the `cme-roundtrip` row is subtracted from nothing; the quantization is stated (1/64 ns per 1 ns clock step, 1/64 refill per event, 1/320 on all-five rows); acceptance claims are replaced by diagnostic comparisons with within-sparse spread and sparse-against-dense agreement kept separate | `latency.c` `run_roundtrip` (`cme-call` rows); plan 11 "Short passes" and "How the sparse rows will be read", 4.1; README output format and phase F row |
| R12 | The core chase runs groups of eight loads, so sparse sizes with 2, 4 or 6 members over-walk and the denominator is wrong | Agreed and fixed: the core loop now runs whole groups of eight and then the remainder one hop at a time, so the reported hop count is the executed count for any size; the 8 KiB unit stays. Verified with a host probe (an 8-node ring: requests of 1 to 8 and 100 hops end at the expected node) and the x86 sparse mechanics at 8 KiB, 16 KiB and 24 KiB | `latency.c` `chase`; plan 11 |
| R13 | The operative tables and the script header still carried the dense rows and 32 commands / 46 launches; the ranges must be exact and say whether they are per pass or per file | Agreed. Section 2.1 row 3, the 4.1 file table and 4.4 budget now carry the sparse row set, the dense control and 33 commands / 48 launches (whole run 100 / 166, 4.1 s est.); the script header, README and source comments say 33 / 48; every range is now per pass with the pass count: 1.1143 to 1.4468 L2 and 0.7627 to 0.9500 L3 over 40 per-region passes, 1.0003 to 1.0006 and 1.0007 to 1.0011 over the eight all-five passes | plan 2.1, 4.1, 4.4, 11; `run_asimov.sh` header and comments; README; `latency.c` comment |

Verification after round 4: x86 build and `--quick`; the chase probe (8-node ring, hop counts 0
to 8 and 9 to 100 in steps of 7 end at the expected node) PASS; x86 sparse runs at 8 KiB, 16 KiB
and 24 KiB (2, 4 and 6 members) produce rows with the executed hop counts; CRB build with
Jesse's flags, no warnings; `perf_cov_test` PASS; `cme_test` PASS under QEMU 11.1.3 and `--sme1`
under QEMU 8.2; `latency --cme --sparse` under QEMU 11 prints the `cme-roundtrip`, `cme-call` and
sparse rows; `sh -n` on the script; the dry-run and the estimator reproduce 33 commands, 48
launches (phase F) and 100 commands, 166 launches (whole run).

## 13. Packaging for Jesse: run_all.sh, run_cme.sh, lib_run.sh

Jibin's instruction (2026-11-02 evening): one top-level script that runs both the cache test
(run 2's code with the sparse fix) and the CME test, pushed to GitHub, with a message to Jesse.

| File | What changed |
|---|---|
| `lib_run.sh` (new) | the block that was the top of `run_asimov.sh`: option parsing (`--quick`, `--dry-run`, `--out`), the output directory and log, the binaries check, the home-node ids and mesh events, the CPU sets, the `say` / `run` / `cmn` / `cmn0` / `cpu_set_online` helpers, and the OCM / SPM / SME2 detection. Sourced by both scripts after they set `HERE`. `run` now appends to `all.txt` directly (there is no `all.txt.tmp` any more, since two scripts write one directory) |
| `run_asimov.sh` | sources the lib; phases 0, A, B, D, E, C unchanged in content (phase B with the sparse rows); phase F removed; header updated |
| `run_cme.sh` (new) | phase F exactly as it was inside `run_asimov.sh`, with its own header, its own CPU 3 offline and online around the rows, the `sme2` gate, and the done lines; runs alone or after `run_asimov.sh` |
| `run_all.sh` (new) | `run_asimov.sh --out DIR` then `run_cme.sh --out DIR` with the other options passed through; prints both exit codes; exit 0 only when both are 0 |
| `README.md` | files table, "How to build and run" (`sh run_all.sh`), the dry-run and quick lines |

The measurement rows, labels, file names and counters did not change in this step; the
dry-run of `run_all.sh` reproduces 100 commands, 66 helper launches, 166 launches, 4.111 s
(est.), and `run_cme.sh --dry-run` alone 33 commands and 48 launches. `sh -n` passes on all
four scripts; `sh run_all.sh --quick` on the x86 host runs phases A, D, E, reports phase F
skipped (no `sme2`), writes one directory with one `all.txt` and exits 0; the CRB `--quick`
run is in the verification table below.

Hand-off state: the commit goes on top of `8ae533c` in jhan-positron/asimov `cache-mem-perf`
when the review loop closes; Jesse builds and runs `sh run_all.sh`; the chip-time budget to
restate is about 4.1 s (est.) against the 2 s he was told for run 2 and his 5 s allowance.

### 12.1 Round 4 follow-up and what changed

| Comment | Response | Changed |
|---|---|---|
| R11: the empty bracket does not bound the core call; `cme-call` is a complete one-hop control, not "minus one hop" | Agreed. The bracket is described as the timer interval only, with the core chase call's cost unresolved; `cme-call` is described as a complete one-hop call (entry, predicate setup, one register hop, exit, the C loop) whose parts are not separated, read beside a short pass and not subtracted | plan 11 "Short passes"; README output format; `latency.c` comment |
| R11: README's "must match" acceptance rule | Replaced by the diagnostic comparison of section 11; a discrepant sparse row is reported with both numbers | README phase B all-five row |
| R13: the estimator missed the 64 one-hop calls per rep | `est_chip_time.py` now counts them (reps x 64 per `--cme` latency command: 1,920 calls, 2,623,360 control hops in all) as hops at the round-trip assumption plus one kernel call each at the 50 ns call assumption; the 32 empty brackets per command and the timer reads around each pass are stated as unmeasured and not counted. Phase F total unchanged at 1.29 s (est.) to two places | `est_chip_time.py`; plan 4.4 table row |
| R13: the flushed DRAM sentence | Corrected: 1.0001 L2 refills per load in both passes, 1.0002 then 1.0001 L3 | plan 11 |

### 13.1 Packaging review (R14 and the R13 follow-up) and what changed

| Comment | Response | Changed |
|---|---|---|
| R14: `run()` returned the status of its `rm`, each suite ended with a successful `say`, so `run_all.sh` could report success after failed measurements | Agreed and fixed. `run()` counts a failing command in `FAILS` (its exit status is still logged as `(exit N)` and its rows still collected); `finish_suite` prints the count and exits 1 when it is nonzero, and both suites call it after their CPU state is restored (`run_cme.sh` brings CPU 3 back first); `run_all.sh` prints both codes and exits 0 only when both are 0. Tested with stub binaries in a scratch directory, no hardware: a `latency` stub that exits 7 on the first phase A row gives `(exit 7)` in the log, "1 measurement command(s) failed", `run_asimov.sh` exit 1, `run_cme.sh` exit 0 (phase F skipped on the host) and `run_all.sh` exit status 1, with the other rows' output present; the succeeding stub set gives exit 0 | `lib_run.sh` (`FAILS`, `finish_suite`), `run_asimov.sh`, `run_cme.sh`, `run_all.sh`; README build section |
| R13 follow-up: section 4.4 cited `run_asimov.sh --dry-run --phase F`, which now yields nothing; sections 2.2 item 9, 3.6, 6 item 6 and 7 still placed phase F inside `run_asimov.sh` | Corrected: 4.4 cites `run_cme.sh --dry-run` for phase F and `run_all.sh --dry-run` for the suite; the four operative references now describe the split | plan 4.4, 2.2 item 9, 3.6, 6 item 6, 7 |

Verification: `sh -n` on all four scripts; the stub runs above; `sh run_all.sh --quick` on the x86
host exits 0 with "0 measurement command(s) failed" from both suites; the dry-run counts are
unchanged (100 commands, 166 launches; phase F 33 and 48).

