# AMX execution queue (per rampup/04-amx-action-plan.html)

Status file for the AMX work. Updated by Claude as tasks run. All times UTC.

## Isolation rules (user directive, 2026-08-18)
- ALL AMX changes live in separate git worktrees, never in ~/workspace/tron (main checkout):
  - `~/workspace/tron-pr2934-reconciled` — byte-verified Aug-3 measured PoC tree
    (main 96e2bdce + 24 files, sha256 24/24 OK). Read-only reference + P0 challenger.
    Builds into its own `gen-delphi/`.
  - `~/workspace/tron-amx` — branch `jhan-amx-p0`, our new AMX code. Empty so far.
- delphi-3bda usage:
  - Nightly CI window (user-confirmed 2026-08-18; the earlier note here had it
    BACKWARDS): **prep starts 03:30 UTC (20:30 PDT), normally done by 09:30 UTC
    (02:30 PDT)**. No AMX work in it. Also: `ci-runner-stop@delphi-3bda.timer`
    fires daily at 02:45 UTC ("stop runner + inference up") - production
    inference may come up then; `ci-runner-start@` (14:00 UTC, "inference down
    + start runner") is disabled. USER-CONFIRMED 2026-08-19 (twice): the usable
    window extends to CI prep at 03:30 UTC - do not stop at 02:00. Practical rule:
    keep working until ~03:15 UTC; at 02:45 check whether the timer brought
    rinzler serving up and yield the measurement cores if it did.
  - Outside CI, the machine runs production inference: 4x rinzler (user positron),
    ~120 physical cores busy. Only ~4 physical cores fully idle (both HT threads):
    89, 94, 96, 108 (sampled 2026-08-18 05:20Z; re-sample each night).
  - AMX builds: pinned to fully-idle cores only, nice 19. AMX benches: single
    fully-idle core. NEVER on lone HT siblings of serving cores.
  - No system changes on 3bda (no BIOS/MSR/prefetcher/SNC/hugepage changes).
    File artifacts only, in the worktrees + ~/workspace/intel-AMX/exec/.
  - CI-BUSY DETECTION (AUTHORITATIVE as of 2026-08-19, Rhys's systems_test
    PR #180, confirmed by jhan): /run/lock/systems-test-ci.lease on the DUT.
    Busy ONLY if file exists AND state=="busy" AND now < expires_at_epoch;
    otherwise CI is not holding - rinzler cleanup, hugepage cleanup, and FPGA
    claiming allowed. Clock windows (prep ~03:30Z, done ~09:30Z) are ADVISORY
    only from now on: the lease says "holding now", not "starting soon", so
    long campaigns re-check between runs. USE exec/lib-guard.sh in every
    campaign script: campaign_guard_acquire (lease + cross-session flock
    /var/tmp/jhan/3bda-campaign.lock + no-runtron guard), ci_took_dut between
    runs, wait_for_ci_release. Live-tested 2026-08-19 (lease-absent + flock
    paths); the lease's exact on-disk format to be verified against tonight's
    nightly (parser tolerates JSON and key=value).
  - CROSS-SESSION COORDINATION (adopted 2026-08-19 from the trace-sync-points
    session): the flock + launch guard above; both peer sessions informed of
    the lease protocol 2026-08-19. lib-guard.sh v2: the campaign flock now uses
    a DYNAMICALLY allocated fd (a hardcoded fd 9 collided with the peer's
    harness - their catch); 3bda handed to trace-sync-points for their ~45 min
    campaign evening 08-19 (nothing of ours running; our only scheduled touch
    is the read-only 04:00Z lease-format probe).
  - /home is NFS-shared between alpha and 3bda; full tron builds are impossible
    on alpha (nix blocked in claude-box), so builds run on 3bda under the rules above.

## Task queue
| # | Task (action-plan ref) | Status | Notes |
|---|---|---|---|
| 1 | Reconstruct measured PoC tree (P0 challenger) | DONE 2026-08-17 | sha256 24/24 OK |
| 2 | Create AMX dev worktree `tron-amx` @ `jhan-amx-p0` | DONE 2026-08-18 | |
| 3 | Build amx_microbench from reconciled tree on 3bda (idle cores, nice 19) | DONE 2026-08-18 05:32Z | 149 targets, clean |
| 4 | Single-core microbench sweep on idle core 96 | DONE 2026-08-18 05:32Z | results: exec/results/p0-night1-microbench.txt. Key: AMX v2 = 263-271 ns/page at ALL M (1990 GFLOPS at M=16 = modeled peak); dotter M=4 1762 ns -> raw AMX kernel is 6.5x at width 4 WITH pre-packed K; dispatch M=4 routes blocked-avx (1142 ns, 1.54x); dispatcher overhead ~19% in scalar buckets. Width-4 question is bookkeeping/pack/transpose, not the TDP kernel. CAVEAT: dormant rinzler threads are placed on all CPUs incl. 96 (see placement-check-20260818.txt) - numbers look clean (peak reached) but final P0 numbers need the quiet slot. |
| 5 | P0 baseline qwen-3-4b-tp2 trace, USE_HW_ATTN=0 | DONE 2026-08-18 17:21Z (slot granted by Rhys; machine cleaned: rinzler stopped, orphaned hugepage slices removed after fuser check). Results: results/slot1/ (qwen-baseline-swattn.txt, p0-baseline.html [moved to rampup/ 2026-08-19], 127MB perfetto trace u8/ctx2048, microbench-quiet.txt, occupancy.txt). KEY: 1u decode 251/203/106 tok/s at ctx 256/2K/8K; 8u/8K aggregate collapses to 116 tok/s; context-linear (attention-shaped) share of 1u decode ~14/30/64% (est.) - attention compute IS the qwen decode wall at long context, unlike gpt-oss. | qwen-capable runtron BUILT 2026-08-18 15:03Z from current main 1407f48dd in ~/workspace/tron-amx/gen/ (sha256 1db68a83..., 713 MB, "qwen plugin present"). User pinging CI team for a ~2h slot (rinzler down, 2 FPGAs). Serving lifecycle owned by positron nightly automation via platformd config patches (traced 2026-08-18). |
| 6 | P0 symmetric clean-main vs reconciled-PoC pairs (A2) | BLOCKED: same slot as #5; also note reconciled tree is June main (pre-qwen) - qwen A/B requires P2 kernels on current main; the #6 pair covers llama/gpt-oss shapes only | |
| 7 | P0 fused-page: OUR formulation | LARGELY DONE 2026-08-18: src/amx_fused_bench.cpp in tron-amx (self-contained, self-validating, rel err 8e-5). Sweep (results/slot1/fused-sweep.txt): width crossover Nq~3; at guaranteed width 4: 1.22-1.37x vs AVX fused (positive in L2/L3/DRAM); Nq=16: 2.8-3.3x; **4+4 blocking beats 6+2 consistently -> adopted (A8.3 verdict)**; Nq<3 stays AVX (dispatcher bucket confirmed). Epilogue (transpose/softmax/pack/rescale ~1000ns of 1300 at Nq=4) is now the optimization target. UPDATE 2026-08-18 later: mirror-orientation variant (amxqk) measured - whole-path 694ns vs our 1263ns at width 4 (kernel-level verdict favors mirror orientation; store->load hazard on our S^T round-trip is the cause). Epilogue opts added (rescale-skip, merged transpose+scale, width-specialized transpose). Grid v2 DONE (all 4 variants, 0 failures) -> results/slot1/fused-sweep-v2.txt + fused-sweep.html: mirror orientation wins everywhere (width 4: 686/1470/1800 ns = 2.36x/1.68x/1.77x vs AVX at L2/L3/DRAM; width 16 up to 5.5x; crossover Nq=2). Formulation decision still needs mirror system costs (RX-worker save_k write, +50% K capacity, defrag). Pipelined epilogue (amxpl) MEASURED: only ~2% (982 vs 1006 ns, width 4, 8-page ring) - stall self-amortizes with alternating buffers; residual gap to mirror ~300ns (982 vs 686; earlier "~200ns" was an arithmetic error, corrected 2026-08-19) - transpose + score traffic expected to account for much of it, not isolated. Formulation decision now rests on mirror system costs (P2 system-level runs). REMAINING: license/power capture (P0(c)). |
| 8 | P1 sharing instrumentation counters | DONE 2026-08-19: p1_share_counters.hpp + apply_page_range hooks (flag-gated); measured on 3 qwen workloads (results/slot1/p1-sharing.txt): prefill avg width 110.9 (99.9% work shared); private decode 1.02 (GQA-only, as predicted); shared-system-prompt decode 5.06 with 87.6% of work at width 8. P4 verdict: justified for shared-prompt + prefill; not for private decode. | |
| 9 | Live placement check (`ps -eLo pid,psr,comm`) + BIOS L2-AMP recording | placement DONE 2026-08-18 (results/placement-check-20260818.txt); BIOS recording needs root - deferred to the quiet slot | rinzler/platformd threads placed across nearly all CPUs incl. dormant ones on "idle" cores |
| 10 | Lifecycle strict-vs-lazy, PV 4+4-vs-6+2, license/power capture | PV blocking DONE (4+4 adopted); license/power DONE 2026-08-19 (AMX = 3.59 vs AVX 3.89 GHz on-core, ~8% license cost, already inside the grid numbers; pkg power flat at 1-core scale; many-core -> T4). Lifecycle strict-vs-lazy still open (needs in-tree context). **P0 COMPLETE.** | |
| 11 | P2 inc-1: AMX QK in real apply_page_tok | DONE 2026-08-19, same-binary A/B: +2.8%/+6.1%/+8.9% decode (1u2K/1u8K/8u2K), results/slot1/p2-inc1.txt | |
| 12 | P2 inc-1b: PV on AMX in same seam | DONE 2026-08-18 22:23Z, same-binary A/B (3 reps, zero failures, results/slot1/p2-inc1b.txt + p2-inc1b.html): decode +4.4%/+12.0%/+16.9% (1u2K/1u8K/8u2K; inc-1 QK-only was +2.8%/+6.1%/+8.9% - PV roughly doubled it as modeled); prefill +44.7%/+102.0%/+41.6% (inc-1 was +15.8%/+28.3%/+13.6%; 8K prefill now 2.0x: 521->1054 tok/s). OFF baselines reproduce inc-1's within 0.5% -> kill-switch A/B stable. | pv_128x4 in amx_attn.cpp (4+4 blocking, 2 halves x 2 k-steps; P zero-padded to 16 rows; output buffer must be 16x128 - tile stores write all 16 configured rows); v_base()/v_data() in kv_cache.hpp; AMX epilogue branch in apply_page_tok. Numerics (CORRECTED 2026-08-19 after Jeremy's precision question): BOTH paths round PV weights to bf16 - AVX scaled_v_expr truncates fp32->bf16 (srli 16, kv_cache.hpp:1795-1800) and multiplies with VDPBF16PS; AMX rounds-to-nearest-even (VCVTNE2PS2BF16). Both attention dot-product paths are bf16-in/fp32-accumulate; for finite non-subnormal values the expected A/B deltas = weight rounding mode + fp32 reduction order (doc 02 sec 6b, Sol-reviewed ENDORSE-WITH-EDITS applied). T1 judges (see row 14 for t1-quick outcome). Chunk-size #error guard rebuild verified clean (sha 9e5df5dd). VERIFIED 2026-08-18 ~23:10Z by 3-agent adversarial check: all published numbers recomputed OK (2 wording fixes in the chart page: spread = 1.1% peak-to-peak worst cell; runs generate 253 tokens, not the 256 requested); PV tile indexing re-derived independently - all 8 B-tile loads, token pairing, strides, and output stores CONFIRMED; one hazard fixed: self_attention.hpp now #errors if TRON_AMX_DISPATCH is built with TRON_CHUNK_SIZE != 16 (chunk-8 V is not pair-interleaved, would silently pair wrong tokens) |
| 13 | P2 inc-2: mirror orientation + system costs | DONE 2026-08-19 00:45Z (code + smoke + full 18-run suite same night; results/slot1/p2-inc2.txt + p2-inc2.html). Decode +0.1/+3.7/+5.2% over inc-1b -> total +4.5/+16.1/+23.0% over AVX (8u agg 358->441). Prefill +1.0-2.0% over inc-1b NET of the RX save_k write-through. Canary: mirror greedy output byte-identical to canonical-AMX (same head-dim sum order). COSTS: AVX fallback on mirror build -3.8/-7.8/-3.9% (fatter blocks hurt locality even with writes gated off); KV capacity -1/3 (48 vs 32 KB per block-page, arithmetic). DECIDED (Sol consensus ENDORSE-WITH-EDITS 2026-08-19): canonical-K = supported default; mirror = opt-in for pinned AMX deployments tolerating -33% KV capacity; mirror's kill switch is NOT a baseline rollback (document as such). 1u/2K mirror delta = parity (rep ranges overlap; worst cell spread 1.15%). Opt-in maturity gated on rows 14-16. Binaries: mirror 02b81206, inc-1b preserved gen/runtron.inc1b |
| 15 | mirOFF fallback-penalty root-cause decomposition | SUITE DONE 2026-08-19 01:11Z (results/slot1/p2-inc2b-decomp.txt; layout-only build = TRON_AMX_K_MIRROR_LAYOUT_ONLY, sha 8cfac55e); decode-phase perf counters running | LAYOUT CONFIRMED as the penalty carrier: layout-only OFF = -3.7/-7.6/-4.0% vs canonical (mirror OFF was -3.8/-7.8/-3.9% - identical within noise). NEW KEY FINDING: layout-only ON (canonical AMX kernel on 3-plane layout) = -1.3/-9.2/-8.1% vs inc-1b -> the fat layout hurts the AMX path too, so the mirror KERNEL's true same-layout gain is ~+14% at 1u/8K and 8u/2K (126.5 vs 110.8; 440.6 vs 384.9) - masked to +3.7/+5.2% net by the layout cost. Implication: shrinking the layout cost could unlock most of the remaining ~9%. COUNTERS (decode-phase-only, sudo perf attach, 15s inside 1u/8K decode, results/slot1/p2-perf-decode.txt): LLC-load miss rate 50.8% (canonical) -> 84.6% (3-plane); instructions retired -26% in equal wall time (IPC 0.52->0.38); dTLB-load-misses ~0.00% BOTH arms -> TLB RULED OUT; verdict = cache/prefetch locality (dead 16KB mirror plane between every K/V block breaks prefetch streams). MITIGATION CANDIDATE (queued design change for mirror maturity): move k_vnni OUT of kv_block into a parallel arena - restores dense 2-plane K/V (fallback penalty should vanish) and makes mirror memory allocatable only when AMX is on. perf_event_paranoid=4 on 3bda: user perf blocked; sudo -n perf attach works (read-only, no system change) |
| 16 | Mirror capacity-adjusted behavior | 8u/8K point DONE 2026-08-19 01:47Z (results/slot1/p2-8u8k.txt, 2 reps, spreads <=0.2%): canonical 114.4->136.4 (+19.2%); mirror 109.5->146.9 (+34.1% own-baseline; +7.7% vs canonical-AMX; +28.4% total vs canonical AVX); prefill per-user 65.4->130.7 (2.0x); fallback penalty -4.3% at this load. Mirror edge GROWS with attention share: +3.7% (1u8K) -> +5.2% (8u2K) -> +7.7% (8u8K). REMAINING: max users at fixed KV budget, allocation-failure/eviction behavior, latency near capacity - still required before mirror opt-in is production-ready | Recon (Explore agent, file:line verified): K store = ONE site (model.hpp:2778 in save_k_impl; RX-worker Wk callback via llama.hpp:918-925 rope_k -> save_k). Block size hard-coded in TWO formulas (kv_cache.hpp:524-538 make_kv_slot_offsets "2*64*sizeof(bf16)*head_size"; :1011-1017 static_assert 2*page_size*head_size) - mirror = 3x. ALL page moves funnel through copy_storage_slot (kv_cache.hpp:1589-1620) <- copy_from <- book::append <- _defrag_books (full.hpp:1158-1198): defrag mirror rebuild = ONE site (regenerate mirror from dst canonical K after the memcpy - always coherent). K mirror pairs adjacent DIMS (not tokens like V) -> per-token writes independent, no even/odd cross-token coupling. Plan: TRON_AMX_K_MIRROR compile flag (default OFF, requires TRON_AMX_DISPATCH); kv_block member k_vnni[head_size/2][page_size][2]; set_k_mirror after canonical store; rebuild in copy_storage_slot + fill_storage_slot; qk_mirror_128x4 kernel (from harness amxqk variant, no transposing store); byte-equivalence test (doc03 A7). Measure: decode gain vs inc-1b, prefill parse rate (direct proxy for RX save_k write cost), n_pages capacity loss |
| 14 | T1 logit-tolerance + T2/T3 test obligations | QUEUED (before any enable-by-default). A7 byte-equivalence DONE 2026-08-19 01:18Z: t/t_amx_mirror.cpp (24576 assertions: exhaustive index map both head sizes, scrambled write order, single-token rewrite isolation) + mirror-coherence checks in t_llama_unit append test (8463 assertions, covers fill_random + defrag rebuild) - ALL PASS on the layout-only config (identical set_k_mirror/copy code as the mirror build; system-level write-through equivalence already shown by the byte-identical canary). Also fixed t_llama_unit's hard-coded 2-plane dma_size_bytes assert -> detail::kv_block_planes. T1 MACHINERY FOUND 2026-08-19 02:05Z: tron already has golden-logit tests - t/force_generate records per-step logits; check_golden_logits applies a PREDECLARED criterion (TVD <= 0.05 vs HF-reference goldens from bin/extract_logits, outlier cap 0.3 at <=10%, top-5 overlap >= 3) - exactly Sol's T1 spec. Goldens present on 3bda (/scratch/test/data, hash-addressed). NO qwen goldens yet (needs bin/extract_logits on qwen HF weights - queued); llama-3.1-8b has goldens AND the AMX fast-path shape (head 128, GQA 4) - t_generate_ingest_1_llama running AMX-off/on as the first formal T1 signal (caveat to verify: AMX engages only on full 64-token pages, so the test's prompt must be >= 64 tokens for the arms to differ). VERIFIED HOLLOW: the canned prompt is 21 tokens (read from the token file header) - both arms passed trivially, AMX never ran. FIRST REAL T1 SIGNAL 2026-08-19 01:52Z (t/t_amx_logit_ab.cpp + compare_logits.py; results/slot1/logits-sw-{off,on}.bin): llama-3.1-8b, 192-token forced generation, USE_HW_ATTN=0 (REQUIRED - without it decode attention runs on FPGA and both arms were bit-identical, a clean negative control: logits-{off,on}.bin). AMX-vs-AVX per-step logits: argmax agreement 190/192; both flips at near-ties (margins 0.031 and 0.000000=exact tie, vs median margin 0.266); worst abs logit delta 0.25. Flips confined to no-preference cases = healthy numerics per Sol's spec. T1 EXTENSION DONE 2026-08-19 15:15Z (results/t4/t1-ext.txt + t1ext-*.bin; goldens f396b61c/14b09da2 and 0425dd37/ce40ff96): prompts 2 (technical, 240 steps) and 3 (narrative, 568 steps) on qwen - AMX-vs-AVX max TVD 0.033 and 0.047, median 0.0000/0.0062, ZERO outliers both. CUMULATIVE T1 (3 prompts, 956 aligned steps): AMX-vs-AVX max TVD 0.054, 1/956 steps over 0.05 -> comfortably inside the repo criterion; both arms remain at IDENTICAL distance to HF (known-issue gap, median 0.09-0.14, consistent). Remaining per Sol gate 1: batching variations + formalize the predeclared criteria. extract_logits mechanics: python shim -> uv-run frontend "tron-reference-logits"; WORKS on 3bda (llama-GPTQ path blocked: venv lacks optimum; non-quantized models fine). T1 FIRST FULL PASS DONE 2026-08-19 02:0xZ vs HF fp32 REFERENCE, ON QWEN (Qwen3-4B-Instruct-2507 HF weights at /opt/positron/weights/huggingface/Qwen/; goldens /scratch/jhan/t1-goldens: tokens 49e8c59b, logits 77c87165, 192-token forced sequence from exec/t1-prompt.txt; --max-tokens TRUNCATES so must be 192, first attempt at 64 gave zero full pages): 148 aligned steps, vocab 151936. AMX-vs-AVX: max TVD 0.054, median 0.0000, 1/148 over 0.05 -> PASSES repo criterion (cap 0.3, <=10% outliers). BOTH arms vs HF: IDENTICAL distance (max TVD 0.7139 both; outliers 117 vs 116/148; argmax-vs-HF 126/148 both) -> AMX ADDS NO ERROR on top of tron's existing HF distance; the absolute tron-vs-HF gap (median ~0.11) is engine-level or row-alignment convention, identical in both arms - KNOWN ISSUE, NON-BLOCKING (positioned by jhan 2026-08-19): pre-exists AMX, does not gate AMX enablement, no human decision required; recorded for whoever works on engine-vs-HF fidelity later. Tools: t/t_amx_logit_ab.cpp (AMX_MODEL/AMX_TOKENS/AMX_LOGIT_OUT envs), scratchpad tvd_compare.py; dumps results/slot1/qwen-logits-{off,on}.bin. NOTE: mirror-kernel arm expected bit-identical to canonical-AMX arm (same summation order; token canary already byte-identical) - not separately dumped | t1-quick precursor DONE 2026-08-18 22:44Z (results/slot1/t1-quick.txt + t1-quick/): with --temperature 0 -s 42 --pay-for-determinism the AVX path is run-to-run byte-identical (control passes; default sampling is random - flags required for any token diff). AMX greedy output: byte-identical at ctx 8192; ONE argmax flip ~20 tokens in at ctx 2048 (continuations then diverge by construction). One prompt per context = sample, not verdict. Formal T1 must compare logits and near-tie margins. NOTE: extract generated text via the green ANSI chunks, not line filtering (ASLR addresses + mid-line log continuation gave a false DIFFER first) | |
| 17 | Kill-switch A/B on the OTHER gate-passing families before any default flip: llama-3-8b, mistral-7b, ministral-8b, mixtral-8x7b, phi-4 (granite-3.3-8b once its plugin is end-to-end). Geometry audit 2026-08-19 (jhan question): gate = head_size==128 && kv_mul()==4 (self_attention.hpp); 8 of 30 registry families match; only qwen-3-4b + llama-3.1-8b measured; tp1/2/4 NOT part of geometry (model-level constants). Documented: pr-rampup.html section 4.1 | machine slot | QUEUED (mixtral covered by row 18) |
| 18 | CI-model A/B round (jhan 2026-08-21, from the nightly-CI list): triage per the dispatch gate - SUPPORTED+UNTESTED: mixtral-8x7b-instruct-v0.1-tp2 @8u ONLY. Excluded: llama-3.2-3b (kv_mul 3, llama.hpp:1540), llama-3.3-70b tp2@8u/tp2@4u/tp4@4u (kv_mul 8; 3.3 rides the llama_3p1_70b config, llama.hpp:1538), qwen-2.5-32b-it (kv_mul 5, llama.hpp:1548); llama-3.1-8b-tp2 removed as already tested (t4-shapes: +15.0/+19.7% decode; CI's "instruct-good" GPTQ variant differs in weights only, same geometry). Script exec/p2-ci-models.sh LAUNCHED 2026-08-21 06:56Z detached on 3bda: waits 09:30Z + quiet check + rinzler cleanup + campaign_guard_acquire, then 3 arms (arena-kill-switch baseline / canonical inc1b / arena-mirror) x ctx {2048,8192} x 3 reps at 8 users, USE_HW_ATTN=0 -> results/ci-models/mixtral-ab.txt, marker logs/p2-ci-models.done. Weights verified present (mistralai/Mixtral-8x7B-Instruct-v0.1). | DONE 2026-08-21 09:52Z, zero failures | MEASURED (per-user decode avg at 8u, vs kill-switch baseline): ctx 2048: canonical +2.3%, mirror +1.2% (33.9 -> 34.7 / 34.3 tok/s; deltas at 2K are small and canonical-vs-mirror ordering is within rep noise); ctx 8192: canonical +9.4%, mirror +18.6% (23.1 -> 25.3 / 27.4). Prefill: ctx 2048 +2.2%/+1.2%; ctx 8192 +56.4%/+55.2% (95.4 -> ~149 tok/s/user). Pattern matches the attention-share model: MoE FFN dominates at short ctx; gains concentrate at 8K; mirror edge is decode-side (prefill parity canonical~mirror). Geometry gate confirmed on a 4th family (32Q/8KV/128, same as llama-3.1-8b). |

## CAPACITY FRAMING CORRECTED + GATE 3 FIRST DATA (2026-08-19 15:40Z, results/t4/cap-sweep.txt)
The arena mirror allocates from ORDINARY RAM (operator new; 32GB on this config, machine has
1.58TB), NOT from the hugepage/DMA budget that sets the KV page count -> by construction the
arena build's PAGE CAPACITY EQUALS CANONICAL'S. (Corrects the "-33% pages on AMX hosts" line
in the data sent to Sol's revision round - that penalty belonged to the in-block design only.)
VERIFIED BEHAVIORALLY: canonical and arena-mirror both admit 32u AND 48u at ctx 8192
(48u ~= 58GB KV vs the 64GB budget - the edge where the in-block mirror's ~36u ceiling would
have failed), failed=0, zero alloc-failure lines; arena-mirror FASTER at the edge (48u wall
442.6s vs 459.1s; aggregate decode 107.0 vs 100.9 tok/s = +6.0%; per-user min/p50/p95 all
slightly better, same distribution shape). Beyond-budget probes: 56u x ctx8192 (~99% of the 64GiB cache) COMPLETED
CLEANLY on both builds (failed=0, all 56 in flight; arena-mirror wall 520s vs canonical
539s). 64u: BOTH builds completed all 64 cleanly (failed=0, all in flight; arena-mirror
wall 594.2s vs canonical 614.9s = -3.4%, mirror faster at every load point: 32/48/56/64u).
HONEST NOTE: no admission failure was reached - my ~54u budget arithmetic was wrong; the real
limit is beyond 64u at ctx 8192 (verify per-token-KV/budget in the book-sizing code before
claiming failure semantics).
Then mixed-context workloads remain.

## Formulation end-state (Sol consensus, revision round 2026-08-19: KEEP-CURRENT for now)
Target once gates pass: arena-mirror DEFAULT on AMX hosts with sufficient KV headroom;
fail-soft to canonical/AVX; kill switch retained; canonical = mature compatibility +
constrained-memory fallback. The five gates: (1) T1 extension, predeclared criteria,
more lengths/batching/shapes; (2) T2/T3 true fallback paths (non-AMX host, runtime-disabled,
arena alloc failure, lifecycle, defrag); (3) [REVISED by Sol 2026-08-19 after the arena capacity data: page-capacity parity is
demonstrated] ordinary-RAM headroom + safe admission/eviction behavior BEYOND the page
budget (never reached: 64u still fit) + mixed-context coverage + verify the mirror arena's
NUMA placement (plain operator new rides the default policy, unlike the NUMA-pinned KV
arena - flagged from jhan's DRAM-cost question 2026-08-19, unverified as a non-cost); (4) [REMOVED from this session's tracking 2026-08-19: remote task handled elsewhere, per jhan]; (5) T4 replication with
confidence intervals + llama/gpt-oss shapes.

## Rinzler policy (user directive 2026-08-18)
Lingering rinzler@0-3 after the nightly is a BUG (Rhys to fix), not machine state to restore.
Until fixed, after CI/nightly completes: check for running rinzlers and clean them up -
(1) confirm zero sessions in journal for ~10 min, (2) sudo systemctl stop rinzler@{0..3},
(3) rm /dev/hugepages/slice-*-of-8 only after fuser confirms no open handles.
NEVER restart them; hand-back is Rhys's side.
NOTE (2026-08-19, refined after the peakbw handback): slice-*-of-8 hugepage files are
rinzler-style working files - when serving is ACTIVE they are mapped by live processes
(fuser shows handles): LEAVE THEM. Our runtron tp2 campaigns also create slice-0/1-of-8;
after a campaign, remove only what fuser shows unmapped AND only when serving is down.
MACHINE-STATE NOTE (22:40Z 08-19): the trace-sync-points peakbw harness restored LIVE rinzler
serving after its campaign (its own stop-and-restore design - distinct from jhan's
never-restart rule, which governs OUR post-CI cleanup of lingering rinzlers). lib-guard.sh v3:
campaign_guard_acquire now also refuses when rinzler serving is active unless the caller
passes --allow-serving (for scripts that implement stop-and-restore).

## Guard rails baked into night scripts
- `ci_guard` (corrected 2026-08-18): start no new run in [02:00, 21:00) UTC -
  clear of the 02:45 UTC inference-up timer and the 03:30 UTC CI prep start.
  (The old "stop by 13:30 UTC" guard was based on the backwards window note.)
- Completion marker: exec/logs/p0-night1.done (ok | guard-stop | configure-failed | build-failed).

## Needs user coordination
- NOTHING (as of 2026-08-19 02:45Z). Standing authorization from jhan: no Rhys
  coordination needed for quiet slots - every morning after the nightly CI window
  (normally done by 09:30 UTC / 02:30 PDT), verify CI is done, clean leftover
  rinzlers per the rinzler policy above, and use the machine.
- T4 FIRST PASS DONE 2026-08-19 10:26Z (self-serve worked: window reached 09:30:58Z,
  machine already quiet at 09:31:05Z; ran 55 min; results exec/results/t4/, marker ok,
  165 timing lines, zero failures). TRUE SYMMETRIC 3-BINARY SUITE (clean = all AMX
  flags OFF, sha recorded; 3 reps): decode vs clean - canonical +3.8/+15.2/+19.0/+17.5%,
  mirror +4.5/+19.8/+22.6/+26.6% (1u2K/1u8K/8u2K/8u8K); prefill - canonical up to
  +102.7%, mirror up to +105.2%. Clean binary reproduces the original P0 baseline
  (105.6 vs 106 at 1u/8K; 204 vs 203 at 1u/2K) -> the kill-switch arms used all week
  sat within 0-3% of true clean (dispatch-off overhead ~zero; 1u/8K kill-switch arm ran
  3% ABOVE clean - code-layout scale noise, favors conservatism in our reported gains).
  CAPACITY: 16u and 24u at ctx 8192 all completed, failed=0 on BOTH binaries (24u/8K
  ~44GB KV, inside even the mirror budget); aggregate saturates past 8u (KV-traffic
  wall): 16u 74.0 vs 78.4, 24u 72.2 vs 76.5 (mirror +6% held at saturation).
  POWER STAGE DONE 2026-08-19 14:07Z (retry with --Summary; results/t4/t4-power.txt,
  busy-sample averages at 8u/8K): idle pkg 423W (2 sockets); clean 543.2W @ Bzy 3759MHz,
  113.4 agg tok/s (4.79 J/token); canonical-AMX 551.8W (+1.6%) @ 3608MHz (-4.0% clock),
  134.7 tok/s -> 4.10 J/token (-14.5%); mirror-AMX 545.1W (+0.3%) @ 3611MHz, 145.2 tok/s
  -> 3.76 J/token (-21.6%). VERDICT: package power essentially flat; the many-core license
  clock cost is ~4% (milder than the 8% single-core pure-AMX case); AMX CUTS energy per
  generated token by 15-22%. SHAPE COVERAGE DONE 2026-08-19 ~16:00Z
  (results/t4/t4-shapes.txt, arena binary, kill-switch A/B, 2 reps): llama-3.1-8b-tp2
  (eligible shape) decode +15.0%/+19.7% (1u8K/8u2K), prefill +89.6%/+29.2% - qwen gains
  GENERALIZE; gpt-oss-20b-tp2 (ineligible shape) -0.3..-1.6% all cells = NO REGRESSION when
  the fast path does not engage (dispatch is free when it does not fire). T4 REPLICATION DONE
  2026-08-19 ~18:30Z (results/t4/t4-reps.txt; campaign lock used, first time): 8 reps/cell,
  CV 0.1-0.7%; decode vs clean with 95% CI - canonical +15.3%+/-0.4 (1u8K), +17.7%+/-0.2
  (8u8K); arena-mirror +19.7%+/-0.3, +27.8%+/-0.8. All CIs exclude zero by wide margins.
  GATE 5 COMPLETE (shapes + replication).

re-check ci_took_dut between long runs.
LEASE FORMAT VERIFICATION: COMPLETE 2026-08-21 (exec/logs/lease-watch-20260821.log, 20-min
samples 03:30-09:30Z). BUSY format captured for the first time - JSON, exactly what the parser
expects: {"state":"busy","owner":"system_ci","lease_id":"<run>-<attempt>",
"updated_at_epoch":...,"expires_at_epoch":...,"github_run_id":...,"github_run_attempt":...}.
Writer refreshes ~every 20 min; expires_at_epoch = updated + 900 s (15-min TTL, so a crashed
CI fails open within 15 min). The nightly finished early (~07:0xZ) and REMOVED the file on
completion - the ABSENT/fail-open case re-verified in the same window (7 ABSENT samples to
09:30Z). Both parser paths now verified against live CI; lease-based scheduling is trustworthy;
no Rhys question needed. The PR #180 writer is deployed and behaving as designed.

## R0 — MoE router P0 (option c plan, router/02-option-c-plan.md sec 3)
STARTED 2026-08-23 ~22:00Z (session intel-amx-a3). Worktree ~/workspace/tron-router-p0,
branch jhan-router-p0 = main 1407f48dd + router perfetto markers (commit 3b0234df6:
await-deps/launch slices per generated matmul launcher, per-kernel first-wait slice,
wait-indices slice, start_reading/start_writing slices on top-level blocking channel
waits, debug_label on driver "Launch hardware matmul job"). Ingest traces copied from
tron-amx (read-only inputs). Build: r0-build.sh, marker ok 22:01Z; runtron includes
ingested-gpt-oss-20b-tp2 AND ingested-gpt-oss-120b-tp2.
G0 statistics PRE-REGISTERED before any capture: exec/results/router/G0-preregistration.md
(gate variable = driving-thread logits-stall sum, NET of P0b CPU cost at measured M,
bootstrap 95% CI; amended pre-data twice, rationale inside).
P0b bench: router/bench_router_kernel.cpp (3 arms x 3 regimes x M sweep + 4-worker split
+ turbostat license clock; adversarially reviewed - avx_bf16 arm was widened to 6
accumulators after review showed a 1.2-1.3x dependency-chain handicap that would have
biased the AMX-vs-AVX gate).
CAMPAIGN r0-campaign.sh attempt 1 22:02:52Z: stopped lingering rinzlers (idle >=10 min
per journalctl, started 08:36Z at nightly end; slices fuser-clean, removed; NOT restarted
per policy), then stopped itself at bench validation - step 6 omitted the required
--regime flag (marker check-output; no captures wasted, guard released cleanly).
Attempt 2 launched 22:07Z after fix. Reps addendum r0-bench-reps.sh queued (pre-reg
needs 3 reps of realistic-regime cells). Results land in exec/results/router/.
R0 P0 COMPLETE 2026-08-23 ~23:10Z. Campaign attempt 2 all green (marker check-output only
from the known amx-n32-w4 geometry refusal). 20b decode captures 4/4, 120b RUNNABLE + 4/4
captures, prefill captured via new TRON_TRACE_GEN_FROM_PARSE (stock --trace cannot: 5s cap
dies in model load). P0b: 90 cells x3 reps + multicore + license clocks (fp32 3.89 / bf16
3.20 / amx 3.59 GHz). Cost-model correction: n=128 cyclic weight delivery 26us/layer, 2.4x
the nominal-L3 floor; disruption adds <=1%; AMX M-flat (6.55us n32 / 26us n128).
GATE: pre-registered variable (logits-read slice) says STOP everywhere (-0.9..-11.4%) BUT
was MIS-SPECIFIED - the driving-thread block is at start_reading topk_snd_channel
(19.3us/layer 1u, 32.4 8u). DEVIATION recorded in G0-preregistration.md. Corrected gate:
20b PROCEED-eligible all 4 configs (+2.6..+5.4%, conservative +2.2..+4.4%); 120b negative
at 1u, +1.35% at 8u/2K single-core; 4-worker AMX (8.49us) makes 120b viable est. AWAITING
jhan: endorse/reject deviation (suggest Sol round); then P1a decisions per plan sec 2/4.
Reports: router/p0-trace.html + router/status-report/index.html. Machine: rinzlers stopped
(lingering cleanup, NOT restarted), slices+amx-r0* hugepages removed, guard released.
R0 GATE DECISION 2026-08-24: jhan ENDORSED the gate-variable deviation (Sol round
ENDORSE-DEVIATION, exec/results/router/sol-deviation-review.md; package
router/G0-decision-package.md). 20b -> P1a, SPIKE-FIRST order (not a P1b/AMX
authorization); 120b conditional scope, 4-worker AMX point may not pass G0. Record
edits applied to p0-trace.html + G0-preregistration.md (wording: "reduced-overlap
sensitivity"; primary corrected estimand = stall_topk_read alone; recomputation +
missing-records notes). g0-decision*.json NOT regenerated (decision basis stands;
per-layer clamp applies prospectively in P1A pre-registration).
P1A STARTED: pre-registration exec/results/router/P1A-preregistration.md; type-
feasibility spike in tron-router-p0 (hand-edited generated header, no emitter change,
no ingest-owner dependency). Emitter-change scoping with ingest owners remains a
jhan action before the real P1a change goes to review.
P1A COMPLETE 2026-08-24 ~00:55Z. Phase S spike: SUCCESS (mixed host/device generated tp2
compiles+runs all executors; host router weight loads via normal visit/safetensors path;
sentinel-safe CPU publish correct; artifacts: exec/r0-p1a-patch-header.py + marker-blocked
header in tron-router-p0 only). Phase M same-binary A/B (TRON_CPU_ROUTER), avx_bf16 arm,
n=6/arm, ABBA: 1u/2K +0.81% [-0.22,+1.85]; 1u/8K -0.03%; 8u/2K -2.30%; 8u/8K -1.77%
[CI<0]. G-B NOT MET anywhere -> corrected G0 estimate superseded per pre-registration.
ROOT CAUSES (measured): (1) tracing inflated the P0 stall ~2.5x (untraced baseline 254 vs
traced-implied 206 tok/s at 1u/2K; untraced recoverable ~8us/layer vs kernel 6.4); (2) the
serialized placement moves the rmsnorm arrival wait onto the driving thread (traced cpu
slice 21.0us = 6.4 kernel + ~14.6 wait). Stall recovery mechanism itself PROVEN
(topk_snd read 19.7->0.36us/layer). First A/B pass used a placeholder expr-dot kernel by
mistake (-4.4% everywhere); detected via attribution, corrected, both generations kept
(results/router/p1a-arm-fp32expr/). Numerics: seeded off-vs-off control diverges ->
token-compare instrument INVALID in this harness; P2 logits pin is the instrument.
Records: router/p1a-spike.html; P1A-preregistration.md OUTCOME section. Machine left
clean (guard released, amx-r1* hugepages removed, serving still down per policy).
NEXT = jhan decision: bounded-parallel P1a variant / P1b+parallel pricing / option (e) /
close option (c).
P1A SOL REVIEW + NUMERICS RESOLUTION 2026-08-24 ~01:20Z. Sol P1a round (sol-p1a-review.md):
negative G-B valid/robust; 7 documentation-of-record corrections applied with Sol wording
(0.2% was the post-replacement residual, gross ~4.8%, net +0.81%; 14.6us rmsnorm wait =
derived attribution; option-e inputs must be REPRICED from untraced magnitudes; rep
extension = registered rule, not deviation; measurement-status addenda on p0-trace.html;
numerics reworded unresolved-not-invalid). Command audit: determinism flags WERE absent in
the first control. Flagged retry: control CLEAN (gpt-oss IS deterministic under
--temperature 0 -s 42 --pay-for-determinism; MoE ties do NOT break it; earlier
"invalid-even-flagged" was a log-interleave normalization artifact, re-verdicted via
token-span extraction) and OFF-vs-ON GENUINELY DIVERGES at token ~16/34 - recorded per
pre-reg; P2 logits/expert-set pin is the deciding investigation (near-tie flip = labeled
hypothesis). Decision package for jhan: router/P1A-decision-package.md (intel-amx-3d).
Sol recommendation: ONE bounded parallel-placement experiment with staged stop conditions,
option (e) repriced handoff, no standalone P1b, close-(c)-now also defensible.
OPTION (C) CLOSED by jhan 2026-08-24 after P1a G-B miss; remaining opportunity handed
card-side. (Decision: bounded-parallel experiment DECLINED; P1b dead; P2 router numerics
pin dead - token-16 divergence stays a documented observation with its near-tie hypothesis.
tron-router-p0 = archived spike branch, no PR. Live handoff owned by jhan: option (e)
pricing by the FPGA team using the REPRICED untraced magnitudes ~8us/layer 1u / ~12us 8u;
pointer set = p1a-spike.html sec 2/4 + p0-trace.html sec 4 + raw traces.)

| p3 | AMX Q-scalar gate + mirror write-through verification (codex P1 x2, 2026-08-28): exec/p3-q-scalar-gate.sh 323b9d5499 609dabba83 LAUNCHED 2026-08-28T05:07:10Z on 3bda: waits for CI lease release, isolated worktree /var/tmp/jhan/tron-p3-q-scalar-gate, mirror + canonical configs, t_amx_* + t_llama_unit + t_generate_host (llama-3-8b-host, 6 dense pages) + logit A/B, then negative control (609dabba83 headers -> t_generate_host must fail). Results logs/p3-q-scalar-gate.txt, marker .done | DONE 2026-08-28 05:34Z | mirror+canonical: all passed incl. t_generate_host (llama-3-8b-host, AMX on); negative control: unfixed build ABORTED (SIGABRT per apport; stderr not captured, marker ok was a false positive - script fixed; exact text via p3c) |
| p3b | codex #4 follow-up (K mirror accounting gauge/test): exec/p3b-mirror-accounting.sh f9b678e5d0 LAUNCHED 2026-08-28T05:21:56Z on 3bda; waits for CI lease + campaign flock (p3 still running), isolated worktree, mirror config, runs t_tronstats_convention (live FUSE, validates the new k_mirror_arena_bytes manifest entry), t_amx_arena_leak (wrapped available), t_amx_numerics, t_llama_unit. Results logs/p3b-mirror-accounting.txt, marker .done | DONE 2026-08-28 05:37Z | all passed: t_tronstats_convention 1149/29 (live FUSE), t_amx_arena_leak 12/3, t_amx_numerics 6414/5, t_llama_unit 144875/26 |
| p3c | pre-fix abort message capture (609dabba83, t_generate_host llama-3-8b-host, AMX on, core dumps off, 20 min bound, then kill-switch control): exec/p3c-prefix-abort-message.sh LAUNCHED 2026-08-28T05:35:48Z on 3bda, waits for the campaign flock behind p3b. Results logs/p3c-prefix-abort-message.txt | DONE 2026-08-28 06:00Z | pre-fix + AMX on: SIGABRT from the -inf m_star assertion (self_attention.hpp:1735-1738) via run_attention_job; TRON_AMX_DISABLE=1 control passed (2805 assertions); core files deleted, worktrees removed |

## SA - single-attention phase measurement (jhan request 2026-09-01: per-unit AVX vs AMX time and the common-work share)
"Single attention" = one apply_page_tok call (one query token x one 64-token KV page x one KV head), the
unit that does not change with users or context. Estimate from stamp-7605 slopes (fence round 3, 27
workers): mirror ~1.30-1.32x, canonical ~1.22-1.24x per unit (page 7.2.1, est.). Measurement: probe commit
on jhan-amx-fence (ref sa-probe-8e9296b; cherry-picked onto the branch by the launcher AFTER the peer
session's fallback-20260901.done marker, per coordination with session "tron PR #3879 AMX K mirror
comment" 2026-09-01 19:30-19:40Z), kvwait stamps 7606-7627 (worker-0 phase cycles + unit counts; tag
table in exec/single-attn-20260901/extract-sa.py), gen-header patcher v2 exec/fence-20260831/
patch-gen-stamps.py (idempotent; adds 7606+ sites only when the probe is present; v1 kept as
patch-gen-stamps.py.v1-20260831). Scripts: exec/single-attn-20260901/{launch-after-peer.sh,
run-single-attn.sh, extract-sa.py, patch-self-attn-phase.py}. Arms canon/mirror/disable, 1u, ctx
256/2048/8192, 2 reps x 256 tokens; binaries gen/runtron.samirror, gen/runtron.sacanon (RUNPATH trap:
run from gen/). Probe gated on TRON_ATTN_PHASE=1 (plus TRON_KVWAIT_FILE), so later fence rounds without it pay nothing. Overhead control: new 7605 vs fence3 medians-7605.json. Follow-up not in the run:
A/A logit check of the dotter-path reorder (design report risk iii; bit-identical by construction).
| sa | attempts 1-2 stopped at my own pre-build text checks (markers .attempt1/.attempt2, no machine effect); attempt 3 2026-09-01 21:01-21:20Z: builds 366 s + 361 s, smoke ok (all 3 arms), 18 cells, marker ok. Probe cherry-picked as 8fd1e7798d (jhan-amx-fence HEAD) | DONE 21:20Z | single attention (ctx 8192): AVX 3.64 / canonical 2.89 / mirror 2.66 us -> 1.37x mirror, 1.26x canonical; common work (softmax+state) 4-12% of a unit; QK 1.67x, PV 1.31x AVX/mirror at 8K vs 3.0x/1.8x at 256 (memory-limited units); per-op fixed cost joins+barrier 9-13 us; probe overhead on 7605 0-5%; page 7.2.1 + summary.json |

## Worktree move 2026-09-01 ~22:00Z
tron-dd and tron-fence-amx moved to ~/workspace/ai-runs/ (git worktree move; exec scripts updated to the new paths). tron-amx stays at ~/workspace/tron-amx for now (not asked). Old absolute paths in earlier QUEUE entries and result headers are historical. The moved trees' gen/ build caches still record the old source path (CMAKE_HOME_DIRECTORY); the next build needs a fresh cmake configure in a clean gen/ (full rebuild), or a reconfigure after deleting gen/CMakeCache.txt.
