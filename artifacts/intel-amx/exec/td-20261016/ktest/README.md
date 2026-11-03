# ktest: bit-level measurements of the tron QK/PV attention kernels (issue #4444)

Short version. The AMX tile multiply TDPBF16PS does not add products in the
order the AVX-512 instruction VDPBF16PS does, so the AMX kernels and the AVX-512
readers of the same data are not bit-identical (hypotheses H-A and H-B are
refuted). The exact arithmetic of every kernel was found and verified bit for
bit on 512,000 QK scores and 102,400 PV outputs. The AVX PV path's truncation
of P to bf16 loses 0.14 % of the weight mass on a 64-token page and biases the
attention output low by about 0.08 %; the AMX path's round-to-nearest has no
measurable bias.

Words used here: QK is the query-key score product, PV the product of the
softmax weights P with V. bf16 is the 16-bit brain float, fp32 the 32-bit
float. RNE is round to nearest even. "fl(x)" is x rounded to fp32 with RNE.
"pe" and "po" are the two exact products of one dimension pair (even dim, odd
dim); a product of two bf16 values is exact in fp32. "ulp" is the spacing of
representable numbers at the value's magnitude. TDPBF16PS is the AMX tile
instruction; VDPBF16PS is the AVX-512 instruction behind `_mm512_dpbf16_ps`.
The "dotter" is `tron::dotter<bf16,128>` (row-major AVX-512 QK); the "VNNI
reader" is `k_vnni::qk_group<4,bf16>` (AVX-512 QK over the VNNI K plane).

## Files

- `ktest.cpp`: the program. Links the real kernel translation unit
  `src/tron/kernels/amx_attn.cpp` and the real headers. The AVX PV loop
  (`detail::scaled_v_expr`, head size 128, kv_cache.hpp) is copied verbatim
  into `avx_scaled_v`, including its truncating `interleave_bf16_ps`.
- `build-run.sh`: the ssh/nix/compile/run recipe (run from claude-box; builds
  and runs on delphi-3bda, cpus 72-143, nice 10).
- `results.txt`: the program's full output from delphi-3bda, 2026-10-16.
- `build.log`: the compile flags and compiler output of that build.

Inputs: K, V, Q are bf16 values of N(0,1) samples (RNE), seed 20261016; 2000
random (query group, page) instances for QK (512,000 scores) and 2000 for PV
(1,024,000 outputs). P is softmax-like: exp(s - max) with s ~ N(0, 3).

## What each section measures and what was found

- T0: one lane of `_mm512_dpbf16_ps` (2,000,000 random triples, with and
  without MXCSR FTZ/DAZ). Result: acc' = (acc + po) + pe, two fp32 RNE adds,
  odd product first. 100 % match; the other three candidates match 92 %.
  MXCSR has no effect (no subnormal inputs occur).
- T1 (H-A): `qk_vnni_128x4` (AMX) vs the VNNI reader on the same plane and q.
  Refuted: 49.5 % of the 512,000 scores differ, up to 2 bf16 ulps.
- T1b: `qk_rowmajor_128x4` vs `qk_vnni_128x4`: bit-identical (512,000/512,000).
- T2: dotter vs AMX QK: 50.1 % differ, max 0.75 bf16 ulps, max relative
  difference 3.3e-3 (on scores near zero).
- T3: dotter vs scalar reference in its own order: bit-identical with lane
  semantics (acc + po) + pe and the halving reduction tree of
  `_mm512_reduce_add_ps` (lanes j+8, then j+4, then j+2, then 0+1).
- T4: VNNI reader vs scalar sequential reference over the 64 dimension pairs:
  bit-identical with (acc + po) + pe.
- T5, T5x, T5y, T5z, T5m: TDPBF16PS. No sequential, pair-fused, tree, exact
  single-rounding or alignment-width model matches (best 81 %). Controlled
  experiments (T5z) show: two products are always summed exactly; pairs with
  one product each accumulate as plain sequential fp32 adds; only pairs with
  both products present break the sequential model. The model that matches
  bit for bit, per instruction (16 dimension pairs = 32 products):
  E = ((0 + pe_0) + pe_1) + ... + pe_15 (sequential fp32 adds of the even-dim
  products), O = the same over the odd-dim products, result = acc + fl(E + O).
  Verified on the 4-instruction QK kernel (T5m, 512,000/512,000) and on the
  2-instruction PV kernel (T6d, 102,400/102,400).
- T6a (H-B): AMX PV vs the AVX loop with P exactly representable in bf16
  (so both see the same P bits). Refuted: 72.8 % of outputs differ (the add
  order above). T6c: the AVX loop fed RNE-rounded P vs AMX: also 72.8 %
  differ. T6b: with fp32 P (truncation vs RNE) 99.99 % differ, mean |diff|
  1.8e-3.
- T7: accuracy vs an fp64 reference (unrounded P): see the table. T8: the same
  for 16-token and 1-token pages; the 1-token case (P = 1 exactly) is exact on
  both paths.

| page | path | mean signed rel. error | RMS rel. error | weight mass sum(bf16(P))/sum(P) - 1 |
|---|---|---|---|---|
| 64 tokens, V ~ N(0,1) | AVX trunc | -7.3e-4 | 2.92e-3 | -1.44e-3 |
| 64 tokens, V ~ N(0,1) | AMX RNE | -5.8e-6 | 1.62e-3 | -4.1e-6 |
| 64 tokens, V ~ 0.1 N(0,1) | AVX trunc | -7.6e-4 | 2.93e-3 | -1.45e-3 |
| 64 tokens, V ~ 0.1 N(0,1) | AMX RNE | -1.2e-6 | 1.63e-3 | -3.3e-8 |
| 16 tokens | AVX trunc | -5.5e-4 | 2.91e-3 | -1.08e-3 |
| 16 tokens | AMX RNE | +1.6e-6 | 1.55e-3 | -4.9e-6 |
| 1 token | both | 0 | 0 | 0 |

The RMS error of the truncating path is 1.8 times that of the RNE path. The
mean signed relative error excludes outputs below 10 % of their absolute-mass
(cancellation); the "mass_weighted_bias" lines in results.txt include every
output and give the same picture (-8.3e-4 vs -4e-6). The output bias (-0.08 %)
is smaller than the weight-mass bias (-0.14 %) because the largest weight of a
page is exp(0) = 1 exactly, which truncation does not change, and that token
dominates the output; this explanation is a hypothesis, the two numbers are
measurements. Both paths divide by the same fp32 sum of the unrounded P, so the
normalized output o/sum(P) carries the same relative errors.

## T9: AVX-512 kernels in the AMX add order (proof of concept)

- T9a: `qk_group_amxorder<4>` (same signature and lane layout as the VNNI
  reader; per 32-dim step E = FMA chain over the 16 even-dim products from 0,
  O = the same over the odd-dim products, acc = acc + fl(E + O), products
  formed exactly from the widened bf16 pairs) vs `qk_vnni_128x4`: bit-identical,
  512,000/512,000 scores, the same instances as T1-T5.
- T9b: `scaled_v_amxorder` (P rounded RNE to bf16 and widened, two groups of
  16 token pairs, same chain rule over even and odd tokens) vs
  `weights_times_v_128x4`: bit-identical, 1,024,000/1,024,000 outputs (2000
  instances, seed 20261016+9).
- T9c cost per (query group of 4 heads, 64-token page), one thread pinned to
  cpu 72, data in cache, 20,000 calls after 2,000 warm-up, two runs within 2 %:

| kernel | ns per call | ratio |
|---|---|---|
| QK current VNNI reader `k_vnni::qk_group<4,bf16>` | 824-829 | 1.00 |
| QK `qk_group_amxorder<4>` (AMX order) | 1071-1074 | 1.30x the reader |
| QK `qk_vnni_128x4` (AMX kernel, with `pack_q_rows_128x4`) | 166 (kernel only 142) | 0.20x the reader |
| PV current AVX loop, 4 heads | 896-901 | 1.00 |
| PV `scaled_v_amxorder`, 4 heads (AMX order) | 942-952 | 1.06x the AVX loop |
| PV `weights_times_v_128x4` (AMX kernel, 4 heads) | 177-178 | 0.20x the AVX loop |

The AMX-order QK costs 30 % more than the reader because every dimension pair
needs two FMAs (even and odd chains) instead of one VDPBF16PS. The AMX-order
PV costs 6 % more than the AVX loop for the same reason, partly hidden by the
loop's dependency chains. Caveat: delphi-3bda carried other jhan jobs during
both runs (load average 30-180); the ratios were stable, the absolute numbers
may be inflated. A first timing run without the memory clobber reported 65 ns
for the AVX loop: the compiler had removed the output chains nobody read; the
harness now forces every output to escape.

## Caveats

- Compile flags: the project's own flags for amx_attn.cpp were taken from
  `gen/compile_commands.json` of /var/tmp/jhan/tron-pr4 (commit ea94e95a4e):
  clang++-19, -O3 (the kernel TU overrides -O2), -DTRON_K_VNNI,
  -DTRON_AMX_DISPATCH, -DTRON_IGNORE_NAN -DTRON_IGNORE_FTZ, the AMX and
  AVX-512 target flags, and the spdlog/yaml/json include paths. ktest.cpp uses
  the same flags plus -ffp-contract=off so its scalar fp32 references are plain
  RNE adds. The link needs `gen/_deps/spdlog-build/libspdlog.a` (common/assert.hpp
  calls spdlog) and a stub `tron::get_abort_context()` defined in ktest.cpp.
- The AVX loop is a copy, not the template instance; it is the same intrinsic
  sequence (verified by reading kv_cache.hpp lines 2930-2960).
- The dotter's reduction tree is what clang 19 emits for
  `_mm512_reduce_add_ps` at these flags; the project builds with the same
  compiler and flags.
- No subnormal inputs or outputs occur with N(0,1) data; MXCSR DAZ/FTZ (which
  tron never sets) was tested only for VDPBF16PS.
- The T5x alignment-model search (2100 candidates) and the T5y/T5z candidate
  lists are kept in the program as a record of what was ruled out; they take
  about 55 s of the 78 s run.
- Residual match rates below 100 % in results.txt are for rejected
  hypotheses; every "<== bit-identical" line is a 100 % match.
