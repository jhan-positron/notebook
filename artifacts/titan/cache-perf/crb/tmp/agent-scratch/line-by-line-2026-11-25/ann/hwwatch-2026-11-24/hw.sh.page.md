## Short version: purpose

`hw.sh` holds the shell functions that make the hardware record of a test: the clock rate of the cores, the signs of throttling and the power. A run script reads the file, calls `hw_init` once, calls `hw_begin` and `hw_end` around each benchmark process, and calls `hw_done` at the end. The functions start the frequency sampler and the vendor tool `atx` in the background, take a snapshot before and after each process, and write all files into the folder `hw` of the result folder.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **Sourced**: a script reads another file with the shell command `.` and runs its lines in its own shell. The functions and variables of that file exist in the script afterwards.
- **Run script**: `ra.sh`, `rx.sh` or `run_kernels.sh`. A run script starts benchmark processes.
- **Driver**: `go.sh` or `go2.sh`. A driver starts run scripts, one after the other.
- **Step**: one call of a run script by a driver. Each step writes one result folder.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process**: one start of a benchmark binary.
- **Clock rate**: the frequency at which a core runs, in kHz or GHz.
- **Throttling**: the chip or its firmware makes a core run slower than Linux requested.
- **Firmware**: the software of the chip that runs below Linux. It controls voltage, frequency and power limits.
- **`hwwatch.py`**: the Python program beside `hw.sh`. It reads the files of Linux for the hardware record. Its commands are `check`, `probe`, `snap`, `watch` and `report`.
- **Frequency sampler, sampler**: the program `hwwatch.py watch`. It runs in the background and writes the clock rate of each core once per period to the file `watch.txt`. The period is 1 s by default.
- **Snapshot**: one read of a small set of files for a list of CPUs, written to one file (`hwwatch.py snap`).
- **Probe**: the file `probe.txt` of a hardware record (`hwwatch.py probe`). It is written once per result folder. It holds the files of the folders `cpufreq` and `acpi_cppc` of the CPUs, without four file names that `hwwatch.py` leaves out, the sensor files and facts about the system.
- **The two counters, counter file**: `ref` and `del` in the file `acpi_cppc/feedback_ctrs` of a CPU, which is the counter file. `ref` counts at a fixed reference rate. `del` counts at the rate that the core delivered.
- **Throttle flag**: the file `cpufreq/perf_limited` of a CPU. The firmware sets it to a value other than 0 when a limit made the core deliver less than Linux requested.
- **`atx`**: Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware.
- **Collection**: one run of the command `atx collect`. `hw.sh` ends it with a signal and then waits for the reports of `atx`.
- **Signal**: a message that Linux delivers to a process. SIGINT is the interrupt signal. SIGTERM asks a process to end. SIGKILL ends a process at once.
- **Trap**: a command that the shell runs when it receives a signal or when it ends.
- **Subshell**: a copy of the shell that runs as its own process.
- **Status of a function**: the number that a shell function returns. 0 means success.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it.
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **UTC**: Coordinated Universal Time.

## Main flow

1. A script sources the file. The lines outside the functions give each setting its default and clear the state variables ({L33-47}).
2. `hw_check` tests the tools: the files of Linux, a short run of the sampler on the CPU `HW_CPU`, and a trial collection of `atx` when `HW_POWER` is `require`. A driver calls it once before its first step ({L80-117}).
3. `hw_init` starts the record of one result folder. It calls `hw_check`, writes `status.txt` and `probe.txt`, sets the `EXIT` trap, and starts the sampler and `atx` in the background (`hw_atx_start` starts `atx`) ({L119-142}).
4. `hw_begin` gives the next process a numbered label and takes the snapshot before it (`hw_snap` runs `hwwatch.py snap`) ({L149-156}).
5. `hw_end` takes the snapshot after the process and tests that the sampler and `atx` still exist ({L158-168}).
6. `hw_done` stops the sampler and `atx` (`hw_atx_stop` sends the stop signal and waits at most 30 s), tests their last output and closes the record ({L170-187}).
7. `hw_failures` prints the number of `FAILED` lines of one record. A driver calls it after each step ({L189-191}).

## Behavior a reader must know

- No test on CRB has run with this file. It was written on 2026-11-24, after all tests [Ref1].
- Only a failed `hw_check` or `hw_init` stops a test. The run scripts then end with exit status 7 before their first benchmark process. A driver ends with exit status 1 before its first step when its own `hw_check` fails. It also ends with exit status 1 when a run script that it started ended with status 7.
- After `hw_init`, a failure of the record does not stop the test. `hw_note` adds a line that starts with `FAILED` to `status.txt`. A driver counts these lines after each step, and it ends with exit status 4 when a record is incomplete.
- With the default `HW_POWER=require`, `hw_check` fails when `atx` is missing or when its trial collection gives no summary with a power metric. `HW_POWER=off` leaves `atx` out.
- Thread placement: the sampler and `atx` are pinned to the CPU `HW_CPU`, which is CPU 119 by default. In a test with 120 threads one benchmark thread runs on that CPU too. This file does not pin the check program, the probe program and the snapshot program. They may run on every CPU that the calling shell may use. `ra.sh` and `run_kernels.sh` limit themselves to the CPUs 0 to 119 with `taskset` at their start. `rx.sh` sets no CPU list for itself.
- Timing: `hw_begin` and `hw_end` each run one snapshot and wait for it. So each process has one snapshot before its start and one after its end. In `rx.sh` the pause of 5 s lies between the first snapshot and the launch. No snapshot runs while the process runs. The sampler and `atx` run while the process runs.
- Reads that interrupt a core: by the header of `hwwatch.py`, a read of the counter file of a CPU interrupts that core. `hw_check` reads it for the CPUs `HW_CHECK_CPUS` (CPU 0 by default). The probe reads it once for each CPU of `HW_WATCH_CPUS`. Each snapshot reads it once for each CPU of its process. In the three run scripts each of these reads is done before a benchmark process starts or after it has ended. The sampler does not read this file. By the same header, its reads of `cpufreq/cpuinfo_avg_freq` send no interrupt to a core.
- `hw_check` does not fail when the throttle flag cannot be read, and it prints no note about it. When no CPU of a process has a readable throttle flag, the report of `hwwatch.py` gives that process the flag `NO_THROTTLE_FLAG`.
- The sampler ends without a signal after `HW_MAX_S` seconds, which is 3600 s by default. By the header comment of this file, `atx` gets the same limit. When the work of one result folder lasts longer, `hw_end` and `hw_done` add `FAILED` lines, and the later processes have no samples.
- The sampler and `atx` run for the whole result folder. There is one collection of `atx` per result folder, not one per process [Ref1].
- With `HW_POWER=require`, `hw_check` lasts at least `HW_ATX_TRIAL_S` seconds (5 s by default). A check that passed is not repeated for the same boot id and the same `HW_POWER`, as long as the variable `HW_CHECKED` reaches the next script.
- `hw_atx_stop` waits at most 30 s for the end of `atx`. Then it kills `atx`. So `hw_done` can last about 30 s.
- The `EXIT` trap of `hw_init` stops the sampler and `atx` when the calling script ends early. When a process is open at that moment, `status.txt` gets a `FAILED` line that names it.

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its short version says that nothing ran on CRB. Decision 5 of its section 5 gives the reason for one collection of `atx` per result folder: a start and a stop of `atx` between two processes would change the timing of the test.
