# Review of PR #3879 as Alexey would write it - round 5

https://github.com/positron-ai/tron/pull/3879 - AMX software attention (default-off): QK/PV tile kernels + K-mirror arena  
Head `234c02bde` (round 4 reviewed `d176c88b3`; delta = ff7269a9f + 901f30d8e (delete src/amx_fused_bench.cpp; rewrite the numbers in Note [Mirror orientation] and three amx_attn.cpp comments), a5ef65761 + 234c02bde (a file since removed from the PR): 5 files, +47/-977, of which -732 is the deleted src/amx_fused_bench.cpp); base `1407f48dd`; 14 files, +1817/-37. Written 2026-08-25. HTML twin: `alexey-review.html`; rounds 1-4 archived as `alexey-review-1.html` ... `-4.html`.

Lineage note: "mirror" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). "canonical-K" = K in today's original single-copy storage, read as-is.

Each comment shows the source lines it refers to (head `234c02bde`; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.

## 1. Verdict

**CHANGES_REQUESTED**

The bench is gone and the pair it left behind now matches a recorded sweep - good, that was the half I refused to approve.  Two things about what replaced it: the date on the pair (`2026-08-19`) is not the date of the only sweep that carries 1249.9/686.0, and the command line that ff7269a9f recorded went out again in 901f30d8e, so a reader still has no way to reproduce 1250 - the Note is now the only place the pair lives, so the provenance has to live there too; and the Note attributes the whole ~560 to transpose and score traffic when the canonical bench variant also re-packed Q once per page - see the header.  Codex's two comments are both right on the facts and both sit on lines I already commented on in round 1 (the 64B contract at `amx_attn_iface.hpp:102`, the pack/region at `self_attention.hpp:1361`); I've answered them inline, and the alignment one wants a fix either way.  What still blocks from my side: the 3-argument `book`/`try_create` that default `amx_mirror_eligible` to allocate, and a compile-only configuration so the flagged code can't rot after merge - all the more since no build or test job has run on this PR at all (draft without the `Run CI` label: every run on the branch is lint only, and the last eight commits have none).  The description still says nothing about the `kv_block_planes` rename, `v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the `amx_mirror_eligible` plumbing through `node_base`.  The rest is carried over unchanged below.

**Round 5 in one line:** 5 comments made obsolete by the deletion (section 2) and 1 merged - R1-51's blocking half is resolved and its provenance half now lives in the R1-14 thread; 69 carried over (five with a follow-up); 4 new: the bench pack asymmetry inside the ~560, the history sentence in the kernel TU header, and his two replies to the Codex review. Blockers 3 -> 2: the default-true 3-argument constructor (`kv_cache.hpp`) and the missing compile-only configuration (`t/CMakeLists.txt`) - each now carries a compiled suggested fix; the kernel-copy blocker is resolved.

## 1a. What EAGLE is, and how likely it is to run together with the mirror

_Added on request in round 3 (2026-08-25) and carried unchanged; background for the EAGLE items, written from the tree at `96b5a6c72` (the fix landed in that commit)._

**What EAGLE is.** EAGLE is a speculative-decoding method: a small _draft_ model proposes several next tokens from the base model's hidden state, and the base model (the _validator_) checks them in one forward pass, so accepted tokens cost less than one full decode step each. In tron the draft is a one-layer model that shares the validator's KV books:

- **Enablement.** `src/tron/scheduler/full.cpp:307-308`: if `cfg.support_eagle` or the process-wide `prefer_eagle` is set, `find_eagle_model("eagle-<model>")` looks the draft up in the registry; if found, `support_eagle` is forced on. `prefer_eagle` reads `TRON_USE_SPECULATION` and is `false` by default (`full.cpp:40-43`, "Disabled by default"); `runtron --draft eagle` sets `support_eagle` per run (`h/runtron/stream_generate.hpp:1421`). Nothing under `.github/`, `bin/ci` or `config/test-benchmarks.json` turns speculation on.
- **Same model type.** The draft is created with the validator's own `model_t` and a copied config with `max_layers = 1`, `is_speculator = true` (`full.cpp:317-324`). Its attention geometry - and therefore its `shape_ok` - is the validator's.
- **Shared books, extra slot.** The draft scheduler adopts the validator's token-tree root (`full.hpp:1446-1448`). Books are created with `support_eagle`, which adds one physical storage slot after the validator's logical slots plus per-token embedding storage (`x_bytes`). Around each draft forward the scheduler calls `set_storage_view(eagle_storage_offset())` on every touched book and `reset_storage_view()` after (`full.hpp:1732`, `:1740`), so the draft's logical slot 0 resolves to that extra slot while canonical accessors go through `kv_blocks_alias`.
- **Registry.** Two production families have a draft: `eagle-llama-3.1-8b-instruct` (`config/models.yaml:254`; base shape 32/8/128 - AMX-eligible) and `eagle-llama-3.3-70b-instruct` (`:298`; base 64/8/128 - ratio 8, ineligible).

```
one KV book, one page, token j          canonical K (DMA)              mirror planes (arena)
                                        [slot 0][slot 1..L-1][slot L]  [M(0)][M(1..L-1)][M(L)]
validator forward (no view)
  save_k(slot 0) = K_v            --->   slot 0                  --->   M(0)
draft forward (view = slot L)
  save_k(slot 0) = K_d, same j    --->   slot L (follows view)
      before 96b5a6c72: mirror ignored the view          -X->   M(0)  (validator's plane overwritten)
      after:            mirror_view_offset_             --->   M(L)
```

**The two ways out of the round-1 bug.** Option A: make `mirror()` follow the view (what `96b5a6c72` does, via `mirror_view_offset_`). Option B: assert that no view is active while a mirror arena exists - i.e. forbid EAGLE and the mirror in the same process.

**How likely EAGLE and the mirror would be active together (the cost of option B).**

| fact | evidence | direction |
|---|---|---|
| Speculation is off unless an operator asks for it | `prefer_eagle` defaults false; `runtron --draft eagle` is per run; no CI/benchmark config enables it | lowers overlap today |
| Exactly one eligible production model has a draft | llama-3.1-8b (32/8/128) is in the gate and measured in this PR (+15%/+20% decode); llama-3.3-70b is ratio 8, outside the gate | overlap is one model, not zero |
| The draft inherits the validator's geometry | same `model_t`, `full.cpp:321-324` | whenever the validator is eligible, the draft's write-through is too - the bug was reachable, and option B would have to refuse the draft |
| Both features target decode latency on the same hosts | the mirror is opt-in "for pinned AMX deployments"; EAGLE cuts decode steps | the deployment that wants one is the deployment that wants the other |
| How often `--draft eagle` is used in production | not in the tree | Insufficient data |

Reading: not a frequent configuration as the tree stands (speculation is opt-in and absent from CI), but not a corner case either - llama-3.1-8b is the one eligible production model with a draft, and option B would have made tron's two decode accelerators mutually exclusive on exactly that model. The PR chose option A, which removes the question; what remains for review is the shape of that fix (two copies of the view state, section 3).

## 2. Resolved since round 4

Open comments the three commits addressed (0 fixed), made moot by deleting the file they were about (5 obsolete), or whose remaining half now lives in another thread (1 merged; the 'how it was addressed' column names the threads).

| comment | where (234c02bde) | what was asked | how it was addressed | his reply, if any |
|---|---|---|---|---|
| R1-51 (merged) | `src/amx_fused_bench.cpp` (deleted) | A 732-line `main()` in `src/` that no CMake target builds, which re-implements every shipped kernel by hand (`pack_q`, `qk_amx`, `qk_amx_rowmajor`, `pv_amx`, `pack_k_mirror`, `st_to_s`).  Any kernel fix now has to be ... | blocking half resolved: src/amx_fused_bench.cpp deleted in ff7269a9f, no CMake/greppable trace left (amxqk, amxpl, transpose16x16, t_amx_attention, amx_fused_bench: 0 hits at 234c02bde); remaining half (the command line that produced the numbers) was recorded by ff7269a9f and removed again by 901f30d8e - now asked in the R1-14 follow-up. Status verifier + refuter: PARTIAL, still_blocker=false. | The copy is gone, good.  The command line went with 901f30d8e - see `amx_attn_iface.hpp:138`. |
| R1-52 (obsolete) | `src/amx_fused_bench.cpp` (deleted) | `amxqk` and `amxpl` are missing from this list (and `amx_attn.cpp:230` cites `amxqk`). | src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde (git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits); the amx_attn.cpp:240-241 comment that cited the `amxqk` variant now describes the kernel only |  |
| R1-53 (obsolete) | `src/amx_fused_bench.cpp` (deleted) | There is no `t_amx_attention` on main; it lives on `bill-amx`.  Also 2e-2 relative is a long way from the `1e-4 * abs_mass` `t_amx_numerics` uses in this same PR, so "practice" is doing a lot of work here.  Flush the ... | src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde (git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits) |  |
| R1-54 (obsolete) | `src/amx_fused_bench.cpp` (deleted) | The degree-5 Taylor terms give ~3.3e-6 at \|f\| = 0.5 (I checked), not 2e-7.  Fix the number or delete the sentence; the conclusion holds either way. | src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde (git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits) |  |
| R1-55 (obsolete) | `src/amx_fused_bench.cpp` (deleted) | Neither `transpose16x16` nor its reference is used by any variant (`st_to_s` has its own copy); they exist to validate each other.  Flush all three pieces. | src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde (git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits) |  |
| R1-56 (obsolete) | `src/amx_fused_bench.cpp` (deleted) | A question mark in a size comment means we don't know the size.  It's 4*16*32 bf16 = 4*16*64 bytes; write one.  Also, s/(Bill's formulation)// at :279 - same as the "ours" in the header Note. | src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde (git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits) |  |

## 3. Open comments (73: 69 carried over from rounds 1-4, 4 new in round 5)

Carried-over comments keep their earlier text; where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**; replies he would post in the two Codex threads are marked **reply** and quote the bot comment they answer. A leading `[blocker]` marks the comments the body names.

### h/tron/kernels/amx_attn_iface.hpp

#### `h/tron/kernels/amx_attn_iface.hpp:56` R1-10 (A3)

```cpp
   53  // Note [Tile stores write 16 rows]
   54  // ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
   55  // TILESTORED always writes ALL 16 configured tile rows, no matter how many
   56* // carry real data: a width-4 result still stores 16 rows. Every output
   57  // buffer handed to a kernel below must therefore be sized for 16 rows -
   58  // a "4 x N" buffer is a silent stack overrun (rows 4..15 land past its
   59  // end). Rows 4..15 receive zeros; only rows 0..3 are the result.
```

Not true for `qk_canonical_128x4`, which writes exactly 4 rows into `s` (and `t_amx_numerics` hands it a 4-row buffer).  Scope the sentence to the kernels whose argument receives a `TILESTORED` directly.

_Verification: round 1 (R1-10), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:56; h/tron/kernels/amx_attn_iface.hpp:57; src/tron/kernels/amx_attn.cpp:156_

#### `h/tron/kernels/amx_attn_iface.hpp:75` R3-02 (A3)

```cpp
   72  // The one attention shape these kernels serve - the tile identity of
   73  // Note [AMX attention dispatch]: a 64-token KV page, 128-dim heads, and 4
   74  // query heads per KV head (4 x 128 bf16 = one full tile operand). Every
   75* // shape literal in the AMX code derives from these three.
   76  inline constexpr size_t PAGE_TOKENS_64 = 64;
   77  inline constexpr size_t HEAD_SIZE_128 = 128;
   78  inline constexpr size_t GROUP_HEADS_4 = 4;
```

"Every shape literal in the AMX code derives from these three" - `DIM_STEP = 32`, `PANEL_ELEMS = 16 * 16 * 2`, the `4` in `step * 4`, the `16`s in the pack index and the `64/16/32/48` in the output stores are still literals in `amx_attn.cpp`, `scatter_k_mirror` has its own 16 and 32, and `Q_PACK_ELEMS_2048` on the next line derives from `TILE_ROWS_16`, a fourth.  s/Every shape literal in the AMX code derives from these three/`shape_ok` and the kernel buffer sizes are written in terms of these/ - or make it true.

_Verification: round 3 (R3-02), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:74; h/tron/kernels/amx_attn_iface.hpp:75; h/tron/kernels/amx_attn_iface.hpp:83_

#### `h/tron/kernels/amx_attn_iface.hpp:77` R3-01 (B3)

```cpp
   75  // shape literal in the AMX code derives from these three.
   76  inline constexpr size_t PAGE_TOKENS_64 = 64;
   77* inline constexpr size_t HEAD_SIZE_128 = 128;
   78  inline constexpr size_t GROUP_HEADS_4 = 4;
   79  // One packed Q group (the pack_q_group_128x4 / pack_q_rows_128x4 output
   80  // buffer): 16 tile rows x 128 bf16 = 2048 bf16 = 4 KB. The VNNI pack
   81  // (4 panels x 16 dim-pair rows x 32 bf16) and the zero-padded A-operand rows
   82  // (16 x 128) are the same size, so callers reuse one buffer.
   83  inline constexpr size_t Q_PACK_ELEMS_2048 = TILE_ROWS_16 * HEAD_SIZE_128;
   84  static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value");
```

A constant whose name carries its value is a literal with a longer name: the day `HEAD_SIZE_128` is not 128 the name lies, and `static_assert(Q_PACK_ELEMS_2048 == 2048, "the constant's name states its value")` guards a problem we created.  `tile_rows`/`q_pack_elems` were fine; `head_size`, `group_heads`, `page_tokens` say what they are, and every constant in `h/tron/models`, `kernels` and `scheduler` is lower snake_case (`page_size`, `kv_block_planes`, `illegal_sliding_window`).  Flush the `static_assert` with the rename.

_Verification: round 3 (R3-01), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:76; h/tron/kernels/amx_attn_iface.hpp:77; h/tron/kernels/amx_attn_iface.hpp:78_

#### `h/tron/kernels/amx_attn_iface.hpp:88` R2-06 (A3)

```cpp
   86  // THE shape gate: the AMX kernels serve exactly one attention shape, 4 query
   87  // heads x 128 dims per KV head (the tile identity, see
   88* // Note [AMX attention dispatch]). Shared by the dispatch, the save_k mirror
   89  // write-through, and the mirror-arena allocation, so the reader and the
   90  // writers can never disagree about which models take the AMX path.
   91  constexpr bool shape_ok(size_t model_head_size, size_t model_kv_mul) noexcept {
   92    return model_head_size == HEAD_SIZE_128 && model_kv_mul == GROUP_HEADS_4;
   93  }
```

"so the reader and the writers can never disagree" - two of the three writers don't use this gate (the `copy_storage_slot` and `fill_random` rebuilds scatter for any geometry whose plane is non-null), and the 3-argument `book` forms pass `true`.  It holds for books the scheduler creates.  Say that, or make it true.

_Verification: round 2 (R2-06), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:89; h/tron/kernels/amx_attn_iface.hpp:90; h/tron/models/kv_cache.hpp:1312_

#### `h/tron/kernels/amx_attn_iface.hpp:96` R1-16 (A3)

```cpp
   95  // True when the CPU, the OS, and the per-process permission all allow AMX,
   96* // and TRON_AMX_DISABLE is not set. See Note [AMX attention dispatch].
   97  bool available() noexcept;
```

s/is not set/is not `1`/ - the A/B recipe in `t_amx_logit_ab.cpp` explicitly uses `=0`.

_Verification: round 1 (R1-16), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:96; src/tron/kernels/amx_attn.cpp:68; t/t_amx_logit_ab.cpp:7_

#### `h/tron/kernels/amx_attn_iface.hpp:102` R1-12 (A3)

```cpp
   99  // Pack one query group (4 query heads x 128 dims, contiguous bf16) into the
  100  // tile B-operand (VNNI pair-interleaved) layout consumed by
  101  // qk_canonical_128x4.
  102* // `packed` must hold Q_PACK_ELEMS_2048 bf16 (4 KB), 64B-aligned.
  103  // `packed` layout: 4 panels, one per 32-dim step of the head; each panel is
  104  // 16 dim-pair rows x 16 query columns (columns 0..3 = the 4 heads, columns
  105  // 4..15 zero) x 2 paired values:
  106  //   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
  107  //     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
  108  void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
```

Who guarantees the 64B alignment?  `amx_qpack` is a `std::vector<uint16_t>`, which promises 16.  The kernels only `_tile_loadd` it, so either drop the requirement from the contract (here and at :135) or give the buffer `alignas(64)` storage.  Fix one.

_Verification: round 1 (R1-12), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:102; h/tron/kernels/amx_attn_iface.hpp:156; h/tron/models/self_attention.hpp:1361_

#### `h/tron/kernels/amx_attn_iface.hpp:108` R1-13 (B5)

```cpp
   99  // Pack one query group (4 query heads x 128 dims, contiguous bf16) into the
  100  // tile B-operand (VNNI pair-interleaved) layout consumed by
  101  // qk_canonical_128x4.
  102  // `packed` must hold Q_PACK_ELEMS_2048 bf16 (4 KB), 64B-aligned.
  103  // `packed` layout: 4 panels, one per 32-dim step of the head; each panel is
  104  // 16 dim-pair rows x 16 query columns (columns 0..3 = the 4 heads, columns
  105  // 4..15 zero) x 2 paired values:
  106  //   packed[((step * 16 + dim_pair) * 16 + q_head) * 2 + j]
  107  //     == q_group[q_head * 128 + step * 32 + 2 * dim_pair + j]
  108* void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept;
```

`uint16_t*`?  Any reason not to take `const bf16*` (or a `const_view<bf16, ..., seq<128>>` for the Q rows and a `std::array<float, 16 * 128>&` for the 16-row outputs)?  Then the size and alignment contracts in the Note are carried by the type instead of prose, and the dozen `reinterpret_cast`s at the call sites go away.  The header would still have no intrinsics.

_Verification: round 1 (R1-13), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:108; h/tron/kernels/amx_attn_iface.hpp:114; h/tron/kernels/amx_attn_iface.hpp:125_

#### `h/tron/kernels/amx_attn_iface.hpp:138` R1-14 (A3/A4)

```cpp
  135  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  136  // (K consumed exactly as stored) and must then round-trip the score tile
  137  // through memory and transpose it - a ~560 ns/page whole-path cost at
  138* // width 4 (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19;
  139  // transpose work + score traffic combined, not isolated). NOT a
  140  // store-forwarding stall: 64-byte
  141  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
  142  // a 6962P microbench measured no stall on that path; the hard restriction
  143  // is the opposite direction, any store -> TILELOADD cannot forward.
```

There is no store-forwarding microbench in the tree, and the 982/686 figures come from `amx_fused_bench.cpp` with unrecorded arguments.  Numbers we can't reproduce shouldn't be stated as facts in a Note.  Record the command that produced them where a reader can find it, and reference that from here.  The figures now agree with a recorded sweep (`exec/results/slot1/fused-sweep-v2.txt`: 1249.9 / 686.0, same ring) - good.  But that file is stamped `2026-08-18T18:34:53Z`, still the 18th in PDT, so where does 08-19 come from?  If there was no second run, s/2026-08-19/2026-08-18/.  And the command line that ff7269a9f recorded went out again in 901f30d8e, so a reader still has nowhere to go to reproduce 1250: this Note is now the only place the pair lives, so let's name the record and the command here, or drop the numbers.  The forwarding-stall "6962P microbench" at :142 still has no record at all.

**Suggested fix** (added at your request)

Replace lines 137-139 with:

```suggestion
// through memory and transpose it - a ~560 ns/page whole-path cost at
// width 4 (1250 vs 686 ns per L2-resident page: exec/results/slot1/
// fused-sweep-v2.txt in the campaign workspace, 2026-08-18, 6962P core 96,
// `taskset -c 96 ./amx_fused_bench 4 200000 amx44 1` / `amxqk` on the
// stand-alone benchmark at d176c88b3; ~500 ns once that benchmark's per-page
// scalar Q pack is amortized, 512-page ring 1972 vs 1470 - the pack, the
// transpose and the score round trip were not isolated). NOT a
```

_Fix note: Replaces Note lines 137-139 and keeps :140 ('store-forwarding stall: 64-byte') reading on. Names the record, the host, the corrected date (file header 2026-08-18T18:34:53Z), the command ff7269a9f recorded and 901f30d8e removed, and the pack artifact R5-01 asks about (pages=512 row: 1971.6 vs 1470.2). 'core 96' is the header's 'cpu 96'; '6962P' rests on the PR body's host line, not on the sweep file. The '6962P microbench' sentence at :140-142 is unchanged: R1-14's ask for a record of that measurement is still open and no replacement text can supply one._

_Verification: round 1 (R1-14), partial | text edited in round 5: the round-1 sentence named a home for the numbers that is no longer in the PR: met: the unrecorded 982 figure is gone; 1250/686 match fused-sweep-v2.txt:14/:30 (amx44 / amxqk, Nq=4, pages=1). Not met: the Note states the numbers as facts with no record or command a reader can follow (the record ff7269a9f wrote was removed again by 901f30d8e); the date 2026-08-19 at :138 does not match the sweep header 2026-08-18T18:34:53Z (mtime 2026-08-18 11:38 -0700; exec/logs/p0-fused-sweep.log lists both sweeps on 08-18); the '6962P microbench measured no stall' sentence at :142 has no recorded source anywhere. '6962P' is not in the sweep header (cpu 96 is a core index); it rests on the PR body's host line. | evidence: h/tron/kernels/amx_attn_iface.hpp:137-142; exec/results/slot1/fused-sweep-v2.txt:1,14,30; exec/logs/p0-fused-sweep.log_

#### `h/tron/kernels/amx_attn_iface.hpp:139` **new** (A3/A4)

```cpp
  133  // Note [Mirror orientation]
  134  // ~~~~~~~~~~~~~~~~~~~~~~~~~
  135  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  136  // (K consumed exactly as stored) and must then round-trip the score tile
  137  // through memory and transpose it - a ~560 ns/page whole-path cost at
  138  // width 4 (1250 vs 686 ns per L2-resident page, 6962P, 2026-08-19;
  139* // transpose work + score traffic combined, not isolated). NOT a
  140  // store-forwarding stall: 64-byte
  141  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
```

IIUC the `amx44` variant re-ran the scalar `pack_q` inside `run_pages` (so once per page at `pages=1`) while `amxqk` built `Qpad` once before the timer, and production packs Q once per (token, kv_head) per section - so isn't part of the 560 a bench artifact rather than transpose or score traffic?  The 512/16384-page rows, where the pack is amortized, show ~500.  Either name it in the 'combined' list or quote the amortized gap and drop 'L2-resident'.

_Verification: new in round 5 (R5-01); finder 'numbers' #3, refuter PARTIAL (line refs corrected), would-he-raise=yes (he commented on pack_q :264 and the ':279 Cost is EXCLUDED' line in round 1). Verified by the orchestrator in the d176c88b3 tree: amx_fused_bench.cpp:610-614 run_pages -> `if (!is_qk_mirror) pack_q(Q.data(), nq, Bp);` before the page loop (:618), timed per run_pages call (:721-726); :599-606 build Kmir/Qpad once for amxqk outside the timer. Sweep: 1249.9-686.0 = 563.9 (pages=1); 1971.6-1470.2 = 501.4 (pages=512); 2294.0-1799.8 = 494.2 (pages=16384). Refuter's pack_q re-timing (65-95 ns on a non-6962P host, est.) is consistent with the ~62 ns shrink but is NOT quoted in the comment. Production pack-once: self_attention.hpp:1354-1355 comment, :1419 mask test, :1424/:1429 pack, :1434 mask set._

#### `h/tron/kernels/amx_attn_iface.hpp:150` R1-15 (B11)

```cpp
  149  // there too). Both ship:
  150* // canonical-K is the supported default; the mirror is opt-in
  151  // (TRON_AMX_K_MIRROR) for pinned AMX deployments. Precedent: the mirror
  152  // formulation is PR #2934's k_vnni idea; this arena implementation is ours.
```

Keep the pointer to #2934 if it helps a reader find the other formulation; flush "this arena implementation is ours".  Attribution goes in the PR description.  Also, what's a "pinned AMX deployment"?  Say the concrete condition (builds that will only run on AMX hosts, since the arena RAM is wasted otherwise).

_Verification: round 1 (R1-15), not addressed | evidence: h/tron/kernels/amx_attn_iface.hpp:150; h/tron/kernels/amx_attn_iface.hpp:151; h/tron/kernels/amx_attn_iface.hpp:152_

### h/tron/kernels/page_share_counters.hpp

#### `h/tron/kernels/page_share_counters.hpp:6` R1-17 (A1/A9/A3)

```cpp
    2  // Page-sharing instrumentation: measures how many query tokens of the
    3  // current minibatch legally attend the SAME physical KV page in one visit -
    4  // the achievable batching width for the AMX kernels.
    5  //
    6* // Compiled in only with -DTRON_PAGE_SHARE_COUNTERS=1. Zero hot-loop cost:
    7  // callers accumulate plain locals and flush to the global atomics once per
    8  // apply_page_range call (roughly once per (worker, kv_head, page-range) - a
    9  // few tens of thousands of flushes per second at most).
   10  //
   11  // Dump: automatic at process exit to stderr.
   12  
   13  #ifdef TRON_PAGE_SHARE_COUNTERS
```

Is this instrumentation still needed?  Its conclusion (width 4 is the guaranteed decode width) is already baked into the kernel shape, nothing in CMake defines `TRON_PAGE_SHARE_COUNTERS`, and it adds a third flag family plus an exit-time printer under `kernels/` for something that instruments `models/`.  I'd record the histogram in the PR description and drop the code; if we want a live counter, the `TRACE_EVENT` args two lines above the page loop are the existing place.  Also, the guard is `#ifdef`, so `=0` enables it too; and with the flag on there is an increment per (page, token) inside the loop, so "Zero hot-loop cost" isn't what the code does.  With the histogram's home gone from the PR, the PR description is where its conclusion belongs; the question whether the code stays is unchanged.

_Verification: round 1 (R1-17), not addressed | text edited in round 5: the proposed home of the histogram is now the PR description | evidence: file unchanged since d176c88b3_

### h/tron/models/kv_cache.hpp

#### `h/tron/models/kv_cache.hpp:182` R2-05 (A5/B1)

```cpp
  181  template <size_t n_kernels>
  182* constexpr bool amx_mirror_eligible(
  183      std::array<attention_kernel_spec, n_kernels> const& kernels) noexcept {
  184    for (auto const& kernel : kernels) {
  185      if (amx_attn::shape_ok(kernel.geometry.kv.head_size, kernel.geometry.kv_mul())) {
  186        return true;
  187      }
  188    }
```

Any eligible kernel makes the whole arena: for a model with one eligible and one ineligible attention kernel the ineligible slots' planes are allocated (`kv_bytes/2` covers every slot), never written by `save_k`, and rebuilt on every page move by `copy_storage_slot`.  No in-tree plugin is mixed today, so fine - but say so here ("any kernel; sized for all slots; only eligible geometries are written through"), and a two-kernel array in `t_amx_arena_leak` would record the intended answer.

_Verification: round 2 (R2-05), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:539` R1-25 (B7)

```cpp
  539* #if defined(TRON_AMX_K_MIRROR) && !defined(TRON_AMX_DISPATCH)
  540  #error "TRON_AMX_K_MIRROR requires TRON_AMX_DISPATCH"
  541  #endif
```

CMake already refuses this combination (`src/tron/CMakeLists.txt:178`).  If the `#error` is for non-CMake builds, say so; otherwise one check is enough.

_Verification: round 1 (R1-25), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:586` R1-24 (A9)

```cpp
  584  // pair-interleaved layout natively, so V needs no second copy. Reopen only
  585  // if a card consumes VNNI K natively or an FPGA-free build ships.
  586* inline constexpr size_t kv_block_planes = 2;
  587  #ifdef TRON_AMX_K_MIRROR
  588  // Note [K mirror coherence]
```

Is `kv_block_planes` ever anything but 2?  If it's a leftover of the in-block third-plane design, the rename of the pre-existing `2 *` literals (here, :1138, `t_llama_unit.cpp:415`) is an unrelated refactor - its own small PR, or drop it.

_Verification: round 1 (R1-24), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:588` R1-19 (A7)

```cpp
  588* // Note [K mirror coherence]
  589  // ~~~~~~~~~~~~~~~~~~~~~~~~~
  590  // Invariant: whenever the mirror arena exists, every stored token's mirror
  591  // bytes equal scatter_k_mirror(its canonical K row). The mirror is a pure
  592  // derived view; canonical K stays the source of truth (the FPGA and the AVX
  593  // fallback keep reading it as stored). Exactly two production write sites
  594  // maintain the invariant:
  595  //   1. the save_k write-through (model.hpp) on the RX worker, right after
```

Lock-free cross-thread hand-off, eh?  Then the Note should say what orders the RX worker's plain stores before the attention worker's tile loads.  IIUC it is not `mark_k_complete` (software attention never reads `kv_saves_`); it is (a) pages written this forward are never in the ready plan, and (b) the write precedes `upstream_kvs_ready.count_down()` in program order and the pending pass acquires on `wait()`.  Write that down, and say the write must stay before the count-down for that reason, not for L1 locality, or someone will "optimize" it later.

_Verification: round 1 (R1-19), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:602` R3-04 (A3)

```cpp
  598  //      goes through copy_storage_slot, which regenerates the mirror from
  599  //      the DESTINATION's just-copied canonical K, so it is coherent no
  600  //      matter the source book's mirror state.
  601  // Both sites address the plane of the PHYSICAL slot the canonical row lives
  602* // in: under the EAGLE storage view (set_storage_view) mirror() remaps logical
  603  // slot 0 to the extra physical slot exactly as kv_block() does, so the
  604  // draft's write-through can never land in the validator's slot-0 plane.
  605  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  606  // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  607  // the mirror checks in t/t_llama_unit.cpp (append + defrag, and the EAGLE
```

Only the `save_k` write-through goes through `mirror()`; `copy_storage_slot` (:1883) addresses the arena by physical `storage_offset` and never sees the view.  "Both sites ... mirror() remaps" sends a reader looking for view handling in the rebuild.  Scope the sentence to site 1.

_Verification: round 3 (R3-04), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:607` R1-20 (A3)

```cpp
  605  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  606  // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  607* // the mirror checks in t/t_llama_unit.cpp (append + defrag, and the EAGLE
  608  // storage-view cases).
```

There is no separate defrag operation; `append` is the defrag path and the test calls it once.  s/(append + defrag)/(`book::append`, the defrag path)/.  This sentence was edited in 96b5a6c72 and kept "(append + defrag)".

_Verification: round 1 (R1-20), not addressed | evidence: file unchanged since d176c88b3_

#### [blocker] `h/tron/models/kv_cache.hpp:769` R2-03 (A12/A6)

```cpp
  764    // Legacy form: keeps today's behavior (mirror arena allocated whenever AMX
  765    // is available) for tests and callers that carry no model information.
  766    book(size_t n_pages,
  767        size_t storage_slot_count = n_slots,
  768        bool support_eagle = false) noexcept
  769*   : book(n_pages, storage_slot_count, support_eagle, /*amx_mirror_eligible=*/true) {}
```

A constructor that defaults `amx_mirror_eligible` to true allocates the arena for a book that may never read it - the thing this commit set out to stop.  Who still needs the 3-argument forms?  As far as I can see the tests, and the `sequence_cache_behavior` concept at :1328-1330, which now describes yesterday's interface.  Let's update the concept to the 4-argument forms, pass the flag explicitly in the tests (about 24 sites), and flush the delegating overloads (here and `try_create` at :965).  Also, "keeps today's behavior" describes the diff, not the code.  The new EAGLE coherence test (`t_llama_unit.cpp:338`) relies on the arena and therefore on this implicit `true` - a third user of the 3-argument form (with `:272`).  Pass the flag explicitly there either way.

**Suggested fix** (added at your request)

1. Delete the 3-argument `book` constructor (:764-769) and its comment; the 4-argument constructor becomes the only one, with a comment that says why there is no default.
2. Delete the 3-argument `try_create` overload (:975-984 with its comment); the STORY-127 comment stays on the 4-argument one.
3. Update the `sequence_cache_behavior` concept (:1352-1357) to the 4-argument forms, so the concept describes the interface that exists.
4. Pass the flag at every construction site in `t/` (29 lines in `t_llama_unit.cpp`, 2 in `t_amx_arena_leak.cpp`; table below). `true` everywhere preserves today's behaviour exactly; the mirror tests (`t_llama_unit.cpp:257`, `:272`, `:338`, `:1004`, `:1076-1077`, `:1221`, `t_amx_arena_leak.cpp:79`) need `true`; the rest can be tightened to `false` afterwards where the mirror is irrelevant - that is the author's call, not part of this fix.
5. Production is untouched: `full.hpp:832` and `:1456` already pass the flag. R2-13 (both arena-leak arms through `try_create`) and R2-14 (the control's wording) stay as separate items; R2-14's control line is covered by the table.

`h/tron/models/kv_cache.hpp`:764-773 - replace the legacy constructor and both comments with one comment on the remaining constructor (line 774 `book(size_t n_pages,` follows unchanged)

```suggestion
  // `amx_mirror_eligible` is the scheduler's
  // amx_mirror_eligible(plugin::attention_kernels): a model without an
  // AMX-eligible attention shape allocates no mirror arena. Deliberately no
  // default - a book that may never read the arena must not get one by
  // omission - so tests pass the flag explicitly.
```

`h/tron/models/kv_cache.hpp`:977-986 - delete these ten lines (the defaulted parameters, the delegating body, the blank and the 'Same, carrying ...' comment plus the duplicated `TRON(nodiscard)` / `static ... try_create(size_t n_pages,` header); lines 968-976 and 987-989 then read

```suggestion
  // Fallible KV-book factory for cache growth (STORY-127 /
  // memory_pressure_governor §8). ... log_kv_footprint fires exactly once, in
  // the adopt-constructor.
  TRON(nodiscard)
  static std::shared_ptr<book> try_create(size_t n_pages,
      size_t storage_slot_count,
      bool support_eagle,
      bool amx_mirror_eligible) noexcept {
```

`h/tron/models/kv_cache.hpp`:1352-1357 - the concept requires the 4-argument forms

```suggestion
    bool support_eagle,
    bool amx_mirror_eligible,
    kv_storage_offset offset) {
  requires std::constructible_from<T, size_t, size_t, bool, bool>;
  {
    T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible)
  } -> std::same_as<std::shared_ptr<T>>;
```

| site | now | with the flag explicit |
|---|---|---|
| `t/t_llama_unit.cpp:111` | `cache_t cache(/*n_pages=*/1);` | `cache_t cache(/*n_pages=*/1, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:257` | `book_t cache(1);` | `book_t cache(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:272` | `book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);` | `book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:338` | `book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);` | `book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:476` | `cache_t destination(/*n_pages=*/2); cache_t source(/*n_pages=*/2);` | `cache_t destination(/*n_pages=*/2, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); cache_t source(/*n_pages=*/2, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:960` | `cache_t destination(/*n_pages=*/1); cache_t source(/*n_pages=*/1);` | `cache_t destination(/*n_pages=*/1, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); cache_t source(/*n_pages=*/1, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1004` | `cache_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);` | `cache_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1027` | `cache_t destination(/*n_pages=*/3); cache_t source(/*n_pages=*/2);` | `cache_t destination(/*n_pages=*/3, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); cache_t source(/*n_pages=*/2, cache_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1076` | `cache_t destination(/*n_pages=*/2, storage_slots, /*support_eagle=*/true); cache_t source(/*n_pages=*/1, storage_slots, /*support_eagle=*/true);` | `cache_t destination(/*n_pages=*/2, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true); cache_t source(/*n_pages=*/1, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1152` | `CHECK(heterogeneous_cache::try_create(std::numeric_limits<size_t>::max()) == nullptr);` | `CHECK(heterogeneous_cache::try_create(std::numeric_limits<size_t>::max(), heterogeneous_cache::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1156` | `CHECK(heterogeneous_cache::try_create(2) == nullptr);` | `CHECK(heterogeneous_cache::try_create(2, heterogeneous_cache::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1163` | `2, storage_slots, /*support_eagle=*/true) == nullptr);` | `2, storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1221` | `book_t bk(1);` | `book_t bk(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1391` | `book_t bk(num_pages, n_layers);` | `book_t bk(num_pages, n_layers, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1614` | `CHECK(book_t::try_create(std::numeric_limits<size_t>::max()) == nullptr);` | `CHECK(book_t::try_create(std::numeric_limits<size_t>::max(), book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1619` | `auto bk = book_t::try_create(2);` | `auto bk = book_t::try_create(2, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1628` | `CHECK(book_t::try_create(2) == nullptr);` | `CHECK(book_t::try_create(2, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1632` | `CHECK(book_t::try_create(2) != nullptr);` | `CHECK(book_t::try_create(2, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true) != nullptr);` |
| `t/t_llama_unit.cpp:1642` | `CHECK(ebook_t::try_create(2, eagle_storage_slots, /*support_eagle=*/true) == nullptr);` | `CHECK(ebook_t::try_create(2, eagle_storage_slots, /*support_eagle=*/true, /*amx_mirror_eligible=*/true) == nullptr);` |
| `t/t_llama_unit.cpp:1676` | `book_t dst_book(1); book_t src_book(1); book_t expected_book(1);` | `book_t dst_book(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); book_t src_book(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); book_t expected_book(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1840` | `book_t dst_book(1); book_t src_book(1);` | `book_t dst_book(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true); book_t src_book(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_llama_unit.cpp:1946` | `book_t bk(1);` | `book_t bk(1, book_t::n_slots, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_amx_arena_leak.cpp:79` | `tron::book<2, 1, 128, 0> cache(/*n_pages=*/4);` | `tron::book<2, 1, 128, 0> cache(/*n_pages=*/4, /*storage_slot_count=*/2, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |
| `t/t_amx_arena_leak.cpp:127` | `// Control: the same book through the legacy constructor (eligible by // default) does allocate when AMX is available - so it is the flag, not // the geometry, that the arena decision follows.` | `// Control: the same book with amx_mirror_eligible=true does allocate when // AMX is available - so it is the flag, not the geometry, that the arena // decision follows.` |
| `t/t_amx_arena_leak.cpp:132` | `tron::book<2, 1, 64, 0> control(/*n_pages=*/4);` | `tron::book<2, 1, 64, 0> control(/*n_pages=*/4, /*storage_slot_count=*/2, /*support_eagle=*/false, /*amx_mirror_eligible=*/true);` |

_Fix note: Compiled, not run: the three header hunks plus all 31 call-site edits were applied to a scratch copy of the tree and syntax-checked (`clang++-19 -fsyntax-only`, the build's own flags from compile_commands.json, TRON_AMX_DISPATCH and TRON_AMX_K_MIRROR ON) for t/t_amx_arena_leak.cpp, t/t_llama_unit.cpp (all 29 sites) and a TU that instantiates `full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>` (covers `full.hpp:832`): 0 errors, 0 warnings. Negative check: the unpatched test against the patched header fails at :79 and :132 with 'no matching constructor', so the default is really gone. Not done: linking or running the tests; a `false` sweep over the mirror-irrelevant sites. Diffs and logs: exec/review-pipeline/r5/fix/ (kv_cache.diff, t_llama_unit.diff, t_amx_arena_leak.diff, syntax_*.log). `T::n_slots` is the static member the concept already relies on (kv_cache.hpp:725), so `book_t::n_slots` is the right spelling of the old default._

_Verification: round 2 (R2-03), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:771` R2-07 (A3)

```cpp
  771*   // The only constructor that carries the mirror-eligibility decision: the
  772    // scheduler passes amx_mirror_eligible(plugin::attention_kernels), so a
  773    // model without an AMX-eligible attention shape allocates no mirror arena.
  774    book(size_t n_pages,
  775        size_t storage_slot_count,
  776        bool support_eagle,
  777        [[maybe_unused]] bool amx_mirror_eligible) noexcept
```

"The only constructor that carries the mirror-eligibility decision" - the adopt-constructor at :1005 carries it too, and the scheduler's path is `try_create` (`full.hpp:832`) into that one; nothing in production reaches this constructor (its sole caller is `t_amx_arena_leak.cpp:123`).  Same for the "see the 4-argument constructor" pointer at :972.  Fix the comments, or the code.

_Verification: round 2 (R2-07), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:777` R2-04 (B4)

```cpp
  774    book(size_t n_pages,
  775        size_t storage_slot_count,
  776        bool support_eagle,
  777*       [[maybe_unused]] bool amx_mirror_eligible) noexcept
  778    : n_pages(n_pages)
```

`model.hpp` spells this `tron_maybe_unused` two lines from your other change; same here (and at :1005)?

_Verification: round 2 (R2-04), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1048` R3-03 (B7/A7)

```cpp
 1043    std::unique_ptr<uint8_t[], mirror_delete> mirror_arena_;
 1044    // The storage offset selected by set_storage_view(), or nullopt when no
 1045    // view is active. The mirror arena has no shifted base pointer of its own,
 1046    // so mirror() consults this to follow the view the way kv_block() follows
 1047    // kv_blocks_alias. See Note [K mirror coherence].
 1048*   std::optional<kv_storage_offset> mirror_view_offset_;
 1049  
```

So the view now lives in two members that must move together (`kv_blocks_alias` and `mirror_view_offset_`), set and cleared in two places, with no statement or assert that they agree.  The layout Note at :495 already describes the design for this: views "preselect their base pointer when the view changes".  A `mirror_alias` set next to `kv_blocks_alias` would make `mirror()` textually `kv_block()` on the other arena - no optional, no branch, one view to keep in sync.  Whichever stays, say here who writes it (the work_queue thread around `state.forward`, `full.hpp:1729-1740`) and who reads it (the RX and attention workers that forward dispatches), since that dispatch is what publishes a plain store to them - the same contract `kv_blocks_alias` has never written down either.

_Verification: round 3 (R3-03), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1055` R1-21 (A6/A3)

```cpp
 1050    void maybe_allocate_mirror_arena(size_t storage_slot_count,
 1051        bool support_eagle,
 1052        bool amx_mirror_eligible) noexcept {
 1053      // Ineligible model (no attention kernel with the AMX shape) or no usable
 1054      // AMX: no arena, and every consumer falls back on the null check.
 1055*     if (!amx_mirror_eligible || !amx_attn::available()) return;
 1056      size_t const bytes =
 1057          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1058              .kv_bytes /
 1059          2;
 1060      mirror_arena_.reset(static_cast<uint8_t*>(
 1061          ::operator new[](bytes, std::align_val_t(64), std::nothrow)));
 1062      // On failure the arena stays null and consumers fall back;
 1063      // see Note [K mirror parallel arena].
```

If `available()` is true and this `new` fails, we run a K_MIRROR build with no AMX QK at all (the canonical kernel is `#else`'d out in `apply_page_tok`) and nothing says so - silent bad performance instead of a loud error.  At least `spdlog::warn` once; better, keep `qk_canonical_128x4` as the fallback in the mirror build.  Also, `kv_bytes/2` of host RAM per book appears in neither `log_kv_footprint` nor `dma_size_bytes()`, and main's `Note [DMA-sized KV books]` (9076993a0) now says every buffer a book owns fits one DMA allocation - that Note needs the arena as an exception when you rebase.

_Verification: round 1 (R1-21), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1058` R1-22 (A5)

```cpp
 1055      if (!amx_mirror_eligible || !amx_attn::available()) return;
 1056      size_t const bytes =
 1057          allocation_sizes_or_assert(n_pages, storage_slot_count, support_eagle)
 1058*             .kv_bytes /
 1059          2;
 1060      mirror_arena_.reset(static_cast<uint8_t*>(
 1061          ::operator new[](bytes, std::align_val_t(64), std::nothrow)));
```

This `/ 2`, and the two in `mirror_at_storage`, are the `kv_block_planes` you just introduced, written as a literal.  Use it, or `static_assert(kv_block_planes == 2)` next to them, so the two can't drift.

_Verification: round 1 (R1-22), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1233` R1-23 (B4/A5)

```cpp
 1233*   bf16* mirror_at_storage(
 1234        kv_storage_offset offset, size_t kv_head, size_t pg) noexcept {
 1235      if (!mirror_arena_) return nullptr;
 1236      constexpr size_t plane_bytes = page_size * geometry.head_size * sizeof(bf16);
 1237      TRON_ASSERT_LT(pg, n_pages);
 1238      TRON_ASSERT_LT(kv_head, geometry.n_kv_heads);
 1239      size_t byte_base;
 1240      if (offset.i < logical_slot_count()) {
```

`kv_block_at_storage` asserts `slot_matches<geometry>` and the EAGLE offset; this copy of its `byte_base` branch asserts nothing, so a mismatched geometry silently computes `plane_bytes` for the wrong head size and can run off the end of the arena.  Factor one `storage_byte_base<geometry>(offset)` helper used by both, so the mirror inherits the asserts.  The eagle-offset assert arrived; `slot_matches<geometry>` on the logical branch did not, and the two `byte_base` branches are still a copy of each other.  The shared helper would give both.

_Verification: round 1 (R1-23), partial | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1513` R1-26 (A3)

```cpp
 1513*   // Raw pair-interleaved V storage of one (slot, kv_head) for this page,
 1514    // consumed as-is by the AMX PV kernel (TRON_AMX_DISPATCH).
 1515    template <kv_geometry geometry>
 1516      requires(book_t::template declares_geometry<geometry>())
 1517    TRON(nodiscard, inline, pure)
 1518    const bf16* v_data(kv_slot_id slot, size_t kv_head) const noexcept
 1519        TRON(this_lifetimebound)
 1520    {
 1521      return kv_block<geometry>(slot, kv_head).v_base();
 1522    }
```

This accessor (and `v_base()` at :2100) exists in every build, but the layout it describes exists only under `TRON_CHUNK_SIZE == 16`; the `#else` branch is plain `[p][i/C][i%C]`.  Guard the accessors the same way, or say so in the comment.

_Verification: round 1 (R1-26), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/kv_cache.hpp:1880` R1-27 (A7/B1)

```cpp
 1879  #ifdef TRON_AMX_K_MIRROR
 1880*       // Rebuild the mirror for the copied tokens from the destination's
 1881        // just-copied canonical K. This is THE defrag/page-move coherence
 1882        // site. See Note [K mirror coherence].
 1883        if (bf16* plane = book.template mirror_at_storage<geometry>(
 1884                storage_offset, kv_head, pageno())) {
 1885          for (size_t i = 0; i < count; ++i) {
 1886            detail::scatter_k_mirror<page_size, geometry.head_size>(
```

One sentence here on who runs this and why concurrent readers are safe (scheduler thread under `tree_lock`; only fresh tokens at or past `tok_ct`; the mirror's only reader needs all 64 tokens live).  The 16-tokens-per-line layout means these stores touch lines that also hold live tokens' columns, which is exactly what the next reader will worry about.

_Verification: round 1 (R1-27), not addressed | evidence: file unchanged since d176c88b3_

### h/tron/models/model.hpp

#### `h/tron/models/model.hpp:2764` R2-08 (A3)

```cpp
 2763  #ifdef TRON_AMX_K_MIRROR
 2764*       // Mirror writes exist only for the shape the AMX kernels serve
 2765        // (amx_attn::shape_ok, compile-time: ineligible geometries compile no
 2766        // scatter) and only when AMX is available and not runtime-disabled
 2767        // (TRON_AMX_DISABLE): otherwise the kernel that reads the mirror never
 2768        // runs. See Note [K mirror parallel arena].
 2769        constexpr bool k_mirror_shape_ok =
 2770            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 2771        const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();
```

"Mirror writes exist only for the shape the AMX kernels serve" is true of this write site, not of mirror writes: `copy_storage_slot` (`kv_cache.hpp:1857`) and `fill_storage_slot` (`:1286`) scatter for any geometry whose plane exists, and a head-64 book from the legacy constructor has one (your own control case).  Scope the sentence to "the `save_k` write-through is compiled out for ineligible geometries", which is what the `if constexpr` below does.

_Verification: round 2 (R2-08), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/model.hpp:2771` R1-28 (A1/A8/B7)

```cpp
 2769        constexpr bool k_mirror_shape_ok =
 2770            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 2771*       const bool k_mirror_on = k_mirror_shape_ok && amx_attn::available();
 2772  #endif
 2773        tron_maybe_unused const bool has_legacy_hardware_binding =
 2774            geometry == self_attn_t::legacy_geometry &&
 2775            operation_has_legacy_hardware_binding(operation);
```

This gates the write-through on `available()` only, but the only reader is behind `head_size == 128 && kv_mul == 4`.  On an AMX host running any other geometry (or any non-matching slot of a mixed layout) the RX worker pays the scatter (and `copy_storage_slot` the rebuild) and the book the `kv_bytes/2`, for planes nobody reads.  Gate the write, the rebuild, and the arena on the same predicate as the reader.  Also, `set_k_mirror` already no-ops on a null plane, so as written `k_mirror_on` is redundant with the arena condition rather than a correctness guard; the comment should say which it is.  And `model.hpp` calls `amx_attn::available()` without including its header.  Good on the gate.  Inside the `if constexpr`, `k_mirror_on` is just `available()`, and that is still redundant with the null check in `set_k_mirror`; say it is an early-out, or drop it.  Also, for an ineligible geometry `k_mirror_on` is now an unused local in a K_MIRROR build - `has_legacy_hardware_binding` two lines down needed `tron_maybe_unused` for exactly this shape; move the bool inside the `if constexpr`.  And `model.hpp` still doesn't include `amx_attn_iface.hpp` itself.

_Verification: round 1 (R1-28), not addressed | evidence: file unchanged since d176c88b3_

### h/tron/models/self_attention.hpp

#### `h/tron/models/self_attention.hpp:19` R1-29 (B15/B4)

```cpp
   12  #include <vector>
   13  
   14  #include "common/assert.hpp"
   15  #include "common/numerics/fp16.hpp"
   16  #include "common/util.hpp"
   17  #include "libpos.hpp"
   18  #include "spdlog/spdlog.h"
   19* #include "tron/kernels/amx_attn_iface.hpp"  // intrinsics-free; used when TRON_AMX_DISPATCH
   20  #include "tron/kernels/dotter.hpp"
```

`kv_cache.hpp` guards its include of `amx_attn_iface.hpp` under the flag; here both new headers are unconditional.  Pick one convention.  Also, `<cstdint>` is now used directly (`uint16_t`, `uint64_t`) and not included.  The include convention is now 'unconditional in both', fine.  `<cstdint>` is still not included here.

_Verification: round 1 (R1-29), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1361` R1-31 (A1/B7)

```cpp
 1361*       thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
```

Why lazy?  Packing all `items.size()` groups once before the page loop is at most `max_minibatch_size` 512-byte copies and deletes the bitmap and the per-(page, token) test-and-set.  If a cache is really wanted, `attn_accum` is already per worker, per token and 64B-aligned; a growable `thread_local std::vector` is neither aligned (see the header contract) nor bounded the way the mask next to it is.  Also, `resize()` here zero-fills the new tail every time `items.size()` grows past the previous call's, and the pack (`pack_q_group_128x4`, or `pack_q_rows_128x4` in the mirror build) then writes the same 4 KB again - and it is 4 KB out per group, not the 512 B I wrote above.  Fixed `alignas(64)` storage sized by `max_minibatch_size` would settle this, the alignment contract, and the bitmap in one move; if the vector stays, at least `if (amx_qpack.size() < n) amx_qpack.resize(n)`.

_Verification: round 1 (R1-31), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1361` **reply** to Codex comment 3858305367 (C2/A3)

```cpp
 1358        constexpr bool amx_shape_ok =
 1359            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 1360        const bool amx_on = amx_shape_ok && amx_attn::available();
 1361*       thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1369          amx_attn::begin_region();
```

> jeremyconner1975 (Codex): The kernel interface requires each packed-Q buffer to be 64-byte aligned, but `std::vector<uint16_t>` guarantees only `alignof(uint16_t)`. Since each slice is exactly 4096 bytes, every query inherits the base misalignment and TILELOADD can repeatedly straddle cache lines. Could this use a 64-byte-aligned allocator or aligned fixed storage?
> 
> - Codex review, submitted at Jeremy's request

Codex has a point about the alignment, and it's the same one as my question at `amx_attn_iface.hpp:102`: `amx_qpack` is a `std::vector<uint16_t>`, so every 4 KB slice inherits whatever `malloc` handed us (16 mod 64 in nearly every allocation when I tried it on glibc; 0 mod 64 only by accident).  The other two 64B contracts (`o` at :123, `s` at :163) are honored by `alignas(64)` storage at `self_attention.hpp:1568` and `:1652`; this is the only one that isn't.  Let's either give it `alignas(64)` storage or drop "64B-aligned" from the contract (:102 and :156); whether the split rows actually cost anything is a per-page timing with the pack at 0 vs 16 mod 64, not something to assert either way.

_Verification: new in round 5 (R5-03), a reply he would post in Codex thread 3858305367 (persona C2: answers bot findings); folds into R1-12 (round 1, same defect; its ':135' reference is :156 at HEAD). Finder 'codex' #1, refuter PARTIAL (histogram counts replaced by the qualitative statement). Verified by the orchestrator on this host (glibc): std::vector<uint16_t> resized to 4 KB..1 MB has data() % 64 = 48 (4 KB) or 16 (16 KB..1 MB), never 0; slices are 4096 B (Q_PACK_ELEMS_2048 * 2, iface:83-84) so every slice keeps the base residue; loads at amx_attn.cpp:137 (64 B stride) and :253 (256 B stride) read 16 rows x 64 B; the `o` and `s` contracts are met by alignas(64) at self_attention.hpp:1568-1569 and :1652. Codex threads have no replies (gh api, in_reply_to_id null on both)._

#### `h/tron/models/self_attention.hpp:1362` R1-32 (A5)

```cpp
 1362*       // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367        if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
```

The comment says `items.size() <= max_minibatch_size`; who enforces it?  (`batch_evenly` does, `model.hpp:326`, but it's a long way from here - a `TRON_ASSERT_LE(items.size(), max_minibatch_size)` next to the mask costs nothing.)

_Verification: round 1 (R1-32), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1367` R1-34 (B6/A12)

```cpp
 1367*       if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1369          amx_attn::begin_region();
 1370        }
 1371  #endif
```

We have `tron::finally` (`h/common/util.hpp:73`, used in `gof.hpp:221`) for exactly this bracket; `tron::finally release([&] { if (amx_on) amx_attn::end_region(); });` makes the pairing structural.  Not a bug today (the function is `noexcept` and there is no return in between), your choice.

_Verification: round 1 (R1-34), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1367` **reply** to Codex comment 3858305362 (C2/A1)

```cpp
 1358        constexpr bool amx_shape_ok =
 1359            amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
 1360        const bool amx_on = amx_shape_ok && amx_attn::available();
 1361        thread_local std::vector<uint16_t> amx_qpack;
 1362        // Bitmap with one bit per batch_job_ix, meaning "this token's Q group
 1363        // is already packed into amx_qpack": word batch_job_ix / 64, bit
 1364        // batch_job_ix % 64. Sized for the largest legal minibatch
 1365        // (items.size() <= max_minibatch_size).
 1366        uint64_t amx_packed_mask[(max_minibatch_size + 63) / 64] = {};
 1367*       if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1369          amx_attn::begin_region();
 1370        }
```

> jeremyconner1975 (Codex): `amx_on` only checks geometry and CPU support, so every eligible page range executes LDTILECFG/TILERELEASE and packs each query before the dense-page predicate is evaluated. Partial pages, masked/sliding-window pages, and null-mirror fallbacks therefore pay AMX setup plus a 4 KB pack even though every page uses AVX. Could we lazily begin the region and pack Q only when the first page actually satisfies the dense predicate?
> 
> - Codex review, submitted at Jeremy's request

Codex is right on the facts - `begin_region()` runs and each token's first visible in-window page pays a 1 KB-in / 4 KB-out pack (not the 512 B I wrote at :1361) before any page has passed the dense test, and PV only runs `if (did_amx)`, so a token whose range has no dense page uses its pack nowhere.  Two precisions: wholly masked or out-of-window pages skip at :1389/:1392 before the pack, and a null mirror with `amx_on` true means the arena allocation failed (`kv_cache.hpp:1055`, `:1060`).  I'd still go the other way from what Codex asks: the region pair is ~229 cycles against 686-1250 ns per dense page, so pack all `items.size()` groups up front and delete the bitmap.  If the calls with no dense page matter in the served shapes, count them per decode step first, before adding a second lazy mechanism inside `apply_page_tok`.

_Verification: new in round 5 (R5-04), a reply he would post in Codex thread 3858305362; folds into R1-31 (round 1, which asks for the opposite - eager packing). Finders 'codex' #2 and 'scope' #2 both verified Codex against HEAD; refuters PARTIAL (line refs, the unmeasured pack cost, the visibility skip) - corrections folded in. Verified by the orchestrator: amx_on = shape && available() (:1360); begin_region under if (amx_on) at :1367-1369 before the page loop, end_region :1468; skips at :1389 (visible) and :1392-1394 (window) precede the pack; pack block :1410-1438 (mask test :1419, pack_q_rows_128x4 :1424 / pack_q_group_128x4 :1429, mask set :1434) runs before apply_page_tok (:1440) tests the dense predicate (:1556-1558); PV under if (did_amx) (:1631); pack sizes amx_attn.cpp:108-120 (memset 4 KB + 512 elements) and :234-238 (memcpy 1 KB + memset 3 KB); ~229 cycles per pair is the figure the PR carries for the LDTILECFG/TILERELEASE pair (no in-tree record); null plane with amx_on true only via kv_cache.hpp:1060-1063 nothrow new failing, since the arena gate (:1055) is the OR of shape_ok over the plugin's kernels (:182-190)._

#### `h/tron/models/self_attention.hpp:1414` R1-33 (A13/B11)

```cpp
 1412                uint16_t* q_packed =
 1413                    amx_qpack.data() + batch_job_ix * amx_attn::Q_PACK_ELEMS_2048;
 1414*               // Pack lazily: select the token's mask word (batch_job_ix / 64
 1415                // via >> 6), shift its bit (batch_job_ix % 64 via & 63) down to
 1416                // bit 0, and test it. Bit clear = this token's Q group is not
 1417                // packed yet; pack it once and set the bit, so every later
 1418                // page in the range reuses the pack.
 1419                if (!((amx_packed_mask[batch_job_ix >> 6] >> (batch_job_ix & 63)) & 1)) {
```

The declaration comment already explains the word/bit split; this second explanation of `>> 6` and `& 63` is more than the two operators deserve.  Flush.

_Verification: round 1 (R1-33), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1493` R1-35 (A12/A9)

```cpp
 1490          const token_range* range_hint,
 1491          int sliding_window_size,
 1492          bool run_visible_in_software,
 1493*         const uint16_t* amx_q_packed = nullptr) {
 1494        constexpr size_t operation_kv_mul = geometry.kv_mul();
 1495        constexpr size_t operation_head_size = geometry.kv.head_size;
```

The default is never used (the one caller always passes `amx_qp`), and in a build without the flag the parameter is unreferenced - does the default build now warn under `-Wextra`?  CI didn't run, so I can't tell.  Drop the default, and I'd rather the OFF build's `apply_page_tok` were textually unchanged (parameter and `did_amx` under the flag).

_Verification: round 1 (R1-35), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1510` R1-36 (A8/A3)

```cpp
 1506        tensor<operation_kv_mul, page::page_size> s_pages;
 1507        int relevant_k_tokens = 0;
 1508        bool did_amx = false;
 1509        {
 1510*         // share the bf16 -> fp32 conversion across the page
 1511          using scalar_t = typename btensor_t<operation_head_size>::element;
 1512          for (size_t offset = 0; offset < operation_kv_mul; ++offset)
 1513            s_pages[offset] = constant<page::page_size>(-1.0f / 0.0f);
```

On the pages AMX takes, the four `dotter` constructions here (16 zmm loads) and the `-inf` init of `s_pages` are dead work per (page, token); moving them under `if (!did_amx)` is free.  Also, "share the bf16 -> fp32 conversion" describes `dotter<float, 128>`; the `dotter<bf16, 128>` used here converts nothing.  Pre-existing, but you're touching it.

_Verification: round 1 (R1-36), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1566` R1-37 (A4/A8)

```cpp
 1566*             if (const bf16* mplane =
 1567                      page.template k_mirror_data<geometry.kv>(slot, kv_head)) {
 1568                alignas(
 1569                    64) thread_local float qk_s[amx_attn::TILE_ROWS_16 * page::page_size];
 1570                amx_attn::qk_mirror_128x4(
 1571                    reinterpret_cast<const uint16_t*>(mplane), amx_q_packed, qk_s);
 1572                std::memcpy(&s_pages[0][0], qk_s,
 1573                    operation_kv_mul * page::page_size * sizeof(float));
 1574                relevant_k_tokens = page::page_size;
```

So the mirror path pays a 1 KB copy per page that the canonical path doesn't, and the `amxqk` bench variant behind the 686 ns figure stores straight into a 16-row `S` with no copy.  Either size `s_pages` for 16 rows in the mirror build, or note the copy's cost next to the 300 ns claim.  Also, when `mplane` is null in this build we fall all the way to the dotter although `qk_canonical_128x4` is compiled into the same binary - why not fall back to it?  The bench half is settled with the file.  The rest stands: `qk_mirror_128x4` still lands in `qk_s` and we `memcpy` 1 KB into `s_pages` per page, while the ~560 ns at `amx_attn_iface.hpp:137` (1250 vs 686) was measured on a path that never paid that copy - either size `s_pages` for 16 rows in the mirror build, or say so next to the number?

_Verification: round 1 (R1-37), not addressed | evidence: h/tron/models/self_attention.hpp:1566; h/tron/models/self_attention.hpp:1572; h/tron/models/self_attention.hpp:1573_

#### `h/tron/models/self_attention.hpp:1626` R1-38 (B11/B6)

```cpp
 1624        // The if-constexpr is runtime-redundant with did_amx (which is only
 1625        // ever set under the same condition, in the QK block above) but
 1626*       // deliberate: without it this 4-head/128-dim softmax-update block would still be
 1627        // COMPILED into every other geometry's instantiation as dead code,
 1628        // and its group-width assumptions would no longer be pinned to the
 1629        // same compile-time gate that guards the QK side.
 1630        if constexpr (amx_shape_ok) {
 1631          if (did_amx) {
```

This paragraph is justifying the code to the reviewer; "`if constexpr` so other geometries don't instantiate this block" is the whole content.  Flush the rest.  Also, pass 1 is a second copy of the per-head scale/softcap/max/exp/sum math below (I diffed them; identical today) - that is how they drift.  Pull the per-head part into a helper both loops call.

_Verification: round 1 (R1-38), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1659` R1-39 (A8)

```cpp
 1657            for (size_t offset = 0; offset < operation_kv_mul; ++offset) {
 1658              scratchpad_ref<geometry> head_sp = sp[kv_head * operation_kv_mul + offset];
 1659*             tensor<operation_head_size> scratch;
 1660              std::memcpy(&scratch[0], amx_o + offset * operation_head_size,
 1661                  operation_head_size * sizeof(float));
 1662              if (was_valid) {
 1663                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1664                head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
```

Any reason not to point a `const_view<float, true, false, seq<128>>` at `amx_o + offset * 128` instead of copying 512 B per head into `scratch`?  The AVX path feeds `fma` an expression for the same reason.

_Verification: round 1 (R1-39), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/models/self_attention.hpp:1664` R1-40 (A5)

```cpp
 1662              if (was_valid) {
 1663                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1664*               head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
 1665                head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
```

`constant<page::page_size>` (64 wide) as the multiplier in a 128-wide `fma` only works because `constant::chunk(i)` ignores `i`.  Pre-existing at :1685, but let's not copy it: `constant<operation_head_size>`.

_Verification: round 1 (R1-40), not addressed | evidence: file unchanged since d176c88b3_

### h/tron/scheduler/full.hpp

#### `h/tron/scheduler/full.hpp:310` R2-09 (A12/B4)

```cpp
  307    // Whether the model has an AMX-eligible attention shape (see
  308    // amx_mirror_eligible in kv_cache.hpp); handed to every KV book this tree
  309    // creates so ineligible models allocate no K mirror arena.
  310*   bool amx_mirror_eligible = true;
```

Every constructor sets this, so the `= true` is dead, and `true` is the unsafe direction for a default (see the constructor comment in `kv_cache.hpp`).  If the file's convention is to give these members a default, make it `false`.

_Verification: round 2 (R2-09), not addressed | evidence: file unchanged since d176c88b3_

#### `h/tron/scheduler/full.hpp:1456` R2-10 (B3)

```cpp
 1454        root = std::make_shared<node_t>(logical_kv_slots, storage_kv_slots,
 1455            cfg->support_eagle,
 1456*           amx_mirror_eligible(model_t::plugin_t::attention_kernels));
 1457      }
```

`amx_mirror_eligible` is now the name of the predicate over kernels, a `node_base` member, and two constructor parameters.  Inside `node` methods the member shadows the function.  `has_amx_attention_shape(kernels)` for the predicate would keep them apart.

_Verification: round 2 (R2-10), not addressed | evidence: file unchanged since d176c88b3_

### src/tron/CMakeLists.txt

#### `src/tron/CMakeLists.txt:170` R1-41 (A3)

```cmake
  166  # AMX software-attention dispatch. The kernel bodies live in one
  167  # isolated translation unit that alone receives the -mamx-* flags; the rest of
  168  # the tree sees only the intrinsics-free interface header plus the
  169  # TRON_AMX_DISPATCH definition that enables the fast-path call sites.
  170* option(TRON_AMX_DISPATCH "Enable AMX software-attention dispatch (Granite Rapids)" OFF)
```

AMX-BF16 is Sapphire Rapids and later, and the code gates on CPUID bits, not the model.  s/(Granite Rapids)/(requires AMX-BF16)/.

_Verification: round 1 (R1-41), not addressed | evidence: file unchanged since d176c88b3_

#### `src/tron/CMakeLists.txt:183` R1-42 (A1)

```cmake
  181  if(TRON_AMX_DISPATCH)
  182    target_sources(tron PRIVATE kernels/amx_attn.cpp)
  183*   set_source_files_properties(kernels/amx_attn.cpp PROPERTIES
  184      COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
  185    target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)
```

Only `-mamx-tile -mamx-bf16` are new for this TU; the `-mavx512*`/`-mavx2`/`-mfma` are already PUBLIC on `tron` (:234-237) unless `AVX512=OFF`, in which case this would be the only AVX-512 code in a non-AVX-512 binary.  Is that build meant to exist?  If not, trim the list; if so, say so.

_Verification: round 1 (R1-42), not addressed | evidence: file unchanged since d176c88b3_

### src/tron/kernels/amx_attn.cpp

#### `src/tron/kernels/amx_attn.cpp:3` **new** (B11)

```cpp
    1  // AMX software-attention kernels. See Note [AMX attention dispatch]
    2  // (in amx_attn_iface.hpp). The ONLY translation unit compiled with
    3* // -mamx-tile/-mamx-bf16. Kernel design and constants were validated with a
    4  // stand-alone whole-path benchmark (scores, softmax and PV of one page,
    5  // self-checked against a scalar reference), since removed from the tree
    6  // (git history up to d176c88b3).
```

This describes a benchmark that is no longer in the tree, and the PR description already says so.  The Note this points at already names `t_amx_numerics` as what pins the kernels; flush the sentence.

**Suggested fix** (added at your request)

Replace lines 1-6 with:

```suggestion
// AMX software-attention kernels. See Note [AMX attention dispatch]
// (in amx_attn_iface.hpp). The ONLY translation unit compiled with
// -mamx-tile/-mamx-bf16.
```

_Fix note: Drops the history sentence; the Note already points at t/t_amx_numerics.cpp (amx_attn_iface.hpp:46-47), and the bench's fate is in the PR description and the ff7269a9f commit message. Line 7 (blank) and the includes are untouched._

_Verification: new in round 5 (R5-02); found by finders 'numbers' and 'tests' independently, both refuters PARTIAL->confirmed with the wording used here. Verified: amx_attn.cpp:3-6 introduced by ff7269a9f (delta.diff @@ -1,8 +1,9 @@); pr_body.md:7 'is not in the tree (git history up to d176c88b3)'; amx_attn_iface.hpp:46-47 (Note [AMX attention dispatch]) already says 't/t_amx_numerics.cpp pins the kernels inside that envelope'; `git grep d176c88b3` at HEAD hits only this line. Persona B11 ('describing dinosaurs ... Flush it.'), 26 such comments in 2026; R1-15 applied the same rule on this PR._

#### `src/tron/kernels/amx_attn.cpp:8` R1-43 (B15)

```cpp
    8* #include <atomic>
    9  #include <cstdlib>
   10  #include <cstring>
   11  #include <immintrin.h>
   12  #include <unistd.h>
```

Unused?

_Verification: round 1 (R1-43), not addressed | evidence: src/tron/kernels/amx_attn.cpp:8; src/tron/kernels/amx_attn.cpp:90_

#### `src/tron/kernels/amx_attn.cpp:35` R1-45 (A13)

```cpp
   35* // One stored tile's worth of fp32 scores (16 rows x 16 values).
   36  // sizeof(float) rather than a literal 4: the constant converts tile bytes
   37  // into elements of the float arrays it indexes, so the element size belongs
   38  // to that type. C++ does not formally fix sizeof(float), but every tron
   39  // target does (the AVX-512 *_ps intrinsics and the fp32 tile accumulators
   40  // require IEEE 32-bit float); the static_assert pins the assumption.
   41  // (C++23 has std::float32_t, but tron's kernel convention is plain float
   42  // for fp32 throughout.)
   43  static_assert(sizeof(float) == 4, "AMX/AVX fp32 kernels assume 32-bit float");
   44  constexpr int TILE_FP32S = TILE_ROWS * TILE_ROW_BYTES / int(sizeof(float));
```

Eight lines of prose for `static_assert(sizeof(float) == 4)`.  I can smell Claude patting itself on the back a mile away.  The message string says everything the assert needs to say; flush the paragraph.

_Verification: round 1 (R1-45), not addressed | evidence: src/tron/kernels/amx_attn.cpp:35; src/tron/kernels/amx_attn.cpp:36; src/tron/kernels/amx_attn.cpp:42_

#### `src/tron/kernels/amx_attn.cpp:46` R1-46 (B3/B12)

```cpp
   45  // TDPBF16PS consumes the head dim in 32-dim steps (16 bf16 pairs per step).
   46* constexpr int DIM_STEP = 32;
   47  // Query heads per KV head - the GQA group width, the "x4" in the kernel names.
   48  constexpr int GROUP_HEADS = int(GROUP_HEADS_4);
```

`DIM_STEP` is documented as 32 head dims per k-step, but at :210 it means 32 tokens per PV k-step and at :211 it means 16 dims x 2 paired tokens per V tile column.  Three quantities with the same numeral shouldn't share a constant; name the other two.  Also, the `4` at :251 is `PAGE / TILE_ROWS`.

_Verification: round 1 (R1-46), not addressed | evidence: src/tron/kernels/amx_attn.cpp:45; src/tron/kernels/amx_attn.cpp:46; src/tron/kernels/amx_attn.cpp:213_

#### `src/tron/kernels/amx_attn.cpp:65` R1-47 (B6)

```cpp
   65* bool detect_and_request() noexcept {
   66    // Runtime kill switch for same-binary A/B tests and emergency disable.
   67    const char* off = std::getenv("TRON_AMX_DISABLE");
   68    if (off && off[0] == '1') return false;
   69    unsigned a, b, c, d;
   70    // CPUID leaf 7.0 EDX: bit 22 AMX-BF16, bit 24 AMX-TILE
   71    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(7), "c"(0));
   72    if (!((d >> 22) & 1) || !((d >> 24) & 1)) return false;
```

You know we have `cpuid_bit(leaf, reg, bit)` in `h/system/mwaitx.hpp:22`, and that `is_rtm_supported` (`lazy<bool>` + `TRON_NO_RTM=1`) is the same shape as this whole function, right?  Reuse it, or say why the AMX probe can't.

_Verification: round 1 (R1-47), not addressed | evidence: src/tron/kernels/amx_attn.cpp:65; src/tron/kernels/amx_attn.cpp:71; src/tron/kernels/amx_attn.cpp:90_

#### `src/tron/kernels/amx_attn.cpp:68` R1-48 (A6/B17)

```cpp
   65  bool detect_and_request() noexcept {
   66    // Runtime kill switch for same-binary A/B tests and emergency disable.
   67    const char* off = std::getenv("TRON_AMX_DISABLE");
   68*   if (off && off[0] == '1') return false;
   69    unsigned a, b, c, d;
```

This is a first-character test: `TRON_AMX_DISABLE=true` leaves AMX on, silently.  Nearest precedents are `strcmp(v, "1") == 0` (`TRON_NO_RTM`, `TRON_USE_ARENA_ALLOCATOR`) or `atoi(v) > 0` (`USE_HW_ATTN`); pick one.

_Verification: round 1 (R1-48), not addressed | evidence: src/tron/kernels/amx_attn.cpp:67; src/tron/kernels/amx_attn.cpp:68; src/system/memory.cpp:88_

#### `src/tron/kernels/amx_attn.cpp:109` R1-49 (A8)

```cpp
  108  void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept {
  109*   std::memset(packed, 0, Q_PACK_ELEMS_2048 * sizeof(uint16_t));
  110    // One panel per 32-dim step; see the layout contract at the declaration.
  111    for (int step = 0; step < HEAD_SIZE / DIM_STEP; step++) {
  112      for (int dim_pair = 0; dim_pair < DIM_STEP / 2; dim_pair++) {
  113        for (int q_head = 0; q_head < GROUP_HEADS; q_head++) {
```

Each pack memsets 4 KB to write 512 B; columns 4..15 never change.  The `P` buffer below zeroes its padding once per thread - same discipline here?

_Verification: round 1 (R1-49), not addressed | evidence: src/tron/kernels/amx_attn.cpp:108; src/tron/kernels/amx_attn.cpp:109; src/tron/kernels/amx_attn.cpp:198_

#### `src/tron/kernels/amx_attn.cpp:203` R1-50 (B1)

```cpp
  199    for (int q = 0; q < GROUP_HEADS; q++) {
  200      for (int c = 0; c < PAGE; c += 32) {
  201        __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
  202        __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
  203*       _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
  204      }
  205    }
```

A one-line comment that `cvtne2ps_pbh(a, b)` puts `b` in the low half would save the next reader the lookup.

_Verification: round 1 (R1-50), not addressed | evidence: src/tron/kernels/amx_attn.cpp:201; src/tron/kernels/amx_attn.cpp:202; src/tron/kernels/amx_attn.cpp:203_

### t/CMakeLists.txt

#### [blocker] `t/CMakeLists.txt:365` R1-58 (A4/A10/B14)

```cmake
  363  add_catch_test(NAME t_alloc_contention LIBRARIES tron pos_fake PROPERTIES LABELS fake DISABLED TRUE)
  364  add_catch_test(NAME t_llama_unit LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  365* add_catch_test(NAME t_amx_mirror LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  366  add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  367  add_catch_test(NAME t_amx_arena_leak LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```

In the default build all three of these are a single `SUCCEED("...skipped")`, and even with the options on they `WARN` and return on a non-AMX host - so after merge nothing in CI compiles or runs the flagged code.  How was this validated, given `make test` has no coverage for it?  At minimum a compile-only configuration with both options ON (precedent: `heterogeneous_scheduler_compile`, :351) so the `#ifdef`'d code can't rot silently; the run log from the 6962P host in the PR would also help.

**Suggested fix** (added at your request)

1. Add an OBJECT library next to `heterogeneous_scheduler_compile` (:356-359) that compiles the AMX code with both flags defined for that library alone, whatever the build's options are: one TU that instantiates the full scheduler for an eligible shape, plus the kernel TU with its `-mamx-*` flags. It is part of `all` like the precedent, so every CI build compiles the dispatch, the `save_k` write-through, the mirror arena and the kernels; no CTest entry.
2. That covers the 'can't rot silently' half. The other half of the comment stands: record in the PR how the three AMX tests were run on the 6962P host (the `ctest -R 't_amx_'` log from delphi-3bda with `-DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON`), since no CI host has AMX.

`t/CMakeLists.txt`:356-359 - keep the precedent block and add the AMX one after it

```suggestion
# Compile-time coverage for scheduler/cache capability boundaries. This target
# deliberately has no CTest entry: it instantiates templates but runs no model.
add_library(heterogeneous_scheduler_compile OBJECT heterogeneous_scheduler_compile.cpp)
target_link_libraries(heterogeneous_scheduler_compile PRIVATE tron full_scheduler)

# Compile-time coverage for the AMX software-attention paths (see
# Note [AMX attention dispatch]): both flags defined for this object library
# alone, so the #ifdef'd dispatch, save_k write-through, mirror arena and the
# kernel TU compile in every configuration, including the default with the
# options OFF. No CTest entry: it instantiates templates and runs no model.
add_library(amx_attention_compile OBJECT amx_attention_compile.cpp
  ../src/tron/kernels/amx_attn.cpp)
target_compile_definitions(amx_attention_compile PRIVATE TRON_AMX_DISPATCH TRON_AMX_K_MIRROR)
set_source_files_properties(../src/tron/kernels/amx_attn.cpp PROPERTIES
  COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
target_link_libraries(amx_attention_compile PRIVATE tron full_scheduler)
```

`t/amx_attention_compile.cpp` (new file) - new file

```cpp
// Compile-time coverage for the AMX software-attention paths (see
// Note [AMX attention dispatch] in tron/kernels/amx_attn_iface.hpp): this
// object library is built with TRON_AMX_DISPATCH and TRON_AMX_K_MIRROR defined
// whatever the build's options are, so the #ifdef'd dispatch, the save_k
// write-through and the mirror arena cannot rot in the default (OFF) build.
// Instantiates the full scheduler for one attention shape the kernels serve
// (llama-3.1-8b: 32 query heads / 8 KV heads / 128 dims). No CTest entry: it
// runs no model.
#include "tron/kernels/amx_attn_iface.hpp"
#include "tron/plugins/llama.hpp"
#include "tron/scheduler/full.hpp"

namespace tron {

static_assert(amx_attn::shape_ok(named_llama_configs::llama_3p1_8b.head_size,
    named_llama_configs::llama_3p1_8b.n_heads / named_llama_configs::llama_3p1_8b.n_kv_heads));
static_assert(amx_mirror_eligible(llama_3p1_8b<tp1>::plugin_model::attention_kernels));

template struct full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>;

}  // namespace tron
```

_Fix note: The TU was syntax-checked against the tree (`clang++-19 -fsyntax-only` with the flags heterogeneous_scheduler_compile.cpp is built with, i.e. -DTRON_AMX_DISPATCH -DTRON_AMX_K_MIRROR): 0 errors in 26 s, and both static_asserts hold (llama-3.1-8b is 32/8/128, ratio 4). The CMake hunk was NOT configured or built - no cmake run was made in your build directory; check it with `cmake --preset native && cmake --build gen --target amx_attention_compile` in a build with both options OFF. Assumptions to confirm at that step: `set_source_files_properties` here applies to the target defined in this directory (CMake 3.19 minimum, so `TARGET_DIRECTORY` is also available if preferred); with the options ON the kernel TU is compiled twice (once into `tron`, once here) - harmless for an object library nothing links; the duplicate -D flags are identical. `heterogeneous_scheduler_compile.cpp.o` is in `ninja -t targets all`, so the precedent (and this target) build in CI without a test entry. Source: exec/review-pipeline/r5/fix/amx_attention_compile.cpp, syntax_compile_tu.log._

_Verification: round 1 (R1-58), not addressed | evidence: file unchanged since d176c88b3_

### t/t_amx_arena_leak.cpp

#### `t/t_amx_arena_leak.cpp:48` R1-59 (A1)

```cpp
   46  // Global replacements of the aligned array forms. Allocation and
   47  // deallocation both route through aligned_alloc/free so every replaced form
   48* // stays pair-compatible with every other.
   49  void* operator new[](std::size_t n, std::align_val_t al) {
   50    void* p = counted_aligned_alloc(n, al);
   51    if (!p) throw std::bad_alloc{};
   52    return p;
   53  }
```

What failure is this guarding against?  `unique_ptr` with `mirror_delete` frees by construction, and a new[]/delete[] form mismatch is what the ASan build is for.  Replacing the global aligned `operator new[]` in a test binary is a lot of mechanism for that; if it stays, `memperf.cpp` already replaces the same forms.

_Verification: round 1 (R1-59), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_arena_leak.cpp:89` R2-11 (A3)

```cpp
   88    if (tron::amx_attn::available()) {
   89*     // The arena allocation actually ran (maybe_allocate_mirror_arena is
   90      // gated on available()), so the balance above covered it.
   91      REQUIRE(alloc_delta >= 1);
```

s/gated on available()/gated on the eligibility flag (true through the 3-argument form) and available()/.

_Verification: round 2 (R2-11), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_arena_leak.cpp:91` R1-60 (A10)

```cpp
   88    if (tron::amx_attn::available()) {
   89      // The arena allocation actually ran (maybe_allocate_mirror_arena is
   90      // gated on available()), so the balance above covered it.
   91*     REQUIRE(alloc_delta >= 1);
   92    } else {
   93      WARN("AMX unavailable on this host - the mirror arena never allocates, so "
   94           "only the trivial balance was checked");
   95    }
```

Can we tighten this to `== 1`?  With an example this small the count is predictable.  The new case does `== 1` (:133); this one still says `>= 1`.  Ditto.

_Verification: round 1 (R1-60), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_arena_leak.cpp:105` R2-12 (A3/B6)

```cpp
  103    // llama-3.3-70b (head 128, ratio 8) fails the ratio; qwen/llama-3.1
  104    // (ratio 4, head 128) pass.
  105*   static_assert(!tron::amx_attn::shape_ok(64, 8));
  106    static_assert(!tron::amx_attn::shape_ok(64, 4));
  107    static_assert(!tron::amx_attn::shape_ok(128, 8));
  108    static_assert(tron::amx_attn::shape_ok(128, 4));
```

These four evaluate `128 == 128 && 4 == 4` in four spellings; they can only fail if someone edits `shape_ok`.  If the point is that the registry shapes classify correctly, read them from `named_llama_configs::llama_3p2_1b` / `llama_3p1_8b` / `llama_3p1_70b` so the test follows the tree - and s/llama-3.3-70b/`llama_3p1_70b`/, which is the config that has this geometry.  gpt-oss and qwen-3-4b have no C++ geometry here, so say so or drop them.

_Verification: round 2 (R2-12), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_arena_leak.cpp:123` R2-13 (A10/B14)

```cpp
  118    // A head-64 book built the way the scheduler builds it for an ineligible
  119    // model: the 4-argument constructor with amx_mirror_eligible=false must
  120    // perform no arena allocation, whether or not this host has AMX.
  121    const long long before_ineligible = aligned_array_allocs.load();
  122    {
  123*     tron::book<2, 1, 64, 0> cache(/*n_pages=*/4, /*storage_slot_count=*/2,
  124          /*support_eagle=*/false, /*amx_mirror_eligible=*/false);
  125      REQUIRE(aligned_array_allocs.load() - before_ineligible == 0);
```

"built the way the scheduler builds it" - the scheduler goes through `try_create` (`full.hpp:832`) into the adopt-constructor, which this doesn't touch; this constructor's only caller is this test.  Can both arms run through `book_t::try_create(4, 2, false, false)` / `(4, 2, false, true)`, so the pair differs only in the flag and the plumbing we ship is what gets tested?  And a `static_assert(amx_mirror_eligible(llama<...>::attention_kernels))` on a real plugin array would test what the case name says.  Also, on a non-AMX host the `== 0` at :125 holds for either flag value, so the only discriminating half is the one we `WARN` past - where does this run with AMX?

_Verification: round 2 (R2-13), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_arena_leak.cpp:132` R2-14 (A10/A12)

```cpp
  127    // Control: the same book through the legacy constructor (eligible by
  128    // default) does allocate when AMX is available - so it is the flag, not
  129    // the geometry, that the arena decision follows.
  130    if (tron::amx_attn::available()) {
  131      const long long before_control = aligned_array_allocs.load();
  132*     tron::book<2, 1, 64, 0> control(/*n_pages=*/4);
  133      REQUIRE(aligned_array_allocs.load() - before_control == 1);
```

This control case is the argument against the legacy constructor: a head-64 book gets an arena no kernel can read, and the test enshrines it.  Once the 3-argument form is gone, the control becomes `book<...>(4, 2, false, true)` and says what it means.

_Verification: round 2 (R2-14), not addressed | evidence: file unchanged since d176c88b3_

### t/t_amx_logit_ab.cpp

#### `t/t_amx_logit_ab.cpp:6` R4-01 (B17/A3)

```cpp
    1  // AMX-vs-AVX A/B logit dump: run force_generate on a LONG synthetic token
    2  // sequence and dump every recorded step's logits to the file named by
    3  // AMX_LOGIT_OUT. This is a tool, not a test - it asserts nothing about AMX -
    4  // so its ctest entry is DISABLED (t/CMakeLists.txt) and nothing in CI runs it.
    5  // Run the binary by hand, twice, and compare the two dumps offline:
    6* //   AMX_LOGIT_OUT=/tmp/avx.bin TRON_AMX_DISABLE=1 gen/t_amx_logit_ab
    7  //   AMX_LOGIT_OUT=/tmp/amx.bin TRON_AMX_DISABLE=0 gen/t_amx_logit_ab
    8  // Optional: AMX_MODEL=<model id> (default ingested-llama-3.1-8b, so the
    9  // binary exists only with BUILD_INGEST_MODELS=ON) and AMX_TOKENS=<file> in
   10  // extract_logits --save-tokens format to align steps with an HF reference.
   11  // The long sequence matters: the AMX fast path engages only on full 64-token
   12  // pages, which the 21-token canned-prompt golden tests never reach.
```

Both commands run the AVX path on a default build - `TRON_AMX_DISPATCH` is OFF (`src/tron/CMakeLists.txt:170`) and the dispatch site is `#ifdef`'d (`self_attention.hpp:1352`) - so the two dumps agree for the wrong reason.  Let's start the recipe with the `-DTRON_AMX_DISPATCH=ON` configure (and `-DTRON_AMX_K_MIRROR=ON` for the mirror arm).

_Verification: round 4 (R4-01), not addressed | evidence: file unchanged since d176c88b3_

### t/t_amx_mirror.cpp

#### `t/t_amx_mirror.cpp:28` R1-61 (A11/B6/B8)

```cpp
   26  template <size_t page_size, size_t head_size>
   27  void require_mirror_matches(const uint16_t* flat_k, const uint16_t* plane) {
   28*   for (size_t s = 0; s < head_size / 32; ++s) {
   29      for (size_t c = 0; c < page_size / 16; ++c) {
   30        for (size_t dp = 0; dp < 16; ++dp) {
   31          for (size_t t = 0; t < 16; ++t) {
   32            for (size_t j = 0; j < 2; ++j) {
   33              const size_t mi = (((s * (page_size / 16) + c) * 16 + dp) * 16 + t) * 2 + j;
```

The reference here is the implementation's own index formula, so a layout change applied to both passes; the only test that ties the plane to its consumer (`qk_mirror_128x4`) is hardware-gated.  A scalar model of the kernel's panel addressing would pin the layout to the reader on any host.  Also, this is the fourth copy of the formula (Note, `scatter_k_mirror`, here, `t_llama_unit.cpp:440`); a `require_mirror_matches` in a `t/` header used by both tests would leave two.  Now six full copies plus two hand-expanded column forms (`t_llama_unit.cpp:370`, `:1128`, `:1135`, `:1140`), and two lambdas that are `require_mirror_matches` again.  `testutil.hpp` is already included there; a whole-plane and a one-token overload in it would serve `t_amx_mirror`, `:522`, `:360` and `:1118`.

_Verification: round 1 (R1-61), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_mirror.cpp:80` R1-62 (B18)

```cpp
   78  TEST_CASE("K mirror is byte-equivalent to canonical K", "[kv_data][amx_mirror]") {
   79    run_case<128>();  // qwen/llama head size (the AMX fast-path shape)
   80*   run_case<64>();   // smaller-head geometry
   81  }
```

Which consumer reads a head-64 plane?  Dispatch requires head 128, so this is 8192 `REQUIRE`s guarding data nobody reads - the same point as the write-through gate in `model.hpp`: don't maintain planes no kernel consumes, and this case goes away.  Still here.  Through the scheduler a head-64 book no longer has a plane at all, so this case now tests a layout only the legacy constructor can produce - one more reason to flush that constructor.

_Verification: round 1 (R1-62), not addressed | evidence: file unchanged since d176c88b3_

### t/t_amx_numerics.cpp

#### `t/t_amx_numerics.cpp:1` R1-63 (A11)

```cpp
    1* // Precision regression tests for the AMX attention kernels: the AMX QK and
    2  // PV outputs must not digress from the AVX path beyond the documented
    3  // numerics contract (see Note [AMX attention dispatch]): both engines are
    4  // bf16-in/fp32-accumulate, so admissible A/B deltas are ONLY
    5  //   (a) fp32 accumulation order, and
    6  //   (b) for PV, the weight rounding mode - AVX scaled_v truncates
    7  //       fp32->bf16, AMX rounds to nearest even.
    8  // Each check pins a kernel to the AVX side (the real dotter for QK, an
```

Nice - a real reference on both sides, in double.

_Verification: round 1 (R1-63), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_numerics.cpp:33` R1-65 (B3/B15)

```cpp
   31  // The kernel shape, from the interface header.
   32  constexpr size_t PAGE = tron::amx_attn::PAGE_TOKENS_64;
   33* constexpr size_t HD = tron::amx_attn::HEAD_SIZE_128;
   34  constexpr size_t NQ = tron::amx_attn::GROUP_HEADS_4;  // query heads per KV head
   35  constexpr size_t ROWS = tron::amx_attn::TILE_ROWS_16;
```

We renamed this `HEAD_SIZE` in the kernel TU; same here (and in the bench)?  Also `std::make_unique` without `<memory>`.  `HD` is now an alias of `HEAD_SIZE_128`; the alias could just be `head_size`.  And `NQ`/`ROWS` are a third spelling of `GROUP_HEADS`/`TILE_ROWS` - one vocabulary, please.  The bench still has its own `HD = 128`.  The bench's `HD = 128` went with the file, so that part is done.  Still: `HD`/`NQ`/`ROWS` at :33-35 remain a third spelling of the kernel TU's `HEAD_SIZE`/`GROUP_HEADS`/`TILE_ROWS`, and `std::make_unique` at :80 and :122 still has no `<memory>`.

_Verification: round 1 (R1-65), partial: t_amx_numerics.cpp is byte-identical between R4 and HEAD (`diff -q` silent). Settled this round: the bench's own `HD = 128` literal went with the deleted file (r4 item 2). Still open: (1) the test aliases are still `HD`/`NQ`/`ROWS` (:33-35) against the kernel TU's `HEAD_SIZE`/`GROUP_HEADS`/`TILE_ROWS` (amx_attn.cpp:29,:48,:33) - the third spelling remains; (3) `std::make_unique` at :80 and :122 with no `#include <memory>` (includes at :12-17 are cmath, cstddef, cstdint, cstring, random, vector; `grep -n memory` finds nothing). | evidence: t/t_amx_numerics.cpp:33; t/t_amx_numerics.cpp:34; t/t_amx_numerics.cpp:35_

#### `t/t_amx_numerics.cpp:108` R1-64 (A11/A13)

```cpp
  102          // of fp32 epsilon times the absolute-product mass.
  103          double abs_mass = 0;
  104          for (size_t d = 0; d < HD; ++d) {
  105            abs_mass += std::fabs(double(bf16_to_float(in->q[qi * HD + d])) *
  106                                  double(bf16_to_float(in->k[t * HD + d])));
  107          }
  108*         const double tol = 1e-4 * abs_mass + 1e-6;
  109          REQUIRE(std::fabs(double(s_amx[qi][t]) - double(s_avx)) <= tol);
```

The reorder bound for 128 exact products summed in fp32 is 127 ulp = 7.6e-6 of the mass, so 1e-4 is 13x looser than the math allows, and the comment calls it "a small multiple of fp32 epsilon" (it's ~1700).  Where does 1e-4 come from?  Tighten to a few times the bound, or state the measured maximum and why the margin.  Ditto :209.

_Verification: round 1 (R1-64), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_amx_numerics.cpp:147` R1-67 (A3)

```cpp
  145    // Both orientations reduce the head dim in the same 4x32 step order with
  146    // the same dim pairing, so TDPBF16PS produces the identical fp32 sums -
  147*   // the system-level regression check (mirror greedy output byte-identical
  148    // to canonical-AMX) rests on this. A failure here means the orientations'
  149    // accumulation orders diverged, which invalidates that equivalence.
  150    for (size_t qi = 0; qi < NQ; ++qi) {
  151      for (size_t t = 0; t < PAGE; ++t) {
  152        REQUIRE(s_mirror[qi * PAGE + t] == s_canon[qi][t]);
```

Where does that check live?  Nothing in the tree performs it (`t_amx_logit_ab` only dumps).  Name it or delete the sentence; the local assertion stands on its own.

_Verification: round 1 (R1-67), not addressed | evidence: file unchanged since d176c88b3_

### t/t_llama_unit.cpp

#### `t/t_llama_unit.cpp:309` R3-05 (5.2/A3)

```cpp
  307      WARN("mirror arena absent (AMX unavailable) - mirror view check not run");
  308    } else {
  309*     alignas(64) std::array<bf16, 128> row;
  310      row.fill(static_cast<bf16>(1.0f));
  311      page->template set_k_mirror<geometry>(slot, 0, 0, row.data());  // validator's row
  312      cache.set_storage_view(cache.eagle_storage_offset());
```

Every check in this block is implied by the coherence case below (:374-:380 read different values at the same index through the two views, which proves the planes are distinct memory).  Flush it - or, if the parallel with `page->k` above is worth keeping, say that these rows are markers and mirror == scatter(canonical) is deliberately not maintained here; dims 1..127 of canonical K are uninitialized at this point.

_Verification: round 3 (R3-05), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_llama_unit.cpp:346` R3-06 (A10/B14)

```cpp
  345    // Like save_k: store the canonical row, then write it through to the mirror.
  346*   auto save_k = [&](size_t i_page, float base) {
  347      auto k = page->k(slot, 0, i_page);
  348      for (size_t d = 0; d < geometry.head_size; ++d)
  349        k[d] = static_cast<bf16>(base + static_cast<float>(d));
  350      page->template set_k_mirror<geometry>(slot, 0, i_page, k.data);
  351    };
  352    for (size_t i = 0; i < book_t::page_size; ++i) {
  353      save_k(i, 1000.0f + static_cast<float>(i));  // validator: physical slot 0
  354      cache.set_storage_view(cache.eagle_storage_offset());
  355      save_k(i, 2000.0f + static_cast<float>(i));  // draft: physical slot L, same (p, j)
  356      cache.reset_storage_view();
  357    }
```

The lambda mimics `save_k_impl`, but nothing in `t/` calls the real one (`model.hpp:2793`) under the view, and the scenario I described ends in the parent's `qk_mirror_128x4` read.  Was an EAGLE (parent, child) run done with `TRON_AMX_K_MIRROR=ON` and its greedy output compared to the canonical build, the way the qwen A/B in the description was?  Record it in the PR.

_Verification: round 3 (R3-06), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_llama_unit.cpp:360` R3-07 (B6)

```cpp
  360*   auto require_plane_matches_canonical = [&] {
  361      const auto* mirror = reinterpret_cast<const uint16_t*>(
  362          page->template k_mirror_data<geometry>(slot, 0));
  363      for (size_t i = 0; i < book_t::page_size; ++i) {
  364        const auto* row = reinterpret_cast<const uint16_t*>(page->k(slot, 0, i).data);
  365        const size_t c = i / 16, t = i % 16;
  366        for (size_t s = 0; s < geometry.head_size / 32; ++s)
  367          for (size_t dp = 0; dp < 16; ++dp)
  368            for (size_t j = 0; j < 2; ++j)
  369              REQUIRE(
  370                  mirror[(((s * (book_t::page_size / 16) + c) * 16 + dp) * 16 + t) * 2 +
  371                         j] == row[s * 32 + 2 * dp + j]);
  372      }
```

Ditto (`t_amx_mirror.cpp:28`): this lambda and `require_mirror_column_matches` at :1118 are `require_mirror_matches` again, and the plane's K rows are contiguous, so the existing helper already covers the whole-plane case.

_Verification: round 3 (R3-07), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_llama_unit.cpp:512` R1-68 (B14/A10)

```cpp
  512* #ifdef TRON_AMX_K_MIRROR
  513    // After fill_random and append (the defrag rebuild path), the K mirror
  514    // plane must stay byte-equivalent to canonical K for every token;
  515    // see Note [K mirror coherence].
  516    // The plane lives in the book's parallel arena, which exists only when AMX
  517    // is available at runtime - skip (with a visible note) on non-AMX hosts.
  518    if (destination_page->template k_mirror_data<geometry_128>(kv_slot_id(1), 1) ==
  519        nullptr) {
```

IIUC only token 0 of this page came through `copy_storage_slot` (append copied 64 tokens into page 0 and one into page 1, and `destination` never advanced `tok_ct`); tokens 1..63 here were rebuilt by `fill_random`.  So the defrag rebuild is checked for `i == 0, dst_begin == 0` only - a dropped `dst_begin + i` or a wrong `dst + i * head_size` stride passes.  Check page 0 too, and do one append into a destination whose `tok_ct` is not a multiple of 64.  The new EAGLE append check covers the moved token in both views - good; this test still checks page 1 only.

_Verification: round 1 (R1-68), partial | evidence: file unchanged since d176c88b3_

#### `t/t_llama_unit.cpp:1133` R3-08 (B7)

```cpp
 1132        require_mirror_column_matches();  // validator's plane vs. physical slot 0
 1133*       REQUIRE(
 1134            float(page->template k_mirror_data<geometry_64>(kv_slot_id(0),
 1135                0)[((offset / 16) * 16 * 16 + (offset % 16)) * 2]) == source_token + 1);
 1136        destination.set_storage_view(destination.eagle_storage_offset());
 1137        require_mirror_column_matches();  // draft's plane vs. physical slot L
 1138        REQUIRE(
 1139            float(page->template k_mirror_data<geometry_64>(kv_slot_id(0),
 1140                0)[((offset / 16) * 16 * 16 + (offset % 16)) * 2]) == source_token + 11);
 1141        destination.reset_storage_view();
```

Both of these are implied by `require_mirror_column_matches()` together with :1099 and :1103 (its s = dp = j = 0 iteration is exactly this index, and `row[0]` is already required equal to `source_token + 1` / `+ 11`).  Flush them; if a literal-value check is wanted, take the index from the helper instead of expanding it by hand a third way.

_Verification: round 3 (R3-08), not addressed | evidence: file unchanged since d176c88b3_

#### `t/t_llama_unit.cpp:1347` R1-69 (B14/A10)

```cpp
 1346    constexpr size_t head_size = 128;
 1347*   constexpr size_t n_heads = 16;
 1348    constexpr size_t dim = head_size * n_heads;
 1349    constexpr size_t hidden_dim = 1024;
 1350    constexpr size_t n_layers = 2;
 1351    constexpr size_t n_kv_heads = 8;
 1352    constexpr size_t kv_mul = n_heads / n_kv_heads;
 1353    constexpr size_t n_q_tokens = 8;
```

I worked through the dense predicate and I believe it (token 0 is the binding window case; the `tok_hi` check on offset 63 covers the range).  But nothing in `t/` ever reaches it: this test uses `n_heads = 16`, `n_kv_heads = 8`, so `kv_mul == 2` and `amx_qp` is always null.  Can we have a `kv_mul == 4` case (n_heads 32 - the llama-3.1-8b shape) so the whole AMX QK + PV path is compared against `emulation::compute_attention`?  On non-AMX hosts it degrades to the AVX path and still passes.  Ideally with sub-cases for a mask range ending inside the page and the window edge (`sliding_window_size` 64 vs 65 for a query at position 127).

_Verification: round 1 (R1-69), not addressed | evidence: file unchanged since d176c88b3_

## 4. Checked and clean in the delta

| area | what was verified | source |
|---|---|---|
| 1250 / 686 / ~560 ns (Note :137-138) | fused-sweep-v2.txt:14 amx44 Nq=4 pages=1 per_page_ns=1249.9 and :30 amxqk Nq=4 pages=1 per_page_ns=686.0; 1249.9-686.0 = 563.9 -> '~560'; same ring and iteration count, so like-for-like as ff7269a9f claims; both variants report the same useful FLOP count (104.9 x 1249.9 = 131114 vs 191.1 x 686.0 = 131095), i.e. both are whole-path QK+softmax+PV; the round-4 982 figure is in no recorded file | exec/results/slot1/fused-sweep-v2.txt:1,14,30; d176c88b3:src/amx_fused_bench.cpp:24,538 |
| 'L2-resident page' and '6962P' | pages=1 ring = one K page (16 KB) + one V page (16 KB) + one mirror page, the bench's own label ('1 = L2-resident page', d176c88b3 bench :27-28); the sweep header names only 'cpu 96' - '6962P' is consistent with the PR body's host line and every other slot1 log from that day but is not in the record itself | d176c88b3:src/amx_fused_bench.cpp:27-28; pr_body.md; exec/results/slot1/perf-decode-logs/perf-layout-only.log:9 |
| Mirror-write cost not in the 686 | the bench excluded the K-mirror pack from its timed loop; in production that write is paid once per token row at save_k (model.hpp:2790-2795) and amortized over every later read of the page, so a per-page read-cost comparison is fair without a qualifier; the Q-pack asymmetry (R5-01) is different because it sat inside the timed loop of one variant only | d176c88b3:src/amx_fused_bench.cpp:279-280,599-606; h/tron/models/model.hpp:2790-2795 |
| Work region = one apply_page_range call | begin_region (self_attention.hpp:1369) and end_region (:1468) bracket one apply_page_range call; sole call site run_sections :1043, once per kv_section, for the ready and the pending plan; the '~229 cycles' per pair the PR quotes has no in-tree source | h/tron/models/self_attention.hpp:1038-1045,1345,1367-1370,1468 |
| amx_attn.cpp :156-158 and :240-241 comment rewrites | both now describe the code only (width-4 specialization; S[16 q][64 tok] = Q . K^T, no transposing store) and no longer point at the deleted file; loop and declaration match | src/tron/kernels/amx_attn.cpp:156-159,240-245 |
| No stale pointer to the deleted benchmark | git grep at 234c02bde for amx_fused_bench, fused_bench, fused-page benchmark, amxqk, amx44, amx62, t_amx_attention, fused-sweep: no hits; the only mention is the history sentence at amx_attn.cpp:3-6 (R5-02); 'git history up to d176c88b3' is accurate (blob present at d176c88b3, absent at ff7269a9f) and stays reachable if #3879 merges with a merge commit as main's history does | git grep; git cat-file -e d176c88b3:src/amx_fused_bench.cpp |
| Delta scope (A9) and title | the delta touches AMX-attention files only; no CI, dependency or neighbouring-code changes; the PR title matches the 14-file content; commit messages describe exactly their diffs (no commit-message comment warranted) | git log d176c88b3..234c02bde |
| Delta touches no test; R1-58 (blocker) unchanged | git diff d176c88b3 234c02bde -- t/ is empty; t/CMakeLists.txt:365-367 still register the three AMX tests with no compile-only target (precedent heterogeneous_scheduler_compile :356-359); default build SUCCEED('... nothing to test') at t_amx_numerics.cpp:229-231, t_amx_mirror.cpp:85-87, t_amx_arena_leak.cpp:141-143; no CI job passes -DTRON_AMX_DISPATCH (git grep -i amx over .github, CMakePresets.json, flake.nix, bin/ci, bin/slice: nothing) | t/CMakeLists.txt:356-367; .github/workflows/cmake-single-platform.yml:368; src/tron/CMakeLists.txt:170,177 |
| What validates the kernels now that the bench is gone | t_amx_numerics.cpp: qk_canonical_128x4 vs the production dotter with a double envelope (:89-109); weights_times_v_128x4 vs an exact double RNE reference and a truncation envelope (:195-224, non-vacuity check :224); qk_mirror_128x4 / pack_q_rows_128x4 / scatter_k_mirror only by bit-identity with the canonical kernel (:152, under TRON_AMX_K_MIRROR); the self_attention.hpp dispatch glue and the per-page softmax update have no direct test (open R1-69) | t/t_amx_numerics.cpp:75-225; t/t_amx_mirror.cpp:23-81 |
| PR body claims added since round 4 | 'registered DISABLED so no CI lane runs it': t/CMakeLists.txt:195 DISABLED TRUE inside BUILD_INGEST_MODELS, bin/slice:875-878 drops DISABLED entries, both CI lanes go through bin/slice; 'not in the tree (git history up to d176c88b3)': correct; '1250 vs 686 ns per L2-resident page at width 4': matches the sweep; the archive link for the design write-up is the author's decision, not a review item | pr_body.md:7-8; t/CMakeLists.txt:195; bin/slice:875-878 |
| CI history (fact used in the body) | draft PR, no labels; 17 runs on jhan-amx-p0 (2026-08-19 .. 2026-08-25T00:22Z), every 'CMake and CTest' run = ci-machinery-filter + lint only (build, test-host, test-fpga, test, benchmark all skipped; lint failed on the two 08-19 runs), every 'Benchmark Only PR' run skipped; the eight commits after bbb55ae5f (cc8a86bb3 .. 234c02bde) have 0 workflow runs and 0 check-runs (cause unverified). Build/test jobs are gated by `!draft \|\| contains(labels, 'Run CI')` | .github/workflows/cmake-single-platform.yml:5-6,23,173-176,619-623; gh run list / gh run view 32793335105 --json jobs; gh api commits/<sha>/check-runs |
| Codex arithmetic and the other 64B contracts | each packed-Q slice is exactly 4096 B (Q_PACK_ELEMS_2048 * 2, static_assert iface:84), so the slice residue mod 64 equals data()'s; the `o` (iface:123) and `s` (iface:163) contracts are met by alignas(64) storage at self_attention.hpp:1568-1569 and :1652 - the Q pack is the only violator | h/tron/kernels/amx_attn_iface.hpp:83-84,102,123,156,163; h/tron/models/self_attention.hpp:1413,1568-1569,1652 |
| Codex 'eager region/pack' - what is exactly true | region bracket eager under if (amx_on) (:1367-1369/:1468); pack once per (token, kv_head, call) via the per-call bitmap (:1366,:1419,:1434), not per page; wholly invisible (:1389) and wholly out-of-window (:1392-1394) pages skip before the pack; dense predicate :1556-1558; PV only if (did_amx) (:1631); a null mirror plane with amx_on true happens only when the nothrow arena allocation failed (kv_cache.hpp:1055,1060-1063); pack sizes 4 KB written (amx_attn.cpp:108-120, :234-238) - Codex's '4 KB' is right, R1-31's '512-byte copies' undercounts | h/tron/models/self_attention.hpp:1354-1370,1389-1394,1410-1440,1468,1550-1558,1631; src/tron/kernels/amx_attn.cpp:108-120,234-238; h/tron/models/kv_cache.hpp:1050-1063 |
| Blocker fixes: what the syntax checks covered | R2-03: patched kv_cache.hpp + t_amx_arena_leak.cpp (0 errors), + t_llama_unit.cpp with 29 edited sites (0 errors, 0 warnings), + a TU instantiating full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>> (covers full.hpp:832's 4-argument try_create; 0 errors); negative check: the unpatched test fails at :79 and :132 ('no matching constructor'). R1-58: the same TU is the proposed amx_attention_compile.cpp; its two static_asserts (shape_ok(128, 4); amx_mirror_eligible over llama-3.1-8b's attention_kernels) hold | exec/review-pipeline/r5/fix/syntax_arena.log, syntax_llama_unit.log, syntax_compile_tu.log, fixcheck.py |

## 5. Glossary

- **canonical-K** - Project shorthand: K kept in today's original single-copy row-major storage and read as-is by the AVX dotter, the FPGA DMA and the canonical AMX kernel.
- **mirror / k_vnni** - A second, derived copy of K in the pair-interleaved (VNNI) layout the AMX B operand wants. The mirror formulation originates from Bill's PR #2934 (k_vnni); the parallel-arena implementation and all numbers in PR #3879 are ours (jhan-amx-p0).
- **parallel arena** - Ordinary (non-DMA) RAM owned by the book, sized kv_bytes/2, one mirror plane per (storage slot, kv_head, page). Not the book's DMA arena_data.
- **shape gate / amx_attn::shape_ok** - head_size == 128 && kv_mul == 4 in one function, used by the dispatch, the save_k write-through and (via amx_mirror_eligible) the arena allocation.
- **amx_mirror_eligible** - (a) a constexpr function over a plugin's attention_kernels (true if any kernel passes the shape gate); (b) a bool carried on every node_base and passed to book::try_create; (c) a constructor parameter of book. The 3-argument book/try_create forms default it to true (blocker R2-03).
- **storage view / kv_blocks_alias** - book::set_storage_view() repoints kv_blocks_alias so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; since 96b5a6c72 the mirror accessors follow it through mirror_view_offset_.
- **EAGLE** - Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots.
- **ready / pending pass** - Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after upstream_kvs_ready.wait() over pages being written this forward (pending).
- **RX worker** - Per-card driver thread running DMA completion callbacks; rope_k/save_k execute there.
- **work region** - One begin_region()/end_region() bracket = one LDTILECFG/TILERELEASE pair, held for one apply_page_range call (~229 cycles measured for the pair).
- **whole-path benchmark / amx_fused_bench.cpp** - A stand-alone program (deleted in ff7269a9f, in history up to d176c88b3) that timed scores + softmax + PV of one 64-token page on hand-written copies of the kernels. Its recorded sweep (exec/results/slot1/fused-sweep-v2.txt in the campaign workspace, outside the tron tree) is the source of the 1250 / 686 ns figures.
- **Codex review** - An automated review posted on 2026-08-25 by jeremyconner1975 (“Review performed by Codex at Jeremy’s request”) with two inline comments on self_attention.hpp. Alexey answers bot findings rather than ignoring them (persona C2); his replies are in section 4 marked reply.
- **Run CI label** - Draft PRs skip the build/test jobs of cmake-single-platform.yml unless the PR carries the Run CI label at the next push (Note [Draft PR Filtering and Label Override]).
- **Note [Title]** - GHC-style named long comment, checked by make lint-notes.
- **A3, B6, ... tags** - Item numbers from ~/workspace/reviewers/alexey.md section 1; shown only in the verification line, never in the comment text.

## 6. Method and limits

- Target: PR head 234c02bde (checked out clean in ~/workspace/tron-amx, verified by the generator). Round 4 reviewed d176c88b3. Delta: ff7269a9f (deletes src/amx_fused_bench.cpp, rewrites the numbers in Note [Mirror orientation] and three amx_attn.cpp comments), 901f30d8e, a5ef65761 and 234c02bde; comments anchored in a file that is no longer in the PR are not carried or listed.
- Only comments anchored in the changed files, or whose text cites the deleted bench (R1-37, R1-65), could change status: re-anchored by 4 status verifiers (header, kernel TU, bench, and the removed file) and checked by 4 adversarial status refuters; every verdict was confirmed. The other carried comments keep their round-4 lines and text (files identical to d176c88b3).
- Finders: 4 independent agents over the delta only, each with one lens (comment/number accuracy; scope, CI and PR-description coverage; the two Codex findings; tests and validation), given the open comments as do-not-repeat. 11 candidates; one adversarial refuter per candidate (default refuted). All 11 survived as PARTIAL - substance confirmed, a line number or wording corrected - and the corrections are folded into the comment texts above. Three finders found the date error independently; two found the header sentence independently.
- Orchestrator's own checks, each recorded in the comment's verification line: the glibc alignment of std::vector<uint16_t> (a compiled program on this host: 48 mod 64 at 4 KB, 16 mod 64 at 16 KB..1 MB); the bench's per-run_pages pack_q in the d176c88b3 tree; the pack site's position relative to the dense predicate at HEAD; the Codex threads' reply count (0); the CI history (gh run list, gh run view --json jobs, per-commit check-runs: 0 for the eight commits after bbb55ae5f).
- Suggested fixes for the two blockers (added at your request): applied to a scratch copy and syntax-checked with the build's own compile commands (-fsyntax-only, clang++-19, both AMX options ON) - 31 call sites + 3 header hunks for R2-03, and the new compile-only TU for R1-58 - with a negative check that the removed default really is gone. Not built, not linked, not run; the CMake hunk was not configured. Diffs, the TU and the logs are in exec/review-pipeline/r5/fix/.
- Numbers the delta cites were checked against the recorded sweep exec/results/slot1/fused-sweep-v2.txt (outside the tron tree): 1249.9 / 686.0 at pages=1 (like-for-like), 1971.6 / 1470.2 at pages=512, 2294.0 / 1799.8 at pages=16384; header stamp 2026-08-18T18:34:53Z. The refuter's re-timing of pack_q (65-95 ns, est., on a non-6962P host) is context only and appears in no comment. '6962P' for the sweep rests on the PR body's host line; the sweep header names only 'cpu 96'.
- Written 2026-08-25. Voice from ~/workspace/reviewers/alexey.md; the persona's most common review is an empty approval, so nothing was added that his lenses would not raise. Suggested-fix blocks are added at your request and labelled as such; the 2026 Alexey describes fixes, he does not paste them.
