# Design draft: the mesh latency map test for Asimov (program `meshmap`, script `run_map.sh`)

Wording rule for every text written for this project: never the word "hop"; a crosspoint-to-crosspoint
move is "a step", a load of a chain is "a load". (The file name measure-hop-latency.md is the user's.)

## Goal
For each measuring CPU and each of the five home nodes (HN-S, node ids 88, 160, 216, 288, 344), the
latency of one dependent load served by that node, for two kinds of line:
- OCM line (region n lives in node n; selected by address range; already measurable),
- SLC line (DRAM-backed line cached in that node's slice; selected by a hash of the physical
  address; NOT measurable today, because no code picks DRAM lines by home node).
Output: one CSV, cells = kind x CPU x node, 7 repeats each, with counters that prove where the loads went.

## Known facts (sources in scratchpad/understand/r1..r6.txt)
- Mesh 6 x 6. Home nodes at (1,3) (2,4) (3,3) (4,4) (5,3). Cluster ports: CPUs 0-1 (1,2), 2-3 (2,3),
  4-5 (3,2), 6-7 (4,3), 8-9 (5,2). Distances are 1, 3 or 5 steps.
- Each node: 1 MiB, 16 ways; 4 ways locked as OCM (256 KiB), 12 ways = 768 KiB for DRAM lines.
- DRAM address -> node: per-64-B-line hash over all five nodes, same in every requester (so the home
  node of a line does not depend on the CPU). Formula known from the Arm manual, not confirmed on the
  image; target-table order unknown; pagemap availability unknown.
- arm_cmn_0 PMU: per-node event hns_pocq_reqs_recvd_all (bynodeid config bit 31, nodeid bits 32-47),
  hns_cache_miss_all, hns_slc_sf_cache_access_all. 8 global counters (one DTC), 4 local counters per
  crosspoint. Events are system-wide on the PMU's CPU (cpumask = 0); a read from another CPU is a
  cross-CPU call. Groups allowed among arm_cmn events.
- DC CIVAC removes a DRAM-backed line from the SLC too (a flushed DRAM line reads from DRAM, 52.7 ns);
  on an OCM line it removes only the core-side copies (data stays in the home node).
- An unflushed 2 MiB chain walked once reads 23.9 ns with 0.998 L3D refills per load on boot B (L3
  off, prefetchers off): lines evicted from the cluster caches are found in the SLC.
- Cluster caches: L1D 32 KiB, L2 128 KiB, L3 256 KiB (L3 off or on by boot).
- Existing clean map: boot B and D dense per-region OCM rows fit 20.75 ns + 1.99 ns per X step +
  0.95 ns per Y step (rms 0.09 ns), 20 cells (CPUs 2,4,6,8).
- The CRB tool homelat.c (/home/jhan/workspace/titan/cache-perf/bench/homelat.c) classifies lines by
  per-node counters, then times fresh single-pass chains per node. It is CRB-specific by constants.
- Emulator: 2,779 wall s per chip s; hang guard at 12 chip s; programs run as root under SCHED_FIFO.
  256 huge pages of 2 MiB (hugetlbfs).

## Method
One new C program `meshmap.c` (uses common.h helpers), one process, one buffer, in this order:

1. Buffer: one 2 MiB hugetlb page (alloc_dram). Lower part = chain pool (default 768 KiB = 12,288
   lines), upper part = evictor pool (default 1 MiB = 16,384 lines). Filled once.
2. Classify the chain pool by counter (the CRB method, no hash assumed):
   - open one perf group of hns_pocq_reqs_recvd_all on the five nodes (5 of 8 global counters);
   - per line: load both neighbour lines, then `probe_loads` (default 64) times {DC CIVAC + DSB, load};
     read the group once per line (delta against the previous read);
   - rule: exactly one node rose by >= 3/4 of probe_loads and no other node by more than 1/4;
     otherwise retry (3), else the line is unused;
   - stop as soon as every node has `--lines` (default 2,048) lines; fail (exit 2) if the pool ends first
     or more than 5 % of probed lines are unusable;
   - verify: re-probe a sample (default 256 lines); fail under 98 % agreement;
   - self-calibration: time the first 32 probes, print the projected classification time, exit 2 if
     above `--max-classify-s` (default 4) so the run never meets the 12 s hang guard;
   - classification runs on `--classify-cpu` (default: the first measuring CPU).
   - optional record: /proc/self/pagemap frame number of the page (comment line, non-fatal when
     unreadable) and `--homes FILE` (line index, node), so the Arm hash formula can be checked offline.
3. OCM: mmap the five regions of /dev/ocm (existing alloc path); region n -> node n (88,160,216,288,344);
   chain = first `--lines` lines of the region. Skipped when /dev/ocm is absent.
4. For each node k (outer loop; per-node counters reopened per k): open
   hns_pocq_reqs_recvd_all on all five nodes + hns_cache_miss_all and hns_slc_sf_cache_access_all on
   node k (7 of 8 global counters, 3 of 4 local on k's crosspoint).
   For each CPU c in `--cpus` (pin with sched_setaffinity), for each kind, for rep r in 0..6:
   - chain r of the cell: Sattolo cycle over the cell's lines, pointer in 8-byte slot r of each line,
     new seed per (kind, node, rep); chains built before any timing;
   - kind `slc`: preload (independent loads of the chain's lines, random order) -> evict (independent
     loads of the evictor pool, new random order each rep) -> read counters -> start core counters ->
     clock -> chase n loads -> clock -> stop core counters -> read mesh counters;
   - kind `ocm-evict`: the same recipe on the OCM lines of node k (control: same recipe, other kind);
   - kind `ocm-flush`: DC CIVAC on the chain's lines + DSB, then the timed chase (the established OCM
     recipe; reproduces the boot B rows when run on boot B's firmware);
   - one `idle` row per node: the counters over an empty window, to give the background.
5. Row: `kind,cpu,node,lines,rep,ns_per_load,cycles_per_load,<6 core counters>_per_load,perf_cov,
   req_88,req_160,req_216,req_288,req_344,miss_node,access_node` (mesh columns are counts per load).
6. `--no-perf`: fake homes (line index mod 5), no mesh counters; lets the x86 host and a machine
   without the PMU run the whole flow. `--selftest`: checks the decision rule and the chain builder.

## Why a row is trusted (reading rules, to be written into the README)
- attribution: req_<k> per load near the idle-corrected 1.0 and the other four near 0;
- cache state: l3d_refill_rd (0xA2) per load near 1.0 (load left the cluster), prefetch refills 0 on a
  prefetchers-off boot, miss_node per load near 0 for slc (near 1 would mean DRAM fetch);
- repeatability: 7 repeats, median quoted, min and max kept.
- cross-check: `ocm-flush` cells on boot B's firmware against boot B's route rows (within 0.7 ns).
- hypothesis under test: per node, slc latency = ocm latency (the means agree: 23.90 vs 23.88 ns).

## CPUs
Default `--cpus 2,3,4,5,6,7,8,9` (partners share a port: a partner pair must agree). `run_map.sh
--kernel-cpus` appends CPU 0 (cluster at (1,2): adds a fifth position, 2 more cells at 5 steps), run
last, for Jesse's assessment (kernel CPU, L3 always on there, prefetcher hook skips it).

## Script and estimator
`run_map.sh` (phase M): M0 = sysinfo additions (CONFIG_PROC_PAGE_MONITOR, arm_cmn cpumask),
M1 = the one meshmap command. `--quick` = host subset with --no-perf. est_chip_time.py learns the
meshmap command. Makefile target. README rows. Nothing else in the existing phases changes.

## Boots to ask for (pf = core data prefetchers)
1. L3 off, pf off (boot B's firmware): the clean reference, reproduces the 20 known OCM cells.
2. L3 on, pf off (boot F2's firmware): no core row exists in this state.
3. optional: L3 on, pf on (boot F1's firmware): what the prefetchers do to the map.
These are three of the four boots of the pending run 7 request, so both scripts can share boots.

## Chip time, est.
Classification: about 11,300 lines x (64 x 60 ns + one counter read) = 0.05 to 0.2 s est. (the
cross-CPU read cost is not measured). Timed part: 8 CPUs x 5 nodes x 3 kinds x 7 reps x about 0.5 ms
(evictor 16,384 loads at 24 ns) = about 0.4 s est. Total under 1 s est. per boot (about 46 min of wall time).
