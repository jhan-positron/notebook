import sys, re
live = open(sys.argv[1], encoding='utf-8').read()
lines = live.split('\n')
assert len(lines) >= 116, len(lines)

def rep_once(text, old, new):
    n = text.count(old)
    assert n == 1, (n, old[:70])
    return text.replace(old, new)

def rep_lines(lines, first, last, must_start, new_lines):
    # first/last are 1-based inclusive line numbers of the LIVE body
    assert lines[first-1].startswith(must_start), (first, lines[first-1][:60])
    return lines[:first-1] + new_lines + lines[last:]

# ---- block replacements first, from the bottom up so line numbers stay valid ----
# Verification (line 106 kept, new bullets after it)
verif_new = [
"- delphi-3bda builds at five points along the six review-round-4 commits (37bb2a4055 which includes 6e23101744, b6fd226982, ae8a6d38d9, 32b918b681 which is 15f355acb2 before a fixup that removed three includes, and bff317e0d3), same preset, incremental, on 2026-09-29. Tests with the fake device and `TRON_ATTN_STATS` unset at bff317e0d3: `t_llama_unit` 220,146 assertions in 61 cases, `t_heterogeneous_scheduler` 2,715 in 2, `t_amx_dispatch_dtype` 1,600 in 1, `t_compute_attention_unit` 124 in 4, `t_amx_numerics` 4,109 in 4, `t_page_share_counters` 61 in 4. All pass, also with `TRON_ATTN_STATS=1`. With `TRON_ATTN_STATS=yes` the ignored-value warning prints once.",
"- delphi-3bda build of 04da001cb5 (tested as 8670da7f0b, which differs by comments only), same preset, incremental, on 2026-09-30 00:00 UTC. Tests with the fake device and `TRON_ATTN_STATS` unset: `t_llama_unit` 220,158 assertions in 62 cases (the new mid-forward case), the other five binaries unchanged. All pass, also with `TRON_ATTN_STATS=1`, and the `TRON_ATTN_STATS=yes` run prints the one ignored-value warning.",
"- The eight commits after 04da001cb5 (seven test-only commits from the 2026-09-29 review, 7f86648d10 to 0f784c44ff, and 441e81178b, which scrubs seven comments, drops one duplicate test case and routes the row key of `note_attn_job` through the `pool_worker` helper) were built and tested in the development container (nix shell, clang 19.1.7, RelWithDebInfo, `-DTRON_AMX_DISPATCH=ON`), not on delphi-3bda. The container reproduces the delphi-3bda counts at 04da001cb5 exactly. Five binaries, each run with `TRON_ATTN_STATS` unset, `=1` and `=yes`, at 441e81178b: `t_llama_unit` 220,153 assertions in 60 cases, `t_heterogeneous_scheduler` 2,783 in 3 (the new real-forward case), `t_amx_dispatch_dtype` 1,612 in 1, `t_compute_attention_unit` 124 in 4, `t_page_share_counters` 61 in 4. All pass. `=yes` logs the ignored-value warning once per model state. `t_amx_numerics` has no file of this PR and was last run on delphi-3bda at 8670da7f0b.",
"- 8c95514924 merges main 9b60b69dce (2026-09-30 20:23 UTC) into the branch, after the approval at 441e81178b. One textual conflict, in the comment list of Note [Attention workers are the last pool workers] in `model.hpp` (both sides added a bullet, both kept). The five test binaries were rebuilt and run in the development container at the merge commit with the same counts as at 441e81178b.",
"- CPU-attention runtron runs with `TRON_ATTN_STATS=1` on bff317e0d3 (delphi-3bda, our half, qwen-3-4b tp2, 8 users, prompt 1024, 256 tokens, `USE_HW_ATTN=0`, two runs on 2026-09-29 at 23:24 and 23:38 UTC). Forwards 255 and 8, token jobs 2,040 and 8,192, the same counts as the 2026-09-24 runs. So `forward_scope` files every forward. `listener_jobs` 2,040 and 64, `kv_only_jobs` 0 and 8,128. Split 20 in every forward. T5 (software join) 2.03 G cycles in decode and 5.37 G cycles in prefill. The worker leaves 0 to 6 read zero and 7 to 26 carry the attention rows. The samples above come from these runs: the stderr summary from the first, the worker leaves from the second.",
]
lines = lines[:106] + verif_new + lines[106:]

# In words (line 102)
inwords = [
"In words:",
"",
"- For the decode steps: 97.3 % of the K tokens scored in software went through the AMX kernel (658 M of 677 M). The rest went through the AVX loop on the partial pending page. Every generated token used AMX, and all but 24 also used AVX.",
"- For prefill: 1.06 G K tokens on AMX (the ready pages of earlier chunks) and 152 M on AVX (the current chunk's own pages).",
"- The forward wall (T1) sums to 8.61 G cycles over the 255 decode steps, which is 12.5 ms per step at 2.7 GHz.",
"- The split was 20 attention workers in every forward of both classes (`n_attn_workers_min` = `n_attn_workers_max` = 20), so `active_workers` is 20. The visit and K-token counts are the same as in the 2026-09-24 run of the first commit.",
"- The software join wait (T5) is 2.03 G cycles over the 183,600 decode jobs (4.1 us per job, 2.1 % of the busy time T2) and 5.37 G cycles over the 5,760 prefill jobs (345 us per job, 10.2 % of T2). The same cell read T5 = 0 before review round 4 widened T5 to the software-only join.",
"- Every prefill forward carried one 128-token chunk of each of the 8 users: 1,024 token jobs with 8 listeners (the chunk-final tokens), so 8,128 of the 8,192 prefill jobs stored K and V only.",
]
lines = rep_lines(lines, 102, 102, "In words, for the decode steps", inwords)

# stderr sample block (lines 89-100) + worker leaves
sample = [
"```",
"[attn-stats] decode_like/all_jobs_with_listener totals: {...,\"ready_amx_visits\":10278144,",
" \"ready_amx_k_tokens\":657801216,\"ready_avx_full_page_visits\":0,...,\"pending_avx_visits\":580608,",
" \"pending_avx_k_tokens\":18579456,\"pending_amx_visits\":6912,\"pending_amx_k_tokens\":442368,...,",
" \"attn_jobs\":183600,\"busy_cycles\":95886519154,\"wall_cycles_w0\":6227932522,\"wall_max_cycles_w0\":3832876,",
" \"period_cycles_w0\":8017787702,\"period_count_w0\":8925,...,\"join_wait_cycles\":2028688892,\"fpga_k_tokens\":0,...}",
"[attn-stats] decode_like/all_jobs_with_listener forwards: {\"forwards\":255,\"wall_cycles\":8610367272,",
" \"wall_max_cycles\":48796864,\"fpga_queries\":0,\"token_jobs\":2040,\"listener_jobs\":2040,\"kv_only_jobs\":0,",
" \"n_attn_workers_min\":20,\"n_attn_workers_max\":20,\"token_jobs_by_path_set\":{\"none\":0,\"avx\":0,\"amx\":24,",
" \"avx+amx\":2016,\"fpga\":0,\"fpga+avx\":0,\"fpga+amx\":0,\"fpga+avx+amx\":0}}",
"[attn-stats] prompt_or_mixed/some_jobs_without_listener totals: {...,\"ready_amx_visits\":16515072,...,",
" \"pending_avx_visits\":3538944,...,\"pending_avx_full_page_visits\":1216512,\"attn_jobs\":5760,",
" \"busy_cycles\":52874188338,...,\"join_wait_cycles\":5367417044,...}",
"[attn-stats] prompt_or_mixed/some_jobs_without_listener forwards: {\"forwards\":8,\"wall_cycles\":8605423498,",
" ...,\"token_jobs\":8192,\"listener_jobs\":64,\"kv_only_jobs\":8128,\"n_attn_workers_min\":20,\"n_attn_workers_max\":20,",
" \"token_jobs_by_path_set\":{\"none\":0,\"avx\":1024,\"amx\":0,\"avx+amx\":7168,...}}",
"```",
"",
"Worker leaves, read live in the second run (snapshot at decode forward 142 of 255). The rows of the main helpers (pool workers 0 to 6) read zero. The attention rows are pool workers 7 to 26:",
"",
"```",
"decode_like_worker_0   {\"worker\":0,...,\"ready_amx_visits\":0,...,\"attn_jobs\":0,\"busy_cycles\":0,\"join_wait_cycles\":0}",
"decode_like_worker_7   {\"worker\":7,...,\"ready_amx_visits\":348075,\"ready_amx_k_tokens\":22276800,...,",
"                        \"attn_jobs\":5817,\"busy_cycles\":2904283836,\"join_wait_cycles\":47550692}",
"decode_like_worker_26  {\"worker\":26,...,\"ready_amx_visits\":285048,...,\"pending_avx_visits\":45536,...,",
"                        \"attn_jobs\":5764,\"busy_cycles\":2840390470,\"join_wait_cycles\":111578888}",
"```",
]
lines = rep_lines(lines, 89, 100, "```", sample)

# line 87 intro of the stderr sample
lines = rep_lines(lines, 87, 87, "The stderr summary at the end of that run", [
"The stderr summary at the end of the first of the two 2026-09-29 runs (prompt 1024, 8 users, 256 tokens, CPU attention). The class label carries the rule: `decode_like/all_jobs_with_listener` is the 255 decode steps, `prompt_or_mixed/some_jobs_without_listener` is the 8 prefill forwards."])

# summary sample (lines 80-85) and its intro (78)
lines = rep_lines(lines, 84, 84, ' "n_workers":27,"tsc_hz":2699999710', [' "n_workers":27,"active_workers":20,"tsc_hz":2699986182,"switch":"TRON_ATTN_STATS=1"}'])
lines = rep_lines(lines, 78, 78, "Read live during the switch-on run", [
"Read live during the switch-on run of 2026-09-29 (bff317e0d3, whose leaf format is unchanged up to the head; dev-build mount `<worktree>/stats/instance-2/model/ingested-qwen-3-4b-instruct-2507-tp2/attention/`):"])

# A/A: new paragraph after line 66
aa_new = [
"",
"No A/A was run after cbf1bb6c0c. The branch has 22 more commits up to 441e81178b, and 8c95514924 then merges main into the branch. Since the cbf1bb6c0c binary the off path changed in three places. Each is a bool test with no memory write:",
"",
"- `forward_scope` replaces the scheduler's begin and end calls: one bool copied per forward and tested three times.",
"- The software-only join poll tests the stats bool once per failed poll, and one local bool per KV head joined. With the switch unset it reads no rdtsc.",
"- `apply_page_range` computes the pool-worker row key only with the switch set: one more test per call. The per-visit test is unchanged.",
"",
"The binary check was repeated on 2026-09-30 on the delphi-3bda build of 8670da7f0b (04da001cb5 with comment-only edits, so 441e81178b differs from it by one helper call on the on path of `run_attention_job` and by comments). The per-visit contract holds there: 384 `apply_page_range` instantiations, the largest 12,708 bytes and 2,217 instructions (main: 11,866 and 2,055), 0 lock-prefixed instructions and 0 rdtsc in both. All `apply_page_range` code grows by 79,633 bytes over the 384 instantiations (+6.5 %). That is the switch-on code, compiled into every instantiation. The largest `run_attention_job` instantiation is 4,941 bytes with 9 rdtsc reads (main: 4,281 and 8).",
]
assert lines[65].startswith("The final binary's instruction counts")
lines = lines[:66] + aa_new + lines[66:]

# Tests block (lines 29-32)
tests_new = [
"- New `t/t_attn_stats.cpp`, 17 cases: tallies, rows, path sets, timers, class routing, JSON leaves and their size, the exit report, FUSE registration with the weak_ptr rule, the last-wins takeover, the EAGLE directory, the `forward_scope` object, the three job counts of a forward, the rows keyed by pool worker, the fold over the attention rows only, the off-state leaves, and the fork-based negative case for an out-of-range worker, layer or token job (every hook index is a `TRON_ASSERT`). The switch rule (exactly \"1\") has no unit case: the reader is one function that reads the environment once, and the `TRON_ATTN_STATS=yes` runs on delphi-3bda and in the development container check the warning. The file is compiled into the `t_llama_unit` binary, so it needs no cost-data row of its own (a row needs a whole-host bench run).",
"- `t/t_llama_unit.cpp`: the fake-lane `apply_page_range` case asserts the stats-on tallies (32 AVX visits of 32 K tokens each, no AMX, no empty visit). The CI lane compiles without `TRON_AMX_DISPATCH`, and this case exercises the per-visit hook there. The case also reads the forward's path sets back (32 jobs `avx`, 32 jobs `none`), checks that the visits land in the last pool row, and repeats the call under a 2-worker split, where the same attention worker lands one row earlier. The two direct `stream_hw_joins` cases pass a real T5 accumulator and check 0. Every sweep there makes progress, so no wait is counted. After a production `apply_page_range` call, the state's own stats object is checked to follow `TRON_ATTN_STATS`.",
"- `t/t_amx_dispatch_dtype.cpp` asserts the amx/avx split against the kernel fakes' call counts, with a section where the fake `available()` answers false (one AVX visit that scored the whole page), and reads the path sets back after each call (the AMX set exactly when the kernels ran, else the AVX set). It also gets the `apply_page_range` argument main's copy lacks (the batch query mask). Main's copy does not compile with `-DTRON_AMX_DISPATCH=ON`, and #4557 carries the same fix.",
"- `t/heterogeneous_scheduler_compile.cpp`: the mixed-attention section checks the hardware join's T5 (greater than 0 and at most the join's wall time). The Q-reuse section reads T2, T3 and T4 back through `run_attention_job` (T3 includes the upstream K/V wait that a 20 ms probe makes real, T2 does not, so T3 exceeds T2). A new section runs `run_joins` with no hardware plan against a producer that finishes 20 ms late, in three arms: late producer with stats on (T5 greater than 0 and at most the wall time), sections already done (T5 = 0), stats flag off (T5 = 0). Another section reaches `note_fpga_pass` through `prepare_hw_attention`. A new case drives `model::state::forward` with the switch forced on and reads one whole record back (the class, the three job counts, T1 and the split) for a decode-like and a prompt-or-mixed forward. The fixtures that drive `apply_page_range` or `run_attention_job` with the switch on open a `forward_scope` first, as production does. This file and the direct `t_llama_unit` callers follow the new `run_joins` and `stream_hw_joins` parameters.",
"- New `t/assertion_signal.hpp`: the fork-based helper that expects an abort, moved out of `t_llama_unit.cpp` and `t_compute_attention_unit.cpp` and shared with the negative case above.",
]
lines = rep_lines(lines, 29, 32, "- New `t/t_attn_stats.cpp`, 12 cases", tests_new)

text = '\n'.join(lines)

# ---- single-line replacements ----
text = rep_once(text, "and how long attention took, per layer and per attention worker. ",
                      "and how long attention took, per layer and per pool worker (one thread of the application thread pool). ")
text = rep_once(text, "`prompt_or_mixed` is every other forward.\n",
"`prompt_or_mixed` is every other forward. Under continuous batching (rinzler, the production server, adds and removes users between forwards) a forward that carries any user's prompt chunk is `prompt_or_mixed`. So `decode_like` counts pure-decode forwards only.\n"
"- listener: the consumer of one token job's logits. Every generated token has one, and so does the last token of a prompt chunk (the slice of a prompt that one forward processes). A prompt token without a listener only stores its K and V.\n"
"- pool worker: one thread of the application thread pool (`n_workers` in `summary`, 27 in the runs below). The attention workers of a forward are its last `n_attn_workers` pool workers. The first pool workers, the main helpers, do the non-attention work, and their attention rows read zero.\n")
text = rep_once(text, "- T1 = wall time of one model forward, around `state.forward(...)` in the scheduler. Logits and listener delivery are inside. Scheduler work before and after is outside.",
"- T1 = wall time of one model forward, taken by `forward_scope` (the one object that owns the per-forward record) inside `model::state::forward`, from just after the trace marker at its top to its return. The layers, the logits, the listener delivery and the release of the forward's synchronization latches (the latch arena) are inside. Scheduler work before and after is outside.")
text = rep_once(text, "- T3 = wall time of one attention job as worker 0 sees it (entry to return).",
"- T3 = wall time of one attention job as attention worker 0 sees it (entry to return), filed per layer. The layer and totals leaves carry the T3 and T4 keys (`wall_cycles_w0`, `period_cycles_w0` and their companions). The worker leaves do not.")
text = rep_once(text, "- T4 = layer period on worker 0: from its first job",
                      "- T4 = layer period on attention worker 0, filed per layer: from its first job")
text = rep_once(text, "- T5 = `join_wait_cycles`: the time a worker spends in the join's wait loop. The loop ends when an FPGA pass or the other workers' software partials become ready.",
"- T5 = `join_wait_cycles`: the time a worker spends waiting in the join with no join progress, in both join modes. In a hardware join it is the wait loop that ends when an FPGA pass or the other workers' software partials become ready. In a software-only join (CPU attention) it is the stretches of failed polls on the other workers' sections. T5 is inside T2.")
text = rep_once(text, "(PR3879/new-PRs/PR1/counter.html, section 9)", "(PR3879/new-PRs/new-counters/counter.html, section 9)")
text = rep_once(text, "Confirmation round on the final commit cbf1bb6c0c, the same cell",
                      "Confirmation round on cbf1bb6c0c (the head on 2026-09-24), the same cell")
text = rep_once(text, "| head2 (final commit, variable unset) |", "| head2 (cbf1bb6c0c, variable unset) |")
text = rep_once(text, "| headon2 (final commit, `TRON_ATTN_STATS=1`) |", "| headon2 (cbf1bb6c0c, `TRON_ATTN_STATS=1`) |")
text = rep_once(text, "The final binary's instruction counts:", "The cbf1bb6c0c binary's instruction counts:")
text = rep_once(text, "- Binary comparison (`objdump` of the two runtron binaries, `exec/attnstats-20260924/objdump-check.sh`):",
                      "- Binary comparison (`objdump` of the two runtron binaries, main 66c7bb8db1 and the first commit 9b3832eb4b, `exec/attnstats-20260924/objdump-check.sh`):")
text = rep_once(text, "Prefill 1,024 `avx` (the first chunk) and 7,168 `avx+amx`.",
                      "Prefill 1,024 `avx` (the first chunk) and 7,168 `avx+amx`. The 2026-09-29 runs at bff317e0d3 (the samples below) reproduce every visit, K-token and path-set count.")
text = rep_once(text, "The switch-unset run showed `\"on\":false` and empty totals. The switch-on run showed",
                      "The switch-unset run showed `\"on\":false`, `{}` for the two totals leaves and a zero-filled object for the two forwards leaves. Since 1430736b2a both class leaves read `{}` with the switch unset, and a unit case checks it. The switch-on run showed")
text = rep_once(text, "- Kill switch (`TRON_AMX_DISABLE=1` on the same binary with the switch set, prompt 1024, one run each).",
                      "- Kill switch (`TRON_AMX_DISABLE=1` on the same 9b3832eb4b binary with the switch set, prompt 1024, one run each, 2026-09-24).")
open(sys.argv[2], 'w', encoding='utf-8').write(text)
print("lines live", len(live.split('\n')), "new", len(text.split('\n')))
