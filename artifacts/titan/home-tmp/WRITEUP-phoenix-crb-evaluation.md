# Phoenix CRB evaluation (Arm AGI CPU)

Measured 2026-10-01/02 on the Phoenix CRB (`arm@192.168.2.46`), compared with delphi-3c51
(Xeon 6962P, Granite Rapids, "GNR") and andoria-b1a3 (EPYC 9654, Genoa). Written 2026-10-19.

## Bottom line

- **Big cores, not little ones.** Neoverse V3 cores: per clock, at or above an Apple M1 P-core
  on 7-Zip and about 4× a Cortex-A53. One core ≈ one Genoa core and ≈1.2× a typical GNR core.
  GNR's 4 favored 4.4 GHz cores are ≈1.3× faster.
- **Two 64-core chiplets.** Each has its own ~64 MB L3. Inside a chiplet the L3 is fast
  (26–31 ns); reaching into the other chiplet costs about what a socket hop costs on GNR.
- **Interference stays inside a chiplet.** One streaming core can triple L3 latency for its whole
  chiplet; the other chiplet barely notices. L2 is never affected.
- **Memory bandwidth peaks at ~540 GB/s and collapses when every core streams**
  (reads drop to ~314 GB/s, writes to ~156 GB/s).
- **Branch-heavy code runs well.** Cheapest mispredicts of the three machines, and real
  orchestration code mispredicts less than on GNR.
- **No offload hardware.** No matrix engine (SME), no DMA engine, no on-die accelerators.
  128-bit NEON/SVE2 only.
- **This board runs below production spec:** 2.8 GHz with boost off (production: 3.2 GHz all-core,
  3.5 GHz max), and memory bandwidth and latency also fall short of spec. Expect production parts
  to be faster.

## 1. The machine

| Item | Value | Source |
|---|---|---|
| Product | Arm "Phoenix" = Arm AGI CPU; board "Phoenix Reference Server", AGI-CPU-CRB-v0.7.2 | DMI, kernel tag `arm-agi`, Arm product page |
| Cores | 128 × Neoverse V3, 1 thread per core (MIDR part 0xD83, which Linux names "V3AE") | `/proc/cpuinfo` |
| Clock | 2.8 GHz max, boost disabled; holds 2.76–2.79 GHz on all 128 cores | perf counters |
| Caches | 64 KB L1I + 64 KB L1D + 2 MB L2 per core; 128 MB L3 (~64 MB per chiplet) | sysfs, measured |
| Topology | 2 chiplets: cores 0–63 and 64–127, joined by UCIe, one CMN S3 mesh each; OS sees 1 NUMA node | core-to-core test, ACPI, Arm test kit |
| Memory | 12 × 32 GB DDR5 RDIMM (377 GB usable); speed unknown (needs root) | EDAC |
| Vector | 128-bit SVE2/NEON (2 pipes); int8/bf16 matrix instructions; no SME | CPU ID registers |
| I/O | 17 PCIe root ports; 2 NVMe, Broadcom BCM57508 200GbE (2 ports), BMC, USB | `lspci` |
| Software | Ubuntu 24.04.5, kernel 7.1.3-arm-agi-20260916-v0.7.2, firmware v0.7.2 | `uname`, DMI |

## 2. Single-core performance

Same gcc 13.3 binaries everywhere; x86 runs on idle cores with idle SMT siblings.

| Core | Clock | CoreMark | per MHz | 7-Zip MIPS | per MHz | Python vs Phoenix |
|---|---|---|---|---|---|---|
| **Phoenix** | 2.80 GHz | 25,584 | 9.1 | 8,363 | 3.0 | baseline |
| GNR typical core | 2.68 GHz | 22,600 | 8.4 | 5,411 | 2.0 | Phoenix 1.21× faster |
| GNR favored core (4 per box) | 4.37 GHz | 36,800 | 8.4 | 7,870–8,393 | 1.8–1.9 | GNR 1.33× faster |
| Genoa 9654 | 3.69 GHz | 32,200 | 8.7 | 6,300 | 1.7 | Phoenix 1.04× faster |
| Apple M1 P-core (published) | 3.2 GHz | – | – | 7,920 | 2.5 | – |
| Cortex-A53 (published) | 1.5 GHz | – | – | ~1,190 | 0.8 | – |

- Python: 16 pyperformance benchmarks, identical CPython 3.12.11 build on every machine, geometric mean.
- On serving-style Python the lead over a typical GNR core grows: asyncio 1.59×, JSON parsing 1.45×,
  BPE tokenizer 1.35×.

## 3. All-core throughput (Phoenix)

| Test | Result | Per-thread efficiency vs single-core |
|---|---|---|
| CoreMark, 128 threads | 3.22 M iterations/s | 98% |
| 7-Zip, 128 threads | 893,454 MIPS | 83% |

- Rough estimate, not measured (the x86 boxes were busy): about one 2-socket GNR 6962P box of
  integer throughput, and 0.6–0.75× a 2-socket Genoa 9654 box.

## 4. Caches, latency and topology

Pointer-chase latency, 2 MB pages, non-repeating chase:

| Level | Phoenix | GNR (this test) | GNR (earlier notes, 1 GB pages) | Genoa |
|---|---|---|---|---|
| L1 | 1.4 ns (4 cycles) | 1.2–1.9 ns | 1.1 ns | 1.1 ns |
| L2 | 3.6–3.9 ns (10–11 cycles) | 3.7–6.0 ns | 3.7 ns | 3.6–3.8 ns |
| L3, own domain | **25–31 ns** (8–16 MB set); 35–49 ns (32–64 MB) | 48–66 ns | 39 ns (local SNC) | ~13 ns (published; not measured) |
| L3, other domain | 81–88 ns (other chiplet) | – | 61–88 ns (other SNC) | – |
| DRAM | ~144 ns | 129–144 ns | 113 ns (local SNC) | not measured |
| Core-to-core, same / other domain | 292 / 402 ns | 188–256 / 323–331 ns (cross-socket) | – | – |

- L3 data stays in the chiplet that last cached it: 33 ns when the same chiplet cached it, 81–88 ns
  when the other chiplet did.
- A repeated pointer chase over 8–32 MB ran at ~5.5 ns: the core learns and replays repeated miss
  sequences. Good for repetitive access patterns; benchmark latency with non-repeating patterns.
- The core-to-core ping-pong reads high on every machine; compare it across machines only.

## 5. Memory bandwidth

| Single core | Phoenix | GNR core |
|---|---|---|
| STREAM Copy / Triad | 44 / 37 GB/s | 21–23 / 15–17 GB/s |

All-core, threads spread across the chip:

| Threads | 16 | 32 | 48 | 64 | 96 | 128 |
|---|---|---|---|---|---|---|
| STREAM Triad, GB/s | 442 | 521 | 511 | 268 | 263 | 175 |
| Read-only, GB/s | 354 | 506 | 519 | 537 | 499 | 314 |
| Write-only, GB/s | 551 | 474 | 320 | 270 | 297 | 156 |

- Peak ~540 GB/s (reads); the published spec is ~845 GB/s with DDR5-8800.
- 16 adjacent cores top out at 150–172 GB/s (≈10 GB/s per core, versus 28 GB/s for a lone core).
  The same 16 threads spread across the chip reach ~350 GB/s. One chiplet alone reads ~358 GB/s.
- Bandwidth collapses with 64+ streaming threads, worst for writes. Reproducible; raise with Arm.

## 6. Loaded latency ("canary" tests)

N cores stream memory (read, or read+write copy) while separate "canary" cores measure L2 (1 MB),
L3 (16 MB) and DRAM (1 GB) latency over the same window.

| Canary | Load in the same chiplet | Load in the other chiplet |
|---|---|---|
| L2 | unaffected (3.7–3.8 ns) | unaffected |
| L3 (idle 26–31 ns) | 1 streaming core: 88–92 ns; 16 cores: 32–101 ns (varies run to run); whole chiplet: 113 ns | 30–35 ns |
| DRAM (idle 146 ns) | 16 cores (150 GB/s): 222 ns; whole chiplet (358 GB/s): 305 ns | 153–170 ns |

DRAM canary versus read load (generators packed from core 0 upward):

| Streaming cores | Read GB/s | Canary, same chiplet | Canary, other chiplet |
|---|---|---|---|
| 0 | 0 | 146 ns | 146 ns |
| 8 | 124 | 181 ns | 152 ns |
| 16 | 150 | 222 ns | 153 ns |
| 61 (all of chiplet 0) | 358 | 305 ns | 170 ns |
| 77 (+16 on chiplet 1) | 486 | 336 ns | 217 ns |
| 122 (whole chip) | 350 (dropping) | 187 ns | 187 ns |

- Where a core sits inside a chiplet doesn't matter; which chiplet it's in does.
- Non-temporal loads (`LDNP`) don't stop the L3 pollution.
- Copy (write) load hurts the other chiplet more: 227 ns there, versus 170 ns for read load.
  Copy bandwidth peaks at 451 GB/s (77 cores), then collapses to 149 GB/s (122 cores).
- Unlike GNR, there's no uncore warm-up effect: idle L3 latency is already low.

## 7. Branch-heavy code

ns per branch, lower is better:

| Test | Phoenix 2.8 GHz | GNR typical 2.68 GHz | GNR favored 4.37 GHz | Genoa 3.69 GHz |
|---|---|---|---|---|
| Predictable branch | 0.51 | 0.56 | 0.34 | 0.40 |
| Random 50/50 branch | **3.24** | 6.31 | 3.94 | 3.75 |
| Repeating pattern, 16K branches | **0.97** | 5.73 | 3.52 | 0.81 |
| Repeating pattern, 64K branches | 2.98 | 6.12 | 3.76 | 2.85 |
| Interpreter dispatch, 16 random targets | 6.79 | 10.53 | 6.45 | 6.50 |
| Interpreter dispatch, 1,024-step repeat | 1.14 | 0.95 | 0.59 | 3.83 |

- A mispredict costs Phoenix ~21 cycles, versus ~31 on GNR.
- Phoenix mispredicts only 36.7% of truly random 50/50 branches, from the first pass; GNR misses
  the expected 50.0%. The mechanism is unknown.
- Pattern memory: Phoenix learns repeating patterns up to ~16K branches, GNR ~4K, Genoa ~32K.
- Interpreter dispatch: Phoenix predicts sequences up to 4,096 steps with no mispredicts, slowing
  only modestly. GNR is faster up to ~1,024 steps, then mispredicts 42–75% at 2,048–4,096 steps.
  Crossover is ~2K steps.
- Real code, share of branches mispredicted (Phoenix / typical GNR core): Python JSON 0.04% / 0.26%,
  tokenizer 0.56% / 0.71%, richards 0.30% / 0.34%, CoreMark 0.12% / 0.28%, 7-Zip 5.8% / 6.1%.

## 8. Vector, matrix and offload hardware

| | Phoenix | GNR 6962P | Genoa 9654 |
|---|---|---|---|
| Widest vector | 128-bit NEON/SVE2 (2 pipes) | 512-bit AVX-512 | AVX-512 on a 256-bit datapath |
| Matrix engine | none (no SME) | AMX in every core | none |
| Matrix instructions | int8/bf16 inside NEON/SVE2 | AMX, AVX-512 VNNI/BF16 | AVX-512 VNNI/BF16 |
| DMA / offload engines | none | DSA, IAA, QAT, DLB | none |

- No DMA engine anywhere: firmware device list, kernel drivers, PCIe, memory map, Arm's test kit,
  the vendor docs in `phoenix/`, Arm's product page and Hot Chips coverage. Arm's own
  cross-chiplet tests move data with CPU copies.
- For `asimovsw-docs/docs/host_comms.md`: drop M06 "Phoenix SoC DMA". Use Asimov-side DMA
  (M04 controller DMA, M05 DMA-357) for bulk moves and CPU copies (M01) for small ones.
- Worth testing: LS64 (64-byte single-shot stores to device memory, Arm's equivalent of Intel's
  `MOVDIR64B`) for submitting commands to Asimov in one PCIe write.

## 9. This board versus production spec

| | Production (public spec) | This CRB |
|---|---|---|
| Clock (128-core part) | 3.2 GHz all-core, 3.5 GHz max | 2.8 GHz, boost disabled |
| Memory | 12 × DDR5-8800 (1 DIMM per channel), ~845 GB/s | DIMM speed unknown; ~540 GB/s measured |
| DRAM latency | "sub-100 ns" | ~144 ns |
| NUMA modes | NUMA1 and NUMA2 (per chiplet) | NUMA1 |
| Memory QoS | MPAM | not tested |

- For production clocks, scale CPU results by ~1.14× (all-core) to ~1.25× (single-core).

## 10. Recommendations

1. Put latency-critical orchestration (Asimov polling, schedulers) on one chiplet and
   bandwidth-heavy work (bulk copies, data prep) on the other.
2. Spread bandwidth-heavy threads across a chiplet; don't pack them on adjacent cores.
3. Don't let all 128 cores stream memory at once.
4. Do bulk Phoenix↔Asimov transfers with Asimov-side DMA.
5. Re-run the key tests once firmware, clocks, DIMM speed and NUMA2 mode are production-like.

## 11. Questions for the Arm FAE

1. Is the bandwidth collapse at high thread counts (especially writes) expected? Is there a firmware or QoS fix?
2. How do we enable NUMA2 (per-chiplet) mode, and what is local DRAM latency in it?
3. What speed are the CRB's DIMMs running at, and why is the CPU limited to 2.8 GHz with boost off?
4. Please confirm there's no DMA engine Linux can use (e.g. DMA-350 or SDXI).
5. Can MPAM partition the L3 so a streaming core can't evict other threads' data? Is Linux resctrl support available?
6. What lets the core mispredict fewer than 50% of truly random branches?
7. The MIDR reports part 0xD83 (Linux: Neoverse V3AE) while the docs say Neoverse V3. Which is it?

## 12. Method and caveats

- Same compiler (gcc 13.3) and binaries on all machines. Phoenix code is tuned with
  `-mcpu=neoverse-v2`, because gcc has no V3 target.
- x86 comparisons are single-core, on idle cores with idle SMT siblings (verified). The first GNR
  runs had busy siblings and were discarded.
- No all-core tests on delphi (Quartus jobs) or andoria (rinzler), so x86 all-core figures are estimates.
- Genoa shared its L3 with rinzler: its 7-Zip compression score is understated, and its L3 and
  DRAM latency weren't measured.
- sw-dev-01 (Zen 5 VM) was excluded because it was oversubscribed.
- Apple M1 and Cortex-A53 figures come from 7-cpu.com and older 7-Zip versions: treat as ±15%.
- Pre-release firmware (v0.7.2) and no root access: DIMM speed, ACPI tables and interconnect
  counters weren't read.

## 13. Files

| What | Where |
|---|---|
| Benchmark kit: scripts, sources, x86 binaries | `/home/bill/crb/bench/` |
| Results | `/home/bill/crb/bench/results/` |
| Board copy: ARM binaries, raw results | `arm@192.168.2.46:/home/arm/bill/bench/` |
| Vendor docs (NDA) | `/home/bill/crb/phoenix/` |

- Main scripts: `build.sh`, `run_1t.sh`, `run_mt.sh`, `canary_runs.sh` (with `canary_table.py`),
  `branch_perf.sh`, `onepass.sh`, `ind_sweep.sh`, `branch_workloads.sh`, `idlecpus.sh`, `sibrun.sh`.
- `results/gnr-1t-cpu108-favored`, `results/gnr-1t-cpu130` and `results/gnr-cpu130-py.json` were
  contaminated by busy SMT siblings. Use `gnr-verify-*`, `gnr-rerun-*` and `gnr-cpu140-py.json` instead.

Sources: [Arm AGI CPU product page](https://www.arm.com/products/cloud-datacenter/arm-agi-cpu),
[ServeTheHome: Arm's AGI CPU at Hot Chips 2026](https://www.servethehome.com/arms-agi-data-center-cpu-at-hot-chips-2026/),
7-cpu.com ([Cortex-A53](https://www.7-cpu.com/cpu/Cortex-A53.html), [Apple M1](https://www.7-cpu.com/cpu/Apple_M1.html)).
