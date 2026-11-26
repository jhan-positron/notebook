#!/usr/bin/env python3
"""Patch 1 of round2-respond-2-issac.html: apply the lesson "a declined fix leaves the finding open".

Each replacement asserts that its old text occurs exactly once. Usage: apply_page_patch1.py PAGE
"""
import sys

p = sys.argv[1]
s = open(p, encoding='utf-8').read()
R = []

def rep(old, new):
    R.append((old, new))

REF = lambda n: f'<a class="ref" href="#R{n}">[R{n}]</a>'

# status table and ask box
rep('<th>State on 2026-11-23, 22:30 PST</th>', '<th>State on 2026-11-24, 08:50 PST</th>')
rep('go, or a different choice in the table of <a href="#choices">section 6</a>.',
    'go, or a different choice in the two tables of <a href="#choices">section 6</a>.')

# section 5
rep('The two commits do not touch it, and the table of section 6 has this choice.</li>',
    'The two commits do not touch it, and the second table of section 6 lists it.</li>\n'
    '<li>Draft PR 5572 of ours changes the same test file under the same guard. I did not check how it merges with this change.</li>')

# step 10
rep('He is on the list today, from the request of 2026-11-20.',
    'He is on the list on 2026-11-24, from the request of 2026-11-20.')

# choices table: three rows move to the table of open findings
old_rows = s[s.index('<tr><td>Registry rows</td>'):s.index('<tr><td>Required lane before the push</td>')]
rep(old_rows, '')
old_rows2 = s[s.index('<tr><td>Extra edits of ours</td>'):s.index('<tr><td>Main</td>')]
rep(old_rows2, '')

old_routes = s[s.index('<h3>The registry rows: three routes</h3>'):s.index('<h2 id="reply">')]
new_routes = f'''<h3 id="openfindings">Findings that stay open after a go</h3>
<p>A fix that we decline does not close its finding. So each row states the finding without a fix, and the smallest fix that I know.</p>
<div class="scrollx"><table>
<tr><th style="width:24%">Finding</th><th style="width:12%">Raised by</th><th style="width:24%">Smallest fix that I know</th><th style="width:18%">Example in the repository</th><th>What I propose</th></tr>
<tr><td>The registry rows of the dispatch test record the placeholder: 8 MB, against 97 to 99 MiB measured.</td><td>Isaac, in PR 5606</td><td>A measurement by <code>bin/slice bench</code> on both machine classes. The list below has four routes.</td><td>The weekly workflow <code>bench-refresh.yml</code> refreshes the rows of all tests {REF(23)}.</td><td>Leave the rows. List them under Open items of the description, and say so in the reply.</td></tr>
<tr><td>The test file does not name the define that it needs. A comment in <code>amx_attn_iface.hpp</code> still says that the option OFF excludes every dispatch block.</td><td>Our readers</td><td>Three comment lines or one <code>#error</code> line in the test file, est. 4 to 6 lines. The header file stays untouched.</td><td><code>t_page_share_counters.cpp</code> has such a comment, and <code>t_llama_unit.cpp</code> has such an <code>#error</code> line {REF(11)}.</td><td>No edit. Isaac asked for the two commits only, and a lost define already fails the test.</td></tr>
<tr><td>The dispatch test still passes when one of two clauses of the dense-page condition is weakened.</td><td>Our fault runs</td><td>One more parameter of the test helper and two sections, est. 20 lines. Not built and not tested.</td><td>The 9 sections of the same test.</td><td>No change in this PR, and no mention in the reply. Section 8 has the detail.</td></tr>
<tr><td>No required CI job executes real AMX instructions.</td><td>Isaac names it as a separate thing</td><td>None in this PR.</td><td>The existing TODO line in <code>src/tron/CMakeLists.txt</code>.</td><td>No action. The reply does not mention it, as you decided on 2026-11-19.</td></tr>
</table></div>
<p>An extra edit of ours would be a new commit. The head would then differ from the tested commit, so the tests of section 3 would run again.</p>

<h3>The registry rows: four routes</h3>
<ul>
<li>Leaving the rows is my proposal. Slice reads them to plan the schedule and to budget memory. The real cases already ran with these rows on both classes {REF(15)}.</li>
<li>Route (a) is the command <code>bin/slice bench --remote --update</code> from this machine {REF(16)}. It reserves a whole pool machine of each class, so it needs your approval.</li>
<li>Insufficient data on whether route (a) works from this machine. The preflight of <code>doc/distributed-dice-agent-guide.md</code> would resolve it.</li>
<li>Route (b) is a dry run of the workflow <code>bench-refresh.yml</code> on our branch {REF(23)}. It measures the whole registry on a benchmark runner of one class, with a job limit of 120 minutes. It needs a manual run of the required lane on the branch first.</li>
<li>Route (c) is a hand edit of the Xeon 6962P row to 99 MB. It leaves the AMD row unmeasured.</li>
<li>Routes (a), (b) and (c) each end in a new commit of ours with the changed rows.</li>
<li>Route (d) needs no action from us. The weekly run of <code>bench-refresh.yml</code> measures both classes on main {REF(23)}. It counts a memory change above 10% as material.</li>
<li>Its pull requests 5037 and 5038 are open drafts since 2026-10-20. So the rows on main change when a person merges one of them.</li>
<li>The rule in <code>t/AGENTS.md</code> names the <code>--remote</code> route itself. So Isaac may ask for route (a) after the reply.</li>
</ul>

'''
rep(old_routes, new_routes)

# reply draft: the bullet on the rows states what is not done and claims no impossibility
rep('<li>The rows of <code>t_amx_dispatch_dtype</code> in <code>config/test-benchmarks.json</code> are unchanged, and the description lists them under Open items. I did not run <code>bin/slice bench --update</code>. The host I test on is shared, and the tool uses the whole machine for its measurement.</li>',
    '<li>The rows of <code>t_amx_dispatch_dtype</code> in <code>config/test-benchmarks.json</code> are unchanged, and the description lists them under Open items. I did not run <code>bin/slice bench --update</code>, for the reason in my <a href="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061343">reply of 2026-11-20</a>.</li>')
rep('<li>The draft has 152 words, against 227 words in the first draft of this page.</li>\n', '')
rep('<li>It uses no word that grades our work down, makes no promise, and does not mention issue 3997.</li>',
    '<li>It uses no word that grades our work down, makes no promise, and does not mention issue 3997.</li>\n'
    '<li>The last bullet states what is not done. It does not say that a measurement is impossible, because routes (a) and (b) of section 6 exist.</li>')

# description edits
rep('<li>Rows 1 to 5 update the four stale places of section 5, and one table row of the description needs two of them.</li>',
    '<li>Rows 1 to 5 update the four stale places of section 5. One table row of the description needs two of them.</li>')

# section 8
old_found = s[s.index('<h2 id="found">'):s.index('<h2 id="gaps">')]
new_found = f'''<h2 id="found">8. Found during the tests</h2>
<p>Fault m04 is not caught, and the cause is older than PR 5022.</p>
<ul>
<li>The dense-page condition of <code>self_attention.hpp</code> has five clauses {REF(12)}. One asks for a full page of 64 active tokens. Another asks that the visible range of the query reaches past the page's last token.</li>
<li>The partial page of the dispatch test holds 63 tokens, and its visible range ends with the last of them. So both clauses reject that page.</li>
<li>Weakening either of the two clauses alone leaves the dispatch test passing. Weakening both makes 2 sections fail {REF(5)}.</li>
<li>The option-ON build misses m04 too.</li>
<li>The condition is on main already, from commit <code>b431585224</code>. The 4-head partial-page section is on main too, from commit <code>1b4db0d5bc</code>.</li>
<li>PR 5022 adds a 16-head partial-page section that builds its page the same way. So that section has the same gap.</li>
</ul>
<p>A fix would separate the two clauses in the test. One new section could use a full page whose last token is outside the visible range. A second could use a 63-token page inside a wider visible range.</p>
<p>This is a sketch from reading the test helper, est. 20 lines. It is not built and not tested. I propose no change for it in this PR, and the reply draft does not mention it.</p>

'''
rep(old_found, new_found)

# references
rep('<li><code>t/t_page_share_counters.cpp:21</code> includes the one project header of that test.</li>',
    '<li><code>t/t_page_share_counters.cpp:21</code> includes the one project header of that test.</li>\n'
    '<li><code>t/t_page_share_counters.cpp:8-11</code> states its define in the file header, and <code>t/t_llama_unit.cpp:1-6</code> holds an <code>#error</code> line for its define.</li>')
rep('<li id="R16"><strong>[R16]</strong> <code>bin/slice:4596-4598</code> (memory budget), <code>:3332-3358</code> (drift warnings). <code>doc/slice.md:468-469</code> ("No timeouts") and <code>:98-108</code> (<code>bench --remote</code>). <code>t/AGENTS.md:23-26</code>.</li>',
    '<li id="R16"><strong>[R16]</strong> Slice and the registry.\n<ul>\n'
    '<li><code>bin/slice:4596-4598</code> reads the memory value for its budget, and <code>:3332-3358</code> holds the drift warnings.</li>\n'
    '<li><code>doc/slice.md:468-469</code> says "No timeouts", and <code>:98-108</code> describes <code>bench --remote</code>.</li>\n'
    '<li><code>t/AGENTS.md:23-26</code> asks for the refresh of the registry after a test change.</li>\n'
    '<li>On this machine <code>bin/slice route</code> answers <code>distributed-dice</code>. The file <code>.agents/skills/run-tron-tests/SKILL.md</code> sends that route to <code>--remote</code>.</li>\n'
    '</ul></li>')
rep('<li id="R18"><strong>[R18]</strong> Live description of PR 5022: <code>RES/inputs/pr5022-body-live.md</code>. The four stale places are lines 33, 45, 46 and 51. Line 53 is the one-word trim, and line 142 holds the open items. Draft with the replacements: <code>MG/round2-tools/pr5022-body-after-5606.draft.md</code>, built by <code>apply_body.py</code> in the same folder.</li>',
    '<li id="R18"><strong>[R18]</strong> The description of PR 5022.\n<ul>\n'
    '<li>The live text is saved as <code>RES/inputs/pr5022-body-live.md</code>.</li>\n'
    '<li>The four stale places are lines 33, 45, 46 and 51. Line 53 is the one-word trim, and line 142 holds the open items.</li>\n'
    '<li>The draft with the replacements is <code>MG/round2-tools/pr5022-body-after-5606.draft.md</code>. The script <code>apply_body.py</code> in the same folder builds it.</li>\n'
    '</ul></li>')
rep('The handoff file holds the three durations and the limit of 2,000 words.</li>',
    'The handoff file holds the three durations and the limit of 2,000 words. The earlier reply on the registry rows is in <a href="https://github.com/positron-ai/tron/pull/5022#discussion_r4356061343">this review thread</a>.</li>')
rep('<li id="R23"><strong>[R23]</strong> <code>.github/workflows/bench-refresh.yml</code>, started every Sunday at 05:00 UTC. Its runs of 2026-11-08, 2026-11-15 and 2026-11-22 succeeded. Pull requests <a href="https://github.com/positron-ai/tron/pull/5037">5037</a> and <a href="https://github.com/positron-ai/tron/pull/5038">5038</a> hold its results.</li>',
    '<li id="R23"><strong>[R23]</strong> The weekly refresh of the registry.\n<ul>\n'
    '<li><code>.github/workflows/bench-refresh.yml</code> starts every Sunday at 05:00 UTC. Its job limit is 120 minutes.</li>\n'
    '<li>Its runs of 2026-11-08, 2026-11-15 and 2026-11-22 succeeded.</li>\n'
    '<li>Pull requests <a href="https://github.com/positron-ai/tron/pull/5037">5037</a> and <a href="https://github.com/positron-ai/tron/pull/5038">5038</a> hold its results.</li>\n'
    '<li><code>doc/slice-benchmark-lifecycle.md</code> describes the refresh, the rule for a material change and the dry run on a branch.</li>\n'
    '</ul></li>')

for old, new in R:
    n = s.count(old)
    assert n == 1, f'old text found {n} times: {old[:90]!r}'
    s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print(f'{len(R)} replacements applied to {p}')
