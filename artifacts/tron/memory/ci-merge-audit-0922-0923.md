---
name: ci-merge-audit-0922-0923
description: "2026-09-23 audit of the 32 tron merges between nightly packages 2026.09.18-3faba6d0 and 2026.09.23-5cf65b92 (first AMX nightly); which merges move which CI rows, new tp4 baselines, controls to use"
metadata:
  node_type: memory
  type: project
  originSessionId: aa64362c-2974-4c1c-9b2c-a2bba37bc1ef
  modified: 2026-09-23T17:54:43.742Z
---

Audit done 2026-09-23 (report: ~/workspace/intel-AMX/CI-test/status/CI-merges-20260923.html,
artifact https://claude.ai/artifact/XfjSvRGsrojxBN2qyHmc2t; scripts and numbers.json in
~/workspace/intel-AMX/exec/ci-merges-20260923/).

- AMX row (llama-3.1-8b tp2, 32 users, prompt 4096): CI 28.25 -> 32.49 TPS (+15.0 %), our same-code
  A/B 09-20 +14.0 %, AMD andoria-b1a3 same packages -0.3 %. Residual +0.29 TPS for other merges.
- Only #4534 (timed-wait atomic counters removed, TRON_MWAIT_STATS default OFF), #4205/#4203 (model code
  compiled per model family, flags copied) and #4456 (pin-position records) can change that row's code.
- #4516 "slice cost data granite_rapids_6962p" is CI unit-test timing (config/test-benchmarks.json), not a
  runtime setting. The morning page (CI-AMX-row-20260923.html) wrongly listed it as a candidate.
- Intel-only tp4 jumps on 09-23: 70b tp4 30.25 -> 31.33, qwen-3-4b tp4 145 -> 172, gpt-oss-120b tp4
  107 -> 119 TPS. Leading hypothesis #4534: Intel RTM wait passes end every 2048 TSC cycles, so a 10 us
  wait updates the shared counters ~15 times vs 2 on AMD MWAITX (est.). Unconfirmed; test = rebuild with
  -DTRON_MWAIT_STATS=ON and run 70b tp4 alternating.
- #4258 (FPGA attention streaming join) sped up qwen-3-4b and gpt-oss-120b on both machines. In CI, FPGA
  attention is on only for these generated models (rinzler journal "HW attention enabled for model").
- Mixtral TTFT +2.4 % on Intel only (AMX-shape model); gemma-4-31b -1.8 % Intel / +1.1 % AMD: unexplained.

**Why:** the pre-09-23 thresholds and ranges for tp4 rows no longer describe the new package, and the
controls used here (AMD CI machine, same-package nightly ranges) are the fastest way to split AMX from
other merges.

**How to apply:** compare future tp4 rows against post-09-23 nights only. Use andoria-b1a3 as the
non-AMX control, but drop its 09-18 run (35302120794, cancelled, rows 20-45 % low). With 4-5 baseline
nights, "just outside the range" happens by chance about 1 in 3 times. Related:
[[3bda-ci-amx-shape-models-2026-09-18]].
