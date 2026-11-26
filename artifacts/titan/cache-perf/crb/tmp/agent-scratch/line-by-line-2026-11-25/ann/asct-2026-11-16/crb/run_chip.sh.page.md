## Short version: purpose

`run_chip.sh` runs the many-core part of the ASCT cross-check on CRB. Each process is one start of the ASCT benchmark binary with one read thread per CPU of a layout, up to 120 threads, and a buffer of 256 MiB per thread. The steps change the number of injected NOPs, the layout, the mix of reads and writes, and one step adds counters.

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
- **Traffic type**: the value of the option `--bw-write` of the ASCT binary. 0 means that all accesses are reads. The values 2 to 5 mix reads and writes.
- **Non-temporal store**: a store that tells the processor that the program will not read the data again soon.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Layout**: the CPUs that get a thread. The name gives the threads on mesh 0 and on mesh 1: `6456` is 64 plus 56 threads, written 64+56.
- **Whole chip, 120 threads**: our runs use the CPUs 0 to 119 only: 64 threads on mesh 0 plus 56 threads on mesh 1.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one process. It is the name of its output file without the ending `.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next process when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists ({L12-13}).
2. Read the settings: the steps, the length of the measured phase and the fixed buffer size of 256 MiB per thread ({L14-18}).
3. Create the result folder, write the start state to `env.txt` and copy `events.codes` ({L19-22}).
4. Step `BASE`: 6 processes at 64+56 with 0 injected NOPs. Each process goes through the function `one`. It checks the two stop files, waits for a quiet machine, pauses 5 s, starts the binary with one `--bw-cpu` option per CPU (function `cpuflags`), watches the marker file and writes the exit status ({L46}).
5. Step `DEF`: 3 processes of the same case with a measured phase of 0.25 s ({L47}).
6. Step `NOPS`: 15 counts of injected NOPs at 64+56, first in rising order, then in falling order ({L48-52}).
7. Step `LAY`: the layouts 64+0, 0+56 and 56+56 at 0 and at 20 injected NOPs, 2 processes each ({L53-55}).
8. Step `MIX`: the traffic types 2 to 5 at 64+56, 2 processes each ({L56-58}).
9. Step `CNT`: the probe binary with each event set, at 64+56 with 0 and with 20 injected NOPs and at 64+0 with 0 injected NOPs ({L59-68}).
10. Print a short summary ({L69-72}).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures. By the decisions file, the rate of one process is the line `Total Bandwidth (MB/sec)` of its output, divided by 1000 to give GB/s [Ref1].
- By the description text of the analysis script `analyze.py`, the rate of one thread is its repetitions times the buffer size, divided by its time. The binary prints the repetitions and the time of each thread in a line that starts with `tid = `. A repetition is one pass over the buffer.
- By the decisions file, ASCT counts 64 bytes for each cache line, although its read loop loads 8 bytes of the line. The total of ASCT is the sum of the rates of the threads, and the threads measure over time spans of different length [Ref1].
- Thread placement: the script limits each process to the CPUs 0 to 119 (`taskset`) and passes one `--bw-cpu` option per CPU of the layout. The binary runs one read thread on each of these CPUs. The buffer is allocated inside the ASCT binary, whose source is not in this repo.
- One process runs at a time. Before each process the script waits until at most 2 tasks are runnable (at most about 60 s) and then 5 s more.
- Stops: the marker file and the STOP file before every process (exit status 3 and 4). During a process only the marker file is checked, once per second. When it appears, the script sends the termination signal to the process and ends with exit status 3.
- The exit status of a benchmark process is written to `launches.txt` but not tested.
- The steps run in the order of the file. The order of the words in `STEPS` does not change this.
- A wrong layout name does not stop the script ({L25}). The binary would start without any `--bw-cpu` option. The layout names of this file are fixed in {L46-63}, so the case cannot happen without a change of the file.
- With the default settings and 7 event sets the script starts 80 processes: 6, 3, 30, 12, 8 and 21 for the six steps. The run of 2026-11-16 23:19 UTC started 80 processes [Ref2].
- That run used an earlier text of {L36} with the variable `r`. 8 result files of the steps `LAY` and `MIX` were overwritten. The two steps ran again at 23:44 UTC, after the variable got the name `rq` [Ref1].

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Readings fixed now", "Added 2026-11-16 23:37 UTC" and "Record of 2026-11-16 23:50 UTC".
- [Ref2] `launches.txt` and `env.txt` in the result folder `asct-chip-20261116T231956Z` of the test folder `2026-11-16-asct-cross-check`: 80 `launch` lines and the line `STEPS BASE DEF NOPS LAY MIX CNT DUR 2`.
