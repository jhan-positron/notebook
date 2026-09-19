---
name: nightly-vs-ours-tps-context
description: "2026-09-11/13: why the nightly CI's qwen TPS (185.4 tp2 / 147.2 tp4) differs from our one-engine CI-harness cells (48.8 / 72.8 off): same 8 users, but 4 / 2 engines behind the Caddy proxy (2 / 4 users per engine) + FPGA attention; verified facts, corrections, open items"
metadata:
  node_type: memory
  type: project
  originSessionId: 0547e267-a1b4-467d-949d-75e55bc8877e
  modified: 2026-09-13T06:39:50.853Z
---

Question (jhan 2026-09-11 17:35 UTC): why does the Slack line
`ingested-qwen-3-4b-instruct-2507-tp2 @8u per machine: 185.38 TPS / 175.00 threshold`
differ from our CI-harness cell (48.8 off / 55.6 on) of Friday-morning-CI-results.html?
Answer given: users PER ENGINE, not the user count. Verified 2026-09-13 by a 17-agent
adversarial check (journal in session 0547e267, workflow wf_01d21805-c56):

- Same 8 users in total on both sides (nightly Config n_users=8, log lines 2006/2165;
  scripts/perf.py nominal_users 8; every cell of ours users=8).
- Nightly engines: 4 for tp2, 2 for tp4 ("All 4/2 inference engines are running",
  "All 4/2 Caddy upstreams are healthy") behind platformd's Caddy reverse proxy at
  http://delphi-3bda.positron.internal/v1. Per-user "Done" lines show two speed levels
  (tp2: ~193 and ~177 TPS; tp4 rounds split 4/4) with EVEN counts per round -> consistent
  with 2 / 4 users per engine and engines running at two speeds (cause unknown). The
  proxy's lb policy is not in any local file (open: curl localhost:2019/config on 3bda).
- Users-per-engine explains 67-76 % of the tp4 log-gap and only 42-59 % of the tp2 gap;
  the tp2 residual (x1.6-2.0) = FPGA attention + CPU attention at tp2 has only 28 app cores
  (vs 56 at tp4). No qwen tp2 2-user measurement existed before 2026-09-13.
- FPGA attention in the nightly: inferred until 2026-09-13, then supported by jhan's paste of
  /etc/rinzler/instance-1.env (no USE_HW_ATTN; tron compiles ingested models with
  force_hw_attn, so unset = FPGA attention). Production env also: TRON_USE_SPECULATION=0
  (the workflow exports SYSTEM_CI_SPECULATION=0 -> posadm config.set), CPUAFFINITY=73,217,74,218
  for the tp4 socket-1 engine, RZ_CLI_ARGS byte-identical to our rz.sh tp4 placement,
  RZ_TASK_GROUPS=2 (platformd-only, not read by tron). No TRON_LOG_LEVEL -> tron default
  = debug (src/system/spdlog.cpp:39-41), the same as our pinned debug.
- CORRECTION to the 09-11 answer: the Slack "175.00 threshold" is the static goal table in
  scripts/system_ci.py get_goal() (granite_rapids_72_rinzler: tp2 175.00, tp4 135.00; the
  nightly ran systems_test efb2d985). thresholds/system_ci_perf.yaml (176.55 -> 178.75 on
  09-11) feeds a separate "YAML THRESHOLDS" Slack section. Build claim was right
  (apt tron 2026.09.11-632c6181 = main head vs our 47f6f2dceb).
- Harness code identical between 470aca1 (ours) and efb2d985 (nightly): testlib/tps.py no
  diff; perf.py only p05 additions.
- Users sweep reference (2026-09-08 g1, qwen tp4 canon, CPU attention, one engine):
  1u 189.3, 2u 159.3, 4u 121.8, 8u 78.5 TPS per user.

**Why:** this comparison will come up every time a nightly number is set next to ours.
**How to apply:** say "same 8 users, different users per engine"; cite the two-level Done
lines as the evidence for even spread; point at the fpga arm of [[p0perf-20260913-campaign]]
for the same-binary link. Related: [[p0perf-20260911-campaign]], [[more-testing-round1]].
