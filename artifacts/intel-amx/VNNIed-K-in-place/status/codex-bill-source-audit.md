# Bill's packed-key prototype: source audit

Short version: Bill's prototype uses the same 16-token packed-key panels as the independent design. It keeps both the original keys and the packed keys. Its shared AMX/AVX reader is useful prior work, but cache-copy, source-type, and padded-row obligations prevent adopting the surrounding integration unchanged.

Words used here:

- tron is the inference program under test.
- K, Q, and V are attention keys, queries, and values.
- AMX and AVX are CPU instruction sets. VNNI layout pairs neighboring reduction values for a matrix instruction's right operand.
- bf16 and fp16 are different 16-bit floating-point formats. fp32 is 32-bit floating point.
- A KV page stores 64 tokens. A head is one attention feature group. `kv_mul` is query heads per stored KV head.
- `M` is the number of query-head rows passed to a kernel. Bill combines several visible query tokens into those rows.
- A mirror is a second retained copy of K in another layout. The scalar/dotter path is the original per-key vector dot-product loop.
- PV is probability-times-value multiplication. CI is continuous integration.

## Source and evidence limits

The local Git reference `origin/bill-amx` in `/home/jhan/workspace/tron` resolves to commit `a28ef6c69a1dcfceb5679dd4fe3f24506e8d7fe1`. The parent audit verified the same current head through the GitHub connector for [PR #2934](https://github.com/positron-ai/tron/pull/2934). Its recorded commit time is 17 June 2026 at 17:06:05 UTC−07:00. Its title is “Merge branch 'main' into bill-amx.”

Source excerpts were extracted into `status/codex-bill-evidence/`. All file references below use that commit. No production code was changed. No C++ test, model run, or hardware benchmark was executed. A Python calculation checked the example floating-point bit reinterpretations below.

No `amx-old*` directory was found immediately under `/home/jhan`, `/home/jhan/workspace`, or `/home/jhan/workspace/intel-AMX`. No `dispatcher-m-sweep.md` was found in the inspected known repositories or the pinned Git tree. The older `single-k-evidence/source` directory contains PR3879 material rather than Bill's dispatcher sources.

Bill's reported 13% scalar-path slowdown comes from the investigation relayed by the parent audit. **Insufficient data:** raw runs, machine configuration, exact compared revisions, and `dispatcher-m-sweep.md` are needed to validate that result or attribute its cause. The source findings below do not establish an end-to-end performance result.

## What the code establishes

```text
save_k -> original K row -> packed K mirror -> completion
              |                 |
         scalar reader      AVX / AMX readers
```

- The writer saves the ordinary K row first. It then scatters a packed mirror before publishing completion. This is packing during `save_k`, rather than repacking on each attention call. [h/tron/models/model.hpp:1863, h/tron/models/model.hpp:1873, h/tron/models/model.hpp:1880]
- Its element offset is `(token/16)*head_dim*16 + (dim/2)*32 + (token%16)*2 + dim%2`. This is algebraically identical to the independent design's `[panel][dimension-pair][token-lane][pair-inner]` layout. [h/tron/kernels/amx_kv_layout.hpp:53]
- Both the AMX and blocked AVX kernels consume the same packed mirror. The blocked kernel broadcasts one Q dimension pair and accumulates scores for 16 keys in vector lanes. This provides a concrete starting point for the separately deferred native packed-layout AVX reader. [h/tron/kernels/amx_attention.hpp:58, h/tron/kernels/avx512_blocked_attention.hpp:51]
- The dispatcher selects the original dotter for fewer than 4 rows, blocked AVX for 4 through 7 rows, and AMX from 8 rows when available. These are coded thresholds. The comments' claim that they are measured optimal points is not validated by the available raw evidence. The proposed 4-row AMX configuration also differs from Bill's 16-row configuration. [h/tron/kernels/attention_dispatch.hpp:174, h/tron/kernels/attention_dispatch.hpp:187, h/tron/simd/amx.hpp:85]
- The original K and V arrays remain. An additional full K array is allocated when the head dimension is 64 or 128 and `SW_ATTN_DISPATCH` is compiled. The storage decision does not check `kv_mul`, although the writer and reader require `kv_mul >= 4`. [h/tron/models/kv_cache.hpp:941, h/tron/models/kv_cache.hpp:959, h/tron/kernels/attention_dispatch.hpp:73]

Static storage accounting for one 64-token, 128-dimension KV-head block:

```text
K/V payload; each block represents 8,192 bytes
Original       ████     32,768 bytes
Bill mirror    ██████   49,152 bytes  (+16,384 bytes)
Single layout  ████     32,768 bytes
```

| Representation | Original K | Packed K | V | Total payload |
| --- | ---: | ---: | ---: | ---: |
| Original cache | 16,384 bytes | 0 bytes | 16,384 bytes | 32,768 bytes |
| Bill's eligible mirror block | 16,384 bytes | 16,384 bytes | 16,384 bytes | 49,152 bytes |
| Independent single-layout proposal | 0 bytes | 16,384 bytes | 16,384 bytes | 32,768 bytes |

Bill's extra plane adds 50% to this block's K/V payload. That is not a claim about whole-process memory use or memory-bus traffic. [h/tron/models/kv_cache.hpp:938]

## Concrete integration findings

1. **Cache copying omits the packed mirror.** `page::copy_from` copies ordinary K and V but never copies or reconstructs `k_vnni`. A destination read through the dispatcher therefore does not receive the source's packed keys after this copy. This is a static data-flow defect in the pinned snapshot. No model-level failure was reproduced. The single-layout design must replace the copy operation itself, including different source and destination offsets. [h/tron/models/kv_cache.hpp:709, h/tron/models/kv_cache.hpp:720, h/tron/models/kv_cache.hpp:954]

2. **The writer and query readers assume bf16 without a type gate.** The original K setter converts its input. The mirror writer instead reinterprets `kout.data` as bf16. Eligibility checks only dimensions and `kv_mul`. Per-page and batched query readers use the same reinterpretation. A float or fp16 activation source can therefore satisfy the shape gate while supplying the wrong bit representation. [h/tron/models/model.hpp:1864, h/tron/models/model.hpp:1870, h/tron/models/model.hpp:1874, h/tron/kernels/attention_dispatch.hpp:73, h/tron/models/self_attention.hpp:1208, h/tron/models/self_attention.hpp:1361]

   The Python bit check used ordinary little-endian representations. Two fp32 values `[1.0, 1.0]` begin with bf16-sized halves that reinterpret as `[0.0, 1.0]`. An fp16 value `1.0` reinterprets as bf16 value `0.0078125`. These demonstrate representation mismatch only. They are not model-output measurements. The independent design's converted setter and original-type AVX fallback avoid this assumption.

3. **The direct query path does not enforce the blocked kernel's row padding.** The blocked kernel processes and stores four rows on every iteration, including its final iteration. For `M=5`, it reads rows 0 through 7. The per-page caller supplies a pointer directly into the query group and passes `M=kv_mul`. The eligibility gate allows `kv_mul=5`, `6`, and `7`. It does not provide a padded copy at this call. Reads can therefore extend past the logical group and, for the final group, past the query token's extent. [h/tron/kernels/avx512_blocked_attention.hpp:44, h/tron/kernels/avx512_blocked_attention.hpp:52, h/tron/models/self_attention.hpp:1208]

4. **The batching gate has no upper limit.** `vnni_eligible` permits any `kv_mul >= 4`. The batch capacity is integer division `16 / kv_mul`. Above 16 query heads per KV head, that capacity is zero. The resulting zero-length array is not standard C++. If the compiler accepts it as an extension, the scan loop cannot advance through any item. The design lesson is to state exact supported shapes and prove progress for rejected shapes. The current independent proposal admits only its fixed 4-head AMX shape. [h/tron/kernels/attention_dispatch.hpp:73, h/tron/models/self_attention.hpp:1020, h/tron/models/self_attention.hpp:1024, h/tron/models/self_attention.hpp:1087]

5. **Initialization once per thread is weaker than ownership of a compute region.** The dispatcher remembers that a thread loaded its tile configuration once. A later tile release or another AMX user can change tile state without resetting that Boolean. This is a conditional integration hazard, not proof that the pinned production schedule triggers it. The independent design should retain explicit begin/end region ownership. [h/tron/kernels/sw_attention.hpp:47, h/tron/kernels/sw_attention.hpp:53]

6. **A reused kernel changes numerical behavior beyond storage.** The blocked QK kernel sums sequential dimension pairs into token lanes. The ordinary dotter uses a different reduction arrangement. Bill also rounds softmax weights to nearest-even before batched PV. His nonbatched value path truncates the high half of fp32 values when forming bf16 pairs. Adopting the blocked reader or batched attention therefore requires a separate numerical comparison. It is not an exact storage-only change. [h/tron/kernels/avx512_blocked_attention.hpp:57, h/tron/kernels/attention_dispatch.hpp:150, h/tron/models/kv_cache.hpp:879]

## What the tests cover and miss

- The tests include direct dispatcher checks, not only standalone kernels. `t_sw_attention` calls the production QK and PV dispatch interfaces for both supported head dimensions. It compares against scalar references and checks contiguous visibility ranges. [t/t_sw_attention.cpp:63, t/t_sw_attention.cpp:81, t/t_sw_attention.cpp:126]
- Every dispatcher test allocates 16 padded query and output rows. This cannot expose a caller that passes an unpadded logical group. The actual QK cases use 1, 4, 8, and 16 rows. The file's opening claim of cases for 0, 2, 3, and 7 rows is broader than its implemented cases. [t/t_sw_attention.cpp:3, t/t_sw_attention.cpp:61, t/t_sw_attention.cpp:126]
- Dispatcher tests construct packed K directly with the bulk packer. They do not pass through `save_k`, page append, or the common cache-copy path. Their success would not resolve the first two integration findings. [t/t_sw_attention.cpp:69, t/t_sw_attention.cpp:79]
- `t_amx_attention`'s AMX correctness cases invoke local three-tile kernels. They do not invoke the production four-accumulator kernels. The separate dispatcher suite does reach the production interface, but can fall back to AVX when AMX is unavailable. Record the actual executed path before claiming AMX validation. [t/t_amx_attention.cpp:78, t/t_amx_attention.cpp:116, t/t_amx_attention.cpp:289, t/t_amx_attention.cpp:379, h/tron/kernels/sw_attention.hpp:86]
- The dispatcher references allow relative errors of 0.5% for QK and 2% for PV. These numerical limits are explicit. They do not establish full-attention or generation equivalence. [t/t_sw_attention.cpp:94, t/t_sw_attention.cpp:121]
- Both test binaries are registered as fake-hardware tests in CMake. **Insufficient data:** no test execution logs or CI collection evidence were inspected. Registration is not evidence that real AMX instructions ran. [t/CMakeLists.txt:119]

## Effect on the independent design

Keep the single retained K representation, converted writer, explicit cache-copy adapter, and typed AVX fallback. Keep explicit tile-region ownership and exact logical buffer extents. Bill's packed AVX loop is useful evidence that one packed representation can serve matrix and vector instructions, but importing it remains a separate arithmetic and performance change.

The reported scalar slowdown does not predict the single-layout proposal's result. Bill's version changes cache footprint and dispatch bookkeeping while retaining ordinary scalar K reads. The independent proposal retains one K plane but reconstructs rows for AVX. Measure those costs separately before comparing end-to-end results.

This second-pass source audit was performed after the independent design freeze. Claude's design and implementation were not read.
