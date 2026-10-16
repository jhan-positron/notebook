Style-only follow-up to #4557, into its branch, so the change can be read on its own.

**Words used here.** Value-suffixed name: a constant whose name ends in its value, such as `V_PAIR_TOKENS_2`. Shared file: a file that code outside the AMX (Intel Advanced Matrix Extensions) kernels also owns or reads. AMX kernel files: `src/tron/kernels/amx_attn.cpp` and `h/tron/kernels/amx_attn_iface.hpp`.

## What this PR does

Wade's comment on #4557 (https://github.com/positron-ai/tron/pull/4557#issuecomment-6021333114) accepts value-suffixed names in the AMX kernel files and asks that shared code keep the idiom of the surrounding file. This PR removes the 24 value-suffixed names #4557 added to its three shared files and spells each value the way the surrounding file does.

| File | Names removed | Spelling now |
|---|---|---|
| `h/tron/tensor/v_vnni.hpp` | 6 | the moved set_v / get_v / append bodies read as they do in `kv_cache.hpp`: `% 2`, `i * 2`, shift `16`, `alignas(64)`, `const __m512i hi_16_of_32 = _mm512_set1_epi32(0xffff0000);` |
| `t/t_llama_unit.cpp` | 16 | lower-case `constexpr` names in the two new test cases (`head_size`, `pattern_base`, `specials_even_token`, ...); the poison case returns to the literal `3`, `4` and `7` of main |
| `t/t_heap_v2.cpp` | 2 | `(1024, std::align_val_t{64})`, the same as the two sibling calls in that test |

The AMX kernel keeps `V_PAIR_TOKENS_2`. Its definition moves from the header into `amx_attn.cpp`, next to the other file-scope constants there, so the header carries no value-suffixed name.

## Verification (delphi-3bda, 2026-10-06)

Measured at commit 425a0e8239. The current head d9e7645fee differs from it only by `/* bf16 */` comments on the seven shift-by-16 lines (review round 1), which do not change object code.

Build: clang 19, RelWithDebInfo, AVX512 and TRON_AMX_DISPATCH on, models off. The disassembly of `libtron.a` is byte-identical before and after this change (`objdump -d`, 120126 lines). The four test binaries pass:

| Test binary | Result |
|---|---|
| t_llama_unit | All tests passed (249115 assertions in 62 test cases) |
| t_amx_numerics | All tests passed (4109 assertions in 4 test cases), real AMX, no "AMX unavailable" warning |
| t_heap_v2 | All tests passed (8242 assertions in 45 test cases) |
| t_amx_dispatch_dtype | All tests passed (1612 assertions in 1 test case) |

Also green on that tree: `clang-format --dry-run -Werror` on the four files, `make lint-notes`, `git diff --check`.

The test binaries' own disassembly differs only where test code changed (Catch stringifies the expression text).

🤖 Generated with [Claude Code](https://claude.com/claude-code)

