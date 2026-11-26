# `visit_h2.sh` explained, line by line

- Source file: `bwx8-2026-11-14/visit_h2.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 18 lines, 1463 bytes).
- sha256 of the source when this page was built: `c7679b83553a417a126a6c64fe99bff3fe1651c330ebf3464b4cc723a30d843e`.

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

1. Stop when `STOP_AT`, `SESSION` or the log name is missing (line 9).
2. Stop when one of three settings holds a character that could split or change the remote command (lines 11 to 13).
3. Set the path of the log file from the first argument (line 14).
4. Open one `ssh` connection to CRB. The remote command checks the marker file, goes to the folder `~/cache-perf/bwx8-20261114` and starts `run_h2.sh` with the settings and the options (lines 15 to 17).
5. Append the exit status of `ssh` and the UTC time to the log file (line 18).

## Behavior a reader must know

- This script starts benchmark processes on CRB. The marker check is the first remote action. When the marker file exists, the remote command ends with exit status 3 and starts nothing.
- A missing `STOP_AT`, `SESSION` or log name ends the script with exit status 1 before the login (line 9). A forbidden character in one of the three checked settings ends it with exit status 2 before the login (line 12).
- `ENVV` is not checked. Its text goes into the remote command line as it is. The arguments after the log name are not checked either (line 17).
- The script takes no step names. The run script ends with exit status 2 for every argument other than `--dry-run` and `--from IDX`.
- A `SESSION1_END` that the caller leaves out reaches the run script as an empty value (line 17). The run script treats it as not set. It needs the value only for session 2.
- The script makes exactly one login and waits until the remote command has ended.
- The log file is written new at every call that reaches the login. A log file with the same name is replaced (line 17). A call that ends at line 9 or line 12 writes no log file.
- The exit status of the run is not the exit status of this script. It stands in the last line of the log file, after the words `ssh status`. The value 255 there means that `ssh` itself failed. The repo holds two logs of this form, one per session of step H2. Both end with `ssh status 0` [Ref1].
- The value 3 there has two possible sources: the marker check of the remote command (line 15), or the run script, which also ends with exit status 3 when the marker file exists. Both mean that the marker file was found.
- The script has no `set -e`. After a failed `ssh` it still writes the status line.
- The script differs from `visit8.sh` of the same folder in its comment lines (lines 2 to 4, line 7, line 10) and in three things of the code: three checked settings in place of four (line 11), no `BWX8_SHA256` in the remote command, and the name of the script that it starts (line 17).

## Source and explanation, line by line

- Text shown: the file `bwx8-2026-11-14/visit_h2.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (18 lines, 1463 bytes, sha256 `c7679b83553a417a126a6c64fe99bff3fe1651c330ebf3464b4cc723a30d843e`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# visit_h2.sh - one visit to CRB for the test of hypothesis H2: marker check, then run_h2.sh.` | Comment: the name and the purpose of the file. It makes one visit to CRB for the test of hypothesis H2. A visit is one login. The login first checks the marker file. Then it starts the run script `run_h2.sh`. By the header comment of that script, H2 says that the original gain of 0.94 % was measured while the new read kernel was at its low level. |
| 3 | `# Usage: STOP_AT=<UTC\|none> SESSION=<1\|2> [SESSION1_END=<UTC>] [ENVV="NAME=value ..."]` | Comment: the usage, first part: the environment variables. `STOP_AT` and `SESSION` are required. `SESSION1_END` and `ENVV` are optional. `ENVV` holds more settings for the run script, each in the form `NAME=value`. |
| 4 | `#        visit_h2.sh <log name> [--dry-run] [--from IDX]` | Continues the usage: the arguments. The first one is a name for the log file. The rest becomes the arguments of the run script (line 17): the options `--dry-run` and `--from IDX`. This script does not check them. The usage names no step, and the run script takes none. |
| 5 | `# Run only after the Slack check of handoff.md. The log goes to new-test-kernel/<log name>.log.` | Comment: the caller must first make the check that the handoff note asks for before every login. That check reads the Slack channel in which other users announce their blocks on CRB. A block is a time window that another user has reserved. The log of the visit goes to the file `<log name>.log` in the folder `new-test-kernel`. |
| 6 | `# STOP_AT and SESSION have no default here: decide them from the current reservations at every visit.` | Comment: the script gives `STOP_AT` and `SESSION` no default value. The caller must decide them at every visit, from the blocks that are announced at that time. |
| 7 | `# SESSION1_END is the end of session 1 of run_h2.sh (line "## end utc=" in env.txt of the h2-s1 folder).` | Comment: `SESSION1_END` must be the time at which session 1 of `run_h2.sh` ended. That time stands in the line that starts with `## end utc=` in the file `env.txt` of the result folder of session 1. The name of that folder starts with `h2-s1`. |
| 8 | `N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel` | `N`: the folder on the agent server that gets the log file. |
| 9 | `: "${STOP_AT:?set STOP_AT to a UTC time or to none}" "${SESSION:?set SESSION to 1 or 2}" "${1:?give a log name}"` | Checks that `STOP_AT`, `SESSION` and the first argument are set and not empty. The command `:` does nothing. `${X:?message}` gives the value of `X`. When `X` is empty or not set, the shell prints the message to the error output and ends the script with exit status 1. No login is made in that case. |
| 10 | `# These three values go into the remote command line. A blank or a shell character would split or change it.` | Comment: the three values that line 11 names become parts of the command line that runs on CRB. A blank, or a character that has a meaning for the shell, would split or change that command line. |
| 11 | `for v in STOP_AT SESSION SESSION1_END; do` | Starts a loop over the names of three variables: `STOP_AT`, `SESSION` and `SESSION1_END`. |
| 12 | `  [[ ${!v:-} =~ ^[A-Za-z0-9:.+-]*$ ]] \|\| { echo "$v holds a character outside A-Z a-z 0-9 : . + - (write a time as 2026-11-15T03:00Z): no login" >&2; exit 2; }` | `${!v:-}` gives the value of the variable whose name is in `v`, or an empty text when it is not set. The value must match the pattern `^[A-Za-z0-9:.+-]*$`: only letters, digits, colons, dots, plus signs and hyphens, or no character at all. If not, the script prints the name of the variable and the allowed characters to the error output (`>&2`) and ends with exit status 2. No login is made. |
| 13 | `done` | Ends the loop over the variable names. |
| 14 | `log=$N/$1.log; shift` | `log`: the path of the log file. It is the folder `N`, the first argument and the ending `.log`. `shift` drops the first argument. The arguments that are left are the options for the run script. |
| 15 | `M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'` | `M`: the text of the marker check that will run on CRB. When the marker file `/tmp/positron-perf.RUNNING` exists (`-e`), the remote command prints `RUNNING file present: stop` and ends with exit status 3. The single quotes keep the text as it is. No part of it runs on the agent server. |
| 16 | `ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \` | Starts the one `ssh` command of the visit, to CRB (user `jhan`, address `192.168.2.45`). `BatchMode=yes`: `ssh` never asks for a password, and it fails when the key does not work. `ConnectTimeout=15`: it gives up when no connection is made within 15 s. `ServerAliveInterval=30`: it sends a test message when the server has sent no data for 30 s. The backslash at the end joins the next line to this command. |
| 17 | `  "$M; cd ~/cache-perf/bwx8-20261114 && STOP_AT=$STOP_AT SESSION=$SESSION SESSION1_END=${SESSION1_END:-} ${ENVV:-} ./run_h2.sh $*" < /dev/null > "$log" 2>&1` | The remote command, in double quotes. So the shell on the agent server puts the values in before `ssh` starts. On CRB it runs the marker check `M`, then `cd` to the folder `~/cache-perf/bwx8-20261114`, then, only when the `cd` worked (`&&`), the script `./run_h2.sh` with the other arguments (`$*`). The settings before the script name go into its environment: `STOP_AT`, `SESSION`, `SESSION1_END` and the text of `ENVV`. `${X:-}` gives an empty text when `X` is not set or is empty. Line 12 checks neither `ENVV` nor the arguments. `< /dev/null` gives `ssh` an empty input, and `> "$log" 2>&1` writes its output and its error messages to a new log file. |
| 18 | `echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"` | Appends one line to the log: the words `ssh status`, the exit status of `ssh` (`$?`), and the UTC date and time. `ssh` ends with the exit status of the remote command, or with 255 when `ssh` itself failed. The exit status of this script is the status of this `echo`, not the status of the run. |

## References

- [Ref1] the log files `visit-h2-s1.log` and `visit-h2-s2.log` in `tests/2026-11-15-tackle-8mb/logs/` of the repo `arm-crb`. Their last lines are `ssh status 0 utc 2026-11-15T06:37:40Z` and `ssh status 0 utc 2026-11-15T11:27:22Z`.
