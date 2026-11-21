#!/usr/bin/env python3
"""Page pass 13 (main session, 2026-11-20, after the go): status box "pushed, CI passed, replies posted", two cards
(B1, B2) with draft replies to the automated review of the new head, and the references R57 to R63. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p, encoding='utf-8').read(); orig = s
RUN = 'https://github.com/positron-ai/tron/actions/runs/'
PR = 'https://github.com/positron-ai/tron/pull/5022'

def ref(n):
    return f'<a class="ref" href="#R{n}">[R{n}]</a>'

def once(old, new):
    """Replace old by new; do nothing when new is already there."""
    global s
    if new in s:
        return 0
    assert s.count(old) == 1, ('not found exactly once', old[:70], s.count(old))
    s = s.replace(old, new)
    return 1

todo = 0
# A. the line under the title
todo += once('tests at the final head done on 2026-11-20 &middot; nothing posted</p>',
             'tests at the final head done on 2026-11-20 &middot; pushed and posted on 2026-11-20 (head ddf843ad97, review 5997064669) &middot; two replies to an automated review wait for your go</p>')
# B. navigation
todo += once('<a href="#open4">Status and the go</a>', '<a href="#open5">Status</a><a href="#bot">Automated review</a>')
# C. Short version
todo += once('You made the six decisions on 2026-11-19 and answered the open points in three rounds, and every reply below now reads as a report of what the final head contains. The tests at the final head ran on the server delphi-3b35 on 2026-11-20 and all 14 runs ended as wanted, so one thing is needed from you: the go to commit, push and post.</p></div>',
             'After your go of 2026-11-20 the final head ddf843ad97 is pushed, both CI workflows pass on it, and the PR description, the 26 thread replies and the combined reply are posted. One thing is needed from you: the go for two more replies (cards <a href="#B1">B1</a> and <a href="#B2">B2</a>), which answer an automated review of the new head, and after them I re-request Isaac\'s review.</p></div>')
# D. the old status box becomes history
todo += once('<div class="open" id="open4"><p><strong>Status 2026-11-20 05:55 PST: the tests at the final head are in.</strong> One thing is needed from you: the go to commit, push and post.</p>',
             '<div class="open done" id="open4"><p><strong>Status 2026-11-20 05:55 PST: the tests at the final head are in.</strong> You answered at 08:50 PST: "go". The steps listed below are done, except the re-request of the review (see the status box above).</p>')
todo += once('<p>If a CI run fails, I stop and report before I post anything. The replies below hold five placeholders until then: ⟦HEAD⟧, ⟦NIXRUN⟧, ⟦CMAKERUN⟧, ⟦RUNNER⟧ and ⟦ISSUE⟧.</p>\n</div>',
             '<p>No CI run failed. The five placeholders of the replies (head, two run ids, runner and issue number) are filled since 2026-11-20 09:42 PST.</p>\n</div>')

# E. the new status box and the two cards, placed before the old status box
BOX = f'''<div class="open" id="open5"><p><strong>Status 2026-11-20 10:05 PST: pushed, CI passed, replies posted.</strong> One thing is needed from you: the go for two more replies, cards <a href="#B1">B1</a> and <a href="#B2">B2</a>. They answer an automated review that arrived on the new head.</p>
<ul>
<li><strong>Commits and push.</strong> The branch <code>jhan-amx-kvmul16</code> is at ddf843ad97 since 08:52 PST. It holds two new commits: the merge of main 3bea58b788 (commit 1bda322822) and the review commit (ddf843ad97). The tree of the head equals the tested tree c114b85944. The push was a fast-forward, without force {ref(57)}.</li>
<li><strong>CI at ddf843ad97: all three runs passed</strong> {ref(58)}.
<div class="scrollx"><table class="grid">
<tr><th style="width:24%">Workflow</th><th style="width:14%">Run</th><th>Result</th></tr>
<tr><td>GCP Nix (the default, required workflow; option OFF)</td><td class="num"><a href="{RUN}44777709823">44777709823</a></td><td class="on">Passed. The job Test host ran on delphi-3bd6-0 and passed 106 tests, among them <code>t_amx_numerics</code>, <code>t_amx_dispatch_dtype</code> and <code>t_llama_unit</code>. The build log names neither the option nor the kernel file.</td></tr>
<tr><td>Slice tests</td><td class="num">44777709810</td><td class="on">Passed.</td></tr>
<tr><td>CMake and CTest (the legacy workflow; option ON; started by hand)</td><td class="num"><a href="{RUN}44777748892">44777748892</a></td><td class="on">Passed. The build ran on andoria-ee10-0 with <code>-DTRON_AMX_DISPATCH=ON</code> and compiled <code>kernels/amx_attn.cpp</code>. Attempt 1 of the job test-host ran on andoria-ee10-0, an AMD EPYC 9654: 106 tests passed, and the QK and PV kernel cases skip on that CPU. I reran only that job. Attempt 2 ran on delphi-3bd6-0, a Xeon 6962P with AMX in its CPU flags: 106 tests passed. The job test-fpga passed on andoria-02-0.</td></tr>
</table></div>
A passing job log has one line per test executable. So the log of attempt 2 does not list the QK and PV cases one by one.</li>
<li><strong>Follow-up issue.</strong> Filed as <a href="https://github.com/positron-ai/tron/issues/5511">#5511</a> {ref(59)}.</li>
<li><strong>PR description.</strong> Edited at 09:43 PST. It has 1,996 words. The description as it was before the edit is saved {ref(59)}.</li>
<li><strong>Comment on #5021.</strong> Posted at 09:43 PST {ref(59)}.</li>
<li><strong>Replies.</strong> Posted at 09:50 PST as one review, <a href="{PR}#pullrequestreview-5997064669">review 5997064669</a>: the 26 thread replies, and the combined reply as the review body. GitHub keeps such a review invisible to others until its last step. Before that step I read the 26 replies back and compared each one with the text sent {ref(59)}.</li>
<li><strong>Texts that changed after you read them.</strong> Each change keeps a text true at the new head.
<ul>
<li>Replies I9 and I12. I counted the instructions in the object of the final head. The 16-head pack holds 512 <code>vpextrw</code> stores, and the 16-head QK kernel holds 40 <code>vshuff64x2</code>, as Isaac counted. Both replies said "not reproduced" before.</li>
<li>Replies I1, I3, I15, I20 and I23. Where they say "now at line N", they give the line numbers of ddf843ad97.</li>
<li>Reply I4. "pack&lt;16&gt;" is written as "the 16-head pack".</li>
<li>The combined reply and reply I7. The runner sentence names both attempts of the test-host job. One more sentence says that both attempts pass all 106 host tests. The combined reply also says that the job log has one line per test executable.</li>
<li>Issue #5511, two additions to the draft you approved. The word list says where the transposing store lives after this PR. Item 2 names the plan from PR #3879 and asks for the share of calls without a dense page for Muse Glimmer. Reply I4 says that the issue holds both.</li>
<li>PR description. The row of the legacy workflow reads "Run 44777748892, test-host on runner delphi-3bd6-0 (Xeon 6962P, attempt 2)" and "The build and both test jobs pass. test-host: 106 of 106 tests pass."</li>
</ul></li>
<li><strong>Side effect of the push.</strong> GitHub requested reviews from three teams: tron-ci, tron-ingest and tron-core. The file <code>.github/CODEOWNERS</code> of main names them as owners of the changed paths {ref(62)}.</li>
<li><strong>Not done: the re-request of Isaac's review.</strong> I hold it until the two comments of the automated review are answered.</li>
</ul>
<p>The rows "Before posting" in the cards below describe the state before 09:50 PST.</p>
</div>
<h2 id="bot">Automated review of the new head: 2 comments, 2 draft replies</h2>
<p class="sub">An automated reviewer (<code>claude[bot]</code>) commented on ddf843ad97 at 09:08 PST, 16 minutes after the push {ref(60)}. Its review body says: "Findings marked &#x1F7E1; are optional suggestions and need no follow-up push." Neither draft reply is posted.</p>
<div class="card" id="B1"><div class="head"><span class="id">B1</span><a class="loc" href="{PR}#discussion_r4645384790">t/CMakeLists.txt:623-625</a><span class="badge" style="background:#b91c1c">red finding</span></div>
<div class="pt"><strong>Four failed assertions would exit with code 4 and be reported as a skip</strong></div>
<div class="quote">A broken AMX transpose or Q packer can now show up as "skipped" instead of "failed" on the Granite Rapids runner, the only host that runs these kernels. Catch2 v3.7.1 exits with the count of failed assertions, so exactly 4 failed REQUIREs gives exit 4. The new SKIP_RETURN_CODE 4 maps that to a skip.</div>
<div class="row"><div class="k">The bot's point</div><div>It asks to remove <code>SKIP_RETURN_CODE 4</code>, the label <code>skip_return_code_4</code> and both <code>"skip_return_codes":[4]</code> entries of the registry. Those are the changes that Isaac asked for in I26 and I25.</div></div>
<div class="row"><div class="k">Checked</div><div>Refuted, by the source and by a run {ref(61)}. Catch2 v3.7.1 is the release that standardised the exit codes: a failed assertion always exits with 42, and 4 means only that every selected case was skipped. The count of failed assertions was the exit code up to v3.7.0. I ran the bot's own trigger on delphi-3b35 (our CPUs only): one broken line in stage 1 of the transpose. With AMX, <code>t_amx_numerics</code> then has exactly 4 failed assertions and exits with 42. Under the kill switch it has 2 failed assertions and exits with 42. ctest, which applies <code>SKIP_RETURN_CODE 4</code>, reports "Failed". After the run the line was restored: the tree hash equals the final head again, and the test binary has the same sha256 as before. <span class="sub">(claim refuted)</span></div></div>
<div class="row"><div class="k">Action</div><div>answer only. No code change, so ddf843ad97 stays the final head.</div></div>
<div class="reply"><div class="lbl">Reply (draft, not posted)</div><p>The mapping stays. Catch2 v3.7.1 does not exit with the count of failed assertions.</p>
<p>v3.7.1 standardised the exit codes. A run with a failed assertion always exits with 42, and 4 means only that every selected case was skipped [catch_session.cpp:37, :39, :350-356 of the pinned source]. Its release notes for 3.7.1 say "Assertion failures are now always 42". Both builds fetch that archive by hash [cmake/versions.cmake:26-27; t/CMakeLists.txt:5-6; flake.nix:1056-1058]. The exit code that counts failed assertions is the behaviour up to v3.7.0.</p>
<p>I ran your trigger at this head on a Granite Rapids host (delphi-3b35). The break: stage 1 of the transpose reads <code>_mm512_unpackhi_ps(r0, r1)</code> where it must read <code>_mm512_unpacklo_ps(r0, r1)</code>.</p>
<ul><li><code>gen/t_amx_numerics</code> with AMX: the transpose and QK cases fail, with exactly 4 failed assertions. The exit code is 42.</li><li>The same under <code>TRON_AMX_DISABLE=1</code>: 2 failed assertions, 2 cases skipped, exit code 42.</li><li><code>ctest -R '^t_amx_numerics$'</code>, which applies <code>SKIP_RETURN_CODE 4</code>: <code>***Failed</code>, and ctest exits with 8.</li></ul>
<p>Slice reports every exit code other than 0 and the listed skip codes as failed [bin/slice:1208-1213]. So ctest and Slice both report four failed assertions as a failure.</p></div></div>
<div class="card" id="B2"><div class="head"><span class="id">B2</span><a class="loc" href="{PR}#discussion_r4645384802">t/t_amx_dispatch_dtype.cpp:364-384</a><span class="badge" style="background:#4b5563">optional</span><span class="tag dec">D1</span></div>
<div class="pt"><strong>The new kv_mul-16 sections never run on pull requests</strong></div>
<div class="quote">The new kv_mul-16 tests never run on PRs, so a regression in Glimmer's AMX dispatch or kernels merges unnoticed. Every new 16-head and 32/2-head section sits under #ifdef TRON_AMX_DISPATCH, including the fake-kernel dispatch sections that need no AMX hardware. [...] AGENTS.md says a test that does not run in a required CI suite must not be committed. Fix: build these sections in a required suite, for example by turning TRON_AMX_DISPATCH ON in the gcp-nix.yml build.</div>
<div class="row"><div class="k">The bot's point</div><div>The same point as Isaac's T1 and I7, which decision D1 covers. The bot marks it optional.</div></div>
<div class="row"><div class="k">Checked</div><div>The facts are right. The sections sit under the guard [t/t_amx_dispatch_dtype.cpp:56], and only the legacy workflow sets the option [cmake-single-platform.yml:355]. The test policy of the repository says: "A test that does not execute in CI must not be committed, except in extremely rare cases explicitly approved by the user. Agents may not decide that an exception applies." {ref(63)}. So this point is yours to decide. You decided it on 2026-11-19: the flag stays out of this PR, and the legacy workflow runs before the merge (cards <a href="#D1">D1</a> and <a href="#CI">CI</a>). The draft states that as your position. The test file was behind the guard before this PR. <span class="sub">(claim confirmed; the decision is made)</span></div></div>
<div class="row"><div class="k">Action</div><div>answer only</div></div>
<div class="reply"><div class="lbl">Reply (draft, not posted)</div><p>The facts are right. No workflow that a pull request triggers builds with <code>TRON_AMX_DISPATCH</code>, so these sections run only in the legacy workflow. The thread at src/tron/CMakeLists.txt:216 has the same point, and my reason for keeping the flag out of this PR: with it ON, every eligible model test of the required lane would run the AMX kernels on an Intel runner and the AVX path on an AMD runner. That changes CI for every pull request.</p>
<p>The test file was behind the guard before this PR. The new sections are the ones the review asked for (threads at t/t_amx_dispatch_dtype.cpp:143, :209 and :305). I accept for this PR that they run in the legacy workflow only.</p>
<p>What ran at this head:</p>
<ul><li>The legacy workflow, which builds with the option ON: run <a href="{RUN}44777748892">44777748892</a>. Its test-host job passes all 106 host tests on an AMD runner (attempt 1) and on a Granite Rapids runner (attempt 2). <code>t_amx_dispatch_dtype</code> is one of them.</li><li>The new transpose case sits outside the guard, so the required lane runs it.</li></ul></div></div>
'''
if 'id="open5"' not in s:
    anchor = '<div class="open done" id="open4">'
    assert s.count(anchor) == 1
    s = s.replace(anchor, BOX + anchor); todo += 1

# F. references
REFS = '''<li id="R57"><code>commits.txt</code> in the results folder: the merge commit 1bda3228229f379ecd8d06fa1cec00c1f73cd542 and the review commit ddf843ad97f8602fc1171458e42036ef03b6e4c4. <code>git rev-parse ddf843ad97^{tree}</code> answers c114b85944795538cb5b2431493f3dc196e9822f. <code>git ls-remote origin refs/heads/jhan-amx-kvmul16</code> answered 4c4b7b8864 before the push and ddf843ad97 after it, on 2026-11-20 at 08:52 PST.</li>
<li id="R58">GitHub Actions runs on ddf843ad97, read on 2026-11-20. GCP Nix: run 44777709823, job Build Tron 136437594151 on andoria-09-0, job Test host 136446778058 on delphi-3bd6-0. Slice tests: run 44777709810. CMake and CTest: run 44777748892, job build 136433703612 and test-host attempt 1 (job 136449930359) on andoria-ee10-0, test-fpga 136449930142 on andoria-02-0, test-host attempt 2 (job 136458006417) on delphi-3bd6-0. The CPU model and the CPU flags come from the step "Debug Info" of each test-host log. The watch log is <code>ci-watch.txt</code> in the results folder.</li>
<li id="R59">Posted on 2026-11-20. Issue <a href="https://github.com/positron-ai/tron/issues/5511">#5511</a>, with its text in <code>muse-glimmer/pr5022-followup-issue.md</code>. The PR description, with its text in <code>muse-glimmer/pr5022-body-round2.final.md</code>; the description before the edit is <code>pr-body-before-round2.md</code> in the results folder. The <a href="https://github.com/positron-ai/tron/issues/5021#issuecomment-7046489138">comment on #5021</a>. The <a href="https://github.com/positron-ai/tron/pull/5022#pullrequestreview-5997064669">review 5997064669</a>, with the record <code>posted-review.json</code> in the results folder.</li>
<li id="R60">Review 5996505130 by <code>claude[bot]</code> on ddf843ad97, submitted 2026-11-20 17:08 UTC, which is 09:08 PST. Its inline comments are 4645384790 (t/CMakeLists.txt:623-625) and 4645384802 (t/t_amx_dispatch_dtype.cpp:364-384).</li>
<li id="R61"><code>mutation-exit-code.txt</code> in the results folder, written by <code>exec/pr5022-final-20261119/mutation-exit-code-3b35.sh</code> on 2026-11-20 at 17:48 UTC. The Catch2 v3.7.1 source in the build tree on delphi-3b35: <code>gen/_deps/catch2-src/src/catch2/catch_session.cpp:37, :39, :350-356</code> and <code>docs/release-notes.md:68-77</code>. The pin of the version: <code>cmake/versions.cmake:26-27</code>, <code>t/CMakeLists.txt:5-6</code> and <code>flake.nix:1056-1058</code> at ddf843ad97. The mapping of exit codes in the test scheduler: <code>bin/slice:1208-1213</code>.</li>
<li id="R62">The timeline of the PR (<code>gh api repos/positron-ai/tron/issues/5022/timeline</code>): three <code>review_requested</code> events at 2026-11-20 16:52:26 UTC, for the teams tron-ci, tron-ingest and tron-core. <code>.github/CODEOWNERS:12-18, :33-35, :49</code> at ddf843ad97.</li>
<li id="R63"><code>AGENTS.md:27-35</code> at ddf843ad97, section "Test policy".</li>
'''
if '<li id="R57">' not in s:
    i = s.index('<li id="R56">'); j = s.index('</ol>', i)
    s = s[:j] + REFS + s[j:]; todo += 1

# G. how this was checked
PROV = ('<p><strong>Update of 2026-11-20, after the go.</strong> Before the posting, every code line that a reply quotes was compared with the pushed head by a script: 162 lines, 0 not found. '
        'All 27 texts were rendered with the markdown service of GitHub, and no text holds a character that GitHub would read as markup outside code. '
        'The posting script stopped once before it sent anything: the PR had 28 review threads and not 26, because the automated review had arrived. '
        'Its red finding was checked against the Catch2 source and with a mutation run on delphi-3b35. That run used our CPUs 96-143 only. The load snapshot before it shows our CPUs 0.1% busy and the same two rinzler servers on the other half. '
        'Not posted: the two draft replies B1 and B2. Not done: the re-request of the review.</p>\n')
if 'Update of 2026-11-20, after the go.' not in s:
    anchor = '</main></body></html>'
    assert s.count(anchor) == 1
    s = s.replace(anchor, PROV + anchor); todo += 1

if s != orig:
    open(p, 'w', encoding='utf-8').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
