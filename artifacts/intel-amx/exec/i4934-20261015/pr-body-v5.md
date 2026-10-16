## Short version

With the kill switch for AMX (a CPU instruction set), the software attention loop of PR #4901 builds four dot-product helpers on every page visit and tests the layout of every token, and the forward end converts the completed K (key) blocks one by one on the main thread. Issue #4934 records the loss against the parent PR #4898: 2.7 to 3.7 % of decode throughput and about half a second of an 8,192-token prefill. This PR makes the loop set one bit per relevant token, scores the row-major tail rows after the loop, reads a page's layout state once per page from its first cache line, and converts the completed blocks on the worker pool. Measured at this head with the kill switch, prefill time equals PR #4898's in every cell, and decode throughput equals it at prompt 8,192 and at tp4 and stays 1.1 % below it at tp2 prompt 1,024 (the row-major tail rows scored one row at a time). With AMX on, and under FPGA attention, this head is inside the band or better against PR #4901 in every cell.

## Background

This PR targets `jhan-vnnik-4-tail-block`, the branch of PR #4901, so its diff holds only its own commits until PR #4901 merges. PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes and converts it to the VNNI layout at the forward end (Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`, a named comment block in the code). The storage policy of PR #4901 is unchanged (short runs stay row-major, whole blocks are saved VNNI, nothing converts under hardware-scored operations, issue #4500).

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
| tp2, tp4 | Tensor parallel degree: the number of FPGA cards one engine spans. |
| TPS, TTFT, the band | TPS is decode throughput in generated tokens per second per user. TTFT is the time to first token, here the prefill time of the whole prompt. The band is twice the larger of the two binaries' sample standard deviations, never smaller than 0.40 TPS or 0.15 s; a difference beyond it counts as a change. |

## How to review this PR

**Does the split of the live mask score every relevant token once, through its block's reader?**
- Read the loop in `h/tron/models/self_attention.hpp`: on a VNNI slot (a K store under the layout option) the token body is `live |= offset_bit(i)` and nothing else. After the loop, `k_vnni::block_token_mask` turns the block mask into 64 token bits. The live tokens of VNNI blocks go to the reader in one call, the others to the dotters one row at a time.
- The two parts partition the live mask, so a token is scored exactly once. The dotter arithmetic is unchanged, and the reader scores each lane independently of the other lanes.
- Verification: the new `t_amx_dispatch_dtype` case "the software loop scores row-major rows with the dotter and VNNI blocks with the reader" checks `m_star` (the running score maximum) bit-exact against the two readers, with the dominant row (the largest score) in a row-major block and in a VNNI block, for bf16, float and fp16 queries.

**Can the block mask read once per page be stale for a query of the same call?**
- Read `apply_page_range` in `h/tron/models/self_attention.hpp`: the read sits after the dismissal of empty and workless pages and before the query loop. The value reaches `apply_page_tok` as an argument and also serves the dense AMX gate (the check that sends a page to the AMX kernel only when every block is VNNI).
- Read `save_k` in `h/tron/models/model.hpp`: a whole-block save sets the bits before the pending sections start (attention work that waits, through a latch, for KV written in this pass, Note [Minibatch Dependency Tracking] in `h/tron/models/common.hpp`), and `convert_pending_k_blocks` runs after every worker is joined. A ready page has no writer in the pass, and a pending page is read only after every writer has counted the latch down. So no bit changes while a call scores.
- Read the `page` members in `h/tron/models/kv_cache.hpp`: the block mask sits before `kv_saves_` (the per-token save counters), in the first cache line with `lo` and `offset_bound`, which every visit reads. Its writers are unchanged.
- Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows check that the gate refuses a page with a row-major block. The timing argument has no test (Open items).

**Can two pool tasks convert one block, or a task race a reader?**
- Read `note_k_row_saved` in `h/tron/models/kv_cache.hpp`: it reports a block's completion only for the call that sets the last of the 16 row bits, so `save_k` queues every block once.
- Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: a queue of `k_convert_parallel_min` (8 blocks) or more goes through `thread_pool::parallel_for`, and the call waits for the latch before the logit (per-word score) delivery is enqueued. That delivery's callbacks take the tree lock (the lock over the KV cache's books) on pool workers and may move or free books.
- Each task publishes its blocks with the release `fetch_or` of `k_block_to_vnni_at`. Every reader loads the bits with acquire before it touches the plane (one page's K storage).
- Verification: the `t_k_vnni_layout` page-state case checks that a re-saved row reports no second completion and the block converts once. The `t_llama_unit` section "the forward end converts a queue of many blocks on the pool" completes 12 blocks in one pass (above the 8-block threshold) and checks every row, every block bit and the empty queue.

## Verification

Head `b87d20dd81` is measured on 2026-10-16 against the base `6b081187e1` (PR #4901's head) on a Granite Rapids server (Intel Xeon 6962P with AMX, 8 FPGA cards), built in `nix develop` (the project's build shell) with clang 19.1.7, the `native` preset and `RelWithDebInfo`.

### Builds and tests

Unit tests with a fake device, the layout option and AMX dispatch on, `--skip-benchmarks` (no benchmark sections), all pass: `t_k_vnni_layout` 1,041,278 assertions in 10 cases, `t_amx_dispatch_dtype` 2,778 in 2, `t_amx_numerics` 6,669 in 5, `t_llama_unit` 277,979 in 67, `t_heterogeneous_scheduler` 2,859 in 4, `t_phase1_integration` 6,250 in 67.
- Under the kill switch the same build passes `t_llama_unit` and `t_heterogeneous_scheduler`. `t_amx_numerics` skips its three AMX checks.
- The option-off build (`TRON_K_VNNI=OFF`) passes the first five tests (1,039,198 / 2,778 / 6,669 / 277,687 / 2,859 assertions). The dispatch-off build (`TRON_AMX_DISPATCH=OFF`) passes the six (1,041,278 / 109 / 1 / 277,979 / 2,859 / 6,250 assertions, two tests compile their AMX cases out).
- clang-format (the code formatter) leaves every touched file unchanged. A syntax-only compile in 22 configurations (dispatch and option on or off, six files) reports 0 errors and 0 warnings.
- Three deliberate breaks (every live token through the reader, a completion reported twice, half the queue converted), each rebuilt from a copy of the head, fail the test named for them in [How to review this PR].

### Token identity

qwen3-4b, 1 user, temperature 0 (the top-scoring token every step), `--pay-for-determinism` (the runtron flag for repeatable runs), 256 generated tokens. `fix2` repeats `fix` and must match it. `fix` against `new` is expected identical (the same dotter and reader). `fixoff` against `fix` is informational (issue #4444, the kill-switch token divergence).

| Cell | fix vs fix2 | fix vs new | fixoff vs fix |
|---|---|---|---|
| CPU attention, prompt 1,024 | identical, 256 of 256 | identical, 256 of 256 | first difference at generated token 247 |
| CPU attention, prompt 8,192 | identical, 256 of 256 | identical, 256 of 256 | identical, 256 of 256 |
| FPGA attention, prompt 1,024 | identical, 256 of 256 | identical, 256 of 256 | not run |

### Performance

The cells: qwen3-4b, 8 users, 256 generated tokens, 3 repetitions with the binary order rotated per repetition. CPU attention at tp2 with prompts of 1,024 and 8,192 tokens and at tp4 with 1,024 tokens, six binaries. FPGA attention at tp2 and tp4 with 1,024 tokens, binaries `head`, `new`, `fix`. The decision rule, every line must hold:
- `fixoff` against `headoff` inside the band in decode TPS and TTFT in every CPU cell (the loss of issue #4934 is gone).
- `fix` against `new` inside the band or better in decode TPS (no cost with AMX on).
- `fix` against `new` inside the band under FPGA attention (the policy of issue #4500 is untouched).

CPU attention. The difference is the mean over the repetitions, t the paired t statistic (the mean of the per-repetition differences over its standard error). The means per binary are in the records [exec/results/i4934-E2-cpu/summary.md].

| Cell | Pair | TPS difference (band) | Verdict | t | TTFT difference ms (band) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| tp2, prompt 1,024 | `fixoff` vs `headoff` | -0.84 (-1.1 %, band 0.40) | beyond | -8.0 | +5 (band 150) | inside |
| tp2, prompt 1,024 | `fix` vs `new` | +0.96 (+1.1 %, band 0.42) | better | +7.6 | -14 (band 150) | inside |
| tp2, prompt 8,192 | `fixoff` vs `headoff` | -0.12 (-0.8 %, band 0.40) | inside | -2.7 | +228 (band 584) | inside |
| tp2, prompt 8,192 | `fix` vs `new` | +0.06 (+0.3 %, band 0.40) | inside | +3.2 | -72 (band 188) | inside |
| tp4, prompt 1,024 | `fixoff` vs `headoff` | +0.46 (+0.4 %, band 2.28) | inside | +0.7 | +8 (band 150) | inside |
| tp4, prompt 1,024 | `fix` vs `new` | +1.53 (+1.3 %, band 1.48) | better | +2.1 | -14 (band 150) | inside |

FPGA attention, the same columns:

| Cell | Pair | TPS difference (band) | Verdict | t | TTFT difference ms (band) | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| tp2, prompt 1,024 | `fix` vs `new` | -0.41 (-0.3 %, band 1.05) | inside | -1.0 | -17 (band 150) | inside |
| tp4, prompt 1,024 | `fix` vs `new` | +0.04 (+0.0 %, band 1.77) | inside | +0.1 | +6 (band 150) | inside |

What the tables say.
- Line 1 holds in TTFT in every cell and in TPS at tp2 prompt 8,192 and at tp4. It does not hold at tp2 prompt 1,024: -0.84 TPS (-1.1 %, t -8.0), beyond the 0.40 floor. PR #4901 loses 3.2 % there and 3.1 % at prompt 8,192, so this head recovers two thirds of the loss at prompt 1,024 and all of it at prompt 8,192.
- Line 2 holds: better than PR #4901 at both prompt-1,024 cells, inside at prompt 8,192.
- Line 3 holds: inside the band at tp2 and tp4. An earlier campaign with a fixed binary order showed -1.2 % at tp4. The rotated order removes it.
- The remaining 1.1 %. Ablation builds of this branch before its last commit (one mechanism removed each, timing only) split the kill-switch loss at tp2 prompt 1,024 into the per-page block-mask read (0.6 %) and the row-major tail rows scored one at a time (1.2 %). The last commit moved the mask into the page's first cache line, and the loss moved from -1.7 % to -1.1 % at prompt 1,024 and from -1.5 % to -0.8 % at prompt 8,192. So the mask-read part is gone and the tail-row part remains. Traces of this head with the kill switch show the decode step 1.7 % (prompt 1,024) and 2.8 % (prompt 8,192) shorter than PR #4901's and the forward-end conversion at 62 us on the pool against 1,038 us serial.

## Open items

**The row-major tail rows at short prompts.** Each user's current block holds up to 15 row-major rows, scored one row at a time with a scalar online softmax per row: a fixed cost per decode step, 1.1 % at tp2 prompt 1,024 and inside the band at prompt 8,192. A 16-row tail-block kernel (one dot product over the block feeding the reader's 16-lane softmax update) would recover it. It is not in this PR. Reviewers decide whether it belongs here or in a tracked follow-up.

**No test of the forward-end ordering.** The join before the logit delivery and the stability of the per-page read rest on the code argument in [How to review this PR]. Reviewers decide whether a two-minibatch fixture (test setup) is needed.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
