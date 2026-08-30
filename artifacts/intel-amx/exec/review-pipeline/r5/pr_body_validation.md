## What this adds

Intel AMX acceleration for tron's CPU (software) attention, entirely behind default-off flags:

- **`TRON_AMX_DISPATCH`** (CMake, default OFF; runtime kill switch `TRON_AMX_DISABLE=1`): a dense-page QK+PV fast path in `apply_page_tok` for head-128 / GQA-4 shapes. 
- **`TRON_AMX_K_MIRROR`** (default OFF): the mirror-orientation QK kernel (S = Q·Kᵀ, no transposing store) reading a VNNI-interleaved K copy kept in a **parallel arena** — ordinary RAM, allocated only for models with the AMX-eligible attention shape (head 128, 4 query heads per KV head) on hosts where AMX is available at runtime, so ineligible models, non-AMX hosts and kill-switched runs pay nothing. save_k writes through; defragmentation rebuilds at the single page-move funnel (`copy_storage_slot`); every consumer null-checks and fails soft to the AVX path. The mirror follows the EAGLE storage view: under `set_storage_view` the draft's logical slot 0 resolves to the extra physical slot's plane, exactly as `kv_block()` resolves canonical K, so the draft and the validator never share a mirror plane (Note [K mirror coherence]).
- Flag-gated page-sharing counters. The stand-alone whole-path kernel benchmark that produced the kernel-level numbers is not in the tree (git history up to d176c88b3); the numbers it produced are stated in Note [Mirror orientation] (1250 vs 686 ns per L2-resident page at width 4). The design and measurement write-up is archived outside the tree at https://github.com/jhan-positron/notebook/tree/main/artifacts/intel-amx.
- Tests: K-mirror byte-equivalence (`t_amx_mirror`, plus checks in `t_llama_unit`'s append test and its EAGLE storage-view cases: the mirror plane moves with the view, interleaved validator/draft writes keep both physical slots' planes coherent, and the page-move rebuild is right in both views), kernel precision regression (`t_amx_numerics`), mirror-arena leak balance (`t_amx_arena_leak`), and a per-step logit A/B dump tool (`t_amx_logit_ab`; registered `DISABLED` so no CI lane runs it — run by hand, recipe in the file).

## Measured (delphi-3bda, Xeon 6 6962P, qwen-3-4b-instruct-2507-tp2, vs a clean binary)

| | 1u/2K | 1u/8K | 8u/2K | 8u/8K |
|---|---|---|---|---|
| decode, canonical | +3.8% | +15.2% | +19.0% | +17.5% |
| decode, mirror-arena | +4.5% | +19.6% | +22.8% | +28.1% |

Prefill up to +105%; package power flat with energy per token −14.5% / −21.6%; logit A/B vs HF fp32 references: max TVD 0.054 over 956 steps, argmax flips only at near-ties; kill-switch and fallback arms measured at clean-binary speed.

### Other measured models

**llama-3.1-8b-tp2** — same-binary kill-switch A/B on the arena-mirror build, 2 reps (`exec/results/t4/t4-shapes.txt`):

| | decode | prefill |
|---|---|---|
| 1u/8K | +14.9% (111.9 → 128.6 tok/s) | +89.6% (542 → 1027 tok/s) |
| 8u/2K | +19.7% (46.6 → 55.7 tok/s aggregate) | +29.2% (158 → 204 tok/s) |

**mixtral-8x7b-instruct-v0.1-tp2, 8 users** — kill-switch baseline vs canonical vs arena-mirror builds, 3 reps (`exec/results/ci-models/mixtral-ab.txt`). MoE: expert FFN dominates at short context, so attention gains concentrate at long context:

| | decode canonical | decode mirror | prefill canonical | prefill mirror |
|---|---|---|---|---|
| 8u/2K | +2.3% | +1.2% | +2.2% | +1.2% |
| 8u/8K | +9.4% (23.1 → 25.3 tok/s) | +18.5% (23.1 → 27.4 tok/s) | +56% (95.4 → 149 tok/s) | +55% (95.4 → 148 tok/s) |

2K decode deltas are within rep spread; the 8K baseline had one high rep (21.4/26.6/21.4), which the mean includes.

**gpt-oss-20b-tp2** (ineligible 64Q/8KV/head-64 shape): both cells within noise — the geometry gate correctly declines, no regression (`exec/results/t4/t4-shapes.txt`).

## Validation and CI coverage

Both options default OFF and every CI lane configures with the defaults, so no CI job compiles the `#ifdef TRON_AMX_*` code or `src/tron/kernels/amx_attn.cpp`, and `t_amx_mirror` / `t_amx_numerics` / `t_amx_arena_leak` each reduce to a single `SUCCEED("... nothing to test")` in CI. This is accepted for now: the feature is default-off and not scheduled for production. The CI configuration is tracked in #3997 (owner: jhan, to be done with the CI team before AMX is enabled in production; a `TODO` next to the two options in `src/tron/CMakeLists.txt` points there).

Until then every push is verified by hand on an AMX host (delphi-3bda, Xeon 6 6962P) in both configurations - mirror (`TRON_AMX_DISPATCH=ON TRON_AMX_K_MIRROR=ON`) and canonical (`TRON_AMX_K_MIRROR=OFF`) - running `t_amx_arena_leak`, `t_amx_mirror`, `t_amx_numerics` and `t_llama_unit`. The log for the current head follows.

_(run log: re-run on the current head queued behind System CI; this paragraph is replaced with the results when it completes)_

## Subsequent PR
Separate changes will add the following features:
- gpt-oss 120B and 20B on AMX
- MoE router matrix calculations use AMX






