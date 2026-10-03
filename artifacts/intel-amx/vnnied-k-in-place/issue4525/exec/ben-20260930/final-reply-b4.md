Agreed. A ticket already exists: #4588 (filed 2026-09-24, label Tech Debt, assigned to me). It covers these three reads and nothing else. For each read it records:

- the rule the read breaks,
- why clang 19 compiles it correctly today (vector accesses are tagged as possibly overlapping anything, and pointer steps are compiled to byte offsets),
- that no warning or sanitizer in our build detects it,
- the fix options.

I intended to remove this paragraph when I filed the issue. It was still in the code.

Is any of this new in this PR? Per read, with line numbers at c73e7fb2f9:

- `scaled_v_expr`: the form changed, the status did not. On main the storage was `bf16s` and the same loop stepped a `bf16s` pointer across the inner arrays of the 2-D array. b951ba9b4c changed the storage to `bf16` and added the two `reinterpret_cast<const bf16s*>` (kv_cache.hpp:2326 and :2400).
- `fill_storage_slot` (kv_cache.hpp:1647, the cast at :1652): byte-identical to main.
- The 8-lane (AVX2, `TRON_CHUNK_SIZE` 8) V accessors. `page::v` and `page::v_ptr` (kv_cache.hpp:1954-2008, the `#else` branch of `TRON_CHUNK_SIZE == 16`) and the 8-lane branch of `copy_storage_slot` (:2183-2197) are identical to main. The 8-lane branch of `page::scaled_v` (:2518) changed form in b951ba9b4c: it casts the whole `bf16s` array to `const bf16*`, where main passed `v[0]` as a `bf16s` pointer. Both forms step across the inner arrays, so the status is the same.

You also opened #4698 against this branch. This comment does not mention it, so I checked whether it fits here. It removes all three reads and this paragraph. A script compared the old and new load addresses for head_size 64, 128, 256 and 512 in both lane widths, and all are equal. All 21 CI checks on #4698 pass. On our Intel machine (AMX kernels compiled in) the four unit tests pass with #4697 and #4698 in the branch, on the AMX-on and the AMX-off tree. The counts are in the Status section of the PR description. In `t_llama_unit` the two `scaled_v_expr<64, 128>` functions (82 and 219 instructions) are identical before and after #4698 once addresses are normalized, so the change is in the source form of the loads, not in the generated code.

I merged #4698 into this branch as merge commit 8e0cf77bed. Issue #4588 will be closed with a pointer to that commit. One gap stays on record: no CI job builds the 8-lane configuration, and the 8-lane `t_llama_unit` has 131 errors before this change (#4588, none of them in kv_cache.hpp). So the 8-lane hunks are checked by reading, not by a build.

If you meant #4698 to land separately after this PR merges, say so and I will drop the merge commit before the next push.
