---
name: issue-4500-fpga-attention-vnni-tps
description: positron-ai/tron issue #4500 (filed 2026-09-18, assigned jhan) tracks the qwen-3-4b FPGA-attention decode TPS loss under PR 4424's VNNI K layout (-5/-11 % tp2/tp4 in the nightly layout, tp4 flips the CI threshold)
metadata:
  type: reference
---

Issue: https://github.com/positron-ai/tron/issues/4500 "qwen-3-4b with FPGA attention loses 5 to 11 % decode TPS
under the VNNI K layout of PR #4424". Filed 2026-09-18 20:35 UTC by Claude on jhan's request ("please file this issue,
assign to me"), assignee jhan-positron. Body = VNNIed-K-in-place/status/issue-fpga-attention-vnni-k-tps.body.md
(draft: status/issue-draft-fpga-attention-vnni-k-tps.md). No names/mentions in the body (project rule).

Data in it: 09-15 runtron n=1 tp2 -1.4 %; 09-16 attribution block D (PR 4424 step alone) tp2 -2.2 % (t -6.5),
tp4 -9.7 % (t -2.9), n=6; 09-18 ci-mimic nightly layout tp2 186.13->176.75 (-5.0 %, t -7.5), tp4 149.94->133.44
(-11.0 %, t -10.2; threshold 135 flips PASS->FAIL), per-round means, TTFT caveat (client host load), AMX probe 13.7 G
cycles, tokens identical 128/128 (09-15). Hypothesis (unmeasured): gof::populate gathers K rows from the VNNI layout
(64 cache lines vs 4 per token-head) on every decode step; test = perfetto spans gof_populate / wait_coop_gof base vs
head. Options: row-major staging copy at save time; tuned gather; gate layout off for FPGA-attention models.

Before this, nothing tracked the loss: #4444 = token divergence + kill switch, #4347 = enable AMX in CI, the PR 4424
body only had the -1.4 % n=1 number and no open item for it.

**How to apply:** cite #4500 in PR 4424 discussions and reports; when the perfetto measurement or a fix lands, update the
issue rather than a new one. Related: [[vnnied-k-in-place-project]], [[fpga-path-under-vnni-k]], [[ci-mimic-20260918-campaign]].
