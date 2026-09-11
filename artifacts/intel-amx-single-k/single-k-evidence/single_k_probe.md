# Local AVX feasibility experiment

Source: `single_k_probe.cpp`. This is a standalone proof for the existing
PR3879 mirror layout, pinned to commit
`60d66d9c04428d907069ced375b93265add02db7`. It does not modify or link Tron.
No remote command or Delphi execution was used.

The 64-token, 128-dimension mirror index is transcribed from
`h/tron/models/kv_cache.hpp:652`:

```
(((dim / 32 * 4 + token / 16) * 16 + dim % 32 / 2) * 16
 + token % 16) * 2 + dim % 2
```

A 64-byte SIMD load reads one dimension pair from 16 consecutive tokens.
The BF16 kernel broadcasts the query pair, then applies `VDPBF16PS`.
The FP32-query kernel shifts/masks each packed pair into FP32 even/odd lanes
and applies two FMAs, preserving FP32 query precision. The AVX2 variant
does the same for eight tokens with `VPMASKMOVD` loads. None reconstructs
canonical rows or uses gather instructions.

The BF16 and FP32 canonical comparison functions reproduce the arithmetic
in `h/tron/kernels/dotter.hpp` and `_mm512_reduce_add_ps` from
`h/tron/simd/fp32.hpp`. They are intrinsic-level transcriptions, not linked
Tron dotters. Installed GCC 11 cannot compile Tron's scalar `__bf16` type.
Canonical storage is present only as the test oracle/baseline.

## Reproduce

Run in `PR3879-codex/single-k-evidence` on an AVX512_BF16-capable x86 host:

```sh
g++ -std=c++20 -O3 -mavx2 -mfma -Wall -Wextra -Wpedantic \
  -o single_k_probe single_k_probe.cpp > single_k_probe.build.log 2>&1
taskset -c 0 ./single_k_probe > single_k_probe.run.log 2>&1
objdump -d -C -Mintel single_k_probe > single_k_probe.disassembly.txt
g++ -std=c++20 -O1 -g -mavx2 -mfma -fsanitize=address,undefined \
  -fno-omit-frame-pointer -o single_k_probe_sanitized single_k_probe.cpp \
  > single_k_probe.sanitizer-build.log 2>&1
ASAN_OPTIONS=detect_leaks=0 taskset -c 0 \
  ./single_k_probe_sanitized --correctness-only \
  > single_k_probe.sanitizer-run-no-leak.log 2>&1
```

The baseline translation unit targets AVX2+FMA. AVX512 and AVX512_BF16
functions have explicit target attributes. `main` requires AVX512_BF16
because it executes all three kernel variants.

## Results

The recorded run used GCC 11.4.0 and an AMD Ryzen 9 9950X reported inside
a KVM guest, pinned to logical CPU 0. CPU/compiler output is retained.

- 3,096 page-mask cases: 24 random trials, each covering all 65 page prefixes
  and 64 arbitrary masks. Zero masks and holes are included.
- Each of the three variants checked 98,905 live scores against scalar FP64
  accumulation. Inputs are normal samples scaled by powers of two from 2^-3 through 2^3.
- Unwritten token locations contain BF16 NaN poison. Only live tokens are
  scattered, in shuffled order. All inactive outputs equal negative infinity.
- The same AVX512 masked load intrinsic passes all 17 prefix masks with
  masked-off lanes crossing into a `PROT_NONE` guard page, including the
  zero-mask case. This specifically checks architectural masked-load access;
  NaN poisoning alone is not evidence that an inactive address was not read.
- ASan and UBSan correctness execution passed. LeakSanitizer's initial run
  failed because it could not inspect `/proc/.../task` in this sandbox;
  the separate address/undefined sanitizer run disables leak detection.

| Kernel | Max absolute error vs FP64 | Max error / max(1, sum of absolute products) | Max absolute difference vs dotter transcription | Bitwise differences vs dotter |
|---|---:|---:|---:|---:|
| AVX512 BF16 Q | 7.37607479e-5 | 1.05893468e-7 | 9.53674316e-5 | 67,462 / 98,905 |
| AVX512 FP32 Q | 1.18228653e-4 | 1.51533602e-7 | 1.22070312e-4 | 74,848 / 98,905 |
| AVX2 FP32 Q | 1.18228653e-4 | 1.51533602e-7 | 1.22070312e-4 | 74,848 / 98,905 |

These statistics come from the optimized build. The sanitizer build also
passes; compiler optimization can change the random FP32 inputs at the last
bit, so its FP32 statistics need not be identical. The acceptance criterion
is `abs(reference - result) <= 1e-6 + 8e-6 * sum_abs_products`.
The observed errors are substantially below that bound, but this is only
QK validation. It does not establish attention, softmax, model-logit,
determinism, or task-quality equivalence.

The new summation order is deliberately different from the row dotter's.
Exact bitwise compatibility is therefore not a valid claim. A subnormal
probe with MXCSR `0x1f80` returns zero from BF16 dot instructions and
`9.18354962e-41` from the FP32 FMA path, agreeing with scalar FP32 for the
latter. This is a datatype/ISA semantic distinction, not a layout failure.
NaNs and infinities in active inputs were not part of the correctness corpus.

## Timing limits

For a resident full 64-token page, one query, median of seven runs of
6,000 calls each:

| Kernel | ns/page |
|---|---:|
| Canonical BF16 dotter transcription | 77.14 |
| Swizzled AVX512 BF16 | 80.08 |
| Canonical FP32-query dotter transcription | 157.65 |
| Swizzled AVX512 FP32-query | 106.64 |
| Swizzled AVX2 FP32-query | 195.85 |

These are local feasibility measurements, not Intel, full-attention, or
end-to-end performance predictions. The raw CSV also contains partial-page
numbers. Its canonical helper scans all 64 mask bits, unlike Tron's normal
contiguous visible-token iteration. Those partial-page numbers must not be
used to claim sparse/decode performance. No query-group reuse, cold-page
streaming, AMX execution, write-through cost, FPGA conversion, scheduling,
softcap, softmax, or P×V work is measured here.

The production integration must combine visibility, readiness, causal,
sliding-window, and token-lifetime rules to form load masks. It must
reapply the negative-infinity score sentinel after score transforms such
as softcap; this probe does not perform such transforms.
