# PR 5022 nightly watch

**Short version:** `watch.py` reads the nightly systems-test results of delphi-3bda (the Intel machine) and andoria-b1a3 (the AMD machine) from Talos (the internal test-results service). It computes the normal value of every model from the nights before tron PR 5022, and it compares the nights whose tron build contains the PR. jhan asked for this watch on 2026-11-25, and it runs until jhan says stop.

## What jhan expects

- Muse Glimmer on delphi-3bda: decode rate and prefill both get faster. The PR's own test measured +4.6 % decode rate and -3.4 % time to first token (TTFT) for the nightly settings.
- Muse Glimmer on andoria-b1a3: no change. AMD has no AMX (the Intel matrix instruction set that the PR uses).
- Every other model on both machines: no change, and above all no series slower.

## Run it

```sh
python3 -B /home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-nightly-watch/watch.py
```

- It needs the company network (`http://talos:5000/sessions`) and the GitHub tool `gh`.
- The run takes a few seconds. It is safe to run at any time and any number of times.
- `--offline` analyses the saved copy. `--backtest` prints the false-alarm rate of the band rule.

## What each run of the schedule does

1. Run the command above and read the output.
2. The last line says `CHANGED=0` or `CHANGED=1`. With `CHANGED=0` and `ALERTS=0`, stop. Nothing is new.
3. With `CHANGED=1`: publish `report.html` again with the Artifact tool. Use the same file path, so the link stays the same.
4. Tell jhan in plain English what the `EVENTS` lines and the Glimmer lines say. Name the night, the tron build and the number of nights behind each verdict. A verdict from one night is preliminary.
   Put the `GLIMMER TABLE` of the output into the report as it is. jhan asked for this table on 2026-11-25: the baseline columns, then two columns for each night with the PR (Day 1 decode, Day 1 TTFT, Day 2 ...), each cell with the number and its change in percent from the normal.
   jhan also asked on 2026-11-25 to report the new table in the chat at every update, and to insert it in the page as the first section, named by the date. `watch.py` does the page part: it saves the table once per nightly date in `data/table-log.json` and prints a `TABLE ADDED` or `TABLE UPDATED` event. The page then shows the newest date as its first section, the earlier dates folded below it, and a table of contents above them.
5. Report every `SLOWER`, `NO GAIN`, `TEST FAILED` and `ERROR` line. Do not explain a change by PR 5022 without evidence: the nightly build holds every commit of that day, and the page lists them.
6. Send one push notification with the headline.
7. On a `NIGHT FINISHED` event: read the two newest reports of the talos bot in Slack channel #ci-cd-notifications (id C06S8PNDBQA, `limit` 4). Check that the Glimmer decode rate and TTFT there equal the Talos values. Quote the pass or fail state and the slowest-user rate, which Talos does not give.
8. Done on 2026-11-25: jhan was reminded to turn off the hourly PR 5022 review watch (cloud task `trig_01GVEL2kVKy4FwLGZXcG7At9`), which has no use after the merge. Do not repeat the reminder.

## Schedule

The schedule lives in the Claude Code session that created it (session cron jobs). It ends when that session ends, and each job expires after 30 days (2026-12-25 for the jobs of 2026-11-25). To start it again in a new session, create the same four jobs.

- The cron tool reads its expressions in the machine's local time, which is Pacific time (PST, UTC-8), not UTC.
- The tool runs a daily job 30 minutes after the time in its expression. The table gives the expression and the real run time.

| Cron expression | Runs at (PST) | Same time in UTC | Why |
|---|---|---|---|
| `10 21 * * *` | 21:40 | 05:40 | The performance tests of both machines are done by about 05:15 UTC. |
| `7 0 * * *` | 00:37 | 08:37 | Second look, for a nightly that started late. |
| `43 3 * * *` | 04:13 | 12:13 | Both sessions have ended by about 11:45 UTC. Final values and the Slack cross-check. |
| `43 6 * * *` | 07:13 | 15:13 | Last look, for a nightly that ended late. |

The prompt of each job: run `watch.py`, then follow the section "What each run of the schedule does" above.

To stop the watch: delete the session cron jobs (CronList, CronDelete) and delete the memory note `pr5022-nightly-watch`.

## Files

- `watch.py`: collection, baseline, comparison, text summary.
- `report.py`: builds `report.html`.
- `report.html`: the page. Published as a private artifact (link in the memory note).
- `status.json`: the full result of the last run.
- `log.txt`: one line per run.
- `data/nights.json`: every nightly session read so far. `data/pr.json`, `data/contains.json`, `data/commits.json`: saved GitHub answers. `data/state.json`: what the last run saw, used to find what is new. `data/table-log.json`: the Glimmer table of every date, shown on the page as dated sections. Do not delete it: an old table cannot be rebuilt once the baseline has moved.

## Rules of the comparison

- Source: scheduled nightly sessions (runner `system-ci-runner`, name `System CI ...`) since 2026-10-01. Reruns started by hand are left out.
- A running nightly session is read too, since 2026-11-26. Until its last phase ends, Talos names it `Performance Benchmarks (date)` and gives it no `dut` field (the machine name). `watch.py` reads the machine from the session log (`/sessions/<uuid>/logs`, the line `Connecting to <machine>.positron.internal`) and saves it in `data/duts.json`. The script takes such a session only in its first 24 hours.
- Three older nights never finished and kept the name `Performance Benchmarks`: 2026-11-01 on both machines and 2026-11-08 on andoria-b1a3. They are not in the stored history. All three are older than the baseline nights.
- A night counts as "with PR 5022" when the merge commit is an ancestor of the commit of its tron build.
- Baseline of a series: the newest nights before the PR with the same platformd version, the same FPGA image and the same test settings, back to the last level shift (two nights in a row more than 3 spreads from the median).
- Normal: the median of the baseline nights. Spread: 1.4826 x the median distance from the median.
- Band: normal plus or minus the largest of 4 spreads, 0.75 % (decode rate) or 1 % (TTFT), and 3 ms (TTFT).
- Backtest on 2026-11-25: 5 of 590 baseline nights fell outside a band built from the other nights (0.8 %).

## Facts found on 2026-11-25

- Talos has a REST interface at `http://talos:5000`. `GET /sessions` returns every session (7.5 MB). `GET /sessions/<uuid>` returns one. `GET /sessions/<uuid>/metrics` returns every sample of a session (17 MB), with the rate of each user and round.
- A session on delphi-3bda starts at about 03:34 UTC. Its last performance test (Muse Glimmer) posts at about 05:11 UTC, its last accuracy test at about 08:23 UTC, and the session ends at about 11:26 UTC.
- A failed performance test stores a string that starts with `FAILED (` in place of the numbers.
- The nightly package build (preset `deb`) sets `TRON_AMX_DISPATCH` to `ON` (tron `CMakePresets.json` line 68).

## Facts found on 2026-11-26

- Talos fills the session summary while the session runs. At 05:40 UTC all 12 performance results of both machines were present.
- A running session has the name `Performance Benchmarks (date)` and no `dut`, `hostname`, `models` or soak fields. Its `ended` field holds the end of the first phase (the functional tests), not the end of the session.
- The session keeps its uuid when it gets the final name `System CI (date)`. The uuid is of version 1, and its time stamp equals the session start for the finished sessions of 2026-11-25.
- The first nightly with PR 5022 is the one of 2026-11-26, tron build `v2026.11.26-d78690db`. The build holds 6 commits that the build of 2026-11-25 did not hold.
- On 2026-10-24 the Muse Glimmer decode rate (77.97 TPS) and the llama-3.1-8b decode rate at 32 users (27.89 TPS) on andoria-b1a3 were both low for one night. The same two series were low on 2026-11-26 (78.49 TPS and 29.32 TPS).
