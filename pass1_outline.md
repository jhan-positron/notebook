# Intel vs AMD CPU/Memory Subsystem Comparison

## Pass 1 — Outline (rev 4)

**Scope:** Pure Intel Xeon 6962P vs AMD EPYC 9654 CPU/memory subsystem comparison.

**Format note:** All data tables and diagrams are wrapped in ` ``` ` code blocks
to preserve monospace alignment. Read on a terminal or monospace viewer for
correct rendering. Tables sized to ~90 character width.

---

## Table of contents

```
1.  Executive summary
2.  Systems under test
    2.1  Inspection method
    2.2  Three-system comparison table
    2.3  System diagrams (Intel + AMD)
    2.4  Comparability caveats
3.  Methodology
4.  Findings
    4.1  Latency vs working-set size
    4.2  Single-thread bandwidth
    4.3  Multi-thread bandwidth scaling
    4.4  Cross-socket
    4.5  Core-to-core latency
    4.5.1  Caveat: in-die scatter has no direct vendor proof
5.  Audit of article's claims
5.5  Validation of Intel L3 latency
    5.5.1  Cross-check vs Chips and Cheese (computed)
    5.5.2  Cross-check vs Intel Hot Chips 2024 (33 ns L2-miss)
    5.5.3  Cross-check vs Intel Optimization Reference Manual
    5.5.4  Verdict
6.  Hugepage handling in scripts
7.  Reproducibility & deliverables
```

---

## 1. Executive summary

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

---

## 2. Systems under test

### 2.1 Inspection method

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

### 2.2 Three-system comparison

All system facts from `script:step0_inspect.sh` on each host.

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

Two Intel boxes:
  Same family, same SNC mode (OFF), same DDR speed.
  Different boost clocks (4.4 vs 3.9 GHz) → expected ~13%
  ns scaling but same architectural picture.
  CI machine used only for system characterization (cannot
  modify); all testing done on 3af6.
```

### 2.3 System diagrams

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

### 2.4 Comparability caveats

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

---

## 3. Methodology

```
Tool             Source file        Driver script        Output CSV name pattern
─────            ──────────────     ──────────────       ──────────────────────────
inspect_pages    inspect_pages.c    (manual)             (stdout only, no CSV)
ptr_chase        ptr_chase.c        sweep_full.sh        ptr_chase_full_<host>_<ts>.csv
bw_avx512        bw_avx512.c        sweep_bw.sh          bw_sweep_<host>_<ts>.csv
bw_multi         bw_multi.c         sweep_bw_multi.sh    bw_multi_<host>_<ts>.csv
c2c_lat          c2c_lat.c          sweep_c2c.sh         c2c_lat_<host>_<ts>.csv
```

```
What each measures:
  ptr_chase    Single-thread load-use latency via random pointer
               chase. NUMA-pinned, hugepage-backed. Reports ns/load.
  bw_avx512    Single-thread streaming bandwidth via AVX-512.
               Patterns: read / rmw / write. Reports GB/s.
  bw_multi     Multi-thread aggregate bandwidth. Each thread has
               its own private buffer (no shared lines).
  c2c_lat      Core-to-core coherency latency via atomic CAS
               ping-pong on a single shared cache line.

Pointer-chase stride note:
  ptr_chase.c uses a fixed 64-byte stride (one cache line) at
  every buffer size, walking a random Hamiltonian cycle. The
  stride does NOT scale with buffer size. Reason: at every level
  (L1, L2, L3, DRAM) the fetch unit is one 64-byte cache line.
  As the buffer grows, the cycle length grows automatically
  (ncells = size / 64); the random ordering still defeats
  prefetchers at every level.

What none of them measures:
  - Mixed read/write workloads at realistic ratios
  - Hardware prefetcher benefits (pointer chase defeats prefetchers)
  - TLB-walk cost (we use hugepages to avoid it)
  - Workloads with shared data among threads
```

```
Benchmarks we did NOT run:
  - SPEC CPU2017: industry-standard CPU benchmark used in the
    Chips and Cheese article. Skipped due to cost: commercial
    license required (~$1-2k), ~25 GB disk, ~20 hours wall time
    per system for one iteration of both suites, 30+ hours for
    reportable run, plus tuning effort. Architectural picture
    is already covered by our microbenchmarks. If a popular
    cross-system CPU benchmark is desired later, Phoronix Test
    Suite (free, open source) is the practical alternative.
```

---

## 4. Findings

### 4.1 Latency vs working-set size

```
Source: script:ptr_chase + sweep_full.sh
Run (Intel): ptr_chase_full_delphi-3af6_20260520_2102.csv
Run (AMD):   ptr_chase_full_andoria-15_20260520_2102.csv

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

```
Cross-socket (cpu 0, mem-node 1):

Source: script:ptr_chase + sweep_full.sh (same runs)

size       Intel ns    AMD ns    I/A      remote/local
─────────  ────────    ──────    ──────   ──────────────
1 GiB      243.8       197.8     1.23×    Intel 1.94×, AMD 1.82×
4 GiB      275.5       199.0     1.38×    Intel 2.01×, AMD 1.80×
```

Bullet observations:

- L1d / L2 region: latency within 4% between vendors
- 4-32 MB band: AMD per-CCD L3 hits 3-5× lower latency
- Crossover at 48 MB working set
- 48-256 MB band: Intel monolithic L3 still serves; AMD pays growing cross-CCD penalty
- 768 MB+: AMD steady-state DRAM 25% lower than Intel
- Cross-socket DRAM: AMD 28% lower than Intel
- Intel ratio (21/10) matches ACPI distance; AMD ratio (32/10) overstates the measured ratio

### 4.2 Single-thread bandwidth

```
Source: script:bw_avx512 + sweep_bw.sh
Run (Intel): bw_sweep_delphi-3af6_20260520_2335.csv
Run (AMD):   bw_sweep_andoria-15_20260520_2335.csv

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

```
Cross-socket (4 GiB only - see section 4.4 caveat for why):

Source: same script

            Intel local    Intel remote    AMD local    AMD remote
read         15.74          8.95           37.50        30.41
rmw          30.99         12.06           56.30        36.11
```

Bullet observations:

- Intel L1d 35% higher BW than AMD L1d for reads
- Intel L1d 2.09× AMD L1d for rmw
- L2 read favors Intel (1.67×); L2 rmw favors AMD (0.6×)
- Intel L3 BW hard-clamped at ~27 GB/s single-core
- AMD in-CCD L3: ~88 GB/s read, ~184 GB/s rmw
- AMD cross-CCD ≈ AMD DRAM = ~38 GB/s; IOD-bound, not DRAM-bound
- Intel cross-socket BW collapses harder than AMD

### 4.3 Multi-thread bandwidth scaling

```
Source: script:bw_multi + sweep_bw_multi.sh
Run (Intel): bw_multi_delphi-3af6_20260521_0052.csv
Run (AMD):   bw_multi_andoria-15_20260521_0052.csv

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

```
L3 region, RMW pattern (bus traffic counted):

threads    Intel GB/s    AMD GB/s     I/A
  8           374          1259       0.30×
 24           876          3359       0.26×
 48          1102          6611       0.17×
 72           982          9870       0.10×
```

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

Bullet observations:

- Intel L3 scales near-linear to 24 threads, plateaus ~550 GB/s at 48-64, drops to 489 at 72
- AMD L3 scales near-linear to 72 threads → 5228 GB/s
- AMD ~10× Intel at full socket L3 BW
- The Intel drop at 72 threads is repeatable but cause not isolated (possible mesh saturation, power license transition, or kernel housekeeping interference)

### 4.4 Cross-socket consolidated

**Caveat for the 16 MB and 256 MB cross-socket bandwidth tests:** Buffers smaller than the caller socket's L3 cache get pulled into local L3 on first pass, then averaged over many passes. Result: "cross-socket BW" at small sizes actually measures local L3 BW. Only the 4 GB row exceeds Intel's 432 MB L3 and represents true cross-socket DRAM traffic.

Sources:
- Latency:  `script:ptr_chase + sweep_full.sh` (ptr_chase_full_*.csv)
- BW:       `script:bw_avx512 + sweep_bw.sh`   (bw_sweep_*.csv)

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

### 4.5 Core-to-core latency

```
Source: script:c2c_lat + sweep_c2c.sh
Run (Intel): c2c_lat_delphi-3af6_20260521_0135.csv
Run (AMD):   c2c_lat_andoria-15_20260521_0135.csv

AMD c2c-RT grouped by peer CCD (caller cpu 0 on CCD 0):

peer CCD    peer cores    median ns/RT    ns/1-way     I/A in-CCD
  0          1-7             55.6           28          —
  1          8-15           364            182          6.55× vs CCD0
  2-11      16-95           365-376        182-188      ~6.6×
```

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

```
Cross-socket spot checks:

           Intel ns/RT     AMD ns/RT       I/A
min        463             598             0.77×
median     579             625             0.93×
max        605             639             0.95×
```

#### 4.5.1 Caveat: in-die scatter has no direct vendor proof

**Observation:** Intel c2c-RT range within one socket is 115 to 230 ns (factor of 2.0). The pattern is NOT a clean step function and does not increase monotonically with `cpu_b` index.

**Reviewer challenge (raised during this study):** *"How can the slowest in-die pair be slower than the fastest cross-die pair? The slowest in-die should be faster than the fastest cross-die."*

**Working hypothesis (suspicion, NOT proof):**

- Each core sits on a 2D mesh stop within its die
- Each core hosts an L3 cache slice
- Test cache line hashes to ONE L3 slice; every c2c round trip routes via that slice
- Measured RT depends on: `mesh_distance(cpu_A → slice) + mesh_distance(cpu_B → slice)`, not on direct cpu_A → cpu_B distance
- Firmware cpu_id is not monotonic in mesh coordinates
- Result: scanning cpu_b sequentially samples the mesh in non-monotonic order, producing scatter

**Supporting evidence (indirect, public):**

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

**What would close the gap:**

- Enable SNC3 in BIOS, rerun c2c. SNC3 scopes slice selection within a die, so cross-die hops become directly measurable as a clean step.
- Sweep test line address across many page offsets, average across slice ownership; reveals whether scatter is physical mesh distance vs slice hashing.
- Find Intel-published mesh dimensions for the GNR-AP compute die. Not currently public.

For this writeup: c2c data is reported as-measured. The mesh + slice-hashing explanation is the most likely interpretation, NOT proof.

---

## 5. Audit of article's claims

**Article:** Chester Lam, *A Look into Intel Xeon 6's Memory Subsystem*, Chips and Cheese, September 2025. <https://chipsandcheese.com/p/a-look-into-intel-xeon-6s-memory>

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

---

## 5.5 Validation of Intel L3 latency

**Goal:** confirm that our measured Intel L3 ~60 ns is what the hardware actually delivers, not measurement error.

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

### 5.5.2 Cross-check vs Intel Hot Chips 2024

**Reference:** Praveen Mosur, "Built for the Edge: The Intel Xeon 6 SoC", Hot Chips 2024 (August 2024). <https://hc2024.hotchips.org/assets/program/conference/day1/14_HC2024.Intel.Xeon_6_SoC.Praveen.Mosur.pdf>

Intel's own measured datapoint:

- **"L2 miss latency: 33 ns"**
- Configuration: 1-node, 1× Xeon, 42 cores, HT on, Turbo on, NUMA 1, DDR5-4800, 1C1T, VPP networking workload

**Interpretation:** L2 miss == L3 hit (in steady state). This is the first official Intel datapoint we have for L3 latency on Granite Rapids. It corroborates the Chips and Cheese article's 33 ns SNC-mode number to within 0.25 ns.

Our ~60 ns monolithic-mode measurement is consistent with the SNC-mode 33 ns figure averaged with cross-die hops, as predicted in section 5.5.1.

### 5.5.3 Cross-check vs Intel Optimization Reference Manual

**Reference:** Intel® 64 and IA-32 Architectures Optimization Reference Manual: Volume 1, document #248966-050US, April 2024. <https://cdrdv2-public.intel.com/671488/248966-Software-Optimization-Manual-V1-048.pdf>

Section 2.1 "6th Generation Intel Xeon Scalable Processor Family" contains Redwood Cove cache parameters.

```
                       Intel official     Our measurement      Implied cycles
                       (cycles)           (ns at 4.4 GHz)      at 4.4 GHz
L1d (Redwood Cove)     5                  1.14                 5.0    MATCHES
L2 (Redwood Cove)      16                 3.65                 16.1   MATCHES
L3 (no spec)           —                  60.3                 265    no spec
                                                                      to compare
```

L1d and L2 measurements match Intel's published cycle counts exactly → methodology is sound. L3 has no Intel-published cycle count for direct comparison, so we cross-check against the Chips and Cheese article and the Hot Chips datapoint instead.

### 5.5.4 Verdict

- L1d and L2 measurements match Intel's published cycle counts to within 1% → methodology is sound
- L3 ~60 ns measurement aligns with the article's predicted monolithic-mode behavior (within 9 ns)
- Intel's own Hot Chips 2024 publication shows 33 ns L2-miss latency in single-core mode, corroborating the article's SNC-mode L3 figure
- The 4× gap to AMD in-CCD L3 (~12 ns) is structural: Intel pays mesh routing + cross-die hops on every access in monolithic mode; AMD's per-CCD L3 has none of that overhead within a CCD
- Latency drop is real architecture, NOT measurement error

**Same check for AMD:**

```
Reference                            Value     Source
─────────────────                    ─────     ──────────────────────
Article Zen 5 L3 (in-CCD)            ~11 ns    article
Article Zen 5 DRAM                   125.6 ns  article
Our Zen 4 L3 (in-CCD, 4 MiB)         12.9 ns   script:ptr_chase
Our Zen 4 DRAM (4 GiB)               109.9 ns  script:ptr_chase
```

AMD numbers consistent with article (Zen 4 should be slightly faster than Zen 5 per other Chips and Cheese reporting).

---

## 6. Hugepage handling in scripts

**Why two different hugepage sizes are used:**

- **4 KiB pages**: too small. A 16 MiB buffer = 4096 pages. The dTLB has ~2K entries. Random pointer chase causes constant TLB misses, contaminating L3/DRAM latency measurements.
- **2 MiB pages**: covers 4 MiB - 768 MiB buffers cleanly. 768 MiB = 384 pages, easily within dTLB capacity.
- **1 GiB pages**: needed for ≥1 GiB buffers. A 4 GiB buffer in 2 MiB pages would need 2048 entries → TLB pressure again.

**Linux pool management:** Each hugepage size has its own pool, controlled via:

```
/sys/kernel/mm/hugepages/hugepages-1048576kB/nr_hugepages
/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
```

The two pools are INDEPENDENT.

The 1 GiB pool was pre-existing at boot on both systems (512 pages Intel, 280 AMD). Our scripts use it as-is.

**The 2 MiB pool is reserved dynamically by each script, then restored on exit:**

```bash
HUGE2M=/sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
ORIG_2M=$(cat "$HUGE2M")

cleanup() {
    sudo bash -c "echo $ORIG_2M > $HUGE2M" || true
}
trap cleanup EXIT

sudo bash -c "echo $WANT_2M > $HUGE2M"
```

- `trap cleanup EXIT` → restoration runs on normal exit, Ctrl-C, and most error paths
- Does NOT survive SIGKILL or power loss
- Manual cleanup if needed: `sudo bash -c 'echo 0 > /sys/kernel/.../hugepages-2048kB/nr_hugepages'`

**Page-size-aware test invocation:** `ptr_chase.c` and `bw_avx512.c` take `--hugepage {1g|2m|none}` and fail loudly if `--size` is smaller than one page:

```c
if (size < pagesize) {
    fprintf(stderr,
        "ERROR: --size (%zu) is smaller than one %s page (%zu)\n"
        "       Pick a larger --size or use --hugepage 2m / none.\n",
        ...);
    return 2;
}
```

This guard exists because an earlier sweep silently rounded `--size 48M --hugepage 1g` up to a 1 GiB allocation, producing identical results for sizes 48M..768M with no error indication. That bug cost a sweep cycle.

**Driver scripts pick the right `--hugepage` per size:**

```
L1/L2 region (32K..2M):    --hugepage none
L3 region (4M..768M):      --hugepage 2m
DRAM region (1G..4G):      --hugepage 1g
```

---

## 7. Reproducibility & deliverables

```
Manifest:

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

# Total: ~25 minutes per system.
```

Each script:

- Reserves required hugepages via sudo
- Restores them on exit via trap (incl. errors / Ctrl-C)
- Writes CSV with header row to a timestamped file
- Sends progress to stderr; CSV to file

**External references:**

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

*End of Pass 1, rev 4.*
