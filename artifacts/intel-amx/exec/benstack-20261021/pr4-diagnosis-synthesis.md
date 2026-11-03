**Synthesis: t_llama_unit "page splits match emulation" failure at PR4' (f7c2ccf6b7)**

**Short version**

The failure is a test-setup change, not a cache or kernel defect. The merge commit 627092917a deleted the test step that gave the VNNI build the same random K rows as the row-major build, so the VNNI build now scores a different random attention instance, and on that instance the pre-existing bf16 truncation of the softmax weights in the PV product lands one element 0.00045 (3 % of the bound) outside an emulation tolerance that was already marginal. Four independent replicas of the seed-18 arithmetic reproduce the printed failure to six digits for the new instance and pass for the old one, and the test's own s_star and m_star checks (1e-5 relative) passed for the failing token, which rules out a wrong K row or a wrong kernel.

**Words used here**

- PR4' = branch jhan-vnnik-4-tail-block-5047 at f7c2ccf6b7. OLD = 6b081187e1, the PR 4959 head that passed. PR3' = 2c501a9390.
- VNNI build = the TRON_K_VNNI=ON build (K stored as 16-token transposed blocks). Row-major build = option OFF.
- Re-store = the deleted test step that read the raw K plane as consecutive 128-value rows and wrote them back through set_k_row.
- Instance = the concrete random Q, K, V values the test scores (which K row each token holds).
- The dotter = the AVX-512 row-major dot product. qk_group = the AVX-512 reader of the VNNI K layout. Both produce the raw q.k scores.
- v_star = the unnormalized weighted V sum per query head. s_star = the fp32 sum of the softmax weights. m_star = the running maximum score.
- PV product = the weighted sum of V rows by the softmax weights (page::scaled_v).
- Arm = one generator value of the section: uses_hw=false scores 2 pages, uses_hw=true scores page 9 of 10.
- Replica = a stand-alone program (not tron) written by the refuters that replays std::mt19937(18), the fill order, the K map, tron's score and PV arithmetic, and the fp32 reference. Its numbers are computed, not estimated, but they are not tron runs.

**1. Ranked causes**

Cause 1 (most likely, confidence high): the K instance changed and the emulation bound is marginal for the bf16 weight truncation.

- Step 1: fill_random writes the K plane as raw consecutive bf16 draws with no layout meaning, identically in both versions [h/tron/models/kv_cache.hpp:1874-1892, k[i] at 1882; OLD 1881-1899].
- Step 2: OLD re-stored every row so that token tok held raw row tok, then recorded and converted [OLD t/t_llama_unit.cpp:2560-2603: comment "Give the VNNI build the K instance of the row-major build", element lambda, set_k_row at 2596, note_k_row_saved + k_block_to_vnni at 2602-2603]. The row-major build holds the same instance, because its fill writes block.k in token order and k_at(i) is row i [kv_cache.hpp:1885-1887, 3237-3241]. The run that passed on 2026-10-12 (ea94e95a4e) carries the same re-store [ea94e95a4e t/t_llama_unit.cpp:2502-2538].
- Step 3: PR4' only records and converts in place [t/t_llama_unit.cpp:2552-2569, comment "The VNNI build scores the K instance fill_random wrote, converted in place", record_k_row_and_convert at 2567; t/kv_cache_helpers.hpp:30-35]. The merge commit deleted the re-store, and its message says so ("The k_packed re-store of check_page_range_reductions is deleted") [git show 627092917a]. Commit 73d6eb2f2e did not remove it, its message says the removal happened "in the merge commit".
- Step 4: an unconverted token 16c + t lives at plane offset ((t/4)*4 + c)*512 + (t%4)*128, in both versions [h/tron/tensor/k_vnni.hpp:457-465; OLD 431-439]. So at PR4' token 16c + 4a + b holds raw row 16a + 4c + b. That swap of a and c moves 48 of the 64 rows of every page (fixed points: tokens 0-3, 20-23, 40-43, 60-63). block_to_vnni reads the same rows through load_row_major [k_vnni.hpp:494-504], get_k_row reads them back by the same block bit [kv_cache.hpp:2425-2436], and score_k scores them by the same bit [kv_cache.hpp:2095-2139]. So PR4' is self-consistent, but Q (same draw stream) meets different K rows than at OLD.

```
fill_random row r = 16a + 4c + b   (a, c, b in 0..3)
  OLD test, row-major build :  held by token r            (identity)
  PR4' test (no re-store)   :  held by token 16c + 4a + b (a, c swapped)
```

- Step 5: production truncates each fp32 softmax weight to bf16 (keeps the high 16 bits, up to 2^-7 of the weight) before the PV product [kv_cache.hpp:3176-3181 interleave_bf16_ps, used by the head-128 loop at 3141-3146; contract line "AVX: P truncated to bf16" at h/tron/kernels/amx_attn_iface.hpp:68]. The emulation keeps fp32 weights [h/tron/emulation/attention.hpp:184-186, 196]. The bound is abs 0.01 + rel 0.02 [t/t_llama_unit.cpp:2778-2781; t/testutil.hpp:66, 86]. For the failing element (expected 0.253496) the bound is 0.01507 and the discrepancy is 0.01552, 0.00045 over (3 % of the bound). The test's own comment measures this truncation effect at 0.018 to 0.022 per element [t/t_llama_unit.cpp:2805-2813].
- Step 6: none of the arithmetic changed between OLD and PR4'. The diff touches no code line of scaled_v, interleave_bf16_ps, get_v or fill_storage_slot (two comment lines only), the softmax epilogue is unchanged [self_attention.hpp:1919-1952], qk_group changed only the spelling of the panel address [h/tron/kernels/k_vnni.hpp, panel_offset], and emulation/attention.hpp, t/testutil.hpp, dotter.hpp and v_vnni.hpp are not in the diff [git diff --stat 6b081187e1 f7c2ccf6b7].
- Step 7: the replicas reproduce the log. Seed-18 results (replica, v_star units):

| K instance | 2-page arm (uses_hw=false) | 10-page arm (uses_hw=true) |
|---|---|---|
| identity (OLD re-store, row-major build) | pass, worst margin 0.0014 | pass, worst margin 0.0028 |
| VNNI index map (PR2'/PR3', no row-major blocks) | pass | pass |
| permuted (PR4') | FAIL q=6, element 255: 0.269017 vs 0.253496, max abs 0.02195, max rel 0.4382 | FAIL q=1, element 199: -0.043137 vs -0.029483 (predicted) |

  The log printed 0.269017, 0.253496, 0.0219526 and 0.438241. Replica sources: /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/replay/replay.cpp (output in replay-output.txt in the same folder), .../scratchpad/replicate/replicate.cpp, .../scratchpad/refuter2/sim.cpp, .../scratchpad/repro_exact.cpp. With fp32 (untruncated) weights the same replica matches the reference within 3e-6, so the truncation is the whole discrepancy.
- Step 8: history already recorded this exact event. The commit that first added the re-store says "the other instance hit the bf16 weight truncation of scaled_v on a 4-sigma V element, 0.016 off on 0.25" [git show 8198eab4cc, 2026-09-29]. Today's failure is 0.0155 off on 0.2535.
- The section runs uses_hw=false first (GENERATE(false, true)) [t/t_llama_unit.cpp:3220-3224], so the quoted failure is the 2-page arm, query token 6 (position 126), head 1, dim 127. The FACTS list the arms in the other order.
- The kill switch and AMX availability cannot matter here: the test has kv_mul 2 [t/t_llama_unit.cpp:2487-2492], the AMX shape needs 4 [amx_attn_iface.hpp:156-158, 172-174], and the dispatch sits behind `if constexpr (eligible...)` [self_attention.hpp:1872-1873]. So the AMX path is compiled out of this test on every host, and the test-change refuters' caveat about an AMX host is wrong.
- What confirms it on 3bda: the per-token score check of section 4 shows every page-1 score within fp32 add-order noise of the reference, the truncated-weight reference matches v_star within 1e-4, and the instance re-store (fix A) makes the section pass.

Cause 2 (refuted, kept as the alternative the diagnostic run separates): a layout or kernel defect in the mixed page (token 32..63 scored from a wrong row, or by the wrong reader).

- Why it is excluded: the scorer and the reference take the layout from the same bit (k_block_is_vnni and k_vnni_token_mask read k_vnni_blocks_) [kv_cache.hpp:2129-2137, 2431-2435, 2646-2657]. The REQUIREs on s_star and m_star at 1e-5 relative run before the failing v_star check for the same token and passed [t/t_llama_unit.cpp:2767-2772, then 2778]. A wrong row moves s_star by about 1e-3 relative or more. The replicas score every token correctly and still land on 0.269017.
- What would confirm it instead: in the section-4 run, any page-1 token whose score differs from the double-precision reference by more than about 1e-3 (scores are of size about 10 unscaled).

Cause 3 (refuted): a changed fp32 add order, scale step or PV numerics. The diff contains none (Step 6).

**2. Minimal fix**

The fix belongs in the test, t/t_llama_unit.cpp, function check_page_range_reductions. No cache code changes (there is no defect). No change to the test helper (record_k_row_and_convert does what production does).

Recommended (fix C, one constant plus a comment): raise the absolute part of the emulation bound at line 2780 from 1e-2f to 5e-2f, the value the split comparison already uses for VNNI K at line 2814 for the same reason.

```
-            /*absolute tolerance*/ 1e-2f,
+            /*absolute tolerance*/ 5e-2f,
```

Add above the assert_allclose at 2778: production truncates each softmax weight to bf16 before the PV product (interleave_bf16_ps, up to 2^-7 of the weight), the emulation keeps fp32 weights, and on this shape (up to 127 visible tokens, |v_star| up to about 10) the gap reaches about 0.04 on one element (replica maximum 0.039 across the instances checked). The s_star and m_star checks at 1e-5 relative above guard the scores, and a wrong K row moves v_star elements by 0.1 to 1, so 5e-2 still detects any real defect. Reason to prefer this fix: every instance checked sits within 10 % of the current bound (margins -0.0014, -0.0008, +0.00045), and about 29 to 32 of 40 random seeds fail the 2-page arm at the current bound (replica sweep, est.). Restoring the old instance would restore a lucky draw.

Alternative (fix A, about 15 lines, public page operations only): restore the cross-build instance. Insert before the record loop (before line 2561), guarded by `if constexpr (k_vnni::layout_on<head_size>)`: for every page and kv_head, read all 64 rows with page->get_k_row into rows[64] (all blocks are still row-major, so this is load_row_major), then write page->set_k_row(slot_0, kv_head, tok, rows[j(tok)]) for tok = 0..63 with j(tok) = ((tok % 16) / 4) * 16 + (tok / 16) * 4 + tok % 4. Read all 64 before writing any. j is its own inverse, so afterwards token tok holds raw row tok, the row-major build's instance. Rewrite the comment at 2552-2559, which now says the opposite. Drawback: the margin at seed 18 is 0.0014 (10 % of the bound), and the merge message states the decision "No test checks a property across builds".

Not recommended: changing interleave_bf16_ps to round-to-nearest (production numerics, and the replica says the OLD instance would then fail at q=1 element 33), or a truncating reference with the emulation's global max (production truncates at a page-wise running max, so that reference would still differ by the same 0.02 order).

**3. 3bda diagnostic plan**

Follow the 3bda rules first (notebook handoffs/check-CI.md and share-3bda-with-bill.md, or newer memory rules). The run is one process for a few seconds.

Step 1, reproduce without a rebuild. add_test runs the binary from the source directory [t/CMakeLists.txt:77], so do the same.

```
SRC=$(sed -n 's/^CMAKE_HOME_DIRECTORY:INTERNAL=//p' /var/tmp/jhan/tron-bp4v/gen/CMakeCache.txt)
( cd "$SRC" && TRON_ATTN_STATS=1 ./gen/t_llama_unit "apply and join page ranges" \
    -c "page splits match emulation" ) 2>&1 | tee /var/tmp/jhan/bp4v-emul-0.log
```

Expected: the same REQUIRE at t/testutil.hpp:86 with observed[255] = 0.269017.

Step 2, one instrumented run that separates cause 1 from cause 2. Edit $SRC/t/t_llama_unit.cpp on 3bda itself (the NFS attribute cache compiles stale content after a cross-host edit), rebuild only the test, rerun.

```
ninja -C /var/tmp/jhan/tron-bp4v/gen t_llama_unit 2>&1 | tail -3
( cd "$SRC" && ./gen/t_llama_unit "apply and join page ranges" \
    -c "page splits match emulation" ) 2>&1 | tee /var/tmp/jhan/bp4v-emul-diag.log
```

The patch, all inside check_page_range_reductions:

(a) Name the arm and token. Before the assert_allclose at line 2778: `CAPTURE(uses_hw, static_cast<int>(algorithm), tok);`

(b) Block bits and per-token scores of the mixed page, after the saved stars (after line 2739, inside `if constexpr (!split_queries)`):

```cpp
    const kv_slot_id slot_0 = test_kv_slot<book_t>(0);
    page_t* mixed = pages.back();
    const unsigned bits = mixed->template k_vnni_blocks<geometry.kv>(slot_0);
    std::printf("DIAG page0 bits=0x%x mixed bits=0x%x\n",
        unsigned(pages[0]->template k_vnni_blocks<geometry.kv>(slot_0)), bits);
    constexpr size_t q_tok = 6;
    alignas(64) float s[kv_mul * page_t::page_size];
    mixed->template score_k<geometry>(slot_0, 0,
        state.plugin_state.qs_roped[token_job_id(q_tok)].as_view(), ~uint64_t{0},
        s, page_t::page_size);
    const size_t base = (num_pages - 1) * page_t::page_size;
    for (size_t h = 0; h < kv_mul; ++h)
      for (size_t i = 0; i < page_t::page_size; ++i) {
        double ref = 0;
        for (size_t d = 0; d < head_size; ++d)
          ref += double(random_qs[q_tok][h * head_size + d]) * random_ks[base + i][d];
        std::printf("DIAG h%zu tok%2zu %s s=%.6f ref=%.6f diff=%.2e\n", h, i,
            ((bits >> (i / 16)) & 1) ? "qk_group" : "dotter  ",
            s[h * page_t::page_size + i], ref, s[h * page_t::page_size + i] - ref);
      }
```

Expected under cause 1: page 0 bits 0xf, mixed page bits 0x3, every diff below about 1e-4 for all four blocks (fp32 add order only). Under cause 2: at least one token with a diff of order 1 to 10.

(c) The v_star discrepancy of the failing token, inside the tok loop before the assert_allclose, for tok == 6: print obs[e] - ref_outputs.v_star[tok][e] for e in 0..255 (obs = slice<2 * head_size>()((*v_stars_saved)[tok].as_view(), 0)) and their standard deviation. Expected under cause 1: a bell-shaped spread, standard deviation about 0.007, no block or head structure, one element over the line.

(d) Decisive for cause 1, same run: recompute v_star for tok 6 with production's PV numerics in double. For each head and each page in order: m_page = max over the page's visible scaled scores and the previous m, weight = exp(score - m_page) in float, truncated to its high 16 bits (`u &= 0xffff0000u` on the float bits), acc[d] = acc[d] * exp(m_prev - m_page) + sum_i weight_i * random_vs[kv][d]. Scores come from the fp32 dot of random_qs[6][head*128 + d] with random_ks[kv][d] times operation_scale, visibility from vis[6][kv]. Expected: |acc[d] - obs[head*128 + d]| below 1e-4 for all 256 elements (std::exp versus tron's exp and the add order are the only differences). Any element off by more than 1e-3 would point to a PV or V defect instead.

Step 3, the A/B of the top cause: apply fix A (the re-store permutation) and rerun. Expected: the section passes both arms. Then revert it, apply fix C (5e-2f) and rerun. Expected: both arms pass, and the second arm reports no element over the line.

**4. Open questions**

- Does the uses_hw=true arm also fail on the real binary? The replica predicts query token 1, element 199 (observed -0.043137, expected -0.029483, 0.003 over). The quoted log stops at the first REQUIRE. Insufficient data until the full log or a run after step 3 is seen.
- Is the merge's decision "No test checks a property across builds" final? It decides between fix A and fix C.
- The row-major build has the same exposure: its seed-18 margin is 0.0014 (replica). Any change of the draw order (slot count, page count, V fill) can flip it. Fix C covers both builds.
- The replicas matched the log only with libstdc++'s normal_distribution draw order, so the bp4v binary links libstdc++. A build against libc++ would change the instance again.
- Do other tests compare a VNNI-instance attention result against the fp32 emulation at abs 1e-2 (t_amx_dispatch_dtype, t_k_vnni_layout)? Not checked here.
- Which commit set the abs 1e-2 + rel 2e-2 bound (the reader-numerics refuter names a383187ab5, 2025-02-27, long before VNNI K) is not independently verified in this synthesis.