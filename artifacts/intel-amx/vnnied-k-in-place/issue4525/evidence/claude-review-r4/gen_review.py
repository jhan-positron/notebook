#!/usr/bin/env python3
"""Render the ROUND-4 review page status/claude-review-design-new-tensor-type.html
from findings.json (built by build_findings.py from the workflow result).

Pure-ASCII output (numeric entities for every non-ASCII glyph). Light theme only.
Run: python3 gen_review.py
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISSUE_DIR = HERE.parents[1]
OUT = ISSUE_DIR / "status" / "claude-review-design-new-tensor-type.html"
VOTES_NAME = "claude-review-design-new-tensor-type-votes.html"
R1_NAME = "claude-review-design-new-tensor-type-r1.html"
R1_VOTES_NAME = "claude-review-design-new-tensor-type-r1-votes.html"
R2_NAME = "claude-review-design-new-tensor-type-r2.html"
R2_VOTES_NAME = "claude-review-design-new-tensor-type-r2-votes.html"
R3_NAME = "claude-review-design-new-tensor-type-r3.html"
R3_VOTES_NAME = "claude-review-design-new-tensor-type-r3-votes.html"
DESIGN = ISSUE_DIR / "status" / "design-new-tensor-type.html"
DATA = json.loads((HERE / "findings.json").read_text())

SEV_ORDER = ["blocker", "major", "minor", "note"]
SEV_LABEL = {"blocker": "Blocker", "major": "Major", "minor": "Minor", "note": "Note"}
SEV_MEANING = {
    "blocker": "the implementing agent would build the wrong thing, or the parent PR could not merge",
    "major": "the design text must change before implementation starts",
    "minor": "the design text should change; low risk if it does not",
    "note": "worth knowing; no change required",
}
ST_ORDER = ["resolved", "partly", "deferred", "unresolved", "regressed"]
ST_LABEL = {"resolved": "Resolved", "partly": "Partly", "deferred": "Deferred", "unresolved": "Unresolved", "regressed": "Regressed"}
ST_CLASS = {"resolved": "ok", "partly": "warn", "deferred": "note", "unresolved": "blocker", "regressed": "blocker"}
ST_MEANING = {
    "resolved": "the revised text meets the corrected recommendation (or the round-3 residual) in substance, and every checkable fact in the fix is right",
    "partly": "the substance is there, but a concrete part of the recommendation is missing or a small slip remains",
    "deferred": "the design explicitly leaves it to separate work; the remark says whether that is acceptable",
    "unresolved": "not addressed, or addressed only in the section 9 table",
    "regressed": "the fix introduced a new error or a contradiction",
}


def esc(s):
    return html.escape(str(s), quote=True)


def para(s):
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(((?:https?://[^)\s]+)|(?:(?:\.\./|\./)?[\w./-]+\.(?:html|json|md|py)(?:#[\w-]+)?))\)", r'<a href="\2">\1</a>', s)
    return s


def to_ascii(text):
    return "".join(ch if ord(ch) < 128 else "&#%d;" % ord(ch) for ch in text)


CSS = """
:root{--bg:#f6f7f5;--panel:#ffffff;--ink:#1d2422;--muted:#5a6663;--line:#d4dad6;--accent:#22587f;--accent-bg:#e6eef5;
--blocker:#9a2b2b;--blocker-bg:#f9e8e8;--major:#9c6410;--major-bg:#fbefd9;--minor:#2c6b5c;--minor-bg:#e3f1ec;--note:#4d5966;--note-bg:#e9ecef;
--ok:#2c6b5c;--ok-bg:#e3f1ec;--warn:#9c6410;--warn-bg:#fbefd9;--code-bg:#eef1ee}
html,body{background:var(--bg);color:var(--ink)}
body{margin:0;font:15px/1.55 "IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:960px;margin:0 auto;padding-block:28px 72px;padding-inline:20px}
h1,h2,h3{text-wrap:balance;line-height:1.2}
h1{font-size:30px;font-weight:600;margin:6px 0 4px}
h2{font-size:21px;font-weight:600;margin:44px 0 12px;padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:16.5px;font-weight:600;margin:26px 0 8px}
p{margin:0 0 12px;max-width:74ch}
ul,ol{margin:0 0 14px;padding-left:22px;max-width:76ch}
li{margin:0 0 6px}
code,pre{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:0.92em}
code{background:var(--code-bg);padding:1px 5px;border-radius:3px}
pre{background:var(--code-bg);padding:12px 14px;border-radius:6px;overflow-x:auto;line-height:1.45}
a{color:var(--accent)}
.eyebrow{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);font-weight:600}
.meta{color:var(--muted);font-size:14px;margin-bottom:22px}
.short{background:var(--panel);border:1px solid var(--line);border-left:4px solid var(--accent);padding:16px 18px;border-radius:6px;margin:18px 0 22px}
.short p{margin:0 0 8px}
.short p:last-child{margin:0}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:12px;margin:0 0 26px}
.tile{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px 14px}
.tile .k{font-size:12px;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);font-weight:600}
.tile .v{font-size:19px;font-weight:600;margin-top:4px;line-height:1.25}
.tile .s{font-size:13px;color:var(--muted);margin-top:4px}
.badge{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:999px;vertical-align:middle;white-space:nowrap}
.b-blocker{background:var(--blocker-bg);color:var(--blocker)}
.b-major{background:var(--major-bg);color:var(--major)}
.b-minor{background:var(--minor-bg);color:var(--minor)}
.b-note{background:var(--note-bg);color:var(--note)}
.b-ok{background:var(--ok-bg);color:var(--ok)}
.b-warn{background:var(--warn-bg);color:var(--warn)}
.tablewrap{overflow-x:auto;margin:0 0 16px}
table{border-collapse:collapse;width:100%;font-size:14px;font-variant-numeric:tabular-nums}
th,td{border:1px solid var(--line);padding:7px 9px;text-align:left;vertical-align:top}
th{background:var(--accent-bg);font-weight:600}
td.num{text-align:right}
.finding{background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:14px 16px;margin:0 0 14px}
.finding h3{margin:0 0 8px;font-size:16px}
.finding .row{display:grid;grid-template-columns:120px 1fr;gap:6px 12px;font-size:14px}
.finding .row .l{color:var(--muted);font-weight:600}
.finding .row .l,.finding .row .r{min-width:0}
.finding blockquote{margin:0;padding:6px 10px;border-left:3px solid var(--line);color:var(--muted);font-style:italic}
.finding .lead{background:var(--accent-bg);padding:6px 10px;border-radius:4px}
figure{margin:18px 0 22px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px}
figure svg{max-width:100%;height:auto;display:block}
figcaption{font-size:13.5px;color:var(--muted);margin-top:8px;max-width:80ch}
.small{font-size:13px;color:var(--muted)}
details{margin-top:6px;font-size:13.5px}
details summary{cursor:pointer;color:var(--accent);font-weight:600}
dl.words{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;max-width:100%}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
.bar{display:flex;height:22px;border-radius:4px;overflow:hidden;border:1px solid var(--line);margin:6px 0 4px;max-width:760px}
.bar span{display:block;height:100%;font-size:12px;line-height:22px;color:#fff;text-align:center;white-space:nowrap;overflow:hidden}
.legend{font-size:13px;color:var(--muted);margin-bottom:14px}
@media (max-width:560px){.finding .row{grid-template-columns:1fr}dl.words{grid-template-columns:1fr}dl.words dd{margin-bottom:8px}}
"""

VOTES_OUT = []


def render_words(words):
    out = ['<dl class="words">']
    for term, meaning in words:
        out.append("<dt>%s</dt><dd>%s</dd>" % (para(term), para(meaning)))
    out.append("</dl>")
    return "\n".join(out)


def status_bar(counts, total):
    colors = {"resolved": "#2c6b5c", "partly": "#9c6410", "deferred": "#4d5966", "unresolved": "#9a2b2b", "regressed": "#6b1f1f"}
    segs = []
    for st in ST_ORDER:
        n = counts.get(st, 0)
        if not n:
            continue
        pct = 100.0 * n / total
        label = "%s %d" % (ST_LABEL[st], n) if pct >= 9 else str(n)
        segs.append('<span style="width:%.1f%%;background:%s" title="%s: %d of %d">%s</span>' % (pct, colors[st], ST_LABEL[st], n, total, label))
    legend = " &middot; ".join("%s = %s" % (ST_LABEL[st], ST_MEANING[st]) for st in ST_ORDER if counts.get(st))
    return '<div class="bar">%s</div><div class="legend">%s</div>' % ("".join(segs), legend)


PAGE_OF = {"round 1": R1_NAME, "round 2": R2_NAME, "round 3": R3_NAME}


def prior_link(d):
    return PAGE_OF[d["origin"]] + "#" + d["id"]


def prior_cell(d):
    hist = "; ".join('<a href="%s#%s">%s after %s</a>' % (PAGE_OF[rnd], esc(d["id"]), ST_LABEL.get(st, st), rnd) for rnd, st in d.get("history", []))
    return '<span class="badge b-%s">%s</span><br><span class="small">%s%s</span>' % (
        d["prior_severity"], SEV_LABEL[d["prior_severity"]], esc(d["origin"]), ("; " + hist) if hist else "")


def render_dispositions(dispos):
    rows = []
    for d in dispos:
        st = d["final_status"]
        votes = d.get("votes", [])
        vtxt = ", ".join("%s: %s" % (v["lens"], ST_LABEL.get(v["status"], v["status"])) for v in votes)
        flag = ""
        if d.get("split"):
            flag = ' <span class="badge b-warn">split vote</span>'
        elif not d.get("unanimous", True):
            flag = ' <span class="small">(majority)</span>'
        if d.get("lead_restatus"):
            flag += ' <span class="small">(lead)</span>'
        remark = d.get("remark") or d.get("assessment", "")
        residual = d.get("residual", "")
        cell = para(remark)
        if residual and st != "resolved":
            cell += '<br><strong>Still needed:</strong> %s' % para(residual)
        VOTES_OUT.append('<section id="dispo-%s"><h3><span class="badge b-%s">%s</span> %s. %s (%s, grade %s)</h3><p class="small">Checker status: %s. Re-graders: %s.</p><p><strong>Design text checked:</strong> %s</p><p><strong>Checker assessment:</strong> %s</p>%s%s%s<p class="small"><a href="claude-review-design-new-tensor-type.html#%s">Back to the disposition row</a></p></section>' % (
            esc(d["id"]), ST_CLASS[st], ST_LABEL[st], esc(d["id"]), esc(d["prior_title"]), esc(d["origin"]), SEV_LABEL[d["prior_severity"]], ST_LABEL.get(d["status"], d["status"]), esc(vtxt),
            para(d.get("design_evidence", "")), para(d.get("assessment", "")),
            ('<p><strong>Still needed:</strong> %s</p>' % para(residual)) if residual else "",
            ('<p><strong>New defect raised by the checker (%s):</strong> %s</p>' % (esc(d.get("new_defect_severity", "")), para(d.get("new_defect", "")))) if d.get("new_defect") and d.get("new_defect_severity", "none") != "none" else "",
            "".join('<p><strong>%s re-grader (%s):</strong> %s%s</p>' % (esc(v["lens"]), ST_LABEL.get(v["status"], v["status"]), para(v.get("reason", "")), (" <em>Correction:</em> " + para(v["correction"])) if v.get("correction") else "") for v in votes),
            esc(d["id"])))
        cell += ' <span class="small">(<a href="%s#dispo-%s">votes and evidence</a>)</span>' % (VOTES_NAME, esc(d["id"]))
        rows.append('<tr id="%s"><td><a href="%s">%s</a></td><td>%s</td><td>%s</td><td><span class="badge b-%s">%s</span>%s</td><td>%s</td></tr>' % (
            esc(d["id"]), prior_link(d), esc(d["id"]), prior_cell(d), esc(d["prior_title"]), ST_CLASS[st], ST_LABEL[st], flag, cell))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Origin and grade</th><th>Finding</th><th>Status now</th><th>What the revision did, and what is still needed</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def render_r1_resolved(items):
    rows = []
    for r in items:
        rows.append('<tr id="%s"><td><a href="%s#%s">%s</a></td><td><span class="badge b-%s">%s</span></td><td>%s</td><td><a href="%s#%s">resolved in round 2</a></td></tr>' % (
            esc(r["id"]), R1_NAME, esc(r["id"]), esc(r["id"]), r["severity"], SEV_LABEL[r["severity"]], esc(r["title"]), R2_NAME, esc(r["id"])))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Round-1 grade</th><th>Round-1 finding</th><th>Status</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def render_r3_resolved(items):
    rows = []
    for r in items:
        page = PAGE_OF[r["origin"]]
        rows.append('<tr id="%s"><td><a href="%s#%s">%s</a></td><td><span class="badge b-%s">%s</span><br><span class="small">%s</span></td><td>%s</td><td><a href="%s#%s">resolved in round 3</a></td></tr>' % (
            esc(r["id"]), page, esc(r["id"]), esc(r["id"]), r["severity"], SEV_LABEL[r["severity"]], esc(r["origin"]), esc(r["title"]), R3_NAME, esc(r["id"])))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Grade and origin</th><th>Finding</th><th>Status</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def render_rejected_prior(items):
    rows = []
    for r in items:
        votes_page = {"1": R1_VOTES_NAME, "2": R2_VOTES_NAME, "3": R3_VOTES_NAME}[r["round"]]
        rows.append('<tr id="%s"><td><a href="%s#%s">%s</a></td><td>round %s</td><td>%s</td><td>%s</td></tr>' % (esc(r["id"]), votes_page, esc(r["id"]), esc(r["id"]), esc(r["round"]), esc(r["title"]), para(r["note"])))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Rejected in</th><th>Candidate</th><th>Status now</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def vote_txt_plain(votes):
    if not votes:
        return ""
    holds = sum(1 for v in votes if not v["refuted"])
    return "%d of %d verifiers could not refute it" % (holds, len(votes))


def render_finding(f):
    sev = f["severity"]
    votes = f.get("votes", [])
    corrections = [v.get("correction", "") for v in votes if v.get("correction")]
    corr = ""
    if corrections:
        corr = '<div class="l">Correction from verification</div><div class="r">%s</div>' % "<br>".join(para(c) for c in corrections)
    q = f.get("design_quote", "")
    compact = sev in ("minor", "note")
    quote_html = ""
    if q and q.lower() not in ("omission", "see evidence"):
        quote_html = '<div class="l">Design says</div><div class="r"><blockquote>%s</blockquote></div>' % esc(q)
    elif q.lower() == "omission":
        quote_html = '<div class="l">Design says</div><div class="r"><span class="small">(omission: the design does not address this)</span></div>'
    lead = ""
    if f.get("lead_note"):
        lead = '<div class="l">Lead\'s reading</div><div class="r lead">%s</div>' % para(f["lead_note"])
    rel = ""
    if f.get("relates_to"):
        rel = '<div class="l">Earlier ids</div><div class="r"><span class="small">touches %s</span></div>' % para(f["relates_to"])
    items = []
    for v in votes:
        tag = "refuted" if v["refuted"] else "holds"
        item = "<li><strong>%s lens</strong>: %s (%s confidence, severity %s). %s" % (esc(v["lens"]), tag, esc(v["confidence"]), esc(v["severity"]), para(v["reason"]))
        if v.get("correction"):
            item += "<br><em>Correction:</em> %s" % para(v["correction"])
        item += "</li>"
        items.append(item)
    VOTES_OUT.append('<section id="%s"><h3><span class="badge b-%s">%s</span> %s. %s</h3><p class="small">%s</p><ul>%s</ul><p class="small"><a href="claude-review-design-new-tensor-type.html#%s">Back to the finding</a></p></section>' % (
        esc(f["id"]), sev, SEV_LABEL[sev], esc(f["id"]), esc(f["title"]), esc(vote_txt_plain(votes)), "".join(items), esc(f["id"])))
    lenses = ", ".join(f.get("lenses", []))
    if compact:
        evidence_html = '<div class="l">Evidence</div><div class="r"><details><summary>Design quote and evidence</summary>%s<div>%s</div></details></div>' % (
            ('<blockquote>%s</blockquote>' % esc(q)) if q and q.lower() not in ("omission", "see evidence") else "", para(f["evidence"]))
        quote_html = ""
    else:
        evidence_html = '<div class="l">Evidence</div><div class="r">%s</div>' % para(f["evidence"])
    return """<div class="finding" id="%s">
<h3><span class="badge b-%s">%s</span> %s. %s</h3>
<div class="row">
<div class="l">Where</div><div class="r">%s</div>
%s
<div class="l">Claim</div><div class="r">%s</div>
%s
%s
%s
<div class="l">Recommendation</div><div class="r">%s</div>
%s
<div class="l">Found by</div><div class="r"><span class="small">%s; %s (<a href="%s#%s">votes and corrections</a>)</span></div>
</div>
</div>""" % (esc(f["id"]), sev, SEV_LABEL[sev], esc(f["id"]), esc(f["title"]), para(f["section"]), rel, para(f["claim"]),
             quote_html, evidence_html, corr, para(f["recommendation"]), lead, esc(lenses), esc(vote_txt_plain(votes)), VOTES_NAME, esc(f["id"]))


def render_summary_table(findings):
    rows = []
    for f in findings:
        rows.append('<tr><td><a href="#%s">%s</a></td><td><span class="badge b-%s">%s</span></td><td>%s</td><td>%s</td></tr>' % (
            esc(f["id"]), esc(f["id"]), f["severity"], SEV_LABEL[f["severity"]], esc(f["title"]), para(f["section"])))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Severity</th><th>Finding</th><th>Where in the design</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def render_rejected(rejected):
    if not rejected:
        return "<p>None.</p>"
    rows = []
    for f in rejected:
        items = []
        for v in f.get("votes", []):
            tag = "refuted" if v["refuted"] else "holds"
            item = "<li><strong>%s lens</strong>: %s (%s confidence, severity %s). %s" % (esc(v["lens"]), tag, esc(v["confidence"]), esc(v["severity"]), para(v["reason"]))
            if v.get("correction"):
                item += "<br><em>Correction:</em> %s" % para(v["correction"])
            item += "</li>"
            items.append(item)
        VOTES_OUT.append('<section id="%s"><h3><span class="badge b-note">Rejected</span> %s. %s</h3><p class="small">Candidate claim: %s</p><ul>%s</ul></section>' % (esc(f["id"]), esc(f["id"]), esc(f["title"]), para(f["claim"]), "".join(items)))
        ref = [v for v in f.get("votes", []) if v.get("refuted")]
        ref.sort(key=lambda v: 0 if v["lens"] == "source" else 1)
        if f.get("lead_dropped"):
            txt = "<strong>Dropped by the lead after reading the votes.</strong> " + para(f.get("lead_drop_reason", ""))
        else:
            txt = para((ref[0].get("correction") or ref[0]["reason"])[:700]) if ref else ""
        holds = sum(1 for v in f.get("votes", []) if not v["refuted"])
        rows.append('<tr><td><a href="%s#%s">%s</a></td><td>%s<br><span class="small">%d of %d verifiers could not refute it</span></td><td>%s</td></tr>' % (VOTES_NAME, esc(f["id"]), esc(f["id"]), esc(f["title"]), holds, len(f.get("votes", [])), txt))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Candidate finding</th><th>Why it was rejected (a refuting verifier&#39;s reading)</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def render_judges(judges):
    rows = []
    for j in judges:
        rows.append('<tr><td>%s</td><td><span class="badge b-%s">%s</span><br><span class="small">%s</span></td><td>%s</td><td>%s</td></tr>' % (
            esc(j["label"]), j["badge"], esc(j["verdict"]), "implementable now" if j["implementable_now"] else "not yet implementable",
            para(j["reasons"]), "<br>".join(para(x) for x in j.get("top_three_edits", []))))
    return '<div class="tablewrap"><table><thead><tr><th>Judge</th><th>Verdict</th><th>Reasons</th><th>Top three edits</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def main():
    d = DATA
    dispos = d["dispositions"]
    confirmed = sorted(d["confirmed"], key=lambda f: (SEV_ORDER.index(f["severity"]), f["id"]))
    rejected = d.get("rejected", [])
    counts = {s: sum(1 for f in confirmed if f["severity"] == s) for s in SEV_ORDER}
    scounts = {}
    for x in dispos:
        scounts[x["final_status"]] = scounts.get(x["final_status"], 0) + 1

    parts = []
    parts.append("<title>%s</title>" % esc(d["title"]))
    parts.append('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">')
    parts.append("<style>%s</style>" % CSS)
    parts.append("<main>")
    parts.append('<div class="eyebrow">%s</div>' % esc(d["eyebrow"]))
    parts.append("<h1>%s</h1>" % esc(d["h1"]))
    parts.append('<div class="meta">%s</div>' % para(d["meta"]))
    parts.append('<div class="short"><div class="eyebrow">Short version</div>')
    for p in d["short_version"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append("</div>")
    parts.append('<div class="tiles">')
    for t in d["tiles"]:
        badge = ' <span class="badge b-%s">%s</span>' % (t["badge"][0], esc(t["badge"][1])) if t.get("badge") else ""
        parts.append('<div class="tile"><div class="k">%s</div><div class="v">%s%s</div><div class="s">%s</div></div>' % (esc(t["k"]), para(t["v"]), badge, para(t["s"])))
    parts.append("</div>")

    parts.append("<h2>1. Words used here</h2>")
    parts.append(render_words(d["words"]))

    parts.append("<h2>2. What changed between the round-3 and round-4 versions of the design</h2>")
    for p in d["changes_intro"]:
        parts.append("<p>%s</p>" % para(p))
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (para(r[0]), para(r[1]), para(r[2])) for r in d["changes_rows"])
    parts.append('<div class="tablewrap"><table><thead><tr><th>Item</th><th>Round-3 version (121,774 bytes)</th><th>Round-4 version (168,971 bytes, reviewed here)</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    for p in d.get("changes_outro", []):
        parts.append("<p>%s</p>" % para(p))

    parts.append("<h2>3. Did the revision address the 79 open items?</h2>")
    for p in d["dispo_intro"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append(status_bar(scounts, len(dispos)))
    parts.append('<div class="tablewrap"><table><thead><tr><th>Status</th><th>Meaning</th><th class="num">Count</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(
        '<tr><td><span class="badge b-%s">%s</span></td><td>%s</td><td class="num">%d</td></tr>' % (ST_CLASS[s], ST_LABEL[s], esc(ST_MEANING[s]), scounts.get(s, 0)) for s in ST_ORDER if scounts.get(s)))
    ordered = sorted(dispos, key=lambda x: (ST_ORDER.index(x["final_status"]) * -1, SEV_ORDER.index(x["prior_severity"]), x["id"]))
    parts.append("<h3>Findings that still need work, first</h3>")
    parts.append(render_dispositions([x for x in ordered if x["final_status"] != "resolved"]))
    parts.append("<h3>Findings the revision resolved</h3>")
    parts.append(render_dispositions([x for x in ordered if x["final_status"] == "resolved"]))
    for p in d.get("dispo_outro", []):
        parts.append("<p>%s</p>" % para(p))
    parts.append("<h3>Items that round 3 already resolved</h3>")
    parts.append("<p>%s</p>" % para(d["r3_resolved_intro"]))
    parts.append(render_r3_resolved(d["r3_resolved"]))
    parts.append("<h3>Round-1 findings that round 2 already resolved</h3>")
    parts.append("<p>%s</p>" % para(d["r1_resolved_intro"]))
    parts.append(render_r1_resolved(d["r1_resolved_r2"]))
    parts.append("<h3>Candidates rejected in rounds 1 to 3</h3>")
    parts.append("<p>%s</p>" % para(d["rejected_prior_intro"]))
    parts.append(render_rejected_prior(d["rejected_prior"]))

    parts.append("<h2>4. New findings on this revision</h2>")
    parts.append("<p>%s</p>" % para(d["findings_intro"]))
    parts.append('<div class="tablewrap"><table><thead><tr><th>Severity</th><th>Meaning</th><th class="num">Count</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(
        '<tr><td><span class="badge b-%s">%s</span></td><td>%s</td><td class="num">%d</td></tr>' % (s, SEV_LABEL[s], esc(SEV_MEANING[s]), counts[s]) for s in SEV_ORDER))
    parts.append(render_summary_table(confirmed))
    if d.get("figure_html"):
        parts.append(d["figure_html"])
    parts.append("<h3>Findings in full</h3>")
    for f in confirmed:
        parts.append(render_finding(f))

    parts.append("<h2>5. The decision record: Q1 to Q4 and D5</h2>")
    for p in d["questions_intro"]:
        parts.append("<p>%s</p>" % para(p))
    rows = "".join("<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (para(r[0]), para(r[1]), para(r[2])) for r in d["questions_rows"])
    parts.append('<div class="tablewrap"><table><thead><tr><th>Question or decision, and the proposed choice</th><th>Covers</th><th>Assessment this round</th></tr></thead><tbody>%s</tbody></table></div>' % rows)
    for p in d.get("questions_outro", []):
        parts.append("<p>%s</p>" % para(p))

    parts.append("<h2>6. What the revision gets right</h2>")
    parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % para(b) for b in d["strengths"]))

    parts.append("<h2>7. Recommended edits, in the order to make them</h2>")
    parts.append("<ol>%s</ol>" % "".join("<li>%s</li>" % para(b) for b in d["edits"]))

    parts.append("<h2>8. Verdict</h2>")
    for p in d["verdict_intro"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append(render_judges(d["judges"]))
    for p in d.get("verdict_outro", []):
        parts.append("<p>%s</p>" % para(p))

    parts.append("<h2>9. Candidate findings that did not survive verification</h2>")
    parts.append("<p>%s</p>" % para(d["rejected_intro"]))
    parts.append(render_rejected(rejected))

    parts.append("<h2>10. Method, evidence, and limits</h2>")
    for p in d["method"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % para(b) for b in d["method_bullets"]))
    parts.append("</main>")

    page = to_ascii("\n".join(parts))
    assert all(ord(c) < 128 for c in page), "non-ASCII slipped through"
    # every id the design links on the LIVE review page must have an anchor here
    design_html = DESIGN.read_text(encoding="utf-8")
    wanted = set(re.findall(r'href="claude-review-design-new-tensor-type\.html#([^"]+)"', design_html))
    have = set(re.findall(r' id="([^"]+)"', page))
    missing_anchors = sorted(wanted - have)
    assert not missing_anchors, "design links without an anchor on the new page: %s" % missing_anchors
    print("design links into the live page:", len(wanted), "all resolve")
    OUT.write_text(page)
    votes_page = to_ascii("\n".join([
        "<title>Design Review Votes, Round 4</title>",
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">',
        "<style>%s</style>" % CSS,
        "<main>",
        '<div class="eyebrow">Companion to the round-4 design review of issue #4525</div>',
        "<h1>Verification votes and corrections, round 4</h1>",
        '<p class="meta">Every new finding on the <a href="claude-review-design-new-tensor-type.html">round-4 review page</a> was put to three verifiers who tried to refute it (a source-truth lens, a design-text-fairness lens, an intent lens). This page holds their reasons and corrections verbatim. A finding survived when at least two of the three could not refute it. Rejected candidates are listed at the end. The disposition rows of section 3 (one checker plus two re-graders per known item) are here too, under dispo-G.., dispo-H.., dispo-N.., dispo-M.., dispo-F.. and dispo-C.. anchors. The round-1 votes are on <a href="%s">their own page</a>, the round-2 votes on <a href="%s">theirs</a> and the round-3 votes on <a href="%s">theirs</a>.</p>' % (R1_VOTES_NAME, R2_VOTES_NAME, R3_VOTES_NAME),
        "\n".join(VOTES_OUT),
        "</main>",
    ]))
    assert all(ord(c) < 128 for c in votes_page)
    (OUT.parent / VOTES_NAME).write_text(votes_page)
    print("wrote", OUT, len(page.encode()), "bytes; confirmed", len(confirmed), "rejected", len(rejected), counts, "dispositions", scounts)
    print("wrote", OUT.parent / VOTES_NAME, len(votes_page.encode()), "bytes")


if __name__ == "__main__":
    main()
