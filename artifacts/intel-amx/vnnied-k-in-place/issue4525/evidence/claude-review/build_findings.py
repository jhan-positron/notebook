#!/usr/bin/env python3
"""Build findings.json for gen_review.py from the workflow result + static prose.

Usage: python3 build_findings.py <workflow-result.json>
The workflow result is the object returned by the review workflow (keys: raw,
lens_verdicts, confirmed, rejected, critic_overall, critic_strengths, ...).
Static prose lives here so the page can be regenerated from data alone.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
result = json.loads(Path(sys.argv[1]).read_text())
overrides = json.loads((HERE / "overrides.json").read_text()) if (HERE / "overrides.json").exists() else {}

confirmed = result["confirmed"]
rejected = result.get("rejected", [])
# Lead edits: drop, re-grade, or amend confirmed findings after reading the votes.
drop = set(overrides.get("drop", []))
regrade = overrides.get("regrade", {})
amend = overrides.get("amend", {})
out_conf = []
for f in confirmed:
    if f["id"] in drop:
        continue
    f = dict(f)
    if f["id"] in regrade:
        f["severity"] = regrade[f["id"]]
    for k, v in amend.get(f["id"], {}).items():
        f[k] = v
    out_conf.append(f)

counts = {s: sum(1 for f in out_conf if f["severity"] == s) for s in ("blocker", "major", "minor", "note")}

data = {
    "title": "Typed Cache Tensors Design Review",
    "eyebrow": "Review of the codex design for issue #4525 (positron-ai/tron)",
    "h1": "Does the codex design for typed KV-cache tensors hold up?",
    "meta": overrides.get("meta", "Reviewed 2026-09-22 UTC by Claude (Fable 5.1) for jhan. Design reviewed: [status/design-new-tensor-type.html](design-new-tensor-type.html) (67,216 bytes, finalized 2026-09-22 00:22 UTC). Sources pinned to main f46e48ba (the design's snapshot), main 98bb8cb2 (the live tip when the design was written) and PR 4424 head 30c4ac82cb. Main moved to 2880c3aa9b at 01:14 UTC on 2026-09-22, during this review; none of the design's step-list source files changed in those five commits."),
    "short_version": overrides.get("short_version", [
        "Issue #4525 captures what jhan and Ben asked for. Three sentences are missing from its body: the problem, the two layout terms, and the direction of dependence on PR #4424.",
        "jhan's reading of Ben's reservation is right. The address formula belongs in the view, and storage stays a separate owner.",
        "The design is sound on layouts, ownership, and kernel typing, but it must change before an agent implements it: it never says which V write the model's save path uses, it labels the live main tip as stale, and it adds slices and iterators no caller needs.",
    ]),
    "tiles": overrides.get("tiles", [
        {"k": "Issue #4525", "v": "Captures the request", "badge": ["ok", "yes"], "s": "3 wording gaps; see section 2"},
        {"k": "jhan's reading of Ben", "v": "Right", "badge": ["ok", "confirmed"], "s": "with two precisions; see section 3"},
        {"k": "Design verdict", "v": "Accept with changes", "badge": ["warn", "not yet implementable"], "s": "%d blocker, %d major, %d minor, %d notes" % (counts["blocker"], counts["major"], counts["minor"], counts["note"])},
    ]),
    "words": [
        ["tron", "the inference program under test; its source is the positron-ai/tron repository"],
        ["PR 4424", "the open draft pull request \"VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save\" (branch jhan-amx-vnniK, head 30c4ac82cb)"],
        ["Ben", "the tron maintainer who reviewed PR 4424 on 2026-09-21 (three comments: a worker-index question, a review asking for typed tensors, and an API sketch)"],
        ["codex, the design", "codex is the agent jhan asked to answer Ben; the design is the page it wrote, status/design-new-tensor-type.html"],
        ["issue #4525", "the GitHub issue codex created for the new work; jhan edited its title and first sentence on 2026-09-22 00:10 UTC"],
        ["KV cache, K, V", "the saved key (K) and value (V) vectors of earlier tokens; attention reads them"],
        ["page, slot, head, D", "a page holds 64 token positions; a slot is the cache region of one layer (or of several layers that share it); a head is one attention head; D is the head size, the number of values per token per head (128 for PR 4424's models)"],
        ["bf16", "the 16-bit brain floating-point format used for cached K and V"],
        ["AMX, AVX-512, 8-lane build", "AMX and AVX-512 are CPU instruction sets. tron's vector width TRON_CHUNK_SIZE is 16 with AVX-512 and 8 without; the 8-lane build stores V row-major, so it has no pair-interleaved V"],
        ["VNNI layout", "a storage order the AMX tile multiply reads directly as its second operand. The design calls it \"packed\""],
        ["pair-interleaved V (the design's \"packed V\")", "today's V storage in the 16-lane build: for each dimension, tokens 2p and 2p+1 sit next to each other. Element offset = (token/2)*(2*D) + 2*dim + token%2"],
        ["blocked VNNI K (the design's \"blocked packed K\")", "PR 4424's K storage for 128-dimension heads: two consecutive dimensions of one token share a 4-byte unit, and 16 tokens share one 64-byte line"],
        ["native K", "today's K storage: one token's D values consecutive in memory (row-major)"],
        ["expr, view, const_view, tensor", "tron's expression interface (h/tron/kernels/expr.hpp), its typed pointer views over regularly laid-out memory and their read-only form (h/tron/tensor/view.hpp), and its owning arrays (h/tron/tensor/tensor.hpp)"],
        ["kv_block", "the struct that holds K then V for one head of one slot in one page (h/tron/models/kv_cache.hpp)"],
        ["set_v, get_v, append_v, scaled_v, v_data", "today's V functions in kv_cache.hpp: write one token, read one token, copy one token between pages, compute the weighted V sum, and return the raw pointer of a V plane"],
        ["save_v_impl, save_k_impl", "the model functions (h/tron/models/model.hpp) that store one token's V and K into the cache during a forward pass"],
        ["Zero-Initialized V Slots invariant", "the rule in kv_cache.hpp that every even-token V write zeroes its odd partner row. The weighted sum reads a whole pair even when the token count is odd, and NaN times 0 is NaN, so the padding row must be zero"],
        ["GOF", "group of four: four tokens of K and V data staged for the FPGA's hardware KV cache, as one 8 KB K block and one 8 KB V block (h/tron/gof.hpp header comment). The staging code reaches a page's rows through the page_info callbacks declared in that file. The design defines GOF differently; finding F24 corrects it"],
        ["EAGLE", "the speculative model; its cache uses an extra storage region"],
        ["parent PR, child PR", "the parent is the new PR that issue #4525 asks for; the child is PR 4424 after it is rebased onto the parent"],
        ["main tip, snapshot", "98bb8cb2 (2026-09-19) was the main tip when the design was written and when this review started; main moved to 2880c3aa9b at 01:14 UTC on 2026-09-22. The snapshot is commit f46e48ba (2026-09-15), the base GitHub records for PR 4424 and the revision the design reviewed"],
        ["CI, Nix test build, TRON_AMX_DISPATCH, TRON_K_VNNI", "CI is the automated build and test. The Nix test build is the required CI lane. The two CMake options compile the AMX attention kernels and PR 4424's K layout; the Nix lane sets neither"],
        ["finder, verifier", "review agents. Eight finders each read the design through one lens; three verifiers then tried to refute every finding (a source-truth lens, a design-text-fairness lens, an intent lens). A finding survived only if at least two verifiers could not refute it"],
        ["blocker, major, minor, note", "severities; the table in section 4 gives the meaning of each"],
    ],
    "issue_intro": [
        "jhan asked codex to create the issue if it agreed with the plan, assign it to jhan, and describe the new PR. The live issue (fetched 2026-09-22 00:3x UTC) is titled \"Introduce typed KV-cache tensors for packed V and native K\", is assigned to jhan-positron, and has five scope bullets and a three-step PR order. jhan renamed it and rewrote its first sentence at 00:10 UTC to say the refactor is \"independent from PR #4424\" instead of \"before #4424\".",
        "The table checks each request against the live body.",
    ],
    "issue_rows": [
        ["A new parent PR types the existing pair-interleaved V and native K on main; PR 4424 is then rebased onto it", "jhan's prompt, item 4", ["ok", "yes"], "Scope bullets 1-5 and PR order steps 1-2."],
        ["Ben's worker-index question (comment #1) stays in PR 4424", "jhan's prompt, item 1", ["ok", "yes"], "PR order step 3 links discussion r4065141577 and calls it \"a separate concern there\"."],
        ["Follow the tensor / dtensor / expr precedent; a rank-2 type with row-wise load and store", "Ben's review 5270587330", ["ok", "yes"], "Scope bullet 1: \"Use the existing expr interface for logical tensor and row operations.\""],
        ["Address mapping lives in the view; storage is a separate owner", "Ben's sketch 5765866077 plus his reservation; jhan's reading", ["ok", "yes"], "Scope bullet 2: \"Combine the address mapping with the concrete view. Keep storage ownership separate.\""],
        ["Typed cache and kernel boundaries so packed V and native K cannot be confused", "Ben's sketch, section 5", ["ok", "yes"], "Scope bullet 4."],
        ["Preserve layouts, conversions, the zero-initialization invariant, and the optimized paths", "Ben's sketch, sections 3-4", ["ok", "yes"], "Scope bullet 3."],
        ["Storage is constructed in the arena, never obtained by casting; no raw pointer can be relabelled as packed; no clearing added to allocation", "Ben's sketch, sections 2-3", ["warn", "implied only"], "Only the generic words \"Keep storage ownership separate\" and \"Preserve existing ... initialization rules\". The design covers all three (its sections 5 and 6), so the gap is in the public record, not in the guidance."],
        ["Assigned to jhan", "jhan's prompt, item 4", ["ok", "yes"], "Assignee jhan-positron (issue events, 2026-09-21 23:37 UTC)."],
        ["A reader who has not opened the PR thread can follow the issue", "Repository issue template (asks for the problem first); jhan's own issue #4500 (opens with a Short version and a Words used here list)", ["warn", "no"], "The body opens with \"Introduce typed tensor access ...\" and never states Ben's problem (bare bf16 pointers carry no layout). \"packed V\" and \"native K\" are not defined."],
        ["The direction of dependence between the two PRs is stated", "jhan's 00:10 UTC edit", ["warn", "no"], "The first sentence says \"independent from PR #4424\"; PR order step 2 says \"Rebase #4424 onto that parent\". Both are true in one direction only (the new PR needs nothing from PR 4424; PR 4424 will need the new PR). The body does not say so."],
    ],
    "issue_outro": overrides.get("issue_outro") or [
        "**Verdict: the issue captures the request.** Every item Ben asked for and every item in jhan's plan appears in the body or follows from it. Three additions would make the body self-contained. First, one problem sentence before Scope: cache K and V planes are passed as bare bf16 pointers whose type does not record the layout, and PR 4424 adds a third layout. Second, one-line definitions of pair-interleaved V, native K, and PR 4424's blocked K. Third, one sentence on direction: this PR does not depend on PR 4424; PR 4424 will be rebased onto it so its K layout becomes a local change inside the new type.",
        "Two smaller points. The issue names Ben twice; jhan's standing rule for issues drafted for him is roles and links only, and jhan left the names in when editing, so this is jhan's call. The design page and its saved evidence files still carry the pre-edit title (\"before PR #4424\") and the deleted last paragraph; finding F-issue-stale below asks codex to refresh them.",
    ],
    "ben_intro": [
        "Ben's sketch has three parts: a layout struct with a static offset function, a storage owner templated on the layout, and a view templated on the layout. His reservation was: \"I'm not entirely convinced of the necessity of separate k_vnni_layout from vnni_view but regardless, it's a starting point\". jhan read this as: the layout should be the view, and agreed. The design agrees too and says jhan's interpretation is \"mostly right\".",
    ],
    "ben_outro": [
        "**jhan's reading is right on the point Ben raised.** Ben's doubt concerns only the separate layout type. Folding the offset formula into the view removes that type. Storage stays a separate owner in Ben's sketch, in jhan's reading, and in the design.",
        "Two precisions the design should state instead of \"mostly right\":",
    ],
    "ben_bullets": overrides.get("ben_bullets") or [
        "Ben's sketch is not a chain layout -> storage -> view. The layout type is a template parameter of both the storage and the view (vnni_tensor<Layout> and vnni_view<T, Layout>), and the view calls Layout::offset. jhan's chain wording describes the dependency, not the shape. Nothing in jhan's reading proposed merging storage into the view, so the design's storage sentence does not correct a mistake.",
        "Ben voiced a doubt, not a decision. The design turns it into a rule (\"Simplify: each view type contains its address calculation\") without saying that the merge is the design's own choice and that Ben should confirm it. The price of the merge is concrete: one view type per layout (a V view now, a K view in the child) that repeat the const conversion, the deleted rvalue access, and the friend accessor, instead of one template over a layout parameter. Ben may prefer either; the design should offer both shapes and let him pick.",
        "The design departs from Ben in three further places and lists no questions for him: it makes a const view yield read-only rows where Ben wrote \"as with std::span, a const view object does not make its elements const\" (the repository itself is split on this, see finding F-const below); it replaces Ben's at(token, dim) with operator[][]; and it adds slices, iterators, and generic expression assignment that Ben did not ask for. jhan's item 3 said to stop and write questions when disagreeing with Ben. Stopping was not required here, because the reservation was soft and the merge is the direction jhan and Ben both lean to. A short \"Questions for Ben\" block in the design, and a one-paragraph reply in the PR thread pointing him at issue #4525, would close the loop. As of 2026-09-22 00:3x UTC, the PR thread has no reply after Ben's sketch and the issue has no cross-reference from the PR.",
    ],
    "findings_intro": overrides.get("findings_intro", "Eight finders produced %d raw candidates, grouped into 59 distinct findings. Each was put to three verifiers who tried to refute it; 49 survived and the 10 that did not are listed in section 7. A completeness critic then added 9 candidates, and all 9 survived the same verification, for %d findings in total. Severities below are the lead's final grades; where they differ from the finder's grade, the finding says so under Lead's reading." % (
        result.get("raw_count", len(result.get("raw", []))), len(out_conf))),
    "show_partner_diagram": overrides.get("show_partner_diagram", True),
    "partner_intro": overrides.get("partner_intro", "The one blocker turns on the Zero-Initialized V Slots invariant. The figure shows one V pair on a page offset that is being reused, under today's code and under the two write operations the design defines."),
    "strengths": overrides.get("strengths", result.get("critic_strengths", [])),
    "edits": overrides.get("edits", []),
    "rejected_intro": "These candidates were raised by a finder and refuted by at least two of the three verifiers. They are listed so that a reader who has the same doubt can see why it did not hold.",
    "method": overrides.get("method", [
        "The lead first verified the ground facts by hand: the live issue and its edit history, Ben's three comments from the GitHub API, the commit graph (f46e48ba is an ancestor of the live tip 98bb8cb2), the files that changed between them, and the tron source lines the design cites. Those facts were written to a file every agent read first [evidence/claude-review/lead-verified-facts.md].",
        "The design was then reviewed by a workflow of agents. Every finding on this page carries the evidence its finder cited and the votes of its three verifiers. The lead read every surviving finding and its votes before publishing, and corrected wording where a verifier's correction was right.",
    ]),
    "method_bullets": overrides.get("method_bullets", [
        "Finder lenses: issue capture; fidelity to Ben and to jhan's reading; C++ interface soundness against tron's expr, view, slice and tensor machinery; behavior preservation (zero-init invariant, conversions, copies, staging); PR split and process (revisions, CI, repository rules); simplicity and scope; handoff actionability (can an agent implement it without guessing; citation spot-check); formulas and page quality.",
        "Verifier lenses: source truth (re-derive from tron source, Ben's text, the issue), design-text fairness (does the design already handle it elsewhere), intent (does the finding respect what Ben and jhan asked for; assign consequence-based severity).",
        "Not done: no C++ was compiled, no test was built or run, no benchmark was taken. The design itself states the same limits. Claims about compile-time behavior (triviality, aliases, concept checks) rest on reading the headers at the pinned commits.",
        "Files: the facts the lead verified first [lead-verified-facts.md](../evidence/claude-review/lead-verified-facts.md); raw candidates [raw-findings-round1.json](../evidence/claude-review/raw-findings-round1.json); workflow result with every vote [workflow-result.json](../evidence/claude-review/workflow-result.json); the lead's re-grades and amendments [overrides.json](../evidence/claude-review/overrides.json); page data [findings.json](../evidence/claude-review/findings.json); generator [gen_review.py](../evidence/claude-review/gen_review.py); all votes rendered [claude-review-design-new-tensor-type-votes.html](claude-review-design-new-tensor-type-votes.html).",
    ]),
    "confirmed": out_conf,
    "rejected": rejected,
    "lens_verdicts": result.get("lens_verdicts", {}),
    "critic_overall": result.get("critic_overall", ""),
}
if overrides.get("issue_rows_replace_last"):
    data["issue_rows"][-1] = overrides["issue_rows_replace_last"]
if overrides.get("method_extra"):
    data["method"].append(overrides["method_extra"])
data["tiles"][2]["v"] = "Accept with changes"
data["tiles"][2]["s"] = "%d blocker, %d major, %d minor, %d notes after the lead's re-grade" % (counts["blocker"], counts["major"], counts["minor"], counts["note"])
data["tiles"][1]["s"] = "with two precisions and three open questions for Ben; see section 3"
data["tiles"][0]["s"] = "2 additions would make it self-contained; see section 2"
(HERE / "findings.json").write_text(json.dumps(data, indent=1))
print("findings.json written:", len(out_conf), "confirmed,", len(rejected), "rejected;", counts)
