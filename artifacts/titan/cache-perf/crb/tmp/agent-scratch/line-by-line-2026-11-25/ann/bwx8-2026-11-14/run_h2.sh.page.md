## Short version: purpose

`run_h2.sh` runs one session of step H2, the test of hypothesis H2, on CRB: 72 processes of the two original benchmark binaries `bw_old` and `bw_new`, one at a time, each with one thread, a buffer of 8 MiB and the read kernel only. Before every launch it tests three stop reasons, waits for a quiet system and records the load of the machine. It stops when the marker file or the stop file exists, when the time `STOP_AT` is reached, when a process fails or when a signal interrupts it.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Step H2, hypothesis H2**: hypothesis H2 says that the original gain of 0.94 % at a buffer size of 8 MiB was measured while the new read kernel was at its low level [Ref5]. Step H2 tests it: it runs the two original binaries `bw_old` and `bw_new` many times at 8 MiB.
- **Investigation, round 1**: the investigation into the small gain at a buffer size of 8 MiB. Round 1 is its first set of tests. The run script of round 1 is `run_bwx8.sh`.
- **Handoff note**: a note of the project that tells the next worker what to do. This page names two. `tackle-8mb-handoff.md` is the handoff note of the investigation. It holds hypothesis H2 [Ref5]. `handoff.md` is the handoff note of the test plan of 2026-11-13 [Ref2].
- **Gain**: the rate of the new read kernel divided by the rate of the old read kernel, minus 1, in percent.
- **Low level, high level**: the two rates between which a load-only kernel, such as the new read kernel, switches at a buffer size of 8 MiB, by the handoff note `tackle-8mb-handoff.md` [Ref5]. The decision rule of step H2 in the note `DECISIONS-bwx8.md` counts a repetition of the new read kernel as low when its rate is at or below 69.5 GB/s, and as high when its rate is at or above 70.5 GB/s.
- **Original run**: the run of `bw_old` and `bw_new` with the script `run_kernels.sh` on 2026-11-13 [Ref3].
- **`run_kernels.sh`**: the run script of the original run. It builds `bw_old` and `bw_new` and runs them. Its text in the code folder was changed on 2026-11-24. This page compares with its text of 2026-11-13 [Ref4].
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Repetition**: one interval of a process of `bw_old` or `bw_new`. The option `--reps` gives the number of repetitions per kernel, and `--min-ms` gives the shortest length of each.
- **Warm-up pass**: one pass of the kernel over the buffer that the benchmark makes before each repetition. It is not timed.
- **Whole-pass stop**: the stop rule of `bandwidth.c`: after the minimum time each thread finishes the pass over its buffer that it is in. The threads stop at different times.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Session 1, session 2**: the two runs of step H2. Session 2 repeats session 1 at least 3 hours later, with the reverse CPU order and the reverse first binary of each pair. `SESSION` selects one of them, and `SESSION1_END` gives the UTC time at which session 1 ended.
- **Pair**: one process of `bw_old` and one process of `bw_new` that run one after the other on one CPU. Each CPU gets 12 pairs per session.
- **`pos`**: the place of a process in its pair: 1 for the process that runs first, 2 for the other.
- **`idx`, tag**: `idx` is the number of a process in the order of a session, from 0 to 71. The tag is the short name of a process, for example `s1-c2-p01-old`: session 1, CPU 2, pair 1, binary `bw_old`.
- **Nominal kernel work**: the sum of the shortest lengths of the timed repetitions: 3 times 500 ms, that is 1500 ms, for one process, and 108 s for the 72 processes of a session. The real run time is longer.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Stop file**: the file `~/cache-perf/STOP` on CRB. We create it from another login to stop this script.
- **`STOP_AT`**: a UTC time that the caller sets. A process starts only when this time is more than `MARGIN` seconds away, and a process that still runs at this time is ended. The value `none` sets no limit.
- **`RESERVE`, `MARGIN`**: `RESERVE` is an estimate of the time that one process needs beside its kernel work, 90 s when the variable is not set or is empty. `MARGIN` is the nominal work of one process, rounded up to whole seconds, plus `RESERVE`: 92 s with the default.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Test variable**: one of the six variables `H2_DIR`, `H2_SHA256_OLD`, `H2_SHA256_NEW`, `BWX8_MARKER`, `BWX8_STOPFILE` and `BWX8_RESULTS`. They give other paths and other expected digests for local tests with dummy binaries.
- **Dummy binary**: a stand-in program for the benchmark. The local tests of this script use two.
- **Dry run**: a call with `--dry-run`. It prints what would run and starts nothing.
- **Output file, header line**: the output file is `H2.csv` in the result folder. Before the output of each process the script writes a header line into it. That line starts with `-- binary`.
- **Load record**: the lines that the script appends to the file `launches.txt` before a launch: the first four fields of `/proc/loadavg`, the number of logins and the 5 processes with the highest `pcpu` value.
- **`pcpu`**: a value that the tool `ps` prints for a process: the CPU time of the process divided by the time from its start to now, in percent.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **First touch**: the first write of a thread to its new buffer. Linux assigns the memory pages at that moment. The benchmarks do it before any timing.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Process group**: a set of processes that one signal can reach together.
- **Linux session**: a set of process groups. The tool `setsid` starts a program in a new one. It is not a session of the test.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. The header comment gives the purpose, the usage, the order of the processes, the settings and the exit statuses ({L1-39}).
2. Limit the script and everything that it starts to the CPUs 0 to 119 ({L40-41}).
3. Read the options, check `SESSION`, and print a warning for each test variable that is set and not empty ({L42-53}).
4. Set the stop controls: the paths of the marker file and of the stop file, the stop time, `RESERVE`, and the trap for an interruption ({L57-80}).
5. Set the folder of the binaries, the place of the result folders, the two expected digests, the kernel, the buffer size, the pairs per CPU and the CPU order of the session ({L106-115}).
6. Build the order of the 72 processes: CPU after CPU, 12 pairs on each CPU, with the first binary changing from pair to pair. Then check the `--from` value and compute `MARGIN` ({L118-132}).
7. For session 2 in a real run, refuse a start earlier than 3 hours after `SESSION1_END` ({L135-143}).
8. In a real run, check that both binaries exist and have the expected digests. Then test the stop reasons once ({L144-149}).
9. Print the summary line ({L152-154}).
10. In a dry run, print one command line per process and the number of lines, and end with exit status 0 ({L155-161}).
11. Test the stop reasons and the distance to `STOP_AT`, make the result folder and write `order.tsv` and `env.txt` ({L163-180}).
12. Run the processes one at a time with the function `one`. It tests the stop reasons, waits for a quiet system, records the load, writes the header line and starts the binary. Then it tests the stop reasons once per second until the binary ends ({L181-183}).
13. Append the end line to `env.txt` and print the path of the result folder ({L184-186}).

## Behavior a reader must know

- What one process runs ({L94}): the binary `bw_old` or `bw_new` with the options `--threads 1 --cpus <cpu> --bytes 8M --kernel read --reps 3 --min-ms 500`. The binary is the only thing that differs between the two processes of a pair.
- What the binary does with these options (functions `worker` and `main` of `bandwidth.orig.c` and of `bandwidth.c`): one worker thread pins itself to the CPU of `--cpus`, allocates a buffer of 8 MiB, asks Linux for transparent huge pages for it and writes it once (first touch). Then it makes 3 repetitions.
- What one repetition times: each repetition starts with one warm-up pass of the read kernel, which is not timed. Then the thread reads the clock, runs whole passes over the buffer and reads the clock after each pass. The repetition ends at the first clock read at which at least 500 ms have passed. This is the whole-pass stop. For each repetition the binary prints one row with the bytes, the elapsed time and the rate, and at the end one row with the best rate.
- The script times nothing. All timing happens inside the two binaries.
- The order of a session ({L115-128}): all 24 processes of one CPU run before the next CPU starts. Session 1 takes the CPUs 2, 0, 41 and session 2 the CPUs 41, 0, 2. On each CPU the pairs follow the order old, new, new, old, and so on in session 1, and new, old, old, new in session 2. So each binary runs first in 6 pairs and second in 6 pairs on every CPU.
- How a process differs from a process of the original run, although {L7} says `exactly`. The options of the binary are the same [Ref4]. At least these three things differ:
  - This script starts the binary in the background in its own process group. While the binary measures, the script starts one `date` process and one `sleep` process per second ({L71}, {L99}). They may run on any of the CPUs 0 to 119, also on the CPU of the benchmark thread. The original script started the binary in the foreground and started no program while it ran [Ref4].
  - Before each launch this script waits for a quiet system and writes the load record. The original script tested the marker file, wrote the header line and started the binary [Ref4].
  - Every process of this script except the first one follows another read process at 8 MiB. The original run had 8 read processes at 8 MiB, among processes of other kernels and sizes [Ref3].
- Six things stop the run with a message of the script. Each has its own exit status.
  - The marker file exists: status 3.
  - The stop file exists: status 5.
  - The time `STOP_AT` is reached: status 4. Before a launch the script also ends with status 4 when `STOP_AT` is `MARGIN` seconds away or less. The rule of {L75} is: stop when the current time plus `MARGIN` is at or after `STOP_AT`. So a process starts only when `STOP_AT` is more than `MARGIN` seconds away.
  - One of the signals INT, TERM or HUP arrives: status 130.
  - A process ends with a status other than 0: status 1. The next process does not start.
  - A wrong usage, a missing setting, a `--from` value above 71, a binary that is missing or has another digest, or a session 2 that would start too early: status 2.
- A seventh thing stops the run without a message of the script. With `set -e` ({L40}) the script ends when a command fails whose status the script does not test, for example when `mkdir` cannot make the result folder ({L165}) or when `order.tsv` or `env.txt` cannot be written ({L167-180}). The exit status is then the status of that command. It can be 1, the same value as for a failed process.
- All checks with status 2 run before the result folder is made and before the first process ({L45-48}, {L59-60}, {L130}, {L135-147}).
- The first three stop reasons are tested in a fixed order: the marker file, then the stop file, then `STOP_AT` ({L68-73}). When two of them hold, the first one gives the exit status.
- The first three stop reasons are tested at these places: once after the checks of the binaries ({L148}), once before the result folder is made ({L163}), twice before each launch ({L87}, {L91}), in every turn of the wait for a quiet system ({L80}), and once per second while a process runs ({L97}).
- A process that runs at a stop is ended: the signal TERM goes to its process group, and the signal KILL follows 1 s later ({L64}). Before that, the script appends a line that starts with `-- killed` to `H2.csv` ({L76}, {L98}).
- Before a launch the script waits until at most 2 tasks are runnable. The shell that reads the count is itself one of these tasks. The script tests the count every 2 s, for at most 20 s. After 20 s it starts the process without a message ({L80}). There is no fixed pause. The header line of the process records the waited seconds as `waited_s` ({L92}). So the second process of a pair does not always start directly after the first.
- For each launch the script records the load in two places. `launches.txt` gets a line with the first four fields of `/proc/loadavg` and the number of logins, and the 5 processes with the highest `pcpu` value ({L90}). The header line of the process in `H2.csv` gets the load average over 1 minute, the UTC time, the waited seconds, the first four fields of `/proc/loadavg` and the number of logins ({L92}).
- The load averages of these records include the benchmark processes of this script that ran in the minutes before. So from the second process on they do not show the load of other users alone.
- The list of the 5 processes does not show which processes are busy at the launch. `pcpu` is an average over the whole life of a process, not the CPU use of the last second.
- The file `env.txt` records the state of the machine at the start of the session, the sha256 of the two binaries and of this script, the command line of a process and the settings ({L171-180}). The end of the session adds the UTC time, the content of `/proc/loadavg` and three huge page counters ({L184-185}).
- A result folder holds five files: `H2.csv` with the header line and the output of every process, `launches.txt`, `env.txt`, `stderr.txt` with the error output of the binaries, and `order.tsv` with the planned order of all 72 processes.
- A process that ends with a status other than 0 gets a line that starts with `-- failed` in `H2.csv` ({L102}). The script does not test the output of a process. It tests the exit status only.
- The script pins no thread. It only limits itself and everything that it starts to the CPUs 0 to 119 ({L41}). The binary pins its worker thread to the CPU of `--cpus`. The main thread of the binary is not pinned.
- The script sets the CPU limit of {L41} only when the caller has not already set `_PINNED` to a text that is not empty. The restart under `taskset` needs a path of the script that can be executed, as in the call `./run_h2.sh` of `visit_h2.sh`, the script that starts this script on CRB through `ssh`.
- The script accepts only the two binaries of the original run, unless a test variable gives another digest. Their expected digests are fixed in {L110-111}, and the record of the original run gives the same two values [Ref3]. The script never builds a binary.
- A value of the form `${X:-default}` is the default when the variable `X` is not set or is empty. The script uses this form for `RESERVE`, for the six test variables and, in a dry run, for `STOP_AT` ({L49}).
- A dry run needs `SESSION` and a `--from` value below 72. It does not test the binaries, the digests, the stop reasons or the 3 hour rule of session 2 ({L135}, {L144}).
- The options of a process stand in four places as fixed text: the header comment ({L8}), the launch ({L94}), the dry run ({L157}) and the line for `env.txt` ({L178}). The nominal work of one process is a fixed number too ({L114}). The four texts are equal, and 1500 ms fits `--reps 3 --min-ms 500`. No line derives one of them from another. So a dry run prints a text of its own, not the command of {L94}.
- The script never repeats a process. A stopped session is continued with `--from IDX`, in a new result folder.
- The script deletes nothing. At every stop the files that were written before stay.
- The exit status is 0 only when every process from `FROM` on ran to its end, or after a dry run.
- The text of this file is the text that ran on CRB in both sessions of step H2 [Ref1]. The words `Never run on CRB` of {L39} are older than those runs.

## References

- [Ref1] the files `env.txt` of the two result folders `h2-s1-20261115T063514Z` and `h2-s2-20261115T112456Z` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`. In each file the list after the line `## sha256:` gives `97184bb2aca7fe43770a9db20f8a5199b77d60637ee3315f8995575334082016` for `run_h2.sh`. The file in the code folder has the same sha256.
- [Ref2] the file `report/handoff.md` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`, the handoff note of the test plan of 2026-11-13. Its section `Files` gives the expected sha256 of `bw_old` and of `bw_new`: the two values of {L110-111}. It names its `Ref4` as their source: the files `probe.txt` of the result folders `kernels-20261113T181222Z` and `kernels-20261113T183218Z`.
- [Ref3] the result folder `kernels-20261113T181222Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`, the record of the original run. The list after the line `## sha256:` of its file `probe.txt` gives the value of {L110} for `bw_old`, the value of {L111} for `bw_new`, and `6a91bbbe799b9279f99c693f44ef5852d5daa437a7e2469bf61c914b40b81842` for `run_kernels.sh`. Its file `one-thread.csv` holds 192 header lines. 8 of them name the kernel `read` and the size `8M`: one for each binary on each of the CPUs 0 and 2 in each of the rounds 1 and 2.
- [Ref4] the file `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh`, the text of `run_kernels.sh` of 2026-11-13. Its sha256 is the value that [Ref3] gives for `run_kernels.sh`. Its function `one` tests the marker file, writes the header line and starts the binary in the foreground with the options `--threads`, `--cpus`, `--bytes`, `--kernel`, `--reps 3` and `--min-ms 500`, in this order. It starts no other program while the binary runs. Commit `5062a35` of the repo `ai-proj` holds the same text as `arm-crb/code/kernels-2026-11-13/run_kernels.sh` (same sha256). The present file `run_kernels.sh` of the code folder has another sha256.
- [Ref5] the file `report/tackle-8mb-handoff.md` in `tests/2026-11-15-tackle-8mb/` of the repo `arm-crb`. The line under its title says that it was written on 2026-11-15 at 03:50 UTC. Its section `Short version` says that the original run showed a gain of 0.94 % at 8 MiB. Its list of terms defines the low level and the high level. Its table of hypotheses holds H2.
