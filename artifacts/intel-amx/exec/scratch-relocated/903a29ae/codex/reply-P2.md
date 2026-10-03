Confirmed and fixed in 977826a272, with the tests completed in 76ef81e2fc.

The cause: `k_vnni::qk_group` (the AVX-512 reader of the VNNI K layout) kept one accumulator register per query head and rejected a group of more than 16 heads with a `static_assert`. `TRON_K_VNNI` selects every 128-dimension K/V head, so `attention_geometry{32, {1, 128}}` reached that assert through `apply_page_tok`. The limit came from PR #4424; this port kept it.

The fix: `qk_group` scores a group wider than 16 heads in passes of 16 (the first 16 heads, then the rest, which may split again). Every head's scores are its own accumulation. So the split changes no head's add order. A group of at most 16 heads takes the same single pass as before. An independent check compared the split reader against a single-pass copy of the previous kernel for 17, 20, 32 and 33 heads with bf16, float and fp16 queries, 26 live masks each: no mismatching score.

Tests added:
- `t_k_vnni_layout`: the reader-versus-dotter case runs for 4, 20 and 32 query heads (one pass, an uneven split, two full passes), with bf16, float and fp16 queries, the same masks, NaN poison and tolerance as before.
- `t_llama_unit`: a case that instantiates `apply_page_tok` for 32 query heads on one 128-dimension K/V head in both builds (with and without `TRON_K_VNNI`) and runs it on a page whose query mask excludes every token. At the previous head it does not compile with the option on.

Verified at 76ef81e2fc: both tests pass on claude-box (AVX-512 host) with `TRON_K_VNNI` on and off, and on delphi-3bda (real AMX, VNNI build with ingest models): `t_k_vnni_layout` 1011650 assertions / 5 cases, `t_llama_unit` 246843 / 46, `t_amx_numerics` 12813 / 5, `t_amx_dispatch_dtype`, `t_heterogeneous_scheduler` and `t_phase1_integration` all pass.
