## Short version

This PR adds faster CPU kernels for the prompt processing of the model Qwen3.5 4B, and counters that time its GatedDeltaNet (GDN) layers. On one test server the time to first token falls by 25 to 39 %. Token generation with 8 users and long prompts gets 18 to 22 % faster.

## Background

- The model has 24 GDN layers and 8 attention layers. A GDN layer keeps a 128 x 128 FP32 state matrix per value head. Its recurrence reads the matrix twice and writes it once, for every token.
- A prompt chain is known before it runs. So the write pass of one token can also be the read pass of the next token. Note [GatedDeltaNet chain recurrence] in `h/tron/kernels/gated_delta_net.hpp` gives the loop.
- 32 tokens can also be applied in a closed form with matrix products, which AMX computes. Note [AMX GatedDeltaNet block kernel] in `h/tron/kernels/amx_gdn_iface.hpp` gives the algebra.
- At the base, the AMX attention kernels serve only heads of 128 values. This model has heads of 256 values, so its attention runs on AVX-512 there. Note [AMX attention dispatch] in `h/tron/kernels/amx_attn_iface.hpp` describes both shapes.
- At the base only a trace can time GDN. Note [GDN path stats] in `h/tron/models/gdn_stats.hpp` describes the counters.

## Words used here

| Term | Meaning |
|---|---|
| AMX | Intel Advanced Matrix Extensions, the tile-matrix instruction set |
| AVX-512 | the 512-bit vector instruction set. The CPU kernels of the base use it |
| bf16, bf16 step | bf16 is a 16-bit floating-point format with 8 significant bits. A bf16 step is the distance between two neighbouring bf16 values, 0.125 for values from 16 to 32 |
| chain | the consecutive tokens of one sequence in one pass |
| token kernel, chain kernel, block kernel | three routines for the GDN recurrence: one token per call (the code of the base), a run of tokens with the bits of the token kernel, and 32 tokens at once with AMX |
| kill switch | `TRON_AMX_DISABLE=1`. No AMX kernel runs |
| GDN switch | `TRON_AMX_GDN_DISABLE=1`. Only the AMX block kernel of GDN is off |
| `base` | the binary of `0d69ef3ce8`: the counters, and the kernels of the PR base |
| `p0` | the head binary with the kill switch set: chain kernel, AVX-512 attention |
| `a0`, `a` | the binary of `775bba7661` with the GDN switch set (chain kernel) and with no switch (block kernel). Attention runs on AVX-512 |
| `b`, `ab` | the head binary with the GDN switch set (chain kernel, AMX attention) and with no switch (block kernel, AMX attention) |

## How to review this PR

**Does the chain kernel give the bytes of the per-token loop for every chain, start position and head width?**

- `h/tron/kernels/gated_delta_net.hpp`: the joined loop `gdn_recurrence_slice`, and the conversion between the stored state and the slice layout.
- `h/tron/models/gdn_rolling_executor.hpp`: `advance()` cuts a chain into windows of at most 32 tokens. `step()` keeps the token kernel for a chain that advances in place.
- `h/tron/models/gdn_execution.hpp`: `run_gdn_operation` advances a chain of 1 token in place with `step()`, and a longer chain in a working copy with `advance()`.
- Claim: with the block kernel off, outputs and stored state are equal byte for byte.
- Verification: the `t_gated_delta_net` cases "advance gives the bytes of step at the Qwen matrix shape" and "... for narrower value heads". Also the `p0` and `a0` rows of [Verification].

**Is the result of the AMX block kernel close enough, and does a refused block leave the state unchanged?**

- `src/tron/kernels/amx_gdn.cpp`: the split of an FP32 value into 3 bf16 pieces, the two refusal rules, and the scope that sets FTZ and DAZ in MXCSR.
- `h/tron/models/gdn_rolling_executor.hpp`: `advance_window_with_block_kernel` gives a refused value head to the chain kernel.
- Claim: for the 8 input families of the test, the output error against a float64 computation is at most 2 times that of the chain kernel. The state error is at most 4 times. A bench outside this PR measures 0.37 to 0.61 and 0.48 to 1.30 times.
- Claim: a refused block leaves the state untouched.
- Verification: the cases of `t/t_amx_gdn_numerics.cpp` and the `t_gated_delta_net` case "advance gives a refused block to the chain kernel". The model level is Open: "Numerics of the block kernel" in [Open items].

**Does the dispatch take the 256-wide kernels only for the 256 x 4 shape, and do the 128-wide kernels keep their code?**

- `h/tron/models/self_attention.hpp`: the gates `amx_serves_128x4` and `amx_serves_256x4`, and the size of the packed-query slot per model.
- `src/tron/kernels/amx_attn.cpp`: namespace `amx_attn_h256g4`. The code of the three 128-wide kernels has no change.
- Two lines of the shared dense-page path change for both shapes: the packed-query array only grows, and the buffer `scratch` is no longer zero-filled.
- Claim: a model with another shape keeps its path, and the kill switch turns both shapes off.
- Verification: the QK and PV error-band cases of `t_amx_numerics` for both shapes, and `t_amx_dispatch_dtype`. Model runs: "Coverage" in [Open items].

## Verification

All results come from delphi-3b35 (an Intel Xeon 6962P server), 2026-11-22 UTC, at the head `882e5322f1` and its two parent commits on the base `72e1191804`. The builds use clang 19, the preset `native` (RelWithDebInfo), `BUILD_INGEST_MODELS=ON` and `TRON_AMX_DISPATCH=ON`, except in the last row of the first table. The performance and token runs use builds of an earlier version of the same commits, which differs only in comments, tests and two README files. Those runs use the binaries `base`, `p0`, `a0`, `a`, `b` and `ab` with the model `ingested-qwen-3.5-4b-tp4`, attention on the CPU, and both counter sets on. GitHub runs only the lint and CI-machinery jobs for this draft, because it has no `Run CI` label.

### Builds and tests

Results are assertions / test cases. Every listed run passes.

| Configuration at the head | Result |
|---|---|
|AMX dispatch on|`t_gated_delta_net` 109,130 / 50; `t_amx_numerics` 11,672 / 12; `t_amx_dispatch_dtype` 4,730 / 1; `t_llama_unit` 265,523 / 74; `t_tronstats_convention` 1,420 / 30|
|AMX dispatch on, kill switch set|`t_gated_delta_net` 109,130 / 50; `t_amx_numerics` 6,162 / 12|
|AMX dispatch on, GDN switch set|`t_gated_delta_net` 109,130 / 50; `t_amx_numerics` 11,284 / 12|
|AMX dispatch off, build type Debug|`t_gated_delta_net` 109,130 / 50; `t_amx_numerics` 1 / 1; `t_amx_dispatch_dtype` 1 / 1|

- The two parent commits pass the same five test programs.
- With a switch set, `t_amx_numerics` skips the cases of the kernels that are off: 9 under the kill switch and 5 under the GDN switch. Without AMX dispatch, `t_amx_numerics` and `t_amx_dispatch_dtype` have one placeholder case each.
- `clang-format` 19.1.7 reports no difference in the 16 changed C++ files. `git diff --check` and `make lint-notes` are clean. The Lint job of this draft passes.

### Token identity

One user, a fixed prompt, temperature 0, `--pay-for-determinism`, 256 generated tokens. Every row compares with `base`.

| Prompt (tokens) | Binary | Rule | Result |
|---|---|---|---|
|1,024|PR base `72e1191804`|must be identical|identical, 256 of 256 tokens|
|1,024|`base`, run again|must be identical|identical, 256 of 256 tokens|
|1,024|`p0`, `a0`|must be identical|identical, 256 of 256 tokens|
|1,024|`a`|informational|first difference at generated token 185|
|1,024|`b`|informational|first difference at generated token 1|
|1,024|`ab`|informational|first difference at generated token 185|
|4,096|PR base `72e1191804`|must be identical|identical, 256 of 256 tokens|
|4,096|`p0`, `a0`|must be identical|identical, 256 of 256 tokens|
|4,096|`a`, `b`, `ab`|informational|identical, 256 of 256 tokens|

What the table says:

- Every pair that must be identical is identical. So the counters and the chain kernel change no generated token.
- `b` differs at an exact tie. At generated token 1, `base` scores 16.375 for two token ids, and `b` scores 16.25 for one of them: one bf16 step.
- `ab` gives the tokens of `a`, and it keeps the tie of `base` at generated token 1.
- `a` differs after 185 equal tokens, and not at a tie. At generated token 0 its scores are within 1 bf16 step of `base`.
- The best score of `a` then moves away by up to 10 bf16 steps. At generated token 185 the best token of `base` leads by 8 bf16 steps, and `a` takes another token. Decode takes the same kernels in both binaries.
- A second run of `a`, `b` and `ab` gives the tokens of its first run. In the 36 performance runs of `a` and `ab` the block kernel refuses no block.

### Performance

- 6 cells, 3 repetitions per binary and cell, 256 generated tokens per user. The counter values in the text are medians of 3 runs.
- Before every run the 56 CPUs of the test are at most 0.1 % busy. The other socket of the server is 42 % busy with other users' jobs.
- A change counts when it is beyond the band: twice the larger standard deviation of the two binaries. The tables mark the other changes "inside". A standard deviation is at most 0.7 % of the time to first token and 0.9 % of the decode speed.

Time to first token in s, mean of 3, with the change against `base` in percent:

| Cell | `base` | `p0` | `a` | `b` | `ab` |
|---|---|---|---|---|---|
|1 user, prompt 1,024|0.385|0.331 (-13.9)|0.293 (-23.9)|0.322 (-16.3)|0.285 (-26.0)|
|1 user, prompt 4,096|1.903|1.690 (-11.2)|1.537 (-19.3)|1.442 (-24.2)|1.292 (-32.1)|
|1 user, prompt 8,192|4.707|4.285 (-9.0)|3.985 (-15.3)|3.206 (-31.9)|2.906 (-38.3)|
|8 users, prompt 1,024|2.901|2.492 (-14.1)|2.184 (-24.7)|2.476 (-14.7)|2.172 (-25.1)|
|8 users, prompt 4,096|14.266|12.616 (-11.6)|11.387 (-20.2)|10.896 (-23.6)|9.677 (-32.2)|
|8 users, prompt 8,192|35.717|32.416 (-9.2)|29.938 (-16.2)|24.207 (-32.2)|21.794 (-39.0)|

What the table says:

- Every change is beyond the band. The time to first token falls by 9.0 to 14.1 % with the chain kernel (`p0`) and by 15.3 to 24.7 % with the block kernel (`a`). With both AMX kernels (`ab`) it falls by 25.1 to 39.0 %.
- One GDN step (one token of one key head) takes 6.08 us in `base`, 4.01 us in `p0` and 2.56 us in `a`. A prefill pass gets shorter by the time that its GDN layers save.
- From `p0` to `b` the attention busy time of a prefill pass gets 1.10 to 2.27 times shorter. It includes the join wait: the time a thread waits for the other attention threads.
- The low end is 8 users, prompt 1,024. There the join wait rises from 3.3 to 10.9 ms per pass, and the change from `p0` to `b` is inside the band (-0.6 %).

Decode speed per user in tok/s, mean of 3, with the change against `base` in percent:

| Cell | `base` | `b` | `ab` |
|---|---|---|---|
|1 user, prompt 1,024|273.0|270.9 (-0.8, inside)|273.0 (0.0, inside)|
|1 user, prompt 4,096|253.7|255.6 (+0.8, inside)|256.2 (+1.0, inside)|
|1 user, prompt 8,192|232.8|238.1 (+2.3)|238.7 (+2.5)|
|8 users, prompt 1,024|121.0|124.7 (+3.1)|125.1 (+3.4)|
|8 users, prompt 4,096|77.9|91.8 (+17.8)|91.9 (+18.0)|
|8 users, prompt 8,192|56.4|69.0 (+22.2)|69.1 (+22.4)|

What the table says:

- The GDN kernels alone (`p0`, `a`, not in the table) change decode by -0.7 to +0.5 %, inside the band in every cell.
- With the attention kernels decode gets 18 to 22 % faster with 8 users and prompts of 4,096 tokens or more. There, from `p0` to `b`, the attention busy time of a decode step gets 1.48 to 1.55 times shorter. 45 to 49 % of that fall is a shorter join wait.
- In control runs on 3 cells, `TRON_GDN_STATS=1` changes the time to first token by -0.2 to +0.3 % and decode by -0.5 to 0.0 %. The decode change is beyond the band in 1 cell (1 user, prompt 4,096: -0.5 %). With the counters off, `0d69ef3ce8` is within 0.4 % of the PR base.

## Open items

**Numerics of the block kernel. Reviewers decide.** The difference of `a` against `base` grows during decode [Verification]. No measurement compares the GDN states of the two binaries after the prompt. A score dump for more prompts would show how often such a difference grows. The owners of the GDN code decide whether the block kernel is on by default.

**One PR or a stack. Reviewers decide.** The PR has three commits: the counters (`0d69ef3ce8`), the two GDN kernels (`775bba7661`) and the attention kernels (`882e5322f1`). The diff has 4,767 added lines. It can become a stack of three PRs, or of four with one PR per GDN kernel.

**Coverage. Reviewers decide which checks this PR must add.**

- The default PR pipeline (GCP Nix) builds the tests with `TRON_AMX_DISPATCH` off. So it compiles neither the AMX kernels nor their test cases. The legacy workflow `cmake-single-platform.yml` builds with the option on.
- No test sets the GDN switch itself, no test runs the counters through a generated model, and no 128-wide model ran at this head.

**Base.** The model is not on `main`, so this PR is a draft on top of PR #3696. Other open PRs of that stack change the GDN code, and PR #5022 changes the same kernel calls in `h/tron/models/self_attention.hpp`. The author rebases this PR when one of them merges below it.

**Changelog and test timing record.** `main` asks for a `changelog.d` fragment for a performance change, and the base of this PR is older than that rule. `config/test-benchmarks.json` is not refreshed for `t_gated_delta_net` and `t_amx_numerics`. The author adds both before the PR leaves the draft state.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
