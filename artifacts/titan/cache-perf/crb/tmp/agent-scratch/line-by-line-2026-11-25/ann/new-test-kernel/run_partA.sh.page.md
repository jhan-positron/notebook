## Short version: purpose

`run_partA.sh` runs Part A, the screening part of the test plan of 2026-11-13, on CRB, the Arm server under test: in the steps A1 to A6 it starts the two existing benchmark binaries `bw_old` and `bw_new` one process at a time, and in step A7 it reads system information. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan: the commands, what each step runs, and how to analyse the results.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. By the plan it closes no hypothesis. This is not the part A of the later rerun.
- **Step**: one named batch of Part A, `A1` to `A7`. The steps A1 to A6 start benchmark processes. Step A7 only reads system files.
- **Part C of the plan**: a later part of the plan. It reads the counters of the cores while the benchmark runs. This is not the part C of the later rerun.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`asmwrite`**: the hand-written write loop of the benchmark.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel names of this script**: `read_old` and `write_old` are the C kernels of `bw_old`. `read_new` and `write_new` are the C kernels of `bw_new`. `asmread` and `asmwrite` are taken from `bw_new`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`. The option `--reps` gives the number of repetitions per kernel, and `--min-ms` gives the shortest length of each.
- **Tag**: the short name of a process in its csv file, for example `read_old-r1`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. The script starts no process that could run past it, and it ends a process that still runs at that time. The value `none` sets no limit.
- **`MARGIN`**: a number of seconds. The script starts a process only when `STOP_AT` is more than `MARGIN` seconds away. It is 150 s when the variable is not set or is empty.
- **Block**: a time window that another user has reserved on CRB.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter device**: the name under which Linux offers one group of hardware counters, as a folder in `/sys/bus/event_source/devices/`.
- **SVE**: the scalable vector instructions of Arm. The length of an SVE vector register is set per process.
- **Process group**: a set of processes that one signal can reach together.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **est.**: an estimate, not a measurement.

## Main flow

1. Limit the script and everything that it starts to the CPUs 0 to 119 ({L11-12}).
2. Require `STOP_AT` and set the stop controls: the paths of the marker file and of the stop file, the stop time, `MARGIN` and the trap for an interruption ({L13-31}).
3. Test the stop reasons once, before any file is written ({L32}).
4. Check that `bw_old` and `bw_new` lie beside the script and have the expected sha256 ({L33-40}).
5. Read the step list, make the result folder and write the state of the machine to `env.txt` ({L41-52}).
6. Run the steps in the order of the call ({L85-120}). The steps A1 to A6 start their processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line, starts the binary, and tests the stop reasons once per second until the binary ends.
7. Step A1: the six kernels with 120 threads and 256 MiB per thread, 3 repetitions of at least 0.5 s, in 2 rounds with reversed order: 12 processes ({L86-88}).
8. Step A2: the same with repetitions of at least 6 s for the read kernels and 15 s for the write kernels: 12 processes ({L89-92}).
9. Step A3: the old read kernel with one buffer per thread and with two, at 0.5 s and at 6 s: 12 processes. The step is skipped when less than 70 GiB of memory are available ({L93-99}).
10. Step A4: the old read kernel and `asmread` at 11 thread counts per mesh, 2 repetitions of at least 6 s: 22 processes ({L100-104}).
11. Step A5: `asmread` with one thread and 8 MiB, 30 repetitions of at least 0.3 s, 2 processes on CPU 2 and 2 on CPU 41 ({L105-108}).
12. Step A6: `asmread` with one thread on CPU 2 and 8 MiB, 8 processes with huge pages allowed and 8 with `--no-thp`, alternating ({L109-113}).
13. Step A7: write the SVE vector length, the event list of `perf`, the names of the counter devices and the event codes of the cores to four files ({L114-118}).
14. Append the end line and the huge page counters to `env.txt`, and print the path of the result folder ({L121-123}).

## Behavior a reader must know

- The script times nothing. All timing happens inside `bw_old` and `bw_new`. The script sets how long and how often they time: `--reps` and `--min-ms`.
- What the benchmark times in one repetition (function `worker` of `bandwidth.c` and of `bandwidth.orig.c`): each thread first makes one warm-up pass over its buffer, which is not timed. Then a barrier releases all threads together, and each thread reads the clock for its own start time. Each thread runs whole passes and reads the clock after each pass, for the two buffer sizes of Part A. It stops at the first clock reading at which at least `--min-ms` have passed after its own start. So the threads of one repetition stop at different times (whole-pass stop).
- Eight things end the run early:
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A benchmark process ends with a status other than 0: status 1. The next process does not start. The header comment does not list this status.
  - A value of `STOP_AT` that `date` cannot read, a missing binary, a wrong sha256 of a binary, or an unknown step name: status 2. The unknown step name is found only when its turn comes, after the steps before it have run ({L119}).
  - `STOP_AT` is empty or not set: the shell ends the script at {L15}. The line names no status. A test with bash 5.1.16 gave status 1.
  - Any other command that fails where no line handles the failure, for example `mkdir` in {L43}: the shell option `-e` ends the script with the status of that command ({L11}).
- The first three stop reasons are tested at these places: once before any file is written ({L32}), twice before each launch ({L61}, {L65}), in every turn of the wait for a quiet system ({L57}), once at the start of step A7 ({L114}), and once per second while a process runs ({L71}).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later ({L19}). After a stop by the marker file, the stop file or `STOP_AT`, the csv file gets a line that starts with `-- killed` ({L72}). After an interruption by a signal it gets no such line ({L31}).
- Before a launch the script waits until at most 2 tasks are runnable. It tests this every 2 s, for at most 20 s. After 20 s it starts the process without a message ({L57}). There is no fixed pause. The header line of each process gives the waited seconds as `waited_s`.
- For each launch the script records the load in two places. `launches.txt` gets a line with the load averages and the number of logins, and the 5 processes with the highest `pcpu` value of `ps` ({L64}). `pcpu` is the CPU time of a process divided by the time from its start to now. So it is an average over the life of the process, not the CPU use at the launch. The header line of the process in the csv file gets the waited seconds, the load averages, the number of logins, the UTC time and the options ({L66}).
- While a benchmark runs, the script starts one `date` process and one `sleep` process per second ({L26}, {L73}). They may run on any of the CPUs 0 to 119. In the steps with 120 threads each of these CPUs also runs one pinned benchmark thread.
- An old kernel and a hand-written kernel never come from the same binary: `read_old` and `write_old` run in `bw_old`, and `asmread` and `asmwrite` run in `bw_new` ({L80}).
- Step A3 is skipped without an error when less than 70 GiB of memory are available. The message goes to `env.txt` and to the error output ({L94}).
- The second process of an A5 pair does not always start at once. It starts after the same wait for a quiet system as every other process ({L105}).
- The script deletes nothing. At every stop the files that were written before stay. The end line of `env.txt` is written only when no stop ended the script before ({L121}). A skipped step A3 does not prevent the end line ({L94}).
- The text of this file is the text that ran on CRB on 2026-11-13, in two calls: first the steps A7, A5 and A6, then the steps A1 to A4 [Ref1]. The comment of {L10} is older than that run.

## References

- [Ref1] the files `env.txt` of the result folders `partA-20261113T204939Z` and `partA-20261113T205055Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. Their first lines end with `steps=A7 A5 A6` and with `steps=A1 A2 A3 A4`. In each file the list after the line `## sha256:` gives `0f496ca60a1127880ae48ef14a63d28205dce3d9d8bc9edb7feefbf28f84d167` for `run_partA.sh`. The file in the code folder has the same sha256.
- [Ref2] the file `probe.txt` of the result folder `kernels-20261113T181222Z` in the same test folder. The list after its line `## sha256:` gives the two values of {L37-38} for `bw_old` and `bw_new`.
- [Ref3] external source: Linux kernel documentation, "Transparent Hugepage Support", the settings `enabled` and `defrag` and the counters `thp_fault_alloc`, `thp_fault_fallback` and `thp_collapse_alloc`: https://www.kernel.org/doc/html/latest/admin-guide/mm/transhuge.html
- [Ref4] external source: Linux manual page `proc_loadavg(5)`, the five fields of `/proc/loadavg`: https://man7.org/linux/man-pages/man5/proc_loadavg.5.html
- [Ref5] external source: Linux kernel documentation, "Scalable Vector Extension support for AArch64 Linux", the file `/proc/sys/abi/sve_default_vector_length`: https://www.kernel.org/doc/html/latest/arch/arm64/sve.html
