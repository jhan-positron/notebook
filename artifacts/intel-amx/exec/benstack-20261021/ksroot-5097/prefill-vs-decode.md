# Why PR 5047's software K scoring loop costs +2.9 % of prefill and 0 % of decode

## Short version

In prefill every K row is read from L1 cache by 128 queries in a row, so the scoring loop is bound by instruction throughput, and the head's two-pass loop adds about 5 to 6 instructions per K token (est. 2 to 3.5 core cycles). In decode every K row comes from DRAM once per step, each K token costs 180 TSC cycles instead of 75, and the extra instructions fit inside the memory wait. The attention path stats of the campaign already show this: prefill busy cycles +3.22 % (2.43 TSC cycles per K token), decode busy cycles -0.28 %.

## Words used here

- tron = the inference program under test. runtron = its command-line tool.
- base = runtron built from a5697f86d3 (the PR 4956 head). head = runtron built from ade89a9d9c (the PR 5047 head = base + commits e17a12ff09 and ade89a9d9c).
- kill switch = TRON_AMX_DISABLE=1. AMX (Intel tile-matrix instructions) is then unavailable at run time and every page is scored by the software loop.
- AMX-on / shipped = the same binaries without the kill switch. AVX = the AVX-512 vector instructions of the software loop.
- visit = one call of apply_page_tok: one query token x one KV page (64 K tokens) x one KV head (4 query heads, kv_mul 4).
- K token = one row of K (128 bf16 values = 256 bytes) scored inside a visit. "AVX K tokens" = K tokens scored by the software loop.
- dotter = the 128-dim bf16 dot product helper of h/tron/kernels/dotter.hpp (4 zmm loads of K, 4 vdpbf16ps against the 4 preloaded Q registers, one add, one horizontal reduce).
- live mask = the 64-bit mask of the tokens of a page that a query may see (one bit per token).
- busy cycles = TSC (time-stamp counter, 2.70 GHz on delphi-3bda) cycles the attention workers spent inside attention work, summed over the 26 active workers, from the TRON_ATTN_STATS=1 exit report.
- prefill phase = the exit report's "prompt_or_mixed" forwards (64 per run). decode phase = its "decode_like" forwards (256 per run).
- est. = estimate, not a measurement.

## 1. What the campaign measured (delphi-3bda, 4 repetitions per arm)

Source: /home/jhan/workspace/intel-AMX/exec/results/pr5047-20261020/exit-reports.txt, parsed by ksroot/parse_exit_reports.py (output in ksroot/exit-report-summary.txt).

| phase | quantity | base (kill switch) | head (kill switch) | delta |
|---|---|---|---|---|
| prefill | forward wall | 78.63 s | 80.88 s | +2.247 s (+2.9 %) |
| prefill | worker-0 attention wall | 75.22 s | 77.43 s | +2.216 s |
| prefill | busy cycles, 26 workers | 5187.6 G | 5354.9 G | +167.3 G (+3.22 %) |
| prefill | busy per AVX K token | 75.5 TSC cycles | 77.9 | +2.43 TSC cycles (0.90 ns) |
| prefill | busy per visit | 4730 TSC cycles (1.75 us) | 4883 | +152.5 TSC cycles (56 ns) |
| decode | forward wall | 11.80 s | 11.77 s | -0.037 s |
| decode | busy cycles, 26 workers | 787.0 G | 784.8 G | -2.2 G (-0.28 %) |
| decode | busy per AVX K token | 180.4 TSC cycles | 179.9 | -0.50 TSC cycles |
| decode | busy per visit | 11426 TSC cycles (4.23 us) | 11394 | -32 TSC cycles |

Three facts follow from this table.

- The whole prefill delta is inside the attention workers. The forward wall delta (+2.247 s) equals the campaign's prefill delta, and the worker-0 attention wall delta (+2.216 s) is 99 % of it.
- The same visit costs 2.4 times more in decode than in prefill (11426 vs 4730 TSC cycles) with the same work per visit (63 K tokens scored, 4 heads). The difference, about 6700 TSC cycles per visit or 105 TSC cycles per K token (est.), is time spent waiting for K and V rows that are not in cache.
- The head adds 2.43 TSC cycles per K token in prefill and nothing in decode. If the prefill per-token cost applied in decode, decode busy cycles would rise by 2.43 x 4.36e9 = 10.6 G (+1.3 %), which is 4 standard deviations (sd 0.8 to 1.5 G) above what was seen (-2.2 G).

## 2. Visit arithmetic from the cell (computed, then checked against the exit report)

Cell: 8 users, prompt 8192 tokens, 256 generated tokens, llama-3.1-8b (32 layers, 8 KV heads, 4 query heads per KV head, head size 128), 64-token pages, causal mask, CPU attention.

Prefill per user, per layer, per KV head:

- pages = 8192 / 64 = 128.
- visits = sum over pages p of 64 queries x (p + 1) pages seen = 64 x 128 x 129 / 2 = 528,384.
- K tokens scored = sum over queries q of (q + 1) = 8192 x 8193 / 2 = 33,558,528.

Over 8 users x 32 layers x 8 KV heads (2048 combinations):

- visits = 1.082e9 computed. Measured 1.097e9 (1.069e9 ready + 0.028e9 pending). The 1.4 % surplus is the pending pass over each user's open page, see item 8 of the attention worker lane facts.
- K tokens = 68,727,865,344 computed. Measured 68,727,863,552 (difference 1792 tokens, 0.000003 %).

Decode per step: each user's one query visits all its pages: 8 users x (128 + t/64) pages x 8 KV heads x 32 layers = 262,144 to 270,336 visits per step, 64 K tokens each. Over 256 steps: 68.1e6 computed, 68.9e6 measured.

Bytes per visit: K 64 rows x 256 B = 16 KB, V the same, so 32 KB per visit. Per K token 256 B = 4 cache lines.

Time conversions used below (26 workers, TSC 2.70 GHz, workers busy 98 % of their wall):

- 1 TSC cycle per prefill K token = 6.87e10 / 26 / 2.7e9 = 0.979 s of prefill wall.
- 1 TSC cycle per prefill visit = 1.097e9 / 26 / 2.7e9 = 0.0156 s of prefill wall.
- 1 TSC cycle per decode K token = 4.36e9 / 26 / 2.7e9 = 0.062 s of the 11.8 s decode (0.53 %).
- 1 TSC cycle = 1.39 core cycles at the 3.75 GHz busy clock measured for AVX arms on 2026-08-31 (est. for this run, not re-measured).

## 3. Where the K rows live in each phase

Prefill. One forward holds 1024 token jobs: 8 users x the 128-token prompt chunk (TRON_PER_USER_PROMPT_CHUNK_LIMIT defaults to 128 [h/libtron.hpp:197-205]). chunk_evenly splits them into minibatches of at most 128 tokens, grouped by user [h/tron/models/model.hpp:208-281, llama max_minibatch_size 128 at h/tron/plugins/llama.hpp:184]. For one (minibatch, layer, KV head) the worker's section is that user's pages so far. apply_page_range loops pages outer and queries inner [h/tron/models/self_attention.hpp:1572-1664 at the head]. So one page's K (16 KB) and V (16 KB) are read by up to 128 queries back to back. The first query brings them from DRAM or L3. The next 127 queries hit L1 (48 KB L1D holds K 16 KB + V 16 KB + s_pages 1 KB + Q 1 KB + the accumulator). The loop is therefore bound by instruction throughput and the dependency chains of the dot products, not by memory. The measured 75.5 TSC cycles (about 105 core cycles, est.) per K token cover the dotter (79 instructions per token in the compiled loop, see section 5), the softmax pieces and the V accumulation.

Decode. One forward holds 8 token jobs (one per user) in one minibatch. Every page is visited by exactly one query per (layer, KV head), so K and V arrive from DRAM on every visit. The KV cache of this cell is 8 users x 8192 tokens x 32 layers x 8 heads x 2 x 256 B = 8.6 GB, 20 times the 432 MB L3 of the socket. Per step the workers stream 269k visits x 32 KB = 8.8 GB in 46 ms, about 190 GB/s, or 7.3 GB/s per worker. The measured 180 TSC cycles per K token versus 75.5 in prefill say the loop waits about 105 TSC cycles per K token for memory (est.). The hardware prefetcher streams the page rows, so the extra instructions of the head execute while the next rows are in flight.

The query side is the same in both phases: Q is 4 heads x 256 B = 1 KB per visit, held in 16 zmm registers by the dotter array.

## 4. What changed in the loop between base and head

Base [tron-split-pr1 h/tron/models/self_attention.hpp:1900-1976, one pass]:

- build the 4 dotters (16 zmm loads of Q) once per visit,
- walk the page's tokens once: range-hint advance, visibility test, sliding-window test, then for each live token read the K row lazily (`if (!keys.valid())`) and write 4 scores.

Head [tron-pr5047 h/tron/models/self_attention.hpp:1888-1918 plus kv_cache.hpp:1973-2005 page::score_k, two passes]:

- walk the page's tokens once and set bits in a 64-bit live mask (`live |= uint64_t{1} << i`),
- call page::score_k (TRON(inline) = always_inline [h/common/attributes.hpp:78]): return if live == 0, build the 4 dotters, then loop over the mask bits (`countr_zero`, `remaining &= remaining - 1`) and write 4 scores per live token.

Everything else a visit does (s_pages fill with -inf, scale, max, exp, scaled_v, accumulator update) is unchanged. The kill-switch arms never reach the AMX gate: `amx_q_packed` is null when AMX is unavailable, so `is_dense_amx_page` and `try_score_k_amx` do not run [self_attention.hpp:1874-1884].

## 5. Compiled instruction counts and a loop-only microbenchmark

ksroot/bench/kloop.cpp copies the dotter and the two loop structures (mask walk identical in both arms, no range-hint changes, window never cuts). Compiled with clang 19.1.7 (the compiler of the 3bda builds) at -O3 for the Granite Rapids target, the loop bodies are (ksroot/bench/loops-scalar.txt):

| loop | instructions per K token | of which scalar / control |
|---|---|---|
| base one pass | 79 | 15 |
| head pass 1 (mask walk, unrolled 2 tokens per iteration) | 11.5 | 11.5 |
| head pass 2 (score_k over the mask bits) | 73 | 9 (tzcnt, mov, shl, blsr, jne, 4 vshufpd) |
| head total | 84.5 | +5.5 per K token vs base |

Both inlined loops load each K row once (4 zmm loads) and reuse it for the 4 heads. An out-of-line score_k (the variant with always_inline removed) instead folds 16 K loads into the vdpbf16ps instructions, because the compiler cannot prove that `float* scores` does not alias K.

Timing on claude-box (AMD Zen 5, 32 threads, load average 17 during the run, so indicative only, ksroot/bench/kloop-znver4.out and kloop-znver4-hot2.out):

| mode | base | head inline | head out-of-line |
|---|---|---|---|
| hot (same page every visit, K in L1) | 4.49 to 4.75 ns per K token | 5.00 to 5.53 | 5.04 to 5.56 |
| cold (next page every visit, 1.09 GB buffer, K from DRAM) | 13.5 to 16.4 | 12.9 to 16.2 | 10.8 to 18.5 |

Hot: head costs +0.3 to +0.8 ns per K token (+7 to +17 %) for the dot-product loop alone. Cold: no consistent difference, the spread between repetitions (+-20 %) is larger than any arm difference. This is the same shape as the 3bda asymmetry.

## 6. Candidate overheads, cost at the measured scale, and what settles each

Scale reminder: the measured prefill delta is 2.43 TSC cycles per AVX K token = 152 TSC cycles per visit = 2.25 s. A candidate explains the delta only if it costs about that much in prefill and nothing visible in decode (where 105 TSC cycles per K token of memory wait can hide instructions, est.).

H1. Extra instructions per K token from the two-pass structure. Mechanism: pass 1 adds shlx, cmovge, or per token. Pass 2 adds tzcnt, blsr, mov, shl, jne per token and loses the `keys.valid()` test. Net +5.5 instructions per K token (clang 19, Granite Rapids target, microbenchmark). Cost est.: 2 to 3.5 core cycles per K token = 1.4 to 2.5 TSC cycles = 1.4 to 2.5 s of prefill (est.). The Zen 5 hot microbenchmark gives +0.3 to +0.8 ns per token, which scales to 1.2 to 3.2 s at 3bda's clock (est.). Measured: 2.25 s. Decode: hidden, the extra instructions are independent of the K loads and execute during the DRAM wait. Prediction for decode if not hidden: +1.3 % busy. Measured: -0.28 %. Settles it: `perf stat -e instructions:u,cycles:u` on the attention worker threads during prefill for baseoff vs headoff (expected instructions +3.8e11 = +5.5 x 6.87e10, cycles +1.65e11 core-equivalent), or an objdump instruction count of the apply_page_range instantiation in runtron.b47b vs runtron.b47h.

H2. Extra K loads per K token (K reloaded for each of the 4 heads). Mechanism: if the compiler cannot prove that `scores` (float*) does not alias the K rows, each head's dot reloads 4 zmm from K, 16 loads per token instead of 4. The microbenchmark shows this happens only when score_k is out of line, and the inlined head keeps 4 loads. Cost est. if present: 12 extra L1 loads per token, 0 to 1.5 TSC cycles per token = 0 to 1.5 s (the Zen 5 out-of-line arm costs about the same as the inline arm, so the loads mostly hide behind the dot-product chain). Decode: hidden (L1 hits during a DRAM wait). Settles it: objdump of runtron.b47h, count `vdpbf16ps` with a memory operand inside the apply_page_range instantiation for the llama geometry (expected 0 if inlined, 16 per loop body if not).

H3. Per-visit setup differences (dotter array build, s_pages fill, kv_block address, k_view, pass-2 loop entry and exit). Mechanism: the head builds the dotters inside score_k after the live == 0 check and adds one loop prologue and epilogue per visit. The s_pages fill and the dotter build exist in both. Cost est.: 5 to 20 TSC cycles per visit = 0.08 to 0.3 s of prefill. It cannot reach the measured 152 TSC cycles per visit. Decode: a per-visit cost of that size would be 0.03 to 0.1 % of decode, below the noise. Settles it: the same objdump count, prologue and epilogue instructions outside the token loop. Or a run where tokens per visit change but visits do not (the shipped AMX-on cell has 36.8 AVX K tokens per AVX visit instead of 62.7, see section 7, but its noise is too large to decide).

H4. score_k not inlined (a call per visit, Q dotters rebuilt inside the callee, plus H2's reloads). Mechanism: TRON(inline) expands to always_inline on clang [h/common/attributes.hpp:78], so this is not expected. Cost est. if it happened: 20 to 40 TSC cycles per visit for the call and register traffic = 0.3 to 0.6 s, plus H2. Decode: hidden. Settles it: `nm -C /var/tmp/jhan/tron-b47h/gen/runtron.b47h | grep score_k` on 3bda (a symbol means an out-of-line copy exists. The campaign's build-symbols-b47h.txt lists only the AMX symbols, so it cannot answer this).

H5. Run-time AMX decline (is_dense_amx_page, the s_pages of apply_dense_amx_page, try_score_k_amx returning false). Mechanism: exists in the head for layouts without an AMX reader. Cost in this cell: 0. Under the kill switch `amx_q_packed` is null and the gate short-circuits before any of this runs, in base and head alike [self_attention.hpp:1874-1884]. Settles it: already settled by the code. The VNNI pair (basev/headv, TRON_K_VNNI=ON, AMX available) is where it can run, and that pair shows decode +1.51 % busy with prefill +0.10 % (see section 7), the opposite asymmetry, not part of this question.

H6. The K store path change (model.hpp set_k_row(expr) for row-major = `kv_block.k_at(i_page).set(row)`, base = `pg.k(slot, kv_head, j).set(kout)`). Mechanism: 16.8 M row stores per prefill (8192 tokens x 8 users x 32 layers x 8 heads). Cost: 0, the generated code is the same expression. Even 100 TSC cycles per store would be 0.06 s on one thread. Decode: 0. Settles it: objdump of the save_k instantiation in both binaries.

H7. The FPGA staging change (full.hpp k_head_fn always memcpy). Cost: 0 in this cell, USE_HW_ATTN=0 never stages K to the FPGA.

Ranking: H1 alone matches the measured size and the prefill-only shape. H2 and H4 would add to it only if the always_inline failed, which one nm call on 3bda decides. H3, H6 and H7 are too small or zero.

## 7. Cross-checks from the other cells of the campaign

- VNNI pair control (basev vs headv, TRON_K_VNNI=ON, 100 % software K tokens through k_vnni::qk_group). Both binaries already used the live-mask-then-score structure for VNNI slots, so the one-pass to two-pass change does not apply there. Prefill busy delta +0.10 % (+4.8 G of 4972 G, 0.07 TSC cycles per K token). This isolates the prefill cost to the row-major dotter path's new structure.
- Shipped cell (AMX on, 2.8 % of K tokens on the software path: 1.98e9 AVX K tokens in 53.8e6 AVX visits). Per-token model (2.43 TSC cycles x 1.98e9) predicts +0.068 s of prefill, per-visit model (152.5 x 53.8e6) predicts +0.117 s. Measured +0.137 s, inside the 0.150 s band, with base prefill sd 0.075 s. The two models differ by 0.05 s, less than one sd, so this cell cannot separate them.
- Prompt 1024, AMX on: prefill wall -0.001 s although worker busy cycles rose +2.8 % (+1.5 G). The attention workers' wall (1.7 s) is half of the 3.4 s prefill there, so they are not on the critical path and their extra cycles do not reach the wall clock.
- Decode of the VNNI pair: headv busy +1.51 % (+11.2 G, 162 TSC cycles per visit) with no prefill change. Insufficient data on the cause. Candidates are the per-call AMX region (begin_region/end_region and the Q packing now run for VNNI slots because the compile-time `!k_vnni::layout_on` gate was removed) and the run-time decline of H5. A perf stat of headv vs basev in decode would resolve it. Outside this question.

## 8. Files

- /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot/parse_exit_reports.py and exit-report-summary.txt: the per-arm, per-phase busy and visit arithmetic of section 1.
- /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot/bench/kloop.cpp, kloop-gnr.asm, loops-scalar.txt, kloop-znver4.out, kloop-znver4-hot2.out: the microbenchmark, its Granite Rapids disassembly and the Zen 5 timings of section 5.
- Code read (read-only): /home/jhan/workspace/ai-runs/tron-split-pr1 (base) and /home/jhan/workspace/ai-runs/tron-pr5047 (head), files h/tron/models/self_attention.hpp, h/tron/models/kv_cache.hpp, h/tron/models/model.hpp, h/tron/kernels/dotter.hpp, h/tron/simd/fp32.hpp, h/tron/simd/aligned.hpp, h/common/attributes.hpp, h/libtron.hpp, h/tron/plugins/llama.hpp.
