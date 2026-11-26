## Short version: purpose

`sets5.txt` is a list of event sets for the counter script `rgc.sh`: 7 lines, each with 16 watchpoint events of the mesh counters. The watchpoints sit at 4 core ports of each mesh and count the data flits that go to the cores, split by a source class. The facts sheet uses these counts to tell where the data of a core comes from.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip that links the cores, the cache and the memory ports. Reading it needs root rights.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **Event set**: one line of this file: a set name, the character `|`, and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command of the script counts. The script takes one window per event set and writes its counts to a file `GROUP.SET.perf`.
- **Full event string**: the name of a counter device, then `/`, the event with its parameters, and `/`. This is the form in which `perf` takes an event of a named device. The strings of a set are separated by commas.
- **Crosspoint**: one junction of the mesh. It has links to its neighbours and device ports.
- **Node id**: the number of one node of a mesh. With `bynodeid=1,nodeid=N` an event counts at the node N only.
- **Core port**: a device port of a crosspoint to which cores are joined. The script `anc4.py` calls the four places of this file core ports.
- **Flit**: one unit of traffic on the mesh. The mesh moves requests, responses and data as flits. By the facts sheet `FINDINGS.md`, 2 data flits carry one 64 B line.
- **Channel**: the kind of a flit. `wp_chn_sel=3` chooses the data channel (DAT) and `wp_chn_sel=1` the response channel (RSP). The script `anc4.py` reads the two numbers this way.
- **Watchpoint**: a counter event that counts the flits of one channel at one device port of a crosspoint. `watchpoint_down` counts flits that the crosspoint sends down to the device. A value (`wp_val`) and a mask (`wp_mask`) choose the flits: a flit counts when it is equal to the value in every bit that the mask does not hide. A mask bit of 1 hides the bit.
- **Source class**: a name that the file `sets5.classes.json` of this folder gives to one pair of a value and of the bits that are compared, for example `snW`, `snE`, `p1y0`. A watchpoint with this pair counts the data flits of that class.

## Main flow

1. Read one line as one event set. The text before the first `|` is the set name. The rest is a list of full event strings with commas between them ({L1}).
2. A comma also stands inside a string, between the parameters of one event. A string ends at the `/` that is followed by a comma or by the end of the line.
3. Every line holds 16 strings: 2 watchpoints at each of 4 crosspoints, first for the device `arm_cmn_0` (mesh 0) and then for `arm_cmn_1` (mesh 1). The 4 node ids are `0x90`, `0x98`, `0x218` and `0x3a0` in every line.
4. In every string `wp_dev_sel=1` chooses device port 1 of the crosspoint, and `wp_grp=0` chooses the match group 0.
5. In every string `wp_chn_sel=3` chooses the data channel.
6. `wp_val` and `wp_mask` tell the source class. The file `sets5.classes.json` lists 14 classes, each with its value and with the bits that are compared. The mask of a string is the complement of those bits.
7. The set name starts with `src` and names the two classes of the line, in a short form: `p0x2` stands for the class `p0mid_x2`.

## Behavior a reader must know

- The file fits `rgc.sh` and `rc2.sh`, which take full event strings. It does not fit `rc.sh`, which splits a set at `;` and adds the device names itself.
- A mask of all ones (`0xffffffffffffffff`) hides every bit. Such a watchpoint counts every flit of its channel. The script `anc4.py` reads this mask as "all".
- The watchpoints count at 4 core ports of each mesh, not at all core ports. So a count is a sample of the traffic to the cores.
- A crosspoint gets 2 watchpoints per window in this file. So the 14 classes need 7 sets. They are counted in 7 windows, one after the other, not at the same time.
- This file and `sets5.classes.json` do not say what a class stands for. The facts sheet `FINDINGS.md` reads the counts as the data that arrives from the two memory-port columns of the own mesh and from the gateway row. This page gives no finer meaning of a class name.
- The result folder `w120-RC5-20261115T201920Z` holds a file `sets.ok` with the same 7 lines [Ref1].

## References

- [Ref1] test data: the file `sets.ok` in the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC5-20261115T201920Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`.
- [Ref2] external source: Linux kernel documentation, page "Arm Coherent Mesh Network PMU" (file `Documentation/admin-guide/perf/arm-cmn.rst`): the parameters `bynodeid` and `nodeid`, and the watchpoint events for flit uploads and downloads.
