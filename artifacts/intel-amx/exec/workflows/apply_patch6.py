#!/usr/bin/env python3
"""Sixth-stage patch of respond-2-Isaac.html (page pass 6, 2026-11-20).

The delphi-3b35 results are in, and every reply draft moves to its posting
form (page-pass-6-brief.md, sections A to D). Idempotent: it always starts
from the stage-5 copy of the page. Run: python3 -I apply_patch6.py
"""
import hashlib
import html
import re

S = ('/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/'
     '78b9fca8-c24b-4ac2-a02d-0236a437cdd6/scratchpad/')
P = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
STAGE5 = S + 'respond-2-Isaac.stage5.html'
LAST = S + 'apply_patch6.last-md5'
STAGE5_MD5 = 'dd47f6919bfb4e5c2f69dc4f8600a3df'
TREE1 = '5821ee86418d3ac07944112c529d7d311e91f3bd'
TREE = 'c114b85944795538cb5b2431493f3dc196e9822f'
HEAD, NIXRUN, CMAKERUN, RUNNER, ISSUE = '⟦HEAD⟧', '⟦NIXRUN⟧', '⟦CMAKERUN⟧', '⟦RUNNER⟧', '⟦ISSUE⟧'


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


assert md5(STAGE5) == STAGE5_MD5, 'stage-5 copy changed'
known = {STAGE5_MD5}
try:
    known.add(open(LAST).read().strip())
except FileNotFoundError:
    pass
assert md5(P) in known, f'page was changed outside this script (md5 {md5(P)})'

s = open(STAGE5, encoding='utf-8').read()
n_rep = 0
changed_replies = set()


def rep(old, new, count=1, reply=None):
    global s, n_rep
    c = s.count(old)
    assert c == count, f'anchor occurs {c} times, expected {count}: {old[:110]!r}'
    s = s.replace(old, new)
    n_rep += 1
    if reply:
        changed_replies.add(reply)


def ref(n):
    return f'<a class="ref" href="#R{n}">[R{n}]</a>'


def esc(code):
    return html.escape(code, quote=False)


def card_span(cid):
    a = s.index(f'<div class="card" id="{cid}">')
    b = s.find('<div class="card" id="', a + 10)
    if b < 0:
        b = s.index('<h2 id="todo">', a)
    return a, b


def div_end(start):
    depth = 0
    for m in re.finditer(r'<div\b|</div>', s[start:]):
        depth += -1 if m.group(0) == '</div>' else 1
        if depth == 0:
            return start + m.end()
    raise AssertionError('unbalanced div')


def replace_reply(cid, inner, after=''):
    global s, n_rep
    a, b = card_span(cid)
    r = s.index('<div class="reply">', a)
    assert r < b, cid
    e = div_end(r)
    s = s[:r] + '<div class="reply"><div class="lbl">Reply</div>' + inner + '</div>' + after + s[e:]
    n_rep += 1
    changed_replies.add(cid)


def cut(start_marker, end_marker, new, must_contain=()):
    global s, n_rep
    assert s.count(start_marker) == 1, f'start marker count {s.count(start_marker)}: {start_marker[:80]!r}'
    a = s.index(start_marker)
    b = s.index(end_marker, a) + len(end_marker)
    old = s[a:b]
    for m in must_contain:
        assert m in old, f'span lacks {m!r}'
    s = s[:a] + new + s[b:]
    n_rep += 1


# ==========================================================================
# 1. Top of the page: header, nav, Short version, intro, status box open4
# ==========================================================================
rep('and a pre-review &middot; nothing posted</p>',
    'and a pre-review &middot; tests at the final head done on 2026-11-20 &middot; nothing posted</p>')
rep('<nav><a href="#short">Short version</a>', '<nav><a href="#short">Short version</a><a href="#open4">Status and the go</a>')
rep('You made the six decisions on 2026-11-19 and answered the open points in three rounds that evening, and the drafts below follow them: '
    'the D1 replies are short and do not mention issue 3997. The code edits are done in an uncommitted working tree, '
    'an independent pre-review found seven points that are all fixed, and the tests on the server delphi-3b35 wait for John Pruitt\'s reboot of that machine.</p></div>',
    'You made the six decisions on 2026-11-19 and answered the open points in three rounds, '
    'and every reply below now reads as a report of what the final head contains. '
    'The tests at the final head ran on the server delphi-3b35 on 2026-11-20 and all 14 runs ended as wanted, '
    'so one thing is needed from you: the go to commit, push and post.</p></div>')
rep('The three boxes below hold your answers of the evening, in three rounds. Nothing is open for you now.',
    'The first box below is the status of 2026-11-20. It holds the one thing that is needed from you. '
    'The three boxes after it hold your answers of 2026-11-19, in three rounds.')
rep('Inline actions: 11 accept as written, 9 accept with a modification, 3 answer only,',
    'Inline actions: 10 accept as written, 9 accept with a modification, 1 accept in part, 3 answer only,')

OPEN4 = f'''<div class="open" id="open4"><p><strong>Status 2026-11-20 05:55 PST: the tests at the final head are in.</strong> One thing is needed from you: the go to commit, push and post.</p>
<ul>
<li><strong>Tests.</strong> All 14 test runs on delphi-3b35 ended with the wanted exit code {ref(48)}. They ran at the final tree c114b85944 {ref(55)}.
<div class="scrollx"><table class="grid">
<tr><th style="width:38%">Run</th><th style="width:14%">Exit code (wanted)</th><th>Result</th></tr>
<tr><td><code>t_amx_numerics</code>, AMX on</td><td class="num">0 (0)</td><td class="on">21,521 assertions in 5 test cases pass. Before this round: 17,425 in 4.</td></tr>
<tr><td><code>t_amx_numerics</code>, kill switch</td><td class="num">0 (0)</td><td class="on">6,671 assertions pass. 3 cases pass, and 2 cases skip.</td></tr>
<tr><td><code>t_amx_numerics "[kv_data]"</code>, kill switch</td><td class="num">4 (4)</td><td class="on">2 cases, both skip, so Catch2 returns 4.</td></tr>
<tr><td><code>t_amx_dispatch_dtype</code>, AMX on and kill switch</td><td class="num">0 (0)</td><td class="on">30,747 assertions in 1 test case, in both runs. Before this round: 3,694.</td></tr>
<tr><td><code>t_llama_unit</code>, AMX on and kill switch</td><td class="num">0 (0)</td><td class="on">265,564 assertions in 75 test cases, in both runs.</td></tr>
</table></div>
The other 7 runs are the 6 section runs (QK, PV and transpose, each with 4 and 16 heads) and the run that writes the JUnit report. All 7 exit 0 (<a href="#todo">Part C</a>).</li>
<li><strong>Object compare of the kernel file.</strong> Between the commit that Isaac reviewed and the final tree, all 11 functions are identical. Between the measured commit 5061623a34 and the final tree, 10 of 11 are identical, and the 16-head QK kernel has the same 207 instructions with two adjacent loop-counter additions swapped {ref(49)}.</li>
<li><strong>Registry.</strong> The tool <code>bin/slice bench --update</code> was not run. It measures on the first slot of each NUMA node, so one of the two tests would run on the other half of the machine {ref(53)}. Done by hand instead: both <code>t_amx_numerics</code> rows carry <code>"skip_return_codes":[4]</code>. The drift warning is gone, and both checks of the tool exit 0 {ref(50)}.</li>
<li><strong>The other half of the machine was not touched.</strong> That half is used by Brian Hamon and John Pruitt. Before the runs our CPUs were 0.1% busy, and the other half ran two rinzler servers with 31 busy threads each. After the runs the same two servers ran, with the same process ids. FPGA cards 4-7 were not open before or after. Every run was pinned to CPUs 96-143 at low priority, and no huge page was used {ref(47)} {ref(51)}.</li>
<li><strong>My error: I reported the reboot 8 hours late.</strong> delphi-3b35 rebooted on 2026-11-19 at 21:19 PST. John Pruitt wrote at 23:48 PST that the reboots were done {ref(52)}. My watcher compared the machine's UTC boot time with the Pacific clock. So it reported the reboot only at 05:35 PST on 2026-11-20. The runs took place from 05:37 to 05:50 PST.</li>
</ul>
<p><strong>What the go starts, in this order:</strong></p>
<ol>
<li>Two commits on <code>jhan-amx-kvmul16</code>: the merge of main 3bea58b788, then the review edits. The tree of the head must equal c114b85944. Then the push. Main has moved by 1 commit since the merge, and that commit conflicts with nothing here {ref(56)}.</li>
<li>The default CI runs by itself. I start the legacy CMake workflow by hand.</li>
<li>I file the approved follow-up issue.</li>
<li>When both CI runs are in, I fill the run ids into the PR description and the replies. Then I edit the PR description, attach the A/B record files as one comment, post the 26 inline replies and the combined reply, and add the comment on #5021.</li>
</ol>
<p>If a CI run fails, I stop and report before I post anything. The replies below hold five placeholders until then: {HEAD}, {NIXRUN}, {CMAKERUN}, {RUNNER} and {ISSUE}.</p>
</div>
'''
rep('<div class="open done" id="open"><p><strong>The three open points: your answers of 2026-11-19, evening.</strong></p>',
    OPEN4 + '<div class="open done" id="open"><p><strong>The three open points: your answers of 2026-11-19, evening.</strong></p>')
rep('<div class="open" id="open3"><!-- pass4 --><p><strong>Answered on 2026-11-19, third round (about 19:50 PST).</strong> Nothing is open for you now. '
    'I ask once for the go to commit, push and post, when the tests at the final head are in.</p>',
    '<div class="open done" id="open3"><!-- pass4 --><p><strong>Answered on 2026-11-19, third round (about 19:50 PST).</strong> These four points are settled. '
    'The tests at the final head are in since 2026-11-20, so the go to commit, push and post is now asked for in the <a href="#open4">status box</a> above.</p>')

# ==========================================================================
# 2. Decision cards D2 and D6
# ==========================================================================
rep('<p><strong>Not verified yet:</strong> the edit is in the working tree. It has not been built with the AMX option ON, and it has not run. '
    'The build and the tests at the final head on delphi-3b35 do both, and they wait for the reboot of the machine (<a href="#todo">Part C</a>). The spelling rests on reading the headers:',
    f'<p><strong>Verified on 2026-11-20:</strong> the build on delphi-3b35 compiles the edit with the AMX option ON and gives 0 compiler warnings {ref(55)}. '
    f'<code>t_amx_dispatch_dtype</code> drives these lines and passes 30,747 assertions {ref(48)}. The headers explain why the spelling compiles:')
D6_TABLE = f'''<p><strong>Repeated at the final tree on 2026-11-20.</strong> Each tree was compiled on delphi-3b35 with the command that the final build recorded for this file. The compiler is clang 19.1.7, the same compiler build as for the measured binaries {ref(49)}.</p>
<div class="scrollx"><table class="grid">
<tr><th style="width:34%">Pair</th><th style="width:20%">Identical functions</th><th>The difference</th></tr>
<tr><td>Reviewed commit 4c4b7b8864 against the final tree</td><td class="on"><span class="cellk">11 of 11</span></td><td>None.</td></tr>
<tr><td>Measured commit 5061623a34 against the final tree</td><td class="new"><span class="cellk">10 of 11</span></td><td><code>qk_rowmajor_128x4&lt;16&gt;</code> has the same 207 instructions. The two adjacent loop-counter additions <code>addq $0x40, %rdx</code> and <code>addq $0x400, %rsi</code> are swapped.</td></tr>
<tr><td>Final tree, compiled again, against the object file of the build itself</td><td class="on"><span class="cellk">11 of 11</span></td><td>None.</td></tr>
<tr><td>Object file of the build against the code inside the linked <code>gen/runtron</code>, with addresses masked</td><td class="new"><span class="cellk">9 of 11</span></td><td>Both PV kernels differ. The linker replaces the 2 instructions that fetch the address of the per-thread buffer (a call of <code>__tls_get_addr</code>) by 2 instructions that read it from <code>%fs</code>.</td></tr>
<tr><td>Main 3bea58b788 against the final tree, 4-head kernels</td><td class="on"><span class="cellk">Pack and QK identical</span>Pack: 509 = 509 instructions. QK: 204 = 204.</td><td>PV has 121 = 121 instructions, with the same instruction names in the same order. Registers, offsets and the access to the per-thread buffer differ.</td></tr>
</table></div>
<p>So the statement in the T10 reply holds as written. The claim in the Short version of the PR description also holds at the final tree: the 4-head pack and QK kernels emit the same instructions as on main.</p>
'''
rep('<p>What this compare does not cover:</p>\n<ul>\n<li><strong>The final head.</strong> The accepted edits change the kernel file again: '
    'I10 moves the transpose into a header, and I14 changes two asserts. The same script repeats the compare at the final head.</li>',
    D6_TABLE + '<p>What the compare of 2026-11-19 did not cover:</p>\n<ul>\n<li><strong>The final head.</strong> This is now covered by the table above.</li>')

# ==========================================================================
# 3. Review-body cards T2..T13 and the combined reply
# ==========================================================================
rep('<p>Agreed. Will do: the per-head state check, in every section of <code>exercise_page</code>. Text and expected values are under your inline comment at t/t_amx_dispatch_dtype.cpp:209.</p>',
    '<p>Agreed. Done: the per-head state check runs in every section of <code>exercise_page</code>. The code and the expected values are under your inline comment at t/t_amx_dispatch_dtype.cpp:209.</p>', reply='T2')
rep('<p>Agreed. Will do: <code>transpose_scores&lt;group_heads&gt;</code> in an AVX-512-only header, and an ungated case for 4 and 16 heads that runs on every host, including the required lane. '
    'Details under your inline comment at src/tron/kernels/amx_attn.cpp:156.</p>',
    '<p>Agreed. Done: <code>transpose_scores&lt;group_heads&gt;</code> is in an AVX-512-only header, with an ungated case for 4 and 16 heads that runs on every host, including the required lane. '
    'Details are under your inline comment at src/tron/kernels/amx_attn.cpp:156.</p>', reply='T3')
# T4
rep('Needs a run on an AMX host at the final head. That host is delphi-3b35 since 2026-11-12.</div></div>',
    f'Needs a run on an AMX host at the final head. That host is delphi-3b35 since 2026-11-12. '
    f'Done on 2026-11-20: 21,521 assertions in 5 test cases with AMX, and 6,671 under the kill switch {ref(48)}.</div></div>')
rep('<p>I will attach per-section Catch2 output from delphi-3b35 (a Granite Rapids host with AMX) at the final head of this PR, in the Verification section. '
    'One command per section, with Catch2\'s <code>-c</code> section filter, so each section reports its own assertion count.',
    f'<p>Here are the per-section results from delphi-3b35 (a Granite Rapids host with AMX) at the final head {HEAD}. '
    'Each section ran as its own command, with Catch2\'s <code>-c</code> section filter, so each section reports its own assertion count.', reply='T4')
rep('<p>The record will also carry a JUnit report (<code>-r junit</code>, one <code>&lt;testcase&gt;</code> per section), the full run, the kill-switch run '
    '(<code>TRON_AMX_DISABLE=1</code>, expected <code>test cases: 5 | 3 passed | 2 skipped</code>), <code>gen/t_amx_dispatch_dtype</code>, the commit hash, the hostname and the host\'s AMX cpuinfo flags.</p>',
    '<p>Each of the four commands exits 0. The QK sections pass 4,096 assertions each. The PV sections pass 2,561 assertions (4 heads) and 4,097 assertions (16 heads).</p>\n'
    '<p>The record also holds a JUnit report (<code>-r junit</code>, one <code>&lt;testcase&gt;</code> per section), the full run (21,521 assertions in 5 test cases), the kill-switch run '
    '(<code>TRON_AMX_DISABLE=1</code>: <code>test cases: 5 | 3 passed | 2 skipped</code>), <code>gen/t_amx_dispatch_dtype</code> (30,747 assertions in 1 test case), '
    'the tree hash of the head, the hostname and the host\'s AMX cpuinfo flags. The Verification table has the totals.</p>', reply='T4')
rep('I will still dispatch that workflow for the linked build (your second gap).</p>',
    f'I still ran that workflow for the linked build (your second gap): run {CMAKERUN}, test-host on {RUNNER}.</p>', reply='T4')
# T5
rep('<p>I will dispatch the CMake lane at the final head of this PR:</p>',
    f'<p>I ran the CMake lane by hand at the final head {HEAD}, as run {CMAKERUN}:</p>', reply='T5')
rep('I will add to the Verification table: the run id, the Build Tron job id with its <code>kernels/amx_attn.cpp</code> compile line and the two link lines, '
    'the Test Host job id with its two <code>passed</code> status lines, and the test-host runner name.</p>',
    f'The Verification table has the row for this run, with its result and the test-host runner {RUNNER}.</p>', reply='T5')
rep('because Catch2 exits 0 on <code>SKIP</code> and <code>t_amx_numerics</code> has no <code>skip_return_codes</code> entry [bin/slice:1208-1213; config/test-benchmarks.json:152].',
    'because Catch2 exits 0 when the other cases pass [bin/slice:1208-1213].', reply='T5')
rep('<p>One caveat on the dispatch itself. The last manual run of that workflow was on 2026-09-11 (run 34633703482). Since then it ran end to end only through the release path: '
    'the tag runs for v2.0.0-rc1 (2026-11-03, run 41738148954) and v2.0.0-rc2 (2026-11-13, run 43511108942) completed its build, test-host and test-fpga jobs. '
    'No manual dispatch on a branch has run since 2026-09-11.</p>',
    '<p>One note on the workflow itself. Before this run, its last manual run was on 2026-09-11 (run 34633703482). In between it ran end to end only through the release path: '
    'the tag runs for v2.0.0-rc1 (2026-11-03, run 41738148954) and v2.0.0-rc2 (2026-11-13, run 43511108942) completed its build, test-host and test-fpga jobs.</p>', reply='T5')
# T6
rep('I will replace the \'Insufficient data\' OFF row of the PR body with these two job ids and the stub-only result (text under your inline comment at t/t_amx_dispatch_dtype.cpp:51).</p>',
    f'The \'Insufficient data\' OFF row of the PR body is replaced. It now cites the default CI run at the final head, {NIXRUN} (text under your inline comment at t/t_amx_dispatch_dtype.cpp:51).</p>', reply='T6')
# T8
rep('<p>What I can add now:</p>', '<p>What I added:</p>', reply='T8')
rep('That timing is the first item of the kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack):',
    f'That timing is the first item of the kernel-performance follow-up issue #{ISSUE} (vectorised pack, stage-3 hoist, lazy pack):', reply='T8')
# T9
rep('<p>Will do: write the reason into the <code>group_heads_ok</code> comment (text under Architecture gap 1).</p>',
    '<p>Done: the reason is in the <code>group_heads_ok</code> comment (text under Architecture gap 1).</p>', reply='T9')
# T10
rep('An object compare with the compiler build and the flags of the measured binaries shows identical listings',
    'An object compare with the compiler build of the measured binaries and the compile command of the final build shows identical listings', reply='T10')
cut('<div class="row"><div class="k">Before posting</div><div>The first bullet states the compare at the final head.',
    'and the bullet is corrected if it shows anything else.</div></div>',
    f'<div class="row"><div class="k">Before posting</div><div>Confirmed on delphi-3b35 on 2026-11-20 (table in card <a href="#D6">D6</a>): '
    f'10 of the 11 functions are identical between 5061623a34 and the final tree, and <code>qk_rowmajor_128x4&lt;16&gt;</code> has the same 207 instructions '
    f'with two adjacent loop-counter additions swapped {ref(49)}. Nothing to correct.</div></div>',
    must_contain=('is pending',))
# T11
rep('<p>You are right on both points. Will do, in this PR: write the reason into the <code>group_heads_ok</code> comment, and replace the first <code>static_assert</code> with the real constraint. '
    'I will not instantiate 8 here (reason under your "next decision" question).</p>',
    '<p>You are right on both points. Done, in this PR: the reason is in the <code>group_heads_ok</code> comment, and the first <code>static_assert</code> is replaced with the real constraint. '
    '8 is not instantiated here (reason under your "next decision" question).</p>', reply='T11')
# T12
rep('I will add your spelling, <code>amx_attn_h128</code> and the <code>_128</code> suffix, to the issue.',
    'The issue gets a comment with your spelling, <code>amx_attn_h128</code> and the <code>_128</code> suffix, together with these replies.', reply='T12')
# T13
rep('is already a candidate in #5021, so I will evaluate the <code>index_sequence</code> spelling there.</p>',
    'is already a candidate in #5021, so the <code>index_sequence</code> spelling is a question for that issue.</p>', reply='T13')
rep('Will do: one paragraph (under your inline comment at src/tron/CMakeLists.txt:216), the same sentence in the CMake comment, and a caption on the flags block at README.ci.md:563-568 '
    'saying it is the <code>cmake-single-platform.yml</code> configure line, so the section has no third unnamed home for the flag.</p>',
    'Done: the paragraph is fixed (text under your inline comment at src/tron/CMakeLists.txt:216), the CMake comment says the same, and the flags block at README.ci.md:563-568 '
    'has a caption that names <code>cmake-single-platform.yml</code>, so the section has no third unnamed home for the flag.</p>', reply='T13')
# combined reply
rep('<li><strong>Transpose lanes.</strong> <code>transpose_scores&lt;group_heads&gt;</code> moves to an AVX-512-only header with an ungated 4/16-head case that also runs in the pull-request lane.',
    '<li><strong>Transpose lanes.</strong> <code>transpose_scores&lt;group_heads&gt;</code> is now in an AVX-512-only header, with an ungated 4/16-head case that also runs in the pull-request lane.', reply='combined')
rep('<li><strong>Real-AMX execution at head.</strong> Per-section Catch2 output, JUnit report, kill-switch run, host and commit from a Granite Rapids host (delphi-3b35) at the final head, in the Verification section.</li>',
    f'<li><strong>Real-AMX execution at head.</strong> Run on a Granite Rapids host (delphi-3b35) at the final head {HEAD}, one command per section. '
    'The QK sections pass 4,096 assertions each (4 and 16 heads). The PV sections pass 2,561 and 4,097. The transpose sections pass 1,280 each. '
    'The whole of <code>t_amx_numerics</code> passes 21,521 assertions in 5 test cases. Under the kill switch 3 cases pass and 2 skip. '
    'The totals are in the Verification section. The result record also holds a JUnit report with one entry per section.</li>', reply='combined')
rep('The kernel cases execute only if its test-host job lands on a Granite Rapids runner, and the body will name the runner.</li>',
    f'It is run {CMAKERUN}, and its test-host job ran on {RUNNER}. The kernel cases execute only on a Granite Rapids runner.</li>', reply='combined')
rep('<li><strong>OFF build.</strong> The Verification row cites jobs 117831672410 and 117835534166 and the guard move.</li>',
    f'<li><strong>OFF build.</strong> The Verification row now cites the default CI run at the final head, {NIXRUN}. The guard move is described on the inline thread at t/t_amx_dispatch_dtype.cpp:51.</li>', reply='combined')
rep('<li><strong>Granite Rapids timing.</strong> No per-kernel number exists. I will attach the A/B record files. '
    'A per-kernel timing on Granite Rapids is the first item of a kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack).</li>',
    f'<li><strong>Granite Rapids timing.</strong> No per-kernel number exists. The A/B record files are attached in a separate comment. '
    f'A per-kernel timing on Granite Rapids is the first item of the kernel-performance follow-up issue #{ISSUE} (vectorised pack, stage-3 hoist, lazy pack).</li>', reply='combined')
rep('and this PR is scoped to Muse Glimmer\'s kv_mul 16. The reason goes into the <code>group_heads_ok</code> comment.</li>',
    'and this PR is scoped to Muse Glimmer\'s kv_mul 16. The reason is in the <code>group_heads_ok</code> comment.</li>', reply='combined')
rep('<li><strong>Gaps 1-3.</strong> The first <code>static_assert</code> becomes the lane bound,',
    '<li><strong>Gaps 1-3.</strong> The first <code>static_assert</code> is now the lane bound,', reply='combined')

# ==========================================================================
# 4. Inline cards
# ==========================================================================
rep('<span class="tag hw">needs an AMX host</span>', '<span class="tag hw">ran on delphi-3b35</span>', count=10)
# I1, I3
rep('<p>Agreed on the reason. Will do: lines 14-16 become</p>', '<p>Agreed on the reason. Done: lines 14-16 now read</p>', reply='I1')
rep('<p>You are right. Will do: scope the sentence to <code>group_heads &lt; TILE_ROWS_16</code>.</p>',
    '<p>You are right. Done: the sentence is scoped to <code>group_heads &lt; TILE_ROWS_16</code>.</p>', reply='I3')
rep('<p>Proposed text for lines 100-105:</p>', '<p>The text of lines 100-105 now:</p>', reply='I3')
# I4
rep('<p>I will not move the pack in this PR. The pack cost and the pack placement are one problem:',
    '<p>The pack stays where it is in this PR. The pack cost and the pack placement are one problem:', reply='I4')
rep('I will put both, with the lazy tile region from the #3879 plan, in one kernel-performance follow-up issue, with a Granite Rapids measurement '
    '(pack&lt;16&gt; ns per call, and the share of zero-AMX-page calls for Muse Glimmer) so the change lands with its number.',
    f'Both are in the kernel-performance follow-up issue #{ISSUE}, together with the lazy tile region from the #3879 plan. '
    'The issue asks for a Granite Rapids measurement (pack&lt;16&gt; ns per call, and the share of zero-AMX-page calls for Muse Glimmer), so the change lands with its number.', reply='I4')
# I5
rep('<p>Agreed. I will take the suggestion.</p>', '<p>Agreed. I took the suggestion.</p>', reply='I5')
rep('This is the first use on a stack scratch buffer, so I will add one line saying why it is safe:</p>',
    'This is the first use on a stack scratch buffer, so one added line says why it is safe:</p>', reply='I5')
rep('<p>I will rerun the unit tests at the final head on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch. The change alters no values.</p>',
    '<p>At the final head <code>t_amx_dispatch_dtype</code> passes 30,747 assertions on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch. The change alters no values.</p>', reply='I5')
# I6
rep('The edit is in the working tree. Its build with the option ON and its run wait for delphi-3b35.',
    f'The edit is in the working tree. The build with the option ON on delphi-3b35 gave 0 compiler warnings, and the tests that drive it passed on 2026-11-20 {ref(48)} {ref(55)}.')
rep('<p>Agreed. I will replace the stack copy just below the PV call with your aligned view over the row.</p>',
    '<p>Agreed. The stack copy just below the PV call is replaced with your aligned view over the row.</p>', reply='I6')
rep('I will rerun <code>t_amx_numerics</code>, <code>t_amx_dispatch_dtype</code> and <code>t_llama_unit</code> at the final head on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch.</p>',
    'At the final head <code>t_amx_numerics</code>, <code>t_amx_dispatch_dtype</code> and <code>t_llama_unit</code> pass on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch.</p>', reply='I6')
# I7
rep('which builds and tests with the option ON: run &lt;id&gt;, test-host on &lt;runner&gt;.</li>',
    f'which builds and tests with the option ON: run {CMAKERUN}, test-host on {RUNNER}.</li>', reply='I7')
cut('<div class="row"><div class="k">Still open</div><div>The placeholders &lt;id&gt; and &lt;runner&gt; are filled in after the run of the legacy CMake workflow.',
    'the promise of a separate PR and the promise to rebase.</div></div>',
    f'<div class="row"><div class="k">Before posting</div><div>The placeholders {CMAKERUN} and {RUNNER} are filled in after the run of the legacy CMake workflow. '
    f'The runs on delphi-3b35 at the final head are done since 2026-11-20 {ref(48)}.</div></div>',
    must_contain=('become true with the runs',))
# I8
rep('<p>The flags block above it gets one caption line:', '<p>The flags block above it has one new caption line:', reply='I8')
# I9
rep('<p>Agreed. I will keep the scalar pack in this PR and track the vectorised version on a kernel-performance follow-up issue, linked here once filed. '
    '#5021 does not fit, since it excludes performance changes.</p>',
    f'<p>Agreed. The scalar pack stays in this PR. The vectorised version is tracked in the kernel-performance follow-up issue #{ISSUE}. '
    '#5021 does not fit, since it excludes performance changes.</p>', reply='I9')
# I10
rep('<li>Object compare of the kernel file (one object file, clang 19.1.7, 2026-11-19): all 10 functions are identical before and after the move. '
    'They are also identical between the commit you reviewed and the final tree. '
    '<code>qk_rowmajor_128x4&lt;4&gt;</code> has 204 instructions, and <code>&lt;16&gt;</code> has 207. '
    'The compare with the product build flags on a Granite Rapids host is pending.</li>',
    '<li>Object compare of the kernel file, on a Granite Rapids host with the compile command of the build: all 11 functions are identical between the commit you reviewed and the final head. '
    '<code>qk_rowmajor_128x4&lt;4&gt;</code> has 204 instructions, and <code>&lt;16&gt;</code> has 207. '
    'The 4-head pack and QK kernels are identical to main\'s, with 509 and 204 instructions.</li>', reply='I10')
rep('Each section makes 1,280 assertions. The case, the sentinel constant',
    'Each section makes 1,280 assertions, and both sections pass on the Granite Rapids host, with AMX on and under the kill switch. The case, the sentinel constant', reply='I10')
cut('<div class="row"><div class="k">Still open</div><div>Two statements of this reply wait for delphi-3b35:',
    'The local compare used the compile flags of an earlier tron build for this file.</div></div>',
    f'<div class="row"><div class="k">Closed 2026-11-20</div><div>Both open statements are settled on delphi-3b35: the object compare with the compile command of the build, '
    f'and the first run of the new test case {ref(48)} {ref(49)}.</div></div>',
    must_contain=('first run of the new test case',))
# Tense of four opening statements that describe the commit Isaac reviewed
rep('<p>You are right. The three new lanes have run in no CI lane at all. The kernel cases skip in the option-on lane, and the pull-request lane (GCP Nix) '
    'does not set <code>TRON_AMX_DISPATCH</code> [nix/cmake-tron-test-build.nix:87-93], so there the whole file compiles to the stub case [t/t_amx_numerics.cpp:339-344].</p>',
    '<p>You are right. At the commit you reviewed, the three new lanes had run in no CI lane at all. The kernel cases skip in the option-on lane, and the pull-request lane (GCP Nix) '
    'does not set <code>TRON_AMX_DISPATCH</code> [nix/cmake-tron-test-build.nix:87-93], so there the whole file compiled to the stub case [t/t_amx_numerics.cpp:339-344].</p>', reply='I10')
rep('<p>You are right. The fixture calls <code>apply_page_range</code> with <code>kv_head</code> 0 only [t/t_amx_dispatch_dtype.cpp:199], so the <code>kv_head * operation_kv_mul * head_size</code> term '
    'of the pack base [h/tron/models/self_attention.hpp:1696] is always 0 here. The comment overstated what the per-head offsets check.</p>',
    '<p>You are right. At the commit you reviewed, the fixture calls <code>apply_page_range</code> with <code>kv_head</code> 0 only [t/t_amx_dispatch_dtype.cpp:199], so the <code>kv_head * operation_kv_mul * head_size</code> term '
    'of the pack base [h/tron/models/self_attention.hpp:1696] is always 0 there. The comment overstated what the per-head offsets check.</p>', reply='I17')
rep('<p>You are right. Nothing after <code>apply_page_range</code> reads the running-softmax state, so the epilogue\'s per-head merge is unchecked here. Done: the check is in',
    '<p>You are right. At the commit you reviewed, nothing after <code>apply_page_range</code> read the running-softmax state, so the epilogue\'s per-head merge was unchecked. Done: the check is in', reply='I19')
rep('<p>You are right. <code>check_pv</code> reads only rows 0..group_heads-1 of <code>o_amx</code> [t/t_amx_numerics.cpp:275],',
    '<p>You are right. At the commit you reviewed, <code>check_pv</code> reads only rows 0..group_heads-1 of <code>o_amx</code> [t/t_amx_numerics.cpp:275],', reply='I24')
# I12, I13
rep('<p>Agreed. I will track the hoist on the kernel-performance follow-up issue rather than change this PR.</p>',
    f'<p>Agreed. The hoist is tracked in the kernel-performance follow-up issue #{ISSUE}. This PR does not make the change.</p>', reply='I12')
rep('<p>Agreed that the row needs an explanation. I will change the PR body rather than add repetitions.</p>',
    '<p>Agreed that the row needs an explanation. I changed the PR body rather than add repetitions.</p>', reply='I13')
# I13: the note as the description draft has it now (draft of 2026-11-20 05:54 PST)
rep('all four repetitions, so it is an offset between the two binaries, cause\n'
    'unknown. The Glimmer decode gains (2.61 to 5.16 TPS) are 4 to 9 times that\n'
    'offset.</code></pre>',
    'all four repetitions. It is an offset between the two binaries, cause unknown.\n'
    'The Glimmer decode gains are 4 to 9 times that offset.</code></pre>', reply='I13')
# I14, I15
rep('<p>Agreed. Will do: replace the first <code>static_assert</code> with the upper bound and keep the <code>% 4</code> assert.</p>',
    '<p>Agreed. Done: the first <code>static_assert</code> is replaced with the upper bound, and the <code>% 4</code> assert is kept.</p>', reply='I14')
rep('<p>You are right. Will do: take your wording, split at the semicolon.</p>',
    '<p>You are right. Done: the comment takes your wording, split at the semicolon.</p>', reply='I15')
rep('<p>Proposed text for line 269:</p>', '<p>The text at line 269 now:</p>', reply='I15')
# I16: whole reply
I16_ROW = ('| `TRON_AMX_DISPATCH=OFF` (default CI build, `gcp-nix.yml`) | CI run ' + NIXRUN + ', jobs Build Tron and Test host | '
           'Both jobs pass. The AMX checks are compiled out. The transpose case runs. |')
replace_reply('I16',
    '<p>You are right. Both parts of the body were stale. The fix is in the PR description, not in the code.</p>\n'
    f'<p>The OFF row now cites the default CI run at the final head: {NIXRUN}, jobs Build Tron and Test host. '
    'That build passes no <code>-DTRON_AMX_DISPATCH</code> flag, and the option defaults OFF [nix/cmake-tron-test-build.nix:79-101, CMakeLists.txt:46]. '
    'In the OFF build <code>t_amx_dispatch_dtype</code> holds only the placeholder case that calls <code>SUCCEED</code>, and <code>t_amx_numerics</code> holds only the transpose case. '
    'So "passed" there means that each binary builds and runs and that the transpose is checked. It does not mean that the AMX checks ran.</p>\n'
    '<p>At the commit you reviewed, the same lane passed in run 39179018918: Build Tron job 117831672410 and Test host job 117835534166.</p>\n'
    '<p>On the guard move: the fakes and the <code>probe</code> object sit under <code>#ifdef TRON_AMX_DISPATCH</code> [t/t_amx_dispatch_dtype.cpp:51]. '
    'The Nix build at 7e7f52d761 (Build Tron job 117801889954) emitted <code>t_amx_dispatch_dtype.cpp:68:11: warning: variable \'probe\' is not needed and will not be emitted [-Wunneeded-internal-declaration]</code>. '
    'The build at the commit you reviewed emits no such warning.</p>\n'
    '<p>The row:</p>\n'
    f'<pre><code>{esc(I16_ROW)}</code></pre>',
    after='\n<div class="row"><div class="k">Before posting</div><div>The draft of the PR description cites the default CI run in its OFF row. '
          'It does not cite the two job ids that Isaac named, and it does not mention the guard move. The reply states both. '
          'Say if the description should carry them as well.</div></div>')
# I17
rep('The section is in the working tree. Its file passed the local syntax check with clang 19.1.7 on 2026-11-19. It has not run yet.',
    f'The section is in the working tree. It ran on delphi-3b35 on 2026-11-20 and passed, in 0.012 s {ref(48)}.')
rep('<p>Will do: add the section you propose. It is Glimmer\'s own shape (32 query heads, 2 KV heads, 128 dimensions per head), and it will be the only check of that base term that runs on a host without AMX. '
    'Fixture changes: <code>n_kv_heads</code> becomes a template parameter with the default <code>KV_HEADS_1</code>,',
    '<p>Done: the section you propose is added. It is Glimmer\'s own shape (32 query heads, 2 KV heads, 128 dimensions per head), and it is the only check of that base term that runs on a host without AMX. '
    'Fixture changes: <code>n_kv_heads</code> is a template parameter with the default <code>KV_HEADS_1</code>,', reply='I17')
rep('The current loop over <code>expected.size()</code> would read past <code>probe.q</code>, which holds 16 x 128 values.',
    'The earlier loop over <code>expected.size()</code> would have read past <code>probe.q</code>, which holds 16 x 128 values.', reply='I17')
rep('for the same reason. I will also reword the comment:</p>', 'for the same reason. The comment is reworded:</p>', reply='I17')
rep('<p>One caveat: the new section builds a 32-head model (dim 4096) through the same fixture. If its construction time turns out too long in the test run, I will fall back to your reword alone and say so.</p>',
    '<p>The new section builds a 32-head model (dim 4096) through the same fixture. It takes 0.012 s in the run on a Granite Rapids host, so its construction time is no concern.</p>', reply='I17')
# I19
rep('<p>I will rerun <code>t_amx_dispatch_dtype</code> with <code>TRON_AMX_DISPATCH=ON</code> and refresh the assertion count in the Verification table once, after all test edits of this round.</p>',
    '<p>At the final head <code>t_amx_dispatch_dtype</code> passes 30,747 assertions in 1 test case (3,694 before this round), with AMX on and with the kill switch. '
    'The Verification table has the new count.</p>', reply='I19')
cut('<div class="row"><div class="k">Still open</div><div>The check has not run yet.',
    'is a reading of the code until that run.</div></div>',
    f'<div class="row"><div class="k">Closed 2026-11-20</div><div>The check ran on delphi-3b35 and passed, including <code>v_star == 0</code> on the AVX path {ref(48)}.</div></div>',
    must_contain=('Its first run is on delphi-3b35',))
# I20
rep('<p>Agreed. Will do: replace the three spelled-out view types with the aliases, so the tests name the layouts the way the kernel does.</p>',
    '<p>Agreed. Done: the three spelled-out view types are replaced with the aliases, so the tests name the layouts the way the kernel does.</p>', reply='I20')
rep('with <code>PAGE_TOKENS_64</code> namespace-qualified. I plan to leave those.', 'with <code>PAGE_TOKENS_64</code> namespace-qualified. I left those.', reply='I20')
# I21
rep('<p>Agreed. Will do: add both sections after the 16-head full-page one.</p>', '<p>Agreed. Done: both sections are added after the 16-head full-page one.</p>', reply='I21')
rep('Today the only 16-head section is dense, so its page goes to the QK/PV fakes',
    'Before this round the only 16-head section was dense, so its page went to the QK/PV fakes', reply='I21')
rep('No section sends a 16-head / 1-KV-head page through the AVX dotter loop in <code>apply_page_tok</code>. These two would be the first, and both assert',
    'No section sent a 16-head / 1-KV-head page through the AVX dotter loop in <code>apply_page_tok</code>. These two are the first, and both assert', reply='I21')
rep('<p>The file header list will name both arms. I will post the new assertion count from a <code>TRON_AMX_DISPATCH=ON</code> build and refresh the 3,694 / 1 rows in the Verification table once, after all test edits.</p>',
    '<p>The file header list names both arms. With the option ON the file now passes 30,747 assertions in 1 test case (3,694 before this round), with AMX on and with the kill switch. '
    'The Verification table has the new count.</p>', reply='I21')
# I22, I23
rep('<p>Will do: put the trailing comment on both lines instead. Each line then describes itself, and no heading spans the three other names.</p>',
    '<p>Done: the trailing comment is on both lines. Each line describes itself, and no heading spans the three other names.</p>', reply='I22')
rep('<p>You are right. Will do: take the suggestion as written.</p>', '<p>You are right. Done: the suggestion is taken as written.</p>', reply='I23')
# I24
rep('<p>Will do: add your zero check, with one change. In the 4-head case the test\'s own <code>exp_rows</code> is also 4 rows [t/t_amx_numerics.cpp:260], '
    'so a regressed bound would read the test\'s stack, and whether that garbage is nonzero is not deterministic. '
    'I will give <code>exp_rows</code> 16 rows and fill rows group_heads..15 with 1.0f.',
    '<p>Done: your zero check is added, with one change. In the 4-head case the test\'s own <code>exp_rows</code> was also 4 rows [t/t_amx_numerics.cpp:260], '
    'so a regressed bound would have read the test\'s stack, and whether that garbage is nonzero is not deterministic. '
    '<code>exp_rows</code> now has 16 rows, and rows group_heads..15 hold 1.0f.', reply='I24')
rep('<p>The PV case skips without AMX, so I will run <code>t_amx_numerics</code> on a Granite Rapids host (delphi-3b35) and post the new per-section counts. '
    'The 4-head section\'s name becomes "4 heads: rows 0..3 in the envelope, rows 4..15 zero".</p>',
    '<p>The PV case skips without AMX, so I ran <code>t_amx_numerics</code> on a Granite Rapids host (delphi-3b35) at the final head. '
    'The 4-head PV section passes 2,561 assertions, and the 16-head section passes 4,097. '
    'The 4-head section\'s name is now "4 heads: rows 0..3 in the envelope, rows 4..15 zero".</p>', reply='I24')
# I25: action, checked row, whole reply
rep('accept (one refresh after all test edits)', 'accept in part: registry metadata by hand, timing rows not re-measured', count=2)
rep('The weekly bot refresh measures the Nix OFF binary and its scheduled runs on 2026-10-18 and 2026-10-25 failed.',
    f'The weekly bot refresh measures the Nix OFF binary. Its scheduled runs failed on 2026-10-18 and 2026-10-25, and they succeeded on 2026-11-01, 2026-11-08 and 2026-11-15 {ref(54)}.')
rep('granite_rapids_6962p [bin/slice:2008-2010]. <span class="sub">(claim confirmed)</span>',
    'granite_rapids_6962p [bin/slice:2008-2010]. '
    f'Result of 2026-11-20: <code>bin/slice route</code> answers <code>local-legacy</code>. The update tool was not run. It measures on the first slot of each NUMA node, '
    f'so one of the two tests would run on the other half of the shared machine {ref(53)}. '
    f'Both <code>t_amx_numerics</code> rows got <code>"skip_return_codes":[4]</code> by hand [config/test-benchmarks.json:151, :494]. '
    f'The drift warning is gone, and both checks of the tool exit 0 {ref(50)}. '
    '<span class="sub">(claim confirmed)</span>')
replace_reply('I25',
    '<p>Partly done. Both <code>t_amx_numerics</code> rows now carry <code>"skip_return_codes":[4]</code>, so the registry agrees with the registration [config/test-benchmarks.json:151, :494]. '
    '<code>bin/slice bench --check</code> and <code>--check-platform</code> pass, and the scheduler\'s drift warning for <code>t_amx_numerics</code> is gone.</p>\n'
    '<p>Not done: I did not run <code>bin/slice bench --update</code>, so <code>times</code> and <code>max_rss_mb</code> are unchanged. '
    '<code>bin/slice route</code> answers <code>local-legacy</code> on the Granite Rapids host I can use. '
    'But the tool measures on slots of both NUMA nodes, and the tests pin their threads by slot. That host is shared, and I may use one half of it.</p>\n'
    '<p>Measured directly on that half with the option-ON build, 5 runs each with the registered command: <code>t_amx_numerics</code> takes 0.66 to 0.69 s and '
    '<code>t_amx_dispatch_dtype</code> 0.77 to 0.79 s. The rows say 0.66 to 0.91 s and 0.60 to 0.85 s, so the scheduling estimates still hold. '
    'One number is off: <code>t_amx_dispatch_dtype</code> peaks at 99 MiB in the option-ON build, and the row says 8 MB, '
    'which is the default build where the file holds only its placeholder case.</p>')
# I26
rep('and carries the label <code>skip_return_code_4</code>. The registry refresh follows.</p>',
    'and carries the label <code>skip_return_code_4</code>. Both registry rows of <code>t_amx_numerics</code> carry <code>"skip_return_codes":[4]</code> (your comment at line 311).</p>', reply='I26')
rep('\n<p>Then the registry refresh from your comment at line 311, which adds <code>"skip_return_codes":[4]</code> to the <code>t_amx_numerics</code> rows [config/test-benchmarks.json:152, :492].</p>',
    '', reply='I26')
cut('<p>Verification: on a non-AMX host, <code>gen/t_amx_numerics "[kv_data]"; echo $?</code> prints 4,',
    'On an AMX host the unfiltered run still passes with exit 0.</p>',
    '<p>Verification, measured on a Granite Rapids host. The kill switch stands in for a host without AMX. '
    'With it, <code>TRON_AMX_DISABLE=1 gen/t_amx_numerics "[kv_data]"</code> exits 4: 2 cases, both skipped. '
    '<code>ctest --show-only=json-v1</code> lists <code>SKIP_RETURN_CODE 4</code> and the label <code>skip_return_code_4</code>. '
    'The unfiltered kill-switch run exits 0, with 3 cases passed and 2 skipped. The unfiltered run with AMX exits 0.</p>',
    must_contain=('the new property only matters for a filtered invocation',))
changed_replies.add('I26')

# ==========================================================================
# 5. Part C
# ==========================================================================
rep('The merge is not committed. The line numbers in the list below are those of the reviewed commit 4c4b7b8864.</p>',
    f'The merge is not committed. Main has moved by 1 commit since: 0af590c21e (PR 5304) of 2026-11-19 21:17 PST. '
    f'It changes line 409 of the registry file and none of the other 11 files. A trial merge of the final tree with it gives 0 conflict markers {ref(56)}. '
    'The merge in the final tree stays at 3bea58b788. The line numbers in the list below are those of the reviewed commit 4c4b7b8864.</p>')
rep('<p><strong>Status on 2026-11-19 at 20:48 PST.</strong> Every edit of the list below is made in the working tree <code>/home/jhan/workspace/ai-runs/pr5022-final/tron</code>, except the registry file. '
    f'Against main, 11 files differ: 9 existing files, the new header and the changelog fragment {ref(46)}. '
    f'The git tree hash of this state is <code>{TREE1}</code> {ref(46)}.</p>',
    '<p><strong>Status on 2026-11-20 at 05:55 PST.</strong> Every edit of the list below is made in the working tree <code>/home/jhan/workspace/ai-runs/pr5022-final/tron</code>. '
    f'Against main 3bea58b788, 12 files differ: 10 existing files, the new header and the changelog fragment {ref(46)}. '
    f'The git tree hash of this state is <code>{TREE}</code> {ref(46)}. The build and the tests on delphi-3b35 used exactly this tree {ref(55)}.</p>')
rep('<li><strong>Not done locally:</strong> a standalone run of the transpose function. The permission system of the agent\'s server blocked it. The test binary on delphi-3b35 covers it.</li>'
    '<li><strong>Pending on delphi-3b35, after the reboot:</strong> the build, the tests, the object compare with the product build flags, and the registry refresh.</li></ul>',
    '<li><strong>Not done locally:</strong> a standalone run of the transpose function. The permission system of the agent\'s server blocked it. '
    'The test binary on delphi-3b35 covered it: the transpose case passes there, with 1,280 assertions per section.</li>'
    '<li><strong>Done on delphi-3b35 on 2026-11-20:</strong> the build, the tests and the object compare with the compile command of the build '
    '(block "Runs on delphi-3b35" below). The registry got a hand edit, and the update tool was not run.</li></ul>')
rep('<li><code>config/test-benchmarks.json</code>: <strong>not edited yet</strong>, it waits for the registry refresh on delphi-3b35. '
    'Planned: refreshed rows for both tests on <code>granite_rapids_6962p</code>; <code>skip_return_codes</code> on the genoa96 row (I25, I26).</li>',
    '<li><code>config/test-benchmarks.json</code>: edited by hand. Both <code>t_amx_numerics</code> rows gain <code>"skip_return_codes":[4]</code>, at line 151 (genoa96) and line 494 (granite_rapids_6962p). '
    'The update tool was not run, so the <code>times</code> and <code>max_rss_mb</code> values are unchanged (I25, I26).</li>')
cut('<h4>PR body edits: drafted, not posted</h4>', 'after the transpose move (I10).</li></ul>',
    '<h4>PR body edits: drafted with the measured values, not posted</h4>\n'
    '<p>The draft is <code>~/workspace/intel-AMX/muse-glimmer/pr5022-body-round2.draft.md</code>. It has 1,979 words. The values of the runs are filled in. '
    'Five placeholders are left, and all of them need the push: ⟦HEAD⟧, ⟦NIXRUN⟧, ⟦CMAKERUN⟧, ⟦RUNNER⟧ and ⟦CMAKERESULT⟧.</p>\n'
    '<ul><li><strong>Short version:</strong> "the kv_mul-4 pack and QK kernels emit the same instructions as on main". '
    f'The compare at the final tree confirms it: pack 509 = 509 instructions, QK 204 = 204 {ref(49)}.</li>'
    '<li><strong>Background:</strong> "Main supports only kv_mul 4 on AMX."</li>'
    '<li><strong>Verification, opening:</strong> the tests ran at the head ⟦HEAD⟧ on delphi-3b35 on 2026-11-20. The token and performance measurements ran on delphi-3bda at 5061623a34, against its merge base 6198824246.</li>'
    '<li><strong>Verification, performance paragraph:</strong> the measurements are not repeated at the head. This PR\'s changes since the measured commit carry a low risk for performance. '
    'The object-compare sentence reads: "Compiled with the build\'s own command, 10 of the kernel file\'s 11 functions match the measured commit exactly. '
    'The 16-head QK kernel has the same 207 instructions, with two adjacent loop-counter additions swapped." '
    'The head also contains main up to 3bea58b788, which the nightly systems test measures (T10, D2, D6).</li>'
    '<li><strong>Builds and tests:</strong> the table has the totals of the final run: <code>t_amx_numerics</code> 21,521 assertions in 5 cases, <code>t_amx_dispatch_dtype</code> 30,747 in 1 case, '
    '<code>t_llama_unit</code> 265,564 in 75 cases, and under the kill switch 6,671 assertions with 3 cases passed and 2 skipped. '
    'It has one row for the option OFF in the default CI build (<code>gcp-nix.yml</code>) and one row for the option ON in CI (<code>cmake-single-platform.yml</code>, started by hand). '
    'Both rows hold placeholders (I16, T5). The table has no per-section rows and no JUnit entry. The per-section counts are in the combined reply (T4).</li>'
    '<li><strong>Performance:</strong> the rule sentence stands in one place, the qwen3-4b cell carries the label "no PR code on path", and the note is one bullet (I13). '
    'Two rows left the merge-base table: qwen3-4b / tp2 / 8192 and gpt-oss-120b / tp4 / 2048, both inside their bands. '
    'The draft says: "Two further rows, both inside their bands, are in the result file."</li>'
    '<li><strong>Not in the draft:</strong> the guard move that I16 asks for. The I16 reply states it (card <a href="#I16">I16</a>).</li></ul>',
    must_contain=('Still to fill in',))
RUNS = f'''<h4>Runs on delphi-3b35: done on 2026-11-20, 05:37 to 05:50 PST (compile and unit tests only, no benchmark; our half is <code>--instance 1,2</code>)</h4>
<ul><li><strong>Start.</strong> My checks on 2026-11-19, the last at 20:47 PST, still read the boot time of 2026-08-24 {ref(41)}. The machine rebooted on 2026-11-19 at 21:19 PST. Its own clock prints 2026-11-20 05:19:05 UTC. John Pruitt wrote in the group thread at 23:48 PST: "Reboots are done. I'm doing some more work on the machines but doesn't appear like I'll need to reboot them again. Still keeping to FPGAs 0-3 on delphi-3b35" {ref(52)}. My watcher compared the machine's UTC boot time with the Pacific clock. So it reported the reboot 8 hours late, at 05:35 PST on 2026-11-20. That is my error.</li><li><strong>The other half was not touched.</strong> The load snapshot before the runs (13:35 UTC) shows our CPUs 0.1% busy and FPGA cards 4-7 not open. The other half, used by Brian Hamon and John Pruitt, runs two rinzler servers of the account <code>disagg</code> with 31 busy threads each. That gives the load average 64. The snapshot after the runs (13:50 UTC) shows the same two servers with the same process ids, 148594 and 150359, and cards 4-7 still not open {ref(47)} {ref(51)}. Every run was pinned to CPUs 96-143 at <code>nice -n10</code>, with <code>SYSTEM_CONFIG="--instance 1,2"</code>. No FPGA card and no huge page was used.</li><li><strong>Two passes.</strong> The first pass used the tree 5821ee8641, in which 11 files differ from main 3bea58b788. The second pass used the final tree c114b85944 with 12 files. The 12th file is <code>config/test-benchmarks.json</code>. The four binaries (runtron and the three tests) have the same sha256 sum in both passes. So the registry edit changes no binary {ref(55)}.</li><li><strong>Build.</strong> <code>cmake --preset native -DBUILD_INGEST_MODELS=OFF -DTRON_AMX_DISPATCH=ON</code> with clang 19.1.7 and ccache, build type RelWithDebInfo. The targets are runtron, <code>t_amx_numerics</code>, <code>t_amx_dispatch_dtype</code> and <code>t_llama_unit</code>. The build gives 0 compiler warnings. runtron holds 64 <code>tdpbf16ps</code> instructions, which is the AMX dot-product instruction. The build took 304 s in the first pass and 19 s in the second {ref(55)}. The earlier plan line of this page named <code>BUILD_INGEST_MODELS=ON</code>. That was wrong for this build.</li><li><strong>Tests at the final tree c114b85944.</strong> All 14 runs ended with the wanted exit code, and the counts are the same in both passes {ref(48)}.
<div class="scrollx"><table class="grid">
<tr><th style="width:34%">Run</th><th style="width:13%">Exit code (wanted)</th><th>Result</th></tr>
<tr><td><code>t_amx_numerics</code>, AMX on</td><td class="num">0 (0)</td><td>21,521 assertions in 5 test cases pass. Before this round: 17,425 in 4.</td></tr>
<tr><td>QK section, 4 heads / 16 heads</td><td class="num">0 (0)</td><td>4,096 / 4,096 assertions.</td></tr>
<tr><td>PV section, 4 heads / 16 heads</td><td class="num">0 (0)</td><td>2,561 / 4,097 assertions.</td></tr>
<tr><td>Transpose section, 4 heads / 16 heads</td><td class="num">0 (0)</td><td>1,280 / 1,280 assertions.</td></tr>
<tr><td><code>t_amx_numerics</code>, kill switch</td><td class="num">0 (0)</td><td>6,671 assertions pass. 3 cases pass, and 2 cases skip with "AMX unavailable".</td></tr>
<tr><td><code>t_amx_numerics "[kv_data]"</code>, kill switch</td><td class="num">4 (4)</td><td>2 cases, both skip, so Catch2 returns 4.</td></tr>
<tr><td><code>t_amx_dispatch_dtype</code>, AMX on and kill switch</td><td class="num">0 (0)</td><td>30,747 assertions in 1 test case, in both runs. Before this round: 3,694.</td></tr>
<tr><td><code>t_llama_unit</code>, AMX on and kill switch</td><td class="num">0 (0)</td><td>265,564 assertions in 75 test cases, in both runs. Before: 265,452 in 67. The 8 new cases come from main: <code>t/t_llama_unit.cpp</code> has 44 TEST_CASE macros at 4c4b7b8864 and 52 on main 3bea58b788.</td></tr>
<tr><td>CTest registration of <code>t_amx_numerics</code></td><td class="num">-</td><td>SKIP_RETURN_CODE=4. Labels: fake, skip_return_code_4, slice_filter_catch2.</td></tr>
</table></div>
The whole of <code>t_amx_numerics</code> takes 0.013 s of test time. In the final pass the 9 sections of <code>t_amx_dispatch_dtype</code> take 0.132 s together, and the three new sections take 0.012 s, 0.008 s and 0.012 s. The first pass gave 0.134 s, and 0.011 s, 0.008 s and 0.011 s {ref(48)}.</li><li><strong>Object compare of the kernel file.</strong> The table is in card <a href="#D6">D6</a>. In short: 11 of 11 functions are identical between the reviewed commit and the final tree, and 10 of 11 between the measured commit and the final tree {ref(49)}.</li><li><strong>Registry (I25, I26).</strong>
<ul><li><code>bin/slice route</code> on delphi-3b35 answers <code>route: local-legacy</code>, with 8 cards: "Local cards are present; shared Dice is not configured." {ref(47)}</li><li><code>bin/slice bench --update</code> was not run. It measures on the first slot of each NUMA node. So one of the two tests always runs with the SYSTEM_CONFIG value <code>--instance 0,N</code>, which is the first half of the machine {ref(53)}. The test programs pin their threads by that value. Their logs print "INIT: Pinning application cores to ...", and <code>t_amx_dispatch_dtype</code> starts 55 pool workers {ref(48)}. That would put test threads on the CPUs of the two rinzler servers. This is the case that this part of the page named before the runs: the tool is skipped if it needs FPGA cards or the whole machine.</li><li>Done by hand instead: both <code>t_amx_numerics</code> rows gain <code>"skip_return_codes":[4]</code> [config/test-benchmarks.json:151 (genoa96), :494 (granite_rapids_6962p)]. Older text of this page named lines 152 and 492. The file equals the output of the tool's own formatter (<code>format_bench_json</code>), byte for byte.</li><li>Before the edit, the drift warning of the scheduler reads "t_amx_numerics: skip_return_codes=[] -> [4]". After the edit there is none. <code>bin/slice bench --check</code> and <code>bin/slice bench --check-platform</code> exit 0 before and after {ref(50)}.</li><li>The values <code>times</code> and <code>max_rss_mb</code> are not changed. Measured directly on our half, 5 runs each, with the registered command (<code>gen/&lt;test&gt; --benchmark-samples=2</code>), at 0.0% load on our CPUs: <code>t_amx_numerics</code> takes 0.66 to 0.69 s and 7 to 9 MiB. <code>t_amx_dispatch_dtype</code> takes 0.77 to 0.79 s and 97 to 99 MiB. The granite_rapids_6962p rows say 0.66 to 0.91 s and 0.60 to 0.85 s, and 8 MB for both. The 8 MB of <code>t_amx_dispatch_dtype</code> belongs to the default build with the option OFF, where the file holds only its placeholder case {ref(50)}.</li><li>The scheduled refresh (<code>bench-refresh.yml</code>, weekly) succeeded on 2026-11-01, 2026-11-08 and 2026-11-15 {ref(54)}.</li></ul></li><li><strong>Scripts:</strong> <code>~/workspace/intel-AMX/exec/pr5022-final-20261119/</code> holds the build, test, object-compare and registry-check scripts and a README with the rules for the shared machine and the results {ref(47)}.</li></ul>'''
cut('<h4>Runs on delphi-3b35: pending (compile and unit tests only,', '<code>bin/slice bench --check</code> (I25, I26).</li></ol>', RUNS,
    must_contain=('BUILD_INGEST_MODELS=ON', 'The runs start when the machine has been up for 15 minutes'))
rep('<li>Comment on #5021, posted together with the replies: add Isaac\'s spelling <code>amx_attn_h128</code> / <code>_128</code> (T12).</li></ul>',
    '<li>Comment on #5021, posted together with the replies: add Isaac\'s spelling <code>amx_attn_h128</code> / <code>_128</code> (T12).</li>'
    '<li>One PR comment with the A/B record files, posted together with the replies. The combined reply says that they are attached (T8).</li></ul>')

# ==========================================================================
# 6. Words used here
# ==========================================================================
rep('<li><strong>pre-review</strong>: a review of the edits of this round by an independent agent, before anything is pushed. '
    'It used the review checklists folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments.</li>',
    '<li><strong>pre-review</strong>: a review of the edits of this round by an independent agent, before anything is pushed. '
    'It used the review checklists folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments.</li>\n'
    '<li><strong>registry</strong>: the file config/test-benchmarks.json. It holds the run time, the peak memory and the skip codes of each test, per machine class. '
    'Slice reads it to schedule the tests. The command bin/slice bench --update measures a test and rewrites its rows.</li>\n'
    '<li><strong>NUMA node</strong>: one processor with its own memory. delphi-3b35 has two. Our half of the machine is node 1.</li>\n'
    '<li><strong>JUnit report</strong>: a test result file in XML form, with one entry per test case or section.</li>\n'
    '<li><strong>posting form</strong>: the wording of a reply as it is posted after the push. It reports what the final head contains. '
    'A placeholder in double brackets, such as ⟦HEAD⟧, stands for a value that exists only after the push.</li>')
a = s.index('<h2 id="words">')
b = s.index('</ul></details>', a)
n_terms = s[a:b].count('<li><strong>')
rep('<summary>Open the word list (37 terms)</summary>', f'<summary>Open the word list ({n_terms} terms)</summary>')

# ==========================================================================
# 7. References
# ==========================================================================
rep('prep.txt</code> of 2026-11-19 20:48 PST.', 'prep.txt</code> of 2026-11-20 05:48 PST.')
rep(f'the git tree hash <code>{TREE1}</code>, and the 11 files that differ from main with their sha256 sums.',
    f'the git tree hash <code>{TREE}</code>, and the 12 files that differ from main with their sha256 sums.')
RESDIR = '~/workspace/intel-AMX/exec/results/pr5022-final-20261119/'
REFS = f'''<li id="R47"><code>~/workspace/intel-AMX/exec/pr5022-final-20261119/README.md</code>, the README of the run. Its section "Results" gives the machine state before the runs (13:35 UTC) and after, the two passes, the build, the tests, the object compare and the registry.</li>
<li id="R48"><code>tests.txt</code> in the results folder <code>{RESDIR}</code>: the 14 runs with their exit codes and assertion counts at the tree c114b85944. The logs are <code>tests/*.log</code>, and the JUnit report is <code>tests/t_amx_numerics.junit.xml</code>. The section durations are in <code>tests/dispatch.log</code>, and those of the first pass in <code>first-pass-tree-5821ee86/tests/dispatch.log</code>.</li>
<li id="R49"><code>objcmp/objcmp.txt</code> and <code>objcmp/main-vs-final-4head.txt</code> in the results folder. The differing instructions are in <code>objcmp/diff-*.txt</code>.</li>
<li id="R50"><code>registry-check-before.txt</code>, <code>registry-check-after.txt</code> and <code>wall-times.txt</code> in the results folder.</li>
<li id="R51"><code>load-snapshot-after.txt</code> in the results folder, taken at 13:50 UTC: two rinzler processes of the account disagg with 31 busy threads each, our CPUs 0.0% busy, the four cards of node 1 not open, and 256 of 256 huge pages free on node 1.</li>
<li id="R52">Slack group message with John Pruitt, Austin Hill, Brian Hamon, Eddy Zhou and you (channel C0CKKMX08LC), John Pruitt on 2026-11-19 at 23:48 PST: "Reboots are done. I'm doing some more work on the machines but doesn't appear like I'll need to reboot them again. Still keeping to FPGAs 0-3 on delphi-3b35".</li>
<li id="R53"><code>bin/slice:2354-2365</code> and <code>:2419-2440</code> in the working tree: the update tool picks the first slot of each NUMA node and spreads the tests over these slots.</li>
<li id="R54"><code>gh run list</code> for <code>bench-refresh.yml</code> on 2026-11-20: the scheduled runs succeeded on 2026-11-01 (41275319942), 2026-11-08 (42449114688) and 2026-11-15 (43679257342). They failed on 2026-10-18 and 2026-10-25.</li>
<li id="R55"><code>tree.txt</code>, <code>prep.txt</code> and <code>build-final.txt</code> in the results folder, and the folder <code>first-pass-tree-5821ee86/</code>: the two tree hashes, the 12 files, the configure line, the compiler, 0 warnings, the 64 <code>tdpbf16ps</code> instructions, the build times of 304 s and 19 s, and the sha256 sums of the four binaries in both passes.</li>
<li id="R56">tron main at 0af590c21e, "Read streamed result latches atomically and clamp the sparse top-k (#5304)", committed 2026-11-20 05:17 UTC. That is 2026-11-19 21:17 PST. It is 1 commit after 3bea58b788 and changes 7 files. Of the 12 files of the final tree it changes only <code>config/test-benchmarks.json</code>. The trial merge ran in the session, and its output is not kept in a record file.</li>
'''
rep('The object files of the local compare are in the session\'s scratch folder, which is temporary.</li>\n</ol>',
    'The object files of the local compare are in the session\'s scratch folder, which is temporary.</li>\n' + REFS + '</ol>')

# ==========================================================================
# 8. How this was checked
# ==========================================================================
rep(f'All 7 are applied in the working tree, whose git tree hash is now <code>{TREE1}</code>.',
    f'All 7 are applied in the working tree, whose git tree hash was then <code>{TREE1}</code>.')
rep('because delphi-3b35 still had its old boot time at 20:47 PST. Nothing was committed, pushed or posted, and no issue was filed.</p>\n</main></body></html>',
    'because delphi-3b35 still had its old boot time at 20:47 PST. Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '<p><strong>Update of 2026-11-20: results and posting form.</strong> The build, the tests and the object compare ran on delphi-3b35 from 05:37 to 05:50 PST. '
    f'The final tree has the git tree hash <code>{TREE}</code>. '
    'Every number that this page states for these runs was compared with the result files: the test summary, the test logs, the JUnit report, the two object-compare files, '
    'the two registry-check files, the wall-time file, the load snapshot and the build record. '
    'One set of durations in my notes came from the first pass. The page gives the durations of the final pass and names the first pass beside them. '
    'Also checked on GitHub: the newest commit of main, and the run list of the weekly registry refresh. John Pruitt\'s message of 23:48 PST was read in Slack. '
    'All 41 reply drafts were read again. The 16 places that said "Will do" and the 30 places that said "I will" now report what the final head contains. '
    'Five values exist only after the push, so the replies hold the placeholders ⟦HEAD⟧, ⟦NIXRUN⟧, ⟦CMAKERUN⟧, ⟦RUNNER⟧ and ⟦ISSUE⟧. '
    'Every code block that a reply quotes was compared with the working tree again. '
    'Three statements of earlier versions were wrong or stale and are corrected: the plan named <code>BUILD_INGEST_MODELS=ON</code> for the test build, '
    'two replies cited the registry lines 152 and 492, and the T5 reply said that <code>t_amx_numerics</code> has no <code>skip_return_codes</code> entry. '
    'My watcher reported the reboot of delphi-3b35 8 hours late, because it compared a UTC time with a Pacific time. '
    'Two things in the replies need an action that the go list must carry: the A/B record files as a PR comment, and the comment on #5021. '
    'Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '</main></body></html>')

# ==========================================================================
# Final checks, then write
# ==========================================================================
reply_blocks = [(m.start(), div_end(m.start())) for m in re.finditer(r'<div class="reply">', s)]
for a0, b0 in reply_blocks:
    blk = s[a0:b0]
    assert '3997' not in blk, 'reply block mentions 3997: ' + blk[:120]
    assert 'Will do' not in blk, 'reply block says Will do: ' + blk[:160]
    assert not re.search(r'\bI will\b', blk), 'reply block says I will: ' + blk[:160]
    for bad in ('&lt;id&gt;', '&lt;runner&gt;', 'is pending', 'Proposed text', 'Proposed row', 'The registry refresh follows',
                'json:152', ':492', 'I plan to', 'will name the runner', 'will also carry', 'will cite', 'will be the only'):
        assert bad not in blk, f'reply block holds {bad!r}: ' + blk[:140]
a = s.index('<h2 id="todo">')
b = s.index('<h2 id="refs">')
assert '3997' not in s[a:b], 'Part C mentions 3997'
for stale in ('needs an AMX host', 'Not verified yet', 'Still open', 'has not run yet', 'wait for the reboot', 'wait for delphi-3b35',
              'Runs on delphi-3b35: pending', 'Pending on delphi-3b35', 'not edited yet', 'BUILD_INGEST_MODELS=ON</code> -DTRON',
              'Nothing is open for you now', 'tests on the server delphi-3b35 wait'):
    assert stale not in s, f'stale phrase left: {stale!r}'
n_refs = len(re.findall(r'<li id="R\d+">', s))
assert n_refs == 56, n_refs
for n in range(1, n_refs + 1):
    assert s.count(f'id="R{n}"') == 1 and f'href="#R{n}"' in s, f'R{n} missing or uncited'
for i in ('open', 'open2', 'open3', 'open4', 'D1-Q4', 'CI', 'combined'):
    assert s.count(f'id="{i}"') == 1, i

open(P, 'w', encoding='utf-8').write(s)
open(LAST, 'w').write(md5(P) + '\n')
ph = {p: s.count(p) for p in sorted(set(re.findall(r'⟦[^⟧]*⟧', s)))}
print(f'{n_rep} replacements; {len(s.encode("utf-8"))} bytes; {s.count(chr(10)) + 1} lines; {n_terms} terms; md5 {md5(P)}')
print('changed replies:', ' '.join(sorted(changed_replies, key=lambda x: (x[0] != 'T', x[0] == 'c', int(re.sub(r'\D', '', x) or 0)))))
print('placeholders:', ph)
