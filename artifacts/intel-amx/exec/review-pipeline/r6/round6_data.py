# Round-6 data for gen_review6.py (head 3fa11d911). His voice: BODY, FOLLOWUP, FIXED_VOICE, NEW[].text, and the
# predicted replies in status.json. Everything else is the verification record for jhan. Sources: r6/workflow_out.json
# (wf_c1bf5118-492: 8 status verifiers + 8 status refuters over the 66 items in changed files, 4 finders on the delta
# -> 8 candidates -> 8 refuters: 5 confirmed/partial, 3 refuted), the author's decision record PR3879/triage.json,
# and r6/fix/ (the compile-checked single-constructor variant behind the R2-03 suggested fix).
import os as _os
_R6 = R6  # the generator exec()s this file

VERDICT = "CHANGES_REQUESTED"

BODY = (
    "Eleven threads closed this round - the `strcmp` rule (R1-16, R1-48), the pack padding zeroed once and the `cvtne2ps_pbh` note "
    "(R1-49, R1-50), the comment trims (R1-33, R1-43, R1-45, R1-67, R5-02), the `node_base` default (R2-09), the control case that now "
    "says what it means (R2-14) - good.\n\n"
    "R2-03: the default flip does the half that mattered.  The two delegating overloads and the 3-argument clauses of "
    "`sequence_cache_behavior` can follow; one constructor with defaulted trailing parameters would do it without touching a test.\n\n"
    "Two sentences the delta introduced are wrong, one of them mine: R1-15, \"anywhere else the arena RAM is wasted\" - nothing is "
    "allocated on a host without AMX, `maybe_allocate_mirror_arena` returns first; and R6-01, \"so callers can reuse the same buffer\", "
    "which stopped being true when the packers stopped zeroing the padding.\n\n"
    "R1-47 and R1-58: so be it, replies inline.\n\n"
    "What still blocks from my side is the stack of comment sentences that do not match the code - none of them big, all of them wrong "
    "as written:\n"
    "- R1-10 - Note [Tile stores write 16 rows] says every output buffer receives 16 rows; `qk_canonical_128x4` writes 4.\n"
    "- R3-02 - \"every shape literal in the AMX code derives from these three\"; `DIM_STEP`, `PANEL_ELEMS`, the pack-index 16s and the store offsets are still literals.\n"
    "- R2-06 - \"the reader and the writers can never disagree\"; the two rebuild writers key on a non-null plane, not on `shape_ok`.\n"
    "- R1-12 - the 64B-aligned contract on the Q pack buffer, which `std::vector<uint16_t>` does not meet (Codex's point too).\n"
    "- R1-14 - the date on the 1250/686 pair is not the date of the sweep that produced it, and the Note names no record a reader can follow.\n"
    "- R1-15, R6-01 - the two sentences above.\n"
    "- Smaller ones of the same kind: R3-04, R1-20, R2-07, R1-21, R1-26, R2-08, R1-41, R2-11, R2-12, R3-05, R4-01.\n\n"
    "The description still says nothing about `kv_block_planes`, `v_data`/`v_base`, the two `#error`s, the `fill_random` rebuild, or the "
    "`amx_mirror_eligible` plumbing through `node_base`, and no build or test job has run on any commit of this PR."
)

TAKE = ("Round 6 in one line: __F__ comments fixed by the six commits (section 2); __D__ declined or deferred by you with his predicted "
        "reply (section 2a); __O__ carried over (nine with a follow-up, one of them his correction of his own round-1 wording); "
        "__N__ new (the pack-buffer reuse sentence that the padding change made false). Blockers 2 -> __B__: R2-03's allocating "
        "default is gone (remainder is non-blocking, with a compiled single-constructor fix attached) and R1-58 is deferred by decision.")
TAKE_MD = ("**Round 6 in one line:** __F__ comments fixed by the six commits (section 2); __D__ declined or deferred by you with his predicted "
           "reply (section 2a); __O__ carried over (nine with a follow-up, one of them his correction of his own round-1 wording); "
           "__N__ new (the pack-buffer reuse sentence that the padding change made false). Blockers 2 -> __B__: R2-03's allocating "
           "default is gone (remainder is non-blocking, with a compiled single-constructor fix attached) and R1-58 is deferred by decision.")

# ---- status overrides (facts the verifiers established but the status field cannot carry)
# R1-15: the author applied his round-1 wording; the finders showed the new consequence clause is false. He corrects himself.
ST["R1-15"].update(status="PARTIAL", remaining=("275fa89a0 applied the round-1 suggestion near-verbatim; its consequence clause 'anywhere else the "
    "arena RAM is wasted' (:153-154) is false: maybe_allocate_mirror_arena returns at kv_cache.hpp:1057 when available() is false, so a "
    "non-AMX host allocates no arena (Note [K mirror parallel arena] :558-561, t_amx_arena_leak.cpp:95 and the PR body all say so). "
    "Finder 'text' #1, refuter PARTIAL (wording), would-he-raise=yes - his own phrasing, corrected in his voice."),
    evidence="h/tron/kernels/amx_attn_iface.hpp:152-154; h/tron/models/kv_cache.hpp:1057; t/t_amx_arena_leak.cpp:95", still_blocker=False)
# R2-06: the carried text's clause about the 3-argument forms is stale since b2010bee9 (they pass false); the rest stands.
ST["R2-06"]["remaining"] = ("sentence unchanged; the two rebuild writers still key on a non-null plane, not on shape_ok; the carried text's "
    "'the 3-argument book forms pass true' is stale since b2010bee9 (they pass false) - the un-gated path is now the eight test sites that pass true")

# Follow-up sentences appended to carried comments (his voice).
FOLLOWUP = {
    "R1-14": ("This is marked done, but :140 still says 2026-08-19 and the Note still names neither the record nor the command - "
              "the sweep we agree on is stamped `2026-08-18T18:34:53Z`."),
    "R1-15": ("Is the arena RAM wasted anywhere?  On a non-AMX host `available()` is false and `maybe_allocate_mirror_arena` returns "
              "before allocating (`kv_cache.hpp:1057`; Note [K mirror parallel arena] and the PR description both say non-AMX hosts pay "
              "nothing), so the mirror's cost is the kv_bytes/2 plus the save_k write-through on the AMX hosts that do run it.  Let's say "
              "that instead - my round-1 phrasing was wrong."),
    "R2-03": ("The allocating default is gone, which was the part that mattered.  What still keeps the 3-argument forms alive is the "
              "tests and `sequence_cache_behavior` at :1356-1358, which now requires an interface production never calls (`full.hpp:834` "
              "passes four) - shall we move the concept to the 4-argument forms and drop the two overloads, or is there a caller I am "
              "not seeing?  Can be a follow-up PR if desired."),
    "R2-06": ("Since b2010bee9 the 3-argument forms pass false, so the un-gated writers are now the eight test sites that pass true; "
              "\"it holds for books the scheduler creates\" is still the true sentence, and the Note still does not say it."),
    "R2-07": ("b2010bee9 dropped \"only\" but kept \"the scheduler passes\": the scheduler still goes `try_create` (`full.hpp:833`) into "
              "the adopt-constructor at :1013, and all nine callers of this constructor are in `t/` - as :766 above now says itself.  "
              "s/the scheduler passes/callers pass/ here, and point the \"(see the 4-argument constructor)\" at :984 at the "
              "adopt-constructor, or drop it."),
    "R1-36": ("The comment is gone, good; the four `dotter` constructions at :1519 and the `-inf` fill at :1511 still run on every page "
              "AMX takes, since `did_amx` is only decided at :1574 - shall we hoist the AMX test above them, or construct `dot_q` inside "
              "the `if (!did_amx)` at :1586?"),
    "R1-38": ("Comment is the right length now.  The scale/softcap/max/exp block at :1631-1641 is still a copy of :1675-1685 - shall we "
              "pull the per-head part into one helper both loops call, so they can't drift?"),
    "R2-11": ("s/gated on available()/gated on the eligibility flag (which this test now passes explicitly) and available()/.  And :78 "
              "has the other half: \"Eligible, so the arena is allocated\" is not so on a host without AMX, as the WARN at :95 says.  "
              ":129-130 already says it right; one sentence naming both conditions of `maybe_allocate_mirror_arena` covers both."),
    "R2-13": ("The pair now differs only in the flag.  Can both arms still go through `book_t::try_create`, so the adopt-constructor "
              "(`kv_cache.hpp:1028`, the path `full.hpp:833` ships) is what gets exercised, and can one "
              "`static_assert(amx_mirror_eligible(...))` use a real plugin array instead of the hand-built ones?"),
    "R1-68": ("Still page 1 only: `destination_page` is `page_of(target_token)` with `target_token == page_size` (:485, :510), so the "
              "64-token copy into page 0 - the only `copy_storage_slot` call with `count > 1` that any mirror check reaches - is still "
              "unchecked; can we check that page too?"),
    "R5-04": ("Two corrections to my own reply: since 35b3f3cae the pack writes 1 KB, not 4 KB (`pack_q_group_128x4` fills columns 0..3 "
              "only, `amx_attn.cpp:99-110`; `pack_q_rows_128x4` is one 1 KB `memcpy`, :229; `resize()` at :1371 zeroes the padding once), "
              "and since b2010bee9 a null plane with `amx_on` true no longer means the allocation failed - the 3-argument `book`/`try_create` "
              "forms (`kv_cache.hpp:770`, `:981`) never allocate the arena.  The first makes the eager version cheaper still, so the bitmap "
              "at :1366/:1419/:1434 has even less to defend."),
}
TEXT_EDIT = {}
DROP = {}
SNIP_OVERRIDE = {}
TRIAGE_PREDICTION = {}

FIXED_VOICE = {
    "R1-49": "Good.",
    "R2-09": "Good.",
}

# Hand-written background block carried from round 5 (HTML only), attached to the declined row of R1-47.
RESPONSES = {"R1-47": open(_os.path.join(_R6, "response_R1-47.html")).read()}

CODEX = CARRY.get("R5_CODEX", [])

NEW = [
    # R6-01 - the pack-buffer reuse sentence became false when 35b3f3cae made the zero padding a precondition
    dict(file="h/tron/kernels/amx_attn_iface.hpp", line=161, snip=(156, 162), tag="A3", blocker=False,
         text=("\"so callers can reuse the same buffer\" - not now that the padding is a precondition: a canonical pack writes elements "
               "512..2023 (this layout's rows 4..15) and a rows pack fills panel 0's columns 4..15, so a buffer that has seen one packer "
               "fails the other's \"must already be zero\" without a memset in between.  Rows 0..3 of S still come out right - the dirt "
               "only reaches the discarded rows/columns - so this is the contract contradicting itself (and \"Rows 4..15 receive zeros\" "
               "at :59), not a wrong number.  s/so callers can reuse the same buffer/so one buffer size serves either orientation/."),
         note=("new in round 6 (R6-01); finder 'design' #2, refuter PARTIAL -> confirmed with the consequence corrected (no wrong S rows: the "
               "canonical transpose emits k = 0..3 only, amx_attn.cpp:147/:173; the mirror path copies rows 0..3 only, self_attention.hpp:1571-1572; "
               "t_amx_numerics compares qi < 4). Verified index math: pack_q_group_128x4 writes offsets 0..7 of every 32-element panel row "
               "(amx_attn.cpp:105), 384 of its 512 elements land in rows 4..15 of the row layout; pack_q_rows_128x4 memcpys elements 0..511, "
               "384 of which are panel 0's columns 4..15. Not exercised in-tree: one packer per build under #ifdef TRON_AMX_K_MIRROR "
               "(self_attention.hpp:1420-1433); t_amx_numerics uses separate buffers (:125, :138). The R5 contract said 'rows 4..15 zeroed by "
               "this call', which made the reuse sentence true; 35b3f3cae changed the precondition and kept the sentence.")),
]

# ------------------------------------------------------------------ suggested fixes (added at jhan's request)
_R1_14_TEXT = (
    "// through memory and transpose it - a ~560 ns/page whole-path cost at\n"
    "// width 4 (1250 vs 686 ns per L2-resident page: exec/results/slot1/\n"
    "// fused-sweep-v2.txt in the campaign workspace, 2026-08-18, 6962P core 96,\n"
    "// `taskset -c 96 ./amx_fused_bench 4 200000 amx44 1` / `amxqk` on the\n"
    "// stand-alone benchmark at d176c88b3; ~500 ns once that benchmark's per-page\n"
    "// scalar Q pack is amortized, 512-page ring 1972 vs 1470 - the pack, the\n"
    "// transpose and the score round trip were not isolated). NOT a")

FIX = {
    "R2-03": dict(
        plan=[
            "Keep the 3-argument spelling (every test and the `sequence_cache_behavior` concept use it) but as defaulted trailing parameters of ONE constructor and ONE `try_create`, instead of two delegating overloads: the same calls compile, the default is still the direction that allocates nothing, and there is one signature to read.",
            "The concept (:1356-1358) then needs no change (a 3-argument call still satisfies `constructible_from<T, size_t, size_t, bool>`); moving it to four arguments becomes optional. R2-07's misattributed 'the scheduler passes' sentence disappears with the second comment.",
        ],
        hunks=[
            dict(file="h/tron/models/kv_cache.hpp", lines=(764, 778), what="one constructor; replaces both comments and both signatures (line 779 `: n_pages(n_pages)` follows unchanged)", text=(
                "  // `amx_mirror_eligible` is amx_mirror_eligible(plugin::attention_kernels)\n"
                "  // for the model this book serves (the scheduler computes it; tests pass it\n"
                "  // explicitly): a model without an AMX-eligible attention shape allocates no\n"
                "  // mirror arena. The default is the direction that allocates nothing.\n"
                "  book(size_t n_pages,\n"
                "      size_t storage_slot_count = n_slots,\n"
                "      bool support_eagle = false,\n"
                "      [[maybe_unused]] bool amx_mirror_eligible = false) noexcept")),
            dict(file="h/tron/models/kv_cache.hpp", lines=(976, 991), what="one try_create; replaces the delegating overload, its body and the second comment (the STORY-127 comment above stays; line 992 `auto const sizes =` follows unchanged)", text=(
                "  // `amx_mirror_eligible` as for the constructor; the scheduler's production\n"
                "  // path passes all four arguments (full.hpp).\n"
                "  TRON(nodiscard)\n"
                "  static std::shared_ptr<book> try_create(size_t n_pages,\n"
                "      size_t storage_slot_count = n_slots,\n"
                "      bool support_eagle = false,\n"
                "      bool amx_mirror_eligible = false) noexcept {")),
        ],
        note=("Applied to a scratch copy of the tree at 3fa11d911 and syntax-checked with the build's own compile commands (clang++-19 -fsyntax-only, "
              "both AMX options ON): t/t_amx_arena_leak.cpp, t/t_llama_unit.cpp (all 3- and 4-argument sites) and a TU instantiating "
              "`full_scheduler<model<llama_3p1_8b<tp1>::plugin_model>>` (covers full.hpp:833) - 0 errors each. Not built or run. Diff and logs: "
              "exec/review-pipeline/r6/fix/kv_cache.diff, arena.log, llama.log, tu.log. His stated preference in R2-03 was no default at all; "
              "this variant answers 'two overloads for one purpose' while keeping your decision to leave the 3-argument calls in place.")),
    "R1-14": dict(lines=(139, 141), text=_R1_14_TEXT,
        note=("Same replacement as round 5, re-anchored (+2 lines): names the record, the host, the corrected date (file header "
              "2026-08-18T18:34:53Z; exec/logs/p0-fused-sweep.log lists both sweeps on 08-18), the command ff7269a9f recorded and 901f30d8e "
              "removed, and the pack artifact R5-01 asks about (pages=512 row: 1971.6 vs 1470.2). Line 142 ('store-forwarding stall: 64-byte') "
              "reads on. The '6962P microbench' sentence at :142-144 is unchanged: no record exists to cite.")),
    "R1-15": dict(lines=(152, 154), text=(
        "// canonical-K is the supported default; the mirror is opt-in\n"
        "// (TRON_AMX_K_MIRROR): on an AMX host it costs kv_bytes/2 of ordinary RAM per\n"
        "// book plus the save_k write-through; on any other host nothing is allocated\n"
        "// and the AVX path runs. The mirror formulation is PR #2934's k_vnni."),
        note=("Replaces the consequence clause with the condition the code implements (kv_cache.hpp:1057 gate; model.hpp:2771 write-through "
              "gate). Keeps the #2934 pointer he asked to keep.")),
    "R6-01": dict(lines=(160, 161), text=(
        "// (= Q_PACK_ELEMS_2048, 4 KB; no alignment requirement) - the same size as\n"
        "// the canonical pack, so one buffer size serves either orientation (never\n"
        "// both in turn: each pack's live data lands in the other's padding)."),
        note=("Two lines become three; line 162 (`void pack_q_rows_128x4(...)`) follows unchanged. Also drops '64B-aligned' here, the R1-12 arm taken above. The call-site comment at "
              "self_attention.hpp:1422 '(same 4 KB buffer either way)' already means one allocation per build, which this wording keeps.")),
    "R2-07": dict(lines=(772, 774), text=(
        "  // The constructor that carries the mirror-eligibility decision: callers\n"
        "  // pass amx_mirror_eligible(plugin::attention_kernels) (the scheduler's path\n"
        "  // is try_create into the adopt-constructor below), so a model without an\n"
        "  // AMX-eligible attention shape allocates no mirror arena."),
        note=("Only needed if the R2-03 single-constructor variant is not taken (that variant replaces this comment). The '(see the 4-argument "
              "constructor)' pointer at :984-985 should then point at the adopt-constructor (:1013) or go.")),
    "R2-11": dict(
        plan=["Name both conditions of `maybe_allocate_mirror_arena` once, in each of the two comments that currently name one."],
        hunks=[
            dict(file="t/t_amx_arena_leak.cpp", lines=(77, 79), what="the leak-balance book's comment", text=(
                "    // The small uniform book shape t_llama_unit uses (2 layers, 1 KV head,\n"
                "    // head size 128); 4 pages keeps the arena real but tiny. Eligible (the flag\n"
                "    // below) and, when this host has AMX, allocated: maybe_allocate_mirror_arena\n"
                "    // needs both; the 3-argument form passes false and allocates none.")),
            dict(file="t/t_amx_arena_leak.cpp", lines=(91, 92), what="the assertion's comment", text=(
                "    // The arena allocation actually ran (maybe_allocate_mirror_arena is gated\n"
                "    // on the eligibility flag, passed above, and on available()), so the\n"
                "    // balance above covered it.")),
        ],
        note="Comment-only; line counts change by +1 and +1, so R1-60's `>= 1` moves to :95 if both are applied."),
}

# ---- suggested fixes for the items named in the verdict's "what still blocks" list (jhan request 2026-08-26)
FIX["R1-10"] = dict(lines=(55, 59), text=(
    "// TILESTORED always writes ALL 16 configured tile rows, no matter how many\n"
    "// carry real data: a width-4 result still stores 16 rows. The two kernels\n"
    "// that store a tile straight into the caller's buffer - weights_times_v_128x4\n"
    "// (`o`) and qk_mirror_128x4 (`s`) - therefore need 16-row buffers; a\n"
    "// \"4 x N\" buffer is a silent overrun (rows 4..15 land past its end).\n"
    "// Rows 4..15 of those buffers receive zeros (the A-operand rows 4..15 are\n"
    "// zero padding); only rows 0..3 are the result. qk_canonical_128x4 stores\n"
    "// its tiles into a kernel-local buffer, transposes, and writes exactly 4 rows\n"
    "// x 64 columns into `s`, so `s` needs only 4 rows (s[4][s_stride_floats])."),
    note=("Fact-checked against 3fa11d911 (CONFIRMED with two wording corrections, applied): the only _tile_stored targets in a caller's buffer "
          "are weights_times_v_128x4's `o` (amx_attn.cpp:220-223) and qk_mirror_128x4's `s` (:255-258); qk_canonical_128x4 stores into its "
          "local s_transposed (:142-145) and its transpose writes rows k = 0..3 (:173-177) - the header's own contract at :114 says "
          "'writes s[4][s_stride_floats]'; t_amx_numerics hands it s_amx[NQ][PAGE] with NQ = 4 (:87). Rows 4..15 of `o` / mirror `s` are zero "
          "because the A-operand rows 4..15 (P rows :187-190, Qpad rows) are zero padding. 'stack overrun' -> 'overrun': the production "
          "mirror scratch qk_s is thread_local (self_attention.hpp:1567-1568), not stack. Five lines become nine; line 60 follows unchanged. "
          "Residual the checker noted, outside this range: :66-69 still says 'output buffers are sized with TILE_ROWS_16' for every kernel - "
          "add 'the two kernels that store into a caller buffer' there too if you take this fix."))
FIX["R3-02"] = dict(lines=(72, 75), text=(
    "// The one attention shape these kernels serve - the tile identity of\n"
    "// Note [AMX attention dispatch]: a 64-token KV page, 128-dim heads, and 4\n"
    "// query heads per KV head (4 x 128 bf16 = one full tile operand). shape_ok\n"
    "// and the kernel buffer sizes are written in terms of these three."),
    note=("Exactly the s/// he offered in R3-02. My first draft added a clause calling the remaining amx_attn.cpp literals 'AMX tile geometry, "
          "not model shape'; the fact-checker refuted it: `step * 4` (:246-252) is PAGE/16 token blocks per dim step, `r < 4` (:150) is "
          "PAGE/TILE_ROWS, `k < 4` (:173) is GROUP_HEADS, `half < 2` (:200) is HEAD_SIZE/64, `s < 2` (:205) is PAGE/DIM_STEP, `half * 64` "
          "(:220-223) is HEAD_SIZE/2 - all model-derived; DIM_STEP, PANEL_ELEMS, the pack-index 16s and the 16-float store offsets are tile "
          "geometry; the transpose/convert 4s, 32s and 0x88 are AVX-512 widths. So the honest sentence stops after 'these three'. Checked: "
          "shape_ok (:91-92) uses HEAD_SIZE_128 / GROUP_HEADS_4; Q_PACK_ELEMS_2048 (:83), s_transposed[PAGE * TILE_ROWS] (amx_attn.cpp:122), "
          "P[TILE_ROWS][PAGE] (:189) and the 1 KB memcpy (:229) use the named constants."))
FIX["R2-06"] = dict(lines=(88, 90), text=(
    "// Note [AMX attention dispatch]). Evaluated by the dispatch, the save_k\n"
    "// write-through and, through amx_mirror_eligible, the scheduler's\n"
    "// mirror-arena decision; the page-move and fill_random rebuilds do not test\n"
    "// it - they rebuild whatever plane exists. So for a book the scheduler\n"
    "// creates, the reader and the writers agree on which models take the AMX\n"
    "// path; a book built by hand with amx_mirror_eligible=true gets planes for\n"
    "// every slot on an AMX host, whether or not its geometry passes this gate."),
    note=("Fact-checked (CONFIRMED with three calibration corrections, applied): shape_ok is evaluated by the dispatch (self_attention.hpp:1358-1359, "
          ":1499-1500), the save_k write-through (model.hpp:2769-2770) and amx_mirror_eligible() at the scheduler's call site (full.hpp:1457; "
          "kv_cache.hpp:184-186) - the book's allocator itself (kv_cache.hpp:1052-1057) only consumes the bool, hence 'through amx_mirror_eligible'; "
          "copy_storage_slot (:1885-1886) and fill_storage_slot (:1314) null-check mirror_at_storage only; the arena also needs "
          "amx_attn::available() (:1057), hence 'on an AMX host'; a hand-built head-64 book with the flag true gets one arena sized kv_bytes/2 "
          "covering every storage slot (t_amx_arena_leak.cpp:134-136; kv_cache.hpp:1058-1061). Line 87 ends with '(the tile identity, see', "
          "so the first line reads on; :91 `constexpr bool shape_ok(` follows. Three lines become seven, max 76 columns."))
FIX["R1-12"] = dict(
    plan=["Take the zero-cost arm of his 'Fix one': drop the alignment claim from the two Q-pack contracts (:102 here; :160 goes with the R6-01 "
          "replacement below), since nothing in the tree provides 64-byte storage and TILELOADD does not require it. Codex's point that a "
          "16 mod 64 base makes every 64-byte tile row straddle two cache lines stays a performance question, not a correctness one.",
          "If that cost is to be settled rather than accepted: time one dense page with the pack at 0 vs 16 mod 64 (his R5-03 sentence). If it "
          "matters, the storage his R1-31 points at - `attn_accum`, per attention worker, per token, already 64B-aligned, allocated in `state` "
          "for the loaded model only - is the place; that change is not drafted here.",
          "NOT suggested: a fixed `alignas(64) thread_local` array sized by `max_minibatch_size` (my first draft, syntax-checked clean). The "
          "fact-checker measured why: a function-local thread_local in apply_page_range is one static-TLS block per model instantiation, and "
          "glibc allocates and zero-fills the whole static TLS image for every thread at creation; ingest-generated plugins hard-code "
          "max_minibatch_size = 1024 (ingest/src/TronCpp.hs:264), so each eligible ingested model costs 4 MB per thread and llama.hpp's 128 costs "
          "512 KB - est. ~52 MB per thread for a production build, on every thread, for models never loaded. The rejected diff is kept at "
          "exec/review-pipeline/r6/fix/self_attention.REJECTED-thread_local-tls.diff."],
    hunks=[dict(file="h/tron/kernels/amx_attn_iface.hpp", lines=(102, 102), what="the canonical pack contract; :103-104 read on", text=(
        "// `packed` must hold Q_PACK_ELEMS_2048 bf16 (4 KB; no alignment requirement), with"))],
    note=("The :160 line ('(= Q_PACK_ELEMS_2048, 4 KB, 64B-aligned) - same size as the canonical pack,') is rewritten by the R6-01 fix, which "
          "drops '64B-aligned' as well, so the two contracts stay consistent. Verified: the only Q-pack storage is `thread_local std::vector<uint16_t> "
          "amx_qpack` (self_attention.hpp:1361), whose data() is 16 mod 64 in nearly every allocation on glibc (measured in round 5); the other two "
          "64B contracts (`o` :123-125, `s` :166-168) are honored by alignas(64) storage at self_attention.hpp:1567-1568 and :1646 and stay as they are. "
          "Line 102 is the only edit here; it stays under 88 columns."))

# Plain-language unpacking of a comment, added at jhan's request (2026-08-27); rendered after the fix block.
EXPLAIN["R1-10"] = dict(title="the Note, sentence by sentence", md=open(_os.path.join(_R6, "explain_R1-10.md")).read())

METHOD = [
    "Target: PR head <code>3fa11d911</code> (checked out clean in <code>~/workspace/tron-amx</code>, verified by the generator). Round 5 reviewed <code>234c02bde</code>. Delta: six commits - b2010bee9, b85fd2789, 298dbad0f (yours from the round-5 follow-up) and 275fa89a0, 35b3f3cae, 3fa11d911 - 9 files, +70/&minus;66.",
    "The author's decision record <code>PR3879/triage.json</code> (31 decisions) was handed to every status verifier: <code>done</code>/<code>partial</code> claims were checked against the tree (one 'done' did not hold: R1-14), <code>ignore</code>/<code>defer</code> items (R1-47, R1-58) were not re-raised and carry his predicted reply instead (section 2a), the <code>question</code> item (R2-05) stays open with the tree's answer in its verification line.",
    "66 items sit in files the delta touched; 8 status verifiers re-anchored them by content and 8 adversarial refuters re-derived every line and quote (13 line/wording corrections applied, no status overturned). The 7 items in unchanged files carry their round-5 lines and text.",
    "Finders: 4 independent agents over the delta only (code correctness of the padding invariant, the kill-switch parse and the default flip; comment/contract accuracy; tests, CI and PR description; design and scope). 8 candidates, one adversarial refuter each: 5 stand (one new comment, four folded into existing threads as follow-ups), 3 refuted as restatements of open items. The padding invariant of 35b3f3cae was checked to the index formula: the live writes never touch the padding, the thread_local vector is written by nothing else, and shrink-then-grow value-initializes the tail.",
    "Suggested fixes (added at your request): the R2-03 single-constructor variant was applied to a scratch copy of 3fa11d911 and syntax-checked with the build's compile commands (0 errors on both tests and the scheduler TU; <code>exec/review-pipeline/r6/fix/</code>); the comment replacements were not compiled.",
    "CI: <code>gh api commits/&lt;sha&gt;/check-runs</code> returns 0 for 3fa11d911, 35b3f3cae, 275fa89a0 and 298dbad0f; the PR is a draft without the <code>Run CI</code> label, so the earlier lint-only runs are still all CI has done. The two Codex threads still have no reply (they are answered by R5-03/R5-04 here).",
    "Written 2026-08-26. Voice from <code>~/workspace/reviewers/alexey.md</code>; the persona's most common review is an empty approval, so nothing was added that his lenses would not raise. The hand-written background block for R1-47 from round 5 is carried under its row in section 2a. Format note: the verdict body is broken into paragraphs and a list with comment ids at your request; he writes review bodies as one prose paragraph (bullet lists in 5 of 365 bodies).",
]

CLEAN = [
    ("35b3f3cae: the padding invariant", "pack_q_group_128x4 writes offsets 0..7 of every 32-element panel row (amx_attn.cpp:105; 512 writes, all live); pack_q_rows_128x4 is one 1 KB memcpy of rows 0..3 (:229); grep amx_qpack: declared :1361, resized :1371, sliced :1416 - nothing else writes it; std::vector::resize value-initializes appended elements, shrink leaves the prefix, reallocation copies then value-initializes; one packer per build (#ifdef TRON_AMX_K_MIRROR at :1420), same 4x128 shape for every instantiation (shape_ok), so no stale-live-becomes-padding path; test buffers `= {}` at t_amx_numerics.cpp:85, :125, :138 (per-seed loop); P buffer precedent `alignas(64) thread_local uint16_t P[TILE_ROWS][PAGE] = {}` (amx_attn.cpp:186-197)", "src/tron/kernels/amx_attn.cpp:98-110,186-197,227-230; h/tron/models/self_attention.hpp:1361-1442; t/t_amx_numerics.cpp:85,125,138"),
    ("3fa11d911: TRON_AMX_DISABLE exactly \"1\"", "amx_attn.cpp:57-58 `off != nullptr && std::strcmp(off, \"1\") == 0` is the TRON_NO_RTM form (mwaitx.cpp:37-38) and the TRON_USE_ARENA_ALLOCATOR form (memory.cpp:90); every statement of the switch agrees (iface:32, :96; t_amx_logit_ab.cpp:6-7; PR body); values other than 1 are ignored without a log line - the B17 half R1-48 mentioned, not asked", "src/tron/kernels/amx_attn.cpp:54-58; src/system/mwaitx.cpp:34-39; src/system/memory.cpp:87-91"),
    ("b2010bee9: default false is safe for production and for every mirror test", "the scheduler reaches the book only through the 4-argument try_create (full.hpp:833-834) with amx_mirror_eligible(model_t::plugin_t::attention_kernels) from :1457; every k_mirror_data / set_k_mirror use in t/ belongs to a test whose book passes true (t_llama_unit.cpp 272-273, 339-340, 478-481, 1080-1083; t_amx_arena_leak.cpp 80-81, 134-135); the remaining 3-argument callers read canonical K or count DMA allocations only (the arena is ::operator new[], not DMA); node_base has one constructor and both node constructors forward the flag", "h/tron/scheduler/full.hpp:306-322,709-727,833-834,1457; t/t_llama_unit.cpp; t/t_amx_arena_leak.cpp; h/tron/models/kv_cache.hpp:1062-1063"),
    ("b2010bee9: the t_amx_arena_leak literal storage_slot_count=2 equals the old default", "book<2, 1, 128, 0>'s default layout is uniform_kv_slot_specs<2> -> n_slots = 2 (kv_cache.hpp:696-725)", "h/tron/models/kv_cache.hpp:696-725; t/t_amx_arena_leak.cpp:80-81,134-135"),
    ("35b3f3cae: cvtne2ps_pbh argument order (R1-50)", "_mm512_cvtne2ps_pbh(a, b): words 0..15 from b, 16..31 from a - so (hi, lo) keeps tokens c..c+31 in order; a finder compiled and ran the intrinsic on this host (avx512_bf16) and saw exactly that", "src/tron/kernels/amx_attn.cpp:191-196"),
    ("275fa89a0: the trims match the threads they answer", "`>> 6 / & 63` re-explanation gone (R1-33), static_assert prose gone (R1-45), 'share the bf16 -> fp32 conversion' gone (R1-36 first half), softmax-update paragraph reduced to one sentence (R1-38 first half), <atomic> removed and unused (R1-43), the system-level byte-identical check sentence gone (R1-67); Note [AMX attention dispatch] still names t_amx_numerics (iface:46-47)", "h/tron/models/self_attention.hpp:1417-1418,1509-1512,1621-1623; src/tron/kernels/amx_attn.cpp:1-12,31-33; t/t_amx_numerics.cpp:145-151"),
    ("298dbad0f: TODO form (B10)", "TODO(owner) with a filed-issue URL at the two options a reader flips; issue #3997 is OPEN, assigned to jhan-positron, and carries the interim recipe the TODO points to", "src/tron/CMakeLists.txt:170-173; gh issue view 3997"),
    ("Delta scope (A9) and commit messages", "all nine files are the PR's AMX files; every hunk is named in a commit message; b2010bee9's '8 mirror-test sites' = 6 in t_llama_unit + 2 in t_amx_arena_leak (:126 already passed false); 35b3f3cae's description of the thread_local vector and the `= {}` buffers matches the code", "delta.diff; git show b2010bee9 35b3f3cae 3fa11d911"),
    ("PR body mechanism sentences", "'save_k writes through' (model.hpp:2793-2795), 'every consumer null-checks and fails soft to the AVX path' (self_attention.hpp:1565-1575, kv_cache.hpp:1237), 'Validation and CI coverage' facts (options OFF at src/tron/CMakeLists.txt:174/:181; no TRON_AMX in .github, ci/, CMakePresets.json, flake.nix; the three tests SUCCEED in the default build), the archive link and #3997 all hold; still undescribed: kv_block_planes, v_data/v_base, the two #error lines, the fill_random rebuild, the amx_mirror_eligible plumbing (grep -c = 0 each)", "pr_body.md; h/tron/models/model.hpp:2769-2795; h/tron/models/self_attention.hpp:1556-1590; src/tron/CMakeLists.txt:170-190"),
    ("CI and the Codex threads", "isDraft=true, labels=[], reviewDecision=REVIEW_REQUIRED; check-runs: 3fa11d911 0, 35b3f3cae 0, 275fa89a0 0, 298dbad0f 0; exactly two Codex comments (3858305362 at :1367, 3858305367 at :1361), no replies, one COMMENTED review", "gh pr view 3879; gh api commits/<sha>/check-runs; gh api pulls/3879/comments"),
    ("Re-anchoring", "kv_cache.hpp 2471 -> 2473 lines (hunks 764-772, 980-986: +1 after :772, +2 after :986); self_attention.hpp +3 at :1368, -3 at :1414-1418, -1 at :1510, -5 at :1618-1623; amx_attn.cpp -7/-8 from the header and static_assert trims, +2 at the cvtne2ps comment; amx_attn_iface.hpp +2 after :96 and +3 after :156; src/tron/CMakeLists.txt +4 from :170; t_amx_arena_leak.cpp +2 after :78; t_llama_unit.cpp +1/+2/+4/+6 from the four wrapped constructors; every anchor confirmed by a content quote", "diff wt-r5 wt-head per file"),
    ("Triage claims that hold", "R1-16, R1-33, R1-45, R1-15 (applied - but see R1-15's new problem), R1-67, R1-43, R1-49, R1-50, R2-03 (as stated), R1-48 done; R1-36, R1-38 partial as stated; R1-47's reason (no helper for the XGETBV and arch_prctl steps; mwaitx.hpp has only cpuid_bit) and R1-58's reason (TODO at the options, #3997 OPEN, PR body section) are factually right", "PR3879/triage.json vs the tree; h/system/mwaitx.hpp:22-44; gh issue view 3997"),
    ("Triage claim that does not hold", "R1-14 'done' (ff7269a9f, 901f30d8e): those commits predate round 5; :137-145 are untouched since; the date 2026-08-19 at :140 contradicts the sweep header 2026-08-18T18:34:53Z and exec/logs/p0-fused-sweep.log (both sweeps on 08-18); no record or command is named - status PARTIAL", "h/tron/kernels/amx_attn_iface.hpp:137-145; exec/results/slot1/fused-sweep-v2.txt:1; exec/logs/p0-fused-sweep.log"),
    ("R2-05 (question): what the tree says", "both in-tree plugins declare a single-kernel attention_kernels array (llama.hpp:191-193, mock.hpp:113-115), so 'no in-tree plugin is mixed today' holds; copy_storage_slot's rebuild has no shape gate (kv_cache.hpp:1881-1889); Option 1 in your kv_cache-hpp-1199.html 4.1 (comment the consequence, add the Note sentence, a two-kernel static_assert) is what the comment asks for and is not applied", "h/tron/plugins/llama.hpp:191-193; h/tron/plugins/mock.hpp:113-115; h/tron/models/kv_cache.hpp:176-190,554,1881-1889"),
]
