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

Not done yet:

- The product build (nix clang 19.1.7, `-std=gnu++23`), including the runtron and rinzler link. Both link `src/pos/memperf.cpp`, which replaces the global `operator new` family. The tagged form has a different signature, so no clash is expected.
- The unit tests on delphi-3bda (`t_llama_unit`, `t_amx_numerics` with and without the AMX kill switch, `t_amx_dispatch_dtype`, `t_heap_v2`), and the ASan and UBSan runs of `t_heap_v2` and `t_llama_unit`.
- objdump of `allocate_retained_storage`, `allocate_reclaimable_chunk` and the accessor wrappers against 633cb88896. The expected result is no `rep stos`, no `memset`, no loop, and identical accessor bodies. The `std::launder` cost is so far measured only in a standalone probe.
- delphi-3bda is held by the nightly CI lease until about 11:25 UTC. Draft PRs also skip the GCP Nix build and test jobs.

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

