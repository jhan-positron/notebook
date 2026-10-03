## Short version

This PR addresses Ben's review comments at PR #4424, model code directly work on specific data layout and it makes code hard to maintain. Issue #4525 was raised to track the issue. This PR (part of #4525) adds typed views to KV cache, instead of bare `bf16` pointers: a typed owner, view and row for the packed V plane, and a typed view for the native row-major K plane. Stored bytes, conversions, and cache behavior stay unchanged. The KV blocks now come into existence in the call that allocates their memory, with no separate construction pass.
The change passed the machine test on delphi-3bda (identical tokens in every arm, no measurable performance change).

### Not in this PR
PR #4424 (the packed-K child) is unchanged. After merging this PR, we will rebase PR #4424 and update its code to use the new tensor data type. The public API in `h/libtron.hpp` is untouched.

## Words used here

| Term | Meaning |
|---|---|
| packed V, VNNI layout | The V plane's storage order in the 16-lane build. VNNI (Vector Neural Network Instructions) is Intel's name for the pair-interleaved operand order this layout follows. Tokens 2i and 2i+1 are interleaved value by value. One 64-byte vector load therefore holds 16 dimensions of one token pair: the even token in the low half and the odd token in the high half of each 32-bit lane. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. Address formula: `plane[(token/2)*(2*D) + 2*dim + token%2]` for D dimensions per row. |
| native K | The K plane's storage order on `main`: one row of head_size `bf16` values per token (row-major). |
| AMX, AVX-512, AVX2 | Intel instruction sets. AMX is the tile matrix unit the attention kernels use for dense (fully filled) 64-token pages. AVX-512 is the 512-bit vector unit of the software path. AVX2 is the older 256-bit vector instruction set. |
| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (16 fp32 values per vector register: AVX-512, the production build) or 8 (AVX2). Packed V exists only in the 16-lane build. The 8-lane build keeps row-major V. |
| AMX-on build, AMX-off build | Configured with `TRON_AMX_DISPATCH=ON` (the AMX kernels are compiled in) or `OFF` (they are not; the configuration the required CI builds). The kill switch below is a run-time setting inside an AMX-on build. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary skips the AMX kernels and runs the AVX-512 software path. |
| owner, view, row | `v_vnni_tensor` owns one aligned V plane. `v_vnni_view` is a non-owning matrix view (rows are tokens, columns are dimensions) that holds the address formula. `v_vnni_row` is one token's row as an expression, readable through the existing `expr` interface. |
| retained slot, sliding-window slot | A KV slot is one layer's K and V storage. A retained slot keeps every token of the sequence. A sliding-window slot keeps only a recent window of tokens. |
| arena, chunk | The raw byte buffers a book allocates for its KV blocks. The accelerator cards read them directly (DMA, direct memory access). One whole-book arena holds the retained slots. Since PR #4455 on `main`, page-aligned chunks hold the sliding-window slots (PR #4456 adds the reclamation of expired chunks in the scheduler). |
| even/odd partner rule | Appending an even token also writes zeros into its odd partner's half of the pair. Appending an odd token merges into the pair and leaves the even half alone. |
| arm | One binary-plus-configuration combination under test, for example `main` with the kill switch. |
| A/B, A/A repeat | A/B: the branch binary against the `main` binary in the same configuration. A/A: the same binary and configuration run twice, as a control for run-to-run noise. |
| rc | Return code of a command; 0 means success. |

## What changes

- **`h/system/memory.hpp`**. A tag type `dma_allocation_t` (an empty type whose only job is to select an overload) and a global `void* operator new[](size_t, dma_allocation_t, std::align_val_t) noexcept` that forwards to `dma_allocate_aligned`.
  - `try_make_unique_dma_for_overwrite` now gets its memory through this `operator new[]`. Its only production caller is the KV book (`t_heap_v2` also tests it directly).
  - In C++, a call of any function named `operator new[]` implicitly creates objects in the memory it returns [N4950 (the C++23 draft standard) intro.object/13]. This covers only implicit-lifetime types, for example classes with a trivial constructor and destructor. No constructor runs, and no bytes are written.
  - Note [DMA allocation creates objects] explains the rule.
- **`h/tron/tensor/kv_cache_fwd.hpp`** (new). Forward declarations of the packed-V types, and the aliases `native_k_view<Rows, Cols>` / `const_native_k_view<Rows, Cols>` for the existing row-major `view` / `const_view` types. The header holds no vector intrinsics. So `h/tron/kernels/amx_attn_iface.hpp` can name the typed kernel parameters and stay intrinsics-free.
- **`h/tron/tensor/v_vnni.hpp`** (new).
  - `v_vnni_tensor<Rows, Cols>`: the owner, one `bf16` array aligned to `V_PLANE_ALIGNMENT_64` bytes, trivially copyable, `as_view()` on lvalues only.
  - `v_vnni_view<T, Rows, Cols>`: the address formula, a private pointer constructor, conversion from writable to const only, `operator[]` returning a logical row, bounds-checked `at()`.
  - `v_vnni_row<T, Cols>`: an `expr` whose `chunk()` exists in the 16-lane build and is deleted in the 8-lane build.
  - `detail::v_vnni_access`: the plane and pair-base addresses for the kernels and the bulk operations.
  - The packed operations moved here from `kv_cache.hpp` with their bodies unchanged: `append_v_row` (one token's row in, under the even/odd partner rule), `load_row` (one row out), `copy_token` (token to token).
  - Note [Packed V layout] documents the layout and the access rules.
- **`h/tron/models/kv_cache.hpp`**.
  - `kv_block::v` is a `v_vnni_tensor` with the size and alignment of the array it replaces (checked by `static_assert`).
  - `kv_block::k` is a plain `bf16` array of `page_size * head_size` values. It has the same bytes, alignment and row order as the array of `bf16s` SIMD vectors it replaces (SIMD: single instruction, multiple data. One `bf16s` fills one vector register.). `k_view` now builds its views from this array with no `reinterpret_cast`.
  - `page::set_v` and `page::get_v` take a typed, aligned, unit-stride row (`const_view<Source, true, Dma, seq<head_size>, sseq<1>>` and `view<Destination, ...>`) instead of a pointer.
  - `page::v_packed()` returns the const packed view of one page and KV head for the kernel.
  - `book::append` copies V through `copy_token`.
  - `scaled_v_expr` (the software path's weighted sum) takes the packed view.
  - `page::v_data` and `kv_block::v_base` are removed.
  - Note [KV block lifetime]: the `kv_block` objects in an arena or chunk come into existence at the allocation call (see `h/system/memory.hpp` above). The accessors reach them through `std::launder` (the standard function that turns an address into a pointer to the object that lives there). A plain cast of the byte address would still point at the bytes, not at the `kv_block` objects. No placement new and no second pass over the arena remain. Every block type stays trivially default-constructible, trivially copyable and trivially destructible (checked by `static_assert`). The object-creation rule of the allocation call covers only such types.
  - Note [Zero-Initialized V Slots] now names the typed operations.
- **`h/tron/models/model.hpp`**. `save_v_impl` passes the V source row as a typed view whose element type and DMA flag come from the V buffer's type.
- **`h/tron/models/self_attention.hpp`, `h/tron/kernels/amx_attn_iface.hpp`, `src/tron/kernels/amx_attn.cpp`**. `qk_rowmajor_128x4` takes `const_native_k_view<64, 128>`. `weights_times_v_128x4` takes `v_vnni_view<const bf16, 64, 128>`. The kernel bodies read the plane pointers through the typed views. The tile loads are unchanged.
- **`h/tron/scheduler/full.hpp`**. The FPGA staging callback `v_head_fn` unpacks a token's V row through `get_v` into a typed destination row.

## Response to the reviewer's comments on #4424

Here are specific points raised at #4424. Sources: the maintainer's [tensor-interface review](https://github.com/positron-ai/tron/pull/4424#pullrequestreview-5270587330) and [API sketch](https://github.com/positron-ai/tron/pull/4424#issuecomment-5765866077) on #4424.

| Point | In PR #4557 | Same as suggested? |
|---|---|
| Encapsulate the VNNI representation. Too many pointers say nothing about the layout they point to. | The packed V plane is reached only through an owner, a view and a row type with no public pointer. The native K plane reaches the QK kernel as a typed view. `page::v_data` and `kv_block::v_base` are removed. |
| Follow the `tensor` / `dtensor` precedent: one interface built on `expr`, so code can convert, slice and compute on any tensor type. | `v_vnni_view` and `v_vnni_row` inherit `expr`. `operator[]` returns a logical row, and `chunk()` reads a row through the packed formula. A host tensor can be built from a packed view (tested). |
| Introduce a `vnni_tensor` type for a VNNI-packed rank-2 tensor. | `v_vnni_tensor<Rows, Cols>` for the packed V plane. |
| Give it the usual tensor operations, in particular row-wise load and store. | `append_v_row` (row in), `load_row` (row out) and `copy_token` (token to token) keep the existing vector bodies. Element reads go through `expr`. |
| No bare `bf16_t*` (tron's `bf16`) values without an indication of the layout. | The packed V plane (16-lane build) and the native K plane cross the cache and kernel boundaries as typed views. A bare pointer or the other plane's view is a compile error (tested with `STATIC_REQUIRE`). The 8-lane build keeps its row-major V path unchanged. |

Summary: the review's five points are addressed for the planes this PR covers. The packed-K half of each point waits for #4424. 


## Verification


### Machine test (delphi-3bda, qwen3-4b `ingested-qwen-3-4b-instruct-2507-tp2`, `runtron --instance 2,4` on cards 90:00.0 and 93:00.0 of socket 1)

The raw tables are in the first comment on this PR.

Token identity:

- Settings: greedy decoding (temperature 0, seed 1, `--pay-for-determinism`), one user with runtron's built-in prompt of the requested length (`--prompt-length`), 256 generated tokens.
- Binary: the production code of the first commit (`85084e937c`, now `b951ba9b4c`).
- Pass rule of the plan, one comparison each: branch equals `main` with AMX on; branch equals `main` with the kill switch; branch equals `main` with FPGA attention; the branch A/A repeat equals the branch. Token for token.
- Result: all 4 comparisons are identical at both prompt lengths (1024 and 8192 tokens). The branch with the kill switch also equals the branch with AMX on (AVX-512 path against AMX kernel).

Performance A/B:

- Settings: 8 users, prompt 1024 / 2048 / 8192 tokens, 256 generated tokens, 3 interleaved repetitions, 4 arms (`main` and branch, each with and without the kill switch) = 36 runs, 0 failures.
- Pass rule, fixed before the runs: every TPS and TTFT difference of the means lies inside the band.
- Band: the larger of two values. The first is 2 x the larger arm standard deviation over the 3 repetitions. The second is the reference spread measured for this shape on 2026-09-14 (0.4 TPS, 0.15 s TTFT).

| Comparison | Result |
|---|---|
| branch against `main`, AMX on: TPS and TTFT at 3 prompt lengths | 6 of 6 inside the band |
| branch against `main`, kill switch: TPS and TTFT at 3 prompt lengths | 6 of 6 inside the band |
| largest difference | +0.72 % TPS and -0.73 % TTFT, both with the branch faster |
| per-arm standard deviation | at most 0.35 TPS and 0.23 s TTFT (each under 0.5 % of its arm's mean: 71.6 TPS at prompt 1024 with the kill switch, 53.1 s TTFT at prompt 8192 with AMX on) |

Meaning: the refactor costs nothing measurable. That is the pass rule stated above.

Instruction comparison:

- Method: 19 `noinline` wrapper functions (the moved bodies and their callers) compiled against `main` and against the branch with `t_llama_unit`'s exact clang-19 command, disassembled with `objdump -d -r`, and compared after normalisation (in-function jump and call targets replaced by a placeholder, numbered string-literal labels unified, long template names shortened, so that only the instruction sequences are compared).
- Instruction-identical: the moved bodies, that is `set_v` even/odd for bf16, float and fp16, `get_v` even/odd for float and bf16, and the `scaled_v` weighted sum.
- Differ by addressing only: the `page::set_v` / `page::get_v` wrappers that take the token index at run time (one scalar `add` fewer), and the `book::append` copy closure (same vector instructions, different scalar address arithmetic).
- Allocation path: no store through the arena pointer, no `rep stos` (the x86 block-fill instruction), no `memset` and no loop.
- One difference found and removed: a bounds assert in `detail::v_vnni_access::pair_base`, which `append_v_row`, `load_row` and `copy_token` call, sat on a frequently executed path. The second commit removed it (`TRON_ASSERT` is active in release builds).
- Scope: the wrapper comparison is of the pre-rebase code. That code still had the placement-new pass. The next section checks the allocation path of the current code.


## Labels

`Skip benchmarks`, the repository's default for every PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


