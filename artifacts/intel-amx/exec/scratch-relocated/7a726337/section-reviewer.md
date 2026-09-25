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

