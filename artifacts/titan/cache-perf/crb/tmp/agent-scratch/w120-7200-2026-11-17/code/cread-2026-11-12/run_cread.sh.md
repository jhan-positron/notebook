# `run_cread.sh` explained, line by line

- Source file: `cread-2026-11-12/run_cread.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 38 lines, 1678 bytes).
- sha256 of the source when this page was built: `6481a5ec1d58a5968974c47a7f19c382a13b4a2bab26367a9c6e6f548f895503`.

## Short version: purpose

`run_cread.sh` is the run script of the cread test on CRB. It builds the benchmark `bandwidth_cread`, writes a build record with the machine code of three read kernels, and then starts 16 processes with one thread each. Each process times the kernels `read`, `asmread` and `cread` at one buffer size on one CPU.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Cread test**: the test that compares the read kernels `read`, `asmread` and `cread` with one thread on CRB.
- **`bandwidth_cread`**: the benchmark binary of this test. The script builds it from the file `bandwidth_cread.c` of the same folder.
- **`read`**: in `bandwidth_cread` the kernel of the function `k_read`: C code with 16 running sums. Each load is followed by an add.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`cread`**: in `bandwidth_cread` the kernel of the function `k_cread`: C code that only loads, written with NEON intrinsics (C functions that map to Arm vector instructions).
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Build record**: the file `probe.txt` that this script writes into the result folder.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **gcc**: the GNU C compiler.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Set the shell options and start the script again under `taskset`, with the CPU list 0 to 119 (lines 4 to 5).
2. Stop when the marker file exists (lines 6 to 8).
3. Set the paths and create the result folder (lines 9 to 12).
4. Build the binary `bandwidth_cread` from `bandwidth_cread.c` (lines 13 to 15).
5. Write the build record `probe.txt`: the machine state, the compiler, the flags, three checksums and the machine-code listing of `k_cread`, `k_asmread` and `k_read` (lines 16 to 26).
6. Create the empty output file `cread.csv` (line 27).
7. Start 16 processes, one after the other: 2 rounds, in each round CPU 0 and then CPU 2, and for each CPU the 4 buffer sizes. Before each process, check the marker file and write a header line to `cread.csv` (lines 28 to 36).
8. Append the load averages after the last process to `probe.txt` and print the path of the result folder (lines 37 to 38).

## Behavior a reader must know

- The script builds before it measures. The build of line 15 replaces the binary `bandwidth_cread` in the folder of the script.
- Stops: exit status 3 when the marker file exists at the start or before a process. A failed build, a failed `objdump` or a failed benchmark process also stops the script, with the exit status of that command (`set -e` and `pipefail`, line 4).
- The marker file is checked before each process, not while a process runs. One process holds at least 4.5 s of timed work: 3 kernels times 3 intervals of at least 0.5 s.
- The script has no pause between two processes and no test of the load. It only records the load average before each process (line 32).
- Thread placement: the script and its processes may run on the CPUs 0 to 119 only (line 5). The benchmark pins its one worker thread to CPU 0 or CPU 2. The benchmark does not pin its main thread.
- Order inside each process: `read`, then `asmread`, then `cread`. The benchmark fixes this order, and the script never changes it. Round 2 repeats round 1 in the same order.
- The comment of line 3 says that the script writes only under `$HOME/cache-perf`. The binary is written into the folder of the script. So the comment holds only when the script lies under that folder.

## Source and explanation, line by line

- Text shown: the file `cread-2026-11-12/run_cread.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (38 lines, 1678 bytes, sha256 `6481a5ec1d58a5968974c47a7f19c382a13b4a2bab26367a9c6e6f548f895503`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header, CPU limit, marker check, paths and build (lines 1 to 15)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# run_cread.sh - compare asmread, cread and read with one thread on CRB.` | Comment: the name and the purpose. The script compares the read kernels `asmread`, `cread` and `read` with one thread on CRB. |
| 3 | `# Reads stdin: nothing. Writes only under $HOME/cache-perf.` | Comment: the script reads nothing from its standard input, and it writes only under `$HOME/cache-perf`. The second part holds only when the script lies under that folder: line 15 writes the binary into the folder of the script. |
| 4 | `set -euo pipefail` | Sets three shell options. `-e`: the script stops when a command fails. `-u`: the script stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any of its commands fails, not only the last one. |
| 5 | `if [[ -z ${_PINNED:-} ]]; then _PINNED=1 exec taskset -c 0-119 "$0" "$@"; fi` | Limits the script to the CPUs 0 to 119. `${_PINNED:-}` gives the value of `_PINNED`, or an empty text when the variable is not set. `-z` tests for an empty text. At the first start the text is empty. Then `exec` replaces the shell with `taskset -c 0-119`, which starts this script again (`$0`) with the same arguments (`"$@"`) and with `_PINNED=1`. Linux may then run the script and every program that it starts on the CPUs 0 to 119 only. At the second start `_PINNED` is set, so this line does nothing. |
| 6 | `MARKER=/tmp/positron-perf.RUNNING` | `MARKER`: the path of the marker file. It exists while another user runs a performance test on CRB. |
| 7 | `check_marker() { if [[ -e $MARKER ]]; then echo "RUNNING file present: stop" >&2; exit 3; fi; }` | Defines the function `check_marker`. When the marker file exists (`-e`), it prints `RUNNING file present: stop` to the error output (`>&2`) and ends the script with exit status 3. |
| 8 | `check_marker` | Marker check 1: before any work. The script has written no file at this point. |
| 9 | `SRC=$(cd "$(dirname "$0")" && pwd)` | `SRC`: the folder of this script as a full path. `dirname "$0"` gives the folder part of the script path. `cd` goes there inside the command substitution, and `pwd` prints the full path. |
| 10 | `TS=$(date -u +%Y%m%dT%H%M%SZ)` | `TS`: the UTC time of this moment (`date -u`) as one word: year, month and day, the letter `T`, then hours, minutes and seconds, and the letter `Z`. |
| 11 | `OUT=$HOME/cache-perf/results/cread-$TS` | `OUT`: the result folder. Its path is `cache-perf/results/cread-` plus the time stamp `TS`, under the home folder of the user. |
| 12 | `mkdir -p "$OUT"` | Creates the result folder. `-p` also creates missing parent folders, and it gives no error when the folder exists. |
| 13 | `CFLAGS="-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11"` | `CFLAGS`: the compiler flags. `-O3`: a high optimization level. `-march=native`: the compiler may use every instruction of the machine that it runs on. `-fno-tree-loop-distribute-patterns`: gcc must not turn a loop into a call of `memset` or `memcpy`. `-pthread`: build with the POSIX thread library. `-Wall -Wextra`: print more warnings. `-std=gnu11`: the C standard of 2011 with the GNU extensions. |
| 14 | `B=$SRC/bandwidth_cread` | `B`: the path of the binary: the file `bandwidth_cread` in the folder of the script. |
| 15 | `gcc $CFLAGS -o "$B" "$SRC/bandwidth_cread.c"` | Builds the binary from `bandwidth_cread.c` with gcc. `$CFLAGS` has no quotes, so the shell splits it into the single flags. `-o` names the output file. When the build fails, the script stops here (`set -e`). The result folder is then empty. |

### The build record `probe.txt` and the empty output file (lines 16 to 27)

| Line | Source | Explanation |
|---:|---|---|
| 16 | `{` | Starts a group of commands. Line 26 sends the whole output of the group to the file `probe.txt`, the build record. |
| 17 | `  echo "## host=$(hostname) utc=$(date -u +%FT%TZ) load_before=$(cut -d' ' -f1-3 /proc/loadavg) logins=$(who \| wc -l)"` | First line of the build record: the host name, the UTC date and time, the load averages and the number of logins. `cut -d' ' -f1-3 /proc/loadavg` takes the first three fields of that file: the load averages of the last 1, 5 and 15 minutes. `who` prints one line per login, and `wc -l` counts the lines. |
| 18 | `  echo "## gcc=$(gcc --version \| head -1)"` | The compiler version. `head -1` keeps the first line of the output of `gcc --version`. |
| 19 | `  echo "## CFLAGS=$CFLAGS"` | The compiler flags of line 13. |
| 20 | `  echo "## thp=$(cat /sys/kernel/mm/transparent_hugepage/enabled)"` | The Linux setting for transparent huge pages. The file that `cat` prints holds the possible values, with the active value in square brackets. |
| 21 | `  echo "## sha256:"; sha256sum "$SRC/bandwidth_cread.c" "$B" "$HOME/cache-perf/bench/bandwidth.c"` | Prints the line `## sha256:`. Then `sha256sum` prints the sha256 and the path of three files: the source `bandwidth_cread.c`, the binary of line 15, and the file `bandwidth.c` in the folder `cache-perf/bench` under the home folder. The script does not use that third file. It only records its checksum. |
| 22 | `  for f in k_cread k_asmread k_read; do` | Loop over the names of three functions of the binary: `k_cread`, `k_asmread` and `k_read`. |
| 23 | `    echo "=== $f ==="` | Prints a heading with the function name, for example `=== k_cread ===`. |
| 24 | `    objdump -d --no-show-raw-insn --disassemble=$f "$B" \| sed -n '/>:$/,$p'` | Prints the machine code of the function. `objdump -d` turns the machine code of the binary into text. `--no-show-raw-insn` leaves out the instruction bytes. `--disassemble=$f` limits the output to the function `f`. The pipe gives the text to `sed -n '/>:$/,$p'`. It prints from the first line that ends with `>:`, which is the label line of the function, to the last line of the text. The lines before the label are dropped. |
| 25 | `  done` | Ends the loop of line 22. |
| 26 | `} > "$OUT/probe.txt"` | Ends the group. `>` writes its output to the file `probe.txt` in the result folder. |
| 27 | `: > "$OUT/cread.csv"` | Creates the empty file `cread.csv` in the result folder. The command `:` does nothing, and `>` creates the file or empties it. |

### The 16 timed processes and the end (lines 28 to 38)

| Line | Source | Explanation |
|---:|---|---|
| 28 | `for round in 1 2; do` | Loop over 2 rounds. Round 2 repeats the processes of round 1 in the same order. |
| 29 | `  for cpu in 0 2; do` | Loop over the 2 CPUs of the test: CPU 0, then CPU 2. |
| 30 | `    for bytes in 32K 1M 8M 1G; do` | Loop over the 4 buffer sizes `32K`, `1M`, `8M` and `1G`. The benchmark reads them as 32768, 1048576, 8388608 and 1073741824 bytes. So the script starts 2 times 2 times 4 = 16 processes, one after the other. |
| 31 | `      check_marker` | Marker check 2: before every process. When the marker file exists, the script stops with exit status 3. The script does not check the marker file while a process runs. |
| 32 | `      echo "-- round $round cpu $cpu bytes $bytes load $(cut -d' ' -f1 /proc/loadavg) utc $(date -u +%T)" >> "$OUT/cread.csv"` | Appends one header line to `cread.csv` before the process (`>>` appends to a file). The line holds the round, the CPU, the buffer size, the load average of the last minute and the UTC time. `cut -d' ' -f1 /proc/loadavg` takes the first field of the file. `date -u +%T` prints hours, minutes and seconds. |
| 33 | `      "$B" --threads 1 --cpus $cpu --bytes $bytes --kernel readcmp --reps 3 --min-ms 500 >> "$OUT/cread.csv"` | Starts the benchmark and waits for its end. `--threads 1 --cpus $cpu`: 1 thread, which the benchmark pins to the CPU `cpu`. `--bytes $bytes`: the buffer size. `--kernel readcmp`: the process times the kernels `read`, `asmread` and `cread`, in this order. `--reps 3`: 3 timed intervals per kernel. `--min-ms 500`: each timed interval lasts at least 500 ms. The rows that the benchmark prints are appended to `cread.csv`. Its error output is not redirected. When the benchmark fails, the script stops (`set -e`). |
| 34 | `    done` | Ends the loop over the buffer sizes (line 30). |
| 35 | `  done` | Ends the loop over the CPUs (line 29). |
| 36 | `done` | Ends the loop over the rounds (line 28). |
| 37 | `echo "## load_after=$(cut -d' ' -f1-3 /proc/loadavg) utc=$(date -u +%FT%TZ)" >> "$OUT/probe.txt"` | Appends a last line to `probe.txt`: the three load averages and the UTC date and time after the last process. |
| 38 | `echo "$OUT"` | Prints the path of the result folder. This is the last command, so the exit status of the script is 0. |
