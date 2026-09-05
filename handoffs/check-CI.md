# Handoff: how to check when the nightly System CI starts and stops on delphi-3bda

> Written by Claude Code (Linux CLI, machine claude-box) on 2026-09-05.
> Every fact below was read from the live machine or the source repo on
> 2026-09-05 00:17 UTC; file:line references point at those sources.

## Short version

The nightly CI is a GitHub Actions workflow in the repo positron-ai/systems_test.
It runs on the host system-ci-runner and drives delphi-3bda (the "DUT", device
under test) over ssh from about 03:30 UTC for about 7 h 40 min. While it holds
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

## The nightly timeline (UTC)

```
02:45  ci-runner-stop timer  -> ci-runner.sh stop: inference up (rinzler engines started)
03:30  GitHub cron '30 3 * * *' -> workflow queued (real start is often 03:38, once 04:57)
03:3x  CI writes the lease, installs the tron deb via apt, runs the suite
~11:20 suite ends, lease cleared, run shows "completed" on GitHub
```

Durations of the last five runs: all 7 h 40 min to 8 h, all `success`
(gh run list, 2026-08-31 to 2026-09-04).

Facts behind the timeline:

- Cron is `30 3 1-31/1 * *` [systems_test .github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml:4].
  GitHub delays scheduled runs; on 2026-09-03 the run started at 04:57 UTC. So
  the clock is advisory only.
- The job timeout is 570 min (9.5 h) [same file:8].
- The lease is written first and cleared in an EXIT trap, so it exists for the
  whole suite [same file:34-44]. The lease client is
  `scripts/manage_dut_lease.py`; TTL 15 min, heartbeat every 60 s
  [manage_dut_lease.py:14-15].
- The stop timer is `OnCalendar=*-*-* 02:45:00 UTC`
  [/etc/systemd/system/ci-runner-stop@.timer on delphi-3bda]. Its service runs
  `/opt/positron/ci/ci-runner.sh stop`, which stops the daytime GitHub runner
  (if any), removes leftover hugepage files, and POSTs `inference/up` to
  platformd.
- There is NO start timer on delphi-3bda. The header comment in ci-runner.sh
  mentions a 14:00 UTC "start runner" timer; `systemctl list-timers --all`
  shows only the 02:45 stop timer, and the daytime runner service
  `actions.runner.positron-ai.delphi-3bda-0.service` is disabled and inactive.
  The nightly does not use that runner: its runner is on system-ci-runner.

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
wait_for_ci_release 21600   # poll every 5 min, give up after 6 h (default)
```

`campaign_guard_acquire` in the same file checks the lease, a host-wide flock,
running runtron processes, and active rinzler serving before a campaign may
start; `ci_took_dut` is the between-runs re-check.

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
Without `sudo` the journal shows `-- No entries --`; that is a permission
notice, not evidence that the timer did not fire.

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
  use `campaign_guard_acquire` [exec/lib-guard.sh:44-72].
- Long campaigns must finish before about 02:30 UTC: the 02:45 prep step brings
  rinzler up and a following campaign cell would collide with it
  (deadline logic exists in `exec/more-testing-r1.sh`).
- Re-check `ci_took_dut` between long runs; the lease says "holding now", not
  "starting in five minutes".
- Do only light work on the machine while the lease is busy (jhan's standing
  rule for this machine).

## Sources

- delphi-3bda: `/etc/systemd/system/ci-runner-stop@.timer`, `ci-runner-stop@.service`,
  `/opt/positron/ci/ci-runner.sh`, `systemctl list-timers --all`, journal of
  the stop service for 2026-09-03 and 2026-09-04.
- positron-ai/systems_test at 470aca1 (clone `~/workspace/ai-runs/systems_test`):
  `.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml`,
  `scripts/manage_dut_lease.py`.
- `gh run list` output for runs 33354547390 .. 33833914529.
- `~/workspace/intel-AMX/exec/lib-guard.sh` (lease rule, guard functions).
