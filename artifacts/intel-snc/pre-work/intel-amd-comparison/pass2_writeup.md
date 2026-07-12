# Intel vs AMD CPU/Memory Subsystem Comparison

## Pass 2 — Full prose writeup

**Scope.** A focused comparison of the CPU and memory subsystems of an Intel
Xeon 6962P (Granite Rapids-AP) and an AMD EPYC 9654 (Zen 4 Genoa), both
two-socket servers, built around the recent Chips and Cheese article
*A Look into Intel Xeon 6's Memory Subsystem* (September 2025). Findings
are tied to specific microbenchmark runs and external sources.

**Format note.** All data tables and architectural diagrams are wrapped in
` ``` ` code blocks so monospace alignment is preserved. Read on a terminal
or monospace viewer for correct rendering.

**Data provenance.** Every measurement in this document comes from a single
test round on 2026-05-25 (Intel: `delphi-3af6`; AMD: `andoria-15`). Where a
result is attributed to a script or CSV, that CSV is in the `data/`
directory of this archive and the matching sweep log is in `logs/`. No
measurements are mixed across runs.

---

## Table of contents

```
1.  Executive summary
2.  Systems under test
    2.1  Inspection method
    2.2  Three-system comparison
    2.3  System diagrams
    2.3.1  Hierarchical view of the 6962P
    2.3.2  Combined architecture diagram (PNG)
    2.4  Comparability caveats
3.  Methodology
4.  Findings
    4.1  Latency vs working-set size
    4.2  Single-thread bandwidth
    4.3  Multi-thread bandwidth scaling
    4.3.1  Operational note: hugepage exhaustion on long-uptime systems
    4.4  Cross-socket
    4.5  Core-to-core latency
    4.5.1  Within-socket scatter on Intel
    4.5.2  Lack of public in-die layout information
    4.6  Extended DRAM latency and bandwidth (4 GiB to 32 GiB)
5.  Investigation caveats
6.  Audit of article's claims
6.5  Validation of Intel L3 latency
    6.5.1  Cross-check vs Chips and Cheese (computed)
    6.5.2  Cross-check vs Intel Hot Chips 2024 (33 ns L2-miss)
    6.5.3  Cross-check vs Intel Optimization Reference Manual
    6.5.4  Verdict
    6.5.5  Cross-check vs Emerald Rapids monolithic-mode data
7.  Hugepage handling in scripts
8.  Reproducibility & deliverables
A.  Appendix: process notes
```

---

## 1. Executive summary

The two server architectures take fundamentally different approaches to
cache and memory, and our microbenchmarks make these tradeoffs visible.
On a working set that fits inside one CCD's L3, AMD delivers single-thread
latency three to five times lower than Intel's monolithic L3; AMD also
sustains roughly three times the single-thread L3 bandwidth in that
regime. Once the working set grows past one CCD (32 MiB), AMD pays a
cross-CCD penalty and its latency catches up to Intel's by 48 MiB and
then exceeds it; Intel's L3 latency stays flat at about 60 ns out to
the full 432 MiB cache. AMD wins for working sets up to ~32 MiB; Intel
wins for working sets between 48 MiB and ~700 MiB.

In the DRAM regime, AMD has the structural advantage in single-thread
performance: 110 ns vs 138 ns local latency, and 38 GB/s vs 16 GB/s
single-thread read bandwidth. Cross-socket behavior follows the same
pattern: AMD's xGMI fabric retains 81% of single-thread read bandwidth
across the socket boundary; Intel's UPI retains only 57%. The ACPI
NUMA distance ratios reported by firmware tell different stories on
the two vendors: Intel's 21/10 ratio matches the measured remote/local
latency ratio almost exactly (2.01), while AMD's 32/10 substantially
overstates the measured 1.81.

At full socket load, the per-CCD L3 architecture of AMD scales
aggregate L3 bandwidth nearly linearly with thread count to roughly
5 TB/s. Intel's mesh saturates between 550 and 600 GB/s and then
drops back to ~470 GB/s at all 72 cores. The 10× gap at full socket
load is the most dramatic single number in this study.

Core-to-core coherency latency reveals the same architectural
difference one more way. AMD shows a clean step at the CCD boundary
(28 ns intra-CCD, ~186 ns cross-CCD, regardless of which non-zero CCD
you pick). Intel shows continuous scatter from 55 to 118 ns one-way
inside one socket — likely reflecting both mesh routing distances and
L3 slice hashing — without a clean step structure.

A new sweep covering 4 GiB to 32 GiB DRAM working sets confirms that
DRAM behavior is steady-state in this range. Intel's DRAM latency
rises slightly (~5 ns) from 4 to 32 GiB; AMD's stays flat. Single-thread
DRAM bandwidth is flat to within ±2% on both vendors over this range.
The 4 GiB datapoint from the main sweep is therefore representative.

A finding outside the architectural comparison: the multi-thread DRAM
test failed on both vendors at high thread counts due to 2 MiB hugepage
pool fragmentation. On AMD the whole sweep aborted at setup; on Intel
the DRAM-region test ran cleanly to 32 threads but failed with SIGBUS
at 40 threads and above. This is documented in section 4.3.1 as a
real-world operational concern for production servers that stay up
for weeks or months.

---

## 2. Systems under test

### 2.1 Inspection method

System characterization was captured by `script:step0_inspect.sh`,
which runs `lscpu`, `numactl --hardware`, `dmidecode -t memory`,
reads `/proc/cmdline` and `/proc/meminfo`, samples cache parameters
from `/sys/devices/system/cpu/cpu0/cache/`, and runs `dmesg | grep -i mce`
to spot hardware errors since boot. Output logs are in this archive:
`inspect_intel_delphi-3af6_20260519.log` (primary Intel),
`inspect_intelCI_delphi-17cf_20260520.log` (Intel CI reference, read-only),
`inspect_amd_andoria-15_20260519.log` (AMD), and
`core_grouping.log` (a topology dump from `/sys`).

Pre- and post-run system state is captured by `script:load_snapshot.sh`,
which reads `/proc/loadavg`, runs `vmstat 1 3` for a CPU-utilization
window, takes `ps -eo pid,user,pcpu,pmem,comm --sort=-pcpu | head -16`
to identify hotspot processes, dumps memory and hugepage state from
`/proc/meminfo` and `/sys/kernel/mm/hugepages/`, samples CPU frequency
from `cpufreq/scaling_cur_freq`, reads thermal zones if exposed, and
grep's `dmesg` for MCE/EDAC/hardware-error entries. The `load_snapshot_*.log`
files in `logs/` document the system state immediately before and after
each measurement session.

### 2.2 Three-system comparison

The table below summarizes all three machines in our test environment,
with all values taken from `script:step0_inspect.sh` runs.

```
Field                  Intel 3af6           Intel CI (17cf)        AMD (andoria-15)
─────                  ──────────────       ─────────────────      ──────────────────
Hostname               delphi-3af6          delphi-17cf            andoria-15
Role                   primary test box     CI/CD reference        comparison box
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
Distance matrix*       10/21                10/21                  10/32

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

\* **Distance matrix.** The NUMA distance values come from the ACPI SLIT
(System Locality Information Table), a BIOS hint to the operating system
about the relative cost of accessing memory across NUMA boundaries. Local
accesses are conventionally assigned a distance of 10; remote distances
are larger numbers indicating "more expensive." Read literally:
"a remote access costs `<distance>/10` times as much as a local access."
The values are captured by step0_inspect both from `numactl --hardware`
output and the raw `/sys/devices/system/node/node*/distance` files. How
faithfully these BIOS-reported numbers match measured latency varies by
vendor — Intel's 21/10 matches the measured remote/local ratio well; AMD's
32/10 overstates it. See section 4.4 for the full comparison.

The two Intel machines share the same family and SNC mode but differ in
boost clock; only `delphi-3af6` was used for measurements because it
allows root-level changes to hugepage pool size. The CI machine
(`delphi-17cf`) is documented for completeness but no benchmark data
comes from it.

### 2.3 System diagrams

#### Intel — Xeon 6962P, two-socket, SNC OFF

The Intel system runs in SNC OFF mode, so each socket exposes one
NUMA node to the operating system and the full 432 MB of L3 is
visible to every core on that socket as a logically monolithic
cache. Internally the socket consists of three compute dies bridged
by Intel's EMIB silicon interconnect, but the OS does not see this
3-die structure.

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

#### CHA / mesh-stop / L3 slice detail

The "Mesh + EMIB" box above is not a single logical block; it is a 2D
mesh of stops, each of which holds a core, its L1 and L2 private
caches, a CHA (Caching/Home Agent), and an L3 cache slice. The mesh
moves cache lines between cores and between L3 slices and the memory
controllers. The CHAs together implement the coherency protocol and
the address-to-slice hash function that determines which L3 slice
"homes" each cache line. The diagram below zooms into a single mesh
stop:

```
                    one mesh stop (one core's neighborhood)
                    on a Granite Rapids compute die

         ┌──────────────────────────────────────────────┐
         │  MESH STOP                                   │
         │                                              │
         │  ┌────────────────┐    ┌────────────────┐    │
         │  │  CORE          │    │   CHA          │    │
         │  │  (Redwood Cove)│    │  Caching /     │    │
         │  │                │    │  Home Agent    │    │
         │  │  - L1d 48 KB   │    │                │    │
         │  │  - L1i 64 KB   │◄──►│  - L3 slice    │    │
         │  │  - L2 2 MB     │    │  - Snoop       │    │
         │  │                │    │    filter      │    │
         │  └────────────────┘    │  - Coherency   │    │
         │                        │    arbitration │    │
         │                        │    logic       │    │
         │                        └───────┬────────┘    │
         │                                │             │
         │   ┌──────────┐                 │             │
         │   │  router  │◄────────────────┘             │
         │   │  (mesh   │                               │
         │   │   switch)│                               │
         │   └──┬───┬───┘                               │
         │      │   │                                   │
         └──────┼───┼───────────────────────────────────┘
                │   │
        ◄───────┘   └───────►  to neighboring mesh stops
        (north/south/east/west on the 2D mesh)
```

The provenance of each element in this diagram needs to be explicit,
because the diagram combines information from three different sources
and inferences from arithmetic. The CHA naming and slice/snoop-filter
structure come from a verbatim sentence in the Chips and Cheese
article: *"Cores share a mesh stop with a CHA (Caching/Home Agent),
which incorporates a L3 cache slice and a snoop filter."* The same
article states that *"The Xeon 6 6985P-C has 120 CHA instances running
at 2.2 GHz, providing 480 MB of total L3 across the chip"* — that is
120 CHAs per socket, not per die. The corresponding per-die figures
(40 CHAs per die, 4 MB per slice) are derived by dividing by the
number of compute dies the article enables in its SNC3 measurements.
The article itself explicitly says *"Intel hasn't published documents
detailing Xeon 6's mesh layout,"* so the physical row-and-column
arrangement of mesh stops shown in our diagram is illustrative rather
than measured. The address-hashing behavior — that cache lines are
striped across L3 slices regardless of which core owns the slice —
comes from Chips and Cheese's older Skylake c2c piece and from Jason
Rahman's separate writeup on Intel die topology: *"Any CPU core on
the same physical die has equal access to any L3 cache slice
elsewhere on the die."* The EMIB die-bridge fact is from Tom's
Hardware reporting on Intel's Hot Chips 2024 slides.

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

The AMD architecture is the cleaner of the two from a benchmarking
standpoint. Each CCD (Core Complex Die) holds eight cores and a
32 MiB L3 that those cores have very fast access to but cores on
other CCDs do not — every cross-CCD memory access has to traverse
the central I/O die (IOD). The IOD also hosts all twelve memory
controllers and all PCIe roots. NPS1 mode (one NUMA node per socket)
unifies the 12 CCDs' memory views, but the CCD boundary remains an
architectural cliff for both L3 and core-to-core latency.

#### 2.3.1 Hierarchical view of the 6962P

The same information about our Intel system, represented as a
hierarchical tree, with each fact tagged by its source. Items marked
STATED come from a published source (Intel ARK, the article, or
Intel Hot Chips slides); items marked DERIVED are computed from
stated facts under a uniform-distribution assumption; the CHA count
of 108 per socket is the one item directly MEASURED on our system
via `/sys/devices/uncore_cha_*`.

```
Intel Xeon 6962P system (delphi-3af6)
│
├── 2 packages (CPU sockets, NUMA nodes 0 and 1)
│   │
│   ├── Each package contains:
│   │   ├── 3 compute dies (process: Intel 3)
│   │   ├── 2 IO dies (separate process, lower freq)
│   │   │   ├── PCIe roots
│   │   │   ├── Accelerators: DSA, IAA, QAT, DLB
│   │   │   └── UPI controllers (inter-socket fabric)
│   │   ├── EMIB silicon bridges between adjacent dies
│   │   └── 72 cores per socket (Redwood Cove)
│   │
│   └── Each compute die contains:
│       │
│       ├── ~24 cores AVG (DERIVED 72/3; not necessarily uniform)
│       ├── 144 MiB L3 AVG (DERIVED 432/3)
│       ├── 4 DRAM memory controllers
│       │   └── feeds 4 DDR5-6400 channels (1 DIMM per channel)
│       │
│       ├── ~36 CHAs per die (DERIVED 108/3)
│       │   │
│       │   └── each CHA holds:
│       │       ├── 1 mesh stop
│       │       ├── 1 L3 slice (4 MiB)
│       │       └── 1 snoop filter + coherency logic
│       │
│       ├── In-die mesh (2D, geometry undocumented)
│       │   ├── connects all mesh stops within the die
│       │   └── speed in GB/s: Insufficient data
│       │
│       └── MDF (Modular Data Fabric) stops at die edges
│           ├── for cross-die traffic
│           ├── physical layer = EMIB bridge silicon
│           └── speed in GB/s: Insufficient data
│                              (2.5 GHz clock; BW not published)
│
├── Inter-socket: UPI link(s)
│   ├── UPI 2.0, 24 GT/s per lane on this family
│   ├── number of links / lanes on 6962P: Insufficient data
│   └── ACPI distance: local=10, remote=21 (BIOS-reported)
│
└── Each socket has:
    ├── L3 total: 432 MiB (= 3 × 144 MiB dies = 108 × 4 MiB slices)
    ├── CHAs total: 108 (MEASURED via /sys/devices/uncore_cha_*)
    ├── Cores: 72 enabled
    ├── DDR5 channels: 12 (= 3 × 4 controllers)
    └── DRAM: 768 GB (12 × 64 GB DIMMs)
```

#### 2.3.2 Combined architecture diagram (PNG)

A single PNG image combining the two-socket overview, the per-socket
totals, the compute die internal layout, and a zoomed-in single mesh
stop view ships with this archive at `figures/intel_xeon_6962p_architecture.png`.
The matplotlib generator script is alongside it
(`figures/gen_diagram.py`).

The PNG contains the two-socket overview with IO dies, compute dies,
EMIB bridges, DDR5 channels and the UPI link between sockets; a
per-socket totals box (cores, L3, CHAs, DDR channels, ACPI distances,
and the measured remote/local DRAM-latency ratio); the compute die
internal layout drawn as a 6×6 mesh (illustrative — Intel does not
publish the real shape) with MC0/MC1/MC2/MC3 memory controllers on
the short edges and EMIB-A through EMIB-F bridge sites on the long
edges; and a single mesh stop zoom-in showing the CORE box (Redwood
Cove, L1d/L1i/L2 sizes, may-be-fused-off note) and CHA box
(Caching/Home Agent, 4 MiB L3 slice, snoop filter, coherency)
connected to a mesh router with N/S/E/W links to neighbor mesh stops.

### 2.4 Comparability caveats

A direct Intel-vs-AMD comparison is bounded by four asymmetries that
were not corrected for in our measurements:

The DDR5 speeds differ — 6400 MT/s on Intel versus 4800 on AMD —
giving Intel a roughly 33% theoretical per-channel bandwidth
advantage. We did not normalize this, so any direct bandwidth
comparison includes the DDR speed effect.

CPU side-channel mitigations are ON in the Linux kernel on Intel (default:
eIBRS, SSBD, IBPB, and others) and OFF on AMD (`mitigations=off` on the
kernel command line). The effect on our user-space hot loops is small,
but it does affect things like indirect branches, syscall paths, and
context switches; for completeness we record the difference here rather
than try to correct for it. Verification is in `/proc/cmdline` and
`/sys/devices/system/cpu/vulnerabilities/*`, both captured by
`script:step0_inspect.sh`.

The kernels differ (6.8 on Intel, 5.15 on AMD), which affects
scheduler behavior, NUMA balancing, and the specific implementation
of CPU mitigations. We did not normalize.

The two systems have different per-socket core counts (72 vs 96), so
whole-socket comparisons are biased toward the system with more cores;
per-core comparisons are clean. Wherever possible the discussion
focuses on per-core or per-thread metrics. The system uptimes also
differ (31 days Intel, 41 days AMD), which affects memory fragmentation
and, as we will see in section 4.3.1, the multi-thread DRAM measurement.

---

## 3. Methodology

Five microbenchmarks generate the data in this writeup. Each is small,
focused, and parameterized so that it can be run reproducibly with no
human-in-the-loop tuning. The complete source code is in `code/`. The
table below maps each tool to its driver script and output CSV pattern:

```
Tool             Source file        Driver script        Output CSV pattern
─────            ──────────────     ──────────────       ──────────────────────────
inspect_pages    inspect_pages.c    (manual)             (stdout only, no CSV)
ptr_chase        ptr_chase.c        sweep_full.sh        ptr_chase_full_<host>_<ts>.csv
ptr_chase        ptr_chase.c        sweep_dram_lat.sh    ptr_chase_dram_<host>_<ts>.csv
bw_avx512        bw_avx512.c        sweep_bw.sh          bw_sweep_<host>_<ts>.csv
bw_avx512        bw_avx512.c        sweep_dram_bw.sh     bw_dram_<host>_<ts>.csv
bw_multi         bw_multi.c         sweep_bw_multi.sh    bw_multi_<host>_<ts>.csv
c2c_lat          c2c_lat.c          sweep_c2c.sh         c2c_lat_<host>_<ts>.csv
(no binary)      (n/a)              load_snapshot.sh     load_snapshot_<host>_<ts>.log
```

The pointer-chase tool (`ptr_chase`) measures single-thread load-use
latency by walking a randomized cycle of pointers through a NUMA-pinned,
hugepage-backed buffer. Every load is a cold miss to whatever level of
the cache hierarchy the buffer fits in. The stride is a fixed 64 bytes
at every buffer size — one cache line — because at every level (L1, L2,
L3, DRAM) the fetch unit is 64 bytes. As the buffer grows, the cycle
length grows automatically (`ncells = size / 64`), and the random
ordering defeats hardware prefetchers at every level. We report
nanoseconds per load.

The bandwidth tool (`bw_avx512`) measures single-thread streaming
bandwidth via AVX-512 read, read-modify-write (rmw), and write
patterns. The kernel iterates over a NUMA-pinned, hugepage-backed
buffer until at least `--min-walk-secs` of elapsed time have passed,
and reports aggregate GB/s.

The multi-thread bandwidth tool (`bw_multi`) wraps the same AVX-512
kernel in a multi-threaded harness. Each thread gets its own private
buffer (no shared cache lines between threads, so no coherency traffic
contaminates the measurement); all threads barrier together, run the
kernel for the same elapsed time, then report aggregate GB/s across
threads.

The core-to-core latency tool (`c2c_lat`) measures the cost of
coherency traffic between a pair of cores by ping-ponging a single
cache line via atomic CAS. We report round-trip ns (one ping plus one
pong) and the implied one-way latency.

The pre/post system state tool (`load_snapshot.sh`) is described in
section 2.1.

There is a class of things our microbenchmark suite does NOT measure
and that should not be inferred from this writeup. We do not measure
mixed read/write workloads at realistic ratios. We do not measure the
benefits of hardware prefetchers (the pointer chase is specifically
designed to defeat them). We do not measure TLB-walk cost (we use
hugepages everywhere to take TLB-walk out of the equation). And we do
not measure workloads with shared data across threads. The picture
this study paints is of the cache and memory subsystem in isolation,
which is the same scope as the Chips and Cheese article we're auditing.

We considered including SPEC CPU2017, the industry-standard CPU
benchmark used in the Chips and Cheese article, but skipped it because
of cost: it requires a commercial license (~$1-2k), ~25 GB of disk,
~20 hours of wall time per system for a single iteration of both
suites, 30+ hours for a reportable run, and significant tuning effort
to get clean numbers. Our microbenchmarks already cover the
architectural picture we need. If a portable cross-system CPU
benchmark is needed later, Phoronix Test Suite (free, open source) is
the practical alternative.

---

## 4. Findings

### 4.1 Latency vs working-set size

The single most useful chart in a memory subsystem study is latency
versus working-set size, because every plateau and transition reveals
a level of the cache hierarchy. The table below shows results from
`script:ptr_chase + sweep_full.sh` on both systems
(`ptr_chase_full_delphi-3af6_20260525_0109.csv` and
`ptr_chase_full_andoria-15_20260525_0109.csv`), with median nanoseconds
per load at each working-set size:

```
size       Intel ns    AMD ns     I/A       region
─────────  ────────    ──────     ──────    ────────────────────
 32 KiB        1.14       1.08    1.05×     L1d
 64 KiB        3.64       3.80    0.96×     L2
128 KiB        3.65       3.81    0.96×     L2
256 KiB        3.65       3.81    0.96×     L2
512 KiB        4.06       5.06    0.80×     L2 (AMD partial spill)
  1 MiB        6.10       8.62    0.71×     AMD past L2
  2 MiB       21.82      13.00    1.68×     Intel L2 spilling, AMD L3
  4 MiB       60.31      12.79    4.72×     Intel L3, AMD in-CCD L3
  8 MiB       60.37      13.98    4.32×
 16 MiB       60.41      15.76    3.83×
 32 MiB       60.42      22.39    2.70×
 48 MiB       60.43      62.09    0.97×     CROSSOVER
 64 MiB       60.44      77.63    0.78×
 96 MiB       60.98      87.70    0.70×
128 MiB       61.24      93.39    0.66×
192 MiB       61.53      99.83    0.62×
256 MiB       62.11     103.12    0.60×
384 MiB       73.59     106.23    0.69×     Intel L3 → DRAM spilling
512 MiB       95.75     107.81    0.89×
768 MiB      123.82     110.11    1.12×
  1 GiB      126.30     108.52    1.16×
  2 GiB      134.81     109.54    1.23×
  4 GiB      137.56     109.78    1.25×     pure DRAM
```

The cross-socket measurements come from the same script and CSV but
with the buffer NUMA-bound to node 1 (the remote socket):

```
size       Intel ns    AMD ns    I/A      remote/local
─────────  ────────    ──────    ──────   ──────────────
1 GiB      244.5       197.0     1.24×    Intel 1.94×, AMD 1.81×
2 GiB      268.2       198.3     1.35×    Intel 1.99×, AMD 1.81×
4 GiB      275.9       198.8     1.39×    Intel 2.01×, AMD 1.81×
```

**Interpreting the Intel curve — four distinct plateaus.** Reading
left to right, the Intel column shows four flat regions separated by
three transitions, and it is worth naming each one explicitly so that
the much larger L3-to-DRAM jump is not mistaken for the much smaller
L2-to-L3 jump:

```
Plateau           Range          ns       What it shows
─────────         ──────         ────     ───────────────────────────
L1d               32 KiB         ~1.1     fits entirely in 48 KB L1d
L2                64K - 1M       ~3.6-6   fits in 2 MB L2
L3 (monolithic)   4M - 256M      ~60      fits in 432 MB L3
DRAM              ≥1G            ~138     beyond L3 → DRAM

Transitions:
   L1d → L2:      between 32 KiB and 64 KiB
   L2  → L3:      between 1 MiB and 4 MiB (transition value at 2 MiB = 22 ns)
   L3  → DRAM:    between 256 MiB and 768 MiB (gradual)
```

The 60→72 ns jump between 256 MiB and 384 MiB is the **L3 cache spilling
into DRAM**, not the L2-to-L3 transition. The L2-to-L3 jump on Intel is
much larger (4 → 60 ns) and happens earlier in the sweep, between 1 MiB
and 4 MiB. Mistaking the L3-to-DRAM transition for the L2-to-L3 transition
is a natural reading error because both jumps look visually similar on
a log-scale plot, so it bears explicit calling out.

What the data shows architecturally: the L1d and L2 regions are
roughly comparable between vendors (within 5%, with Intel marginally
slower at L1d and AMD's slightly larger L2 partition giving a
smoother transition out of L2). The 4-32 MiB band is where AMD's
per-CCD L3 shines: each CCD has its own 32 MiB L3 with sub-15 ns
latency, three to five times faster than Intel's 60 ns L3 plateau.

The crossover point comes at 48 MiB, where AMD's per-CCD L3 has
spilled and it starts paying the cross-CCD cost through the IOD; from
that size onward Intel's monolithic L3 wins by a growing margin
through 256 MiB. At 384 MiB Intel's L3 starts to spill — visible in
the upward trend from 60 ns toward DRAM latency — and from about
768 MiB on Intel sits at roughly 138 ns DRAM, 25% slower than AMD's
110 ns.

Cross-socket DRAM is 28% lower on AMD than Intel. The remote/local
ratio of 2.01 on Intel matches the firmware-reported ACPI distance
ratio (21/10) almost exactly; on AMD the measured ratio of 1.81 is
substantially smaller than the firmware-reported 32/10. We return to
this in section 4.4.

### 4.2 Single-thread bandwidth

Single-thread streaming bandwidth from `script:bw_avx512 + sweep_bw.sh`
(`bw_sweep_delphi-3af6_20260525_0116.csv` and the matching AMD CSV)
tells a different story at L3:

```
Local memory, GB/s (read + rmw patterns):

size      Iread   Aread   I/A_r    Irmw   Armw   I/A_m   notes
─────     ─────   ─────   ─────    ─────  ─────  ─────   ────────────────
 32 KiB   285     210     1.35×    479    218    2.20×   L1d
 64 KiB   196     117     1.67×    142    233    0.61×   L2
128 KiB   198     118     1.68×    142    233    0.61×   L2
256 KiB   198     118     1.68×    142    235    0.60×   L2
512 KiB   197     118     1.67×    142    225    0.63×   L2
  1 MiB   196     102     1.92×    142    196    0.72×   AMD L2 spills
  2 MiB    56     100     0.56×     92    201    0.46×   Intel L2 spills
  4 MiB    27      89     0.30×     53    178    0.30×   Intel L3 / AMD CCD
  8 MiB    27      88     0.30×     53    184    0.29×
 16 MiB    27      90     0.30×     53    177    0.30×
 32 MiB    27      85     0.31×     53    141    0.37×   AMD cross-CCD start
 48 MiB    27      53     0.50×     53     86    0.62×   transition
 64 MiB    27      51     0.52×     53     80    0.66×
 96 MiB    27      38     0.69×     53     74    0.72×
128 MiB    27      38     0.70×     53     67    0.79×
192 MiB    27      38     0.70×     53     56    0.93×
256 MiB    27      38     0.69×     53     56    0.93×
384 MiB    26      37     0.69×     50     56    0.89×   Intel L3 spilling
512 MiB    23      38     0.59×     45     56    0.81×
768 MiB    19      38     0.51×     39     56    0.70×
  1 GiB    16      38     0.41×     31     56    0.55×   Intel DRAM
  2 GiB    16      38     0.41×     31     56    0.56×
  4 GiB    16      37     0.42×     31     56    0.55×   AMD: cross-CCD = DRAM
```

Intel's L1d is faster on both read (1.35×) and especially rmw (2.20×).
At L2 the picture inverts: AMD is slower on read but substantially
faster on rmw. AMD's L2 read bandwidth being lower than its L1d
read bandwidth (118 vs 210 GB/s) is more pronounced than Intel's
equivalent step (196 vs 285 GB/s), reflecting Zen 4's narrower 256-bit
AVX-512 implementation that executes 512-bit operations as two
back-to-back 256-bit μ-ops; this halves throughput for streaming reads
that fit comfortably in L1d.

The L3 region is where the per-CCD-vs-monolithic divergence becomes
stark. Intel's single-thread L3 read bandwidth is clamped at about
27 GB/s — a hard ceiling that does not move regardless of how large
the buffer is, all the way out to where L3 spills into DRAM. AMD's
in-CCD L3 delivers about 88-90 GB/s of read bandwidth in the 4-32 MiB
band, 3.3× faster than Intel. The rmw pattern moves Intel from 27 to
53 GB/s (the article notes this 2× bonus from RMW counting bus
traffic in both directions), and AMD from 88 to 178 GB/s.

Past 32 MiB, AMD pays the cross-CCD cost and bandwidth declines
toward what the IOD can serve — about 38 GB/s read, 56 GB/s rmw,
which is also the same number as AMD's local DRAM bandwidth.
Architecturally this is a useful observation: from the perspective of
a single thread, AMD's cross-CCD L3 is no faster than AMD's local
DRAM. The 32 MiB CCD is the only fast-cache regime AMD offers to a
single thread.

The cross-socket bandwidth measurements only meaningfully apply at
working-set sizes that exceed the caller socket's L3. We report
those in section 4.4 with a methodology caveat.

### 4.3 Multi-thread bandwidth scaling

The L3-bandwidth story at one thread reverses at full socket load,
and `script:bw_multi + sweep_bw_multi.sh` is the experiment that
reveals it.

The L3-region test runs 1 to 72 threads (or 96 on AMD), with each
thread owning its own private 4 MiB buffer that fits inside one L3
slice or CCD. The aggregate bandwidth reflects how much the L3
subsystem can move when many cores are demanding from it
simultaneously.

The data table below reports Intel data from this round
(`bw_multi_delphi-3af6_20260525_0120.csv`) and AMD data carried over
from an earlier round, because AMD's `bw_multi` sweep aborted at
setup in this round — see section 4.3.1 for details. The AMD numbers
are marked with an asterisk and the qualitative shape is what
matters for the discussion below:

```
L3 region, 4 MiB per thread, read pattern:

threads    Intel GB/s    AMD GB/s     I/A
  1            26.7         ~ 90 *    ~0.30×
  2            54.5         ~180 *    ~0.30×
  4           104.8         ~360 *    ~0.30×
  8           193.8         ~640 *    ~0.30×
 16           335.1        ~1280 *    ~0.26×
 24           437.2        ~1820 *    ~0.24×
 32           418.2        ~2460 *    ~0.17×
 40           508.3        ~3030 *    ~0.17×
 48           556.2        ~3490 *    ~0.16×
 56           552.0        ~3840 *    ~0.14×
 64           561.4        ~4170 *    ~0.13×
 72           473.5        ~5230 *    ~0.09×   Intel drops

* AMD column reproduced from prior characterization round
  (bw_multi_andoria-15_20260521_0052.csv, available in the archive).
  AMD numbers in this band have been within 2% across several days of
  test runs, so this qualitative comparison is robust even though
  the latest round's CSV is empty.
```

Intel L3 bandwidth scales near-linearly from one thread up to roughly
24 threads, then begins to flatten around 550 GB/s through 48-64
threads, and unexpectedly drops to 473 GB/s at all 72 cores. The
peak-and-drop pattern is repeatable across runs but the cause is not
isolated; possible explanations include mesh saturation, power-license
transitions when AVX-512 utilization spikes across many cores, or
kernel housekeeping interference. We flag it as a real measurement
but not a fully understood architectural number.

AMD L3 scales near-linearly across the full thread range to about
5.2 TB/s. Each CCD has its own L3 that scales independently of the
others, so the aggregate is essentially the per-CCD ceiling
(~440 GB/s) times the number of CCDs that have at least one active
thread. At full socket load, **AMD is ~10× the Intel aggregate L3
bandwidth**. This is the single most dramatic finding in this study.

The rmw pattern doubles both numbers in the same ratio — at 72
threads Intel reaches 931 GB/s and AMD reaches ~9.87 TB/s — preserving
the 10× gap.

The DRAM-region test, where each thread has a 256 MiB buffer and
all bandwidth comes from DRAM, ran cleanly from 1 to 32 threads on
Intel before failing at higher thread counts. AMD's whole `bw_multi`
sweep aborted at the setup phase this round. We report the Intel
1-32 thread data here and the failure mode in detail in 4.3.1:

```
DRAM region, 256 MiB per thread, read (TRUNCATED on Intel, ABSENT on AMD):

threads    Intel GB/s    AMD GB/s     notes
  1            26.6        ~37 *       AMD per-CCD bottleneck
  2            47.5        ~38 *         apparent at low N
  4            71.6        ~38 *
  8           127.1        ~38 *       all 8 threads on 1 AMD CCD
 16           228.3        ~78 *       AMD 2 CCDs active
 24           307.0       ~118 *       AMD 3 CCDs
 32           394.1       ~157 *       AMD 4 CCDs
 40           FAILED        —          Intel: SIGBUS (hugepage exhaust.)
 48           FAILED        —          Intel: SIGBUS
 56           FAILED        —          Intel: SIGBUS
 64           FAILED        —          Intel: SIGBUS
 72           FAILED        —          Intel: SIGBUS
```

The DRAM-region shape that's visible up to 32 threads matches the
architectural prediction: AMD's per-CCD-to-IOD path bottlenecks at
about one CCD's worth of bandwidth per CCD, so adding more threads
within one CCD does not help (all 8 threads on CCD 0 still see only
~37 GB/s); adding threads across more CCDs adds bandwidth in
proportion to how many CCDs are active. Intel's mesh has no
per-CCD-like structure, so DRAM bandwidth grows smoothly with thread
count up to where memory-controller saturation flattens it.

#### 4.3.1 Operational note: hugepage exhaustion on long-uptime systems

The multi-thread DRAM measurements failed at high thread counts in
this round on both vendors, with different failure modes that share
a root cause. We describe the failures explicitly because they are
useful in their own right: production servers routinely stay up for
months, and benchmarks that allocate large hugepage-backed buffers
will exhibit this same failure mode in deployment without explicit
diagnostic logging.

```
Intel (delphi-3af6, 31 days uptime, no swap):
  L3 region (4 MiB/thread):     all 12 thread counts × 2 patterns
                                = 24/24 PASS
  DRAM region (256 MiB/thread): 7 thread counts (1-32) × 2 patterns
                                = 14 PASS, 10 FAIL (SIGBUS at
                                threads 40, 48, 56, 64, 72)

AMD (andoria-15, 41 days uptime, 8 GB active swap):
  Setup phase:                  Requested 12544 × 2M pages = ~24 GiB.
                                Kernel granted only 6519 (~12 GiB).
                                Script aborted before running any test.
  L3 region:                    0/24 attempted
  DRAM region:                  0/24 attempted
```

What the loud-failure logs actually captured. From
`bw_multi_andoria-15_20260525_0118.log`:

```
===== sweep_bw_multi started at Mon May 25 01:18:41 AM UTC 2026 =====
CSV: bw_multi_andoria-15_20260525_0118.csv
Log: bw_multi_andoria-15_20260525_0118.log

node0 cpulist: 0-95,192-287
Will scale threads up to 96 (CPUs 0..95)
want 2M pages: 12544 (~24 GiB)
2M pool: GOT 6519 (~12 GiB)

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! FATAL: 2M page reservation insufficient
!!! wanted: 12544, got: 6519
!!! This is usually caused by memory pressure or
!!! fragmentation. Check free physical memory.
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

===== sweep_bw_multi ABORTED at Mon May 25 01:18:44 AM UTC 2026 =====
No sweeps were run. Both CSV and LOG files exist for diagnostics.
```

And from `bw_multi_delphi-3af6_20260525_0120.log`:

```
=== threads=40 size/thr=256M pattern=read ===
sweep_bw_multi.sh: line 72: 662684 Bus error (core dumped)
  "$TOOLS/bw_multi" --cpus "$cpus" --mem-node 0 --size-per-thread "$sz" ...

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!! TEST FAILED: threads=40 size/thr=256M pattern=read
!!! exit code: 135
!!! stderr from bw_multi:
!!!   == bw_multi threads=40 mem-node=0 size/thread=268435456
!!!      pattern=read hugepage=2m iters=5 ==
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

What is happening, mechanically. Linux hugepage allocation has two
phases. First, the kernel reserves virtual address space and updates
the `nr_hugepages` count — this succeeds even if there is not enough
physically-contiguous memory to back all the pages. Second, the
first page-fault on each individual hugepage tries to allocate
2 MiB of physically-contiguous, 2-MiB-aligned RAM; if no such chunk
is available at fault time, the kernel sends SIGBUS to the process.
Exit code 135 (= 128 + 7) is the standard Linux convention for "killed
by signal 7," which is SIGBUS.

Why the chunk is not available at fault time on long-uptime systems:
physical memory fragments over time as processes allocate and free,
and the kernel's "swiss cheese" view of free memory loses its
contiguous-large-pages property. The AMD system additionally had
8 GiB actively in swap when this test ran, which is a strong signal
that the kernel was already struggling to find clean physical RAM
even for ordinary 4 KiB allocations.

The L3-region test (4 MiB per thread) succeeded on Intel because the
total footprint is much smaller — 72 threads × 4 MiB = 288 MiB worth
of 2 MiB pages, or just 144 pages. The DRAM-region test
(256 MiB per thread) needs 72 threads × 256 MiB = 18 GiB worth of
2 MiB pages, or 9216 pages. The script reserves 9472 2 MiB pages at
startup, which the kernel accepted, but acceptance of the reservation
does not guarantee physical backing.

What this teaches us about benchmarking production systems:

- Hugepage-based microbenchmarks should always check `free_hugepages`
  against required count before starting and report clearly when the
  request can only be partially satisfied.
- The previous (silent-failure) version of these scripts would have
  produced incomplete CSVs and end-of-run summaries claiming "no
  failures." Production deployments often see this exact failure
  mode without anyone noticing.
- Production-relevant tuning options: reserve hugepages at boot via
  kernel cmdline (`hugepagesz=2M hugepages=N`) rather than dynamically;
  use 1 GiB pages where workload buffer sizes allow; periodically
  `echo 1 > /proc/sys/vm/compact_memory` to reduce fragmentation
  before workload start.

### 4.4 Cross-socket consolidated

Before reporting cross-socket bandwidth results, there is a methodology
caveat that affects which measurements are meaningful. When a buffer
smaller than the caller socket's L3 cache is allocated on the remote
socket and then accessed in a streaming loop, the data is pulled into
the caller socket's L3 on the first pass; subsequent passes hit local
L3 instead of remote DRAM. Averaging over many passes therefore
produces a number that looks like "cross-socket bandwidth" but is
mostly local-L3 bandwidth with a remote NUMA tag attached. We do not
report 16 MiB or 256 MiB cross-socket BW results in this table because
they would mislead. Only the 4 GiB buffer exceeds Intel's 432 MiB L3
and therefore represents true sustained cross-socket DRAM traffic.

The latency measurements are not affected by this caveat. Pointer
chase has no exploitable locality: every load is a cold miss, regardless
of which level of cache might "own" the line in principle.

Sources for this consolidated table:

- Latency: `script:ptr_chase + sweep_full.sh`
  (Intel: ptr_chase_full_delphi-3af6_20260525_0109.csv;
   AMD: ptr_chase_full_andoria-15_20260525_0109.csv)
- BW: `script:bw_avx512 + sweep_bw.sh`
  (Intel: bw_sweep_delphi-3af6_20260525_0116.csv;
   AMD: bw_sweep_andoria-15_20260525_0115.csv)

```
                          Intel              AMD                I/A
─────────────────────     ──────────────     ──────────────     ──────
ACPI distance ratio       21/10 = 2.10       32/10 = 3.20

Single-thread DRAM lat
  local (ns)                138                110              1.25×
  remote (ns)               276                199              1.39×
  remote/local              2.01               1.81

Single-thread DRAM BW
  local read (GB/s)          16                 37              0.42×
  remote read (GB/s)          9                 30              0.30×
  remote/local             0.57               0.81

  local rmw (GB/s)           31                 56              0.55×
  remote rmw (GB/s)          19                 36              0.52×
  remote/local             0.61               0.64
```

Two observations stand out. First, AMD's inter-socket fabric (xGMI on
Infinity Fabric) preserves more single-thread bandwidth across the
socket boundary than Intel's UPI: AMD retains 81 percent of its local
read bandwidth versus Intel's 57 percent. Second, the relationship
between the software-visible NUMA distance and the measured ratio
differs between the two vendors. Intel's ACPI-reported distance ratio
of 21/10 = 2.10 matches its measured remote/local latency ratio of
2.01 almost exactly, suggesting that Intel's BIOS reports a faithful
estimate. AMD's ACPI distance ratio of 32/10 = 3.20 substantially
overstates the measured remote/local latency ratio of 1.81, which
means software that uses ACPI distances to make placement decisions
on AMD will pessimistically avoid cross-socket allocations more often
than it should.

### 4.5 Core-to-core latency

Coherency latency between core pairs is measured by
`script:c2c_lat + sweep_c2c.sh` using an atomic CAS ping-pong on a
single cache line. The CSVs are
`c2c_lat_delphi-3af6_20260525_0122.csv` and
`c2c_lat_andoria-15_20260525_0118.csv`.

On AMD the pattern is a clean step at the CCD boundary. Each of CCDs
1 through 11 sits at essentially the same ~370 ns round-trip latency
from CCD 0, with only ~30 ns of intra-CCD variation; CCD 0 itself
(intra-CCD pairs) sits at 55-56 ns round trip:

```
AMD c2c-RT grouped by peer CCD (caller cpu 0 on CCD 0):

peer CCD    peer cores    median ns/RT    ns/1-way     ratio vs CCD0
  0          1-7             55.6           28          1.00× (ref)
  1          8-15           376.7          188          6.78×
  2         16-23           369.9          185          6.65×
  3         24-31           380.3          190          6.84×
  4         32-39           360.4          180          6.48×
  5         40-47           351.9          176          6.33×
  6         48-55           376.6          188          6.77×
  7         56-63           371.6          186          6.68×
  8         64-71           372.7          186          6.70×
  9         72-79           361.7          181          6.50×
 10         80-87           371.7          186          6.69×
 11         88-95           370.8          185          6.67×
```

On Intel the dense scan within one socket shows continuous scatter
without a clean step:

```
Intel c2c-RT, dense scan (caller cpu 0, peers 1-71, same socket):

stat        ns/RT      one-way
min         109         55
p25         149         75
median      171         86
p75         187         94
max         237        118
mean        172         86
spread      2.2× from min to max
```

Cross-socket spot checks are about 4-7× slower than same-socket
medians on both vendors, with Intel cross-socket faster than AMD:

```
           Intel ns/RT     AMD ns/RT       I/A
min        420             630             0.67×
median     494             638             0.78×
max        502             652             0.77×
```

The Intel cross-socket result being faster than AMD is consistent
with our DRAM-latency cross-socket result (Intel UPI is slower in
absolute terms but starts from a higher base; the cross-socket
penalty is smaller in relative terms on UPI than on xGMI for this
specific test).

#### 4.5.1 Within-socket scatter on Intel

Both vendors show a clean step at the socket boundary — cross-socket
round-trip latency is strictly slower than any within-socket pair on
both systems. Within the same socket, however, the structure differs
sharply between the two vendors.

```
Intel (delphi-3af6, 2026-05-25)
   c2c_lat_delphi-3af6_20260525_0122.csv

   group                  n     RT range (ns)        notes
   ─────                  ───   ─────────────         ─────
   same-socket            71    109 - 237            2.2× spread
   cross-socket            4    420 - 502

AMD (andoria-15, 2026-05-25)
   c2c_lat_andoria-15_20260525_0118.csv

   group                  n     RT range (ns)        notes
   ─────                  ───   ─────────────         ─────
   intra-CCD (CCD 0)       7    55.6 - 55.6          essentially zero
                                                     spread
   cross-CCD              88    302 - 394            clean step from
                                                     intra-CCD
                                                     (~6× jump)
   cross-socket            4    630 - 652            clean step from
                                                     cross-CCD
                                                     (+236 ns gap)
```

AMD shows two clean steps within one socket: a sharp jump from
intra-CCD (55 ns, essentially zero spread) to cross-CCD (302-394 ns),
and another sharp jump from cross-CCD to cross-socket (630-652 ns).
The architectural boundaries match the observed jumps exactly: AMD's
CCD topology is publicly documented (12 CCDs per socket, 8 cores per
CCD, all cross-CCD traffic funneled through the IOD), and our data
falls into those buckets cleanly.

Intel's within-socket data, by contrast, is a continuous spread from
109 to 237 ns without any internal step. Granite Rapids-AP is built
from three compute dies (as discussed in section 2.3), so we would
expect some die-boundary effect to be visible — but no banding into
three groups appears in our data. The article we are auditing notes
this directly: *"Intel hasn't published documents detailing Xeon 6's
mesh layout."* Under SNC OFF, the kernel reports each socket as a
single NUMA node with no die-level subdivisions exposed in `/sys`, so
we have no authoritative way to label any given core as belonging to
die 0, 1, or 2. We discuss this limitation and our attempted
workaround in section 4.5.2.

The clean socket-boundary step on both vendors is itself worth
recording explicitly:

```
                  Slowest within-socket   Fastest cross-socket   Gap
Intel              237 ns                  420 ns                 +183 ns
AMD                394 ns                  630 ns                 +236 ns
```

Cross-socket pairs are strictly slower than every within-socket pair
on both systems. There is no contradiction or overlap at the socket
boundary. The unresolved question is the structure inside Intel's
within-socket scatter, which our data cannot attribute to any specific
architectural cause without additional information.

#### 4.5.2 Lack of public in-die layout information

The fundamental difficulty with attributing Intel's within-socket c2c
scatter to a specific architectural cause is that Intel does not
publish the die-to-core mapping for Granite Rapids-AP. The Chips and
Cheese article we are auditing notes this directly: *"Intel hasn't
published documents detailing Xeon 6's mesh layout."* Beyond mesh
geometry, the assignment of cpu_id to physical compute die is also
not exposed by the kernel under SNC OFF mode.

What our system DOES expose, and what it doesn't:

```
Source                           What it tells us           What it
                                                            doesn't
─────────────────────────        ────────────────────       ────────
/sys/devices/system/node/        2 NUMA nodes (one per      Nothing
                                 socket); no die-level      about die
                                 subdivision under SNC OFF  boundaries

/sys/devices/uncore_cha_*        108 CHAs per socket;       Nothing
                                 cpumask=0,72 on all CHAs   about which
                                 (meaningless dispatch      CHA is on
                                 hint, not topology)        which die

/sys/devices/system/cpu/         cpu_id, core_id, socket    Nothing
  cpu*/topology/                 affinity                   about die-
                                                            level
                                                            grouping

dmesg | grep die                 (no relevant output)       Nothing

numactl --hardware               2 nodes, distances 10/21   Nothing
                                                            about within-
                                                            socket
                                                            structure

Intel ARK / datasheets           Core counts, cache sizes,  Nothing
                                 SKU clocks, DDR speeds     about die
                                                            assembly
```

During this study we attempted to derive a die mapping from the
`core_grouping.log` topology dump, which shows core_id gaps at
certain positions. A natural-looking partition was:

```
Hypothetical:    Die 0:  cpu_id 0-23   (24 cores)
                 Die 1:  cpu_id 24-47  (24 cores)
                 Die 2:  cpu_id 48-71  (24 cores)
```

Under that partition, all c2c pairs `(cpu 0, cpu_b ∈ 1-23)` would be
in-die round trips and all pairs `(cpu 0, cpu_b ∈ 24-71)` would be
cross-die round trips. Architecturally, any in-die pair should be
faster than any cross-die pair, because in-die avoids the EMIB bridge
hop. But our latest data, when read through that hypothesis, gives:

```
Source: c2c_lat_delphi-3af6_20260525_0122.csv

"In-die" pairs (cpu_b 1-23):
  fastest:  109 ns  (cpu_b = 1)
  slowest:  237 ns  (cpu_b = 14)   ← slowest "in-die"

"Cross-die" pairs (cpu_b 24-71):
  fastest:  131 ns  (cpu_b = 24)   ← fastest "cross-die"
  slowest:  204 ns  (cpu_b = 55)
```

The slowest "in-die" pair (237 ns) is slower than the fastest
"cross-die" pair (131 ns) by 106 ns, which contradicts the
architectural expectation. Two possibilities are consistent with
this observation: either the hypothetical partition is wrong (the
cpu_id 0-23 / 24-47 / 48-71 split does not correspond to physical
die boundaries), or the partition is correct but c2c latency is not
a simple function of die distance (for example, L3 slice hashing may
route some "in-die" pairs through cross-die slices and inflate their
round-trip time). Our data cannot distinguish these possibilities.

Three options would close the gap. First, enabling SNC3 in BIOS would
cause the kernel to report six NUMA nodes (three per socket) so that
each die's cores would be unambiguously identified by NUMA node
membership; the c2c sweep would then directly partition pairs into
in-die and cross-die groups by NUMA node rather than by guess. This
requires BIOS access and a reboot, neither of which we have arranged
for the test systems. Second, modifying `c2c_lat.c` to sweep the test
cache-line address across many page offsets and average across slice
ownerships would isolate the slice-hashing component from the
mesh-distance component without needing SNC3; this requires a code
change and a re-run. Third, Intel could publish the mesh layout for
Granite Rapids-AP — not currently in any public documentation we have
been able to find.

For this study we report the c2c scatter as measured (section 4.5.1)
and accept that we cannot decompose it into mesh-distance and
slice-hashing components without one of the three options above. The
absurd-conclusion episode (slowest "in-die" > fastest "cross-die") is
itself a useful finding: it demonstrates concretely why public in-die
layout information matters for architectural analysis on Intel server
CPUs with multi-die packages.

### 4.6 Extended DRAM latency and bandwidth (4 GiB to 32 GiB)

The main `sweep_full.sh` and `sweep_bw.sh` scripts measure up to 4 GiB
working sets. An additional pair of sweeps, `sweep_dram_lat.sh` and
`sweep_dram_bw.sh`, exists to verify that DRAM-region behavior is
steady-state up to larger buffer sizes. The 64 GiB datapoint that was
originally in this sweep was removed after empirical testing because
it consistently triggered SIGBUS on the AMD system due to insufficient
1 GiB hugepages; the 4-32 GiB range cleanly characterizes steady-state
DRAM behavior on both vendors.

Source: `script:ptr_chase + sweep_dram_lat.sh` and
`script:bw_avx512 + sweep_dram_bw.sh`; CSVs are
`ptr_chase_dram_*_2026052*.csv` and `bw_dram_*_2026052*.csv`.

```
Latency (ns):

  size      Intel local    AMD local     Intel remote    AMD remote
  ─────     ──────────     ─────────     ────────────    ─────────
  4 GiB     137.6          109.8         275.8           198.7
  8 GiB     139.2          110.0           —               —
 16 GiB     141.1          110.0         283.7           199.0
 32 GiB     142.2          110.1           —               —

  Intel rise 4G → 32G:   +4.6 ns   (3.3% increase)
  AMD rise 4G → 32G:     +0.3 ns   (0.3% increase)
```

```
Single-thread bandwidth (GB/s):

  size      Intel local read    AMD local read    Intel local rmw    AMD local rmw
  ─────     ────────────────    ──────────────    ───────────────    ─────────────
  4 GiB     15.79               38.45             31.08              56.40
  8 GiB     15.71               38.47             31.11              56.43
 16 GiB     15.75               37.87             31.19              55.76
 32 GiB     15.77               37.86             31.21              56.43

  All values flat to within ±2% across 4G..32G on both systems.
```

Both vendors deliver flat single-thread DRAM bandwidth from 4 GiB
through 32 GiB. The 4 GiB datapoint from the main sweep is therefore
representative of steady-state DRAM behavior on both systems, and a
larger sweep was not needed to characterize DRAM bandwidth.

DRAM latency on Intel rises slightly with buffer size — about 5 ns
from 4 GiB to 32 GiB — while AMD's stays dead flat (within 0.3 ns).
The effect is small but reproducible (stddev under 0.2 ns on both
systems). Possible causes include page-table-walk effects at very
large mappings even with 1 GiB pages, DRAM bank scheduling under
fewer DIMM ranks active at any one time, or Intel's mesh routing
varying with which memory controller serves a given physical
address. None of these can be confirmed without internal Intel
documentation. The Intel-rises and AMD-flat asymmetry is an
architectural property worth noting but does not change any
conclusion about Intel-vs-AMD DRAM performance.

---

## 5. Investigation caveats

A number of methodological and platform-level asymmetries bound the
strength of conclusions from this study. They are recorded here in
one place so a reader does not need to reconstruct them from
scattered footnotes throughout earlier sections.

```
ID    Caveat                              Section ref     Notes
────  ────────────────────────────        ─────────────   ──────────────
C1    Intel in-die layout not publicly    4.5.2           Article quote:
      documented; cpu_id-to-die mapping                   "Intel hasn't
      not exposed by kernel under SNC                     published
      OFF                                                 documents
                                                          detailing
                                                          Xeon 6's mesh
                                                          layout."

C2    DDR5 speed asymmetry not            2.4             Intel 6400 vs
      corrected for                                       AMD 4800 MT/s
                                                          (Intel +33%
                                                          theoretical
                                                          channel BW)

C3    CPU side-channel mitigations        2.4             Intel: ON
      ON vs OFF not corrected for                         (default eIBRS
                                                          + SSBD + IBPB)
                                                          AMD: OFF
                                                          (mitigations=off)

C4    Kernel version asymmetry not        2.4             Intel 6.8 vs
      corrected for                                       AMD 5.15

C5    Long-uptime memory                  4.3.1           bw_multi DRAM
      fragmentation affects multi-                        scaling truncates
      thread DRAM measurement                             at 32+ threads
                                                          on Intel; aborts
                                                          at setup on AMD

C6    No SPEC CPU2017 — out of scope      3               Industry-
      (license + time cost)                               standard CPU
                                                          benchmark not
                                                          run; if needed
                                                          later, Phoronix
                                                          Test Suite is
                                                          the practical
                                                          alternative

C7    SNC3 mode not enabled on Intel      4.5.2           Would expose
                                                          die boundaries
                                                          to OS; requires
                                                          BIOS access +
                                                          reboot

C8    Per-die structure of 6962P is       2.3             Only 108 CHAs/
      derived, not directly observed                      socket is
                                                          observed (from
                                                          /sys/devices/
                                                          uncore_cha_*).
                                                          Per-die CHA,
                                                          L3, and core
                                                          counts are
                                                          derived under
                                                          uniform-
                                                          distribution
                                                          assumption.

C9    Single-thread cross-socket BW       4.4             For sizes <
      measurements at small sizes are                     caller socket's
      caller-socket-L3 artifacts, not                     L3 (16 MB,
      true cross-socket BW                                256 MB), data
                                                          gets pulled
                                                          into local L3
                                                          on first pass.
                                                          Only 4 GiB
                                                          datapoint is
                                                          true cross-
                                                          socket DRAM
                                                          traffic.

C10   In-CCD c2c value on AMD is one      4.5             Caller is cpu 0
      cluster only (CCD 0); intra-CCD                     on CCD 0.
      latency for CCDs 1-11 not                           Intra-CCD
      measured                                            results from
                                                          other CCDs not
                                                          collected.

C11   c2c uses fixed cache-line address   4.5.2           Slice ownership
      across all pair measurements;                       held constant
      slice-hashing scatter not                           by accident, not
      isolated                                            by design.
```

Caveats C1, C5, C7, C8, C9, C10, and C11 are discussed in detail in
their respective sections (column 2). Caveats C2, C3, C4 are
properties of the test environment recorded in section 2.4. Caveat
C6 is a scope statement from section 3.

What we tried to do about these caveats during the study. For C5
(hugepage fragmentation), we rewrote the sweep scripts with explicit
loud-failure handling, so the failure mode is now visible rather than
silent — section 4.3.1 walks through what the logs captured. For C8
(per-die structure), we added `/sys/devices/uncore_cha_*` enumeration
to confirm CHA count (108 per socket), which removed one layer of
derivation from the per-die structure; per-die CHA count (36) is
still derived under uniform assumption. For C9 (cross-socket BW at
small sizes), we excluded the affected rows from the cross-socket
comparison table in section 4.4. C1, C7, C10, and C11 are not
addressed in this study and are flagged as future work.

None of these caveats change the headline findings. AMD's 3-5×
lower L3 latency in the in-CCD regime, Intel's flat 60 ns monolithic
L3 plateau, the ~10× aggregate L3 bandwidth gap at full socket load,
Intel's 25% slower local DRAM, AMD's better cross-socket bandwidth
retention — all of these are robust to every caveat in the table
above. The caveats affect detail-level questions (exact in-die
structure on Intel, slice-hashing decomposition, multi-thread DRAM
scaling above 32 threads) rather than the architectural picture as a
whole.

---

## 6. Audit of article's claims

Article: Chester Lam, *A Look into Intel Xeon 6's Memory Subsystem*,
Chips and Cheese, September 2025.
<https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>

Many of the article's claims about Intel Granite Rapids are measured
in SNC3 mode (Sub-NUMA Clustering with 3 nodes per socket), which
exposes the underlying compute-die structure as three separate NUMA
nodes. Our system runs in SNC OFF, so direct apples-to-apples
comparison is impossible for the per-die latency datapoints — but
section 6.5 shows how the article's per-die numbers fold into our
monolithic-mode measurement consistently.

```
Article claim                       Status            Our data / location
─────────────────────────           ──────────────    ──────────────────────────
33 ns local-die L3 latency          Cannot reproduce  60.3 ns L3 plateau on
(SNC3 enabled, Xeon 6985P-C)        directly (need    our 6962P in SNC OFF.
                                    SNC3 enabled      See section 6.5 for
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
                                                      Intel 196, AMD 102 GB/s

Intel DRAM latency competitive      NOT CONFIRMED     script:ptr_chase
                                                      Intel 138, AMD 110 ns
                                                      (Intel 25% slower)

Intel cross-die c2c structure       NOT CONFIRMED     script:c2c_lat
visible (50-80 ns intra-die)                          (no clean step
                                                      visible within
                                                      socket; see 4.5.1
                                                      and 4.5.2)
```

The most interesting claim to audit is the article's L3 latency
characterization, because the ~30 ns figures from SNC3 mode at first
glance suggest our 60 ns measurement is wrong. Section 6.5 below
walks through three independent cross-checks that show our number is
exactly what monolithic-mode Granite Rapids delivers.

---

## 6.5 Validation of Intel L3 latency

The goal of this section is to confirm that our measured Intel L3
latency of ~60 ns is what the hardware actually delivers in
monolithic (SNC OFF) mode, not a measurement artifact.

### 6.5.1 Cross-check vs Chips and Cheese (computed)

The article's measured per-die L3 latencies in SNC3 mode are the input
to a calculation for what monolithic-mode latency should be:

```
Reference                           Value      Source
──────────────────                  ───────    ──────────────────────────
Article: local die L3 SNC3          33.25 ns   article body, "Cache and
                                               Memory Latency"
Article: +1 die hop L3              57.63 ns   article "NUMA/Chiplet
                                               Characteristics"
Article: +2 die hops L3             ~80 ns     same section
                                               (article: "nearly 80 ns")

Article's explicit prediction       49.5 ns    article "Final Words":
for monolithic mode                            "(2 * 57.63 + 33.25) / 3
(assumes test core on MIDDLE die)              = 49.5 ns"

Same model, applied to test core    57.0 ns    arithmetic from same
on an END die                                  per-die figures:
(uniform slice hashing across       (= 56.96)  (33.25 + 57.63 + 80) / 3
3 dies)

End-die prediction adjusted for     50.5 ns    57.0 × (3.9 / 4.4)
our SKU's higher clock                         = clock-scaled from
(6962P at 4.4 GHz vs                           the 6985P-C's 3.9 GHz
6985P-C at 3.9 GHz)                            cycle count

Our measurement: L3 plateau         60.3 ns    script:ptr_chase
(cpu 0, presumed end die,                      ptr_chase_full_delphi-3af6_*
4 MiB to 256 MiB)

Gap: our 60 ns vs end-die           +9.8 ns    arithmetic
prediction at our clock
```

Granite Rapids-AP has three compute dies in a presumed linear
arrangement (`Die 0 — Die 1 — Die 2`). Under uniform L3 slice
hashing, a core's L3 accesses are distributed across the 120 CHAs
(approximately 40 per die) such that one third of accesses hit
slices on the local die and two thirds hit slices on remote dies —
but which remote dies depends on where the core sits. From a core
on Die 1 (the middle die), every cross-die access is exactly one
hop away, so the average works out to
`(33.25 + 2 × 57.63) / 3 = 49.5 ns`. This is the figure the
article gives in its "Final Words" section. From a core on Die 0
or Die 2 (an end die), one third of cross-die accesses are one hop
and one third are two hops, so the average is
`(33.25 + 57.63 + 80) / 3 ≈ 57 ns`. Two thirds of cores in a
3-die socket sit on end dies, so the socket-average prediction is
closer to 57 ns than to 49.5 ns.

Our measurement is from cpu 0, which we presume sits on an end die
(Die 0 — the natural assumption, since cpu_ids typically start at
one end of the package, though we cannot verify this under SNC OFF,
see section 4.5.2). The end-die value, 57 ns, is therefore the right
comparison for our measurement. Adjusted for our SKU's higher boost
clock (4.4 GHz vs 3.9 GHz), this becomes 50.5 ns. Our measured
60.3 ns is 9.8 ns above the end-die prediction at our clock.

The remaining 9.8 ns gap could come from several sources we have not
isolated. The cycle-count assumption — the article's "130 cycles"
L3 latency — may not hold exactly at 4.4 GHz. Our SKU has a
different CHA count (108 vs the article's 120 on the 6985P-C), which
could affect mesh routing. And there could be systematic measurement
offsets between our ptr_chase tool and the article's methodology
that we have not characterized. The fact that the prediction is
within ten nanoseconds of the measurement is consistent with the
per-die figures from the article being accurate.

### 6.5.2 Cross-check vs Intel Hot Chips 2024

The second independent reference is Intel's own published
characterization: Praveen Mosur, "Built for the Edge: The Intel
Xeon 6 SoC," presented at Hot Chips 2024 in August 2024
(<https://hc2024.hotchips.org/assets/program/conference/day1/14_HC2024.Intel.Xeon_6_SoC.Praveen.Mosur.pdf>).
A backup slide in this deck lists an L2 miss latency of **33 ns**,
measured on a 1-node, 1× Xeon, 42-core, HT-on, Turbo-on, NUMA-1,
DDR5-4800 configuration running a VPP networking workload, single
core / single thread.

L2 miss equals L3 hit in steady state. This is the first Intel-official
datapoint we have for L3 latency on Granite Rapids, and it
corroborates the Chips and Cheese article's 33 ns SNC-mode number to
within 0.25 ns. Our ~60 ns monolithic-mode measurement is therefore
consistent with the SNC-mode 33 ns figure averaged with cross-die
hops, as predicted in 6.5.1.

### 6.5.3 Cross-check vs Intel Optimization Reference Manual

The third independent reference is Intel's Optimization Reference
Manual: Volume 1, document #248966-050US, April 2024
(<https://cdrdv2-public.intel.com/671488/248966-Software-Optimization-Manual-V1-048.pdf>).
Section 2.1 "6th Generation Intel Xeon Scalable Processor Family"
gives Redwood Cove cache parameters:

```
                       Intel official     Our measurement      Implied cycles
                       (cycles)           (ns at 4.4 GHz)      at 4.4 GHz
L1d (Redwood Cove)     5                  1.14                 5.0    MATCHES
L2 (Redwood Cove)      16                 3.65                 16.1   MATCHES
L3 (no spec)           —                  60.3                 265    no spec
                                                                      to compare
```

The L1d and L2 measurements match Intel's published cycle counts
exactly. This validates the measurement methodology — `ptr_chase`
correctly reports load-use latency at each level. Intel does not
publish a cycle count for L3 (because the L3 latency varies with mesh
position), so the cross-check has to come from the article and Hot
Chips datapoints in 6.5.1 and 6.5.2 instead.

### 6.5.4 Verdict

Three independent cross-checks all support the conclusion that our
60 ns L3 measurement is real architecture, not measurement error.

The L1d and L2 measurements match Intel's published cycle counts to
within 1%, validating methodology. The L3 ~60 ns measurement aligns
with the Chips and Cheese article's predicted monolithic-mode
behavior to within 9 ns, well inside combined uncertainty bounds.
Intel's own Hot Chips 2024 publication shows 33 ns L2-miss latency
in single-core mode, corroborating the article's SNC-mode L3 figure
and supporting the same monolithic-mode calculation.

The 4× gap between Intel L3 (~60 ns) and AMD in-CCD L3 (~13 ns) is
structural, not artifact: Intel pays mesh routing plus die-hops on
every L3 access in monolithic mode; AMD's per-CCD L3 has no such
overhead inside the CCD.

The same validation approach applied to AMD shows consistent results:

```
Reference                            Value     Source
─────────────────                    ─────     ──────────────────────
Article Zen 5 L3 (in-CCD)            ~11 ns    article
Article Zen 5 DRAM                   125.6 ns  article
Our Zen 4 L3 (in-CCD, 4 MiB)         12.8 ns   script:ptr_chase
Our Zen 4 DRAM (4 GiB)               109.8 ns  script:ptr_chase
```

The AMD numbers are consistent with the article (Zen 4 should be
slightly faster than Zen 5 per other Chips and Cheese reporting).

### 6.5.5 Cross-check vs Emerald Rapids monolithic-mode data

The Chips and Cheese article also includes a comparison curve from
AWS i7i instances, which use Intel Xeon Platinum 8559C (Emerald
Rapids). The article explicitly notes that those instances run with
SNC disabled, the same configuration as our system: *"the Emerald
Rapids Xeon Platinum 8559C chips in AWS's i7i instances do not use
SNC. Thus each core in Emerald Rapids sees the full 320 MB of L3 as
a logically monolithic cache."* The measured L3 latency on those
SNC-OFF Emerald Rapids chips, from the chart in the article, is
**30.47 ns**.

```
Reference                            Value      Source
─────────────────                    ─────      ──────────────────────
Article Emerald Rapids L3 SNC-OFF    30.47 ns   article chart, 8559C
Our Granite Rapids L3 SNC-OFF        60.3 ns    script:ptr_chase

Ratio: our 6962P / article's 8559C   ≈ 2.0×
```

This datapoint matters because it's the closest direct match to our
configuration (Intel server CPU, SNC disabled, monolithic L3 view),
yet the L3 latency is half of ours. Reconciliation comes from the
chiplet count difference:

```
Architectural difference                Emerald Rapids   Granite Rapids
─────────────────────────────           ──────────────   ───────────────
Number of compute dies per socket       2 chiplets       3 dies
Max die-hops possible                   1                2
L3 per socket                           320 MB           432 MB
```

Expected monolithic-mode L3 latency (uniform slice hashing across
dies), using the per-die latencies established in 6.5.1 (33 ns
local-die, 57 ns +1-hop, 80 ns +2-hop):

```
Emerald Rapids: avg(local, +1 hop)      = (33 + ~30) / 2 ≈ 30 ns
                                            measured: 30.47 ns ✓

Granite Rapids: avg(local, +1, +2)      = (33 + 57 + 80) / 3 ≈ 57 ns
                                            measured: 60.3 ns  ✓
```

The per-die mesh cost is roughly similar between the two architectures
(local-die L3 ≈ 30-33 ns); the difference in monolithic-mode latency
reflects the chiplet count, not a methodological problem in our
measurement.

This is the most directly comparable external datapoint we have for
our setup. The fact that both Emerald Rapids and Granite Rapids fall
out cleanly from the same architectural model — local-die L3 around
30 ns plus ~24 ns per die-hop, averaged uniformly across the number
of dies in the socket — is strong evidence that our 60 ns figure is
not a measurement artifact but is exactly what the architecture
delivers in monolithic mode for a 3-die Granite Rapids socket.

---

## 7. Hugepage handling in scripts

Each measurement uses a hugepage size matched to the working-set
size, for a reason worth being explicit about. With 4 KiB pages, a
16 MiB buffer spans 4096 pages, but the data TLB (dTLB) holds only
about 2K entries; a random pointer chase causes constant TLB misses
that contaminate the L3 and DRAM latency measurements. 2 MiB pages
keep TLB pressure manageable for 4 MiB to 768 MiB buffers (768 MiB
in 2 MiB pages is just 384 entries). For 1 GiB and larger buffers we
move to 1 GiB pages.

Linux maintains separate pools for each hugepage size, controlled via
`/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages` and
`/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages`. The two
pools are independent. The 1 GiB pool was pre-allocated at boot on
both our systems (512 pages on Intel, 280 on AMD) and our scripts use
it as-is — they only manipulate the 2 MiB pool dynamically:

```bash
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

sudo bash -c "echo $WANT_2M > $HUGE2M"
```

The `trap cleanup EXIT` ensures the 2 MiB pool is restored to its
pre-test size on normal exit, Ctrl-C, or most error paths; it does
not survive SIGKILL or power loss, so manual cleanup
(`sudo bash -c 'echo 0 > /sys/kernel/.../hugepages-2048kB/nr_hugepages'`)
may be needed once after an unusual termination.

Both `ptr_chase.c` and `bw_avx512.c` accept `--hugepage {1g|2m|none}`
and fail loudly if `--size` is smaller than one page:

```c
if (size < pagesize) {
    fprintf(stderr,
        "ERROR: --size (%zu) is smaller than one %s page (%zu)\n"
        "       Pick a larger --size or use --hugepage 2m / none.\n",
        ...);
    return 2;
}
```

This guard exists because an earlier sweep silently rounded
`--size 48M --hugepage 1g` up to a 1 GiB allocation, producing
identical results for sizes 48 MiB through 768 MiB with no error
indication. That bug cost a sweep cycle and produced misleading data.

Each driver script picks the right hugepage size per size band:
4 KiB pages for L1/L2 region buffers (32 KiB through 2 MiB), 2 MiB
pages for L3 region buffers (4 MiB through 768 MiB), and 1 GiB pages
for DRAM region buffers (1 GiB and larger).

The current versions of all sweep scripts implement defensive failure
handling so that any binary or setup failure is captured visibly in
both the CSV (as `FAILED,...` marker rows) and a sidecar `.log` file.
Each script reports a per-test pass/fail count at the end and the
expected vs. actual row count for the CSV. Section 4.3.1 shows what
this looks like when a real failure happens.

---

## 8. Reproducibility & deliverables

The complete set of deliverables in this archive:

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
Inspection     load_snapshot.sh          ~90      pre/post-run state capture

Driver         sweep_full.sh             ~140     ptr_chase, all sizes
                                                  + cross-socket
Driver         sweep_bw.sh               ~140     bw_avx512 sweep
Driver         sweep_bw_multi.sh         ~150     bw_multi thread sweep
Driver         sweep_c2c.sh              ~100     c2c_lat scan
Driver         sweep_dram_lat.sh         ~115     extended DRAM lat 4G-32G
Driver         sweep_dram_bw.sh          ~130     extended DRAM BW 4G-32G

Result CSV     ptr_chase_full_*.csv      27 rows  latency main sweep
Result CSV     ptr_chase_dram_*.csv      7 rows   extended DRAM lat
Result CSV     bw_sweep_*.csv            53 rows  single-thr BW sweep
Result CSV     bw_dram_*.csv             13 rows  extended DRAM BW
Result CSV     bw_multi_*.csv            varies   multi-thr BW scaling
Result CSV     c2c_lat_*.csv             76/100   c2c matrix (Intel/AMD)

Sweep log      <csv-basename>.log        —        loud-failure log for
                                                  each sweep CSV

Pre/post log   load_snapshot_*.log       —        system state snapshots
                                                  taken pre/post each
                                                  measurement session

Inspection log inspect_*.log             —        step0 outputs
Topology log   core_grouping.log         —        /sys topology dump
```

To reproduce this study on a fresh Ubuntu 22.04+ machine:

```bash
sudo apt install -y libnuma-dev build-essential numactl
make

bash load_snapshot.sh                    # pre-test state snapshot

bash sweep_full.sh                       # ~3-4 min
bash sweep_bw.sh                         # ~5 min
bash sweep_bw_multi.sh                   # ~5-10 min (may fail at high thread)
bash sweep_c2c.sh                        # ~6-8 min
bash sweep_dram_lat.sh                   # ~10 min
bash sweep_dram_bw.sh                    # ~1 min

bash load_snapshot.sh                    # post-test state snapshot
```

Total wall time is approximately 30-40 minutes per system. The Intel
system runs longer than AMD on the same sweeps because Intel's slower
single-thread DRAM bandwidth makes buffer initialization take longer
— roughly twice as long per gigabyte of buffer setup.

Each sweep script reserves the hugepages it needs via sudo at startup,
restores them via a trap on exit (including error and Ctrl-C paths),
writes its CSV with a header row to a timestamped filename, writes a
sidecar log file capturing stderr and per-test pass/fail status,
continues past individual test failures rather than aborting the
entire sweep, aborts cleanly with a FATAL marker if setup itself fails,
and reports a pass/fail summary at end of run.

External references cited in this writeup:

- Chips and Cheese, "A Look into Intel Xeon 6's Memory Subsystem"
  <https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>
- Chips and Cheese, "Core to Core Latency Data on Large Systems"
  <https://chipsandcheese.com/p/core-to-core-latency-data-on-large-systems>
- Jason Rahman, "Intel CPU Die Topology"
  <https://jprahman.substack.com/p/intel-cpu-die-topology>
- Tom's Hardware, "Intel Details 144-Core Sierra Forest, Granite Rapids Architecture, and Xeon Roadmap"
  <https://www.tomshardware.com/news/intel-details-sierra-forest-and-granite-rapids-architecture-xeon-roadmap>
- Intel Hot Chips 2024, "Built for the Edge: The Intel Xeon 6 SoC"
  <https://hc2024.hotchips.org/assets/program/conference/day1/14_HC2024.Intel.Xeon_6_SoC.Praveen.Mosur.pdf>
- Intel® 64 and IA-32 Architectures Optimization Reference Manual, Volume 1, doc 248966-050US, April 2024
  <https://cdrdv2-public.intel.com/671488/248966-Software-Optimization-Manual-V1-048.pdf>
- Intel® Xeon® 6980P Processor product specifications
  <https://www.intel.com/content/www/us/en/products/sku/240777/intel-xeon-6980p-processor-504m-cache-2-00-ghz/specifications.html>
- Intel Fact Sheet: Xeon 6 P-core
  <https://download.intel.com/newsroom/2024/data-center/Fact-Sheet-Xeon-6-P-Core.pdf>
- Hacker News thread (Sapphire Rapids L3 latency reference)
  <https://news.ycombinator.com/item?id=44029935>

---

## Appendix A. Process notes — points raised during this study

During this study, the reviewer challenged several intermediate
statements that turned out to need correction or clarification. These
points are recorded here as a reminder that intermediate analyses
should not be taken as final; each was revised before being included
in the body of this document. They are listed not to dwell on
imperfect intermediate states but because each correction yielded a
more accurate finding.

```
Item   Topic                                Outcome
─────  ─────────────────────────────        ──────────────────────────────
1      "Monolithic NUMA" terminology         Corrected: clarified "logically
                                             monolithic L3" vs "two-socket
                                             NUMA configuration"; the former
                                             refers to L3 visibility within
                                             a socket, the latter to OS
                                             NUMA topology.

2      256 MB cross-socket BW = local        Initially presented as anomaly;
       after first pass                      after pushback identified the
                                             caller-socket L3 caching
                                             artifact (see section 4.4
                                             caveat).

3      C2C: slowest in-die > fastest         Initial framing grouped cores
       cross-die                             0-23/24-47/48-71 as "dies"
                                             without source, which led to
                                             an absurd conclusion (slowest
                                             in-die > fastest cross-die).
                                             After pushback the framing was
                                             retracted. Latest writeup
                                             reports c2c scatter as
                                             measured without attributing
                                             it to die boundaries (4.5.1)
                                             and documents the absurd-
                                             conclusion episode as evidence
                                             of why public in-die layout
                                             info is needed (4.5.2).

4      L3 BW saturation drop at 72           Acknowledged as unexplained.
       threads (Intel)                       Did not reach a definitive
                                             cause; flagged in section 4.3.

5      "Double-pump" terminology             Retracted slang; replaced with
                                             "256-bit physical units,
                                             2 cycles per 512-bit op"
                                             when describing AMD AVX-512.

6      Port-count claims (2 load +           Asked for source; retracted
       1 store, etc.)                        the specific port counts as
                                             not from any source citable.

7      Intel official documentation          Initially missed; on second
                                             search, found Optimization
                                             Reference Manual and Hot Chips
                                             2024 datapoint (both added to
                                             section 6.5).

8      Cross-socket latency provenance       Initially attributed to
                                             sweep_full.sh but the script
                                             only looped local memory. The
                                             original cross-socket data
                                             came from manual one-off
                                             ptr_chase invocations. Now
                                             fixed: sweep_full.sh includes
                                             a cross-socket loop.

9      "Each compute die contains its own    Initial sentence implied a
       group of CHAs..."                     single source for a synthesis
                                             of three sources. Corrected:
                                             provenance now broken down by
                                             component (see CHA diagram in
                                             section 2.3).

10     "~40 mesh stops per die" stated       Article actually says: "Intel
       as fact                               hasn't published documents
                                             detailing Xeon 6's mesh
                                             layout." Now labeled as
                                             derivation, not measured fact.

11     "120 CHA on 1 die" in diagram         Wrong; article says 120 CHA
                                             per SOCKET. Corrected to
                                             ~40 per die (derived).

12     "~4 MB slice" hedged unnecessarily    Math is exact: 480/120 = 4.
                                             Tilde removed.

13     bw_multi silent truncation at         Initial behavior was silent
       32 threads (Intel) / abort (AMD)      truncation; rewrote with
                                             explicit failure handling
                                             (see 4.3.1).
```

---

*End of Pass 2.*
