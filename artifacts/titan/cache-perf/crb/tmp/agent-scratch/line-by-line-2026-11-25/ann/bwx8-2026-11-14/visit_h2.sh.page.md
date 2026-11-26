## Short version: purpose

`visit_h2.sh` makes one visit to CRB from the agent server for step H2: one `ssh` login that first checks the marker file and then starts `run_h2.sh` with the settings and the options of the caller. Before the login it checks that `STOP_AT`, `SESSION` and the log name are given, and that three of the settings hold no character that could change the remote command. It writes everything that the login prints to a log file on the agent server.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Visit**: one login to CRB that starts one script.
- **Step H2, hypothesis H2**: hypothesis H2 says that the original gain of 0.94 % at a buffer size of 8 MiB was measured while the new read kernel was at its low level. Step H2 tests it: it runs the two original binaries `bw_old` and `bw_new` many times at 8 MiB.
- **Gain**: the rate of the new read kernel divided by the rate of the old read kernel, minus 1, in percent.
- **Low level**: a term of the decision rule of step H2 in the note `DECISIONS-bwx8.md`. By that rule a repetition of the new read kernel is low when its rate is at or below 69.5 GB/s, and high when its rate is at or above 70.5 GB/s.
- **Run script**: the script `run_h2.sh` on CRB. It starts the 72 processes of one session of step H2, one at a time.
- **`bandwidth.c`, `bw_old`, `bw_new`**: the benchmark and its two binaries of 2026-11-13. `bw_old` was built from the old source (`bandwidth.orig.c`), `bw_new` from the new source (`bandwidth.c`).
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Read kernel**: the kernel that reads memory.
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **Rate**: bytes divided by time, in GB/s.
- **Process**: one start of a benchmark binary.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **`STOP_AT`**: a UTC time that the caller sets, or the word `none` for no limit. The run script starts a process only when that time is more than a margin away. The margin is the planned work of one process plus a reserve.
- **Session 1, session 2**: the two runs of step H2. Session 2 repeats session 1 at least 3 hours later. `SESSION` selects one of them, and `SESSION1_END` gives the UTC time at which session 1 ended.
- **Block**: a time window that another user has reserved on CRB.
- **`ENVV`**: an optional text with more settings for the run script, each in the form `NAME=value`, for example `RESERVE=90`. `RESERVE` is the reserve of the margin, in seconds.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Stop when `STOP_AT`, `SESSION` or the log name is missing ({L9}).
2. Stop when one of three settings holds a character that could split or change the remote command ({L11-13}).
3. Set the path of the log file from the first argument ({L14}).
4. Open one `ssh` connection to CRB. The remote command checks the marker file, goes to the folder `~/cache-perf/bwx8-20261114` and starts `run_h2.sh` with the settings and the options ({L15-17}).
5. Append the exit status of `ssh` and the UTC time to the log file ({L18}).

## Behavior a reader must know

- This script starts benchmark processes on CRB. The marker check is the first remote action. When the marker file exists, the remote command ends with exit status 3 and starts nothing.
- A missing `STOP_AT`, `SESSION` or log name ends the script with exit status 1 before the login ({L9}). A forbidden character in one of the three checked settings ends it with exit status 2 before the login ({L12}).
- `ENVV` is not checked. Its text goes into the remote command line as it is. The arguments after the log name are not checked either ({L17}).
- The script takes no step names. The run script ends with exit status 2 for every argument other than `--dry-run` and `--from IDX`.
- A `SESSION1_END` that the caller leaves out reaches the run script as an empty value ({L17}). The run script treats it as not set. It needs the value only for session 2.
- The script makes exactly one login and waits until the remote command has ended.
- The log file is written new at every call that reaches the login. A log file with the same name is replaced ({L17}). A call that ends at {L9} or {L12} writes no log file.
- The exit status of the run is not the exit status of this script. It stands in the last line of the log file, after the words `ssh status`. The value 255 there means that `ssh` itself failed. The repo holds two logs of this form, one per session of step H2. Both end with `ssh status 0` [Ref1].
- The value 3 there has two possible sources: the marker check of the remote command ({L15}), or the run script, which also ends with exit status 3 when the marker file exists. Both mean that the marker file was found.
- The script has no `set -e`. After a failed `ssh` it still writes the status line.
- The script differs from `visit8.sh` of the same folder in its comment lines ({L2-4}, {L7}, {L10}) and in three things of the code: three checked settings in place of four ({L11}), no `BWX8_SHA256` in the remote command, and the name of the script that it starts ({L17}).

## References

- [Ref1] the log files `visit-h2-s1.log` and `visit-h2-s2.log` in `tests/2026-11-15-tackle-8mb/logs/` of the repo `arm-crb`. Their last lines are `ssh status 0 utc 2026-11-15T06:37:40Z` and `ssh status 0 utc 2026-11-15T11:27:22Z`.
