## Short version

This PR is PR #4957 (the AMX QK kernel for the VNNI K layout) re-expressed on the structure of PR #5047, in which the cache alone knows the K layout. The kernel call moves into `page::try_score_k_amx`, and a new `page::pack_q_amx` chooses the query packer next to the kernel, so the attention code holds no layout clause. It also fixes three defects of PR #5047's head: a test that breaks the build, two compile-time probes that test nothing, and comments that no longer match the code.

## Background

PR #5047 rewrites PR #4956. In its form the cache owns the K layout: `page::score_k` scores selected tokens in software, `page::try_score_k_amx` scores a dense page with AMX or returns false, and `set_k_row` converts a row inside the cache. At its head `try_score_k_amx` declines every VNNI slot. PR #4956 has no AMX kernel for that layout.

PR #4957 adds the kernel, but it calls it from the attention code with a layout clause at the dense-page site and packs the query with a second layout clause at the pack site. Those two clauses are what PR #5047 removes everywhere else. This PR is the same kernel, the same packer and the same tests behind the cache's two operations. The stack then reads as one design. Note [QK orientation] in `h/tron/kernels/amx_attn_iface.hpp` explains why the two layouts need different packers (the query is the left operand of the tile multiply for a VNNI slot and the right operand for a row-major slot).

## Words used here

| Term | Meaning |
|---|---|
| the cache | h/tron/models/kv_cache.hpp: `struct page` (one 64-token KV page) and `struct book` (the pages of one model instance) |
| the attention code | h/tron/models/self_attention.hpp, the CPU attention loop that calls the cache |
| the option | the CMake option TRON_K_VNNI. When it is on, the K cache of 128-dimension heads is stored in the AMX VNNI layout |
| a VNNI slot | a K storage slot that uses that layout. A row-major slot stores one token's row after another |
| AMX | Intel tile-matrix instructions. TRON_AMX_DISABLE=1 (the kill switch) turns the AMX attention path off at run time |
| the kernel | qk_vnni_128x4, the AMX QK kernel over a VNNI page (kernels in src/tron/kernels/amx_attn.cpp) |
| the reader | k_vnni::qk_group, the AVX-512 scoring loop over the VNNI plane (h/tron/kernels/k_vnni.hpp) |
| a dense page | a full 64-token page that the query sees whole. It is the only page shape the AMX path scores |
| the dispatch test | t_amx_dispatch_dtype, which counts calls of stand-in kernels instead of running AMX |
| the identity case | the case of t_amx_numerics that compares the kernel's scores from the VNNI plane with the row-major AMX kernel's scores bit for bit, on real AMX |
| the hetero test | t_heterogeneous_scheduler (source t/heterogeneous_scheduler_compile.cpp), the scheduler test that stores one K row by hand |
| the syntax matrix | 22 compiler runs (two generated trees x the option off/on x five test files, plus the AMX kernel file) that parse and instantiate the code without linking or running it |
| 3bda | delphi-3bda, the Intel server where the builds and unit tests run |

## How to review this PR

**Does the cache choose the packer and the kernel of the same layout, and does nothing outside the cache know the layout?**
- `h/tron/models/kv_cache.hpp`: `page::pack_q_amx` and `page::try_score_k_amx` sit side by side under `TRON_AMX_DISPATCH`. Each tests the layout once. A VNNI slot gets `pack_q_rows_128x4` and the kernel. A row-major slot gets `pack_q_group_128x4` and `qk_rowmajor_128x4`.
- `h/tron/models/self_attention.hpp`: `packed_amx_query` calls `page::pack_q_amx`, and `apply_dense_amx_page` calls `try_score_k_amx` and returns false when the cache declines. The file uses no `k_vnni::` symbol and includes neither the reader nor the dotter header.
- `h/tron/models/model.hpp` and `h/tron/scheduler/full.hpp` are byte-identical to PR #5047's head.
- Verification: the dispatch test expects one pack, one QK and one PV call for a dense page under either value of the option, and one call of `pack_q_rows_128x4` only with the option on. Compile-time probes in `t_llama_unit` check that the kernel accepts the VNNI plane view and rejects raw pointers, the row-major K view and the V view, and that no page operation returns a K storage view.

**Are the stored bytes and the scores those of PR #4957?**
- `h/tron/models/kv_cache.hpp`, `try_score_k_amx`: the VNNI branch passes the plane view the cache holds to the kernel. Both branches return true. So the software fallback that follows a false return has no live caller at this head. Its first live caller is the row-major tail block of the fourth PR of the stack.
- `h/tron/tensor/k_vnni.hpp`, `k_vnni::panel_offset`: the one spelling of a panel's address (a panel is the 1 KiB part of a plane for one 32-dimension step and one 16-token block, one AMX tile). The kernel and the reader both take their panel addresses from it. A `static_assert` checks it against the element index map for all 16 panels.
- Storage, the store path and the kernel's tile loads are unchanged against PR #4957, so the scores are bit for bit the same.
- Verification: the identity case on 3bda, and the token-identity run listed under Pending measurement.

**Do the three fixes of PR #5047's head hold, and should PR #5047 take them?**
- `t/heterogeneous_scheduler_compile.cpp`: the zero K row is stored through `page::set_k_row` with a `k_source_row`. At PR #5047's head the test writes through `page::k`, which that head removes, so its "Build Tron" job fails.
- `t/t_llama_unit.cpp`: `page_k_accepts_slot` is a template on the slot type. The `kv_slot_id` form is asserted true as a positive control, and the `size_t` form asserted false. At PR #5047's head the probe names `Page::head_size`, which does not exist, so it is false for the wrong reason. `page_exposes_kv_block` asserts that `kv_block` stays private and replaces a probe of `page::k_packed`, which no longer exists.
- The comments of `apply_dense_amx_page`, the AMX gate, `try_score_k_amx` and `page_info` in `h/tron/gof.hpp` state what the code does at this head: the cache may decline, and K and V rows always arrive in the caller's scratch.
- Verification: the hetero test compiles and passes on 3bda [Verification]. The probe change is a compile-time assertion. Open: whether PR #5047 takes the same three fixes. Its author decides.

## Verification

Head `3258fcbe69` is PR #4957's head `26b86a279a` merged with PR #5047's head `ade89a9d9c`, followed by five commits. The syntax matrix runs on the development host with zig clang 19 at the head. The builds and unit tests run on 3bda on 2026-10-21 at `9a8045836a`, which differs from the head by three deleted comment lines, with clang 19, the `native` preset, `BUILD_INGEST_MODELS` and `TRON_AMX_DISPATCH` on, in two configurations: `bp2` (the option off) and `bp2v` (the option on). No performance run exists at this head. PR #4957's table is measured at `0ee8671d35` on PR #4956 at `82d05e94be`.

### Builds and tests

The syntax matrix is clean at the head: 22 cells, 0 errors, 0 warnings. It proves parsing, template instantiation and every `static_assert`, and nothing about object code, linking or run time.

Clean: clang-format on the 13 changed C++ files, `git diff --check`, no `<cassert>` in the diff, no issue or PR number in a new comment.

Unit tests on 3bda (fake device, `--skip-benchmarks`, software attention):

BDA_TABLE_PR2

### Pending measurement

- Question: does this head generate the tokens PR #4957's head generates, and does it keep PR #4957's throughput?
- Comparator: PR #4957's head `26b86a279a` built the same way, plus this head under the kill switch.
- Cells: qwen3-4b, tp2, prompt 1,024 and 8,192 tokens, 256 generated tokens, under CPU attention and under FPGA attention. Token identity uses 1 user. Throughput uses 8 users.
- Expected verdict: identical tokens. Storage, the store path and the kernel are unchanged, so the scores are the same. Throughput inside the band in the CPU cells for the same reason. The FPGA cells carry PR #5047's always-copy K staging (`k_head_fn`). PR #5047 measures that copy inside the band against its base (2026-10-21 campaign, 4 repetitions: qwen3-4b tp2 prompt 1,024 tokens TPS +0.2 % and prefill +0.010 s, gpt-oss-120b tp4 TPS -0.8 %).

## Open items

**Three fixes for PR #5047.** The hetero test, the two probes and the comments [How to review this PR, third question]. Reviewers decide.

**Performance at this head.** The run under Pending measurement. The session owner runs it after the stack's three drafts are gated. One inherited fact for the CPU cells: PR #5047's own kill-switch cell (llama-3.1-8b, prompt 8,192 tokens, every K token through the software scoring loop) measures prefill +2.9 % against its base. This head inherits that loop.

STACK_SECTION

🤖 Generated with [Claude Code](https://claude.com/claude-code)
