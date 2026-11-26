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

1. Open an `ssh` connection to CRB. The rest of the file is the remote command ({L1}).
2. Stop when the marker file exists ({L2}).
3. Set the paths and the time stamp ({L3}).
4. Compare the run files with the checksum list `local.sha`. Stop on a difference ({L4}).
5. Read the machine state and the module list, and write them to a file ({L5}).
6. Stop unless 12 modules run at 7200 MT/s and MemTotal is at least 395000000 kB ({L6-7}).
7. Write `go-direct.sh`, a copy of `go.sh` without the line of the older boot id check ({L8}).
8. Start `go-direct.sh`, wait for its end, and print its exit status and its log ({L9}).

## Behavior a reader must know

- One step needs root on CRB: `sudo -n dmidecode -t 17` in {L5}. It asks for no password. When `sudo` would need a password, the step prints an error, the memory check of {L7} fails, and nothing is started.
- Each stop before the start has its own exit status: 3 (marker file), 4 (checksums), 5 (memory), 6 (the copy could not be written).
- After the start, the command ends with the exit status of `go-direct.sh` ({L9}). The `go.sh` of this repo ends with exit status 4 when all steps ran and a hardware record is incomplete. So an exit status 4 of the command has two meanings: the checksum stop of {L4}, or a finished run with an incomplete hardware record. The printed text tells them apart: `NOT STARTED` for the checksum stop, `go.sh exit status 4` for the finished run.
- The command checks the marker file once, before the start. During the run the scripts `ra.sh` and `rx.sh` check it.
- The file `local.sha` on CRB decides which text of `go.sh` may run. A changed `go.sh` on CRB needs a checksum list that fits it.
- The command waits until the run has ended. The run does not need the connection: `nohup` and `setsid` in {L9} let it go on when the connection closes.
