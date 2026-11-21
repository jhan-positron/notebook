#!/usr/bin/env python3
"""Third-stage patch of respond-2-Isaac.html (page pass 3, 2026-11-19 evening).

Applies sections A to F and D2 of page-pass-3-brief.md on top of the page as
apply_patch2.py left it. Idempotent: it always starts from the stage-2 copy.
Run: python3 -I apply_patch3.py
"""
import hashlib
import html
import re

S = ('/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/'
     '78b9fca8-c24b-4ac2-a02d-0236a437cdd6/scratchpad/')
P = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
STAGE2 = S + 'respond-2-Isaac.stage2.html'
LAST = S + 'apply_patch3.last-md5'
STAGE2_MD5 = '1096666e58e6bc74abcb24c91acc1edf'
TREE = 'bbe06f7ed06cf6e265c2a017614b75ee555be3b7'


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


assert md5(STAGE2) == STAGE2_MD5, 'stage-2 copy changed'
known = {STAGE2_MD5}
try:
    known.add(open(LAST).read().strip())
except FileNotFoundError:
    pass
assert md5(P) in known, f'page was changed outside this script (md5 {md5(P)})'

s = open(STAGE2, encoding='utf-8').read()
n_rep = 0


def rep(old, new, count=1):
    global s, n_rep
    c = s.count(old)
    assert c == count, f'anchor occurs {c} times, expected {count}: {old[:100]!r}'
    s = s.replace(old, new)
    n_rep += 1


def ref(n):
    return f'<a class="ref" href="#R{n}">[R{n}]</a>'


def esc(code):
    return html.escape(code, quote=False)


def card_span(cid):
    a = s.index(f'<div class="card" id="{cid}">')
    b = s.find('<div class="card" id="', a + 10)
    assert b > a
    return a, b


def div_end(start):
    """Index just past the </div> that closes the <div ...> starting at `start`."""
    depth = 0
    for m in re.finditer(r'<div\b|</div>', s[start:]):
        depth += -1 if m.group(0) == '</div>' else 1
        if depth == 0:
            return start + m.end()
    raise AssertionError('unbalanced div')


def reply_span(cid):
    a, b = card_span(cid)
    r = s.index('<div class="reply">', a)
    assert r < b, cid
    return r, div_end(r)


def replace_reply(cid, inner, after=''):
    """Replace the whole reply block of a card; `after` goes right behind it."""
    global s, n_rep
    r, e = reply_span(cid)
    s = s[:r] + '<div class="reply"><div class="lbl">Reply</div>' + inner + '</div>' + after + s[e:]
    n_rep += 1


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


# --------------------------------------------------------------------------
# Header line, nav, Short version, intro of the decisions section
# --------------------------------------------------------------------------
rep('&middot; your decisions of 2026-11-19 applied, with your answers of that evening &middot; nothing posted</p>',
    '&middot; your decisions of 2026-11-19 applied, with your two rounds of answers of that evening &middot; nothing posted</p>')
rep('<a href="#open2">Needs your word</a>', '<a href="#open3">Needs your word</a>')
rep('You made the six decisions on 2026-11-19 and answered the three open points that evening, '
    'and the drafts below follow both. Four smaller points still need your word, and the tests '
    'at the final head run on the server delphi-3b35 after John Pruitt reboots it.</p></div>',
    'You made the six decisions on 2026-11-19 and answered the open points in two rounds that evening, '
    'and the drafts below follow them: the D1 replies are now short and do not mention issue 3997. '
    'The code edits are done in an uncommitted working tree, two new small points need your word, '
    'and the tests on the server delphi-3b35 wait for John Pruitt\'s reboot of that machine.</p></div>')
rep('The two boxes below hold your answers of the evening and the points that are still open.',
    'The three boxes below hold your answers of the evening, in two rounds, and the two points that are still open.')

# --------------------------------------------------------------------------
# A. Box #open2: the second-round answers.   B. New box #open3.
# --------------------------------------------------------------------------
OPEN23 = f'''<div class="open done" id="open2"><p><strong>The four smaller points: your answers of the second round (2026-11-19, about 19:27 PST).</strong></p>
<ol>
<li><strong>The promise of a separate PR for the Nix flag: dropped.</strong> Your words: "I kind of think Issac and we are treating this too serious than what it deserves. We did the manual testing at CI machine delphi-3bda when we had the access, so all the tests were CI equivalent, but not run from CI process. I leave the decision to you, if you can think of a simpler change and explaination and without mentioning issue 3997 at all, that would be great; if you think what you current have is the best to move forward, please do." My choice: the simpler form. The comment fix and the README fix are short. The replies in <a href="#T1">T1</a>, <a href="#I7">I7</a> and <a href="#I8">I8</a> are short. The flag stays out of this PR. No reply mentions issue 3997, and no reply promises another PR.</li>
<li><strong>Merge main first:</strong> "yes, merge". Done in the working tree. Before the merge the branch was 272 commits behind main {ref(42)}. The PR head 4c4b7b8864 is merged with main 3bea58b788, without a conflict {ref(46)}. Git merged three files that both sides had changed: <code>h/tron/models/self_attention.hpp</code>, <code>src/tron/CMakeLists.txt</code> and <code>t/t_llama_unit.cpp</code>.</li>
<li><strong>README.ci.md and your rule on issue numbers:</strong> "it is not source code, rule does not cover it". The new README paragraph carries no issue link in any case (card <a href="#I8">I8</a>).</li>
<li><strong>Commit, push and post:</strong> "sounds good". So I ask once, when the tests at the final head are in. Nothing is committed, pushed or posted.</li>
</ol></div>
<div class="open" id="open3"><p><strong>Needs your word: two new small points.</strong> Both came up while the edits were made. The work goes on with the choice stated in each point.</p>
<ol>
<li><strong>A changelog fragment for this PR.</strong> Main has a new rule. A pull request with a change that users would notice adds one small file in <code>changelog.d/</code> {ref(44)}. Weishan Yang announced the rule in #software on 2026-11-17 at 16:48 PST. The announcement asks open pull requests with such a change to add the file before they merge {ref(45)}. The rule lists performance among these changes {ref(44)}. So I added the file <code>changelog.d/5022.changed.md</code> to the working tree. It holds one line of 79 characters, and the limit is 80:
<pre><code>- runtime: Speed up Muse Glimmer 30B attention with AMX on Intel hosts. (#5022)</code></pre>
Confirm the wording, or say that this PR needs no fragment.</li>
<li><strong>The test policy of the repository and the new tests.</strong> The file AGENTS.md has a section "Test policy" since 2026-09-01. It says: "Every committed test must run in CI." It also says: "A test that does not execute in CI must not be committed, except in extremely rare cases explicitly approved by the user. Agents may not decide that an exception applies." {ref(43)} This is the written rule behind Isaac's blocker.
<ul>
<li>The new transpose test runs in the required lane. It meets the policy.</li>
<li>Three new sections of <code>t_amx_dispatch_dtype</code> exist only in a build with the option ON: 16 heads with a partial page, 16 heads with AMX reported as unavailable, and 32 heads with 2 KV heads. The same holds for the new checks in the PV case of <code>t_amx_numerics</code>. They run in the legacy CMake workflow and by hand. They do not run in the required lane.</li>
<li>I read your D1 decision as the approval that the policy asks for. Say if you see it differently.</li>
</ul></li>
</ol></div>'''
cut('<div class="open" id="open2">', '</ol></div>', OPEN23,
    must_contain=('Still needs your word: four smaller points', 'The go to commit, push and post'))

# --------------------------------------------------------------------------
# C. D1 card, D5, N1: the replies do not cite the issue
# --------------------------------------------------------------------------
rep('<p><strong>Your decision:</strong> the build flag for the required lane stays out of this PR. Issue #3997 keeps it.</p>',
    '<p><strong>Your decision:</strong> the build flag for the required lane stays out of this PR. '
    'In the second round you asked for a simpler change and a simpler reply, without any mention of issue #3997. '
    'So the replies do not cite it, and they promise no other PR.</p>')
rep('<li>README.ci.md is documentation, not source. The I8 paragraph keeps its link to #3997. Say if your rule covers README files too '
    '(point 3 of the box <a href="#open2">Still needs your word</a>).</li>',
    '<li>README.ci.md: your answer of the second round is "it is not source code, rule does not cover it". '
    'The new I8 paragraph carries no issue link in any case.</li>')
rep('<td>#3997, open since 2026-08-26 <a class="ref" href="#R9">[R9]</a></td>',
    '<td>#3997, open since 2026-08-26 <a class="ref" href="#R9">[R9]</a>. The replies do not cite it (your second-round answer).</td>')
# Q4: the closest record that the page already holds
rep('on such a host would show whether it sets <code>USE_HW_ATTN</code>.</li>',
    'on such a host would show whether it sets <code>USE_HW_ATTN</code>. '
    'The closest record is the CI machine delphi-3bda: its <code>/etc/rinzler/instance-1.env</code> of 2026-09-13 sets no <code>USE_HW_ATTN</code> '
    '(card <a href="#T9">T9</a>).</li>')
# D2: state of the I6 edit
rep('<p><strong>Not verified yet:</strong> the edit is not compiled. The build at the final head on delphi-3b35 compiles it, '
    'and that build waits for the reboot of the machine (<a href="#todo">Part C</a>). The spelling rests',
    '<p><strong>Not verified yet:</strong> the edit is in the working tree. It has not been built with the AMX option ON, and it has not run. '
    'The build and the tests at the final head on delphi-3b35 do both, and they wait for the reboot of the machine (<a href="#todo">Part C</a>). The spelling rests')

# --------------------------------------------------------------------------
# C. Reply T1 (whole reply)
# --------------------------------------------------------------------------
replace_reply('T1',
    '<p>You are right on the facts: the required GCP Nix build leaves <code>TRON_AMX_DISPATCH</code> OFF, so in that lane both AMX test binaries ran their placeholder case. '
    'The stale sentence in the CMake comment and in README.ci.md is fixed in this PR.</p>\n'
    '<p>I am not adding the flag to the Nix build here: it would change what every eligible model test of the required lane exercises on Intel runners, '
    'and that is a CI change for all pull requests, not part of serving kv_mul 16.</p>\n'
    '<p>Evidence for this PR: the option-ON test records from Granite Rapids hosts (delphi-3bda at the reviewed commit, delphi-3b35 at the final head), '
    'a run of the legacy CMake workflow at the final head, and the new transpose test, which runs in the required lane.</p>')

# --------------------------------------------------------------------------
# C. Reply T4: section name, expected counts, last sentence
# --------------------------------------------------------------------------
rep('gen/t_amx_numerics "AMX PV stays inside the AVX weight-rounding envelope" -c "4 heads"\n',
    'gen/t_amx_numerics "AMX PV stays inside the AVX weight-rounding envelope" -c "4 heads: rows 0..3 in the envelope, rows 4..15 zero"\n')
rep('expected <code>test cases: 4 | 2 passed | 2 skipped</code>',
    'expected <code>test cases: 5 | 3 passed | 2 skipped</code>')
rep('\n<p>The required-lane change stays on #3997, as recorded there on 2026-10-19.</p></div></div>', '</div></div>')

# --------------------------------------------------------------------------
# C. Combined reply, first bullet
# --------------------------------------------------------------------------
rep('<li><strong>CI lane.</strong> The CMake comment and README.ci.md get rewritten in this PR to name the lanes that exist. '
    'The one-line <code>-DTRON_AMX_DISPATCH=ON</code> for the Nix build goes in its own PR under #3997 with the CI owner, '
    'because on a Granite Rapids runner it changes what the model tests of the required lane exercise. '
    'If it merges first, I rebase this PR on it. (Inline threads at src/tron/CMakeLists.txt:216.)</li>',
    '<li><strong>CI lane.</strong> The stale sentence in the CMake comment and in README.ci.md is fixed. '
    'The Nix flag stays out of this PR: it changes what the model tests of the required lane exercise on Intel runners. '
    'Evidence for this PR: option-ON test records from Granite Rapids hosts, a run of the legacy CMake workflow at the final head, '
    'and the transpose test in the required lane. (Inline threads at src/tron/CMakeLists.txt:216.)</li>')

# --------------------------------------------------------------------------
# C. I7: action, checked row, reply
# --------------------------------------------------------------------------
rep('accept, modified (comment here; Nix flag as its own PR)',
    'accept, modified (comment and README fixed here; no Nix flag in this PR)', count=2)
rep('the last two runs show test: skipped. The TODO line with the link to #3997 is on main already [src/tron/CMakeLists.txt:217-218 at 6198824246]; '
    'the proposed text leaves those two lines as they are (D5).',
    'the last two runs show test: skipped. That detail is no longer in the reply. '
    'The TODO line below the comment carries an issue link and is on main already [src/tron/CMakeLists.txt:217-218 at 6198824246]; '
    'the edit leaves those two lines as they are (D5), and the reply does not show them.')
I7_CMT = '''# fast-path call sites. The default CI build (GCP Nix) leaves the option OFF;
# the deb preset and the legacy CMake workflow (cmake-single-platform.yml) set
# it ON. In that workflow the kernel tests execute only on a Granite Rapids
# runner; on other runners they are reported as skipped, and ctest and Slice
# still report a pass.'''
assert max(len(x) for x in I7_CMT.split('\n')) <= 79
replace_reply('I7',
    '<p>You are right. The comment went stale when CI moved to GCP Nix: that build leaves the option OFF [nix/cmake-tron-test-build.nix:79-101], '
    'and the legacy CMake workflow no longer runs on pull requests. Fixed here and in README.ci.md:</p>\n'
    f'<pre><code>{esc(I7_CMT)}</code></pre>\n'
    '<p>I am not adding the flag to the Nix build in this PR. With it ON, every eligible model test of the required lane would run the AMX kernels on an Intel runner '
    'and the AVX path on an AMD runner. That changes CI for every pull request, and it is not part of serving kv_mul 16.</p>\n'
    '<p>What covers this PR:</p>\n'
    '<ul><li>The AMX tests ran with the option ON on Granite Rapids hardware: on delphi-3bda, the machine of the nightly systems test, at the commit you reviewed '
    '(2026-10-18, <code>round3.log</code>), and on delphi-3b35 at the final head. The records are in the Verification section.</li>'
    '<li>A run of the legacy CMake workflow at the final head, which builds and tests with the option ON: run &lt;id&gt;, test-host on &lt;runner&gt;.</li>'
    '<li>The new transpose test needs no AMX, so it runs in the required lane.</li></ul>',
    after='\n<div class="row"><div class="k">Still open</div><div>The placeholders &lt;id&gt; and &lt;runner&gt; are filled in after the run of the legacy CMake workflow. '
          'The words "on delphi-3b35 at the final head" become true with the runs that wait for the reboot (<a href="#todo">Part C</a>). '
          'Removed from the earlier draft: the publish-deb detail, the Catch2 exit codes, the promise of a separate PR and the promise to rebase.</div></div>')

# --------------------------------------------------------------------------
# C. I8: checked row, reply
# --------------------------------------------------------------------------
rep("so 'only lane' must be worded as 'only workflow that passes the flag and builds the tests with it'. <span class=\"sub\">(claim confirmed)</span>",
    "so 'only lane' must be worded with care. On main the paragraph has one more sentence, about the <code>deb-host</code> preset. "
    "The new text is main's paragraph with two phrases fixed and one sentence added. <span class=\"sub\">(claim confirmed)</span>")
I8_PARA = '''`TRON_AMX_DISPATCH=ON` compiles the AMX software-attention kernels and their
dispatch (see Note [AMX attention dispatch] in
`h/tron/kernels/amx_attn_iface.hpp`). Of the CI workflows, only the legacy
`cmake-single-platform.yml` passes it; the default `gcp-nix.yml` build leaves
it OFF. The `deb` preset also sets the option ON, so the released package
carries the kernels and selects them at run time only on hosts with AMX. The
`deb-host` preset inherits the setting from `deb`. Every other preset leaves
it at its default OFF. The kernel cases of `t_amx_numerics` execute AMX only
when the test job lands on a Granite Rapids runner; elsewhere Catch2 reports
them as skipped, and ctest and Slice still report a pass.'''
assert max(len(x) for x in I8_PARA.split('\n')) <= 80
replace_reply('I8',
    '<p>You are right. Fixed in this PR: the paragraph no longer says "so CI covers that code" or "skip with a warning".</p>\n'
    f'<pre><code>{esc(I8_PARA)}</code></pre>\n'
    '<p>The flags block above it gets one caption line: "The legacy CMake build (<code>cmake-single-platform.yml</code>) configures with the '
    '<code>native</code> preset and, among others, these flags:".</p>')

# --------------------------------------------------------------------------
# D, D2. I10: checked row and reply follow the implementation
# --------------------------------------------------------------------------
rep('ctest registers each case through catch_discover_tests with SKIP_RETURN_CODE 4 by default, so ctest lists the two kernel cases as skipped and the run passes.',
    'ctest and Slice each run the whole binary as one test, because add_catch_test takes its plain add_test branch (card I26). '
    'Catch2 exits 0 when the ungated cases pass, so both report a pass.')
I10_FN = '''// s[head][token] = s_transposed[token][head] for head < group_heads, where
// s_transposed is 64 tokens x 16 columns. Other rows of `s` are not written.
template <size_t group_heads>
  requires(group_heads_ok(group_heads))
inline void transpose_scores(
    const float* s_transposed, float* s, size_t s_stride_floats) noexcept {'''
replace_reply('I10',
    '<p>You are right. The three new lanes have run in no CI lane at all. The kernel cases skip in the option-on lane, and the pull-request lane (GCP Nix) '
    'does not set <code>TRON_AMX_DISPATCH</code> [nix/cmake-tron-test-build.nix:87-93], so there the whole file compiles to the stub case [t/t_amx_numerics.cpp:339-344].</p>\n'
    '<p>Done, with one change to the placement:</p>\n'
    '<ul><li>Stages 1-4 are now <code>transpose_scores&lt;group_heads&gt;</code>, an inline template in the new header '
    '<code>h/tron/kernels/amx_attn_transpose.hpp</code> (AVX-512 intrinsics only, no AMX, the same convention as <code>dotter.hpp</code>). '
    'The helper <code>store_transposed_rows</code>, the lane constants and <code>TILE_FP32S</code> moved with it. '
    '<code>amx_attn.cpp</code> includes the header and calls the function after the four tile stores. '
    'The interface header stays intrinsics-free. Its Note [QK orientation] gains one sentence: "The transpose is transpose_scores in amx_attn_transpose.hpp."</li>'
    '<li>The definition sits in the header and not in a separate translation unit, so the compiler can inline it into the QK kernel. '
    'Plain <code>inline</code> was enough. I did not need <code>[[gnu::always_inline]]</code>.</li>'
    '<li>Object compare of the kernel file (one object file, clang 19.1.7, 2026-11-19): all 10 functions are identical before and after the move. '
    'They are also identical between the commit you reviewed and the final tree. '
    '<code>qk_rowmajor_128x4&lt;4&gt;</code> has 204 instructions, and <code>&lt;16&gt;</code> has 207. '
    'The compare with the product build flags on a Granite Rapids host is pending.</li>'
    '<li>New test case <code>"AMX QK transpose writes the group_heads score rows"</code>, tag <code>[q_pack]</code>, '
    'with the sections "4 heads: rows 0..3 written, rows 4..15 untouched" and "16 heads: all 16 rows written". '
    'It fills a block of 64 tokens x 16 columns with distinct values that start at <code>FIRST_SCORE_1</code>. '
    'It calls the function and compares with the scalar transpose <code>s[q][t] == s_transposed[t * 16 + q]</code>. '
    'The output rows have a stride of 80 floats (<code>ROW_STRIDE_80</code>). So each row has 16 guard columns past token 63. '
    'The guard columns and rows <code>group_heads..15</code> must keep the sentinel. Each section makes 1,280 assertions. '
    'The case and the sentinel constant sit above <code>#ifdef TRON_AMX_DISPATCH</code>, so the case also runs in the pull-request lane, where the option is off. '
    'The test TU already gets the AVX-512 flags from the <code>tron</code> target [src/tron/CMakeLists.txt:269].</li>'
    '<li>Earlier check, on the code you reviewed: I built stages 1-4 as a standalone program without <code>-mamx</code> on an AMD host with AVX-512 '
    'and compared with a scalar transpose. Result: 0 mismatches over 1024 cells for 4 heads and for 16 heads, and no tile instruction in the binary.</li></ul>\n'
    '<p>The function and its comment in the new header:</p>\n'
    f'<pre><code>{esc(I10_FN)}</code></pre>\n'
    '<p>On the comment text: ctest and Slice each run the whole binary as one test [t/CMakeLists.txt:212-219; bin/slice:1208-1210]. '
    'Catch2 exits 0 because the ungated cases pass. So both report a pass while the two kernel cases are skipped. '
    'The CMake comment and README.ci.md now say that.</p>',
    after='\n<div class="row"><div class="k">Still open</div><div>Two statements of this reply wait for delphi-3b35: the object compare with the product build flags, '
          'and the first run of the new test case (<a href="#todo">Part C</a>). The local compare used the compile flags of an earlier tron build for this file.</div></div>')

# --------------------------------------------------------------------------
# D2. T11: the group_heads_ok comment, 5 lines
# --------------------------------------------------------------------------
T11_CMT = '''// The group sizes the kernels are compiled for: 4 and 16, the sizes validated
// on AMX hardware (unit sections, token identity, throughput). The code could
// serve any multiple of 4 up to 16; kv_mul 8 has no AMX run yet and is left
// out. A new size also needs its explicit instantiations at the end of
// amx_attn.cpp and its t_amx_numerics sections.'''
assert max(len(x) for x in T11_CMT.split('\n')) <= 79
rep('Proposed comment for <code>group_heads_ok</code> [h/tron/kernels/amx_attn_iface.hpp:143-145]:</p>',
    'The comment of <code>group_heads_ok</code> [h/tron/kernels/amx_attn_iface.hpp:143-145] now reads:</p>')
cut('<pre><code>// The group sizes the kernels are compiled for: 4 (llama-3.1-8b, qwen3-4b)',
    'and run them on an AMX host.</code></pre>',
    f'<pre><code>{esc(T11_CMT)}</code></pre>',
    must_contain=('its t_amx_numerics sections',))

# --------------------------------------------------------------------------
# D, D2. I17: checked row, constants, the new section
# --------------------------------------------------------------------------
rep('A drafted version of the section exists but was not compiled here (no clang 19 or TBB headers on this host).',
    'The section is in the working tree. Its file passed the local syntax check with clang 19.1.7 on 2026-11-19. It has not run yet.')
rep('Fixture changes: <code>n_kv_heads</code> becomes a template parameter, <code>exercise_page</code> takes a <code>kv_head</code> argument,',
    'Fixture changes: <code>n_kv_heads</code> becomes a template parameter with the default <code>KV_HEADS_1</code>, '
    '<code>exercise_page</code> takes a <code>kv_head</code> argument,')
I17_CALL = '''    exercise_page<host_bf16, QUERY_HEADS_32, KV_HEADS_2>(
        page_size, /*repeat=*/false, /*amx_available=*/true, SECOND_KV_HEAD_1);'''
rep('<p>One caveat: the new section builds a 32-head model (dim 4096) through the same fixture.',
    '<p>The new section is "host_bf16, 32 heads / 2 KV heads, KV head 1, full page: the pack reads the second group of 16 heads". Its call:</p>\n'
    f'<pre><code>{esc(I17_CALL)}</code></pre>\n'
    '<p>One caveat: the new section builds a 32-head model (dim 4096) through the same fixture.')

# --------------------------------------------------------------------------
# D, D2. I20: clang-format signatures; the comment is removed
# --------------------------------------------------------------------------
I20_OLD = ('// t/t_amx_dispatch_dtype.cpp:272\n'
           'void qk_rowmajor_128x4(const_k_row_major_plane_view,\n'
           '// t/t_amx_dispatch_dtype.cpp:282\n'
           'void weights_times_v_128x4(const_v_vnni_plane_view,\n'
           '// t/t_amx_numerics.cpp:183\n'
           '    tron::amx_attn_h128g4::const_k_row_major_plane_view{in-&gt;k}, q_packed,</code></pre>')
I20_NEW = '''// t/t_amx_dispatch_dtype.cpp:272
void qk_rowmajor_128x4(
    const_k_row_major_plane_view, const bf16*, float* output, size_t stride) noexcept {
// t/t_amx_dispatch_dtype.cpp:282
void weights_times_v_128x4(
    const_v_vnni_plane_view, const float*, size_t, float* output) noexcept {
// t/t_amx_numerics.cpp:183
        tron::amx_attn_h128g4::const_k_row_major_plane_view{in->k}, q_packed,'''
rep(I20_OLD, esc(I20_NEW) + '</code></pre>\n<p>clang-format puts each of the two fake signatures on two lines.</p>')
rep('I will also shorten the comment above that call, since the alias name now says "the K plane the kernel takes" [t/t_amx_numerics.cpp:181-182].',
    'The comment above that call is removed, because the alias name says what the comment said [t/t_amx_numerics.cpp:181-182].')

# --------------------------------------------------------------------------
# D2. I24: the named sentinel weight.   I26, I6: wording that the new case changes
# --------------------------------------------------------------------------
rep('  // Rows group_heads..15 hold a nonzero value the kernel must never read.\n'
    '  alignas(64) float exp_rows[TILE_ROWS_16][PAGE_TOKENS_64];',
    '  // Rows group_heads..15 hold a nonzero value the kernel must never read.\n'
    '  constexpr float UNREAD_WEIGHT_1 = 1.f;\n'
    '  alignas(64) float exp_rows[TILE_ROWS_16][PAGE_TOKENS_64];')
rep('      x = qi &lt; group_heads ? std::exp(ue(gen)) : 1.f;', '      x = qi &lt; group_heads ? std::exp(ue(gen)) : UNREAD_WEIGHT_1;')
rep('because the two pack cases run and pass;', 'because the ungated cases run and pass;')
rep('and commit b431585224 added both. The edit is not compiled yet.',
    'and commit b431585224 added both. The edit is in the working tree. Its build with the option ON and its run wait for delphi-3b35.')

# --------------------------------------------------------------------------
# E. Part C
# --------------------------------------------------------------------------
cut('<h4>First step: merge main into the branch (pending your word, recommended)</h4>',
    '<h4>Code and comment edits (one text per file, conflicts resolved)</h4>',
    '<h4>First step: merge main into the branch (done in the working tree)</h4>'
    f'<p>You said "yes, merge" in the second round. The PR head 4c4b7b8864 is merged with main 3bea58b788 in the working tree, without a conflict {ref(46)}. '
    'Git merged three files that both sides had changed: <code>h/tron/models/self_attention.hpp</code>, <code>src/tron/CMakeLists.txt</code> and <code>t/t_llama_unit.cpp</code>. '
    'The merge is not committed. The line numbers in the list below are those of the reviewed commit 4c4b7b8864.</p>'
    '<h4>Code and comment edits: done in the working tree, not committed</h4>'
    '<p><strong>Status on 2026-11-19 at 19:39 PST.</strong> Every edit of the list below is made in the working tree '
    '<code>/home/jhan/workspace/ai-runs/pr5022-final/tron</code>, except the registry file. '
    f'Against main, 11 files differ: 9 existing files, the new header and the changelog fragment {ref(46)}. '
    f'The git tree hash of this state is <code>{TREE}</code> {ref(46)}.</p>'
    '<ul><li><strong>Local syntax check</strong> with clang 19.1.7: <code>t_amx_numerics.cpp</code> with the option ON and with the option OFF, '
    '<code>t_amx_dispatch_dtype.cpp</code> and <code>t_llama_unit.cpp</code>. Result: 0 errors and 0 warnings.</li>'
    '<li><strong>clang-format 19.1.7:</strong> clean on the 6 C++ files.</li>'
    '<li><strong>Local object compare of the kernel file:</strong> all 10 functions of <code>amx_attn.o</code> are identical before and after the move of the transpose. '
    'They are also identical between 4c4b7b8864 and the final tree (card <a href="#I10">I10</a>).</li>'
    '<li><strong>Timing of these checks:</strong> they were recorded by 19:30 PST. The cleanup of 19:39 PST, which named five constants and shortened comments, came after that record. '
    'The build on delphi-3b35 compiles the final state.</li>'
    '<li><strong>Not done locally:</strong> a standalone run of the transpose function. The permission system of the agent\'s server blocked it. '
    'The test binary on delphi-3b35 covers it.</li>'
    '<li><strong>Pending on delphi-3b35, after the reboot:</strong> the build, the tests, the object compare with the product build flags, and the registry refresh.</li></ul>',
    must_contain=('272 commits behind main',))
rep('one line near Note [QK orientation] pointing at the new transpose header (I10).</li>',
    'one sentence in Note [QK orientation] that names the new transpose header (I10).</li>')
rep('alias at line 183 and shorter comment at 181-182 (I20);', 'alias at line 183, and the comment at 181-182 removed (I20);')
rep('<li><code>config/test-benchmarks.json</code>: refreshed rows for both tests on',
    '<li><code>config/test-benchmarks.json</code>: <strong>not edited yet</strong>, it waits for the registry refresh on delphi-3b35. Planned: refreshed rows for both tests on')
rep('<li><code>nix/cmake-tron-test-build.nix</code>: not in this PR; one-line PR under #3997 (D1).</li></ul>',
    '<li><code>nix/cmake-tron-test-build.nix</code>: not changed in this PR (D1).</li>'
    '<li><code>changelog.d/5022.changed.md</code> (new): one line. It waits for your word (box <a href="#open3">Needs your word</a>, point 1).</li></ul>')
rep('<h4>Runs on delphi-3b35 (compile and unit tests only,', '<h4>Runs on delphi-3b35: pending (compile and unit tests only,')
rep(f'At 19:09 PST the boot time was still 2026-08-24 16:12:16 {ref(41)}.',
    f'At 19:33 PST the machine had not rebooted: its boot time was still 2026-08-24 16:12:16 {ref(41)}.')
rep('<li><strong>Registry refresh:</strong> <code>bin/slice bench --update</code> runs only after a read of what it touches. '
    'It is skipped if it needs FPGA cards or the whole machine.</li></ul>',
    '<li><strong>Registry refresh:</strong> <code>bin/slice bench --update</code> runs only after a read of what it touches. '
    'It is skipped if it needs FPGA cards or the whole machine.</li>'
    f'<li><strong>Scripts:</strong> <code>~/workspace/intel-AMX/exec/pr5022-final-20261119/</code> holds <code>build-3b35.sh</code>, <code>tests-3b35.sh</code> and a README with the rules for the shared machine {ref(46)}. '
    'The build script makes a worktree of main, copies the 11 prepared files over it, and checks the tree hash before it builds.</li></ul>')
cut('<li>One-line PR: <code>-DTRON_AMX_DISPATCH=ON</code> in <code>nix/cmake-tron-test-build.nix</code>, under #3997,',
    '<a href="#open2">Still needs your word</a>.</li>', '',
    must_contain=('CI owner as reviewer (D1)',))

# --------------------------------------------------------------------------
# Words used here
# --------------------------------------------------------------------------
rep('<li><strong>soak test</strong>: the part of the nightly systems test that keeps several models under load for a long time and counts errors.</li>',
    '<li><strong>soak test</strong>: the part of the nightly systems test that keeps several models under load for a long time and counts errors.</li>\n'
    '<li><strong>changelog fragment</strong>: one small file in changelog.d/ that a pull request adds when users would notice its change. '
    'The file holds one line. The rule is on main since 2026-11-18 UTC.</li>\n'
    '<li><strong>test policy</strong>: the section "Test policy" of the file AGENTS.md in the tron repository. It says that every committed test must run in CI.</li>\n'
    '<li><strong>working tree</strong>: the directory /home/jhan/workspace/ai-runs/pr5022-final/tron. It holds the PR head merged with main, plus the review edits. Nothing in it is committed.</li>\n'
    '<li><strong>tree hash</strong>: git\'s identifier for the exact content of a directory tree. Two trees with the same hash hold the same files.</li>')
a = s.index('<h2 id="words">')
b = s.index('</ul></details>', a)
n_terms = s[a:b].count('<li><strong>')
rep('<summary>Open the word list (32 terms)</summary>', f'<summary>Open the word list ({n_terms} terms)</summary>')

# --------------------------------------------------------------------------
# References: F (moved lines), R41, new R43..R46
# --------------------------------------------------------------------------
rep('<code>GNUmakefile:510</code>: <code>make deb</code> runs <code>cmake --preset deb</code>.</li>',
    '<code>GNUmakefile:510</code>: <code>make deb</code> runs <code>cmake --preset deb</code>. On main at 3bea58b788 that line is <code>GNUmakefile:580</code>.</li>')
rep('Line 113 runs <code>make deb</code>.</li>',
    'Line 113 runs <code>make deb</code>. On main at 3bea58b788 it is line 118.</li>')
rep('No job of ours ran there. The account disagg used about 31 CPUs.</li>',
    'No job of ours ran there. The account disagg used about 31 CPUs. A further check at 19:33 PST read the same boot time.</li>')
REFS = f'''<li id="R43"><code>AGENTS.md:27-35</code> on main at 3bea58b788, section "Test policy". Commit 7db7228e2c of 2026-09-01 by Hannah Van Eenoo added it: "Define high-value CI test policy".</li>
<li id="R44"><code>changelog.d/README.md</code> on main at 3bea58b788: lines 3-8 (who adds a fragment, with performance in the list), line 10 (the file name <code>&lt;PR&gt;.&lt;section&gt;.md</code>), lines 21-23 (one line of at most 80 characters) and lines 28-30 (the scopes, with <code>runtime</code>). Commit 3609c3b4f8 added the file. It is tron pull request <a href="https://github.com/positron-ai/tron/pull/5179">5179</a>, "Add changelog rules with changelog.d fragments", merged 2026-11-18 00:45 UTC. That is 2026-11-17 16:45 PST.</li>
<li id="R45">Slack #software, Weishan Yang, <a href="https://positronai.slack.com/archives/C057NJGDW4T/p1794962936600459">2026-11-17 16:48 PST</a>: "Tron now has a changelog (tron#5179 just merged)". On pull requests that are already open: "If yours is notable, please add a fragment before it merges."</li>
<li id="R46">The working tree <code>/home/jhan/workspace/ai-runs/pr5022-final/tron</code> and its record <code>~/workspace/intel-AMX/exec/results/pr5022-final-20261119/prep.txt</code> of 2026-11-19 19:39 PST. The record states the content (PR head 4c4b7b8864 merged with main 3bea58b788, plus the review edits), the git tree hash <code>{TREE}</code>, and the 11 files that differ from main with their sha256 sums. The scripts for the runs are in <code>~/workspace/intel-AMX/exec/pr5022-final-20261119/</code>. The output of the local checks was read in the session. The object files of the local compare are in the session's scratch folder, which is temporary.</li>
'''
rep('<code>bin/slice</code> 2. The two kernel files and the two AMX test files: 0.</li>\n</ol>',
    '<code>bin/slice</code> 2. The two kernel files and the two AMX test files: 0.</li>\n' + REFS + '</ol>')

# --------------------------------------------------------------------------
# How this was checked
# --------------------------------------------------------------------------
rep('Nothing was committed, pushed or posted, and no issue was filed.</p>\n</main></body></html>',
    'Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '<p><strong>Update of 2026-11-19, second round (19:27 to 19:50 PST).</strong> Your answers to the four smaller points were applied. '
    'The D1 replies (T1, I7, I8, the first bullet of the combined reply) were rewritten short. No reply draft and no item of Part C mentions issue 3997 now. '
    'Read in the working tree for this update: the CMake comment, the README paragraph and its caption, the new header, both AMX test files and the changelog fragment. '
    'Every code block that this update quotes was compared with those files. '
    'Read on main at 3bea58b788: the section "Test policy" of AGENTS.md, changelog.d/README.md, and the moved line numbers of the package build. '
    'One statement of the earlier draft was wrong and is corrected: ctest does not register each test case on its own. It runs the whole binary as one test (cards I10 and I26). '
    'The kill-switch expectation in the T4 reply now counts the new transpose case: 5 test cases, 3 passed, 2 skipped. '
    'Not done at the time of this update: no build and no test ran at the final head, because delphi-3b35 had not rebooted at 19:33 PST. '
    'The local checks of Part C were not repeated for this page. '
    'Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '</main></body></html>')

# --------------------------------------------------------------------------
# Final checks, then write
# --------------------------------------------------------------------------
# 1. No reply block and no Part C item mentions the issue.
for m in re.finditer(r'<div class="reply">', s):
    blk = s[m.start():div_end(m.start())]
    assert '3997' not in blk, 'reply block mentions 3997: ' + blk[:120]
a = s.index('<h2 id="todo">')
b = s.index('<h2 id="refs">')
assert '3997' not in s[a:b], 'Part C mentions 3997'
for cid in ('I7', 'I8', 'T1', 'T4'):
    x, y = card_span(cid)
    assert '3997' not in s[x:y], cid
# 2. Stale phrases.
for stale in ('Still needs your word', 'own one-line PR', 'I will open it as its own', 'its own PR under',
              'href="#open2">Still', 'pending your word, recommended', '19:09 PST the boot time was still',
              '19c930544eb3', 'true, KV_HEAD_1', 'two pack cases', 'two host cases', 'Proposed comment for <code>group_heads_ok'):
    assert stale not in s, f'stale phrase left: {stale!r}'
for n in range(1, 47):
    assert s.count(f'id="R{n}"') == 1 and f'href="#R{n}"' in s, n
for i in ('open', 'open2', 'open3', 'D1-Q4', 'CI', 'combined'):
    assert s.count(f'id="{i}"') == 1, i

open(P, 'w', encoding='utf-8').write(s)
open(LAST, 'w').write(md5(P) + '\n')
print(f'{n_rep} replacements; {len(s.encode("utf-8"))} bytes; {s.count(chr(10)) + 1} lines; {n_terms} terms; md5 {md5(P)}')
