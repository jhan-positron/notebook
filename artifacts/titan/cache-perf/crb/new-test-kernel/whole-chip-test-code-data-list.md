# Whole-chip read test at 7200 MT/s: list of test code and test data

## Short version

- This list names the source files, the functions of the call sequences and the data files of the whole-chip read test that ran on CRB (an Arm reference server with 128 CPUs) on 2026-11-17, in calling order.
- Each linked file has a companion file that explains it: the same name plus `.md`, in the same folder.
- The old read kernel (the old inner loop of the benchmark that reads memory) is the function `k_read` in `bandwidth.orig.c` and `k_oldread` in `bwx12.c`, and the new read kernel is `k_read` in `bandwidth.c` and `k_read` in `bwx12.c`.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Rerun**: the whole-chip read test of 2026-11-17, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM. CRB has 12 slots.
- **Read kernel**: the inner loop of the benchmark that reads memory. In this list "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Load-only loop**: the new read kernel or asmread.
- **bw_old, bw_new**: the two binaries of 2026-11-13. bw_old was built from the old source `bandwidth.orig.c`, bw_new from the new source `bandwidth.c`.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **Control I**: the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.
- **Line, argument line**: the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.
- **Spec file**: a file with one line "tag|arguments" per process. `rx.sh` reads each line, names the csv file after the tag, and passes the arguments to the binary (bwx12 in this test). Each of the three spec files of this test holds one line.
- **Idle start**: a launch at a 1-minute load average below 1.0.
- **Visit**: one time at which the same line was run. A later visit is the same line run again at a later time.
- **State line**: a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.
- **I, T, P, C rows**: the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Common stop**: the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).
- **Total rate, throughput**: the read rate of all 120 threads together in one interval, in GB/s. The request of the user calls it aggregation throughput. Part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time.
- **Drop**: how far the rate of the new read kernel (or of asmread) lies below the rate of the old read kernel, in percent: (1 - new / old) x 100.
- **First touch**: the first write to a buffer by its own thread, before any timing.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **rc, rc line**: rc is the exit status of a process. 0 means success. The rc line is the line `rc <status> <tag> utc <time>` that `rx.sh` appends to launches.txt when a process ends.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Baseline**: an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.
- **Pool**: the intervals of several rows taken together as one range.
- **X2d12**: one earlier process with the part L line, run on 2026-11-17 at 8000 MT/s with 12 modules, in another boot and with a firmware test setting. The rules file lists it as not a baseline.
- **Facts sheet**: the file `FACTS.md`. The script `build_facts.py` writes it. It holds all tables and verdicts of the rerun.
- **Rules V1 to V4, F1, F2**: the comparison rules in `baselines-and-rules.txt`.
- **Q1**: at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much.
- **Q2**: did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s.
- **Journal**: the log store of Linux. It keeps the Linux kernel log of earlier boots.
- **Hardware error record**: a message that the firmware passes to Linux when hardware reports an error.
- **Companion**: the explanation file of a listed file. It has the same name plus `.md` and lies in the same folder.
- **Call sequence**: the functions that run, in the order in which they are called. A deeper list level is a call made by the entry above it. Where the two entries are in different files, the call can pass through functions that the section of the called file lists. Example: `ra.sh:one` starts a process, and `main`, `worker` and `pass` of that process run before `k_read`. The kernels below one `pass` or `call` entry are alternatives: each process or interval runs one of them. An entry marked "NOT called" names a function that does not run in this test.
- **Agent server**: the Linux server on which Claude Code ran. Claude Code is the AI coding agent that sent the commands of section 3.1 to CRB with ssh.
- **Session record**: a file that records one working session of Claude Code. This list uses three of them [Ref3] [Ref6] [Ref7]. In this term "session" does not mean a session of go.sh.
- **GB**: 1e9 bytes.

</details>

## 1. How to read this list

- Every path of a listed file is relative to the folder `crb`, which is `/home/jhan/workspace/titan/cache-perf/crb`. A path that starts with `~/cache-perf/` is a path on CRB. Three files lie outside `crb`: the session records [Ref3], [Ref6] and [Ref7].
- A path is a link to the file. The word "explained" after it is a link to the companion file.
- The companion of a code file shows the source at the left and the explanation at the right.
- The companion of a data file explains its rows and columns.
- The number after a function name is the line of its definition in the source file. For an entry that is a script, a command of a script (for example `sha256sum -c`) or a block of statements (for example `main: rate loop`), it is the line where that script, command or block starts.
- A note that starts with "line N:" or "Lines N to M:" gives the lines of the calls in the same source file.
- The call sequences and the line numbers are those of the sections "Call sequence in the whole-chip test" and "Functions" of each companion. The script `tmp/agent-scratch/code-data-list-2026-11-21/make_list.py` copied them into this list from the same checked data. For `ra.sh` and `rx.sh` this list shows the first two levels only. The deeper levels are in the two companions and in the sections of the C files.
- No separate assembly file exists. The hand-written loops are inline assembly (`__asm__` statements) inside the C files: `k_asmread`, `k_asmwrite` and `k_asmcopy` in `bandwidth.orig.c` and in `bandwidth.c`, and in `bwx12.c` the macro `DEF_ASMREAD` (kernels `asmread`, `read_nop96`, `read_nop256`) and the function `k_read_1pl`.
- The old and the new read kernel are C text. `k_read` of `bandwidth.c` (line 205) and of `bwx12.c` (line 522) holds one `__asm__` statement with an empty instruction text. It adds no instruction to the loop.
- The test ran on CRB under `~/cache-perf/`. The table gives the folder on CRB for each local folder.

| Local folder (below `crb/`) | Folder on CRB (below `~/cache-perf/`) | What it holds |
|---|---|---|
| `tmp/agent-scratch/w120-7200-2026-11-17` | `w120-7200-20261117` | run scripts and spec files of the rerun (copied to CRB, section 3.1), and the analysis scripts (they ran on the agent server) |
| `tmp/agent-scratch/kernels-2026-11-13` | `scratch-kernels-20261113` | old and new benchmark source. On CRB also the binaries `bw_old` and `bw_new` |
| `tmp/agent-scratch/bwx12-2026-11-15` | `bwx12-20261115` | source and build script of the runner `bwx12`. On CRB also the binary `bwx12` and the build records |
| `tmp/agent-scratch/bwx12-2026-11-15/crb-build-1` | `bwx12-20261115` (no sub-folder on CRB) | copies of the build records that `build12.sh` wrote on CRB |
| `tmp/agent-scratch/w120-2026-11-15` | `w120-20261115` | the runner script `rx.sh` |
| `results` | `results` | result folders, copied back after the run |

- The folders on CRB are named in `go.sh`, `ra.sh` and the copy commands of section 3.1 [Ref3].
- The three binaries are not in the local folders. Their sha256 values are in the records of section 4.8.

## 2. Calling sequence in one diagram

```text
agent server (commands of section 3.1)
  |  copy scripts, then: ssh CRB nohup setsid go.sh > log
  v
CRB, CPUs 0-119, no root
  go.sh                           driver: 3 sessions, then 1 more C
   |- ra.sh T72A<s>               part A: 24 processes
   |    |- bw_old                 old: bandwidth.orig.c, k_read
   |    `- bw_new                 new: bandwidth.c, k_read
   |- rx.sh T72L<s> < like.spec   part L: 1 process
   |    `- bwx12                  old: k_oldread, also k_asmread
   `- rx.sh T72C<s> < cfwd.spec   part C: 1 process (or crev.spec)
        `- bwx12                  old: k_oldread, new: k_read
  go2.sh                          control I: 2 processes
   `- rx.sh T72I<i> < like.spec
        `- bwx12                  old: k_oldread, also k_asmread
  |
  v  copy results back
agent server
  build_facts.py  -> FACTS.md, facts.json
  make_report.py  -> whole-chip-rerun-7200.html
```

- The diagram is schematic. Section 3 gives the files and functions of each step.
- "old" marks the code of the old read kernel. "new" marks the code of the new read kernel.
- The `bwx12` lines of the diagram do not name every kernel. Part C also runs `k_asmread`. Part L and control I also run three test loops (section 3.4).
- `<s>` is the session number, 1 to 3. `<i>` is 1 or 2.
- `T72A<s>`, `T72L<s>`, `T72C<s>` and `T72I<i>` are the names of the steps. Each result folder carries the name of its step and its start time (UTC), for example `k120-T72A1-20261117T221209Z`.
- Part C uses `cfwd.spec` in sessions 1 and 3. It uses `crev.spec` in session 2 and in the extra process `T72C4`.

## 3. Test code, in calling order

### 3.1 Commands of the agent server (no script file)

No script holds these commands. The record of the Claude Code session of 2026-11-17 holds them [Ref3]. That record lies outside the project folder.

1. Line 309 of the record writes `local.sha` on the agent server. It copies `go.sh`, `ra.sh`, the three spec files and `local.sha` to CRB with `tar` over `ssh`. On CRB, `sha256sum -c local.sha` checks the copied files.
   - This step did not copy `rx.sh` or the three binaries. They were already on CRB.
   - `go.sh` checks `rx.sh` and `bwx12` by sha256 before use (lines 22 and 23). `ra.sh` checks `bw_old` and `bw_new` (lines 16 to 20).
   - The local `go.sh` is not the copied text any more. The message of its line 20 was changed on 2026-11-24 (section 7). In the local folder, `sha256sum -c local.sha` now prints `go.sh: FAILED`.
2. Line 313 starts the driver on CRB: `nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null &`. `L` is the log file `~/cache-perf/results/go-T72-<time>.log`. The companion of `go.sh` explains each part of this command (section "Behavior a reader must know").
3. Line 339 copies the log and the result folders of parts A, L and C back with `tar` over `ssh`.
4. Line 353 writes `go2.sh` and `go2.sha`. It copies both to CRB. On CRB, `sha256sum -c go2.sha` checks the copy.
5. Line 365 starts `go2.sh` in the same way, with the log `go2-T72-<time>.log`.
6. Line 377 copies the log of `go2.sh` and the two result folders of control I back.

### 3.2 The driver `go.sh`

- [`tmp/agent-scratch/w120-7200-2026-11-17/go.sh`](../tmp/agent-scratch/w120-7200-2026-11-17/go.sh) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/go.sh.md)): Top-level driver of the rerun: three sessions of parts A, L and C.
  - The local file and its companion show the text of 2026-11-24. It differs from the text that ran in the message of line 20 only (section 7).
  - Call sequence:
    - `go.sh` (line 1): driver: checks, then 3 sessions, then one more part C process
      - `fail` (line 18): only when a check fails: state line, then exit status 1
      - `state` (line 17): state line at the start, after each step, at the end
      - `ra.sh`: part A, once per session: checks, wait, then 24 processes
        - `ra.sh:one`: 24 processes: bw_old and bw_new in turn per kernel. Round 2 reverses the order
          - `bandwidth.orig.c:k_read`: old read kernel: first process of round 1, last process of round 2
          - `bandwidth.c:k_read`: new read kernel: second process of round 1, second last of round 2
          - `bandwidth.orig.c:k_write, k_copy, k_asmread, k_asmwrite, k_asmcopy`: the other five kernels of bw_old, one process each per round
          - `bandwidth.c:k_write, k_copy, k_asmread, k_asmwrite, k_asmcopy`: the other five kernels of bw_new, one process each per round
      - `runx` (line 30): part L and part C: one call of rx.sh each
        - `rx.sh`: checks, wait, starts bwx12 on CPUs 0-119, writes the rc line
          - `bwx12.c:main`: one process: 120 threads run the kernel sequence of the spec line
            - `bwx12.c:k_oldread`: old read kernel (parts L and C)
            - `bwx12.c:k_read`: new read kernel (part C only)
            - `bwx12.c:k_asmread`: hand-written load-only loop (parts L and C)
            - `bwx12.c:k_read_nop96, k_read_nop256, k_read_1pl`: test loops (part L only)
        - `rxok` (line 29): tests the rc line in launches.txt
        - `state` (line 17): state line after the step

### 3.3 Part A: `ra.sh`, then `bw_old` (old code) and `bw_new` (new code)

- [`tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`](../tmp/agent-scratch/w120-7200-2026-11-17/ra.sh) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/ra.sh.md)): Part A runner: 24 processes of bw_old and bw_new with 120 threads.
  - Call sequence:
    - `ra.sh NAME` (line 1): go.sh calls it once per session with NAME T72A1, T72A2 or T72A3
      - `taskset -c 0-119 ra.sh NAME` (line 9): restart of the script, limited to CPUs 0 to 119
      - `check_marker` (line 12): stop with status 3 if the marker file exists
      - `sha256sum -c` (line 16): compare bw_old and bw_new with the checksums of 2026-11-13
      - `load` (line 24): print the three load averages for probe.txt
      - `one` (line 39): 24 calls: bw_old and bw_new in turn per kernel. Round 2: reverse order
- Old code: [`tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c`](../tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c) ([explained](../tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c.md)): Source of bw_old: the benchmark with the old read kernel, run in part A.
  - Call sequence of one `bw_old` process:
    - `ra.sh:one`: part A: starts one bw_old process per kernel and round
      - `main` (line 339): started by ra.sh: one process per kernel and round
        - `parse_cpus` (line 80): reads the list 0-119: 120 CPUs
        - `parse_bytes` (line 62): reads 256M: 268435456 bytes per thread
        - `worker` (line 288): 120 threads, each runs this function once
          - `pin_cpu` (line 107): thread i pins itself to CPU i
          - `alloc_buf` (line 118): reserves the 256 MiB buffer and asks for 2 MiB pages
          - `k_write` (line 150): first touch of the buffer, not timed
          - `pass` (line 260): warm-up pass before each interval, not timed
            - `k_read` (line 138): the selected kernel, here the old read kernel
          - `now_s` (line 55): clock read at the start of the timed interval
          - `pass` (line 260): timed passes, repeated until 0.5 s have passed
            - `k_read` (line 138): kernel read: the old read kernel
            - `k_write` (line 150): kernel write, in its own process
            - `k_copy` (line 156): kernel copy, in its own process
            - `k_asmread` (line 173): kernel asmread, in its own process
            - `k_asmwrite` (line 197): kernel asmwrite, in its own process
            - `k_asmcopy` (line 220): kernel asmcopy, in its own process
          - `now_s` (line 55): clock read after every pass
        - `main: rate loop` (line 420): waits at the barrier twice, then prints one row per interval
- New code: [`tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`](../tmp/agent-scratch/kernels-2026-11-13/bandwidth.c) ([explained](../tmp/agent-scratch/kernels-2026-11-13/bandwidth.c.md)): Source of bw_new: the benchmark with the new read kernel (part A).
  - Call sequence of one `bw_new` process:
    - `ra.sh:one`: part A: starts one bw_new process per kernel and round
      - `main` (line 496): reads the arguments, starts 120 threads, computes and prints the rates
        - `parse_cpus` (line 81): `--cpus 0-119` becomes the CPU numbers 0 to 119
        - `parse_bytes` (line 63): `--bytes 256M` becomes 268,435,456 bytes
        - `worker` (line 446): one thread per CPU, started by `pthread_create` in line 566
          - `pin_cpu` (line 108): binds thread i to CPU i
          - `alloc_buf` (line 119): maps the 256 MiB buffer of the thread
          - `k_write` (line 213): first write of the buffer, not timed
          - `pass` (line 418): warm-up pass before every interval, not timed
            - `k_read` (line 184): the selected kernel, here the new read kernel
          - `now_s` (line 56): clock read at the start of the timed interval
          - `pass` (line 418): timed passes, repeated until 0.5 s have passed
            - `k_read` (line 184): new read kernel: the process with `--kernel read`
            - `k_write` (line 213): the process with `--kernel write`
            - `k_copy` (line 239): the process with `--kernel copy`
            - `k_asmread` (line 297): hand-written read loop: the process with `--kernel asmread`
            - `k_asmwrite` (line 321): the process with `--kernel asmwrite`
            - `k_asmcopy` (line 344): the process with `--kernel asmcopy`
          - `now_s` (line 56): clock read after every pass, and the last read ends the interval
        - `main (rate and output rows)` (line 577): bytes of all threads / longest thread time, one row per interval

Old code and new code of part A, step by step:

| Step | Old code | New code |
|---|---|---|
| Binary | `bw_old` | `bw_new` |
| Source file | `bandwidth.orig.c` | `bandwidth.c` |
| Entry point | `main` (line 339) | `main` (line 496) |
| One thread | `worker` (line 288) | `worker` (line 446) |
| First touch of the buffer | `k_write` (line 150) | `k_write` (line 213) |
| One pass over the buffer | `pass` (line 260) | `pass` (line 418) |
| Read kernel (kernel name `read`) | `k_read` (line 138) | `k_read` (line 184) |
| Hand-written loop (kernel name `asmread`) | `k_asmread` (line 173) | `k_asmread` (line 297) |
| Machine code of `k_read` in `probe.txt` (section 4.8) | section `bw_old k_read`, lines 155 to 227 | section `bw_new k_read`, lines 23 to 38 |

- `bandwidth.c` also holds the old `k_read`, `k_write` and `k_copy` (lines 136 to 166) and the old `pass` (lines 381 to 415). These lines are comments that start with the word "History". gcc does not compile them. `bw_new` runs the functions that the table names.

### 3.4 Parts L and C: `rx.sh`, then `bwx12`

- [`tmp/agent-scratch/w120-2026-11-15/rx.sh`](../tmp/agent-scratch/w120-2026-11-15/rx.sh) ([explained](../tmp/agent-scratch/w120-2026-11-15/rx.sh.md)): Runner script: starts one bwx12 process per spec line and records its exit status.
  - Call sequence:
    - `go.sh:runx or go2.sh`: callers: 7 calls in parts L and C, 2 calls in control I
      - `rx.sh` (line 1): checks, result folder, env.txt, then the loop over the spec lines
- Input of `rx.sh`, one argument line each:
  - [`tmp/agent-scratch/w120-7200-2026-11-17/like.spec`](../tmp/agent-scratch/w120-7200-2026-11-17/like.spec) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/like.spec.md)): Argument line of part L and control I: one bwx12 process, five kernels.
  - [`tmp/agent-scratch/w120-7200-2026-11-17/cfwd.spec`](../tmp/agent-scratch/w120-7200-2026-11-17/cfwd.spec) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/cfwd.spec.md)): Argument line of part C, forward order: oldread, read, asmread in one process.
  - [`tmp/agent-scratch/w120-7200-2026-11-17/crev.spec`](../tmp/agent-scratch/w120-7200-2026-11-17/crev.spec) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/crev.spec.md)): Argument line of part C, reverse order: asmread, read, oldread in one process.
- [`tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`](../tmp/agent-scratch/bwx12-2026-11-15/bwx12.c) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/bwx12.c.md)): Source of bwx12, the benchmark program that parts L, C and control I run.
  - Call sequence of one `bwx12` process with these argument lines:
    - `main` (line 2904): entry point. rx.sh starts it under `taskset -c 0-119`
      - `now_ns` (line 327): line 2908: process start time `t_base_ns`
      - `restrict_cpus` (line 368): line 2911: removes CPUs above 119 from the allowed CPU set
      - `trial_main` (line 2800): NOT called: no argument is `--trial` (lines 2912 to 2914)
      - `parse_long` (line 353): `--threads 120`, `--rounds 2`, `--pmu-type 11`
      - `parse_cpus` (line 388): `--cpus 0-63,64-119`: the list 0, 1, ... 119
      - `parse_bytes` (line 334): `--bytes 256M`: 268435456 bytes
      - `parse_seq` (line 1750): `--seq`: each kernel name becomes an index into `kernels[]`
      - `parse_events` (line 1771): `--events`: 6 names and 6 codes
      - `worker` (line 1632): 120 threads, created at line 3012. Thread i runs on CPU i
        - `pin_cpu` (line 415): line 1642: binds the thread to its CPU
        - `open_counters` (line 1582): line 1644: opens the 6 counters as one group
        - `alloc_buf` (line 434): line 1645: maps the 256 MiB buffer, asks for 2 MiB pages
          - `buf_len` (line 426): buffer length, rounded up to a multiple of 2 MiB
        - `k_write` (line 531): line 1646: first touch, writes every word of the buffer once
        - `call` (line 1491): line 1669, per interval: warm-up, one untimed pass, same kernel as below
        - `now_ns` (line 327): line 1681: spin-wait until the common start time
        - `read_group` (line 1617): line 1685: first counter reading, before `t0`
        - `cpu_ns` (line 1609): line 1686: thread CPU time before `t0`
        - `now_ns` (line 327): line 1688: `t0`, the start of the timed interval
        - `call` (line 1491): line 1695, timed: one 2 MiB chunk per call
          - `k_oldread` (line 474): kernel `oldread`: the old read kernel, text in macro `DEF_OLDREAD` (line 461)
          - `k_read` (line 501): kernel `read`: the new read kernel (part C only)
          - `k_asmread` (line 642): kernel `asmread`: hand-written load-only loop, text in macro `DEF_ASMREAD` (line 616)
          - `k_read_nop96` (line 1063): asmread loop plus 96 nop, macro `DEF_ASMREAD` (part L and control I only)
          - `k_read_nop256` (line 1199): asmread loop plus 256 nop, macro `DEF_ASMREAD` (part L and control I only)
          - `k_read_1pl` (line 988): one 16 B load per 64 B line (part L and control I only)
        - `now_ns` (line 327): line 1700: `t1` after each chunk. The loop ends at the deadline
        - `cpu_ns` (line 1609): line 1718: thread CPU time after the last `t1`
        - `read_group` (line 1617): line 1719: second counter reading
      - `now_ns` (line 327): line 3059, main thread, per interval: common start = now + 2 ms
      - `libc:printf`: lines 3077 to 3102 of `main`: I row, T rows, C rows
      - `now_ns` (line 327): line 3110: start of the page-state reading
      - `read_smaps` (line 1515): line 3111, main thread: page state before the first and after each interval
        - `buf_len` (line 426): the length that the mapping of a buffer must have
      - `read_vmstat` (line 1545): line 3112: four counters of the whole system
      - `now_ns` (line 327): line 3113: end of the page-state reading, for its duration in ms
      - `print_p` (line 1570): line 3117: one P row per buffer
        - `print_na` (line 1562): one field, or `NA` for a negative value
      - `libc:printf`: line 3118 of `main`: the `# page_read` line

Old code and new code inside `bwx12.c`:

| Step | Old code | New code | Hand-written loop |
|---|---|---|---|
| Kernel name in `--seq` | `oldread` | `read` | `asmread` |
| Kernel function | `k_oldread` (line 474) | `k_read` (line 501) | `k_asmread` (line 642) |
| Source text of the loop | macro `DEF_OLDREAD(name)`, lines 461 to 473 | body of `k_read`, lines 501 to 528 | macro `DEF_ASMREAD(name, nops)`, lines 616 to 641 |
| Called by | `call` (line 1491) | `call` (line 1491) | `call` (line 1491) |
| Runs in | parts L and C, control I | part C | parts L and C, control I |
| Machine code in `listing.txt` (section 4.8) | lines 133 to 205 | lines 1 to 16 | lines 59 to 82 |

- Lines 474, 642, 1063 and 1199 are macro calls. Each call creates one kernel function. The loop text is in the macro.
- Part L and control I also run three test loops: `k_read_nop96` (line 1063) and `k_read_nop256` (line 1199), both made by the macro `DEF_ASMREAD`, and `k_read_1pl` (line 988).
- `bwx12.c` also holds a second, plain C text of these loops for a machine that is not AArch64: a second macro `DEF_ASMREAD` (line 858), a second `k_read`, `k_write` and `k_asmread` (lines 880, 881 and 883) and a second `k_read_1pl` (line 1014). They are in the `#else` branches of lines 851 to 897 and 1005 to 1022. The CRB binary does not hold them. Line 2 of each of the 9 csv files that `bwx12` wrote in the test (sections 4.4 to 4.6) says `kernels=aarch64`.
- The thread function of every kernel is `worker` (line 1632). The entry point is `main` (line 2904).

### 3.5 Control I: `go2.sh`

- [`tmp/agent-scratch/w120-7200-2026-11-17/go2.sh`](../tmp/agent-scratch/w120-7200-2026-11-17/go2.sh) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/go2.sh.md)): Driver of control I: the part L line twice, each from an idle machine.
  - Call sequence:
    - `go2.sh` (line 1): control I: checks, then two times wait and one bwx12 process
      - `fail` (line 14): only when a check fails: state line, then exit status 1
      - `state` (line 13): state line at the start, before and after each process, at the end
      - `waitidle` (line 25): waits for a 1-minute load average below 1.0
      - `rx.sh`: checks, wait, starts bwx12 on CPUs 0-119, writes the rc line
        - `bwx12.c:main`: one process: 120 threads run the kernel sequence of like.spec
          - `bwx12.c:k_oldread`: old read kernel, first in the sequence
          - `bwx12.c:k_asmread`: hand-written load-only loop, second in the sequence
          - `bwx12.c:k_read_nop96, k_read_nop256, k_read_1pl`: test loops, third to fifth in the sequence
      - `rxok` (line 23): tests the rc line in launches.txt

### 3.6 Build of the binaries (ran before the rerun)

The rerun built nothing. These files built and tested the three binaries on 2026-11-13 and 2026-11-15.

- Build of `bw_old` and `bw_new` (2026-11-13):
  - [`tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`](../tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh) ([explained](../tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh.md)): Script of 2026-11-13 that built bw_old and bw_new and ran the first test.
    <details>
    <summary>Call sequence of <code>run_kernels.sh</code></summary>

      - `run_kernels.sh all` (line 1): ran on CRB on 2026-11-13, not during the rerun of 2026-11-17
        - `taskset -c 0-119 run_kernels.sh all` (line 9): restart of the script, limited to CPUs 0 to 119
        - `check_marker` (line 13): stop with status 3 if the marker file exists
        - `load` (line 20): print the three load averages for probe.txt
        - `build` (line 29): gcc with the flags of line 19, four calls
          - `gcc bandwidth.orig.c` (line 31): builds bw_old, the binary with the old read kernel
          - `gcc bandwidth.c` (line 32): builds bw_new, the binary with the new read kernel
          - `gcc selftest.c` (line 33): builds the self-test of the new source
          - `gcc -c probe.c` (line 34): compiles three copy candidates, never run
        - `objdump` (line 42): machine code of the six kernels of both binaries to probe.txt
        - `selftest` (line 55): checks the kernels of the new source, must end with status 0
        - `one` (line 60): mode all: 192 one-thread processes, then 24 processes with 120 threads
          - `check_marker` (line 13): before every process
          - `bandwidth.orig.c:main`: binary bw_old: half of the processes, one kernel each
            - `bandwidth.orig.c:worker`: one thread: pins, allocates, times the kernel
              - `bandwidth.orig.c:pin_cpu`: pin the thread to its CPU
              - `bandwidth.orig.c:alloc_buf`: buffer of the thread, with a request for huge pages
              - `bandwidth.orig.c:k_write`: writes the whole buffer once, before any timing
              - `bandwidth.orig.c:pass`: one pass of the chosen kernel over the buffer
                - `bandwidth.orig.c:k_read`: old read kernel (kernel name read)
                - `bandwidth.orig.c:k_asmread`: hand-written load-only loop (kernel name asmread)
                - `bandwidth.orig.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels
          - `bandwidth.c:main`: binary bw_new: half of the processes, one kernel each
            - `bandwidth.c:worker`: one thread: pins, allocates, times the kernel
              - `bandwidth.c:pin_cpu`: pin the thread to its CPU
              - `bandwidth.c:alloc_buf`: buffer of the thread, with a request for huge pages
              - `bandwidth.c:k_write`: writes the whole buffer once, before any timing
              - `bandwidth.c:pass`: one pass of the chosen kernel over the buffer
                - `bandwidth.c:k_read`: new read kernel (kernel name read)
                - `bandwidth.c:k_asmread`: same hand-written loop as in bw_old (kernel name asmread)
                - `bandwidth.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels

    </details>

  - The folder `results` holds three records of `run_kernels.sh` of 2026-11-13: 18:12:10 UTC (mode `probe`), 18:12:22 UTC (mode `all`, the first test) and 18:32:18 UTC (mode `probe`). In mode `probe` the script builds the binaries, writes the machine code of the kernels to `probe.txt` and runs the self-test. It times nothing. In mode `all` it does the same and then runs the timed processes. Each run compiled `bw_old` and `bw_new` again (lines 31 and 32). The run of 18:32:18 UTC compiled the local text of `bandwidth.c` (sha256 `f1985072...`). It recorded the sha256 value `fd7c14df...` for `bw_new`. `ra.sh` checks this value before part A [Ref4].
  - [`tmp/agent-scratch/kernels-2026-11-13/selftest.c`](../tmp/agent-scratch/kernels-2026-11-13/selftest.c) ([explained](../tmp/agent-scratch/kernels-2026-11-13/selftest.c.md)): Self-test of the six kernels of bandwidth.c. Not run in the 2026-11-17 rerun.
  - [`tmp/agent-scratch/kernels-2026-11-13/probe.c`](../tmp/agent-scratch/kernels-2026-11-13/probe.c) ([explained](../tmp/agent-scratch/kernels-2026-11-13/probe.c.md)): Three compile-only candidates for the copy kernel. Not used in the 2026-11-17 rerun.
- Build of `bwx12` (2026-11-15):
  - [`tmp/agent-scratch/bwx12-2026-11-15/build12.sh`](../tmp/agent-scratch/bwx12-2026-11-15/build12.sh) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/build12.sh.md)): Build script: compiled the runner bwx12 on CRB on 2026-11-15 and recorded the build.
    <details>
    <summary>Call sequence of <code>build12.sh</code></summary>

      - `build12.sh` (line 30): ran on CRB on 2026-11-15, not during the whole-chip test
        - `check_marker` (line 32): called on lines 33, 50 and 61: status 3 if the marker file exists
        - `taskset` (line 34): restarts this script limited to CPUs 0 to 119
        - `gcc` (line 47): compiles bwx12.c, which includes bwx12_selftest.c, into the binary bwx12
        - `bwx12 --selftest` (line 51): first run of the new binary, output to selftest-bwx12.txt
          - `bwx12.c:main`: finds the option and calls the self-test
            - `bwx12_selftest.c:selftest`: calls all 55 kernels on small buffers and checks the memory
              - `bwx12.c:call`: runs one kernel, the same function as in the benchmark
                - `bwx12.c:k_oldread, k_read, k_asmread, k_read_nop96, k_read_nop256, k_read_1pl`: the six kernels of the whole-chip test, among the 55
        - `bwx12 --list` (line 62): prints the 55 kernel names for the loop
        - `objdump` (line 64): once per kernel: machine code of the kernel function for listing.txt
        - `objdump` (line 86): machine code of the two timed functions of the trial mode
        - `placement` (line 107): called on lines 114, 117, 130 and 142, each with one binary
          - `nm` (line 109): lists the symbols and addresses of that binary
        - `sha256sum` (line 155): checksums of seven files for build.txt

    </details>

  - [`tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`](../tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c.md)): Self-test of the runner bwx12. Runs at build time, never in a timed run.
  - [`tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`](../tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py.md)): Acceptance check of the bwx12 kernel machine code, run after the build.
  - [`tmp/agent-scratch/bwx12-2026-11-15/test_kernels12.py`](../tmp/agent-scratch/bwx12-2026-11-15/test_kernels12.py) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/test_kernels12.py.md)): Local test of the bwx12 kernel source and its acceptance checker. It measures nothing.

## 4. Test data

### 4.1 Where the old and the new read kernel are in the data

| Part | File | Rows of the old read kernel | Rows of the new read kernel | Rate |
|---|---|---|---|---|
| A | `threads120.csv` | interval rows after a line `-- binary bw_old kernel read` | interval rows after a line `-- binary bw_new kernel read` | column `aggregate_GBps`: bytes of all threads / longest thread time / 1e9, in GB/s |
| L, control I | `a6456.csv` | rows with the kernel name `oldread` | no row. `asmread` is used in place of it [Ref2] | sum over the 120 T rows of one interval of (bytes / elapsed_s / 1e9), in GB/s |
| C | `cfwd.csv`, `crev.csv` | rows with the kernel name `oldread` | rows with the kernel name `read` | the same sum over the T rows |

- GB = 1e9 bytes.
- No csv file of sections 4.3 to 4.6 holds the rows of one kernel only.
- Part A: each `threads120.csv` holds the 24 processes of one session. The old and the new read kernel run in separate processes (`bw_old` and `bw_new`). Each process starts with its own header line.
- Part C: the old and the new read kernel run in the same process.
- Part L and control I: the file holds rows of the old read kernel and of `asmread`. It holds no row of the new read kernel.
- One listed csv file holds one kernel only: `base8000/partA-A3-onebuf500/threads120.csv` (section 4.9) holds 3 processes of `bw_old`, kernel `read`.
- The companion of each csv file lists its intervals with the kernel and the rate.

### 4.2 Logs of the two driver scripts

- Folder: `results`
  - [`go-T72-20261117T221209Z.log`](../results/go-T72-20261117T221209Z.log) ([explained](../results/go-T72-20261117T221209Z.log.md)): Log of go.sh: machine settings and machine state between the steps of the rerun.
  - [`go2-T72-20261117T222335Z.log`](../results/go2-T72-20261117T222335Z.log) ([explained](../results/go2-T72-20261117T222335Z.log.md)): Log of go2.sh: machine state around the two idle-start processes of control I.

### 4.3 Part A: three sessions of `ra.sh`

- Folder: `results/k120-T72A1-20261117T221209Z`
  - [`threads120.csv`](../results/k120-T72A1-20261117T221209Z/threads120.csv) ([explained](../results/k120-T72A1-20261117T221209Z/threads120.csv.md)): 24 processes of `bw_old` and `bw_new`, 72 interval rows with rates.
  - [`probe.txt`](../results/k120-T72A1-20261117T221209Z/probe.txt) ([explained](../results/k120-T72A1-20261117T221209Z/probe.txt.md)): Machine state before and after the session, sha256 of both binaries.
- Folder: `results/k120-T72A2-20261117T221518Z`
  - [`threads120.csv`](../results/k120-T72A2-20261117T221518Z/threads120.csv) ([explained](../results/k120-T72A2-20261117T221518Z/threads120.csv.md)): 24 processes of `bw_old` and `bw_new`, 72 interval rows with rates.
  - [`probe.txt`](../results/k120-T72A2-20261117T221518Z/probe.txt) ([explained](../results/k120-T72A2-20261117T221518Z/probe.txt.md)): Machine state before and after the session, sha256 of both binaries.
- Folder: `results/k120-T72A3-20261117T221827Z`
  - [`threads120.csv`](../results/k120-T72A3-20261117T221827Z/threads120.csv) ([explained](../results/k120-T72A3-20261117T221827Z/threads120.csv.md)): 24 processes of `bw_old` and `bw_new`, 72 interval rows with rates.
  - [`probe.txt`](../results/k120-T72A3-20261117T221827Z/probe.txt) ([explained](../results/k120-T72A3-20261117T221827Z/probe.txt.md)): Machine state before and after the session, sha256 of both binaries.

### 4.4 Part L: three sessions of `rx.sh` with `like.spec`

- Folder: `results/w120-T72L1-20261117T221329Z`
  - [`a6456.csv`](../results/w120-T72L1-20261117T221329Z/a6456.csv) ([explained](../results/w120-T72L1-20261117T221329Z/a6456.csv.md)): One `bwx12` process: 10 intervals, 1200 thread rows, kernels `oldread,asmread,read_nop96,read_nop256,read_1pl`.
  - [`env.txt`](../results/w120-T72L1-20261117T221329Z/env.txt) ([explained](../results/w120-T72L1-20261117T221329Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72L1-20261117T221329Z/launches.txt) ([explained](../results/w120-T72L1-20261117T221329Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72L1-20261117T221329Z/stderr.txt) ([explained](../results/w120-T72L1-20261117T221329Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72L2-20261117T221638Z`
  - [`a6456.csv`](../results/w120-T72L2-20261117T221638Z/a6456.csv) ([explained](../results/w120-T72L2-20261117T221638Z/a6456.csv.md)): One `bwx12` process: 10 intervals, 1200 thread rows, kernels `oldread,asmread,read_nop96,read_nop256,read_1pl`.
  - [`env.txt`](../results/w120-T72L2-20261117T221638Z/env.txt) ([explained](../results/w120-T72L2-20261117T221638Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72L2-20261117T221638Z/launches.txt) ([explained](../results/w120-T72L2-20261117T221638Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72L2-20261117T221638Z/stderr.txt) ([explained](../results/w120-T72L2-20261117T221638Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72L3-20261117T221947Z`
  - [`a6456.csv`](../results/w120-T72L3-20261117T221947Z/a6456.csv) ([explained](../results/w120-T72L3-20261117T221947Z/a6456.csv.md)): One `bwx12` process: 10 intervals, 1200 thread rows, kernels `oldread,asmread,read_nop96,read_nop256,read_1pl`.
  - [`env.txt`](../results/w120-T72L3-20261117T221947Z/env.txt) ([explained](../results/w120-T72L3-20261117T221947Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72L3-20261117T221947Z/launches.txt) ([explained](../results/w120-T72L3-20261117T221947Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72L3-20261117T221947Z/stderr.txt) ([explained](../results/w120-T72L3-20261117T221947Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.

### 4.5 Part C: four processes of `rx.sh` with `cfwd.spec` or `crev.spec`

- Folder: `results/w120-T72C1-20261117T221436Z`
  - [`cfwd.csv`](../results/w120-T72C1-20261117T221436Z/cfwd.csv) ([explained](../results/w120-T72C1-20261117T221436Z/cfwd.csv.md)): One `bwx12` process: 6 intervals, 720 thread rows, kernels `oldread,read,asmread`.
  - [`env.txt`](../results/w120-T72C1-20261117T221436Z/env.txt) ([explained](../results/w120-T72C1-20261117T221436Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72C1-20261117T221436Z/launches.txt) ([explained](../results/w120-T72C1-20261117T221436Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72C1-20261117T221436Z/stderr.txt) ([explained](../results/w120-T72C1-20261117T221436Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72C2-20261117T221745Z`
  - [`crev.csv`](../results/w120-T72C2-20261117T221745Z/crev.csv) ([explained](../results/w120-T72C2-20261117T221745Z/crev.csv.md)): One `bwx12` process: 6 intervals, 720 thread rows, kernels `asmread,read,oldread`.
  - [`env.txt`](../results/w120-T72C2-20261117T221745Z/env.txt) ([explained](../results/w120-T72C2-20261117T221745Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72C2-20261117T221745Z/launches.txt) ([explained](../results/w120-T72C2-20261117T221745Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72C2-20261117T221745Z/stderr.txt) ([explained](../results/w120-T72C2-20261117T221745Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72C3-20261117T222054Z`
  - [`cfwd.csv`](../results/w120-T72C3-20261117T222054Z/cfwd.csv) ([explained](../results/w120-T72C3-20261117T222054Z/cfwd.csv.md)): One `bwx12` process: 6 intervals, 720 thread rows, kernels `oldread,read,asmread`.
  - [`env.txt`](../results/w120-T72C3-20261117T222054Z/env.txt) ([explained](../results/w120-T72C3-20261117T222054Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72C3-20261117T222054Z/launches.txt) ([explained](../results/w120-T72C3-20261117T222054Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72C3-20261117T222054Z/stderr.txt) ([explained](../results/w120-T72C3-20261117T222054Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72C4-20261117T222136Z`
  - [`crev.csv`](../results/w120-T72C4-20261117T222136Z/crev.csv) ([explained](../results/w120-T72C4-20261117T222136Z/crev.csv.md)): One `bwx12` process: 6 intervals, 720 thread rows, kernels `asmread,read,oldread`.
  - [`env.txt`](../results/w120-T72C4-20261117T222136Z/env.txt) ([explained](../results/w120-T72C4-20261117T222136Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72C4-20261117T222136Z/launches.txt) ([explained](../results/w120-T72C4-20261117T222136Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72C4-20261117T222136Z/stderr.txt) ([explained](../results/w120-T72C4-20261117T222136Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.

### 4.6 Control I: two processes of `go2.sh`

- Folder: `results/w120-T72I1-20261117T222700Z`
  - [`a6456.csv`](../results/w120-T72I1-20261117T222700Z/a6456.csv) ([explained](../results/w120-T72I1-20261117T222700Z/a6456.csv.md)): One `bwx12` process: 10 intervals, 1200 thread rows, kernels `oldread,asmread,read_nop96,read_nop256,read_1pl`.
  - [`env.txt`](../results/w120-T72I1-20261117T222700Z/env.txt) ([explained](../results/w120-T72I1-20261117T222700Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72I1-20261117T222700Z/launches.txt) ([explained](../results/w120-T72I1-20261117T222700Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72I1-20261117T222700Z/stderr.txt) ([explained](../results/w120-T72I1-20261117T222700Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.
- Folder: `results/w120-T72I2-20261117T223227Z`
  - [`a6456.csv`](../results/w120-T72I2-20261117T223227Z/a6456.csv) ([explained](../results/w120-T72I2-20261117T223227Z/a6456.csv.md)): One `bwx12` process: 10 intervals, 1200 thread rows, kernels `oldread,asmread,read_nop96,read_nop256,read_1pl`.
  - [`env.txt`](../results/w120-T72I2-20261117T223227Z/env.txt) ([explained](../results/w120-T72I2-20261117T223227Z/env.txt.md)): Machine state before the process, sha256 of `bwx12`.
  - [`launches.txt`](../results/w120-T72I2-20261117T223227Z/launches.txt) ([explained](../results/w120-T72I2-20261117T223227Z/launches.txt.md)): Launch line with load and arguments, then the rc line.
  - [`stderr.txt`](../results/w120-T72I2-20261117T223227Z/stderr.txt) ([explained](../results/w120-T72I2-20261117T223227Z/stderr.txt.md)): Error output of `bwx12`. Empty: 0 bytes.

### 4.7 Input files, rules and launch records

- Folder: `tmp/agent-scratch/w120-7200-2026-11-17`
  - The three spec files are listed in section 3.4.
  - [`local.sha`](../tmp/agent-scratch/w120-7200-2026-11-17/local.sha) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/local.sha.md)): sha256 list of go.sh, ra.sh and the three spec files, written at launch.
    - The `go.sh` entry is the sha256 value of the text that ran. The local `go.sh` has another value since 2026-11-24 (section 7).
  - [`go2.sha`](../tmp/agent-scratch/w120-7200-2026-11-17/go2.sha) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/go2.sha.md)): sha256 of go2.sh, the script of control I, written at launch.
  - [`baselines-and-rules.txt`](../tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt.md)): List of 8000 MT/s baselines and comparison rules, written before the run.

### 4.8 Records of the builds: compiler flags and machine code of the kernels

- Folder: `results/kernels-20261113T181222Z`
  - [`probe.txt`](../results/kernels-20261113T181222Z/probe.txt) ([explained](../results/kernels-20261113T181222Z/probe.txt.md)): Build record and machine code of bw_old and bw_new, the part A binaries.
- Folder: `tmp/agent-scratch/bwx12-2026-11-15/crb-build-1`
  - [`build.txt`](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt.md)): Build record of the runner bwx12: compiler, flags, self-test result, sha256 digests.
  - [`listing.txt`](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt.md)): Machine instructions of every bwx12 kernel, as text, written when bwx12 was built.
  - [`offsets.tsv`](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/offsets.tsv) ([explained](../tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/offsets.tsv.md)): Address table of the 55 bwx12 kernels: function start, loop start, offset modulo 64.

### 4.9 Earlier data that the analysis compares with (8000 MT/s, and one 7200 MT/s sample)

This test did not generate these files. They have no companion, except the two converted copies. The fixed list of baselines is in `baselines-and-rules.txt` (section 4.7). The facts sheet lists every file that the analysis opened [Ref1].

| Row name | Folder below `results/` | What it is |
|---|---|---|
| A-1 | `kernels-20261113T181222Z` | The first whole-chip test of 2026-11-13: `threads120.csv`, same process order as `ra.sh`. |
| A-2 | `partA-20261113T205055Z` | `A1.csv`: same binaries, other process order. Arguments differ by `--per-thread` and the `--cpus` spelling. |
| A-3 | `partA-20261113T205055Z` | `A3.csv`, only the 3 processes with tags `onebuf-ms500-1` to `-3`: `bw_old`, kernel `read`. |
| L-1 | `w120-R8-20261117T020549Z` | `a6456.csv` with the argument line of `like.spec`, at 8000 MT/s. |
| L-2 | `w120-R1-20261115T185140Z` | `p1nop.csv`, `p2add.csv`: bwx12, 4 s intervals. |
| L-3 | `w120-R5-20261115T203152Z` | `thp.csv`: bwx12, 4 s intervals. |
| L-4 | `w120-R6-20261115T203438Z` | `st1.csv`, `st2.csv`, `st3.csv`: bwx12, 4 s intervals. |
| R0 | `w120-R0-20261115T165608Z` | `p1.csv`, `p2.csv`: the older runner bwx11, 6 s intervals. |
| R0b | `w120-R0b-20261115T170342Z` | `cA.csv`, `cB.csv`, `cC.csv`: the older runner bwx11, 4 s intervals. |
| F72d12 | `w120-w120-F72d12-20261117T200231Z` | `a6456.csv`: a 7200 MT/s sample of the same boot, run before the rerun. |
| B7a, B7b | `B7-20261113T232859Z` | First runner bwx, `B7.csv`: nearest 8000 MT/s data for kernel `read`. Second folder: `B7-20261114T024352Z`. |
| C3a, C3b | `C3-20261114T022708Z` | First runner bwx, `C3.csv`: pooled with B7a and B7b. Second folder: `C3-20261114T054116Z`. |
| B5a, B5b, B5a-rev, B5b-rev | `B5-20261114T011723Z` | First runner bwx, `B5.csv`: forward and reverse kernel order. Second folder: `B5-20261114T043213Z`. |
| X2d12 | `w120-X2d12-20261117T040922Z` | `a6456.csv`: 8000 MT/s, 12 modules, firmware test setting. Not a baseline. |
| X1d10 | `w120-X1d10-20261117T034916Z` | `a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline. |
| X1d10b | `w120-X1d10b-20261117T040407Z` | `a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline. |
| BASEd10 | `w120-BASEd10-20261117T041738Z` | `a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline. |

- In rows L-2, L-3, L-4, R0, R0b, X1d10, X1d10b and BASEd10 the analysis uses only `oldread` at position 0 and `asmread` at position 1. These files hold more kernels (5 to 15 per sequence).
- In rows B7a, B7b, C3a and C3b the analysis uses only the processes with a tag `common-6000-*`: 8 of the 48 processes of each `B7.csv` and 4 of the 18 processes of each `C3.csv`. The four B5 rows use all 4 processes of each `B5.csv`. In all eight rows the analysis keeps only the kernels `oldread`, `read` and `asmread`.
- Converted copies of rows A-2 and A-3. Their header lines have the format of `threads120.csv`:
  - [`tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A1/threads120.csv`](../tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A1/threads120.csv) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A1/threads120.csv.md)): 8000 MT/s data of 2026-11-13 (`A1.csv`) with rewritten header lines, 12 processes.
  - [`tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A3-onebuf500/threads120.csv`](../tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A3-onebuf500/threads120.csv) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/base8000/partA-A3-onebuf500/threads120.csv.md)): The 3 `onebuf-ms500` processes of `A3.csv` (8000 MT/s, 2026-11-13) with rewritten header lines.
  - The `sed` and `awk` commands that wrote the two copies are in `baselines-and-rules.txt`, lines 47 to 53 (section 4.7). No script file holds them. The analysis reads the copies only for the cross-check with `stat_k120.py`. It takes the rates of rows A-2 and A-3 from the raw files `A1.csv` and `A3.csv`.

## 5. Analysis code: from the raw rows to the final throughput

### 5.1 The path of one number

Part A (binaries `bw_old` and `bw_new`):

1. The binary computes the rate of one interval: bytes of all threads / longest thread time / 1e9. The code is in `main` of `bandwidth.orig.c` and of `bandwidth.c` (section 3.3). It prints the rate in the column `aggregate_GBps`.
2. `facts_data.py`: `read_k120` (line 264) reads the interval rows.
3. `build_facts.py`: `add_k120` (line 119) makes one record per interval row.
4. `facts_text.py`: `analyse` (line 283) pairs the old and the new process of the same session and round. `med` (line 279) takes the median of the 3 intervals of one process. `analyse` computes the drop of each pair as (1 - new median / old median) x 100.
5. `build_facts.py`: `write_json` (line 899) writes the records and the verdicts to `facts.json`. The verdicts hold the smallest and the largest drop of each part.
6. `make_report.py` reads `facts.json`. `file_process` (line 166) checks each record against its csv row. `a_pair` (line 444) computes the drop between two process medians a second time. `xc_drops` (line 646) compares the smallest and the largest drop with section 3.4 of `FACTS.md`.

Parts L and C and control I (runner `bwx12`):

1. `bwx12.c`: `main` (line 2904) prints one I row per interval and one T row per thread (bytes and elapsed time of the thread).
2. `facts_data.py`: `read_bwx` (line 313) reads the rows. `bwx_intervals` (line 356) sums bytes / elapsed_s / 1e9 over the T rows of each interval.
3. `build_facts.py`: `add_bwx` (line 142) makes one record per interval with this sum as its rate.
4. `facts_text.py`: `pairs` (line 304) pairs the old-kernel interval and the load-only interval of one process and round. It computes the drop of each pair as (1 - new / old) x 100.
5. `build_facts.py`: `write_json` (line 899) writes the records and the verdicts to `facts.json`.
6. `make_report.py`: `val` (line 176) sums the T rows of the raw csv again. `drop` (line 417) computes each drop a second time. `xc_drops` (line 646) compares the smallest and the largest drop with section 3.4 of `FACTS.md`.

Both paths:

- `facts_data.py`: `rng` (line 461) gives the lowest, the highest and the median rate of a group of records.
- `facts_text.py`: `compare` (line 333) compares a 7200 MT/s range with an 8000 MT/s range.
- `make_report.py`: the class `Rg` (line 192) holds the range of one group of records on the report page.

### 5.2 Quick statistics tools (also used as a cross-check)

- [`tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`](../tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py.md)): Quick statistics tool for part A: reads threads120.csv, reports rates per kernel and binary.
  - Call sequence:
    - `main` (line 89): command-line use: folders, optional `--pool` and `--json`
      - `load` (line 24): once per folder: processes and intervals of `threads120.csv`
      - `rows_of` (line 47): once per folder and once for the pool: statistics per kernel and binary
      - `print_text` (line 70): once per group, when `--json` is not given
    - `build_facts.py:run_checks`: second use: cross-check while the facts sheet is built
      - `load` (line 24): its intervals are compared with those of the facts_data.py parser
    - `facts_data.py:read_k120`: uses the pattern `HDR` (line 21) to find header lines
- [`tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py`](../tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/stat_bwx.py.md)): Quick statistics tool for bwx12 csv files: per-interval totals, statistics per kernel.
  - Call sequence:
    - `main` (line 125): command-line use: folders, optional `--pool` and `--json`
      - `interval_rows` (line 61): once per folder: one row per interval
        - `read_csv` (line 38): once per csv file: thread rates and I row rates
        - `half` (line 34): mesh of each thread, for the sums per mesh
      - `summarize` (line 84): once per folder, once more over all folders with `--pool`
      - `rounded` (line 102): only with `--json`
      - `fmt_half` (line 112): text output: the two mesh columns of each interval line
      - `print_summary` (line 118): text output: Part 2 table per folder and pooled
    - `build_facts.py:run_checks`: second use: cross-check while the facts sheet is built
      - `interval_rows` (line 61): totals, mesh sums, 64+56 test and flagged counts are compared

### 5.3 The facts sheet: `build_facts.py` and its modules

- [`tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py`](../tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/build_facts.py.md)): Main analysis script: builds the interval records, runs integrity checks, writes facts.json and FACTS.md.
  <details>
  <summary>Call sequence of <code>build_facts.py</code> (57 entries)</summary>

    - `main` (line 1033): entry point: collect, check, render, then write the two output files
      - `collect` (line 50): reads the result files and saved machine records, builds the dictionary `D`
        - `facts_data.py:read_try6`: boot of the rerun: boot id, MemTotal, 12 modules, 7200 MT/s
        - `facts_data.py:read_boot_table`: boot table of the DIMM report, used for the earlier folders
        - `facts_data.py:read_log`: called twice: log of go.sh, then log of go2.sh
        - `facts_data.py:find`: the one result folder of each tag of the rerun
        - `facts_data.py:read_probe`: probe.txt of each part A folder
        - `facts_data.py:read_k120`: part A: processes and interval rows of 3 threads120.csv files
        - `facts_data.py:read_bwx`: parts L, C, I: the I, T and P rows of 9 csv files
        - `facts_data.py:bwx_intervals`: per interval: sum over the T rows of bytes / elapsed_s / 1e9
        - `facts_data.py:read_env`: env.txt: Linux kernel release and sha256 of bwx12
        - `facts_data.py:read_launches`: launches.txt: launch time, load, arguments, exit status
        - `facts_data.py:folder_date`: the time in a folder name, for the 12 steps of the rerun
        - `facts_data.py:clock`: turns a time of day of a run file into date and time
        - `add_k120` (line 119): rerun part A: 3 calls, one record per interval row
          - `iso` (line 34): formats the launch time of the process
          - `facts_data.py:base_record`: returns a record with every key, filled from the arguments
        - `add_bwx` (line 142): rerun parts L, C, I: 9 calls, one record per interval
          - `facts_data.py:bwx_intervals`: gives the rate of each interval (sum over its T rows)
          - `facts_data.py:base_record`: returns a record with every key, filled from the arguments
        - `facts_data.py:read_k120`: 8000 MT/s baselines A-1, A-2 and A-3
        - `open_probe13` (line 568): records of the 2026-11-13 run and the journal of its boot
          - `facts_data.py:read_error_records`: hardware error records of the saved journal
          - `facts_data.py:step_headers`: header lines of A1.csv, A2.csv and A3.csv
        - `state_of` (line 58): memory speed, module count and boot label of an earlier folder
          - `boot_of` (line 44): the boot of the DIMM report that contains a time
        - `add_k120` (line 119): baselines A-1, A-2, A-3: 3 calls
        - `add_bwx` (line 142): 17 earlier csv files of bwx12 and bwx11, 8 data sets with `POS01`
        - `add_bwx` (line 142): sections of the first runner bwx, kernels of `READ3` only
        - `hw_records` (line 296): hardware error records inside the process windows of 6 data sets
          - `facts_data.py:read_error_records`: hardware error records of the saved journal
          - `facts_data.py:bwx_intervals`: start time and end time of every interval of a process
        - `hw_compare` (line 340): intervals with a record against the same interval of the other round
          - `cmp_` (line 363): one interval, its partner, and the difference of the two rates
            - `other` (line 358): the interval of the same kernel and position in the other round
        - `open_fw` (line 429): saved firmware setting lists and replies of the settings tool
        - `open_a2pre` (line 509): the run folder that ended shortly before baseline A-2
          - `facts_data.py:step_headers`: header lines of A5.csv and A6.csv
        - `open_mod` (line 536): a 10-module boot, read for the two lines that prove 12 modules
      - `run_checks` (line 653): 27 checks, appended to `D['checks']` in a fixed order
        - `chk` (line 661): appends one check: key, pass flag, text
        - `per` (line 664): builds a text with one value per rerun folder
        - `facts_data.py:sha256`: checksums of the local scripts and spec files
        - `stat_k120.py:load`: second reader of the part A files, for check `x-k120`
        - `stat_bwx.py:interval_rows`: second reader of the bwx csv files, for check `x-bwx`
        - `facts_data.py:bwx_intervals`: the rates of this script, compared with those of stat_bwx.py
      - `facts_text.py:render`: ranges, medians, percent values, verdicts and the text of FACTS.md
        - `facts_text4.py:section4`: sections 4 to 6 of FACTS.md, ends the script unless every check passed
      - `write_json` (line 899): writes facts.json, rates rounded to 0.001 GB/s
        - `facts_data.py:sel`: selects records by field values, for the counts in `meta`
        - `iso` (line 34): formats every time of `meta`
        - `r3` (line 38): line 996: rate of an interval that holds or may hold an error record
        - `hw_compare_json` (line 400): the hardware error view in the form of facts.json
          - `r3` (line 38): rounds one number to 3 decimal places
        - `r3all` (line 1017): rounds every float of the verdicts
          - `r3` (line 38): rounds one number to 3 decimal places
        - `r3` (line 38): line 1027: rounds every float of each record

  </details>

- [`tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py`](../tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/facts_data.py.md)): Parsers of the raw result files and range functions for the facts sheet.
  <details>
  <summary>Call sequence of <code>facts_data.py</code> (39 entries)</summary>

    - `build_facts.py:main`: entry point: writes facts.json and FACTS.md
      - `build_facts.py:collect`: reads all raw files and builds the interval records
        - `read_try6` (line 206): record of 12 modules at 7200 MT/s in the boot of the rerun
        - `read_boot_table` (line 405): boot history, used for the folders of earlier runs
        - `read_log` (line 83): state lines of the logs of go.sh and go2.sh
        - `find` (line 397): result folder of each tag of the rerun
        - `read_probe` (line 117): probe.txt of each part A folder
        - `read_k120` (line 264): part A csv: processes, interval rows, printed rate
        - `read_bwx` (line 313): bwx12 csv of parts L, C and control I
          - `_new_section` (line 309): empty container for the rows of the process
        - `bwx_intervals` (line 356): sum of the per-thread rates of each interval
        - `read_env` (line 159): env.txt: checksum of the runner, process list
        - `read_launches` (line 137): launches.txt: launch time, load, exit status
          - `clock` (line 68): time of day to full date and time
            - `folder_date` (line 62): date and time of the folder name
        - `build_facts.py:add_k120`: one record per part A interval, rate = agg
          - `rel` (line 46): folder path in the form R/...
          - `base_record` (line 421): record with all keys, rate kind KIND_A
        - `build_facts.py:add_bwx`: one record per bwx12 interval, rate = total
          - `bwx_intervals` (line 356): called again for the same section
          - `base_record` (line 421): record with all keys, rate kind KIND_X
        - `read_k120` (line 264): again, for the 8000 MT/s baseline files of part A
        - `build_facts.py:open_probe13`: records of the run of 2026-11-13
          - `read_error_records` (line 174): hardware error records of a saved journal
          - `step_headers` (line 193): step lines of the csv files of run_partA.sh
        - `read_bwx` (line 313): again, for the bwx csv files of earlier runs
        - `build_facts.py:hw_records`: hardware error records inside process windows
          - `read_error_records` (line 174): the same saved journal
      - `build_facts.py:run_checks`: integrity checks of the files and the records
        - `sha256` (line 55): checksums of the local copies of the run scripts
      - `facts_text.py:render`: text of the facts sheet
        - `facts_text.py:analyse`: pairs of old and new intervals, and record groups of several data sets
          - `sel` (line 442): intervals of one data set and kernel
        - `facts_text.py:compare`: 7200 MT/s range against 8000 MT/s range
          - `rng` (line 461): lowest, highest, median, counts
          - `overlap` (line 471): decides the wording of the comparison
          - `gap` (line 475): distance between the nearest ends
          - `width_pct` (line 484): width of the 8000 MT/s range in percent
      - `build_facts.py:write_json`: writes facts.json, rates rounded to 3 decimals

  </details>

- [`tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py`](../tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/facts_text.py.md)): Analysis module: computes the old-against-new statistics, writes sections 0-3 and 7 of FACTS.md.
  <details>
  <summary>Call sequence of <code>facts_text.py</code> (50 entries)</summary>

    - `build_facts.py:main`: entry point: collects the data, runs the checks, then calls `render`
      - `render` (line 341): returns the verdict object `V` and the text of FACTS.md
        - `analyse` (line 283): builds the pairs for Q1 and the selector `pool`
          - `cell` (line 292): the 3 intervals of one part A process, sorted
            - `facts_data.py:sel`: returns the records that match every condition
          - `need` (line 36): guard: stops the script when a condition is false
          - `med` (line 279): median of the 3 rates of one part A process
          - `pairs` (line 304): bwx12 pairs and drops per process and round, 5 calls
            - `one` (line 286): checks that exactly one record matches and returns it
        - `register` (line 156): numbers every script and raw file for section 7
          - `Refs.add` (line 146): gives a new file the next reference number
        - `one_len` (line 372): the one interval length of a data set, in seconds
        - `facts_data.py:_open`: opens a file and notes its path for the file list
        - `mtime` (line 384): file time of the rules file and of `local.sha`
        - `cgroup` (line 402): records and drops of one part C group, 5 calls
        - `pool` (line 324): the 8000 MT/s pools of oldread and asmread, 4 calls
        - `compare` (line 333): 7200 MT/s range against 8000 MT/s range, 8 calls
          - `facts_data.py:rng`: lowest, highest and median rate, and the counts of a list
          - `facts_data.py:overlap`: true when two ranges share at least one value
          - `facts_data.py:gap`: distance of the nearest ends of two ranges, in GB/s
          - `facts_data.py:width_pct`: width of a range in percent of its lower end
        - `inside` (line 468): true when the 7200 MT/s range lies inside the 8000 MT/s range
        - `Refs.__call__` (line 151): `ref(path)`: the text `[RefN]` of a registered file
        - `hm` (line 64): formats a time as `HH:MM:SS`
        - `table` (line 132): Markdown lines of one table
        - `procs_str` (line 732): process counts per user of one state line, as text
        - `hmd` (line 72): formats a time with its date
        - `g` (line 46): formats a rate with 2 decimals, half up
          - `_q` (line 41): decimal rounding, half up
        - `dur` (line 90): formats seconds as hours, minutes and seconds
        - `inboot` (line 1000): number of the boot that contains a time
        - `facts_data.py:rel`: path as the sheet writes it: `R/...` or `S/...`
        - `one_set` (line 1063): the one reply to a change in a reply file `set.txt`
        - `sp` (line 50): formats a range as `lo to hi`
        - `nn` (line 98): formats the counts of a range as intervals / processes / boots
        - `lgap` (line 1141): seconds between the last two launches of a baseline file
        - `pc` (line 54): formats a percent value with 1 decimal, half up
        - `lrow` (line 1315): one table row of section 3.2 from one pair
        - `cellf` (line 1365): one part C rate with position and kernel before
        - `mm` (line 1367): the two mesh sums of a record as text
        - `cpair` (line 1401): one part C group for the Q1 table of section 3.4
          - `tags` (line 1400): the folder tags of a record list, each once
          - `sess` (line 108): the sessions of a record list as text
        - `pcr` (line 58): lowest and highest drop of a list, as text
        - `facts_text4.py:section4`: appends sections 4, 5, 6 and sets the verdict for Q2
          - `q2row` (line 359): adds one comparison row to `V['q2_rows']`
        - `short_version` (line 477): the three sentences and the detail list of section 0
          - `nns` (line 124): n as intervals / processes / sessions / boots
        - `check_dates` (line 79): finds a time of another day without its date
      - `build_facts.py:write_json`: writes facts.json with the records and `V`

  </details>

- [`tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py`](../tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/facts_text4.py.md)): Analysis module: compares 7200 with 8000 MT/s rates, writes FACTS.md sections 4 to 6.
  <details>
  <summary>Call sequence of <code>facts_text4.py</code> (65 entries)</summary>

    - `build_facts.py:main`: entry point: collects the records, calls render, writes FACTS.md and facts.json
      - `facts_text.py:render`: writes sections 1 to 3, calls section4, then writes sections 0 and 7
        - `section4` (line 24): writes sections 4, 5 and 6 and the Q2 verdicts
          - `facts_data.py:sel`: returns the records that match the given field values
          - `facts_text.py:dur`: prints a time span as hours, minutes and seconds
          - `facts_data.py:_open`: opens like.spec, cfwd.spec and crev.spec and notes the file names
          - `noseq` (line 123): removes the `--seq` value before the three argument lines are compared
          - `facts_text.py:need`: stops the build when the data do not show a stated pattern
          - `facts_text.py:Refs.__call__`: the argument `ref`: returns the label `[RefN]` of a file
          - `source` (line 57): section 4.1: Source cell of each earlier row
            - `src` (line 44): labels of the csv files that hold the records
          - `facts_text.py:table`: formats a header and rows as a Markdown table
          - `facts_text.py:hmd`: prints a time with its date
          - `facts_text.py:hm`: prints a time of day as HH:MM:SS
          - `kind_txt` (line 262): section 4.1: position of an error record against the used intervals
            - `facts_text.py:g`: prints a number with 2 decimal places, rounded half up
          - `sg` (line 339): section 4.1: prints a rate difference with its sign
          - `c['hw']['cmp']['lst']` (line 373): joins the loop names with commas and `and`
          - `lst` (line 411): joins texts with commas and `and`
          - `ranges` (line 48): section 4.2: range table of bw_old read, part A and rows A-1 to A-3
            - `facts_data.py:rng`: lowest, highest, median, interval count and process count of a list
            - `facts_text.py:nn`: prints n as intervals / processes, with sessions and boots as options
            - `facts_text.py:sp`: prints a range as lowest to highest, 2 decimal places
          - `cmps` (line 71): section 4.2: overlap tests of bw_old read, part A
            - `facts_text.py:compare`: two ranges, overlap flag, nearest-end distance, wording, width
              - `facts_data.py:overlap`: true when two ranges share at least one value
              - `facts_data.py:gap`: distance of the nearest ends, signed, 0 for an overlap
              - `facts_data.py:width_pct`: width of a range in percent of its lower end
            - `facts_text.py:q2row`: appends the test to `V['q2_rows']` for facts.json
            - `facts_text.py:pc`: prints a percent value with 1 decimal place, rounded half up
          - `lrows` (line 471): range-table rows of L-1 to L-4 for one kernel and position
          - `orows` (line 472): range-table rows of R0 and R0b for one kernel and position
          - `ranges` (line 48): section 4.2: range table of oldread, part L and the 8000 MT/s rows
          - `cmps` (line 71): section 4.2: overlap tests of oldread for part L, F72d12 and control I
          - `grp` (line 539): start-state view: pool records of the group `idle` or `busy`
          - `names` (line 544): start-state view: the processes of a group as text
          - `loads` (line 543): start-state view: sorted loads at launch of a group
          - `lsrc` (line 545): start-state view: labels of the launches.txt files of a group
          - `facts_text.py:_q`: prints one percent value with 2 decimal places, rounded half up
          - `secs` (line 18): interval lengths of a record list as text
          - `scm` (line 674): keeps the records of processes with `--start common`
          - `ranges` (line 48): section 4.2: range table of oldread, part C and the 8000 MT/s rows
          - `cmps` (line 71): section 4.2: overlap tests of oldread for three part C groups
          - `facts_text.py:nns`: prints n of rerun records with the session text
          - `cellt` (line 722): section 4.3: three rates with their pass counts as one table cell
          - `facts_text.py:med`: median of the rates of a record list
          - `same` (line 781): section 4.3: keeps the intervals with 663 or 664 passes
          - `one_v` (line 42): prints one rate, or the range of several rates
          - `av` (line 825): section 4.3: per-thread average rates of a record list
          - `span` (line 826): prints one value, or lowest to highest
          - `ranges` (line 48): section 4.4: range table of asmread at position 1, all rows
          - `cmps` (line 71): section 4.4: overlap tests of asmread for part L, F72d12 and control I
          - `ranges` (line 48): section 4.5: range table of kernel read, part C and runner bwx rows
          - `facts_text.py:q2row`: section 4.5: stores the two read groups of part C, without a wording
          - `ranges` (line 48): section 4.5: range table of asmread, part C groups and 8000 MT/s rows
          - `m_k` (line 1004): section 4.5: key and label of a scope that matches the kernel before
          - `cmps` (line 71): section 4.5: overlap tests of asmread for three part C groups
          - `in_` (line 1126): section 4.6: tests whether a value lies inside a range
          - `where` (line 1132): section 4.6: says where one record comes from
          - `facts_text.py:pool`: section 4.7: `N['pool']`, the records of rows R0 and R0b
          - `mrow` (line 1220): section 4.7: one table row with the ranges of the two mesh sums
          - `side` (line 1311): section 4.9: both sides of a comparison as verdict text
          - `facts_data.py:rel`: section 4.9: path of env.txt as the facts sheet writes it
          - `facts_text.py:pcr`: section 6: lowest and highest of a list of percent values
          - `sgn` (line 1516): section 6: prints a rate difference with its sign

  </details>


### 5.4 The report page: `make_report.py` and its test

- [`tmp/agent-scratch/w120-7200-2026-11-17/make_report.py`](../tmp/agent-scratch/w120-7200-2026-11-17/make_report.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/make_report.py.md)): Last analysis step: builds the HTML report page from facts.json and raw csv rows.
  <details>
  <summary>Call sequence of <code>make_report.py</code> (101 entries)</summary>

    - `top-level statements of make_report.py` (line 20): No main function: statements run top to bottom. Small text helpers are left out.
      - `read_retry` (line 64): Lines 234 and 235: loads facts.json and FACTS.md, with up to 10 tries.
        - `facts_complete` (line 230): FACTS.md only: tests that the text holds its last section.
      - `need` (line 46): First call in line 239. Hard assertion with 238 call sites in the file.
        - `stop` (line 42): Prints a STOP message and ends the script with exit status 1.
      - `sel` (line 242): Lines 272 to 332: selects the interval records of one group.
      - `expect` (line 260): The same lines: asserts the number of intervals and processes of the group.
      - `check` (line 52): First call in line 337. Adds one PASS or FAIL line to `CHECKS`.
      - `val` (line 176): Line 341: rate of each bwx12 record of `USED`. Line 344: records of `OTHER`.
        - `t_rows` (line 124): bwx12 record: the 120 T rows directly after its I row.
          - `file_lines` (line 116): Reads the csv file of the record once and keeps its lines.
            - `lines_of` (line 80): Opens the file and returns its lines.
        - `t_rows_block` (line 142): Record of the older runner bwx: the same 120 rows, read by line number.
      - `q` (line 90): Lines 341 and 344: rounds the sum to 0.01 GB/s for the test.
      - `i_row_rate` (line 158): The same lines: the rate printed in the I row.
      - `file_process` (line 166): Line 349: checks each used part A record against its csv row.
      - `pairs_in_process` (line 407): Lines 431 to 436: old and load-only interval of one process and round.
      - `drops_of` (line 421): Line 439: the drop of each pair in percent.
        - `drop` (line 417): (1 - new / old) x 100.
        - `val` (line 176): Returns the value that the first call stored in the record.
      - `Rg` (line 192): Lines 440 to 469: the range object of each record group.
        - `__init__ (method of Rg)` (line 195): Sorts the records. Stores lowest, highest, median, n and the processes.
          - `val` (line 176): Rate of each record of the group.
          - `median` (line 102): Median of these rates.
      - `a_pair` (line 444): Lines 454 and 455: part A, drop between the medians of two processes.
      - `overlaps (method of Rg)` (line 207): Lines 486 to 514: tests the expected overlap results of this run.
      - `nearest (method of Rg)` (line 210): Lines 489 to 545: distance of the nearest ends of two ranges.
      - `farthest (method of Rg)` (line 216): Line 506: distance of the farthest ends, for part L with asmread.
      - `md_sections` (line 556): Line 586: splits FACTS.md into its numbered sections.
      - `T34 (lambda)` (line 653): Lines 654 to 659: finds the row of a part in FACTS.md section 3.4.
        - `facts_row` (line 598): First table row of the section that passes the test.
          - `md_tables` (line 569): Parses the Markdown tables of the section.
      - `xc_drops` (line 646): Lines 654 to 659: computed drops against that row.
        - `col` (line 592): Picks one cell of the row by the start of its column title.
        - `near` (line 616): True when two values differ by at most the tolerance.
        - `check` (line 52): Adds the PASS or FAIL line.
      - `xc_range` (line 620): Line 661 and later: a computed range against a FACTS.md table cell.
        - `rng_of` (line 610): Reads the two numbers of the cell.
      - `xc_text_range` (line 640): Line 665 and later: a range that stands in the text of FACTS.md.
      - `xc_val` (line 626): Line 670 and later: one computed value against a FACTS.md table cell.
      - `grouped` (line 56): Line 673 and later: replaces the checks of one block by one line.
      - `wording` (line 481): Lines 696 to 719: the fixed text for overlap or no overlap.
      - `width_pct` (line 476): Line 697 and later: width of a range in percent of its lower end.
      - `xc_text` (line 633): Line 704 and later: a value with its unit in the text of FACTS.md.
      - `vrow` (line 773): Lines 787 to 798: finds one verdict record of facts.json.
      - `xv` (line 779): Lines 787 to 797: computed ranges, n and distance against that record.
      - `state_lines` (line 847): Line 862: the state lines of the logs of go.sh and go2.sh.
      - `launch_window` (line 944): Line 962: launch and end time of each process of rows L-1 to L-4.
      - `hw_in` (line 953): Line 964 and later: hardware error records between two times.
      - `a_headers` (line 972): Line 990: process header lines of the csv files of rows A-1 to A-3.
      - `secs` (line 983): Line 1002 and later: a time of day in seconds.
      - `t_rows` (line 124): Lines 1018 and 1019: start and end of the lowest asmread interval.
      - `clock` (line 1022): Line 1030: launch time plus seconds, as a time of day.
      - `set_records` (line 1047): Lines 1064 to 1067: changed firmware settings in four set.txt files.
      - `proc_list` (line 1100): Lines 1118 and 1131: process lists that were saved before a launch.
      - `mem_line` (line 1149): Line 1156: the memory size line of two saved Linux kernel logs.
      - `spec_line` (line 1178): Line 1195: the argument lines of like.spec, cfwd.spec and crev.spec.
      - `launch_args` (line 1188): Line 1201 and later: the arguments of a launch line in launches.txt.
      - `bwx_header` (line 1235): Line 1258: header lines of each process of runner bwx.
      - `klog_boot` (line 1289): Line 1303: saved Linux kernel logs of X2d12 and of three 10-module boots.
      - `addref` (line 815): Lines 1389 to 1474: reference entries. Each path must exist.
      - `bwx_row` (line 1555): Lines 1562 to 1572: the rows of figure 1 for bwx12.
        - `pairs_in_process` (line 407): Pairs the intervals of the row.
        - `Rg` (line 192): Range of each kernel of the row.
        - `drops_of` (line 421): Drops of the pairs of the row.
        - `f1_row` (line 1551): Packs the row into a dictionary.
      - `f1_row` (line 1551): Lines 1574 and 1577: the rows of figure 1 for part A.
      - `band_title` (line 1876): Line 1889 and later: tooltip text of a grey band of figure 2.
      - `p_row` (line 1695): Lines 1890 to 1932: the rows of figure 2, each with its range.
        - `Rg` (line 192): Range of the records of the row.
      - `l_rows` (line 1869): Lines 1896 and 1922: the rows L-1 to L-4 of figure 2.
      - `a_new_block` (line 1905): Line 1933: the blocks of figure 2 for bw_new read, rounds 1 and 2.
      - `panel_rows` (line 1938): Lines 1943 to 1957: lists the rows of a panel for the caption tests.
      - `legend` (line 1963): Lines 1975 and 1983: the legends of the two figures.
      - `facts_words` (line 2279): Line 2290: reads the word list of FACTS.md.
      - `fw` (line 2293): Lines 2329 to 2395: copies definitions of that word list.
      - `ref` (line 821): Line 2356 and later: a reference mark. Its number comes later.
      - `UL` (line 1493): Lines 2423 to 2467: the bullet lists of the page text.
      - `build` (line 2677): Line 2784: assembles the whole page as one text.
        - `P` (line 1488): Line 2679: the three paragraphs of the Short version.
        - `panel` (line 1756): Lines 2695 and 2698: figure 2, one call per panel.
          - `beeswarm` (line 1682): Vertical offsets of the dots of one row.
          - `hit_cell` (line 1725): Hover area of each dot.
          - `val` (line 176): Rate of a dot, for its tooltip.
          - `src` (line 359): File and line numbers of a dot, for its tooltip.
        - `fig1` (line 1593): Lines 2729 to 2731: figure 1 in the wide, mid and narrow layout.
          - `drop_txt` (line 425): Drop text on the line between the two dots.
          - `dot_title` (line 1545): Tooltip text of a dot.
        - `q1_table` (line 2003): Line 2736: Table 1, the drop per part.
          - `table` (line 1501): HTML of the table. Every table function ends with this call.
        - `detail_fig1` (line 2255): Line 2739: the table view of figure 1.
        - `q2_table` (line 2079): Line 2752: Table 2, 7200 MT/s against 8000 MT/s, with its notes.
        - `visits_table` (line 2184): Line 2756: Table 3, the three visits of the part L line.
        - `dist_table` (line 2213): Line 2758: Table 4, three kinds of distance.
        - `detail_fig2` (line 2266): Line 2760: the table view of figure 2.
        - `state_table` (line 2503): Line 2768: Table 5, the machine state.
        - `load_table` (line 2219): Line 2771: Table 6, the 1-minute load average at launch.
      - `number_refs` (line 828): Line 2784: numbers the references in the order of first use.
      - `strip_tags` (line 1484): Lines 2787 to 2803: plain text of the page for the page checks.
      - `check` (line 52): Lines 2789 to 2813: the checks of the built page.
      - `end of the top-level statements` (line 2819): Prints the self-check list. Writes the page only when every line is PASS.

  </details>

- [`tmp/agent-scratch/w120-7200-2026-11-17/test_make_report.py`](../tmp/agent-scratch/w120-7200-2026-11-17/test_make_report.py) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/test_make_report.py.md)): Test script: checks that make_report.py stops on damaged input data.
  <details>
  <summary>Call sequence of <code>test_make_report.py</code> (5 entries)</summary>

    - `script body` (line 15): setup, 11 calls of `run`, verdict from the exit statuses
      - `run` (line 21): one case: damaged facts, patched generator copy, separate process
        - `mutate` (line 21): parameter: one of 9 damage functions (lines 37 to 65), or no change
        - `patch` (line 21): parameter: the last case (line 77) changes one path in the copy
        - `make_report.py:script body`: the patched copy runs as a separate Python process

  </details>


## 6. Results of the analysis

- Folder: `tmp/agent-scratch/w120-7200-2026-11-17`
  - [`facts.json`](../tmp/agent-scratch/w120-7200-2026-11-17/facts.json) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/facts.json.md)): Every interval as one record, plus run facts and verdicts.
  - [`FACTS.md`](../tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md) ([explained](../tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md.md)): The facts sheet: all tables and verdicts of the rerun.
- Folder: `new-test-kernel`
  - [`whole-chip-rerun-7200.html`](whole-chip-rerun-7200.html) ([explained](whole-chip-rerun-7200.html.md)): The report page with the final old-against-new throughput.

The final total rates of the 120 threads at 7200 MT/s [Ref5]. All values come from 1 boot of CRB.

Part A (binaries `bw_old` and `bw_new`, whole-pass stop, 0.5 s). One row per session and round. Each rate is the median of the 3 intervals of one process:

| Session | Round | `bw_old`, kernel `read`: median, GB/s | `bw_new`, kernel `read`: median, GB/s | New below old, % |
|---|---|---|---|---|
| 1 | 1 | 467.83 | 330.59 | 29.3 |
| 1 | 2 | 461.33 | 327.60 | 29.0 |
| 2 | 1 | 468.21 | 324.42 | 30.7 |
| 2 | 2 | 467.52 | 328.96 | 29.6 |
| 3 | 1 | 469.73 | 320.46 | 31.8 |
| 3 | 2 | 465.61 | 332.96 | 28.5 |

- The facts sheet gives the drop range of part A as 28.5 to 31.8 % (6 pairs of process medians).
- The comparison rules of the test allow no pooled range of `bw_new` over rounds or sessions (rule V3 of `baselines-and-rules.txt`). So the table has one row per pair of processes.
- Limit of part A: with the whole-pass stop the pass count moves in steps, and the rate moves with it. So the percent values of part A are less exact than those of parts L and C (section 3.1 of `FACTS.md`). Rule V3 says to take the main percent value from parts L and C.
- The facts sheet gives the 3 interval rates and the pass counts of each process (section 3.1 of `FACTS.md`).

Parts L and C and control I (runner `bwx12`, common stop, 6 s):

| Part | Group | Old read kernel (`oldread`): total rate, GB/s | New read kernel: total rate, GB/s | Below `oldread`, % |
|---|---|---|---|---|
| C | `read` directly after `oldread` (`cfwd.spec`: T72C1, T72C3) | 465.54 to 467.83 (4 intervals) | `read`: 320.89 to 324.98 (4 intervals) | 30.5 to 31.2 (4 pairs) |
| C | `read` directly after `asmread` (`crev.spec`: T72C2, T72C4) | 464.00 to 468.14 (4 intervals) | `read`: 322.22 to 326.27 (4 intervals) | 29.7 to 31.1 (4 pairs) |
| L | all 3 processes | 461.61 to 464.29 (6 intervals) | `asmread`, used in place of the new read kernel: 321.65 to 327.93 (6 intervals) | 29.2 to 30.5 (6 pairs) |
| Control I | both processes | 466.30 to 469.20 (4 intervals) | `asmread`, used in place of the new read kernel: 313.78 to 317.60 (4 intervals) | 31.9 to 32.8 (4 pairs) |

- A rate range gives the lowest and the highest interval rate of the group.
- The column "Below `oldread`" is the drop: (1 - new / old) x 100, computed per pair of intervals of the same process and round. The range gives the smallest and the largest drop of the group.
- Part C keeps the two kernel orders apart for `read`. Rule V2 of `baselines-and-rules.txt` asks for this. In each part C row, the `oldread` range comes from the two processes that the column "Group" names.
- The facts sheet gives three more groups of part C, for `asmread` (section 3.3 of `FACTS.md`).
- Part L and control I did not run the new read kernel. `asmread` is used in place of it there [Ref2].

How these numbers were made:

- Part A and the `bwx12` parts compute the total rate of one interval in two ways. Section 5.1 gives both formulas: step 1 of the part A path and step 2 of the bwx12 path.
- The script `tmp/agent-scratch/code-data-list-2026-11-21/make_list.py` wrote this list. Its function `result_tables` computed the medians and the rate ranges from the interval records of `facts.json`. It read the same intervals again from the raw csv files with the parsers of `stat_k120.py` and `stat_bwx.py`. Part A: the 3 interval rates of each of the 12 processes of the table are the same in both sources after rounding to 0.01 GB/s. `bwx12` parts: the lowest rate and the highest rate of each rate range are the same in both sources after rounding to 0.01 GB/s, and the interval count is the same.
- The percent ranges are the fields `smallest_drop_pct` and `largest_drop_pct` of `verdicts.q1_parts` in `facts.json`.
- The percent values of the part A table were computed by `make_list.py` from the medians. Their smallest and their largest value agree with `verdicts.q1_parts`.

## 7. Findings and open points of this list

- **Two texts of `bandwidth.c`: they differ in comment lines only.** The local `bandwidth.c` has the sha256 value `f1985072...`. The run of 18:12:22 UTC on 2026-11-13 (mode `all`, the first test) recorded `c1406e02...` for its `bandwidth.c`. The run of 18:12:10 UTC (mode `probe`) recorded the same value. All three build records of that day give the same sha256 value for the binary `bw_new` (`fd7c14df...`), and `ra.sh` checks that value. So the machine code that ran is not in doubt [Ref4]. The record of 18:32:18 UTC holds the sha256 value of the local `bandwidth.c` and the same sha256 value of `bw_new`. So the local text compiles to the binary that ran. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref6]. With this edit reversed, the local text has the sha256 value `c1406e02...` of the first test. No code line differs.
- **Two texts of `go.sh`: they differ in the message of line 20 only.** The run of 2026-11-17 used the text with the sha256 value `75bc50b0...`. This value is the `go.sh` entry of `local.sha`. The session record of 2026-11-17 shows that `sha256sum -c local.sha` printed `OK` for `go.sh` on CRB before the start [Ref3]. Line 295 of the record holds the last command that wrote `go.sh` before the copy to CRB. The script text in that command has the same sha256 value [Ref3]. On 2026-11-24 the message of line 20 was changed on the instruction of the user. `RUNNING file present` became `RUNNING file present, Jeremy or someone else is using CRB` [Ref7]. Jeremy is another user of CRB [Ref8]. The local `go.sh` now has the sha256 value `d68cf6c0...`. With this edit reversed, the local text has the value `75bc50b0...` again [Ref9]. `local.sha` was not changed. So `sha256sum -c local.sha` in the local folder now prints `go.sh: FAILED`. Check 20 of `build_facts.py` makes the same comparison (line 778, key `sha-local`). So a new run of `build_facts.py` fails check 20. It then stops and writes no file. With the edit reversed it passes [Ref9]. The edit was made in the local file only. `go2.sh` was not edited. It keeps the old message in lines 16 and 25.
- **The binaries are not local.** `bw_old`, `bw_new` and `bwx12` are in no local folder. They were on CRB on 2026-11-17. `ra.sh` checked the sha256 values of `bw_old` and `bw_new` at the start of each session. `rx.sh` checked the sha256 value of `bwx12` before each process. Insufficient data: whether the binaries are still on CRB today. A listing of the three paths on CRB would resolve it.
- **The machine code of the timing functions is not recorded.** The objdump records of section 4.8 do not hold `worker`, `pass` or `call`. `listing.txt` holds the 55 kernels of `bwx12`. `probe.txt` holds the 6 kernels of each part A binary, 3 functions of `probe.o` and the function `chase` of two other programs. Insufficient data: the machine code of `worker`, `pass` and `call`, and whether gcc placed `call` inside `worker`. An objdump of these functions on CRB would resolve it.
- **The top-level commands are in no script.** The commands of section 3.1 are only in the session record [Ref3]. That file lies outside the project folder.
- **The CPU list of the shell of `go2.sh` is not recorded.** `go.sh` prints the CPU list of its shell (line 38), and its log shows `0-119`. `go2.sh` has no such line. Neither start command holds a `taskset` [Ref3]. Hypothesis: the shell of `go2.sh` had the same list `0-119`. It started in the same way, about 11 min later, in the same boot. The companion of `go.sh` names the source of that list (section "Behavior a reader must know"). `rx.sh` starts `bwx12` under `taskset -c 0-119` (line 17). So the CPUs of the benchmark threads are known. Insufficient data: a direct record of the CPU list of the shell of `go2.sh`, and so of the wait loop of `rx.sh` during control I. A line `taskset -cp $$` in `go2.sh` would resolve it for a later run.
- **The text templates of the analysis hold numbers that the script does not compute.** A text template is a piece of the text of `FACTS.md` that is written in the script. The first lines of `facts_text.py` say that the templates hold words only. Five numbers that are written in the templates of that file: "12 state lines" (line 191), "24 processes, 72 interval rows" (line 194), "0 logins" (line 833), "1 task was runnable" (line 887) and "ended 8 s before the first process of row A-2" (line 255). Three of the five have a test. The check `A-shape` of `build_facts.py` (line 701) tests the text of line 194: 24 processes with 3 intervals each. The check `logins` of `build_facts.py` (line 689) tests the text of line 833. `facts_text4.py` stops the script when a check fails (line 1461). The `need` test in line 886 stops the script when the data do not show the value of line 887. Two of the five have no test in the scripts that write `FACTS.md`. No line of `build_facts.py`, `facts_text.py` or `facts_text4.py` compares the number of state lines with 12. `make_report.py` tests this number for the report page (line 863). For line 255, line 1011 computes the gap from the data, and the test of line 1014 accepts any gap between 0 s and 60 s. Both texts agree with the data today. The log of `go.sh` holds 12 state lines. The gap that the script computes is 8 s (item 11 of section 1.5 of `FACTS.md`). Insufficient data: the full list of such numbers in `facts_text.py`, `facts_text4.py` and `make_report.py`, and which of them a test checks. A reading of the string literals of these scripts that hold a digit would resolve it.
- **The test of the report generator checks the exit status only.** The first lines of `test_make_report.py` say that a damaged case must not write a page. The script prints whether the output file was written (line 32). Its verdict uses only the exit statuses of the 11 runs (line 79). So a damaged case that writes a page and ends with status 1 passes the test.
- **Part A does not record the page size of the buffers.** `bw_old` and `bw_new` ask Linux for 2 MiB pages and print the request only. They do not check the result. `bwx12` records the page state in its P rows. Insufficient data: whether the part A buffers lay on 2 MiB pages. The field AnonHugePages in `/proc/PID/smaps` of a running part A process would resolve it.

## 8. Left out of this list

- The files of the earlier runs of section 4.9 have no companion, except the two converted copies. This test did not generate them. The analysis reads them with the same two parsers as the files of sections 4.3 to 4.6 (`read_k120` and `read_bwx` of `facts_data.py`). Their layout differs in these points. `A1.csv`, `A3.csv`, `B7.csv`, `C3.csv` and `B5.csv` start each process with a line `-- step ...`. `A1.csv` and `A3.csv` also hold one row `thread,...` per thread and interval. Each `B7.csv`, `C3.csv` and `B5.csv` holds several processes in one file (48, 18 and 4). `B7.csv` and `B5.csv` hold no C rows. The C rows of `C3.csv` and of the files of rows L-2, L-3, L-4, R0 and R0b hold another list of counters than the C rows of sections 4.4 to 4.6. `C3.csv` holds 5 counters per C row, not 6.
- The code of the earlier runs of section 4.9 is not listed. The rerun did not start it. Examples: `new-test-kernel/run_partA.sh` (rows A-2 and A-3), `tmp/agent-scratch/w120-2026-11-15/r0.sh` (row R0), the spec files `r8.spec`, `r1.spec`, `r5.spec` and `r6.spec` of that folder (rows L-1 to L-4) and `r0b.spec` (row R0b), and the sources of the older runners in `tmp/agent-scratch/bwx11-2026-11-15` and `tmp/agent-scratch/bwx-2026-11-13`. The line of `like.spec` is the line with the tag `a6456` of `r8.spec`.
- The other 54 entries of `tmp/agent-scratch/w120-2026-11-15` (spec files, logs and scripts of the investigation of 2026-11-15) are not listed. The analysis reads two of them: `r0.sh`, for the sha256 value of bwx11, and `FINDINGS.md`. The facts sheet lists both [Ref1].
- The other machine records that the analysis reads (memory module records, saved Linux kernel logs, firmware settings) are not listed. The facts sheet lists them [Ref1].
- The scripts under `tmp/agent-scratch/w120-7200-2026-11-17/render` are not listed. They take screenshots of the report page, measure its layout and test the hover areas of Figure 2, all in a headless Chrome. They compute no rate.
- The backup, review and test folders and files of that scratch folder (`bak-*`, `r1fix-work`, `r2fix-work`, `r3fix-work`, `final-check`, `review-scratch`, `verify-*`, `review-w1.json`, `review-w2.json`, the empty folder `test-tmp`) are not listed.
- Two more build records of 2026-11-13 are not listed and have no companion: `results/kernels-20261113T181210Z/probe.txt` and `results/kernels-20261113T183218Z/probe.txt` [Ref4]. The record of 18:32:18 UTC is the one that holds the sha256 value of the local `bandwidth.c`.
- `README.orig.md` of `tmp/agent-scratch/kernels-2026-11-13` is not listed. No listed script reads it.
- The other build records in `tmp/agent-scratch/bwx12-2026-11-15/crb-build-1` are not listed: `build.out`, `selftest-bwx12.txt`, `seq-listing.txt`, `smoke12.txt`, `check_listing12.out`.
- `tmp/agent-scratch/bwx12-2026-11-15/ref-bwx11` (`build.txt`, `listing.txt` and `offsets.tsv` of the older runner bwx11) is not listed. `check_listing12.py` and `test_kernels12.py` compare with it.
- Files on CRB that the two build scripts only read are not listed. `build12.sh` read the binaries of the earlier runners bwx8, bwx10 and bwx11 with `nm`, for the placement lines of `build.txt`. `run_kernels.sh` read `bench/bandwidth.c`, `bench/latency` and `bench/homelat` below `~/cache-perf/`, for one sha256 line and two objdump sections of `probe.txt`.
- The lock file `~/cache-perf/results/go-T72.lock` on CRB is not listed. `go.sh` (line 21) and `go2.sh` (line 17) create it and lock it. Only one of the two scripts can run at a time. No command writes to it. The copy commands of section 3.1 did not copy it back.
- In `listing.txt` the companion shows the six timed kernels of the test. The other 49 kernels of `bwx12` are left out there. One of the 49 runs in the test: `k_write` (lines 17 to 32 of `listing.txt`) fills each buffer once before the first interval. It is not timed.
- Not every function is named in a call sequence. The call sequences name the functions on the path of the test. Small helper functions of the analysis scripts are left out, for example `esc`, `plural`, `f1` and `f2` of `make_report.py`. The table "Functions" of the companion of `make_report.py` lists these four. Most functions that the test never calls are left out too, for example `usage` in the three C programs and the kernels of `bwx12.c` that the argument lines do not select. Three entries are exceptions. `trial_main` of `bwx12.c` is named and marked "NOT called". `fail` of `go.sh` and `fail` of `go2.sh` are named. `fail` runs only when a check fails, and no check failed in the rerun.

## References

- [Ref1] `tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: section 7 "Files" lists every raw file and script that the analysis used.
- [Ref2] `tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`, line 36: "In part L, asmread stands in for the new read kernel (same loop: 8 ldp q per 256 B)".
- [Ref3] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl`: record of the Claude Code session of 2026-11-17. Lines 309, 313, 339, 353, 365 and 377 hold the commands of section 3.1. Line 310 holds the output of the copy command, with `go.sh: OK`. Line 295 holds the last command that wrote `go.sh` before the copy.
- [Ref4] `results/kernels-20261113T181210Z/probe.txt`, `results/kernels-20261113T181222Z/probe.txt`, `results/kernels-20261113T183218Z/probe.txt`: line 15 (sha256 of `bandwidth.c`) and line 20 (sha256 of `bw_new`) of the three build records. `tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`, lines 16 to 20: the check of the two binaries.
- [Ref5] `tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: the list `intervals` (one record per interval, field `GBps`) and the list `verdicts.q1_parts` (one entry per compared group).
- [Ref6] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`, line 1000: record of the Claude Code session of 2026-11-13. It holds the edit of `bandwidth.c` between the runs of 18:12:22 UTC and 18:32:18 UTC. The file lies outside the project folder.
- [Ref7] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl`, lines 2153 and 2245: record of the Claude Code session in which line 20 of `go.sh` was changed. The session began on 2026-11-22. Line 2153 holds the instruction of the user (2026-11-24, 20:27:54 UTC). Line 2245 holds the edit. The file lies outside the project folder.
- [Ref8] `jeremy-plan-constraints-2026-10-30.md`, lines 12 and 13: notes of 2026-10-30 about the tests of Jeremy on CRB. The file `/tmp/positron-perf.RUNNING` is present for the whole of each time window that is reserved for these tests.
- [Ref9] `tmp/agent-scratch/go-edit-2026-11-24`: tests of 2026-11-24 for the edit of `go.sh` line 20, with their output in the files that end with `.out`. `check_line20.py` puts the old line back in a copy of the text of `go.sh` and compares the sha256 value. It does not change `go.sh`. `check_facts_build.py` runs `build_facts.py` in a copy of the run folder, with the edited text and with the old line. `go.sh.as-run-2026-11-17` is a copy of `go.sh` from before the edit.
