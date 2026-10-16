## 4188336250 t/t_llama_unit.cpp:3575
This row makes "a float NaN stores as +inf" a tested contract. AGENTS.md treats NaN as corruption; this pins the path that hides it. The truncation and tie rows likewise pin today's rounding, with no named consumer. Suggest dropping the NaN->inf and rounding rows and keeping the bf16 bit-exact round trip and partner-zero checks.

## 4188336256 t/t_amx_numerics.cpp:227
This is the only check of the packed layout against an independent formula, but it sits after the `available()` early return (line 197), so it silently skips on hosts without AMX. The `at()` section in t_llama_unit doesn't cover it: `at()` and `append_v_row` share `pair_base`, so a wrong formula passes both. Move it above the early return, or into t_llama_unit.

## 4188336267 h/tron/tensor/kv_cache_fwd.hpp:43
`native_k_view` is an alias of the generic row-major `view`, and t_llama_unit asserts it is constructible from `const bf16*`. So any pointer or row-major 64x128 bf16 view passes the QK kernel; "a bare pointer is a compile error" holds for V only. Fine as a first step, but please say so in the description and give K a distinct type in #4424.

## 4188336279 h/system/memory.hpp:192
As this line says, nothing can catch a regression here, and it adds a global `operator new[]` overload in a widely included header. It's a correct reading of [intro.object], but since it came from 39a68994465f3fb753623eec18378544be806862 rather than #4698, it'd be good to get @bgamari-positron's explicit sign-off on the approach.

## 4188336302 t/t_llama_unit.cpp:419
The kernel probes above (bare pointer / other plane's view rejected) are the PR's real contract. Several of these only document structure (test policy): no `operator[]`, no view of a temporary, not default-constructible, `sizeof`/`alignof`. And the three trivial-type checks repeat `static_assert`s that kv_cache.hpp already makes. Suggest keeping the kernel probes and dropping the rest.

## 4188336316 t/t_llama_unit.cpp:3298
This `GENERATE` and the new "token copies keep bits in all four parity combinations" section (line 3664) both run all four `copy_token` parities through `book::append`; the bit-exact one covers more. One parity here already protects the NaN zeroing, so one of these is duplicate coverage.

## 4188336324 t/t_llama_unit.cpp:3293
Nit: the section is still named "append_v preserves poison", but it now asserts that the poison is zeroed.

