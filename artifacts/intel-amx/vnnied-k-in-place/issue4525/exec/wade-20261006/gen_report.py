# Build status/Wade-code-review-skill-v2.html (pure ASCII, light theme) from the campaign data.
import json, html, re
m = json.load(open('merged-taxonomy.json')); S = json.load(open('style-stats.json'))
nums = json.load(open('items2/numbers.json')); R3 = json.load(open('wf3-result.json'))
heads = {c['label']: re.sub(r'^### [0-9AB]+\. ', '', c['heading']) for c in R3['checks']}
NUMTXT = {**{k: str(v) for k, v in nums.items()}, 'test-silently-skips-or-cannot-fail': '3A', 'tests-run-at-head-before-approve': '3B'}
SECTION = {}
for sec, labs in [('code: hygiene', ['dead-symbol-no-consumer-or-definition','typo-or-wording-in-added-text','magic-literal-or-constant-name','debug-switch-or-output-left-on','comment-contradicts-adjacent-code','duplicate-logic-use-existing-helper','type-and-initialization-choice','identifier-name-states-role','missing-explanation-at-declaration','redundant-code-simplify','disabled-code-left-in','declaration-placement-and-file-organization','silent-behavior-change-or-unexamined-threshold']),
 ('code: lifetime, concurrency, cost', ['index-count-or-wait-set-mismatch','silent-fallback-where-assert-belongs','concurrency-race-or-lock-placement','buffer-lifetime-or-alignment','hot-path-avoidable-work','state-ownership-and-key-granularity','observability-and-operability-of-new-path']),
 ('tests', ['value-rows-need-consumer-or-provenance','test-silently-skips-or-cannot-fail','tests-run-at-head-before-approve','duplicate-test-coverage','test-name-tag-output-conventions','test-exists-and-reaches-changed-path','workaround-needs-tracking']),
 ('claims and body', ['claim-wider-than-code','pr-body-and-branch-state','code-comment-carries-no-lasting-fact']),
 ('scope, history, bots', ['unrelated-or-unexplained-hunk','verify-automated-findings'])]:
    for l in labs: SECTION[l] = sec
COL = {'code: hygiene': '#2a78d6', 'code: lifetime, concurrency, cost': '#eb6834', 'tests': '#1baf7a', 'claims and body': '#4a3aa7', 'scope, history, bots': '#e34948'}
rows = [(c['label'], c['count'], c['prs_spanned'], c['disposition']) for c in m['checks'] if c['disposition'] not in ('drop', 'keep_existing')]
rows.sort(key=lambda r: -r[1])
mx = max(r[1] for r in rows)
def esc(s): return html.escape(s, quote=True)
bars = []
for lab, n, prs, disp in rows:
    w = 100.0 * n / mx; sec = SECTION[lab]
    name = f"{NUMTXT[lab]}. {heads[lab]}"
    tag = 'new' if disp == 'add_new' else 'widened'
    bars.append(f'<div class="row"><div class="lab" title="{esc(lab)}">{esc(name)} <span class="tag {tag}">{tag}</span></div><div class="bar"><div class="fill" style="width:{w:.1f}%;background:{COL[sec]}"></div><span class="val">{n} comments, {prs} PRs</span></div></div>')
legend = ' '.join(f'<span class="lg"><i style="background:{c}"></i>{esc(s)}</span>' for s, c in COL.items())
area = S['inline_by_area']; amx = max(area.values())
area_bars = ''.join(f'<div class="row"><div class="lab">{esc(k)}</div><div class="bar"><div class="fill" style="width:{100.0*v/amx:.1f}%;background:#2a78d6"></div><span class="val">{v}</span></div></div>' for k, v in area.items())
vb = S['final_verdict_by_top_level_comment_count']
verdict_rows = ''.join(f'<tr><td>{k}</td><td>{v.get("APPROVED",0)}</td><td>{v.get("COMMENTED",0)}</td></tr>' for k, v in vb.items())
new = sum(1 for r in rows if r[3] == 'add_new'); wid = sum(1 for r in rows if r[3] != 'add_new')
page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Wade skill v2</title>
<meta name="description" content="How the Wade-code-review skill was rebuilt from all 115 PRs Wade reviewed, and the cross-check against codex's version">
<style>
:root{{color-scheme:light;--bg:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--line:#e4e3df;--card:#ffffff}}
body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,Segoe UI,Helvetica,Arial,sans-serif}}
main{{max-width:980px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:28px;margin:0 0 8px}} h2{{font-size:20px;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:4px}} h3{{font-size:17px;margin:20px 0 6px}}
.short{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 16px;margin:12px 0 20px}}
.row{{display:grid;grid-template-columns:minmax(220px,42%) 1fr;gap:8px;align-items:center;margin:3px 0}}
.lab{{font-size:13px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.bar{{position:relative;height:18px;background:#f1f0ec;border-radius:3px}} .fill{{height:100%;border-radius:0 3px 3px 0}}
.val{{position:absolute;left:6px;top:0;font-size:12px;line-height:18px;color:var(--ink);mix-blend-mode:multiply}}
.tag{{font-size:10px;padding:0 5px;border-radius:8px;border:1px solid var(--line);color:var(--ink2);vertical-align:middle}} .tag.new{{background:#eef5ff}}
.lg{{display:inline-block;margin:0 12px 6px 0;font-size:13px;color:var(--ink2)}} .lg i{{display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:5px;vertical-align:-1px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:8px 0}} th,td{{border:1px solid var(--line);padding:5px 8px;text-align:left;vertical-align:top}} th{{background:#f5f4f0}}
.take{{font-size:14px;color:var(--ink2);margin:6px 0 0}} code{{font-size:13px;background:#f1f0ec;padding:0 4px;border-radius:3px}}
ul{{padding-left:22px}} li{{margin:3px 0}} .glos dt{{font-weight:600;margin-top:6px}} .glos dd{{margin:0 0 0 0}}
@media (max-width:600px){{.row{{grid-template-columns:1fr}} .bar{{height:20px}}}}
</style></head><body><main>
<h1>Wade-code-review skill, version 2</h1>
<p class="take">2026-10-06. Source data and scripts: <code>issue4525/exec/wade-20261006/</code>. Installed skill: <code>~/.claude/skills/Wade-code-review/</code>.</p>
<div class="short"><b>Short version.</b> The 2026-10-05 skill (13 checks) came from one review, PR 4557, and covered tests, the PR body and history. Wade's whole record (115 PRs he did not author, 273 texts) shows 203 of his 243 inline comments on production code in h/ and src/, so version 2 adds 22 code-level checks and widens 9 of the old 13 to 35 checks. Codex's parallel refresh was cross-checked: it refuted two sentences of the old skill (value suffixes in shared code; BASE against origin/main), and 39 of its 65 guidance bullets are now carried by a check or the style section.</div>

<h2>1. What Wade comments on: comments per check</h2>
<p>Each bar is one check of version 2. The length is the number of Wade comments the check was derived from (273 texts classified; 35 are answers, praise or self-notes and belong to no check). Colour is the section of the skill.</p>
<p>{legend}</p>
{''.join(bars)}
<p class="take">Takeaway: the five largest checks (dead symbols, typos, magic literals, debug switches left on, comments that contradict code) are code-hygiene questions; none of them existed in version 1. {new} checks are new, {wid} are widenings of version-1 checks.</p>

<h2>2. Where his inline comments land</h2>
<p>Inline comments by file area, 243 inline comments on the 115 PRs.</p>
{area_bars}
<p class="take">Takeaway: test files (t/) draw 27 of 243 inline comments (11 percent). Version 1 derived 5 of its 13 checks from tests.</p>

<h2>3. How he decides</h2>
<table><tr><th>Top-level comments on the PR</th><th>Final review APPROVED</th><th>Final review COMMENTED</th></tr>{verdict_rows}</table>
<ul>
<li>334 reviews: 100 APPROVED, 234 COMMENTED, 0 CHANGES_REQUESTED. He has never used CHANGES_REQUESTED on another author's PR.</li>
<li>48 of 115 PRs were approved with no text (median 2 files, 39 changed lines) against a median of 7 files and 410 lines for the 67 PRs with comments.</li>
<li>A must-change is a sentence ("before merging", "needs", "Please &lt;verb&gt;") or a withheld approval (16 of 67 commented PRs never got his approval).</li>
<li>Median time from PR creation to his first review: 0.6 days.</li>
<li>Two registers: hand-written short lowercase questions until 2026-08 (median 131 characters, 2 sentences; 115 of 232 top-level texts contain a question mark; 43 carry a suggestion block), and from 2026-09 a long "fact, So consequence, ask" form with file:line citations that matches his disclosed assistant-assisted reviews. Nine texts disclose pasted assistant analysis (first 2026-03-27).</li>
</ul>

<h2>4. Cross-check against codex's version of the skill</h2>
<p>Codex rewrote its copy (<code>~/.codex/skills/wade-code-review</code>, 2026-10-06 10:26 UTC) from the same record: 11 KB of prose guidance in five priority groups plus a review-history reference with 48 cited comments. Two agents checked it against the corpus.</p>
<table><tr><th>Codex claim that contradicts or qualifies the old Claude skill</th><th>Verdict</th><th>Consequence in version 2</th></tr>
<tr><td>"Wade never reviews formatting or benchmark methods" is wrong</td><td>partly: 1 formatting comment and 1 measurement request in 269 texts</td><td>Style section says "rarely" and names the two ids</td></tr>
<tr><td>Do not invent an owner-approval gate from file authorship (check 12)</td><td>partly: the one request rests on the commit's origin; the placement half alone matches 57 of 115 PRs</td><td>Check 12 keeps both halves and states n = 1</td></tr>
<tr><td>Commit count alone does not justify a squash</td><td>holds: 1 squash request in 334 reviews</td><td>Check 11 unchanged, precedent added</td></tr>
<tr><td>Value suffixes accepted in kernel files do not extend to shared code</td><td>holds, refutes "never a finding"</td><td>Check 13 widened; the shared-code idiom is a non-blocking nit (6021333114)</td></tr>
<tr><td>BASE must come from the PR's base branch, not origin/main</td><td>holds: 42 of 115 PRs targeted another branch</td><td>Setup and every procedure use the PR's baseRefOid</td></tr>
<tr><td>Approval coexists with follow-ups; 0 CHANGES_REQUESTED</td><td>holds</td><td>Verdict calibration section</td></tr>
<tr><td>Pasted assistant text is attributed material</td><td>holds for 9 disclosed cases; PR 4557 Insufficient data</td><td>"Attributed text" defined; checks built on pastes say so</td></tr>
<tr><td>48 cited comments support the review-history wording</td><td>40 hold, 7 partly, 1 not in corpus (Wade's own PR)</td><td>Only verbatim-backed citations reused</td></tr>
</table>
<p>Evidence map of codex's 65 guidance bullets: 58 backed by Wade comments, 2 by pasted assistant text only, 5 by none. 39 were marked worth adopting; the critic traced each to a version-2 check or the style section, with three partial gaps folded in (before/after measurement request, reading the full discussion including later replies, boundary-case list for queue tests).</p>
<p>What the two versions still do differently: codex's skill is principle-level prose ("trace what the changed code reads, owns, waits for"), the Claude skill gives each check a grep-level trigger, numbered commands and a do-not-fire list tested against the diffs of PRs Wade approved in silence. Codex's review-history.md is a better short reading list of his precedent; version 2 cites the same ids inside each check instead.</p>

<h2>5. Method</h2>
<ol>
<li>Corpus: union of <code>gh search prs --reviewed-by</code> and <code>--commenter</code> for Wado-posi across positron-ai, minus his own PRs: 115 PRs, 334 reviews, 243 inline and 11 conversation comments, every endpoint paginated. One digest per PR with hunks and replies.</li>
<li>30 classifier agents labelled all 273 texts (concern, fit to the 13 old checks, detection sketch, evidence read, form, severity, author outcome). 202 texts fit none of the old checks.</li>
<li>3 taxonomists (by mechanism, by evidence, by delta to the skill) and 1 judge merged them into 35 clusters.</li>
<li>Per cluster: 1 drafter, 3 refuters (precision on 15 silently approved PR diffs, verbatim facts at the cited commit, executability on an originating PR), 1 tightener. All 32 drafted checks survived. 6 quotes that were author replies were removed.</li>
<li>1 critic (overlaps, codex coverage, contradictions), 32 compressors, 1 style writer, 3 plain-English checkers, 1 consistency reviewer. 235 agents in total (34 + 162 + 33 in three workflows, plus 6 standalone).</li>
</ol>

<h2>6. Words used here</h2>
<dl class="glos">
<dt>PR</dt><dd>pull request on GitHub.</dd>
<dt>Inline comment, conversation comment, review</dt><dd>a comment on a diff line; a comment in the discussion tab; a submitted review with a state (APPROVED, COMMENTED, CHANGES_REQUESTED).</dd>
<dt>Top-level text</dt><dd>a Wade text that is not a reply to someone else.</dd>
<dt>Check, trigger, do-not-fire</dt><dd>one review question in the skill; the diff pattern that starts it; the cases where it must stay silent.</dd>
<dt>Precision probe</dt><dd>running a check's trigger on the diffs of PRs Wade approved without a word, to count false positives.</dd>
<dt>BASE, HEAD</dt><dd>the merge base against the PR's target branch; the reviewed commit.</dd>
<dt>Attributed text</dt><dd>analysis Wade pasted from an AI assistant (Claude, "CC", GPT) and framed with his own sentence.</dd>
</dl>
</main></body></html>'''
assert all(ord(ch) < 128 for ch in page), 'non-ASCII in page'
open('../../status/Wade-code-review-skill-v2.html', 'w').write(page)
print('written', len(page))
