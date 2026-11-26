# Page pass 5 brief (respond-2-Isaac.html), written 2026-11-19 20:50 PST

Apply on top of the page as it stands now (209,118 bytes; passes 2 to 4 plus two small edits by the main session:
the "Timing of these checks" bullet in Part C and the I6 diffs with VIEW_ALIGNED_TRUE / VIEW_DMA_FALSE).
Same rules as before (idempotent apply_patch5.py, assert anchors, keep ids, plain English, light theme,
structure check, no "3997" in reply blocks, headless render of changed parts).

## H. Changes after an independent pre-review (2026-11-19, about 20:40 PST)

An independent agent reviewed the round-2 edits and the PR description draft with the skills folks-code-review,
tron-code-review, cpp-coding-guide and simplify-cpp-comments. It reported 4 "fix before push" findings and 3 nits.
All are applied. The git tree hash of the prepared tree is now 5821ee86418d3ac07944112c529d7d311e91f3bd
(prep.txt updated). Local checks were repeated after these edits (20:47 PST): syntax check of both AMX test
files with the option ON and OFF: 0 errors, 0 warnings; clang-format clean; git diff --check clean.
Add a short "Pre-review" paragraph to "How this was checked" and to Part C with these facts, and fix the texts below.

1. I26 (t/CMakeLists.txt). The registration in the reply draft would stop every CMake configure:
   add_catch_test forwards its arguments unquoted, so "fake;skip_return_code_4" splits into two items and
   set_tests_properties gets an odd number of values. Final text (the label is appended the way t_mwaitx_cliff does it):
```
# The QK and PV cases SKIP without AMX; a run that selects only them exits
# Catch2's code 4. SKIP_RETURN_CODE + the skip_return_code_4 label report
# that as skipped (ctest and Slice) rather than failed.
add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake
  PROPERTIES SKIP_RETURN_CODE 4 LABELS fake)
set_property(TEST t_amx_numerics APPEND PROPERTY LABELS skip_return_code_4)
```
2. I19 (t/t_amx_dispatch_dtype.cpp). The check as drafted could not see which PV row feeds which head, because the
   PV test double wrote 0 into every row. Now the double writes a distinct value per row (row + 1), the check
   expects that value on the dense path and 0 on the AVX path, and each round visits the page a second time
   without clearing validity, which covers the merge line of the epilogue (the `fma` line that I6 changes).
   Quote the final code from the working tree: the helper `pv_fake_row_value`, the lambda `require_state(visits)`,
   the second visit, and the PV double. Say in the reply that this goes one step beyond his proposal and why.
   The cumulative call count in the stats block is now `2 * round + 1`.
3. I10 (t/t_amx_numerics.cpp). The transpose case has the tag `[amx_numerics][transpose]`, not `[q_pack]`.
   The `#else` placeholder case of t_amx_numerics.cpp is removed: the file now has a real case in every build,
   and the placeholder said "nothing to test". The interface header is included above the `#ifdef`.
   So in a build with the option OFF, t_amx_numerics holds exactly the transpose case (2 sections).
4. I20. Side effect: the direct include of tron/tensor/kv_cache_fwd.hpp is removed from both test files,
   because the aliases come from the interface header and nothing else in those files uses it.
5. I5 reply, WRONG SENTENCE in the draft: "The real-value coverage is t_llama_unit with the option on."
   t_llama_unit does not reach the dense AMX path: its model has one query head per KV head (n_heads 8,
   n_kv_heads 8), so the AMX path is not eligible [t/t_llama_unit.cpp:141-142, :3060-3061]. Replace the coverage
   paragraph of I5 (and any same claim in I6, T4 or Part C) with: "Unit coverage: `t_amx_dispatch_dtype` drives
   this path with kernel test doubles. Its PV double writes a distinct value per row, and a second visit covers
   the merge line. `t_llama_unit` does not reach this path, because its model has one query head per KV head.
   Real-value coverage of the epilogue is the token-identity runs in the Verification section, at the measured
   commit." Name this correction in "How this was checked".
6. Function name. The two edits (I5, I6) are in `apply_dense_amx_page`, not in `apply_page_range`
   [h/tron/models/self_attention.hpp:1734]. Fix every reply and note that says `apply_page_range` for them
   (T10 reply, combined reply, #open3, D2, D6 if present). `apply_page_range` stays correct where a reply
   speaks of the test calling it or of the pack placement.
7. T10 and the combined benchmark bullet: say "This PR's changes since that commit carry a low risk for
   performance" (not "the changes since that commit"), and add one sentence: "The head also contains main up to
   3bea58b788, which the nightly systems test measures." Reason: the final head includes 272 commits of main.
8. PR description draft (pr5022-body-round2.draft.md), for the page's Part C list of body edits: the Short
   version says "the kv_mul-4 pack and QK kernels emit the same instructions as on main" (PV has one more
   instruction, as the Verification section says); "6198824246" is named "the merge base of the measured
   commit"; Background says "Main supports only kv_mul 4 on AMX"; the two CI rows name `gcp-nix.yml` and
   `cmake-single-platform.yml`; the I13 note is one bullet without the band sentence:
   "The qwen3-4b / tp2 / 1024 row runs no PR code: the AMX kernel scores 0 key tokens in both configurations
   (`exit-reports.txt`). Its +0.56 TPS appears in all four repetitions, so it is an offset between the two
   binaries, cause unknown. The Glimmer decode gains (2.61 to 5.16 TPS) are 4 to 9 times that offset."
   The I13 reply must quote this final bullet, and say that the later duplicate rule sentence is removed.
9. T4: the kill-switch expectation stays `5 | 3 passed | 2 skipped`.

## I. Final code to quote (from the working tree at tree hash 5821ee86418d)

### t/t_amx_dispatch_dtype.cpp, helper and PV double
```
// What the PV fake writes into every dimension of output row `row`. The
// value differs per row, so the state check sees which row a head read.
constexpr float PV_FAKE_FIRST_ROW_VALUE_1 = 1.f;
constexpr float pv_fake_row_value(size_t row) {
  return PV_FAKE_FIRST_ROW_VALUE_1 + static_cast<float>(row);
}

...
void weights_times_v_128x4(
    const_v_vnni_plane_view, const float*, size_t, float* output) noexcept {
  ++probe.pv_calls;
  probe.pv_group_heads = group_heads;
  for (size_t row = 0; row < TILE_ROWS_16; ++row) {
    std::fill_n(output + row * HEAD_SIZE_128, HEAD_SIZE_128, pv_fake_row_value(row));
  }
}

```
### t/t_amx_dispatch_dtype.cpp, state check and second visit
```
    // The running-softmax state of every head in the group after `visits`
    // visits of the page. K is zero, so each score is 0, each exp is 1, m* is
    // 0 and s* is the token count per visit. v* is what PV returned for the
    // head's own row per visit: the fake's row value on the dense path, 0 from
    // the zero V on the AVX path. An epilogue that merged fewer than
    // group_heads heads, or read another head's row, fails here.
    const auto require_state = [&](float visits) {
      auto sp = state.self_attn_state.template token_scratchpad_ref_at<geometry>(0, 0);
      REQUIRE(sp.is_valid_for(kv_head));
      for (size_t offset = 0; offset < group_heads; ++offset) {
        CAPTURE(visits, offset);
        auto head_sp = sp[kv_head * group_heads + offset];
        REQUIRE(head_sp.s_star == visits * static_cast<float>(n_tokens));
        REQUIRE(head_sp.m_star == 0.f);
        const float v_expected = dense ? visits * pv_fake_row_value(offset) : 0.f;
        for (size_t i = 0; i < head_size; ++i) {
          CAPTURE(i);
          REQUIRE(static_cast<float>(head_sp.v_star[i]) == v_expected);
        }
      }
    };
    constexpr float ONE_VISIT_1 = 1.f;
    require_state(ONE_VISIT_1);
    if (packs) {
      // The pack reads one group: the group_heads heads of the visited KV head.
      const size_t group_begin = kv_head * group_heads * head_size;
      for (size_t i = 0; i < group_heads * head_size; ++i) {
        CAPTURE(i, expected[group_begin + i], probe.q[i]);
        REQUIRE(probe.q[i] == expected[group_begin + i]);
      }
    }
    // A second visit of the same page with validity kept: the epilogue merges
    // into the first visit's state. m* stays 0, so s* and v* double.
    {
      attn_stats::forward_scope stats_scope(*state.self_attn_state.stats,
          attn_stats::forward_class::decode_like, token_jobs.size(), token_jobs.size());
      state.self_attn_state.template apply_page_range<geometry>(jobs, operation,
          state.plugin_state.qs_roped, kv_head, 0, 1,
          std::span<const page_id>(page_ids), {}, visible);
    }
    constexpr float TWO_VISITS_2 = 2.f;
    require_state(TWO_VISITS_2);
```
