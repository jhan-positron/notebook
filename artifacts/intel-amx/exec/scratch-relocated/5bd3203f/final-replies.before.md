# Replies to post on PR #4557 (one file per reply is split by the checklist)

Each reply goes under the review comment named in its heading, with `in_reply_to` set to that id.
B1 (4133613638) is already answered by jhan in comment 4158498407 and is not repeated here.

## B2, reply under 4133643149

Agreed. The layout is called VNNI everywhere else: the file name, the `v_vnni_*` types, and the kernel comments. The Note title should say it too.

Commit 76502ce5b2 renames the Note to `Note [VNNI Packed V layout]` at all 16 places where the name appears (the header and 15 references, in 7 files) and widens the underline to match. I applied it by hand rather than through the suggestion button. The button would have renamed the header only, and 15 other comments reference the title. The PR description line that names the Note is updated too.

The Note never spelled out VNNI. I added one clause to it: "That is the VNNI layout (named after Intel's Vector Neural Network Instructions)". Comment-only change. clang-format 19.1.7 reports no change. lint-notes (the repo's checker of Note references) finds no dangling reference.

If you would rather have the literal rename only, say so and I will drop the added clause.

## B3, reply under 4133869073

Thanks for working through it. Your second reading is right on the main point. On main, `try_make_unique_dma_for_overwrite` called `dma_allocate_aligned` directly. The accessors then cast the bytes with a plain `reinterpret_cast`. No `kv_block` ever started its lifetime. A member access through such a pointer is undefined behavior (N4950, the C++23 draft standard, [basic.life]/6). GCC 14.3 and 11.4 with -Wall -Wextra -Wpedantic give no warning on a 17-line sample of that pattern, and ASan/UBSan (AddressSanitizer and UndefinedBehaviorSanitizer) run it clean. I did not measure clang.

Two details, so that the Note states the rule exactly:

- `operator new` is one item on the list, not the only one. [intro.object]/13 also names starting the lifetime of a `std::byte` array, and its note points to `malloc` and its relatives, `memcpy`/`memmove`, `bit_cast`, `start_lifetime_as` and `allocator_traits::allocate`. `dma_allocate_aligned` is on none of these lists. That is why the allocation now goes through a function named `operator new[]`.
- `v_vnni_tensor` needs the same care as the old `kv_block`, not more. Both are implicit-lifetime types: types that an allocation may create without a constructor call ([class.prop]/9). The old `kv_block` was an aggregate of arrays. The new one still is. `v_vnni_tensor` has a trivial implicit default constructor and a trivial destructor. The `static_assert` inside `kv_block` (on `v_storage`) and the two in the accessors keep that true. So the rule was the same before and after. What changed is that the allocation now satisfies it.

I reworded the Note in commit a52ce4db25 and tightened it in 55f0068cbf and 34b157326f (comment only, no code change). It now says what the KV book does, what an implicit-lifetime type is, which operations create such objects, why `dma_allocate_aligned` is not one of them, what goes wrong without the wrapper, and why the unit tests cannot tell the difference (`aligned_alloc` is on the list, [c.malloc]). The title and the facts of the old paragraphs stay. Does the new text read clearly to you?

## B4, reply under 4134028988

Agreed. A ticket already exists: #4588 (filed 2026-09-24, label Tech Debt, assigned to me). It covers these three reads and nothing else. For each read it records:

- the rule the read breaks,
- why clang 19 compiles it correctly today (vector accesses are tagged as possibly overlapping anything, and pointer steps are compiled to byte offsets),
- that no warning or sanitizer in our build detects it,
- the fix options.

I intended to remove this paragraph when I filed the issue. It was still in the code.

Is any of this new in this PR? Per read:

- `scaled_v_expr`: the form changed, the status did not. On main the storage was `bf16s` and the same loop stepped a `bf16s` pointer across the inner arrays of the 2-D array. b951ba9b4c changed the storage to `bf16` and added the two `reinterpret_cast<const bf16s*>` (kv_cache.hpp:2326, :2400 at c73e7fb2f9).
- `fill_storage_slot` (kv_cache.hpp:1652): byte-identical to main.
- The 8-lane (AVX2, `TRON_CHUNK_SIZE` 8) V accessors (kv_cache.hpp:2462): identical to main.

You also opened #4698 against this branch. This comment does not mention it, so I checked whether it fits here. It removes all three reads and this paragraph. A script compared the old and new load addresses for head_size 64, 128, 256 and 512 in both lane widths, and all are equal. All 21 CI checks on #4698 pass. On our Intel machine the four unit tests pass at the branch head faf8ee42ca on the AMX-on tree (AMX kernels compiled in) and the AMX-off tree (compiled out). That head has #4697 and #4698 in it. Counts: t_llama_unit 44 cases / 244522 assertions on both trees (the test case "packed V rows keep their bits through set_v, get_v and at()" alone 20755), t_amx_numerics 12301 assertions on the AMX-on tree (1 on AMX-off, the AMX cases compiled out), t_amx_dispatch_dtype 1559 (1 on AMX-off), t_heterogeneous_scheduler 1900 on both trees, and `make lint-notes` rc 0 (no dangling Note reference). The `t_llama_unit` count is lower than the 252720 of c73e7fb2f9. The `v_vnni_row` removal (the other thread) dropped test-only checks.

I merged #4698 into this branch as merge commit 8e0cf77bed. Issue #4588 will be closed with a pointer to that commit. One gap stays on record: no CI job builds the 8-lane configuration, and the 8-lane `t_llama_unit` has 131 errors before this change (#4588, none of them in kv_cache.hpp). So the 8-lane hunks are checked by reading, not by a build.

If you meant #4698 to land separately after this PR merges, say so and I will drop the merge commit before the next push.

## B5, reply under 4134076112

You are right that nothing in production uses it. I dropped it in commit faf8ee42ca.

Why it was there: your PR #4424 review asked for the `tensor` / `dtensor` `expr` precedent (review 5270587330). I followed that. Your later sketch had `at()` only and no `operator[]` (comment 5765866077). The two differ on `operator[]`, and the code followed the first. This commit moves it to the second.

What the commit removes: `v_vnni_row` with its comment, the two `operator[]` overloads of `v_vnni_view`, the `expr` base of `v_vnni_view`, the row's forward declaration in kv_cache_fwd.hpp, and the `expr.hpp` include in v_vnni.hpp. Net: 33 lines added, 140 removed, in 4 files. No production path changes. The AMX PV kernel (probabilities times V) and `scaled_v_expr` read the plane in place through `detail::v_vnni_access`, as before. `append_v_row`, `load_row` and `copy_token` move whole token rows, as before.

What element access is now: `at(token, dim)` only, bounds-checked, writable through a writable view and read-only through a const one. `v_vnni_view` is a plain struct. That is the public surface of your sketch. The packed-K child (#4424) then needs no `k_vnni_row` either.

Tests: the only user of the row was one test section that built a host `tensor` from a packed view. That section now reads every (token, dim) of a filled page back through `at()` for both parities. The row-only static checks (`matrix_row_writes`, `row_writes`, the `v_row_t` probes) are gone. The static checks on the view stay: no pointer constructor, no default constructor, writable converts to read-only and not back, no view of a temporary owner, `at()` writes through a writable view and not through a const one. On our Intel machine the four unit tests pass at faf8ee42ca on the AMX-on tree (AMX kernels compiled in) and the AMX-off tree (compiled out). Counts: t_llama_unit 44 cases / 244522 assertions on both trees (the test case "packed V rows keep their bits through set_v, get_v and at()" alone 20755), t_amx_numerics 12301 assertions on the AMX-on tree (1 on AMX-off, the AMX cases compiled out), t_amx_dispatch_dtype 1559 (1 on AMX-off), t_heterogeneous_scheduler 1900 on both trees, and `make lint-notes` rc 0 (no dangling Note reference). The `t_llama_unit` count is lower than the 252720 of c73e7fb2f9 by exactly the dropped test-only checks.

If you would rather keep the expression interface, say so and I will restore it.

## B6, reply under 4134925164

Thanks for #4697. I checked it against c73e7fb2f9. It is correct as written. Every caller passes the row width explicitly. The element type deduces from the pointer. The DMA (direct memory access) flag of the executor's V buffer is kept, through `v_buffer_t::dma` in model.hpp. clang-format 19.1.7 reports no change.

I took it by fast-forward: the branch tip moved to your commit 8bbbb7c82d, no new commit. Your commit id and authorship stay. GitHub should then mark #4697 as merged once I push. If it does not, I will close it with a note. #4698 went in after it as merge commit 8e0cf77bed (see my reply on the other thread). Then my comment-only commits and the `v_vnni_row` removal follow.

On testing: your PR's own CI run at 8bbbb7c82d passed Build Tron, Test host and Test FPGA. That run builds without `TRON_AMX_DISPATCH` (the CMake option that compiles the AMX attention kernels). I built the branch head faf8ee42ca on our Intel machine. That head has your change in it. I ran t_llama_unit, t_amx_numerics, t_amx_dispatch_dtype and t_heterogeneous_scheduler on the AMX-on tree (AMX kernels compiled in) and the AMX-off tree (compiled out). All pass. Counts: t_llama_unit 44 cases / 244522 assertions on both trees (the test case "packed V rows keep their bits through set_v, get_v and at()" alone 20755), t_amx_numerics 12301 assertions on the AMX-on tree (1 on AMX-off, the AMX cases compiled out), t_amx_dispatch_dtype 1559 (1 on AMX-off), t_heterogeneous_scheduler 1900 on both trees, and `make lint-notes` rc 0 (no dangling Note reference).

The remaining spelled-out views in kv_cache.hpp (three `const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<page_size, head_size>>` sites) are two-dimensional plane views, not rows. They stay as they are. One row view is left spelled out: the `page_supports_uniform_kv_access` probe in t_llama_unit.cpp. I can convert it to `v_row_view` in a small commit if you want every row view to go through the aliases.

Any objection to the fast-forward?
