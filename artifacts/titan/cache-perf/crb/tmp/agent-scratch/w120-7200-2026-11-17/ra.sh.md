# `ra.sh` explained

- Source file: `ra.sh` in this folder (Bash script, 50 lines, 3038 bytes).
- sha256 of the source when this page was built: `6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254`.
- Role in the whole-chip test: Part A runner: 24 processes of bw_old and bw_new with 120 threads.
- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.

## Short version: purpose

`ra.sh` repeats the 120-thread part of the test of 2026-11-13 with the binaries `bw_old` and `bw_new` of that day: 24 processes, one per binary, kernel and round, each with 120 threads on CPUs 0 to 119. It builds nothing, and it writes the rows that the binaries print to `threads120.csv` and the machine state to `probe.txt` in a new result folder.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **Machine code, listing**: the instructions that the compiler produced for a function. The listing is their text form. run_kernels.sh wrote it to its own `probe.txt` on 2026-11-13 [Ref1].
- **Loop pass**: one execution of the body of a loop.
- **write, copy, asmwrite, asmcopy**: the four other kernels of bw_old and bw_new. `write` fills a buffer. `copy` copies one buffer to a second buffer. `asmwrite` and `asmcopy` are hand-written loops for the same two jobs. They are not read kernels.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Session**: one pass of go.sh through part A, part L and part C.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **Part L**: one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.
- **Part C**: one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).
- **go.sh**: the driver script of the rerun of 2026-11-17. It calls ra.sh once per session.
- **run_kernels.sh**: the script of 2026-11-13. It built bw_old and bw_new and ran the test for the first time.
- **gcc**: the GNU C compiler. run_kernels.sh built bw_old and bw_new with it [Ref7].
- **Self-test**: the program `selftest`. run_kernels.sh builds it and runs it before its timed processes [Ref7]. It checks what the kernels of the new source do to memory [Ref10].
- **rx.sh**: the script that starts the bwx12 processes of part L and part C.
- **stat_k120.py**: an analysis script that reads threads120.csv.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test [Ref8]. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **Boot id**: a random identifier that Linux creates at each start. Equal boot ids mean the same boot.
- **MemTotal**: the usable memory that Linux reports, in kB.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Whole-pass stop**: the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. The benchmark does it before any timing, so that a timed interval holds no page fault.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **GB, MiB**: GB = 1e9 bytes. MiB = 2^20 bytes. The argument `256M` means 256 MiB = 268435456 bytes.
- **Exit status**: the number that a program returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time. The scripts write every time in UTC.
- **taskset**: a Linux tool that starts a command with a limit on the CPUs that the command may use.

</details>

## Main flow

1. Set the shell options that stop the script at a failed command and at an unset variable. Then restart the script under `taskset -c 0-119`. The script and every process that it starts may then use CPUs 0 to 119 only (lines 8-9).
2. Read the argument `NAME` (`T72A1`, `T72A2` or `T72A3` in go.sh). Stop if the marker file exists (lines 10-13).
3. Compare the sha256 of `bw_old` and `bw_new` with the values of 2026-11-13. Stop on a difference (lines 14-20).
4. Create the result folder `k120-NAME-TIME` (`TIME` is the UTC time) (lines 21-23).
5. Wait until at most 2 tasks are runnable (at most 40 readings, 1 s apart), then 5 s more. Stop if more than 2 tasks stay runnable. After the wait, check the marker file again (lines 25-29).
6. Write host, time, load averages, boot id, `MemTotal`, Linux kernel release, the 5 processes with the highest %CPU and the checksums to `probe.txt` (lines 30-36).
7. Round 1, 12 processes: for each kernel in the order `read`, `write`, `copy`, `asmread`, `asmwrite`, `asmcopy`, first `bw_old`, then `bw_new`. Each process appends its rows to `threads120.csv` (lines 37-48).
8. Round 2, 12 processes: the same processes in the exact reverse order. The last two are `bw_new` with `read`, then `bw_old` with `read` (lines 45-48).
9. Append the load averages after the last process to `probe.txt` and print the result folder (lines 49-50).

## Behavior a reader must know

- Nothing in this script runs inside a timed interval. The script starts a binary and waits for it. The clock reads, the pinning of the threads and the buffers are in the binary [Ref2].
- What one process does with its arguments [Ref2]: each of the 120 threads first pins itself to one CPU (thread number i to CPU i). Then it allocates its own buffer of 256 MiB and asks Linux for huge pages for it (`madvise` with `MADV_HUGEPAGE`). Then it writes its whole buffer once before any timing (first touch). It writes with `k_write`, the function of the kernel `write` of the same binary. For `copy` and `asmcopy` each thread has a second buffer of the same size.
- Timing inside one process [Ref2]: before each of the 3 intervals every thread runs the kernel once over its buffer without timing. Then all threads start together. A thread reads the clock at its start and after each whole pass over its buffer. It stops when 0.5 s or more have passed. So the threads stop at different times (whole-pass stop).
- The rate [Ref2]: the binary prints one row per interval. For `read` and `asmread` a thread counts 268435456 bytes per pass over its buffer. It counts the same number for `write` and `asmwrite`. For `copy` and `asmcopy` it counts twice that number: the bytes that it read plus the bytes that it wrote. The column `aggregate_GBps` is the sum of the bytes of all threads, divided by the longest elapsed time of any thread, in GB/s. Each process also prints a comment line, a title line and one `best` row with the highest of its 3 rates.
- Machine code of the two read kernels, from the listing of 2026-11-13 [Ref1]: one loop pass of the old read kernel in `bw_old` has 4 `ldp q` loads (128 bytes) and 8 vector `add` instructions that add the loaded values to the running sums. One loop pass of the new read kernel in `bw_new` has 8 `ldp q` loads (256 bytes) and no instruction that uses the loaded values. The listing agrees with the comment on lines 4 and 5 of ra.sh: 8 vector registers hold the 16 running sums of the old read kernel, and the new read kernel has loads only.
- Order of the processes: one process holds one kernel of one binary. So no kernel is timed after another kernel in the same process. But the processes follow each other without a wait. In round 1 the old read kernel is process 1 and the new read kernel is process 2. In round 2 the new read kernel is process 23 and the old read kernel is process 24.
- The wait of lines 26 to 28 uses the number of tasks that are runnable at that moment. It does not use the load average. In sessions 2 and 3 the 1-minute load average after the wait was 98.64 and 102.96, and `probe.txt` records `runnable=2` [Ref3].
- The 1-minute load average is higher at the last process of a session than at the first process. The line that starts with `-- ` records it at the start of each process. It was 0.07 for process 1 and 77.06 for process 24 in session 1, 98.64 and 112.71 in session 2, and 102.96 and 111.98 in session 3 [Ref3]. It does not rise at every process. In session 3 it fell from 105.51 at process 5 to 98.02 at process 6 [Ref3].
- The marker file is checked before each process and not while a process runs. In the three sessions the start of a process came 2 s to 5 s after the start of the process before it [Ref3]. These start times have a resolution of 1 s. rx.sh checks the file every second while a process runs. When the file exists, rx.sh stops that process [Ref5].
- The script can stop early. Status 1: no `NAME`. Status 2: a binary is not the one of 2026-11-13, or cannot be read. Status 3: the marker file exists. Status 6: more than 2 tasks are runnable after 40 readings. A benchmark process that fails stops the script with its own status. go.sh stops the whole run when ra.sh ends with a status other than 0 [Ref4].
- The main differences between ra.sh and the 120-thread part of run_kernels.sh: ra.sh builds nothing and runs no self-test. It checks the checksums of the binaries. It waits before the first process, and it runs no one-thread process before the 120-thread processes. It records the boot id, `MemTotal`, the Linux kernel release and the runnable tasks. It does not record the gcc version and the compiler flags. The function `one`, the two kernel lists and the loop have the same text in both scripts [Ref7].
- The local file is the script that ran. Its sha256 (6d67715e...) equals the value that `probe.txt` records in all three sessions [Ref3].
- The records show two texts of the new source `bandwidth.c`. The local file has the sha256 f1985072... [Ref2]. The timed run of 2026-11-13 recorded the sha256 c1406e02... for `bandwidth.c` in its `probe.txt` [Ref1]. All three `probe.txt` files that run_kernels.sh wrote on that day record the same sha256 for `bw_new` (fd7c14df...) [Ref1] [Ref9]. ra.sh checks this value. So the machine code is not in doubt. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref11]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- The binaries `bw_old` and `bw_new` are not in the local folders. Their sha256 values are known only from records such as lines 17 and 18 of ra.sh and the `probe.txt` files [Ref1] [Ref3] [Ref9].

## Call sequence in the whole-chip test

- `ra.sh NAME` (line 1): go.sh calls it once per session with NAME T72A1, T72A2 or T72A3
  - `taskset -c 0-119 ra.sh NAME` (line 9): restart of the script, limited to CPUs 0 to 119
  - `check_marker` (line 12): stop with status 3 if the marker file exists
  - `sha256sum -c` (line 16): compare bw_old and bw_new with the checksums of 2026-11-13
  - `load` (line 24): print the three load averages for probe.txt
  - `one` (line 39): 24 calls: bw_old and bw_new in turn per kernel. Round 2: reverse order
    - `check_marker` (line 12): before every process
    - `bandwidth.orig.c:main`: binary bw_old: 12 of the 24 processes, one kernel each
      - `bandwidth.orig.c:worker`: one of 120 threads: pins, allocates, times the kernel
        - `bandwidth.orig.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.orig.c:alloc_buf`: 256 MiB buffer of the thread, with a request for huge pages
        - `bandwidth.orig.c:k_write`: first touch: writes the whole buffer once, before any timing
        - `bandwidth.orig.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.orig.c:k_read`: old read kernel (kernel name read)
          - `bandwidth.orig.c:k_asmread`: hand-written load-only loop (kernel name asmread)
          - `bandwidth.orig.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels, one process each per round
    - `bandwidth.c:main`: binary bw_new: 12 of the 24 processes, one kernel each
      - `bandwidth.c:worker`: one of 120 threads: pins, allocates, times the kernel
        - `bandwidth.c:pin_cpu`: pin the thread to its CPU
        - `bandwidth.c:alloc_buf`: 256 MiB buffer of the thread, with a request for huge pages
        - `bandwidth.c:k_write`: first touch: writes the whole buffer once, before any timing
        - `bandwidth.c:pass`: one pass of the chosen kernel over the buffer
          - `bandwidth.c:k_read`: new read kernel (kernel name read)
          - `bandwidth.c:k_asmread`: same hand-written loop as in bw_old (kernel name asmread)
          - `bandwidth.c:k_write, k_copy, k_asmwrite, k_asmcopy`: the four other kernels, one process each per round

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 12-12 | Ends the script with status 3 when the marker file exists. | - | no |
| `load` | 24-24 | Prints the load averages of the last 1, 5 and 15 minutes. | - | no |
| `one` | 39-43 | Writes the `-- ` line, starts one benchmark binary with one kernel and waits for it. The timed intervals run inside that binary. | `check_marker`, `bw_old or bw_new` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `w120-7200-2026-11-17/ra.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (58 lines, 3585 bytes, sha256 `0324bab14b14769137bb6a606a9aa4982dd278551c0026c64c008dd71002eec9`).
- The other sections of this page describe an older text of the file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh` (50 lines, sha256 `6d67715e69d5d1fc020aa4ef4b22e7a12c11d771457513ffd7d6d38553626254`). Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

Line numbers of the older text and of the text shown here:

| Older text | Text shown here | Change |
|---|---|---|
| lines 1 to 7 | lines 1 to 7 | equal |
| (none) | line 8 | added |
| lines 8 to 11 | lines 9 to 12 | equal |
| (none) | lines 13 to 14 | added |
| lines 12 to 23 | lines 15 to 26 | equal |
| (none) | line 27 | added |
| lines 24 to 33 | lines 28 to 37 | equal |
| (none) | line 38 | added |
| lines 34 to 40 | lines 39 to 45 | equal |
| (none) | line 46 | added |
| lines 41 to 42 | lines 47 to 48 | equal |
| (none) | line 49 | added |
| lines 43 to 48 | lines 50 to 55 | equal |
| (none) | line 56 | added |
| lines 49 to 50 | lines 57 to 58 | equal |

### Header comment (lines 1 to 8)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# ra.sh NAME - rerun of the 120-thread part of run_kernels.sh (2026-11-13).` | Comment: the usage and the purpose. The script takes one argument, a name. It repeats the 120-thread part of the script `run_kernels.sh` of 2026-11-13. |
| 3 | `# It uses the SAME two binaries as that run (sha256 checked) and builds nothing.` | Comment: the script uses the same two binaries as that run and builds nothing. It checks their sha256 (lines 19 to 23). |
| 4 | `# bw_old = bandwidth.orig.c (read kernel: portable C, 16 running sums, load + add).` | Comment: the binary `bw_old` was built from the source `bandwidth.orig.c`. It holds the old read kernel: portable C code with 16 running sums. Each load is followed by an add. |
| 5 | `# bw_new = bandwidth.c      (read kernel: NEON intrinsics, loads only).` | Comment: the binary `bw_new` was built from the source `bandwidth.c`. It holds the new read kernel: NEON intrinsics (C functions that map to Arm vector instructions), loads only. |
| 6 | `# Process arguments, kernel order and round order are those of run_kernels.sh.` | Comment: the arguments of each process, the order of the kernels and the order of the rounds are those of `run_kernels.sh`. In the present texts of the two scripts, the function `one`, the two kernel lists and the 120-thread loop differ in one line only: the label that `hw_begin` gets (line 46). |
| 7 | `# Writes only under $HOME/cache-perf/results. Uses CPUs 0-119 only. No sudo.` | Comment: the script writes only below `$HOME/cache-perf/results`, uses the CPUs 0 to 119 only and needs no root rights. `sudo` is the tool that runs a command as root. The text of 2026-11-24 has one exception to the first point. When the function `hw_check` of `hw.sh` runs its tests, it makes a temporary folder and removes it again. The folder lies below `/tmp`, or below the folder that the variable `TMPDIR` names. |
| 8 | `# hw.sh records the clock rate, the throttle flags and the power in OUT/hw (HW=off: no such record; exit status 7: it is not usable).` | Comment: the file `hw.sh` records the clock rate of the cores, the throttle flags and the power in the folder `hw` of the result folder. This is the hardware record. A throttle flag is set by the firmware when a thermal, power or current limit made a core deliver less than Linux requested. With `HW=off` no such record is made. The script ends with exit status 7 when the record is not usable. |

### Shell options, restart on the CPUs 0 to 119, settings and the first marker check (lines 9 to 16)

| Line | Source | Explanation |
|---:|---|---|
| 9 | `set -euo pipefail` | Sets three shell options. `-e`: the script stops at the first command that fails (exit status not 0). A failing command inside an `if` test or in front of `\|\|` does not stop it. `-u`: the script stops when it uses a variable that was never set. `-o pipefail`: a pipeline (commands joined with `\|`) counts as failed when any command of it fails, not only the last one. |
| 10 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Restart on the CPUs 0 to 119. The script starts itself again under `taskset -c 0-119`, with the same arguments (`"$0" "$@"`). This tool limits a command to the CPUs 0 to 119. `exec` replaces the running shell with that command. No extra process is created. `_PINNED=1` is set for the new start. The test `-z ${_PINNED:-}` (is the variable empty or not set?) is then false. So the restart happens only once. Every process that the script starts later inherits the CPU limit. The benchmark binaries are among them. |
| 11 | `NAME=${1:?usage: ra.sh NAME}` | `NAME` is the first argument. If it is missing or empty, `bash` prints `usage: ra.sh NAME` and the script ends with status 1. `NAME` becomes part of the name of the result folder (line 25). `go.sh` passes `T72A1`, `T72A2` and `T72A3`, one per session [Ref4]. |
| 12 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. |
| 13 | `HWDIR=${HWDIR:-$HOME/cache-perf/hwwatch-20261124}` | `HWDIR`: the folder that holds `hw.sh`. When the caller has set the variable `HWDIR` to a value that is not empty, that value is kept. If not, the folder is `$HOME/cache-perf/hwwatch-20261124`. |
| 14 | `if [[ ${HW:-on} == off ]]; then hw_init() { :; }; hw_begin() { :; }; hw_end() { :; }; hw_done() { :; }; else . "$HWDIR/hw.sh" \|\| { echo "cannot read $HWDIR/hw.sh: stop" >&2; exit 7; }; fi` | Chooses the hardware record. When the variable `HW` is `off`, the line defines four functions that do nothing: `hw_init`, `hw_begin`, `hw_end` and `hw_done`. The command `:` does nothing and succeeds. In every other case the line reads the file `hw.sh` into this shell (the command `.`). That file defines the real functions. When `hw.sh` cannot be read, the script prints a message that starts with `cannot read` to the error output (`>&2`) and ends with exit status 7. |
| 15 | `check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }` | Defines the function `check_marker`. It tests whether the marker file exists (`-e`). If it exists, the function prints `RUNNING file present: stop` to the error output and ends the script with status 3. |
| 16 | `check_marker` | First call of `check_marker` (line 15). The script has written no file at this point. |

### Check that the binaries are those of 2026-11-13 (lines 17 to 23)

| Line | Source | Explanation |
|---:|---|---|
| 17 | `SRC=$HOME/cache-perf/scratch-kernels-20261113` | `SRC`: the folder on CRB that holds `bw_old` and `bw_new`. |
| 18 | `# sha256 of the binaries as recorded in results/kernels-20261113T181222Z/probe.txt` | Comment: the two checksums of lines 20 to 21 are the sha256 values of the binaries as the file `probe.txt` of the result folder `kernels-20261113T181222Z` recorded them. The two checksums equal the values that `run_kernels.sh` recorded for the binaries on 2026-11-13 [Ref1]. |
| 19 | `(cd "$SRC" && sha256sum -c - > /dev/null <<'SUMS'` | Starts the checksum check of the two binaries. The parentheses run `cd` and the check in a subshell (a child copy of the shell). So the working folder of the script itself does not change. `sha256sum -c -` reads the two lines between `<<'SUMS'` and `SUMS` (lines 20 to 21). Each line holds a checksum and a file name. The tool computes the sha256 of each file and compares it with the given value. `> /dev/null` drops the report of the tool. Only its exit status is used. |
| 20 | `e8fc0205f2a5b9eb3e9fe10483b0d5c42eab55a586a6d7baabdfa758a8069dfa  bw_old` | Input line of the check: the sha256 that the file `bw_old` must have, then the file name. |
| 21 | `fd7c14df3afe442f08a0f545b1e8b0a2f8afe4b85d1aec1b1e26d3944fd888a6  bw_new` | Input line of the check: the sha256 that the file `bw_new` must have, then the file name. |
| 22 | `SUMS` | The word `SUMS` ends the input text that started in line 19. |
| 23 | `) \|\| { echo "sha mismatch: bw_old or bw_new is not the binary of 2026-11-13" >&2; exit 2; }` | Ends the subshell of line 19. If a file differs or cannot be read, or if `cd` fails, the part after `\|\|` runs: the script prints `sha mismatch: bw_old or bw_new is not the binary of 2026-11-13` to the error output and ends with status 2. |

### Result folder and start of the hardware record (lines 24 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 24 | `TS=$(date -u +%Y%m%dT%H%M%SZ)` | `TS`: the UTC time of this moment (`date -u`), written as date, `T`, time, `Z`. In session 1 it was `20261117T221209Z` [Ref3]. The time is read before the wait of lines 30 to 32. So the first process starts at least 5 s after the time in the folder name. |
| 25 | `OUT=$HOME/cache-perf/results/k120-$NAME-$TS` | `OUT`: the result folder. Its name is `k120-`, then `NAME`, then `-` and `TS`, below `$HOME/cache-perf/results`. |
| 26 | `mkdir -p "$OUT"` | `mkdir -p` creates the result folder, with its parent folders when they are missing. |
| 27 | `hw_init "$OUT" \|\| { echo "hardware record not usable: stop" >&2; exit 7; }` | Starts the hardware record for the result folder. `hw_init` first tests the tools (function `hw_check` of `hw.sh`). Then it writes the files `status.txt` and `probe.txt` in the folder `hw` of the result folder. Then it starts two background programs. The first is the frequency sampler (`hwwatch.py watch`, one sample per second unless `HW_PERIOD_S` says otherwise). The second is the vendor tool `atx` (Arm Telemetrix), which reads power, temperature and frequency values of the firmware. `atx` is started only when `HW_POWER` is `require`. Both are pinned to CPU 119 unless `HW_CPU` says otherwise, and line 56 stops them. So during the timed intervals they share CPU 119 with one benchmark thread. `hw_init` also sets a trap that calls `hw_done` when the shell of the script ends. When `hw_init` fails, the script prints `hardware record not usable: stop` to the error output and ends with exit status 7. With `HW=off` the call does nothing (line 14). |

### Wait until at most 2 tasks are runnable (lines 28 to 33)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `load() { cut -d' ' -f1-3 /proc/loadavg; }` | Defines the function `load`. It prints the first three fields of `/proc/loadavg` (`cut -d' ' -f1-3`: split the line at spaces and keep fields 1 to 3). They are the load averages over the last 1, 5 and 15 minutes. |
| 29 | `# Before the first process: wait until at most 2 tasks are runnable, then 5 s (rule of rx.sh).` | Comment: before the first process the script waits until at most 2 tasks are runnable, and then 5 s more. By the comment this is the rule of `rx.sh`. This wait runs once, before the first of the 24 processes. `rx.sh` has the same loop and the same 5 s wait before every process, but not the stop of line 31 [Ref5]. |
| 30 | `for _ in $(seq 40); do r=$(cut -d' ' -f4 /proc/loadavg \| cut -d/ -f1); if [[ $r -le 2 ]]; then break; fi; sleep 1; done` | The loop runs at most 40 times. Each time it reads the fourth field of `/proc/loadavg`, which holds two numbers with a slash between them. The second `cut` keeps the number before the slash. This is `r`, the number of tasks that are runnable now. If `r` is 2 or less, `break` leaves the loop. If not, the script sleeps 1 s and reads again. Unless `HW` is `off`, the background programs that line 27 started are already running during this wait. |
| 31 | `if [[ $r -gt 2 ]]; then echo "not quiet: $r tasks runnable after 40 s: stop" >&2; exit 6; fi` | If `r` is still above 2 after the 40 readings, the script prints `not quiet: N tasks runnable after 40 s: stop` to the error output, where N is the value of `r`. Then it ends with status 6. |
| 32 | `sleep 5` | The script then always waits 5 s more. |
| 33 | `check_marker` | The marker file is checked again after the wait (`check_marker`, line 15). |

### Write the machine state to `probe.txt` (lines 34 to 41)

| Line | Source | Explanation |
|---:|---|---|
| 34 | `{` | Opens a group of commands. Line 41 closes the group and sends the output of all its commands to the file `probe.txt`. |
| 35 | `  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who \| wc -l) name=$NAME"` | First line of `probe.txt`: the host name, the UTC time, the load averages (function `load`, line 28) under the name `load_before`, the number of login sessions and `NAME`. `who` prints one line per login session, and `wc -l` counts the lines. The load averages are read here, after the wait of lines 30 to 32. |
| 36 | `  echo "## boot_id=$(cat /proc/sys/kernel/random/boot_id) $(grep MemTotal /proc/meminfo \| tr -s ' ') runnable=$r"` | Second line of `probe.txt`: the boot id, the `MemTotal` line of `/proc/meminfo` (`tr -s ' '` turns each run of spaces into one space) and the last value of `r` under the name `runnable`. The script read this value in the loop of line 30, before the 5 s wait. |
| 37 | `  echo "## kernel=$(uname -r) thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"` | Third line of `probe.txt`: the release of the Linux kernel (`uname -r`) and the setting for transparent huge pages. The value in square brackets is the active one. |
| 38 | `  echo "## hw=${HW:-on} hw_power=${HW_POWER:-require}"` | Fourth line of `probe.txt`: the two settings of the hardware record. The line shows `hw=on` and `hw_power=require` when the variables `HW` and `HW_POWER` are not set or are empty. |
| 39 | `  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6` | Writes a title line, then the busiest processes. `ps -eo pcpu,user,comm --sort=-pcpu` lists all processes with their %CPU, user and command name, highest %CPU first. `head -6` keeps the title line of `ps` and 5 processes. %CPU (`pcpu`) is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. |
| 40 | `  echo "## sha256:"; (cd "$SRC" && sha256sum bw_old bw_new); sha256sum "$0"` | Writes a title line, then the sha256 of `bw_old`, of `bw_new` and of this script (`$0`). The parentheses run `cd` and the first `sha256sum` in a subshell, so the working folder of the script does not change. |
| 41 | `} > "$OUT/probe.txt"` | Closes the group of line 34. `> "$OUT/probe.txt"` writes the output of all its commands to the new file `probe.txt` in the result folder. This file is not the file `probe.txt` of the hardware record, which lies in the folder `hw`. |

### Function `one`: start one benchmark process (lines 42 to 50)

| Line | Source | Explanation |
|---:|---|---|
| 42 | `# One process per (binary, kernel): no kernel is timed after another kernel` | Comment: each process runs one kernel of one binary. So no kernel is timed after another kernel in the same process. The sentence ends in line 43. |
| 43 | `# in the same process. Round 2 reverses the order of binaries and kernels.` | Comment, continued: round 2 runs the binaries and the kernels in the reverse order of round 1. |
| 44 | `one() { # csv binary kernel threads cpus bytes round` | Starts the function `one`. It starts one benchmark process and waits for it. Its arguments, in this order: csv file, binary, kernel, threads, CPU list, bytes, round. |
| 45 | `  check_marker` | Checks the marker file before every process (`check_marker`, line 15). Nothing checks it while a process runs. |
| 46 | `  hw_begin "$2-$3-r$7" "$5"` | Takes the first snapshot of the hardware record for this process. `hw_begin` gets a label and the CPU list. The label holds the binary, the kernel and the round, for example `bw_old-read-r1`. `hw_begin` gives the process a numbered label and writes a snapshot of these CPUs to a file `NNN-LABEL.before.txt` in the folder `hw`. By the comment in `hw.sh`, this call must stand before the quiet time of the launch. `ra.sh` has no pause between this call and the start of the binary in line 48. |
| 47 | `  echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$1"` | Appends one line that starts with `--` and a space to the csv file. It holds the arguments, the 1-minute load average at this moment and the UTC time (hours, minutes, seconds). `stat_k120.py` reads this line to know which rows belong to which process [Ref6]. |
| 48 | `  "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 >> "$1"` | Starts the binary with one kernel (`--kernel`) and waits until it ends. `>>` appends the rows that the binary prints to the csv file. `--reps 3`: the process times 3 intervals. `--min-ms 500`: each interval lasts at least 500 ms [Ref2]. If the binary ends with a status other than 0, `set -e` ends the script with that status. |
| 49 | `  hw_end` | Takes the second snapshot of the hardware record, after the process (file `NNN-LABEL.after.txt`). `hw_end` also tests that the sampler is still running, and `atx` too when `HW_POWER` is `require`. When a snapshot fails or a program is not running, `hw_end` adds a line that starts with `FAILED` to the file `status.txt` in the folder `hw`. It does not stop the script. |
| 50 | `}` | Ends the function `one`. |

### The 24 processes and the end (lines 51 to 58)

| Line | Source | Explanation |
|---:|---|---|
| 51 | `K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"` | `K1` is the kernel order of round 1. `K2` holds the same six names in the reverse order, for round 2. `read` and `asmread` are the read kernels, and the other four names are the write and copy kernels. A `for` loop over such a list takes the names one by one. |
| 52 | `for round in 1 2; do` | Starts the loop over the two rounds: `round` is 1, then 2. Each round runs 12 processes. All 24 processes append to one file, `threads120.csv`. No wait separates two processes. Only the first process (old `read`, round 1) starts directly after the wait of lines 30 to 32. Between two processes the script runs the snapshot of line 49, the marker check and the snapshot of lines 45 to 46, and the line of line 47. |
| 53 | `  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi` | Sets the order of the round. Round 1 (`BINS` holds old, then new, and `KS` is `K1`): for each kernel first `bw_old`, then `bw_new`. Order: old `read`, new `read`, old `write`, new `write`, old `copy`, new `copy`, old `asmread`, new `asmread`, old `asmwrite`, new `asmwrite`, old `asmcopy`, new `asmcopy`. Round 2 (`BINS` holds new, then old, and `KS` is `K2`): the exact reverse of round 1. Order: new `asmcopy`, old `asmcopy`, new `asmwrite`, old `asmwrite`, new `asmread`, old `asmread`, new `copy`, old `copy`, new `write`, old `write`, new `read`, old `read`. |
| 54 | `  for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done` | Two loops in one line: for each kernel of `KS` and for each binary of `BINS`, one call of `one` (line 44). Every process gets the same arguments: 120 threads and the CPU list `0-119`. The binary pins thread number i to CPU i. `256M` gives each thread its own buffer of 256 MiB. For the kernels `copy` and `asmcopy` each thread gets a second buffer of the same size. Each process times 3 intervals of at least 500 ms each [Ref2]. The new read kernel starts directly after the old read kernel in round 1. In round 2 it starts directly after `bw_old` with `write`, and the old read kernel is the last process. |
| 55 | `done` | Ends the loop over the rounds (line 52). |
| 56 | `hw_done` | Stops the hardware record. `hw_done` ends the sampler and `atx`, adds its last lines to `status.txt` and removes the trap of line 27. It waits at most 30 s for `atx` to end. |
| 57 | `echo "## load_after=$(load) utc=$(date -u +%FT%TZ) $(grep MemTotal /proc/meminfo \| tr -s ' ')" >> "$OUT/probe.txt"` | Appends a last line to `probe.txt`: the load averages under the name `load_after`, the UTC time and the `MemTotal` line. They are read after the last process and after the stop of the hardware record in line 56. |
| 58 | `echo "done $OUT"` | Prints `done` and the path of the result folder. It is the last command, so the script then ends with status 0. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Written by run_kernels.sh on 2026-11-13 at 18:12:22 UTC. Line 15 holds the sha256 of bandwidth.c: c1406e02.... Lines 19 and 20 hold the sha256 of bw_old and bw_new. They equal the values on lines 17 and 18 of ra.sh. From line 23 the file holds the machine code of the kernels of bw_new, and from line 155 the machine code of the kernels of bw_old.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c, /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: Sources of bw_old and bw_new. The functions `main`, `worker`, `pin_cpu`, `alloc_buf` and `pass` are the source for the statements on arguments, pinning, buffers, timing and the rate. The local bandwidth.orig.c has the sha256 on line 14 of Ref1. The local bandwidth.c has the sha256 f1985072.... The probe.txt in /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z records this sha256 (line 15) together with a bw_new that has the sha256 that ra.sh checks (line 20).
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A1-20261117T221209Z, /home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A2-20261117T221518Z, /home/jhan/workspace/titan/cache-perf/crb/results/k120-T72A3-20261117T221827Z`: Result folders of sessions 1, 2 and 3. In each `threads120.csv` the 24 lines that start with `-- ` give the process order, the load and the start time. In each `probe.txt` line 1 holds the load averages read after the wait (`load_before`), line 2 holds `runnable=2`, and line 14 holds the sha256 of ra.sh.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: Line 41 calls ra.sh once per session and stops the whole run when ra.sh ends with a status other than 0.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: Lines 14 and 15 hold the same wait loop and the 5 s wait, before every process and without a stop. Line 19 checks the marker file every second while a process runs.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Line 21 holds the pattern that reads the lines that start with `-- `.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: Line 29 runs gcc. Lines 31 to 33 build bw_old, bw_new and the program selftest with it. Line 55 runs selftest. Lines 58 to 65 and 75 to 78 have the same text as lines 37 to 48 of ra.sh (compared with diff).
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The facts sheet of the rerun of 2026-11-17. Line 77 (list "Words used here") says that another user creates the marker file during a performance test. The script itself does not say who creates the file.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181210Z/probe.txt, /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: The two other records that run_kernels.sh wrote on 2026-11-13, at 18:12:10 UTC and at 18:32:18 UTC. Both starts built the binaries and timed nothing. Line 15 holds the sha256 of bandwidth.c: c1406e02... in the first file and f1985072... in the second file. Lines 19 and 20 hold the sha256 of bw_old and bw_new. Both files give the same two values as Ref1.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c`: Source of the program selftest. Line 2 says that the program checks what the six kernels of bandwidth.c do to memory. Line 16 includes bandwidth.c, the new source.
- [Ref11] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
