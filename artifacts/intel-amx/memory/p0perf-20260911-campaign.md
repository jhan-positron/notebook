---
name: p0perf-20260911-campaign
description: "2026-09-11 AMX perf test after the nightly CI on jhan-amx-p0 head 47f6f2dceb: runtron + CI-harness qwen tp2/tp4 8u prompt-1024 off/on on OUR half; scripts exec/p0perf-20260911/, report PR3879/new-PRs/PR1/Friday-morning-CI-results.html; review-confirmed campaign traps"
metadata: 
  node_type: memory
  type: project
  originSessionId: 9a280aff-a9b6-4897-bf8d-d65c3b967d8f
  modified: 2026-09-11T07:45:02.415Z
---

Request (jhan 2026-09-11 06:2x UTC): after the nightly CI, on the latest jhan-amx-p0
(47f6f2dcebfa69d3c0b2d94096c8ce9bf3718511), measure TPS and TTFT for qwen-3-4b tp2 and tp4, 8
users, prompt 1024, AMX-off vs AMX-on, with runtron "as usual" and with the CI setup (nightly
perf harness); 8 tests. Report file: PR3879/new-PRs/PR1/Friday-morning-CI-results.html
(jhan named it mid-task). jhan asked "do CI tests need whole 3bda or half?": half is enough
(one engine per test on our cards 90/93/b9/bc; the nightly's own numbers come from 2-4
engines behind the proxy with FPGA attention and are not comparable).

RESULTS (DONE 2026-09-11 11:37-13:04Z, marker ok, machine left clean; runtron 6 reps per arm with
one early-stop run excluded, CI harness 2 reps): per-user decode TPS off -> on: runtron tp2 71.07
-> 79.53 (+11.9%, per-rep +11.5..+12.1), runtron tp4 95.15 -> 101.63 (+6.8%, per-rep +5.2..+9.5,
sd 3.4 = noisy short decode), CI tp2 48.81 -> 55.61 (+13.9%), CI tp4 72.76 -> 82.38 (+13.2%,
reps +15.8/+10.7). TTFT: runtron tp2 3.93 -> 3.13 s (-20.5%), tp4 2.46 -> 2.19 s (-11.0%); CI tp2
3052 -> 2460 ms (-19.4%), tp4 1738 -> 1578 ms (-9.2%). Build 526 s; binaries runtron.p0perf
d5286347..., rinzler.p0perf 9244f7a5..., version 2026.09.11-47f6f2dc. Nightly 34559196745 (its
own conclusion: failure after perf) qwen tp2 185.4 / 507 ms, tp4 147.2 / 635 ms on tron
2026.09.11-632c6181 with FPGA attention over several engines: NOT comparable (orientation only).
Round-1 CI tp4 gain was +4.5% (head 60d66d9c04, socket 0); today +13.2% -> which change
(head, socket, baseline) carries it = Insufficient data; test = round-1 rinzler.canon in today's
placement.

Report: PR3879/new-PRs/PR1/Friday-morning-CI-results.html (generator exec/p0perf-20260911/gen_report.py,
version 2 after a 105-agent verification: both independent recomputations matched every number; 46 wording /
definition / record findings applied). Published as artifact https://claude.ai/code/artifact/a92880b9-a389-406b-833c-3bfb953edd8e
(republish with the same file path, or url=... from another session). Kill-switch cost claim corrected there: the
2026-09-09 clean-build arm (14.65) was NOT faster than the kill-switch arm (14.74), so the old "2-5 pp" figure
(August K-mirror builds) does not apply to this branch.

Campaign: exec/p0perf-20260911/{campaign.sh,rz.sh,launch.sh,summarize.py,gen_report.py};
results exec/results/p0perf-20260911/; log/status/marker exec/logs/p0perf-20260911.*.
Design: waiter polls the lease (3 clear polls) -> build runtron+rinzler (TRON_AMX_DISPATCH=ON,
BUILD_INGEST_MODELS=ON) in /var/tmp/jhan/tron-p0perf on socket 1 -> idle-serving takeover
(G1 recipe) -> runtron cells 4 x RT_REPS=3 (interleaved off/on) -> CI-harness cells 4 x
CI_REPS=2 -> summarize. AMX-off = kill switch TRON_AMX_DISABLE=1 on the same binary.
Placement tp2 = qwen8u8k-pr1-half.sh's (--instance 2,4); tp4 = --instance 1,2 with the
nightly's own socket-1 core lists (+72 from round 1's socket-0 lists).

Review (workflow, 99 agents, 6 lenses x 3 skeptics): 14 confirmed, all in abort/relaunch
paths, none in the measurement path. Traps worth remembering for the next campaign script:
- bash runs the EXIT trap on SIGTERM but the foreground child survives; `timeout` puts its
  child in its own process group, so a group kill misses runtron/harness: finish() must
  kill_ours by absolute path, WAIT until gone (fuser says "mapped" otherwise), then remove
  our slice files. Same gap existed in g1-campaign.sh finish().
- background subshells (watcher, rinzler via exec, runtron subshell) inherit the campaign
  flock fd: close it (`exec {CAMPAIGN_LOCK_FD}>&-`) or an orphan holds the lock forever
  after a kill -9; the watcher must `kill -0 $$` and exit when the main shell is gone.
- distinguish "stopped" (watcher) from "start-failed"; retry stopped CI cells (G1's rc 2).
- attempt logs: continue numbering across relaunches (ls | wc -l), never overwrite.
- summarize: keep per-request generated-token counts and flag EARLY-STOP (runtron has no
  --dont-stop; a stop token ends one user early and inflates the others' TPS).
- pgrep self-match, second form (bit at 11:32Z, campaign exited on its own duplicate-instance
  check): `others=$(pgrep -f PATTERN | grep -vx "$$")` finds the $(...) subshell AND the
  not-yet-exec'd pipeline members (forks of bash with the campaign's command line). Run
  pgrep directly from the main shell into a temp file, then filter $$. Verified detached.
Refuted (not defects here): guard not user-filtered, single-shot takeover, no deadline,
launch.sh pgrep matches an editor of the file, stale status line while guard refuses.

**Why:** the campaign pattern (waiter + takeover + guarded cells + watcher) is reused every
week; these abort-path traps recur in every fork.
**How to apply:** fork exec/p0perf-20260911/ (not G1) for the next our-half campaign; the
report generator gen_report.py reads summary.json and draws per-test dumbbell panels.
Related: [[more-testing-round1]], [[3bda-shared-with-bill]], [[g1-store-cost-campaign]].
