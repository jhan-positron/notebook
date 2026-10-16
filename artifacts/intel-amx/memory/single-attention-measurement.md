---
name: single-attention-measurement
description: "2026-09-01 DONE: single attention (one query x one KV page x one KV head) MEASURED via phase probe stamps 7606-7627: AVX 3.64 / canonical 2.89 / mirror 2.66 us at ctx 8192 (1.37x / 1.26x); common work 4-12%; QK+PV memory-limited; per-op fixed 9-13 us; peer-session coordination rules for the fence worktree"
metadata: 
  node_type: memory
  type: project
  originSessionId: 2549245f-706d-4cdd-bc17-40d5d5064a07
  modified: 2026-09-01T19:33:47.404Z
---

jhan (2026-09-01): "single attention time is important because it does not change with number of
users and context length" - wants it measured and contrasted AVX vs AMX, with the common work
(softmax, state update) recorded separately. Page section: PR3879/make-sense-amx-vs-avx.html 7.2.1
(TOC + numbered h2/h3/h4 ids added the same day).

Definition used: one apply_page_tok call = 1 query token x 1 KV page (64 tokens) x 1 KV head
(4 grouped query heads). Units per pass = 36 layers x 8 KV heads x ceil(KVlen/64); +4.5 units per
KV token per pass. Stamp 7605 = worker-0 wall over 36 ops, 27 attention workers in the fence runs
(28 app cores), so CPU time ~= 27x wall. Norms (input RMSNorm, Qwen3 q_norm/k_norm) run BEFORE the
attention op in the main workers; only the softmax denominator is inside.

Estimate (est., fence round 3 slopes x 27 / 4.5): per unit AVX 4.06 / canonical 3.34 / mirror
3.08 us in the RAM regime (2K->8K); cache regime (256->2K) 3.08 / 2.49 / 2.37 -> mirror 1.30-1.32x,
canonical 1.22-1.24x; kernel bench (fused-sweep-v2 Nq=4; amxqk = mirror kernels, amx44 = canonical,
recovered source ff7269a9fa^) gives 1.77x / 1.39x RAM, 2.36x / 1.29x hot; serving adds +0.9/+1.0/+1.3
us per unit (AVX/canon/mirror). Hot-cache common work (softmax+pack+update) ~0.42 us of a 0.69 us
AMX unit (bench-derived). Scripts: scratch chart.py -> PR3879/make-sense-amx-vs-avx/figG-single-attn.svg.

Measurement: probe commit (kvwait stamps 7606-7627, thread_local counters in self_attention.hpp,
gen-header export by worker 0 after op 35) lives on ref sa-probe-8e9296b in ~/workspace/ai-runs/tron-fence-amx;
the launcher exec/single-attn-20260901/launch-after-peer.sh cherry-picks it onto jhan-amx-fence on
3bda after the peer's marker, then run-single-attn.sh builds runtron.samirror/sacanon in gen/ and runs
3 arms x 3 ctx x 2 reps. Reader: extract-sa.py (tag table inside). Overhead control = new 7605 vs
exec/results/fence3-20260901/medians-7605.json.

RESULTS (2026-09-01 21:20Z, exec/results/single-attn-20260901/summary.json, page 7.2.1): per unit
(QK+softmax+PV+state, worker 0, 510 tokens): ctx 8192 AVX 3.64 / canon 2.89 / mirror 2.66 us (1.37x /
1.26x); ctx 2048 2.80 / 2.14 / 2.07 (1.35x / 1.31x); ctx 256 2.88 / 2.38 / 1.36 (2.12x / 1.21x).
Common work (softmax pieces + state update) 0.11-0.31 us = 4% (AVX) / 7-12% (AMX) of a unit - NOT the
dilution mechanism; QK and PV themselves are memory-limited in the RAM regime (AVX/mirror QK 1.67x, PV
1.31x at 8K vs 3.0x / 1.8x at 256). Canonical-vs-mirror = QK transpose penalty 0.37 us at 8K (1.0 us at
256). Fixed per-op cost (joins + barrier) 9-13 us = 320-480 us/token, > hot loop at ctx 256. Probe
overhead on 7605: 0-5%; phases cover 83-98% of 7605. Estimate (slopes) was 13-16% high in absolute,
ratios within 5%. Probe commit on jhan-amx-fence = 8fd1e7798d (gated TRON_ATTN_PHASE=1). Bins gzipped
for the notebook archive. Open follow-up: A/A logit check of the dotter-path reorder.

**Why:** the per-token attention speedup (1.09-1.27x) mixes fixed per-op costs with the per-unit
speedup; only the per-unit number is context-independent and comparable to the kernel benches.
**How to apply:** the measurement is done; for a future round reuse exec/single-attn-20260901/
(run-single-attn.sh needs EXPECT_COMMIT; extract-sa.py --check per arm; both pre-build greps look for
"namespace attn_phase" and "sites 7606" - the literal marker texts, which cost two failed attempts).
Quote per-unit numbers from summary.json, never the per-token 7605 speedups, when jhan asks for
"single attention". In prose write "prompt 8192", never "ctx 8192" (jhan 2026-09-01, rule in
intel-AMX/CLAUDE.md and [[prompt-not-ctx]]); the "ctx" shorthand in this note is the raw-data label. PEER RULE (2026-09-01):
another session ("tron PR #3879 AMX K mirror comment") shares the fence worktree, gen/ and the page;
never commit/edit the worktree while its markers are pending; message it before touching gen/ or the
page; patch-gen-stamps.py v2 must keep the "site 760x" markers. Related: [[amx-vs-avx-sense]],
[[nfs-attr-cache-build-trap]], [[debug-code-new-branch]].
