# `sets1.txt` explained, line by line

- Source file: `w120-2026-11-15/sets1.txt` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 22 lines, 1753 bytes).
- sha256 of the source when this page was built: `9196ad707c2cf0f55359fe98e73ec115519f3cca7e3fbcc632dba195948945c7`.
- This file is equal to `asct-2026-11-16/crb/sets_chip.txt` of the same repo (same sha256). Both pages hold the same explanation.

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

1. Read each line as one event set. The text in front of the `|` is the set name, `s01` to `s22` (lines 1 to 22).
2. Read the text after the `|` as a list of event names with a `;` between them. The names are event names of the mesh units.
3. The sets `s01` to `s05` hold 2 home-node events and 4 events with the prefixes `ccra`, `ccha` and `ccla` (lines 1 to 5). The sets `s06` to `s16` hold 2 home-node events (lines 6 to 16). The sets `s17` to `s22` hold 4 crosspoint events (lines 17 to 22).
4. `run_mesh.sh` and `rc.sh` read the file with the same code. First they test each event alone with a short `perf stat` run on the unit `arm_cmn_0`. They write the sets with the events that passed to the file `sets.ok`.
5. Then, while a benchmark process runs, they open one counting window per set of `sets.ok`, in the order of the lines. `perf stat -a` counts each event of the set on `arm_cmn_0` and on `arm_cmn_1`, together with the cycle counter `dtc_cycles` of both units.
6. The set name becomes a part of the name of the result file of the window, `TAG.SET.perf`.

## Behavior a reader must know

- The sets are counted one after the other, each in its own window of a few seconds. Two sets are never counted at the same moment, so their counts come from different seconds of the same process.
- The scripts test each event alone. They do not test whether all events of one set can be counted together.
- The run `w120-RC1` of 2026-11-15 used this file. The copy in its result folder is equal to it, and every event passed the test [Ref1].
- The mesh-counter runs of the ASCT cross-check, for which `sets_chip.txt` was prepared, did not happen [Ref2].
- Many names have no plain name in the notes of the project. The rows say so and add no guess about what such an event counts.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/sets1.txt` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (22 lines, 1753 bytes, sha256 `9196ad707c2cf0f55359fe98e73ec115519f3cca7e3fbcc632dba195948945c7`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `s01\|hns_pocq_reqs_recvd_all;hns_pocq_retry_all;ccra_rht_alloc;ccha_reqtrk_alloc;ccla_tx_cxs;ccla_tx_cxs_lcrd_backpressure` | Set `s01`. The text in front of the `\|` is the set name. The script that reads the file puts it into the name of the result file of each counting window of this set. After it stand the event names with a `;` between them, here 6. The script first tests each event alone. Then it counts each event that passed on both mesh units. `hns_pocq_reqs_recvd_all`: requests that the home nodes received. `hns_pocq_retry_all`: request retries at the home nodes [Ref3]. The other four names start with `ccra`, `ccha` or `ccla`. The notes of the project give a plain name to one event of this kind only, in set `s03`. |
| 2 | `s02\|hns_qos_pocq_occupancy_all;hns_sn_throttle_all;ccra_rht_occ;ccha_reqtrk_occ;ccra_cxreq_pcrd_stalls_link0;ccra_cxdat_pcrd_stalls_link0` | Set `s02`: 6 events. `hns_qos_pocq_occupancy_all`: the queue occupancy of the home nodes [Ref3]. `hns_sn_throttle_all` has no plain name in the notes. The other four names start with `ccra` or `ccha`. Two of them, `ccra_rht_occ` and `ccha_reqtrk_occ`, have the names of two events of set `s01` with the ending `occ` in place of `alloc`. The notes give them no plain name. |
| 3 | `s03\|hns_mc_reqs_local_all;hns_mc_retries_local_all;ccra_chidat_stalls;ccra_external_chidat_stalls;ccha_chidat_up_stall;ccha_rdb_alloc` | Set `s03`: 6 events. `hns_mc_reqs_local_all`: requests to the memory controllers. `hns_mc_retries_local_all`: retries of such requests. `ccra_chidat_stalls`: data stalls of the gateway [Ref3]. The other three names (`ccra_external_chidat_stalls`, `ccha_chidat_up_stall`, `ccha_rdb_alloc`) have no plain name in the notes. |
| 4 | `s04\|hns_mc_reqs_remote_all;hns_mc_retries_remote_all;ccla_rx_cxs;ccla_tx_cxs_avg_size;ccra_rdb_alloc;ccha_rddatbyp` | Set `s04`: 6 events. The first two have the names of the first two of set `s03` with `remote` in place of `local`. The other four start with `ccla`, `ccra` or `ccha`. None of the six has a plain name in the notes. |
| 5 | `s05\|hns_txdat_stall;hns_txrsp_stall;ccra_chirsp_stalls;ccra_external_chirsp_stalls;ccha_chirsp_up_stall;ccha_rdb_occ` | Set `s05`: 6 events. `hns_txdat_stall`: data stalls of the home nodes [Ref3]. `hns_txrsp_stall` has the same name with `rsp` in place of `dat`. The other four start with `ccra` or `ccha`. They have no plain name in the notes. |
| 6 | `s06\|hns_cache_miss_all;hns_cache_fill_all` | Set `s06`: 2 events. `hns_cache_miss_all`: SLC misses. `hns_cache_fill_all`: SLC fills [Ref3]. |
| 7 | `s07\|hns_pocq_reqs_recvd_read;hns_pocq_retry_read` | Set `s07`: 2 events. They have the names of the two home-node events of set `s01` with the ending `read` in place of `all`. |
| 8 | `s08\|hns_pocq_reqs_recvd_lbt;hns_pocq_retry_lbt` | Set `s08`: the same two names with the ending `lbt`. The notes of the project do not explain this ending. |
| 9 | `s09\|hns_pocq_reqs_recvd_hbt;hns_pocq_retry_hbt` | Set `s09`: the same two names with the ending `hbt`. The notes of the project do not explain this ending. |
| 10 | `s10\|hns_qos_pocq_occupancy_lbt;hns_sn_throttle_ccg_read` | Set `s10`: 2 events. `hns_qos_pocq_occupancy_lbt` has the name of the queue occupancy of set `s02` with the ending `lbt`. `hns_sn_throttle_ccg_read` has no plain name in the notes. |
| 11 | `s11\|hns_qos_pocq_occupancy_hbt;hns_sn_throttle_lbt_read` | Set `s11`: 2 events. `hns_qos_pocq_occupancy_hbt` has the name of the queue occupancy of set `s02` with the ending `hbt`. `hns_sn_throttle_lbt_read` has no plain name in the notes. |
| 12 | `s12\|hns_cbusy11_all;hns_sn_throttle_min_all` | Set `s12`: 2 events. `hns_cbusy11_all`: busy level 3 at the home nodes [Ref3]. `hns_sn_throttle_min_all` has no plain name in the notes. |
| 13 | `s13\|hns_cbusy00_all;hns_cbusy10_all` | Set `s13`: 2 events. `hns_cbusy00_all`: busy level 0. `hns_cbusy10_all`: busy level 2 [Ref3]. The two digits in the name are the level as a binary number. This file does not hold the event for level 1, `hns_cbusy01_all`. |
| 14 | `s14\|hns_pocq_class_occup_class3;hns_pocq_class_retry_class3` | Set `s14`: 2 events with the ending `class3`: `hns_pocq_class_occup_class3` and `hns_pocq_class_retry_class3`. They have no plain name in the notes. |
| 15 | `s15\|hns_pocq_class_occup_class0;hns_pocq_class_retry_class0` | Set `s15`: the two names of set `s14` with the ending `class0`. |
| 16 | `s16\|hns_qos_hh_retry;hns_pocq_addrhaz_all` | Set `s16`: 2 events, `hns_qos_hh_retry` and `hns_pocq_addrhaz_all`. They have no plain name in the notes. |
| 17 | `s17\|mxp_p0_req_txflit_valid;mxp_p0_req_txflit_stall;mxp_p0_dat_txflit_valid;mxp_p0_dat_txflit_stall` | Set `s17`: 4 events of device port 0 of the crosspoints (`mxp_p0`). For the request channel (`req`) and for the data channel (`dat`) it holds the flits that were delivered (`txflit_valid`) and the stalls (`txflit_stall`) [Ref3]. |
| 18 | `s18\|mxp_p1_req_txflit_valid;mxp_p1_req_txflit_stall;mxp_p1_dat_txflit_valid;mxp_p1_dat_txflit_stall` | Set `s18`: the same 4 events for device port 1 (`mxp_p1`). |
| 19 | `s19\|mxp_e_dat_txflit_valid;mxp_e_dat_txflit_stall;mxp_w_dat_txflit_valid;mxp_w_dat_txflit_stall` | Set `s19`: 4 events of the data channel on the mesh links to the east (`mxp_e`) and to the west (`mxp_w`): the flits that were forwarded and the stalls [Ref3]. |
| 20 | `s20\|mxp_n_dat_txflit_valid;mxp_n_dat_txflit_stall;mxp_s_dat_txflit_valid;mxp_s_dat_txflit_stall` | Set `s20`: the same 4 events of the data channel for the mesh links to the north (`mxp_n`) and to the south (`mxp_s`). |
| 21 | `s21\|mxp_e_req_txflit_valid;mxp_e_req_txflit_stall;mxp_n_req_txflit_valid;mxp_n_req_txflit_stall` | Set `s21`: 4 events of the request channel on the mesh links to the east and to the north: the flits that were forwarded and the stalls. |
| 22 | `s22\|mxp_p0_rsp_txflit_valid;mxp_p0_rsp_txflit_stall;mxp_p1_rsp_txflit_valid;mxp_p1_rsp_txflit_stall` | Set `s22`: 4 events of the response channel (`rsp`) at the device ports 0 and 1: the flits that were delivered and the stalls. The notes give a plain name to the `req` and `dat` forms only. The reading of `rsp` as response follows the same pattern. |

## References

- [Ref1] `sets.txt` and `sets.ok` in the result folder `w120-RC1-20261115T190208Z` of the test folder `2026-11-15-whole-chip-read-drop`. Both are equal to this file.
- [Ref2] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" and "Record of 2026-11-16 23:50 UTC".
- [Ref3] The plain names: the lists `MESH_ROWS` and `SINGLE_MESH` in the script `report.py` of the folder `asct-2026-11-16`, and section F4 of `FINDINGS.md` in the folder `w120-2026-11-15`.
- [Ref4] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": the mesh as a grid of crosspoints with up to two device ports each, and one counter unit per mesh.
