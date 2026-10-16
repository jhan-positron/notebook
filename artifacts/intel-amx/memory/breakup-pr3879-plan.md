---
name: breakup-pr3879-plan
description: "2026-09-04/05 plan (decisions recorded 09-05) for splitting PR3879 (Ben's order) reconciled with Bill's single-K proposal: A+C with a dated gate 2026-09-16; mirror arena demoted to reference draft after round-1 TTFT/RAM findings; page PR3879/breakup-PR3879.html; 11 of 13 decisions made 09-05"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0a757d7f-8c84-4b08-a4b0-595e23118332
  modified: 2026-09-05T01:45:02.003Z
---

Deliverable: PR3879/breakup-PR3879.html (written 2026-09-04 evening PDT, also published as a
private artifact). Produced from three gpt-6-astra PAL passes (plan max / red-team high /
synthesis max; raw outputs in the session scratchpad pal-out/) plus six read-only Claude
verification agents (hunk classification, refutations, main drift, two planners).

Recommendation (Claude's, all planners converged): "A+C with a dated gate".
- PR 0 = page-share counters (~150 lines est.: header 85 + 16 hooks + CMake option + host
  test), base main, ready. PR 0b = one-line memory_order fix (Ben's comment on pre-existing
  kv_cache.hpp:487), base main. PR 1 = #3879 force-pushed and retitled, canonical kernel +
  dispatch + tests + CI flag (-DTRON_AMX_DISPATCH=ON at cmake-single-platform.yml:365-367),
  ~1,050 lines est., base main recommended (ask Ben), four topical commits. PR 2 = K mirror
  arena as a stacked draft "reference; not for review", never marked ready under this plan.
  Single-K series SK-A/B/C (350-650 / 500-900 / 400-800 lines est.) opens only after gates.
- Gate 2026-09-16 fed by G1 (VNNI store cost: save_k variants, TTFT vs 1/2/4/8 users) and
  G2 (GOF shuffle from the VNNI plane, hot/cold, byte-exact; Bill's step 3 on OUR offsets),
  G3 (AVX fallback on Granite Rapids) in week 2. GO -> close PR 2, its kernel/layout/tests
  move into SK-B. NO-GO -> PR 2 becomes interim only after TTFT root cause + fix + arena
  admission check + Wade's agreement (a new decision).

Decisive new evidence (systems-test round 1, all 12 cells done 00:40 UTC 2026-09-05,
PR3879/more-testing/round-1/status.md + exec/results/more-testing-r1/notes.md): mirror arm
TTFT +24% vs canonical on qwen tp4 (2009 vs 1618 ms; off 1777) and +17% on llama tp2 (3148 vs
2683), in all 10 rounds, A/A TTFT spread 0.2%; absent on mixtral and gpt-oss. Soak: arena
43.8-44.6 GB host RAM per tp2 engine (half the DMA KV bytes), CI soak monitor alert
"Memory Growth above 5 GiB". MMLU Pro: no detectable change (A/A spread ~1.6 points).
Candidate cause of TTFT penalty = write-through scatter during 8 concurrent prefills
(hypothesis; G1 settles it). Under single-K that scatter becomes the PRIMARY store.

Verified facts worth keeping: mirror = 1,170 non-blank lines -> 202 reusable as is / 519
adapted / 449 throwaway under single-K (classify.py in scratchpad wf/classify-mirror/);
~400 mirror lines are OUTSIDE any #ifdef TRON_AMX_K_MIRROR (4-arg book ctors, try_create,
amx_mirror_aware_cache, amx_mirror_eligible, footprint column, gauges, full.hpp, rinzler,
FUSE, CMake option) so subtraction is by concern not by guard; the response doc's counts
(600 code + 572 test) DO add up - both gpt-6-astra passes claimed otherwise and were wrong
(660/700); total non-blank is 2,373 by script vs the doc's 2,394. k_at() has six callers
(Bill's "dead code" claim false). Ingested plugins force_hw_attn=true (TronCpp.hs:233,
model.hpp:795) so AMX only engages with USE_HW_ATTN=0 / EAGLE / sw_required / HBM-exhaustion
fallback; gof_populate trace at gof.cpp:143 "hwattention-detail"; pay_for_determinism only
in model.hpp:2021,2070 (worker planning), not in self_attention.hpp.

Names proposed: namespace amx_attn_h128g4; qk_canonical_128x4 -> qk_rowmajor; layout k_vnni
(dimension-block-first); qk_mirror_128x4 -> qk_vnni with k_plane; options TRON_AMX_DISPATCH
kept, TRON_K_VNNI_STORAGE + TRON_K_ENCODING=row_major|vnni for single-K; amx_k_mirror only if
the arena ever lands.

Decisions by jhan 2026-09-05 (recorded in the page's section 8): PR 1 based on main; keep #3879
as PR 1 (force-push, tag old head first); no messages to Ben/Bill/Jeremy from the plan (jhan
communicates directly; message drafts removed); namespace amx_attn_h128g4 (follow Ben);
kernel names keep the shape suffix: qk_rowmajor_128x4, qk_vnni_128x4; keep TRON_AMX_DISABLE=1 =
clean-binary contract + separate dev control forcing AVX on VNNI storage; counters PR = CMake
option + host test; PR 1 is NOT cut further at the kernel/dispatch seam; round-1 results stand
(re-run only qwen 8u/8K canonical on the PR 1 tip); Wade's governor item discussed at the gate;
the proposed kill thresholds (G1 spread, G2 1.5x cold/1.2x hot, G3 10%/5%) are agreed;
reopening PR 2 deferred to the gate;
jhan asks Jeremy whether production runs qwen-class models with software attention.
Each PR = its own branch: jhan-page-share-counters, jhan-kv-footprint-memorder (new, from main);
jhan-amx-p0 (PR 1, force-pushed); jhan-amx-k-mirror (PR 2, from PR 1); jhan-single-k-1/2/3 later.

Status: nothing posted to Slack/GitHub; no split performed. Still open: Jeremy's software-attention answer (decision 10) and reopening PR 2 (at the gate).
Section 7.4 of the page now says no messages are sent from the plan.

**How to apply:** before any split work re-read the page's sections 6 (what PR 1 must not
bake in) and 8; check #intel-amx, Ben's DM (D0B7WC0FZLY) and the PR for newer messages;
supersedes the 3-PR-stack recommendation in [[ben-split-request-pr3879]]. Related:
[[more-testing-round1]], [[mirror-naming-convention]], [[debug-code-new-branch]],
[[pal-bridge]] (PAL file budget ~269K tokens: attach docs + diff, not the big headers).
