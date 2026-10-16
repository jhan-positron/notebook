---
name: amx-tron-softattn-project
description: "AMX-for-tron-software-attention project — goal, deliverables, consensus process, key findings"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-08-25T12:14:39.696Z
---

Goal: use Intel AMX (Xeon 6 6962P, delphi-3bda) to boost tron decode for
ingested-qwen-3-4b-instruct-2507-tp2; software (CPU) attention only, not FPGA hw-attention.
Spec: /home/jhan/workspace/intel-AMX/input-2-ai/rampup.md. Deliverables (HTML, light theme,
pure-ASCII with entities + meta charset — mojibake fix 2026-08-17) in
/home/jhan/workspace/intel-AMX/rampup/: 01-amx-rampup.html, 02-tron-decode-amx-plan.html,
03-bill-poc-gap-analysis.html, 04-amx-action-plan.html (execution-ordered merge of 02+03,
Sol-reviewed), index.html. Doc 02's who-does-what diagram has 5 lanes incl. per-card driver
TX/RX workers: rope_k/save_k/save_v run on RX workers as DMA completion callbacks
(pos/worker.cpp:605-616, driver.cpp:493-568) — RX is on the per-layer critical chain; AMX
workers must stay off dev cpu set and TX/RX HT siblings (matches jhan's notebook
tron_threads.html function-to-thread matrix).

Process requirement: every deliverable must be a consensus of Claude + GPT-5.6-Sol via [[pal-bridge]].
Consensus v2 (2026-08-16) key corrections from Sol: (1) independent decode users own disjoint
physical KV pages — cross-user tile batching is invalid; guaranteed widths are QK N=4 / PV M=4
(GQA group); wider only via shared physical pages (shared prefixes, token tree, speculative).
(2) rolling-softmax v* cannot stay resident in AMX C tiles across pages (no tile-elementwise scale);
v* lives in a memory scratchpad, per-page TILESTORED + AVX-512 rescale/add.
Design: QK as Sᵀ=K_page·Q_packᵀ (K layout untouched — shared FPGA-DMA contract), PV with stored V
as B operand (already VNNI pair-interleaved, zero repack). No speedup claims before P0 fused-page
microbenchmark on delphi.

EXECUTION (2026-08-18): isolation rules — all AMX work in separate worktrees
(~/workspace/tron-pr2934-reconciled = byte-verified Aug-3 PoC tree, P0 challenger;
~/workspace/tron-amx = branch jhan-amx-p0 for our code); 3bda nightly CI window
(USER-CONFIRMED 2026-08-18, my first trace had it BACKWARDS): prep starts 03:30 UTC
(20:30 PDT), normally done by 09:30 UTC (02:30 PDT). ci-runner-stop@ timer fires 02:45 UTC
daily ("stop runner + inference up" — production inference may come up then);
ci-runner-start@ (14:00 UTC) is disabled. USER-CONFIRMED (twice, 2026-08-19): the usable
window extends to CI prep at 03:30 UTC - keep working until ~03:15Z; at 02:45Z check whether
the timer brought rinzler serving up and yield measurement cores if so. Free window =
~09:30 UTC -> 03:15 UTC next day (verify machine state first). When production rinzler
serving is up, AMX builds/benches pinned to fully-idle cores, nice 19, no system changes. /home is
NFS-shared alpha<->3bda; full tron builds impossible on alpha (nix blocked in claude-box) —
build on 3bda in the worktree. Queue + status: ~/workspace/intel-AMX/exec/QUEUE.md.
RINZLER POLICY (user directive 2026-08-18): lingering rinzler@0-3 after the nightly is a BUG
Rhys will fix, NOT machine state to restore. Until fixed: after CI/nightly completes, CHECK for
running rinzlers and CLEAN THEM UP (verify zero traffic in journal ~10 min -> systemctl stop
rinzler@{0..3} -> rm orphaned /dev/hugepages/slice-*-of-8 after fuser shows no open handles).
Never systemctl start them back.

P0 BASELINE MEASURED (2026-08-18, quiet slot granted by Rhys; serving = rinzler@0-3 systemd
units under positron account, lifecycle owned by nightly harness via platformd config patches;
cleanup = systemctl stop + rm orphaned /dev/hugepages slices after fuser check):
qwen-3-4b-tp2 USE_HW_ATTN=0, 1 tp2 instance: 1u decode 251/203/106 tok/s at ctx 256/2K/8K
(ms/tok = 3.43 + 0.734us*ctx est.); 8u/8K aggregate collapses to 116 tok/s; attention-shaped
share of 1u decode ~14/30/64% at 256/2K/8K (est.) -> unlike gpt-oss (FPGA-wait ceiling),
ATTENTION COMPUTE IS THE QWEN DECODE WALL at long ctx. Quiet-slot kernel numbers: AMX v2
263-271ns/page flat in M (1990 GFLOPS = modeled peak); dotter M=4 1762ns -> raw AMX 6.5x at
width 4 with pre-packed K. 127MB perfetto trace (u8/ctx2048) span analysis DONE: at 8u/ctx2048 attention compute = 13.0 cores-worth, ~67% of each attention worker (joins 0.24 cores, ~32% uninstrumented spin-waits) - estimate confirmed.
Results in ~/workspace/intel-AMX/exec/results/.
FUSED HARNESS MEASURED (2026-08-18, tron-amx/src/amx_fused_bench.cpp, self-contained +
self-validating): our S^T=K.Q^T fused path vs AVX fused at widths 1-16 x {L2,L3,DRAM}:
crossover Nq~3; width 4 = 1.22-1.37x (positive all residencies); width 16 = 2.8-3.3x;
PV 4+4 blocking BEATS 6+2 (adopted, settles the A8.3 A/B); Nq<3 stays AVX. Epilogue
(transpose/softmax/pack/rescale) ~1000 of 1300ns at width 4 = the tuning target. Combined
with baseline: projected width-4 decode gain at ctx 8K ~15% end-to-end (est., before epilogue
tuning); prefill-shaped width 16 gets ~3x attention. FORMULATION A/B AT HARNESS LEVEL (2026-08-18, fused-sweep-v2): mirror orientation (S=Q.K^T
+ pre-packed K mirror, Bill's) beats our S^T=K.Q^T at every width/residency - width 4:
686/1470/1800 ns = 2.36x/1.68x/1.77x vs AVX (L2/L3/DRAM); width 16 up to 5.5x; crossover Nq=2.
Cause of our gap: score round-trip through memory (tile stores cannot forward to vector loads).
Decision still open pending mirror system costs (RX-worker save_k write, +50% K capacity,
defrag). P5 candidate: pipelined score handling (page N-1 scores while page N tiles store).
Next: pipelined-epilogue experiment OR proceed to P2 integration with dual-orientation dispatch;
P1 counters; license/power capture; trace span analysis.

Gate honored: docs 01/02 were finished and signed off by Sol BEFORE reading Bill's PoC
(branch bill-amx, PR #2934 "+11.7% TPS on gpt-oss-120b", perf data in
~/workspace/tron-pr2934-perf-20260803). Phase 2 (consensus v3, 2026-08-16) = doc 03 gap analysis.
Bill's PoC key facts: K solved via k_vnni write-through mirror (2x K storage ≈ +50% K+V payload;
defrag drops the mirror — open MAJOR); M-bucket dispatch (1-3 scalar / 4-7 blocked-AVX512 / >=8 AMX);
wins are mostly PREFILL (+22..+63% prompt TPS; decode +6..+10.5% best, llama-tp4 -2.9% inconcl,
llama-3.2-3b kv_mul=3 only net regression ~-4%, causes hypothesized). Measured decode ceiling on
gpt-oss-tp4: qs_for_attn_channel.start_reading (FPGA Q-matmul wait) = 73% of attention-worker time
(76% all channel sync) — attention compute only ~12%; workload-specific, must be re-measured for
qwen before kernel work. qwen3-4b decode forecast: unresolved 0-10% hypothesis (kv_mul=4 = weak
bucket). Kernel amendments (A8): actual-width buckets, independent QK/PV thresholds, 4+4-vs-6+2 PV
blocking A/B, head-64/128 specialization, fused transpose+scale+mask+max, canonical K default
pending formulation A/B vs his mirror. PR #2934 still OPEN, no human review, 1 BLOCKER + 5 MAJORs
open — evidence and kernel material, not a safe integration base as-is.

Tron facts that took effort: software attention kernel = apply_page_tok
(h/tron/models/self_attention.hpp:1400), QK via dotter<bf16,128> (dotter.hpp:176), PV via
scaled_v_expr (kv_cache.hpp:1642); qwen3-4b = 36L/2560h/32Q/8KV/head128/GQA4, full causal;
ingested plugins force_hw_attn=true (USE_HW_ATTN=0 forces software); positions <127 + HBM-shard
tails are always software even in hw mode; tp2 = FPGA matmul split, CPU attention unsharded.

P1 SHARING MEASURED (2026-08-19, p1_share_counters.hpp in apply_page_range, flag-gated):
widths = tokens/page-visit (x4 GQA = GEMM width). Prefill avg 110.9 (99.9% work shared);
private decode 1.02 (GQA-only width, consensus confirmed); shared-1024-system-prompt decode
avg 5.06 with 87.6% of work at width 8 (shared prefix dominates attention bytes). P4 verdict:
shared-KV batching justified for shared-prompt deployments + prefill; useless for private
decode. Remaining P0: license/power capture. Next: P2 integration scoping (orientation choice
pending mirror system costs).

P0 COMPLETE (2026-08-19). (c) license/power: sustained width-16 AMX runs the core at 3.59 GHz
vs 3.89 GHz AVX (~8% license clock cost, both orientations equal; grid speedups already include
it since same-core wall-clock); package power flat ~225W at 1-core scale; many-core -> T4.
Next phase: P2 in-tree integration (dispatcher + kernels behind runtime guard, orientation
decision via mirror system costs), tests T1-T3, then T4 slot.

P2 INCREMENT 1 MEASURED (2026-08-19): AMX QK fast path integrated in real apply_page_tok
(iface header + isolated -mamx TU src/tron/kernels/amx_attn.cpp + TRON_AMX_DISPATCH cmake opt
+ TRON_AMX_DISABLE kill switch + lazy Q pack per (token,kv_head) + region per apply_page_range).
Same-binary A/B on real qwen tp2: +2.8% (1u/2K), +6.1% (1u/8K), +8.9% (8u/2K, 358->390 agg)
decode from the QK half alone; scales with attention share as modeled. Next: 1b PV-on-AMX,
increment 2 mirror orientation, T1-T3 tests, then T4 slot.

P2 INCREMENT 1B CODE DONE (2026-08-18 22:00Z), measurement queued: pv_128x4 in the AMX TU
(exp rows fp32->bf16 into zero-padded 16x64 A tile via _mm512_cvtne2ps_pbh(hi,lo); page V
storage consumed directly as B — kv_block V layout IS the AMX B format; 4+4 blocking, 2 halves
x 2 K-steps). kv_cache.hpp gained v_base()/v_data<geometry>() raw-pointer accessors. AMX
epilogue branch in apply_page_tok: pass 1 = identical scale/softcap/max/exp per head saving
corr/m_new/sum, one pv_128x4 call, pass 2 = standard v*/s*/m* update from AMX output; early
return; old epilogue untouched when did_amx==false (did_amx hoisted to function scope).
TRAP LEARNED: _tile_stored always writes the configured 16 tile rows — output buffers must be
16 rows even when only 4 are meaningful (a 4x128 buffer is a 6KB stack overrun). Numerics
(CORRECTED 2026-08-19, Jeremy's question): BOTH paths round PV weights to bf16 — AVX
scaled_v_expr TRUNCATES fp32->bf16 (srli 16, kv_cache.hpp:1795-1800) into VDPBF16PS; AMX uses
round-to-nearest-even (VCVTNE2PS2BF16). Both engines bf16-in/fp32-accumulate end to end (QK:
dotter uses VDPBF16PS too). A/B numeric deltas = weight rounding mode + accumulation order
ONLY (qualified: finite non-subnormal inputs; DAZ/FTZ + NaN/inf deferred to T1). Earlier claim
"AVX path uses fp32 weights" was WRONG. bf16 ULP fact (Sol correction): 8-bit significand
(7 stored), adjacent values ~0.78% apart within a binade — NOT 0.4%. 6962P also has AMX-FP16
(TDPFP16PS, CPUID 7.1 EAX bit 21; not reported in /proc/cpuinfo on this stack) — irrelevant to
tron (KV is bf16). DECISION (2026-08-19, jhan approved): keep RNE in pv_128x4; formal T1 =
pre-sampling logit comparison vs fp32 reference with predeclared abs+rel criterion; chop
variant = one-line fallback if T1 owners want bit-identical weights vs AVX. Full writeup:
doc 02 sec 6b (addendum, Sol consensus round 3: ENDORSE-WITH-EDITS, 7 corrections applied;
consensus log updated). Harness 8e-5 = observed worst-case on normalized outputs, denominator
floored 1e-3; its reference ALSO rounds P to bf16 (amx_fused_bench.cpp:439). Script
exec/p2-inc1b.sh on 3bda (launch: ssh jhan@delphi-3bda, I run as root in claude-box so plain
ssh defaults to root and fails): runs immediately in the evening-UTC free window (guard: no
new run in [02:00, 21:00) UTC), rinzler policy, build, 18-run A/B ->
results/slot1/p2-inc1b.txt, marker logs/p2-inc1b.done. Relaunched 22:09Z after the user
corrected the CI window (first version waited for 03:50Z = inside CI prep).

P2 INCREMENT 1B MEASURED (2026-08-18 22:23Z, same-binary A/B, 3 reps, zero failures,
results/slot1/p2-inc1b.txt + chart p2-inc1b.html): decode +4.4%/+12.0%/+16.9%
(1u2K/1u8K/8u2K aggregate 358->419 tok/s) — PV roughly DOUBLED inc-1's QK-only gains
(+2.8/+6.1/+8.9%) as modeled. PREFILL gains larger: +44.7%/+102.0%/+41.6% (8K prompt
521->1054 tok/s = 15.7->7.8 s; inc-1 already gave +15.8/+28.3/+13.6%) — prefill pages are
dense and cache-resident, the regime with max kernel margins. OFF arm reproduced inc-1
baselines within 0.5% — kill-switch A/B night-to-night stable. t1-quick numerics precursor:
runtron needs --temperature 0 -s 42 --pay-for-determinism for deterministic output (default
sampling random); with them the control passes (OFF-vs-OFF byte-identical). AMX greedy output
byte-identical at ctx 8192; ONE argmax flip ~20 tokens in at ctx 2048 (then divergence by
construction). Extract generated text via green ANSI chunks (\x1b[38;2;000;128;000m...\x1b[0m),
NOT line filtering — ASLR mapping lines + mid-line log continuation gave a false DIFFER.
Formal T1 = logit deltas + near-tie margins.

P2 INCREMENT 2 (K MIRROR) DONE 2026-08-19 00:45Z, code+smoke+full suite in ONE night
(results/slot1/p2-inc2.txt + p2-inc2.html; mirror binary 02b81206, inc-1b preserved as
gen/runtron.inc1b). Design: TRON_AMX_K_MIRROR cmake opt (PUBLIC define - layout change);
kv_block gains 3rd plane k_vnni[page*head] (planes const 2->3 feeds BOTH capacity formulas,
kv_cache.hpp:524-538 + static_assert ~1027); save_k write-through at model.hpp:2778 gated on
amx_attn::available(); defrag rebuild at the ONE page-move funnel copy_storage_slot (from dst
canonical K); qk_mirror_128x4 = harness amxqk port (S=Q.K^T, no transpose; 16-row store ->
16x64 scratch + 1KB memcpy); pack_q_rows_128x4 (A-operand row pad, same 4KB buffer).
MEASURED: decode +0.1/+3.7/+5.2% over inc-1b -> TOTAL +4.5/+16.1/+23.0% over AVX (8u agg
358->441 tok/s); prefill +1.0-2.0% over inc-1b NET of RX write cost. Mirror greedy output
byte-identical to canonical-AMX (same head-dim sum order - expected, cross-kernel check).
COSTS: (1) mirror build's AVX fallback -3.8/-7.8/-3.9% decode vs inc-1b build (fatter blocks
hurt locality even with writes gated) - mirror build must only ship where AMX is ON;
(2) KV capacity -33% (48 vs 32KB per block-page). FORMULATION DECIDED (Sol consensus
ENDORSE-WITH-EDITS 2026-08-19): canonical-K = supported default; mirror = opt-in for pinned
AMX deployments tolerating -33% KV capacity; mirror kill switch is NOT a baseline rollback
(must document as such). 1u/2K mirror delta +0.117% = PARITY (rep ranges overlap; worst cell
spread 1.15% peak-to-peak). mirOFF penalty cause NOT established (zero writes rules out write
bandwidth only) - queued: layout-only control build + TLB/cache counters (QUEUE row 15);
capacity-adjusted tests (row 16: max users at fixed KV, 8u/8K, latency near capacity) gate
mirror production-readiness, plus A7 byte-equivalence test + formal T1. Reevaluate default
after P4 with END-TO-END capacity-adjusted results, not tile timing.

ROW-15 DECOMPOSITION DONE (2026-08-19 01:15Z, same night): layout-only control build
(TRON_AMX_K_MIRROR_LAYOUT_ONLY cmake opt - 3-plane kv_block, canonical kernel, zero mirror
code) reproduces the mirror fallback penalty EXACTLY (-3.7/-7.6/-4.0%) -> layout is the whole
penalty. KEY: fat layout also hurts the AMX path (-9.2/-8.1% at 1u8K/8u2K) -> mirror kernel's
TRUE same-layout gain ~+14%; net +3.7/+5.2% = kernel gain minus layout tax. Decode-phase perf
(sudo -n perf attach -p PID after prefill line, 15s; perf_event_paranoid=4 blocks user perf on
3bda): LLC-load miss 50.8%->84.6%, dTLB ~0.00% both -> cache/prefetch locality, NOT TLB (dead
16KB mirror plane between K/V blocks breaks prefetch streams). MITIGATION QUEUED: move k_vnni
to a parallel arena - K/V stay dense (both penalties should vanish, unlocking ~14%), mirror
memory allocatable only when AMX on. A7 tests written: t/t_amx_mirror.cpp (kv_block-level
byte equivalence) + mirror checks in t_llama_unit append test + fixed its hard-coded 2-plane
dma_size_bytes assert (now detail::kv_block_planes). Result HTML pages moved to rampup/
(user: HTML deliverables live in rampup/; index.html links verified).

T1 PROGRESS (2026-08-19 ~01:52Z): tron's golden-logit machinery = t/force_generate (per-step
logits) + check_golden_logits (TVD<=0.05 vs HF goldens from bin/extract_logits, outlier cap
0.3@10%, top-5 overlap>=3). TRAPS: (1) canned ingest-test prompts are 21 tokens -> AMX never
engages (needs full 64-token pages) - their pass is hollow for AMX; (2) without USE_HW_ATTN=0,
decode attention runs on FPGA -> A/B arms bit-identical (good negative control). FIRST REAL
SIGNAL (t/t_amx_logit_ab.cpp, 192-token forced gen, llama-3.1-8b, sw attention): AMX-vs-AVX
argmax agreement 190/192, both flips at near-ties (margins 0.031 and 0.000 exact tie; median
margin 0.266), worst abs logit delta 0.25 - healthy per Sol's spec. 8u/8K point (row 16):
total +28.4% decode (114.4->146.9 agg), mirror edge grows with attention share
(+3.7->+5.2->+7.7%). Sec 4b transpose addendum in doc 02 (Sol round 4 ENDORSE-WITH-EDITS;
my ~200ns gap figure was WRONG - it is ~300ns, 982-686). T1 FULL FIRST PASS DONE same night (02:05Z) ON QWEN vs HF fp32 reference:
bin/extract_logits WORKS on 3bda via uv (non-quantized models only; GPTQ blocked, venv lacks
optimum; --max-tokens TRUNCATES input - use 192). Qwen3-4B-Instruct-2507 HF weights on 3bda.
148 aligned steps: AMX-vs-AVX max TVD 0.054/median 0.0000/1 outlier -> PASSES repo criterion;
both arms IDENTICAL distance to HF (max 0.7139, argmax 126/148 both) -> AMX adds NO error on
top of tron's existing HF gap (median ~0.11, engine-level or alignment convention - T1-owner
follow-up, not AMX). Tools: t/t_amx_logit_ab.cpp (AMX_MODEL/AMX_TOKENS envs). TRAPS: canned
21-token prompts never engage AMX; without USE_HW_ATTN=0 decode attention is on FPGA (bit-
identical arms = negative control). Next: T2/T3, T4 slot, parallel-arena mirror design,
qwen ingest-vs-HF gap question to T1 owners.

STANDING AUTHORIZATION (jhan, 2026-08-19 02:45Z): NO Rhys coordination needed for quiet
slots. Every morning after the nightly CI window (normally done by 09:30 UTC / 02:30 PDT):
verify CI is done (rinzler zero-traffic or inactive), clean leftover rinzlers per the rinzler
policy, and use the machine. Nothing in the project is externally blocked. T4 first pass
scheduled via exec/p2-t4-morning.sh (waits 09:30Z; clean-baseline build with all AMX flags
OFF + 3-binary symmetric suite + turbostat power per arm at 8u/8K + capacity probe u16/u24
at ctx 8192 -> exec/results/t4/).

POSITIONING (jhan, 2026-08-19): the tron-vs-HF gap (median TVD ~0.11 with AMX off, identical
both arms) = KNOWN ISSUE, NON-BLOCKING. It is not introduced by AMX, does not gate AMX
enablement, and needs no human decision. Present it that way in all docs; recorded for
whoever works on engine-vs-HF fidelity later. T1's remaining scope = more prompts/seeds only.

BILL'S PR MIRROR PLACEMENT (verified in source 2026-08-19): his k_vnni is ALSO a kv_block
member (in-block, mirror_eligible(head_size)-gated) - same placement as our inc-2, so the
layout penalty class is expected to apply to his PR too (hypothesis, never measured on his
models). His PUSHED branch's copy_from never rebuilds the mirror (doc-03 defrag MAJOR
confirmed at code level); his Aug-3 MEASURED local tree DOES rebuild in the copy path - one
of his three unpushed local edits. The parallel-arena design is new to both implementations.

T4 FIRST PASS DONE (2026-08-19 10:26Z, self-serve morning script worked end to end; results
exec/results/t4/). TRUE clean binary (all AMX flags OFF): decode vs clean - canonical
+3.8/+15.2/+19.0/+17.5%, mirror +4.5/+19.8/+22.6/+26.6% (1u2K/1u8K/8u2K/8u8K); prefill up to
+105%. Clean reproduces P0 baseline (105.6~106 at 1u8K) -> week's kill-switch A/Bs validated
(dispatch-off overhead ~0; kill-switch arm ran 0-3% ABOVE clean -> our reported gains were
conservative). Capacity: 16u+24u at ctx8192 zero failures BOTH binaries; aggregate saturates
past 8u (KV-traffic wall: 147 agg at 8u -> 78 at 16u); mirror +6% held at saturation. Power
capture incomplete (turbostat rows lacked PkgWatt - retry with --Summary). Remaining T4:
power, more reps, llama/gpt-oss shapes.

INCREMENT 3 (PARALLEL-ARENA MIRROR) BUILT+MEASURED same day (2026-08-19 ~15:00Z;
results/t4/p2-inc3-arena.txt, binary runtron.inc3arena; A7 suites pass on the new design).
Design: kv_block back to dense 2-plane; mirror planes in book-owned parallel arena (plain
non-DMA, = kv_bytes/2, 64B-aligned, allocated ONLY when amx_attn::available(); consumers
null-check, fail soft); same save_k site + defrag funnel; scatter_k_mirror moved to the EARLY
detail block (first build failed: defined after use sites); LAYOUT_ONLY flag retired (#error).
VERDICT: prediction (a) CONFIRMED - fallback penalty GONE (kill-switch arm = clean speed,
-1.3..+3.3%); kill switch = true rollback; capacity cost AMX-only. Prediction (b) REFUTED -
AMX arm unchanged (within 1.1% of in-block mirror): the ~9% layout tax belonged to the
CANONICAL kernel on fat blocks, NOT the mirror kernel (my "unlock ~14%" inference was wrong;
corrected in all docs). Arena mirror vs clean: decode +4.5/+19.6/+22.8/+28.1%.
T4 POWER (8u/8K, turbostat --Summary): pkg flat (+0.3% mirror/+1.6% canonical vs clean 543W);
busy clock -4% (milder than 8% single-core); ENERGY/TOKEN -14.5% canonical / -21.6% mirror.
Formulation REVISION question (arena-mirror as default?) sent to Sol - his kill-switch
objection is resolved; capacity (-33% pages on AMX hosts) + young-code gates remain.

FORMULATION REVISION ROUND (Sol, 2026-08-19): KEEP-CURRENT now; REVISED END STATE once 5
gates pass = arena-mirror DEFAULT on AMX hosts with sufficient KV headroom, fail-soft to
canonical/AVX, kill switch retained; canonical = mature compatibility/constrained-memory
fallback ("canonical no longer deserves default status on performance or energy grounds").
Gates: (1) T1 extension w/ predeclared criteria; (2) T2/T3 true fallback paths (non-AMX host,
runtime-disabled, arena alloc failure, lifecycle, defrag); (3) capacity-bound behavior
at/beyond KV limit incl. whether default needs a memory-headroom threshold; (4) A7 tests in
CI; (5) T4 replication w/ confidence intervals + llama/gpt-oss shapes. Recorded in doc 04 +
QUEUE "Formulation end-state" section.

CAPACITY FRAMING CORRECTED + GATE-3 DATA (2026-08-19 15:40Z): the arena allocates from
ORDINARY RAM (operator new, 32GB; machine 1.58TB), NOT the hugepage/DMA budget that sets KV
page count -> arena build page capacity == canonical (my "-33% pages on AMX hosts" line to
Sol was the in-block framing, corrected). VERIFIED: both binaries admit 32u+48u at ctx8192
(48u ~58GB of the 64GB budget; in-block would have ceilinged ~36u), failed=0; arena-mirror
+6.0% aggregate at the edge (107.0 vs 100.9), per-user min/p50/p95 all slightly better.
T1 EXTENSION DONE (3 prompts/956 steps total: AMX-vs-AVX max TVD 0.054, 1/956 outliers;
prompts 2-3 zero outliers). SHAPES DONE: llama-3.1-8b-tp2 +15.0/+19.7% decode (generalizes);
gpt-oss-20b-tp2 -0.3..-1.6% = no regression when ineligible. Remaining gates: T1 batching
variations + criteria text; T2/T3 fallback tests; beyond-page-budget behavior; A7-in-CI;
T4 confidence intervals.

DRAFT PR CREATED (2026-08-19, user-directed): positron-ai/tron#3879, branch jhan-amx-p0 on
main 1407f48dd, ONE commit, 12 files +1506 lines, assigned to jhan (--assignee @me), no
reviewer, DRAFT until remaining gates. Reviewer docs (user-directed, in rampup/):
pr-rampup.html (newcomer intro: problem/AMX/what-changes/safety-chain/evidence/glossary,
3 computed SVGs) + pr-walkthrough.html (12-file diff map SVG + per-file what-to-check table
+ reading order + 4 review invariants). Both linked from index.html; Sol review in flight.
NO further code changes planned at this point (user statement) - remaining work is testing
gates only.

PR-DOCS SOL ROUND (2026-08-19): ENDORSE-WITH-EDITS, 10 corrections, ALL APPLIED to
pr-rampup.html + pr-walkthrough.html (canonical range is +3.8..+19.0% - also amended in the
commit message via force-push; "no data conversion" qualified; storage-format claim narrowed;
safety figure restructured to 5 universal gates + 1 mirror-only branch; byte-for-byte fallback
claim softened to "unchanged code path at clean-binary speed"; numerics comparators
disambiguated; compressed claims labeled with configs; invariants expanded 4->9; plain-language
not-in-PR section; walkthrough marked dated snapshot). ONE Sol claim corrected by me:
arch_prctl(ARCH_REQ_XCOMP_PERM) is per-PROCESS on Linux (kernel xstate docs), not per-thread
as Sol wrote - invariant 8 states the per-process grant + per-thread tile config instead.

A7-INTO-CI REMOVED from tracking (jhan 2026-08-19: remote task handled elsewhere - do not
track or plan it). T2 AMD question answered from code: detect_and_request() gates every AMX
instruction on CPUID 7.0 EDX bits 22+24 (feature bits, not vendor string - correctly 0 on
AMD) AND XCR0[18:17] AND arch_prctl success; AMD gets the AVX path. Remaining T2 gap: one
empirical boot on an AMD host (andoria machines likely AMD - NEED jhan to name/authorize one;
standing rule forbids andoria without explicit mention).

GATE 5 COMPLETE (2026-08-19 ~18:30Z): replication 8 reps/cell (CV 0.1-0.7%), decode vs clean
95% CI: canonical +15.3+/-0.4 / +17.7+/-0.2; arena-mirror +19.7+/-0.3 / +27.8+/-0.8 (1u8K,
8u8K). First campaign under the cross-session flock. REMAINING GATES: T1 batching+criteria
text; T2 AMD-host boot check (awaiting jhan to name a machine); gate-3 mixed-context (harness
decision needed). A7-in-CI removed from tracking (remote task).

MIRROR-GENERATION COST ISOLATED (2026-08-19 23:20Z, user question; exec/bench_scatter.cpp run
on 3bda idle core 96 nice 19): scatter_k_mirror = 70.3 ns/token-row (head 128, L2-resident) ->
~20.3 us per prefill token (36 layers x 8 heads), spread across RX workers (~2% serial-equiv
of prefill wall; decode ~0.3-0.4%/step). Consistent with the system A/B (prefill net +1-2%
over no-write build). Caveat: favorable single-core setting; system A/B stays authoritative.
Numbers added to pr-rampup fork callout + walkthrough model.hpp row.

PR-RAMPUP NOTION UPDATE (2026-08-19, instructions at notion "Update pr-rampup.html" page under
Daily notes > Intel AMX > Prepare review): (1) section 2 retitled "Intel AMX", content now
TRANSPLANTED AT BUILD TIME from doc 01 section 1 (intro bullets + One-P-core figure + caption;
generator reads 01-amx-rampup.html so they stay in sync; cite/pill/svgwrap CSS added);
(2) energy-per-token paradox answered in-text (flat watts x less time = fewer joules/token);
(3) llama numbers removed from the run-on evidence sentence (they were shape-test results,
NOT averages - user misread them, so they moved); (4) new subsection 5.1 "Model coverage"
with the full llama (eligible, gains) + gpt-oss (ineligible, no change) table.

DECISION (jhan 2026-08-19): mirror STAYS OPT-IN for now (despite arena removing all measured
costs); the consensus end-state (arena-mirror default once gates pass) unchanged as the plan.
pr-rampup evidence paragraph restructured into Power + Numerics bullets; "greedy flips only at
ties" rewritten in plain words (rounding can only tip a coin the model was already flipping).

GEOMETRY AUDIT (2026-08-19, jhan question "what geometry do we support / which models match"):
gate = `geometry.kv.head_size == 128 && geometry.kv_mul() == 4` (self_attention.hpp:1357) +
runtime available(). Why (128,4): 4 q-heads x 128 dims = 512 bf16 = 1024 B = one full tile.
tp1/2/4 NOT part of geometry (model-level compile-time constants; executor is a separate
template param). Registry (config/models.yaml, geometry from plugin headers): 8 of 30 C++
families match: qwen-3-4b-2507, llama-3-8b, llama-3.1-8b, mistral-7b, ministral-8b,
mixtral-8x7b, phi-4 (40Q/10KV - ratio is what counts), granite-3.3-8b (plugin not e2e yet).
Near miss: llama-3.2-1b (ratio 4, head 64). gpt-oss 64Q/8KV/head64 fails both. Measured only
qwen + llama-3.1 (+ gpt-oss no-regression). Documented: pr-rampup.html section 4.1 (matrix
table by ratio x head width); QUEUE row 17 = A/B the other 6 before any default flip.

GPT-OSS ESTIMATE (2026-08-19, rampup/gptoss-estimate.html, gen_gptoss_estimate.py):
gpt-oss-20b in tron = 24 layers ALTERNATING: even = sliding-window-128 + software_only
(always CPU even in FPGA mode), odd = full attn + FPGA-capable; per-layer sinks
tensor<64>; scale 0.125. Sinks applied AFTER page loop (apply_attn_sinks :1184) and the
dense fast-path predicate ALREADY has the window check (:1537) -> sinks+window need ZERO
AMX changes (code-verified). Tile identity: 8 heads x 64 dims = 512 bf16 = same full tile
as 4x128; third family member 256x2 = gemmas. Work est: qk_st_64x8/pv_64x8 + 2 gate sites
~1 week + tests; NO mirror for v1. Payoff est: gpt-oss reads 5.9x fewer KV bytes/token
(204.5 vs 1208 MB at 8K) -> attn share est 20% -> ceiling +5.5% (range +3.8..+7.3) decode
1u/8K all-software; production FPGA mode est ~0. First step before committing: one-slot
decode perf attach to pin real attn share. index.html card added (also fixed stale
"three sentences" card text).
Sol round on gptoss-estimate (2026-08-19): 8 defects fixed - key ones: bytes 5.9x != share
ratio 3.1x (conflation); the +5.5% figure is bandwidth-bound-case est ONLY, arithmetic
shrinks just 3x (12 vs 36 full layers, per-layer multiply work equal at 4096 query numbers)
-> compute-bound case = share ~40%, est ~+12%; qwen 25.7% attn cut is DERIVED not measured;
"+19.7%" (not 19.6) from the 105.7/126.5 anchors; payoff numbers are 20b-only (120b = 18+18
layers, verified, needs own arithmetic); "ceiling" wording removed (sensitivity range).

DOC-01 SUBSECTIONS 1.1 + 5.1 (2026-08-20): added 1.1 "AMX and AVX-512 on the same core"
(id=amx-vs-avx, port-5 SVG; generator gen_amx_avx_core.py v2, now idempotent strip+reinsert)
and 5.1 "Who does the rearranging" (id=who-repacks). Sol round 1 = 9 findings (review output
RECOVERED from the crashed session's task file bx4u379fi.output - the chat call succeeded even
though the client exited 1). ALL 9 APPLIED 2026-08-20: port-5 map qualified as Intel's
documented model (opt-manual:3655 is the Skylake-Server chapter, FMA-on-port-5 "on some parts";
no 6962P port map in local refs); "whole story" narrowed to execution-unit collision point;
"in flight" -> "while TDP* execute" + manual's "usually closes"; reopen trichotomy per 20.11.3
(<100-insn AVX blocks never reopen port 5, 100-300 lose up to 20%, longer blocks run faster
with both FMA ports open - TILEZERO countermeasure only for the middle case); contention
wording widened beyond cache misses; asymmetry takeaway narrowed to the supported claim;
sec 7.3 gained a measured paragraph (3.59 vs 3.89 GHz, pkg ~225W flat, p0c-freq-power.txt;
8u/8K busy clock -4% pkg flat, t4-power.txt; non-AMX-core APERF/MPERF split still unmeasured)
fixing the broken cross-ref + meas pills; instruction-list completeness qualified to -052 base
set + 6962P-advertised extensions; AMX-TRANSPOSE = "for rearranging tile data". Round 2
(2026-08-20): ENDORSE-WITH-EDITS, all 9 round-1 fixes verified, 5 new defects, ALL APPLIED:
"usually closes/closed" hedge in SVG + table (and, for consistency, glossary sec 0 + pitfalls
sec 7.2); asymmetry claim reworded to "local references document no corresponding dedicated
mechanism"; 7.3 prose narrowed to what p0c-freq-power.txt records (variants avx/amx44/amxqk -
no width-16/same-kernel characterization, that metadata is NOT in the artifact); "whole socket"
-> "two-socket system total" with the +0.3%/+1.6% pkg deltas spelled out; document-wide
"measured = 2026-08-16" legend generalized to allow later-dated result-file citations.
FMA TERMINOLOGY (jhan request 2026-08-20, mid-round): plain "FMA" now reserved for the AVX-512
vector units document-wide; TMUL's internal array renamed "multiply-add grid" (Intel:
"conceptually a grid of fused multiply-add units", isa-extensions-progref:7086); section-1 SVG
now "TMUL (fed via port 5)"; 1.1 figcaption states closing port-5 FMA takes nothing from AMX
itself; 1.1 port-5 tenant box = "TMUL feed (TDP* ops)". gen_pr_rampup.py RERUN after the
section-1 edits (its transplant copies the bullet + SVG labels; diff verified minimal; note:
transplanted doc-01 sec-refs like sec 6.2/6.3 dangle in pr-rampup - PRE-EXISTING pattern, the
new bullet was made self-contained to avoid adding another). Round 3 (2026-08-20):
ENDORSE-WITH-EDITS - all 5 round-2 fixes + FMA terminology verified correct; 2 residual
qualification defects, BOTH APPLIED with Sol's suggested wording verbatim (1.1 takeaway:
"while the port-5 FMA is closed during TDP* execution, AVX-512 loses one of its two FMA ports";
glossary FMA entry: port-0/port-5 map qualified as Intel's documented model, "on some parts",
no 6962P port map in local refs, and "the port-5 issue slot (in that documented model)").
Consensus CLOSED per project practice (ENDORSE-WITH-EDITS + edits applied verbatim = done, as
in the pr-docs round). Neither round-3 edit region is in the pr-rampup transplant (glossary is
before '<h2 id="what">', takeaway inside 1.1) - no re-sync needed.
gen_pr_rampup.py's transplant is otherwise UNAFFECTED by 1.1 (extracts section 1 only up to
'<h3>Configuration lifecycle</h3>', which precedes 1.1). Doc 01 has no in-document consensus
log; its rounds are recorded here (same as the pr-docs round).

BILL'S REPLACE-K QUESTION SCOPED (2026-08-20, pr-rampup.html NEW SECTION 4.3 id=why-two-k,
in gen_pr_rampup.py): why not store K transposed once instead of two copies? Answer: canonical K
is a shared interface, transposed K is one kernel's private view. Code evidence: (1) FPGA reads
the K page bytes as stored - save_k_impl comment "Update the page first so HW sees the latest K
values" (model.hpp:2779); hw offload DMAs completed 4-token GOFs (gof_tokens=4, gof.hpp:33;
gating full.hpp:2382); KV book is DMA hugepage memory, arena is plain RAM the card never sees.
(2) AVX fallback dotter<bf16,128> (dotter.hpp:176) consumes contiguous 128-value K rows (QK
reduction along head dim = contiguous in canonical row); transposed layout puts one token's
values 32 B apart across 16x16x2 panels -> narrow/partial/kill-switch cases become gathers.
(3) Kill-switch rollback (-1.3..+3.3% of clean) requires the unchanged layout to exist.
Replacement would save only: arena RAM (<=32GB plain of 1.58TB; page capacity already identical),
defrag rebuild + A7 tests; NOT the write (70ns scatter becomes the primary store). V is the
precedent for when replace IS right: all V consumers (AVX scaled_v_expr, AMX B operand, card)
read the same interleaved layout natively -> V needs no mirror. Reopen if a card consumes
transposed K natively or an FPGA-free build exists. Sol review of 4.3 (2026-08-20):
ENDORSE-WITH-EDITS, 3 defects, ALL APPLIED: (1) "every query below position 127" removed as an
AVX-fallback category (contradicted 4.2 - such queries' COMPLETE pages take AMX; only partial
tails fall to AVX); (2) "cache-line gather / hurt most" softened to the demonstrated layout
consequence (loses contiguous-row loads, needs strided/gather loads + rearrangement) - no
replacement-layout benchmark exists; (3) accounting balanced: replacement also removes the
alloc/lifetime plumbing, null-check fallbacks, and the two-copy consistency invariant; capacity
claim narrowed to the measured probe (32u/48u at ctx 8192, zero failures); "made small" qualified
as relative to memory/page budgets. Consensus CLOSED (edits applied verbatim).

Generators + patched PAL client
live in session scratchpad f8e01291* (gen_amx_avx_core.py v2 idempotent, gen_pr_rampup.py copy,
pal_client_local.py, sol-round2-groundtruth.md). Session fd2027a1 scratchpad has pal_client_local.py
v2 (@file args: `chat @args.json` - background Bash drops stdin redirects AND $() substitution,
so pass a file path; also never `python - <<EOF > file` when the script writes that same file).

NOTES CONVENTION ADOPTED (2026-08-20, user-directed, commit 6c9d9c3f5 pushed to jhan-amx-p0 as a
FOLLOW-UP commit - amend blocked by permission classifier): 5 named Notes anchor the AMX design
commentary - [AMX attention dispatch], [Tile stores write 16 rows], [Mirror orientation] in
amx_attn_iface.hpp; [K mirror parallel arena], [K mirror coherence] in kv_cache.hpp; See-refs in
self_attention.hpp, model.hpp, amx_attn.cpp, both mirror tests. make lint-notes + make lint pass
on 3bda (`nix develop --command make ...`; lint-notes' def listing = ORPHANED defs only).
make format applied per AGENTS commit rules - it revealed the ORIGINAL PR commit was not
format-clean (reflow-only fixes folded into 6c9d9c3f5). Tron Notes context: convention in
AGENTS.md, 577 pre-existing sites, linter bin/lint-notes scans h/ src/ t/.

DECISION RECORD STARTED (2026-08-20, user-directed): rampup/distilled.html - one entry per design
decision (chosen / rejected+why / settling measurement / Note anchors), the artifact for the
scoped design review with Bill+Alexey; grows a section at a time. D1 (K-mirror formulation:
canonical default, arena-mirror opt-in, end state behind 5 gates; rejected R1 in-block, R2
default-now, R3 replace-K, R4 canonical-only) DONE - Sol round ENDORSE-WITH-EDITS, 10 defects,
ALL APPLIED (key: end-state wording needs "with sufficient KV headroom"; ~300ns is a DERIVED
whole-path gap not a measured stall; arena removed the fallback+page-capacity penalties NOT all
costs (kv_bytes/2 ordinary RAM + 70.3ns scatter now a table row); R1 reopen condition replaced
"never"; gap ratio 2.3x not "doubles"; CIs are per-gain-vs-clean; dumbbell x-coords 247/390/579;
kernel claim narrowed to width-4; gate rows gained top-5-overlap criterion, gate-2 incompleteness
caveat, gate-4 "evidence still required", llama cell labels). Planned entries D2-D5 (dispatch
gate, PV numerics, 4+4 blocking, replace-K). Consensus D1 CLOSED. MOVED+RENAMED (user request 2026-08-20): lives at
~/workspace/intel-AMX/tron-amx-distilled.html (NOT rampup/); internal links use rampup/ prefix;
index.html card points to ../tron-amx-distilled.html.
SUPERSEDED 2026-08-21 (user request): tron-amx-distilled.html DISCARDED and regenerated from
scratch per the Notion skeleton "Distilled" (Daily notes > Intel AMX > Generate design md from
my HTML). It is now the single assembled DESIGN DOC (~250KB), NOT the decision record: TL;DR
(jhan's verbatim bullets) / What AMX is (01 secs 1,1.1,2,3,4-minus-intrinsics + 02 secs
2b,4-minus-design-table,4b,6,6b + 01 secs 6(+"Function" column in 6.4 table),7) / Problem
(02 secs 1,2 + pr-rampup 1) / PR changes (pr 3) + mirror deep-dive (status 4 + pr 4.3) / FPGA+AMX
(pr 4.2 + hw-mode Q&A) / Test results (pr 5 with table->BAR charts - Notion said "pie" but the
referenced status sec-2 form is bars and pie cannot show A/B gains; deviation reported to jhan;
prefill deltas computed from t4-suite.txt: canon +44.9/+102.7/+41.3/+90.4, mirror
+46.7/+105.2/+43.6/+100.0) / Geometry (pr 4.1 + gpt-oss-vs-small-llama Q&A: shared head-64
kernel family but kv_mul decides payoff - gpt-oss 8x64=full tile, llama-3.2-1b 4x64=half
(llama.hpp:1539), llama-68m MHA kv_mul=1 below AVX crossover (llama.hpp:1531)) / Glossary
(4 subsections). GENERATOR: exec/gen_distilled.py (durable, rerun to re-sync; single deduped
stylesheet 01-base; transplant internals demoted h3->h4 under h3 skeleton items; hrefs
rewritten to rampup/; unresolved #anchors rewritten to their source doc; duplicate ids
suffixed -2; D-label note added since 02's design-decisions table is omitted). Sol round:
ENDORSE-WITH-EDITS, 4 assembly defects (duplicated stylesheets, flat heading hierarchy,
broken #glossary/#plan/#tests/#design/#targets links, orphaned D1/D6 labels), ALL FIXED in
the generator + verified in output; Sol agreed with the pie->bar decision. Consensus CLOSED.
The DECISION RECORD (D1, rejected alternatives, gates) now lives ONLY in amx-design.md;
index.html card updated to describe the new doc.
ADDITIONS 2026-08-21 (all via gen_distilled.py): (a) page margin fix - doc 01 CSS centers via a
<main> wrapper the assembled doc lacks; body now carries max-width 980 + margin 24px auto +
padding 0 24px. (b) NEW subsection id=pair-worked under VNNI B-operand layout: worked
pair-interleave example with jhan's Scratch-page mock A/B matrices (C[0,0]=3.0 via pair steps
0.5+2.5; the Scratch's stored BYTES were correct, its error = multiplying the stored block as an
ordinary matrix giving 1.0014; Scratch also has a typo 10*0.01 for 10*0.1 in C[1,0]). Sol round:
ENDORSE-WITH-EDITS, 2 defects applied (bf16-representability caveat - printed decimals treated
as exact; "not a matrix you index" softened to "not the original logical 4x4 scalar matrix,
physically two rows of four 32-bit pair lanes"). CLOSED. REVISED 2026-08-21 (jhan approved after
discussion): B replaced by exactly-bf16-representable integers, columns scaled by powers of 8
(rows (k+1)x[1,8,64,512]); A unchanged (already exact). C row0 = [30,240,1920,15360], rows
x10/x100; steps 5+25=30; wrong-reading value 906. Everything exact end-to-end incl. fp32
accumulation -> the bf16 caveat sentence was REMOVED (replaced by an exactness statement).
All arithmetic + bf16 exactness script-verified. (c) TOC at top (skeleton headings get
toc-* ids; 24 entries, all resolve). NOTE FOR PAL CALLS: launching pal_client via plain shell
'&' in a foreground Bash call DOES survive, but gives no completion notification - pair it with
a run_in_background waiter loop on the output file; run_in_background drops stdin redirects AND
$() substitution (use @file args).

NOTE [Why not replace canonical K] ADDED (2026-08-21, jhan request "mirror will be hot in PR
review, distill the deep-dive into source", commit 0ca3aa18b pushed): new Note in kv_cache.hpp
beside the arena note (OUTSIDE the mirror #ifdef - the question applies to every reader):
shared-interface argument (FPGA reads pages as stored / AVX dotter contiguous rows / kill-switch
needs unchanged layout), what replacement would+would-not save (~70ns scatter becomes primary
store), V precedent (one layout serves all consumers), reopen conditions. Also: arena note
gained the isolation method (layout-only control build + dTLB ruled out); cross-refs from
Note [Mirror orientation] and v_base(). The 4 mirror notes now tell the full deep-dive story
in-source. lint-notes passes.

CI-MODEL A/B ROUND (jhan 2026-08-21, QUEUE row 18): from the nightly-CI list only
mixtral-8x7b-instruct-v0.1-tp2 @8u is gate-supported AND untested (llama-3.2-3b kv_mul 3;
llama-3.3-70b kv_mul 8 - 3.3 uses the llama_3p1_70b config; qwen-2.5-32b kv_mul 5;
llama-3.1-8b already in t4-shapes). exec/p2-ci-models.sh launched detached on 3bda 06:56Z
2026-08-21 (waits 09:30Z, quiet+cleanup+campaign guard; 3 arms x {2K,8K} x 3 reps @ 8u ->
results/ci-models/mixtral-ab.txt, marker logs/p2-ci-models.done). Weights verified. NOTE:
mixtral is MoE (8 experts) - AMX touches only attention; attention share of decode may be
smaller than qwen's, so expect smaller end-to-end gains at equal ctx.
MEASURED (2026-08-21 09:52Z, results/ci-models/mixtral-ab.txt, zero failures): decode @8u vs
kill-switch baseline - ctx2K: canonical +2.3%/mirror +1.2% (within noise of each other);
ctx8K: canonical +9.4%/mirror +18.6% (23.1->25.3/27.4 tok/s per user). Prefill: 2K +2%;
8K +56%/+55% (95.4->~149). As modeled: MoE FFN dominates short ctx, gains concentrate at
long ctx; prefill parity canonical~mirror (mirror edge is decode-side). 4th gate-family
confirmed (mixtral 32Q/8KV/128). Lease BUSY format also verified this window (QUEUE):
JSON {"state":"busy","owner":"system_ci",...updated/expires epochs, 15-min TTL, refreshed
~20min, REMOVED on CI completion} - both parser paths live-verified, writer deployed.

IN-REPO DESIGN DOC (2026-08-23, spec input-2-ai/generate-design.md, commit 6734e461d pushed):
doc/intel-amx.md in PR #3879 - brief expert-level design doc, referenced by future AMX PRs.
Naming: kept intel-amx.md per doc/ convention (short topic slugs; told jhan
intel-amx-leveraged-features-design.md too long, middle option intel-amx-design.md). Structure:
AMX intro (unit/ISA table spec-vs-measured/throughput reality/VNNI pair rule/precision/system
reqs) + PR3879 (target incl USE_HW_ATTN=0 main + FPGA composition, model+measured numbers,
mirror layout + why-two-copies WITHOUT naming Bill per spec, geometry minus tp-paragraph minus
4.1.1 per spec). Sol round 2 (round 1 = files_required; PAL continuations don't survive, resent
self-contained with 6 source files): ENDORSE-WITH-EDITS, 8 defects ALL APPLIED - 64% share
labeled archived estimate; precision contract scoped finite/non-subnormal + archive pointer
replaced by in-tree Note; methodology qualifiers scoped (8-rep CI = decode only; prefill 3-rep;
energy separate); mixtral MoE causal dropped; 300ns = measured gap not component cost;
"complete table"/"occupies TMUL"/"saturated core" softened; cmake location named
(src/tron/CMakeLists.txt:170,175 - NOT root). TWO NOTE CORRECTIONS shipped in same commit:
dispatch Note "positions below 127" fixed (unit is the PAGE; young query's complete pages take
AMX) + finite/non-subnormal + deliberate-RNE recorded; arena Note gained in-block -33% capacity
fact. KEY DISCOVERY: make lint-notes VALIDATES doc/*.md Note references against in-tree
definitions (literal "Note [...]" placeholder text breaks it - write around it). Consensus
CLOSED.

PR-RAMPUP 4.1.1 (2026-08-21, jhan request): new subsection id=gate-fail in gen_pr_rampup.py
(now durable at exec/gen_pr_rampup.py + builder exec/_gate_fail_411.py, inlined at patch time;
flows into tron-amx-distilled via the 4.1 transplant). Content: why kv_mul 3/5/8 CI models are
not served (constexpr gate = nothing fails as shipped) + SVG of the forced-gate counterfactual
(fixed 4-head window: kv_mul 3 = neighbor-group read + OOB read/write on last kv_head, slots
28-31 of 24; kv_mul 5 = 5th head never updated + x4-vs-x5 stride misattribution; kv_mul 8 =
half skipped + x4-vs-x8 stride). 4.1 status table refreshed: mixtral -> measured (exact cells +
prefill). Sol round: ENDORSE-WITH-EDITS, 3 defects ALL APPLIED (kv_mul 8 = TWO full query tiles
not "fills better" - 4x128 already fills one exactly; "stale garbage" -> "remains uncomputed,
scratchpad entry not updated" (lifecycle not established); mixtral row = exact numbers + correct
results/ path, causal "expert layers dominate" phrase dropped as unmeasured). CLOSED.

PRECISION REGRESSION TEST (2026-08-20, Alexey's ask via jhan, commit 39ef03ece pushed):
t/t_amx_numerics.cpp - pins AMX kernels to AVX within the numerics contract (deltas = fp32
accumulation order + PV weight rounding ONLY). 3 cases: (1) qk_st_128x4 vs REAL dotter<bf16,128>,
envelope 1e-4*abs_product_mass+1e-6, 4 seeds; (2) qk_mirror_128x4 BIT-IDENTICAL to canonical AMX
(same 4x32-dim step order - invariant behind the byte-identical canary); (3) pv_128x4 within acc
slack of exact-RNE-weight fp64 ref AND within exact per-element |RNE(p)-trunc(p)|*|v| envelope of
the truncated-weight (AVX) ref, envelope asserted non-trivial. Passes on 3bda: 2305 assertions
(PV sits ~1e-3 from AVX-ref inside ~9e-3 envelope; ~6e-8 from own ref). Skips WARN when AMX
unavailable; explicit skip case without TRON_AMX_DISPATCH. Prior coverage did NOT have this:
t_amx_mirror = layout bytes, t_amx_logit_ab = system logit-dump tool, amx_fused_bench ref rounds
like AMX (cannot catch digression). Test construction facts: dotter needs
tron::const_view<bf16,true,false,seq<128>>{ptr}; V pair-interleave = storage[(pair*HD+d)*2+j] =
V[2*pair+j][d]; inline Note mentions in tests must be "See Note [...]" or lint-notes reads them
as definitions. 3bda idle-core sample 2026-08-21 00:0xZ (serving active, load 125): fully-idle
physical pairs incl (22,166)(23,167)(24,168)(36,180).

AMX OVERHEAD SECTION 6.4 (2026-08-21, Bill's runtime-overhead question): doc 01 new sec 6.4
id=overhead; bench exec/bench_amx_overhead.cpp -> results/amx-overhead-20260821.txt (core 22
nice 19, serving active - cycles via perf stat minus null run; TSC 2.700 GHz). MEASURED 6962P
vs Intel Table 20-2 (opt-manual:31320-31329, SPR-era; "TILETRELEASE" typo is the manual's):
LDTILECFG 182-216 (spec 204), STTILECFG 19, TILERELEASE 15 (spec 13), TILEZERO 0.5 (spec thr 0),
TILELOADD 8.4, TILESTORED 16.1, TDPBF16PS 16.2-16.4 both dependent-C-chain AND independent
(52-cycle consumer-latency path NOT measured). One-time: arch_prctl 887ns/process; XFD first
TILEDATA insn 4-9us/thread; LDTILECFG+TILERELEASE pair ~229c per region. KEY FINDINGS:
(1) STORE-FORWARDING CORRECTION - "tile stores cannot forward to vector loads" was WRONG:
opt-manual 20.15 (32781-32784) supports 64B tile-store->vector-load forwarding (hard restriction
is opposite: any store->TILELOADD, 32752-32758); measured store_fwd == store_far (16.0-16.2c).
~300ns canonical gap = transpose+traffic NOT isolated. Fixed in 5 places: Note [Mirror
orientation] (commit dbb1233e7 pushed), fused-sweep.html, 04-amx-action-plan.html,
tron-amx-distilled.html x2 (doc 02's store->TILELOADD row was the correct direction, kept).
(2) Port-5 closure NOT reproduced on 6962P: 80-FMA named-register block after TDP = +0.9+/-0.1c
(one block size, not a general disproof); pure block anomalous 2.48 FMA/cycle (label: anomalous
probe result, not port-map evidence). (3) The real AMX<->AVX mixing cost = LICENSE CLOCK:
same cycles, ns/iter 12.0->17.2 (2.70->1.93 GHz, serving-active env). BENCH TRAPS: __m512 x[10]
array stays in MEMORY at -O2 (141c/iter artifact - use named locals); 4 chains = latency-bound
(port-blind); whole-process perf cycles dominated by the 50ms TSC calibration spin (subtract
null run). Sol round on 6.4: ENDORSE-WITH-EDITS, 8 defects, ALL APPLIED verbatim (rep counts in
header; TDP=reciprocal-throughput wording; first-LDTILECFG not a one-time charge; width-4-L2
scoping + drop unverified "4KB"; 2.48 = anomalous; cycles "nearly unchanged" not "equal"; exact
result-file citations for 686-1800ns/kill-switch/decode/energy; takeaway rewrite). Consensus
CLOSED (recorded here; doc 01 has no in-document log).

MIRROR-COST SECTION ADDED (2026-08-24, jhan review question "why does the mirror arena code not
impact performance - pipelining/concurrency?"): tron-amx-distilled.html new authored section
"The cost of maintaining the mirror" (in gen_distilled.py: MIRROR_COST + lanes_mirror_write(),
PARTS entry after the mirror deep-dive). Content: allocation once at startup (AMX-gated);
reads unchanged (dense kv_block, kill switch clean); the write = only recurring cost, 70.9 ns/row
RE-MEASURED (exec/results/bench-scatter-20260824.txt: 5 reps cores 24/36 range 70.8-71.0, one
107.7 core-23 interference outlier recorded; serving active) -> 0.567 us/(token,layer) = 2.2% of
the 26.2 us slot (1060.87 tok/s 8K prefill / 36 layers), 20.4 us/token serial-equiv, decode
0.2-0.4% est. Wall-clock-lanes SVG (compute/FPGA+DMA/RX lanes, orange scatter tick to scale,
"conceptual execution lanes, not an execution trace"). Honest framing per Sol: concurrency real
but UNQUANTIFIED; no mirror-specific deferral (synchronous in save_k, L1-hot); RX on per-layer
critical chain so not hidden by construction; A/B = ground truth for NET only (mirror also
changes the QK kernel - cannot decompose the write's wall-clock share). Sol round:
ENDORSE-WITH-EDITS, 12 defects, ALL APPLIED verbatim-or-integrated. Consensus CLOSED.
Also same day: PR 3879 review-response edits (see commit-pending working tree in tron-amx):
renames qk_st_128x4->qk_canonical_128x4, pv_128x4->weights_times_v_128x4, p1_share_counters.hpp->
page_share_counters.hpp (tron::page_share, TRON_PAGE_SHARE_COUNTERS), planning-token sweep of all
PR files (P0/P1/P2/P3/P5/T1/T4/doc-03/doc-04/D8/A8/consensus/fused-sweep refs removed),
LAYOUT_ONLY leftovers deleted, new t/t_amx_arena_leak.cpp (counts global aligned array
new[]/delete[] balance across book ctor/dtor; passes on 3bda with arena exercised); all three
AMX unit tests pass, full build + make format + lint-notes clean.

ARENA-NO-GROW SECTION (2026-08-24, jhan question "why doesn't the mirror grow with the KV
cache / does scatter allocate?"): distilled doc new h3 "Why the arena never grows" (ARENA_NO_GROW
in gen_distilled.py, after the mirror-cost section). KEY FACTS (Sol-verified): each BOOK is
fixed-capacity (n_pages const; occupancy grows, arena never resizes) but the CACHE can grow by
creating additional books via try_create ("cache growth" factory) - never say "the KV cache
never grows"; mirror = ONE nothrow kv_bytes/2 allocation ATTEMPT per book ctor (fail -> null ->
fallback); scatter_k_mirror row = head_size/2 pairs = 2*head_size bytes (head 128: 64 pairs /
128 values / 256 B - NOT "128 pairs"); address arithmetic lives in book::mirror_at_storage
(k_mirror_data delegates); 32u/48u capacity probe = exec/results/t4/cap-sweep.txt (cap-over.txt
is the 56u/64u over-budget probe). Sol round ENDORSE-WITH-EDITS, 8 defects, ALL APPLIED.
Consensus CLOSED. Review-response commit ab1e50fae pushed to jhan-amx-p0 same day (15 files:
renames, braces, constants, mask sized from max_minibatch_size, t_amx_arena_leak).

PERF ROUND 2026-08-25 (jhan request, latest jhan-amx-p0 = bbb55ae5f + comment-only tree, before
CI): 2 arms (canon = DISPATCH ON/K_MIRROR OFF, mirror = both ON) x 8 cells x 3 reps, 48/48 runs,
00:45-01:40Z. Script exec/p2-perf-round-20260825.sh (+ p2-perf-round-resume.sh, NOT needed);
results exec/results/perf-round-20260825/{perf-round.txt,perf-round.html}; report generator
exec/perf-round-report.py. VERDICT: latest branch matches the Aug 19-21 references within noise
in every cell (decode |delta| <= 2.5%, mostly <0.5%); mirror-over-canonical decode
+0.3/+4.0/+5.9/+9.1% qwen (1u2K/1u8K/8u2K/8u8K), +3.9/+5.0% llama (1u8K/8u2K),
-0.1/+8.9% mixtral (8u2K/8u8K). Builds: two cmake reconfigures of gen/ (OFF then ON) took 13 min
total at -j96 on the quiet machine; runs ~35 s (qwen/llama) to ~1.5 min (mixtral).
PROCESS FINDINGS: (1) jhan CANNOT read the system journal without sudo - unprivileged journalctl
returns nothing, so the "zero rinzler traffic" checks in older campaign scripts (p2-ci-models.sh)
were vacuous; use `sudo -n journalctl` + `sudo -n ss` (non-loopback established conns on
13000-13003) - the four 127.0.0.1 keepalives are always present when idle. (2) The daily
rinzler@0-3 instance (ActiveEnter 08:30Z) showed zero journal entries for 60 min and only
loopback conns -> stopped per policy at 00:50Z; not restarted (02:45Z timer brings it back).

MIRROR ELIGIBILITY GATE (2026-08-25, from a mocked review: "arena allocated + save_k scatters
for EVERY geometry under TRON_AMX_K_MIRROR" - TRUE; gated only on available(), not geometry).
Fix (jhan approved design: a second book ctor with NON-defaulted bool amx_mirror_eligible):
amx_attn::shape_ok(head_size, kv_mul) in the iface header = THE single gate used by dispatch,
both apply_page_tok if-constexpr blocks, save_k write-through (now `if constexpr
(k_mirror_shape_ok)` - compiled out for ineligible geometries), and arena allocation.
kv_cache.hpp: tron::amx_mirror_eligible(plugin::attention_kernels) constexpr helper; book 3-arg
ctor delegates to new 4-arg ctor; try_create 3-arg delegates to 4-arg; adopt ctor carries flag;
maybe_allocate_mirror_arena(slots, eagle, eligible). Scheduler: flag lives in node_base (beside
storage_kv_slots/support_eagle), set at the root by full_scheduler<model_t> from
model_t::plugin_t::attention_kernels, propagated to children, passed to try_create (model_t is
NOT in scope at the try_create site - node<book> - my first attempt failed there). New test in
t_amx_arena_leak.cpp: static_asserts of the gate on registry shapes + head-64 book with
eligible=false performs ZERO aligned allocations; control (legacy ctor) allocates exactly 1 when
AMX available. LESSON: kv_cache.hpp's amx_attn_iface.hpp include was #ifdef TRON_AMX_K_MIRROR ->
canonical build broke (undeclared amx_attn); include is now unconditional (header is
intrinsics-free). VERIFICATION METHOD under CI/serving: single-core `-fsyntax-only` of TUs from
gen/compile_commands.json with -D flags stripped for canonical/clean variants
(exec/logs/syntax-check*.sh) - caught both errors cheaply; full build+tests via
exec/p2-verify-after-ci.sh (waits for lease release; if serving has traffic it builds pinned -j6
instead of stopping rinzlers). Mirror build: 4 tests pass incl. new test (5 assertions/2 cases).
Canonical build re-run pending at time of writing. Doc sentence fixed (canonical vs mirror).

HW-MODE COMPOSITION (2026-08-19, jhan question, pr-rampup.html section 4.2): AMX is NOT
bypassed when FPGA attention is on. Dispatch has no uses_hw check; it sits inside the sw
page loop which runs in both modes (self_attention.hpp:1344 run_visible_in_software =
window || !uses_hw; :1526 sw_required vs visible per query). In hw mode CPU still gets:
young positions (<127 always sw; at most 1 full page each), window/software_only layers
(all-visible sw), hw-ineligible configs (everything sw). Full fully-visible pages among
that work take AMX; partial pages -> AVX as always. Measured +15..28% is all-software mode.

ALEXEY-PERSONA REVIEW OF PR 3879 DONE (2026-08-24, jhan request; deliverable
~/workspace/intel-AMX/PR3879/alexey-review.html, 69 inline comments, verdict CHANGES_REQUESTED-grade).
OPEN DEFECTS IN THE PR (not yet fixed as of head bbb55ae5f): (1) book::mirror()/mirror_at_storage index
the arena by logical slot and ignore set_storage_view (kv_blocks_alias), so with EAGLE the draft's save_k
scatters K_d into the VALIDATOR's slot-0 mirror plane (same pages, draft runs behind validator); eagle
mirror region written only by copy_storage_slot, never read - K_MIRROR + support_eagle is broken;
verified by 3 agents + 2 refuters. (2) t_amx_logit_ab registered LABELS fpga and REQUIREs AMX_LOGIT_OUT
-> FPGA CI lane fails once CI runs (draft skips CI; label "Run CI" overrides). (3) doc/intel-amx.md
lines 44-45 contain "xxx:" editor notes. (4) Mirror arena + save_k write-through + copy_storage_slot
rebuild are gated on available() only, not on the 128x4 reader gate -> RAM + RX cost for ineligible
geometries; doc "no AMX code compiled into its instantiation" false under K_MIRROR. (5) Arena nothrow
allocation failure is silent and the K_MIRROR build has no canonical-AMX fallback (#else'd out).
(6) Note [K mirror coherence] omits the real publication mechanism (ready/pending partition +
upstream_kvs_ready latch; mark_k_complete is GOF-only). (7) No test reaches apply_page_tok with a
non-null pack (t_llama_unit "apply and join page ranges" is kv_mul=2); t_llama_unit mirror check covers
copy_storage_slot rebuild for token 0 only. (8) 64B-aligned contract vs std::vector amx_qpack; QK
tolerance 1e-4 = 13x the 127-ulp reorder bound; amx_fused_bench.cpp = unbuilt fork of every kernel in
src/. Reuse targets found in tree: cpuid_bit + lazy<bool> is_rtm_supported (h/system/mwaitx.hpp),
tron::finally (h/common/util.hpp:73). Main moved 388 commits (still MERGEABLE); on rebase, main's
Note [DMA-sized KV books] (9076993a0) needs the arena as an exception.

ALEXEY-PERSONA REVIEW ROUND 2 (2026-08-25, head cc8a86bb3 = +1 commit "Gate the K mirror arena and
write-through on the AMX attention shape"): verdict still CHANGES_REQUESTED-grade. Fixed: xxx lines,
arch_prctl sentence, doc:189 gate statement (3 of 69). Partial: 8 (doc 64% lost its qualifier and still
unsourced; 229-cycle frequency removed not corrected; doc code block still shows old literal gate;
k_mirror_on redundancy; HEAD_SIZE/GROUP_HEADS not tied to shape_ok; >= 1 vs == 1). Still open: EAGLE
storage-view aliasing (mirror() unchanged, kv_cache.hpp:1244/1250), t_amx_logit_ab fpga-label failure,
PR body stale ("allocated only when AMX is available" now also needs eligibility; no mention of doc,
kv_block_planes, full.hpp plumbing). New in cc8a86bb3 he'd press on: 3-arg book/try_create default
amx_mirror_eligible=true (kept for tests + sequence_cache_behavior concept kv_cache.hpp:1328-1330 - update
concept, drop overloads); comment on 4-arg public ctor false (scheduler goes try_create -> adopt ctor; only
caller is the test); doc "8 models" lists 6 (phi-4 40/10/128 passes shape_ok and was dropped); new test
exercises public ctor not try_create path, vacuous on non-AMX host; "can never disagree" header claim
holds only for scheduler-created books (rebuild writers ungated; legacy forms pass true); mixed-kernel
models (none in tree) would over-allocate. Deliverables: PR3879/alexey-review.html (round 2, with source
snippets), PR3879/alexey-review-2.md, PR3879/alexey-review-1.html (round-1 archive); jhan's own triage is
PR3879/alexey-review.md (DONE/IGNORE marks) - read it before any round 3. Generators gen_review2.py +
round2_data.py + r2/collect.py in session scratchpad c79e32fa.

OPTION A FIX FOR DEFECT (1) IMPLEMENTED 2026-08-25 (jhan chose A over B; COMMITTED 96b5a6c72 + pushed, PR body updated; in
~/workspace/tron-amx on top of 8e22b0aa5): kv_cache.hpp adds std::optional<kv_storage_offset>
mirror_view_offset_ (set/reset by set_storage_view/reset_storage_view); book::mirror() maps logical
slot 0 to it under the view (TRON_ASSERT_EQ(slot.i,0)); mirror_at_storage got kv_block_at_storage's
offset-range assert; Note [K mirror coherence] states the view rule. Tests in t_llama_unit.cpp: EAGLE-view
test extended with mirror checks; new case "K mirror stays coherent for both physical slots under the
EAGLE view" (64 interleaved writes, whole-plane byte compare per physical slot); EAGLE append test checks
the moved token's mirror column in both views. Verified on delphi-3bda (gen/ = RelWithDebInfo, DISPATCH+
K_MIRROR ON): full t_llama_unit 23 cases/144,855 assertions pass, 0 WARN-skips; NEGATIVE CONTROL on the
original header fails exactly the 3 new checks (:314 same plane, :370 plane mismatch, :1128 column under
view); t_amx_mirror + t_amx_arena_leak pass. clang-format-19 clean. Recipe: exec/optA-verify.sh (swap header,
rebuild target, run named Catch2 cases, restore); build = nix develop --command cmake --build gen --target
t_llama_unit -j64 (~6 min incl. trace re-exports; ccache makes the re-run ~30 s). Explainer doc:
PR3879/kv_cache-hpp-1199.html (sections 3 EAGLE, 8 status, 9 coverage matrix). Not done: commit, PR body,
t_generate_2 [eagle] end-to-end run (needs eagle-llama-3.1-8b-instruct weights on 3bda - unchecked).
E2E EAGLE RUNS 2026-08-25 (t_generate_2 on 3bda; llama-3.1-8b-instruct-good has HW attention "default off",
so all runs are software attention = AMX mirror path): fixed build passes all [eagle] cases; 1100-token case
acceptance 1.70/0.86 with mirror vs 1.68/0.84 with TRON_AMX_DISABLE=1, texts identical for 204 tokens then a
near-tie flip. NEGATIVE CONTROL (pre-fix header): test still PASSES (1.76/0.88) but text diverges from both
fixed and no-AMX runs at generated token 57 (~position 67 = first full page readable via the mirror). So the
existing [eagle] e2e tests are blind to this bug class: the 50-token agreement case never fills a page; the
1100-token case checks only acceptance thresholds. Follow-up idea (not done): T=0 agreement case past 2 full
pages (~200 tokens). Catch2 trap: commas in test names must be escaped as "\," in the name filter, else the
name is split into two filters (bit me once; "No test cases matched" is the tell). Scripts: exec/optA-e2e2.sh,
exec/optA-e2e-neg.sh; logs exec/logs/optA-e2e2-runs/.

ALEXEY-PERSONA REVIEW ROUND 3 (2026-08-25, head 96b5a6c72 = cc8a86bb3 + 8e22b0aa5 "named constants" +
96b5a6c72 "K mirror follows the EAGLE storage view"): still CHANGES_REQUESTED-grade. FIXED (5): EAGLE aliasing
(option A: mirror_view_offset_ set/reset with the view, TRON_ASSERT_EQ(slot.i,0), 3 new t_llama_unit cases that
fail on the old header - verified by reasoning), gate spelled once, tile_row_bytes now used, PAGE tied to
page::page_size, q_pack_elems literal in test. STILL OPEN blockers: t_amx_logit_ab fpga-label failure; legacy
3-arg book/try_create default amx_mirror_eligible=true (now 3 test users incl. the new EAGLE test); doc
"8 models" lists 6. PR body updated (arena condition + EAGLE view + tests) but still omits doc, kv_block_planes,
v_data/v_base, #errors, fill_random, full.hpp plumbing. NEW in round 3: constants named with values
(HEAD_SIZE_128 etc., UPPER_CASE; h/tron/{models,kernels,scheduler} is 172/179 lower_snake, 0 value-suffixed) +
static_assert guarding the name; header claim "Every shape literal ... derives from these three" false
(DIM_STEP, PANEL_ELEMS, step*4, half*64 literals remain); view state now in two members (kv_blocks_alias +
mirror_view_offset_) - layout Note :495 suggests a mirror_alias pointer instead; Note "Both sites ... mirror()
remaps" overstated (copy_storage_slot is physical-offset, view-independent); plane formula now 10 spellings
(two new lambdas duplicate require_mirror_matches; testutil.hpp already included); REQUIREs at
t_llama_unit:1133-1140 implied by the lambda; EAGLE-view block :309-321 dominated by the coherence case;
no test drives production save_k under the view (ask: record an EAGLE pair run with K_MIRROR=ON).
EAGLE facts (for the "how likely EAGLE+mirror together" question): prefer_eagle reads TRON_USE_SPECULATION,
disabled by default (full.cpp:40-43); runtron --draft eagle sets support_eagle per run; not enabled in any
CI/benchmark config; drafts exist for llama-3.1-8b (32/8/128, AMX-eligible) and llama-3.3-70b (ratio 8,
ineligible); draft = validator's model_t with max_layers=1 -> same shape_ok. Deliverables: alexey-review.html
(round 3, section 1a = EAGLE explainer + option-B likelihood table + SVG), alexey-review-3.md,
alexey-review-2.html archived. Generators gen_review3.py/round3_data.py/r3/collect.py in scratchpad c79e32fa.
DEFECT (2) t_amx_logit_ab FIXED 2026-08-25 (review R1-57): add_catch_test entry moved inside if(BUILD_INGEST_MODELS)
with DISABLED TRUE (t_clearhbm precedent); header comment carries the manual two-run recipe. Verified on 3bda:
ctest manifest DISABLED=True, `ctest -L fpga -R amx_logit` -> "Not Run (Disabled)" exit 0, bin/slice manifest filter
has no enabled amx_logit entry, binary still builds (BUILD_INGEST_MODELS defaults ON; CI passes ON). Mechanism note:
add_catch_test registers ONE ctest entry per executable via add_test + set_tests_properties (the
`elseif(NOT DEFINED TEST_SIMPLE)` catch_discover_tests branch is dead because cmake_parse_arguments always defines
option vars) - so DISABLED applies to the whole binary. Still open from the persona review about this tool: wording
at amx_attn_iface.hpp:75 ("is not set" -> "is not 1") and the t_amx_numerics.cpp:143 comment claiming a check nobody
performs. PR body test line updated.
R2-05 (kv_cache.hpp:182 amx_mirror_eligible = ANY kernel; arena kv_bytes/2 sized for ALL slots) EXPLAINED 2026-08-25 as
subsection 4.1 of PR3879/kv_cache-hpp-1199.html (Table 7 gates, Figure 3). Verified facts: save_k write-through and the
qk_mirror reader are per-operation compile-time shape_ok gates; copy_storage_slot rebuilds EVERY slot's plane (incl. EAGLE)
with no gate -> in a mixed model ineligible planes cost RAM + page-move scatter (est. 70 ns x head/128 per row per kv_head)
but never affect results. No plugin mixes eligible+ineligible today: llama/mock 1 kernel; generated gemma-4 (gen/) has 2
kernels but both ineligible (256/512-wide heads); test arrays in t/ all-ineligible. Recommended fix = the reviewer's
Option 1 (comment consequences + Note sentence + two-kernel static_assert in t_amx_arena_leak); Option 2 = per-slot mask
computed by the scheduler from attention_operations x attention_kernels (book lacks kv_mul), passed where the bool goes
today; mirror_at_storage -> nullptr for masked slots makes copy_storage_slot skip via its null check. Not implemented.
WHOLE-PATH BENCH (src/amx_fused_bench.cpp) EXPLAINED 2026-08-25 as subsection 4.2 of PR3879/kv_cache-hpp-1199.html
(jhan asked for a plain word instead of "fused": use "whole-path benchmark" = QK+softmax+PV of one page timed back to
back; rampup/fused-sweep.html already uses that name). Verified facts: 5 variants avx/amx44/amx62/amxqk/amxpl (header
lists 3); args [Nq][iters][variant][pages]; scalar-float reference, rel tol 2e-2, measured 8e-5 at Nq=4 (3e-4 at Nq=16);
amxqk's K mirror is packed BEFORE the timed loop (its write cost excluded) while canonical variants re-pack Q inside the
timed region. NUMBERS: recorded v2 sweep Nq=4 pages=1: avx 1618 / amx44 1250 / amx62 1279 / amxqk 686 ns. THE 982 ns IN
Note [Mirror orientation] IS NOT A RECORDED ROW: QUEUE.md:59 prose = amxpl on an 8-page ring (vs 1006 non-pipelined);
the sweep never ran amxpl or 8 pages. So "982 vs 686" mixes ring sizes; like-for-like recorded gap = 564 ns. Our own
pages amx-design.md:75, rampup/01-amx-rampup.html:733, rampup/02-tron-decode-amx-plan.html:1033 cite fused-sweep-v2.txt
for 982 - FALSE citation, fix them. R1-54 recheck: vexp poly error is 3.3e-6 (base-2 remainder (0.5 ln2)^6/720), not 2e-7.
Recommended: reviewer's option (b) - drop the file, keep Table 9 + compile/run line in doc/intel-amx.md; else (a) t/
target calling the real amx_attn kernels.
OPTION (b) DONE 2026-08-25, commit ff7269a9f (pushed): src/amx_fused_bench.cpp removed; whole-path benchmark record
(Table: Nq=4, pages 1/512/16384, avx/canonical 4+4/6+2/mirror) + compile/run lines added under "Mirror layout" in
doc/intel-amx.md; Note [Mirror orientation] now says ~560 ns (1250 vs 686, L2-resident page) and cites the doc record;
amx_attn.cpp comments repointed. jhan's uncommitted doc hunks were kept OUT of the commit by staging HEAD+my hunk as a
blob (git hash-object -w + update-index --cacheinfo) - pattern for committing only my hunks of a co-edited file. PR body
harness bullet replaced. R1-51..56 moot. Still to fix outside the PR: amx-design.md:75, rampup/01:733, rampup/02:1033
cite fused-sweep-v2.txt for 982 ns (false).
CORRECTION 2026-08-25 to the line above that says "~300ns, 982-686": 982/1006 ns were an UNSAVED pipelined-epilogue
run (8-page ring; QUEUE.md prose only). The saved sweep (results/slot1/fused-sweep-v2.txt) gives canonical amx44 1250 vs
mirror amxqk 686 ns at Nq=4, 1 page = 564 ns gap. All our pages (amx-design.md, rampup/01, 02, 04, tron-amx-distilled
regenerated via exec/gen_distilled.py) now say so; doc/intel-amx.md + Note [Mirror orientation] in tron use 1250 vs 686.
901f30d8e (2026-08-25, pushed): jhan asked to DROP the "Whole-path benchmark record" paragraph again ("spending too much
time on intel-amx.md") - doc keeps only the one-line numbers in the canonical-K bullet (1250 vs 686 ns, L2 page, width 4,
6962P, 2026-08-19); Note [Mirror orientation] + amx_attn.cpp comments now cite the measurement, not a record; PR body
updated. Table 9 in PR3879/kv_cache-hpp-1199.html is the only full record now. Lesson: jhan wants the tron doc lean -
don't expand doc/intel-amx.md beyond what a reviewer explicitly asked for.
a5ef65761 (2026-08-25, pushed): jhan's doc/intel-amx.md round-3 fixes committed on request (8 hunks: region frequency,
SMT condition, ~64% fit derivation, Model paragraph -> pointer to PR body, arena eligibility, shape_ok gate paragraph +
code block, "8 models" count dropped). Working tree of tron-amx now clean; PR head a5ef65761. Still open per round 4:
R2-01 half (phi-4/granite omitted, no derivation rule), R2-03 default-true 3-arg ctor, R1-58 compile-only config;
R1-51..56 moot (file removed in ff7269a9f).
2026-08-25 late (all pushed to jhan-amx-p0): 234c02bde removed doc/intel-amx.md from the PR (archived at
github.com/jhan-positron/notebook artifacts/intel-amx/intel-amx.md, notebook f3d1ee4; PR body points there);
b2010bee9 3-arg book/try_create now delegate with amx_mirror_eligible=false, node_base default false, 8 mirror-test
sites pass true (R2-03 resolved jhan's way); b85fd2789 amx_attn.cpp header history sentence dropped (R5-02);
298dbad0f TODO(jhan) at the two AMX options -> tron issue #3997 (no CI config compiles/runs the AMX code; accepted
until the CI team adds one; interim = verify both configs on delphi-3bda before pushing). PR body has a "Validation
and CI coverage" section WITHOUT run logs (jhan: logs stay out of the PR). R1-58 is closed by decision - skip it in
review rounds. Verify run exec/p2-verify-after-ci.sh launched on delphi-3bda 2026-08-26T04:53Z for head 298dbad0f
(waiting for the System CI lease); result to be appended here when done. Last complete run before that: 17:33Z
(pre-tonight head), mirror 5/24576/2305/128206 and canonical 1/1/2049/120014 assertions, all passed
(exec/logs/p2-verify-after-ci.round4.txt).
35b3f3cae (2026-08-25, pushed): R1-49 (packers no longer memset padding; owner zeroes once - thread_local vector
resize + test buffers = {}; both header contracts say padding must be zero on entry) + R1-50 (cvtne2ps_pbh arg-order comment).
Verified: t_amx_numerics 2305 assertions (AMX vs AVX, covers both packers), t_llama_unit [kv_data]. R1-47 = IGNORE (jhan).
R1-48 suggestion given (exact-match "1" + R1-16 wording; optional INIT log line) - awaiting go.
3fa11d911 (2026-08-25, pushed): R1-48 exact-match "1" for TRON_AMX_DISABLE + R1-16 contract wording. Verified on 3bda:
unset/=10 -> full t_amx_numerics run, =1 -> AMX unavailable skips. PR head now this sha. triage.json has 31 entries.
2026-08-26: round-6 mock review at head 3fa11d911 (jhan's 275fa89a0 comment trims, 35b3f3cae pack padding zeroed once
by the buffer owner, 3fa11d911 exact-"1" kill switch, plus the three default-false/header/TODO commits): 73 -> 61 open,
0 blockers, 11 fixed, R1-47 declined / R1-58 deferred per triage.json, 1 new (R6-01: 'so callers can reuse the same
buffer' is false now that padding is a precondition). Verdict still CHANGES_REQUESTED on the A3 false-sentence stack
(R1-10, R3-02, R2-06, R1-12, R1-14 date, R1-15 new wording). Deliverables PR3879/alexey-review-6.md + alexey-review.html.
Verify run on delphi-3bda for 298dbad0f still queued behind System CI as of 05:55Z (monitor armed; result to be appended).
2026-08-26 verify run (exec/p2-verify-after-ci.sh on delphi-3bda; queued 04:53Z, CI lease released ~11:48Z; built the
shared checkout as it stood = head 3fa11d911): mirror build 11:48Z - t_amx_arena_leak 5/2, t_amx_mirror 24576/1,
t_amx_numerics 2305/3, t_llama_unit 144855/23, all passed; canonical build 11:52Z - 1/1, 1/1, 2049/2, 120014/22, all
passed. AMX was live (arena/mirror cases ran). Log: exec/logs/p2-verify-after-ci.txt (previous run kept as
p2-verify-after-ci.round4.txt). Not pasted into the PR by jhan's decision. Run finished 12:23:40Z, marker ok, mirror config restored in gen/.
