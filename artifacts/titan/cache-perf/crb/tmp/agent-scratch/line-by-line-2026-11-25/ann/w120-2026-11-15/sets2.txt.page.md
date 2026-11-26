## Short version: purpose

`sets2.txt` is a list of event sets for the counter script `rc2.sh`: 45 lines, one set of mesh counter events or memory controller events per line. The first 5 sets count the traffic at the 24 memory ports of the two meshes: requests in, write data in, read data out, data on the mesh links, and responses. The other 40 sets scan the event numbers 0 to 39 of the 48 memory controller counters.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip that links the cores, the cache and the memory ports. Reading it needs root rights.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **Event set**: one line of this file: a set name, the character `|`, and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command of the script counts. The script takes one window per event set and writes its counts to a file `TAG.SET.perf`.
- **Full event string**: the name of a counter device, then `/`, the event with its parameters, and `/`. This is the form in which `perf` takes an event of a named device. The strings of a set are separated by commas.
- **Crosspoint**: one junction of the mesh. It has links to its neighbours in the east, west, north and south, and device ports. Events with the prefix `mxp` belong to crosspoints.
- **Device port**: a port of a crosspoint that leads to a device and not to another crosspoint. The events name the ports `p0` and `p1`.
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits. By the facts sheet `FINDINGS.md`, 2 data flits carry one 64 B line.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back. The facts sheet counts 24 of them.
- **Node id**: the number of one node of a mesh. With `bynodeid=1,nodeid=N` an event counts at the node N only.
- **Watchpoint**: a counter event that counts the flits of one channel at one device port of a crosspoint. A value and a mask choose which flits count. `watchpoint_up` counts flits that the device sends into the mesh.
- **Memory controller counters**: the 48 counter devices `arm_cspmu_mc_0` to `arm_cspmu_mc_47`. The script `anc2.py` calls them the memory controller counters.

## Main flow

1. Read one line as one event set. The text before the first `|` is the set name. The rest is a list of full event strings with commas between them ({L1}).
2. A comma can also stand inside a string, between the parameters of one event. A string ends at the `/` that is followed by a comma or by the end of the line.
3. The script `rc2.sh` gives the list to `perf stat` as it stands, after two `dtc_cycles` events of its own. The set name becomes a part of the name of the output file.
4. In {L1-5} the device name tells the mesh and `nodeid` tells the crosspoint. The 12 node ids are the same in every one of these five lines.
5. In {L6-45} the device name tells the memory controller counter (0 to 47), and `event=K` tells the event number. The two digits of the set name repeat K.

## Behavior a reader must know

- The file fits `rc2.sh` and `rgc.sh`, which take full event strings. It does not fit `rc.sh`, which splits a set at `;` and adds the device names itself.
- The lines are long: 1194 to 4273 characters. A set holds 24 or 48 events, and all of them are counted in one window.
- The file gives the memory controller events numbers only. What an event number counts is not written in this folder. The script `anc2.py` prints, for each number, the sum over the 48 devices per line read.
- The result folder `w120-RC2-20261115T192222Z` holds a file `sets.ok` with the same 45 lines, and 180 files with the ending `.perf`: one per set for each of 4 processes [Ref1].

## References

- [Ref1] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC2-20261115T192222Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`: the files `sets.ok`, `launches.txt` and the `.perf` files.
- [Ref2] external source: Linux kernel documentation, page "Arm Coherent Mesh Network PMU" (file `Documentation/admin-guide/perf/arm-cmn.rst`): the parameters `bynodeid` and `nodeid`, and the watchpoint events for flit uploads and downloads.
