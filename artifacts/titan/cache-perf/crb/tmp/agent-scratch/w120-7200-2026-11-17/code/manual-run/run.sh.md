# `run.sh` explained, line by line

- Source file: `manual-run/run.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 9 lines, 1353 bytes).
- sha256 of the source when this page was built: `b6a65e4836e84276127120cf56220272b20d71acb34052f66549fc412a42a011`.

## Short version: purpose

`run.sh` is one command that starts the whole-chip test on CRB from the agent server. It first checks the marker file, the checksums of the run files, the memory speed (12 modules at 7200 MT/s) and the memory size. Then it starts a copy of `go.sh`, waits for its end and prints the log.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Whole-chip test**: a memory benchmark with 120 threads on the CPUs 0 to 119.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **MT/s**: million transfers per second, the unit of memory speed.
- **Memory module**: one DIMM, a plug-in memory board.
- **Module list**: the output of the command `dmidecode -t 17`. It prints the hardware table of the firmware, with one entry per memory module.
- **MemTotal**: the usable memory that Linux reports in the file `/proc/meminfo`, in kB.
- **Counter device**: the hardware counters of the CPU cores, as Linux lists them. On CRB the device has the name `armv8_pmuv3_0`. Linux gives it a type number. The argument lists of the benchmark name the device by this number (`--pmu-type 11`).
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **`local.sha`**: the checksum list of the run files. It lies in the folder of the run scripts on CRB.
- **`go.sh`**: the top-level script of the whole-chip test.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Process group**: a set of processes that one signal can reach together.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Open an `ssh` connection to CRB. The rest of the file is the remote command (line 1).
2. Stop when the marker file exists (line 2).
3. Set the paths and the time stamp (line 3).
4. Compare the run files with the checksum list `local.sha`. Stop on a difference (line 4).
5. Read the machine state and the module list, and write them to a file (line 5).
6. Stop unless 12 modules run at 7200 MT/s and MemTotal is at least 395000000 kB (lines 6 to 7).
7. Write `go-direct.sh`, a copy of `go.sh` without the line of the older boot id check (line 8).
8. Start `go-direct.sh`, wait for its end, and print its exit status and its log (line 9).

## Behavior a reader must know

- One step needs root on CRB: `sudo -n dmidecode -t 17` in line 5. It asks for no password. When `sudo` would need a password, the step prints an error, the memory check of line 7 fails, and nothing is started.
- Each stop before the start has its own exit status: 3 (marker file), 4 (checksums), 5 (memory), 6 (the copy could not be written).
- After the start, the command ends with the exit status of `go-direct.sh` (line 9). The `go.sh` of this repo ends with exit status 4 when all steps ran and a hardware record is incomplete. So an exit status 4 of the command has two meanings: the checksum stop of line 4, or a finished run with an incomplete hardware record. The printed text tells them apart: `NOT STARTED` for the checksum stop, `go.sh exit status 4` for the finished run.
- The command checks the marker file once, before the start. During the run the scripts `ra.sh` and `rx.sh` check it.
- The file `local.sha` on CRB decides which text of `go.sh` may run. A changed `go.sh` on CRB needs a checksum list that fits it.
- The command waits until the run has ended. The run does not need the connection: `nohup` and `setsid` in line 9 let it go on when the connection closes.

## Source and explanation, line by line

- Text shown: the file `manual-run/run.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (9 lines, 1353 bytes, sha256 `b6a65e4836e84276127120cf56220272b20d71acb34052f66549fc412a42a011`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `ssh -o BatchMode=yes -o ConnectTimeout=15 -o ServerAliveInterval=30 -i /home/jhan/.ssh/id_ed25519 jhan@192.168.2.45 '` | Starts one `ssh` command to CRB (user `jhan`, address `192.168.2.45`) with the key file `/home/jhan/.ssh/id_ed25519`. `BatchMode=yes`: `ssh` never asks for a password, and it fails when the key does not work. `ConnectTimeout=15`: it gives up when no connection is made within 15 s. `ServerAliveInterval=30`: it sends a test message when the server has sent no data for 30 s. The single quote at the end of the line starts the text of the remote command. That text ends in line 9. The shell on CRB runs lines 2 to 9. |
| 2 | `if [ -e /tmp/positron-perf.RUNNING ]; then echo "RUNNING file present: stop"; exit 3; fi` | On CRB: when the marker file exists (`-e`), the remote command prints `RUNNING file present: stop` and ends with exit status 3. Nothing is started. |
| 3 | `D=~/cache-perf/w120-7200-20261117; T=$(date -u +%Y%m%dT%H%M%SZ); R=~/cache-perf/results/memcheck-$T.txt; L=~/cache-perf/results/go-T72-$T.log` | Sets four variables. `D`: the folder of the run scripts on CRB. `T`: the UTC time of this moment. `R`: the file for the machine state that line 5 reads. `L`: the log file of the run. Both file names hold the time `T`. |
| 4 | `(cd $D && sha256sum -c local.sha) \|\| { echo "NOT STARTED: a script differs from local.sha"; exit 4; }` | Checksum check of the run files. The parentheses run the two commands in a subshell (a child copy of the shell), so the working folder of the remote command does not change. `sha256sum -c local.sha` computes the sha256 of every file that the list `local.sha` names and compares it with the value in the list. It prints one line per file. When a file differs or is missing, the remote command prints `NOT STARTED: a script differs from local.sha` and ends with exit status 4. |
| 5 | `{ date -u +%FT%TZ; cat /proc/sys/kernel/random/boot_id; uptime; echo "counter device type $(cat /sys/bus/event_source/devices/armv8_pmuv3_0/type)"; grep MemTotal /proc/meminfo; sudo -n dmidecode -t 17 \| grep "Configured Memory Speed" \| sort \| uniq -c; } 2>&1 \| tee $R` | Reads the machine state. `tee` writes it to the standard output and to the file `R`. The state holds the UTC time, the boot id, the output of `uptime` (time since boot, logins, load averages), the type number that Linux gives to the counter device `armv8_pmuv3_0`, the `MemTotal` line of `/proc/meminfo`, and the number of memory modules per configured speed. For the last value, `sudo -n dmidecode -t 17` prints the module list as root. `-n` means that `sudo` never asks for a password and fails when it would need one. `grep` keeps the lines with `Configured Memory Speed`, and `sort` with `uniq -c` counts equal lines. `2>&1` sends the error messages of the group to the same output. |
| 6 | `S=$(grep "Configured Memory Speed" $R \| tr -s " \t" " "); M=$(grep MemTotal $R \| tr -s " " \| cut -d" " -f2)` | Takes two values from the file `R`. `S`: the line with the module count and the speed. `tr -s` reduces each run of spaces and tabs in it to one space. `M`: the second field of the `MemTotal` line, a number in kB. |
| 7 | `[ "$S" = " 12 Configured Memory Speed: 7200 MT/s" ] && [ "${M:-0}" -ge 395000000 ] \|\| { echo "NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s"; exit 5; }` | Memory check. The run starts only when both tests pass. Test 1: `S` is exactly the text ` 12 Configured Memory Speed: 7200 MT/s`. So 12 modules report 7200 MT/s. A module with another speed would add a second line, and the text would differ. Test 2: `M` is at least 395000000 kB (about 376.7 GiB). `${M:-0}` gives 0 when `M` is empty. When a test fails, the remote command prints `NOT STARTED: memory is not confirmed at 12 modules, 7200 MT/s` and ends with exit status 5. |
| 8 | `sed "/boot id is not the boot checked/d" $D/go.sh > $D/go-direct.tmp && chmod +x $D/go-direct.tmp && mv $D/go-direct.tmp $D/go-direct.sh \|\| { echo "NOT STARTED: go-direct.sh could not be written"; exit 6; }` | Writes the script that will run: `go-direct.sh`, a copy of the `go.sh` on CRB. `sed` copies `go.sh` to a temporary file and leaves out every line that holds the text `boot id is not the boot checked`. That text belongs to the check of a fixed boot id in an older `go.sh`. The `go.sh` of this repo has no such line, so `sed` leaves out nothing of it. Then `chmod +x` makes the copy executable, and `mv` gives it the name `go-direct.sh`. When one of the three steps fails, the remote command prints `NOT STARTED: go-direct.sh could not be written` and ends with exit status 6. |
| 9 | `nohup setsid $D/go-direct.sh > $L 2>&1 < /dev/null & pid=$!; echo "log $L pid $pid"; wait $pid; rc=$?; echo "go.sh exit status $rc"; cat $L; exit $rc'` | Starts the run and waits for it. `nohup` makes `go-direct.sh` ignore the hangup signal. That signal tells a program that its connection was closed. `setsid` makes it the leader of a new process group. Its standard output and its error output go to the log file `L`. Its input is `/dev/null`, an empty input. `&` starts it in the background, and `pid` keeps its process id. The remote command prints the log path and the process id. `wait` returns when the run has ended and gives its exit status, which `rc` keeps. The remote command then prints that status and the whole log, and it ends with the same status. The single quote ends the text that began in line 1. `ssh` ends with the exit status of the remote command. |
