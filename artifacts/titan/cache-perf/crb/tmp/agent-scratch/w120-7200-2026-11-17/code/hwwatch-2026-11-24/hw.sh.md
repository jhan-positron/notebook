# `hw.sh` explained, line by line

- Source file: `hwwatch-2026-11-24/hw.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 191 lines, 10046 bytes).
- sha256 of the source when this page was built: `7455abf4b05635a5d2fc6503145fcf73a44f9adf387b38af8b52bace40c769c4`.

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

1. A script sources the file. The lines outside the functions give each setting its default and clear the state variables (lines 33 to 47).
2. `hw_check` tests the tools: the files of Linux, a short run of the sampler on the CPU `HW_CPU`, and a trial collection of `atx` when `HW_POWER` is `require`. A driver calls it once before its first step (lines 80 to 117).
3. `hw_init` starts the record of one result folder. It calls `hw_check`, writes `status.txt` and `probe.txt`, sets the `EXIT` trap, and starts the sampler and `atx` in the background (`hw_atx_start` starts `atx`) (lines 119 to 142).
4. `hw_begin` gives the next process a numbered label and takes the snapshot before it (`hw_snap` runs `hwwatch.py snap`) (lines 149 to 156).
5. `hw_end` takes the snapshot after the process and tests that the sampler and `atx` still exist (lines 158 to 168).
6. `hw_done` stops the sampler and `atx` (`hw_atx_stop` sends the stop signal and waits at most 30 s), tests their last output and closes the record (lines 170 to 187).
7. `hw_failures` prints the number of `FAILED` lines of one record. A driver calls it after each step (lines 189 to 191).

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

## Source and explanation, line by line

- Text shown: the file `hwwatch-2026-11-24/hw.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (191 lines, 10046 bytes, sha256 `7455abf4b05635a5d2fc6503145fcf73a44f9adf387b38af8b52bace40c769c4`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

### Header comment: what the file is for (lines 1 to 6)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `# hw.sh - sourced by the run scripts of the CRB tests (ra.sh, rx.sh, run_kernels.sh, go.sh, go2.sh).` | Comment: the run scripts of the CRB tests read this file with the shell command `.` (the file is "sourced"). The script then runs the lines of this file in its own shell. So the functions and variables that this file defines exist in the script afterwards. The comment names five scripts: `ra.sh`, `rx.sh`, `run_kernels.sh`, `go.sh` and `go2.sh`. |
| 2 | `# It records the clock rate of the cores, the signs of throttling and the power beside a test.` | Comment: the file makes the hardware record. It records the clock rate of the cores, the signs of throttling and the power beside a test. Throttling means that the chip or its firmware makes a core run slower than Linux requested. |
| 3 | `# hwwatch.py (beside this file) reads the files of Linux. The vendor tool atx (Arm Telemetrix) reads the power,` | Comment: two programs do the reading. `hwwatch.py`, which lies beside this file, reads the files of Linux. The vendor tool `atx` (Arm Telemetrix) reads the power values of the firmware. The sentence goes on in line 4. |
| 4 | `# temperature and frequency values of the firmware. Nothing here needs root.` | Comment: `atx` also reads the temperature and frequency values of the firmware. No command of this file needs root rights. |
| 5 | `# atx needs one root step per boot, done by hand before the test: the script setup_arm_agi_cpu_telemetry.sh of the tool.` | Comment: `atx` needs one step with root rights after each boot. A person must run it before the test: the script `setup_arm_agi_cpu_telemetry.sh`, which belongs to the tool. |
| 6 | `#` | Comment: an empty comment line. It separates two blocks of the header. |

### Header comment: the settings (lines 7 to 19)

| Line | Source | Explanation |
|---:|---|---|
| 7 | `# Settings (environment variables):` | Comment: the heading of the list of settings. A caller sets them as environment variables before it reads this file. The list leaves out two settings of the code: `HW_PY` (line 34) and `HW_CHECK_CPUS` (line 39). |
| 8 | `#   HW=on\|off              off: the caller defines empty functions and does not source this file` | Comment: `HW` chooses between a test with the hardware record (`on`) and a test without it (`off`). With `off` the calling script defines empty functions and does not read this file. This file itself never reads the variable `HW`. |
| 9 | `#   HW_POWER=require\|off   require (default): hw_check fails when atx cannot collect. off: no record of atx.` | Comment: `HW_POWER` has two values. `require` is the default: `hw_check` fails when `atx` cannot collect. `off`: no record of `atx` is made. Line 35 sets the default. |
| 10 | `#   HW_CPU=119             the CPU on which the sampler and atx run. In a 120-thread test one test thread shares it.` | Comment: `HW_CPU` is the CPU on which the frequency sampler and `atx` run. The default is CPU 119 (line 36). In a test with 120 threads one test thread runs on the same CPU. |
| 11 | `#   HW_PERIOD_S=1          seconds between two samples of the frequency sampler` | Comment: `HW_PERIOD_S` is the time between two samples of the frequency sampler, in seconds. The default is 1 s (line 37). |
| 12 | `#   HW_WATCH_CPUS=0-119    the CPUs that the sampler and the probe read` | Comment: `HW_WATCH_CPUS` names the CPUs that the sampler and the probe read. The default is `0-119` (line 38). The probe is the file `probe.txt` that `hw_init` writes once per result folder. |
| 13 | `#   HW_ATX=$HOME/cache-perf/arm-telemetrix/bin/atx     an absolute path` | Comment: `HW_ATX` is the absolute path of the program `atx`. The default lies below the home folder (line 40). |
| 14 | `#   HW_ATX_MS=1000         sampling interval of atx, in ms` | Comment: `HW_ATX_MS` is the time between two samples of `atx`, in ms. The default is 1000 ms, which gives one sample per second (line 41). |
| 15 | `#   HW_ATX_SELECT="-g power -g thermal -g frequency"   what atx collects (metric groups of its guide)` | Comment: `HW_ATX_SELECT` says what `atx` collects. The default asks for three metric groups: `power`, `thermal` and `frequency` (line 42). By the comment, the guide of the tool describes these groups. |
| 16 | `#   HW_ATX_STOP=INT        the signal that ends a collection of atx` | Comment: `HW_ATX_STOP` is the name of the signal that ends a collection of `atx`. The default is `INT`, the interrupt signal (line 43). |
| 17 | `#   HW_ATX_TRIAL_S=5       length of the trial collection of hw_check, in s` | Comment: `HW_ATX_TRIAL_S` is the length of the trial collection that `hw_check` makes, in seconds. The default is 5 s (line 44). |
| 18 | `#   HW_MAX_S=3600          the sampler and atx end by themselves after this time, in s` | Comment: `HW_MAX_S` is a time limit in seconds. The sampler and `atx` end without a signal after this time. The default is 3600 s, which is 1 hour (line 45). |
| 19 | `#   HW_ROOT=               prefix of /sys and /proc for hwwatch.py (tests only)` | Comment: `HW_ROOT` is a folder name that `hwwatch.py` puts in front of `/sys` and `/proc`. It is empty by default (line 46). Only the tests set it, to read a copied file tree. |

### Header comment: the functions and the files (lines 20 to 32)

| Line | Source | Explanation |
|---:|---|---|
| 20 | `# Functions:` | Comment: the heading of the list of functions. |
| 21 | `#   hw_check               tests the tools, once per boot and setting. Status 0 = usable.` | Comment: `hw_check` tests the tools, once per boot and setting. Status 0 means that the hardware record is usable. The code remembers a passed test by the boot id and the value of `HW_POWER` only (line 83). So a change of another setting, for example `HW_CPU` or `HW_ATX`, does not repeat the test. The function starts in line 80. |
| 22 | `#   hw_init DIR            writes DIR/hw/probe.txt and starts the sampler and atx for the result folder DIR.` | Comment: `hw_init DIR` writes the file `DIR/hw/probe.txt`. Then it starts the sampler and `atx` for the result folder `DIR`. The function starts in line 119. |
| 23 | `#                          Status 0 = started. It sets an EXIT trap that calls hw_done.` | Comment: continues line 22. Status 0 means "started". `hw_init` sets an `EXIT` trap that calls `hw_done`: the shell runs `hw_done` when it ends. The code is less strict than the word "started": `hw_init` does not test whether the sampler or `atx` runs after its start, and it returns 0 also when `atx` could not be started (lines 135 to 141). |
| 24 | `#   hw_begin LABEL CPUS    snapshot of CPUS before a process. Call it before the quiet time of the launch.` | Comment: `hw_begin LABEL CPUS` takes a snapshot of the CPUs `CPUS` before a process. A snapshot is one read of a small set of files for a list of CPUs, written to one file. The caller must place the call before the quiet time of the launch. In `rx.sh` the quiet time is a pause of 5 s. So the launch still follows the pause directly. |
| 25 | `#   hw_end                 snapshot after the process` | Comment: `hw_end` takes the snapshot after the process. |
| 26 | `#   hw_done                stops the sampler and atx` | Comment: `hw_done` stops the sampler and `atx`. |
| 27 | `#   hw_failures DIR        prints the number of FAILED lines of DIR/hw/status.txt ("missing" without that file)` | Comment: `hw_failures DIR` prints the number of lines that start with `FAILED` in the file `DIR/hw/status.txt`. It prints the word `missing` when that file does not exist. |
| 28 | `# After hw_init a failure does not stop the test: it adds a line "FAILED ..." to DIR/hw/status.txt.` | Comment: a failure after `hw_init` does not stop the test. It adds a line that starts with `FAILED` to the file `DIR/hw/status.txt`. |
| 29 | `# Files in DIR/hw: probe.txt, watch.txt, NNN-LABEL.before.txt, NNN-LABEL.after.txt, atx/ (files of atx), status.txt,` | Comment: the files in the folder `DIR/hw`: `probe.txt`, `watch.txt` (the samples), one file `NNN-LABEL.before.txt` and one file `NNN-LABEL.after.txt` per process (the two snapshots), the folder `atx` with the files of `atx`, and `status.txt`. The list goes on in line 30. |
| 30 | `# errors.txt (error output of hwwatch.py). "hwwatch.py report DIR" prints the result.` | Comment: the last file of the list is `errors.txt`, the error output of `hwwatch.py`. The command `hwwatch.py report DIR` prints the result of the record. |
| 31 | `# The functions are safe under "set -euo pipefail": each command that can fail is guarded.` | Comment: the functions are safe under `set -euo pipefail`. These three options of Bash make a script stop at a failed command (`-e`), at a variable that was never set (`-u`) and at a failed stage of a pipeline (`pipefail`). Each command of this file that can fail is guarded, for example with `\|\| true`. So a failure of the record does not end the calling script. |

### Settings with their defaults, and the state variables (lines 33 to 48)

| Line | Source | Explanation |
|---:|---|---|
| 33 | `HW_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)` | `HW_DIR`: the full path of the folder that holds this file. `${BASH_SOURCE[0]}` is the path of the file that Bash reads now, also when another script sources it. `dirname` cuts off the file name. `cd` goes into that folder, and `pwd` prints its full path. `$( )` runs these commands in a subshell (a copy of the shell in its own process) and gives their output. So the working folder of the caller does not change. |
| 34 | `HW_PY=${HW_PY:-python3}` | `HW_PY`: the Python program that runs `hwwatch.py`. `${HW_PY:-python3}` keeps the value of the caller when the variable is set and not empty. If not, the value is `python3`. The header comment does not list this setting. |
| 35 | `HW_POWER=${HW_POWER:-require}` | `HW_POWER`: `require` unless the caller has set another value that is not empty (line 9). |
| 36 | `HW_CPU=${HW_CPU:-119}` | `HW_CPU`: 119 unless the caller has set it to a value that is not empty. The sampler and `atx` are pinned to this CPU (line 60, line 91, line 135). |
| 37 | `HW_PERIOD_S=${HW_PERIOD_S:-1}` | `HW_PERIOD_S`: 1 unless the caller has set it to a value that is not empty. The sampler of a result folder takes one sample per this number of seconds (line 136). |
| 38 | `HW_WATCH_CPUS=${HW_WATCH_CPUS:-0-119}` | `HW_WATCH_CPUS`: `0-119` unless the caller has set it to a value that is not empty. The probe and the sampler of a result folder read these CPUs (line 130, line 135). |
| 39 | `HW_CHECK_CPUS=${HW_CHECK_CPUS:-0}` | `HW_CHECK_CPUS`: `0` unless the caller has set it to a value that is not empty. `hw_check` tests the files of Linux on these CPUs only, by default on CPU 0 (line 86, line 91). The header comment does not list this setting. |
| 40 | `HW_ATX=${HW_ATX:-$HOME/cache-perf/arm-telemetrix/bin/atx}` | `HW_ATX`: the path of the program `atx`. The default is `cache-perf/arm-telemetrix/bin/atx` below the home folder. |
| 41 | `HW_ATX_MS=${HW_ATX_MS:-1000}` | `HW_ATX_MS`: 1000 unless the caller has set it to a value that is not empty. `atx` gets it as its sampling interval in ms (line 60). |
| 42 | `HW_ATX_SELECT=${HW_ATX_SELECT:--g power -g thermal -g frequency}` | `HW_ATX_SELECT`: the options that say what `atx` collects. The default text is `-g power -g thermal -g frequency`. In the source, the first hyphen of this text follows the `:-` of the expansion directly. |
| 43 | `HW_ATX_STOP=${HW_ATX_STOP:-INT}` | `HW_ATX_STOP`: `INT` unless the caller has set it to a value that is not empty. This signal ends a collection (line 69). |
| 44 | `HW_ATX_TRIAL_S=${HW_ATX_TRIAL_S:-5}` | `HW_ATX_TRIAL_S`: 5 unless the caller has set it to a value that is not empty. The trial collection of `hw_check` lasts this number of seconds (line 105). |
| 45 | `HW_MAX_S=${HW_MAX_S:-3600}` | `HW_MAX_S`: 3600 unless the caller has set it to a value that is not empty. The sampler and `atx` get it as their time limit in seconds (line 60, line 136). |
| 46 | `HW_ROOT=${HW_ROOT:-}` | `HW_ROOT`: empty unless the caller has set it. The expansion `${HW_ROOT:-}` also makes sure that the variable exists. So a later use does not fail under `set -u`. |
| 47 | `HW_OUT=; HW_N=0; HW_CUR=; HW_CUR_CPUS=; HW_WATCH_PID=; HW_ATX_PID=` | Sets the six state variables of the record. `HW_OUT`: the folder `hw` of the result folder. It is empty while no record is open. `HW_N`: the number of processes so far. `HW_CUR`: the label of the process that is open now. `HW_CUR_CPUS`: the CPU list of that process. `HW_WATCH_PID`: the process id of the sampler. `HW_ATX_PID`: the process id of `atx`. |

### Function `hw_note`: one line for the file `status.txt` (lines 49 to 52)

| Line | Source | Explanation |
|---:|---|---|
| 49 | `hw_note() { # ok\|FAILED text` | Starts the function `hw_note`. It appends one line to the file `status.txt` of the record. By the comment, the first argument is the word `ok` or `FAILED`, and the second is a text. |
| 50 | `  echo "$1 utc $(date -u +%FT%TZ) $2" >> "$HW_OUT/status.txt" \|\| true` | `echo` writes the first argument, the word `utc`, the UTC time of this moment and the text. `date -u +%FT%TZ` prints the date and the time in the form `YYYY-MM-DDTHH:MM:SSZ`. `>>` appends the line to `status.txt` in the folder `HW_OUT`. `\|\| true`: when the write fails, the command `true` runs and succeeds. So a failed write cannot stop a caller that uses `set -e`. |
| 51 | `}` | Ends the function `hw_note`. |

### Function `hw_atx_start`: start `atx` in the background (lines 53 to 64)

| Line | Source | Explanation |
|---:|---|---|
| 53 | `# atx in the background, with its output folder as its working folder. The subshell replaces itself by atx (exec),` | Comment: the function starts `atx` in the background, and the output folder of `atx` is its working folder. The subshell of line 60 replaces itself with the program (`exec`). The sentence goes on in line 54. |
| 54 | `# so $! is the process id of atx. The word splitting of HW_ATX_SELECT is wanted.` | Comment: so `$!` is the process id of `atx`. `$!` gives the process id of the last command that the shell started in the background. The text of `HW_ATX_SELECT` stands without quotes on purpose: the shell splits it at the spaces into single options. |
| 55 | `# "env --default-signal": the drivers are started with "nohup setsid ... &" from a shell without job control. That` | Comment: explains `env --default-signal` in line 60. The drivers (`go.sh` and `go2.sh`) are started with `nohup setsid ... &` from a shell without job control. The sentence goes on in line 56. |
| 56 | `# shell makes them ignore SIGINT, and every program they start inherits this. env gives atx the default action back.` | Comment: such a shell makes the driver ignore the signal SIGINT, and every program that the driver starts inherits this. `env` sets the action for the signal back to the default before it starts `atx`. So `atx` can react to the signal. |
| 57 | `hw_atx_start() { # folder` | Starts the function `hw_atx_start`. Its argument is the folder for the files of `atx`. |
| 58 | `  mkdir -p "$1" \|\| return 1` | `mkdir -p` creates the folder and the folders above it. It reports no error when the folder exists. When it fails, the function returns status 1 and starts nothing. |
| 59 | `  # shellcheck disable=SC2086` | Comment for ShellCheck, a tool that checks shell scripts: do not report rule SC2086 for the next command. That rule reports a variable without quotes. Here `$HW_ATX_SELECT` has no quotes on purpose (line 54). |
| 60 | `  ( cd "$1" && exec taskset -c "$HW_CPU" env --default-signal="$HW_ATX_STOP" "$HW_ATX" collect -i "$HW_ATX_MS" -d "$HW_MAX_S" \` | The parenthesis opens a subshell. `cd` goes into the output folder. When that works, `exec` replaces the subshell with `taskset -c`, which limits the process to the CPU `HW_CPU` (119 by default). `taskset` then runs `env --default-signal`, which sets the action for the signal `HW_ATX_STOP` back to the default. `env` then runs `atx collect`. `-i`: the sampling interval in ms (1000 by default). `-d`: the time limit in seconds (3600 by default). Each program replaces the one before it in the same process. The backslash at the end continues the command in line 61. |
| 61 | `      $HW_ATX_SELECT -r summary -r interval -o . -n atx > atx.stdout 2> atx.stderr < /dev/null ) &` | Continues the command of line 60. `$HW_ATX_SELECT` gives the options that choose the metric groups. `-r summary -r interval` asks for two reports. `-o .` and `-n atx`: by the stand-in program of `test_hwwatch.py`, `-o` names the output folder and `-n` the start of the report names. So the summary is the file `atx_summary.csv` in this folder (line 77). The standard output of `atx` goes to the file `atx.stdout` and its error output to `atx.stderr`. Its input is `/dev/null`, an empty input. The closing parenthesis ends the subshell, and `&` runs it in the background. So the function goes on immediately. |
| 62 | `  HW_ATX_PID=$!` | `HW_ATX_PID`: the process id of the background process. After the `exec` chain of line 60 this process is `atx`. |
| 63 | `}` | Ends the function `hw_atx_start`. |

### Function `hw_atx_stop`: end the collection of `atx` and test its summary (lines 65 to 79)

| Line | Source | Explanation |
|---:|---|---|
| 65 | `# Ends the collection and waits at most 30 s for atx to write its reports. Status 0 = the summary file holds a table.` | Comment: the function ends the collection. Then it waits at most 30 s for `atx` to write its reports. Status 0 means that the summary file holds a table. |
| 66 | `hw_atx_stop() { # folder` | Starts the function `hw_atx_stop`. Its argument is the folder of the files of `atx`. |
| 67 | `  local i` | `local i`: the loop variable `i` exists only inside this function. |
| 68 | `  [ -n "$HW_ATX_PID" ] \|\| return 1` | `-n` tests that a text is not empty. When `HW_ATX_PID` is empty, no `atx` was started, and the function returns status 1. |
| 69 | `  kill -s "$HW_ATX_STOP" "$HW_ATX_PID" 2>/dev/null \|\| true` | `kill -s` sends the stop signal `HW_ATX_STOP` (`INT` by default) to `atx`. `2>/dev/null` discards the error message of `kill`, for example when the process no longer exists. `\|\| true` keeps a failed `kill` from stopping a caller that uses `set -e`. |
| 70 | `  for i in $(seq 60); do kill -0 "$HW_ATX_PID" 2>/dev/null \|\| break; sleep 0.5; done` | Waits until `atx` has ended, at most 60 times 0.5 s, which is 30 s. `seq 60` prints the numbers 1 to 60. `kill -0` sends no signal. It only tests whether the process still exists. When the process is gone, `break` leaves the loop. If not, `sleep 0.5` waits 0.5 s. |
| 71 | `  if kill -0 "$HW_ATX_PID" 2>/dev/null; then` | Tests once more whether `atx` still exists after the wait. |
| 72 | `    echo "atx did not end within 30 s after SIG$HW_ATX_STOP: killed" >> "$1/atx.stderr" \|\| true` | `atx` still exists: appends a message to the file `atx.stderr` in the folder. It says that `atx` did not end within 30 s after the stop signal and was killed. |
| 73 | `    kill -KILL "$HW_ATX_PID" 2>/dev/null \|\| true` | `atx` still exists: `kill -KILL` ends it at once. A process cannot catch or ignore this signal. So `atx` writes nothing more. |
| 74 | `  fi` | Ends the `if` of line 71. |
| 75 | `  wait "$HW_ATX_PID" 2>/dev/null \|\| true` | `wait` waits for the end of the process and reads its exit status. The status is not used, and errors are discarded. |
| 76 | `  HW_ATX_PID=` | Empties `HW_ATX_PID`: no `atx` runs now. |
| 77 | `  [ -s "$1/atx_summary.csv" ] && grep -q '^Metric:' "$1/atx_summary.csv"` | The last command gives the status of the function. The status is 0 only when both tests pass. `-s`: the file `atx_summary.csv` exists and is not empty. `grep -q` prints nothing. It succeeds when the file holds a line that starts with `Metric:` (`^` stands for the start of a line). |
| 78 | `}` | Ends the function `hw_atx_stop`. |

### Function `hw_check`: test of the files of Linux and of the sampler (lines 80 to 97)

| Line | Source | Explanation |
|---:|---|---|
| 80 | `hw_check() {` | Starts the function `hw_check`. It tests whether the hardware record is usable: the files of Linux, the sampler and, when power is required, `atx`. It returns 0 when all tests pass. On a failure it prints lines that start with `hw: FAILED` and returns 1. |
| 81 | `  local t boot` | `local t boot`: two variables that exist only inside this function. `t` will hold a temporary folder and `boot` the boot id. |
| 82 | `  boot=$(cat "$HW_ROOT/proc/sys/kernel/random/boot_id" 2>/dev/null) \|\| true` | `boot`: the boot id, read from the file `/proc/sys/kernel/random/boot_id` (with the prefix `HW_ROOT` in tests). Linux creates this random identifier once per boot. When the file cannot be read, `boot` stays empty and the function goes on. |
| 83 | `  if [ -n "$boot" ] && [ "${HW_CHECKED:-}" = "$boot:$HW_POWER" ]; then return 0; fi` | Skips the whole check when it already passed. `HW_CHECKED` holds the boot id and the value of `HW_POWER` of the last check that passed (line 115). When the boot id could be read and both are the same now, the function returns 0 at once. `${HW_CHECKED:-}` gives an empty text when the variable is not set. `HW_CHECKED` is an exported variable. So a run script that a driver starts later gets it and does not repeat the check. |
| 84 | `  [ -r "$HW_DIR/hwwatch.py" ] \|\| { echo "hw: FAILED: missing $HW_DIR/hwwatch.py"; return 1; }` | `-r` tests that the file `hwwatch.py` beside this file exists and is readable. If not, the function prints `hw: FAILED: missing` with the path and returns 1. The braces group the two commands that run after a failed test. |
| 85 | `  t=$(mktemp -d "${TMPDIR:-/tmp}/hwcheck.XXXXXX") \|\| { echo "hw: FAILED: mktemp"; return 1; }` | `mktemp -d` creates a new empty folder with a random name that starts with `hwcheck.` and prints its path. The folder lies in `TMPDIR`, or in `/tmp` when `TMPDIR` is not set. `t` keeps the path. When this fails, the function prints `hw: FAILED: mktemp` and returns 1. |
| 86 | `  if ! "$HW_PY" "$HW_DIR/hwwatch.py" check --cpus "$HW_CHECK_CPUS" --root "$HW_ROOT" > "$t/check.txt" 2>&1; then` | Test 1 of 3: the files of Linux. Runs `hwwatch.py check` for the CPUs `HW_CHECK_CPUS` (CPU 0 by default). `check` tests that the two counters, the average clock rate and the requested rate of each of these CPUs are readable. For this it reads the counter file of each of these CPUs once, and by the header of `hwwatch.py` such a read interrupts the core. The command has no `taskset`. `--root` passes the prefix `HW_ROOT`. `>` writes the output to the file `check.txt` in the temporary folder, and `2>&1` sends the error output to the same file. `if !` runs lines 87 to 89 when the program returns a status other than 0. |
| 87 | `    cat "$t/check.txt"; rm -rf "$t"` | On failure: `cat` prints the output of the check, and `rm -rf` deletes the temporary folder with all its files. |
| 88 | `    echo "hw: FAILED: the frequency files of Linux are not usable (HW=off runs the test without any hardware record)"` | On failure: prints that the frequency files of Linux are not usable. The message adds that `HW=off` runs the test without any hardware record. |
| 89 | `    return 1` | On failure: the function returns 1. |
| 90 | `  fi` | Ends the `if` of line 86. |
| 91 | `  if ! taskset -c "$HW_CPU" "$HW_PY" "$HW_DIR/hwwatch.py" watch --cpus "$HW_CHECK_CPUS" --root "$HW_ROOT" --pid $$ \` | Test 2 of 3: a short run of the sampler on the CPU of the record. `taskset -c` limits the program to the CPU `HW_CPU`. `hwwatch.py watch` samples the CPUs `HW_CHECK_CPUS`. `--pid $$` names the process that the sampler watches: `$$` is the process id of the shell that runs the script. The command continues in line 92. |
| 92 | `       --period-s 0.1 --max-s 0.3 --out "$t/watch.txt" > "$t/watch.err" 2>&1 < /dev/null \` | Continues the command of line 91. `--period-s 0.1`: one sample each 0.1 s. `--max-s 0.3`: the sampler ends without a signal after 0.3 s. The samples go to the file `watch.txt` in the temporary folder. The other output of the program goes to `watch.err`. The input is `/dev/null`, an empty input. |
| 93 | `     \|\| ! grep -q '^# end reason=max_s' "$t/watch.txt"; then` | Continues the condition of line 91. The test fails when the sampler returns a status other than 0, or when `watch.txt` holds no line that starts with `# end reason=max_s`. That line shows that the sampler ran until its time limit. |
| 94 | `    cat "$t/watch.err"; rm -rf "$t"` | On failure: prints the messages of the sampler and deletes the temporary folder. |
| 95 | `    echo "hw: FAILED: the sampler did not run on CPU $HW_CPU (HW_CPU names the CPU)"` | On failure: prints that the sampler did not run on the CPU `HW_CPU`, and that the setting `HW_CPU` names the CPU. |
| 96 | `    return 1` | On failure: the function returns 1. |
| 97 | `  fi` | Ends the `if` of line 91. |

### Function `hw_check`: trial collection of `atx`, and the result (lines 98 to 118)

| Line | Source | Explanation |
|---:|---|---|
| 98 | `  if [ "$HW_POWER" = require ]; then` | Test 3 of 3 runs only when `HW_POWER` is `require`. |
| 99 | `    if [ ! -x "$HW_ATX" ]; then` | `-x` tests whether the file `HW_ATX` exists and is executable. `!` reverses the test. So lines 100 to 102 run when there is no such program. |
| 100 | `      rm -rf "$t"` | No `atx`: deletes the temporary folder. |
| 101 | `      echo "hw: FAILED: no atx at $HW_ATX (HW_ATX names it; HW_POWER=off runs the test without the power record)"` | No `atx`: prints `hw: FAILED: no atx at` with the path. The message names the two ways to go on: `HW_ATX` gives the right path, or `HW_POWER=off` runs the test without the power record. |
| 102 | `      return 1` | No `atx`: the function returns 1. |
| 103 | `    fi` | Ends the `if` of line 99. |
| 104 | `    hw_atx_start "$t/atx" \|\| true` | The trial collection. `hw_atx_start` starts `atx` in the background. Its output folder is the folder `atx` in the temporary folder. `\|\| true`: a failed start does not end the function here. The test of line 106 finds it. |
| 105 | `    sleep "$HW_ATX_TRIAL_S"` | Waits `HW_ATX_TRIAL_S` seconds (5 by default) while `atx` collects. |
| 106 | `    if ! hw_atx_stop "$t/atx" \|\| ! grep -q '^Metric: .*power' "$t/atx/atx_summary.csv"; then` | `hw_atx_stop` sends the stop signal and waits for the reports. The trial fails in two cases. Case 1: `hw_atx_stop` returns a status other than 0. Case 2: the summary file holds no line that starts with `Metric:` and holds the word `power` later in the line. So the summary must hold at least one power metric. |
| 107 | `      echo "hw: FAILED: a trial collection of atx ($HW_ATX_TRIAL_S s, then SIG$HW_ATX_STOP) gave no summary with a power metric (HW_ATX_TRIAL_S sets the time)."` | On failure: prints that the trial collection gave no summary with a power metric. The message names the length of the trial, the stop signal and the setting `HW_ATX_TRIAL_S`. |
| 108 | `      echo "hw: after each boot, root must run setup_arm_agi_cpu_telemetry.sh of the tool once. HW_POWER=off runs the test without the power record."` | On failure: prints a hint. After each boot, root must run the script `setup_arm_agi_cpu_telemetry.sh` of the tool once. The message adds that `HW_POWER=off` runs the test without the power record. |
| 109 | `      echo "hw: last lines of atx:"; tail -n 5 "$t/atx/atx.stderr" "$t/atx/atx.stdout" 2>/dev/null \|\| true` | On failure: prints the heading `hw: last lines of atx:`. Then `tail -n 5` prints the last 5 lines of each of the files `atx.stderr` and `atx.stdout`. Errors of `tail` are discarded. |
| 110 | `      rm -rf "$t"` | On failure: deletes the temporary folder. |
| 111 | `      return 1` | On failure: the function returns 1. |
| 112 | `    fi` | Ends the `if` of line 106. |
| 113 | `  fi` | Ends the `if` of line 98. |
| 114 | `  rm -rf "$t"` | All tests passed: deletes the temporary folder. The output of `hwwatch.py check` in the file `check.txt` is deleted with it and is never printed in this case. So a note of that program about a missing throttle flag is not shown here. |
| 115 | `  export HW_CHECKED="$boot:$HW_POWER"` | Remembers the check. `HW_CHECKED` gets the boot id, a colon and the value of `HW_POWER`. `export` puts the variable into the environment. So every process that this shell starts later gets it (line 83). |
| 116 | `  echo "hw: check ok (frequency files of Linux: yes; power by atx: $([ "$HW_POWER" = require ] && echo yes \|\| echo "no, HW_POWER=$HW_POWER"); sampler CPU $HW_CPU)"` | Prints one line that starts with `hw: check ok`. It says that the frequency files of Linux are usable, whether `atx` records the power, and on which CPU the sampler runs. `$( )` runs a test inside the text: it gives `yes` when `HW_POWER` is `require`. If not, it gives `no, HW_POWER=` with the value. This `echo` is the last command. So the function returns 0. |
| 117 | `}` | Ends the function `hw_check`. |

### Function `hw_init`: start the record of one result folder (lines 119 to 143)

| Line | Source | Explanation |
|---:|---|---|
| 119 | `hw_init() { # result folder` | Starts the function `hw_init`. Its argument is the result folder. The function writes the first files of the record and starts the sampler and `atx`. |
| 120 | `  [ -n "${1:-}" ] \|\| { echo "hw: FAILED: hw_init needs the result folder"; return 1; }` | `${1:-}` is the first argument, or an empty text when there is none. When it is empty, the function prints `hw: FAILED: hw_init needs the result folder` and returns 1. |
| 121 | `  hw_check \|\| return 1` | Runs `hw_check`. When it fails, `hw_init` returns 1. It has written nothing into the result folder at this point. When `HW_CHECKED` already fits, `hw_check` returns at once (line 83). |
| 122 | `  HW_OUT=$1/hw; HW_N=0; HW_CUR=` | `HW_OUT`: the folder `hw` inside the result folder. `HW_N` becomes 0 and `HW_CUR` becomes empty: no process is counted yet. |
| 123 | `  mkdir -p "$HW_OUT" \|\| { echo "hw: FAILED: cannot create $HW_OUT"; HW_OUT=; return 1; }` | Creates the folder `hw`. When this fails, the function prints `hw: FAILED: cannot create` with the path, empties `HW_OUT` and returns 1. With an empty `HW_OUT`, the functions `hw_begin`, `hw_end` and `hw_done` do nothing. |
| 124 | `  {` | Opens a group of commands. The output of the whole group goes to one file (line 129). |
| 125 | `    echo "settings HW_POWER=$HW_POWER HW_CPU=$HW_CPU HW_PERIOD_S=$HW_PERIOD_S HW_WATCH_CPUS=$HW_WATCH_CPUS HW_MAX_S=$HW_MAX_S HW_ATX=$HW_ATX HW_ATX_MS=$HW_ATX_MS HW_ATX_STOP=$HW_ATX_STOP HW_ATX_SELECT=$HW_ATX_SELECT"` | The first line of `status.txt`: the word `settings` and the values of nine settings: `HW_POWER`, `HW_CPU`, `HW_PERIOD_S`, `HW_WATCH_CPUS`, `HW_MAX_S`, `HW_ATX`, `HW_ATX_MS`, `HW_ATX_STOP` and `HW_ATX_SELECT`. |
| 126 | `    echo "sha256 $(sha256sum < "$HW_DIR/hw.sh" \| cut -d' ' -f1) hw.sh"` | The second line of `status.txt`: the word `sha256`, the checksum of this file and the name `hw.sh`. `sha256sum` reads the file from its standard input and prints the checksum and a hyphen. `cut -d' ' -f1` keeps the first field, which is the checksum. |
| 127 | `    echo "sha256 $(sha256sum < "$HW_DIR/hwwatch.py" \| cut -d' ' -f1) hwwatch.py"` | The third line: the same for `hwwatch.py`. |
| 128 | `    if [ "$HW_POWER" = require ]; then echo "sha256 $(sha256sum < "$HW_ATX" \| cut -d' ' -f1) atx"; fi` | The fourth line: the same for the program `atx`. It is written only when `HW_POWER` is `require`. |
| 129 | `  } > "$HW_OUT/status.txt" \|\| true` | Closes the group. `>` writes its output to the file `status.txt` in `HW_OUT` and replaces an older file. `\|\| true`: a failed write does not end the function. |
| 130 | `  if ! "$HW_PY" "$HW_DIR/hwwatch.py" probe --cpus "$HW_WATCH_CPUS" --root "$HW_ROOT" --out "$HW_OUT/probe.txt" \` | Writes the probe. `hwwatch.py probe` reads the CPUs `HW_WATCH_CPUS` (0 to 119 by default) and writes the file `probe.txt` in `HW_OUT`. The probe holds the files of the folders `cpufreq` and `acpi_cppc` of these CPUs, without four file names that `hwwatch.py` leaves out. It also holds the sensor files and facts about the system. One of the files is the counter file, and by the header of `hwwatch.py` a read of it interrupts the core. So each of these CPUs gets one such read per probe. The command has no `taskset`, and the shell waits until the probe is written. The command continues in line 131. |
| 131 | `       < /dev/null 2>> "$HW_OUT/errors.txt"; then` | Continues the command of line 130. The input is `/dev/null`. `2>>` appends the error output of the program to the file `errors.txt` in `HW_OUT`. |
| 132 | `    echo "hw: FAILED: probe (see $HW_OUT/errors.txt)"; HW_OUT=; return 1` | The probe failed: the function prints `hw: FAILED: probe` with the path of `errors.txt`, empties `HW_OUT` and returns 1. |
| 133 | `  fi` | Ends the `if` of line 130. |
| 134 | `  trap hw_done EXIT` | Sets a trap: when the shell of the calling script ends, it first runs `hw_done`. So the sampler and `atx` are also stopped when the script ends early. |
| 135 | `  taskset -c "$HW_CPU" "$HW_PY" "$HW_DIR/hwwatch.py" watch --cpus "$HW_WATCH_CPUS" --root "$HW_ROOT" --pid $$ \` | Starts the frequency sampler. `taskset -c` limits it to the CPU `HW_CPU`. `hwwatch.py watch` samples the CPUs `HW_WATCH_CPUS`: for each sample it reads the file `cpufreq/cpuinfo_avg_freq` of each of these CPUs, a clock rate in kHz. By the header of `hwwatch.py`, such a read sends no interrupt to the core. The sampler runs in the background while the benchmark processes of the result folder run. `--pid $$`: the sampler watches the process of the calling script and ends when that process is gone. The command continues in line 136. |
| 136 | `    --period-s "$HW_PERIOD_S" --max-s "$HW_MAX_S" --out "$HW_OUT/watch.txt" < /dev/null 2>> "$HW_OUT/errors.txt" &` | Continues the command of line 135. `--period-s`: the time between two samples, `HW_PERIOD_S` seconds (1 by default). `--max-s`: the sampler ends without a signal after `HW_MAX_S` seconds (3600 by default). The samples go to the file `watch.txt` in `HW_OUT`. The input is `/dev/null`, and the error output is appended to `errors.txt`. `&` runs the command in the background. So the function goes on immediately. |
| 137 | `  HW_WATCH_PID=$!` | `HW_WATCH_PID`: the process id of the background command. `taskset` replaces itself with the Python program in the same process. So this is the process id of the sampler. |
| 138 | `  if [ "$HW_POWER" = require ]; then` | `atx` is started only when `HW_POWER` is `require`. |
| 139 | `    hw_atx_start "$HW_OUT/atx" \|\| hw_note FAILED "atx could not be started"` | `hw_atx_start` starts one collection of `atx` for the whole result folder. Its files go to the folder `atx` in `HW_OUT`. `atx` runs on the CPU `HW_CPU` while the benchmark processes run (line 60). `hw_atx_start` returns a status other than 0 only when it cannot create the folder. Then `hw_note` adds a `FAILED` line to `status.txt`, and the function goes on. An `atx` that fails after its start in the background is not seen here. The tests of line 163 and line 180 find it later. |
| 140 | `  fi` | Ends the `if` of line 138. |
| 141 | `  hw_note ok "init: probe written, sampler pid $HW_WATCH_PID, atx pid ${HW_ATX_PID:-none}"` | Adds an `ok` line to `status.txt`. It says that the probe is written and gives the process ids of the sampler and of `atx`. `${HW_ATX_PID:-none}` gives the word `none` when no `atx` was started. This is the last command, and `hw_note` always succeeds (line 50). So `hw_init` returns 0 from here, also when the sampler or `atx` did not start. |
| 142 | `}` | Ends the function `hw_init`. |

### Functions `hw_snap` and `hw_begin`: the snapshot before a process (lines 144 to 157)

| Line | Source | Explanation |
|---:|---|---|
| 144 | `hw_snap() { # before\|after` | Starts the function `hw_snap`. It takes one snapshot of the CPUs of the open process. By the comment, its argument is the word `before` or `after`. |
| 145 | `  "$HW_PY" "$HW_DIR/hwwatch.py" snap --cpus "$HW_CUR_CPUS" --root "$HW_ROOT" --label "$HW_CUR" \` | Runs `hwwatch.py snap` for the CPUs `HW_CUR_CPUS`. A snapshot reads six files of each of these CPUs, among them the counter file, and then the system and sensor files. By the header of `hwwatch.py`, a read of the counter file interrupts the core. `--label` passes the label of the process. The command has no `taskset`. So the snapshot program may run on every CPU that the calling shell may use. The shell waits until the snapshot is written. The command continues in line 146. |
| 146 | `    --out "$HW_OUT/$HW_CUR.$1.txt" < /dev/null 2>> "$HW_OUT/errors.txt" \|\| hw_note FAILED "snapshot $1 of $HW_CUR"` | Continues the command of line 145. The snapshot goes to a file in `HW_OUT`. Its name is the label, a dot, the argument and `.txt`, for example `001-a.before.txt`. The input is `/dev/null`, and the error output is appended to `errors.txt`. When the program fails, `hw_note` adds a `FAILED` line with the word `snapshot`, the argument and the label. |
| 147 | `}` | Ends the function `hw_snap`. |
| 149 | `hw_begin() { # label cpus` | Starts the function `hw_begin`. A run script calls it before each benchmark process, with a label and the CPU list of the process. |
| 150 | `  [ -n "$HW_OUT" ] \|\| return 0` | When `HW_OUT` is empty, no record is open. The function then returns 0 and does nothing. |
| 151 | `  HW_N=$((HW_N + 1))` | Adds 1 to the process counter `HW_N`. `$(( ))` computes the sum. |
| 152 | `  HW_CUR=$(printf '%03d-%s' "$HW_N" "$(printf '%s' "$1" \| tr -c 'A-Za-z0-9_.+-' '_')") \|\| true` | `HW_CUR`: the label of this process in the record. The inner `printf` prints the first argument. `tr -c` replaces every character that is not a letter, a digit, an underscore, a dot, a plus sign or a hyphen with an underscore. The outer `printf` puts the counter in front, with 3 digits and leading zeros, and a hyphen. So the label `bw old/read` of a first process becomes `001-bw_old_read`. `\|\| true` keeps a failure of this line from stopping a caller that uses `set -e`. |
| 153 | `  HW_CUR_CPUS=$2` | `HW_CUR_CPUS`: the second argument, the CPU list of the process. |
| 154 | `  hw_snap before` | Takes the first snapshot. It goes to the file `NNN-LABEL.before.txt`. |
| 155 | `  return 0` | Returns 0 in every case. So a failed snapshot cannot stop a caller that uses `set -e`. |
| 156 | `}` | Ends the function `hw_begin`. |

### Function `hw_end`: the snapshot after a process (lines 158 to 169)

| Line | Source | Explanation |
|---:|---|---|
| 158 | `hw_end() {` | Starts the function `hw_end`. A run script calls it after a benchmark process has ended. |
| 159 | `  [ -n "$HW_OUT" ] && [ -n "$HW_CUR" ] \|\| return 0` | When no record is open (`HW_OUT` is empty) or no process is open (`HW_CUR` is empty), the function returns 0 and does nothing. |
| 160 | `  hw_snap after` | Takes the second snapshot. It goes to the file `NNN-LABEL.after.txt`. |
| 161 | `  kill -0 "$HW_WATCH_PID" 2>/dev/null \|\| hw_note FAILED "the sampler was not running at the end of $HW_CUR"` | `kill -0` tests whether the sampler still exists. If not, `hw_note` adds a `FAILED` line: the sampler was not running at the end of this process. |
| 162 | `  if [ "$HW_POWER" = require ]; then` | The test of `atx` runs only when `HW_POWER` is `require`. |
| 163 | `    { [ -n "$HW_ATX_PID" ] && kill -0 "$HW_ATX_PID" 2>/dev/null; } \|\| hw_note FAILED "atx was not running at the end of $HW_CUR"` | The braces group two tests: `HW_ATX_PID` is not empty, and the process with that id still exists. When one of them fails, `hw_note` adds a `FAILED` line: `atx` was not running at the end of this process. |
| 164 | `  fi` | Ends the `if` of line 162. |
| 165 | `  hw_note ok "process $HW_CUR cpus $HW_CUR_CPUS"` | Adds an `ok` line with the label and the CPU list of the process. The line is also written when a `FAILED` line was added before. |
| 166 | `  HW_CUR=` | Empties `HW_CUR`: no process is open now. |
| 167 | `  return 0` | Returns 0 in every case. |
| 168 | `}` | Ends the function `hw_end`. |

### Function `hw_done`: stop the sampler and `atx` (lines 170 to 188)

| Line | Source | Explanation |
|---:|---|---|
| 170 | `hw_done() {` | Starts the function `hw_done`. A run script calls it after its last process. The trap of line 134 also calls it when the shell ends. |
| 171 | `  [ -n "$HW_OUT" ] \|\| return 0` | When no record is open, the function returns 0. So a second call does nothing. |
| 172 | `  if [ -n "$HW_WATCH_PID" ]; then` | Lines 173 to 177 run only when a sampler was started. |
| 173 | `    kill -TERM "$HW_WATCH_PID" 2>/dev/null \|\| true` | Sends the signal SIGTERM to the sampler. The sampler then writes its last line, which holds `reason=signal`, and ends. |
| 174 | `    wait "$HW_WATCH_PID" 2>/dev/null \|\| true` | Waits until the sampler has ended. |
| 175 | `    HW_WATCH_PID=` | Empties `HW_WATCH_PID`. |
| 176 | `    grep -q '^# end reason=signal' "$HW_OUT/watch.txt" 2>/dev/null \` | Tests whether `watch.txt` holds a line that starts with `# end reason=signal`. The command continues in line 177. |
| 177 | `      \|\| hw_note FAILED "the sampler ended before the test did: $(grep '^# end' "$HW_OUT/watch.txt" 2>/dev/null \|\| echo "no end line")"` | Continues the command of line 176. Without such a line, the sampler ended before this stop, or it wrote no last line. `hw_note` then adds a `FAILED` line. Its text holds the last line of the sampler (a line that starts with `# end`), or the words `no end line`. |
| 178 | `  fi` | Ends the `if` of line 172. |
| 179 | `  if [ -n "$HW_ATX_PID" ]; then` | Line 180 runs only when `atx` was started and is not yet stopped. |
| 180 | `    hw_atx_stop "$HW_OUT/atx" \|\| hw_note FAILED "atx wrote no summary with a table (see $HW_OUT/atx/atx.stderr)"` | `hw_atx_stop` ends the collection and waits for the reports. When it returns a status other than 0, `hw_note` adds a `FAILED` line: `atx` wrote no summary with a table. The line names the file `atx.stderr`. |
| 181 | `  fi` | Ends the `if` of line 179. |
| 182 | `  [ -z "$HW_CUR" ] \|\| hw_note FAILED "the test ended inside the process $HW_CUR: no snapshot after it"` | `-z` tests that `HW_CUR` is empty. When it is not empty, the script ended between `hw_begin` and `hw_end`. `hw_note` then adds a `FAILED` line: the test ended inside this process, and no snapshot was taken after it. |
| 183 | `  hw_note ok "done: $HW_N processes"` | Adds the last `ok` line: the word `done` and the number of processes. |
| 184 | `  HW_OUT=` | Empties `HW_OUT`: the record is closed. Later calls of `hw_begin`, `hw_end` and `hw_done` do nothing. |
| 185 | `  trap - EXIT` | `trap - EXIT` removes the trap of line 134. |
| 186 | `  return 0` | Returns 0 in every case. |
| 187 | `}` | Ends the function `hw_done`. |

### Function `hw_failures`: count the failed parts of one record (lines 189 to 191)

| Line | Source | Explanation |
|---:|---|---|
| 189 | `hw_failures() { # result folder` | Starts the function `hw_failures`. Its argument is a result folder. The drivers `go.sh` and `go2.sh` call it after each step. They count a step as incomplete when the printed value is not `0`. |
| 190 | `  if [ -f "$1/hw/status.txt" ]; then grep -c '^FAILED' "$1/hw/status.txt" \|\| true; else echo missing; fi` | `-f` tests whether the file `hw/status.txt` exists in the result folder. If it does, `grep -c` prints the number of lines that start with `FAILED`. `grep` returns status 1 when the number is 0, and `\|\| true` turns that status into 0. If the file does not exist, the function prints the word `missing`. |
| 191 | `}` | Ends the function `hw_failures`. |

## References

- [Ref1] The design note of this code: the file `status/2026-11-24-hw-record-handoff.md` of the repo `/home/jhan/workspace/ai-proj/arm-crb`. Its short version says that nothing ran on CRB. Decision 5 of its section 5 gives the reason for one collection of `atx` per result folder: a start and a stop of `atx` between two processes would change the timing of the test.
