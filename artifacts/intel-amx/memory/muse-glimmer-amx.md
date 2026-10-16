---
name: muse-glimmer-amx
description: "2026-10-16 report muse-glimmer-amx.html (intel-AMX top level): Muse Glimmer 30B = production ingested plugin, shape 32 q heads / 2 KV heads / head 128 = kv_mul 16; 39 of 52 layers are sliding-window (2048) and ingest marks them software_only -> CPU AVX always, only 13 full layers go to the FPGA; AMX support = generalize the 128x4 kernels to 16 live tile columns"
metadata:
  node_type: memory
  type: project
  originSessionId: f08a968d-af8f-4685-a0aa-76d2fec72264
  modified: 2026-10-16T19:32:29.273Z
---

Verified at tron main 6198824246 (2026-10-16):
- Model: config/models.yaml:684-712, tags production+test since 003695e390 (2026-09-14), executors tp1/2/4 (+ permuted),
  weights positron-ai/meta-models--Muse-Glimmer-30B-ingest-best-gptq. Nightly: perf cell tp4 8u prompt 1024 gen 1536
  (systems_test perf.py:218-226), MMLU Pro threshold 64.5, TPS goals placeholders 1.00. TPS unknown from here.
- Shape (HF config on 3bda + generated header pr3660-regen/out-pre/ingested_meta_models_Muse_Glimmer_30B.hpp):
  52 layers, pattern S S S F x13 -> 39 sliding (window 2048 = 32 pages) + 13 full; 32 q heads, 2 KV heads, head 128,
  kv_mul 16; hidden 6656; vocab 202048.
- AoF premise is wrong for 75 % of layers: ingest marks sliding layers software_only (AttentionHardware.hs:14-18,
  TronCheck.hs:1067-1069; kv_cache.hpp is_hardware_attention_candidate rejects sliding; model.hpp static_assert);
  header has 39 software_only / 13 kv_slot_candidate. force_hw_attn=true (TronCpp.hs:242) -> USE_HW_ATTN default on
  for the 13 full layers only.
- K+V bytes per user per decode step (computed): CPU sliding layers 81.8 MB at window limit (40.9 MB at ctx 1024);
  FPGA full layers 34.1 MB at ctx 2560; llama-8b all-CPU at ctx 1152 = 151 MB.
- kv_mul 16 = the full-tile shape: Q is the B operand with 16 columns (4 live today), P is the A operand with 16 rows
  (4 live); tile multiplies per page unchanged (16 QK + 16 PV); AVX MACs per page grow 4x (65,536 -> 262,144).
  Changes: shape_ok (amx_attn_iface.hpp:149-151), pack_q loop, qk transposing store (rows 0..3 -> 16), PV P-conversion
  loop, names/Note text, t_amx_numerics cases; caller buffers already geometry-sized (s_pages<kv_mul,64>, amx_o 16x128,
  amx_qpack slot 4096 B). No new work: sliding-window dense predicate (self_attention.hpp:1711-1722), K row-major on
  main (VNNI-K PR 4424 not merged), deb preset TRON_AMX_DISPATCH ON (CMakePresets.json:68).
- gemma-4-31b for contrast: head 256, 16 KV heads, kv_mul 2, 50 sliding (1024) / 10 full.

**Why:** jhan asked 2026-10-16 whether AMX matters for Glimmer ("it is AoF, isn't it?"); the answer (mostly CPU) will
recur for every sliding-window ingested model.
**How to apply:** next step = measure the attention share (runtron Glimmer tp2 8u prompt 2048, TRON_ATTN_STATS=1 +
perfetto) before implementing the 128x16 shape; then A/B with TRON_AMX_DISABLE=1. Related: [[vnnik6-kvmul8-campaign]],
[[aof-amx-question-20260925]], [[single-attention-measurement]], [[amx-ci-coverage-facts]].
