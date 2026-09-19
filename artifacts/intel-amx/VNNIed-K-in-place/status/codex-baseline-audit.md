# Baseline audit: writing the K cache in its AMX input layout

Short version: The current cache stores each key as one contiguous row. Replacing that row with dimension pairs spread across tokens affects the writer, both software readers, cache copying, and hardware transfer preparation. The existing publication points can remain, provided every key store finishes before those points.

Words used here:

- tron is the inference program under test.
- K and V are the key and value vectors retained for attention.
- A KV page is a 64-token block. A KV slot identifies stored vectors independently of the operation that consumes them.
- AMX and AVX are CPU instruction sets. VNNI layout is the paired-element layout required by the AMX matrix multiplication's second operand.
- bf16 is the 16-bit brain floating-point format.
- RoPE is rotary position encoding. It modifies a key before the cache writer receives it.
- GOF is a group of four tokens prepared for hardware attention. DMA is direct memory access used to transfer this preparation to hardware.
- EAGLE is the speculative-decoding model that can share a cache allocation through a shifted storage view.

All source references below use commit `544ca05c7a954f892f0e23ccb465f74ad46bea5e` of PR #3879, as pinned by the parent audit. They refer to paths inside tron. Extracted files are under `status/codex-evidence/`. No production code was changed. No model, kernel, or hardware test was run for this audit.

The local working checkout `/home/jhan/workspace/tron-amx` is at commit `47f6f2dcebfa69d3c0b2d94096c8ce9bf3718511`. The separate review checkout has an `origin/jhan-amx-p0` reference at `609dabba83547e7d290b161b88221907853eaa8b`. Neither checkout's working files are treated as the current PR snapshot here.

## Writer and publication

```text
key matrix multiply -> RoPE -> save_k -> key-complete publication
                                 |
                                 +-> downstream attention readiness
```

- The handwritten Llama plugin applies optional bias and normalization before RoPE. It then calls the shared `save_k` interface. [h/tron/plugins/llama.hpp:988, h/tron/plugins/llama.hpp:1022]
- Generated attention also calls the shared `save_k` interface. Its generator starts the key input channel before that call. [ingest/src/TronCpp.hs:2339]
- The shared `save_k_impl` writer checks the per-token write mask. It slices one key head from the post-RoPE intermediate and calls `page.k(...).set(kout)`. It publishes key completion after every head for that token has been saved. [h/tron/models/model.hpp:2731, h/tron/models/model.hpp:2747, h/tron/models/model.hpp:2754, h/tron/models/model.hpp:2760]
- The writer credits the hardware transfer group after key completion. It signals downstream minibatches after processing its tokens. A replacement store belongs before both signals. [h/tron/models/model.hpp:2763, h/tron/models/model.hpp:2768]
- The current generic `view::set` evaluates chunks as floating-point vectors before storing them. A replacement must preserve that conversion for non-bf16 source buffers. Keeping the same post-RoPE intermediate is the smallest scope. Fusing RoPE into the new store would also change the plugin boundary and recording path. [h/tron/tensor/view.hpp:186, h/tron/plugins/llama.hpp:1020, h/tron/models/model.hpp:2748]

## Current storage and every production consumer found

For token offset `p`, head dimension `d`, and head width `H`, the current K element offset is `p * H + d` in bf16 elements. The declared indexing is `[p][d / C][d % C]`, where `C` is the vector chunk width. [h/tron/models/kv_cache.hpp:1890]

V is already interleaved across neighboring tokens in the chunk-16 build. Its element offset is `(p / 2) * (2 * H) + 2 * d + (p % 2)` in bf16 elements. This pairs tokens for the probability-times-value multiplication. A VNNI K representation instead pairs neighboring head dimensions for query-times-key multiplication. Copying V's exact indexing to K would pair the wrong reduction axis. [h/tron/models/kv_cache.hpp:1893, h/tron/kernels/amx_attn_iface.hpp:173]

| Consumer | Current dependency | Required integration |
| --- | --- | --- |
| AMX score path | `apply_dense_amx_page` passes token zero's contiguous K row to `qk_rowmajor_128x4`. [h/tron/models/self_attention.hpp:1423] | Pass the packed K base to the corresponding query-times-key kernel. |
| AVX score path | `apply_page_tok` obtains each visible key through `page.k`. [h/tron/models/self_attention.hpp:1579] | Supply one reconstructed key row or a dedicated packed-layout reader. |
| AVX dot product | The bf16 width-128 specialization accepts contiguous view types and loads consecutive vectors. [h/tron/kernels/dotter.hpp:175, h/tron/kernels/dotter.hpp:213] | A custom expression alone does not satisfy its current interface. Preserve arithmetic order if reconstructing rows. |
| Cache append and compaction | `copy_storage_slot` copies `count * head_size * sizeof(bf16)` bytes starting at a K row. [h/tron/models/kv_cache.hpp:1625] | Copy the requested token interval at every dimension pair. Handle source and destination offsets independently. |
| Hardware staging callback | `page_info::k_head_fn` returns a pointer to a contiguous token row. [h/tron/gof.hpp:65, h/tron/scheduler/full.hpp:2506] | Reconstruct K into caller-owned scratch or change the staging consumer to read packed K directly. |
| Hardware staging assembly | `gof::populate` collects all head pointers before calling `k.set_position`. [src/tron/gof.cpp:203, src/tron/gof.cpp:217] | Reconstructed head rows must remain valid together until `set_position` consumes them. A single reused row buffer is insufficient. |

The hardware V callback already uses caller-owned aligned scratch. The caller reserves a separate slice per head. That existing interface is a suitable model for a K reconstruction boundary. [h/tron/gof.hpp:62, h/tron/scheduler/full.hpp:2514, src/tron/gof.cpp:203]

The search over production headers and source is recorded in `status/codex-evidence/k-access-sites.txt`. It found the writer and consumers above. The direct K indexing implementation is confined to `detail::kv_block::k_at`. [h/tron/models/kv_cache.hpp:1906]

## Lifecycle and correctness constraints

- Layout ownership must follow stored KV slots. AMX eligibility also depends on the query scalar type and query-head multiplier. Those are consumer properties. A slot can still need AVX or hardware access when its AMX consumer is ineligible. [h/tron/models/kv_cache.hpp:1018, h/tron/kernels/amx_attn_iface.hpp:159, h/tron/kernels/amx_attn_iface.hpp:163]
- The current runtime-disable contract keeps the same storage and AVX path. A packed-only cache needs a working reader when `TRON_AMX_DISABLE=1` or hardware support is absent. Choosing a storage layout from a worker's AMX availability would violate shared storage consistency. [h/tron/kernels/amx_attn_iface.hpp:42, h/tron/kernels/amx_attn_iface.hpp:47]
- Partial pages, visibility boundaries, sliding-window exclusions, and the EAGLE first-token exception fall through to AVX. Retaining that policy is valid only after the fallback can read the packed layout. [h/tron/models/self_attention.hpp:1503, h/tron/models/self_attention.hpp:1518, h/tron/models/self_attention.hpp:1561]
- `page.count()` bounds active tokens. The ordinary AVX path skips invisible tokens before reading their keys. A new full-width fallback must not consume unwritten tail storage merely because it will mask scores afterward. [h/tron/models/self_attention.hpp:1511, h/tron/models/self_attention.hpp:1569]
- Allocation and rollback change token counts without zeroing K payloads. Fresh assignment resets completion state. Any proposal to compute over unused packed tokens needs an explicit initialization or masked-read rule. [h/tron/models/kv_cache.hpp:791, h/tron/models/kv_cache.hpp:801, h/tron/models/kv_cache.hpp:1487]
- Completion uses an acquire-release increment for each K/V save and an acquire read by consumers. Packed K stores must finish before `mark_k_complete`. Cache copying publishes copied completion after copying payload. [h/tron/models/kv_cache.hpp:1467, h/tron/models/kv_cache.hpp:1481, h/tron/models/kv_cache.hpp:1668]
- Independent token writers must never overwrite neighboring tokens while packing. The current scheduler only groups even/odd pairs to protect V's read-modify-write stores. It does not establish exclusive ownership of an entire packed K tile. A pair of dimensions belonging to one token can be written independently if the store touches only those dimensions. [h/tron/models/model.hpp:209]
- Appending books can split at different source and destination page offsets. EAGLE's extra physical storage slot is copied separately. Both paths must use the new K mapping. [h/tron/models/kv_cache.hpp:818, h/tron/models/kv_cache.hpp:1664, h/tron/models/kv_cache.hpp:1673]
- The arena checks exactly two equal-sized K/V planes per block. A storage permutation can preserve allocation sizes. A second retained K copy cannot satisfy that invariant without revising accounting and allocation. [h/tron/models/kv_cache.hpp:1052, h/tron/models/kv_cache.hpp:1903]

## Verification targets

These are required behaviors to check if implementation proceeds. They are not completed test results.

- Preserve key values across writing, reading, overwrite, arbitrary append offsets, and EAGLE storage shifts. Extend the existing KV data and append cases. [t/t_llama_unit.cpp:324, t/t_llama_unit.cpp:1182, t/t_llama_unit.cpp:1231, t/t_llama_unit.cpp:1766]
- Preserve visibility and running-attention results with incomplete pages and masked ranges. Extend the existing page-range test. Poison unused packed entries to expose accidental reads. [t/t_llama_unit.cpp:1465]
- Preserve the non-bf16 and partial-page dispatch policy. Add correctness assertions that exercise the reconstructed keys rather than only counting dispatch calls. [t/t_amx_dispatch_dtype.cpp:193]
- Verify hardware staging reads each head's distinct values after reconstruction. The required boundary is `gof::populate` through `k.set_position`, including page relocation and reuse. [src/tron/gof.cpp:205, h/tron/scheduler/full.hpp:2494]
- Measure end-to-end performance and the producer/readback costs separately. Insufficient data: this static audit cannot establish a speedup. The resolving measurements are save-K time, partial-page AVX time, hardware staging time, cache append time, and total generated-token latency on the same prompt and batch shapes.

This audit was completed without reading Bill's investigation or Claude's proposed VNNI design.
