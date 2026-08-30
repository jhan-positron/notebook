# Review of PR #3879 as Alexey would write it - round 3

https://github.com/positron-ai/tron/pull/3879 - AMX software attention (default-off): QK/PV tile kernels + K-mirror arena  
Head `96b5a6c72` (round 2 reviewed `cc8a86bb3`; delta = two commits, 8e22b0aa5 "Export the AMX kernel shape as named constants; evaluate the gate once" + 96b5a6c72 "Make the K mirror follow the EAGLE storage view", 6 files, +208/-38); base `1407f48dd`; 16 files, +2735/-37. Written 2026-08-25. HTML twin: `alexey-review.html`; rounds 1-2 archived as `alexey-review-1.html` / `alexey-review-2.html`.

Lineage note: "mirror" names the formulation S = Q.K^T read from a second, VNNI-interleaved copy of K, which originates from Bill's PR #2934 (`k_vnni`); the parallel-arena implementation and all numbers in PR #3879 are ours (`jhan-amx-p0`). "canonical-K" = K in today's original single-copy storage, read as-is.

Each comment shows the source lines it refers to (new head; the anchored line is marked with `*`). The line starting `Verification:` is the evidence record for jhan, not part of the review.

## 1. Verdict

**CHANGES_REQUESTED**

The mirror now follows the view, with the assert and the interleaved test - good, that is the fix I had in mind.  The named constants settle the three-places question too.  What's left from my side: `t_amx_logit_ab` is still an `fpga`-labelled test that fails without `AMX_LOGIT_OUT` (that one alone blocks), the 3-argument `book`/`try_create` still default `amx_mirror_eligible` to allocate - and the new EAGLE coherence test is a third user of that form - the doc still says "8 models" and lists six, and the description now has the arena condition right but still says nothing about the doc, the `kv_block_planes` refactor, `v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the scheduler plumbing.  One new thing: constants named after their values (`HEAD_SIZE_128`) are literals with a longer name; see the header.  The rest is carried over unchanged below.

## 1a. What EAGLE is, and how likely it is to run together with the mirror

_Added on request (2026-08-25). Not part of his review; background for the EAGLE items in sections 2 and 3, written from the tree at `96b5a6c72`._

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

## 2. Resolved by 8e22b0aa5 + 96b5a6c72

| comment | where (new head) | what was asked | how it was addressed | his reply, if any |
|---|---|---|---|---|
| R1-11 (fixed) | `h/tron/kernels/amx_attn_iface.hpp:71` | Grepping suggests nobody reads `tile_row_bytes`, and `amx_attn.cpp` redefines both constants as `TILE_ROWS`/`TILE_ROW_BYTES` while including this header.  Use these there, or flush this one. | h/tron/kernels/amx_attn_iface.hpp:70-71 now: "inline constexpr size_t TILE_ROWS_16 = 16;\ninline constexpr size_t TILE_ROW_BYTES_64 = 64;" and src/tron/kernels/amx_attn.cpp:29-33 now derives its constants from the header instead of redefining them: "// Region tile shape: begin_region() configures all 8 tiles as 16 rows x\n// 64 bytes (amx_attn::TILE_ROWS_16 / TILE_ROW_BYTES_64 in the interface header).\nconstexpr int N_TILES = 8;\nconstexpr int TILE_ROWS = int(TILE_ROWS_16);\nconstexpr int TILE_ROW_BYTES = int(TILE_ROW_BYTES_64);" - TILE_ROW_BYTES_64 now has a reader (amx_attn.cpp:33). The .cpp keeps int-typed local aliases TILE_ROWS/TILE_ROW_BYTES, but they are derived from the header constants, not independent definitions. |  |
| R1-18 (fixed) | `h/tron/models/kv_cache.hpp:1265` | This indexes the arena by the logical slot and never looks at `kv_blocks_alias`, but `page::k` does.  So under `set_storage_view(eagle_storage_offset())` (`full.hpp:1717`) the draft's `save_k` stores canonical K in th... | h/tron/models/kv_cache.hpp:1265-1270 (new): "bf16* mirror(kv_slot_id slot, size_t kv_head, size_t pg) noexcept {\n  if (mirror_view_offset_) {\n    TRON_ASSERT_EQ(slot.i, 0);\n    return mirror_at_storage<geometry>(*mirror_view_offset_, kv_head, pg);\n  }\n  return mirror_at_storage<geometry>(kv_storage_offset(slot.i), kv_head, pg);". Member at :1048 "std::optional<kv_storage_offset> mirror_view_offset_;"; set at :843-845 in set_storage_view "#ifdef TRON_AMX_K_MIRROR\n    mirror_view_offset_ = offset;\n#endif" and cleared at :850-852 in reset_storage_view "mirror_view_offset_.reset();". Const overload :1274-1275 delegates to the non-const one. Note [K mirror coherence] :601-604 states the rule: "under the EAGLE storage view (set_storage_view) mirror() remaps logical slot 0 to the extra physical slot exactly as kv_block() does, so the draft's write-through can never land in the validator's slot-0 plane." Tests: t/t_llama_unit.cpp delta adds the mirror check to "EAGLE shifts storage without shifting logical KV completion" (REQUIRE(plane_view != plane_no_view); REQUIRE(float(plane_no_view[0]) == 1.0f); ... == 2.0f), a new TEST_CASE "K mirror stays coherent for both physical slots under the EAGLE view" with interleaved validator/draft save_k, and a mirror-column check in "heterogeneous EAGLE append preserves both views and embeddings". | Good - that is the fix I had in mind, and the `slot.i == 0` assert is the right call. |
| R1-30 (fixed) | `h/tron/models/self_attention.hpp:1358` | `head_size == 128 && kv_mul() == 4` is spelled here and twice more in `apply_page_tok` (1547, 1622) with bare `4`/`128`, and `amx_attn.cpp` has its own `HEAD_SIZE`/`GROUP_HEADS`.  Let's export the two constants (or a ... | Constants exported and the predicate evaluated once. h/tron/kernels/amx_attn_iface.hpp:76-78 `inline constexpr size_t PAGE_TOKENS_64 = 64; inline constexpr size_t HEAD_SIZE_128 = 128; inline constexpr size_t GROUP_HEADS_4 = 4;`, :91-92 `constexpr bool shape_ok(size_t model_head_size, size_t model_kv_mul) noexcept { return model_head_size == HEAD_SIZE_128 && model_kv_mul == GROUP_HEADS_4; }`. h/tron/models/self_attention.hpp:1499-1502 (apply_page_tok) `constexpr bool amx_shape_ok = amx_attn::shape_ok(operation_head_size, operation_kv_mul); static_assert(amx_attn::PAGE_TOKENS_64 == page::page_size, ...)`, used at :1555 `if constexpr (amx_shape_ok) {` and :1630 `if constexpr (amx_shape_ok) {` (old head had the shape_ok(...) call spelled at both sites). Kernel tie: src/tron/kernels/amx_attn.cpp:27-28 `constexpr int PAGE = int(PAGE_TOKENS_64); constexpr int HEAD_SIZE = int(HEAD_SIZE_128);`, :47 `constexpr int GROUP_HEADS = int(GROUP_HEADS_4);`. The caller-side line the comment sits on is unchanged: :1358-1359 `constexpr bool amx_shape_ok = amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());`. | Good. |
| R1-44 (fixed) | `src/tron/kernels/amx_attn.cpp:28` | Ditto: `TILE_ROWS`/`TILE_ROW_BYTES` duplicate `tile_rows`/`tile_row_bytes` from the header this file includes, and `PAGE` duplicates `page::page_size` with nothing tying them together. | src/tron/kernels/amx_attn.cpp:25-33 `// The kernel shape, from the interface header (int-typed for the offset arithmetic below). constexpr int PAGE = int(PAGE_TOKENS_64); constexpr int HEAD_SIZE = int(HEAD_SIZE_128); ... constexpr int TILE_ROWS = int(TILE_ROWS_16); constexpr int TILE_ROW_BYTES = int(TILE_ROW_BYTES_64);` and :47 `constexpr int GROUP_HEADS = int(GROUP_HEADS_4);` (old head: literal 64/128/16/64/4). PAGE is tied to the KV page size in h/tron/models/self_attention.hpp:1501-1502 `static_assert(amx_attn::PAGE_TOKENS_64 == page::page_size, "the AMX kernels assume the KV page size");`. |  |
| R1-66 (fixed) | `t/t_amx_numerics.cpp:85` | `q_pack_elems` exists for this. | head/t/t_amx_numerics.cpp:85 "    alignas(64) uint16_t q_packed[tron::amx_attn::Q_PACK_ELEMS_2048];" (was "alignas(64) uint16_t q_packed[4 * 16 * 32];"); same change at :125 "  alignas(64) uint16_t q_packed[tron::amx_attn::Q_PACK_ELEMS_2048];". The constant the reviewer named was renamed in the same commit: delta.diff "-inline constexpr size_t q_pack_elems = 4 * 16 * 32;" -> head/h/tron/kernels/amx_attn_iface.hpp:83-84 "inline constexpr size_t Q_PACK_ELEMS_2048 = TILE_ROWS_16 * HEAD_SIZE_128;\nstatic_assert(Q_PACK_ELEMS_2048 == 2048, \"the constant's name states its value\");". grep for lowercase q_pack_elems in the head tree: no hits. |  |

## 3. Open comments (82: 74 carried over from rounds 1-2, 8 new in round 3)

Carried-over comments keep their earlier text; where the commits addressed a comment in part, one follow-up sentence is appended. New comments are marked **new**. A leading `[blocker]` marks the comments the body names.

### doc/intel-amx.md

#### `doc/intel-amx.md:38` R1-05 (A3)

```markdown
   38* One `LDTILECFG`/`TILERELEASE` pair per work region (Intel guidance; ~229
   39  cycles measured between `begin_region()`/`end_region()`). 6962P also has AMX-INT8
   40  and AMX-FP16; tron's KV cache is bf16, so only `TDPBF16PS` is used.
```

It's once per `apply_page_range` call, i.e. per (worker, kv_head, page-range section) and again for the pending pass, not once per worker per layer.  Say that.  The frequency statement was removed instead of corrected, and "~229 cycles measured between `begin_region()`/`end_region()`" now reads as time elapsing inside the region; the number is the cost of the pair.  Say both.

**Suggested fix** (added at your request) - replace lines 38-40 with:

```suggestion
One `LDTILECFG`/`TILERELEASE` pair per work region, where a work region is one
`apply_page_range` call (per attention worker, kv_head and page-range section,
and again for the pending pass); the pair itself costs ~229 cycles measured
(`begin_region()`/`end_region()`). 6962P also has AMX-INT8 and AMX-FP16; tron's
KV cache is bf16, so only `TDPBF16PS` is used.
```

_Fix note: Frequency from self_attention.hpp: begin_region at :1367-1369 / end_region at :1468 inside apply_page_range, called per kv_section from run_sections for the ready and the pending plan. Line 50 ('~229 cycles per work region') then agrees with the definition._

_Verification: round 1 (R1-05), not addressed_

#### `doc/intel-amx.md:90` R1-06 (A3)

```markdown
   88  - 8 KB XTILEDATA per thread in the XSAVE area once used; `TILERELEASE` when
   89    leaving a region re-enables the XSAVE init optimization.
   90* - One AMX thread per physical core (Intel guidance); tron already pins one
   91    attention worker per CPU from an explicit core list.
   92  - Toolchain: `-mamx-tile -mamx-bf16` confined to one translation unit
   93    (`src/tron/kernels/amx_attn.cpp`); the interface header is intrinsics-free.
```

`with_app_pin_thread` pins to a logical CPU taken from a list; nothing keeps SMT siblings out of that list.  s/tron already pins one attention worker per CPU/this holds if the configured core list excludes SMT siblings/.

**Suggested fix** (added at your request) - replace lines 90-91 with:

```suggestion
- One AMX thread per physical core (Intel guidance). tron pins one attention
  worker per logical CPU from an explicit core list, so this holds only when the
  configured list contains no two SMT siblings of one physical core; tron does
  not check that.
```

_Fix note: Your triage: IGNORE. The fix states the condition instead of implying enforcement; if the measured hosts ran with sibling-free lists, add that as the second sentence._

_Verification: round 1 (R1-06), not addressed_

#### `doc/intel-amx.md:100` R1-03 (A3)

```markdown
   99  Software attention - the `apply_page_tok` QK and PV inner loops. The main
  100* target is forced software attention (`USE_HW_ATTN=0`), where attention
  101  compute is the decode wall at long context (a measurement based estimation
  102  put attention at ~64% of the decode step on the primary model at ctx 8192).
  103  The FPGA-attention flow benefits too, with no additional code: the dispatch
  104  sits inside the software page loop, which hardware mode still uses for its
  105  software-required subset (positions below 127, sliding-window and software-only
  106  layers, hw-ineligible configurations). The dispatch has no `uses_hw` check.
  107  See `Note [AMX attention dispatch]`.
```

Archived where?  A number a reader cannot check should get a pointer or go.  This went the other way: the qualifier that it was a fit and not a trace is gone, and there is still nothing a reader can follow.  Cite where the estimate lives (result file, doc, PR) or drop the number.

**Suggested fix** (added at your request) - replace lines 100-102 with:

```suggestion
target is forced software attention (`USE_HW_ATTN=0`), where attention
compute is the decode wall at long context (a linear fit of the pre-AMX decode
step time against context length - 3.43 ms + 0.734 us x tokens, qwen-3-4b tp2
on delphi-3bda, 2026-08-18 - attributes 6.0 of 9.4 ms per step at ctx 8192 to
the context-proportional term, i.e. ~64%; a fit, not a trace of that cell).
```

_Fix note: The fit constants are your P0 baseline of 2026-08-18 (exec/results/, ms/tok = 3.43 + 0.734 us x ctx; 0.734 us x 8192 = 6.01 ms of 9.44 ms = 63.7%). Confirm them against the result file before committing. His alternative ('or go'): end the sentence at 'long context.' and drop the number._

_Verification: round 1 (R1-03), not addressed_

#### `doc/intel-amx.md:118` R1-04 (A3/A4)

```markdown
  118* Primary: `ingested-qwen-3-4b-instruct-2507-tp2`. All comparisons are
  119  same-binary kill-switch A/Bs against the true clean binary. Decode
  120  (replicated, 8 reps/cell, 95% CI): +15.3..+17.7% (canonical) /
  121  +19.7..+27.8% (mirror) at 1u/8K..8u/8K. Prefill (3-rep suite): up to +105%.
  122  Energy per token (separate power capture at 8u/8K): -14.5% / -21.6%.
  123  Generalization: llama-3.1-8b decode +15.0% (1u/8K) / +19.7% (8u/2K);
  124  mixtral-8x7b +9.4% canonical / +18.6% mirror (8u/8K); gpt-oss (ineligible
  125  geometry) -0.3..-1.6% = no regression when the gate does not fire.
```

These are 0.1-0.3 points off the table in the PR description (15.3 vs 15.2, 27.8 vs 28.1, 15.0 vs 14.9, 18.6 vs 18.5).  Presumably different campaigns; say so in both places, or use one table.

**Suggested fix** (added at your request) - replace lines 119-125 with:

```suggestion
same-binary kill-switch A/Bs against the true clean binary. Decode
(replicated campaign, 8 reps/cell, 95% CI; the table in the PR description is
the earlier 3-rep suite and differs from these cells by at most 0.3 points):
+15.3..+17.7% (canonical) / +19.7..+27.8% (mirror) at 1u/8K..8u/8K. Prefill
(3-rep suite): up to +105%. Energy per token (separate power capture at
8u/8K): -14.5% / -21.6%. Generalization (the runs cited in the PR description,
`exec/results/t4/t4-shapes.txt` and `exec/results/ci-models/mixtral-ab.txt`):
llama-3.1-8b decode +14.9% (1u/8K) / +19.7% (8u/2K); mixtral-8x7b +9.4%
canonical / +18.5% mirror (8u/8K); gpt-oss (ineligible geometry) within noise
= no regression when the gate does not fire.
```

_Fix note: Your triage: IGNORE. Two-part fix: label the primary table as the replicated campaign and say how far the PR table is from it (max |delta| = 0.3 points: 28.1 vs 27.8); make the Generalization line quote the same runs the PR description cites (llama +14.9%, mixtral +18.5%, gpt-oss 'within noise'), so both texts agree. Confirm the PR table's rep count (3) against exec/results/t4/._

_Verification: round 1 (R1-04), not addressed_

#### `doc/intel-amx.md:145` R2-02 (A3)

```markdown
  144  canonical path) and cost 33% KV page capacity. The arena is ordinary RAM
  145* (`kv_bytes/2`), allocated only when AMX is available at runtime, fail-soft
  146  to null; page capacity is identical with and without it. Coherence
  147  (`Note [K mirror coherence]`): the mirror is a pure derived view with
```

This sentence didn't follow the gate: the arena now also requires an eligible attention shape.  Ditto the same sentence in the PR description.  The PR description now says it; this sentence still doesn't.

**Suggested fix** (added at your request) - replace lines 144-146 with:

```suggestion
canonical path) and cost 33% KV page capacity. The arena is ordinary RAM
(`kv_bytes/2`), allocated only for a model with an AMX-eligible attention shape
(`amx_mirror_eligible` over the plugin's attention kernels - the same
`amx_attn::shape_ok` gate as the dispatch) on a host where AMX is available at
runtime, fail-soft to null; page capacity is identical with and without it.
```

_Fix note: Mirrors the condition in kv_cache.hpp maybe_allocate_mirror_arena (`if (!amx_mirror_eligible || !amx_attn::available()) return;`) and the wording the PR description already uses._

_Verification: round 2 (R2-02), not addressed_

#### `doc/intel-amx.md:167` R1-07 (A3/B6)

```markdown
  167* The fast path engages only for one attention shape. The whole gate is one
  168  line of compile-time arithmetic plus the runtime check
  169  (`h/tron/models/self_attention.hpp`):
  170  
  171  ```c++
  172  constexpr bool amx_shape_ok =
  173      geometry.kv.head_size == 128 && geometry.kv_mul() == 4;
  174  const bool amx_on = amx_shape_ok && amx_attn::available();
  175  ```
```

The gate is spelled three times in `self_attention.hpp` (1358, 1547, 1622), two of them with bare `4`/`128`.  See my comment there; then this sentence can become true.  The code block below (:171-175) still shows the old literal, and the prose still says "one line"; the gate is `amx_attn::shape_ok(...)` now.  Update the block.

**Suggested fix** (added at your request) - replace lines 167-175 with:

````suggestion
The fast path engages only for one attention shape. The gate is one function,
`amx_attn::shape_ok` (`h/tron/kernels/amx_attn_iface.hpp`), evaluated at
compile time wherever the shape matters - the dispatch and both fast-path
blocks in `h/tron/models/self_attention.hpp`, the `save_k` write-through in
`h/tron/models/model.hpp`, and (through `amx_mirror_eligible`) the mirror-arena
allocation - plus the runtime check:

```c++
constexpr bool amx_shape_ok =
    amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());
const bool amx_on = amx_shape_ok && amx_attn::available();
```
````

_Fix note: The code block is now the exact text of self_attention.hpp:1358-1360 at 96b5a6c72. The Markdown suggestion uses a four-backtick fence because the replacement itself contains a fence._

_Verification: round 1 (R1-07), partial: The doc code block (doc/intel-amx.md:171-175) still shows the old literal `== 128 && ... == 4` instead of `amx_attn::shape_ok(...)`, and the prose at :167-168 still says "one line". The gate is now spelled twice in self_attention.hpp (:1358 and :1499), both via shape_ok._

#### [blocker] `doc/intel-amx.md:182` R2-01 (A3)

```markdown
  182* The following 8 models match the gate: qwen-3-4b-2507, llama-3-8b, llama-3.1-8b,
  183  mistral-7b, ministral-8b, mixtral-8x7b. Three are measured (qwen,
  184  llama-3.1-8b, mixtral). Every other family runs the unchanged AVX path. In
```

Six names, and the sentence says 8.  Fix either the number or the list - and were phi-4 and granite-3.3-8b dropped on purpose?  The other half of my earlier question stands too: record how the list was produced, or it will go stale.

**Suggested fix** (added at your request) - replace lines 182-184 with:

```suggestion
Eight registry families match the gate: six with hand-written C++ geometry in
`h/tron/plugins/llama.hpp` (llama-3-8b, llama-3.1-8b, mistral-7b, ministral-8b,
mixtral-8x7b, phi-4 - 40Q/10KV, the ratio is what the gate reads) and two
ingested families (qwen-3-4b-2507; granite-3.3-8b, plugin not end-to-end yet).
The list is `amx_attn::shape_ok(head_size, n_heads / n_kv_heads)` applied to
the `TRON_LLAMA_CONFIG` rows and to the ingested families' HF configs, as of
2026-08-25; re-derive it when the registry changes. Three are measured (qwen,
llama-3.1-8b, mixtral). Every other family runs the unchanged AVX path. In
```

_Fix note: Count check from the tree: llama.hpp TRON_LLAMA_CONFIG rows with head 128 and ratio 4 = llama_3_8b, llama_3p1_8b, mistral_7b, ministral_8b, mixtral_8x7b, phi_4 (six); qwen-3-4b (32/8/128) and granite-3.3-8b (32/8/128) are ingested, geometry from HF configs, not in the tree. The replacement ends with 'In' so the following sentence at line 185 still reads._

_Verification: round 2 (R2-01), not addressed_

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

_Verification: round 1 (R1-10), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:75` **new** (A3)

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

_Verification: N1-2 + N2-2 (high): amx_attn.cpp :45, :113, :158, :199, :213-229, :250-265 unchanged by 8e22b0aa5._

#### `h/tron/kernels/amx_attn_iface.hpp:77` **new** (B3)

```cpp
   72  // The one attention shape these kernels serve - the tile identity of
   73  // Note [AMX attention dispatch]: a 64-token KV page, 128-dim heads, and 4
   74  // query heads per KV head (4 x 128 bf16 = one full tile operand). Every
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

_Verification: N1: 179 constexpr definitions in h/tron/{models,kernels,scheduler}: 172 lower_snake, 1 UPPER_CASE (function-local), 0 with a value suffix; across all of h/ no constant embeds its value. AGENTS.md:38 asks to match the local module's naming._

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

_Verification: round 2 (R2-06), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:96` R1-16 (A3)

```cpp
   95  // True when the CPU, the OS, and the per-process permission all allow AMX,
   96* // and TRON_AMX_DISABLE is not set. See Note [AMX attention dispatch].
   97  bool available() noexcept;
```

s/is not set/is not `1`/ - the A/B recipe in `t_amx_logit_ab.cpp` explicitly uses `=0`.

_Verification: round 1 (R1-16), not addressed_

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

_Verification: round 1 (R1-12), not addressed_

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

_Verification: round 1 (R1-13), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:138` R1-14 (A3/A4)

```cpp
  135  // Two QK formulations exist. The canonical-K kernel computes S^T = K . Q^T
  136  // (K consumed exactly as stored) and must then round-trip the score tile
  137  // through memory and transpose it - a ~300 ns/page whole-path cost at
  138* // width 4 (982 vs 686 ns, measured with the fused-page benchmark,
  139  // src/amx_fused_bench.cpp; transpose work + score traffic combined, not
  140  // isolated). NOT a store-forwarding stall: 64-byte
  141  // tile-store -> vector-load forwarding is supported (opt manual 20.15) and
  142  // a 6962P microbench measured no stall on that path; the hard restriction
  143  // is the opposite direction, any store -> TILELOADD cannot forward.
```

There is no store-forwarding microbench in the tree, and the 982/686 figures come from `amx_fused_bench.cpp` with unrecorded arguments.  Numbers we can't reproduce shouldn't be stated as facts in a Note.  Keep them in the doc with the command that produced them, and reference that from here.

_Verification: round 1 (R1-14), not addressed_

#### `h/tron/kernels/amx_attn_iface.hpp:150` R1-15 (B11)

```cpp
  149  // there too). Both ship:
  150* // canonical-K is the supported default; the mirror is opt-in
  151  // (TRON_AMX_K_MIRROR) for pinned AMX deployments. Precedent: the mirror
  152  // formulation is PR #2934's k_vnni idea; this arena implementation is ours.
```

Keep the pointer to #2934 if it helps a reader find the other formulation; flush "this arena implementation is ours".  Attribution goes in the PR description.  Also, what's a "pinned AMX deployment"?  Say the concrete condition (builds that will only run on AMX hosts, since the arena RAM is wasted otherwise).

_Verification: round 1 (R1-15), not addressed_

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

Is this instrumentation still needed?  Its conclusion (width 4 is the guaranteed decode width) is already baked into the kernel shape, nothing in CMake defines `TRON_PAGE_SHARE_COUNTERS`, and it adds a third flag family plus an exit-time printer under `kernels/` for something that instruments `models/`.  I'd record the histogram in `doc/intel-amx.md` and drop the code; if we want a live counter, the `TRACE_EVENT` args two lines above the page loop are the existing place.  Also, the guard is `#ifdef`, so `=0` enables it too; and with the flag on there is an increment per (page, token) inside the loop, so "Zero hot-loop cost" isn't what the code does.

_Verification: round 1 (R1-17), not addressed_

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

_Verification: round 2 (R2-05), not addressed_

#### `h/tron/models/kv_cache.hpp:539` R1-25 (B7)

```cpp
  539* #if defined(TRON_AMX_K_MIRROR) && !defined(TRON_AMX_DISPATCH)
  540  #error "TRON_AMX_K_MIRROR requires TRON_AMX_DISPATCH"
  541  #endif
```

CMake already refuses this combination (`src/tron/CMakeLists.txt:178`).  If the `#error` is for non-CMake builds, say so; otherwise one check is enough.

_Verification: round 1 (R1-25), not addressed_

#### `h/tron/models/kv_cache.hpp:586` R1-24 (A9)

```cpp
  584  // pair-interleaved layout natively, so V needs no second copy. Reopen only
  585  // if a card consumes VNNI K natively or an FPGA-free build ships.
  586* inline constexpr size_t kv_block_planes = 2;
  587  #ifdef TRON_AMX_K_MIRROR
  588  // Note [K mirror coherence]
```

Is `kv_block_planes` ever anything but 2?  If it's a leftover of the in-block third-plane design, the rename of the pre-existing `2 *` literals (here, :1138, `t_llama_unit.cpp:415`) is an unrelated refactor - its own small PR, or drop it.

_Verification: round 1 (R1-24), not addressed_

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

_Verification: round 1 (R1-19), not addressed_

#### `h/tron/models/kv_cache.hpp:602` **new** (A3)

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

_Verification: N1-4 (low): copy_from hands copy_storage_slot the physical offsets (:1913-1925). The 'can never land in the validator's plane' clause holds._

#### `h/tron/models/kv_cache.hpp:607` R1-20 (A3)

```cpp
  605  // (fill_random additionally rebuilds, for tests only.) Verified byte-exactly
  606  // by t/t_amx_mirror.cpp (exhaustive index map, scrambled write order) and
  607* // the mirror checks in t/t_llama_unit.cpp (append + defrag, and the EAGLE
  608  // storage-view cases).
```

There is no separate defrag operation; `append` is the defrag path and the test calls it once.  s/(append + defrag)/(`book::append`, the defrag path)/.  This sentence was edited in 96b5a6c72 and kept "(append + defrag)".

_Verification: round 1 (R1-20), not addressed_

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

_Verification: round 2 (R2-03), not addressed_

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

_Verification: round 2 (R2-07), not addressed_

#### `h/tron/models/kv_cache.hpp:777` R2-04 (B4)

```cpp
  774    book(size_t n_pages,
  775        size_t storage_slot_count,
  776        bool support_eagle,
  777*       [[maybe_unused]] bool amx_mirror_eligible) noexcept
  778    : n_pages(n_pages)
```

`model.hpp` spells this `tron_maybe_unused` two lines from your other change; same here (and at :1005)?

_Verification: round 2 (R2-04), not addressed_

#### `h/tron/models/kv_cache.hpp:1048` **new** (B7/A7)

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

_Verification: N2-1 + N2-4: set :842/:844, reset :849-851; layout Note kv_cache.hpp:493-497; mirror base = (kv_blocks_alias - arena_data.get())/2 exactly (all block sizes even). Readers: model.hpp:2790-2794 (RX), self_attention.hpp:1566-1567 (attention)._

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

_Verification: round 1 (R1-21), not addressed_

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

_Verification: round 1 (R1-22), not addressed_

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

_Verification: round 1 (R1-23), partial: No slot_matches<geometry> assert on the logical-slot branch of mirror_at_storage (:1240-1241) and no primary_geometry assert on the EAGLE branch; no shared storage_byte_base<geometry>(offset) helper - kv_block_at_storage (:1203-1212) and mirror_at_storage (:1240-1246) still compute byte_base separately, so a mismatched geometry still computes plane_bytes for the wrong head size on a logical slot without an assert._

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

_Verification: round 1 (R1-26), not addressed_

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

_Verification: round 1 (R1-27), not addressed_

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

_Verification: round 2 (R2-08), not addressed_

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

_Verification: round 1 (R1-28), not addressed_

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

_Verification: round 1 (R1-29), not addressed_

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

Why lazy?  Packing all `items.size()` groups once before the page loop is at most `max_minibatch_size` 512-byte copies and deletes the bitmap and the per-(page, token) test-and-set.  If a cache is really wanted, `attn_accum` is already per worker, per token and 64B-aligned; a growable `thread_local std::vector` is neither aligned (see the header contract) nor bounded the way the mask next to it is.

_Verification: round 1 (R1-31), not addressed_

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

_Verification: round 1 (R1-32), not addressed_

#### `h/tron/models/self_attention.hpp:1367` R1-34 (B6/A12)

```cpp
 1367*       if (amx_on) {
 1368          amx_qpack.resize(items.size() * amx_attn::Q_PACK_ELEMS_2048);
 1369          amx_attn::begin_region();
 1370        }
 1371  #endif
```

We have `tron::finally` (`h/common/util.hpp:73`, used in `gof.hpp:221`) for exactly this bracket; `tron::finally release([&] { if (amx_on) amx_attn::end_region(); });` makes the pairing structural.  Not a bug today (the function is `noexcept` and there is no return in between), your choice.

_Verification: round 1 (R1-34), not addressed_

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

_Verification: round 1 (R1-33), not addressed_

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

_Verification: round 1 (R1-35), not addressed_

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

_Verification: round 1 (R1-36), not addressed_

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
```

So the mirror path pays a 1 KB copy per page that the canonical path doesn't, and the `amxqk` bench variant behind the 686 ns figure stores straight into a 16-row `S` with no copy.  Either size `s_pages` for 16 rows in the mirror build, or note the copy's cost next to the 300 ns claim.  Also, when `mplane` is null in this build we fall all the way to the dotter although `qk_canonical_128x4` is compiled into the same binary - why not fall back to it?

_Verification: round 1 (R1-37), not addressed_

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

_Verification: round 1 (R1-38), not addressed_

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

_Verification: round 1 (R1-39), not addressed_

#### `h/tron/models/self_attention.hpp:1664` R1-40 (A5)

```cpp
 1662              if (was_valid) {
 1663                auto corr_ = constant<page::page_size>(corr_arr[offset]);
 1664*               head_sp.v_star.set(fma(head_sp.v_star, corr_, scratch));
 1665                head_sp.s_star = head_sp.s_star * corr_arr[offset] + sum_arr[offset];
```

`constant<page::page_size>` (64 wide) as the multiplier in a 128-wide `fma` only works because `constant::chunk(i)` ignores `i`.  Pre-existing at :1685, but let's not copy it: `constant<operation_head_size>`.

_Verification: round 1 (R1-40), not addressed_

### h/tron/scheduler/full.hpp

#### `h/tron/scheduler/full.hpp:310` R2-09 (A12/B4)

```cpp
  307    // Whether the model has an AMX-eligible attention shape (see
  308    // amx_mirror_eligible in kv_cache.hpp); handed to every KV book this tree
  309    // creates so ineligible models allocate no K mirror arena.
  310*   bool amx_mirror_eligible = true;
```

Every constructor sets this, so the `= true` is dead, and `true` is the unsafe direction for a default (see the constructor comment in `kv_cache.hpp`).  If the file's convention is to give these members a default, make it `false`.

_Verification: round 2 (R2-09), not addressed_

#### `h/tron/scheduler/full.hpp:1456` R2-10 (B3)

```cpp
 1454        root = std::make_shared<node_t>(logical_kv_slots, storage_kv_slots,
 1455            cfg->support_eagle,
 1456*           amx_mirror_eligible(model_t::plugin_t::attention_kernels));
 1457      }
```

`amx_mirror_eligible` is now the name of the predicate over kernels, a `node_base` member, and two constructor parameters.  Inside `node` methods the member shadows the function.  `has_amx_attention_shape(kernels)` for the predicate would keep them apart.

_Verification: round 2 (R2-10), not addressed_

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

_Verification: round 1 (R1-41), not addressed_

#### `src/tron/CMakeLists.txt:183` R1-42 (A1)

```cmake
  181  if(TRON_AMX_DISPATCH)
  182    target_sources(tron PRIVATE kernels/amx_attn.cpp)
  183*   set_source_files_properties(kernels/amx_attn.cpp PROPERTIES
  184      COMPILE_OPTIONS "-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma")
  185    target_compile_definitions(tron PUBLIC TRON_AMX_DISPATCH)
```

Only `-mamx-tile -mamx-bf16` are new for this TU; the `-mavx512*`/`-mavx2`/`-mfma` are already PUBLIC on `tron` (:234-237) unless `AVX512=OFF`, in which case this would be the only AVX-512 code in a non-AVX-512 binary.  Is that build meant to exist?  If not, trim the list; if so, say so.

_Verification: round 1 (R1-42), not addressed_

### src/tron/kernels/amx_attn.cpp

#### `src/tron/kernels/amx_attn.cpp:7` R1-43 (B15)

```cpp
    7* #include <atomic>
    8  #include <cstdlib>
    9  #include <cstring>
   10  #include <immintrin.h>
   11  #include <unistd.h>
```

Unused?

_Verification: round 1 (R1-43), not addressed_

#### `src/tron/kernels/amx_attn.cpp:34` R1-45 (A13)

```cpp
   34* // One stored tile's worth of fp32 scores (16 rows x 16 values).
   35  // sizeof(float) rather than a literal 4: the constant converts tile bytes
   36  // into elements of the float arrays it indexes, so the element size belongs
   37  // to that type. C++ does not formally fix sizeof(float), but every tron
   38  // target does (the AVX-512 *_ps intrinsics and the fp32 tile accumulators
   39  // require IEEE 32-bit float); the static_assert pins the assumption.
   40  // (C++23 has std::float32_t, but tron's kernel convention is plain float
   41  // for fp32 throughout.)
```

Eight lines of prose for `static_assert(sizeof(float) == 4)`.  I can smell Claude patting itself on the back a mile away.  The message string says everything the assert needs to say; flush the paragraph.

_Verification: round 1 (R1-45), not addressed_

#### `src/tron/kernels/amx_attn.cpp:45` R1-46 (B3/B12)

```cpp
   44  // TDPBF16PS consumes the head dim in 32-dim steps (16 bf16 pairs per step).
   45* constexpr int DIM_STEP = 32;
   46  // Query heads per KV head - the GQA group width, the "x4" in the kernel names.
   47  constexpr int GROUP_HEADS = int(GROUP_HEADS_4);
```

`DIM_STEP` is documented as 32 head dims per k-step, but at :210 it means 32 tokens per PV k-step and at :211 it means 16 dims x 2 paired tokens per V tile column.  Three quantities with the same numeral shouldn't share a constant; name the other two.  Also, the `4` at :251 is `PAGE / TILE_ROWS`.

_Verification: round 1 (R1-46), not addressed_

#### `src/tron/kernels/amx_attn.cpp:64` R1-47 (B6)

```cpp
   64* bool detect_and_request() noexcept {
   65    // Runtime kill switch for same-binary A/B tests and emergency disable.
   66    const char* off = std::getenv("TRON_AMX_DISABLE");
   67    if (off && off[0] == '1') return false;
   68    unsigned a, b, c, d;
   69    // CPUID leaf 7.0 EDX: bit 22 AMX-BF16, bit 24 AMX-TILE
   70    __asm__ volatile("cpuid" : "=a"(a), "=b"(b), "=c"(c), "=d"(d) : "a"(7), "c"(0));
   71    if (!((d >> 22) & 1) || !((d >> 24) & 1)) return false;
```

You know we have `cpuid_bit(leaf, reg, bit)` in `h/system/mwaitx.hpp:22`, and that `is_rtm_supported` (`lazy<bool>` + `TRON_NO_RTM=1`) is the same shape as this whole function, right?  Reuse it, or say why the AMX probe can't.

_Verification: round 1 (R1-47), not addressed_

#### `src/tron/kernels/amx_attn.cpp:66` R1-48 (A6/B17)

```cpp
   64  bool detect_and_request() noexcept {
   65    // Runtime kill switch for same-binary A/B tests and emergency disable.
   66*   const char* off = std::getenv("TRON_AMX_DISABLE");
   67    if (off && off[0] == '1') return false;
   68    unsigned a, b, c, d;
```

This is a first-character test: `TRON_AMX_DISABLE=true` leaves AMX on, silently.  Nearest precedents are `strcmp(v, "1") == 0` (`TRON_NO_RTM`, `TRON_USE_ARENA_ALLOCATOR`) or `atoi(v) > 0` (`USE_HW_ATTN`); pick one.

_Verification: round 1 (R1-48), not addressed_

#### `src/tron/kernels/amx_attn.cpp:108` R1-49 (A8)

```cpp
  107  void pack_q_group_128x4(const uint16_t* q_group, uint16_t* packed) noexcept {
  108*   std::memset(packed, 0, Q_PACK_ELEMS_2048 * sizeof(uint16_t));
  109    // One panel per 32-dim step; see the layout contract at the declaration.
  110    for (int step = 0; step < HEAD_SIZE / DIM_STEP; step++) {
  111      for (int dim_pair = 0; dim_pair < DIM_STEP / 2; dim_pair++) {
  112        for (int q_head = 0; q_head < GROUP_HEADS; q_head++) {
```

Each pack memsets 4 KB to write 512 B; columns 4..15 never change.  The `P` buffer below zeroes its padding once per thread - same discipline here?

_Verification: round 1 (R1-49), not addressed_

#### `src/tron/kernels/amx_attn.cpp:202` R1-50 (B1)

```cpp
  198    for (int q = 0; q < GROUP_HEADS; q++) {
  199      for (int c = 0; c < PAGE; c += 32) {
  200        __m512 lo = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c);
  201        __m512 hi = _mm512_loadu_ps(exp_rows + q * row_stride_floats + c + 16);
  202*       _mm512_storeu_si512(P[q] + c, (__m512i)_mm512_cvtne2ps_pbh(hi, lo));
  203      }
  204    }
```

A one-line comment that `cvtne2ps_pbh(a, b)` puts `b` in the low half would save the next reader the lookup.

_Verification: round 1 (R1-50), not addressed_

### src/amx_fused_bench.cpp

#### [blocker] `src/amx_fused_bench.cpp:3` R1-51 (B6/B8/A9)

```cpp
    1  // amx_fused_bench.cpp — fused-page software-attention benchmark.
    2  //
    3* // Self-contained (no tron includes; compiles with plain g++), but uses the
    4  // EXACT tron kv_block layouts so numbers transfer:
    5  //   K page: [64 tokens][128 dims] bf16 row-major, row stride 256 B
    6  //   V page: [32 pairs][128 dims][2] bf16 token-pair-interleaved (AMX B format)
    7  // and replicates the shipping kernels' instruction patterns for the AVX
    8  // baseline (dotter: 4x vdpbf16ps + hreduce per (token, query);
```

A 732-line `main()` in `src/` that no CMake target builds, which re-implements every shipped kernel by hand (`pack_q`, `qk_amx`, `qk_amx_rowmajor`, `pv_amx`, `pack_k_mirror`, `st_to_s`).  Any kernel fix now has to be made twice, and the numbers quoted in `Note [Mirror orientation]` were measured on the copy, not on `amx_attn.cpp`.  Either make it a `t/` benchmark target that links `libtron` and calls the real kernels, or take it out of the tree and keep the numbers in the doc with the command line that produced them.  A second copy of every kernel in `src/` is not something I want to approve.

_Verification: round 1 (R1-51), not addressed_

#### `src/amx_fused_bench.cpp:22` R1-52 (A3)

```cpp
   22* // Variants:
   23  //   avx     : dotter-pattern QK + shared softmax + scaled_v-pattern PV
   24  //   amx44   : our fused AMX path, PV output blocking 4+4
   25  //   amx62   : our fused AMX path, PV output blocking 6+2
   26  // Usage: amx_fused_bench [Nq] [iters] [variant] [pages]
```

`amxqk` and `amxpl` are missing from this list (and `amx_attn.cpp:230` cites `amxqk`).

_Verification: round 1 (R1-52), not addressed_

#### `src/amx_fused_bench.cpp:31` R1-53 (A3/A11)

```cpp
   30  // Correctness: every variant is checked against a scalar reference once
   31* // (rel tol 2e-2, matching t_amx_attention practice) before timing.
```

There is no `t_amx_attention` on main; it lives on `bill-amx`.  Also 2e-2 relative is a long way from the `1e-4 * abs_mass` `t_amx_numerics` uses in this same PR, so "practice" is doing a lot of work here.  Flush the clause.

_Verification: round 1 (R1-53), not addressed_

#### `src/amx_fused_bench.cpp:75` R1-54 (A3)

```cpp
   74  // fast exp used IDENTICALLY by all variants (so softmax cost is comparable):
   75* // exp(x) via exp2(x * log2e), 2^i * poly(f). Max rel err ~2e-7, fine at tol 2e-2.
   76  static inline __m512 vexp(__m512 x) {
```

The degree-5 Taylor terms give ~3.3e-6 at |f| = 0.5 (I checked), not 2e-7.  Fix the number or delete the sentence; the conclusion holds either way.

_Verification: round 1 (R1-54), not addressed_

#### `src/amx_fused_bench.cpp:120` R1-55 (B2)

```cpp
  119  // ---------- 16x16 fp32 transpose (validated against reference below) ----------
  120* static inline void transpose16x16(
  121      const float* src, int src_stride_f, float* dst, int dst_stride_f) {
```

Neither `transpose16x16` nor its reference is used by any variant (`st_to_s` has its own copy); they exist to validate each other.  Flush all three pieces.

_Verification: round 1 (R1-55), not addressed_

#### `src/amx_fused_bench.cpp:264` R1-56 (A3/B11)

```cpp
  261  // Q pack: Q[nq][128] bf16 -> 4 B panels, each 16 rows x 64 B:
  262  // panel s, row dp (dim pair), lane q: { Q[q][s*32+2dp], Q[q][s*32+2dp+1] },
  263  // lanes q>=nq zeroed (padding).
  264* static void pack_q(const bf16* Q, int nq, bf16* Bp /*4*16*64 bf16? bytes*/) {
  265    std::memset(Bp, 0, 4 * 16 * 64);
```

A question mark in a size comment means we don't know the size.  It's 4*16*32 bf16 = 4*16*64 bytes; write one.  Also, s/(Bill's formulation)// at :279 - same as the "ours" in the header Note.

_Verification: round 1 (R1-56), not addressed_

### t/CMakeLists.txt

#### [blocker] `t/CMakeLists.txt:190` R1-57 (A10/B8)

```cmake
  186      set_property(TEST t_generate_ingest_1_${model} APPEND PROPERTY
  187        LABELS ${TEST_LABELS})
  188    endforeach()
  189  endif()
  190* add_catch_test(NAME t_amx_logit_ab FILES t_amx_logit_ab.cpp force_generate.cpp LIBRARIES tron full_scheduler PROPERTIES RESOURCE_LOCK fpga LABELS fpga)
```

This is registered under `LABELS fpga`, so `bin/slice run --filter=fpga` (the Test FPGA job), `make test`, and `ctest -L fpga` all select it, and its first line is `REQUIRE(getenv("AMX_LOGIT_OUT") != nullptr)`.  The FPGA lane fails the moment CI runs on this PR.  It's a dump tool, not a test (its one `SUCCEED` asserts nothing about AMX): make it a `runtron`/`tronutil` flag or a `bin/` script and drop the ctest entry; if it stays, `DISABLED TRUE` like `t_clearhbm`.  Also, it defaults to `ingested-llama-3.1-8b` but sits outside `if(BUILD_INGEST_MODELS)`.

_Verification: round 1 (R1-57), not addressed_

#### [blocker] `t/CMakeLists.txt:359` R1-58 (A4/A10/B14)

```cmake
  358  add_catch_test(NAME t_llama_unit LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  359* add_catch_test(NAME t_amx_mirror LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  360  add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake PROPERTIES LABELS fake)
  361  add_catch_test(NAME t_amx_arena_leak LIBRARIES tron pos_fake PROPERTIES LABELS fake)
```

In the default build all three of these are a single `SUCCEED("...skipped")`, and even with the options on they `WARN` and return on a non-AMX host - so after merge nothing in CI compiles or runs the flagged code.  How was this validated, given `make test` has no coverage for it?  At minimum a compile-only configuration with both options ON (precedent: `heterogeneous_scheduler_compile`, :351) so the `#ifdef`'d code can't rot silently; the run log from the 6962P host in the PR would also help.

_Verification: round 1 (R1-58), not addressed_

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

_Verification: round 1 (R1-59), not addressed_

#### `t/t_amx_arena_leak.cpp:89` R2-11 (A3)

```cpp
   88    if (tron::amx_attn::available()) {
   89*     // The arena allocation actually ran (maybe_allocate_mirror_arena is
   90      // gated on available()), so the balance above covered it.
   91      REQUIRE(alloc_delta >= 1);
```

s/gated on available()/gated on the eligibility flag (true through the 3-argument form) and available()/.

_Verification: round 2 (R2-11), not addressed_

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

_Verification: round 1 (R1-60), not addressed_

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

_Verification: round 2 (R2-12), not addressed_

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

_Verification: round 2 (R2-13), not addressed_

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

_Verification: round 2 (R2-14), not addressed_

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

_Verification: round 1 (R1-61), not addressed_

#### `t/t_amx_mirror.cpp:80` R1-62 (B18)

```cpp
   78  TEST_CASE("K mirror is byte-equivalent to canonical K", "[kv_data][amx_mirror]") {
   79    run_case<128>();  // qwen/llama head size (the AMX fast-path shape)
   80*   run_case<64>();   // smaller-head geometry
   81  }
```

Which consumer reads a head-64 plane?  Dispatch requires head 128, so this is 8192 `REQUIRE`s guarding data nobody reads - the same point as the write-through gate in `model.hpp`: don't maintain planes no kernel consumes, and this case goes away.  Still here.  Through the scheduler a head-64 book no longer has a plane at all, so this case now tests a layout only the legacy constructor can produce - one more reason to flush that constructor.

_Verification: round 1 (R1-62), not addressed_

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

_Verification: round 1 (R1-63), not addressed_

#### `t/t_amx_numerics.cpp:33` R1-65 (B3/B15)

```cpp
   31  // The kernel shape, from the interface header.
   32  constexpr size_t PAGE = tron::amx_attn::PAGE_TOKENS_64;
   33* constexpr size_t HD = tron::amx_attn::HEAD_SIZE_128;
   34  constexpr size_t NQ = tron::amx_attn::GROUP_HEADS_4;  // query heads per KV head
   35  constexpr size_t ROWS = tron::amx_attn::TILE_ROWS_16;
```

We renamed this `HEAD_SIZE` in the kernel TU; same here (and in the bench)?  Also `std::make_unique` without `<memory>`.  `HD` is now an alias of `HEAD_SIZE_128`; the alias could just be `head_size`.  And `NQ`/`ROWS` are a third spelling of `GROUP_HEADS`/`TILE_ROWS` - one vocabulary, please.  The bench still has its own `HD = 128`.

_Verification: round 1 (R1-65), partial: (1) alias is still named HD, not HEAD_SIZE (t_amx_numerics.cpp:33); (2) bench still has its own literal "static constexpr int HD = 128;" (src/amx_fused_bench.cpp:53, untouched by the two commits); (3) <memory> still not included although std::make_unique is used at t_amx_numerics.cpp:80 and :122._

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

_Verification: round 1 (R1-64), not addressed_

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

_Verification: round 1 (R1-67), not addressed_

### t/t_llama_unit.cpp

#### `t/t_llama_unit.cpp:309` **new** (5.2/A3)

```cpp
  307      WARN("mirror arena absent (AMX unavailable) - mirror view check not run");
  308    } else {
  309*     alignas(64) std::array<bf16, 128> row;
  310      row.fill(static_cast<bf16>(1.0f));
  311      page->template set_k_mirror<geometry>(slot, 0, 0, row.data());  // validator's row
  312      cache.set_storage_view(cache.eagle_storage_offset());
```

Every check in this block is implied by the coherence case below (:374-:380 read different values at the same index through the two views, which proves the planes are distinct memory).  Flush it - or, if the parallel with `page->k` above is worth keeping, say that these rows are markers and mirror == scatter(canonical) is deliberately not maintained here; dims 1..127 of canonical K are uninitialized at this point.

_Verification: N3-3: set_k_mirror with a filled row while only canonical dim 0 was set (:282, :288); :314/:319/:321 are dominated by :374-:380._

#### `t/t_llama_unit.cpp:346` **new** (A10/B14)

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

_Verification: N3-4: grep save_k t/ finds only comments and this lambda; is_eagle appears in tests only as false; commit message verifies the three unit cases only. His #1131 pattern ('record how you validated')._

#### `t/t_llama_unit.cpp:360` **new** (B6)

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

_Verification: N3-1: 10 spellings of the formula in 4 files (6 code, 2 comment, 2 partial), 5 in t_llama_unit.cpp; kv_cache.hpp:1870 'The .k data is contiguous'; testutil.hpp included at t_llama_unit.cpp:38._

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

_Verification: round 1 (R1-68), partial: The commented test (t_llama_unit.cpp:455-556) itself is unchanged: it still checks only page_of(target_token) (page 1) where only token 0 came through copy_storage_slot, does not check destination page 0, and still compares the whole plane (:524-537) rather than only copied tokens. The non-multiple-of-64 tok_ct append and the offset-63 column check exist only in the separate EAGLE test at :1071-1145 (geometry_64 slot, heterogeneous_eagle_cache), not in the fixed-KV-layout test with geometry_128 that the comment anchors to._

#### `t/t_llama_unit.cpp:1133` **new** (B7)

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

_Verification: N3-2 (high): (((0*4+c)*16+0)*16+t)*2 == ((offset/16)*16*16 + offset%16)*2._

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

_Verification: round 1 (R1-69), not addressed_

## 4. Checked and clean in the delta

| area | what was verified | source |
|---|---|---|
| The EAGLE fix | For slot 0 the remap is exactly kv_block()'s: mirror_arena + n_pages*(offsets[L]/2) + (kv_head*n_pages + pg)*plane_bytes is the same cell of the half-size arena as kv_blocks_alias + (slot.i*n_kv_heads + kv_head)*n_pages + pg. The TRON_ASSERT_EQ(slot.i, 0) is stricter than canonical (which indexes past the last slot for slot.i > 0 under the view, guarded only by model.hpp:1379-1381) and guards the exact quantity. k_mirror_data (reader) and set_k_mirror (save_k writer) both go through mirror(); copy_storage_slot and fill_random address physical slots directly and are view-independent, consistent with 'plane(physical X) == scatter(K of physical X)'. The new mirror_at_storage assert copies kv_block_at_storage's eagle-offset check. A view with no arena is a no-op (mirror_at_storage returns nullptr first). | N2 (1),(4),(8); N3 (5) |
| The three new tests fail on the old mirror() | Reasoned per REQUIRE: case 1 fails at :314 (same plane for both accessors); case 2 fails at :374 (M(0) holds the draft's 2000+i rows vs canonical 1000+i); case 3 fails at :1137 (column under the view read from M(0), token+1 vs token+11). Matches the commit message's three parentheticals. Production write order (validator batch, then draft batch under the view) is the order the interleaved test uses per token; draft-last is the order that exposed the bug. | N3 (2),(3) |
| Named constants, mechanics | amx_attn.cpp's PAGE/HEAD_SIZE/GROUP_HEADS/TILE_ROWS/TILE_ROW_BYTES now derive from the header constants, so the kernels and shape_ok cannot drift (closes R1-30's follow-up and R1-11's dead tile_row_bytes); apply_page_tok evaluates the predicate once and static_asserts PAGE_TOKENS_64 == page::page_size (page::page_size resolves to the type despite the page parameter - qualified lookup ignores variables); every new constant has readers; no stale q_pack_elems/tile_rows anywhere; header :69 'output buffers are sized with TILE_ROWS_16' is true; no added line exceeds the 88-column limit. The two constexpr amx_shape_ok live in different member functions - no shadowing. | N1 (b), N2 (7) |
| PR description text | The new sentences (arena condition; mirror follows the EAGLE view; three test descriptions) match kv_cache.hpp:1265-1271, full.hpp:1729-1740 and t_llama_unit.cpp - no inaccuracy in the new text. What is still missing is listed in the body. | N1 (f) |
| New EAGLE tests | The interleaved-write test writes validator then draft to the same (page, offset), as production orders them, and compares each plane byte-exactly with its own physical slot; the extended view test checks the two planes are distinct memory; the append test checks the moved token's column in both views. All three WARN-skip on non-AMX hosts (same pattern as before). | delta read; N3 |
| Doc and description | Not touched by the two commits - the round-2 doc comments and the description comment carry over unchanged. | delta file list |

## 5. Glossary

- **canonical-K** - Project shorthand: K kept in today's original single-copy row-major storage and read as-is by the AVX dotter, the FPGA DMA and the canonical AMX kernel.
- **mirror / k_vnni** - A second, derived copy of K in the pair-interleaved (VNNI) layout the AMX B operand wants. The mirror formulation originates from Bill's PR #2934 (k_vnni); the parallel-arena implementation and all numbers in PR #3879 are ours (jhan-amx-p0).
- **parallel arena** - Ordinary (non-DMA) RAM owned by the book, sized kv_bytes/2, one mirror plane per (storage slot, kv_head, page). Not the book's DMA arena_data.
- **shape gate / amx_attn::shape_ok** - New in cc8a86bb3: head_size == 128 && kv_mul == 4 in one function, used by the dispatch, the save_k write-through and (via amx_mirror_eligible) the arena allocation.
- **amx_mirror_eligible** - New in cc8a86bb3: (a) a constexpr function over a plugin's attention_kernels (true if any kernel passes the shape gate); (b) a bool carried on every node_base and passed to book::try_create; (c) a constructor parameter of book. The 3-argument book/try_create forms default it to true.
- **storage view / kv_blocks_alias** - book::set_storage_view() repoints kv_blocks_alias so logical slot 0 resolves to the extra EAGLE physical slot for the whole draft forward; canonical K accessors follow it, the mirror accessors do not (still true at cc8a86bb3).
- **EAGLE** - Speculative-decoding draft model that runs its own forward through the same books, storing its layer-0 K/V in an extra physical storage slot after the validator's logical slots.
- **ready / pending pass** - Software attention runs twice per operation: over pages that receive no K/V this forward (ready), then after upstream_kvs_ready.wait() over pages being written this forward (pending).
- **RX worker** - Per-card driver thread running DMA completion callbacks; rope_k/save_k execute there.
- **Note [Title]** - GHC-style named long comment, checked by make lint-notes.
- **A3, B6, ... tags** - Item numbers from ~/workspace/reviewers/alexey.md section 1; shown only in the verification line, never in the comment text.

## 6. Method and limits

- Persona: ~/workspace/reviewers/alexey.md Part 1. Round-3 behaviour applied: concede on what was fixed ("Very good." / "Good."), check that the fixes are the fixes asked for, carry the rest unchanged, isolate what still blocks in the body.
- Inputs: new head 96b5a6c72 (delta from cc8a86bb3 = two commits, 6 files, +208/−38), clean worktrees of head and merge base, the full PR diff, the PR description (updated since round 2: arena condition and EAGLE view now described; still no mention of the doc, kv_block_planes, v_data/v_base, the #errors, fill_random, full.hpp), and the 79 open comments after round 2 (no triage marks were found on alexey-review-2.md this time).
- Agents: 5 status-checkers re-anchored the 79 open comments to the new head with a source snippet range each (70 unchanged, 4 partial, 5 fixed); 3 finders (design/correctness, naming and comment accuracy, tests) returned 14 findings on the delta, merged into 8 new comments and 6 follow-up sentences. No adversarial round: the new findings are naming, comment accuracy, test structure and a validation-record ask; the correctness of the EAGLE fix was confirmed by two finders independently (N1 (1), N3 (2)-(3)). Verdict-carrying facts re-checked first-hand: t/CMakeLists.txt not in the delta (fpga-labelled tool unchanged); doc/intel-amx.md not in the delta ("8 models" list unchanged); legacy 3-argument forms unchanged; mirror() now remaps under the view (kv_cache.hpp:1266-1268).
- Not verifiable here: no tron build (nix unavailable); the commit messages report all suites passing on delphi-3bda with TRON_AMX_K_MIRROR=ON and the three new EAGLE checks failing on the previous header - taken as author-reported. CI has not run on the new head (draft, no Run CI label).
- Counts: 82 open comments (carried over + new), 5 resolved in this round.
