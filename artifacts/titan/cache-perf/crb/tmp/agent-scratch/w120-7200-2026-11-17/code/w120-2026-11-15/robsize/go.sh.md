# `go.sh` explained, line by line

- Source file: `w120-2026-11-15/robsize/go.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 60 lines, 2311 bytes).
- sha256 of the source when this page was built: `7c433df1c81cc98d762eabb6ca011b1c910bdf3b34a1c0d2412dfac8ddef5f14`.

## Short version: purpose

`go.sh` is the wrapper that runs the window test program `robsize` on CRB. It waits until the marker file is absent and no other measurement process runs, builds `robsize.c` with `gcc -O2`, and runs the program on CPU 2 with a time limit of 570 s. The output goes to a file `rob-TAG-TIME.csv` in the folder of the script, with head lines for the machine, the compiler and the load.

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
- **N**: the number of filler units after each of the two loads in the loop of `robsize`. The program measures a list of N values for each kind.
- **Tag**: the first argument of `go.sh`. It goes into the name of the result file, and it names the spec file `TAG.spec`.
- **Spec file**: here a text file `TAG.spec` in the folder of the script. Each line holds the arguments of one call of `robsize`. It has no tag column, unlike the spec files of `rx.sh`.
- **Lock file**: the file `LOCK.rob`. It exists while `go.sh` measures.
- **Budget**: the 570 s that all calls of one run of `go.sh` may take together.

## Main flow

1. Go to the folder of the script, take the tag from the first argument and set the names of the lock file and of the result file (lines 5 to 9).
2. Wait until no other measurement runs. The function `quiet` checks the marker file and looks three times, 20 s apart, for processes with the names `bwx11`, `bwx12`, `perf` and `robsize` (lines 11 to 27).
3. Build `robsize`. With the tag `build` stop here (lines 28 to 29).
4. Wait a second time, create the lock file, and write five head lines to the result file (lines 30 to 39).
5. When a file `TAG.spec` exists, call `robsize` once per line of it, each call with the time that remains of the budget (lines 42 to 52).
6. If not, call `robsize` once with the arguments of the script (lines 53 to 55).
7. Append the exit status, the load and the end time to the result file, and print `DONE` (lines 57 to 60).

## Behavior a reader must know

- What is timed: `robsize` times its own loops. `go.sh` times nothing. It only limits the run time with `timeout`.
- The marker file is checked only inside `quiet`, that is before the build and before the run. It is not checked while `robsize` measures. This differs from `rx.sh`, which checks it once per second.
- The process check of line 17 knows four names. A runner with another name, for example `bwx13`, does not make the script wait.
- The script creates the lock file and removes it at its end. It never tests whether the lock file exists. So the lock stops no second `go.sh`.
- Exit statuses: 3 when the marker file exists, 4 after 60 min of waiting, 5 when the build fails, 0 in every other case. The status of `robsize` is not the exit status of the script. It stands in the line `exit_code=` of the result file and in the `DONE` line.
- A call that runs past the budget is ended by `timeout`. The rows that it had printed stay in the result file, and the status is 124.
- The time in the name of the result file is the start of the script, not the start of the measurement (line 9). In the result file `rob-r1-20261115T191146Z.csv` the line `start_utc` holds 19:33:27, 21 min and 41 s after the time of the name [Ref1].
- Each run builds the binary again. So the binary that measured is the one built from the `robsize.c` of that moment.

## Source and explanation, line by line

- Text shown: the file `w120-2026-11-15/robsize/go.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (60 lines, 2311 bytes, sha256 `7c433df1c81cc98d762eabb6ca011b1c910bdf3b34a1c0d2412dfac8ddef5f14`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment and settings (lines 1 to 10)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/bin/bash` | Tells Linux to run this file with `bash`, by the fixed path `/bin/bash`. |
| 2 | `# CRB wrapper: wait until no other measurement runs, hold the lock file,` | Comment: `go.sh` is the wrapper for CRB. It waits until no other measurement runs, and it holds the lock file. |
| 3 | `# build, then run robsize on CPU 2 inside CPUs 0-119.` | Comment: it then builds `robsize` and runs it on CPU 2, inside the CPUs 0 to 119. |
| 4 | `# usage: go.sh TAG [robsize arguments]` | Comment: the usage. The first argument is a tag. The other arguments are arguments of `robsize`. |
| 5 | `set -uo pipefail` | `-u`: the script stops when it uses a variable that was never set. `-o pipefail`: a pipeline fails when any command of it fails, not only the last one. The script has no `set -e`. So a failed command alone does not stop it. |
| 6 | `cd "$(dirname "$0")"` | Changes the working folder to the folder of the script. `$0` is the path of the script, and `dirname` cuts its last part. So the relative paths of line 9, line 28 and line 44 are paths in this folder. |
| 7 | `tag=$1; shift` | `tag`: the first argument. `shift` removes it. So the arguments that remain are those for `robsize`. |
| 8 | `LOCK=$HOME/cache-perf/w120-20261115/LOCK.rob` | `LOCK`: the path of the lock file, `LOCK.rob` in the folder `cache-perf/w120-20261115` below the home folder of the user. |
| 9 | `out="rob-$tag-$(date -u +%Y%m%dT%H%M%SZ).csv"` | `out`: the name of the result file: `rob-`, the tag, the UTC time of this moment (`date -u`) and `.csv`. The time is read here, before the waits of line 27 and line 30. So it can be much earlier than the start of the measurement, which line 36 writes into the file. |

### Function `quiet`: wait until no other measurement runs (lines 11 to 25)

| Line | Source | Explanation |
|---:|---|---|
| 11 | `quiet() { # 3 empty checks 20 s apart; else wait 2 min; up to 60 min` | Starts the function `quiet`. By the comment it returns after 3 checks, 20 s apart, that found nothing. If a check finds something, it waits 2 min and starts again, for up to 60 min. |
| 12 | `    local deadline=$(( $(date +%s) + 3600 ))` | `deadline`: the time of this moment in seconds since 1970-01-01 00:00 UTC (`date +%s`), plus 3600 s. `local` keeps the variable inside the function. |
| 13 | `    while :; do` | Starts a loop without an end condition (`while :`). Only line 14, line 20 and line 21 leave it. |
| 14 | `        if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi` | Marker check. When the marker file `/tmp/positron-perf.RUNNING` exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. |
| 15 | `        local ok=1` | `ok`: 1 as long as no check of this pass found a measurement process. |
| 16 | `        for i in 1 2 3; do` | Starts the loop over the three checks of one pass. |
| 17 | `            if [ -n "$(pgrep -x 'bwx11\|bwx12\|perf\|robsize')" ]; then ok=0; break; fi` | One check. `pgrep -x` prints the process ids of all processes whose name is exactly `bwx11`, `bwx12`, `perf` or `robsize`. The `\|` in the pattern means "or". `-n` tests that the output is not empty. When such a process exists, `ok` becomes 0 and `break` leaves the loop of line 16. Other names, for example `bwx13`, are not in the pattern. |
| 18 | `            [ $i -lt 3 ] && sleep 20` | After the first and the second check (`-lt 3`: `i` is below 3) the function sleeps 20 s. So three clean checks take about 40 s. |
| 19 | `        done` | Ends the loop over the three checks (line 16). |
| 20 | `        [ $ok = 1 ] && return 0` | When all three checks were clean, the function returns with status 0. |
| 21 | `        [ "$(date +%s)" -ge "$deadline" ] && { echo "busy for 60 min: stop"; exit 4; }` | When the 60 min are over (the time of this moment is at or after `deadline`), the script prints `busy for 60 min: stop` and ends with exit status 4. |
| 22 | `        echo "busy at $(date -u +%T), waiting 2 min"` | Prints `busy at`, the UTC time and `waiting 2 min`. |
| 23 | `        sleep 120` | Sleeps 120 s. Then the loop of line 13 starts the next pass, which begins with the marker check. |
| 24 | `    done` | Ends the loop of line 13. |
| 25 | `}` | Ends the function `quiet`. |

### Build, lock file and the head of the result file (lines 26 to 39)

| Line | Source | Explanation |
|---:|---|---|
| 27 | `quiet` | First call of `quiet`, before the build. The script goes on only when no other measurement runs. |
| 28 | `taskset -c 0-119 gcc -O2 -Wall -o robsize robsize.c \|\| { echo "BUILD FAILED"; exit 5; }` | Builds the program. `gcc` compiles `robsize.c` to the file `robsize`. `-O2` turns on the usual optimisations, and `-Wall` prints the common warnings. `taskset -c 0-119` keeps the compiler on the CPUs 0 to 119. When the build fails, the script prints `BUILD FAILED` and ends with exit status 5. |
| 29 | `[ "$tag" = build ] && { echo "BUILD OK"; exit 0; }` | When the tag is the word `build`, the script prints `BUILD OK` and ends here with exit status 0. Nothing is measured. |
| 30 | `quiet` | Second call of `quiet`. The build took time, so the script tests again that no other measurement runs. |
| 31 | `touch "$LOCK"` | Creates the lock file (`touch` makes an empty file or sets the time of a file that exists). The script does not test whether the lock file was already there. |
| 32 | `trap 'rm -f "$LOCK"' EXIT` | `trap ... EXIT`: when the script ends, for any reason, the shell runs the command in quotes: `rm -f` removes the lock file and gives no error when it is missing. |
| 33 | `{` | Starts a group of commands. Line 39 sends the output of all of them to the result file. |
| 34 | `    echo "# host=$(uname -n) arch=$(uname -m) kernel=$(uname -r)"` | First head line: the host name (`uname -n`), the machine type (`uname -m`) and the release of the running Linux kernel (`uname -r`). |
| 35 | `    echo "# gcc=$(gcc -dumpfullversion) args=$*"` | Second head line: the full version of `gcc`, and after `args=` the arguments that were given to the script after the tag (`$*`). |
| 36 | `    echo "# start_utc=$(date -u +%FT%TZ)"` | Third head line: the UTC date and time of this moment, in the form `2026-11-15T19:33:27Z`. This is the start of the measurement. |
| 37 | `    echo "# loadavg_before=$(cat /proc/loadavg)"` | Fourth head line: the content of `/proc/loadavg`, the load of the machine before the measurement. |
| 38 | `    echo "# thp_enabled=$(cat /sys/kernel/mm/transparent_hugepage/enabled 2>/dev/null \|\| echo unknown)"` | Fifth head line: the setting of transparent huge pages. `cat` prints the file of the Linux kernel that holds it. When the file cannot be read, `2>/dev/null` hides the error and `echo` prints `unknown`. |
| 39 | `} > "$out"` | Ends the group. `>` creates the result file, or empties it, and writes the five head lines into it. |

### The run of `robsize` and the last lines of the result file (lines 40 to 60)

| Line | Source | Explanation |
|---:|---|---|
| 40 | `# With no arguments: one run of every kind. With a file TAG.spec: one` | Comment: with no arguments `robsize` runs once with every kind. With a file `TAG.spec` it runs once per line of that file. |
| 41 | `# robsize call per line of that file, all inside one 570 s budget.` | Comment: all calls of a spec file must fit into one budget of 570 s. |
| 42 | `t_end=$(( $(date +%s) + 570 ))` | `t_end`: the end of the budget, the time of this moment plus 570 s. |
| 43 | `rc=0` | `rc`: the exit status that the script will report. It starts at 0. |
| 44 | `if [ -f "$tag.spec" ]; then` | Tests whether a regular file with the name of the tag and the ending `.spec` exists in the folder of the script (`-f`). |
| 45 | `    while read -r line; do` | Starts the loop over the lines of the spec file (line 52 gives the file as the input). `read -r line` puts one whole line into `line` and keeps each backslash as it is. |
| 46 | `        [ -z "$line" ] && continue` | Skips an empty line. |
| 47 | `        left=$(( t_end - $(date +%s) ))` | `left`: the seconds that remain of the budget. |
| 48 | `        [ $left -le 5 ] && { echo "# budget used up, skipped: $line" >> "$out"; rc=124; continue; }` | When 5 s or less remain: the script writes a comment line with `budget used up, skipped:` and the spec line into the result file, sets `rc` to 124 and goes to the next line. So every line that remains is skipped in the same way. |
| 49 | `        echo "# call: $line" >> "$out"` | Writes a comment line with `call:` and the spec line into the result file. |
| 50 | `        # shellcheck disable=SC2086` | Comment for the check tool `shellcheck`: it turns off the warning SC2086 for the next line. That warning names a variable without quotes. Here the missing quotes are wanted. |
| 51 | `        timeout $left taskset -c 0-119 ./robsize --cpu 2 $line >> "$out" 2>> "$out.err" < /dev/null \|\| rc=$?` | One call of `robsize`. `timeout $left` ends the program when it runs longer than the seconds that remain, and then gives the status 124. `taskset -c 0-119` allows the process to run on the CPUs 0 to 119 only. `--cpu 2` makes `robsize` pin itself to CPU 2. `$line` has no quotes, so the shell splits the spec line at the spaces into single arguments. The standard output is appended to the result file, the error messages to a file with `.err` after the name. The input is `/dev/null`, so the program cannot read the rest of the spec file. When the call fails, `rc` takes its exit status. |
| 52 | `    done < "$tag.spec"` | Ends the loop (line 45). `< "$tag.spec"` makes the spec file the input of the loop. |
| 53 | `else` | The other case: no spec file with the name of the tag exists. |
| 54 | `    timeout 570 taskset -c 0-119 ./robsize --cpu 2 "$@" >> "$out" 2> "$out.err"` | One call of `robsize` with a time limit of 570 s, on the CPUs 0 to 119, with `--cpu 2` and then the arguments of the script (`"$@"` gives each one as one word). With no arguments `robsize` runs every kind with its default list of N. The standard output is appended to the result file. `2>` writes the error messages to the `.err` file and replaces its old content. |
| 55 | `    rc=$?` | `rc`: the exit status of that call. |
| 56 | `fi` | Ends the `if` of line 44. |
| 57 | `echo "# exit_code=$rc" >> "$out"` | Appends the comment line `exit_code=` with `rc` to the result file. |
| 58 | `echo "# loadavg_after=$(cat /proc/loadavg)" >> "$out"` | Appends the content of `/proc/loadavg` after the measurement. |
| 59 | `echo "# end_utc=$(date -u +%FT%TZ)" >> "$out"` | Appends the UTC date and time of the end. |
| 60 | `echo "DONE rc=$rc $out"` | Prints `DONE`, `rc=` with the status, and the name of the result file. The exit status of `go.sh` itself is 0 here. Then the trap of line 32 removes the lock file. |

## References

- [Ref1] test data: the file `tests/2026-11-15-whole-chip-read-drop/robsize-results/rob-r1-20261115T191146Z.csv` of the repo `/home/jhan/workspace/ai-proj/arm-crb`, line `# start_utc=2026-11-15T19:33:27Z`.
