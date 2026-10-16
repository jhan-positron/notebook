#!/usr/bin/env python3
# Generates status/respond-2-runar-PR4557.html from final-items.json (the merged
# workflow output) plus the page-level text in this file. Every reply < 100 words.
import html, json, re, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parents[1] / 'status' / 'respond-2-runar-PR4557.html'
PR = 'https://github.com/positron-ai/tron/pull/4557'
REVIEW = f'{PR}#pullrequestreview-5432936425'
ITEMS = json.loads((HERE / 'final-items.json').read_text())
PAGE = json.loads((HERE / 'page-text.json').read_text())

def disc(i): return f'{PR}#discussion_r{i}'
def e(s): return html.escape(str(s), quote=False)
def words(s): return len(re.findall(r"[A-Za-z0-9][^\s]*", s))
def para(s):
    # Split on blank lines into <p>; keep single text otherwise.
    parts = [p.strip() for p in re.split(r'\n\s*\n', s.strip()) if p.strip()]
    return ''.join(f'<p>{e(p)}</p>' for p in parts)

for it in ITEMS:
    f = it['final']
    n = words(f['reply']); f['nwords'] = n
    assert n < 100, (it['id'], n, f['reply'])

ORDER = {it['id']: i for i, it in enumerate(ITEMS)}
PILL = {'holds': 'holds', 'partly': 'partly', 'refuted': 'refuted'}

rows = ''.join(
    f'<tr><td><a href="#{it["id"].lower()}"><strong>{it["id"]}</strong></a></td>'
    f'<td><code>{e(it["where"])}</code></td>'
    f'<td>{e(it["final"]["title"].split(": ", 1)[-1])}</td>'
    f'<td><span class="pill {PILL[it["final"]["verdict"]]}">{e(it["final"]["verdict"])}</span></td>'
    f'<td>{e(it["final"]["action"])}</td></tr>' for it in ITEMS)

sections = ''
for it in ITEMS:
    f = it['final']
    claims = ''.join(
        f'<tr><td>{e(c["claim"])}</td><td><span class="pill {PILL[c["verdict"]]}">{e(c["verdict"])}</span></td><td>{e(c["evidence"])}</td></tr>'
        for c in f['claims'])
    facts = ''.join(f'<li>{e(x)}</li>' for x in f['facts'])
    opts = ''.join(
        f'<tr><td><strong>{e(o["label"])}</strong></td><td>{e(o["what"])}</td><td>{e(o["for"])}</td><td>{e(o["against"])}</td></tr>'
        for o in f['options'])
    oq = ''.join(f'<li>{e(x)}</li>' for x in f.get('open_questions', []))
    sections += f'''
<h2 id="{it["id"].lower()}">{e(f["title"])} <span class="pill {PILL[f["verdict"]]}">{e(f["verdict"])}</span></h2>
<div class="quote"><div class="who"><a href="{disc(it["cid"])}">comment {it["cid"]}</a> on <code>{e(it["where"])}</code> (the reviewer's text, verbatim)</div>{para(it["quote"])}</div>
<h4>The reviewer's claims, graded</h4>
<div class="tbl"><table><tr><th>Claim</th><th>Holds?</th><th>What the code says</th></tr>{claims}</table></div>
<h4>Facts for the record</h4><ul>{facts}</ul>
<h4>Options</h4>
<div class="tbl"><table><tr><th>Option</th><th>What</th><th>For</th><th>Against</th></tr>{opts}</table></div>
<p><strong>Recommended.</strong> {e(f["recommended"])}</p>
<div class="reply"><div class="lbl">Proposed reply ({f["nwords"]} words)</div><p>{e(f["reply"])}</p></div>
<p class="ev"><strong>Action.</strong> {e(f["action"])}</p>
<p class="ev"><strong>Line numbers on the side branch d9e7645fee.</strong> {e(f["line_shift"])}</p>
{('<h4>Open for jhan</h4><ul>' + oq + '</ul>') if oq else ''}'''

summary_reply = PAGE['summary_reply']
sw = words(summary_reply)

page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PR 4557 Runar Response</title>
<style>
:root{{--paper:#fbfaf6;--ink:#1f2a33;--muted:#5b6770;--line:#d8ddd6;--accent:#0b6e7f;--accent-soft:#e3f0f2;--good:#2e7d4f;--warn:#a8691a;--bad:#b3463b;--code:#f0f1ec;--card:#ffffff}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif;font-size:15px;line-height:1.55}}
.wrap{{max-width:960px;margin:0 auto;padding:32px 20px 64px}}
h1{{font-size:26px;font-weight:600;margin:0 0 6px}}
h2{{font-size:19px;font-weight:600;margin:40px 0 12px;padding-top:14px;border-top:1px solid var(--line)}}
h4{{font-size:14.5px;font-weight:600;margin:18px 0 6px;color:var(--muted)}}
p{{margin:0 0 12px;max-width:80ch}}
.meta{{color:var(--muted);font-size:13.5px;margin-bottom:22px}}
.short{{background:var(--accent-soft);border-left:4px solid var(--accent);padding:12px 16px;margin:0 0 18px;border-radius:0 6px 6px 0}}
.short p{{margin:0 0 8px}}.short p:last-child{{margin:0}}
code{{font-family:ui-monospace,Menlo,monospace;font-size:13px;background:var(--code);padding:1px 5px;border-radius:4px}}
table{{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:14px}}
th,td{{text-align:left;vertical-align:top;padding:7px 9px;border-bottom:1px solid var(--line)}}
th{{font-weight:600;color:var(--muted);font-size:12.5px;letter-spacing:0.04em;text-transform:uppercase}}
.tbl{{overflow-x:auto}}
ul,ol{{padding-left:22px;margin:0 0 12px}}li{{margin-bottom:5px;max-width:80ch}}
.pill{{display:inline-block;font-size:12px;font-weight:500;padding:1px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);margin-left:6px;vertical-align:middle}}
.pill.holds{{color:var(--good);border-color:var(--good)}}.pill.partly{{color:var(--warn);border-color:var(--warn)}}.pill.refuted{{color:var(--bad);border-color:var(--bad)}}
.quote{{margin:14px 0 18px;padding:12px 16px;background:var(--card);border:1px solid var(--line);border-left:4px solid var(--warn);border-radius:0 6px 6px 0}}
.quote .who{{font-weight:600;margin-bottom:6px;font-size:13.5px;color:var(--muted)}}
.quote p{{margin:0 0 8px;font-size:14px}}.quote p:last-child{{margin:0}}
.reply{{margin:14px 0 18px;padding:12px 16px;background:#fffdf5;border:1px solid var(--warn);border-radius:6px}}
.reply .lbl{{font-weight:600;color:var(--warn);margin-bottom:6px}}
.reply p{{margin:0}}
.ev{{color:var(--muted);font-size:13.5px}}
a{{color:var(--accent)}}
@media (max-width:600px){{.wrap{{padding:24px 16px 48px}}h1{{font-size:22px}}}}
</style></head><body><div class="wrap">
<h1>PR 4557: the third reviewer's comments and the proposed replies</h1>
<div class="meta">2026-10-06 &middot; PR <a href="{PR}">#4557</a> reviewed at <code>c5d44bd86f</code> (branch <code>jhan-kv-typed-tensors</code>, one commit on <code>main</code> dd6e85226b); head since 2026-10-07 <code>d9e7645fee</code> &middot; review <a href="{REVIEW}">5432936425</a> of 2026-10-06 18:29 UTC &middot; replies drafted by Claude, decisions by jhan &middot; edits applied and pushed 2026-10-07 (see Outcome), replies not yet posted</div>
<div class="short">{para(PAGE['short'])}</div>

<h2 id="outcome">Outcome (2026-10-07)</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in PAGE['outcome'])}</ul>

<h2 id="scope">0. Scope and branch state</h2>
{para(PAGE['scope'])}
<ul>{''.join(f'<li>{e(x)}</li>' for x in PAGE['state_bullets'])}</ul>

<h2 id="glance">1. The eight points at a glance</h2>
<p>Terms are defined in the section where they first appear. "Holds" means the code confirms the reviewer's statement.</p>
<div class="tbl"><table><tr><th>Id</th><th>Where (at c5d44bd86f)</th><th>The point</th><th>Holds?</th><th>Proposed action</th></tr>{rows}</table></div>

<h2 id="order">2. Proposed order of work</h2>
<ol>{''.join(f'<li>{e(x)}</li>' for x in PAGE['order'])}</ol>
{sections}

<h2 id="summary">3. Reply to the review summary</h2>
<div class="quote"><div class="who"><a href="{REVIEW}">review 5432936425</a> (the reviewer's summary, verbatim)</div>{para(PAGE['summary_quote'])}</div>
<div class="reply"><div class="lbl">Proposed PR-level comment ({sw} words)</div>{para(summary_reply)}</div>

<h2 id="gaps">4. What is not verified</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in PAGE['gaps'])}</ul>

<h2 id="sources">5. Sources and method</h2>
<ul>{''.join(f'<li>{e(x)}</li>' for x in PAGE['sources'])}</ul>
</div></body></html>
'''
nonascii = sorted(set(c for c in page if ord(c) >= 128))
print('non-ascii chars converted to entities:', [hex(ord(c)) for c in nonascii])
page = page.encode('ascii', 'xmlcharrefreplace').decode()
OUT.write_text(page)
print('written', OUT, 'replies:', {it['id']: it['final']['nwords'] for it in ITEMS}, 'summary words', sw)
