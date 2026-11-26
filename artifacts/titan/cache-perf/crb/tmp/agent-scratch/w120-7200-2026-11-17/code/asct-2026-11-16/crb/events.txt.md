# `events.txt` explained, line by line

- Source file: `asct-2026-11-16/crb/events.txt` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 7 lines, 773 bytes).
- sha256 of the source when this page was built: `11cc29a4d89acdb7ce162a0e7a3fcfe4c5582d148aa55e204d53dec50804aa2f`.

## Short version: purpose

`events.txt` lists the counter events of the cores for the counted runs of the ASCT cross-check: 7 sets of 7 event names. The script `prep.sh` gives the file to `resolve_events.py`, which writes the same sets with raw codes to the file `events.codes`. The run scripts read `events.codes` and count one set per process.

## Words used here

- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter unit of the cores**: the name under which Linux shows the counters of the cores, `armv8_pmuv3_0`. The event names of this file belong to it.
- **Event set**: a named list of counter events that one process counts together.
- **Raw code**: the number that selects one counter event of a counter unit.
- **L1, L2**: the first and the second cache level of a core. Each core has its own.
- **Last cache level**: the cache level after which a miss goes to memory.
- **Refill**: one cache line that enters a cache from the next level or from memory.
- **Long-latency miss**: a load that had to wait for its line. A load whose line was prefetched in time is not counted.
- **Hardware prefetch**: a request for a cache line that the core makes on its own, before the program asks for the line.
- **Software preload**: a prefetch instruction in the program.
- **Write-back**: a cache line that a cache passes on to the next level.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy.
- **TLB**: the cache of a core for address translations.
- **Stall cycle**: a cycle in which the core issues no new operation.
- **Frontend, backend**: the frontend of a core fetches and decodes instructions. The backend executes them.

## Main flow

1. Read each line as one event set. The text in front of the `|` is the set name, a letter from `A` to `G` (lines 1 to 7).
2. Read the text after the `|` as a list of event names with commas between them. The names are those of the counter unit of the cores.
3. Each set starts with `cpu_cycles` and holds 6 more events. By the decisions file a set has at most 6 events plus `cpu_cycles`. Then no event shares a counter [Ref2].
4. `resolve_events.py` keeps every line that holds a `|`. It takes the set name and the names and looks up the raw code of each name. It writes one line per set to `events.codes`, in the form `SET|name=0xCODE,...`.
5. The run scripts read `events.codes`. They put the set name into the tag and into the file names of the process. They pass the codes of the set to the probe binary in the environment variable `DIETPERF_PMUv3`, in the order of the line.

## Behavior a reader must know

- A name that `resolve_events.py` cannot resolve is left out of the set in `events.codes`. In the run of 2026-11-16 all 43 names were resolved [Ref3].
- Three scripts read `events.codes`: the smoke test of `prep.sh`, the parts C and NC of `run_single.sh`, and the step `CNT` of `run_chip.sh`. Part NC uses the sets `A`, `B` and `E` only.
- The short meaning of each event in the rows comes from the event list that `perf` printed on CRB [Ref1]. The file itself holds only names.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/events.txt` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (7 lines, 773 bytes, sha256 `11cc29a4d89acdb7ce162a0e7a3fcfe4c5582d148aa55e204d53dec50804aa2f`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `A\|cpu_cycles,inst_retired,l1d_cache_refill,l2d_cache_refill,l1d_cache_lmiss_rd,l2d_cache_lmiss_rd,ll_cache_miss_rd` | Set `A`: the basic counts. The text in front of the `\|` is the set name. `resolve_events.py` copies it to `events.codes`, and the run scripts put it into the names of their output files. After it stand 7 event names with commas between them. `resolve_events.py` writes each name for which it finds a raw code as `name=0xCODE`. `cpu_cycles`: cycles. `inst_retired`: instructions executed. `l1d_cache_refill` and `l2d_cache_refill`: refills of the L1 and of the L2 data cache. `l1d_cache_lmiss_rd` and `l2d_cache_lmiss_rd`: long-latency read misses of these two caches. `ll_cache_miss_rd`: read misses of the last cache level [Ref1]. |
| 2 | `B\|cpu_cycles,l1d_cache_hwprf,l2d_cache_hwprf,l2d_cache_l1hwprf,l2d_cache_refill_l1hwprf,l1d_cache_refill_outer,l1d_cache_refill_inner` | Set `B`: the hardware prefetchers. `cpu_cycles` again, as in every set. `l1d_cache_hwprf` and `l2d_cache_hwprf`: hardware prefetches of the L1 and of the L2 data cache. `l2d_cache_l1hwprf`: accesses to the L2 cache that an L1 hardware prefetch causes. `l2d_cache_refill_l1hwprf`: L2 refills that an L1 hardware prefetch causes. `l1d_cache_refill_outer` and `l1d_cache_refill_inner`: L1 refills of the two kinds that `perf` names outer and inner [Ref1]. |
| 3 | `C\|cpu_cycles,bus_access,bus_access_rd,l2d_cache_wb,l2d_cache_wb_victim,l2d_cache_wb_clean,l1d_cache_wb` | Set `C`: bus accesses and write-backs. `bus_access`: bus accesses. `bus_access_rd`: bus accesses that are reads. `l2d_cache_wb`: write-backs of the L2 data cache. `l2d_cache_wb_victim`: its write-backs of a victim line. `l2d_cache_wb_clean`: its write-backs for cleaning and coherency. `l1d_cache_wb`: write-backs of the L1 data cache [Ref1]. |
| 4 | `D\|cpu_cycles,l2_chi_cbusy0,l2_chi_cbusy1,l2_chi_cbusy2,l2_chi_cbusy3,l2_chi_cbusy_mt,bus_cycles` | Set `D`: the busy level that the core receives. `l2_chi_cbusy0` to `l2_chi_cbusy3`: responses that arrive with a busy level (`CBusy` in the text of `perf`) of 0, 1, 2 or 3. `l2_chi_cbusy_mt`: responses that arrive with the multi-threaded flag of the busy level set. `bus_cycles`: bus cycles [Ref1]. |
| 5 | `E\|cpu_cycles,stall_backend_mem,stall_backend_l1d,stall_backend_l2d,stall_backend_membound,stall_backend,stall_frontend` | Set `E`: stalls of the core. `stall_backend_mem`: memory stall cycles. `stall_backend_l1d` and `stall_backend_l2d`: backend stall cycles for the L1 and for the L2 data cache. `stall_backend_membound`: backend stall cycles that are memory bound. `stall_backend`: no operation is issued, due to the backend. `stall_frontend`: no operation is issued, due to the frontend [Ref1]. |
| 6 | `F\|cpu_cycles,dtlb_walk,l1d_tlb_refill,l2d_tlb_refill,l1d_cache_rd,l2d_cache_rd,ll_cache_rd` | Set `F`: address translation and read accesses. `dtlb_walk`: data accesses that cause a walk of the translation tables. `l1d_tlb_refill` and `l2d_tlb_refill`: refills of the L1 and of the L2 data TLB. `l1d_cache_rd` and `l2d_cache_rd`: read accesses to the L1 and to the L2 data cache. `ll_cache_rd`: read accesses to the last cache level [Ref1]. |
| 7 | `G\|cpu_cycles,l1d_cache_prfm,l2d_cache_prfm,l1d_cache_refill_prfm,l2d_cache_refill_prfm,prf_spec,l3d_cache_lmiss_rd` | Set `G`: prefetch instructions. `l1d_cache_prfm` and `l2d_cache_prfm`: software preloads of the L1 and of the L2 data cache. `l1d_cache_refill_prfm` and `l2d_cache_refill_prfm`: refills that a software preload causes. `prf_spec`: prefetch operations that the core executes speculatively. `l3d_cache_lmiss_rd`: the saved list gives no text for it. By its name it counts long-latency read misses of the level 3 data cache [Ref1]. |

## References

- [Ref1] `perf-list-details.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the text that `perf list --details` printed for each event on CRB.
- [Ref2] `DECISIONS.md` in the folder `asct-2026-11-16`, section "How ASCT is used, and why not through `asct run`".
- [Ref3] `resolve.txt` in the same result folder: 43 lines, each starts with `resolved`.
