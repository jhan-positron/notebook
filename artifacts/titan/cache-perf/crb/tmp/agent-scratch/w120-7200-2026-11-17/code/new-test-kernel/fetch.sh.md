# `fetch.sh` explained, line by line

- Source file: `new-test-kernel/fetch.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 6 lines, 454 bytes).
- sha256 of the source when this page was built: `35030b68eaaf35b9631a86cd37024d2937eb953a01494cbb5530e7b9a49dfa29`.

## Short version: purpose

`fetch.sh` copies result folders from CRB, the Arm server under test, to the agent server in one `ssh` login. The login first checks the marker file and then packs the named folders with `tar`, and a local `tar` unpacks them into the folder `crb/results/`. At the end the script prints the exit statuses of the two commands.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Archive**: one stream of data that the tool `tar` makes from files and folders. A second `tar` turns it into files and folders again.
- **Handoff note**: the file `handoff.md`. It tells how to carry out the test plan of 2026-11-13.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Set the folder on the agent server that gets the copies (line 3).
2. Keep the text of the marker check in `M` (line 4).
3. Log in to CRB once. The remote command checks the marker file and packs the named result folders into an archive. The archive comes back through `ssh`, and a local `tar` unpacks it (line 5).
4. Print the exit statuses of `ssh` and of the local `tar` (line 6).

## Behavior a reader must know

- On CRB the script only reads: the remote `tar` writes the archive to its output and changes no file there.
- On the agent server `tar` replaces a file that has the same path as a file of the archive.
- The script has no `set -e`. Its own exit status is the status of the last `echo`. A failed copy shows only in the printed line: any number other than 0 after `status` (line 6).
- The marker file is checked once, at the start of the login. The copy is not stopped when the marker file appears later.
- The copy runs inside an `ssh` login for a reason that the handoff note gives: a copy with `scp` is a login that cannot check the marker file first.
- The script makes no Slack check. The caller must do it before the call, as for every login.
- The folder names of the call are names below `~/cache-perf/results` on CRB. The same names appear below the folder `R`.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/fetch.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (6 lines, 454 bytes, sha256 `35030b68eaaf35b9631a86cd37024d2937eb953a01494cbb5530e7b9a49dfa29`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# fetch.sh <result folder name>...: one login to CRB (marker check first) that copies result folders to crb/results/.` | Comment: the usage and the purpose. The arguments are the names of one or more result folders. The script makes one login to CRB, which first checks the marker file. Then it copies the named folders into the folder `crb/results/` on the agent server. |
| 3 | `R=/home/jhan/workspace/titan/cache-perf/crb/results` | `R`: the folder on the agent server that gets the copies, as a fixed path. |
| 4 | `M='if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop" >&2; exit 3; fi'` | `M`: the text of the marker check. The single quotes keep the local shell from changing it. The shell on CRB runs it as the first command of the login. When the marker file exists (`-e`), the remote command prints `RUNNING file present: stop` and ends with exit status 3. Here the message goes to the error output (`>&2`). The standard output of this login carries the archive of line 5, so a message there would become a part of the archive data. |
| 5 | `ssh -o BatchMode=yes -o ConnectTimeout=15 jhan@192.168.2.45 "$M; tar cf - -C ~/cache-perf/results $*" \| tar xf - --no-same-owner -C $R/` | One `ssh` login to CRB (user `jhan`, address `192.168.2.45`) sends the folders as one stream of data, and a local `tar` unpacks it. `BatchMode=yes`: `ssh` never asks for a password, and it fails when the key does not work. `ConnectTimeout=15`: it gives up when no connection is made within 15 s. On CRB, after the marker check `M`: `tar cf -` packs the named folders (`$*`) into one archive and writes it to its standard output. `-C ~/cache-perf/results` makes `tar` take the names from that folder. `\|` gives the archive to the local `tar`. `tar xf -` reads it from its input and unpacks it into the folder `R` (`-C $R/`). `--no-same-owner`: the unpacked files belong to the local user, not to the owner that the archive records. `tar` replaces a local file that has the same path. |
| 6 | `echo "status ${PIPESTATUS[*]}"` | Prints the word `status` and the exit statuses of the two commands of line 5: first that of `ssh`, then that of the local `tar`. `PIPESTATUS` is the list that `bash` keeps for the last pipeline, and `[*]` joins its values with spaces. The line `status 0 0` means that both commands worked. After a marker stop the first number is 3. The second number is then not 0 either: the local `tar` gets an empty input and fails. The exit status of `fetch.sh` itself is the status of this `echo`. |
