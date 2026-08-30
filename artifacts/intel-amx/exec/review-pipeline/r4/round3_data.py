# Round-3 data for gen_review3.py (exec'd into its namespace). His voice in BODY, NEW[].text,
# FOLLOWUP, FIXED_VOICE; everything else is the verification record.

BODY = (
"The mirror now follows the view, with the assert and the interleaved test - good, that is the fix I had in mind.  "
"The named constants settle the three-places question too.  "
"What's left from my side: `t_amx_logit_ab` is still an `fpga`-labelled test that fails without `AMX_LOGIT_OUT` "
"(that one alone blocks), the 3-argument `book`/`try_create` still default `amx_mirror_eligible` to allocate - and "
"the new EAGLE coherence test is a third user of that form - the doc still says \"8 models\" and lists six, and the "
"description now has the arena condition right but still says nothing about the doc, the `kv_block_planes` refactor, "
"`v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the scheduler plumbing.  "
"One new thing: constants named after their values (`HEAD_SIZE_128`) are literals with a longer name; see the "
"header.  The rest is carried over unchanged below."
)

FOLLOWUP = {
  "R1-23": "The eagle-offset assert arrived; `slot_matches<geometry>` on the logical branch did not, and the two `byte_base` branches are still a copy of each other.  The shared helper would give both.",
  "R1-65": "`HD` is now an alias of `HEAD_SIZE_128`; the alias could just be `head_size`.  And `NQ`/`ROWS` are a third spelling of `GROUP_HEADS`/`TILE_ROWS` - one vocabulary, please.  The bench still has its own `HD = 128`.",
  "R1-20": "This sentence was edited in 96b5a6c72 and kept \"(append + defrag)\".",
  "R1-68": "The new EAGLE append check covers the moved token in both views - good; this test still checks page 1 only.",
  "R2-02": "The PR description now says it; this sentence still doesn't.",
  "R1-61": "Now six full copies plus two hand-expanded column forms (`t_llama_unit.cpp:370`, `:1128`, `:1135`, `:1140`), and two lambdas that are `require_mirror_matches` again.  `testutil.hpp` is already included there; a whole-plane and a one-token overload in it would serve `t_amx_mirror`, `:522`, `:360` and `:1118`.",
  "R2-03": "The new EAGLE coherence test (`t_llama_unit.cpp:338`) relies on the arena and therefore on this implicit `true` - a third user of the 3-argument form (with `:272`).  Pass the flag explicitly there either way.",
}
SNIP_OVERRIDE = {}
DROP = {}

FIXED_VOICE = {
  "R1-18": "Good - that is the fix I had in mind, and the `slot.i == 0` assert is the right call.",
  "R1-30": "Good.",
}
TRIAGE = {}
TRIAGE_PREDICTION = {}

NEW = [
  dict(file="h/tron/kernels/amx_attn_iface.hpp", line=77, snip=(72, 84),
       text="A constant whose name carries its value is a literal with a longer name: the day `HEAD_SIZE_128` is not 128 the name lies, and `static_assert(Q_PACK_ELEMS_2048 == 2048, \"the constant's name states its value\")` guards a problem we created.  `tile_rows`/`q_pack_elems` were fine; `head_size`, `group_heads`, `page_tokens` say what they are, and every constant in `h/tron/models`, `kernels` and `scheduler` is lower snake_case (`page_size`, `kv_block_planes`, `illegal_sliding_window`).  Flush the `static_assert` with the rename.",
       tag="B3", note="N1: 179 constexpr definitions in h/tron/{models,kernels,scheduler}: 172 lower_snake, 1 UPPER_CASE (function-local), 0 with a value suffix; across all of h/ no constant embeds its value. AGENTS.md:38 asks to match the local module's naming.", blocker=False),
  dict(file="h/tron/kernels/amx_attn_iface.hpp", line=75, snip=(72, 78),
       text="\"Every shape literal in the AMX code derives from these three\" - `DIM_STEP = 32`, `PANEL_ELEMS = 16 * 16 * 2`, the `4` in `step * 4`, the `16`s in the pack index and the `64/16/32/48` in the output stores are still literals in `amx_attn.cpp`, `scatter_k_mirror` has its own 16 and 32, and `Q_PACK_ELEMS_2048` on the next line derives from `TILE_ROWS_16`, a fourth.  s/Every shape literal in the AMX code derives from these three/`shape_ok` and the kernel buffer sizes are written in terms of these/ - or make it true.",
       tag="A3", note="N1-2 + N2-2 (high): amx_attn.cpp :45, :113, :158, :199, :213-229, :250-265 unchanged by 8e22b0aa5.", blocker=False),
  dict(file="h/tron/models/kv_cache.hpp", line=1048, snip=(1043, 1049),
       text="So the view now lives in two members that must move together (`kv_blocks_alias` and `mirror_view_offset_`), set and cleared in two places, with no statement or assert that they agree.  The layout Note at :495 already describes the design for this: views \"preselect their base pointer when the view changes\".  A `mirror_alias` set next to `kv_blocks_alias` would make `mirror()` textually `kv_block()` on the other arena - no optional, no branch, one view to keep in sync.  Whichever stays, say here who writes it (the work_queue thread around `state.forward`, `full.hpp:1729-1740`) and who reads it (the RX and attention workers that forward dispatches), since that dispatch is what publishes a plain store to them - the same contract `kv_blocks_alias` has never written down either.",
       tag="B7/A7", note="N2-1 + N2-4: set :842/:844, reset :849-851; layout Note kv_cache.hpp:493-497; mirror base = (kv_blocks_alias - arena_data.get())/2 exactly (all block sizes even). Readers: model.hpp:2790-2794 (RX), self_attention.hpp:1566-1567 (attention).", blocker=False),
  dict(file="h/tron/models/kv_cache.hpp", line=602, snip=(598, 607),
       text="Only the `save_k` write-through goes through `mirror()`; `copy_storage_slot` (:1883) addresses the arena by physical `storage_offset` and never sees the view.  \"Both sites ... mirror() remaps\" sends a reader looking for view handling in the rebuild.  Scope the sentence to site 1.",
       tag="A3", note="N1-4 (low): copy_from hands copy_storage_slot the physical offsets (:1913-1925). The 'can never land in the validator's plane' clause holds.", blocker=False),
  dict(file="t/t_llama_unit.cpp", line=309, snip=(299, 321),
       text="Every check in this block is implied by the coherence case below (:374-:380 read different values at the same index through the two views, which proves the planes are distinct memory).  Flush it - or, if the parallel with `page->k` above is worth keeping, say that these rows are markers and mirror == scatter(canonical) is deliberately not maintained here; dims 1..127 of canonical K are uninitialized at this point.",
       tag="5.2/A3", note="N3-3: set_k_mirror with a filled row while only canonical dim 0 was set (:282, :288); :314/:319/:321 are dominated by :374-:380.", blocker=False),
  dict(file="t/t_llama_unit.cpp", line=346, snip=(345, 357),
       text="The lambda mimics `save_k_impl`, but nothing in `t/` calls the real one (`model.hpp:2793`) under the view, and the scenario I described ends in the parent's `qk_mirror_128x4` read.  Was an EAGLE (parent, child) run done with `TRON_AMX_K_MIRROR=ON` and its greedy output compared to the canonical build, the way the qwen A/B in the description was?  Record it in the PR.",
       tag="A10/B14", note="N3-4: grep save_k t/ finds only comments and this lambda; is_eagle appears in tests only as false; commit message verifies the three unit cases only. His #1131 pattern ('record how you validated').", blocker=False),
  dict(file="t/t_llama_unit.cpp", line=360, snip=(360, 372),
       text="Ditto (`t_amx_mirror.cpp:28`): this lambda and `require_mirror_column_matches` at :1118 are `require_mirror_matches` again, and the plane's K rows are contiguous, so the existing helper already covers the whole-plane case.",
       tag="B6", note="N3-1: 10 spellings of the formula in 4 files (6 code, 2 comment, 2 partial), 5 in t_llama_unit.cpp; kv_cache.hpp:1870 'The .k data is contiguous'; testutil.hpp included at t_llama_unit.cpp:38.", blocker=False),
  dict(file="t/t_llama_unit.cpp", line=1133, snip=(1132, 1141),
       text="Both of these are implied by `require_mirror_column_matches()` together with :1099 and :1103 (its s = dp = j = 0 iteration is exactly this index, and `row[0]` is already required equal to `source_token + 1` / `+ 11`).  Flush them; if a literal-value check is wanted, take the index from the helper instead of expanding it by hand a third way.",
       tag="B7", note="N3-2 (high): (((0*4+c)*16+0)*16+t)*2 == ((offset/16)*16*16 + offset%16)*2.", blocker=False),
]

METHOD = [
  "Persona: <code>~/workspace/reviewers/alexey.md</code> Part 1. Round-3 behaviour applied: concede on what was fixed (\"Very good.\" / \"Good.\"), check that the fixes are the fixes asked for, carry the rest unchanged, isolate what still blocks in the body.",
  "Inputs: new head <code>96b5a6c72</code> (delta from <code>cc8a86bb3</code> = two commits, 6 files, +208/&minus;38), clean worktrees of head and merge base, the full PR diff, the PR description (updated since round 2: arena condition and EAGLE view now described; still no mention of the doc, <code>kv_block_planes</code>, <code>v_data</code>/<code>v_base</code>, the <code>#error</code>s, <code>fill_random</code>, <code>full.hpp</code>), and the 79 open comments after round 2 (no triage marks were found on <code>alexey-review-2.md</code> this time).",
  "Agents: 5 status-checkers re-anchored the 79 open comments to the new head with a source snippet range each (70 unchanged, 4 partial, 5 fixed); 3 finders (design/correctness, naming and comment accuracy, tests) returned 14 findings on the delta, merged into 8 new comments and 6 follow-up sentences. No adversarial round: the new findings are naming, comment accuracy, test structure and a validation-record ask; the correctness of the EAGLE fix was confirmed by two finders independently (N1 (1), N3 (2)-(3)). Verdict-carrying facts re-checked first-hand: <code>t/CMakeLists.txt</code> not in the delta (fpga-labelled tool unchanged); <code>doc/intel-amx.md</code> not in the delta (\"8 models\" list unchanged); legacy 3-argument forms unchanged; <code>mirror()</code> now remaps under the view (<code>kv_cache.hpp:1266-1268</code>).",
  "Not verifiable here: no tron build (nix unavailable); the commit messages report all suites passing on delphi-3bda with TRON_AMX_K_MIRROR=ON and the three new EAGLE checks failing on the previous header - taken as author-reported. CI has not run on the new head (draft, no <code>Run CI</code> label).",
  "Counts: __N__ open comments (carried over + new), __F__ resolved in this round.",
]

CLEAN = [
  ("The EAGLE fix", "For slot 0 the remap is exactly kv_block()'s: mirror_arena + n_pages*(offsets[L]/2) + (kv_head*n_pages + pg)*plane_bytes is the same cell of the half-size arena as kv_blocks_alias + (slot.i*n_kv_heads + kv_head)*n_pages + pg. The TRON_ASSERT_EQ(slot.i, 0) is stricter than canonical (which indexes past the last slot for slot.i > 0 under the view, guarded only by model.hpp:1379-1381) and guards the exact quantity. k_mirror_data (reader) and set_k_mirror (save_k writer) both go through mirror(); copy_storage_slot and fill_random address physical slots directly and are view-independent, consistent with 'plane(physical X) == scatter(K of physical X)'. The new mirror_at_storage assert copies kv_block_at_storage's eagle-offset check. A view with no arena is a no-op (mirror_at_storage returns nullptr first).", "N2 (1),(4),(8); N3 (5)"),
  ("The three new tests fail on the old mirror()", "Reasoned per REQUIRE: case 1 fails at :314 (same plane for both accessors); case 2 fails at :374 (M(0) holds the draft's 2000+i rows vs canonical 1000+i); case 3 fails at :1137 (column under the view read from M(0), token+1 vs token+11). Matches the commit message's three parentheticals. Production write order (validator batch, then draft batch under the view) is the order the interleaved test uses per token; draft-last is the order that exposed the bug.", "N3 (2),(3)"),
  ("Named constants, mechanics", "amx_attn.cpp's PAGE/HEAD_SIZE/GROUP_HEADS/TILE_ROWS/TILE_ROW_BYTES now derive from the header constants, so the kernels and shape_ok cannot drift (closes R1-30's follow-up and R1-11's dead tile_row_bytes); apply_page_tok evaluates the predicate once and static_asserts PAGE_TOKENS_64 == page::page_size (page::page_size resolves to the type despite the page parameter - qualified lookup ignores variables); every new constant has readers; no stale q_pack_elems/tile_rows anywhere; header :69 'output buffers are sized with TILE_ROWS_16' is true; no added line exceeds the 88-column limit. The two constexpr amx_shape_ok live in different member functions - no shadowing.", "N1 (b), N2 (7)"),
  ("PR description text", "The new sentences (arena condition; mirror follows the EAGLE view; three test descriptions) match kv_cache.hpp:1265-1271, full.hpp:1729-1740 and t_llama_unit.cpp - no inaccuracy in the new text. What is still missing is listed in the body.", "N1 (f)"),
  ("New EAGLE tests", "The interleaved-write test writes validator then draft to the same (page, offset), as production orders them, and compares each plane byte-exactly with its own physical slot; the extended view test checks the two planes are distinct memory; the append test checks the moved token's column in both views. All three WARN-skip on non-AMX hosts (same pattern as before).", "delta read; N3"),
  ("Doc and description", "Not touched by the two commits - the round-2 doc comments and the description comment carry over unchanged.", "delta file list"),
]

# ---------------------------------------------------------------- EAGLE section (requested 2026-08-25)
EAGLE_SVG = '''<figure><svg viewBox="0 0 980 300" width="980" height="300" role="img" aria-label="Validator and EAGLE draft writing the same KV page: canonical K slots and mirror planes, before and after the fix">
<text x="14" y="20" font-size="12.5" fill="#0b0b0b" font-weight="600">One KV book, one page, token j. Left: canonical K (DMA memory). Right: mirror planes (arena). Arrows = save_k writes for logical slot 0.</text>
<text x="20" y="52" font-size="11.5" fill="#52514e" font-weight="600">physical K slots</text>
<rect x="20" y="60" width="90" height="34" rx="5" fill="#f4f3ef" stroke="#52514e"/><text x="65" y="81" font-size="11" text-anchor="middle">slot 0</text>
<rect x="118" y="60" width="90" height="34" rx="5" fill="#f4f3ef" stroke="#52514e"/><text x="163" y="81" font-size="11" text-anchor="middle">slot 1 .. L-1</text>
<rect x="216" y="60" width="110" height="34" rx="5" fill="#fdeaf3" stroke="#e7298a"/><text x="271" y="75" font-size="11" text-anchor="middle">slot L (EAGLE)</text><text x="271" y="88" font-size="9.5" text-anchor="middle" fill="#52514e">extra physical slot</text>
<text x="560" y="52" font-size="11.5" fill="#52514e" font-weight="600">mirror planes</text>
<rect x="560" y="60" width="90" height="34" rx="5" fill="#f4f3ef" stroke="#52514e"/><text x="605" y="81" font-size="11" text-anchor="middle">M(0)</text>
<rect x="658" y="60" width="90" height="34" rx="5" fill="#f4f3ef" stroke="#52514e"/><text x="703" y="81" font-size="11" text-anchor="middle">M(1 .. L-1)</text>
<rect x="756" y="60" width="110" height="34" rx="5" fill="#fdeaf3" stroke="#e7298a"/><text x="811" y="81" font-size="11" text-anchor="middle">M(L)</text>
<text x="20" y="130" font-size="11.5" font-weight="600" fill="#0b0b0b">validator forward (no view)</text>
<text x="20" y="146" font-size="10.5" fill="#52514e">save_k(slot 0) = K_v</text>
<path d="M 200 141 L 65 100" stroke="#2a78d6" stroke-width="2" fill="none" marker-end="url(#a)"/><text x="130" y="128" font-size="9.5" fill="#2a78d6">canonical -&gt; slot 0</text>
<path d="M 330 141 L 605 100" stroke="#2a78d6" stroke-width="2" fill="none" marker-end="url(#a)"/><text x="430" y="128" font-size="9.5" fill="#2a78d6">mirror -&gt; M(0)</text>
<text x="20" y="200" font-size="11.5" font-weight="600" fill="#0b0b0b">draft forward (set_storage_view = slot L)</text>
<text x="20" y="216" font-size="10.5" fill="#52514e">save_k(slot 0) = K_d, same page, same j</text>
<path d="M 330 211 L 271 100" stroke="#2a78d6" stroke-width="2" fill="none" marker-end="url(#a)"/><text x="290" y="170" font-size="9.5" fill="#2a78d6">canonical follows the view -&gt; slot L</text>
<path d="M 400 211 L 605 100" stroke="#e34948" stroke-width="2" stroke-dasharray="6 4" fill="none" marker-end="url(#r)"/><text x="470" y="176" font-size="9.5" fill="#e34948">before 96b5a6c72: mirror ignored the view -&gt; M(0) overwritten with K_d</text>
<path d="M 400 220 L 811 100" stroke="#008300" stroke-width="2" fill="none" marker-end="url(#g)"/><text x="600" y="214" font-size="9.5" fill="#008300">after: mirror_view_offset_ -&gt; M(L)</text>
<text x="20" y="262" font-size="10.5" fill="#52514e">Validator's next dense-page read of M(0) then scored against the draft's K (red); now M(0) keeps K_v and the draft reads its own M(L) (green).</text>
<text x="20" y="280" font-size="10.5" fill="#52514e">Schematic: slot boxes not to scale; L = the validator's logical slot count; EAGLE writes only logical slot 0 (its single layer).</text>
<defs><marker id="a" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#2a78d6"/></marker>
<marker id="r" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#e34948"/></marker>
<marker id="g" markerWidth="8" markerHeight="8" refX="6" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#008300"/></marker></defs>
</svg><figcaption>Where the two models' K rows and mirror rows land for the same token. Before the fix the draft's mirror write followed the logical slot, not the view.</figcaption></figure>'''

EAGLE_HTML = '''<h2>1a. What EAGLE is, and how likely it is to run together with the mirror</h2>
<p class="sub">Added on request (2026-08-25). Not part of his review; background for the EAGLE items in sections 2 and 4, written from the tree at <code>96b5a6c72</code>.</p>
<p><b>What EAGLE is.</b> EAGLE is a speculative-decoding method: a small <em>draft</em> model proposes several next tokens from the base model's hidden state, and the base model (the <em>validator</em>) checks them in one forward pass, so accepted tokens cost less than one full decode step each. In tron the draft is a one-layer model that shares the validator's KV books:</p>
<ul class="plain">
<li><b>Enablement.</b> <code>src/tron/scheduler/full.cpp:307-308</code>: if <code>cfg.support_eagle</code> or the process-wide <code>prefer_eagle</code> is set, <code>find_eagle_model("eagle-&lt;model&gt;")</code> looks the draft up in the registry; if found, <code>support_eagle</code> is forced on. <code>prefer_eagle</code> reads <code>TRON_USE_SPECULATION</code> and is <code>false</code> by default (<code>full.cpp:40-43</code>, comment "Disabled by default"); <code>runtron --draft eagle</code> sets <code>support_eagle</code> per run (<code>h/runtron/stream_generate.hpp:1421</code>). Nothing under <code>.github/</code>, <code>bin/ci</code> or <code>config/test-benchmarks.json</code> turns speculation on.</li>
<li><b>Same model type.</b> The draft is created with the validator's own <code>model_t</code> and a copied config with <code>max_layers = 1</code>, <code>is_speculator = true</code> (<code>full.cpp:317-324</code>). Its attention geometry - and therefore its <code>shape_ok</code> - is the validator's.</li>
<li><b>Shared books, extra slot.</b> The draft scheduler adopts the validator's token-tree root (<code>full.hpp:1446-1448</code>). Books are created with <code>support_eagle</code>, which adds one physical storage slot after the validator's logical slots (<code>storage_slot_count = logical + 1</code>) plus per-token embedding storage (<code>x_bytes</code>). Around each draft forward the scheduler calls <code>set_storage_view(eagle_storage_offset())</code> on every touched book and <code>reset_storage_view()</code> after (<code>full.hpp:1732</code>, <code>:1740</code>), so the draft's logical slot 0 resolves to that extra slot while canonical accessors go through <code>kv_blocks_alias</code>.</li>
<li><b>Registry.</b> Two production families have a draft: <code>eagle-llama-3.1-8b-instruct</code> (<code>config/models.yaml:254</code>; base shape 32/8/128 - AMX-eligible) and <code>eagle-llama-3.3-70b-instruct</code> (<code>:298</code>; base shape 64/8/128 - ratio 8, ineligible).</li>
</ul>
''' + EAGLE_SVG + '''
<p><b>The two ways out of the round-1 bug.</b> Option A: make <code>mirror()</code> follow the view (what <code>96b5a6c72</code> does, via <code>mirror_view_offset_</code>). Option B: assert that no view is active while a mirror arena exists - i.e. forbid EAGLE and the mirror in the same process.</p>
<p><b>How likely EAGLE and the mirror would be active together (the cost of option B).</b></p>
<table><tr><th>fact</th><th>evidence</th><th>direction</th></tr>
<tr><td>Speculation is off unless an operator asks for it</td><td><code>prefer_eagle</code> defaults false; <code>runtron --draft eagle</code> is per run; no CI/benchmark config enables it</td><td>lowers overlap today</td></tr>
<tr><td>Exactly one eligible production model has a draft</td><td>llama-3.1-8b (32/8/128) is in the gate and measured in this PR (+15%/+20% decode); llama-3.3-70b is ratio 8 and outside the gate</td><td>overlap is one model, not zero</td></tr>
<tr><td>The draft inherits the validator's geometry</td><td>same <code>model_t</code>, <code>full.cpp:321-324</code></td><td>whenever the validator is eligible, the draft's write-through is too - the bug was reachable, and option B would have to refuse the draft</td></tr>
<tr><td>Both features target decode latency on the same hosts</td><td>the mirror is opt-in "for pinned AMX deployments"; EAGLE cuts decode steps</td><td>the deployment that wants one is the deployment that wants the other</td></tr>
<tr><td>How often <code>--draft eagle</code> is used in production</td><td>not in the tree</td><td>Insufficient data</td></tr>
</table>
<p>Reading: not a frequent configuration as the tree stands (speculation is opt-in and absent from CI), but not a corner case either - llama-3.1-8b is the one eligible production model with a draft, and option B would have made tron's two decode accelerators mutually exclusive on exactly that model. The PR chose option A, which removes the question; what remains for review is the shape of that fix (two copies of the view state, section 4).</p>
'''

EAGLE_MD = '''## 1a. What EAGLE is, and how likely it is to run together with the mirror

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
'''

# ---------------------------------------------------------------- suggested fixes for the doc comments (user request 2026-08-25)
# id -> lines (inclusive, new head) to replace, replacement text, and a note for jhan (not his voice).
FIX = {
  "R1-05": dict(lines=(38, 40), text=(
"One `LDTILECFG`/`TILERELEASE` pair per work region, where a work region is one\n"
"`apply_page_range` call (per attention worker, kv_head and page-range section,\n"
"and again for the pending pass); the pair itself costs ~229 cycles measured\n"
"(`begin_region()`/`end_region()`). 6962P also has AMX-INT8 and AMX-FP16; tron's\n"
"KV cache is bf16, so only `TDPBF16PS` is used."),
    note="Frequency from self_attention.hpp: begin_region at :1367-1369 / end_region at :1468 inside apply_page_range, called per kv_section from run_sections for the ready and the pending plan. Line 50 ('~229 cycles per work region') then agrees with the definition."),
  "R1-06": dict(lines=(90, 91), text=(
"- One AMX thread per physical core (Intel guidance). tron pins one attention\n"
"  worker per logical CPU from an explicit core list, so this holds only when the\n"
"  configured list contains no two SMT siblings of one physical core; tron does\n"
"  not check that."),
    note="Your triage: IGNORE. The fix states the condition instead of implying enforcement; if the measured hosts ran with sibling-free lists, add that as the second sentence."),
  "R1-03": dict(lines=(100, 102), text=(
"target is forced software attention (`USE_HW_ATTN=0`), where attention\n"
"compute is the decode wall at long context (a linear fit of the pre-AMX decode\n"
"step time against context length - 3.43 ms + 0.734 us x tokens, qwen-3-4b tp2\n"
"on delphi-3bda, 2026-08-18 - attributes 6.0 of 9.4 ms per step at ctx 8192 to\n"
"the context-proportional term, i.e. ~64%; a fit, not a trace of that cell)."),
    note="The fit constants are your P0 baseline of 2026-08-18 (exec/results/, ms/tok = 3.43 + 0.734 us x ctx; 0.734 us x 8192 = 6.01 ms of 9.44 ms = 63.7%). Confirm them against the result file before committing. His alternative ('or go'): end the sentence at 'long context.' and drop the number."),
  "R1-04": dict(lines=(119, 125), text=(
"same-binary kill-switch A/Bs against the true clean binary. Decode\n"
"(replicated campaign, 8 reps/cell, 95% CI; the table in the PR description is\n"
"the earlier 3-rep suite and differs from these cells by at most 0.3 points):\n"
"+15.3..+17.7% (canonical) / +19.7..+27.8% (mirror) at 1u/8K..8u/8K. Prefill\n"
"(3-rep suite): up to +105%. Energy per token (separate power capture at\n"
"8u/8K): -14.5% / -21.6%. Generalization (the runs cited in the PR description,\n"
"`exec/results/t4/t4-shapes.txt` and `exec/results/ci-models/mixtral-ab.txt`):\n"
"llama-3.1-8b decode +14.9% (1u/8K) / +19.7% (8u/2K); mixtral-8x7b +9.4%\n"
"canonical / +18.5% mirror (8u/8K); gpt-oss (ineligible geometry) within noise\n"
"= no regression when the gate does not fire."),
    note="Your triage: IGNORE. Two-part fix: label the primary table as the replicated campaign and say how far the PR table is from it (max |delta| = 0.3 points: 28.1 vs 27.8); make the Generalization line quote the same runs the PR description cites (llama +14.9%, mixtral +18.5%, gpt-oss 'within noise'), so both texts agree. Confirm the PR table's rep count (3) against exec/results/t4/."),
  "R2-02": dict(lines=(144, 146), text=(
"canonical path) and cost 33% KV page capacity. The arena is ordinary RAM\n"
"(`kv_bytes/2`), allocated only for a model with an AMX-eligible attention shape\n"
"(`amx_mirror_eligible` over the plugin's attention kernels - the same\n"
"`amx_attn::shape_ok` gate as the dispatch) on a host where AMX is available at\n"
"runtime, fail-soft to null; page capacity is identical with and without it."),
    note="Mirrors the condition in kv_cache.hpp maybe_allocate_mirror_arena (`if (!amx_mirror_eligible || !amx_attn::available()) return;`) and the wording the PR description already uses."),
  "R1-07": dict(lines=(167, 175), text=(
"The fast path engages only for one attention shape. The gate is one function,\n"
"`amx_attn::shape_ok` (`h/tron/kernels/amx_attn_iface.hpp`), evaluated at\n"
"compile time wherever the shape matters - the dispatch and both fast-path\n"
"blocks in `h/tron/models/self_attention.hpp`, the `save_k` write-through in\n"
"`h/tron/models/model.hpp`, and (through `amx_mirror_eligible`) the mirror-arena\n"
"allocation - plus the runtime check:\n"
"\n"
"```c++\n"
"constexpr bool amx_shape_ok =\n"
"    amx_attn::shape_ok(geometry.kv.head_size, geometry.kv_mul());\n"
"const bool amx_on = amx_shape_ok && amx_attn::available();\n"
"```"),
    note="The code block is now the exact text of self_attention.hpp:1358-1360 at 96b5a6c72. The Markdown suggestion uses a four-backtick fence because the replacement itself contains a fence."),
  "R2-01": dict(lines=(182, 184), text=(
"Eight registry families match the gate: six with hand-written C++ geometry in\n"
"`h/tron/plugins/llama.hpp` (llama-3-8b, llama-3.1-8b, mistral-7b, ministral-8b,\n"
"mixtral-8x7b, phi-4 - 40Q/10KV, the ratio is what the gate reads) and two\n"
"ingested families (qwen-3-4b-2507; granite-3.3-8b, plugin not end-to-end yet).\n"
"The list is `amx_attn::shape_ok(head_size, n_heads / n_kv_heads)` applied to\n"
"the `TRON_LLAMA_CONFIG` rows and to the ingested families' HF configs, as of\n"
"2026-08-25; re-derive it when the registry changes. Three are measured (qwen,\n"
"llama-3.1-8b, mixtral). Every other family runs the unchanged AVX path. In"),
    note="Count check from the tree: llama.hpp TRON_LLAMA_CONFIG rows with head 128 and ratio 4 = llama_3_8b, llama_3p1_8b, mistral_7b, ministral_8b, mixtral_8x7b, phi_4 (six); qwen-3-4b (32/8/128) and granite-3.3-8b (32/8/128) are ingested, geometry from HF configs, not in the tree. The replacement ends with 'In' so the following sentence at line 185 still reads."),
}
