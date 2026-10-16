## Short version

With the kill switch for AMX (a CPU instruction set), the software attention loop of PR #4901 builds four dot-product helpers on every page visit and tests the layout of every token, and the forward end converts the completed K (key) blocks one by one on the main thread while every worker waits. This PR makes the loop set one bit per relevant token, as the parent PR #4898 does, scores the rows of the row-major tail blocks after the loop, reads a page's layout state once per page from the page's first cache line, and converts the completed blocks on the worker pool. Issue #4934 records the loss against PR #4898 with the kill switch: 2.7 to 3.7 % of decode (token generation) throughput and about half a second of an 8,192-token prefill (the prompt pass). Measured at this head, the kill-switch prefill time equals PR #4898's in every cell. The kill-switch decode throughput equals PR #4898's at prompt 8,192 and at tp4, and stays 1.1 % below it at tp2 with a 1,024-token prompt, the cost of scoring the row-major tail rows one row at a time. With AMX on, and under FPGA attention, this head is inside the band or better against PR #4901 in every cell.

## Background

This PR targets `jhan-vnnik-4-tail-block`, the branch of PR #4901, so its diff holds only its own commits until PR #4901 merges. PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes and converts the block to the VNNI layout at the forward end (Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp` and Note [K VNNI storage] in `h/tron/models/kv_cache.hpp`). A Note is a named comment block in the code.

The loop under PR #4901 tells, per token, whether the token's block is row-major or VNNI, and builds the row-major dotters before it knows whether any token needs them. With the kill switch every (query, page) visit runs that loop: an 8-user prefill of 8,192 tokens runs it about 1.2 billion times and its token body about 77 billion times (both computed from the prompt length, the page size and the model shape). The forward-end conversion of a user's completed block is about 300 in-place transposes (36 layers times 8 KV heads) on the main thread with the pool idle.

The fix keeps the storage policy of PR #4901: short runs (saves of fewer than 16 tokens) stay row-major, whole blocks are saved VNNI, the conversion happens at the forward end, and no conversion happens under hardware-scored operations (attention scored on the FPGA, issue #4500).

## Words used here

| Term | Meaning |
|---|---|
| AMX, AVX-512 | CPU instruction sets. AMX works on matrix tiles, AVX-512 on 512-bit vectors. |
| the kill switch | `TRON_AMX_DISABLE=1`: the AMX kernels off at run time inside the same binary. The same software path serves a host without AMX. |
| K, V, KV head, page | K and V are the key and value tensors of attention, stored per KV head. A page is a KV page (64-token block) of the cache. |
| VNNI layout, tail block | VNNI (Vector Neural Network Instructions) names the pair-interleaved K layout that the AMX kernels read in place. Row-major is the plain layout, one token per row. A tail block is an incomplete 16-token block, kept row-major until it fills. |
| the forward end | The end of one forward pass (one pass of the model over its batch). |
| the pool, a worker, the main thread | The engine's thread pool and one of its threads. The main thread runs the forward pass and hands parallel work to the pool. |
| the loop | The software scoring loop of `apply_page_tok` in `h/tron/models/self_attention.hpp`: one query against one page of one KV head. |
| the reader, the dotter | The reader is `k_vnni::qk_group`, the AVX-512 routine that scores a query group (the query heads that share one KV head) against the VNNI blocks of a page through a 64-bit live mask (one bit per token of the page that the call must score). The dotter is the per-token dot product over one row-major K row (`h/tron/kernels/dotter.hpp`). |
| block mask | `page::k_vnni_blocks`, one byte per page and storage slot (one K store of the page), bit c set when 16-token block c holds the VNNI layout. |
| the conversion | `convert_pending_k_blocks` in `h/tron/models/model.hpp`: at the forward end, every block a short run completed in the pass is transposed in place to the VNNI layout, for every KV head. |
| FPGA attention, CPU attention, the fake device | FPGA (field-programmable gate array): the accelerator card. FPGA attention scores attention on the card. CPU attention scores it on the CPU, with the AMX kernels or the loop. The fake device is a simulated FPGA for unit tests. |
| fix, new, head and fixoff, newoff, headoff | runtron (the command-line tool of tron, the inference program under test) builds of this head, of PR #4901's implementation commit (`ea94e95a4e`) and of PR #4898 (`dfafd13dce`), with AMX dispatch (`TRON_AMX_DISPATCH`, the build option that compiles the AMX kernels in) and the layout option (`TRON_K_VNNI`, the build option that stores K in the VNNI layout) on. The `off` builds run the same binaries with the kill switch. The commit `ea94e95a4e` is the binary issue #4934 measured; PR #4901's later commits add tests, cost rows, comment reviews and main merges only. |
| TPS, TTFT, the band | TPS is decode throughput in generated tokens per second per user. TTFT is the time to first token, here the prefill time of the whole prompt. The band is twice the larger of the two binaries' sample standard deviations, never smaller than 0.40 TPS or 0.15 s; a difference beyond it counts as a change. |

## How to review this PR

**Does the split of the live mask score every relevant token once, through the reader of its block's layout?**
- Read the loop in `h/tron/models/self_attention.hpp`: on a VNNI slot (a K store under the layout option) the token body is `live |= offset_bit(i)` and nothing else. After the loop, `k_vnni::block_token_mask` turns the block mask into 64 token bits. The live tokens of VNNI blocks go to the reader in one call, the others to the dotters one row at a time.
- Read `block_token_bits` and `block_token_mask` in `h/tron/tensor/k_vnni.hpp`: bit c of the block mask becomes page offsets 16 c to 16 c + 15.
- The two parts partition the live mask, so a token is scored exactly once. The dotter arithmetic for a row-major row is unchanged. The reader scores each lane (one token position of its vector) independently of whether the other lanes are live.
- Verification: the new `t_amx_dispatch_dtype` case "the software loop scores row-major rows with the dotter and VNNI blocks with the reader" checks `m_star` (the running score maximum) bit-exact against the two readers, with the dominant row (the row with the largest score) in a row-major block and in a VNNI block, for queries in bf16, float and fp16 (three number formats). The mixed pages of the `t_llama_unit` case "apply and join page ranges" cover the split as well.

**Can the block mask read once per page be stale for a query of the same call?**
- Read `apply_page_range` in `h/tron/models/self_attention.hpp`: the read sits after the dismissal of empty and workless pages (pages with no work for the call) and before the query loop. The value reaches `apply_page_tok` as an argument, and the same argument serves the dense AMX gate (the check that sends a page to the AMX kernel only when every block of the page is VNNI).
- Read `save_k` in `h/tron/models/model.hpp`: a whole-block save sets the bits before the pending sections start. A pending section is attention work that waits, through a latch (a countdown that the writers tick), for KV written in this pass by a minibatch (a group of requests the model runs together) that may be a different one (Note [Minibatch Dependency Tracking] in `h/tron/models/common.hpp`). `convert_pending_k_blocks` runs after the plugin (the model-specific code that runs the forward pass) has joined every worker.
- A page read by a ready section (attention work whose KV is written before the pass) has no writer in the pass. A pending page is read only after every writer has counted the latch down. So no bit changes while a call scores.
- Read the `page` members in `h/tron/models/kv_cache.hpp`: the block mask is declared before `kv_saves_` (the per-token save counters), in the page's first cache line with `lo` and `offset_bound`, which every visit reads. The mask's writers are unchanged: the whole-block save and the forward-end conversion. The page copy constructor copies the members by name, so nothing depends on the member order.
- Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows check that the gate refuses a page with any row-major block. The timing argument itself has no test. Open: reviewers decide whether the argument in the code comment is enough.

**Can two pool tasks convert one block, or a task race a reader?**
- Read `note_k_row_saved` in `h/tron/models/kv_cache.hpp`: it reports a block's completion for the call that sets the last of the 16 row bits, and never for a row saved again. So `save_k` queues every block once.
- Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: a queue of `k_convert_parallel_min` (8 blocks) or more goes through `thread_pool::parallel_for`, one strided share per worker (every n-th block, n the worker count). The call waits for the latch before the logit (per-word score) delivery is enqueued. The listener thunks (callbacks) of that delivery take the tree lock (the lock over the KV cache's books) on pool workers and may move or free books (the owners of the cache's pages). So the join must come first.
- Each task publishes its blocks with the release `fetch_or` of `k_block_to_vnni_at`. Every reader loads the block bits with acquire before it touches a plane (one page's K storage). Release and acquire are the C++ memory orders that order the block's bytes before its bit.
- Verification: the `t_k_vnni_layout` page-state case checks that a re-saved row of a complete block does not report the completion again, and that the block converts once. The `t_llama_unit` save_k section "the forward end converts a queue of many blocks on the pool" completes 12 blocks in one pass (above the 8-block pool threshold) and checks every row, every block bit and the empty queue.

## Verification

Head `b87d20dd81` is measured on 2026-10-16 against the base `6b081187e1` (PR #4901's head). The machine is a Granite Rapids server (Intel Xeon 6962P, the CPU generation with AMX, and 8 FPGA cards). The build is `nix develop` (the project's build shell), clang 19.1.7, the `native` preset (the CMake preset for the build host's CPU) and `RelWithDebInfo` (the optimized build type with debug symbols). The binaries are `fix`, `new`, `head` and their `off` builds [Words used here].

### Builds and tests

Unit tests with a fake device, the layout option and AMX dispatch on, and `--skip-benchmarks` (the test flag that leaves out the benchmark sections):

| Test | Result |
|---|---|
| `t_k_vnni_layout` | 1,041,278 assertions in 10 cases, pass |
| `t_amx_dispatch_dtype` | 2,778 assertions in 2 cases, pass |
| `t_amx_numerics` | 6,669 assertions in 5 cases, pass |
| `t_llama_unit` | 277,979 assertions in 67 cases, pass |
| `t_heterogeneous_scheduler` | 2,859 assertions in 4 cases, pass |
| `t_phase1_integration` | 6,250 assertions in 67 cases, pass |

- The same build passes `t_llama_unit` and `t_heterogeneous_scheduler` under the kill switch. `t_amx_numerics` then reports AMX unavailable in its three AMX checks and skips them.
- The option-off build (`TRON_K_VNNI=OFF`, row-major K) passes `t_k_vnni_layout`, `t_amx_dispatch_dtype`, `t_amx_numerics`, `t_llama_unit` and `t_heterogeneous_scheduler` (1,039,198 / 2,778 / 6,669 / 277,687 / 2,859 assertions). The dispatch-off build (`TRON_AMX_DISPATCH=OFF`, the option on) passes the six tests («R2» 1,041,278 / 109 / 1 / 277,962 / 2,855 / 6,220 assertions; `t_amx_dispatch_dtype` and `t_amx_numerics` compile their AMX cases out).
- clang-format (the code formatter) leaves every touched file unchanged. A syntax-only compile in 22 configurations (AMX dispatch on or off, the option on or off, five test files and the AMX kernel file) reports 0 errors and 0 warnings.
- Three deliberate breaks, each applied to a copy of the head and rebuilt, fail the test that guards them: every live token sent through the reader fails the `t_amx_dispatch_dtype` case "the software loop scores row-major rows with the dotter and VNNI blocks with the reader", a completion reported again for a re-saved row fails the `t_k_vnni_layout` page-state case, and a conversion of half the queue fails the `t_llama_unit` section "the forward end converts a queue of many blocks on the pool".

### Token identity

qwen3-4b, 1 user, temperature 0 (the top-scoring token every step), `--pay-for-determinism` (the runtron flag that makes a run repeatable), 256 generated tokens. `fix2` is a repeat of `fix` and must match `fix`. `fix` against `new` is expected identical, since both score a row-major row with the same dotter and a VNNI block with the same reader. `fixoff` against `fix` is informational: it follows issue #4444 (the kill-switch rollback contract and the token divergence it records).

| Cell | fix vs fix2 | fix vs new | fixoff vs fix |
|---|---|---|---|
| CPU attention, prompt 1,024 | «R2» identical, 256 of 256 | «R2» identical, 256 of 256 | «R2» first difference at generated token 247 |
| CPU attention, prompt 8,192 | «R2» identical, 256 of 256 | «R2» identical, 256 of 256 | «R2» identical, 256 of 256 |
| FPGA attention, prompt 1,024 | «R2» identical, 256 of 256 | «R2» identical, 256 of 256 | not run |

### Performance

The cells: qwen3-4b, 8 users, 256 generated tokens, 3 repetitions with the binary order rotated per repetition. CPU attention at tp2 (tensor parallel degree 2, the number of FPGA cards one engine spans) with prompts of 1,024 and 8,192 tokens, and at tp4 with 1,024 tokens, binaries `head`, `headoff`, `new`, `newoff`, `fix`, `fixoff`. FPGA attention at tp2 and tp4 with 1,024 tokens, binaries `head`, `new`, `fix`. The decision rule, every line of which must hold:
- `fixoff` against `headoff` is inside the band in decode TPS and TTFT in every CPU cell (the kill-switch loss of issue #4934 is gone).
- `fix` against `new` is inside the band or better in decode TPS (no cost with AMX on).
- `fix` against `new` is inside the band under FPGA attention (the policy of issue #4500 is untouched).

CPU attention. Means over the repetitions with the sample standard deviation in parentheses; t is the paired t statistic over the repetitions (the mean of the per-repetition differences over its standard error):

| Cell | Pair | TPS per user (sd) | TPS difference (band) | Verdict | t | TTFT s (sd) | TTFT difference ms (band) | Verdict |
|---|---|---|---|---|---|---|---|---|
| tp2, 8 users, prompt 1,024 | `fixoff` vs `headoff` | 75.00 (0.09) vs 75.84 (0.15) | -0.84 (-1.1 %, band 0.40) | beyond | -8.0 | 3.861 (0.002) vs 3.856 (0.005) | +5 (band 150) | inside |
| tp2, 8 users, prompt 1,024 | `fix` vs `new` | 86.12 (0.21) vs 85.16 (0.12) | +0.96 (+1.1 %, band 0.42) | better | +7.6 | 3.077 (0.006) vs 3.092 (0.005) | -14 (band 150) | inside |
| tp2, 8 users, prompt 8,192 | `fixoff` vs `headoff` | 15.30 (0.08) vs 15.42 (0.01) | -0.12 (-0.8 %, band 0.40) | inside | -2.7 | 117.609 (0.292) vs 117.381 (0.139) | +228 (band 584) | inside |
| tp2, 8 users, prompt 8,192 | `fix` vs `new` | 19.02 (0.02) vs 18.95 (0.04) | +0.06 (+0.3 %, band 0.40) | inside | +3.2 | 51.547 (0.057) vs 51.619 (0.094) | -72 (band 188) | inside |
| tp4, 8 users, prompt 1,024 | `fixoff` vs `headoff` | 111.64 (0.08) vs 111.18 (1.14) | +0.46 (+0.4 %, band 2.28) | inside | +0.7 | 2.404 (0.003) vs 2.396 (0.013) | +8 (band 150) | inside |
| tp4, 8 users, prompt 1,024 | `fix` vs `new` | 122.36 (0.60) vs 120.83 (0.74) | +1.53 (+1.3 %, band 1.48) | better | +2.1 | 2.119 (0.005) vs 2.133 (0.002) | -14 (band 150) | inside |

FPGA attention, the same columns:

| Cell | Pair | TPS per user (sd) | TPS difference (band) | Verdict | t | TTFT s (sd) | TTFT difference ms (band) | Verdict |
|---|---|---|---|---|---|---|---|---|
| tp2, 8 users, prompt 1,024 | `fix` vs `new` | 133.14 (0.53) vs 133.55 (0.25) | -0.41 (-0.3 %, band 1.05) | inside | -1.0 | 3.106 (0.004) vs 3.123 (0.011) | -17 (band 150) | inside |
| tp4, 8 users, prompt 1,024 | `fix` vs `new` | 165.21 (0.89) vs 165.17 (0.32) | +0.04 (+0.0 %, band 1.77) | inside | +0.1 | 2.170 (0.011) vs 2.164 (0.010) | +6 (band 150) | inside |

What the tables say.
- Line 1 holds in TTFT in every cell, and in TPS at tp2 prompt 8,192 (-0.12 TPS, inside the 0.40 floor) and at tp4 (+0.46 TPS). It does not hold at tp2 prompt 1,024: -0.84 TPS (-1.1 %, t -8.0), beyond the 0.40 floor. PR #4901 loses 2.40 TPS (-3.2 %) in that cell, so this head recovers two thirds of the loss there and all of it at prompt 8,192 (PR #4901: -3.1 %).
- Line 2 holds: better than PR #4901 at both prompt-1,024 cells, inside the band at prompt 8,192.
- Line 3 holds: inside the band at tp2 and tp4. An earlier campaign with a fixed binary order showed -1.2 % at tp4; the rotated order removes it, so that was an order effect.
- Where the remaining 1.1 % comes from. Ablation builds of this branch before its last commit (one mechanism removed each, timing only) split its kill-switch loss at tp2 prompt 1,024 into the per-page block-mask read (0.6 %) and the row-major tail rows scored one at a time by the dotters (1.2 %); at prompt 8,192 into the mask read (1.0 %) and 0.6 % elsewhere. The last commit moved the block mask into the page's first cache line, and the campaign moved from -1.7 % to -1.1 % at prompt 1,024 and from -1.5 % to -0.8 % at prompt 8,192: the mask-read part is gone, the dotter part remains. Perfetto traces (tron's trace format) of this head with the kill switch show the decode step 1.7 % (prompt 1,024) and 2.8 % (prompt 8,192) shorter than PR #4901's, the forward-end conversion at 62 us on the pool against 1,038 us serial, and the whole step difference inside the workers' attention spans.

## Open items

**The row-major tail rows at short prompts.** Each user's current block holds up to 15 row-major rows, and the loop scores them one row at a time with a scalar online softmax per row. That is a fixed cost per decode step, 1.1 % of the step at tp2 prompt 1,024 and inside the band at prompt 8,192. A 16-row tail-block kernel (one dot product over the block's rows feeding the reader's 16-lane softmax update) would recover it. It is not in this PR. Reviewers decide whether it belongs here or in a tracked follow-up.

**No test of the forward-end ordering.** The join of the conversion before the logit delivery, and the stability of the per-page read, rest on the code argument in [How to review this PR]. Reviewers decide whether a fixture (a test setup) with two minibatches is needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
