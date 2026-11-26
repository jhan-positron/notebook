# `visit.sh` explained, line by line

- Source file: `new-test-kernel/visit.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 10 lines, 808 bytes).
- sha256 of the source when this page was built: `f49e7f9392cc6705d02a51d6d306c51048fc2f73a6cb5dc21b89a31f1baa8df6`.

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

1. Take the name of the log from the first argument. The other arguments are the step names (lines 5 to 6).
2. Keep the text of the marker check in `M` (line 7).
3. Log in to CRB once. The remote command checks the marker file, goes to the folder of the runner and runs `run_bwx.sh` with the settings and the step names. The output of the login goes to the log file (lines 8 to 9).
4. Append the exit status of `ssh` and the UTC time to the log (line 10).

## Behavior a reader must know

- The script times nothing and starts no benchmark itself. `run_bwx.sh` starts the processes on CRB.
- The script has no `set -e`, and it tests no result. Its own exit status is the status of the last `echo`. How the visit ended stands only in the log, in the line `ssh status` (line 10).
- When `STOP_AT` of the caller is empty or not set, the script passes `STOP_AT=none`. The visit then has no stop time. `run_bwx.sh` alone refuses to run without `STOP_AT`.
- This script checks the marker file once, as the first command of the login (line 7). After that `run_bwx.sh` makes its own checks.
- The Slack check that line 4 asks for is not part of the script. The caller must do it before the call.
- The sha256 of line 9 is fixed in the file. So a visit runs only with the binary `bwx` that has this sha256.
- The log file is written new at every call. A second call with the same log name replaces the first log.
- The exit status in the log is the status of `ssh`. When the remote command reached `run_bwx.sh`, it is the status of that script: 0 when all steps ran, 1 when a benchmark failed, 2 for a wrong usage or a missing setting or binary, 3 for the marker file, 4 for `STOP_AT`, 5 for the stop file, 6 when a process was skipped for lack of memory, 130 after an interruption. The header comment of `run_bwx.sh` lists these values. A status of 255 means that `ssh` itself failed [Ref3].

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/visit.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (10 lines, 808 bytes, sha256 `f49e7f9392cc6705d02a51d6d306c51048fc2f73a6cb5dc21b89a31f1baa8df6`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# visit.sh - one visit to CRB for Parts B and C: marker check, then run_bwx.sh with the steps given.` | Comment: the name and the purpose of the file. One call is one visit to CRB for Parts B and C of the plan: one login that first checks the marker file and then runs the script `run_bwx.sh` with the steps of the call. |
| 3 | `# Usage: [STOP_AT=<UTC\|none>] [ENVV="NAME=value ..."] visit.sh <log name> STEP...` | Comment: the usage. Two optional environment variables come first. `STOP_AT` is a UTC time or the word `none`. `ENVV` is a text with settings of the form `NAME=value`, separated by spaces. The first argument is the name of the log. The other arguments are the step names for `run_bwx.sh`. |
| 4 | `# Run only after the Slack check of handoff.md. The log goes to new-test-kernel/<log name>.log.` | Comment: the script must run only after the Slack check of the handoff note. That note asks the caller to read, before every login, the Slack channel in which other users announce their blocks on CRB. A block is a time window that another user has reserved. This script does not make that check. The log goes to the file `<log name>.log` in the folder `new-test-kernel`. |
| 5 | `N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel` | `N`: the folder `new-test-kernel` on the agent server, as a fixed path. The log is written there. |
| 6 | `log=$N/$1.log; shift` | `log`: the path of the log file: the folder `N`, the first argument and the ending `.log`. `shift` drops the first argument. The arguments that are left are the step names. |
| 7 | `M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'` | `M`: the text of the marker check. The single quotes keep the local shell from changing it. The shell on CRB runs it as the first command of the login. When the marker file exists (`-e`), the remote command prints `RUNNING file present: stop` and ends with exit status 3. Nothing is started then. |
| 8 | `ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \` | Starts one `ssh` command to CRB (user `jhan`, address `192.168.2.45`). `BatchMode=yes`: `ssh` never asks for a password, and it fails when the key does not work. `ConnectTimeout=15`: it gives up when no connection is made within 15 s. `ServerAliveInterval=30`: it sends a test message when the server has sent no data for 30 s. The backslash at the end continues the command in line 9. |
| 9 | `  "$M; cd ~/cache-perf/bwx-20261113 && STOP_AT=${STOP_AT:-none} BWX_SHA256=5b702073586a536e85002a39eaf01c144167e4a494bdbe90353c8e2caad826f1 ${ENVV:-} ./run_bwx.sh $*" < /dev/null > "$log" 2>&1` | Continues line 8: the text that the shell on CRB runs. The local shell fills in the variables first. The text is the marker check `M`, then `cd` to `~/cache-perf/bwx-20261113`, then `./run_bwx.sh` with the step names (`$*`). `&&` starts the script only when `cd` worked. Three settings stand before the script name and hold for this call only. `STOP_AT`: the value of the caller, or `none` when it is empty or not set (`${STOP_AT:-none}`). `BWX_SHA256`: the sha256 that the binary `bwx` must have. If the binary differs, `run_bwx.sh` ends with status 2 before its first launch. The build record lists this value for `bwx` [Ref1]. `${ENVV:-}`: the settings of `ENVV`, or nothing. `< /dev/null`: `ssh` gets an empty input. `> "$log" 2>&1`: the output and the error messages of the login replace the content of the log file. |
| 10 | `echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"` | Appends one line to the log: the words `ssh status`, the exit status of the `ssh` command (`$?`), the word `utc`, and the UTC date and time of this moment. `ssh` returns the exit status of the remote command, or 255 when the connection failed [Ref3]. The remote command ends with the status of `run_bwx.sh`, with 3 after a marker stop of line 7, or with the status of a failed `cd`. The log `visit-s2-B7.log` of the test of 2026-11-14 ends with such a line: `ssh status 0 utc 2026-11-14T03:13:56Z` [Ref2]. The script `session2.sh` looks for the text `ssh status 0` in the log. The exit status of `visit.sh` itself is the status of this `echo`. It does not show how the visit ended. |

## References

- [Ref1] the file `build.txt` in `tests/2026-11-13-new-read-kernel/build-records/bwx-crb-build-2/` of the repo `arm-crb`. The list after its line `## sha256:` gives the value of line 9 for `bwx`.
- [Ref2] the file `logs/visit-s2-B7.log` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`: the log of one visit. Its last line is the line that line 10 wrote.
- [Ref3] external source: OpenSSH manual page `ssh(1)`, section "EXIT STATUS": `ssh` exits with the exit status of the remote command, or with 255 if an error occurred. https://man.openbsd.org/ssh.1
