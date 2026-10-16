## Short version

This PR stores the saved key vectors (K) of 128-dimension attention heads in the AMX VNNI layout, behind a typed owner (`k_vnni_tensor`) and typed views (`k_vnni_view`). The layout is read by an AVX-512 routine on the CPU and by the FPGA staging gather. No AMX instruction is added, and the CMake option that selects the layout is off in every build preset. This is the first of four PRs [The stack], and the AMX kernel that reads the layout comes in the second.

## Background

AMX tile multiplication accepts a row-major matrix only as its left operand and requires the VNNI layout for its right operand.

`main` stores K as one 128-value row per token. Its AMX QK kernel (the query-key score kernel) therefore puts the K page on the left and the VNNI-packed queries on the right, and transposes the resulting score matrix [PR #3879].

The new layout stores K^T in the right-operand format, in the same number of bytes. The next PR's AMX kernel is intended to compute `S = Q * K^T` directly, without the transpose. Other head sizes (gpt-oss-120b has 64-dimension heads) keep row-major K. Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` explains the layout, its writers and readers, and the kill switch.

## Words used here

| Term | Meaning |
|---|---|
| VNNI layout, VNNI-packed | Two consecutive dimensions of one token are adjacent in memory, and one 64-byte line holds that dimension pair for 16 consecutive tokens. This is the right-operand format of AMX tile multiplication. VNNI-packed means stored in this layout. |
| row-major K | The existing layout: one contiguous row of 128 values per token. |
| the option, AMX dispatch, the kill switch | The option is the CMake option `TRON_K_VNNI`, off by default. When on, it selects VNNI-packed K storage for every 128-dimension head. AMX dispatch is the CMake option `TRON_AMX_DISPATCH`, which compiles the AMX kernels and the code that selects them. The kill switch is `TRON_AMX_DISABLE=1`, which stops their use at run time. |
| KV page, plane, slot | A KV page is a 64-token block of the cache. A plane is the K or V storage of one page for one KV head (16 KiB for K). A slot is one persistent K/V storage region, usually one per layer. |
| dense page | A full 64-token page that the query sees whole. `main`'s AMX page kernel serves it in one call. |
| the reader, the dotter | The reader is `k_vnni::qk_group` in `h/tron/kernels/k_vnni.hpp`, the AVX-512 routine that scores a query group (the query heads sharing one KV head) against one VNNI-packed page, one token per vector lane. The dotter is `main`'s per-token dot product over a row-major row. |
| kv_mul | The number of query heads per KV head: 4 for qwen3-4b and llama-3.1-8b, 3 for llama-3.2-3b, 8 for qwen-3-30b-a3b. |
| rollback contract | Item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp`: the kill switch restores the tokens of a clean binary (a build with both options off). |
| base, new, baseoff, newoff | `base` is runtron (tron's command-line tool) built from `main` at the merge base with row-major K and AMX dispatch on. `new` is this head built with both options on. `baseoff` and `newoff` run those binaries with the kill switch. |

## How to review this PR

The best case against merging is that the PR adds a second storage layout for K while the kernel that justifies it comes in the next PR, and this head loses decode throughput on AMX hosts with the option on [Performance].

**Where this could be wrong**

**Can a raw pointer or a row-major view reach a VNNI-packed plane?** Read `h/tron/tensor/k_vnni.hpp`: `k_vnni_tensor` owns the plane, `k_vnni_view` reads it through `at(token, dim)`, and `detail::k_vnni_access` is the only route from a view to a plane address. Read `h/tron/models/kv_cache.hpp`: the row accessors `page::k()`, `kv_block::k_view` and `k_at` exist only for row-major slots, and `page::k_packed` is the read-only view the reader takes. The layout gate `k_vnni::layout_on<head_size>` depends only on storage geometry. Every reader and writer of a slot therefore selects the same layout. Pinned by: the compile checks in `t_llama_unit` (a raw pointer cannot construct a view, a temporary owner cannot produce one, `at()` cannot write) and cases 1 and 2 of `t_k_vnni_layout` (the index map, and stores and loads in scrambled token order).

**Which pages take which scoring path with the option on, and what does the kill switch change?** Read `h/tron/models/self_attention.hpp`: `if constexpr` on the layout gate selects the reader for VNNI-packed K and the per-token dotters for row-major K. The dense-page AMX predicate carries `&& !k_vnni::layout_on<operation_head_size>`, the temporary gate, until the AMX kernel PR. Every VNNI-packed page therefore goes through the reader on every host. Read `save_k` in `h/tron/models/model.hpp`: one `page::set_k_row` per token, a 4-scatter store that touches 64 cache lines per token where the row-major store touches 4. With the option on, the kill switch keeps the layout and the reader. Pinned by: the `t_amx_dispatch_dtype` expectation under the option (Q is prepared, no dense kernel call), the four-binary decomposition and the token-identity table [Verification].

**Does each head keep its own scratch row until `gof::populate` has copied it?** Read `populate` in `src/tron/gof.cpp`: it allocates K scratch beside V scratch and collects every head's pointer before it copies the rows. Read the scheduler callback in `h/tron/scheduler/full.hpp`: it gathers a VNNI-packed row through `page::get_k_row` into the caller's 64-byte-aligned scratch, and returns the existing row pointer for row-major K. Pinned by: the populate case of `t_phase1_integration`, which compares every staged value through the K swizzle (the element transposition the FPGA expects), and its mutation check (a deliberate code change that the test must catch) [Builds and tests].

**What you might decide differently**

**Should the layout gate depend on storage geometry alone?** Choice: `k_vnni::layout_on<head_size>` selects every 128-dimension head. Models with kv_mul 3 or 8 therefore also use the reader where `main` uses the dotter. Alternative: restrict the gate to the AMX group shape of 4 query heads. Check: the kv_mul item under Open items. Open.

**Is 0.05 the right weighted-V bound under VNNI K?** Choice: 0.05 absolute with the option on, and `main`'s 0.02 with it off, selected by the layout gate. Alternative: the observed maximum plus a margin, such as 0.03. Check: the tolerance item under Open items. Open. The test's author decides.

**May the rollback contract narrow to "with `TRON_K_VNNI` off"?** Choice: with the option on, the kill switch keeps the layout and the reader [the question above]. After the next PR it is not expected to reproduce the tokens of a clean binary. Alternative: keep a row-major binary as the deployment rollback artifact. Check: the kill-switch item under Open items and issue #4444. Open. Reviewers decide.

## Verification

Head `82d05e94be` (includes `main` at `72308ec90c`), Granite Rapids test machine (Intel Xeon 6962P with AMX), 2026-10-10. Builds: `nix develop` (the project's pinned build shell), clang 19.1.7, the `native` preset (explicit AVX-512 flags), `RelWithDebInfo`. Binaries: `base`, `new`, `baseoff`, `newoff` [Words used here].

### Builds and tests

Unit tests in three configurations: the option on with AMX dispatch, on without it, and off. Required CI builds with both options off [nix/cmake-tron-test-build.nix]. The option-dependent branches and dispatch paths run only in the manually dispatched legacy CMake lane and here (issue #4865).

- Pass in all three: `t_k_vnni_layout` (the new layout test, 4 cases), `t_llama_unit` (model and cache unit tests, 66 cases, also under the kill switch) and `t_heterogeneous_scheduler` (scheduling across attention geometries, 3 cases).
- Pass with dispatch on, and are `SUCCEED` placeholders with no dispatch coverage without it: `t_amx_dispatch_dtype` (dispatch per activation type, 1 case) and `t_amx_numerics` (AMX numerical accuracy, 4 cases). Under the kill switch the latter's QK and PV cases report "AMX unavailable".
- Passes in both option-on configurations, not built with the option off: `t_phase1_integration` (staging and dispatch integration, 64 cases).

Mutation check: removing the per-head offset from the scratch address in `gof::populate` makes the populate case of `t_phase1_integration` fail at `t/t_phase1_integration.cpp:920`.

Clean at the head: clang-format 19.1.7 on the 17 changed C++ files, `git diff --check` against `main`, no `<cassert>` in the diff, and a syntax-only compile of 9 translation units in all 4 combinations of the two options (38 configurations, 0 errors, 0 warnings). `make test-host` passes 93 tests, with `t_proxy_lib` skipped and `t_proxy_llama31` failed for the missing `t/proxy/.venv`, the two known exceptions.

### Token identity

qwen3-4b, `tp2` (split across 2 devices), 1 user, temperature 0, `--pay-for-determinism` (sums in a fixed order), 256 generated tokens. `new2` repeats `new` (the A/A control). `new2` and `newoff` must match `new` in every cell, and `base` is informational [issue #4444]. Identical means all 256 tokens match.

| Cell | new vs new2 | newoff vs new | new vs base |
|---|---|---|---|
| CPU attention, prompt 1,024 tokens | identical | identical | first difference at generated token 83 |
| CPU attention, prompt 8,192 tokens | identical | identical | identical |
| FPGA attention, prompt 1,024 tokens | identical | identical | first difference at generated token 83 |

### Performance

qwen3-4b, tp2, 8 users, 256 generated tokens, CPU attention, prompt lengths 1,024 and 8,192 tokens, 3 repetitions in alternating order. TPS is decode throughput in tokens/s/user. TTFT is the time to first token in seconds, the maximum over the 8 users. A difference is beyond the band, and counts as a change, when it exceeds twice the larger of the two binaries' sample standard deviations over the 3 repetitions (at most 0.19 TPS and 1.63 s), with a floor of 0.4 TPS and 0.15 s.

| Pair | TPS, prompt 1,024 | TPS, prompt 8,192 | TTFT, prompt 1,024 | TTFT, prompt 8,192 |
|---|---|---|---|---|
| new vs base | -6.4 %, beyond | -11.6 %, beyond | +25.8 %, beyond | +119.6 %, beyond |
| newoff vs baseoff | +3.4 %, beyond | +4.5 %, beyond | -1.0 %, inside | -4.8 %, beyond |
| newoff vs new | -0.5 %, inside | +0.3 %, inside | -1.6 %, inside | -0.4 %, inside |
| baseoff vs base | -9.9 %, beyond | -15.2 %, beyond | +25.0 %, beyond | +129.7 %, beyond |

- `new` loses against `base` in both cells. The temporary gate [How to review this PR] sends every page of a 128-dimension head to the reader, including the dense pages that `main`'s AMX kernel serves.
- `baseoff` minus `base` (the AMX kernels, -7.99 and -2.63 TPS) plus `newoff` minus `baseoff` (the layout, reader and row store, +2.45 and +0.66 TPS) gives -5.54 and -1.96 TPS, within the band of the measured -5.16 and -2.00 TPS. The loss is the disabled AMX kernels, partly offset by the reader.
- `newoff` against `new` is inside the band in both cells: the kill switch changes no scoring path here [How to review this PR].

## Open items

**128-dimension heads with kv_mul other than 4.** The next AMX kernel supports kv_mul 4 only, so llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) keep the reader after the stack. Settled by: their decode TPS at this head against `main`, with the band rule of Performance. Earlier measurements with this PR's reader on the PR #4424 branch (`9d5c7a389b`, 2026-10-09, and `65a1c41d72`, 2026-09-16): llama-3.2-3b -1.4 % at 32 users, qwen-3-30b-a3b from -4.1 % to +24.1 % by prompt length.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]** The first difference from `main` at generated token 83 [Token identity] has one hypothesis: a near tie between the two highest-scoring candidates under a different fp32 add order. Settled by: a forced run (teacher forcing via `--force-feed-text-token-file`), tracked in issue #4444 with the rollback-contract choice.

**A main test tolerance is widened.** `main` allows 0.02 absolute per weighted-V element in the `t_llama_unit` case "query splits match unsplit page reductions". Row-major results reach 0.018 and VNNI-packed K reaches 0.022. The option-on bound is therefore 0.05, with 1e-6 relative on the weight sum. The comment above `v_star_tolerance` in `t/t_llama_unit.cpp` explains why. The test's author decides.

**Not measured at this head.** The reader on an AMD host without AMX (`newoff` against `baseoff` on the genoa96 runner, the AMD test platform). The reader's gain against the row store's cost, and the share of the unconsumed AMX query pack, which runs once per token for a VNNI-packed slot with no consumer in this PR (per-function profiles of `newoff` and `new` at prompt length 8,192 tokens). The genoa96 timing row of `t_k_vnni_layout` in `config/test-benchmarks.json` (the slice check warns until a genoa96 run adds it).

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.** After a failed binary transfer, the legacy CMake workflow's benchmark job rebuilds runtron through `make` with neither option. Required CI is unaffected. Remedy: a configuration with both options, as `TRON_PAGE_SHARE_COUNTERS` has through the `coverage` preset.

## The stack

These four PRs, each based on the preceding one, replace PR #4424 (branch `jhan-amx-vnniK`, 4,054 lines), which stays open as a reference.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #4868 | this PR, `jhan-vnnik-1-layout` on `main` | VNNI-packed K layout, owner and views, row store, reader, FPGA staging gather, tests | ready for review |
| 2 | #4887 | `jhan-vnnik-2-amx` on this PR | AMX QK kernel `qk_vnni_128x4`, query packer `pack_q_rows_128x4`, bit-identity test, temporary gate removed | draft until PR #4868 merges |
| 3 | #4898 | `jhan-vnnik-3-shared-save` on PR #4887 | Shared 16-token block saves by the main thread and idle helper threads (the TTFT gain) | draft until PR #4887 merges |
| 4 | #4901 | `jhan-vnnik-4-tail-block` on PR #4898 | Row-major tail block, row-major policy under hardware attention (issue #4500), option on in the `deb` preset | draft until PR #4898 merges |

The option stays off in every preset until PR 4.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
