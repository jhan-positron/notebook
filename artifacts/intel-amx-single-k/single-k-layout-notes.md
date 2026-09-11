# Single-K source audit

Audited exact PR head `60d66d9c04428d907069ced375b93265add02db7`, extracted at
`PR3879-codex/single-k-evidence/source`. All paths/lines below refer to that
revision. The earlier `tron-pr3879-codex` working copy was read briefly and was
not modified; conclusions were rechecked against the exact PR head. No machine
jobs, remote sessions, or Delphi access were used for this audit.

## Conclusion

One persistent CPU K representation in the current mirror format is viable.
It needs a new pagewise AVX consumer and layout-aware save/copy/HW-staging
interfaces. It is not a safe substitution under the existing contiguous-row
`page.k(...).data` interface. The current rationale overstates three barriers:

1. FPGA DMA does **not** directly consume host KV-page K bytes in this path.
   `gof::populate` obtains K rows and shuffles them into GOF staging;
   `shard::xfer_gof` DMAs the staging. Keeping the HBM packing unchanged permits
   a different durable host K encoding without a bitstream change.
2. Current `dotter<bf16,128>` does need contiguous rows, but AVX can consume
   the mirror natively with token lanes. Pagewise packed BF16 instructions do
   not inherently require per-token gathers or an inverse transpose.
3. An AMX kill switch need only disable AMX instructions if a native AVX
   packed-K implementation exists. A separate process-start encoding switch
   can retain a true rollback to the old storage/kernel behavior.

Performance remains a separate issue: tails, sparse masks, stores, defrag,
HW staging and AMX-disabled fallback all need measured coverage.

## Exact layout

Source: `h/tron/models/kv_cache.hpp:640-664`.

For token `p`, dimension `d`, page size P=64, head size H=128, define
`s=d/32`, `c=p/16`, `dp=(d%32)/2`, `t=p%16`, `j=d%2` (integer divisions).

```
packed_offset(p,d) = ((((s*(P/16)+c)*16+dp)*16+t)*2+j)
packed[packed_offset(p,d)] = canonical[p*H+d]
```

Packed shape is `[4 dim blocks][4 token blocks][16 dim pairs][16 tokens][2]`.
There are 16 panels of 1024 bytes; each panel is 16 rows of 64 bytes.
For fixed `s,c,dp`, a ZMM contains 16 tokens' two-dimensional K pairs.
Broadcast the corresponding two BF16 Q elements as one dword and accumulate
with `_mm512_dpbf16_ps`: each FP32 lane becomes one token's score. Four token
blocks cover the page; 64 dimension-pair iterations cover H=128.

The text at `kv_cache.hpp:602-603` says 32 B between a token's values. The
formula actually gives **32 BF16 elements = 64 B** between successive pairs
inside a panel; the two members of each pair are adjacent. This correction
matters for explaining the vector access.

The layout itself can generalize to any H divisible by 32; the current AMX
kernel remains H=128 and query/KV ratio 4. Do not imply all model geometries
are covered merely by replacing the H=128 K plane.

## Production producer/consumer map

| Component | Exact source | Current assumption / required design change |
|---|---|---|
| Projection/RoPE output save | `h/tron/models/model.hpp:2752-2817` | `pg.k(...).set(kout)` stores BF16 canonical row at 2791, then scatter at 2798. Replace with encoding-aware store that preserves BF16 conversion and publishes completion only after the whole packed token is written. |
| Canonical row accessors | `h/tron/models/kv_cache.hpp:1570-1597`, `:2227-2254` | `k_at` returns contiguous BF16 view; cannot honestly retain `.data` for a strided token. Replace hot users with explicit page/row operations. |
| AVX software QK | `h/tron/models/self_attention.hpp:1493-1624`, `h/tron/kernels/dotter.hpp:175-223` | One token at a time with contiguous K rows; replace packed-encoding path with 16-token SIMD blocks. Leave row-major path available during migration. |
| Canonical AMX QK | `h/tron/models/self_attention.hpp:1591-1593` | Build-time alternate branch calls canonical kernel using K token-0 pointer. Encoding dispatch must select the correct kernel, never reinterpret packed data as canonical. |
| Mirror AMX QK | `h/tron/models/self_attention.hpp:1572-1589` | Native packed-K plane already accepted by kernel; primary K-plane pointer can replace mirror pointer. |
| Host-to-device K source | `h/tron/scheduler/full.hpp:2279-2307` | Sole `page_info` factory captures `pg.k(...).data` at 2289-2291. Replace with layout-aware copy/pack callback. V already uses deinterleave scratch at 2293-2301. |
| GOF populate / HBM shuffle | `src/tron/gof.cpp:135-163`, `h/pos/hwattention.hpp:393-397`, `:727-760` | K row callback -> `k.set_position` -> `shuffle_k_entry` -> `shuffle_k_head`. Change input adaptation, preserve staging bytes. |
| DMA submission | `src/tron/gof.cpp:92-128`, `h/pos/hwattention.hpp:939-985` | DMA sources are prepacked `g.k`/`g.v` staging, not book K planes; preserve DMA and HBM layout. |
| Defrag/append token copying | `h/tron/models/kv_cache.hpp:963-990`, `:1951-2021` | K range is one `memcpy` today; packed range copy must split at source/destination 16-token block boundaries and copy corresponding pair-row spans. |
| EAGLE extra physical slot | `h/tron/models/kv_cache.hpp:883-901`, `:1315-1326`, `:2010-2012`; `h/tron/scheduler/full.hpp:1732-1743` | Layout selection and access must follow physical slot, including view remap and copy of extra slot. |
| Test-only fill | `h/tron/models/kv_cache.hpp:997-1003`, `:1356-1374` | Fills physical bytes and reconstructs mirror. Replace reconstruction with logical-value fixtures or native packed interpretation; do not keep tests falsely assuming `.k[p]` is contiguous. |

Search of production `h/` and `src/` found K-row accesses concentrated in
save_k, self-attention, GOF page_info and KV-copy code. This audit found no
KV-page on-disk serialization interface. Do not assert a storage migration
format is required without finding one; in-memory restart/encoding policy
still needs explicit handling.

## Hardware path and lifecycle

`h/pos/hwattention.hpp:130-139` explicitly documents the split: books contain
durable KV; staging is a transient formatted copy, then HBM holds device data.
One GOF comprises four tokens, with current 8 KiB K and 8 KiB V staging
(`h/tron/gof.hpp:1-7, 41-44`). A single persistent CPU K proposal does not
eliminate that staging or HBM copy.

For H=128 the existing HBM K transform is:

```
hw_K[(d % 4) * 32 + d / 4] = logical_K[d]
```

(`h/pos/hwattention.hpp:727-738`). The direct fused adapter is therefore

```
hw_K[(d % 4) * 32 + d / 4] = packed_K[packed_offset(page_token,d)]
```

It can write the current GOF staging destination directly. No persistent
canonical K is needed; no intermediate full page is needed. After review of Bill's supplied PDF, the preferred production design is the direct
fused adapter. A bounded H-element unpack followed by the existing shuffle remains
a useful test oracle or reference fallback. Measure first populate and cold
reconstruction before deleting the mirror. Avoid attaching
one new persistent K scratch vector to every `page_info`: that would reintroduce
memory pressure at a different granularity. A callback taking caller-owned
destination storage is clearer than a callback returning a temporary pointer.

The HBM padding path at `hwattention.hpp:711-720` must continue to preserve
zero-padded cells for head size below baked HW head size. Existing K head-count
and fetcher limits are unchanged. A first H=128-only encoding does not need to
broaden HW support.

Completion and staging lifetime must remain unchanged:

- `save_k` completes K before `mark_k_complete`/`credit_gof_save`
  (`model.hpp:2787-2813`). The GOF counter's acq_rel chain covers all eight
  saves for four tokens (`gof.hpp:151-162`).
- `gof::prepare_for_dma` locks staging, reacquires and repopulates if needed,
  then reserves inflight credit (`gof.hpp:206-232`). Idle eviction releases
  buffers and clears populated (`gof.hpp:235-250`). Every repopulate must use
  the new adapter, not just the first save.
- Live completion and later shard backfill both call this same path:
  `model.hpp:2983-3059`, `src/tron/gof.cpp:170-221`.
- New shards can appear later and backfill old tokens:
  `scheduler/full.hpp:2111-2179`. `src/tron/models/ranged_mask.cpp:67-80`
  moves query work from software to DMA-complete hardware shards; this is
  scheduling, not host K format conversion.
- Prefixes and causal tails can use different backends within a page:
  `scheduler/full.hpp:1658-1709`, `self_attention.hpp:1395-1400`.
- Defrag changes page pointers and token offsets. `full.hpp:1200-1210,
  1214-1240, 1266-1281` rebuilds captured page_info via the single factory.
  Any layout tag/token index/destination callback must be rebuilt there too.
- EAGLE is currently SW-only for its extra cache view (`full.hpp:2117-2118,
  2199-2207`); it must still consume the selected host encoding correctly.

## Storage policy and dtype details

K cache storage is always BF16 (`kv_cache.hpp:2227-2231`), even when the query
executor uses another scalar. Current AMX dispatch correctly restricts Q to
BF16 (`amx_attn_iface.hpp:140-172`, `self_attention.hpp:1352-1362`). Preserve
this separation: swizzled BF16 K does not mean FP32/FP16 Q may be bitcast to
BF16, and setting K directly from a projection must preserve the existing
`.set(kout)` conversion behavior.

The exact PR fixed a shared-slot issue: a writer with query ratio 8 can feed
a read-only ratio-4 consumer. Consequently mirror writers use head-size/scalar
eligibility without their own query ratio (`model.hpp:2763-2774`,
`amx_attn_iface.hpp:159-172`, `kv_cache.hpp:616-626`). The primary K encoding
must belong to the physical storage slot, never to the current writer or
attention operation. Decide it before any K writes and keep it immutable for
the cache lifetime. All books copied together must agree or use explicit
conversion. A model with mixed H=64/H=128 slots needs per-slot decisions.

Recommended initial scope is a deliberate packed-K feature for H=128 slots
with a complete native BF16 AVX fallback; retain row-major encoding for other
slots/executors until their consumers are implemented. Do not silently select
packed K because AMX happens to be usable during one dispatch. A
process-start encoding policy can choose packed vs row-major independently
of `TRON_AMX_DISABLE`; the latter then tests AVX on the *same* packed data.
For full rollback, a separate encoding override selected before cache
allocation restarts in row-major mode. Runtime conversion of populated books
would need synchronization and is unnecessary for this proposal.

If broader coverage is desired, native FP32-Q over packed BF16 K can load each
pair vector and convert the low/high BF16 halves to FP32 via bit shifts/masks,
then broadcast the two FP32 Q values and FMA; keep query precision. AVX2 can
do equivalent 8-token blocks via conversions/FMA without AMX. Neither is
proof of equal performance, and neither should be implemented implicitly by
rounding non-BF16 Q. The simplest staged design keeps existing row-major
fallback for configurations not yet covered.

## Masks, bounds and numerical behavior

Retain all current predicates, not just `page.count()`: EAGLE first-token
exception, range visibility vs sw_required, causal tree branches, sliding
window, and relevant-token count. Current logic is at
`self_attention.hpp:1543-1624` (actual page count documentation at
`kv_cache.hpp:1506-1517`). Construct one 16-bit active-token mask for each
SIMD token block; skip zero masks; keep inactive scores at negative infinity.
Advance and return range_hint exactly as today. Dense AMX can keep its
existing all-64-valid gate.

Do not merely load all 16 tokens, compute, then mask output: inactive columns
can contain uninitialized storage or be written concurrently. Use 32-bit
pair-granularity masked loads so excluded tokens are not read. Distinct token
columns can be written independently; a store must not read-modify-write a
whole vector of neighboring tokens. The existing scalar scatter already
has token ownership (`kv_cache.hpp:645-648`). CPU cache-line false sharing
remains a possible throughput issue to measure under multiple writers.

New lane-as-token AVX accumulation differs from old dotter accumulation plus
horizontal reduction (`dotter.hpp:213-222`). Equal BF16 inputs do not imply
bitwise FP32 score identity. Compare error against high-precision reference
and model-level acceptance separately; do not conflate K storage correctness
with existing AMX PV rounding differences. FP32/FP16 query cases require
their own correctness checks or explicit initial row-major scope.

## Copy algorithm

Full page, same encoding, same geometry: memcpy the complete K plane.
Arbitrary token range: for each source/destination run until the next
16-token boundary, and each dimension block/pair row, copy `run*2` BF16
elements from source token-column offset to destination token-column offset.
This preserves all unselected destination token columns and avoids a
whole-page unpack/repack. Use explicit overlap policy (`memmove`/scratch if
overlap supported), and retain completion-state publication and V/EAGLE
copies in `kv_cache.hpp:1997-2019`. Existing append takes potentially different
source/destination page offsets, so memcpy of a contiguous logical token
range is incorrect. Cross-encoding copies can be an explicit slow adapter
during rollout, or rejected by immutable session policy.

## Capacity and accounting

For one H=128 KV-head/page: K=16 KiB, V=16 KiB, mirror=16 KiB. Reusing the
existing K plane for packed K removes 16 KiB: 33.3% of mirrored K+V+mirror
bytes, or 50% of baseline K+V size. It does not increase the current DMA-pool
page budget if the two-plane allocation remains unchanged. Current mirror
bytes are ordinary RAM outside that pool and now separately counted
(`kv_cache.hpp:562-580, 1101-1118`). Remove mirror counters/allocation and
their tests when removing the arena; do not claim the existing two-plane
hugepage footprint shrinks. Moving durable CPU pages from DMA memory to
ordinary RAM would be an independent allocator/accounting change and is
unnecessary to prove single K.

## Validation needed before replacement

- Exhaustive bit-exact scalar index-map and scrambled per-token store tests;
  no neighbor corruption, 0/15/16/31/32/63 boundaries.
- Query ratios 1/4/8, writer ratio != read-only consumer ratio, mixed slots,
  EAGLE extra-slot selection, and model dtype gates.
- All prefix lengths 0..64 plus sparse/disjoint/causal/sliding-window/EAGLE
  masks; inactive NaN/poison and concurrency instrumentation where feasible.
- Same/cross-page copies, all source/destination offsets, defrag and copied
  completion counters, GOF relocation then repopulation.
- Byte-exact old canonical->HBM staging vs packed->HBM staging comparison,
  including GOFs spanning book boundaries and rebuilding after eviction;
  exercise backfill and live save completion.
- Real attention numeric/model checks separately from layout equivalence;
  AMX-enabled and AMX-disabled packed K, plus old row-major rollback.
- Bench complete/partial/sparse QK, writes, copy/defrag, direct HBM packing,
  and end-to-end prefill/decode. A microkernel win is insufficient to decide
  rollout, particularly on AMD/AVX fallback hosts and mixed CPU/FPGA work.

Relevant existing tests include `t/t_amx_mirror.cpp`,
`t/t_amx_dispatch_dtype.cpp`, `t/t_amx_numerics.cpp`, `t/t_llama_unit.cpp`,
`t/t_gof_dma.cpp`, `t/t_gof_staging_leaks.cpp`, `t/t_hwattention_2.cpp`, and
`t/t_kv_oom_*`. Existing fixtures often write `page.k(...).data` directly and
must migrate with the storage interface rather than bypassing it.
