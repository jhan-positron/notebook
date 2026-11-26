## Short version: purpose

`resolve_events.py` turns the event names of the file `events.txt` into the raw codes that the counter code of ASCT needs. The script `prep.sh` runs it on CRB. It writes the file `events.codes` with one line per event set and prints one report line per event name.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter unit of the cores**: the name under which Linux shows the counters of the cores, `armv8_pmuv3_0`.
- **Raw code**: the number that selects one counter event of a counter unit.
- **Event set**: a named list of counter events that one process counts together. `events.txt` holds one set per line.
- **sysfs**: the folder `/sys`, in which the Linux kernel shows its devices and their settings as files.
- **`perf list`**: the command that prints the counter events that the tool `perf` knows on a machine.
- **L1, L2**: the first and the second cache level of a core.
- **TLB**: the cache of a core for address translations.

## Main flow

1. Read the two arguments: the input file and the output file ({L6}).
2. Read the event sets of the input file and collect every event name once ({L7-9}).
3. Source 1: for each name, read its code from the sysfs file of the event, when that file exists ({L10-16}).
4. Source 2: run `perf list --details` and take the code of each name that still has none ({L17-30}).
5. Source 3: take the code from the table `FALLBACK` for each name that still has none ({L31-42}).
6. Write the output file: one line per set, with a `name=0xCODE` pair for each name that has a code ({L43-46}).
7. Print the report: one line per name with its code and its source, or with the word `unresolved` ({L47-48}).

## Behavior a reader must know

- The three sources have a fixed order. A later source never replaces a code of an earlier source.
- A name without a code does not stop the script. It is left out of its set in the output file and shows as `unresolved` in the report.
- The description text at the top names two sources. The code has three.
- Pattern 3 in {L28} takes a code only when it starts with `0x`. The list of `perf` on CRB prints some small codes without `0x` [Ref1].
- In the run of 2026-11-16 all 43 names were resolved: 19 from sysfs, 24 from the list of `perf`, none from the table `FALLBACK` [Ref2].
- The script runs `perf list --details` itself. When `perf` is missing, the script stops with an error in {L17}, before it writes the output file.

## References

- [Ref1] `perf-list-details.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the output of `perf list --details` on CRB, with lines such as `armv8_pmuv3_0/event=8/`.
- [Ref2] `resolve.txt` in the same result folder: 43 lines that start with `resolved`, 19 with the source `sysfs` and 24 with the source `perf-list`.
