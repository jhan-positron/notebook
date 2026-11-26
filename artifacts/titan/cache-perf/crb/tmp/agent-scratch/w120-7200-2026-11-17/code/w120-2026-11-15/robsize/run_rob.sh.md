# `run_rob.sh` explained, line by line

- Source file: `w120-2026-11-15/robsize/run_rob.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 25 lines, 828 bytes).
- sha256 of the source when this page was built: `e2eff7e4ede6a208e5db456bba5435125b9a228ba03ab56ee9e617fd6eee6963`.

## Short version: purpose

`run_rob.sh` is the plain start script of the window test: it builds `robsize.c` with `gcc -O2` and runs `robsize` on CPU 2. It writes the output, with head lines for the machine, the compiler and the load, to a file `rob-TIME.csv` in its own folder and prints the step lines at the end. It has none of the checks of `go.sh`, the wrapper for CRB.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **`robsize`**: the window test program of this folder. It measures how many filler instructions of one kind fit in the out-of-order window of one core.
- **Kind**: one sort of filler instruction of `robsize`, chosen with the option `--kind`.
- **N**: the number of filler units after each of the two loads in the loop of `robsize`.
- **Step line**: a comment line of the output that starts with `# step`. It gives the N at which the time per loop pass steps up. A line that starts with `# cut` says where the series was cut before that search.
- **AArch64**: the 64-bit instruction set of Arm. `robsize.c` builds for it only.

## Main flow

1. Go to the folder of the script and set the CPU number and the name of the result file (lines 5 to 9).
2. Build `robsize` (line 11).
3. Write four head lines to the screen and to the result file (lines 13 to 18).
4. Run `robsize` on CPU 2 with the arguments of the script, and copy its output to the result file (line 20).
5. Append the load after the run, and print the path of the file and the step lines (lines 22 to 25).

## Behavior a reader must know

- The script does not check the marker file, does not wait for a quiet machine and sets no time limit. On CRB the wrapper `go.sh` does these things.
- The script does not limit the process to the CPUs 0 to 119 with `taskset`. The program itself refuses a CPU number above 119, and it pins itself to the CPU of `--cpu`.
- With `set -e` and `pipefail` a failed build or a failed run of `robsize` stops the script. The lines after the failed command do not run.
- The script itself times nothing. All times in the result file come from `robsize`.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/robsize/run_rob.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (25 lines, 828 bytes, sha256 `e2eff7e4ede6a208e5db456bba5435125b9a228ba03ab56ee9e617fd6eee6963`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/bin/bash` | Tells Linux to run this file with `bash`, by the fixed path `/bin/bash`. |
| 2 | `# Build robsize and run every filler kind on CPU 2.` | Comment: the script builds `robsize` and runs every filler kind on CPU 2. |
| 3 | `# Run on the AArch64 target, from any directory. Extra arguments are passed` | Comment: it is meant to run on the AArch64 target machine, from any folder. Extra arguments are given to `robsize`. |
| 4 | `# to robsize, for example:  ./run_rob.sh --kind nop --nmin 300 --nmax 420 --nstep 1` | Comment: an example with extra arguments. It measures the kind `nop` for every N from 300 to 420. |
| 5 | `set -euo pipefail` | `-e`: the script stops at the first command that fails. `-u`: it stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any command of it fails, not only the last one. |
| 6 | `cd "$(dirname "$0")"` | Changes the working folder to the folder of the script. `$0` is the path of the script, and `dirname` cuts its last part. So the source file and the result file are found in this folder. |
| 8 | `CPU=2` | `CPU`: the number of the CPU on which `robsize` measures, 2. |
| 9 | `out="rob-$(date -u +%Y%m%dT%H%M%SZ).csv"` | `out`: the name of the result file: `rob-`, the UTC time of this moment (`date -u`) and `.csv`. |
| 11 | `gcc -O2 -Wall -o robsize robsize.c` | Builds the program. `gcc` compiles `robsize.c` to the file `robsize`. `-O2` turns on the usual optimisations, and `-Wall` prints the common warnings. A failed build stops the script (line 5). |
| 13 | `{` | Starts a group of commands. Line 18 sends the output of all of them to the screen and to the result file. |
| 14 | `    echo "# host=$(uname -n) arch=$(uname -m) kernel=$(uname -r)"` | First head line: the host name (`uname -n`), the machine type (`uname -m`) and the release of the running Linux kernel (`uname -r`). |
| 15 | `    echo "# gcc=$(gcc -dumpfullversion)"` | Second head line: the full version of `gcc`. |
| 16 | `    echo "# loadavg_before=$(cat /proc/loadavg)"` | Third head line: the content of `/proc/loadavg`, the load of the machine before the measurement. |
| 17 | `    echo "# thp_enabled=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null \|\| echo unknown)"` | Fourth head line: the setting of transparent huge pages. `cat` prints the file of the Linux kernel that holds it. When the file cannot be read, `2>/dev/null` hides the error and `echo` prints `unknown`. |
| 18 | `} \| tee "$out"` | Ends the group. The pipe gives its output to `tee`, which prints it and writes it to the result file. The file is created new or emptied. |
| 20 | `./robsize --cpu "$CPU" "$@" \| tee -a "$out"` | Runs `robsize`. `--cpu "$CPU"` makes the program pin itself to CPU 2. `"$@"` adds the arguments of the script, each as one word. With no arguments `robsize` measures every kind with its default list of N. `tee -a` prints the output and appends it to the result file. `robsize` times its own loops. This script times nothing. |
| 22 | `echo "# loadavg_after=$(cat /proc/loadavg)" \| tee -a "$out"` | Appends one more line through `tee -a`: the content of `/proc/loadavg` after the measurement. |
| 23 | `echo "wrote $(pwd)/$out" >&2` | Prints `wrote` and the full path of the result file to the error output (`>&2`). `pwd` prints the working folder. |
| 24 | `echo "step summary:" >&2` | Prints the text `step summary:` to the error output. |
| 25 | `grep -E '^# (step\|cut)' "$out" >&2 \|\| true` | Prints every line of the result file that starts with `# step` or `# cut` to the error output. `grep -E` takes the pattern as an extended regular expression, in which `(step\|cut)` means one of the two words. These lines hold the step position that `robsize` found for each kind. `\|\| true` keeps the exit status 0 when `grep` finds no such line. |
