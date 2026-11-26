## Short version: purpose

`rc2.sh` is a variant of the counter script `rc.sh`. It starts a benchmark binary once per line of a spec file and reads mesh counters as root with `sudo perf stat` while each process runs: one counter window of `WIN` seconds per event set. The difference is the form of an event set: a set line holds full `perf` event strings, and the script gives them to `perf` without a test and without a change.

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
- **Spec file**: a text file that the script `rx.sh` reads as its input. Each line has the form `tag|arguments of the binary` and gives one process. `rc2.sh` reads a file of the same form.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **Mesh counter**: a hardware counter of the mesh, the network inside one half of the chip. It counts events of that network, for example requests, retries and stalled transfers.
- **`arm_cmn_0`, `arm_cmn_1`**: the counter devices of mesh 0 and of mesh 1. Linux offers the mesh counters under these two names.
- **`perf stat`**: the Linux tool that counts events while a command runs.
- **Full event string**: the name of a counter device, then `/`, the event with its parameters, and `/`. This is the form in which `perf` takes an event of a named device.
- **Event set**: one line of the file with the event sets: a set name and the events that one counter window counts together.
- **Counter window**: the time for which one `perf stat` command counts. In this script it is the run time of the command `sleep $WIN`.
- **`dtc_cycles`**: an event of the mesh counter device. The analysis script `anc.py` uses its count as the number of clock cycles of a mesh.

## Main flow

1. Read the four arguments and the settings `WIN` and `DELAY` ({L7}).
2. Stop when the marker file exists, or when the binary does not have the expected sha256 ({L8-9}).
3. Create the result folder, write `env.txt` and copy the event sets two times, as `sets.txt` and as `sets.ok` ({L10-13}).
4. For each line of the spec file: wait until the machine is quiet, write a `launch` line and start the binary in the background ({L14-21}).
5. Wait `DELAY` seconds, then take one counter window of `WIN` seconds per event set ({L22-30}).
6. Wait for the end of the process and write its exit status to `launches.txt` ({L31-32}).
7. After the last line: make the user the owner of the result files and print a summary ({L34-35}).

## Behavior a reader must know

- Two commands run as root: the `sudo -n perf stat` of {L27} and the `sudo -n chown` of {L34}. The header comment names `perf stat` only.
- No event is tested before the run. When `perf` cannot count an event, or when `sudo` would need a password, the script goes on: it does not test the exit status of `perf`. The error message of `perf` goes to `stderr.txt`, and the summary of {L35} prints the first 800 bytes of that file.
- The script times nothing of the benchmark. The runner times its own interval. A counter window is the run time of `sleep $WIN` under `perf stat`, and its counts are counts of the whole machine, not of one process.
- The windows of one process follow one after the other. So the timed interval must be longer than `DELAY` plus the number of sets times `WIN`, plus the start time of each `perf` command. When the process ends earlier, {L24} writes a line with the text `process ended before set`, and the sets that remain get no window.
- The script does not test that a window lies inside the timed interval. Only the pause of {L22} keeps the first window out of the start phase of the process.
- The marker file is checked four times: at the start, before each process, before each counter window, and once per second while the script waits for the end of a process. Each check ends the script with exit status 3. The last two also end the running process.
- Other exit statuses: 2 when the sha256 of the binary differs. The exit status of the binary is written to `launches.txt` and is not tested.
- The comment of {L4} does not fit the code: the script adds no device name to an event.
- This script does not call `hw.sh`. It makes no hardware record.

## References

- [Ref1] external source: Linux manual page proc(5), entry `/proc/loadavg`.
- [Ref2] test data: the folder `tests/2026-11-15-whole-chip-read-drop/w120-RC2-20261115T192222Z` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its name has the form that {L10} builds.
- [Ref3] external source: Linux manual page perf-stat(1), options `-a`, `-e`, `-o`, `-x` and the section "CSV FORMAT".
