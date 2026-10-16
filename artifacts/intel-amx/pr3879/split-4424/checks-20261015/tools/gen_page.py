#!/usr/bin/env python3
"""Build checks-20261015.html: the record of the two checks on PRs 4824/4868/4887."""
import json, re, collections, html, sys, os, glob
S = sys.argv[1]; OUT = sys.argv[2]
PRS = ['4824', '4868', '4887']
TITLE = {'4824': 'PR 4824 (review copy of #4424, 28 files)', '4868': 'PR 4868 (PR-1 of the split: layout and readers)', '4887': 'PR 4887 (PR-2 of the split: AMX attention)'}
HEAD = {'4824': '9d5c7a389b', '4868': '82d05e94be', '4887': '0ee8671d35'}
RULE_B = {'1': 'Rule 1: the name carries it', '2': 'Rule 2: restates identifiers', '3': 'Rule 3: one-line contract', '4': 'Rule 4: lines that map to no code', '5': 'Rule 5: call-site comment says only why here', '6': 'Rule 6: idiom comment'}
RULE_A = {'bare-literal-argument': 'bare literal as a call argument', 'bare-literal-template-argument': 'bare literal as a template argument', 'bare-literal-aggregate': 'bare literal in positional aggregate init', 'named-constant-not-argument': 'named constant outside an argument position'}
def load(pr, ch):
    for d in ['out2', 'out1']:
        p = f'{S}/{d}/{pr}-{ch}.json'
        if os.path.exists(p): return json.load(open(p))
    return []
F = {(pr, ch): load(pr, ch) for pr in PRS for ch in 'AB'}
# reviews from logs
reviews = []
for pr in PRS:
    for ch in 'AB':
        for lf in sorted(glob.glob(f'{S}/post/log-*.txt')):
            for ln in open(lf):
                m = re.search(rf'part (\d+)/(\d+) (?:POSTED review|landed as review) (\d+)', ln)
                if m and f'--pr {pr}' in open(lf).read()[:0] + '' : pass
        # parse from payload/body files instead: body-<pr>-<ch>-<k>.md exists => part k
for lf in sorted(glob.glob(f'{S}/post/log-*.txt')) + [f'{S}/post/log-chain2.txt']:
    if not os.path.exists(lf): continue
    cur = None
    for ln in open(lf):
        m = re.search(r'part (\d+)/(\d+) payload: PR (\d+): (\d+) comments', ln)
        if m: cur = {'part': int(m.group(1)), 'n': int(m.group(2)), 'pr': m.group(3), 'count': int(m.group(4))}
        m = re.search(r'part (\d+)/(\d+) (?:POSTED review|landed as review) (\d+)', ln)
        if m and cur and cur['part'] == int(m.group(1)):
            cur['id'] = m.group(3); reviews.append(dict(cur)); cur = None
        m = re.search(r'4887-A POSTED (\d+)', ln)
        if m: reviews.append({'part': 1, 'n': 1, 'pr': '4887', 'count': 0, 'id': m.group(1), 'ch': 'A'})
# checker of a review: from the body file's first line
for r in reviews:
    if 'ch' in r: continue
    for ch in 'AB':
        bf = f"{S}/post/body-{r['pr']}-{ch}-{r['part']}.md"
        if os.path.exists(bf) and r['count'] == len(json.load(open(f"{S}/post/comments-{r['pr']}-{ch}-{r['part']}.json"))): r['ch'] = ch
reviews = [r for r in reviews if 'ch' in r]
seen = set(); uniq = []
for r in reviews:
    if r['id'] in seen: continue
    seen.add(r['id']); uniq.append(r)
if not any(r['pr'] == '4824' and r['ch'] == 'B' and r['part'] == 1 for r in uniq):
    uniq.append({'part': 1, 'n': 7, 'pr': '4824', 'count': 60, 'id': '5528225084', 'ch': 'B'})  # landed despite the HTTP 502; its log line says POST FAILED
reviews = sorted(uniq, key=lambda r: (r['pr'], r['ch'], r['part']))
# counts
cnt = {(pr, ch): collections.Counter(c['rule'] for c in F[(pr, ch)]) for pr in PRS for ch in 'AB'}
files = {(pr, ch): collections.Counter(c['path'] for c in F[(pr, ch)]) for pr in PRS for ch in 'AB'}
tot = {(pr, ch): len(F[(pr, ch)]) for pr in PRS for ch in 'AB'}
def esc(s): return html.escape(str(s))
def panel(pr, ch, rules, maxv):
    rows = [(rules[r], cnt[(pr, ch)].get(r, 0)) for r in rules]
    W, LW, BH, GAP = 560, 250, 18, 8
    h = len(rows) * (BH + GAP) + 10
    svg = [f'<svg viewBox="0 0 {W} {h}" width="100%" role="img" aria-label="{esc(TITLE[pr])}: findings per rule">']
    for i, (name, v) in enumerate(rows):
        y = i * (BH + GAP) + 4
        bw = 0 if maxv == 0 else (W - LW - 50) * v / maxv
        svg.append(f'<text x="{LW - 8}" y="{y + BH - 4}" text-anchor="end" class="lbl">{esc(name)}</text>')
        if v: svg.append(f'<rect x="{LW}" y="{y}" width="{bw:.1f}" height="{BH}" rx="4" class="bar"><title>{esc(name)}: {v}</title></rect>')
        svg.append(f'<text x="{LW + bw + 6:.1f}" y="{y + BH - 4}" class="val">{v}</text>')
    svg.append('</svg>')
    return '\n'.join(svg)
maxB = max(max(cnt[(pr, 'B')].values(), default=0) for pr in PRS); maxA = max(max(cnt[(pr, 'A')].values(), default=0) for pr in PRS)
def table_files(ch):
    paths = sorted({p for pr in PRS for p in files[(pr, ch)]})
    out = ['<table><thead><tr><th>file</th>' + ''.join(f'<th>{pr}</th>' for pr in PRS) + '</tr></thead><tbody>']
    for p in paths: out.append(f'<tr><td><code>{esc(p)}</code></td>' + ''.join(f'<td class="num">{files[(pr, ch)].get(p, 0) or ""}</td>' for pr in PRS) + '</tr>')
    out.append('<tr class="tot"><td>total</td>' + ''.join(f'<td class="num">{tot[(pr, ch)]}</td>' for pr in PRS) + '</tr></tbody></table>')
    return '\n'.join(out)
def table_reviews():
    out = ['<table><thead><tr><th>PR</th><th>check</th><th>part</th><th>inline comments</th><th>review</th></tr></thead><tbody>']
    for r in reviews:
        url = f"https://github.com/positron-ai/tron/pull/{r['pr']}#pullrequestreview-{r['id']}"
        out.append(f"<tr><td>{r['pr']}</td><td>{'comments' if r['ch']=='B' else 'named bool'}</td><td>{r['part']} of {r['n']}</td><td class=\"num\">{r['count']}</td><td><a href=\"{url}\">{r['id']}</a></td></tr>")
    out.append('</tbody></table>'); return '\n'.join(out)
dropped = json.load(open(f'{S}/out2/dropped.json'))
allB = sum(tot[(pr, 'B')] for pr in PRS); allA = sum(tot[(pr, 'A')] for pr in PRS)
page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Two checks on three PRs</title>
<style>
:root {{ --surface: #fcfcfb; --text: #0b0b0b; --text2: #52514e; --grid: #e6e5e1; --bar: #2a78d6; --panel: #f4f4f1; }}
body {{ background: var(--surface); color: var(--text); font: 15px/1.5 system-ui, sans-serif; margin: 0; padding: 24px 16px; }}
main {{ max-width: 960px; margin: 0 auto; }}
h1 {{ font-size: 24px; margin: 0 0 8px; }} h2 {{ font-size: 18px; margin: 32px 0 8px; }} h3 {{ font-size: 15px; margin: 16px 0 4px; color: var(--text2); }}
.short {{ background: var(--panel); border-left: 4px solid var(--bar); padding: 10px 14px; margin: 12px 0 20px; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; margin: 8px 0 16px; }} th, td {{ text-align: left; padding: 4px 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }} td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }} tr.tot td {{ font-weight: 600; }}
.lbl {{ font-size: 12px; fill: var(--text2); }} .val {{ font-size: 12px; fill: var(--text); font-weight: 600; }} .bar {{ fill: var(--bar); }}
.panel {{ background: var(--panel); border-radius: 8px; padding: 10px 12px; margin: 8px 0; }}
.take {{ color: var(--text2); font-size: 14px; margin: 4px 0 12px; }}
code {{ font-size: 13px; }} dl dt {{ font-weight: 600; margin-top: 6px; }} dl dd {{ margin: 0 0 4px 0; }}
</style></head><body><main>
<h1>Two checks on PRs 4824, 4868 and 4887</h1>
<p class="take">positron-ai/tron, 2026-10-15. Review comments posted by the checks described below; nothing in the code was changed.</p>
<div class="short"><strong>Short version.</strong> Two checks ran over every C++ line the three PRs add: the named-bool rule and the simplify-cpp-comments skill in Check mode. They produced {allB} comment findings and {allA} named-bool findings, each one checked by two or three independent refuter agents before it was posted. The findings are posted as inline review comments on the PRs; the tables below link every review.</div>

<h2>Words used here</h2>
<dl>
<dt>named-bool rule</dt><dd>jhan's rule of 2026-10-15: use a named <code>constexpr bool</code> only where a bool is passed as an argument in a function call, constructor call or template argument, because a bare <code>true</code> or <code>false</code> at a call site does not say what it means. Default arguments and initializers take the bare literal (precedent: PR #4901 commit d0e6f816dd).</dd>
<dt>simplify-cpp-comments, Check mode</dt><dd>the skill that lists every added or changed comment a rule would cut, shorten or move, with the rule number and the proposed text. Rule 1: the name carries it. Rule 2: do not restate identifiers. Rule 3: one line for the one fact the code does not say. Rule 4: every comment line maps to a code line. Rule 5: a call-site comment says only why the call sits here. Rule 6: no comment on a language idiom. Rule 0: only comments the diff adds or changes.</dd>
<dt>refuter</dt><dd>an independent agent given one finding and told to refute it, through one lens: the rule as written, the code at the PR head, or diff scope and line anchoring. A comment finding is posted when at least two of three refuters did not refute it; a named-bool finding when neither of two did.</dd>
<dt>PR 4824 / 4868 / 4887</dt><dd>4824 is the draft review copy of the original PR #4424 (28 files); 4868 is PR-1 of its split (the VNNI K layout and readers); 4887 is PR-2 (the AMX attention path), based on 4868. Heads checked: {', '.join(f'{pr} at {HEAD[pr]}' for pr in PRS)}.</dd>
</dl>

<h2>Comment findings per rule</h2>
<p class="take">One bar per rule, one panel per PR. Rule 2 (a comment restating a name or type) is the largest group in every PR.</p>
{''.join(f'<div class="panel"><h3>{esc(TITLE[pr])}: {tot[(pr, "B")]} findings</h3>{panel(pr, "B", RULE_B, maxB)}</div>' for pr in PRS)}

<h2>Named-bool findings per kind</h2>
<p class="take">PR 4887 adds no bool literal in an argument position and no named literal bool, so it has none. The named constants outside an argument position are the <code>*_TRUE</code>/<code>*_FALSE</code> values used in returns, initializers and default arguments.</p>
{''.join(f'<div class="panel"><h3>{esc(TITLE[pr])}: {tot[(pr, "A")]} findings</h3>{panel(pr, "A", RULE_A, maxA)}</div>' for pr in PRS)}

<h2>Reviews posted</h2>
{table_reviews()}

<h2>Comment findings per file</h2>
{table_files('B')}
<h2>Named-bool findings per file</h2>
{table_files('A')}

<h2>Method and limits</h2>
<ul>
<li>Inputs: the three PR diffs, split per file with new-file line numbers; the full files at each head for context. Only added lines were checked.</li>
<li>Finders: per changed C++ file, two comment finders with different framings (rule by rule, and the cover test) and one named-bool finder where the file has a bool candidate. Findings from the two comment finders were merged by overlapping line range; 244 of the 285 first-run comment findings were found by both.</li>
<li>Run 1 (workflow wf_a5efbc70-452) reached the 1000-agent cap before two files of PR 4868 (t_k_vnni_layout.cpp, t_llama_unit.cpp) were checked; run 2 (wf_a84b3a54-b45, 239 agents) covered them and re-ran the named-bool check under the rule wording of 2026-10-15 (template arguments in, default arguments out). Named-bool findings from run 1 were discarded.</li>
<li>Refuted: {len(dropped)} comment finding(s) were dropped by the refuters (listed in findings/dropped.json): one cut a clause that exists before the PR (Rule 0), one cut a step heading that states a placement reason.</li>
<li>Not flagged under the named-bool rule: bare literals in returns, assignments, initializers, comparisons, designated initializers and default arguments; Catch2 macros; computed constexpr bools. On <code>main</code> the parameter-name comment form <code>/*name=*/true</code> appears 454 times and no <code>*_TRUE</code>/<code>*_FALSE</code> constant exists outside numeric_limits traits.</li>
<li>Not flagged under the comment rules: Note [..] blocks as a whole; inside a Note only a sentence that restates an identifier.</li>
<li>Every proposed comment line fits the 88-column limit of the project's clang-format. No code was built or run.</li>
<li>Posting: GitHub returned a 502 and then a secondary rate limit on the first large review; the rest went out in parts of at most 25 comments, 90 seconds apart. Review ids are in the table above.</li>
<li>Record: split-4424/checks-20261015/ holds the tools, the findings with every refuter vote (merged-with-votes.json.gz), the review bodies and the annotated diffs.</li>
</ul>
</main></body></html>'''
open(OUT, 'w').write(page)
print('wrote', OUT, len(page), 'bytes;', len(reviews), 'reviews in table')
