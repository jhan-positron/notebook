# Handoff: the VNNI K store, measured and shortened (2026-09-14/15)

Short version. The VNNI K store of the jhan-amx-vnniK branch ("Save K", one thread, per layer) was traced at 859 us per prefill layer against 274 us for the baseline, on the critical path, and is the cause of the branch's TTFT cost. The fix, a striped block store (the pass's tokens cut into page-block units that the main thread and the idle helper threads write as whole cache lines), is built as commits 9928cb2849 and 10fc7c724c on that branch, tested, and measured: the prompt-1024 TTFT drops by 128 ms at tp2 and 254 ms at tp4 against the unchanged store, which puts the branch 45-88 ms below the AMX baseline, with decode TPS unchanged. Nothing is pushed; the action plan (section 5) starts with removing the two measurement switches.

## Words used here

| Term | Meaning |
|---|---|
| tron, runtron | tron is the inference program under test; runtron is its command-line tool, which produced every number here. |
| AMX, VNNI layout | AMX is the Intel matrix instruction set used for CPU attention. The VNNI layout is the pair-interleaved K layout the branch stores K in, so that the AMX kernel reads K without a transpose. |
| Save K, Save V | The functions (model.hpp save_k_impl / save_v_impl, traced as spans of those names) that copy the K and V vectors of a pass's tokens into the KV cache, once per layer per pass, on the main thread. |
| pass | One forward() call. In the measured runs a prefill pass holds 128 tokens of each of the 8 users (1024 token jobs); a decode pass holds one token per user. |
| main thread, main helpers, attention workers | The generated qwen plugin runs the pass on one main thread; a fixed set of main helpers runs the per-token kernels in stripes; the other application-pool threads are attention workers (tp2: 1 + 7 + 20 on 28 cores; tp4: 1 + 15 + 40 on 56). The split is re-decided per pass. |
| tp2, tp4 | The model split over two or four FPGA cards (tensor parallelism); our half of delphi-3bda is socket 1, cards 90/93 (tp2) or 90/93/b9/bc (tp4). |
| TTFT, TPS | Time to first token = runtron's "Parsing the prompt took" (the batched prefill of the 8 prompts). TPS = generated tokens per second per user in decode. |
| arms | base = PR #3879 binary (row-major K). vnni = Monday's VNNI binary (5e45ae55ae). vnni0 / a / b / ab = one new binary with the two remedies off / block store only / striping only / both. |
| block store (a) | k_vnni::store_block + page::set_k_block: the 16 K rows of one page block are transposed in registers and written as whole 64-byte lines (64 full-line stores per block and KV head) instead of 64 scatters writing 4 bytes into each of 64 lines. |
| striping (b) | Note [Striped K store] in model.hpp: the generated helpers call save_k_helper at the attention statement; main cuts the pass's items into page-block work units, opens a window, every thread claims units from one atomic counter, main waits for all helpers' finished counts, then marks the tokens and releases the attention. |

## 1. State of the code

Branch **jhan-amx-vnniK**, repository ~/workspace/tron, worktree `VNNIed-K-in-place/tron-VNNIed-K`. Tracks origin/jhan-amx-p0, 9 commits ahead, **not pushed**.

| commit | content | state |
|---|---|---|
| 5e45ae55ae | Monday's VNNIed-K tip (K in the VNNI layout, per-token scatter store) | measured Monday (status/Monday-morning-report.html) |
| 9928cb2849 | (a) block store + (b) helper striping, both on by default; switches TRON_K_VNNI_BLOCK=0 and TRON_K_VNNI_STRIPE=0 (exact "0" turns one off) | built as runtron.vnnik2; all cells of section 3 measured with it |
| 10fc7c724c | review fixes: page-block work units instead of 16-item blocks, one join counter, 120-s time-based watchdog, more than 128 workers turns striping off, save_k_helper descriptor overload, model-level test in t_llama_unit, exact emitter-test assertions, comment wording | built as runtron.vnnik3; confirmation round measured with it |

Files changed by the two commits: h/tron/kernels/k_vnni.hpp, h/tron/models/kv_cache.hpp, h/tron/models/common.hpp (batch::k_store_window), h/tron/models/model.hpp (store_k_block, k_store_cut_units, save_k_helper, save_k_impl), ingest/src/TronCpp.hs (helper call emitted at the attention statement; save_k receives n_workers), ingest/test/LoopyTronSpec.hs, t/t_k_vnni_layout.cpp, t/t_llama_unit.cpp.

Tests passing at 10fc7c724c (TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON, fake device, delphi-3bda): t_k_vnni_layout (5 cases, 63426 assertions), t_amx_numerics (real AMX, 4621), t_amx_dispatch_dtype (1559), t_llama_unit (30 cases, 122438, includes the new save_k grouping and striped-window test with two helper threads), and the Haskell emitter suite (cabal test, 7514 examples).

Greedy smoke (1 user, prompt 1024, 128 tokens, temperature 0, pay-for-determinism): the arms vnni, vnni0, a, b, ab and the A/A repeat ab2 produced identical tokens, in both campaigns. The store is data movement, so any difference would be a defect.

## 2. What was measured and found

Report page: `status/store-remedies-report.html` (generator `exec/vnnik2-20260915/gen_report.py`), published as artifact https://claude.ai/artifact/E8czhhjwBmC2qqPvVKPthD (republish with the same file path from the publishing session, or with `url`).

Trace measurement (exec/results/vnnik-trace-20260914, base and vnni at tp2 and tp4, prompt 1024, 8 users, in-process Perfetto with `--trace-gen FILE --trace-passes 1-16` and `TRON_TRACE_CATEGORIES="-*,+model,+scheduler"`):

| | base | vnni |
|---|---|---|
| Save K per prefill layer (tp2 / tp4) | 274 / 281 us | 859 / 862 us |
| share of a prefill pass | 2.5% / 3.7% | 7.7% / 10.5% |
| Save K per decode layer | 4.6 / 5.8 us | 28 / 35 us |

Readings. In prefill the pending attention sections start only after Save K and Save V, so the span is on the critical path in every layer; the 585 us per layer difference is 169 ms per 8 x 1024-token prefill, which equals the measured +171 ms TTFT at tp4 (at tp2 the transpose-free kernel offsets about 100 ms, est., net +71 ms). In decode the span is 6x the baseline's but hidden: the attention workers run Ready sections during it and each worker's Pending section waits for its own Ready work, about 110 us later. Decode Save K is unchanged by the remedies (one token per user per step: no run to transpose, no window).

Remedies, main campaign (exec/results/vnnik2-20260915, 84 runs, 0 failures, binary 9928cb2849; TTFT in seconds, 8 users, prompt 1024):

| arm | tp2 TTFT | tp4 TTFT | Save K per layer tp2 / tp4 |
|---|---|---|---|
| base | 3.143 | 2.197 | 274 / 281 us |
| vnni0 (old store) | 3.226 | 2.362 | 858 / 863 us |
| a (block store) | 3.135 | 2.208 | 346 / 353 us |
| b (striping) | 3.101 | 2.130 | 175 / 110 us |
| ab (both) | 3.098 (-128 ms vs vnni0, -45 vs base) | 2.108 (-254 ms vs vnni0, -88 vs base) | 80 / 60 us |

Prompt 2048: ab -112 ms (tp2) and -120 ms (tp4) against base. Prompt 8192: ab -1.37 s (tp2) and -0.52 s (tp4) against base. Decode TPS unchanged in every arm (tp2 within 0.4%; tp4 has a 1-3 TPS spread over 2 repetitions, as on Monday). vnni0 equals vnni within noise (no build drift).

Confirmation round (exec/results/vnnik2-confirm-20260915, binary 10fc7c724c, prompt 1024, 2 repetitions): ab vs vnni0 -135 ms (tp2) and -252 ms (tp4); ab vs base -56 / -77 ms. The page-block units perform like the 16-item blocks on these aligned passes; they matter when a user's chunk does not start at a multiple of 16 items.

## 3. Machine state (delphi-3bda, our half)

| path | content |
|---|---|
| /var/tmp/jhan/tron-p0perf13/gen/runtron.p0perf13 | base binary, commit 544ca05c7a (PR #3879 head) |
| /var/tmp/jhan/tron-vnnik/gen/runtron.vnnik | Monday's VNNI binary, 5e45ae55ae |
| /var/tmp/jhan/tron-vnnik2/gen/runtron.vnnik2 | 9928cb2849 (a, b, ab arms via the switches) |
| /var/tmp/jhan/tron-vnnik3/gen/runtron.vnnik3 | 10fc7c724c (review-fixed) |
| /var/tmp/jhan/traces/ | local copies of the traces (also copied to exec/results) |

All are git worktrees of ~/workspace/tron-amx on local disk; no campaign is running; hugepage files were removed by the campaigns. The nightly CI takes the lease around 03:38 UTC; the pre-CI hold is 01:40-03:45 UTC.

## 4. Scripts and raw data (all under ~/workspace/intel-AMX/exec)

| path | purpose |
|---|---|
| vnnik-trace-20260914/trace.sh | traced runtron runs (arms via ARMS, ARM_<name>_BIN, ARM_<name>_ENV; RES/LOG/MARKER env) |
| vnnik-trace-20260914/analyze.py | Save K / Save V spans, shares, worker busy fractions per trace -> analysis.json/md (run on claude-box; the python perfetto module has no prebuilt on 3bda) |
| vnnik-trace-20260914/lanes.py | one layer's spans on every thread -> <trace>.lanes.json (the lanes figures) |
| vnnik2-20260915/build.sh | fetch a commit into a worktree, configure, syntax-check, build runtron + 4 tests, run them, cabal test (RES/LOG/WT/SUFFIX env) |
| vnnik2-20260915/campaign.sh | smoke + traces + cells; arms and reps via env (NAME, WT, SUFFIX, ARMS, PROMPTS, RT_REPS, TP4_REPS, LONG_REPS, LONG_ARMS, RUN_TRACES) |
| vnnik2-20260915/{summarize.py, compare_tokens.py, gen_report.py, precheck.sh, confirm2.sh} | summary tables and deltas; smoke token comparison; the report page; socket-0 syntax + cabal check; the confirmation launcher |
| results/vnnik-trace-20260914, results/vnnik2-trace-20260915 | traces + analysis (base/vnni; vnni0/a/b/ab) |
| results/vnnik2-20260915, results/vnnik2-confirm-20260915 | rt-results.txt, rt/ logs, smoke/, build.txt, tests.txt, summary.json/md |
| logs/vnnik2-*.log, .status, .done | campaign logs and markers |

## 5. Action plan

The solution is the combination of the two remedies, called the **striped block store** below: the pass's tokens are cut into page-block units, the main thread and the idle main helpers claim the units from one counter, and each unit is written with the block store (16 rows transposed in registers, one full 64-byte line per store). The separate "block store only" and "striping only" configurations were measurement arms and go away.

1. **Remove the measurement switches.** Delete TRON_K_VNNI_BLOCK and TRON_K_VNNI_STRIPE with their read-once functions in k_vnni.hpp, the `|| !block_store` branch in store_k_block, the switch term in k_store_striped, and the arm wording in Note [K VNNI storage] and Note [Striped K store]. About 30 lines; no behaviour change, because both switches already default to on. Two branches stay because they are cases of the data, not options: a token alone in its block keeps the per-token scatter (every decode token), and a save_k with n_workers 1 (the handwritten plugins, the unit tests) or a pass of at most 16 tokens stores on the calling thread without a window.
2. **Re-verify after the cleanup.** Build with build.sh, run the four unit tests and the Haskell suite, and run the greedy smoke against runtron.vnnik3: the tokens must be identical for 128 steps (the store is data movement). One prompt-1024 cell at tp2 and tp4 against base confirms the TTFT numbers of section 2 still hold.
3. **Run the other generated models once.** This is a check, not an optimization. The code generator now emits the helper call for every generated plugin with a KV-writing attention operation, but only qwen3-4b was run. For a model whose heads are not 128 wide (gpt-oss, head 64) the VNNI layout is off and save_k_helper returns at once, so the check is that nothing hangs and the output is unchanged. For a 128-head model with a different kv_mul (llama-3.2-3b, kv_mul 3) the striped store is active; run the smoke and one cell. The handwritten llama plugin is not affected: it calls save_k without a worker count and stores serially, with the block store only.
4. **CI lane.** No CI configuration compiles TRON_K_VNNI=ON, so the VNNI store paths and the new tests run only on delphi-3bda. Add a TRON_K_VNNI=ON configure to the Intel-runner build (a preset or a matrix entry) so that t_k_vnni_layout, t_llama_unit and t_amx_numerics run there; add the cost-data entries the slice check needs (bin/slice bench --update, a whole-machine measurement, so only when Bill is idle).


## 6. Future consideration

Lower priority; none of these blocks the PR.

- **Decode store.** In decode the VNNI store takes 28-35 us per layer (1.0-1.3 ms per step, 8-11% of a step) because the 64 lines of a token's column are cold. It is hidden today: the attention workers run their Ready sections during it and each worker's Pending section waits for its own Ready work, about 110 us later. It would surface with shorter contexts or faster attention. Candidates: stripe the decode tokens over the helpers one token each (a window with one-token units), or prefetch the token's 64 lines early in the layer. Unmeasured.
- **The residual 60-80 us per prefill layer** that remains with the striped block store is below the baseline's 274 us and needs no action. If someone wants to know what it consists of (the block loop itself, the join wait, or the helpers' arrival at the window), a per-unit trace span would separate the three. It is a measurement question, not a known inefficiency.
- **Trace of the review-fixed commit.** The confirmation round skipped its trace phase to finish before the pre-CI hold; its cells reproduced the gains, so the trace is a nice-to-have. `RUN_TRACES=1 NAME=vnnik2-confirm-20260915 WT=/var/tmp/jhan/tron-vnnik3 SUFFIX=vnnik3 bash exec/vnnik2-20260915/campaign.sh` runs only the trace phase (cells and smoke are skipped as done).
- **Mixed chunk lengths.** The measured passes were 8 x 128 tokens, so every page block was a whole unit. Passes where a user's chunk does not start at a multiple of 16 items produce partial units at the chunk edges; 10fc7c724c handles them (one writer per page block) but their cost was not measured separately.

## 7. Traps met, to avoid repeating

- Never edit a campaign script while bash runs it: bash re-reads the file from its byte offset after every forked command. An edit made during the tp2 loop was compensated by deleting the same number of bytes from the already-parsed header; the scripts now take their parameters from the environment so this is not needed.
- `pgrep`/`pkill -f` patterns that appear literally in the same `ssh 'bash -c ...'` command line match the shell itself; use `[c]onfirm2` style patterns, or check in a separate connection.
- The system g++ 11 on 3bda lacks `__bf16`; compile checks need the nix develop toolchain (clang 19).
- A syntax-only compile of t_llama_unit.cpp needs the libfuse3_external target built first (fuse3/fuse.h is generated).
- The Haskell test `Txt.count "outer_state.template save_k"` also matched `save_k_helper`; the tests now check the full call text, and the shared-slot module's K buffer is named `k`, not `kv`.
- Thread roles (helper vs attention worker) change between passes; classify per drawn layer, not per trace.
- The python perfetto TraceProcessor runs on claude-box (prebuilt cached) but not on 3bda; analyze over NFS from claude-box.
- Publish pure-ASCII HTML only (the artifact viewer showed mojibake for UTF-8 pages earlier); gen_report.py asserts it.

## 8. Cleanup round and draft PR (2026-09-15, 06:20-07:35 UTC)

Short version. Items 1 and 4 of the action plan are done and pushed as draft PR #4424 (jhan-amx-vnniK -> jhan-amx-p0, assigned to jhan, label "Skip benchmarks"). The two extra passes jhan asked for (the C++ coding guide on the added code, plain English on the added comments) are committed as two topical commits. Item 2 (re-verify) and item 3 (other generated models) run on delphi-3bda as one chain that starts when the nightly CI releases the machine (about 11:30 UTC).

Words used here: cpp-coding-guide = jhan's two-rule guide (named constexpr values with the value in the name; braces on every control-flow body); plain-english = jhan's comment rules (one claim per sentence, no idioms, define imported terms at first use).

| commit | content |
|---|---|
| ec1be6dde4 | the switches TRON_K_VNNI_BLOCK / TRON_K_VNNI_STRIPE removed (read-once functions, `|| !block_store` branch, the switch term of k_store_striped, the arm wording in both Notes); no behaviour change |
| 58779d3ed6 | cpp-coding-guide on the added code: layout constants in k_vnni.hpp (BLOCK_TOKENS_16, TOKEN_BLOCKS_4, STEP_DIMS_32, STEP_PAIRS_16, DIM_STEPS_4, ROW_ELEMS_32, ...), K_JOIN_TIMEOUT_S_120 and K_JOIN_CLOCK_SPINS_1048576 in model.hpp, MAX_STRIPED_WORKERS_128 in common.hpp, amx_attn.cpp reads the k_vnni constants, the tests name their seeds, masks, poison values, tolerances and scenario positions; braces everywhere; static_assert pins on derived constants |
| f3418e627f | CI lane: -DTRON_K_VNNI=ON in the CMake build job, README.ci.md paragraph |
| 87f82708d7 | plain English in the added comments; six comments corrected against the code (listed in the commit message) |
| dc950be5f2 | corrections from a read-only review of the pushed head (38-agent workflow, 16 confirmed findings): a page block can hold several work units when its items are not consecutive (masked stores on disjoint lanes, no conflict); "a run of one token" instead of "a token alone in its block"; the striping gate counts items; the watchdog fires 120 s after its first clock read; the amx_attn.cpp pins now state what the kernel relies on; common.hpp uses alignas(cache_line_size); README.ci.md says the benchmark artifact now carries the VNNI layout. PR head = dc950be5f2. |

Guards used for "changed code only": a blame-based script proves no line of origin/jhan-amx-p0 was touched by any cleanup commit; a comment-stripping script proves the plain-English commit left the code byte-identical. Both scripts live in the session scratchpad (check_only_added.sh, check_code_unchanged.py); copy them into exec/ if they are needed again.

Interpretation of the coding guide that the PR states: literal values kept on purpose are 0 and 1 as identity or first, array and register index arithmetic, alignas(64) (matches the surrounding base code), type-trait bools, hand-computed expected values inside test assertions, and two loop bodies in t_llama_unit.cpp whose `for` header is a base line.

Checks passed on the final head (delphi-3bda socket 0, exec/vnnik4-20260915/precheck.sh): clang-format-19 on every changed C++ file, syntax-only compile of the five translation units that instantiate the VNNI code, cabal test (Haskell emitter suite).

Running (exec/vnnik4-20260915/chain.sh dc950be5f2, log exec/logs/vnnik4-chain.log; the first launch for 87f82708d7 was stopped before any run): build into /var/tmp/jhan/tron-vnnik4 (runtron.vnnik4) + the four unit tests + cabal test; cost data `bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics` (the slice check fails the CI build without a row for the new test; the diff lands in results/vnnik4-20260915/bench-update.diff and must be committed); greedy smoke vs runtron.vnnik3's tokens; cells base vs new, prompt 1024, tp2 + tp4, 2 repetitions; the whole host suite with TRON_K_VNNI=ON (make build-test-host + make test-host); models.sh (FPGA attention qwen tp2, gpt-oss-120b tp2, llama-3.1-8b tp2, qwen-3-30b-a3b tp2: smoke + one 8-user cell each, base vs new).

Facts learned this round: the local branch jhan-amx-p0 in ~/workspace/tron-amx (47f6f2dceb) is behind origin/jhan-amx-p0 (544ca05c7a); the base for "changed code" is origin. The nightly CI run takes about 8 hours (03:38 to 11:30 UTC). llama-3.2-3b is not an ingested plugin of the build; llama-3.1-8b (same head geometry as qwen3-4b) and qwen-3-30b-a3b (kv_mul 8: VNNI layout on, AMX dense kernel not eligible) stand in for "other 128-dim models".

### 8.1 State at 13:45 UTC (blocked on delphi-3bda)

- The nightly CI run 34925789174 ended (failure) at 13:17 UTC and released the lease, but it left `rinzler@0` and `rinzler@1` running (user positron, four tp4 models, started 10:11 UTC, load about 130). The campaign of the chain waits with "rinzler@N unit active" and everything behind it (host suite, other models) waits too.
- The build step ran before that: runtron.vnnik4 built from dc950be5f2 in 641 s, all four unit tests pass with the same assertion counts as at 10fc7c724c, cabal test passes.
- My attempt to stop the two leftover units (`sudo -n systemctl stop rinzler@0 rinzler@1`) was refused by the session's permission classifier. Someone with a shell on delphi-3bda has to stop them; the campaign then resumes by itself (it polls every 120 s). Earlier scripts did this after a traffic check: `sudo journalctl -u 'rinzler@*' --since '-10 min'` shows no requests, then `sudo systemctl stop rinzler@0 rinzler@1 rinzler@2 rinzler@3` (exec/p2-ci-models.sh lines 24-40).
- The cost-data step (`bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics`) inside verify.sh was killed by SIGTERM about 20 s in (results/vnnik4-20260915/bench-update.txt ends in "Terminated"). Cause: exec/bill-watch.sh (running since 2026-09-07) kills jhan's `bin/slice bench` and runtron whenever a rinzler@N unit is active, and the leftover units were active. The same watcher would kill our runtron cells, so nothing of ours can run until the units are stopped. It has to be rerun on a quiet machine: `cd /var/tmp/jhan/tron-vnnik4 && env -u SYSTEM_CONFIG ~/.nix-profile/bin/nix develop --command bin/slice bench --update t_k_vnni_layout t_llama_unit t_amx_numerics`, then commit the `config/test-benchmarks.json` diff on the branch. The CMake CI job fails at "Check slice cost data" until that row exists. A waiter script for this (exec/vnnik4-20260915/bench-after-chain.sh) exists but its launch was refused by the same classifier.

### 8.2 Results of the chain (2026-09-15, 15:43-16:15 UTC) and the final head

jhan stopped the leftover rinzler units at 15:43 UTC; the chain resumed and finished at 16:05 UTC with no failed run. Final head: bb325d0a6e (dc950be5f2 + the cost-data commit). PR #4424 body updated with everything below.

| check | result |
|---|---|
| greedy smoke (1 user, prompt 1024, 128 tokens) | new binary == runtron.vnnik3 tokens (128 of 128); A/A repeat identical |
| cells prompt 1024, 8 users, 2 repetitions | tp2 TTFT 3.083 vs base 3.141 s (-59 ms), TPS 84.2 vs 79.8 (+5.5%); tp4 TTFT 2.120 vs 2.193 s (-73 ms), TPS 106.8 vs 105.6 (+1.2%) |
| host suite with TRON_K_VNNI=ON (make build-test-host + make test-host) | 302 targets compile; 89 passed, 1 skipped (t_proxy_lib, venv absent), 0 failed; t_k_vnni_layout passed under slice |
| qwen3-4b tp2 with FPGA attention (USE_HW_ATTN unset) | tokens identical to base; cell TTFT 3.155 / 3.162 s, TPS 125.4 / 123.7 |
| gpt-oss-120b tp2 (head 64, layout off) | tokens identical; cell TTFT 4.311 / 4.304 s, TPS 63.7 / 62.6 (one completion line missing in the new run's log; base had one early stop at 110 tokens) |
| llama-3.1-8b tp2 (head 128, kv_mul 4) | first token difference at 46; cell TTFT 4.309 / 4.279 s, TPS 78.6 / 83.1 (+5.7%) |
| qwen-3-30b-a3b tp2 (head 128, kv_mul 8: VNNI layout on, AMX kernel not eligible) | first token difference at 5 (both outputs fluent); cell TTFT 5.204 / 4.835 s (-369 ms), TPS 36.3 / 34.3 (-5.4%, one run) -> open item in the PR: gate the layout on the AMX shape or measure more |
| cost data | bin/slice bench --update on the idle machine: t_k_vnni_layout new row (0.70 s), t_llama_unit 3.4 -> 11.8 s and 329 -> 643 MB, t_amx_numerics within noise; committed as bb325d0a6e |

Raw data: exec/results/vnnik4-20260915/ (build.txt, tests.txt, smoke/, rt/, rt-results.txt, summary.md, host-suite.txt, bench-update.diff), exec/results/vnnik4-models-20260915/ (results.txt, smoke/, rt/). Logs: exec/logs/vnnik4-chain.log, vnnik4-20260915.log, vnnik4-models-20260915.log. Slice's per-test logs of the host run: /var/tmp/jhan/tron-vnnik4/logs-delphi-3bda/latest/.

Open for jhan: (1) the message to Rhys about the leftover rinzler units after the failed nightly run (drafted in the chat); (2) the qwen-3-30b-a3b decode result; (3) the benchmark-artifact question in PR section 6.
