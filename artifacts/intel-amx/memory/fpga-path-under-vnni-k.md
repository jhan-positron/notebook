---
name: fpga-path-under-vnni-k
description: 2026-09-16 verified answer to "does the VNNI K layout of PR 4424 affect the FPGA attention path": single consumer gof::populate made layout-aware, gate/concurrency facts, the one FPGA measurement, CI gap, open items
metadata:
  type: project
---

Question (jhan, 2026-09-16): does PR 4424 (TRON_K_VNNI) affect FPGA attention? Answer: no functional
impact found; cost unmeasured; no CI has run the VNNI build on an FPGA.

Verified facts (300-agent trace + 3-lens adversarial verify, head ff680c8020, base c7844ca2ce):
- The FPGA reads host K only through gof::populate -> page_info::k_head_fn -> shuffle_k_entry.
  The PR rewired k_head_fn (full.hpp ~2644) to page::get_k_row (k_vnni::gather_row) into caller
  scratch; gof.cpp gained k_scratch. DMA (shard::xfer_gof) reads the hwcacheblock only. HBM format
  and h/pos, h/libpos.hpp, lib, fpga-reg, h/tron/hardware are outside the diff.
- Gate consistency: a HW slot must equal hardware_attention_geometry.kv (kv_cache.hpp:404-416);
  accessors enforce geometry (static_assert / TRON_ASSERT). layout_on = head_size == 128 only;
  kv_mul is not in the gate (qwen-3-30b-a3b kv_mul 8 gathers too). 64-dim heads row-major.
- Completion guards unchanged (kv_saves_, save_count); shared block save marks complete after all
  helpers leave; masked stores never write another token's lane. populate runs on attention workers
  (4 GOFs per job) and the remainder on the forward thread before logits (inside TTFT).
- CPU-scored share of an FPGA run (positions 0-126 + tail tokens not yet in HBM) uses qk_group /
  qk_vnni_128x4; TRON_AMX_DISABLE=1 does not restore the row-major dotter (issue #4444).
- Only FPGA measurement: exec/results/vnnik4-models-20260915 (cell=fpga, qwen-3-4b tp2, prompt
  1024, USE_HW_ATTN unset, base 544ca05c7a vs VNNI dc950be5f2 pre-rebase, staging code identical to
  head). Smoke 1u greedy 128 tokens identical 128/128, TTFT 0.427->0.416 s, decode 223.7->222.8
  tok/s. Cell 8u 256 tokens: TTFT 3.155->3.162 s (+7.6 ms), 125.39->123.62 tok/s/user (-1.4%). n=1.
  NOTE: exec/results/vnnik4-20260915 (no "-models") has NO fpga cell.
- Gather cost: 64 cache lines per (token, KV head) vs 4; design est. 1 us/GOF/layer = est. 9 ms per
  1024-token prompt over 36 layers; never measured (perfetto spans gof_populate, wait_coop_gof exist).
- CI gap: gcp-nix.yml (the PR lane) builds without TRON_K_VNNI/TRON_AMX_DISPATCH; the legacy
  cmake-single-platform.yml has the flag but only workflow_dispatch/workflow_call; PR is draft with
  "Skip benchmarks" and no "Run CI" label, so GCP Nix run 35046296975 at head skipped Build Tron /
  Test host / Test FPGA. Zero reviews/comments on PR 4424 as of 2026-09-16.
- Gaps: no unit test asserts staged K bytes through the real full.hpp lambda (gof tests use synthetic
  buffers); no FPGA run at ff680c8020 or vs main base; page relocation + VNNI untested.

**Why:** jhan asked; likely reviewer question. **How to apply:** cite these facts; to close, run FPGA
cells base(main) vs head with >=3 paired reps + token compare + perfetto spans; add a staged-bytes test.
Related: [[vnnied-k-in-place-project]], [[vnnik6-kvmul8-campaign]], [[amx-ci-coverage-facts]].
