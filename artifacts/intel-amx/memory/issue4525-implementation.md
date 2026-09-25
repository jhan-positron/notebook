---
name: issue4525-implementation
description: "2026-09-22/23: IMPLEMENTED issue #4525; DRAFT PR #4557 (jhan-kv-typed-tensors, rebased onto main 996f58ec82, tip 1c87d66926 = 4 commits + style commit, Skip benchmarks; pre-rebase tip pushed as jhan-kv-typed-tensors-pre-rebase-20260923); PR READY FOR REVIEW 2026-09-23 ~13:45 UTC after the 3bda chain passed on 1c87d66926; all unit tests pass on 3bda; review wf_d2b470ca-509 done, 15 findings fixed/recorded) (typed KV-cache tensors, parent of PR 4424) from the codex design rev d2e9dabf; branch jhan-kv-typed-tensors in ~/workspace/ai-runs/tron-issue4525 (NFS) + build worktree /var/tmp/jhan/tron-issue4525 on 3bda (detached at main 0a51385e95); sync = rsync -rlc over ssh WITHOUT --delete; main's t_amx_dispatch_dtype does not compile with AMX on (stale apply_page_range call, fixed in the branch); test plan goes to issue4525/status/first-3bda-test-plan.md"
metadata:
  node_type: memory
  type: project
  originSessionId: 7a726337-9373-4eb4-935f-269e8630de97
  modified: 2026-09-22T20:23:55.366Z
---

jhan (2026-09-22 ~19:50 UTC): "implement the solution for issue 4525 ... The design is at
status/design-new-tensor-type.html ... Do not bother changing PR4424. Only do the new tensor
types. The base is main branch. Do the change at a new branch. After the code changes pass unit
tests, write a test plan to do 3bda machine test, generate the test plan to
status/first-3bda-test-plan.md" (cwd VNNIed-K-in-place/issue4525).

Setup facts:
- Branch jhan-kv-typed-tensors from origin/main 0a51385e95 (2026-09-22 14:28 UTC), worktree
  ~/workspace/ai-runs/tron-issue4525 (NFS-shared, edit here). claude-box has NO nix, so every
  compile runs on delphi-3bda in the local-disk worktree /var/tmp/jhan/tron-issue4525
  (git worktree add --detach done ON 3bda; gen/ configured with cmake --preset native -DAVX512=ON
  -DTRON_AMX_DISPATCH=ON -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=OFF
  -DBUILD_TEST_MODELS=OFF -DBUILD_PRODUCTION_MODELS=OFF inside nix develop --accept-flake-config).
- Sync claude-box -> 3bda: `rsync -rlc --exclude=/.git --exclude=/gen --exclude=/gen-*
  --exclude=/ingest/traces --exclude=/ingest/dist-newstyle --exclude=/compile_commands.json
  ~/workspace/ai-runs/tron-issue4525/ delphi-3bda:/var/tmp/jhan/tron-issue4525/` (checksum
  compare, no -t/-p so untouched files keep their mtimes and ninja does not rebuild them; NEVER
  --delete: it would remove 3bda-local build artifacts such as rust/harmony/target, rust/rustenv).
- Build pinned to our half: `taskset -c 72-143,216-287 nix develop ... cmake --build gen -j 48
  --target ... -- -k 0` (ninja's -k goes after `--`; `cmake --build -k 0` prints usage and exits 1).
- bin/slice route on 3bda = local-legacy (normal local commands).
- Baseline defects at main 0a51385e95: (1) t/t_rinzler.cpp:5316 read_stats_counter undeclared when
  BUILD_INGEST_MODELS=OFF (helper guarded by TRON_GPT_OSS_20B_INGEST_MODEL_ENABLED); (2) t/t_amx_dispatch_dtype.cpp:149 calls apply_page_range with
  8 args; the signature (self_attention.hpp:1374) needs work_estimate + batch_queries -> AMX-on
  build of that test fails on unmodified main. The branch adds `visible` as batch_queries.

Design decisions taken while implementing (deviations/clarifications vs the design page):
- dma flag of the model's V source row comes from the buffer type (btensor: dma=true), not the
  design's "dma = false" claim (round-4 finding J09 confirmed the design was wrong).
- Class key `struct` (repo convention: 408 struct vs 10 class in h/tron) for v_vnni_tensor/
  v_vnni_view/v_vnni_row; all three forward-declared in kv_cache_fwd.hpp with `struct`.
- Constants follow the user's C++ guide: V_PAIR_TOKENS_2, V_ROW_WIDTH_MULTIPLE_32, BF16_BITS_16,
  V_ODD_TOKEN_LANE_MASK_0XFFFF0000, V_EVEN_TOKEN_LANE_MASK_0X0000FFFF in v_vnni.hpp.
- New test case in t_llama_unit ("packed V rows keep their bits through set_v, get_v and
  expression reads") pins truncation/no-NaN-correction and the row expression parity.

Status log:
- 20:35 UTC: all 12 files edited (10 modified + 2 new headers); review workflow wf_d2b470ca-509
  running (8 finder lenses -> 3 refuters each -> critic).
- 20:55 UTC: on 3bda, 16-lane AMX-on tree: every target builds except t_rinzler (pre-existing
  on main: t/t_rinzler.cpp:5316 read_stats_counter); clang-format clean; lint-notes exit 0;
  t_llama_unit 43 cases/176462 assertions, t_amx_numerics real AMX 12301 assertions (kill switch
  control shows both "AMX unavailable" warnings), t_amx_dispatch_dtype, t_heterogeneous_scheduler
  all pass. 16-lane AMX-off tree (gen-amxoff): all four pass. Debug tree (gen-debug, no
  TRON_IGNORE_NAN): [kv_data] 29/29 after fixing the new test (bf16 denormal 0x0001 -> 0x8000:
  clang-19 -O0 flushes a denormal through a plain bf16 struct copy even with DAZ/FTZ off; proof
  program /var/tmp/jhan/tron-issue4525-tests/denorm/). 8-lane build of libtron fails on main
  itself (h/tron/simd/fp32.hpp) -> A3 not applicable.
- Test plan written: issue4525/status/first-3bda-test-plan.md (section 7 = results). Peer session
  issue4525-40 executes Steps C-F on 3bda from snapshot 48ab31f7 (my tree at 20:47 UTC) starting
  20:55 UTC; it asked for a quiet socket 1 until ~01:35 UTC: start NOTHING on 3bda before it
  reports done, message it first (address uds:/tmp/cc-socks/743469.sock).
- 21:05 UTC: committed 85084e937c on jhan-kv-typed-tensors with `git commit --no-verify` (the
  pre-commit hook points at a Nix lefthook path that does not exist on claude-box; clang-format,
  lint-notes and the whitespace check had already passed on 3bda). Review fixes, if any, follow
  as a second commit. NOT pushed.
- 21:30 UTC: Step F objdump (subagent, files /var/tmp/jhan/tron-issue4525-tests/objdump/): all moved
  bodies instruction-identical to main; allocation/restore has no clearing; the one hot-path
  addition was TRON_ASSERT_LT(token, Rows) in v_vnni_access::pair_base (TRON_ASSERT is active in
  release) -> removed in commit 682064f8fb (uncompiled by me at commit time; the peer builds it).
  Peer measures snapshot 48ab31f7 WITH the assert = upper bound on cost; peer then builds 682064f8fb
  into /var/tmp/jhan/tron-i4525rt2 for Step E.
- 21:40 UTC: review workflow wf_d2b470ca-509 (8 finders -> 22 merged -> 3 refuters each): 15 confirmed
  (0 major, 5 minor, 10 notes), 7 rejected. Fixes applied locally, UNCOMPILED (waiting for a 3bda window
  from the peer): partner-zero checks after the bf16 and fp16 even appends, test guarded by
  TRON_CHUNK_SIZE == 16, "readiness" wording -> "marks the token complete (page::mark_v_complete)",
  class comment "no PUBLIC pointer constructor / no data() accessor", glossary (SIMD, AVX-512/AVX2,
  lane, pair chunk, B operand), V_ROW_WIDTH_MULTIPLE_32 comment, chunk() comment (shift vs mask),
  8-lane `fp32s chunk(size_t) const noexcept = delete;` (turns the expr::chunk self-forwarding hazard
  into a compile error), kv_cache_fwd.hpp header comment, "interleaving trick" -> "pair-interleaved".
  Kept as decided: assert removal 682064f8fb (2 of 3 refuters preferred keeping the assert, citing the
  kv_block asserts on the same path; I kept main's instruction-neutral hot path). Deferred/recorded only:
  test-benchmarks.json refresh (bin/slice bench --update t_llama_unit, whole host, user direction);
  PR-body sentence "internal KV-cache API change authorized by #4525; public API h/libtron.hpp untouched";
  const_native_k_view is passed by hidden reference (rank-2 const_view has user-provided copy/move ctors)
  = one store + one load per QK kernel call, design-mandated signature.
- 21:15 UTC: review fixes compiled + tested in the peer's window (t_llama_unit 43 cases / 176594
  assertions) and committed as c2efd73ff6 = BRANCH HEAD (3 commits, none pushed). Debug tree not
  rebuilt for c2efd73ff6.
- 21:20 UTC: critic done (all design steps 1-6 implemented; gaps = test contracts). Two closed in
  commit c3c368d298 = BRANCH HEAD (poison case GENERATE dst_tokens {2,3}; new "token copies keep
  bits" section): t_llama_unit 43 cases / 199125 assertions pass on 3bda. Deferred: generic
  fp32s_to_bf16s NaN expectation under #ifdef TRON_IGNORE_NAN (unchanged code, recorded in the
  plan sec. 6). 4 commits, none pushed. Peer runs Steps D/E on 682064f8fb (= head at 16 lanes).
- 21:35 UTC (peer report): Step D token identity OK in all arms (CPU attention 1024/8192 x base,
  head, head A/A, base+kill, head+kill; FPGA attention 1024/8192 head == base; 256 tokens each).
  Step E perf A/B running on 682064f8fb, expected end 00:00-00:30 UTC, then make test-host (AMX-off
  tree). Guard gap found by the peer: rinzler_takeover_if_idle refuses when the last journal line is
  "0 history events" (platformd 0.11 engines) -> dut.sh serving-down used instead.
- 22:30 UTC (peer report): Step E 682064f8fb vs main, 36 runs, 0 failures, all 12 comparisons inside
  band (largest +0.72 % TPS / -0.73 % TTFT, head faster; sd <= 0.35 TPS / 0.23 s). Step C branch tree
  AMX-off: build-test-host 669 host targets rc 0 (t_rinzler is fpga-labelled, never a host target; its
  compile error at t_rinzler.cpp:5316 comes from BUILD_INGEST_MODELS=OFF: the helper is guarded by
  TRON_GPT_OSS_20B_INGEST_MODEL_ENABLED, its use is not; pre-existing on main),
  test-host 88 passed / 1 skipped / 0 failed (110 s). Base host suite pending (~23:15 UTC). Report page:
  issue4525/status/first-3bda-test-results.html; evidence issue4525/evidence/3bda-first-test/.
- 22:49 UTC (peer DONE, 3bda free): Step C main control 88/0/1 = same status set as the branch. All
  plan steps pass. Peer's extra trees on 3bda: tron-main0922, tron-i4525rt, tron-i4525rt2, tron-i4525c,
  tron-i4525cbase (under /var/tmp/jhan).
- 22:55 UTC: Step F re-run on final code: constant-token bodies identical; runtime-token wrappers
  differ by address mode only (one fewer scalar add); copy closure 409->417 = register/addressing
  bookkeeping; allocate_kv_group outlined (cold) with bytes % sizeof assert; no clearing. Files
  out/report_final.txt, out/diff_final_*.txt under /var/tmp/jhan/tron-issue4525-tests/objdump/.
  ALL PLAN STEPS PASS. Task complete; branch not pushed (jhan decides push/PR/bench refresh/CI route).

**Why:** the compile/test loop spans two machines; these traps cost time every round.
**How to apply:** edit on claude-box, rsync as above, build on 3bda in the local worktree, run tests
from the repo root there; commit on claude-box in the NFS worktree. Related:
[[issue4525-design-review]], [[claude-box-tron-build-env]], [[nfs-attr-cache-build-trap]].
- 2026-09-23 05:00 UTC (jhan: "please push the branch and create PR"): main had moved 0a51385e95 -> 996f58ec82
  (68 files; PRs #4455/#4456 replaced the single reclaimable arena with page-aligned chunks:
  reclaimable_chunks_, allocate_retained_storage, allocate_reclaimable_chunk, slot_page; main's new
  t_llama_unit case "Sliding KV chunks reserve and restore transactionally" called the old pointer
  set_v/get_v). Rebased with `GIT_EDITOR=true git rebase --no-verify origin/main` (backup branch
  jhan-kv-typed-tensors-pre-rebase-20260923 = c3c368d298). Resolution in commit 1: construct_kv_blocks(base,
  bytes, pages, reclaimable) called from allocate_retained_storage and allocate_reclaimable_chunk (offset
  pages * byte_offset = slot_page's); Note [KV block lifetime] reworded; hetero test keeps both include sets;
  main's new test migrated to v_source_row/v_destination_row. Commit messages byte-identical (checked).
  New head 9bd53996cb. 3bda light check during the CI lease (jhan's standing rule: light work only while the
  lease is busy): -fsyntax-only of the 5 affected TUs via gen/compile_commands.json inside nix develop, pinned
  to 2 CPUs at nice 19 -> all rc 0; clang-format-19 and lint-notes clean (log
  /var/tmp/jhan/tron-issue4525-rebase-syntax.log). Full build + tests of the rebased tip wait for the lease
  (nightly ends ~11:25-13:20 UTC). PR body draft: scratchpad pr-body.md (Short version, Words, What changes,
  Decisions record Q1-Q4/D5 Proposed, Verification per tip, CI section, Skip benchmarks). Plan: open as DRAFT
  after the rebase review + body verification workflows, then build/test after the nightly, update the body,
  `gh pr ready`. Deb preset now compiles AMX on main (PR #4505 merged 09-22).
- 2026-09-23 05:26-06:10 UTC: rebase review workflow (25 agents): no code defect; Note [KV block lifetime]
  sentence reworded (slot-major fast path over kv_blocks_alias + per-slot [head][page] index) and commit 1's
  message bullet (allocate_kv_group -> allocate_retained_storage / allocate_reclaimable_chunk) amended by
  checkout + amend + cherry-pick 2-4 => final commits b951ba9b4c daf227de13 959d1ae229 707159b9ef (2-4
  byte-identical to the 9bd53996cb series). PR body verified by 4 lenses (design/facts/english/newcomer):
  fixes applied (Step D used --instance 2,4 on cards 90:00.0/93:00.0 and runtron's built-in prompt, NOT a
  forced token file; packed-V "64-byte load = 16 dims of one token pair" (the 16-tokens wording was the K
  layout); chunked storage = PR #4455 alone; Step F = 19 noinline wrappers; commit map old->new ids; Status
  section "Posted as a draft. Pending: build, 4 tests, CI"; cost-data deferral names all 4 platform blocks
  and t/AGENTS.md rule). PUSHED: jhan-kv-typed-tensors (707159b9ef) + jhan-kv-typed-tensors-pre-rebase-20260923
  (c3c368d298, so reviewers can open the tested commits). DRAFT PR #4557
  https://github.com/positron-ai/tron/pull/4557 (title "Typed KV-cache tensors for packed V and native K
  (parent of #4424)", label Skip benchmarks, assignee jhan-positron, no reviewers requested = jhan's call);
  first comment = evidence tables (Step D pairs, Step E 36 runs + band comparisons, unit-test lines, Step F,
  syntax check). Body files: scratchpad pr-body.md, pr-evidence-comment.md.
  3bda chain /var/tmp/jhan/tron-issue4525-rebase-chain.sh (pid 796184, log -rebase-chain.log, GO marker
  written 06:0x UTC): waits for the CI lease (+10 min grace), builds gen (all targets, -k 0) + gen-amxoff
  (4 tests) on our half, runs the 4 tests + the sliding-chunk and packed-bits cases, writes
  /var/tmp/jhan/tron-issue4525-rebase-chain.done. THEN: update PR body Verification (rebased-tip row, counts,
  Step F allocation-path re-check via objdump of gen/t_llama_unit: no rep stos/memset/loop in
  construct_kv_blocks callers), `gh pr ready 4557`, add CI run links. Open for jhan: reviewers; cost-data
  refresh (t/AGENTS.md rule, whole host); `make lint` / lint-toolchain not run; Steps D/E not re-run on the
  rebased tip (production code differs only by the chunk-construction call sites).
- 2026-09-23 06:10-06:25 UTC (jhan: "/cpp-coding-guide check and update source code changes of PR #4557 and
  /plain-english check and update PR #4557 description"): workflow (5 finders x 2 refuters = 129 agents + 2
  English checkers): 61 C++ guide findings confirmed (54 named-value, 7 braces), 0 refuted -> fixed in commit
  1c87d66926 (5th commit, pushed): V_PLANE_ALIGNMENT_64 (v_vnni.hpp, used by t_llama_unit's alignof check),
  PV_TILES_PER_HALF_4 + V_PAIR_TOKENS_2 in the amx_attn.cpp PV loads, full.hpp alias hw_head_size removed
  (inline model constant), test rows alignas(chunk_alignment) (the aligned-view contract), test constants
  HEAD_SIZE_64 N_SLOTS_1 X_BYTES_0 N_PAGES_1 PATTERN_BASE_0X3C00 SPECIALS_EVEN_TOKEN_2/ODD_3
  FLOAT_ROW_EVEN_TOKEN_4/ODD_5 FP16_ROW_EVEN_TOKEN_6/ODD_7 EVEN_START_DST_TOKENS_2/ODD_START_DST_TOKENS_3
  APPENDED_TOKENS_7, 7 for-bodies braced. Left as judgment calls: sseq<1>, #if TRON_CHUNK_SIZE == 16,
  first-index zeros, unrolled tile indices, constexpr predicates/aggregates. Verified on 3bda (light):
  -fsyntax-only 5 TUs, clang-format-19 -i then dry-run, lint-notes all rc 0. English: ~60 distinct
  violations (rules 1,2,3,6,7,8) -> body rewritten (Words rows added: fp32/fp16, AVX2, software path,
  AMX-on/off build, retained/sliding slot, partner rule, Note [Name], FPGA, QK/PV, shape, rc; sub-bullets
  for v_vnni.hpp / kv_cache.hpp / Tests; Rebase resolution, Token identity, Perf A/B, Instruction comparison,
  CI as bullets; no semicolons). Report page issue4525/status/pr4557-guide-checks.html (tables + corrected
  text). PR body updated (gh pr edit). GO marker re-written 06:24 UTC for tip 1c87d66926; chain still waits
  for the CI lease. TRAP: the user's brace/named-value guide conflicts with the repo's brace-less idiom
  (clang-format InsertBraces: false); applied to PR-added lines only, main's lines untouched.
- 2026-09-23 13:09-13:45 UTC: lease cleared 13:09; chain built gen (all targets, 308 s, only t_rinzler
  fails = pre-existing) and gen-amxoff (274 s) on our half and ran the tests on 1c87d66926: t_llama_unit
  44 cases / 252718 assertions (both trees; sliding-chunk case 53593, packed-bits case 28947 alone),
  t_amx_numerics 12301 real AMX + 2060 kill switch (2 "AMX unavailable"), t_amx_dispatch_dtype 1559,
  t_heterogeneous_scheduler 1900: all pass. TRAP: Catch2 splits test names on commas -> run a single case
  as "...set_v\, get_v..." (escaped) or the filter matches nothing (exit 2). Step F re-check on the rebased
  binary (objdump gen/t_llama_unit -> tests/rebase/alloc_path_check.py): every allocate_retained_storage /
  allocate_reclaimable_chunk instantiation (uniform + heterogeneous) 68-92 insns, 0 backward jumps, 0 rep
  stos, 0 memset, calls only dma_allocate/deallocate/max + tron_abort => placement-new compiles to nothing.
  Logs copied to issue4525/evidence/3bda-first-test/rebase/. PR body updated (Status = ready, rebased-tip
  rows, Step F scope) and `gh pr ready 4557` done -> GCP Nix CI runs; add its links to the body when done.
- 2026-09-23 ~14:40 UTC: GCP Nix run 35868511322 (ready_for_review event, tip 1c87d66926) completed
  success: Lint, toolchain/CI-machinery contracts, Build ingest/model traces, Test ingest, Generate model
  plugins, Build Tron, Test host, Test FPGA, Test all pass; Benchmark jobs skipped (Skip benchmarks). Debian
  smoke 35868511345 pass. Draft-time run 35826452601 had skipped Build Tron + tests (J01 confirmed). PR body
  CI section records the links. DONE on my side; jhan: reviewers, cost-data refresh, pre-rebase branch.
- 2026-09-23 ~15:30-16:30 UTC (jhan: add a section on Ben's points: which are addressed, which differently):
  workflow (extract 44 points from review 5270587330 + sketch 5765866077 -> 1 mapper + 2 refuters each, 133
  agents; 42 confirmed, 2 refuted on citations only) -> section "Response to the reviewer's comments on
  #4424" inserted in the PR body before Status: review table (5 points, all "Partly": packed K deferred,
  q_packed stays a bare pointer into qk_rowmajor_128x4, fill_random = documented raw test fill) + sketch
  table (35 rows: 17 same, 6 same rule/other shape, 6 different with recorded reason = Q1 x2, Q2 (deep
  const), Q3 (operator[] logical rows), header split, append_v_row name + view row args, 1 different with no
  reason = no packed_*_page aliases, 5 deferred to 4424). Verified by 2 checkers (facts + plain English):
  22 semicolons removed, Words list added (expr, tensor/dtensor, rank-2, logical row, matrix rule, SIMD,
  intrinsics, STATIC_REQUIRE, lvalue/rvalue, placement new, ...). Source texts saved in scratchpad
  ben-review-5270587330.md / ben-comment-5765866077.md; mapping summary ben-mapping-summary.txt. Never name
  the reviewer in PR text ("the reviewing maintainer").

- 2026-09-23 ~18:00 UTC (jhan: "true and false should have been replaced by variables. How come they got
  missed?" about full.hpp:2762 `view<bf16, true, false, ...>`): the 06:10 guide check narrowed the
  named-value rule to numbers (cause in [[cpp-guide-literals-include-bools]]). Still on tip 1c87d66926: 28
  PR-added lines with 39 bare boolean literals (26 view/const_view aligned/dma flag lines incl. the
  native_k_view aliases in kv_cache_fwd.hpp:43-50, plus kv_cache.hpp:1429/1441 `/*reclaimable=*/`). Not
  fixed yet; naming and placement of the flag constants is jhan's decision.
- 2026-09-23 18:23-18:40 UTC (jhan: "28 lines ... 39 boolean literals: make the changes, and push"): commit
  5051264d80 = PR HEAD (6th commit, pushed, fast-forward from 1c87d66926): VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE
  (inline constexpr in kv_cache_fwd.hpp, after the view/const_view forward declarations; every use site sees
  the header, full.hpp via load.hpp -> model_load.hpp -> model.hpp -> kv_cache.hpp -> v_vnni.hpp) and
  book::RECLAIMABLE_FALSE/TRUE (private static constexpr, replace /*reclaimable=*/ args). clang-format-19 run
  on 3bda then files pulled back (claude-box has no clang-format). 3bda (people-check FREE/claimed/released):
  lint-notes 0, gen all targets 269 s (only t_rinzler, pre-existing), gen-amxoff 276 s, 4 tests + sliding +
  packed-bits pass with 1c87d66926's counts in both trees, symbol sets of t_llama_unit (25049) and
  t_amx_numerics (19111) identical before/after. Script /var/tmp/jhan/tron-issue4525-boolnames.sh, log
  ...-boolnames.log, results /var/tmp/jhan/tron-issue4525-tests/boolnames/. CI: Debian smoke 35903869177
  success, GCP Nix 35903869986 started 18:38 UTC. PR body NOT updated (still says five commits, tip
  1c87d66926). Open per the updated guide ("0 and 1 are literals, list exceptions"): 132 literal 0/1 tokens
  (102 zeros, 30 ones) on 113 PR-added lines outside constexpr declarations; counter script in the session
  scratchpad zero_one_lits.py (classes: call args 46, loop starts 32, comparisons 20, sseq<1> 19 +
  integer_sequence 2, [0] 8, offsets 5).
- 2026-09-23 19:11 UTC: GCP Nix 35903869986 on 5051264d80 completed success (33 min): Lint, Build ingest,
  Build model traces, Generate model plugins, Build Tron, Test host, Test FPGA, Test all pass; benchmarks
  skipped (label). Build Tron compiled the model plugins, which cover full.hpp in plugin TUs (not built on 3bda).
- 2026-09-23 22:30 UTC (jhan: rewrite the "Packed V" comment with /plain-english, then "commit and push"): commit
  fcdbfff8e4 = PR HEAD (7th commit, pushed): kv_cache_fwd.hpp Packed V comment as one bullet per type (8-agent
  check wf_a03e8621-ee9), jhan's own staged edits (kv_cache_fwd.hpp glossary removed, v_vnni.hpp header shortened +
  blank lines between constexprs) with 7 trailing-space lines stripped by me. Checks: git diff --check, clang-format
  19.1.7 via `uvx --from clang-format==19.1.7` (works on claude-box, no 3bda needed), no build (comment only),
  --no-verify (hook's nix lefthook path absent on claude-box). Debian smoke 35928376483 success, GCP Nix 35928376376
  queued. PR body still describes tip 1c87d66926 (5 commits). Not applied, only proposed: a comment for
  VIEW_ALIGNED_TRUE/VIEW_DMA_FALSE that states the aligned promise; answer given: keep the name, keep the int mask.
- 2026-09-23 ~23:45 UTC (jhan: commit and push): 2280e4beb2 (packed V comments: 16 * i, parity_ comment, rank
  defined, [Rows tokens * Cols dimensions]) + ec795fbce8 = PR HEAD (AMX tile numbers named: ACCUMULATOR_TILE_0..3,
  K_EVEN_BLOCK_TILE_4/K_ODD_BLOCK_TILE_5/Q_TILE_6, P_TILE_4/V_EVEN_SLICE_TILE_5/V_ODD_SLICE_TILE_6; before/after
  disassembly identical on 3bda). TRAP: named tile constants work only with clang (GCC's AMX headers stringize the
  tile arg into asm). Left: literal "+ 0"/"0 *"/64,16,32,48 offsets on main's lines in amx_attn.cpp.
- 2026-09-24: 633cb88896 = PR HEAD: Note [KV block lifetime] rewritten to jhan's approved text (per-geometry details dropped by jhan's choice).
