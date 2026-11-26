# SPEC v2: `meshmap` (mesh latency map) and `run_map.sh` for the Asimov emulator

This replaces DESIGN.md. It folds in the three critiques (scratchpad/critique/c1.txt operations,
c2.txt measurement, c3.txt PMU). Background facts: scratchpad/understand/r1..r6.txt.

Repository: /home/jhan/workspace/ai-runs/asimov-repo/cache-mem-perf (git clone, HEAD b85d975, 7 local
commits ahead of origin; do NOT commit, do NOT push, do NOT touch git state).
Wording rule for all prose, comments, option help and CSV names: never the word "hop". A move between
crosspoints is "a step"; a load of a chain is "a load". Plain English: short sentences, one claim per
sentence, no idioms, define terms at first use in comments that import outside terms.

The run is on an RTL emulator operated by someone else: ONE chance per boot, no debugging there,
2,779 wall seconds per chip second, a guard kills the script (SIGKILL) at 12 chip seconds. So:
every failure must degrade, not exit, and every row must reach the file as soon as it exists.

## 1. What is measured
Cell = (kind, cpu, node). Node = one of the five home nodes (default ids 88,160,216,288,344 =
OCM regions 0..4, in that order). Per cell: `--reps` (7) timed passes of `lines` dependent loads, each
pass over a different random single-cycle chain on the same lines.

Kinds:
- `ocm-flush`: OCM lines of region n (node n). Recipe per rep: DC CIVAC on every chain line, DSB SY,
  timed chase. (The established OCM recipe. Needs no mesh counter and no classification.)
- `slc`: DRAM-backed lines whose home node is k (found by classification). Recipe per rep = one cycle:
  store-preload, evictor, timed chase (see section 4).
- `dram-flush`: the same lines as `slc`; per rep: DC CIVAC on every chain line, DSB SY, timed chase.
  The load goes to node k, misses, and is fetched from DRAM. This is the all-miss end of the counter
  scale and the per-node DRAM latency.
- `ocm-evict`: OCM lines of node k with the `slc` recipe (control: same recipe, other kind of line).
- `idle`: one row per pass through section 5's bracket with zero loads (the background of the counters).
- With `--no-perf` the DRAM kinds are named `slc-fake` and `dram-flush-fake` (homes are not measured).

## 2. Command line of meshmap
```
meshmap [--cpus LIST] [--last-cpus LIST] [--nodes ID,..] [--pmu NAME] [--sysfs DIR]
        [--event NAME] [--lines N] [--reps R] [--warm W] [--probe-loads P]
        [--max-classify-s S] [--out FILE] [--homes FILE] [--no-perf] [--no-ocm] [--selftest]
        [--ocm-dev PATH] [--no-hugetlb] [--no-thp]
```
- `--cpus` default `2,4,6,8,3,5,7,9` (order = measuring order). `--last-cpus` default empty: CPUs
  measured in a final block after every other row is written (meant for CPU 0, the kernel's CPU).
- `--nodes` default `88,160,216,288,344`; at most 8. OCM region i belongs to node i of the list (only
  when the list is the default length 5 and /dev/ocm maps; otherwise the OCM kinds are skipped).
- `--pmu` default `arm_cmn_0`. `--sysfs` default `/sys/bus/event_source/devices` (the directory that
  holds `<pmu>/type`, `<pmu>/cpumask`, `<pmu>/events/<name>`, `<pmu>/format/<field>`); the option
  exists so the host test can point it at a fixture directory holding the image's exact strings.
- `--event` default `hns_pocq_reqs_recvd_all` (the per-node request counter used to find homes).
- `--lines` default 2048 (multiple of 8, 64..4096). `--reps` default 7 (1..7: slots 0..6 of a line hold
  the chains, slot 7 is the preload's store target). `--warm` default 2 untimed cycles before the timed
  ones (doubled on the first CPU of each node for the kinds `slc` and `ocm-evict`).
- `--probe-loads` default 64 (flush-and-load pairs per probed line; may double itself, see 3).
- `--max-classify-s` default 1.0: time budget for classification; the program lowers `lines` to fit.
- `--out FILE`: rows and `#` lines are APPENDED to FILE and flushed after every line (fflush). Without
  it they go to stdout, also flushed per line. Progress and summary lines always go to stdout.
- `--homes FILE`: compact record of the classification (see 3).
- `--no-perf`: no mesh PMU; fake homes (line index mod number of nodes); for the x86 host.
- `--no-ocm`: skip the OCM kinds. They are also skipped, with a `#` line, when the device is absent
  or a region fails to map (never exit for that).
- `--selftest`: run the unit checks of section 8 and exit 0 or 1; touches no PMU and no device.

## 3. Order of work in the process (surest first)
A. Preflight (nothing here may end the process except a bad command line or no memory):
   - try sched_setaffinity on every CPU of both lists; drop a failing CPU with a `#` line
     (do not use common.h pin_cpu here: it exits).
   - buffer: ONE 2 MiB page through common.h alloc_dram (hugetlb, else THP, else 4 KiB; print which).
     32,768 lines. Fill it (stores). Never use more than one huge page (set-conflict bound).
   - map the OCM regions (own non-exiting code; region i at offset 0xE0000000 + i*0x100000, size
     0x40000, PROT_READ|PROT_WRITE, MAP_SHARED, device default /dev/ocm; reuse the constants and option
     names of common.h). Store one word in every used line (first touch).
   - /proc/self/pagemap: print the page frame number of the buffer's first 4 KiB page as a `#` line,
     or `# pagemap: unreadable (<errno text>)`.
   - core counters: one group on the calling thread per the common.h pattern (user only) with events
     cycles, 0x03 l1d_refill, 0x17 l2d_refill, 0xA2 l3d_refill_rd, 0x81BC l1d_refill_hwprf,
     0x81BD l2d_refill_hwprf, 0x05 l1d_tlb_refill. Reuse common.h's perf machinery (perf_open_* /
     perf_start / perf_stop / validity rule); add one new open function for this set next to the
     others in common.h if the existing ones do not offer it. Rows print "-" when not valid, as
     latency.c does. Note the thread changes CPU between cells: check whether common.h's group
     follows the thread (pid 0, cpu -1); if not, reopen per CPU.
   - bracket overhead: median of 32 empty brackets, printed as `# bracket_overhead_ns=`.
B. `ocm-flush` cells for every CPU of `--cpus`, every node. No mesh counter is open yet; the mesh
   columns print "-".
C. Mesh counters (skipped with `--no-perf`):
   - build each event's config from sysfs the way cmncount.c does (copy its read_text / set_field /
     build_event logic into meshmap.c; leave cmncount.c unchanged; comment that the code is a copy).
     Per-node events set bynodeid=1 and nodeid=<id>; sums leave both unset. pid -1, cpu = the PMU's
     cpumask CPU, no exclude bits, read_format = GROUP | TOTAL_TIME_ENABLED | TOTAL_TIME_RUNNING.
   - layout level 1: ONE group: leader = `--event` on node 0, then the other nodes, then the optional
     sums `hns_mc_reqs_local_all`, `hns_cache_miss_all`, `hns_snp_sent` (use the exact sysfs name if
     it differs: look for an event whose name starts with `hns_snp_sent`; none: column "-"). An
     optional member that fails to open is dropped (column "-").
   - check: one idle window (read, read) must show time_running == time_enabled and running > 0.
     If not: level 2 = close all, reopen the group with the per-node events only. If that fails too:
     level 3 = the per-node events opened alone (no group), each read by its own read().
     If level 3 fails: `# meshmap: no mesh counters (<why>)`, skip classification and the DRAM kinds,
     still run `ocm-evict` (it needs only the evictor) and finish.
   - print `# mesh counters: level=<1|2|3> events=<names> pmu_cpu=<n>`.
   - every later read checks enabled == running; a row whose bracket fails it prints "-" in the mesh
     columns. Deltas are signed 64-bit.
   - read floor: 64 empty windows (read, read) on the first measuring CPU; per-node median printed as
     `# read_floor: <five values>`; subtracted from every later delta of that node.
D. Classification of the DRAM lines (pinned to the first CPU of `--cpus`):
   - probe(line): load both neighbour lines (when inside the buffer); then P times {DC CIVAC on the
     line; DSB SY; load the line}; then ONE counter read. Delta = this read minus the previous read
     (the previous line's read; the first probe is preceded by one read).
   - decision rule on the floor-corrected deltas: winner w is the largest; accept when
     w >= 3*P/4 and runner-up <= w/4; otherwise ambiguous. An ambiguous line is retried up to 2
     more times, then left unused.
   - print the five raw deltas and the probe's elapsed ns of the first 32 probes and of the first 32
     ambiguous probes as `# probe line=<i> ns=<t> d=<..>` lines.
   - after the first 32 probes: projected time = mean probe time x lines needed (5/4 x nodes x lines);
     choose the largest `lines` in {requested, 1024, 512, 256} whose projection fits
     `--max-classify-s`; print `# classify: probe_ns=<mean> lines=<chosen> projected_s=<x>`.
   - if more than 1/4 of the first 256 probes are ambiguous and P < 256: double P, print a `#` line,
     restart classification from line 0 (redo the projection).
   - walk the buffer's lines in address order from line 0 and stop when every node has `lines` lines,
     or at the end of the buffer. If a node has fewer: lower `lines` to the largest of
     {2048,1024,512,256,64} every node reaches; below 64 for any node: `# meshmap: classification
     failed (<counts>)`, skip the DRAM kinds, continue with E for `ocm-evict` only.
   - print `# classify: probed=<n> ambiguous=<n> unused=<n> per_node=<five counts> lines=<n>
     probe_loads=<P> elapsed_s=<x>`.
   - `--homes FILE`: line 1 `# meshmap homes: first_line=0 count=<probed> nodes=<ids> pfn=<hex or ->`,
     then ONE character per probed line in address order, 64 per text row: the node's index 0..7,
     or `?` for unused. (About 10 KB.)
E. `slc` cells: every CPU of `--cpus`, every node. Then `dram-flush` cells, same loops. Then
   `ocm-evict` cells, same loops. One `idle` row per (cpu) before its first slc cell.
F. `--last-cpus` block: per CPU, the kinds in the order ocm-flush, slc, dram-flush, ocm-evict.
G. Final `# meshmap: done cells=<printed>/<requested>` line; exit 0 when equal, else 1. Summary of
   three lines of at most 120 characters on stdout (classification result, counter level, cells).

## 4. The cycle of the kinds `slc` and `ocm-evict` (cell = cpu c, node k)
1. Pin to c. Build `reps` chains over the cell's `lines` lines: chain r is one random cycle (Sattolo),
   pointer stored in 8-byte slot r of each line; seed from (kind, node, cpu, r). Built on the measuring
   CPU directly before the cell's warm-up.
2. One cycle:
   - store-preload: one 8-byte store into slot 7 of every chain line, in a new random order. (A store
     needs the line in the unique state, so every other copy in another cluster is invalidated; the
     line is then held only by the measuring cluster. It also keeps the rule "every slc line is stored
     after its last DC CIVAC".)
   - evictor: one independent load (not a dependent chain; sum the first word into a sink) of every
     line of the DRAM buffer that is NOT a chain line of the DRAM chain of node k, in a new order each
     cycle: order = perm[(a + i*s) mod n] with a random a and a random s coprime with n over one fixed
     random permutation built once per node. For `ocm-evict` the same list is used (the buffer minus
     node k's DRAM chain; when classification failed, the whole buffer).
   - mesh read; core counters start; clock; chase `lines` loads of chain r; clock; core counters stop;
     mesh read.
3. `warm` untimed cycles (using chain 0), doubled on the first CPU of each node, then `reps` timed
   cycles (chain r in cycle r). Print the row of each timed cycle at once.
For the flush kinds a "cycle" is: flush every chain line (DC CIVAC + one DSB SY at the end), then the
same bracket. No warm-up. `dram-flush` must store slot 7 of its lines after its last timed pass of a
cell (so the lines are dirty again before any later `slc` use).

The chase is the same routine as latency.c's (8 dependent loads per loop iteration plus a tail);
copy or share it without changing latency.c's behaviour. Clock = common.h now_s (CLOCK_MONOTONIC).

## 5. Output rows
First lines of the output (each run appends a new header block):
```
# meshmap: ns_per_load = elapsed_ns / lines; one row per timed pass. cpus=.. last_cpus=.. nodes=.. lines=.. reps=.. warm=.. probe_loads=.. event=.. backing=.. cntfrq_hz=..
kind,cpu,node,lines,rep,ns_per_load,cycles_per_load,l1d_refill,l2d_refill,l3d_refill_rd,l1d_refill_hwprf,l2d_refill_hwprf,l1d_tlb_refill,perf_cov,req_n0,req_n1,req_n2,req_n3,req_n4,mc_reqs,cache_miss,snp_sent,window_ns
```
- The header's req columns are named by node id: `req_88,req_160,...` (as many as nodes).
- Core counter columns are per load (same formats as latency.c: %.2f cycles, %.4f rates, "-" when
  refused or invalid); perf_cov as latency.c prints it.
- Mesh columns are COUNTS PER LOAD of the timed bracket, floor-corrected, %.4f; "-" when no counter.
  For `idle` rows (lines = 0) the mesh columns are raw counts and ns_per_load is "-".
- window_ns = time between the two mesh reads.
- The reading rules are NOT applied by the program; it never drops or stops on a row.

## 6. run_map.sh (phase M) and harness
- Header comment block like run_l3.sh's: what the phase measures, the dry-run sizing command.
- Remove the option `--kernel-cpus` from the arguments BEFORE sourcing lib_run.sh (lib_run.sh exits 2
  on an unknown option); with it, pass `--last-cpus 0` to meshmap.
- `[ -x ./meshmap ] || { echo "build first: make" >&2; exit 2; }` in the style of lib_run.sh line 36.
- Bring CPU 3 online (cpu_set_online) at the start; all of CPUs 2-9 stay online in this phase.
- `say "## M. ..."` single-letter phase marker (est_chip_time.py's regex needs one character).
- M step 1: write `$OUT/sysinfo-map.txt` (own file; do not truncate sysinfo.txt): the online CPU
  list, the line of /proc/config.gz for CONFIG_PROC_PAGE_MONITOR (or "config.gz unreadable"), the
  arm_cmn_0 cpumask. Skipped in dry-run like other sysinfo steps.
- M step 2: four control commands with the existing program, uncounted (plain `run`, not `cmn`):
  `latency --cpu $c --perf --mem ocm --ocm-regions $r --sizes 256K --fresh 3 --flush` for c in 2 8,
  r in 0 4 -> `latency-ocm-region$r-mapctl-cpu$c.csv` (only when HAVE_OCM).
- M step 3: `run meshmap-log.txt ./meshmap --out "$OUT/latency-map.csv" --homes "$OUT/map-homes.txt"
  --nodes "$HNS" [--last-cpus 0]`. NEVER under cmn/cmnq (cmncount would hold the mesh counters).
- `--quick` (x86 host): `./meshmap --selftest`, then `./meshmap --no-perf --no-ocm --cpus 3 --lines 256
  --reps 3 --out ...` (follow lib_run.sh's quick conventions for the CPU).
- `say` three summary lines at the end (grep the `# classify:` and `# meshmap: done` lines).
- finish_suite as the other scripts.
- est_chip_time.py: learn the meshmap command (classification at the pool bound: 5/4 x nodes x lines
  probes x (P x 60 ns + 7 us read, est.), plus per kind the loads of section 4 at the per-load
  costs the file already uses; evictor loads at 24 ns est.), and count its launch. Keep its existing
  outputs for the other scripts unchanged.
- Makefile: `meshmap` in `all` and `clean`, built like `latency`.
- README.md: Files table rows (meshmap.c, run_map.sh), phase table rows tagged "M (run 8)", terms in
  "Words used here" (home node, step, slice, evictor, classification), "Output format" for
  latency-map.csv and map-homes.txt, the reading rules of section 7, chip-time paragraph. Match the
  README's existing style. Do not rewrite existing text (the README's older "hop" wording stays).
- test: `test_meshmap.sh` is NOT wanted; the selftest plus the quick run are the tests.

## 7. Reading rules (for README; applied by the page generator later, not by the program)
- Attribution: req_k minus the mean of the other four, per load. The evictor's lines leave the
  cluster during the timed pass and are written to their own home nodes, so the other four are not
  near zero. `slc` and `ocm-evict` of the same cell should show the same pattern.
- Cache state: l3d_refill_rd per load near 1.0 (the load left the cluster). For `slc`, mc_reqs per
  load near the `ocm-evict` value of the same cell (near the `dram-flush` value would mean DRAM
  fetches). snp_sent near the idle value.
- A prefetchers-on boot is not a distance map (label: prefetcher effect).
- Hypothesis under test: per node, `slc` latency equals `ocm-evict` latency.
- The step counts are coordinate assumptions (crosspoint positions), not measured routes.

## 8. Selftest (must fail when the logic is wrong)
- decision rule: clear winner accepted; winner below 3P/4 rejected; runner-up above w/4 rejected;
  floor subtraction applied before the rule; ties rejected.
- chain builder: every chain is ONE cycle covering exactly the cell's lines, uses only its slot, and
  walking `lines` loads from the start returns to the start; two reps differ in order.
- evictor list: contains no chain line of node k, contains every other line of the buffer once;
  the re-indexed order (a, s) visits every element once.
- lines step-down: the chosen `lines` for given per-node counts and a time budget.
- homes file text round-trip for a small case.
- sysfs config builder against an in-memory or temp-dir fixture holding the image's strings:
  `type` = 8, events/hns_pocq_reqs_recvd_all = `type=0x200,eventid=0x5,occupid=0x0`,
  format/type `config:0-15`, eventid `config:16-26`, occupid `config:27-30`, bynodeid `config:31`,
  nodeid `config:32-47`; expected config for node 160 = 0x200 | 0x5<<16 | 1<<31 | 160<<32.

## 9. Not in scope
The page (asimov-c1nano-perf.html) and its generators; git commits; follow-up-run-plan.md.
