# Asimov cache tests, run 2: context, design, code and plan

Short version: run 1 of the cache tests on the Asimov emulator gave the level map
(L1 2.0 ns, L2 6.1 ns, SLC 24 ns, DRAM 52 ns, OCM 19 to 23 ns by region) and
showed three measurement defects in our own rows. Run 2, commits f81eb51, 94572c5,
7ba4c5b, 89552a1 and 8ae533c (the review fixes of sections 8 to 11) in
`github.com/jhan-positron/asimov` (folder `cache-mem-perf`, local clone
`~/workspace/ai-runs/asimov-repo`, pushed 2026-11-02), fixes the three defects,
adds the per-DSU OCM rows the handoff asked for, and adds a small program that
counts mesh requests per home node around each OCM row. This document is for a
reviewer who has not seen the project; the files to read are listed at the end.

Status on 2026-11-02: four codex review rounds are applied (sections 8 to 11),
and the fifth round found nothing new in 8ae533c and declared the loop complete.
The working copy in this folder is byte-identical to the clone at 8ae533c for
every source file. The five commits were pushed to origin/main on 2026-11-02
(9c6b8e7..8ae533c). Jesse has not yet been told about run 2. The aarch64 build
check of 8ae533c on the CRB is done (section 5), as are the host build and
tests.

## Words used here

- Asimov: Positron's chip. One hemisphere has 5 DSUs of 2 C1-Nano cores, a CMN S3
  mesh with 5 home nodes, a 5 MiB SLC and 5 OCM regions.
- DSU: DynamIQ Shared Unit, a 2-core cluster with a shared 128 KiB L2 and a 256 KiB
  L3. CPU pairs {2,3}, {4,5}, {6,7}, {8,9}; CPUs 0 and 1 run the kernel.
- CMN, home node (HN-S), SLC: the Arm mesh interconnect, the node that owns an
  address, and the System Level Cache (1 MiB per home node, 16 ways).
- OCM: On-Chip Memory, 4 of the 16 SLC ways in each home node locked by firmware in
  CMN OCM mode. Five regions of 256 KiB at 0xE0000000 + n MiB, one per home node,
  reached through `/dev/ocm` in 4 KiB pages. No memory sits behind OCM.
- hop: one crosspoint-to-crosspoint step on the mesh. CPU 2's DSU port is 1 hop
  from the homes of OCM 0, 1, 2 and 3 hops from the homes of OCM 3, 4 (Jesse's run 1
  notes; the crosspoint ids from the RTL give the same picture).
- Emulator: Jesse Zhang's Palladium model `hemi_rtws_tlm`. Run 1 took 2,779 wall
  seconds per chip second. Jesse builds and runs our code; we never log in.
- fresh chain: a random pointer chase walked exactly once. The core prefetches a
  repeated chase, which hides the real latency.
- flushed: `DC CIVAC` (clean and invalidate) over every line of the buffer, then
  `DSB SY`, before a timed pass.
- PMU: performance monitoring unit. The core PMU counts refills per cache level
  (events 0x03, 0x17, 0xA2). The mesh PMU (`arm_cmn_0`) counts requests at the home
  nodes.
- perf_event_open: the Linux system call that opens a hardware counter. The image
  has no `perf` tool (busybox only), so our own program calls it.
- est.: an estimate, not a measurement.
- chip time: time as the chip sees it; wall time is 2,779 times longer.

## 1. Context

### 1.1 What exists

- Sources: `latency.c`, `bandwidth.c`, `common.h` (one new option, `--no-thp`,
  since run 1; the timed loops are unchanged),
  `run_asimov.sh`, `README.md`, `Makefile`, and the new `cmncount.c`. The README is
  the document Jesse reads.
- Run 1: commit 9c6b8e7, ran 2026-10-31, 1.237 s of chip time, 34 commands, all
  exit 0. Data in `results/membench-jibin-001/` (checksums verified). Jesse's
  platform notes are in `results/membench-jibin-001/README.md`.
- Run 1 report: `run1-report.html` (every number cross-checked against the CSVs).
- Facts from Jesse's agent on 2026-11-01, each verified against a primary source
  (SCP firmware source `asimov_physical_sam.c`, address map `sam_map.yaml`, the
  arm-cmn kernel driver, Jesse's environment dump): OCM is CMN OCM mode; OCM 0 to 4
  are homed at node ids 88, 160, 216, 288, 344; `arm_cmn_0` lists 280 events; mesh
  events are system-wide only, reject `exclude_*` bits, and cannot share a group
  with core events; `CONFIG_DEBUG_FS` is off (unverified, Jesse offers to enable it).

### 1.2 The three defects in run 1 (run1-report.html, section 5)

1. **Flushed rows re-walked a learned chain.** `--flush --reps 3` walks chain 0,
   which the warm-up already walked twice. At 256 KiB (4,096 lines) the per-region
   OCM rows counted only 0.77 to 0.91 L3 read refills per load: 9 to 23 % of the
   lines arrived before their load. Rows with 16,384 lines or more counted 1.00.
2. **Flushed DRAM rows measured DRAM.** `DC CIVAC` removes a DRAM-backed line from
   the SLC too. Every flushed DRAM row from 1 MiB up read 52.7 ns, the DRAM value.
   Those rows cannot stand for an SLC hit.
3. **OCM write rows timed the flush instruction.** With `--flush-after` the timed
   region holds 256 KiB of stores plus `DC CIVAC` of 4,096 lines. The stores take
   8.2 us at the core's 32 GB/s store rate; the row took 36.6 us. The other 28 us is
   the flush, 6.9 ns per line (est.). The copy row and the 4-core write row have the
   same defect.

Jesse's own note pointed at defect 3 ("three kinds of OCM row are timed without a
flush first").

### 1.3 What the handoff asked for

The previous session's handoff (`HANDOFF-2026-11-02.md`) wanted a topology check,
the home-node mapping, per-slice latency from more than one DSU, a per-core
average, and write placement. Run 2 covers the listed work except the per-home-node
DRAM-backed comparison, which is deferred (section 2.3); it does not port the CRB
per-line classification (80 chip seconds there, days here).

## 2. Design

### 2.1 Questions run 2 answers, and the row that answers each

| Question | Row (run_asimov.sh) | How the answer is read |
|---|---|---|
| Per-region OCM latency without prefetched lines | per-region rows, `--fresh 3 --flush`, line 187 | 1.00 L3 read refills per load; ns per region |
| Hop cost on the mesh | the same rows from CPUs 2, 4, 6, 8 (line 178) | from each DSU, 1-hop regions against 3-hop regions |
| Which home node holds each region | mesh counters around each per-region row (`cmn`), with one control row per core (a 4 KiB DRAM chase on 4 KiB pages, line 184) | the region's node exceeds the other four by well over the control row's per-node count; the control gives the background of program load, kernel and output |
| Per-core average over all home nodes | all-five OCM rows from CPUs 2, 4, 6, 8, (line 189) and the 2 MiB DRAM-backed fresh chase (the SLC regime) from CPUs 4, 6, 8 (line 192) | ns per core, OCM beside SLC |
| DRAM reference | 8 MiB fresh chain + flush (line 173) | should equal the 32 MiB fresh value, 52.3 ns in run 1 |
| Does a DRAM buffer spread over all 5 nodes | 2 MiB read under the counters (line 203) | about 40,000 requests per node if even (est.) |
| OCM read bandwidth per home node | per-region reads, flushed before (line 206) | 15 to 17 GB/s in run 1 |
| Does OCM sink one core's stores at the store rate | streaming write over all five regions, 8 passes (line 214) | 32 GB/s if yes; the counters show how the requests spread over the five nodes. The request count cannot tell a data fetch from a dataless ownership request, so the write protocol stays unmeasured |
| Does writer placement change the hemisphere write limit | 2 writers on 2+4, 2+8, 2+3; 4 writers on 2+4+6+8 (the control), 2+3+4+5, 2+3+8+9, all with the same options (lines 236 to 239) | 2 writers stay under the limit (2 x 32 GB/s) and show the per-DSU path; a 4-writer placement differs from the control only if the gap exceeds the spread of the repeats. Run 1's reference placement gave 86.8 GB/s at 16 MiB per writer and 88.8 at 2 MiB, so no fixed threshold is used. Where a limit sits cannot be told from these rows |
| Mesh layout from the kernel | sysinfo: debugfs mesh map, `arm_cmn_0` events (lines 134 to 152) | the map's HN-S and RN-F cells against the RTL crosspoints |

### 2.2 Method decisions

- **`--fresh 3 --flush` for every flushed latency row.** `latency.c` builds three
  chains over the same lines, walks chain 0 twice untimed, and times chains 1 and 2
  once each; with `--flush`, `timed_walk` flushes before each timed chain
  (latency.c:87, :116, :123, :127). A timed chain has never been walked, and a
  prefetcher that learned chain 0's order cannot predict chain 1's successor. The
  reviewer workflow raised, and then refuted, the worry that chain-0 training could
  still leave lines resident: the flush invalidates them, and run 1's all-five fresh
  row (never flushed, 20,480 lines) already read 0.99 refills per load.
- **Streaming write for OCM.** One core writes at 32 GB/s at every DRAM footprint in
  run 1, so a write row can only show whether OCM keeps up with one core. The 1.25
  MiB buffer is 3.3 times the 384 KiB of L2 plus L3, so lines leave the core by
  eviction during the passes. Up to 384 KiB of each 10 MiB rep may still be dirty
  in the core at the end (under 4 %). A per-region (256 KiB) write cannot be
  measured from one core because it fits the core caches. The copy kernel needs two
  five-region buffers and only five regions exist (bandwidth.c:192 to 214), so the
  copy row is dropped.
- **Counters around the whole process.** `cmncount` counts from before `exec` to
  after exit: program load, buffer fill, chain builds, warm-up, flushes and timed
  passes, plus the kernel. For an OCM row every buffer touch goes to the same home
  node, so the per-node split is the signal. A control row per core (the same
  program on a 4 KiB DRAM buffer, on 4 KiB pages so that no 2 MiB page is
  allocated or zeroed inside the count) measures the background per node. A
  counter whose enable fails or whose running time is zero gets a comment line,
  never a numeric row. Every command run through `cmncount` also gets two timing
  rows in chip ns: `child_elapsed_ns` (the command, fork to exit) and
  `helper_elapsed_ns` (`cmncount` itself, entry of `main` to the flush of every
  preceding record, which holds the counter open, enable, disable, read and
  close; the same boundary on the counted and the uncounted path).
- **Seven counters per row.** Five per-node `hns_pocq_reqs_recvd_all` plus two sums
  (`hns_mc_reqs_local_all`, `hns_cache_miss_all`). The driver allows 8 counters per
  DTC (debug trace controller); seven fit without multiplexing. `cmncount` reports
  enabled and running time so multiplexing, if it happens, is visible.
- **CPUs 5, 7, 9 idle during phase B.** CPU 3 is offline as in run 1; the other
  partners stay online and idle. Jesse: an idle isolated core does not touch the
  caches. The asymmetry is stated in the README.
- **The timed loops of `latency.c` and `bandwidth.c` do not change.** Run 2's
  rows use option combinations those programs already accept, plus one new
  allocation option in `common.h` (`--no-thp`, 4 KiB pages) for the control rows.

### 2.3 Not done, on purpose

- No per-line home-node classification and no DRAM-backed per-slice chains, so
  the handoff's per-home-node DRAM-backed latency (to compare with OCM) is
  deferred: it needs each line's home node. The OCM regions are per-home-node
  line sets by design and give the hop cost. The 2 MiB read under the counters
  shows whether a DRAM buffer spreads over the five nodes.
- No scratchpad (SPM) rows: the driver cannot load on this image (Jesse,
  2026-10-31). Phase C stays in the script and is skipped when `/dev/asimov-spm`
  is absent.
- No L3-hit isolation row. Run 1 could not isolate the DSU L3 (at 192 KiB only
  0.11 of loads were served by it). That needs a DSU L3 hit counter or a different
  footprint sweep; open item, not in run 2.

## 3. Code

### 3.1 `cmncount.c` (new, 401 lines)

Purpose: the part of `perf stat` the tests need, without the perf tool.

- Usage: `cmncount [--pmu arm_cmn_0] [--nodes 88,160,...] [--events a,b] [--global c]
  [--out FILE] [--label TEXT] [--dry-run] -- command args...`
- Event encoding is read from sysfs, the same files `perf` reads: `events/<name>`
  gives `type=0x200,eventid=0x5,occupid=0x0`; `format/<field>` gives the bit range
  (`config:16-26`). `set_field` (line 87) places each value; `build_event` (line
  123) assembles one event, adding `bynodeid=1` and `nodeid=id` for per-node events.
  Checked on CRB's real `arm_cmn_0` sysfs: node 88 gives `config=0x5880050200`
  (0x58 in bits 32 to 47, bit 31 set, eventid 5 in bits 16 to 26, type 0x200).
- Driver rules applied: system-wide (`pid -1`, the PMU's CPU from `cpumask`), no
  `exclude_*` bits, each event alone (no group), `PERF_FLAG_FD_CLOEXEC` so the
  child inherits no counter fds (line 353). `read_format` asks for enabled and
  running time (line 352). A failed enable marks the counter unavailable (line
  357); a counter whose running time reads zero gets a comment line, never a
  numeric row (line 388).
- The command always runs. PMU absent, bad node id, `--events` without `--nodes`,
  or no usable event: one `# cmncount: ... ran uncounted` line and `execvp` of the
  command (`run_uncounted`, line 220). An unknown event among good ones is skipped
  with a comment line; the others count. An open that fails (for example EINVAL for
  a wrong node id) gives a comment line with the errno. The child's exit status is
  returned (line 400); a failed fork returns an encoded status that exits 2
  (line 180). `run_child` (line 174) forks, execs and waits in every path and
  appends a `child_elapsed_ns` row with the command's lifetime on
  `CLOCK_MONOTONIC` (line 196). `helper_row` (line 205) flushes every preceding
  record, reads the clock, and appends a `helper_elapsed_ns` row with the
  helper's own lifetime from the entry of `main` (line 245) to that flush,
  after the counters are read and closed. The flush sits at the same point on
  the counted and the uncounted path (the uncounted path no longer flushes its
  comment line before the child), and the row itself is outside the interval;
  the exec and load of the helper before `main` are not timed. An invocation
  with no events times the command only (line 319).
- Output: appended to `--out`, header written once on an empty regular file (line
  269): `label,event,nodeid,count,enabled_ns,running_ns,scaled_count`.
- Tested: x86 host (software PMU, every error path, exit-status propagation), CRB
  aarch64 static build (mesh events refused without root, command still ran), dry
  run on CRB's `arm_cmn_0`. Round 3 (section 10) added a host test with a
  preloaded `fork` that fails, and the `msr` PMU of the host for the counted
  path (the counter is refused without privilege; both timing rows still come
  out in order). Round 4 (section 11) added an `strace` of both paths: after
  the child exits, each path makes one `write` of all preceding records and
  then one `write` of the helper row.

### 3.2 `run_asimov.sh` (256 lines)

- Constants: home-node ids and event names (lines 71 to 74). `cmn()` (line 98)
  runs a command under `cmncount` with the seven counters; `cmn0()` (line 107)
  runs it through `cmncount` with no counters, timing only. `run()` (line 84)
  keeps its form and adds the chip's `/proc/uptime`, a coarse 10 ms start stamp,
  to every command line in `log.txt` (counted rows show as `cmn <label>
  <command>`).
- Phase A: flushed DRAM rows are now one `--fresh 3 --flush --sizes 8M` row (line
  173).
- Phase B: loop over CPUs 2, 4, 6, 8 (line 178); per CPU one control row on 4 KiB
  pages (line 184; on CPU 2 once more without counters, line 185), five
  per-region rows (line 187) and one all-five row (line 189), all `--fresh 3
  --flush` except the control, all under `cmn`; and from CPUs 4, 6, 8 the 2 MiB
  DRAM-backed fresh chase (line 192). Output files carry the CPU in their name.
- Phase D: 2 MiB read under the counters (line 203); per-region reads under the
  counters (line 206); all-five read (line 208); streaming write (line 214). Gone:
  the unflushed 4-pass read, the write-then-flush row, the copy row.
- Phase E: six writer-placement rows, one file each (lines 236 to 239); OCM 4-core
  read under the counters (line 243). Gone: the 4-core OCM write.
- sysinfo: `DEBUG_FS` in the config grep (line 134), the `arm_cmn_0` type, cpumask,
  event count, five event texts and the full event list (lines 138 to 146), a
  debugfs mount attempt and the mesh map (lines 150 to 152).
- `--quick` (any Linux host) still runs: 15 commands, DRAM only, `cmncount` on the
  absent-PMU path. The full configuration, expanded with stub binaries, is 63
  commands, 46 of them counted and 1 timed without counters.

### 3.3 `common.h`, `README.md` and `Makefile`

`common.h` gains `--no-thp` (line 305): with it `alloc_dram` skips the huge-page
paths and asks for 4 KiB pages with `MADV_NOHUGEPAGE` (lines 120 to 121), so a 4
KiB control buffer touches one page instead of a zeroed 2 MiB page. The usage
texts of `latency.c` and `bandwidth.c` list the option; their timed loops are
unchanged.

The README is rewritten for run 2: the change list, the glossary with the verified
OCM and home-node facts, the phase table with the new rows, the `cmn-counts.csv`
format with expected magnitudes, the assumptions to check (node ids, event names),
and the chip-time estimate. The Makefile builds `cmncount` and states the x86 host
build line.

## 4. Plan

1. Codex review of this document and the commit.
2. Push 8ae533c and DM Jesse: the commit, yes to enabling
   `CONFIG_DEBUG_FS`, the same setup as run 1 (CPUs 2 to 9 online and isolated,
   256 huge pages of 2 MiB, `/dev/ocm`), and the note that the script mounts
   debugfs.
3. When the results directory is back, parse in this order:
   - `sysinfo.txt`: the mesh map (HN-S and RN-F cells against crosspoints 13, 24,
     33, 44, 53 and 12, 23, 32, 43, 52), `arm_cmn_0` present and its events.
   - `cmn-counts.csv`: any `# cmncount:` line means a counter did not open, enable
     or run; per core, the control row's five node counts; per region row, which
     node rose above its control value.
   - per-region rows: refills 1.00 per load (the defect-1 fix worked); ns per
     region per CPU; the hop table.
   - all-five OCM rows per CPU beside the 2 MiB SLC chase per CPU; the 8 MiB
     flushed row against the 32 MiB fresh row.
   - the timing rows: `child_elapsed_ns` is the chip time of each command run
     through the helper; `helper_elapsed_ns` minus `child_elapsed_ns` is the
     helper's own in-process work; the CPU 2 control's counted minus uncounted
     `helper_elapsed_ns` is the cost of the seven counters (setup, read,
     teardown and any effect on the command, the last visible in the child
     rows). The run's total (log.txt start and end, 1 s resolution) minus the
     summed helper lifetimes is unaccounted time: the 16 uncounted commands,
     the shell, sysinfo and the exec of the helper itself. That remainder
     cannot be split, so the helper's launch cost stays an estimate.
   - streaming write GB/s and its counters; placement rows.
4. Update `run1-report.html` into a run 2 report with the hop chart (5 regions x 4
   DSUs) and the counter table; update memory.

Success criteria: every counted row has seven numeric counter lines, one
`child_elapsed_ns` line and one `helper_elapsed_ns` line in `cmn-counts.csv`,
each with `running_ns` above zero and at least 95 % of `enabled_ns` (a counter
that did not run gets a comment line instead); per-region rows read 1.00 L3
refills per load; for each region row the region's node exceeds each of the
other four by more than that node's count in the core's control row (the other
four sit near their control values); the 8 MiB flushed row is within 1 ns of the
32 MiB fresh row; chip time under 3 s (Jesse allowed 5 s).

Chip time (est.): about 2 s. Run 1: 1.237 s for 34 commands, about 14 ms of it
per command for process start (est.). Run 2 has 63 commands, 47 of them through
`cmncount`, which adds one program launch each: about 110 launches, about 1.5 s
of launch cost (est.). The added OCM rows cost 2 to 10 ms of work each; the 8 MiB
fresh-plus-flush row about 0.13 s. `cmncount` records each command's lifetime
and its own (1 ns resolution), and the CPU 2 control runs counted and
uncounted, so the counters' cost is measured; the exec of the helper itself is
not timed, so its launch cost stays an estimate. Wall time about 1.5 h at
2,779 s per chip second.

## 5. Verification done before the commit

- x86 host: build with `-O2 -Wall -Wextra`, zero warnings; `sh run_asimov.sh
  --quick`, 15 commands, zero non-zero exits.
- CRB (Arm Neoverse V3AE server, gcc 14.2, Jesse's exact flags `-O2
  -mcpu=cortex-a520 -static`): zero warnings, static aarch64 binaries, `--quick`
  with 15 commands and zero non-zero exits, `cmncount` dry run on the real
  `arm_cmn_0` sysfs.
- Adversarial review workflow (4 reviewers, 2 skeptics per finding) before
  f81eb51: 30 findings, 25 survived, all applied. The blocker was a comma inside a `cmncount` label
  (`write2-cpus2,4`) that would have broken `cmn-counts.csv`; the labels are now
  `write-cpus2-4`. The main should-fix was `cmncount` exiting before running the
  command on a bad event name; it now runs the command uncounted.
- After the codex review (section 8): the same host and CRB builds and quick
  self-tests, plus the stub expansion of the full configuration.
- After the second round (section 9): the same again; the `--no-thp` control row
  reports `backing=4k` on both hosts; expansion gives 63 commands, 46 counted and
  1 timed without counters.
- After the third round (section 10), on the x86 host: build with zero warnings,
  `sh -n` of the script, both timing rows on the uncounted, no-event and counted
  paths with the child's exit status 7 kept, a preloaded `fork` that fails gives
  exit 2 and no child row, expansion unchanged at 63, 46, 1 and 16. The CRB
  aarch64 build of 89552a1 is pending: the CRB held another job's run lock.
- After the fourth round (section 11), on the x86 host: build with zero
  warnings; the uncounted, counted, forced-fork-failure and dry-run paths give
  exit 7, 7, 2 and 0 with the expected rows; `strace` shows one `write` of the
  preceding records and one of the helper row after the child on both paths.
- CRB, 8ae533c (sources checked by sha256 against the local files): zero
  warnings with Jesse's flags, static aarch64 binaries, the timing-only and
  counted paths both write the two timing rows (the mesh events are refused
  without root, as before), `--quick` runs 15 commands with zero non-zero
  exits.

## 6. Open items and risks for the reviewer

- **Node ids.** 88, 160, 216, 288, 344 come from the address map and decode to the
  RTL crosspoints, but no `perf_event_open` with `bynodeid` has been tried on this
  image. If the driver's ids differ, every per-node line reads `unavailable
  (Invalid argument)` and the mesh map in `sysinfo.txt` gives the right ids for run
  3. The row itself still runs.
- **Event names.** In the kernel driver the `_all` suffix of `hns_pocq_reqs_recvd`
  is defined for CMN-700 and CMN S3 r0/r1 models; Jesse's environment dump lists
  `hns_pocq_reqs_recvd_all` for this kernel, so it exists here. If a name is
  missing, `cmncount` says so and the row runs uncounted.
- **Kernel traffic in the counts.** System-wide counters see the idle kernel on
  CPUs 0 and 1. On this box that is small; the per-node split is what is read.
- **TLB asymmetry.** OCM rows run on 4 KiB pages, DRAM rows on 2 MiB pages, so an
  OCM-versus-SLC comparison carries a few ns (est.) of TLB cost. `--no-thp` (added
  in round 2) could put a 2 MiB DRAM chase on 4 KiB pages, but no such row is in
  run 2; the option is used only by the 4 KiB control rows.
- **`--passes 8` versus the report's 4.** The run 1 report (section 6) wrote 4
  passes for the streaming write; the script uses 8 to halve the dirty tail. The
  report is not updated for that.
- **Idle partners.** CPUs 5, 7, 9 are online and idle while 4, 6, 8 run the OCM
  rows, unlike CPU 3 which is offline. Jesse says idle cores do not touch caches.
- **Debugfs mount.** The script mounts debugfs on the emulator if it is not
  mounted. A benign state change; stated in the README.
- **Process start cost.** About 14 ms per command in run 1 (est. from the total
  against the summed row work). It dominates the small OCM rows, and each counted
  command launches two programs. The `child_elapsed_ns` and `helper_elapsed_ns`
  rows and the counted-versus-uncounted control measure the command and counter
  costs; the exec of the helper itself is outside both rows, so its launch cost
  stays an estimate, and the 2 s total with it.

## 7. Files to read, in order

1. `run1-report.html`, sections 5 and 6 (the defects and the change list).
2. `cmncount.c` (new).
3. `run_asimov.sh`, diff against 9c6b8e7 (`git diff 9c6b8e7 8ae533c -- cache-mem-perf/run_asimov.sh` in the clone).
4. `README.md`.
5. `latency.c` lines 84 to 140 (how `--fresh` and `--flush` combine),
   `bandwidth.c` lines 192 to 255 (buffer allocation and the timed region), and
   `common.h` lines 100 to 130 (DRAM allocation and `--no-thp`).
6. `results/membench-jibin-001/README.md` (Jesse's platform facts) and the CSVs
   under `results/membench-jibin-001/results/19700101T000000Z/`.

## 8. Codex review (codex-review-RUN2-PLAN.md) and what changed

Each finding was checked against the code, the run 1 data or the TRM before it
was applied.

1. **Write protocol from the request count (P1).** Confirmed: the TRM lists
   MakeUnique as a dataless ownership request, so "twice the count" cannot mean
   "fetched the old data", and the count also holds the fill, warm-up and flush
   traffic. Changed: the row's claim is now throughput and per-node spread only
   (run_asimov.sh comment, README phase table, section 2.1 here). The protocol is
   insufficient data until an event that separates data reads from ownership and
   write-back requests is chosen.
2. **88 GB/s threshold (P2).** Confirmed from run 1: 86.8 GB/s at 16 MiB per
   writer, 88.8 at 2 MiB. Changed: the 2+4+6+8 row, with the same options, is the
   control; a placement differs only beyond the spread of the repeats. The claim
   about locating a bottleneck is withdrawn.
3. **Counters must have run (P2).** Confirmed in cmncount.c: the enable ioctl was
   unchecked and a zero running time printed a numeric row. Changed: an enable
   failure marks the counter unavailable; zero running time gives a comment line;
   the success criterion requires running time above zero and at least 95 % of
   enabled time.
4. **"Exactly one node rises" (P2).** Confirmed: the counts include program load
   and kernel traffic on all nodes. Changed: one control row per core (the same
   program on a 4 KiB DRAM buffer, 4 commands) measures the background per node;
   the criterion compares the region's node against the others relative to the
   control.
5. **Helper launches in the chip budget (P2).** Confirmed: 39 counted commands in
   the reviewed version, 46 now, each one extra launch. Changed: estimate raised
   to about 2 s and the criterion to under 3 s; every command line in log.txt
   now carries the chip's uptime. Round 2 (section 9, item 2) found the stamps
   too coarse for that purpose; the `child_elapsed_ns` rows replaced them as the
   measurement.
6. **Deferred SLC scope (P2).** Confirmed against the handoff. Changed: the 2 MiB
   DRAM-backed fresh chase now runs from CPUs 4, 6, 8 (3 commands, under the
   counters) as the per-core SLC average; the per-home-node DRAM-backed latency
   is stated as deferred (section 2.3).

The fixes of this round are commit 94572c5.

## 9. Second codex review round and what changed

1. **The control allocated a 2 MiB huge page (P2).** Confirmed: `alloc_dram` rounds
   every DRAM request to 2 MiB and maps it with `MAP_HUGETLB` (run 1's 4 KiB row
   shows `backing=hugetlb`), and the kernel zeroes the whole page on first touch
   inside the counted window; the THP fallback would do the same. Changed:
   `common.h` gains `--no-thp` (4 KiB pages with `MADV_NOHUGEPAGE`), and the
   control rows use it, so the control touches its own 4 KiB only. Verified on the
   host and on CRB: `backing=4k`.
2. **The uptime stamps did not measure command cost (P2).** Confirmed: 10 ms steps,
   start stamps only. Changed: `cmncount` now forks and waits in every path and
   appends a `child_elapsed_ns` row (fork to exit on `CLOCK_MONOTONIC`, 1 ns
   resolution) for every command it runs; the CPU 2 control runs once with the
   seven counters and once without (`cmn0`), which measures the counters' cost.
   The uptime stamps stay and are described as coarse start times. The helper's
   own launch cost stays an estimate. Round 3 (section 10, item 1) found that
   the child rows alone do not hold the counter setup and read; the
   `helper_elapsed_ns` row now does.
3. **Stale "covers all five" sentence (P3).** Changed in section 1.3.

Commit 7ba4c5b. Command count: 63 (46 counted, 1 timed without counters, 16
uncounted).

## 10. Third codex review round and what changed

1. **`child_elapsed_ns` excludes the counter costs the plan claimed it measures
   (P2).** Confirmed in cmncount.c: the counters are opened and enabled before
   `run_child` starts its clock and disabled, read and closed after it stops, so
   a counted and an uncounted child lifetime differ only by the counters' effect
   on the command, not by their setup and read. Changed: `cmncount` appends a
   second row, `helper_elapsed_ns`, its own lifetime from the entry of `main` to
   just before exit, which holds the sysfs reads, the counter open, enable,
   disable, read and close, and the output. The counted minus uncounted
   `helper_elapsed_ns` of the CPU 2 control is now the counters' cost. The
   exec and load of the helper before `main` are not timed by either row, so
   the plan, script and README now call the run's remainder unaccounted time,
   not a launch cost, and the launch cost stays an estimate. The residual
   calculation of section 4 is withdrawn.
2. **A failed `fork` exited 130 (P3).** Confirmed: `run_child` returned a bare 2,
   which `exit_code` read as death by signal 2 (SIGINT) and turned into 130.
   Changed: it returns `2 << 8`, an encoded wait status, like the `waitpid`
   failure branch. Verified on the host with a preloaded `fork` that fails with
   EAGAIN: exit 2, no `child_elapsed_ns` row (the `helper_elapsed_ns` row is
   still written).

Commit 89552a1. Command count unchanged: 63 (46 counted, 1 timed without
counters, 16 uncounted).

## 11. Fourth codex review round and what changed

1. **Counted and uncounted helper timings had different flush work inside the
   interval (P2).** Confirmed in cmncount.c at 89552a1: `run_uncounted` flushed
   its comment line before the child, inside the interval, and `helper_row`
   read the clock before the final flush, so the counted path's rows were
   written after its clock stopped. Changed: `helper_row` flushes every
   preceding record, then reads the clock, then writes its own row; the early
   flush in `run_uncounted` is gone (the dry run still flushes, it has no
   timing). Both paths now carry the same output work inside the interval and
   the helper row itself is outside it. The README states the boundary.
   Verified on the host with `strace`: on both paths, after the child exits,
   one `write` of all preceding records precedes one `write` of the helper row.
   The size of the former bias on the emulator was never measured (the row did
   not exist in run 1).

Commit 8ae533c. Command count unchanged: 63 (46 counted, 1 timed without
counters, 16 uncounted). Five commits on main of the local clone, unpushed.

## 12. Fifth codex review round

No new findings. Codex verified the flush boundary on both paths with its own
host test (both helper intervals include an injected flush cost) and closed
the loop for 8ae533c. The CRB aarch64 build and quick test of 8ae533c passed
afterwards (section 5). Open: the push and the message to Jesse.

## 13. Run 2 results (2026-11-02)

Jesse delivered membench-jibin-002 (commit 8ae533c) at 16:21 PST: 63 commands exit 0,
57 files intact, 1.630 s chip time, on SCP 0.48.0 and TF-A 0.35.0 (run 1: 0.34.0 and
0.24.0). Copied to results/membench-jibin-002/ (SHA256SUMS verified). Parsed per
section 4 by gen_hierarchy.py, which builds asimov-memory-hierarchy.html.

Success criteria: all met except the per-region refill criterion. Every counted row
has seven counters and both timing rows with running equal to enabled; all 20
per-region rows put their own node 111k to 123k requests against 9k to 10.6k on the
others (node ids confirmed); the 8 MiB flushed row (52.71 ns) is within 0.5 ns of the
32 MiB fresh row (52.23); chip time 1.63 s. Not met: the 256 KiB per-region rows still
count 0.76 to 0.95 L3 read refills per load (fresh chains did not remove the prefetched
lines). A fix (--sparse chains, one line per 4 KiB page) is in the working copy for
run 3, written by the parallel session on 2026-11-02, not yet committed or run.

Findings: OCM latency by distance 19.6 ns (1 xp), 21.8 (3 xp), 24.6 (5 xp); per-core
SLC latency ordered by mean distance; multi-DSU DRAM writes 44 to 76 % faster than
run 1 (128 and 152 to 155 GB/s), with a per-DSU limit of 41 to 43 GB/s for two
writers; every other shared row within 3.5 %. Jesse's control run membench-jibin-003
(this code on run 1's firmware) is pending and being watched on the lab share.

Control run (membench-jibin-003, delivered 2026-11-03 01:09 UTC, copied and checksum-verified): run 2's code and kernel on run 1's firmware (SCP 0.34.0, TF-A 0.24.0), 1.610 s chip time, 63 commands exit 0. The multi-DSU write rows return to run 1's limit (86.6 to 88.8 GB/s, within 0.4 % of run 1), so the firmware caused run 2's faster writes. The 2+3 row gives 40.9 GB/s on both firmware sets (the per-DSU limit is not firmware-dependent). Every other row agrees with run 2 within 1.9 % except the per-region OCM rows (up to 3.05 ns apart, still 0.77 to 0.96 L3 refills per load). On the old firmware the 2+4+6+8 row put 2,105,333 requests on node 344 against 1.276 M on each other node, with the same memory-controller requests and SLC misses as on the new firmware (hypothesis: retries; test with hns_pocq_retry_all per node). asimov-memory-hierarchy.html section 9 covers it.
