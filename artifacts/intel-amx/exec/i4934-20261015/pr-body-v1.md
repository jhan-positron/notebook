## Short version

With the AMX kill switch, the software attention loop of PR #4901 builds four dot-product helpers on every page visit and tests the layout of every token, and the forward end converts the completed K blocks one by one on the main thread while every worker waits. This PR makes the loop set one bit per relevant token, as the parent PR #4898 did, scores the rows of the row-major tail blocks after the loop, reads a page's layout state once per page instead of once per visit, and converts the completed blocks on the worker pool. Issue #4934 records the loss this removes: 2.7 to 3.7 % of decode throughput and about half a second of an 8,192-token prefill against PR #4898 with the kill switch.

## Background

PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes and converts it at the forward end (Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp`, Note [K VNNI storage] in `h/tron/models/kv_cache.hpp`). Its software loop had to tell, per token, whether the token's block is row-major or VNNI, and it built the row-major dotters before knowing whether any token needed them. With the kill switch every (query, page) visit runs that loop: an 8-user prefill of 8,192 tokens runs it about 1.2 billion times and its token body 77 billion times. The forward-end conversion of a user's completed block is about 300 in-place transposes (36 layers, 8 KV heads) on the main thread with the pool idle.

The fix keeps the storage policy of PR #4901: short runs row-major, whole blocks VNNI, conversion at the forward end, no conversion under hardware-scored operations (issue #4500).

## Words used here

| Term | Meaning |
|---|---|
| the kill switch | `TRON_AMX_DISABLE=1`: the AMX kernels off at run time inside the same binary. The same software path serves a host without AMX. |
| the loop | The software scoring loop of `apply_page_tok` in `h/tron/models/self_attention.hpp`: one query against one page of one KV head. |
| the reader, the dotter | The reader is `k_vnni::qk_group`, the AVX-512 routine that scores a query group against the VNNI blocks of a page through a 64-bit live mask. The dotter is the per-token dot product over one row-major K row (`h/tron/kernels/dotter.hpp`). |
| block mask | `page::k_vnni_blocks`, one byte per page and storage slot, bit c set when 16-token block c holds the VNNI layout. |
| the conversion | `convert_pending_k_blocks` in `h/tron/models/model.hpp`: at the forward end, every block a short run completed in the pass is transposed in place to the VNNI layout, for every KV head. |
| fix, new, head; fixoff, newoff, headoff | runtron builds of this head, of PR #4901 (`ea94e95a4e`) and of PR #4898 (`dfafd13dce`), with AMX dispatch and the layout option on; the `off` arms run the same binaries with the kill switch. |

## How to review this PR

**Does the split of the live mask score every relevant token once, through the reader of its block's layout?**
- Read the loop in `h/tron/models/self_attention.hpp`: on a VNNI slot the token body is `live |= offset_bit(i)` and nothing else. After the loop, `k_vnni::block_token_mask` turns the block mask into 64 token bits; the live tokens of VNNI blocks go to the reader in one call, the others to the dotters one row at a time.
- Read `block_token_bits` and `block_token_mask` in `h/tron/tensor/k_vnni.hpp`: bit c of the block mask becomes page offsets 16 c to 16 c + 15.
- The two parts partition the live mask, so a token is scored exactly once. The dotter arithmetic for a row-major row is unchanged, and the reader scores each lane independently of the other lanes' liveness.
- Verification: the new `t_amx_dispatch_dtype` case "the software loop scores row-major rows with the dotter and VNNI blocks with the reader" (bit-exact `m_star` against the two readers, dominant row in a row-major block and in a VNNI block, bf16, float and fp16 queries), and the mixed pages of the `t_llama_unit` case "apply and join page ranges".

**Can the block mask read once per page be stale for a query of the same call?**
- Read `apply_page_range` in `h/tron/models/self_attention.hpp`: the read sits after the dismissal of empty and workless pages, before the query loop, and the value reaches `apply_page_tok` as an argument that also serves the dense AMX gate.
- Read `save_k` in `h/tron/models/model.hpp`: a whole-block save sets the bits before the pending sections start (the latch of Note [Minibatch Dependency Tracking] in `h/tron/models/common.hpp`); `convert_pending_k_blocks` runs after the plugin joined every worker.
- A page read by a ready section has no writer in the pass, and a pending page is read only after every writer counted the latch down. So no bit changes while a call scores.
- Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows (the gate refuses a page with any row-major block). The timing argument itself has no test. Open: reviewers decide whether the argument in the code comment is enough.

**Can two pool tasks convert one block, or a task race a reader?**
- Read `note_k_row_saved` in `h/tron/models/kv_cache.hpp`: it reports a block's completion for the call that sets the last of the 16 row bits and never for a row saved again, so `save_k` queues every block once.
- Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: a queue of `k_convert_parallel_min` blocks or more goes through `thread_pool::parallel_for`, one strided share per worker, and the call waits for the latch before the logit delivery is enqueued. The listener thunks of that delivery take the tree lock on pool workers and may move or free books, so the join must come first.
- Each task publishes its blocks with the release `fetch_or` of `k_block_to_vnni_at`; every reader loads the block bits with acquire before it touches a plane.
- Verification: the `t_k_vnni_layout` page-state case (a re-saved row of a complete block does not report the completion again, and the block converts once), and the `t_llama_unit` save_k section "the forward end converts a queue of many blocks on the pool" (12 blocks completed in one pass, every row, every block bit and the empty queue checked).

## Verification

Head `c30a86f252`, measured on 2026-10-15 against the base `175b1837b9` (PR #4901's head) on a Granite Rapids machine (Intel Xeon 6962P, 8 FPGA cards), `nix develop` (the project's build shell), clang 19.1.7, the `native` preset, `RelWithDebInfo`. Binaries: `fix`, `new`, `head` and their `off` arms [Words used here].

### Builds and tests

Unit tests with a fake device (a simulated FPGA), the layout option and AMX dispatch on, `--skip-benchmarks`:

| Test | Result |
|---|---|
| `t_k_vnni_layout` | 1,041,278 assertions in 10 cases, pass |
| `t_amx_dispatch_dtype` | 2,778 assertions in 2 cases, pass |
| `t_amx_numerics` | 6,669 assertions in 5 cases, pass |
| `t_llama_unit` | 277,962 assertions in 66 cases, pass |
| `t_heterogeneous_scheduler` | 2,855 assertions in 4 cases, pass |
| `t_phase1_integration` | 6,220 assertions in 64 cases, pass |

The same build passes `t_llama_unit` and `t_heterogeneous_scheduler` under the kill switch; `t_amx_numerics` then reports AMX unavailable in its three AMX checks and skips them. The option-off and the dispatch-off builds are pending [Open items]. Clean at the head: clang-format on every touched file, and a syntax-only compile in 22 configurations (AMX dispatch on or off, the option on or off, five test files and the AMX kernel file) with 0 errors; the dispatch-off `t_amx_dispatch_dtype` warns about one unused test constant where the base warns about two.

### Token identity

Pending [Open items]. The rule: `fix2` (a repeat of `fix`) must match `fix`; `fix` against `new` is expected identical in the CPU cells, since both score a row-major row with the same dotter and a VNNI block with the same reader, and `fixoff` against `fix` follows issue #4444.

### Performance

Pending [Open items]. Cells: qwen3-4b, 8 users, 256 generated tokens, 3 repetitions in alternating order; CPU attention at tp2 with prompts of 1,024 and 8,192 tokens and at tp4 with 1,024 tokens, arms `head`, `headoff`, `new`, `newoff`, `fix`, `fixoff`; FPGA attention at tp2 and tp4 with 1,024 tokens, arms `head`, `new`, `fix`. The band is twice the larger of the two arms' sample standard deviations, never smaller than 0.4 TPS or 0.15 s; a difference beyond it counts as a change. The decision rule: `fixoff` against `headoff` inside the band in decode TPS and TTFT in every CPU cell (the kill-switch loss of issue #4934 is gone), `fix` against `new` inside the band or better in decode TPS (no cost with AMX on), and `fix` against `new` inside the band under FPGA attention (the policy of issue #4500 is untouched).

## Open items

**Pending measurements.** Each is queued at this head on the same machine:
- Performance in the cells of [Verification]: settles the decision rule there.
- Token identity: `fix` against `fix2`, `new` and `fixoff` in the CPU cells at prompts 1,024 and 8,192 tokens and the FPGA cell at 1,024 tokens, 1 user, temperature 0, `--pay-for-determinism`.
- The option-off build (row-major K, 5 tests) and the dispatch-off build (6 tests).
- The derivation of `k_convert_parallel_min` (8): the `convert_k_blocks` trace span of a kill-switch decode run gives the serial cost per block, against which the pool's hand-off cost is weighed. The value is an estimate until then.
- Mutation checks: scoring the row-major rows through the reader must fail the new `t_amx_dispatch_dtype` case; reporting a completion on a re-saved row must fail the page-state case; converting half the queue must fail the 12-block section.

**No test of the forward-end ordering.** The join of the conversion before the logit delivery and the per-page read's stability rest on the code argument in section 4. Reviewers decide whether a fixture with two minibatches is needed.

## The stack

PR #4901 is the last of four PRs that replace PR #4424 (its description lists them). This PR is based on PR #4901 and changes nothing below it.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 5 | this PR | `jhan-vnnik-5-i4934` on PR #4901 | Kill-switch parity: the live-mask loop, the per-page block mask, completion reported once, the conversion on the pool | draft until PR #4901 merges |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
