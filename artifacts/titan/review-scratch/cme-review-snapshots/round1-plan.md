# Asimov CME load and store test (phase F of cache-mem-perf): context, design, code and data

Written 2026-11-02 by Jibin Han's Claude session for review by codex. Review comments go to
`codex-review-CME-plan.md`; each round's responses are appended here in numbered sections.

**Short version.** Bill Baumann asked for the C1-Nano cache statistics again with the CME, the
DSU's Arm C1-SME2 matrix unit, doing the loads and stores, on one core. Phase F adds that to
`run_asimov.sh`: the same chains, footprints and flush rules as phases A, B and D, run through the
CME in streaming SVE mode, so every CSV row has a C1-Nano twin. The code builds with Jesse's flags,
its kernels pass a self-test under QEMU 11 with SME2, and nothing has run on the emulator yet.

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
- Round trip: a DUP of a general register into a Z register followed by `LASTB` back to a general
  register, in streaming mode, with no memory access. It is the core-to-CME-to-core path that every
  CME chase hop also pays.
- CME counters: C1-SME2 PMU events read through the core PMU with `perf_event_open`:
  `CME_CYCLES` 0x3246, `CME_L1D_CACHE_REFILL_RD` 0x3280, `CME_BUS_REQ_RD` 0x3268 (names and
  numbers from TRM 107831 chapter 12; asimov-bench reads them the same way).
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
- Streaming mode rules: no system call and no signal inside a streaming span (either drops the
  state); no Advanced SIMD (the CME has no FA64); the first `SMSTART` of a thread traps to the
  kernel once; `d8` to `d15` and `FPCR` must be saved around the span.
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
| 1 | What does a CME load cost before any memory is touched? | `cme-roundtrip`: a chain of DUP + LASTB hops, 64 K hops, 3 reps | none; it is the floor to subtract from every CME chase hop |
| 2 | Load-to-use latency through the CME by level: CME L1 (64 KB), DSU L3 (256 KiB), SLC, DRAM | `latency --cme --perf` repeated chase at 4 KiB to 384 KiB; fresh chains at 512 KiB to 32 MiB; fresh + flush at 8 MiB | phase A, same sizes and options |
| 3 | OCM latency through the CME, per region and all five | `latency --cme --perf --mem ocm --fresh 3 --flush`, 256 KiB per region and 1.25 MiB, under the mesh counters | phase B, CPU 2 rows |
| 4 | Bytes per second one core streams through the CME: read, write, copy with 256 B per instruction | `bandwidth --cme --kernel all` at 16 KiB, 48 KiB, 96 KiB, 160 KiB, 256 KiB, 1 MiB, 2 MiB, 32 MiB | phase D (which has no 160 KiB and 1 MiB; those sit inside the DSU L3 and the SLC, the two levels that matter more for the CME) |
| 5 | Does the instruction width limit the stream? | `bandwidth --cme --kernel ldr16` and `str16` (single-vector 64 B loads and stores) at 16 KiB, 2 MiB, 32 MiB | phase D's `ldr16`/`str16` exist only for SPM; the comparison is with row 4 |
| 6 | OCM read and write through the CME | `bandwidth --cme --mem ocm` read per region, read all five, write all five, flushed before, under the mesh counters | phase D OCM rows |

Which level served a CME chase comes from the CME counters per load: `CME_L1D_CACHE_REFILL_RD`
near 1 means the CME L1 missed; `CME_BUS_REQ_RD` near 1 means the request left the CME (to the
DSU L3 or beyond). The DSU L3 and the mesh are told apart by the latency step and, for OCM, by
the mesh counters.

### 2.2 Method decisions

1. **Same harness, new engine.** `--cme` is an option of the existing `latency` and `bandwidth`
   programs, not a new program. The chain builder, the fresh and flush logic, the buffers (huge
   pages, OCM regions), the reps, the CSV layout and the counter plumbing are unchanged, so a CME
   row differs from its twin only in which unit executes the loads and stores.
2. **Instruction forms are the asimov-bench forms.** Chase: `LD1D {z0.d}, p0/z, [x0]` with a
   one-element predicate, then `LASTB x0, p0, z0.d` (their `chase.S`). Stream: `LD1B` of four
   vectors with `[x0, #k, mul vl]` offsets, four per KiB (their `stream.S`). Stores use the matching
   `ST1B` of four vectors. So our chase numbers are directly comparable with their 21.56 ns and
   26.60 ns, and our read stream with their 34.5 GB/s.
3. **One streaming span per call.** Each kernel does `SMSTART SM`, its whole loop, `SMSTOP SM`.
   The timer and the counter reads are outside the span (they are system calls). The first
   `SMSTART` of the thread traps once; every timed path has an untimed warm-up call before it
   (`latency` already walks each chain twice before timing; `run_roundtrip` does one untimed call;
   `bandwidth` runs one warm-up pass per rep).
4. **The round trip is its own row.** A CME chase hop is load latency plus the register return path.
   Jacob's 21.56 ns from the CME L1 is about 43 cycles, ten times the core's L1. The
   `cme-roundtrip` row gives that path without memory, so the memory part of each level is the
   chase minus the round trip (reported both ways; the subtraction is an estimate of the memory
   part, not a measurement of it).
5. **Read kernels fold everything they load.** Every loaded vector is XORed into an accumulator
   and the fold is returned. In `bandwidth` the fold goes to a volatile sink; in `cme_test` it is
   compared with a scalar XOR of the buffer, which is how the first bug was caught. EOR issues at
   two per cycle on the CME beside the load pipe, so the fold does not slow a memory-bound stream;
   from the CME L1 the loads themselves cost 2 cycles per 256 B.
6. **Stores write a constant.** `cme_write4` and `cme_write1` store a value every 8 B, like the
   core's `k_write`. No read of the destination, so a write row is a pure store stream.
7. **Footprints.** The CME sweep keeps every phase A and D size so the twins line up, and adds
   160 KiB and 1 MiB to the bandwidth rows: the CME has a 64 KB L1 and then the 256 KiB DSU L3,
   so 96 KiB and 160 KiB both sit in the L3 and 1 MiB sits in the SLC. 4 KiB to 48 KiB are inside
   the CME L1, 64 KiB is at its edge.
8. **Flush rules carry over.** `DC CIVAC` from the core cleans and invalidates a line everywhere in
   the coherent system, the CME L1 included (Jacob's chase cleans the same way). Flushed DRAM rows
   still stand for DRAM, not the SLC, as run 1 showed.
9. **CPU 3 stays offline.** The two cores of a DSU share one CME. Phase F runs after phase D and
   before phase E, in the window where CPU 3 is already offline.
10. **Gate and self-description.** The script runs phase F only when `/proc/cpuinfo` lists
    `sme2`; each `--cme` program checks the SME and SME2 hwcaps and that `RDSVL` returns 64 and
    exits 2 with a `# cme:` line otherwise. A missing row then says why.
11. **CME counter set.** `--perf` with `--cme` opens cycles plus the three CME events instead of
    the core refill events, in one group as before. The column names come from the open set, so
    the CSV header says which set it holds.

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

### 3.1 `cme_kern.S` (new, 246 lines)

Eight AAPCS64 functions under `.arch armv9.3-a+sve2+sme2`. Two macros, `SM_ENTER` and `SM_LEAVE`,
push `d8` to `d15` and `FPCR`, enter streaming mode, and the reverse.

| Function | Loop body | Bytes per instruction |
|---|---|---|
| `cme_svl()` | `RDSVL x0, #1` (legal outside streaming mode) | |
| `cme_chase(p, hops)` | `LD1D {z0.d}, p0/z, [x0]`; `LASTB x0, p0, z0.d`; `SUBS`; `B.NE` (p0 = `PTRUE p0.d, VL1`) | 8 B read per hop |
| `cme_roundtrip(x, n)` | `MOV z0.d, x0` (DUP); `LASTB x0, p0, z0.d`; `SUBS`; `B.NE` | none |
| `cme_read4(p, bytes)` | four `LD1B {z0-z3 ... z12-z15}, pn8/z, [x0, #0/4/8/12, mul vl]`, 16 `EOR` into z16 to z19, `ADD x0, #1024`; after the loop `EORV` and `FMOV` return the fold | 256 |
| `cme_write4(p, bytes, v)` | four `ST1B {z0-z3}, pn8, [x0, #k, mul vl]` of a DUP'd v | 256 |
| `cme_copy4(d, s, bytes)` | four `LD1B` from s, four `ST1B` to d, per KiB | 256 + 256 |
| `cme_read1(p, bytes)` | eight `LD1B {zk.b}, p0/z, [x0, #k, mul vl]`, eight `EOR`, `ADD x0, #512` | 64 |
| `cme_write1(p, bytes, v)` | eight `ST1B {z0.b}, p0, [x0, #k, mul vl]` | 64 |

`bytes` must be a multiple of 1024 (`bandwidth` enforces it). The multi-vector forms need SME2;
the chase, the round trip and the single-vector forms need only SME.

### 3.2 `common.h` (73 changed lines)

- Declarations of the eight kernels for AArch64, and inline stand-ins returning 0 for a non-Arm
  host build, so `make` on x86 still works.
- `require_cme()`: `getauxval(AT_HWCAP2)` must have `HWCAP2_SME` (bit 23) and `HWCAP2_SME2`
  (bit 37), and `cme_svl()` must return 64; otherwise print `# cme: ...` and exit 2.
- `perf_open_set(g, raw, names)` generalizes the one fixed group; `perf_open()` keeps the core set
  (0x03, 0x17, 0xA2) and `perf_open_cme()` opens 0x3246, 0x3280, 0x3268. `struct perfgrp` carries
  the column names of the open set.

### 3.3 `latency.c` (69 changed lines)

- `--cme`: `chase()` calls `cme_chase()` instead of the C pointer loop; mode labels get a `cme-`
  prefix (`cme-repeat`, `cme-fresh1`, `cme-flushed`, `cme-best`); `--perf` opens the CME set; the
  header line prints `cme=1` and the counter column names of the open set.
- `run_roundtrip()`: before the sizes, `--reps` timed calls of `cme_roundtrip(x, --loads)` after one
  untimed call, printed as rows with size 0 and mode `cme-roundtrip`, plus `cme-roundtrip-best`.
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

### 3.6 `Makefile`, `run_asimov.sh`, `README.md`

- `Makefile` links `cme_kern.S` into `latency`, `bandwidth` and `cme_test` when
  `$(CC) -dumpmachine` contains `aarch64`, so the x86 host build and Jesse's cross or native build
  both work without options.
- `run_asimov.sh` (54 changed lines): phase F between D and E, gated on `sme2` in `/proc/cpuinfo`,
  with the rows of section 2.1; the header comment and the chip-time note updated.
- `README.md` (42 changed lines): phase F rows in "What each phase measures", the words CME,
  streaming mode, SVL and CME counters, the two new files, the gate and the streaming rules, and
  the chip-time paragraph.

## 4. Data collection and output

### 4.1 Files phase F writes (in `results/<UTC time>/`)

| File | Program and options | Rows |
|---|---|---|
| `cme-latency-dram-small.csv` | `latency --cme --cpu 2 --perf --loads 64K --reps 3 --sizes 4K..384K` | 3 `cme-roundtrip` rows + best, then per size 3 `cme-repeat` rows + `cme-best` |
| `cme-latency-dram-large.csv` | `--fresh 3 --sizes 512K..32M` | per size `cme-fresh1`, `cme-fresh2`, `cme-best` |
| `cme-latency-dram-flushed.csv` | `--fresh 3 --flush --sizes 8M` | the same, flushed |
| `cme-latency-ocm-region<r>.csv`, `cme-latency-ocm-all5.csv` | `--mem ocm --fresh 3 --flush` under `cmncount` | the same, plus the mesh counts in `cmn-counts.csv` with labels `cme-ocm-region<r>-cpu2`, `cme-ocm-all5-cpu2` |
| `cme-bandwidth-dram-1core.csv` | `bandwidth --cme --kernel all` at 8 footprints; `ldr16`, `str16` at 3 | per kernel and size 3 reps + best, kernel names `cme-read`, `cme-write`, `cme-copy`, `cme-ldr16`, `cme-str16` |
| `cme-bandwidth-ocm-region<r>.csv`, `cme-bandwidth-ocm-all5.csv`, `cme-bandwidth-ocm-write.csv` | `bandwidth --cme --mem ocm --flush-before` under `cmncount` | as phase D's OCM rows, labels `cme-ocm-read-region<r>`, `cme-ocm-read-all5`, `cme-ocm-write-all5` |

Every row is also in `all.txt` after its command line, and every command line with its uptime stamp
in `log.txt`, as in run 2.

### 4.2 Row formats

`latency` rows: `mem,size_bytes,mode,rep,loads,ns_per_load[,cycles_per_load,cme_cycles_per_load,cme_l1d_refill_rd_per_load,cme_bus_req_rd_per_load]`.
The counter columns are present when the group opened; the header names them. A `cme-roundtrip`
row has `size_bytes` 0.

`bandwidth` rows are unchanged: `mem,kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps`
with the `cme-` kernel names. The header comment carries `cme=1`.

### 4.3 How the data will be read

1. **Side-by-side latency table** per footprint: core best (phase A) against CME best (phase F),
   and CME best minus the round trip (est., labelled so). Expected shape from Jacob's numbers:
   about 21 ns flat up to 48 KiB, a step near 64 KiB (CME L1 edge), about 27 ns to 256 KiB (DSU
   L3), then the SLC and DRAM steps about 20 ns above the core's (the mesh part is the same path).
2. **Level attribution** from the two CME counters per load, against the core's three refill
   counters per load in the twin row.
3. **OCM**: per-region CME latency against the core's 18.8 to 23.2 ns, with the home-node request
   counts checking that the traffic went to the expected node.
4. **Bandwidth table**: CME read, write, copy against the core's, per footprint; the 256 B and
   64 B forms against each other. Expected: CME read above the core's 9 to 10 GB/s beyond L2
   (Jacob: 34.5 GB/s from DRAM); CME write unknown (no prior number; the core does 32 GB/s).
5. **Sanity checks** before any number is used: every `--cme` program printed `cme=1` and no
   `# cme:` refusal; `cme_cycles_per_load` close to `cycles_per_load` (the CME stayed allocated to
   CPU 2); the OCM rows' mesh counts land on the expected home node.

### 4.4 Chip time (est.)

The CME chase pays about 22 ns per hop from its L1 (Jacob) against the core's 2 ns, so the phase A
sizes through the CME cost about ten times phase A's small rows: about 0.1 s for the 4 KiB to
384 KiB rows (12 sizes x 3 reps x 64 K loads x about 22 to 30 ns) and about 0.25 s for the fresh
rows (each size walks its chains four times at 30 to 70 ns per hop; 32 MiB alone is 0.1 s). The
bandwidth rows move about 1 GB at 20 to 35 GB/s, about 0.05 s. The OCM rows add about 0.03 s and
the launches about 40 x 14 ms. Phase F total about 0.5 s; run 2 plus F about 2.5 s, about 2 h of
wall time at 2,779 s per chip second.

## 5. Verification done

| Check | Where | Result |
|---|---|---|
| Host build with the stand-ins, `run_asimov.sh --quick` | x86 agent host | builds; phase F reported skipped (no `sme2` in cpuinfo) |
| Build with Jesse's flags; `objdump` shows the eight `cme_*` symbols and 18 `smstart`/`smstop` | CRB, GCC 14.2, binutils 2.42 | builds, no warnings |
| `latency --cme`, `bandwidth --cme`, `cme_test` on a machine without SME | CRB (Neoverse V3AE) | each prints `# cme: SME2 not supported` and exits 2 |
| `run_asimov.sh --quick` | CRB | phases A, D, E run; F skipped with the reason line |
| `cme_test --sme1` (chase, round trip, 64 B read and write) | QEMU 8.2 on the CRB, `-cpu max,sme-default-vector-length=64` | first run: 3 failures (the read fold covered one vector in eight); after the fix: PASS |
| `cme_test` (all eight kernels) | QEMU 11.1.3 user mode on the x86 host (Debian `qemu-user` 11.1.3 extracted, SME2 present, SVL 64) | PASS, 0 failures |
| `latency --cme` with `--perf`, `--fresh 3`, `--flush`; `bandwidth --cme` with every kernel name; `latency` without `--cme` | QEMU 11.1.3 | CSV rows in the expected format; perf reported unavailable (QEMU has no PMU); timings meaningless |

Not verified: anything about timing, the CME counter events (whether the kernel accepts 0x3246,
0x3280, 0x3268 in one group with cycles; asimov-bench opens twelve CME events in one group on the
same kernel), the OCM path through the CME, and the chip-time estimate. All need the emulator.

## 6. Open items and risks for the reviewer

1. **The chase through the CME at tiny sizes.** With `--loads 64K` and a 4 KiB ring, the CME L1
   serves every hop; the row measures the round trip plus the L1 hit. Fine for the twin table, and
   the `cme-roundtrip` row separates the two. Is a second control, a chase whose line is already
   in a Z register, worth a row? Not added.
2. **CME counter group.** If the kernel refuses one of the three raw events, `perf_open_set` prints
   the event and leaves the group closed, and the rows come without counter columns (the harness
   already behaves this way for the core set). Nothing fails. The sysinfo step does not list the
   core PMU's events because the image has no `perf` tool; the C1-Nano TRM's event list is the
   reference.
3. **`DC CIVAC` and the CME L1.** The flush rows assume a core `DC CIVAC` invalidates the CME L1
   copy. The CME is a coherent requester on the DSU (it has its own L1 with coherency requests,
   TRM 107831 section 6), and Jacob's chase cleaned with `DC CIVAC` and then read OCM at 34.8 ns,
   above his L3 figure, which is consistent. Not proven on our rows.
4. **Huge pages and the CME TLB.** The CME has its own TLB and asks the host core for
   translations. The DRAM rows use 2 MiB pages, the OCM rows 4 KiB pages, as in run 2; a CME
   translation miss may cost more than a core miss. The OCM rows carry that asymmetry, as they do
   for the core.
5. **The `cme-` prefix on labels instead of a new column.** Chosen so the run 2 CSV layout and the
   report scripts stay as they are. A reader must match `cme-repeat` to `repeat`.
6. **Phase F position.** It runs after D and before E, inside the CPU 3 offline window. It adds
   about 40 launches and 0.5 s of chip time to run 2. The alternative is a run 3 of phase F alone;
   Jibin decides when the code goes to Jesse.
7. **Store rate anomaly.** asimov-bench saw back-to-back `st1h` at 3 cycles each where the RTL
   says 1. Our `cme-write` rows at 16 KiB will show whether 256 B stores stream at the CME L1 or
   stall; no row isolates the cause.

## 7. Files to read, in order

1. `cme_kern.S` (the kernels), `cme_test.c` (what is proven about them).
2. `common.h` (search `cme`), `latency.c` (search `cme`), `bandwidth.c` (search `cme`).
3. `run_asimov.sh` phase F block (search `F. the same loads`), `README.md` phase F rows and words.
4. `cme-survey.html` sections 2, 4 and 9 for the CME facts and the prior measurements, and
   `/scratch/jgeldbach/cme-perf-for-jibin/02-results-so-far.md` for Jacob's numbers.
