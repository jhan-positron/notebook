## Short version: purpose

`run_single.sh` runs the one-core part of the ASCT cross-check on CRB. Each process is one start of the ASCT benchmark binary with one read thread on CPU 2 or CPU 41 and one buffer size, with or without counters and injected NOPs. The script stores the output of every process in a new result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Probe binary, probe variant**: the same benchmark program, built by `prep.sh` with the flag `-DUSE_PROBE`. It holds the counter code of ASCT.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter capture**: the counter code of ASCT inside the probe binary. It reads a list of raw codes from the environment variable `DIETPERF_PMUv3`. It writes its counter files to the folder that `DIETPERF_OUTDIR` names.
- **Raw code**: the number that selects one counter event in the counter unit of the cores.
- **Event set**: a named list of counter events that one process counts together. The file `events.codes` holds one set per line.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Part U, N, C, NC**: the four parts of the one-core runs. U: no counters. N: injected NOPs, no counters. C: counters. NC: injected NOPs with counters.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next process when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists ({L10-11}).
2. Read the settings from the environment: the processes per case, the length of the measured phase, the parts, the buffer sizes and the two CPUs ({L12-19}).
3. Create the result folder, write the start state to `env.txt` and copy `events.codes` ({L20-24}).
4. Part U: for each size and each CPU, run the installed binary without counters, `REPS` times. Each run goes through the function `one`, which checks the two stop files, writes a `launch` line, runs the binary and writes its exit status ({L35-39}).
5. Part C: for each event set, size and CPU, run the probe binary with the counters of the set, `CREPS` times ({L40-50}).
6. Part N: run the installed binary with 1, 2, 4 and 8 injected NOPs at 32 KiB, 1 MiB and 8 MiB on each CPU, `NREPS` times ({L51-56}).
7. Part NC, only when `PARTS` names it: run the probe binary with 1, 2 and 4 injected NOPs and the sets `A`, `B` and `E` at 1 MiB and 8 MiB on each CPU, `CREPS` times ({L57-68}).
8. Print a short summary ({L69-72}).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures. By the decisions file, the rate of one process is the line `Total Bandwidth (MB/sec)` of its output, divided by 1000 to give GB/s [Ref1].
- By the description text of the analysis script `analyze.py`, the rate of one thread is its repetitions times the buffer size, divided by its time. The binary prints the repetitions and the time of each thread in a line that starts with `tid = `. A repetition is one pass over the buffer.
- By the decisions file, ASCT counts 64 bytes for each cache line, although its read loop loads 8 bytes of the line [Ref1].
- Thread placement: the script limits each process to the CPUs 0 to 119 (`taskset`) and passes one CPU with `--bw-cpu`. The binary runs its one read thread on that CPU. The buffer is allocated inside the ASCT binary, whose source is not in this repo. By the text of the report script `dyn_notes.py`, the ASCT code allocates the buffer with `posix_memalign` and does not ask for huge pages.
- One process runs at a time. The two CPUs never run at the same time. The script does not wait for a quiet machine and does not pause between two processes.
- The parts run in the order of the file: U, C, N, NC. The order of the words in `PARTS` does not change this.
- The order inside a part alternates: odd rounds run CPU `CA` first and the sizes upward, even rounds run CPU `CB` first and the sizes downward. The parts N and NC alternate the CPU order only.
- The marker file and the STOP file are checked before every process, not during a process. The exit statuses are 3 for the marker file and 4 for the STOP file.
- The exit status of a benchmark process is written to `launches.txt` but not tested.
- With the default settings and 7 event sets, part U starts 256 processes, part C 448 and part N 96. The first run of 2026-11-16 started these 800 processes in this order [Ref2]. Part NC starts 72 processes. A second run with `PARTS` set to `NC` started them [Ref3].

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Runs" and "Readings fixed now".
- [Ref2] `launches.txt` and `env.txt` in the result folder `asct-single-20261116T231240Z` of the test folder `2026-11-16-asct-cross-check`: 800 `launch` lines, first 256 with a tag that starts with `u`, then 448 with `c`, then 96 with `n`.
- [Ref3] `env.txt` in the result folder `asct-single-20261116T233721Z` of the same test folder (`PARTS NC`), and the file `logs/nc.log` (`processes 72`).
