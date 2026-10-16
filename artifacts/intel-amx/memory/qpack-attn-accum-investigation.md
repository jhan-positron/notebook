---
name: qpack-attn-accum-investigation
description: "2026-09-10 Ben's PR3879 thread r3973410716 (amx_qpack thread_local vs attn_accum member): jhan chose option B; commit 752e9f571a on jhan-amx-p0 (LOCAL, not pushed), tree = tested prototype; reply text reviews/amx_qpack-reply.post.md not posted; page reviews/amx_qpack-2-attn_accum.html"
metadata:
  type: project
---

Ben (r3936949728 2026-09-04, r3973410716 2026-09-09, meeting 2026-09-09 00:29-00:38) wants the
AMX packed-Q buffer moved from `thread_local std::vector<amx_qpack_slot>` inside apply_page_range
into attn_accum as `std::array<amx_qpack_slot, max_minibatch_size>`. Our earlier reply
("per (token, kv_head)"; "ownership unchanged") was a scope statement, not a technical reason;
Ben could not follow it and said so.

Verified 2026-09-10 (9 claims x 2 refuters, workflow wf_63e1a5b3-ebf):
- A pack lives one apply_page_range call (one kv_head), packed once per (token, call), read only by
  the QK kernel, never by the join. Its index space = attn_accum's (batch_job_ix). Nothing blocks a
  member (attn_accum never copied/moved/memset; hw_attn grows by emplace_back; value-init zeroes).
- attn_accum instances = num_workers (55 under --instance 1,2 on the 6962P) + 2 per hw_attn_results
  (0 for CPU-only attention). Inline sizeof 35,840 B (llama-8b) / 286,720 B (Qwen3-4B); v_stars are
  16-B handles to 8 KiB DMA-pool blocks (bf16 executors), allocated eagerly at state ctor
  (55 x 128 = 7,040 allocations). Host executor: inline floats, 2,130,944 B.
- Ben's array adds 512 KiB (llama plugin) / 4 MiB (ingested) per instance = 27.5 MiB / 220 MiB per
  model state here, in eligible and non-eligible models alike. Eligible: 32/8/128 on bf16 executors
  (llama-3.1-8b, llama-3-8b, mistral-7b, ministral-8b, mixtral-8x7b, Qwen3-4B).
- thread_local cost (objdump of 2026-08-31 runtron): local-exec TLS, 7 TLS instructions per call,
  0 in the loops; 24+8 B per thread per instantiation (74 instantiations); __cxa_thread_atexit
  registered even when AMX off. Attention-worker<->thread mapping can shift between passes
  (recommend_n_main_helpers), so thread_local buffers spread over threads in long runs.

Prototypes (branch jhan-amx-qpack-accum-proto, worktree ~/workspace/ai-runs/tron-qpack-accum, NOT pushed):
- B = std::vector member sized on first use: 5b5eeca67f. DISPATCH=ON build 126 s, t_amx_numerics /
  t_amx_dispatch_dtype / t_llama_unit all pass; DISPATCH=OFF t_llama_unit passes (exec/logs/split-qpackB*.txt).
- A = std::array member: 250ff8204d, DISPATCH=ON, same 3 tests pass (split-qpackA.txt). Should get `{}` init.
DECISION 2026-09-10: jhan chose B and asked to proceed. Commit 752e9f571a on jhan-amx-p0 in ~/workspace/tron-amx
(cherry-pick of 5b5eeca67f + jhan's short comment 4a676753b6, squashed; tree identical to 4a676753b6). NOT pushed.
752e9f571a VERIFIED on 3bda 2026-09-10: DISPATCH=ON build 126 s, t_amx_numerics/t_amx_dispatch_dtype/t_llama_unit
all pass; DISPATCH=OFF t_llama_unit passes (exec/logs/split-qpackB-final*.txt). Reply text (not posted):
PR3879/new-PRs/PR1/reviews/amx_qpack-reply.post.md. triage.json GH-3936949728/GH-3973410716 = done; thread-map row 3
rewritten (the posted GitHub thread-map comment 5578693039 still shows the old row). Not measured: decode A/B.
jhan's comment-wording feedback: short struct comment (what it is, how indexed); keep zero-fill/growth facts at the
resize() call site; "cannot read ... as they are stored" must keep the qualifier.

**Why:** Ben's action item from the meeting was "determine if qpack can be integrated into attention
accum and provide reasoning if it cannot"; the answer is yes, so PR 1 needs the change or Ben's OK.
**How to apply:** remaining outward steps for jhan (or on his say-so): push jhan-amx-p0 (752e9f571a, fast-forward),
post amx_qpack-reply.post.md on r3973410716, edit thread-map comment 5578693039 row 3, resolve the thread. Related:
[[pr3879-split-progress]], [[breakup-pr3879-plan]], [[debug-code-new-branch]].
