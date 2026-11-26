# `sets_single.txt` explained, line by line

- Source file: `asct-2026-11-16/crb/sets_single.txt` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 7 lines, 959 bytes).
- sha256 of the source when this page was built: `f959f427369dbe1f4f230c713574289e77efb427798f240e226971e7c70dc2c5`.

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

1. Read each line as one event set. The text in front of the `|` is the set name, `t01` to `t07` (lines 1 to 7).
2. Read the text after the `|` as a list of 6 event names with a `;` between them. The names are event names of the mesh units.
3. The sets `t01` to `t03` and `t07` hold events of the home nodes (lines 1 to 3, line 7). The sets `t04` to `t06` hold events of the crosspoints (lines 4 to 6).
4. `run_mesh.sh` first tests each event alone with a short `perf stat` run on the unit `arm_cmn_0`. It writes the sets with the events that passed to the file `sets.ok`.
5. Then, while a benchmark process runs, it opens one counting window per set of `sets.ok`, in the order of the lines. `perf stat -a` counts each event of the set on `arm_cmn_0` and on `arm_cmn_1`, together with the cycle counter `dtc_cycles` of both units.
6. The set name becomes a part of the name of the result file of the window, `TAG.SET.perf`.

## Behavior a reader must know

- By the decisions file this file belongs to the spec file `spec_single.txt`, with a window of 3 s per set [Ref1].
- The sets are counted one after the other, each in its own window. Two sets are never counted at the same moment.
- `run_mesh.sh` tests each event alone. It does not test whether the 6 events of one set can be counted together.
- The mesh-counter runs did not happen. So no result shows which of these events CRB can count [Ref1].

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/sets_single.txt` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (7 lines, 959 bytes, sha256 `f959f427369dbe1f4f230c713574289e77efb427798f240e226971e7c70dc2c5`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `t01\|hns_slc_sf_cache_access_all;hns_cache_miss_all;hns_cache_fill_all;hns_sf_hit_all;hns_pocq_reqs_recvd_all;hns_pocq_retry_all` | Set `t01`. The text in front of the `\|` is the set name. `run_mesh.sh` puts it into the name of the result file of each counting window of this set. After it stand 6 event names with a `;` between them. `run_mesh.sh` first tests each event alone. Then it counts each event that passed on both mesh units. `hns_slc_sf_cache_access_all`: SLC lookups. `hns_cache_miss_all`: SLC misses. `hns_cache_fill_all`: SLC fills. `hns_sf_hit_all`: hits of the snoop filter. `hns_pocq_reqs_recvd_all`: requests that the home nodes received. `hns_pocq_retry_all`: request retries at the home nodes [Ref2]. |
| 2 | `t02\|hns_mc_reqs_local_all;hns_mc_retries_local_all;hns_slc_eviction_all_all;hns_slc_fill_invalid_way_all;hns_seq_hit;hns_sf_evictions_all_all` | Set `t02`: 6 events of the home nodes. `hns_mc_reqs_local_all`: requests to the memory controllers. `hns_mc_retries_local_all`: retries of such requests. `hns_slc_eviction_all_all`: SLC evictions. `hns_seq_hit`: hits of a sequential stream [Ref2]. `hns_slc_fill_invalid_way_all` and `hns_sf_evictions_all_all` have no plain name in the notes. |
| 3 | `t03\|hns_cbusy00_all;hns_cbusy01_all;hns_cbusy10_all;hns_cbusy11_all;hns_txdat_stall;hns_qos_pocq_occupancy_all` | Set `t03`: 6 events of the home nodes. `hns_cbusy00_all`, `hns_cbusy01_all`, `hns_cbusy10_all` and `hns_cbusy11_all`: the busy levels 0, 1, 2 and 3. The two digits in the name are the level as a binary number. `hns_txdat_stall`: data stalls of the home nodes. `hns_qos_pocq_occupancy_all`: the queue occupancy of the home nodes [Ref2]. |
| 4 | `t04\|mxp_p0_req_txflit_valid;mxp_p0_dat_txflit_valid;mxp_p1_req_txflit_valid;mxp_p1_dat_txflit_valid;mxp_p0_dat_txflit_stall;mxp_p1_dat_txflit_stall` | Set `t04`: 6 events of the device ports of the crosspoints. For port 0 (`mxp_p0`) and port 1 (`mxp_p1`): the request flits that were delivered (`req_txflit_valid`) and the data flits that were delivered (`dat_txflit_valid`). Then the data stalls of both ports (`dat_txflit_stall`) [Ref2]. |
| 5 | `t05\|mxp_e_dat_txflit_valid;mxp_w_dat_txflit_valid;mxp_n_dat_txflit_valid;mxp_s_dat_txflit_valid;mxp_e_dat_txflit_stall;mxp_n_dat_txflit_stall` | Set `t05`: 6 events of the data channel on the mesh links. The data flits that were forwarded to the east, west, north and south (`mxp_e`, `mxp_w`, `mxp_n`, `mxp_s` with `dat_txflit_valid`). Then the data stalls to the east and to the north [Ref2]. |
| 6 | `t06\|mxp_e_req_txflit_valid;mxp_w_req_txflit_valid;mxp_n_req_txflit_valid;mxp_s_req_txflit_valid;mxp_e_req_txflit_stall;mxp_n_req_txflit_stall` | Set `t06`: the same 6 events for the request channel (`req` in place of `dat`): the request flits that were forwarded in the four directions, and the request stalls to the east and to the north. |
| 7 | `t07\|hns_readonce_fwd_data_completed_all;hns_ro_rnsd_new_alloc_hint_all;hns_snp_sent_vc0;hns_intv_dirty;hns_sn_throttle_all;hns_mc_reqs_remote_all` | Set `t07`: 6 events of the home nodes. `hns_sn_throttle_all` and `hns_mc_reqs_remote_all` also stand in the file `sets_chip.txt`. None of the six has a plain name in the notes of the project. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs) and "Record of 2026-11-16 23:50 UTC" (the runs did not happen).
- [Ref2] The plain names: the lists `MESH_ROWS` and `SINGLE_MESH` in the script `report.py` of the folder `asct-2026-11-16`.
