# Design brief: PRs 4957, 4958, 4959 re-expressed on PR 5047's structure

Words used here: tron = the inference program; the cache = h/tron/models/kv_cache.hpp (struct page, struct book);
the option = CMake option TRON_K_VNNI; a VNNI slot = a K storage slot of a 128-dimension head when the option is on;
the kernel = the AMX QK kernel; the reader = k_vnni::qk_group (AVX-512 scoring of the VNNI plane); the dotter = the
per-token AVX-512 dot product over a row-major row; a block = 16 consecutive tokens of a 64-token KV page.

## 1. The stack and the new branches

| PR | title | PR branch | head | base | new branch (worktree) |
|---|---|---|---|---|---|
| 4956 | Add the VNNI K layout and its readers | jhan-vnnik-1-layout | a5697f86d3 | main | (Ben's PR 5047 targets this branch) |
| 5047 | Ben: self_attention token selection + kv_cache hides the K layout | bgamari/vnnik-1 | ade89a9d9c | jhan-vnnik-1-layout | (worktree ~/workspace/ai-runs/tron-pr5047, read-only reference) |
| 4957 | Use VNNI K layout in AMX attention | jhan-vnnik-2-amx | 26b86a279a | jhan-vnnik-1-layout | jhan-vnnik-2-amx-5047 (~/workspace/ai-runs/tron-ben-pr2) |
| 4958 | Save K in 16-token blocks, shared with idle worker threads | jhan-vnnik-3-shared-save | b39765ec29 | jhan-vnnik-2-amx | jhan-vnnik-3-shared-save-5047 (~/workspace/ai-runs/tron-ben-pr3) |
| 4959 | Keep short K writes row-major; enable VNNI K in the deb preset | jhan-vnnik-4-tail-block | 6b081187e1 | jhan-vnnik-3-shared-save | jhan-vnnik-4-tail-block-5047 (~/workspace/ai-runs/tron-ben-pr4) |

Merge base of every stack branch with Ben's head = a5697f86d3. Simulated merges of Ben's head (git merge-tree):
4957: 6 conflict hunks (kv_cache.hpp 2, self_attention.hpp 3, t_amx_dispatch_dtype.cpp 1);
4958: 9 (kv_cache 3, model 1, self_attention 3, tensor/k_vnni 1, t_amx_dispatch_dtype 1);
4959: 13 (kv_cache 4, model 1, self_attention 5, scheduler/full 1, tensor/k_vnni 1, t_amx_dispatch_dtype 1).
Files that merge without markers but still need care: t/t_llama_unit.cpp, t/heterogeneous_scheduler_compile.cpp.

The new branches are stacked like the PRs: pr2 branch = jhan-vnnik-2-amx + merge of origin/bgamari/vnnik-1 + changes;
pr3 branch = jhan-vnnik-3-shared-save + merge of jhan-vnnik-2-amx-5047 + changes; pr4 branch = jhan-vnnik-4-tail-block +
merge of jhan-vnnik-3-shared-save-5047 + changes. Draft PRs will target the PR branches (jhan-vnnik-2-amx, ...).

Reference material (scratchpad/stack/): pr4957.diff, pr4958.diff, pr4959.diff, pr495N-body.md, ben-corpus.md,
ben-profile.md; ../pr5047.diff, ../pr5047-c1.diff, ../pr5047-c2.diff (Ben's commits); Ben's tree at
~/workspace/ai-runs/tron-pr5047 (do not modify).

## 2. Ben's structure at ade89a9d9c (what the merges must preserve)

- page::score_k<geometry>(slot, kv_head, q, uint64_t live, float* scores, size_t stride) const: VNNI slot -> the reader
  over `live`; row-major slot -> the dotter array over the live bits (kv_cache.hpp:1978-2007).
- page::try_score_k_amx<geometry>(slot, kv_head, const bf16* q_packed, float* scores, stride) const (under
  TRON_AMX_DISPATCH): VNNI slot -> `return false` (no AMX reader yet); row-major -> qk_rowmajor_128x4 (2015-2031).
- page::set_k_row(slot, kv_head, i_page, const_k_row_view) and set_k_row(slot, kv_head, i_page, const expr<X,dims>&)
  (converts on the stack for a VNNI slot, `k_at(i_page).set(row)` for row-major) (2035-2065); get_k_row (2071).
- page::kv_block(slot, kv_head) is PRIVATE (2233 private:, 2264-2290). page::k() (8 overloads) and page::k_packed are
  gone. save_k (model.hpp:3096-3101) is one set_k_row call per (token, kv_head). full.hpp k_head_fn (2747-2753) always
  get_k_row into caller scratch (a memcpy for row-major slots: a cost PR 5047 added, see section 5).
- self_attention.hpp: packed_amx_query (1684-1700) calls pack_q_group_128x4; apply_dense_amx_page (1734-1806) asks
  try_score_k_amx and returns false when declined; apply_page_tok (1819-1920): the loop fills `live`, then one score_k
  call. No k_vnni::layout_on in self_attention.hpp, model.hpp, full.hpp.
- Tests: t/kv_cache_helpers.hpp set_k_tag/k_tag; t_llama_unit probes page_k_accepts_geometry (set_k_row with a row view)
  and STATIC_REQUIRE_FALSE(page_k_packed_accepts_geometry).
- Known defects of Ben's head that the merged branches must not inherit:
  (d1) t/heterogeneous_scheduler_compile.cpp:687-689 still calls page->k<...>(slot, 0, 0)[i] -> GitHub "Build Tron" is
       red; fix with test::set_k_tag / test::k_tag (the helpers Ben added).
  (d2) t_llama_unit.cpp:118-120 page_k_accepts_raw_index names Page::head_size, which does not exist, so the probe is
       vacuous (always false). Fix: use the page's primary geometry head size (page_t::head_size exists? check) or drop.
  (d3) stale comments: self_attention.hpp:1723-1727 ("so this function always applies the page" - it can decline now),
       gof.hpp:61-67 (says a pointer into the page; the staging now copies). Fix the wording where the merge touches it.

## 3. Target per PR

### PR2' = jhan-vnnik-2-amx-5047 (worktree ~/workspace/ai-runs/tron-ben-pr2): "the VNNI AMX kernel behind the cache"

Goal: PR 4957's content (qk_vnni_128x4, pack_q_rows_128x4, bit-identity test, dispatch test, comments) with zero layout
knowledge outside the cache. Steps:

1. `git merge origin/bgamari/vnnik-1` (resolve, then commit as "Merge PR 5047 (bgamari/vnnik-1) into jhan-vnnik-2-amx").
   Resolution rules:
   - self_attention.hpp: Ben's side everywhere. PR 4957's packer choice moves into the cache (step 2). Keep PR 4957's
     comment edits that are still true (the amx_qpack_slot comment: "the output of either query packer").
   - kv_cache.hpp: Ben's code side; PR 4957's Note [K VNNI storage] edits re-worded to Ben's items ("2. page::try_score_k_amx
     passes the plane to qk_vnni_128x4", "3. page::score_k runs k_vnni::qk_group for every other visit of a VNNI slot ...").
     Any "page::k_packed" wording -> "the plane view the cache holds (kv_block::k.as_view())".
   - t_amx_dispatch_dtype.cpp: PR 4957's fakes (pack_q_rows_128x4 + qk_vnni_128x4, rows_pack_calls) and its `dense`
     predicate; the file-header comment merged by hand (Ben's text + 4957's "Under TRON_K_VNNI ..." sentence).
   - t_llama_unit.cpp: PR 4957's amx_qk_vnni_accepts probes stay (they test view types, not page accessors).
   - tensor/k_vnni.hpp header comment: Ben's wording + PR 4957's sentence about the two score kernels; no page::k_packed.
   - kernels/k_vnni.hpp, amx_attn_iface.hpp, amx_attn.cpp, README.ci.md: PR 4957's hunks, no conflict.
2. The cache picks the kernel AND the query operand format (one decision, one place):
   - page::try_score_k_amx VNNI branch: `amx_attn_h128g4::qk_vnni_128x4(kv_block<geometry>(slot, kv_head).k.as_view(),
     q_packed, scores, stride); return true;` (the row-major branch unchanged).
   - New static member next to it, same #ifdef: `template <kv_geometry geometry> static void pack_amx_query(const bf16*
     q_group, bf16* packed) noexcept` -> pack_q_rows_128x4 for a VNNI slot, pack_q_group_128x4 otherwise. Comment: the
     packer and the kernel are chosen together here; a slot buffer packed by this function is what try_score_k_amx
     expects for the same geometry.
   - self_attention.hpp packed_amx_query calls `page::template pack_amx_query<geometry.kv>(group, slot)`.
     Nothing else in self_attention.hpp changes.
3. Fix d1 (hetero test :687-689) and d2 in this branch (they are in files the merge touches anyway); mention both in the
   PR body as "needed in PR 5047 too".
4. Keep PR 4957's tests. Update README.ci.md wording if it names a removed accessor.

### PR3' = jhan-vnnik-3-shared-save-5047 (worktree ~/workspace/ai-runs/tron-ben-pr3): "shared block save through the cache"

Goal: PR 4958's content (block save store_block, page::set_k_block, the shared window, generated helpers' save_k call,
tests) with: no k_vnni::layout_on in model.hpp, activation-row conversion inside the cache (like Ben's set_k_row(expr)),
and the window protocol as operations of its own type instead of inline code in save_k_impl.

1. `git merge jhan-vnnik-2-amx-5047`. Resolution rules: self_attention.hpp, t_amx_dispatch_dtype.cpp, t_llama_unit.cpp
   type probes = the PR2' side; kv_cache.hpp = Ben's code + PR 4958's set_k_block placed after Ben's set_k_row(expr) +
   Note item 1 from PR 4958 reworded (no page::k); tensor/k_vnni.hpp = both comment edits; model.hpp = PR 4958's
   store_k_block + window code (then changed in step 2).
2. Changes:
   a. model.hpp knows no layout. The cache answers "does this slot save K in blocks": add to page (or book) a constexpr
      `template <kv_geometry geometry> static constexpr size_t k_block_tokens()` = k_vnni::BLOCK_TOKENS_16 for a VNNI
      slot and 0 for a row-major slot (0 = no block save; the row store is per token). k_store_shared and the run cutting
      in store_k_block use it; `if constexpr (!k_vnni::layout_on<...>)` disappears from model.hpp.
   b. The row-major branch of store_k_block stores with `pg.template set_k_row<geometry.kv>(slot, kv_head, j, kout)`
      (Ben's expr overload). page::k() does not exist any more.
   c. Conversion of non-bf16 activation rows moves into the cache: the single-row path calls set_k_row(expr) (Ben's);
      the block path calls a new set_k_block overload that takes the 16 row views as they are (`std::array<Row, 16>` of
      the row view type, plus `present`), reads bf16 rows in place and converts other types on the stack inside the
      page. store_k_block then has no `rows_are_bf16` / `conv` code.
   d. The window protocol becomes operations of batch::k_store_window_t (common.hpp): open(n_units) [main: resets
      next_unit and finished, releases opened], enter(worker_ix) [helper: waits for its window], claim() [fetch_add;
      returns the unit index], finish() [helper], join(n_helpers) [main; the watchdog constants k_join_clock_spins /
      k_join_timeout_s become members of the type]. save_k_impl reads as the protocol of Note [Shared block save] in
      about 20 lines. The fields stay public (the t_llama_unit case reads them). Behaviour and memory orders unchanged.
   e. store_k_block: if it is longer than about 60 lines after (c), move the VNNI run scan into a helper
      (e.g. next_k_run) so each function has one job.
3. Tests of PR 4958 stay; adapt names if a field or helper is renamed. LoopyTronSpec/TronCpp.hs unchanged.

### PR4' = jhan-vnnik-4-tail-block-5047 (worktree ~/workspace/ai-runs/tron-ben-pr4): "the row-major tail block inside the cache"

Goal: PR 4959's content (per-block layout state in the page, row-major tail block, forward-end conversion, hardware-attention
policy, deb preset, tests) with: self_attention.hpp unchanged from PR3' (Ben's loop), the tail-block scoring and the
"all blocks converted" gate inside page::score_k / page::try_score_k_amx, one page call for the FPGA staging row.

1. `git merge jhan-vnnik-3-shared-save-5047`. Resolution rules: self_attention.hpp = PR3' side entirely (drop PR 4959's
   k_layout_dense lambda, the vnni_blocks/plane placeholders and the in-loop tail dotter; keep nothing of PR 4959 there
   except comment corrections that are still true); kv_cache.hpp = Ben's operations + PR 4959's state and members;
   model.hpp = PR3' save_k_impl + PR 4959's pending_k_blocks_ / convert_pending_k_blocks / row-bit recording (the
   `if (n < k_store_block)` change of store_k_block stays); full.hpp = step 2c; tensor/k_vnni.hpp = both;
   t_amx_dispatch_dtype.cpp = PR3' + PR 4959's record_rows additions; hetero test = both (d1 fix from PR2' + PR 4959's
   forward-conversion case).
2. Changes:
   a. page::try_score_k_amx VNNI branch: `if (k_vnni_blocks<geometry>(slot) != k_vnni::BLOCKS_PER_PAGE_MASK_0XF) return
      false;` before the kernel call (comment: the page is dense for the kernel only when every block is converted;
      the caller then scores in software).
   b. page::score_k VNNI branch: the live tokens of converted blocks go to the reader (live & mask of the converted
      blocks expanded to 64 bits); the live tokens of row-major blocks go to the dotter over row_major_row(plane, i).
      Factor the dotter array + "for each live bit" loop (Ben's row-major branch) into one private helper that both
      branches call with a row accessor (keys[i] for row-major slots, row_major_row(plane, i) for a tail block), so the
      dot-product code exists once.
   c. full.hpp staging: one page call `bf16* k_staging_row<geometry>(slot, kv_head, off, bf16* dest)`: returns the row's
      own address when the row is stored row-major (a row-major slot; a row-major block of a VNNI slot) and otherwise
      gathers into dest and returns dest. k_head_fn becomes `return pg_ptr->template k_staging_row<hw_kv>(slot, kv_head,
      off, dest);`. PR 4959's k_row_if_row_major is replaced by this. (Side effect worth stating in the PR body: the
      OFF build loses the memcpy PR 5047 added for row-major slots.)
   d. The bit helpers k_vnni::block_bit / offset_bit / BLOCKS_PER_PAGE_MASK_0XF stay in tensor/k_vnni.hpp and the cache;
      no use in self_attention.hpp, model.hpp or full.hpp. model.hpp keeps pending_k_blocks_ (a pass-timing concern)
      and the note_k_row_saved loop.
   e. Tests without raw plane access (page::kv_block is private, page::k_packed is gone):
      - t_llama_unit.cpp check_page_range_reductions: replace the k_packed/element() re-store with rows read through
        get_k_row (fill_random -> get_k_row per row -> set_k_row per row -> record rows as before). The cross-build
        "same instance as the row-major build" property is not checked by any test; say so in the comment.
      - t_k_vnni_layout.cpp page cases: byte-level checks go through get_k_row (a stable function of the bytes), the
        in-place staging check uses k_staging_row (pointer != dest for a row-major block, == dest for a converted
        block, bytes equal the row), block masks through k_vnni_blocks. The owner-level cases (plane_and_rows) are
        unchanged.
   f. PR 4959's set_k_block signature (no `present`) stays; PR3' overload shape follows.
3. CMakePresets.json, README.ci.md, config/test-benchmarks.json hunks of PR 4959 unchanged.

## 4. Rules for every branch

- Behaviour-preserving: same bytes stored, same scores, same memory orders, same test expectations. No new features.
- Surgical: touch only what the merge and the listed changes require. Do not edit the PR branches themselves. Do not
  push. Do not run git in any /var/tmp/jhan tree.
- Style: clang-format 19.1.7 (`uvx --from clang-format==19.1.7 clang-format --style=file:<worktree>/.clang-format -i
  <files>`), `git diff --check` clean, no `<cassert>`, no issue/PR numbers in code comments, bool/0/1 literals named
  only in AMX-owned files (shared files keep literals), Note references consistent (lint-notes), comments in plain
  English (define terms, one claim per sentence, no idioms).
- Commits: topical; `git commit --no-verify` (the lefthook hook is missing on this host); every message ends with
  `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
- Verification on this host: the 22-cell syntax matrix `W=<worktree> P=<scratch>/stack/lcheck bash
  <scratch>/stack/lcheck/matrix.sh <label>` must print "MATRIX OK" (cells: gen / gen-amxoff x option off / on x
  t_llama_unit, t_k_vnni_layout, t_amx_dispatch_dtype, t_amx_numerics, heterogeneous_scheduler_compile, + amx_attn.cpp).
  Also: `grep -n "k_vnni::layout_on" h/tron/models/self_attention.hpp h/tron/models/model.hpp h/tron/scheduler/full.hpp`
  prints nothing. Builds and unit tests on delphi-3bda are run by the session owner afterwards, not by agents.

## 5. Facts to carry into the PR bodies

- PR 5047 added a memcpy per staged K row for row-major slots (full.hpp k_head_fn always get_k_row); PR4' step 2c
  removes it again. The 3bda campaign of 2026-10-21 measured PR 5047 vs its base: llama-3.1-8b prompt 8192 prefill
  +0.19 s (+0.5 %) on both option values, decode inside the band (option OFF), -1.5 % at prompt 8192 (option ON).
- Ben's CI "Build Tron" failure (d1) and the vacuous probe (d2) are defects of PR 5047's head; the merged branches fix them.
