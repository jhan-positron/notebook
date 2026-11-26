# `spec_single.txt` explained, line by line

- Source file: `asct-2026-11-16/crb/spec_single.txt` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (text file, 10 lines, 227 bytes).
- sha256 of the source when this page was built: `3378aa5c3433ed317ee71fb471e706a2b33fbd1da4f3dcab549edff2dea83ff6`.

## Short version: purpose

`spec_single.txt` is the list of the one-core cases for the mesh-counter runs of the ASCT cross-check. The script `run_mesh.sh` reads it as its input and handles one line at a time: an idle pass first, then one ASCT benchmark process per line, during which it reads the counters of the mesh. These runs did not happen [Ref1].

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Tag**: the name of one case. `run_mesh.sh` uses it in the names of the output files.
- **Layout**: the CPUs that get a thread. The letter `c` with a number is the one CPU of that number. `idle` is no process.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Counting window**: one run of the command `perf stat -a` for a fixed number of seconds. `run_mesh.sh` opens one window per event set.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).

## Main flow

1. Read each line as one case. A `|` stands between the five fields (lines 1 to 10).
2. Field 1 is the tag. `run_mesh.sh` writes the output of the process to `TAG.out` and the counts of each window to `TAG.SET.perf`.
3. Field 2 is the layout. For `idle` no process starts (line 1). For a one-core layout the function `cpuflags` of `run_mesh.sh` gives one `--bw-cpu` option (lines 2 to 10).
4. Field 3 is the buffer size in bytes. It becomes the option `--bw-buflen`.
5. Field 4 is the number of injected NOPs. It becomes the option `--bw-fine-delay`.
6. Field 5 is the length of the measured phase in seconds. It becomes the option `--duration`.

## Behavior a reader must know

- `run_mesh.sh` skips a line with an empty first field. It copies the four other fields into the `launch` line of `launches.txt`.
- `run_mesh.sh` ends with exit status 2 when a one-core layout names a CPU from 120 to 127. The CPUs of this file are 2 and 41.
- By the decisions file these cases belong to the event set file `sets_single.txt`: 7 sets, with a window of 3 s per set [Ref1]. The default window of `run_mesh.sh` is 4 s. The plan needs the setting `WIN=3`.
- The cases run in the order of the lines, one process at a time.
- The mesh-counter runs did not happen. So no result exists for these cases [Ref1].

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/spec_single.txt` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (10 lines, 227 bytes, sha256 `3378aa5c3433ed317ee71fb471e706a2b33fbd1da4f3dcab549edff2dea83ff6`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `idle\|idle\|0\|0\|0` | Case `idle`. The five fields have a `\|` between them. Field 1 is the tag. `run_mesh.sh` puts it into the names of the output files of the case. Field 2 is the layout. With the layout `idle` the script `run_mesh.sh` starts no process and counts while the machine does nothing. The three other fields are 0. They are written to the `launch` line but not used. |
| 2 | `c2s1m\|c2\|1048576\|0\|32` | Case `c2s1m`. The layout `c2` means one read thread on CPU 2. Field 3 is the buffer size, 1048576 bytes (1 MiB). Field 4 is the number of injected NOPs, here 0. Field 5 is the length of the measured phase, 32 s. |
| 3 | `c2s6m\|c2\|6291456\|0\|32` | Case `c2s6m`: CPU 2 with a buffer of 6291456 bytes (6 MiB), 0 injected NOPs, 32 s. |
| 4 | `c2s8m\|c2\|8388608\|0\|32` | Case `c2s8m`: CPU 2 with a buffer of 8388608 bytes (8 MiB), 0 injected NOPs, 32 s. |
| 5 | `c2s12m\|c2\|12582912\|0\|32` | Case `c2s12m`: CPU 2 with a buffer of 12582912 bytes (12 MiB), 0 injected NOPs, 32 s. |
| 6 | `c2s32m\|c2\|33554432\|0\|32` | Case `c2s32m`: CPU 2 with a buffer of 33554432 bytes (32 MiB), 0 injected NOPs, 32 s. |
| 7 | `c2s1g\|c2\|1073741824\|0\|32` | Case `c2s1g`: CPU 2 with a buffer of 1073741824 bytes (1 GiB), 0 injected NOPs, 32 s. |
| 8 | `c41s1m\|c41\|1048576\|0\|32` | Case `c41s1m`: the layout `c41`, one read thread on CPU 41, with a buffer of 1 MiB, 0 injected NOPs, 32 s. |
| 9 | `c41s8m\|c41\|8388608\|0\|32` | Case `c41s8m`: CPU 41 with a buffer of 8 MiB, 0 injected NOPs, 32 s. |
| 10 | `c2s8mn2\|c2\|8388608\|2\|32` | Case `c2s8mn2`: CPU 2 with a buffer of 8 MiB and 2 injected NOPs, 32 s. The decisions file added this case later. By that file, the loop with injected NOPs read 8 MiB faster than the loop without them in the first one-core run [Ref1]. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, sections "Added 2026-11-16 23:23 UTC" (plan of the mesh-counter runs and the first one-core data), "Added 2026-11-16 23:37 UTC" (the case with 2 injected NOPs) and "Record of 2026-11-16 23:50 UTC" (the runs did not happen).
