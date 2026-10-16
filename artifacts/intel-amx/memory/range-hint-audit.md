---
name: range-hint-audit
description: "2026-09-10 audit of range_hint (ranged-mask bookmark) in the PR1 AMX path for Ben's comment r3973407196: safe, returns the hint unchanged = dotter's value; page PR1/reviews/range_hint.html; measured range_cut data location; open 128-query prefill-pass puzzle"
metadata: 
  node_type: memory
  type: project
  originSessionId: 4522d927-a06a-4a4b-9642-e7b1bb418a38
  modified: 2026-09-10T17:51:26.330Z
---

Ben's PR #3879 comment r3973407196 (2026-09-09) and the AMX walkthrough call of
2026-09-09 (Google Doc 1S-vphIbaMq0oVNNGto3XwafFVagWNENTwFxH0-ZJUQA, 00:52-00:54)
asked whether the AMX path must "handle range_hint" too. Answer page:
PR3879/new-PRs/PR1/reviews/range_hint.html (2026-09-10, audited at 26a0338c3b; artifact
https://claude.ai/code/artifact/ddceb70f-c833-402d-bf05-d7f6229cb8e5). Follow-up the same
day: jhan reworded the is_dense_amx_page sliding-window clause ('the whole page is inside
the query's sliding window'), committed 339dde7fe7 and pushed together with the peer
session's attn_accum commit 752e9f571a; then 524c510609 added the comment above the AMX
return (why range_hint is returned unchanged). PR head = 524c510609 (2026-09-10 15:20 PT).
Ben's GitHub sentence 'make sure that we shouldn't be handling range_hint in the AMX path
as well' = hedged idiom for 'check whether the AMX path also needs to advance it' (transcript
00:52/00:54 confirms); jhan's draft reply wording agreed 2026-09-10.

Verified facts (line numbers at 26a0338c3b):
- range_hint = the cached token_range pointer for find_range(tok, hint)
  (ranged_mask.hpp:240-264: hit -> walk <=4 -> binary search). It is validated
  on every lookup; a stale hint costs time, never a wrong range.
- is_dense_amx_page (self_attention.hpp:1440-1451) requires at_offset(63) <
  range.tok_hi; page entries are consecutive token_ids (kv_cache.hpp:1231), so
  a dense page lies entirely inside the hinted range. The dotter advances the
  hint only at kv_idx >= tok_hi (1623), which cannot fire for such a page, so
  the AMX return {64, range_hint} (1597) equals the dotter's return; the caller's
  page_end_hint sequence (1386) is identical AMX on/off. No other hint consumer
  changed (model.hpp, common.hpp not in the PR1 diff).
- Ranged-mask construction: every query token creates a range boundary
  (build_edge_ranges, src/tron/models/ranged_mask.cpp); stored tokens with no
  query in the pass share one range. So in prefill only the pages holding the
  pass's own query tokens have boundaries inside (fallback cause range_cut);
  decode never has range_cut (only the partial tail page).
- Measured per-cause fallback counters: exec/results/fallback-20260901/
  fallback.txt (fence branch 3cd2670df1, qwen 1u mirror arm): prefill range_cut
  60.00 / 9.09 / 2.33 % at prompt 256 / 2048 / 8192; decode range_cut 0.
  The counts are reproduced to the digit by assuming 128 query tokens per
  prefill forward pass (history pages dense, two query pages cut).
- OPEN: where the 128-query-per-pass prefill split comes from was not found in
  the scheduler (qwen plugin max_minibatch_size = 1024; chunk_evenly in
  model.hpp:180-250 splits by max_minibatch_size and halves a lone chunk).
  Does not affect the safety argument.
- TTFT: round-1 canon -8.9%/-3.6% vs off, mirror +13.1% vs off; the hint code
  is identical in both arms, so the hint is not the mirror TTFT cause.

Verification (workflow wf_a7b37a5f-ba6, 61 agents): C1-C6 (whole page in range,
hint return, visibility, window, count, scope) not refuted by any of 3 lenses;
wording traps caught: "same code" (fence gate is inline, PR1 a helper -> say
"same five conditions"), fallback shares are inferred for PR1 (measured mirror
arm only), TTFT argument must cite 60d66d9c04 inline predicate (is_dense_amx_page
did not exist there; mirror build had an extra plane-null check + other packer),
percentages hold for qwen/llama only. Ben's call premise "we won't mix AMX
attention" is false: paths mix per (query, page) pair. Third boundary source:
full.hpp:1791-1826 split_range_at (HW attention on only). token30 memory also
saw 128-token prefill chunks (2026-08-30).

**Why:** Ben's concern mixes the mask's correctness role with the hint's
performance role; the page separates them so the same question is not re-asked.

**How to apply:** when the AMX gate or the dotter walk changes, re-check that
the gate still implies "no boundary inside the page" before trusting the
unchanged-hint return; proposed host test (not written): two ranges over one
full page in t_amx_dispatch_dtype.cpp, expect 0 kernel calls. See
[[pr3879-split-progress]], [[amx-vs-avx-sense]] (section 7.7 of that page).
