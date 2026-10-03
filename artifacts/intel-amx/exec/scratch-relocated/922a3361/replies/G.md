C++ guide observation: addressed in commit 9e813a8ce5.

Named in the added code:

- k_vnni.hpp: `alignas(LINE_BYTES_64)` in `block_to_vnni` and `block_to_rows`. `BIT_1` with `block_bit(c)` and `offset_bit(offset)` build the single-bit masks of the page's block and saved-row state. Every reader tests a mask bit through them instead of shifting and masking with `1u`. `ROW_ALIGNED_TRUE` and `ROW_DMA_FALSE` are the view flags of a row at `row_ptr`: the row starts on a 64-byte line, and it is not DMA (direct memory access) memory.
- self_attention.hpp: the row view uses the two flags and drops the explicit `sseq<1>`. The default stride `row_major<seq<head_size>>` is the unit stride the dotter requires. It is the same form the page's own row views use (`page::k`). `ROW_MAJOR_DENSE_TRUE` names the `true` that the dense-page check returns for a row-major slot (a row-major slot has no layout gate to pass).
- kv_cache.hpp: `EAGLE_STORAGE_SLOTS_1` (the one extra state entry for the EAGLE storage, used by speculative decoding), `BLOCK_COMPLETED_FALSE`, `CONVERTED_FALSE`, `CONVERTED_TRUE`. The copy's block loop is bounded by the range end instead of computing a last index. The empty-range assert and the full mask are written with zero as the only literal (`count != 0`, `~uint64_t{}`).
- tests: `LINE_BYTES_64` for the added row buffers, `SUPPORT_EAGLE_TRUE`, `NEXT_ROW_1`, `LAST_OF_BLOCK_0_15`, `REPEAT_FALSE`, `RECORD_ROWS_TRUE`, `RECORD_ROWS_FALSE`, `CONVERTED_FALSE`, `CONVERTED_TRUE`, `PAGE_1`, `PAGE_2`, `OTHER_OPERATION_1`.

Left as literals, listed as the guide asks:

- index-zero arguments in the tests (KV head 0, page 0, slot 0): 39 lines, written the same way as the pre-existing lines of those files.
- the `static_assert`s that check a constant's numeric suffix against its value ("every constant's name states its value"), Catch2 (the test framework) test and section names, `TRACE_EVENT` strings.
- lines this branch does not add: `alignas(64) float qf` in k_vnni.hpp (line 328 at 452b2052c9, line 344 at 9e813a8ce5; from PR #4424), eight pre-existing `alignas(64)` lines in t_k_vnni_layout.cpp, `/*repeat=*/true` in t_amx_dispatch_dtype.cpp.

Two notes:

- `ROW_ALIGNED_TRUE` and `ROW_DMA_FALSE` are defined in k_vnni.hpp. PR #4557 defines `tron::VIEW_ALIGNED_TRUE` and `VIEW_DMA_FALSE` in kv_cache_fwd.hpp. This branch does not include that PR. After both merge, one pair should be removed.
- Those two flags are `constexpr`. They are template arguments of `const_view`, and a template argument must be a compile-time constant.
