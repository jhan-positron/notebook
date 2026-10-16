# Draft replies for PR #4868 round 1 (placeholders: 82d05e94be = pushed head, 6220 assertions in 64 cases = t_phase1_integration counts, 266522 assertions in 66 cases = option-off t_llama_unit result)

## r4238076829 (Cursor Bugbot, pair_base unbound token)

Accepted. `store_row` and `load_row` now assert `token < Rows` before they compute the scatter or gather address (`TRON_ASSERT_LT`, compiled in release builds like the packed-V check in `v_vnni_access::pair_base`); `copy_token` inherits both checks (82d05e94be). The production callers already checked the index (`page::set_k_row` / `get_k_row` assert `i_page < page_size`, and the ranges of `copy_storage_slot` are bounded by the page), so no reachable out-of-range call existed; the typed operations are now self-checking as the V side is. The unit tests, the smokes and the 8-user cells ran again at 82d05e94be with the asserts in place (Verification in the description).

## r4238128316 (P2, staging test ignores the scratch)

Applied in 82d05e94be. The populate case now stores K rows with distinct per-(token, head, element) patterns in one packed `k_vnni_tensor` plane per head. Its K callbacks gather each head's row out of the plane into the scratch row that `populate` supplies (`load_row` into `k_destination_row`) and return the scratch, as the scheduler's callback does for a VNNI slot. After `populate`, every staged value is compared through the K swizzle (`position_ptr(t, h)[(e % nwords) * hbm_word_width + e / nwords]`, the transposition `t_gof_dma` checks on `set_position`) for all 4 tokens, 8 heads and 128 elements. Mutation check on the Granite Rapids machine: with `+ h * HW_BAKED_HEAD_SIZE` removed from the scratch address in `gof::populate`, the case fails (exit code 42: the `REQUIRE` at `t/t_phase1_integration.cpp:920` fails at the first compared element); with the file restored it passes (6220 assertions in 64 cases). A second mutation, the scheduler's callback in `full.hpp` ignoring the scratch it is given, is not covered by this unit test (the test supplies its own callbacks). What covers it: the type system excludes the most likely wrong form (under the layout `page::k()` has no overload for a VNNI slot and the packed view has no pointer access, so the callback can only return a row through `get_k_row` into a destination row), and the FPGA-attention token run gives the same tokens as `main` up to the same divergence point as the CPU-attention run, which is indirect evidence that the K the FPGA reads is right.

## r4238128323 (P2, keep main's bounds for row-major K)

Applied in 82d05e94be. The bounds now follow the layout gate: with `TRON_K_VNNI` off the first site keeps `main`'s absolute 2e-6 on `s_star` and both sites keep 0.02 on the weighted V sum; with the option on the VNNI bounds (relative 1e-6, 0.05) apply. The second site's `s_star` check was already `WithinRel(2e-6)` on `main` and is unchanged. Both builds pass on the merged `main`: 266522 assertions in 66 cases (option off) and 266453 assertions in 66 cases (option on). The description's Open item says so.

## r4238128330 (P3, poison-test claim)

Applied in 82d05e94be, with your two sentences. The description's test summary says the same (dead-token values cannot affect live scores; the test does not detect a stray read).

## r4238128350 (optional, k_destination_row)

Applied in 82d05e94be: the stack row is built with `k_destination_row<geometry.kv.head_size>(row).set(kout)`; the bf16 branch keeps `k_source_row(kout)` as you said.

## PR comment: the review body's description points and the plain-English check

Description updated at 82d05e94be (the edit is visible in the description's history):

- CI coverage: the paragraph now distinguishes what required CI runs (the first three `t_k_vnni_layout` cases exercise the packed owner, the row operations and the reader in every build; only the cache case depends on the option; `t_amx_dispatch_dtype` without dispatch is a `SUCCEED` placeholder) from what it misses (the option-dependent cache and model paths). The exception and #4865 stay.
- The next PR's effect is stated as the intended result, to be measured at that PR's head.
- The cause of the loss against `main` is stated with the decomposition that supports it: `baseoff - base` (main's AMX kernel) plus `newoff - baseoff` (the layout, the reader and the row store with AMX off) equals `new - base` within `new - newoff`, which is inside the band in both cells.
- The plain-English proposal is adopted as the base of the description, with these differences: the Short version keeps the specifics of what is stored, who reads it and the state of the option; the decision rule of the earlier "resolved" pass pairs is given (paired t at least 2.26 in magnitude and a difference of at least 1 %) instead of "insufficient data"; the review-fix items are added to The changes; the Verification numbers are those of the re-run at 82d05e94be.
