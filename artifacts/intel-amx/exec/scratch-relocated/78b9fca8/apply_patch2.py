#!/usr/bin/env python3
"""Second-stage patch of respond-2-Isaac.html.

Adds jhan's answers of the evening of 2026-11-19 and the facts verified that
evening. Idempotent: it always starts from the stage-1 copy of the page (the
page as it stood before this patch) and rewrites the page from it.
Run: python3 -I apply_patch2.py
"""
import hashlib
import sys
import textwrap

S = ('/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/'
     '78b9fca8-c24b-4ac2-a02d-0236a437cdd6/scratchpad/')
P = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
STAGE1 = S + 'respond-2-Isaac.stage1.html'
LAST = S + 'apply_patch2.last-md5'
STAGE1_MD5 = '668591e96b8f6382f3aded21a83b1fdf'


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


# Refuse to overwrite a page that somebody else changed.
assert md5(STAGE1) == STAGE1_MD5, 'stage-1 copy changed'
cur = md5(P)
known = {STAGE1_MD5}
try:
    known.add(open(LAST).read().strip())
except FileNotFoundError:
    pass
assert cur in known, f'page was changed outside this script (md5 {cur})'

s = open(STAGE1, encoding='utf-8').read()
n_rep = 0


def rep(old, new, count=1):
    """Replace `old` by `new`; `old` must occur exactly `count` times."""
    global s, n_rep
    c = s.count(old)
    assert c == count, f'anchor occurs {c} times, expected {count}: {old[:90]!r}'
    s = s.replace(old, new)
    n_rep += 1


def ref(n):
    return f'<a class="ref" href="#R{n}">[R{n}]</a>'


def cut(start_marker, end_marker, new, must_contain=()):
    """Replace the span from start_marker to the end of end_marker."""
    global s, n_rep
    assert s.count(start_marker) == 1, f'start marker count: {start_marker[:80]!r}'
    a = s.index(start_marker)
    b = s.index(end_marker, a) + len(end_marker)
    old = s[a:b]
    for m in must_contain:
        assert m in old, f'span lacks {m!r}'
    s = s[:a] + new + s[b:]
    n_rep += 1
    return old


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
rep('.open{background:#fffbeb;border-left:4px solid var(--warn);padding:10px 14px;margin:14px 0}',
    '.open{background:#fffbeb;border-left:4px solid var(--warn);padding:10px 14px;margin:14px 0}\n'
    '.open.done{background:#eff6ff;border-left-color:var(--accent)}\n'
    '.open figure{margin:8px 0 4px}\n'
    '.bars.wide .lab{width:var(--lw,260px);overflow-wrap:anywhere}\n'
    '.bars.wide .track{flex:1;min-width:0;display:flex;align-items:center;gap:10px}\n'
    '.bars.wide .track .fill{flex:none;width:calc(var(--v) * var(--k,0.8))}\n'
    '.bars.wide .track .n{white-space:nowrap}\n'
    '.bars.wide.k7{--k:0.7}\n'
    '@media (max-width:640px){.bars.wide .bar{flex-wrap:wrap;gap:2px 10px}.bars.wide .lab{width:100%;text-align:left}.bars.wide,.bars.wide.k7{--k:0.45}}')

# --------------------------------------------------------------------------
# 1. Header sub line, nav, Short version, intro of the decisions section
# --------------------------------------------------------------------------
rep('&middot; your decisions of 2026-11-19 applied &middot; nothing posted</p>',
    '&middot; your decisions of 2026-11-19 applied, with your answers of that evening &middot; nothing posted</p>')
rep('<a href="#decisions">Decisions</a>',
    '<a href="#decisions">Decisions</a><a href="#open2">Needs your word</a>')
rep('You made the six decisions on 2026-11-19, and the drafts below now follow them. '
    'Three points still need your word before anything is posted: two accepted edits now land '
    'without a throughput number, one new tracking issue is proposed, and the test runs at the '
    'final head move to the server delphi-3b35.</p></div>',
    'You made the six decisions on 2026-11-19 and answered the three open points that evening, '
    'and the drafts below follow both. Four smaller points still need your word, and the tests '
    'at the final head run on the server delphi-3b35 after John Pruitt reboots it.</p></div>')
rep('The drafts in Parts A to C now follow these decisions. A mark such as',
    'The drafts in Parts A to C now follow these decisions. The two boxes below hold your answers '
    'of the evening and the points that are still open. Card <a href="#CI">CI</a> describes the '
    'pre-merge CI process. A mark such as')

# --------------------------------------------------------------------------
# 2. Box #open: the three answers.  3. New box #open2: still needs your word.
# --------------------------------------------------------------------------
OPEN = f'''<div class="open done" id="open"><p><strong>The three open points: your answers of 2026-11-19, evening.</strong></p>
<ol>
<li><strong>I5 and I6 stay in this PR.</strong> Your words: "yes, let us do this `the PR body will say that the benchmarks predate them`. Basically we take this small risk and will see the result from nightly CI." You also asked to use the process that runs CI before a merge. Card <a href="#CI">CI</a> describes it {ref(34)}.</li>
<li><strong>The new tracking issue is approved.</strong> Your words: "looks good". The issue of card <a href="#N1">N1</a> is filed together with the replies, so that the replies can cite its number. Nothing is filed yet.</li>
<li><strong>The tests at the final head run on delphi-3b35.</strong> They start after John Pruitt's reboot of that machine {ref(40)}. They must not disturb the work of Brian Hamon and John Pruitt on the other half of the FPGA cards. The three unit-test programs use the fake device, so the runs open no FPGA card {ref(30)}. <a href="#todo">Part C</a> lists the other precautions.</li>
</ol></div>
<div class="open" id="open2"><p><strong>Still needs your word: four smaller points.</strong> The work goes on with the recommended choice in each case.</p>
<ol>
<li><strong>The promise of a separate PR for the Nix flag.</strong> The replies in <a href="#T1">T1</a> and <a href="#I7">I7</a> say: "I will open it as its own one-line PR under #3997". Keep that promise, or change the sentence to "that change stays with #3997"? Recommended: keep it. It is the strongest answer to his blocker. The drafts keep it.</li>
<li><strong>Merge main into the branch before the final head.</strong> The branch is 272 commits behind main. Its merge base is 6198824246 of 2026-10-16 {ref(42)}. Since then main changed six files that the branch or the review edits touch (figure below). GitHub reports no merge conflict {ref(42)}. Recommended: merge first. Then the tests, the object compare and the manual CI run cover the code that lands. The final head is being prepared that way. Say no if you want the edits on the reviewed commit.
<figure><div class="bars wide">
<div class="bar"><div class="lab"><code>config/test-benchmarks.json</code></div><div class="track"><div class="fill" style="--v:100%;background:#2a78d6"></div><div class="n">48</div></div></div>
<div class="bar"><div class="lab"><code>t/CMakeLists.txt</code></div><div class="track"><div class="fill" style="--v:16.67%;background:#2a78d6"></div><div class="n">8</div></div></div>
<div class="bar"><div class="lab"><code>t/t_llama_unit.cpp</code></div><div class="track"><div class="fill" style="--v:14.58%;background:#2a78d6"></div><div class="n">7</div></div></div>
<div class="bar"><div class="lab"><code>README.ci.md</code></div><div class="track"><div class="fill" style="--v:8.33%;background:#2a78d6"></div><div class="n">4</div></div></div>
<div class="bar"><div class="lab"><code>src/tron/CMakeLists.txt</code></div><div class="track"><div class="fill" style="--v:6.25%;background:#2a78d6"></div><div class="n">3</div></div></div>
<div class="bar"><div class="lab"><code>h/tron/models/self_attention.hpp</code></div><div class="track"><div class="fill" style="--v:6.25%;background:#2a78d6"></div><div class="n">3</div></div></div>
</div><figcaption>Commits on main since the merge base that change each file. Bar length is proportional to the count. The kernel files and the two AMX test files have 0 {ref(42)}.</figcaption></figure></li>
<li><strong>README.ci.md and your rule on issue numbers.</strong> The I8 paragraph keeps its link to #3997, because a README is documentation and not source code (card <a href="#D5">D5</a>). Say if your rule covers README files.</li>
<li><strong>The go to commit, push and post.</strong> Nothing is committed, pushed, posted or filed. I ask once, when the tests at the final head are in.</li>
</ol></div>'''
cut('<div class="open" id="open">', '</ol></div>', OPEN,
    must_contain=('Three points still need your word', 'second reply for that case', '#R30'))

# --------------------------------------------------------------------------
# 4. D1: pointer to the reply cards, a third step in Q2, the table cell, Q4
# --------------------------------------------------------------------------
rep('<p><strong>Your decision:</strong> the build flag for the required lane stays out of this PR. Issue #3997 keeps it.</p>',
    '<p><strong>Your decision:</strong> the build flag for the required lane stays out of this PR. Issue #3997 keeps it.</p>\n'
    '<p><strong>Where the proposed reply is:</strong> in cards <a href="#T1">T1</a> (the review body), '
    '<a href="#I7">I7</a> (the thread where he asks for the Nix flag) and <a href="#I8">I8</a> (the README paragraph). '
    'The first bullet of the <a href="#combined">combined reply</a> says the same in short.</p>')
rep('<h3>One combined reply to the review body (if you post a single comment)</h3>',
    '<h3 id="combined">One combined reply to the review body (if you post a single comment)</h3>')
rep('<td class="off"><span class="cellk">Not compiled</span>Same as today.</td></tr>',
    '<td class="off"><span class="cellk">Not compiled</span>Same as today for the kernels. '
    'The new transpose test case runs here, because it needs no AMX (I10).</td></tr>')
rep('The comment and README.ci.md stop claiming coverage that does not exist (I7, I8).</p>',
    'The comment and README.ci.md stop claiming coverage that does not exist (I7, I8). '
    'A third step was added on 2026-11-19: a manual run of the legacy CMake pipeline at the final head, '
    'which builds and tests with the option ON (card <a href="#CI">CI</a>).</p>')

Q4 = f'''<div class="qa" id="D1-Q4"><div class="q">Q4 (asked on 2026-11-19, evening). In the product, does llama-3.1-8b-instruct-good-tp2 run its attention on the CPU with AMX?</div>
<p><strong>Yes, on an Intel host with AMX.</strong></p>
<ul>
<li>The model's default is CPU attention. With <code>USE_HW_ATTN</code> unset, tron turns FPGA attention on for generated plugins only {ref(31)}.</li>
<li>llama uses the hand-written plugin. No hand-written plugin defines the <code>force_hw_attn</code> member: a search of <code>h/tron/plugins</code> returns 0 results {ref(31)}.</li>
<li>Nothing in the tron repository sets <code>USE_HW_ATTN</code> for the product. The only setters are one test registration and the repro script <code>bin/hugepage_exhaustion_repro.py</code> {ref(31)}.</li>
<li>The product package holds the AMX kernels (Q1). tron selects them at run time for every full 64-token page {ref(5)}.</li>
<li>Measured on delphi-3bda on 2026-10-02 with 8 users: AMX scored 96.5% of the decode K tokens at prompt 1024 and 98.9% at prompt 8192 {ref(32)}. The rest ran in the AVX loop, on pages that were not full yet.</li>
<li>Product evidence: the nightly row "AMX benchmark" runs this model with 32 users. It read 28.253 TPS on 2026-09-22, with a package that had no AMX kernels. It read 32.494 TPS on 2026-09-23, with the first package that had them. That is +15.0%. It read 33.27 TPS on 2026-11-19 {ref(33)} {ref(6)}.</li>
</ul>
<figure><div class="bars wide k7" style="--lw:300px">
<div class="bar"><div class="lab">2026-09-22, package without the kernels</div><div class="track"><div class="fill" style="--v:84.92%;background:#9ca3af"></div><div class="n">28.253 TPS</div></div></div>
<div class="bar"><div class="lab">2026-09-23, first package with the kernels</div><div class="track"><div class="fill" style="--v:97.67%;background:#2a78d6"></div><div class="n">32.494 TPS (+15.0%)</div></div></div>
<div class="bar"><div class="lab">2026-11-19, latest nightly report</div><div class="track"><div class="fill" style="--v:100%;background:#2a78d6"></div><div class="n">33.27 TPS</div></div></div>
</div><figcaption>Nightly row "AMX benchmark" on delphi-3bda: llama-3.1-8b-instruct-good-tp2 with 32 users. The row was added on 2026-09-22 with prompt 4096 and 1536 generated tokens. Bar length is proportional to TPS and starts at zero. The gray bar is the only one without the AMX kernels in the package. The Slack report prints its value as 28.3 {ref(33)} {ref(6)}.</figcaption></figure>
<p>Limits:</p>
<ul>
<li>On an AMD host the same package runs the AVX loop. AMD CPUs have no AMX.</li>
<li>The 96.5% and 98.9% figures come from our own build of main, run with runtron. They do not come from the product package. The nightly row is the product-package evidence.</li>
<li><strong>Insufficient data</strong> on one point: I did not read the service settings on a product host. The command <code>systemctl show rinzler@0 -p Environment</code> on such a host would show whether it sets <code>USE_HW_ATTN</code>.</li>
</ul>
<p>The FPGA cards still do the weight multiplications of each layer. Only the attention scoring runs on the CPU.</p>
</div>
'''
rep('</figure>\n</div>\n</div>\n\n<div class="dec" id="D2">',
    '</figure>\n</div>\n' + Q4 + '</div>\n\n<div class="dec" id="D2">')

# --------------------------------------------------------------------------
# 6. D2: the conflict with D6 is settled; D6 bullet; I5 and I6 cards
# --------------------------------------------------------------------------
rep('<p><strong>Not verified:</strong> the edit is not compiled. No tron build exists on a host I can use today. The spelling rests',
    '<p><strong>Not verified yet:</strong> the edit is not compiled. The build at the final head on delphi-3b35 compiles it, '
    'and that build waits for the reboot of the machine (<a href="#todo">Part C</a>). The spelling rests')
rep('<p><strong>Conflict with D6 (open point 1).</strong> I5 and I6 change code on the measured path, and D6 now has no rerun. '
    'Both edits remove work per dense page visit at 16 heads: one zero fill of 4096 bytes (I5) and 16 copies of 512 bytes each (I6). '
    'Neither changes a value. Their effect on throughput is not measured.</p>',
    '<p><strong>The conflict with D6 is settled by your answer of 2026-11-19, evening.</strong> I5 and I6 change code on the measured path, '
    'and D6 has no rerun. Your words: "yes, let us do this `the PR body will say that the benchmarks predate them`. '
    'Basically we take this small risk and will see the result from nightly CI." So both edits stay in this PR.</p>\n'
    '<ul>\n'
    '<li>Both edits remove work per dense page visit at 16 heads: one zero fill of 4096 bytes (I5) and 16 copies of 512 bytes each (I6). Neither changes a value.</li>\n'
    '<li>Their effect on throughput is not measured before the merge. The PR body will say that the benchmarks predate them.</li>\n'
    '<li>Before the merge, the manual run of the legacy CMake pipeline compiles and tests them with the AMX option ON (card <a href="#CI">CI</a>).</li>\n'
    '<li>After the merge, the nightly systems test shows the throughput of the Glimmer rows and the llama-3.1-8b rows.</li>\n'
    '</ul>')
rep('<li><strong>I5 and I6.</strong> They come after the measurement (open point 1).</li>',
    '<li><strong>I5 and I6.</strong> They come after the measurement. You decided on 2026-11-19 that they stay, '
    'and the PR body will say that the benchmarks predate them (card <a href="#D2">D2</a>).</li>')

# I5: reply limit paragraph, then the dashed alternative reply becomes a decision row.
rep('<p>One limit. The benchmarks in the PR body were measured before this edit, and I cannot rerun them (see my reply on benchmark provenance). '
    'The PR body will say that this edit has no throughput number.</p></div>',
    '<p>One limit. The benchmarks in the PR body predate this edit, and I cannot rerun them (see my reply on benchmark provenance). '
    'The PR body will say so.</p></div>')
cut('<div class="reply alt"><div class="lbl">If I5 moves to the performance follow-up (open point 1)</div>',
    'where it lands with a measurement.</p></div>',
    '<div class="row"><div class="k">Your decision</div><div>2026-11-19, evening: I5 stays in this PR. The PR body will say that the benchmarks predate it. '
    'You accept the small risk, and the nightly systems test after the merge is the check (card <a href="#D2">D2</a>). '
    'The second reply, for moving I5 to the follow-up issue, is removed.</div></div>',
    must_contain=('I will not change it in this PR. The line is on the path',))
# I6: same.
rep('<p>One limit. The benchmarks in the PR body were measured before this edit, and I cannot rerun them (see my reply on benchmark provenance). '
    'I have no timing for the saved 8 KB of copies per page visit, and the PR body will say so.</p>',
    '<p>One limit. The benchmarks in the PR body predate this edit, and I cannot rerun them (see my reply on benchmark provenance). '
    'I have no timing for the saved 8 KB of copies per page visit. The PR body will say that the benchmarks predate this edit.</p>')
cut('<div class="reply alt"><div class="lbl">If I6 moves to the performance follow-up (open point 1)</div>',
    'where it lands with a measurement.</p></div>',
    '<div class="row"><div class="k">Your decision</div><div>2026-11-19, evening: I6 stays in this PR. The PR body will say that the benchmarks predate it. '
    'You accept the small risk, and the nightly systems test after the merge is the check (card <a href="#D2">D2</a>). '
    'The second reply, for moving I6 to the follow-up issue, is removed.</div></div>',
    must_contain=('I will not change it in this PR. The block is on the path',))
assert 'class="reply alt"' not in s

# D5: pointer to the open point.
rep('The I8 paragraph keeps its link to #3997. Say if your rule covers README files too.</li>',
    'The I8 paragraph keeps its link to #3997. Say if your rule covers README files too '
    '(point 3 of the box <a href="#open2">Still needs your word</a>).</li>')

# --------------------------------------------------------------------------
# 5. New card CI, before N1.   8. N1: approved.
# --------------------------------------------------------------------------
CI = f'''<div class="dec" id="CI"><div class="t">CI. The pre-merge CI process: a manual run of the legacy CMake pipeline <span class="decided">found</span></div>
<p><strong>Your request of 2026-11-19, evening:</strong> "I remember there is a process to run CI before merging PR. We can use that process to run through CI".</p>
<pre><code>gh workflow run cmake-single-platform.yml --ref jhan-amx-kvmul16 -F skip_benchmarks=true</code></pre>
<ul>
<li><strong>Source.</strong> Hannah Van Eenoo wrote this command into README.ci.md on 2026-09-11, in the section "CMake and CTest". Her words there: "run it on the final PR commit and wait for both pipelines before merging" {ref(34)}. Her #software announcement of that day is "Required jobs for tron repo merge are changing TODAY" {ref(35)}.</li>
<li><strong>Why it helps this PR.</strong> It is the only CI pipeline that configures with <code>-DTRON_AMX_DISPATCH=ON</code> {ref(36)}. So it compiles, links and tests the AMX code that the required lane leaves out.</li>
<li><strong>Where it runs.</strong> Each of its build and test jobs runs on one of 7 runners that carry the labels self-hosted, fpga, test and avx512 {ref(36)}. Four are AMD: andoria-02, andoria-09, andoria-14 and andoria-ee10. Three are Intel Granite Rapids: delphi-17cf, delphi-3af6 and delphi-3bd6. GitHub picks the runner for each job. The run does not use delphi-3bda or delphi-3b35.</li>
<li><strong>State.</strong> The last manual run was on 2026-09-11 (run 34633703482). The release path ran the same pipeline for the tags v2.0.0-rc1 (2026-11-03, run 41738148954) and v2.0.0-rc2 (2026-11-13, run 43511108942). Its build, test-host and test-fpga jobs passed both times {ref(37)}. The workflow file on the PR branch differs from main by one comment line {ref(37)}.</li>
<li><strong>Duration.</strong> The pipeline part of the v2.0.0-rc2 run took 53 minutes. In the v2.0.0-rc1 run it took 17.6 hours: its test-fpga job started 14.8 hours after its test-host job had ended {ref(37)}. So a run can take from about one hour to most of a day.</li>
<li><strong>When.</strong> After the final head is pushed. The run uses the workflow file and the code of the pushed branch.</li>
</ul>
<table class="grid">
<tr><th style="width:30%">What we get</th><th>Manual CMake run, before the merge</th><th>Nightly systems test, after the merge</th></tr>
<tr><th>The AMX code compiles and links in CI</th><td class="on"><span class="cellk">Yes</span></td><td class="on"><span class="cellk">Yes</span>The nightly package is built with the option ON.</td></tr>
<tr><th>The AMX unit tests execute</th><td class="new"><span class="cellk">Only on an Intel runner</span>On an AMD runner the kernel cases are reported as skipped, and the job still passes.</td><td class="off"><span class="cellk">No</span>The nightly test runs no unit tests.</td></tr>
<tr><th>Throughput with AMX</th><td class="off"><span class="cellk">No</span></td><td class="on"><span class="cellk">Yes</span>The Glimmer rows and the llama-3.1-8b rows.</td></tr>
</table>
<p>Limits:</p>
<ul>
<li>A passing log has one line per test binary. Slice uploads the output of a test only when the test fails (card <a href="#T4">T4</a>). So the log does not show whether the kernel cases ran or were skipped. The runner name shows it.</li>
<li>The benchmark step of this pipeline has only the AMD class active. The Intel class is commented out {ref(36)}. So <code>skip_benchmarks</code> stays <code>true</code>.</li>
<li>No process runs the nightly test on an unmerged PR. The package publish for feature branches is switched off: <code>FEATURE_TESTING_PUBLISH</code> is "0" in publish-deb.yml {ref(38)}.</li>
<li>The nightly keeps the throughput rows of Glimmer and llama-3.1-8b. Since 2026-11-19 it also runs Glimmer in the soak test {ref(39)}.</li>
<li>This is the only process for "run CI before merging" that I found in Hannah Van Eenoo's Slack messages since August 2026. Say if you meant a different announcement.</li>
</ul>
</div>

'''
rep('<div class="dec" id="N1"><div class="t">N1. New tracking issues for the rest of his comments: one, for your review</div>',
    CI + '<div class="dec" id="N1"><div class="t">N1. New tracking issues for the rest of his comments: one <span class="decided">approved</span></div>')
rep('<p><strong>One new issue is needed.</strong> Every other comment is handled in this PR, belongs to an issue that exists, or needs none.</p>',
    '<p><strong>One new issue is needed, and you approved its draft on 2026-11-19, evening: "looks good".</strong> '
    'It is filed together with the replies, so that the replies can cite its number. Nothing is filed yet. '
    'Every other comment is handled in this PR, belongs to an issue that exists, or needs none.</p>')
rep('<p>Draft of the new issue. If you move I5 and I6 out of this PR (open point 1), they become items 5 and 6.</p>',
    '<p>Draft of the new issue, as approved. I5 and I6 stay in this PR, so the issue keeps its four items.</p>')
rep('<p>Proposed comment on #5021, also not posted:',
    '<p>Proposed comment on #5021, not posted yet. It goes out together with the replies:')

# --------------------------------------------------------------------------
# 7. Replies: T1, T5 caveat, combined reply, I7 (new paragraph + comment text)
#    Coordinator corrections: I7 comment block, I8 paragraph, I14 sentence
# --------------------------------------------------------------------------
rep('so they name the lanes that exist at this head (text under your inline comments at src/tron/CMakeLists.txt:216).</p>',
    'so they name the lanes that exist at this head (text under your inline comments at src/tron/CMakeLists.txt:216).</p>\n'
    '<p>For this PR\'s own evidence I will also run the legacy CMake lane by hand at the final head '
    '(<code>cmake-single-platform.yml</code>), which builds and tests with the option ON, and I will post the run id and the test-host runner.</p>')
rep('<p>One caveat on the dispatch itself. The last runs of that workflow (2026-09-28 to 2026-09-30) were <code>pull_request</code> events '
    'from before the trigger change, with build and test-host skipped, and the 2026-10-30 <code>publish-deb</code> dispatch also skipped its call into it. '
    'Whether a manual dispatch runs end to end after the GCP Nix cutover is unknown until tried.</p>',
    '<p>One caveat on the dispatch itself. The last manual run of that workflow was on 2026-09-11 (run 34633703482). '
    'Since then it ran end to end only through the release path: the tag runs for v2.0.0-rc1 (2026-11-03, run 41738148954) '
    'and v2.0.0-rc2 (2026-11-13, run 43511108942) completed its build, test-host and test-fpga jobs. '
    'No manual dispatch on a branch has run since 2026-09-11.</p>')
rep('<li><strong>Linked AMX-on build.</strong> Manual <code>cmake-single-platform.yml</code> dispatch at the final head; '
    'it proves compile and link only, and the body will say so.</li>',
    '<li><strong>Linked AMX-on build.</strong> Manual <code>cmake-single-platform.yml</code> run at the final head. '
    'It builds and tests with the option ON. The kernel cases execute only if its test-host job lands on a Granite Rapids runner, '
    'and the body will name the runner.</li>')

# I7 comment block: the transpose case of I10 runs in every build.
OLD_CMT = '# so t_amx_numerics and t_amx_dispatch_dtype run their SUCCEED stubs there.\n'
NEW_CMT = ('# so there t_amx_dispatch_dtype holds only its SUCCEED stub, and\n'
           '# t_amx_numerics only that stub and the AVX-512 transpose case.\n')
for line in NEW_CMT.splitlines():
    assert len(line) <= 79, (len(line), line)
rep(OLD_CMT, NEW_CMT)
a = s.index('<pre><code># fast-path call sites. No pull-request lane sets the option:')
b = s.index('</code></pre>', a)
for line in s[a + len('<pre><code>'):b].splitlines():
    assert len(line) <= 79, (len(line), line)
# I7: the new evidence paragraph.
rep('<p>On <code>-DTRON_AMX_DISPATCH=ON</code> in the Nix <code>cmake_args</code>: agreed that it is the right fix',
    '<p>For this PR\'s own evidence I will run the legacy CMake lane by hand at the final head. '
    'It configures with the option ON, so it compiles, links and tests the AMX code. '
    'I will post the run id and the test-host runner here. '
    'The kernel cases execute only if that job lands on a Granite Rapids runner, '
    'so the Verification section also carries a per-section record from a Granite Rapids host.</p>\n'
    '<p>On <code>-DTRON_AMX_DISPATCH=ON</code> in the Nix <code>cmake_args</code>: agreed that it is the right fix')

# I8 README paragraph: same correction, tail of the paragraph wrapped again at 80 columns.
TAIL_START = 'with it OFF, so there `t_amx_numerics` and `t_amx_dispatch_dtype` hold only\n'
TAIL_END = 'a required check is tracked in https://github.com/positron-ai/tron/issues/3997.'
assert s.count(TAIL_START) == 1 and s.count(TAIL_END) == 1
a = s.index(TAIL_START)
b = s.index(TAIL_END, a) + len(TAIL_END)
tail = ' '.join(s[a:b].split('\n'))
OLD_SENT = 'so there `t_amx_numerics` and `t_amx_dispatch_dtype` hold only their placeholder case'
NEW_SENT = ('so there `t_amx_dispatch_dtype` holds only its placeholder case, and `t_amx_numerics` '
            'holds that placeholder and the transpose case, which needs no AMX')
assert tail.count(OLD_SENT) == 1
tail = tail.replace(OLD_SENT, NEW_SENT)
wrapped = textwrap.fill(tail, width=80, break_long_words=False, break_on_hyphens=False)
assert max(len(x) for x in wrapped.split('\n')) <= 80
s = s[:a] + wrapped + s[b:]
n_rep += 1

# I14: where the asserts live after I10.
rep('lanes 0..3");</code></pre>\n<p>History, for the record.',
    'lanes 0..3");</code></pre>\n'
    '<p>Both asserts now sit in <code>transpose_scores</code> in the new header <code>h/tron/kernels/amx_attn_transpose.hpp</code>, '
    'next to the ladder they guard (see the thread at amx_attn.cpp:156).</p>\n'
    '<p>History, for the record.')

# --------------------------------------------------------------------------
# 9. Part C
# --------------------------------------------------------------------------
rep('<h2 id="todo">Part C. Consolidated to-do (after the decisions)</h2><h4>Code and comment edits (one text per file, conflicts resolved)</h4>',
    '<h2 id="todo">Part C. Consolidated to-do (after the decisions)</h2>'
    '<h4>First step: merge main into the branch (pending your word, recommended)</h4>'
    f'<p>The branch is 272 commits behind main {ref(42)}. The review edits touch files that main changed since the merge base. '
    'So the edits are made on the merged tree (point 2 of the box <a href="#open2">Still needs your word</a>). '
    'The line numbers in the list below are those of the reviewed commit 4c4b7b8864.</p>'
    '<h4>Code and comment edits (one text per file, conflicts resolved)</h4>')
rep('<li><code>h/tron/kernels/amx_attn_transpose.hpp</code> (new): <code>transpose_scores&lt;group_heads&gt;</code> as an inline template, '
    'AVX-512 intrinsics only (I10).</li><li><code>src/tron/kernels/amx_attn.cpp</code>: lines 213-215 static_asserts (I14 text, Isaac\'s form); '
    'line 269 comment (I15 text); stages 1-4 moved out to the header (I10).</li>',
    '<li><code>h/tron/kernels/amx_attn_transpose.hpp</code> (new): <code>transpose_scores&lt;group_heads&gt;</code> as an inline template, '
    'AVX-512 intrinsics only (I10). It also holds the two static_asserts in Isaac\'s form, next to the ladder they guard (I14).</li>'
    '<li><code>src/tron/kernels/amx_attn.cpp</code>: stages 1-4 move out to the new header, and the static_asserts of lines 213-215 move with them (I10, I14); '
    'line 269 comment (I15 text).</li>')
rep('the compare result, and one sentence that the I5 and I6 edits came after the measurement and have no throughput number (D2, D6).</li>',
    'the compare result, and one sentence that the benchmarks predate the I5 and I6 edits (D2, your answer of 2026-11-19).</li>')
rep('one build, one test pass, one registry refresh, one body refresh, in that order)</h4>\n<ol>',
    'one build, one test pass, one registry refresh, one body refresh, in that order)</h4>\n'
    '<ul>'
    f'<li><strong>Start:</strong> after John Pruitt\'s reboot of delphi-3b35. He announced it in Slack on 2026-11-19 at 17:54 PST {ref(40)}. '
    f'At 19:09 PST the boot time was still 2026-08-24 16:12:16 {ref(41)}. He wrote "some rebooting", so more than one reboot is possible. '
    'The runs start when the machine has been up for 15 minutes.</li>'
    f'<li><strong>No FPGA card is opened.</strong> The three unit-test programs use the fake device {ref(30)}. '
    'The half of the cards that Brian Hamon and John Pruitt use is not touched.</li>'
    '<li><strong>CPUs:</strong> everything is pinned to our CPUs 96-143 and runs at low priority.</li>'
    '<li><strong>Before the first run:</strong> the load snapshot, and one more read of John Pruitt\'s Slack thread.</li>'
    '<li><strong>Registry refresh:</strong> <code>bin/slice bench --update</code> runs only after a read of what it touches. '
    'It is skipped if it needs FPGA cards or the whole machine.</li>'
    '</ul>\n<ol>')
rep('<p>Needs your OK (open point 1): if I5 and I6 stay in this PR, one token-identity pair on delphi-3b35, measured commit against final head, '
    'for llama-3.1-8b and Glimmer at prompt 1024. It is a pass or fail check on one machine, and it uses the FPGA cards.</p>',
    '<p>Not run: the token-identity pair on delphi-3b35 (measured commit against final head, llama-3.1-8b and Glimmer at prompt 1024). '
    'It would use the FPGA cards. On 2026-11-19 you accepted the small risk of I5 and I6 without it. '
    'The nightly systems test after the merge is the check.</p>')
rep('at the final head; record run and job ids and the test-host runner (T5).</li>',
    'at the final head; record run and job ids and the test-host runner (T5). '
    'This is the pre-merge CI process you asked for (card <a href="#CI">CI</a>). It needs the final head pushed.</li>')
rep('under #3997, CI owner as reviewer (D1).</li><li>New issue, after your review of card N1:',
    'under #3997, CI owner as reviewer (D1). Whether the replies promise it is point 1 of the box '
    '<a href="#open2">Still needs your word</a>.</li><li>New issue, approved on 2026-11-19 and filed together with the replies:')
rep('<li>Comment on #5021, after your review of card N1:',
    '<li>Comment on #5021, posted together with the replies:')

# --------------------------------------------------------------------------
# 10. Words used here
# --------------------------------------------------------------------------
rep('With it OFF, both AMX test binaries hold one placeholder case that reports SUCCEED.</li>',
    'With it OFF, both AMX test binaries hold one placeholder case that reports SUCCEED. '
    'After the I10 edit, t_amx_numerics also holds the transpose case, which needs no AMX.</li>')
rep('<li><strong>kill switch</strong>: TRON_AMX_DISABLE=1: the same binary with AMX turned off at run time.</li>',
    '<li><strong>kill switch</strong>: TRON_AMX_DISABLE=1: the same binary with AMX turned off at run time.</li>\n'
    '<li><strong>CPU attention / FPGA attention / USE_HW_ATTN</strong>: where tron computes the attention scores of a layer. '
    'The environment variable USE_HW_ATTN selects it. When it is unset, generated plugins use FPGA attention and hand-written plugins use CPU attention. '
    'The value 0 selects CPU attention for every model.</li>\n'
    '<li><strong>hand-written plugin / generated plugin</strong>: a model definition written by hand in C++ (the llama family, h/tron/plugins/llama.hpp), '
    'or produced by the ingest tool (Muse Glimmer, gpt-oss, qwen3).</li>\n'
    '<li><strong>K token</strong>: one stored key vector that one query scores. The attention counters report the AMX, AVX and FPGA shares in K tokens.</li>')
rep('<li><strong>CMake lane</strong>: cmake-single-platform.yml, the legacy workflow. It passes -DTRON_AMX_DISPATCH=ON but runs only on manual dispatch '
    'or when publish-deb.yml calls it on a tag push.</li>',
    '<li><strong>CMake lane / legacy CMake pipeline</strong>: cmake-single-platform.yml, the legacy workflow. It passes -DTRON_AMX_DISPATCH=ON but runs only on manual dispatch '
    'or when publish-deb.yml calls it on a tag push. A manual run of it on the final commit of a pull request is the pre-merge CI process (card CI).</li>\n'
    '<li><strong>runner</strong>: a lab machine that executes CI jobs. The Delphi runners are Intel Xeon machines (Granite Rapids) with AMX. '
    'The Andoria runners are AMD machines (Genoa) without AMX.</li>')
rep('<li><strong>nightly systems test</strong>: the run that installs the nightly tron package on delphi-3bda every night and reports throughput per model.</li>',
    '<li><strong>nightly systems test</strong>: the run that installs the nightly tron package on delphi-3bda every night and reports throughput per model.</li>\n'
    '<li><strong>soak test</strong>: the part of the nightly systems test that keeps several models under load for a long time and counts errors.</li>')
rep('merge base 6198824246 is the shared ancestor of main and the branch. head 4c4b7b8864',
    'merge base 6198824246 is the shared ancestor of main and the branch. On 2026-11-19 main is 272 commits ahead of it. head 4c4b7b8864')
a = s.index('<h2 id="words">')
b = s.index('</ul></details>', a)
n_terms = s[a:b].count('<li><strong>')
rep('<summary>Open the word list (27 terms)</summary>', f'<summary>Open the word list ({n_terms} terms)</summary>')

# --------------------------------------------------------------------------
# 11. References R31..R42
# --------------------------------------------------------------------------
REFS = '''<li id="R31">tron main at 3bea58b788. <code>h/tron/models/hw_attn_config.hpp:12</code>: "USE_HW_ATTN unset defaults to enabled for *ingested* models, disabled for others". <code>h/tron/models/model.hpp:761-767</code>: <code>model_forces_hw_attn</code> returns the plugin's <code>force_hw_attn</code> member, and false when the plugin has none. <code>ingest/src/TronCpp.hs:258</code>: the ingest tool writes <code>force_hw_attn = true</code> into each generated plugin. Searches: <code>force_hw_attn</code> in <code>h/tron/plugins</code> returns 0 results. <code>USE_HW_ATTN</code> occurs in 7 files. Four of them read or describe it (3 under <code>h/</code>, 1 under <code>src/</code>). Two set it: <code>t/CMakeLists.txt:598</code> for one test, and <code>bin/hugepage_exhaustion_repro.py</code>. The seventh, <code>t/heterogeneous_scheduler_compile.cpp:917</code>, is a comment.</li>
<li id="R32"><code>~/workspace/intel-AMX/PR3879/new-PRs/new-counters/attn-stats-compare.md</code>, the report of the campaign attnstats-20261002 (delphi-3bda, 2026-10-02): cells <code>l8b-8u-p1024-cpu</code> and <code>l8b-8u-p8192-cpu</code>, and section 2.3 with the 96.5% and 98.9% shares.</li>
<li id="R33">Nightly reports of 2026-09-22 and 2026-09-23 in Slack #ci-cd-notifications. The <a href="https://positronai.slack.com/archives/C06S8PNDBQA/p1790095827478439">note of 2026-09-22 09:50 PDT</a> introduces the row: 32 users, prompt length 4k, "a baseline with no AMX changes present". The row means come from the run logs: 28.253 TPS with package 2026.09.18-3faba6d0 (no AMX code), and 32.494 TPS with package 2026.09.23-5cf65b92. Records: <code>~/workspace/intel-AMX/CI-test/status/first-CI-AMX-row-20260922.html</code> and <code>CI-AMX-row-20260923.html</code>.</li>
<li id="R34"><code>README.ci.md:97-114</code> on main at 3bea58b788, section "CMake and CTest (<code>cmake-single-platform.yml</code>)". Commit 2f1ee29982 of 2026-09-11 by Hannah Van Eenoo added it: "ci: Retain manual legacy checks for the GCP Nix cutover".</li>
<li id="R35">Slack #software, Hannah Van Eenoo, <a href="https://positronai.slack.com/archives/C057NJGDW4T/p1789144049264719">2026-09-11 09:27 PDT</a>: "Required jobs for tron repo merge are changing TODAY". Searches of her messages since August 2026 for CI, merge, label and queue returned no other process. Her note of 2026-08-03 on the label <code>Run CI</code> concerns draft pull requests only, and PR 5022 is not a draft.</li>
<li id="R36"><code>.github/workflows/cmake-single-platform.yml</code> on main at 3bea58b788: lines 353-355 (the configure line with <code>-DTRON_AMX_DISPATCH=ON</code>), lines 151, 381 and 510 (the runner labels of the build, test-host and test-fpga jobs), lines 678-689 (the benchmark matrix: the class 2x96core is active, the Intel class 2x72core is commented out). Runner table: <code>README.ci.md:447-457</code> on main.</li>
<li id="R37"><code>gh run list</code> and <code>gh run view</code> for positron-ai/tron. Manual runs of <code>cmake-single-platform.yml</code>: the latest is 34633703482 of 2026-09-11, with success. Runs of <code>publish-deb.yml</code> on tags: 41738148954 (v2.0.0-rc1, pipeline part from 2026-11-03 23:19 to 2026-11-04 16:56 UTC) and 43511108942 (v2.0.0-rc2, 2026-11-13 from 21:29 to 22:22 UTC). In both, the jobs test / build, test / test-host, test / test-fpga and test / test ended with success. <code>git diff 6198824246 origin/main</code> for the workflow file: 1 line, a comment.</li>
<li id="R38"><code>.github/workflows/publish-deb.yml:29-32</code> on main at 3bea58b788: <code>FEATURE_TESTING_PUBLISH: "0"</code>, under the comment "Feature-branch publishes to testing stay disabled".</li>
<li id="R39">systems_test pull request <a href="https://github.com/positron-ai/systems_test/pull/283">283</a>, "Trim nightly model list and add Glimmer-30B to soaks", merged 2026-11-19 17:41 UTC. It removes qwen-2.5-32b-it-fast-tp2 and gemma-2-9b-it-fast-tp2 from the throughput suite. It adds <code>ingested-meta-models--Muse-Glimmer-30B-tp4</code> to the soak models.</li>
<li id="R40">Slack group message with John Pruitt, Austin Hill, Brian Hamon, Eddy Zhou and you, 2026-11-19. John Pruitt at <a href="https://positronai.slack.com/archives/C0CKKMX08LC/p1795139699960739">17:54 PST</a>: "I'd like to do some rebooting of delphi-3b35 and hercules-a4d8 tonight to close out some disagg work." At <a href="https://positronai.slack.com/archives/C0CKKMX08LC/p1795139922822639">17:58 PST</a>: "may not be for another hour or 2". Austin Hill (18:00 PST) and Eddy Zhou (18:01 PST) answered that he can go ahead. The thread holds no written answer from Brian Hamon or from you.</li>
<li id="R41"><code>ssh delphi-3b35</code> on 2026-11-19 at 19:01 and 19:09 PST: boot time 2026-08-24 16:12:16, 87 days up. No job of ours ran there. The account disagg used about 31 CPUs.</li>
<li id="R42">GitHub and git: PR 5022 is mergeable, is not a draft, carries the label "Skip benchmarks", and has review decision CHANGES_REQUESTED at head 4c4b7b8864. Merge base with main: 6198824246 of 2026-10-16 18:11 UTC. <code>git rev-list --count 6198824246..origin/main</code> at 3bea58b788: 272. Commits on main since the merge base, per file: <code>config/test-benchmarks.json</code> 48, <code>t/CMakeLists.txt</code> 8, <code>t/t_llama_unit.cpp</code> 7, <code>README.ci.md</code> 4, <code>src/tron/CMakeLists.txt</code> 3, <code>h/tron/models/self_attention.hpp</code> 3, <code>bin/slice</code> 2. The two kernel files and the two AMX test files: 0.</li>
'''
rep('link <code>pos_fake</code>, the fake device, and carry the label <code>fake</code>.</li>\n</ol>',
    'link <code>pos_fake</code>, the fake device, and carry the label <code>fake</code>.</li>\n' + REFS + '</ol>')

# --------------------------------------------------------------------------
# 12. How this was checked
# --------------------------------------------------------------------------
rep('Nothing was posted to GitHub, and no issue was filed.</p>\n</main></body></html>',
    'Nothing was posted to GitHub, and no issue was filed.</p>\n'
    '<p><strong>Update of 2026-11-19, evening.</strong> Your answers to the three open points were applied. '
    'Checked that evening: the attention default of the llama plugin at main 3bea58b788, the measured AMX share in the campaign report of 2026-10-02, '
    'the nightly rows of 2026-09-22, 2026-09-23 and 2026-11-19, README.ci.md and the workflow files for the manual CMake pipeline, the run history of that pipeline, '
    'the nightly model list, John Pruitt\'s Slack messages, the boot time of delphi-3b35, and the distance of the PR branch from main. '
    'Three reply texts changed because the new transpose test of I10 runs in every build: the CMake comment (I7), the README paragraph (I8) and the place of the two asserts (I14). '
    'One caveat in the T5 reply was replaced by the measured run history. '
    'Not done at the time of this update: the code edits are not compiled, and no test ran at the final head. '
    'One limit: the service settings of a product host were not read (card D1, Q4). '
    'Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '</main></body></html>')

# --------------------------------------------------------------------------
# Final checks, then write
# --------------------------------------------------------------------------
for stale in ('Three points still need your word', 'Needs your OK (open point 1)',
              'If I5 moves to the performance follow-up', 'If I6 moves to the performance follow-up',
              'open point 1', '19:35', 'unknown until tried', 'for your review'):
    assert stale not in s, f'stale phrase left: {stale!r}'
for n in range(31, 43):
    assert s.count(f'id="R{n}"') == 1, n
    assert f'href="#R{n}"' in s, f'R{n} is never cited'

open(P, 'w', encoding='utf-8').write(s)
open(LAST, 'w').write(md5(P) + '\n')
print(f'{n_rep} replacements; {len(s.encode("utf-8"))} bytes; {s.count(chr(10)) + 1} lines; {n_terms} terms; md5 {md5(P)}')
