## Short version: purpose

`sets_single.txt` lists the counter events of the mesh for the one-core counter runs of the ASCT cross-check: 7 sets of 6 event names. The script `run_mesh.sh` gets the file as its second argument and counts one set per counting window while a benchmark process runs. These runs did not happen [Ref1].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Mesh unit**: the counter unit that Linux shows for one mesh, one half of the chip. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **Mesh counter, mesh event**: a hardware counter of the mesh counts events such as requests, retries or stalls. It does not belong to a core. Linux reads it through the `perf` interface.
- **Event set**: a named list of mesh events that one counting window counts together.
- **Counting window**: one run of the command `perf stat -a` for a fixed number of seconds.
- **Plain name**: the name in words that the notes of the project give to an event. The source is the script `report.py` of the ASCT cross-check.
- **Home node**: a node of the mesh that receives the memory requests of the cores and passes them on. Its events start with `hns`.
- **Crosspoint**: one point of the grid of the mesh. It has links to its neighbours and up to two device ports. Its events start with `mxp`.
- **Device port**: a port of a crosspoint to which a part of the chip is connected.
- **Flit**: one unit of transfer on a mesh link. Two data flits carry one cache line.
- **Busy level**: a value from 0 to 3 that a response message carries. A higher value says that the sender is more busy.
- **SLC**: the system level cache, the last cache level (L3) of the chip. All cores of a mesh share it.
- **Snoop filter**: a part of the home node. The notes of the project name its hit counter but do not explain it.

## Main flow

1. Read each line as one event set. The text in front of the `|` is the set name, `t01` to `t07` ({L1-7}).
2. Read the text after the `|` as a list of 6 event names with a `;` between them. The names are event names of the mesh units.
3. The sets `t01` to `t03` and `t07` hold events of the home nodes ({L1-3}, {L7}). The sets `t04` to `t06` hold events of the crosspoints ({L4-6}).
4. `run_mesh.sh` first tests each event alone with a short `perf stat` run on the unit `arm_cmn_0`. It writes the sets with the events that passed to the file `sets.ok`.
5. Then, while a benchmark process runs, it opens one counting window per set of `sets.ok`, in the order of the lines. `perf stat -a` counts each event of the set on `arm_cmn_0` and on `arm_cmn_1`, together with the cycle counter `dtc_cycles` of both units.
6. The set name becomes a part of the name of the result file of the window, `TAG.SET.perf`.

## Behavior a reader must know

- By the decisions file this file belongs to the spec file `spec_single.txt`, with a window of 3 s per set [Ref1].
- The sets are counted one after the other, each in its own window. Two sets are never counted at the same moment.
- `run_mesh.sh` tests each event alone. It does not test whether the 6 events of one set can be counted together.
- The mesh-counter runs did not happen. So no result shows which of these events CRB can count [Ref1].

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs) and "Record of 2026-11-16 23:50 UTC" (the runs did not happen).
- [Ref2] The plain names: the lists `MESH_ROWS` and `SINGLE_MESH` in the script `report.py` of the folder `asct-2026-11-16`.
