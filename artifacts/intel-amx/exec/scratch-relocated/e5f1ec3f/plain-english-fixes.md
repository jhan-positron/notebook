# Plain-English check of Ben-PR4956.html (prose only)

Checked file: /home/jhan/workspace/intel-AMX/random/Ben-PR4956.html (same prose as /home/jhan/workspace/intel-AMX/exec/pr5047-20261020/page_template.html).
Ignored: SVG text, CSS, and the generated placeholder sections "Builds", "Tests of the head builds", "Token identity", "Throughput and prefill".

**Short version.** 58 rule violations: Rule 1 x14, Rule 2 x14, Rule 6 x10, Rule 7 x3, Rule 8 x17. Plus 3 grammar fixes outside the numbered rules. Rules 3, 4 and 5 have zero violations. The page has no em-dashes or en-dashes, and none of the banned words (convoy, refund, "in disguise", swept/sweep) appear.

Rows are in page order. Line numbers are from Ben-PR4956.html. Original phrases are exact for text search (HTML inline markup included). Three fixes are multi-line and sit in blocks A, B, C under the table. Where one row carries two or three rule numbers, each number counts one violation in the totals above.

| # | Line | Rule | Original phrase | Fix |
|---|---|---|---|---|
| 1 | 69 | 1 | `Perf campaign state:` | `Performance campaign state:` |
| 2 | 72 | 1 | `are older main code rather than PR 4956 code` | `are older code from main (tron's trunk branch) rather than PR 4956 code` |
| 3 | 72 | 1 | `and the 3bda measurement shows {{PERF_VERDICT}}` (template text; the page shows `pending` in place of the placeholder) | `and the throughput measurement on 3bda (the Intel test server delphi-3bda) shows {{PERF_VERDICT}}` |
| 4 | 82 | 1 | insert after `<dt>tron, runtron</dt><dd>tron is the inference program under test. runtron is its command-line tool.</dd>` | `<dt>3bda</dt><dd>delphi-3bda, the Intel test server where the four binaries are built and the throughput test runs.</dd>` |
| 5 | 84 | 2 | `Its base branch is PR 4956's branch, so merging it changes PR 4956.` | `Its base branch is PR 4956's branch. Merging it therefore changes PR 4956.` |
| 6 | 85 | 1 | `ON: they are stored in the VNNI pair-interleaved layout, the format the AMX tile multiply wants for its right operand.` | `ON: they are stored in the VNNI layout (VNNI = Vector Neural Network Instructions, Intel's name for the layout that interleaves pairs of rows), the format the AMX tile multiply takes as its right operand.` |
| 7 | 86 | 1 | `A plane is the K or the V storage of one page and one KV head (64 tokens × 128 dimensions × 2 bytes = 16 KiB for K).` | `A plane is the K or the V storage of one page and one KV head. A KV head is one key/value head, shared by several query heads. For K, a plane is 64 tokens × 128 dimensions × 2 bytes = 16 KiB.` |
| 8 | 88 | 1 | `Both are CPU paths, as opposed to the FPGA.` | `Both are CPU paths, as opposed to the FPGA (field-programmable gate array, the accelerator card).` |
| 9 | 90 | 1 | `scores a query group against one VNNI page` | `scores a query group (the query heads that share one KV head) against one VNNI page` |
| 10 | 94 | 1 | insert before `<dt>base, head, basev, headv</dt>` ("arms" is first used in the TPS entry on line 95, "cell" on line 336) | `<dt>cell, arm</dt><dd>A cell is one model-and-shape configuration of the 3bda test, for example llama-3.1-8b with 8 users at prompt 1024. An arm is one of the binaries run inside a cell.</dd>` |
| 11 | 131 | 2 | `PR 5047 is two commits on top of the PR 4956 head, so its diff is exactly what jhan would be accepting into PR 4956.` | `PR 5047 is two commits on top of the PR 4956 head. Its diff is therefore exactly what jhan would be accepting into PR 4956.` |
| 12 | 138 | 2 | `Test, Test host, Test FPGA and Benchmark were skipped because the build failed.` | `The build failed. GitHub therefore skipped Test, Test host, Test FPGA and Benchmark.` |
| 13 | 140 | 1 | `PR 4956's own CI at its head` | `PR 4956's own CI (continuous integration, the same GitHub checks) at its head` |
| 14 | 157 | 8 | `(<code>ea3122b914</code>, 2026-09-11); two lines date from Alexey's 2024-2025 page loop.` | `(<code>ea3122b914</code>, 2026-09-11). Two lines date from Alexey's 2024-2025 page loop.` |
| 15 | 162 | 6 | `It is the price Ben chose for the rule "layout-specific access stays in the cache"` | `It follows from the rule Ben chose, "layout-specific access stays in the cache"` |
| 16 | 208 | 2 | `The dotter and the two kernels are now called from <code>kv_cache.hpp</code>, which therefore includes` | `The dotter and the two kernels are now called from <code>kv_cache.hpp</code>. That header therefore includes` |
| 17 | 208 | 7, 1 | the figcaption text from `Still outside the page:` to `and now copies the row.</figcaption>` (five points in one caption, "PV kernel" undefined) | block A |
| 18 | 238 | 8 | `Before, two control flows shared one function, and the row-major one needed a dotter array and a lazy row view that the VNNI flow replaced with placeholder lambdas returning 0 and <code>[[maybe_unused]]</code> variables (base 1915-1933). After, the layout question is asked once per page, after selection: VNNI slots go to <code>qk_group</code>; row-major slots build four dotters and score each set bit in ascending order (<code>countr_zero</code>), the same order the old loop used.` | `Before, two control flows shared one function. The row-major flow needed a dotter array and a lazy row view. The VNNI flow replaced them with placeholder lambdas returning 0 and <code>[[maybe_unused]]</code> variables (base 1915-1933). After, the layout question is asked once per page, after selection. VNNI slots go to <code>qk_group</code>. Row-major slots build four dotters and score each set bit in ascending order (<code>countr_zero</code>), the same order the old loop used.` |
| 19 | 240 | 8 | `are now built only when at least one token is live, while the base built the dotter array before the loop even when nothing was live (base 1915-1924 versus head <code>kv_cache.hpp:1993-1998</code>).` | `are now built only when at least one token is live. The base built the dotter array before the loop even when nothing was live (base 1915-1924 versus head <code>kv_cache.hpp:1993-1998</code>).` |
| 20 | 251 | 8 | `Compile-time gate <code>eligible</code> only; <code>apply_dense_amx_page</code> returns <code>bool</code> and calls <code>pg.try_score_k_amx(...)</code>, which returns <code>false</code> for a VNNI slot and otherwise calls the same kernel with <code>kv_block.k_view()</code> (head 1757-1759, 2015-2030).` | `Compile-time gate <code>eligible</code> only. <code>apply_dense_amx_page</code> returns <code>bool</code> and calls <code>pg.try_score_k_amx(...)</code>. That call returns <code>false</code> for a VNNI slot. Otherwise it calls the same kernel with <code>kv_block.k_view()</code> (head 1757-1759, 2015-2030).` |
| 21 | 252 | 8 | `Three branches: bf16 VNNI row stored directly; other activation types converted to bf16 then stored; row-major <code>pg.k(...).set(kout)</code> (base 3097-3115).` | `Three branches: (1) a bf16 VNNI row stored directly, (2) other activation types converted to bf16 and then stored, (3) row-major <code>pg.k(...).set(kout)</code> (base 3097-3115).` |
| 22 | 292 | 7, 2 | the whole paragraph from `<p>With <code>page::k</code> gone,` to `expose the same operations.</p>` (five points in one paragraph, one "because" clause) | block B |
| 23 | 300 | 6 | `two control flows braided into one loop.` | `two control flows mixed in one loop.` |
| 24 | 301 | 6 | `reached into page storage with a layout-specific accessor` | `read or wrote page storage through a layout-specific accessor` |
| 25 | 302 | 6 | `<code>page::k()</code> handed out a writable row view of the plane to any caller, including tests that poked <code>k(...)[0]</code>.` | `<code>page::k()</code> gave any caller a writable row view of the plane, including tests that wrote single elements through <code>k(...)[0]</code>.` |
| 26 | 309 | grammar | `<span class="pill bad">Does not compile</span> the GitHub "Build Tron" check` | `<span class="pill bad">Does not compile</span> in the GitHub "Build Tron" check` |
| 27 | 309 | 2, 6 | `Everyone: CI is red, so Test, Test host and Test FPGA did not run on this head.` | `Everyone. The CI build fails, and Test, Test host and Test FPGA did not run on this head.` |
| 28 | 310 | 2, 1 | `V was already copied this way, so the staging cost roughly doubles its memory traffic per token but stays tiny next to the DMA and the attention itself.` | `V was already copied this way. The staging now moves about twice the bytes per token. That is still small next to the DMA (the direct-memory-access transfer to the FPGA) and the attention itself.` |
| 29 | 311 | 8 | `Now every (query, page) pair with a packed Q evaluates <code>is_dense_amx_page</code> (five comparisons, head 1710-1722) and, when the page is dense, enters <code>apply_dense_amx_page</code>, allocates its 1 KiB score tensor on the stack and returns at <code>try_score_k_amx</code>.` | `Now every (query, page) pair with a packed Q evaluates <code>is_dense_amx_page</code> (five comparisons, head 1710-1722). When the page is dense, the call enters <code>apply_dense_amx_page</code>, allocates its 1 KiB score tensor on the stack and returns at <code>try_score_k_amx</code>.` |
| 30 | 311 | 8 | `Expected small; PR 4957 removes it by adding the VNNI reader.` | `Expected to be small. PR 4957 removes it by adding the VNNI reader.` |
| 31 | 312 | 6 | `bf16 rows take a detour on the VNNI store path` | `bf16 rows pass through an extra buffer on the VNNI store path` |
| 32 | 313 | 8 | `The cache header depends on kernel headers; before, only the attention code did.` | `The cache header now depends on kernel headers. Before, only the attention code did.` |
| 33 | 313 | 6 | `Compile time and header hygiene. No run-time effect.` | `Compile time and header dependencies. No run-time effect.` |
| 34 | 314 | 2 | `<code>page_k_packed_accepts_geometry</code> still probes <code>page.k_packed</code>, which no longer exists, so the concept is always false and the <code>STATIC_REQUIRE_FALSE</code> on it no longer checks anything.` | `<code>page_k_packed_accepts_geometry</code> still probes <code>page.k_packed</code>, which no longer exists. The concept is therefore always false. The <code>STATIC_REQUIRE_FALSE</code> on it no longer checks anything.` |
| 35 | 315 | 2 | `The view semantics it tested are gone with the API, so nothing is left untested that still exists.` | `The view semantics it tested are gone with the API. Nothing that still exists is left untested.` |
| 36 | 324 | 1 | `reports gpt-oss-120b tp4 generation +7.18 % and llama rows within ±0.5 %.` | `reports gpt-oss-120b tp4 (tensor-parallel degree 4) generation throughput +7.18 % and llama rows within ±0.5 %.` (confirm what tp counts, cards or engines, before pasting) |
| 37 | 328 | 2, grammar | `It has no AMX, so the dense-page kernel path that commit 1 and 2 touch on Intel is not exercised there.` | `It has no AMX. The dense-page kernel path that commits 1 and 2 touch on Intel therefore does not run there.` |
| 38 | 330 | 2 | `The option never applies to it, and the dense AMX path never applies to it, so on that model commit 1 changes only the dotter loop's control flow.` | `The option never applies to it, and neither does the dense AMX path. On that model, commit 1 changes only the dotter loop's control flow.` |
| 39 | 336 | 7, 8, 6, 1 | the whole paragraph from `<p>Design. Four runtron binaries` to `<code>exec/results/pr5047-20261020/</code>.</p>` (four points in one paragraph, one 40-word sentence, "back to back", cell names l8b/q4b/gptoss/pN/cpu/fpga undefined) | block C |
| 40 | 340 | 1, 8 | `The AMX dense path plus the dotter tail page; the option applies (128-dim heads).` | `The AMX dense path plus the dotter tail page (the last, partly filled page, scored by the dotter). The option applies (128-dim heads).` |
| 41 | 341 | 8 | `The FPGA staging copy; the option applies.` | `The FPGA staging copy. The option applies.` |
| 42 | 342 | 2, 8 | `The FPGA staging copy on 64-dim heads; the option never applies, so no ON arms.` | `The FPGA staging copy on 64-dim heads. The option never applies to this model, and there are no ON arms.` |
| 43 | 359 | 2, 6 | `The build is red: convert the loop at <code>t/heterogeneous_scheduler_compile.cpp:687-689</code> (for example a <code>set_k_tag</code> per token, or one <code>set_k_row</code> of a zero row per token), then CI's Test lanes can run.` | `The build fails. Convert the loop at <code>t/heterogeneous_scheduler_compile.cpp:687-689</code> (for example one <code>set_k_tag</code> per token, or one <code>set_k_row</code> of a zero row per token). CI's Test lanes can then run.` |
| 44 | 361 | 8 | `The qwen3-4b and gpt-oss-120b cells of level 7 give the measured answer; if it costs nothing measurable, keeping one path is the simpler code.` | `The qwen3-4b and gpt-oss-120b cells of level 7 give the measured answer. If the copy costs nothing measurable, keeping one path is the simpler code.` |
| 45 | 363 | 6, grammar | `The bf16 detour in <code>set_k_row(expr)</code> for VNNI slots (<code>kv_cache.hpp:2052-2066</code>): a <code>if constexpr` | `The extra bf16 buffer in <code>set_k_row(expr)</code> for VNNI slots (<code>kv_cache.hpp:2052-2066</code>): an <code>if constexpr` |
| 46 | 364 | 8 | `and the compile-time "temporary gate"; they would need the new names (<code>score_k</code>, <code>try_score_k_amx</code>).` | `and the compile-time "temporary gate". They would need the new names (<code>score_k</code>, <code>try_score_k_amx</code>).` |
| 47 | 365 | 2, 8 | `The removal of <code>page::k</code> touches Rhys's cache API and tests; he may want to see it, since PR 4956 left those accessors in place.` | `The removal of <code>page::k</code> touches Rhys's cache API and tests. PR 4956 left those accessors in place. Rhys may want to see the removal.` |
| 48 | 373 | 8 | `(base <code>a5697f86d3</code>); <code>git diff a5697f86d3..ade89a9d9c</code>` | `(base <code>a5697f86d3</code>). Commands: <code>git diff a5697f86d3..ade89a9d9c</code>` |
| 49 | 375 | 8 | `covers every changed line of both commits; this page is the top-down companion.` | `covers every changed line of both commits. This page is the top-down companion.` |

Tally of the 58 rule violations by row (a row with several rule numbers counts once per number):

- Rule 1 (14): rows 1, 2, 3, 4 (with 3), 6, 7, 8, 9, 10, 13, 17 (PV kernel), 28 (DMA), 36, 39 (cell names), 40 (tail page). Rows 3 and 4 fix the same term (3bda), so they count once.
- Rule 2 (14): rows 5, 11, 12, 16, 22, 27, 28, 34, 35, 37, 38, 42, 43, 47.
- Rule 6 (10): rows 15, 23, 24, 25, 27, 31, 33, 39 ("back to back"), 43, 45.
- Rule 7 (3): rows 17, 22, 39.
- Rule 8 (17): rows 14, 18, 19, 20, 21, 29, 30, 32, 39 (long sentence), 40, 41, 42, 44, 46, 47, 48, 49.
- Grammar, not a numbered rule (3): rows 26, 37, 45.

## Block A (row 17, line 208)

End the figcaption after `(head 28-31).` with `</figcaption>`, delete the three sentences that followed it inside the caption, and put this list right after the closing `</figure>` of that figure:

```html
<ul>
<li>Still outside the page: the AMX query pack, <code>is_dense_amx_page</code> (head 1710), the softmax step and the PV kernel (the multiply of the softmax weights by V).</li>
<li>Still a raw row inside the cache: <code>kv_block::k_view</code> and <code>k_at</code> (head 2589-2607), which the four page methods use for row-major slots.</li>
<li>The arrow from the scheduler is the one whose work changes for the production (row-major) build. It used to return a pointer into the page and now copies the row.</li>
</ul>
```

The exact caption text to delete (one string):

```html
 Still outside the page: the AMX query pack, <code>is_dense_amx_page</code> (head 1710), the softmax step and the PV kernel. Still a raw row inside the cache: <code>kv_block::k_view</code> and <code>k_at</code> (head 2589-2607), which the four page methods use for row-major slots. The arrow from the scheduler is the one whose work changes for the production (row-major) build: it used to return a pointer into the page and now copies the row.
```

## Block B (row 22, line 292)

Replace the whole paragraph. The exact original:

```html
<p>With <code>page::k</code> gone, every test that wrote or read one K element through it needed another way. Ben adds <code>t/kv_cache_helpers.hpp</code> with two helpers: <code>test::set_k_tag</code> writes a whole row whose first element is the tag and the other 127 elements are zero, and <code>test::k_tag</code> reads the row back and returns the first element. 24 call sites in two test files switch to them. The test that checked view identity and lazy views ("page K views preserve geometry and row addressing") becomes a store-and-load round trip of elements 0 and 127 ("page K rows ..."). Two <code>#ifdef TRON_K_VNNI</code> branches in <code>t_llama_unit.cpp</code> disappear because both layouts now expose the same operations.</p>
```

The replacement:

```html
<p>With <code>page::k</code> gone, every test that wrote or read one K element through it needed another way.</p>
<ul>
<li>Ben adds <code>t/kv_cache_helpers.hpp</code> with two helpers. <code>test::set_k_tag</code> writes a whole row whose first element is the tag and the other 127 elements are zero. <code>test::k_tag</code> reads the row back and returns the first element.</li>
<li>24 call sites in two test files switch to them.</li>
<li>The test that checked view identity and lazy views ("page K views preserve geometry and row addressing") becomes a store-and-load round trip of elements 0 and 127 ("page K rows ...").</li>
<li>Two <code>#ifdef TRON_K_VNNI</code> branches in <code>t_llama_unit.cpp</code> disappear. Both layouts now expose the same operations, and the test no longer needs to tell them apart.</li>
</ul>
```

## Block C (row 39, line 336)

Replace the whole "Design." paragraph. The exact original:

```html
<p>Design. Four runtron binaries were built on delphi-3bda with one recipe (plain shell, clang 19.1.7, preset native, <code>BUILD_INGEST_MODELS=ON</code>, <code>TRON_AMX_DISPATCH=ON</code>): the PR 5047 base and head, each with the option OFF and ON. The option-OFF pair is what every preset ships. The option-ON pair is the configuration PR 4956 adds. Each cell runs its arms back to back, 4 repetitions, the arm order reversed on even repetitions, on our half of the machine (socket 1, FPGA cards 90/93/b9/bc), with <code>TRON_ATTN_STATS=1</code> so the exit report says which path scored each K token. Scripts: <code>exec/pr5047-20261020/</code> (README.md there). Results: <code>exec/results/pr5047-20261020/</code>.</p>
```

The replacement:

```html
<p>Design.</p>
<ul>
<li>Builds: four runtron binaries were built on delphi-3bda with one recipe (plain shell, clang 19.1.7, preset native, <code>BUILD_INGEST_MODELS=ON</code>, <code>TRON_AMX_DISPATCH=ON</code>): the PR 5047 base and head, each with the option OFF and ON. The option-OFF pair is what every preset ships. The option-ON pair is the configuration PR 4956 adds.</li>
<li>Runs: each cell runs its arms one after another, 4 repetitions, with the arm order reversed on even repetitions. The runs use our half of the machine (socket 1, FPGA cards 90/93/b9/bc). <code>TRON_ATTN_STATS=1</code> makes the exit report say which path scored each K token.</li>
<li>Cell names: l8b, q4b and gptoss name the model, pN is the prompt length in tokens, cpu or fpga says where attention runs.</li>
<li>Scripts: <code>exec/pr5047-20261020/</code> (README.md there). Results: <code>exec/results/pr5047-20261020/</code>.</li>
</ul>
```

## Outside the requested scope

Prose inside the generated placeholder sections, fix in the template or the generator if wanted:

- line 348 `step T runs after the perf cells`: undefined label "step T" and the abbreviation "perf". Suggested: `the test step runs after the throughput cells`.
- line 350 `pay-for-determinism`: an undefined runtron setting. Suggested: `pay-for-determinism (the runtron setting that makes the token stream reproducible)`.
- line 352 `The chain resumes`: "chain" is undefined. Suggested: `The script chain (build, smoke, campaign, tests) resumes`.
- gen_page.py line 208 returns the verdict word `pending`, which makes the Short version read "shows pending". Suggested value: `no result yet`.

## Checked and left alone

- "API", "CPU" and "git blame" are not flagged as undefined terms (dictionary-level for engineers).
- "kill switch", "live mask", "the dotter", "the reader", "row-major" and "Build Tron" are defined at first use.
- The Short version has three sentences. It relies on the Words list that follows it for "K" and "KV cache page", which Rule 1 allows.
- No standalone citations (Rule 4). Every number carries a unit or a count noun (Rule 3).
