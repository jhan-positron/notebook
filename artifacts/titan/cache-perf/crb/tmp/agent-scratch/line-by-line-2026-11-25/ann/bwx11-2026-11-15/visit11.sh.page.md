## Short version: purpose

`visit11.sh` makes one visit to CRB from the agent server for round 4: one `ssh` login that first checks the marker file and then starts `run_bwx11.sh` with the settings and the steps of the caller. Before the login it checks that `STOP_AT`, `SESSION` and the log name are given, and that six of the settings hold no character that could change the remote command (the setting `ENVV` and the arguments are not checked). It writes everything that the login prints to a log file on the agent server.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Round 4**: the fourth set of tests of the investigation into the buffer size of 8 MiB. Its steps have names that start with `Z`.
- **Visit**: one login to CRB that starts one script.
- **Run script**: the script `run_bwx11.sh` on CRB. It runs the processes of the steps that it gets as arguments.
- **Step**: one batch of processes of a round, for example `ZD`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **`STOP_AT`**: a UTC time that the caller sets, or the word `none`. The run script starts no process that could run past that time.
- **Session 1, session 2**: the two runs of the same steps. Session 2 repeats session 1 at least 3 hours later. `SESSION` selects one of them, and `SESSION1_END` gives the UTC time at which session 1 ended.
- **Block**: a time window that another user has reserved on CRB.
- **Digest**: the sha256 of a file. The three digest settings `BWX8_SHA256`, `BWX10_SHA256` and `BWX11_SHA256` give the checksums that the three runner binaries must have.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **`ENVV`**: an optional text with more settings for the run script, for example `RESERVE=90`.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when `STOP_AT`, `SESSION` or the log name is missing ({L10}).
2. Stop when one of six settings holds a character that could split or change the remote command ({L12-14}).
3. Set the path of the log file from the first argument ({L15}).
4. Open one `ssh` connection to CRB. The remote command checks the marker file, goes to the folder `~/cache-perf/bwx11-20261115` and starts `run_bwx11.sh` with the settings and the steps ({L16-18}).
5. Append the exit status of `ssh` and the UTC time to the log file ({L19}).

## Behavior a reader must know

- This script starts benchmark processes on CRB. The marker check is the first remote action. When the marker file exists, the remote command ends with exit status 3 and starts nothing.
- A missing `STOP_AT`, `SESSION` or log name ends the script with exit status 1 before the login ({L10}). A forbidden character in one of the six checked settings ends it with exit status 2 before the login ({L13}).
- `ENVV` is not checked. Its text goes into the remote command line as it is.
- The script makes exactly one login and waits until the remote command has ended.
- The exit status of the run is not the exit status of this script. It stands in the last line of the log file, after the words `ssh status`.
- The script has no `set -e`. After a failed `ssh` it still writes the status line.
