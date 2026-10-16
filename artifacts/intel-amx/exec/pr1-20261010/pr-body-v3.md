## Short version

This PR stores the saved key vectors (K) of 128-dimension attention heads in the AMX VNNI layout, behind a typed owner and typed views. In this pull request the layout is read by an AVX-512 routine on the CPU and by the FPGA staging gather, and no AMX instruction is added. The CMake option that selects the layout is off in every build preset, and the three later pull requests listed under The stack add the AMX kernel that reads the layout, a faster block save and a row-major tail block.

## Background

AMX tile multiplication accepts a row-major matrix only as its left operand. Its right operand must use the VNNI layout.

`main` stores K as one 128-value row per token. Its AMX QK kernel (the query-key score kernel) therefore puts the K page on the left. The page has 64 tokens × 128 dimensions. VNNI-packed queries go on the right. The resulting score matrix S is transposed. [PR #3879]

```text
S^T = K * Q^T
  K is the left operand. VNNI-packed Q^T is the right operand.
S = transpose(S^T)
  AVX-512 writes the 4 query columns as score rows.
```

The new memory layout stores K^T in the format required by the right operand. It uses the same number of bytes as row-major K. The next PR's AMX kernel is intended to compute `S = Q * K^T` directly, without the register transpose. Other head sizes retain row-major K. For example, gpt-oss-120b has 64-dimension heads. Note [K VNNI storage] in `h/tron/models/kv_cache.hpp` explains the layout, its writers and readers, and the kill switch.

## Words used here

| Term | Meaning |
|---|---|
| VNNI layout, VNNI-packed | Two consecutive dimensions of one token are adjacent in memory. One 64-byte line holds that dimension pair for 16 consecutive tokens. This is the B-operand format, meaning the right-hand matrix format, of AMX tile multiplication. VNNI-packed means stored in this layout. |
| row-major K | The existing layout: one contiguous row of values per token. For the heads changed here, each row holds 128 values. |
| the option, AMX dispatch, the kill switch | The option is the CMake option `TRON_K_VNNI`. It defaults to OFF. When on, it selects VNNI-packed K storage for every 128-dimension head. AMX dispatch is `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. This PR does not require it. The kill switch is `TRON_AMX_DISABLE=1`. It prevents use of the AMX kernels at run time. AMX-on names a run without the switch, and AMX-off a run with it. |
| KV page, block, plane, slot | A KV page is a 64-token block allocated by the cache. Within this PR, a block means 16 consecutive tokens of a page, or one AMX tile width. A plane is K or V storage for one page and one KV head (one key/value head). A K plane occupies 16 KiB: 64 tokens × 128 dimensions × 2 bytes per value. A slot is one persistent K/V storage region, usually one per layer. |
| owner, view, row view | `k_vnni_tensor` owns one K plane as a 64-byte-aligned array. `k_vnni_view` refers to that plane and computes element addresses. Views come only from an owner. `at(token, dim)` reads one element and cannot write it. A row view is a typed view of one token's 128 K values in dimension order (`const_k_row_view` and `k_row_view`, with the `k_source_row` and `k_destination_row` helpers). It moves a row into or out of the cache. |
| dense page | A full 64-token page that the query sees whole. The AMX page kernel of `main` processes it in one call. |
| the reader, the dotter | The reader is `k_vnni::qk_group` in `h/tron/kernels/k_vnni.hpp`, the AVX-512 routine that scores a query group (the query heads that share one KV head) against one VNNI-packed page, one token per vector lane. The dotter is `main`'s per-token dot-product routine for a row-major row. |
| kv_mul | The number of query heads per KV head: 4 for qwen3-4b and llama-3.1-8b, 3 for llama-3.2-3b, and 8 for qwen-3-30b-a3b. |
| rollback contract | The documented promise of what the kill switch restores: item 4 of Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp`, which promises the tokens of a clean binary (a build with both options off). |
| base, new, baseoff, newoff | `base` is `main` at this PR's merge base, built as runtron (tron's command-line tool) with row-major K and AMX dispatch on. `new` is this branch at the head, built with both options on. Both commits are named under Verification. `baseoff` and `newoff` run those respective binaries with the kill switch. |

## How to review this PR

The best case against merging is that the PR adds a second storage layout for K while the kernel that justifies it comes in the next PR, and this head loses decode throughput on AMX hosts with the option on [Performance].

**Where this could be wrong**

**Can a raw pointer or a row-major view reach a VNNI-packed plane?** Read `h/tron/tensor/k_vnni.hpp`: `k_vnni_tensor` owns the plane, `k_vnni_view` reads it through `at(token, dim)`, and `detail::k_vnni_access` is the only route from a view to a plane address. Read `h/tron/models/kv_cache.hpp`: the row accessors `page::k()`, `kv_block::k_view` and `k_at` exist only for row-major slots, and `page::k_packed` is the read-only view the reader takes. The layout gate `k_vnni::layout_on<head_size>` depends only on storage geometry (head counts and dimensions). Every reader and writer of a slot therefore selects the same layout. Pinned by: the compile checks in `t_llama_unit` (a raw pointer cannot construct a view, a temporary owner cannot produce one, `at()` cannot write) and cases 1 and 2 of `t_k_vnni_layout` (the index map, and stores and loads in scrambled token order).

**Which pages take which scoring path with the option on, and what does the kill switch change?** Read `h/tron/models/self_attention.hpp`: `if constexpr` on the layout gate selects the reader for VNNI-packed K and the per-token dotters for row-major K. The dense-page AMX predicate carries `&& !k_vnni::layout_on<operation_head_size>`, the temporary gate, until the AMX kernel PR. Every VNNI-packed page therefore takes CPU software attention, through the reader, on every host. Read `save_k` in `h/tron/models/model.hpp`: one `page::set_k_row` per token, a 4-scatter store that touches 64 cache lines per token where the row-major store touches 4. With the option on, the kill switch keeps the layout and the reader. Pinned by: the `t_amx_dispatch_dtype` expectation under the option (Q is prepared, no dense kernel call), the four-binary decomposition and the token-identity table [Verification].

**Does each head keep its own scratch row until `gof::populate` has copied it?** Read `populate` in `src/tron/gof.cpp`: it allocates K scratch beside V scratch and collects every head's pointer before it copies the rows. Read the scheduler callback in `h/tron/scheduler/full.hpp`: it gathers a VNNI-packed row through `page::get_k_row` into the caller's 64-byte-aligned scratch, and returns the existing row pointer for row-major K. Pinned by: the populate case of `t_phase1_integration`, which compares every staged value through the K swizzle (the element transposition the FPGA expects), and its mutation check (a deliberate code change that the test must catch) [Builds and tests].

**What you might decide differently**

**Should the layout gate depend on storage geometry alone?** Choice: `k_vnni::layout_on<head_size>` selects every 128-dimension head. Models with kv_mul 3 or 8 therefore also use the reader where `main` uses the dotter. Alternative: restrict the gate to the AMX group shape of 4 query heads. Check: the kv_mul item under Open items. Open.

**Is 0.05 the right weighted-V bound under VNNI K?** Choice: 0.05 absolute with the option on, and `main`'s 0.02 with it off, selected by the layout gate. Alternative: the observed maximum plus a margin, such as 0.03. Check: the tolerance item under Open items. Open. The test's author decides.

**May the rollback contract narrow to "with `TRON_K_VNNI` off"?** Choice: with the option on, the kill switch keeps the layout and the reader [the question above]. After the next PR it is not expected to reproduce the tokens of a clean binary (a build with both options off). Alternative: keep a row-major binary as the deployment rollback artifact. Check: the kill-switch item under Open items and issue #4444. Open. Reviewers decide.

## Verification

Head `82d05e94be`, which includes `main` at `72308ec90c`, on the Granite Rapids test machine (Intel Xeon 6962P with AMX), 2026-10-10. Builds use `nix develop` (the project's pinned build shell), clang 19.1.7, the `native` preset (explicit AVX-512 flags) and the `RelWithDebInfo` build type, each configuration in its own worktree. `BUILD_INGEST_MODELS` controls compilation of generated models. The runtron binaries are `base`, `new`, `baseoff` and `newoff` [Words used here].

### Builds and tests

| Configuration | `TRON_K_VNNI` | `TRON_AMX_DISPATCH` | `BUILD_INGEST_MODELS` | Targets | Build time |
|---|---|---|---|---|---|
| option on | ON | ON | ON | runtron and the 6 tests below | 597 s |
| option on, no AMX dispatch | ON | OFF | OFF | the same | 284 s |
| option off | OFF | ON | OFF | the 5 layout-independent tests | 292 s |

The unit tests ran with a fake device and `--skip-benchmarks`. Each cell gives assertions / test cases.

| Test | Option on | Option on, no AMX dispatch | Option off |
|---|---|---|---|
| `t_k_vnni_layout` (the new layout test, 4 cases) | 1011432 / 4 | 1011432 / 4 | 1011432 / 4 |
| `t_amx_dispatch_dtype` (dispatch per activation type) | 1612 / 1 | 1 / 1 (placeholder without dispatch) | 1612 / 1 |
| `t_amx_numerics` (AMX numerical accuracy) | 4109 / 4 (AMX cases ran, no “AMX unavailable” line) | 1 / 1 (placeholder) | 4109 / 4 |
| `t_llama_unit` (model and cache unit tests) | 266453 / 66 | 266453 / 66 | 266522 / 66 |
| `t_heterogeneous_scheduler` (scheduling across attention geometries) | 2783 / 3 | 2783 / 3 | 2783 / 3 |
| `t_phase1_integration` (staging and dispatch integration) | 6220 / 64 | 6220 / 64 | not built |

With the kill switch, the option-on build passes `t_llama_unit` with the same 266453 assertions in 66 cases, and `t_amx_numerics` with 2060 assertions in 4 cases, its QK and PV (weighted-V product) precision cases reporting "AMX unavailable". The row-major build passes the split-versus-unsplit case of `t_llama_unit` under `main`'s bounds, and the VNNI-packed builds pass it under the VNNI bounds [Open items]. The option-off build has 69 more `t_llama_unit` assertions: its geometry case checks individual elements of the 128-dimension slot, where the VNNI-packed build checks that the row view is absent.

Mutation check: with `+ h * HW_BAKED_HEAD_SIZE` (the per-head offset, from the FPGA's fixed head size) removed from the scratch address in `gof::populate`, `t_phase1_integration` fails its populate case (1 of 3 assertions, at the `REQUIRE` of `t/t_phase1_integration.cpp:920`). With the file restored it passes again with 6220 assertions in 64 cases.

Clean at `82d05e94be`: clang-format 19.1.7 with `--dry-run --Werror` on all 17 changed C++ files, `git diff --check` against `main`, and a search for the prohibited `<cassert>` header in the diff. A syntax-only compile (clang 19 with `-fsyntax-only` and the product's compile flags) of 9 translation units in all 4 combinations of the two options, plus `kernels/amx_attn.cpp` with dispatch on and the option on or off, gives 0 errors and 0 warnings in 38 configurations.

The host suite (`make test-host` with a fake device, option on): 93 tests passed, 1 skipped (`t_proxy_lib`, "SKIP: t/proxy/.venv missing") and 1 failed (`t_proxy_llama31`, "ERROR: t/proxy/.venv missing"), the two known exceptions for the missing Python virtual environment, in 112 s.

### Token identity

runtron ran qwen3-4b, `tp2` (the model split across 2 devices), 1 user, temperature 0, `--pay-for-determinism` (sums in a fixed order), seed identifier 1 and 256 generated tokens: CPU attention at prompt lengths 1,024 and 8,192 tokens, FPGA attention at 1,024 tokens. `new2` is a repeat of `new`, the A/A control. `new2` and `newoff` must match `new` for all 256 tokens in every cell. The comparison with `base` is informational [issue #4444].

| Cell | new vs new2 | newoff vs new | new vs base |
|---|---|---|---|
| CPU attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 |
| CPU attention, prompt length 8192 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| FPGA attention, prompt length 1024 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 83 |

### Performance

The cells: qwen3-4b, tp2, 8 users, 256 generated tokens, CPU attention (`USE_HW_ATTN=0`), prompt lengths 1,024 and 8,192 tokens, 3 repetitions with the binaries in alternating order, on the experiment's half of the machine. TPS is decode throughput in tokens/s/user. TTFT is time to first token in seconds, the maximum over the 8 users. Values in parentheses are the sample standard deviation over the 3 repetitions. The decision band is twice the larger of the two binaries' standard deviations, never smaller than 0.4 TPS or 0.15 s, and a difference beyond it counts as a change. The paired t statistic (the mean paired difference relative to its uncertainty, dimensionless) uses the 3 repetitions.

| Prompt length (tokens) | Binary | TPS (tokens/s/user) | TTFT (s) |
|---|---|---|---|
| 1024 | base | 80.61 (0.16) | 3.185 (0.010) |
| 1024 | new | 75.45 (0.11) | 4.005 (0.002) |
| 1024 | newoff | 75.07 (0.14) | 3.941 (0.000) |
| 1024 | baseoff | 72.62 (0.19) | 3.981 (0.007) |
| 8192 | base | 17.26 (0.01) | 53.510 (1.634) |
| 8192 | new | 15.26 (0.03) | 117.516 (0.160) |
| 8192 | newoff | 15.30 (0.05) | 117.090 (0.301) |
| 8192 | baseoff | 14.64 (0.03) | 122.938 (0.126) |

| Prompt length (tokens) | Pair | TPS difference (paired t) | TTFT difference (paired t) |
|---|---|---|---|
| 1024 | new vs base | -6.4 % (-5.16 TPS, t -36.5), beyond | +820 ms (+25.8 %, t +158.8), beyond |
| 1024 | newoff vs baseoff | +3.4 % (+2.45 TPS, t +36.3), beyond | -41 ms (-1.0 %, t -10.5), inside |
| 1024 | newoff vs new | -0.5 % (-0.37 TPS, t -5.4), inside | -65 ms (-1.6 %, t -65.2), inside |
| 1024 | baseoff vs base | -9.9 % (-7.99 TPS, t -150.2), beyond | +796 ms (+25.0 %, t +209.4), beyond |
| 8192 | new vs base | -11.6 % (-2.00 TPS, t -174.6), beyond | +64.0 s (+119.6 %, t +69.6), beyond |
| 8192 | newoff vs baseoff | +4.5 % (+0.66 TPS, t +13.4), beyond | -5.8 s (-4.8 %, t -23.9), beyond |
| 8192 | newoff vs new | +0.3 % (+0.04 TPS, t +0.9), inside | -425 ms (-0.4 %, t -1.8), inside |
| 8192 | baseoff vs base | -15.2 % (-2.63 TPS, t -199.0), beyond | +69.4 s (+129.7 %, t +69.3), beyond |

What the tables say:

- `new` loses decode throughput against `base`: -6.4 % at prompt length 1,024 tokens and -11.6 % at 8,192 tokens, with TTFT +26 % and +120 % (rounded). The temporary gate [How to review this PR] sends every page of a 128-dimension head to the reader, including the dense pages that `main`'s AMX kernel serves.
- `main` loses the same way when its own AMX kernels are switched off. `baseoff` against `base` is -9.9 % and -15.2 % TPS and about +25 % and +130 % TTFT. At prompt length 8,192 tokens those kernels do most of the prefill attention work.
- The four binaries decompose the loss. `baseoff` minus `base` is the contribution of `main`'s AMX kernels. `newoff` minus `baseoff` is the effect of the layout, the reader and the row store, with AMX off on both. Their sum from the unrounded means is -5.54 and -1.96 TPS, against a measured `new` minus `base` of -5.16 and -2.00 TPS. The residuals, +0.37 and -0.04 TPS, equal `new` minus `newoff` and are inside the band in both cells. So the loss is the disabled AMX kernels, partly offset by the reader. The comparison does not separate the reader's gain from the row store's cost [Open items].
- The reader against the dotter, with the kill switch on both binaries (`newoff` against `baseoff`): decode TPS +3.4 % and +4.5 %, both beyond the band, and TTFT -1.0 % (inside the band) and -4.8 % (beyond).
- The kill switch inside this PR (`newoff` against `new`): TPS -0.5 % and +0.3 %, inside the band in both cells. The switch changes no scoring path here [How to review this PR]. TTFT is lower with the switch by 65 ms (1.6 %) and 425 ms (0.4 %), inside the band in both cells. The unconsumed query pack is the known difference [Open items].
- The next PR is intended to remove the temporary gate by adding an AMX kernel for this layout. A measurement at that PR's head must establish the result.

### CI coverage

Required CI builds with both options off: neither `TRON_AMX_DISPATCH` nor `TRON_K_VNNI` is enabled in its test build. [nix/cmake-tron-test-build.nix] The first 3 cases of `t_k_vnni_layout` run there and exercise the VNNI-packed owner, the storage operations and the reader. Its fourth case runs there with row-major cache storage only. The VNNI-packed branch of that case and the option-dependent branches of `t_llama_unit` do not run there. Without dispatch, `t_amx_dispatch_dtype` runs a `SUCCEED` placeholder, a passing case with no dispatch-path coverage. Those paths run in the manually dispatched legacy CMake lane, which enables both options, and in the Granite Rapids verification above. The author accepts this limitation for this PR. Issue #4865 tracks enabling both options in the required test build, and an AMX runner for the next PR's kernel-identity case (the test that compares the new AMX kernel's output bit for bit with the row-major kernel's).

## Open items

**128-dimension heads with kv_mul other than 4 query heads.** The next AMX kernel supports kv_mul 4 only. Other groups keep the VNNI-packed layout and use the reader wherever `main` uses the dotter, in this PR and after the stack. This is not measured at `82d05e94be`. The measurement that settles it: decode TPS of llama-3.2-3b and qwen-3-30b-a3b at this head against `main` at `72308ec90c`, 3 repetitions, with the band rule of the Performance subsection. Earlier measurements on the PR #4424 branch, whose reader and decode store are this PR's, give the direction:

- llama-3.2-3b, tp2, 32 users, 200 tokens per user plus an 800-token prompt prefix shared by all users: -1.4 % decode TPS, confirmed in two independent pairs of nightly benchmark passes (paired t at least 2.26 in magnitude, difference at least 1 %). `9d5c7a389b` against `main` `be0d5565b3`, 2026-10-09.
- qwen-3-30b-a3b, tp2, 8 users: +1.5 % at prompt length 1,024 tokens (6 repetitions, within the reported measurement variation), -4.1 % at 2,048 tokens and +24.1 % at 8,192 tokens (3 repetitions each). `65a1c41d72` against `main` `c7844ca2ce`, 2026-09-16.

The two alternatives, a gate restricted to the AMX group shape (which would then depend on the group size) or a better reader for larger groups, are posed under How to review this PR.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]** The first difference from `main` at generated token 83 in both 1,024-token cells [Token identity] has one hypothesis: the different fp32 add order changes a near tie between the two highest-scoring token candidates. A forced run (teacher forcing via `--force-feed-text-token-file`) is needed to confirm or reject it. That measurement is tracked in issue #4444. After the next PR the kill switch is expected to provide an AMX-off run of the same binary, not clean-binary tokens, which the rollback contract promises. Issue #4444 records the two choices posed under How to review this PR: narrow the contract by adding "with `TRON_K_VNNI` off" to its item 4, or keep a row-major binary as the deployment rollback artifact and document that requirement.

**A main test tolerance is widened.** The `t_llama_unit` case "apply and join page ranges / query splits match unsplit page reductions" compares one page reduction (the attention sum over all tokens of one page) with two separately computed ranges joined afterward. `main` permits an absolute difference of 0.02 in a weighted-V output element and 2e-6 in the weight sum (both dimensionless). The two computations can reach a page with different running maxima (the largest score seen so far, which softmax subtracts before exponentiation). The weights are therefore converted to bf16 (16-bit brain floating point) at different scales for the PV product, and the AVX path truncates in that conversion. Row-major results already reach 0.018 and 1.9e-6 against those limits. VNNI-packed K changes the last bits of the scores. The bf16 conversion then rounds at a different point. One weighted-V element reaches an absolute difference of 0.022. With the option on, this PR uses 0.05 absolute for weighted V and 1e-6 relative (one part per million) for the weight sum, selected by a compile-time check of the layout gate. With the option off, the bounds are `main`'s. Both builds pass [Builds and tests]. The question for the test's author, whether 0.05 (2.3 times the observed 0.022) is the right bound, is posed under How to review this PR.

**Not measured at this head.**

- AMD host: whether the reader gains decode TPS where no AMX exists. The measurement: `newoff` against `baseoff` on the genoa96 runner (the AMD test platform) at the same two cells.
- Reader gain against row-store cost: how much of the `newoff` against `baseoff` gain is the reader, and how much the scatter store costs. The measurement: a per-function profile of `newoff` at prompt length 8,192 tokens, splitting `save_k` time from `k_vnni::qk_group` time.
- Unconsumed query pack: the AMX query pack (the step that rearranges query vectors into the AMX operand format) runs once per token for a VNNI-packed slot. No kernel consumes it in this PR. The kill switch skips it. The measurement: the same profile on `new`, with the pack's share of a decode step.
- genoa96 timing for `t_k_vnni_layout`: the genoa96 block of `config/test-benchmarks.json` has no timing row for it. Another platform has one. The slice check (`bin/slice bench --check`, which requires a timing record for every registered test) therefore passes with a warning. A genoa96 run adds the row.

**Benchmark binary mismatch, inherited from PR #3879. Reviewers decide.** The legacy CMake workflow's `build` job compiles runtron with `-DTRON_AMX_DISPATCH=ON -DTRON_K_VNNI=ON` and transfers that binary to its `benchmark` job. After a failed transfer, the benchmark job builds runtron through `make`, which sets neither option, and benchmarks row-major K without AMX kernels. PR #3879 introduced the mismatch for AMX dispatch. This PR adds the layout option to the same configure line. Required CI is unaffected: its benchmark binary has neither option enabled. One remedy is a separate configuration containing both options, as `TRON_PAGE_SHARE_COUNTERS` (the page-sharing instrumentation option) already has through the `coverage` preset.

## The stack

PR #4424 uses branch `jhan-amx-vnniK` and adds 4,054 lines. Four dependent PRs replace it. Each is based on the preceding PR. PR #4424 remains open as a reference until all four are open.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #4868 | this PR, `jhan-vnnik-1-layout`, based on `main` | VNNI-packed K layout, owner and views, per-row store, reader, FPGA staging gather, the option disabled in presets, and tests | ready for review |
| 2 | #4887 | `jhan-vnnik-2-amx`, based on this PR | The AMX QK kernel `qk_vnni_128x4` and query packer `pack_q_rows_128x4`. A bit-identity test compares with the row-major kernel. The temporary gate and comments are removed. | draft until PR #4868 merges |
| 3 | #4898 | `jhan-vnnik-3-shared-save`, based on PR #4887 | Shared saves of 16-token blocks, transposed in registers and written as whole cache lines by the main thread and idle helper threads. This provides PR #4424's TTFT improvement. | draft until PR #4887 merges |
| 4 | #4901 | `jhan-vnnik-4-tail-block`, based on PR #4898 | A row-major tail block: a 16-token block with unsaved rows stays row-major. It converts to the VNNI-packed layout when all 16 rows are saved. A row-major policy under hardware attention addresses issue #4500. The `deb` package-build preset enables the option in the released package. | draft until PR #4898 merges |

The option stays off in every preset until PR 4. Intermediate states therefore do not enter production through those presets.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
