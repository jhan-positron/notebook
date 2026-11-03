# Root cause record: issue positron-ai/tron#5097, PR 5047 kill-switch prefill +2.9 %

Date: 2026-10-21. Campaign: pr5047-20261020 on delphi-3bda. Author: Claude (workflow step), read-only on both worktrees, no machine access.

## Short version

PR 5047 (head ade89a9d9c) splits the software K scoring loop of one KV page into two passes: a selection pass that builds a 64-bit live mask, and a scoring pass (`page::score_k`) that runs only after the mask is complete. In the base (a5697f86d3) the 20 to 23 scalar bookkeeping instructions per K token ran inside the same loop iteration as the 16 `vdpbf16ps` dot-product instructions and were hidden under them, and at the head they run as a loop of their own before any dot product can start, at est. 150 to 250 core cycles per 64-token page visit against the measured +152.5 TSC cycles (56.5 ns) per visit. The cost shows only in prefill because prefill reads K from L1 cache and is bound by the core, while decode waits est. 105 TSC cycles per K token on memory and hides the extra pass (decode busy -0.28 %).

## Words used here

- tron: the inference program under test. runtron: its command-line tool.
- base: commit a5697f86d3 (PR 4956 head), worktree /home/jhan/workspace/ai-runs/tron-split-pr1, binary runtron.b47b on delphi-3bda.
- head: commit ade89a9d9c (PR 5047 head), worktree /home/jhan/workspace/ai-runs/tron-pr5047, binary runtron.b47h. head = base + commit e17a12ff09 ("self_attention: Make token selection logic a bit more obvious", the token loop becomes a live mask plus a second pass) + commit ade89a9d9c ("kv_cache: hide K layout behind row and scoring operations", the second pass moves into `page::score_k`, `page::k` is removed).
- kill switch: the environment variable TRON_AMX_DISABLE=1. AMX (Intel tile-matrix instructions) is then unavailable at run time, and 100 % of K tokens take the software scoring path. "shipped" = the same binaries without the kill switch (AMX on).
- AVX: the AVX-512 vector instructions of the software scoring path. `vdpbf16ps`: the AVX-512 instruction that multiplies 32 bf16 pairs and accumulates into 16 floats.
- bf16: the 16-bit floating-point format of the K rows and queries.
- KV page: a 64-token block of the KV cache. K row: the 256-byte key vector of one token (128 bf16 values).
- visit: one call of `apply_page_tok` = one query token against one KV page for one KV head (4 query heads, kv_mul 4 = query heads per KV head). K token or selected token: one K row scored inside a visit (4 dot products).
- pass 1: the head's loop that walks the 64 tokens of a page and sets a bit in the live mask (a `uint64_t`, one bit per token) for every token the query may see. pass 2: `page::score_k`, the head's loop over the set bits that does the dot products.
- dotter: the helper in h/tron/kernels/dotter.hpp that holds one 128-value bf16 query head in four 512-bit registers (zmm) and computes one dot product with one K row.
- `relevant_k_tokens`: the `int` local of `apply_page_tok` that counts selected tokens. The compiler keeps it on the stack at both heads.
- TSC cycle: one tick of the time-stamp counter, 2.70 GHz on delphi-3bda. The attention path stats (TRON_ATTN_STATS=1) report busy time in TSC cycles. core cycle: one tick of the core clock, est. 3.75 GHz for AVX work on this machine (measured 2026-08-31, not re-measured in this campaign). 1 TSC cycle = est. 1.39 core cycles.
- busy cycles: TSC cycles the attention worker threads spent inside attention work, summed over the 26 active workers, from the exit report.
- ThinLTO: link-time re-optimization (`-flto=thin`), which the production build adds on top of -O3.
- ROB: reorder buffer, the window of instructions the core can hold in flight (512 entries on Granite Rapids, est.).
- sd: standard deviation over the 4 repetitions. band: the campaign's noise band for one cell.
- est.: an estimate, not a measurement.

## Measured facts

All numbers from the campaign pr5047-20261020 (4 repetitions per arm, llama-3.1-8b, tensor-parallel 2, 8 users per engine, prompt 8192 tokens, 256 generated, CPU attention, TRON_K_VNNI OFF in both binaries). Source: /home/jhan/workspace/intel-AMX/exec/results/pr5047-20261020/ (rt-results.txt, exit-reports.txt), parsed into ksroot/exit-report-summary.txt.

| cell | quantity | base | head | delta |
|---|---|---|---|---|
| kill switch, prefill | wall (campaign) | 78.793 s (sd 0.083) | 81.040 s (sd 0.057) | +2.247 s (+2.9 %), band 0.166 s, degradation |
| kill switch, prefill | forward wall (exit report) | 78.63 s | 80.88 s | +2.247 s |
| kill switch, prefill | worker-0 attention wall | 75.22 s | 77.43 s | +2.216 s (99 % of the delta) |
| kill switch, prefill | busy cycles, 26 workers | 5187.6 G TSC (sd 3.8) | 5354.9 G (sd 1.6) | +167.3 G (+3.22 %) |
| kill switch, prefill | busy per visit (1.097 G visits) | 4730 TSC cycles (1752 ns) | 4883 | +152.5 TSC cycles (56.5 ns) |
| kill switch, prefill | busy per K token (68.73 G tokens, 62.7 per visit) | 75.5 TSC cycles | 77.9 | +2.43 TSC cycles (0.90 ns) |
| kill switch, decode | TPS | 21.39 (sd 0.04) | 21.46 (sd 0.05) | +0.3 %, inside the band |
| kill switch, decode | busy cycles, 26 workers | 787.0 G TSC (sd 0.8) | 784.8 G (sd 1.5) | -2.2 G (-0.28 %) |
| kill switch, decode | busy per K token (4.36 G tokens) | 180.4 TSC cycles | 179.9 | -0.50 TSC cycles |
| shipped (AMX on), prefill | wall | 35.258 s | 35.396 s | +0.138 s, inside the 0.150 s band |
| shipped, prompt 1024, prefill | wall | 3.39 s | 3.39 s | -0.001 s |
| VNNI control pair (basev vs headv, K in VNNI layout, 100 % software path), prefill | busy cycles | 4972.3 G | 4977.1 G | +4.8 G (+0.10 %) |

Facts that follow from the table:

- The whole prefill delta sits inside the attention workers. The worker-0 attention wall delta (+2.216 s) is 99 % of the forward wall delta.
- The delta is a per-K-token cost. 2.43 TSC cycles x 68.73 G tokens / 26 workers / 2.70 GHz = 2.38 s, which matches the +2.247 s wall delta within 6 %.
- The same visit costs 2.4 times more in decode (11,426 TSC cycles) than in prefill (4730) with the same work per visit. The difference, est. 105 TSC cycles per K token, is memory wait: decode reads every K row from DRAM once per step (8.6 GB KV cache against a 432 MB L3), prefill reads each page's 16 KB K plane from L1 for up to 128 queries in a row (pages outer, queries inner in `apply_page_range`).
- If the prefill per-token cost applied in decode, decode busy would rise 2.43 x 4.36 G = +10.6 G TSC cycles (+1.3 %). The measurement is -2.2 G (sd 0.8 to 1.5 G), 4 sd below that. So decode hides the cost.
- With AMX on, 2.88 % of prefill K tokens (1.98 G of 68.73 G) take the software path. 2.88 % of 2.247 s = est. 0.065 s per token model, or est. 0.117 s by the per-visit model (53.8 M AVX visits x 152.5 TSC cycles). The measured +0.138 s is inside the band and of that order.
- The VNNI control pair already used the mask-then-score structure at both heads. Its prefill delta is +0.10 %. So the one-pass to two-pass change of the row-major path is the only prefill-path difference that moved.

## What changed on the hot path

The only run-time change on the kill-switch path is the K scoring loop of `apply_page_tok` (inlined into `apply_page_range`, h/tron/models/self_attention.hpp). `apply_page_range` itself, the s_pages -inf fill, the softmax epilogue, the PV loop and the dotter kernel are unchanged (git diff a5697f86d3..ade89a9d9c has no hunk in dotter.hpp, and the PV loops are byte-identical in the compiled objects).

Base, one loop [tron-split-pr1 h/tron/models/self_attention.hpp:1935-1961]: for each token of the page, do the range-hint advance, the visibility test and the sliding-window test, then `relevant_k_tokens++`, then `if (!keys.valid()) keys = page.k(...)`, then 4 dot products stored into `s_pages[offset][i]`.

Head, two loops [tron-pr5047 h/tron/models/self_attention.hpp:1896-1917, h/tron/models/kv_cache.hpp:1976-2003]: pass 1 does the same three tests, then `relevant_k_tokens++` and `live |= uint64_t{1} << i`. After the loop, `page.score_k(slot, kv_head, q, live, &s_pages[0][0], 64)` runs pass 2: `for (remaining = live; remaining != 0; remaining &= remaining - 1) { i = countr_zero(remaining); 4 dot products }`. `score_k` is `TRON(inline)` = `inline __attribute__((always_inline))` [h/common/attributes.hpp:78].

## Machine code (local compile of the production translation unit)

Method: gen/src/tron/model_llama_3p1_8b.cpp (the six-line file CMake generates for the llama model) was reproduced at ksroot/tu/ and compiled at both heads with clang 19.1.7 (the campaign's compiler version) and the production flags (-O3, AVX-512 and AMX -m flags, -DTRON_AMX_DISPATCH, TRON_K_VNNI off) without -flto=thin. The tp2 `apply_page_range` instantiation was disassembled into ksroot/obj/{base,head}/apply_page_range.short.dis. A second compile with -flto=thin plus a ThinLTO link through ld.lld --lto-O3 is at ksroot/h7/lto/{base,head}.apr.lto.dis.

Per-token instruction counts along the steady path (a visible, in-window token, no range advance), recounted by address range with ksroot/h1-verify/recount.py:

| item | base | head |
|---|---|---|
| instructions per K token | 94 in one loop | 97 = 23 (pass 1) + 74 (pass 2) |
| `vdpbf16ps` per K token | 16, each with a memory operand (the K row is re-read from L1 for each of the 4 heads) | 16, register operands (the K row is loaded once into zmm16 to zmm19 by 4 `vmovaps`) |
| load micro-operations per K token | 20 | 9 |
| stores per K token | 5 (4 `vmovss` scores + the counter) | 5 (4 `vmovss` scores + the counter) |
| counter `relevant_k_tokens` | `mov 0x78(%rsp),%rsi; inc %esi; mov %rsi,0x78(%rsp)` at 0x1a4e, inside the vector loop | `mov 0x60(%rsp),%rcx; inc %ecx; mov %rcx,0x60(%rsp)` at 0x178e, inside pass 1 |
| taken branches per K token | 1 (`jmp 15e9` at 0x1a9e) | 3 (pass 1: `jmp 1770` at 0x157c and `jmp 155a` at 0x179e; pass 2: `jne 1a80` at 0x1c50) |
| calls inside the loops | 0 | 0 |
| whole function | 2166 instructions, 32 `vdpbf16ps` | 2151 instructions, 32 `vdpbf16ps` |
| per-visit setup (s_pages fill, Q load, K block lookup, loop entry and exit) | 105 instructions | 102 instructions |

Head pass 1, steady path, last 12 instructions (ksroot/obj/head/apply_page_range.short.dis):

```
1770: mov    0xb0(%rsp),%rcx     ; sliding-window test
1778: add    %r9d,%ecx
177b: mov    0x28(%rsp),%edx
177f: sub    %ecx,%edx
1781: mov    $0x1,%r15b
1784: cmp    0x6c(%rsp),%edx
1788: jge    155a
178e: mov    0x60(%rsp),%rcx     ; relevant_k_tokens++ through the stack
1793: inc    %ecx
1795: mov    %rcx,0x60(%rsp)
179a: bts    %r9,%rdi            ; live |= 1 << i
179e: jmp    155a
```

Head pass 2, loop head and tail:

```
1a80: tzcnt  %rdi,%rcx           ; i = lowest set bit
1a85: mov    %ecx,%edx
1a87: shl    $0x8,%edx           ; byte offset = i * 256
1a8a: vmovaps (%rax,%rdx,1),%zmm19   ; K row loaded once
...   16 vdpbf16ps, 4 reductions, 4 vmovss stores (same as the base)
1c49: lea    -0x1(%rdi),%rcx     ; live &= live - 1
1c4d: and    %rcx,%rdi
1c50: jne    1a80
```

Base, the same bookkeeping inside the vector loop:

```
18c5: cmp    $0x40,%r8           ; bounds check i < 64
18c9: jae    2d5f
18cf: mov    %r8,%r9
18d2: shl    $0x8,%r9
18d6: vxorps %xmm16,%xmm16,%xmm16
18dc: vdpbf16ps (%r11,%r9,1),%zmm0,%zmm16   ; K row read from memory, 16 times per token
...
1a4e: mov    0x78(%rsp),%rsi     ; relevant_k_tokens++ through the stack, under the vector work
1a53: inc    %esi
1a55: mov    %rsi,0x78(%rsp)
...
1a9e: jmp    15e9
```

ThinLTO check (ksroot/h7/lto, both links finished 2026-10-21 19:32 UTC): the structure survives the production link step. Base-ThinLTO: 2644 instructions, 16 memory-operand `vdpbf16ps`, no `tzcnt`, no `bts`, the counter increment `mov 0xb0(%rsp),%rcx; inc %ecx; mov %rcx,0xb0(%rsp)` at offset 0x1c7b between the `vdpbf16ps` of head 3 and its reduction. Head-ThinLTO: 2660 instructions, 16 register-operand `vdpbf16ps`, one `tzcnt` loop (0x1c80 to 0x1e50), one `bts` at 0x1af3 preceded by the same counter triple at 0x1ae7 to 0x1aee in pass 1. So the local non-LTO listing is representative of what the campaign binaries run, up to register names.

## Ranked causes

### 1. The selection pass runs alone before any dot product (the pass split) - primary cause

Mechanism. The base executed the 20 to 23 scalar bookkeeping instructions per K token (range check, visibility test, sliding-window test, counter increment, bounds check) in the same loop iteration as the 16 `vdpbf16ps` and 4 horizontal reductions (52 vector micro-operations, est. 26 core cycles per token on the two 512-bit vector ports). The out-of-order core overlapped the scalar work with the vector work, so it cost about nothing. The head runs the same bookkeeping as pass 1, a loop of 23 instructions and 2 taken branches per token with no vector work to hide under. Pass 1 is bound by issue width and taken branches at est. 4 to 5 core cycles per token. Pass 2 cannot start before pass 1 has produced the complete mask (`tzcnt %rdi` needs the final `live`). The ROB lets est. 22 tokens of pass 1 (512 entries / 23 instructions) overlap with the end of the previous visit or the start of pass 2, so the exposed cost is est. (63 - 22) x 4 to 5 = 160 to 250 core cycles per dense visit.

Evidence.
- The disassembly shows the split at both the non-LTO and the ThinLTO compile (counts above). Vector work is identical (16 `vdpbf16ps` per token, same reductions).
- Scale: measured +152.5 TSC cycles per visit = est. 212 core cycles at 3.75 GHz, inside the est. 160 to 250 range.
- Shape: the cost is per K token (2.43 TSC cycles x 68.73 G = 2.38 s against 2.247 s measured), not per visit (a per-visit cost of 152.5 TSC cycles would raise decode busy +1.34 %, and decode measured -0.28 %).
- The VNNI control pair, which had the two-pass structure at both heads, moved +0.10 % in prefill. The row-major path's structure change is the only moving part.
- Microbenchmark (ksroot/h6/kloop_ws.cpp, the two loop shapes with the production dotter, clang 19.1.7, pinned to one core of claude-box, AMD Zen 5, load average 17, indicative only): with K in L1 the head loop costs +24 to +38 ns per 64-token visit, the same size for every working set from 16 KB to 1 GB in the prefill access pattern (128 visits per page). The loss does not depend on where K lives, which is what a serial scalar pass predicts and what an exposed cache miss does not.
- Decode: pass 1 adds est. 4 to 5 core cycles per token, and decode waits est. 105 TSC cycles per token on memory. The extra pass fits inside the wait, consistent with -0.28 % busy.

Confidence: medium. No perf counters were taken on delphi-3bda, the core clock during the campaign is an estimate, and the campaign binaries themselves were not disassembled (the ThinLTO re-link here used the same compiler version and flags, not the same build tree).

### 2. The `relevant_k_tokens` increment through the stack sets part of the pace of pass 1 - sub-mechanism of cause 1

Mechanism. The counter lives on the stack at both heads. In pass 1 the `mov 0x60(%rsp); inc; mov 0x60(%rsp)` triple is a loop-carried chain through store-to-load forwarding, est. 5 core cycles per token on Intel cores (Insufficient data on memory renaming for Granite Rapids). In the base the same chain sat under 26 cycles of vector work per token and cost nothing. In pass 1 it is one of three per-token bounds of similar size (issue width est. 4 cycles, two taken branches est. 2 to 4 cycles, the chain est. 5 cycles). Nothing in pass 1 reads the counter, so the chain gates retirement, not issue, and adds est. 1 to 2 cycles on top of the issue bound, not the full 5.

Evidence. The kloop microbenchmark keeps the counter in a register (`add ecx,r12d` in ksroot/bench/loops-scalar.txt) and still measures the head at +0.3 to +0.8 ns per token hot. So the pass split without any memory chain already produces a delta of the measured order. The chain is a contributor, not the cause. Settled by fix candidate F1 below (one-line experiment).

### 3. Three more instructions per K token in the two loops - minor contributor

Mechanism. The head's per-token path is 97 instructions against the base's 94 (+3.2 %): `tzcnt`, `mov`, `shl`, `lea`, `and`, `jne` in pass 2 and `bts` in pass 1, minus the base's bounds check pair (`cmp $0x40; jae`), index shift and `keys.valid()` test. The pass-2 loop issues 52 vector micro-operations per token on two ports (est. 26 cycles) against 74 instructions over a 6-wide front end (est. 12 cycles), so it has issue slack. Three extra scalar instructions there cost est. 0 to 1 core cycle per token, and the 11 fewer load micro-operations per token give some of it back. Bound: est. 0 to 30 % of the measured delta.

### 4. One extra loop boundary per visit - negligible

Mechanism. The head has two loop exits per visit (`jae` at 0x1563 after pass 1, `jne` at 0x1c50 after pass 2) where the base has one. Per visit the head's setup code is 3 instructions shorter (102 against 105, counted with ksroot/h3/rng.py). At most one extra branch mispredict per visit, est. 20 core cycles = 14 TSC cycles per visit = est. 0.22 s over 1.097 G visits. Bound: est. 10 % of the measured delta.

## Refuted hypotheses (one line each, so nobody re-opens them)

- "Second-pass loop overhead (tzcnt/blsr/branch) adds instructions per selected token": the count is +3 instructions per token (94 to 97), not +6, inside a loop with issue slack, est. 0 to 30 % of the delta, so it is a minor contributor (cause 3), not the cause.
- "Production-binary code generation differs from the local compile (score_k not inlined, run-time stride, Q spills)": 0 `score_k` or `dotter` symbols in all objects, 0 calls and 0 `imul` inside the scoring loops, score stores at constant stack offsets (stride folded to 256 bytes), Q in zmm0 to zmm15 across the page with 0 stack moves, and the ThinLTO re-link shows the same loops.
- "save_k's extra TRON_ASSERT_LT per stored K row": the base's `view::operator[]` already asserted `i < 64`, the compiled `save_k_impl` has exactly one `cmp $0x3f; ja` per token at both heads (base 650 instructions, head 627), and 16.8 M rows per prefill at even 100 cycles each is under 0.7 s on one thread, outside the attention workers where 99 % of the delta sits.
- "The head reads the K row more often": the opposite holds, the base reads the row 16 times per token as `vdpbf16ps` memory operands, the head 4 times (`vmovaps` into zmm16 to zmm19).
- "score_k or the dotter is not inlined at the head": `score_k` is always_inline, no such symbols exist in any object (non-LTO and ThinLTO), and 0 calls sit inside the loops; an un-inlined call per token would cost est. 60 s, far above 2.2 s.
- "Q (the dotter array) or the K row spills to the stack": 0 zmm stores to and 0 zmm loads from the stack inside either scoring loop, register demand is 22 of 32 zmm.
- "Per-visit stack traffic (s_pages fill, token counter) grew": 16 zmm stores of -inf per visit at both heads, 9 stack accesses per token at both heads (base 3 loads + 6 stores, head 4 loads + 5 stores).
- "Pass 2 exposes K cache-miss latency the one-pass loop overlapped": prefill reads each page's K from L1 for 127 of every 128 visits (pages outer, queries inner, minibatch 128), so a first-visit miss of even 300 ns is 2.3 ns per visit against the measured 56 ns, and the microbenchmark reproduces the loss with K in L1 (+24 to +38 ns per visit, flat from 16 KB to 1 GB working set).
- "ThinLTO on 3bda changes the loop": the local ThinLTO link of the same translation unit (ksroot/h7/lto) keeps the base's one-pass loop with the memory-operand `vdpbf16ps` and the head's pass-1 `bts` loop plus the pass-2 `tzcnt` loop with register `vdpbf16ps`, and the build rules are identical at both heads (PR 5047 touches no build file).
- "Extra K loads per token (K row reloaded for each of the 4 heads)": the head loads K once per token and the base 16 times. The mechanism exists only in the base.
- "Per-visit setup differences (dotter build, s_pages fill, kv_block lookup, loop entry and exit)": 105 instructions at the base against 102 at the head per non-empty visit, all 1.097 G prefill visits are non-empty, bound est. 0.1 to 0.3 s (cause 4).
- "Run-time AMX decline (is_dense_amx_page, try_score_k_amx returning false)": under the kill switch `amx_q_packed` is nullptr and the `&&` chain stops at its first operand at both heads, and in the option-off build `try_score_k_amx`'s decline is an `if constexpr` that folds away; 0 AMX visits in the exit reports of both arms.
- "K store path change (set_k_row(expr)) and FPGA staging change (full.hpp)": `set_k_row` compiles to the same view lookup and bf16 store as the base's `page::k(...).set(...)` (head `save_k_impl` is 23 instructions shorter), and the full.hpp lambda runs only with FPGA attention, which USE_HW_ATTN=0 disables in this cell.

## Fix candidates (code terms)

F1. Register counter (diagnostic, one line). In `apply_page_tok` at the head [tron-pr5047 h/tron/models/self_attention.hpp:1914-1915], delete `relevant_k_tokens++;` from pass 1 and set `relevant_k_tokens = std::popcount(live);` after the loop. Removes the store-to-load chain of cause 2. Expected recovery: est. 20 to 40 % of the 2.247 s if the chain contributes est. 1 to 2 of the 4 to 5 cycles per token, 0 % if pass 1 is purely issue-bound. This is the experiment that settles cause 2, and it is a harmless change on its own.

F2. Arithmetic live mask for dense pages (keeps the two-pass design, removes pass 1's per-token cost). In pass 1 of `apply_page_tok`, before the token loop, test the common case: the page lies inside one visible range (`page.at_offset(begin) >= range_hint->tok_lo && page.at_offset(end - 1) < range_hint->tok_hi` after one `find_range`), the query may see it, and the sliding window does not cut it (`(int)q_position - (int)(k_position + begin) < sliding_window_size`). Then `live = (end - begin == 64) ? ~uint64_t{0} : ((uint64_t{1} << (end - begin)) - 1) << begin;` and `relevant_k_tokens = std::popcount(live);`, and skip the loop. Otherwise fall back to the existing loop. Shape: a `page::dense_live_mask(begin, end)` helper or an inline block of est. 10 scalar instructions per visit in place of est. 1440 (23 x 62.7). In prefill at prompt 8192 almost every visit is dense (the only partial page is the query's own page), so this removes est. 90 % or more of the pass-1 work. The AMX path already has the same idea (`is_dense_amx_page`), so the fast path can share its test. Expected recovery: most of the 2.247 s (est. 80 to 100 %), with pass 2 kept as PR 5047 wrote it.

F3. Fuse the passes for the row-major layout (returns to the base's codegen while keeping the K layout hidden in the page). Replace `page::score_k(slot, kv_head, q, live, scores, stride)` on the row-major branch by a per-visit scorer object: `auto scorer = page.template k_scorer<geometry>(slot, kv_head, q);` built once per visit (it holds the `kv_block` K view and the 4 dotters), with `scorer.score(i, scores, stride)` called inside the selection loop for each selected token, under `if constexpr (!k_vnni::layout_on<dims>)`. The VNNI branch keeps the mask and `k_vnni::qk_group`. Shape: a small struct in kv_cache.hpp (two members, one `TRON(inline)` method), and the selection loop in self_attention.hpp gets back one line per selected token. Expected recovery: 100 % of the delta (the compiled loop becomes the base's loop, with the K row possibly still loaded once if the compiler keeps the view in registers). Cost: the selection loop again contains layout-specific code, which is what PR 5047 set out to remove, so this is the fallback if F2 is judged too special-cased.

Not recommended: software prefetch of the K block before pass 1. It addresses an exposed cache miss, which the evidence rules out for prefill (K is in L1), and decode shows no delta to recover.

## delphi-3bda profile plan (one repetition each, kill-switch binaries, prefill of the prompt-8192 cell)

Preconditions: the usual 3bda rules (lease, our half, campaign guard) as in exec/pr5047-20261020/campaign.sh. The binaries are /var/tmp/jhan/tron-b47b/gen/runtron.b47b (base) and /var/tmp/jhan/tron-b47h/gen/runtron.b47h (head). Run from each binary's worktree (`cd /var/tmp/jhan/tron-b47b` or `tron-b47h`). `perf` must be allowed for user jhan (`sysctl kernel.perf_event_paranoid` at most 1, or run under sudo if the machine rules allow). Prefill of this cell lasts about 79 s (base) to 81 s (head), so a 50 s sampling window started 10 s into prefill stays inside it.

Launch (same command as the campaign, arm `<arm>off`, `<bin>` = runtron.b47b or runtron.b47h):

```
env -u SYSTEM_CONFIG USE_HW_ATTN=0 TRON_ATTN_STATS=1 TRON_AMX_DISABLE=1 TRON_LOG_LEVEL=debug SPDLOG_LEVEL=debug \
  timeout -k 60 2400 /var/tmp/jhan/tron-b47h/gen/<bin> stream-generate-text -m llama-3.1-8b-instruct-good-tp2 \
  --instance 2,4 --devices 90:00.0,93:00.0 --app-cores 223-224,96-101,120-125,225-226,102-107,126-131 \
  --dev-cores 75,76 --numa 1 --nr_hugepages 128 --hugepage_file /dev/hugepages/amx-prof-<arm> -o \
  --prompt-length 8192 -l 256 -u 8 --dont-stop > /var/tmp/jhan/prof-<arm>.log 2>&1 &
PID=$!
```

Find the attention worker threads (so the counts cover only them): `ls /proc/$PID/task | while read t; do echo "$t $(cat /proc/$PID/task/$t/comm)"; done`. Insufficient data on the worker thread names; pick the 26 threads whose CPU time grows during prefill (`top -H -p $PID`), or use `--per-thread` and sum the attention threads afterwards.

Step A, counters, one 50 s window per binary, started 10 s after the log shows the prompt being processed (the first "prompt" progress line after "App CPU list"):

```
perf stat -p $PID --per-thread -o /var/tmp/jhan/prof-<arm>.stat \
  -e cycles:u,instructions:u,ref-cycles:u \
  -e cpu/event=0x03,umask=0x82,name=ld_blocks_store_forward/u \
  -e cpu/event=0xc5,umask=0x00,name=br_misp_retired_all/u \
  -e cpu/event=0xc4,umask=0x00,name=br_inst_retired_all/u \
  -e cpu/event=0xb2,umask=0x01,name=uops_port_0/u,cpu/event=0xb2,umask=0x02,name=uops_port_1/u \
  -e cpu/event=0xb2,umask=0x20,name=uops_port_5_11/u,cpu/event=0xb2,umask=0x04,name=uops_port_2_3_10/u \
  -e cpu/event=0xd1,umask=0x08,name=mem_load_retired_l1_miss/u,cpu/event=0xd1,umask=0x10,name=mem_load_retired_l2_miss/u \
  -- sleep 50
```

(The raw event codes are the Sapphire Rapids / Granite Rapids codes for LD_BLOCKS.STORE_FORWARD, BR_MISP_RETIRED.ALL_BRANCHES, BR_INST_RETIRED.ALL_BRANCHES, UOPS_DISPATCHED.PORT_x and MEM_LOAD_RETIRED.Lx_MISS. If `perf list` on 3bda shows the symbolic names, use them instead. A second window with `perf stat -M TopdownL1 -p $PID -- sleep 50` gives the front-end-bound, back-end-bound, bad-speculation and retiring shares, if the installed perf supports the metric group.)

Step B, samples, one 40 s window per binary, in the same prefill (start it right after step A, when prefill still has about 15 s left) or in a second repetition:

```
perf record -e cycles:u -c 500000 -p $PID -o /var/tmp/jhan/prof-<arm>.data -- sleep 40
perf report -i /var/tmp/jhan/prof-<arm>.data --stdio --sort sym | head -30
perf annotate -i /var/tmp/jhan/prof-<arm>.data --stdio --no-source \
  --symbol='<the tp2 apply_page_range symbol, from perf report>' > /var/tmp/jhan/prof-<arm>.annot
```

In the head's annotation, the pass-1 loop is the block that ends with `bts` + `jmp`, the pass-2 loop is the block from `tzcnt` to `jne`. In the base's annotation, the single loop is the block from `cmp $0x40` through the 16 `vdpbf16ps` to the `jmp` back edge.

Numbers that confirm or reject each cause (all per 50 s window on the attention threads, head against base):

| cause | confirms | rejects |
|---|---|---|
| 1. pass split (serial pass 1) | cycles +3.0 to +3.5 % (busy +3.22 % measured). instructions +2.5 to +3.5 % (+3 per token x 68.7 G = +206 G over est. 6.5 T loop instructions). IPC head / base = 0.97 to 1.00. perf annotate: the pass-1 loop holds >= 3 % of the head's `apply_page_range` samples (152 of 4883 TSC cycles per visit = 3.1 %) and the pass-2 loop holds about the base loop's share. uops_port_0 + uops_port_5_11 within 1 % of the base (vector work unchanged). br_inst_retired +2 per token (+137 G, 3 taken branches instead of 1) | the pass-1 loop holds < 1 % of the samples while cycles still rise 3 % (then the cost is in pass 2 or outside the loop). Or cycles rise < 1 % (then the regression is not in the attention workers' instruction stream, contradicting the busy-cycle delta) |
| 2. counter chain | fix F1 (popcount) applied to the head cuts the prefill delta by >= 0.5 s on a re-run of the cell. ld_blocks_store_forward is NOT a discriminator (it counts forwards that fail, and an 8-byte store followed by an 8-byte load forwards without a block), so expect it flat at both heads. A rise > 1 G at the head would mean an unexpected forward failure | fix F1 leaves the delta at +2.2 s within the 0.166 s band |
| 3. +3 instructions per token | instructions +3.2 % and the pass-2 loop (not pass 1) holds the extra samples in the annotation, with cycles tracking instructions (IPC unchanged) | instructions +3.2 % but the extra samples sit in pass 1 (then cause 1) |
| 4. loop boundary per visit | br_misp_retired_all delta between +0.5 G and +1.1 G (up to one per visit, 1.097 G visits) and no more | br_misp_retired_all delta > 3 G (then mispredicts matter more than estimated, and the annotation should show it at the `jae` after pass 1 or the `jne` after pass 2). A delta < 0.3 G with cycles +3 % confirms it is negligible |

Cache-miss control (closes the refuted H6 on the production binary): mem_load_retired_l1_miss and l2_miss per instruction within 5 % of the base at the head. A rise > 20 % would re-open the exposed-miss hypothesis.

## Insufficient data

- Core clock of the attention workers during the campaign: not measured. The 3.75 GHz busy clock is the 2026-08-31 figure. `ref-cycles` against `cycles` in step A gives the real ratio.
- Thread names of the attention workers for `--per-thread` filtering: not in this task's inputs.
- Whether the campaign binaries were linked with ThinLTO at all (the native preset adds it only if `check_ipo_supported` passes; no configure log was saved). The local ThinLTO link shows the loop structure is the same either way.
- Store-to-load forwarding latency and memory renaming behaviour on Granite Rapids: not measured. Fix F1 settles whether it matters.

## Files

- This record: /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot/root-cause.md
- Evidence read: ksroot/source-diff.md, ksroot/objdump-compare.md, ksroot/prefill-vs-decode.md, ksroot/exit-report-summary.txt, ksroot/h3/h3-verdict.md, ksroot/h6/kloop_ws-znver5-*.out, ksroot/bench/loops-scalar.txt.
- Disassembly: ksroot/obj/{base,head}/apply_page_range.short.dis (non-LTO), ksroot/h7/lto/{base,head}.apr.lto.dis (ThinLTO, extracted with ksroot/h7/lto/aprbody.py, written in this step), ksroot/h7/lto/{base,head}.lto.compare.txt (this step: the head link was re-run because the first one did not finish).
- Code read (read-only): /home/jhan/workspace/ai-runs/tron-pr5047 and /home/jhan/workspace/ai-runs/tron-split-pr1, h/tron/models/self_attention.hpp and h/tron/models/kv_cache.hpp at the lines cited. Also /home/jhan/workspace/intel-AMX/exec/pr5047-20261020/campaign.sh (run command, placement, arm environments) and /home/jhan/workspace/intel-AMX/exec/results/pr5047-20261020/build-b47h.txt (compiler and preset).
