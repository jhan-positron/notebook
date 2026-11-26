## Short version: purpose

`visit.sh` makes one visit to CRB, the Arm server under test, for Parts B and C of the test plan of 2026-11-13: one `ssh` login from the agent server that checks the marker file and then runs `run_bwx.sh` with the steps of the call. All output of the login goes to a log file. The script then appends the exit status of `ssh` and the UTC time to that log.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the plan.
- **Parts B and C**: the deciding measurements of the plan that need no root. They use the runner `bwx`. Part C also reads the counters of the cores. These are not the part C of the later rerun.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **`run_bwx.sh`**: the run script of Parts B and C on CRB. One call runs the steps that its arguments name, one process at a time, with the runner `bwx`.
- **Step**: one named batch of processes of Parts B and C, for example `B7` or `C3`.
- **Visit**: one login to CRB that runs one call of `run_bwx.sh`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Block**: a time window that another user has reserved on CRB.
- **`STOP_AT`**: a UTC time that the caller sets. `run_bwx.sh` starts no process that could run past it, and it ends a process that still runs at that time. The value `none` sets no limit.
- **`ENVV`**: a text with extra settings of the form `NAME=value` for `run_bwx.sh`. The caller sets it for the steps that need such settings.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Take the name of the log from the first argument. The other arguments are the step names ({L5-6}).
2. Keep the text of the marker check in `M` ({L7}).
3. Log in to CRB once. The remote command checks the marker file, goes to the folder of the runner and runs `run_bwx.sh` with the settings and the step names. The output of the login goes to the log file ({L8-9}).
4. Append the exit status of `ssh` and the UTC time to the log ({L10}).

## Behavior a reader must know

- The script times nothing and starts no benchmark itself. `run_bwx.sh` starts the processes on CRB.
- The script has no `set -e`, and it tests no result. Its own exit status is the status of the last `echo`. How the visit ended stands only in the log, in the line `ssh status` ({L10}).
- When `STOP_AT` of the caller is empty or not set, the script passes `STOP_AT=none`. The visit then has no stop time. `run_bwx.sh` alone refuses to run without `STOP_AT`.
- This script checks the marker file once, as the first command of the login ({L7}). After that `run_bwx.sh` makes its own checks.
- The Slack check that {L4} asks for is not part of the script. The caller must do it before the call.
- The sha256 of {L9} is fixed in the file. So a visit runs only with the binary `bwx` that has this sha256.
- The log file is written new at every call. A second call with the same log name replaces the first log.
- The exit status in the log is the status of `ssh`. When the remote command reached `run_bwx.sh`, it is the status of that script: 0 when all steps ran, 1 when a benchmark failed, 2 for a wrong usage or a missing setting or binary, 3 for the marker file, 4 for `STOP_AT`, 5 for the stop file, 6 when a process was skipped for lack of memory, 130 after an interruption. The header comment of `run_bwx.sh` lists these values. A status of 255 means that `ssh` itself failed [Ref3].

## References

- [Ref1] the file `build.txt` in `tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/` of the repo `arm-crb`. The list after its line `## sha256:` gives the value of {L9} for `bwx`.
- [Ref2] the file `logs/visit-s2-B7.log` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the log of one visit. Its last line is the line that {L10} wrote.
- [Ref3] external source: OpenSSH manual page `ssh(1)`, section "EXIT STATUS": `ssh` exits with the exit status of the remote command, or with 255 if an error occurred. https://man.openbsd.org/ssh.1
