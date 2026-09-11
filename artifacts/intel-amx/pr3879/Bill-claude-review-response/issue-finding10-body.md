## What this tracks

PR #3879 adds the AMX software-attention path behind the CMake option `TRON_AMX_DISPATCH`. At the PR head 47f6f2dceb, `h/tron/models/self_attention.hpp` holds six `#ifdef TRON_AMX_DISPATCH` blocks plus one `#error` guard (225 lines of an 1,827-line file):

| Block | Lines | What it holds |
|---|---|---|
| guard | :29-35 | `#error` when `TRON_CHUNK_SIZE != 16` (the pair-interleaved V layout the PV kernel reads exists only then) |
| 1 | :277-285 | the 4096-byte slot type for one packed query group |
| 2 | :299-308 | the per-worker slot vector inside `attn_accum` |
| 3 | :1320-1355 | set-up at the top of `apply_page_range`: compile-time and run-time gates, slot sizing, `begin_region()`, the scope guard that releases the tile configuration |
| 4 | :1390-1397 | inside the page and token loops: pack a token's query heads on its first page |
| 5 | :1421-1551 | the three helpers `packed_amx_query`, `is_dense_amx_page`, `apply_dense_amx_page` |
| 6 | :1598-1621 | in `apply_page_tok`: if the pair has a packed Q and a dense page, run the dense function and return; else fall through to the AVX-512 dotter loop |

An architecture review of the pre-split head (2026-09-05) asked for "one call and no preprocessor" in the attention loop. The single-call half is done: the dense-page path is one function called from one place (commit 69031c201d), the pack is one helper, and the region bracket is a scope guard (commit 4290402491). The preprocessor half is this issue.

## Why it matters

- One file, two shapes. A default build (option OFF, what a developer builds locally) compiles `apply_page_range`, `apply_page_tok` and `attn_accum` without these blocks; the CI lane (`-DTRON_AMX_DISPATCH=ON`, `.github/workflows/cmake-single-platform.yml`) compiles them with. A rename made in the OFF shape can break the ON shape without the author seeing it until CI runs.
- Reading the two in-loop sites means holding three conditions at once: the preprocessor condition, the per-geometry `if constexpr`, and the per-process `amx_on`.

## Why it is a design step, not an edit

- The statements (blocks 3, 4, 6) can move behind `if constexpr` on a constexpr flag exported by `h/tron/kernels/amx_attn_iface.hpp` that is true only when the kernel translation unit is compiled. Both functions are member templates, so the discarded branch is not instantiated and the OFF build references no kernel symbol. One trap: `amx_on = amx_eligible && available()` must sit inside the discarded branch, not behind `&&`, or an unoptimised OFF build still needs `available()`.
- Block 5 could lose its guard too: member functions of a class template are compiled only when something calls them (to be verified by a build).
- Blocks 1 and 2 are declarations, which `if constexpr` cannot remove. Options: (a) an unconditional member, at the cost of an unused 24-byte `std::vector` with a destructor in every `attn_accum` of the OFF build; (b) a build-dependent type alias; (c) a backend type: a struct whose static members are the kernel entry points, passed as a defaulted template parameter of `apply_page_range` (second position, before the deduced query-buffer type) and threaded through `packed_amx_query`, `apply_page_tok` and `apply_dense_amx_page`. Option (c) also lets `t/t_amx_dispatch_dtype.cpp` pass a fake type instead of redefining the six entry points in its own translation unit, and gives `available()` a home to move to if the CPU probe ever leaves the kernel TU.
- The `#error` guard stays until a `static_assert` on the V byte layout at the call site replaces it (separate item).

## Done when

- `grep -c '#ifdef TRON_AMX_DISPATCH' h/tron/models/self_attention.hpp` is 0 (the `#error` guard may remain until its replacement lands).
- The OFF build links without the kernel translation unit at `-O0` and `-O2`.
- The ON build passes `t_amx_numerics` on a Granite Rapids host (both kernel cases executing), `t_amx_dispatch_dtype` and `t_llama_unit`.
- No hot-path change: the disassembly of `apply_page_range` is unchanged, or a same-binary A/B decode run is within run-to-run noise.

## Related

- #3879 (the PR), #3997 (CI execution on an AMX host), #4338 (environment-variable document).
