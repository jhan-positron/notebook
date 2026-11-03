## Short version

The attention planner now prices a page visit by the path that scores it (AMX dense 1, AVX full page 3, AVX partial page 3) and, when a KV head has at least 2 pending pages per worker of its block, places the head's ready pages and its pending pages in two separate walks. On Muse Glimmer 30B at tp2 with prompt 2048, the prompt parse is 3.3 % shorter and decode 1.9 % faster per user. The other Glimmer cells gain 0 to 1.1 % decode, and llama-3.1-8b loses 0.4 % decode. The change is stacked on PR #5015.

## Background

The attention planner (`finish_sw_plan` in `model.hpp`) assigns the pages of each KV head to the workers of that head's block by cumulative work. Its work unit is one visit (one query token against one page) whatever the path, and one cumulative sum covers the ready pages (written in earlier forwards) and then the pending pages (written in this forward). So a head's pending pages land on the last one or two workers of its block. The join of a head cannot start until every section of that head is done (`run_joins` polls `sections_left`), so the slowest worker sets the layer time.

With the AMX kernels serving Glimmer (PR #5015), an AMX dense visit costs about 1.7 us and an AVX visit about 5 to 7 us, so the unit cost is wrong by about 3x, and the per-worker attention counters of the prompt forwards show the pending-page workers as the slowest (tp2, prompt 2048: 5.9 ms compute per job on the pending worker against a 3.6 ms mean, join wait share 45 %).

Note [Path-weighted attention plan] in `common.hpp` states the weights and the rule.

## Words used here

| Term | Meaning |
|---|---|
| tron | the inference program under test |
| runtron | tron's command-line tool. It runs one model with N users and prints per-user rates |
| AMX, AVX | two Intel CPU instruction sets. The AMX kernel scores dense pages, the AVX loop scores the rest |
| KV page | a 64-token block of the key/value cache. A visit is one query token scored against one page |
| ready page, pending page | a page written in an earlier forward, a page written in this forward |
| block | the workers assigned to one KV head |
| kill switch | `TRON_PLAN_WEIGHTED_DISABLE=1`. Restores the unit-cost single-walk plan |
| Muse Glimmer 30B | the production ingested model (tp2 and tp4 variants). 52 layers, 2 KV heads, 16 query heads per KV head |
| delphi-3bda | the Intel Xeon 6 test machine with 8 FPGA cards; "our half" is socket 1 |

## How to review this PR

**Does the planner's page classification equal the kernel's dispatch?**

- `h/tron/models/self_attention.hpp`: `is_dense_amx_page` is now a namespace-scope template used by both the AMX call site and the planner. Its conditions are unchanged.
- `h/tron/models/model.hpp`, `estimate_work`: a visit counts as AMX dense when the predicate holds and AMX is on (`amx_on` = eligible and available), as AVX full when the visit scores all 64 tokens through more than one range, else as AVX partial. The pending pass uses the same gate as the ready pass.
- Verification: `t_llama_unit` case "attention plan weights pages by path and spreads pending pages" (whole pages dense, the diagonal page partial except the last query, AMX off makes every page AVX full, work() equals the named weights times the counts).

**Does the two-walk placement keep every page assigned once and inside its head's block, and fall back to the old walk below the threshold?**

- `model.hpp`, `finish_sw_plan`: `place_pages(passes, catch_up)`. The weighted path calls it once per pass with the cursor catching up to the page centre. Below `pending_pages_per_worker_for_split` (2) and under the kill switch it calls it once over both passes with one step per page, the old walk.
- Verification: `t_llama_unit` case "attention plan keeps a KV head's pending pages inside its worker block" (shapes at 0.25, 0.8 and 4.0 pending pages per worker, with and without ready work): every pending section sits on a worker of its head's block that also holds the head's ready pages, section counts add up, and below the threshold the pending pages sit on the block's last worker.

**Is the threshold justified?**

- The constant's comment cites the measurement in [Verification]: without the threshold, the separate walk raised the sum of worker compute in the prompt forwards by 2.6 % at tp4 (20 workers per block, 0.8 pending pages per worker) and cost 2.1 % of the prompt parse, while at 3.2 pending pages per worker it saved 4.4 %.
- Open: the value 2 is the lowest measured ratio that gains. No cell between 0.8 and 3.2 was measured. Reviewers decide whether a cell at about 1.6 (tp2, prompt 1024, 16 users) is needed before merging.

## Verification

Every result below comes from head 7ce44251c0 (branch `jhan-amx-kvmul16-planner`, base `jhan-amx-kvmul16` 5061623a34 = PR #5015) on delphi-3bda, our half, on 2026-10-17, built in a plain shell with the host clang 19.1.7 (preset `native`, RelWithDebInfo, `-DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON`). The performance runs use the binary of f2c75d260b, which differs from the head only in one test file. One binary, two arms: the weighted plan (default) and the kill switch. runtron, 8 users, 256 generated tokens, 3 repetitions, FPGA attention on Glimmer's 13 full layers (the production mode), CPU attention for llama. Raw results: result set glimpl-20261017 (rt-results.txt, attn-stats-compare.md, results.json). The threshold-less measurement is result set glimpl-20261017-r1.

### Builds and tests

| Configuration | Built | Tests (assertions / cases) |
|---|---|---|
| AMX on | runtron, t_amx_numerics, t_amx_dispatch_dtype, t_llama_unit | t_amx_numerics 17,424 / 4 pass. t_amx_dispatch_dtype 5,756 / 1 pass. t_llama_unit 265,621 / 69 pass (two new planner cases) |
| AMX off (kill switch `TRON_AMX_DISABLE=1`) | same binaries | t_amx_numerics 4,110 / 4 pass, 2 sections skipped with "AMX unavailable on this host" |

clang-format (19.1.7, dry run) is clean on every touched file. The format and whitespace hooks run in CI. No mutation check was run.

### Token identity

Not measured. Section boundaries change the fold order of the join partials, which is bf16 rounding order. The pending measurement is in [Open items].

### Performance

Decision rule: a difference counts when it exceeds a band of twice the larger of the two arms' sample standard deviations over the 3 repetitions. Decode TPS per user is the mean over the 8 users' "average tok/s" lines, then over repetitions. Prefill time is the slowest user's "Parsing the prompt took" value.

| Cell | Decode TPS per user, kill switch | weighted plan | Difference | Band | Prefill s, kill switch | weighted plan | Difference | Band |
|---|---|---|---|---|---|---|---|---|
| Glimmer tp2, prompt 2048 | 38.18 | 38.90 | +1.9 % | 0.12 | 30.946 | 29.925 | -3.3 % | 0.070 |
| Glimmer tp2, prompt 1024 | 41.91 | 42.38 | +1.1 % | 0.12 | 14.856 | 14.866 | +0.1 % (inside) | 0.026 |
| Glimmer tp4, prompt 1024 | 63.04 | 63.29 | +0.4 % (inside) | 0.27 | 8.295 | 8.264 | -0.4 % | 0.018 |
| llama-3.1-8b tp2, prompt 1024 | 119.66 | 119.18 | -0.4 % | 0.30 | 3.408 | 3.406 | -0.0 % (inside) | 0.002 |

Without the threshold (result set glimpl-20261017-r1, same cells, 3 repetitions): Glimmer tp2 prompt 2048 prefill -4.4 % and decode +1.9 %, tp2 prompt 1024 prefill +0.4 % and decode +1.7 %, tp4 prompt 1024 prefill +2.1 % and decode -0.8 %, llama unchanged.

What the tables say: at tp2 with prompt 2048 the attention counters show the join wait share of the prompt forwards falling from 45 % to 33 % and the busy time per prompt job from 6.95 ms to 5.76 ms, which is the balance gain the design predicts. At the other Glimmer cells the threshold keeps the old placement, and the weights alone move decode by 0 to 1.1 %. llama-3.1-8b loses 0.4 % decode, beyond its band of 0.30 tokens/s. The weights change its plan too (its pages are AMX dense and AVX partial in the same ratio as Glimmer's), and the cause is not isolated.

## Open items

**llama-3.1-8b decode -0.4 %.** Beyond its band. The measurement that isolates it is the same cell with the weights disabled and the walk unchanged (a build with unit weights). Reviewers decide whether this loss blocks the merge.

**Token identity between the arms.** Not measured. The measurement is runtron with pay-for-determinism, temperature 0, CPU attention and one prompt, weighted plan against the kill switch, on Glimmer tp2 at prompt 2048. A difference is expected to be within bf16 rounding order, and any stored expected logits that depend on the fold order need regeneration.

**Threshold value.** See the third question in [How to review this PR]. Reviewers decide.

## The stack

PR #5015 makes the AMX kernels serve Glimmer's shape. This PR is its follow-up and is based on that branch.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #5015 | `jhan-amx-kvmul16` on `main` | AMX kernels for kv_mul 16 | ready for review |
| 2 | this PR | `jhan-amx-kvmul16-planner` on `jhan-amx-kvmul16` | path-weighted plan, separate pending walk above a threshold | draft until #5015 merges |

Nothing stays disabled. Each PR is complete on its own.
