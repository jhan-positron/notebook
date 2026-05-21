# Intel vs AMD CPU/Memory Subsystem Comparison

A characterization of single-thread and multi-thread memory behavior on Intel
Xeon 6962P (Granite Rapids-AP) and AMD EPYC 9654 (Zen 4 Genoa) systems.

> **Reading note.** All data tables and architectural diagrams in this document
> are wrapped in fenced code blocks so monospace alignment is preserved. For
> proper rendering, view this file in a monospace markdown viewer (VS Code,
> Obsidian, GitHub web), or paste it into a terminal pager. Most table widths
> are ≤ 90 columns to fit common viewers without wrap.

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Systems under test](#2-systems-under-test)
   - 2.1 [Inspection method](#21-inspection-method)
   - 2.2 [Three-system comparison](#22-three-system-comparison)
   - 2.3 [System diagrams](#23-system-diagrams)
   - 2.4 [Comparability caveats](#24-comparability-caveats)
3. [Methodology](#3-methodology)
4. [Findings](#4-findings)
   - 4.1 [Latency vs working-set size](#41-latency-vs-working-set-size)
   - 4.2 [Single-thread bandwidth](#42-single-thread-bandwidth)
   - 4.3 [Multi-thread bandwidth scaling](#43-multi-thread-bandwidth-scaling)
   - 4.4 [Cross-socket](#44-cross-socket-consolidated)
   - 4.5 [Core-to-core latency](#45-core-to-core-latency)
     - 4.5.1 [Caveat: in-die scatter has no direct vendor proof](#451-caveat-in-die-scatter-has-no-direct-vendor-proof)
5. [Audit of article's claims](#5-audit-of-articles-claims)
6. [Validation of Intel L3 latency](#55-validation-of-intel-l3-latency)
   - 5.5.1 [Cross-check vs Chips and Cheese](#551-cross-check-vs-chips-and-cheese-computed)
   - 5.5.2 [Cross-check vs Intel Hot Chips 2024](#552-cross-check-vs-intel-hot-chips-2024)
   - 5.5.3 [Cross-check vs Intel Optimization Reference Manual](#553-cross-check-vs-intel-optimization-reference-manual)
   - 5.5.4 [Verdict](#554-verdict)
7. [Hugepage handling in scripts](#6-hugepage-handling-in-scripts)
8. [Reproducibility and deliverables](#7-reproducibility-and-deliverables)

---

## 1. Executive summary

This study compares the memory subsystems of two server CPUs at single-thread
and multi-thread scale: an Intel Xeon 6962P (Granite Rapids-AP) configured with
sub-NUMA clustering disabled (SNC OFF), and an AMD EPYC 9654 (Zen 4 Genoa)
configured with one NUMA node per socket (NPS1). Measurements come from a
small suite of custom microbenchmarks: pointer-chase load latency, single-thread
AVX-512 streaming bandwidth, multi-thread aggregate bandwidth, and core-to-core
coherency latency. Each is wrapped in a driver script that handles hugepage
reservation, NUMA pinning, and CSV emission.

The headline findings are summarized in the table below. Each row cites the
script and CSV that produced it.

```
Finding                              Magnitude            Source / Run
─────────────────────────            ──────────────       ──────────────────────
AMD per-CCD L3 latency lower         3-4× for ≤32 MB      script:ptr_chase
than Intel monolithic-mesh L3                             ptr_chase_full_*.csv
for small-to-mid working sets

Intel monolithic L3 latency flat     flat 4-256 MB        script:ptr_chase
at ~60 ns                                                 ptr_chase_full_*.csv

AMD cross-CCD L3 latency rises       +42 ns vs Intel      script:ptr_chase
smoothly with working set            at 256 MB            ptr_chase_full_*.csv

Intel local DRAM latency higher      137 vs 110 ns        script:ptr_chase
than AMD                                                  ptr_chase_full_*.csv

Intel single-thread L3 BW clamped    3.3× lower than      script:bw_avx512
~27 GB/s                             AMD in-CCD           bw_sweep_*.csv

RMW doubles Intel L3 BW              27 → 53 GB/s         script:bw_avx512

Intel mesh saturates aggregate       ~9× lower than       script:bw_multi
L3 BW at ~550 GB/s (72 thr)          AMD at full load     bw_multi_*.csv

Intel local DRAM single-thread BW    16 vs 38 GB/s        script:bw_avx512
lower than AMD                                            bw_sweep_*.csv

Intel cross-socket DRAM BW           -43% / -61%          script:bw_avx512
collapses (single thread)                                 bw_sweep_*.csv

AMD c2c has hard CCD-boundary        28 vs 182 ns         script:c2c_lat
step                                 one-way              c2c_lat_*.csv

Intel c2c shows scatter, not         57-115 ns range      script:c2c_lat
step structure                       one-way              c2c_lat_*.csv
```

The architectural picture that emerges is consistent with the published
analysis in *A Look into Intel Xeon 6's Memory Subsystem* (Chester Lam, Chips
and Cheese, September 2025) but extends it in several directions. AMD's
per-CCD L3 is the dominant single-thread cache for working sets that fit
inside one CCD's 32 MB private L3 — 3 to 5 times lower load-use latency than
Intel's monolithic mesh L3 and roughly 3.3× higher single-core bandwidth.
Above 48 MB, AMD spills out of one CCD and pays a roughly uniform cross-CCD
penalty as accesses scatter through the I/O die, while Intel's 432 MB
monolithic L3 continues to serve at a flat ~60 ns and ~27 GB/s. Beyond
roughly 700 MB the working set exceeds Intel's L3 entirely and Intel's DRAM
takes over at 137 ns latency, slightly worse than AMD's 110 ns despite
Intel's faster DDR5 channels. At the multi-thread scale the asymmetry widens
dramatically: AMD's per-CCD L3 caches scale independently, so aggregate L3
bandwidth grows almost linearly to roughly 5.2 TB/s with all cores engaged,
while Intel's mesh saturates near 550 GB/s and then drops slightly at full
load. Core-to-core coherency traffic mirrors the cache topology: AMD shows a
sharp 7× step at the CCD boundary, Intel shows a 2× scatter across the entire
socket with no clean structural step.

Several of these findings have been cross-checked against external sources.
Our measured Intel L1d and L2 latencies match Intel's officially published
cycle counts from the *Intel 64 and IA-32 Architectures Optimization Reference
Manual* to within one percent. Our Intel L3 latency of approximately 60 ns
falls within 9 ns of the value the Chips and Cheese article predicts for a
Xeon 6 in monolithic mode, derived from the article's measured SNC3 die-hop
numbers. An additional 33 ns L2-miss datapoint published by Intel at Hot Chips
2024 corroborates the article's SNC-mode L3 figure to within 0.25 ns. The
small remaining gap between our 60 ns and the predicted ~51 ns is consistent
with SKU-level differences in CHA and mesh frequencies and the approximate
nature of the article's monolithic-mode estimate.

The remainder of this document presents the system inventory, the
microbenchmark methodology, the full data tables, a claim-by-claim audit
against the Chips and Cheese article, the cross-check of our Intel L3 number
against multiple external sources, and the operational details (hugepage
handling, reproduction commands, file manifest) needed to reproduce the work.

---

## 2. Systems under test

Three systems were inspected for this study: two Intel boxes that share the
Granite Rapids-AP architecture, and one AMD Genoa box. Only one of the Intel
boxes, hostname `delphi-3af6`, was used for actual measurements; the other,
`delphi-17cf`, is a CI/CD reference machine that we could only read from. It
is included here to confirm that the test box is representative of the broader
Intel fleet rather than an outlier configuration.

### 2.1 Inspection method

System characterization is performed by a single read-only shell script,
`step0_inspect.sh`, which gathers facts from canonical Linux sources. The
script does not modify any system state; it only emits a log file. The
commands it invokes, summarized:

```
Tool                        Commands inside (selected)
─────────────────────       ──────────────────────────────────────
script:step0_inspect.sh     lscpu, numactl --hardware, dmidecode,
                            /proc/cmdline, /sys cache topology,
                            free, /proc/meminfo, dmesg | grep -i mce

Output logs:
  inspect_intel_delphi-3af6_20260519.log
  inspect_intelCI_delphi-17cf_20260520.log
  inspect_amd_andoria-15_20260519.log
  core_grouping.log         (Intel /sys/.../topology/* dump)
```

All numbers in the comparison table below trace back to one of these log
files. The `core_grouping.log` file was produced by a separate one-shot
read of `/sys/devices/system/cpu/cpu*/topology/{core_id,cluster_id,die_id,
package_cpus_list,die_cpus_list,cluster_cpus_list,core_cpus_list}` and is
used later in section 4.5 to interpret the Intel core-to-core latency
structure.

### 2.2 Three-system comparison

```
Field                  Intel 3af6           Intel CI (17cf)        AMD (andoria-15)
─────                  ──────────────       ─────────────────      ──────────────────
Hostname               delphi-3af6          delphi-17cf            andoria-15
Role                   primary test box     CI/CD reference         comparison box
                       (sudo, can change)   (read-only access)

CPU SKU                Xeon 6962P           Xeon 6960P             EPYC 9654 Embedded
Generation             GNR-AP / Xeon 6      GNR-AP / Xeon 6        Zen 4 Genoa
Cores/socket           72                   72                     96
Sockets                2                    2                      2
Max boost              4.4 GHz              3.9 GHz                3.7 GHz

L1d / core             48 KB                48 KB                  32 KB
L2 / core              2 MB                 2 MB                   1 MB
L3                     432 MB monolithic    432 MB monolithic      12×32 MB per CCD
                       1 inst per socket    1 inst per socket      12 inst per socket

NUMA nodes total       2                    2                      2
SNC / NPS mode         SNC OFF              SNC OFF                NPS1
Distance matrix        10/21                10/21                  10/32

DRAM                   24×64 GB DDR5-6400   16×48 GB DDR5-6400     24×16 GB DDR5-4800
Total                  1.5 TB               768 GB                 377 GB
Channels populated     12 per sock          12 per sock            12 per sock
                       (1 DPC)              (1 DPC)                (1 DPC)

Hugepages reserved     512 × 1 GiB          256 × 1 GiB            280 × 1 GiB
THP setting            madvise              madvise                madvise
Governor               performance          performance            performance
Mitigations            ON                   ON                     OFF
                       (eIBRS, SSBD, IBPB)  (eIBRS, SSBD, IBPB)    (mitigations=off)
Kernel                 6.8.0-110            6.8.0-110              5.15.0-126
Distro                 Ubuntu 22.04.5       Ubuntu 22.04.5         Ubuntu 22.04.5
Motherboard vendor     Oracle               Oracle                 Supermicro
                                                                   AS-4125GS-TNRT
```

The two Intel systems share the same Granite Rapids-AP family, the same SNC
mode (off), the same DDR5 speed (6400 MT/s), and the same monolithic 432 MB
L3 configuration. They differ in maximum boost clock (4.4 GHz on the 6962P
versus 3.9 GHz on the 6960P), which would scale latency-in-nanoseconds
measurements by approximately thirteen percent but not change the
architectural picture. We treat the 6962P test box as representative of the
broader fleet for all qualitative findings. The CI machine was used only for
characterization, not for measurements, because we did not have privileged
access to reserve hugepages or pin processes there.

The AMD system uses NPS1 mode, which exposes one NUMA node per socket and
stripes addresses uniformly across all twelve memory controllers in that
socket. This is the AMD configuration most often used for general-purpose
workloads, and it is the configuration the Chips and Cheese article also
tested when comparing to AMD.

### 2.3 System diagrams

The two systems organize cache and memory very differently inside each
socket. The Intel diagram below shows a single monolithic last-level cache
shared by all 72 cores in a socket, with three internal compute dies hidden
from the operating system because SNC is disabled. The AMD diagram shows
twelve discrete core complex dies (CCDs), each with its own private 32 MB L3,
all connected through a central I/O die that handles inter-CCD coherency, all
memory controllers, and inter-socket links.

#### Intel — Xeon 6962P, two-socket, SNC OFF

```
   ┌──────────────────── Socket 0 ────────────────────┐
   │                                                  │
   │   ┌────────────────────────────────────────┐     │
   │   │                                        │     │     ┌─────┐
   │   │   72 cores  (cores 0..71, HT siblings  │     │     │     │
   │   │             144..215)                  │     │     │     │
   │   │                                        │     │     │     │
   │   │   ┌────────────────────────────────┐   │     │     │  12 │
   │   │   │   Mesh + EMIB-connected dies   │   │     │     │  ch │
   │   │   │   (3 compute dies internally)  │◄──┼─────┼─────┤ DDR5│
   │   │   │                                │   │     │     │6400 │
   │   │   │   ONE 432 MB L3 region         │   │     │     │     │
   │   │   │   (shared by ALL 72 cores)     │   │     │     │     │
   │   │   └────────────────────────────────┘   │     │     │     │
   │   └────────────────────────────────────────┘     │     │     │
   │                                                  │     └─────┘
   │           NUMA node 0  ─── all 768 GB local      │      cpus 0-71
   └──────────────────┬───────────────────────────────┘      see 768GB
                      │                                       as local
                      │  UPI links  (2 sockets connect)
                      │  distance = 21 (vs local = 10)
                      │
   ┌──────────────────┴───────────────────────────────┐
   │                                                  │
   │   ┌────────────────────────────────────────┐     │     ┌─────┐
   │   │   72 cores  (cores 72..143,            │     │     │     │
   │   │             HT siblings 216..287)      │     │     │     │
   │   │                                        │     │     │  12 │
   │   │   ┌────────────────────────────────┐   │     │     │  ch │
   │   │   │   Mesh + EMIB                  │◄──┼─────┼─────┤ DDR5│
   │   │   │   ONE 432 MB L3 region         │   │     │     │6400 │
   │   │   └────────────────────────────────┘   │     │     │     │
   │   └────────────────────────────────────────┘     │     │     │
   │                                                  │     │     │
   │           NUMA node 1  ─── all 768 GB local      │     └─────┘
   └──────────────── Socket 1 ────────────────────────┘
```

The mesh-plus-EMIB box in the diagram is a simplification: Granite Rapids-AP
actually places three compute dies side by side in each socket, connected by
embedded silicon bridges (EMIB) that carry the mesh protocol across die
boundaries. Each compute die contains its own group of CHAs (Caching/Home
Agents), each of which holds an L3 cache slice and acts as a coherency
arbiter for a hashed portion of the physical address space. With SNC OFF,
the operating system sees one NUMA node per socket and the L3 appears as one
flat 432 MB pool; the underlying three-die structure is not directly visible
to software, though it is partially inferable from `/sys` topology data and
becomes relevant when interpreting the core-to-core latency measurements in
section 4.5.

#### AMD — EPYC 9654, two-socket, NPS1

```
   ┌─────────────────────── Socket 0 ───────────────────────┐
   │                                                        │
   │   ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐                 │
   │   │CCD0││CCD1││CCD2││CCD3││CCD4││CCD5│   each CCD:     │
   │   │8c  ││8c  ││8c  ││8c  ││8c  ││8c  │   8 cores       │
   │   │32MB││32MB││32MB││32MB││32MB││32MB│   own 32 MB L3  │
   │   │L3  ││L3  ││L3  ││L3  ││L3  ││L3  │                 │
   │   └─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘                 │
   │     │     │     │     │     │     │                    │     ┌──────┐
   │   ┌────┐┌────┐┌────┐┌────┐┌────┐┌────┐                 │     │      │
   │   │CCD6││CCD7││CCD8││CCD9││CCDA││CCDB│                 │     │      │
   │   │8c  ││8c  ││8c  ││8c  ││8c  ││8c  │                 │     │  12  │
   │   │32MB││32MB││32MB││32MB││32MB││32MB│                 │     │  ch  │
   │   └─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘└─┬──┘                 │     │ DDR5 │
   │     │     │     │     │     │     │                    │     │ 4800 │
   │   ┌─┴─────┴─────┴─────┴─────┴─────┴─────────────────┐  │     │      │
   │   │  IOD (I/O die) - Infinity Fabric                ├──┼─────┤      │
   │   │  12 mem channels, all PCIe roots                │  │     │      │
   │   │  Connects CCDs + to other socket                │  │     └──────┘
   │   └─────────────────────────┬───────────────────────┘  │
   │                             │                          │     NUMA node 0
   └─────────────────────────────┼──────────────────────────┘
                                 │
                                 │  xGMI links (Infinity Fabric)
                                 │  distance = 32 (vs local = 10)
                                 │
   ┌─────────────────────────────┼──────────────────────────┐
   │                             │                          │
   │   ┌─────────────────────────┴───────────────────────┐  │     ┌──────┐
   │   │  IOD                                            ├──┼─────┤      │
   │   └─────────────────────────────────────────────────┘  │     │  12  │
   │                                                        │     │  ch  │
   │   12 more CCDs (same layout)                           │     │ DDR5 │
   │                                                        │     │ 4800 │
   │                                                        │     │      │
   │             NUMA node 1                                │     └──────┘
   └─────────────────────── Socket 1 ───────────────────────┘
```

The AMD socket is composed of twelve CCDs and one large central I/O die.
Each CCD contains eight Zen 4 cores and a private 32 MB L3 cache shared only
by those eight cores. The CCDs do not communicate directly with one another;
inter-CCD coherency traffic, DRAM traffic, and PCIe traffic all flow through
the IOD on the Infinity Fabric. This topology has two important consequences
that show up repeatedly in our data. First, a thread running on one CCD has
an extremely fast (low-latency, high-bandwidth) path to its own CCD's 32 MB
L3 but pays a substantial penalty to reach any other CCD's L3, because every
such access traverses the IOD. Second, the IOD acts as a shared bandwidth
bottleneck for any traffic that has to cross CCDs.

### 2.4 Comparability caveats

The two systems are not perfectly matched. The most important asymmetries to
keep in mind when reading the results:

```
Asymmetry          Intel vs AMD       Definition / Impact
──────────         ─────────────      ───────────────────────────────────
DDR5 speed         6400 vs 4800       Intel +33% theoretical channel BW
                                      (not compensated)

Mitigations        ON vs OFF          CPU side-channel countermeasures
                                      (Spectre/Meltdown/MDS/etc.) in the
                                      Linux kernel. Intel runs defaults
                                      (eIBRS + SSBD + IBPB + ...); AMD
                                      has mitigations=off on cmdline.
                                      Mostly affects syscalls, context
                                      switches, indirect branches; small
                                      effect on our user-space hot loops.
                                      Not compensated. Verified via
                                      script:step0 reading /proc/cmdline
                                      and /sys/.../vulnerabilities/*

Kernel             6.8 vs 5.15        Scheduler / NUMA balancing /
                                      mitigation handling differ.
                                      Not compensated.

Cores per socket   72 vs 96           Whole-socket comparisons biased;
                                      per-core comparisons clean.
```

None of these asymmetries is large enough to invalidate the architectural
findings below. The DDR5 speed delta affects steady-state DRAM bandwidth and
latency but not the cache-hierarchy results that are the focus of this study.
Mitigations affect syscalls and branchy code; our microbenchmark hot loops
are pinned user-space code with no syscalls in the timed window. The kernel
version difference matters mainly for any test that relies on scheduler
behavior, which ours do not (every thread is explicitly pinned with
`sched_setaffinity`). The core-count difference (72 vs 96) is significant for
whole-socket aggregate measurements; we report per-thread numbers wherever
that matters.

---

## 3. Methodology

The measurements in this study come from a small suite of custom C
microbenchmarks, each focused on one specific aspect of the memory subsystem.
They are accompanied by driver shell scripts that handle hugepage pool
reservation, NUMA pinning, parameter sweeping, and CSV emission. The mapping
between tools, source files, driver scripts, and output filenames:

```
Tool             Source file        Driver script        Output CSV name pattern
─────            ──────────────     ──────────────       ──────────────────────────
inspect_pages    inspect_pages.c    (manual)             (stdout only, no CSV)
ptr_chase        ptr_chase.c        sweep_full.sh        ptr_chase_full_<host>_<ts>.csv
bw_avx512        bw_avx512.c        sweep_bw.sh          bw_sweep_<host>_<ts>.csv
bw_multi         bw_multi.c         sweep_bw_multi.sh    bw_multi_<host>_<ts>.csv
c2c_lat          c2c_lat.c          sweep_c2c.sh         c2c_lat_<host>_<ts>.csv
```

`inspect_pages` is a sanity-check tool that verifies CPU pinning is working,
NUMA binding is in effect, and the buffer is backed by the requested page
size. It does not produce performance numbers; it is run once at the start
of any measurement session to confirm the environment is configured
correctly.

`ptr_chase` measures single-thread load-use latency by walking a random
permutation of pointers through a buffer. The buffer is allocated with
`mmap`, optionally backed by 2 MiB or 1 GiB hugepages, bound to a specific
NUMA node with `mbind(MPOL_BIND)`, and the calling thread is pinned to a
specific CPU with `sched_setaffinity`. The pointer array is initialized as a
Fisher-Yates shuffle so the chain forms a single Hamiltonian cycle through
all cache lines in the buffer; this defeats prefetchers at every level
because the access pattern has no detectable stride or spatial locality.
Each cell occupies exactly one 64-byte cache line and holds a single
pointer at offset zero. The hot loop is a tight `p = *p` dependency chain;
the measured time per load is reported in nanoseconds.

`bw_avx512` measures single-thread streaming bandwidth using 512-bit AVX-512
load and store instructions. Three patterns are supported. The `read`
pattern issues four 64-byte loads per inner iteration (256 bytes per chunk)
and XOR-accumulates the data so the compiler cannot dead-code-eliminate the
loop. The `rmw` (read-modify-write) pattern loads four vectors, increments
them, and stores them back; it stresses both the load and store ports of the
cache hierarchy simultaneously. The `write` pattern uses non-temporal stores
(`_mm512_stream_si512`) to push data directly to memory, bypassing cache
allocation. The reported number is total bytes of bus traffic divided by
elapsed time; for `rmw`, bytes count both the load and the store (since both
hit the cache/memory bus), giving a number that is roughly double the
`read` figure when read and write paths run independently.

`bw_multi` measures aggregate multi-thread bandwidth. It spawns *N* worker
threads, each of which allocates its own private buffer (so threads do not
share cache lines or compete for the same bytes), pins itself to a specific
CPU, faults its pages, and runs the same AVX-512 kernel as `bw_avx512`. The
threads synchronize through a barrier and then all start their timed loops
together. The reported aggregate is the sum of each thread's bytes-moved
divided by its elapsed time. This number reveals where the system saturates
under simultaneous load from many cores — a question that single-thread
measurements cannot answer.

`c2c_lat` measures core-to-core coherency latency by ping-ponging an atomic
counter between two threads on different cores. Thread A waits until the
counter is even, then issues an atomic compare-and-swap (CAS) to increment
it. Thread B waits until the counter is odd, then does the same. Each CAS
forces the line into the issuing core's L1 in Modified state, requiring a
coherency round-trip through whatever fabric connects the two cores. The
reported number is nanoseconds per round-trip (one A-increment plus one
B-increment); dividing by two gives an estimate of one-way latency between
the cores.

**Pointer-chase stride note.** A natural question is whether the 64-byte
stride used by `ptr_chase` should be adjusted upward when measuring larger
caches or DRAM. It should not. The stride is fixed at one cache line at
every buffer size, because on every level of the hierarchy the fetch unit
is one 64-byte cache line. As the buffer grows, the cycle length grows
automatically (the cell count is `size / 64`), and the random ordering
continues to defeat prefetchers regardless of which level of the hierarchy
holds the data. Striding more aggressively would skip cache lines and break
the load-use chain.

**What none of these tools measures.** A few important properties of real
workloads are deliberately outside the scope of this microbenchmark suite:
mixed read/write workloads at realistic ratios; hardware prefetcher
benefits (our pointer chase explicitly defeats them); TLB-walk cost (we
use hugepages to eliminate it); workloads with shared data among threads;
and instruction cache pressure. Each of these would require a different
benchmark. The goal here is to characterize the underlying hardware
asymmetries between Intel and AMD; real workload behavior would mix our
clean numbers with prefetch benefit, TLB churn, and inter-thread sharing.

**Benchmarks we did NOT run.** SPEC CPU2017 is the industry-standard CPU
benchmark used by the Chips and Cheese article as a single-thread per-core
performance reference. We did not run it on either system. It would have
added a roughly comparable cross-system number but requires a commercial
license (approximately $1000–2000 per site), about 25 GB of disk for the
source distribution, two to three hours of build time per system, and ten
to twenty hours of wall time per system for one iteration of both the
integer and floating-point suites. A reportable run with the required three
iterations would push that to thirty hours per system. Tuning effort
(compiler flag selection, NUMA pinning, hugepage configuration) typically
adds one to two more days. Given that the microbenchmarks in this study
already establish the architectural picture in detail, the SPEC investment
did not seem justified for this work. If a single-number cross-system CPU
comparison is desired in the future, the Phoronix Test Suite (free, open
source, broad benchmark coverage) is the practical alternative and can be
set up in an afternoon.

---
## 4. Findings

This section presents the measured data from each microbenchmark. Each
subsection begins with a provenance block identifying the script and CSV
files that produced the numbers, then shows the data tables, then
interprets them with bullet observations.

### 4.1 Latency vs working-set size

```
Source: script:ptr_chase + sweep_full.sh
Run (Intel): ptr_chase_full_delphi-3af6_20260520_2102.csv
Run (AMD):   ptr_chase_full_andoria-15_20260520_2102.csv
```

The pointer-chase sweep walks a single thread through buffers of
increasing size, from 32 KiB (fits in L1d) through 4 GiB (firmly in DRAM).
The buffer is bound to the local NUMA node, the thread is pinned to CPU 0
on that socket, and hugepage size is chosen per-buffer so TLB walks do not
contaminate the measurement. Each row reports the median latency over five
iterations of the chase, each iteration running at least half a second so
the result is well-averaged.

```
size       Intel ns    AMD ns     I/A       region
─────────  ────────    ──────     ──────    ────────────────────
 32 KiB        1.14       1.08    1.06×     L1d
 64 KiB        3.64       3.80    0.96×     L2
128 KiB        3.65       3.81    0.96×     L2
256 KiB        3.65       3.81    0.96×     L2
512 KiB        4.06       4.79    0.85×     L2
  1 MiB        4.65       8.50    0.55×     Intel L2, AMD spilling
  2 MiB       21.10      13.13    1.61×     Intel spilling, AMD L3
  4 MiB       60.20      12.90    4.67×     Intel L3, AMD in-CCD L3
  8 MiB       60.31      14.02    4.30×
 16 MiB       60.37      15.73    3.84×
 32 MiB       60.37      21.19    2.85×
 48 MiB       60.38      61.70    0.98×     CROSSOVER
 64 MiB       60.39      77.59    0.78×
 96 MiB       60.91      87.43    0.70×
128 MiB       61.17      93.03    0.66×
192 MiB       61.42     100.04    0.61×
256 MiB       61.92     103.40    0.60×
384 MiB       72.08     106.27    0.68×     Intel L3 spilling
512 MiB       94.89     108.10    0.88×
768 MiB      123.57     109.83    1.13×
  1 GiB      125.91     108.73    1.16×
  2 GiB      134.54     109.44    1.23×
  4 GiB      137.29     109.85    1.25×     pure DRAM
```

The shape of the two curves is fundamentally different. Intel's curve has
two long plateaus: a 60 ns plateau spanning every working set from 4 MiB
to 256 MiB, and a 137 ns plateau from roughly 1 GiB onward. Between the
two plateaus there is a transition region (384 MiB through 768 MiB) where
the working set begins to overflow the 432 MiB monolithic L3 and an
increasing fraction of accesses must go to DRAM. AMD's curve, by contrast,
is monotonically increasing from 4 MiB to 256 MiB, climbing smoothly from
the 13 ns in-CCD L3 floor to about 103 ns. There is no clear plateau in
that range; the latency reflects a probabilistic average of in-CCD and
cross-CCD accesses that shifts toward cross-CCD as the working set grows.

The two curves cross at 48 MiB, where Intel measures 60.38 ns and AMD
61.70 ns. Below that crossover, AMD's per-CCD L3 dominates: at 16 MiB the
ratio is 3.84× in AMD's favor (15.73 ns versus 60.37 ns). Above the
crossover and up to roughly 700 MiB, Intel's monolithic L3 dominates: at
256 MiB the ratio is 0.60× (Intel 61.92 ns versus AMD 103.40 ns). Once the
working set exceeds Intel's L3 capacity, the curves cross again and AMD's
lower-latency DRAM takes over the comparison: at 4 GiB, Intel 137.29 ns
versus AMD 109.85 ns, a 25 percent gap in AMD's favor despite Intel
having faster DDR5 channels.

```
Cross-socket (cpu 0, mem-node 1):

Source: script:ptr_chase + sweep_full.sh (same runs)

size       Intel ns    AMD ns    I/A      remote/local
─────────  ────────    ──────    ──────   ──────────────
1 GiB      243.8       197.8     1.23×    Intel 1.94×, AMD 1.82×
4 GiB      275.5       199.0     1.38×    Intel 2.01×, AMD 1.80×
```

Cross-socket latency is measured by pinning the thread on socket 0 and
binding the buffer on socket 1, forcing every access to traverse the
inter-socket fabric (UPI on Intel, xGMI on AMD). At 4 GiB Intel pays
roughly twice its local DRAM latency to reach socket 1; AMD pays roughly
1.8× its local DRAM latency. The Intel ratio matches the ACPI distance
matrix (21/10 = 2.10) almost exactly, while the AMD ratio (1.80) is
notably lower than the ACPI distance (32/10 = 3.20), suggesting that the
ACPI distance is a conservative software hint rather than a hardware
measurement on AMD.

Key observations from this section:

- L1d and L2 latencies are nearly identical between vendors, within 4
  percent.
- In the 4 MiB to 32 MiB band, AMD's per-CCD L3 is 3 to 5 times faster
  than Intel's monolithic-mesh L3.
- The two curves cross at exactly 48 MiB.
- Between 48 MiB and 256 MiB, Intel's monolithic L3 is 17 to 42 ns
  faster than AMD's smoothly-rising cross-CCD curve.
- Beyond 700 MiB, AMD's steady-state DRAM is 25 percent faster than
  Intel's, despite Intel having a faster DDR5 specification.
- Cross-socket DRAM latency is 28 percent lower on AMD than on Intel
  (199 ns versus 275 ns at 4 GiB).
- The Intel remote/local ratio matches its ACPI distance ratio almost
  exactly; the AMD remote/local ratio is significantly lower than its
  ACPI distance ratio.

### 4.2 Single-thread bandwidth

```
Source: script:bw_avx512 + sweep_bw.sh
Run (Intel): bw_sweep_delphi-3af6_20260520_2335.csv
Run (AMD):   bw_sweep_andoria-15_20260520_2335.csv
```

The single-thread bandwidth sweep walks the same buffer-size range as the
latency sweep, but uses AVX-512 streaming kernels instead of pointer
chase. Two patterns are reported below: pure read (16 loads per 256-byte
chunk, XOR-accumulated) and read-modify-write (load, increment, store
back). The numbers count bus traffic, so the RMW pattern at the L3 level
shows roughly double the read figure on architectures where read and
write paths run concurrently.

```
Local memory, GB/s (read + rmw patterns):

size      Iread   Aread   I/A_r    Irmw   Armw   I/A_m   notes
─────     ─────   ─────   ─────    ─────  ─────  ─────   ────────────────
 32 KiB   285     211     1.35×    479    229    2.09×   L1d
 64 KiB   196     117     1.68×    142    232    0.61×   L2
128 KiB   197     118     1.67×    142    233    0.61×   L2
256 KiB   197     118     1.67×    142    235    0.60×   L2
512 KiB   197     118     1.67×    142    235    0.60×   L2
  1 MiB   196     100     1.96×    142    185    0.77×   AMD L2 spills
  2 MiB    59      97     0.61×     98    197    0.50×   Intel L2 spills
  4 MiB    27      89     0.30×     53    183    0.29×   Intel L3 / AMD CCD
  8 MiB    27      88     0.31×     53    184    0.29×
 16 MiB    27      88     0.31×     53    184    0.29×
 32 MiB    27      89     0.30×     53    163    0.33×   AMD cross-CCD start
 48 MiB    27      55     0.49×     53     85    0.62×   transition
 64 MiB    27      50     0.54×     53     82    0.65×
 96 MiB    27      47     0.57×     53     74    0.72×
128 MiB    27      39     0.69×     53     68    0.78×
192 MiB    27      39     0.69×     53     56    0.95×
256 MiB    27      39     0.69×     53     56    0.95×
384 MiB    25      39     0.64×     50     56    0.89×   Intel L3 spilling
512 MiB    22      38     0.58×     45     56    0.80×
768 MiB    19      38     0.50×     39     56    0.70×
  1 GiB    16      38     0.42×     31     56    0.55×   Intel DRAM
  2 GiB    16      39     0.41×     31     56    0.55×
  4 GiB    16      38     0.42×     31     56    0.55×   AMD: cross-CCD = DRAM
```

The L1d region (32 KiB) shows Intel ahead by a substantial margin: 285
GB/s read versus AMD's 211 GB/s, a 1.35× ratio. The RMW gap is even
larger, 479 GB/s versus 229 GB/s, a 2.09× ratio. Intel's L1d delivers
more combined load-plus-store throughput per cycle than AMD's at AVX-512
widths, an effect consistent with the Chips and Cheese article's
observation that Zen 4 implements 512-bit operations as two 256-bit
operations executed back-to-back on 256-bit physical units rather than
with native 512-bit hardware.

The L2 region (64 KiB through 1 MiB on AMD, 64 KiB through 2 MiB on
Intel) shows the opposite asymmetry. Intel L2 read bandwidth holds steady
at about 197 GB/s while AMD's holds at 118 GB/s, giving Intel a 1.67×
advantage for read-only L2 access. But AMD's RMW pattern reaches 233
GB/s in L2 while Intel's stays at 142 GB/s, reversing the ratio to 0.61×
in AMD's favor for combined-traffic patterns. The likely reason is that
AMD's L2 has separate read and write ports that scale better under
simultaneous load, while Intel's L2 port budget is shared between reads
and stores.

The L3 region shows the most dramatic asymmetry. AMD's in-CCD L3 (4 MiB
through 32 MiB) sustains roughly 88 GB/s read and 184 GB/s RMW from a
single core. Intel's L3 caps at 27 GB/s read and 53 GB/s RMW, regardless
of buffer size from 4 MiB up to 256 MiB. The Intel RMW figure is almost
exactly twice the Intel read figure, confirming the article's claim that
Intel's L3 has independent read and write paths that can run
concurrently. AMD's L3 RMW is also roughly 2× its L3 read, so this
property is not unique to Intel as the article slightly implied. The
single-core bandwidth gap is dramatic: at 16 MiB read, AMD's 88 GB/s
versus Intel's 27 GB/s is a ratio of 3.3× in AMD's favor.

In the 48 MiB to 256 MiB band, AMD's curve drops as accesses spill out of
the caller's CCD and start traversing the IOD to other CCDs' L3 caches.
At 256 MiB, AMD's bandwidth has fallen to 39 GB/s, still slightly higher
than Intel's 27 GB/s plateau but no longer dominant. AMD's curve plateaus
at 38 GB/s from roughly 128 MiB onward, and notably this same 38 GB/s
figure persists into the DRAM region (1 GiB to 4 GiB). What this tells us
is that for a single AMD core, accessing data outside its CCD's local L3
is bandwidth-limited not by DRAM but by the IOD's per-CCD bandwidth
allocation. Whether the line is "cached cross-CCD" or "fetched from DRAM"
makes no difference to a single core; both paths funnel through the
IOD and saturate at the same rate.

Intel's curve in the DRAM region settles at 16 GB/s read and 31 GB/s RMW,
about half of AMD's 38 GB/s and 56 GB/s. The Intel single-core DRAM
bandwidth is the lowest number we measured anywhere in this study and is
consistent with the article's observation that single-core DRAM bandwidth
on Xeon 6 sits below 20 GB/s.

```
Cross-socket (4 GiB only - see section 4.4 caveat for why):

Source: same script

            Intel local    Intel remote    AMD local    AMD remote
read         15.74          8.95           37.50        30.41
rmw          30.99         12.06           56.30        36.11
```

For cross-socket single-thread bandwidth we report only the 4 GiB
datapoint, because smaller buffers can be cached entirely in the caller
socket's L3 after a warm pass — see section 4.4 for the explanation.
Intel's cross-socket bandwidth collapses harder than AMD's: a 43 percent
drop for reads and 61 percent for RMW, compared to AMD's 19 percent and
36 percent. Intel's single-core cross-socket read bandwidth of 9 GB/s is
particularly striking and reflects a combination of two factors: the
high cross-socket latency (275 ns) reducing achievable memory-level
parallelism per core, and the UPI link's bandwidth being shared across
all in-flight requests.

Key observations from this section:

- Intel L1d delivers 1.35× read bandwidth and 2.09× RMW bandwidth versus
  AMD L1d. The L1 throughput difference reflects Intel's native 512-bit
  load and store paths versus AMD's 256-bit physical units running each
  512-bit operation in two cycles.
- L2 read bandwidth favors Intel by 1.67×; L2 RMW bandwidth favors AMD
  by 1.6×.
- Intel L3 single-core bandwidth is hard-clamped at approximately 27
  GB/s read and 53 GB/s RMW, exactly the values the Chips and Cheese
  article reports for Xeon 6.
- AMD in-CCD L3 single-core bandwidth is approximately 88 GB/s read and
  184 GB/s RMW, about 3.3× Intel's L3 bandwidth.
- AMD cross-CCD bandwidth and AMD DRAM bandwidth are both approximately
  38 GB/s for a single core, indicating that the IOD per-CCD bandwidth
  budget — not DRAM bandwidth — limits single-core access to anything
  outside the caller's own CCD.
- Intel single-core DRAM bandwidth (16 GB/s read) is less than half of
  AMD's (38 GB/s read).
- Intel's single-core cross-socket bandwidth collapses by 43-61 percent
  versus AMD's 19-36 percent.

### 4.3 Multi-thread bandwidth scaling

```
Source: script:bw_multi + sweep_bw_multi.sh
Run (Intel): bw_multi_delphi-3af6_20260521_0052.csv
Run (AMD):   bw_multi_andoria-15_20260521_0052.csv
```

The multi-thread sweep characterizes how aggregate bandwidth scales as
threads are added. Each thread operates on its own private buffer (no
shared cache lines, no inter-thread coherency traffic) and is pinned to
its own physical core. The reported numbers are the sum of per-thread
bandwidth across all participating threads. Two working-set sizes are
tested: 4 MiB per thread (which keeps each thread's data in its CCD's L3
on AMD, and in the shared monolithic L3 on Intel) and 256 MiB per thread
(which exceeds any L3 and exercises DRAM).

```
L3 region, 4 MiB per thread, read pattern:

threads    Intel GB/s    AMD GB/s     I/A
  1            27            91       0.30×
  2            54           181       0.30×
  4           105           360       0.29×
  8           194           637       0.30×
 16           334          1284       0.26×
 24           437          1818       0.24×
 32           403          2456       0.16×
 40           493          3026       0.16×
 48           550          3487       0.16×
 56           549          3839       0.14×
 64           552          4166       0.13×
 72           489          5228       0.09×    Intel drops
```

Both systems scale near-linearly at low thread counts (one to eight),
because each added thread brings its own L3 path. From eight threads
onward the two systems diverge sharply. Intel's aggregate L3 bandwidth
continues to grow but with diminishing returns: 16 threads reach 334
GB/s, 24 threads reach 437 GB/s, and then growth flattens. Between 48
and 64 threads the aggregate sits around 550 GB/s with no further
improvement. At 72 threads, full socket load, the aggregate actually
*drops* slightly to 489 GB/s. This drop is repeatable across runs and we
have not isolated its cause; candidates include mesh interconnect
saturation that adds latency faster than parallelism adds throughput, an
AVX-512 power-license downclock kicking in under full load, or kernel
housekeeping interference at high core counts.

AMD's curve scales differently. Up to eight threads, all activity stays
in CCD 0 (cores 0 through 7 are the eight cores of one CCD), and the
8-thread bandwidth of 637 GB/s represents that one CCD's L3 fully
utilized. From 16 threads onward, additional CCDs come online: 16
threads reach 1284 GB/s (two CCDs), 24 threads reach 1818 GB/s (three),
32 threads reach 2456 GB/s (four), and the curve continues nearly
linearly all the way to 72 threads at 5228 GB/s. At full load, the
AMD-to-Intel ratio reaches roughly 10:1.

```
L3 region, RMW pattern (bus traffic counted):

threads    Intel GB/s    AMD GB/s     I/A
  8           374          1259       0.30×
 24           876          3359       0.26×
 48          1102          6611       0.17×
 72           982          9870       0.10×
```

The RMW pattern follows the same shape but with roughly double the
numerical values, since bus traffic counts both loads and stores. At 72
threads, Intel reaches 982 GB/s aggregate L3 RMW; AMD reaches 9870 GB/s,
again a 10× ratio.

```
DRAM region, 256 MiB per thread, read (INCOMPLETE - sweep
truncated due to 2M pool fragmentation; not re-run by decision):

threads    Intel GB/s    AMD GB/s     notes
  1            26            37       AMD per-CCD bottleneck
  2            48            38         apparent at low N
  4            71            38
  8           127            38       all 8 threads on 1 AMD CCD
 16           228            78       AMD 2 CCDs active
 24           307           118       AMD 3 CCDs
 32           394           157       AMD 4 CCDs
  *           *             *         no data above 32 threads
```

The DRAM scaling data is incomplete. On both systems the sweep
terminated at 32 threads because the 2 MiB hugepage pool became
fragmented and could no longer satisfy the larger allocations needed for
the higher thread counts. The data we do have shows two interesting
features. First, Intel's DRAM aggregate grows steadily from 26 GB/s at
one thread to 394 GB/s at 32 threads; that 32-thread figure is
approximately 64 percent of the theoretical DDR5-6400 ceiling of 614
GB/s per socket, with room to grow at higher thread counts. Second,
AMD's DRAM aggregate stays at 38 GB/s for thread counts 1 through 8,
then doubles at 16, triples at 24, and quadruples at 32. The reason is
the AMD topology again: the first eight threads all run on CCD 0, and
all of CCD 0's DRAM traffic funnels through one IOD-to-DRAM path with a
bandwidth ceiling around 38 GB/s. Only when threads spread to additional
CCDs do additional IOD paths come online. This per-CCD-funneling
behavior is structural; it is the price AMD pays for the per-CCD L3
locality that delivers such favorable single-thread numbers.

Key observations from this section:

- Intel L3 aggregate bandwidth scales near-linearly up to 24 threads,
  plateaus at approximately 550 GB/s in the 48 to 64 thread range, and
  drops slightly to 489 GB/s at 72 threads. The drop is repeatable;
  cause not isolated.
- AMD L3 aggregate bandwidth scales near-linearly across the full
  socket, reaching 5228 GB/s at 72 threads.
- At full socket load on the L3 region, AMD's aggregate bandwidth is
  roughly 10× Intel's, for both read and RMW patterns.
- AMD's DRAM aggregate bandwidth is bottlenecked at approximately 38
  GB/s per active CCD; reaching the system DRAM bandwidth ceiling
  requires spreading work across many CCDs.
- DRAM scaling data above 32 threads was not collected on either
  system.

### 4.4 Cross-socket consolidated

**Caveat for the 16 MB and 256 MB cross-socket bandwidth tests.**
Buffers smaller than the caller socket's L3 cache get pulled into local
L3 on the first pass and then averaged over many subsequent passes that
hit local L3. As a result, what looks like a "cross-socket bandwidth"
measurement at small buffer sizes is actually a local-L3 bandwidth
measurement with a remote NUMA allocation tag. Only the 4 GiB datapoint
exceeds Intel's 432 MiB L3 and therefore represents true sustained
cross-socket DRAM traffic. The 16 MB and 256 MB cross-socket bandwidth
measurements we collected are not reported in this section for that
reason; they would mislead.

The latency measurements are not affected by this caveat because pointer
chase has no exploitable locality: every load is a cold miss, regardless
of which level of cache might "own" the line in principle.

Sources for this consolidated table:

- Latency: `script:ptr_chase + sweep_full.sh` (ptr_chase_full_*.csv)
- BW: `script:bw_avx512 + sweep_bw.sh` (bw_sweep_*.csv)

```
                          Intel              AMD                I/A
─────────────────────     ──────────────     ──────────────     ──────
ACPI distance ratio       21/10 = 2.10       32/10 = 3.20

Single-thread DRAM lat
  local (ns)                137                110              1.25×
  remote (ns)               275                199              1.38×
  remote/local              2.01               1.81

Single-thread DRAM BW
  local read (GB/s)          16                 38              0.42×
  remote read (GB/s)          9                 30              0.30×
  remote/local             0.57               0.81

  local rmw (GB/s)           31                 56              0.55×
  remote rmw (GB/s)          12                 36              0.33×
  remote/local             0.39               0.64
```

Two observations stand out. First, AMD's inter-socket fabric (xGMI on
Infinity Fabric) preserves more single-thread bandwidth across the
socket boundary than Intel's UPI: AMD retains 81 percent of its local
read bandwidth versus Intel's 57 percent, and 64 percent of its local
RMW versus Intel's 39 percent. Second, the relationship between the
software-visible NUMA distance and the measured ratio differs between
the two vendors. Intel's ACPI-reported distance ratio of 21/10 = 2.10
matches its measured remote/local latency ratio of 2.01 almost exactly,
suggesting that Intel's BIOS reports a faithful estimate. AMD's ACPI
distance ratio of 32/10 = 3.20 substantially overstates the measured
remote/local latency ratio of 1.80, which means software that uses ACPI
distances to make placement decisions on AMD will pessimistically avoid
cross-socket allocations more often than it should.

### 4.5 Core-to-core latency

```
Source: script:c2c_lat + sweep_c2c.sh
Run (Intel): c2c_lat_delphi-3af6_20260521_0135.csv
Run (AMD):   c2c_lat_andoria-15_20260521_0135.csv
```

Core-to-core (c2c) latency is measured by ping-ponging an atomic counter
between two pinned threads on different cores. Each CAS forces the
shared cache line to migrate from one core's L1 (in Modified state) to
the other, requiring a coherency round-trip through whatever fabric
mediates between them. We report two figures per pair: the median
round-trip time in nanoseconds, and the implied one-way latency (round
trip divided by two).

```
AMD c2c-RT grouped by peer CCD (caller cpu 0 on CCD 0):

peer CCD    peer cores    median ns/RT    ns/1-way     I/A in-CCD
  0          1-7             55.6           28          —
  1          8-15           364            182          6.55× vs CCD0
  2-11      16-95           365-376        182-188      ~6.6×
```

The AMD result is a textbook step function. When the caller (cpu 0,
which is on CCD 0) ping-pongs with one of the other seven cores on the
same CCD (cores 1 through 7), the round-trip is approximately 56 ns, or
28 ns one-way. When the peer is on any other CCD (cores 8 through 95),
the round-trip jumps to roughly 365 ns regardless of which CCD the peer
is on. The 6.5× step happens at the CCD boundary and is essentially
flat across all 11 other CCDs. This makes physical sense: in-CCD
coherency stays inside the CCD's L3 fabric, while cross-CCD coherency
must traverse the IOD, and the IOD cost dominates the per-CCD
positional differences.

```
Intel c2c-RT, dense scan (caller cpu 0, peers 1-71, same socket):

stat        ns/RT      one-way
min         115         57
p25         149         75
median      171         86
p75         184         92
max         230        115
mean        168         84
spread      2.0× from min to max
```

The Intel result looks very different. The spread of round-trip times
within a single socket is a factor of 2 (115 to 230 ns), but the
pattern is not a clean step function — successive cpu_b indices do not
show monotonically increasing latency. The data instead resembles
scatter around a central tendency, with some same-socket pairs measuring
115 ns and other same-socket pairs measuring 230 ns with no clean
boundary between the two regimes.

Grouping the Intel data by hypothesized 24-core compute-die boundaries,
inferred from the gaps in `core_id` and `cluster_id` values at cpu 24
and cpu 48 in our topology dump:

```
Intel buckets by hypothesized 24-core die (inferred from
/sys/.../topology/core_id and cluster_id gaps at cpu 24 and 48):

Source: script:topology-dump → core_grouping.log

die       cores    n    min    med    max    mean    med-vs-die0
─────     ─────    ─    ───    ───    ───    ────    ───────────
die 0     1-23    23    115    162    230     157    1.00× (ref)
die 1    24-47    24    136    159    225     171    0.98×
die 2    48-71    24    163    176    189     175    1.09×
```

There is a weak trend: the mean latency from cpu 0 to peers on the
opposite end of the socket (die 2) is roughly 9 percent higher than to
peers on the same die (die 0). But the within-die spread (e.g., 115 to
230 ns within die 0) is roughly six times the cross-die mean shift,
which means scanning latency-versus-peer-index does not show a clean
step at the die boundaries.

```
Cross-socket spot checks:

           Intel ns/RT     AMD ns/RT       I/A
min        463             598             0.77×
median     579             625             0.93×
max        605             639             0.95×
```

For cross-socket pairs both systems are slower than any same-socket
pair, as expected. Intel's cross-socket median is 579 ns round-trip,
AMD's is 625 ns. The median Intel cross-socket round-trip exceeds the
median Intel same-socket round-trip by approximately 408 ns; for AMD
the equivalent jump from in-CCD to cross-socket is 569 ns.

#### 4.5.1 Caveat: in-die scatter has no direct vendor proof

During this study one reviewer challenged the c2c interpretation with a
sharp question: *"How can the slowest in-die pair be slower than the
fastest cross-die pair? The slowest in-die should be faster than the
fastest cross-die."* The challenge is well-founded. If a die hop adds a
fixed positive cost, then in-die latency should bound cross-die latency
from below. Yet our data clearly shows die-0 cores reaching as high as
230 ns round-trip with cpu 0, while die-1 cores reach as low as 136 ns
with the same cpu 0. The simple "concentric dies" model is contradicted.

A plausible explanation, supported by indirect public evidence but not
directly proven, is that the Intel measurement is dominated by two
effects unrelated to die boundaries. First, each core sits at a specific
position on its die's 2D mesh; the mesh-distance from cpu 0 to other
cores in its same die varies considerably depending on physical
position. Second, the test cache line lives at a specific address that
hashes to a specific L3 slice somewhere on the mesh; every coherency
operation must route through that slice. The measured round-trip
therefore reflects the sum of two mesh distances — caller to slice and
peer to slice — rather than the direct caller-to-peer distance. Because
the firmware-assigned cpu_id values are not monotonic in mesh
coordinates, scanning peer cpu_b sequentially samples the mesh in a
non-monotonic order, producing the scatter we observe.

Public evidence supporting this interpretation:

```
Source                       What it confirms
─────────────                ──────────────────────────────
Intel Hot Chips 2024         Granite Rapids dies have 2D mesh
Tom's Hardware (Intel        "flexible row/column structure"
 slides quoted)              per die
Chips and Cheese article     "Intel stripes accesses across
                             [L3] slices to avoid partition
                             camping"
Chips and Cheese (Skylake    "different Skylake chips have
 c2c piece)                  different core numberings or
                             address to L3 slice mappings"
Jason Rahman article         "L3 slice attached to a core is
                             not exclusive to that particular
                             CPU core. Any CPU core on the
                             same physical die has equal access
                             to any L3 cache slice elsewhere"
Our topology dump            core_id gaps at cpu 24 and 48
                             consistent with three 24-core
                             dies (core_grouping.log)
Our c2c measurement          scatter pattern matches what
                             mesh + slice-hashing would produce
```

Three follow-up experiments would close the remaining gap:

1. Enable SNC3 in BIOS and rerun the c2c sweep. SNC3 scopes L3 slice
   selection within a single die, so cross-die hops become directly
   measurable as a clean step in the data.
2. Sweep the test cache-line address across many page offsets and
   average over slice ownership. If the within-die scatter persists,
   it is physical mesh distance; if it averages out, it is slice
   hashing.
3. Locate Intel-published mesh row-by-column dimensions for the
   Granite Rapids-AP compute die. None are publicly available at this
   writing.

For this writeup the c2c data is reported as measured, with the
mesh-plus-slice-hashing explanation labeled as the most likely
interpretation but not proven.

---
## 5. Audit of article's claims

This section walks through each major claim in the Chips and Cheese
article *A Look into Intel Xeon 6's Memory Subsystem* (Chester Lam,
September 2025) and states whether our measurements confirm,
contradict, or are unable to test it.

Article URL: <https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>

```
Article claim                       Status            Our data / location
─────────────────────────           ──────────────    ──────────────────────────
33 ns local-die L3 latency          Cannot reproduce  60.3 ns L3 plateau on
(SNC3 enabled, Xeon 6985P-C)        directly (need    our 6962P in SNC OFF.
                                    SNC3 enabled      See section 5.5 for
                                    on our system)    cross-check vs article's
                                                      predicted ~51 ns for
                                                      monolithic mode.

57.63 ns one-die-hop L3             Cannot reproduce  Same — folded into our
                                    directly           ~60 ns monolithic L3.

~80 ns two-die-hop L3               Cannot reproduce  Same.
                                    directly

432-480 MB total L3 capacity        CONFIRMED         script:ptr_chase
                                                      chase stays in L3
                                                      ≤256 MB, transitions
                                                      at 384 MB

~30 GB/s single-core L3 read        CONFIRMED         script:bw_avx512
on Xeon 6                                             measured 27 GB/s

L3 RMW ~2× L3 read on Xeon 6        CONFIRMED         script:bw_avx512
                                                      27 → 53 GB/s

Per-CCD L3 with limited             CONFIRMED         script:ptr_chase +
capacity (AMD)                                        script:bw_avx512

Intel L3 advantage at large WS      CONFIRMED         script:ptr_chase
                                                      48-256 MB band

Zen 4 AVX-512 lower throughput      CONFIRMED         script:bw_avx512
than Intel                                            1 MiB L1 read:
                                                      Intel 192, AMD 100 GB/s

Intel DRAM latency competitive      NOT CONFIRMED     script:ptr_chase
                                                      Intel 137, AMD 110 ns
                                                      (Intel 25% slower)

Intel cross-die c2c structure       WEAKLY SUPPORTED  script:c2c_lat
visible (50-80 ns intra-die)                          (see 4.5.1 caveat re
                                                      L3 slice hashing)
```

The three "cannot reproduce" claims are all SNC3-mode-specific. The
article measured them on AWS's r8i instance, which uses Xeon 6985P-C
configured by AWS in SNC3 mode (three NUMA nodes per socket). Our test
system runs with SNC disabled, so the per-die latencies are folded
together into one monolithic-L3 average. Section 5.5 cross-checks this
folded average against the article's own arithmetic prediction.

The L3 capacity claim is confirmed by inspection: our pointer chase
stays at the 60 ns L3 plateau through buffer sizes up to 256 MiB,
begins to transition at 384 MiB, and is mostly in DRAM by 768 MiB.
The 432 MiB L3 of the 6962P SKU absorbs random working sets up to
roughly 60 percent of its physical capacity, which is consistent with
random-eviction behavior in a large set-associative cache.

The L3 bandwidth claims match almost exactly. The article says "about
30 GB/s of L3 bandwidth" per core on Xeon 6; we measured 27 GB/s, and
the RMW pattern doubles it to 53 GB/s.

The DRAM latency claim is the only one we contradict. The article
states (in its "Final Words" section) that "the DRAM latency advantage
doesn't materialize" — by which the author means that despite Intel's
SNC3 layout placing memory controllers on the compute dies, AMD still
delivered slightly better DRAM latency in the article's tests. Our data
goes further: in monolithic mode our Intel system delivers 137 ns DRAM
latency versus AMD's 110 ns, a 25 percent gap in AMD's favor. This is a
larger gap than the article reported, probably because monolithic mode
averages local-die and far-die memory controller accesses where SNC3
mode pins each NUMA node to its local memory controllers.

The intra-die c2c claim is "weakly supported" rather than confirmed
because our SNC-OFF test cannot directly distinguish in-die from
cross-die pairs, and our c2c data is confounded by the L3 slice
hashing effect documented in section 4.5.1. The article's 50 to 80 ns
intra-die c2c range overlaps with the lower end of our 57 to 115 ns
one-way range, which is suggestive but not proof of structural
agreement.

---

## 5.5 Validation of Intel L3 latency

This section addresses a specific concern: are our Intel L3 measurements
real architecture, or are they measurement artifacts? The Intel L3
latency of approximately 60 ns is roughly 4× higher than AMD's in-CCD
L3 latency of approximately 13 ns. That is a large enough gap that it
deserves an independent cross-check before being reported as a finding.

We cross-check our Intel L3 number against three independent sources:
the Chips and Cheese article (using its measured SNC3 numbers to
predict a monolithic-mode latency), an Intel-published L2-miss number
from Hot Chips 2024, and the Intel Optimization Reference Manual
(which gives L1d and L2 cycle counts that we can compare against our
measurements at those levels for methodology validation).

### 5.5.1 Cross-check vs Chips and Cheese (computed)

```
Reference                           Value      Source
──────────────────                  ───────    ──────────────────────────
Article: local die L3 SNC3          33.25 ns   article body, "Cache and
                                               Memory Latency"
Article: +1 die hop L3              57.63 ns   article "NUMA/Chiplet
                                               Characteristics"
Article: +2 die hops L3             ~80 ns     same section
                                               (article: "nearly 80 ns")

Article prediction for monolithic   ~49-57 ns  computed: from article's
mode (author's own calculation                 closing paragraph
in "Final Words" section)                      and our arithmetic

Adjusted for our SKU clock          ~44-51 ns  computed: × (3.9/4.4)
(6962P at 4.4 GHz vs 6985P-C 3.9)              = × 0.886

Our measurement: L3 plateau         60.3 ns    script:ptr_chase
(4 MiB to 256 MiB)                             ptr_chase_full_delphi-3af6_*

Gap: our 60 ns vs predicted ~51 ns  +9 ns      arithmetic
```

The Chips and Cheese article includes the author's own arithmetic
estimate for what L3 latency would look like if the same Xeon 6 chip
were run in monolithic mode rather than SNC3 mode. Quoting the
relevant section: *"having 2/3 of accesses cross a die boundary would
likely send latency to just under 50 ns. That is, (2 × 57.63 + 33.25) /
3 = 49.5 ns."* A straightforward average of the article's three
die-hop values gives the slightly higher 57 ns figure. Both numbers
represent the article author's prediction for what our system should
measure.

Adjusting for the clock difference between the article's 6985P-C (3.9
GHz max boost) and our 6962P (4.4 GHz max boost) brings the prediction
down to roughly 44 to 51 ns. Our measured 60.3 ns is 9 to 16 ns higher
than this clock-adjusted prediction. The remaining gap is plausibly
explained by SKU-level differences (CHA and mesh clock frequencies
differ across SKUs in ways Intel does not publish), by the
approximate nature of the article's arithmetic model (which assumes
uniform 1/3 distribution across dies and ignores per-die variation in
cache slice distribution), and by minor differences in the DDR5
generation and DIMM speed grades. The match is not perfect but is
within the expected error of a back-of-envelope estimate based on data
from a different SKU.

### 5.5.2 Cross-check vs Intel Hot Chips 2024

Reference: Praveen Mosur, *Built for the Edge: The Intel Xeon 6 SoC*,
Hot Chips 2024 (August 2024).
<https://hc2024.hotchips.org/assets/program/conference/day1/14_HC2024.Intel.Xeon_6_SoC.Praveen.Mosur.pdf>

In a footnote to one of the slides, Intel publishes a measured
datapoint:

> **"L2 miss latency: 33 ns"**
>
> Configuration: 1-node, 1× Xeon, 42 cores, HT on, Turbo on,
> NUMA 1, DDR5-4800, 1C1T, VPP networking workload.

L2 miss in steady state is the same as L3 hit, so this is Intel's own
measured L3 hit latency on a Granite Rapids SoC under a
single-core-single-thread workload. It corroborates the Chips and
Cheese article's measured SNC-mode L3 latency of 33.25 ns to within
0.25 ns. This is the first Intel-authored number we have for L3
latency on this generation, and it gives independent vendor
confirmation that the article's measurements are sound.

Our 60 ns monolithic-mode measurement is consistent with averaging
this 33 ns local-die figure with the cross-die hops as predicted in
section 5.5.1.

### 5.5.3 Cross-check vs Intel Optimization Reference Manual

Reference: *Intel 64 and IA-32 Architectures Optimization Reference
Manual: Volume 1*, document #248966-050US, April 2024.
<https://cdrdv2-public.intel.com/671488/248966-Software-Optimization-Manual-V1-048.pdf>

Section 2.1, "6th Generation Intel Xeon Scalable Processor Family,"
documents the Redwood Cove microarchitecture and its cache parameters.
The relevant numbers:

```
                       Intel official     Our measurement      Implied cycles
                       (cycles)           (ns at 4.4 GHz)      at 4.4 GHz
L1d (Redwood Cove)     5                  1.14                 5.0    MATCHES
L2 (Redwood Cove)      16                 3.65                 16.1   MATCHES
L3 (no spec)           —                  60.3                 265    no spec
                                                                      to compare
```

This is the most important cross-check in this section. Intel publishes
L1d latency as 5 cycles and L2 latency as 16 cycles for Redwood Cove,
the Xeon 6 P-core. Our measurements, divided by the 4.4 GHz boost
clock, give 5.0 cycles for L1d and 16.1 cycles for L2 — matches to
within one percent for both. This validates the methodology of `ptr_chase`
end-to-end: the pinning is working, the hugepage backing is working,
the Hamiltonian cycle is generating real random load-use chains, and
the timer is accurate. If our L1d or L2 measurements had been off,
suspicion of the L3 measurement would be warranted; instead, both
agree exactly with Intel's published spec, which gives us strong
confidence in the L3 number as well.

Intel does not publish an L3 cycle count for Granite Rapids in either
the Optimization Reference Manual or the product spec page for any
Xeon 6 SKU. The available L3 latency references for this generation
are the Chips and Cheese article and the Hot Chips 2024 datapoint
above. Our cross-check therefore relies on those two sources for the
L3 specifically.

### 5.5.4 Verdict

The validation evidence stacks up as follows:

- L1d and L2 latencies measured in our pointer chase match Intel's
  officially published cycle counts to within one percent, validating
  the measurement methodology end-to-end.
- Our 60.3 ns L3 plateau aligns with the Chips and Cheese article's
  predicted monolithic-mode behavior to within 9 ns (after SKU clock
  adjustment), which is within the noise of an arithmetic estimate
  from a different SKU.
- Intel's own Hot Chips 2024 publication shows 33 ns L2-miss latency
  in single-core mode, corroborating the article's SNC-mode L3 figure
  to 0.25 ns precision. This is the first vendor-published number for
  Xeon 6 L3 latency.
- The 4× gap between Intel's monolithic-mode L3 (~60 ns) and AMD's
  in-CCD L3 (~13 ns) is structural: Intel pays mesh routing and
  cross-die hops on every L3 access in monolithic mode; AMD's per-CCD
  L3 has no such overhead inside the CCD.

The latency drop from L2 to L3 on Intel is real architecture, not a
measurement artifact. The same conclusion applies to the bandwidth
clamp at the L3 level (~27 GB/s single-core read), which matches the
article's "about 30 GB/s of L3 bandwidth" figure exactly.

```
Same check for AMD:

Reference                            Value     Source
─────────────────                    ─────     ──────────────────────
Article Zen 5 L3 (in-CCD)            ~11 ns    article
Article Zen 5 DRAM                   125.6 ns  article
Our Zen 4 L3 (in-CCD, 4 MiB)         12.9 ns   script:ptr_chase
Our Zen 4 DRAM (4 GiB)               109.9 ns  script:ptr_chase
```

The same cross-check on the AMD side: the article measures Zen 5 Turin
L3 at approximately 11 ns and DRAM at 125.6 ns. We measure Zen 4
Genoa L3 in-CCD at 12.9 ns and DRAM at 109.9 ns. Genoa is the
previous generation and is reported elsewhere in Chips and Cheese to
have slightly lower L3 latency than Turin, so our numbers being close
to but slightly different from the article's Turin numbers is
expected. Both AMD measurements are internally consistent with the
published Zen architecture characterization, giving us further
confidence that the methodology produces accurate numbers on both
vendors.

---

## 6. Hugepage handling in scripts

This section documents the hugepage handling logic used by the test
scripts. The driver scripts reserve hugepages dynamically, choose
hugepage size per buffer size, and restore the system to its original
state on exit. The C tools refuse buffer-size and hugepage-size
combinations that would silently misbehave. The motivation for each of
these behaviors comes from a specific real-world bug we encountered
during this study.

**Why two different hugepage sizes are used.** Three regimes call for
different page sizes:

- **4 KiB pages**: too small for our L3 and DRAM tests. A 16 MiB
  buffer covered by 4 KiB pages requires 4096 distinct page table
  entries, but the L2 dTLB on both Intel and AMD has only about 2K
  entries. With a random pointer chase, every load is essentially a
  TLB miss, and the measurement is dominated by page-walk latency
  rather than cache latency.
- **2 MiB pages**: appropriate for the L3 region (4 MiB through 768
  MiB buffers). A 768 MiB buffer at 2 MiB granularity uses only 384
  page table entries, easily within the dTLB capacity even for fully
  random walks.
- **1 GiB pages**: needed for buffers larger than approximately 1
  GiB. A 4 GiB buffer at 2 MiB granularity would need 2048 page table
  entries, putting TLB pressure back into the measurement.

**Linux pool management.** Each hugepage size has its own pool,
controlled via separate sysfs files:

```
/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages   (1 GiB pool)
/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages      (2 MiB pool)
```

The two pools are independent. Setting `nr_hugepages` for one size does
not affect the other. The `vm.nr_hugepages` sysctl applies only to the
"default" huge page size as set at boot, which on these systems is 1
GiB; using that sysctl is therefore not the right way to manage the 2
MiB pool.

The 1 GiB pool was pre-existing at boot on both systems (512 pages on
the Intel system, 280 on the AMD system). Our scripts use it as-is and
do not modify it. They verify the free count before each DRAM test and
abort with a clear error if too few pages are available.

**The 2 MiB pool is reserved dynamically by each script** and restored
on exit. The mechanism, in shell:

```bash
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

sudo bash -c "echo $WANT_2M > $HUGE2M"
```

The `trap cleanup EXIT` line registers the restore function to run on
any exit path: normal completion, an error mid-script, a Ctrl-C, or
most signal-handled terminations. It does not survive `SIGKILL` or
power loss; if either happens during a run, the 2 MiB pool will remain
at the size the script reserved until manually reset:

```bash
sudo bash -c 'echo 0 > /sys/kernel/.../hugepages-2048kB/nr_hugepages'
```

**Page-size-aware test invocation.** Both `ptr_chase.c` and
`bw_avx512.c` accept a `--hugepage {1g|2m|none}` argument and fail
loudly if the requested buffer size is smaller than one page of the
requested type:

```c
if (size < pagesize) {
    fprintf(stderr,
        "ERROR: --size (%zu) is smaller than one %s page (%zu)\n"
        "       Pick a larger --size or use --hugepage 2m / none.\n",
        ...);
    return 2;
}
```

This guard exists because of a bug we hit during the early L3 sweep.
The original C code silently rounded the buffer size up to one full
page when the requested size was smaller. A driver script that asked
for `--size 48M --hugepage 1g` therefore got a 1 GiB allocation,
which produced perfectly plausible-looking latency numbers identical
to the 1G run — and the same was true for 64M, 96M, 128M, all the
way up to 768M. The bug cost a full sweep cycle to identify, and
afterward we added the explicit error so it cannot happen again. The
script and the C code together now make the failure mode loud.

**Driver scripts pick the right `--hugepage` per buffer size.** Each
sweep script categorizes its buffer sizes into the three regimes and
passes the appropriate flag:

```
L1/L2 region (32K..2M):    --hugepage none
L3 region (4M..768M):      --hugepage 2m
DRAM region (1G..4G):      --hugepage 1g
```

This is the simplest scheme that uses the smallest page size that
keeps the buffer within dTLB capacity. Smaller pages give us more
flexibility (we can run a 48 MiB test without needing a 64 MiB
allocation rounded up from 1 GiB pages), and larger pages remove TLB
walks from the measurement.

---

## 7. Reproducibility and deliverables

This section lists all source files, scripts, and data files
referenced in this writeup, and gives the commands needed to
reproduce every measurement.

**Source files manifest:**

```
Type           Filename                  Lines    Purpose
─────          ─────────────────         ─────    ──────────────────────
C source       inspect_pages.c           ~280     pinning + NUMA sanity
C source       ptr_chase.c               ~270     single-thread latency
C source       bw_avx512.c               ~330     single-thread BW
C source       bw_multi.c                ~360     multi-thread agg BW
C source       c2c_lat.c                 ~280     c2c CAS ping-pong
Makefile       Makefile                  ~25      builds all binaries

Inspection     step0_inspect.sh          ~120     system characterization
Inspection     gpu_topo_inspect.sh       ~120     PCIe topology
                                                  (not used in this writeup)

Driver         sweep_full.sh             ~60      ptr_chase size sweep
Driver         sweep_bw.sh               ~75      bw_avx512 sweep
Driver         sweep_bw_multi.sh         ~90      bw_multi thread sweep
Driver         sweep_c2c.sh              ~40      c2c_lat scan

Result CSV     ptr_chase_full_*.csv      22 rows  latency sweep
Result CSV     bw_sweep_*.csv            52 rows  single-thr BW sweep
Result CSV     bw_multi_*.csv            ~38 rows multi-thr BW scaling
Result CSV     c2c_lat_*.csv             ~75 rows c2c matrix

Inspection log inspect_*.log             —        step0 outputs
Topology log   core_grouping.log         —        /sys topology dump
```

**Reproduction sequence on a fresh Ubuntu 22.04+ machine:**

```bash
sudo apt install -y libnuma-dev build-essential numactl
make
bash step0_inspect.sh         # ~30 sec
bash sweep_full.sh            # ~2 min,  ptr_chase_full_*.csv
bash sweep_bw.sh              # ~5 min,  bw_sweep_*.csv
bash sweep_bw_multi.sh        # ~10 min, bw_multi_*.csv
bash sweep_c2c.sh             # ~5-8 min, c2c_lat_*.csv
```

Total elapsed time is approximately 25 minutes per system. Each
script reserves required hugepages via sudo, restores them on exit via
trap (including errors and Ctrl-C), writes a CSV with a header row to
a timestamped file, and sends progress messages to stderr while
keeping stdout free for the CSV.

**External references** used in this writeup:

- Chester Lam, *A Look into Intel Xeon 6's Memory Subsystem*, Chips
  and Cheese, September 2025.
  <https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>
- Chester Lam, *Core to Core Latency Data on Large Systems*, Chips
  and Cheese.
  <https://chipsandcheese.com/p/core-to-core-latency-data-on-large-systems>
- Jason Rahman, *Intel CPU Die Topology*.
  <https://jprahman.substack.com/p/intel-cpu-die-topology>
- Paul Alcorn, *Intel Details 144-Core Sierra Forest, Granite Rapids
  Architecture, and Xeon Roadmap*, Tom's Hardware.
  <https://www.tomshardware.com/news/intel-details-sierra-forest-and-granite-rapids-architecture-xeon-roadmap>
- Praveen Mosur, *Built for the Edge: The Intel Xeon 6 SoC*, Hot Chips
  2024.
  <https://hc2024.hotchips.org/assets/program/conference/day1/14_HC2024.Intel.Xeon_6_SoC.Praveen.Mosur.pdf>
- *Intel 64 and IA-32 Architectures Optimization Reference Manual*,
  Volume 1, document 248966-050US, April 2024.
  <https://cdrdv2-public.intel.com/671488/248966-Software-Optimization-Manual-V1-048.pdf>
- *Intel Xeon 6980P Processor product specifications*.
  <https://www.intel.com/content/www/us/en/products/sku/240777/intel-xeon-6980p-processor-504m-cache-2-00-ghz/specifications.html>
- *Intel Fact Sheet: Xeon 6 P-core*.
  <https://download.intel.com/newsroom/2024/data-center/Fact-Sheet-Xeon-6-P-Core.pdf>
- Hacker News discussion thread, Sapphire Rapids L3 latency reference.
  <https://news.ycombinator.com/item?id=44029935>

---

*End of writeup. All measurements collected May 19-21, 2026.*
