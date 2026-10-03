#!/usr/bin/env python3
"""Generate claude-review.html for PR 4596 from the workflow results.

Inputs (scratchpad):
  report-base.json      103 verified findings (refuter corrections applied in code) + 3 rejected
  synth.json            light synthesis workflow result: triage, overview, counters, conditions, tests, correct, cCheck, dCheck
  testdata-result.json  test-data check workflow result (out, verified)
  buildtest.json        build-and-test facts of the head on claude-box
  glossary.json         terms defined at first use
  meta.json             page metadata and fixed prose
Output: claude-review.html (pure ASCII, single-theme light).
"""
import html
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / 'claude-review.html'

base = json.load(open(HERE / 'report-base.json'))
synth = json.load(open(HERE / 'synth.json'))
testdata = json.load(open(HERE / 'testdata-result.json'))
buildtest = json.load(open(HERE / 'buildtest.json'))
glossary = json.load(open(HERE / 'glossary.json'))
meta = json.load(open(HERE / 'meta.json'))
overrides = json.load(open(HERE / 'overrides.json')) if (HERE / 'overrides.json').exists() else {}

TD = testdata['out']
OV = synth['overview']
TR = {r['id']: r for r in synth['triage']['rows']}


def esc(s):
    if s is None:
        return ''
    s = html.escape(str(s), quote=True)
    return s.encode('ascii', 'xmlcharrefreplace').decode('ascii')


def code_refs(s):
    s = esc(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'(?<![\w/`>])((?:h|t|src|ingest|exec|README|CMakeLists|config)[\w./-]*\.(?:hpp|cpp|md|txt|sh|hs|py|json|yml)(?::\d+(?:-\d+)?)?)', r'<code>\1</code>', s)
    return s


def para(s):
    parts = [p.strip() for p in re.split(r'\n\s*\n|\n', str(s or '')) if p.strip()]
    out = []
    items = []
    for p in parts:
        if p.startswith('- '):
            items.append(p[2:].strip())
            continue
        if items:
            out.append('<ul>' + ''.join(f'<li>{code_refs(i)}</li>' for i in items) + '</ul>')
            items = []
        out.append(f'<p>{code_refs(p)}</p>')
    if items:
        out.append('<ul>' + ''.join(f'<li>{code_refs(i)}</li>' for i in items) + '</ul>')
    return ''.join(out)


def pill(kind, text):
    return f'<span class="pill {esc(kind)}">{esc(text)}</span>'


SEV_ORDER = {'must_fix': 0, 'should_fix': 1, 'nit': 2, 'info': 3}
CAT_ORDER = {'defect': 0, 'design_choice': 1, 'future_risk': 2, 'test_gap': 3, 'doc_mismatch': 4, 'style': 5}
SEV_LABEL = {'must_fix': 'must fix', 'should_fix': 'should fix', 'nit': 'nit', 'info': 'info'}
CAT_LABEL = {'defect': 'defect', 'design_choice': 'design choice', 'future_risk': 'future risk', 'test_gap': 'test gap', 'doc_mismatch': 'doc mismatch', 'style': 'style'}
STR_LABEL = {'confirmed_by_code': 'confirmed by code', 'plausible': 'plausible', 'hypothesis': 'hypothesis'}

# ---------- apply triage: final severity/category, plain title, merges ----------
findings = []
merged_into = {}
by_id = {f['id']: f for f in base['findings']}
for f in base['findings']:
    t = TR.get(f['id'])
    g = dict(f)
    if t:
        g['severity'] = t['final_severity']
        g['category'] = t['final_category']
        g['theme'] = t['theme']
        g['title_plain'] = t['title_plain']
        g['why_changed'] = t['why_changed']
        if t['merge_into'] and t['merge_into'] in by_id and t['merge_into'] != f['id']:
            merged_into[f['id']] = t['merge_into']
    else:
        g['theme'] = 'other'
        g['title_plain'] = f['title']
        g['why_changed'] = ''
    findings.append(g)
# resolve merge chains, attach merged findings to their keeper
keep = {}
for f in findings:
    if f['id'] in merged_into:
        target = merged_into[f['id']]
        seen = {f['id']}
        while target in merged_into and target not in seen:
            seen.add(target)
            target = merged_into[target]
        keep.setdefault(target, []).append(f)
final = []
for f in findings:
    if f['id'] in merged_into:
        continue
    f['absorbed'] = keep.get(f['id'], [])
    # overrides from the orchestrator's own checks (plain-English pass, factual fixes)
    if f['id'] in overrides:
        f.update(overrides[f['id']])
    final.append(f)
final.sort(key=lambda f: (SEV_ORDER.get(f['severity'], 9), CAT_ORDER.get(f['category'], 9), f['id']))
counts = {}
for f in final:
    counts[f['severity']] = counts.get(f['severity'], 0) + 1
td_findings = sorted(TD['findings'], key=lambda f: (SEV_ORDER.get(f.get('severity', '').split(' ')[0], 9)))

verdict_text = {'approve': 'approve', 'approve_with_nits': 'approve with nits', 'request_changes': 'request changes', 'needs_measurement': 'needs a measurement'}.get(OV['verdict'], OV['verdict'])


def finding_body(f):
    rows = []
    rows.append(('Trigger', para(f.get('trigger'))))
    rows.append(('Consequence', para(f.get('consequence'))))
    locs = [f.get('location', '')] + list(f.get('other_locations') or [])
    rows.append(('Where', '<p>' + ', '.join(f'<code>{esc(l)}</code>' for l in locs if l) + '</p>'))
    ev = f.get('evidence') or ''
    if f.get('extra_evidence'):
        ev = ev + '\n' + f['extra_evidence']
    rows.append(('Evidence', f'<pre>{esc(ev)}</pre>'))
    rows.append(('Evidence strength', f'<p>{esc(STR_LABEL.get(f.get("evidence_strength"), f.get("evidence_strength")))}</p>'))
    rows.append(('Discriminating check', para(f.get('discriminating_check'))))
    rows.append(('Suggested fix', para(f.get('suggested_fix'))))
    if f.get('closed_by'):
        rows.append(('Status', f'<p><strong>Closed</strong> by commit <code>{esc(f["closed_by"])}</code> on 2026-09-30 (see the follow-up section).</p>'))
    if f.get('verifier_notes'):
        rows.append(('Verifier notes', para(f.get('verifier_notes'))))
    if f.get('why_changed'):
        rows.append(('Triage note', para(f.get('why_changed'))))
    if f.get('absorbed'):
        rows.append(('Same root cause', '<p>' + '; '.join(f'{esc(a["id"])}: {esc(a.get("title_plain") or a["title"])} ({esc(a["location"])})' for a in f['absorbed']) + '</p>'))
    if f.get('lenses'):
        rows.append(('Found by', '<p>' + esc(', '.join(sorted(set(f['lenses'])))) + '</p>'))
    return '<div class="kv">' + ''.join(f'<div class="k">{esc(k)}</div><div class="v">{v}</div>' for k, v in rows) + '</div>'


def finding_card(f, prefix=''):
    fid = f.get('id', '')
    anchor = f'f-{re.sub(r"[^A-Za-z0-9]+", "-", prefix + fid)}'
    head = (f'<span class="fid">{esc(fid)}</span> {esc(f.get("title_plain") or f.get("title"))} '
            f'{pill(f.get("severity"), SEV_LABEL.get(f.get("severity"), f.get("severity")))} '
            f'{pill("cat", CAT_LABEL.get(f.get("category"), f.get("category")))}')
    if f.get('severity') in ('must_fix', 'should_fix'):
        return f'<article class="finding" id="{anchor}"><h4>{head}</h4>{finding_body(f)}</article>'
    return f'<details class="finding" id="{anchor}"><summary>{head}<span class="loc"><code>{esc(f.get("location"))}</code></span></summary>{finding_body(f)}</details>'


def table(headers, rows, cls='num'):
    h = ''.join(f'<th>{esc(x)}</th>' for x in headers)
    b = ''.join('<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in rows)
    return f'<div class="tbl"><table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def apply_corrections(rows, check, key):
    """Fold the refuter's corrections into the cells: replace the wrong text when it appears verbatim, else annotate."""
    corr = {}
    for c in check.get('corrections', []):
        corr.setdefault(c['row'], []).append(c)
    out = []
    for r in rows:
        name = r[key]
        notes = corr.get(name) or [c for k, v in corr.items() for c in v if k and (k in name or name in k)]
        r = dict(r)
        left = []
        for n in notes:
            applied = False
            for fld in list(r.keys()):
                if fld.startswith('_') or not isinstance(r[fld], str):
                    continue
                if n['wrong'] and n['wrong'] in r[fld]:
                    r[fld] = r[fld].replace(n['wrong'], n['right'])
                    applied = True
            if not applied:
                left.append(n)
        if left:
            r['_corr'] = ' '.join(f'Correction ({n["field"]}): {n["right"]} [{n["evidence"]}]' for n in left)
        out.append(r)
    return out


parts = []
parts.append(f'''<title>PR 4596 Claude Review</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* layout: one reading column; cards only for findings; wide tables scroll inside their own box */
:root{{--paper:#fbfaf6;--ink:#1f2a33;--muted:#5b6770;--line:#d8ddd6;--accent:#0b6e7f;--accent-soft:#e3f0f2;--good:#2e7d4f;--warn:#a8691a;--bad:#a83a2a;--code:#f0f2ee;--card:#ffffff;color-scheme:light}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:15px;line-height:1.55}}
.wrap{{max-width:980px;margin:0 auto;padding-block:32px 64px;padding-inline:20px}}
h1{{font-size:26px;font-weight:600;letter-spacing:-0.01em;margin:0 0 6px;text-wrap:balance}}
h2{{font-size:19px;font-weight:600;margin:40px 0 12px;padding-top:14px;border-top:1px solid var(--line);text-wrap:balance}}
h3{{font-size:16px;font-weight:600;margin:24px 0 8px}}
h4{{font-size:15px;font-weight:600;margin:0 0 8px;line-height:1.4}}
p{{margin:0 0 10px;max-width:78ch}}
.meta{{color:var(--muted);font-size:13.5px;margin-bottom:22px}}
.short{{background:var(--accent-soft);border-left:4px solid var(--accent);padding:12px 16px;margin:0 0 18px;border-radius:0 6px 6px 0}}
.short p{{margin:0 0 8px;max-width:none}}.short p:last-child{{margin:0}}
code,pre{{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace;font-size:13px}}
code{{background:var(--code);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}}
pre{{background:var(--code);padding:10px 12px;border-radius:6px;overflow-x:auto;line-height:1.45;margin:4px 0 8px;white-space:pre-wrap;overflow-wrap:anywhere}}
table{{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:13.5px}}
th,td{{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--line)}}
th{{font-weight:600;color:var(--muted);font-size:12px;letter-spacing:0.04em;text-transform:uppercase}}
.tbl{{overflow-x:auto}}
.num{{font-variant-numeric:tabular-nums}}
ul,ol{{padding-left:22px;margin:0 0 12px}}li{{margin-bottom:5px;max-width:78ch}}
.pill{{display:inline-block;font-size:12px;font-weight:500;padding:1px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);margin-left:4px;vertical-align:middle;white-space:nowrap}}
.pill.must_fix{{color:#fff;background:var(--bad);border-color:var(--bad)}}
.pill.should_fix{{color:var(--warn);border-color:var(--warn)}}
.pill.nit,.pill.info{{color:var(--muted)}}
.pill.cat{{color:var(--accent);border-color:var(--accent)}}
.pill.verdict{{font-size:14px;padding:3px 12px;color:var(--good);border-color:var(--good)}}
.finding{{margin:14px 0 18px;padding:12px 16px;background:var(--card);border:1px solid var(--line);border-radius:6px}}
details.finding{{margin:8px 0;padding:8px 14px}}
details.finding summary{{cursor:pointer;font-weight:500;line-height:1.5}}
details.finding summary .loc{{display:block;font-weight:400;font-size:13px;color:var(--muted);margin-top:2px}}
details.finding[open] summary{{margin-bottom:10px}}
.fid{{font-family:"IBM Plex Mono",ui-monospace,monospace;font-size:12.5px;color:var(--muted);margin-right:4px}}
.kv{{display:grid;grid-template-columns:150px minmax(0,1fr);gap:4px 12px}}
.kv .k{{color:var(--muted);font-size:12.5px;letter-spacing:0.03em;text-transform:uppercase;padding-top:3px}}
.kv .v{{min-width:0}}.kv .v p{{margin:0 0 6px}}.kv .v pre{{margin:0 0 6px}}
.count{{display:flex;flex-wrap:wrap;gap:10px 24px;margin:0 0 14px;font-variant-numeric:tabular-nums}}
.count span{{white-space:nowrap}}
.toc{{columns:2;column-gap:28px;font-size:14px}}.toc li{{break-inside:avoid}}
.corr{{color:var(--warn);font-size:13px}}
a{{color:var(--accent)}}
a:focus-visible,summary:focus-visible{{outline:2px solid var(--accent);outline-offset:2px}}
@media (max-width:600px){{.wrap{{padding-inline:16px}}h1{{font-size:22px}}.kv{{grid-template-columns:1fr}}.toc{{columns:1}}}}
</style>
<div class="wrap">
<h1>PR 4596 review: attention path stats behind TRON_ATTN_STATS</h1>
<div class="meta">{esc(meta["date"])} &middot; reviewer: Claude, following the tron-code-review skill (the review checklist for tron pull requests) &middot; reviewed head <code>{esc(meta["head"])}</code> (PR head now <code>0f784c44ff</code> after the follow-up commits) on branch <code>{esc(meta["branch"])}</code>, diff base <code>{esc(meta["base"])}</code> (the main commit the branch started from) &middot; verdict {pill("verdict", verdict_text)}</div>
''')

parts.append('<div class="short"><p><strong>Short version.</strong> ' + ' '.join(code_refs(s) for s in OV['short_version']) + '</p><p>' + code_refs(meta['followup_short']) + '</p></div>')

toc = [('words', 'Words used here'), ('scope', 'Scope, method, what was actually run'), ('wade', 'The five earlier review comments and their fixes'),
       ('themes', 'Findings by theme'), ('findings', 'Findings'), ('followup', 'Follow-up: the five test gaps closed'), ('testdata', 'Posted test data of 2026-09-30'), ('counters', 'Counter and timer audit'),
       ('conditions', 'Conditions checked'), ('tests', 'Test review'), ('proposed', 'Proposed tests'), ('correct', 'Verified correct'),
       ('questions', 'Open questions for the author'), ('rejected', 'Findings rejected by the verifiers'), ('method', 'Method details')]
parts.append('<ul class="toc">' + ''.join(f'<li><a href="#{a}">{esc(n)}</a></li>' for a, n in toc) + '</ul>')

parts.append('<h2 id="words">Words used here</h2><ul>' + ''.join(f'<li><strong>{esc(g["term"])}</strong>: {code_refs(g["def"])}</li>' for g in glossary) + '</ul>')

parts.append('<h2 id="scope">Scope, method, what was actually run</h2>')
parts.append(para(meta['scope_text']))
parts.append('<h3>Verdict</h3>')
parts.append(para(OV['verdict_reason']))
parts.append('<h3>Tests actually run for this review</h3>')
parts.append(para(buildtest['summary']))
parts.append(table(['binary', 'TRON_ATTN_STATS', 'result', 'cases', 'assertions', 'wall s', '[attn-stats] lines'], [[esc(c) for c in r] for r in buildtest['rows']]))
parts.append('<ul>' + ''.join(f'<li>{code_refs(n)}</li>' for n in buildtest['notes']) + '</ul>')
parts.append('<h3>Code inspection</h3>')
parts.append(para(meta['inspection_text']))

parts.append('<h2 id="wade">The five earlier review comments and their fixes</h2>')
parts.append(para(meta['wade_intro']))
wrows = []
for w in meta['wade']:
    ids = [f['id'] for f in final if any(k in (f.get('title', '') + ' ' + f.get('trigger', '') + ' ' + f.get('consequence', '') + ' ' + f.get('evidence', '')) for k in w['keys'])]
    wrows.append([esc(w['id']), code_refs(w['comment']), code_refs(w['fix']), code_refs(w['status']), ', '.join(f'<a href="#f-{i}">{esc(i)}</a>' for i in ids[:8]) or 'none'])
parts.append(table(['comment', 'what it asked', 'fix commit', 'this review finds', 'related findings'], wrows))

parts.append('<h2 id="themes">Findings by theme</h2>')
parts.append('<div class="count">' + ''.join(f'<span><strong>{counts.get(k, 0)}</strong> {esc(SEV_LABEL[k])}</span>' for k in ['must_fix', 'should_fix', 'nit', 'info']) + f'<span><strong>{len(td_findings)}</strong> on the posted test data</span></div>')
parts.append(para(OV['findings_intro']))
if OV.get('top_items'):
    parts.append('<h3>Read these first</h3><ol>' + ''.join(f'<li><a href="#f-{esc(i)}">{esc(i)}</a>: {esc((next((f for f in final if f["id"] == i), None) or {}).get("title_plain", ""))}</li>' for i in OV['top_items'] if any(f['id'] == i for f in final)) + '</ol>')
parts.append(table(['theme', 'one line', 'findings'], [[esc(t['theme']), code_refs(t['one_line']), ', '.join(f'<a href="#f-{esc(i)}">{esc(i)}</a>' for i in t['ids'] if any(f['id'] == i for f in final))] for t in OV['themes_summary']]))

parts.append('<h2 id="findings">Findings</h2>')
cur = None
for f in final:
    if f['severity'] != cur:
        cur = f['severity']
        parts.append(f'<h3>{esc(SEV_LABEL.get(cur, cur))} ({counts.get(cur, 0)})</h3>')
        if cur in ('nit', 'info'):
            parts.append('<p>Each item below opens on click.</p>')
    parts.append(finding_card(f))

parts.append('<h2 id="followup">Follow-up: the five test gaps closed</h2>')
parts.append(para(meta['followup_intro']))
parts.append(table(['finding', 'commit', 'test added', 'production entry point', 'run result', 'mutation check', 'review'],
                   [[f'<a href="#f-{esc(r["id"])}">{esc(r["id"])}</a>', esc(r['commit']), code_refs(r['test']), code_refs(r['entry']), code_refs(r['run']), code_refs(r['mutation']), code_refs(r['review'])] for r in meta['followup_rows']]))
parts.append('<h3>What the new tests do not discriminate</h3><ul>' + ''.join(f'<li><strong>{esc(r["id"])}</strong>: {code_refs(r["not_caught"])}</li>' for r in meta['followup_rows'] if r['not_caught']) + '</ul>')
parts.append('<h3>Full runs at the new head</h3>')
parts.append(para(meta['followup_runs']))
parts.append('<h2 id="testdata">Posted test data of 2026-09-30</h2>')
parts.append('<div class="short"><p>' + ' '.join(code_refs(s) for s in TD['short_version']) + '</p></div>')
parts.append(para(meta['testdata_intro']))
parts.append('<h3>Consistency checks</h3>')
parts.append(table(['check', 'expected', 'observed', 'result'], [[code_refs(c['check']), code_refs(c['expected']), code_refs(c['observed']), code_refs(c['result'])] for c in TD['consistency_checks']]))
parts.append('<h3>Claims in the comments</h3>')
parts.append(table(['claim', 'verdict', 'evidence'], [[code_refs(c['claim']), esc(c['verdict']), code_refs(c['evidence'])] for c in TD['claims_table']]))
parts.append('<h3>Idle time no timer covers</h3>')
parts.append(para(TD['untimed_idle']))
parts.append('<h3>Findings on the comments and the PR body</h3>')
for f in td_findings:
    g = dict(f)
    g['severity'] = g['severity'].split(' ')[0]
    parts.append(finding_card(g, 'td-'))
parts.append('<h3>PR body items that are stale at the head</h3><ul>' + ''.join(f'<li>{code_refs(s)}</li>' for s in TD['stale_pr_body_items']) + '</ul>')

parts.append('<h2 id="counters">Counter and timer audit</h2>')
parts.append(para(synth['counters']['intro']))
crow = apply_corrections(synth['counters']['rows'], synth.get('cCheck') or {}, 'counter')
parts.append(table(['counter or timer', 'counts the intended work?', 'updated by', 'owner: init, aggregate, reset', 'omit or double-count risk', 'verdict'],
                   [[code_refs(c['counter']), code_refs(c['counts_intended_work']), code_refs(c['updated_by']), code_refs(c['owner_init_reset']), code_refs(c['omit_or_double_count_risk']), code_refs(c['verdict']) + (f'<div class="corr">{code_refs(c["_corr"])}</div>' if c.get('_corr') else '')] for c in crow]))

parts.append('<h2 id="conditions">Conditions checked</h2>')
parts.append(para(synth['conditions']['intro']))
STATUS = {'checked_by_reading': 'checked by reading', 'not_checked': 'not checked', 'test_run_needed': 'needs a test run'}
drow = apply_corrections(synth['conditions']['rows'], synth.get('dCheck') or {}, 'condition')
parts.append(table(['condition', 'status', 'evidence', 'result'], [[code_refs(c['condition']), esc(STATUS.get(c['status'], c['status'])), code_refs(c['evidence']), code_refs(c['result']) + (f'<div class="corr">{code_refs(c["_corr"])}</div>' if c.get('_corr') else '')] for c in drow]))

parts.append('<h2 id="tests">Test review</h2>')
parts.append(para(synth['tests']['tests_intro']))
TT = json.load(open(HERE / 'test-table.json'))
parts.append(para(TT['build_lanes']))
VERD = {'meaningful': 'meaningful', 'weak': 'weak', 'cannot_fail': 'cannot fail', 'flaky_risk': 'flaky risk'}
parts.append(table(['file', 'case or section', 'lines', 'production boundary called', 'fake keeps the information?', 'semantic break that fails it', 'breaks not caught', 'verdict'],
                   [[code_refs(t['file']), code_refs(t['case_or_section']), esc(t['lines']), code_refs(t['production_boundary_called']), code_refs(t['fake_retains_information']), code_refs(t['semantic_break_that_fails_it']), code_refs(t['breaks_not_caught']), esc(VERD.get(t['verdict'], t['verdict']))] for t in TT['tests']]))

parts.append('<h2 id="proposed">Proposed tests</h2>')
parts.append('<ol>' + ''.join(f'<li>{code_refs(s)}</li>' for s in synth['tests']['proposed_tests']) + '</ol>')

parts.append('<h2 id="correct">Verified correct</h2>')
parts.append(para(synth['correct']['intro']))
for g in synth['correct']['groups']:
    parts.append(f'<h3>{esc(g["area"])}</h3><ul>' + ''.join(f'<li>{code_refs(s)}</li>' for s in g['items']) + '</ul>')

parts.append('<h2 id="questions">Open questions for the author</h2>')
parts.append('<ol>' + ''.join(f'<li>{code_refs(s)}</li>' for s in OV['open_questions_for_author']) + '</ol>')

parts.append('<h2 id="rejected">Findings rejected by the verifiers</h2>')
parts.append(para(meta['rejected_intro']))
parts.append(table(['id', 'claim', 'where', 'why rejected'], [[esc(r['id']), code_refs(r['title']), code_refs(r['location']), code_refs(r['why_rejected'])] for r in base['rejected']]))
parts.append(table(['id', 'claim', 'why rejected'], [[esc(r['id']), code_refs(r['title']), code_refs(r['why'])] for r in TD['rejected']]))

parts.append('<h2 id="method">Method details</h2>')
parts.append(para(meta['method_text']))
parts.append('</div>')

out = '\n'.join(parts)
assert all(ord(ch) < 128 for ch in out), 'non-ASCII character in output'
OUT.write_text(out)
print(OUT, len(out), 'bytes;', len(final), 'findings shown,', len(merged_into), 'merged;', counts)
