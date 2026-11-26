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

1. Set the folder of `visit.sh` and of the logs ({L4}).
2. Keep two groups of settings as texts: the counter settings `EV` and the timing settings `ST` ({L5-6}).
3. Define the function `v`: one visit, then the test of its log ({L7}).
4. Visits 1 to 3: the steps B7, B10a and B10b, each in its own login ({L8-10}).
5. Visit 4: the steps B8, B5 and B9, with the timing settings and the thread counts of B8 ({L11}).
6. Visit 5: the steps B1, B4 and B6 ({L12}).
7. Visit 6: the steps B2, B3, C1 and C2, with the counter settings ({L13}).
8. Visit 7: step C3, with the counter settings, the timing settings and the list of the B7 settings to repeat ({L14}).

## Behavior a reader must know

- The script times nothing and starts no benchmark itself. Each visit runs `run_bwx.sh` on CRB.
- The script has no `set -e`. The only test is the search for the text `ssh status 0` in the log of each visit ({L7}). When the text is missing, the script prints a message and ends with exit status 1. The later visits do not run. When all seven visits pass the test, the exit status is 0.
- The seven visits follow each other without a pause. The script makes seven logins to CRB.
- The script sets no `STOP_AT`. `visit.sh` then passes `STOP_AT=none`, unless the caller of `session2.sh` has set `STOP_AT` in the environment. One value then holds for all seven visits. The result folders of session 2 record `STOP_AT=none` [Ref2].
- The script does not read the Slack channel. {L3} leaves that to the caller, every 10 min. The marker file is checked on CRB: once by `visit.sh` at each login, and by `run_bwx.sh` before and during every process.
- All settings are fixed in the file: the counter codes, the timing settings, the thread counts of B8 and the B7 settings of C3. They are the settings of session 1 [Ref2].
- Each visit writes its log to `visit-s2-<steps>.log` in the folder `N`. A log of an earlier run with the same name is replaced.
- The run of session 2 printed seven lines `visit ... done`, one per visit [Ref3].

## References

- [Ref1] the file `A7-core-events.txt` of the result folder `partA-20261113T204939Z` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. Its first line gives `type=11` for the counter device `armv8_pmuv3_0`. Its lines for `cpu_cycles`, `inst_retired`, `l1d_cache_refill`, `l2d_cache_refill` and `ll_cache_miss_rd` give the codes `0x0011`, `0x0008`, `0x0003`, `0x0017` and `0x0037`.
- [Ref2] the files `env.txt` of the 28 step folders of the two sessions in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. The files `logs/session1-folders.txt` and `logs/session2-folders.txt` list the folders in time order. The first line of each `env.txt` ends with the steps of its visit, and its line `## settings:` holds `STOP_AT`, the timing settings, the thread counts of B8, the B7 settings of C3 and the counter settings. The settings line of each step folder of session 2 is equal to that of the same step in session 1.
- [Ref3] the file `logs/session2.log` in `tests/2026-11-13-new-read-kernel/` of the repo `arm-crb`. It holds seven lines of the form `visit <log> done <time>`, one for each of the seven log names of this script, in the order of {L8-14}. A last line, `session2 exit 0`, is not printed by this script. The result folders of session 2 carry the date 2026-11-14 in their names.
