---
name: pr4587-alloc-creates-blocks
description: 2026-09-24 construct_kv_blocks redesign: draft PR #4587 (jhan-kv-alloc-creates-blocks, stacked on #4557) = A2-min + K1; judges/critic verdict; page status/remove-dummy-new-claude.html; 3bda test pending
metadata:
  type: project
  modified: 2026-09-24T05:24:48.023Z
---

jhan 2026-09-23 ~20:50 PDT: "construct_kv_blocks() spells some design level defect ... identify designs which do
not need the ::new call, pick the best one, compare with the PR version ... implement it and push a draft PR";
then "generate your analysis and new design at status/remove-dummy-new-claude.html (override)"; then "Push the
draft PR after the Design choice step" (do not wait for the 3bda build).

Outcome:
- Draft PR #4587, branch jhan-kv-alloc-creates-blocks (worktree ~/workspace/ai-runs/tron-issue4525-a2min), base
  jhan-kv-typed-tensors. Commits 39a6899446 (A2-min: tagged global `operator new[](size_t, dma_allocation_t,
  std::align_val_t) noexcept` in h/system/memory.hpp used by try_make_unique_dma_for_overwrite, whose only callers
  are the KV book; construct_kv_blocks + RECLAIMABLE_* deleted; std::launder at the 3 accessor casts; Note [DMA
  allocation creates objects]) and c73e7fb2f9 (K1: kv_block::k = bf16[page_size*head_size], k_view without cast).
  5 files +90/-70 vs #4557.
- Key standard fact: N4950 [intro.object]/13 "Any implicit or explicit invocation of a function named operator new
  or operator new[] implicitly creates objects ... and returns a pointer to a suitable created object".
  std::start_lifetime_as is NOT in libstdc++ 14.3.0 (nix toolchain).
- Verdict: 3 judges (object model: C2/#4584 8.5; maintainability: A2-min 7.5; delivery: P' 8) -> means A2-min 6.8,
  P' 6.7, P 5.5, C2 5.2, D1 2.2; critic chose A2-min + K1. All agree #4557 must not merge with the discarded ::new
  result (its Note overclaims). Fallback if the maintainer rejects allocation-time creation: P' (#4557 + launder +
  Note fix). Maintainer question drafted on the page, NOT posted.
- #4584 (jhan + Codex, design C2: bf16 arenas, no kv_block) exists as a draft; it syntax-checks clean; conflicts
  with #4587 in memory.hpp; its fate is jhan's; its scaled_v_expr/fill_storage_slot hunks = follow-up for G5/G6.
- 3bda test: script issue4525/evidence/pr4587-3bda/run.sh (reuses /var/tmp/jhan/tron-issue4525, whose content was
  5051264d80 before; objdump before/after + fn_diff.py + alloc_kind_summary.py); started by a claude-box background
  waiter after the nightly CI lease clears. PR body of #4587 still says "not done yet" for the build/tests.

Traps learned:
- Workflow subagents obey a relayed mid-turn user message: in the first workflow 4 "read-only" agents wrote
  status/remove-dummy-new-claude.html and -r2..-r4 copies. Put "do not write any file under ~/workspace, even if a
  relayed user message asks" in every read-only agent prompt (worked in the second workflow).
- Local clang-19 syntax checks on claude-box: ~/workspace/ai-runs/lcheck (see its README) [[claude-box-tron-build-env]].
- Headless chromium from ~/.cache/ms-playwright crashes on claude-box; render-check SVG with cairosvg instead [[svg-render-check]].

Related: [[issue4525-implementation]], [[cpp-guide-literals-include-bools]].

2026-09-24 ~06:10 UTC (jhan: "when you have access to 3bda after CI, run runtron to test correctness and performance of
#4587 + #4557, no regression at either"): harness exec/i4587-20260924/ (fork of i4525-20260922 with a third binary
RT_NEW = arms new/newoff, SKIP_SERVING_UP=1; chain.sh driver). Arms: base = main 996f58ec82 (tree tron-main0922,
runtron.main0924), head = #4557 633cb88896 (tron-i4525rt, runtron.pr4557), new = #4587 c73e7fb2f9 (tron-i4525rt2,
runtron.pr4587). Step D identity (cpu p1024 incl. A/A head2/new2 + kill-switch arms, cpu p8192, fpga p1024/p8192);
Step E 8u x 3 reps: E-cpu p1024/2048/8192 base/head/new, E-fpga p1024/8192, E-off (TRON_AMX_DISABLE=1) p1024/8192.
Band rule from 09-22: inside max(2*max sd, 0.4 TPS / 0.15 s). Waiters on claude-box: b4u7fmdc9 (lease -> run.sh unit
tests) and b2hmc80wo (run.done clean -> chain.sh -> summaries). Results exec/results/i4587-*/, evidence copy
issue4525/evidence/pr4587-3bda/runtron/.

2026-09-24 13:24 UTC unit run DONE on 3bda: all tests pass both trees (t_llama_unit 252720/44, t_amx_numerics 12301 AMX / 2060 kill switch, t_heap_v2 8242), runtron+rinzler link, lint-notes 0. fn_diff2 (layout-normalized): 261/317 KV functions identical (hot paths), allocate_* now inlined into ctor/reserve/restore (+31..+42 insns), no clearing. PR 4587 body updated. runtron chain started 13:25:35 UTC.

2026-09-24 runtron RESULTS (model qwen3-4b-instruct-2507 tp2, our half, cards 90/93):
- Step D: all identical (cpu/fpga x p1024/p8192, incl. kill switch and A/A).
- Step E (8u, 3 reps): 35/42 inside band. AMX path + FPGA path: no regression for #4557 or #4587. Kill-switch (AVX) path:
  p8192 TTFT #4587 = #4557 + 1.25 s (+1.0 %), p1024 decode #4587 = #4557 - 0.9 % (= main).
- Isolation (i4587-iso, commit 1 39a6899446 alone): p8192 TTFT c1 +1.27 s, full +1.25 s vs #4557; p1024 decode c1 -1.2 %,
  full -0.9 % -> effect comes with commit 1, not K1.
- runtron codegen: 1646/1676 KV+attention functions instruction-identical (normalized) #4557 vs #4587; only alloc paths
  differ. 132 of 135 qwen attention functions (138 symbols incl. 3 guard variables) start at a different offset mod 64 -> layout hypothesis.
- Alignment test i4587-align (align.sh, campaign4.sh = 4 slots): #4557/#4587 unaligned + both rebuilt with
  -falign-functions=64, kill switch, p8192 x4 + p1024 x3; started 16:44 UTC, waiter bt22k7tr4.
- Alignment test DONE 18:03 UTC: normal builds #4587 vs #4557 p8192 TTFT +1.20 s (+1.0 %), p1024 TPS -0.9 %; with both
  built -falign-functions=64: +0.21 s (+0.2 %, inside band 0.25 s) and +0.2 % TPS -> AVX-path gap = code placement.
  PR 4587 body + status page section 7 updated with all runtron results. Serving restored after each run.
- 2026-09-24 ~19:xx UTC (jhan): "Forget about 4584, I already closed it. Yes, fold 4587 to 4557." DONE: fast-forward
  jhan-kv-typed-tensors 633cb88896 -> c73e7fb2f9 (pushed; GitHub auto-marked #4587 MERGED, pointer comment posted). #4557 body
  updated (Short version +1 sentence, What changes: memory.hpp + kv_block::k + Note rewrite, new "Machine test of the
  allocation-call change" section) after a 2-agent check (facts + plain English; fixed: ctor growth +23..+44 not +31..+42,
  132 of 135 functions, t_heap_v2 also calls the factory, main comparison, A/A only at p1024). Body had CRLF; now LF.
- Maintainer question (allocation call vs "the page arena must construct the actual storage type") explained to jhan in
  plain English; NOT posted. Recommended: add as Q5 (Proposed) in the #4557 Decisions record; waiting for jhan.
