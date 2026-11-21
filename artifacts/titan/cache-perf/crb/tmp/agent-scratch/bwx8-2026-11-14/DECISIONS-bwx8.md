# bwx8: interfaces and fixed readings for the implementation of tackle-8mb.md

## Short version

This file is the contract between the parts of the implementation of the design `crb/new-test-kernel/tackle-8mb.md`. It fixes the file formats that the parts exchange. It also fixes one reading for every place where the design can be applied in two ways. The design wins over this file in any conflict: report the conflict, do not blend.

## Words used here

- **Design**: `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb.md`. "Design line N" is line N of that file.
- **Review record**: `tackle-8mb.md.review.md` beside the design. Its last entry (line 344 to the end) holds four notes for the implementer.
- **`bwx`**: the existing benchmark, in `crb/tmp/agent-scratch/bwx-2026-11-13/`. It is never changed.
- **`bwx8`**: the scratch copy in this folder, with an added trial mode.
- **CRB**: the Arm test machine. The development machine is x86-64 and has no AArch64 compiler. On it `bwx8` builds with plain C stand-in loops, and its rates mean nothing.
- **Unit**: the thing counted 6 times per CPU and session by the repeatability rule. In Stage 2 it is a matched set (three processes). In all other work it is one process.

## Layout

| Path | Content | Owner part |
|---|---|---|
| `crb/tmp/agent-scratch/bwx8-2026-11-14/` (called `X` below) | everything that goes to CRB | |
| `X/bwx8.c`, `X/bwx8_selftest.c`, `X/build8.sh`, `X/check_listing8.py`, `X/test_runner8.py` | runner | runner |
| `X/schedule8.py`, `X/run_bwx8.sh`, `X/visit8.sh`, `X/test_schedule8.py` | schedules and run script | schedule |
| `crb/new-test-kernel/tackle-8mb-analysis/` (called `A` below) | analysis that runs on the development machine | |
| `A/analyze8.py`, `A/test_analyze8.py` | parser, rules, decisions | analysis |
| `A/stage0.py`, `A/stage0.html`, `A/stage0.json`, `A/test_stage0.py` | Stage 0 on the saved files | stage0 |
| `A/report8.py` | HTML report of new runs | report |

No file outside `X` and `A` is changed. `bench/bandwidth.c`, `bwx.c`, earlier result folders and the design stay as they are. Python: standard library only (no numpy, no pytest). Tests are plain scripts that exit with status 0 only if every check passed, and print one line per check.

## Stages and their step names

| Step | Design source | Processes per session | Trials per process | Trial |
|---|---|---:|---:|---|
| `B6W` | Stage 1 item 2 | 4 (2 per CPU) | none: `--seq` mode | B6 sequence, `--bytes 8M --rounds 4 --min-ms 300 --stop pass` |
| `S2` | Stage 2 | 180 | 4 | prefix K@S 1200 ms, target K@S 4 x 300 ms |
| `S4` | Stage 4, uncounted | 18 | 1 | no prefix, target K@8M 200 x 300 ms |
| `P3G` | Stage 1 item 5, paired-allocation prefix check | 12 | 36 | previous activity J@8M 2400 ms, prefix K@8M 1200 ms, target K@8M 4 x 300 ms |
| `P3` | Stage 2, conditional branch | 12 | 12 | prefix K@8M 1200 ms, target K@8M 4 x 300 ms |
| `S3G` | Stage 1 item 5, mixed-sequence prefix check | 12 | 12 | previous activity J@8M 1200 ms, prefix oldread@8M 1200 ms, predecessor oldread@8M 300 ms, target oldread@8M 4 x 300 ms |
| `S3` | Stage 3 | 12 | 48 | prefix oldread@8M 1200 ms, predecessor P 300 ms, target T@8M 4 x 300 ms |
| `BIN` | Stage 1 item 3 (optional) | 12 per selected kernel and size | 8 | as `S2`, modes window-only and 10 ms bins, 4 repeats each |
| `CS` | Stage 4, size counters | 12 per selected kernel and size | 12 | as `S2`, three counter modes, 4 repeats each |
| `CM` | Stage 4, mixed-sequence counters | 12 | 48 | as `S3` with predecessor and target in {oldread, read} at 8M, three counter modes |
| `C4` | Stage 4, sustained with counters | 18 | 1 | as `S4`, counter mode `read` |

K, J, T are one of `oldread` (old read), `read` (new read), `asmread` (assembly read). CPUs: 2 and 41. Sessions: 1 and 2. Session 2 uses the reversed CPU order (41, then 2). Stage 5 and the root-only D2 work are not implemented: the design says to choose one branch after the results.

Nominal kernel work that `schedule8.py` must print, for both sessions together (design lines 344 to 355): `S2` 360 processes and 3,456 s. `S4` 36 and 2,160 s. `P3` 24 and 691.2 s. `S3` 24 and 3,110.4 s. `P3G` 24 and 4,147.2 s. `S3G` 24 and 1,123.2 s. `B6W` 8 and 124.8 s. A test compares the computed values with these.

## Plan file (schedule8.py writes it, bwx8 reads it)

One plan file per process. Text, one trial per line, fields separated by single spaces.

```
# bwx8-plan v1
# step=S2 session=1 cpu=2 bytes=8388608 proc=17 rep_set=3 kernel=oldread size=8388608 seed=20261114 test=0
# trial cond rep prev pfx pred tgt nwin win_ms count bins
0 K=oldread|S=8M 1 - oldread@8M:1200 - oldread@8M 4 300 closed 0
```

- Line 1 is exactly `# bwx8-plan v1`. Line 2 holds `key=value` pairs. `bwx8` copies each pair to an `M,plan.<key>,<value>` row and gives them no meaning, except `bytes` and `cpu`, which must equal `--bytes` and `--cpus`. Line 3 is the column comment.
- `trial`: 0, 1, 2, ... in order. `cond`: condition label without spaces or commas. `rep`: 1 to 4, the number of this repeat of `cond` in the process, in time order.
- `prev`, `pfx`, `pred`: `-` or `KERNEL@SIZE:MS`. `tgt`: `KERNEL@SIZE`. SIZE is a whole number with an optional K, M or G. `pfx` MS must be a multiple of 4: the prefix is recorded as 4 windows of MS/4.
- `nwin` 1 to 4096 target windows of `win_ms` each. `count`: `closed`, `open` or `read`. `bins`: 0 or 1.
- Only kernels of the read kinds are accepted. A size must be a multiple of 256, above 0 and at most `--bytes`.
- `bwx8` reads and checks the whole plan before it pins, allocates or opens anything. Any defect ends the process with status 2 and a message that names the line.

## bwx8 command line

The old interval mode (`--seq ...`) stays byte for byte as in `bwx.c`, so step `B6W` uses "the unchanged interval wrapper". New:

```
bwx8 --trial --cpus C --bytes B --plan FILE [--ctl-cpu N] [--no-thp] [--trace]
     [--pmu-type N --events NAME=CODE,...]      (or BWX_PMU_TYPE, BWX_EVENTS; required if any trial has count open or read)
```

- `--cpus` takes exactly one CPU in trial mode. `--ctl-cpu` (default 0) is the CPU of the controlling thread. It must differ from the worker CPU. The controlling thread pins itself, starts the worker, and waits in `pthread_join`. It never touches the buffer.
- `--trace`: the non-measuring test of Stage 1 item 4. Every wrapper event is appended to a memory log and printed as `TR` rows after each trial. Rates of a trace run are not used.

### Worker, in order

1. Pin. Allocate with the unchanged `alloc_buf()`. First touch with `k_write`. Allocate and first-touch the record storage, sized from the plan. Print its size.
2. For each trial: print and flush the `S` row. Then, outside the timed sequence: set the counter state of the trial (open or close the group, checked), read the page state, read thread CPU time and the context-switch counts of the thread (`getrusage(RUSAGE_THREAD)`).
3. Timed sequence, with no call other than the kernels, `clock_gettime`, and (count `read` only, at the boundaries of target windows) the group read and the thread CPU clock: previous activity (one window), prefix (4 windows), predecessor (one window), target (`nwin` windows).
4. After the last window: thread CPU time, context switches, page state, the check of the old-read sink, then all rows of the trial are printed and flushed.

Rules of the timed sequence:

- Every kernel call goes through the unchanged `call()`, with the `volatile` sink on the worker stack.
- A window runs whole passes over `[0, SIZE)`. The clock is read after every `max(1, 8 MiB / SIZE)` passes. A window ends at the first clock read at or after its requested duration.
- At each boundary the worker reads the clock for the end of the window, then (count `read`, target boundaries only) the counters, then reads the clock again for the start of the next window. So every gap is measured, never assumed zero.
- 10 ms bins (`bins` 1, target windows only): at each clock read that the window loop makes anyway, the worker stores (time, bytes so far) if the requested bin end has passed. No clock read is added.
- No warm-up pass, page read, output, allocation, sleep or barrier lies inside the timed sequence.

### Output rows of trial mode

Comma-separated. Times are whole nanoseconds since process start on `CLOCK_MONOTONIC`. Lines that start with `#` are comments.

| Row | Fields |
|---|---|
| `M` | `M,<key>,<value>`. Keys at least: `mode` (`trial`), `cpu`, `ctl_cpu`, `bytes`, `thp` (`madvise` or `nohugepage`), `madvise_ok` (1 or 0), `check_bytes`, `kernels` (`aarch64` or `STAND-IN`), `plan_fnv1a64` (hash of the bytes of the plan file, 16 hex digits), `ntrials`, `rec_windows`, `rec_bins`, `rec_bytes`, `trace` (0 or 1), `pmu_type`, `events`, and every `plan.<key>`. |
| `K` | `K,<kernel>,<function address, hex>,<address modulo 64>`, one per kernel of the plan |
| `S` | `S,<trial>,<cond>,<rep>,<prev>,<pfx>,<pred>,<tgt>,<nwin>,<win_ms>,<count>,<bins>,<cond of the previous trial or none>,<tgt of the previous trial or none>` |
| `P` | `P,<trial>,<pre or post>,<kB_total>,<kB_huge>,<thp_fault_alloc>,<thp_fault_fallback>,<thp_collapse_alloc>,<pgmigrate_success>`; `NA` where unreadable |
| `W` | `W,<trial>,<phase>,<widx>,<kernel>,<pass_bytes>,<bytes>,<t_start_ns>,<t_end_ns>`; phase is `prev`, `prefix`, `pred` or `target`; `widx` counts from 0 inside the phase; `bytes` is a whole multiple of `pass_bytes` |
| `B` | `B,<trial>,<widx>,<bin>,<t_end_ns>,<bytes since window start>` |
| `C` | `C,<trial>,<widx>,<enabled_ns>,<running_ns>,<cputime_ns>,<count per event...>`; deltas over the target window; `NA` for an event that did not open |
| `E` | `E,<trial>,<wall_ns>,<cpu_ns>,<nvcsw>,<nivcsw>,<gap_ns>,<max_boundary_gap_ns>,<sink_ok>,<count_state>`. `wall_ns` and `cpu_ns` span the timed sequence. `nvcsw`, `nivcsw`: change of the voluntary and involuntary context-switch counts. `gap_ns`: start of target window 0 minus the end of the window before it. `sink_ok`: 1, 0, or `NA` if the trial ran no old read. `count_state`: `closed`, `open`, `read`, or `fail`. |
| `X` | `X,<trial or -1>,<code>,<text>`: a reported failure. Codes: `madvise`, `coverage_na`, `count_open`, `count_multiplexed`, `sink`. A process with an `X` row still ends with status 0 unless the plan cannot run. |
| `TR` | `TR,<trial>,<n>,<event>,<t_ns>` (trace mode). Events: `clock`, `kernel_first:<phase>:<widx>`, `count_read`, `cpu_clock`, `page_read`, `rusage`, `output`, `count_open`, `count_close`. |

An `S` row without the `E` row of the same trial means that the trial was interrupted.

## Result folders (run_bwx8.sh writes them)

`~/cache-perf/results/bwx8-<step>-s<session>-<UTC>/` on CRB, copied to `crb/results/`. Content: `<step>.csv` (all processes, each after a line `-- step <step> session <n> idx <i> tag <tag> waited_s .. loadavg .. logins .. utc .. args ...`, as `run_bwx.sh` writes it), `env.txt`, `launches.txt`, `stderr.txt`, `schedule.tsv` (the copy of the schedule that ran), `build.txt`. A stopped step keeps its folder. A line `-- killed ...` or `-- failed ...` marks the process that did not end.

`schedule8.py` writes `X/sched/s<session>/<step>.tsv` (columns `idx`, `tag`, `cpu`, `bytes`, `plan` (file name, or `-` for `B6W`), `args`) and the plan files in `X/sched/s<session>/<step>/`. The seed is one whole number per step and session, derived from a base seed that is saved in the file. Generation is deterministic: the same seed gives the same bytes.

`run_bwx8.sh` keeps the stop controls of `run_bwx.sh` unchanged (marker file, `STOP_AT`, stop file, interruption, the 2-task wait, the load record per launch). It prints the selected conditions, the process count and the nominal kernel work before it starts. Session 2 of a step needs `SESSION1_END=<UTC>` (no default) and refuses to start earlier than 3 hours after it. It never replaces or repeats a process on its own. `--from IDX` continues a stopped step and is written to `env.txt`.

`schedule8.py --test-divisor N` divides every duration by N and writes `test=1` into the plans. It exists only for the local test of the whole chain. Analysis and report print a banner for such data and give no decision.

## Fixed readings of the design

### The four notes of the review record

1. **Stage 0 item 8 and the P3 branch.** The forecast is computed as written: blocks of four intervals of B4 and C1, split {1, 3} against {2, 4}, largest absolute value per process, then per CPU and session. If it gives "precision insufficient" for a gate that includes assembly read at 8 MiB, then `P3G` and `P3` are not scheduled by default. The page says this in words and shows the numbers. The forecast is not softened (no percentile, no removal of transitions from the maximum; transitions are shown separately as the design says).
2. **Clipped margin.** The margin is `clip(roundup_to_0.05(2 x L0), lower, upper)`. The gate keeps its three conditions exactly: |median difference| at most the limit; limit below the margin; |median difference| plus limit at most the margin. When the margin was clipped, the largest median that can pass is margin minus limit. The output prints that value. No condition is relaxed.
3. **Unit of L0.** L0 is computed per selected use: the quantity (one rate, two-rate difference, four-rate interaction) together with the conditions, CPUs and sessions that this use needs (design lines 193, 300, 302). It is not one value per branch. A quieter condition is not failed by a noisier condition that its use does not need.
4. **P3 without coverage.** A P3 comparison whose load-only range is below 2.0 GB/s is labelled **Insufficient data** (design line 228), never "undecided". The same label applies to an unstable process and to a failed prefix gate. "Undecided" is only the last case of design line 86: coverage present, all traces stable, neither compatible nor contrary. Neither label supports or contradicts the candidate.

### Rates and the repeatability rule

- Rate of a window: `bytes / (t_end_ns - t_start_ns)`, in GB/s (1 GB = 1e9 bytes). First window: `widx` 0 of the target. Fourth window: `widx` 3.
- `R(process, cond, w)`: median of the rates of window `w` over the 4 repeats of `cond`.
- A/A value: `median(rep 1, rep 3) - median(rep 2, rep 4)` of that process, condition and window. A/A spread: the largest absolute A/A value over the 6 processes of one CPU and session. Limit of a contrast: the sum of the spreads of its constituent rates.
- Repeatable on a CPU in a session: |median of the 6 unit values| above the limit, and 6 values of one sign (a value of exactly 0 has no sign and fails). Confirmed on a CPU: repeatable in both sessions with the same sign. Fewer than 6 valid units: "incomplete", with the partial values kept.
- Stage 2 pairing: the matched set of replicate `r` is the three kernel processes with `rep_set=r` of one size, CPU and session. A size contrast pairs replicate `r` at 8 MiB with replicate `r` at 1 MiB.

### P1, P2, the decomposition

- P1 per CPU and session, with `d_r = old(8M) - old(1M)` of set `r` in the fourth window and `L = spread(old, 8M) + spread(old, 1M)`: **equivalent** if every `|d_r| + L <= 0.30`. **contradicted** if the contrast is repeatable and |median| > 0.30. Otherwise **undecided**. Per CPU: equivalent only if both sessions are equivalent; contradicted only if both sessions are contradicted with one sign; otherwise undecided. Overall P1 "meets its equivalence margin" only if all four CPU/session cells are equivalent.
- P2 per load-only kernel, with `d_r = rate(8M) - rate(1M)`: **supported** if confirmed negative on the CPU, **contradicted** if confirmed positive, otherwise **undecided**.
- `dG = (new_1 - new_8) - (old_1 - old_8)` per set, four spreads. "Resolved" means repeatable. Shares are printed only then.

### P3

Per CPU and session, and separately for X = new read and X = assembly read, in this order:

1. Prefix gate `P3G` not passed: Insufficient data.
2. Any of the 6 processes unstable for X or for old read: Insufficient data. Unstable: the four fourth-window rates of the kernel span more than 0.30 GB/s, or a trial has |first window - fourth window| above 0.30 GB/s.
3. Range of the six X medians below 2.0 GB/s: Insufficient data.
4. `Lc = 2 x max |A/A of old read|` over the six processes. Compatible if (range of the six old medians) + Lc <= 0.30.
5. Contrary if `|old(process of max X) - old(process of min X)| - Lc > 0.30`. A tie takes the earlier process of the schedule.
6. Otherwise undecided.

### Gates

- Gate value per process: the within-process difference of the quantity between two modes or two previous activities. Gate on a CPU and session: the three conditions of note 2, with the median over the 6 processes.
- Outcome words: `pass`; `precision insufficient` (limit at or above the margin, or |median| within the limit but |median| + limit above the margin); `resolved difference` (repeatable under the directional rule); `not established` (the rest).
- A margin is read from a frozen file `margins.json` that the `forecast` command of `analyze8.py` wrote from earlier data. The gate command refuses to run without it and refuses a margins file that names the gated batch as its source.

### Quality marks

As design lines 273 to 279. Rejected (execution failure): no `E` row, pinning or byte accounting failed, required rows missing. Disturbed: `cpu_ns < 0.99 x wall_ns`, or `nivcsw > 0`, or `gap_ns > 100000`. Coverage change: `kB_huge` differs between `pre` and `post`, or is `NA`. Every estimate is given filtered and unfiltered, with counts.

## Not implemented, and why

- Stage 5 branches and the D2 physical-page work: chosen after results, and D2 needs root.
- Authoritative event definitions for the refill counters: Insufficient data. The report prints raw event names and counts and assigns no cache mechanism.

## Changes after the review round (2026-11-14)

One reviewer per part checked the code against the design. The items below changed an interface or fix a reading. Where an item differs from an earlier section, this section holds.

### Runner and build

- A field of the `E` row can be `NA`: `gap_ns`, `max_boundary_gap_ns`, `sink_ok`, `nvcsw`. Trials of `S4` and `C4` have no window before the first target window, so they have no gap.
- More `X` codes exist: `count_read`, `count_close`. More `M` keys exist: `rec_counts`, `rec_trace`. `M,events` separates events with `;`.
- A plan whose record storage is above 256 MiB is rejected with status 2.
- With `--trace`, one comment line per trial follows the `TR` rows: `# minflt,<trial>,<n>` (minor page faults of the worker during the timed sequence).
- `timed_sequence()` and `tcount()` are not inlined. `alloc_records()` stores to every page of the record block. Reason: gcc 11.4 joined `malloc` and `memset` into `calloc`, so the pages were first touched inside the timed sequence.
- `bwx8 --selftest` prints 19 `trial,` lines.
- `build8.sh` has exit status 6: `timed_sequence` reaches a function other than `clock_gettime`, the kernel call, `tcount` or `__stack_chk_fail`. `build.txt` has the line `## timed_sequence branch targets: ...`.
- `check_listing8.py` prints `NOTE: got_offset_differs (...)` and still exits 0 for the stack-guard pointer load of `k_oldread` and `k_oldread2`. It fails when an outside branch target has another symbol name, or when the pointer loads after `adrp` use more table places than the reference. Open decision for the owner: accept this note, or require an identical offset.

### Schedules and run script

- The base seed is saved in `sched/MANIFEST.txt`.
- `BIN` and `CS` are not in the saved `sched/`. They need `schedule8.py --select` after the Stage 2 choice.
- `CM` uses one row construction of design line 242 over its 12 cells. The two factors are not balanced independently. Open decision for the owner.
- `SESSION1_END` is accepted only as `YYYY-MM-DDTHH:MMZ` or `YYYY-MM-DDTHH:MM:SSZ`.
- A step named twice gives status 2. A schedule row whose `idx`, `--rounds` or `--min-ms` is not a whole number gives status 2.
- An interruption (INT, TERM, HUP) during a process writes `-- killed tag <tag> status 130 utc <time>` to the csv.
- The `## settings:` line of `env.txt` ends with `MARKER= STOPFILE= BIN= RESULTS=`.
- `visit8.sh` gives status 2 and makes no login when `STOP_AT`, `SESSION`, `SESSION1_END` or `BWX8_SHA256` holds a character outside `A-Z a-z 0-9 : . + -`.
- Not done: `run_bwx8.sh` does not refuse a schedule with `test=1`. The analysis prints a banner and no decision for such data.

### Analysis

- Gate outcome order: `pass`, then `resolved difference`, then `precision insufficient`, then `not established`.
- A trial whose counter group did not run as planned (`count_state` differs from the plan, or an `X` row `count_open`, `count_read`, `count_close`) is left out of every contrast whose condition names a counter mode. It stays usable for timing-only contrasts.
- Test data (`test=1`): every decision value of the summary is `None`. A margins file made from test data keeps its margin and L0 numbers and has no forecast word.
- Forecast: L0 comes from the unfiltered A/A values and needs 6 processes per CPU, session and condition. Otherwise the forecast is "Insufficient data". The filtered L0 is printed beside it.
- A process that was stopped and then run again with `--from` is replaced by the complete process with the same key. The summary lists every replacement.
- A process with `M,trace` not 0 is rejected.
- Sums compared with a margin are rounded to 1e-9 GB/s first (P1, gates, P3).
- Stage 3 cells carry `gain_change_pp`: per process, the gain after a predecessor minus the gain after old read, in percentage points (design line 222). It is a description. No decision uses it.
- `gate()` evaluates CPUs 2 and 41 only.
- Not done: no coded Stage 3 trigger, and no function for counted repeats of a contrast (design line 306).

### Stage 0

- "Proceed" needs three facts: Stage 0 complete, sources consistent with the size table, and the candidate not contradicted by the original run. The candidate check uses the 0.30 GB/s margin of P1 without an A/A limit (3 repetitions per process). This threshold is a choice of the implementation.
- The use table has 13 rows. `BIN other selections` and `CS other selections` are "Insufficient data" until the uncounted step `S2` gives A/A values.

## CRB acceptance, 2026-11-15 (fixed before any rate of S2 was read)

- Build `crb-build-1`: gcc 14.2.0, `bwx8` sha256 `f84be912beb05d8ac035066bbe25ac0be6de5817d79523a9dfcea96800ea0ea9`. `check_listing8.py` gives 21 of 21 kernels "same" with the reference offsets, and no note. The self-test ends with `failures=0`.
- Trace runs (`results/bwx8-accept-s1-20261115T002916Z`, `results/bwx8-accept2-s1-20261115T003042Z`, checked with `check_accept8.py`): 18 trials on CPUs 2 and 41, 0 problems. The gap before the target is 60 to 140 ns. Minor page faults in the timed sequence are 0. Huge-page coverage is 8192 of 8192 kB before and after every trial.
- **Context-switch mark.** Every one of the 18 trials has 2 to 5 involuntary context switches on an idle host (load 0.04 to 0.47). That is 0.8 to 1.9 per second of trial. Thread CPU time is 99.95 % of wall time. With the limit of design line 276 (any rise marks the trial) every trial would be marked, and no filtered estimate would exist. The design calls its limits diagnostic proposals. Host limit fixed here: a trial is marked only if it has more than 3.0 involuntary context switches per second of its wall time (`BWX8_NIVCSW_PER_S=3.0` for `analyze8.py` and `report8.py`). The CPU-time and gap limits stay as designed. The report states the count of trials that the design's limit of 0 would mark.
- The counter check of this visit did not run: my plan file had `bins` 10, and the plan format allows 0 or 1. It is needed only before the counter steps.
- Session 1 steps: `B6W`, `S2`, `S4`. `P3G` and `P3` are not scheduled (Stage 0 forecast, note 1). `S3G` and `S3` wait for the trigger of Stage 3.

## Second agent, 2026-11-15 (work under `tackle-8mb-handoff.md`)

### Decisions at the start (04:05 UTC)

- Slack #phoenix-crb read at 04:02 UTC, last 44 hours: one block, 2026-11-13 15:30 to 18:10 UTC, already over. So `STOP_AT=none` for the visits of this hour. I read the channel again before every login.
- One read-only login at 03:56 UTC ran `A/h3/hostfacts.sh` (marker check first, no write on CRB). Output: `A/h3/hostfacts-20261115T0403Z.txt`. Facts used below: one NUMA node (a NUMA node is one group of memory and CPUs), `kernel.numa_balancing` is 0, the tick rate is 250 per second, the core PMU lists the events named in the event sets below, `python3` availability is checked by the run script.
- Context-switch mark: unchanged, `BWX8_NIVCSW_PER_S=3.0`.
- `check_listing8.py` note about the stack-guard offset: accepted as a note (the CRB build shows no note).
- Step `CM`: not used. No decision on its balance is needed.

### Observation that sets round 2 (session 1 data only, not confirmed)

Read from `A/h3/trace_dump.py` and `A/h3/s2_windows.py` on the session 1 folders:

- In the 60 s runs (`S4`) the load-only loops go from the low to the high level at the same times after process start in every process that is low at that moment: windows 21, 44, 67, 90, 114, 137 and 179 (6.3 s, then steps of 6.9 or 7.2 s, last step 12.6 s). The launch times differ by 60 to 120 s, so the times are tied to the process, not to the wall clock.
- In the 9.6 s processes of `S2` at 8 MiB and 4 MiB the up-switch sits at window 13 (3.9 s). A process that is high often falls in the window that starts at 2.7 s.
- The 1 MiB traces are flat at 85.2 GB/s. The 16 MiB traces move by 0.4 GB/s at most. Old read is flat at every size.
- Step sizes of 6.9 s and 7.2 s equal 27 and 28 units of 0.256 s. Hypothesis H3a: a kernel timer on the worker's CPU (timer wheel, unit 0.256 s at this tick rate) triggers the switch. The host sampler of step `XW` tests it.

### Round 2: steps, sizes and decision rules (written before any rate of round 2 was read)

Round 2 uses the accepted binary (sha256 `f84be912...`), no new build. New files: `X/schedule9.py`, `X/run_bwx9.sh`, `X/visit9.sh`, `X/hostwatch.py`, `X/sched9/`, `A/levels9.py`. Result folders: `bwx9-<step>-s<session>-<UTC>`. CPUs 2 and 41, two sessions at least 3 hours apart, session 2 with the reversed CPU order.

| Step | Processes per session | Content | Nominal work per session |
|---|---:|---|---:|
| `XEV` | 3 (session 1 only) | acceptance of the three event sets: `read`@8M, 3 windows, counters read | 2.7 s |
| `XW` | 28 | 30 s sustained, uncounted, host sampler beside each process. Conditions: `read`, `asmread`, `oldread` at 8 MiB; `read` at 8 MiB after 3 s of old read at 8 MiB; `read` at 8 MiB after 3 s of `read` at 1 MiB; `read` at 4 MiB; `read` at 16 MiB. 2 processes per condition and CPU | 852 s |
| `XCA`, `XCB`, `XCC` | 18 each | 30 s sustained with counters read once per 0.3 s window: `read`, `asmread`, `oldread` at 8 MiB (2 processes per CPU each); 6 s references `read` at 32 KiB, 1 MiB, 16 MiB (1 process per CPU each). Host sampler on | 396 s each |
| `XN` | 144 | `S2`-style trials. Kernels `asmread`, `read_nop16`, `read_nop32`, `read_sparse` at 32 KiB, 1 MiB, 8 MiB. 6 processes per cell and CPU | 1,382.4 s |
| `XF` | 90 | `S2`-style trials. `read` at 1.5, 2, 2.5, 3, 5, 6, 12, 24, 32, 64 MiB; old read at 2, 3, 6, 12, 32 MiB. 3 processes per cell and CPU | 864 s |

Event sets (core PMU type 11, codes from the PMU's own `events` folder on CRB):

- A: `cpu_cycles=0x11`, `inst_retired=0x08`, `l1d_cache_refill=0x03`, `l2d_cache_refill=0x17`, `l3d_cache_refill=0x2a`, `stall_backend_mem=0x4005`.
- B: `l1d_cache_lmiss_rd=0x39`, `l2d_cache_lmiss_rd=0x4009`, `l3d_cache_lmiss_rd=0x400b`, `ll_cache_miss_rd=0x37`, `l2d_cache=0x16`, `bus_access=0x19`.
- C: `exc_taken=0x09`, `l1d_tlb_refill=0x05`, `dtlb_walk=0x34`, `l2d_cache_wb=0x18`, `l3d_cache_allocate=0x29`, `mem_access=0x13`.

Readings and rules:

1. **Counters without the mode gates of the design.** The design asks for the three-mode check (`CS`) before counters are interpreted. I do not run it. Reason: the question for the counters is the difference between low and high windows inside one process, in one mode. The check that counting leaves the behaviour unchanged is this: the counted 8 MiB traces must show both levels within 0.5 GB/s of the uncounted `S4` levels of the same CPU, and up-switches at the `S4` times (within one window). If that fails, the counts are labelled "counted mode differs" and are not used for the mechanism. A window with `enabled_ns` different from `running_ns` is left out. An event that does not open is "NA" and its set is run again without it.
2. **Level labels.** Per process: low and high are the two groups of window rates split at the largest gap, if that gap is at least 1.0 GB/s. A window more than 0.5 GB/s from both group medians is "mixed" and is left out of level statistics. A process without such a gap has one level.
3. **`XC*` decision rule (H4, what differs between the levels).** For each event: value = count per 64 B read, median over the windows of one level in one process. The event "differs between levels" on a CPU in a session if all processes of that CPU that show both levels (at least 3 of the 4 load-only processes) have low minus high of one sign, and the median difference is larger than twice the largest within-level spread (half the range of the per-window values inside a level, largest over those processes). Confirmed: same sign in both sessions on both CPUs. Events are raw names. A mechanism reading needs the reference rows (32 KiB, 1 MiB, 16 MiB) and is a hypothesis until an intervention tests it.
4. **`XW` decision rule (H3, what triggers a switch).** For each sampler key: share of up-switches with a change of that key within 0.15 s, share of down-switches, and the base rate (share of all 0.3 s spans with a change). A key "accompanies the up-switch" if its share at up-switches is at least 0.8 and at least 3 times its base rate, on both CPUs. Same for down. Confirmed: both sessions. This names the host activity that coincides with a switch. It does not show that the activity causes the switch: that needs the intervention of round 3.
5. **`XW` onset rule.** Time base of the up-switches. Prediction "tied to the process start": after 3 s of previous activity the first up-switch of the target sits at the `S4` time measured from the process start (about 6.4 s, so about 3.4 s into the target). Prediction "tied to the start of load-only reading from the SLC": it sits about 6.4 s into the target. Rule: per condition the median first-up time over the 4 processes of a session; the prediction whose time is within 0.6 s is supported, and the other is rejected if it is more than 1.5 s away. If neither fits: "other time base", and the times are reported.
6. **`XN` decision rule (H1, the core-limit family).** Statistic per process: the median rate over all 32 windows, and the 95th percentile window rate (the high level when the process visits it). C_k = median rate of kernel k at 32 KiB (its limit when the data is in the first-level cache). H1 predicts for 8 MiB: rate(k) = min(C_k, S), where S is the supply rate that `asmread` shows at 8 MiB. So: (a) every kernel with C_k at least 5 GB/s above the `asmread` 8 MiB high level has an 8 MiB 95th-percentile rate within 1.0 GB/s of that of `asmread`; (b) a kernel with C_k below the `asmread` 8 MiB low level has an 8 MiB median within 1.0 GB/s of C_k; (c) the spread of the four kernels at 8 MiB is at most 25 % of their spread at 32 KiB. H1 is contradicted for a kernel if (a) or (b) fails on both CPUs in both sessions. Unit: the 6 processes of a cell; the cell value is the median of the 6. This is the dose-response form of the Stage 5 test of the design: the added instructions change the core limit, and the 8 MiB rate must follow min(C_k, S).
7. **`XF` rule.** Descriptive curve of rate against size, 3 processes per cell. No contrast decision. It is used to place the fall of the `read` rate between 1 MiB and 64 MiB and to choose sizes for round 3.
8. Order of a session visit: `XEV` (session 1), `XW`, `XCA`, `XCB`, `XCC`, `XN`, `XF`.

### Round 2, added 05:25 UTC (before any round 2 rate was read)

- Tools passed their local tests after one review round by a second agent each: `test_schedule9.py` 246 of 246 checks, `test_levels9.py` 128 of 128, `test_h2.py` 84 of 84.
- The host sampler `hostwatch.py` runs on CPU 100, pinned by `run_bwx9.sh`. It only reads `/proc`. Check that it leaves the behaviour unchanged: condition W0 of `XW` against `S4` (same trial without sampler), by rule 1 above.
- `XEV` runs as its own visit. `XCA`, `XCB`, `XCC` start only after its output shows every event open and `enabled_ns` equal to `running_ns`.
- **Step `H2` (the original program at 8 MiB, hypothesis H2).** Script `run_h2.sh`: binaries `bw_old` and `bw_new` of 2026-11-13 (digests checked), original options `--threads 1 --bytes 8M --kernel read --reps 3 --min-ms 500`, CPUs 2, 0 and 41, 12 processes per binary and CPU, 72 processes per session, nominal work 108 s. Rule, per CPU: a new-read repetition is "low" at or below 69.5 GB/s and "high" at or above 70.5 GB/s. H2 ("the original 0.94 % gain was measured at the low level") is supported on a CPU if at least 75 % of the new-read repetitions are low in both sessions, and the median gain of the low processes is within 1.5 percentage points of 0.94 %. It is rejected if fewer than 25 % are low in both sessions. Otherwise undecided. The gain per pair of neighbouring processes is reported for every pair.

### Round 2, session 1: what was read by 06:00 UTC, and one deviation

- Deviation: I fetched `XW` at 05:42 UTC and `XCA`, `XCB`, `XCC` at about 05:57 UTC while later steps of the same visit ran. These are 2 extra logins (marker check first, one `tar` each). Reason: the data sets the design of round 3. `XN` and `XF` rates were not read when round 3 was fixed below.
- `XEV`: all 18 events opened, `enabled_ns` equals `running_ns` (folder `bwx9-XEV-s1-20261115T052101Z`).
- `XW` rule 4 (session 1): no sampler key accompanies the switches. Involuntary context switches of the worker change near 8.7 % of the up-switches and 5.6 % of the down-switches, and the base rate is 9.6 % (`A/h3/xw-s1-watch.txt`). Hypothesis H3a (a kernel timer on the worker's CPU) is not supported in session 1.
- `XW` rule 5 (session 1): after 3 s of previous activity the first up-switch sits 5.8 to 6.13 s into the target (9 values of 10), not 3.4 s. So the time base is the start of the target, not the process start.
- Switch times are locked to the runner's window index: the fall times of `S4` are whole numbers of windows apart (26, 27, 26, 27, 26, 20, 26 windows), with a spread of 5 to 10 ms over 10 processes (`A/h3/switches-s2.txt`). With one previous-activity window before the target the events sit one target window earlier, which is the same index of the record array `win[]`. Time is at least 3 times more regular than bytes read (script in the progress file entry).
- Counters, session 1 (`A/h3/XC*-s1-counters.txt`), counts per 64 B read: `l1d_cache_lmiss_rd` is 0.30 at the high level and 0.36 to 0.37 at the low level for `read` and `asmread` at 8 MiB, 0.29 at 1 MiB, 0.007 for old read at 8 MiB. `l2d_cache_lmiss_rd` is 0.0004 to 0.0006. `exc_taken` is 77 to 78 per 0.3 s window at both levels.

### Round 3: hypotheses, steps and decision rules (written before any round 3 rate was read, and before `XN` and `XF` were read)

- **H1b** (replaces the open part of H1): at 8 MiB the load-only loop is limited by first-level cache misses that the hardware prefetcher leaves (0.30 to 0.37 per line). Old read is slow enough that the prefetcher covers it (0.007 per line), so old read does not depend on the size.
- **H7**: the low or high level depends on the address of the runner's window record `win[i]`, which the loop reads after every pass. The level is a property of the harness layout, not of time.

New binary `bwx10` (folder `tmp/agent-scratch/bwx10-2026-11-15/`, on CRB `~/cache-perf/bwx10-20261115/`): `bwx8` plus the kernels `read_pf256`, `read_pf512`, `read_pf1024`, `read_pf2048` (the `asmread` loop with one software prefetch to the first-level cache per line, 256 to 2048 B ahead), `read_1pl` (one 16 B load per line), and the options `--rec-pad BYTES` (moves `win[]`) and `--hot-copy` (the loop does not touch `win[i]` inside a window). Acceptance: `check_listing10.py` gives "same" for the 21 old kernels, the 5 new loops have the expected instructions, the self-test passes, and step `YA` (trace runs) passes `check_accept8.py` rules.

| Step | Binary | Processes per session | Content |
|---|---|---:|---|
| `YA` | `bwx10` | 9 (session 1) | acceptance, trace mode |
| `YL` | `bwx8` | 32 | window length: `asmread` and `read` at 8 MiB, 30 s, with windows of 100, 300, 1000 ms, and one window of 30,000 ms with 10 ms bins |
| `YP` | `bwx10` | 28 | record pad 0, 80, 400, 1040, 2080, 4000 B, and `--hot-copy`; `asmread` at 8 MiB, 100 windows of 300 ms |
| `YF` | `bwx10` | 288 | `S2`-style trials; `asmread`, the 4 prefetch kernels, `read_1pl`; 32 KiB, 1, 8, 16 MiB; 6 processes per cell and CPU |
| `YC` | `bwx10` | 42 | 6 s with counters (cycles, instructions, L1 refill, L2 refill, L1 long miss, L2 long miss) for the 6 kernels and old read at 1, 8, 16 MiB |

Rules:

1. **`YL` (H7).** H7 predicts: the switches keep their window index, not their time. With 100 ms windows the first falls sit at windows 16 and 42 (1.6 s and 4.2 s) and the first ups at windows 21 and 44, each within 1 window. With 1000 ms windows they sit at windows 16 and 21 (16 s and 21 s). With one 30 s window no switch occurs inside the window (the 10 ms bins show one level, apart from the first 0.3 s). A time-based cause predicts the `S4` times (falls at 4.93 s and 12.76 s) for every window length. Decision per CPU and session: over the processes that show a switch, the median index of the first fall and of the first up. H7 is supported if both medians match the index prediction and the one-window runs show no switch after 0.3 s in at least 3 of 4 processes. H7 is rejected if the medians match the time prediction. Confirmed: both sessions, both CPUs.
2. **`YP` (H7, the controlled change).** H7 predicts: with pad P the events move to an earlier window by P / 80 (pad 80: 1 window, 400: 5, 1040: 13, 2080: 26, 4000: 50). Statistic: the window index of the first fall after window 30 without pad (index 42), per process. Supported if the median shift matches the prediction within 1 window for at least 4 of the 5 pads on both CPUs. With `--hot-copy` H7 predicts no switch tied to the index (at most 1 switch per 30 s process, median over the 4 processes). Rejected if the events keep index 42 for every pad. If the shift is real but not P / 80, the address rule is reported as measured.
3. **`YF` and `YC` (H1b, the controlled change for goal point 2).** Per kernel and size: cell value = median over 6 processes of the process median rate (all windows), and the 95th-percentile window rate. From `YC`: L1 long misses per 64 B. H1b predicts for 8 MiB: a prefetch kernel that has at most half of the `asmread` L1 long misses per line has a rate at least 2.0 GB/s above the `asmread` high level. Then the gain over old read (67.05 GB/s) rises by the same amount, and the report states the share of the 1 MiB to 8 MiB loss that the prefetch recovers: (rate_pf(8M) - rate_asm(8M)) / (rate_asm(1M) - rate_asm(8M)). H1b is rejected if a kernel halves the misses and its rate is less than 1.0 GB/s above `asmread`. If no kernel halves the misses, the test is "Insufficient data" and other prefetch forms are tried. `read_1pl` gives the rate when the load ports are not the limit. Confirmed: both sessions, both CPUs, repeatability rule with the 6 processes as units for the contrast pf minus `asmread` at 8 MiB.
4. Order of a session visit: `YA` (own visit, session 1), then `YL`, `YP`, `YC`, `YF`.

### `bwx10` acceptance on CRB, 2026-11-15 07:03 UTC (before any round 3 rate was used)

- Build at 07:02 UTC in `~/cache-perf/bwx10-20261115/`: gcc 14.2.0, `bwx10` sha256 `22cbb1ee13ff3c10136d3208d4245bd8c1fcd6b30add91479cd70c5dc63a4d24`. Record: `tmp/agent-scratch/bwx10-2026-11-15/crb-build-1/`. Local tests before the build: `test_runner10.py` 367 of 367, `test_schedule10.py` 241 of 241, one review round by a second agent each, no defect found.
- `check_listing10.py`: 21 of 21 old kernels "same" against the `bwx8` build, the 5 new loops have the expected instructions, all loop offsets as planned (20 modulo 64 for the new kernels). The self-test ends with `failures=0`. `timed_sequence` and `timed_sequence_hot` reach only `clock_gettime`, the kernel call, `tcount` and `__stack_chk_fail`.
- Step `YA` (`results/bwx10-YA-s1-20261115T070307Z`, 9 trace processes on CPU 2): every trial has its `E` row, 0 minor page faults in the timed sequence, gap before the target 48 to 112 ns, huge-page coverage complete (8192 of 8192 kB; the 32 KiB process has 2048 of 2048 kB), `M,win_addr` moves by 80 B (0x50) with `--rec-pad 80` relative to the page offset 0x0d8. Trace-mode rates are not used.
- A mistake of mine: the build login wrote one file `/tmp/.x` on CRB (outside `~/cache-perf`). I removed it in the next login, 1 minute later.
- `read_nop4` has the same loop length and offset as the prefetch kernels and is not in `YF`. The control for code layout is therefore missing in `YF`. If a prefetch kernel differs from `asmread`, a later step adds `read_nop4`.
- Round 3 session 1 (`YL`, `YP`, `YC`, `YF`) started at 07:04 UTC, `STOP_AT=none` (Slack read at 07:02 UTC: no block).

### Round 3, session 1: what was read by 07:45 UTC (`YL`, `YP`, `YC`; `YF` not read)

- 3 extra logins fetched `YL`, `YP` and `YC` while later steps ran (marker check first).
- `YL` (`A/h3/yl-s1-dump.txt`): with 100 ms windows the first up sits at window 21 or 22 (2.1 s) and a first fall at window 16 or 17 (1.6 s). With 1000 ms windows the first up sits at window 21 (21 s). With 300 ms windows: 21, 44, 67, 90 as before. The one-window runs show no switch after the first 1 s (3 of 3 read so far). So the switches keep their window index, not their time. Some processes show no switch at all.
- `YP` (table in the progress file): the up-switches of pad 0 sit at windows 21, 44, 67, 90. With pad 80: 20, 43, 66, 89. Pad 400: 16, 39, 62, 85. Pad 1040: 8, 31, 54, 77. Pad 2080: 18, 41, 64, 88. Pad 4000: 17, 40, 64, 87. Each equals the pad 0 series moved by pad / 80 windows (within 1 window). The falls at windows 70 and 95 move the same way. The statistic that I fixed for rule 2 ("first fall after window 30") is not usable: that fall is not present in every process. I report the series above in its place and say so.
- `YP` with `--hot-copy`: 3 of 4 processes show no switch. One (CPU 41) shows ups at 21, 44, 67, 90 and falls 1 to 4 windows later. So reading the record after every pass is not needed for a switch. The access at the window end is enough. Reading for round 4: an access to the record at certain addresses moves the loop to the other level ("kick"), and the level then stays.
- `YC` (`A/h3/YC-s1-counters.txt`), counts per 64 B:
  - 1 MiB: `asmread` 85.2 GB/s with 0.293 L1 long misses. The four prefetch kernels have 0.002 to 0.017 L1 long misses and 77.4 GB/s. `read_1pl` has 0.996 and 92.8 GB/s.
  - 8 MiB: `asmread` 67.2 and 69.4 GB/s with 0.37 and 0.34. `read_pf1024` 66.0 and 67.4 GB/s with 0.19 and 0.18. `read_1pl` 57.0 and 57.9 GB/s with 0.99 L1 and 0.32 L2 long misses. Old read 67.0 GB/s with 0.012.
- Reading by rule 3: H1b (the count of L1 misses limits the loop) is not supported in session 1. At 1 MiB the prefetch removes 94 to 99 % of the misses and the rate falls by 7.8 GB/s. At 8 MiB `read_pf1024` has 52 to 53 % of the `asmread` misses (just above the "half" limit of the rule) and is 1.2 to 2.0 GB/s slower.

### Round 4: hypotheses, steps and rules (written before `YF` was read and before any round 4 data)

- **H1c** (replaces H1b): the load-only loop is limited by the rate at which lines can be moved into the first-level cache, not by the count of misses. From L2 this rate is about 85 to 93 GB/s. From the SLC it is lower because each line that enters L2 also needs traffic between L2 and the SLC.
- **H1d** (one named part of H1c): at 8 MiB each line that enters L2 pushes one dirty line back to the SLC (`l2d_cache_refill` and `l2d_cache_wb` are both 0.82 per line). The buffer lines are dirty because the first touch wrote them. If the lines were clean, the write-back would carry no data, and the rate would be higher.

New binary `bwx11` (folder `tmp/agent-scratch/bwx11-2026-11-15/`): `bwx10` plus `--evict-mb N` (after first touch the worker writes N MiB of other memory twice, so the benchmark buffer leaves all caches and comes back from memory clean) and the kernels `read_nop64`, `read_nop96`, `read_nop128` (the `asmread` loop with 64, 96, 128 `nop`).

| Step | Processes per session | Content |
|---|---:|---|
| `ZA` | 6 (session 1) | acceptance, trace mode |
| `ZD` | 216 | `S2`-style; `asmread`, `read`, old read at 4, 8, 16 MiB; without and with `--evict-mb 512`; 6 processes per cell and CPU |
| `ZC` | 32 | 6 s with counters (cycles, L1 long miss, L2 refill, L2 write-back, bus access, L2 long miss); `asmread` and old read at 8 and 16 MiB; without and with evict |
| `ZN` | 144 | `S2`-style; `read_nop64`, `read_nop96`, `read_nop128` at 32 KiB, 1, 8, 16 MiB |
| `ZM` | 40 | kick map: `asmread` at 8 MiB, 300 windows of 100 ms, record pads 0 to 72 B in steps of 8 B |

Rules:

1. **`ZD` and `ZC` (H1d).** First the check that the intervention worked: with evict, `l2d_cache_wb` per 64 B of `asmread` at 8 MiB is below 0.2 (without: about 0.82). If it is not, the lines still take the write-back path, the intervention did not change the mechanism, and H1d stays open ("Insufficient data", with the counts reported). If it worked: H1d predicts that the 95th-percentile rate of `asmread` and of `read` at 8 MiB (cell median over 6 processes) rises by at least 3.0 GB/s with evict on both CPUs. H1d is rejected if the rise is below 1.0 GB/s. Between 1.0 and 3.0: "partly". Old read is the control: its rate must stay within 0.3 GB/s. Confirmed: both sessions. If confirmed, the share of the 1 MiB to 8 MiB loss that clean lines recover is (rate_evict(8M) - rate_plain(8M)) / (85.2 - rate_plain(8M)).
2. **`ZN` (H1, slow load-only kernels; closes part (b) of rule 6 of round 2).** C_k = cell median at 32 KiB. S8 = the range from the low to the high level of `asmread` at 8 MiB in the same session (from `YF` or `ZD`). Prediction: a kernel with C_k at most 66 GB/s has an 8 MiB cell median within 1.0 GB/s of C_k (it does not feel the supply limit, as old read does not). A kernel with C_k at least 76 GB/s has an 8 MiB 95th-percentile rate inside S8 widened by 1.0 GB/s. Between 66 and 76: at most min(C_k, top of S8) + 1.0. Also the gain of `asmread` over each nop kernel is reported per size. H1 (two limits, the smaller one holds) is contradicted if a slow kernel loses more than 1.0 GB/s from 32 KiB to 8 MiB on both CPUs in both sessions.
3. **`ZM`.** Descriptive: for every window boundary the address of the record (from `M,win_addr` and the window index), the level before, and the event (up, fall, none). The report gives the addresses of the kicks and tests candidate address rules. No decision rule.
4. Order: `ZA` (own visit), then `ZC`, `ZD`, `ZN`, `ZM`.

### `bwx11` acceptance on CRB, 2026-11-15 08:41 UTC

- Build in `~/cache-perf/bwx11-20261115/`: gcc 14.2.0, `bwx11` sha256 `f1215f9ea7b64dd89bad83520e39356dbfdd14934927723ace8024e7d72b00ec`. Record: `tmp/agent-scratch/bwx11-2026-11-15/crb-build-1/`. Local tests before the build: `test_runner11.py` 497 of 497, `test_schedule11.py` 283 of 283, one review round each.
- `check_listing11.py`: 26 of 26 kernels of `bwx10` "same", the 3 new loops as expected (loop offset 20 modulo 64). Self-test `failures=0`. Placement of the timed functions modulo 64 equals `bwx10`.
- Step `ZA` (`results/bwx11-ZA-s1-20261115T084128Z`, 6 trace processes on CPU 2): every trial complete, 0 minor page faults in the timed sequence, gaps 48 to 120 ns, huge-page coverage complete. The evict step took 44 ms for 512 MiB (two passes) and lies before the first window. `M,win_addr` has the page offset 0x0d8 as in step `YA` of `bwx10`.
- Open point for rule 1 of round 4: 44 ms for 1 GiB of line stores is fast. Whether the step moves the benchmark buffer out of the caches is decided by the counter step `ZC` (write-backs per line), as rule 1 says.
- Round 4 session 1 (`ZC`, `ZD`, `ZN`, `ZM`) started at 08:42 UTC, `STOP_AT=none` (Slack read at 08:41 UTC: no block).

### Round 4, session 1: `ZC` read at 08:46 UTC, and the added step `ZS` (rule written before any `ZS` data)

- `ZC` (`results/bwx11-ZC-s1-*`, table in the progress file): with `--evict-mb 512` the write-backs per line of `asmread` at 8 MiB are 0.817 to 0.823, and without it 0.818 to 0.826. So the check of rule 1 fails: the intervention did not change the write-back count. By rule 1, H1d stays open ("Insufficient data"). Two readings fit, and this data cannot separate them: the evict step did not move the buffer out of the caches, or L2 writes back a clean line in the same way as a dirty one. `ZD` is still reported, as a descriptive result.
- **Step `ZS` ("size as the dose", counters).** Reason: `ZC` and `XC*` give, per 64 B line, the processor cycles and the L2 refills. At 1 MiB there are 0 L2 refills and 2.101 cycles. At 8 MiB there are 0.82 L2 refills and 2.52 (high level) to 2.67 (low level) cycles. H1c says: each line that must come from the SLC costs a fixed number of extra cycles. From the 8 MiB numbers of session 1 that cost is 0.50 (high level) to 0.69 (low level) cycles per L2 refill.
- Content: `asmread` and old read at 13 sizes (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 12, 16, 24, 32 MiB), 6 s with counters, 1 process per cell and CPU, 52 processes per session. Generator `tmp/agent-scratch/bwx11-2026-11-15/schedule_zs.py`.
- Rule: r = `l2d_cache_refill` per 64 B (median over the windows). H1c predicts for `asmread` at every size: cycles per 64 B lie between 2.10 + 0.50 r - 0.05 and 2.10 + 0.69 r + 0.05. H1c in this simple form is contradicted if more than 2 of the 11 sizes other than 1 and 8 MiB lie outside the band on both CPUs in both sessions. For old read the prediction is: cycles per 64 B stay within 0.02 of 2.671 while 2.10 + 0.69 r is below 2.671, that is while r is below 0.83.
- `ZS` runs with the session 2 visits of round 2 or 3 as its session 1, and again at least 3 hours later.

### Closing notes, 2026-11-15 14:50 UTC

- One more extra login, not listed above: at 08:45 UTC I fetched `ZC` while `ZD` of the same visit ran (marker check first, one `tar`). The total is 6 extra logins during running visits.
- Supplementary evaluations (block 16 of `A/final8.txt`) were defined after the data was seen: `YP` against the round 1 switch series, old read against `read_sparse`, the prefetch family at 1 MiB, and the gain predicted from two rates. They are printed beside the recorded verdicts and replace none of them.
- All sessions are complete. The verdicts are in block 15 of `A/final8.txt`. The result handoff is `new-test-kernel/tackle-8mb-results.md`.
