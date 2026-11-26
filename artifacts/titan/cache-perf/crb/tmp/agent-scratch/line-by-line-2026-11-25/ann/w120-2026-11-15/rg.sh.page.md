## Short version: purpose

`rg.sh` starts groups of benchmark processes that run at the same time, on the CPUs 0 to 119 and without root rights. Each line of its spec file is one group, and each item of the line is one process with its own arguments, for example one process per mesh with a different kernel. It is the script of the 120-thread investigation for tests in which two sets of threads run different kernels at the same time.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. The spec file of `rg.sh` has another form: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Group**: the processes of one line of the spec file. The script starts them one after the other and then waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `.
- **Latency probe**: a second program that times memory loads on one CPU while the benchmark processes run on the other CPUs. The spec file `r4.spec` uses the program `robsize` for it.

## Main flow

1. Read the three arguments ({L6}).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 ({L7-8}).
3. Create the result folder and write `env.txt` ({L9-10}).
4. For each line of the spec file: wait until the machine is quiet and write a `launch` line ({L11-16}).
5. Start one process per item of the line, in the background, and note each launch time ({L17-24}).
6. Wait until every process of the group has ended, with a check of the marker file once per second ({L25-26}).
7. Write one `rc` line with the exit status of each process ({L27}).
8. After the last line: print a summary ({L29}).

## Behavior a reader must know

- The processes of a group are started one after the other, as fast as the shell starts them. The script does not make their timed intervals begin at the same moment. Each process times its own interval, so the intervals of a group overlap only as far as the start phases of the processes allow.
- A group is over when all its processes have ended. Only then does the script go to the next line, with a new wait for a quiet machine and a new pause of 5 s.
- An item whose arguments start with `@` runs the text after the `@` as a full command ({L21}). The checksum check of {L8} does not cover that program.
- The marker file is checked three times: at the start, before each group, and once per second while a group runs. Each check ends the script with exit status 3. The last one also ends every process of the group.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of each process is written to `launches.txt` and is not tested.
- An `rc` line holds the group name and no tag. The `rc` lines of a group stand in the order of the items of its spec line.
- The script runs no command as root.
- This script does not call `hw.sh`. It makes no hardware record.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-R3-20261115T193922Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that {L9} builds.
