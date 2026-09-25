## Short version

Three reads of the KV cache in `h/tron/models/kv_cache.hpp` break the rules of ISO C++: `scaled_v_expr`, `fill_storage_slot` and the 8-lane V accessors. They give correct values today through two clang 19 compilation choices (vector accesses tagged as possibly overlapping anything, and pointer arithmetic compiled to byte offsets), not through a language guarantee. This issue is the record of where each read is, which rule it breaks, why it works today, what would show a break, and the fix options, for the code owner to decide.

## Words used here

| Term | Meaning |
|---|---|
| KV cache, book, page | The store of attention keys (K) and values (V) of past tokens. `book` is the class that owns the storage. `page` is the class with the per-page accessors. A page covers 64 tokens. |
| slot, storage slot | One persistent K/V storage region of the book. A `kv_slot_spec` (kv_cache.hpp:154-160) describes it: a `kv_geometry` (the number of KV heads and the head_size, kv_cache.hpp:105-108) plus a `kv_slot_retention` (whether the slot keeps the full history or a sliding window of tokens). A storage slot is that region at one storage offset. |
| page_size, head_size, chunk_size, KV head | page_size is the number of tokens per page (64). head_size is the number of bf16 values per token in one attention head (`kv_geometry`, kv_cache.hpp:105-108). chunk_size is `TRON_CHUNK_SIZE`, the number of 32-bit lanes in one SIMD chunk (16 or 8). A KV head is one key/value head of grouped-query attention, shared by several query heads. |
| kv_block, kv_block_t, kv_block_alignment | `kv_block` is one struct with the K plane (member `k`) and the V plane (member `v`) of one KV head for one page (kv_cache.hpp:2445-2466). `kv_block_t` is the kv_block type of one `kv_geometry` (1553, 1592). `kv_block_alignment` is 64 bytes (2440). |
| K plane, V plane, native K, packed V | The K plane and the V plane are the K half and the V half of one kv_block. Native K is the K plane stored as plain bf16 values in their original order. Packed V is the 16-lane V layout, two tokens interleaved per 32-bit column. |
| v_vnni_tensor, v_storage | `v_vnni_tensor` is the typed owner of one packed V plane in the 16-lane build. Its only member is `alignas(V_PLANE_ALIGNMENT_64) bf16 data_[Rows * Cols]`, and `V_PLANE_ALIGNMENT_64` is 64 (h/tron/tensor/v_vnni.hpp:268, constant at 79). `v_storage` is the alias for it inside kv_block (kv_cache.hpp:2454). |
| view, k_view | `tron::view` is the strided tensor view template (h/tron/tensor/view.hpp:16-25): a data pointer plus extents and strides. `view::operator[]` returns the element at `data + i * stride`. `k_view` is the kv_block member function that returns such a view of the K plane (kv_cache.hpp:2468-2479). |
| bf16 | `tron::bf16`, a 2-byte struct that wraps clang's `__bf16` brain-float scalar. |
| bf16s, tron_mm_load_bf16 | `bf16s` is the SIMD vector alias for one chunk of bf16 values: `__m256i` (32 bytes) in the 16-lane build, `__m128i` (16 bytes) in the 8-lane build. `bf16x32` is `__m512i` (64 bytes). `tron_mm_load_bf16` is the macro for the aligned load of one bf16s chunk: `_mm_load_si128` in the 8-lane build (h/tron/simd/auto.hpp:40), `_mm256_load_si256` in the 16-lane build (auto.hpp:69). |
| SIMD, AVX2, AVX-512, AMX, intrinsic | SIMD: one CPU instruction that works on a whole vector register. AVX2 and AVX-512 are the x86 vector instruction sets with 256-bit and 512-bit registers. AMX is the Intel tile-matrix instruction set used by the attention kernel in src/tron/kernels/amx_attn.cpp. An intrinsic is a compiler function such as `_mm512_load_si512` that maps to one such instruction. |
| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (AVX-512, the production and CI build) or 8 (AVX2 only). The CMake option `AVX512` defines the macro `TRON_AVX512_ENABLED` (src/tron/CMakeLists.txt:269-272), and h/tron/simd/auto.hpp:17-21 picks 16 lanes when that macro is defined. |
| scaled_v_expr, tile | `scaled_v_expr` is the CPU kernel that forms the weighted sum of the V rows of one page (kv_cache.hpp:2231-2438). `page::scaled_v` builds it. A tile here is the loop variable `tile` in that kernel (not an AMX register): a pointer to one 64-byte block of a V row in the three 16-lane loops (`const bf16x32*`, kv_cache.hpp:2257, 2337, 2352) and to one 16-byte block in the 8-lane loop (`const bf16s*`, 2413). |
| fill_storage_slot | A test-only helper that fills every kv_block of one storage slot with random bf16 values (kv_cache.hpp:1646-1656). |
| 8-lane V accessors, copy_storage_slot | `page::v`, `page::v_ptr`, and the 8-lane branches of `copy_storage_slot` and `page::scaled_v`. They return bf16 pointers into the `bf16s` array `v`. `copy_storage_slot` is the page function that copies the K and V rows of `count` tokens of one storage slot from a source page (kv_cache.hpp:2167-2197). |
| chunky | The per-element-type SIMD chunk helper (h/tron/kernels/chunky.hpp:15). `chunky<bf16, true>` loads or stores one aligned bf16s chunk at a bf16 pointer (chunky.hpp:49-59). |
| DMA arena | DMA: direct memory access, memory that a hardware device can read without the CPU copying it. The DMA arena is the byte array (`unique_dma<uint8_t[]>`) that holds the kv_blocks of every retained slot. A reclaimable chunk is a smaller such array that holds some pages of a reclaimable slot (kv_cache.hpp:1424-1435, Note [KV block lifetime] at 1448-1450). |
| Note [Title] | The codebase writes design notes as block comments headed `Note [Title]`. Note [KV block lifetime] (kv_cache.hpp) and Note [Packed V layout] (h/tron/tensor/v_vnni.hpp) are two of them. |
| FPGA, hardware attention, staging, GOF | FPGA: the programmable accelerator card that can compute attention (hardware attention) in place of the CPU. Staging is the copy of K and V rows into the layout the FPGA reads. GOF: group of four, the 4-token unit of KV data staged for the FPGA (h/tron/gof.hpp:3-5). `gof::populate` copies K and V rows into it. |
| EAGLE, x_data | EAGLE is a speculative-decoding scheme: a small draft model proposes tokens and shares the KV cache with the main model. `x_data` is the book's storage for the EAGLE embeddings, kept beside each KV page (kv_cache.hpp:1328). |
| clang, LLVM | clang is the C++ compiler that builds the product, version 19.1.7. It is built on LLVM, the compiler framework that turns clang's internal program form (the IR) into machine code. |
| nix, delphi-3bda | nix is the package manager that supplies the compiler and the libraries of the product build (flake.nix). delphi-3bda is the Intel test host that builds and runs the product with the nix clang toolchain. |
| CI, runner, GCP Nix run, host tests | CI: continuous integration, the automated GitHub build-and-test jobs of the repository. A runner is the machine that executes one CI job. The GCP (Google Cloud Platform) Nix run is the CI workflow that builds with nix and runs the tests. Host tests are the test binaries that run on the build host without an FPGA. |
| CMake, preset, tree | CMake is the build configuration tool. A preset is a named set of CMake options in CMakePresets.json: `native` (the build for the host CPU), `darwin` (the macOS x86_64 cross-compile) and `deb` (the Debian package build). A tree is one configured build directory. |
| ISO C++, N4950 | The C++ standard. N4950 is the C++23 draft. A name in brackets such as [expr.add] is a stable section name, and the number after the slash is a paragraph. |
| undefined behavior (UB) | Behavior the standard places no requirements on. The compiler may assume it never happens. |
| [expr.add]/4 and /6, similar | Pointer plus integer is defined only inside one array object (/4), and only when the pointer type is similar to the array's element type (/6). Similar means the same type apart from const and volatile ([conv.qual]/2). |
| [basic.lval]/11, strict aliasing | An object may be read or written only through an expression of a similar type or of a char type. Compilers assume that differently typed accesses never overlap. |
| [intro.object]/9, nested | Two objects may share bytes only when one is nested in the other. Nested is the standard's term for an object placed inside another object's storage ([intro.object]/4). |
| trivially copyable | A type whose bytes may be copied with memcpy to make a valid copy ([basic.types.general]/2-3). |
| std::launder | A library function that returns a pointer to an object that already lives at an address. It creates no object ([ptr.launder]/2). |
| TBAA, struct-path tag, omnipotent char | TBAA: type-based alias analysis, the compiler's use of the strict-aliasing rule. LLVM records the access type of every load and store as `!tbaa` metadata. A struct-path tag records the member path inside a struct. The `omnipotent char` tag marks an access that may overlap anything. |
| __may_alias__, GCC | `__may_alias__` is the GNU type attribute that tells the compiler a type may overlap objects of any other type. GCC is the GNU C++ compiler. It is not the product compiler. |
| UBSan, ASan, TySan, clang-tidy | clang tools. UBSan (`-fsanitize=undefined`) checks a fixed list of undefined operations at run time. ASan (AddressSanitizer) checks address validity. TySan (`-fsanitize=type`) checks strict aliasing and exists only from LLVM 20 on. clang-tidy is clang's static checker, configured by a `.clang-tidy` file. |
| standalone model, syntax-only check | A standalone model is a small C++ program that copies the pointer and load pattern of one tron read (not an ML model). A syntax-only check is a compile with `-fsyntax-only`: it checks types and template instantiation and generates no code. |
| hunk | One changed region of a diff. |
| tron | The inference program under test. Its source is the positron-ai/tron repository. "The product" in this issue means tron. |
| PR (pull request) #4557, #4587, #4584 | #4557: typed KV-cache tensors, open, head 633cb88896. #4587: creates the kv_blocks in the DMA allocation, open draft whose base branch is the #4557 branch, head c73e7fb2f9. #4584: an alternative design without kv_block, closed draft, head 9380012de5. |

All file:line references are at c73e7fb2f9 unless another revision is named.

## Where this list comes from

A code comment named these three reads. It was the last paragraph of Note [KV block lifetime] in kv_cache.hpp at commit c73e7fb2f9 of PR #4587 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1459-L1462]. The PR author is removing that paragraph from the code (2026-09-24). This issue replaces it as the record of the three reads. The removed text was:

```
  // Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr
  // steps through V with vector pointers, fill_storage_slot walks one bf16
  // pointer across K and V, and the 8-lane V accessors read the bf16s (SIMD
  // vector) array v as bf16 values.
```

The PR body lists six items under "Still outside ISO C++ (unchanged here)" (as of 2026-09-24). This issue tracks the three that the removed comment named. The other three are not in this issue:

- the EAGLE `x_data` casts in `page::x<T>` (the page accessor that returns one token's x_data bytes as `T*`, kv_cache.hpp:2024-2038),
- the intrinsic and AMX tile loads inside the compiler headers,
- the placement-new pattern whose result pointer is discarded (the code keeps using the pointer from an earlier cast instead) in `h/tron/scheduler/token_tree.hpp:305-314`.

## The three reads

### 1. scaled_v_expr steps through V with vector pointers

The code of this read is kv_cache.hpp:2231-2438 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L2231-L2438].

| | |
|---|---|
| Code | The member `const bf16s* const data` (kv_cache.hpp:2233). The 16-lane constructor sets it with `reinterpret_cast<const bf16s*>(v_vnni_access::plane(v_page))` (2326). `v_page` is the packed-V view passed into the constructor, and `plane` returns its raw `bf16*` (v_vnni.hpp:272-278). The loops step `data + i * (head_size / chunk_size)` and cast to `const bf16x32*` (2257-2258, 2337-2338, 2352-2353), then load with `_mm512_load_si512(tile + k)` (2260-2275, 2339-2342, 2354-2361). The 8-lane constructor casts `v_page.data` the same way (2400) and loads with `tron_mm_load_bf16(tile + k)` (2413-2421). |
| Build, callers | Both builds. Production: the CPU attention path calls `page.scaled_v` for every (query, page) pair that the AMX kernel does not take (h/tron/models/self_attention.hpp:1842, 1846). Tests: the t/t_llama_unit.cpp cases "scaled_v", "scaled_v supports wide values" and "scaled_v padding NaN". |
| Storage vs access | 16-lane: the storage is the `bf16` array `data_` of `v_vnni_tensor`. The access steps in `__m256i` units and loads through `__m512i`. 8-lane: the storage is `bf16s v[page_size][head_size / chunk_size]` (2462). The loads match the element type, but the row stride crosses the inner arrays. |
| Rule | 16-lane: [expr.add]/6 (the pointer type `__m256i` is not similar to the element type `bf16`), [expr.add]/4 (no `__m256i` array exists there), [basic.lval]/11 (a `__m512i` read of `bf16` objects). 8-lane: [expr.add]/4 (arithmetic across the inner arrays of a 2-D array). |
| On main (11b7763c87) | Yes, with the types swapped. main stored `v` as `bf16s` vectors and read them through `__m512i` loads (main:2456, 2275-2277). The first commit of #4557 (b951ba9b4c) made the 16-lane storage `bf16` and added the two casts. The loop text is unchanged. |
| A conforming version | Step with `const bf16*` inside `data_`. Pass that pointer to `_mm512_load_si512`. Its parameter type is `void const*`. Then no vector-typed pointer is formed in tron code. `_mm_load_si128` (8-lane) takes `__m128i const*`. So one cast per load remains there. |

### 2. fill_storage_slot walks one bf16 pointer across K and V

The code of this read is kv_cache.hpp:1646-1656 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1646-L1656].

| | |
|---|---|
| Code | `bf16* data = reinterpret_cast<bf16*>(&block)`, then `data[i] = ...` for every i below `sizeof(block) / sizeof(bf16)` (kv_cache.hpp:1651-1654). |
| Build, callers | Both builds. Test only. The one caller is `book::fill_random` (1223-1231, comment "For testing only" at 1218). Tests: t/t_llama_unit.cpp:1148-1149 and :2376. No caller under src/. |
| Storage vs access | The pointer starts at the kv_block, steps through `bf16 k[page_size * head_size]` (2448) and continues into `v`: the private `bf16 data_[]` of `v_vnni_tensor` (16-lane) or the `bf16s` array (8-lane). Every access is a `bf16` write. |
| Rule | [expr.add]/4: `data + i` leaves the array `k` once i reaches page_size * head_size. [intro.object]/9: no `bf16` array over the whole block can exist. Such an array would overlap the kv_block without being nested in it. 8-lane also: `bf16` writes into `__m128i` objects ([basic.lval]/11). |
| On main | Yes, byte-identical text (main:1610-1620). On main every write went into a vector object. At the head (16-lane) every touched element is a `bf16`, and only the pointer stepping across two arrays remains. |
| A conforming version | Generate the values into a `std::array<bf16, N>` in storage order and copy the whole block with `std::bit_cast` or `std::memcpy`. The block accessor `book::kv_block_at_storage` already asserts that kv_block is trivially copyable (1597-1600). Or fill `k` and `v` in two loops through their owners. The bytes stay the same. |

### 3. The 8-lane V accessors read the bf16s array v as bf16 values

The code of this read is kv_cache.hpp:1954-2005 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1954-L2005].

| | |
|---|---|
| Code | `page::v` builds `view<bf16, ...>` from `reinterpret_cast<bf16*>(kv_block(slot, kv_head).v[i_page])` (kv_cache.hpp:1961, 1969, 1986, 1996). `page::v_ptr` returns that pointer (1972-1977, 1999-2004). `copy_storage_slot` casts two rows and calls `memcpy` (2191, 2194). `page::scaled_v` casts the whole array to `const bf16*` (2518). |
| Build, callers | 8-lane only. Every site is under the `#else` of `#if TRON_CHUNK_SIZE == 16`. In that build the callers are production code: the V save in h/tron/models/model.hpp:2846-2847, the FPGA staging lambda `v_head_fn` in h/tron/scheduler/full.hpp:2767-2774 (called from `gof::populate`, src/tron/gof.cpp:213), `page::scaled_v` and `copy_storage_slot`. Tests: t/t_llama_unit.cpp:1163-1164 and :2293. |
| Storage vs access | Storage: a 2-D array of `__m128i` (2462). Access: `bf16` element reads and writes through `view::operator[]`, `std::fill_n` and the staging code, plus `bf16` pointer arithmetic before each vector load in `chunky` (chunky.hpp:49-59). The removed comment said "read", but the save path also writes. |
| Rule | [basic.lval]/11 (a `bf16` access names a `__m128i` object), [expr.add]/4 and /6 (`bf16` arithmetic over storage that holds no `bf16` array). The `memcpy` site is the least affected. memcpy performs no typed access. |
| On main | Yes, same casts (main:1939, 1947, 1964, 1974) and same storage (main:2459). main had the same pattern for `k` in both builds. Commit c73e7fb2f9 removed it for `k` by declaring `bf16 k[page_size * head_size]`. |
| A conforming version | Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch, as c73e7fb2f9 did for `k`. Same bytes, same alignment, same order. The accessors then need no cast. |

State of the 8-lane build:

- Production and CI compile 16 lanes. The CI job uses `--preset native` on runners labeled `avx512` (.github/workflows/cmake-single-platform.yml:151, 353). The nix build passes `-DAVX512=ON` (flake.nix:1208). The `deb` preset inherits the option default `ON` (CMakeLists.txt:44).
- Three routes give an 8-lane tree: the `darwin` preset (`AVX512 OFF`, CMakePresets.json:50-66), the `native` preset on a host that fails the AVX-512 probe (CMakeLists.txt:95-117), or an explicit `-DAVX512=OFF`. On macOS, `make` selects the `darwin` preset (GNUmakefile:219-220). On Linux, `make` selects `native` or `cross-avx512` (the preset that cross-compiles for AVX-512 on a host without AVX-512, CMakePresets.json:41-47), both 16-lane (GNUmakefile:227-231).
- A syntax-only check of t/t_llama_unit.cpp with 8-lane flags gives 131 errors at c73e7fb2f9, at 633cb88896 and at e6c53ba70a.
  - e6c53ba70a is an ancestor of main. Its kv_cache.hpp, its t_llama_unit.cpp and every header that carries an error are identical to the same files at origin/main 11b7763c87.
  - None of the errors is in kv_cache.hpp. The largest group, 58 of the 131, is in kernels/wide.hpp.
  - 37 are in the test file. 20 of those 37 are `no member named 'set_v'` or `'get_v'` at unguarded calls of these 16-lane-only page members. 2 are inside the 8-lane test block t_llama_unit.cpp:2100-2135 (a `bf16` to `bf16s` conversion at 2113).
  - So the 8-lane test binary did not compile at e6c53ba70a, and the same files are on main today.
- Whether any 8-lane tron binary is linked or run anywhere is not established.

## Why it works today, and what would show a break

Compiler and flags:

- clang 19.1.7 from nix, `-std=gnu++23` (C++23 with GNU extensions), `-O3` (the highest standard optimization level) [CMakeLists.txt:56-57 and the compile commands captured from delphi-3bda].
- No `-fstrict-aliasing` or `-fno-strict-aliasing` anywhere in CMakeLists.txt, cmake/, flake.nix, GNUmakefile or CMakePresets.json. So TBAA is on.
- Warnings: `-Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed`. None concerns aliasing [CMakeLists.txt:609, 621].

Mechanism, verified on standalone models of the three patterns. The compiler was a clang 19.1.7 driver (the `clang` command-line executable that runs the compilation) from the `ziglang` 0.14.0 Python package. That package bundles the same upstream clang version as the nix toolchain in a different build. The headers and flags were the product's, copied from delphi-3bda.

- clang tags every vector-typed load and store with the `omnipotent char` TBAA node. The `bf16` accesses carry `__bf16` or struct-path tags that also end at that node. So LLVM treats every vector access as possibly overlapping every `bf16` access, in both directions. This is the main part of what keeps reads 1 and 3 correct.
- Pointer arithmetic compiles to byte offsets (`getelementptr inbounds`, LLVM's address-computation instruction, applied to the whole allocation and not to a C++ member or sub-array). So no member boundary reaches LLVM. This is the other part, and for read 2 at 16 lanes (only `bf16` writes, no vector access) it is the whole reason.
- A probe confirms that TBAA is active. A vector load, a `bf16` store into the same bytes and a vector reload compile to three instructions. So the reload is kept. The same pattern with `long long` and `float` is computed at compile time into one constant. So the reload is removed.
- The reliance is on an implementation detail, not on a documented guarantee. clang's `CodeGenTBAA.cpp` (the clang source file that assigns TBAA tags, release 19.x) has no vector-type branch. Vector types therefore reach the default case. That case returns the `omnipotent char` node under the comment "For now". clang's `__m128i`, `__m256i` and `__m512i` typedefs carry no `__may_alias__` attribute. GCC's headers do carry it. GCC was not tested on this code.
- Not established: that the nix-built clang emits the same TBAA metadata as the driver used here, and the code generation of the real translation units (the local check is syntax-only).

Nothing in the build or the test flow would detect a break today:

- clang emits no diagnostic. The 16-lane model compiled with `-Wall -Wextra -Wpedantic -Wstrict-aliasing=2 -Wcast-align -fsyntax-only` prints nothing. clang's `-Wstrict-aliasing` groups are empty by design (clang 19 DiagnosticGroups.td: "Just silence warnings about -Wstrict-aliasing for now"). `-Wcast-align` covers C-style casts only.
- UBSan has no aliasing check. On the models `-fsanitize=undefined` emits only pointer-overflow, null and alignment checks. Those checks pass for aligned addresses inside one arena. The CMake option `UBSAN` (CMakeLists.txt:42) is used by no preset and no CI job.
- ASan checks address validity only. The ASan target list excludes `t_llama_unit` (GNUmakefile:597-602).
- TySan is the tool for this defect class. clang 19.1.7 rejects `-fsanitize=type`. LLVM 20 adds it as an experimental feature.
- The repository has no `.clang-tidy` file, and no build step runs clang-tidy.

Test evidence:

- The head of PR #4557, 633cb88896, passed the GCP Nix CI run with GitHub Actions id 35942439015 on 2026-09-24. That run covers the build, the host tests and the FPGA tests. The unit tests of c73e7fb2f9 itself on delphi-3bda are listed as not done in the PR #4587 body.
- The 8-lane accessors have not been executed anywhere that this issue can point to.

## Options (the code owner decides)

Read 1, scaled_v_expr:

1. Step with `const bf16*`.
   - Change: the member, the two initializers and the four tile expressions (2257, 2337, 2352 and 2413). Pass `bf16` pointers to `_mm512_load_si512` (16-lane) or cast once per load (8-lane).
   - Size: est. 25 lines. The byte offsets are identical. On the standalone model the current form and this form compile to the same single load instruction.
   - Risk: a stride error in `bf16` units. The three `scaled_v` tests would catch it.
   - Precedent: PR #4584 wrote this form (9380012de5 kv_cache.hpp:2227-2249, 2385-2408). That PR was never compiled, per its body. v_vnni.hpp already passes `bf16` pointers to `_mm512_load_si512` in eleven places (136, 344, 364, 388, 402, 434, 441, 442, 453, 460, 461).
2. Option 1 plus `std::memcpy` of each 64-byte tile into a `__m512i`. On the model this is still one instruction, and the load carries no TBAA tag at all. This removes the dependence on clang's vector TBAA policy.
3. Keep the code as is, with this issue as the record. No tool detects a future regression.

Read 2, fill_storage_slot (test only):

1. Generate a `std::array<bf16, N>` in storage order and assign `block = std::bit_cast<kv_block_t>(buf)`.
   - Change: same bytes as today.
   - Size: one stack temporary of `sizeof(kv_block)` per block, 32 KiB at head size 128 and 128 KiB at head size 512. 128 KiB is 1.6 % of the 8 MiB default Linux main-thread stack (`ulimit -s` = 8192 KiB on the Linux host that compiled the standalone models, not measured on delphi-3bda).
   - Precedent: t/t_llama_unit.cpp:2023-2031 already builds random `bf16` values with `std::bit_cast`.
2. The same with `std::memcpy`. Precedent: `copy_storage_slot` copies K rows with `memcpy` (2174-2182).
3. One loop per array, with a new owner operation on `v_vnni_tensor` for its plane. Note [Packed V layout] (v_vnni.hpp:52-58) must then list that operation.
4. Fill through the typed views. This changes which random draw lands in which element. Neither test depends on that mapping. Two texts would then need rewording. One is the `fill_random` comment. The other is the Note [Packed V layout] sentence that names `fill_random` as the one caller allowed to write the plane bytes without the typed operations.
5. Keep as is. The code is test only. Production behavior does not change.

Read 3, the 8-lane V accessors:

1. Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch, as c73e7fb2f9 did for `k`.
   - Change: the four accessor groups lose their casts. The `scaled_v_expr` member must change too (read 1, option 1). The 8-lane test block t_llama_unit.cpp:2100-2135 does not compile today. It needs a rewrite too.
   - Size: est. 30 lines plus the test block. No effect on the 16-lane build.
   - Risk: the 8-lane tree cannot reach zero errors today. So verification is limited to comparing error sets.
   - Precedent: c73e7fb2f9 for `k`, and #4584 for the 8-lane V (9380012de5:1932, 1939, with no `reinterpret_cast<bf16*>` left in the file).
2. A typed owner for the 8-lane plane in the style of `v_vnni_tensor`. Both builds then declare `v_storage v`. More code for the same result.
3. A partial fix for the FPGA staging path only. The 8-lane `v_head_fn` ignores the 64-byte-aligned `bf16` scratch buffer that `gof::populate` passes (gof.cpp:203, 213, full.hpp:2769). Copying the row into it, as the 16-lane branch does, would make the staging code read only `bf16` objects.
4. Delete the 8-lane V path, or the 8-lane build as a whole.
   - For: no CI job, no Linux makefile route and no shipped package builds it. Its test binary does not compile.
   - Against: the `darwin` preset selects it, and `make` picks that preset on macOS. v_vnni.hpp:47-50 records the decision to keep the 8-lane classes compiling. GNUmakefile:987-995 documents compile-only development on laptops without AVX-512.
5. Keep the code as is, with this issue as the record.

## What is not affected

- The 16-lane K path after c73e7fb2f9. `k` is a `bf16` array (2448), and `k_view` builds its views with no cast (2468-2479).
- The 16-lane V plane reads in v_vnni.hpp and the AMX kernel. They pass `bf16` pointers to the intrinsics (the eleven v_vnni.hpp lines listed under read 1, option 1, and src/tron/kernels/amx_attn.cpp:223). `scaled_v_expr` is the only tron-code site that forms vector-typed pointers into the plane.
- The `std::launder` calls of #4587 (kv_cache.hpp:1565, 1574, 1614). They address the arena-to-kv_block casts. They cannot cover these reads. [ptr.launder]/2 needs an object of the target type at the address, and no `__m256i`, `__m512i` or `bf16` object exists where these reads look.
- Correctness as far as tested. No test result or bug report examined here shows a wrong value from any of the three reads.
- Production packages. They are 16-lane. Read 3 is not compiled into them.

Note on "inside ISO C++": `bf16` wraps clang's `__bf16`. `__bf16` is a compiler extension type. The phrase here means that the pointer arithmetic and the access types follow the rules of N4950. The intrinsics' own dereferences stay compiler extensions in every option.

## Related

- #4525: typed KV-cache tensors for packed V and native K, the parent tracking issue.
- #4557: the typed-tensor PR, base of #4587. Its first commit b951ba9b4c changed the 16-lane V storage from vectors to `bf16` and added the two `reinterpret_cast<const bf16s*>` in `scaled_v_expr`.
- #4587: the PR whose Note carried the comment at c73e7fb2f9. Its second commit made `k` a plain `bf16` array.
- #4584: the closed alternative design whose `scaled_v_expr` and 8-lane hunks are the precedent for options 1.1 and 3.1 above. Never compiled, per its body.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
