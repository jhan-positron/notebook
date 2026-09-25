#!/usr/bin/env python3
"""Build findings.json for the ROUND-3 gen_review.py from the workflow result + static prose.

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


r2_new = {f["id"]: f for f in R2["confirmed"]}            # N.., M..
r2_disp = {d["id"]: d for d in R2["dispositions"]}         # F.., C.. with round-2 status
r1_by_id = {f["id"]: f for f in R1["confirmed"]}
r1_rejected = {f["id"]: f for f in R1.get("rejected", [])}
r2_rejected = {f["id"]: f for f in R2.get("rejected", [])}

# ---------------------------------------------------------------- dispositions (87 items)
restatus = overrides.get("restatus", {})
remarks = overrides.get("remark", {})
residuals = overrides.get("residual", {})
dispositions = []
for d in result["dispositions"]:
    x = dict(d)
    i = d["id"]
    if i in r2_new:
        x["origin"] = "round 2"
        x["prior_severity"] = r2_new[i]["severity"]
        x["prior_title"] = r2_new[i]["title"]
        x["prior_status"] = "new in round 2"
    else:
        x["origin"] = "round 1"
        x["prior_severity"] = r2_disp[i]["r1_severity"]
        x["prior_title"] = r2_disp[i]["r1_title"]
        x["prior_status"] = r2_disp[i]["final_status"]
    if i in restatus:
        x["final_status"] = restatus[i]
        x["lead_restatus"] = True
    if i in residuals:
        x["residual"] = residuals[i]
    x["remark"] = remarks.get(i, short(d.get("assessment", "")))
    dispositions.append(x)
expected = set(r2_new) | {i for i, d in r2_disp.items() if d["final_status"] != "resolved"}
missing = sorted(expected - {d["id"] for d in dispositions})
if missing:
    print("WARNING: known items without a disposition:", missing, file=sys.stderr)
scounts = {}
for x in dispositions:
    scounts[x["final_status"]] = scounts.get(x["final_status"], 0) + 1

# round-1 items resolved in round 2: keep their anchors
r1_resolved_r2 = [{"id": i, "title": d["r1_title"], "severity": d["r1_severity"]} for i, d in sorted(r2_disp.items()) if d["final_status"] == "resolved"]

# ---------------------------------------------------------------- new findings (G.., H..)
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
rejected_prior = [{"id": rid, "round": "1", "title": r1_rejected[rid]["title"], "note": REJ_NOTE.get(rid, "Still rejected; the design's section 9 says so and this round agrees.")} for rid in sorted(r1_rejected)]
rejected_prior += [{"id": rid, "round": "2", "title": r2_rejected[rid]["title"], "note": REJ_NOTE.get(rid, "Still rejected; the design's section 9 says so and this round agrees.")} for rid in sorted(r2_rejected)]

data = {
    "title": "Typed Cache Tensors Design Review, Round 3",
    "eyebrow": "Round-3 review of the second codex revision of the design for issue #4525 (positron-ai/tron)",
    "h1": overrides.get("h1", "Did the second revision close the round-2 findings, and is the typed KV-cache tensor design implementable now?"),
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
    "r1_resolved_r2": r1_resolved_r2,
    "r1_resolved_intro": overrides.get("r1_resolved_intro", "Round 2 graded these 35 round-1 findings resolved. This round did not re-grade them; the rows are kept so that the design's [F..] and [C..] links keep working."),
    "rejected_prior_intro": overrides.get("rejected_prior_intro", "Round 1 rejected ten candidates and round 2 rejected six. The design's section 9 keeps them rejected, and this round agrees."),
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
print("wrote findings.json:", len(dispositions), "dispositions", scounts, "| new confirmed", len(confirmed), counts, "| rejected", len(rejected), "| judges", len(judges))
