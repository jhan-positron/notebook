## Short version: purpose

`rgc.sh` joins the two scripts `rg.sh` and `rc2.sh`. It starts groups of benchmark processes that run at the same time, one group per line of its spec file, on the CPUs 0 to 119. While a group runs, it reads mesh counters as root with `sudo perf stat`: one counter window of `WIN` seconds per event set.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. The spec file of `rgc.sh` has another form: each line gives one group of processes.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Group**: the processes of one line of the spec file. The script starts them one after the other and then waits until all of them have ended.
- **Item**: one process of a group, in the form `tag=arguments`. The items of a line are separated by ` ;; `.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together. In this script the events are full `perf` event strings, with the device name in each of them.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` ({L6}).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 ({L7-8}).
3. Create the result folder, write `env.txt` and copy the event sets to `sets.ok` ({L9-11}).
4. For each line of the spec file: wait until the machine is quiet and write a `launch` line ({L12-17}).
5. Start one process per item of the line, in the background ({L18-24}).
6. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set ({L25-30}).
7. Wait until every process of the group has ended, and write one `rc` line per process ({L31-33}).
8. After the last line: make the user the owner of the result files and print a summary ({L35-36}).

## Behavior a reader must know

- Two commands run as root: the `sudo -n perf stat` of {L29} and the `sudo -n chown` of {L35}. The header comment names `perf stat` only.
- No event is tested before the run. When `perf` cannot count an event, or when `sudo` would need a password, the script goes on: it does not test the exit status of `perf`. The error message goes to `stderr.txt`.
- The processes of a group are started one after the other. The script does not make their timed intervals begin at the same moment. Each process times its own interval.
- The counts of a window are counts of the whole machine while all processes of the group run. The device name of an event tells the mesh, not the process.
- The windows of a group follow one after the other. So every timed interval of the group must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. As soon as one process of the group has ended, {L27} writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script writes no `start` line and no `win` line. So `launches.txt` shows the launch of a group only in its `launch` line, with a time in whole seconds, and it does not show when a window began.
- The marker file is checked four times: at the start, before each group, before each counter window, and once per second while the script waits for the end of a group. Each check ends the script with exit status 3. The last two also end every process of the group.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of each process is written to `launches.txt` and is not tested.
- This script does not call `hw.sh`. It makes no hardware record.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC3-20261115T194737Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that {L9} builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
