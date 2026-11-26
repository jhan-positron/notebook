---
name: pr5022-nightly-watch
description: "Daily watch of the nightly systems-test numbers after tron PR 5022 (asked by jhan 2026-11-25, runs until jhan says stop): folder, command, artifact link, session cron jobs to re-create, what to report"
metadata:
  node_type: memory
  type: project
  originSessionId: 8c78edcb-78c6-4643-820a-9f4db3e627b1
  modified: 2026-11-26T05:44:11.684Z
---

On 2026-11-25 jhan put PR 5022 in the merge queue and asked for a monitor "for coming days (until I tell you to stop)". jhan's expectations: Muse Glimmer on delphi-3bda (Intel) gets faster in decode and prefill; Muse Glimmer on andoria-b1a3 (AMD) does not change; no other model changes, "at least there should be no negative impact".

Everything is in `/home/jhan/workspace/intel-AMX/muse-glimmer/pr5022-nightly-watch/`. README.md there holds the run steps, the band rule and the schedule. Command: `python3 -B .../pr5022-nightly-watch/watch.py`. It prints `CHANGED=0|1 ALERTS=n` on its last line and writes `report.html`.

The page is the private artifact https://claude.ai/artifact/Jqy5HcQnLLWdrKEe5Xxfu8 (title "PR 5022 Nightly Watch"). From a new session, publish with `url` set to that link so the link stays the same.

Baseline on 2026-11-25 (before the merge): Glimmer on delphi-3bda 77.34 TPS per user and 3726 ms TTFT (10 nights, 11-11 to 11-25); on andoria-b1a3 79.75 TPS and 3738 ms (14 and 15 nights). The PR's own test for the nightly settings measured +4.6 % decode and -3.4 % TTFT on delphi-3bda.

**Why:** jhan checks the nightly in Slack by hand and wants the change after the merge judged against a computed normal, for Glimmer and for every other model.

jhan, 2026-11-25, on the baseline table of my first report (one row per machine: decode normal, decode band, TTFT normal, TTFT band, baseline nights, expected with the PR): "This table is great, after PR effect starts in CI, add new columns: day1 decode number(change % from normal), day1 TTFT number (change % from normal), day2, day3, etc." `watch.py` prints this table as Markdown (`GLIMMER TABLE`), and the page shows it under the Short version.

jhan, 2026-11-25, second request: "Report the new table here once there are update, and insert to the first section (named by date)" of the artifact, add the baseline table as the first section now, and "add Table of Content at top". Done the same day: the page has the Short version, then a table of contents, then one section per nightly date (newest first, earlier dates folded). The order Short version before the contents was my choice, to keep jhan's rule that a page starts with a Short version.

PR 5022 merged on 2026-11-25 18:33 UTC as commit 67a380d9c0. The first nightly with it is the one of 2026-11-26 (tron build v2026.11.26-d78690db).

Day 1 (2026-11-26, reported to jhan at the 21:40 PST check of 2026-11-25): Glimmer on delphi-3bda 82.71 TPS (+6.9 %) and 3687 ms TTFT (-1.0 %, at the edge of the band, less than the PR's own -3.4 %). Glimmer on andoria-b1a3 78.49 TPS (-1.6 %, outside the band, not expected) and 3735 ms. Two other series flagged slower by small margins: gpt-oss-120b tp4 decode on delphi-3bda (-0.99 %, band 0.90 %) and llama-3.1-8b tp2 at 32 users decode on andoria-b1a3 (-1.21 %). I told jhan that the cause of the AMD drop is not known, that the same two AMD series were low together for one night on 2026-10-24, and that Day 2 decides. Follow these three series in the next reports.

`watch.py` was changed on 2026-11-26 to read a running session (see [[talos-rest-api]]); before that it saw a night only after its end.

**How to apply:**
- Every report to jhan carries the `GLIMMER TABLE` from the script output, unchanged.
- The dated sections come from `data/table-log.json`, which `watch.py` fills. Republish the page after every `TABLE ADDED` or `TABLE UPDATED` event.
- The schedule is four session cron jobs (they die with the session that made them, and expire on 2026-12-25). If a new session finds no such jobs in CronList and jhan has not said stop, tell jhan and re-create them from the README table. The cron tool uses Pacific time and runs a daily job 30 minutes after its expression.
- When jhan says stop: CronDelete the jobs and delete this memory.
- The schedule was my choice (a session schedule plus a local script, because the data source [[talos-rest-api]] is on the company network and a cloud task cannot reach it). jhan has not confirmed it. For the PR review watch jhan wanted a watch that survives a closed session ([[pr5022-cloud-watch]]).
- I reminded jhan on 2026-11-25 (after the merge) to turn off the cloud task of [[pr5022-cloud-watch]]. Do not repeat it. When jhan confirms the task is off, delete that memory.
