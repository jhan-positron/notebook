# Software K scoring path: base a5697f86d3 vs head ade89a9d9c (PR 5047)

## Short version

With the AMX kernel off at run time, the head scores K with the same dot-product kernel, the same K bytes and the same number of dot products as the base. The only hot-path change is the loop shape: the base scores each selected token inside the token-selection loop, and the head first records the selected tokens in a 64-bit mask (pass 1) and then scores them in a second loop inside `page::score_k` (pass 2). A local compile of both versions shows that pass 1 carries a load-add-store of `relevant_k_tokens` through the stack on every selected token, which the base hid under the dot-product work and the head now runs alone, est. 320 to 384 cycles per dense 64-token visit; that is the leading candidate for the +2.247 s (+2.9 %) kill-switch prefill regression, and `perf stat` plus `perf annotate` of the pass-1 loop on the two binaries would settle it.

## Words used here

- base: commit a5697f86d3 (PR 4956 head), worktree /home/jhan/workspace/ai-runs/tron-split-pr1.
- head: commit ade89a9d9c (PR 5047 head), worktree /home/jhan/workspace/ai-runs/tron-pr5047. It is base plus two commits: e17a12ff09 (token loop rewritten with a live mask and a second pass) and ade89a9d9c (K scoring moved into `page::score_k`, `page::k` removed).
- option-off build: a binary compiled without TRON_K_VNNI, so K is stored one 256-byte row per token ("row-major" K).
- kill switch: TRON_AMX_DISABLE=1 at run time. `amx_on` is false, every page goes to the software scoring path.
- software scoring path: the code that computes one Q.K dot product per (query head, K token) with AVX-512 instructions. It fills `s_pages`, a 4 x 64 float array (4 query heads of one KV head, 64 tokens of one page).
- dotter: the struct in h/tron/kernels/dotter.hpp that holds one query head (128 bf16 values in 4 zmm registers) and computes a dot product against one K row with 4 `vdpbf16ps` instructions and one horizontal sum.
- visit: one call of `apply_page_tok` = one (query token, KV page, KV head) triple. Prefill at prompt 8192 makes 1.08 G visits per engine (computed below).
- selected token: one K token of a visit that passes the range and sliding-window checks and therefore gets 4 dot products. Prefill at prompt 8192 makes 68.7 G of these per engine.
- live mask: a `uint64_t` with bit i set when token i of the page is selected.
- `TRON(inline)`: `inline __attribute__((always_inline))` [h/common/attributes.hpp:78].
- `TRON_ASSERT`: compiled in every build, release included. It is an `if unlikely (!cond) abort` [h/common/assert.hpp:69-74].

## Scope

Read in full at both heads: `apply_page_range` [self_attention.hpp:1457-1700 base, 1455-1698 head], `apply_page_tok` [base 1853-1997, head 1842-1968], `apply_dense_amx_page`, `page::k` (base) and `page::score_k` / `try_score_k_amx` / `set_k_row(expr)` (head) [kv_cache.hpp:1973-2065 head], `kv_block::k_view` / `k_at` [kv_cache.hpp:2586-2610 base, 2583-2607 head], dotter.hpp (whole file, both heads identical), view.hpp (view flags), slice.hpp, model.hpp save_k hunk, full.hpp hunk.

`git diff a5697f86d3 ade89a9d9c --stat`: 9 files. Runtime files: kv_cache.hpp, model.hpp, self_attention.hpp, scheduler/full.hpp, tensor/k_vnni.hpp (comment only). The rest are tests.

## What is unchanged on the path (verified by reading both bodies)

- `apply_page_range` is byte-identical between base and head. The diff has no hunk in it. The page loop, the query loop, the range dismissal (`dismiss_workless_ranges`), the page-visibility gate, the sliding-window page skip, the stats hooks and the `mark_valid_for` logic are the same.
- The AMX gate with `amx_on == false`: `amx_qp` stays `nullptr`, and in `apply_page_tok` the condition `amx_q_packed != nullptr && ...` short-circuits before `is_dense_amx_page` in both versions. The head adds `apply_dense_amx_page(...)` as a third `&&` operand, which is never reached.
- The `s_pages` fill: both write `-inf` into 4 x 64 floats before scoring (16 zmm stores per visit).
- The range/mask walk inside `apply_page_tok`: the `for (i = begin; i < end; ++i)` loop, the `range_hint` advance, the `query_visible` skip (`i = page.offset_for(tok_hi) - 1`), the sliding-window test and `relevant_k_tokens++` are the same text in both.
- The dot-product kernel: both instantiate `dotter<bf16, 128, aligned=true>`. Base uses `scalar_t = btensor_t<128>::element`, head uses `scalar_t = remove_cv_t<Q::element>`. Both resolve to `bf16`: the query buffer is `hardware::btensor` = `dmatensor<bf16, ...>` whose 1-D `element` is `bf16` and whose `as_view()` returns `view<bf16, aligned=true, dma=true, seq<N>, sseq<1>>` [h/tron/hardware/btensor.hpp:21, dmatensor.hpp:168 and :223]. dotter.hpp is identical at both heads (`git diff --stat -- h/tron/kernels/` lists only k_vnni.hpp, a comment).
- The K view: both take `kv_block<geometry>(slot, kv_head).k_view()` = `const_view<bf16, VIEW_ALIGNED_TRUE, VIEW_DMA_FALSE, seq<64, 128>>` over the same storage; `keys[i]` is the same `const_view<bf16, true, false, seq<128>, sseq<1>>` at `data + 128 * i` with the same two asserts (`data != nullptr`, `i < 64`). `kv_block::k_view` and `k_at` are byte-identical at both heads.
- K bytes read per selected token: 256 bytes (one row) in both. Number of dot products per selected token: 4 (kv_mul) in both. Number of selected tokens: decided by the unchanged selection loop in both.
- The epilogue (scale, max, exp, `scaled_v` PV, v*/s*/m* update): no hunk. `scaled_v_expr` is unchanged.
- The score store: base writes `s_pages[offset][i]` (plain array index, `tensor::operator[]` has no assert [tensor.hpp:142-149]); head writes `scores[h * stride + i]` with `scores = &s_pages[0][0]` and `stride = 64`, a compile-time constant after inlining. Same addresses.

## Every difference on the path (amx_on false, option-off build)

### D1. One pass became two passes (commit e17a12ff09, kept by ade89a9d9c)

Base [self_attention.hpp:1935-1961 base]: inside the selection loop, for each selected token `i`: `if (!keys.valid()) keys = page.k(...)` (one load + compare + branch per selected token), then `keys[i]` and 4 dot products stored to `s_pages[offset][i]`.

Head [self_attention.hpp:1893-1919 head, kv_cache.hpp:1978-2003]: pass 1 records `live |= 1 << i` per selected token (shift + or, 2 instructions). After the loop, `page.score_k(...)` runs pass 2: `for (remaining = live; remaining != 0; remaining &= remaining - 1) { i = countr_zero(remaining); ... }` (tzcnt + blsr + test/branch, 3 instructions) then the same `keys[i]` and 4 dot products.

Mechanism: the dot-product work is identical. The bookkeeping around it changes by est. +5 instructions and -2 instructions (the removed `keys.valid()` check) per selected token, net est. +3 instructions per selected token, plus the second loop's own entry and exit per visit (est. +5 instructions per visit). The base body is est. about 100 instructions per selected token (4 dotters x (4 loads + 4 vdpbf16ps + 1 add + about 10 for the horizontal sum + 1 store) + about 12 for selection), so the net change is est. +3 %. Two second-order effects go the same direction: pass 2 starts only after pass 1 finishes the whole page, so the out-of-order window overlaps less selection work with dot-product work, and the `tzcnt` result feeds the K row address (3-cycle latency on the address chain instead of a loop counter).

Shows in prefill and not in decode: yes. Prefill visits each page with the query loop inside the page loop, so the 16 KB K plane (64 rows x 256 bytes) stays in L1/L2 across the minibatch's queries and the loop is instruction-bound. Decode streams every K page from memory once per query and is memory-bound, so extra ALU instructions hide under the loads. Also the event count differs: 68.7 G selected tokens per engine in prefill vs 4.36 G over the whole 256-step decode (ratio 15.8, computed below).

Measurement that settles it: `perf stat -e instructions,cycles` on the engine process for the kill-switch prefill, base vs head. D1 predicts instructions up by about +3 % of the attention share with cycles up by about the same, and `perf annotate` of the `apply_page_range` instantiation shows a `tzcnt`/`blsr` loop at the head only. A direct microbenchmark (one visit of a dense page, 64 live tokens, both loop shapes) gives the per-token delta in cycles.

### D2. `dotter` construction moved from before the selection loop to after it, and under `live != 0`

Base builds `dot_q` (4 dotters = 16 zmm loads of the query, 1 KB) before the selection loop on every visit, including visits that end with `relevant_k_tokens == 0`. Head builds it inside `score_k`, only when `live != 0`. Mechanism: saves 16 loads per empty visit. Prefill empty visits are rare (the page-visibility gate in `apply_page_range` already drops pages the query cannot see). Cost: 0 or negative (est. -16 instructions per empty visit). This cannot cause a regression. Settled by the same `perf annotate`.

### D3. The K view is taken eagerly once per visit instead of lazily on the first selected token

Base: `keys` starts invalid and `page.k(...)` runs at the first selected token, guarded by `keys.valid()` on every selected token. Head: `kv_block<geometry.kv>(slot, kv_head)` runs once at the top of `score_k` (after the `live == 0` return). Mechanism: `kv_block` is `book.kv_block(slot, kv_head, pageno())` with `pageno() = this - book.pages.data()` (a pointer subtraction, est. 5 instructions). Both versions do it once per non-empty visit. The head drops the per-token `valid()` check (est. -2 instructions per selected token, already counted in D1). Cost: 0 per visit, negative per token. Cannot cause a regression.

### D4. The scoring loop now lives in `page::score_k` (a member of the page class template) instead of inline in `apply_page_tok`

`score_k` is `TRON(inline)` = always_inline [kv_cache.hpp:1976], so the compiler must inline it. After inlining, `scores` is `&s_pages[0][0]` (a stack array) and `stride` is the constant 64, so the store addressing is the same as the base. The dotter objects live in a local `std::array` whose address is not taken, so the compiler can keep the 16 zmm in registers in both versions. Risk: if the compiler keeps `stride` as a runtime value or spills the query registers around the second loop, the per-token cost rises by a few instructions. This is a code-generation question, not visible in the source. Settled by `objdump -d` of the two binaries' `apply_page_range` instantiation (count instructions in the loop that contains `vdpbf16ps`). See the object-code section below for what a local compile shows.

### D5. The AMX `if constexpr` no longer excludes the VNNI layout, and `apply_dense_amx_page` returns `bool`

With `amx_q_packed == nullptr` the `&&` chain stops at the first operand in both versions. Zero instructions at run time with the kill switch. Not a candidate.

### Adjacent (not the scoring path, but prefill-only) changes

- A1. `save_k` [model.hpp:3097-3102]: base calls `pg.k<geometry>(slot, kv_head, j).set(kout)`, head calls `pg.set_k_row<geometry>(slot, kv_head, j, kout)` which is `TRON_ASSERT_LT(i_page, page_size)` + `kv_block(...).k_at(i_page).set(row)` [kv_cache.hpp:2035-2049]. Same conversion and same store. One extra compare-and-branch per stored row. Prefill stores 16.8 M rows per engine (8 users x 8192 tokens x 32 layers x 8 KV heads), so est. 17 M to 50 M extra instructions, well under 0.05 s. Decode stores 1 row per user per step. Not a candidate for 2.2 s.
- A2. FPGA staging [full.hpp:2748-2754]: `k_head_fn` now always copies the row through `get_k_row` into the caller's scratch (a 256-byte memcpy) instead of returning a pointer into the page for row-major K. This runs only when hardware attention is in use. The campaign cell used CPU attention. Zero cost here. (It would be a real per-token copy on an FPGA-attention cell.)
- A3. The dotter and k_vnni headers are now included from kv_cache.hpp instead of self_attention.hpp. Compile-time only.

## Event counts (computed, llama-3.1-8b, 8 users, prompt 8192, 256 generated, per engine)

Script: `python3 -I` with P=8192, users=8, layers=32, kv_heads=8, kv_mul=4, page=64.

- Prefill selected-token events: 8 x 32 x 8 x (8192 x 8193 / 2) = 68.7 G. Dot products: 274.9 G.
- Prefill visits (query, page, KV head): 8 x 32 x 8 x sum over q of (q / 64 + 1) = 1.08 G.
- Decode selected-token events over 256 steps: 4.36 G. Ratio prefill / decode = 15.8.
- If the whole +2.247 s is in the scoring loop, the implied extra cost per selected token is 2.247 s x (attention workers per engine) / 68.7 G: 1.05 ns at 32 workers, 2.09 ns at 64 workers, 4.18 ns at 128 workers. At about 2.2 GHz that is 2.3 to 9 cycles per selected token. D1's est. +3 instructions per token lands at the low end of that range only if the loop runs near 1 instruction per cycle. Insufficient data on the worker count per engine in that campaign and on the loop's IPC. The `perf stat` counts above resolve both.

Note on tensor-parallel 2: whether each rank scores all 8 KV heads or 4 of them changes the per-rank count by 2x but not the base-vs-head comparison.

## Why the shipped (AMX on) cells do not show it

With AMX on, 2.8 % of K tokens take the software path (campaign figure). 2.8 % of +2.247 s = +0.063 s est. The measured +0.138 s is inside the 0.150 s band and consistent with that order. At prompt 1024 the software share and the absolute time are both small, matching the -0.001 s delta.

## Object-code check (local compile, no machine)

Method: both worktrees were compiled with the lcheck toolchain (clang 19.1.7 from the ziglang package, the mirrored nix headers, the `gen` tree's flags: -O3, -mavx512bf16, -DTRON_AMX_DISPATCH, -DNDEBUG) to objects, then disassembled with `objdump -d`. Script: /tmp/claude-0/-home-jhan-workspace-intel-AMX-random/e5f1ec3f-7cb5-4755-a5bc-0280de828ba5/scratchpad/ksroot/obj/ocompile.sh. Objects and disassembly are in that `obj/` directory. Caveats: the flags are the test tree's (the nightly deb preset may differ), the compiler is clang 19 as in production but not the same build, and the instantiations are the test units' model shapes, not llama-3.1-8b. The unit t/t_amx_dispatch_dtype.cpp instantiates the production-like shape: bf16 queries (`hardware::btensor`), head size 128, kv_mul 4 (files `base_dtype.bf1.asm`, `head_dtype.bf1.asm`). The unit t/t_llama_unit.cpp instantiates float queries with kv_mul 2 (files `base.fn1.asm`, `head.fn1.asm`).

Findings on the bf16-query, kv_mul-4 instantiation (the production shape):

- `score_k` and `apply_page_tok` are fully inlined into `apply_page_range` in both versions (no call to either symbol in the function body). D4's "not inlined" risk is excluded. The score stores are `vmovss %xmm, 0x980(%rsp,%rdx,4)` and so on: constant stack offsets per head, so `stride` is folded. The 16 query zmm registers (zmm0-zmm15) are loaded once per visit and kept in registers across the loop in both versions. D4's "spill" risk is excluded.
- Base scoring loop body (addresses 18f6-1ad5): 72 instructions per selected token: 16 `vdpbf16ps` with memory operands (each head re-reads the 4 K cache lines, 16 load micro-ops), 8 `vxorps`, 4 horizontal sums of 9 instructions each, 4 `vmovss` stores, the `cmp $0x40; jae` assert, and a `mov 0xb0(%rsp); inc; mov 0xb0(%rsp)` triple: `relevant_k_tokens` lives on the stack and is incremented through memory once per selected token.
- Head second-pass loop body (addresses 18b0-1a80): 74 instructions per selected token: `tzcnt`, `mov`, `shl`, 4 `vmovaps` K loads shared by all 4 heads, 16 register-operand `vdpbf16ps`, the same 4 horizontal sums and 4 stores, `lea; and; jne` (the blsr idiom). So the head's scoring loop has 2 more instructions and 12 fewer load micro-ops per selected token than the base's.
- Head first-pass loop (addresses 1544-1762): about 24 instructions per selected token: loop head (bounds check, `page.at_offset` compare against `range_hint->tok_hi`, visibility test), the sliding-window test, `mov 0x38(%rsp); inc; mov 0x38(%rsp)` (the same memory increment of `relevant_k_tokens`), `bts` into the live mask, and a `mov %rsi,0x90(%rsp)` / `mov 0x90(%rsp),%rdx` round trip of `range_hint` through the stack.
- Base selection path per selected token (addresses 1634-184b): about 20 instructions of the same bookkeeping, executed in the same loop iteration as the 72-instruction scoring body.

Totals per selected token (counted, this instantiation): base about 92 instructions in one loop; head about 24 (pass 1) + 74 (pass 2) = 98 instructions in two loops. The instruction-count difference is est. +6 % on the scoring loop, smaller than the source reading suggested, because the compiler shares the K loads across heads in the head's loop and did not in the base's.

The structural difference that the counts do not show: the base hides the bookkeeping under the dot-product work, and the head runs it as its own pass. The `relevant_k_tokens` increment is a load-add-store through the stack on every selected token, in both versions. That is a loop-carried dependency through memory of est. 5 to 6 cycles per iteration (store-to-load forwarding latency plus the add). In the base loop, those cycles overlap with the 16 `vdpbf16ps` and 4 horizontal sums of the same iteration (est. 20 or more cycles per token, bound by the shuffle port), so the chain costs nothing extra. In the head's pass 1 there is almost no other work, so the chain sets the pace: est. 5 to 6 cycles x 64 selected tokens = est. 320 to 384 cycles per dense visit, spent before pass 2 can start (pass 2's first `tzcnt` needs the finished mask). Pass 2 then costs about what the base loop cost. Net: est. +20 to +30 % on the QK scoring loop per dense visit, prefill only (decode visits are memory-bound and 15.8x fewer).

Cross-check against the measurement: the +2.247 s over 1.08 G prefill visits per engine equals 2.247 s x W / 1.08 G per visit, where W is the number of attention workers per engine: 67 ns at W = 32, 133 ns at W = 64, 266 ns at W = 128, or est. 146, 293 and 586 cycles at an assumed 2.2 GHz. The est. 320 to 384 cycles of pass 1 per dense visit sits inside that range for W between 64 and 128. Insufficient data: the attention-worker count per engine and the core clock during the campaign are not in this task's inputs. `perf stat` on the engine process (cycles, instructions, and the event for store-forwarding stalls or `ld_blocks.store_forward`) and `perf annotate` of the pass-1 loop would settle it.

The float-query kv_mul-2 instantiation (t_llama_unit) shows the same shape: base 76 + 20 = 96 instructions per selected token in one loop, head 20 + 58 = 78 in two loops (the head's loop converts each K row from bf16 to float once instead of once per head). The same memory increment of `relevant_k_tokens` is in pass 1 there too (`mov 0xa0(%rsp); inc; mov 0xa0(%rsp)` at address 114d-1157).

## Hypotheses, ranked

1. H1 (D1, pass-1 serialization): the two-pass split moves the per-token bookkeeping, including a load-add-store of `relevant_k_tokens` through the stack (a loop-carried memory dependency of est. 5 to 6 cycles per selected token), out of the dot-product loop into a pass of its own. The base overlapped it with est. 20 or more cycles of `vdpbf16ps` and shuffle work per token. Est. +320 to +384 cycles per dense visit, est. +20 to +30 % on the QK scoring loop. Prefill-only: prefill is compute-bound on L1-resident K and has 15.8x more selected tokens than decode. Settle with `perf stat` (cycles, instructions, `ld_blocks.store_forward`) on the kill-switch prefill, base vs head, and `perf annotate` of the pass-1 loop. A one-line check: make `relevant_k_tokens` a register value (`std::popcount(live)` after the loop) at the head and re-run the cell.
2. H2 (D1, instruction count): pass 2's `tzcnt` / `blsr` / branch and the second loop's entry cost est. +6 instructions per selected token (+6 % counted on the local compile), partly paid back by 12 fewer load micro-ops. Smaller than H1. Settled by the same `perf stat` instruction count.
3. H3 (D4, code generation of the production binary): the local compile shows full inlining, folded `stride` and no query-register spills, so this is excluded for this toolchain and these flags. It stays open only if the nightly build's flags differ. Settle with `objdump -d` of the two production binaries (count instructions in the `vdpbf16ps` loop and look for `tzcnt`).
4. H4 (A1): the extra assert in `save_k`. Est. under 0.05 s. Listed for completeness, cannot explain 2.2 s. Settle with `perf annotate` of `save_k`.
5. Excluded by reading: D2, D3 (cheaper at the head), D5 (not executed), A2 (not executed with CPU attention).
