## Short version: purpose

`recount_results_md.py` counts again a set of numbers of the result handoff `results.md` of Parts B and C of the test plan of 2026-11-13. It reads the raw csv files of the two sessions and of the short run and prints the numbers as text lines. It decides nothing, and it applies none of the rules that leave a process or an interval out.

## Words used here

- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read kernel**: portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary `bw_old` and `oldread` in the runners.
- **New read kernel**: NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary `bw_new` and in the runners.
- **`asmread`**: a hand-written load-only loop. It has the same 8 `ldp q` loads per 256 B as the new read kernel. `ldp q` is the Arm instruction that loads two 16-byte vector registers.
- **`copy`, `asmcopy`, `asmcopy2`**: the new C copy kernel, the asm copy kernel, and a second copy of the asm copy kernel under another name.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC. This script reads the copies on the agent server.
- **Counter, counter event**: a hardware counter of the core counts events such as cycles, instructions or cache misses. Linux reads it through the `perf` interface.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13, with its questions, hypotheses, rules and steps [Ref2].
- **Handoff**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the rows of the csv files, and its section B.10 the decision rules [Ref3].
- **`results.md`**: the result handoff of Parts A, B and C of the plan. It cites the output of this script for the numbers that the script counts [Ref1].
- **Session of Parts B and C**: one run of all steps of Parts B and C of the plan. Two sessions were run, named `s1` and `s2` [Ref1].
- **Step**: one measurement of the plan with its own result folder and csv file.
- **Steps with one thread**: B1 (`copy` against `asmcopy` at four buffer sizes), B2 (three asm variants of the copy loop against `asmcopy`), B3 (the sequence of B1 in three builds with other loop addresses), B4 (`asmread` alone at 8 MiB for 200 intervals), B6 (old read at 8 MiB and at 1 MiB), C1 (B4 with counters) and C2 (B1 at 8 MiB with counters).
- **Steps with 120 threads**: B7 (the four read kernels in 8 settings) and B10 (the four write kernels in 8 settings, in the two folders `B10a` and `B10b`).
- **Short run**: one run of every sequence with intervals of 0.1 s, made before the first session to test the scripts.
- **Header line**: the line that the run script writes into the csv file before each process. It starts with `-- step` and holds the tag, the binary and the arguments of the runner.
- **Tag**: the name of a process in the run script.
- **T row**: a row of the csv file for one thread and one interval. Its fields, counted from 0, are `T`, round, position, kernel, thread number, CPU, bytes (6), `elapsed_s` (7), `t_sched_s`, `t_start_s`, `t_end_s` (10), `passes` and the flag (12).
- **C row**: a row for one thread and one interval of a run with counters. Its fields are `C`, round, position, kernel, thread number, CPU, the enabled time (6), the running time (7) and the CPU time of the thread (8), all in ns, and then the counter values from field 9 on: cycles, instructions, L1 refills, L2 refills and last-level read misses.
- **Level limits**: for one thread with an 8 MiB buffer, the plan calls an interval low below 69 GB/s and high above 70.5 GB/s. It calls the two limits provisional.
- **Pair value, d, e**: a pair is two intervals of two kernels that follow each other. Its value is the rate of the first-named kernel minus the rate of the other. For one process, d is the median pair value of the kernel pair and e the median pair value of the A/A pair.
- **A/A pair, A/A spread**: an A/A pair is one loop that exists twice in the program under two names. The A/A spread of a CPU is the largest absolute e of its processes.
- **Total, `M_hist`**: the bytes of all threads of one interval divided by the longest elapsed time of a thread, in GB/s.
- **D**: the total of old read minus the total of new read. For one process it is the mean over its rounds.
- **Setting**: one combination of stop method (`pass` for whole passes, `common` for a common stop time), shortest interval length in ms and start (`common` or `offset`).
- **End skew**: the latest end time of a thread in an interval minus the earliest one.
- **Choice A2, choice A5**: two choices of the analysis script `analyze_bwx.py` from its notes. A2: a rate comes from the T rows, not from the rounded total that the runner prints. A5: with whole passes an end skew above 5 ms does not make an interval irregular [Ref4].
- **Line**: 64 B, the unit of a cache.

## Main flow

1. The paths on the agent server and the two level limits are set ({L6-8}).
2. For each of the two sessions the script reads the list of its result folders and prints a heading ({L68-70}).
3. B4: it counts the intervals of each process by level. C1: it prints the number of all intervals of the step, the highest rate and the number of high intervals ({L71-77}).
4. C2: it groups the asm read intervals with counters by level and prints medians per 64 B line ({L78-93}).
5. B1 at 8 MiB, B2 and B3: with the helpers `d_and_e` and `group` it prints d and the A/A spread per CPU, without level labels ({L94-101}).
6. B6: it prints old read at 8 MiB minus old read at 1 MiB for two positions of the sequence, and counts A/A pairs whose first interval is slower ({L102-117}).
7. B7: it prints the median D of each setting as a share of the median old read total ({L118-141}).
8. B10 and B7: it prints the largest end skew with whole passes, and counts the intervals with an end skew above 5 ms ({L142-167}).
9. Over all csv files of both sessions it counts C rows with a very large count and T rows with the flag `late`, and finds the longest page reading ({L170-192}).
10. From the short run it prints the instructions per 256 B of the process with a 32 KiB buffer ({L193-202}).

## Behavior a reader must know

- Where the numbers come from: a rate is field 6 of a T row divided by field 7, in GB/s ({L36}). For 120 threads the total of an interval is the sum of field 6 over its T rows divided by the largest field 7 ({L126-128}). The end skew uses field 10 ({L150}). Counter values come from the fields 6 to 13 of the C rows ({L87}, {L182}).
- No filter: the script uses every T row that it finds. It does not test whether a process is complete or an interval is irregular, as the analysis script does. It also does not look at the level of the reference intervals, so the lines for B1, B2 and B3 are a description without labels ({L53}).
- The paths are fixed to the working folders on the agent server ({L6-7}). The code repo keeps the same result folders and the two folder lists in another place [Ref6].
- The script prints to the standard output only. The usage line sends that output to `recount_results_md.txt` ({L3}).
- The script stops with a Python error when a file is missing, when a C row of C2 holds `NA` in a field that it reads, when a counter group of C2 did not run for its whole enabled time ({L88}), or when one of the three levels of C2 has no interval ({L93}).
- Fixed values in the code: the level limits 69.0 and 70.5 GB/s ({L8}), the end skew of 0.005 s ({L166}), the count of 1e13 ({L182}), and the name of the folder of the short run ({L194}).
- For a process with 120 threads the entry `cpu` holds only the first number of its CPU list ({L22}). The script uses `cpu` only for the steps with one thread.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/results.md`: the result handoff. Its reference 21 names this script and its output, and its section "What was run" lists the two sessions.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the plan: rule 5 (the level limits) and the tables of the steps.
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff: section B.3 (output rows), B.8 (the test of 11 instructions per 256 B), B.9 (the sequences of the steps) and B.10 (pair values, d and e).
- [Ref4] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-scripts.md`: the choices A2 and A5 of the analysis script.
- [Ref5] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/DEVIATIONS-bwx.md`: the added line `# page_read`, and the list of the points that only a build on CRB can verify.
- [Ref6] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/logs/session1-folders.txt` and `session2-folders.txt` in the same folder: the two folder lists. The result folders lie in `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/`.
- [Ref7] `/home/jhan/workspace/ai-proj/arm-crb/code/bwx-2026-11-13/run_bwx.sh`: the run script, with the sequences of B1 and B6 and the process of the short run with a 32 KiB buffer.
