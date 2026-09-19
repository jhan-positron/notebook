# Handoff: how to check when the nightly System CI starts and stops on delphi-3bda

> Written by Claude Code (Linux CLI, machine claude-box) on 2026-09-05.
> Every fact below was read from the live machine or the source repo on
> 2026-09-05 00:17 UTC; file:line references point at those sources.
> Updated 2026-09-14 17:10 UTC. The same sources were re-read. The run
> durations now cover 14 runs. A new section "Change planned on 2026-09-14"
> records Rhys's plan to add gemma-4-31b to the nightly.

## Short version

The nightly CI is a GitHub Actions workflow in the repo positron-ai/systems_test.
It runs on the host system-ci-runner and drives delphi-3bda (the "DUT", device
under test) over ssh from about 03:30 UTC for about 7 h 50 min (est. 9 h 40 min
once gemma-4-31b is added, planned 2026-09-14). While it holds
the machine it keeps a lease file on delphi-3bda; that lease file is the only
reliable "CI is running right now" signal, so check it instead of the clock.

## Words used here

- DUT: device under test; here always delphi-3bda.
- System CI / nightly: the workflow `system_ci_granite_rapids_72_rinzler_OCI.yaml`
  in positron-ai/systems_test (functional tests, perf, MMLU Pro, 3 h soak).
- rinzler: the production inference server (systemd units rinzler@0..3).
- platformd: the local control service on delphi-3bda (port 8080) that starts
  and stops the rinzler engines.
- lease: the file `/run/lock/systems-test-ci.lease` on delphi-3bda, written by
  the CI client while it owns the DUT.
- ci-runner-stop: a systemd timer on delphi-3bda that fires at 02:45 UTC and
  brings inference up before the nightly.
- daytime runner: a GitHub Actions runner service installed on delphi-3bda
  itself (`actions.runner.positron-ai.delphi-3bda-0.service`). It is disabled.
  The nightly does not use it. The nightly's runner is on system-ci-runner.
- campaign: a long batch of our own AMX (Intel Advanced Matrix Extensions, the
  CPU matrix instructions our tests exercise) test runs on the DUT, launched by
  scripts under `~/workspace/intel-AMX/exec/`.
- tron: the inference program under test. runtron: its command-line tool. Our
  campaign builds are named `runtron.<variant>`, for example `runtron.canon`.
- flock: the Linux file-lock tool. Our campaigns take one lock on
  `/var/tmp/jhan/3bda-campaign.lock`, so only one campaign runs per machine.
- blackout window: a time range listed in `/var/tmp/jhan/3bda-blackout`, used
  for days promised to another person. No campaign may start inside it.
- gemma-4-31b: a Gemma 4 language model with 31 billion parameters, the model
  Rhys (owner of systems_test) plans to add to the nightly (2026-09-14).
- gh: the GitHub command-line tool. PR: pull request.
- TTL: time to live. The lease expires 15 min after its last heartbeat.
- PDT: Pacific Daylight Time, UTC-7.

## The nightly timeline (UTC)

```
02:45  ci-runner-stop timer  -> ci-runner.sh stop: inference up (rinzler engines started)
03:30  GitHub cron '30 3 1-31/1 * *' (every day) -> workflow queued (real start is often 03:38, once 04:57)
03:3x  CI writes the lease, installs the tron deb via apt, runs the suite
~11:25 suite ends, lease cleared, run shows "completed" on GitHub
       (est. about 13:15 UTC once gemma-4-31b is added. See the section below.)
```

Durations of the last 14 runs (`gh run list`, 2026-09-01 to 2026-09-14): 6 h 39 min
to 7 h 58 min, median 7 h 49 min (the middle value of the 14). Thirteen runs
started between 03:37 and 03:41 UTC. Twelve of them ended between 11:15 and
11:35 UTC. One ended early, at 10:18 UTC on 2026-09-09 (a failed run). Nine runs were `success` and
five `failure`. The four latest runs (2026-09-11 to 2026-09-14) failed. The four
failed runs that ran to the end lasted 7 h 36 min to 7 h 52 min, close to the
range of the successful runs (7 h 40 min to 7 h 58 min).

Facts behind the timeline:

- Cron is `30 3 1-31/1 * *` [systems_test .github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml:4].
  GitHub delays scheduled runs; on 2026-09-03 the run started at 04:57 UTC. So
  the clock is advisory only.
- The job timeout is 570 min (9.5 h) as of 2026-09-14 [same file:8]. The
  comment on that line says the value was chosen so the job ends before the
  daytime runner "reclaims delphi at 14:00 UTC". That reclaim is the 14:00 UTC
  start timer described below. It is installed but disabled. Rhys plans to
  raise this timeout for gemma-4-31b.
- The lease is written first and cleared in an EXIT trap, so it exists for the
  whole suite [same file:34-44]. The lease client is
  `scripts/manage_dut_lease.py`; TTL 15 min, heartbeat every 60 s
  [manage_dut_lease.py:14-15].
- The stop timer is `OnCalendar=*-*-* 02:45:00 UTC`
  [/etc/systemd/system/ci-runner-stop@.timer on delphi-3bda]. Its service runs
  `/opt/positron/ci/ci-runner.sh stop`, which stops the daytime GitHub runner
  (if any), removes leftover hugepage files, and POSTs `inference/up` to
  platformd.
- The 14:00 UTC start timer is installed but disabled. (Corrected 2026-09-14.
  The 2026-09-05 text said no start timer exists.) The unit
  `/etc/systemd/system/ci-runner-start@.timer` (`OnCalendar=*-*-* 14:00:00 UTC`,
  and `Persistent=true`: a firing missed while the machine was off runs at the
  next boot) is in the same directory as the stop timer. Its instance
  `ci-runner-start@delphi-3bda.timer` is disabled and inactive, with no link in
  `timers.target.wants`. That is why `systemctl list-timers --all` shows only
  the 02:45 stop timer. If the start timer ever fires, `ci-runner.sh start`
  POSTs `inference/down`, runs `pkill -f runtron` and `pkill -f rinzler`,
  clears hugepages and starts the daytime runner [ci-runner.sh:120,151-152,171].
  The daytime runner service itself is disabled and inactive.

## Change planned on 2026-09-14: gemma-4-31b joins the suite

Rhys wrote to jhan on 2026-09-14 that gemma-4-31b will be added to the nightly
suite. He expects it to add about 1 h 50 min to the run. He will raise the job
timeout to fit.

State of the repo as of 2026-09-14 17:10 UTC:

- Nothing is merged. `origin/main` (commit 3c0a77a) still has
  `timeout-minutes: 570`. No file on `origin/main` mentions gemma-4
  (`git grep -i gemma-4 origin/main` prints nothing). There is no open PR for it.
- The current timeout is already too short for the projected run. Median
  7 h 49 min + 1 h 50 min = 579 min. Longest recent run 7 h 58 min + 1 h 50 min
  = 588 min. Both exceed 570 min. If gemma-4-31b is merged before the timeout is
  raised, GitHub cancels the job at 570 min (about 13:08 UTC for a 03:38 start).
- gemma-4 model rows exist only on the unmerged `ares-*` branches by John
  Wiegley for MMLU work (MMLU: a question-answering accuracy benchmark; "ares"
  is a branch-name prefix the repo does not explain):
  `ares-gemma4-metal-mmlu` (2026-07-03, gemma-4-12b), `ares-test` (2026-07-11)
  and `ares-gpt-oss-mmlu-selection` (2026-07-13). The last two carry
  `gemma-4-31b-it-tp4` and `gemma-4-31b-it-host-bf16` rows in
  `scripts/mmlu_pro.py`. None of them changes the System CI suite.
- Files to watch for the change: `FUNCTIONAL_TEST_MODELS` and `SOAK_MODELS` in
  `scripts/system_ci.py`, the model rows in `scripts/perf.py` and
  `scripts/mmlu_pro.py`, `thresholds/system_ci_perf.yaml`,
  `thresholds/system_ci_mmlu_pro.yaml`, and `timeout-minutes` in the workflow.

What changes for our work once the change is merged:

- The suite end moves from about 11:25 UTC to about 13:15 UTC (est.: 03:38
  start + 7 h 49 min median + 1 h 50 min). That is 06:15 PDT, before the
  working day.
- Late GitHub starts push the end later. In the 14-run window one start was
  04:57 UTC (2026-09-03). Just before that window, 2026-08-27 started at
  05:17 UTC and 2026-08-28 at 06:07 UTC (`gh run list --limit 20`). With
  gemma-4-31b those three would end about 14:35, 14:55 and 15:45 UTC (est.,
  same method).
- The start (cron 03:30 UTC), the 02:45 UTC prep step and our 02:30 UTC
  campaign deadline do not move, as long as Rhys keeps the cron minute.
  Confirm that with Rhys if the change also alters the schedule.
- The raised timeout may move the job deadline past 14:00 UTC. Cron 03:30 UTC +
  570 min = 13:00 UTC today. Any timeout of 630 min or more reaches 14:00 UTC. The 14:00 UTC
  start timer (installed, disabled, see above) must stay disabled. If it fires,
  `ci-runner.sh start` kills every runtron and rinzler process and brings
  inference down. That would abort a nightly still running, and any run of ours.
- Check 1 (the lease) does not change. The CI writes the lease at the start and
  clears it at the end, whatever the run length [workflow yaml:34-44]. So the
  guard functions `ci_lease_busy`, `campaign_guard_acquire` and `ci_took_dut`
  in lib-guard.sh (see Check 1) need no edit.
- Wait timeouts in our scripts must cover the longer run.
  - `wait_for_ci_release` and `wait_for_dut_free` default to 6 h (21600 s)
    [lib-guard.sh:216,227]. That default is already shorter than today's
    7 h 49 min run.
  - Pass at least 50400 s (14 h). A 12 h wait started at 03:38 UTC gives up at
    15:38 UTC, before the 15:45 UTC late-start case. A 14 h wait lasts until
    17:38 UTC. `perf-model-20260903/run-perf-model.sh:76` already passes 50400 s.
  - Four scripts under `~/workspace/intel-AMX/exec/` pass 28800 s (8 h):
    `p2-verify-after-ci.sh:16`, `p3-q-scalar-gate.sh:34`,
    `p3b-mirror-accounting.sh:25`, `p3c-prefix-abort-message.sh:20`. After the
    change, a 03:38 UTC launch of any of them gives up at 11:38 UTC, about
    1 h 40 min before the lease clears.
  - `dd/dd-campaign.sh:62` and `dd/dd-campaign-v3.sh:67` pass 36000 s (10 h).
    A 03:38 UTC launch gives up at 13:38 UTC, about 20 min after the estimated
    end. A CI start more than about 20 min late makes them give up.
  - `p2-perf-round-resume.sh:41-48` and `ctxfill-20260901/run-ctxfill.sh:24-26`
    pass 21600 s (6 h) but first wait for the clock to reach 09:30 or 09:15 UTC.
    Their effective deadline is 15:30 or 15:15 UTC. That covers a 03:38 start.
  - `g1-20260908/g1-campaign.sh:85-88` holds new runs during a 01:30 to 11:00
    UTC clock window (its comment: "nightly ends ~11:25") and also waits on the
    lease. It still waits for the lease after the change. The hold protects
    against a lease gap (the lease file absent for one poll while the CI is
    still running). After the change that protection is missing between 11:00
    and about 13:15 UTC. Extend the window to 13:30 UTC before reusing it.
- A hung run holds the lease at most until the new timeout plus about 15 min.
  At `timeout-minutes` the GitHub runner sends SIGINT (the interrupt signal),
  then SIGTERM (the terminate signal), then kills the process tree. bash runs the EXIT trap on SIGTERM, and the trap runs
  `manage_dut_lease.py clear` [workflow yaml:39-44]. If the clear does not
  finish, the heartbeat stops and the lease expires after its 15 min TTL.
  `ci_lease_busy` treats an expired lease as not busy. Rhys has not yet named
  the new timeout value.

## Check 1: is CI running right now? (authoritative)

Run on delphi-3bda:

```bash
cat /run/lock/systems-test-ci.lease
```

- File missing: CI is not holding the DUT.
- File present: JSON like
  `{"state":"busy","owner":"system_ci","lease_id":"<run>-<attempt>","updated_at_epoch":...,"expires_at_epoch":...,"github_run_id":"...","github_run_attempt":"..."}`.
  CI holds the DUT only if `state` is `busy` AND the current epoch is below
  `expires_at_epoch`. An expired lease means the CI client died without
  cleanup; treat it as not busy.

The same rule is already coded in `~/workspace/intel-AMX/exec/lib-guard.sh`:

```bash
source ~/workspace/intel-AMX/exec/lib-guard.sh
ci_lease_busy && echo "CI holds the DUT" || echo "CI not holding"
wait_for_ci_release 50400   # poll every 5 min, give up after 14 h (the 6 h default is shorter than the nightly)
```

`campaign_guard_acquire` in the same file checks, in order: the lease, whether
another person is actively using the machine (`other_user_active`), a blackout
window (`/var/tmp/jhan/3bda-blackout`), a host-wide flock, running runtron
processes, and active rinzler serving [exec/lib-guard.sh:145-178].
`ci_took_dut` is the between-runs re-check. It covers the lease, other people
and blackout windows [exec/lib-guard.sh:210].

## Check 2: did the nightly start / finish? (GitHub side)

From any machine with `gh` logged in as jhan-positron:

```bash
# last runs: status, conclusion, start and end time
gh run list -R positron-ai/systems_test \
  --workflow system_ci_granite_rapids_72_rinzler_OCI.yaml --limit 5 \
  --json databaseId,status,conclusion,createdAt,updatedAt,event

# one run: job duration and link
gh run view <databaseId> -R positron-ai/systems_test
```

`status` is `in_progress` while the suite runs and `completed` afterwards;
`createdAt` is the real start (not the cron minute) and `updatedAt` the end.
The `github_run_id` inside the lease file matches `databaseId` here, so the two
checks can be tied together.

## Check 3: did the 02:45 UTC prep step run?

On delphi-3bda (needs sudo for the system journal; `sudo -n` works for jhan):

```bash
systemctl list-timers --all --no-pager | grep ci-runner-stop
sudo -n journalctl -u ci-runner-stop@delphi-3bda.service --since -30h --no-pager -q
```

A healthy night ends with the lines
`Bringing inference up for nightly...` and
`Inference up: success. Ready for nightly use.` (seen for 2026-09-04 02:45:05).
Without `sudo` the command above prints nothing at all. The `-q` flag hides
the permission notice. Without `-q` it prints `Hint: You are currently not
seeing messages from other users and the system` and `-- No entries --`. Either
output is a permission effect (jhan is in group `sudo` but not in `adm` or
`systemd-journal`), not evidence that the timer did not fire.

## Check 4: is inference (rinzler) up or down?

```bash
for i in 0 1 2 3; do echo "rinzler@$i $(systemctl is-active rinzler@$i)"; done
sudo -n /opt/positron/ci/ci-runner.sh status     # runner state + platformd inference status JSON
curl -s --max-time 5 http://localhost:8080/api/inference/status | grep -o '"activity":"[^"]*"'
```

During the nightly the CI itself starts and stops rinzler through a config
patch and polling, so engines being up or down does not by itself say whether
CI is running. Use the lease for that.

## Rules for our own work on delphi-3bda

- Never launch a campaign while the lease says busy; source lib-guard.sh and
  use `campaign_guard_acquire` [exec/lib-guard.sh:145-178].
- Long campaigns must finish before about 02:30 UTC: the 02:45 prep step brings
  rinzler up and a following campaign cell would collide with it
  (deadline logic exists in `exec/more-testing-r1.sh`).
- Re-check `ci_took_dut` between long runs; the lease says "holding now", not
  "starting in five minutes".
- When a script waits for the lease to clear, pass at least 50400 s (14 h) to
  `wait_for_ci_release` or `wait_for_dut_free`. The 6 h default is shorter than
  the nightly, and a late GitHub start has delayed the run by as much as about
  2.5 h (06:07 UTC on 2026-08-28) (added 2026-09-14).
- Do only light work on the machine while the lease is busy (jhan's standing
  rule for this machine).

## Sources

- delphi-3bda: `/etc/systemd/system/ci-runner-stop@.timer`, `ci-runner-stop@.service`,
  `/opt/positron/ci/ci-runner.sh`, `systemctl list-timers --all`, journal of
  the stop service for 2026-09-03 and 2026-09-04.
- positron-ai/systems_test at 470aca1 (clone `~/workspace/ai-runs/systems_test`):
  `.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml`,
  `scripts/manage_dut_lease.py`.
- `gh run list` output for runs 33354547390 .. 33833914529 (read 2026-09-05)
  and 32927747757 .. 34803449646 (20 runs, read 2026-09-14).
- Rhys's message to jhan on 2026-09-14 (gemma-4-31b, about 1 h 50 min more,
  timeout to be raised).
- systems_test `origin/main` commit 3c0a77a, `git branch -r` and `git grep`
  over all `origin/*` refs on 2026-09-14.
- delphi-3bda on 2026-09-14 17:07 UTC: lease absent, `systemctl list-unit-files
  'ci-runner*'`, `/etc/systemd/system/ci-runner-start@.timer`,
  `actions.runner.positron-ai.delphi-3bda-0.service` disabled and inactive,
  stop-service journal for 2026-09-13 and 2026-09-14 healthy.
- `~/workspace/intel-AMX/exec/*.sh` and subdirectories: `grep` for
  `wait_for_ci_release`, `wait_for_dut_free` and clock windows (2026-09-14).
- `~/workspace/intel-AMX/exec/lib-guard.sh` (lease rule, guard functions).
