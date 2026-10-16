## Short version

This PR writes the VNNI-packed key vectors (K) of 128-dimension attention heads in 16-token blocks, as whole cache lines after a register transpose, and lets the idle helper threads of a generated plugin share that store with the main thread. Against the kernel PR, time to first token falls by 153 ms on 2 devices and 243 ms on 4 devices at prompt length 1,024 tokens, and decode throughput stays inside the decision band [Performance]. This is the third of four PRs [The stack].

## Background

With the option on, the layout PR's `save_k` writes each token's K row with 4 scatters [Words used here], where `main`'s row-major store writes 4 whole lines. Traces of 2026-09-14 on the Granite Rapids test machine measured that cost on the PR #4424 branch [The stack] at `9928cb28`, with qwen3-4b, 8 users and prompt length 1,024 tokens. One prefill layer's K store took 858 us at tp2 with the per-row store, and 80 us at tp2 and 60 us at tp4 with the block save shared with the helpers. A second trace set of the same day and settings put `main`'s row-major store (PR #3879's binary at `544ca05c7a`) at 274 us at tp2. Note [Shared block save] in `h/tron/models/model.hpp` states the protocol and the deadlock argument.

## Words used here

| Term | Meaning |
|---|---|
| AMX, AVX-512, FPGA | AMX (Intel Advanced Matrix Extensions) is the CPU's tile matrix-multiplication instruction set. AVX-512 is the CPU's 512-bit vector instruction set. The FPGA (field-programmable gate array) is the accelerator card that runs attention for the pages assigned to it. |
| KV page, KV head | A KV page is a 64-token unit of the KV cache (the stored keys and values of past tokens). A KV head is one key/value head. |
| VNNI-packed | Stored in the VNNI layout, the right-operand format of AMX tile multiplication: two consecutive dimensions of one token are adjacent in memory, and one 64-byte line holds that dimension pair for 16 consecutive tokens. |
| row-major K | `main`'s layout: one contiguous 128-value row per token. |
| prefill, decode | Prefill is the pass over the prompt tokens. Decode generates one token per user per pass. |
| the option, AMX dispatch, the kill switch | The option is the CMake option `TRON_K_VNNI`. It defaults to OFF. When on, it selects VNNI-packed K storage for every 128-dimension head. AMX dispatch is `TRON_AMX_DISPATCH`, the CMake option that compiles the AMX kernels and the code that selects them. The kill switch is `TRON_AMX_DISABLE=1`. It prevents use of the AMX kernels at run time. With the option on, the reader then scores every page. |
| the layout PR, the kernel PR | PR #4868 (branch `jhan-vnnik-1-layout`) and PR #4887 (branch `jhan-vnnik-2-amx`), the first two PRs of the stack. The layout PR adds the VNNI-packed K storage and the per-row store. The kernel PR adds the AMX kernel that reads it. |
| the per-row store, the block save, present mask | The per-row store (`store_row`, through `page::set_k_row`) writes one token's K row into its page's VNNI-packed K storage with 4 scatters, 4 bytes into each of the token's 64 lines. The block save (`store_block`, through `page::set_k_block`) writes the K rows of up to 16 tokens of one block as whole 64-byte lines after a register transpose. The present mask is the 16-bit mask of the block's tokens that the run holds. A partial block uses line stores masked to those lanes. |
| block | 16 consecutive tokens of a KV page, one AMX tile width. |
| pass, item | A pass is one forward computation of the model over its current input. Its items are the pass's token jobs. |
| main thread, helpers, generated plugin | A generated plugin is the model code that the code generator (`ingest/src/TronCpp.hs`) emits. Its main thread runs the schedule. Its helpers (the main helpers) run the per-token kernels. The worker index is 0 for the main thread and 1 to `n_workers - 1` for the helpers. |
| the reader | `k_vnni::qk_group` of the layout PR, the AVX-512 routine that scores a query group (the query heads sharing one KV head) against one VNNI-packed page. |
| mutation check | A deliberate code change that a test must catch. |
| `t_llama_unit`, `t_k_vnni_layout` | The model and cache unit tests, and the layout test of the layout PR. |
| LoopyTronSpec | The code generator's test suite (`ingest/test/LoopyTronSpec.hs`), run by `bin/ingest-cabal test`. |
| tp2, tp4, TPS, TTFT, the band | tp2 and tp4 split the model across 2 or 4 devices. TPS is decode throughput in tokens per second per user. TTFT is the time to first token in seconds, the maximum over the users. The band is the decision band defined under Performance. |
| base, new, head, newoff, headoff | runtron (the command-line tool of tron, the inference program under test) built from `main` at `72308ec90c` with row-major K (`base`), from this branch at `80bce9a08d` (`new`) and from the kernel PR at `0ee8671d35` (`head`), all with AMX dispatch on and the last two with the option on. `newoff` and `headoff` run `new` and `head` with the kill switch. |

## How to review this PR

The best case against merging is that the PR puts a cross-thread protocol (a window that the main thread opens and the helpers join, a claim counter, a join and a watchdog) on the main thread's path in every prefill layer of every generated plugin with the option on, for a TTFT gain that is beyond the band only at prompt length 1,024 tokens [Performance].

**Where this could be wrong**

**Can the main thread leave `save_k` before a helper has finished its rows, or mark a token complete before its rows are stored?** Read `save_k_impl` in `h/tron/models/model.hpp`: the main thread cuts the items into work units (runs of consecutive items in one block of one page), opens the window, and waits until every helper has incremented `finished` before it writes the per-token completion marks and dispatch credits. Release and acquire ordering on the counters makes every helper's row stores visible to the main thread when it returns. Verification: the three-thread section of the `save_k` case in `t_llama_unit` (a helper that starts 20 ms late, and the finished count read as the main call returns) and its mutation check [Builds and tests].

**Can a helper wait for a window that the main thread never opens, or the join wait for a helper that waits for the main thread?** Read `k_store_shared`: both sides decide from the same inputs (the option on, 2 to 128 workers, more than 16 items). Read the deadlock argument in Note [Shared block save]: why a helper always reaches its `save_k` call without the main thread's help. Read the `AttentionStmt` case of `runHelperStatement` in `ingest/src/TronCpp.hs`: it emits the helper-side `save_k` call at the same statement position as the main call. Verification: the two LoopyTronSpec specs that check both call texts, and the call counts in the 19 generated plugins [Builds and tests].

**Do two threads ever write the same bytes, and does the block save write exactly the per-row store's bytes?** Read `k_store_cut_units` and `store_k_block` (a repeated page offset ends a run, one token takes `set_k_row`, 2 to 16 tokens take `set_k_block` with the present mask). Read `store_block` in `h/tron/tensor/k_vnni.hpp`: per 32-dimension step, one 64-byte load per present row, a 16 x 16 register transpose, then 16 line stores, masked to the present lanes when the block is partial. Verification: the block-save case of `t_k_vnni_layout` (4 blocks and 38 masks, bit for bit against `store_row`), the unit invariant of the three-thread section (each work unit lies in one page, one block and one KV-write state), their mutation checks [Builds and tests], and `new` matching `head` in every token-identity cell [Verification].

**What you might decide differently**

**Should the helpers share the store, or should the main thread alone use the block save?** Choice: sharing, decided per pass by `k_store_shared`. Alternative: the block save on the main thread only, without window, join or watchdog. Check: the trace numbers in Background, which have no figure for an unshared block save. Open. Reviewers decide.

**Is an abort after 120 s the right outcome for a join that does not complete?** Choice: abort with the finished-helper and claimed-unit counts in the message. Alternative: no watchdog, or a shorter limit. Check: `k_join_timeout_s` (the 120 s limit) and `k_join_clock_spins` (pause loops) in `h/tron/models/model.hpp`. Open. Reviewers decide.

**Should the masked partial-block path land here, when PR #4901 replaces it?** Choice: the masked path, tested and measured here, until PR #4901 replaces it with the row-major tail block. Alternative: merge the tail block in this PR. Settled by the split into four PRs [The stack].

## Verification

Measured revision `80bce9a08d` on the kernel PR at `0ee8671d35`. The head `dfafd13dce` adds one test-only commit, built and run the same way. Granite Rapids test machine (Intel Xeon 6962P with AMX), 2026-10-12. Builds: `nix develop` (the project's build shell), clang 19.1.7, the `native` preset (explicit AVX-512 flags), the `RelWithDebInfo` build type. Binaries: `base`, `new`, `head`, `newoff`, `headoff` [Words used here].

### Builds and tests

Unit tests (fake device, a simulated FPGA, `--skip-benchmarks`) in three builds: the option on with AMX dispatch, on without it, and off.

- Pass in all three: `t_k_vnni_layout` (5 cases), `t_llama_unit` (66 cases, also in the option-on build under the kill switch) and `t_heterogeneous_scheduler` (scheduling across attention geometries, 3 cases).
- Pass in the two builds with dispatch and are `SUCCEED` placeholders (passing cases with no AMX coverage) in the build without it: `t_amx_dispatch_dtype` (dispatch per activation type, 1 case) and `t_amx_numerics` (AMX numerical accuracy, 5 cases).
- Passes in both option-on builds and is not in the option-off build's target list: `t_phase1_integration` (staging and dispatch integration, 64 cases).

Mutation checks in the option-on build, each failing the named case and passing again with the file restored:

- `store_block` writing block c into block c ^ 1 (c XOR 1) fails the block-save case at `t/t_k_vnni_layout.cpp:257`.
- The block condition of `k_store_cut_units` inverted fails the `save_k` case at `t/t_llama_unit.cpp:4052` of `80bce9a08d`.
- The production join removed fails it at `t/t_llama_unit.cpp:4028` of `dfafd13dce`.

LoopyTronSpec passes 1,363 tests, and in each of the 19 generated plugins the main-side and helper-side `save_k` calls equal the `save_v` calls.

Clean: clang-format on the 7 changed C++ files, fourmolu (Haskell formatting) on the 2 Haskell files, `git diff --check`, no `<cassert>` in the diff, `make lint-notes` (Note references), and a syntax-only compile in all 4 option combinations (38 configurations, 0 warnings). `make test-host` (the host suite, option-on build, fake device) passes 93 tests, with 1 unnamed skip (the permitted `t_proxy_lib`) and `t_proxy_llama31` failed for the missing `t/proxy/.venv`, the two known exceptions.

Required CI builds with both options off [nix/cmake-tron-test-build.nix], so the option-on store runs only in the manually dispatched legacy CMake lane and here (issue #4865).

### Token identity

qwen3-4b, tp2, 1 user, temperature 0, `--pay-for-determinism` (sums in a fixed order), 256 generated tokens. `new2` repeats `new` (the A/A control). `new2` and `head` must match `new` in every cell, as the block save writes the per-row store's bytes. `newoff` against `new` must repeat the kernel PR's result [PR #4887]: a first difference at generated token 247 in the CPU, prompt 1,024 cell (an exact tie there) and identical elsewhere. `base` is informational [issue #4444]. Identical means all 256 tokens match.

| Cell | new vs new2 | new vs head | newoff vs new | new vs base |
|---|---|---|---|---|
| CPU attention, prompt 1,024 tokens | identical | identical | first difference at generated token 247 | first difference at generated token 83 |
| CPU attention, prompt 8,192 tokens | identical | identical | identical | identical |
| FPGA attention, prompt 1,024 tokens | identical | identical | identical | first difference at generated token 83 |

### Performance

qwen3-4b, 8 users, 256 generated tokens, CPU attention, 3 repetitions in alternating order: tp2 at prompt lengths 1,024 and 8,192 tokens, and tp4 at 1,024 tokens. The decision band is twice the larger of the two binaries' sample standard deviations over the 3 repetitions, never smaller than 0.4 TPS or 0.15 s. A difference beyond the band counts as a change. Per-binary means and standard deviations: result record `pr3-E-cpu/summary.json`.

| Pair | TTFT tp2, prompt 1,024 | TTFT tp2, prompt 8,192 | TTFT tp4, prompt 1,024 |
|---|---|---|---|
| new vs head | -153 ms, beyond | -172 ms, inside | -243 ms, beyond |
| new vs base | -57 ms, inside | -827 ms, beyond | -75 ms, inside |
| newoff vs headoff | -50 ms, inside | beyond [Open items] | -132 ms, inside |

- `new` and `head` differ only in the store. At 8,192 tokens the 172 ms gain is 0.3 % of a prefill of about 52 s, inside the band.
- Decode TPS of `new` against `head` is inside the band in all three cells (+0.3 %, -0.6 % and +0.9 % in the table's cell order). A decode pass of 8 items is below the sharing threshold. Against `base` it is +5.1 %, +9.1 % and +3.4 %, beyond the band.
- With both binaries on the reader (`newoff` against `headoff`), the TTFT gain at prompt length 1,024 tokens is 50 ms at tp2 and 132 ms at tp4, inside the band. The cause of the smaller gain is not measured. At 8,192 tokens that pair is beyond the band [Open items].

## Open items

**A control difference beyond the band.** `newoff` against `headoff` at tp2, prompt length 8,192 tokens [Performance]: TTFT +599 ms (+0.5 %) beyond the 0.22 s band. Settled by: the K-store spans of a Perfetto trace (tron's timing trace) of one 8,192-token prefill of each binary, and 5 repetitions.

**128-dimension heads with kv_mul other than 4.** The kernel serves kv_mul (query heads per KV head) 4 only, and the store does not depend on kv_mul. Settled by: decode TPS of llama-3.2-3b (kv_mul 3) and qwen-3-30b-a3b (kv_mul 8) at this head against `main`.

**Kill switch and token divergence. Reviewers decide. [Issue #4444]** This head's results are under Token identity. The status after the stack, the forced-run data and the two rollback-contract choices are tracked in issue #4444.

**Cost rows not refreshed.** The block-save case and the three-thread section add run time to `t_k_vnni_layout` and `t_llama_unit`. Their Granite Rapids rows in `config/test-benchmarks.json` are not refreshed here, and the slice check (`bin/slice bench --check`) was not run at `80bce9a08d`. Settled by: the refresh planned with PR #4901.

## The stack

These four PRs, each based on the preceding one, replace PR #4424 (branch `jhan-amx-vnniK`, 4,054 lines), which stays open as a reference.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #4868 | `jhan-vnnik-1-layout` on `main` | VNNI-packed K layout, owner and views, row store, reader, FPGA staging gather, tests | ready for review |
| 2 | #4887 | `jhan-vnnik-2-amx` on PR #4868 | AMX QK kernel `qk_vnni_128x4`, query packer `pack_q_rows_128x4`, bit-identity test, temporary gate removed | draft until PR #4868 merges |
| 3 | #4898 | this PR, `jhan-vnnik-3-shared-save` on PR #4887 | Shared 16-token block saves by the main thread and idle helper threads (the TTFT gain) | draft until PR #4887 merges |
| 4 | #4901 | `jhan-vnnik-4-tail-block` on PR #4898 | Row-major tail block, row-major policy under hardware attention (issue #4500), option on in the `deb` package-build preset | draft until PR #4898 merges |

The option stays off in every preset until PR 4.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
