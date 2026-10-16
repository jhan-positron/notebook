---
name: g1-store-cost-campaign
description: "2026-09-08 (Tue): G1 store-cost gate campaign queued on delphi-3bda for the whole-machine window after the nightly CI + the other session's PR 0b chain, only while Bill is absent; probe commit fceeddc529 (branch jhan-dd-g1-store, env TRON_DD_G1=sonly|inplace); scripts exec/g1-20260908/; plan page PR3879/new-PRs/Tuesday-plan.html"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4cd330c4-93d0-429c-8584-0b5d34ee913c
  modified: 2026-09-08T06:30:08.150Z
---

Request (jhan, 2026-09-08 06:xx UTC = Mon 23:xx PDT): scope the tests one level above PR 0b
for the whole-machine window on delphi-3bda tomorrow morning (CI ends ~11:25 UTC; Bill usually
starts 15:00-16:00 UTC), answer "do we have enough data to call the SK series over PR 2", and
(second message) "after CI finishes and after the PR 0b test finishes, if Bill does not log in,
go ahead to execute the whole-machine tests"; (third message) write PR3879/new-PRs/Tuesday-plan.html
with next steps for PR 0b, PR 1, SK-*; PR 2 low priority, defer.

What was built (2026-09-08 06:30-07:30 UTC):
- Probe commit fceeddc529 on NEW branch jhan-dd-g1-store (worktree ~/workspace/ai-runs/tron-g1,
  base = tag pr3879-pre-split 60d66d9c04 = round 1's head). Env TRON_DD_G1: unset = mirror arm
  unchanged; "sonly" = no canonical K store, scatter into the arena only; "inplace" = no canonical
  store, scatter into the page's own K plane and the AMX kernel reads that plane (single-K storage
  proxy). Numerics wrong in probe modes; timing only. Prints "DD G1 store mode: ..." on stderr once.
  Debug code stays on this branch (rule: debug code never on jhan-amx-p0). Never merge.
- exec/g1-20260908/{g1-campaign.sh, rz.sh, g1-summary.py, launch.sh}. Campaign waits: CI lease clear
  -> stop idle production rinzler@0-3 (round-1 recipe with the traffic check) -> PR 0b chain done
  (marker exec/logs/split-PR0b-test.bench-done or its wrapper gone) -> monitor CLEAR + campaign
  guard (GUARD_EXCLUDE_USERS default, so Bill counts) -> build rinzler.g1/runtron.g1 in
  /var/tmp/jhan/tron-g1 (socket 1, ~10 min) -> qwen tp4 TTFT sweep (users 8: off canon mirror
  g1mirror sonly inplace; users 1,4: canon mirror sonly inplace) -> runtron qwen 8u/8K (canon =
  runtron.pr1amx, g1kill, g1mirror, sonly, inplace; 2 reps; August placement) -> llama tp2 sweep
  (8: off canon mirror sonly inplace; 1,4: canon mirror sonly inplace) -> canonical soak 60 min.
  Round-1 placement (socket 0, cards 38/3b/10/13) so TTFT extends round 1's table. Own 10-s watcher
  kills our rinzler/runtron when the Bill flag appears (bill-watch's kill matches only comm
  "rinzler" exactly, not rinzler.canon). Results exec/results/g1-20260908/, summary.md.
- One-core compile check of the probe passed during CI (exec/logs/g1-syntax.log, ninja rc=0, 06:27 UTC).
- VERSION 2 (07:5x UTC) after a 23-agent review + the evidence workflow's critic: order = probe builds
  (mirror ON: rinzler.g1+runtron.g1; mirror OFF: runtron.g1canon = same-head canonical for the runtron
  point) BEFORE the takeover -> waits -> 8-user cells both models first (arms canon inplace sonly
  g1mirror off mirror canon2; canon2 = in-campaign spread) -> runtron 8u/8K (g1canon g1kill g1mirror
  sonly inplace, --dont-stop) -> 1/4-user cells -> 2-user cells -> soak. Fixes: PR0b wait matches
  'split-(verify3|bench3)[.]sh PR0b-test' (bash execs the last -c command in place, so the old
  'bash -c KEEP_WT=1' anchor stopped matching when the bench started); deadline checked before the
  free test; 01:30-11:00 is a HOLD before start; flock released while waiting for Bill; kills scoped
  to our binaries by absolute path; watcher before rz_start; proof grep -m1 per fact + mode-line check;
  3 consecutive start failures end the campaign; soak cutoff; FUSE lazy unmount; health 600 s.
  v1 kept as *.v1-20260908. Harness scratchpad/g1-harness.sh passed all wait/deadline paths.
- VERSION 3 (08:3x UTC) after a 22-agent delta review of v2 (17 real findings): summary regex read ms/tok as
  tok/s (fixed: r'at ([0-9.]+) average tok/s'); paired comparison now pairs per-ROUND means (harness appends
  samples in completion order, not user order); G1_OK now from the probe worktree only (a g1canon build
  failure drops only that arm); probe-binary start failures counted separately (PROBE_DEAD skips probe cells,
  round-1 binaries' failures end the campaign); watcher keeps killing every 10 s; kills only our binaries by
  path; rz_stop and the runtron cleanup remove only OUR (-O) unmapped hugepage files (fuser cannot see other
  users' maps; dir 775 root:positron, no sticky bit); runtron output to per-run log files; bare campaign flock
  held during the socket-1 builds (the PR0b bench measures socket-1 slots too); takeover fails closed on an
  empty/failed journal read; mode-line check also for g1mirror ('unset (0)'), arena check also for sonly, with
  leading space ' 0.00 GB K mirror'; PR0b regex anchored '^bash (-c KEEP_WT=1 )?[^ ]*split-(verify3|bench3)[.]sh
  PR0b-test'. Not covered by the campaign: gate G1's second clause (save_k per-row time). v2 kept as *.v2-20260908.
- FINAL CHECK (8 agents, 08:5x UTC) on v3 found one regression I had introduced (the takeover required a
  SYSTEM_STATS line inside 10 min, but idle rinzler units log it 1.5x less often per line: 300/450/675/1013 s;
  replaced by a journal-readability probe `journalctl -n 1 -o cat`) plus: takeover cleans slice files only after a
  successful systemctl stop and by owner (positron = stopped units, ours = -O + fuser, others left alone);
  the soak kill matches by cwd under results/; summary counts RUN-FAILED/RUN-STOPPED/BINARY-MISSING attempts out;
  rinzler kill pattern also requires --port 13100. Applied 08:5x UTC; harness 12 PASS; 3bda copies match.
  TRAP learned: SYSTEM_STATS cadence is adaptive (token_stream_monitor.cpp calculate_system_stats_interval).
- exec/g1-20260908/g3-lite.sh = standalone single_k_probe.cpp on one socket-1 core (G3 indicative
  Granite Rapids point; minutes; half machine; run when socket 1 is quiet).

RESULTS (campaign ran 11:26 UTC builds -> 11:52 guard -> phases 2-4 done by 13:47; phase 5 running at 14:00;
Bill absent all morning, two 30-s python blips only): qwen tp4 8 users TTFT ms: canon 1630, canon2 1633 (0.2%),
off 1778 (round 1: 1777), inplace 1820 (+11.7%), sonly 2010 (+23.3%), mirror 2022 (+24.0%, round 1: 2009),
g1mirror 2034 (probe fidelity +0.6%). Penalty split: 64-line store pattern ~190 ms, arena placement ~190 ms,
second canonical store ~12 ms. Users curve (inplace/sonly/mirror): 1u +8.0/+16.7/+17.6%, 2u +8.5/+18.4/+18.4%,
4u +12.0/+22.5/+23.4%, 8u +11.7/+23.3/+24.0% -> mostly per-token cost, mild contention. llama tp2 8u: canon 2685,
canon2 2690, off 2784, mirror 3160 (+17.7%); llama probe arms (sonly/inplace) ABORTED at every user count:
"TRON_ASSERT(!std::isnan(elt)): Encountered NaN logit at token 0" (probe numerics reach the sampler on llama;
qwen tolerated them) -> llama gate cells missing; fix = suppress the NaN assert in probe modes on jhan-dd-g1-store.
runtron qwen tp2 8u prompt 8192 (same head): prefill s/request g1canon 62.34, g1mirror 63.31 (+1.6%), sonly 63.27,
inplace 63.01 (+1.1%), g1kill (AVX) 128.86; decode tok/s 16.92 / 18.59 / 18.61 / 18.67 / 14.22 -> the store costs
~1.5% in the long-prompt batch path but +12..24% in the short-prompt serving path (per-token prefill time there is
~4.5x smaller). G3-lite on GNR core 141 (L1-hot, 1 query): swizzled bf16 reader 182 vs canonical 222 ns/page at
visible=64 (-18%), faster at every count >= 3, slower only at visible=1 (46 vs 36-45) -> favourable, indicative only.
FINISHED 14:58 UTC marker ok (2-user cells done 14:05; soak 14:05-14:58 = 53 of 60 min, stopped by a 30-s
Bill python blip; host memory growth -0.12 GiB, 0 failed requests, 95 coherency checks). Bill worked 15:19-16:26
UTC (eoe_engine), idle after. Status page PR3879/new-PRs/Tuesday-morning-status.html (charts + plan of actions).
GATE READING: G1 clause 1 on qwen: inplace +11.7% at 8 users >> 2% -> the in-place VNNI store as prototyped FAILS
the store-cost gate in the serving path (caveat: inplace uses the faster mirror kernel, so the store cost is if
anything understated; llama not measured). PR0b chain: all three markers ok (verify, on-main, bench).

Gate reading (breakup plan 5.2, thresholds agreed by jhan 09-05): kill single-K if scatter-only
prefill or TTFT is worse than canonical by more than ~2% at 8 concurrent prefills. inplace vs
canonical isolates the store pattern; sonly vs inplace isolates the arena placement; mirror vs
sonly isolates the canonical-store-plus-reread; g1mirror vs mirror = A/A of the probe binary.

**Why:** the whole-machine window is short and jhan wants it used for the gate measurement that
decides SK vs PR 2; nothing else in the plan needs the whole machine except cost-data benches.
**How to apply:** check exec/logs/g1-20260908.status and summary.md; fold numbers into
Tuesday-plan.html and the gate decision (2026-09-16). Related: [[breakup-pr3879-plan]],
[[more-testing-round1]], [[pr3879-split-progress]], [[3bda-shared-with-bill]].
