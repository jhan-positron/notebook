## Short version: purpose

`rc.sh` starts a benchmark binary once per line of a spec file, on the CPUs 0 to 119. While each process runs its one long timed interval, the script reads the mesh counters as root with `sudo perf stat`: one counter window of `WIN` seconds per event set, each written to its own `.perf` file. It is the counter script of the 120-thread investigation for event sets that hold plain event names.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. `rc.sh` reads a file of the same form.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` ({L7}).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 ({L8-9}).
3. Create the result folder and write `env.txt` and a copy of the event sets ({L10-12}).
4. Test every event with a `perf stat` run of the command `true`, and write the usable events to `sets.ok` ({L14-21}).
5. For each line of the spec file: wait until the machine is quiet, write a `launch` line and start the binary in the background ({L22-29}).
6. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set of `sets.ok` ({L30-40}).
7. Wait for the end of the process and write its exit status to `launches.txt` ({L41-42}).
8. After the last line: make the user the owner of the result files and print a summary ({L44-45}).

## Behavior a reader must know

- Three commands run as root: the two `sudo -n perf stat` commands of {L18} and {L37}, and the `sudo -n chown` of {L44}. The header comment names `perf stat` only.
- When `sudo` would need a password, every test of {L18} fails. Then every event is listed in `unsupported.txt`, `sets.ok` stays empty and no counter window is taken. The benchmark processes still run.
- The script times nothing of the benchmark. The runner times its own interval. A counter window is the run time of `sleep $WIN` under `perf stat`, and its counts are counts of the whole machine, not of one process.
- The windows of one process follow one after the other. So the timed interval must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. When the process ends earlier, {L32} writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script does not test that a window lies inside the timed interval. Only the pause of {L30} keeps the first window out of the start phase of the process.
- The marker file is checked four times: at the start, before each process, before each counter window, and once per second while the script waits for the end of a process. Each check ends the script with exit status 3. The last two also end the running process.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of the binary is written to `launches.txt` and is not tested.
- The test of {L18} uses the device `arm_cmn_0` only. {L37} counts each event on both devices.
- The events of a set line must be separated by `;` ({L17}). The header comment shows commas.
- This script does not call `hw.sh`. It makes no hardware record.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC1-20261115T190208Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that {L10} builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
