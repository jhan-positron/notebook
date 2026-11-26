# `run_kernels.sh` explained

- Source file: `kernels-2026-11-13/run_kernels.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 89 lines, 4792 bytes).
- sha256 of the source when this page was built: `69d1dcfd1f72be49655797d1ebbc177d8a1c55e5ba58c11c2193aedfaa13ccf9`.
- Role in the whole-chip test: Script of 2026-11-13 that built bw_old and bw_new and ran the first test.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

`run_kernels.sh` compiles the old benchmark source `bandwidth.orig.c` into the binary `bw_old` and the new source `bandwidth.c` into `bw_new`, writes the machine code of every kernel to `probe.txt`, and runs a self-test. In mode `all` it then times every kernel of both binaries, first with 1 thread and then with 120 threads on CPUs 0 to 119.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Whole chip, 120 threads, 64+56**: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Read kernel**: the inner loop of the benchmark that reads memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **write, copy, asmwrite, asmcopy**: the four other kernels of bw_old and bw_new. `write` fills a buffer. `copy` copies one buffer to a second buffer. `asmwrite` and `asmcopy` are hand-written loops for the same two jobs. They are not read kernels.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **Process, interval, round, position**: a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.
- **Part A**: the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.
- **ra.sh**: the script of the rerun of 2026-11-17 that runs part A. It uses the binaries that run_kernels.sh built.
- **go.sh**: the driver script of the rerun of 2026-11-17. It calls ra.sh.
- **stat_k120.py**: an analysis script that reads threads120.csv.
- **gcc**: the GNU C compiler.
- **objdump**: a tool that prints the machine code of a binary as assembler text.
- **Machine code, listing**: the instructions that the compiler produced for a function. The listing is their text form in probe.txt.
- **Loop pass**: one execution of the body of a loop.
- **NEON**: the Arm vector instructions with 16-byte registers. The listing writes these registers as `q` or `v` with a number.
- **SVE**: the Scalable Vector Extension, another set of Arm vector instructions. The listing writes its registers as `z` or `p` with a number.
- **SVE2**: the Scalable Vector Extension 2, a further set of Arm vector instructions. The record of 2026-11-11 names four SVE2 extensions [Ref13]. The gcc manual says that each of them also turns on SVE2, and that SVE2 also turns on the SVE instructions [Ref12].
- **Stack check**: code that the compiler adds to a function. At entry the function copies a guard value to its stack frame. Before it returns it compares the copy with the guard value. On a difference it calls `__stack_chk_fail`.
- **Self-test**: the program `selftest`. It checks what the kernels do to memory. Exit status 0 means that every check passed.
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test [Ref11]. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **%CPU**: the column pcpu of the tool ps. It is the CPU time that a process has used, divided by the time since the process started. So it is an average over the life of the process. It is not the use at the moment of the reading.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **GB, KiB, MiB, GiB**: GB = 1e9 bytes. KiB = 2^10 bytes, MiB = 2^20 bytes, GiB = 2^30 bytes. The size arguments `32K`, `1M`, `8M`, `256M` and `1G` use the binary units: `256M` means 256 MiB = 268435456 bytes.
- **Exit status**: the number that a program returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time. The scripts write every time in UTC.
- **taskset**: a Linux tool that starts a command with a limit on the CPUs that the command may use.

</details>

## Main flow

1. Set the shell options that stop the script at a failed command and at an unset variable. Then restart the script under `taskset -c 0-119`. The script and every process that it starts may then use CPUs 0 to 119 only (lines 8-9).
2. Read the mode (`probe` or `all`). Stop if the marker file exists (lines 10-14).
3. Find the script folder and create the result folder `kernels-TIME` (`TIME` is the UTC time) (lines 15-18).
4. Set the compiler flags. Write host, time, load averages, gcc version and flags to `probe.txt` (lines 19-27).
5. Build `bw_old`, `bw_new`, `selftest` and `probe.o` with the same flags. Stop if a build fails (lines 28-35).
6. Append the checksums of sources and binaries and the machine code of the six kernels of each binary to `probe.txt` (lines 36-53).
7. Run the self-test. Stop with status 4 if it fails (lines 54-55).
8. Mode `probe` ends here (line 56).
9. Mode `all`: run 192 processes with 1 thread each, on CPU 0 and on CPU 2, with four buffer sizes. Their rows go to `one-thread.csv` (lines 58-74).
10. Mode `all`: run 24 processes with 120 threads each. Their rows go to `threads120.csv`. This is the part that ra.sh repeats (lines 75-78).
11. Append the load averages after the last process to `probe.txt` and print the result folder (lines 79-80).

## Behavior a reader must know

- The rerun of 2026-11-17 did not start this script. go.sh calls ra.sh, and ra.sh uses the binaries `bw_old` and `bw_new` that this script built on CRB on 2026-11-13 [Ref8].
- Every start of the script builds the binaries again. Three result folders of this script exist from 2026-11-13. Their starts were at 18:12:10 UTC (mode `probe`) [Ref4], at 18:12:22 UTC (mode `all`) [Ref1] and at 18:32:18 UTC (mode `probe`) [Ref5]. All three `probe.txt` files record the same sha256 for `bw_old` (e8fc0205...) and the same sha256 for `bw_new` (fd7c14df...) [Ref1] [Ref4] [Ref5]. ra.sh checks these two values [Ref8].
- The new source changed between the starts. `bandwidth.c` had the sha256 c1406e02... at 18:12:10 UTC and at 18:12:22 UTC, and f1985072... at 18:32:18 UTC [Ref4] [Ref1] [Ref5]. The sha256 of `bw_new` and the machine code of the kernels in `probe.txt` did not change [Ref1] [Ref5]. The local `bandwidth.c` has the sha256 f1985072... [Ref3]. The two texts differ in comment lines only. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref14]. With this edit reversed, the local text has the sha256 value of the earlier text (c1406e02...). No code line differs.
- Compiler result for the read kernels, from the listing [Ref1]: gcc turned the 16 sums of the old `k_read` into 8 vector registers with 2 sums each. One loop pass of the old `k_read` in `bw_old` has 4 `ldp q` loads (128 bytes) and 8 vector `add` instructions that add the loaded values to the sums. One loop pass of the new `k_read` in `bw_new` has 8 `ldp q` loads (256 bytes) and no instruction that uses the loaded values.
- Compiler result for the instruction sets, from the listing [Ref1]: the old `k_write` and `k_copy` in `bw_old` use SVE instructions (`whilelo`, `st1d`, `ld1d`). `-march=native` is the only flag of line 19 that sets the target architecture. The architecture decides which instructions gcc may use [Ref12]. A record from CRB of 2026-11-11 shows what the same gcc version picked for `native`: the architecture name `armv8-a` with 16 extensions (sets of extra instructions), among them four SVE2 extensions [Ref13]. The ten other kernel listings of the two binaries hold no SVE instruction.
- Compiler result for `-fno-tree-loop-distribute-patterns`, from the listing [Ref1]: no kernel calls `memset` or `memcpy`. The only call in the twelve kernel listings is the stack check of the old `k_read`.
- The old `k_read` in `bw_old` ends with a call to `__stack_chk_fail`, which belongs to a stack check. The instructions of the check sit before and after the loop, not inside it [Ref1]. No flag of line 19 asks for it. Insufficient data: the options that the gcc of CRB turns on without a flag. The output of `gcc -v` and of `gcc -Q --help=common -O3 -march=native` on CRB would resolve it.
- Source of the flag meanings on line 19: the help text of the local gcc 11.4.0 for x86-64 [Ref9]. The meaning of `-march=native` on an Arm machine comes from the public manual of gcc 14.2.0 [Ref12]. The value that gcc picked for `native` on CRB comes from a record of 2026-11-11, two days before the build [Ref13]. The `probe.txt` files of 2026-11-13 do not record this value. No manual page of gcc is installed on the local machine. CRB used gcc 14.2.0 [Ref1]. Insufficient data: the exact list of steps that `-O3` turns on in gcc 14.2.0 on CRB. The output of `gcc -Q --help=optimizers -O3` on CRB would resolve it.
- The self-test covers the new source only. `selftest.c` includes `bandwidth.c` [Ref6]. It does not check the kernels `read`, `write` and `copy` of the old source `bandwidth.orig.c`. The three hand-written kernels have the same source text in both files [Ref3].
- Order of the processes: one process holds one kernel of one binary. So no kernel is timed after another kernel in the same process. But the processes follow each other without a wait. On 2026-11-13 the 1-minute load average was 1.00 at the first 120-thread process and 85.38 at the last one [Ref2].
- What one 120-thread process does [Ref3]: each thread first pins itself to one CPU (thread number i to CPU i). Then it allocates its own buffer of 256 MiB, asks Linux for huge pages for it, and writes it once before any timing. It writes with `k_write`, the function of the kernel `write` of the same binary. For `copy` and `asmcopy` each thread has a second buffer of the same size. Before each of the 3 intervals every thread runs the kernel once over its buffer without timing. Then all threads start together. In each of the 3 intervals a thread reads the clock at its start and after each whole pass over its buffer. It stops when 0.5 s or more have passed.
- The rate [Ref3]: the binary prints one row per interval. Per pass over its buffer a thread counts the size of the buffer in bytes. For `copy` and `asmcopy` it counts twice that size: the bytes that it read plus the bytes that it wrote. The column `aggregate_GBps` is the sum of the bytes of all threads, divided by the longest elapsed time of any thread, in GB/s. Each process also prints a comment line, a title line and one `best` row with the highest of its 3 rates.
- The marker file is checked at the start, before the self-test and before each benchmark process. Nothing checks it while a process runs.
- The script can stop early. Status 2: unknown mode. Status 3: the marker file exists. Status 5: a build failed. Status 4: the self-test failed. A benchmark process that fails stops the script with its own status. Mode `probe` ends with status 0 after the self-test.
- The local file is the script that ran. Its sha256 (6a91bbbe...) equals the value that all three `probe.txt` files record [Ref1] [Ref4] [Ref5]. The local files `bandwidth.orig.c` (61228754...), `selftest.c` (90456a56...) and `probe.c` (81f96b39...) also have the sha256 values that all three files record [Ref1] [Ref4] [Ref5].
- The binaries `bw_old` and `bw_new` are not in the local folders. Their sha256 values are known only from records such as the three `probe.txt` files of this script [Ref1] [Ref4] [Ref5] and the two values that ra.sh checks [Ref8].

## Call sequence in the whole-chip test

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

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 13-13 | Ends the script with status 3 when the marker file exists. | - | no |
| `load` | 20-20 | Prints the load averages of the last 1, 5 and 15 minutes. | - | no |
| `build` | 29-29 | Runs gcc with the flags of line 19. Appends the compiler messages to build.txt. Ends the script with status 5 when gcc fails. | `gcc` | no |
| `one` | 60-64 | Writes the `-- ` line, starts one benchmark binary with one kernel and waits for it. The timed intervals run inside that binary. | `check_marker`, `bw_old or bw_new` | no |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `kernels-2026-11-13/run_kernels.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (89 lines, 4792 bytes, sha256 `69d1dcfd1f72be49655797d1ebbc177d8a1c55e5ba58c11c2193aedfaa13ccf9`).
- The other sections of this page describe an older text of the file: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh` (80 lines, sha256 `6a91bbbe799b9279f99c693f44ef5852d5daa437a7e2469bf61c914b40b81842`). Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

Line numbers of the older text and of the text shown here:

| Older text | Text shown here | Change |
|---|---|---|
| lines 1 to 7 | lines 1 to 7 | equal |
| (none) | lines 8 to 9 | added |
| lines 8 to 11 | lines 10 to 13 | equal |
| (none) | lines 14 to 15 | added |
| lines 12 to 56 | lines 16 to 60 | equal |
| (none) | lines 61 to 62 | added |
| lines 57 to 61 | lines 63 to 67 | equal |
| (none) | line 68 | added |
| lines 62 to 63 | lines 69 to 70 | equal |
| (none) | line 71 | added |
| lines 64 to 78 | lines 72 to 86 | equal |
| (none) | line 87 | added |
| lines 79 to 80 | lines 88 to 89 | equal |

### Header comment: the two modes (lines 1 to 9)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_kernels.sh - on CRB: build the old and the new bandwidth.c, print the` | Comment: the purpose. On CRB the script builds the old and the new `bandwidth.c` and prints the machine code of the kernels. The sentence ends in line 3. |
| 3 | `# machine code of the kernels, run the self-test, then time old and new.` | Comment, continued: then the script runs the self-test and times the old and the new binary. |
| 4 | `# Usage: run_kernels.sh probe \| all` | Comment: the usage. The script takes one argument, the mode: `probe` or `all`. |
| 5 | `#   probe: build, machine code and self-test only (no timing)` | Comment: mode `probe` builds the binaries, prints the machine code of the kernels and runs the self-test. It times nothing. |
| 6 | `#   all:   probe, then the timed runs` | Comment: mode `all` does the same and then runs the timed processes. The timed run of 2026-11-13 used `all` [Ref1]. |
| 7 | `# Writes only under $HOME/cache-perf. Uses CPUs 0-119 only. No sudo.` | Comment: the script writes only below `$HOME/cache-perf`, uses the CPUs 0 to 119 only and needs no root rights. `sudo` is the tool that runs a command as root. The first point depends on the place of the script: the binaries are written to the folder that holds the script (line 19). The text of 2026-11-24 has one more exception. When the function `hw_check` of `hw.sh` runs its tests, it makes a temporary folder and removes it again. That folder lies below `/tmp`, or below the folder that the variable `TMPDIR` names. |
| 8 | `# Mode all: hw.sh records the clock rate, the throttle flags and the power in OUT/hw` | Comment: in mode `all` the file `hw.sh` records the clock rate of the cores, the throttle flags and the power in the folder `hw` of the result folder. This is the hardware record. A throttle flag is set by the firmware when a thermal, power or current limit made a core deliver less than Linux requested. |
| 9 | `# (HW=off: no such record; exit status 7: it is not usable).` | Comment, continued: with `HW=off` no such record is made. The script ends with exit status 7 when the record is not usable. |

### Shell options, restart on the CPUs 0 to 119, mode, hardware record, marker check (lines 10 to 18)

| Line | Source | Explanation |
|---:|---|---|
| 10 | `set -euo pipefail` | Sets three shell options. `-e`: the script stops at the first command that fails (exit status not 0). A failing command inside an `if` test or in front of `\|\|` does not stop it. `-u`: the script stops when it uses a variable that was never set. `-o pipefail`: a pipeline (commands joined with `\|`) counts as failed when any command of it fails, not only the last one. |
| 11 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Restart on the CPUs 0 to 119. The script starts itself again under `taskset -c 0-119`, with the same arguments (`"$0" "$@"`). This tool limits a command to the CPUs 0 to 119. `exec` replaces the running shell with that command. No extra process is created. `_PINNED=1` is set for the new start. The test `-z ${_PINNED:-}` (is the variable empty or not set?) is then false. So the restart happens only once. Every process that the script starts later inherits the CPU limit. The compiler, the self-test and the benchmark binaries are among them. |
| 12 | `MODE=${1:-probe}` | `MODE` is the first argument. Without an argument it is `probe`. |
| 13 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. |
| 14 | `HWDIR=${HWDIR:-$HOME/cache-perf/hwwatch-20261124}` | `HWDIR`: the folder that holds `hw.sh`. When the caller has set the variable `HWDIR` to a value that is not empty, that value is kept. If not, the folder is `$HOME/cache-perf/hwwatch-20261124`. |
| 15 | `if [[ ${HW:-on} == off \|\| $MODE != all ]]; then hw_init() { :; }; hw_begin() { :; }; hw_end() { :; }; hw_done() { :; }; else . "$HWDIR/hw.sh" \|\| { echo "cannot read $HWDIR/hw.sh: stop" >&2; exit 7; }; fi` | Chooses the hardware record. When the variable `HW` is `off` or the mode is not `all`, the line defines four functions that do nothing: `hw_init`, `hw_begin`, `hw_end` and `hw_done`. The command `:` does nothing and succeeds. In every other case the line reads the file `hw.sh` into this shell (the command `.`). That file defines the real functions. When `hw.sh` cannot be read, the script prints a message that starts with `cannot read` to the error output (`>&2`) and ends with exit status 7. |
| 16 | `case $MODE in probe\|all) ;; *) echo "usage: $0 probe\|all" >&2; exit 2;; esac` | The `case` accepts `probe` and `all`. Any other word prints the usage text `usage: $0 probe\|all` to the error output and ends the script with status 2. `$0` is the path of the script. |
| 17 | `check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }` | Defines the function `check_marker`. It tests whether the marker file exists (`-e`). If it exists, the function prints `RUNNING file present: stop` to the error output and ends the script with status 3. |
| 18 | `check_marker` | First call of `check_marker` (line 17). The script has written no file at this point. |

### Folders, compiler flags and the function `load` (lines 19 to 24)

| Line | Source | Explanation |
|---:|---|---|
| 19 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC` is the absolute path of the folder that holds this script. `dirname "$0"` gives the folder part of the script path. `cd` and `pwd` turn it into an absolute path. The sources are read from `SRC` and the binaries are written to `SRC`. |
| 20 | `TS=$(date -u +%Y%m%dT%H%M%SZ)` | `TS`: the UTC time of this moment (`date -u`), written as date, `T`, time, `Z`. |
| 21 | `OUT=$HOME/cache-perf/results/kernels-$TS` | `OUT`: a new result folder, `kernels-` plus `TS`, below `$HOME/cache-perf/results`. |
| 22 | `mkdir -p "$OUT"` | `mkdir -p` creates the result folder, with its parent folders when they are missing. |
| 23 | `CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"` | `CFLAGS`: the seven flags of every `gcc` call of line 33. `-O3`: optimization level 3, the highest numbered level of gcc. At this level gcc may turn a scalar loop into a vector loop. `-march=native`: the target architecture is that of the machine that compiles, here CRB. The architecture decides which instructions gcc may use [Ref12]. A record from CRB of 2026-11-11 shows what the same gcc version picked for `native`: the architecture name `armv8-a` with 16 extensions (sets of extra instructions), among them four SVE2 extensions [Ref13]. The listing shows one case: two kernels of `bw_old` use SVE instructions [Ref1]. The line has no `-mtune` and no `-mcpu` flag. For this case the gcc manual says that the code is tuned for a range of processors that implement the architecture [Ref12]. `-fno-tree-loop-distribute-patterns`: turns off one step that `-O3` would run. That step replaces a loop pattern with a call to a library function, for example a copy loop with `memcpy`. With the flag, gcc does not replace a kernel loop with such a call. `-pthread`: compile and link with support for POSIX threads (the standard thread interface of Unix systems). The benchmark creates its threads with `pthread_create`. `-Wall`: turn on most warning messages. `-Wextra`: turn on some extra warnings. A warning does not change the machine code. `-std=gnu11`: the language is C of the 2011 standard with the GNU extensions. |
| 24 | `load() { cut -d' ' -f1-3 /proc/loadavg; }` | Defines the function `load`. It prints the first three fields of `/proc/loadavg` (`cut -d' ' -f1-3`: split the line at spaces and keep fields 1 to 3). They are the load averages over the last 1, 5 and 15 minutes. |

### Start `probe.txt` with the build environment (lines 25 to 31)

| Line | Source | Explanation |
|---:|---|---|
| 25 | `{` | Opens a group of commands. Line 31 closes the group and writes the output of lines 26 to 30 to the new file `probe.txt`. |
| 26 | `  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(load) logins=$(who \| wc -l) mode=$MODE"` | First line of `probe.txt`: the host name, the UTC time, the load averages (function `load`, line 24) under the name `load_before`, the number of login sessions and the mode. `who` prints one line per login session, and `wc -l` counts the lines. |
| 27 | `  echo "## gcc=$(gcc --version \| head -1)"` | Line of `probe.txt`: the first line of `gcc --version` (`head -1` keeps the first line). It names the compiler version. |
| 28 | `  echo "## CFLAGS=$CFLAGS"` | Line of `probe.txt`: the flags of line 23. |
| 29 | `  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"` | Line of `probe.txt`: the setting for transparent huge pages. The value in square brackets is the active one. |
| 30 | `  echo "## busiest processes (pcpu user comm):"; ps -eo pcpu,user,comm --sort=-pcpu \| head -6` | Writes a title line, then the busiest processes. `ps -eo pcpu,user,comm --sort=-pcpu` lists all processes with their %CPU, user and command name, highest %CPU first. `head -6` keeps the title line of `ps` and 5 processes. %CPU (`pcpu`) is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU use at this moment. |
| 31 | `} > "$OUT/probe.txt"` | Closes the group of line 25. `> "$OUT/probe.txt"` writes the output of all its commands to the new file `probe.txt` in the result folder. |

### Function `build` and the four builds (lines 32 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 32 | `# old = the source before the change; new = the changed source` | Comment: in the names below, `old` means the source before the change and `new` means the changed source. |
| 33 | `build() { gcc $CFLAGS "$@" 2>> "$OUT/build.txt" \|\| { echo "build failed: $OUT/build.txt" >&2; cat "$OUT/build.txt" >&2; exit 5; }; }` | Defines the function `build`. It runs `gcc` with the flags of line 23, followed by the arguments of the call (`"$@"`). `$CFLAGS` has no quotes. So the shell splits it into the seven flags. `2>>` appends the messages of gcc (its error output) to `build.txt`. If gcc fails, the script prints `build failed:` with the path of `build.txt`, then the content of `build.txt`, to the error output and ends with status 5. |
| 34 | `: > "$OUT/build.txt"` | Creates `build.txt` as an empty file before the first build. `:` is a command that does nothing, and `>` empties the file. |
| 35 | `build -o "$SRC/bw_old" "$SRC/bandwidth.orig.c"` | `bandwidth.orig.c` (the old source) becomes the binary `bw_old`. It holds the old read kernel. `-o` names the output file. The four builds of lines 35 to 38 use the same flags, and all four output files are written to the script folder. Both modes run these lines. So every start of the script builds `bw_old` and `bw_new` again and replaces the files. |
| 36 | `build -o "$SRC/bw_new" "$SRC/bandwidth.c"` | `bandwidth.c` (the new source) becomes the binary `bw_new`. It holds the new read kernel. |
| 37 | `build -o "$SRC/selftest" "$SRC/selftest.c"` | `selftest.c` becomes the binary `selftest`. This source includes `bandwidth.c`. So the self-test checks the kernels of the new source [Ref6]. |
| 38 | `build -c -o "$SRC/probe.o" "$SRC/probe.c"` | `probe.c` becomes the object file `probe.o`. `-c` means compile only, with no linking. The file holds three candidate copy loops [Ref7]. |
| 39 | `echo "## build output bytes: $(wc -c < "$OUT/build.txt")" >> "$OUT/probe.txt"` | Appends the size of `build.txt` in bytes to `probe.txt` (`wc -c` counts bytes). 0 bytes means that gcc printed no warning. On 2026-11-13 the size was 0 bytes [Ref1]. |

### Append checksums and machine code to `probe.txt` (lines 40 to 57)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `{` | Opens a second group of commands. Line 57 closes it and appends the output of lines 41 to 56 to `probe.txt`. |
| 41 | `  echo "## sha256:"; (cd "$SRC" && sha256sum bandwidth.orig.c bandwidth.c selftest.c probe.c run_kernels.sh bw_old bw_new selftest)` | Writes a title line, then the sha256 of the four sources, of this script and of the three binaries. The parentheses run `cd` and `sha256sum` in a subshell (a child copy of the shell) inside `SRC`. So the output shows the file names without a folder. `ra.sh` later compares `bw_old` and `bw_new` with the two values that this line wrote [Ref8]. |
| 42 | `  sha256sum "$HOME/cache-perf/bench/bandwidth.c"` | Writes the sha256 of the copy of the benchmark source in the folder `bench`. On 2026-11-13 it was equal to the sha256 of `bandwidth.orig.c` [Ref1]. |
| 43 | `  for b in bw_new bw_old; do` | Starts the listing of the machine code. Outer loop: first the binary `bw_new`, then `bw_old`. |
| 44 | `    for f in k_read k_write k_copy k_asmread k_asmwrite k_asmcopy; do` | Inner loop: each of the six kernel functions `k_read`, `k_write`, `k_copy`, `k_asmread`, `k_asmwrite` and `k_asmcopy`. |
| 45 | `      echo "=== $b $f ==="` | Prints a title line of the form `=== binary function ===`. |
| 46 | `      objdump -d --no-show-raw-insn --disassemble=$f "$SRC/$b" \| sed -n '/>:$/,/^$/p'` | Prints the machine code of that function. `objdump -d --disassemble=$f` prints the instructions of the function `$f` only. `--no-show-raw-insn` leaves out the bytes of each instruction. `sed -n '/>:$/,/^$/p'` prints only the lines from the function label (a line that ends with `>:`) to the next empty line. The title lines of objdump are dropped. This listing is the record of what each kernel does in one loop pass. The C source alone does not decide that. The compiler chooses the instructions. |
| 47 | `    done` | Ends the loop over the functions (line 44). |
| 48 | `  done` | Ends the loop over the binaries (line 43). |
| 49 | `  for f in copy_barrier copy_plain copy_plain_norestrict; do` | The same listing for the three functions of `probe.o`: `copy_barrier`, `copy_plain` and `copy_plain_norestrict`. These loops are only compiled. No part of the script runs them. |
| 50 | `    echo "=== probe.o $f ==="` | Prints a title line of the form `=== probe.o function ===`. |
| 51 | `    objdump -d --no-show-raw-insn --disassemble=$f "$SRC/probe.o" \| sed -n '/>:$/,/^$/p'` | Prints the machine code of that function of `probe.o`, with the same `objdump` and `sed` commands as in line 46. |
| 52 | `  done` | Ends the loop of line 49. |
| 53 | `  for b in latency homelat; do` | The same listing for the function `chase` of two other programs in the folder `bench`: `latency` and `homelat`. The script only prints the machine code of these two programs. It does not run them. |
| 54 | `    echo "=== bench/$b chase ==="` | Prints a title line of the form `=== bench/program chase ===`. |
| 55 | `    objdump -d --no-show-raw-insn --disassemble=chase "$HOME/cache-perf/bench/$b" \| sed -n '/>:$/,/^$/p' \|\| echo "(not available)"` | Prints the machine code of `chase`, with the same commands as in line 46. `objdump` fails when the binary is missing. `pipefail` then makes the pipeline fail. The part after `\|\|` prints the line `(not available)`, and the script continues. |
| 56 | `  done` | Ends the loop of line 53. |
| 57 | `} >> "$OUT/probe.txt"` | Closes the group of line 40. `>> "$OUT/probe.txt"` appends the output of lines 41 to 56 to `probe.txt`. |

### Self-test, end of mode `probe`, start of the hardware record (lines 58 to 63)

| Line | Source | Explanation |
|---:|---|---|
| 58 | `check_marker` | Checks the marker file again (`check_marker`, line 17), before the self-test. |
| 59 | `"$SRC/selftest" > "$OUT/selftest.txt" 2>&1 && echo "## selftest exit=0" >> "$OUT/probe.txt" \|\| { echo "## selftest exit=$?" >> "$OUT/probe.txt"; echo "selftest failed" >&2; echo "$OUT"; exit 4; }` | Runs `selftest`. `> "$OUT/selftest.txt" 2>&1` writes its output and its error output to `selftest.txt`. On success (`&&`) the script appends `## selftest exit=0` to `probe.txt`. On failure (`\|\|`) it appends the exit status to `probe.txt`, prints `selftest failed` to the error output and the result folder to the standard output, and ends with status 4. So the timed processes below start only after the self-test has passed. |
| 60 | `if [[ $MODE != all ]]; then echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"; echo "$OUT"; exit 0; fi` | In mode `probe` the script ends here with status 0. Before that it appends the load averages and the UTC time to `probe.txt` and prints the result folder. Only mode `all` continues to the timed processes. |
| 61 | `echo "## hw=${HW:-on} hw_power=${HW_POWER:-require}" >> "$OUT/probe.txt"` | Appends the two settings of the hardware record to `probe.txt`. The line shows `hw=on` and `hw_power=require` when the variables `HW` and `HW_POWER` are not set or are empty. Only mode `all` reaches this line. |
| 62 | `hw_init "$OUT" \|\| { echo "hardware record not usable: stop" >&2; exit 7; }` | Starts the hardware record for the result folder. `hw_init` first tests the tools (function `hw_check` of `hw.sh`). Then it writes the files `status.txt` and `probe.txt` in the folder `hw` of the result folder. Then it starts two background programs. The first is the frequency sampler (`hwwatch.py watch`, one sample per second unless `HW_PERIOD_S` says otherwise). The second is the vendor tool `atx` (Arm Telemetrix), which reads power, temperature and frequency values of the firmware. `atx` is started only when `HW_POWER` is `require`. Both are pinned to CPU 119 unless `HW_CPU` says otherwise, and line 87 stops them. So during the timed intervals of a 120-thread process they share CPU 119 with one benchmark thread. `hw_init` also sets a trap that calls `hw_done` when the shell of the script ends. When `hw_init` fails, the script prints `hardware record not usable: stop` to the error output and ends with exit status 7. With `HW=off` the call does nothing (line 15). |

### Function `one`: start one benchmark process (lines 64 to 72)

| Line | Source | Explanation |
|---:|---|---|
| 64 | `# One process per (binary, kernel): no kernel is timed after another kernel` | Comment: each process runs one kernel of one binary. So no kernel is timed after another kernel in the same process. The sentence ends in line 65. |
| 65 | `# in the same process. Round 2 reverses the order of binaries and kernels.` | Comment, continued: round 2 runs the binaries and the kernels in the reverse order of round 1. |
| 66 | `one() { # csv binary kernel threads cpus bytes round` | Starts the function `one`. It starts one benchmark process and waits for it. Its arguments, in this order: csv file, binary, kernel, threads, CPU list, bytes, round. |
| 67 | `  check_marker` | Checks the marker file before every process (`check_marker`, line 17). Nothing checks it while a process runs. |
| 68 | `  hw_begin "$2-$3-t$4-c$5-$6-r$7" "$5"` | Takes the first snapshot of the hardware record for this process. `hw_begin` gets a label and the CPU list. The label holds the binary, the kernel, the thread count, the CPU list, the bytes and the round, for example `bw_old-read-t1-c0-32K-r1`. `hw_begin` gives the process a numbered label and writes a snapshot of these CPUs to a file `NNN-LABEL.before.txt` in the folder `hw`. By the comment in `hw.sh`, this call must stand before the quiet time of the launch. `run_kernels.sh` has no pause between this call and the start of the binary in line 70. |
| 69 | `  echo "-- binary $2 kernel $3 threads $4 cpus $5 bytes $6 round $7 load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$1"` | Appends one line that starts with `--` and a space to the csv file. It holds the arguments, the 1-minute load average at this moment and the UTC time (hours, minutes, seconds). `stat_k120.py` reads this line to know which rows belong to which process [Ref10]. |
| 70 | `  "$SRC/$2" --threads "$4" --cpus "$5" --bytes "$6" --kernel "$3" --reps 3 --min-ms 500 >> "$1"` | Starts the binary with one kernel (`--kernel`) and waits until it ends. `>>` appends the rows that the binary prints to the csv file. `--reps 3`: the process times 3 intervals. `--min-ms 500`: each interval lasts at least 500 ms [Ref3]. If the binary ends with a status other than 0, `set -e` ends the script with that status. |
| 71 | `  hw_end` | Takes the second snapshot of the hardware record, after the process (file `NNN-LABEL.after.txt`). `hw_end` also tests that the sampler is still running, and `atx` too when `HW_POWER` is `require`. When a snapshot fails or a program is not running, `hw_end` adds a line that starts with `FAILED` to the file `status.txt` in the folder `hw`. It does not stop the script. |
| 72 | `}` | Ends the function `one`. |

### One-thread processes (the rerun of 2026-11-17 does not repeat them) (lines 73 to 82)

| Line | Source | Explanation |
|---:|---|---|
| 73 | `K1="read write copy asmread asmwrite asmcopy"; K2="asmcopy asmwrite asmread copy write read"` | `K1` is the kernel order of round 1. `K2` holds the same six names in the reverse order, for round 2. `read` and `asmread` are the read kernels, and the other four names are the write and copy kernels. A `for` loop over such a list takes the names one by one. |
| 74 | `for round in 1 2; do` | Starts the one-thread part: a loop over two rounds. `round` is 1, then 2. |
| 75 | `  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi` | Sets the order of the round. Round 1: `BINS` holds old, then new, and `KS` is `K1`. Round 2: `BINS` holds new, then old, and `KS` is `K2`. So round 2 reverses the order of the kernels and of the binaries, as in the 120-thread part. It does not reverse the order of the CPUs and of the sizes. |
| 76 | `  for cpu in 0 2; do` | In each round: CPU 0, then CPU 2. |
| 77 | `    for bytes in 32K 1M 8M 1G; do` | For each CPU the buffer sizes `32K`, `1M`, `8M` and `1G` (32 KiB, 1 MiB, 8 MiB, 1 GiB). |
| 78 | `      for k in $KS; do for b in $BINS; do one "$OUT/one-thread.csv" $b $k 1 $cpu $bytes $round; done; done` | For each size all six kernels with both binaries: one call of `one` (line 66) per kernel and binary. Each process has 1 thread, pinned to that one CPU. Its rows are appended to `one-thread.csv`. That gives 2 times 2 times 4 times 6 times 2 = 192 processes. |
| 79 | `    done` | Ends the loop over the buffer sizes (line 77). |
| 80 | `  done` | Ends the loop over the CPUs (line 76). |
| 81 | `done` | Ends the loop over the rounds (line 74). |
| 82 | `echo "## one-thread done load=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"` | Appends the load averages and the UTC time after this part to `probe.txt`. |

### The 120-thread part (the test that `ra.sh` repeats) and the end (lines 83 to 89)

| Line | Source | Explanation |
|---:|---|---|
| 83 | `for round in 1 2; do` | Starts the 120-thread part: a loop over two rounds. All 24 processes append to one file, `threads120.csv`. No wait comes before this part or between two processes. On 2026-11-13 the last one-thread process started at 18:17:20 UTC and the first of the 24 processes at 18:17:21 UTC [Ref2]. In the present text the two snapshots of the hardware record run between two processes (line 71 and line 68). |
| 84 | `  if [[ $round == 1 ]]; then BINS="bw_old bw_new"; KS=$K1; else BINS="bw_new bw_old"; KS=$K2; fi` | Sets the order of the round, with the same text as line 75. Round 1: for each kernel first `bw_old`, then `bw_new`. Order: old `read`, new `read`, old `write`, new `write`, old `copy`, new `copy`, old `asmread`, new `asmread`, old `asmwrite`, new `asmwrite`, old `asmcopy`, new `asmcopy`. Round 2: the exact reverse of round 1. Order: new `asmcopy`, old `asmcopy`, new `asmwrite`, old `asmwrite`, new `asmread`, old `asmread`, new `copy`, old `copy`, new `write`, old `write`, new `read`, old `read`. |
| 85 | `  for k in $KS; do for b in $BINS; do one "$OUT/threads120.csv" $b $k 120 0-119 256M $round; done; done` | One call of `one` (line 66) per kernel and binary. Every process gets the same arguments: 120 threads and the CPU list `0-119`. The binary pins thread number i to CPU i. `256M` gives each thread its own buffer of 256 MiB. For the kernels `copy` and `asmcopy` each thread gets a second buffer of the same size. Each process times 3 intervals of at least 500 ms each [Ref3]. In the present texts `ra.sh` holds lines 83 to 86 with the same text. Its function `one` differs from lines 66 to 72 in one line only: the label that `hw_begin` gets. |
| 86 | `done` | Ends the loop over the rounds (line 83). |
| 87 | `hw_done` | Stops the hardware record. `hw_done` ends the sampler and `atx`, adds its last lines to `status.txt` and removes the trap of line 62. It waits at most 30 s for `atx` to end. |
| 88 | `echo "## load_after=$(load) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"` | Appends the load averages and the UTC time to `probe.txt`, under the name `load_after`. They are read after the last process and after the stop of the hardware record in line 87. |
| 89 | `echo "$OUT"` | Prints the path of the result folder. It is the last command, so the script then ends with status 0. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Written by this script at 18:12:22 UTC on 2026-11-13. Line 1: mode `all`. Line 2: gcc 14.2.0. Line 3: the flags. Line 12: build output of 0 bytes. Lines 14 to 22: checksums. Lines 23 to 330: machine code of the six kernels of bw_new (from line 23) and of bw_old (from line 155). Line 437: self-test exit status 0.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/one-thread.csv, /home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/threads120.csv`: The 192 and the 24 lines that start with `-- ` give the order, the load and the start time of each process on 2026-11-13.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.orig.c, /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/bandwidth.c`: The old and the new benchmark source. The functions `main`, `worker`, `pin_cpu`, `alloc_buf` and `pass` are the source for the statements on arguments, pinning, buffers, timing and the rate. Lines 162 to 255 of the old source and lines 286 to 379 of the new source (the hand-written kernels) have the same text (compared with diff). The local bandwidth.orig.c has the sha256 61228754... and the local bandwidth.c has the sha256 f1985072... (computed with sha256sum on 2026-11-21).
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181210Z/probe.txt`: Written by the start of 18:12:10 UTC, mode `probe`. Lines 14 to 22 hold the same checksums as in Ref1.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T183218Z/probe.txt`: Written by the start of 18:32:18 UTC, mode `probe`. Line 15: bandwidth.c with the sha256 f1985072.... Lines 19 and 20: bw_old and bw_new with the same sha256 as in Ref1. Lines 23 to 436 (the machine code) equal the same lines of Ref1 (compared with diff).
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/selftest.c`: Lines 15 to 17 include bandwidth.c under another name for `main`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/probe.c`: Line 1 calls the file "compile-only candidates for k_copy". It defines copy_barrier, copy_plain and copy_plain_norestrict.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`: Lines 17 and 18 hold the sha256 values that it checks. Lines 37 to 48 have the same text as lines 58 to 65 and 75 to 78 of run_kernels.sh (compared with diff). The driver go.sh in the same folder calls ra.sh and does not call run_kernels.sh.
- [Ref9] Help text of the local gcc 11.4.0 for x86-64, read on 2026-11-21: `gcc --help=optimizers`, `gcc --help=common`, `gcc --help=warnings`, `gcc --help=c`, `gcc --help=target`, `gcc -Q --help=optimizers` with `-O2`, `-O3` and `-O4`, and `gcc -dumpspecs` for `-pthread`. In this gcc, `-O3` and `-O4` turn on the same options, `-O3` turns on loop vectorization, and `-fno-tree-loop-distribute-patterns` turns off exactly one option that `-O3` has on.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/stat_k120.py`: Line 21 holds the pattern that reads the lines that start with `-- `.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: The facts sheet of the rerun of 2026-11-17. Line 77 (list "Words used here") says that another user creates the marker file during a performance test. The script itself does not say who creates the file.
- [Ref12] external source: manual of gcc 14.2.0, page "AArch64 Options", entry `-march=name`, read on 2026-11-21. The entry says that the value `native` "causes the compiler to pick the architecture of the host system". It says that gcc uses the architecture name to decide which instructions it can emit. It also says that with `-march` and without `-mtune` or `-mcpu` the code is tuned for a range of processors that implement the architecture. The sub-section "-march and -mcpu Feature Modifiers" of the same page says that each of `sve2-aes`, `sve2-bitperm`, `sve2-sha3` and `sve2-sm4` also enables SVE2 instructions, and that `sve2` also enables SVE instructions.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt`: A record from CRB of 2026-11-11 at 21:00:17 UTC. Line 4 holds the same gcc version text as line 2 of Ref1. Line 5 holds what `gcc -march=native -Q --help=target` printed for the options `-march=`, `-mcpu=` and `-mtune=`. The value of `-march=` is `armv8-a` with 16 extensions. Four of them are SVE2 extensions: `sve2-aes`, `sve2-bitperm`, `sve2-sha3` and `sve2-sm4`. The values of `-mcpu=` and `-mtune=` are empty. The file probe-20261111T210017Z.cmd.txt in the same folder holds the commands that wrote the record.
- [Ref14] `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl`: record of the Claude Code session of 2026-11-13. Line 1000 (18:32:07 UTC) holds the command that replaced 2 comment lines above `k_read` in bandwidth.c with 5 comment lines and copied the file to the folder kernels-2026-11-13. With this edit reversed, the local bandwidth.c has the sha256 value c1406e026ac26af21d88beb011ef51c0529600b6623eba0d1d2bde8ea6a04ba2 (test of 2026-11-21). That is the value that the runs of 18:12:10 UTC and 18:12:22 UTC recorded.
