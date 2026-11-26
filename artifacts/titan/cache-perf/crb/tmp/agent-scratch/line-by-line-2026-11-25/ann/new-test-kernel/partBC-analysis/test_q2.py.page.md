## Short version: purpose

`test_q2.py` tests the page builder `make_q2_html.py`. It writes invented result folders in the row format of the runner, builds pages from them, and checks the words of the hypotheses and the text of the pages. The rates are invented in a way that gives each decision rule a known result.

## Words used here

- **Page builder**: the file `make_q2_html.py`. It builds the HTML result page for question Q2 from result folders. The tests import it under the short name `Q`.
- **Plan**: the file `plan.md`, the test plan of 2026-11-13. It names the questions, the hypotheses, eleven rules for the measurements, and the steps [Ref3].
- **Handoff**: the file `handoff.md`, the instructions for the execution of the plan. Its section B.3 defines the rows that the runner prints. Its sections B.4 and B.10 define the irregular interval and the decision rules [Ref2].
- **Q2**: the second question of the plan, about 64 threads on mesh 0 and 56 threads on mesh 1 with one 256 MiB buffer per thread: why the old read kernel has a higher total than the new one, and why the write kernels give several separate totals.
- **Mesh 0, mesh 1**: the two halves of the chip. CPUs 0 to 63 sit on mesh 0. CPUs 64 to 127 sit on mesh 1.
- **Kernel**: the inner loop of a benchmark that reads, writes or copies memory. On this page "kernel" means this loop. The operating system kernel is always written "Linux kernel".
- **Old read, new read, asm read**: the names that the page builder prints for the kernels `oldread`, `read` and `asmread`. `asmread2` is a second copy of `asmread`. The write kernels are `oldwrite`, `write`, `asmwrite` and `asmwrite2`.
- **Runner**: a benchmark program that times a sequence of kernels in one process and prints one row per thread. The versions are named `bwx`, `bwx8`, `bwx10`, `bwx11`, `bwx12` and `bwx13`.
- **Process**: one start of a benchmark binary.
- **Interval**: one timed measurement inside a process.
- **Round, position**: a runner repeats its sequence of kernels. Each repeat is a round, counted from 0. The position is the place of a kernel in the sequence, counted from 0.
- **Rate**: bytes divided by time, in GB/s.
- **GB, MiB**: GB = 1e9 bytes. MiB = 1048576 bytes (2 to the power of 20).
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC. The tests write folders of the same form on the machine on which they run.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **Load average**: the number of tasks that are runnable or wait for disk input and output, averaged by Linux over the last 1, 5 and 15 minutes (file `/proc/loadavg`). The fourth field of the file gives the tasks that are runnable now and the number of all tasks.
- **Invented session**: the result folders that the function `session` writes for one session. No measurement stands behind them.
- **Session of Parts B and C**: one run of all steps of Parts B and C of the plan. Rule 10 of the plan asks for at least 2 sessions some hours apart. On this page "session" has this meaning.
- **Step**: one measurement of the plan with its own result folder. The steps of Q2 are B7 (read kernels in 8 settings), B10 (write kernels in 8 settings), B8 (read kernels with fewer threads on mesh 1), B5 (old read against loops with added `nop` instructions), B9 (one and two buffers per thread) and C3 (the sequences of B7 and B5 with counters).
- **Hypotheses H7a to H11**: H7a: the stop method and the short interval make a part of the difference. H7b: the common start makes a part of it. H8: a loop that only loads reaches the uniform state at a lower thread count than old read. H9a: the second buffer per thread changed the pattern of old read. H9b: old read differs between days or sessions for a reason other than the kernel. H10: the memory system fetches lines that the loop does not consume. H11: the higher write totals come from the threads of one mesh.
- **B5 statement**: the statement that step B5 of the plan tests: vector adds are needed for the split pattern of old read at 64+56 threads [Ref3]. The page builder words it as "vector adds are needed for the pattern and total of old read".
- **Header line**: the line that the run script writes into the csv file before each process. It starts with `-- step` and holds the step, the tag, the binary, the waited seconds, the load averages, the logins, the time and the arguments.
- **Tag**: the name of a process, for example `pass-500-common-p1`.
- **`env.txt`, `launches.txt`**: two files of a result folder. `env.txt` holds a reading of the machine state at the start and at the end of the step. `launches.txt` holds a load reading and a process list before each process.
- **T row, P row, C row**: rows of the csv file. A T row holds for one thread and one interval the CPU, the bytes, the elapsed time, three times of the thread, the passes and the flag `late`. A P row holds the page state of one buffer. A C row holds times and counter values of one thread and interval.
- **Setting**: one combination of stop method (`pass` or `common`), shortest interval length in ms and start (`common` or `offset`), written as in `pass/500/common`.
- **Reproduction condition**: the setting `pass/500/common`.
- **Total, `M_hist`**: the bytes of all threads of one interval divided by the longest elapsed time of a thread, in GB/s.
- **D**: the total of old read minus the total of new read, one value per process.
- **A/A spread**: the largest absolute difference between the two copies of one loop (`asmread2` minus `asmread`) over the processes of one setting.
- **Resolved**: D of a setting is resolved when its absolute median over the processes is above the A/A spread and every D has the same sign. A setting needs 4 processes with a value. If not, it is `not observed`.
- **q**: the thread rate at the 10th percentile divided by the thread rate at the 90th percentile, in one interval.
- **Pattern labels**: the labels `split` (q below 0.65) and `uniform` (q above 0.85) of the handoff. By decision 2 of the user of 2026-11-13 they are not used.
- **Label rule**: a rule of the analysis script that needs the pattern labels.
- **The five words**: the words that rule 11 of the plan allows for a result: `rejected`, `not rejected`, `not observed`, `not resolved` and `not tested`.
- **Flag**: the result of one session for the prediction of a hypothesis: `fail` (it failed), `hold` (it held), `not observed` or `not resolved`.
- **Plan word**: `supported` or `contradicted`, the words of the plan for H8 and H11. For H11 the page builder prints one of them in brackets after its own word.
- **Page rules**: four rules of the page builder for the words of H8, H9a, H9b, H10, H11 and the B5 statement. They are not rules of the plan.
- **Open for the user**: the mark of the page builder for a judgment between two readings of a rule that the page does not make.
- **Late thread, irregular interval**: a T row with the flag `late` marks a thread that started late. An interval with such a thread is irregular and is not used.
- **2 % check**: rule 7 of the plan for whole passes: one pass may take at most 2 % of the interval, so each thread needs at least 50 passes.
- **Analysis script**: the file `analyze_bwx.py`. The page builder uses it to read the rows and to apply the decision rules.
- **Model**: the dictionary of computed values that the function `compute` of the page builder returns.
- **Unix time**: the seconds counted from 1970-01-01 00:00 UTC.
- **`assert`**: a Python statement that stops the program with an error when its condition is false.

## Main flow

1. The helpers are defined: the class `Folder` writes one invented result folder, and `session` writes the folders of one session with chosen effects ({L26-147}).
2. `check_page_rules` holds checks of the user's rules for a page: no outside resource, a Short version of at most three sentences, the place of the reference indexes, and text that stays inside each drawing ({L170-216}). The tests 1, 2, 5, 7 and 10 call it for one page each. The 7 other pages of the tests do not go through it.
3. Test 1 builds a page from one session and proves that it never says `rejected` ({L231-251}).
4. Test 2 adds a second equal session and proves that `rejected` then appears, with the other reading and the mark for the user ({L253-275}).
5. Test 3 gives the stop method a real effect and proves that only H7a changes its word ({L277-287}).
6. Test 4 proves that results of the label rule do not reach the words of the page ({L289-309}).
7. Tests 5 to 7 cover one late thread, the three cases of H11, and missing steps ({L311-347}).
8. Tests 8 and 9 cover the command line with a folder of another step, and the load section ({L349-363}).
9. Test 10 covers a busy process of another account, the times of the sessions, and a deviation of the setting ({L365-393}).
10. Test 11 covers the 2 % check, the sign of a rounded zero, the common axis of B8, and H11 over two sessions ({L395-416}).
11. The temporary folder is deleted, and the script prints that all tests passed ({L418-420}).

## Behavior a reader must know

- The tests run the real analysis script through the page builder. So they test both together. The import in {L12} needs the folders that `make_q2_html.py` looks in.
- No test reads a real result folder or contacts CRB. Every number in the folders is invented ({L44-63}).
- Every invented T row of an interval has the same elapsed time and the same end time. So the end skew is 0, and the total `M_hist` equals the sum of the thread rates ({L59}).
- A failed `assert` stops the run at once with a Python error. The later tests do not run. The temporary folder is not deleted either: the delete stands at the end of `main` ({L418-419}).
- With `--keep DIR` the folder `DIR` is first deleted with all its content and then filled ({L223}).
- Without `--keep` the invented folders lie in a new temporary folder whose name starts with `q2test-` ({L221}).
- Test 6 checks for one session with two faster meshes only that the word is not `rejected`. It does not check the plan word of that page ({L330}). By the code of the function `hypotheses` of the page builder, that page gets the word `not rejected` with the plan word `supported`. For two such sessions the test expects the plan word `contradicted` ({L332}). So the plan word of the one-session page does not fit its data, and no test notices it.
- The check of the text boxes in the drawings uses an estimated text width. No browser measures the text ({L202}).

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q2_html.py`: the page builder under test.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/handoff.md`: the handoff: section B.3 (output rows), B.4 (late thread, irregular interval) and B.10 (decision procedure).
- [Ref3] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/report/plan.md`: the plan: the hypotheses, the rules 7, 10 and 11, and the tested statement of step B5 in the table of the steps.
