## Short version

A comment in `h/tron/models/kv_cache.hpp` at the head of draft PR #4587 names three reads of the KV cache that stay outside the rules of ISO C++. They produce correct values today because clang 19 treats vector loads as if they may alias anything, not because the language guarantees it. This issue records where each read is, which rule it steps outside, why it works today, what would show a break, and the fix options, for the code owner to decide.

## Words used here

| Term | Meaning |
|---|---|
| KV cache, book, page | The store of attention keys (K) and values (V) of past tokens. `book` is the class that owns the storage. `page` is the class with the per-page accessors. A page covers 64 tokens. |
| kv_block | One struct with the K plane (member `k`) and the V plane (member `v`) of one KV head for one page (kv_cache.hpp:2445-2466 at c73e7fb2f9). |
| bf16 | `tron::bf16`, a 2-byte struct that wraps clang's `__bf16` brain-float scalar. |
| bf16s | The SIMD vector alias for one chunk of bf16 values: `__m256i` (32 bytes) in the 16-lane build, `__m128i` (16 bytes) in the 8-lane build. `bf16x32` is `__m512i` (64 bytes). |
| SIMD, AVX2, AVX-512, intrinsic | SIMD: one CPU instruction that works on a whole vector register. AVX2 and AVX-512 are the x86 vector instruction sets with 256-bit and 512-bit registers. An intrinsic is a compiler function such as `_mm512_load_si512` that maps to one such instruction. |
| 16-lane build, 8-lane build | `TRON_CHUNK_SIZE` 16 (AVX-512, the production and CI build) or 8 (AVX2 only). The CMake option `AVX512` selects it (h/tron/simd/auto.hpp:17-21). |
| packed V, v_vnni_tensor | The 16-lane V layout, two tokens interleaved per 32-bit column, owned by the class `v_vnni_tensor`. Its only member is `alignas(64) bf16 data_[Rows * Cols]` (h/tron/tensor/v_vnni.hpp:268). |
| scaled_v_expr | The CPU kernel that forms the weighted sum of the V rows of one page (kv_cache.hpp:2231-2438). `page::scaled_v` builds it. |
| fill_storage_slot | A test-only helper that fills every kv_block of one storage slot with random bf16 values (kv_cache.hpp:1646-1656). |
| 8-lane V accessors | `page::v`, `page::v_ptr`, and the 8-lane branches of `copy_storage_slot` and `page::scaled_v`. They hand out bf16 pointers into the `bf16s` array `v`. |
| ISO C++, N4950 | The C++ standard. N4950 is the C++23 draft. A name in brackets such as [expr.add] is a stable section name, and the number after the slash is a paragraph. |
| undefined behavior (UB) | Behavior the standard places no requirements on. The compiler may assume it never happens. |
| [expr.add]/4 and /6 | Pointer plus integer is defined only inside one array object (/4), and only when the pointer type matches the array's element type (/6). |
| [basic.lval]/11, strict aliasing | An object may be read or written only through an expression of its own type (apart from const and volatile) or of a char type. Compilers assume that differently typed accesses never overlap. |
| TBAA | Type-based alias analysis: the compiler's use of the strict-aliasing rule. LLVM records the access type of every load and store as `!tbaa` metadata. The `omnipotent char` tag marks an access that may overlap anything. |
| UBSan, TySan | clang sanitizers. UBSan (`-fsanitize=undefined`) checks a fixed list of undefined operations. TySan (`-fsanitize=type`) checks strict aliasing and exists only from LLVM 20 on. |
| PR #4557, #4587, #4584 | #4557: typed KV-cache tensors, open, head 633cb88896. #4587: creates the kv_blocks in the DMA allocation, open draft stacked on #4557, head c73e7fb2f9. #4584: an alternative design without kv_block, closed draft, head 9380012de5. |

All file:line references are at c73e7fb2f9 unless another revision is named.

## Where the note comes from

The comment is the last paragraph of Note [KV block lifetime] in kv_cache.hpp at the head of PR #4587 [https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1459-L1462].

```
  // Some reads stay outside ISO C++ and rely on the compiler: scaled_v_expr
  // steps through V with vector pointers, fill_storage_slot walks one bf16
  // pointer across K and V, and the 8-lane V accessors read the bf16s (SIMD
  // vector) array v as bf16 values.
```

The PR body lists six items under "Still outside ISO C++ (unchanged here)". This issue tracks the three that the comment names. The other three are not in this issue:

- the EAGLE `x_data` casts (`page::x<T>`, kv_cache.hpp:2024-2038),
- the intrinsic and AMX tile loads inside the compiler headers,
- the discarded placement-new pattern in `h/tron/scheduler/token_tree.hpp:305-314`.

## The three reads

### 1. scaled_v_expr steps through V with vector pointers

| | |
|---|---|
| Code | The member `const bf16s* const data` (kv_cache.hpp:2233). The 16-lane constructor sets it with `reinterpret_cast<const bf16s*>(v_vnni_access::plane(v_page))` (2326). The loops step `data + i * (head_size / chunk_size)`, cast to `const bf16x32*` and load with `_mm512_load_si512` (2257-2258, 2337-2338, 2352-2353). The 8-lane constructor casts `v_page.data` the same way (2400) and loads with `tron_mm_load_bf16(tile + k)` (2413-2421). Permalink: [L2231-L2438](https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L2231-L2438). |
| Build, callers | Both builds. Production: the CPU attention path calls `page.scaled_v` for every (query, page) pair that the AMX kernel does not take (h/tron/models/self_attention.hpp:1842, 1846). Tests: the t/t_llama_unit.cpp cases "scaled_v", "scaled_v supports wide values" and "scaled_v padding NaN". |
| Storage vs access | 16-lane: the storage is the `bf16` array `data_` of `v_vnni_tensor`. The access steps in `__m256i` units and loads through `__m512i`. 8-lane: the storage is `bf16s v[page_size][head_size / chunk_size]` (2462). The loads match the element type, but the row stride walks across the inner arrays. |
| Rule | 16-lane: [expr.add]/6 (the pointer type is not similar to the element type), [expr.add]/4 (no `__m256i` array exists there), [basic.lval]/11 (a `__m512i` read of `bf16` objects). 8-lane: [expr.add]/4 (arithmetic across the inner arrays of a 2-D array). |
| On main (11b7763c87) | Yes, with the types swapped. main stored `v` as `bf16s` vectors and read them through `__m512i` loads (main:2456, 2275-2277). The first commit of #4557 (b951ba9b4c) made the 16-lane storage `bf16` and added the two casts. The loop text is unchanged. |
| A conforming version | Step with `const bf16*` inside `data_` and pass that pointer to `_mm512_load_si512`, whose parameter is `void const*`. Then no vector-typed pointer is formed in tron code. `_mm_load_si128` (8-lane) takes `__m128i const*`, so one cast per load remains there. |

### 2. fill_storage_slot walks one bf16 pointer across K and V

| | |
|---|---|
| Code | `bf16* data = reinterpret_cast<bf16*>(&block)`, then `data[i] = ...` for every i below `sizeof(block) / sizeof(bf16)` (kv_cache.hpp:1651-1654). Permalink: [L1646-L1656](https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1646-L1656). |
| Build, callers | Both builds. Test only. The one caller is `book::fill_random` (1223-1231, comment "For testing only" at 1218). Tests: t/t_llama_unit.cpp:1148-1149 and :2376. No caller under src/. |
| Storage vs access | The pointer starts at the kv_block, walks `bf16 k[page_size * head_size]` (2448) and continues into `v`: the private `bf16 data_[]` of `v_vnni_tensor` (16-lane) or the `bf16s` array (8-lane). Every access is a `bf16` write. |
| Rule | [expr.add]/4: `data + i` leaves the array `k` once i reaches page_size * head_size. [intro.object]/9: no `bf16` array over the whole block can exist, since it would overlap the kv_block without being nested in it. 8-lane also: `bf16` writes into `__m128i` objects ([basic.lval]/11). |
| On main | Yes, byte-identical text (main:1611-1620). On main every write went into a vector object. At the head (16-lane) every touched element is a `bf16`, and only the walk across two arrays remains. |
| A conforming version | Generate the values into a `std::array<bf16, N>` in storage order and copy the whole block with `std::bit_cast` or `std::memcpy` (the accessor already asserts that kv_block is trivially copyable), or fill `k` and `v` in two loops through their owners. The bytes stay the same. |

### 3. The 8-lane V accessors read the bf16s array v as bf16 values

| | |
|---|---|
| Code | `page::v` builds `view<bf16, ...>` from `reinterpret_cast<bf16*>(kv_block(slot, kv_head).v[i_page])` (kv_cache.hpp:1961, 1969, 1986, 1996). `page::v_ptr` returns that pointer (1972-1977, 1999-2004). `copy_storage_slot` casts two rows and calls `memcpy` (2191, 2194). `page::scaled_v` casts the whole array to `const bf16*` (2518). Permalink: [L1954-L2005](https://github.com/positron-ai/tron/blob/c73e7fb2f99c8f369c809929d1df15bea507cdc3/h/tron/models/kv_cache.hpp#L1954-L2005). |
| Build, callers | 8-lane only. Every site is under the `#else` of `#if TRON_CHUNK_SIZE == 16`. In that build the callers are production code: the V save in h/tron/models/model.hpp:2846-2847, the FPGA staging lambda `v_head_fn` in h/tron/scheduler/full.hpp:2767-2774 (called from src/tron/gof.cpp:213), `page::scaled_v` and `copy_storage_slot`. Tests: t/t_llama_unit.cpp:1163-1164 and :2293. |
| Storage vs access | Storage: a 2-D array of `__m128i` (2462). Access: `bf16` element reads and writes through `view::operator[]`, `std::fill_n` and the staging code, plus `bf16` pointer arithmetic before each vector load in `chunky` (h/tron/kernels/chunky.hpp:49-59). The comment says "read", but the save path also writes. |
| Rule | [basic.lval]/11 (a `bf16` access names a `__m128i` object), [expr.add]/4 and /6 (`bf16` arithmetic over storage that holds no `bf16` array). The `memcpy` site is the least affected, since memcpy is untyped. |
| On main | Yes, same casts (main:1939, 1947, 1964, 1974) and same storage (main:2459). main had the same pattern for `k` in both builds. Commit c73e7fb2f9 removed it for `k` by declaring `bf16 k[page_size * head_size]`. |
| A conforming version | Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch, as c73e7fb2f9 did for `k`. Same bytes, same alignment, same order. The accessors then need no cast. |

State of the 8-lane build:

- Production and CI compile 16 lanes. The CI job uses `--preset native` on runners labeled `avx512` (.github/workflows/cmake-single-platform.yml:151, 353). The nix build passes `-DAVX512=ON` (flake.nix:1208). The `deb` preset inherits the option default `ON` (CMakeLists.txt:44).
- Three routes give an 8-lane tree: the `darwin` preset (`AVX512 OFF`, CMakePresets.json:50-66), the `native` preset on a host that fails the AVX-512 probe (CMakeLists.txt:95-117), or an explicit `-DAVX512=OFF`.
- A syntax-only check of t/t_llama_unit.cpp with 8-lane flags gives 131 errors at c73e7fb2f9, at 633cb88896 and at main. None is in kv_cache.hpp. Most are in kernels/wide.hpp, and 37 are in the test file, 20 of them `no member named 'set_v'` or `'get_v'` in the 8-lane test block at t_llama_unit.cpp:2100-2135. So the 8-lane test binary has not compiled since at least the current main.
- Whether any 8-lane tron binary is linked or run anywhere is not established.

## Why it works today, and what would show a break

Compiler and flags (evidence: CMakeLists.txt:56-57, 609, 621 and the compile commands captured from delphi-3bda):

- clang 19.1.7 from nix, `-std=gnu++23`, `-O3`.
- No `-fstrict-aliasing` or `-fno-strict-aliasing` anywhere in CMakeLists.txt, cmake/, flake.nix, GNUmakefile or CMakePresets.json. So TBAA is on.
- Warnings: `-Wall -Wpedantic -Wextra -Wno-shadow -Wconsumed`. None concerns aliasing.

Mechanism, verified on standalone models of the three patterns with a clang 19.1.7 driver (the `ziglang` 0.14.0 package, the same upstream version as the nix toolchain, a different build) and the product's mirrored headers and flags:

- clang tags every vector-typed load and store with the `omnipotent char` TBAA node. The `bf16` accesses carry `__bf16` or struct-path tags that also end at that node. So LLVM treats every vector access as possibly overlapping every `bf16` access, in both directions. This is what keeps the reads correct.
- A probe confirms that TBAA is active. A vector load, a `bf16` store into the same bytes and a vector reload compile to three instructions, so the reload is kept. The same pattern with `long long` and `float` folds to a constant, so the reload is removed.
- Pointer arithmetic compiles to byte offsets (`getelementptr inbounds` on the allocation, not on a C++ member or sub-array). So no member boundary reaches LLVM.
- The reliance is on an implementation detail, not on a documented guarantee. clang's `CodeGenTBAA.cpp` (release 19.x) has no vector-type branch and falls through to the char node with the comment "For now". clang's `__m128i`, `__m256i` and `__m512i` typedefs carry no `__may_alias__` attribute. GCC's headers do carry it. GCC is not the product compiler and was not tested on this code.
- Not established: that the nix-built clang emits the same TBAA metadata as the driver used here, and the code generation of the real translation units (the local check is syntax-only).

Nothing in the build or the test flow would detect a break today:

- clang emits no diagnostic. The 16-lane model compiled with `-Wall -Wextra -Wpedantic -Wstrict-aliasing=2 -Wcast-align -fsyntax-only` prints nothing. clang's `-Wstrict-aliasing` groups are empty by design (clang 19 DiagnosticGroups.td: "Just silence warnings about -Wstrict-aliasing for now"). `-Wcast-align` covers C-style casts only.
- UBSan has no aliasing check. On the models `-fsanitize=undefined` emits only pointer-overflow, null and alignment checks, which pass for aligned addresses inside one arena. The CMake option `UBSAN` (CMakeLists.txt:42) is used by no preset and no CI job.
- ASan checks address validity only. The ASan target list excludes `t_llama_unit` (GNUmakefile:597-602).
- TySan is the tool for this defect class. clang 19.1.7 rejects `-fsanitize=type`. LLVM 20 adds it as an experimental feature.
- The repository has no `.clang-tidy` file, and no build step runs clang-tidy.

Test evidence:

- The head of PR #4557, 633cb88896, passed the GCP Nix CI run 35942439015 on 2026-09-24 (build, host tests, FPGA tests). The unit tests of c73e7fb2f9 itself on delphi-3bda are listed as not done in the PR #4587 body.
- The 8-lane accessors have not been executed anywhere that this issue can point to.

## Options (the code owner decides)

Read 1, scaled_v_expr:

1. Step with `const bf16*`. Change the member, the two initializers and the three tile expressions, and pass `bf16` pointers to `_mm512_load_si512` (16-lane) or cast once per load (8-lane). Size: est. 25 lines. The byte offsets are identical. On the standalone model the current form and this form compile to the same single load instruction. Risk: a stride error in `bf16` units, which the three `scaled_v` tests would catch. Precedent: PR #4584 wrote this form (9380012de5 kv_cache.hpp:2227-2249, 2385-2408), never compiled per its body. v_vnni.hpp already passes `bf16` pointers to `_mm512_load_si512` in five places (136, 344, 364, 388, 402).
2. Option 1 plus `std::memcpy` of each 64-byte tile into a `__m512i`. On the model this is still one instruction, and the load carries no TBAA tag at all. This removes the dependence on clang's vector TBAA policy.
3. Keep the code and the comment. No tool detects a future regression.

Read 2, fill_storage_slot (test only):

1. Generate a `std::array<bf16, N>` in storage order and assign `block = std::bit_cast<kv_block_t>(buf)`. Same bytes as today. One stack temporary of `sizeof(kv_block)` per block: 32 KiB at head size 128, 128 KiB at head size 512. Precedent: t/t_llama_unit.cpp:2023-2031 already builds random `bf16` values with `std::bit_cast`.
2. The same with `std::memcpy`. Precedent: `copy_storage_slot` copies K rows with `memcpy` (2174-2182).
3. One loop per array, with a new owner operation on `v_vnni_tensor` for its plane. Note [Packed V layout] (v_vnni.hpp:52-58) must then list that operation.
4. Fill through the typed views. This changes the draw-to-element mapping. Neither test depends on the mapping. The `fill_random` comment and the Note [Packed V layout] sentence that names `fill_random` as the exception would need rewording.
5. Keep as is. Test only, so production behavior does not change.

Read 3, the 8-lane V accessors:

1. Declare `alignas(kv_block_alignment) bf16 v[page_size * head_size]` in the 8-lane branch, as c73e7fb2f9 did for `k`. The four accessor groups lose their casts. The `scaled_v_expr` member must change too (read 1, option 1). The 8-lane test block t_llama_unit.cpp:2100-2135, which does not compile today, needs a rewrite. Size: est. 30 lines plus the test block. No effect on the 16-lane build. Risk: the 8-lane tree cannot reach zero errors today, so verification is limited to comparing error sets. Precedent: c73e7fb2f9 for `k`, and #4584 for the 8-lane V (9380012de5:1932, 1939, with no `reinterpret_cast<bf16*>` left in the file).
2. A typed owner for the 8-lane plane in the style of `v_vnni_tensor`, so that both builds declare `v_storage v`. More code for the same result.
3. A partial fix for the FPGA staging path only. The 8-lane `v_head_fn` ignores the 64-byte-aligned `bf16` scratch buffer that `gof::populate` passes (gof.cpp:203, 213, full.hpp:2769). Copying the row into it, as the 16-lane branch does, would make the staging code read only `bf16` objects.
4. Delete the 8-lane V path, or the 8-lane build as a whole. For: no CI job, no makefile route and no shipped package builds it, and its test binary does not compile. Against: the `darwin` preset selects it, v_vnni.hpp:47-50 records the decision to keep the 8-lane classes compiling, and GNUmakefile:987-995 documents compile-only development on laptops without AVX-512.
5. Keep the code and the comment.

## What is not affected

- The 16-lane K path after c73e7fb2f9. `k` is a `bf16` array (2448), and `k_view` builds its views with no cast (2468-2481).
- The 16-lane V plane reads in v_vnni.hpp and the AMX kernel. They pass `bf16` pointers to the intrinsics (v_vnni.hpp:136, 344, 364, 388, 402 and src/tron/kernels/amx_attn.cpp:223). `scaled_v_expr` is the only tron-code site that forms vector-typed pointers into the plane.
- The `std::launder` calls of #4587 (kv_cache.hpp:1565, 1574, 1614). They address the arena-to-kv_block casts. They cannot cover these reads. [ptr.launder]/2 needs an object of the target type at the address, and no `__m256i`, `__m512i` or `bf16` object exists where these reads look.
- Correctness as far as tested. No test result or bug report examined here shows a wrong value from any of the three reads.
- Production packages. They are 16-lane. Read 3 is not compiled into them.

Note on "inside ISO C++": `bf16` wraps clang's `__bf16`, which is a compiler extension type. The phrase here means that the pointer arithmetic and the access types follow the rules of N4950. The intrinsics' own dereferences stay compiler extensions in every option.

## Related

- #4525: typed KV-cache tensors for packed V and native K (the parent tracking issue).
- #4557: the typed-tensor PR, base of #4587. Its first commit b951ba9b4c changed the 16-lane V storage from vectors to `bf16` and added the two `reinterpret_cast<const bf16s*>` in `scaled_v_expr`.
- #4587: the PR whose Note carries the comment. Its second commit made `k` a plain `bf16` array.
- #4584: the closed alternative design whose `scaled_v_expr` and 8-lane hunks are the precedent for options 1.1 and 3.1 above. Never compiled, per its body.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
