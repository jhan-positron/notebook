#!/usr/bin/env python3
"""Render status/claude-review-design-new-tensor-type.html from findings.json.

Pure-ASCII output (numeric entities for every non-ASCII glyph). Light theme only,
per the user's HTML rule. Run: python3 gen_review.py
"""
import html
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISSUE_DIR = HERE.parents[1]
OUT = ISSUE_DIR / "status" / "claude-review-design-new-tensor-type.html"
DATA = json.loads((HERE / "findings.json").read_text())

SEV_ORDER = ["blocker", "major", "minor", "note"]
SEV_LABEL = {"blocker": "Blocker", "major": "Major", "minor": "Minor", "note": "Note"}
SEV_MEANING = {
    "blocker": "the implementing agent would build the wrong thing, or the parent PR could not merge",
    "major": "the design text must change before implementation starts",
    "minor": "the design text should change; low risk if it does not",
    "note": "worth knowing; no change required",
}


def esc(s):
    return html.escape(s, quote=True)


def para(s):
    """Markdown-lite: **bold**, `code`, [text](url). Escapes everything else."""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\[([^\]]+)\]\(((?:https?://[^)\s]+)|(?:(?:\.\./|\./)?[\w./-]+\.(?:html|json|md|py)))\)", r'<a href="\2">\1</a>', s)
    return s


def to_ascii(text):
    return "".join(ch if ord(ch) < 128 else "&#%d;" % ord(ch) for ch in text)


CSS = """
:root{--bg:#f6f7f5;--panel:#ffffff;--ink:#1d2422;--muted:#5a6663;--line:#d4dad6;--accent:#22587f;--accent-bg:#e6eef5;
--blocker:#9a2b2b;--blocker-bg:#f9e8e8;--major:#9c6410;--major-bg:#fbefd9;--minor:#2c6b5c;--minor-bg:#e3f1ec;--note:#4d5966;--note-bg:#e9ecef;
--ok:#2c6b5c;--ok-bg:#e3f1ec;--warn:#9c6410;--warn-bg:#fbefd9;--code-bg:#eef1ee}
html,body{background:var(--bg);color:var(--ink)}
body{margin:0;font:15px/1.55 "IBM Plex Sans",-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:920px;margin:0 auto;padding-block:28px 72px;padding-inline:20px}
h1,h2,h3{font-family:"IBM Plex Sans",-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;text-wrap:balance;line-height:1.2}
h1{font-size:30px;font-weight:600;margin:6px 0 4px}
h2{font-size:21px;font-weight:600;margin:44px 0 12px;padding-top:14px;border-top:1px solid var(--line)}
h3{font-size:16.5px;font-weight:600;margin:26px 0 8px}
p{margin:0 0 12px;max-width:72ch}
ul,ol{margin:0 0 14px;padding-left:22px;max-width:74ch}
li{margin:0 0 6px}
code,pre{font-family:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:0.92em}
code{background:var(--code-bg);padding:1px 5px;border-radius:3px}
pre{background:var(--code-bg);padding:12px 14px;border-radius:6px;overflow-x:auto;line-height:1.45}
pre code{background:none;padding:0}
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
.finding .votes{font-size:12.5px;color:var(--muted);margin-top:8px}
figure{margin:18px 0 22px;background:var(--panel);border:1px solid var(--line);border-radius:6px;padding:12px}
figure svg{max-width:100%;height:auto;display:block}
figcaption{font-size:13.5px;color:var(--muted);margin-top:8px;max-width:80ch}
.small{font-size:13px;color:var(--muted)}
.finding .lead{background:var(--accent-bg);padding:6px 10px;border-radius:4px}
details{margin-top:10px;font-size:13.5px}
details summary{cursor:pointer;color:var(--accent);font-weight:600}
details ul{margin-top:8px}
details li{margin-bottom:8px}
dl.words{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;max-width:100%}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
@media (max-width:560px){.finding .row{grid-template-columns:1fr}dl.words{grid-template-columns:1fr}dl.words dd{margin-bottom:8px}}
"""

# ---------------------------------------------------------------- diagrams
DIAGRAM_LAYERS = """
<figure>
<svg viewBox="0 0 940 330" role="img" aria-label="Ben's straw-man has three parts: layout, storage, view. Ben's own reservation and the codex design fold the layout into the view, leaving storage and view. The cost is one view type per layout instead of one template.">
<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker></defs>
<g font-family="IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif" font-size="12.5" fill="currentColor">
<text x="14" y="24" font-weight="600" font-size="13.5">A. Ben's straw-man (PR 4424 conversation comment, 18:58 UTC)</text>
<rect x="14" y="40" width="250" height="78" rx="5" fill="#fbefd9" stroke="#9c6410"/>
<text x="26" y="60" font-weight="600">layout struct</text>
<text x="26" y="78">k_vnni_layout / v_vnni_layout</text>
<text x="26" y="96">static offset(token, dim)</text>
<rect x="330" y="40" width="250" height="78" rx="5" fill="#ffffff" stroke="currentColor"/>
<text x="342" y="60" font-weight="600">storage (owner)</text>
<text x="342" y="78">vnni_tensor&lt;Layout&gt;</text>
<text x="342" y="96">alignas(64) array of bf16</text>
<rect x="646" y="40" width="280" height="78" rx="5" fill="#ffffff" stroke="currentColor"/>
<text x="658" y="60" font-weight="600">view (typed access)</text>
<text x="658" y="78">vnni_view&lt;T, Layout&gt;</text>
<text x="658" y="96">at(token, dim) = data[Layout::offset]</text>
<line x1="264" y1="79" x2="330" y2="79" stroke="currentColor" marker-end="url(#arr)"/>
<text x="297" y="70" text-anchor="middle" font-size="11">names</text>
<line x1="580" y1="79" x2="646" y2="79" stroke="currentColor" marker-end="url(#arr)"/>
<text x="613" y="70" text-anchor="middle" font-size="11">as_view()</text>
<path d="M 139 118 C 139 160, 786 160, 786 118" fill="none" stroke="#9c6410" stroke-dasharray="5 4" marker-end="url(#arr)"/>
<text x="470" y="150" text-anchor="middle" font-size="11" fill="#9c6410">view computes addresses by calling Layout::offset()</text>

<text x="14" y="204" font-weight="600" font-size="13.5">B. Ben's reservation, jhan's reading, and the codex design: fold the layout into the view</text>
<rect x="330" y="220" width="250" height="78" rx="5" fill="#ffffff" stroke="currentColor"/>
<text x="342" y="240" font-weight="600">storage (owner)</text>
<text x="342" y="258">vnni_tensor&lt;R, D&gt;</text>
<text x="342" y="276">array inside kv_block, no allocation</text>
<rect x="646" y="220" width="280" height="78" rx="5" fill="#e6eef5" stroke="#22587f" stroke-width="1.5"/>
<text x="658" y="240" font-weight="600" fill="#22587f">view = layout + access</text>
<text x="658" y="258">vnni_view&lt;T, R, D&gt; holds the V formula</text>
<text x="658" y="276">k_vnni_view&lt;T, R, D&gt; holds the K formula</text>
<line x1="580" y1="259" x2="646" y2="259" stroke="currentColor" marker-end="url(#arr)"/>
<text x="613" y="250" text-anchor="middle" font-size="11">as_view()</text>
<rect x="14" y="220" width="250" height="78" rx="5" fill="none" stroke="#9c6410" stroke-dasharray="5 4"/>
<text x="26" y="244" fill="#9c6410">layout struct removed</text>
<text x="26" y="262" fill="#9c6410">cost: one view type per layout</text>
<text x="26" y="280" fill="#9c6410">instead of one template over Layout</text>
</g>
</svg>
<figcaption>The straw-man (A) has three parts. Ben's reservation ("not entirely convinced of the necessity of separate k_vnni_layout from vnni_view") and jhan's reading both remove the left box, which is what the codex design does (B). Storage stays a separate owner in both. The price of B is that the K and V views repeat the owner, row and access boilerplate instead of sharing one template.</figcaption>
</figure>
"""

DIAGRAM_PARTNER = """
<figure>
<svg viewBox="0 0 940 300" role="img" aria-label="Today the model's even-token V write zeroes the odd partner row, and the weighted sum reads that zero when the token count is odd. In the design, ordinary row assignment preserves the partner, so if the model save path uses ordinary assignment, a stale value from an earlier use of the page survives in the padding row and the weighted sum reads it.">
<defs><marker id="arr2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse"><path d="M0 0 L10 5 L0 10 z" fill="currentColor"/></marker></defs>
<g font-family="IBM Plex Sans, Segoe UI, Helvetica, Arial, sans-serif" font-size="12.5" fill="currentColor">
<text x="14" y="22" font-weight="600" font-size="13.5">One V pair (tokens 2p, 2p+1) of a page that is being reused. count = 2p+1 (odd), so the weighted sum reads both rows of the pair.</text>

<text x="14" y="62" font-weight="600">Today (main)</text>
<rect x="150" y="44" width="180" height="46" rx="4" fill="#ffffff" stroke="currentColor"/>
<text x="160" y="62">before save: [stale_a, stale_b]</text>
<text x="160" y="80" font-size="11" fill="#5a6663">left over from an earlier token</text>
<line x1="330" y1="67" x2="392" y2="67" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="361" y="58" text-anchor="middle" font-size="11">set_v(even)</text>
<rect x="392" y="44" width="180" height="46" rx="4" fill="#e3f1ec" stroke="#2c6b5c"/>
<text x="402" y="62">[a, 0]</text>
<text x="402" y="80" font-size="11" fill="#2c6b5c">cvtepu16_epi32 zero-extends: partner = 0</text>
<line x1="572" y1="67" x2="634" y2="67" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="603" y="58" text-anchor="middle" font-size="11">scaled_v</text>
<rect x="634" y="44" width="290" height="46" rx="4" fill="#ffffff" stroke="currentColor"/>
<text x="644" y="62">sum += w_even * a + 0 * 0</text>
<text x="644" y="80" font-size="11" fill="#5a6663">padding contributes exactly 0</text>

<text x="14" y="152" font-weight="600">Design, if save_v uses</text>
<text x="14" y="168" font-weight="600">ordinary row assignment</text>
<rect x="150" y="134" width="180" height="46" rx="4" fill="#ffffff" stroke="currentColor"/>
<text x="160" y="152">before save: [stale_a, stale_b]</text>
<text x="160" y="170" font-size="11" fill="#5a6663">same reused page</text>
<line x1="330" y1="157" x2="392" y2="157" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="361" y="148" text-anchor="middle" font-size="11">row[2p].set(x)</text>
<rect x="392" y="134" width="180" height="46" rx="4" fill="#f9e8e8" stroke="#9a2b2b"/>
<text x="402" y="152">[a, stale_b]</text>
<text x="402" y="170" font-size="11" fill="#9a2b2b">"preserve the other row in the pair"</text>
<line x1="572" y1="157" x2="634" y2="157" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="603" y="148" text-anchor="middle" font-size="11">scaled_v</text>
<rect x="634" y="134" width="290" height="46" rx="4" fill="#f9e8e8" stroke="#9a2b2b"/>
<text x="644" y="152">sum += w_even * a + 0 * stale_b</text>
<text x="644" y="170" font-size="11" fill="#9a2b2b">if stale_b is NaN, the sum is NaN (NaN * 0 = NaN)</text>

<text x="14" y="242" font-weight="600">Design, if save_v uses</text>
<text x="14" y="258" font-weight="600">append_v_row / set_pair</text>
<rect x="150" y="224" width="180" height="46" rx="4" fill="#ffffff" stroke="currentColor"/>
<text x="160" y="242">before save: [stale_a, stale_b]</text>
<line x1="330" y1="247" x2="392" y2="247" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="361" y="238" text-anchor="middle" font-size="11">append_v_row(even)</text>
<rect x="392" y="224" width="180" height="46" rx="4" fill="#e3f1ec" stroke="#2c6b5c"/>
<text x="402" y="242">[a, 0]</text>
<text x="402" y="260" font-size="11" fill="#2c6b5c">"adds an even token and zeros the odd row"</text>
<line x1="572" y1="247" x2="634" y2="247" stroke="currentColor" marker-end="url(#arr2)"/>
<text x="603" y="238" text-anchor="middle" font-size="11">scaled_v</text>
<rect x="634" y="224" width="290" height="46" rx="4" fill="#ffffff" stroke="currentColor"/>
<text x="644" y="242">sum += w_even * a + 0 * 0</text>
<text x="644" y="260" font-size="11" fill="#5a6663">same result as today</text>
</g>
</svg>
<figcaption>The Zero-Initialized V Slots invariant (kv_cache.hpp Note, main f46e48ba) holds because every even-token write zeroes its odd partner. The design gives ordinary row assignment the opposite rule and does not name which operation the model's save path (save_v_impl in model.hpp) must call. Only the third lane is safe. Interleaving is schematic; no durations are shown.</figcaption>
</figure>
"""


VOTES_OUT = []
VOTES_NAME = "claude-review-design-new-tensor-type-votes.html"


def render_words(words):
    out = ['<dl class="words">']
    for term, meaning in words:
        out.append("<dt>%s</dt><dd>%s</dd>" % (para(term), para(meaning)))
    out.append("</dl>")
    return "\n".join(out)


def render_finding(f, idx):
    sev = f["severity"]
    votes = f.get("votes", [])
    vote_txt = ""
    if votes:
        parts = []
        for v in votes:
            parts.append("%s: %s (%s)" % (v["lens"], "refuted" if v["refuted"] else "holds", v["confidence"]))
        vote_txt = '<div class="votes">Verification votes: %s.</div>' % esc("; ".join(parts))
    corr = ""
    corrections = [v.get("correction", "") for v in votes if v.get("correction")]
    if corrections:
        corr = '<div class="l">Correction from verification</div><div class="r">%s</div>' % "<br>".join(para(c) for c in corrections)
    q = f.get("design_quote", "")
    compact = sev in ("minor", "note")
    quote_html = ""
    if q and q.lower() != "omission":
        quote_html = '<div class="l">Design says</div><div class="r"><blockquote>%s</blockquote></div>' % esc(q)
    elif q:
        quote_html = '<div class="l">Design says</div><div class="r"><span class="small">(omission: the design does not address this)</span></div>'
    lead = ""
    if f.get("lead_note"):
        lead = '<div class="l">Lead\'s reading</div><div class="r lead">%s</div>' % para(f["lead_note"])
    details = ""
    if votes:
        items = []
        for v in votes:
            tag = "refuted" if v["refuted"] else "holds"
            item = "<li><strong>%s lens</strong>: %s (%s confidence, severity %s). %s" % (esc(v["lens"]), tag, esc(v["confidence"]), esc(v["severity"]), para(v["reason"]))
            if v.get("correction"):
                item += "<br><em>Correction:</em> %s" % para(v["correction"])
            item += "</li>"
            items.append(item)
        details = ""
        VOTES_OUT.append('<section id="%s"><h3><span class="badge b-%s">%s</span> %s. %s</h3><p class="small">%s</p><ul>%s</ul><p class="small"><a href="claude-review-design-new-tensor-type.html#%s">Back to the finding</a></p></section>' % (esc(f["id"]), sev, SEV_LABEL[sev], esc(f["id"]), esc(f["title"]), esc(vote_txt_plain(votes)), "".join(items), esc(f["id"])))
    lenses = ", ".join(f.get("lenses", []))
    return """<div class="finding" id="%s">
<h3><span class="badge b-%s">%s</span> %s. %s</h3>
<div class="row">
<div class="l">Where</div><div class="r">%s</div>
<div class="l">Claim</div><div class="r">%s</div>
%s
%s
<div class="l">Recommendation</div><div class="r">%s</div>
%s
<div class="l">Found by</div><div class="r"><span class="small">%s; %s (<a href="%s#%s">votes and corrections</a>)</span></div>
</div>
%s
</div>""" % (
        esc(f["id"]), sev, SEV_LABEL[sev], esc(f["id"]), esc(f["title"]),
        para(f["section"]), para(f["claim"]), "" if compact else quote_html,
        ('<div class="l">Evidence</div><div class="r"><details><summary>Design quote and evidence</summary>%s<div>%s</div></details></div>' % (('<blockquote>%s</blockquote>' % esc(q)) if q and q.lower() != "omission" else "", para(f["evidence"]))) if compact else ('<div class="l">Evidence</div><div class="r">%s</div>' % para(f["evidence"])),
        para(f["recommendation"]), lead, esc(lenses), esc(vote_txt_plain(votes)), VOTES_NAME, esc(f["id"]), details,
    )


def vote_txt_plain(votes):
    if not votes:
        return ""
    holds = sum(1 for v in votes if not v["refuted"])
    return "%d of %d verifiers could not refute it" % (holds, len(votes))


def render_summary_table(findings):
    rows = []
    for f in findings:
        rows.append("<tr><td><a href=\"#%s\">%s</a></td><td><span class=\"badge b-%s\">%s</span></td><td>%s</td><td>%s</td></tr>" % (
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
        txt = ""
        if ref:
            v = ref[0]
            txt = para((v.get("correction") or v["reason"])[:700])
        holds = sum(1 for v in f.get("votes", []) if not v["refuted"])
        rows.append("<tr><td><a href=\"%s#%s\">%s</a></td><td>%s<br><span class=\"small\">%d of %d verifiers could not refute it</span></td><td>%s</td></tr>" % (VOTES_NAME, esc(f["id"]), esc(f["id"]), esc(f["title"]), holds, len(f.get("votes", [])), txt))
    return '<div class="tablewrap"><table><thead><tr><th>Id</th><th>Candidate finding</th><th>Why it was rejected (a refuting verifier&#39;s corrected reading)</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows)


def main():
    d = DATA
    confirmed = sorted(d["confirmed"], key=lambda f: (SEV_ORDER.index(f["severity"]), f["id"]))
    rejected = d.get("rejected", [])
    counts = {s: sum(1 for f in confirmed if f["severity"] == s) for s in SEV_ORDER}

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
        badge = ''
        if t.get("badge"):
            badge = ' <span class="badge b-%s">%s</span>' % (t["badge"][0], esc(t["badge"][1]))
        parts.append('<div class="tile"><div class="k">%s</div><div class="v">%s%s</div><div class="s">%s</div></div>' % (esc(t["k"]), para(t["v"]), badge, para(t["s"])))
    parts.append("</div>")

    parts.append("<h2>1. Words used here</h2>")
    parts.append(render_words(d["words"]))

    parts.append("<h2>2. Does issue #4525 capture the request?</h2>")
    for p in d["issue_intro"]:
        parts.append("<p>%s</p>" % para(p))
    rows = []
    for r in d["issue_rows"]:
        rows.append("<tr><td>%s</td><td>%s</td><td><span class=\"badge b-%s\">%s</span></td><td>%s</td></tr>" % (para(r[0]), para(r[1]), r[2][0], esc(r[2][1]), para(r[3])))
    parts.append('<div class="tablewrap"><table><thead><tr><th>Request</th><th>Source</th><th>In the issue?</th><th>Evidence and remark</th></tr></thead><tbody>%s</tbody></table></div>' % "\n".join(rows))
    for p in d["issue_outro"]:
        parts.append("<p>%s</p>" % para(p))

    parts.append("<h2>3. Is jhan's reading of Ben's reservation right?</h2>")
    for p in d["ben_intro"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append(DIAGRAM_LAYERS)
    for p in d["ben_outro"]:
        parts.append("<p>%s</p>" % para(p))
    if d.get("ben_bullets"):
        parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % para(b) for b in d["ben_bullets"]))

    parts.append("<h2>4. Findings on the codex design</h2>")
    parts.append("<p>%s</p>" % para(d["findings_intro"]))
    parts.append('<div class="tablewrap"><table><thead><tr><th>Severity</th><th>Meaning</th><th class="num">Count</th></tr></thead><tbody>%s</tbody></table></div>' % "".join(
        '<tr><td><span class="badge b-%s">%s</span></td><td>%s</td><td class="num">%d</td></tr>' % (s, SEV_LABEL[s], esc(SEV_MEANING[s]), counts[s]) for s in SEV_ORDER))
    parts.append(render_summary_table(confirmed))
    if d.get("show_partner_diagram"):
        parts.append("<h3>The invariant the blockers turn on</h3>")
        parts.append("<p>%s</p>" % para(d["partner_intro"]))
        parts.append(DIAGRAM_PARTNER)
    parts.append("<h3>Findings in full</h3>")
    for i, f in enumerate(confirmed):
        parts.append(render_finding(f, i))

    parts.append("<h2>5. What the design gets right</h2>")
    parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % para(b) for b in d["strengths"]))

    parts.append("<h2>6. Recommended edits, in the order to make them</h2>")
    parts.append("<ol>%s</ol>" % "".join("<li>%s</li>" % para(b) for b in d["edits"]))

    parts.append("<h2>7. Candidate findings that did not survive verification</h2>")
    parts.append("<p>%s</p>" % para(d["rejected_intro"]))
    parts.append(render_rejected(rejected))

    parts.append("<h2>8. Method, evidence, and limits</h2>")
    for p in d["method"]:
        parts.append("<p>%s</p>" % para(p))
    parts.append("<ul>%s</ul>" % "".join("<li>%s</li>" % para(b) for b in d["method_bullets"]))

    parts.append("</main>")
    page = to_ascii("\n".join(parts))
    assert all(ord(c) < 128 for c in page), "non-ASCII slipped through"
    OUT.write_text(page)
    votes_page = to_ascii("\n".join([
        "<title>Design Review Votes</title>",
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;600&family=IBM+Plex+Mono:wght@400&display=swap">',
        "<style>%s</style>" % CSS,
        "<main>",
        '<div class="eyebrow">Companion to the design review of issue #4525</div>',
        "<h1>Verification votes and corrections</h1>",
        '<p class="meta">Every finding on the <a href="claude-review-design-new-tensor-type.html">review page</a> was put to three verifiers who tried to refute it (a source-truth lens, a design-text-fairness lens, an intent lens). This page holds their reasons and corrections verbatim. A finding survived when at least two of the three could not refute it. Rejected candidates are listed at the end.</p>',
        "\n".join(VOTES_OUT),
        "</main>",
    ]))
    assert all(ord(c) < 128 for c in votes_page)
    (OUT.parent / VOTES_NAME).write_text(votes_page)
    print("wrote", OUT.parent / VOTES_NAME, len(votes_page.encode()), "bytes")
    print("wrote", OUT, len(page.encode()), "bytes;", "confirmed", len(confirmed), "rejected", len(rejected), counts)


if __name__ == "__main__":
    main()
