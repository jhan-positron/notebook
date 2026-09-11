#!/usr/bin/env python3
"""2026-09-11 update: PR head moved to 4290402491 (jhan, 2026-09-11 02:29 UTC) and jhan replied on five review
threads and two PR-level comments overnight. Applies the resulting edits to build_data.py, static.json and replies_v2.json."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))

def sub(text, old, new, n=1):
    c = text.count(old)
    if c != n:
        print(f"MISMATCH ({c} != {n}): {old[:100]}"); sys.exit(1)
    return text.replace(old, new)

# ---------------- static.json: meta, timeline
S = json.load(open(os.path.join(HERE, "static.json"), encoding="utf-8"))
S["meta"] = ("Prepared 2026-09-10 for jhan (the PR author), updated 2026-09-11. Answers the 14 findings in \"AMX Review Findings\" (Claude, for Bill Baumann, dated 2026-09-05, shared as a claude.ai artifact and linked from Bill's approval of PR 3879 on 2026-09-10). The findings cite the pre-split head `60d66d9c04`. Every line number on this page refers to `524c510609`, the head Bill approved, unless another tree is named; the PR head moved to `4290402491` on 2026-09-11 02:29 UTC (see the update block below for what shifted). Nothing here has been posted by Claude; the draft replies are for jhan.")
S["timeline"]["t1"] = "2026-09-11T18:00:00"
S["timeline"]["events"].append({"t": "2026-09-11T02:29:00", "lane": "code", "label": "jhan pushes 4290402491", "sub": "guard, s_pages assert", "level": 0, "anchor": "end"})
S["timeline"]["events"].append({"t": "2026-09-11T01:21:00", "lane": "review", "label": "jhan replies on 5 threads + 2 PR comments", "sub": "incl. Bill's hugepage thread", "level": 1, "anchor": "end"})
S["timeline"]["caption"] = ("Reviews above the axis, code events below. Bill's Claude findings (2026-09-05) and Ben's and Wade's reviews (2026-09-04) cite the old head; the split on 2026-09-08 moved the mirror, the counters and the memory-order fix out of PR 3879; Bill's approval (2026-09-10) is on 524c510609; jhan's commit 4290402491 and his thread replies followed on 2026-09-11.")
json.dump(S, open(os.path.join(HERE, "static.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)

# ---------------- build_data.py
P = os.path.join(HERE, "build_data.py")
b = open(P, encoding="utf-8").read()

# short version
b = sub(b, "two structural asks (a shared softmax helper, a tile-region guard) are accepted as follow-ups, and on three (test fakes, CPU-probe home, V accessors) our position differs.",
        "the tile-region guard and the s_pages stride assert landed in 4290402491 on 2026-09-11, the shared softmax helper was dropped by agreement with Ben, and on three (test fakes, CPU-probe home, V accessors) our position differs.")

# update block (rendered as a section right after the timeline text): add to timeline_text as a second paragraph
b = sub(b, "Both small PRs merged on 2026-09-10; Bill approved #3879 at `524c510609` the same evening. Ben's CHANGES_REQUESTED of 2026-09-04 still stands on the PR.\")",
        "Both small PRs merged on 2026-09-10; Bill approved #3879 at `524c510609` the same evening. Ben's CHANGES_REQUESTED of 2026-09-04 still stands on the PR.\\n\\n"
        "Update 2026-09-11. After this page was written, jhan pushed `4290402491` (02:29 UTC; one file, h/tron/models/self_attention.hpp, +12/-4): a static_assert that sizeof(s_pages) equals 4 rows x 64 floats x 4 bytes, a tron::finally scope guard that releases the tile configuration on every exit (the explicit end_region() block is gone), and the removal of the `= nullptr` default on apply_page_tok's packed-query parameter. This settles finding 14, the static_assert half of finding 9 and Wade's default-argument item, and lowers finding 10's count to six #ifdef TRON_AMX_DISPATCH blocks. Line numbers on this page refer to 524c510609; at 4290402491 the blocks are at :277, :299, :1320, :1390, :1421 and :1598, the guard at :1352-1354, the new assert at :1500-1502, apply_dense_amx_page at :1475 and its call at :1612. Between 01:21 and 02:33 UTC jhan also replied on Ben's threads 4 (mask_t), 5 (two paths, resolved: the split stays as it is, so no shared softmax helper), 6 (syscall comment) and 8 (tron::bf16), on Bill's hugepage thread (\\\"I will keep this in mind when working on AMX improvement\\\"; the document is being removed, see #4338), and posted PR-level answers to Ben's review body (namespace renamed) and to Wade's evaluation. The PR is still CONFLICTING with main and no CI has run on either 524c510609 or 4290402491.\")")

# order of work
b = sub(b, "{\"items\": \"9, 13, 14, 6, 7\", \"action\": \"Optional small commits before merge, all compile-time or comment-only: stride static_asserts (9, 13; also Wade's item), tron::finally or a guard type around the tile region (14; also Wade's item), two sentences naming the fake-TU invariants (6), one Note paragraph on why AMX is probed at run time (7).\", \"pre\": \"Each needs a CI re-run and, for the guard, the three tests with TRON_AMX_DISPATCH ON and t_llama_unit OFF on delphi-3bda. Est. 25-40 lines in total.\"},",
        "{\"items\": \"13, 6, 7\", \"action\": \"Optional small commits before merge, all compile-time or comment-only: the V/K row-size static_asserts at the call site (13), two sentences naming the fake-TU invariants (6), one Note paragraph on why AMX is probed at run time (7). The s_pages assert (9) and the tile-region guard (14) landed in 4290402491.\", \"pre\": \"Each needs a CI re-run. Est. 15-25 lines in total.\"},")
b = sub(b, "Follow-ups after merge: an Intel-pinned AMX CI job (#3997), Catch2 SKIP() for the OFF-build stubs, the shared softmax-step helper (Ben's thread 5), and one decision on the backend-type seam",
        "Follow-ups after merge: an Intel-pinned AMX CI job (#3997), Catch2 SKIP() for the OFF-build stubs, and one decision on the backend-type seam")
b = sub(b, "{\"items\": \"all\", \"action\": \"Decide whether to answer Bill at all: he approved, and the findings live in a claude.ai artifact, not in PR threads. If yes, post the one consolidated comment below on #3879 (or send it to him directly).\", \"pre\": \"Decision. The draft names every finding by number so Bill can map it to his list.\"},",
        "{\"items\": \"all\", \"action\": \"Decide whether to answer Bill's findings at all: he approved, and they live in a claude.ai artifact, not in PR threads. If yes, post the one consolidated comment below on #3879 (or send it to him directly). His inline hugepage thread is already answered (jhan, 2026-09-11 02:33 UTC).\", \"pre\": \"Decision. The draft names every finding by number so Bill can map it to his list.\"},")

# consolidated comment
b = sub(b, "- 9 (duplicated softmax step): both facts hold. A shared per-head step helper is drafted as the reply to Ben's thread 3936986164 (not yet posted); a two-line static_assert tying the s_pages row stride to 256 bytes goes next to the kernel calls.",
        "- 9 (duplicated softmax step): both facts hold. The static_assert on the s_pages layout landed in 4290402491 (self_attention.hpp:1500-1502). The duplication stays: Ben and I compared the two paths in a walkthrough and agreed to keep the split (his thread 3936986164, resolved 2026-09-11).")
b = sub(b, "- 14 (manual tile-region bracket): agreed; three continue paths, not four, and no live path skips end_region() today. A scope guard (tron::finally one-liner, or a guard type in amx_attn_iface.hpp) is the fix; timing to be decided.",
        "- 14 (manual tile-region bracket): agreed and done in 4290402491: a tron::finally guard declared next to begin_region() (self_attention.hpp:1352-1354) releases the tile configuration on every exit, and the explicit end_region() block is gone. One count: the loop has three continue paths, not four.")
b = sub(b, "but seven #ifdef TRON_AMX_DISPATCH blocks plus the #error remain. Removing them needs the seam decision below.",
        "but six #ifdef TRON_AMX_DISPATCH blocks (seven at the head you approved; the region-close block went with the guard in 4290402491) plus the #error remain. Removing them needs the seam decision below.")
b = sub(b, "Your two inline comments (hugepage arena): agreed on the direction. The paragraph and the arena are not in #3879 any more.",
        "Your two inline comments (hugepage arena): answered on the thread on 2026-09-11; in more words, agreed on the direction. The paragraph and the arena are not in #3879 any more.")
b = sub(b, "Housekeeping: #3879 currently conflicts with main in four files (next to the #4267 hooks), so CI has not run on 524c510609; a rebase is coming.",
        "Housekeeping: #3879 currently conflicts with main in four files (next to the #4267 hooks), so CI has not run on 524c510609 or on 4290402491; a rebase is coming.")

# finding 9: status partial, texts
b = sub(b, "    status=\"agree\",\n    action=\"Two-line stride static_assert next to the kernel calls; shared per-head step helper via Ben's thread 5; decide on the update helper.\",",
        "    status=\"partial\",\n    action=\"Stride static_assert landed in 4290402491; the shared helper was dropped by agreement with Ben (thread 5 resolved 2026-09-11); the duplication stays.\",")
b = sub(b, "join_page_ranges now has five asserts, two of them from main.\",\n    now_refs=[\n        {\"tree\": \"#3879 head\", \"ref\": \"h/tron/models/self_attention.hpp:1502-1518, :1532-1540 (AMX) vs :1661-1676, :1678-1690 (dotter)\"",
        "join_page_ranges now has five asserts, two of them from main.\\n\\nUpdate 2026-09-11: commit 4290402491 adds the static_assert (self_attention.hpp:1500-1502 there: `sizeof(s_pages) == operation_kv_mul * page::page_size * sizeof(float)`). The duplication stays: jhan and Ben compared the two paths in a walkthrough, noted that the per-head softmax and commit loops differ (the AMX path folds the PV kernel's output where the dotter folds scaled_v inside the same loop), and agreed to keep the current split; Ben's thread 3936986164 was resolved on that basis (jhan's comment 3985240699).\",\n    now_refs=[\n        {\"tree\": \"4290402491\", \"ref\": \"h/tron/models/self_attention.hpp:1500-1502\", \"what\": \"`static_assert(sizeof(s_pages) == operation_kv_mul * page::page_size * sizeof(float), ...)` next to the QK kernel call.\"},\n        {\"tree\": \"#3879 head\", \"ref\": \"h/tron/models/self_attention.hpp:1502-1518, :1532-1540 (AMX) vs :1661-1676, :1678-1690 (dotter)\"")
b = sub(b, "    position=\"Agree with both fixes. The step helper is the same ask as Ben's thread 5",
        "    position=\"Status after 2026-09-11: the static_assert is done (4290402491) and the helper is not going to happen in this PR, because jhan and Ben agreed in the walkthrough to keep the current split and the thread is resolved. The reply to Bill states both. What follows is the position as it stood before that: agree with both fixes. The step helper is the same ask as Ben's thread 5")
b = sub(b, "    decisions=[\"Stride static_assert inside #3879 now (compile-time only), or with the helper change.\", \"Shared step helper inside #3879 or as a follow-up; the Ben draft currently says \\\"in this PR\\\".\", \"Also do the second helper (the v*/s*/m* update taking the new-V contribution) as Bill's fix describes; if yes, add it to the Ben reply first.\", \"Post the Ben reply before or together with the Bill reply, so Bill finds the proposal on the thread it cites.\"],",
        "    decisions=[\"Whether to tell Bill that the helper was dropped by agreement with Ben (the draft does), or to leave the duplication question open for a later PR.\", \"Whether a per-page NaN check is wanted at all (it would be new for both paths).\"],")

# finding 14: status done
b = sub(b, "    status=\"agree\",\n    action=\"Add a scope guard: tron::finally one-liner or Bill's guard type; decide the form and whether before merge.\",",
        "    status=\"done\",\n    action=\"Done in 4290402491 (tron::finally guard next to begin_region()); only the two manual test brackets could still be converted.\",")
b = sub(b, "Wade's evaluation asked for the same guard; the earlier page (PR-open-comments.html, item 12) proposed the one-liner and left the timing to jhan.\",\n    now_refs=[",
        "Wade's evaluation asked for the same guard; the earlier page (PR-open-comments.html, item 12) proposed the one-liner and left the timing to jhan.\\n\\nUpdate 2026-09-11: done in 4290402491. A `tron::finally end_amx_region([&] { if (amx_on) amx_attn_h128g4::end_region(); });` is declared right after begin_region() (self_attention.hpp:1352-1354 at that commit) and the explicit end_region() block that followed the loop is removed, so the #ifdef TRON_AMX_DISPATCH count in the file drops from seven to six. Form (a) below is what landed; the two manual brackets in t/t_amx_numerics.cpp are unchanged.\",\n    now_refs=[\n        {\"tree\": \"4290402491\", \"ref\": \"h/tron/models/self_attention.hpp:1348-1354\", \"what\": \"begin_region() inside `if (amx_on)`, then the tron::finally guard; the old block at 524c510609:1414-1416 is gone.\"},")
b = sub(b, "    decisions=[\"Timing: add the guard to #3879 now (then re-run the three tests with the option ON and t_llama_unit OFF on delphi-3bda), or post the reply with \\\"a follow-up commit\\\".\", \"Form: (a) tron::finally one-liner at the call site, or (b) a guard type in amx_attn_iface.hpp, also replacing the two manual brackets in t_amx_numerics.cpp.\"],",
        "    decisions=[\"Whether to also convert the two manual brackets in t/t_amx_numerics.cpp:157-160 and :225-228 to the same guard (test code only).\", \"Whether the three tests were re-run on delphi-3bda after 4290402491 (no CI has run on it: the PR still conflicts with main).\"],")
b = sub(b, "    insufficient=[\"Whether the compiled hot path is identical with the guard: compare `objdump -d` of apply_page_range between the two builds.\"],",
        "    insufficient=[\"Whether the compiled hot path is identical with the guard: compare `objdump -d` of apply_page_range between builds of 524c510609 and 4290402491.\", \"Whether 4290402491 was built and tested on an AMX host before the push: no CI run exists for it.\"],")

# finding 10: count at new head
b = sub(b, "Two blocks sit on the per-page path. CI now compiles the ON cell on every PR; the scheduled benchmark and coverage workflows still build the default OFF cell.\",",
        "Two blocks sit on the per-page path. CI now compiles the ON cell on every PR; the scheduled benchmark and coverage workflows still build the default OFF cell.\\n\\nUpdate 2026-09-11: at 4290402491 the count is six (:277, :299, :1320, :1390, :1421, :1598) plus the #error, because the tron::finally guard replaced the region-close block.\",")

# hugepage section: thread answered
b = sub(b, "Nobody has replied. (\\\"covo em's\\\" is quoted as written; it probably means OOM kills.)",
        "(\\\"covo em's\\\" is quoted as written; it probably means OOM kills.) Update 2026-09-11: jhan replied on the thread at 02:33 UTC (comment 3985437314): \\\"I will keep this in mind when working on AMX improvement. BTW this document is being removed, Ben asked me to create another document which lists all TRON environment variables, tracked at #4338.\\\" The longer draft below is therefore optional material for a follow-up, not a pending reply.")
b = sub(b, "\"Reply now on the outdated inline thread, or hold for the PR 2 description if it is ever opened (draft: reply now, since Bill called the comments outstanding).\", ",
        "\"Whether to post the longer explanation below in addition to the short reply already on the thread (2026-09-11), or leave it for the PR 2 description if the mirror is ever reopened.\", ")

# CI section: also 0 runs on the new head
b = sub(b, "GitHub does not start pull_request workflows on a conflicting PR; only Cursor Bugbot and Graphite ran on the head.",
        "GitHub does not start pull_request workflows on a conflicting PR; only Cursor Bugbot and Graphite ran on the head. The same holds for 4290402491 (0 workflow runs on 2026-09-11).")

open(P, "w", encoding="utf-8").write(b)

# ---------------- replies_v2.json: findings 9, 10, 14
R = json.load(open(os.path.join(HERE, "replies_v2.json"), encoding="utf-8"))
R["findings"]["9"] = ("Both facts hold; the stride static_assert landed in 4290402491, and the duplication stays by agreement with Ben. The static_assert checks that sizeof(s_pages) equals 4 rows x 64 floats x 4 bytes (self_attention.hpp:1500-1502 at that commit), which forces the rows to be consecutive with no padding, the property both kernels rely on when they take &s_pages[0][0] with row stride page_size. On the duplicated step: Ben and I compared the two paths side by side in a walkthrough, noted that the per-head softmax and commit loops differ (the AMX path folds the PV kernel's output where the dotter folds scaled_v inside the same loop), and agreed to keep the current split; his thread 3936986164 is resolved on that basis. On the NaN asserts, the comparison mixes stages: the dotter's per-page step has no assert either, and the join_page_ranges asserts check the state either path produced.")
R["findings"]["10"] = ("The dense path is one function now, but six #ifdef TRON_AMX_DISPATCH blocks plus the #error remain, so \"single call and no preprocessor\" is not met yet. At 4290402491 apply_dense_amx_page (self_attention.hpp:1475) is called from one place (:1612), the query pack is one call, and the K_MIRROR blocks are gone, so the deepest nest is #ifdef, then if constexpr, then if. The blocks are at :277, :299, :1320, :1390, :1421 and :1598 (seven at the head you approved; the region-close block went with the tron::finally guard). I kept the #error (:29-35) on purpose: the pair-interleaved V storage exists only when TRON_CHUNK_SIZE is 16, which is only the AVX-512 build (h/tron/simd/auto.hpp:17-21); without the guard a build on a host that fails the AVX-512 probe gets chunk 8, still compiles the AMX path, and pairs the wrong tokens. The #error stays until the static_assert next to the V layout from your finding 13 replaces it. Removing the rest needs a design step: the in-loop gates can move behind if constexpr, but the slot type and the attn_accum member (:277-285, :299-308) are declarations, which is the same question as your backend seam.")
R["findings"]["14"] = ("Agreed, and done in 4290402491: a tron::finally scope guard declared next to begin_region() now releases the tile configuration on every exit from apply_page_range, and the explicit end_region() block is gone. The guard is `tron::finally end_amx_region([&] { if (amx_on) amx_attn_h128g4::end_region(); });` (self_attention.hpp:1352-1354 at that commit; the scope guard type is h/common/util.hpp:73, already used in gof.hpp and runtron.cpp). One count to correct: the loop had three continue paths, not four, and today no live path skipped end_region(), because the only return precedes the bracket, TRON_ASSERT aborts, and the function is noexcept; the guard covers the future early return you describe. The two manual brackets in t/t_amx_numerics.cpp (:157-160, :225-228) are unchanged; a guard type in amx_attn_iface.hpp would cover those too if you think it is worth it.")
json.dump(R, open(os.path.join(HERE, "replies_v2.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("update applied")
