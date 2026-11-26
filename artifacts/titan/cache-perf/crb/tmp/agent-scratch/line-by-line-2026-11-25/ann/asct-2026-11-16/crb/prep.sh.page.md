## Short version: purpose

`prep.sh` is the first script of the ASCT cross-check of 2026-11-16 on CRB. It records the machine state, builds the probe variant of the ASCT benchmark binary, finds the raw codes of the counter events and saves the machine code of the read loops. Then it runs short test processes that show whether both binaries and the counter files work.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **ASCT**: a measurement tool from Arm.
- **ASCT cross-check**: the test of 2026-11-16. It repeats our read tests with the benchmark binary of ASCT on the same CPUs and buffer sizes.
- **Decisions file**: the file `DECISIONS.md` in the folder `asct-2026-11-16`. It holds the plan and the rules of the cross-check, written before the data.
- **Installed binary**: the benchmark program `loaded-latency-asct-sve.bin` that the installer of ASCT built on CRB.
- **Probe binary, probe variant**: the same benchmark program, built with the flag `-DUSE_PROBE`. It holds the counter code of ASCT.
- **dietperf**: the counter code of ASCT. It reads a list of raw codes from the environment variable `DIETPERF_PMUv3`. It writes one counter file per thread.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Counter unit**: a group of hardware counters that Linux shows under one name. The counter unit of the cores is `armv8_pmuv3_0`.
- **Raw code**: the number that selects one counter event of a counter unit.
- **Event set**: a named list of counter events that one process counts together. The file `events.txt` holds the sets `A` to `G`.
- **Injected NOPs**: an option of the ASCT binary (`--bw-fine-delay N`). For N above 0 the binary runs an empty loop of N rounds after each load.
- **Measured phase**: the part of a run of the ASCT binary for which it reports its rate. The option `--duration` sets its length in seconds.
- **Machine-code listing**: the instructions that the compiler produced for a function, as text (output of the tool `objdump`).
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **NUMA node**: a group of CPUs and the memory that is local to them.
- **Transparent huge pages (thp)**: memory pages of 2 MiB that Linux can use for a buffer in place of its smaller standard pages.
- **Governor**: the Linux policy that sets the CPU frequency.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **KiB, GiB**: KiB = 1024 bytes. GiB = 1073741824 bytes (2 to the power of 30).
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Stop when the marker file exists ({L7-8}).
2. Set the work folder, the result folder and the path of the installed binary ({L9-12}).
3. Write the machine state to `env.txt` ({L13-30}).
4. Unpack the source archive of ASCT. Build the probe binary and a second plain binary, and write their checksums to `sha.txt` ({L31-46}).
5. Save the machine code of the read loops of the three binaries, and compare the installed binary with the second plain binary ({L47-54}).
6. Save the event list of `perf`, and let `resolve_events.py` write the raw codes to `events.codes` ({L55-58}).
7. Check the marker file again. Then run the smoke test: the installed binary, the probe binary once per event set, a run with two threads, and a run with a buffer of 64 MiB whose page size is read ({L59-75}).
8. Print the result files as a summary ({L76-79}).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures and prints its own rate. The script only stores that output.
- Three places can stop the script: the marker file in {L8} and {L62} (exit status 3) and a missing work folder in {L11} (exit status 2). No other failure stops it. A failed build shows only in `build.txt`, `sha.txt` and `smoke.txt`.
- {L34} deletes the folder `build` of the work folder at every run.
- The only command with `sudo` is the test `sudo -n true` in {L27}. It changes nothing.
- The marker file is checked before the smoke test but not during it. The smoke test starts 10 processes in the run of 2026-11-16 [Ref5].
- The comments in {L4} and {L59} do not fit the code. They speak of 3 processes and of the sets A and B. The loop of {L64-69} runs every set.
- The comment in {L47} speaks of two read loops. {L50} saves three functions.

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, section "Record of 2026-11-16 23:50 UTC": no root command ran on CRB in this work, except the test `sudo -n true` of `prep.sh`.
- [Ref2] `build.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the commands that `make` printed, with the two `rm -f` lines of `make clean`.
- [Ref3] `sha.txt` in the same result folder: the four checksums and the line `read loops: installed plain == rebuilt plain`.
- [Ref4] `env.txt` in the same result folder: the line `shell affinity 0-119`.
- [Ref5] `smoke.txt` in the same result folder: one `rc` line for the installed binary, 7 lines for the sets `A` to `G` and one line for the run with two threads. The tenth process is the run of {L74}, whose output file is `smoke.thp.out`.
- [Ref6] external source: Linux manual page perf-list(1), option `--details`.
