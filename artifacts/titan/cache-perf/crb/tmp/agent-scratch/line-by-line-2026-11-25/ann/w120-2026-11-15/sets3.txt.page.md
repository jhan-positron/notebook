## Short version: purpose

`sets3.txt` is a list of event sets for the counter script `rgc.sh`: 25 lines, one set of mesh counter events per line. The first 24 sets hold 2 to 8 events each, the same events on mesh 0 and on mesh 1: requests, retries and queue occupancy of the home nodes for several classes of requests, memory controller requests, throttle and busy-level events, and gateway events. The last set counts the requests into each of the 24 memory ports.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip that links the cores, the cache and the memory ports. Reading it needs root rights.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **Event set**: one line of this file: a set name, the character `|`, and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command of the script counts. The script takes one window per event set and writes its counts to a file `GROUP.SET.perf`.
- **Full event string**: the name of a counter device, then `/`, the event with its parameters, and `/`. This is the form in which `perf` takes an event of a named device. The strings of a set are separated by commas.
- **Home node**: a node of the mesh that receives requests for cache lines. Its events have the prefix `hns`. The notes of the project name some of them: requests received, request retries, queue occupancy, requests to the memory controller.
- **Gateway**: the link between the two meshes. Its events have the prefixes `ccra`, `ccha` and `ccla`. The facts sheet uses this word for them.
- **Busy level**: a number from 0 to 3 that the mesh sends to a core with each answer. 3 means most busy. This definition comes from the notes of the ASCT cross-check in the same repo. In an event name the two digits `00`, `01`, `10` and `11` stand for the levels 0, 1, 2 and 3.
- **Crosspoint**: one junction of the mesh. It has links to its neighbours and device ports. Events with the prefix `mxp` belong to crosspoints.
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits.
- **Memory port**: a place where a mesh hands requests to the memory and takes data back. The facts sheet counts 24 of them.
- **Node id**: the number of one node of a mesh. With `bynodeid=1,nodeid=N` an event counts at the node N only.

## Main flow

1. Read one line as one event set. The text before the first `|` is the set name. The rest is a list of full event strings with commas between them ({L1}).
2. In {L1-24} every event stands two times: first on `arm_cmn_0`, then on `arm_cmn_1`. So a set of 4 events counts 2 different events.
3. The set names group the lines: `rq` for requests and retries, `oc` for queue occupancy ({L1-14}), `mcl` and `mcr` for requests to the memory controllers ({L15-16}), `thr` for throttle and busy-level events ({L17-21}), `cc` for the gateway ({L22-24}).
4. The ending of an event name (`all`, `rnf`, `ccgrn`, `ccglcn`, `lbt`, `hbt`, `read`) names the class of requests that the event counts. This file does not say what the classes are.
5. {L25} has the other form: one event pair per crosspoint, with `bynodeid=1,nodeid=N`. A comma can stand inside such a string, so a string ends at the `/` that is followed by a comma or by the end of the line.
6. The script `rgc.sh` gives the list to `perf stat` as it stands, after two `dtc_cycles` events of its own. The set name becomes a part of the name of the output file.

## Behavior a reader must know

- The file fits `rgc.sh` and `rc2.sh`, which take full event strings. It does not fit `rc.sh`, which splits a set at `;` and adds the device names itself.
- This page gives the meaning of an event only where a note of the project gives it: the facts sheet `FINDINGS.md` of this folder, or the report script of the ASCT cross-check. For the other events the page repeats the name.
- The result folder `w120-RC3-20261115T194737Z` holds a file `sets.ok` with the same 25 lines, and 150 files with the ending `.perf`: one per set for each of 6 groups [Ref1].

## References

- [Ref1] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC3-20261115T194737Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`: the files `sets.ok`, `launches.txt` and the `.perf` files.
- [Ref2] external source: Linux kernel documentation, page "Arm Coherent Mesh Network PMU" (file `Documentation/admin-guide/perf/arm-cmn.rst`): the parameters `bynodeid` and `nodeid`, and the rule that an event without them is a sum over all nodes of its type.
