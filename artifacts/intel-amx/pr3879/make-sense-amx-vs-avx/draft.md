# Making sense of the AMX decode boost - brainstorm draft v2 (Claude, 2026-08-31)

Setting: tron decode, delphi-3bda (2x Xeon 6962P GNR, 512x1GB hugepages, 5-level paging),
model ingested-qwen-3-4b-instruct-2507-tp2 (36 layers, 32 q-heads / 8 KV heads / head 128,
GQA ratio 4 = the AMX shape), software attention. AMX replaces only QK and PV on DENSE 64-token
pages; softmax/rescale/joins, partial pages, and per-token bookkeeping stay AVX/scalar.
All numbers below are measured and cited unless marked est.

## A. The measurement plan (jhan's), refined

Plan as stated: measure attention AMX vs AVX; saving x * 36 layers; fence-to-fence
(F1->F1 or F3->F3) as token time; compute boost %. Sound, with these refinements:

1. x is x(ctx), not a constant: decode attention re-reads the whole KV prefix per token
   (pages per layer per kv_head = ctx/64), so attention time grows ~linearly with ctx while
   the rest of the token is ~flat. Measured attention share of 1u decode: ~14/30/64% at
   ctx 256/2K/8K (rampup/2026-08-19-amx-status.html).
2. "* 36" checks out (qwen_3_4b_instruct_2507.hpp: n_layers=36, uniform geometry), but the
   per-token attention saving is better measured directly than extrapolated from one layer.
3. Denominator choice matters, measured: the same-binary kill-switch arm (TRON_AMX_DISABLE=1)
   runs 2-5pp SLOWER than a clean AVX binary (8u/2K: 43.0 vs 45.1 tok/s; p2-inc2.txt vs
   chart-check.csv), so kill-switch A/B overstates the boost. The authoritative deltas are
   clean-binary vs AMX-binary (tmp/amx-raw-data/chart-check.csv). Keep both: kill-switch for
   same-binary control, clean-binary for the headline.
4. Fences: F1 = return of workers_done.wait() on the scheduler thread (all 70 workers joined,
   after the last host kernel, before wcls); F3 = return of listeners_notified.wait() (logits
   consumed, listeners done). Both are definitive sync points (nothing concurrent across the
   cut); F2 (logits_done) is NOT. Attention lives entirely in [F3 -> next F1]; [F1->F3] is
   wcls/logits/listener work (~5-9% of the token on 3bda) untouched by AMX. So F3->F3 (or
   F1->F1) periods are a valid per-token denominator, and the AMX delta should appear
   exclusively in the [F3->F1] leg - a built-in sanity split. Note: these fences come from the
   tron-perf-fluctuation project (stall-map 3.6, decode-sync-lanes), not definitive-decode.
   Probe recipe exists (tags 7601/7600, RUNBOOK, tron-kvprobe worktree); the AMX branch has
   the fence SITES but no probe stamps yet - no fence data exists on any AMX binary.
5. Much of the headline data already exists (no new runs needed for it):
   clean-binary decode boost, qwen tp2 (chart-check.csv; 8-rep CIs in amx-raw-data/README.md):
   - arena-mirror: 1u/2K +4.5%, 1u/8K +19.6%+/-0.3, 8u/2K +22.8%, 8u/8K +27.8%+/-0.8
   - canonical:    1u/2K +3.8%, 1u/8K +15.3%+/-0.4, 8u/2K +19.0%, 8u/8K +17.7%+/-0.2
   Missing for the curve: ctx between 32 and 2048, ctx > 8192, matched short-ctx pair
   (the ctx32 point has no valid AVX arm), 4u points, and ANY fence-based decomposition.

## B. Q1: why is the boost bigger at larger context?

The premise "boost is constant per token" assumes attention time per token is constant.
It is not; that is the whole answer at first order.

Model: T_avx(ctx) = R + a_avx*ctx; T_amx(ctx) = R + a_amx*ctx + c_tok, where c_tok = per-token
AMX overhead (Q pack, tile config region, save_k scatter of ONE new token ~20us est.).
Boost%(ctx) grows with ctx and saturates at 1 - a_amx/a_avx. With attention at 14/30/64% of
the token (256/2K/8K), even infinite attention speedup caps the token boost at those shares;
the measured +4.5% -> +19.6% (1u, 2K->8K, mirror) is this curve.

Secondary mechanisms, same direction, all now measured:
1. Partial-page dilution: the AMX fast path needs a DENSE page (begin==0, end==64, fully
   visible, inside window); the tail page always falls back to the dotter. Measured share of
   pages taking AMX: 64.4% at ctx32, 92.2% at 2K, 97.8% at 8K (jeremy-measure-20260831/
   counter-summary.txt). qwen sets no sliding window, so the SWA edge is inert here.
2. Per-token fixed costs amortize: Q pack once per (token, kv_head), reused across all pages
   (mirror-build pack = one 1 KB memcpy, 6.3 ns/op rows fn); tile config once per page-range
   (ldtilecfg 182-216 cyc); calls_amx_zero (regions that pack but process zero AMX pages)
   drop from 36.7% of calls at ctx32 to 24.0% at 8K.
3. Bandwidth regime flip favors AMX at long ctx (measured, fused-sweep-v2): cache-resident
   pages=1 the dotter WINS at Nq=1 (422 vs 588 ns/page); RAM-resident pages=16384 AMX wins
   even at Nq=1 (1633 vs 1970 ns) and 2.45x at Nq=8 - the dotter's GFLOPS collapse 77.6->16.6
   going cache->RAM while amxqk only halves. Long-context decode is the RAM-resident regime
   (AVX-arm perf-stat: IPC 0.38-0.52, LLC-miss 51-85% at 1u/8K, p2-perf-decode.txt).

Counterweight (why boost does not keep growing forever): DRAM bandwidth ceiling at high
occupancy - 8u/8K aggregate is 14.5 tok/s AVX -> 18.6 AMX; both arms are far below 8x 1u,
consistent with a shared memory wall (~614 GB/s/socket theoretical). Uncore BW not yet
measured (gap).

## C. Q2: factors beyond the "8x MAC throughput" headline

First, the headline itself does not apply at decode width. Decode GQA group = 4 query heads;
Q occupies 4 of 16 tile rows (rows 4-15 are zero padding), so each TDPBF16PS does useful work
on 1/4 of its output. Measured kernel-grid: M=4 1141 ns vs dotter 1748 ns = 1.53x; the 8x-class
gains appear only at M>=8 (298 ns) / M=16 (276 ns, 1900 GFLOPS) - microbench-quiet.txt.
(Caveat: confirm M semantics in the microbench source before quoting 1.53x as THE decode-shape
kernel gain.) Decode sharing is ~absent: avg visit width 1.022 tokens private 8u (p1-sharing.txt),
so decode cannot ride the M>=8 curve; prefill can (width 110.9).

| factor | direction | measured / mechanism | how to close the gap |
|---|---|---|---|
| tile row utilization 4/16 | hurts AMX | 1.53x at M=4 vs 6-7x at M>=8 (microbench-quiet.txt) | already measured; confirm M semantics |
| instruction count per page | helps AMX | est. static read: AMX ~96 tile ops + ~32 AVX ops vs dotter ~2048 loads + 2048 converts + 2048 FMA (QK); AVX PV already uses AVX512-BF16 dpbf16 so PV gap is smaller | perf stat instructions/uops, AMX arm vs AVX arm (NO AMX-on perf-stat exists yet) |
| bandwidth-bound regime | helps AMX at long ctx | fused-sweep pages=16384: +21% at Nq=1, 2.45x at Nq=8; AVX IPC 0.38-0.52, LLC-miss 51-85% | uncore DRAM BW during 1u vs 8u serving |
| frequency license | hurts AMX ~8% core / ~4% service est. | 3.59 vs 3.89 GHz sustained AMX, package power flat (p0c-freq-power.txt); rampup: license grants ~500us, <15% TMUL util may keep clocks up - decode issues TDPs sparsely | APERF/MPERF + CORE_POWER.LVL*_TURBO_LICENSE during real decode, both arms (not measured in serving) |
| save_k scatter tax | hurts AMX (mirror) | 70.9 ns/row measured (bench-scatter); 36 layers x 8 kv_heads = 288 rows/token ~ 20 us/token est., on RX workers (per-layer critical chain) | RX-worker span timing per arm |
| dTLB: mirror in 4KB pages vs canonical in 1GB hugepages | hurts AMX (mirror), unmeasured | mirror arena = ::operator new[], no madvise; 16 KB plane spans 4 pages; 5-level walks; AVX-arm dTLB-miss ~0 because KV is hugepage | dtlb_load_misses.walk_completed/pending per arm; /proc/pid/smaps THP state; optional madvise(THP) experiment |
| extra copies on AMX path | hurts AMX (small) | qk_s->s_pages 1 KB memcpy + amx_o scratch copies per page; tile stores write 16 rows for 4 useful | included in kernel wall times already |
| softmax/rescale floor | caps boost | identical scale/max/exp/rescale code both arms (self_attention.hpp:1642-1710) | cycle split inside apply_page_tok (trace spans; listed as not-done in 04-amx-action-plan) |
| mirror RAM footprint | deployment cost | kv_bytes/2 ordinary RAM, outside all gauges; bound 256 GB est. on 3bda | FUSE gauge k_mirror_arena_bytes |
| allocation / dealloc | ~neutral | arena once per book, nothrow new, first-touch commits at first scatter; no per-token alloc either arm | page-fault count on first decode after book creation |
| numerics | not perf | dd/ campaign: OFF-vs-ON token flip at token 22 = exact-tie resolution, no bug; A/A byte-identical | done |

## D. Proposed campaign (delphi-3bda, campaign_guard_acquire, outside CI)

P1. Fill the ctx axis with clean-binary pairs: {256, 512, 1K, 4K, 16K} x {clean-AVX, AMX-mirror},
    1u and 8u, 8 reps - completes the boost%(ctx) curve whose endpoints exist.
P2. First AMX-ON perf-stat round (none exists): instructions, cycles, IPC, LLC-misses,
    dTLB walk events, APERF/MPERF, at 1u/8K and 8u/8K, both arms, attention-worker cores only.
P3. Fence campaign on the AMX branch: stamp tags 7601/7600 (recipe in RUNBOOK), measure
    F3->F3 period and the [F3->F1] vs [F1->F3] split per arm at 2-3 contexts. Prediction to
    falsify: the whole AMX delta sits in [F3->F1]; [F1->F3] flat.
P4. did_amx/fallback counters already exist in the tron-dd binary - carry them into the
    perf-round harness so every future round reports AMX page coverage.
P5. Optional: madvise THP on the mirror arena, re-run P2 - isolates the dTLB factor.

## Questions for GPT-5.6-Sol (validate/refute, name what I got wrong)

S1. Is the linear model in B (T = R + a*ctx, boost saturating at the attention share) the right
    first-order story? Anything material it hides (e.g., paging of KV across NUMA, prefix cache)?
S2. Ranking of B's secondary mechanisms - is the bandwidth-regime flip (B.3) real or an artifact
    of the fused-sweep methodology (streaming 16K pages vs decode's scattered page walk)?
S3. Any factor missing from C that moves AMX-vs-AVX on Granite Rapids specifically (e.g., AMX
    power-license behavior under sparse TDP issue, tile-load bank conflicts on the VNNI mirror
    layout, uncore/mesh effects of the extra mirror-resident footprint)?
S4. The kill-switch arm runs 2-5pp slower than a clean binary (code-layout effect measured in
    p2-inc2b-decomp). For the public boost claim, is clean-binary-vs-AMX the right comparison,
    and what is the cleanest way to report both without confusing readers?
S5. For P2, which exact GNR perf events give the least ambiguous AMX-vs-AVX attribution
    (tile uops, license residency, dTLB walk duration under 5-level paging)?
S6. Fences: any flaw in using F3->F3 as the per-token denominator given wcls prep precedes F1
    and the listener enqueues the next extend before its F3 countdown (documented caveats)?
