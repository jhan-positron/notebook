# Final report markdown
- Date
- Host

## Conclusion

## Prediction provenance and scorecard
Before presenting measured results, include a prediction provenance section.
For every test-level prediction, provide a table with at least:

| Prediction ID | Test | Metric | Evidence source | Source value(s) | Model/equation | Assumptions | Predicted value/range | Tolerance | Acceptance threshold | Result | Pass/fail | Model lesson |
|---|---|---|---|---:|---|---|---:|---:|---:|---:|---|---|

Rules:
- `Evidence source` must name the exact CSV/report/reference and row selector when
  available.
- `Model/equation` must show enough arithmetic or topology logic that another
  reviewer can reproduce the prediction.
- A user target or project goal belongs in `Acceptance threshold`; it must not
  be cited as evidence for the predicted value/range.
- If a number comes from a pre-work anchor or spec sheet rather than a measured
  source row, label it clearly and say why it applies to this environment.
- If a prediction is qualitative, state the expected ordering/shape and the
  falsification condition.
- The final report should explain the largest misses by pointing to the model
  component that failed or needed refinement.

## Test results
### up-time
The up time of the system is important data, make sure to note it.

### NODE-COUNT ADAPTIVITY
The example tables show the SNC/3 (6-node) shape. Under
SNC-OFF there are only node 0 (this socket) and node 1 (the other socket): collapse
the per-die rows to those two, and state it.
- Test 3 (mirror-die L3 rule) is SNC/3-ONLY: under SNC-OFF report the single
  whole-socket L3-hit latency and note the mirror rule does not apply (no dies).
- Test 2's per-die rationale (die0/die1/die2 distances) is SNC/3-only; under
  SNC-OFF it degenerates to local-socket vs cross-socket — keep that, drop the dies.
### Compare the two same-machine passes: SNC/3 vs SNC-OFF (both measured here).
The "vs pre-SNC3" columns are filled from the LIVE SNC-OFF pass of this project
(cite its date). Pre-work AMD/Intel is a secondary cross-check, not the baseline.

### At least the following comparisons are needed and feel free to add more:
- Add similar AMD BW test results from pre-work to each table; if there is no similar AMD data, state so
- Tables with ACPI distance need to have a column of "real distance", this tells us how accurate Intel spec is.

1. Single-thread L3 hit latency, cpu 0 + mem-node 0 (local die)
- Need to state working set sizes and the test is read only or RMW
- Here is an example table for reference (only for format reference, not for data):
| mem-node | ACPI distance | Latency | Description |
|---|---:|---:|---|
| 0 | 10 | **112.8 ns** | Local die (4 IMCs). Was 133 ns pre-SNC; −15%. |
| 1 | 15 | 138.2 ns | Adjacent die same socket |
| 2 | 17 | 165.3 ns | Far die same socket |
| 3 | 21 | 302.3 ns | Cross-socket "mirror" |
| 4 | 28 | 395.6 ns | Cross-socket far |
| 5 | 26 | 386.7 ns | Cross-socket far via alt path |


2. Single-thread DRAM latency per NUMA node, cpu 0, 4 GiB working set
- Measure the latencies from CPU 0 (NUMA 0) to memory node (NUMA node) 0, 1, 2, 3, 4 and 5. 

  Rational: This measurement provides data between CPU in first die to itself, its neighbor die and the furthest die. (Let me know if you disagree. Feel free to add caveats)

  Use 4GB as work-set size (If you prefer another size, explain to me and go ahead)

  Test both read-only and RMW, so we have 2 comparison tables.

  (Metric = single-thread random pointer-chase load-use latency, ns, via
   ptr_chase. read = pure load chain; RMW = same chain plus a store to the
   chased 64-byte line, via `ptr_chase --rmw`. Note RMW latency at L3 can be
   LOWER than read because the store's RFO prefetches the line into L2 — report
   it, don't "correct" it.)

- Measure the latencies from CPU 24 (NUMA 1) to memory node (NUMA node) 0, 1, 2, 3, 4 and 5
  Rational: This measurement provides data between CPU in the middle die to itself and its 2 neighbor dies. (I know I am making assumptions of die layout as sequential, let me know if you believe such assumption is too bold and if so, please suggest alternatives)
  Use 4GB as work-set size (If you prefer another size, explain to me and go ahead)
  Test both read-only and RMW, so we have 2 comparison tables.
- Measure the latencies from CPU 48 (NUMA 2) to memory node (NUMA node) 0, 1, 2, 3, 4 and 5
  Rational: This measurement provides data between CPU in third die to itself, its neighbor die and the furthest die. The expectation is the data of this measurement are same as the first. If the measurement are different, please explain and suggest further tests to validate the explanation.
  Use 4GB as work-set size (If you prefer another size, explain to me and go ahead)
  Test both read-only and RMW, so we have 2 comparison tables.
- Synthesize the above data and come up a model of DRAM latencies from a CPU (any CPU) to memory of 1) any NUMA node 2) NUMA nodes of the same socket 3) NUMA nodes of the the other socket (note: each is 1 latency value which is representative of the shape).  

3. Single-thread L3 hit latency 
- Here is an example table for reference (only for format reference, not for data):
| mem-node | ACPI dist | Mirror die in local sock | Measured at 4 MiB | Measured at 64 MiB |
|---|---:|---|---:|---:|
| 0 | 10 | die 0 (local) | 35.85 ns | 35.97 ns |
| 1 | 15 | die 1 (adjacent) | **60.05 ns** | 60.24 ns |
| 2 | 17 | die 2 (far same sock) | **84.54 ns** | 84.71 ns |
| 3 | 21 | die 0 (via mirror rule!) | **35.84 ns** | 35.95 ns |
| 4 | 28 | die 1 (via mirror rule) | **60.06 ns** | 60.24 ns |
| 5 | 26 | die 2 (via mirror rule) | **84.50 ns** | 84.72 ns |
- Test both read-only and RMW, so we have 2 comparison tables.

4. Single-thread DRAM read bandwidth per node, cpu 0, 4 GiB
- columns are memo-node, ACPI dist, Read BW, vs pre-SNC3
- each row of column "vs pre-SNC3" has data like, "<pre-SNC3 value> : <plus or minus percentage change from pre-SNC3>"

5. Cache-coherence latency for shared mutable data
 *How long it takes a modified cache line to migrate from one core's L1 to another core's*

6. CAT (Cache Allocation Technology) mini-experiment 

7. Multi-thread topology BW
- Here is one example table for reference of format:
| Topology | cpus | Read GB/s | rmw GB/s |
|---|---|---:|---:|
| A local die 0 | 0-23 | **383.9** | 767.4 |
| B cross-die from die 1 | 24-47 | 288.9 | 578.9 |
| C cross-die from die 2 | 48-71 | 289.2 | 577.1 |
| D mixed 3 dies | 0-7, 24-31, 48-55 | 351.6 | 709.7 |
| E cross-socket from socket 1 | 72-95 | **377.0** | 755.3 |

- Test 4MB/6MB/8MB/16MB/20MB work set
- The pre-work used 24 threads, is that right it is each of 24 CPU cores ran 1 thread? Yes or no, please add a brief description.
- The BW tests did not have definitive measurement whether satuation were achieved, correct? In other words, we do not know if the test results are really the utmost throughput up limit at the corresponding configurations, right? No need to update the tests to attempt satuation, just add a short description. 

8. Multi-thread big buffer BW
  Test per-thread working sets that span: (a) just past socket L3 (~aggregate
  > 432 MiB), (b) several x socket L3, (c) deep DRAM. Concretely 100/500/1000 MiB
  per thread is the intent, BUT the data-home node 0 lacks free memory and 1G
  hugepages can't express sub-GiB sizes -- so the executor may host this on a
  free node (node 2-5) and pick the page size that represents the sizes, and
  must state the substitution. The point is the DRAM-streaming regime + the
  local-vs-cross-socket ceiling, not the exact byte counts.

9. Multi-thread BW vs thread count (scaling curve)
   - bw_multi, cpus 0..N-1 -> node 0, N across 1..72. Two regimes: L3-resident
     (4M/thread) and DRAM (64M/thread, N<=24 on the home die). read + rmw.
   - Report where aggregate BW saturates and at what thread count; note the
     inflection at 24T (leaving the home die's cores).

10. Loaded latency (latency under memory load)
   - Victim ptr_chase on cpu 0 -> node 0 at a DRAM size (e.g. 1 GiB) and an L3
     size (e.g. 16 MiB), while K background threads (cpus 1..K) stream to the
     same node. Sweep K (e.g. 0,4,8,12,16,23). Report victim latency vs offered
     load -- the curve between unloaded latency and peak BW (queueing delay
     diverges as load nears the channel ceiling).
11. Saturated WHOLE-SOCKET DRAM bandwidth (the headline throughput number)
   - This is the test that answers "DRAM throughput of a 72-core socket." It must
     engage ALL of the socket's memory channels, so each thread first-touches its
     OWN local node (bw_multi --local, no single-node mbind). Single-node binding
     caps SNC/3 at one die's 4 channels (~204 GB/s) and is NOT a whole-socket
     number -- do not report it as one.
   - bw_multi --local, all of socket 0 (up to 72 threads), 64 MiB/thread, 4K pages.
     Sweep N = 1,2,4,8,12,16,24,32,40,48,56,64,72. read + rmw.
   - SATURATION MUST BE SHOWN: report the N where aggregate BW flattens or droops
     (not just the peak). Compare peak to the channel-count theoretical ceiling
     (12 x DDR5-6400 ~= 614 GB/s) and state the % achieved.
   - Cores are added memory-rich-node-first / memory-poor-node-LAST (probe per-node
     free memory at runtime), so the plateau is reached before any fragmented node
     is touched -- otherwise a SIGBUS on a memory-scarce node truncates the sweep.
   - APPLE-TO-APPLE pre-SNC3: re-run the IDENTICAL script under SNC-OFF; the only
     difference between the two curves must be the BIOS SNC mode (same --local,
     same per-thread size, same page size, same thread-count points, same cores).

12. Latency while whole-socket DRAM bandwidth is being driven (throughput/latency balance)
   - This is a separate test from Test 11. Test 11 answers "what is the saturated
     whole-socket throughput curve?" Test 12 answers "what latency does a
     single-core DRAM access see while that throughput load is active?"
   - Reuse the Test 11 background load shape exactly:
     `bw_multi --local`, socket 0 cores, 64 MiB/thread, 4K pages, same
     memory-rich-node-first core ordering, same thread-count points, and read +
     rmw patterns unless there is a documented reason to narrow the sweep.
   - For each background point, launch a long enough Test-11-style background
     bandwidth run, let it reach steady state, then run `ptr_chase` DRAM latency
     probes while the background load is still active.
   - Minimum victim probes per background point:
     1. `saturated_core`: a victim pinned to one logical CPU already included in
        the active `bw_multi` background set.
     2. `remote_unused_core`: a victim pinned to a remote/same-socket core that
        the Test 11 scaling prefix has NOT reached yet.
   - Interpret these two victim roles differently:
     - `saturated_core` is an end-to-end contention measurement. It includes
       memory queueing plus core scheduling/execution contention because the
       core is already running a bandwidth worker. Do not label it as pure DRAM
       latency.
     - `remote_unused_core` is closer to a memory-system interference
       measurement: a core not yet participating in the throughput ramp observes
       latency while other cores/nodes drive bandwidth.
   - Victim working set should be DRAM-sized, e.g. 1 GiB or 4 GiB, and use the
     same page mode as the background comparison unless explicitly testing page
     size. Record victim page mode.
   - Victim memory placement:
     - Required: victim-local memory, so the victim measures its own local DRAM
       latency under background socket load.
     - Optional but useful: victim to the active/saturated background node, to
       isolate queueing on the loaded node.
   - At high background thread counts there may be no `remote_unused_core` left.
     Do not silently drop the row; write `NA`/empty values with a note such as
     `no unused same-socket remote core remains at N=72`.
   - CSV output should be a separate Test 12 file, for example
     `results/<mode>/latency_vs_socket_bw_${HOST}_${STAMP}.csv`, not appended to
     Test 11. Include at least:

```csv
snc_mode,bg_pattern,bg_nthreads,bg_cpus,bg_agg_GBps,victim_role,victim_cpu,victim_mem_node,victim_ws,hugepage,median_ns,min_ns,max_ns,mean_ns,stddev_ns,notes
```

   - Run the identical Test 12 script in both SNC/3 and SNC-OFF. The only intended
     difference should be BIOS SNC mode and the resulting NUMA topology. If only
     one mode has been collected, add a Todo for the missing mode.
   - Report the tradeoff explicitly: identify where Test 11 throughput flattens
     or droops, then state what happens to `saturated_core` and
     `remote_unused_core` latency at the same points.

#### Tooling note: 
- bw_multi SIGBUSes at very large per-thread WS (>~256 MiB with
  2M pages). Use 1G/4K pages or smaller per-thread WS to stay in range; record
  any size that had to be dropped.
- bw_multi gains a `--local` mode: each worker first-touches its buffer while
  pinned (no mbind), so memory lands on the running thread's local node and ALL of
  a socket's channels engage. Without it, every multi-thread BW number is pinned to
  a single node = one die's 4 channels under SNC/3, silently understating
  whole-socket throughput by ~3x. Required for Test 11; harmless to Tests 9/10
  (which intentionally target one node and keep using single-node bind).

#### Page-size, TLB, and page-walk effects
Explicitly model page-size effects separately from memory-topology effects.

The benchmark suite uses a mix of normal pages, 2 MiB hugepages, and 1 GiB
hugepage-related system state. Do not let the report imply that every latency or
bandwidth difference is purely due to SNC/NUMA topology when address translation
may be part of the result.

Required reporting:

- Every table and figure that uses `ptr_chase`, `bw_avx512`, or `bw_multi` must
  include the page mode used for that measurement: `4K/none`, `2M`, or `1G`.
- If a requested page mode was unavailable and the script fell back, state the
  fallback in the table caption and figure footnote.
- For cross-mode comparisons, compare like page sizes whenever possible. If the
  SNC/3 and SNC-OFF runs use different page modes, mark that row as not
  apples-to-apples.

Add a small page-size sensitivity subsection:

- Pointer-chase latency: choose representative local-node working sets:
  - L3-sized, for example 16 MiB or 64 MiB;
  - DRAM-sized, for example 1 GiB or 4 GiB.
  Run/read existing rows for `4K/none`, `2M`, and `1G` where available.
- Streaming bandwidth: choose representative local-node and remote-node cases
  and compare `4K/none`, `2M`, and `1G` where available.
- Present this as a compact table:

```markdown
| Test | Mode | CPU(s) | mem-node | Working set | Page mode | Latency/BW | Notes |
|---|---|---|---:|---:|---|---:|---|
```

Interpretation requirements:

- Separate these effects in the text:
  - cache residency effects;
  - NUMA/SNC topology effects;
  - TLB reach/page-walk effects;
  - hugepage availability/fallback effects.
- For pointer-chase beyond cache, call out that random access can become
  sensitive to TLB reach and page walks in addition to raw DRAM latency.
- For streaming bandwidth, call out whether the access pattern is likely
  dominated by sustained memory channels or whether page translation overhead is
  visible.
- If perf counters are available, add a short optional cross-check using TLB or
  page-walk-related events. Do not hard-code event names blindly; use
  `perf list | grep -i -E 'dtlb|tlb|walk'` on the target system and record the
  exact event names used.

Todo requirement:

- If the current artifact set does not contain a clean page-size sweep, add a
  Todo item to run a page-size sensitivity pass for both SNC/3 and SNC-OFF.
  The Todo must name the scripts, page modes, working-set sizes, and expected
  output CSV paths.

#### Note of tests 9 & 10
- Tests 9 & 10 characterize the HARDWARE response surface -- how THIS silicon's
  latency degrades under load, and how its BW scales with concurrency. These are
  intrinsic to the chip, workload-independent, and are required predictor anchors
  (a real workload runs at some concurrency / load operating point, not at the
  single-thread-idle or peak-BW extremes).
- Two further dimensions are deliberately DEFERRED because they characterize
  SOFTWARE DEMAND, not hardware, and are a separate/larger modeling effort:
    * access-pattern spectrum (stride / prefetcher efficiency) -- the existing
      random + sequential anchors still BOUND a strided loop (floor..ceiling), so
      prediction degrades to a range, not a blank.
    * software code size (i-cache / front-end) -- the genuine blind spot; out of
      scope until software modeling is taken on.


### Cache-capacity-boundary effect (required call-out for any multi-size test)
When a size sweep has some sizes at/under a cache capacity (esp. L3) and some
just over it, EXPLICITLY state whether the larger (just-over) size is MORE
performant than the at/under one, and explain.

- Expected on this system: aggregate THROUGHPUT often PEAKS just past L3
  capacity, not at it. L3-hit delivery (mesh slices) and DRAM-miss delivery (IMC
  channels) are separate hardware, so a partial spill recruits the otherwise-idle
  DRAM channels in PARALLEL and their bandwidths ADD. It declines only once the
  spill is large enough that DRAM is the sole bottleneck.
- Support with per-size L3 miss rate (perf: LLC-loads / LLC-load-misses). The
  signature is a rising miss-rate ladder (e.g. ~4% -> ~17% -> ~84%) with the BW
  peak at the middle point.
- The relevant capacity is TOPOLOGY-DEPENDENT: per-die quota (~144 MiB) when
  threads and their data share one die; up to socket L3 (~432 MiB) when threads
  are spread across the socket's dies. State which applies.
- Do NOT assume "exceeds L3 => slower": that treats L3 and DRAM as serial
  alternatives; they are parallel subsystems.

### latency vs throughput
- do we see throughput and latency disagree in the tests? E.g. one configuration (cpu/cache/DRAM shape/workset) has best throughout but not best latency, or vise versa? if there is disagreement, explain the reason 

## Figures
Generate PNG plots that visually contrast the systems. Put them in
`REPORT/figures/` with:

- `make_figures.py`, which regenerates figures from result data.
- `figure_data.csv`, generated by `make_figures.py`, containing every plotted
  value with source filename and row selector.
- `README.md`, with captions, caveats, source files, and regenerate command.

### Figure-generation requirements
`make_figures.py` must be data-driven. Do not hard-code measured Intel arrays in
the plotting code.

Use this data-source policy:

- Read Intel SNC/3 data from `results/snc3/*.csv`.
- Read Intel pre-SNC3 / SNC-OFF data from `results/snc-off/*.csv`.
- If AMD raw CSVs exist and are usable, parse them too. If AMD data is only
  available from pre-work/writeup and no usable CSV is present, keep the AMD
  values in one clearly named reference block, label them as `pre-work`, and
  print/write that caveat for every affected figure.
- Prefer `results/MANIFEST.csv` or `results/MANIFEST.md` when present. Otherwise
  select the newest usable CSV per test/mode/prefix.
- Reject superseded or invalid CSVs automatically:
  - reject files with `FAILED` rows;
  - reject files whose plotted metric column contains zero/non-positive values
    for selected rows;
  - print every rejected candidate and why.
- Print an audit trail on every run:
  - figure name;
  - series name;
  - source CSV;
  - row selector;
  - number of selected rows.
- Write the same audit trail into `figure_data.csv`, along with the plotted
  values.

If `input-2-ai/util/make_figures_csv_reference.py` exists, use it as the
starting point for `REPORT/figures/make_figures.py` and adapt only the captions,
selectors, and any newly added tests. That reference script already implements
CSV loading, stale-run rejection, source/selector printing, and
`figure_data.csv` generation.

### Required contrasts
Include these figures, and add more if useful:

- Memory-hierarchy latency vs working-set size: line plot, one curve per system.
- Latency at each level: L1/L2/L3/DRAM-local/DRAM-remote bars.
- Single-thread DRAM read bandwidth, local and remote bars.
- Cache-coherence/c2c latency: near / same-socket-far / cross-socket bars.
- Multi-thread aggregate L3 bandwidth bars.

Hardware response-curve figures:

- BW vs thread count (Test 9): plot the curves that exist. If both SNC/3 and
  SNC-OFF data exist, plot both. If AMD has no non-empty CSV, do not fabricate
  an AMD curve; state `AMD missing: CSV absent/empty` in the footnote and Todo.
- Loaded latency vs background threads (Test 10): plot the curves that exist.
  If SNC-OFF has been run, include it. If not, plot SNC/3 only and add an
  explicit Todo to run the same script under SNC-OFF.
- Whole-socket saturated DRAM bandwidth (Test 11), when present: plot SNC/3 vs
  SNC-OFF response curves from `socket_sat_*.csv`; this is complementary to
  Test 9, not a summary of it.
- Latency while whole-socket DRAM bandwidth is active (Test 12): plot victim
  median latency vs Test-11-style background thread count from
  `latency_vs_socket_bw_*.csv`. Show separate curves or panels for
  `saturated_core` and `remote_unused_core`. Cross-reference Test 11 as the
  throughput curve that supplies the background load, but do not imply Test 12
  is a summary of Test 11; it is the latency/throughput tradeoff measurement.

### Plot conventions
- Use one consistent color per system across all figures.
- Put a legend on every figure.
- Annotate bars with values.
- Use human-readable axis units: KB/MB/GB, not `2^x` notation.
- Use log spacing only when the range spans many orders of magnitude, such as
  32 KB through 4 GB, and label ticks in human units.
- Each figure footnote must:
  - cross-reference related figures;
  - say whether the related figure is a different view of the same data,
    complementary data, or an independent metric;
  - name the source result CSV(s) and test number(s);
  - include caveats such as `remote = mean of N cross-socket nodes`,
    `thread counts differ`, `not saturated`, or `value from pre-work
    because CSV absent/empty`.
- Label which numbers were measured in this project and which were sourced from
  pre-work.
- Pick representative values honestly. If a bar is a favorable single point
  rather than a saturated ceiling or range, say so in the figure footnote or show
  the range.

### Required validation
Before considering figures done, run:

```bash
cd REPORT/figures
python3 make_figures.py
```

The run must:

- regenerate every PNG without errors;
- print source CSVs and selectors;
- write/update `figure_data.csv`;
- avoid using stale failed runs when a newer clean run exists.

Do a quick sanity check of `figure_data.csv`: sampled values in the file must
match the corresponding CSV rows under `results/`.

## Math model
## Analyze the gaps between predicts of the SNC3 and test results
## Suggest how to predict performance before porting a software
- The software currently run at AMD system
- The software currently run at the same Intel system with SNC3 disabled
In the above situations, how to use the following data (and more, please add) to predict the performance:
- metrics of the software at the currently running situation
- models constructed from this project
- test data from this project

## caveats
## Todo
- If there are tests needed to perform in pre-SNC3 environment, list here and document corresponding action plan after performing the tests.

- If there are anything currently cannot be done and they are helpful, list here.

## feedback to inputs
Good, bad and ugly of the markdown files at input_2_ai/:
- anything to improve?
- focus more on improvement on semantics or content, not just on wording/format. E.g. are inputs over constrained? are inputs less clear on goals and intentions?

## inputs to subsequent projects
Subsequent projects are not defined yet, however they sure will need to leverage this project. Summarize this project to help future projects.

Make this project whole and independent: include all the code, build files, scripts, etc. as needed to do independent rerun, do not depend on pre-work project.
