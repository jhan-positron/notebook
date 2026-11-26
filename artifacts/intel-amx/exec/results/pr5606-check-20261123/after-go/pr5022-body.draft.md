## Short version

The AMX kernels accept Muse Glimmer 30B's shape, 16 query heads per KV head, through one template parameter, and the kv_mul-4 pack and QK kernels emit the same instructions as on main. Glimmer's 39 sliding-window layers then run on AMX instead of the AVX loop. On delphi-3bda with 8 users, Glimmer's decode rate per user rises by 4.4 to 15.2 % and its prefill time shortens by 0.6 to 8.7 % with the production attention mode (FPGA on the 13 full layers, CPU on the 39 sliding-window layers).

## Background

Glimmer has 32 query heads sharing 2 KV heads, with 128 dimensions per head. Main supports only kv_mul 4 on AMX. Its CPU attention therefore uses AVX for Glimmer.

The interface header's Notes [AMX attention dispatch], [QK orientation] and [Tile stores write 16 rows] define the dispatch, layout and buffer contracts. Kernel naming and future group-size work are tracked in [#5021](https://github.com/positron-ai/tron/issues/5021).

## How to review this PR

**Does the transpose write exactly the intended query rows?**

- `h/tron/kernels/amx_attn_transpose.hpp`: check the lane-to-row mapping in `store_transposed_rows` against Note [QK orientation]. Lane stores are selected by `if constexpr`, without runtime condition checks.
- `h/tron/kernels/amx_attn_iface.hpp`: distinguish the QK buffer's useful rows from the PV buffer's required 16 rows.
- Verification: `t_amx_numerics`. The transpose case checks both group sizes against a scalar transpose on every host. The QK case checks both group sizes on an AMX host and that unused score rows stay untouched. The PV case checks the useful rows and that the other rows are zero. The packer case checks zero padding.

**Do dispatch and compiled kernels agree on supported groups?**

- `h/tron/kernels/amx_attn_iface.hpp`: `group_heads_ok` and each declaration's `requires` clause admit only 4 or 16 heads. Eligibility also requires 128 dimensions per head and bf16 activations (the 16-bit bfloat16 format).
- `src/tron/kernels/amx_attn.cpp`: explicit instantiations must match that set. Direct kernel calls with unsupported group sizes fail to compile. An admitted size without an instantiation would fail to link.
- `h/tron/models/self_attention.hpp`: all three kernel calls pass the model's `operation_kv_mul`. Partial pages retain the AVX path.
- Verification: `t_amx_numerics` rejects kv_mul 8 and 32. `t_amx_dispatch_dtype`, with kernel test doubles, checks the group size through the executor, the softmax state of every head, and the pack start for a second KV head.

**Does the four-head path retain its behavior?**

- `src/tron/kernels/amx_attn.cpp`: inspect the four-head loops and separate per-instantiation scratch storage.
- Verification: [Verification] records the kernel comparison, llama-3.1-8b token identity and performance results.

## Verification

Tests run at the head `90a9110be5` on delphi-3b35, a Xeon 6962P host with AMX, on 2026-11-24 (`pr5606-check-20261123`). Token and performance measurements run on delphi-3bda, the machine of the nightly systems test, at `5061623a34`, against its merge base `6198824246` ("base" below) where specified. The test and measurement builds use clang 19.1.7, preset `native`, RelWithDebInfo and `TRON_AMX_DISPATCH=ON`. Only the measurement builds set `BUILD_INGEST_MODELS=ON`. Initial runs use `nix develop` on 2026-10-16–17 (`glimmer-20261016`). Extended comparisons use a plain-shell build on 2026-10-18 (`glimext-20261018`). The nightly comparison uses main package `3751511dcc` and a `deb`-preset package of the measured commit on 2026-10-17 (`glimci-20261017`). These result records are on the test servers, outside this repository.

The performance measurements are not repeated at the head. This PR's changes since the measured commit carry a low risk for performance. Compiled with the build's own command, 10 of the kernel file's 11 functions match the measured commit exactly. The 16-head QK kernel has the same 207 instructions, with two adjacent loop-counter additions swapped. Two edits in `apply_dense_amx_page` remove work: the zero fill of the score buffer `s_pages` and the copy of each PV output row. The PR's other changes since then are comments, tests and documentation. The head also contains main up to `3bea58b788`, which the nightly systems test measures.

Below, the kill switch means `TRON_AMX_DISABLE=1` in the same binary. Layouts tp2/tp4 use two/four FPGA cards per model instance.

### Builds and tests

| Configuration | Built test executables | Results: assertions / cases |
|---|---|---|
| AMX enabled | `t_amx_numerics`, `t_amx_dispatch_dtype`, `t_llama_unit` | `t_amx_numerics`: 21,521 / 5 pass<br>`t_amx_dispatch_dtype`: 30,747 / 1 pass<br>`t_llama_unit`: 265,564 / 75 pass |
| Kill switch | Same executables | `t_amx_numerics`: 6,671 / 3 pass, 2 skipped<br>`t_amx_dispatch_dtype`: 30,747 / 1 pass<br>`t_llama_unit`: 265,564 / 75 pass |
| `TRON_AMX_DISPATCH=OFF` (default CI build, `gcp-nix.yml`) | CI run [RUN_ID_NIX](https://github.com/positron-ai/tron/actions/runs/RUN_ID_NIX), jobs Build Tron and Test host | Both jobs pass. `t_amx_dispatch_dtype` and the transpose case run. Four `t_amx_numerics` cases are compiled out. |
| Option ON in CI (`cmake-single-platform.yml`, started by hand) | Run [RUN_ID_CMAKE](https://github.com/positron-ai/tron/actions/runs/RUN_ID_CMAKE), test-host on runner RUNNER_NAME (Xeon CPU_MODEL, attempt ATTEMPT_N) | The build and both test jobs pass. test-host: N_PASS of N_TOTAL tests pass. |

What the table says:

- The kill switch skips the QK and PV precision cases with "AMX unavailable on this host". The test process exits successfully.
- The dispatch test uses fake kernels and passes `TRON_AMX_DISPATCH` itself. It and the transpose case need no AMX CPU.

Clang-format 19.1.7 and `git diff --check` pass at the head.

At the measured commit, the four-head pack and QK instruction listings match the merge base. PV adds one instruction to form its per-thread scratch address. The remaining instruction names match, with different registers and offsets. [`glimext-20261018/preservation2.txt`]

### Token identity

Each configuration generates 256 tokens, numbered from 1, for one user at temperature 0 with seed 1 and deterministic reductions. Here `run` is the measured commit, `repeat` repeats it, `base` is the merge base and `disabled` uses the measured commit with the kill switch. [`glimext-20261018/identity.txt`]

| Model / layout / attention / prompt tokens | Run vs repeat | Run vs base | Disabled vs base |
|---|---|---|---|
| llama-3.1-8b / tp2 / CPU / 1024 | identical, 256 of 256 tokens | identical, 256 of 256 tokens | first difference at generated token 13 |
| qwen3-4b / tp2 / FPGA / 1024 | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| gpt-oss-120b / tp4 / FPGA / 1024 | identical, 256 of 256 tokens | identical, 256 of 256 tokens | identical, 256 of 256 tokens |
| Glimmer / tp2 / FPGA / 1024 | identical, 256 of 256 tokens | first difference at generated token 6 | identical, 256 of 256 tokens |
| Glimmer / tp2 / CPU / 1024 | identical, 256 of 256 tokens | first difference at generated token 54 | identical, 256 of 256 tokens |
| Glimmer / tp2 / FPGA / 2048 | identical, 256 of 256 tokens | first difference at generated token 13 | identical, 256 of 256 tokens |
| Glimmer / tp4 / FPGA / 1024 | identical, 256 of 256 tokens | first difference at generated token 31 | identical, 256 of 256 tokens |

What the table says:

- Required matches are run/repeat for every row, run/base for llama-3.1-8b, qwen3-4b and gpt-oss-120b, and disabled/base for Glimmer. Every required comparison matches. Other pairs are informational.
- Glimmer's enabled path differs from the merge base. Measured score differences for the tp2 CPU/1024-token case are recorded in [#4444](https://github.com/positron-ai/tron/issues/4444#issuecomment-6255615621).
- **Insufficient data:** the other divergent cells lack comparisons of the gaps between the highest token scores.
- The disabled llama run uses AVX instead of AMX and differs from the AMX-enabled base. This comparison is tracked in [#4444](https://github.com/positron-ai/tron/issues/4444#issuecomment-6255615621).

### Performance

The paired t statistic compares the mean paired difference with its uncertainty. Each band below is twice the larger of the two configurations' standard deviations. The check gates losses only: a configuration fails when its decode loss or its prefill increase exceeds the band. A gain beyond the band is reported, but it is claimed as an effect of this PR only where PR code runs on that path. Paired t values do not override this rule. All differences use unrounded means.

**Production attention.** The measured commit runs 8 users with 2 repetitions per configuration. Full CPU-attention and prefill rows are in `glimmer-20261016/rt-results.txt`.

| Glimmer layout / prompt tokens | Disabled TPS (sd) | Enabled TPS (sd) | Delta TPS (%) | Band TPS |
|---|---:|---:|---:|---:|
| tp2 / 1024 | 38.42 (0.003) | 41.89 (0.004) | +3.47 (+9.0%) | 0.01 |
| tp2 / 2048 | 33.11 (0.032) | 38.15 (0.046) | +5.04 (+15.2%) | 0.09 |
| tp4 / 1024 | 60.44 (0.168) | 63.08 (0.190) | +2.64 (+4.4%) | 0.38 |
| tp4 / 2048 | 54.21 (0.018) | 59.74 (0.105) | +5.53 (+10.2%) | 0.21 |

What the table says:

- Every listed decode gain exceeds its band.
- Prefill is 0.6–8.7% shorter.
- CPU-attention decode gains are 6.1–21.2% for Glimmer and 5.2% for llama-3.1-8b against the kill switch.
- At prompt 1024, AMX scores 72.1% of key tokens, FPGA 24.9% and AVX 2.9%. [`attn-stats-compare.md`]
- Mean busy time per attention worker per model execution falls from 5.3 ms to 3.1 ms in the tp2 run. [`attn-stats-compare.md`]

**Nightly configuration.** The whole-machine comparison uses Glimmer tp4, 8 users, a 1024-token prompt and 1,536 generated tokens, with 3 interleaved passes per configuration. The bands below apply the same rule to the saved pass results. [`glimci-20261017/summary.md`]

| Configuration | TPS (sd) | TTFT ms (sd) |
|---|---:|---:|
| [Nightly reference](https://github.com/positron-ai/systems_test/actions/runs/38999609242), 1 pass | 78.69 (—) | 3696 (—) |
| Nightly package rerun | 78.69 (0.13) | 3780 (14.42) |
| Measured commit, disabled | 78.60 (0.25) | 3781 (8.13) |
| Measured commit, enabled | 82.27 (0.28) | 3651 (9.59) |

| Against nightly package | Delta TPS / band | Delta TTFT ms / band |
|---|---:|---:|
| Disabled | −0.09 / 0.50, inside | +0.77 / 28.85, inside |
| Enabled | +3.58 / 0.56, beyond | −128.98 / 28.85, beyond |

What the table says:

- Enabled AMX improves decode by 4.6% against the nightly package (`t=33.1`).
- Enabled AMX reduces TTFT by 3.4%.
- Disabled AMX differs by −0.1% (`t=−0.4`), within its band.
- A 20-second hardware-counter probe records 5.52–5.56 billion AMX busy cycles in enabled runs and zero in the other configurations.

**Merge-base comparison.** These runs use 8 users and 4 paired repetitions, or 8 for llama-3.1-8b at prompt 8192. Llama uses CPU attention, and other rows use default FPGA attention. Two further rows, both inside their bands, are in the result file. [`glimext-20261018/rt-results.txt`]

| Model / layout / prompt tokens | Base TPS (sd) | Measured TPS (sd) | Delta TPS / band | Prefill change |
|---|---:|---:|---:|---:|
| llama-3.1-8b / tp2 / 1024 | 119.22 (0.11) | 119.35 (0.14) | +0.13 / 0.27, inside | +0.1% |
| qwen3-4b / tp2 / 1024 | 133.61 (0.16) | 134.17 (0.15) | +0.56 / 0.33, beyond, no PR code on path | +0.03% |
| gpt-oss-120b / tp4 / 1024 | 96.77 (1.47) | 97.05 (0.35) | +0.28 / 2.93, inside | −0.2% |
| llama-3.1-8b / tp2 / 8192 | 25.31 (0.06) | 25.24 (0.03) | −0.07 / 0.12, inside | −1.3% |
| Glimmer / tp2 / 1024 | 38.34 (0.02) | 41.92 (0.05) | +3.58 / 0.10, beyond | −2.8% |
| Glimmer / tp2 / 2048 | 33.01 (0.02) | 38.17 (0.05) | +5.16 / 0.10, beyond | −8.9% |
| Glimmer / tp4 / 1024 | 60.46 (0.07) | 63.07 (0.09) | +2.61 / 0.19, beyond | −0.5% |

What the table says:

- Glimmer gains 4.3–15.6% decode TPS.
- Glimmer has 0.5–8.9% shorter prefill.
- Other tested models satisfy the stated decision rule.
- The qwen3-4b / tp2 / 1024 row runs no PR code: the AMX kernel scores 0 key tokens in both configurations (`exit-reports.txt`). Its +0.56 TPS appears in all four repetitions. It is an offset between the two binaries, cause unknown. The Glimmer decode gains are 4 to 9 times that offset.
- The llama 8192-token decode change is −0.3% (`t=−3.7`), within the 0.12 TPS band. No further investigation of this difference is required for this PR.

## Open items

Not measured at the head: throughput [Verification]. Not refreshed: the `config/test-benchmarks.json` rows of `t_amx_dispatch_dtype`.


