#!/usr/bin/env python3
"""Build findings.json for the ROUND-2 gen_review.py from the workflow result + static prose.

Usage: python3 build_findings.py <workflow-result.json>
Keys of the workflow result: dispositions, dispo_batches, lens_verdicts, raw, confirmed, rejected,
critic_overall, critic_strengths, critic_disputes, judges.
Lead edits live in overrides.json (drop / regrade / amend for new findings; restatus / remark for
dispositions; prose blocks). Static prose lives here so the page can be regenerated from data alone.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R1 = json.loads((HERE.parent / "claude-review" / "findings.json").read_text())
result = json.loads(Path(sys.argv[1]).read_text())
overrides = json.loads((HERE / "overrides.json").read_text()) if (HERE / "overrides.json").exists() else {}

SEV_ORDER = ["blocker", "major", "minor", "note"]


def short(text, limit=420):
    """First sentences of a checker assessment, up to about limit characters."""
    import re as _re
    out = []
    for sent in _re.split(r"(?<=[.!?])\s+", text.strip()):
        if out and sum(len(x) + 1 for x in out) + len(sent) > limit:
            break
        out.append(sent)
    return " ".join(out)


r1_by_id = {f["id"]: f for f in R1["confirmed"]}
r1_rejected = {f["id"]: f for f in R1.get("rejected", [])}

# ---------------------------------------------------------------- dispositions
restatus = overrides.get("restatus", {})
remarks = overrides.get("remark", {})
dispositions = []
for d in result["dispositions"]:
    r1 = r1_by_id.get(d["id"], {})
    x = dict(d)
    x["r1_severity"] = r1.get("severity", "note")
    x["r1_title"] = r1.get("title", d["id"])
    if d["id"] in restatus:
        x["final_status"] = restatus[d["id"]]
        x["lead_restatus"] = True
    x["remark"] = remarks.get(d["id"], short(d.get("assessment", "")))
    dispositions.append(x)
missing_ids = sorted(set(r1_by_id) - {d["id"] for d in dispositions})
if missing_ids:
    print("WARNING: round-1 ids without a disposition:", missing_ids, file=sys.stderr)
scounts = {}
for x in dispositions:
    scounts[x["final_status"]] = scounts.get(x["final_status"], 0) + 1

# ---------------------------------------------------------------- new findings
drop = set(overrides.get("drop", []))
regrade = overrides.get("regrade", {})
amend = overrides.get("amend", {})
confirmed = []
for f in result["confirmed"]:
    if f["id"] in drop:
        continue
    f = dict(f)
    if f["id"] in regrade:
        f["severity"] = regrade[f["id"]]
    for k, v in amend.get(f["id"], {}).items():
        f[k] = v
    confirmed.append(f)
rejected = list(result.get("rejected", []))
for f in result["confirmed"]:
    if f["id"] in drop:
        g = dict(f)
        g["votes"] = g.get("votes", [])
        g["lead_dropped"] = True
        rejected.append(g)
counts = {s: sum(1 for f in confirmed if f["severity"] == s) for s in SEV_ORDER}

# ---------------------------------------------------------------- judges
JUDGE_LABEL = {"implementer": "Implementing agent's view", "maintainer": "Maintainer's (Ben's) view", "risk": "Risk reviewer's view"}
BADGE = {"accept as is": "ok", "accept with minor edits": "ok", "accept with changes": "warn", "redo": "blocker"}
judges = []
for j in result.get("judges", []):
    judges.append({"label": JUDGE_LABEL.get(j["judge"], j["judge"]), "verdict": j["verdict"], "badge": BADGE.get(j["verdict"], "note"),
                   "implementable_now": j["implementable_now"], "reasons": j["reasons"], "top_three_edits": j.get("top_three_edits", []),
                   "must_fix": j.get("must_fix_before_implementation", []), "questions_block_adequate": j.get("questions_block_adequate")})

REJ_NOTE = overrides.get("rejected_r1_note", {})
rejected_r1 = [{"id": rid, "title": r1_rejected[rid]["title"], "note": REJ_NOTE.get(rid, "Still rejected. The revision does not reinstate it as a defect (design section 9).")} for rid in sorted(r1_rejected)]

data = {
    "title": "Typed Cache Tensors Design Review, Round 2",
    "eyebrow": "Round-2 review of the REVISED codex design for issue #4525 (positron-ai/tron)",
    "h1": "Did the revised design for typed KV-cache tensors close the round-1 findings, and is it implementable now?",
    "meta": overrides.get("meta", "Reviewed 2026-09-22 UTC by Claude (Fable 5.1) for jhan. Design reviewed: [status/design-new-tensor-type.html](design-new-tensor-type.html), revised by codex after the [round-1 review](%s) (revision finalized 2026-09-22 03:06 UTC, 83,567 bytes). Sources pinned to main f46e48ba (the design's snapshot), main 98bb8cb2 (the tip the design records), the live main tip 2880c3aa9b (fetched 2026-09-22 ~04:00 UTC, unchanged since 01:14 UTC) and PR 4424 head 30c4ac82cb." % "claude-review-design-new-tensor-type-r1.html"),
    "short_version": overrides.get("short_version", ["(fill in overrides.json)"]),
    "tiles": overrides.get("tiles", [
        {"k": "Round-1 findings", "v": "%d of 58 resolved" % scounts.get("resolved", 0), "badge": ["ok", "closed"], "s": "%d partly, %d deferred, %d unresolved, %d regressed; see section 3" % (scounts.get("partly", 0), scounts.get("deferred", 0), scounts.get("unresolved", 0), scounts.get("regressed", 0))},
        {"k": "New findings", "v": "%d" % len(confirmed), "badge": ["warn", "on the revision"], "s": "%d blocker, %d major, %d minor, %d notes; see section 4" % (counts["blocker"], counts["major"], counts["minor"], counts["note"])},
        {"k": "Verdict", "v": overrides.get("verdict_tile", "(fill in)"), "badge": overrides.get("verdict_badge", ["warn", "see section 8"]), "s": overrides.get("verdict_sub", "")},
    ]),
    "words": [
        ["tron", "the inference program under test; its source is the positron-ai/tron repository"],
        ["PR 4424, the child", "the open draft pull request \"VNNI K: store the K cache of 128-dimension heads in the AMX VNNI layout, with a shared block save\" (branch jhan-amx-vnniK, head 30c4ac82cb). After the new parent PR exists, PR 4424 is rebased onto it and is then called the child"],
        ["the parent PR", "the new pull request that issue #4525 asks for: typed access to the existing V and K caches on main, with no new layout"],
        ["Ben, the reviewer", "the tron maintainer who reviewed PR 4424 on 2026-09-21 (a worker-index question, a review asking for typed tensors, and an API sketch). The revised design calls him \"the reviewer\""],
        ["codex, the design, the revision", "codex is the agent jhan asked to answer Ben; the design is the page it wrote, status/design-new-tensor-type.html; the revision is the version of that page finalized 2026-09-22 03:06 UTC after the round-1 review"],
        ["round 1, F.. and C.. ids", "the first Claude review of the original design (2026-09-22 ~03:00 UTC), archived as [claude-review-design-new-tensor-type-r1.html](claude-review-design-new-tensor-type-r1.html). Its 58 retained findings are F01-F59 (finders) and C01-C09 (completeness critic); ten candidates F06, F07, F09, F18, F22, F33, F36, F44, F53, F55 were rejected. The revised design cites these ids in brackets, for example [F05]"],
        ["N.. and M.. ids", "new findings of this round: N.. from the eight finders, M.. from the completeness critic"],
        ["issue #4525", "the GitHub issue codex created for the parent PR; jhan edited its title and first sentence on 2026-09-22 00:10 UTC; unchanged since"],
        ["KV cache, K, V", "the saved key (K) and value (V) vectors of earlier tokens; attention reads them"],
        ["page, slot, head, D", "a page holds 64 token positions; a slot is the cache region of one layer (or of several layers that share it); a head is one attention head; D is the head size, the number of values per token per head (128 for PR 4424's models)"],
        ["bf16", "the 16-bit brain floating-point format used for cached K and V"],
        ["AMX, AVX-512, 16-lane and 8-lane builds", "AMX and AVX-512 are CPU instruction sets. tron's vector width TRON_CHUNK_SIZE is 16 fp32 values with AVX-512 (the 16-lane build) and 8 without (the 8-lane build); the 8-lane build stores V row-major, so it has no pair-interleaved V"],
        ["packed V (pair-interleaved V)", "today's V storage in the 16-lane build: for each dimension, tokens 2p and 2p+1 sit next to each other. Element offset = (token/2)*(2*D) + 2*dim + token%2"],
        ["native K", "today's K storage: one token's D values consecutive in memory (row-major)"],
        ["blocked packed K (VNNI K)", "PR 4424's K storage for 128-dimension heads: two consecutive dimensions of one token share a 4-byte unit, and 16 tokens share one 64-byte line"],
        ["expr, view, const_view, tensor", "tron's expression interface (h/tron/kernels/expr.hpp), its typed pointer views over regularly laid-out memory and their read-only form (h/tron/tensor/view.hpp), and its owning arrays (h/tron/tensor/tensor.hpp)"],
        ["v_vnni_tensor, v_vnni_view, v_vnni_row", "the revised design's names for the packed-V owner (the aligned array inside the cache block), the typed rank-2 view over it, and its logical row expression"],
        ["append_v_row, load_row, copy_token, copy_plane", "the revised design's typed bulk operations: write one token's V row into the packed plane (even token zeroes its odd partner), read one row out, copy one token between planes, copy a whole plane"],
        ["kv_block", "the struct that holds K then V for one head of one slot in one page (h/tron/models/kv_cache.hpp)"],
        ["set_v, get_v, append_v, scaled_v, v_data", "today's V functions in kv_cache.hpp: write one token, read one token, copy one token between pages, compute the weighted V sum, and return the raw pointer of a V plane"],
        ["save_v_impl", "the model function (h/tron/models/model.hpp) that stores one token's V into the cache during a forward pass; it calls page::set_v"],
        ["Zero-Initialized V Slots invariant", "the rule in kv_cache.hpp that every even-token V write zeroes its odd partner row. The weighted sum reads a whole pair even when the token count is odd, and NaN times 0 is NaN, so the padding row must be zero"],
        ["arena, book", "an arena is one allocated memory region holding cache blocks; book is the class that owns the arenas and the pages"],
        ["EAGLE", "the speculative model; its cache adds one extra physical KV slot and a separate embedding buffer (x_data); it requires uniform geometry"],
        ["GOF, page_info", "group of four: four tokens of K and V staged for the FPGA's hardware KV cache; the staging code reaches a page's rows through the page_info callbacks in h/tron/gof.hpp (namespace tron::hardware)"],
        ["CI, Nix test build, TRON_AMX_DISPATCH, TRON_K_VNNI", "CI is the automated build and test. The Nix test build is the required CI lane. The two CMake options compile the AMX attention kernels and PR 4424's K layout; the Nix lane sets neither. Issue #3997 tracks the AMX gap"],
        ["checker, re-grader, finder, verifier, judge", "review agents of this round. A checker graded a batch of round-1 findings against the revision; two re-graders (a source-truth lens and a fairness lens) independently re-graded each; the majority of the three decided. Eight finders looked for new defects; three verifiers tried to refute each; a finding survived when at least two could not. Three judges gave independent implementability verdicts"],
        ["resolved, partly, deferred, unresolved, regressed", "disposition statuses; the table in section 3 gives the meaning of each"],
        ["blocker, major, minor, note", "severities; the table in section 4 gives the meaning of each"],
    ] + overrides.get("words_extra", []),
    "changes_intro": overrides.get("changes_intro", [
        "The revision keeps the structure of the original design and adds the parts the round-1 review asked for. Codex changed no production code, posted nothing to GitHub, and edited no issue; it says so in the page header and in section 10.",
    ]),
    "changes_rows": overrides.get("changes_rows", [
        ["Size and sections", "67,216 bytes; 10 sections", "83,567 bytes; 10 sections; section 9 is now a disposition table of the 58 round-1 findings and section 2 has a \"Questions for the reviewer\" block"],
        ["Non-ASCII characters", "267", "59 (em dash in the title, curly quotes, arrows, multiplication signs)"],
        ["Type names", "vnni_tensor / vnni_view / vnni_row for V; k_vnni_* for the child", "v_vnni_tensor / v_vnni_view / v_vnni_row; native_k_view and const_native_k_view aliases for K; k_vnni_* stays in the child"],
        ["Scope of the parent", "matrix and row expressions, slices, iterators, generic row.set / matrix.set / set_pair, owner expression constructor", "expression reads and typed bulk operations only; slices, iteration, generic assignment and the owner expression constructor are listed as \"Explicitly deferred\""],
        ["Model V save path", "not named", "save_v_impl -> page::set_v -> append_v_row named in the accessor table and in step 3; a \"One cache row-write rule\" table gives the even/odd partner behavior"],
        ["Accessor mapping", "absent", "a table with one row per existing accessor (page::k, set_v, get_v, v/v_ptr, v_data/v_base, append_v, scaled_v, kernels)"],
        ["Revision table", "98bb8cb2 labelled a stale local copy", "98bb8cb2 labelled the main tip recorded when the design was written, 79 commits after the older snapshot; the older snapshot labelled \"the older PR base, not the main tip\""],
        ["Arena construction", "\"placement construction\"; std::start_lifetime_as offered as an option", "the exact array-new form with a runtime bound; construct_at / T() / T{} forbidden; start_lifetime_as removed; uniform and heterogeneous enumeration rules; EAGLE slot and x_data distinguished"],
        ["8-lane build", "three configurations listed without flags", "both chunk widths must compile the packed types; exact CMake flags per configuration; the 8-lane lane has no CI coverage, stated"],
        ["CI paragraph", "\"A required CI job must build with AMX enabled\"", "the AMX gap is separately tracked by issue #3997; the Nix flag change is a decision for jhan and the CI owners"],
        ["Ben's sketch", "\"Your interpretation is mostly right\"; \"No clarification from Ben is needed\"", "\"The interpretation of the reviewer's reservation is right\"; four questions with proposed answers, marked as proposals pending reviewer agreement"],
        ["Issue #4525 and the PR thread", "no reply planned", "still no reply or issue edit; the design says a future PR reply should link the issue and the questions, and that the issue-body additions are recorded in the design only"],
    ]),
    "changes_outro": overrides.get("changes_outro", []),
    "dispositions": dispositions,
    "dispo_intro": overrides.get("dispo_intro", [
        "Each of the 58 round-1 findings was checked against the revised text by one checker agent and then independently re-graded by two adversarial re-graders (a source-truth lens and a fairness lens). The status below is the majority of the three; a split vote (three different statuses) keeps the checker's status and is flagged. Where I (the lead) changed a status after reading the votes, the row says so.",
    ]),
    "dispo_outro": overrides.get("dispo_outro", []),
    "rejected_r1_intro": overrides.get("rejected_r1_intro", "Round 1 rejected ten candidate findings. The revised design's section 9 says it does not reinstate them as defects, and this round agrees. Two of them still shaped the revision in a useful way: F09's generic-write scope is deferred as part of the smaller parent, and F36's rvalue-overload clarification is kept."),
    "rejected_r1": rejected_r1,
    "confirmed": confirmed,
    "rejected": rejected,
    "findings_intro": overrides.get("findings_intro", "Eight finders read the revised text through one lens each (C++ interface, behavior and arena construction, process and CI, handoff actionability, fidelity to Ben, simplicity and scope, formulas and page quality, the child's needs). Their candidates, plus defects the disposition checkers found in the fixes themselves, were merged and each put to three verifiers who tried to refute it; a finding survived only if at least two could not. A completeness critic then added candidates that went through the same verification. Severities are the lead's final grades; where they differ from the finder's grade, the finding says so under Lead's reading."),
    "figure_html": overrides.get("figure_html", ""),
    "questions_intro": overrides.get("questions_intro", ["(fill in)"]),
    "questions_rows": overrides.get("questions_rows", []),
    "questions_outro": overrides.get("questions_outro", []),
    "strengths": overrides.get("strengths", result.get("critic_strengths", [])),
    "edits": overrides.get("edits", ["(fill in)"]),
    "verdict_intro": overrides.get("verdict_intro", ["(fill in)"]),
    "judges": judges,
    "verdict_outro": overrides.get("verdict_outro", []),
    "rejected_intro": overrides.get("rejected_intro", "These candidates were refuted by at least two of the three verifiers. They are listed so a reader can see what was considered and why it did not hold; the votes page carries the full reasons."),
    "method": overrides.get("method", ["(fill in)"]),
    "method_bullets": overrides.get("method_bullets", []),
}
(HERE / "findings.json").write_text(json.dumps(data, indent=1))
print("wrote findings.json:", len(dispositions), "dispositions", scounts, "| new confirmed", len(confirmed), counts, "| rejected", len(rejected), "| judges", len(judges))
