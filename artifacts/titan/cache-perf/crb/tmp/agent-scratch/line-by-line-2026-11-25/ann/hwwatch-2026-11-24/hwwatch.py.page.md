## Short version: purpose

`hwwatch.py` is the program that reads the files of Linux for the hardware record of a test. Four commands run beside a test: `check` tests the files, `probe` copies the frequency files once per result folder, `snap` reads six files per CPU before and after a process, and `watch` samples the clock rate of each core once per period. The fifth command, `report`, reads the recorded files after the test and prints the clock rate of the cores per process, with flags for a core that ran slow or was throttled.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Hardware record**: the record of the clock rate of the cores, of the signs of throttling and of the power that the file `hw.sh` makes beside a test since 2026-11-24.
- **`hw.sh`**: the shell file beside this program. The run scripts of the tests call its functions, and these functions start this program.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC.
- **Process**: one start of a benchmark binary.
- **Clock rate**: the frequency at which a core runs, in kHz or GHz. 2800000 kHz is 2.8 GHz.
- **Throttling**: the chip or its firmware makes a core run slower than Linux requested.
- **Firmware**: the software of the chip that runs below Linux. It controls voltage, frequency and power limits.
- **Snapshot**: one read of a small set of files for a list of CPUs, written to one file (command `snap`).
- **Probe**: the file `probe.txt` of a hardware record (command `probe`). It is written once per result folder.
- **Frequency sampler, sampler**: the command `watch`. It runs in the background and writes the clock rate of each core once per period.
- **Window of a process**: the time from the end of the snapshot before a process to the start of the snapshot after it.
- **`/sys` and `/proc`**: two file trees of Linux. Their files are not on a disk. The Linux kernel computes the content when a program reads a file.
- **`cpufreq`**: the part of the Linux kernel that sets the frequency of the CPUs. Each CPU has a folder `cpufreq` with its files.
- **`acpi_cppc`**: the folder of a CPU with the values of CPPC. CPPC (Collaborative Processor Performance Control) is the interface through which Linux requests a performance level from the firmware and reads the two counters.
- **The two counters**: `ref` and `del` in the file `acpi_cppc/feedback_ctrs` of a CPU. `ref` counts at a fixed reference rate. `del` counts at the rate that the core delivered.
- **Performance value**: a number on the scale of the firmware table of CPPC. The scale has no unit. The firmware table also gives the frequency for two of these numbers.
- **Counter ratio**: the change of `del` divided by the change of `ref` between two snapshots of one CPU.
- **Limit**: the clock rate below which the report flags a value. It is 99 % of the highest frequency of the CPU (`cpuinfo_max_freq`) unless `--tol` says otherwise.
- **Flag**: a word in capital letters that the report prints for a process, for example `LOW_AVG`.
- **`atx`**: Arm Telemetrix, a tool of the chip vendor. It reads power, temperature and frequency values of the firmware.
- **Metric, target**: words of the summary file of `atx`. A metric is one measured quantity, for example the power of one supply. A target is the source that a row of values comes from.
- **Docstring**: a text literal at the top of a Python file or function that describes it.
- **Signal**: a message that Linux delivers to a process. SIGINT is the interrupt signal. SIGTERM asks a process to end.
- **Boot id**: a random identifier that Linux creates once per boot. Equal boot ids mean the same boot.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Governor**: the Linux policy that sets the CPU frequency.
- **Pinned**: a thread that is pinned to a CPU may run on that CPU only.
- **CPU list**: the CPUs on which Linux may run a process. The tool `taskset` sets or prints it. In this file the words also stand for the value of `--cpus`, the CPUs that a command reads.
- **sha256**: a checksum. Two files with the same sha256 have the same content.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. `main` reads the command and its options from the command line and calls the function of the command ({L645-667}).
2. Command `check`: for each CPU of the list, test that the counter file, the average rate and the requested rate are readable. Print the failures and return 1 when there is one ({L221-246}).
3. Command `probe`: write the files of the folders `cpufreq`, `cpufreq/stats` and `acpi_cppc` of each CPU without four file names that are left out, the system and sensor files, and the entry names of five folders ({L186-218}).
4. Command `snap`: for each CPU read five files of `cpufreq`, then the time, then the two counters. Then read the system and sensor files and write one file ({L176-183}).
5. Command `watch`: open the file of the average rate of each CPU once, then write one line of values per period, until the watched process is gone, the time limit is reached or a signal arrives ({L249-309}).
6. Command `report`: for each result folder read the probe, the samples and each pair of snapshots (`report_folder`), compute the clock rates and the flags per process, read the summary of `atx`, and print the result as text or as JSON ({L425-552}, {L559-618}, {L633-642}).

## Behavior a reader must know

- No test on CRB has run with this file. It was written on 2026-11-24, after all tests [Ref7].
- A CPU list with a CPU above 119 ends the program with exit status 2 before any file of a CPU is read ({L119-122}).
- Reads that interrupt a core: by the docstring, a read of the counter file `feedback_ctrs` interrupts the core. `snap` reads it once per CPU, and `probe` and `check` read it too. `watch` never reads it.
- What is timed: the window of a process starts at the value `mono_ns` in the footer of the first snapshot and ends at the value `mono_ns` in the header of the second snapshot ({L469-470}). The clock is `CLOCK_MONOTONIC`.
- How a clock rate is computed from the two counters ({L477-488}):
  - Counter ratio of one CPU = (change of `del`) divided by (change of `ref`) between its two snapshot lines. No time enters this ratio.
  - Performance value = `reference_perf` times the ratio. `perf_to_khz` turns it into kHz ({L365-382}).
  - The two counter reads of a CPU lie inside the two snapshots. So the ratio covers the window and a part of each snapshot.
  - A CPU gets no ratio when a counter is unreadable, when `ref` did not advance, or when `del` went backwards. The process gets the flag `NO_COUNTERS` when no CPU has a ratio.
  - By the design note, Linux on Arm64 can read `ref` and `del` from two counters of the core that stop while the core is idle. Which counters the firmware of CRB names for them was not checked [Ref7].
- Four flags compare a value with the `cpuinfo_max_freq` of the probe: `LOW_AVG`, `LOW_SAMPLE`, `LIMIT_LOWERED` and `REQUEST_BELOW_MAX`. A CPU without that value cannot set any of the four, and a record without `probe.txt` gets none of them ({L475-476}, {L497}, {L511}, {L524}).
- Sampled rates of a process: the values of the sampler whose time stamp lies inside the window, both ends included, for the CPUs of the process ({L501-515}).
- The energy of a process is the change of an energy counter between the two snapshots. The average power divides it by the time from the end of the first snapshot to the end of the second ({L471-472}, {L588-593}).
- The report sets no flag from a value of `atx`. It prints these values for the whole result folder, not per process [Ref7].
- Exit statuses: 0 on success. `check` returns 1 when a source is not usable. A bad option value or a bad CPU list gives 2.
- `watch` ends with exit status 0 and a footer line in three cases: the watched process is gone, the time limit is reached, or the signal SIGTERM or SIGINT arrived inside the loop. A sampler that is killed leaves a file without a footer.

## References

- [Ref1] external source: Linux kernel documentation, document "CPU Performance Scaling" (source file `Documentation/admin-guide/pm/cpufreq.rst`), read on 2026-11-25 at https://docs.kernel.org/admin-guide/pm/cpufreq.html . It defines the files `cpuinfo_avg_freq`, `cpuinfo_cur_freq`, `cpuinfo_max_freq`, `scaling_cur_freq`, `scaling_max_freq`, `scaling_min_freq` and `scaling_setspeed` with the unit kHz, and the file `boost`.
- [Ref2] external source: Linux kernel documentation, document "Collaborative Processor Performance Control (CPPC)" (source file `Documentation/admin-guide/acpi/cppc_sysfs.rst`), read on 2026-11-25 at https://docs.kernel.org/admin-guide/acpi/cppc_sysfs.html . It defines the files of the folder `acpi_cppc`, and its section "Computing Average Delivered Performance" gives the rule for the two counters.
- [Ref3] external source: Linux kernel file `Documentation/ABI/testing/sysfs-devices-system-cpu`, read on 2026-11-25 at https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-devices-system-cpu . Entries `perf_limited`, `online`, `offline`, `possible` and `isolated`.
- [Ref4] external source: Linux kernel files `sysfs-class-hwmon`, `sysfs-class-thermal` and `sysfs-class-powercap` in the folder `Documentation/ABI/testing`, read on 2026-11-25 at https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-hwmon , https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-thermal and https://www.kernel.org/doc/Documentation/ABI/testing/sysfs-class-powercap . They give the meaning and the unit of the sensor files.
- [Ref5] external source: Linux manual pages `proc_uptime(5)` and `proc_cmdline(5)`, read on 2026-11-25 at https://man7.org/linux/man-pages/man5/proc_uptime.5.html and https://man7.org/linux/man-pages/man5/proc_cmdline.5.html .
- [Ref6] external source: Linux kernel documentation, source file `Documentation/cpu-freq/cpufreq-stats.rst`, read on 2026-11-25 at https://docs.kernel.org/cpu-freq/cpufreq-stats.html . It describes the files `trans_table` and `reset` of the folder `cpufreq/stats`.
- [Ref7] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its short version says that nothing ran on CRB. Its list of words describes the two counters. Its section 4 lists the sources and the flags of the report. Its section 6 says that the report sets no flag from a power or a temperature value, and that it prints the values of `atx` for a whole result folder.
