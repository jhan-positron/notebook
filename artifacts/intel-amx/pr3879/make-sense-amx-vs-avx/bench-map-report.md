# Bench-to-kernel map: fused-sweep-v2 and microbench-quiet vs tron decode attention

Sources
- Fused bench source: deleted in tron commit ff7269a9fa; recovered with
  `git show ff7269a9fa^:src/amx_fused_bench.cpp` in ~/workspace/tron-amx, copy at
  /tmp/claude-0/-home-jhan-workspace-intel-AMX/2549245f-706d-4cdd-bc17-40d5d5064a07/scratchpad/amx_fused_bench.cpp
  (line numbers below refer to that copy). Run by exec/p0-fused-sweep.sh (taskset cpu 96,
  pages in {1,512,16384}, Nq in {1,2,3,4,6,8,12,16}).
- Microbench source: /home/jhan/workspace/ai-runs/tron-pr2934-reconciled/src/amx_microbench.cpp
  (tree at 96e2bdcede, 2026-08-02). Run by exec/p0-slot1-measure.sh:30-45
  (`./gen-delphi/amx_microbench M 200000 variant hd`, cpu 96).
- Tron kernels: /home/jhan/workspace/tron-fence-amx/h/tron/models/self_attention.hpp (apply_page_tok
  1500-1720), src/tron/kernels/amx_attn.cpp (qk_canonical_128x4 117-180, weights_times_v_128x4 183-235,
  qk_mirror_128x4 241-272), h/tron/models/kv_cache.hpp (scaled_v_expr 2026-2170),
  h/tron/kernels/dotter.hpp (dotter<bf16,128> 176-222).

## 1. fused-sweep-v2 variants

One "page" iteration = 64 tokens x 128 dims, Nq query rows, and the FULL pipeline in every variant:
QK, scale, running max, exp, sum, P pack to bf16, PV, v*/s*/m* running-state update
(run_pages, bench 618-690; softmax_page 182-213 shared by all variants). The v* rescale runs only when
the running max moved (bench 200-208). Scale is applied inside QK for avx (231), in the transposing
store for amx44/amx62 (371), as a separate pass for amxqk (629-635). K-mirror packing is excluded from
the timed loop (bench 279-280, 599-607).

| variant | QK | PV | tron code path |
|---|---|---|---|
| avx | AVX dotter pattern, 4 vdpbf16ps + reduce per (query, token) (217-234) | AVX, 8 fp32 accumulators over pair-interleaved V (236-257) | dotter fallback: dotter<bf16,128> per token (self_attention.hpp:1608-1612) then page.scaled_v (1702-1710). tron scaled_v_expr uses 16 accumulators per step (kv_cache.hpp:2047-2070); the bench uses 8. |
| amx44 | AMX canonical: A = K as stored, B = Q packed, S^T 64x16 in 4 C tiles, transposing store + scale (320-389) | AMX 4+4 output blocking (396-426) | canonical build: qk_canonical_128x4 (amx_attn.cpp:117-180, called self_attention.hpp:1592) + weights_times_v_128x4 (amx_attn.cpp:183-235). Same tile pattern. |
| amx62 | same as amx44 | AMX 6+2 output blocking (427-483) | none; tron PV is 4+4 only. |
| amxqk | AMX mirror: A = Q zero-padded to 16 rows, B = K mirror panels, S 16x64 stored directly (297-317) | AMX 4+4 (637) | mirror build (TRON_AMX_K_MIRROR): qk_mirror_128x4 (amx_attn.cpp:241-272, called self_attention.hpp:1583) + weights_times_v_128x4 (1661). Production path. |

Tile config: one LDTILECFG per region, all 8 tiles 16 rows x 64 B, both in the bench (108-116) and in
tron begin_region() (amx_attn.cpp:26-29, 84-91). Query width handled by zero padding to 16 rows in both
(bench 264-275; amx_attn.cpp:190-191; amx_attn_iface.hpp:95-96).

Differences from tron apply_page_tok: tron always computes the correction factor and does the fma
rescale (self_attention.hpp:1652, 1667-1670); the bench skips it when the max did not move. Tron copies
the 4 real score rows with memcpy (1585) and copies amx_o rows into scratch tensors (1665-1666). Tron
packs P inside weights_times_v_128x4 with cvtne2ps (amx_attn.cpp:192-200); the bench packs in
softmax_page (197-198).

## 2. microbench-quiet variants

One iteration = one 64-token page, M query rows: QK for M rows, then PV for M rows, nothing else. No
scale, max, exp, sum, no running state; P is random pre-filled bf16 (amx_microbench.cpp:207-208,
215-250). All buffers static; K VNNI-packed and V pair-packed once before the loop (190-211), so
everything is L1-hot.

- dotter: dotter<bf16,128> per (query, token) over K, then the same dotter loop over V as a "V proxy"
  (224-231). Not scaled_v. Matches tron fallback QK only.
- avx: PR2934 blocked AVX-512 kernels avx512_blocked::qk/pv, 4-row micro-tiles on VNNI K (232-239;
  avx512_blocked_attention.hpp:25-26). Not a shipping tron kernel.
- dispatch: sw_attention::qk/pv with choose_bucket: M<4 dotter + scalar_pv, M 4-7 blocked AVX, M>=8
  AMX v2 (attention_dispatch.hpp:186-191; sw_attention.hpp:85-105, 172-182). Includes a visibility
  mask scan (sw_attention.hpp:113-129). Not a shipping tron kernel.
- v1: hand-rolled single-C-tile AMX QK then PV (45-86), tile config load_attention_tile_config
  (amx.hpp:69-79).
- v2: amx_attention::qk<128,64> + pv<128,64> (90-97): A = Q, B = K VNNI, 4 C tiles; PV 4 C tiles per
  half (amx_attention.hpp:44-112). Same tile pattern as tron qk_mirror_128x4 + weights_times_v_128x4,
  minus P packing and the 16-row zero-padding contract.

## 3. Nq=4 per-page ns (fused-sweep-v2.txt) and ratios avx/variant

| pages | avx | amx44 | amx62 | amxqk |
|---|---|---|---|---|
| 1 | 1618.1 | 1249.9 (1.29x) | 1278.8 (1.27x) | 686.0 (2.36x) |
| 512 | 2466.0 | 1971.6 (1.25x) | 2033.6 (1.21x) | 1470.2 (1.68x) |
| 16384 | 3186.3 | 2294.0 (1.39x) | 2340.9 (1.36x) | 1799.8 (1.77x) |

Microbench M=4 hd=128 per_iter_ns: dotter 1748.1, avx 1137.3, dispatch 1141.0, v1 298.4, v2 263.1.

## 4. Split of one page's time into QK / softmax+update / PV

Neither bench times QK, softmax, or PV separately. Derivable pieces (all "est.", ns per page, Nq=M=4):

Pages=1 (K, V, Q all L1/L2-hot):
- AMX mirror (amxqk) QK+PV tiles = 263 est. (microbench v2 M=4, 263.1). Assumption: v2's tile
  sequence equals qk_mirror_128x4 + weights_times_v_128x4 minus the P bf16 pack.
- AMX mirror softmax + scale pass + P pack + O add + store-to-load round trips = 686.0 - 263.1 = 423 est.
- Canonical transposing-store penalty (QK only; PV and softmax identical) = amx44 - amxqk = 563.9.
- AVX QK (dotter) = 1748.1 / 2 = 874 est. (microbench dotter M=4 runs the same dotter loop twice).
- AVX softmax + PV + update residual = 1618.1 - 874 = 744 est.
- AVX PV (scaled_v pattern) = 744 - 423 = 321 est. Assumption: softmax_page cost is the same in both
  variants (same function, bench 182-213) and the AMX-only pieces (scale pass, O add, 16 vector ops
  each) are small. Two chained cross-bench assumptions; treat as a rough number.

Pages=512 and 16384: only the fused bench ran, so no QK/softmax/PV split is derivable. Derivable:
- Transposing-store penalty amx44 - amxqk: 501.4 (512), 494.2 (16384). Stable across regimes.
- Added memory cost per page vs pages=1: avx +847.9 (512) / +1568.2 (16384); amxqk +784.2 / +1113.8;
  amx44 +721.7 / +1044.1. Each page moves 16 KB K + 16 KB V; the split of the added time between the
  K read (QK) and the V read (PV) is not measured. Insufficient data; a QK-only or PV-only variant at
  pages=512/16384 would resolve it.

## 5. Caveats vs decode in tron

- Pages are a contiguous ring (bench 555, 619-620); tron pages are scattered 64-token KV pages reached
  via enclosing_state.pages[page_ix] (self_attention.hpp:1382-1383).
- Q is one hot 16x128 buffer with Nq rows filled (bench 556, 565-569); tron packs Q lazily once per
  (token, kv_head) and reuses it across the section's pages (self_attention.hpp:1356-1358, 1425-1447).
- Tiles are 16 rows with Nq used; tron only ever runs Nq=4 (kv_mul 4) in the 128x4 kernels.
- Bench K/V values are uniform random in +/-0.3 (bench 558); the v* rescale is skipped when the max did
  not move (bench 200), tron never skips it (1667-1670).
- pages=1 keeps the K mirror hot; tron reads the mirror from a separate arena (self_attention.hpp:1576-1580).
- Bench avx PV uses 8 accumulators; tron scaled_v_expr uses 16 (kv_cache.hpp:2047-2070). Microbench
  "avx" and "dispatch" are PR2934 PoC kernels absent from tron-fence-amx. Microbench dispatch at M>=8
  (276-298 ns) is slower than v2 (263-265 ns); the files read do not explain the gap.
