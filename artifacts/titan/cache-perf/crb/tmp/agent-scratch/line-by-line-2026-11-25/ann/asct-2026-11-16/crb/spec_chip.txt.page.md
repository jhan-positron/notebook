## Short version: purpose

`spec_chip.txt` is the list of the whole-chip cases for the mesh-counter runs of the ASCT cross-check. The script `run_mesh.sh` reads it as its input and starts one ASCT benchmark process per line, during which it reads the counters of the mesh. These runs did not happen [Ref1].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Tag**: the name of one case. `run_mesh.sh` uses it in the names of the output files.
- **Layout**: the CPUs that get a thread. `6456` is 64 threads on mesh 0 plus 56 on mesh 1. `6400` is mesh 0 only.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Counting window**: one run of the command `perf stat -a` for a fixed number of seconds. `run_mesh.sh` opens one window per event set.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).

## Main flow

1. Read each line as one case. A `|` stands between the five fields ({L1-4}).
2. Field 1 is the tag. `run_mesh.sh` writes the output of the process to `TAG.out` and the counts of each window to `TAG.SET.perf`.
3. Field 2 is the layout. The function `cpuflags` of `run_mesh.sh` turns it into one `--bw-cpu` option per CPU.
4. Field 3 is the buffer size of each thread in bytes. It becomes the option `--bw-buflen`.
5. Field 4 is the number of injected NOPs. It becomes the option `--bw-fine-delay`.
6. Field 5 is the length of the measured phase in seconds. It becomes the option `--duration`.

## Behavior a reader must know

- `run_mesh.sh` skips a line with an empty first field. It copies the four other fields into the `launch` line of `launches.txt`.
- By the decisions file these cases belong to the event set file `sets_chip.txt`: 22 sets, with a window of 3 s per set [Ref1]. The default window of `run_mesh.sh` is 4 s. The plan needs the setting `WIN=3`.
- The cases run in the order of the lines, one process at a time.
- The mesh-counter runs did not happen. So no result exists for these cases [Ref1].

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs), "Added 2026-11-16 23:37 UTC" (the case with 4 injected NOPs) and "Record of 2026-11-16 23:50 UTC" (the runs did not happen).
