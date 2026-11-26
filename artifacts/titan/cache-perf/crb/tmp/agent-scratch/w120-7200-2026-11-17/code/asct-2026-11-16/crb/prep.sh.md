# `prep.sh` explained, line by line

- Source file: `asct-2026-11-16/crb/prep.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 79 lines, 6039 bytes).
- sha256 of the source when this page was built: `701b60cfba52332f8650fd23339cd0102ff9e92d87bb399fbdb37079d5d46616`.

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

1. Stop when the marker file exists (lines 7 to 8).
2. Set the work folder, the result folder and the path of the installed binary (lines 9 to 12).
3. Write the machine state to `env.txt` (lines 13 to 30).
4. Unpack the source archive of ASCT. Build the probe binary and a second plain binary, and write their checksums to `sha.txt` (lines 31 to 46).
5. Save the machine code of the read loops of the three binaries, and compare the installed binary with the second plain binary (lines 47 to 54).
6. Save the event list of `perf`, and let `resolve_events.py` write the raw codes to `events.codes` (lines 55 to 58).
7. Check the marker file again. Then run the smoke test: the installed binary, the probe binary once per event set, a run with two threads, and a run with a buffer of 64 MiB whose page size is read (lines 59 to 75).
8. Print the result files as a summary (lines 76 to 79).

## Behavior a reader must know

- The script times nothing itself. The ASCT binary measures and prints its own rate. The script only stores that output.
- Three places can stop the script: the marker file in line 8 and line 62 (exit status 3) and a missing work folder in line 11 (exit status 2). No other failure stops it. A failed build shows only in `build.txt`, `sha.txt` and `smoke.txt`.
- line 34 deletes the folder `build` of the work folder at every run.
- The only command with `sudo` is the test `sudo -n true` in line 27. It changes nothing.
- The marker file is checked before the smoke test but not during it. The smoke test starts 10 processes in the run of 2026-11-16 [Ref5].
- The comments in line 4 and line 59 do not fit the code. They speak of 3 processes and of the sets A and B. The loop of lines 64 to 69 runs every set.
- The comment in line 47 speaks of two read loops. Line 50 saves three functions.

## Source and explanation, line by line

- Text shown: the file `asct-2026-11-16/crb/prep.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (79 lines, 6039 bytes, sha256 `701b60cfba52332f8650fd23339cd0102ff9e92d87bb399fbdb37079d5d46616`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.
- One line holds a backslash directly before a `|`: line 78. Markdown readers do not agree on how to read this pair in a table cell. So such a line stands in a code block between two tables, with its explanation below it.

### Header comment, marker check and paths (lines 1 to 12)

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# prep.sh - one login, no root: record the machine state, build ASCT's probe variant of the memory benchmark` | Comment: the purpose. The script needs one login to CRB and no root rights. It records the machine state. Then it builds the probe variant of the benchmark binary of ASCT. The probe variant is the build that holds the counter code of ASCT. One line of the code uses `sudo`: the test `sudo -n true` in line 27. |
| 3 | `# binary from ASCT's own source tarball with ASCT's own flags (src/core/config/ubench.json), resolve the counter` | Comment, continued: the build uses the source archive of ASCT and the compiler flags of ASCT (file `src/core/config/ubench.json` of ASCT). Then the script finds the raw code of each counter event. |
| 4 | `# event codes, save the machine code of the read loops, and run a 3-process smoke test on CPU 2.` | Comment, continued: the script saves the machine code of the read loops and runs a smoke test with 3 processes on CPU 2. A smoke test is a short run that only shows whether the programs work. The code starts more than 3 processes: one in line 63, one per event set in line 68, one in line 72 and one in line 74. |
| 5 | `# Writes only under ~/cache-perf. CPUs 0-119 only.` | Comment: the script writes only below `~/cache-perf` and uses the CPUs 0 to 119 only. The code sets the CPU list of each benchmark process with `taskset -c 0-119`. The other commands, such as `make`, run with the CPU list of the login shell, which line 16 records. The file `env.txt` of the run of 2026-11-16 gives `0-119` for that list [Ref4]. |
| 6 | `set -u` | `set -u`: the script stops when it uses a variable that was never set. There is no `set -e`. So a failed command alone does not stop the script. |
| 7 | `M=/tmp/positron-perf.RUNNING` | `M`: the path of the marker file. |
| 8 | `[ -e $M ] && { echo "RUNNING file present: stop"; exit 3; }` | Marker check 1 of 2. When the marker file exists (`-e`), the script prints `RUNNING file present: stop` and ends with exit status 3. It has written no file at this point. |
| 9 | `W=$HOME/cache-perf/asct-20261116` | `W`: the work folder on CRB, `cache-perf/asct-20261116` in the home folder of the user. It holds the scripts and the input files of this cross-check. |
| 10 | `out=$HOME/cache-perf/results/asct-prep-$(date -u +%Y%m%dT%H%M%SZ); mkdir -p $out` | `out`: the result folder. Its name is `asct-prep-` and the UTC time of this moment (`date -u`): year, month and day, the letter `T`, hours, minutes and seconds, the letter `Z`. `mkdir -p` creates the folder, with the folders above it when they are missing. |
| 11 | `cd $W \|\| exit 2` | Changes to the work folder. When that fails, the script ends with exit status 2. The file names without a folder in line 34, line 57, line 58 and line 69 mean files of this folder. |
| 12 | `PLAIN=$HOME/asct/asct_venv/bin/loaded-latency-asct-sve.bin` | `PLAIN`: the benchmark binary that the installer of ASCT built, in the folder `asct_venv/bin` of the ASCT installation. This page calls it the installed binary. |

### The machine state, written to `env.txt` (lines 13 to 30)

| Line | Source | Explanation |
|---:|---|---|
| 13 | `{` | Opens a group of commands. Line 30 sends the output of the whole group to the file `env.txt`. |
| 14 | `  echo "utc $(date -u +%FT%TZ)"; echo "kernel $(uname -r)"; echo "loadavg $(cat /proc/loadavg)"; echo "users $(who \| wc -l)"; who` | Writes five things. First the word `utc` and the UTC date and time. Then the word `kernel` and the release of the running Linux kernel (`uname -r`). Then the word `loadavg` and the content of `/proc/loadavg`. Then the word `users` and the number of logins: `who` prints one line per login, and `wc -l` counts the lines. Last, the logins themselves. |
| 15 | `  echo "nproc $(nproc) online $(cat /sys/devices/system/cpu/online) isolated $(cat /sys/devices/system/cpu/isolated)"` | Writes three values: the number of CPUs that this shell may use (`nproc`), the list of the CPUs that are online, and the list of the isolated CPUs. Linux gives the two lists in files below `/sys/devices/system/cpu`. Isolated CPUs are CPUs that the Linux scheduler keeps free of normal tasks. |
| 16 | `  echo "shell affinity $(taskset -pc $$ \| sed 's/.*: //')"` | Writes the CPU list of this shell. `taskset -pc` prints the list of a process, and `$$` is the process id of the shell. `sed` removes everything up to the last colon and the space after it. So only the list stays, in a form such as `0-119`. |
| 17 | `  echo "perf_event_paranoid $(cat /proc/sys/kernel/perf_event_paranoid)"` | Writes the Linux setting `perf_event_paranoid`. It limits which counter events a user without root rights may open. A higher number allows less. |
| 18 | `  echo "thp enabled $(cat /sys/kernel/mm/transparent_hugepage/enabled) defrag $(cat /sys/kernel/mm/transparent_hugepage/defrag)"` | Writes the two settings of transparent huge pages. `enabled` says when Linux uses them. `defrag` says whether Linux moves other memory to make room for them. In each file the active choice stands in square brackets. |
| 19 | `  grep -H . /sys/devices/system/node/node*/hugepages/hugepages-*kB/free_hugepages` | Writes the number of free reserved huge pages, one line per NUMA node and page size. `grep -H .` prints every line that is not empty, with the file name in front. |
| 20 | `  echo "numa nodes $(ls -d /sys/devices/system/node/node[0-9]* \| wc -l)"` | Writes the number of NUMA nodes. `ls -d` lists the folders `node0`, `node1` and so on. `wc -l` counts them. |
| 21 | `  echo "governor cpu2 $(cat /sys/devices/system/cpu/cpu2/cpufreq/scaling_governor 2>/dev/null) cpu41 $(cat /sys/devices/system/cpu/cpu41/cpufreq/scaling_governor 2>/dev/null)"` | Writes the governor of CPU 2 and of CPU 41. These are the two CPUs of the one-core runs. `2>/dev/null` discards the error message when a file is missing. |
| 22 | `  echo "sysreg dir: $(ls -d /sys/kernel/sysreg 2>&1)"` | Writes whether the folder `/sys/kernel/sysreg` exists. `2>&1` puts the error message of `ls` into the text when the folder does not exist. By the decisions file, the register report of ASCT needs a Linux kernel module that creates this folder. |
| 23 | `  echo "pmu units: $(ls /sys/bus/event_source/devices/ \| tr '\n' ' ')"` | Writes the names of all counter units that Linux knows. These are the folders below `/sys/bus/event_source/devices/`. `tr` replaces each line end with a space, so the names stand on one line. |
| 24 | `  echo "core pmu type $(cat /sys/bus/event_source/devices/armv8_pmuv3_0/type)"` | Writes the type number that Linux gives to the counter unit of the cores, `armv8_pmuv3_0`. |
| 25 | `  echo "numactl $(command -v numactl \|\| echo none) venv-numactl $(ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null \|\| echo none)"` | Writes where `numactl` is. `command -v` prints the path of a program that the shell can find. When it finds none, `echo none` prints `none`. The second value is the path of the copy in the ASCT installation, or `none` when `ls` does not find it. |
| 26 | `  echo "gcc $(gcc --version \| head -1)"; echo "perf $(perf --version)"` | Writes the first line of the version text of the compiler `gcc`, and the version of `perf`, the Linux counter tool. |
| 27 | `  echo "sudo without password: $(sudo -n true 2>/dev/null && echo yes \|\| echo no)"` | Writes whether `sudo` works without a password. `sudo -n true` runs the command `true`, which does nothing, as root. `-n` means that `sudo` never asks for a password and fails when it would need one. The line prints `yes` on success and `no` on failure. By the decisions file this test was the only command that ran as root on CRB in this work [Ref1]. |
| 28 | `  echo "cmdline $(cat /proc/cmdline)"` | Writes the boot parameters of the running Linux kernel (file `/proc/cmdline`). |
| 29 | `  ps -eo user,pcpu,comm --sort=-pcpu \| head -6` | Writes a header line and the 5 processes with the highest CPU share. `ps -eo user,pcpu,comm` lists all processes with three columns: user, CPU share in percent and command name. `--sort=-pcpu` puts the highest share first. `pcpu` is the CPU time of a process divided by the time from its start to now, in percent. It is not the CPU share at this moment. `head -6` keeps the first 6 lines. |
| 30 | `} > $out/env.txt 2>&1` | Ends the group of line 13. The standard output and the error messages (`2>&1`) of all its commands go to the file `env.txt` in the result folder. |

### Build of the probe binary and of a second plain binary (lines 31 to 46)

| Line | Source | Explanation |
|---:|---|---|
| 31 | `# build the probe variant and, as a check of the build recipe, the plain variant` | Comment: the next block builds the probe variant. It also builds the plain variant again. That second build is a check that the build commands of this script are the right ones. |
| 32 | `SD=$HOME/asct/asct-0.7.1+77461b3/asct-0.7.1+77461b3.tar.gz` | `SD`: the source archive of ASCT, version `0.7.1+77461b3`, on CRB. |
| 33 | `sha256sum $SD > $out/sha.txt` | Writes the sha256 of the source archive to the new file `sha.txt` in the result folder. |
| 34 | `rm -rf build && mkdir build && tar --no-same-owner -xzf $SD -C build` | Three steps. Each one runs only when the step before it succeeded. `rm -rf build` deletes the folder `build` of an earlier run. `mkdir build` creates it again. `tar -xzf` unpacks the gzip-compressed archive into it (`-C build`). `--no-same-owner`: the unpacked files belong to the user who runs `tar`. |
| 35 | `L=$W/build/asct-0.7.1+77461b3/extern/infra-microbenchmarks/loaded-latency` | `L`: the folder of the unpacked source that holds the benchmark `loaded-latency`. By the notes of the project, its file `bandwidth.c` holds the read loops of ASCT. That file is not the `bandwidth.c` of our own benchmark. |
| 36 | `DP=$W/build/asct-0.7.1+77461b3/extern/dietperf` | `DP`: the folder of the unpacked source that holds dietperf, the counter code of ASCT. |
| 37 | `{` | Opens a group of commands. Line 44 sends its output to the file `build.txt`. |
| 38 | `  cd $L` | Changes to the source folder `L`. |
| 39 | `  make clean EXE=loaded-latency-asct-probe-sve.bin` | `make clean` runs the target `clean` of the `Makefile` of ASCT. `EXE` gives the name of the probe binary. The file `build.txt` of the run of 2026-11-16 shows what the target did there: `rm -f` on a binary of that name, on the object files and on the dependency files [Ref2]. The source folder is freshly unpacked at this point (line 34). |
| 40 | `  make EXE=loaded-latency-asct-probe-sve.bin CFLAGS="-DASCT -DUSE_PROBE -DHAS_SVE -march=armv8.2-a+sve -I$DP" && cp loaded-latency-asct-probe-sve.bin $W/` | Builds the probe binary. `EXE` names the output file. `CFLAGS` holds the compiler flags that the comment in line 3 speaks of. `-DASCT`, `-DUSE_PROBE` and `-DHAS_SVE` each define a macro for the source. `-DUSE_PROBE` is the flag that the plain build of line 42 does not have. `-march=armv8.2-a+sve` allows the instructions of Armv8.2 with the vector extension SVE. `-I` with the folder `DP` tells the compiler where the header file of the counter code is. When the build succeeds, `cp` copies the binary to the work folder. |
| 41 | `  make clean EXE=loaded-latency-asct-probe-sve.bin` | Runs `make clean` again with the name of the probe binary. By the file `build.txt` of the run of 2026-11-16, it removes the object files, the dependency files and the probe binary of the source folder [Ref2]. So line 42 compiles every source file again, with its other flags. The copy of the probe binary that line 40 made in the work folder stays. |
| 42 | `  make EXE=loaded-latency-asct-sve.rebuild.bin CFLAGS="-DASCT -DHAS_SVE -march=armv8.2-a+sve" && cp loaded-latency-asct-sve.rebuild.bin $W/` | Builds the plain variant again under the name `loaded-latency-asct-sve.rebuild.bin`, without `-DUSE_PROBE` and without the folder `DP`. When the build succeeds, `cp` copies it to the work folder. Line 46 and line 53 compare it with the installed binary. |
| 43 | `  cd $W` | Changes back to the work folder. |
| 44 | `} > $out/build.txt 2>&1` | Ends the group of line 37. The output and the error messages of both builds go to the file `build.txt`. A failed build does not stop the script. |
| 45 | `PROBE=$W/loaded-latency-asct-probe-sve.bin` | `PROBE`: the copy of the probe binary in the work folder. |
| 46 | `sha256sum $PLAIN $PROBE $W/loaded-latency-asct-sve.rebuild.bin >> $out/sha.txt 2>&1` | Appends the sha256 of three binaries to `sha.txt`: the installed binary, the probe binary and the plain binary of line 42. Equal checksums of the first and the third show that the build commands of this script give the same file as the installer of ASCT. In the file `sha.txt` of the run of 2026-11-16 these two checksums are equal [Ref3]. An error message, such as one for a missing file, goes to `sha.txt` too. |

### Machine code of the read loops (lines 47 to 54)

| Line | Source | Explanation |
|---:|---|---|
| 47 | `# machine code of the two read loops in each binary; addresses removed so that the texts can be compared` | Comment: the next block saves the machine code of the two read loops of each binary. It removes the addresses. Then two texts can be compared. |
| 48 | `for b in $PLAIN $PROBE $W/loaded-latency-asct-sve.rebuild.bin; do` | Starts a loop over the three binaries: the installed one, the probe one and the plain one of line 42. `b` is the path of the binary. |
| 49 | `  n=$(basename $b)` | `n`: the file name of the binary without its folder (`basename`). |
| 50 | `  objdump -d --no-show-raw-insn $b \| awk '/^[0-9a-f]+ <(my_read\|my_read_no_nops_rep_64b\|run_bw_repetitions)>:/{p=1} p{print} p&&/^$/{p=0}' > $out/listing.$n.txt` | Writes the machine-code listing of three functions to the file `listing.NAME.txt`. `objdump -d` prints the instructions of the program as text. `--no-show-raw-insn` leaves out the instruction bytes. `awk` keeps a part of that text. It starts to print at the header line of `my_read`, `my_read_no_nops_rep_64b` or `run_bw_repetitions`. Such a line holds an address, a space, the name in angle brackets and a colon. `awk` stops after the next empty line, which ends the function. By the decisions file, `my_read_no_nops_rep_64b` is the read loop of ASCT, and `my_read` is its loop with injected NOPs. The comment in line 47 speaks of two read loops. `run_bw_repetitions` is a third function. |
| 51 | `  sed -E 's/^ *[0-9a-f]+:\s*//; s/[0-9a-f]+ <([a-z_0-9]+)\+0x[0-9a-f]+>/<\1+off>/g; s/^[0-9a-f]+ </</' $out/listing.$n.txt > $out/listing.$n.noaddr.txt` | Writes a copy without addresses to `listing.NAME.noaddr.txt`. `sed -E` makes three replacements in each line. First: at the start of an instruction line it removes the spaces, the address, the colon and the white space after it. Second: it replaces each jump target of the form address, space and `name+0x...` in angle brackets with `name+off` in angle brackets. Third: it removes the address at the start of a function header line. A jump target that has no `+0x` part keeps its address. |
| 52 | `done` | Ends the loop of line 48. |
| 53 | `cmp -s $out/listing.$(basename $PLAIN).noaddr.txt $out/listing.loaded-latency-asct-sve.rebuild.bin.noaddr.txt && echo "read loops: installed plain == rebuilt plain" >> $out/sha.txt \|\| echo "read loops: installed plain DIFFERS from rebuilt plain" >> $out/sha.txt` | Compares two listings without addresses: that of the installed binary and that of the plain binary of line 42. `cmp -s` prints nothing and returns exit status 0 when the files are equal. In that case the line appends `read loops: installed plain == rebuilt plain` to `sha.txt`. If not, it appends `read loops: installed plain DIFFERS from rebuilt plain`. The listing of the probe binary is saved but not compared here. |
| 54 | `objdump -d --no-show-raw-insn $PLAIN \| awk '/<my_read_no_nops_rep_64b>:/{p=1} p{print} p&&/^$/{p=0}' \| grep -c . >> $out/sha.txt` | Appends one number to `sha.txt`: the number of lines that the listing of `my_read_no_nops_rep_64b` has in the installed binary, with its header line. `objdump` and `awk` print the function as in line 50. `grep -c .` counts the lines that are not empty. |

### Raw codes of the counter events (lines 55 to 58)

| Line | Source | Explanation |
|---:|---|---|
| 55 | `# event codes` | Comment: the next block finds the event codes. |
| 56 | `perf list --details > $out/perf-list-details.txt 2>&1` | Saves the event list of `perf` to the file `perf-list-details.txt`. `perf list` prints the counter events that `perf` knows on this machine. With `--details` it also prints how it passes each named event to the Linux kernel: the counter unit and the raw code [Ref6]. |
| 57 | `python3 resolve_events.py events.txt events.codes > $out/resolve.txt 2>&1` | Runs `resolve_events.py`. It reads the event names of `events.txt` and writes the same sets with raw codes to `events.codes`. Both files lie in the work folder. Its report, one line per event name, goes to `resolve.txt` in the result folder. |
| 58 | `cp events.codes $out/` | Copies `events.codes` into the result folder as a record. |

### Smoke test (lines 59 to 75)

| Line | Source | Explanation |
|---:|---|---|
| 59 | `# smoke test on CPU 2: plain, then probe with set A and set B, 1 MiB` | Comment: the smoke test on CPU 2 with a buffer of 1 MiB. First the installed binary runs, then the probe binary. The comment names the sets A and B. The loop of lines 64 to 69 runs every set of `events.codes`. The file `smoke.txt` of the run of 2026-11-16 holds 7 lines of this loop, for the sets `A` to `G` [Ref5]. |
| 60 | `NUMA=$(command -v numactl \|\| ls $HOME/asct/asct_venv/bin/numactl 2>/dev/null)` | `NUMA`: the path of `numactl`. `command -v` gives the one in the search path. When there is none, `ls` gives the copy in the ASCT installation if it exists. If both fail, `NUMA` is empty. |
| 61 | `ARGS="--duration 0.25 --delay-seconds 0 --bw-cpu 2 --bw-buflen 1048576 --bw-fine-delay 0 --bw-write=0 --bw-cacheline-bytes 64"` | `ARGS`: the arguments of the smoke test processes. `--duration 0.25`: the measured phase lasts 0.25 s. `--delay-seconds 0`: the delay setting of the binary is 0 s. `--bw-cpu 2`: one read thread on CPU 2. `--bw-buflen 1048576`: a buffer of 1048576 bytes (1 MiB). `--bw-fine-delay 0`: 0 injected NOPs. `--bw-write=0`: all accesses are reads. `--bw-cacheline-bytes 64`: one cache line has 64 bytes. |
| 62 | `[ -e $M ] && { echo "marker: stop"; exit 3; }` | Marker check 2 of 2, before the first benchmark process. When the marker file exists, the script prints `marker: stop` and ends with exit status 3. The processes of lines 63 to 75 run without a further check. |
| 63 | `taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PLAIN $ARGS > $out/smoke.plain.out 2>&1; echo "rc plain $?" >> $out/smoke.txt` | Runs the installed binary once and waits for its end. `taskset -c 0-119` allows the process to run on the CPUs 0 to 119 only. `${NUMA:+$NUMA --membind 0}` gives `numactl --membind 0` when `NUMA` is not empty. The process then gets its memory from NUMA node 0 only. When `NUMA` is empty, this part gives nothing. The output and the error messages go to `smoke.plain.out`. Then the line appends `rc plain` and the exit status of the run to `smoke.txt`. |
| 64 | `while IFS='\|' read -r s evs; do` | Starts a loop over the lines of `events.codes` (line 69). `IFS='\|'` splits each line at the first `\|`. The set name goes to `s`. The list of `name=code` pairs goes to `evs`. `-r` keeps each backslash as it is. |
| 65 | `  [ -z "$evs" ] && continue` | Skips a line that has no events (`-z`: the text is empty). |
| 66 | `  codes=$(echo "$evs" \| tr ',' '\n' \| cut -d= -f2 \| paste -sd,)` | `codes`: the raw codes of the set, joined with commas. `tr` puts each `name=code` pair on its own line. `cut -d= -f2` keeps the part after the `=`. `paste -sd,` joins the lines with commas. The result has a form such as `0x11,0x8,0x3`. |
| 67 | `  mkdir -p $out/smoke.$s.d` | Creates the folder for the counter files of this set, `smoke.SET.d`. |
| 68 | `  DIETPERF_OUTDIR=$out/smoke.$s.d DIETPERF_PMUv3=$codes taskset -c 0-119 ${NUMA:+$NUMA --membind 0} $PROBE $ARGS > $out/smoke.probe.$s.out 2>&1 < /dev/null; echo "rc probe $s $? codes $codes" >> $out/smoke.txt` | Runs the probe binary once with the counters of this set. The two assignments at the start set environment variables for this one command only. `DIETPERF_OUTDIR` is the folder where the counter code writes its files. `DIETPERF_PMUv3` is the list of raw codes to count. The other parts are those of line 63. The output goes to `smoke.probe.SET.out`. The input is `/dev/null`, an empty input. So the binary cannot read the rest of `events.codes`. Then the line appends `rc probe`, the set name, the exit status and the codes to `smoke.txt`. |
| 69 | `done < events.codes` | Ends the loop of line 64. The loop reads its lines from `events.codes` in the work folder. |
| 70 | `# two threads with the probe variant: one counter file per thread is expected` | Comment: the next test runs two threads with the probe binary. It expects one counter file per thread. |
| 71 | `mkdir -p $out/smoke.two.d` | Creates the folder `smoke.two.d` for these counter files. |
| 72 | `DIETPERF_OUTDIR=$out/smoke.two.d DIETPERF_PMUv3=0x11,0x8 taskset -c 0-119 $PROBE --duration 0.25 --delay-seconds 0 --bw-cpu 2 --bw-cpu 66 --bw-buflen 1048576 --bw-fine-delay 3 --bw-write=0 --bw-cacheline-bytes 64 > $out/smoke.two.out 2>&1 < /dev/null; echo "rc two-thread probe $? files $(ls $out/smoke.two.d \| wc -l)" >> $out/smoke.txt` | Runs the probe binary with two read threads: one on CPU 2 (mesh 0) and one on CPU 66 (mesh 1). The codes `0x11` and `0x8` belong to `cpu_cycles` and `inst_retired` in the table of `resolve_events.py`. `--bw-fine-delay 3` asks for 3 injected NOPs. Each thread has a buffer of 1 MiB. This command does not use `numactl`. Then the line appends the exit status and the number of files in `smoke.two.d` to `smoke.txt`. The expected number is 2. |
| 73 | `# a 4 KiB-page or 2 MiB-page buffer? AnonHugePages of a 64 MiB run, read while it runs` | Comment: the question of the next test. Does Linux give the buffer pages of 4 KiB or pages of 2 MiB? The test reads the `AnonHugePages` value of a process with a buffer of 64 MiB while that process runs. |
| 74 | `taskset -c 0-119 $PLAIN --duration 1 --delay-seconds 0 --bw-cpu 2 --bw-buflen 67108864 --bw-fine-delay 0 --bw-write=0 --bw-cacheline-bytes 64 > $out/smoke.thp.out 2>&1 &` | Starts the installed binary in the background (`&`). The script goes on immediately. The measured phase lasts 1 s. The one thread runs on CPU 2 with a buffer of 67108864 bytes (64 MiB). This command does not use `numactl`. The output goes to `smoke.thp.out`. |
| 75 | `p=$!; sleep 1.2; grep -E "AnonHugePages\|Rss" /proc/$p/smaps_rollup > $out/smoke.thp.smaps 2>&1; wait $p` | `p`: the process id of that process. The script sleeps 1.2 s. Then `grep -E` copies two lines of `/proc/PID/smaps_rollup` to `smoke.thp.smaps`. That file is the memory summary that Linux keeps for the process. `Rss` is the memory of the process that is in RAM. `AnonHugePages` is the part of it that lies on transparent huge pages. When the process has ended by then, the error message of `grep` goes to `smoke.thp.smaps`. `wait` then waits for the end of the process. |

### Summary on the standard output (lines 76 to 79)

| Line | Source | Explanation |
|---:|---|---|
| 76 | `echo "done $out"` | Prints `done` and the path of the result folder. |
| 77 | `cat $out/env.txt; cat $out/sha.txt; tail -3 $out/build.txt; cat $out/resolve.txt; cat $out/smoke.txt` | Prints the files `env.txt` and `sha.txt`, the last 3 lines of `build.txt`, and the files `resolve.txt` and `smoke.txt`. |

Line 78 holds a backslash directly before a `|`. It stands outside the table:

```text
grep -h "Total Bandwidth (MB/sec)\|tid = " $out/smoke.*.out; for d in $out/smoke.*.d; do echo "== $(basename $d)"; cat $d/* 2>&1 | head -16; done; cat $out/smoke.thp.smaps
```

Explanation of line 78: Prints selected lines of every output file of the smoke test: each line that holds `Total Bandwidth (MB/sec)` or `tid = `. `-h` leaves out the file names. The first kind of line is the rate that the binary reports for the process. By the patterns of the analysis script `analyze.py`, two kinds of line hold `tid = `: the line with the settings of one thread, and the line with the repetitions and the time of one thread. Then, for each counter folder, the line prints the folder name and the first 16 lines of its files. Last it prints `smoke.thp.smaps`.

| Line | Source | Explanation |
|---:|---|---|
| 79 | `wc -l $out/listing.*.txt` | Prints the number of lines of each listing file. The exit status of the script is the status of this last command. |

## References

- [Ref1] `DECISIONS.md` in the folder `asct-2026-11-16`, section "Record of 2026-11-16 23:50 UTC": no root command ran on CRB in this work, except the test `sudo -n true` of `prep.sh`.
- [Ref2] `build.txt` in the result folder `asct-prep-20261116T231215Z` of the test folder `2026-11-16-asct-cross-check`: the commands that `make` printed, with the two `rm -f` lines of `make clean`.
- [Ref3] `sha.txt` in the same result folder: the four checksums and the line `read loops: installed plain == rebuilt plain`.
- [Ref4] `env.txt` in the same result folder: the line `shell affinity 0-119`.
- [Ref5] `smoke.txt` in the same result folder: one `rc` line for the installed binary, 7 lines for the sets `A` to `G` and one line for the run with two threads. The tenth process is the run of line 74, whose output file is `smoke.thp.out`.
- [Ref6] external source: Linux manual page perf-list(1), option `--details`.
