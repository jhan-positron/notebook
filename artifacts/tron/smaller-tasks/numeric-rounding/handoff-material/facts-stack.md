# Facts: the Qwen3.5 PR stack and the bases our GDN work can use

Read on 2026-11-23 between 18:30 and 19:30 UTC.
The local clone was fetched at 19:16 UTC.
GitHub main was f454423b09 at 19:27 UTC [E1].

## Short version

- The model's branch (head of PR #3696, commit 72e1191804) is a copy of the stack as it was on 2026-11-17: 12 open PRs lie between it and main, and 7 of its 21 commits are already on main in a newer form.
- No single base has both today's GDN code and the model: main (f454423b09) and the head of PR #3221 (127a662083) do not register Qwen3.5 4B, and the model's branch holds the old GDN code.
- Our three parts (counters, Part 0, Part A) apply unchanged only to the model's branch; the head of PR #3221 needs a port by hand, and main lacks the code that runs the GDN kernel inside a model.

## Words used here

- **tron**: the C++ inference program, repository positron-ai/tron.
- **GDN (GatedDeltaNet)**: a recurrent layer type of the model Qwen3.5 4B.
- **main**: the default branch. Today its head is f454423b09.
- **the model's branch**: the head branch of PR #3696 ("Register Qwen3.5 4B"), commit 72e1191804.
- **base / head**: a PR asks to merge its head branch into its base branch.
- **stack**: PRs chained so that the head of one is the base of the next.
- **squash merge**: GitHub joins all commits of a PR into one new commit on main. The new commit has a new id. Its subject ends with "(#N)".
- **patch-id**: a hash of the diff of a commit (`git patch-id --stable`). Two commits with one patch-id make the same change.
- **pre-image of a hunk**: the context lines and the removed lines of one diff hunk. The hunk can apply where this block of lines exists.
- **token kernel**: the function `gdn_recurrence`. It advances the GDN state by one token.
- **executor**: the class `gdn_rolling_executor`. For one token it runs the convolution, the token kernel and the output step. It also binds the state checkpoint.
- **chain**: the tokens of one sequence that one forward pass must advance in order.
- **key head, value head**: the GDN layer has `n_key_heads` query/key heads and `n_value_heads` value heads. Each key head serves `n_value_heads / n_key_heads` value heads.
- **head group**: `key_heads_per_group` key heads plus their value heads. One worker thread advances one head group.
- **work item**: the unit of work that one worker takes in `run_gdn_operation`.
- **generator**: `ingest/src/TronCpp.hs`, the Haskell program that writes the C++ plugin of a model.
- **plugin**: the generated C++ code of one model.
- **counters**: our commit 0d69ef3ce8 (GDN path statistics, `gdn_stats.hpp`).
- **Part 0**: the AVX-512 chain kernel `gdn_recurrence_chain`. **Part A**: the AMX block kernel `amx_gdn_k128v128`. Both are in our commit 775bba7661.
- **Part B**: our commit 882e5322f1 (AMX attention kernels for 256-wide heads).
- **AVX-512, AMX**: CPU instruction sets.
- **bf16**: a 16-bit floating-point format.
- **draft**: a PR that its author has marked as not ready to merge.
- **CHANGES_REQUESTED, APPROVED**: the review decision that GitHub shows for a PR.

Every head branch of the family carries the prefix `rbjarnason/`. The tables below omit the prefix.

## 1. The stack today

### Counts

- GitHub has 668 open PRs in the repository [E2].
- 41 of them have a head branch that starts with `rbjarnason/qwen35` [E2].
- 31 of the 41 are drafts [E2].
- The command in the task text uses `--limit 200`. That limit returns only 4 of the 41. Use `--limit 1000` [E2].

### The chain from main up to PR #3696

```
main f454423b09
 |
#3206 - #5345 -+- #3205 - #3221 -+- #5023 - #5486 - #5024
               |                 |
               +- #5346          +- #5571 (draft)

#5024 - #3689 - #3690 - #3692 - #3694 - #3695 - #3696
```

Each PR in the table has the PR above it as its base [E2].

| Step | PR | Title | Head branch | Head commit | Draft | Review | Sits on today's main |
|---|---|---|---|---|---|---|---|
| 0 | | main | main | f454423b09 | | | |
| 1 | #3206 | Represent pending recurrent sequence endpoints | qwen35-25-scheduler-gdn-state | 7f9011ffb7 | no | CHANGES_REQUESTED | yes |
| 2 | #5345 | Schedule recurrent continuations in the full scheduler | qwen35-recurrent-scheduling | e175e34705 | no | CHANGES_REQUESTED | yes |
| 3 | #3205 | Activate generated recurrent GDN execution | qwen35-24-hybrid-attn-integration | 1f705f0140 | no | CHANGES_REQUESTED | yes |
| 4 | **#3221** | Parallelize GatedDeltaNet operations across key-head groups | qwen35-37-gdn-head-parallel | 127a662083 | no | CHANGES_REQUESTED | yes |
| 5 | #5023 | Resume GatedDeltaNet state from cached prefixes | qwen35-38a-gdn-prefix-reuse | 1af8baacf6 | no | CHANGES_REQUESTED | yes |
| 6 | #5486 | Export GatedDeltaNet state statistics from Rinzler | qwen35-38ab-gdn-state-stats | fc79d3b5c0 | no | APPROVED | yes |
| 7 | #5024 | Keep GatedDeltaNet state at chat conversation ends | qwen35-38b-gdn-conversation-ends | 3c888791c9 | no | CHANGES_REQUESTED | yes |
| 8 | #3689 | Infer Cat result shapes during equality saturation | qwen35-infer-cat-shapes | 5326fa4fd7 | yes | CHANGES_REQUESTED | **no** |
| 9 | #3690 | Lower arbitrary-arity last-axis Cat to row copies | qwen35-lower-last-axis-cat | 00202eb454 | yes | CHANGES_REQUESTED | no |
| 10 | #3692 | Lower proper-prefix rank-4 RoPE | qwen35-lower-partial-head-rope | 4e34e13e00 | yes | CHANGES_REQUESTED | no |
| 11 | #3694 | Normalize Qwen text-only rotary export | qwen35-normalize-text-rope-export | bd9f93bbaa | yes | CHANGES_REQUESTED | no |
| 12 | #3695 | Normalize singleton-axis checkpoint storage by shape | qwen35-normalize-conv-weight-storage | 451ba42be4 | yes | CHANGES_REQUESTED | no |
| 13 | **#3696** | Register Qwen3.5 4B | qwen35-native-4b-registry | 72e1191804 | no | APPROVED | no |

Side branches of this chain:

- **PR #5571** (draft, no review decision) has PR #3221 as its base. Its head is 69cc70fae0, two commits on 127a662083 [E2][E3].
- PR #5346 ("Keep hardware attention correct in recurrent passes", head c3b51adf66) has PR #5345 as its base. It is not on the path to PR #3696 any more [E2][E3].
- Above PR #3696: PR #3207 (draft), and PR #4728 then #4790 then #5274 (drafts, the 27B, 9B and 0.8B models) [E2].

### Answers

- **12 open PRs sit between main and PR #3696.** They are steps 1 to 12 of the table. 7 of them are not drafts (steps 1 to 7). 5 are drafts (steps 8 to 12).
- **The lowest open PR is #3206.** Its base is main. It has 1 commit, 875 added lines and 1 deleted line in 4 files. GitHub reports it as mergeable and blocked (review decision CHANGES_REQUESTED) [E4].
- PR #3221 is step 4. Three open PRs sit between main and it (#3206, #5345, #3205).

### The chain is broken between step 7 and step 8

- Steps 1 to 7 sit on today's main. Each of their heads is a descendant of f454423b09 [E3].
- The head commits of steps 1 to 5 carry the date 2026-11-23 12:47 -0500, so they were rewritten today [E3].
- Steps 8 to 13 were not rewritten. Their head commits are the commits of 2026-11-17, on top of the main commit 54476c6581 of 2026-11-16 [E3][E6].
- The head of step 8 (5326fa4fd7) is not a descendant of the head of step 7 (3c888791c9) [E3].
- GitHub reports PR #3689 (step 8) as CONFLICTING. It shows 16 commits and 10,623 added lines for it, because its branch still carries the old copies of the lower PRs [E4].
- So the head of PR #3696 does not contain the present heads of the PRs below it.

### Other open PRs of the family (not on the path)

- Three PRs have main as base and no child: #3171 (draft), #3439 (draft), #3456 [E2].
- 19 draft PRs form a second tree. Its root base is the branch `qwen35-force-generate-stop-tokens`. PR #5005 owned that branch and was closed without merge on 2026-11-20 [E2][E5]. The tree holds #3215, #3326, #3217, #3329, #3218, #3330, #3219, #3434, #3457, #3459, #3462, #3463, #5250, #3472, #3654, #5286, #5287, #5300, #5301.

### PRs of the family merged since 2026-11-15

11 PRs were merged. All had main as base [E5].

| PR | Title | Merged (UTC) | Commit on main |
|---|---|---|---|
| #3178 | Add GDN depthwise convolution | 2026-11-18 17:43 | ab34e3d85c |
| #3471 | Match Qwen GatedDeltaNet recurrence semantics | 2026-11-18 19:10 | 715b19b2c6 |
| #3317 | Prepare GatedDeltaNet operation constants | 2026-11-18 20:19 | 8fc328329d |
| #3203 | Add rolling GatedDeltaNet executor | 2026-11-19 20:59 | 9ee049ddd7 |
| #3475 | Start rolling GatedDeltaNet chains from a checkpoint | 2026-11-19 22:31 | 20d9e39b03 |
| #3204 | Plan GatedDeltaNet dependency chains | 2026-11-19 23:14 | 3bea58b788 |
| #5461 | Tighten GDN convolution comments, names and tests | 2026-11-20 20:41 | e1b4b8421f |
| #5462 | Stop rounding GDN convolution history entries on read | 2026-11-21 00:33 | 2559c133df |
| #3443 | Lower TypedFx tuples structurally | 2026-11-21 16:18 | 9b477b9875 |
| #3208 | Add a server-side output-token ceiling | 2026-11-21 16:42 | 0799d23cc7 |
| #3476 | Store recurrent state in DMA blocks | 2026-11-23 17:47 | f454423b09 |

Two PRs of the family were closed without merge in the same period: #3814 ("Exercise generated GDN through the scheduler", closed 2026-11-19) and #5005 (closed 2026-11-20) [E5].

## 2. Is the model's branch stale against main?

Yes.

- The model's branch left main at commit 54476c6581 (2026-11-16 07:43 UTC) [E6].
- It has 21 commits that main does not have [E6].
- Main has 49 commits that the model's branch does not have [E6].

### The 21 commits, oldest first

"Same patch" means that the two commits have one patch-id [E8].
The date in the last column is the commit date that git shows. GitHub's merge time in section 1 is a few minutes later.

| # | Commit on the model's branch | Subject | State today | Commit on main, date (UTC) |
|---|---|---|---|---|
| 1 | 5bf272e3c3 | Add GDN depthwise convolution | **on main**, same patch | ab34e3d85c (#3178), 2026-11-18 17:08 |
| 2 | 50214b125a | Match Qwen GatedDeltaNet recurrence semantics | **on main**, same patch | 715b19b2c6 (#3471), 2026-11-18 18:34 |
| 3 | ea21d16f69 | Prepare GatedDeltaNet operation constants | **on main**, same patch | 8fc328329d (#3317), 2026-11-18 19:48 |
| 4 | 19b7b20667 | Add rolling GatedDeltaNet executor | **on main**, changed in review (branch: 2 files, +737; main: 4 files, +817 -5) | 9ee049ddd7 (#3203), 2026-11-19 19:41 |
| 5 | 70e9773dbf | Add rolling GatedDeltaNet checkpoints | **on main**, changed in review (other patch-id) | 20d9e39b03 (#3475), 2026-11-19 22:03 |
| 6 | 05f89c24aa | Plan GatedDeltaNet dependency chains | **on main**, changed in review (`gdn_chain_plan.hpp` became `recurrent_chain_plan.hpp`) | 3bea58b788 (#3204), 2026-11-19 23:07 |
| 7 | 6b0e9d2ddc | Store one recurrent checkpoint bundle per sequence endpoint | **on main**, changed in review, under a new subject (branch: +647 -36; main: +825 -37) | f454423b09 "Store recurrent state in DMA blocks (#3476)", 2026-11-23 17:37 |
| 8 | d278081ba3 | Represent pending recurrent sequence endpoints | open PR #3206, older copy (+649 against +875 today) | none |
| 9 | 9a4bca1f45 | Schedule recurrent continuations in the full scheduler | open PR #5345, older copy | none |
| 10 | 4fa8ec8856 | Keep hardware attention correct in recurrent passes | open PR #5346, older copy | none |
| 11 | d34b31a9fc | Activate generated recurrent GDN execution | open PR #3205, older copy (+769 against +1401 today) | none |
| 12 | 2ce07371db | Parallelize the GDN recurrence across heads | open PR #3221, older copy (+645 -218 against +807 -259 today) | none |
| 13 | be4f6d8b0e | Exercise generated GDN through the scheduler | PR #3814, closed without merge | none |
| 14 | 738b6684c7 | Resume GatedDeltaNet state from cached prefixes | open PR #5023, older copy | none |
| 15 | 875abe88ec | Keep GatedDeltaNet state at chat conversation ends | open PR #5024, older copy | none |
| 16 | 5326fa4fd7 | Infer Cat result shapes during equality saturation | open PR #3689, this is its head | none |
| 17 | 00202eb454 | Lower arbitrary-arity last-axis Cat to row copies | open PR #3690, this is its head | none |
| 18 | 4e34e13e00 | Lower proper-prefix rank-4 RoPE | open PR #3692, this is its head | none |
| 19 | bd9f93bbaa | Normalize Qwen text-only rotary export | open PR #3694, this is its head | none |
| 20 | 451ba42be4 | Normalize singleton-axis checkpoint storage by shape | open PR #3695, this is its head | none |
| 21 | 72e1191804 | Register native Qwen3.5 4B ingestion | open PR #3696, this is its head | none |

### Counts

- **7 of the 21 commits have a squash-merged commit on main** (rows 1 to 7).
- 3 of those 7 are the same patch (rows 1 to 3). 4 were changed before the merge (rows 4 to 7).
- Row 7 was matched by the PR, not by the subject. The first commit of PR #3476 has the subject of row 7 [E9].
- 7 commits are older copies of open PRs that were rewritten since (rows 8 to 12, 14, 15). None has the patch-id of today's PR head [E8].
- 1 commit belongs to a PR that was closed without merge (row 13).
- 6 commits are still the heads of their open PRs (rows 16 to 21).

### Main commits that touch GDN numerics and that the model's branch lacks

- #5462 (2559c133df): the convolution no longer rounds the history entries when it reads them [E11].
- #5461 (e1b4b8421f): convolution comments, names and tests.
- #5232 (7eddde7895): `reduce_sum(fp32x16)` now adds the 16 lanes in a fixed order with plain adds. On the model's branch it calls `_mm512_reduce_add_ps` [E23]. `normalize_gdn` calls `reduce_sum` [E12].

## 3. GDN files: main against the model's branch

Command for each row: `git diff --numstat 72e1191804 origin/main -- <file>` [E10].
"Added" lines exist only on main. "Deleted" lines exist only on the model's branch.

| File | Added (main only) | Deleted (model's branch only) | Lines on main | Lines on the model's branch |
|---|---|---|---|---|
| h/tron/kernels/gated_delta_net.hpp | 51 | 56 | 297 | 302 |
| h/tron/models/gdn_rolling_executor.hpp | 163 | 324 | 317 | 478 |
| h/tron/models/gdn_prepared_operation.hpp | 0 | 0 | 135 | 135 |
| t/t_gated_delta_net.cpp | 256 | 722 | 1976 | 2442 |
| h/tron/models/model.hpp | 28 | 196 | 3842 | 4010 |
| ingest/src/TronCpp.hs | 288 | 744 | 3748 | 4204 |
| h/tron/models/gdn_execution.hpp | 0 | 149 | absent | 149 |

### h/tron/kernels/gated_delta_net.hpp

- The code of `normalize_gdn`, `gdn_beta` and `gdn_recurrence` is the same at both commits. Only one comment line differs [E12].
- Main has the newer convolution `gdn_conv1d_silu(output, history, input, weights)` with one template parameter `n_channels`. It uses the three history entries without rounding them [E11].
- The model's branch has the older convolution for head groups: `gdn_conv1d_silu<n_local_channels, n_source_chunks>(output, history, input, weights, source_chunks)` and the type `gdn_conv1d_chunk_map`. It rounds each history entry to bf16 on read [E11].
- Main does not include `common/assert.hpp` in this file. The model's branch does [E11].

### h/tron/models/gdn_rolling_executor.hpp

- Main has the single-group executor `gdn_rolling_executor<geometry>`. Its entry points are `start_from_zero(operation, destination)`, `start_from_checkpoint(operation, source, destination)` and `step(...)`. It always advances the state inside the destination checkpoint [E13].
- Main also has `checkpoint_alignment()` and an alignment check with a message. The model's branch lacks both [E13][E14].
- The model's branch has the head-group executor `gdn_rolling_executor<geometry, key_heads_per_group>`, the alias `gdn_rolling_head_executor<geometry>`, the enum `gdn_checkpoint_access` (`in_place`, `working_copy`), `group_count()`, `write_checkpoint()`, `history_runs()` and a working copy of the state [E14].
- Main has none of these head-group names.

### h/tron/models/gdn_prepared_operation.hpp

- The file is identical at both commits [E10].
- The head of PR #3221 adds 14 lines to it: the struct `gdn_operation_weights<geometry>` (added by PR #3205) [E10].

### t/t_gated_delta_net.cpp

- Main has 29 test cases. The model's branch has 33 [E10].
- Only the model's branch has the five cases on replay and head groups, for example "GatedDeltaNet replay shards one chain across head groups" and "GatedDeltaNet helper capacity counts chain and head work" [E10].
- Only main has the case "Rolling GatedDeltaNet execution rejects a start on a misaligned destination" [E10].
- Main names the chain types `recurrent_chain_id` and `recurrent_chain_plan`. The model's branch names them `gdn_chain_id` (65 uses) and `gdn_chain_plan` (15 uses) [E20].

### h/tron/models/model.hpp

- Main's file has no GDN code. A search for `gdn_operations`, `gdn_kernels`, `in_recurrent_chains`, `recurrent_chain_plan` and `gdn_registry.hpp` gives 0 matches each [E19].
- The model's branch has the plugin constants `recurrent_execution`, `recurrent_slot_specs`, `gdn_kernels` and `gdn_operations` with their checks. It has the state members `recurrent_chain_plan` and `recurrent_checkpoint_table`, the `forward` parameters `in_recurrent_chains` and `in_recurrent_checkpoints`, and the functions `recurrent_chains()`, `recurrent_checkpoints()` and `validate_recurrent_minibatch()` [E19].
- The 28 lines that only main has are comments, one check that every token job needs KV or a listener, and one changed `insert_stream` call. None is GDN code [E19].

### ingest/src/TronCpp.hs

- Main's generator emits no GDN code. `gdnExecutionCall`, `run_gdn_operation` and `GdnOperation` give 0 matches [E19].
- The model's branch has 14 generator functions for GDN that main lacks, counted by their type signatures. Examples: `gdnOperations`, `gdnKernels`, `gdnRegistryComponents`, `gdnPreparedOperationsField`, `gdnExecutorRegistryField`, `gdnFinalization`, `gdnExecutionCall` [E19].
- Main has newer worker-group helpers that the model's branch lacks: `shardPrologue`, `kernelOwnerAsserts`, `sideCounts`, `hostSideCount`, `groupWorkers`, `itemCount`, `itemsPerToken` [E19].

### h/tron/models/gdn_execution.hpp (on the model's branch, not on main)

- The file holds `run_gdn_operation`, the function that replays the chains of one GDN operation in a forward pass [E16].
- A worker calls it with its worker index. The function picks that worker's work items, starts the worker's executor from zero or from a checkpoint, calls `executor.step` for each token of the chain, and writes the checkpoint [E16].
- It also holds `gdn_replay_work_item_count` and `gdn_available_main_helpers`, which count the work items and the helper threads that they can keep busy [E16].
- **PR #3205 adds the file.** The commit that adds it is "Activate generated recurrent GDN execution": d34b31a9fc on the model's branch and 1f705f0140 today, which is the head of PR #3205 [E17].
- PR #3221 then changes it (+75 lines in 127a662083) [E17].

## 4. PR #3221 against the model's branch

### Does 72e1191804 already contain an older version of the head-group parallelism?

Yes.

- Commit 2ce07371db ("Parallelize the GDN recurrence across heads") is on the model's branch. It is the copy of PR #3221 from 2026-11-17 [E7].
- Today's PR #3221 head 127a662083 has the same subject and another patch (+807 -259 against +645 -218) [E8].
- The executor has the same public shape at both commits. The body of `step` is the same code at both commits [E14][E15].

### Entry points of the executor

| | main f454423b09 | PR #3221 head 127a662083 | model's branch 72e1191804 |
|---|---|---|---|
| Class template | `gdn_rolling_executor<geometry>` (line 120) | `gdn_rolling_executor<geometry, key_heads_per_group>` (line 147) | same as 127a (line 132) |
| Alias for one key head per group | none | `gdn_rolling_head_executor<geometry>` (line 494) | same (line 476) |
| Start from zero | `start_from_zero(operation, destination)` | `start_from_zero(operation, group, destination, access)` | same as 127a |
| Start from a checkpoint | `start_from_checkpoint(operation, source, destination)` | `start_from_checkpoint(operation, group, source, destination, access)` | same as 127a |
| Advance one token | `step(mixed_qkv, output_gate, decay_input, update_input, output)` | same five arguments; it reads and writes only the group's columns | same as 127a |
| Advance a chain of tokens in one call | none | none | none |
| Store a working copy | none | `write_checkpoint() noexcept` | `write_checkpoint() const noexcept` |
| Where the state advances | always in the destination | `gdn_checkpoint_access::in_place` or `::working_copy` | same as 127a |
| Alignment query | `checkpoint_alignment()` | `checkpoint_alignment()` | none |

Evidence: [E13] for main, [E15] for 127a662083, [E14] for 72e1191804.

No commit of the three has an entry point that advances several tokens in one call. Our Part 0 adds that entry point (`advance`) [E24].

### The work item and the split over threads

- **main**: there is no work item. Nothing on main calls the executor except the tests [E19].
- **PR #3205 head 1f705f0140**: a work item is one whole chain. Worker `worker_ix` takes the chains `worker_ix`, `worker_ix + n_workers`, and so on [E16].
- **127a662083 and 72e1191804**: a work item is one pair (chain, head group). There is no named type for it. It is the index `work_ix`, with `chain_ix = work_ix / head_group_count` and `head_group_ix = work_ix % head_group_count`. Worker `worker_ix` takes the items `worker_ix`, `worker_ix + n_workers`, and so on [E16].
- At both commits a head group is one key head. A `static_assert` requires `group_count() == n_key_heads` [E16].
- Each worker uses only `executors[worker_ix]` [E16].

### Does 127a662083 hold h/tron/models/gdn_execution.hpp?

Yes. It has 158 lines there. It has 149 lines on the model's branch [E10].

### Differences in `run_gdn_operation` between 127a662083 and 72e1191804

| | 127a662083 | 72e1191804 |
|---|---|---|
| Template parameters | `<gdn_geometry geometry>` | `<gdn_operation_descriptor operation_descriptor, gdn_kernel_spec kernel_spec>` |
| Descriptor | function argument `gdn_operation_descriptor const&` | template argument |
| Prepared constants | `prepared_gdn_operation<geometry> const& prepared` | `std::optional<prepared_gdn_operation<...>> const& prepared_optional` |
| Executors | `std::span<gdn_rolling_head_executor<geometry>>` | `std::vector<gdn_rolling_head_executor<...>>&` |
| Chain types | `recurrent_chain_plan`, `recurrent_checkpoint_table`, `recurrent_chain_id` (from `recurrent_chain_plan.hpp`) | `gdn_chain_plan`, `gdn_checkpoint_table`, `gdn_chain_id` (from `gdn_chain_plan.hpp`, a file that 127a662083 lacks) |
| When the state advances in place | chain of 1 token, or `n_workers == 1` | chain of 1 token only |
| Who calls it | `model::state::run_gdn_operation<operation_ix>` in model.hpp line 2315 | the generated plugin, directly |
| Who owns the executors | `model::state` (`gdn_executors`, model.hpp line 1477, with `grow_gdn_executors`) | the generated plugin (field `gdn_executors`) |
| `gdn_available_main_helpers` | three arguments (adds `helper_bound`) | two arguments |

Evidence: [E16][E18].

### What "changes how the kernel is driven" means for code that calls `gdn_recurrence`

The signature and the body of `gdn_recurrence` are the same at the three commits [E12]. The call sites differ.

- **Production call site.** Each commit has exactly one, inside `gdn_rolling_executor::step` [E19].
  - main, line 241: `gdn_recurrence<n_key_heads, n_value_heads, key_head_dim, value_head_dim>(...)`. One call covers all key heads of the layer. The views have the full widths. `A_exp` and `dt_bias` start at element 0 [E13].
  - 127a662083, line 360, and 72e1191804, line 346: `gdn_recurrence<key_heads_per_group, value_heads_per_group, key_head_dim, value_head_dim>(...)`. One call covers one head group. The query, key and value views have the group widths. The state argument is the group's rows only. `A_exp` and `dt_bias` are passed as `data + value_head_base` [E14][E15].
- **Input gather.** At 127a662083 and 72e1191804, `step` first copies the group's chunks out of the mixed row through `source_chunks`, and the convolution takes `source_chunks` as a fifth argument. On main `step` copies the whole row and the convolution has four arguments [E13][E14].
- **Number of calls per token.** On main one thread makes one call per token. At 127a662083 and 72e1191804 there is one call per token and head group, and different threads make the calls for different groups of one chain [E16].
- **Where the state lives.** On main the kernel always writes the state inside the destination checkpoint. At 127a662083 and 72e1191804 it writes the executor's working copy when the access is `working_copy`, and `write_checkpoint()` copies the group's state to the destination after the last token [E14][E16].
- **Caller of the executor.** Main has no caller outside the tests. At 72e1191804 the plugin calls `tron::run_gdn_operation<gdn_operations[i], gdn_kernels[k]>(...)`. At 127a662083 the plugin calls `outer_state.run_gdn_operation<i>(mixed_qkv, output_gate, decay, update, output, worker_ix, n_workers)`, and model.hpp calls `tron::run_gdn_operation<geometry>(...)` [E18].
- **Test call sites.** The four calls in `t/t_gated_delta_net.cpp` use the full-layer template arguments at all three commits [E19].

## 5. What our commits need that main lacks

Method: for every hunk of a commit, the pre-image was searched as one block of lines in the file at the base [E20]. "5 of 6" means that 5 hunks of 6 have their pre-image at the base.
Nothing was built. `git apply --check` was not run. See "Not verified".

### Commit 0d69ef3ce8 (counters), 8 files

| File | On main | Hunks found on main | Verdict for main | Hunks found at 127a662083 | Verdict for 127a662083 |
|---|---|---|---|---|---|
| README.stats.md | yes | 2 of 2 | applies to main as is | 2 of 2 | applies as is |
| h/tron/models/gdn_stats.hpp (new, 775 lines) | no | new file | applies to main as is. Its 7 includes exist on main [E21] | new file | applies as is |
| t/t_gdn_stats.cpp (new, 602 lines) | no | new file | applies to main as is [E21] | new file | applies as is |
| t/CMakeLists.txt | yes | 1 of 1 (line 263) | applies to main as is | 1 of 1 | applies as is |
| h/tron/models/gdn_execution.hpp | **no** | no file | no target on main (`run_gdn_operation` does not exist) | 0 of 7 | needs a port (the function was rewritten, see section 4) |
| h/tron/models/model.hpp | yes | 5 of 6 | no target on main. The context lines exist, but the added code reads `gdn_operations`, `gdn_kernels` and `in_recurrent_chains`, and main has 0 uses of each [E19] | 5 of 6 (lines 15, 45, 1461, 1827, 2216) | needs a small port. The include hunk misses. The stats pointer must also reach the call in model.hpp line 2315 [E18] |
| ingest/src/TronCpp.hs | yes | 0 of 1 | no target on main (`gdnExecutionCall` does not exist) | 0 of 1 | needs a port. `gdnExecutionCall` now emits the state method call, which has no stats argument [E18] |
| t/t_gated_delta_net.cpp | yes | 0 of 2 | no target on main (the test calls `run_gdn_operation`) | 0 of 2 | needs a port. Our test uses `gdn_chain_plan`, `gdn_chain_id`, `gdn_checkpoint_table`, `replay_kernel` and `emplace_replay_operation`. 127a662083 has 0 uses of each [E20] |

### Commit 775bba7661 (Part 0 and Part A), 15 files

| File | Part | Hunks found on main | Verdict for main | Hunks found at 127a662083 | Verdict for 127a662083 |
|---|---|---|---|---|---|
| h/tron/kernels/gated_delta_net.hpp | 0 | 3 of 4 | needs a port of one line. The include hunk misses: main dropped `#include "common/assert.hpp"`, and our added code uses `TRON_ASSERT` 4 times [E11][E20] | 4 of 4 | applies as is |
| h/tron/models/gdn_rolling_executor.hpp | 0 and A | 0 of 21 | no target on main. Main's executor has no head group, no working copy and no `write_checkpoint`. Our `advance` needs a working copy [E13][E24] | 11 of 21 | needs a port. 10 hunks miss on changed comments, includes, assertions and a rewritten `bind`. The class has the same members [E15][E20] |
| h/tron/models/gdn_execution.hpp | 0 and A | no file | no target on main | 0 of 4 | needs a port. The hunks change lines of our counters commit |
| h/tron/models/model.hpp | A | 0 of 2 | no target on main | 0 of 2 | applies only after the counters port (both hunks change lines of the counters commit) |
| h/tron/models/gdn_stats.hpp | counters | our own file | follows the counters commit | our own file | follows the counters commit |
| t/t_gated_delta_net.cpp | 0 and A | 0 of 4 | no target on main | 0 of 4 | needs a port (old chain type names, old `run_gdn_operation` call) |
| h/tron/kernels/amx_gdn_iface.hpp (new, 161 lines) | A | new file | applies as is. It includes no project header [E21] | new file | applies as is |
| src/tron/kernels/amx_gdn.cpp (new, 553 lines) | A | new file | applies as is. It includes `amx_attn_iface.hpp`, which is identical on main [E21] | new file | applies as is |
| t/t_amx_gdn_numerics.cpp (new, 535 lines) | A | new file | applies once the Part 0 kernel is in `gated_delta_net.hpp`. It uses `gdn_recurrence_chain` and `gdn_recurrence_window` [E21] | new file | same |
| CMakeLists.txt | A | 1 of 1 | applies as is | 1 of 1 | applies as is |
| src/tron/CMakeLists.txt | A | 1 of 1 (line 204) | applies as is | 1 of 1 | applies as is |
| t/CMakeLists.txt | A | 1 of 1 (line 626) | applies as is | 1 of 1 (line 630) | applies as is |
| README.ci.md | A | 1 of 1 (line 582) | applies as is | 1 of 1 | applies as is |
| h/tron/kernels/amx_attn_iface.hpp | A | 1 of 1 | applies as is (comment only) | 1 of 1 | applies as is |
| src/tron/kernels/amx_attn.cpp | A | 1 of 1 | applies as is (comment only) | 1 of 1 | applies as is |

### What this means per base

- **main**: the files that hold only a kernel or only the statistics types can sit on main. These are `gdn_stats.hpp`, `t_gdn_stats.cpp`, the chain kernel in `gated_delta_net.hpp`, `amx_gdn.cpp`, `amx_gdn_iface.hpp`, `t_amx_gdn_numerics.cpp` and the build files.
- **main**: every hunk that connects them to a model has no target. These are the hunks in `gdn_execution.hpp`, `model.hpp`, `TronCpp.hs`, `gdn_rolling_executor.hpp` and `t_gated_delta_net.cpp`.
- **127a662083**: no code that our commits need is absent. 4 files of the counters commit need a port by hand (`gdn_execution.hpp`, `model.hpp`, `TronCpp.hs`, `t_gated_delta_net.cpp`). 3 files of the Part 0 and Part A commit need a port by hand (`gdn_rolling_executor.hpp`, `gdn_execution.hpp`, `t_gated_delta_net.cpp`). Its `model.hpp` hunks follow the counters port.
- **PR #5571 head 69cc70fae0** (for the rounding work): the Part 0 hunk next to `gdn_beta` in `gated_delta_net.hpp` misses there (3 of 4 found). The executor hunks give 10 of 21 [E20][E25].

## 6. Summary table: three candidate bases

| Base | Counters | Part 0 (chain kernel) | Part A (AMX block kernel) | Is Qwen3.5 4B registered | Can the model run end to end |
|---|---|---|---|---|---|
| main f454423b09 | Only the types, the report and their unit test. The hooks need `run_gdn_operation`, `gdn_operations` and `gdnExecutionCall`, which main lacks | Only the kernel function (plus one include line). `advance` needs the head-group executor with a working copy, which main lacks | Only the kernel, its interface, its unit test and the build lines. Nothing on main would call it | No. `config/models.yaml` has no Qwen3.5 entry [E22] | No. The model is not registered, and model.hpp has no GDN code [E19][E22] |
| PR #3221 head 127a662083 | All of it, after a port by hand. No needed code is absent | All of it, after a port by hand (kernel header 4 of 4 hunks, executor 11 of 21) | All of it, after the same port | No [E22] | No. The registry entry is missing. The five ingest PRs #3689 to #3695 and the three state PRs #5023, #5486, #5024 are above this base [E2][E22] |
| model's branch 72e1191804 | All of it, as it is (our commits were made here) | All of it, as it is | All of it, as it is | Yes: `qwen_3p5_4b`, variant `ingested-qwen-3.5-4b`, lines 812 to 824 [E22] | Registered. A run was not repeated in this task. See "Not verified" |

More facts for the choice:

- The plugin of Qwen3.5 4B is generated (`source: generated` in the registry entry). No plugin source for it is checked in at any of the three commits [E22].
- PR #3696 itself changes one file: 14 added lines in `config/models.yaml` [E22].
- Our draft PR #5572 has the model's branch as base. Its head is 882e5322f1 with 3 commits. GitHub reports it as mergeable [E26].
- PR #5022 (ours, AMX attention kv_mul 16) has main as base. Its head ddf843ad97 is 7 commits ahead of main and 11 commits behind [E26].

## Not verified

- **Whether a hunk that matches textually also compiles at that base.** Nothing was built. To settle it: apply the commit on a new worktree at the base and build `t_gated_delta_net` and `t_amx_numerics`.
- **`git apply --check`.** It was not run, because it needs an index file and the task gave no directory for temporary files. To settle it: `GIT_INDEX_FILE=<tmp> git read-tree <base>` and then `git show <commit> -- <file> | GIT_INDEX_FILE=<tmp> git apply --cached --check`.
- **Whether Qwen3.5 4B runs end to end at 72e1191804.** Only the registry entry was checked. To settle it: one runtron run of `ingested-qwen-3.5-4b` from a build of that commit.
- **Whether the upper six PRs (#3689 to #3696) apply cleanly on today's PR #5024 head.** GitHub reports PR #3689 as CONFLICTING. The size of the conflict was not measured. To settle it: `git merge-tree --write-tree 3c888791c9 72e1191804` in a scratch object directory.
- **Whether the fixed-order `reduce_sum` of #5232 changes any bit of `normalize_gdn` against the model's branch.** The note in the code says the order equals the one clang 19 emits. To settle it: run `t_gated_delta_net` reference cases at both commits and compare the normalized values.

## How this was checked

- All git commands were read-only and ran with `git -C /home/jhan/workspace/tron`.
- All GitHub commands were `gh pr list`, `gh pr view` and `gh api` GET with `--repo positron-ai/tron`.
- Three PR listings were stored for a short time as JSON files in the session scratch directory and then deleted. No other temporary file was made.

## Evidence

- **[E1]** `gh api repos/positron-ai/tron/commits/main` gave `f454423b09 2026-11-23T17:37:21Z Store recurrent state in DMA blocks (#3476)`. `git rev-parse origin/main` gave f454423b09. `.git/FETCH_HEAD` has the time 2026-11-23 11:16 -0800.
- **[E2]** `gh pr list --repo positron-ai/tron --state open --limit 1000 --json number,title,baseRefName,headRefName,headRefOid,isDraft,reviewDecision,updatedAt`, then a filter on `headRefName` starting with `rbjarnason/qwen35`. Output: 668 open PRs, 41 in the family, 31 drafts. With `--limit 200` the output was 200 PRs and 4 of the family (#5345, #5346, #5486, #5571). Path from main computed from base and head names: `main, 3206, 5345, 3205, 3221, 5023, 5486, 5024, 3689, 3690, 3692, 3694, 3695, 3696`. Path to #5571: `main, 3206, 5345, 3205, 3221, 5571`. Each PR page is https://github.com/positron-ai/tron/pull/N.
- **[E3]** `git log --format='%h %ci p=%p %s' origin/main..3c888791c9` lists 29 commits. The lowest five are `7f9011ffb7 p=f454423b09`, `e175e34705 p=7f9011ffb7`, `1f705f0140 p=e175e34705`, `127a662083 p=1f705f0140`, `1af8baacf6 p=127a662083`, all dated 2026-11-23 12:47 -0500. `git merge-base --is-ancestor 3c888791c9 5326fa4fd7` answers no. `git merge-base --is-ancestor 127a662083 72e1191804` answers no. `git merge-base --is-ancestor 127a662083 c3b51adf66` answers no. `git log origin/main..69cc70fae0` adds `59429b0955` and `69cc70fae0` on 127a662083. Ahead/behind against main: steps 8 to 13 are 16 to 21 commits ahead and 49 behind, with merge base 54476c6581.
- **[E4]** `gh pr view N --json isDraft,reviewDecision,mergeable,mergeStateStatus,additions,deletions,changedFiles,commits`. #3206: `MERGEABLE, BLOCKED, +875 -1, files=4, commits=1`. #3221: `MERGEABLE, BLOCKED, +807 -259, files=8, commits=1`. #5571: `draft, MERGEABLE, CLEAN, +243 -181, files=3, commits=2`. #3689: `draft, CONFLICTING, DIRTY, +10623 -241, files=64, commits=16`. #3696: `APPROVED, MERGEABLE, CLEAN, +14 -0, files=1, commits=1`.
- **[E5]** `gh pr list --state merged --search "merged:>=2026-11-15" --limit 1000 --json ...` gave 52 merged PRs, 11 with the head prefix. `--search "head:rbjarnason/qwen35 merged:>=2026-11-15"` gave the same 11. `gh pr list --state all --search "Exercise generated GDN through the scheduler in:title"` gave PR #3814, CLOSED 2026-11-19T19:39:47Z, head be4f6d8b0e. `gh pr list --state all --head rbjarnason/qwen35-force-generate-stop-tokens` gave PR #5005, CLOSED 2026-11-20T17:11:42Z.
- **[E6]** `git merge-base origin/main 72e1191804` gave 54476c6581 (`2026-11-16 07:43:19 +0000 Execute forward plans over decoder-layer ranges (#5184)`). `git rev-list --count origin/main..72e1191804` gave 21. `git rev-list --count 72e1191804..origin/main` gave 49.
- **[E7]** `git log --format='%h | %ci | %s' origin/main..72e1191804` gave the 21 rows of section 2. `git log 54476c6581..origin/main` gave the 49 main commits with the PR numbers of the table.
- **[E8]** `git show <id> | git patch-id --stable` for both commits of a pair. Equal for 5bf272e3c3/ab34e3d85c, 50214b125a/715b19b2c6, ea21d16f69/8fc328329d. Different for 19b7b20667/9ee049ddd7, 70e9773dbf/20d9e39b03, 05f89c24aa/3bea58b788, 6b0e9d2ddc/f454423b09. Different for all seven pairs of rows 8 to 12, 14 and 15 against 7f9011ffb7, e175e34705, c3b51adf66, 1f705f0140, 127a662083, 1af8baacf6, 3c888791c9. `git show --shortstat` gave the line counts in the table.
- **[E9]** `gh pr view 3476 --json commits`: the first commit headline is "Store one recurrent checkpoint bundle per sequence endpoint". The head branch is `qwen35-24bc-endpoint-checkpoint-store`.
- **[E10]** `git diff --numstat 72e1191804 origin/main -- <file>` gave `51 56`, `163 324`, no output (identical), `256 722`, `28 196`, `288 744`, `0 149` for the seven files in table order. `git diff --numstat origin/main 127a662083 -- h/tron/models/gdn_prepared_operation.hpp` gave `14 0`. `git show <commit>:<file> | wc -l` gave the line counts. `grep -c '^TEST_CASE('` on `t/t_gated_delta_net.cpp` gave 29 (main), 37 (127a662083), 33 (72e1191804). `comm` on the sorted case names gave the names in the text.
- **[E11]** h/tron/kernels/gated_delta_net.hpp. At f454423b09 lines 120 to 124: `template <size_t n_channels> void gdn_conv1d_silu(tensor<n_channels>& output, gdn_conv1d_history<n_channels> history, tensor<n_channels> const& input, prepared_gdn_conv1d_weights<n_channels> const& weights)`. Line 130 there: `fp32s const entry0 = tron_mm_loadu_ps(chunk_history);`. At 72e1191804 lines 117 to 123: `template <size_t n_local_channels, size_t n_source_chunks> TRON(noinline) void gdn_conv1d_silu(..., gdn_conv1d_chunk_map<n_local_channels> const& source_chunks)`, and line 133 there: `fp32s const entry0 = round_chunk_to<bf16>(tron_mm_loadu_ps(chunk_history));`. At 127a662083 the convolution has the five-argument form of 72e1191804 (lines 139 to 144) and the unrounded read of main (`fp32s const entry0 = tron_mm_loadu_ps(chunk_history);`). Line 8 at 72e1191804 and at 127a662083 is `#include "common/assert.hpp"`. Main's include block (lines 3 to 14) has no such line. `git log 54476c6581..origin/main -- h/tron/kernels/gated_delta_net.hpp` lists #5462 and #5461 as the last two changes.
- **[E12]** The text from `gdn_qk_norm_epsilon` to the end of the file was compared with `diff`: main lines 150 to 297, 72e1191804 lines 154 to 302, 127a662083 lines 176 to 324. 72e1191804 against 127a662083: no difference. Main against either: one comment sentence differs ("so a caller may pass one head group's slice of the prepared constants"). Main line 183 (in `normalize_gdn`): `float const quadrance = round_to<bf16>(reduce_sum(squared));`.
- **[E13]** h/tron/models/gdn_rolling_executor.hpp at f454423b09. Line 120: `template <gdn_geometry geometry>`. Lines 180, 193, 210: `start_from_zero(operation_type const& operation, checkpoint_destination destination)`, `start_from_checkpoint(operation_type const& operation, checkpoint_source source, checkpoint_destination destination)`, `step(mixed_qkv_row const& mixed_qkv, gate_row const& output_gate, decay_row const& decay_input, update_row const& update_input, output_row& output)`. Line 220: `working.convolution_qkv = mixed_qkv;`. Lines 229 to 232: `gdn_conv1d_silu(working.convolution_qkv, gdn_conv1d_history<convolution_channels>(...), working.convolution_qkv, operation.convolution_weights);`. Lines 241 to 247: `gdn_recurrence<n_key_heads, n_value_heads, key_head_dim, value_head_dim>(working.recurrence_output, *working.recurrent_state, query, key, recurrence_value, ...)`. Line 172: `static constexpr size_t checkpoint_alignment() noexcept`.
- **[E14]** The same file at 72e1191804. Lines 44 to 49: `enum class gdn_checkpoint_access { in_place, working_copy };`. Lines 132 to 135: `template <gdn_geometry geometry, size_t key_heads_per_group> ... class gdn_rolling_executor`. Line 221: `group_count()`. Lines 241 to 244: `start_from_zero(operation_type const& operation, size_t group, checkpoint_destination destination, gdn_checkpoint_access access)`. Lines 262 to 266: `start_from_checkpoint(operation, group, source, destination, access)`. Line 291: `void write_checkpoint() const noexcept`. Lines 322 to 324: `working.convolution_qkv.store_chunk(chunk, mixed_qkv.chunk(working.source_chunks[chunk]));`. Lines 334 to 337: the convolution call with `working.source_chunks` as fifth argument. Lines 346 to 354: `gdn_recurrence<key_heads_per_group, value_heads_per_group, key_head_dim, value_head_dim>(..., operation.A_exp.data.data() + value_head_base, operation.dt_bias.data.data() + value_head_base)`. Line 476: `using gdn_rolling_head_executor = gdn_rolling_executor<geometry, 1>;`.
- **[E15]** The same file at 127a662083: lines 47, 147 to 150, 237, 255, 276, 305 (`void write_checkpoint() noexcept`), 325, 348, 360, 494 hold the same declarations. `git diff 72e1191804 127a662083` on the file has no hunk inside the body of `step`. Its hunks change comments, includes, assertions, `checkpoint_alignment()`, the removal of the explicit copy and move declarations, and the loop in `bind` that fills `source_chunks`.
- **[E16]** h/tron/models/gdn_execution.hpp. At 72e1191804 lines 76 to 89: `template <gdn_operation_descriptor operation_descriptor, gdn_kernel_spec kernel_spec> void run_gdn_operation(std::optional<prepared_gdn_operation<kernel_spec.geometry>> const& prepared_optional, std::vector<gdn_rolling_head_executor<kernel_spec.geometry>>& executors, gdn_chain_plan const& chains, gdn_checkpoint_table const& checkpoints, ...)`. Lines 112 to 114: `for (size_t work_ix = worker_ix; work_ix < work_item_count; work_ix += n_workers) { size_t const chain_ix = work_ix / head_group_count; size_t const head_group_ix = work_ix % head_group_count;`. Lines 128 to 130: `chain.order.size() == 1 ? gdn_checkpoint_access::in_place : gdn_checkpoint_access::working_copy`. Lines 141 to 145: the `executor.step(...)` loop and `executor.write_checkpoint();`. Lines 93 to 94: `static_assert(executor_type::group_count() == kernel_spec.geometry.n_key_heads, ...)`. Line 68: `gdn_available_main_helpers(size_t chain_count_upper_bound, size_t key_head_count)`. At 127a662083 lines 78 to 90: `template <gdn_geometry geometry> void run_gdn_operation(gdn_operation_descriptor const& operation_descriptor, prepared_gdn_operation<geometry> const& prepared, std::span<gdn_rolling_head_executor<geometry>> executors, recurrent_chain_plan const& chains, recurrent_checkpoint_table const& checkpoints, ...)`. Line 113: `executor_type& executor = executors[worker_ix];`. Lines 114 to 116: the same `work_ix` loop. Line 134: `chain.order.size() == 1 || n_workers == 1`. Lines 69 to 71: `gdn_available_main_helpers(size_t chain_count_upper_bound, size_t key_head_count, size_t helper_bound)`. At 1f705f0140 (111 lines): `std::span<gdn_rolling_executor<geometry>> executors`, `for (size_t chain_ix = worker_ix; chain_ix < chains.size(); chain_ix += n_workers)`, `executor.start_from_zero(prepared, destination);`.
- **[E17]** `git log --diff-filter=A --format='%h %s' 72e1191804 -- h/tron/models/gdn_execution.hpp` gave `d34b31a9fc Activate generated recurrent GDN execution`. The same command on 127a662083 gave `1f705f0140 Activate generated recurrent GDN execution`. 1f705f0140 is the head of PR #3205 [E2]. `git show --stat 127a662083` lists `h/tron/models/gdn_execution.hpp | 75`.
- **[E18]** At 127a662083, h/tron/models/model.hpp lines 2302 to 2319: `template <size_t operation_ix> void run_gdn_operation(auto const& mixed_qkv, auto const& output_gate, auto const& decay, auto const& update, auto& output, size_t worker_ix, size_t n_main_workers) { ... tron::run_gdn_operation<gdn_kernels[kernel_ix].geometry>(gdn_operations[operation_ix], *prepared, std::get<kernel_ix>(gdn_executors), recurrent_chains(), recurrent_checkpoints(), ...); }`. Line 1477: `gdn_executors_t gdn_executors;`. Line 2283: `void grow_gdn_executors(size_t n_main_workers)`. At 127a662083, ingest/src/TronCpp.hs lines 2838 to 2854: `gdnExecutionCall` builds `TemplateMethodCall (Var "outer_state") "run_gdn_operation" [operation index] (the four inputs ++ [output, workerIx, Var "n_workers"])`. At 72e1191804, ingest/src/TronCpp.hs lines 3121 to 3144: `TemplateFunCall "tron::run_gdn_operation" [Index (Var "gdn_operations") operationIx, Index (Var "gdn_kernels") kernelIx] (...)`. Lines 765 to 778 there: the plugin field `gdn_executors` of type `std::tuple<std::vector<tron::gdn_rolling_head_executor<...>>...>`.
- **[E19]** `git grep -c -F <name> f454423b09 -- h/tron/models/model.hpp` gave 0 for `gdn_operations`, `gdn_kernels`, `in_recurrent_chains`, `recurrent_chain_plan`, `gdn_registry.hpp`, `run_gdn_operation`, `gdn_rolling`. The same on `ingest/src/TronCpp.hs` gave 0 for `gdnExecutionCall`, `run_gdn_operation`, `GdnOperation`. `git grep -l run_gdn_operation f454423b09` gave no file. `git grep -l -E 'gdn_rolling_(head_)?executor' f454423b09` gave only `gdn_rolling_executor.hpp` and `t/t_gated_delta_net.cpp`. `git grep -n -E 'gdn_recurrence<'` gave one non-test call per commit (main line 241, 127a662083 line 360, 72e1191804 line 346) and four test calls per commit, all with `<n_key_heads, n_value_heads, key_head_dim, value_head_dim>` or fixed sizes. `git diff 72e1191804 origin/main -- h/tron/models/model.hpp | grep '^-'` lists the names of section 3. `grep '^+'` lists the 28 added lines. The same on `TronCpp.hs` with a filter on top-level type signatures lists the generator functions.
- **[E20]** A script read `git show --format= -U3 <commit> -- <file>`, split it into hunks, and searched each pre-image as one block in `git show <base>:<file>`. Results for 0d69ef3ce8: README.stats.md 2 of 2 on every base; gdn_execution.hpp 0 of 7 at 127a662083 and 7 of 7 at 72e1191804; model.hpp 5 of 6 on main and at 127a662083, 6 of 6 at 72e1191804 (the hunk `@@ -51,6 +53,7 @@` misses); TronCpp.hs 0 of 1 on main and at 127a662083; t/CMakeLists.txt 1 of 1 everywhere; t_gated_delta_net.cpp 0 of 2 on main and at 127a662083. Results for 775bba7661: gated_delta_net.hpp 3 of 4 on main (the hunk `@@ -1,8 +1,10 @@` misses), 4 of 4 at 127a662083, 3 of 4 at 69cc70fae0 (the hunk `@@ -198,6 +200,13 @@` misses); gdn_rolling_executor.hpp 0 of 21 on main, 11 of 21 at 127a662083, 21 of 21 at 72e1191804, 10 of 21 at 69cc70fae0; gdn_execution.hpp 0 of 4 at 127a662083; model.hpp 0 of 2 on every base (the lines come from 0d69ef3ce8); t_gated_delta_net.cpp 0 of 4 on main and at 127a662083; build and comment files 1 of 1 everywhere. Name counts in `t/t_gated_delta_net.cpp` (main, 127a662083, 72e1191804): `gdn_chain_id` 0, 0, 65; `gdn_chain_plan` 0, 0, 15; `gdn_checkpoint_table` 0, 0, 5; `replay_kernel` 0, 0, 4; `emplace_replay_operation` 0, 0, 5; `recurrent_chain_id` 43, 87, 0; `recurrent_chain_plan` 2, 22, 0. `git show 775bba7661 -- h/tron/kernels/gated_delta_net.hpp | grep -c '^+.*TRON_ASSERT'` gave 4.
- **[E21]** For each `#include "..."` of a new file, `git cat-file -e <base>:h/<path>` (or `t/<path>`) was run. gdn_stats.hpp includes `common/assert.hpp`, `common/attributes.hpp`, `common/util.hpp`, `system/fuse_stats.hpp`, `system/fuse_sysfs.hpp`, `system/system.hpp`, `tron/models/attn_stats.hpp`: all present on main, at 127a662083 and at 72e1191804. amx_gdn_iface.hpp has no quoted include. amx_gdn.cpp includes `tron/kernels/amx_attn_iface.hpp` and `tron/kernels/amx_gdn_iface.hpp`. t_amx_gdn_numerics.cpp includes `common/numerics/bf16.hpp`, `common/random.hpp`, `tron/kernels/amx_attn_iface.hpp`, `tron/kernels/amx_gdn_iface.hpp`, `tron/kernels/gated_delta_net.hpp`, and its line 229 calls `tron::gdn_recurrence_chain(...)`. `git diff --numstat 72e1191804 origin/main` gave no output for `attn_stats.hpp`, `fuse_stats.hpp`, `fuse_sysfs.hpp`, `amx_attn_iface.hpp`, `amx_attn.cpp`, `t_amx_numerics.cpp` and `README.stats.md`.
- **[E22]** `git grep -n -i -E 'qwen[-_ ]?3[.p_]?5|qwen35' <commit> -- config/models.yaml` gave no match at f454423b09, 127a662083 and 69cc70fae0. At 72e1191804 it gave lines 812 to 823: `- name: qwen_3p5_4b`, `hf_id: Qwen/Qwen3.5-4B`, `source: generated`, `- slug: ingested-qwen-3.5-4b`, `executors: [tp1, tp2, tp4]`. A tree-wide `git grep -l` for `qwen_3p5_4b|qwen-3.5-4b|Qwen3.5-4B` gave `bin/ci/prime_hf_models.py` and `bin/ci/test_prime_hf_models.py` at every commit, plus `config/models.yaml` at 72e1191804 only. `git show --stat 72e1191804` gave `config/models.yaml | 14 ++++++++++++++`, 1 file.
- **[E23]** `git diff 72e1191804 origin/main -- h/tron/simd/fp32.hpp`: the line `return _mm512_reduce_add_ps(x);` is replaced by four plain add steps under "Note [Fixed-order reduce_sum]". `git log 54476c6581..origin/main -- h/tron/simd/fp32.hpp` gave `7eddde7895 simd: Reduce fp32x16 sums in a fixed order (#5232)`.
- **[E24]** `git show --stat 0d69ef3ce8`: 8 files, 1678 insertions, 6 deletions, parent 72e1191804. `git show --stat 775bba7661`: 15 files, 2488 insertions, 100 deletions, parent 0d69ef3ce8. In h/tron/models/gdn_rolling_executor.hpp at 775bba7661: line 503 `void advance(token_range const& tokens, size_t first_position, gdn_block_kernel block_kernel, gdn_token_rows<...> const& rows, gdn_stats::work_tally* tally = nullptr) noexcept`, line 550 `gdn_recurrence_chain(`, line 696 `void advance_window_with_block_kernel(`. The note our commit adds there says "advance() advances it by a run of tokens and needs a working copy".
- **[E25]** `git diff --stat 127a662083 69cc70fae0`: `gated_delta_net.hpp | 65`, `gdn_rolling_executor.hpp | 31`, `t/t_gated_delta_net.cpp | 328`, 243 insertions and 181 deletions. Hunk results at 69cc70fae0 are in [E20].
- **[E26]** `gh pr view 5572`: `OPEN, draft, base=rbjarnason/qwen35-native-4b-registry, head=jhan-gdn-amx 882e5322f1, MERGEABLE CLEAN, commits=3`. `gh pr view 5022`: `base=main, head=ddf843ad97, CHANGES_REQUESTED, MERGEABLE BLOCKED`. `git rev-list --count origin/main..ddf843ad97` gave 7, the reverse gave 11.
