# `session2.sh` explained, line by line

- Source file: `new-test-kernel/session2.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 14 lines, 1077 bytes).
- sha256 of the source when this page was built: `bb384617858b38f013132083698fb032d5be9bfcdbaae41dacd42baacbf52dcd`.

## Short version: purpose

`session2.sh` runs session 2 of Parts B and C of the test plan of 2026-11-13 from the agent server: seven visits to CRB, the Arm server under test, one after the other, each made by `visit.sh`. After each visit it reads the log of the visit. It stops with exit status 1 at the first visit whose log does not show the `ssh` status 0.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It asks two questions about the new kernels and lists the measurements in the parts A to D.
- **Parts B and C**: the deciding measurements of the plan that need no root. They use the runner `bwx`. Part C also reads the counters of the cores. These are not the part C of the later rerun.
- **Part A (screening)**: the first part of the plan: a first look with the two existing binaries, in the steps A1 to A7. Its step A7 read the type number and the event codes of the core counters. This is not the part A of the later rerun.
- **Session 1, session 2**: the two runs of all steps of Parts B and C. The plan asks for 2 sessions some hours apart. This is not the session of the later rerun.
- **Visit**: one login to CRB that runs one call of `run_bwx.sh`. The script `visit.sh` makes it and writes a log.
- **`run_bwx.sh`**: the run script of Parts B and C on CRB. One call runs the steps that its arguments name, one process at a time, with the runner `bwx`.
- **Step**: one named batch of processes of Parts B and C, for example `B7` or `C3`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **`ENVV`**: a text with extra settings of the form `NAME=value`. `visit.sh` puts it before the call of `run_bwx.sh` on CRB.
- **Block**: a time window that another user has reserved on CRB.
- **Marker file**: the file `/tmp/positron-perf.RUNNING` on CRB. It exists while another user runs a performance test. Our scripts stop when it exists.
- **Exit status**: the number that a process returns when it ends. 0 means success.
- **UTC**: Coordinated Universal Time.

## Main flow

1. Set the folder of `visit.sh` and of the logs (line 4).
2. Keep two groups of settings as texts: the counter settings `EV` and the timing settings `ST` (lines 5 to 6).
3. Define the function `v`: one visit, then the test of its log (line 7).
4. Visits 1 to 3: the steps B7, B10a and B10b, each in its own login (lines 8 to 10).
5. Visit 4: the steps B8, B5 and B9, with the timing settings and the thread counts of B8 (line 11).
6. Visit 5: the steps B1, B4 and B6 (line 12).
7. Visit 6: the steps B2, B3, C1 and C2, with the counter settings (line 13).
8. Visit 7: step C3, with the counter settings, the timing settings and the list of the B7 settings to repeat (line 14).

## Behavior a reader must know

- The script times nothing and starts no benchmark itself. Each visit runs `run_bwx.sh` on CRB.
- The script has no `set -e`. The only test is the search for the text `ssh status 0` in the log of each visit (line 7). When the text is missing, the script prints a message and ends with exit status 1. The later visits do not run. When all seven visits pass the test, the exit status is 0.
- The seven visits follow each other without a pause. The script makes seven logins to CRB.
- The script sets no `STOP_AT`. `visit.sh` then passes `STOP_AT=none`, unless the caller of `session2.sh` has set `STOP_AT` in the environment. One value then holds for all seven visits. The result folders of session 2 record `STOP_AT=none` [Ref2].
- The script does not read the Slack channel. Line 3 leaves that to the caller, every 10 min. The marker file is checked on CRB: once by `visit.sh` at each login, and by `run_bwx.sh` before and during every process.
- All settings are fixed in the file: the counter codes, the timing settings, the thread counts of B8 and the B7 settings of C3. They are the settings of session 1 [Ref2].
- Each visit writes its log to `visit-s2-<steps>.log` in the folder `N`. A log of an earlier run with the same name is replaced.
- The run of session 2 printed seven lines `visit ... done`, one per visit [Ref3].

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/session2.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (14 lines, 1077 bytes, sha256 `bb384617858b38f013132083698fb032d5be9bfcdbaae41dacd42baacbf52dcd`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# session2.sh - session 2 of Parts B and C: the visits of session 1 in the same order with the same settings.` | Comment: the name and the purpose of the file. It runs session 2 of Parts B and C: the visits of session 1 again, in the same order and with the same settings. The files `env.txt` of the result folders of the two sessions record the same groups of steps and the same settings [Ref2]. |
| 3 | `# It stops at the first visit that does not end with status 0. Watch #phoenix-crb every 10 min while it runs.` | Comment: the script stops at the first visit that does not end with status 0 (line 7). The second sentence is an instruction for the caller: read the Slack channel `#phoenix-crb` every 10 min while the script runs. Other users announce their blocks on CRB in that channel. A block is a time window that another user has reserved. The script itself does not read the channel. |
| 4 | `N=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel` | `N`: the folder `new-test-kernel` on the agent server, as a fixed path. It holds `visit.sh` and gets the logs. |
| 5 | `EV='BWX_PMU_TYPE=11 BWX_EVENTS=cycles=0x11,instructions=0x08,l1d_refill=0x03,l2d_refill=0x17,ll_miss_rd=0x37'` | `EV`: the counter settings of Part C, as one text. `BWX_PMU_TYPE=11`: the type number that Linux gives to the counter device of the cores. `BWX_EVENTS`: five counter events, each written as name and code. They are the cycles (`0x11`), the instructions (`0x08`), the refills of the L1 data cache (`0x03`), the refills of the L2 data cache (`0x17`) and the read misses of the last cache level (`0x37`). The file `A7-core-events.txt`, which step A7 of Part A wrote on CRB, holds the type number 11 and these five codes [Ref1]. The runner `bwx` reads the two variables from its environment when it counts (option `--count`). |
| 6 | `ST='BWX_STOP=common BWX_START=common BWX_MIN_MS=6000'` | `ST`: the timing settings for the steps that depend on the result of step B7, as one text. `BWX_STOP=common`: all threads of a process have one common stop time. The runner sets it, and each thread stops at its first clock reading at or after it. `BWX_START=common`: every thread starts at the start of its buffer. `BWX_MIN_MS=6000`: the stop time lies 6000 ms after the common start time of the interval. A thread reads its own start time a little later. So its own time can be a little shorter than 6000 ms. `run_bwx.sh` passes the three values to the runner as `--stop`, `--start` and `--min-ms` in the steps B8, B5 and B9, and in the B5 processes of step C3. |
| 7 | `v() { local log=$1; shift; "$N/visit.sh" "$log" "$@"; grep -q "ssh status 0" "$N/$log.log" \|\| { echo "visit $log did not end with status 0: stop"; exit 1; }; echo "visit $log done $(date -u +%T)"; }` | Defines the function `v`, which makes one visit and tests how it ended. The first argument is the log name. `shift` drops it, and the arguments that are left are the step names. The function calls `visit.sh` with them and waits for its end. Then `grep -q` looks, without output, for the text `ssh status 0` in the log of the visit. `visit.sh` writes a line with that text when `ssh` ended with status 0. When the text is missing, the function prints `visit <log> did not end with status 0: stop` and ends the whole script with exit status 1. If not, it prints `visit <log> done` and the UTC time (`date -u +%T` prints hours, minutes and seconds). |
| 8 | `v visit-s2-B7 B7` | Visit 1: step B7, with the log `visit-s2-B7.log`. No extra setting is passed. By `run_bwx.sh`, step B7 times the old read kernel, the new read kernel and `asmread` with 64 threads on mesh 0 and 56 on mesh 1, in all 8 combinations of the stop method, the interval length (500 ms or 6000 ms) and the start method. |
| 9 | `v visit-s2-B10a B10a` | Visit 2: step B10a. By `run_bwx.sh`, step B10 times the write kernels with the same thread placement in the 8 combinations of the timing settings, with interval lengths of 500 ms and 15000 ms. B10a holds the processes 1 and 2 of every combination. |
| 10 | `v visit-s2-B10b B10b` | Visit 3: step B10b, the processes 3 and 4 of every combination of step B10. |
| 11 | `ENVV="$ST B8_COUNTS=\"64+32 64+36 64+40 64+44 64+48 64+52 64+56\"" v visit-s2-B8B5B9 B8 B5 B9` | Visit 4: the steps B8, B5 and B9. A setting before a function call holds for that one call: `v` and the `visit.sh` that it starts see `ENVV`, and the next call does not. The value is the timing settings `ST` plus `B8_COUNTS`, the thread counts of step B8: 64 threads on mesh 0 and 32, 36, 40, 44, 48, 52 or 56 threads on mesh 1. Each backslash with a quote puts a quote character into the text. So the shell on CRB reads the seven counts as one value. B5 times read loops with added `nop` instructions, which do nothing. B9 times the old read kernel with one and with two buffers per thread. |
| 12 | `v visit-s2-B1B4B6 B1 B4 B6` | Visit 5: the steps B1, B4 and B6, the steps with one thread that need no extra setting. B1 compares the C copy kernel with the hand-written copy kernel. B4 times `asmread` at 8 MiB with and without huge pages. B6 times the old read kernel at 8 MiB and at 1 MiB. |
| 13 | `ENVV="$EV" v visit-s2-B2B3C1C2 B2 B3 C1 C2` | Visit 6: the steps B2, B3, C1 and C2, with the counter settings `EV`. The steps C1 and C2 need them: they repeat B4 and B1 with counters. B2 and B3 are variants of step B1. Their processes do not count, so they do not use the settings. |
| 14 | `ENVV="$EV $ST C3_B7_SETTINGS=\"pass:500:common pass:500:offset pass:6000:common pass:6000:offset common:500:common common:500:offset common:6000:common common:6000:offset\"" v visit-s2-C3 C3` | Visit 7: step C3, with the counter settings `EV`, the timing settings `ST` and `C3_B7_SETTINGS`. That value lists the settings of step B7 that C3 repeats with counters. Each entry has the form `stop:min_ms:start`. Here it lists all 8 combinations: `pass` or `common`, 500 or 6000 ms, `common` or `offset`. When this visit has ended with status 0, the script ends too. Its exit status is then that of the last `echo`, which is 0. |

## References

- [Ref1] the file `A7-core-events.txt` of the result folder `partA-20261113T204939Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. Its first line gives `type=11` for the counter device `armv8_pmuv3_0`. Its lines for `cpu_cycles`, `inst_retired`, `l1d_cache_refill`, `l2d_cache_refill` and `ll_cache_miss_rd` give the codes `0x0011`, `0x0008`, `0x0003`, `0x0017` and `0x0037`.
- [Ref2] the files `env.txt` of the 28 step folders of the two sessions in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. The files `logs/session1-folders.txt` and `logs/session2-folders.txt` list the folders in time order. The first line of each `env.txt` ends with the steps of its visit, and its line `## settings:` holds `STOP_AT`, the timing settings, the thread counts of B8, the B7 settings of C3 and the counter settings. The settings line of each step folder of session 2 is equal to that of the same step in session 1.
- [Ref3] the file `logs/session2.log` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. It holds seven lines of the form `visit <log> done <time>`, one for each of the seven log names of this script, in the order of lines 8 to 14. A last line, `session2 exit 0`, is not printed by this script. The result folders of session 2 carry the date 2026-11-14 in their names.
