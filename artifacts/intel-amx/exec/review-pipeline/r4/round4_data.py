# Round-4 data for gen_review4.py. Filled from the workflow (wf_06ebd45f-af6) + orchestrator reading.
import json as _json, os as _os
_SP = "/tmp/claude-0/-home-jhan-workspace-intel-AMX/5827c364-b93e-4e5c-aa49-89cb6addf5a4/scratchpad/pr3879/r4"
_g = {}
exec(open(_os.path.join(_SP, "round3_data.py")).read(), _g)   # reuse round-3 EAGLE section + glossary-safe bits
EAGLE_HTML = _g["EAGLE_HTML"].replace("_Added on request (2026-08-25). Not part of his review; background for the EAGLE items in sections 2 and 3, written from the tree at `96b5a6c72`._",
                                      "_Added on request in round 3 (2026-08-25) and carried unchanged; background for the EAGLE items, written from the tree at `96b5a6c72` (the fix landed in that commit)._")
EAGLE_MD = _g["EAGLE_MD"].replace("_Added on request (2026-08-25). Not part of his review; background for the EAGLE items in sections 2 and 3, written from the tree at `96b5a6c72`._",
                                  "_Added on request in round 3 (2026-08-25) and carried unchanged; background for the EAGLE items, written from the tree at `96b5a6c72` (the fix landed in that commit)._")

VERDICT = "CHANGES_REQUESTED"
BODY = (
    "The doc caught up: the region frequency, the SMT condition, the arena condition and the gate paragraph now say what the code does, "
    "and `t_amx_logit_ab` is `DISABLED` and inside `BUILD_INGEST_MODELS` - fine.  Two doc things I'd still change: the measured-numbers "
    "paragraph now says \"please check the related PR for latest\" - a doc in the tree outlives the PR, so either keep one table here with "
    "its rep count and where it came from, or write `PR #3879` and drop the gpt-oss cells too; and the model list is consistent with itself "
    "now, but phi-4 (40/10/128) and granite-3.3-8b (32/8/128) pass the gate and aren't on it, so it is already stale - record the rule that "
    "produced it.  What still blocks from my side: the 3-argument `book`/`try_create` that default `amx_mirror_eligible` to allocate, "
    "`amx_fused_bench.cpp` as a second copy of every kernel in `src/`, and a compile-only configuration so the flagged code can't rot after "
    "merge.  The description still says nothing about the doc, the `kv_block_planes` refactor, `v_data`/`v_base`, the two `#error`s, the "
    "`fill_random` rebuild, or the scheduler plumbing, and the `Run CI` run is still outstanding.  The rest is carried over unchanged below."
)
TAKE = ("Round 4 in one line: __F__ comments resolved by the delta (section 2) - five doc items and the <code>fpga</code>-labelled dump tool; __O__ still open "
        "(two of them, the numbers paragraph and the model list, with a follow-up on your rewrite); __N__ new on the delta (the A/B recipe's missing configure step). Three blockers remain: "
        "the default-true 3-argument constructor (<code>kv_cache.hpp</code>), the kernel copies in <code>amx_fused_bench.cpp</code>, and the missing "
        "compile-only configuration for the AMX tests (<code>t/CMakeLists.txt</code>).")

FOLLOWUP = {
    "R1-04": ("Which PR?  The section header says #3879; say it here too, and drop \"latest\" - a description is frozen the day this merges.  "
              "\"Could fluctuate a little\" isn't checkable either (the two campaigns differ by at most 0.3 points; say that or nothing), and half a "
              "table is the worst of both: keep one table with its rep counts, or point at the PR and drop the gpt-oss cell with the rest."),
    "R2-01": ("The count is gone, but the other half stands: `phi_4` (`llama.hpp:1549`, 40Q/10KV/128) and granite-3.3-8b "
              "(`ingest/traces/granite-3.3-8b-instruct/metadata.json`, 32/8/128) pass `shape_ok` too - dropped on purpose?  And let's say how the "
              "list was made (`shape_ok` over the `TRON_LLAMA_CONFIG` rows and the ingested configs, as of a date), or the next added row makes "
              "this sentence stale.  Not blocking now that it is no longer self-contradictory."),
}
DROP = {}
SNIP_OVERRIDE = {}
TRIAGE = {}
TRIAGE_PREDICTION = {}
FIXED_VOICE = {
    "R1-03": "OK.  FWIW the three cells give 3.67 ms + 0.70 us by least squares (61%); the 3.43/0.734 line is the 2K-8K pair.  Same conclusion either way.",
    "R1-07": "Now that :172-177 lists the sites, the parenthetical at :194-196 says it again - flush one.",
}
NEW = [
    dict(file="t/t_amx_logit_ab.cpp", line=6, snip=(1, 12), tag="B17/A3", blocker=False,
         text=("Both commands run the AVX path on a default build - `TRON_AMX_DISPATCH` is OFF (`src/tron/CMakeLists.txt:170`) and the dispatch "
               "site is `#ifdef`'d (`self_attention.hpp:1352`) - so the two dumps agree for the wrong reason.  Let's start the recipe with the "
               "`-DTRON_AMX_DISPATCH=ON` configure (and `-DTRON_AMX_K_MIRROR=ON` for the mirror arm)."),
         note="new in round 4 (R4-01); from the delta (d176c88b3 rewrote this header). Verified: option default OFF at src/tron/CMakeLists.txt:170; call site #ifdef TRON_AMX_DISPATCH at self_attention.hpp:1352; the header says nothing about the configure."),
]
FIX = {
    "R1-04": dict(lines=(124, 128), text=(
        "Primary: `ingested-qwen-3-4b-instruct-2507-tp2`. All comparisons are\n"
        "same-binary kill-switch A/Bs against the true clean binary. The measured\n"
        "numbers (qwen decode/prefill/energy, and the llama-3.1-8b, mixtral-8x7b and\n"
        "gpt-oss generalization runs, gpt-oss being the ineligible-geometry control)\n"
        "are in the PR #3879 description; the replicated 8-rep campaign and the\n"
        "earlier 3-rep suite differ by up to 0.3 points, and this file does not repeat\n"
        "either table."),
        note=("Pointer form, matching your decision to delete the table: names the PR (the section header at :99 already does), replaces "
              "'could fluctuate a little' with the measured spread (max 0.3 points: 28.1 vs 27.8), and drops the lone gpt-oss cell so the doc is "
              "not half a table. If you keep that cell instead, cite its source: -0.3..-1.6% is the min..max over the four decode+prefill "
              "cells of exec/results/t4/t4-shapes.txt (2 reps; decode -0.4% 1u/8K, -0.3% 8u/2K; prefill -0.5%, -1.6%). Alternative he offered "
              "in round 3: keep one table with rep counts and align the generalization cells with the PR (+14.9%, +18.5%). Either way remove "
              "the trailing space on :126 - CI's whitespace check fails on it at commit time.")),
    "R2-01": dict(lines=(190, 192), text=(
        "Eight registry families match the gate: six with hand-written C++ geometry in\n"
        "`h/tron/plugins/llama.hpp` (llama-3-8b, llama-3.1-8b, mistral-7b, ministral-8b,\n"
        "mixtral-8x7b, phi-4 - 40Q/10KV, the ratio is what the gate reads) and two\n"
        "ingested families (qwen-3-4b-2507; granite-3.3-8b, not yet promoted to working\n"
        "per `config/models.yaml`). The list is `amx_attn::shape_ok(head_size,\n"
        "n_heads / n_kv_heads)` applied to the `TRON_LLAMA_CONFIG` rows and to the\n"
        "ingested traces' `metadata.json`, as of 2026-08-25; re-derive it when the\n"
        "registry changes. Three are measured (qwen, llama-3.1-8b, mixtral). Every\n"
        "other family runs the unchanged AVX path. In"),
        note=("Same content as the round-3 suggestion, re-verified against the working tree: llama.hpp rows with head_size 128 and "
              "n_heads/n_kv_heads == 4 are exactly llama_3_8b, llama_3p1_8b, mistral_7b, mixtral_8x7b, ministral_8b, phi_4 (six); ingested traces "
              "with 128/ratio-4: granite-3.3-8b-instruct and qwen3-4b-instruct-2507. If phi-4 or granite are excluded on purpose, say so in the "
              "sentence instead of omitting them. The replacement ends with 'In' so :193 still reads.")),
    "R4-01": dict(lines=(5, 7), text=(
        "// Run the binary by hand, twice, from a build configured with\n"
        "// -DTRON_AMX_DISPATCH=ON (and -DTRON_AMX_K_MIRROR=ON for the mirror arm; both\n"
        "// default OFF), and compare the two dumps offline:\n"
        "//   AMX_LOGIT_OUT=/tmp/avx.bin TRON_AMX_DISABLE=1 gen/t_amx_logit_ab\n"
        "//   AMX_LOGIT_OUT=/tmp/amx.bin TRON_AMX_DISABLE=0 gen/t_amx_logit_ab"),
        note="Replaces lines 5-7 of the header; nothing else in the file changes."),
}

METHOD = [
    "Target: the working tree of <code>~/workspace/tron-amx</code> = head <code>d176c88b3</code> plus the uncommitted <code>doc/intel-amx.md</code> (your edit in response to round 3). Delta since round 3's head <code>96b5a6c72</code>: <code>t/CMakeLists.txt</code>, <code>t/t_amx_logit_ab.cpp</code> (commit d176c88b3) and <code>doc/intel-amx.md</code> (+30/&minus;22, uncommitted).",
    "Only comments anchored in those three files can change status; the other __O__ open comments are carried over with their round-3 text and lines (files identical to <code>96b5a6c72</code>).",
    "Verification: 3 status agents over the nine changed-file items (each item: status, working-tree anchor, evidence quotes, and whether the applied text matches the round-3 suggested fix), 1 independent finder over the whole delta through his lenses, and one adversarial refuter per agent (8 agents). Disagreements are shown, not averaged.",
    "Numbers the doc cites were checked where a source exists: the attention-share fit (3.43 ms + 0.734 us x ctx) against <code>exec/results/slot1/qwen-baseline-swattn.txt</code>; the model list against <code>TRON_LLAMA_CONFIG</code> rows and the granite ingest metadata. The tron tree itself carries no result files, which is why the pointer question keeps coming back.",
    "Written 2026-08-25. Voice from <code>~/workspace/reviewers/alexey.md</code>; the persona's most common review is an empty approval, so nothing was added that his lenses would not raise.",
]
CLEAN = [
    ("doc:38-41 region frequency", "begin_region/end_region appear once each, inside apply_page_range (:1369/:1468); apply_page_range is called per kv_section from run_sections (:1043), which runs for the ready and the pending plan (:865/:876) - the doc's definition is exact; the 229-cycle pair matches exec/results/amx-overhead-20260821.txt (229.14/228.69 cycles/op)", "self_attention.hpp; exec/results"),
    ("doc:92-95 SMT sentence", "app_pin_thread picks from app_cpu_set (system.cpp:558); find_peers builds the SMT peer set for logging only, no exclusion - 'tron does not check that' is accurate", "src/system/system.cpp:409-425, :558"),
    ("doc:104-108 attention-share fit", "constants = the line through the ctx 2K and 8K cells of qwen-baseline-swattn.txt (3.423 ms + 0.7337 us; 63.7%); least squares over all three cells gives 3.67 ms + 0.70 us (60.9%) - same conclusion", "exec/results/slot1/qwen-baseline-swattn.txt"),
    ("doc:148-151 arena condition", "matches maybe_allocate_mirror_arena (`if (!amx_mirror_eligible || !amx_attn::available()) return;`) and amx_mirror_eligible over the plugin's attention kernels", "kv_cache.hpp:182-190, :1055; full.hpp:1456"),
    ("doc:172-183 gate paragraph + code block", "shape_ok defined once (amx_attn_iface.hpp:91); evaluated at self_attention.hpp:1358 and :1499 (both fast-path blocks), model.hpp:2769 (write-through), and via amx_mirror_eligible; the code block equals self_attention.hpp:1358-1360", "amx_attn_iface.hpp; self_attention.hpp; model.hpp"),
    ("t/CMakeLists.txt:189-196 DISABLED entry", "same form as t_clearhbm (:147); one ctest entry per executable via add_test + set_tests_properties; bin/slice drops DISABLED entries (bin/slice:875-878); `make test` and the FPGA lane run through bin/slice (GNUmakefile:684-685; cmake-single-platform.yml:581); the portable CI manifest also drops DISABLED (bin/ci/ci-create-portable-test-manifest.py:55-60)", "t/CMakeLists.txt; bin/slice; .github"),
    ("t_amx_logit_ab.cpp header (except the configure step, R4-01)", "TRON_AMX_DISABLE=1/=0 matches available() (amx_attn.cpp:66-67); gen/ is the build dir; 'binary exists only with BUILD_INGEST_MODELS=ON' true after the move; the --save-tokens format matches ingest/export/reference_logits.py:54-58", "t/t_amx_logit_ab.cpp; src/tron/kernels/amx_attn.cpp"),
    ("doc formatting", "no line over 80 columns; the only `git diff --check` hit is the trailing space at :126 (folded into R1-04)", "git diff --check"),
    ("PR description vs delta", "the t_amx_logit_ab change is described (Tests bullet); the doc is still not mentioned anywhere in the body - carried item, not new", "gh pr view 3879"),
]
