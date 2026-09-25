## Short version

PR #4557 starts the `kv_block` lifetimes with a separate placement-new pass, `construct_kv_blocks`, after every arena allocation. This draft deletes that pass. The DMA allocation now creates the objects itself, and the three accessor casts go through `std::launder`. The typed V owner (`v_vnni_tensor`) stays inside `kv_block`.

Stacked on #4557 (base branch `jhan-kv-typed-tensors`). If it is accepted, the two commits can be folded into #4557.

## Words used here

- **kv_block**: the struct that holds the K plane and the V plane of one KV head for one 64-token page.
- **arena, chunk**: one DMA allocation that holds many kv_blocks. The retained arena holds the full-history slots. A reclaimable chunk holds some pages of the sliding-window slots.
- **placement new**: `::new (p) T[n]`. It starts object lifetimes at an address without allocating.
- **implicit object creation**: a C++20 rule (paper P0593R6). Some operations create objects of implicit-lifetime types without running any code. Implicit-lifetime types include scalars, arrays and classes with a trivial constructor and destructor. A call of any function named `operator new[]` is one such operation (N4950 [intro.object]/13).
- **std::launder**: a C++17 function that turns an address into a pointer to the object that lives there.
- **UB**: undefined behavior. The C++ standard gives the program no meaning.

## Why construct_kv_blocks shows a design defect

- The DMA pool (`dma_allocate_aligned`) is an ordinary function, so C++ creates no objects in the memory it returns. The book therefore had to start the lifetimes after the fact.
- The pass repeats the slot offset formula of the accessors [kv_cache.hpp:1487-1491 and 1516-1524 at 633cb88896]. No test can catch drift between the two copies. The pass emits no instructions, and the unit-test allocator (`aligned_alloc`) creates objects by itself.
- The pass throws away the pointer that `::new` returns. The accessors cast `uint8_t*` to `kv_block_t*` [kv_cache.hpp:1593, 1602, 1642]. In strict C++ that pointer still points at the byte, not at the new object ([expr.static.cast]/14, [basic.life]/8 Note 5). So the pass does not complete what its Note claims.
- The same gap existed on main for `kv_block` member access. #4557 made it visible, because `v` became a class type with member functions.

## What changes

Commit 1, "Create the KV blocks in the DMA allocation, not in a second pass":

- `h/system/memory.hpp`: a tag type `dma_allocation_t` and a global `void* operator new[](size_t, dma_allocation_t, std::align_val_t) noexcept` that forwards to `dma_allocate_aligned`. `try_make_unique_dma_for_overwrite` calls it directly. Its only callers are the KV book [kv_cache.hpp:1289, 1429, 1441]. The wrapper writes no bytes. New Note [DMA allocation creates objects].
- `kv_cache.hpp`: delete `construct_kv_blocks`, `RECLAIMABLE_FALSE/TRUE` and both calls. Wrap the three accessor casts in `std::launder`. Rewrite Note [KV block lifetime]. The uniform accessor now asserts the trivial-type traits, which only `construct_kv_blocks` checked before.
- Tests: `kv_block` and `v_vnni_tensor` must stay trivially destructible [t_llama_unit.cpp]. The fallible DMA factory must return the requested 64-byte alignment [t_heap_v2.cpp].

Commit 2, "Declare kv_block::k as a plain bf16 array":

- `kv_block::k` changes from an array of `bf16s` SIMD vectors to `alignas(kv_block_alignment) bf16 k[page_size * head_size]`. The bytes, the alignment and the row order stay the same. `k_view` builds its views with no `reinterpret_cast`. This removes a read of vector storage as bf16 values, which is outside ISO C++ ([expr.add]).
- This commit is separate because it touches native K. The agreed design said native K keeps its storage. Drop this commit alone if that rule should hold.

| | #4557 as is | this draft | #4584 (draft, other route) |
|---|---|---|---|
| Placement new in kv_cache.hpp | 2 | 0 | 0 |
| Second pass over the layout | yes | no | no |
| Accessor pointer points at the kv_block | no (discarded result) | yes (`std::launder`) | no kv_block objects; views from `bf16*` |
| V owner inside kv_block (sketch items 3 and 5) | yes | yes | no |
| Files changed vs #4557 head | none | 5 files, +90/-70 lines | 6 files, +280/-258 lines |

#4584 takes the other route: plain bf16 arenas, no `kv_block`. It removes more of the remaining non-ISO reads (listed below). But it drops the owner inside `kv_block` that the reviewing maintainer's sketch asks for, and it changes about 540 lines.

## How this design was chosen

Five candidates were compared:

- #4557 as is.
- #4557 plus `std::launder`.
- This design.
- The #4584 design.
- Plain V arrays as on main.

Three independent reviews each took one angle: object-model correctness, maintainability and reviewer fit, and delivery risk. Mean scores (1 to 10): this design 6.8, #4557 plus `std::launder` 6.7, #4557 as is 5.5, the #4584 design 5.2, plain arrays 2.2. This design was the only candidate in every review's top three. All three reviews said #4557 should not merge with the discarded `::new` result.

## Verification

Done:

- `clang-format` 19.1.7 `--dry-run --Werror` on the changed files, and `git diff --check`.
- Syntax-only compile on claude-box. It used the clang 19.1.7 driver from the zig 0.14.0 package, the product's libstdc++ 14.3.0, glibc and dependency headers copied from the build host, and the product compile flags. `t_llama_unit`, `t_amx_numerics`, `t_amx_dispatch_dtype`, `heterogeneous_scheduler_compile`, `t_heap_v2` and `amx_attn.cpp` (AMX-on tree), plus `t_llama_unit` (AMX-off tree): 0 errors, 0 warnings for each commit.
- 8-lane build: it already fails on the #4557 head in headers this PR does not touch (130 errors in the `t_llama_unit` unit). The error set is the same after each commit, ignoring line numbers.
- Grep gates: 0 `::new` and 3 `std::launder` in kv_cache.hpp, 0 `construct_kv_blocks` in the tree.

On delphi-3bda, 2026-09-24 13:14-13:24 UTC (our half, nix clang 19.1.7, the #4557 test tree with this branch's files; md5 of the 5 changed files checked against the branch):

- AMX-on tree, every target: builds, including runtron and rinzler. Both link `src/pos/memperf.cpp`, and the tagged form does not clash with its replacements. The one failing target is `t_rinzler`, which fails the same way on main (t/t_rinzler.cpp:5316, `read_stats_counter` needs an ingest model).
- Unit tests, AMX-on and AMX-off trees: `t_llama_unit` 252720 assertions in 44 test cases (252718 before, plus the 2 new checks), `t_amx_numerics` 12301 assertions with real AMX and 2060 with the kill switch, `t_amx_dispatch_dtype`, `t_heterogeneous_scheduler`, `t_heap_v2` (8242 assertions, including the new alignment check): all pass.
- `make lint-notes`: exit 0.
- Machine code of `t_llama_unit` (AMX-on), compared function by function with the previous #4557 build, after removing layout-only differences (addresses and rip-relative offsets):
  - 261 of 317 KV-cache functions are instruction-identical, including `copy_storage_slot`, `append`, `copy_from`, `slot_page`, `fill_storage_slot` and the `scaled_v_expr` instantiations. `std::launder` adds no instructions there.
  - `allocate_retained_storage` and `allocate_reclaimable_chunk` are now small enough to be inlined into their callers: the book constructor (+23 to +44 instructions), `reserve_token_range` (+36) and `restore_reclaimable_kv_storage` (+42). These run once per arena or chunk allocation. They still have 0 `rep stos`, 0 `memset` calls and the same vector stores, so no clearing was added.
  - 10 Catch2 test bodies differ in a few lines with the same instruction count. The likely cause is the assertion line numbers, because t_llama_unit.cpp gained 3 lines (not checked line by line).

### runtron on delphi-3bda, 2026-09-24 14:02-18:00 UTC

Model qwen3-4b-instruct-2507, tensor parallel 2 (cards 90:00.0 and 93:00.0, CPU socket 1). Three binaries built from the same preset (cross-avx512, AMX dispatch on): main 996f58ec82 (the base of #4557), #4557 633cb88896, and this branch c73e7fb2f9.

Correctness: 1 user, temperature 0, `--pay-for-determinism`, seed 1, 256 generated tokens. All three binaries produced identical tokens in every case:

- CPU attention at prompt 1024 and 8192, with AMX and with the AMX kill switch (`TRON_AMX_DISABLE=1`), plus repeat-run controls.
- FPGA attention at prompt 1024 and 8192.

Performance: 8 users, 256 tokens, 3 repetitions, binaries interleaved inside each repetition. "Inside band" means the difference is at most max(2 x the larger standard deviation, 0.4 TPS per user or 0.15 s), the rule of the #4557 test on 2026-09-22.

| Path | Prompt | TPS per user (main / #4557 / this) | #4557 vs main | this vs main | this vs #4557 |
|---|---|---|---|---|---|
| AMX, CPU attention | 1024 | 79.50 / 79.81 / 79.83 | inside | inside | inside |
| AMX, CPU attention | 2048 | 52.35 / 52.45 / 52.61 | inside | inside | inside |
| AMX, CPU attention | 8192 | 17.12 / 17.06 / 17.04 | inside | inside | inside |
| FPGA attention | 1024 | 125.08 / 125.07 / 125.63 | inside | +0.4 % (faster) | +0.4 % (faster) |
| FPGA attention | 8192 | 61.25 / 61.26 / 61.22 | inside | inside | inside |

Time to first token was inside the band in all of those cells.

With the AMX kill switch (the AVX path), this branch measured slower than #4557 in two cells:

- Prompt 8192 prefill: +1.25 s (+1.0 %) of about 123 s. A second and a third session measured +1.25 s and +1.20 s.
- Prompt 1024 decode: -0.9 % TPS per user. Against main it is -0.2 %, because #4557 measured +0.7 % above main in that cell.

Both effects also appear with commit 1 alone, so K1 does not cause them. But they do not come from changed attention code:

- 1646 of the 1676 KV-cache and attention functions of the two runtron binaries have identical instructions, after removing address-only differences. The only functions that differ are the allocation paths (book constructor, `reserve_token_range`, restore), which run once per allocation.
- 132 of the 135 qwen3-4b attention functions start at a different offset within a 64-byte line, because the removed allocation code shifts everything after it.
- With both branches rebuilt with `-falign-functions=64` (every function starts on a 64-byte boundary), the differences shrink to +0.21 s (+0.2 %) at prompt 8192 and +0.2 % TPS at prompt 1024. Both are inside the band. The same session measured +1.20 s and -0.9 % for the normal builds.

So the kill-switch differences come from code placement, not from this change.

Scripts: `exec/i4587-20260924/` (chain.sh, iso.sh, align.sh). Summaries and logs are kept with the issue #4525 notes.


Not done: ASan and UBSan runs of `t_heap_v2` and `t_llama_unit`. Draft PRs skip the GCP Nix build and test jobs.

## Open question for the reviewing maintainer (not posted)

The sketch says "The page arena must construct the actual storage type." Does creation by the allocation call satisfy that? If the answer is no, the fallback is #4557 plus `std::launder` at the three casts, with its Note corrected.

## Still outside ISO C++ (unchanged here)

- `scaled_v_expr` steps through V with vector pointers.
- `fill_storage_slot` (test only) walks one `bf16*` across K and V.
- The 8-lane V accessors read `bf16s` arrays as bf16 values.
- The EAGLE `x_data` casts.
- The intrinsic and AMX tile loads.
- `token_tree.hpp:305-314` has the same discarded-placement-new pattern.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
