# 03: The code, and how to run it

Two codebases in positron-ai/asimov-bench measure the CMEs:

| Code | Path | For | State (2026-11-02) |
|---|---|---|---|
| **cme-perf bench** | `presilicon-perf/cme-perf/` | CME performance from userspace: latency, bandwidth, prefetch, per-instruction cost, all five CMEs at once, workloads such as GDN decode | PR stack #107 → #108 → #109, all **drafts**; read branch `feature/cme-perf-pr3` |
| DPA stress app | `dpa/stress/` | Whole-hemisphere and full-chip stress (CMEs plus DMA, SAL, CPS/TWS, SVL, XMS) with power receipts | #84-#88 merged; #91-#95, #121, #122 open for review |

**Start from cme-perf.** It's the CME bench; the stress app is for whole-chip load.

## cme-perf: the PR stack

| PR | Title | Adds |
|---|---|---|
| #107 | cme-perf/gdn: the GDN decode kernels and their host test | `gdn/kernel/`: Bill's GDN decode kernels (`gdn_rows` ZA kernel, 446 instructions per 16-row block; `gdn_rows_sve`, 766), a `GDN_NO_RPRFM` build that turns each `rprfm` into a `nop`, `count_insns.py`, and a host SME2 model so the kernel C runs without hardware (`make test`) |
| #108 | cme-perf: the CME bench with the chase mode and the GDN decode mode | `bench/cme_perf`: a static AArch64 bench, one pinned `SCHED_FIFO` thread per CME, a timer and CME-PMU window per call, buffers in DRAM or an OCM window. Modes `chase` (load latency) and `decode` (GDN, with a checked output digest) |
| #109 | cme-perf: the Palladium boot and checker, GDN, prefetch and five-CME sync rows | `palladium/` (`init.sh`, `rows.sh`, `build-composite.sh`, `check_cme_perf.py`), `stream` mode, `--sync` (five CMEs started together), `isa/` per-instruction tests, `gdn_rows_il`, and the row sets behind GA13 #3845-#4065 |

Review and merge order is #107 → #108 → #109. Each is based on main `07cd7ade8`. To read the code
before merge: `git fetch origin feature/cme-perf-pr3 && git worktree add <dir> origin/feature/cme-perf-pr3`
(see the build rule in `env-setup-general/AGENTS.md` for where `<dir>` goes).

## cme-perf: what the bench is

```
presilicon-perf/cme-perf/
  bench/      cme_perf: threads, timer, CME PMU, DRAM/OCM/SPM buffers; modes chase, stream, --sync
  gdn/        the GDN decode workload (decode mode) and its kernels
  isa/        generated per-instruction tests (throughput, latency, feed)
  palladium/  init.sh + rows.sh (the boot), build-composite.sh, check_cme_perf.py
```

A workload on the CME is CME performance with a specific set of ops. The timing, the PMU group and
the OCM mapping are shared in `bench/`, and each workload gets its own directory. GDN is the first.
New CME kernels would go in beside it.

**Modes**

| Mode | What it does |
|---|---|
| `chase` | Dependent 64 B loads in streaming mode over a random ring: CME L1, DSU L3, OCM (cleaned before each call); optionally under load from other CMEs |
| `stream` | A linear read, four 4-register `LD1B` per KiB, with `RPRFM PSTKEEP` at a set distance or a `NOP` in its slot (hardware prefetch only) |
| `decode` | One GDN kernel call per rep (`gdn_rows`, `gdn_rows_nopf`, `gdn_rows_sve`, `gdn_rows_il`), state in DRAM or OCM slots; a check rep compares the output digest |
| `--sync` | All listed CPUs start each rep at one timer value; reports per-CPU windows, overlap, skew and combined GB/s; `--users` gives each user its own slot; `--ev` adds the 12-event CME group and CMN HN-S counts |
| `isa` | CME cycles per instruction class, from loops at 4 and 132 iterations |

**Row sets** (`cme_perf.rows=<set>` on the kernel command line):

| Row set | Measures | GA13 runs |
|---|---|---|
| `palladium` | E3: ns per dependent load in L1, L3, OCM, OCM under load | #3845, #3955 |
| `decode`, `gdn` | E7 (cycles per block, state in L1), E9 (state streamed from OCM), and a mixed row | #3845, #3969 |
| `gdn-il` | `gdn_rows` against `gdn_rows_il` | #3983 |
| `isa` | Per-instruction throughput, latency and feed | #4001, #4007 |
| `pf` | Prefetch: E9 and `stream` from OCM, SMS and SPM, HW only and `RPRFM` 1-16 KiB ahead | #4045 |
| `sync` | Five CMEs at once from SMS: stream, then `gdn_rows_il` over 64 users | #4065 |
| `fvp`, `fvp-*` | Function-only versions for the FVP | — |

**Timed window and counters.** One rep is one call: `dsb sy; isb; mrs cntvct_el0`, the call,
`isb; mrs cntvct_el0` (1 tick = 1 ns). Per thread, user-only PMU group: `CPU_CYCLES` (`0x11`),
`CME_CYCLES` (`0x3246`), `CME_OP_MMDP_ISSUE` (`0x3264`), `SSVE_CONTEXT_SWITCH` (`0x32A8`). A rep is
unclean if the group was multiplexed or an SSVE context switch happened. A `decode` rep is also
unclean if CME cycles are under 95 % of CPU cycles.

**Output.** `uart_1.log` (AP console) carries `CME,*` records: `CME,hdr` (config), `CME,r` (every
rep), `CME,s` (medians per CPU), `CME,chk` (digest), `CME,st` (stream), `CME,sw`/`CME,sy`/`CME,ss`/
`CME,sg` (sync windows and results), `CME,isa`, `CME,done`. Full list: `cme-perf/README.md`, "Output".

## Build and check (host and FVP)

```sh
# in a worktree under /scratch/$USER/agent-builds (never in ~/dev)
make -C presilicon-perf/cme-perf/bench O=<dir> CROSS=<aarch64-none-linux-gnu- prefix>        # static cme_perf
make -C presilicon-perf/cme-perf/gdn/kernel O=<dir>/kernel PYTHON=<python with numpy> check-data
make -C presilicon-perf/spm-dma-lat/kernel KDIR=<kernel build dir> ARCH=arm64 CROSS_COMPILE=<prefix>   # spm_dma_map.ko, maps OCM/SPM

# host tests
make -C presilicon-perf/cme-perf/bench O=<dir> test
make -C presilicon-perf/cme-perf/gdn/kernel O=<dir> PYTHON=<python> test
make -C presilicon-perf/cme-perf/isa O=<dir> test
python3 presilicon-perf/cme-perf/palladium/check_cme_perf.py --selftest
```

- The GDN kernels need clang-19 (`-march=armv9-a+sme2 -O2`). The rest is C++17 with GCC 14.2, linked static.
- The FVP checks function only. It has no memory at the OCM windows (the first OCM store faults) and
  reads 0 for CME PMU events, so OCM rows and all CME counts come from Palladium.

## Run on Palladium

1. **Set up once:** `/scratch/jgeldbach/env-setup-general/README.md`, then `04-emulation.md` (GA13
   chamber account, ssh config, an asimov clone on the chamber). Install the `palladium-emulation`
   skill. It's Dan McDermott's skill, which Jacob's was built from, with the current GA13 rules
   added. Your agent follows it for every launch, health check and stop.
2. **Build the boot:** `palladium/build-composite.sh OUT` with `ROWS=<row set>`. It takes the asimov-os
   release, adds `/cme-perf` (bench, `spm_dma_map.ko`, check data) to the rootfs, sets
   `rdinit=/cme-perf/init.sh cme_perf.rows=<set>` in the Palladium DTB, and writes `OUT/os/` (the
   `ASIMOV_OS_DIR`) with `SHA256SUMS`.
3. **Launch** (with your yes), on the executor host, from your clone of the matching RTL release:
   ```sh
   ASIMOV_OS_DIR=<OUT>/os HEMI_LINUX_BOOT=1 PALLADIUM_HOST=<host> TOOLS_DIR=<tools dir> \
     emu/common/scripts/run.sh -Jd "<plain description>" --task emu --test hemi_tlm --rtws \
     --run-only --run-cycles 4000000000 --timelimit 10800
   ```
   - The bench has used `hemi_rtws_tlm` (4 boards).
   - 4.0e9 cycles = 2.0 s of chip time, about 100 min wall time at about 50 min per chip second.
     Linux reaches `init.sh` at about 0.22 s.
   - Don't pass `--pcie-boot`.
   - Take current flags from `run.sh --help` and the skill, not from this page.
4. **Health:** `CME,boot` on `uart_1` at the first checkpoint. If `uart_0` (SCP) stops before the AP
   powers on, stop the run (SIGTERM, per the skill).
5. **Check:** `python3 palladium/check_cme_perf.py <run dir>/uartout/uart_1.log --rows <set>`. It
   checks each row (rc, per-CPU records, digests, `CME,done`) and prints the numbers.

**Recipe used so far** (from `cme-perf/README.md`): RTL `a10181848` `hemi_rtws_tlm`; SCP BL1/BL2
scp-v0.40.0 (profile `cold-boot-ocm-w4`, 4 locked OCM ways per SLC); BL31 tfa-v0.24.0, kernel,
rootfs, DTB and SMS profile from asimov-os v0.0.13 (Linux 6.18.36).

**How we're preparing it next:**
- The stack is still in draft. It's moving to stock main firmware, so a run doesn't depend on a
  hand-picked SCP/BL31 set.
- The GDN recipes and other CME recipes will come through the presilicon-perf/bench recipe runner.
  That runner isn't in asimov-bench main yet. Ask Jacob for its status before building on the
  `build-composite.sh` path above.

## The DPA stress app (for whole-chip load)

`dpa/stress` runs a matrix of cases on all 10 CPUs and every block at once and writes `STRESS_*`
records, checked by `stress_receipt.py`.

| PR | Title |
|---|---|
| #91 | stress: SMS-to-SMS DMA bandwidth, stuck-engine containment, the idle case and two-case runs |
| #92 | stress: SAL feeder with the vendored RTL command packer, the SPM SRAM band map and the SAL receipt rules |
| #93 | stress: CPS replay feeder with an offline payload generator, TWS proof records and a rootfs unpack guard |
| #94 | stress: SVL schedule payloads, the SVL programming layer and recorded-only SVL rules |
| #95 | stress: XMS weight-path records, the streaming-xms profile and the WMEM_HEX_V1 lane preload |
| #121 | stress: HN-S retry counter sets and SMS write attributes |
| #122 | stress: DMA-357 channel groups and raw-XMS lanes (top of the stack) |

- The stack carries CME kernels (`src/kernels/k_cme.S`, `cme_stream.S`, `cme_pool.S`: FMOPA, BFMOPA,
  UMOPA, SME2 dot, memory streams), the CMN counter sets, and the DMA engine drivers.
- **The `cme_gdn` matrix case** (the GDN rows in 02, #4292-#4480) is *not* in the pushed stack yet.
  It's on local commits of the app (none of the #91-#122 branches has a GDN file). Ask Jacob for it if
  you need the SMS-fed/OCM-fed GDN case.

## Suggested first steps

1. Read 01 and 02, then `presilicon-perf/cme-perf/README.md` on `feature/cme-perf-pr3`.
2. Build the bench and run the host tests and an FVP `fvp` row set (function only).
3. For a first Palladium run, repeat a known row set (`pf` or `sync`) and check that your numbers match
   #4045 or #4065 before changing anything.
4. Add your own C1-Nano CME kernels as a new workload directory beside `gdn/`, reusing `bench/`.
