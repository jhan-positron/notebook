## Short version

At the head of draft PR #4587 (commit c73e7fb2f9), a code comment in `h/tron/models/kv_cache.hpp` names three reads of the KV cache that fall outside the rules of ISO C++. They give correct values today only through a clang 19 compilation choice, not through any language guarantee. This issue records each read's location, the rule it breaks, why it works today, what would detect a break and the fix options for the code owner, and no test or bug report examined here shows a wrong result from any of the three.

## Words used here

| Term | Meaning |
|---|---|
| clang, clang 19 | The C++ compiler that builds the product, version 19.1.7, built on LLVM. |
| LLVM, IR | LLVM is the compiler framework under clang. clang turns C++ into LLVM IR (intermediate representation, the compiler's internal form of the program), and LLVM turns the IR into machine code. |
| nix | The package manager that supplies the compiler and the libraries on delphi-3bda. |
| delphi-3bda | The Intel test host that builds and runs the product with the nix clang toolchain. |
| CI, runner | CI: continuous integration, the automated GitHub build-and-test jobs of the repository. A runner is the machine that executes one CI job. |
| CMake, preset | CMake is the build configuration tool. A preset is a named set of CMake options in CMakePresets.json, such as `native`, `darwin` and `deb` (the Debian package build). |
| tree | One configured build directory. |
| GCC, libstdc++ | GCC is the GNU C++ compiler. It is not the product compiler. libstdc++ is GCC's C++ standard library, which the product links. |
| ISA flags | ISA: instruction set architecture. The ISA flags are compiler options such as `-mavx512f` that select the CPU instructions the compiler may emit. |
| KV cache, book | The store of attention keys (K) and values (V) for past tokens. `book` is the class that owns the storage (`h/tron/models/kv_cache.hpp`). |
| page | One 64-token block of the KV cache (`page_size` tokens). `page` is the class with the per-page accessors. |
| slot, storage slot | One persistent K/V storage region of the book. `kv_slot_id` selects it, and a `kv_slot_spec` (geometry plus retention) describes it (kv_cache.hpp:154-161, h/tron/attention_ids.hpp:18-22). A storage slot is that region at one `kv_storage_offset`. EAGLE selects a second offset. |
| geometry, page_size, head_size, chunk_size, kv_head | `kv_geometry` is the pair (n_kv_heads, head_size) that describes one slot's layout (kv_cache.hpp:103-110). The templates take it as a compile-time value. page_size is the number of tokens per page (64). head_size is the number of bf16 values per token in one attention head. chunk_size is `TRON_CHUNK_SIZE`. kv_head is the index of one KV head (one key/value head of grouped-query attention, shared by several query heads). |
| kv_block, kv_block_t | One struct holding K and V for one KV head in one page: member `k`, then member `v` (kv_cache.hpp:2445-2466). `kv_block_t` is `detail::kv_block<page_size, head_size>` for one geometry (kv_cache.hpp:1553, 1592). |
| kv_block_alignment | 64 bytes, the alignment of every kv_block and of both planes (`std::max<size_t>(64, chunk_alignment)`, kv_cache.hpp:2440). |
| kv_block_at_storage | The book accessor that returns the kv_block of one (storage offset, kv_head, page index) (kv_cache.hpp:1586-1600). |
| K plane, V plane | The K half or the V half of one kv_block. |
| packed V, native K | Packed V is the 16-lane V layout: two tokens interleaved per 32-bit column, owned by `v_vnni_tensor`. Native K is the K plane stored as plain bf16 values in their original order, with no vector packing. |
| k_view | The kv_block member function that returns a typed view of the K plane (kv_cache.hpp:2468-2481). `page::k` calls it (1843-1863). |
| v_storage | The 16-lane alias inside kv_block: `using v_storage = v_vnni_tensor<page_size, head_size>` (kv_cache.hpp:2454). |
| v_vnni_tensor | The typed owner of one packed V plane in the 16-lane build. Its only data member is `alignas(V_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols]`, and `V_PLANE_ALIGNMENT_64` is 64 (h/tron/tensor/v_vnni.hpp:246-269, constant at 79). |
| v_vnni_access::plane | The friend accessor that returns the raw `bf16*` of a packed V view (v_vnni.hpp:272-276). It is the one permitted way for a kernel to get the plane pointer. `v_page` is the `v_vnni_view` passed into scaled_v_expr. |
| as_view, kv_page_view, v_view | `as_view` is the `v_vnni_tensor` method that returns a typed view of the plane. `kv_page_view` and its `v_view()` are the page view class of the closed PR #4584 (9380012de5 kv_cache.hpp:2431-2471). |
| bf16, __bf16 | `tron::bf16`, a struct with one `__bf16` member, 2 bytes (h/common/numerics/bf16.hpp:12-13). `__bf16` is clang's built-in 16-bit brain-float scalar type. |
| bf16s | The SIMD vector alias for one chunk of bf16 values: `__m256i` (32 bytes) in the 16-lane build, `__m128i` (16 bytes) in the 8-lane build (h/tron/simd/auto.hpp:28, 54 and h/tron/simd/types.hpp:25-27). `bf16x32` is `__m512i` (64 bytes). |
| SIMD, AVX2, AVX-512, AMX | SIMD: one CPU instruction that operates on a whole vector register. AVX2 and AVX-512 are the x86 instruction sets with 256-bit and 512-bit vectors. AMX is the Intel tile-matrix instruction set used by the attention kernel in `src/tron/kernels/amx_attn.cpp`. |
| intrinsic | A compiler-provided function such as `_mm512_load_si512` that maps to one SIMD instruction. clang defines these in its own headers. |
| tron_mm_load_bf16 | The macro for the aligned load of one bf16s chunk: `_mm_load_si128` in the 8-lane build (auto.hpp:40), `_mm256_load_si256` in the 16-lane build (auto.hpp:69). |
| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (AVX-512, the production build and the CI build) or 8 (AVX2 only). The macro `TRON_AVX512_ENABLED` selects 16, and the CMake option `AVX512` defines that macro (h/tron/simd/auto.hpp:17-21, src/tron/CMakeLists.txt:269-272). |
| TRON_CHUNK_SIZE | The number of 32-bit float lanes in one SIMD chunk: 16 or 8. |
| view | `tron::view`, the strided tensor view template (h/tron/tensor/view.hpp:16-25, 115-116): a data pointer plus extents and strides. `view::operator[]` returns the element at `data + i * stride`. |
| chunky | The per-element-type SIMD chunk helper (h/tron/kernels/chunky.hpp:15). `chunky<bf16, true>` loads or stores one aligned bf16s chunk at a bf16 pointer. |
| scaled_v_expr | The CPU kernel that computes the weighted sum of the V rows of one page (`detail::scaled_v_expr`, kv_cache.hpp:2231-2438). `page::scaled_v` builds it. |
| fill_storage_slot | A test-only helper that fills every kv_block of one storage slot with random bf16 values (kv_cache.hpp:1646-1656). Its only caller is `book::fill_random`. |
| 8-lane V accessors | `page::v`, `page::v_ptr`, the 8-lane branch of `page::copy_storage_slot` and the 8-lane branch of `page::scaled_v`. They return bf16 pointers or bf16 views into the `bf16s` array `v` (kv_cache.hpp:1954-2005, 2188-2197, 2514-2519). |
| software attention, hardware attention, staging, AMX gate | Software attention is the attention computed on the CPU (h/tron/models/self_attention.hpp). Hardware attention is the attention computed on the FPGA. Staging is the copy of K and V rows into the layout the hardware reads. The AMX gate is the runtime check in the CPU path that sends a page to the AMX kernel when its conditions hold (self_attention.hpp:1757-1768). |
| gof, gof::populate | GOF: group of four, the 4-token unit of KV data staged for the FPGA attention hardware (h/tron/gof.hpp:3-5). `gof::populate` copies K and V rows into it (src/tron/gof.cpp:188). |
| EAGLE, x_data | EAGLE is a speculative-decoding scheme: a small draft model proposes tokens and shares the KV cache with the exact model (h/tron/scheduler/full.hpp:1666-1667, kv_cache.hpp:1323-1324). `x_data` is the book's storage for the EAGLE embeddings, kept beside each KV page (kv_cache.hpp:1328, 2024-2025). |
| DMA arena | DMA: direct memory access, memory that a hardware device can read without the CPU copying it. The DMA arena is the byte array (`unique_dma<uint8_t[]>`) that holds all kv_blocks of one slot. It is allocated through an `operator new[]` wrapper, so the allocation itself creates the kv_block objects (kv_cache.hpp:1424-1435, h/system/memory.hpp:167-190). |
| Note [Title] | The codebase writes design notes as block comments headed `Note [Title]`. Note [KV block lifetime] and Note [Packed V layout] are two of them. |
| ISO C++, N4950 | The C++ standard. N4950 is the C++23 draft. A name in brackets such as [expr.add] is a stable section name, and the number after the slash is the paragraph. |
| undefined behavior (UB) | Behavior for which the standard imposes no requirements. A compiler may assume it never happens. |
| glvalue, lvalue | A glvalue is an expression that names an object, such as `*p` or `a[i]`. An lvalue is a glvalue that names a persistent object, not a temporary. |
| similar, pointer-interconvertible, trivially copyable, nested, array-to-pointer conversion | N4950 terms. Similar: the same type apart from const and volatile at any level ([conv.qual]/2). Pointer-interconvertible: two objects at one address between which a `reinterpret_cast` may move, for example a struct and its first non-static data member ([basic.compound]/4). Trivially copyable: a type whose bytes may be copied with memcpy to make a valid copy ([basic.types.general]/2-3). Nested: the standard's term for an object placed inside another object's storage ([intro.object]/4). Array-to-pointer conversion: the conversion of an array operand to a pointer to its first element ([conv.array]). |
| strict aliasing, [basic.lval]/11 | The rule that an object may be read or written only through a glvalue of a similar type, or of a char type. Compilers use it to assume that differently typed accesses do not overlap. |
| [expr.add]/4 and /6 | The rules for pointer plus integer. Paragraph 4: defined only inside one array object. Paragraph 6: undefined when the pointer's type is not similar to the array's element type. |
| TBAA, struct-path tag, _ZTS4bf16 | TBAA: type-based alias analysis. LLVM metadata (`!tbaa`) that records the type of each load and store. The `omnipotent char` node marks an access that may overlap anything. A struct-path tag records the member path inside a struct. `_ZTS4bf16` is the mangled name of `tron::bf16`. |
| __may_alias__ | The GNU type attribute that tells the compiler a type may overlap objects of any other type. It is the documented way to make such accesses safe. |
| std::launder | A library function that returns a pointer to an object that already lives at an address. It does not create objects ([ptr.launder]/2). |
| UBSan, ASan, TySan | clang sanitizers. UBSan (`-fsanitize=undefined`) checks a list of undefined operations. ASan checks address validity. TySan (TypeSanitizer, `-fsanitize=type`) checks type-based aliasing and is absent from clang 19. |
| clang-tidy, lefthook | clang-tidy is clang's static checker, configured by a `.clang-tidy` file. lefthook is the git-hook runner configured in lefthook.yml at the repository root. |
| syntax-only check | A compile with `-fsyntax-only` using the product flags and mirrored product headers. It checks types and template instantiation, not code generation. |
| standalone model | A small C++ program that copies the pointer and load pattern of one tron read. Not an ML model. |
| host tests, TEST_CASE, TEMPLATE_TEST_CASE | Host tests are the test binaries that `make test-host` runs on the build host without an FPGA. `TEST_CASE` is the Catch2 test macro, and the string is the test name. `TEMPLATE_TEST_CASE` is the same macro instantiated once per listed type. |
| qwen3-4b | The 4-billion-parameter Qwen 3 language model, used for the token-identity runs. |
| kill switch, A/A | The kill switch is `TRON_AMX_DISABLE`, the run-time setting that turns the AMX kernel off. An A/A run is the same binary run twice with the same settings. |
| campaign, campaign record | A campaign is one planned series of test runs on delphi-3bda. The campaign record is the local report `first-3bda-test-results.html` of 2026-09-22 (not in the tron repository). |
| NaN | Not-a-number, a float value that marks an invalid result. |
| hunk | One changed region of a diff. |
| PR #4557 | "Typed KV-cache tensors for packed V and native K (parent of #4424)", open, base branch of #4587, head 633cb88896. |
| PR #4587 | "KV blocks: create them in the DMA allocation, drop construct_kv_blocks (stacked on #4557)", open draft based on the #4557 branch, head c73e7fb2f9. |
| PR #4584 | "Own KV cache scalars and derive typed page views", closed draft with an alternative design (bf16 arenas, no kv_block), head 9380012de5. |
| main | `origin/main` at 11b7763c87 (fetched 2026-09-23). |

All `file:line` references below are at c73e7fb2f9 unless a revision is named.

## Where the note comes from

The comment is the last paragraph of Note [KV block lifetime] in kv_cache.hpp at the head of PR #4587 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1459-L1462]. The PR is https://github.com/positron-ai/tron/pull/4587.

```
  // Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr
  // steps through V with vector pointers, fill_storage_slot walks one bf16
  // pointer across K and V, and the 8-lane V accessors read the bf16s (SIMD
  // vector) array v as bf16 values.
```

History of the paragraph:

- The #4557 head 633cb88896 has no such paragraph (a grep for "ISO C++" in its kv_cache.hpp finds nothing).
- Commit 39a6899446 (the parent of c73e7fb2f9) introduced it with a first item "k_view reads the bf16s (SIMD vector) array k as bf16 values".
- Commit c73e7fb2f9 made `k` a plain bf16 array, removed that item and added the 8-lane V item.

The PR body has a section "Still outside ISO C++ (unchanged here)" with six items. This issue tracks the three that the code comment names. The other three are not in this issue:

- "The EAGLE `x_data` casts": the `reinterpret_cast<T*>` and `reinterpret_cast<const T*>` in `page::x<T>`, the accessor of the EAGLE embedding bytes in `x_data` (kv_cache.hpp:2024-2038, casts at 2029 and 2036). Not in this issue.
- "The intrinsic and AMX tile loads": every `_mm512_load_si512` and AMX tile load dereferences a vector-typed pointer inside the compiler's header. Not in this issue, except where a tron pointer feeds it (read 1).
- "`token_tree.hpp:305-314` has the same discarded-placement-new pattern": a separate lifetime question in `h/tron/scheduler/token_tree.hpp`. Not in this issue.

## The three reads

### 1. scaled_v_expr steps through V with vector pointers

The code of this read is kv_cache.hpp:2231-2438 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L2231-L2438].

| | |
|---|---|
| Code | The stepping pointer is the member `const bf16s* const data` (kv_cache.hpp:2233). The 16-lane constructor sets it with `data(reinterpret_cast<const bf16s*>(v_vnni_access::plane(v_page)))` (2318-2329, cast at 2326). The 16-lane loops form `reinterpret_cast<const bf16x32*>(data + i * (head_size / chunk_size))` and load with `_mm512_load_si512(tile + k)` (2257-2275 for head sizes 256 and 512, 2337-2342 for 64, 2352-2361 for 128). The 8-lane constructor sets `data(reinterpret_cast<const bf16s*>(v_page.data))` (2400). The 8-lane loop steps `const bf16s* tile = data + i * (head_size / chunk_size) + part * 8` and loads with `tron_mm_load_bf16(tile + k)` (2413-2421). |
| Build variant | Both, with different defects. The 16-lane build is the one production and CI compile. |
| Production or test | Production. `apply_page_tok` in the CPU software-attention path calls `page.template scaled_v<geometry.kv>(...)` for every (query, page) pair that the AMX gate does not take (h/tron/models/self_attention.hpp:1842 and 1846, the AMX branch returns at 1768). Tests: t/t_llama_unit.cpp TEMPLATE_TEST_CASE "scaled_v" (2033, instantiated for `full_retention_scaled_v_cache` and `mixed_retention_scaled_v_cache` at 2035-2036, calls at 2153 and 2191), TEST_CASE "scaled_v supports wide values" (1564), TEST_CASE "scaled_v padding NaN" (3028, calls at 3127 and 3196), and calls at 208, 1194, 3003 and 3005. Line 179 is inside the requires-expression of the concept `page_scaled_v_accepts_geometry` (176-180), a compile-time check used by `STATIC_REQUIRE` at 1473, not a runtime call. |
| Declared storage type | 16-lane: `alignas(V_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols]` inside `v_vnni_tensor` (v_vnni.hpp:268, the constant is 64 at line 79), held as `alignas(kv_block_alignment) v_storage v` in kv_block (kv_cache.hpp:2454, 2459). 8-lane: `alignas(kv_block_alignment) bf16s v[page_size][head_size / chunk_size]`, a 2-D array of `__m128i` (2462). |
| Access type | 16-lane: pointer arithmetic in `__m256i` units, then a load through a `__m512i` glvalue. clang defines `_mm512_load_si512(void const *__P)` as `return *(const __m512i *) __P` (avx512fintrin.h:4481-4484). 8-lane: arithmetic and loads in `__m128i` units. `_mm_load_si128(__m128i const *__p)` is `return *__p` (emmintrin.h:3425-3427). |
| Rule it breaks | 16-lane: [expr.add]/6. `data` has type pointer to `__m256i`. The array's element type is `bf16`. The two are not similar. So every `data + ...` is undefined. Also [expr.add]/4: no `__m256i` or `__m512i` array object exists at that address. Also [basic.lval]/11: the `__m512i` glvalue reads objects whose type is `bf16`. 8-lane: [expr.add]/4. `data` points at element 0 of the inner array `v[0]`, and the row stride carries it into `v[1]`, `v[2]` and so on (the usual flattening of a 2-D array). The 8-lane loads themselves match the storage type. |
| On main (11b7763c87) | Yes, with the storage type and the access type swapped. main declared `bf16s v[page_size / 2][head_size / chunk_size * 2]` at 16 lanes (main:2456), the constructor took `const bf16s* data` (main:2324-2332), and `page::scaled_v` passed `v[0]` (main:2518-2519). The loop text was identical (main:2275-2277, 2344-2345, 2359-2360, 2417-2418). So main read `__m256i` objects through `__m512i` loads and crossed the inner-array bound. At the head the storage is `bf16` and the type mismatch starts at the first pointer step. The change came with b951ba9b4c, the first commit of #4557. The diff from 633cb88896 to c73e7fb2f9 has no hunk inside scaled_v_expr. |
| A conforming version | Step with `const bf16*` inside `data_`. Then [expr.add] holds. Pass that pointer to `_mm512_load_si512`, whose parameter type is `void const*`. No vector-typed pointer is then formed in tron code. The intrinsic's own dereference stays a compiler extension. The strongest form copies each 64-byte tile with `std::memcpy` into a `__m512i`. At 8 lanes `_mm_load_si128` takes `__m128i const*`. So one `reinterpret_cast` per load remains. The storage must also become a `bf16` array for the cross-row arithmetic to be defined. |

One detail of the 8-lane path at the head. `page::scaled_v` casts the whole 2-D array `v` (kv_cache.hpp:2518). That operand converts (array-to-pointer conversion) to a pointer to the row array `v[0]`, not to element `v[0][0]`. The constructor then casts the `const bf16*` to `const bf16s*` (2400). This is not a conversion back to the original type. Under [expr.static.cast]/14 the pointer value is unchanged. So under a strict reading `data` designates the row array object. main's `v[0]` designated element 0. The address and the generated code are the same. The strict-reading defect set grew by this step rather than staying equal.

### 2. fill_storage_slot walks one bf16 pointer across K and V

The code of this read is kv_cache.hpp:1646-1656 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1646-L1656].

| | |
|---|---|
| Code | `auto& block = kv_block_at_storage<geometry>(offset, kv_head, pg)`, then `bf16* data = reinterpret_cast<bf16*>(&block)`, then `data[i] = static_cast<bf16>(distribution(gen))` for every i below `sizeof(block) / sizeof(bf16)` (kv_cache.hpp:1651-1654). `kv_block_at_storage` asserts that `sizeof(kv_block_t)` equals 2 * page_size * head_size * 2 bytes, with no padding (1593-1595), and kv_block asserts `sizeof(k) == sizeof(v)` (2466). So the one pointer covers exactly `k` and then `v`. |
| Build variant | Both. The function has no `TRON_CHUNK_SIZE` guard. Only the type of `v` differs. |
| Production or test | Test only. The only caller is `book::fill_random` (kv_cache.hpp:1223-1231, calls at 1227 and 1230), whose comment says "For testing only" (1218). `fill_random` is called from t/t_llama_unit.cpp:1148-1149 (TEST_CASE "fixed KV layout addresses each slot geometry", 1125) and :2376 (TEST_CASE "apply and join page ranges", 2321). There is no caller under src/. |
| Declared storage type | `alignas(kv_block_alignment) bf16 k[page_size * head_size]` (2448), followed by `v`: at 16 lanes a `v_vnni_tensor` with the private array `bf16 data_[Rows * Cols]` (v_vnni.hpp:268), at 8 lanes `bf16s v[page_size][head_size / chunk_size]` (2462). |
| Access type | Writes through `bf16` glvalues. `bf16` is a class. So `data[i] = x` is its copy assignment on whatever object `data[i]` names. The scalar store is the `__bf16` member. |
| Rule it breaks | [expr.add]/4: `data + i` for i at or above page_size * head_size leaves the array `k`. Note 1 of that paragraph says adding a value other than 0 or 1 to a pointer to a complete object is undefined. [expr.static.cast]/14 with [basic.compound]/4: `reinterpret_cast<bf16*>(&block)` keeps its value. It still points at the kv_block object, not at `k[0]`. The reason: kv_block's first member is the array `k`, and an array is not pointer-interconvertible with its first element. Under that reading `data[0]` names a kv_block through a `bf16` glvalue ([expr.ref]/8, [basic.lval]/11). [intro.object]/9 and /10: no `bf16` array of 2 * page_size * head_size elements can be created over the block. Such an array would overlap the kv_block without being nested in it. 8-lane only: the `v` half holds `__m128i` objects, and `bf16` writes into them are outside the rule as well. |
| On main (11b7763c87) | Yes. The text is byte-identical (main:1611-1620). On main both `k` and `v` were `bf16s` arrays. So every write was a `bf16` write into a vector object. At the head, in the 16-lane build, every element the pointer touches is a `bf16`. Only the pointer stepping across two arrays remains. The 8-lane V half keeps the type mismatch. main had no `std::launder` at the accessors (0 occurrences), the head has three (1565, 1574, 1614). |
| A conforming version | Generate the values in storage order, then either `block = std::bit_cast<kv_block_t>(buf)` with `buf` a `std::array<bf16, N>` ([bit.cast]: same size, both trivially copyable, which the accessor already asserts), or `std::memcpy(&block, buf.data(), sizeof block)` ([cstring.syn]/3), or one loop per array with an owner-provided fill for `v`. Each keeps the same bytes in memory: draw i goes to element i. At 8 lanes no form is inside ISO C++. The V elements there are `__m128i`. |

One caveat that applies to all three reads. In this toolchain `__bf16` is not designated as `std::bfloat16_t`. The clang 19.1.7 driver used for the checks below does not define the macro `__STDCPP_BFLOAT16_T__`. So N4950 [basic.fundamental]/12 places no requirements on `__bf16`. Even the matching `bf16` writes are inside ISO C++ only up to that caveat. Whether the nix-built clang behaves the same is not established.

### 3. The 8-lane V accessors read the bf16s array v as bf16 values

The code of this read is kv_cache.hpp:1954-2005 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1954-L2005].

| | |
|---|---|
| Code | Storage: `alignas(kv_block_alignment) bf16s v[page_size][head_size / chunk_size]` (kv_cache.hpp:2460-2463). `page::v` builds `view<bf16, true, false, seq<head_size>>` from `reinterpret_cast<bf16*>(kv_block(slot, kv_head).v[i_page])` (1957-1970, casts at 1961 and 1969). `page::v<geometry>` does the same for a named geometry (1982-1997, casts at 1986 and 1996). `page::v_ptr` returns that view's `data` pointer (1972-1977 and 1999-2004). `copy_storage_slot` casts two rows to `bf16*` and calls `memcpy` (2188-2197, casts at 2191 and 2194). `page::scaled_v` casts the whole 2-D array to `const bf16*` (2514-2519, cast at 2518), and the 8-lane `scaled_v_expr` constructor casts it back (2400). |
| Build variant | 8-lane only. Every site sits under the `#else` of `#if TRON_CHUNK_SIZE == 16`. The 16-lane `v` is a `v_vnni_tensor` with typed accessors. |
| Production or test | Both, in the 8-lane build. Production site 1: the V save `pg.template v<geometry.kv>(slot, kv_head, j)` with its `.set(...)` call (h/tron/models/model.hpp:2846-2847). Production site 2: the hardware-attention staging function `v_head_fn`, which returns `v_ptr<...>` (h/tron/scheduler/full.hpp:2767-2774). `gof::populate` calls it (src/tron/gof.cpp:213). `shuffle_v_entry` (h/pos/hwattention.hpp:846) then reads scalar `bf16` values through that pointer (`src[pchan].to_bits()` in the `packed` statement at 884-888). It also calls `shuffle_v_entry_padded` (defined at 820, call at 861), which reads `dst[offset] = src[entry]` at 840. Production site 3: `page::scaled_v` (self_attention.hpp:1842 and 1846). Production site 4: `copy_storage_slot` through `book::append`. Tests: t/t_llama_unit.cpp:1163-1164 (`std::fill_n` through the view), :2293 (`.set` of a NaN row), and :2100-2114 (does not compile, see below). |
| Declared storage type | A 2-D array of `__m128i` vectors: page_size rows of head_size / 8 vectors each, 64-byte aligned. |
| Access type | `bf16` glvalues: `view::operator[]` returns `*(data + i * s0)` (h/tron/tensor/view.hpp:146-148), `std::fill_n`, and the `src[...]` reads in hwattention.hpp. Vector accesses through `chunky<bf16, true>::get` and `set`, which do `bf16` pointer arithmetic `data + i * chunk_size` and then `reinterpret_cast` to `bf16s*` for `_mm_load_si128` / `_mm_store_si128` (h/tron/kernels/chunky.hpp:49-59, reached from view.hpp:156-158 and 188-191, macros at auto.hpp:40 and 42). |
| Rule it breaks | [basic.lval]/11: `bf16` glvalues name `__m128i` objects, and a class type is not similar to a vector type. `__m128i` is not an ISO type. The rule applies by analogy. [expr.add]/4 and /6: `bf16` pointer arithmetic over storage that holds no `bf16` array. [intro.object]/9: no `bf16` array can be created in `v`'s bytes. Such an array would overlap the kv_block without being nested in it. The kv_block must exist for the `std::launder` at the accessors ([ptr.launder]/2). The `memcpy` in `copy_storage_slot` performs no typed access and is the least problematic site ([basic.types.general], [cstring.syn]/3). The comment says "read", but the production sites also write: the `.set` call at model.hpp:2846-2847 ends in a vector store after `bf16` arithmetic. |
| On main (11b7763c87) | Yes. The same casts are at main:1939, 1947, 1964, 1974 and the same storage at main:2459. The text of the cast dates from 493412716c (2026-07-10). The `#if TRON_CHUNK_SIZE` split in kv_cache.hpp dates from 20239f14bb (2024-07-31). The PR series changed one thing here: `page::scaled_v` now casts `v` to `const bf16*` and the constructor casts back (b951ba9b4c). main passed `v[0]` as `const bf16s*` to a constructor taking `const bf16s* data` (main:2397-2404, 2518-2519). At the head, the 8-lane `v` is the only kv_block member still stored as vectors and read as scalars. |
| A conforming version | Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch, as c73e7fb2f9 did for `k`. The bytes, the alignment and the order stay the same. chunk_size consecutive `bf16` values form one `bf16s`. The accessors then build their views with no cast, `copy_storage_slot` copies `bf16` rows, and `page::scaled_v` needs no cast. Only the intrinsic's dereference remains. `_mm_load_si128` takes `__m128i const*`, and `chunky` therefore keeps one `reinterpret_cast` per chunk. |

State of the 8-lane build:

- Production and CI compile 16 lanes:
  - The CI job configures with `--preset native` on runners labeled `avx512` (.github/workflows/cmake-single-platform.yml:353 and 151).
  - The nix builds pass `-DAVX512=ON` (flake.nix:1208, nix/cmake-tron-test-build.nix:88).
  - The `deb` preset inherits `AVX512 ON` from the option default (CMakeLists.txt:44).
- Three routes produce an 8-lane tree:
  - The `darwin` preset (`AVX512 OFF`, CMakePresets.json:50-66).
  - A `cmake --preset native` with no other option on a host that lacks one of the six probed AVX-512 features (CMakeLists.txt:95-117 sets `AVX512 OFF` with a warning).
  - An explicit `-DAVX512=OFF` (one such tree, `gen-avx2`, is configured on delphi-3bda).
- `make` never selects 8 lanes on Linux. It picks `cross-avx512` on a host without AVX-512 (GNUmakefile:225-237).
- A syntax-only check of t/t_llama_unit.cpp with the `gen-avx2` flags reports 131 errors at c73e7fb2f9, at 633cb88896 and at a main-equivalent commit (e6c53ba70a, whose kv_cache.hpp, simd and tensor headers equal origin/main). The three error sets are identical apart from line numbers. None is in kv_cache.hpp. Errors by file:
  - kernels/wide.hpp 58
  - t_llama_unit.cpp 37 (15 `no member named 'set_v'`, 5 `get_v`, 2 `no viable conversion from 'tron::bf16' to 'bf16s'` at t_llama_unit.cpp:2113)
  - models/ranged_mask.hpp 14
  - simd/fp32.hpp 5, kernels/expr.hpp 5
  - hardware/permuted.hpp 3
  - simd/int4.hpp 2, simd/bf16.hpp 2, models/self_attention.hpp 2, hardware/dmatensor.hpp 2
  - common/mask.hpp 1
- The PR body reports 130 for the same check.
- Whether any 8-lane tron binary links or runs anywhere is not established.

## Why it works today, and what would show a break

Compiler and flags:

- Compiler: clang 19.1.7 from nix (CMakePresets.json:18-19 names `clang-19`).
- Language standard: `-std=gnu++23`. Evidence:
  - `CMAKE_CXX_STANDARD 23` at CMakeLists.txt:56-57.
  - No `CMAKE_CXX_EXTENSIONS` setting anywhere.
  - Every captured compile command from delphi-3bda carries `-std=gnu++23`.
- Optimization level: `-O3`. The captured commands carry `-O2 -g -DNDEBUG` and later `-O3` (src/tron/CMakeLists.txt:293 and 316), and the local clang 19.1.7 driver applies the last `-O` flag.
- Aliasing flags: none. No `-fstrict-aliasing` or `-fno-strict-aliasing` appears in CMakeLists.txt, cmake/, flake.nix, GNUmakefile, CMakePresets.json, the per-target CMake files or the captured commands. So type-based alias analysis is on.
- Warning set: `-Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed` (CMakeLists.txt:609 and 621). It contains no aliasing warning.

Mechanism, verified on standalone models of the three code patterns. The compiler was clang 19.1.7 from the `ziglang==0.14.0` Python package, which bundles a clang 19.1.7 driver. It is the same upstream version as the nix toolchain but a different build. The headers were the product's libstdc++ 14.3.0 and clang resource headers mirrored from delphi-3bda. The flags were `-std=gnu++23 -O3` and the product's ISA flags.

- clang tags every vector-typed load and store with the `omnipotent char` TBAA node. A `bf16` access is tagged by its form. A member access (`p->content = x`, or a read of `.content` such as `to_bits()` does) is tagged with the struct-path node `_ZTS4bf16 -> __bf16 -> omnipotent char`. A whole-object `bf16` copy (`data[i] = x`, `*p = x`, `std::fill_n`) is tagged with the scalar node `__bf16 -> omnipotent char`, and no `_ZTS4bf16` node appears. Both chains end at `omnipotent char`. So the optimizer treats every vector access as possibly overlapping every `bf16` access, in both directions. This is the main reason the typed accesses produce the intended values under clang. The byte-offset compilation of the pointer arithmetic (the `getelementptr` bullet below) is the other part.
- A reorder probe confirms that TBAA is active and that only the char tag protects these reads. A vector load, a `bf16` store into the same 64 bytes, and a vector reload compile to three instructions (`vmovdqa64`, `vpextrw`, `vpxorq`). So the reload is kept. The same pattern with `long long` and `float` folds to `xorl %eax, %eax` (return zero). So the reload is removed.
- With `-fno-strict-aliasing` the IR carries no `!tbaa` node at all (0 nodes on the same model). That switch is documented and portable, and its cost on tron is not measured.
- Pointer arithmetic compiles to byte offsets (`getelementptr inbounds`). LLVM's `inbounds` rule refers to the allocated object, not to a C++ member or a sub-array (LLVM 19.1.7 Language Reference manual, section "getelementptr"). In the fill model the store carries a scalar `__bf16` tag, not a struct-path tag that names `kv_block::k`. So no member boundary reaches LLVM.
- In the 8-lane model the vector store is `store <8 x i16> ... omnipotent char`, and the scalar read is `load bfloat` tagged `__bf16`. The address computation is `getelementptr inbounds [64 x [16 x <2 x i64>]]`.
- Alignment holds. `v_vnni_tensor` and its `data_` are 64-byte aligned (v_vnni.hpp:246, 268). `kv_block_alignment` is 64 bytes (kv_cache.hpp:2440). Every tile offset is a multiple of 64 bytes for the allowed head sizes.
- Two things are not established. First, that the nix-built clang emits the same TBAA metadata as the zig-built clang used here. Second, the code generation of the real translation units. The local check is syntax-only.

The reliance is on an implementation detail, not on a documented guarantee. clang's `CodeGenTBAA.cpp` (release 19.x) has no vector-type branch and falls through to the char node with the comment "For now". clang's `__m128i`, `__m256i` and `__m512i` typedefs carry no `__may_alias__` attribute (emmintrin.h:20, avxintrin.h:36, avx512fintrin.h:35). GCC's headers do carry `__may_alias__` on these typedefs. GCC was not tested on this code and is not the product compiler.

What would detect a break today: nothing in the build or the test flow.

- clang emits no diagnostic. The 16-lane model compiled with `-Wall -Wextra -Wpedantic -Wstrict-aliasing=2 -Wcast-align -fsyntax-only` gives exit 0 and no output. clang's `-Wstrict-aliasing` groups are empty by design (clang 19 DiagnosticGroups.td: "Just silence warnings about -Wstrict-aliasing for now"). `-Wcast-align` warns for C-style casts only, not for `reinterpret_cast`. The off-by-default `-Wundefined-reinterpret-cast` is silent for the scalar-to-vector, vector-to-scalar and vector-to-class patterns used here.
- UBSan has no aliasing check. On the models, `-fsanitize=undefined` emits only the pointer-overflow check (address wrap-around) and the null and alignment checks. Both pass for aligned addresses inside one arena. The `UBSAN` CMake option exists (CMakeLists.txt:42, 134-136, 585-587). No preset and no CI job uses it. The ASan target list excludes `t_llama_unit` (GNUmakefile:597-602).
- ASan checks address validity only. It cannot see a type mismatch at a valid address. This follows from the tool's design and was not run here.
- TySan is the tool for this kind of defect. clang 19.1.7 rejects it: `error: unsupported argument 'type' to option '-fsanitize='`. LLVM 20 includes it as an experimental feature (Clang 20.1.0 release notes, Sanitizers section: "Introduced an experimental Type Sanitizer, activated by using the -fsanitize=type flag.").
- The repository has no `.clang-tidy`, and CMake, lefthook and the GNUmakefile do not run clang-tidy.
- `-D_GLIBCXX_ASSERTIONS` (the libstdc++ macro that turns on the library's own precondition checks), which `t_llama_unit` compiles with (t/CMakeLists.txt:592-598), does not check aliasing.
- GCC 11.4 with `-Wstrict-aliasing=1` warns at the `reinterpret_cast` line of a fill model (with a `uint16_t` payload in place of `__bf16`). GCC's default level is silent.

Test evidence:

- A delphi-3bda run on 2026-09-22 of the #4557 branch gave 88 passed, 0 failed, 1 skipped host tests, the same status set as main. The host suite ran on the working-tree snapshot 48ab31f7 of that branch. 682064f8fb, a later commit of the same branch, was the binary of the performance comparison only. The token-identity check also ran the 48ab31f7 binary.
- Neither 48ab31f7 nor 682064f8fb is an ancestor of 633cb88896 (`git merge-base --is-ancestor`). The branch was rewritten after the run.
- The `scaled_v_expr` struct text of 48ab31f7 is identical to that of 682064f8fb. It equals the head's apart from the spelling of two view constants (`true, false` against `VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE` in the 8-lane constructor parameter). Three comment paragraphs inside the struct also differ (the "Invariant", "Direct element writes" and "Note [Packed V layout]" sentences above the 16-lane constructor). `fill_storage_slot` is byte-identical from main to the head.
- The pass of the three named `scaled_v` cases is implied by the `t_llama_unit` pass, not shown separately.
- The unit tests at c73e7fb2f9 itself on delphi-3bda are listed under "Not done yet" in the PR body.
- The 16-lane syntax checks of the affected test units at c73e7fb2f9 report 0 errors and 0 warnings (PR body).
- The 8-lane accessors have not been executed anywhere I can point to.

## Options (the code owner decides)

Read 1, scaled_v_expr:

1. Step with `const bf16*`. Three changes:
   - Change the member to `const bf16* const data`.
   - Change the 16-lane tile to `const bf16* tile = data + i * head_size + chunk_offset * pair_chunk_size` and load with `_mm512_load_si512(tile + k * pair_chunk_size)`.
   - Change the 8-lane loads to `tron_mm_load_bf16(reinterpret_cast<const bf16s*>(tile + k * chunk_size))`.

   Cost: est. 25 lines in `scaled_v_expr` (member, two initializers, three tile expressions, the 8-lane loop). The byte offsets are identical. On the standalone model the current form, the `bf16`-stepping form and the memcpy form all compile to one load instruction with the address folded (`vmovaps 64(%rdi,%rsi), %zmm0` on the model used here). Risk: a stride error in `bf16` units would read wrong rows. The three `scaled_v` tests compare against reference sums and would catch it. At 8 lanes the storage stays `__m128i`. The cross-row [expr.add] question then remains. Read 3, option 1 removes it. Precedent: PR #4584 wrote exactly this (9380012de5 kv_cache.hpp:2202, 2207, 2227-2249, 2300, 2311-2315, 2372, 2385-2408, 2504). #4584 was never compiled by its author, per its body. The codebase already passes `bf16` pointers to the intrinsics in five places in v_vnni.hpp and one in amx_attn.cpp [v_vnni.hpp:136, 344, 364, 388, 402 and amx_attn.cpp:223].
2. Option 1 plus `std::memcpy` into a `__m512i` for each tile. Verified on the standalone model: the same single instruction, and the IR load carries no TBAA tag at all. This removes the dependence on clang's vector TBAA policy. Cost: the same lines plus one temporary per load.
3. Keep the code and the comment. Zero code risk. No tool detects a future regression, and a compiler change to vector-type TBAA could miscompile silently. The comment's wording is accurate for this site.

Read 2, fill_storage_slot (test only):

1. Whole-block `std::bit_cast`. Generate a `std::array<bf16, N>` in storage order, then `block = std::bit_cast<kv_block_t>(buf)`. The same bytes in memory as today. Inside ISO C++ at 16 lanes ([bit.cast]). One stack temporary of `sizeof(kv_block)` per block: 32 KiB at head size 128, 128 KiB at head size 512 (128 KiB is 1.6 % of the 8 MiB default Linux main-thread stack, `ulimit -s` = 8192 KiB on the check host, not measured on delphi-3bda). On a model where both operands are reference parameters, clang 19.1.7 folds the bit_cast and the assignment into one 32768-byte copy intrinsic (`llvm.memcpy` or `llvm.memmove`, depending on whether the operands can alias). Precedent: t/t_llama_unit.cpp:2023-2031 already builds random `bf16` values with `std::bit_cast`.
2. Whole-block `std::memcpy` from the same buffer. Also inside ISO C++ under the common reading ([cstring.syn]/3). It is slightly weaker than `bit_cast`. [basic.types.general]/3 is written for a copy from an object of the same type. Precedent: `copy_storage_slot` already copies K rows with `memcpy` (kv_cache.hpp:2174-2182).
3. One loop per array: `for (bf16& e : block.k) e = ...`, then a new owner operation on `v_vnni_tensor` for `data_` (16 lanes) or per-vector `bit_cast` at 8 lanes. Adds one permitted access path to the plane, which Note [Packed V layout] (v_vnni.hpp:52-58) must list.
4. Fill through the typed views (`k_view`, `v.as_view().at(...)`, `page::v<geometry>`). Changes the draw-to-element mapping. Neither test depends on the mapping. The `fill_random` comment "interprets no coordinates" (1221-1222) and the Note [Packed V layout] sentence naming `fill_random` as the exception (v_vnni.hpp:57-58) would need rewording.
5. Keep as is. Test only. Production behavior does not change. The sentence at kv_cache.hpp:1459-1462 and the PR body already record it.
6. The PR #4584 design: a `bf16[]` arena and a `kv_page_view` with `T* data_`. The fill then writes `block.data_[i]` inside one array object (9380012de5 kv_cache.hpp:1617-1628, 1309, 1319, 1426, 1436, 2431-2471). Inside ISO C++ for the pointer stepping across K and V. Cost: the whole design change, 538 changed lines (280 insertions and 258 deletions across 6 files, `git diff --shortstat 633cb88896..9380012de5`), and the removal of the V owner inside kv_block that the reviewing maintainer's design sketch (cited in the #4587 body) asks for. That PR was closed on 2026-09-24 as the design not chosen.

Read 3, the 8-lane V accessors:

1. Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch (the pattern c73e7fb2f9 used for `k`). `page::v`, `page::v_ptr`, `copy_storage_slot` and `page::scaled_v` lose their casts. The shared member `const bf16s* const data` of `scaled_v_expr` must change too (read 1, option 1 does that). The 8-lane test block t/t_llama_unit.cpp:2100-2135, which does not compile today, needs a rewrite. Cost: est. 30 lines in kv_cache.hpp plus the test block. No effect on the 16-lane build. All changed code is under `#else`. Risk: the 8-lane tree cannot be compiled to zero errors today (131 pre-existing errors in other headers). Verification is therefore limited to comparing error sets. Precedent: c73e7fb2f9 for `k` (commit message: "Pointer arithmetic over bf16 elements of a vector array is outside ISO C++ ([expr.add])"), and PR #4584 for the 8-lane V (`v_view()[i_page]` with no cast at 9380012de5:1932, 1939, and no `reinterpret_cast<bf16*>` left in that file).
2. A typed owner for the 8-lane plane in the style of `v_vnni_tensor` (one aligned `bf16` array, `as_view()` on lvalues only). Both lane branches then declare `v_storage v`. More code than option 1 for the same result. Precedent: `v_vnni_tensor` (v_vnni.hpp:246-269) and #4584's `kv_page_view::v_view()` (9380012de5:2458-2471).
3. A partial fix for the staging path only. `gof::populate` already passes a 64-byte-aligned `bf16` scratch buffer as the third argument of `v_head_fn` (gof.cpp:213, buffer at 203). The 8-lane lambda ignores that argument (full.hpp:2769). Copying the row into that scratch buffer, as the 16-lane branch of the same lambda does, would make hwattention.hpp read only `bf16` objects without touching that file.
4. Delete the 8-lane V path, or the 8-lane variant as a whole.
   - Evidence for:
     - No CI job, no makefile route and no shipped package builds it.
     - Its `t_llama_unit` has not compiled at least since the current main.
   - Evidence against:
     - The `darwin` preset selects it.
     - v_vnni.hpp:47-50 records the decision to keep the 8-lane classes compiling.
     - The GNUmakefile documents compile-only development on laptops without AVX-512 (Note [Cross-Compile for AVX-512], GNUmakefile:987-995).
   - Whether anyone builds the `darwin` preset is not established.
5. Keep the code and the comment. Leaves a documented out-of-ISO read in a build variant that does not compile, and leaves the test block at t_llama_unit.cpp:2100-2135 uncompilable.

## What is not affected

- The 16-lane K path after c73e7fb2f9. `k` is `bf16 k[page_size * head_size]` (kv_cache.hpp:2448) and `k_view` builds its views from the array with no cast (2468-2481). No vector-typed read of `k` remains in kv_cache.hpp.
- The 16-lane V plane reads in v_vnni.hpp. They pass `bf16` pointers to `_mm512_load_si512` and `_mm512_store_si512`, whose parameters are `void const*` and `void*` (v_vnni.hpp:136, 344, 364, 388, 402). The AMX kernel keeps the plane pointer as `const bf16* const v_pairs` (amx_attn.cpp:223). Within the 16-lane V path, `scaled_v_expr` is the only tron-code site that forms vector-typed pointers into the plane. `load_row` forms `__m256i*` pointers into its destination row, not into the plane (`_mm256_store_si256(reinterpret_cast<__m256i*>(vout_ptr + i), ...)` at v_vnni.hpp:395 and 409).
- The casts as conversions. Every `reinterpret_cast` named here is a well-formed conversion ([expr.reinterpret.cast]/7). The 8-lane cast in `copy_storage_slot` feeds only `memcpy`. What falls outside the rules is the arithmetic and the typed accesses after the casts.
- The `std::launder` fix of #4587. It addresses the arena-to-kv_block casts (kv_cache.hpp:1565, 1574, 1614). It cannot cover these three reads. [ptr.launder]/2 requires an object of the target type at the address. No `__m256i`, `__m512i` or `bf16` object exists at the addresses these reads use.
- Correctness as far as tested. The 2026-09-22 delphi-3bda run of the #4557 snapshot 48ab31f7 passed 88 of 89 host tests with 1 skipped, the same as main. The campaign record shows identical generated tokens against main for the 48ab31f7 binary (qwen3-4b, 256 generated tokens): CPU attention at prompt 1024 and 8192 with the settings base, head, head A/A, base with the kill switch and head with the kill switch, every pair identical, and FPGA attention at prompt 1024 and 8192, head equal to base, 4 of 4 specs passed. No test data or bug report examined here shows a wrong result from the three reads.
- Production packages. They are 16-lane. Read 3 is not compiled into them.

## Related

- #4525: the tracking issue for typed KV-cache tensors for packed V and native K. Open.
- #4557: "Typed KV-cache tensors for packed V and native K (parent of #4424)", the base of #4587. Open, head 633cb88896. Its first commit b951ba9b4c changed the 16-lane V storage from vectors to `bf16` and added the two `reinterpret_cast<const bf16s*>` in `scaled_v_expr`.
- #4587: "KV blocks: create them in the DMA allocation, drop construct_kv_blocks (stacked on #4557)". Open draft based on the #4557 branch, head c73e7fb2f9. Carries the comment this issue tracks. Its second commit made `k` a plain `bf16` array.
- #4584: "Own KV cache scalars and derive typed page views". Closed draft, head 9380012de5. The alternative design whose `scaled_v_expr`, `fill_storage_slot` and 8-lane accessor hunks are the precedent for options 1.1, 2.6 and 3.1. Never compiled, per its body.

🤖 Generated with [Claude Code](https://claude.com/claude-code)