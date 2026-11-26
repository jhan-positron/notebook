## Short version: purpose

`analyze.py` reads the result folders of the ASCT cross-check and writes one JSON file, which the project keeps as `asct.json`. For each process it takes the rates that the ASCT binary printed and, when the process counted events, the counts per 64-byte line. It also checks the files and lists every failed check as a problem.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **ASCT binary**: the benchmark program of ASCT, `loaded-latency-asct-sve.bin`. The run scripts start it directly. One start is one process.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Process**: one start of a benchmark binary.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Repetition**: one pass of a thread over its buffer in the measured phase. The ASCT binary prints the number of repetitions and the time of each thread.
- **Line**: one cache line of 64 bytes.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Median**: the middle value of a sorted list of values.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter capture**: the counter code of ASCT inside the probe binary. It reads a list of raw codes from the environment variable `DIETPERF_PMUv3`. It writes its counter files to the folder that `DIETPERF_OUTDIR` names.
- **Probe binary**: the ASCT binary built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT.
- **Raw code**: the number that selects one counter event in the counter unit of the cores.
- **Event set**: a named list of counter events that one process counts together. The file `events.codes` holds one set per line.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Cell**: all processes with the same settings, for example one CPU and one buffer size.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Mesh unit**: the counter unit that Linux shows for one mesh. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **`perf stat`**: the Linux command that counts events while another command runs.
- **Counting window**: one run of `perf stat -a` for the command `sleep` in the script `run_mesh.sh`.
- **`launches.txt`**: a file that each run script writes into its result folder. It gets one `launch` line before each process and one `rc` line after it.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. `main` takes the output file from argument 1 and the result folders from the later arguments. It picks the function for each folder by the start of the folder name ({L281-296}).
2. A one-core folder goes to `do_single`. For each output file of the parts U, N, NC and C it reads the total of the process with `parse_out` and appends it to the list of its cell. For the parts NC and C it also reads the counter files with `parse_counters`, which gives counts per line and two checks ({L121-166}).
3. A many-core folder goes to `do_chip`. For each read process it keeps sums and ranges per mesh and a lower bound of the total (`mesh_split`). For the processes with counters it keeps the smallest, the median and the largest count per line over the threads of each mesh ({L180-219}).
4. A mesh-counter folder goes to `do_mesh`. It reads the settings and the times from `launches.txt`, checks that each counting window lies inside the measured phase, and reads the counts from the result files of `perf stat` ({L222-278}).
5. For a preparation folder the texts of `env.txt`, `sha.txt` and `resolve.txt` are stored unchanged ({L291-294}).
6. Each folder of the steps 2 to 4 also gets a summary of `launches.txt`: the load at the starts and the exit statuses ({L103-118}). A preparation folder gets none.
7. The script writes everything as JSON to the output file. Then it prints one line per folder and the first 8 problems of the folder ({L297-302}).

## Behavior a reader must know

- The script times nothing. Every time and every repetition count comes from the output of the ASCT binary. How that binary times a thread is not visible in this repo, which does not hold the ASCT source. Its output gives one repetition count and one time per thread [Ref1]. The report text in `dyn_notes.py` says that every thread runs the same number of passes and measures its own time.
- Rate of a thread: repetitions times buffer bytes, divided by the time of that thread and by 1e9, in GB/s ({L50}). Total of a process: the number of the line `Total Bandwidth (MB/sec)` divided by 1000, in GB/s ({L40}).
- Every pass counts all bytes of the buffer. By the decisions file ASCT counts 64 bytes for each line, although its read loop loads 8 bytes of the line [Ref3].
- The total that ASCT prints is a sum of thread rates, and each thread has its own time. The value `floor` of {L176} divides all bytes of the process by the longest time of a thread. The decisions file added it as a lower bound after the many-core data was seen [Ref3].
- Count per line: the count of a counter file divided by the lines of the measured phase of the same thread, which is repetitions times buffer bytes divided by 64 ({L51}, {L77}).
- A failed check does not stop the script. It adds a text to the list `problems` of the folder, and the console report prints the first 8 of them. A value that fails a check stays in the output. Three things are left out, each with a problem text: an output file without a result ({L45-46}), a counter file that fits no thread of its output file ({L62-64}) and a mesh event that `perf stat` printed without a count ({L268-271}).
- The exit status of a process is counted in `rc_nonzero` but not tested. A process with another status than 0 is used when its output holds a total.
- These things stop the script, among others: a folder name of an unknown kind (exit status 1, {L296}), a missing file that the code opens without a test ({L225}, {L292-294}), a result line of a thread without a settings line ({L49}), a file name that does not have the expected form ({L60}, {L184}), and a field of a counter file that is not a number ({L70}).
- A counter folder that does not exist gives no counts and no problem text ({L59}).
- The list of a counted cell mixes the processes of all event sets. Its `rate` list holds every process. An event list holds only the processes that counted the event ({L151-153}, {L163-165}).
- In `asct.json` of this folder the list `mesh` is empty [Ref6]. So `do_mesh` has no result in the data of the report.
- The script `facts.py` of the same folder reads the output file.

## References

- [Ref1] The output file `u.2.8388608.1.out` in the result folder `asct-single-20261116T231240Z` of the test folder `2026-11-16-asct-cross-check`: the settings line of the thread with `buflen`, `inner_nops` and `tid`, the result line with `repetitions`, `tickdiff` and `time`, and the lines `Total Bandwidth (MB/sec)` and `Bandwidth Repetitions`. In this file 1702 repetitions of a buffer of 8388608 bytes in 0.249577 s give 57.2 GB/s, and the printed total is 57206.53 MB/sec.
- [Ref2] `launches.txt` in the result folders `asct-single-20261116T231240Z` and `asct-chip-20261116T231956Z` of the same test folder: the `launch` lines and the `rc` lines.
- [Ref3] `DECISIONS.md` in the folder `asct-2026-11-16`: the sections "How ASCT is used, and why not through `asct run`" (at most 6 events plus `cpu_cycles` per set), "Readings fixed now", "Added 2026-11-16 23:37 UTC" (the lower bound of a total) and "Record of 2026-11-16 23:50 UTC" (the mesh-counter runs did not happen).
- [Ref4] external source: Linux manual page `perf_event_open(2)`, the fields `time_enabled` and `time_running` and the text on multiplexing.
- [Ref5] external source: Linux manual page perf-stat(1), section "CSV FORMAT".
- [Ref6] `asct.json` in the folder `asct-2026-11-16`: the lists `single` (2 folders), `chip` (2 folders), `prep` (1 folder) and `mesh` (no entry).
