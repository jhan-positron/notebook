# page_share_counters: count query tokens per KV page visit (instrumentation, default off)

**Draft.** First of the pieces PR #3879 is being split into, in the order Ben (bgamari-positron, the requested reviewer) proposed: the page-share counters (this PR), then the attention kernel that uses AMX (Intel Advanced Matrix Extensions) without the K mirror (#3879 itself, to be retitled; the K mirror is a second copy of the attention keys), then the K mirror (a draft stacked on #3879). A one-line fix Ben found while reviewing is its own PR. This PR is based on `main` and does not depend on the kernel PRs.

## Words used here

- A **KV page** holds 64 tokens of attention keys (K) and values (V); a **kv_head** is one key/value head.
- The **minibatch** is the set of query tokens one attention call serves.
- A **page visit** is the processing of one (KV page, kv_head) pair in the software attention loop (`apply_page_range`); its **query tokens per page visit** is the number of query tokens of the minibatch that had at least one relevant K token on that page (in the code: `n_relevant_query_tokens`). A **shared** visit served two or more query tokens. The **pending** pass is the second attention pass of a step, over the pages whose K and V are written during that same forward pass, by this or another minibatch.

## What it adds

`h/tron/kernels/page_share_counters.hpp` and five hook blocks guarded by `TRON_PAGE_SHARE_COUNTERS` in `h/tron/models/self_attention.hpp`. For every page visit the hooks count the query tokens served, keep a histogram of that count (slots 1, 2, 3, 4, 5-8, 9-16, >16 query tokens) and add the per-call counts to process-wide totals. Visits that served no query token are not counted. At normal process exit a static object's destructor prints a four-line summary to stderr if at least one visit was counted; no summary appears after an abort (a failed `TRON_ASSERT`), a crash or SIGKILL.

The CMake option `TRON_PAGE_SHARE_COUNTERS` (top-level `CMakeLists.txt`, default OFF) adds the define of the same name to the `tron` library. Without the define the header declares no instrumentation and the preprocessor removes the five hook blocks, so a default build compiles no counter code into the library. The new test supplies the define to its own translation unit (see Test).

## Why keep it in the tree

The first version of this instrumentation measured the averages below on 2026-08-18 (qwen-3-4b, tp2 = tensor parallelism over two FPGA (field-programmable gate array) cards, attention on the CPU, 8 users). Prefill is the processing of the prompt; decode is the generation of the following tokens. The values are workload-wide averages; they show how often several query tokens visit the same page, which is the condition under which a per-page kernel could serve several query tokens from one page load. The source code does not repeat these numbers; this description is their record:

| Workload (8 users) | Query tokens per page visit, average |
|---|---|
| prefill-heavy: prompt 2048 tokens, 2 generated | 110.9 |
| decode-heavy, private prompts: prompt 64 tokens, 512 generated | 1.02 |
| decode with a shared system prompt: 1024 shared + 64 private prompt tokens, 256 generated | 5.06 |

The kernel in the next PR serves the four query heads of one query token per page load; the averages mark where a kernel that batches several query tokens per page would pay (prefill and shared prompts) and where it would not (private decode, 1.02). Keeping the instrumentation in the tree, behind an option, makes the measurement repeatable when the batching behaviour changes. A query counts if at least one K token on the page is relevant to it; the counters do not measure whether the page was dense (all 64 tokens visible) for that query.

## Test

`t/t_page_share_counters.cpp` checks the histogram slot boundaries, that a visit with no relevant query token is not counted, the per-call counts including the shared subset (visits with at least two query tokens) and the pending-phase count, and that `flush()` adds the per-call counts to the process-wide totals. It exercises the counter accumulator directly, not the hooks in the attention loop. Without it, a count landing in the wrong slot or a flush that drops or double-counts a total would silently distort the reported statistics. It carries the `fake` label, so the continuous-integration (CI) host suite (`bin/slice run --filter=host`, which selects every test without the `fpga` label) runs it whenever that suite runs. The registration passes the define to this one test target, so the test runs whatever the option's value. The CMake CI lane (the `build` job of `.github/workflows/cmake-single-platform.yml`) now also configures with `-DTRON_PAGE_SHARE_COUNTERS=ON`, so builds in that lane compile the five hook blocks in the software attention loop; tests that execute that path exercise the hooks, and a binary that counted at least one page visit prints four `[page-share]` summary lines to stderr at normal exit (`t_llama_unit` does, in the build with the option on); `README.ci.md` documents the flag. The option's default and every other lane's configuration are unchanged. The cost-data entry for `t_page_share_counters` in `config/test-benchmarks.json`, which CI's `bin/slice bench --check` requires, has not been measured yet (the measurement needs the whole test machine, which is shared this week); until it is added, CI's "Check slice cost data" step fails.

## Review history

Ben [asked why the counters are global inline variables](https://github.com/positron-ai/tron/pull/3879#discussion_r3936847383) and then [named the C++17 feature himself](https://github.com/positron-ai/tron/pull/3879#discussion_r3937150401); the thread holds the answer (a C++17 inline variable has one definition shared by every translation unit that includes the header, so the instrumentation needs no `.cpp` file); the header does not repeat it. The agent review Wade (Wado-posi) posted on #3879 ([comment](https://github.com/positron-ai/tron/pull/3879#issuecomment-5544513215)) asked for the instrumentation to leave the tree; this PR keeps it behind an option with a test and a stated purpose instead.

## Verification

Built and tested on 2026-09-07 on delphi-3bda (Intel Xeon 6962P, a Granite Rapids CPU) from commit REV1-TIP in a clean worktree, CMake preset `cross-avx512` (with `-DBUILD_INGEST_MODELS=OFF`, which only skips the ingest models), once with `-DTRON_PAGE_SHARE_COUNTERS=ON` and once with `-DTRON_PAGE_SHARE_COUNTERS=OFF` (the option's default value). In both configurations the two test targets and the `tron` library they link compiled. Catch2 (the test framework) printed the same summary lines in both builds: `t_page_share_counters` "All tests passed (61 assertions in 4 test cases)"; `t_llama_unit` "All tests passed (120054 assertions in 27 test cases)". In the ON build `t_llama_unit` printed the four `[page-share]` summary lines at exit; in the OFF build it printed none. clang-format-19 (the repository's formatter) leaves the files of this PR unchanged. The cost-data entry for `t_page_share_counters` has not yet been measured, so CI's "Check slice cost data" step will fail until it is added to `config/test-benchmarks.json`.

## Labels

`Skip benchmarks`, the repository's default for every PR.
