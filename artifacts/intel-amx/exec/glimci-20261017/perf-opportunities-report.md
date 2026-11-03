# Lost performance under the minimum-change rule: synthesis

## Short version

Two candidates survive: a software prefetch of the next KV page inside the AMX attention kernels (decode TPS est. +0.7 to +2.0 % at tp4, prompt 1024, FPGA full layers; est. +1.1 to +3.2 % at prompt 2048), and a planner change that balances the pending pass on its own with a path-weighted page cost (prompt-parsing time est. 4 to 5 % shorter, decode neutral). Twenty other candidates were refuted, almost all because the gain is under 1 % of a decode step or of a prompt forward. Recommendation: implement the prefetch first as one PR stacked on jhan-amx-kvmul16, then the planner change as a second PR, each with its own 3bda A/B.

## Words used here

- tron: the inference program under test. runtron: its command-line tool. Branch jhan-amx-kvmul16 (worktree /home/jhan/workspace/ai-runs/tron-glimmer-amx, head 5061623a34) is the kv_mul-16 AMX change this report is about.
- AMX, AVX: two CPU instruction sets. AMX-on / AMX-off: the two arms of the kill switch TRON_AMX_DISABLE.
- kv_mul: query heads per KV head (16 for Muse Glimmer: 32 query heads over 2 KV heads).
- KV page: a 64-token block of the key/value cache. K plane and V plane: the 16 KB of keys and the 16 KB of packed values of one page for one KV head.
- visit: one (query token, KV head, page) scoring step. A dense page is a complete page that one query sees in full, the only kind the AMX kernel scores.
- ready page: a page written in an earlier forward. pending page: a page written in this forward. The ready pass runs before the K/V wait, the pending pass after it [self_attention.hpp:815-827].
- planner: finish_sw_plan [model.hpp:2861-2917], the per-forward assignment of (KV head, page) sections to attention workers. work(): its cost unit, today one unit per visit regardless of path [common.hpp:679-680].
- busy: time a worker spends inside one attention job (counter T2). join wait: the part of busy spent waiting for peer workers (counter T5). compute: busy minus join wait. These come from TRON_ATTN_STATS=1 runs.
- T1: forward wall time per decode step. TTFT: time to first token, the prompt-parsing time.
- TSC: the CPU time-stamp counter, 2.70 GHz on delphi-3bda (1,000 TSC cycles = 0.37 us).
- L1 / L2 / L3: the 48 KB per-core, 2 MB per-core and 432 MB per-socket caches. Prefetch hint T0 / T1: the level (L1 or L2) a software prefetch instruction targets.
- tp2 / tp4: tensor-parallel width (2 or 4 engines). FPGA config: 13 full layers on the card, 39 sliding-window layers on CPU (production). CPU config: all 52 layers on CPU.
- prompt 1024 / prompt 2048: runtron --prompt-length; every run then generates 256 tokens.
- bf16 rounding order: a change that alters only the order of floating-point additions, inside one bf16 notch. This class is accepted in this project.
- est.: an estimate, not a measurement.

## Candidate 1 (highest decode gain): prefetch the next page's K and V planes inside the AMX kernels (pv-3)

### What to change

- src/tron/kernels/amx_attn.cpp: qk_rowmajor_128x4 (lines 199-221) and weights_times_v_128x4 (lines 284-327) take two extra nullable pointers, next_k and next_v. After each of the 16 K tile loads, the QK kernel issues 16 _mm_prefetch lines of next_k with _MM_HINT_T1. After each of the 16 V tile loads, the PV kernel does the same for next_v.
- h/tron/kernels/amx_attn_iface.hpp: the two signatures and the two explicit instantiations (group_heads 4 and 16) gain the pointers.
- h/tron/models/self_attention.hpp: the page loop (lines 1563-1600) looks one page ahead in page_range for the same KV head. apply_dense_amx_page (lines 1755-1812) passes the next page's K plane (page.k<geometry.kv>(slot, kv_head).data) and packed V plane. The V plane address is friend-gated by detail::v_vnni_access [amx_attn.cpp:273]. A small helper in h/tron/tensor/v_vnni.hpp or in the kernel file must expose it for prefetch only.
- Issue the prefetch once per page, not once per (query, page). In prefill the same page is reused by up to 128 queries, so a per-query prefetch would waste 512 instructions per query.
- Keep a kill switch for the A/B (an environment variable read once at start, like TRON_AMX_DISABLE).

Size: about 30 lines in the kernels, about 15 at the call site, about 10 for the V plane helper.

### Why faster

- No software prefetch exists on the attention path today. grep for prefetch over self_attention.hpp, amx_attn.cpp, amx_attn_iface.hpp and kv_cache.hpp finds only comments that rely on the hardware prefetcher [kv_cache.hpp:62, 75, 2384].
- In decode each page is read once per forward. Each engine reads 490 MB (prompt 1024) to 958 MB (prompt 2048) of KV per forward, and two engines share one 432 MB L3. So the K and V tile loads miss to L3 or DRAM.
- The hardware prefetcher stops at 4 KB boundaries. The 16 KB planes span four OS pages each, and the V plane sits in a different 4 KB page from the K plane. So the memory pipe is idle during the softmax epilogue, and the compute is idle during the two streams.
- Measured on delphi-3bda, one core: a visit with the data in L1 costs about 5,500 TSC cycles. With a 128 MB working set it costs about 9,400. With a 1 GB working set it costs about 13,000 to 17,600 (the two benches differ in page size). The in-situ upper bound from the counters is 11,700 TSC per AMX visit (tp2, prompt 1024, FPGA config). So about half of a production visit is data wait.
- A burst of 512 prefetches at the top of the page loop does not help. It fills the 16 line-fill buffers and stalls the front end. Measured: 0 to -8 % of the visit, and worse than no prefetch at the 128 MB set.
- Spreading the prefetch across the tile loads overlaps the data wait with the compute. Three independent benches agree on the direction:
  - pvbench-sk1 (one core, 2 reps): variant 13 (16 lines after each tile load, T1 hint) cut the loop time by 25 to 29 % at the 128 MB set (9,415 to 6,659-6,726 TSC) and 27 % at the 1 GB set (13,001 to 9,242-9,464 TSC).
  - pvbench2 (one core, 2 MB pages, shipped epilogue kept): the candidate's spread form saved 1,220 TSC at 128 MB (-19 %) and 880 to 1,190 TSC at 1 GB (-10 to -14 %).
  - pfbench (dispatch-1's skeptic, 2 GB buffer, 2 MB pages, 16 parallel copies on cores 79-94 to mimic 20 workers): in-kernel prefetch after each tile load cut the median visit from 10,703 to 8,857 TSC (-17 %), and from 9,574 to 8,016 on a second run. T0 instead of T1 gained only 4 to 7 %. Two pages ahead gained nothing more.
- So the saving per visit under contention is est. 1,200 to 1,850 TSC cycles (0.44 to 0.69 us), with the one-core upper range at 2,300 to 3,500 TSC.

### Est. gain

- Decode, production configuration (tp4, 8 users, FPGA full layers): est. +0.7 to +2.0 % TPS at prompt 1024 (forward 15.64 ms, about 5.6 AMX visits per job, 39 CPU layers); est. +1.1 to +3.2 % at prompt 2048 (forward 16.44 ms). The low end uses 1,200 TSC per visit (pvbench2), the high end 1,850 to 3,500 TSC (pfbench under contention, pvbench-sk1 one core).
- Decode at tp2: est. +1.0 to +3.0 % at prompt 1024 (forward 23.70 ms, 13.8 visits per job); est. +1.6 to +4.7 % at prompt 2048.
- CPU config (52 layers): about 1.4x the FPGA-config numbers.
- Prefill: about 0 %. A page is reused by up to 128 queries in a prompt forward, so the data wait is per page, not per visit.
- Why the AMX visit time maps 1:1 to the forward wall: the kill switch moved busy per worker by -2.18 ms and T1 by -2.16 ms per forward (tp2, prompt 1024, FPGA); by -4.0 ms and -3.95 ms at prompt 2048 [attn-stats-compare.md section 7].
- The repetition spread of decode TPS in the campaign is 0.0 to 0.4 % [section 6], so +1 % is measurable with 3 to 4 reps.
- Open point that only the runtron cell settles: in production 40 (tp2) to 47 (tp4) workers fetch at once, plus the FPGA DMA traffic. Part of the stall may be bandwidth, which prefetch cannot remove. The 16-copy pfbench covers part of this, not all of it.

### Numerics risk

None. A prefetch has no architectural effect. The same loads run in the same order. The kill-switch comparison must produce identical tokens and identical logits.

### Test to add

- In t/t_amx_numerics.cpp: one case per group_heads (4 and 16) that runs qk_rowmajor_128x4 and weights_times_v_128x4 twice on the same page, once with next_k and next_v null and once pointing at a second page, and asserts bit identity of the outputs. This encodes the contract that the prefetch pointers never change results.
- The existing kernel tests keep covering the math.

### runtron measurement

- Cells: glm-tp4-8u-p1024-fpga, glm-tp4-8u-p2048-fpga (production shape), glm-tp2-8u-p1024-fpga, glm-tp2-8u-p2048-fpga, plus the CPU-config pair at tp2. Two arms via the kill switch, 4 reps, TRON_ATTN_STATS=1, our half of delphi-3bda, about 3 hours.
- Metrics: decode TPS per user; (busy_cycles - join_wait_cycles) / ready_amx_visits per decode forward class (expect a drop of 1,200 to 1,850 TSC from about 11,700 at tp2 prompt 1024); T1; forced-run token identity between arms.
- Optional: perf stat on one attention worker core for L2 and LLC misses. perf_event_paranoid is 4 on delphi-3bda, so this needs a root run or the sysctl relaxed.
- Prefill check: 'Parsing the prompt took' must stay inside its 0.06 % repetition band, so the per-page prefetch costs nothing there.

## Candidate 2: balance the ready and pending passes separately and weight pages by path cost (prefill-2)

### What to change

- h/tron/models/model.hpp finish_sw_plan (lines 2861-2917): run the page-centre assignment twice, once over the ready pages and once over the pending pages, each with its own total, its own work cumsum and its own worker cursor spanning all workers of the KV head by speed share. Today one cumulative sum covers ready then pending per KV head [lines 2884-2912], so all pending pages of a KV head land on the last one or two workers of that head's block. The ASCII diagram comment at lines 2853-2860 must change with it. About 30 to 70 lines.
- h/tron/models/model.hpp estimate_work (lines 2511-2600): classify each page's runs as AMX dense, AVX full page or AVX partial, using the same conditions as is_dense_amx_page [self_attention.hpp:1711-1723] (whole page in one run, inside the window, AMX shape and available). Tally a weighted cost. In the FPGA configuration the pending pass never takes the AMX path (pending_amx_visits is 0 in every FPGA cell), so pending pages count as AVX there. About 30 lines.
- h/tron/models/common.hpp work_estimate_t (lines 671-695): add the dense-visit count and make work() return the weighted cost, with named integer weights derived from the measured ratio (AMX dense visit about 1.65 to 1.7 us, AVX full page about 5.5 to 6.9 us, AVX partial about 5 to 6.6 us, so about 1 : 3 : 3). About 15 lines.
- split_sections_by_query fixed_cost [model.hpp:2944-2947] moves to the same units. About 5 lines.
- self_attention.hpp exposes the dense-predicate inputs or a profile flag to the planner. About 10 lines.

Total est. 200 to 300 lines over 4 files plus tests.

### Why faster

- The join wait share of prompt forwards rises from 16.0 % to 43.8 % (tp2, prompt 1024, FPGA), from 17.5 % to 42.5 % (tp2, CPU config) and from 30.5 % to 56.8 % (tp4, prompt 1024, FPGA) when the kernel is turned on [attn-stats-compare.md section 7].
- The per-worker counters exist for six AMX-on cells (leaves/*/prompt_or_mixed_worker_N) and show the mechanism directly. tp2, prompt 2048, FPGA, rep 1: worker 16 holds 687,427 pending AVX visits and computes 5.86 ms per job with 0.69 ms of join wait. The 13 AMX-ready workers compute 3.1 to 3.4 ms and wait 3.7 ms each. Mean compute is 3.63 ms, maximum 5.86 ms. With the kernel off the same cell has maximum 10.39 ms against mean 9.41 ms. So the kernel widened the gap from 0.98 ms to 2.22 ms per layer.
- tp2, prompt 2048, CPU config: workers 16 and 26 compute 6.38 and 6.41 ms against a 4.16 ms mean.
- tp4, prompt 1024, FPGA: the slowest workers are the first of each block (workers 16 and 35, 207,636 partial-page AVX ready visits, 3.30 and 2.92 ms per job) and then the pending workers (3.00 ms), against a 1.62 ms mean. This cell showed no prefill gain from the kernel (busy 3.72 vs 3.78 ms) because the slowest workers run AVX in both arms. It shows that change (a), the path-weighted cost, is required. Change (b) alone leaves tp4 on the partial-page worker.
- The speedometer cannot fix this. estimate_speeds clamps every worker to at least 0.5x the fastest [threading.hpp:642-650]. The pending workers already sit at that clamp (exit log 'Worker speeds': 0.0239 against 0.0479 max on pool workers 16 and 26, rt/glm-tp2-8u-p1024-fpga__fpga__amxon__rep1.log:167).
- The join cannot start until every section of the KV head is done (run_joins polls sections_left [self_attention.hpp:1259-1265]). So the slowest worker sets the layer time.

### Est. gain

- Prefill (TTFT) only. Production shape tp4, prompt 1024, FPGA: 1.3 ms per layer x 52 layers = 68 ms of a 1,032 ms prompt forward = 6.6 % bound, est. 4 to 5 % realistic.
- tp2, prompt 2048, FPGA: max worker 5.86 ms to about 3.6 ms, minus 0.4 ms residual skew = 1.8 ms per layer x 52 = 94 ms of 1,924 ms = est. 4.9 %. TTFT 30.9 s to about 29.4 s.
- tp2, prompt 2048, CPU config: est. about 5 %. tp2, prompt 1024, FPGA: est. 4 to 6 % from the aggregate (5.18 ms busy against 2.91 ms mean compute, no per-worker data for that cell).
- Changes (a)+(b) together: bound 6 to 8 %, realistic 4 to 5 % of prefill time. Change (b) alone at tp2 prompt 2048: est. 3.8 %.
- Decode: est. 0 % (under 1 %). Per-worker decode compute is 42.5 to 48.6 us per job across all 20 workers (tp2, prompt 1024, FPGA), so decode join wait is not plan imbalance at tp2.
- Conflict to surface (Rule 7): the decode side of the same pending pile-up was examined as parallel-1 and dispatch-6 (both refuted, table below). One parallel-1 vote put the tp4 decode gain at est. +2.0 to +3.0 %. The other put it at about 0 because a second tail (AVX ready pages on the first worker of each block) is as long as the pending tail. Change (a) of this candidate addresses that second tail. So the decode effect at tp4 is est. 0 to +3 % and is an open measurement, not a claim.

### Numerics risk

Section boundaries change the fold order of the join partials. That is bf16 rounding order, the same class the speedometer already causes between runs. Pay-for-determinism identity tests compare against a fixed plan within one build, so they pass. Any stored expected logits that depend on the fold order need regeneration. A forced-run logits A/A against the jhan-amx-kvmul16 head is the check. A wrong cost constant can slow other models, because the planner is shared by every model and by the FPGA split. Keep the llama-8b control cell.

### Test to add

- t/t_llama_unit.cpp (planner tests around lines 3094-3240 build plans by hand and call split_sections_by_query): recompute the expected values of the existing estimate_work and split tests for the new units, add one test that asserts the pending pages of a KV head spread over all of that head's workers instead of forming a tail, and one test that an AVX-partial page costs more than an AMX dense page in work(). About 100 lines.
- Run t_llama_unit, t_amx_numerics and the kill-switch identity test.

### runtron measurement

- Cells: glm-tp4-8u-p1024-fpga, glm-tp2-8u-p1024-fpga, glm-tp2-8u-p2048-fpga, plus l8b-tp2-8u-p1024-cpu as the regression control. TRON_ATTN_STATS=1, 2 to 4 reps, about 3 hours of our half.
- Metrics: per-worker prompt_or_mixed_worker_N maximum compute per job (expect 5.86 ms toward 3.6 ms at tp2 prompt 2048 FPGA); join wait share of prompt forwards (expect 45 % toward 15 %); 'Parsing the prompt took' of the slowest user (expect 30.9 s toward 29.4 s); decode TPS per user inside the repetition band of 41.89 (tp2 prompt 1024 FPGA) and 119.08 (llama control).
- Trap: the FUSE leaf copy is racy, and half the per-worker files in the prompt-1024 leaves are 0 or 2 bytes. Read the exit report or copy the leaves after the run ends.

## Refuted candidates

| id | Title (short) | Why refuted |
|---|---|---|
| qk-1 | Vectorise the 16-head Q packer | Decode est. 0.2 to 0.6 % of a step (pack count 2 to 5x lower than claimed). Prefill est. 0.7 to 2.1 % TTFT, one vote under 1 %. Below bar on decode, borderline on prefill. |
| qk-2 | Pack Q once per token and only on a dense hit | Per-section duplication does not exist (assign_page merges pages per KV head). Wasted packs est. 0.1 to 0.2 % of a decode step, under 0.5 % of prefill. |
| qk-3 | Q as A operand on VNNI-laid-out K | Needs the K storage layout of PR 4424 (out of scope); the FPGA path reads K and lost 2.3 to 11.8 % on qwen3-4b under that layout; gain est. under 1 % of a decode step. |
| qk-4 | Software-pipeline the transposing store | Loop is page-outer, token-inner, so consecutive calls are not the same token's next page; hideable work bounded at 140 to 170 cycles per visit; est. +0.1 to +0.3 % TPS. |
| qk-5 | Tile configuration for 16 heads (negative finding) | Already at the shape's minimum (16 + 16 TDPBF16PS, no padding work). Resident Q panels save 2 of 20 tile loads, hidden under the multiply chain. |
| pv-1 | Vectorise the 16 correction-factor exps | 240 to 340 TSC per visit = est. 0.2 to 0.4 % of a decode step, 0.13 to 0.3 % of prefill. Also needs a forced-run A/A for a sub-noise gain. |
| pv-2 | Fuse scale / max / exp / sum / bf16 convert | Fusion itself saves about 0 (passes stay in L1 with store forwarding); the real part (vector corr + interleave) is 250 to 334 TSC per visit = est. 0.28 % of a decode step, 0.17 % of TTFT. |
| pv-4 | Load P twice, read amx_o in place | Candidate refuted itself; pvbench variant 2 vs 0 is inside run-to-run spread at every working set. |
| pv-5 | Column-wise softmax on transposed scores | Transpose costs 209 to 503 TSC per visit (4 to 18 % of the QK kernel, under the candidate's own 20 % gate); the PV operand layout keeps half of it; est. 0.1 to 0.2 % TPS. |
| dispatch-1 | Prefetch at the top of the page walk (burst) | The burst form measures 0 % (pfbench, 16 copies); the interleaved form that works is pv-3 above. |
| dispatch-2 | Window-edge page on AMX with a position mask | At most 624 edge visits per forward; est. +0.15 to +0.48 % of T1 at prompt 2048, 0 at prompt 1024 and in prefill. |
| dispatch-3 | Pending page on AMX with a count mask | Needs a V-plane zeroing invariant in the KV cache (out of scope); at mean count 32 the AVX visit costs the same as one AMX visit; est. 0 to 0.6 % of a decode step. Prefill claim wrong (diagonal page fails the causal clause). |
| dispatch-4 | Accept multi-range full pages in the dense predicate | Decode est. +0.1 % (29,016 visits of 2.8 M). Prefill est. 0.5 to 1.3 % TTFT, borderline; 43 % of those pages have 64 one-token ranges so the walk costs part of the saving. |
| dispatch-5 | Vectorise and hoist the Q packer | Measured pack<16> 281 ns on 3bda; est. +0.1 to +0.2 % decode TPS, 0.6 to 0.8 % TTFT ceiling. |
| dispatch-6 | Rebalance for the AMX cost model | Premise wrong: work() already charges one fixed unit per page; granularity bound est. 0.2 to 0.3 % of a forward. Its replacement mechanism (spread pending pages) is covered by prefill-2 / parallel-1. |
| dispatch-7 | Drop the 8 KB amx_o copy | The compiler already folds the memcpy (objdump of the 16-head instantiation at production flags: zero stack stores after the PV call). |
| parallel-1 | Spread decode pending sections | tp2: recoverable wait is 5 us per layer = est. +0.8 % (at the bar). tp4: votes conflict, est. 0 to +3 %, because an AVX-ready tail on worker 0 of each block is as long. Folded into prefill-2 change (a). |
| parallel-2 | Weight the pending walk by dot products | AVX pending cost is 63 % fixed per visit, so k_dot_products is a worse weight than scaled_vs; the pending pass is granularity-bound (48 atomic tasks); extra gain over parallel-1 est. 0. |
| parallel-3 | Job granularity check (no change) | Sections are already page-sized; a query-head split would read each page twice and fill 8 of 16 tile rows. 0 %. |
| parallel-4 | Worker split (TRON_MAX_MAIN_HELPERS) | No code change proposed; prompt forwards already use the estimator branch (2 minibatches); best case est. 1.1 % of prefill with likely loss on the main lane. |
| parallel-5 | Card-layer join wait is the FPGA wait (context) | No change proposed; 0 %. Corrected: software layers hold 74 % of decode join wait, not 60 %. |
| prefill-1 | Pending pass on AMX when a query sees the whole page | Votes split: one vote est. 1.2 to 5 % TTFT (if pending holders are the critical path), the other est. 0.7 to 1.6 % with central 1 %. Mechanism is real; the per-worker data now shows the pending holder is the critical path, so this item should be re-read after prefill-2 lands (see recommendation). |
| prefill-3 | Score N dense pages per kernel call, accumulate in tiles | Removes est. 0.2 to 0.3 us of a 3.7 us visit; est. 0.3 to 0.7 % of a decode step, 0.4 to 0.5 % of prefill; needs the page-outer / query-inner loop inverted. |
| prefill-4 | Tokens-as-tile-rows orientation (negative finding) | Same tile loads, multiplies, exps and transposes at kv_mul 16; 0 %. |

## Recommendation

Implement in this order, on branches stacked on jhan-amx-kvmul16, one PR each.

1. pv-3, in-kernel spread prefetch with the T1 hint (Option B). Reasons: it is the only surviving candidate with a decode gain on the production configuration; it changes no numerics, so the A/B is a bit-identity check plus TPS; it is about 55 lines in three files; the micro-benchmarks, including one with 16 parallel copies, already show the per-visit saving. First step on 3bda before the tron change: none required, the bench step is done. First step on tron: the campaign above with the kill switch. Ship if decode TPS at tp4 prompt 1024 FPGA rises by at least 1 % over 4 reps and prefill time stays inside its band.

2. prefill-2, changes (a) and (b) together. Reasons: it is the largest prefill gain found (est. 4 to 5 % of TTFT) and the per-worker counters confirm its mechanism; it touches the shared planner, so it needs its own test changes, its own forced-run A/A and the llama control cell. Do (a) and (b) in one PR, because (b) alone leaves tp4 on the AVX-partial worker. Report the decode TPS at tp4 as a measured side result, since the parallel-1 votes conflict on it.

3. After prefill-2 lands, re-read prefill-1 (pending pass on AMX when the query sees the whole page) against the new per-worker leaves. Its gain depends on whether the pending holder is still the critical path after rebalancing. If the per-worker maximum compute is still on a pending worker, prefill-1 is the next prefill item; if not, it is below 1 % and closed.

Not recommended now: qk-1 and dispatch-4 are borderline on prefill only (est. 0.7 to 2.1 % and 0.5 to 1.3 % TTFT) and should be measured only if a prefill-only PR is wanted later. Everything else in the table is closed.

Measurement rules for both PRs: delphi-3bda, our half, 8 users, TRON_ATTN_STATS=1, 4 reps for decode cells (repetition spread 0.0 to 0.4 %), copy the per-worker leaves after the run ends, label every projected number est. until the cell has run.

Source files referenced: /home/jhan/workspace/ai-runs/tron-glimmer-amx/src/tron/kernels/amx_attn.cpp, /home/jhan/workspace/ai-runs/tron-glimmer-amx/h/tron/kernels/amx_attn_iface.hpp, /home/jhan/workspace/ai-runs/tron-glimmer-amx/h/tron/models/self_attention.hpp, /home/jhan/workspace/ai-runs/tron-glimmer-amx/h/tron/models/model.hpp, /home/jhan/workspace/ai-runs/tron-glimmer-amx/h/tron/models/common.hpp, /home/jhan/workspace/ai-runs/tron-glimmer-amx/h/tron/tensor/v_vnni.hpp, /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/attn-stats-compare.md, /home/jhan/workspace/intel-AMX/exec/results/glimmer-20261016/leaves/, /home/jhan/workspace/intel-AMX/exec/glimmer-20261016/pfbench/results-20261017.txt, /tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/2286d13f-0c9b-4afd-a521-f1f97342a0e9/scratchpad/pv/pvbench-sk1.cpp.