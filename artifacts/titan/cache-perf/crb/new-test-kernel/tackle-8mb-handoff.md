# Handoff: find out why the new read kernel gains so little at 8 MiB

Written 2026-11-15 03:50 UTC by the agent that built the runner and ran session 1.

## Short version

- **The goal.** Find out why the new read kernel raises the read throughput at 8 MiB far less than at the other sizes on the CRB machine. The original run showed a gain of 0.94 % at 8 MiB, and the gain at 1 MiB is 27 % [Ref1] [Ref5].
- **The work rule.** The goal is not reached yet. Keep running the loop "analyse, choose the next test, run it, analyse" until the goal is reached. Do not end your turn to report progress, to ask a question, or to wait for a review.
- **The next action.** Run session 2 on CRB, not before 04:20:18 UTC on 2026-11-15. The command is in "Step 1".

## Words used here

| Term | Meaning |
|---|---|
| CRB | The Arm Phoenix Reference Server, 128 cores. Login `ssh jhan@192.168.2.45`. |
| old read, `oldread` | The read loop of the original benchmark `bench/bandwidth.c`. |
| new read, `read` | The new C read kernel (a load-only loop). |
| `asmread` | The same load-only loop written in assembly. |
| gain | (new read rate − old read rate) / old read rate, in percent, at one buffer size. |
| `bwx8` | The test runner built for this design. Source `bwx8.c` in folder X. |
| X | `/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx8-2026-11-14/` (runner, schedules, run scripts, decisions file). |
| A | `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis/` (analysis and report scripts). |
| N | `/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/` (design, logs, this file). |
| R | `/home/jhan/workspace/titan/cache-perf/crb/results/` (result folders copied from CRB). |
| the design | `N/tackle-8mb.md`. It defines Stage 0 to Stage 5, the predictions P1 to P3, and the repeatability rule [Ref1]. |
| the rules file | `N/handoff.md`. It is the earlier handoff. Its section "The machine, and the rules for using it" holds the CRB rules [Ref2]. Do not overwrite it. |
| step | One batch of processes of `run_bwx8.sh`: `B6W`, `S2`, `S4`, `P3G`, `P3`, `S3G`, `S3`, `BIN`, `CS`, `CM`, `C4` [Ref3]. |
| session | One visit set on CRB. Session 2 repeats session 1 at least 3 hours later, with the CPU order reversed. |
| confirmed | A result that has the same sign in both sessions and passes the repeatability rule of the design [Ref1]. |
| block | A time window that Jeremy Conner reserves on CRB in the Slack channel #phoenix-crb. |
| marker file | `/tmp/positron-perf.RUNNING` on CRB. If it exists, another measurement runs. |
| low level, high level | The two rates between which a load-only kernel switches at 8 MiB: about 67.2 to 69.0 GB/s and about 71.1 to 71.6 GB/s [Ref5]. |

## The goal, and when it is reached

The question: **why does the new kernel improve the read throughput at 8 MiB much less than at other sizes?**

The goal is reached only when all three points hold:

1. A named mechanism explains the small gain at 8 MiB.
2. A controlled test changed that mechanism, and the gain changed as predicted. The change appeared on both CPUs (2 and 41) and in both sessions.
3. The report states which share of the gap the test explains, and what stays unexplained.

This is the "complete answer" of the design (section "What counts as progress, and what counts as an answer") [Ref1].

These results are **not** the goal:

- A threshold that labels the data.
- A hypothesis that was not rejected.
- A result from one session only.
- A description of the low and high levels without their cause.

## How to work: the loop

```
analyse the data you have
        |
        v
choose the test that separates the open hypotheses best
        |
        v
record its schedule and decision rule in DECISIONS-bwx8.md
        |
        v
build and test locally -> run on CRB (session 1, then session 2)
        |
        v
fetch, analyse, append to the progress file
        |
        v
goal reached?  -- no --> back to the top
        |
       yes
        v
final report and result handoff
```

Rules of the loop:

- **Do not end your turn while the goal is open.** A finished stage is not a reason to stop. A progress summary is not a reason to stop. Write progress to `N/tackle-8mb-progress.md` and continue.
- **Decide things yourself.** Examples: a threshold where the design is silent, the reading of a rule, the order of steps, which counter events to add. Pick one, write one line in `X/DECISIONS-bwx8.md`, and proceed. The user called questions of this kind "over cautious" on 2026-11-14.
- **The user has authorized CRB logins, builds and runs for this investigation** ("Go ahead to test CRB", 2026-11-14). You do not need a new approval for a further step or a new test on CRB, as long as it obeys the machine rules below.
- **Waiting is not stopping.** During a block, during the 3 hour gap before a session 2, or while the marker file exists: wait with a background sleep and do local work (analysis, the next schedule, code, tests). A foreground `sleep` is blocked in this harness.
- **A failed run is a task, not a stop.** Find the cause, fix it, run again. Keep the failed result folder.
- **A new test may leave the design.** The design's Stage 5 table is a starting list, not a limit. If the data points to a test that the design does not list, design it, record it, and run it.
- **New code needs no human review.** Test it locally (the existing tests must still pass, and new behaviour needs a test that can fail). Check the listings of changed kernels with `check_listing8.py`. Then use it.

### When the work ends

The work ends in one of two ways only:

1. **The goal is reached.** Deliver the report of section "Reporting".
2. **Every test that needs no root is done, and the puzzle is still open.** The remaining tests need root (physical page addresses, mesh counters, the design's Part D). Root stays forbidden. Before you end this way, exhaust the list in "Step 3" and every further test you can design without root. Then report "Insufficient data", name each root measurement, and say what it would decide.

Nothing else ends the work. In particular:

| Event | What to do (do not end your turn) |
|---|---|
| The Slack channel cannot be read | Do not log in. Do local work. Try again every 10 minutes. Load the Slack tool again with the tool search if it is missing. |
| `ssh` asks for a password or fails | Do not type a password. Do local work, and try again every 30 minutes. Write the failure in the progress file. All analysis of existing data, and the code and schedules of the next tests, continue meanwhile. End your turn only if no local work is left and the login has failed for 3 hours. |
| A block is announced, or the marker file exists | Wait with a background sleep. Do local work. |
| An acceptance check or a gate of the design fails | Find the cause. Fix the runner, the schedule or the check, record the fix, and run again. If the branch cannot work, record why and take the next test. |
| A stage ends without an explanation | Take the next test of the loop. |
| An automatic message says the user has not heard from you | Answer in one line and continue. It is not a request to stop. |
| You are uncertain about a reading, a threshold or a method | Decide, record one line in `X/DECISIONS-bwx8.md`, continue. |

## Instructions in older files that no longer apply

The older files were written for a more careful mode of work. Several of their instructions ask for a human review or a confirmation, and they caused stops. **This handoff has priority over them.** The user asked for this on 2026-11-15.

| Older instruction | Where | What applies now |
|---|---|---|
| "If you doubt it, ask the user once before the first login." | rules file, line 30 [Ref2] | Do not ask. The logins are authorized. |
| "Ask the user who reviews `bwx` before you run Part B." A second agent reviews code before use on the machine. | rules file, line 34 [Ref2] | No human review and no question. Your own tests and a listing check are enough. A review by a second agent is optional, and only for a change to a measured loop. It must not block a run for more than one round. |
| "Report what is still open ... and let the user decide." | rules file, line 31 [Ref2] | Do not report in the middle. Continue with the tests that need no root. |
| "If you cannot read Slack, do not log in. Tell the user." | rules file, line 57 [Ref2] | Do not log in, but do not stop: see the table above. |
| "Open decision for the owner" (balance of step `CM`) | decisions file, line 192 [Ref4] | You are the owner. Decide and record. |
| "Do not launch every branch automatically." Stage 3 and Stage 5 wait for a trigger. | design, lines 230 and 313 [Ref1] | You choose the branch from the data and launch it yourself. A missing trigger is a reason to pick another test, not to wait for a person. |
| "The initial fixed batch can end without an explanation. That is a valid outcome." | design, line 358 [Ref1] | Valid for the batch, not for this task. Continue the loop. |
| "Stop a branch if its acceptance fails." | design, line 355 [Ref1] | Stop that branch's data collection, repair it or replace it, and continue the investigation. |
| Coding rule "If uncertain, ask rather than guess", and "Checkpoint after every significant step" | the user's general instructions | For this task: decide and record instead of asking. A checkpoint is an entry in the progress file, not a message that ends your turn. |
| The long review round before the first run (31 defects fixed) | history of the earlier agent | Do not repeat a full review round for each new test. Match the check to the risk: a schedule change needs its test, a new loop needs a listing check and a short acceptance run on CRB. |

What still applies from the older files, unchanged: every machine rule of the next section, the repeatability rule, the rule to record a test's decision rule before reading its rates, and the limits on what a result allows you to conclude.

## The machine rules (they stay in force in every loop round)

Read the full rules in the rules file before the first login [Ref2]. The short form:

- Use CRB only. Do not use any delphi or andoria machine.
- Before **every** login, read Slack #phoenix-crb (channel ID `C0C1R7XEVU6`, the Slack connector tool that reads a channel), the last 24 hours. Blocks are posted by Jeremy Conner or "Jeremy's Claude" at least 2 hours ahead.
- No login during an announced block. If a block starts before your run would end, set `STOP_AT` to the start of the block, or wait until the block has ended.
- `STOP_AT=none` is allowed only when no block is announced at that moment. Decide it again at every visit.
- The first command of every login checks the marker file. The scripts also check it before every process. If it exists: start nothing, log out, wait, try later. Never remove it.
- While a script runs on CRB, read the channel every 10 minutes. If a new block is announced that the run would touch: `touch ~/cache-perf/STOP` on CRB (one login with the marker check), and remove that file after the run has stopped.
- CPUs 0 to 119 only. Never CPUs 126 or 127.
- Write only under `~/cache-perf` on CRB.
- Never `sudo`. Never install a package, change a system setting, or reboot.
- No `scp`. Send and fetch files with `tar` through an `ssh` call that checks the marker file first.
- Few logins: one script per login.
- The scripts record the system load before every process (`launches.txt` in each result folder). State the load in every performance report.
- Do not change `bench/bandwidth.c`, `crb/crb-memory-hierarchy.html`, or any earlier result folder.
- Do not create files or folders directly in `~/workspace`. Work inside N, X, A and R.

## State on 2026-11-15 03:50 UTC

Done:

- The runner `bwx8`, the schedules, the run scripts, and the analysis are written and tested (local tests: 232, 235, 159 and 157 checks pass) [Ref3].
- The build on CRB is accepted. The digest (sha256) of `bwx8` on CRB is `f84be912beb05d8ac035066bbe25ac0be6de5817d79523a9dfcea96800ea0ea9`. It sits in `~/cache-perf/bwx8-20261114/` [Ref4].
- The counter check passed with 0 problems (run `bwx8-accept3-s1-20261115T012031Z`). The core counter unit is `armv8_pmuv3_0`, type 11. The tested event codes are `cpu_cycles=0x11,inst_retired=0x08,l1d_cache_refill=0x03,l2d_cache_refill=0x17` [Ref4].
- Session 1 of the steps `B6W`, `S2`, `S4` ran and is analysed: 202 processes, 738 trials, 0 rejected. It ended at 2026-11-15T01:20:18Z. The load at launch was 0.04 to 0.99 [Ref5] [Ref6].

Not done:

- Session 2 of `B6W`, `S2`, `S4`.
- Every later stage: the counters (Stage 4), the mixed sequences (Stage 3), the mechanism test (Stage 5).
- The final report and the result handoff.

Nothing runs on CRB now. No background task of the earlier agent is left.

## What session 1 shows (one session, so nothing is "confirmed" yet)

All rates are in GB/s, fourth target window, medians of 6 processes [Ref5].

| Size | Old read | New read − old read, CPU 2 | New read − old read, CPU 41 | Gain |
|---|---|---|---|---|
| 1 MiB | about 67.1 | +18.14 | +18.14 | 27.0 % on both CPUs |
| 4 MiB | about 67 | +7.65 (sets 4.85 to 7.70) | +5.47 (sets 1.70 to 8.04) | 11.4 % and 8.2 % |
| 8 MiB | 67.05 to 67.09 | +3.91 (sets 0.23 to 4.02) | +2.25 (sets 1.97 to 4.57) | 5.83 % and 3.35 % |
| 16 MiB | not listed here, see [Ref5] | −1.35 | −1.07 | −2.0 % and −1.6 % |

Observations:

- **The old read rate does not depend on the size from 1 MiB to 8 MiB.** Old read at 8 MiB minus old read at 1 MiB is −0.046 GB/s on CPU 2 and −0.024 GB/s on CPU 41. Both are inside the margin of 0.30 GB/s (prediction P1).
- **The new read rate falls with the size.** New read at 8 MiB minus new read at 1 MiB is −14.27 GB/s (CPU 2) and −15.92 GB/s (CPU 41). The assembly loop gives −14.17 and −14.77 GB/s (prediction P2). The fall of the new loop carries 100.1 to 100.3 % of the lost advantage.
- **So the small gain comes from the new loop, not from the old loop.** The old loop stays near 67 GB/s. The new loop drops from about 85 GB/s at 1 MiB to about 67 to 71 GB/s at 8 MiB.
- **At 8 MiB (and 4 MiB) the load-only loops switch between two levels inside one process.** Low is about 67.2 to 69.0 GB/s. High is about 71.1 to 71.6 GB/s. In the 60 s traces of `S4`, old read has 0 steps above 0.30 GB/s in 6 of 6 processes. `read` and `asmread` have 1 to 31 steps per process.
- **The up-steps look periodic.** They sit near 6.3, 13.2, 20.1, 27.0, 34.2 and 41.1 s after the process start, on both CPUs. That is a period of about 6.9 s (est., read from the summary lines, not yet fitted).
- The first interval of a process is slower in 16 of 16 pairs on each CPU (step `B6W`).

### Hypotheses (each one still needs its test)

| ID | Hypothesis | Measurement that confirms or rejects it |
|---|---|---|
| H1 | At 8 MiB the new loop is limited by the data supply of the cache level that holds the buffer, and the old loop is limited by its own instructions at about 67 GB/s. The two limits are close at 8 MiB, so the gain is small. | Counters per kernel and size (step `CS`): cycles, instructions, and cache refill counts at 1 MiB and 8 MiB. A finer size sweep between 1 and 16 MiB that locates where the new rate falls. The Stage 5 test with added instructions (the 4-`nop` variant) at 1 MiB and 8 MiB. |
| H2 | The original gain of 0.94 % was measured while the new loop was at the low level. | Run the original program (`bw_old`, `bw_new`, see the rules file) many times at 8 MiB and compare its new-read rates with the low and high levels. The original new-read rate was 67.71 GB/s, which lies in the low range [Ref5]. Read section "What the existing evidence supports" of the design (line 39) for the original protocol first. |
| H3 | The switch between low and high is caused by a periodic event of the host (period about 6.9 s), not by the process. | Fit the step times of all `S4` traces. Compare them against the wall clock (`launches.txt` holds the launch time) and against the process start. A match on the wall clock across processes points to the host. Then run two processes at the same time on two CPUs and check whether their steps coincide. |
| H4 | The level depends on the state of the buffer's pages or on the core, not on time. | Longer sustained runs (for example 300 s). Runs on other CPUs, including one on mesh 1 (CPUs 64 to 119). Counters split by level (step `C4`): compare the counts of low windows with those of high windows. |

The data so far supports the direction of H1 (P1 and P2). It does not name the supply limit, and it does not explain the two levels. Both are part of the goal.

## Step 1: session 2 (first action)

Not before 2026-11-15T04:20:18Z. The run takes about 50 minutes.

1. Read Slack #phoenix-crb for the last 24 hours. Decide `STOP_AT`.
2. Start the run in the background of your session:

```bash
cd /home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx8-2026-11-14
STOP_AT=none SESSION=2 SESSION1_END=2026-11-15T01:20:18Z \
BWX8_SHA256=f84be912beb05d8ac035066bbe25ac0be6de5817d79523a9dfcea96800ea0ea9 \
./visit8.sh visit8-s2-B6W-S2-S4 B6W S2 S4
```

3. Check Slack every 10 minutes while it runs. Do local work between the checks (for example the step-time fit of H3 on the session 1 traces).
4. The log is `N/visit8-s2-B6W-S2-S4.log`. Its last line gives the `ssh` status. Status 0 means done. The other values are listed at the top of `X/run_bwx8.sh`. Use `--from IDX` to continue a stopped step.
5. Fetch the result folders in one login. Their names are in the log, in the lines "result folder: ...":

```bash
/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/fetch.sh bwx8-B6W-s2-<UTC> bwx8-S2-s2-<UTC> bwx8-S4-s2-<UTC>
```

`fetch.sh` checks the marker file first and unpacks into R.

## Step 2: analyse both sessions

- Run the analysis with the host limit for context switches: `BWX8_NIVCSW_PER_S=3.0`. The reason is in the decisions file, section "CRB acceptance" [Ref4].
- `python3 A/analyze8.py summary --help` shows the arguments. The session 1 output is `A/s1-summary.txt` and `A/s1-summary.json`.
- `python3 A/report8.py --note "<text>" -o <out.html> <folders...>` builds the HTML page. The note must state the host limit of 3.0 per second and how many trials the design's limit of 0 would mark.
- Apply the shared repeatability rule of the design to decide what is confirmed [Ref1].
- Fit the step times of H3 with both sessions.

## Step 3: the test loop after session 2

Choose the order from the data. This is my proposed order, with the reason for each item:

1. **Level timing (H3), no machine time.** The traces exist. The result decides whether the next tests must control time or the host.
2. **Counters (H1, H4).** Steps `CS` and `C4` with `BWX_PMU_TYPE=11` and `BWX_EVENTS=...`, passed through `ENVV` of `visit8.sh`. `CS` needs plan files from `schedule8.py --select KERNEL@SIZE,...` (they are not in the saved `X/sched/`). Send new plan files to CRB with `tar` through `ssh`. You may add event codes. Validate each new code with a short run and `check_accept8.py` first.
3. **Original program at 8 MiB (H2).** This links the new data to the original 0.94 %.
4. **Finer size sweep (H1).** Sizes between 1 and 16 MiB. Check what `schedule8.py` supports. Extend it if needed, with a test.
5. **Stage 5 test with added instructions (H1).** The 4-`nop` variant at 1 MiB and 8 MiB. This is the controlled change that goal point 2 needs for H1.
6. **Stage 3 mixed sequences (`S3G`, then `S3`).** Run them only if the data shows that a predecessor changes the rate. Session 1 did not establish that trigger.
7. **Host-side observation without root (H3).** For example `/proc/interrupts`, `/proc/vmstat` and `/proc/<pid>/sched` read before and after a run. Reading them is allowed. Changing a setting is not.

Not scheduled: `P3G` and `P3` (the Stage 0 forecast said they cannot decide P3; see the decisions file) [Ref4].

For every new test:

- Write its conditions, process count, nominal work time and decision rule in `X/DECISIONS-bwx8.md` **before** you read its rates.
- Run it on CPUs 2 and 41, in two sessions at least 3 hours apart. Group several new steps into one session to save waiting time.
- Keep every result folder, including stopped and failed ones.

## Reporting

- Append to `N/tackle-8mb-progress.md` after each loop round: what ran, the load, what is confirmed, what is open, the next test. This file replaces progress messages to the user.
- When the work ends (section "When the work ends"), deliver:
  - the HTML report (light background, charts with direct labels, exact numbers in a table, one-line takeaway under each chart),
  - the result handoff of the design (section "Deliverables and validation") [Ref1],
  - a short chat report: "Short version" first, the load, each claim tied to a named run and metric, each hypothesis labelled as a hypothesis.
- Follow the plain-english skill in all prose.

## Known limits of this handoff

- The period of 6.9 s is read from the printed step times. It is an estimate until the fit of Step 2 is done.
- I did not verify the options of `analyze8.py summary` in this file. Read its help text.
- `schedule8.py` has a fixed size list for `S2` (32 KiB, 1, 4, 8, 16 MiB). A finer sweep needs a change.
- The step `CM` uses one row construction over its 12 cells, and its two factors are not balanced independently [Ref4]. Decide the balance yourself before you use `CM`.
- The header of `X/run_bwx8.sh` still says "Never run on CRB". That line is outdated: session 1 ran with it.

## References

- [Ref1] `N/tackle-8mb.md`: the design. Sections "Shared repeatability rule" (line 257), "Stage 5" (line 311), "What counts as progress, and what counts as an answer" (line 326), "Run budget and gates" (line 340), "Deliverables and validation" (line 368). Review notes: `N/tackle-8mb.md.review.md`, line 344 to the end.
- [Ref2] `N/handoff.md`: the CRB rules, sections "What you may do, and what needs the user" (line 28) and "The machine, and the rules for using it" (line 36).
- [Ref3] `X/DECISIONS-bwx8.md`: interfaces, step table (lines 30 to 48), plan file format, output rows, fixed readings. Scripts: `X/visit8.sh`, `X/run_bwx8.sh`, `X/schedule8.py`, `X/check_listing8.py`, `X/check_accept8.py`, `X/test_runner8.py`, `X/test_schedule8.py`, `A/test_analyze8.py`, `A/test_stage0.py`.
- [Ref4] `X/DECISIONS-bwx8.md`, sections "Changes after the review round (2026-11-14)" (line 173) and "CRB acceptance, 2026-11-15" (line 218). Build folder `X/crb-build-1/`. Acceptance runs `R/bwx8-accept-s1-20261115T002916Z`, `R/bwx8-accept2-s1-20261115T003042Z`, `R/bwx8-accept3-s1-20261115T012031Z`.
- [Ref5] Session 1 analysis: `A/s1-summary.txt`, `A/s1-summary.json`, `A/report-s1.html`. Result folders `R/bwx8-B6W-s1-20261115T003102Z`, `R/bwx8-S2-s1-20261115T003207Z`, `R/bwx8-S4-s1-20261115T010216Z`. The original 0.94 % gain (old read 67.08 GB/s, new read 67.71 GB/s at 8 MiB): `N/tackle-8mb.md`, lines 47 to 50.
- [Ref6] Logs: `N/visit8-build1.log`, `N/visit8-accept1.log`, `N/visit8-accept2.log`, `N/visit8-s1-B6W-S2-S4.log`, `N/visit8-s1-fetch.log`.
