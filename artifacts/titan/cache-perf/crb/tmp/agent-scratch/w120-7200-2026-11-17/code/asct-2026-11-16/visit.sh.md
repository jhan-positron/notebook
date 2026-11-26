# `visit.sh` explained, line by line

- Source file: `asct-2026-11-16/visit.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 15 lines, 1001 bytes).
- sha256 of the source when this page was built: `29aa4b724158440b8c95e177aaefb4b5a423081c9d91851a9f4c87df20fb9e8f`.

## Short version: purpose

`visit.sh` runs on the agent server and makes one `ssh` login to CRB for the ASCT cross-check. On CRB it first checks the marker file and then runs the given command in the work folder. With `SEND=1` it first copies the scripts of the folder `crb` to CRB through the same login.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Work folder**: the folder `~/cache-perf/asct-20261116` on CRB. It holds the scripts and the input files of the cross-check.
- **Remote command**: the text that `ssh` gives to the shell on CRB.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Set the folder of the work and the path of the log file from the first argument (lines 5 to 6).
2. Prepare two texts for the remote command: the marker check and the change to the work folder (lines 7 to 8).
3. With `SEND=1`: send the folder `crb` as a `tar` stream. On CRB check the marker file, enter the work folder, unpack the stream and run the command (lines 9 to 11).
4. Without `SEND=1`: on CRB check the marker file, enter the work folder and run the command (lines 12 to 14).
5. Append the exit status of `ssh` and the UTC time to the log (line 15).

## Behavior a reader must know

- The marker check is the first step on CRB. When the marker file exists, nothing is unpacked, the command does not run, and the log ends with `ssh status 3`.
- The script waits until the remote command has ended. All output of the remote command goes to the log file, not to the screen.
- A new call with the same log name replaces the older log.
- The command is joined into one text with spaces. Quotes around a single argument are lost on the way to CRB.
- The exit status of the script is not the status of the remote command. The status of `ssh` stands only in the last line of the log.
- The path in line 5 is fixed. The script works only when that folder exists on the agent server.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/visit.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (15 lines, 1001 bytes, sha256 `29aa4b724158440b8c95e177aaefb4b5a423081c9d91851a9f4c87df20fb9e8f`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# visit.sh LOG COMMAND...  - one login to CRB: marker check first, then COMMAND in ~/cache-perf/asct-20261116.` | Comment: the usage. The first argument is the name of a log. The other arguments are a command. The script makes one login to CRB. There the marker file is checked first. Then the command runs in the folder `~/cache-perf/asct-20261116`. |
| 3 | `# With SEND=1 the folder crb/ of this directory is copied to CRB first (tar through the same ssh call).` | Comment: with `SEND=1` the script first copies the folder `crb/` of its own folder to CRB. The copy goes as a `tar` stream through the same `ssh` call. |
| 4 | `# Run only after reading Slack #phoenix-crb. The log goes to this folder as LOG.log.` | Comment: a rule for the one who starts the script. Read the Slack channel `#phoenix-crb` first. In that channel another user reserves time on CRB. The script does not check this rule. The comment also says that the log goes to the folder of the script as `LOG.log`. |
| 5 | `X=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/asct-2026-11-16` | `X`: a fixed path on the agent server, the folder of this work. The folder `crb` with the scripts for CRB lies in it, and the log files go to it. |
| 6 | `log=$X/$1.log; shift` | `log`: the path of the log file. It is the first argument with the ending `.log`, in the folder `X`. `shift` then removes the first argument. The arguments that are left are the command. |
| 7 | `M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi'` | `M`: the text of the marker check. The shell on CRB will run it. When the marker file exists there (`-e`), that shell prints `RUNNING file present: stop` and ends with exit status 3. The single quotes keep the text unchanged on the agent server. |
| 8 | `W='mkdir -p ~/cache-perf/asct-20261116 ~/cache-perf/results && cd ~/cache-perf/asct-20261116'` | `W`: the text of the second remote step. `mkdir -p` creates the work folder `asct-20261116` and the folder `results` below `~/cache-perf` when they are missing. `cd` then changes to the work folder. The shell on CRB expands the `~`, so it means the home folder on CRB. |
| 9 | `if [ "${SEND:-0}" = 1 ]; then` | Tests the variable `SEND`. `${SEND:-0}` gives 0 when the variable is not set or is empty. The lines lines 10 to 11 run when the value is 1. |
| 10 | `  tar cf - -C $X/crb . \| ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 \` | With `SEND=1`. `tar cf - -C $X/crb .` packs all files of the folder `crb` into one archive and writes it to its standard output (`-f -`). `-C` makes `tar` change to that folder first, so the names in the archive have no folder in front. The pipe gives the archive to `ssh` as its input. `ssh` logs in to CRB as the user `jhan` at the address `192.168.2.45`. `BatchMode=yes`: `ssh` never asks for a password and fails when the key does not work. `ConnectTimeout=15`: it gives up when no connection is made within 15 s. `ServerAliveInterval=30`: it sends a test message when the server has sent no data for 30 s. The backslash continues the command in the next line. |
| 11 | `    "$M; $W && tar xf - --no-same-owner && $*" > "$log" 2>&1` | Continues the command of line 10: the remote command, in double quotes. The local shell puts the values of `M` and `W` and the command (`$*`, all arguments that are left, joined with spaces) into the text. On CRB the marker check runs first. Then three steps follow, each only when the one before it succeeded: create and enter the work folder, unpack the archive from the input (`tar xf -`), and run the command. `--no-same-owner`: the unpacked files belong to the remote user. The output and the error messages of the whole call go to the log file (`> "$log" 2>&1`). An older log of the same name is replaced. |
| 12 | `else` | The other branch: `SEND` is not 1. |
| 13 | `  ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 jhan@192.168.2.45 "$M; $W && $*" < /dev/null > "$log" 2>&1` | The same `ssh` call without the copy. On CRB the marker check runs, then the work folder is created and entered, then the command runs. The input of `ssh` is `/dev/null`, an empty input. The output and the error messages go to the log file. |
| 14 | `fi` | Ends the `if` of line 9. |
| 15 | `echo "ssh status $? utc $(date -u +%FT%TZ)" >> "$log"` | Appends one line to the log: `ssh status`, the exit status of the `ssh` call and the UTC date and time. `ssh` returns the exit status of the remote command, so 3 when the marker file exists. The script itself ends with the status of this `echo`. |
