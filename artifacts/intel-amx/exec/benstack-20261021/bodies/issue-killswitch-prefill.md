## Short version

PR #5047 restructures the software K scoring loop (the CPU path that scores K rows with AVX-512 when the AMX kernel does not run). With the AMX kill switch on, every K token takes that path, and the PR's head costs +2.25 s (+2.9 %) of prefill time on llama-3.1-8b at prompt 8192 against its base, with decode inside the band (+0.3 %). This issue tracks the root cause and the fix.

## Words used here

| Term | Meaning |
|---|---|
| PR #5047, its base | PR #5047 (head `ade89a9d9c`, two commits) targets the branch of PR #4956. Its base is PR #4956's head `a5697f86d3`. |
| the option | The CMake option TRON_K_VNNI that PR #4956 adds. It is off in every preset. Both binaries of this issue have it off. |
| the software K scoring path | The loop that scores one query token against the K rows of one 64-token KV page with the AVX-512 dot product `dotter` (h/tron/kernels/dotter.hpp). It runs for every page the AMX kernel does not score. |
| the kill switch | TRON_AMX_DISABLE=1, the run-time switch that keeps the AMX attention kernels from running. Under it every K token takes the software K scoring path. |
| 3bda | delphi-3bda, the Intel server where the binaries are built and the cells run. |
| cell, arm | A cell is one model-and-shape configuration of the throughput test (model, tensor-parallel split, users per engine, prompt length, attention device). An arm is one binary run in a cell. |
| prefill time, decode TPS | Prefill time is the slowest user's prompt-processing time in seconds. Decode TPS is generated tokens per second per user. |
| the band | The decision threshold of a pair: twice the larger of the two arms' standard deviations, never below 0.4 TPS or 0.15 s. |
| K tokens by path | The exit report of TRON_ATTN_STATS=1: the share of K tokens scored by the AMX kernel, by the software path and by the FPGA. |

## Measurement

The campaign of 2026-10-21 on 3bda builds the base and the head with clang 19, the `native` preset, `BUILD_INGEST_MODELS` and `TRON_AMX_DISPATCH` on, the option off. Each cell runs 4 repetitions per arm. The cell is llama-3.1-8b, tensor-parallel 2, 8 users per engine, prompt 8192 tokens, 256 generated tokens, CPU attention.

| Cell | Arm | Decode TPS (sd) | Prefill s (sd) | K tokens by path |
|---|---|---|---|---|
| shipped (AMX on) | base | 25.37 (0.03) | 35.258 (0.075) | AMX 97.2 %, software 2.8 % |
| shipped (AMX on) | head | 25.30 (0.04) | 35.396 (0.012) | AMX 97.2 %, software 2.8 % |
| kill switch | base | 21.39 (0.04) | 78.793 (0.083) | software 100 % |
| kill switch | head | 21.46 (0.05) | 81.040 (0.057) | software 100 % |

What the table says:

- Under the kill switch the head's prefill is 2.247 s slower (+2.9 %). The band is 0.166 s. This is a degradation beyond the band.
- Under the kill switch the head's decode is +0.3 % (0.07 TPS, band 0.40 TPS), inside the band. The cost is in prefill only.
- In the shipped cell the head's prefill is +0.138 s (+0.4 %), inside the 0.150 s band. 2.8 % of the K tokens take the software path there. Scaled by that share, the kill-switch cost accounts for about 0.06 s (est.) of the 0.138 s.
- The generated tokens of the head and the base are identical in the campaign's identity cell (llama-3.1-8b, 1 user, prompt 1024 tokens, 256 of 256 tokens). No identity run exists under the kill switch.

## What changed on that path

The two commits keep the number of dot products and the K bytes read the same. They change the shape of the loop.

- Commit 1 (`e17a12ff09`, h/tron/models/self_attention.hpp): the token loop no longer scores a row-major K row as soon as it selects the token. It collects a 64-bit live mask. After the loop it builds the per-head dot-product objects and scores the selected tokens in a second pass that walks the mask with `countr_zero`.
- Commit 2 (`ade89a9d9c`, h/tron/models/kv_cache.hpp): the second pass moves into `page::score_k`. The scores pointer and the row stride become run-time parameters. The K rows are read through `kv_block::k_view`, the same view type the base's `page::k` returned.

## Hypotheses and the measurement that settles each

- **H1, the inner loop reads each K row once per query head instead of once per token.** The base scores the 4 query heads of one K row inside one unrolled block. The head's `score_k` loops over the heads inside a loop over the mask. If the compiler no longer keeps the 256-byte K row in registers across the 4 heads, the loop issues 4 times the loads. Settles it: the disassembly of the inner loop of both -O3 objects (compiled on the development host, no 3bda needed), then `perf stat` of instructions and L1 loads on the two kill-switch binaries in prefill.
- **H2, the second pass costs per selected token.** The mask walk, the row view construction and the run-time stride add instructions per token. A 128-element bf16 dot product is about 8 loads and 8 fused multiply-adds, so a few extra instructions per token are a measurable share. Settles it: the same disassembly, and a `perf record` of prefill with the self time of `score_k` against the base's `apply_page_range` loop.
- **H3, why prefill and not decode.** In prefill one page's K rows stay in the L1 or L2 cache across the many query tokens of one minibatch, so the loop is bound by instructions. In decode each user's one query streams K from memory, so the loop is bound by memory and extra instructions hide behind the loads. This hypothesis explains the decode result and does not name a cause by itself. Settles it: `perf stat` cycles and instructions per K token in prefill and in decode for both binaries.

## Plan

1. Development host, no 3bda: compile the attention translation unit of both heads at -O3 with the same flags and compare the disassembly of the software K scoring loop (instructions per token, loads per token, unrolling).
2. 3bda, when the machine is free: `perf record` and `perf stat` on the two kill-switch binaries in the cell above, one repetition each, during prefill only.
3. Fix, decided by the result: score the row-major K row inside the selection loop again (the base's shape behind the cache's `score_k`), or load each K row once per token inside `score_k` and apply the 4 heads to it.

## Who decides

The author of PR #5047 and the owner of the stack PR #4956 to PR #4959. The three draft PRs that re-express PRs #4957 to #4959 on PR #5047's structure (#5086, #5087, #5094) inherit the loop and carry this issue as an open item.
