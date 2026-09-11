#!/usr/bin/env python3
"""Applies the 48 corrections of the 2026-09-10 claim-check workflow to build_data.py (exact string edits)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(HERE, "build_data.py")
b = open(P, encoding="utf-8").read()
edits = []  # (old, new, expected_count)
def E(old, new, n=1): edits.append((old, new, n))

# ---- finding 1
E("settle by running gen/t/t_amx_numerics on delphi-3bd6 or delphi-3af6 with the CI build.",
  "settle by running gen/t_amx_numerics (the recipe at doc/amx_software_attention.md:74) on delphi-3bd6 or delphi-3af6 with the CI build.")
E("Drop the \\\"seven other default-OFF options also lack CI\\\" rebuttal: true, but it does not answer Bill's sentence and reads as deflection.",
  "Drop the \\\"other default-OFF options also lack CI\\\" rebuttal (five of the six other top-level default-OFF options had no workflow reference at 60d66d9c04; COVERAGE did): true, but it does not answer Bill's sentence and reads as deflection.")
E("GNUmakefile:402, :411, :423; doc/amx_software_attention.md:69-73\", \"what\": \"Fixed -D lists in the configure rules, no CMAKE_ARGS-style variable; the doc gives",
  "GNUmakefile:402, :411, :423; doc/amx_software_attention.md:69-77\", \"what\": \"Fixed -D lists in the configure rules, no CMAKE_ARGS-style variable; the doc's recipe (:72) gives")
E("a further Intel host, delphi-3af6-0, serves the same labels without being in the README table.",
  "a further runner in the delphi family, delphi-3af6-0, serves the same labels without being in the README table (its CPU is not recorded in any repo file; the CI log of run 34375107972 shows an Intel Xeon 6962P).")
E("so the kernel translation unit, the dispatch blocks and both AMX tests compile on every PR build; README.ci.md:507-518 documents it.",
  "so the kernel translation unit, the dispatch blocks and both AMX tests compile on every PR build that reaches the build step; README.ci.md:507-518 documents it.")

# ---- finding 2
E("t_amx_mirror, t_amx_arena_leak and three of the four new t_llama_unit cases moved to PR 2; the fourth (the eligibility case) was dropped because the first case of t_amx_numerics checks the same predicate. t_llama_unit changes by one line in this PR",
  "t_amx_mirror, t_amx_arena_leak and the three K-mirror t_llama_unit cases moved to PR 2. The fourth case (AMX eligibility) was split: its canonical-gate assertions are now the first case of t_amx_numerics (t/t_amx_numerics.cpp:83), and its amx_mirror_eligible assertions live in PR 2 as \\\"K mirror eligibility follows the executor's activation scalar\\\" (PR 2 t/t_llama_unit.cpp:1179-1215), so PR 2's t_llama_unit carries four new cases. t_llama_unit changes by one line in this PR")
E("t_amx_mirror, t_amx_arena_leak and three of the four new t_llama_unit cases moved to the parked K-mirror draft, the eligibility case was dropped because t_amx_numerics.cpp:83 checks the same predicate, and t_llama_unit changes by one line here",
  "t_amx_mirror, t_amx_arena_leak and the three K-mirror t_llama_unit cases moved to the parked K-mirror draft, the eligibility case was split (its canonical-gate half is the first case of t_amx_numerics, t/t_amx_numerics.cpp:83; its mirror half stays in the draft), and t_llama_unit changes by one line here")
E("\"what\": \"Gate and packer cases run anywhere; QK and PV cases WARN and return without AMX;",
  "\"what\": \"Gate case runs on any host; packer case runs on any AVX-512 host; QK and PV cases WARN and return without AMX;")
E("and t_amx_numerics runs its gate and packer cases anywhere and its two kernel cases only on an AMX host, otherwise warning and returning",
  "and t_amx_numerics runs its gate case anywhere, its packer case on any AVX-512 host, and its two kernel cases only on an AMX host, otherwise warning and returning")
E("t/t_amx_dispatch_dtype.cpp:168, :193-206, :210-214", "t/t_amx_dispatch_dtype.cpp:168, :193-208, :210-214")
E("and t_llama_unit grew by 301 lines and four TEST_CASEs.", "and t_llama_unit gained 301 lines (6 removed, net +295) and four TEST_CASEs.")

# ---- finding 4
E("refs_old=\"definition h/tron/models/kv_cache.hpp:183 · thread h/tron/scheduler/full.hpp:312 → 318 → 713 → 728 → 835 → kv_cache.hpp:1444 → 1455 → 1039 → 1066 → 1106 · defaults kv_cache.hpp:800, 1029\",",
  "refs_old=\"definition h/tron/models/kv_cache.hpp:183 · static asserts t/t_llama_unit.cpp:902, 1060-1064 · thread h/tron/scheduler/full.hpp:312 → 318 → 713 → 728 → 835 → kv_cache.hpp:1444 → 1455 → 1039 → 1066 → 1106 · defaults kv_cache.hpp:800, 1029 · [[maybe_unused]] at :809, :1066\",")
E("This supersedes the earlier partial fix R2-03 (false default kept) rather than conflicting with it.",
  "This supersedes the earlier fix R2-03 (triage decision done, b2010bee9, 2026-08-25: the false default) rather than conflicting with it.")
E("enumerate the pairs at src/tron/scheduler/full.cpp:326-336 and compare.",
  "derive the pairs from find_eagle_model (src/tron/scheduler/full.cpp:286-307: the draft is the registered model `eagle-<model>`, or that name with -good/-fast/-nice/-best removed) applied to the registered model list; the attach site that casts shared_root is :325-336.")

# ---- finding 5
E("#3879 has no concept, shim, fixture or flag; its book constructors are main's three-argument forms and full.hpp is unchanged.",
  "#3879 has no concept, shim, fixture or flag; its book constructor and try_create factory are main's three-argument forms, its adopt constructor carries no mirror flag, and the PR does not touch h/tron/scheduler/full.hpp (empty diff against its merge base a80b102c18; main has since changed that file in unrelated places).")
E("its book constructors are main's three-argument forms (h/tron/models/kv_cache.hpp:673, :865, :889) and h/tron/scheduler/full.hpp is unchanged from main.",
  "its book constructor and try_create factory are main's three-argument forms (h/tron/models/kv_cache.hpp:673, :865), its adopt constructor carries no mirror flag (:889-893), and the PR does not touch h/tron/scheduler/full.hpp (empty diff against its merge base; main has since changed that file in unrelated places).")
E("every production cache_t is a book, including both branches of the plugin generator (ingest/src/TronCpp.hs:543, :567). Under single-K",
  "every production cache_t is a book, including both branches of the plugin generator (ingest/src/TronCpp.hs:540, :564 at 524c510609; :543, :567 at the head you reviewed). Under single-K")
E("the quoted comment \\\"Today every production cache is a book, so the no-bool path is compiled but not run\\\" (:1435-1437)",
  "the quoted comment \\\"Today every production cache is a book, so the no-bool path is compiled but not run\\\" (:1435-1436)")

# ---- finding 7
E("Every reference resolves (the probe spans :54-82, three lines off).",
  "Every reference resolves (the probe spans :54-82; the review's :57-86 is off by three lines at the start and four at the end).")
E("Confirm the deployment fact before writing it into the Note: one tron binary runs on hosts with and without AMX (no tree states it).",
  "Confirm the deployment fact before writing it into the Note: one tron binary is deployed to hosts with and without AMX. The trees say only that the binary runs the AVX path on a host without AMX (amx_attn_iface.hpp:45-46; doc/amx_software_attention.md:65); none states that production ships one binary to both host classes.")

# ---- finding 8
E("On the mutable bf16* handed to the hardware layer (full.hpp:2288-2291): you are right",
  "On the mutable bf16* handed to the hardware layer (full.hpp:2289-2292; your ref 2288-2291 starts one line early): you are right")
E("Two citation errors: :1294 is an assert (the plane size constant is :1292), and 11 of the 12 #ifdef blocks sit inside book/page, the twelfth in namespace detail.",
  "Three citation errors: :1294 is an assert (the plane size constant is :1292); full.hpp:2288-2291 starts one line early (the lambda is :2289-2292); and 11 of the 12 #ifdef blocks sit inside book/page, the twelfth in namespace detail.")
E("so gof.hpp:62, gof.cpp:152 and five hwattention.hpp declarations change together", "so gof.hpp:62, gof.cpp:202 and five hwattention.hpp declarations change together")
E("PR 2 has everything the finding names, unchanged apart from renames and Note wording; its rewritten Note",
  "PR 2 has everything the finding names; the write sites, the `/ 2` offsets, the view offset and the twelve #ifdef blocks are unchanged apart from the amx_attn -> amx_attn_h128g4 rename and Note wording, and the mirror read moved into the refactored dense-page function (self_attention.hpp:1505-1509) without gaining a verify; its rewritten Note")
E("The mirror lives in a local reference draft that differs from the commit you reviewed only by renames and comment wording, so your description holds:",
  "The mirror lives in a local reference draft that differs from the commit you reviewed by renames, comment wording and the dense-page refactor that moved the mirror read into one function; every point of your description holds there:")

# ---- finding 9
E("and :1661-1676 (the dotter epilogue in apply_page_tok), and the v*/s*/m* update at :1532-1540 and :1678-1690. I am proposing",
  "and :1661-1676 (the dotter epilogue in apply_page_tok, where the sum is taken inside the update at :1684 and :1688), and the v*/s*/m* update at :1532-1540 and :1678-1690. I am proposing")

# ---- finding 10
E("\"what\": \"ON cell per PR; OFF cell weekly (bench refresh, golden benchmark, coverage).\"",
  "\"what\": \"ON cell on every non-draft PR; OFF cell on a schedule: bench refresh weekly (Sunday), golden benchmark nightly, coverage weekly (Saturday).\"")
E("with the chunk-size axis the matrix has four valid cells and the repository built one.",
  "with the chunk-size axis the matrix has four valid cells; CI built one (dispatch off, chunk 16) and the darwin developer preset builds a second (dispatch off, chunk 8).")

# ---- finding 11
E("Four of PR 0's five hook hunks sit in regions #3879 also edits: this is the merge conflict CI reports today.",
  "Two of PR 0's five hook blocks (main self_attention.hpp:1290 and :1356) sit exactly where #3879 inserts its AMX blocks, so they conflict when main is merged into 524c510609; the same merge also conflicts in CMakeLists.txt, README.ci.md and config/test-benchmarks.json, where PR 0 and #3879 each added lines at the same place. GitHub reports the PR as CONFLICTING today.")
E("Consistent with PR 0's body, which answered Wade's identical \\\"compiled by nobody\\\" point with the \\\"Why keep it in the tree\\\" section.",
  "Consistent with PR 0's body, whose \\\"Review history\\\" section answers Wade's identical \\\"compiled by nobody\\\" point (the counters stay behind an option, with a test and a stated purpose) and whose \\\"What does this PR serve?\\\" section gives the purpose.")
E("Offer Bill outright removal as an alternative to #4303 (the draft does, in one clause).",
  "Offer Bill outright removal as an alternative to #4303 (the draft reply does not; add one clause if wanted, e.g. \\\"If you would rather see the counters removed than published as FUSE files, say so and I will raise it on #4303.\\\").")
E("h/tron/models/self_attention.hpp:21, :1290, :1300, :1333, :1352, :1356; README.ci.md:574-582", "h/tron/models/self_attention.hpp:21, :1290, :1300, :1333, :1352, :1356; README.ci.md:574-583")

# ---- finding 12
E("Overstated: \\\"the leak test shrinks to a plain check\\\": the test has three cases and only the first (alloc/free balance) depends on the allocation form; the eligibility-gate and accounting-gauge cases do not.",
  "Overstated: \\\"the leak test shrinks to a plain check\\\": the test has three cases under TRON_AMX_K_MIRROR (plus a SUCCEED placeholder in the #else branch, :185-187), and all three read the counters fed by the replaced operator new[] forms (:137-148, :159-169), so the eligibility-gate and accounting-gauge assertions would also need rewriting, not only the alloc/free balance case.")
E("and the round-1 soak measured the arena at 43.8-44.6 GB of host RAM per tp2 engine, which sizes that extra reservation.",
  "and in the round-1 soak the server log's KV footprint line put the arena at 43.8 GB at 30 min and a 46.5 GB peak (10^9 bytes; half of the DMA KV bytes) on one tp2 engine, with host used memory up by as much as 42.3 GiB; the peak sizes that extra reservation.")
E("about one third fewer books at a fixed pool (est.) or a pool about half larger, as you suggest, and in the round-1 soak",
  "about one third fewer books at a fixed pool (est.) or a pool about half larger (est.), which is the \\\"add more huge pages\\\" route you suggest, and in the round-1 soak")
E("or a pool about half larger, which is what Bill's second comment asks for), touches the fault-injection seam",
  "or a pool about half larger (est., because the arena is kv_bytes/2), which is the direction Bill's second comment points to (\\\"add more huge pages\\\")), touches the fault-injection seam")

# ---- finding 13
E("and the contract text is also in the interface header, the doc, the kernel constant and the test's formula; the PR added a consumer, not the contract.",
  "and the contract text is also in the interface header (amx_attn_iface.hpp:214 at the old head), the kernel constant V_PAIR_ROW_BYTES (amx_attn.cpp:41-42) and the test's formula (t_amx_numerics.cpp:236-246); the doc that also states it (doc/amx_software_attention.md:16, :25) was added on 2026-09-07, after the review. The PR added a consumer, not the contract.")
E("{\"tree\": \"main\", \"ref\": \"h/tron/models/kv_cache.hpp:1287-1396 (git blame 5d94957ac8, 2024-11-05)\", \"what\": \"Pair-interleaved V layout, set_v writers and readers (append_v, scaled_v, get_v) all pre-exist.\"}",
  "{\"tree\": \"main\", \"ref\": \"h/tron/models/kv_cache.hpp:1866-1873 (layout), :1287-1344 (set_v/get_v declarations), :1401-1412 (scaled_v), :1544 (append_v), :1938-2050 (set_v definitions); `git log -S'page_size / 2'` -> 5d94957ac8, 2024-11-05\", \"what\": \"The [p/2] layout and its set_v writers and scaled_v/get_v/append_v readers all pre-exist; the layout text was introduced by 5d94957ac8 (2024-11-05) and last moved by fffa24972ef9 (2025-12-18).\"}")
E("{\"tree\": \"#3879 head\", \"ref\": \"t/t_amx_numerics.cpp:22-27, :197-209\", \"what\": \"No kv_cache.hpp include; builds `storage[(pair * HEAD_SIZE_128 + dim) * 2 + parity]` itself.\"}",
  "{\"tree\": \"#3879 head\", \"ref\": \"t/t_amx_numerics.cpp:22-28, :197-211\", \"what\": \"No kv_cache.hpp include; builds `v_page[(pair * HEAD_SIZE_128 + d) * 2 + j]` itself (:207).\"}")
E("because t_amx_numerics builds its own V buffer from the same formula (t_amx_numerics.cpp:197-209), and making that test fill a real kv_block would close the gap.",
  "because t_amx_numerics builds its own V buffer from the same formula (t_amx_numerics.cpp:197-211), and making that test fill a real kv_block would close the gap.")
E("not the V consumer (weights_times_v_128x4 at :208-222);", "not the V consumer (weights_times_v_128x4, :183-230; its V tile loads with V_PAIR_ROW_BYTES are at :208-222);")

# ---- finding 14
E("tron::finally (h/common/util.hpp:73) existed with four use sites.",
  "tron::finally (h/common/util.hpp:73) existed with four use sites in h/ and src/ (h/tron/gof.hpp:221, :240; src/runtron.cpp:252, :265) and twelve more in t/.")
E("\"ref\": \"h/common/util.hpp:73-85; h/tron/gof.hpp:221, :240; src/runtron.cpp:257, :273; src/pos/memperf.cpp:83\"",
  "\"ref\": \"h/common/util.hpp:73-86; h/tron/gof.hpp:221, :240; src/runtron.cpp:257, :273; src/pos/memperf.cpp:83\"")

# ---- CI section
E("All four show identical \\\"passed\\\" lines for t_amx_numerics and t_amx_dispatch_dtype, because bin/slice",
  "All four report the status word \\\"passed\\\" for t_amx_numerics and t_amx_dispatch_dtype, whether or not the host has AMX (on andoria-14 the two lines carry a [new] tag, because the genoa96 section of config/test-benchmarks.json has no cost entry for them), because bin/slice")
E("an AMD host without AMX, and all four show the same \\\"passed\\\" lines; three other runs",
  "an AMD host without AMX, and all four report \\\"passed\\\" for both binaries, the AMD host included; three other runs")
E("run gen/t/t_amx_numerics on one of those hosts with the CI build, or change the workflow to keep that log.",
  "run gen/t_amx_numerics on one of those hosts with the CI build, or change the workflow to keep that log.")
E("Whether any of the 49 model tests in the test-fpga job on delphi-17cf (run 34341042253) took the AMX path:",
  "Whether any of the 49 fpga-labelled tests (some of which load a model) in the test-fpga job on delphi-17cf (run 34341042253) took the AMX path:")

# ---- seam section
E("Bill's second artifact proposes wrapping the kernel entry points in a struct with static member functions and adding a defaulted type parameter to apply_page_range, so that tests pass a fake type instead of redefining the functions; it says this collapses findings 3, 4, 5, 6 and 7. Checked against 524c510609:",
  "Bill's second artifact proposes, as its first step, wrapping the kernel entry points in `struct hardware_backend` with static member functions and adding a defaulted type parameter to apply_page_range, so that tests pass a fake type instead of redefining the functions. It says the seam \\\"collapses the four costly findings and both test link hacks at once\\\" under four headings (eligibility, detection, accounting, tests); in the findings page's numbering these are 4 (taking 5 with it), 7, 3 and 6. For 3, 4, 5 and 7 the artifact attributes the collapse to three further steps (eligibility as a policy type on book, the probe moved to system/, the arena bytes reported through get_memory_pressure_stats()), which are the same fixes this page accepts for those findings under the mirror-lands branch. Checked against 524c510609:")
E("The type has to be threaded through three more member templates that call kernel functions: packed_amx_query (:1426), apply_page_tok (:1551) and apply_dense_amx_page (:1473).",
  "The type has to be threaded through three more member templates on the path to the kernel calls: packed_amx_query (:1426, calls pack_q_group_128x4 at :1434), apply_page_tok (:1551, calls no kernel itself; it forwards to apply_dense_amx_page at :1604) and apply_dense_amx_page (:1473, calls qk_rowmajor_128x4 at :1496 and weights_times_v_128x4 at :1522).")
E("Findings 3, 4, 5: not in #3879 (mirror code). Finding 7: no; a static-member wrapper does not change the probe's home or the predicate count. Cost: about 80 lines over 7 files (est., not built): the interface header, the kernel TU, four member templates in self_attention.hpp, the fake struct in t_amx_dispatch_dtype.cpp, and ten call renames in t_amx_numerics.cpp.",
  "Findings 3, 4, 5: not in #3879 (mirror code); the artifact's further steps for them are answered in those findings' sections. Finding 7: the wrapper step alone does not change the probe's home or the predicate count; the artifact's probe-move step is the follow-up discussed in finding 7. Cost of the wrapper step: about 80 lines over five code files (est., not built): the interface header, the kernel TU, four member templates in self_attention.hpp, the fake struct in t_amx_dispatch_dtype.cpp, and ten call renames in t_amx_numerics.cpp; plus the two-line comment at t/CMakeLists.txt:589-590 and the doc sentence at doc/amx_software_attention.md:61-62, seven files in all.")
E("It does not collapse findings 3, 4 and 5, which are mirror code not in this PR, nor finding 7, which is about where the CPU probe lives and how many gate predicates there are. The change is small and mechanical, about 80 lines over seven files (estimate, not built),",
  "The wrapper step alone does not settle findings 3, 4 and 5, which are mirror code not in this PR, nor finding 7, which is about where the CPU probe lives and how many gate predicates there are; your further steps for those (policy type, probe move, accounting field) are answered under each finding. The change is small and mechanical, about 80 lines over seven files (five code files plus a CMake comment and a doc sentence; estimate, not built),")
E("{\"tree\": \"#3879 head\", \"ref\": \"t/t_amx_dispatch_dtype.cpp:82-83, :104, :149, :166-190; t/t_llama_unit.cpp:1537, :1600, :1603\", \"what\": \"Model built in the test; direct call; the six fakes; three further test call sites, all passing only `<geometry>`.\"}",
  "{\"tree\": \"#3879 head\", \"ref\": \"t/t_amx_dispatch_dtype.cpp:82-83, :89-90, :104, :149, :166-190; t/t_llama_unit.cpp:1537, :1600, :1603\", \"what\": \"Model type (:82-83), model constructed (:89-90) and state constructed (:104) in the test; direct call; the six fakes; three further test call sites, all passing only `<geometry>`.\"}")
E("The \\\"single call\\\" half is done at this head", "The \\\"single call\\\" half is done at this head", 0)  # no-op guard

# ---- hugepage section
E("the PR's Note [Why not replace canonical K] argued against single-K until three consumer costs were measured, which is exactly what G1 and G2 measure.",
  "the PR's Note [Why not replace canonical K] argued against single-K until its unmeasured costs were known: the FPGA GOF staging adapter (G2 measures this), a new AVX fallback reader, the kill switch's same-layout contract, and, in its closing line, the VNNI scatter as the primary store (G1 measures this). G1 and G2 cover two of those four points.")
E("\"ref\": \"doc/memory_pressure_governor.md:504-516 (old) = :540-552 (PR 2); h/tron/models/kv_cache.hpp:554-575 (PR 2, Note [K mirror parallel arena])\"",
  "\"ref\": \"doc/memory_pressure_governor.md:504-516 (old) = :540-552 (PR 2); h/tron/models/kv_cache.hpp:550-587 (PR 2; :555 at the old head), Note [K mirror parallel arena]: the ordinary-RAM reason at :558-560, the pool/2 sentence at :572-575\"")
E("traps: the helper's \\\"callers must propagate failure\\\" rule, the fault-injection seam's \\\"only caller is book::try_create\\\" assumption,",
  "traps: the helper's \\\"callers must propagate failure\\\" rule, the fault-injection seam's assumption that the helper's \\\"only callers are book::try_create\\\" (h/system/memory.hpp:263-264),")

# ---- page-level
E("the commit Ben, Jeremy and Wade also reviewed (35 commits,", "the commit Ben and Wade also reviewed (Jeremy's review of 2026-08-25 was on the earlier commit d176c88b3c; 35 commits,")
E("- 9 (duplicated softmax step): both facts hold. A shared per-head step helper is proposed to Ben on thread 3936986164; a two-line static_assert",
  "- 9 (duplicated softmax step): both facts hold. A shared per-head step helper is drafted as the reply to Ben's thread 3936986164 (not yet posted); a two-line static_assert")
E("I am proposing to Ben, on his thread 3936986164, a shared per-head helper", "I am drafting for Ben's thread 3936986164 (not yet posted) a shared per-head helper")
E("[\"book, page, kv_block\", \"book is the per-model KV cache object; a page holds 64 tokens; kv_block is the storage struct for one (slot, kv_head) with its K and V arrays.\"]",
  "[\"book, page, kv_block\", \"book is the per-model KV cache object; a page holds 64 tokens; kv_block is the storage struct for one page of one (slot, kv_head): its K and V arrays hold that page's keys and values.\"]")

# apply
bad = []
for old, new, n in edits:
    c = b.count(old)
    if n == 0:
        continue
    if c != n:
        bad.append((c, n, old[:90]))
        continue
    b = b.replace(old, new)
if bad:
    for c, n, o in bad: print(f"MISMATCH count={c} expected={n}: {o}")
    sys.exit(1)
open(P, "w", encoding="utf-8").write(b)
print("applied", sum(1 for e in edits if e[2]), "edits")
