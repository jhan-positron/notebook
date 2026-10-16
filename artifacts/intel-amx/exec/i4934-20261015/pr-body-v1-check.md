# Plain-English check of pr-body-v1.md

Short version: 88 violations. Rule 1: 45, Rule 2: 12, Rule 3: 5, Rule 4: 4, Rule 5: 0, Rule 6: 4, Rule 7: 4, Rule 8: 14. Plus 4 past-tense phrases against the document's own present-tense rule (listed as "Doc").

Notes on the fixes:

- Definitions added in the Words used here table are limited to terms used in more than one section (AMX, K/KV/page, VNNI, the forward end, the pool, FPGA). Terms used in one section are defined inline in a parenthesis at first use.
- Code definitions were checked against the fix worktree at c30a86f252 (CMakeLists.txt options, kv_cache.hpp, k_vnni.hpp, model.hpp, common.hpp) and the GitHub titles of issue #4444 and PRs #4901 and #4898.
- The Short version keeps three sentences (Rule 5 cap), so its first sentence still joins two costs with ", and" (allowed by Rule 8).
- Not changed, for the author: (a) the Words table gives PR #4901 as `ea94e95a4e` while Verification gives PR #4901's head as `175b1837b9` (GitHub shows 175b1837b9 as the PR head today); (b) "where the base warns about two" is a count comparison against another head, which the PR-description rules exclude; (c) "(its description lists them)" in The stack has an ambiguous "its"; (d) the 1.2 billion and 77 billion loop counts carry "about" but no "est." mark, and the check cannot tell whether they are measured or computed.
- Word count without the Words used here section: 1,894 (v1: 1,509), under the 2,000 limit.

| Rule | Original phrase | Fix |
|---|---|---|
| 1 | With the AMX kill switch | With the kill switch for AMX (a CPU instruction set), plus a table row "AMX, AVX-512" |
| 1 | converts the completed K blocks | converts the completed K (key) blocks, plus a table row "K, V, KV head, page" |
| 1 | 2.7 to 3.7 % of decode throughput | 2.7 to 3.7 % of decode (token generation) throughput |
| 1 | an 8,192-token prefill against PR #4898 | an 8,192-token prefill (the prompt pass) against PR #4898 |
| 1 | the forward end converts (first use, undefined) | table row "the forward end: The end of one forward pass (one pass of the model over its batch)" |
| 1 | while every worker waits / on the worker pool (undefined) | table row "the pool, a worker, the main thread" |
| 1 | whether the token's block is row-major or VNNI (first use of VNNI) | table row "VNNI layout, tail block" with VNNI expanded |
| 1 | (Note [Row-major tail block] in ... (Note undefined) | A Note is a named comment block in the code. |
| 1 | and its token body 77 billion times | and its token body (the per-token part of the loop) 77 billion times |
| 1 | (36 layers, 8 KV heads) (KV head undefined) | KV head defined in the table row "K, V, KV head, page" |
| 1 | short runs row-major | short runs (saves of fewer than 16 tokens, shorter than one block) stay row-major |
| 1 | no conversion under hardware-scored operations (issue #4500) | no conversion happens under hardware-scored operations (attention scored on the FPGA, issue #4500), plus a table row for FPGA attention |
| 1 | runtron builds of this head | runtron (the command-line tool of tron, the inference program under test) builds of this head |
| 1 | with AMX dispatch and the layout option on | with AMX dispatch (`TRON_AMX_DISPATCH`, the build option that compiles the AMX kernels in) and the layout option (`TRON_K_VNNI`, the build option that stores K in the VNNI layout) on |
| 1 | scores a query group | scores a query group (the query heads that share one KV head) |
| 1 | through a 64-bit live mask | through a 64-bit live mask (one bit per token of the page that the call must score) |
| 1 | one byte per page and storage slot | one byte per page and storage slot (one K store of the page) |
| 1 | on a VNNI slot | on a VNNI slot (a K store under the layout option) |
| 1 | the reader scores each lane | the reader scores each lane (one token position of its vector) |
| 1 | bit-exact `m_star` | `m_star` (the running score maximum) bit-exact |
| 1 | dominant row | the dominant row (the row with the largest score) |
| 1 | bf16, float and fp16 queries | for queries in bf16, float and fp16 (three number formats) |
| 1 | an argument that also serves the dense AMX gate | The same argument serves the dense AMX gate (the check that sends a page to the AMX kernel only when every block of the page is VNNI). |
| 1 | before the pending sections start (the latch of Note [Minibatch Dependency Tracking] ...) | before the pending sections start. A pending section is attention work that waits, through a latch (a countdown that the writers tick), for KV written in this pass by a minibatch (a group of requests the model runs together) that may be a different one (Note [...]). |
| 1 | A page read by a ready section | A page read by a ready section (attention work whose KV is written before the pass) |
| 1 | after the plugin joined every worker | after the plugin (the model-specific code that runs the forward pass) has joined every worker |
| 1 | one strided share per worker | one strided share per worker (every n-th block, n the worker count) |
| 1 | before the logit delivery is enqueued | before the logit (per-word score) delivery is enqueued |
| 1 | The listener thunks of that delivery | The listener thunks (callbacks) of that delivery |
| 1 | take the tree lock | take the tree lock (the lock over the KV cache's books) |
| 1 | may move or free books | may move or free books (the owners of the cache's pages) |
| 1 | the release `fetch_or` ... with acquire (memory orders undefined) | added: Release and acquire are the C++ memory orders that order the block's bytes before its bit. |
| 1 | before it touches a plane | before it touches a plane (one page's K storage) |
| 1 | on a Granite Rapids machine (Intel Xeon 6962P, 8 FPGA cards) | a Granite Rapids server (Intel Xeon 6962P, the CPU generation with AMX, and 8 FPGA cards), FPGA expanded in the table |
| 1 | the `native` preset, `RelWithDebInfo` | the `native` preset (the CMake preset for the build host's CPU) and `RelWithDebInfo` (the optimized build type with debug symbols) |
| 1 | `--skip-benchmarks`: | `--skip-benchmarks` (the test flag that leaves out the benchmark sections): |
| 1 | clang-format on every touched file | clang-format (the code formatter) leaves every touched file unchanged |
| 1 | `fixoff` against `fix` follows issue #4444 | follows issue #4444 (the kill-switch rollback contract and the token divergence it records) |
| 1 | Cells: qwen3-4b | The cells (a cell is one attention path, tensor parallel degree and prompt length): qwen3-4b (the model) |
| 1 | CPU attention at tp2 ... and at tp4 | at tp2 (tensor parallel degree 2, the number of FPGA cards one engine spans) ... and at tp4 |
| 1 | 0.4 TPS or 0.15 s / decode TPS and TTFT | 0.4 TPS (decode tokens per second) or 0.15 s (of TTFT, the time to first token) |
| 1 | temperature 0, `--pay-for-determinism` | temperature 0 (the top-scoring token every step) and `--pay-for-determinism` (the runtron flag that makes a run repeatable) |
| 1 | the `convert_k_blocks` trace span | the `convert_k_blocks` trace span (a timed region in the trace) |
| 1 | Mutation checks: | Mutation checks (a deliberate break of the code that the named test must catch): |
| 1 | a fixture with two minibatches | a fixture (a test setup) with two minibatches |
| 2 | PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes and converts it at the forward end | PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes. It converts the block to the VNNI layout at the forward end (...). |
| 2 | Its software loop had to tell, per token, whether the token's block is row-major or VNNI, and it built the row-major dotters before knowing whether any token needed them. | The loop under PR #4901 tells, per token, whether the token's block is row-major or VNNI. It builds the row-major dotters before it knows whether any token needs them. |
| 2 | With the kill switch every (query, page) visit runs that loop: an 8-user prefill of 8,192 tokens runs it about 1.2 billion times and its token body 77 billion times. | With the kill switch every (query, page) visit runs that loop. An 8-user prefill of 8,192 tokens runs the loop about 1.2 billion times, and its token body (...) 77 billion times. |
| 2 | The two parts partition the live mask, so a token is scored exactly once. | The two parts partition the live mask. So a token is scored exactly once. |
| 2 | The dotter arithmetic for a row-major row is unchanged, and the reader scores each lane ... | The dotter arithmetic for a row-major row is unchanged. The reader scores each lane ... |
| 2 | before the query loop, and the value reaches `apply_page_tok` as an argument that also serves the dense AMX gate. | and before the query loop. The value reaches `apply_page_tok` as an argument. The same argument serves the dense AMX gate (...). |
| 2 | A page read by a ready section has no writer in the pass, and a pending page is read only after every writer counted the latch down. | A page read by a ready section (...) has no writer in the pass. A pending page is read only after every writer has counted the latch down. |
| 2 | and never for a row saved again, so `save_k` queues every block once. | and never for a row saved again. So `save_k` queues every block once. |
| 2 | one strided share per worker, and the call waits for the latch before the logit delivery is enqueued. | one strided share per worker (...). The call waits for the latch before the logit (per-word score) delivery is enqueued. |
| 2 | and may move or free books, so the join must come first. | and may move or free books (...). So the join must come first. |
| 2 | `fix` against `new` is expected identical in the CPU cells, since both score a row-major row with the same dotter and a VNNI block with the same reader | `fix` against `new` is expected identical in the CPU cells. Both score a row-major row with the same dotter and a VNNI block with the same reader. |
| 2 | gives the serial cost per block, against which the pool's hand-off cost is weighed. | gives the serial cost per block. The pool's hand-off cost is compared with that cost. |
| 3 | about 300 in-place transposes (36 layers, 8 KV heads) | about 300 in-place transposes (36 layers times 8 KV heads) |
| 3 | a queue of `k_convert_parallel_min` blocks or more / `k_convert_parallel_min` (8) | a queue of `k_convert_parallel_min` (8 blocks) or more / `k_convert_parallel_min` (8 blocks) |
| 3 | 12 blocks completed in one pass | completes 12 blocks in one pass (above the 8-block pool threshold) |
| 3 | never smaller than 0.4 TPS or 0.15 s | never smaller than 0.4 TPS (decode tokens per second) or 0.15 s (of TTFT, the time to first token) |
| 3 | The value is an estimate until then. | The value is an estimate (est.) until then. |
| 4 | Verification: the new `t_amx_dispatch_dtype` case "..." (bit-exact `m_star` against the two readers, dominant row in a row-major block and in a VNNI block, bf16, float and fp16 queries), and the mixed pages of the `t_llama_unit` case "apply and join page ranges". (names tests, carries no sentence) | Verification: the new `t_amx_dispatch_dtype` case "..." checks `m_star` (...) bit-exact against the two readers, with the dominant row (...) in a row-major block and in a VNNI block, for queries in bf16, float and fp16 (...). The mixed pages of the `t_llama_unit` case "apply and join page ranges" cover the split as well. |
| 4 | Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows (the gate refuses a page with any row-major block). | Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows check that the gate refuses a page with any row-major block. |
| 4 | Verification: the `t_k_vnni_layout` page-state case (a re-saved row ... converts once), and the `t_llama_unit` save_k section "..." (12 blocks completed in one pass, every row, every block bit and the empty queue checked). | Verification: the `t_k_vnni_layout` page-state case checks that a re-saved row of a complete block does not report the completion again, and that the block converts once. The `t_llama_unit` save_k section "..." completes 12 blocks in one pass (...) and checks every row, every block bit and the empty queue. |
| 4 | rest on the code argument in section 4 (no section carries a number) | rest on the code argument in [How to review this PR] |
| 6 | arms (their `off` arms; arms `head`, `headoff`, ...; the two arms' sample standard deviations) | builds / binaries (their `off` builds; binaries `head`, `headoff`, ...; the two binaries' sample standard deviations) |
| 6 | independently of the other lanes' liveness | independently of whether the other lanes are live |
| 6 | against which the pool's hand-off cost is weighed | The pool's hand-off cost is compared with that cost. |
| 6 | Clean at the head: clang-format on every touched file, and a syntax-only compile ... | At the head, clang-format (the code formatter) leaves every touched file unchanged. At the head, a syntax-only compile ... reports 0 errors. |
| 7 | Background paragraph "PR #4901 keeps ... with the pool idle." (storage policy, loop test, loop counts, conversion cost in one paragraph) | three paragraphs: storage and conversion point, the loop and its counts, the forward-end cost |
| 7 | Paragraph "The same build passes ... where the base warns about two." (five results in one paragraph) | four bullets: kill-switch tests, pending builds, clang-format, syntax-only compile and its warning |
| 7 | The rule: `fix2` (a repeat of `fix`) must match `fix`; `fix` against `new` ...; and `fixoff` against `fix` follows issue #4444. | The rules: three bullets, one per pair |
| 7 | Performance paragraph "Cells: ... The decision rule: ..." (cells, band, decision rule in one paragraph) | cells as two bullets, the band as two sentences, the decision rule as three bullets |
| 8 | fix, new, head; fixoff, newoff, headoff (term cell) | fix, new, head and fixoff, newoff, headoff |
| 8 | with AMX dispatch and the layout option on; the `off` arms run the same binaries with the kill switch. | ... on. The `off` builds run the same binaries with the kill switch. |
| 8 | turns the block mask into 64 token bits; the live tokens of VNNI blocks go to the reader in one call, the others to the dotters one row at a time. | turns the block mask into 64 token bits. The live tokens of VNNI blocks go to the reader in one call. The others go to the dotters one row at a time. |
| 8 | `h/tron/models/common.hpp`); `convert_pending_k_blocks` runs after | `h/tron/models/common.hpp`). `convert_pending_k_blocks` runs after |
| 8 | release `fetch_or` of `k_block_to_vnni_at`; every reader loads | release `fetch_or` of `k_block_to_vnni_at`. Every reader loads |
| 8 | under the kill switch; `t_amx_numerics` then reports | under the kill switch. `t_amx_numerics` then reports |
| 8 | with 0 errors; the dispatch-off `t_amx_dispatch_dtype` warns | reports 0 errors. The dispatch-off `t_amx_dispatch_dtype` warns |
| 8 | must match `fix`; `fix` against `new` is expected identical | bullets, one sentence each |
| 8 | 3 repetitions in alternating order; CPU attention at tp2 ...; FPGA attention at tp2 and tp4 | 3 repetitions in alternating order. Then two bullets, CPU attention and FPGA attention. |
| 8 | never smaller than 0.4 TPS or 0.15 s; a difference beyond it counts as a change. | never smaller than 0.4 TPS (...) or 0.15 s (...). A difference beyond the band counts as a change. |
| 8 | must fail the new `t_amx_dispatch_dtype` case; reporting a completion on a re-saved row must fail the page-state case; converting half the queue must fail the 12-block section. | three sentences |
| 8 | Head `c30a86f252`, measured on 2026-10-15 against the base `175b1837b9` (PR #4901's head) on a Granite Rapids machine (...), `nix develop` (...), clang 19.1.7, the `native` preset, `RelWithDebInfo`. (one fragment, nine items) | Head `c30a86f252` is measured on 2026-10-15 against the base `175b1837b9` (PR #4901's head). The machine is ... The build is ... The binaries are ... |
| 8 | Q1 Verification sentence: 60 words with a nested parenthesis list | two sentences (see the Rule 4 row) |
| 8 | Q3 Verification sentence: two nested parenthesis lists | two sentences (see the Rule 4 row) |
| Doc | as the parent PR #4898 did | as the parent PR #4898 does |
| Doc | had to tell ... built ... before knowing whether any token needed them | tells ... builds ... before it knows whether any token needs them |
| Doc | after the plugin joined every worker | after the plugin (...) has joined every worker |
| Doc | after every writer counted the latch down | after every writer has counted the latch down |

# Corrected text (pr-body-v2.md)

## Short version

With the kill switch for AMX (a CPU instruction set), the software attention loop of PR #4901 builds four dot-product helpers on every page visit and tests the layout of every token, and the forward end converts the completed K (key) blocks one by one on the main thread while every worker waits. This PR makes the loop set one bit per relevant token, as the parent PR #4898 does, scores the rows of the row-major tail blocks after the loop, reads a page's layout state once per page instead of once per visit, and converts the completed blocks on the worker pool. Issue #4934 records the loss this removes: 2.7 to 3.7 % of decode (token generation) throughput and about half a second of an 8,192-token prefill (the prompt pass) against PR #4898 with the kill switch.

## Background

PR #4901 keeps an incomplete 16-token block of K rows row-major inside the block's own bytes. It converts the block to the VNNI layout at the forward end (Note [Row-major tail block] in `h/tron/tensor/k_vnni.hpp` and Note [K VNNI storage] in `h/tron/models/kv_cache.hpp`). A Note is a named comment block in the code.

The loop under PR #4901 tells, per token, whether the token's block is row-major or VNNI. It builds the row-major dotters before it knows whether any token needs them. With the kill switch every (query, page) visit runs that loop. An 8-user prefill of 8,192 tokens runs the loop about 1.2 billion times, and its token body (the per-token part of the loop) 77 billion times.

The forward-end conversion of a user's completed block is about 300 in-place transposes (36 layers times 8 KV heads) on the main thread with the pool idle.

The fix keeps the storage policy of PR #4901: short runs (saves of fewer than 16 tokens, shorter than one block) stay row-major, whole blocks are saved VNNI, the conversion happens at the forward end, and no conversion happens under hardware-scored operations (attention scored on the FPGA, issue #4500).

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
| fix, new, head and fixoff, newoff, headoff | runtron (the command-line tool of tron, the inference program under test) builds of this head, of PR #4901 (`ea94e95a4e`) and of PR #4898 (`dfafd13dce`), with AMX dispatch (`TRON_AMX_DISPATCH`, the build option that compiles the AMX kernels in) and the layout option (`TRON_K_VNNI`, the build option that stores K in the VNNI layout) on. The `off` builds run the same binaries with the kill switch. |

## How to review this PR

**Does the split of the live mask score every relevant token once, through the reader of its block's layout?**
- Read the loop in `h/tron/models/self_attention.hpp`: on a VNNI slot (a K store under the layout option) the token body is `live |= offset_bit(i)` and nothing else. After the loop, `k_vnni::block_token_mask` turns the block mask into 64 token bits. The live tokens of VNNI blocks go to the reader in one call. The others go to the dotters one row at a time.
- Read `block_token_bits` and `block_token_mask` in `h/tron/tensor/k_vnni.hpp`: bit c of the block mask becomes page offsets 16 c to 16 c + 15.
- The two parts partition the live mask. So a token is scored exactly once. The dotter arithmetic for a row-major row is unchanged. The reader scores each lane (one token position of its vector) independently of whether the other lanes are live.
- Verification: the new `t_amx_dispatch_dtype` case "the software loop scores row-major rows with the dotter and VNNI blocks with the reader" checks `m_star` (the running score maximum) bit-exact against the two readers, with the dominant row (the row with the largest score) in a row-major block and in a VNNI block, for queries in bf16, float and fp16 (three number formats). The mixed pages of the `t_llama_unit` case "apply and join page ranges" cover the split as well.

**Can the block mask read once per page be stale for a query of the same call?**
- Read `apply_page_range` in `h/tron/models/self_attention.hpp`: the read sits after the dismissal of empty and workless pages (pages with no work for the call), and before the query loop. The value reaches `apply_page_tok` as an argument. The same argument serves the dense AMX gate (the check that sends a page to the AMX kernel only when every block of the page is VNNI).
- Read `save_k` in `h/tron/models/model.hpp`: a whole-block save sets the bits before the pending sections start. A pending section is attention work that waits, through a latch (a countdown that the writers tick), for KV written in this pass by a minibatch (a group of requests the model runs together) that may be a different one (Note [Minibatch Dependency Tracking] in `h/tron/models/common.hpp`). `convert_pending_k_blocks` runs after the plugin (the model-specific code that runs the forward pass) has joined every worker.
- A page read by a ready section (attention work whose KV is written before the pass) has no writer in the pass. A pending page is read only after every writer has counted the latch down. So no bit changes while a call scores.
- Verification: the `t_amx_dispatch_dtype` sections with 0 and with 48 recorded rows check that the gate refuses a page with any row-major block. The timing argument itself has no test. Open: reviewers decide whether the argument in the code comment is enough.

**Can two pool tasks convert one block, or a task race a reader?**
- Read `note_k_row_saved` in `h/tron/models/kv_cache.hpp`: it reports a block's completion for the call that sets the last of the 16 row bits, and never for a row saved again. So `save_k` queues every block once.
- Read `convert_pending_k_blocks` in `h/tron/models/model.hpp`: a queue of `k_convert_parallel_min` (8 blocks) or more goes through `thread_pool::parallel_for`, one strided share per worker (every n-th block, n the worker count). The call waits for the latch before the logit (per-word score) delivery is enqueued. The listener thunks (callbacks) of that delivery take the tree lock (the lock over the KV cache's books) on pool workers and may move or free books (the owners of the cache's pages). So the join must come first.
- Each task publishes its blocks with the release `fetch_or` of `k_block_to_vnni_at`. Every reader loads the block bits with acquire before it touches a plane (one page's K storage). Release and acquire are the C++ memory orders that order the block's bytes before its bit.
- Verification: the `t_k_vnni_layout` page-state case checks that a re-saved row of a complete block does not report the completion again, and that the block converts once. The `t_llama_unit` save_k section "the forward end converts a queue of many blocks on the pool" completes 12 blocks in one pass (above the 8-block pool threshold) and checks every row, every block bit and the empty queue.

## Verification

Head `c30a86f252` is measured on 2026-10-15 against the base `175b1837b9` (PR #4901's head). The machine is a Granite Rapids server (Intel Xeon 6962P, the CPU generation with AMX, and 8 FPGA cards). The build is `nix develop` (the project's build shell), clang 19.1.7, the `native` preset (the CMake preset for the build host's CPU) and `RelWithDebInfo` (the optimized build type with debug symbols). The binaries are `fix`, `new`, `head` and their `off` builds [Words used here].

### Builds and tests

Unit tests with a fake device, the layout option and AMX dispatch on, and `--skip-benchmarks` (the test flag that leaves out the benchmark sections):

| Test | Result |
|---|---|
| `t_k_vnni_layout` | 1,041,278 assertions in 10 cases, pass |
| `t_amx_dispatch_dtype` | 2,778 assertions in 2 cases, pass |
| `t_amx_numerics` | 6,669 assertions in 5 cases, pass |
| `t_llama_unit` | 277,962 assertions in 66 cases, pass |
| `t_heterogeneous_scheduler` | 2,855 assertions in 4 cases, pass |
| `t_phase1_integration` | 6,220 assertions in 64 cases, pass |

- The same build passes `t_llama_unit` and `t_heterogeneous_scheduler` under the kill switch. `t_amx_numerics` then reports AMX unavailable in its three AMX checks and skips them.
- The option-off and the dispatch-off builds are pending [Open items].
- At the head, clang-format (the code formatter) leaves every touched file unchanged.
- At the head, a syntax-only compile in 22 configurations (AMX dispatch on or off, the option on or off, five test files and the AMX kernel file) reports 0 errors. The dispatch-off `t_amx_dispatch_dtype` warns about one unused test constant, where the base warns about two.

### Token identity

Pending [Open items]. The rules:
- `fix2` (a repeat of `fix`) must match `fix`.
- `fix` against `new` is expected identical in the CPU cells. Both score a row-major row with the same dotter and a VNNI block with the same reader.
- `fixoff` against `fix` follows issue #4444 (the kill-switch rollback contract and the token divergence it records).

### Performance

Pending [Open items]. The cells (a cell is one attention path, tensor parallel degree and prompt length): qwen3-4b (the model), 8 users, 256 generated tokens, 3 repetitions in alternating order.
- CPU attention at tp2 (tensor parallel degree 2, the number of FPGA cards one engine spans) with prompts of 1,024 and 8,192 tokens, and at tp4 with 1,024 tokens, binaries `head`, `headoff`, `new`, `newoff`, `fix`, `fixoff`.
- FPGA attention at tp2 and tp4 with 1,024 tokens, binaries `head`, `new`, `fix`.

The band is twice the larger of the two binaries' sample standard deviations, and never smaller than 0.4 TPS (decode tokens per second) or 0.15 s (of TTFT, the time to first token). A difference beyond the band counts as a change. The decision rule, every line of which must hold:
- `fixoff` against `headoff` is inside the band in decode TPS and TTFT in every CPU cell (the kill-switch loss of issue #4934 is gone).
- `fix` against `new` is inside the band or better in decode TPS (no cost with AMX on).
- `fix` against `new` is inside the band under FPGA attention (the policy of issue #4500 is untouched).

## Open items

**Pending measurements.** Each is queued at this head on the same machine:
- Performance in the cells of [Verification]: settles the decision rule there.
- Token identity: `fix` against `fix2`, `new` and `fixoff` in the CPU cells at prompts of 1,024 and 8,192 tokens and in the FPGA cell at 1,024 tokens, with 1 user, temperature 0 (the top-scoring token every step) and `--pay-for-determinism` (the runtron flag that makes a run repeatable).
- The option-off build (row-major K, 5 tests) and the dispatch-off build (6 tests).
- The derivation of `k_convert_parallel_min` (8 blocks): the `convert_k_blocks` trace span (a timed region in the trace) of a kill-switch decode run gives the serial cost per block. The pool's hand-off cost is compared with that cost. The value is an estimate (est.) until then.
- Mutation checks (a deliberate break of the code that the named test must catch): scoring the row-major rows through the reader must fail the new `t_amx_dispatch_dtype` case. Reporting a completion on a re-saved row must fail the page-state case. Converting half the queue must fail the 12-block section.

**No test of the forward-end ordering.** The join of the conversion before the logit delivery, and the stability of the per-page read, rest on the code argument in [How to review this PR]. Reviewers decide whether a fixture (a test setup) with two minibatches is needed.

## The stack

PR #4901 is the last of four PRs that replace PR #4424 (its description lists them). This PR is based on PR #4901 and changes nothing below it.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 5 | this PR | `jhan-vnnik-5-i4934` on PR #4901 | Kill-switch parity: the live-mask loop, the per-page block mask, completion reported once, the conversion on the pool | draft until PR #4901 merges |

🤖 Generated with [Claude Code](https://claude.com/claude-code)
