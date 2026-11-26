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

1. Go to the folder of the script, take the tag from the first argument and set the names of the lock file and of the result file ({L5-9}).
2. Wait until no other measurement runs. The function `quiet` checks the marker file and looks three times, 20 s apart, for processes with the names `bwx11`, `bwx12`, `perf` and `robsize` ({L11-27}).
3. Build `robsize`. With the tag `build` stop here ({L28-29}).
4. Wait a second time, create the lock file, and write five head lines to the result file ({L30-39}).
5. When a file `TAG.spec` exists, call `robsize` once per line of it, each call with the time that remains of the budget ({L42-52}).
6. If not, call `robsize` once with the arguments of the script ({L53-55}).
7. Append the exit status, the load and the end time to the result file, and print `DONE` ({L57-60}).

## Behavior a reader must know

- What is timed: `robsize` times its own loops. `go.sh` times nothing. It only limits the run time with `timeout`.
- The marker file is checked only inside `quiet`, that is before the build and before the run. It is not checked while `robsize` measures. This differs from `rx.sh`, which checks it once per second.
- The process check of {L17} knows four names. A runner with another name, for example `bwx13`, does not make the script wait.
- The script creates the lock file and removes it at its end. It never tests whether the lock file exists. So the lock stops no second `go.sh`.
- Exit statuses: 3 when the marker file exists, 4 after 60 min of waiting, 5 when the build fails, 0 in every other case. The status of `robsize` is not the exit status of the script. It stands in the line `exit_code=` of the result file and in the `DONE` line.
- A call that runs past the budget is ended by `timeout`. The rows that it had printed stay in the result file, and the status is 124.
- The time in the name of the result file is the start of the script, not the start of the measurement ({L9}). In the result file `rob-r1-20261115T191146Z.csv` the line `start_utc` holds 19:33:27, 21 min and 41 s after the time of the name [Ref1].
- Each run builds the binary again. So the binary that measured is the one built from the `robsize.c` of that moment.

## References

- [Ref1] test data: the file `tests/2026-11-15-whole-chip-read-drop/robsize-results/rob-r1-20261115T191146Z.csv` of the repo `/home/jhan/workspace/ai-proj/arm-crb`, line `# start_utc=2026-11-15T19:33:27Z`.
