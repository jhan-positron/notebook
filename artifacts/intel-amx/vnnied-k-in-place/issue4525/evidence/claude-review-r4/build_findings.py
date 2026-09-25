#!/usr/bin/env python3
"""Build findings.json for the ROUND-4 gen_review.py from the workflow result + static prose.

Usage: python3 build_findings.py <workflow-result.json>
The workflow result is the Workflow tool's output file; its script return value sits under ['result']
(keys: dispositions, dispo_batches, raw, merge_dropped, merged, confirmed, rejected, critic_overall,
critic_strengths, critic_disputes, judges). Lead edits live in overrides.json (drop / regrade / amend for
new findings; restatus / remark / residual for dispositions; prose blocks).
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R1 = json.loads((HERE.parent / "claude-review" / "findings.json").read_text())
R2 = json.loads((HERE.parent / "claude-review-r2" / "findings.json").read_text())
R3 = json.loads((HERE.parent / "claude-review-r3" / "findings.json").read_text())
raw = json.loads(Path(sys.argv[1]).read_text())
result = raw["result"] if isinstance(raw, dict) and "result" in raw and "dispositions" not in raw else raw
overrides = json.loads((HERE / "overrides.json").read_text()) if (HERE / "overrides.json").exists() else {}

SEV_ORDER = ["blocker", "major", "minor", "note"]


def short(text, limit=420):
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        if out and sum(len(x) + 1 for x in out) + len(sent) > limit:
            break
        out.append(sent)
    return " ".join(out)


r3_new = {f["id"]: f for f in R3["confirmed"]}            # G.., H..
r3_disp = {d["id"]: d for d in R3["dispositions"]}         # N.., M.., F.., C.. with round-3 status and origin
r2_new = {f["id"]: f for f in R2["confirmed"]}            # N.., M..
r2_disp = {d["id"]: d for d in R2["dispositions"]}         # F.., C.. with round-2 status
r1_by_id = {f["id"]: f for f in R1["confirmed"]}
r1_rejected = {f["id"]: f for f in R1.get("rejected", [])}
r2_rejected = {f["id"]: f for f in R2.get("rejected", [])}
r3_rejected = {f["id"]: f for f in R3.get("rejected", [])}

# ---------------------------------------------------------------- dispositions (79 items)
restatus = overrides.get("restatus", {})
remarks = overrides.get("remark", {})
residuals = overrides.get("residual", {})
dispositions = []
for d in result["dispositions"]:
    x = dict(d)
    i = d["id"]
    if i in r3_new:
        x["origin"] = "round 3"
        x["prior_severity"] = r3_new[i]["severity"]
        x["prior_title"] = r3_new[i]["title"]
        x["prior_status"] = "new in round 3"
        x["history"] = []
    else:
        d3 = r3_disp[i]
        x["origin"] = d3["origin"]
        x["prior_severity"] = d3["prior_severity"]
        x["prior_title"] = d3["prior_title"]
        x["prior_status"] = d3["final_status"]
        hist = []
        if d3["origin"] == "round 1":
            hist.append(("round 2", r2_disp[i]["final_status"]))
        hist.append(("round 3", d3["final_status"]))
        x["history"] = hist
    if i in restatus:
        x["final_status"] = restatus[i]
        x["lead_restatus"] = True
    if i in residuals:
        x["residual"] = residuals[i]
    x["remark"] = remarks.get(i, short(d.get("assessment", "")))
    dispositions.append(x)
expected = set(r3_new) | {i for i, d in r3_disp.items() if d["final_status"] != "resolved"}
missing = sorted(expected - {d["id"] for d in dispositions})
if missing:
    print("WARNING: known items without a disposition:", missing, file=sys.stderr)
extra = sorted({d["id"] for d in dispositions} - expected)
if extra:
    print("WARNING: dispositions for unknown items:", extra, file=sys.stderr)
scounts = {}
for x in dispositions:
    scounts[x["final_status"]] = scounts.get(x["final_status"], 0) + 1

# items round 3 resolved: keep their anchors (60)
r3_resolved = [{"id": i, "title": d["prior_title"], "severity": d["prior_severity"], "origin": d["origin"]}
               for i, d in sorted(r3_disp.items()) if d["final_status"] == "resolved"]
# round-1 items resolved in round 2: keep their anchors (35)
r1_resolved_r2 = list(R3["r1_resolved_r2"])

# ---------------------------------------------------------------- new findings (J.., L..)
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
        g["lead_dropped"] = True
        g["lead_drop_reason"] = overrides.get("drop_reason", {}).get(f["id"], "")
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

REJ_NOTE = overrides.get("rejected_prior_note", {})
DEFAULT_REJ = "Still rejected; the design's section 9 says so and this round agrees."
rejected_prior = [{"id": rid, "round": "1", "title": r1_rejected[rid]["title"], "note": REJ_NOTE.get(rid, DEFAULT_REJ)} for rid in sorted(r1_rejected)]
rejected_prior += [{"id": rid, "round": "2", "title": r2_rejected[rid]["title"], "note": REJ_NOTE.get(rid, DEFAULT_REJ)} for rid in sorted(r2_rejected)]
for rid in sorted(r3_rejected):
    f = r3_rejected[rid]
    note = REJ_NOTE.get(rid, ("Dropped by the round-3 lead (%s); needs no design response." % f.get("lead_drop_reason", "")) if f.get("lead_dropped") else DEFAULT_REJ)
    rejected_prior.append({"id": rid, "round": "3", "title": f["title"], "note": note, "dropped": bool(f.get("lead_dropped"))})

data = {
    "title": "Typed Cache Tensors Design Review, Round 4",
    "eyebrow": "Round-4 review of the third codex revision of the design for issue #4525 (positron-ai/tron)",
    "h1": overrides.get("h1", "Did the third revision close the round-3 findings, and is the typed KV-cache tensor design implementable now?"),
    "meta": overrides.get("meta", "(fill in overrides.json)"),
    "short_version": overrides.get("short_version", ["(fill in overrides.json)"]),
    "tiles": overrides.get("tiles", [
        {"k": "Known items", "v": "%d of %d resolved" % (scounts.get("resolved", 0), len(dispositions)), "badge": ["ok", "closed"], "s": "%d partly, %d deferred, %d unresolved, %d regressed; see section 3" % (scounts.get("partly", 0), scounts.get("deferred", 0), scounts.get("unresolved", 0), scounts.get("regressed", 0))},
        {"k": "New findings", "v": "%d" % len(confirmed), "badge": ["warn", "on this revision"], "s": "%d blocker, %d major, %d minor, %d notes; see section 4" % (counts["blocker"], counts["major"], counts["minor"], counts["note"])},
        {"k": "Verdict", "v": overrides.get("verdict_tile", "(fill in)"), "badge": overrides.get("verdict_badge", ["warn", "see section 8"]), "s": overrides.get("verdict_sub", "")},
    ]),
    "words": overrides.get("words", []),
    "changes_intro": overrides.get("changes_intro", []),
    "changes_rows": overrides.get("changes_rows", []),
    "changes_outro": overrides.get("changes_outro", []),
    "dispositions": dispositions,
    "dispo_intro": overrides.get("dispo_intro", []),
    "dispo_outro": overrides.get("dispo_outro", []),
    "r3_resolved": r3_resolved,
    "r3_resolved_intro": overrides.get("r3_resolved_intro", "Round 3 graded these 60 items resolved: 50 round-2 findings and 10 round-1 residuals. This round did not re-grade them; the rows are kept so that every earlier id keeps an anchor on this page."),
    "r1_resolved_r2": r1_resolved_r2,
    "r1_resolved_intro": overrides.get("r1_resolved_intro", "Round 2 graded these 35 round-1 findings resolved. Rounds 3 and 4 did not re-grade them; the rows are kept so that the design's [F..] and [C..] links keep working."),
    "rejected_prior_intro": overrides.get("rejected_prior_intro", "Round 1 rejected ten candidates, round 2 six, and round 3 two (plus two the lead dropped). The design's section 9 keeps them rejected, and this round agrees."),
    "rejected_prior": rejected_prior,
    "confirmed": confirmed,
    "rejected": rejected,
    "findings_intro": overrides.get("findings_intro", "(fill in)"),
    "figure_html": overrides.get("figure_html", ""),
    "questions_intro": overrides.get("questions_intro", ["(fill in)"]),
    "questions_rows": overrides.get("questions_rows", []),
    "questions_outro": overrides.get("questions_outro", []),
    "strengths": overrides.get("strengths", result.get("critic_strengths", [])),
    "edits": overrides.get("edits", ["(fill in)"]),
    "verdict_intro": overrides.get("verdict_intro", ["(fill in)"]),
    "judges": judges,
    "verdict_outro": overrides.get("verdict_outro", []),
    "rejected_intro": overrides.get("rejected_intro", "These candidates were refuted by at least two of the three verifiers, or dropped by the lead after reading the votes. They are listed so a reader can see what was considered and why it did not hold; the votes page carries the full reasons."),
    "method": overrides.get("method", ["(fill in)"]),
    "method_bullets": overrides.get("method_bullets", []),
}
(HERE / "findings.json").write_text(json.dumps(data, indent=1))
print("wrote findings.json:", len(dispositions), "dispositions", scounts, "| new confirmed", len(confirmed), counts, "| rejected", len(rejected), "| judges", len(judges), "| r3_resolved", len(r3_resolved), "| rejected_prior", len(rejected_prior))
