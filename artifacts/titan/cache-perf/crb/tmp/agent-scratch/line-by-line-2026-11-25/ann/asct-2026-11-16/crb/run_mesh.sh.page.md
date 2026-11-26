## Short version: purpose

`run_mesh.sh` is the script for the mesh-counter runs of the ASCT cross-check on CRB. For each line of a spec file it starts one ASCT benchmark process and reads the counters of the mesh as root with `perf stat -a` while the process runs, one counting window per event set. These runs did not happen, so no result of this script exists [Ref1].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **CMN**: Coherent Mesh Network, the name that Arm gives to the mesh. The mesh links the cores, the shared cache and the memory ports.
- **Mesh unit**: the counter unit that Linux shows for one mesh. The two units are `arm_cmn_0` and `arm_cmn_1`.
- **Mesh counter, mesh event**: a hardware counter of the mesh counts events such as requests, retries or stalls. It does not belong to a core. Linux reads it through the `perf` interface.
- **`perf stat`**: the Linux command that counts events while another command runs.
- **Event set**: a named list of mesh events that one counting window counts together. The sets file holds one set per line.
- **Counting window**: one run of `perf stat -a` for the command `sleep`. Its length is `WIN` seconds.
- **Spec file of `run_mesh.sh`**: the input of the script. Each line has the form `tag|layout|bytes|nops|duration` and gives one process, or one idle pass.
- **Layout**: the CPUs that get a thread. `6456` is 64 threads on mesh 0 plus 56 on mesh 1. `6400` is mesh 0 only. `c2` is the one CPU 2. `idle` is no process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Process**: one start of a benchmark binary.
- **Tag**: the name of one spec line. The output file of its process is `TAG.out`.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **STOP file**: the file `~/cache-perf/STOP` on CRB. The script stops before the next spec line when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists ({L9-10}).
2. Read the two arguments and the settings `WIN` and `DELAY` ({L11-14}).
3. Stop when `sudo` would need a password ({L15}).
4. Create the result folder, write the start state to `env.txt` and copy the sets file ({L16-18}).
5. Test every event of the sets file with a short `perf stat` run, and write the events that can be counted to `sets.ok` ({L19-26}).
6. For each spec line: check the two stop files, wait for a quiet machine, pause 5 s and write a `launch` line. Then start the benchmark process in the background, unless the layout is `idle`. The function `cpuflags` gives the `--bw-cpu` options. Then wait `DELAY` seconds ({L31-45}).
7. For each event set of `sets.ok`: run one counting window of `WIN` seconds and write its start time and its end time to `launches.txt` ({L46-55}).
8. Wait for the end of the process and write its exit status ({L56-59}).
9. After the last spec line: give the result files to the user and print a short summary ({L61-63}).

## Behavior a reader must know

- This script did not run in the cross-check. The permission system of the agent session refused the command with `sudo -n perf stat -a` [Ref1]. So this page describes the code only.
- Root is used by three kinds of commands: the test `sudo -n true` ({L15}), `perf stat -a` ({L23}, {L52}) and `chown` on the result folder ({L61}). The header comment names `perf stat -a` only. None of them changes a system setting.
- What is counted: `perf stat -a` counts on the whole system. A count holds the mesh events of everything that runs on the machine during the window, not only of the benchmark process.
- What a window covers: `perf` counts while `sleep $WIN` runs. The two `win` times in `launches.txt` are read by the shell before and after the `sudo` command. So they also hold the start time and the end time of `sudo` and `perf`.
- Nothing ties a window to the measured phase of the process. The first window starts `DELAY` seconds after the launch. By the decisions file, the analysis script `analyze.py` checks that every window lies inside the measured phase [Ref1].
- The event test of {L23} uses the unit `arm_cmn_0` only. An event that opens there is then counted on both units.
- Exit statuses: 3 for the marker file (at the start, before every spec line, before every window, and during the wait for the process), 4 for the STOP file (before every spec line), 5 when `sudo` needs a password, 2 for a one-core layout with CPU 120 to 127.
- When the marker file appears during a process, the script sends the termination signal to that process before it ends.
- A layout name that `cpuflags` does not know, such as `5656`, does not stop the script ({L28}). The binary would start without any `--bw-cpu` option.
- The exit status of the benchmark process is written to `launches.txt` but not tested.

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs, check in `analyze.py`) and "Record of 2026-11-16 23:50 UTC" (the mesh-counter runs did not happen).
- [Ref2] external source: Linux manual page perf-stat(1), options `-a`, `-x`, `-e`, `-o` and section "CSV FORMAT".
- [Ref3] external source: Linux kernel documentation, admin guide, page "Arm Coherent Mesh Network PMU": one counter unit per mesh, and the cycle counter of the DTC node of a mesh.
