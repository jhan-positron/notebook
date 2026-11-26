## Short version: purpose

This file lists the counter events of the mesh for the whole-chip counter runs: 22 sets of 2 to 6 event names. A run script counts one set per counting window on both mesh units while a benchmark process runs. The file exists under two names with equal content: `sets_chip.txt` for the script `run_mesh.sh` of the ASCT cross-check, and `sets1.txt` for the script `rc.sh` of the 120-thread investigation of 2026-11-15.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **120-thread investigation**: the tests of 2026-11-15 on the read rate of CRB with 120 threads. The script `rc.sh` in the folder `w120-2026-11-15` belongs to it.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Mesh unit**: the counter unit that Linux shows for one mesh. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **Mesh counter, mesh event**: a hardware counter of the mesh counts events such as requests, retries or stalls. It does not belong to a core. Linux reads it through the `perf` interface.
- **Event set**: a named list of mesh events that one counting window counts together.
- **Counting window**: one run of the command `perf stat -a` for a fixed number of seconds.
- **Plain name**: the name in words that the notes of the project give to an event. The sources are the script `report.py` of the ASCT cross-check and the facts sheet `FINDINGS.md` of the 120-thread investigation.
- **Home node**: a node of the mesh that receives the memory requests of the cores and passes them on. Its events start with `hns`.
- **Gateway**: the link that carries requests and data from one mesh to the other mesh.
- **Crosspoint**: one point of the grid of the mesh. It has links to its neighbours and up to two device ports. Its events start with `mxp`.
- **Device port**: a port of a crosspoint to which a part of the chip is connected.
- **Flit**: one unit of transfer on a mesh link. Two data flits carry one cache line.
- **Busy level**: a value from 0 to 3 that a response message carries. A higher value says that the sender is more busy.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.

## Main flow

1. Read each line as one event set. The text in front of the `|` is the set name, `s01` to `s22` ({L1-22}).
2. Read the text after the `|` as a list of event names with a `;` between them. The names are event names of the mesh units.
3. The sets `s01` to `s05` hold 2 home-node events and 4 events with the prefixes `ccra`, `ccha` and `ccla` ({L1-5}). The sets `s06` to `s16` hold 2 home-node events ({L6-16}). The sets `s17` to `s22` hold 4 crosspoint events ({L17-22}).
4. `run_mesh.sh` and `rc.sh` read the file with the same code. First they test each event alone with a short `perf stat` run on the unit `arm_cmn_0`. They write the sets with the events that passed to the file `sets.ok`.
5. Then, while a benchmark process runs, they open one counting window per set of `sets.ok`, in the order of the lines. `perf stat -a` counts each event of the set on `arm_cmn_0` and on `arm_cmn_1`, together with the cycle counter `dtc_cycles` of both units.
6. The set name becomes a part of the name of the result file of the window, `TAG.SET.perf`.

## Behavior a reader must know

- The sets are counted one after the other, each in its own window of a few seconds. Two sets are never counted at the same moment, so their counts come from different seconds of the same process.
- The scripts test each event alone. They do not test whether all events of one set can be counted together.
- The run `w120-RC1` of 2026-11-15 used this file. The copy in its result folder is equal to it, and every event passed the test [Ref1].
- The mesh-counter runs of the ASCT cross-check, for which `sets_chip.txt` was prepared, did not happen [Ref2].
- Many names have no plain name in the notes of the project. The rows say so and add no guess about what such an event counts.

## References

- [Ref1] `sets.txt` and `sets.ok` in the result folder `w120-RC1-20261115T190208Z` of the test folder `2026-11-15-whole-chip-read-drop`. Both are equal to this file.
- [Ref2] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" and "Record of 2026-11-16 23:50 UTC".
- [Ref3] The plain names: the lists `MESH_ROWS` and `SINGLE_MESH` in the script `report.py` of the folder `asct-2026-11-16`, and section F4 of `FINDINGS.md` in the folder `w120-2026-11-15`.
- [Ref4] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": the mesh as a grid of crosspoints with up to two device ports each, and one counter unit per mesh.
