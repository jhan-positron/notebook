#!/usr/bin/env python3
"""Patch 3 of ../round2-respond-2-issac.html: the results of the eleven steps after jhan's go of 2026-11-24.

Each replacement asserts that its old text occurs once. Kept as a record. Do not run it again.
Usage: apply_page_patch3.py PAGE.html
"""
import sys

page = sys.argv[1]
s = open(page, encoding='utf-8').read()
RUN = 'https://github.com/positron-ai/tron/actions/runs/'
R26 = '<a class="ref" href="#R26">[R26]</a>'
R27 = '<a class="ref" href="#R27">[R27]</a>'
R28 = '<a class="ref" href="#R28">[R28]</a>'
R20 = '<a class="ref" href="#R20">[R20]</a>'

DONE = f'''<h3 id="done">After your go</h3>
<p>You answered "go" on 2026-11-24 at 10:35 PST. All eleven steps of <a href="#steps">section 6</a> are done, and no check stopped them {R26}.</p>
<div class="scrollx"><table>
<tr><th style="width:4%">#</th><th style="width:24%">Step</th><th>Result on 2026-11-24</th></tr>
<tr><td class="num">1</td><td>Fast-forward</td><td>The branch <code>jhan-amx-kvmul16</code> is at <code>90a9110be5</code>, and its git tree is <code>d6c77bd315</code>.</td></tr>
<tr><td class="num">2</td><td>Push without force</td><td>Pushed at 18:36 UTC (10:36 PST). GitHub then showed PR 5606 as merged, so the hypothesis of section 6 holds.</td></tr>
<tr><td class="num">3</td><td>CMake workflow, started by hand</td><td><a href="{RUN}45461357302">Run 45461357302</a>, started 8 seconds after the push.</td></tr>
<tr><td class="num">4</td><td>Both CI runs</td><td>The required lane, <a href="{RUN}45461355215">run 45461355215</a>, passed in 38 minutes. The CMake workflow passed in 35 minutes.</td></tr>
<tr><td class="num">5</td><td>Test host log and the other checks</td><td>The Test host log of the required lane lists <code>t_amx_dispatch_dtype</code> and <code>t_amx_numerics</code> as passed. Its last line says 106 passed, 0 skipped, 0 failed. No check of the new head failed.</td></tr>
<tr><td class="num">6</td><td>Delphi runner for test-host</td><td>Attempt 1 ran on andoria-09-0, an AMD runner. One rerun was enough: attempt 2 ran on delphi-3bd6-0, a Xeon 6962P runner. It passed 106 of 106 tests in 2.3 minutes.</td></tr>
<tr><td class="num">7</td><td>Reviews, threads and comments again</td><td>The automated review of the new head arrived 4 minutes after the push and found no issues {R28}. It marked its own 2 threads of 2026-11-20 as resolved. No new finding came.</td></tr>
<tr><td class="num">8</td><td>Live description</td><td>Unchanged since the saved copy, so the edit went on.</td></tr>
<tr><td class="num">9</td><td>Description edits</td><td>Saved at 19:24:05 UTC with the seven replacements and 1,998 words {R27}. The read-back equals the text sent.</td></tr>
<tr><td class="num">10</td><td>Reply</td><td>Posted at 19:24:15 UTC (11:24 PST) as <a href="https://github.com/positron-ai/tron/pull/5022#issuecomment-7142046348">conversation comment 7142046348</a>. The read-back equals the text sent.</td></tr>
<tr><td class="num">11</td><td>Requested reviewers</td><td>Isaac is still on the list.</td></tr>
</table></div>
<ul>
<li>The review state is still "changes requested", and 2 of 28 threads are marked resolved. The state changes when Isaac reviews again.</li>
<li>The head has 48 checks: 31 passed, 16 skipped and 1 with the result "neutral". The neutral one is the automated review.</li>
<li>Of the skipped checks, 12 belong to the run of draft PR 5606 at the same commit. The other 4 are benchmark jobs.</li>
<li>The required lane built the merge of <code>90a9110be5</code> with main at <code>0e37695a12</code> {R26}. That closes the first two gaps of section 9.</li>
<li>The CMake workflow built the head itself, with <code>TRON_AMX_DISPATCH</code> ON.</li>
<li>Before step 9, three checker agents compared both final texts with the CI logs {R28}. They checked 60 claims and found no false statement.</li>
<li>Section 6 estimated 33 minutes for the required lane, 41 for the CMake workflow and 16 for the automated review. The measured values are 38, 35 and 4 minutes.</li>
<li>The go did not cover a new review request, a registry refresh or the merge. None of them was done.</li>
<li>The five findings of the <a href="#openfindings">second table of section 6</a> stay open.</li>
</ul>

<p>The table below shows the state before your go. The rest of the page is the proposal as you approved it.</p>
'''

VALUES = '''<div class="scrollx"><table>
<tr><th style="width:30%">Name in capitals</th><th>Value from the CI runs of 2026-11-24</th></tr>
<tr><td>RUN_ID_NIX</td><td>45461355215, the run of the required lane</td></tr>
<tr><td>RUN_ID_CMAKE</td><td>45461357302, the run of the CMake workflow</td></tr>
<tr><td>N_PASS and N_TOTAL</td><td>106 and 106 tests</td></tr>
<tr><td>RUNNER_NAME</td><td>delphi-3bd6-0</td></tr>
<tr><td>CPU_MODEL</td><td>6962P</td></tr>
<tr><td>ATTEMPT_N</td><td>2</td></tr>
</table></div>
'''

REFS = f'''<li id="R26"><strong>[R26]</strong> CI runs at the new head <code>90a9110be5</code> on 2026-11-24. The records are in <code>RES/after-go/</code>.
<ul>
<li>Required lane, <a href="{RUN}45461355215">run 45461355215</a>, 18:36:27 to 19:14:38 UTC: <code>nix-run-45461355215.json</code> lists 15 jobs as passed and 2 benchmark jobs as skipped.</li>
<li><code>nix-test-host.log:414-415</code> holds the two lines of the AMX tests, and <code>:435</code> the totals. Line 2 names the runner andoria-09-0.</li>
<li><code>nix-test-host.log:118</code> shows the checkout of the merge commit <code>5cc51e69ab</code>, the merge of <code>90a9110be5</code> into <code>0e37695a12</code>.</li>
<li><code>.github/workflows/gcp-nix.yml:15</code> also starts the required lane for the merge queue.</li>
<li>CMake workflow, <a href="{RUN}45461357302">run 45461357302</a>, 18:36:28 to 19:11:47 UTC for attempt 1: <code>cmake-run-45461357302-attempt1-jobs.json</code> and <code>cmake-run-45461357302-attempt2-jobs.json</code>.</li>
<li><code>cmake-test-host-attempt2.rest.log:2</code> names the runner, <code>:78</code> the CPU model, and <code>:784</code> the totals. Attempt 2 of test-host ran from 19:12:36 to 19:14:52 UTC.</li>
<li><code>cmake-build-attempt1.log:4899</code> holds <code>-DTRON_AMX_DISPATCH=ON</code>.</li>
<li><code>checks-head-90a9110be5.tsv</code> lists the 48 checks, and <code>workflow-runs-head-90a9110be5.tsv</code> the 6 workflow runs of the commit.</li>
</ul></li>
<li id="R27"><strong>[R27]</strong> What was saved on GitHub on 2026-11-24.
<ul>
<li>The reply: <a href="https://github.com/positron-ai/tron/pull/5022#issuecomment-7142046348">issuecomment-7142046348</a>. Saved copies: <code>RES/after-go/reply.final.md</code> and <code>posted-reply.json</code>.</li>
<li>The description: <code>RES/after-go/pr5022-body.final.md</code> and <code>posted-body.json</code>. The text before the edit is <code>pr5022-body-live-before-edit.md</code>.</li>
<li>The filled values are in <code>RES/after-go/values.json</code>.</li>
<li>The scripts <code>fill_ci_results.py</code> and <code>post_after_go.py</code> are in <code>MG/round2-tools/</code>.</li>
</ul></li>
<li id="R28"><strong>[R28]</strong> Reviews and checks after the push.
<ul>
<li>The automated review of <code>90a9110be5</code>: <a href="https://github.com/positron-ai/tron/pull/5022#pullrequestreview-6045211710">review 6045211710</a> of 2026-11-24 18:40:33 UTC. Its text is in <code>MG/pr5022-watch/changes/20261124T1840Z.md</code>.</li>
<li>The three checker agents: <code>wf_21f8409a-358/journal.jsonl</code> in the folder of {R20}. They checked 26, 15 and 19 claims.</li>
</ul></li>
</ol>

</main></body></html>'''

REPL = [
 ('nav', '<a href="#short">Short version</a><a href="#words">',
  '<a href="#short">Short version</a><a href="#done">After the go</a><a href="#words">'),
 ('short version',
  '<div class="short"><p>Isaac, the reviewer of pull request 5022, has one request left, and he wrote the fix for it himself. I tested his two commits on our test server, and all 20 test runs pass. I recommend taking both commits unchanged.</p></div>\n',
  '<div class="short"><p>Isaac, the reviewer of pull request 5022, had one request left, and he wrote the fix for it himself. After your go of 2026-11-24 the branch holds his two commits, both CI runs pass, and the reply is posted. His review stays at "changes requested" until he reviews again.</p></div>\n\n' + DONE),
 ('state table header', '<th>State on 2026-11-24, 10:20 PST</th>', '<th>State on 2026-11-24, 10:20 PST, before your go</th>'),
 ('ask box',
  '''<div class="ask"><p>Nothing is pushed or posted before you approve. I need one answer from you: go, or a different choice in the two tables of <a href="#choices">section 6</a>.</p>
<ul>
<li>One go covers the <a href="#steps">eleven steps of section 6</a>, with the reply and the description edits of section 7.</li>
<li>It does not cover a reply to a new finding, a fix after a failed CI run, or the merge.</li>
</ul></div>''',
  '''<div class="ask"><p>You gave the go on 2026-11-24 at 10:35 PST, and it is carried out. I need no answer from you now.</p>
<ul>
<li>The go covered the <a href="#steps">eleven steps of section 6</a>, with the reply and the description edits of section 7.</li>
<li>The next event is Isaac's new review. A reply to a new finding needs a new go.</li>
<li>The merge is your step, and the go did not cover it.</li>
<li>The hourly cloud task that watches PR 5022 still runs. Please turn it off after the merge.</li>
</ul></div>'''),
 ('section 7 intro',
  '''<p>The reply is posted after both CI runs pass. Seven names in capitals will be replaced by CI results.</p>
<ul>
<li>The reply uses five of them: RUN_ID_NIX, RUN_ID_CMAKE, N_PASS, N_TOTAL and RUNNER_NAME.</li>
<li>The description edits use these five and two more: CPU_MODEL and ATTEMPT_N.</li>
<li>Steps 4 and 6 of section 6 collect the values.</li>
</ul>
''',
  f'''<p>The reply was posted on 2026-11-24 at 19:24 UTC, after both CI runs passed {R27}. The block below is the draft as you approved it. Its seven names in capitals were replaced by CI results.</p>
<ul>
<li>The reply uses five of them: RUN_ID_NIX, RUN_ID_CMAKE, N_PASS, N_TOTAL and RUNNER_NAME.</li>
<li>The description edits use these five and two more: CPU_MODEL and ATTEMPT_N.</li>
<li>Steps 4 and 6 of section 6 collected the values.</li>
</ul>
''' + VALUES),
 ('reply label', "<div class=\"lbl\">Reply to Isaac's comment (draft, not posted)</div>",
  "<div class=\"lbl\">Reply to Isaac's comment (the draft, posted with the CI results)</div>"),
 ('description intro',
  'The live description has 1,996 words <a class="ref" href="#R18">[R18]</a>. It must stay under 2,000 words <a class="ref" href="#R19">[R19]</a>. With the seven replacements it has 1,998 words, counted by a script.',
  'The description had 1,996 words before the edit <a class="ref" href="#R18">[R18]</a>. It must stay under 2,000 words <a class="ref" href="#R19">[R19]</a>. The saved description has 1,998 words, counted by a script.'),
 ('word count bullet',
  '<li>Each name in capitals counts as one word. I count again after they are replaced, and I stop at 2,000 words or more.</li>',
  '<li>Each name in capitals counted as one word. The count after the replacement is 1,998 words.</li>'),
 ('attempt bullet',
  '<li>If attempt 1 of the CMake workflow runs on a Delphi runner, row 4 drops the attempt number. The description then has 1,996 words.</li>',
  '<li>Attempt 1 of the CMake workflow ran on an AMD runner. So row 4 keeps the attempt number.</li>'),
 ('gap 1',
  '<li>The required lane has not run the change. The run after the push resolves it.</li>',
  f'<li>The required lane has now run the change. Run 45461355215 passed on 2026-11-24 {R26}.</li>'),
 ('gap 2',
  '<li>That run builds the merge of the new head with main. Main is 14 commits ahead, and no build of that merge exists yet.</li>',
  '<li>That run built the merge of the new head with main at <code>0e37695a12</code>. Main has moved by 1 commit since then. The required lane runs again in the merge queue (the queue that tests a PR before merging).</li>'),
 ('gap AMD class',
  '<li>All our runs are on one Xeon 6962P host. A CI job on an Andoria runner would cover the AMD class.</li>',
  f'<li>Our own runs are on one Xeon 6962P host. In CI, the real cases also passed on andoria-09-0, an AMD runner {R26}.</li>'),
 ('how checked',
  '<li>I checked each new fact of the reviewers against the repository or GitHub before I used it.</li>\n</ul>',
  f'''<li>I checked each new fact of the reviewers against the repository or GitHub before I used it.</li>
<li>After your go, a workflow of 3 checker agents compared the final reply and the final description with the CI logs {R28}. They checked 60 claims and found no false statement.</li>
<li>Their 2 notes concern a count in my instruction and the order of steps 9 and 10. Neither changed a text.</li>
</ul>'''),
 ('references', '</ol>\n\n</main></body></html>', REFS),
]
for name, old, new in REPL:
    assert s.count(old) == 1, f'{name}: old text found {s.count(old)} times'
    s = s.replace(old, new)
open(page, 'w', encoding='utf-8').write(s)
print(f'{len(REPL)} replacements applied to {page}')
