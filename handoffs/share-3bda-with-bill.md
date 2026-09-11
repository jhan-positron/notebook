# Handoff: how to share delphi-3bda with Bill outside the nightly CI

> Written by Claude Code (Linux CLI, machine claude-box) on 2026-09-06.
> Every fact below was read from the live machine on 2026-09-06 05:16 to
> 05:20 UTC (Sat 2026-09-05 22:16 PDT); file:line references point at those
> sources. Companion to `handoffs/check-CI.md`, which covers the nightly CI.

## Short version

Before touching delphi-3bda, run one script on the machine. It says FREE, WAIT,
or YIELD by checking, in order: the CI lease, a blackout window, a claim file
from Bill, how recently Bill logged in, whether he is typing, and whether his
programs use CPU. On WAIT, re-run it every 30 minutes until it says FREE; on
YIELD (Bill logged in within 15 minutes of us) we back off and do the same.

```bash
ssh delphi-3bda '~/workspace/intel-AMX/exec/people-check.sh --claim "what I am doing"'
```

## Words used here

- DUT: device under test; here always delphi-3bda.
- Bill: Bill Baumann, Linux user `bill` (uid 1062305141) on delphi-3bda. He
  logs in over ssh from a Tailscale address (100.103.205.15 on 2026-09-05).
- lease: `/run/lock/systems-test-ci.lease`, the nightly CI's "I hold the DUT"
  file; details in `handoffs/check-CI.md`.
- lib-guard.sh: `~/workspace/intel-AMX/exec/lib-guard.sh`, the shell library
  our campaign scripts source before launching anything on the DUT. `/home`
  is one NFS share (filer.positron.internal), so the same file is visible on
  claude-box and on delphi-3bda (identical md5 on both, 2026-09-06).
- people-check.sh: `~/workspace/intel-AMX/exec/people-check.sh`, the script
  described here (written 2026-09-06). It sources lib-guard.sh.
- claim file: `/var/tmp/3bda-claim.<user>`, one small text file per person
  saying "I am using the machine". Optional; the check works without it.
- blackout: a line in `/var/tmp/jhan/3bda-blackout` naming a time window in
  which we promised the machine to someone else (`blackout_active` in
  lib-guard.sh).
- tty idle: how long since the person last typed in their terminal, as
  printed by `who -u` (`.` = under a minute, `HH:MM`, or `old` = over a day).

## What "Bill is using the machine" means (the six checks, in order)

people-check.sh stops at the first check that fails and prints one line.

| # | Check | Verdict | Exit | Source of truth on the machine |
|---|-------|---------|------|--------------------------------|
| 1 | CI lease busy | WAIT | 1 | `ci_lease_busy` (lease file, `state=busy` and not expired) |
| 2 | Blackout window active | WAIT | 1 | `blackout_active` reading `/var/tmp/jhan/3bda-blackout` |
| 3 | Fresh claim file from another user (younger than 12 h) | WAIT | 1 | `/var/tmp/3bda-claim.*` |
| 4 | Bill logged in during the last 15 min | YIELD (or HOLD, see below) | 2 (0) | `loginctl list-sessions` + `show-session -p Timestamp` |
| 5 | Bill typed in a terminal in the last 30 min | WAIT | 1 | `who -u` idle column |
| 6 | Bill's processes used over 2 CPU-seconds in a 10 s window, or run tron or build binaries | WAIT | 1 | `other_user_active` in lib-guard.sh |
| - | none of the above | FREE | 0 | prints whether Bill has an idle login |

Why each check exists:

- Check 4 covers "we both logged in at the same time" (see the rule below).
- Check 5 exists because an interactive session uses almost no CPU. Bill's
  `python3` prompt on 2026-09-06 had used 1 clock tick in 6 h 17 min
  (`/proc/831866/stat` utime) but he could have been typing a minute ago.
- Check 6 is the existing rule from lib-guard.sh (added 2026-09-05): an idle
  login (open shell, tmux, editor) is not activity. Accounts on delphi-3bda
  come from a directory service, so `getent passwd` does not list Bill;
  `other_user_active` finds people by process ownership instead
  [lib-guard.sh, comment above `other_user_active`].
- Checks 1 and 2 are here so one command answers "may I start", not just
  "is Bill here". On 2026-09-06 05:19 UTC the real run said
  `WAIT: System CI holds the DUT (lease busy)` (nightly run 34009467357), and
  the blackout file held a HOLD line until 2026-09-07 07:00 UTC
  (Mon 2026-09-07 00:00 PDT). When jhan wants the machine back before then,
  delete that line from `/var/tmp/jhan/3bda-blackout`.

Thresholds are environment variables: `SAME_TIME_MIN` (15),
`KEYBOARD_IDLE_MIN` (30), `CLAIM_MAX_H` (12), `PEOPLE_OTHER` (bill).

## Procedure each time we want the machine

1. Check and claim in one step:

   ```bash
   ssh delphi-3bda '~/workspace/intel-AMX/exec/people-check.sh --claim "AMX perf campaign, ~3 h"'
   ```

   FREE + CLAIMED: start work. WAIT: go to step 2. YIELD: go to the rule below.
2. On WAIT, check again every 30 minutes until FREE. In Claude Code:

   ```
   /loop 30m ssh delphi-3bda ~/workspace/intel-AMX/exec/people-check.sh; if the line starts with FREE, claim it with --claim, tell me, and stop the loop; otherwise report the WAIT line only.
   ```

   Without Claude Code, from claude-box:

   ```bash
   until ssh delphi-3bda '~/workspace/intel-AMX/exec/people-check.sh --claim "..."'; do sleep 1800; done
   ```

   (`wait_for_dut_free` in lib-guard.sh is the older 5-minute poll; it covers
   checks 1, 2 and 6 but not the claim, keyboard, or same-time rules.)
3. Campaign scripts still call `campaign_guard_acquire` and re-check
   `dut_contended` between runs, as before [lib-guard.sh].
4. When done, remove the claim:

   ```bash
   ssh delphi-3bda '~/workspace/intel-AMX/exec/people-check.sh --release'
   ```

## The same-time rule (we yield)

"Same time" means Bill's newest login is under 15 minutes old when the check
runs. Then:

- If we have no claim, or our claim is also under 15 minutes old: the script
  prints `YIELD`, deletes our claim file, and exits 2. We do not start; if a
  run began in those minutes, stop it (`campaign_guard_release`, kill our
  runtron), then poll every 30 minutes as in step 2.
- If our claim is older than 15 minutes, Bill arrived while we were already
  working: the script prints `HOLD ... tell bill we are mid-run` and exits 0.
  We keep the machine and message Bill.

Bill's side of the same rule: if he adopts the claim file, he writes
`/var/tmp/3bda-claim.bill` (any text, e.g. `bill since <time>: <note>`) when
he starts and deletes it when he stops; check 3 then makes us wait as long as
his file is under 12 hours old. Without it, checks 4 to 6 still see him.

## Verifying by hand

All on delphi-3bda; none needs sudo.

```bash
who -u                                    # login time, tty idle, pid; Bill was pts/0, idle 06:20 on 2026-09-06
loginctl list-sessions --no-pager         # also shows ssh sessions without a tty
ps -u bill -o pid,stat,etime,pcpu,args --forest
source ~/workspace/intel-AMX/exec/lib-guard.sh; GUARD_OTHER_USERS=bill other_user_active; echo rc=$?   # 0 = active
ls -l /var/tmp/3bda-claim.* 2>/dev/null; cat /var/tmp/jhan/3bda-blackout
```

## Test record (2026-09-06 05:19 to 05:22 UTC, on delphi-3bda)

Machine state: nightly CI lease busy; blackout active; Bill logged in since
2026-09-05 22:47 UTC with one idle `python3` prompt in `/home/bill/gold-arrow`
(tty idle 6 h 20 min, 0.00 CPU-s in 10 s). A copy of the script with checks 1
and 2 removed was used to reach the later checks.

| Case | Setup | Result |
|------|-------|--------|
| A | real script | `WAIT: System CI holds the DUT (lease busy)`, exit 1 |
| B | checks 1-2 removed | `FREE: bill idle login, ...`, exit 0 |
| C | B + `--claim` | wrote `/var/tmp/3bda-claim.jhan`, exit 0 |
| D | fake claim file for user `bill2` | `WAIT: bill2 claimed the machine at ...`, exit 1 |
| E | `SAME_TIME_MIN=1000` (Bill's 391-min-old login counts as recent), our claim fresh | `YIELD ... releasing our claim`, exit 2, claim file gone |
| F | as E, our claim aged to 2000 min | `HOLD: ... tell bill we are mid-run`, exit 0 |
| G | `KEYBOARD_IDLE_MIN=100000` | `WAIT: bill at keyboard on pts/0 (tty idle 06:20)`, exit 1 |
| H | `--release` | `RELEASED`, exit 0, no claim files left |

Not tested live: check 6 returning active (Bill ran nothing during the test).
Its logic is the pre-existing `other_user_active`, unchanged.

## Sources

- delphi-3bda on 2026-09-06 05:16 to 05:22 UTC: `who -u`, `w`, `last -F`,
  `loginctl list-sessions` / `show-session`, `ps -u bill`,
  `/proc/831866/{stat,cmdline,cwd,fd}`, `/run/lock/systems-test-ci.lease`,
  `/var/tmp/jhan/3bda-blackout`, `mount | grep /home`, `command -v` for
  flock, jq, python3, tmux, screen (all present; inotifywait absent).
- `~/workspace/intel-AMX/exec/lib-guard.sh` (md5 6232f1cc... on both hosts):
  `ci_lease_busy`, `other_user_active`, `blackout_active`, `dut_contended`,
  `wait_for_dut_free`, `campaign_guard_acquire`.
- `~/workspace/intel-AMX/exec/people-check.sh` (new, 2026-09-06).
- `handoffs/check-CI.md` (2026-09-05) for the CI lease rule; Bill has a copy at
  `/home/bill/gold-arrow/check-CI-delphi-3bda.md`.
