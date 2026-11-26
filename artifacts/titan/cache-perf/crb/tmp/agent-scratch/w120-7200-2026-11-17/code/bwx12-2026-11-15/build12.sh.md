# `build12.sh` explained

- Source file: `bwx12-2026-11-15/build12.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 160 lines, 8561 bytes).
- sha256 of the source when this page was built: `8601ca3a4daaffa48438c749d5fa6c3387358ba88bdab89a9e5eef4b0aabf185`.
- Role in the whole-chip test: Build script: compiled the runner bwx12 on CRB on 2026-11-15 and recorded the build.
- This page was built on 2026-11-25 from an older page: `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh.md`. Every section except "Source and explanation, line by line" is a copy of a section of that page.

## Short version: purpose

The script compiles `bwx12.c` into the binary `bwx12` with ten fixed compiler flags, tests the binary, and records the build: compiler, flags, checks, the machine code of every kernel, and sha256 values. It ran on CRB on 2026-11-15, and the whole-chip test of 2026-11-17 used the binary that it built.

<details>
<summary>Words used here</summary>

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **CRB build**: the run of this script on CRB on 2026-11-15 that built the binary of the whole-chip test. The folder `crb-build-1` beside the script holds its records, without the binary [Ref1].
- **Whole-chip test**: the run under review: the read test of 2026-11-17 on CRB. "Whole chip" means: our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.
- **Kernel**: one inner loop of the benchmark. In bwx12.c each kernel is a function with the name `k_<name>`. The CRB build of bwx12 has 55 kernels. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the inner loop of the benchmark that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.
- **asmread**: a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.
- **read_nop96, read_nop256, read_1pl**: test loops of bwx12: the asmread loop with 96 or 256 no-operation instructions per 256 B, and a loop with one load per 64 B line.
- **bandwidth.c, bw_old, bw_new**: the benchmark and its two binaries of 2026-11-13. bw_old was built from the old source, bw_new from the new source.
- **bwx12, bwx11, bwx**: later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.
- **bwx8, bwx10**: two more older versions of the runner. bwx12.c is bwx11.c plus additions, bwx11.c is bwx10.c plus additions, and bwx10.c is bwx8.c plus additions [Ref8].
- **Accepted build, accepted binary**: the build on CRB of an older runner version. It serves as the reference for a new build. For bwx11 it is the build in the folder `crb-build-1` of bwx11 [Ref10].
- **Development machine**: the machine on which the check scripts run on the files that come back from CRB. It is not CRB [Ref10].
- **Marker file**: `/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.
- **Self-test**: the mode `--selftest` of bwx12. It calls every kernel on small buffers and checks the memory afterwards. It prints one row per check and ends with the line `# failures=N` [Ref9].
- **Interval mode, trial mode**: the two modes of bwx12. Interval mode (option `--seq`): the threads run a sequence of kernels. Each kernel of the sequence gets one timed interval per round (a round is one repeat of the sequence). The whole-chip test uses it. Trial mode (option `--trial`): one pinned thread runs the trials of a plan file. A trial is a series of timed windows. The whole-chip test does not use it [Ref8].
- **Spec file**: a text file with one line per bwx12 process: a tag, the character `|`, and the arguments of the process. The whole-chip test has three, each with one line: `like.spec`, `cfwd.spec` and `crev.spec` [Ref13].
- **`go.sh`, `go2.sh`, `rx.sh`**: scripts of the whole-chip test. `go.sh` and `go2.sh` are the drivers. They call `rx.sh`, which starts one bwx12 process per line of a spec file [Ref11] [Ref12].
- **`worker`**: the function of bwx12.c that each benchmark thread runs in the interval mode. It reads the clock before and after the kernel calls of an interval [Ref8].
- **`timed_sequence`, `timed_sequence_hot`**: the two functions of bwx12.c that time the windows of one trial in the trial mode. `timed_sequence_hot` runs when the option `--hot-copy` is given [Ref8].
- **`tcount`**: a function of bwx12.c for the trial mode. It reads the event counters and the CPU time of the thread at the edge of a window [Ref8].
- **`call`**: the function of bwx12.c that runs one kernel on a byte range of the buffer of a thread [Ref8].
- **`read_smaps`**: the function of bwx12.c that reads the page state of a buffer from the file `/proc/self/smaps` [Ref8].
- **`PLACE`**: a macro of bwx12.c that stands before each kernel. It pads the code to a 64-byte boundary and then adds a set number of bytes. So the kernel starts at a planned address modulo 64 [Ref8].
- **Address modulo 64**: the remainder when the address is divided by 64. It is the offset inside a 64-byte block of code, from 0 to 63 bytes.
- **Loop start**: the address of the first instruction of the loop of a kernel. The script takes the target of the first backward branch of the function.
- **Branch target**: the address that a branch or call instruction goes to.
- **Listing**: machine code printed as assembler text, one instruction per line with its address.
- **objdump**: a tool that prints the machine code of a binary as a listing.
- **nm**: a tool that lists the symbols of a binary (the names of functions and variables) with their addresses.
- **taskset**: a Linux tool that starts a program limited to a list of CPUs.
- **sha256**: a checksum. Two files with the same sha256 have the same content. The value has 64 hexadecimal digits.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file /proc/loadavg).
- **SVE**: Scalable Vector Extension, a vector instruction set extension of Arm CPUs.
- **Stack-guard failure function**: `__stack_chk_fail`. Check code that the compiler adds to a function calls it when the guard value on the stack was overwritten.

</details>

## Main flow

1. Stop with status 3 if the marker file exists. The same check runs again before each run of the new binary (lines 31-33).
2. Restart the script under `taskset`, limited to CPUs 0 to 119 (line 34).
3. Set the compiler and the ten compiler flags (lines 35-37).
4. Start `build.txt` with host, time, load averages, logins, compiler version and flags (lines 38-45).
5. Compile `bwx12.c` into `bwx12`. Compiler messages go to `build.txt`. A failed compile ends the script with status 5 (lines 46-48).
6. Run `bwx12 --selftest` and save its output in `selftest-bwx12.txt`. A failed self-test ends the script with status 4 (lines 49-55).
7. For each kernel that `bwx12 --list` names: append its machine code to `listing.txt`, and write its start, its loop start and the loop start modulo 64 to `offsets.tsv` (lines 56-75).
8. Save the machine code of `timed_sequence` and `timed_sequence_hot` in `seq-listing.txt`, write their branch targets to `build.txt`, and end with status 6 if a target is not allowed (lines 76-99).
9. Write to `build.txt` where five functions start modulo 64, and whether the accepted binaries of bwx8, bwx10 and bwx11 have the same values (lines 100-151).
10. Append the sha256 values of seven files, the load averages and the end time to `build.txt` (lines 152-157).
11. Print `build.txt` and `offsets.tsv` to the standard output (lines 158-160).

## Behavior a reader must know

- The script does not run during the whole-chip test. The saved record is of one run on CRB on 2026-11-15, from 17:12:11 to 17:12:14 UTC [Ref1]. The folder `crb-build-1` beside the script holds the files of that build. The script times nothing and computes no rate.
- `set -euo pipefail` (line 30) holds for the whole script. The script ends when a command fails, when it uses a variable that was never set, or when one command of a pipeline fails. A command that `if` tests, or that `||` follows, does not end it. Other failures also do not stop the build. Two examples: a failed `bwx12 --list` in the `for` list of line 62, and a failed `nm` inside `placement` (line 109). The row of line 30 gives the rule.
- Records of one build: the binary `bwx12`, `build.txt`, `selftest-bwx12.txt`, `listing.txt`, `offsets.tsv`, `seq-listing.txt`, and the text on the standard output. The rows of lines 38 to 160 explain each record at the line that writes it. The entry [Ref1] says what each of the 24 lines of the CRB `build.txt` holds.
- Link from the test to this build: `build.txt` records the sha256 value `cd58e5644cd3e76d58a23569c8a42f4f23e240e5f75cce5f84f6bdf31033546a` for the binary [Ref1]. `go.sh` and `go2.sh` hold this value and pass it to `rx.sh`. All three scripts stop when the `bwx12` file has another value [Ref11] [Ref12]. All 9 `env.txt` files of the bwx12 runs of the test record this value [Ref14].
- Link from the build to the local source: the local copies of `bwx12.c`, `bwx12_selftest.c` and `build12.sh` have the sha256 values that `build.txt` records [Ref20]. The binary itself is not under the local folder `crb`.
- Compiler and flags against the binaries of 2026-11-13: the same gcc 14.2.0 built bw_old and bw_new with the first seven flags of line 37. bwx12 has three more flags: `-fno-ipa-icf`, `-fno-toplevel-reorder` and `-falign-functions=4` [Ref15] [Ref16].
- The branch-target check of lines 76 to 99 covers the trial mode only. The whole-chip test ran the interval mode (`--seq` in the spec files). In that mode the function `worker` of bwx12.c reads the clock and calls the kernels [Ref8] [Ref13]. The build record holds the machine code of the kernels, not of `worker`. Insufficient data: whether gcc inlined the function `call` into `worker`. The output of `objdump -d --disassemble=worker` on the binary would resolve it. The symbol `call` in the placement line of `build.txt` does not resolve it [Ref21].
- This script does not compare the kernel code with an accepted build. `check_listing12.py` does that afterwards on the development machine [Ref10]. Its saved output for the CRB build reports 0 failed rows for the 29 kernels of bwx11 and 0 failed rows for the 26 new kernels. Of the six kernels of the whole-chip test, `oldread`, `read`, `asmread`, `read_nop96` and `read_1pl` have the same function text as in the accepted bwx11 build, apart from addresses. `read_nop256` is a new kernel, and its loop has the expected instructions [Ref7].
- `build.txt` is written in steps. The sha256 block (lines 154 and 155) and the `load_after` line (line 156) come last. A `build.txt` of this script without the `## sha256:` block belongs to a build that stopped early.
- Six environment variables change a run: `BWX_MARKER` (path of the marker file), `BWX_CPUS` (CPU list), `CC` (compiler), and `BWX8_BIN`, `BWX10_BIN`, `BWX11_BIN` (paths of the older binaries). The script also reads `_PINNED` (line 34). It sets this variable itself for the restart under `taskset`. If the variable is already set and not empty at the start, the script does not restart, and it sets no CPU limit.

## Call sequence in the whole-chip test

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

## Functions

| Function | Lines | What it does | Calls | On the timed path |
|---|---|---|---|---|
| `check_marker` | 32-32 | Ends the script with status 3 when the marker file exists. | - | - |
| `placement` | 107-112 | Prints `name=value` pairs: the start address modulo 64 of five functions of the given binary, read with `nm`. | `nm`, `awk`, `sort` | - |

## Source and explanation, line by line

- This section was written on 2026-11-25. It replaces an earlier table that explained the source in groups of lines.
- Text shown: the file `bwx12-2026-11-15/build12.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (160 lines, 8561 bytes, sha256 `8601ca3a4daaffa48438c749d5fa6c3387358ba88bdab89a9e5eef4b0aabf185`).
- The other sections of this page were written for the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/build12.sh`. It has the same sha256. So the line numbers in those sections fit the tables below.
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: what the script does (lines 1 to 12)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# build12.sh - on CRB: build bwx12, run its self-test, print the digests, and` | Comment: the name and the purpose of the script. It runs on CRB, the Arm reference server under test. It builds the binary `bwx12`, runs the self-test of the binary and prints checksums. The comment calls the checksums digests. The sentence goes on in line 3. |
| 3 | `# save the machine code of every kernel (design tackle-8mb.md, "Fixed setup":` | Comment: the script also saves the machine code of every kernel. A kernel is one inner loop of the benchmark. The comment then names the section "Fixed setup" of the design note `tackle-8mb.md`. |
| 4 | `# a build whose listing differs from the accepted one is rejected).` | Comment: the rule of that section. A build whose listing differs from the accepted one is rejected. A listing is machine code printed as assembler text. This script does not apply the rule. The check script that the header comment names as the step after the build applies it. |
| 5 | `# It is build11.sh for bwx12.c, with the same checks, and one addition:` | Comment: this script is `build11.sh`, the build script of the runner version before, changed for `bwx12.c`. It has the same checks and one addition. |
| 6 | `# build.txt also holds the placement of the timed path in the accepted bwx11` | Comment: the addition. The record `build.txt` also holds the placement of the timed path in the accepted `bwx11` binary. The placement is the start address modulo 64 of five functions (lines 101 to 106). The accepted binary of an older runner version comes from its build on CRB. It serves as the reference for a new build. |
| 7 | `# and says whether bwx12 has the same placement.` | Comment: `build.txt` also says whether `bwx12` has the same placement (lines 140 to 151). |
| 8 | `# (build11.sh is build10.sh with the same addition for the accepted bwx10.)` | Comment: `build11.sh` is `build10.sh` with the same addition for the accepted `bwx10` binary. |
| 9 | `# (build10.sh is build8.sh with three additions: the branch-target check` | Comment: `build10.sh` is `build8.sh` with three additions. The first addition starts here: the branch-target check (lines 77 to 99) ... |
| 10 | `# covers timed_sequence_hot() too, the machine code of both timed functions is` | Comment: ... covers the function `timed_sequence_hot` too. The second addition: the machine code of both timed functions ... |
| 11 | `# saved in seq-listing.txt, and build.txt holds the placement of the timed` | Comment: ... is saved in `seq-listing.txt` (line 87). The third addition: `build.txt` holds the placement of the timed ... |
| 12 | `# path in the new binary and in the accepted bwx8.)` | Comment: ... path in the new binary and in the accepted `bwx8` binary (lines 113 to 127). |

### Header comment: usage, output files, exit statuses, files read (lines 13 to 29)

| Line | Source | Explanation |
|---:|---|---|
| 13 | `# Usage: build12.sh` | Comment: the usage. The script takes no argument. |
| 14 | `# The compiler flags are the flags of build8.sh. There is no EXTRA.` | Comment: the compiler flags are the flags of `build8.sh`. `EXTRA` was a variable for more compiler flags in the build script of the older runner version `bwx` [Ref19]. This script has no such variable, so the flags of line 37 are the only flags. |
| 15 | `# Output, all in the folder of this script (on CRB: ~/cache-perf/bwx12-20261115/):` | Comment: the script writes all its output into its own folder. On CRB that folder is `~/cache-perf/bwx12-20261115/`. Lines 16 to 21 list the six files. The rows below explain each file at the line that writes it. |
| 16 | `#   bwx12                the binary` | Comment: the output file `bwx12`, the binary (line 47). |
| 17 | `#   build.txt            host, load, compiler, flags, compiler messages, sha256` | Comment: the output file `build.txt`, the record of the build. It holds the host, the load, the compiler, the flags, the compiler messages and the sha256 values. A sha256 value is a checksum. Two files with the same sha256 have the same content. |
| 18 | `#   selftest-bwx12.txt   output of "bwx12 --selftest"` | Comment: the output file `selftest-bwx12.txt`, the output of `bwx12 --selftest` (line 51). |
| 19 | `#   listing.txt          "=== bwx12 <kernel> ===" and the objdump text of function k_<kernel>` | Comment: the output file `listing.txt`. For each kernel it holds the title line `=== bwx12 <kernel> ===` and the `objdump` text of the function `k_<kernel>` (line 65). `objdump` is a tool that prints the machine code of a binary as a listing. |
| 20 | `#   offsets.tsv          binary, kernel, function, start, loop_start, loop_mod64 (addresses in hex)` | Comment: the output file `offsets.tsv`, a table with the six columns `binary`, `kernel`, `function`, `start`, `loop_start` and `loop_mod64`. The addresses are hexadecimal (line 60, line 74). |
| 21 | `#   seq-listing.txt      the objdump text of timed_sequence and timed_sequence_hot (for reading; no script uses it)` | Comment: the output file `seq-listing.txt`, the `objdump` text of the functions `timed_sequence` and `timed_sequence_hot` (line 87). It is for a person to read. No script uses it. |
| 22 | `# Then, on the development machine: check_listing12.py listing.txt offsets.tsv` | Comment: the step after the build. On the development machine, `check_listing12.py` compares `listing.txt` and `offsets.tsv` with the accepted build of bwx11 (the runner version before bwx12) [Ref10]. The development machine is the machine on which the check scripts run. It is not CRB. |
| 23 | `# Exit status: 0 done; 3 marker file present; 4 the self-test failed; 5 the build failed;` | Comment: the exit statuses. Each one belongs to one check: 3 to `check_marker` (line 32), 4 to the self-test (line 54), 5 to the compiler call. Status 0 means that every step ran. Another failed command can also end the script (rule `-e` of line 30, with the exceptions named there). The exit status is then the status of that command. |
| 24 | `#   6 a timed sequence of the trial mode reaches a function that is not allowed there.` | Comment: exit status 6 belongs to the branch-target check (line 99): a timed sequence of the trial mode reaches a function that is not allowed there. The trial mode is the mode of the runner with the option `--trial`. The code gives status 6 in one more case that the comment does not name. In that case the list of branch targets of a timed function has no entry for `clock_gettime` or no entry for an indirect call (line 95). |
| 25 | `# Writes only in its own folder. No sudo. Runs on CPUs 0-119 only (BWX_CPUS changes the list).` | Comment: the script writes only in its own folder. It does not use `sudo`, the command that runs a program as root. It runs on the CPUs 0 to 119 only. The environment variable `BWX_CPUS` changes that list (line 34). The code makes one exception that the comment does not name: it sets no CPU limit when the variable `_PINNED` is already set and not empty at the start (line 34). |
| 26 | `# It reads three files outside its folder, if they exist: the accepted binaries` | Comment: the script reads three files outside its folder, when they exist: the accepted binaries of three older runner versions ... |
| 27 | `# of bwx8 (BWX8_BIN, default ../bwx8-20261114/bwx8), of bwx10 (BWX10_BIN,` | Comment: ... of bwx8 (environment variable `BWX8_BIN`, default `../bwx8-20261114/bwx8`), of bwx10 (environment variable `BWX10_BIN`, default on the next line) ... |
| 28 | `# default ../bwx10-20261115/bwx10) and of bwx11 (BWX11_BIN, default` | Comment: ... default `../bwx10-20261115/bwx10`, and of bwx11 (environment variable `BWX11_BIN`, default on the next line) ... |
| 29 | `# ../bwx11-20261115/bwx11), with nm only. It does not run them.` | Comment: ... default `../bwx11-20261115/bwx11`. The script reads them with the tool `nm` only and does not run them. `nm` lists the symbols of a binary with their addresses. A missing file does not stop the script (lines 125 to 127, lines 137 to 139 and lines 149 to 151). |

### Shell options, marker check and CPU limit (lines 30 to 34)

| Line | Source | Explanation |
|---:|---|---|
| 30 | `set -euo pipefail` | `set -euo pipefail` sets three rules for the whole script. `-e`: the script ends when a command fails. A command that `if` tests, or that `\|\|` follows, does not end it. The form `$( )` runs commands and inserts their output. A failed command inside `$( )` ends the script only when the `$( )` is the whole right side of an assignment (line 64). It does not end the script when the `$( )` stands inside an `echo` text (line 41) or a `for` list (line 62). Bash also turns `-e` off inside `$( )`, and every call of `placement` stands inside `$( )`. So a failed `nm` (line 109) does not end the script. `-u`: the script ends when it uses a variable that was never set. `-o pipefail`: a pipeline counts as failed when any of its commands fails, not only the last one. |
| 31 | `MARKER=${BWX_MARKER:-/tmp/positron-perf.RUNNING}   # BWX_MARKER: only for a test of this check` | `MARKER`: the path of the marker file. `${BWX_MARKER:-...}` takes the value of the environment variable `BWX_MARKER` when it is set and not empty. If not, the path is `/tmp/positron-perf.RUNNING`. Another user creates this file during a performance test [Ref18]. Comment: `BWX_MARKER` is only for a test of this check. |
| 32 | `check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }` | Defines the function `check_marker`. `[[ -e $MARKER ]]` tests whether the marker file exists. If it exists, the function prints `RUNNING file present: stop` to the error output (`>&2`) and ends the script with exit status 3. |
| 33 | `check_marker` | The first call of `check_marker`, before the script does anything else. Line 50 and line 61 call it again, each time before the script runs the new binary. |
| 34 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c "${BWX_CPUS:-0-119}" "$0" "$@"; fi` | CPU limit: the script restarts itself under `taskset`. `[[ -z ${_PINNED:-} ]]` is true when the variable `_PINNED` is not set or empty. On the first pass that is the case, so the `if` branch runs. `exec` replaces the shell with `taskset`, and `taskset` starts this script again (`$0`) with the same arguments (`$@`). `taskset -c 0-119` limits a program to the CPUs 0 to 119. `bwx12.c` names this range as the rule of the test machine [Ref8]. `_PINNED=1` goes into the environment of the new run. The new run starts at the first line again, so the marker check of line 33 runs a second time. Then it skips the `if` branch and continues with line 35. Every program that the script starts later inherits the limit: the compiler, the new binary, `objdump` and `nm`. The list is the value of the environment variable `BWX_CPUS`, or `0-119` when `BWX_CPUS` is not set or empty. If `_PINNED` is already set and not empty at the start, the script does not restart, and it sets no CPU limit. `taskset` must be able to execute `$0`. After a start as `bash build12.sh`, `$0` has no folder part, and `taskset` looks for the name in the search path only. If it finds no such program, the run ends with the exit status of `taskset` (127 in a test of this construct with a small script). |

### Folder of the script, compiler and compiler flags (lines 35 to 37)

| Line | Source | Explanation |
|---:|---|---|
| 35 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC`: the absolute path of the folder that holds this script. `dirname "$0"` gives the folder part of the path of the script. `cd` goes to that folder, and `pwd` prints its full path. Both run inside `$( )`, so the working folder of the script itself does not change. |
| 36 | `CC=${CC:-gcc}` | `CC`: the compiler. It is the environment variable `CC` if that is set and not empty, otherwise `gcc`. The CRB build used gcc 14.2.0 [Ref1]. The CRB build is the run of this script on CRB on 2026-11-15 that built the binary of the whole-chip test. |
| 37 | `CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4"` | `CFLAGS`: the ten compiler flags. The same gcc 14.2.0 built `bw_old` and `bw_new` with the first seven flags and without the last three [Ref15] [Ref16]. `-O3`: the highest numbered optimization level of gcc. The compiler may inline functions and vectorize loops [Ref17]. In the CRB build the 16 sums of the old read kernel are 8 vector adds per loop pass of `k_oldread` [Ref3]. `-march=native`: gcc picks the architecture of the build machine, here CRB. The architecture decides which instructions gcc may use [Ref22]. Example: the machine code of `timed_sequence` holds SVE instructions (SVE is a vector extension of Arm) [Ref4]. The line has no `-mtune` and no `-mcpu`. By the gcc manual the code is then tuned to perform well on a range of processors of that architecture [Ref22]. `-fno-tree-loop-distribute-patterns`: gcc does not turn a loop pattern into a call of a library function [Ref17]. A store loop that becomes a call of `memset` is such a pattern. In the CRB build `k_oldwrite` and `k_oldcopy` are loops, and no kernel calls a library function for its work [Ref3]. `-pthread`: support for POSIX threads, which `bwx12` uses for its benchmark threads [Ref8]. `-Wall -Wextra`: most warnings of the compiler, and some more [Ref17]. A warning does not stop the build. It goes into `build.txt` (line 47). The CRB build has none [Ref1]. `-std=gnu11`: C of the 2011 standard with the GNU extensions [Ref17]. The row of line 43 explains the last three flags. |

### Record `build.txt`: the first lines, and the compiler call (lines 38 to 48)

| Line | Source | Explanation |
|---:|---|---|
| 38 | `b=bwx12` | `b`: the name of the binary, `bwx12`. |
| 39 | `B="$SRC/build.txt"` | `B`: the path of the record `build.txt` in the folder of the script. |
| 40 | `{` | Starts a group of commands. Line 45 sends the output of the whole group to `build.txt`. |
| 41 | `  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who \| wc -l)"` | The group of lines 40 to 45 writes four lines. This is the first line of the record: `## host=... utc=... load_before=... logins=...`. `hostname` gives the host name. `date -u +%FT%TZ` gives the UTC time at the start, in the form `2026-11-15T17:12:11Z`. `cut -d' ' -f1-3 /proc/loadavg` takes fields 1 to 3 of that file: the load averages of the last 1, 5 and 15 minutes. `who \| wc -l` counts the lines that `who` prints, one line per login session. CRB build: host `ubuntu`, start at 17:12:11 UTC on 2026-11-15, load averages 1.18, 28.51 and 31.03 tasks (1, 5 and 15 minutes), 0 logins [Ref1]. |
| 42 | `  echo "## cc=$($CC --version \| head -1)"` | The second line of the record: `## cc=` and the first line of the version text of the compiler. `head -1` keeps that first line. |
| 43 | `  echo "## CFLAGS=$CFLAGS"` | The third line of the record: `## CFLAGS=` and the ten flags of line 37. The row of line 37 explains the first seven. The last three are these. `-fno-ipa-icf`: gcc does not merge two functions that have identical code [Ref17]. `bwx12.c` holds kernels that are one source under two names, for example `oldread` and `oldread2`. With this flag gcc keeps both [Ref8]. `-fno-toplevel-reorder`: gcc writes the functions and the top-level `asm` statements into the binary in the order of the source file [Ref17]. `bwx12.c` needs this for its macro `PLACE`, which puts padding bytes directly before a kernel [Ref8]. `-falign-functions=4`: gcc aligns the start of a function to 4 bytes only. Then a kernel starts directly after the pad of `PLACE`, at the planned address modulo 64 [Ref8]. |
| 44 | `  echo "## compiler messages:"` | A title line of the record: `## compiler messages:`. The messages of the compiler follow it. |
| 45 | `} > "$B"` | Ends the group of line 40. `>` writes the output of the group to `build.txt` and replaces an older `build.txt`. |
| 46 | `# shellcheck disable=SC2086` | Comment for the checking tool `shellcheck`: do not warn about rule `SC2086` in the next line. That rule asks for double quotes around a variable. The quotes would stop the shell from splitting the value into words. `$CFLAGS` in the compiler call below has no quotes on purpose. |
| 47 | `$CC $CFLAGS -o "$SRC/$b" "$SRC/bwx12.c" >> "$B" 2>&1 \|\| { echo "build of $b failed: $B" >&2; cat "$B" >&2; exit 5; }` | The compiler builds `bwx12.c` into the binary `bwx12` in the folder of the script (`-o` names the output file). `bwx12.c` includes `bwx12_selftest.c` with `#include`, so one compiler call is enough [Ref8]. `$CFLAGS` has no quotes: the shell must split it into single flags. `>> "$B" 2>&1` appends every message of the compiler to `build.txt`: `>>` appends the standard output, and `2>&1` sends the error output to the same place. A warning of the compiler does not stop the build. If the compiler fails, the part after `\|\|` runs. It prints `build of bwx12 failed:` and the path of `build.txt` to the error output, then the content of `build.txt`, and ends the script with exit status 5. |
| 48 | `echo "## compiler messages end" >> "$B"` | Appends the line `## compiler messages end` to `build.txt`. CRB build: nothing stands between the two `compiler messages` lines, so the compiler printed no warning [Ref1]. |

### Self-test of the new binary (lines 49 to 55)

| Line | Source | Explanation |
|---:|---|---|
| 50 | `check_marker` | Checks the marker file again (line 32). Line 51 is the first run of the new binary. |
| 51 | `if "$SRC/$b" --selftest > "$SRC/selftest-$b.txt" 2>&1; then` | Runs `bwx12 --selftest`, the self-test of the new binary, and tests its exit status. The whole output goes to `selftest-bwx12.txt` (`2>&1` adds the error output). The self-test calls each of the 55 kernels on buffers of 1 page, 3 pages and 1 MiB, and on single blocks of 256 B. Before each of these calls it prints a line that begins with `call,`. After each call it checks the memory. Then it tests the trial mode. Each check prints one row that ends with `pass` or `FAIL` [Ref9]. Limit: for a read kernel that returns nothing, the self-test shows that the buffer is unchanged and that the kernel touches every page of a 3-page range. It does not show that the kernel reads every byte [Ref9]. In the CRB build the rows of `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` hold these two kinds of check only. The rows of `oldread` also hold the check that the returned sum equals the sum of all words [Ref5]. |
| 52 | `  echo "## selftest $b exit=0 $(tail -1 "$SRC/selftest-$b.txt")" >> "$B"` | Exit status 0: appends `## selftest bwx12 exit=0` plus the last line of the self-test output (`tail -1`) to `build.txt`. CRB build: that last line is `# failures=0`, and 457 rows end with `pass` [Ref1] [Ref5]. |
| 53 | `else` | The other branch: the self-test ended with a status other than 0. |
| 54 | `  echo "## selftest $b exit=$?" >> "$B"; echo "selftest of $b failed: $SRC/selftest-$b.txt" >&2; tail -3 "$SRC/selftest-$b.txt" >&2; exit 4` | Appends the line `## selftest`, the name of the binary and `exit=N` to `build.txt`. N is the exit status of the self-test (`$?`). Then the line prints `selftest of`, the name of the binary, `failed:` and the path of the output file to the error output. `tail -3` prints the last 3 lines of the self-test output there too. `exit 4` ends the script with exit status 4. |
| 55 | `fi` | Ends the `if` of line 51. |

### Records `listing.txt` and `offsets.tsv`: machine code of every kernel (lines 56 to 75)

| Line | Source | Explanation |
|---:|---|---|
| 57 | `# Machine code of every kernel. The loop start is the target of the first` | Comment: the next block saves the machine code of every kernel. It also defines the loop start of a kernel: the target of the first branch of the function ... |
| 58 | `# branch of the function that goes backward to an address inside it.` | Comment: ... that goes backward to an address inside the function (lines 69 to 71). |
| 59 | `: > "$SRC/listing.txt"` | Empties `listing.txt`: the command `:` does nothing, and `>` creates the file or makes it empty (0 bytes). |
| 60 | `printf 'binary\tkernel\tfunction\tstart\tloop_start\tloop_mod64\n' > "$SRC/offsets.tsv"` | Writes the header line of `offsets.tsv`: six column names with tabs between them (`\t`). `>` replaces an older file. |
| 61 | `check_marker   # the next line runs the binary again` | Checks the marker file again (line 32). Comment: the next line runs the binary once more. |
| 62 | `for k in $("$SRC/$b" --list); do` | `bwx12 --list` prints the names of all kernels, one per line (55 in the CRB build [Ref2]). The loop runs once per name `k`. A failed `--list` run does not end the script (line 30). The loop then runs over the names that the binary printed before it failed. In the CRB build the loop got every name. The first line of the self-test output gives `kernels=55`. `offsets.tsv` has 55 kernel rows [Ref2] [Ref5]. |
| 63 | `  fn=k_$k` | `fn`: the function of the kernel: `k_` plus the kernel name. |
| 64 | `  text=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b" \| sed -n '/>:$/,/^$/p')` | `text`: the machine code of this one function as assembler text. `objdump -d --disassemble=$fn` prints the code of the function `fn` and stops at the end of the function. `--no-show-raw-insn` leaves out the bytes of each instruction. `sed -n '/>:$/,/^$/p'` keeps the lines from the label line of the function (it ends with `>:`) to the next empty line. This drops the header that `objdump` prints first. A failed `objdump` ends the script (line 30). |
| 65 | `  { echo "=== $b $k ==="; echo "$text"; echo; } >> "$SRC/listing.txt"` | Appends three things to `listing.txt`: the title line `=== bwx12 <kernel> ===`, the text of the function, and an empty line. The listing holds the six kernels of the whole-chip test: `oldread`, `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` [Ref3]. |
| 66 | `  start=$(sed -n '1s/^0*\([0-9a-f]\+\) .*/\1/p' <<< "$text"); loop=NA; mod=NA` | `start`: the address on the label line, which is the first line of `text`, without leading zeros. `sed` works on that line only: it replaces the line by the hexadecimal digits that follow the leading zeros and prints it. `<<<` gives the content of `text` to `sed` as its input. `loop` and `mod` begin as `NA`. |
| 67 | `  while read -r addr rest; do` | Starts a loop over the instruction lines that line 73 gives. `read` puts the first word of a line, an address with a colon, into `addr` and the rest of the line into `rest`. `-r` keeps each backslash as it is. |
| 68 | `    addr=${addr%:}` | Removes the colon at the end of `addr` (`${addr%:}`). |
| 69 | `    if [[ $rest =~ ([0-9a-f]+)\ \<$fn(\+0x[0-9a-f]+)?\> ]]; then` | Looks for a branch to a place inside the same function. `=~` tests `rest` against a regular expression: hexadecimal digits, one space, and the function name in angle brackets, with or without an offset such as `+0x4`. `objdump` prints such a target as an address and a name. The listing of the CRB build (`listing.txt`) holds for example `49a4 <k_read+0x4>` [Ref3]. Group 1 holds the address. |
| 70 | `      tgt=${BASH_REMATCH[1]}` | `tgt`: the target address, taken from group 1 of the match (`BASH_REMATCH[1]`). |
| 71 | `      if (( 16#$tgt < 16#$addr && 16#$tgt >= 16#$start )); then loop=$tgt; mod=$(( 16#$tgt % 64 )); break; fi` | Compares the addresses as numbers. `(( ))` computes with numbers, and `16#` marks a hexadecimal number. The branch goes backward when the target is lower than the address of the branch instruction and not lower than `start`. Then `loop` is the target, `mod` is the target modulo 64 as a decimal number, and `break` ends the search. So the loop start is the target of the first backward branch. If a function had two loops, only the first would be recorded. In the CRB build each of the 55 kernel functions holds exactly one backward branch to an address inside the function [Ref3]. |
| 72 | `    fi` | Ends the `if` of line 69. |
| 73 | `  done < <(tail -n +2 <<< "$text" \| grep -E '^ *[0-9a-f]+:')` | Ends the loop of line 67 and gives it its input. `tail -n +2` prints `text` from its second line on. `grep -E` keeps every line that begins with a hexadecimal address and a colon, with or without spaces before the address. These are the instruction lines. `< <( )` runs the two commands and feeds their output to the loop. The loop itself runs in the shell of the script, so `loop` and `mod` keep their values after it. |
| 74 | `  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$b" "$k" "$fn" "$start" "$loop" "$mod" >> "$SRC/offsets.tsv"` | Appends one row per kernel to `offsets.tsv`, with tabs between the six fields. `binary`: always `bwx12`. `kernel`: the kernel name. `function`: `k_` plus that name. `start`: the address of the first instruction of the function, hexadecimal. `loop_start`: the address of the first instruction of the loop, hexadecimal. It is `NA` when the function has no backward branch. `loop_mod64`: `loop_start` modulo 64, a decimal number of bytes from 0 to 63. It is the offset of the loop start inside a 64-byte block of code. CRB build: `oldread` has `start` 4600, `loop_start` 4668 (both hexadecimal) and `loop_mod64` 40 bytes. `read` has 49a0, 49a4 and 36 bytes. `asmread` has 4ac0, 4ad4 and 20 bytes. No row holds `NA` [Ref2]. |
| 75 | `done` | Ends the loop of line 62. |

### Check with exit status 6: branch targets of the timed functions of the trial mode (lines 76 to 99)

| Line | Source | Explanation |
|---:|---|---|
| 77 | `# Branch targets of timed_sequence() and of timed_sequence_hot() that lie` | Comment: the next block lists the branch targets of the functions `timed_sequence` and `timed_sequence_hot` ... A branch target is the address that a branch or call instruction goes to. Both functions belong to the trial mode of bwx12 (option `--trial`). They time the windows of a trial [Ref8]. |
| 78 | `# outside the function (design, Stage 1 item 4: no warm-up, page read, output` | Comment: ... that lie outside the function. The reason is item 4 of Stage 1 of the design: no warm-up, page read, output ... A page read is a read of the page state of a buffer from Linux. The function `read_smaps` of `bwx12.c` does it [Ref8]. The whole-chip test does not use the trial mode. Its spec files start bwx12 with `--seq`. Then the function `worker` of `bwx12.c` times each interval [Ref8] [Ref13]. So this check does not cover the timed path of the whole-chip test. This script does not save the machine code of `worker`. |
| 79 | `# or barrier can enter the timed path). Allowed: clock_gettime, the kernels` | Comment: ... or barrier can enter the timed path. A barrier is a point at which a thread waits for the other threads. The list of the allowed targets starts: `clock_gettime`, which is the clock read, and the kernels ... |
| 80 | `# (an indirect call), tcount (the counter read of count "read") and the` | Comment: ... which are called through a function pointer (an indirect call). Also allowed: `tcount`, a function of the runner source, the C file that this script compiles. It reads the event counters when a trial has the count setting `read`. The last allowed target is the ... |
| 81 | `# stack-guard failure. A helper that is not inlined shows as its own name and` | Comment: ... stack-guard failure function `__stack_chk_fail`. Check code that the compiler adds to a function calls it when the guard value on the stack was overwritten. A helper function that gcc did not inline shows under its own name and ... |
| 82 | `# is rejected. Both functions are listed before the script decides.` | Comment: ... is rejected. Both functions are listed before the script decides: line 99 ends the script only after the loop of lines 85 to 98. |
| 83 | `: > "$SRC/seq-listing.txt"` | Empties `seq-listing.txt`, in the same way as line 59. |
| 84 | `seq_fail=0` | `seq_fail=0`: no function has failed yet. |
| 85 | `for fn in timed_sequence timed_sequence_hot; do` | The loop runs once for each of the two functions. `fn` is the name of the function. |
| 86 | `  code=$(objdump -d --no-show-raw-insn --disassemble=$fn "$SRC/$b")` | `code`: the whole `objdump` output for the function, with the header lines. The flags are the flags of line 64. |
| 87 | `  { echo "=== $b $fn ==="; sed -n '/>:$/,/^$/p' <<< "$code"; echo; } >> "$SRC/seq-listing.txt"` | Appends three things to `seq-listing.txt`: a title line (`===`, the name of the binary, the name of the function, `===`), the text of the function from its label line to the next empty line, and an empty line. Apart from the checksum of line 155, no script reads `seq-listing.txt` (line 21): it is for a person to read. |
| 88 | `  seq_calls=$(awk -v self="$fn" '` | `seq_calls`: the places outside the function that the function calls or branches to, each with a count. The pipeline of lines 88 to 92 builds it. `awk -v self="$fn"` gives the function name to the `awk` program as the variable `self`. The single quote starts the text of the program. |
| 89 | `    $1 !~ /^[0-9a-f]+:$/ { next }` | First `awk` rule: skip every line whose first field is not a hexadecimal address with a colon. So only instruction lines reach the next rules. |
| 90 | `    /[ \t](call\|jmp)q?[ \t]+\*/ \|\| $2 == "blr" \|\| $2 == "br" { print "(indirect)"; next }` | Second rule: an indirect call or jump prints `(indirect)`, and `next` goes to the next line. On Arm these are the instructions `blr` (call) and `br` (jump) in field 2. Both go to the address in a register. The first pattern (`call` or `jmp`, then a `*`) matches the x86 forms. |
| 91 | `    $2 ~ /^(callq?\|jmpq?\|j[a-z]+\|bl\|b\|b\.[a-z]+\|cbn?z\|tbn?z)$/ && $NF ~ /^<.*>$/ {` | Third rule, the condition: field 2 is a call or branch instruction, and the last field (`$NF`) is a name in angle brackets. The list holds x86 names (`call`, `jmp`, `j` plus letters) and Arm names: `bl` (call), `b` (branch), `b.` plus a condition, and `cbz`, `cbnz`, `tbz`, `tbnz` (branches that test a register or one bit). `objdump` adds a comment such as `// b.any` after some conditional branches. Then the last field is not a name, and the rule skips the line. In the saved listing every such branch stays inside its own function [Ref4]. That listing is the file `seq-listing.txt` of the CRB build. A name with an offset looks there like `<timed_sequence+0x2c0>` [Ref4]. |
| 92 | `      t = $NF; gsub(/^<\|>$\|\+0x[0-9a-f]+>$\|@plt/, "", t); if (t != self) print t }' <<< "$code" \| LC_ALL=C sort \| uniq -c \| awk '{ printf "%s%s=%s", (NR > 1 ? " " : ""), $2, $1 }')` | Third rule, the action: `t` is the last field. `gsub` removes the angle brackets, an offset (`+0x` and hexadecimal digits before the closing bracket), and the text `@plt`. The name is printed unless it is the name of the function itself (`self`). So a branch inside the function does not count. The single quote ends the program, and `<<< "$code"` gives it the `objdump` text as input. `LC_ALL=C sort` sorts the names, and `uniq -c` counts each name. `LC_ALL=C` makes `sort` compare plain byte values. The last `awk` joins the names into one line of `name=count` pairs with one space between them. |
| 93 | `  echo "## $fn branch targets: ${seq_calls:-none}" >> "$B"` | Appends the list to `build.txt` as `## <function> branch targets: ...`. An empty list is written as `none` (`${seq_calls:-none}`). CRB build, the same for both functions: `(indirect)=4 __stack_chk_fail=1 clock_gettime=2 tcount=2`. Each number counts the instructions that go to that target [Ref1]. |
| 94 | `  seq_bad=$(tr ' ' '\n' <<< "$seq_calls" \| sed 's/=[0-9]*$//' \| grep -vxE 'clock_gettime\|\(indirect\)\|tcount\|__stack_chk_fail' \|\| true)` | `seq_bad`: the names that are not allowed. `tr` puts each `name=count` pair on its own line, and `sed` removes `=count`. `grep -vxE` keeps the lines that are not exactly one of the four allowed names. `\|\| true` stops the rule `-e` from ending the script when `grep` keeps no line (`grep` then returns status 1). |
| 95 | `  if [[ -n $seq_bad \|\| $seq_calls != *"clock_gettime="* \|\| $seq_calls != *"(indirect)="* ]]; then` | A function fails in three cases: `seq_bad` holds a name (`-n` tests for a text that is not empty), the list has no `clock_gettime=` entry, or the list has no `(indirect)=` entry. In the last two cases the function would not read the clock or would not call a kernel. |
| 96 | `    echo "$fn of $b: branch targets '${seq_calls:-none}'; not allowed or missing: ${seq_bad:-clock_gettime or the kernel call}" >&2; seq_fail=1` | On failure: prints the function name, the list and the reason to the error output. The reason is the content of `seq_bad`, or the text `clock_gettime or the kernel call` when `seq_bad` is empty. Then `seq_fail=1` records the failure. The loop still handles the second function, so `seq-listing.txt` and `build.txt` hold both. |
| 97 | `  fi` | Ends the `if` of line 95. |
| 98 | `done` | Ends the loop of line 85. |
| 99 | `if (( seq_fail )); then exit 6; fi` | Ends the script with exit status 6 if a function failed. `(( seq_fail ))` is true when the number is not 0. In that case `build.txt` gets no placement lines and no sha256 lines. |

### Function `placement`: where five functions start, modulo 64 (lines 100 to 112)

| Line | Source | Explanation |
|---:|---|---|
| 101 | `# Placement of the timed path: the start modulo 64 of call(), read_smaps(),` | Comment: the next block records the placement of the timed path: the start address modulo 64 of the functions `call`, `read_smaps` ... The address modulo 64 is the remainder when the address is divided by 64. It is the offset inside a 64-byte block of code, from 0 to 63 bytes. |
| 102 | `# tcount() and the two timed functions (a function that gcc inlined everywhere` | Comment: ... `tcount` and the two timed functions. The comment adds that a function which gcc inlined everywhere ... |
| 103 | `# has no symbol and is left out). bwx12.c pads after its new kernels so that` | Comment: ... has no symbol and is left out. The row of line 115 reports a test in which gcc kept the symbol of such a function. The comment goes on: `bwx12.c` adds padding after its new kernels. The goal is ... |
| 104 | `# the functions from call() to timed_sequence_hot() start where they start in` | Comment: ... that the functions from `call` to `timed_sequence_hot` start at the same address modulo 64 as in ... |
| 105 | `# bwx11 and bwx10, modulo 64 (and up to timed_sequence() as in bwx8). This is a record,` | Comment: ... bwx11 and bwx10, and the functions up to `timed_sequence` as in bwx8 [Ref8]. The result is a record ... |
| 106 | `# not a gate: a difference does not stop the build.` | Comment: ... and not a condition: a difference does not stop the build. |
| 107 | `placement() {` | Starts the function `placement`. `placement FILE` prints one line of `name=value` pairs for a binary: where five functions start, modulo 64. |
| 108 | `  local out` | `out`: a variable that exists only inside the function. |
| 109 | `  out=$(nm "$1" 2>/dev/null \| awk '$3 ~ /^(call\|read_smaps\|tcount\|timed_sequence\|timed_sequence_hot)$/ { print $3, $1 }' \| LC_ALL=C sort \|` | `nm` lists the symbols of the binary `$1` with their addresses. `2>/dev/null` hides its error messages. `awk` keeps the symbols with the names `call`, `read_smaps`, `tcount`, `timed_sequence` and `timed_sequence_hot` (field 3) and prints the name and the address (field 1). `LC_ALL=C sort` sorts the lines by name. `LC_ALL=C` makes `sort` compare plain byte values. The pipeline goes on in line 110. |
| 110 | `    while read -r name addr; do printf '%s=%d ' "$name" $(( 16#$addr % 64 )); done)` | The `while` loop prints each name with its address modulo 64, in decimal. `16#` reads the address as a hexadecimal number. The value is the offset of the function start inside a 64-byte block, in bytes. The closing parenthesis ends the `$( )` of line 109. |
| 111 | `  echo "${out% }"` | Prints the result without the space at its end (`${out% }`). |
| 112 | `}` | Ends the function `placement`. |

### Placement record and comparison with the older binaries (lines 113 to 151)

| Line | Source | Explanation |
|---:|---|---|
| 113 | `BWX8_BIN=${BWX8_BIN:-$SRC/../bwx8-20261114/bwx8}` | `BWX8_BIN`: the path of the accepted binary of bwx8. The value of the environment variable is kept when it is set and not empty. The default is the file `bwx8` in the folder `bwx8-20261114`, which stands beside the folder of this script. |
| 114 | `p12=$(placement "$SRC/$b")` | `p12`: the placement line of the new binary. |
| 115 | `echo "## placement $b (start modulo 64): ${p12:-none}" >> "$B"` | Appends the placement line of the new binary to `build.txt` (`none` if it is empty). CRB build: `call=24 read_smaps=52 tcount=52 timed_sequence=28 timed_sequence_hot=32` [Ref1]. For example, `call` starts 24 bytes after a 64-byte boundary. A name in this line shows that the binary holds a symbol for the function. It does not show that any code calls it. In a test, gcc 11.4.0 with `-O3 -fno-toplevel-reorder` kept the symbol of a `static` function that it had inlined at its only call [Ref21]. So with that compiler the rule of the comment of lines 102 to 103 does not hold for every function. The CRB compiler (gcc 14.2.0) was not tested. |
| 116 | `if [[ -f $BWX8_BIN ]]; then` | Tests whether the bwx8 binary exists as a regular file (`-f`). |
| 117 | `  p8=$(placement "$BWX8_BIN")` | `p8`: the placement line of the bwx8 binary. |
| 118 | `  echo "## placement bwx8 (start modulo 64): ${p8:-none}" >> "$B"` | Appends the placement line of bwx8 to `build.txt` (`none` if it is empty). |
| 119 | `  # timed_sequence_hot does not exist in bwx8; it sorts last` | Comment: bwx8 has no function `timed_sequence_hot`, and this name is the last one in the sorted line. |
| 120 | `  if [[ -n $p8 && $(sed 's/ timed_sequence_hot=[0-9]*$//' <<< "$p12") == "$p8" ]]; then` | So `sed` removes the pair of `timed_sequence_hot` from the end of the line of the new binary, and the rest is compared with the bwx8 line as text. The test also needs a bwx8 line that is not empty (`-n`). |
| 121 | `    echo "## placement up to timed_sequence against bwx8: same" >> "$B"` | Equal: appends a result line that ends with `same`. CRB build: `same` [Ref1]. |
| 122 | `  else` | The other branch: the two texts differ, or the bwx8 line is empty. |
| 123 | `    echo "## placement up to timed_sequence against bwx8: DIFFERS" >> "$B"` | Appends a result line that ends with `DIFFERS`. An empty bwx8 line also gives `DIFFERS`. The script goes on. |
| 124 | `  fi` | Ends the `if` of line 120. |
| 125 | `else` | The other branch of line 116: the bwx8 file is missing. |
| 126 | `  echo "## placement against bwx8: not compared (no file $BWX8_BIN)" >> "$B"` | Appends a line with the words `not compared` and the path of the missing file. |
| 127 | `fi` | Ends the `if` of line 116. |
| 128 | `BWX10_BIN=${BWX10_BIN:-$SRC/../bwx10-20261115/bwx10}` | `BWX10_BIN`: the path of the accepted binary of bwx10. The default is the file `bwx10` in the folder `bwx10-20261115` beside the folder of this script. Lines 129 to 139 repeat the steps of lines 116 to 127 for this binary. |
| 129 | `if [[ -f $BWX10_BIN ]]; then` | Tests whether the bwx10 binary exists as a regular file. |
| 130 | `  p10=$(placement "$BWX10_BIN")` | `p10`: the placement line of the bwx10 binary. |
| 131 | `  echo "## placement bwx10 (start modulo 64): ${p10:-none}" >> "$B"` | Appends the placement line of bwx10 to `build.txt` (`none` if it is empty). |
| 132 | `  if [[ -n $p10 && $p12 == "$p10" ]]; then` | Compares the two whole lines as text. The bwx10 line must not be empty. The bwx10 line of the CRB build has all five functions [Ref1]. |
| 133 | `    echo "## placement up to timed_sequence_hot against bwx10: same" >> "$B"` | Equal: appends a result line that ends with `same`. CRB build: `same` [Ref1]. |
| 134 | `  else` | The other branch: the two lines differ, or the bwx10 line is empty. |
| 135 | `    echo "## placement up to timed_sequence_hot against bwx10: DIFFERS" >> "$B"` | Appends a result line that ends with `DIFFERS`. The script goes on. |
| 136 | `  fi` | Ends the `if` of line 132. |
| 137 | `else` | The other branch of line 129: the bwx10 file is missing. |
| 138 | `  echo "## placement against bwx10: not compared (no file $BWX10_BIN)" >> "$B"` | Appends a line with the words `not compared` and the path of the missing file. |
| 139 | `fi` | Ends the `if` of line 129. |
| 140 | `BWX11_BIN=${BWX11_BIN:-$SRC/../bwx11-20261115/bwx11}` | `BWX11_BIN`: the path of the accepted binary of bwx11. The default is the file `bwx11` in the folder `bwx11-20261115` beside the folder of this script. Lines 141 to 151 repeat the same steps for this binary. |
| 141 | `if [[ -f $BWX11_BIN ]]; then` | Tests whether the bwx11 binary exists as a regular file. |
| 142 | `  p11=$(placement "$BWX11_BIN")` | `p11`: the placement line of the bwx11 binary. |
| 143 | `  echo "## placement bwx11 (start modulo 64): ${p11:-none}" >> "$B"` | Appends the placement line of bwx11 to `build.txt` (`none` if it is empty). |
| 144 | `  if [[ -n $p11 && $p12 == "$p11" ]]; then` | Compares the two whole lines as text. The bwx11 line must not be empty. |
| 145 | `    echo "## placement up to timed_sequence_hot against bwx11: same" >> "$B"` | Equal: appends a result line that ends with `same`. CRB build: `same` [Ref1]. So in the CRB build the five functions of bwx12 start at the same offsets as in bwx10 and bwx11, and the first four at the same offsets as in bwx8. |
| 146 | `  else` | The other branch: the two lines differ, or the bwx11 line is empty. |
| 147 | `    echo "## placement up to timed_sequence_hot against bwx11: DIFFERS" >> "$B"` | Appends a result line that ends with `DIFFERS`. The script goes on. |
| 148 | `  fi` | Ends the `if` of line 144. |
| 149 | `else` | The other branch of line 141: the bwx11 file is missing. |
| 150 | `  echo "## placement against bwx11: not compared (no file $BWX11_BIN)" >> "$B"` | Appends a line with the words `not compared` and the path of the missing file. |
| 151 | `fi` | Ends the `if` of line 141. |

### Last records: sha256 values, load and end time, printed output (lines 152 to 160)

| Line | Source | Explanation |
|---:|---|---|
| 153 | `{` | Starts a group of commands. Line 157 appends the output of the whole group to `build.txt`. |
| 154 | `  echo "## sha256:"` | The title line `## sha256:`. |
| 155 | `  (cd "$SRC" && sha256sum bwx12.c bwx12_selftest.c build12.sh $b listing.txt offsets.tsv seq-listing.txt)` | One line per file from `sha256sum`: the sha256 value (a checksum of 64 hexadecimal digits) and the file name. `cd` goes to the folder of the script first, so the names carry no path. The parentheses limit this `cd` to the one command line. The seven files are `bwx12.c`, `bwx12_selftest.c`, this script, the binary, `listing.txt`, `offsets.tsv` and `seq-listing.txt`. `build.txt` and `selftest-bwx12.txt` get no line. CRB build: the value of the binary begins with `cd58e564` [Ref1]. `go.sh` of the whole-chip test holds the full value and passes it to `rx.sh`. Both scripts check it and do not start a `bwx12` file with another value [Ref11] [Ref12]. |
| 156 | `  echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)"` | The line `## load_after=... utc=...`: the three load averages and the UTC time at the end, read in the same way as in line 41. CRB build: end at 17:12:14 UTC, 3 s after the start, with load averages 1.17, 28.05 and 30.86 tasks [Ref1]. |
| 157 | `} >> "$B"` | Ends the group of line 153. `>>` appends its output to `build.txt`. |
| 158 | `cat "$B"` | Prints `build.txt` to the standard output. |
| 159 | `echo "## offsets.tsv:"` | Prints the title line `## offsets.tsv:`. |
| 160 | `cat "$SRC/offsets.tsv"` | Prints `offsets.tsv` to the standard output. For the CRB build the file `build.out` in the folder `crb-build-1` holds the text of lines 158 to 160: the 24 lines of `build.txt`, the title line, and the 56 lines of `offsets.tsv` [Ref6]. |

## References

- [Ref1] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.txt`: The record that this script wrote on CRB on 2026-11-15, 24 lines. Line 1: host, start time, load, logins. Line 2: gcc 14.2.0. Line 3: flags. Lines 4 and 5: no compiler message between them. Line 6: self-test result. Lines 7 and 8: branch targets. Lines 9 to 15: placement lines and comparisons. Lines 16 to 23: sha256 values. Line 24: load and end time.
- [Ref2] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/offsets.tsv`: The table of the CRB build: 1 header line and 55 kernel rows. Line 2 `read`, line 5 `asmread`, line 8 `oldread`. No row holds `NA`.
- [Ref3] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/listing.txt`: The machine code of the 55 kernels of the CRB build. The six kernels of the whole-chip test begin at line 1 (`read`), 59 (`asmread`), 133 (`oldread`), 754 (`read_1pl`), 854 (`read_nop96`) and 2126 (`read_nop256`). Lines 161 to 176: the loop of `k_oldread` with 4 `ldp` loads and 8 vector adds. Lines 206 to 234: `k_oldwrite` and `k_oldcopy` with a backward branch each. The only call of a library function in the file is `__stack_chk_fail`, in `k_oldread` and `k_oldread2`. Checked in this task with a script that applies the rule of lines 69 to 71 of `build12.sh`: each of the 55 functions holds exactly one backward branch to an address inside the function.
- [Ref4] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/seq-listing.txt`: The machine code of `timed_sequence` (from line 1) and `timed_sequence_hot` (from line 310) of the CRB build. Line 21 holds the SVE instruction `cntb`. Checked in this task: the 48 branch lines with a trailing comment all have a target inside their own function.
- [Ref5] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/selftest-bwx12.txt`: The self-test output of the CRB build, 852 lines. Line 1 holds `kernels=55`. The 852 lines are: 2 comment lines, 393 lines that begin with `call,`, and 457 rows that end with `pass`. The last line is `# failures=0`. The kernels `read`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl` have 8 rows each: 3 rows with the check `buffer unchanged`, 2 rows with a check that ends with `page unchanged`, and 3 rows with a check that begins with `faults in page`. `oldread` has these 8 rows and 3 rows with the check `returned sum equals the sum of all words`.
- [Ref6] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/build.out`: The standard output of the CRB build, 81 lines. Checked in this task with `diff`: lines 1 to 24 equal `build.txt`, line 25 is `## offsets.tsv:`, lines 26 to 81 equal `offsets.tsv`.
- [Ref7] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/crb-build-1/check_listing12.out`: The saved output of `check_listing12.py` for the CRB build. Line 58: `kernels=29 failed_rows=0 new_kernels=26 new_failed_rows=0`. Lines 2, 5, 8, 27 and 29: `read`, `asmread`, `oldread`, `read_1pl` and `read_nop96` with text `same`. Line 40: `read_nop256` with loop `expected`.
- [Ref8] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12.c`: The source of the runner. Lines 3 to 7, 36 to 42 and 62 to 68: each version is the version before plus additions. Lines 90 to 94: interval mode (`--seq`) and trial mode (`--trial`). Lines 134 to 140: CPUs 0 to 119 are the rule of the test machine. Lines 142 to 163: `PLACE` needs `-fno-toplevel-reorder` and `-falign-functions=4`. Lines 454 to 459: `-fno-ipa-icf` keeps a kernel and its copy under a second name. Lines 1440 to 1449: the pad after the new kernels. Line 1491: `call`. Line 1515: `read_smaps`. Line 112: `#include <pthread.h>`. Line 3012: `pthread_create` starts each `worker` thread. Lines 1632 to 1735: `worker`. Lines 1688 to 1701: the timed loop for the stop rule `--stop common` of the spec files. Line 1688 reads the clock at the start. Line 1695 calls the kernel through `call`. Line 1700 reads the clock after each call. Line 1967: `tcount`. Lines 1995 and 2056: the two timed functions of the trial mode. Line 2900: the `#include` of the self-test file. Lines 2913 to 2924: `main` handles `--trial`, `--selftest` and `--list`.
- [Ref9] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/bwx12_selftest.c`: Lines 60 to 100: what the self-test checks. Lines 67 to 70: the line `call,...` before each kernel call names the kernel if the call crashes. Lines 76 to 83: the checks for a read kernel and their limit. Lines 134 to 139: a row ends with `pass` or `FAIL`. Lines 147 to 188: one kernel is called through `call` and the memory is checked. Lines 676 to 711: the function `selftest` with the buffer sizes and the last line `# failures=N`.
- [Ref10] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx12-2026-11-15/check_listing12.py`: Lines 1 to 25: the script runs on the development machine on `listing.txt` and `offsets.tsv`. The reference is the accepted build of bwx11. For every kernel of the reference it compares the function text and the loop start modulo 64.
- [Ref11] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/go.sh`: The driver of the whole-chip test. Line 13 holds the sha256 value of the binary. Line 23 stops the run when the `bwx12` file has another value. Line 31 calls `rx.sh` and passes the value to it. The file `go2.sh` in the same folder holds the same value on line 10, checks it on line 19 and passes it on line 30.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-2026-11-15/rx.sh`: The runner script of the bwx12 parts of the test. Line 3: a spec line is a tag, the character `|`, and the arguments of the binary. Line 8 checks the sha256 value of the binary and ends with status 2 when it differs. Lines 11 to 21: one process per spec line.
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/like.spec`: Line 1: the arguments of bwx12 in the whole-chip test, with `--seq` and without `--trial`. The files `cfwd.spec` and `crev.spec` in the same folder have the same form.
- [Ref14] `/home/jhan/workspace/titan/cache-perf/crb/results/w120-T72L1-20261117T221329Z/env.txt`: The line that begins with `binary` holds the path and the sha256 value of the binary. Checked in this task: the 9 folders `w120-T72*` under `results` all hold the same line.
- [Ref15] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`: Line 19: the seven flags of the build of bw_old and bw_new. Line 29: the compiler call. Lines 31 and 32: the builds of bw_old and bw_new.
- [Ref16] `/home/jhan/workspace/titan/cache-perf/crb/results/kernels-20261113T181222Z/probe.txt`: Lines 1 to 3 of the record of 2026-11-13: host `ubuntu`, gcc 14.2.0, and the seven flags.
- [Ref17] Help text of gcc 11.4.0 on the development machine, read in this task (`gcc --help=optimizers`, `gcc --help=c`, `gcc -Q --help=optimizers -O3`, `gcc -dumpspecs`). It gives one line per flag, for example "Enable loop distribution for patterns transformed into a library call" for `-ftree-loop-distribute-patterns` and "Perform Identical Code Folding for functions and read-only variables" for `-fipa-icf`. At `-O3` it lists `-finline-functions` and `-ftree-loop-vectorize` as enabled. The help text of the CRB compiler (gcc 14.2.0) was not read.
- [Ref18] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: Lines 38 to 89: the word list of the project. Line 77 defines the marker file. Line 80 defines sha256.
- [Ref19] `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/build.sh`: Lines 5 to 7, 27 and 42: `EXTRA` holds more compiler flags and goes into the compiler call of the older runner version bwx.
- [Ref20] Computed in this task with `sha256sum` on the local files `bwx12.c`, `bwx12_selftest.c` and `build12.sh`, and on `listing.txt`, `offsets.tsv` and `seq-listing.txt` in `crb-build-1`. All six values equal the values on lines 17 to 19 and 21 to 23 of `build.txt`. `find` shows no file with the name `bwx12` under the local folder `crb`.
- [Ref21] Test in this task on the development machine with gcc 11.4.0 (x86-64). The C file has 16 lines. Its `static` function `call` has one call, through a `static inline` function, from a function `worker`. Built with `-O3`: `nm` shows no symbol `call`. Built with `-O3 -fno-toplevel-reorder`, and with `-O3 -fno-ipa-icf -fno-toplevel-reorder -falign-functions=4`: `nm` shows the symbol `call`, and the `objdump` text of the binary holds no call of it. The `static inline` function has no symbol in any of the three builds. The CRB compiler (gcc 14.2.0, AArch64) was not tested.
- [Ref22] external source: the gcc 14.2.0 manual, chapter "AArch64 Options", entry `-march=name`, read in this task on gcc.gnu.org. The value `native` "causes the compiler to pick the architecture of the host system". GCC uses the architecture name "to determine what kind of instructions it can emit". If `-march` is given without `-mtune` or `-mcpu`, "the code is tuned to perform well across a range of target processors implementing the target architecture".
