# Handoff for review: boot-id check removed, hardware record added (2026-11-24)

## Short version

The check of a fixed boot id is removed from `go.sh` and `go2.sh`. The run scripts now record the clock rate of each core and the signs of throttling for each benchmark process, and the power values of the vendor tool for each result folder. Nothing ran on CRB: the checks use stand-in programs, and section 8 lists what the first use on CRB must confirm.

## State of the work

- Place: the working tree of `~/workspace/ai-proj` on the agent server, branch `main`.
- Nothing is committed and nothing is pushed.
- Changed files: `git diff` shows 6 files (58 lines added, 15 lines removed).
- New files: the folder `arm-crb/code/hwwatch-2026-11-24` (4 files) and the folder `arm-crb/status` (this note and 4 evidence files).
- All paths in this note are relative to `arm-crb/`, unless they start with `/` or `~`.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs. Our tests use CPUs 0 to 119 only.
- **Agent server**: the Linux server on which this work was done. It is not CRB.
- **Benchmark process**: one start of a benchmark binary (`bw_old`, `bw_new` or `bwx12`).
- **Read kernel**: the inner loop of a benchmark that reads memory. It is not the Linux kernel. "Old" is the C loop with sums. "New" and "load-only" are the loops that only load (`read`, `asmread` and their variants).
- **Whole-chip test**: the test that `go.sh` drives. 120 threads run on CPUs 0 to 119.
- **Step**: one call of `ra.sh` or `rx.sh` by a driver. Each step writes one result folder.
- **Result folder**: the folder that one run of `ra.sh`, `rx.sh` or `run_kernels.sh` writes on CRB under `~/cache-perf/results/`.
- **Driver**: `go.sh` or `go2.sh`. A driver starts the steps.
- **Run script**: `ra.sh`, `rx.sh` or `run_kernels.sh`. A run script starts benchmark processes.
- **Hardware record**: the new folder `hw` inside a result folder. It holds the files that section 4 lists.
- **Snapshot**: one read of a small set of files for a list of CPUs, written to one file.
- **Sampler**: the program that writes the clock rate of each core once per second (`hwwatch.py watch`).
- **The two counters**: `ref` and `del` in the Linux file `acpi_cppc/feedback_ctrs` of a CPU. Linux defines `ref` as a counter that runs at a fixed reference rate and `del` as a counter that runs at the delivered rate [Ref7]. On Arm64 Linux can read them from two counters of the core, the constant counter and the cycle counter, and these stop while the core is idle [Ref7] [Ref8]. Not checked: which counters the firmware of CRB names for them.
- **Clock rate**: the frequency at which a core runs, in kHz or GHz.
- **Throttling**: the chip or its firmware makes a core run slower than Linux requested.
- **Firmware**: the software of the chip that runs below Linux. It controls voltage, frequency and power limits.
- **atx**: Arm Telemetrix, the vendor tool that reads power, temperature and frequency values from the firmware [Ref10].
- **Rail**: one power supply line of the chip. The firmware reports voltage, current and power per rail.
- **Mesh (CMN)**: the network inside the chip that connects cores, cache and memory controllers.
- **Marker file**: `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test.
- **Boot id**: a random identifier that Linux creates once per boot.
- **Interrupt to a core (IPI)**: a signal from one CPU that makes another CPU stop its work for a short time.
- **Stand-in**: a small program that the tests use in place of a real one (for atx, for the benchmark binaries, for `taskset`).
- **sha256**: a checksum. Two files with the same sha256 have the same content.

## 1. The request

The user asked for three things on 2026-11-24:

1. Remove the check of the boot id.
2. Measure the clock rate of all 120 cores during the whole-chip test, and of the single core during single-core tests. Measure the power of the cores, of the mesh and of the chip. Record whether the chip lowers its speed to save power.
3. Write this note for a review by another agent.

The user's idea behind item 2: the new read kernel may run so fast that the chip uses too much power, and the chip may then shut down or lower its speed.

## 2. What earlier result files already show

This section is new analysis of files that are already in `tests/`. No new run was made.

Some earlier runs counted the cycles of the core clock per thread, and some counted the cycles of the mesh clock. The new script `clock_from_counts.py` turns these counts into clock rates [Ref2]. Its output is kept [Ref3].

**Core clock.** 29 csv files in three tests hold a cycle count.

| Test folder in `tests/` | Files | Values | Lowest | Highest |
|---|---:|---:|---:|---:|
| `2026-11-13-new-read-kernel` | 7 | 70,133 | 2.7881 GHz | 2.7990 GHz |
| `2026-11-15-tackle-8mb` (one worker thread per process) | 11 | 7,691 | 2.7972 GHz | 2.7991 GHz |
| `2026-11-15-whole-chip-read-drop` | 11 | 20,248 | 2.7911 GHz | 2.7978 GHz |

- One value is the count of one thread in one timed interval or trial, divided by the time for which the counter was enabled.
- The files of the second test have the trial layout of the runners: one pinned worker thread per process [Ref17].
- The counter counts user mode only, because each runner sets it so [Ref17]. So a value is a lower bound of the clock rate.
- The highest rate that Linux reports for a core of CRB is 2.8 GHz [Ref12].
- No row was left out: in every row the counter ran for the whole enabled time.
- In the third test, 10 of the 11 files have 120 threads per interval, and one file has 64. Each of the 11 files holds the old read kernel and at least one load-only kernel.
- Example from that test: in the file `w120-R0-20261115T165608Z/p1.csv` the old read kernel read 469.31 GB/s and the load-only kernel `asmread` read 302.59 GB/s with 120 threads [Ref4]. The lowest clock rate of any thread in any interval of that file is 2.7919 GHz [Ref3].

**Mesh clock.** Six result folders of 2026-11-15 (`w120-RC1` to `w120-RC6`) hold the mesh cycle counter `dtc_cycles` for both meshes. These runs used root.

- 1,296 lines hold a count for the whole measured time. They give 1.99959 GHz to 2.00001 GHz [Ref3].
- 48 lines hold a count that the tool `perf` scaled up from 66 % of the time. They are not used.
- The kernels in these folders are `oldread`, `asmread`, `read_nop96`, `read_nop256` and `read_1pl`.
- The vendor guide gives 2.0 GHz as the clock rate of the mesh [Ref11].

**What this says about the idea.**

- Not observed in these runs: a core clock below 2.788 GHz, or a mesh clock that differs from 2.000 GHz by more than 0.03 %.
- In the example file the read rate of `asmread` is 35.5 % below the rate of the old read kernel. The clock rates of all threads and intervals of that file lie between 2.7919 GHz and 2.7975 GHz [Ref3]. So a lower core clock does not explain that difference.
- Not measured in any run: power, temperature, and the throttle flag of the firmware.
- Not covered: the runs after the memory speed was changed from 8000 MT/s to 7200 MT/s on 2026-11-17 [Ref5]. The test `2026-11-17-whole-chip-7200` holds no cycle counter. Its three spec files count six other events [Ref6].
- Not tested by a clock rate: a limit that slows memory requests without a change of the clock.

## 3. Files

| File | Change |
|---|---|
| `code/w120-7200-2026-11-17/go.sh` | The fixed boot id and its check are removed (3 lines). New: the self-test of the hardware record before the first step, a count of incomplete records after each step, exit status 4. The checksum of `rx.sh` is the new one. |
| `code/w120-7200-2026-11-17/go2.sh` | The same changes as in `go.sh`. |
| `code/w120-7200-2026-11-17/ra.sh` | Calls `hw_init`, `hw_begin`, `hw_end` and `hw_done` around its 24 processes. |
| `code/w120-2026-11-15/rx.sh` | The same calls around each line of the spec file. The CPUs come from `--cpus` of the line. |
| `code/kernels-2026-11-13/run_kernels.sh` | The same calls in mode `all`: 192 one-thread processes and 24 processes of 120 threads. |
| `code/hwwatch-2026-11-24/hwwatch.py` (new, 671 lines) | Reads the files of Linux: `check`, `probe`, `snap`, `watch`. Prints the result: `report`. |
| `code/hwwatch-2026-11-24/hw.sh` (new, 191 lines) | The functions that the run scripts call. It starts and stops the sampler and atx. |
| `code/hwwatch-2026-11-24/clock_from_counts.py` (new, 131 lines) | The analysis of section 2. |
| `code/hwwatch-2026-11-24/test_hwwatch.py` (new, 748 lines) | 117 checks without CRB. |
| `README.md` | Four statements that the change made false are corrected, and the new folders are listed. |
| `status/2026-11-24-hw-record-evidence/` (new) | Output of the tests, of the defect trials and of `clock_from_counts.py`. |

Not changed: the three spec files, the benchmark sources, `code/manual-run/run.sh`, and `SOURCES.tsv`.

## 4. How the hardware record works

One result folder, schematic and not to scale:

```
run script [init]--wait--[B]-pause-[  process  ][A]---[done]
benchmark                          [###########]
sampler          [s  s  s  s  s  s  s  s  s  s  s  s  s]
atx              [a  a  a  a  a  a  a  a  a  a  a  a  a][report]

init   probe file, start of the sampler and of atx
B, A   snapshot before and after one process
s, a   one sample per second, both on CPU 119
done   stop of the sampler and of atx
```

- `rx.sh` takes snapshot B before its 5 s pause. So the launch still follows the pause directly [Ref1].
- `ra.sh` and `run_kernels.sh` have no pause between two processes. There the snapshots A and B lie between two processes.

**Sources.**

| What is recorded | Linux file or tool | Read when | Known cost |
|---|---|---|---|
| Clock rate of each core of the process, averaged over the process | `acpi_cppc/feedback_ctrs` (the two counters) | Snapshot before and after each process | Each read interrupts the core [Ref8] [Ref13]. No read happens while the process runs. |
| Clock rate of each core, sampled | `cpufreq/cpuinfo_avg_freq` of CPUs 0 to 119 | Once per second, for the whole result folder | No interrupt to the core [Ref8]. The sampler runs on CPU 119. |
| Throttle flag of the firmware | `cpufreq/perf_limited` | Snapshot | Not known. |
| Rate that Linux requested, and its range | `cpufreq/scaling_cur_freq`, `scaling_max_freq`, `scaling_min_freq` | Snapshot | Linux answers from its own data [Ref8]. |
| List of online CPUs, boot id, sensor files of `hwmon`, `thermal` and `powercap` | `/sys`, `/proc` | Snapshot | On 2026-10-30 CRB had two such sensors, both of the network card [Ref12]. |
| Every file of `cpufreq` and `acpi_cppc`, and the telemetry folders | `/sys`, `/dev/scmi` | Once per result folder (`probe.txt`) | Not known. |
| Power, current and voltage per rail, temperatures, core frequency as the firmware reports it | atx with the groups `power`, `thermal`, `frequency` | One collection per result folder, one sample per second, on CPU 119 | Not known. It needs a root step per boot (section 8). |

**How a clock rate is computed from the two counters.** The Linux document gives the rule: delivered performance = `reference_perf` x (change of `del`) / (change of `ref`) [Ref7]. `hwwatch.py report` turns this value into kHz with the same line through two points that the Linux function `cppc_perf_to_khz` uses [Ref8]. The report prints which rule it used.

**Flags of the report.** `hwwatch.py report RESULT_FOLDER` prints one row per process and these flags:

- `LOW_AVG`: a core ran below the limit on average, by its two counters. The limit is 99 % of `cpuinfo_max_freq` (`--tol` changes it).
- `LOW_SAMPLE`: a sampled rate of a core was below the limit.
- `LIMIT_LOWERED`, `REQUEST_BELOW_MAX`: Linux was told to request less, or requested less.
- `PERF_LIMITED`: the throttle flag went from 0 to not 0 during the process.
- `PERF_LIMITED_ALREADY_SET`: the flag was not 0 before the process. Then this run cannot show a new event. Only root can clear the flag [Ref9].
- `NO_THROTTLE_FLAG`: the flag could not be read.
- `ONLINE_CHANGED`, `BOOT_CHANGED`: a CPU went offline, or the machine rebooted.
- `NO_COUNTERS`, `NO_SAMPLES`, `NO_AFTER`, `CUT_FILE`: a part of the record is missing.

**Settings.** `HW=off` gives the behavior before this change: the scripts do not need `hw.sh`. `HW_POWER=off` leaves atx out. The other settings are listed at the top of `hw.sh`.

## 5. Decisions that I made

Each of these is a choice of mine. The reviewer should challenge them.

1. **`go2.sh` is changed too.** The user's earlier words named `go.sh` only. The same fixed boot id stops `go2.sh` in every other boot, and `go2.sh` needs the new checksum of `rx.sh` in any case.
2. **Power is required by default.** With the default `HW_POWER=require`, a driver stops before its first step when atx cannot collect. The message names the two ways to go on. Reason: a run of about 20 minutes without the requested data should be a choice. Effect: on CRB as it is today, `go.sh` does not start until atx is installed and set up, or `HW_POWER=off` is set.
3. **The spec files are unchanged.** A cycle counter in `--events` would give the clock rate per thread and interval, as in section 2. I did not add it. The spec lines already hold six events, and it is not known whether a seventh fits (section 8).
4. **A failure of the record does not stop a test after its start.** It adds a line `FAILED` to `hw/status.txt`. A driver then ends with status 4 and without the word `ALLDONE`.
5. **One collection of atx per result folder, not per process.** A start and stop of atx between two processes of `ra.sh` would change the timing of the test.
6. **The sampler and atx run on CPU 119.** In a 120-thread test they share this CPU with one benchmark thread. The record names the CPU.
7. **CPUs above 119 are refused.** The sharing rules of CRB forbid a read of the counter file of CPUs 126 and 127 [Ref13].
8. **The copied scripts are edited in place.** `SOURCES.tsv` keeps the checksums of the copy of 2026-11-24. `README.md` now says which files differ.
9. **`run.sh` is unchanged.** It is the user's saved start command. Its `sed` command now deletes no line of `go.sh`, so it starts an equal copy [Ref1]. It still needs a checksum list `local.sha` on CRB that fits the new files.
10. **Only three scripts start the record.** Not changed: the older run scripts in `code/bench`, `code/new-test-kernel`, `code/bwx*`, `code/cread-2026-11-12`, `code/asct-2026-11-16`, and the scripts `r0.sh`, `rc.sh`, `rc2.sh`, `rg.sh`, `rgc.sh` and `robsize/go.sh` in `code/w120-2026-11-15`.

## 6. Asked for and not delivered

- **Power of the mesh.** The telemetry table of the firmware has no power value for the mesh. It has a frequency entry `CMN` and two temperature entries `MXP` and `HNS`, which are parts of the mesh by their names. atx has no name for these three entries [Ref10]. This version does not collect them. Insufficient data: which rail feeds the mesh. Arm's power documentation of the chip would resolve it.
- **Power per core.** The firmware reports power per rail, not per core. The four main rails exist twice, with names that end in `C0` and `C1` [Ref10]. The rail `VCPU` is the core supply by its name. I found no list of the blocks that each rail feeds in the kit documents that I searched [Ref16].
- **Power per process or per kernel.** The report prints the values of atx for a whole result folder. In `ra.sh` this covers 24 processes. In a part C step it covers three kernels. atx also writes a file with every sample (`atx_interval.csv`), and the record keeps it. Insufficient data: the layout of that file. One collection on CRB would resolve it.
- **A shutdown of the chip.** The record can show only two signs: a changed list of online CPUs and a changed boot id.
- **The Linux kernel log.** The scripts do not read it. Two records disagree on whether a read needs root. The inspection of 2026-10-30 read it without root [Ref12]. The kernel configuration of the kit restricts it to root [Ref8]. One `dmesg` call on CRB would resolve it.

## 7. Checks that ran

All checks ran on the agent server. None proves anything about CRB.

- `python3 code/hwwatch-2026-11-24/test_hwwatch.py`: 117 checks, 117 passed, 141 s [Ref14]. 92 of them run without a script start (`--no-run`). 25 start the run scripts with stand-in programs.
- What the 117 checks cover:
  - `go.sh` and `go2.sh` hold no boot id check, and `go.sh` runs to `ALLDONE` in a boot that is not the one of 2026-11-17.
  - The checksum of `rx.sh` in both drivers is the checksum of the `rx.sh` of this repository.
  - `rx.sh` and `run_kernels.sh` run unchanged. Copies of `ra.sh`, `go.sh` and `go2.sh` run with the eight text changes that `COPY_CHANGES` in the test file lists: four checksums of stand-ins, and four reads of the load or of the memory size of the machine.
  - A one-thread process gets a snapshot of its one CPU. A 120-thread process gets a snapshot of 120 CPUs.
  - The rate rule: a counter ratio of 0.9 gives 2,520,000 kHz in the test tree, and only that core is flagged.
  - Each flag of section 4 fires for its case and does not fire for a process at full speed.
  - With `HW=off`, `rx.sh` runs without `hw.sh` and writes no record.
  - A driver that starts with the interrupt signal ignored can still stop atx. `run.sh` starts the driver in the background from a shell without job control, and such a shell makes the command ignore that signal [Ref18].
  - No sampler and no atx is left running after any case.
- Seven defect trials: one defect at a time was put into a copy of the code. Each trial made at least one check fail [Ref15].

| Trial | Checks that failed |
|---|---:|
| 1. atx is started without `env --default-signal` | 2 |
| 2. The CPU limit is 127 instead of 119 | 4 |
| 3. `go.sh` holds the fixed boot id again | 1 |
| 4. `rx.sh` takes the snapshot after the 5 s pause | 3 |
| 5. The counter ratio is `ref/del` instead of `del/ref` | 4 |
| 6. `PERF_LIMITED` ignores the value before the process | 1 |
| 7. An atx that is not running at the end of a process is not written to `status.txt` | 1 |

The trial output counts four more failed checks per trial. They compare files with the last commit and always fail in a copy [Ref15].

## 8. Not checked: needs CRB

Each item names the check and what it decides. None needs a benchmark run, except items 5 and 6.

1. **The three Linux files.** `cpuinfo_avg_freq` was read on CRB on 2026-10-30, and the sharing rules name `feedback_ctrs` [Ref12] [Ref13]. `perf_limited` is in the kernel source of the kit [Ref9]. Not known: whether the firmware of CRB fills `perf_limited`. Check: `python3 hwwatch.py check --cpus 0` (no root). Without the file, each process gets `NO_THROTTLE_FLAG`.
2. **The time of a snapshot and of the probe.** Some of these files read a register of the firmware. Check: the report prints both times. A long time lengthens the gap between two processes.
3. **The kHz rule and the two counters.** Check: one one-thread process on an idle machine, started through `rx.sh`. Expected: about 2,800,000 kHz by the counters and by the samples. If the two differ, the constants of the firmware table do not fit, and only the ratio can be used. The window of `rx.sh` holds the 5 s pause. So the same check shows whether the counters stop while the core is idle.
4. **atx.** Not known: whether it is on CRB, whether its root step works with the kernel of CRB, whether it writes its reports when it gets the signal SIGINT, how long it needs to start (the trial collection takes 5 s), how much CPU time it uses, and the layout of its two files. The summary layout in its guide and in its program text differ in one column name, and the parser accepts both [Ref10]. Check: `hw_check` after the root step. It fails with a message when any of these does not hold.
5. **The effect of the record on the benchmark.** The sampler and atx use CPU 119. Check: one step with `HW=off` and one with the record, and the rate of the thread on CPU 119 against the other threads.
6. **The time between two steps.** A step now ends with the stop of atx and starts with the probe and the start of atx. So a `bwx12` process starts later after the last 120-thread work than in the run of 2026-11-17. Check: the times in `status.txt` and in the driver log.
7. **A seventh counter event.** Hypothesis: a cycle counter does not fit beside the six events of the spec files. The kernel configuration of the kit enables the hard lockup detector that works through the counters of the core [Ref8]. Whether it takes a counter on CRB is not known. Check: one short `bwx12` process with `cycles=0x11` added. An event that does not open is printed as `NA`.

Two points about the shared machine, for the user:

- The root step of atx loads a kernel module and changes access rights [Ref10]. This is a change of the host state on a machine that another user measures on. It needs the user's approval and a note to the other user.
- The vendor says that the values of atx are not validated, and names two errors that need a reboot [Ref10].

## 9. How to use it

Places on CRB that the scripts expect:

| Folder of this repository | Folder on CRB |
|---|---|
| `code/hwwatch-2026-11-24` (`hw.sh`, `hwwatch.py`) | `~/cache-perf/hwwatch-20261124` (or the path in `HWDIR`) |
| `code/w120-7200-2026-11-17` | `~/cache-perf/w120-7200-20261117` |
| `code/w120-2026-11-15/rx.sh` | `~/cache-perf/w120-20261115/rx.sh` |
| `code/kernels-2026-11-13/run_kernels.sh` | the folder on CRB that holds the sources of the two binaries (the script builds and runs in its own folder) |
| the kit folder `tools/arm-telemetrix` | `~/cache-perf/arm-telemetrix` (or the path of `bin/atx` in `HW_ATX`) |

Order of a first use, all without a benchmark run:

1. Copy the files. Write a new `local.sha` on CRB for `run.sh`.
2. `python3 hwwatch.py check --cpus 0`, then `python3 hwwatch.py probe --cpus 0-119 --out probe.txt`. Both need no root.
3. With the user's approval: the root step of atx (`setup_arm_agi_cpu_telemetry.sh`), once per boot.
4. `bash -c '. ~/cache-perf/hwwatch-20261124/hw.sh; hw_check'`. It prints `hw: check ok` or the reason.
5. Start a test. After it: `python3 hwwatch.py report RESULT_FOLDER...`.

Without atx: start with `HW_POWER=off`. Without any record: `HW=off`.

## 10. Questions for the user

1. May the root step of atx run on CRB, and who tells the other user of CRB?
2. Is "power required by default" (decision 2) right, or should a missing atx only be reported?
3. Was the change of `go2.sh` wanted (decision 1)?
4. Is the mesh frequency an acceptable stand-in for the mesh power until the rail is known (section 6)?

## 11. Where a reviewer should look first

- `hw.sh`: every function must be safe under `set -euo pipefail`, because `ra.sh` and `run_kernels.sh` use it. Check the EXIT trap of `hw_init`.
- `rx.sh`: the place of `hw_begin` and `hw_end`, and the exit paths inside the loop.
- `hwwatch.py`, function `report_folder`: the time window of a process, the rule for kHz, and the conditions of each flag.
- `go.sh`: the order of the checks, and the new exit status 4.
- Section 2 of this note: each number against `clock_from_counts.out`, and each "not observed" against its scope.
- Sections 5 and 6: whether a decision or a gap contradicts the request.

## References

- [Ref1] `code/w120-2026-11-15/rx.sh`: `hw_begin` in line 19, the pause in line 20, the launch in line 22, `hw_end` in line 26. `code/w120-7200-2026-11-17/go.sh`: the checksum of `rx.sh` in line 16, the self-test in line 32, exit status 4 in line 55. `code/manual-run/run.sh`: the `sed` command in line 8. The check "run.sh still fits" of `test_hwwatch.py` compares the output of that `sed` command with `go.sh`.
- [Ref2] `code/hwwatch-2026-11-24/clock_from_counts.py`: the rules for a core value and a mesh value, and the two cases that are counted as "scaled", are in its header.
- [Ref3] `status/2026-11-24-hw-record-evidence/clock_from_counts.out`: output of `python3 code/hwwatch-2026-11-24/clock_from_counts.py tests/*/*`, run in `arm-crb` on 2026-11-25 UTC. Line 34: 29 csv files, 98,072 values, lowest 2.7881 GHz, highest 2.7991 GHz, 0 scaled rows. Line 79: 1,296 mesh values, lowest 1.99959 GHz, highest 2.00001 GHz, 48 scaled lines. Lines 82 to 85: the table per test. The line of `w120-R0-20261115T165608Z/p1.csv` holds 2.7919 GHz as its lowest value.
- [Ref4] `tests/2026-11-15-whole-chip-read-drop/w120-R0-20261115T165608Z/p1.csv`: line 128 (`I,0,0,oldread,...,120,...,469.31`) and line 490 (`I,0,1,asmread,...,120,...,302.59`). The last field is the read rate of all threads in GB/s (1 GB = 1e9 bytes), as line 1 of the file defines it.
- [Ref5] `README.md`, table "Tests": the row of `2026-11-17-firmware-and-dimm` names the change of the memory speed from 8000 MT/s to 7200 MT/s. The rows of the three tests of section 2 give start times from 2026-11-13 to 2026-11-15.
- [Ref6] `code/w120-7200-2026-11-17/like.spec`, `cfwd.spec`, `crev.spec`: each holds `--events cbusy0=0x198,cbusy1=0x199,cbusy2=0x19a,cbusy3=0x19b,cbusy_mt=0x19c,bus_access=0x19`. `code/w120-2026-11-15/r0.sh` line 10 holds the six events of the run of section 2, with `cycles=0x11` first.
- [Ref7] Linux documents in the kernel source of the kit, file `/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/linux/arm-agi-cpu-linux-7.1.3-v0.9.0-source.tar.gz`: `Documentation/admin-guide/acpi/cppc_sysfs.rst` (section "Computing Average Delivered Performance") and `Documentation/arch/arm64/amu.rst` (the cycle counter of the core, the constant counter, and "When in WFI or WFE these counters do not increment").
- [Ref8] The same kernel source. `drivers/cpufreq/cpufreq.c`: `show_cpuinfo_avg_freq`, `show_scaling_cur_freq`, and `show_one(scaling_min_freq, min)` with `show_one(scaling_max_freq, max)`. `arch/arm64/kernel/topology.c`: `arch_freq_get_on_cpu` reads values that the core stored at its last tick, `cpc_read_ffh` reads the cycle counter or the constant counter of a core, and `counters_read_on_cpu` calls `smp_call_function_single` for such a read. `drivers/acpi/cppc_acpi.c`: `show_feedback_ctrs` and `cppc_perf_to_khz`. The kernel configuration `arm-agi-cpu-linux-7.1.3-v0.9.0-ubuntu24.config` in the same folder: `CONFIG_SECURITY_DMESG_RESTRICT=y` and `CONFIG_HARDLOCKUP_DETECTOR_PERF=y`. Limit: this source is the kernel of firmware release 0.9.0. The kernel release of CRB ends with `v0.7.2-g4dbc8bb88858` in line 2 of `tests/2026-11-17-whole-chip-7200/go-T72-20261117T221209Z.log`. The file `arm-agi-cpu-patch-list.txt` in the same folder lists 17 commits between the two, and by their titles none changes the files named here. This is a reading of commit titles, not a comparison of the files.
- [Ref9] The same kernel source: `Documentation/ABI/testing/sysfs-devices-system-cpu`, entry `/sys/devices/system/cpu/cpuX/cpufreq/perf_limited` ("A non-zero value indicates throttling occurred", "The platform sets these bits; OSPM can only clear them"), and `drivers/cpufreq/cppc_cpufreq.c` (the attribute `perf_limited`).
- [Ref10] The tool folder `/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/tools/arm-telemetrix`. `ATX_ARM_AGI_PLATFORM_TELEMETRY_README.md`: the values are not validated (lines 27 to 30), the root step per boot (lines 90 to 109), the two errors (lines 130 to 139), the list of metrics (lines 147 to 172). `scripts/setup_arm_agi_cpu_telemetry.sh`: it loads the module `scmi_system_telemetry` and changes access rights. `doc/arm_telemetrix_cli_reference_guide_112049_0.1.0_03_en.pdf`: the options of `collect` (page 7), the summary layout (page 11), the metric groups of this chip (page 17). `lib/config/scmi/public/phoenix/scp.json`: the telemetry table of the firmware, with the entry `CMN` (`FREQUENCY_PRESENT`), the entries `MXP` and `HNS` (temperature), and the rail names. `bin/config/atx/metric_definitions/arm-agi-cpu/metric_definitions.json`: no name for the entry `CMN`. The program text of `bin/atx` holds the header `Target,Min,Max,Average,Time Weighted Average,Count` and the name `OnSigInt` (found with the tool `strings`). The output of that search was not saved.
- [Ref11] `/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf`, page 10: "Interconnect clocked at 2.0 GHz". The guide describes firmware release 0.9.0.
- [Ref12] `/home/jhan/workspace/titan/cache-perf/crb/inspection-record-2026-10-30.md`: line 22 (highest rate 2,800,000 kHz, `cpuinfo_avg_freq` 2,797,265 kHz), line 23 (driver `cppc_cpufreq`), line 141 (no thermal zone, the two `hwmon` devices belong to the network card), line 144 (`dmesg` readable for the user `jhan`).
- [Ref13] `/home/jhan/workspace/titan/cache-perf/crb/jeremy-plan-constraints-2026-10-30.md`, lines 60 and 123: no read of `feedback_ctrs` of CPU 126 or 127 during a run, two to four interrupts per read.
- [Ref14] `status/2026-11-24-hw-record-evidence/test_hwwatch.out`: the output of the test run of 2026-11-25 01:49 UTC. Lines 3 to 11 hold the sha256 of the nine files under test. The last two lines hold `# checks: 117, passed: 117, failed: 0` and the time.
- [Ref15] `status/2026-11-24-hw-record-evidence/defect_trials.sh` and `defect_trials.out`: the seven trials and their output. The header of the script names the four checks that always fail in a copy.
- [Ref16] The kit documents that were searched for the rail names `VCPU`, `VSOC` and `VSYS`: the SVK user guide (Ref11), `svk-release/VRM_FW/Arm_AGI_CPU_CRB_VR_config_code_Release_note_0.9c.pdf`, `tools/sysdiag/Arm_Sys_Diag_Tool_2.0.pdf`, `svk-release/docs/ARM-SVK-Installer.pdf`, the quick start guide in `docs/`, and the two documents of atx (Ref10). The text was extracted with the Python library PyMuPDF and searched with `grep`. The extracted text and the search output were not saved. Other files of the kit were not searched.
- [Ref17] The runner sources `code/bwx-2026-11-13/bwx.c`, `code/bwx8-2026-11-14/bwx8.c`, `code/bwx10-2026-11-15/bwx10.c`, `code/bwx11-2026-11-15/bwx11.c` and `code/bwx12-2026-11-15/bwx12.c`: each sets `exclude_kernel = 1` for its counters. The header comments of the last four say for `--trial`: "one pinned worker runs the trials of a plan file". The files `env.txt` of the result folders name the runner binary of each run.
- [Ref18] External source: GNU Bash Reference Manual, section "Signals": when job control is not in effect, asynchronous commands ignore SIGINT and SIGQUIT. `code/manual-run/run.sh` line 9 starts the driver with `nohup setsid ... &` inside the command string of `ssh`.
