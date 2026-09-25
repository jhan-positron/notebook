# Round-4 facts (verified by the lead, 2026-09-22 ~17:10-17:40 UTC) for the review of the THIRD codex revision

History: round 1 (2026-09-22 ~03:00 UTC) reviewed the original design (67,216 bytes): 58 retained findings F01-F59 / C01-C09.
Codex revised (83,567 bytes). Round 2 (~06:20 UTC) graded the 58 (35 resolved / 20 partly / 3 deferred) and added 64 findings
N01-N62 / M01-M08 (4 major). Codex revised again (121,774 bytes, sha 5dea1702). Round 3 (~07:00-09:30 UTC) graded the 87 open
items (64 round-2 findings + 23 round-1 residuals): 60 resolved / 25 partly / 2 deferred / 0 unresolved / 0 regressed, and added
52 findings G01-G51 (finders; G11 and G43 rejected, G52 dropped as a positive check) and H01-H03 (critic; H04 dropped as a
duplicate of G18): 1 major (G01), 27 minor, 24 notes; verdict "accept with changes", 2 of 3 judges "not yet implementable".
Codex revised a THIRD time (finalized 2026-09-22 16:43 UTC, 168,971 bytes, sha256 d2e9dabf...) and its section 9 claims to
address every round-3 finding and every round-1 residual. THIS round (round 4) reviews that third revision:
 (a) did each of the 79 open items get addressed, correctly? The 79 = 52 round-3 findings (G../H..) + 27 items round 3 graded
     partly or deferred (M01 N56 N59 F29 N11 M06 N44 F23 F57 F58 F54 F35 N20 N50 F38 N30 M04 C01 N28 C06 N33 F16 N42 F19 F20 F21 M03).
 (b) does the new text introduce new defects? (c) is the design implementable now?

Paths (absolute; the scratchpad directory is called $S below):
- $S = /tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place-issue4525/9a0c3ca8-75c1-4ba0-8af2-e929fafddbfc/scratchpad
- Design under review (HTML, for links): /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/design-new-tensor-type.html
- Plain-text extraction of the design (683 lines; READ THIS; cite as design-r4.txt:<line>): $S/design-r4.txt
  Table rows are rendered "| cell | cell |"; links are rendered "text <href>"; SVG/diagram text as plain words.
  Section starts: Short version :11; 1 Words :21-64; 2 Reviewer comments and decisions :68-131 (decision record :95-108,
  proposed issue text :110-131); 3 Add the interface to main first :135-167; 4 Indexing :171-235; 5 Interface design :239-307
  (declarations :243-245, owner and expression reads :247-253, operation table :255-260, extraction :262, row-write rule :264-275,
  callers table :277-292, build boundaries :294-301, deferred :303-307); 6 Behavior :311-380 (padding :313-337, conversions :339-353,
  arena :355-372, copies and comment sites :374-380); 7 Steps :384-452 (step table :388-395, AMX numerics fixture :397-407, child
  :409-422, child storage :424-443, worker index :445-452); 8 Verification :456-540 (behavior checks :460-472, build configurations
  :474-488, CI :490-498, log preservation :500-504, AMX proof :506-508, commands and hosts :510-518, instruction comparison :520-528,
  definition of done :530-540); 9 Disposition :544-646 (round-3 table :548-574, round-1 residual table :576-597, round-2 table
  :599-621, round-1 table :623-643, rejected candidates :644); 10 Sources :650-681 (S21 at :675).
- Every link of the design (text TAB href), 526 links: $S/design-r4-links.tsv
- Word-level diff round-3 text -> round-4 text (210 changed segments; OLD:/NEW: pairs with 6 words of context): $S/design-wdiff.txt
  Totals: 11,746 -> 15,133 words; 1,474 deleted, 4,861 inserted.
- Round-3 design text (the version round 3 reviewed; cite as design-r3.txt:<line>): $S/design-r3.txt
- Round-3 findings, compact (52 findings G../H.. with claim, evidence, recommendation, lead note and verifier corrections; the 27
  residual items with STILL NEEDED text; the 4 rejected/dropped candidates; judges; recommended edits): $S/r3-findings.md
  (grep for "### G01 " etc.; do not read whole)
- Round-2 findings, compact: $S/r2-findings.md (grep "### N13 "). Round-1 findings, compact: $S/r1-findings.md (grep "### F13").
- Verified facts of the earlier rounds: $S/facts-r3.md, $S/facts-r2.md, $S/facts-r1.md (line numbers at 2880c3aa9b and f46e48ba).
  CORRECTION to facts-r3.md: the #if TRON_AMX_DISPATCH width-check block of self_attention.hpp@2880c3aa9b spans lines 30-36
  (#if at 30, four comment lines 31-34, #error at 35, #endif at 36), not 31-37. The design's "self_attention.hpp:30-36" is RIGHT.
- Disposition batch files (one per checker batch): $S/batches/B01.md ... B17.md (list in $S/batches/batches.json)
- Round-3 review page (what codex worked from), archived: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/status/claude-review-design-new-tensor-type-r3.html (+ -r3-votes.html)
  (Until the lead archives it, the same content is at status/claude-review-design-new-tensor-type.html and -votes.html.)
- Round-2 and round-1 pages, archived: .../status/claude-review-design-new-tensor-type-r2.html (+ -r2-votes.html), -r1.html (+ -r1-votes.html)
- jhan's request to codex: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/input-2-ai/codex-add-tensor-type.md
- jhan's review request to Claude: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/input-2-ai/claude-review-add-tensor-type.md
- Ben's comments + saved issue JSON: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/evidence/github-review.json
- Project glossary codex wrote: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4525/CONTEXT.md
- Codex's own evidence for THIS revision (its files are named "round3"): .../issue4525/evidence/design-round3-{artifact-validation,
  layout-checks,render-checks,source-audit}.json (checked_at 16:43 UTC; 42 ids, 397 local links, 120 pinned source links,
  "round3_findings_covered": 52, "round1_residuals_covered": 23, checks_passed true; render at 1440/390/320 px: no missing anchors,
  no script errors, light theme, one PRE scrolls horizontally at 1440 px).
- tron git worktree (branch jhan-amx-vnniK, HEAD 30c4ac82cb = PR 4424 head): /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/tron-VNNIed-K
  Read files at pinned commits ONLY with: git -C <worktree> show <commit>:<path>  or  git -C <worktree> grep -n <pattern> <commit> -- <path>
  Commits: f46e48bab498 (design's "older source snapshot", S1-S13), 98bb8cb22f94 (main tip recorded by the design), 2880c3aa9b
  (round-2 main snapshot; S15-S17, S19-S21 cite it), 1400fa4481 (round-3 live main), 0a51385e95 (LIVE main tip, fetched 2026-09-22
  17:05 UTC), 30c4ac82cb (child = PR 4424 head; S10, S14, S18, S21 child links), c7844ca2ce (merge-base).
  NEVER checkout, reset, modify, build, or run anything in that worktree. Do not write files anywhere except your own scratch notes
  under $S/agent-notes/. Do not post to GitHub (read-only gh is fine). Do not read /home/jhan/.claude.

Live state (2026-09-22 ~17:05 UTC):
- origin/main = 0a51385e95 (2026-09-22 14:28:54 UTC, "Merge pull request #4519 ... placement-default"), 4 commits after 1400fa4481,
  12 after 2880c3aa9b. Files changed between 2880c3aa9b and live main among the design's files: h/tron/models/model.hpp (ONE line
  inserted at 891, `if (!placement) placement = hardware::all_devices();`, so every model.hpp line the design cites at or after
  892 is +1 at live main: the partner-scheduling comment 2816-2820@2880c3aa9b is 2817-2821@0a51385e95; 209-213 unchanged);
  config/test-benchmarks.json (the t_threading record only); h/tron/hardware/placer.hpp, src/tron/hardware/placer.cpp,
  t/t_expert_placement.cpp, t/t_threading.cpp, .github/workflows/publish-deb.yml, ingest/src/*.hs (TronCpp.hs: 5 lines removed).
  kv_cache.hpp, self_attention.hpp, common.hpp, amx_attn_iface.hpp, amx_attn.cpp, full.hpp, gof.hpp/gof.cpp, the 4 tests,
  t/CMakeLists.txt, GNUmakefile, CMakeLists.txt, src/tron/CMakeLists.txt, CMakePresets.json, nix/cmake-tron-test-build.nix,
  gcp-nix.yml, README.ci.md, AGENTS.md, .github/AGENTS.md, ingest/AGENTS.md, bin/slice, the tensor headers, expr.hpp, dotter.hpp,
  flake.nix, bin/lint-notes are byte-identical between 2880c3aa9b and 0a51385e95. The design pins to 2880c3aa9b and says "relocate
  these references on fetched main" (:380, :652) -> the one-line model.hpp shift is NOT a defect; a note at most.
- The design says (:159) "The round-2 review last observed main at 2880c3aa9b ... Branch from the commit returned by a new fetch"
  and (:652) "The round-3 review reports main 1400fa4481 at its saved fetch. That is review history, not this revision's baseline
  or a live check." -> consistent; do not raise "main moved" as a defect.
- Issue #4525: OPEN, title "Introduce typed KV-cache tensors for packed V and native K " (trailing space), updatedAt
  2026-09-22T00:11:35Z (unchanged since round 1), assignee jhan-positron, 0 comments. Body: intro sentence "This follows Ben's
  [tensor-interface review](...5270530330) and [API sketch](...5765866077)"; five Scope bullets (expr interface; mapping in the
  concrete view + ownership separate; preserve layouts/conversions/initialization/optimized ops/cache behavior; type cache and kernel
  boundaries; extend tests + required CI); PR order 1-3, item 3 "... Ben's [save_k worker-interface comment](...r4065141577) remains a
  separate concern there." Names "Ben" twice. No checklist, no task-list items.
- PR 4424: OPEN, draft, base main, head 30c4ac82cb, updatedAt 2026-09-21T18:59:58Z; unchanged since round 1. PR 4505: OPEN, unmerged,
  head a92a312249, updatedAt 2026-09-21T16:07:17Z (design :498 "open and unmerged at review time" RIGHT). Issue #3997: OPEN.

Design page facts (measured this round):
- 168,971 bytes (was 121,774), 0 non-ASCII bytes (glyphs are numeric entities; design-r4.txt decodes them, so curly quotes and
  arrows appear in the text extraction). 42 element ids; all 526 in-page and local links resolve; 120 GitHub blob links
  (67 at 2880c3aa9b, 34 at f46e48ba, 19 at 30c4ac82cb). Links to the review pages: 77 to claude-review-design-new-tensor-type.html
  (the LIVE page: all 52 G/H ids, the 23 round-1 residual ids of the section-9 table, N38 and a few others), 66 to -r1.html
  (F../C.. ids), 64 to -r2.html (N../M.. ids; round-3 G03 asked for exactly this repointing), 1 to -r2-votes.html.
  Every anchor the design links on the live page exists on the round-3 page. The round-4 page the lead generates MUST keep an anchor
  for every one of those ids.
- Section list (:17 nav): Terms, Review request, PR split, Layouts, Interfaces, Preserved behavior, Implementation steps,
  Verification, Review dispositions, Sources. New in this revision: Words rows Live token / Issue author / Poison / Catch2 /
  GCP Nix / Generator / qk_group (:56-62); the "Child scope" bullet (:83); the issue text rewritten as an additive draft (:112-131);
  the panel formula (:222); struct-key forward declarations (:243-245); the bf16_chunk row now adopts the inherited fallback (:258);
  "Internal storage access" names scaled_v_expr as a permitted user (:260); extraction copied from get_v (:262); append_v_row =
  sketch's store_row (:266); DMA rule (:270); page::v_packed (:284); scaled_v_expr stays in kv_cache.hpp (:286, :346, :390);
  arena wording (:366-368); comment replacement wording (:379-380); the AMX numerics fixture migration (:397-407); the two rg
  commands (:405-407); child header split and K forward declarations (:416-418); test-cost records (:420); K copy via owner
  assignment (:434); 8-lane K guard (:441); LoopyTronSpec seven assertions (:451); typed-boundary row with function names (:465);
  8-lane row (:481); Debug row (:482); log preservation (:500-504); AMX proof (:506-508); make lint-notes + lint-toolchain +
  Note convention (:514); marker rules (:518); V row unpack in the objdump list (:523); definition of done additions (:536-537);
  a round-3 disposition table (:548-574) and a round-1-residuals table (:576-597); S21 (:675).
- Section 9 coverage (lead counted): the round-3 table lists 52 ids exactly once = G01-G51 minus G11 and G43, plus H01-H03
  (G52 and H04, dropped by the lead in round 3, are not listed, which is right: the round-3 page listed them under "did not survive").
  The round-1-residuals table lists exactly the 23 ids round 3 carried as partly/deferred round-1 items (F08 F12 C01 F15 F16 F19 F20
  F21 F23 F25 F29 F30 F35 F38 F41 F48 F49 F54 F57 F58 C02 C06 C07). Note: F30, F41, F48, F49, F25, F08, F12, F15 were graded
  RESOLVED in round 3 (only 27 of the 87 stayed open); the table's heading says "with residual work after round 2", so listing them
  is not wrong. The 27 open items of THIS round are the ones in the header above.
- :644 "The rejected round-3 candidates G11 and G43 remain rejected." RIGHT (G11 = 4-lane note on t_amx_dispatch_dtype fake
  placement... see r3-findings.md; G43 see r3-findings.md). G52 (a positive check) and H04 (duplicate of G18) were dropped by the
  lead, not rejected by verification; the design need not list them.

Newly verified tron facts for claims the new text makes (all at 2880c3aa9b unless stated; all identical at live main 0a51385e95):
- Words :53 "PAGE_TOKENS_64 ... HEAD_SIZE_128 ... Both constants are declared in h/tron/kernels/amx_attn_iface.hpp. The child repeats
  them in namespace tron::k_vnni": amx_attn_iface.hpp:136-137 `inline constexpr size_t PAGE_TOKENS_64 = 64; HEAD_SIZE_128 = 128;`
  inside `namespace tron::amx_attn_h128g4` (opens :114, closes :240). Child h/tron/kernels/k_vnni.hpp@30c4ac82cb:42 `namespace
  tron::k_vnni {`, :44-45 the same two constants. RIGHT. "TRON_AMX_DISPATCH compiles the AMX kernels and dispatch, with default OFF"
  (CMakeLists.txt option, default OFF; facts-r2) RIGHT. "TRON_AMX_DISABLE=1 selects the non-AMX path": src/tron/kernels/amx_attn.cpp:61
  `std::getenv("TRON_AMX_DISABLE")`, :80 comment "read once, at that first call"; amx_attn_iface.hpp:47, :168. RIGHT, and the
  design's "Retain a separate process run with TRON_AMX_DISABLE=1 set before launch" (:508) matches the once-per-process caching.
- Words :58 Poison: t_llama_unit padding tests write quiet NaN through set_v (t_llama_unit.cpp:1919-1925, 2776-2792); child
  t_k_vnni_layout.cpp@30c4ac82cb:50-51 POISON 0xa5a5; book::fill_random (kv_cache.hpp:1058-1065) draws std::normal_distribution
  through fill_storage_slot and "bypasses partner zeroing" (its comment). RIGHT.
- Words :60 GCP Nix / RUN_TESTS: gcp-nix.yml:538 `RUN_TESTS: ${{ needs.tron-build.outputs.tests_required == 'true' || github.run_attempt > 1 }}`
  gates the Test host job; the Test FPGA job has the same variable (:605 per round 3). RIGHT.
- Words :61 Generator: ingest/src/TronCpp.hs emits the model C++; bin/ingest-cabal test runs the Haskell tests. RIGHT (round 3).
- Words :62 qk_group: child k_vnni.hpp:248 `void qk_group(const bf16* plane, ...)`; main has NO h/tron/kernels/k_vnni.hpp
  (git ls-tree at 2880c3aa9b: no k_vnni file). RIGHT.
- :77 "The issue author's reading was that the address formula belongs in the view rather than in a separate layout type":
  codex-add-tensor-type.md says "layout itself should be view of which it is how storage are presented to client. I tend to agree".
  RIGHT (this is the N11 fix; the citation given is the GitHub JSON, which does not contain jhan's reading - the round-3 N11 residual
  said an input-2-ai citation was optional).
- :112-131 issue draft: the live issue has five Scope bullets and a three-item PR order list, names Ben in the intro and in PR order
  item 3, carries three GitHub links (review 5270533330, comment 5765866077, discussion r4065141577). The draft's instructions
  (keep five bullets verbatim, add a sixth, replace the name in both places, keep all three links, "Part of #4525" is not a closing
  keyword, close after PR order item 2) match G05/G06/G07/F19/F20/F21/M06 recommendations. Check the draft's own sentences for the
  links: :118 carries the two review links inline; :129 carries the discussion link inline.
- :222 panel formula: k_vnni::index@30c4ac82cb:101 = ((((d/32)*(R/16) + t/16)*16 + (d%32)/2)*16 + t%16)*2 + d%2. Algebra:
  = ((d/32)*(R/16) + t/16)*512 + ((d%32)/2)*32 + 2*(t%16) + d%2. The design's base (s*(R/16)+c)*512 and in-panel
  ((dimension%32)/2)*32 + 2*(token%16) + dimension%2 are exactly that. PANEL_ELEMS_512 = 16 pairs x 16 tokens x 2 (k_vnni.hpp:62).
  RIGHT. "Each 16-token by 32-dimension panel is one AMX B tile": 1024 bytes = 16 rows x 64 bytes. RIGHT.
- :224 "page::set_v, the page method that writes one V row, still requires widths divisible by 32 dimensions": set_v requires
  head_size % 32 == 0 (kv_cache.hpp:1623-1673). RIGHT (F23 residual applied).
- :243-245 declarations: views.hpp:22-27 `template <typename T, bool aligned, bool dma, typename Dim, typename Stride = row_major<Dim>>
  struct view {...}` (primary, static_assert no<T>), :29-34 `struct const_view;` (same head). Both use the struct key; the fifth
  parameter is defaulted, so a forward declaration must NOT repeat the default (the design says "Declare all five view parameters
  without defaults"). bf16 is `struct bf16` (h/common/numerics/bf16.hpp:10-12). RIGHT.
- :253 "The named host-tensor constructor reads row chunk() values": tensor.hpp:271-275 rank-2 `tensor(expr<B, d0, d1, ds...> const& rhs)`
  does `std::construct_at(&data[i], rhs[i])` per row; the rank-1 `tensor(expr<B, N> const& rhs)` at :80-84 loops `store_chunk(i, rhs.chunk(i))`.
  RIGHT. So the host-tensor route exercises operator[] and chunk(), never bf16_chunk().
- :258 bf16_chunk row: expr.hpp:110-116 `bf16s bf16_chunk(size_t i) const noexcept { if constexpr (&B::bf16_chunk != &expr::bf16_chunk)
  return self().bf16_chunk(i); else return fp32s_to_bf16s(self().chunk(i)); }`. A stored bf16 widened to fp32 has a zero low half;
  fp32s_to_bf16s (bf16.hpp@f46e48ba:92-109) without TRON_IGNORE_NAN adjusts only when the exponent is all ones AND the low 16 bits are
  nonzero, so a zero low half is returned unchanged; with the macro it truncates. -> "Converting back preserves the stored bits under
  either NaN policy" RIGHT. (This adopts round-3 G12 option A, which the round-3 lead offered as one of two acceptable options.)
- :262 extraction: page::get_v(float*) at kv_cache.hpp:2412-2432: even token `_mm512_slli_epi32(both, 16)`, odd token
  `_mm512_and_si512(both, hi_16_of_32)` with hi_16_of_32 = set1_epi32(0xffff0000). get_v(bf16*) at :2446-2466 narrows with
  `_mm512_cvtepi32_epi16` at :2454 (even) and :2462 (odd, after srli 16). even_part/odd_part are private members of
  detail::scaled_v_expr (kv_cache.hpp:1996-2005, under `private:` at 1996; odd_part reads member hi_16_of_32). RIGHT.
- :260, :286, :346, :390 scaled_v_expr: defined in namespace detail inside kv_cache.hpp (:1987-...); its 16-lane constructor
  (:2066-2109 for head 64/128; more branches follow) computes `const bf16x32* tile = reinterpret_cast<const bf16x32*>(data + i * (head_size / chunk_size))`
  and accumulates `_mm512_dpbf16_ps(t, _mm512_load_si512(tile + k), scale)` with unrolled t0..t7; end = (count + 1) / 2 * 2. The
  design's "obtains the pair-tile base once through detail::v_vnni_access. Preserve its _mm512_load_si512 and _mm512_dpbf16_ps loop,
  tile unrolling, and addition order" is consistent (this is round-3 G01 option A). Whether an implementer can store the base pointer
  once and keep the existing loop: yes, the existing code already keeps `const bf16s* const data` as a member.
- :270 DMA: model.hpp:2802 save_v_impl; the 16-lane branch (:2833-2834) passes a raw pointer `&vs[ix][kv_head * geometry.kv.head_size]`;
  the 8-lane branch (:2836-2838) uses `vs[ix].as_view()`. The buffer type has as_view() with dma = false (model.hpp:1381-1383 per round-3 G41).
  So "The model source already has a view with dma = false" is defensible (the buffer can produce one); the GOF scratch (gof.cpp:203
  alignas(64) std::array on the stack) and raw-array test fixtures have none -> "Use dma = false" there. RIGHT (G41 applied).
- :280 "Update the token-zero pointer comment at self_attention.hpp:1642-1645": lines 1642-1645 = "// It reads K straight from
  storage: k0 points at token 0's K row for this (slot, kv_head), and the kernel reads the 64 rows that follow it as one block. This
  is the only place where the AMX path depends on K being stored as consecutive rows." followed at :1653-1655 by
  `const auto k0 = pg.template k<geometry.kv>(slot, kv_head, 0); amx_attn_h128g4::qk_rowmajor_128x4(k0.data, q_packed, &s_pages[0][0], page::page_size);`.
  RIGHT (N50 residual applied).
- :282 get_v callers: t/t_llama_unit.cpp get_v at :107 (inside the page_supports_uniform_kv_access probe), :819, :1575, :2038, :2539,
  :2761, :2824 -> "six raw-pointer test callers at 819,1575,2038,2539,2761,2824" RIGHT; the probe at :105-109 is handled by the
  separate "Rewrite the existing compile-time page_supports_uniform_kv_access probe" sentence. full.hpp v_head_fn lambda spans
  :2652-2657 (the get_v call is :2654-2655; :2657 is the closing `};`); the design writes 2652-2656 (one line short; trivial).
- :284 page::v_packed / :431 page::k_packed: round-3 G38 suggested v_packed; Ben's sketch uses k_packed and v_packed. Consistent.
- :296 fakes: t/t_amx_dispatch_dtype.cpp:166-190 defines available() { return true; }, begin/end_region, pack_q_group_128x4,
  qk_rowmajor_128x4(const bf16*, const bf16*, float*, size_t), weights_times_v_128x4(const bf16*, const float*, size_t, float*)
  OUTSIDE any #ifdef; the TEST_CASE is under `#ifdef TRON_AMX_DISPATCH` at :192; the #else placeholder SUCCEED at :210-213.
  "These fake bodies are unused when AMX is disabled. Keep their current placement" RIGHT (declines round-3 G14's optional move).
- :298 static_assert not requires-clause: kv_cache_fwd.hpp cannot name chunk_size / TRON_CHUNK_SIZE (defined in tron/simd/auto.hpp,
  an intrinsics header); a redeclaration with different constraints is ill-formed (round-3 G09, reproduced with g++). Adopted. RIGHT.
- :301 "The kernels-to-tensor include follows existing includes in dotter.hpp and expr.hpp": h/tron/kernels/expr.hpp:13
  `#include "tron/tensor/seq.hpp"`; h/tron/kernels/dotter.hpp:10 `#include "tron/tensor/view.hpp"`. README.code-org.md:58
  "Dependencies (aspirational)", :76 "tron/kernels depends on tron/simd", :78 "tron/tensor depends on tron/simd, tron/kernels".
  RIGHT (H03 applied). "The reviewer's sketch also places its header under h/tron/tensor" RIGHT (comment 5765866077: // h/tron/tensor/vnni.hpp).
- :336 model.hpp comment sites 209-213 ("Fix grains not to split even/odd token pairs ... page.set_v interleaves them") and
  2816-2820 ("Take care: we can't just split the items across threads ... interleaving the even-offset and odd-offset tokens")
  at 2880c3aa9b RIGHT (live main: 2817-2821).
- :379 comment sites at 2880c3aa9b: kv_cache.hpp:2055-2065 = Note [Zero-Initialized V Slots] (2066 = constructor line) RIGHT;
  1617-1620 = "If we know the chunk size, we can play a clever trick to store `v` interleaved ... But this is not compatible with
  the normal `view` machinery, so the API of access to `v` changes a little." RIGHT; 2196-2197 = "and v is indexed as
  [p/2][i/C][i%C][p%2]. See Note [Zero-Initialized V Slots] for the interleaved pair invariant." RIGHT; 565-571 = Note [Shared KV
  cache mechanics] ("... Allocation, physical addressing, page completion, append, V interleaving, and EAGLE views therefore have
  one implementation.") RIGHT. :380 amx_attn_iface.hpp:224-229 = the six-line weights_times_v_128x4 comment (decl at 230-233) RIGHT;
  self_attention.hpp:30-36 RIGHT (see the facts-r3 correction above); 1601-1605 v_data comment and 2233-2235 v_base comment RIGHT (round 3).
- :366-367 arena: book constructor allocates retained then reclaimable (kv_cache.hpp:1101-1102 `allocate_kv_group(false, ...)`,
  `allocate_kv_group(true, ...)`) and calls refresh_kv_blocks_alias() at :1114 afterwards; restore_reclaimable_kv_storage (:963-973)
  calls allocate_kv_group(true, ...) at :968 then refresh_kv_blocks_alias() at :971. allocate_kv_group defined at :1199.
  -> "Use the arena pointer just installed by allocate_kv_group, not kv_blocks_alias, which is refreshed later" RIGHT.
  kv_block() accessor (:1277-1300, requires uniform_geometry): `if constexpr (layout_t::uniform_reclaimability)` indexes
  `blocks[(slot.i * n_kv_heads + kv_head) * n_pages + pg]` from kv_blocks_alias (:1284-1289); else addresses each slot through
  slot_base(kv_storage_offset(physical_slot)) (:1290-1299). -> "Cross-slot array indexing exists only in the uniform-reclaimability
  accessor" RIGHT (G42 applied). for_each_active_slot (:1243-1249) calls the lambda for slot < logical_slot_count() = logical slots;
  fill_random (:1060-1061) forms kv_storage_offset(slot). -> :367 RIGHT (G19/M04 applied). storage_location at :727-734 RIGHT.
- :56 "live count ... returned by page::count()": page::count() at kv_cache.hpp:1492 (`size_t count() const noexcept`). RIGHT.
- :397-403 AMX numerics fixture: t/t_amx_numerics.cpp@2880c3aa9b: bf16_rne(float) at :42 (round-to-nearest-even helper);
  `struct alignas(64) qk_inputs { tron::bf16 k[PAGE_TOKENS_64 * HEAD_SIZE_128]; tron::bf16 q[...]; }` at :65-68; the QK case
  (:144-185) calls `qk_rowmajor_128x4(in->k, q_packed, &s_amx[0][0], PAGE_TOKENS_64)` at :156-157 with the raw array; the PV case
  (:187-260) builds `std::vector<tron::bf16> v_page(PAGE_TOKENS_64 * HEAD_SIZE_128)` at :203 by hand with the pair formula
  (:204-210) from `std::vector<float> v` (:199) via bf16_rne, and calls `weights_times_v_128x4(v_page.data(), &exp_rows[0][0], PAGE_TOKENS_64, o_amx)`
  at :225-226; both cases `WARN("AMX unavailable on this host - ... precision check skipped"); return;` when available() is false
  (:146-147, :190-191); the #else placeholder SUCCEED at :262-263. -> the fixture migration text and the AMX-proof text (:506-508) RIGHT.
  A v_vnni_tensor<64,128> is 64 x 128 x 2 bytes = 16,384 bytes RIGHT.
- :407 rg commands: word-boundary pattern over h src t, plus `rg -n "reinterpret_cast" h/tron/models/kv_cache.hpp h/tron/tensor/v_vnni.hpp`
  (G21 applied). Fine.
- :414 "main's restructured src/tron/CMakeLists.txt, where the child's build-option block must be placed": child
  src/tron/CMakeLists.txt@30c4ac82cb:201-213 has the TRON_K_VNNI block (`if(TRON_K_VNNI) ... message(FATAL_ERROR "TRON_K_VNNI requires
  TRON_AMX_DISPATCH=ON") ... target_compile_definitions(tron PUBLIC TRON_K_VNNI)`); top-level CMakeLists.txt@30c4ac82cb:49 declares
  the option (default OFF). RIGHT.
- :416 child helpers: k_vnni.hpp@30c4ac82cb `namespace detail` :109-133 pair_base (:113 writable, :119 const), pair_row_offsets (:126);
  second detail block :148-180 transpose_16x16_epi32 (:153); scatter_row :139, store_block :194, gather_row :221, qk_group :248;
  layout_on :93/:96; index :101. RIGHT. The child's h/tron/kernels/k_vnni.hpp includes only <cstddef>, <cstdint>, <cstring>,
  <immintrin.h>, <type_traits>, common/attributes.hpp, common/numerics/bf16.hpp, common/numerics/fp16.hpp (:32-40); the child's
  kv_cache.hpp includes "tron/kernels/k_vnni.hpp" at :27 -> ":417 The cache drops its include of this kernel header" describes a
  real include. RIGHT. "The reviewer's sketch used one header, h/tron/tensor/vnni.hpp" RIGHT (N59/G48 applied).
- :420 test-cost records: child diff c7844ca2ce..30c4ac82cb of config/test-benchmarks.json changes exactly three rows, all inside the
  "granite_rapids_6962p" block (block starts at line 365 of the child file; hunks at 423 and 475): t_llama_unit 3.38 -> 13.436 s
  (1 slice), t_amx_numerics 0.737 -> 0.804 s, t_k_vnni_layout added (0.709 s). RIGHT (G24 applied). bin/slice: `bench --update`
  and `--new` subset the manifest (:2012-2022, :1149 "Re-run `bin/slice bench --update <test>`"); `bench --check` reports
  "bench entries missing from every platform" / "missing from platform" (:1810-1832) -> "--check detects missing records, not stale
  timings" RIGHT. Platform keys: genoa96, genoa32, granite_rapids_6960p, granite_rapids_6962p RIGHT. SLICE_OPTIONS = [1, 2, 4] RIGHT.
- :434 "replace the whole-page K memcpy at child kv_cache.hpp:2107 with dst_block.k = src_block.k in the packed branch":
  kv_cache.hpp@30c4ac82cb:2107 `memcpy(dst_block.k, src_block.k, sizeof(dst_block.k))` inside copy_storage_slot (2093-2141). RIGHT (G44 applied).
- :441 "The child's cache header rejects packed K at 8 lanes. Its CMake option also requires AMX dispatch": kv_cache.hpp@30c4ac82cb:35-39
  `#if defined(TRON_K_VNNI) && TRON_CHUNK_SIZE != 16 ... #error "TRON_K_VNNI requires TRON_CHUNK_SIZE == 16"`; src/tron/CMakeLists.txt@30c4ac82cb:209-211
  FATAL_ERROR. RIGHT (G47 applied).
- :451 LoopyTronSpec.hs@30c4ac82cb: case 1 :2801 `Txt.count "outer_state.template save_k<" cpp `shouldBe` 1`, :2808-2811 main call
  `attentionCallPrefix "save_k" geometry 0 <> "q_batch->outer_batch,k,n_workers);"`, :2812 `count "outer_state.template save_k_helper<" ... 1`,
  :2813-2818 helper call `attentionCallPrefix "save_k_helper" geometry 0 <> "q_batch->outer_batch,k,worker_ix,n_workers);"`;
  case 2 :3225 count save_k< 1, :3227 `",k,n_workers);" isInfixOf`, :3231 count save_k_helper< 1, :3232 `",k,worker_ix,n_workers);" isInfixOf`.
  After the merge: both save_k< counts 2; save_k_helper< counts 0 (or deleted); main tails ",k,0,n_workers);"; the case-1 helper
  prefix becomes save_k; helper tails unchanged, so :3232 stays true. Seven changing assertions (:2801, :2808, :2812, :2813-2816,
  :3225, :3227, :3231). The design's sentence matches (G23 applied). "Both save_k< counts become 2 calls" RIGHT.
  gcp-nix.yml:203 job "Test ingest", :235-237 step "Run Haskell ingest tests": `nix build .#checks.x86_64-linux."tron-ingest:test:ingest-tests" -L`.
  RIGHT (design omits -L; fine). GNUmakefile:762 format-haskell target exists (H02 applied); ingest/AGENTS.md exists.
- :465 typed-boundary row: `namespace tron::amx_attn_h128g4` RIGHT; t_llama_unit.cpp:84-123 hold the requires-expression constants
  (:84 `template <typename Page> constexpr bool page_k_accepts_raw_index = requires...`), :316 `TEST_CASE("attention operations resolve
  to typed KV slots", "[kv_data]")` (case body to ~342). RIGHT (M03 + G30 applied).
- :481 8-lane row: t_amx_dispatch_dtype.cpp #else placeholder at :210-213. RIGHT (M01 applied).
- :482 Debug row: GNUmakefile:80 `BUILD_TYPE := RelWithDebInfo`; the only configure stamp is PRESET_STAMP (gen/.preset_stamp, :299-303),
  which tracks CMAKE_PRESET only; configure recipes at :532/:541/:553 pass -DCMAKE_BUILD_TYPE=$(BUILD_TYPE). -> "Make's configuration
  stamp does not track BUILD_TYPE" RIGHT (G27 applied). CMakePresets native binaryDir = gen (round 3).
- :502-504 logs: bin/slice:4181 `print(f"Logs: {run_dir}", file=sys.stderr)`; allocate_run_dir (:2751-2775) names run-NNNN and prunes
  while len(existing) >= RETENTION with RETENTION = 10 (:114). gcp-nix.yml:546 step "Restore exact Nix test runtime"; the runtime
  script bin/ci/tron-build/test_runtime.py:134 prints `Preparing test runtime: {canonical_build}; environment={canonical_environment}`
  (confirmed in a real Test host job log from 2026-09-19: "Preparing test runtime: /nix/store/...-testRuntime; environment=/nix/store/...";
  "Logs: /opt/positron/runners/delphi-3af6-0/_work/tron/tron/logs-delphi-3af6/run-0000"). :573 runs `$TRON_TEST_ENVIRONMENT/bin/tron-test-host`;
  :574-575 "Upload alderaan.log" `if: failure() && env.RUN_TESTS == 'true'`. Test host runner labels [self-hosted, fpga, test, avx512]
  (:535). Every job checks out with actions/checkout@de0fac2e (v6) with no clean: input, whose default clean deletes untracked
  logs-<host>/ at the next job (round-3 G25 correction) -> "The next checkout cleans the workspace" RIGHT. "Set up job" is GitHub's own
  first step of every job (not in the yml) and names the runner. RIGHT.
- :514 "make lint-notes": GNUmakefile:675-681 (uses tron-lint-notes if on PATH, else bin/lint-notes with ghc+cabal, else error).
  "The exact CI toolchain-lint check is nix build .#checks.x86_64-linux.lint-toolchain -L --no-update-lock-file": bin/ci/run-lint-checks.sh:7
  default check_ref `.#checks.x86_64-linux.lint-toolchain`, :18 `nix build "${check_ref}" -L --no-update-lock-file --no-link`; the
  lint-toolchain runCommand (flake.nix:2087-2236) ends with `make lint-notes` (:2233). RIGHT (H01 applied). Note convention:
  bin/lint-notes:21-31 "Note [Name of the concept]" underlined with "~~~", references "See Note [Name of the concept]". RIGHT.
- :518 marker: exec/bill-share.sh: marker /bill-has-instance-0,2; "Our second-half campaigns run either way; they never look at the
  marker"; `take` removes it (refused if Bill is active), `release` re-creates it. -> "Second-half runs do not change the marker. Taking
  the whole host requires user direction, and release restores the marker." RIGHT (G28 applied; the [Instance-sharing protocol] link
  points at ../../../exec/bill-share.sh, which exists).
- :523 V row unpack: get_v(bf16*) narrowing at kv_cache.hpp:2454 and :2462, callers t_llama_unit.cpp:819, :1575, :2038 (F38 residual
  applied; the two bf16 callers are :819 and :2038, :1575 passes value.data() of a bf16 array). "The production caller in full.hpp is
  in another binary" RIGHT.
- :666 S12: rule files AGENTS.md (last main change 2026-09-09), t/AGENTS.md (2026-09-14), .agents/skills/run-tron-tests/SKILL.md
  (2026-08-25) -> "The latest main change to any of these files was t/AGENTS.md on 14 September 2026" RIGHT; blob identity at the
  five commits incl. c7844ca2ce RIGHT (round 3).
- :492 "Adding -DTRON_AMX_DISPATCH=ON to cmake_args in nix/cmake-tron-test-build.nix:79-103": the cmake_args list spans :79-103. RIGHT (G29/F16 applied).
- Round-2 and round-3 facts still valid: TRON_IGNORE_NAN in every non-Debug GCC/Clang build (src/tron/CMakeLists.txt:292-295, :314-318);
  NaN table 0x7F800001 -> 0x7F80 / 0x7F81 / 0x7F80; kv_block layout (:2191-2202) and kv_block_alignment; set_v/get_v requires;
  scaled_v_expr head sizes 64/128/256/512; page_supports_uniform_kv_access is test-local (t_llama_unit.cpp:105-109, asserted :483, :779);
  kernel declarations amx_attn_iface.hpp:219-222 and :230-233; TRON_AMX_DISPATCH #error block; BUILD_NATIVE/AVX512 probe; presets;
  README.ci.md required checks (:76-79); gcp-nix.yml source_hash and passage marker; testlog.cpp Catch2 lines; Ben's sketch text.

TRAPS for this round:
- Facts-file summaries can seed false findings. ALWAYS confirm against the primary source (git show at the named commit, design-r4.txt,
  Ben's JSON) before asserting. facts-r3.md has one known error (self_attention.hpp 31-37; the block is 30-36).
- The design's [Fnn]/[Cnn] citations point at the ROUND-1 page (-r1.html); [Nnn]/[Mnn] at the ROUND-2 page (-r2.html); [Gnn]/[Hnn]
  and the 23 round-1 residual ids of the section-9 table at the LIVE page (round 3's content, to be archived as -r3.html). Section 9
  "[Words]", "[Access contract]" etc. links point at anchors inside the design itself.
- The design explicitly compiled nothing and ran nothing (:458); that is not a finding. It posts nothing and edits no issue (:646, :681);
  the issue-body items are "prepared text for the assignee to apply" - judge the text, not whether the issue changed.
- Round-3 verifier corrections narrowed several round-3 findings (G01 = ambiguity not contradiction; G22 = a permitted route was
  derivable, the gap was which route; G26 = only the cost-record item; G31 = F38 only, not F35; G41 = GOF scratch and fixtures only;
  G14 and G12 were OPTIONS the design may adopt or decline). Codex was told to follow the corrections. Grade against the CORRECTED
  recommendation, which the batch files carry. Where the round-3 lead offered two options (G01 A/B, G12 A/B, G14 adopt/decline,
  N59/G48 revert or state the choice), choosing either option with the reason stated resolves the item.
- Do not re-raise the 18 rejected candidates (round 1: F06 F07 F09 F18 F22 F33 F36 F44 F53 F55; round 2: N10 N19 N21 N26 N47 N54;
  round 3: G11 G43) or the two dropped ones (G52, H04) without NEW evidence.
- "resolved" means the design TEXT now specifies what the (corrected) recommendation asked and every checkable fact in the fix is right.
  The design does not have to implement or run anything to resolve a finding; "implementation must still do X" is a residual only when
  the recommendation asked the design text for something it still lacks.
- Line numbers: the design cites 2880c3aa9b for main and 30c4ac82cb for the child. Live main 0a51385e95 differs from 2880c3aa9b in
  model.hpp by one inserted line at 891 (cited comment 2816-2820 is 2817-2821 live). Not a defect: the design tells the implementer to
  relocate on fetched main. Mention it only as a note if at all.
- One PRE code block scrolls horizontally at 1440 px (codex's own render check). Not a defect by itself.
- Plain-English rules for jhan's project apply to the REVIEW page we write, not to grading the design; do not grade the design's prose
  style except where a term is undefined or a sentence is ambiguous enough to mislead an implementer.
- The design grew by 3,387 words; much of it is section 9 (three tables) and S21 (31 new link labels). Section 9 claims are only
  claims: a "Design response" cell counts only if the BODY text carries it.

CORRECTIONS after the round (lead, 2026-09-22 ~20:00 UTC):
- The entry ":270 DMA" above is WRONG where it says the buffer type has as_view() with dma = false (model.hpp:1381-1383 defines
  attention_buffer_width and fixes no flag). The production V save buffer is intermediate_t = indexed_vector<token_job_id, btensor_t<width>>
  (model.hpp:736), btensor_t = plugin_t::btensor_t (:733), hardware::btensor = dmatensor<bf16,...> (h/tron/hardware/btensor.hpp:21), and the
  rank-1 dmatensor has static constexpr bool dma = true (h/tron/hardware/dmatensor.hpp:173; as_view() at :223-228). tp1/tp2/tp4, perm_tp*,
  host_bf16 and host_fp16 therefore carry dma = true; only the host executor's tensor (common.hpp:100; tensor.hpp:71-75) carries false, and
  that executor is what the t_llama_unit model cases use. The design's sentence "The model source already has a view with dma = false" is
  wrong for every production executor (round-4 J09; G41 partly).
- The entry ":523 V row unpack" above names :819 and :2038 as the bf16 get_v callers. The bf16 callers are :819 and :1575 (std::array<bf16>
  data()); :2038 passes alignas(64) float temp[] and takes the float overload (round-4 J37).
