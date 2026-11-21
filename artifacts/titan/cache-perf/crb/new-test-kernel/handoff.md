# Handoff: execute the investigation of the two open questions of the new C kernels

## Short version

Your task is to execute the reviewed plan `plan.md` in this folder. The plan says what to test and how to decide. This handoff adds what the plan does not give: access to the machine, a ready script for Part A, numeric rules, and a build specification for the changed benchmark of Parts B and C. Nothing of the plan has been run yet.

Read in this order: this file, then `plan.md`, then the files of "Files" below as you need them.

## Words used here

The plan has its own list "Words used here". It defines CRB, kernel, old read, new read, asm kernels, process, repetition, interval, reference interval, pass, mesh 0 and mesh 1, "a+b threads", low level and high level, split and uniform pattern, A/A control, huge-page coverage, counter, root, and marker file. This handoff uses those terms with the same meaning. Terms that only this handoff uses:

- **Development machine**: the x86-64 Linux server where this folder is. It has no AArch64 compiler. Every build runs on CRB.
- **Plan**: `plan.md` in this folder.
- **`bwx`**: the name of the scratch binary of Parts B and C (the changed copy of the benchmark).
- **Sequence**: the ordered list of kernels that one `bwx` process times, one interval per entry.
- **Block**: the time in which Jeremy has reserved CRB.
- **Specification v1**: the design in this handoff for `bwx`. It was written by the author of the plan and has not been built or tried.
- **est.**: an estimate, not a measurement.

## State on 2026-11-13

- The plan is reviewed: 4 rounds, 9 comments, all accepted, ended with "No further comments." [Ref2].
- No step of the plan has been run.
- A test with two agents that did not know the project showed that the plan alone is not sufficient to execute [Ref13]. This handoff closes the gaps that the test found. The review record of the handoff is `handoff.md.review.md` in this folder.
- `run_partA.sh` in this folder is new. It passed a syntax check (`bash -n`) and local tests of its stop controls with dummy programs. It has never been run on CRB.

## What you may do, and what needs the user

- **Parts A, B and C** need no root. The user said that another agent will execute the plan. I read that as the approval to run them outside Jeremy's blocks. If you doubt it, ask the user once before the first login.
- **Part D** (mesh counters, physical page addresses) needs root. Do not run it. Report what is still open after Parts A to C, and let the user decide.
- **Never run sudo.** Never install a package, change a system setting, or reboot.
- **Do not change `bench/bandwidth.c`**, the report `crb/crb-memory-hierarchy.html`, or any earlier result folder.
- **Review of `bwx`**: the user's practice in this project is a review by a second agent before code is used on the machine (the file-based review loop with a worker and a reviewer). Ask the user who reviews `bwx` before you run Part B.

## The machine, and the rules for using it

| Fact | Value | Source |
|---|---|---|
| Name in this project | CRB (Arm Phoenix Reference Server) | [Ref7] |
| Login | `ssh jhan@192.168.2.45` from the development machine. The host name it prints is `ubuntu`. The login worked with a key and without a password on 2026-11-13 (not recorded in a file). If it asks for a password, stop and tell the user. | [Ref7] |
| Cores | 128, AArch64. CPUs 0 to 63 are on mesh 0, CPUs 64 to 127 on mesh 1. | [Ref8], and the plan's Ref6 |
| CPUs we may use | 0 to 119. Never pin anything to CPUs 126 or 127. | [Ref7] |
| Where we may write | Only under `~/cache-perf` on CRB. This is this project's own choice, not a rule of the host. | [Ref7] |
| Compiler on CRB | gcc 14.2.0 | [Ref4] |
| Compiler flags | `-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11` | [Ref4] |
| Page size | 4096 B. Transparent huge pages are set to "always". | [Ref4] |

Rules before and during every use of CRB [Ref7]:

1. **Read the Slack channel #phoenix-crb before every login.** The channel ID is `C0C1R7XEVU6`. Use the Slack connector of your session (the tool that reads a channel). A block looks like this message of 2026-11-13: "CRB block Fri 13 Nov 15:30 UTC - 18:10 UTC ... Please stay off the host during that window." Blocks are posted by Jeremy Conner or by "Jeremy's Claude". Read the messages of the last 24 hours. The rules of the host say that a block is posted at least 2 hours ahead, and that no announcement means no block [Ref7].
2. **Do not log in during an announced block.** A login alone disturbs his measurement. If a block starts in less than the time your run needs, wait until it has ended.
3. **Check the marker file** `/tmp/positron-perf.RUNNING` as the first command of every login and before every process. A file copy with `scp` is a login that cannot make this check, so the commands below send and fetch files inside an `ssh` call that checks first. If it exists, start nothing and log out. Do not remove it. Both scripts of this handoff do the check.
4. **Measure the system load before every run and report it in every result.** This is a standing rule of the user. The scripts record it.
5. Keep the number of logins small. Run one script per login, not one command per login.

If you cannot read Slack, do not log in. Tell the user.

## Files

All paths are on the development machine unless "on CRB" is said. `C` stands for `/home/jhan/workspace/titan/cache-perf`.

| File | What it is |
|---|---|
| `C/crb/new-test-kernel/plan.md` | The plan. Copy of `/home/jhan/tmp/investigate-new-c-mysteries.md`, sha256 `0b0c4a34...4599a` [Ref1]. |
| `C/crb/new-test-kernel/plan.review.md` | The review record of the plan [Ref2]. |
| `C/crb/new-test-kernel/run_partA.sh` | The script for Part A [Ref3]. Its stop controls are the model for every later run script. |
| `C/crb/new-test-kernel/decide.py` | The decision rules of B.10 as code, with synthetic tests (`python3 decide.py`). |
| `C/bench/bandwidth.c` | The benchmark with the new kernels (sha256 `f1985072...7824`). Base of `bwx`. |
| `C/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c` | The benchmark before the rewrite. Source of the old kernels. |
| `C/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c` | The self-test of the six kernels. Model for the self-test of `bwx`. |
| `C/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh` | The run script of 2026-11-13. Model for a run script (marker check, pinning, header lines). |
| `C/crb/results/kernels-20261113T181222Z/` | The run of 2026-11-13: `probe.txt` (machine code of every kernel), the two csv files, `summarize.py`, `make_html.py` (model for a result page). |
| `/home/jhan/tmp/update_kernel.md` | The handoff of the kernel rewrite. |
| `C/bench/homelat.c` | Lines 770 to 790: a counter group opened with `perf_event_open`. Model for Part C, with the correction below. |
| On CRB: `~/cache-perf/scratch-kernels-20261113/` | Holds `bw_old`, `bw_new` and their sources. They were there at 18:32 UTC on 2026-11-13. |

Check the two binaries on CRB before use:

```
sha256sum ~/cache-perf/scratch-kernels-20261113/bw_old ~/cache-perf/scratch-kernels-20261113/bw_new
# expected [Ref4]:
# e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old
# fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new
```

If they are missing or differ, rebuild them in that folder with `./run_kernels.sh probe`. This builds both, prints the machine code and runs the self-test, and takes about 1 s (measured on 2026-11-13) [Ref4].

## Part A: how to run it

Part A is screening. It closes no hypothesis (plan, section "Two kinds of measurement").

### Commands

```
# on the development machine, after the Slack check
N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel
M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'
S='cd ~/cache-perf/scratch-kernels-20261113'
STOP_AT=none          # or a UTC time such as 2026-11-14T15:00Z, see "Stop controls"

# login 1: marker check, send the script through stdin, run the short steps
ssh jhan@192.168.2.45 "$M; $S && cat > run_partA.sh && chmod +x run_partA.sh && STOP_AT=$STOP_AT ./run_partA.sh A7 A5 A6" \
    < $N/run_partA.sh > $N/partA-short.log 2>&1

# login 2: the long steps; run this call in the background of your session
ssh jhan@192.168.2.45 "$M; $S && STOP_AT=$STOP_AT ./run_partA.sh A1 A2 A3 A4" < /dev/null > $N/partA-long.log 2>&1

# login 3: fetch both result folders (their names are in the two log files, line "result folder: ...")
ssh jhan@192.168.2.45 "$M; tar cf - -C ~/cache-perf/results partA-<UTC time 1> partA-<UTC time 2>" \
    | tar xf - -C /home/jhan/workspace/titan/cache-perf/crb/results/

# only if a new block is announced while login 2 runs: stop our work, then remove the stop file
ssh jhan@192.168.2.45 "touch ~/cache-perf/STOP"
ssh jhan@192.168.2.45 "$M; rm -f ~/cache-perf/STOP"      # after the script has ended, before the next visit
```

### Stop controls

The script can be stopped in four ways. In each case it kills its running benchmark, keeps the csv files written so far, and writes a line `-- killed ...` into the csv file if a benchmark was running.

| Cause | What the script does | Exit status |
|---|---|---|
| The marker file appears | It checks the file before the wait for a quiet system, in every turn of that wait, directly before each launch, and every second while a benchmark runs. | 3 |
| `STOP_AT` | Before each launch it starts no further process if `STOP_AT` is less than 150 s away. In every turn of the wait and every second while a benchmark runs it checks `STOP_AT` itself, and it kills the benchmark when that time is reached. `STOP_AT` is required: a UTC time, or `none`. | 4 |
| The file `~/cache-perf/STOP` exists | It is checked at the same points as the marker file. It is our own file, for a stop from a second login. | 5 |
| The script is interrupted (the login ends, or a signal) | It kills the benchmark before it ends. | 130 |

These cases were tested on the development machine with dummy programs in place of the benchmark and a temporary marker file: marker during the wait, marker during a run, stop file during a run, interruption during the wait and during a run, a stop time that is too near before a launch, a stop time that is reached during a run, and a benchmark that fails. In each case the status was the one in the table, or 1 for the failing benchmark, and no dummy program was left running. The script was not run on CRB.

Rules for a visit:

- **No duration in this handoff is a safe upper value.** Set `STOP_AT` from the known blocks: 30 min before the start of the next announced block. Use `none` only if no block is announced. Blocks are announced at least 2 hours ahead [Ref7].
- **Watch the channel while a script runs on CRB.** Read #phoenix-crb every 10 min. The rules of the host ask for this during a long run [Ref7]. If a new block is announced that starts before your script can end, create the stop file with the command above (a login before the block starts is allowed), wait for the script to end, and log out.
- The marker file may appear only when the block starts. So do not rely on it alone.
- **Status other than 0:** after status 3, wait for the end of the block. After status 4 or 5, run the missing steps in a later visit by naming them. After status 1, read `stderr.txt`. Say in the report which steps were stopped and repeated.
- The script compares the digests of `bw_old` and `bw_new` with the expected ones and stops with status 2 if they differ. Then rebuild as "Files" says. If the rebuilt binaries still differ, stop and tell the user: the compiler or the sources on CRB have changed.
- Messages of the benchmark on standard error go to `stderr.txt` in the result folder.
- `launches.txt` in the result folder holds, for every launch, the load, the number of logged-in users and the 5 busiest processes at that moment.

### What each step runs (fixed here, where the plan left it open)

| Step | Binary and kernels | Options | Processes |
|---|---|---|---|
| A1 | Old read and old write from `bw_old`. New read, new write, asm read, asm write from `bw_new`. | 120 threads on CPUs `0-63,64-119`, `--bytes 256M --per-thread --reps 3 --min-ms 500` | 6 kernels x 2 rounds. Round 2 runs the kernels in the reversed order. |
| A2 | The same six. | The same, with `--min-ms 6000` for read kernels and `--min-ms 15000` for write kernels. | 6 kernels x 2 rounds. |
| A3 | Old read, `bw_old`. One buffer: `--kernel read`. Two buffers: `--kernel all`. | 120 threads, 256 MiB, `--per-thread --reps 3`, with `--min-ms 500` and with `--min-ms 6000`. | 3 processes for each of the 4 cases, the two buffer cases alternating. |
| A4 | Old read (`bw_old`) and asm read (`bw_new`). | `--bytes 256M --per-thread --reps 2 --min-ms 6000`. Thread counts 64+0, 64+16, 64+32, 64+40, 64+48, 64+52, 64+56, 32+32, 40+40, 48+48, 56+56. | 1 process for each kernel and count: 22 processes. |
| A5 | Asm read, `bw_new`. | 1 thread, `--bytes 8M --reps 30 --min-ms 300`, on CPU 2 and on CPU 41. | 2 processes on each CPU, the second directly after the first. |
| A6 | Asm read, `bw_new`. | 1 thread on CPU 2, `--bytes 8M --reps 3 --min-ms 500`, with and without `--no-thp`. | 8 processes of each kind, alternating. |
| A7 | - | Reads the SVE vector length, the list of `perf` events, and the event files of the core counters in `/sys`. | - |

Notes:

- **CPU lists.** "a+b threads" means CPUs 0 to a-1 and CPUs 64 to 64+b-1. This is the rule of the earlier grid run [Ref8].
- **Asm kernels come from `bw_new` in every step.** On 2026-11-13 the same asm read loop differed by 6.2 % (best rates) between the two binaries at 120 threads [Ref5]. So an old kernel and an asm kernel in Part A are always from two binaries. This is one reason why Part A closes nothing.
- **`--kernel all` in A3** also times write and copy at the same interval. Compare only the rows of the read kernel. The step takes longer than the plan's estimate for this reason.
- **Memory.** 120 threads with two buffers of 256 MiB use 60 GiB. Earlier runs did this on CRB [Ref8]. The script skips A3 if less than 70 GiB of memory are available, and says so in `env.txt`.
- **Waiting between processes.** The script waits until at most 2 tasks are runnable (the 4th field of `/proc/loadavg`), for at most 20 s, and writes the wait into the header line of the process (`waited_s`). For A5 the second process must follow at once: report an A5 pair whose second `waited_s` is above 0 as such.
- **Duration (est.):** A7, A5 and A6 together about 3 min. The long call has 58 processes. Their timed intervals sum to 894 s (14.9 min), and the waits between them can add up to 58 x 20 s (19.3 min). Allocation, first touch and warm-up passes come on top and are not bounded here. My estimate is 25 to 45 min. It is not an upper value: use `STOP_AT`.

### Output format

Each csv file holds one block per process. The block starts with a header line `-- step ... tag ... binary ... waited_s ... loadavg ... utc ... args ...`. Then follow the lines of the benchmark [Ref6]:

- one comment line that starts with `# bandwidth:`;
- one line with the column names, `kernel,threads,bytes_per_thread,rep,total_bytes,elapsed_s,aggregate_GBps,per_thread_min_GBps,per_thread_max_GBps,per_thread_avg_GBps`;
- one data line per repetition with these columns. A data line is a line whose 4th field is a number, as `summarize.py` tests it [Ref5];
- `<kernel>,<threads>,<bytes>,best,,,<GB/s>,,,`: one line per kernel. Do not use it as the main value (plan, rule 4).
- `thread,<index>,<cpu>,<kernel>,<rep>,<GB/s>`: one line per thread and repetition, printed after the repetitions of a kernel.

`env.txt` holds the load, the logged-in users, the page settings, the busiest processes and the digests.

### How to analyse Part A

1. **Passes.** Passes per thread (average) = `total_bytes / (threads x bytes_per_thread)`. For copy, divide by 2 more. Mark every repetition with fewer than 50 passes per thread: it fails the 2 % check of rule 7. From the pass counts of 2026-11-13, I expect about 52 to 86 passes per thread in 6 s for the read kernels and about 55 to 67 in 15 s for the write kernels (est.) [Ref5]. This is an average over the threads. In a split repetition the slow threads have fewer passes than the average, and `bw_old` and `bw_new` do not print the passes of each thread.
2. **Per-mesh rates.** From the `thread` lines: sum and median of the rates of the threads on CPUs 0 to 63, and the same for CPUs 64 to 119, for each repetition.
3. **Pattern, numeric rule (provisional).** The label is defined over all threads of one repetition, as in the plan. Let q be the rate of the thread at the 10th percentile divided by the rate of the thread at the 90th percentile. The repetition is "split" if q is below 0.65, "uniform" if q is above 0.85, and "between" otherwise. This also works for a count like 64+0. No per-thread data exists yet at 256 MiB, so the two limits are my choice from the minimum and maximum values of earlier runs (for example 2.67 and 5.13 GB/s in a split run, 2.3 and 2.6 GB/s in a uniform run [Ref5]). Before you use the rule, plot the distribution of q over all repetitions of Part A. If q does not fall into two groups, say so and do not use the labels.
   - Second, separate result: whether a split follows the border between the meshes. Give the per-mesh medians of item 2, and the number of threads of each mesh among the fastest half.
4. **Level at 8 MiB (A5, A6).** Use the provisional limits of rule 5 of the plan: below 69 GB/s is low, above 70.5 GB/s is high. Report the sequence of the 30 intervals of each A5 process as a chart of rate against interval number.
5. **What to state.** For each step, the column "What the result points to" of the plan. Use "observed in screening". Do not write "rejected" or "confirmed" for anything in Part A.

## Parts B and C: specification v1 of `bwx`

The plan describes what `bwx` must do. This section fixes a design, so that you do not have to invent one. You may change a detail if it does not work. Record every change and its reason in your result handoff.

Build `bwx` from a copy of `C/bench/bandwidth.c` in a new folder `C/crb/tmp/agent-scratch/bwx-<date>/`. Do not edit the file in `bench/`. Use the compiler flags of the machine table, plus `-fno-ipa-icf`. Without this flag gcc may merge two functions with equal bodies into one, and an A/A copy would then not exist.

### B.1 Kernels in `bwx`

| Name | What it is |
|---|---|
| `read`, `write`, `copy` | The new C kernels, unchanged. |
| `asmread`, `asmwrite`, `asmcopy` | The asm kernels, unchanged. |
| `oldread`, `oldwrite`, `oldcopy` | The functions `k_read`, `k_write`, `k_copy` of `bandwidth.orig.c`, renamed. `oldread` returns a sum: store it to a `volatile` variable on the stack of the thread, as the old `pass()` did. |
| `asmread2`, `asmwrite2`, `asmcopy2`, `oldread2` | A/A copies: the same source under a second name. |
| `asmcopy_c` | Step B2. An asm kernel whose loop is the machine code of the C copy loop: same instruction order, same offsets, registers q16 to q31. Take the text from the listing "bw_new k_copy" [Ref4]. |
| `asmcopy_c_add` | Step B2. As `asmcopy_c`, but the two `add` instructions stand after the 8 `stp`, and the 8 `stp` use the offsets 0 to 224, as in `asmcopy`. Registers stay q16 to q31. |
| `asmcopy_c_reg` | Step B2. As `asmcopy_c`, but with the registers q0 to q15 (and d8 to d15 named as clobbered, as in `asmcopy`). |
| `read_nopN`, N = 4, 8, 16, 32 | Step B5. The loop of `asmread` with N `nop` instructions placed after the 8 `ldp` and before the `add`. |
| `read_sparse` | Step B5. Per 128 B: 4 `ldp` of q0 to q7, then 9 `nop`, then `add`, `cmp`, `b.lo`. This gives 16 instructions per 128 B, as the old read loop has [Ref4], and no vector add. |

Every kernel that stores gets the checks of `selftest.c` (guard pages, every word compared). Run the self-test on CRB before any timed run, and keep its output.

### B.2 Command line

Keep the options `--threads`, `--cpus`, `--bytes`, `--min-ms` and `--no-thp` of `bandwidth.c`. Remove `--kernel`, `--reps` and `--per-thread`: `bwx` always prints the per-thread lines. The fixed result arrays of `bandwidth.c` (32 repetitions at most) are not kept: each thread holds one result for the current interval, and the main thread prints the lines of an interval between the barrier that ends it and the barrier that starts the next. New options:

- `--seq LIST`: the sequence, a comma-separated list of entries. An entry is a kernel name, optionally followed by `@SIZE` (for example `oldread@1M`). Without `@SIZE` the entry uses `--bytes`. Each entry is one timed interval of at least `--min-ms`.
- `--rounds N`: the whole sequence is run N times in one process. Default 1.
- `--stop pass|common`: the stop method (B.4). Default `pass`.
- `--start common|offset`: where a thread starts in its buffer (B.5). Default `common`.
- `--count`: read core counters around every interval (B.8).

Buffers: each thread allocates buffer `a` of `--bytes`, and buffer `b` if any entry of the sequence is a copy kernel or if `--two-buffers` is given (step B9). An entry with `@SIZE` uses the first SIZE bytes of the buffers. A read or write entry uses buffer `a`. A copy entry reads `a` and writes `b`.

Before each interval the thread makes one warm-up pass with the kernel of the entry, as `bandwidth.c` does [Ref6]. All threads start an interval together after a barrier, as `bandwidth.c` does.

### B.3 Output rows

Keep the header comment line of `bandwidth.c`. Then print, in time order:

- `I,<round>,<pos>,<kernel>,<bytes_per_thread>,<threads>,<total_bytes>,<max_elapsed_s>,<aggregate_GBps>`: one line per interval. `pos` is the position in the sequence, from 0.
- `T,<round>,<pos>,<kernel>,<tid>,<cpu>,<bytes>,<elapsed_s>,<t_sched_s>,<t_start_s>,<t_end_s>,<passes>,<flags>`: one line per thread and interval. Times are seconds since the start of the process on the monotonic clock, with 6 decimals. `t_sched_s` is the common start that was scheduled (`common` mode; in `pass` mode it equals `t_start_s`). `t_start_s` and `t_end_s` are clock readings of the thread itself, taken directly before its first kernel call and directly after its last. `elapsed_s` is `t_end_s` minus `t_start_s`. `passes` is bytes divided by the bytes of the entry, with 3 decimals. `flags` is `-`, or `late` (B.4).
- `P,<round>,<pos>,<tid>,<buffer>,<kB_total>,<kB_huge>,<thp_fault_alloc>,<thp_fault_fallback>,<thp_collapse_alloc>,<pgmigrate_success>`: the page state (B.6).
- `C,<round>,<pos>,<kernel>,<tid>,<cpu>,<enabled_ns>,<running_ns>,<cputime_ns>,<count 1>,...`: the counters (B.8), only with `--count`.

Print the `T`, `P` and `C` lines after the interval is over, never inside a timed interval.

### B.4 The two stop methods

- `pass` is the method of `bandwidth.c`, unchanged: a thread runs whole passes and reads the clock after at least 8 MiB of work, until `--min-ms` has elapsed [Ref6].
- `common`: the common times cannot be set before the barrier, because the main thread passes the barrier only when the last worker has finished its warm-up pass. Protocol, with C11 atomic variables (`<stdatomic.h>`), valid for every interval of a process:
  - Shared: `_Atomic uint64_t gen` (starts at 0), `_Atomic int64_t t_sched_ns`, `_Atomic int64_t deadline_ns`.
  - Each worker keeps a local counter `k` of the intervals it has run (starts at 0). After it has passed the start barrier of an interval, it loops until `atomic_load(&gen)` equals `k + 1`. Because `gen` only grows, a worker can never take the state of the earlier interval for the new one.
  - The main thread, directly after it has passed the same barrier: reads the clock, stores `t_sched_ns = now + 2 ms` and `deadline_ns = t_sched_ns + min-ms`, and then does `atomic_fetch_add(&gen, 1)`. The two times are stored before `gen` changes, so a worker that sees the new `gen` reads the new times.
  - The worker then loads the two times and loops on the clock until `t_sched_ns`. Directly after this loop it reads the counters (B.8) and then the clock. That clock reading is its actual start `t_start_s`. Then it sets `k = k + 1` and runs.
  - A thread whose actual start is more than 100 µs after `t_sched_ns` gets the flag `late`.
  - After the interval, the analysis computes the end skew: the latest `t_end_s` minus the earliest. An interval is "irregular" if any thread is `late` or if the end skew is above 5 ms. Irregular intervals are listed in the report and are not used for a decision. The two limits (100 µs, 5 ms) are provisional.
  - Whether the threads really start together is a result of these readings. It is not assumed.
  - Each thread calls the kernel on chunks of 2 MiB (for an entry smaller than 2 MiB: on the whole entry). After each chunk it reads the clock and stops if the deadline has passed. It counts the bytes of the chunks it finished. The position in the buffer continues from chunk to chunk and wraps at the end of the entry.

Two things to know about `common`: the kernel function is entered once per 2 MiB and not once per pass, and one clock read per 2 MiB is added. At 2.4 GB/s for each thread a chunk takes about 0.9 ms (est.). So `common` differs from `pass` in more than the stop. Step B7 measures the difference between the two methods, and this is why it keeps `pass` as its reproduction condition.

Use `pass` for the one-thread steps (B1 to B4 and B6). Use the method that the step names for B7 and B10. For B5, B8, B9 and C3, see "Settings after B7" in B.9.

In `common` mode an entry size must be a multiple of 2 MiB or smaller than 2 MiB. `passes` of a copy entry is bytes divided by twice the entry size, because copy counts the bytes read plus the bytes written.

### B.5 Start offsets

With `--start offset`, thread number i (0 to 119) starts its first pass at byte offset `(i x 37 mod 128) x 2 MiB` of a 256 MiB entry, and wraps. In `pass` mode a pass is then the range from the offset to the end, followed by the range from the start to the offset. A range of length 0 (thread 0) is not called. For another entry size, use `(i x 37 mod n) x 2 MiB`, where n is the entry size divided by 2 MiB.

### B.6 Page state (corrects a defect of the plan)

The plan says to read the huge-page coverage "of each buffer" from `/proc/self/smaps` (rule 8). It does not say how one buffer is found in that file. A buffer is certain to be one entry of its own only if its neighbours differ from it in a setting. The `madvise` call of `alloc_buf()` gives such a difference when it succeeds, but the program continues when it fails [Ref6].

So: `alloc_buf()` maps the buffer length plus 4 MiB, and takes as buffer start `p` the first 2 MiB boundary that lies at least one page above the start of the mapping. Then the unused part before `p` and the unused part after `p + len` both have a length above zero. Change both to `PROT_NONE` with `mprotect`. The lookup in `/proc/self/smaps` must find one entry whose start is `p` and whose end is `p + len`. Its `Size` is `kB_total` and its `AnonHugePages` is `kB_huge`. If no entry has exactly this start and this end, print `NA` for both values and do not use the interval for a statement on page state. Do not assume that the lookup succeeds: test it in the short run of step 2 of "Order of work".

The four system counters come from `/proc/vmstat` (`thp_fault_alloc`, `thp_fault_fallback`, `thp_collapse_alloc`, `pgmigrate_success`). They count for the whole system, not for our buffer.

When to read the page state. Rule 8 of the plan asks for it before every interval, and this specification keeps that for every process:

- In a process with one thread, the worker reads it after the warm-up pass of each entry and before it enters the start barrier.
- In a process with more than one thread, the main thread reads it for all buffers at two kinds of points: once before the first interval (the workers pass one extra barrier after they have allocated and first touched their buffers, the main thread reads, and then the normal sequence starts), and after the end barrier of every interval. These `P` lines carry the `round` and `pos` of the interval that has just ended, or `pos` -1 for the first reading.
- So for an interval of a multi-thread process, the state before it is the reading after the interval before it. The warm-up pass of the interval lies between that reading and the timed part. A change of page state during the warm-up pass is therefore seen only in the next reading. Say this limit wherever a page state is assigned to an interval of a multi-thread process.
- The reading of the main thread takes time between two intervals, not inside one. If it takes more than 50 ms with 240 buffers (measure it in the short run), report that, and keep the per-interval readings.

### B.7 Loop addresses

The offset of a loop start modulo 64 is a factor of step B3 and a condition of step B1 (plan, rule 2).

- In `bw_new` both copy functions start at an address that is 32 modulo 64: `k_copy` at 0x1ca0 with its loop at 0x1ca4 (36 modulo 64), and `k_asmcopy` at 0x1be0 with its loop at 0x1bf4 (52 modulo 64) [Ref4].
- Method to place a function (not tried): compile with the added flags `-fno-toplevel-reorder -falign-functions=4`, and put a file-level statement `__asm__(".text\n.p2align 6\n.skip N, 0\n");` directly before the function. N = 32 puts the start of the function at 32 modulo 64.
- Acceptance test, required: after every build, print the start address of every loop with `objdump -d --no-show-raw-insn --disassemble=<function>` and save the listing. Compare the loop bodies of the new C kernels and the asm kernels with the listings "bw_new" in `probe.txt`, and the loop bodies of `oldread`, `oldwrite` and `oldcopy` with the listings "bw_old" [Ref4]. Check that every A/A copy has its own start address, different from that of its original. A build whose loops differ, or whose loop offsets are not the planned ones, is not used.
- The value N depends on the function: the loop of a function without the save of d8 to d15 starts 4 B after the function start (`copy`, `asmcopy_c`), and the loop of `asmcopy` starts 20 B after it [Ref4]. Compute N for each function from its listing.
- Planned offsets: `copy` loop at 36 and `asmcopy` loop at 52 modulo 64 (as in `bw_new`). `asmcopy2` at 52. `asmcopy_c`, `asmcopy_c_add`, `asmcopy_c_reg` at 52. Step B3 needs three more builds or six more functions, with the loops of `copy` and of `asmcopy` at 0, 36 and 52 modulo 64. For all other kernels, record the offset that the build gives. An A/A copy must have the same offset modulo 64 as its original.

### B.8 Counters (corrects a defect of the plan)

The plan names the counter code of `bench/homelat.c` as the model. That code does not ask for user-mode counting, so a copy of it fails without root on CRB (`kernel.perf_event_paranoid` is 2). Correction: set these fields in `struct perf_event_attr` for every event:

- `exclude_kernel = 1` and `exclude_hv = 1`;
- `read_format = PERF_FORMAT_GROUP | PERF_FORMAT_TOTAL_TIME_ENABLED | PERF_FORMAT_TOTAL_TIME_RUNNING`;
- open with `pid = 0`, `cpu = -1`, in the thread that is counted, after the thread is pinned.

Events: cycles, instructions, L1 data refills, L2 data refills, last-level read misses. Take the PMU type and the event codes from the files that step A7 saves (`A7-core-events.txt`: the `type` file and the `events/` files of the core PMU). Insufficient data here: I did not read these codes on CRB, so I do not give them. If an event cannot be opened, print `NA` in its column and go on.

The thread reads the group at two points: directly after its wait for the common start has ended and before the clock reading `t_start_s` (in `pass` mode: directly after the start barrier), and directly after the clock reading `t_end_s`. So the waits on the barrier, for `gen` and for `t_sched_ns` are outside the counts. It reads its CPU time (`CLOCK_THREAD_CPUTIME_ID`) at the same two points. A `C` line whose `running_ns` is below its `enabled_ns` is not used. The clock of a busy core is the cycle count divided by `cputime_ns`. Rates of a counter run use `elapsed_s` of the `T` line, which comes from the actual start and end.

Before any counter run, make one short test on CRB: `bwx --count` with one thread at 32 KiB. Check that instructions per byte match the loop: 11 instructions per 256 B for `asmread` [Ref4]. The call, the save of d8 to d15 and the loop of the worker add a little (est. 1 to 2 % at 32 KiB), so accept a value within 3 %.

### B.9 Sequences and sizes of each step

One observation is defined per step. "Session" means one visit to CRB; the plan asks for 2 sessions some hours apart for every deciding step (rule 10). R stands for a reference interval of `asmread` at the size of the step.

| Step | Sequence (one round) | Options | Processes per session |
|---|---|---|---|
| B1 | `asmread,copy,asmcopy,asmread,asmcopy,copy,asmread,asmcopy,asmcopy2,asmread,asmcopy2,asmcopy,asmread` | 1 thread, `--rounds 4 --min-ms 300 --stop pass`. Sizes 4M, 8M, 16M, 32M, one size per process. | 4 on each of the CPUs 0, 2, 41, 94 for each size: 64 processes. |
| B2 | The B1 sequence with `copy` replaced by `asmcopy_c`, then by `asmcopy_c_add`, then by `asmcopy_c_reg`. | As B1, size 8M only. | 16 for each variant. |
| B3 | The B1 sequence, in the builds with the loops at 0, 36 and 52 modulo 64. | As B1, size 8M only. | 16 for each build. |
| B4 | `asmread` alone. | 1 thread, `--bytes 8M --rounds 200 --min-ms 300 --stop pass`. Half of the processes with `--no-thp`. | 4 on CPU 2 and 4 on CPU 41. |
| B6 | `asmread,oldread,oldread@1M,asmread,oldread@1M,oldread,asmread,oldread,oldread2,asmread,oldread2,oldread,asmread` | 1 thread, `--bytes 8M --rounds 4 --min-ms 300 --stop pass`. | 8 on each of the CPUs 2, 41, 94. |
| B7 | `oldread,read,asmread,asmread2,asmread2,asmread,read,oldread` | 64+56 threads, 256M, `--rounds 2`. All 8 combinations of `--stop pass|common`, `--min-ms 500|6000`, `--start common|offset`. Also the reproduction condition (`pass`, 500, `common`) with one kernel per process, as `--seq oldread`, `--seq read`, `--seq asmread`, `--seq asmread2`, each `--rounds 3`. | 4 for each combination, and 4 for each single-kernel sequence. |
| B8 | `oldread,asmread,asmread2,asmread2,asmread,oldread` | `--stop common --min-ms 6000 --rounds 1`. Thread counts 64+b in steps of 4 around the two counts between which A4 saw the pattern change, for each kernel. | 2 for each count. |
| B5 | `oldread,read,read_sparse,read_nop4,read_nop8,read_nop16,read_nop32,asmread,asmread2`, and the same in the reversed order in the next process. | 64+56 threads, 256M, `--stop common --min-ms 6000 --rounds 1`, and the `--start` setting under which B7 resolved the difference. | 4. |
| B9 | `oldread` alone, with and without `--two-buffers`. | 64+56 threads, 256M, `--stop common --min-ms 6000 --rounds 3`. | 3 of each kind, alternating. The A/A value is the difference between two processes of one kind. |
| B10 | `oldwrite,write,asmwrite,asmwrite2,asmwrite2,asmwrite,write,oldwrite` | 64+56 threads, 256M, `--rounds 2`. All 8 combinations of `--stop pass|common`, `--min-ms 500|15000`, `--start common|offset`. | 4 for each combination. This gives 16 intervals for each kernel and combination. |
| C1 | As B4, with `--count`, without `--no-thp`. | | 2 on each of the CPUs 2 and 41. |
| C2 | As B1 at 8M, with `--count`. | | 2 on each of the CPUs 0, 2, 41, 94. |
| C3 | As B7 in the settings where the difference is resolved, and as B5, with `--count`. | | 2 for each. |

**Order of the processes.** Where a step has several settings or kinds, interleave them: one process of each setting, then the second process of each, and so on. Do not run all processes of one setting first.

**Settings after B7.** B8, B5, B9 and C3 depend on the result of B7. So the visit for B7 comes first, then the analysis of B7 on the development machine, then a new Slack check and the visit for B8, B5, B9 and C3. The settings for these steps: among the B7 settings in which D is resolved, take the one with `--stop common` and the largest |median D|. If D is resolved only in settings with `--stop pass`, take the one with the largest |median D| and say so. If D is resolved in no setting, do not run B8, B5 and C3 for Q2a (plan, step B7). The entries for B5, B8 and B9 in the table give `--stop common --min-ms 6000` as the expected case.

Machine time (est., timed intervals plus an allowance for allocation and warm-up): B1 about 17 min, B4 about 8 min, B6 about 6 min, B7 about 35 min, B10 about 75 min, B5, B8 and B9 together about 15 min, Part C about 20 min. The plan says 90 min for Part B. My sum is about 3 hours for one session, mostly because of the 15 s intervals of B10.

**Visits.** A session of this length is longer than the 2 hours of notice that a block gets. So do not run it as one call. Divide a session into visits of at most about 45 min of planned work each (for example: B1 with B4 and B6; B7; B10 in two halves; B8 with B5 and B9; Part C). The run script of each visit must have the stop controls of `run_partA.sh` (marker, `STOP_AT`, stop file, interruption, kill of the running benchmark): copy its functions `why_stop`, `check_marker`, `check_deadline`, `stop_child`, `settle` and `one`, and set `MARGIN` to the longest process of the visit plus a reserve. Watch the channel every 10 min during every visit. The visits of one session may be spread over a day; "two sessions some hours apart" (plan, rule 10) then means that every deciding step is run twice with some hours between its two runs.

### B.10 Numeric decision procedure

These definitions make rule 3 and rule 11 of the plan computable. They are my choices where the plan gives no number.

**One-thread steps (B1, B2, B3, B6):**

- A pair is two neighbouring intervals of the two compared kernels that stand between the same two reference intervals. In the B1 sequence, `copy,asmcopy` and `asmcopy,copy` are pairs of the kernel comparison, and `asmcopy,asmcopy2` and `asmcopy2,asmcopy` are pairs of the A/A comparison.
- The pair value is the rate of the first-named kernel minus the rate of the second (for B1: `copy` minus `asmcopy`, and `asmcopy2` minus `asmcopy`), in GB/s.
- At 8 MiB an interval has the label of rule 5 of the plan (low, high or changing), from the rate of a reference interval.
- **One value per process** (plan, rule 4). At 8 MiB a process is "stable low" or "stable high" if all its reference intervals have that label, and only stable processes give process values. At 4, 16 and 32 MiB no level is defined: every process gives process values, with the label "none", and the reference rates are reported. The process value d is the median of the kernel pair values of the process. The process value e is the median of its A/A pair values. The pairs of processes that are not stable are listed in the report with their labels and are not used for a decision.
- **One CPU at a time** (plan, rule 3). A decision group is one session, one size, one CPU and one label. The A/A spread of a group is the largest |e| of its processes. The group is "resolved" if |median of d| is larger than the A/A spread and all d have one sign. A group with fewer than 3 processes is "not observed". Processes of different CPUs are never put into one group.
- A label of a size is "resolved" in a session if at least 2 CPUs have a group with enough processes, every such group is resolved, and all have the same sign. With fewer than 2 such CPUs it is "not observed": report "Insufficient data" and the number of stable processes per CPU. Do not pool CPUs to reach a number.
- With 4 processes per CPU (B1), a label can be decided on a CPU only if at least 3 of its 4 processes are stable at that label. If the high level is rare, the decision for "high" will be "not observed". That is a valid result.
- "Rejected" needs the same resolved result in both sessions (rule 11).
- B6 has two comparisons, both per CPU. The A/A spread of a CPU is the largest |median of `oldread2` minus `oldread`| over its processes. First: the median over the stable low processes of that CPU of their rate of `oldread` at 8 MiB, minus the same over the stable high processes of that CPU. It is resolved if its absolute value is larger than the A/A spread and if every low value lies on one side of every high value. A CPU with fewer than 2 stable processes of either label is "not observed". Low processes of one CPU are never compared with high processes of another CPU. Second: the pair value `oldread` minus `oldread@1M`, decided as in B1, with the label "none" (it uses all processes of a CPU).
- B3: for each of the three builds (both loops at 0, at 36, at 52 modulo 64), d and the A/A spread per CPU as in B1. The change, per CPU, is the median d of B1 (original offsets) minus the median d of the build. It is resolved on a CPU if its absolute value is larger than the sum of the two A/A spreads and if every d of one lies on one side of every d of the other. H6 is rejected if the change is resolved on no CPU, for all three builds, in both sessions.
- B4: each interval is its own reference, so its label comes from its own rate (below 69 GB/s low, above 70.5 GB/s high). Coverage is "full" if `kB_huge` equals `kB_total`, and "none" if `kB_huge` is 0. H3a predicts that low intervals have less than full coverage and high intervals have full coverage. Two cases contradict it, each per CPU and per session: (a) at least 10 low intervals and at least 10 high intervals, all with full coverage; (b) at least 10 low intervals and at least 10 high intervals, all with coverage none (the processes with `--no-thp`). H3a is rejected if case (a) or case (b) occurs on one CPU in both sessions. Report which case occurred. If neither occurs, the result is "not observed", with the counts of intervals per label and coverage.
- The file `decide.py` in this folder holds these rules as code (`process_value`, `resolved`, `decide_one_thread`, `decide_b6_state`). Its synthetic tests pass. They show that a difference between two CPUs does not become a difference between levels, and that one process with many intervals counts once. Use it, or code that passes the same tests.

**Steps with 120 threads (B7, B10, B5):**

- **Metrics of one interval.** Three values are named here. Two are computed from the `T` lines:
  - `M_hist` = (sum of the bytes of all threads) / (longest elapsed time of a thread). This is the value that `bandwidth.c` prints and that the run of 2026-11-13 used [Ref6].
  - `M_sum` = sum over the threads of (bytes of the thread / elapsed time of the thread).
  - The third, the bytes moved during the time in which all threads ran, is not measured: a thread records only its total. So no value of this handoff is the traffic of the common time, and rule 6 of the plan is met only in part. Say this limit in the report. Do not derive a common-time rate from the totals.
- **The decision metric is `M_hist`**, for the reproduction condition and for every setting of B7 and B10, so that all settings are counted in one way. `M_sum` is reported next to it as a description. If `M_hist` and `M_sum` of a setting lead to different words for D, report both and call the result "not resolved".
- The value of one mesh uses the same formula over the threads of that mesh, with the longest elapsed time of all threads as divisor for `M_hist`.
- **One value per process.** B7: for one process, D is the mean over its rounds of (mean of the two `oldread` intervals minus mean of the two `read` intervals), and E is the same for `asmread2` minus `asmread`. One setting in one session has 4 values of D and 4 of E, one per process.
- For one setting: the A/A spread is the largest |E|. D is "resolved" if |median D| is larger than the A/A spread and all 4 values of D have one sign. With fewer than 4 processes it is "not observed".
- B7 with one kernel per process: the process value is the median of the 3 intervals of the process. D is the median of the 4 process values of `oldread` minus the median of the 4 of `read`. The A/A value is |median of the 4 of `asmread2` minus median of the 4 of `asmread`|. D is resolved if |D| is larger than the A/A value and if every process value of one kernel lies on one side of every process value of the other.
- B8: label every interval with the pattern rule of Part A. For one kernel, a count is "split" or "uniform" if all its intervals have that label, and "mixed" otherwise. A bracket exists only if the counts are ordered: there is a count x and a higher count y so that every tested count up to x is split, every tested count from y on is uniform, and the counts between them are mixed or untested. The bracket is then x to y. If no count is split, if no count is uniform, or if a split count lies above a uniform count, the kernel has no single change of pattern: report the labels of all counts and the result "not resolved". Do not build a bracket from the highest split count alone.
- A change between two settings that differ in one factor: the change is median D of the first minus median D of the second. It is "resolved" if its absolute value is larger than the sum of the two A/A spreads, and if every D of one setting lies on one side of every D of the other.
- B10 has three separate controls for one setting, all from the A/A pair `asmwrite` and `asmwrite2`:
  - the control of the spread: the largest, over the 4 processes, of |spread of `asmwrite2` minus spread of `asmwrite`|;
  - the control of the total rate: the largest absolute difference of the total between two neighbouring intervals of `asmwrite2` and `asmwrite`;
  - the control of the rate of each mesh: the same, computed for the rate of mesh 0 alone and for the rate of mesh 1 alone.
- B10, spread: for one kernel in one process, the spread is the highest minus the lowest value of its 4 intervals. The process value of a kernel is this spread. A change of the spread of a kernel between two settings is the difference of the two medians of its process values. It is "resolved" if its absolute value is larger than the sum of the two controls of the spread and if the process values of the two settings do not overlap.
- H11 in B10, per process: for one kernel, take the interval with the highest total and the interval with the lowest total of the process. The process counts only if the two totals differ by more than the control of the total rate. For each mesh, the change is its rate in the high interval minus its rate in the low interval. A mesh "has changed" only if the absolute change is larger than the control of the rate of that mesh. A control of a total or of a spread is never used for a mesh. H11 is "supported" for a kernel and setting if in every counted process exactly one mesh has changed, that change is positive (the mesh is faster in the high interval), and it is the same mesh in all of them. A process in which the only changed mesh got slower does not support H11, and the result is then "not resolved". It is "contradicted" if in every counted process both meshes have changed in the same direction. With fewer than 2 counted processes it is "not observed". In all other cases it is "not resolved". `decide.py` holds this rule (`controls_from_aa`, `decide_h11`). One of its tests has A/A intervals with equal totals and opposite mesh rates: the control of the total is then 0 GB/s and the controls of the meshes are 5 GB/s, and a change of 0.1 GB/s on one mesh does not support H11.
- `decide.py` holds the rules for one setting and for a change between two settings (`decide_setting`, `decide_change`).
- B5: a `nop` variant "shows the pattern and total of old read" if its pattern label (Part A, rule 3) equals that of `oldread` in the same process, and if `oldread` minus the variant is not resolved against the A/A spread of `asmread2` minus `asmread`.

**Words in the result handoff.** Rule 11 of the plan has five words. Where a step of the plan says "supported" or "contradicted" (B8, H11), write "not rejected" for supported and "rejected" for contradicted, and add the plan's word in brackets.

If a definition does not fit the data (for example no process has 4 pairs of one label), do not adapt it silently. Report the case as "not resolved" or "not observed", and state what was missing.

## Order of work

1. Slack check. Then Part A (script ready). Analyse it and write its result page before Part B is designed further, because A7 gives the counter codes and A4 gives the thread counts of B8.
2. Build `bwx` and its self-test on CRB. Run the self-test, the objdump acceptance test (B.7), and one short run of every sequence with `--min-ms 100`.
3. Get `bwx` reviewed (see "What you may do").
4. Session 1 of Part B, then Part C, divided into visits (B.9, "Visits"). Session 2 some hours later. The order inside Part B is in the plan, section "Order and decision points".
5. Report. Stop before Part D.

## What to deliver

- A result folder for each visit under `C/crb/results/`, with the raw files, the analysis script, and one HTML result page. Model: `C/crb/results/kernels-20261113T181222Z/` [Ref5].
- The result page follows the user's standing rules: light background; a "Short version" of at most three sentences; a list of the terms used; a chart whose form fits the data, with values on the points; the exact numbers in a table; estimates marked "est."; the system load of the run; references at the end.
- A result handoff `C/crb/new-test-kernel/results.md` that gives, for every hypothesis H1 to H11 of the plan, one of the five words of rule 11, with the step, the number of processes and the A/A spread behind it. It also lists every change you made to specification v1 and every step you did not run.
- Every claim rests on a named file of your results. Where data is missing, write "Insufficient data" and name the measurement that would give it.

## Known limits of this handoff

- Specification v1 is untested. `run_partA.sh` passed a syntax check and the tests of its stop controls with dummy programs ("Stop controls"). It was never run on CRB or with the real binaries.
- The method to place a loop at an address (B.7) and the counting inside a thread without root (B.8) have not been tried on CRB.
- The limits 0.65 and 0.85 for the pattern, and 69 and 70.5 GB/s for the level, are provisional.
- The time estimates are estimates. Only the 1 s of `run_kernels.sh probe` and the 6 min 15 s of the run of 2026-11-13 are measured [Ref4].
- The counter codes of Part C are not in this handoff. Step A7 fetches them.
- This handoff was checked once by a second cold-read test [Ref13]. That test found 2 errors that would have blocked or misled the work and about 20 smaller gaps and errors, in the script and in specification v1. I corrected them in this version. The corrected version was not tested again by a cold read. Its review record is `handoff.md.review.md` in this folder.

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.md`, sha256 `0b0c4a3455792e88389f4f7c783223f9871d52ff89fe0b147200bd18a724599a`. Identical to `/home/jhan/tmp/investigate-new-c-mysteries.md` on 2026-11-13.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/plan.review.md`. Session `20261113T1915Z-p7x3`, 4 rounds.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/run_partA.sh`.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt` and `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: compiler, flags, digests of the binaries, machine code and addresses of every kernel, page setting, start and end times. The page size is in `selftest.txt` of the same folders.
- [Ref5] `/home/jhan/tmp/update_kernel.md` and `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/` (`one-thread.csv`, `threads120.csv`, `summarize.py`, `make_html.py`, `kernels-result.html`).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c`: `worker()` (warm-up pass, barrier, whole passes, clock read after at least 8 MiB), `main()` (options and output lines), `alloc_buf()`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md` (host rules, CPUs 126 and 127, blocks, marker file) and `/home/jhan/tmp/k_cread.md` (login, machine). The Slack channel ID was read with the Slack connector on 2026-11-13; no file records it.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/bench/run_followup3.sh` (function `cpulist`, the grid of threads per mesh) and `/home/jhan/workspace/titan/cache-perf/bench/run_followup.sh` (120 threads with the three asm kernels at 256 MiB).
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/`: `bandwidth.orig.c`, `selftest.c`, `run_kernels.sh`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/bench/homelat.c`, lines 770 to 790.
- [Ref13] The two cold-read tests of 2026-11-13: agents without knowledge of the project tried to execute the plan (first test) and this handoff (second test) and listed every fact they could not find. Their output is not saved as a file in the project. First test: 13 facts not found for Part A and 21 for Parts B and C.
