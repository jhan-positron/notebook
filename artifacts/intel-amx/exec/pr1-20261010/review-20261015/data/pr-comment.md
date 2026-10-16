Commit dbcb28387f applies the review threads of the two 2026-10-15 style checks (simplify-cpp-comments Check mode and the named-bool rule): 111 of the 113 threads, as accepted in the replies (no reply = accept the proposal or cut).

- 81 proposed rewrites applied as proposed, 3 in the author's own wording (the kernels/k_vnni.hpp header, the k_vnni_view and k_vnni_tensor comments), 27 cuts, 13 named bools (t_llama_unit.cpp constants WAS_VALID_FALSE, RUN_VISIBLE_IN_SOFTWARE_FALSE, KV_TRUE, KV_FALSE, PERMUTED_FALSE, WRITES_KV_TRUE; literal default template arguments in tensor/k_vnni.hpp).
- Not applied: the ROW_STRIDE_16 comment thread (rejected) and the `(void)dest;` thread in full.hpp (a question, answered in the thread).
- Checks on the working tree: 38-cell syntax matrix identical to the one at 82d05e94be (0 errors, 0 warnings in every cell), clang-format 19.1.7 clean, `git diff --check` clean. Every applied thread was re-verified against its decision by an independent agent (123 verifiers). No behaviour change: the named constants have the values the literals had.
- The 111 applied threads are resolved. Diff: +149 / -338 lines in 12 files.
