# Independent ISA and numerics review

Reviewed PR head `60d66d9c04428d907069ced375b93265add02db7` on 2026-09-04.
This is source/ISA analysis; it does not claim deployment or Delphi measurements.

## Verdict

Bill's core hardware claim is correct. The mirror format is a directly usable
SIMD format as well as an AMX B operand. It does not force reconstruction of a
canonical token-major K row. Deleting canonical K still requires replacing its
readers and lifecycle operations; ISA compatibility alone does not prove that
the overall migration is fast or safe.

## Exact layout and vector interpretation

`h/tron/models/kv_cache.hpp:639-667` specifies and implements:

```
plane[(((s * (page_size/16) + c) * 16 + dp) * 16 + t) * 2 + j]
  = K[c*16+t][s*32+2*dp+j]
```

For page size 64, head size 128, `s=0..3`, `c=0..3`, `dp=0..15`,
`t=0..15`, `j=0..1`. Each fixed `(s,c,dp)` row has 16 adjacent 32-bit
words, each packing two BF16 dimensions of one token. Its 64 bytes are exactly
one AVX-512 input. Treat SIMD lane `t` as token `16*c+t`; broadcast the query's
32-bit BF16 pair to all lanes; perform one `_mm512_dpbf16_ps` per dimension
pair. After 64 such updates, a register contains 16 token scores. This consumes
the existing mirror byte order without gather, transpose or horizontal sum.
Reuse the loaded K row for the other query heads. The AMX reader already uses
these panels at `src/tron/kernels/amx_attn.cpp:239-264`.

Intel defines VDPBF16PS as one independent adjacent-pair dot product per FP32
lane and allows 32-bit memory broadcast. The 512-bit encoding requires
AVX512F + AVX512_BF16; 128/256-bit encodings require AVX512VL + AVX512_BF16.
Calling it simply an AVX instruction obscures the feature requirement.
Primary references:

- [Intel SDM volume 2C, VDPBF16PS, pp. 5-164–5-165](https://cdrdv2-public.intel.com/850976/326018-087-sdm-vol-2c.pdf).
- [Intel's BF16 introduction and intrinsic example](https://www.intel.com/content/www/us/en/developer/articles/technical/intel-deep-learning-boost-new-instruction-bfloat16.html).

## AVX2 + FMA is also viable

Process each 16-token row as two 8-token halves. Let `p` be eight packed
32-bit BF16 pairs, with even dimension in bits 15:0 and odd in bits 31:16.
The following bit manipulations produce exact FP32 encodings of the BF16
values, without a conversion rounding step:

```cpp
__m256 k_even = _mm256_castsi256_ps(_mm256_slli_epi32(p, 16));
__m256 k_odd = _mm256_castsi256_ps(
    _mm256_and_si256(p, _mm256_set1_epi32(0xffff0000)));
acc = _mm256_fmadd_ps(k_odd, q_odd, acc);
acc = _mm256_fmadd_ps(k_even, q_even, acc);
```

`q_even` and `q_odd` are broadcast FP32 scalars. Their source can be BF16,
float, or FP16 Q, provided the executor's actual scalar type is decoded
correctly. In particular, retaining FP32 Q precision is possible; there is no
need to round Q to BF16 just because K is swizzled. AMX's current BF16-only
query packer is an independent restriction, not a restriction of K's layout.
The current source explicitly gates that packer by the executor's scalar type
at `h/tron/kernels/amx_attn_iface.hpp:140-172`.

This fallback needs AVX2 and FMA independently; Tron already compiles the
baseline with `-mavx2;-mfma` at `src/tron/CMakeLists.txt:238`. A pure scalar
implementation can use the same indexing if a broader portability target is
ever needed. A generic float/fp16 backend need not keep row-major K for ISA
reasons, though a staged migration may choose to retain that format per slot.

Compiler primary references:

- [Clang AVX2 intrinsics: shifts, AND, maskload](https://clang.llvm.org/doxygen/avx2intrin_8h.html).
- [Clang FMA intrinsics](https://clang.llvm.org/doxygen/fmaintrin_8h.html).

## Arithmetic equivalence is not bitwise equivalence

1. A layout permutation preserves every BF16 bit; test that exactly.
2. VDPBF16PS performs an odd-element FMA followed by an even-element FMA for
   each lane. It uses RNE, treats input subnormals as zero, flushes output
   subnormals to zero, and does not consult/update MXCSR. These are documented
   in the Intel SDM VDPBF16PS reference linked above. Therefore a matching FMA
   implementation needs the same operation order and FP environment, with
   extra attention to NaN payload/exception behavior; an unrestricted claim of
   bitwise equivalence would be too strong.
3. AMX TDPBF16PS uses separate even and odd FP32 chains over a tile's reduction
   dimension, combines them, then adds into the destination tile. Its order
   differs from repeated VDPBF16PS and from canonical dotter. It also fixes
   RNE and DAZ/FTZ. [Intel SDM volume 2, TDPBF16PS, pp. 4-699–4-700](https://cdrdv2-public.intel.com/789581/325383-sdm-vol-2abcd.pdf).
4. The existing `dotter<bf16,128>` makes four VDPBF16PS operations in two
   partial chains, adds those vectors, then horizontally reduces 16 lanes
   (`h/tron/kernels/dotter.hpp:176-225`). A token-lane kernel necessarily
   changes the reduction tree unless it deliberately recreates those partial
   sums. Finite normal inputs can consequently differ at the FP32 rounding
   level; no precision is lost in K itself.
5. Keep layout migration separate from PV weight conversion. The current AVX
   PV path truncates weights to BF16; AMX rounds them to nearest-even. That
   pre-existing difference is documented at `amx_attn_iface.hpp:46-73` and
   does not disappear with one K format.

## Masks, tails and write visibility

Swizzling pairs dimensions of the *same* token; it does not couple two tokens
as V's pair interleave does. A token's column is independently writable. No
read/modify/write of another token is required. A 32-bit pair store is a
natural unit, but publication still must occur only after all pairs are ready.

Mask nonexistent/unpublished token lanes at load, or establish fully
initialized readable padding. AVX-512 can mask dword loads; AVX2 has
`_mm256_maskload_epi32`, whose most-significant mask bit decides each 32-bit
load and whose disabled result lanes become zero (Clang AVX2 reference).
Then apply the existing causal/window/EAGLE visibility mask to scores before
softmax max/exp, with masked logits set to negative infinity. Zeroed K is not
an attention mask: a zero logit still participates in softmax. Do not rely on
NaN times zero to remove padding. Existing V code explains exactly this trap
at `h/tron/models/kv_cache.hpp:2091-2104`.

Partial pages remain feasible: full 16-token blocks plus one masked block,
or eight-token AVX2 sub-blocks. Very small prefixes may favor a scalar or
gathered-token alternative, but such alternatives are performance choices,
not reasons a second persistent K must exist. Shared-byte cache-line traffic
and false sharing among token writers should be measured separately.

## Performance claims that need measurement

For 64 tokens, D=128, four queries, both the canonical BF16 dotter and the
straightforward swizzled AVX-512 kernel execute 1,024 VDPBF16PS instructions:

- Canonical: 64 tokens × 4 queries × 4 instructions/dot.
- Swizzled: 4 token blocks × 4 queries × 64 dimension pairs.

Swizzled K removes horizontal reductions and permits K-load reuse across
queries. It also creates longer accumulator chains and query broadcasts.
Use several live independent outputs/partial sums and inspect generated
assembly for register spills. AVX2 has more widening/FMA work. Neither the
layout derivation nor an isolated kernel speed proves full attention speed.
Measure score generation, masks/softmax, append cost, small tails, multi-head
reuse and full model latency separately. A cache-hot proof is not a NUMA or
serving benchmark.

## Format-specific acceptance tests

- Exhaustive unique-bit index map; scrambled token writes; overwrite one
  token; all 16-token/32-dimension boundaries; exact round-trip K bytes.
- AVX2, AVX-512 BF16 and AMX versus a double-precision reference using the
  stored BF16 K values; cancellation, random signs/magnitudes and a documented
  absolute-plus-relative tolerance. Preserve original query dtype.
- Separate special-value/FP-environment tests: signed zeros, subnormals,
  extreme finite inputs, infinities and poisoned NaN padding; NaN in active
  data must remain detectable. Do not use relative error alone near zero.
- Every live count 0..64, 7/8/9 and 15/16/17 boundaries, non-prefix visibility
  masks, and empty visible sets. Verify masked lanes never affect maxima or
  denominator and scratch guards remain untouched.
- Integration checks for copy/append, defrag, EAGLE storage remapping, mixed
  reader/writer head ratios, and hardware/DMA views must be covered by the
  lifecycle migration, not inferred from a QK microkernel test.
