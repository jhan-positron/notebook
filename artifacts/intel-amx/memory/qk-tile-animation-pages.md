---
name: qk-tile-animation-pages
description: "2026-10-04 pages in PR3879/new-PRs/new-counters: attn-stats-compare-QA.html (why AMX = 0 under AoF: kernel unit = whole 64-token page, card boundary = last complete GOF of 4, decode closed forms for CPU and AoF verified exactly) and Q-K-page-AMX_tile-claude.html (8-tile usage of the canonical QK kernel vs PR 4424's VNNI-K kernel, JS animations of the 40 tile ops); neither page could be browser-rendered on claude-box (no node, no browser)"
metadata:
  type: project
---

Facts verified for these pages (tron main dd0f942c75; PR 4424 head 30c4ac82cb in VNNIed-K-in-place/tron-VNNIed-K):
- Canonical qk_rowmajor_128x4 (amx_attn.cpp:128-151): acc tiles 0-3 = S^T per 16-token block, K slices (A operand, 16 tokens x 32
  dims, row stride 256 B) in tiles 4/5 in turn, packed Q panel (B, 16 pair-rows x 16 cols, 4 real) in tile 6, tile 7 unused; per
  page 4 zero + 4 Q loads + 16 K loads + 16 TDPBF16PS + 4 stores + AVX-512 transpose into s[4][64]. One tile load covers 16
  tokens x 32 dims, so a page = 4 token blocks x 4 dim steps = 16 loads (jhan's "4 tiles cover 16 rows" is right per slice only).
- PR 4424 qk_vnni_128x4 (branch amx_attn.cpp:195-261; k_vnni.hpp plane[(((s*4+c)*16+dp)*16+t)*2+j]): K plane = 16 contiguous 1 KiB
  panels (step-major, then token block) = B operand in K_TILE_5/6; padded Q rows (16 rows, 4 real, memcpy pack) = A operand in
  Q_TILE_4; S upright in S_TILE_0..3; stores to s16[16][64], rows 0..3 memcpy'd; same tile-op counts, no transpose.
- Decode closed forms per (user, KV head, layer), p = P + s - 1, s = 1..S: CPU ready AMX = sum floor(p/64); pending AMX = #{p mod
  64 = 63}; pending AVX = the rest with (p mod 64)+1 keys; AoF: AMX 0, AVX S visits with (p mod 4)+1 keys, card 4*floor(p/4) per
  query. Match qwen data exactly (4,461 + 3 / 252 / 8,064; 255 / 636 / 293,124).
- jhan's "x = 4 or 16" = GOF (4 tokens, card copy unit) and tile rows (16); the kernel's unit is the whole page (x = 64).

**How to apply:** when jhan opens the animation page, ask for rendering glitches (unverified in a browser). Related:
[[attnstats-20261002-campaign]], [[vnnied-k-in-place-project]], [[attention-stats-claude-page]].

UPDATE 2026-10-04 (later session): attn-stats-compare-QA.html gained section 3 ("Under FPGA attention, can the kernel do anything, and
would a smaller kernel unit help?"; old section 3 Corrections renumbered to 4) answering jhan's follow-up (AoF unit 4 vs AMX unit 64,
"fruitless to lower the AMX unit"). Verified by 3 workflow rounds (wf_f9324547-16c 65 claims, wf_efac67ae-904 84 claims, round 3 diff-only)
against tron dd0f942c75 + exit reports. Facts worth reusing:
- Decode AoF steady state: exact zero AMX (cold cache, prompt 1024/8192). Smaller kernel unit U recovers 0 keys at U=16/8, 252 of 636 tail
  keys at U=4 = 0.09 % (p1024) / 0.01 % (p8192) of decode keys. Under CPU attention U=16 moves 2.09 % (p1024) / 0.29 % (p8192), U=4 2.61/0.36 %.
  Script exec/attnstats-20261002/subunit.py (asserts vs exit report).
- The unit mismatch explains the exact zero only: the card takes all 4,461 ready visits per unit for any card unit dividing 64; the 3 pending
  visits (0.07 %) are what the mismatch removes. Raising the card unit to 64 moves 7,620 keys/unit off the card: 7,428 to AVX, 192 to the kernel.
- Prefill AoF: exact swap kernel -> card (1,056,964,608 keys at p1024); own-chunk pages always AVX in BOTH modes (1,216,512 pending full-page
  AVX visits in all 4 qwen p1024 runs = 528/unit = 8 chunks x 66, NOT 64: positions 63..127 on page A + 127 on page B); copy lag 7,077,888 at
  p8192 = 0.6 %. "Visibility change" (accept a page visible through several ranges) would take 33,792 keys/unit = 6.4 % of prefill keys, same
  in both modes.
- Six AoF cases where the kernel runs: short prompt (8.5 % of decode keys at p64), copy lag (prefill), prefix-cache branch (3.0-3.6 % of the
  closed-form kernel visits 1,258,272 at p1000), shard-end hit then branch (1.4 % vs 1,285,632 at p1024), card K/V store full (TTFT only,
  retry when the edge goes dirty: full.hpp:2503-2617), 2026-09-17 rinzler 57 % busy cycles (open). TRAP: these shares have three different
  denominators; name the base per item.
- Code facts: is_dense_amx_page self_attention.hpp:1710-1721 (4 clauses incl. sliding window; under AoF the flag is sw_required, :1868-1869);
  card boundary full.hpp:2850-2854 / 2882-2889 (count_complete_prefix_gofs shard.hpp:355-365); range split = build_edge_ranges
  ranged_mask.cpp:42-49, 68-80 (NOT the Note [Prompt HW-attention entries] split, which is multi-query only, full.hpp:2051); tile config once
  per worker loop (amx_attn.cpp:88-96), per-page fixed work = 4 zeroes + 4 Q loads + 4 stores + transpose (amx_attn.cpp:128-185); one K tile
  load = 1 KiB, 4 KiB per 16-row block; gpt-oss sliding window 128 keys = ONE whole page + parts of two per step (two whole only at 4/256 steps).
- Time under AoF: busy/job 0.043 ms, 58 % join wait -> CPU scoring <= est. 0.018 ms/job, 36 jobs per worker per step (est. 0.65 ms); no per-path time.
- Round 3 (wf_34b97b85-58e, 53 changed claims) added: prefix-cache shares are 3.0-3.6 % / 1.4 % against the CLOSED-FORM cold count (1,258,272 at
  p1000, 1,285,632 at p1024); the measured p1000 control (1,239,648/request) gives 3.1-3.6 %. Card-full retry gate = room for a shard AND one
  free 64 KiB block (full.hpp:2541-2556). Attention counters: first commit 2026-09-24 on a branch, merged main 2026-10-01 UTC. llama p8192 cpu
  cell measures the 8,064 pending-page base (16,515,072 / 2,048) but also has 16,384 ready AVX keys/unit (report section 8, unexplained).
  Final page: section 3 inserted 2026-10-04, old section 3 -> 4; backup attn-stats-compare-QA.html.bak-20261004-before-section3; fragment
  versions v1-v4 only in the session scratchpad (not kept).
