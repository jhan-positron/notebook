# `gen_s1.sh` explained, line by line

- Source file: `new-test-kernel/partBC-analysis/gen_s1.sh` in the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (Bash script, 5 lines, 631 bytes).
- sha256 of the source when this page was built: `843d9a67e22f8a0b8ab34cea94f2090d7676a976bae49c7951d4e505fc8ceb52`.

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

1. Set the folder of the result folders on the agent server (line 3).
2. Find the folder of this script (line 4).
3. Run `make_q1_html.py` with the session name `s1`, the 14 result folders, the arguments of the caller and the output file (line 5).

## Behavior a reader must know

- The script builds the page of Q1 only. Its name and its comment do not say which page (line 2, line 5).
- The paths of the result folders are fixed to the working folder on the agent server (line 3). The code repo keeps the same folders in another place [Ref2].
- The output file is written beside the script, also when the script is called from another folder (lines 4 to 5). By the code of `make_q1_html.py` an existing file of that name is replaced [Ref1].
- The script has no `set -e` and one command. Its exit status is the exit status of `python3`.
- It reads local files only. It does not contact CRB.

## Source and explanation, line by line

- Text shown: the file `new-test-kernel/partBC-analysis/gen_s1.sh` of the code repo `/home/jhan/workspace/ai-proj/arm-crb/code` (5 lines, 631 bytes, sha256 `843d9a67e22f8a0b8ab34cea94f2090d7676a976bae49c7951d4e505fc8ceb52`).
- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) and its explanation. A blank line of the source has no row.
- In the raw text of this page, each `|` of the source is written `\|`. A plain `|` would end the table cell. A Markdown viewer shows `|`.

| Line | Source | Explanation |
|---:|---|---|
| 1 | `#!/usr/bin/env bash` | Tells Linux to run this file with `bash`. The tool `env` finds `bash` in the search path of the user. |
| 2 | `# gen_s1.sh: builds the page from the session 1 folders. For session 2, add: --session s2 <folders...>` | Comment: the script builds the page from the result folders of session 1. For session 2 the caller adds `--session s2` and the folders of that session as arguments. The page is the result page of question Q1, as line 5 shows. |
| 3 | `R=/home/jhan/workspace/titan/cache-perf/crb/results` | `R`: the folder on the agent server that holds the result folders. |
| 4 | `H=$(dirname "$(realpath "$0")")` | `H`: the folder that holds this script. `realpath "$0"` gives the full path of the script, and `dirname` removes the file name from it. |
| 5 | `PYTHONDONTWRITEBYTECODE=1 python3 $H/make_q1_html.py --session s1 $R/B7-20261113T232859Z $R/B10a-20261113T235919Z $R/B10b-20261114T003359Z $R/B8-20261114T010839Z $R/B5-20261114T011723Z $R/B9-20261114T012105Z $R/B1-20261114T012315Z $R/B4-20261114T014024Z $R/B6-20261114T014825Z $R/B2-20261114T015517Z $R/B3-20261114T020808Z $R/C1-20261114T022058Z $R/C2-20261114T022500Z $R/C3-20261114T022708Z "$@" -o $H/partB-q1-result.html` | Runs the page generator `make_q1_html.py`, which lies beside this script, with `python3`. `PYTHONDONTWRITEBYTECODE=1` is set for this one command: Python then writes no compiled `.pyc` files. `--session s1` names the session `s1`. The 14 paths after it are its result folders, one per step and call of the run script [Ref2]. Seven hold the steps of question Q1, which run one thread: B1, B2, B3, B4, B6, C1 and C2. Seven hold the steps of question Q2, which run many threads: B7, B10a, B10b, B8, B5, B9 and C3. By the description of `make_q1_html.py` it reads only the header lines and `env.txt` of the Q2 folders, for the system load. `"$@"` puts all arguments of the caller at this place, for example a second `--session` group. `-o` names the output file: `partB-q1-result.html` beside the script. `$H` and `$R` stand without quotes, so a path with a space would break the command. The exit status of the script is that of `python3`. |

## References

- [Ref1] `/home/jhan/workspace/ai-proj/arm-crb/code/new-test-kernel/partBC-analysis/make_q1_html.py`: the page generator. Its description names the steps of Q1 and says what it reads from folders of other steps. Its function `main` reads the options `--session` and `-o` and opens the output file for writing.
- [Ref2] `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/logs/session1-folders.txt`: the list of the 14 result folders of session 1, with the same names as in the script. The folders lie in `/home/jhan/workspace/ai-proj/arm-crb/tests/2026-11-13-new-read-kernel/`.
