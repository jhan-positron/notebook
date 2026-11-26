## Short version: purpose

`visit8.sh` makes one visit to CRB from the agent server for round 1: one `ssh` login that first checks the marker file and then starts `run_bwx8.sh` with the settings and the steps of the caller. Before the login it checks that `STOP_AT`, `SESSION` and the log name are given, and that four of the settings hold no character that could change the remote command. It writes everything that the login prints to a log file on the agent server.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Round 1**: the first set of tests of the investigation into the buffer size of 8 MiB. The script `run_bwx8.sh` runs its steps.
- **Design**: the file `tackle-8mb.md`, the plan of the investigation.
- **Visit**: one login to CRB that starts one script.
- **Run script**: the script `run_bwx8.sh` on CRB. It runs the processes of the steps that it gets as arguments.
- **Step**: one batch of processes of a round, for example `S2`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **`STOP_AT`**: a UTC time that the caller sets, or the word `none` for no limit. The run script starts a process only when that time is more than a margin away. The margin is the planned work of the longest process of the step plus a reserve.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later. `SESSION` selects one of them, and `SESSION1_END` gives the UTC time at which session 1 ended.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file. The digest setting `BWX8_SHA256` gives the checksum that the runner binary `bwx8` must have.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **`ENVV`**: an optional text with more settings for the run script, each in the form `NAME=value`. The handoff note of the investigation names one use: the two counter settings `BWX_PMU_TYPE` and `BWX_EVENTS`, which the steps with hardware counters need.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Stop when `STOP_AT`, `SESSION` or the log name is missing ({L8}).
2. Stop when one of four settings holds a character that could split or change the remote command ({L10-12}).
3. Set the path of the log file from the first argument ({L13}).
4. Open one `ssh` connection to CRB. The remote command checks the marker file, goes to the folder `~/cache-perf/bwx8-20261114` and starts `run_bwx8.sh` with the settings and the steps ({L14-16}).
5. Append the exit status of `ssh` and the UTC time to the log file ({L17}).

## Behavior a reader must know

- This script starts benchmark processes on CRB. The marker check is the first remote action. When the marker file exists, the remote command ends with exit status 3 and starts nothing.
- A missing `STOP_AT`, `SESSION` or log name ends the script with exit status 1 before the login ({L8}). A forbidden character in one of the four checked settings ends it with exit status 2 before the login ({L11}).
- `ENVV` is not checked. Its text goes into the remote command line as it is. The arguments after the log name are not checked either ({L16}).
- A setting that the caller leaves out reaches the run script as an empty value ({L16}). The run script treats an empty `SESSION1_END` and an empty `BWX8_SHA256` as not set. So without `BWX8_SHA256` the run script does not check the digest of the binary.
- The script makes exactly one login and waits until the remote command has ended.
- The log file is written new at every call that reaches the login. A log file with the same name is replaced ({L16}). A call that ends at {L8} or {L11} writes no log file.
- The exit status of the run is not the exit status of this script. It stands in the last line of the log file, after the words `ssh status`. The value 255 there means that `ssh` itself failed. The repo holds two logs of this form with the steps `B6W`, `S2` and `S4`, one per session. Both end with `ssh status 0` [Ref1].
- The value 3 there has two possible sources: the marker check of the remote command ({L14}), or the run script, which also ends with exit status 3 when the marker file exists. Both mean that the marker file was found.
- The script has no `set -e`. After a failed `ssh` it still writes the status line.
- The script `visit9.sh` of the same folder differs from this script only in its comment lines and in the name of the script that it starts ({L16}).

## References

- [Ref1] the log files `visit8-s1-B6W-S2-S4.log` and `visit8-s2-B6W-S2-S4.log` in `tests/2026-11-15-tackle-8mb/logs/` of the repo `arm-crb`. Their last lines are `ssh status 0 utc 2026-11-15T01:20:18Z` and `ssh status 0 utc 2026-11-15T05:09:39Z`.
