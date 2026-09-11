#!/usr/bin/env python3
"""Render PR3879/Bill-claude-review-response.html from data.json.

Usage: python3 gen.py [data.json] [out.html]
The data file holds the per-finding records (verified by the 2026-09-10 workflow) and
the page-level texts. This script only lays them out; it invents no facts.
"""
import html, json, sys, datetime as dt, os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "data.json")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "Bill-claude-review-response.html")

d = json.load(open(DATA, encoding="utf-8"))
E = html.escape

STATUS = {
    # key: (label, css class)
    "done":    ("Done in #3879", "s-done"),
    "partial": ("Partly done in #3879", "s-partial"),
    "agree":   ("Open in #3879, we agree", "s-open"),
    "differ":  ("Open in #3879, position differs", "s-differ"),
    "pr2":     ("Not in #3879: parked PR 2", "s-moved"),
    "pr0":     ("Not in #3879: merged as PR 0", "s-merged"),
    "moot":    ("Moot", "s-moot"),
}
SEV = {"blocker": "Blocker", "structural": "Structural", "cleanup": "Cleanup"}

def pill(key):
    label, cls = STATUS[key]
    return f'<span class="pill {cls}">{E(label)}</span>'

def para(text):
    """Split a text on blank lines into <p> elements; keep inline <code> if the text has backticks."""
    out = []
    for chunk in [c.strip() for c in text.split("\n\n") if c.strip()]:
        out.append("<p>" + inline(chunk) + "</p>")
    return "\n".join(out)

def inline(s):
    s = E(s)
    # `code` -> <code>
    parts = s.split("`")
    for i in range(1, len(parts), 2):
        parts[i] = "<code>" + parts[i] + "</code>"
    return "".join(parts)

def ul(items):
    if not items:
        return ""
    return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"

# ---------------------------------------------------------------- figures
def fig_timeline(events, t0, t1):
    """Horizontal, to scale. events: list of {t: ISO UTC, lane: 'review'|'code', label, strong?}."""
    W, H = 1000, 300
    L, R = 70, 70
    x0, x1 = L, W - R
    T0 = dt.datetime.fromisoformat(t0); T1 = dt.datetime.fromisoformat(t1)
    span = (T1 - T0).total_seconds()
    def X(t):
        return x0 + (dt.datetime.fromisoformat(t) - T0).total_seconds() / span * (x1 - x0)
    axis_y = 132
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="tl-title" xmlns="http://www.w3.org/2000/svg">',
         '<title id="tl-title">Timeline of the review and of the code it reviewed</title>',
         '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:12px;fill:#1f2933}.mu{fill:#52606d}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:11px}</style>',
         f'<line x1="{x0}" y1="{axis_y}" x2="{x1}" y2="{axis_y}" stroke="#c3c2b7" stroke-width="1"/>']
    # day ticks
    day = T0.replace(hour=0, minute=0, second=0)
    while day <= T1:
        if day >= T0:
            x = X(day.isoformat())
            s.append(f'<line x1="{x:.1f}" y1="{axis_y-4}" x2="{x:.1f}" y2="{axis_y+4}" stroke="#c3c2b7"/>')
            s.append(f'<text x="{x:.1f}" y="{axis_y+16}" text-anchor="middle" class="mu">{day.strftime("%b %d")}</text>')
        day += dt.timedelta(days=1)
    s.append(f'<text x="{x0}" y="{H-8}" text-anchor="start" class="mu">2026, UTC dates; positions to scale</text>')
    # lanes label
    s.append(f'<text x="{x0-8}" y="{axis_y-60}" text-anchor="end" class="mu">reviews</text>')
    s.append(f'<text x="{x0-8}" y="{axis_y+80}" text-anchor="end" class="mu">code</text>')
    for ev in events:
        x = X(ev["t"]); up = ev["lane"] == "review"
        lvl = ev.get("level", 0)
        y_dot = axis_y - 14 if up else axis_y + 34
        y_lab = (axis_y - 44 - 30 * lvl) if up else (axis_y + 66 + 30 * lvl)
        col = "#2b6cb0" if ev.get("strong") else "#52606d"
        y_from = axis_y if up else axis_y + 24
        s.append(f'<line x1="{x:.1f}" y1="{y_from}" x2="{x:.1f}" y2="{y_lab + (6 if up else -12)}" stroke="{col}" stroke-width="1" opacity="0.6"/>')
        s.append(f'<circle cx="{x:.1f}" cy="{y_dot}" r="{5 if ev.get("strong") else 4}" fill="{col}"/>')
        anchor = ev.get("anchor", "middle")
        s.append(f'<text x="{x:.1f}" y="{y_lab}" text-anchor="{anchor}" font-weight="{600 if ev.get("strong") else 400}">{E(ev["label"])}</text>')
        if ev.get("sub"):
            s.append(f'<text x="{x:.1f}" y="{y_lab+14}" text-anchor="{anchor}" class="mono mu">{E(ev["sub"])}</text>')
    s.append("</svg>")
    return "\n".join(s)

def fig_matrix(findings):
    """Rows = findings in Bill's order; columns = trees where the concern's code exists now."""
    cols = [("Old head", "60d66d9c04", "reviewed 09-05"), ("#3879 now", "524c510609", "approved 09-10"),
            ("PR 2", "c64b0ca102", "parked draft"), ("main", "1279137d25", "via PR 0 #4267")]
    W = 1000; rowh = 30; top = 80; sevx = 300; colx0 = 390; colw = 105; statx = 820
    H = top + rowh * len(findings) + 16
    s = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="mx-title" xmlns="http://www.w3.org/2000/svg">',
         '<title id="mx-title">Where the code behind each finding lives now</title>',
         '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;font-size:12.5px;fill:#1f2933}.mu{fill:#52606d;font-size:11px}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-size:10.5px;fill:#52606d}.st{font-size:11.5px;font-weight:600}</style>']
    for i, (h1, h2, h3) in enumerate(cols):
        cx = colx0 + colw * i + colw / 2
        s.append(f'<text x="{cx}" y="22" text-anchor="middle" font-weight="600">{E(h1)}</text>')
        s.append(f'<text x="{cx}" y="38" text-anchor="middle" class="mono">{E(h2)}</text>')
        s.append(f'<text x="{cx}" y="53" text-anchor="middle" class="mu">{E(h3)}</text>')
    s.append(f'<text x="{statx}" y="22" font-weight="600">Status</text>')
    s.append(f'<text x="{sevx}" y="22" font-weight="600" class="mu">Bill\'s rank</text>')
    s.append(f'<line x1="16" y1="{top-12}" x2="{W-16}" y2="{top-12}" stroke="#d9dee3"/>')
    colors = {"done": ("#e6f4ea", "#276749"), "partial": ("#fdf0e6", "#c05621"), "agree": ("#fde8e8", "#c53030"),
              "differ": ("#fde8e8", "#c53030"), "pr2": ("#ede9f7", "#553c9a"), "pr0": ("#e8f0fa", "#2b6cb0"), "moot": ("#eef1f4", "#52606d")}
    short = {"done": "done", "partial": "partly done", "agree": "open, agree", "differ": "open, differs",
             "pr2": "parked PR 2", "pr0": "merged, PR 0", "moot": "moot"}
    for r, f in enumerate(findings):
        y = top + rowh * r + rowh / 2
        if r % 2 == 0:
            s.append(f'<rect x="16" y="{y - rowh/2:.1f}" width="{W-32}" height="{rowh}" fill="#fbfcfd"/>')
        s.append(f'<text x="22" y="{y+4:.1f}" class="mu">{f["n"]}</text>')
        s.append(f'<text x="44" y="{y+4:.1f}">{E(f["short_title"])}</text>')
        sev = f["severity"]
        s.append(f'<text x="{sevx}" y="{y+4:.1f}" class="mu">{E(sev)}</text>')
        w = f["where"]
        for i, key in enumerate(["old", "pr1", "pr2", "main"]):
            cx = colx0 + colw * i + colw / 2
            v = w.get(key, "no")
            if v == "yes":
                s.append(f'<circle cx="{cx}" cy="{y:.1f}" r="6" fill="#2b6cb0"/>')
            elif v == "partly":
                s.append(f'<circle cx="{cx}" cy="{y:.1f}" r="6" fill="#ffffff" stroke="#2b6cb0" stroke-width="1.5"/>')
                s.append(f'<path d="M {cx} {y-6:.1f} A 6 6 0 0 1 {cx} {y+6:.1f} Z" fill="#2b6cb0"/>')
            else:
                s.append(f'<circle cx="{cx}" cy="{y:.1f}" r="3" fill="#d9dee3"/>')
        bg, fg = colors[f["status"]]
        lab = short[f["status"]]
        tw = 7 * len(lab) + 16
        s.append(f'<rect x="{statx}" y="{y-10:.1f}" width="{tw}" height="20" rx="10" fill="{bg}"/>')
        s.append(f'<text x="{statx + tw/2:.1f}" y="{y+4:.1f}" text-anchor="middle" class="st" fill="{fg}" style="fill:{fg}">{E(lab)}</text>')
    s.append("</svg>")
    return "\n".join(s)

# ---------------------------------------------------------------- page
F = d["findings"]
counts = {}
for f in F:
    counts[f["status"]] = counts.get(f["status"], 0) + 1

def board():
    order = ["done", "partial", "agree", "differ", "pr2", "pr0", "moot"]
    cards = []
    for k in order:
        if counts.get(k):
            cards.append(f'<div class="card"><div class="n">{counts[k]}</div><div class="l">{E(STATUS[k][0])}</div></div>')
    return '<div class="board">' + "".join(cards) + "</div>"

def summary_table():
    rows = []
    for f in F:
        rows.append(f'<tr><td>{f["n"]}</td><td>{E(SEV[f["severity"]])}</td><td><a href="#f{f["n"]}">{E(f["title"])}</a></td>'
                    f'<td>{E(f["verdict_old"])}</td><td>{pill(f["status"])}</td><td>{inline(f["action"])}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr><th>#</th><th>Bill\'s rank</th><th>Finding</th><th>Right on 09-05?</th><th>Status at 524c510609</th><th>Action for jhan</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table></div>")

def finding_section(f):
    parts = [f'<h2 id="f{f["n"]}">{f["n"]}. {E(f["title"])}</h2>',
             f'<p class="meta">{pill(f["status"])} &nbsp; Bill\'s rank: {E(SEV[f["severity"]])} &nbsp;|&nbsp; Right on 2026-09-05: <strong>{E(f["verdict_old"])}</strong></p>',
             '<h3>The finding</h3>',
             f'<div class="quote"><div class="qmeta">Claude for Bill, 2026-09-05, against 60d66d9c04. Refs: <span class="cite">{E(f["refs_old"])}</span></div>{para(f["quote"])}</div>',
             '<h3>Was it right on 2026-09-05?</h3>', para(f["verdict_old_text"]),
             '<h3>Where the code is now</h3>', para(f["now_text"])]
    if f.get("now_refs"):
        parts.append('<div class="tablewrap"><table><thead><tr><th>Tree</th><th>Location</th><th>What is there</th></tr></thead><tbody>'
                     + "".join(f'<tr><td>{E(r["tree"])}</td><td><span class="cite">{E(r["ref"])}</span></td><td>{inline(r["what"])}</td></tr>' for r in f["now_refs"])
                     + "</tbody></table></div>")
    if f.get("extra_html"):
        parts.append(f["extra_html"])
    parts += ['<h3>Our position</h3>', para(f["position"])]
    if f.get("decisions"):
        parts.append('<div class="decision"><strong>Decision for jhan.</strong>' + ul(f["decisions"]) + "</div>")
    if f.get("insufficient"):
        parts.append('<p class="note"><strong>Insufficient data:</strong> ' + inline("; ".join(f["insufficient"])) + "</p>")
    parts += ['<h3>Draft reply</h3>',
              f'<div class="copywrap"><button class="copybtn" data-copy="rp{f["n"]}">Copy</button><pre class="reply" id="rp{f["n"]}">{E(f["reply"])}</pre></div>']
    return "\n".join(parts)

def gloss(items):
    return '<dl class="gloss">' + "".join(f'<dt>{E(k)}</dt><dd>{inline(v)}</dd>' for k, v in items) + "</dl>"

page = []
page.append(f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(d["title"])}</title>
<style>
  :root {{ --ink:#1f2933; --muted:#52606d; --line:#d9dee3; --bg:#ffffff; --panel:#f5f7fa; --blue:#2b6cb0; --blue-bg:#e8f0fa;
           --green:#276749; --green-bg:#e6f4ea; --orange:#c05621; --orange-bg:#fdf0e6; --red:#c53030; --red-bg:#fde8e8; --grey-bg:#eef1f4; --purple:#553c9a; --purple-bg:#ede9f7; }}
  html, body {{ background: var(--bg); color: var(--ink); }}
  body {{ margin:0; font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }}
  main {{ max-width: 1060px; margin: 0 auto; padding: 28px 24px 64px; }}
  h1 {{ font-size: 26px; line-height:1.25; margin: 0 0 6px; text-wrap: balance; }}
  h2 {{ font-size: 20px; margin: 44px 0 10px; padding-top: 10px; border-top: 2px solid var(--line); text-wrap: balance; }}
  h3 {{ font-size: 13.5px; margin: 20px 0 6px; color: var(--muted); text-transform: uppercase; letter-spacing: .04em; }}
  p {{ margin: 8px 0; max-width: 78ch; }}
  .meta {{ color: var(--muted); font-size: 14px; max-width: none; }}
  .short {{ background: var(--panel); border-left: 4px solid var(--blue); padding: 12px 16px; margin: 18px 0; }}
  .short p {{ margin: 6px 0; max-width: none; }}
  .quote {{ border-left: 4px solid var(--line); padding: 8px 14px; margin: 10px 0; background: #fafbfc; }}
  .quote .qmeta {{ color: var(--muted); font-size: 13px; margin-bottom: 4px; }}
  .quote p {{ font-style: italic; }}
  .cite {{ color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12.5px; }}
  code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
  code {{ background: var(--grey-bg); padding: 1px 4px; border-radius: 3px; font-size: 13.5px; }}
  pre {{ background: var(--panel); border: 1px solid var(--line); border-radius: 6px; padding: 14px 16px; overflow-x: auto; font-size: 13.5px; line-height: 1.5; white-space: pre-wrap; }}
  pre.reply {{ background: #fffdf5; border-color: #e9dfb8; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; font-size: 14.5px; }}
  table {{ border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; font-variant-numeric: tabular-nums; }}
  th, td {{ border: 1px solid var(--line); padding: 7px 9px; vertical-align: top; text-align: left; }}
  th {{ background: var(--panel); }}
  tbody tr:nth-child(even) td {{ background: #fbfcfd; }}
  .tablewrap {{ overflow-x: auto; }}
  dl.gloss {{ display: grid; grid-template-columns: max-content 1fr; gap: 5px 16px; margin: 10px 0; font-size: 14px; }}
  dl.gloss dt {{ font-weight: 600; }}
  dl.gloss dd {{ margin: 0; }}
  @media (max-width: 600px) {{ dl.gloss {{ grid-template-columns: 1fr; }} }}
  ul, ol {{ padding-left: 24px; }}
  li {{ margin: 5px 0; }}
  .pill {{ display:inline-block; padding: 1px 9px; border-radius: 10px; font-size: 12.5px; font-weight: 600; white-space: nowrap; }}
  .pill.s-done {{ background: var(--green-bg); color: var(--green); }}
  .pill.s-partial {{ background: var(--orange-bg); color: var(--orange); }}
  .pill.s-open, .pill.s-differ {{ background: var(--red-bg); color: var(--red); }}
  .pill.s-moved {{ background: var(--purple-bg); color: var(--purple); }}
  .pill.s-merged {{ background: var(--blue-bg); color: var(--blue); }}
  .pill.s-moot {{ background: var(--grey-bg); color: var(--muted); }}
  .copywrap {{ position: relative; }}
  .copybtn {{ position: absolute; right: 10px; top: 10px; font-size: 12.5px; padding: 4px 10px; border: 1px solid var(--line); background: #fff; border-radius: 4px; cursor: pointer; }}
  .copybtn:focus-visible {{ outline: 2px solid var(--blue); outline-offset: 2px; }}
  .note {{ font-size: 13.5px; color: var(--muted); }}
  .decision {{ background: var(--orange-bg); border-left: 4px solid var(--orange); padding: 8px 14px; margin: 10px 0; }}
  .decision ul {{ margin: 6px 0; }}
  figure {{ margin: 18px 0; }}
  figure svg {{ width: 100%; height: auto; display: block; }}
  figcaption {{ color: var(--muted); font-size: 13.5px; margin-top: 6px; max-width: 78ch; }}
  .board {{ display:flex; flex-wrap: wrap; gap: 10px; margin: 12px 0; }}
  .board .card {{ flex: 1 1 140px; border: 1px solid var(--line); border-radius: 6px; padding: 10px 12px; background: var(--panel); }}
  .board .card .n {{ font-size: 26px; font-weight: 700; line-height: 1.1; }}
  .board .card .l {{ font-size: 13px; color: var(--muted); }}
  .toc {{ columns: 2; column-gap: 24px; font-size: 14px; }}
  @media (max-width: 600px) {{ .toc {{ columns: 1; }} }}
</style>
</head>
<body>
<main>
<h1>{E(d["title"])}</h1>
<p class="meta">{inline(d["meta"])}</p>
<div class="short"><p><strong>Short version.</strong> {inline(d["short"])}</p></div>
''')

page.append("<h2>Words used here</h2>" + gloss(d["glossary"]))

page.append('<h2>What was reviewed and what was approved</h2>' + para(d["timeline_text"]))
page.append('<figure>' + fig_timeline(d["timeline"]["events"], d["timeline"]["t0"], d["timeline"]["t1"]) + f'<figcaption>{inline(d["timeline"]["caption"])}</figcaption></figure>')

page.append('<h2>Overview: where each finding stands</h2>' + board())
page.append('<figure>' + fig_matrix(F) + f'<figcaption>{inline(d["matrix_caption"])}</figcaption></figure>')
page.append(summary_table())
page.append(para(d.get("overview_text", "")))

for f in F:
    page.append(finding_section(f))

for sec in d.get("extra_sections", []):
    page.append(f'<h2 id="{E(sec["id"])}">{E(sec["title"])}</h2>' + para(sec["text"]))
    if sec.get("refs"):
        page.append('<div class="tablewrap"><table><thead><tr><th>Tree</th><th>Location</th><th>What is there</th></tr></thead><tbody>'
                    + "".join(f'<tr><td>{E(r["tree"])}</td><td><span class="cite">{E(r["ref"])}</span></td><td>{inline(r["what"])}</td></tr>' for r in sec["refs"])
                    + "</tbody></table></div>")
    if sec.get("decisions"):
        page.append('<div class="decision"><strong>Decision for jhan.</strong>' + ul(sec["decisions"]) + "</div>")
    if sec.get("insufficient"):
        page.append('<p class="note"><strong>Insufficient data:</strong> ' + inline("; ".join(sec["insufficient"])) + "</p>")
    if sec.get("reply"):
        page.append(f'<h3>Draft reply</h3><div class="copywrap"><button class="copybtn" data-copy="rp-{E(sec["id"])}">Copy</button><pre class="reply" id="rp-{E(sec["id"])}">{E(sec["reply"])}</pre></div>')

page.append('<h2 id="order">Suggested order of work</h2>' + para(d["order_text"]) +
            '<div class="tablewrap"><table><thead><tr><th>Step</th><th>Items</th><th>Action</th><th>Precondition or decision</th></tr></thead><tbody>'
            + "".join(f'<tr><td>{i+1}</td><td>{inline(s["items"])}</td><td>{inline(s["action"])}</td><td>{inline(s["pre"])}</td></tr>' for i, s in enumerate(d["order"]))
            + "</tbody></table></div>")

page.append('<h2 id="comment">One consolidated PR comment (draft)</h2>' + para(d["comment_intro"]) +
            f'<div class="copywrap"><button class="copybtn" data-copy="rp-all">Copy</button><pre class="reply" id="rp-all">{E(d["comment"])}</pre></div>')

page.append('<h2 id="method">Method and evidence</h2>' + para(d["method"]))

page.append('''
</main>
<script>
document.querySelectorAll('.copybtn').forEach(function (b) {
  b.addEventListener('click', function () {
    var el = document.getElementById(b.getAttribute('data-copy'));
    if (!el) return;
    var t = el.innerText;
    function done(ok) { b.textContent = ok ? 'Copied' : 'Select and copy'; setTimeout(function(){ b.textContent = 'Copy'; }, 1800); }
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(t).then(function(){done(true)}, function(){done(false)}); }
    else { done(false); }
  });
});
</script>
</body>
</html>
''')

open(OUT, "w", encoding="utf-8").write("\n".join(page))
print("wrote", OUT, os.path.getsize(OUT), "bytes;", len(F), "findings")
