# AMX decision record

Markdown digest of `tron-amx-distilled.html` (the full page carries the chart and layout).
One entry per design decision: what was chosen, what was rejected and why, the measurement
that settles it, and the `Note [...]` names that anchor it in source. Companion to
`rampup/pr-rampup.html` (newcomer intro) and `rampup/pr-walkthrough.html` (file-by-file map)
for reviewing draft PR positron-ai/tron#3879.

Lineage note: "mirror" names the formulation from Bill's PR #2934 (a second, VNNI-layout
copy of K); the implementation and all measurements here are ours.

## How this document stays in sync with the code

Every decision entry lists its anchoring `Note [...]` names - GHC-convention named comments
in the tron sources (codified in tron's AGENTS.md, validated by `make lint-notes`). The
bracketed name is an exact-match, greppable key: from this document, grep the name to find
the mechanism and its invariants in code; from a `See Note [...]` reference in code, grep
here to find the decision, the rejected alternatives, and the evidence. The doc owns *why
this design and not the others*; the Notes own *how it works and what must stay true*.

## Entry index

| # | Decision | Status |
|---|----------|--------|
| D1 | K-mirror formulation: canonical-K default, arena-mirror opt-in | written |
| D2 | Dispatch gate: geometry (head 128, GQA 4) and dense-page-only predicate | planned |
| D3 | PV numerics: keep round-to-nearest-even, do not imitate AVX truncation | planned |
| D4 | PV blocking 4+4 over 6+2; epilogue pipelining rejected | planned |
| D5 | Replace-K rejected: canonical K is a shared interface (Bill's question) | planned |

## D1 - K-mirror formulation: canonical-K default, arena-mirror opt-in

**Decision (2026-08-19, Sol consensus + jhan sign-off).** Ship both QK formulations.
Canonical-K (`S^T = K . Q^T`, K consumed exactly as stored) is the supported default. The
mirror formulation (`S = Q . K^T` from a derived VNNI-layout copy of K held in a parallel
arena) is opt-in via `TRON_AMX_K_MIRROR` for pinned AMX deployments. Declared end state,
adopted as the plan but *not yet in force*: arena-mirror becomes the default on AMX hosts
with sufficient KV headroom once the five gates pass; canonical-K remains the compatibility
fallback.

**Why the choice exists.** The mirror kernel is faster - the canonical kernel must
round-trip its score tile through memory and transpose it, a ~560 ns width-4 L2 whole-path
gap (1250 vs 686 ns, `results/slot1/fused-sweep-v2.txt`; a pipelined-epilogue variant narrowed
it to ~300 ns, 982 vs 686, in an unsaved 8-page-ring run recorded only in `exec/QUEUE.md`) whose
components (transpose work + score traffic) were not isolated. (Corrected 2026-08-21: an earlier version blamed a
tile-store-to-vector-load forwarding stall; opt-manual 20.15 supports that forwarding at
64-byte granularity, and a direct microbenchmark on the 6962P measured no such stall - doc
01 section 6.4.) But the mirror needs a second copy of K, and where that copy lives and what
it costs determined the whole formulation question.

### Rejected alternatives

- **R1 - In-block mirror (third `kv_block` plane; the placement in Bill's PR #2934).**
  Rejected for the current shared `kv_block` layout: it caused the measured locality and
  DMA-page-capacity regressions. The dead 16 KB plane between every K and V plane broke
  prefetch streams: LLC-load miss 50.8% -> 84.6%, the AVX fallback lost 3.8-7.8% decode
  *with zero mirror writes*, and the canonical AMX path itself lost ~9%. A layout-only
  control build (3-plane layout, no mirror code) reproduced the fallback penalty exactly,
  isolating layout as the entire cause. It also cost 33% KV page capacity (48 vs 32 KB per
  block-page). (`results/slot1/p2-inc2b-decomp.txt`, `results/slot1/p2-perf-decode.txt`)
- **R2 - Mirror as default now.** Rejected by consensus (Sol: KEEP-CURRENT, 2026-08-19;
  jhan reaffirmed after the arena removed the measured fallback and DMA-page-capacity
  penalties): the mirror is young code, and gates T1-T3 plus capacity-boundary behavior
  were open at decision time. The end-state revision (arena-mirror default behind five
  gates) replaced an immediate flip.
- **R3 - Replace canonical K with transposed K (one copy; Bill's question).** Rejected:
  canonical K is a shared interface, not the CPU kernel's private format - the FPGA DMAs
  the K page bytes exactly as stored, the AVX dotter consumes contiguous 128-value K rows,
  and the kill-switch rollback requires the unchanged layout to exist. Full treatment:
  planned entry D5 and `rampup/pr-rampup.html` section 4.3.
- **R4 - Canonical only (no mirror at all).** Rejected: forfeits a measured, replicated
  gain (+4.4 percentage points of decode over canonical at 1u/8K, +10.1 at 8u/8K - growing
  with attention share) and the larger energy cut (-21.6% vs -14.5% J/token). The ~560 ns
  orientation gap (1250 vs 686 ns in the saved sweep) is the score-tile memory round trip plus
  transpose work (components not isolated; see the correction note above); the pipelined-epilogue
  attempt improved canonical by only ~2% (1006 to 982 ns) in an unsaved 8-page-ring run that
  is recorded only in `exec/QUEUE.md`, not in the sweep files.

### Settling measurements

Decode gain vs the true clean binary (qwen-3-4b-tp2, 8 reps, 95% CI,
`results/t4/t4-reps.txt`):

| Config | Canonical | Arena-mirror |
|--------|-----------|--------------|
| 1u / 8K | +15.3 +/- 0.4 % | +19.7 +/- 0.3 % |
| 8u / 8K | +17.7 +/- 0.2 % | +27.8 +/- 0.8 % |

The mirror-over-canonical gap grows from 4.4 pp at 1u/8K to 10.1 pp at 8u/8K (about 2.3x).
All four gain-versus-clean confidence intervals exclude zero.

| Claim | Measurement | Record |
|-------|-------------|--------|
| Mirror kernel faster at width 4 at every residency; measured AVX crossover Nq=2 | width 4 whole-path 686/1470/1800 ns at L2/L3/DRAM = 2.36x/1.68x/1.77x vs fused AVX; canonical (4+4) 1250 ns vs mirror 686 ns at L2; the pipelined canonical's 982 ns is from an unsaved 8-page-ring run | `results/slot1/fused-sweep-v2.txt` (686/1470/1800, 1250); 982: `exec/QUEUE.md` prose only |
| In-block placement penalty is the layout, not mirror code | layout-only build: -3.7/-7.6/-4.0% (= mirror build's -3.8/-7.8/-3.9%); LLC miss 50.8 -> 84.6%; dTLB ~0 both arms | `results/slot1/p2-inc2b-decomp.txt`, `results/slot1/p2-perf-decode.txt` |
| Arena removes the fallback penalty; kill switch = true rollback | kill-switch arm within -1.3..+3.3% of clean binary | `results/t4/p2-inc3-arena.txt` |
| Arena costs no KV page capacity (ordinary RAM, not DMA budget) | 32u and 48u at ctx 8192 admitted by both builds, failed=0; mirror +6.0% aggregate at the edge | `results/t4/cap-sweep.txt` |
| Arena resource cost (what the arena does NOT remove) | ordinary 64B-aligned RAM, kv_bytes/2 (32 GB this config; 1.58 TB host), allocated only when AMX is available, fail-soft on failure; scatter write-through 70.3 ns/token-row (single-core, L2-resident); system prefill stayed +1-2% net vs the no-write build | `exec/bench_scatter.cpp`, `results/slot1/p2-inc2.txt` |
| Energy per token | package power flat (+0.3% mirror, +1.6% canonical vs clean 543 W, two-socket total); J/token -21.6% mirror, -14.5% canonical at 8u/8K | `results/t4/t4-power.txt` |
| Numerics: mirror adds nothing on top of canonical AMX | greedy output byte-identical to canonical-AMX (same head-dim sum order) | `results/slot1/p2-inc2.txt` |

### End-state gates (arena-mirror default on AMX hosts)

| Gate | Scope | Status (2026-08-20) |
|------|-------|---------------------|
| 1 | T1 logit tolerance, predeclared criteria, more lengths/shapes | 3 prompts / 956 steps done: AMX-vs-AVX max TVD 0.054, 1/956 outliers (criterion: <=0.05, cap 0.3 at <=10%, top-5 overlap >=3). Batching variations + criteria text remain. |
| 2 | T2/T3 true fallback paths (non-AMX host, runtime-disabled, arena alloc failure, lifecycle, defrag) | Code-level AMD gating verified (CPUID feature bits, not vendor). Empirical non-AMX boot pending a named machine; the other listed fallback/lifecycle checks are not reported complete here. |
| 3 | Behavior at/beyond the KV page budget + mixed-context coverage + arena NUMA placement | 64u/ctx8192 completed cleanly on both builds (admission failure never reached). Mixed-context and NUMA checks remain. |
| 4 | A7 byte-equivalence tests in CI | Removed from this project's tracking (remote task); completion evidence is still required before the default flip. |
| 5 | T4 replication with confidence intervals + other model shapes | DONE: 8 reps/cell, CV 0.1-0.7%; llama-3.1-8b generalizes (+15.0% at 1u/8K, +19.7% at 8u/2K), gpt-oss ineligible shape shows no regression (-0.3..-1.6%). |

### Anchors in source

- `Note [Mirror orientation]` (h/tron/kernels/amx_attn_iface.hpp) - the two formulations
  and the score round-trip cost.
- `Note [K mirror parallel arena]` (h/tron/models/kv_cache.hpp) - the placement decision
  and the arena's properties.
- `Note [K mirror coherence]` (h/tron/models/kv_cache.hpp) - the two-copy invariant and its
  two production write sites.
- `Note [AMX attention dispatch]` (h/tron/kernels/amx_attn_iface.hpp) - eligibility,
  runtime availability, kill switch, and fallback behavior that the opt-in/default policy
  rides on.
- `Note [Tile stores write 16 rows]` (h/tron/kernels/amx_attn_iface.hpp) - the kernel
  output-buffer invariant behind both orientations.

### Reopen conditions

- Flip the default when the five gates pass, on AMX hosts with sufficient KV headroom
  (that is the recorded plan, not a new decision).
- Revisit R3 (replace-K) only if a card consumes transposed K natively or an FPGA-free
  build ships.
- Revisit R1 (in-block) only if the shared `kv_block` layout constraints materially change,
  or a future placement avoids the dead plane without consuming KV-page capacity.

---

Consensus: D1 reviewed by Sol 2026-08-20 (ENDORSE-WITH-EDITS, 10 defects, all applied).
Measurements 2026-08-18..19 on delphi-3bda (Xeon 6 6962P), qwen-3-4b-instruct-2507-tp2
unless labeled; records under `~/workspace/intel-AMX/exec/results/`.
