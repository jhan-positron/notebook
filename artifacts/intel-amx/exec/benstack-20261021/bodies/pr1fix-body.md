## Short version

Four fixes for the head of PR #5047. A test still writes K through `page::k`, which that PR removes, so the branch does not build and its test jobs never run. Two compile-time probes in the unit test file pass without testing anything, and the software K scoring loop costs +2.7 % of prefill time under the AMX kill switch (issue #5097), which a dense-page fast path in the live-mask build removes.

## Background

PR #5047 hides the K storage layout inside the cache: `page::score_k`, `page::try_score_k_amx`, `page::set_k_row` and `page::get_k_row` are the only ways to score, store or read a K row, and `page::k` is gone. Its "Build Tron" job fails at t/heterogeneous_scheduler_compile.cpp, in the hardware-attention configuration case, which still fills a K row through `page::k` element by element. GitHub then skips the Test, Test host and Test FPGA jobs, so the branch has no test result.

The same refactor leaves two probes in t/t_llama_unit.cpp with nothing to test: one names a member the page never had, so its negative assertion holds for the wrong reason, and one probes `page::k_packed`, which the refactor removed. Two comments still say that the dense AMX page path always applies the page and that a staged K row may point into the page.

The refactor also splits the software K scoring loop of `apply_page_tok` into a selection pass, which builds a 64-bit live mask with three tests per token, and a scoring pass, `page::score_k`. The selection pass runs alone before any dot product, and issue #5097 holds the measurement and the root cause. On a dense page (every token in the hint's range, visible to the query and inside the sliding window) the three tests decide nothing. In prefill at prompt 8192 almost every visit is such a page.

## Words used here

| Term | Meaning |
|---|---|
| the cache | h/tron/models/kv_cache.hpp: `struct page` (one 64-token KV page) and the row and scoring operations PR #5047 gives it |
| the hetero test | t/heterogeneous_scheduler_compile.cpp, built as `t_heterogeneous_scheduler`. It drives one model with a hardware (FPGA) attention slot and a software slot |
| a probe | a `constexpr bool` template in t/t_llama_unit.cpp built from a requires-expression. It is true when its body compiles for the given types, and false otherwise. A probe whose body cannot compile for any type is false for every type and tests nothing |
| the fast path | the branch of `apply_page_tok` in h/tron/models/self_attention.hpp that builds the live mask of a dense page arithmetically, without the per-token loop |
| the kill switch | `TRON_AMX_DISABLE=1`: every K token takes the software scoring path, so the selection pass runs for every visit |
| base, head, fix, c1 | the four binaries of the measurement: PR #5047's base `a5697f86d3`, its head `ade89a9d9c`, this PR's head, and PR #5047's first commit `e17a12ff09` alone. A trailing `off` means the same binary under the kill switch |

## How to review this PR

**Does the fast path select the same tokens as the per-token loop?**
- `h/tron/models/self_attention.hpp`, `apply_page_tok`: the fast path runs when the page's last token is below the hint's `tok_hi`, the query sees the hint's range, and the first token is inside the sliding window. That is the test `is_dense_amx_page` makes for the AMX path, widened from a full page to the span `[begin, end)`. The mask is `n` ones shifted by `begin`, with the full-page case written out so the shift stays defined. The loop stays unchanged for every other page. `relevant_k_tokens` is the popcount of the mask in both branches.
- Claim: on a dense page the loop sets exactly the bits `[begin, end)`. Its three tests cannot fail for any token of the span, and no token reaches `tok_hi`, so the hint never advances. The mask, the count and the returned hint are the same in both branches.
- Claim: the fast path changes nothing on the AMX path. It sits after the AMX attempt, and under the kill switch the AMX attempt does not run.
- Verification: t/t_llama_unit.cpp, case "a dense page selects the same tokens through the fast path and the token loop". It scores one page of `n` tokens as one range (the fast path) and as two ranges `[0, n - 1)` and `[n - 1, n)` (the loop), for `n` in 2, 63 and 64, and requires the same count, the same returned hint, and bit-identical running maxima, sums and value accumulators per head. `n` = 1 exercises the fast path alone. The token identity rows and the kill-switch cells below are the end-to-end check [Verification].

**Does the hetero test store its K row through the cache's contract?**
- `t/heterogeneous_scheduler_compile.cpp`: the case stores one zero row with `page::set_k_row` and a `k_source_row`. The comment above it states that `set_k_row` has no alignment precondition (`store_row` and `load_row` in h/tron/tensor/k_vnni.hpp use unaligned loads and stores). The `set_v` line above keeps its aligned source. `set_v` requires one.
- Claim: the row the case stores is the same 256 zero bytes the loop wrote, under either value of TRON_K_VNNI.
- Verification: the syntax matrix compiles the file in all four of its cells, and the binary builds on 3bda [Verification]. The run of the test is in the GitHub Test job of this PR.

**Do the two probes test something now?**
- `t/t_llama_unit.cpp`: `page_k_accepts_slot` is a template on the slot type. The `kv_slot_id` form is asserted true, the positive control that proves the body compiles. The `size_t` form is asserted false. So the false result means the raw index is refused, not that the row type was wrong. The old probe named `Page::head_size`, a member the page never had, so its body never compiled and its negative assertion held for every type. `page_exposes_kv_block` asserts that `kv_block` is private, in place of the probe of the removed `page::k_packed`: a requires-expression on a private member is false, so the assertion holds only while no page operation returns a K storage view.
- Claim: each `STATIC_REQUIRE_FALSE` now has a `STATIC_REQUIRE` with the same body that holds, or probes a member that exists.
- Verification: both are compile-time assertions. The syntax matrix instantiates them in its t_llama_unit cells [Verification].

Two comments change and need no question. `h/tron/models/self_attention.hpp`, above `apply_dense_amx_page`: the function returns false when `page::try_score_k_amx` declines, and has changed nothing then. `h/tron/gof.hpp`, `page_info`: every staged K and V row arrives in the caller's scratch through `page::get_k_row` and `page::get_v`, and no pointer into the page leaves the cache. Both are read against `apply_dense_amx_page` and `k_head_fn` in h/tron/scheduler/full.hpp at this head.

## Verification

Head `b79dfb9fed` is PR #5047's head `ade89a9d9c` followed by five commits. The four binaries base, head, fix and c1 were built on delphi-3bda on 2026-10-22 from a plain shell with clang 19.1.7, preset native, `BUILD_INGEST_MODELS=ON`, `TRON_AMX_DISPATCH=ON` and the CMake option `TRON_K_VNNI` off, and every run below is on that machine on that date with the model llama-3.1-8b-instruct, tensor parallel 2, CPU attention (`USE_HW_ATTN=0`). The syntax matrix ran on the development host with zig clang 19 at the head. No binary with `TRON_K_VNNI` on was built at this head on 3bda: the fast path does not read K and is the same code under both values of the option, and the matrix compiles every cell with the option on. The GitHub jobs of this PR build and test the head as well.

### Builds and tests

The syntax matrix is clean at the head: 22 cells, 0 errors, 0 warnings. It proves parsing, template instantiation and every `static_assert`, and nothing about object code, linking or run time.

The fix binary and `t_heterogeneous_scheduler` build on 3bda. The unit tests run on the fix build with `--skip-benchmarks`:

| test | environment | result |
|---|---|---|
| t_amx_numerics | none | 4,109 assertions in 4 cases pass |
| t_amx_dispatch_dtype | none | 1,612 assertions in 1 case pass |
| t_llama_unit | none | 267,937 assertions in 68 cases pass |
| t_amx_numerics | kill switch | 2,060 assertions in 4 cases pass. The QK and PV precision checks skip: they need the AMX unit, which the kill switch hides |
| t_llama_unit | kill switch | 267,937 assertions in 68 cases pass |

`t_heterogeneous_scheduler` did not run on 3bda. Its run is the GitHub Test job.

Clean: clang-format on the changed files, `git diff --check`, no issue or PR number in a new comment.

### Token identity

One user, temperature 0, pay-for-determinism, seed 1, prompt 1024, 256 generated tokens. Every pair must match.

| pair | result |
|---|---|
| fix against a repeat of fix | identical, 256 of 256 tokens |
| fix against head | identical, 256 of 256 tokens |
| fixoff against headoff | identical, 256 of 256 tokens |

### Performance

Cells: 8 users per engine, 256 generated tokens, prompt 8192 under the kill switch (every K token on the software path), prompt 8192 shipped (AMX on, the software path scores 2.8 % of the K tokens), and prompt 1024 shipped (10.2 %). Decision rule: 4 repetitions per arm, and the band is twice the larger standard deviation of the pair and at least 0.4 TPS or 0.15 s. Result file: exec/results/i5097-20261021/results.md in the author's campaign record.

Per-arm means and standard deviations are in the result file. The band column carries the pair's band.

| cell | pair | decode delta TPS (band) | prefill delta s (band) | prefill verdict |
|---|---|---|---|---|
| prompt 8192, kill switch | headoff against baseoff | +0.08 (0.40) | +2.152, +2.7 % (0.150) | beyond the band |
| prompt 8192, kill switch | c1off against baseoff | +0.05 (0.40) | +2.513, +3.2 % (0.150) | beyond the band |
| prompt 8192, kill switch | fixoff against headoff | +0.17 (0.40) | -3.135, -3.9 % (0.280) | beyond the band |
| prompt 8192, kill switch | fixoff against baseoff | +0.25 (0.40) | -0.982, -1.2 % (0.280) | beyond the band |
| prompt 8192, shipped | head against base | -0.03 (0.40) | +0.094 (0.150) | inside |
| prompt 8192, shipped | fix against head | -0.01 (0.40) | -0.172, -0.5 % (0.150) | beyond the band |
| prompt 8192, shipped | fix against base | -0.05 (0.40) | -0.078 (0.150) | inside |
| prompt 1024, shipped | fix against head | -0.02 (0.49) | +0.002 (0.150) | inside |

What the table says:

- The fast path removes the cost of issue #5097. Under the kill switch at prompt 8192 the fix build's prefill is 3.135 s (3.9 %) shorter than the head's, beyond the band, and 0.982 s (1.2 %) shorter than the base's.
- PR #5047's first commit alone carries the cost: c1off is 2.513 s (3.2 %) slower than baseoff, and the second commit adds nothing to it (headoff is 2.152 s slower). This agrees with the root cause on issue #5097: the loop split, not `page::score_k`.
- The fix build is faster than the base under the kill switch. Candidate mechanism: the two-pass loop loads each K row once where the base's loop re-read it for every query head (9 against 20 load micro-operations per K token in the disassembly on issue #5097), and the fast path removes the serial selection pass that cost more than that saving. A profile would confirm it.
- Decode changes by at most 0.25 TPS per user in every pair, inside the band of 0.40.
- In the shipped configuration at prompt 8192 the fix build's prefill is 0.172 s (0.5 %) shorter than the head's, just beyond the band. At prompt 1024 the two are equal.

## Open items

**The software K scoring loop costs prefill time under the AMX kill switch.** This head carries the fix and the measurement, and issue #5097 closes when PR #5047's branch takes this PR.

## The stack

PR #5047 rewrites PR #4956. Three draft PRs re-express the rest of the split of PR #4424 on its structure, each against the PR branch it re-expresses. This PR sits between: it is the smallest change that makes PR #5047's branch build and test, plus the fast path.

| Order | PR # | PR branch and base | What it adds | State |
|---|---|---|---|---|
| 1 | #5047 | bgamari/vnnik-1 -> jhan-vnnik-1-layout | the cache hides the K layout | open, author decides |
| 1a | #5098 | jhan-vnnik-1-5047-fixes -> bgamari/vnnik-1 | the build fix, the two probes, the two comments, the fast path | draft until #5047's author takes it |
| 2 | #5086 | jhan-vnnik-2-amx-5047 -> jhan-vnnik-2-amx | the VNNI AMX kernel behind the cache, with the build fix, the probes and the comments as its own commits | draft until #5047 is taken |
| 3 | #5087 | jhan-vnnik-3-shared-save-5047 -> jhan-vnnik-3-shared-save | the shared K block save | draft until #5086 is taken |
| 4 | #5094 | jhan-vnnik-4-tail-block-5047 -> jhan-vnnik-4-tail-block | the row-major tail block inside the cache | draft until #5087 is taken |

The option stays off in the released package until the fourth PR merges.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
