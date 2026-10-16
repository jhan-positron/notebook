---
name: mirror-write-ok-unpack
description: "2026-08-28 verified facts behind the mirror_write_ok comment (amx_attn_iface.hpp:159-173) and the K-mirror arena Note bullet (kv_cache.hpp:581-591); why-only replacement options offered, none adopted yet"
metadata:
  type: project
---

Unpacked 2026-08-28 for jhan (page PR3879/unpack-mirror-write-ok.html, artifact
https://claude.ai/code/artifact/e5c4ae20-249d-4040-a519-c94daeba4807; claims, 7-agent verdicts,
fig2.svg in PR3879/unpack-mirror-write-ok/). Facts verified at tron-amx 1d158249e2:

- mirror_write_ok = eligible minus the kv_mul==4 term (repeats the HEAD_SIZE_128 literal, does
  not call shape_ok). Only production caller: model.hpp:2772-2773 (save_k_impl), `if constexpr`.
- Why: valid_attention_operation_descriptors allows one writer + read-only readers of other ratios
  on one kv_slot (kv_cache.hpp:301-308; KV geometry must match, 324-328); the READER's ratio decides
  the mirror read (self_attention.hpp:1359-1361, 1507-1509). Codex P1 (2nd finding), commit
  323b9d5499. Permitted but unused: all 17 registered plugins have 1 writer/slot, writes_kv true
  everywhere, one head size per plugin (parsed gen/src/tron/h/tron/plugins/*).
- The mirror_arena_ null test is in mirror_at_storage:1291; set_k_mirror (1628-1636) tests the
  returned pointer. copy_storage_slot (1966-1975) and fill_storage_slot rebuild planes of EVERY
  head size, so "save_k does not write head-64 planes" must not become "never written".
- The "reader's ratio, not writer's" reason is written in 4 places (iface, model.hpp:2764-2771,
  kv_cache.hpp:621-625, bullet 585-587) - Rule 7 duplication flagged to jhan.
- 2026-08-30 Q&A added to the page (jhan asked how one layer can be AMX-ineligible and the next
  eligible): kernels are per operation; registered example gemma_4_31b_it / gemma_4_12b_it_permuted
  alternate two geometries in a 5-local(sliding window 1024)+1-global layer pattern (op->kernel
  string 000001..., parsed from gen plugins); no registered plugin mixes a head-128 ratio-4 kernel
  with anything, so the AMX instance is future-only; the shared-slot case needs cross-layer KV
  reuse on top (IR permits, Loopy never emits - 323b9d5499 message).
- Offered replacements: question-form 4-liner (recommended), 3-line shortest, history, a code
  change `return eligible<query_scalar_t>(model_head_size, GROUP_HEADS_4);` with 2-line comment,
  and a 5-line Note bullet without the write-gate clause. jhan has not chosen yet.

**Why:** jhan asked for why-only comments (rejected mechanics in comments, see
[[amx-mirror-aware-cache-unpack]]); if asked to apply one of these, re-check line numbers and keep
the t_llama_unit.cpp:908-913 STATIC_REQUIREs green. Related: [[plain-words-comment-register]],
[[codex-review-loop]].
