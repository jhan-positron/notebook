# Round-5 data for gen_review5.py (head 234c02bde). His voice: BODY, FOLLOWUP, FIXED_VOICE, NEW[].text. Everything
# else is the verification record for jhan. Sources: r5/workflow_out.json (wf_b8f009bd-07b: 4 status verifiers +
# 4 status refuters, 4 finders -> 11 candidates -> 11 refuters, all 11 survived as PARTIAL with wording/line
# corrections, folded in below), the orchestrator's own checks named in METHOD, and r5/fix/ (the compiled patch
# behind the two blocker fix sections: kv_cache.diff, t_llama_unit.diff, t_amx_arena_leak.diff,
# amx_attention_compile.cpp, syntax_*.log, fixcheck.py).
import json as _json, os as _os
_R5 = R5  # the generator exec()s this file: use its r5/ directory
_SITES = _json.load(open(_os.path.join(_R5, "fix", "fix_sites.json")))

# Carried EAGLE diagram (round 3): the "canonical -> slot 0" arrow label sat on top of the bold row label; move it
# right of that label, next to the arrow's start (render check 2026-08-25).
_old = '<text x="130" y="128" font-size="9.5" fill="#2a78d6">canonical -&gt; slot 0</text>'
_new = '<text x="205" y="118" font-size="9.5" fill="#2a78d6">canonical -&gt; slot 0</text>'
assert _old in EAGLE_HTML, "EAGLE label not found"
EAGLE_HTML = EAGLE_HTML.replace(_old, _new)

VERDICT = "CHANGES_REQUESTED"

BODY = (
    "The bench is gone and the pair it left behind now matches a recorded sweep - good, that was the half I refused to "
    "approve.  Two things about what replaced it: the date on the pair (`2026-08-19`) is not the date of the only sweep that "
    "carries 1249.9/686.0, and the command line that ff7269a9f recorded went out again in 901f30d8e, so a reader still has no "
    "way to reproduce 1250 - the Note is now the only place the pair lives, so the provenance has to live there too; and the "
    "Note attributes the whole ~560 to transpose and score traffic when the canonical bench variant also re-packed Q once per "
    "page - see the header.  Codex's two comments are both right on the facts and both sit on lines I already commented on in "
    "round 1 (the 64B contract at `amx_attn_iface.hpp:102`, the pack/region at `self_attention.hpp:1361`); I've answered them "
    "inline, and the alignment one wants a fix either way.  What still blocks from my side: the 3-argument `book`/`try_create` "
    "that default `amx_mirror_eligible` to allocate, and a compile-only configuration so the flagged code can't rot after "
    "merge - all the more since no build or test job has run on this PR at all (draft without the `Run CI` label: every run "
    "on the branch is lint only, and the last eight commits have none).  The description still says nothing about the "
    "`kv_block_planes` rename, `v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the `amx_mirror_eligible` "
    "plumbing through `node_base`.  The rest is carried over unchanged below."
)

TAKE = ("Round 5 in one line: __X__ comments made obsolete by the deletion (section 2) and __M__ merged - R1-51's blocking half is "
        "resolved and its provenance half now lives in the R1-14 thread; __O__ carried over (five with a follow-up); __N__ new: the "
        "bench pack asymmetry inside the ~560, the history sentence in the kernel TU header, and his two replies to the Codex review. "
        "Blockers 3 -> __B__: the default-true 3-argument constructor (<code>kv_cache.hpp</code>) and the missing compile-only "
        "configuration (<code>t/CMakeLists.txt</code>) - each now carries a compiled suggested fix; the kernel-copy blocker is resolved.")
TAKE_MD = ("**Round 5 in one line:** __X__ comments made obsolete by the deletion (section 2) and __M__ merged - R1-51's blocking half is "
           "resolved and its provenance half now lives in the R1-14 thread; __O__ carried over (five with a follow-up); __N__ new: the "
           "bench pack asymmetry inside the ~560, the history sentence in the kernel TU header, and his two replies to the Codex review. "
           "Blockers 3 -> __B__: the default-true 3-argument constructor (`kv_cache.hpp`) and the missing compile-only configuration "
           "(`t/CMakeLists.txt`) - each now carries a compiled suggested fix; the kernel-copy blocker is resolved.")

# Follow-up sentences appended to carried comments whose status changed or whose subject the delta touched.
FOLLOWUP = {
    "R1-14": ("The figures now agree with a recorded sweep (`exec/results/slot1/fused-sweep-v2.txt`: 1249.9 / 686.0, same ring) - good.  "
              "But that file is stamped `2026-08-18T18:34:53Z`, still the 18th in PDT, so where does 08-19 come from?  If there was no "
              "second run, s/2026-08-19/2026-08-18/.  And the command line that ff7269a9f recorded went out again in 901f30d8e, so a "
              "reader still has nowhere to go to reproduce 1250: this Note is now the only place the pair lives, so let's name the record "
              "and the command here, or drop the numbers.  The forwarding-stall \"6962P microbench\" at :142 still has no record at all."),
    "R1-37": ("The bench half is settled with the file.  The rest stands: `qk_mirror_128x4` still lands in `qk_s` and we `memcpy` 1 KB into "
              "`s_pages` per page, while the ~560 ns at `amx_attn_iface.hpp:137` (1250 vs 686) was measured on a path that never paid that "
              "copy - either size `s_pages` for 16 rows in the mirror build, or say so next to the number?"),
    "R1-65": ("The bench's `HD = 128` went with the file, so that part is done.  Still: `HD`/`NQ`/`ROWS` at :33-35 remain a third spelling "
              "of the kernel TU's `HEAD_SIZE`/`GROUP_HEADS`/`TILE_ROWS`, and `std::make_unique` at :80 and :122 still has no `<memory>`."),
    "R1-31": ("Also, `resize()` here zero-fills the new tail every time `items.size()` grows past the previous call's, and the pack "
              "(`pack_q_group_128x4`, or `pack_q_rows_128x4` in the mirror build) then writes the same 4 KB again - and it is 4 KB out per "
              "group, not the 512 B I wrote above.  Fixed `alignas(64)` storage sized by `max_minibatch_size` would settle this, the "
              "alignment contract, and the bitmap in one move; if the vector stays, at least `if (amx_qpack.size() < n) amx_qpack.resize(n)`."),
    "R1-17": ("With the histogram's home gone from the PR, the PR description is where its conclusion belongs; the question whether the "
              "code stays is unchanged."),
}

# Carried texts edited this round (a GitHub thread stays as written; these are our files): the page-share
# histogram's proposed home no longer exists in the PR.
TEXT_EDIT = {
    "R1-17": ("I'd record the histogram in `doc/intel-amx.md` and drop the code", "I'd record the histogram in the PR description and drop the code",
              "the proposed home of the histogram is now the PR description"),
    "R1-14": ("Keep them in the doc with the command that produced them, and reference that from here.",
              "Record the command that produced them where a reader can find it, and reference that from here.",
              "the round-1 sentence named a home for the numbers that is no longer in the PR"),
}

# R1-51 (blocker, src/amx_fused_bench.cpp:3): the file is deleted, so the thing he refused to approve is gone; the
# "with the command line that produced them" half is now asked in the R1-14 thread.
DROP = {
    "R1-51": ("blocking half resolved: src/amx_fused_bench.cpp deleted in ff7269a9f, no CMake/greppable trace left (amxqk, amxpl, "
              "transpose16x16, t_amx_attention, amx_fused_bench: 0 hits at 234c02bde); remaining half (the command line that produced "
              "the numbers) was recorded by ff7269a9f and removed again by 901f30d8e - now asked in the R1-14 follow-up. Status "
              "verifier + refuter: PARTIAL, still_blocker=false."),
}
SNIP_OVERRIDE = {}
TRIAGE = {}
TRIAGE_PREDICTION = {}

# Evidence text for the five comments made obsolete by the deletion (the status builder's file:line join
# renders the deleted file as ':0').
for _cid in ("R1-52", "R1-53", "R1-54", "R1-55", "R1-56"):
    ST[_cid]["evidence"] = ("src/amx_fused_bench.cpp deleted in ff7269a9f (732 lines); nothing it commented on survives at 234c02bde "
                            "(git grep amxqk / amxpl / t_amx_attention / transpose16x16 / 'Bill' / amx_fused_bench: no hits)"
                            + ("; the amx_attn.cpp:240-241 comment that cited the `amxqk` variant now describes the kernel only" if _cid == "R1-52" else ""))
# R1-14's verification record, rewritten for the tree as it is now (the agent text referred to a file no longer in the PR).
ST["R1-14"]["remaining"] = ("met: the unrecorded 982 figure is gone; 1250/686 match fused-sweep-v2.txt:14/:30 (amx44 / amxqk, Nq=4, pages=1). "
                            "Not met: the Note states the numbers as facts with no record or command a reader can follow (the record "
                            "ff7269a9f wrote was removed again by 901f30d8e); the date 2026-08-19 at :138 does not match the sweep header "
                            "2026-08-18T18:34:53Z (mtime 2026-08-18 11:38 -0700; exec/logs/p0-fused-sweep.log lists both sweeps on 08-18); "
                            "the '6962P microbench measured no stall' sentence at :142 has no recorded source anywhere. '6962P' is not in "
                            "the sweep header (cpu 96 is a core index); it rests on the PR body's host line.")
ST["R1-14"]["evidence"] = "h/tron/kernels/amx_attn_iface.hpp:137-142; exec/results/slot1/fused-sweep-v2.txt:1,14,30; exec/logs/p0-fused-sweep.log"

FIXED_VOICE = {
    "R1-51": "The copy is gone, good.  The command line went with 901f30d8e - see `amx_attn_iface.hpp:138`.",
}

CODEX = [
    dict(id=3858305367, path="h/tron/models/self_attention.hpp", line=1361, author="jeremyconner1975",
         body=("The kernel interface requires each packed-Q buffer to be 64-byte aligned, but `std::vector<uint16_t>` guarantees only "
               "`alignof(uint16_t)`. Since each slice is exactly 4096 bytes, every query inherits the base misalignment and TILELOADD can "
               "repeatedly straddle cache lines. Could this use a 64-byte-aligned allocator or aligned fixed storage?\n\n"
               "- Codex review, submitted at Jeremy's request")),
    dict(id=3858305362, path="h/tron/models/self_attention.hpp", line=1367, author="jeremyconner1975",
         body=("`amx_on` only checks geometry and CPU support, so every eligible page range executes LDTILECFG/TILERELEASE and packs each "
               "query before the dense-page predicate is evaluated. Partial pages, masked/sliding-window pages, and null-mirror fallbacks "
               "therefore pay AMX setup plus a 4 KB pack even though every page uses AVX. Could we lazily begin the region and pack Q only "
               "when the first page actually satisfies the dense predicate?\n\n- Codex review, submitted at Jeremy's request")),
]

NEW = [
    # R5-01 - Note [Mirror orientation]: the ~560 includes a per-page scalar Q pack only the canonical bench variant paid
    dict(file="h/tron/kernels/amx_attn_iface.hpp", line=139, snip=(133, 141), tag="A3/A4", blocker=False,
         text=("IIUC the `amx44` variant re-ran the scalar `pack_q` inside `run_pages` (so once per page at `pages=1`) while `amxqk` built "
               "`Qpad` once before the timer, and production packs Q once per (token, kv_head) per section - so isn't part of the 560 a "
               "bench artifact rather than transpose or score traffic?  The 512/16384-page rows, where the pack is amortized, show ~500.  "
               "Either name it in the 'combined' list or quote the amortized gap and drop 'L2-resident'."),
         note=("new in round 5 (R5-01); finder 'numbers' #3, refuter PARTIAL (line refs corrected), would-he-raise=yes (he commented on "
               "pack_q :264 and the ':279 Cost is EXCLUDED' line in round 1). Verified by the orchestrator in the d176c88b3 tree: "
               "amx_fused_bench.cpp:610-614 run_pages -> `if (!is_qk_mirror) pack_q(Q.data(), nq, Bp);` before the page loop (:618), timed "
               "per run_pages call (:721-726); :599-606 build Kmir/Qpad once for amxqk outside the timer. Sweep: 1249.9-686.0 = 563.9 "
               "(pages=1); 1971.6-1470.2 = 501.4 (pages=512); 2294.0-1799.8 = 494.2 (pages=16384). Refuter's pack_q re-timing (65-95 ns "
               "on a non-6962P host, est.) is consistent with the ~62 ns shrink but is NOT quoted in the comment. Production pack-once: "
               "self_attention.hpp:1354-1355 comment, :1419 mask test, :1424/:1429 pack, :1434 mask set.")),
    # R5-02 - kernel TU header narrates the deleted benchmark (B11)
    dict(file="src/tron/kernels/amx_attn.cpp", line=3, snip=(1, 6), tag="B11", blocker=False,
         text=("This describes a benchmark that is no longer in the tree, and the PR description already says so.  The Note this points at "
               "already names `t_amx_numerics` as what pins the kernels; flush the sentence."),
         note=("new in round 5 (R5-02); found by finders 'numbers' and 'tests' independently, both refuters PARTIAL->confirmed with the "
               "wording used here. Verified: amx_attn.cpp:3-6 introduced by ff7269a9f (delta.diff @@ -1,8 +1,9 @@); pr_body.md:7 'is not in "
               "the tree (git history up to d176c88b3)'; amx_attn_iface.hpp:46-47 (Note [AMX attention dispatch]) already says "
               "'t/t_amx_numerics.cpp pins the kernels inside that envelope'; `git grep d176c88b3` at HEAD hits only this line. Persona B11 "
               "('describing dinosaurs ... Flush it.'), 26 such comments in 2026; R1-15 applied the same rule on this PR.")),
    # R5-03 - reply in the Codex thread on alignment (= R1-12)
    dict(file="h/tron/models/self_attention.hpp", line=1361, snip=(1358, 1369), tag="C2/A3", blocker=False,
         reply_to=dict(id=CODEX[0]["id"], author=CODEX[0]["author"], body=CODEX[0]["body"]),
         text=("Codex has a point about the alignment, and it's the same one as my question at `amx_attn_iface.hpp:102`: `amx_qpack` is a "
               "`std::vector<uint16_t>`, so every 4 KB slice inherits whatever `malloc` handed us (16 mod 64 in nearly every allocation "
               "when I tried it on glibc; 0 mod 64 only by accident).  The other two 64B contracts (`o` at :123, `s` at :163) are honored by "
               "`alignas(64)` storage at `self_attention.hpp:1568` and `:1652`; this is the only one that isn't.  Let's either give it "
               "`alignas(64)` storage or drop \"64B-aligned\" from the contract (:102 and :156); whether the split rows actually cost "
               "anything is a per-page timing with the pack at 0 vs 16 mod 64, not something to assert either way."),
         note=("new in round 5 (R5-03), a reply he would post in Codex thread 3858305367 (persona C2: answers bot findings); folds into R1-12 "
               "(round 1, same defect; its ':135' reference is :156 at HEAD). Finder 'codex' #1, refuter PARTIAL (histogram counts replaced by "
               "the qualitative statement). Verified by the orchestrator on this host (glibc): std::vector<uint16_t> resized to 4 KB..1 MB "
               "has data() % 64 = 48 (4 KB) or 16 (16 KB..1 MB), never 0; slices are 4096 B (Q_PACK_ELEMS_2048 * 2, iface:83-84) so every "
               "slice keeps the base residue; loads at amx_attn.cpp:137 (64 B stride) and :253 (256 B stride) read 16 rows x 64 B; the `o` "
               "and `s` contracts are met by alignas(64) at self_attention.hpp:1568-1569 and :1652. Codex threads have no replies (gh api, "
               "in_reply_to_id null on both).")),
    # R5-04 - reply in the Codex thread on the eager region/pack (opposite direction from R1-31)
    dict(file="h/tron/models/self_attention.hpp", line=1367, snip=(1358, 1370), tag="C2/A1", blocker=False,
         reply_to=dict(id=CODEX[1]["id"], author=CODEX[1]["author"], body=CODEX[1]["body"]),
         text=("Codex is right on the facts - `begin_region()` runs and each token's first visible in-window page pays a 1 KB-in / 4 KB-out "
               "pack (not the 512 B I wrote at :1361) before any page has passed the dense test, and PV only runs `if (did_amx)`, so a "
               "token whose range has no dense page uses its pack nowhere.  Two precisions: wholly masked or out-of-window pages skip at "
               ":1389/:1392 before the pack, and a null mirror with `amx_on` true means the arena allocation failed (`kv_cache.hpp:1055`, "
               "`:1060`).  I'd still go the other way from what Codex asks: the region pair is ~229 cycles against 686-1250 ns per dense "
               "page, so pack all `items.size()` groups up front and delete the bitmap.  If the calls with no dense page matter in the "
               "served shapes, count them per decode step first, before adding a second lazy mechanism inside `apply_page_tok`."),
         note=("new in round 5 (R5-04), a reply he would post in Codex thread 3858305362; folds into R1-31 (round 1, which asks for the "
               "opposite - eager packing). Finders 'codex' #2 and 'scope' #2 both verified Codex against HEAD; refuters PARTIAL (line refs, "
               "the unmeasured pack cost, the visibility skip) - corrections folded in. Verified by the orchestrator: amx_on = shape && "
               "available() (:1360); begin_region under if (amx_on) at :1367-1369 before the page loop, end_region :1468; skips at :1389 "
               "(visible) and :1392-1394 (window) precede the pack; pack block :1410-1438 (mask test :1419, pack_q_rows_128x4 :1424 / "
               "pack_q_group_128x4 :1429, mask set :1434) runs before apply_page_tok (:1440) tests the dense predicate (:1556-1558); PV under "
               "if (did_amx) (:1631); pack sizes amx_attn.cpp:108-120 (memset 4 KB + 512 elements) and :234-238 (memcpy 1 KB + memset 3 KB); "
               "~229 cycles per pair is the figure the PR carries for the LDTILECFG/TILERELEASE pair (no in-tree record); null plane with "
               "amx_on true only via kv_cache.hpp:1060-1063 nothrow new failing, since the arena gate (:1055) is the OR of shape_ok over the "
               "plugin's kernels (:182-190).")),
]

# ------------------------------------------------------------------ suggested fixes (added at jhan's request)
_SITE_ROWS = [(w, cur.replace("\n", " "), new.replace("\n", " ")) for w, cur, new in _SITES["llama_unit"] + _SITES["arena_leak"]]

FIX = {
    # ---- blocker R2-03: the 3-argument book / try_create default amx_mirror_eligible to true
    "R2-03": dict(
        plan=[
            "Delete the 3-argument `book` constructor (:764-769) and its comment; the 4-argument constructor becomes the only one, with a comment that says why there is no default.",
            "Delete the 3-argument `try_create` overload (:975-984 with its comment); the STORY-127 comment stays on the 4-argument one.",
            "Update the `sequence_cache_behavior` concept (:1352-1357) to the 4-argument forms, so the concept describes the interface that exists.",
            "Pass the flag at every construction site in `t/` (29 lines in `t_llama_unit.cpp`, 2 in `t_amx_arena_leak.cpp`; table below). `true` everywhere preserves today's behaviour exactly; the mirror tests (`t_llama_unit.cpp:257`, `:272`, `:338`, `:1004`, `:1076-1077`, `:1221`, `t_amx_arena_leak.cpp:79`) need `true`; the rest can be tightened to `false` afterwards where the mirror is irrelevant - that is the author's call, not part of this fix.",
            "Production is untouched: `full.hpp:832` and `:1456` already pass the flag. R2-13 (both arena-leak arms through `try_create`) and R2-14 (the control's wording) stay as separate items; R2-14's control line is covered by the table.",
        ],
        hunks=[
            dict(file="h/tron/models/kv_cache.hpp", lines=(764, 773), what="replace the legacy constructor and both comments with one comment on the remaining constructor (line 774 `book(size_t n_pages,` follows unchanged)", text=(
                "  // `amx_mirror_eligible` is the scheduler's\n"
                "  // amx_mirror_eligible(plugin::attention_kernels): a model without an\n"
                "  // AMX-eligible attention shape allocates no mirror arena. Deliberately no\n"
                "  // default - a book that may never read the arena must not get one by\n"
                "  // omission - so tests pass the flag explicitly.")),
            dict(file="h/tron/models/kv_cache.hpp", lines=(977, 986), what="delete these ten lines (the defaulted parameters, the delegating body, the blank and the 'Same, carrying ...' comment plus the duplicated `TRON(nodiscard)` / `static ... try_create(size_t n_pages,` header); lines 968-976 and 987-989 then read", text=(
                "  // Fallible KV-book factory for cache growth (STORY-127 /\n"
                "  // memory_pressure_governor §8). ... log_kv_footprint fires exactly once, in\n"
                "  // the adopt-constructor.\n"
                "  TRON(nodiscard)\n"
                "  static std::shared_ptr<book> try_create(size_t n_pages,\n"
                "      size_t storage_slot_count,\n"
                "      bool support_eagle,\n"
                "      bool amx_mirror_eligible) noexcept {")),
            dict(file="h/tron/models/kv_cache.hpp", lines=(1352, 1357), what="the concept requires the 4-argument forms", text=(
                "    bool support_eagle,\n"
                "    bool amx_mirror_eligible,\n"
                "    kv_storage_offset offset) {\n"
                "  requires std::constructible_from<T, size_t, size_t, bool, bool>;\n"
                "  {\n"
                "    T::try_create(n_pages, storage_slot_count, support_eagle, amx_mirror_eligible)\n"
                "  } -> std::same_as<std::shared_ptr<T>>;")),
        ],
        sites=_SITE_ROWS,
        note=("Compiled, not run: the three header hunks plus all 31 call-site edits were applied to a scratch copy of the tree and "
              "syntax-checked (`clang++-19 -fsyntax-only`, the build's own flags from compile_commands.json, TRON_AMX_DISPATCH and "
              "TRON_AMX_K_MIRROR ON) for t/t_amx_arena_leak.cpp, t/t_llama_unit.cpp (all 29 sites) and a TU that instantiates "
              "`full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>` (covers `full.hpp:832`): 0 errors, 0 warnings. Negative check: "
              "the unpatched test against the patched header fails at :79 and :132 with 'no matching constructor', so the default is "
              "really gone. Not done: linking or running the tests; a `false` sweep over the mirror-irrelevant sites. Diffs and logs: "
              "exec/review-pipeline/r5/fix/ (kv_cache.diff, t_llama_unit.diff, t_amx_arena_leak.diff, syntax_*.log). `T::n_slots` is "
              "the static member the concept already relies on (kv_cache.hpp:725), so `book_t::n_slots` is the right spelling of the "
              "old default.")),
    # ---- blocker R1-58: no compile-only configuration for the flagged code
    "R1-58": dict(
        plan=[
            "Add an OBJECT library next to `heterogeneous_scheduler_compile` (:356-359) that compiles the AMX code with both flags defined for that library alone, whatever the build's options are: one TU that instantiates the full scheduler for an eligible shape, plus the kernel TU with its `-mamx-*` flags. It is part of `all` like the precedent, so every CI build compiles the dispatch, the `save_k` write-through, the mirror arena and the kernels; no CTest entry.",
            "That covers the 'can't rot silently' half. The other half of the comment stands: record in the PR how the three AMX tests were run on the 6962P host (the `ctest -R 't_amx_'` log from delphi-3bda with `-DTRON_AMX_DISPATCH=ON -DTRON_AMX_K_MIRROR=ON`), since no CI host has AMX.",
        ],
        hunks=[
            dict(file="t/CMakeLists.txt", lines=(356, 359), what="keep the precedent block and add the AMX one after it", text=(
                "# Compile-time coverage for scheduler/cache capability boundaries. This target\n"
                "# deliberately has no CTest entry: it instantiates templates but runs no model.\n"
                "add_library(heterogeneous_scheduler_compile OBJECT heterogeneous_scheduler_compile.cpp)\n"
                "target_link_libraries(heterogeneous_scheduler_compile PRIVATE tron full_scheduler)\n"
                "\n"
                "# Compile-time coverage for the AMX software-attention paths (see\n"
                "# Note [AMX attention dispatch]): both flags defined for this object library\n"
                "# alone, so the #ifdef'd dispatch, save_k write-through, mirror arena and the\n"
                "# kernel TU compile in every configuration, including the default with the\n"
                "# options OFF. No CTest entry: it instantiates templates and runs no model.\n"
                "add_library(amx_attention_compile OBJECT amx_attention_compile.cpp\n"
                "  ../src/tron/kernels/amx_attn.cpp)\n"
                "target_compile_definitions(amx_attention_compile PRIVATE TRON_AMX_DISPATCH TRON_AMX_K_MIRROR)\n"
                "set_source_files_properties(../src/tron/kernels/amx_attn.cpp PROPERTIES\n"
                "  COMPILE_OPTIONS \"-mamx-tile;-mamx-bf16;-mavx512f;-mavx512bw;-mavx512vl;-mavx512dq;-mavx512bf16;-mavx2;-mfma\")\n"
                "target_link_libraries(amx_attention_compile PRIVATE tron full_scheduler)")),
            dict(file="t/amx_attention_compile.cpp", lines=None, what="new file", text=open(_os.path.join(_R5, "fix", "amx_attention_compile.cpp")).read().rstrip("\n")),
        ],
        note=("The TU was syntax-checked against the tree (`clang++-19 -fsyntax-only` with the flags heterogeneous_scheduler_compile.cpp "
              "is built with, i.e. -DTRON_AMX_DISPATCH -DTRON_AMX_K_MIRROR): 0 errors in 26 s, and both static_asserts hold "
              "(llama-3.1-8b is 32/8/128, ratio 4). The CMake hunk was NOT configured or built - no cmake run was made in your build "
              "directory; check it with `cmake --preset native && cmake --build gen --target amx_attention_compile` in a build with "
              "both options OFF. Assumptions to confirm at that step: `set_source_files_properties` here applies to the target defined "
              "in this directory (CMake 3.19 minimum, so `TARGET_DIRECTORY` is also available if preferred); with the options ON the "
              "kernel TU is compiled twice (once into `tron`, once here) - harmless for an object library nothing links; the duplicate "
              "-D flags are identical. `heterogeneous_scheduler_compile.cpp.o` is in `ninja -t targets all`, so the precedent (and this "
              "target) build in CI without a test entry. Source: exec/review-pipeline/r5/fix/amx_attention_compile.cpp, syntax_compile_tu.log.")),
    # ---- R1-14: the Note has to carry the provenance itself now
    "R1-14": dict(lines=(137, 139), text=(
        "// through memory and transpose it - a ~560 ns/page whole-path cost at\n"
        "// width 4 (1250 vs 686 ns per L2-resident page: exec/results/slot1/\n"
        "// fused-sweep-v2.txt in the campaign workspace, 2026-08-18, 6962P core 96,\n"
        "// `taskset -c 96 ./amx_fused_bench 4 200000 amx44 1` / `amxqk` on the\n"
        "// stand-alone benchmark at d176c88b3; ~500 ns once that benchmark's per-page\n"
        "// scalar Q pack is amortized, 512-page ring 1972 vs 1470 - the pack, the\n"
        "// transpose and the score round trip were not isolated). NOT a"),
        note=("Replaces Note lines 137-139 and keeps :140 ('store-forwarding stall: 64-byte') reading on. Names the record, the host, the "
              "corrected date (file header 2026-08-18T18:34:53Z), the command ff7269a9f recorded and 901f30d8e removed, and the pack "
              "artifact R5-01 asks about (pages=512 row: 1971.6 vs 1470.2). 'core 96' is the header's 'cpu 96'; '6962P' rests on the PR "
              "body's host line, not on the sweep file. The '6962P microbench' sentence at :140-142 is unchanged: R1-14's ask for a "
              "record of that measurement is still open and no replacement text can supply one.")),
    "R5-02": dict(lines=(1, 6), text=(
        "// AMX software-attention kernels. See Note [AMX attention dispatch]\n"
        "// (in amx_attn_iface.hpp). The ONLY translation unit compiled with\n"
        "// -mamx-tile/-mamx-bf16."),
        note=("Drops the history sentence; the Note already points at t/t_amx_numerics.cpp (amx_attn_iface.hpp:46-47), and the bench's "
              "fate is in the PR description and the ff7269a9f commit message. Line 7 (blank) and the includes are untouched.")),
}

METHOD = [
    "Target: PR head <code>234c02bde</code> (checked out clean in <code>~/workspace/tron-amx</code>, verified by the generator). Round 4 reviewed <code>d176c88b3</code>. Delta: <code>ff7269a9f</code> (deletes <code>src/amx_fused_bench.cpp</code>, rewrites the numbers in Note [Mirror orientation] and three <code>amx_attn.cpp</code> comments), <code>901f30d8e</code>, <code>a5ef65761</code> and <code>234c02bde</code>; comments anchored in a file that is no longer in the PR are not carried or listed.",
    "Only comments anchored in the changed files, or whose text cites the deleted bench (R1-37, R1-65), could change status: re-anchored by 4 status verifiers (header, kernel TU, bench, and the removed file) and checked by 4 adversarial status refuters; every verdict was confirmed. The other carried comments keep their round-4 lines and text (files identical to <code>d176c88b3</code>).",
    "Finders: 4 independent agents over the delta only, each with one lens (comment/number accuracy; scope, CI and PR-description coverage; the two Codex findings; tests and validation), given the open comments as do-not-repeat. 11 candidates; one adversarial refuter per candidate (default refuted). All 11 survived as PARTIAL - substance confirmed, a line number or wording corrected - and the corrections are folded into the comment texts above. Three finders found the date error independently; two found the header sentence independently.",
    "Orchestrator's own checks, each recorded in the comment's verification line: the glibc alignment of <code>std::vector&lt;uint16_t&gt;</code> (a compiled program on this host: 48 mod 64 at 4 KB, 16 mod 64 at 16 KB..1 MB); the bench's per-<code>run_pages</code> <code>pack_q</code> in the <code>d176c88b3</code> tree; the pack site's position relative to the dense predicate at HEAD; the Codex threads' reply count (0); the CI history (<code>gh run list</code>, <code>gh run view --json jobs</code>, per-commit check-runs: 0 for the eight commits after bbb55ae5f).",
    "Suggested fixes for the two blockers (added at your request): applied to a scratch copy and syntax-checked with the build's own compile commands (<code>-fsyntax-only</code>, clang++-19, both AMX options ON) - 31 call sites + 3 header hunks for R2-03, and the new compile-only TU for R1-58 - with a negative check that the removed default really is gone. Not built, not linked, not run; the CMake hunk was not configured. Diffs, the TU and the logs are in <code>exec/review-pipeline/r5/fix/</code>.",
    "Numbers the delta cites were checked against the recorded sweep <code>exec/results/slot1/fused-sweep-v2.txt</code> (outside the tron tree): 1249.9 / 686.0 at pages=1 (like-for-like), 1971.6 / 1470.2 at pages=512, 2294.0 / 1799.8 at pages=16384; header stamp 2026-08-18T18:34:53Z. The refuter's re-timing of <code>pack_q</code> (65-95 ns, est., on a non-6962P host) is context only and appears in no comment. '6962P' for the sweep rests on the PR body's host line; the sweep header names only 'cpu 96'.",
    "Written 2026-08-25. Voice from <code>~/workspace/reviewers/alexey.md</code>; the persona's most common review is an empty approval, so nothing was added that his lenses would not raise. Suggested-fix blocks are added at your request and labelled as such; the 2026 Alexey describes fixes, he does not paste them.",
]

CLEAN = [
    ("1250 / 686 / ~560 ns (Note :137-138)", "fused-sweep-v2.txt:14 amx44 Nq=4 pages=1 per_page_ns=1249.9 and :30 amxqk Nq=4 pages=1 per_page_ns=686.0; 1249.9-686.0 = 563.9 -> '~560'; same ring and iteration count, so like-for-like as ff7269a9f claims; both variants report the same useful FLOP count (104.9 x 1249.9 = 131114 vs 191.1 x 686.0 = 131095), i.e. both are whole-path QK+softmax+PV; the round-4 982 figure is in no recorded file", "exec/results/slot1/fused-sweep-v2.txt:1,14,30; d176c88b3:src/amx_fused_bench.cpp:24,538"),
    ("'L2-resident page' and '6962P'", "pages=1 ring = one K page (16 KB) + one V page (16 KB) + one mirror page, the bench's own label ('1 = L2-resident page', d176c88b3 bench :27-28); the sweep header names only 'cpu 96' - '6962P' is consistent with the PR body's host line and every other slot1 log from that day but is not in the record itself", "d176c88b3:src/amx_fused_bench.cpp:27-28; pr_body.md; exec/results/slot1/perf-decode-logs/perf-layout-only.log:9"),
    ("Mirror-write cost not in the 686", "the bench excluded the K-mirror pack from its timed loop; in production that write is paid once per token row at save_k (model.hpp:2790-2795) and amortized over every later read of the page, so a per-page read-cost comparison is fair without a qualifier; the Q-pack asymmetry (R5-01) is different because it sat inside the timed loop of one variant only", "d176c88b3:src/amx_fused_bench.cpp:279-280,599-606; h/tron/models/model.hpp:2790-2795"),
    ("Work region = one apply_page_range call", "begin_region (self_attention.hpp:1369) and end_region (:1468) bracket one apply_page_range call; sole call site run_sections :1043, once per kv_section, for the ready and the pending plan; the '~229 cycles' per pair the PR quotes has no in-tree source", "h/tron/models/self_attention.hpp:1038-1045,1345,1367-1370,1468"),
    ("amx_attn.cpp :156-158 and :240-241 comment rewrites", "both now describe the code only (width-4 specialization; S[16 q][64 tok] = Q . K^T, no transposing store) and no longer point at the deleted file; loop and declaration match", "src/tron/kernels/amx_attn.cpp:156-159,240-245"),
    ("No stale pointer to the deleted benchmark", "git grep at 234c02bde for amx_fused_bench, fused_bench, fused-page benchmark, amxqk, amx44, amx62, t_amx_attention, fused-sweep: no hits; the only mention is the history sentence at amx_attn.cpp:3-6 (R5-02); 'git history up to d176c88b3' is accurate (blob present at d176c88b3, absent at ff7269a9f) and stays reachable if #3879 merges with a merge commit as main's history does", "git grep; git cat-file -e d176c88b3:src/amx_fused_bench.cpp"),
    ("Delta scope (A9) and title", "the delta touches AMX-attention files only; no CI, dependency or neighbouring-code changes; the PR title matches the 14-file content; commit messages describe exactly their diffs (no commit-message comment warranted)", "git log d176c88b3..234c02bde"),
    ("Delta touches no test; R1-58 (blocker) unchanged", "git diff d176c88b3 234c02bde -- t/ is empty; t/CMakeLists.txt:365-367 still register the three AMX tests with no compile-only target (precedent heterogeneous_scheduler_compile :356-359); default build SUCCEED('... nothing to test') at t_amx_numerics.cpp:229-231, t_amx_mirror.cpp:85-87, t_amx_arena_leak.cpp:141-143; no CI job passes -DTRON_AMX_DISPATCH (git grep -i amx over .github, CMakePresets.json, flake.nix, bin/ci, bin/slice: nothing)", "t/CMakeLists.txt:356-367; .github/workflows/cmake-single-platform.yml:368; src/tron/CMakeLists.txt:170,177"),
    ("What validates the kernels now that the bench is gone", "t_amx_numerics.cpp: qk_canonical_128x4 vs the production dotter with a double envelope (:89-109); weights_times_v_128x4 vs an exact double RNE reference and a truncation envelope (:195-224, non-vacuity check :224); qk_mirror_128x4 / pack_q_rows_128x4 / scatter_k_mirror only by bit-identity with the canonical kernel (:152, under TRON_AMX_K_MIRROR); the self_attention.hpp dispatch glue and the per-page softmax update have no direct test (open R1-69)", "t/t_amx_numerics.cpp:75-225; t/t_amx_mirror.cpp:23-81"),
    ("PR body claims added since round 4", "'registered DISABLED so no CI lane runs it': t/CMakeLists.txt:195 DISABLED TRUE inside BUILD_INGEST_MODELS, bin/slice:875-878 drops DISABLED entries, both CI lanes go through bin/slice; 'not in the tree (git history up to d176c88b3)': correct; '1250 vs 686 ns per L2-resident page at width 4': matches the sweep; the archive link for the design write-up is the author's decision, not a review item", "pr_body.md:7-8; t/CMakeLists.txt:195; bin/slice:875-878"),
    ("CI history (fact used in the body)", "draft PR, no labels; 17 runs on jhan-amx-p0 (2026-08-19 .. 2026-08-25T00:22Z), every 'CMake and CTest' run = ci-machinery-filter + lint only (build, test-host, test-fpga, test, benchmark all skipped; lint failed on the two 08-19 runs), every 'Benchmark Only PR' run skipped; the eight commits after bbb55ae5f (cc8a86bb3 .. 234c02bde) have 0 workflow runs and 0 check-runs (cause unverified). Build/test jobs are gated by `!draft || contains(labels, 'Run CI')`", ".github/workflows/cmake-single-platform.yml:5-6,23,173-176,619-623; gh run list / gh run view 32793335105 --json jobs; gh api commits/<sha>/check-runs"),
    ("Codex arithmetic and the other 64B contracts", "each packed-Q slice is exactly 4096 B (Q_PACK_ELEMS_2048 * 2, static_assert iface:84), so the slice residue mod 64 equals data()'s; the `o` (iface:123) and `s` (iface:163) contracts are met by alignas(64) storage at self_attention.hpp:1568-1569 and :1652 - the Q pack is the only violator", "h/tron/kernels/amx_attn_iface.hpp:83-84,102,123,156,163; h/tron/models/self_attention.hpp:1413,1568-1569,1652"),
    ("Codex 'eager region/pack' - what is exactly true", "region bracket eager under if (amx_on) (:1367-1369/:1468); pack once per (token, kv_head, call) via the per-call bitmap (:1366,:1419,:1434), not per page; wholly invisible (:1389) and wholly out-of-window (:1392-1394) pages skip before the pack; dense predicate :1556-1558; PV only if (did_amx) (:1631); a null mirror plane with amx_on true happens only when the nothrow arena allocation failed (kv_cache.hpp:1055,1060-1063); pack sizes 4 KB written (amx_attn.cpp:108-120, :234-238) - Codex's '4 KB' is right, R1-31's '512-byte copies' undercounts", "h/tron/models/self_attention.hpp:1354-1370,1389-1394,1410-1440,1468,1550-1558,1631; src/tron/kernels/amx_attn.cpp:108-120,234-238; h/tron/models/kv_cache.hpp:1050-1063"),
    ("Blocker fixes: what the syntax checks covered", "R2-03: patched kv_cache.hpp + t_amx_arena_leak.cpp (0 errors), + t_llama_unit.cpp with 29 edited sites (0 errors, 0 warnings), + a TU instantiating full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>> (covers full.hpp:832's 4-argument try_create; 0 errors); negative check: the unpatched test fails at :79 and :132 ('no matching constructor'). R1-58: the same TU is the proposed amx_attention_compile.cpp; its two static_asserts (shape_ok(128, 4); amx_mirror_eligible over llama-3.1-8b's attention_kernels) hold", "exec/review-pipeline/r5/fix/syntax_arena.log, syntax_llama_unit.log, syntax_compile_tu.log, fixcheck.py"),
]
