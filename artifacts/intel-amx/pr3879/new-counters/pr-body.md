# Attention path stats: AVX / AMX / FPGA shares and timers behind TRON_ATTN_STATS

## Short version

This PR counts how much of a model's attention work ran on each path (the AVX software loop, the AMX kernel, the FPGA) and how long attention took, per layer and per attention worker. One environment variable, `TRON_ATTN_STATS=1`, turns collection on at run time. The numbers come out as FUSE leaves under `/model/<id>/attention/` and as one stderr summary at the end of a runtron run.

## Words used here

- tron: the inference program. runtron: its command-line tool. rinzler: the production server.
- AMX, AVX: Intel instruction sets. AMX = the tile-matrix instructions of the software attention kernel merged in #3879. AVX = the AVX-512 vector instructions of the older software attention loop (the "dotter" loop in `apply_page_tok`). The kill switch `TRON_AMX_DISABLE=1` turns the AMX kernel off at run time.
- FPGA attention: attention computed on the accelerator card (also called AoF or HW attention in the code).
- visit: one call of `apply_page_tok`. That is one (query token, KV page of 64 tokens, KV head) triple that passed the page-level checks of `apply_page_range`. The AMX kernel serves a whole dense page per visit. The AVX loop serves the relevant K tokens of the page. An empty visit found no software work.
- K tokens: cached key rows multiplied against the query. Dot products = K tokens x kv_mul (query heads per KV head).
- forward: one model run for all users' pending token jobs. Forward class: `decode_like` when every token job has a listener (one generated token per user, but also a one-token final prompt chunk or a speculative verify step). `prompt_or_mixed` is every other forward.
- ready pass and pending pass: pages written in earlier forwards, and pages written in this forward.
- FUSE leaves: files in tron's live statistics tree (`README.stats.md`). Casual leaves carry no export convention.
- TPS: decode tokens per second per user. sd: sample standard deviation. A/A: two runs that should be equal (same code). band: the run-to-run spread of one binary measured twice.
- T1 to T5: the five timers, defined under "What changes".

## What changes

New header `h/tron/models/attn_stats.hpp` with `Note [Attention path stats]`:

- `visit_tally`: plain integers on the stack, one object per `apply_page_range` call.
- One row per (forward class, attention worker, layer). A row holds visits and K tokens per path (`empty`, `avx`, `amx`) and per pass, the AVX visits that scored a whole page (AMX-eligible volume that did not take AMX), and T2 to T5 in TSC cycles. Only the owning worker writes its row, with relaxed load-add-store and no lock prefix. The FUSE callbacks read the same atomics with relaxed loads.
- FPGA K tokens (inclusive last index + 1 per query) and query passes, per forward class and layer. Forwards, T1, token jobs with FPGA work, and token jobs by path set (`none`, `avx`, `amx`, `avx+amx`, `fpga`, ...) per forward class.
- JSON renderers and the FUSE registration: `summary`, `<class>_totals`, `<class>_forwards`, and with the switch on also `<class>_layer_<L>` and `<class>_worker_<W>`. Every callback captures a `weak_ptr`, so a read after the model state is gone returns `{}`. An EAGLE draft state shares the target's id and publishes under `attention_eagle/`. A later state of the same id takes the leaves over, with one info line in the log (runtron builds one state per prompt batch).
- A stderr summary from the destructor when the switch was on and anything was counted. A batch runtron run destroys the state before the tree can be read, so the summary is the end-of-run record.

Timers, all in TSC cycles (`summary` carries `tsc_hz`):

- T1 = wall time of one model forward, around `state.forward(...)` in the scheduler. Logits and listener delivery are inside. Scheduler work before and after is outside.
- T2 = busy time of one attention job on one worker. This is `attn_elapsed`, which exists today: both passes and the join, without the upstream K/V wait.
- T3 = wall time of one attention job as worker 0 sees it (entry to return).
- T4 = layer period on worker 0: from its first job of one attention operation to its first job of the next operation. The second minibatch of the same operation starts no period. The last layer of a forward has no period.
- T5 = `join_wait_cycles`: the time a worker spends in the join's wait loop. The loop ends when an FPGA pass or the other workers' software partials become ready.

Hooks:

- `apply_page_tok` returns `page_tok_result {hint, relevant_k_tokens, served}` instead of the pair. The struct has the size of the pair (16 bytes, a static_assert keeps it so). The three exits name their path.
- `apply_page_range` copies `stats->on` once per call. Behind that bool it tallies per visit, records each token job's path bit through a span hoisted per call, and adds the tally to the worker's row once per call.
- `run_attention_job` records T2 and T3 per job and T4 by the operation-change rule.
- `stream_hw_joins` gets a `uint64_t*` accumulator (nullptr when off) and times only its wait loop. `run_joins` passes it and records the sum per job.
- `prepare_uniform_hw_attention` counts the FPGA K tokens and queries per pass. `construct_hw_plan` counts the token jobs with at least one FPGA pass from `hw_plan.by_job` after `set_passes`.
- `model::state::run_forward` sets the forward class and sizes the path bits before `plugin_state.run`, and folds the bits after it.
- `full_scheduler::forward` times the forward (T1).
- perfetto: a `"layer"` argument on the `Attention Ready` / `Attention Pending` span, and `"n_listeners"` on the `forward` event.

Docs: `README.stats.md` describes the leaves and the switch.

Tests:

- New `t/t_attn_stats.cpp`, 13 cases: tallies, rows, path sets, timers, the switch rule, class routing, JSON leaves and their size, the exit report, FUSE registration with the weak_ptr rule, the last-wins takeover, the EAGLE directory. The file is compiled into the `t_llama_unit` binary, so it needs no cost-data row of its own (a row needs a whole-host bench run).
- `t/t_llama_unit.cpp`: the fake-lane `apply_page_range` case asserts the stats-on tallies (32 AVX visits of 32 K tokens each, no AMX, no empty visit). The CI lane compiles without `TRON_AMX_DISPATCH`, and this case exercises the per-visit hook there.
- `t/t_amx_dispatch_dtype.cpp` asserts the amx/avx split against the kernel fakes' call counts. It also gets the two `apply_page_range` arguments main's copy lacks. Main's copy does not compile with `-DTRON_AMX_DISPATCH=ON`, and #4557 carries the same fix.
- `t/heterogeneous_scheduler_compile.cpp` and the direct `t_llama_unit` callers follow the new `run_joins` and `stream_hw_joins` parameters.

C++ guide: named values and braces on the added lines. Left as they are, on purpose, and listed here as the guide asks: loop starts (`i = 0`), zero-initializers of counters and facts (`= 0`, `= false`, `{}`), `return true` and `return false` in predicates, and emptiness tests (`== 0`, `!= 0`, the repository's idiom).

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

The stderr summary at the end of that run (prompt 1024, 8 users, 256 tokens). The `decode_like` class is the 255 decode steps. The `prompt_or_mixed` class is the 8 prefill forwards.

```
[attn-stats] decode_like totals: {"ready_empty_visits":0,...,"ready_amx_visits":10278144,
 "ready_amx_k_tokens":657801216,"ready_avx_full_page_visits":0,...,"pending_avx_visits":580608,
 "pending_avx_k_tokens":18579456,"pending_amx_visits":6912,"pending_amx_k_tokens":442368,...,
 "attn_jobs":183600,"busy_cycles":95498357004,"wall_cycles_w0":6171775010,...,
 "period_cycles_w0":7933853172,"period_count_w0":8925,...,"join_wait_cycles":0,"fpga_k_tokens":0,...}
[attn-stats] decode_like forwards: {"forwards":255,"wall_cycles":8518609356,"wall_max_cycles":43970704,
 "fpga_queries":0,"token_jobs":2040,"token_jobs_by_path_set":{"none":0,"avx":0,"amx":24,"avx+amx":2016,
 "fpga":0,"fpga+avx":0,"fpga+amx":0,"fpga+avx+amx":0}}
[attn-stats] prompt_or_mixed totals: {...,"ready_amx_visits":16515072,...,"pending_avx_visits":3538944,
 ...,"pending_avx_full_page_visits":1216512,"attn_jobs":5760,...}
```

In words, for the decode steps: 97.3 % of the K tokens scored in software went through the AMX kernel (658 M of 677 M). The rest went through the AVX loop on the partial pending page. Every generated token used AMX, and all but 24 also used AVX. For prefill: 1.06 G K tokens on AMX (the ready pages of earlier chunks) and 152 M on AVX (the current chunk's own pages). The forward wall (T1) sums to 8.52 G cycles over the 255 decode steps, which is 12.4 ms per step at 2.7 GHz. The first commit's `summary` had no `active_workers`. The final commit adds it: 20 attention workers were active in this run (183,600 jobs / 255 forwards / 36 layers).

## Verification

- Syntax-only compile (clang 19.1.7) of `t_attn_stats.cpp`, `t_llama_unit.cpp`, `t_amx_dispatch_dtype.cpp` and `heterogeneous_scheduler_compile.cpp` in the AMX-on and AMX-off configurations: clean at every commit.
- delphi-3bda build of 9b3832eb4b (cross-avx512 preset, ingest models on, AMX on, runtron plus the tests, 759 s on 48 jobs). Tests with the fake device and `TRON_ATTN_STATS` unset: `t_attn_stats` 113 assertions in 8 cases, `t_page_share_counters` 61 in 4, `t_llama_unit` 219,765 in 43, `t_amx_numerics` 4,109 in 4 (real AMX), `t_amx_dispatch_dtype` 1,589 in 1. All pass. With `TRON_ATTN_STATS=1`, `t_attn_stats` and `t_llama_unit` pass with the same counts.
- delphi-3bda build of the final commit cbf1bb6c0c (same preset, 649 s). Tests with the fake device and `TRON_ATTN_STATS` unset: `t_llama_unit` 219,944 assertions in 56 cases (the 13 stats cases included), `t_page_share_counters` 61 in 4, `t_amx_numerics` 4,109 in 4 (real AMX), `t_amx_dispatch_dtype` 1,589 in 1, `t_heterogeneous_scheduler` 1,900 in 2. All pass. With `TRON_ATTN_STATS=1`: `t_llama_unit` and `t_heterogeneous_scheduler` pass with the same counts. With `TRON_ATTN_STATS=yes`: the stats cases pass and the log carries the "ignored" warning.
- clang-format 19.1.7: clean on every touched file.

## Cost data

No new test target: the stats cases are part of `t_llama_unit`, whose row in `config/test-benchmarks.json` stays valid (the cases add about 0.1 s). A refresh of that row with `bin/slice bench --update t_llama_unit` (a whole-host run) can follow when delphi-3bda has a quiet window.

## Not in this PR

The per-phase timers of design-page section 6 (QK, softmax step, PV per visit, a lab-build option). The AVX-visit reasons, hollow tile regions, Q packs per call, DMA lag, HBM fallback, prefill accounting and inter-token latency of section 7. A unit test of the forward-class rule itself (the class-routing test drives `begin_forward` with an explicit class). Runtime evidence for the FPGA counters and T5 (the runs above used CPU attention, so those counters read 0). The page-share counters of #4267 keep their CMake option, and #4303 stays open for them.

Refs #4303.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
