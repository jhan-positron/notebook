## Short version: purpose

`gen_s1.sh` is one command that builds the result page of question Q1 of Parts B and C from the 14 result folders of session 1. It calls the page generator `make_q1_html.py` and writes the file `partB-q1-result.html` beside itself. Arguments of the caller are passed on, so the folders of a second session can be added.

## Words used here

- **Agent server**: the Linux server from which the tests were started and on which the analysis ran.
- **Result folder**: the folder that one run of a test script writes on CRB, under `~/cache-perf/results/`. Its name ends with the start time in UTC. This script names the copies on the agent server.
- **CRB**: the Arm reference server under test. It has 128 CPUs.
- **UTC**: Coordinated Universal Time.
- **Plan**: the test plan of 2026-11-13. It has two questions, Q1 and Q2, and the Parts A to D.
- **Q1**: the first question of the plan, about one thread with an 8 MiB buffer. Its steps are B1, B2, B3, B4, B6, C1 and C2.
- **Q2**: the second question of the plan, about 120 threads with one 256 MiB buffer per thread. Its steps are B7, B10, B8, B5, B9 and C3. Another script, `make_q2_html.py`, builds its page.
- **Parts B and C**: the parts of the plan that use the runner `bwx`, a benchmark program that times a sequence of loops in one process. Part C repeats steps with core counters.
- **Session of Parts B and C**: one run of all steps of Parts B and C. On this page "session" has this meaning.
- **Step**: one measurement of the plan. Each call of the run script for a step writes one result folder. Step B10 has two calls, `B10a` and `B10b`.
- **Page generator**: the script `make_q1_html.py`. It builds one HTML result page for question Q1 from result folders [Ref1].
- **Header line**: the line that the run script writes into the csv file of a result folder before each process. It holds load readings.
- **`env.txt`**: a file of a result folder with a reading of the machine state at the start and at the end of the step.
- **Exit status**: the number that a process returns when it ends. 0 means success.

## Main flow

1. Set the folder of the result folders on the agent server ({L3}).
2. Find the folder of this script ({L4}).
3. Run `make_q1_html.py` with the session name `s1`, the 14 result folders, the arguments of the caller and the output file ({L5}).

## Behavior a reader must know

- The script builds the page of Q1 only. Its name and its comment do not say which page ({L2}, {L5}).
- The paths of the result folders are fixed to the working folder on the agent server ({L3}). The code repo keeps the same folders in another place [Ref2].
- The output file is written beside the script, also when the script is called from another folder ({L4-5}). By the code of `make_q1_html.py` an existing file of that name is replaced [Ref1].
- The script has no `set -e` and one command. Its exit status is the exit status of `python3`.
- It reads local files only. It does not contact CRB.

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q1_html.py`: the page generator. Its description names the steps of Q1 and says what it reads from folders of other steps. Its function `main` reads the options `--session` and `-o` and opens the output file for writing.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/logs/session1-folders.txt`: the list of the 14 result folders of session 1, with the same names as in the script. The folders lie in `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/`.
