## Short version: purpose

`hostwatch.py` is the host sampler: while one benchmark process runs, it reads files under `/proc` 20 times per second and writes what changed for that process and on its CPU. The run scripts `run_bwx9.sh`, `run_bwx10.sh` and `run_bwx11.sh` start it beside every process of a step that has a `.watch` file. Its output file shows scheduler activity, interrupts, memory statistics and the threads of other processes on the watched CPU, each with a time on one clock.

## Words used here

- **Host sampler**: this program. It records what the Linux kernel does on one CPU while one process runs.
- **Target**: the watched process, given with `--pid`. The run script gives the process id of the benchmark.
- **Watched CPU**: the CPU given with `--cpu`. The run script gives the CPU of the benchmark from its schedule.
- **Run script**: the script that starts the benchmark processes of a step and, beside them, this sampler.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Process**: one start of a benchmark binary.
- **`/proc`**: a folder in which Linux shows its state as text files. Reading such a file changes no setting.
- **Sample**: one reading of all watched files at one time.
- **Sample grid, slot**: the planned sample times. They lie one period apart, 50 ms at 20 samples per second. A slot is one of these times.
- **Key**: the name of one value in the output, for example `w.run_ns`.
- **Delta line**: a sample line that holds only the values that changed, each as a difference to the last sample.
- **Absolute line**: a sample line with the word `ABS` that holds the full value of every key.
- **State item**: an item of the form `key:=value`. It gives a new state and not a difference.
- **Scan**: one pass over all threads of the host. It finds the threads of other processes whose last CPU is the watched CPU.
- **Tracked thread**: a thread of another process that a scan found on the watched CPU. The sampler reads its values in every sample.
- **Thread id (`tid`), process id (`pid`)**: the numbers that Linux gives to a thread and to a process.
- **`comm`**: the command name of a process or thread, as Linux shows it.
- **Time slice**: one uninterrupted period in which a thread runs on a CPU.
- **Context switch**: the moment at which Linux takes a thread off a CPU. It is voluntary when the thread waits for something, and involuntary when Linux takes the CPU away.
- **Page fault**: the event in which a thread touches a memory page that Linux must first provide. It is minor when no disk read is needed, and major when one is needed.
- **Clock tick**: the unit in which Linux reports the CPU time and the start time of a process. `SC_CLK_TCK` gives the number of ticks per second.
- **Soft interrupt**: a piece of work that the Linux kernel puts off to a later moment, for example work for timers or for the network.
- **`CLOCK_MONOTONIC`**: a Linux clock that only moves forward. All sample times come from it.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Read the options `--pid`, `--cpu`, `--out`, `--hz` and `--max-s`, and check their values ({L393-401}).
2. Set the handler for the signals SIGTERM and SIGINT, and open the output file ({L402-404}).
3. Write four header lines: the settings, three clocks, the start time and the name of the target, and the CPU list of the sampler ({L412-418}).
4. Scan all threads of the host once. Write one `# th` line per thread of another process whose last CPU is the watched CPU, and one scan line ({L419-422}).
5. Start the sample grid and take one sample per slot ({L423-434}). A sample reads the threads of the target, the line of the watched CPU in `/proc/schedstat`, `/proc/softirqs`, the tracked threads, `/proc/vmstat` and, twice per second, `/proc/interrupts` ({L347-354}).
6. Write a delta line when something changed, and an absolute line as the first line and then every 5 s ({L355-389}, {L443-444}).
7. Leave the loop when the time limit is over or when the target is gone ({L429-431}, {L448-449}).
8. Between two samples, run a part of a new scan every 2 s, count skipped slots, and sleep until the next slot ({L454-475}).
9. Write the footer line with the end reason and the counters, and close the file ({L481-485}).

## Behavior a reader must know

- The sampler only reads. It opens files under `/proc` for reading and writes one file, the one named by `--out`.
- The sampler pins nothing. The run script pins it with `taskset` to a CPU that is not a CPU of the benchmark. The fourth header line of the output records the CPU list that the sampler really has ({L418}).
- Every sample line starts with one time: `CLOCK_MONOTONIC` in ns, read once before the files of the sample are read ({L428}). The files are read one after the other, so the values of one line are not from exactly the same moment.
- The sampler ends in four ways. The footer line names the way ({L484}).
  - The target is gone: reason `pid_gone`, exit status 0.
  - The time limit `--max-s` is over: reason `max_s`, exit status 0.
  - The signal SIGTERM or SIGINT arrives: reason `signal`, exit status 0.
  - An error outside a sample: reason `error`, exit status 1.
- A wrong option ends the program with exit status 2 before any file is written ({L399-401}).
- An error inside a sample or inside a scan does not end the sampling. It is counted in `errors` and written as an item `hw.error:=` ({L437-439}, {L465-468}).
- A sample or a part of a scan that takes too long makes the loop skip grid slots. The skipped slots are counted in `missed` and reported with the item `hw.missed:=` ({L469-471}).
- At most 512 threads of other processes are tracked at one time ({L58}, {L327}).
- An absolute line leaves out every interrupt key whose count is 0 ({L384}).
- A file without the footer line means that the sampler did not end normally. The run script prints a warning for such a file.
- The folders `bwx8-2026-11-14`, `bwx10-2026-11-15` and `bwx11-2026-11-15` hold the same text of this file.

## References

- [Ref1] external source: Linux kernel documentation, page "Scheduler Statistics" (https://docs.kernel.org/scheduler/sched-stats.html). It gives the 9 values of a CPU line of `/proc/schedstat` and the 3 values of the file `schedstat` of a process.
- [Ref2] external source: Linux manual page `proc_pid_stat(5)` (https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html). It gives the numbered fields of the file `stat` of a process: 3 state, 10 minor faults, 12 major faults, 14 user time, 15 system time, 22 start time, 39 last CPU.
