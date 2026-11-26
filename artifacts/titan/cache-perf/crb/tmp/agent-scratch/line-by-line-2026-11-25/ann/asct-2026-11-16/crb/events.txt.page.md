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

1. Read each line as one event set. The text in front of the `|` is the set name, a letter from `A` to `G` ({L1-7}).
2. Read the text after the `|` as a list of event names with commas between them. The names are those of the counter unit of the cores.
3. Each set starts with `cpu_cycles` and holds 6 more events. By the decisions file a set has at most 6 events plus `cpu_cycles`. Then no event shares a counter [Ref2].
4. `resolve_events.py` keeps every line that holds a `|`. It takes the set name and the names and looks up the raw code of each name. It writes one line per set to `events.codes`, in the form `SET|name=0xCODE,...`.
5. The run scripts read `events.codes`. They put the set name into the tag and into the file names of the process. They pass the codes of the set to the probe binary in the environment variable `DIETPERF_PMUv3`, in the order of the line.

## Behavior a reader must know

- A name that `resolve_events.py` cannot resolve is left out of the set in `events.codes`. In the run of 2026-11-16 all 43 names were resolved [Ref3].
- Three scripts read `events.codes`: the smoke test of `prep.sh`, the parts C and NC of `run_single.sh`, and the step `CNT` of `run_chip.sh`. Part NC uses the sets `A`, `B` and `E` only.
- The short meaning of each event in the rows comes from the event list that `perf` printed on CRB [Ref1]. The file itself holds only names.

## References

- [Ref1] `perf-list-details.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the text that `perf list --details` printed for each event on CRB.
- [Ref2] `DECISIONS.md` in the folder `asct-2026-11-16`, section "How ASCT is used, and why not through `asct run`".
- [Ref3] `resolve.txt` in the same result folder: 43 lines, each starts with `resolved`.
