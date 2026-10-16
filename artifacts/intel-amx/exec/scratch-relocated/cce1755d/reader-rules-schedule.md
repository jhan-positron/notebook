# Reader report: machine rules and the PR-4 schedule on delphi-3bda

Read on 2026-10-12. Every fact below comes from the files named in brackets. Nothing was run on delphi-3bda. Nothing was modified.

## Short version

The rules the PR-3 handoff quotes are all still in their sources, and the measured October lease-clear time (about 13:10 to 13:26 UTC, seen by the guard as "free" between 13:19 and 13:36 UTC) is later than the check-CI.md timeline line, which still carries the pre-gemma end of about 11:25 UTC. Two schedules are possible for PR-4: (a) everything whole-machine on one day after the nightly (chain part 13:25 to about 15:45 UTC, then the campaign W to about 00:15 UTC the next day, with about 2 h of slack before the 02:05 UTC hard end), or (b) the chain's whole-machine part the evening before (launch by 20:00 UTC, end before 01:30 UTC) and W alone the next day (13:25 to about 22:05 UTC, about 4 h of slack). The 2026-10-09 pre-check marker design failed in practice because the pre-check and the campaign waited for the same lease event, so for PR-4 the chain must create the hand-off marker before it waits for the lease.

## Words used here

- delphi-3bda (3bda, the DUT): the Intel Xeon 6 test server, shared with Bill and with the nightly CI [check-CI.md:21].
- nightly / System CI: the GitHub Actions workflow in positron-ai/systems_test that drives delphi-3bda from about 03:30 UTC [check-CI.md:12-15, 22-23].
- lease: the file /run/lock/systems-test-ci.lease, written by the CI while it holds the machine [check-CI.md:27-28].
- grace (600 s): ci_lease_busy's optional argument; a "busy" lease that expired less than 600 s ago still counts as busy [lib-guard.sh:25].
- rinzler: the production inference server, four systemd units rinzler@0..3; "serving up" = units active [check-CI.md:24].
- platformd: the control service (port 8080) that starts and stops the rinzler engines [check-CI.md:25-26].
- Bill's marker: the file /bill-has-instance-0,2 on delphi-3bda; present = Bill may use the first half (socket 0) [bill-share.sh:4-10].
- our half: socket 1, cpus 72-143 and 216-287, tron `--instance 1,2` [memory 3bda-shared-with-bill.md:64-65].
- chain: the PR's delphi-3bda build-and-test script (PR-3: exec/pr3-20261012/chain2.sh). Its steps: A, M1, M2, A2, A3, B, F, A0, head (our half); C (host suite), D (token-identity smokes), E (runtron cells) (whole machine) [PR3-handoff.md:256-313].
- W: the whole-machine nightly-config perf campaign exec/pr4424ci-20261009/campaign.sh (4 arm passes: base, target, target, base) [campaign.sh:11-18].
- deb: the Debian package of tron; build-target.sh builds it with `make deb` [build-target.sh:8-10, 88-91].
- bench --update: `bin/slice bench --update <tests>`, which re-measures the named tests' cost rows in config/test-benchmarks.json [bin/slice:5, 2169-2171].
- hand-off marker: the file /var/tmp/jhan/pr4424ci-precheck.running, which campaign.sh waits on after the lease [campaign.sh:358].
- D (day): the UTC evening on which the executor starts; D+1 the next UTC day. Today is 2026-10-12. The executor may start on 2026-10-12 evening UTC or later. The nightly runs every day at 03:30 UTC [check-CI.md:53, 69].

## 1. The rules the PR-4 executor must follow

| # | Rule | Source line(s) | PR-3 handoff | Status |
|---|---|---|---|---|
| R1 | The lease is the only authoritative "CI holds the DUT" signal. Busy = file exists, state "busy", now < expires_at_epoch (+ grace). Missing, non-busy or expired = not busy. | check-CI.md:16-17, 187-192; lib-guard.sh:5-10, 25-45 | 5.3 (line 360) | unchanged |
| R2 | Never launch while `ci_lease_busy 600` says busy; wait with 600 s grace (CI heartbeat gaps of 261 s to 322 s were seen). | lib-guard.sh:207-208, 267; dut.sh:27, 51-53; check-CI.md:260-261 | 5.3 (360) | unchanged |
| R3 | Take `campaign_guard_acquire` before a campaign: it checks the lease, other_user_active, blackout_active, the flock /var/tmp/jhan/3bda-campaign.lock, a running runtron, and active rinzler serving (unless `--allow-serving`). | lib-guard.sh:146-179; check-CI.md:202-205, 260-261 | 5.3 (360) | unchanged |
| R4 | Re-check `ci_took_dut` (= ci_lease_busy or other_user_active or blackout_active) between long runs. | lib-guard.sh:319-337; check-CI.md:265-266 | 5.3 (360) | unchanged |
| R5 | Pass at least 50400 s (14 h) to `wait_for_ci_release` / `wait_for_dut_free`; their default is 21600 s (6 h), shorter than the nightly. | lib-guard.sh:340-360; check-CI.md:147-153, 199, 267-270 | 5.3 (360) | unchanged in the source; the chain scripts do not call these functions, they poll with their own wait_slot (120 s, no timeout, bounded by END_BY) [chain2.sh:98, 95] |
| R6 | Long campaigns must finish before about 02:30 UTC; the 02:45 UTC prep step brings rinzler up. | check-CI.md:262-264 | 5.3 (360) | unchanged; the scripts use stricter times: END_BY 01:30 UTC and DEADLINE_HHMM 0130 for D and E [chain2.sh:66; sync4424-20261002/campaign.sh:14, 37, 75, 164; PR3-handoff.md:309]; W's DRIVER_END_BY 02:05 UTC with a restore of up to 16 min [campaign.sh:75; README.md:90]; the takeover hold 01:40 to 04:30 UTC in rinzler_takeover_if_idle [lib-guard.sh:210-213, 233-236, 269]; the chain's advisory pre-CI hold 02:10 to 03:45 UTC, during which no step starts [chain2.sh:97-98; memory:76] |
| R7 | The ci-runner-stop timer fires at 02:45 UTC and POSTs inference/up (serving comes up before the nightly). | check-CI.md:29-30, 52, 81-85 | 5.3, step 6 | unchanged |
| R8 | The nightly cron is `30 3 1-31/1 * *` (03:30 UTC daily). Real starts 03:37 to 03:41 UTC, once 04:57 UTC; the lease is written at about 03:38 UTC. | check-CI.md:53, 59-61, 69-71; lib-guard.sh:211-212; campaign.sh:337-338 | 5.3 (360) | unchanged |
| R9 | Only light work (ls, git rev-parse, sha256sum, reading files) on 3bda while the lease is busy. | check-CI.md:271-272 | 5.3 (360) | unchanged |
| R10 | Bill's marker: present = Bill may use the first half; absent = whole machine ours. Our second-half campaigns ignore it. "take" only on jhan's word, never from a campaign script on its own; "take" is refused (exit 2) while Bill is active; after our whole-machine work WE re-create it with "release". | bill-share.sh:8-16, 21, 38-51; memory:84-96 | 5.3 (361) | unchanged; the PR-1 to PR-3 chains took it themselves after the our-half verdict, with jhan's order to execute the handoff as the word [PR3-handoff.md:361; split-status.md:342, 372] |
| R11 | Marker changes by Claude itself were refused by the auto-mode classifier ("Modify Shared Resources"); jhan runs them by hand as `! ssh delphi-3bda bash ~/workspace/intel-AMX/exec/bill-share.sh release`. | memory:94-96 | section 7 (classifier refusals) | unchanged |
| R12 | Whole-machine work (cells against serving, the host suite with serving down, the deb campaign, bench --update) only through the takeover rules, with serving restored afterwards. | split-handoff.md:241-244; memory:74-76 | 5.3 (361) | unchanged |
| R13 | platformd 0.11 restarts a unit stopped with systemctl within about a minute; take serving down through the platformd API (POST /api/inference/down, `dut.sh serving-down`), bring it up with `dut.sh serving-up`. | lib-guard.sh:248-253; dut.sh:28-30 | 5.3 (361) | unchanged |
| R14 | Never run a real-driver tron binary on 3bda without `--instance` (it deletes every unlocked slice file). Scripts that pin cards on the command line must `env -u SYSTEM_CONFIG`. | memory:72-74, 78-82 | 5.3 (365: `SYSTEM_CONFIG="--instance 1,2"`) | unchanged |
| R15 | bench --update is a whole-machine measurement: it launches tests under `--instance i,n` for every slot (both sockets); run it only when Bill is idle (marker taken). | memory:74-76 | split-handoff.md:201, 241 | unchanged |
| R16 | The deb build (`make deb`) runs outside nix with 48 jobs pinned to socket 1; not while the nightly perf phase runs; not while another build of ours runs on 3bda. | build-target.sh:8-10, 27, 90; README.md:61-68 | split-handoff.md:201 (W) | unchanged |
| R17 | Run `bin/slice route` from the worktree on 3bda before the hardware steps and obey the verdict; a free lease is not a route decision. | PR3-handoff.md:358 | 5.3 (358) | PR-3 measured `local-legacy` on 2026-10-12 [split-status.md:340] |
| R18 | Isolated worktrees under /var/tmp/jhan on 3bda's local disk; never build in the NFS tree; never edit a script a 3bda process is running. | PR3-handoff.md:359, 445 | 5.3, section 8 | unchanged |
| R19 | A campaign and a pre-check must not wait for the same lease event; create the hand-off marker before waiting. | split-handoff.md:338; PR3-handoff.md:443; precheck2.sh:3-5 | section 8 | see section 5 below |

### 1.1 Flags: what the PR-3 handoff quotes against what the sources say

- Lease-clear time. PR3-handoff.md:360 says "It holds the lease until about 13:15 to 13:30 UTC (check-CI.md:170)". check-CI.md:170 does not state a lease-clear time. That line says "Extend the window to 13:30 UTC before reusing it" about the g1 campaign's clock hold [check-CI.md:165-170]. The 13:15 figure is an estimate at check-CI.md:55-56 and 127-129 ("est.: 03:38 start + 7 h 49 min median + 1 h 50 min"). The timeline line check-CI.md:55 still says "~11:25 suite ends" (the pre-gemma value). gemma-4-31b is in the suite now: the nightly's 14 perf configs include "gemma-4-31b tp2 8u" [campaign.sh:11-13], and the nightly reports have been posted at 06:15 to 06:17 PDT (13:15 to 13:17 UTC) since 2026-09-15 [exec/results/nightly_rows.json, reports 2026-09-15 to 2026-09-17]. Measured in October, the time at which our guard (600 s grace, 120 s poll) said "free": 13:36:08 UTC on 2026-10-09 [pr4424ci status-history.log:47; merge4737-precheck-chain.log:30], 13:19:41 on 2026-10-10 [pr1-20261010-chain.log:4], 13:28:11 on 2026-10-11 [pr2-20261011-chain.log:26], 13:24:15 on 2026-10-12 [pr3-20261012-chain.log:74]. With the 600 s grace, the lease itself cleared about 10 min earlier each day: about 13:09 to 13:26 UTC. So the PR-4 handoff should say: "the guard reports the lease free between 13:19 and 13:36 UTC (4 days measured, 2026-10-09 to 2026-10-12); plan on 13:25 and allow 13:36".
- The 02:30 UTC end rule: still at check-CI.md:262-264. No change. The scripts' own deadlines are stricter (R6).
- The 50400 s wait: still at check-CI.md:267-270 and in the example at :199. No change. Note for the PR-4 handoff: the chain and W do not use `wait_for_ci_release`; W's lease wait is bounded by DEADLINE_START (19:00 UTC on 2026-10-09, 6 h after NOT_BEFORE) [campaign.sh:349-351, 73].
- The 02:45 ci-runner-stop timer: still at check-CI.md:29-30, 52, 81-85. No change.
- The 03:30 cron: still at check-CI.md:53, 69. No change.
- The light-work rule: still at check-CI.md:271-272. No change.
- The job timeout: check-CI.md:72-76 says 570 min as of 2026-09-14 and that Rhys planned to raise it. 03:38 + 570 min = 13:08 UTC. The October runs ended after 13:08 UTC, so the timeout was raised. Its current value: Insufficient data (not in these files; `gh run view` of a recent run or the workflow yaml would resolve it). It matters because a hung run holds the lease until timeout + 15 min TTL [check-CI.md:171-177], and a timeout of 630 min or more reaches the disabled 14:00 UTC start timer [check-CI.md:138-142].
- Dates of the sources: check-CI.md was written 2026-09-05 and updated 2026-09-14 [check-CI.md:3-8]. The memory file's front matter says modified 2026-09-05T03:43:39Z [memory:8], but its body carries entries dated up to 2026-09-18 [memory:102]; the marker protocol entry is dated 2026-09-15 [memory:84-93]. bill-share.sh is dated 2026-09-15 in its header [bill-share.sh:2].

## 2. Durations: measured where a record exists, estimated otherwise

| Step | Measured | Source | Planning figure |
|---|---|---|---|
| A (VNNI build, fresh worktree, 6 tests, kill switch) | 873 s (14.6 min) on 2026-10-12 | split-status.md:358 | 15 min |
| M1 | about 2 min (t_k_vnni_layout rebuild and one case) | split-status.md:360 (no time recorded) | 2 min |
| M2 | t_llama_unit rebuilds 122 s + 13 s plus two runs | split-status.md:361 | 10 min (the task's figure; measured is less) |
| A3 | 271 s (4.5 min) | split-status.md:363 | 6 min |
| B | 289 s (4.8 min) | split-status.md:364 | 6 min |
| F | about 1 min plus the lint shell | split-status.md:344 | 2 min |
| Our half total | 01:13:09 to 01:44 UTC = 31 min (PR-3, with A2 112 s) | split-status.md:355, 367 | 41 min (the task's sum) |
| Deb build (build-target.sh, one run) | 23:58:09 to 00:14:47 UTC = 16 min 38 s; `make deb` 918 s | pr4424ci-20261009-build-target.log:1, 73; manifest "built" 00:14:47Z | README says 30 to 40 min [README.md:61, build-target.sh:20]; use 17 min measured, 40 min worst |
| Marker take to serving down (5 min idle test) | 13:24:25 to 13:31:45 = 7 min 20 s | pr3-20261012-chain.log:74, 84, 93-94; split-status.md:372 | 7.5 min (the task's 2 min is low) |
| D, 3 cells x 5 arms | 13:31:45 to 13:42:22 = 10 min 37 s | pr3-20261012-chain.log:94-97 | 11 min |
| E, 45 runs | 13:42:22 to 14:43:38 = 61 min 16 s = 81.7 s per run | pr3-20261012-chain.log:97-98 | PR-4: 5 cells = (3 CPU x 5 arms + 2 FPGA x 3 arms) x 3 reps = 63 runs x 81.7 s = 86 min (est.; FPGA cells at 8 users have no record here: Insufficient data, likely shorter) |
| C, host suite (build-test-host + test-host) | 14:43:48 to 14:57:13 = 13 min 25 s; test makespan 109.6 s | pr3-20261012-chain.log:99-100; host-suite-pr3.txt:170 | 13.5 min (the task's 5 min is low) |
| bench --update of 4 tests | no record. Cost rows on granite_rapids_6962p (= delphi-3bda [attnstats-20260924/tests-on-t_llama_unit.out: "Found server type: granite_rapids_6962p"]): t_llama_unit 28.081 / 28.287 / 28.294 s at widths 1 / 2 / 4; t_amx_numerics 0.81 / 0.832 / 0.743 s; t_amx_dispatch_dtype 0.778 / 0.775 / 0.873 s; t_k_vnni_layout 0.9 / 0.907 / 0.91 s | probe worktree config/test-benchmarks.json, host granite_rapids_6962p | one run per test per width (widths 1, 2, 4) [slice_bench_manifest.py:14, 122-130; bin/slice:114]; up to one test per NUMA node in parallel [bin/slice:2236-2240]; calibration is skipped on --update [bin/slice:2532-2541]; sum of the rows 92 s, so about 2 min of measurement (est.) plus `make build-test` first [bin/slice:2161-2165]; the build's duration is Insufficient data (C's build-test-host took about 11 min inside C's 13.5 min, the nearest record); plan 15 min |
| Serving up | 14:57:14 to 14:59:30 = 2 min 16 s | pr3-20261012-chain.log:108-113 | 2.5 min |
| Whole-machine part, PR-3 | marker held 13:24:25 to 14:59:30 = 95 min; serving down 86 min | split-status.md:384 | PR-4: 7.5 + 11 + 86 + 13.5 + 15 + 2.5 = 136 min; plan 2 h 15 min (est.) |
| W, one arm pass (full 14 configs + sw8k + restarts) | 110 + 8, 106 + 7, 109 + 8, 109 + 8 min driver time; start-to-start 124.5, 121.4, 123.8 min; last pass 121.3 min | status-history.log:52-67 | 122 min per arm pass; 8 h 11 min for four |
| W, setup before the first pass | 13:36:08 lease free to 13:42:46 first driver start = 6.6 min | status-history.log:47-52 | 7 min |
| W, restore | 21:53:44 to 22:02:47 = 9 min | status-history.log:67-69 | up to 16 min [README.md:90] |
| W, lease free to done | 13:36:08 to 22:02:47 = 8 h 27 min | status-history.log:47, 69 | 8 h 30 min |

## 3. The two schedules (UTC)

Common facts for both:

- The our-half steps (A, M1, M2, A3, B, F) run next to serving on socket 1 with the lease free; PR-3 ran them 01:13 to 01:44 UTC without touching serving [split-status.md:355-367]. The chain's wait_slot holds a step that would start between 02:10 and 03:45 UTC [chain2.sh:97-98].
- The two deb builds run on socket 1 outside nix; they must not run while the nightly runs (lease busy) and not while another build of ours runs [README.md:66-68; check-CI.md:271-272]. On 2026-10-08 the build ran 23:58 to 00:15 UTC [build-target.log:1, 73]. They run before W's launch, because launch.sh checks build.status = ok [README.md:63-70].
- W's knobs are dates; the 2026-10-09 defaults (NOT_BEFORE 13:00, DEADLINE_START 19:00, PASS_DEADLINE 23:30, DRIVER_END_BY 02:05 next day) must be re-set for the new day [campaign.sh:72-75; README.md:85-90]. campaign.sh refuses a start more than 8 h before DEADLINE_START without NOT_BEFORE [campaign.sh:333] and requires DEADLINE_START < PASS_DEADLINE < DRIVER_END_BY [campaign.sh:330].
- A full pass starts only when at least max(measured pass + 10 min, 110 min) remains before DRIVER_END_BY [campaign.sh:465-466]; with a 110 min pass that is 120 min. So the fourth full pass must start by 00:05 UTC, and the first by 00:05 minus 3 x 122 min = about 17:59 UTC. W's first pass starts about 7 min after the machine is free. So the machine must be free for W by about 17:50 UTC D+1 for all four passes.
- A late nightly: the latest observed start was 04:57 UTC (2026-09-03) [check-CI.md:70, 132], 1 h 19 min after the usual 03:38; earlier 05:17 and 06:07 UTC starts were seen in August [check-CI.md:132-134]. The lease then clears that much later.

### Option (a): one whole-machine session on D+1, chain part first, then W

Pre-work on D evening (lease free, next to serving): launch the our-half chain and the two deb builds. Duration 41 min + 2 x 17 min = 75 min (measured basis); 41 + 2 x 40 = 121 min (README basis). Latest launch so that every step starts before the 02:10 hold: 00:50 UTC D+1 (measured basis) or 00:05 UTC (README basis). Recommended: launch by 22:00 UTC on D.

D+1 session (planned on a 13:25 marker take; measured range 13:19 to 13:36):

| Time (UTC) | Step |
|---|---|
| 13:00 | chain leaves START_NOT_BEFORE, polls the lease every 120 s with 600 s grace |
| 13:25 | lease free: Bill's marker taken (hand-off marker already present since launch, section 5) |
| 13:25-13:33 | serving down through platformd (5 min idle test) |
| 13:33-13:44 | D: 3 smoke cells x 5 arms |
| 13:44-15:10 | E: 63 runs (est. 86 min) |
| 15:10-15:24 | C: host suite |
| 15:24-15:40 | bench --update (make build-test + 4 tests at 3 widths) |
| 15:40-15:43 | serving up; hand-off marker removed; Bill's marker released |
| 15:45 | W (polling every 2 min) sees the hand-off marker absent; takes Bill's marker; preflight, restore.deb saved |
| 15:52 | base-pass1; then target-pass1 17:54, target-pass2 19:56, base-pass2 21:58 (122 min each) |
| 00:00 D+2 | last sw8k cell ends; restore 9 to 16 min |
| 00:10-00:16 D+2 | W done; serving up; marker released |

Knobs for W: NOT_BEFORE=D+1T13:00Z, DEADLINE_START=D+1T18:00Z (the latest useful first-pass start; W aborts and gives the marker back if the chain part has not released the machine by then [campaign.sh:363, 88]), PASS_DEADLINE=D+2T00:10Z (the 23:30 default would block a fourth pass that starts after 23:30 when the session runs late), DRIVER_END_BY=D+2T02:05Z.

Latest launch: the chain part must release the machine by about 17:50 UTC D+1; with a 2 h 15 min chain part the marker take must happen by about 15:35 UTC; so the lease may be late by up to about 2 h 10 min (free by 15:35). Expected end: about 00:15 UTC D+2. Slack before DRIVER_END_BY: about 1 h 50 min.

Risks:
- A nightly that starts 04:57 UTC (observed) pushes everything by about 1 h 20 min; the slack covers it.
- A failed W pass: the campaign repeats a tag once when time remains [campaign.sh:472-492]; one repeat of a 122 min pass uses all the slack, and the fourth pass is then skipped ("not enough time before DRIVER_END_BY") [campaign.sh:466]; the ABBA design then lacks its second base pass.
- A failed E cell is cheap to redo (one arm-cell = 3 x 82 s = about 4 min); a failed C or bench costs its own length once; every minute spent is taken from W's slack.
- A failure in the pre-work on D evening (our-half verdict not ok, deb build not ok) blocks the whole D+1 session; the WHOLE_MACHINE_ONLY mode aborts on a failed verdict [split-status.md:350].
- If the pre-work is NOT done on D evening and runs on D+1 after the lease clears instead, the chain part starts about 14:40 to 15:25 and releases about 16:55 to 17:40, which is at the 17:50 limit; W then likely gets three passes.

### Option (b): the chain's whole-machine part on D evening, W alone on D+1

D evening, serial: our-half chain (41 min planning, 31 min measured), two deb builds (34 min measured, 60 to 80 min README), the whole-machine part (2 h 15 min est.). Total about 3 h 30 min (measured basis) to about 4 h 15 min (README basis). The D export and the E line stop at DEADLINE_HHMM 0130 and the chain at END_BY 01:30 UTC [chain2.sh:66, 95; sync4424-20261002/campaign.sh:37, 75, 164; PR3-handoff.md:309]. Latest launch: 22:00 UTC (measured basis) or 21:15 UTC (README basis). Recommended launch: 20:00 UTC on D, which leaves about 2 h for one redo.

Timeline at a 20:00 UTC launch:

| Time (UTC) | Step |
|---|---|
| 20:00-20:41 | our-half steps, next to serving |
| 20:41-21:15 | two deb builds (17 min each measured; to 22:00 at 40 min each) |
| 21:15 | Bill's marker taken; serving down to 21:23 |
| 21:23-21:34 | D |
| 21:34-23:00 | E (63 runs) |
| 23:00-23:14 | C |
| 23:14-23:30 | bench --update |
| 23:30-23:33 | serving up; Bill's marker released; chain done |
| 02:10-03:45 | pre-CI hold; 02:45 prep; nightly lease about 03:38 |

Sub-variant: the two deb builds can instead run on D+1 from 13:20 to 13:55 UTC after the lease clears, with W's NOT_BEFORE set to 13:50; W then ends about 22:40 UTC. The builds must not overlap the nightly [README.md:66].

D+1 (W alone): launched from claude-box any time after build.status = ok, with NOT_BEFORE=D+1T13:00Z, DEADLINE_START=D+1T19:00Z, PASS_DEADLINE=D+1T23:30Z, DRIVER_END_BY=D+2T02:05Z (the 2026-10-09 values moved by date). W polls the lease from 13:00, sees it free between 13:19 and 13:36 (measured range), finds the hand-off marker absent (the chain ended the evening before), takes Bill's marker, and starts base-pass1 about 13:32 to 13:44. Four passes end about 21:40 to 21:52; restore; done about 21:50 to 22:05 UTC (the 2026-10-09 run: 13:36 to 22:02) [status-history.log:47-69]. Slack before DRIVER_END_BY: about 4 h. The nightly may be late by up to about 4 h 20 min (first pass by 17:59).

Risks:
- The evening part has about 2 h of margin at a 20:00 launch and none at a 22:00 launch; a failure late in E or in C cannot be redone before 01:30; the redo slot is D+1 after W (about 22:05 to 01:30 D+2 = 3 h 25 min, enough for the whole-machine part once) or D+2 after the nightly.
- The bench --update commit and the stack comparison (split-handoff.md:199, run again "on the exact commit that will be pushed") wait for the whole-machine part; a slip moves the PR opening by a day.
- W has about 4 h of slack for a late nightly or one pass repeat; a W failure that needs a second repeat moves to D+2.
- No hand-off marker is needed between the chain and W in (b), because the chain has ended before W's NOT_BEFORE; W's launch must still come after the deb builds (launch.sh checks build.status) [README.md:63-70].

### Today

The machine on 2026-10-12 after PR-3's run 2: units 0 and 1 active, lease free, Bill's marker present (released 14:59:30 UTC) [split-status.md:372; pr3-20261012-chain.log:111-113]. For option (b), today's launch window is 20:00 to 22:00 UTC on 2026-10-12, with W on 2026-10-13 from 13:00 UTC, done about 22:05 UTC. For option (a), the pre-work tonight by 22:00 UTC, the session on 2026-10-13 from 13:25 UTC, done about 00:15 UTC on 2026-10-14.

## 4. W's own waits and deadline handling (campaign.sh)

- Sleep until NOT_BEFORE in naps of up to 30 min; "no lease file exists before the nightly takes it, so a lease-free test alone would start the campaign at once" [campaign.sh:337-345; status-history.log:1-28].
- Lease: `dut.sh lease-free` (ci_lease_busy 600) every 120 s; an ssh failure counts as busy; abort at DEADLINE_START [campaign.sh:347-353; dut.sh:51-53].
- Hand-off marker: `ssh test -e /var/tmp/jhan/pr4424ci-precheck.running` every 120 s; rc 0 = wait, other rc = "DUT did not answer", retry; abort at DEADLINE_START [campaign.sh:355-369].
- No runtron or campaign.sh peer on the DUT; abort at DEADLINE_START [campaign.sh:370-380].
- Remote flock holder with HOLDER_LIFE = DRIVER_END_BY + 2 h [campaign.sh:69, 383-388].
- Bill's marker: `bill-share.sh take`; rc 2 (Bill active) = retry every 30 min until DEADLINE_START, with a lease re-check each time; other rc = abort [campaign.sh:390-406].
- Preflight: installed version must be the nightly's (not one of ours), restore.deb saved, "bill marker: absent" required [campaign.sh:409-427].
- Lease re-test before the first package switch [campaign.sh:429-431].
- Per tag: DEADLINE_START before the first pass; PASS_DEADLINE before every full pass; lease state (3 attempts); the DRIVER_END_BY need check (measured pass + 10 min, at least 110 min, for a full pass) [campaign.sh:456-466].
- Driver rc 9 = the lease became busy during a pass: stop safely [campaign.sh:472]. A failed tag is repeated once when time remains [campaign.sh:477-492].
- End: restore_and_release runs exactly once, on the normal path and on a signal: config.env cleared, restore.deb reinstalled, engines down and up (HANDOFF=up), Bill's marker released (3 attempts), flock released [campaign.sh:215-254, 502-503]. The restore needs up to 16 min; the ci-runner-stop timer fires at 02:45 UTC [campaign.sh:75; README.md:90].
- Stop early with `kill -TERM <pid>`, never -9 [README.md:151-152].

## 5. The pre-check marker hand-off

### 5.1 The 2026-10-09 design, quoted

precheck.sh (runs on delphi-3bda) creates the marker after its lease wait and removes it in its EXIT trap:

- precheck.sh:8-10: `#   0.  sleep until NOT_BEFORE (no lease file exists before the nightly takes it, so a lease-free test alone would start at once); then the marker /var/tmp/jhan/pr4424ci-precheck.running is created: the perf campaign's wait loop holds while it exists.`
- precheck.sh:34: `MARKER=/var/tmp/jhan/pr4424ci-precheck.running`
- precheck.sh:48-49: `finish() { rm -f "$MARKER"; echo "$(ts) marker removed"; }` and `trap finish EXIT`
- precheck.sh:59-60: `wait_slot "step 1"` then `touch "$MARKER"; echo "$(ts) marker $MARKER created (the perf campaign waits for it to disappear)"`
- precheck.sh:47 (wait_slot): `while ci_lease_busy 600 || other_user_active 2>/dev/null; do ... sleep 120; done`

campaign.sh (runs on claude-box) waits for the marker after the lease and before the peer check, the flock and Bill's marker:

- campaign.sh:45-47: `# Wait order: NOT_BEFORE, CI lease free, pre-check marker /var/tmp/jhan/pr4424ci-precheck.running absent (the correctness pre-check chain of exec/merge4737-20261008/precheck.sh runs before us in the same window and holds that file), no runtron/campaign peer, campaign flock, Bill's marker; DEADLINE_START applies to every wait.`
- campaign.sh:358-369: `PRECHECK_MARKER=/var/tmp/jhan/pr4424ci-precheck.running`; `timeout 60 ssh $SSH_OPTS "$DUT_ALIAS" "test -e $PRECHECK_MARKER"; mrc=$?`; rc 0: abort past DEADLINE_START, else `status "waiting: pre-check running (marker $PRECHECK_MARKER present)"; nap 120`; other rc: `status "waiting: DUT did not answer the pre-check marker test (rc $mrc); retry in 2 min"; nap 120`; then `status "pre-check marker absent"`.
- README.md:59-64 describes the same order and says an ssh failure means "retry", never "absent".

### 5.2 What happened on 2026-10-09

- Both scripts polled the same lease with the same 600 s grace. The campaign saw the lease free at 13:36:08 and tested the marker at 13:36:08: absent [status-history.log:47-48]. The pre-check's wait_slot returned at 13:36:11 and created the marker at 13:36:11, 3 s after the campaign's test [merge4737-precheck-chain.log:30-31].
- The campaign took Bill's marker at 13:36:30 and started base-pass1 at 13:42:46 [status-history.log:50, 52]. The pre-check's serving-down found traffic at 13:48:21 ("engines still see traffic; NOT taking serving down") and then blocked on the campaign flock; precheck.sh was stopped at 15:1x UTC [merge4737-precheck-chain.log:44-46; precheck2.sh:3-5].
- The fix, precheck2.sh, inverted the order: it waits for the campaign's end marker exec/results/pr4424ci-20261009/.done* (polled every 300 s), sleeps 60 s "the campaign's release_lock and bill release follow the marker by seconds", then creates its own marker and runs [precheck2.sh:10-12, 64-77]. A first attempt at 22:10 UTC ran the host suite with serving up (6 heap_setup failures); the 23:05 run (precheck3.sh: NOT_BEFORE now, END_BY 01:30, Bill's marker taken) took serving down at 23:06 and finished at 23:10 [merge4737-precheck-chain.log:49, 76-107; precheck3.sh:2-6, 71-74].
- The recorded lesson: "a campaign and a pre-check must not wait for the same lease event; create the hand-off marker before waiting" [split-handoff.md:338; PR3-handoff.md:443].

### 5.3 What this means for PR-4's chain and W (option (a))

- The chain must create /var/tmp/jhan/pr4424ci-precheck.running at launch, before its START_NOT_BEFORE hold and before its lease wait, and remove it in its exit handler after serving-up and the Bill marker release (the order of PR-3's chain-finish.sh: stop our workload, serving up when the lease is free and no unit is active, release the marker, print the machine line [split-status.md:311]). W's campaign.sh then needs no change: after the lease it waits on the marker.
- Why the marker is the only guard during C and bench: W's "no runtron peer" wait [campaign.sh:370-380] protects W only while the chain runs runtron (D and E). During C (host suite) and bench no runtron of ours runs. W's `bill take` on an absent marker returns 0 with "marker already absent; the whole machine is ours" [bill-share.sh:39], and W's preflight requires the marker absent [campaign.sh:421]. So if the hand-off marker is missing while the chain holds Bill's marker, W runs on top of the chain's C or bench step.
- The chain's hold on W is bounded by W's DEADLINE_START [campaign.sh:363]; set it after the chain's expected release (section 3, option (a): 18:00 UTC).
- In option (b) no hand-off marker is needed, because the chain ends the evening before W's NOT_BEFORE.

## 6. Insufficient data

- The current nightly job timeout (check-CI.md:72-76 is from 2026-09-14). Resolve with `gh run view` of a recent run or the workflow yaml.
- The duration of `make build-test` before bench --update. Resolve by timing it once on our half with the lease free.
- The duration of an 8-user FPGA-attention E cell (the two FPGA cells of PR-4's E). The 2026-10-09 E cells were CPU only [precheck.sh:94; steps.txt]. Resolve from the first PR-4 run.
- The duration of a deb build of PR-4's head on a day when the machine is otherwise idle: one measurement exists (16 min 38 s on 2026-10-08, next to serving), the README says 30 to 40 min [README.md:61].
- Whether PR-4's W needs two deb builds. On 2026-10-09 the base arm was the nightly deb saved from apt (no build) and only the target was built [README.md:20-22; campaign.sh:6-8]. A second build is needed only if the base arm is to be built from the stack's main 72308ec90c instead of the nightly deb of the day; the task text asks for two builds, so the schedule allows two.

--- concerns ---
- PR3-handoff.md:360 cites check-CI.md:170 for "holds the lease until about 13:15 to 13:30 UTC"; that line is about a clock-hold window, not the lease-clear time. The PR-4 handoff should cite the measured October times instead (guard free at 13:19 to 13:36 UTC on 2026-10-09 to 2026-10-12).
- check-CI.md's timeline (line 55) still says the suite ends about 11:25 UTC; gemma-4-31b is in the suite (campaign.sh:11-13) and the measured end is about 13:10 to 13:26 UTC. The nightly job timeout value after the gemma change is Insufficient data; it bounds how long a hung run holds the lease (timeout + 15 min).
- The task's per-step figures understate three measured steps: marker take to serving down took 7 min 20 s (not 2 min; the 5-min idle test), C took 13 min 25 s (not 5 min; it includes make build-test-host), and E for PR-4 with 63 runs is about 86 min at the measured 81.7 s per run (the task's 45-run figure is PR-3's). The whole-machine part is about 2 h 15 min (est.), not 95 min.
- In option (a) the campaign W's 2026-10-09 defaults must change: PASS_DEADLINE 23:30 would block a fourth full pass that starts after 23:30 when the session runs late (planned start 21:58); set PASS_DEADLINE to about 00:10 UTC D+2 and DEADLINE_START to 18:00 UTC D+1 (the latest useful first-pass start for four passes).
- Option (a) only works with four W passes if the our-half steps and the two deb builds are done the evening before; done on D+1 after the lease clears, the chain part releases the machine at 16:55 to 17:40 UTC, at the 17:50 limit, and W likely gets three passes.
- For option (a) the PR-4 chain must create /var/tmp/jhan/pr4424ci-precheck.running at launch, before its lease wait, and remove it in its exit handler after serving-up and the Bill release; on 2026-10-09 the pre-check created it 3 s after the campaign tested it and the campaign took the machine. Without the marker, W's `bill take` on an absent marker returns 0 and W's preflight passes, so W would run on top of the chain's C or bench step (no runtron of ours runs then).
- bench --update needs `make build-test` first (bin/slice:2161-2165); its duration on 3bda is Insufficient data (C's build-test-host took about 11 min). The bench run itself is about 2 min for the four tests at widths 1, 2 and 4 (one run each, calibration skipped on --update).
- The cost-row commit ("chore(bench): refresh the cost rows") comes after W's target deb is built from PR-4's head; the deb's commit then differs from the pushed head by config/test-benchmarks.json only. The author should state the order (deb from the pre-bench commit, or bench before the deb build) and what the body reports as the measured commit.
- The task asks for two deb builds; on 2026-10-09 only the target deb was built and the base arm was the nightly deb saved from apt (README.md:20-22). If the base arm is again the nightly deb, one build suffices and 17 to 40 min is saved.
- The memory file 3bda-shared-with-bill.md has front matter dated 2026-09-05 but body entries up to 2026-09-18; the marker protocol entry is dated 2026-09-15. Cite the entry date, not the front-matter date.
