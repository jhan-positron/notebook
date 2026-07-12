# SNC3 Pre-Measurement Predictions

Date: 2026-06-05
Host: delphi-3af6
Live mode to be measured: SNC3 (`/sys/devices/system/node/online = 0-5`)

This file was written before the SNC3 measurement pass. Goal thresholds are used
only as acceptance criteria, never as evidence for a predicted value.

## Evidence And Source Rows

| ID | Source | Row selector / fact | Value used | Role |
|---|---|---|---:|---|
| E1 | `results/snc-off/ptr_chase_delphi-3af6_20260603_2358.csv` | `phase=T1 pattern=read cpu=0 mem_node=0 size_bytes=4194304 hugepage=2m` | 60.535 ns | Same-machine SNC-OFF L3 prior |
| E2 | same | `phase=T1 pattern=read cpu=0 mem_node=0 size_bytes=67108864 hugepage=2m` | 60.646 ns | Same-machine SNC-OFF L3 prior |
| E3 | same | `phase=T1 pattern=read cpu=0 mem_node=0 size_bytes=4294967296 hugepage=1g` | 137.696 ns | Same-machine SNC-OFF local DRAM prior |
| E4 | same | `phase=T2 pattern=read cpu=0 mem_node=0 size_bytes=4294967296 hugepage=1g` | 137.728 ns | Same-machine SNC-OFF local-socket DRAM prior |
| E5 | same | `phase=T2 pattern=read cpu=0 mem_node=1 size_bytes=4294967296 hugepage=1g` | 276.871 ns | Same-machine SNC-OFF cross-socket DRAM prior |
| E6 | `results/snc-off/bw_avx512_delphi-3af6_20260604_0044.csv` | `cpu=0 mem_node=0 size_bytes=4294967296 hugepage=1g pattern=read/rmw` | 15.874 / 31.128 GB/s | Same-machine SNC-OFF local single-thread DRAM BW prior |
| E7 | same | `cpu=0 mem_node=1 size_bytes=4294967296 hugepage=1g pattern=read/rmw` | 9.000 / 18.794 GB/s | Same-machine SNC-OFF cross-socket single-thread DRAM BW prior |
| E8 | `results/snc-off/thread_scaling_delphi-3af6_20260604_0056.csv` | `regime=DRAM pattern=read nthreads=64/72` | 596.319 / 594.060 GB/s | Same-machine whole-socket-ish DRAM scaling prior |
| E9 | `results/snc-off/socket_sat_delphi-3af6_20260604_0101.csv` | `pattern=read nthreads=64/72` | 595.222 / 593.863 GB/s | Same-machine Test 11 endpoint prior |
| E10 | same | `pattern=rmw nthreads=24/72` | 641.305 / 480.763 GB/s | Same-machine Test 11 RMW peak and droop prior |
| E11 | `results/snc-off/loaded_lat_delphi-3af6_20260604_0059.csv` | `victim_ws=DRAM_1G bg_threads=0/23` | 126.587 / 146.890 ns | Same-machine loaded-latency prior |
| E12 | `results/snc-off/cat_delphi-3af6_20260604_0045.csv` | `cbm_hex=ffff/0001 size_bytes=134217728` | 61.242 / 131.626 ns | Same-machine CAT capacity-cliff prior |
| E13 | `results/snc-off/c2c_delphi-3af6_20260604_0045.csv` | `cpu_a=0 cpu_b in {1,5,11,23,24,47,48,71,72,96,120,143}` | 127.583 to 590.730 ns RT | Same-machine c2c physical-pair prior |
| E14 | `/sys/devices/system/node/node*/distance` via `numactl --hardware` | node0 distances | `10 15 17 21 28 26` | Runtime SNC3 topology evidence |
| E15 | DDR5-6400 channel arithmetic | `6400 MT/s * 8 B = 51.2 GB/s/channel` | 204.8 GB/s per 4-channel SNC node; 614.4 GB/s per 12-channel socket | Theoretical BW ceiling |
| E16 | `pre-work/intel-amd-comparison/pass2_writeup.md` | pass2 section 4.1 AMD row `4 MiB/4 GiB` and section 4.2 AMD local BW | 12.79 ns L3, 109.78 ns DRAM, ~38 GB/s DRAM read | AMD reference, not an SNC3 prior |
| E17 | `pre-work/intel-amd-comparison/pass2_writeup.md` | section 6.5.1 model: local/one-hop/two-hop L3 | 33.25 / 57.63 / ~80 ns | External topology-model sanity anchor |

## Shared Model

Topology:

- SNC3 exposes three NUMA nodes per socket: nodes 0,1,2 on socket 0 and nodes
  3,4,5 on socket 1.
- Each SNC3 node corresponds to one compute die with about 24 cores, 144 MiB of
  L3, and 4 DDR5-6400 channels.
- SNC-OFF node 0 represented the whole socket: three dies, about 432 MiB L3,
  and 12 channels interleaved.

L3 latency equation:

- Use the same-machine SNC-OFF L3 row E1 as the measured average for cpu0 over
  local, one-hop, and two-hop L3/home paths.
- Use the pre-work/article topology increment of roughly 24 ns per die hop:
  `57.63 - 33.25 = 24.38 ns`, `80 - 57.63 = 22.37 ns`.
- Solve for SNC3 local-die L3 from E1:
  `L_local ~= 60.535 - (0 + 24 + 48) / 3 = 36.535 ns`.
- Then predict adjacent and far die L3 as:
  `L_adjacent ~= 36.535 + 24 = 60.535 ns`;
  `L_far ~= 36.535 + 48 = 84.535 ns`.

DRAM latency equation:

- Treat same-socket SNC-OFF local DRAM E4 as an average over memory controllers
  across three dies.
- Use the same 24 ns per die-hop increment as a first-order mesh/EMIB penalty:
  `D_local ~= 137.728 - 24 = 113.728 ns`;
  `D_adjacent ~= 137.728 ns`;
  `D_far ~= 161.728 ns`.
- For cross-socket SNC3 rows, scale E5 by the ACPI-distance shape from E14,
  normalized to the node0 cross-socket mean: mean distances to nodes 3,4,5 are
  `(21 + 28 + 26) / 3 = 25`, so cpu0 cross predictions are
  `276.871 * 21/25 = 232.6 ns`,
  `276.871 * 28/25 = 310.1 ns`,
  `276.871 * 26/25 = 287.9 ns`.

Bandwidth equation:

- Single-thread streaming is core-loop limited before it is channel-count
  limited; use E6/E7 as the primary prior for Test 4.
- Multi-thread single-node DRAM is channel-count limited in SNC3:
  4 channels * 51.2 GB/s = 204.8 GB/s.
- Whole-socket `--local` bandwidth should recover the 12-channel endpoint:
  12 channels * 51.2 GB/s = 614.4 GB/s, with E9 showing the same-machine
  attainable value is about 594-595 GB/s.

General tolerance:

- Numeric prediction agreement target: within +/-10% unless a row explicitly
  states a wider range.
- Structural surprise threshold: wrong ordering, missing plateau, missing
  capacity cliff, or unexpected failure mode triggers gap analysis even if a
  single number is within tolerance.

## Predictions

| Prediction ID | Test | Metric | Evidence | Model / arithmetic | Assumptions | Predicted range | Tolerance | Acceptance threshold | Falsification trigger |
|---|---|---|---|---|---|---:|---:|---|---|
| P1 | Test 1 | `ptr_chase` T1, cpu0/mem0, 4 MiB and 64 MiB, read/rmw, 2M pages, median ns | E1, E2, E17 | `60.535 - 24 = 36.535 ns` local-die L3; 64 MiB fits inside 144 MiB SNC3 die L3 | cpu0 belongs to node0/die0; 2M pages available; cache residency holds through 64 MiB | 35-41 ns for read and rmw | +/-10% | `<=45 ns` for local L3 from `goal.md` | `>45 ns`, or values near 60 ns, means SNC3 is not isolating local L3 or page/cache placement is wrong |
| P2 | Test 2 | `ptr_chase` T2, CPUs 0/24/48 to nodes 0-5, 4 GiB, 1G pages, read/rmw | E4, E5, E14 | Same-socket: `local=137.728-24=113.7`, `adjacent=137.7`, `far=161.7`; cross cpu0: `276.871 * distance/25` | 4 GiB is DRAM; 1G pages avoid most TLB noise; ACPI distance captures cross-socket ordering better than magnitude | local 105-125 ns; same-socket adjacent 125-150 ns; same-socket far 145-175 ns; cross-socket 230-320 ns depending node | +/-15% | local SNC3 DRAM should be lower than same-machine SNC-OFF local 137.728 ns | local >= SNC-OFF local, or cross-socket ordering contradicts distance matrix |
| P3 | Test 3 | `ptr_chase` T3, cpu0 to nodes 0-5, 4 MiB and 64 MiB, read/rmw, 2M pages | E1, E2, E14, E17 | Mirror-die rule: nodes 0 and 3 use local-die L3 path `~36.5`; nodes 1 and 4 `~60.5`; nodes 2 and 5 `~84.5` | Test actually homes lines on the expected die; 4/64 MiB fit inside per-die L3 | node0/node3 35-41 ns; node1/node4 55-67 ns; node2/node5 76-93 ns | +/-10% | node0/node3 `<=45 ns` | mirror pairs differ by >10%, or all nodes collapse to ~60 ns |
| P4 | Test 4 | `bw_avx512`, cpu0 to each mem node, 4 GiB, 1G pages, read/rmw GB/s | E6, E7 | Single-thread local read/rmw inherit E6; cross-socket inherits E7; same-socket remote remains core-loop limited, not channel-limited | Streaming loop, not random; one thread cannot saturate 4 channels | same-socket read 14-18 GB/s, rmw 28-34 GB/s; cross-socket read 8-10.5 GB/s, rmw 17-21 GB/s | +/-10% | no formal pass threshold; compare apples-to-apples page mode | local read <12 GB/s or cross-socket read ~= local read without explanation |
| P5 | Test 5 | `c2c_lat`, cpu0 to partner CPUs, mem0, median ns round-trip | E13 | BIOS SNC mode should not materially change physical cache-line migration; use same partner-pair values with relabeling by SNC3 node | Same CPU IDs map to same cores after reboot; c2c is dominated by mesh/slice path and scheduling noise | same pairs within +/-15% of E13; cross-socket still about 450-600 ns RT | +/-15% | no formal pass threshold | systematic >20% shift for most pairs, or cross-socket faster than same-socket |
| P6 | Test 6 | CAT capacity sweep, cpu0/mem0, sizes 1-128 MiB, CBM ways | E12, E1, E15 | Effective per-die capacity under SNC3: `144 MiB * bits/16 = 9 MiB/bit`; latency floor changes from 60.5 to 36.5 ns; capacity cliff shifts from socket-L3 scale to die-L3 scale | resctrl L3 domains remain per socket but effective victim capacity is per die for cpu0/node0 | full/14-way floor 35-42 ns until near 126-144 MiB; 6-way cliff above ~54 MiB; 1-way cliff above ~9 MiB | +/-15% | CAT must show capacity sensitivity | no capacity cliff, or floor remains ~60 ns |
| P7 | Test 7 | `bw_multi` topology BW, 24 threads, mem-node0, 4/6/8/16/20 MiB per thread, read/rmw | E8, `bw_topology` SNC-OFF rows, E15 | Local die has 144 MiB L3 and 204.8 GB/s DRAM channel ceiling. 24*4M=96M fits; 24*6M=144M boundary; 24*8M=192M spills and may recruit DRAM in parallel | 24 threads are one per core; 2M pages available; mem-node0 is one die, not whole socket | A/local read 350-500 GB/s at 4-6M; just-over-L3 sizes may peak rather than drop; cross-die and mixed rows lower or noisier, broad 250-500 GB/s | +/-20% | must call out cache-capacity-boundary behavior | no inflection near 6-8 MiB, or single-node rows exceed whole-socket 12-channel ceiling |
| P8 | Test 8 | Big-buffer BW, 24 threads, 100/500/1000 MiB per thread, 4K pages, local node and cross-socket | E6, E7, E15, `results/snc-off/bigbuf_*.csv` | Local SNC3 node is 4 channels: ceiling `204.8 GB/s`; SNC-OFF local 24T 1G read was 287.754 GB/s because node0 was whole socket | Script substitution to mem-node2 is valid in SNC3; 4K page overhead applies uniformly | local read 175-220 GB/s; local rmw 330-430 GB/s; cross-socket read 160-210 GB/s; 1T read 14-25 GB/s depending size | +/-15% | no formal pass threshold | local read >300 GB/s implies the test is not constrained to one SNC node; local read <120 GB/s implies load/placement failure |
| P9 | Test 9 | Thread scaling, `bw_multi` cpus 0..N-1 to mem-node0, L3 4M/thread and DRAM 64M/thread | E8, E15 | DRAM single-node curve must plateau near 204.8 GB/s by 12-24T; L3 curve should show 24T die boundary and cache-boundary effects | Node0 conventional memory currently sufficient; 4K pages used for DRAM regime | DRAM read reaches 180-220 GB/s and stays near that, not 595 GB/s; L3 read scales to hundreds of GB/s and may peak just past L3 | +/-15% | plateau must be shown, not just peak | DRAM read >300 GB/s under single-node binding, or no visible 24T inflection |
| P10 | Test 10 | Loaded latency, victim cpu0->node0, DRAM 1G and L3 16M, bg K=0..23 to node0 | E11, P1, P2, E15 | SNC3 background uses only node0's 4 channels; queueing grows faster than SNC-OFF. Baseline DRAM follows P2 local, L3 follows P1 | Background threads run on same node; `bg_threads=23` is near a full die | DRAM baseline 105-125 ns; DRAM at K=23 roughly 200-400 ns; L3 baseline 35-45 ns and may rise to 60-120 ns under load | +/-25% for loaded points | qualitative: SNC3 loaded DRAM should degrade more than SNC-OFF E11 | K=23 no worse than SNC-OFF 146.890 ns, or L3 baseline near 60 ns |
| P11 | Test 11 | Socket saturation, `bw_multi --local`, socket0, 64M/thread, 4K pages, read/rmw | E9, E10, E15 | Endpoint should match 12-channel ceiling: expected `~595/614.4 = 96.8%` of theory; SNC3 shape steps as each die's local channels join | Memory-rich-node-first order may start on node2/node0/node1 depending runtime free memory | read: ~200 GB/s around first 24T group, ~400 GB/s around two die groups, 580-620 GB/s at 64-72T; rmw peaks 600-700 then may droop | +/-10% endpoint, +/-20% intermediate | read endpoint >=550 GB/s and saturation/flattening shown | 72T read <500 GB/s, or curve stays capped near 204 GB/s |
| P12 | Test 12 | Latency while Test-11-style socket BW is active; victim roles `saturated_core` and `remote_unused_core`; hugepage `none` and `1g`; includes `bg_nthreads=0` baselines | E9, E11, P2, P11 | Baseline 1G follows P2. `none` has extra TLB/page-walk cost, so predict 1.2x-3x 1G baseline. At high background N, remote-unused latency tracks memory queueing; saturated-core adds core execution contention | Test 12 reuses Test 11 core order and background shape; baseline comparison uses same victim CPU, mem node, working set, and hugepage mode | 1G baseline 105-125 ns; none baseline 150-350 ns; high-N remote-unused 180-350 ns; high-N saturated-core likely >= remote-unused and can exceed 300 ns | +/-25% | required rows exist for `hugepage=none` and `hugepage=1g`, including `bg_nthreads=0` baselines | missing baseline rows, missing `none` or `1g`, missing NA rows for unavailable remote-unused victims, or high-N latency not increasing at all |

## Assumptions

- The current live topology remains SNC3 for the entire pass.
- The user-provided same-machine SNC-OFF result folder is preserved and is the
  comparison half for this SNC3 pass.
- CPU numbering remains node0: 0-23, node1: 24-47, node2: 48-71, node3:
  72-95, node4: 96-119, node5: 120-143 for physical cores.
- 1G hugepages are available for 1G/4G pointer-chase and single-thread BW rows.
- The scripts may temporarily adjust the 2M hugepage pool and restore it on exit.
- CAT requires resctrl; if resctrl is not mounted, it should be mounted using
  the documented NOPASSWD allowlist.
- Shared-machine load can move bandwidth and loaded-latency rows. That is why
  loaded rows have wider tolerances than idle pointer-chase rows.
- AMD values from pre-work are only external reference context. The live
  SNC3-vs-SNC-OFF comparison uses same-machine Intel CSVs.

## Missing Opposite-Mode Prediction Coverage

The current SNC-OFF artifact set has no `latency_vs_socket_bw_*.csv` Test 12
file. After this SNC3 pass, Test 12 will therefore have SNC3 data only. The
final report must add a Todo to run the identical Test 12 script under SNC-OFF
unless a clean SNC-OFF Test 12 CSV is produced before report generation.
