## Root cause from the code and the machine code (no profile yet)

### Short version

The cost comes from the split of the software K scoring loop into two passes. The base scores a K row in the same loop iteration that selects it, so the scalar bookkeeping of a token (range check, visibility test, sliding-window test, counter) runs under the 16 `vdpbf16ps` instructions of its 4 dot products and costs about nothing. The head runs that bookkeeping as a selection pass of its own that must finish the whole 64-bit live mask before `page::score_k` can start, and that pass is serial scalar work of about 23 instructions and 2 taken branches per token with nothing to hide under. The cost shows in prefill and not in decode for one reason: prefill reads each page's K rows from the L1 cache across the many query tokens of a minibatch and is bound by the core, while decode streams K from memory and the extra pass fits inside the memory wait.

### What the campaign's own counters say

The attention path stats (TRON_ATTN_STATS=1, in both arms' exit reports) count visits (one query token against one 64-token page for one KV head), K tokens scored, and busy cycles of the 26 attention workers in TSC cycles (2.70 GHz).

| Phase | Quantity | base | head | delta |
|---|---|---|---|---|
| prefill | busy cycles, 26 workers | 5,187.6 G (sd 3.8) | 5,354.9 G (sd 1.6) | +167.3 G (+3.22 %) |
| prefill | busy per visit (1.097 G visits) | 4,730 | 4,883 | +152.5 TSC cycles (56.5 ns) |
| prefill | busy per K token (68.73 G tokens) | 75.5 | 77.9 | +2.43 TSC cycles |
| decode | busy cycles, 26 workers | 787.0 G (sd 0.8) | 784.8 G (sd 1.5) | -2.2 G (-0.28 %) |
| decode | busy per K token (4.36 G tokens) | 180.4 | 179.9 | -0.50 TSC cycles |

What the table says:

- The whole prefill delta is inside the attention workers. 2.43 TSC cycles x 68.73 G K tokens / 26 workers / 2.70 GHz = 2.38 s, against the +2.247 s wall delta (within 6 %).
- The same visit costs 2.4 times more in decode than in prefill with the same work per visit. The difference (est. 105 TSC cycles per K token) is memory wait: decode reads every K row from DRAM once per step, prefill reads each page's 16 KB K plane from L1 for up to 128 queries in a row.
- A per-token cost of 2.43 TSC cycles would raise decode busy by +1.3 % if decode did not hide it. Decode measures -0.28 %, 4 standard deviations below that.
- The option-on pair (K in the VNNI layout, 100 % software path) already had the mask-then-score structure at both heads. Its prefill busy delta is +0.10 %. The one-pass to two-pass change of the row-major path is the only part that moved.

### What the machine code shows

The generated llama translation unit was compiled at both heads with clang 19.1.7 and the production flags (-O3, AVX-512 and AMX flags, TRON_AMX_DISPATCH on, TRON_K_VNNI off), with and without ThinLTO, and the `apply_page_range` instantiation was disassembled. Per K token on the steady path (visible, in-window token):

| Item | base | head |
|---|---|---|
| instructions per K token | 94, one loop | 97 = 23 (selection pass) + 74 (scoring pass) |
| `vdpbf16ps` per K token | 16, memory operands (the K row is re-read for each of the 4 heads) | 16, register operands (the K row is loaded once) |
| load micro-operations per K token | 20 | 9 |
| taken branches per K token | 1 | 3 |
| calls inside the loops | 0 | 0 |
| `score_k` or `dotter` symbols | none (inlined) | none (inlined) |

So the head's loops are not worse by instruction count or by loads. They are worse by shape: the selection pass (ending in `bts` + `jmp`) runs alone, and the scoring pass (`tzcnt` to `jne`) cannot start before the mask is complete. Estimate: 4 to 5 core cycles per token of exposed scalar work, 160 to 250 core cycles per dense visit (est.), against the measured +152.5 TSC cycles = est. 212 core cycles per visit.

A microbenchmark of the two loop shapes with the production `dotter` (clang 19.1.7, one pinned core of an AMD Zen 5 development host, indicative only) measures the head loop at +24 to +38 ns per 64-token visit with K in L1, and the same delta for every working set from 16 KB to 1 GB in the prefill access pattern. A serial scalar pass predicts that. An exposed cache miss does not.

### Ranked causes

1. **The selection pass runs alone before any dot product** (primary). Evidence above. Confidence medium: no counters were taken on 3bda yet, and the campaign binaries themselves were not disassembled (same compiler version and flags, not the same build tree).
2. **The `relevant_k_tokens` increment goes through the stack** (`mov 0x60(%rsp); inc; mov 0x60(%rsp)` inside the selection pass, at both heads, a loop-carried store-to-load chain of est. 5 core cycles). The base hid it under the vector work. Contributor, not the cause: the microbenchmark keeps the counter in a register and still shows the delta.
3. **Three more instructions per K token** (97 against 94, in a scoring loop with issue slack): est. 0 to 30 % of the delta.
4. **One extra loop exit per visit** (possible mispredict): est. under 10 % of the delta.

Refuted (one line each): the scoring pass is not un-inlined (no `score_k` or `dotter` symbol, no call in the loops). The run-time stride folds to a constant. Q does not spill (22 of 32 zmm used, no zmm stack traffic). The head does not read K more often (it reads it 4 times per token, the base 16 times). The per-visit setup is 3 instructions shorter at the head. `save_k`'s extra assertion is one compare per row at both heads and outside the attention workers. The run-time AMX decline does not execute under the kill switch (the `&&` chain stops at the null packed query). The staging change runs only under FPGA attention.

### Fix candidates

- **F1, diagnostic, one line.** Drop `relevant_k_tokens++` from the selection pass and set it to `std::popcount(live)` after the loop. Settles cause 2 (recovers est. 20 to 40 % if the chain contributes, 0 % if the pass is issue-bound).
- **F2, recommended, keeps the two-pass design.** A dense-page fast path in the selection pass: when the page lies inside one visible range, the query may see it, and the sliding window does not cut it, build the mask arithmetically (`live = ((1 << (end - begin)) - 1) << begin`, all ones for a full page) and skip the token loop. About 10 scalar instructions per visit in place of est. 1,440. In prefill at prompt 8192 almost every visit is dense. Expected recovery est. 80 to 100 %, with `page::score_k` unchanged. The AMX path already has the same test (`is_dense_amx_page`).
- **F3, fallback.** A per-visit scorer object from the page (holds the K view and the 4 dotters) called inside the selection loop for row-major slots, the VNNI branch keeping the mask. Returns to the base's code shape at the cost of a layout-specific branch in the selection loop, which PR #5047 set out to remove.

### What settles it on 3bda (when the machine is free)

One repetition of each kill-switch binary in the same cell, `perf stat` on the attention workers over a 50 s window of prefill (cycles, instructions, ref-cycles, branch and mispredict counts, vector-port uops, L1 and L2 miss loads), then `perf record -e cycles:u` and `perf annotate` of the `apply_page_range` symbol.

| Cause | Confirmed if | Rejected if |
|---|---|---|
| 1 | cycles +3.0 to +3.5 %, instructions +2.5 to +3.5 %, IPC ratio 0.97 to 1.00, vector-port uops within 1 %, and the selection-pass block holds 3 % or more of the head's `apply_page_range` samples | the selection pass holds under 1 % of the samples while cycles still rise 3 %, or cycles rise under 1 % |
| 2 | fix F1 cuts the prefill delta by 0.5 s or more | F1 leaves the delta at +2.2 s |
| 3 | the extra samples sit in the scoring pass with IPC unchanged | the extra samples sit in the selection pass |
| 4 | mispredicts rise by 0.5 to 1.1 G (at most one per visit) | mispredicts rise by more than 3 G |

Insufficient data: the core clock of the workers during the campaign (3.75 GHz is the 2026-08-31 figure, `ref-cycles` against `cycles` gives the real ratio), and whether the campaign binaries were linked with ThinLTO (the loop structure is the same either way in the local links).

🤖 Generated with [Claude Code](https://claude.com/claude-code)
