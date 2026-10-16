#!/usr/bin/env python3
# Generates status/Wade-code-review-skill.html from analysis.json (13 Wade points, verified),
# crosscheck.json (judges of the two skills) and the hand-written tables below. Pure ASCII output.
import json, html, pathlib, re
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent.parent.parent / 'status' / 'Wade-code-review-skill.html'
PR = 'https://github.com/positron-ai/tron/pull/4557'
A = json.load(open(HERE / 'analysis.json'))
CC = json.load(open(HERE / 'crosscheck.json')) if (HERE / 'crosscheck.json').exists() else None
by = {p['analysis']['id'].split('-')[0]: p for p in A['points']}

def e(s): return html.escape(str(s), quote=False)

CHECK = {'W1': 1, 'W4': 2, 'W2': 3, 'W5': 4, 'W6': 5, 'W3': 6, 'L4a': 7, 'L4b': 8, 'L4c': 9, 'S2': 10, 'L3': 11, 'M1': 12, 'S1': 13}
ORDER = ['W1', 'W2', 'W3', 'W4', 'W5', 'W6', 'M1', 'S1', 'S2', 'L3', 'L4a', 'L4b', 'L4c']
WHERE = {'W1': 't/t_llama_unit.cpp:3575', 'W2': 't/t_amx_numerics.cpp:227', 'W3': 'h/tron/tensor/kv_cache_fwd.hpp:43', 'W4': 't/t_llama_unit.cpp:419',
         'W5': 't/t_llama_unit.cpp:3298', 'W6': 't/t_llama_unit.cpp:3293', 'M1': 'h/system/memory.hpp:192', 'S1': 'constants in the diff',
         'S2': 'amx_attn.cpp (ec795fbce8), t/t_heap_v2.cpp', 'L3': 'git log BASE..HEAD', 'L4a': 'PR body, Words row', 'L4b': 'PR body, Verification', 'L4c': 'PR body, Status'}
POINT = {'W1': 'NaN-to-inf and rounding rows pin today\'s conversion with no consumer',
         'W2': 'The only independent layout-formula check sits after available(); at() shares pair_base',
         'W3': 'native_k_view is an alias; "bare pointer is a compile error" holds for V only',
         'W4': 'Structure-only STATIC_REQUIREs; trivial-type checks repeat kv_cache.hpp',
         'W5': 'The poison GENERATE duplicates the four-parity section',
         'W6': 'Section named "preserves poison" asserts the poison is zeroed',
         'M1': 'Global operator new[] overload, no test can catch a regression, needs the owner\'s sign-off',
         'S1': 'Constant names with the value built in',
         'S2': 'Unrelated changes: tile-number constants and the t_heap_v2 alignment check',
         'L3': '20 commits, three rewording one Note; squash',
         'L4a': '"Required CI builds AMX-off" vs cmake-single-platform.yml:355',
         'L4b': 'Results from c12df586b6 / faf8ee42ca, before the merge of main',
         'L4c': 'Assertion arithmetic, UTC timestamps, log paths'}
VERDICT_NOTE = {'W3': 'with a qualification: a bare pointer at the call is rejected for K too; a one-line wrap or a same-shaped view passes',
                'W5': 'same setup, different observation: each GENERATE value reaches a different partner-clearing branch',
                'S1': 'the family ACCUMULATOR_TILE_0..3 has no role stem; the suffix is jhan\'s convention',
                'L4a': 'the sentence names no lane; Wade\'s cited workflow does not gate the PR',
                'L4b': 'unit rows at 96a6220ab6 were present; token identity was pre-merge and unlabelled'}
MISSED = {  # (closest earlier lens, mechanism)
 'W1': ('09-22 tests lens: quoted the test policy for the whole TEST_CASE and asked to verify each expected constant for correctness', 'The policy question ran once per case and the row question asked "is the value correct". The oracle was the design bit table, itself copied from the implementation. The critic recommended adding a second NaN row. The NaN rule of AGENTS.md was in no lens.'),
 'W2': ('09-22 tests lens: handed the finder the author\'s summary "memcpy compare against the independent formula"', 'No lens asked where an assertion executes or whether another check is independent of the helper under test. The CI runner facts (AMD hosts, no AMX) lived in a campaign memory note, never in a review question.'),
 'W3': ('09-22 compile lens: is the alias the same type as page::k\'s view, so the call compiles', 'Type identity was the pass condition. Read the other way it is Wade\'s finding. The design recorded the alias limitation four times. The body sentence was written after the only lens review, and no gate compared body guarantees with the enforcing declarations.'),
 'W4': ('09-22 tests lens: evaluate each STATIC_REQUIRE against the class definitions', 'Every lens asked whether the assertion is true and can fail. Any structure check satisfies both. The design prescribed these checks, so adding them read as conformance. Nobody searched h/ for the same trait on the same type.'),
 'W5': ('09-22 completeness critic: list omissions per design row', 'Both overlapping units were created by one commit answering the critic, after every lens had run. A critic that scores design rows can only add. The duplicate-coverage clauses of AGENTS.md were dropped when the lens paraphrased the policy.'),
 'W6': ('09-22 critic and the design review: both used the name as the address of the test', 'They wrote "append_v preserves poison" while stating that the copy clears the poison. No lens classified SECTION strings as prose that can be wrong. The author agent was told where to edit by name and kept the name.'),
 'M1': ('09-23 design-choice judges (which option is best) and the 09-30 Ben response (is Ben\'s claim about the standard true)', 'The overload arrived 31 hours after the lens review. The judges wrote "maintainer question drafted, NOT posted" and the fold of #4587 into #4557 lost it. Nobody computed the include fan-out (42 direct, 153 transitive of 502 files) or asked whether the owner accepted the placement.'),
 'S1': ('09-23 guide check: is every literal on a + line a named constexpr with the value suffix', 'The rule ran in one direction. ACCUMULATOR_TILE_0..3 were named at jhan\'s instruction after the check. No lens compared the stem with what each tile holds at its use site.'),
 'S2': ('09-23 guide check: examined other literal sets in amx_attn.cpp', 'Every lens asked whether each hunk is correct at HEAD. No lens asked, per commit, which PR claim needs it. Both hunks post-date the lens review.'),
 'L3': ('09-23 rebase review, hygiene lens: are the rebased commits byte-identical and do they compile alone', 'That question rewards keeping fixup commits as separate tested units. main lands PRs by merge commit, so branch commits are permanent. No lens held that fact.'),
 'L4a': ('09-23 plain-English check of the body', 'It checked term definitions. The CI paragraph that named the lane was deleted later the same day and the Words row lost its referent. The response agent checked only whether Wade\'s cited line contains the flag.'),
 'L4b': ('09-29 PR 4596 recipe, docs-exports lens (seven days after the 4557 review)', 'The 09-22 review read no PR body; it did not exist. The memory rule "measurements keep commit id + date" stops at provenance and never asks whether the id is the head.'),
 'L4c': ('09-23 plain-English check', 'It asked whether a sentence is readable. The author-side rules ("every number gets a meaning clause", "cite the run") reward adding evidence and have no companion rule asking whether the number belongs in the document.'),
}
CHECK_Q = {1: 'Name the production reader, format or repository rule that breaks if this exact expected value changes.',
 2: 'If this compile-time assertion flipped, which production line would misbehave, and is it not already protected by a static_assert in its own header?',
 3: 'If the helper that computes the address were wrong, which assertion fails on a CI host that lacks the gated hardware?',
 4: 'Is there a deliberate code break that fails test A but passes test B?',
 5: 'Reading only the name string and the REQUIRE lines, does the name describe the passing state?',
 6: 'For every subject the sentence covers, which enforcement level does the code reach (bare pointer at the call, one-line wrap, nominal type), and does the sentence say so?',
 7: 'Which lanes set or omit this setting, with their triggers, and does the sentence name the lane it means?',
 8: 'For each result row, is the cited commit the reviewed head, or is the row labelled with its older id and the reason it still applies?',
 9: 'If the reviewer could not open the machine, the log or the earlier revision, would deleting this clause change any decision about the head?',
 10: 'If this hunk alone were reverted, would any body sentence stop being true, or any PR symbol stop compiling or stop being tested?',
 11: 'Would a reader of git log main learn anything from this commit that its neighbours in the same PR do not already give?',
 12: 'Can a reader of the PR conversation find an owner\'s sentence that accepts the mechanism, and would a test fail if the mechanism were reverted?',
 13: 'If the value suffix is deleted, does the stem alone tell a reader at the use site which constant this is and why that value?'}
CHECK_NAME = {1: 'Value-pinning rows need a consumer', 2: 'Structure-only compile-time checks', 3: 'A layout-formula check must execute on every CI runner class', 4: 'Same experiment run twice', 5: 'A test name states the enforced contract', 6: 'Guarantee claim versus enforcing declaration', 7: 'CI claims name the lane, the trigger and the configure line', 8: 'Result rows cite the reviewed head', 9: 'PR-body passages a GitHub reader cannot use', 10: 'Hunk-to-claim trace (unrelated changes)', 11: 'Commit history is reviewed content', 12: 'A shared-header change no test observes needs a named owner\'s acceptance', 13: 'Role-bearing constant names (the suffix convention stays)'}

def pill(v):
    cls = {'holds': 'ok', 'partly': 'warn', 'refuted': 'bad'}.get(v, '')
    return f'<span class="pill {cls}">{e(v)}</span>'

rows = ''
for k in ORDER:
    a = by[k]['analysis']
    v = a['verdict']
    note = VERDICT_NOTE.get(k, '')
    rows += f'<tr><td><a href="#{k}"><strong>{k}</strong></a></td><td><code>{e(WHERE[k])}</code></td><td>{e(POINT[k])}</td><td>{pill(v)}{(" " + e(note)) if note else ""}</td><td>{e(a["miss_category"])}</td><td><a href="#c{CHECK[k]}">{CHECK[k]}</a></td></tr>'

miss_rows = ''.join(f'<tr><td><strong>{k}</strong></td><td>{e(MISSED[k][0])}</td><td>{e(MISSED[k][1])}</td></tr>' for k in ORDER)

check_rows = ''.join(f'<tr id="c{n}"><td>{n}</td><td>{e(CHECK_NAME[n])}</td><td>{e(CHECK_Q[n])}</td><td>{", ".join(k for k in ORDER if CHECK[k]==n)}</td></tr>' for n in range(1, 14))

# Wade corpus themes bar chart (counts from the pattern agent, review-type comments only)
themes = A['pattern']['themes']
mx = max(t['count'] for t in themes)
bars = ''
for t in sorted(themes, key=lambda t: -t['count']):
    w = 100.0 * t['count'] / mx
    label = e(t['theme'].split(':')[0].split('(')[0].strip())
    bars += f'<div class="bar"><div class="lbl">{label}</div><div class="track"><div class="fill" style="width:{w:.1f}%"></div><span class="val">{t["count"]}</span></div></div>'

# per-point details
details = ''
for k in ORDER:
    p = by[k]; a = p['analysis']; pr = p.get('probe') or {}
    ev = ''.join(f'<li><code>{e(x["ref"])}</code>: {e(x["quote"][:220])}{(" (" + e(x.get("note",""))[:200] + ")") if x.get("note") else ""}</li>' for x in a['evidence'][:5])
    votes = ', '.join(f'{L}: {"refuted" if v["refuted"] else "ok"}' for L, v in zip(p['lenses'], p['votes']))
    fps = len(pr.get('fires_on_kept', []))
    details += f'''<h3 id="{k}">{k}. {e(POINT[k])} {pill(a["verdict"])}</h3>
<p><strong>Where.</strong> <code>{e(WHERE[k])}</code> at 96a6220ab6. <strong>Miss category.</strong> {e(a["miss_category"])}. <strong>Check.</strong> <a href="#c{CHECK[k]}">{CHECK[k]}</a>.</p>
<p><strong>Evidence (first five of {len(a["evidence"])}).</strong></p><ul>{ev}</ul>
<p><strong>Root cause of the miss.</strong> {e(a["why_missed"]["root_cause"][:900])}</p>
<p class="ev">Refuter votes: {e(votes)}. Precision probe: the untightened procedure reproduced Wade's finding blind ({"yes" if pr.get("reproduces_wade") else "no"}) and fired on {fps} other places, which the tightened wording in the skill drops.</p>'''

# cross-check section
cc_html = '<p>Insufficient data: the judge workflow has not reported yet.</p>'
if CC:
    J = CC['judged']
    # coverage matrix from the coverage judge (first judge whose coverage has the 13 points)
    cov = None
    for j in J:
        if len(j.get('coverage', [])) >= 13: cov = j; break
    mat = ''
    if cov:
        cells = {'full': 'ok', 'partial': 'warn', 'none': 'bad'}
        for c in cov['coverage']:
            mat += f'<tr><td><strong>{e(c["point"])}</strong></td><td class="{cells.get(c["claude"],"")}">{e(c["claude"])}</td><td class="{cells.get(c["codex"],"")}">{e(c["codex"])}</td><td>{e(c["note"][:260])}</td></tr>'
    scores = ''.join(f'<tr><td>{e(L)}</td><td>{j["scores"]["claude"]}</td><td>{j["scores"]["codex"]}</td></tr>' for L, j in zip(['coverage', 'executability', 'precision', 'facts', 'form'], J))
    errs = ''.join(f'<li><strong>{e(x["skill"])}</strong> {e(x["location"])}: {e(x["error"][:240])} [{e(x["evidence"][:160])}]</li>' for j in J for x in j.get('factual_errors', []))
    graft = ''.join(f'<li>{e(x[:300])}</li>' for j in J for x in j.get('codex_strengths_to_graft', [])[:3])
    cw = ''.join(f'<li>{e(x[:300])}</li>' for j in J for x in j.get('claude_weaknesses', [])[:2])
    xw = ''.join(f'<li>{e(x[:300])}</li>' for j in J for x in j.get('codex_weaknesses', [])[:2])
    R = CC['refuted']
    ref_rows = ''.join(f'<tr><td>{e(r["check"].split(" ")[0])}</td><td>{"yes" if r["reproduces_wade"] else "no"}</td><td>{len(r["false_positives"])}</td><td>{len(r["defects"])}</td><td>{e(r["verdict"])}</td></tr>' for r in R)
    eng = CC['english']
    cc_html = f'''<p>Five judges scored both skills on one lens each (0 to 10). Thirteen refuters ran each of my checks on the PR blind. One checker applied the plain-English rules to my SKILL.md. The scores are the judges' numbers on the first draft. Every factual error and wording defect they and the refuters found was then applied: the procedures file was rewritten without the probe narrative, every line citation was re-checked against 96a6220ab6 (54 spot checks, all landing), and the 49 plain-English violations were fixed.</p>
<h3>5.1 Scores by lens</h3>
<div class="tbl"><table><tr><th>Lens</th><th>Claude's skill</th><th>codex's skill</th></tr>{scores}</table></div>
<h3>5.2 Coverage of the 13 points and the 3 reply-correcting facts</h3>
<div class="tbl"><table><tr><th>Point</th><th>Claude</th><th>codex</th><th>Judge's note</th></tr>{mat}</table></div>
<h3>5.3 Factual errors the judges found (both skills)</h3><ul>{errs or "<li>None reported.</li>"}</ul>
<h3>5.4 What codex's skill has that mine lacked (grafted where the refuters agreed)</h3><ul>{graft or "<li>None reported.</li>"}</ul>
<h3>5.5 Weaknesses named by the judges</h3><p>Mine:</p><ul>{cw}</ul><p>codex's:</p><ul>{xw}</ul>
<h3>5.6 Refuters on my 13 checks</h3>
<div class="tbl"><table><tr><th>Check</th><th>Reproduces Wade blind</th><th>False positives found</th><th>Wording defects</th><th>Verdict</th></tr>{ref_rows}</table></div>
<p>Plain-English check of SKILL.md: {eng["count"]} violations found and fixed.</p>'''

SV = ('Wade\'s 13 points on PR 4557 all hold at least partly against the code at 96a6220ab6. '
      'They were missed because every earlier review asked whether the tests and hunks were correct and matched the design, never who depends on them, where they execute, or what a reviewer who only has GitHub needs. '
      'The new skill Wade-code-review asks those questions as 13 executable checks, and three of its verifications change the replies planned for Wade (W5, L4a, M1).')

page = f'''<title>Wade Code Review Skill</title>
<style>
/* Layout: one reading column, light paper, teal accent for links and the Short version, amber for warnings. Single light theme by the user's standing rule. */
:root{{--paper:#fbfaf6;--ink:#1f2a33;--muted:#5b6770;--line:#d8ddd6;--accent:#0b6e7f;--accent-soft:#e3f0f2;--good:#2e7d4f;--warn:#a8691a;--bad:#b3463b;--code:#f0f1ec;--card:#ffffff;--font:system-ui,-apple-system,"Segoe UI",sans-serif;--mono:ui-monospace,Menlo,Consolas,monospace}}
body{{margin:0;background:var(--paper);color:var(--ink);font-family:var(--font);font-size:15px;line-height:1.55}}
.wrap{{max-width:960px;margin:0 auto;padding-block:32px 64px;padding-inline:20px}}
h1{{font-size:26px;font-weight:600;margin:0 0 6px;text-wrap:balance}}
h2{{font-size:19px;font-weight:600;margin:40px 0 12px;padding-top:14px;border-top:1px solid var(--line)}}
h3{{font-size:16px;font-weight:600;margin:24px 0 8px}}
p{{margin:0 0 12px;max-width:78ch}}
.meta{{color:var(--muted);font-size:13.5px;margin-bottom:22px}}
.short{{background:var(--accent-soft);border-left:4px solid var(--accent);padding:12px 16px;margin:0 0 18px;border-radius:0 6px 6px 0}}
.short p{{margin:0}}
code{{font-family:var(--mono);font-size:13px;background:var(--code);padding:1px 5px;border-radius:4px}}
table{{border-collapse:collapse;width:100%;margin:8px 0 16px;font-size:13.5px}}
th,td{{text-align:left;vertical-align:top;padding:7px 9px;border-bottom:1px solid var(--line);min-width:0}}
th{{font-weight:600;color:var(--muted);font-size:12.5px;letter-spacing:0.04em;text-transform:uppercase}}
td.ok{{color:var(--good);font-weight:600}}td.warn{{color:var(--warn);font-weight:600}}td.bad{{color:var(--bad);font-weight:600}}
.tbl{{overflow-x:auto}}
ul,ol{{padding-left:22px;margin:0 0 12px}}li{{margin-bottom:5px;max-width:78ch}}
.pill{{display:inline-block;font-size:12px;font-weight:500;padding:1px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);vertical-align:middle}}
.pill.ok{{color:var(--good);border-color:var(--good)}}.pill.warn{{color:var(--warn);border-color:var(--warn)}}.pill.bad{{color:var(--bad);border-color:var(--bad)}}
.flag{{margin:14px 0 18px;padding:12px 16px;background:#fffdf5;border:1px solid var(--warn);border-radius:6px}}
.flag .lbl{{font-weight:600;color:var(--warn);margin-bottom:6px}}
.ev{{color:var(--muted);font-size:13.5px}}
a{{color:var(--accent)}}
.chart{{margin:12px 0 18px}}
.bar{{display:grid;grid-template-columns:minmax(120px,38%) 1fr;gap:10px;align-items:center;margin:4px 0;font-size:13.5px}}
.bar .lbl{{text-align:right;color:var(--ink);min-width:0}}
.track{{position:relative;height:18px;background:var(--code);border-radius:3px;min-width:0}}
.fill{{height:100%;background:var(--accent);border-radius:3px}}
.val{{position:absolute;left:calc(100% - 100%);top:0;line-height:18px;padding-left:6px;font-variant-numeric:tabular-nums;color:var(--muted);font-size:12.5px}}
.bar .val{{left:auto;right:6px}}
@media (max-width:600px){{.wrap{{padding-inline:16px}}h1{{font-size:22px}}.bar{{grid-template-columns:1fr}}.bar .lbl{{text-align:left}}}}
</style>
<div class="wrap">
<h1>Wade-code-review: what the reviewer caught, why we missed it, and the skill that covers it</h1>
<div class="meta">2026-10-05 &middot; PR <a href="{PR}">#4557</a> at head 96a6220ab6, review <a href="{PR}#pullrequestreview-5420005787">5420005787</a> &middot; skill installed at <code>~/.claude/skills/Wade-code-review/</code> &middot; codex's version at <code>~/.codex/skills/wade-code-review/</code></div>
<div class="short"><p><strong>Short version.</strong> {e(SV)}</p></div>

<p>Words used here: PR 4557 is "Typed KV-cache tensors for VNNI packed V and native K" (branch jhan-kv-typed-tensors). Wade is the second reviewer (GitHub Wado-posi). BASE is main e5fa372c19, the side merged into the branch before the review. A "lens" is one finder prompt of an earlier agent review. The "09-22 review" is the eight-lens workflow of 2026-09-22 (behavior, compile, callers, includes, tests, adversarial, prose, design, then refuters and a completeness critic). AMX is Intel's matrix instruction set; the AMX kernels run only on hosts that have it. A STATIC_REQUIRE is a Catch2 compile-time assertion. Other terms are defined where they first appear.</p>

<h2 id="glance">1. The 13 points at a glance</h2>
<p>Verdicts come from 13 analysis agents, each checked by three refuters (fact, cause, rule) and a precision probe that ran the derived rule blind on the whole PR. Line numbers are at 96a6220ab6.</p>
<div class="tbl"><table><tr><th>Id</th><th>Where</th><th>Wade's point</th><th>Holds?</th><th>Miss category</th><th>Check</th></tr>{rows}</table></div>

<h2 id="flags">2. Three facts that change the planned replies</h2>
<p>The page <code>status/PR4557-respond-Wade-comments.html</code> (2026-10-05) proposed accepting every point. The verification contradicts three of its replies. jhan decides.</p>
<div class="flag"><div class="lbl">W5: the two GENERATE values are not duplicates of each other</div><p>copy_token has two partner-clearing branches for an even destination: andnot for an even source [h/tron/tensor/v_vnni.hpp:359-364] and srli for an odd source [v_vnni.hpp:378-384]. With 2 destination tokens the last copy lands on token 6 from source 4 (even from even). With 3 it lands on token 6 from source 3 (even from odd). Each value observes one branch. The bit-exact section fills all 64 tokens, so its later odd-destination copies overwrite every odd partner and it cannot observe partner clearing. Returning the poison section to one value drops the observation of one branch. The reply should concede the shared setup and keep both values, or move one clearing observation into the bit-exact section.</p></div>
<div class="flag"><div class="lbl">L4a: Wade's cited workflow does not gate the PR, and the replacement row is wrong</div><p>cmake-single-platform.yml has only workflow_dispatch and workflow_call triggers [.github/workflows/cmake-single-platform.yml:5-12 at e5fa372c19]; its caller is publish-deb.yml:68, under its tag or feature-branch gate at lines 64-67. The checks that gate the PR are the GCP Nix lane, which configures without TRON_AMX_DISPATCH (default OFF). So the reviewed sentence was true for the gating lane and wrong only in naming no lane. The row posted after the review ("CI builds AMX-on since PR #4505") is wrong twice: the gating lane builds AMX-off, and the flag entered the legacy workflow in PR #3879 (commit f4889f8072), not #4505.</p></div>
<div class="flag"><div class="lbl">M1: jhan's reply cites a commit that predates Ben's request</div><p>The reply says commit 39a6899 answered Ben's comment-update request (thread 4159939672). 39a6899 is dated 2026-09-23 22:13 PDT. Ben's thread is from 2026-09-29. The 2026-09-24 design record says "maintainer question drafted, NOT posted". The owner's acceptance of the mechanism (a global operator new[] overload in a header that 153 of 502 C++ files include (42 directly)), as opposed to the Note wording, is still not on the PR.</p></div>

<h2 id="why">3. Why we missed them</h2>
<p>Five mechanisms cover all 13 points.</p>
<ul>
<li><strong>Wrong oracle.</strong> The author-side lenses judged the tests against the design document, and the design's bit table and check list were copied from the implementation. Nobody asked, per row, who consumes the value (W1, W4).</li>
<li><strong>A critic that can only add.</strong> The completeness critic walked the design row by row and recommended tests per row. It created the duplicate coverage and the stale section name (W5, W6).</li>
<li><strong>One review, too early.</strong> The only full review ran on 2026-09-22 against the diff. The PR body, the later commits (the overload, the tile constants, the alignment check, the fix commits) and the merge of main came afterwards, and nothing re-ran at the final head (M1, S1, S2, L3, L4a, L4b, L4c).</li>
<li><strong>Known facts not carried forward.</strong> The design records already said the K alias does not enforce the layout, the formula check sits behind a hardware gate, and the maintainer must accept the allocation change. None reached the PR body or a finding (W2, W3, M1).</li>
<li><strong>Truth and readability instead of reader need.</strong> Body passages and commits were checked for being true and plain, never for whether a reviewer who only has GitHub needs them (L4c, L3).</li>
</ul>
<h3>3.1 Per point: the closest earlier lens and the mechanism</h3>
<div class="tbl"><table><tr><th>Id</th><th>Closest earlier lens and what it asked</th><th>Mechanism of the miss</th></tr>{miss_rows}</table></div>

<h2 id="skill">4. The skill</h2>
<p>Installed at <code>~/.claude/skills/Wade-code-review/</code>: SKILL.md (setup, 13 checks, the reviewer's register, the report format), references/procedures.md (the exact commands per check, as tightened by the refuters and the precision probes) and references/pr4557-misses.md (this analysis in short). Each check has a trigger, a procedure, one discriminating question, a false-positive guard and a finding template. The questions:</p>
<div class="tbl"><table><tr><th>#</th><th>Check</th><th>Discriminating question</th><th>Points</th></tr>{check_rows}</table></div>
<p>Two standing decisions are built in. The value-suffix naming convention is jhan's and is never reported (check 13 reports the stem only). When the reviewer has already commented, the same checks run on his comments before any reply: on this PR they correct W5 and L4a.</p>

<h2 id="codex">5. Cross-check with codex's skill</h2>
<p>codex wrote <code>~/.codex/skills/wade-code-review/</code> (SKILL.md, references/pr4557.md) on the same prompt. Its reference note makes four claims beyond Wade's text. All four were verified against the code by a separate workflow (4 verifiers, 8 refuters): the K pointer constructor is explicit, so a direct bare-pointer call is rejected for K too; the two poison GENERATE values reach different clearing branches; the misses were known at design time and not carried forward; the memory.hpp comment itself declares the change untestable. My skill incorporates all four.</p>
{cc_html}

<h2 id="pattern">6. What Wade comments on, from 480 inline comments</h2>
<p>One agent read every inline comment Wade left on positron-ai/tron (480 comments on 117 PRs, 2025-09-25 to 2026-10-05, fetched with the GitHub API) and tagged the 196 review-type remarks by theme. Counts below are those tags. The remaining 284 are annotations on his own PRs, replies, or adjudications of bot findings.</p>
<div class="chart">{bars}</div>
<p>Takeaway: half of his review remarks are about text that is wider or staler than the code, dead code, and duplication. He does not comment on formatting, benchmark method, the C++ guide, or kernel arithmetic line by line. His finding shape is a fact, then "So" and the consequence, then one ask, with what to keep named in every drop request.</p>

<h2 id="gaps">7. What is not verified</h2>
<ul>
<li>The skill has not yet been run end to end by a fresh agent on a PR other than 4557. The precision probes ran each check's procedure on PR 4557 only.</li>
<li>The Wade corpus theme counts are one agent's tagging; a second tagger was not run.</li>
<li>Whether Ben accepted the memory.hpp mechanism elsewhere (Slack, a call) is unknown; only the PR conversation was read.</li>
</ul>

<h2 id="sources">8. Sources</h2>
<ul>
<li>GitHub: review 5420005787 and its seven inline comments, jhan's comment 6008399647 and reply 4190971320, the PR body as edited at 2026-10-05T19:44:11Z (the version Wade read, from the body edit history), read 2026-10-05.</li>
<li>Code at 96a6220ab6 and main e5fa372c19 in the worktree <code>~/workspace/ai-runs/tron-issue4525</code>.</li>
<li>Earlier reviews: the 2026-09-22 workflow prompts and results, status/pr4557-guide-checks.html, status/PR4557-respond-2-Ben.html, the four standing skills.</li>
<li>Workflows of this analysis: wf_f8254d84-b13 (66 agents), wf_29b24ce0-20d (12 agents), wf_ede30b01-af0 (19 agents). Inputs, outputs and scripts: <code>issue4525/exec/wade-20261005/skill/</code>. Generator: <code>gen_report.py</code> in the same folder.</li>
</ul>
<h3>Per-point detail</h3>
{details}
</div>
'''
assert all(ord(c) < 128 for c in page), sorted({c for c in page if ord(c) >= 128})[:10]
OUT.write_text(page)
print('written', OUT, len(page), 'bytes')
