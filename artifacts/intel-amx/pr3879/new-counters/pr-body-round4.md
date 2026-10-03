## Short version

This PR counts how much of a model's attention work ran on each path (AVX, AMX, FPGA), and how long attention took, per layer and per pool worker (the attention workers of a forward are the last pool workers). 

One environment variable, `TRON_ATTN_STATS=1`, turns on the collection at run time. The numbers come out as FUSE leaves under `/model/<id>/attention/`, and as stderr summary at the end of a runtron run.

Perf impacts are neglectable. 

## Not in this PR
MoE models are not specifically scoped, it is likely MoE stats are not covered. Will add when AMX feature extends to MoE.

## Words used here

- visit: one call of `apply_page_tok`. That is one (query token, KV page of 64 tokens, KV head) triple that passed the page-level checks of `apply_page_range`. The AMX kernel serves a whole dense page per visit. The AVX loop serves the relevant K tokens of the page. An empty visit found no software work.
- forward: one model run for all users' pending token jobs. Forward class: `decode_like` when every token job has a listener (one generated token per user, but also a one-token final prompt chunk or a speculative verify step). `prompt_or_mixed` is every other forward.

**Timers**, all in TSC cycles (`summary` carries `tsc_hz`):
- T1 = wall time of one model forward, taken by `forward_scope` (the one object that owns the per-forward record, review round 4) inside `model::state::forward`: from after its perfetto slice to its return. Logits and listener delivery are inside. Scheduler work before and after is outside.
- T2 = busy time of one attention job on one worker. This is `attn_elapsed`, which exists today: both passes and the join, without the upstream K/V wait.
- T3 = wall time of one attention job as attention worker 0 sees it (entry to return), filed per layer.
- T4 = layer period on attention worker 0, filed per layer: from its first job of one attention operation to its first job of the next operation. The second minibatch of the same operation starts no period. The last layer of a forward has no period.
- T5 = `join_wait_cycles`: the time a worker spends waiting in the join with no join progress, in both join modes. In a hardware join it is the wait loop that ends when an FPGA pass or the other workers' software partials become ready. In a software-only join it is the stretches of failed polls on the peer workers' sections in `run_joins`.

## Review round 4 (five inline comments of 2026-09-28)

- T5 covers the software-only join (W1, commit 6e23101744). `run_joins` times each stretch of consecutive failed polls with no join progress into `join_wait_cycles`. With the switch off there is no rdtsc read. With the switch on there are two reads per stretch.
- One owner of the per-forward record (W2, b6fd226982). `attn_stats::forward_scope` is the first statement of `model::state::forward` after its perfetto slice. Its constructor stores the forward class, sizes the path bits and takes the T1 start stamp. Its destructor takes the T1 stop stamp and folds the path bits. The scheduler file `full.hpp` is no longer changed by the PR.
- Forward class under continuous batching (W3, ae8a6d38d9). A forward that carries one user's prompt chunk next to other users' generated tokens is `prompt_or_mixed`. So `decode_like` counts pure-decode forwards only. The `<class>_forwards` leaf gains `listener_jobs` (token jobs with a listener: every generated token, and the last token of a prompt chunk) and `kv_only_jobs` (token jobs that only stored their K and V). A per-token-job split of the visit counters is offered as a follow-up PR.
- Asserts instead of silent range guards (W4, 15f355acb2). In production every index of the hooks is in range by construction. A wrong index now fails with `TRON_ASSERT` instead of going uncounted. `note_token_path` had no production caller and is deleted.
- The three job counts of a forward move together (04da001cb5, found in the live read of the round-4 run). `begin_forward` keeps the listener count and `end_forward` adds `token_jobs`, `listener_jobs` and `kv_only_jobs` together, so `listener_jobs` + `kv_only_jobs` = `token_jobs` at every read of the leaf, also during a forward. Before, a read during a forward showed the two listener counts one forward ahead.
- Rows keyed by pool worker (W5, bff317e0d3). The rows are sized by the app pool, and attention worker `i` of a forward runs on pool worker `num_workers - n_attn_workers + i`. `model_stats::pool_worker` applies that formula and asserts its inputs. The main helpers' rows read zero. T3 and T4 move to one struct per (class, layer), so the worker leaves no longer carry the `*_w0` keys. `assemble_attention_plan_impl` records the split of the forward. `end_forward` folds the last `n_attn_workers` rows only, and the `<class>_forwards` leaf carries `n_attn_workers_min` and `n_attn_workers_max`.

## Doc and tests
Docs: `README.stats.md` describes the leaves and the switch.

Tests:

- New `t/t_attn_stats.cpp`, 18 cases: tallies, rows, path sets, timers, class routing, JSON leaves and their size, the exit report, FUSE registration with the weak_ptr rule, the last-wins takeover, the EAGLE directory, `forward_scope` and the two half-record defects of round 4 (W2), the fork-based negative case for out-of-range indices (W4), the pool-worker mapping, the split-moves case that exposes the old keying, and the restricted fold (W5). The switch rule (exactly "1") has no unit case: the reader is one function that reads the environment once, and the `TRON_ATTN_STATS=yes` run on delphi-3bda checks the warning. The file is compiled into the `t_llama_unit` binary, so it needs no cost-data row of its own (a row needs a whole-host bench run).
- `t/t_llama_unit.cpp`: the fake-lane `apply_page_range` case asserts the stats-on tallies (32 AVX visits of 32 K tokens each, no AMX, no empty visit). The CI lane compiles without `TRON_AMX_DISPATCH`, and this case exercises the per-visit hook there. The case also checks that the visits land in the last pool row, then repeats the call under a 2-worker split and checks the row one earlier (W5). The two direct `stream_hw_joins` cases pass a real accumulator and check 0, because every sweep there makes progress (W1).
- `t/t_amx_dispatch_dtype.cpp` asserts the amx/avx split against the kernel fakes' call counts. It also gets the two `apply_page_range` arguments main's copy lacks. Main's copy does not compile with `-DTRON_AMX_DISPATCH=ON`, and #4557 carries the same fix.
- `t/heterogeneous_scheduler_compile.cpp`: the mixed-attention section checks the hardware join's T5 (greater than 0 and at most the join's wall time). A new section runs `run_joins` with no hardware plan against a producer that finishes 20 ms late, in three arms: late producer with stats on (T5 greater than 0 and at most the wall time), sections already done (T5 = 0), stats flag off (T5 = 0) (W1). The fixtures that drive `apply_page_range` or `run_attention_job` with the switch on open a `forward_scope` first, as production does (W4).


## Why one environment variable and no CMake option

The earlier design page (PR3879/new-PRs/PR1/counter.html, section 9) put the per-visit tallies behind a CMake option. Its rule was that hooks in the hottest loop stay out of the production binary. The approving reviewers of #4267 asked for the opposite shape for the page-share counters: FUSE leaves with a run-time opt-in (#4303). The cost argument for the run-time switch is small numbers. With the variable unset, a visit pays one test of a stack bool. A visit costs est. 5,800 to 11,200 cycles (2.1 to 2.9 us per visit measured on 2026-09-01 at prompts 256 to 2048). The margin below a 1 % TPS change is therefore 60x to 400x. The A/A below is the check. Section 13 of the design page records the decision.

## Off-state cost (A/A) and on-state cost

Setup: delphi-3bda, our half (socket 1, cards 90/93), runtron, CPU attention (`USE_HW_ATTN=0`). CPU attention is the worst case for the per-visit hooks, because every page visit is software. Model qwen-3-4b tp2, 8 users, 256 generated tokens, 3 interleaved repetitions per arm and cell. Arms: base and base2 = main 66c7bb8db1 with the variable unset (the same-binary pair gives the band). head = this branch at 9b3832eb4b with the variable unset. headon = the same binary with `TRON_ATTN_STATS=1`. TPS is the mean over the repetitions, with the sample sd. The band per cell was fixed before the runs: the largest of |base2 - base|, twice the largest per-arm sd, and 0.5 % of base.

| Cell | Arm | TPS | sd | vs base | Reading |
|---|---|---|---|---|---|
| prompt 1024 | base | 79.95 | 0.29 | | reference |
| prompt 1024 | base2 | 79.67 | 0.29 | -0.34 % | same binary: band 0.59 TPS (0.73 %) |
| prompt 1024 | head (switch unset) | 79.81 | 0.17 | -0.17 % | inside the band |
| prompt 1024 | headon (switch set) | 79.91 | 0.24 | -0.05 % | on-state cost: none visible |
| prompt 8192 | base | 17.12 | 0.00 | | reference |
| prompt 8192 | base2 | 17.11 | 0.02 | -0.10 % | same binary: band 0.09 TPS (the 0.5 % floor) |
| prompt 8192 | head (switch unset) | 17.25 | 0.04 | +0.77 % | faster than main, outside the band on the fast side (code placement, the same size of effect the PR 4587 measurement showed on this host) |
| prompt 8192 | headon (switch set) | 17.24 | 0.02 | +0.70 % | on-state cost: none visible |

TTFT (prefill time, max over the users), base / head / headon / base2: prompt 1024 3.146 / 3.153 / 3.161 / 3.147 s. Prompt 8192 52.65 / 52.78 / 53.01 / 52.68 s. The head with the switch set costs +0.4 % and +0.7 % of prefill time at the two prompt lengths (est. from single runs with sd 0.1 to 0.4 s: inside the run-to-run spread at 8192, at the edge at 1024).

Reading: the hooks with the variable unset cost nothing this A/A can see. The A/A resolves about 0.5 to 0.7 %. With the variable set, the counting costs nothing visible either. The pre-registered rule flips the switch to a build option only on a loss beyond the band at both cells. The environment variable stays.

Confirmation round on the final commit cbf1bb6c0c, the same cell at prompt 1024, three interleaved repetitions per arm, run after the main round on the same host:

| Arm | TPS | sd | vs base3 | Reading |
|---|---|---|---|---|
| base3 (main, variable unset) | 79.78 | 0.41 | | reference of this round |
| head2 (final commit, variable unset) | 79.81 | 0.38 | +0.04 % | inside the band |
| headon2 (final commit, `TRON_ATTN_STATS=1`) | 80.10 | 0.17 | +0.39 % | on-state cost: none visible |

The final binary's instruction counts: the largest `apply_page_range` instantiation is 12,603 bytes and 2,196 instructions (main: 11,866 and 2,055), with 0 lock-prefixed instructions and 0 rdtsc in both. The largest `run_attention_job` instantiation is 4,874 bytes with 9 rdtsc reads (main: 4,281 and 8).

## Cross-checks

- Binary comparison (`objdump` of the two runtron binaries, `exec/attnstats-20260924/objdump-check.sh`): 384 `apply_page_range` instantiations in both. The largest instantiation grows from 11,866 to 12,444 bytes (2,055 to 2,182 instructions). Lock-prefixed instructions: 0 in both. rdtsc in `apply_page_range`: 0 in both. The largest `run_attention_job` instantiation grows from 4,281 to 4,872 bytes and from 8 to 9 rdtsc reads. The added read runs only with the switch on. All `apply_page_range` code grows by 47,276 bytes over the 384 instantiations (+3.9 %). That is the switch-on code, compiled into every instantiation.
- The exit report prints only with the switch set: 0 `[attn-stats]` lines in every run with the variable unset, and the full report in every run with `TRON_ATTN_STATS=1`.
- Counter sanity against the closed-form visit model (qwen-3-4b tp2, 8 users, prompt 1024, 255 decode forwards, 36 layers, 8 KV heads). `ready_amx_visits` = 10,278,144, which equals the sum over the 255 steps of floor((1023 + t) / 64) x 36 x 8 x 8 exactly. `pending_amx_visits` = 6,912 = 3 steps x 2,304: the three steps whose new page was full took AMX in the same forward. That closes open point 11.1 of the design page. Prefill: `ready_amx_visits` 16,515,072 and `pending_avx_full_page_visits` 1,216,512. Full pages written in the current chunk take AVX even with AMX on, because the query sees them through several mask ranges. Token jobs by path set: decode 2,016 `avx+amx` and 24 `amx`. Prefill 1,024 `avx` (the first chunk) and 7,168 `avx+amx`.
- Live reads: while the head runtron ran, a poller read `summary`, `<class>_totals` and `<class>_forwards` under `<worktree>/stats/instance-2/model/<id>/attention/` every 15 s. The switch-unset run showed `"on":false` and empty totals. The switch-on run showed `"on":true` and rising counts (`fuse-poll.log`, 99 lines).
- Kill switch (`TRON_AMX_DISABLE=1` on the same binary with the switch set, prompt 1024, one run each). Decode, AMX on: 10,285,056 AMX visits and 0 AVX full-page visits. Decode, kill switch: 0 AMX visits and 10,285,056 AVX full-page visits. Prefill, AMX on: 16,515,072 AMX visits and 1,216,512 AVX full-page visits. Prefill, kill switch: 0 and 17,731,584. The identity `avx_full_page (kill) == amx + avx_full_page (on)` holds in both classes. The K tokens scored in software are equal in both arms (676,823,040 decode, 1,209,139,200 prefill). The counters see the same work whichever path served it.

## What the leaves look like

Read live during the switch-on run (dev-build mount `<worktree>/stats/instance-2/model/ingested-qwen-3-4b-instruct-2507-tp2/attention/`):

```
summary
{"on":true,"model_id":"ingested-qwen-3-4b-instruct-2507-tp2","eagle":false,"amx_compiled":true,
 "amx_available":true,"n_kv_heads":8,"kv_mul":4,"head_size":128,"n_layers":36,"page_size":64,
 "n_workers":27,"tsc_hz":2699999710,"switch":"TRON_ATTN_STATS=1"}
```

The stderr summary at the end of the round-4 run (head bff317e0d3, the same cell: prompt 1024, 8 users, 256 tokens, CPU attention, delphi-3bda, 2026-09-29). The class label carries the rule: `decode_like/all_jobs_with_listener` is the 255 decode steps, `prompt_or_mixed/some_jobs_without_listener` is the 8 prefill forwards.

```
[attn-stats] decode_like/all_jobs_with_listener totals: {...,"ready_amx_visits":10278144,
 "ready_amx_k_tokens":657801216,"ready_avx_full_page_visits":0,...,"pending_avx_visits":580608,
 "pending_avx_k_tokens":18579456,"pending_amx_visits":6912,"pending_amx_k_tokens":442368,...,
 "attn_jobs":183600,"busy_cycles":95886519154,"wall_cycles_w0":6227932522,"wall_max_cycles_w0":3832876,
 "period_cycles_w0":8017787702,"period_count_w0":8925,...,"join_wait_cycles":2028688892,"fpga_k_tokens":0,...}
[attn-stats] decode_like/all_jobs_with_listener forwards: {"forwards":255,"wall_cycles":8610367272,
 "wall_max_cycles":48796864,"fpga_queries":0,"token_jobs":2040,"listener_jobs":2040,"kv_only_jobs":0,
 "n_attn_workers_min":20,"n_attn_workers_max":20,"token_jobs_by_path_set":{"none":0,"avx":0,"amx":24,
 "avx+amx":2016,"fpga":0,"fpga+avx":0,"fpga+amx":0,"fpga+avx+amx":0}}
[attn-stats] prompt_or_mixed/some_jobs_without_listener totals: {...,"ready_amx_visits":16515072,...,
 "pending_avx_visits":3538944,...,"pending_avx_full_page_visits":1216512,"attn_jobs":5760,
 "busy_cycles":52874188338,...,"join_wait_cycles":5367417044,...}
[attn-stats] prompt_or_mixed/some_jobs_without_listener forwards: {"forwards":8,"wall_cycles":8605423498,
 ...,"token_jobs":8192,"listener_jobs":64,"kv_only_jobs":8128,"n_attn_workers_min":20,"n_attn_workers_max":20,
 "token_jobs_by_path_set":{"none":0,"avx":1024,"amx":0,"avx+amx":7168,...}}
```

Worker leaves, read live in a repeat of the same run (snapshot at decode forward 142 of 255). The rows of the main helpers (pool workers 0 to 6) read zero. The attention rows are pool workers 7 to 26:

```
decode_like_worker_0   {"worker":0,...,"ready_amx_visits":0,...,"attn_jobs":0,"busy_cycles":0,"join_wait_cycles":0}
decode_like_worker_7   {"worker":7,...,"ready_amx_visits":348075,"ready_amx_k_tokens":22276800,...,
                        "attn_jobs":5817,"busy_cycles":2904283836,"join_wait_cycles":47550692}
decode_like_worker_26  {"worker":26,...,"ready_amx_visits":285048,...,"pending_avx_visits":45536,...,
                        "attn_jobs":5764,"busy_cycles":2840390470,"join_wait_cycles":111578888}
```

In words, for the decode steps: 97.3 % of the K tokens scored in software went through the AMX kernel (658 M of 677 M). The rest went through the AVX loop on the partial pending page. Every generated token used AMX, and all but 24 also used AVX. For prefill: 1.06 G K tokens on AMX (the ready pages of earlier chunks) and 152 M on AVX (the current chunk's own pages). The visit and K-token counts are the same as in the 2026-09-24 run of the first commit. The forward wall (T1) sums to 8.61 G cycles over the 255 decode steps, which is 12.5 ms per step at 2.7 GHz. The split was 20 attention workers in every forward of both classes (`n_attn_workers_min` = `n_attn_workers_max` = 20), so `active_workers` is 20. The software join wait (T5) is 2.03 G cycles over the 183,600 decode jobs (4.1 us per job, 2.1 % of the busy time T2) and 5.37 G cycles over the 5,760 prefill jobs (345 us per job, 10.2 % of T2). Every prefill forward carried one 128-token chunk of each of the 8 users: 1,024 token jobs with 8 listeners (the chunk-final tokens), so 8,128 of the 8,192 prefill jobs stored K and V only.

## Verification

- delphi-3bda builds of the four review-round-3 commits (ebadce2adb as f7da0e64ab, which differs by one comment line; 0274131d23; 7f8a4aa4d8; d85edc0e28; same preset, incremental, about 10 min each). Tests with the fake device and `TRON_ATTN_STATS` unset, same counts at every build: `t_llama_unit` 219,937 assertions in 55 cases (7 assertions and 1 case fewer: the deleted switch-rule case), `t_page_share_counters` 61 in 4, `t_amx_numerics` 4,109 in 4, `t_amx_dispatch_dtype` 1,589 in 1, `t_heterogeneous_scheduler` 1,900 in 2. All pass, also with `TRON_ATTN_STATS=1`. With `TRON_ATTN_STATS=yes` a real model state (`t_heterogeneous_scheduler`) logs the "ignored" warning once.
- delphi-3bda builds of the six review-round-4 commits (6e23101744, 37bb2a4055, b6fd226982, ae8a6d38d9, 15f355acb2 as 32b918b681 which differs by three removed unused includes, bff317e0d3), same preset, incremental, on 2026-09-29. Tests with the fake device and `TRON_ATTN_STATS` unset at the head bff317e0d3: `t_llama_unit` 220,146 assertions in 61 cases, `t_heterogeneous_scheduler` 2,715 in 2, `t_amx_dispatch_dtype` 1,600 in 1, `t_compute_attention_unit` 124 in 4, `t_amx_numerics` 4,109 in 4, `t_page_share_counters` 61 in 4. All pass, also with `TRON_ATTN_STATS=1`. With `TRON_ATTN_STATS=yes` the ignored-value warning prints once. In the software-join test section the 20 ms late producer measured 54,179,328 cycles of T5 (20.07 ms at 2.7 GHz) in the 6e23101744 run.
- delphi-3bda build of 04da001cb5 (the job counts move together; tested as 8670da7f0b, which differs by comments only), same preset, incremental, on 2026-09-30 00:01 UTC. Tests with the fake device and `TRON_ATTN_STATS` unset: `t_llama_unit` 220,158 assertions in 62 cases (the new mid-forward case), the other five binaries unchanged. All pass, also with `TRON_ATTN_STATS=1`, and the `TRON_ATTN_STATS=yes` run prints the one ignored-value warning.
- CPU-attention runtron runs with `TRON_ATTN_STATS=1` on the head bff317e0d3 (delphi-3bda, our half, qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, two runs on 2026-09-29 at 23:24 and 23:38 UTC). Forwards 255 and 8, token jobs 2,040 and 8,192, the same as the 2026-09-24 runs, so `forward_scope` files every forward. `listener_jobs` 2,040 and 64, `kv_only_jobs` 0 and 8,128. Split 20 in every forward. T5 (software join) 2.03 G cycles in decode and 5.37 G cycles in prefill. The worker leaves 0 to 6 read zero and 7 to 26 carry the attention rows. The samples above come from these runs.

## Cost data

No new test target: the stats cases are part of `t_llama_unit`, whose row in `config/test-benchmarks.json` stays valid (the cases add about 0.1 s). A refresh of that row with `bin/slice bench --update t_llama_unit` (a whole-host run) can follow when delphi-3bda has a quiet window.



Refs #4303.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

