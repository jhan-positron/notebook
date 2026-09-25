## Short version

This PR (part of #4525) makes the KV cache and the AMX attention kernels exchange typed views instead of bare `bf16` pointers: a typed owner, view and row for the packed V plane, and a typed view alias for the native row-major K plane. Stored bytes, conversions, addition order and cache behavior stay unchanged. The pre-rebase tip `c3c368d298` passed the machine test on delphi-3bda (identical tokens in every arm, no measurable performance change), and the rebased tip `1c87d66926` passed its full build and its unit tests on delphi-3bda on 2026-09-23 (Verification).

## Words used here

| Term | Meaning |
|---|---|
| KV cache, book, page, `kv_block` | The stored key (K) and value (V) vectors of past tokens. A book is one sequence's cache. A page holds 64 tokens. A `kv_block` is one page's storage for one KV head: one K plane and one V plane. |
| packed V, VNNI layout | The V plane's storage order in the 16-lane build. VNNI (Vector Neural Network Instructions) is Intel's name for the pair-interleaved operand order this layout follows. Tokens 2i and 2i+1 are interleaved value by value. One 64-byte vector load therefore holds 16 dimensions of one token pair: the even token in the low half and the odd token in the high half of each 32-bit lane. It is the B-operand layout (the right-hand matrix) of the AMX tile multiply. Address formula: `plane[(token/2)*(2*D) + 2*dim + token%2]` for D dimensions per row. |
| native K | The K plane's storage order on `main`: one row of head_size `bf16` values per token (row-major). |
| bf16, fp32, fp16 | bf16 is the 16-bit brain floating point format the cache stores. fp32 is the 32-bit float, fp16 the 16-bit IEEE half-precision float. |
| AMX, AVX-512, AVX2 | Intel instruction sets. AMX is the tile matrix unit the attention kernels use for dense (fully filled) 64-token pages. AVX-512 is the 512-bit vector unit of the software path. AVX2 is the older 256-bit vector instruction set. |
| software path | The CPU attention code that uses neither the AMX tiles nor an accelerator card. |
| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (16 fp32 values per vector register: AVX-512, the production build) or 8 (AVX2). Packed V exists only in the 16-lane build. The 8-lane build keeps row-major V. |
| AMX-on build, AMX-off build | Configured with `TRON_AMX_DISPATCH=ON` (the AMX kernels are compiled in) or `OFF` (they are not; the configuration the required CI builds). The kill switch below is a run-time setting inside an AMX-on build. |
| kill switch | `TRON_AMX_DISABLE=1`: the binary skips the AMX kernels and runs the AVX-512 software path. |
| owner, view, row | `v_vnni_tensor` owns one aligned V plane. `v_vnni_view` is a non-owning matrix view (rows are tokens, columns are dimensions) that holds the address formula. `v_vnni_row` is one token's row as an expression, readable through the existing `expr` interface. |
| retained slot, sliding-window slot | A KV slot is one layer's K and V storage. A retained slot keeps every token of the sequence. A sliding-window slot keeps only a recent window of tokens. |
| arena, chunk | The raw byte buffers a book allocates for its KV blocks. The accelerator cards read them directly (DMA, direct memory access). One whole-book arena holds the retained slots. Since PR #4455 on `main`, page-aligned chunks hold the sliding-window slots (PR #4456 adds the reclamation of expired chunks in the scheduler). |
| even/odd partner rule | Appending an even token also writes zeros into its odd partner's half of the pair. Appending an odd token merges into the pair and leaves the even half alone. |
| Note [Name] | tron's convention for a named comment block in the source; other comments refer to it by that name. |
| FPGA, FPGA attention | The accelerator card (field-programmable gate array). FPGA attention computes attention on the card instead of the CPU (`USE_HW_ATTN=1`). |
| QK, PV | The two attention steps: QK forms the query-times-key scores, PV multiplies the softmax weights with V. |
| arm | One binary-plus-configuration combination under test, for example `main` with the kill switch. |
| A/B, A/A repeat | A/B: the branch binary against the `main` binary in the same configuration. A/A: the same binary and configuration run twice, as a control for run-to-run noise. |
| band | The run-to-run spread inside which a performance difference counts as no change. It is defined under Performance A/B below. |
| shape | One users-and-prompt-length setting of a performance run. |
| TPS, TTFT | Decode tokens per second per user, and time to first token. |
| rc | Return code of a command; 0 means success. |
| delphi-3bda | The Intel Xeon 6962P (Granite Rapids) host with AMX where every build, test and measurement below ran. |

## What changes

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
  - `page::set_v` and `page::get_v` take a typed, aligned, unit-stride row (`const_view<Source, true, Dma, seq<head_size>, sseq<1>>` and `view<Destination, ...>`) instead of a pointer.
  - `page::v_packed()` returns the const packed view of one page and KV head for the kernel.
  - `book::append` copies V through `copy_token`.
  - `scaled_v_expr` (the software path's weighted sum) takes the packed view.
  - `page::v_data` and `kv_block::v_base` are removed.
  - Note [KV block lifetime]: the arenas are still allocated as raw bytes. Each allocation path (`allocate_retained_storage`, `allocate_reclaimable_chunk`) constructs an array of `kv_block` over the bytes with placement new and no initializer. Every block type is trivially default-constructible. So this compiles to no instruction and clears nothing.
  - Note [Zero-Initialized V Slots] now names the typed operations.
- **`h/tron/models/model.hpp`**. `save_v_impl` passes the V source row as a typed view whose element type and DMA flag come from the V buffer's type.
- **`h/tron/models/self_attention.hpp`, `h/tron/kernels/amx_attn_iface.hpp`, `src/tron/kernels/amx_attn.cpp`**. `qk_rowmajor_128x4` takes `const_native_k_view<64, 128>`. `weights_times_v_128x4` takes `v_vnni_view<const bf16, 64, 128>`. The kernel bodies read the plane pointers through the typed views. The tile loads are unchanged.
- **`h/tron/scheduler/full.hpp`**. The FPGA staging callback `v_head_fn` unpacks a token's V row through `get_v` into a typed destination row.
- **Tests.**
  - `t_llama_unit`: `STATIC_REQUIRE` checks that each kernel accepts only its typed view and rejects raw pointers and the other plane's view, the const rules of view and row, and the trivial traits and `sizeof`/`alignof` of the owner. A new case "packed V rows keep their bits through set_v, get_v and expression reads" covers bf16, float and fp16 sources, special values, a zero partner after even appends, and exact bits after token copies at both parities. The existing poison case now runs both destination parities. That case writes NaN into the padding slot. It then checks that the zero-initialized odd partner keeps the NaN out of the weighted sum. Every `set_v`/`get_v` caller uses the typed rows, including `main`'s new sliding-chunk case.
  - `t_amx_numerics`: the PV fixture is built through `append_v_row` into a `v_vnni_tensor` and byte-compared with the independent layout formula before the kernel runs.
  - `t_amx_dispatch_dtype`: typed fakes. Its `apply_page_range` call also gains the query-mask argument it was missing. So this test compiles with `TRON_AMX_DISPATCH=ON` again. It did not at `main` `0a51385e95`, nor at the current base `996f58ec82` (`apply_page_range` takes `batch_queries` with no default, and the call omitted it).
  - `heterogeneous_scheduler_compile.cpp`: its one `set_v` caller passes an aligned typed row.
- **Code style (fifth commit).** The fixed values of the new code are named constants with their value in the name (`V_PLANE_ALIGNMENT_64`, `PV_TILES_PER_HALF_4`, the test constants such as `SPECIALS_EVEN_TOKEN_2`), and every new loop body has braces. No change in generated code is intended.

Not in this PR: PR #4424 (the packed-K child) is unchanged. Its rebase onto this parent is PR order item 2 of #4525. This is an internal KV-cache API change whose scope is recorded in #4525 (filed by the PR author). The public API (`h/libtron.hpp` and the four headers it exports through IWYU pragmas; IWYU is include-what-you-use, the header-dependency checker) is untouched.

## Decisions record

The design's questions to the reviewing maintainer, with the choice this PR implements. Rows Q1-Q4 are **Proposed**: no reviewer answer is recorded yet. Row D5 is scope the issue author requested. It is not a question to the reviewer and not reviewer approval. Sources: the maintainer's [tensor-interface review](https://github.com/positron-ai/tron/pull/4424#pullrequestreview-5270587330) and [API sketch](https://github.com/positron-ai/tron/pull/4424#issuecomment-5765866077) on #4424.

| Id | Question | Choice implemented | Status |
|---|---|---|---|
| Q1 | May each concrete view contain its address formula? | Yes. `v_vnni_view` holds the packed formula, and the owner is a separate type. Native K reuses the existing `view` types. | Proposed |
| Q2 | Should const matrix and row objects prevent element mutation? | Yes, at both ranks: `v_vnni_view<const bf16, ...>` and `v_vnni_row<const bf16, ...>` have no writable access, and a const view does not convert to a writable one. | Proposed |
| Q3 | May packed views expose logical rows through `operator[]`? | Yes. `operator[]` returns a `v_vnni_row` with no public pointer. `at()` is bounds-checked. | Proposed |
| Q4 | Is the smaller parent scope sufficient? | Yes. Expression reads plus the existing typed bulk operations. Slices, iterators and generic writes are deferred to PR order item 2 (#4424) or a follow-up PR. | Proposed |
| D5 | Who owns native-K typing? | Requested by the issue author: the `const_native_k_view` alias and the typed QK kernel parameter. | Requested scope, not reviewer approval |

If the reviewer answers a question differently, the code changes before merge.

## Response to the reviewer's comments on #4424

This PR answers two comments the reviewing maintainer left on PR #4424: the [tensor-interface review](https://github.com/positron-ai/tron/pull/4424#pullrequestreview-5270587330) and the [API sketch](https://github.com/positron-ai/tron/pull/4424#issuecomment-5765866077) (API: application programming interface). The tables below list every technical point of the two comments. Two pairs of adjacent sketch statements share one row. The "In PR #4557" column says what this PR does. The "Same as suggested?" column has these values:

- Same: the mechanism follows the sketch.
- Same rule, other shape: the rule is kept. Only a name or a type shape differs.
- Different by decision: this PR chose another way on purpose. The decision id refers to the Decisions record above.
- Different (no id): this PR chose another way. The reason, or its absence, is stated in the cell.
- Deferred to #4424: the point concerns the packed-K layout. PR #4424 adds that layout, and this PR does not touch it.
- Partly (review table only): the point is met for the planes this PR covers and open for the rest, as the cell says.

Words used here:

- layout type: a struct whose only job is the address formula from (token, dimension) to a memory position.
- `std::span`: the standard C++ array view. The sketch uses it with a fixed size.
- mutable view, const view: a mutable view can write elements. A const view cannot.
- `expr`: tron's shared base type for tensor-like objects (`h/tron/kernels/expr.hpp`). A type that inherits it gets row indexing and vector-chunk reads through one interface.
- `tensor`, `dtensor`, host tensor: `tensor` is tron's owning tensor type in CPU memory, built on `expr`. `dtensor` is the hardware-side tensor type. A host tensor is a `tensor` in CPU memory.
- rank-2: two-dimensional, here token by dimension.
- logical row, contiguous row: a logical row is one token's values addressed by coordinates. In the packed layout they are interleaved with the partner token, so they are not one contiguous run of bytes.
- the matrix rule: the repository has two const rules. A const matrix returns a read-only row. A const rank-1 view can still return a writable element. The matrix rule is the first one.
- SIMD: single instruction, multiple data, that is the vector registers and instructions.
- intrinsics: the compiler's built-in functions for vector instructions.
- `STATIC_REQUIRE`: the compile-time check of the Catch2 test framework.
- lvalue, rvalue: a named object, and a temporary.
- placement new: C++ construction of an object at a given address, here over the arena bytes.
- trivially copyable: the type can be copied as plain bytes.
- concept: a named C++20 compile-time constraint on a template parameter.
- friend: a C++ declaration that lets a named type call a private constructor or read a private member.
- hot path: code that runs for every token or every page during inference.

### The review (5 points)

| Point | In PR #4557 | Same as suggested? |
|---|---|---|
| Encapsulate the VNNI representation. Too many pointers say nothing about the layout they point to. | The packed V plane is reached only through an owner, a view and a row type with no public pointer. The native K plane reaches the QK kernel as a typed view. `page::v_data` and `kv_block::v_base` are removed. | Partly. The packed-K representation, the case the review was written about, is deferred to #4424. One packed operand is still passed as a bare pointer: `q_packed`, the output of `pack_q_group_128x4`, consumed by `qk_rowmajor_128x4`. It is not cache storage, and it stays as on `main`. The one raw write into packed V storage is the documented test fill `book::fill_random` (Note [Packed V layout]). |
| Follow the `tensor` / `dtensor` precedent: one interface built on `expr`, so code can convert, slice and compute on any tensor type. | `v_vnni_view` and `v_vnni_row` inherit `expr`. `operator[]` returns a logical row, and `chunk()` reads a row through the packed formula. A host tensor can be built from a packed view (tested). | Partly, by decision Q4. Expression reads and single-element writes (`at()`, `row[dim]`) are provided. Slices, iterators, generic writes and expression assignment are deferred until a caller needs them. |
| Introduce a `vnni_tensor` type for a VNNI-packed rank-2 tensor. | `v_vnni_tensor<Rows, Cols>` for the packed V plane. | Same rule, other shape. Q1 gives one concrete type family per layout and no shared layout-policy template. The packed-K owner is deferred to #4424. |
| Give it the usual tensor operations, in particular row-wise load and store. | `append_v_row` (row in), `load_row` (row out) and `copy_token` (token to token) keep the existing vector bodies. Element reads go through `expr`. | Partly, by decision Q4. The row operations, element reads and single-element writes exist. The wider set of tensor operations is deferred. |
| No bare `bf16_t*` (tron's `bf16`) values without an indication of the layout. | The packed V plane (16-lane build) and the native K plane cross the cache and kernel boundaries as typed views. A bare pointer or the other plane's view is a compile error (tested with `STATIC_REQUIRE`). The 8-lane build keeps its row-major V path unchanged. | Partly, as in the first row: packed K deferred, `q_packed` unchanged. |

### The API sketch (sections 1 to 5, 35 rows)

| Section, point | In PR #4557 | Same as suggested? |
|---|---|---|
| Intro: the reviewer doubts that a separate `k_vnni_layout` type is needed. | There is no layout type. The address formula is part of the view type (`pair_base`, `at`) and is written out in Note [Packed V layout]. | Different by decision Q1. This matches the doubt the reviewer stated. |
| Intro: separate layout, storage and views. | Storage (`v_vnni_tensor`) and views (`v_vnni_view`, `v_vnni_row`) are separate types. The address formula is part of the view type. | Different by decision Q1. |
| 1: layouts describe the two existing representations with logical (token, dimension) coordinates. | The packed V formula is unchanged: `plane[(token/2)*(2*D) + 2*dim + token%2]`. Native K keeps its row-major `view`. | Same rule, other shape. The formula is inside the view, not in a layout struct. |
| 1: one header `h/tron/tensor/vnni.hpp` for both layouts. | Two headers. `h/tron/tensor/v_vnni.hpp` holds the V family. `h/tron/tensor/kv_cache_fwd.hpp` holds declarations free of intrinsics and the native-K aliases. The K family goes to `h/tron/tensor/k_vnni.hpp` in #4424. | Different. The design record lists the per-plane file split as the design's own choice. No reviewer answer is recorded. |
| 1: `k_vnni_layout` with `offset()` and the shape asserts. | Not in this PR. | Deferred to #4424. The plan there also puts the formula inside the view type (Q1). |
| 1: `v_vnni_layout` with `offset()`, `Tokens % 2 == 0`, `Dims > 0`. | The same formula. The even-rows rule is a `static_assert` in the owner and the view. The column rule `Cols % chunk_size == 0` (one vector chunk: 16 columns in the 16-lane build, 8 in the 8-lane build) is in the owner, the view and the row. It is stricter than `Dims > 0`. | Same rule, other shape (Q1), with one stricter storage check. |
| 1: storage checks are loose, and kernels may be stricter. | Storage checks as above. The kernels are fixed at 64 tokens x 128 dimensions by their signatures. `set_v` and `get_v` keep `head_size % 32 == 0`. | Same. |
| 2: `vnni_view<T, Layout>` with `T` limited to `bf16` or `const bf16`. | `v_vnni_view<T, Rows, Cols>`. `T` is limited the same way by the concept `v_vnni_element`. | Same rule, other shape (Q1). |
| 2: the only converting constructor is mutable to const. | One constrained constructor, writable to const only. | Same. |
| 2: `at(token, dim)` with `TRON_ASSERT_LT` bounds checks. | The same asserts. There are two overloads, and the const overload returns a read-only element. | Same, plus the const rule of Q2. |
| 2: private pointer constructor, and views come from typed storage. | The pointer constructor is private. The friends are the owner, the internal helper `detail::v_vnni_access` and the other instantiations of the view. | Same. |
| 2: no `data()`, no pointer conversion, no `operator[]`. | No `data()` and no pointer conversion. `operator[]` exists and returns a logical row with no public pointer. | Different by decision Q3. The `expr` interface needs row indexing. The returned row type has no public pointer. It cannot be mistaken for a contiguous row. |
| 2: `at()` is for inspection only, and hot paths use the bulk operations. | No production path calls `at()`. The page methods use the bulk operations. The PV kernel and `scaled_v_expr` take the plane address through `detail::v_vnni_access`. | Same. |
| 2: const follows `std::span`, so a const view object does not make elements const. | A const view (the matrix, rank 2) and a const row (rank 1) are both read-only. | Different by decision Q2. This PR applies the matrix rule at both ranks. |
| 3: storage is a 64-byte-aligned class holding a `std::array<bf16, elements>` inline. | `v_vnni_tensor` holds one `bf16` array aligned to `V_PLANE_ALIGNMENT_64` (64 bytes) inline. It is trivially copyable. | Same rule, other shape (a plain array, and `Rows` / `Cols` parameters). |
| 3: `as_view()` on lvalues only, and both rvalue forms deleted. | The same four overloads. | Same. |
| 3: keep V's zero-initialization invariant, and add no clearing to hot allocation paths. | The even/odd partner rule is moved code. The arenas are constructed with placement new and no initializer (Note [KV block lifetime]). The instruction comparison and the `objdump` disassembly check (both under Verification, Instruction comparison) show no clearing. | Same. |
| 3: the arena constructs the storage type, with no casting of a SIMD array. | `kv_block::v` is the owner type. Each arena and chunk is constructed with placement new. | Same. |
| 4: bulk operations as overloads per layout, and no generic scalar loop. | The three V operations keep their 16-lane vector bodies. The `set_v` and `get_v` bodies are instruction-identical to `main`. The copy closure has the same vector instructions with different scalar address arithmetic (pre-rebase comparison, Verification). | Same for V. The K operations are deferred to #4424. |
| 4: `store_row` / `load_row` with `std::span` arguments. | `append_v_row`, `load_row` and `copy_token` with tron `const_view` / `view` row arguments. | Different, for two recorded reasons. The name `append_v_row` records the partner zeroing that the K store will not have. The tron row views carry the caller's alignment flag and DMA flag, which `std::span` cannot. The element type (bf16, fp16 or float) is a template parameter in either form. |
| 4: for K, `store_row` / `load_row` wrap the scatter and gather, and a typed `store_block` keeps the transpose path. | Not in this PR. | Deferred to #4424. |
| 4: for V, the overloads wrap the interleave and de-interleave code with the bf16, fp16 and float conversions. | The same code, moved unchanged. | Same. |
| 4: the layout header does not include the attention kernels. | `v_vnni.hpp` includes no attention-kernel header. Its one include from the kernels directory is `tron/kernels/expr.hpp`, the expression base that `tensor.hpp` also includes. The kernel interface header names the views through `kv_cache_fwd.hpp` and includes no SIMD or tensor definition header. | Same. |
| 4: raw-address access only through `detail::vnni_access::packed_data`. | `detail::v_vnni_access` with `plane()` and `pair_base()`. Its users are the three V operations, the PV kernel and `scaled_v_expr`. | Same rule, other shape (a V-only helper, and #4424 adds a K helper). |
| 4: that helper is an internal helper, not an access-control boundary, and ordinary cache and attention code must not use it. | The same rule, stated in the header comment. | Same. |
| 5: `kv_block` selects K storage at compile time with `std::conditional_t`. | `kv_block::k` is unchanged. | Deferred to #4424. |
| 5: V storage follows the `TRON_CHUNK_SIZE` condition. | The 16-lane build selects `v_vnni_tensor`, and the 8-lane build keeps the row-major array. | Same. |
| 5: both configurations keep their bytes and alignment. | Checked by `static_assert` on `sizeof` and `alignof` and by tests. | Same. |
| 5: page accessors return typed views (`k_packed`). | `page::v_packed` returns the const packed V view. The native K view comes from the existing `page::k`. | Same for V. `k_packed` is deferred to #4424. |
| 5: aliases `packed_k_page` and `packed_v_page` name what the kernels accept. | No fixed-size aliases. The kernel signatures spell the full types: `const_native_k_view<64, 128>` and `v_vnni_view<const bf16, 64, 128>`. The only aliases added are the generic `native_k_view` / `const_native_k_view<Rows, Cols>`. | Different. No reason is recorded. It is a naming choice. |
| 5: `qk_vnni_128x4` takes `packed_k_page`. | Not in this PR. Instead the native kernel `qk_rowmajor_128x4` takes `const_native_k_view<64, 128>`. | Deferred to #4424 for packed K. The native-K typing is the issue author's request (D5), beyond the sketch. |
| 5: `weights_times_v_128x4` takes `packed_v_page`. | Takes `v_vnni_view<const bf16, 64, 128>`. | Same rule, other shape. |
| 5: the AVX-512 fallback also takes `packed_k_page`. | Not in this PR. | Deferred to #4424. |
| 5: kernels extract the pointer once and keep the instruction sequence. | Both typed kernels read the pointer once into a const local. Their tile-load sequences are unchanged apart from the pointer source and two named constants with the same values (`V_PAIR_TOKENS_2`, `PV_TILES_PER_HALF_4`). The instruction comparison covered the moved cache bodies (`set_v`, `get_v`, `scaled_v`), not these two kernels. | Same. |
| 5: the compile-error examples (right plane accepted, other plane and bare pointer rejected). | Implemented for both kernels this PR ships and pinned by `STATIC_REQUIRE` in `t_llama_unit`. | Same, for the two kernels on `main`. The packed-K kernel is deferred to #4424. |

Summary. The review's five points are addressed for the planes this PR covers. The packed-K half of each point waits for #4424. The sketch table has 35 rows:

- 17 are followed as written ("Same").
- 6 keep the rule with another name or type shape.
- 6 are done differently for a recorded reason: Q1 (twice), Q2, Q3, the header split, and the row-operation names and argument types.
- 1 differs without a recorded reason: no `packed_*_page` aliases.
- 5 are deferred to #4424.

Not addressed anywhere yet: the bare `q_packed` pointer between `pack_q_group_128x4` and `qk_rowmajor_128x4`.

## Status

Ready for review since 2026-09-23, about 13:45 UTC. The full 16-lane AMX-on build, the AMX-off build and the four unit tests of `1c87d66926` passed on delphi-3bda (Verification). The GCP Nix CI run (GCP is Google Cloud Platform; `gcp-nix.yml` is the default CI workflow: lint, Nix builds, tests) started when the PR left draft. Its jobs all passed (CI). The rebase changed only `construct_kv_blocks`, its two call sites and two test calls (see Rebase resolution), and the fifth commit changes names and braces only.

## Verification

### Commits and what ran on each

| This PR | Before the rebase | Content |
|---|---|---|
| `b951ba9b4c` | `85084e937c` | the typed tensors and every caller. The rebase resolution is in this commit. |
| `daf227de13` | `682064f8fb` | removes a bounds assert from the bulk route (see Instruction comparison) |
| `959d1ae229` | `c2efd73ff6` | review fixes: two test checks, comments |
| `707159b9ef` | `c3c368d298` | test extensions in `t_llama_unit` |
| `1c87d66926` | (none) | code style: named constants for the fixed values of the new code, braces on the new loop bodies |

The pre-rebase branch is pushed as `jhan-kv-typed-tensors-pre-rebase-20260923` (tip `c3c368d298` on `main` `0a51385e95`). This lets a reviewer open the tested commits. `git range-diff 0a51385e95..c3c368d298 996f58ec82..707159b9ef` shows commits 2-4 unchanged and commit 1 changed only in the rebase resolution. At 16 lanes, the production code of commits 2, 3 and 4 is the same. Commits 3 and 4 change tests and comments only.

| Tip | Base | What ran |
|---|---|---|
| `c3c368d298` (before the rebase) | `main` `0a51385e95` | the unit-test and machine-test sections below. Each row names the commit its run used. |
| `1c87d66926` (this PR; rebased on 2026-09-23 at 05:03 UTC, commits re-created at 05:26 UTC after commit 1's Note comment and message were amended, fifth commit added at 06:22 UTC) | `main` `996f58ec82` | A syntax check (`-fsyntax-only`, 16-lane AMX-on compile commands) of the five translation units that include the changed headers: all rc 0. `clang-format-19 --dry-run -Werror` on the 12 changed files: rc 0. `make lint-notes` (the checker of the Note [Name] comment blocks): rc 0. Full build on 2026-09-23 13:19-13:30 UTC (`cmake --build gen -- -k 0`, 16-lane AMX on, 308 s with a warm cache): every target builds except `t_rinzler` (the pre-existing failure below). AMX-off tree: the four tests build. Tests: the two `1c87d66926` rows of the Unit tests table. |

Rebase resolution:

- `main` replaced the single reclaimable arena with page-aligned chunks (PR #4455).
- `construct_kv_blocks` therefore takes the bytes, the page count and the retention group (retained or sliding-window) of the arena or chunk being installed.
- It is called from `allocate_retained_storage` and from `allocate_reclaimable_chunk`.
- The slot offsets it uses (`pages * byte_offset`) are the ones `slot_page` computes.
- `main`'s new test "Sliding KV chunks reserve and restore transactionally" now calls `set_v`/`get_v` with typed rows.
- Commit 1's message names the two new allocation functions. The other three messages are unchanged.

Checks not run: `make lint`, the full `make build-test` (`make build-test-host` ran), `nix build .#checks.x86_64-linux.lint-toolchain`, and `make iwyu-check` (optional: no public API header changed).

### Unit tests (delphi-3bda, clang 19 from the Nix shell, RelWithDebInfo)

The first two rows are the rebased tip `1c87d66926` (2026-09-23, 13:19-13:35 UTC). The later rows are the pre-rebase commits. The rebased tip carries one more `t_llama_unit` case from `main` ("Sliding KV chunks reserve and restore transactionally"), so its counts differ.

| Tree | Configuration | Commit | Result |
|---|---|---|---|
| 16-lane, AMX on | `cmake --preset native -DAVX512=ON -DTRON_AMX_DISPATCH=ON`, RelWithDebInfo | `1c87d66926` | `t_llama_unit` 44 cases / 252718 assertions pass (the sliding-chunk case alone: 53593 assertions; the packed-V bit case alone: 28947). `t_amx_numerics` 4 cases / 12301 assertions pass on real AMX. The kill-switch control: 4 cases / 2060 assertions, "AMX unavailable" printed for the QK and the PV case. `t_amx_dispatch_dtype` 1 case / 1559 assertions pass. `t_heterogeneous_scheduler` 2 cases / 1900 assertions pass. |
| 16-lane, AMX off (the CI feature set) | `-DTRON_AMX_DISPATCH=OFF`, RelWithDebInfo | `1c87d66926` | `t_llama_unit` 44 cases / 252718 assertions pass. `t_heterogeneous_scheduler` 2 cases / 1900 assertions pass. `t_amx_numerics` and `t_amx_dispatch_dtype` run their "not compiled" placeholder (1 assertion each). |
| 16-lane, AMX on | `cmake --preset native -DAVX512=ON -DTRON_AMX_DISPATCH=ON` | `c3c368d298` | `t_llama_unit` 43 cases / 199125 assertions pass. |
| 16-lane, AMX on | same | working tree of the first commit (production code of `85084e937c`) | `t_amx_numerics` 4 cases / 12301 assertions pass on real AMX. The kill-switch control (4 cases / 2060 assertions) prints "AMX unavailable" for the QK and the PV case. `t_amx_dispatch_dtype` passes. `t_heterogeneous_scheduler` passes. The build of runtron (tron's command-line inference tool) and these four tests gave 0 compiler warnings. Not rerun on the later commits. The only later production-code change is the assert removal of `daf227de13`. |
| 16-lane, AMX off (the CI feature set) | `-DTRON_AMX_DISPATCH=OFF` | `85084e937c` | `t_llama_unit` 43 cases / 176462 assertions, `t_heterogeneous_scheduler` 1852 assertions pass. `t_amx_numerics` and `t_amx_dispatch_dtype` run their "not compiled" placeholder (1 assertion each). |
| 16-lane, Debug, AMX off | `CMAKE_BUILD_TYPE=Debug`, without `TRON_IGNORE_NAN` (the option, set in every non-Debug build, that drops the NaN correction from the fp32-to-bf16 conversion) | `85084e937c` | `t_llama_unit`, cases tagged `[kv_data]` (the KV-cache cases): 29 of 29 pass, 48958 assertions. |
| 8-lane (AVX2) | `-DAVX512=OFF` | `main` `0a51385e95` | Not testable. The `tron` library (the inference engine this repository builds) fails to compile at 8 lanes on `main` itself. First errors: `h/tron/simd/fp32.hpp:807: unknown type name 'fp32x16'` and `'mask1x16'`, `h/tron/simd/fp32.hpp:749: no matching function for call to 'cast_fp32'`. Not attempted on the rebased base. The 8-lane parts of this PR (row-major V kept, `v_vnni_row::chunk` deleted) are checked by reading only. |
| Host suite (the tests labelled `host`: they need no accelerator card), 16-lane AMX off | `make build-test-host`, then `make test-host` (= `bin/slice run --filter=host --exclude-tag=slow`) | snapshot of `85084e937c` | 669 host targets build. 88 passed / 0 failed / 1 skipped (`t_proxy_lib`, whose Python venv is absent on the machine). `main` `0a51385e95` in the same configuration gives the identical status set. |

Every target of the 16-lane AMX-on tree builds except `t_rinzler` (the test of rinzler, the production inference server), on the pre-rebase tip and on `1c87d66926` alike. It fails identically on unmodified `main` in this configuration, and this PR does not touch the file. At `main` `0a51385e95`, `t/t_rinzler.cpp:5316` calls `read_stats_counter`, and that function is defined (line 4628) only inside both `TRON_GPT_OSS_20B_INGEST_MODEL_ENABLED` and `TRON_FUSE_STATS_ENABLED`. The tree was configured with `BUILD_INGEST_MODELS=OFF`. `t_rinzler` is FPGA-labelled and not part of the host suite.

### Machine test (delphi-3bda, qwen3-4b `ingested-qwen-3-4b-instruct-2507-tp2`, `runtron --instance 2,4` on cards 90:00.0 and 93:00.0 of socket 1)

The raw tables are in the first comment on this PR.

Token identity:

- Settings: greedy decoding (temperature 0, seed 1, `--pay-for-determinism`), one user with runtron's built-in prompt of the requested length (`--prompt-length`), 256 generated tokens.
- Binary: the production code of the first commit (`85084e937c`, now `b951ba9b4c`).
- Pass rule of the plan, one comparison each: branch equals `main` with AMX on; branch equals `main` with the kill switch; branch equals `main` with FPGA attention; the branch A/A repeat equals the branch. Token for token.
- Result: all 4 comparisons are identical at both prompt lengths (1024 and 8192 tokens). The branch with the kill switch also equals the branch with AMX on (AVX-512 path against AMX kernel).

Performance A/B:

- Binary: the production code of the second commit (`682064f8fb`, now `daf227de13`) against `main`. At 16 lanes that code equals this PR's production code before the rebase.
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
- Scope: the wrapper comparison is of the pre-rebase code. On `1c87d66926`, `objdump -d` of the AMX-on `t_llama_unit` binary shows every `allocate_retained_storage` and `allocate_reclaimable_chunk` instantiation (uniform and heterogeneous books) at 68 to 92 instructions, with no backward jump, no `rep stos`, no `memset`, and no call other than the DMA allocator, its deallocator, the allocation-limit query and the assert's abort. The placement-new therefore compiles to nothing on the rebased path too. The language guarantee holds on every tip: `::new (p) kv_block_t[n]` with no initializer default-initializes a trivially default-constructible type and emits no code.

### CI

- Policy: under the repository's PR CI policy (AGENTS.md), only the PR based on `main` may be ready for review, and this is that PR.
- Draft exit: 2026-09-23, after the rebased tip's full build and unit tests passed on delphi-3bda (Status).
- Workflow: the GCP Nix workflow (`gcp-nix.yml`) then runs, and its links are added here.
- CI run: [GCP Nix run 35868511322](https://github.com/positron-ai/tron/actions/runs/35868511322) on `1c87d66926`, started when the PR left draft on 2026-09-23: completed with success. Every job passed (Lint, Nix Toolchain Contracts, CI machinery contracts and tests, Fresh Cabal plan, Build ingest, Build model traces, Test ingest, Generate model plugins, Prepare Tron build inputs, Wait for lab cache, Build Tron, [Test host](https://github.com/positron-ai/tron/actions/runs/35868511322/job/107216531906), [Test FPGA](https://github.com/positron-ai/tron/actions/runs/35868511322/job/107216531039), Test); the two Benchmark jobs were skipped by the Skip benchmarks label. [Debian smoke run 35868511345](https://github.com/positron-ai/tron/actions/runs/35868511345) passed. The earlier draft-time run 35826452601 ran only the lint and CI-machinery jobs and skipped Build Tron and the test jobs, as expected for a draft.
- Coverage: the required `test-host` job builds the 16-lane AMX-off configuration. No required job runs on an AMX machine (the AMX CI gap). The AMX-on evidence is therefore the delphi-3bda record above.
- After merge: the nightly systems test (the CI job that installs the nightly package on delphi-3bda) compiles the AMX kernels (PR #4505) and runs the typed kernel path.

### Not covered

- The `t_llama_unit` row of `config/test-benchmarks.json` was not refreshed for the new test case (the rule in `t/AGENTS.md`: refresh after adding or materially changing a test). `bin/slice bench --update t_llama_unit` needs the whole delphi-3bda host. The refresh is therefore deferred. The decision to run it is the author's. No platform block was remeasured: `granite_rapids_6962p` (delphi-3bda), `genoa96`, `genoa32` and `granite_rapids_6960p` (the file's other three platform blocks) are all unrefreshed. The weekly Slice Cost Data Refresh workflow (`bench-refresh.yml`) maintains that file.
- PR #4424 and the packed-K types (PR order item 2 of #4525).

## Labels

`Skip benchmarks`, the repository's default for every PR.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

