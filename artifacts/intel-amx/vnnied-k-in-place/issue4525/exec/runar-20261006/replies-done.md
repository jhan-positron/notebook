# Replies to post on PR 4557 (third review, 5432936425). State: edits pushed as 79478c254a + 5128a3a47e. Plain-English checked 2026-10-07, each under 100 words.

## R1 4199039224 (t/t_llama_unit.cpp:3461)
Done in 5128a3a47e. I ran bin/slice bench --update t_llama_unit on delphi-3bda (the Intel test machine, block granite_rapids_6962p, whole machine, serving stopped). The row moved from 5.187 / 5.256 / 4.936 s to 27.657 / 27.587 / 27.996 s at 1, 2 and 4 slices (a slice is one accelerator card with its CPUs and memory). The growth is not this PR's. The old row dates from 2026-09-20, and the largest cases are main's (attn-stats abort 14.2 s, dynamic attention descriptors 5.6 s). The two new cases take 0.35 s and 0.30 s. t_amx_numerics and t_heap_v2 are left out, as you suggested.

## R2 4199039245 (h/tron/tensor/v_vnni.hpp:190)
Done in 79478c254a. pair_base asserts token < Rows. Its comment names who satisfies the precondition: save_v_impl (the model's V save) takes the offset from the token's page, page::copy_from asserts both ranges, and the tests loop over one plane's rows. The two history sentences ("never checked it", "always did") are gone. Line 74 has its own thread. The cost, measured on the runtron binary with objdump (the disassembler): one compare-and-branch per pair_base call, two per copied token. The description's instruction-comparison section states it, and the instruction-identical claim is reworded.

## R3 4199039256 (h/tron/tensor/v_vnni.hpp:209)
Done in 79478c254a. v_source_row and v_destination_row assert is_aligned(row, chunk_alignment), one compare-and-branch per call. In the runtron binary the three FPGA staging closures grow by 10 instructions each. One correction: main already wraps raw pointers as aligned views at plugins/llama.hpp:1369, model.hpp:3408 and dmatensor.hpp:215. So these helpers are the first such site in the KV path, not in the tree. Validating inside view is the better fix (view.hpp:13 carries that TODO), but it is outside this PR.

## R4 4199039265 (h/tron/tensor/v_vnni.hpp:74)
Done in 79478c254a. The constant, both Cols % 32 clauses and the comment are gone. The loops step one chunk of 16 dimensions. So Cols % chunk_size == 0 (the static_assert of the view and the owner) carries the width rule, and all three bulk operations accept every plane the type admits. page::set_v and page::get_v keep their head_size % 32 clauses from main. No accepted page width changes.

## R5 4199039272 (h/tron/tensor/v_vnni.hpp:57)
Done in 79478c254a. The writable at() is removed. Nothing wrote through it. at() is now a bounds-checked read. Rows enter through append_v_row and copy_token, and the test probe pins that no view writes an element (a STATIC_REQUIRE_FALSE, a compile-time check). Both Notes say that instead of "serve fixtures". One caveat: the maintainer's API sketch had a writable at(). If he wants that surface back, I will restore it.

## R6 4199039284 (h/tron/models/kv_cache.hpp:2248)
Done in 79478c254a. The sentence now reads: "Page methods, book::append and tests go through the typed operations instead. book::fill_random is the one documented exception: it fills a whole kv_block without interpreting coordinates (Note [VNNI Packed V layout])."

## R7 4199039288 (h/tron/models/kv_cache.hpp:2190)
Done in the description. Both maintainer PRs are described as merged into this branch. The scaled_v_expr addressing rewrite and the fill_storage_slot cast removal are described as changes of this PR. The four row aliases are listed in the v_vnni.hpp bullet. The Verification section cites the objdump (disassembler) check of the head-128 loop: the two scaled_v_expr<64,128> functions have 82 and 219 instructions with and without the rewrite, identical after address normalisation. It also cites the token identity, whose kill-switch arm (AMX kernels disabled at run time) runs that loop.

## R8 4199039306 (h/system/memory.hpp:197)
Agreed, not for this PR. The four templates still call dma_allocate_aligned directly, and memset is not on the object-creation list. The class-typed callers include the two you named plus the dmatensor arrays of bf16 and fp16 (both structs with a defaulted constructor). strip has a user-provided constructor and takes placement new. It is unaffected. I will add one sentence to the Note (the wrapper covers the KV-book path only) and file a Tech Debt issue alongside #4588. Both wait for the maintainer's sign-off on the operator new[] approach, as the line-192 thread asks.

## PR-level comment (summary 5432936425)
Thank you for the review. All eight points hold, and each thread has its reply. The edits are pushed as 79478c254a (code and comments) and 5128a3a47e (the benchmark row), on top of d9e7645fee (the second reviewer's style comment). The description is updated: the two maintainer PRs are described as merged into this branch, the scaled_v_expr rewrite as a change of this PR, and the Status section carries the 2026-10-07 unit tests, token identity, instruction comparison and benchmark row. The memory.hpp sentence and its tracking issue wait for the maintainer's sign-off on the operator new[] approach.
