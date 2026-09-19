---
name: p0perf-20260913-campaign
description: "DONE 2026-09-13 12:50Z (0 failures): Friday's runtron cells + CI-harness cells in the nightly's per-engine layout on our half (tp2: 2 engines x 2 users at once; tp4: 1 engine x 4 users), arms off/on/fpga, head 544ca05c7a; goal = predict runtron-vs-CI TPS/TTFT after AMX is merged and enabled in CI; scripts exec/p0perf-20260913/, results exec/results/p0perf-20260913/"
metadata:
  node_type: memory
  type: project
  originSessionId: 0547e267-a1b4-467d-949d-75e55bc8877e
  modified: 2026-09-13T07:09:01.190Z
---

Request (jhan 2026-09-13 06:3x UTC): "schedule a run after CI completes, re-do the tests as
last time (Friday-morning-CI-results.html), make sure CI tests have same config as nightly CI.
The goal is to predict TPS and TTFT comparison between runtron and CI after we merge AMX and
enable it in CI." Decisions (AskUserQuestion, 06:4x UTC): half-machine layout with the
nightly's per-engine load (not the whole machine); add the fpga arm.

Design (exec/p0perf-20260913/{campaign.sh,rz.sh,launch.sh,combine.py,summarize.py}, fork of
p0perf-20260911): TIP 544ca05c7a954f892f0e23ccb465f74ad46bea5e (jhan-amx-p0 = merge of main,
CI green); worktree /var/tmp/jhan/tron-p0perf13, binaries runtron.p0perf13 / rinzler.p0perf13.
- runtron: tp2 (--instance 2,4) / tp4 (--instance 1,2), 8 users, prompt 1024, 256 tokens,
  off/on, RT_REPS=6 (Friday's cells unchanged).
- CI-config cells: tp2 = engines 2a (--instance 2,4, cards 90/93, port 13100, launcher cores
  73,217) + 2b (--instance 3,4, cards b9/bc, port 13101, cores 74,218) started together, one
  st_perf.py client per engine with --users 2 at the same time; tp4 = engine 4 (--instance 1,2,
  port 13100, cores 73,217,74,218 = production CPUAFFINITY) with --users 4. combine.py pools
  the per-engine perf-e<k>.json into perf.json the way the nightly pools 8 users. Clients pinned
  to cores 87-95,231-239 (no engine uses them). CI_REPS=3, arms off, on, fpga interleaved.
- fpga arm = USE_HW_ATTN unset (FPGA attention from query position 127 on; positions 0-126
  stay on CPU attention, hw_attn_config.hpp engagement point) AND TRON_AMX_DISABLE=1 so that
  CPU share runs on AVX as main (no AMX code) does. Review finding: without the kill switch the
  fpga arm would still run AMX in that share.
- 2a/2b placements and launcher cores are DERIVED by halving the production tp4 file
  (/etc/rinzler/instance-1.env pasted by jhan 2026-09-13 06:11 UTC); asked jhan to paste
  instance-*.env to confirm. Production env matched: TRON_USE_SPECULATION=0, RZ_FUSE_MOUNT_PRESCOPED=1,
  RZ_ENABLE_SAVE_TOKENS=1, no TRON_LOG_LEVEL (= debug default, same as ours).
- Deliberate differences from the nightly (header of campaign.sh): no Caddy proxy hop; client
  on the DUT (pinned); stagger per client; same 20/40 prompt conversations across the two tp2
  clients (harness seeds round*users+user); clients not round-synchronized.
- Review (workflow 48 agents): 13 confirmed, all applied: fpga kill switch; anchored instance
  pgrep '(^|/)bash /full/path/campaign[.]sh$' (an editor naming the file used to count);
  rz_ready watches every engine pid and tails logs on failure; break at first engine failure;
  client wait loop polls and kills the sibling client when one fails; RZ_HP_SNAPPED flag
  (empty /dev/hugepages made the snapshot repeat); take_guard logs whose runtron blocks;
  header wording (stagger per tp, prompt sample, sync).
RESULTS (11:17-12:50 UTC, marker ok, machine clean; runtron 6 reps, CI 3 reps):
- runtron 8u: tp2 off 70.23 -> on 79.53 (+13.2%), TTFT 3.933 -> 3.148 s (-20.0%); tp4 96.74 -> 103.35
  (+6.8%, per rep +2.8..+12.4, sd 3 = noisy as Friday), TTFT 2.458 -> 2.199 (-10.5%).
- CI nightly layout: tp2 (2 eng x 2u) off 140.61 / on 152.46 / fpga 192.11 TPS; TTFT 909 / 727 / 761 ms.
  tp4 (1 eng x 4u) off 114.77 (sd 4.5) / on 123.89 (sd 2.9) / fpga 153.98 (sd 6.0); TTFT 952 / 856 / 839.
- on vs off: +8.4% / +7.9% TPS, -20.0% / -10.1% TTFT. on vs fpga (= nightly change if qwen goes to CPU
  attention with AMX): -20.6% / -19.5% TPS, -4.4% / +1.9% TTFT -> the nightly's qwen thresholds
  (static 175 / 135, yaml 176.55/178.75) would FAIL after such a switch.
- Fidelity: fpga arm vs nightly 09-11: 192.1 vs 185.4 (+3.6%), 154.0 vs 147.2 (+4.6%) -> layout reproduces.
- CI / runtron ratios: TPS tp2 2.00x (off) 1.92x (on), tp4 1.19x / 1.20x; TTFT tp2 0.23x, tp4 0.39x.
- Both tp2 engines agree within 0.3% (no two-speed engines on our socket). One client-side burst sample
  appeared in the fpga arm without a proxy. Report PR3879/new-PRs/PR1/Sunday-CI-layout-results.html
  (gen_report.py v2 after a 132-agent verification: 385+470 numbers recomputed, 0 data errors, 59 wording/claim/figure findings applied; published https://claude.ai/code/artifact/c0627a97-9a89-4279-b459-93ceff390350, republish with the same file path or url=). Production unit-file paste archived as exec/results/p0perf-20260913/platformd-instance-1.env.txt. Open: TTFT not reproduced (our fpga arm 761/839 ms vs nightly 507/635; hypothesis = arrival stagger 0.4 s between engine-mates in the nightly; test = one cell with stagger 0.4 s); nightly tp2 has two engine-speed groups (193/177), ours only the fast one (hypothesis: socket 0 slower).
- Queued 2026-09-13 ~07:10 UTC via launch.sh (waiter polls the lease; nightly run 34735975511
  busy since 03:38 UTC, expected clear ~11:30 UTC). Expected duration ~2.5 h. Log
  exec/logs/p0perf-20260913.log, status .status, marker .done. Report page to write:
  PR3879/new-PRs/PR1/ (name to be chosen; generator fork of exec/p0perf-20260911/gen_report.py).

**Why:** this is the first measurement in the nightly's own per-engine layout; the fpga arm is
the same-binary link between today's CI numbers (185.4 / 147.2) and post-merge AMX numbers.
**How to apply:** compare fpga arm with the nightly's 2026-09-11 numbers first (fidelity check),
then on-vs-fpga = predicted CI change, on-vs-off = AMX gain, runtron vs CI = the ratio jhan
asked for. Related: [[nightly-vs-ours-tps-context]], [[p0perf-20260911-campaign]],
[[3bda-shared-with-bill]].
