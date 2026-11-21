# The mesh latency map: context and changes (run 8)

## Short version

- A new program, `meshmap`, and a new script, `run_map.sh`, measure the time of one load from each CPU to each of the five home nodes of the Asimov mesh.
- The map has two kinds of line: OCM lines, and DRAM-backed lines held in one node's cache slice. The second kind was not measurable before, and it is the new part.
- The code builds and passes its self-test on x86 and on the CRB (aarch64). The code that reads the mesh counters has not run on real counters.

State: 2026-11-11. The code is uncommitted in the clone and copied to this folder. Nothing was sent to Jesse.

## Words used here

- **Mesh**: the on-chip network (Arm CMN S3) of 6 x 6 crosspoints that links the CPU clusters, the home nodes and the memory bridges.
- **Home node**: the mesh node that owns an address. Asimov has five (node ids 88, 160, 216, 288, 344). Each holds one slice of the mesh cache and one OCM region.
- **SLC**: the mesh cache (system level cache). Each home node holds a 1 MiB slice with 16 ways.
- **OCM**: on-chip memory. The firmware locks 4 of a slice's 16 ways (256 KiB) as a memory region with no DRAM behind it.
- **Cluster**: two CPUs that share one L2, one L3 and one mesh port. CPUs 2-3, 4-5, 6-7, 8-9 are the measured clusters. CPUs 0-1 run the kernel.
- **Step**: one move from a crosspoint to the next one. A distance is counted in steps.
- **Chain**: lines linked by pointers into one cycle. Each load gives the address of the next, so the loads cannot overlap.
- **Cell**: one (kind, CPU, node) combination. It gets 7 timed passes.
- **Classification**: finding the home node of each DRAM line with the per-node mesh counters.
- **Probe**: the test of one line: flush it and load it 64 times, then read the counters.
- **Evictor**: loads of other lines that push the chain's lines out of the cluster's caches into the SLC.
- **Bracket**: mesh counter read, core counters start, clock, timed loads, clock, core counters stop, mesh counter read.
- **DC CIVAC**: the Arm instruction that removes one line from the caches.
- **PMU**: performance monitoring unit. `arm_cmn_0` is the mesh's PMU.
- **CRB**: the Phoenix reference board, an Arm server with the same mesh driver. Its report is the reference for this work.
- **Boot B, F1, F2**: earlier emulator boots. B has the L3 off and the prefetchers off. F1 has both on. F2 has the L3 on and the prefetchers off.
- **est.**: an estimate from a model, not a measurement.

## 1. Context

Jibin asked for a distance and latency map of the Asimov mesh, like the one in the CRB report [Ref1]. The CRB map gives the latency from one CPU to each of the 64 slices of its mesh.

What the CRB tool does [Ref2]:

- It finds the home node of every line of a buffer with the per-node mesh counters.
- It then times chains built from the lines of one node only.

What Asimov has that the CRB does not:

- Five home nodes, not 64. Each holds a cache slice and an OCM region [Ref3].
- Every distance from a cluster to a home node is 1, 3 or 5 steps. No cluster shares a crosspoint with a home node [Ref3].

What the data on disk already give [Ref4]:

- **OCM, 20 cells.** CPUs 2, 4, 6, 8 against the five OCM regions. On boot B the 20 cells fit 20.75 ns + 1.99 ns per X step + 0.95 ns per Y step. The fit error is 0.09 ns (root mean square).
- **SLC, an average only.** A 2 MiB chain of DRAM-backed lines reads 23.9 ns on boot B from CPU 2. Its requests spread evenly over the five nodes, so it is a mean over the five slices.

What is missing:

- **SLC per node.** A DRAM line's home node is a hash of its physical address [Ref5]. No program on Asimov selects lines by node.
- **CPUs 3, 5, 7, 9.** No latency row exists from the second CPU of a cluster.
- **A clean row with the L3 on.** No core row exists with the L3 on and the prefetchers off.

## 2. What the new test measures

One row per timed pass of 2,048 dependent loads. Five kinds:

| Kind | Lines | Before each timed pass | What the load does |
|---|---|---|---|
| `ocm-flush` | OCM lines of the node | DC CIVAC on every chain line | served by the node's OCM region |
| `slc` | DRAM lines of the node | one store to every chain line, then the evictor | served by the node's cache slice |
| `dram-flush` | the same DRAM lines | DC CIVAC on every chain line | misses at the node, fetched from DRAM |
| `ocm-evict` | OCM lines of the node | the `slc` recipe | control: the `slc` recipe on lines known to stay in the node |
| `idle` | none | none | zero loads: the background of the counters |

- CPUs: 2, 4, 6, 8, then 3, 5, 7, 9. CPU 0 is optional and runs last (`--kernel-cpus`).
- Cells: 8 CPUs x 5 nodes x 4 kinds = 160, each with 7 passes, plus 8 idle rows.
- The step counts are not measured. They come from the crosspoint positions [Ref3].

## 3. Method

### 3.1 Finding the home node of a DRAM line

- The buffer is 2 MiB of addresses (32,768 lines). The program asks for one 2 MiB huge page and prints whether it got one (`# one_2mib_page: yes`, `not established` or `no`).
- A probe loads the two neighbour lines, then runs 64 pairs of DC CIVAC and load on the line, then reads the five per-node counters once (`hns_pocq_reqs_recvd_all`).
- Rule: the largest count must be at least 48 (3/4 of 64), and the second largest at most 1/4 of the largest. Otherwise the line is tried twice more, then left unused.
- The counts that one empty read adds to each node's request counter (the read floor) are measured first. They are subtracted from the per-node request counts only.
- The walk goes in address order and stops when every node has 2,048 lines. That is about 10,240 probed lines when the hash spreads evenly.
- The home node does not depend on the CPU, because the firmware programs every requester alike [Ref5]. One classification serves all CPUs.

No hash formula is assumed. The program records the buffer's frame number and each line's node (`map-homes.txt`). Arm's formula can be checked from them only when the run printed `# one_2mib_page: yes`. Otherwise the frame number covers the first 4 KiB page only, and the check is `Insufficient data`.

### 3.2 The `slc` recipe

1. The measuring CPU builds 7 chains over the cell's 2,048 lines (8-byte slots 0 to 6 of each line).
2. Store: one 8-byte store to slot 7 of every chain line, in a new random order.
3. Evictor: one independent load of every line of the page that is not in this chain (30,720 lines), in a new order.
4. Bracket with the timed chase.
5. Two untimed passes come first (four on the first CPU of a node), then 7 timed passes.

Why each part is there:

- **The store.** A store needs the line in the unique state. So a copy left in another cluster's caches by an earlier cell is invalidated, and the timed load cannot be answered by a snoop of that cluster.
- **The store, second reason.** DC CIVAC removes a DRAM line from the SLC too [Ref6]. Every existing SLC row used lines that were stored after their last flush. The store keeps that condition.
- **The evictor's size.** With the L3 on, a cluster holds 6,656 lines. An evictor of 30,720 lines leaves at most 0.3 % (est.) of the chain in the cluster.
- **One huge page only.** With Arm's hash and the default set index, one 2 MiB page puts at most 8 lines of one node in one SLC set, against 12 ways (arithmetic, not a measurement). This bound holds only when the run printed `# one_2mib_page: yes`. Without that line it is `Insufficient data`, and the `mc_reqs` column is the test of whether the slice kept the lines. The 2 MiB footprint equals the existing 2 MiB chain, which reads as SLC hits [Ref4].
- **The warm-up.** The classification flushes the lines to DRAM. The first passes refill the slices.

### 3.3 Order of work and failure handling

The emulator gives one chance per boot, and a guard kills the script after 12 chip seconds. So:

- The `ocm-flush` cells run first. They need no mesh counter and no classification.
- The mesh counters open at three levels: one group of the five per-node events plus three sums, then the five as a group, then the five alone. The program steps down by itself.
- A failed classification skips only the `slc` and `dram-flush` cells. The `ocm-evict` cells still run.
- The classification has a time budget of 1 chip second. The program lowers the lines per cell (2,048, 1,024, 512, 256) to fit, and it stops the walk at twice the budget.
- Two more stops: 64 invalid counter windows in a row, and no clear home in the first 256 probes at 256 pairs.
- Every row is appended to the file and flushed at once.
- The exit code is 1 when a requested cell is missing, or when a write to the row file or the homes file failed. `run_map.sh` counts that as a failed command and continues.
- A requested cell is one that can exist: a node id without an OCM region has no OCM cells.
- A failed write prints one line on stderr per file. The measurement still runs to its end.

## 4. Changes

Repository: `cache-mem-perf`, clone at `/home/jhan/workspace/ai-runs/asimov-repo`, on top of commit b85d975 (run 7, unpushed). The changes are uncommitted. The same files are copied to this folder.

| File | Change | SHA-256 prefix |
|---|---|---|
| `meshmap.c` | new, 1,846 lines: the program of sections 2 and 3, with `--selftest` and `--no-perf` | a0df4de1865ddfb3 |
| `run_map.sh` | new, 118 lines: phase M | 1e6526433664d2fc |
| `common.h` | +11 lines: the core counter set `perf_open_map` | 1e9befc4e1096d2e |
| `Makefile` | `meshmap` in `all` and `clean` | aac0835e5e5979e5 |
| `est_chip_time.py` | +78 lines: the cost of the `meshmap` command | c81f67005e853194 |
| `README.md` | +269 lines: terms, files, phase M rows, output format, reading rules, chip time | 83546e4958cd0cfb |
| `.gitignore` | +1 line: the `meshmap` binary (clone only) | - |

Unchanged: `latency.c`, `cmncount.c`, `lib_run.sh` and every other run script.

Points a reviewer may want to check first:

- **`meshmap.c` copies cmncount's sysfs event builder.** `cmncount.c` stays byte-identical, since ten boots of counted rows depend on it. The copy is marked in a comment.
- **Core counters.** The set is cycles, 0x03, 0x17, 0xA2, 0x81BC, 0x81BD and 0x05 (L1D TLB refill). 0x05 replaces 0x0111 of the default set, because the OCM chain covers 32 pages of 4 KiB and the DRAM chain one 2 MiB page.
- **Mesh counters.** They are opened once and never reopened: `hns_pocq_reqs_recvd_all` on each node, plus the sums `hns_mc_reqs_local_all`, `hns_cache_miss_all` and `hns_snp_sent`. That is 8 of the 8 global counters and 4 of the 4 local ones per crosspoint. Seven of eight and three of four are proven on the image [Ref7], so level 2 exists.
- **`meshmap` is never run under `cmncount`.** A second counter set would not fit.
- **OCM regions follow the node id.** Region 0 to 4 belong to nodes 88, 160, 216, 288, 344, whatever the order of `--nodes`. A node id outside that table gets the DRAM kinds only.

### 4.1 `run_map.sh`, phase M

1. Brings CPU 3 online. All of CPUs 2 to 9 stay online.
2. Writes `sysinfo-map.txt`: online CPUs, the kernel's `CONFIG_PROC_PAGE_MONITOR` line, the PMU's CPU.
3. Four control rows with the existing `latency` program: the dense flushed OCM chain from CPUs 2 and 8 on regions 0 and 4.
4. One `meshmap` command, which writes `latency-map.csv` and `map-homes.txt`.
5. Three summary lines on the console.

### 4.2 Row format of `latency-map.csv`

```
kind,cpu,node,lines,rep,ns_per_load,cycles_per_load,l1d_refill,l2d_refill,l3d_refill_rd,
l1d_refill_hwprf,l2d_refill_hwprf,l1d_tlb_refill,perf_cov,req_88,req_160,req_216,req_288,req_344,
mc_reqs,cache_miss,snp_sent,window_ns
```

- Core counter columns are counts per load.
- Mesh columns are counts per load of the bracket. The read floor is subtracted from the `req_<id>` columns only. The three sums (`mc_reqs`, `cache_miss`, `snp_sent`) carry no floor.
- An `idle` row holds raw counts in every mesh column, with no floor subtracted.
- The program applies no reading rule. It never drops a row.

## 5. How the rows are read

- **Attribution.** `req` of the cell's node minus the mean of the other four, per load. The other four are not near zero: the evictor's lines leave the cluster during the timed pass and go to their own nodes.
- **Cache state.** `l3d_refill_rd` per load near 1.0 means the load left the cluster. For `slc`, `mc_reqs` should be near the `ocm-evict` value of the same cell. A value near the `dram-flush` one would mean DRAM fetches.
- **Snoops.** Compare `snp_sent` with the idle row as raw counts: the measured row's per-load value times its `lines` is the raw count of its bracket. Read both `window_ns` values, since the two windows differ in length.
- **The floor.** Before comparing an idle row's `req` count with a measured row, subtract the node's `# read_floor` value from the idle count. The three sums are compared without a floor.
- **Hypothesis under test.** Per node, `slc` latency equals `ocm-evict` latency. The means on boot B agree: 23.90 ns for the 2 MiB chain, 23.88 ns for the mean of the five OCM rows [Ref4].
- **Cross-check.** The `ocm-flush` cells against the four `latency` control rows of the same boot, and against boot B's rows when the firmware is boot B's.
- **No thresholds yet.** "Near" has no number until the first boot gives the idle and control values.
- **A boot with the prefetchers on is not a distance map.** Its rows show the prefetchers' effect.

## 6. Verification

| Check | Result |
|---|---|
| x86 build, `-Wall -Wextra` | no warning |
| `./meshmap --selftest`, x86 | 47 of 47 checks pass |
| Mutation check: 42 single-rule breaks of `meshmap.c` (32 before review 1, 10 on its fixes) | the self-test fails on 42 of 42 |
| `--no-perf` runs, x86, with a stand-in file for `/dev/ocm` | 180 of 180 cells, 1,269 rows, 23 fields in every row |
| Run without the PMU, x86 | prints "no mesh counters", skips the DRAM kinds, finishes |
| Counter stand-in linked under `meshmap`, 7 modes | levels 1, 2, 3 and the no-counter path each reached; the two new stops reached |
| `sh run_map.sh --dry-run` | 5 commands |
| `sh run_map.sh --dry-run --kernel-cpus` | 5 commands, `--last-cpus 0` added |
| `sh run_map.sh --quick --dry-run` | 7 commands: the self-test, the `--no-perf` run, the `/dev/full` check and the four controls that every dry run lists |
| `sh run_map.sh --quick`, with and without `--kernel-cpus` | 0 failed commands |
| `--out /dev/full`, and `--homes /dev/full` | exit 1, one stderr line per file, all cells still run |
| `--nodes 344,288,216,160,88` against a stand-in file | every node on its own region, 0 of 20 OCM cells mislabelled (16 of 20 before the fix) |
| Estimator output for the five other scripts | byte-identical before and after |
| CRB (aarch64, GCC 14.2), `make` with the default flags | exit 0, no warning |
| CRB, `./meshmap --selftest` | 47 of 47 checks pass |
| CRB, `--no-perf` run on CPU 3 | 10 of 10 cells, `# one_2mib_page: yes` |
| CRB, `--out /dev/full` | exit 1 with the stderr line |
| CRB, run without `--no-perf` as a normal user | the event configuration is built from the real sysfs files, the open is refused ("Permission denied"), the run finishes |

Reviews before this document: three reviewers examined the design, five examined the code, and one verified the fixes. Their findings are folded in. Codex review 1 (R1 to R4) is applied; the replies are in `codex-review-measure-hop-latency.md`.

## 7. What is not verified

- **The mesh counter path on real counters.** The group open, the read from CPU 2 while the PMU is on CPU 0, the read floor and the probe counts have run only against a stand-in. The CRB needs root for them.
- **The count per flush-and-load pair on a DRAM line.** It is known for OCM lines only (0.6 to 1.0 per DC CIVAC, est.) and on the CRB (2.0 per pair) [Ref2][Ref7].
- **The cost of one counter read across CPUs.** 7 us est., from cmncount's timing rows [Ref7].
- **Whether `/proc/self/pagemap` gives the frame number on the image.** The run reports it.
- **The SLC's behaviour for one node's chain**: the set index, and whether the slice keeps 2,048 lines of the chain plus its share of the evictor. The `mc_reqs` column answers it.
- **Every `/dev/ocm` path of `meshmap`.** It ran against a file, not the device.
- **busybox `sh`.** `run_map.sh` was checked with `dash`.
- **The hugetlb case of the one-page check.** The x86 host and the CRB runs used transparent huge pages. The emulator reserves 256 pages of 2 MiB, so its runs take the hugetlb path, which prints `yes` from the allocator's label.
- **A host artifact.** On the x86 host, which is a virtual machine, about 3 % of rows carry a cycle count near 2^47. The CRB rows do not show it. It is not handled in the code.

## 8. Request planned for Jesse (after this review)

- **Step 1, a rehearsal.** One short command on CPU 2 with 64 lines per cell, about 0.06 s est. of chip time. Its files come back before the full run is queued. It answers the first four items of section 7.
- **Step 2, the full run.** `sh run_map.sh`, about 0.92 s est. of chip time per boot (about 43 min of wall time). A classification that runs to its stop makes it about 2.8 s est.
- **Boots, in this order:**
  1. L3 off, prefetchers off (boot B's firmware). The clean reference. It repeats the 20 known OCM cells.
  2. L3 on, prefetchers off (boot F2's firmware). No core row exists in this state.
  3. Optional: L3 on, prefetchers on (boot F1's firmware). The prefetchers' effect.
- These are three of the four boots of the pending run 7 request [Ref8]. On a shared boot `run_map.sh` runs last.
- **One question:** whether a timed test may run on CPU 0. Its cluster sits at crosspoint (1,2), a fifth position, and adds two cells at five steps.

## 9. Questions for the review

1. Is the `slc` recipe (store, evictor, bracket) a sound way to time a slice hit on one node? Which counter would show that it is not?
2. Is the classification rule safe against the counts that the read itself adds, at 64 pairs per probe?
3. Is the mesh counter layout (8 of 8 global, 4 of 4 local at level 1) worth the risk, given level 2 as the fallback?
4. Does any path still end the process, or loop, after the preflight?
5. Are the reading rules of section 5 enough to accept or reject a row?

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`, lines 220-236 (the distance map) and 714-733 (its chart).
- [Ref2] `/home/jhan/workspace/titan/cache-perf/bench/homelat.c`: `probe()` lines 370-411, `classify()` 425-517, `measure()` 736-761; run log `crb/results/sudo-20261102T054936Z/log.txt`.
- [Ref3] `results/membench-jibin-011/results/bootF1/sysinfo.txt` lines 489-551 (the mesh map); `results/membench-jibin-002/README.md` lines 28-35, 57-65, 80 (clusters, node ids, slice size, counter limits).
- [Ref4] `results/membench-jibin-006/results/bootB/latency-ocm-region*-route-cpu*.csv` (the 20 cells) and `latency-dram-large.csv` (the 2 MiB chain); `cmn-counts.csv` of 004 and 011, labels `dram-slc-2M-cpu*` (even spread over the nodes).
- [Ref5] Arm CMN S3 manual, document 107858, the hashed target group and its hash; SCP source `asimov_physical_sam.c` lines 552-602 (one hashed region and one 5-entry target table for every requester).
- [Ref6] `README.md` lines 119-123; `results/membench-jibin-006/results/bootB/latency-dram-flushed.csv` (52.7 ns flushed).
- [Ref7] `results/membench-jibin-011/results/bootF1/cmn-counts.csv` lines 2-21, 149-154; `results/membench-jibin-002/README.md` line 35.
- [Ref8] `message-to-jesse-round6.md` (the run 7 request, not sent as far as the files show).

Ready for review (after codex review 1): `meshmap.c` SHA-256 a0df4de1865ddfb3, `run_map.sh` SHA-256 1e6526433664d2fc (prefixes; the full list is in section 4).
