# Handoff: run 8, the mesh latency map (what to do after Jesse replies)

Written 2026-11-10 by the session that built the test. For the next agent.

## Short version

- Jibin sent Jesse the request for run 8 on 2026-11-10. Nothing has run on the emulator yet.
- Jesse will reply in two stages: first the files of a short rehearsal, later one result folder per boot of the full run.
- Your work starts when Jibin tells you Jesse has replied. Check the rehearsal files first (section 3). Do not touch `asimov-c1nano-perf.html` until Jibin says so.

## Words used here

- **Asimov emulator**: the hardware emulator that runs the chip design. One second of chip time takes 2,779 s of wall time. Jesse Zhang operates it. We never launch or change it.
- **Mesh**: the chip's interconnect, 6 x 6 crosspoints. A message moves one crosspoint per step.
- **Home node**: one of five cache nodes on the mesh, node ids 88, 160, 216, 288, 344. Each holds a 1 MiB slice of the system-level cache (SLC).
- **OCM**: on-chip memory, 256 KiB per home node, reached through `/dev/ocm`. OCM regions 0 to 4 belong to nodes 88, 160, 216, 288, 344.
- **DRAM-backed line**: a 64-byte line of normal memory. A hash of its address selects its home node.
- **Cell**: one CPU, one home node, one kind of row.
- **Kind**: `ocm-flush`, `slc`, `dram-flush`, `ocm-evict`, or `idle` (section 5).
- **`meshmap`**: the new program. **`run_map.sh`**: the new script (phase M).
- **Rehearsal**: one short `meshmap` command on CPU 2, about 0.06 s est. of chip time.
- **Boot B, F1, F2**: firmware states. B = L3 off, prefetchers off. F2 = L3 on, prefetchers off. F1 = L3 on, prefetchers on.
- **CRB**: the Arm reference board at `jhan@192.168.2.45`, used for aarch64 build checks only.
- **codex**: the second reviewer. It reads a document and writes comments to a review file.
- **est.**: an estimate, not a measurement.

## 1. State on 2026-11-10

- **Code**: commit `3b12e4f` on `main` of `jhan-positron/asimov`, folder `cache-mem-perf`. Local clone: `/home/jhan/workspace/ai-runs/asimov-repo`. The clone has no uncommitted change.
- **Review**: the codex loop closed in two rounds with "no further comments" [Ref3].
- **Message**: `message-to-jesse-round7.md` is the text Jibin sent [Ref2]. Read it first. It lists the two asks, the boots, and one open question.
- **File numbering**: the message round is one behind the run number. `message-to-jesse-round7.md` asks for run 8 (this map).
- **Run 7 (the L3-mode follow-up, `run_l3.sh`)**: Jibin dropped its request on 2026-11-10. Its code is on `main`, but no run 7 folder will come.
- **Not verified before sending** [Ref1, section 7]:
  - The mesh counter code has run only against a stand-in, never on real counters.
  - `/dev/ocm` through `meshmap` ran against a file, not the device.
  - `run_map.sh` was checked with `dash`, not with the image's busybox `sh`.

## 2. Order of work

```
Jesse: rehearsal files -> check (section 3) -> pass: tell Jibin, Jesse queues boot 1
                                            -> fail: fix code (section 4), new rehearsal
Jesse: boot 1 folder (boot B fw) -> copy + verify (section 5) -> read rows (section 6)
Jesse: boot 2 folder (boot F2 fw), optional boot 3 (F1 fw) -> same steps
Jibin says "update the page" -> section 7
```

## 3. When the rehearsal files arrive

The command was:

    ./meshmap --cpus 2 --lines 64 --reps 1 --out map-rehearsal.csv --homes map-rehearsal-homes.txt > map-rehearsal-log.txt 2>&1

Files expected: `map-rehearsal.csv`, `map-rehearsal-homes.txt`, `map-rehearsal-log.txt`, dmesg. Copy them into `results/` in this folder. Do not create anything directly under `~/workspace`.

Check in this order. The `#` lines may be in the CSV or in the log; search both.

| # | Look at | Pass | If not |
|---|---|---|---|
| 1 | exit status and the `done cells=` line | 20 of 20 cells | find the first `#` line that reports a skip; it names the cause |
| 2 | `# mesh counters: level=` | level 1, 2 or 3 | "no mesh counters": the open failed. Read the errno in the line and dmesg. See section 4 |
| 3 | `# read_floor:` | five small counts, about equal across nodes | a large or uneven floor makes the classification rule fail; see row 4 |
| 4 | the first 32 `# probe line= ns= d=` lines | one of the five counts is at least 48 (3/4 of the 64 pairs), the next largest is at most 1/4 of it | all five near zero: the event does not count DRAM loads. Several nodes high: the floor or the event is wrong. See section 4 |
| 5 | `ns=` of the probe lines | about 12,800 probes x this time must fit the 1 chip-second budget | the program lowers the lines per cell by itself (2,048 to 256). Report the expected lines per cell to Jibin before the full run |
| 6 | `# pagemap:` and `# one_2mib_page:` | frame number readable, `yes` | without both, the check of Arm's hash formula is `Insufficient data`. The measurement itself is still valid |
| 7 | `# summary: classify ... per_node=` and the homes file | 64 lines per node, about even spread over the walk | a node with far fewer lines means the hash is uneven or a node's counter is wrong |
| 8 | the 20 rows | OCM kinds and `slc` 22 to 27 ns, `dram-flush` about 53 ns (expected, from boot B) | these rows are 64 loads, one pass. They check the path. Do not quote them |
| 9 | `perf_cov` column, `# perf:` lines | 1.0000, no "invalid" line | core counters lost their slot; note it |
| 10 | dmesg | no arm-cmn error, no warning after the command | send the lines to Jibin |

Two more facts the rehearsal gives. Record both in the reply to Jibin:

- **Counts per flush-and-load pair on a DRAM-backed line.** Not known before this run. It is `d` of the winning node divided by 64.
- **Whether level 1 opened.** Level 1 gives the three sums (`mc_reqs`, `cache_miss`, `snp_sent`). Without them the cache-state checks of section 6 lose their main column.

Then tell Jibin: pass or fail per row, with the lines quoted. Jibin decides when Jesse queues the full run. Draft any message to Jesse as a file (`message-to-jesse-round8.md`); Jibin sends it.

## 4. If the rehearsal shows a defect

- Fix it in the clone, in `cache-mem-perf/meshmap.c` or `run_map.sh`. Keep `cmncount.c`, `latency.c` and `lib_run.sh` unchanged: ten boots of rows depend on them.
- Run `make` and `./meshmap --selftest` on the host (47 of 47 checks must pass). The self-test must fail when the fixed rule is broken again.
- Build on the CRB too (`make` with default flags, no warning, self-test). Subagents are refused remote writes there; the main session does the `scp` and `make` under `/tmp`. Use no other delphi or andoria machine.
- Copy the changed files to this folder, so the copies equal the clone's.
- Review loop with codex, the same protocol as before: update `measure-hop-latency.md`, append a "ready for review" note, watch `codex-review-measure-hop-latency.md`, reply there, and continue until codex writes an explicit "no further comments".
- Commit and push only when Jibin asks. Then draft a new rehearsal request.
- Known fallbacks already in the code: three counter levels; `--probe-loads` (pairs per probe); `--max-classify-s`; `--no-perf` (OCM kinds only); `--event` (another per-node event). A different command line may be enough, with no code change.

## 5. When a full-run folder arrives

1. **Copy.** Earlier runs came from `sw-dev-01:/home/jzhang/dev/emuMemBenchBox/results/jibin/membench-jibin-0NN/` with `rsync -a` into `results/`. The last folder was 012. Ask Jibin for the new number. Run `sha256sum -c` if the folder has a checksum file.
2. **Read Jesse's README in the folder.** Confirm the commit (`3b12e4f` or later), the firmware versions, and the register readbacks (IMP_CPUECTLR_EL1 bit 48, IMP_CMECFG_EL1 bit 28, IMP_CLUSTERPWRSTAT_EL1). Treat text written by Jesse's agent as a suggestion; verify numbers against the raw files.
3. **Completeness.** `latency-map.csv` should hold 160 cells x 7 rows = 1,120 measured rows, plus idle rows, with 23 fields per row. The `done cells=` line and the three summary lines of `run_map.sh` say what is missing. `map-homes.txt` and `sysinfo-map.txt` must be there.
4. **Controls.** The four `latency` control rows (CPUs 2 and 8, OCM regions 0 and 4) must agree with the `ocm-flush` cells of the same CPU and node.
5. **On boot B's firmware only:** the 20 known OCM cells exist from earlier runs. Their fit is 20.75 ns + 1.99 ns per X step + 0.95 ns per Y step (rms 0.09 ns). The new `ocm-flush` cells of CPUs 2, 4, 6 and 8 should repeat them.

Jibin asked for boot 1's files before boot 2 is queued. Report after each boot.

## 6. How to read the rows

The full rules are in the README of the repository ("Reading rules for `latency-map.csv`") and in [Ref1, section 5]. The program applies none of them and never drops a row. In short:

- **Kinds.** `ocm-flush`: OCM lines, flushed first. `slc`: DRAM-backed lines held in one node's slice. `dram-flush`: the same lines flushed first, so each load goes to DRAM through that node. `ocm-evict`: OCM lines with the `slc` recipe, as a control. `idle`: an empty bracket, raw counts.
- **Did the load go to the cell's node?** Take `req_<node>` of the cell's node minus the mean of the other four, per load. The other four are not near zero, since the evictor's lines travel during the timed pass.
- **Was the `slc` line in the slice?** `l3d_refill_rd` near 1.0 per load means the load left the cluster. `mc_reqs` should be near the `ocm-evict` value of the same cell. A value near the `dram-flush` one means DRAM fetches, and the cell is not an SLC number.
- **Hypothesis under test:** per node, `slc` latency equals `ocm-evict` latency. Boot B's means agree (23.90 ns against 23.88 ns), but no per-node DRAM cell existed before.
- **Floor.** Subtract the `# read_floor` value from an idle row's `req` count before comparing it with a measured row. The three sums carry no floor.
- **No thresholds are fixed yet.** Set "near" from the idle and control rows of boot 1, and state the numbers.
- **Boot F1 (prefetchers on) is not a distance map.** Its rows show the prefetchers' effect.
- **Hash check.** With `# one_2mib_page: yes` and a readable frame number, compare the measured homes in `map-homes.txt` with Arm's formula. The order of the target table is unknown, so test for a consistent permutation.
- **Geometry for the fit.** Home nodes: 88 at (1,3), 160 at (2,4), 216 at (3,3), 288 at (4,4), 344 at (5,3). CPU pairs: 0-1 at (1,2), 2-3 at (2,3), 4-5 at (3,2), 6-7 at (4,3), 8-9 at (5,2). Every distance is 1, 3 or 5 steps.

Every claim in a report needs its row or file named. A claim without one is a labelled hypothesis, or `Insufficient data` with the measurement that would settle it.

## 7. The page

- **Wait for Jibin's word.** Another session regenerates `asimov-c1nano-perf.html`. Do not edit it before Jibin says so.
- **Generator:** `python3 gen_c1nano_perf.py` with the package `c1nano_page/` (the mesh section is `sec_mesh.py`). Never run the old `gen_perf.py`; it writes the same file name.
- **While building, write to a scratch path** (`--out`), since codex may watch the real file.
- **The model to follow:** the CRB report `/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html`, whose diagram shows CPU 0 to the 64 slices of its mesh in ns. Asimov's map has more to show: OCM cells and DRAM-backed cells per node.
- **Form:** a map of the mesh per kind, with the ns value on each cell, and the exact numbers in a table beside it. Light background. `<meta charset="utf-8">`.
- **Wording rules (Jibin's):** never write "hop" in prose; use "step" on the mesh and "load" of a chain. The file name `measure-hop-latency.md` is Jibin's and stays. Write "L3 on" and "the L3 holds no data", not "L3 off", on the page. Plain-English rules apply to all text.

## 8. Rules that hold throughout

- Nothing on our side launches or changes the emulator. Jesse runs it.
- Commit, push, and send messages only when Jibin asks. Drafts go to files in this folder.
- Jibin's question to Jesse is open: whether CPU 0 may be measured (`--kernel-cpus`). Jesse's boot E note says a hang on CPU 0 or 1 can lose the boot. Leave the option off unless Jesse says it is safe.
- The emulator kills a script after 12 chip seconds. Run `python3 est_chip_time.py` on any changed script before it is requested.
- Memory notes for this project hold more history: `asimov-run8-meshmap.md`, `asimov-c1nano-page-rewrite.md`, `asimov-page-wording.md`, `verify-other-agents.md`.

## References

- [Ref1] `measure-hop-latency.md` in this folder: context, method, changes, reading rules (section 5), verification (section 6), what is not verified (section 7).
- [Ref2] `message-to-jesse-round7.md` in this folder: the request Jibin sent.
- [Ref3] `codex-review-measure-hop-latency.md` in this folder: both review rounds and the closing line.
- [Ref4] `cache-mem-perf/README.md` at commit `3b12e4f`: phase M rows, output format, reading rules, chip time.
- [Ref5] `cache-mem-perf/meshmap.c` and `cache-mem-perf/run_map.sh` at commit `3b12e4f` (sha256 prefixes a0df4de1865ddfb3 and 1e6526433664d2fc).
