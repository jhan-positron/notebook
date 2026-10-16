# C++ coding guide check of jhan-vnnik-5-i4934 (175b1837b9..7a41c79edd), 2026-10-15 02:0x UTC

Short version: no violation found in the added production lines (h/), none in the added test lines.

Method: every added line of `git diff -U0 175b1837b9 7a41c79edd -- h t`, comments stripped, scanned for (1) control statements whose body is not on the same line and whose line does not end with `{` (brace rule), (2) numeric literals above 1 outside `static_assert`, `constexpr` declarations and array indices (named-value rule).

Results:

- Brace rule: one hit, `if (amx_q_packed != nullptr && k_layout_dense &&` (self_attention.hpp, the dense gate), a condition continued on the next line whose brace follows it. Not a violation.
- Named values, production code: no bare literal above 1 added. `rows &= rows - 1` (self_attention.hpp, the row loop) uses the literal 1 like the file's existing `page.offset_for(range_hint->tok_hi) - 1`. `k_convert_parallel_min = 8` (model.hpp) follows that file's idiom for its sibling constants (`k_store_block`, `k_join_timeout_s = 120`): lower-case `k_` name, value in the initializer, derivation in the comment. jhan's 2026-10-06 rule keeps `NAME_<value>` constants in the AMX kernel files and the file's own spelling elsewhere.
- Named values, tests: the new constants in t/t_amx_dispatch_dtype.cpp follow that file's `NAME_<value>` idiom (RECORDED_ROWS_32, DOMINANT_TOKEN_20, BF16_EXPONENT_BIAS_127, ...). The pattern multipliers inside `query_value` and `k_row_value` (3, 5, 37, 11, 2) are bare, like the file's existing `i % 4`, `0.25f` and `i % 8`, `0.5f` query patterns. t/t_llama_unit.cpp additions follow that file's lower-case idiom (`no_block_mask`, `rows_per_block`, `pre_bits` with `4099`/`17`-style multipliers already used by `source_bits`).
- Bool literals: `return BLOCK_COMPLETED_FALSE` keeps the function's existing named return; `true` / `false` appear only in returns and initializations.
