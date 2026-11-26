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

1. Set the folder of the work and the path of the log file from the first argument ({L5-6}).
2. Prepare two texts for the remote command: the marker check and the change to the work folder ({L7-8}).
3. With `SEND=1`: send the folder `crb` as a `tar` stream. On CRB check the marker file, enter the work folder, unpack the stream and run the command ({L9-11}).
4. Without `SEND=1`: on CRB check the marker file, enter the work folder and run the command ({L12-14}).
5. Append the exit status of `ssh` and the UTC time to the log ({L15}).

## Behavior a reader must know

- The marker check is the first step on CRB. When the marker file exists, nothing is unpacked, the command does not run, and the log ends with `ssh status 3`.
- The script waits until the remote command has ended. All output of the remote command goes to the log file, not to the screen.
- A new call with the same log name replaces the older log.
- The command is joined into one text with spaces. Quotes around a single argument are lost on the way to CRB.
- The exit status of the script is not the status of the remote command. The status of `ssh` stands only in the last line of the log.
- The path in {L5} is fixed. The script works only when that folder exists on the agent server.
