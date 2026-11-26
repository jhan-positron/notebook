#!/usr/bin/env python3
"""Fifth-stage patch of respond-2-Isaac.html (page pass 5, 2026-11-19 about 21:00 PST).

Applies sections H and I of page-pass-5-brief.md (the changes after the
independent pre-review) on top of the page as it stood after pass 4 and the
two direct edits of the main session. Idempotent: it always starts from the
stage-4 copy. Run: python3 -I apply_patch5.py
"""
import hashlib
import html
import re

S = ('/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/'
     '78b9fca8-c24b-4ac2-a02d-0236a437cdd6/scratchpad/')
P = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
STAGE4 = S + 'respond-2-Isaac.stage4.html'
LAST = S + 'apply_patch5.last-md5'
STAGE4_MD5 = '8498c824707b5d74dbf27c8f1e4b4246'
OLD_TREE = 'b026009a4291a9bd1dbe405fee494000cfd9711d'
TREE = '5821ee86418d3ac07944112c529d7d311e91f3bd'


def md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


assert md5(STAGE4) == STAGE4_MD5, 'stage-4 copy changed'
known = {STAGE4_MD5}
try:
    known.add(open(LAST).read().strip())
except FileNotFoundError:
    pass
assert md5(P) in known, f'page was changed outside this script (md5 {md5(P)})'

s = open(STAGE4, encoding='utf-8').read()
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
# Header line, nav, Short version, intro (passes 4 and 5 made them stale)
# --------------------------------------------------------------------------
rep('with your two rounds of answers of that evening &middot; nothing posted</p>',
    'with your three rounds of answers of that evening and a pre-review &middot; nothing posted</p>')
rep('<a href="#open3">Needs your word</a><a href="#top">', '<a href="#open">Your answers</a><a href="#top">')
rep('answered the open points in two rounds that evening, and the drafts below follow them: the D1 replies are now short and do not mention issue 3997. '
    'The code edits are done in an uncommitted working tree, two new small points need your word, and the tests on the server delphi-3b35 wait',
    'answered the open points in three rounds that evening, and the drafts below follow them: the D1 replies are short and do not mention issue 3997. '
    'The code edits are done in an uncommitted working tree, an independent pre-review found seven points that are all fixed, and the tests on the server delphi-3b35 wait')
rep('The three boxes below hold your answers of the evening, in two rounds, and the two points that are still open.',
    'The three boxes below hold your answers of the evening, in three rounds. Nothing is open for you now.')

# open3: keep reference 45 cited
rep('stays in the working tree with this line <a class="ref" href="#R44">[R44]</a>:',
    'stays in the working tree with this line <a class="ref" href="#R44">[R44]</a> <a class="ref" href="#R45">[R45]</a>:')

# D2: the view is no longer his text word for word
rep('<li>The two <code>row</code> lines are his own suggestion, word for word.',
    '<li>The <code>row</code> view is his own suggestion. The final code spells its two flags with the named constants '
    '<code>VIEW_ALIGNED_TRUE</code> and <code>VIEW_DMA_FALSE</code>, where he wrote <code>true</code> and <code>false</code>.')

# --------------------------------------------------------------------------
# H6, H7. T10 and the combined benchmark bullet
# --------------------------------------------------------------------------
rep('The changes since that commit carry a low risk for performance, so I accept that the numbers are not repeated at the final head.</p>',
    'This PR\'s changes since that commit carry a low risk for performance, so I accept that the numbers are not repeated at the final head. '
    'The head also contains main up to 3bea58b788, which the nightly systems test measures.</p>')
rep('<li>The two edits in <code>apply_page_range</code> that you asked for remove work:',
    '<li>The two edits in <code>apply_dense_amx_page</code> that you asked for remove work:')
rep('The changes since then carry a low risk for performance: the kernel file compiles to the same instructions (object compare in the Verification section), '
    'and the two epilogue edits you asked for remove work. The nightly systems test measures Muse Glimmer and llama-3.1-8b throughput after the merge.</li>',
    'This PR\'s changes since that commit carry a low risk for performance: the kernel file compiles to the same instructions (object compare in the Verification section), '
    'and the two epilogue edits you asked for remove work. The head also contains main up to 3bea58b788, which the nightly systems test measures. That test measures Muse Glimmer and llama-3.1-8b throughput after the merge.</li>')

# --------------------------------------------------------------------------
# H5. I5 and I6: unit coverage, no credit to t_llama_unit
# --------------------------------------------------------------------------
COVERAGE = ('Unit coverage: <code>t_amx_dispatch_dtype</code> drives this path with kernel test doubles. '
            'Its PV double writes a distinct value per row, and a second visit covers the merge line. '
            '<code>t_llama_unit</code> does not reach this path, because its model has one query head per KV head. '
            'Real-value coverage of the epilogue is the token-identity runs in the Verification section, at the measured commit.')
rep('<p>Coverage: <code>t_amx_dispatch_dtype</code> drives this path with kernel test doubles that also write every row. '
    'The real-value coverage is <code>t_llama_unit</code> with the option on. I will rerun both at the final head on a Granite Rapids host (delphi-3b35), '
    'with AMX on and under the kill switch. The change alters no values.</p>',
    f'<p>{COVERAGE}</p>\n'
    '<p>I will rerun the unit tests at the final head on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch. The change alters no values.</p>')
rep('<p>The performance numbers in the PR body predate this edit. The edit removes a copy of 8 KB per page visit at 16 heads,',
    f'<p>{COVERAGE}</p>\n'
    '<p>The performance numbers in the PR body predate this edit. The edit removes a copy of 8 KB per page visit at 16 heads,')

# --------------------------------------------------------------------------
# H3. I10: tag, placeholder case, include
# --------------------------------------------------------------------------
rep('writes the group_heads score rows"</code>, tag <code>[q_pack]</code>, with the sections',
    'writes the group_heads score rows"</code>, tags <code>[amx_numerics][transpose]</code>, with the sections')
rep('The case and the sentinel constant sit above <code>#ifdef TRON_AMX_DISPATCH</code>, so the case also runs in the pull-request lane, where the option is off.',
    'The case, the sentinel constant and the include of the interface header sit above <code>#ifdef TRON_AMX_DISPATCH</code>, '
    'so the case also runs in the pull-request lane, where the option is off. '
    'The <code>#else</code> placeholder case of this file is removed. The file now has a real case in every build, and the placeholder said "nothing to test". '
    'So with the option OFF, <code>t_amx_numerics</code> holds exactly the transpose case with its 2 sections.')

# --------------------------------------------------------------------------
# H8. I13: the final bullet of the PR description
# --------------------------------------------------------------------------
I13_RULE = '''The check gates losses only: a configuration fails when its decode loss or its
prefill increase exceeds the band. A gain beyond the band is reported, but it is
claimed as an effect of this PR only where PR code runs on that path.'''
I13_NOTE = '''The qwen3-4b / tp2 / 1024 row runs no PR code: the AMX kernel scores 0 key
tokens in both configurations (`exit-reports.txt`). Its +0.56 TPS appears in
all four repetitions, so it is an offset between the two binaries, cause
unknown. The Glimmer decode gains (2.61 to 5.16 TPS) are 4 to 9 times that
offset.'''
cut('<p>Will do, in the Performance section:</p>', '4 to 9 times that offset.</code></pre>',
    '<p>Changed in the Performance section of the PR description:</p>\n'
    '<ul><li>"A change counts when its absolute size exceeds the band." is replaced with:</li></ul>\n'
    f'<pre><code>{esc(I13_RULE)}</code></pre>\n'
    '<ul><li>The later sentence that stated the same rule a second time is removed. The rule now stands in one place.</li>'
    '<li>The cell of the row reads <code>+0.56 / 0.33, beyond, no PR code on path</code>.</li>'
    '<li>One bullet under the table says:</li></ul>\n'
    f'<pre><code>{esc(I13_NOTE)}</code></pre>',
    must_contain=('Relabel the row', 'does not cover such an offset'))

# --------------------------------------------------------------------------
# H2, I. I19: distinct PV rows and a second visit
# --------------------------------------------------------------------------
rep('sum = token count; the PV fake zero-fills, so v_star = 0,', 'sum = token count; the PV fake of the reviewed commit zero-fills, so v_star = 0,')
rep('accept, modified (in exercise_page, every section)',
    'accept, modified (in exercise_page, every section, with distinct PV rows and a second visit)', count=2)
rep('The AVX arm with zero K and V should give the same state; that is a reading, confirmed only by the run. <span class="sub">(claim confirmed)</span>',
    'The AVX arm with zero K and V should give the same state; that is a reading, confirmed only by the run. '
    'Pre-review of 2026-11-19: with a PV fake that writes 0 into every row, the check cannot see which PV row feeds which head, '
    'and with validity cleared before each call it never reaches the merge line. The fake now writes row + 1, and each round visits the page twice. '
    '<span class="sub">(claim confirmed)</span>')
I19_HELPER = '''// What the PV fake writes into every dimension of output row `row`. The
// value differs per row, so the state check sees which row a head read.
constexpr float PV_FAKE_FIRST_ROW_VALUE_1 = 1.f;
constexpr float pv_fake_row_value(size_t row) {
  return PV_FAKE_FIRST_ROW_VALUE_1 + static_cast<float>(row);
}

...
void weights_times_v_128x4(
    const_v_vnni_plane_view, const float*, size_t, float* output) noexcept {
  ++probe.pv_calls;
  probe.pv_group_heads = group_heads;
  for (size_t row = 0; row < TILE_ROWS_16; ++row) {
    std::fill_n(output + row * HEAD_SIZE_128, HEAD_SIZE_128, pv_fake_row_value(row));
  }
}'''
I19_CHECK = '''    // The running-softmax state of every head in the group after `visits`
    // visits of the page. K is zero, so each score is 0, each exp is 1, m* is
    // 0 and s* is the token count per visit. v* is what PV returned for the
    // head's own row per visit: the fake's row value on the dense path, 0 from
    // the zero V on the AVX path. An epilogue that merged fewer than
    // group_heads heads, or read another head's row, fails here.
    const auto require_state = [&](float visits) {
      auto sp = state.self_attn_state.template token_scratchpad_ref_at<geometry>(0, 0);
      REQUIRE(sp.is_valid_for(kv_head));
      for (size_t offset = 0; offset < group_heads; ++offset) {
        CAPTURE(visits, offset);
        auto head_sp = sp[kv_head * group_heads + offset];
        REQUIRE(head_sp.s_star == visits * static_cast<float>(n_tokens));
        REQUIRE(head_sp.m_star == 0.f);
        const float v_expected = dense ? visits * pv_fake_row_value(offset) : 0.f;
        for (size_t i = 0; i < head_size; ++i) {
          CAPTURE(i);
          REQUIRE(static_cast<float>(head_sp.v_star[i]) == v_expected);
        }
      }
    };
    constexpr float ONE_VISIT_1 = 1.f;
    require_state(ONE_VISIT_1);
    ...
    // A second visit of the same page with validity kept: the epilogue merges
    // into the first visit's state. m* stays 0, so s* and v* double.
    {
      attn_stats::forward_scope stats_scope(*state.self_attn_state.stats,
          attn_stats::forward_class::decode_like, token_jobs.size(), token_jobs.size());
      state.self_attn_state.template apply_page_range<geometry>(jobs, operation,
          state.plugin_state.qs_roped, kv_head, 0, 1,
          std::span<const page_id>(page_ids), {}, visible);
    }
    constexpr float TWO_VISITS_2 = 2.f;
    require_state(TWO_VISITS_2);'''
replace_reply('I19',
    '<p>You are right. Nothing after <code>apply_page_range</code> reads the running-softmax state, so the epilogue\'s per-head merge is unchecked here. '
    'Done: the check is in <code>exercise_page</code> after the stats block, so it runs in every section (the 4-head rounds, the 16-head sections and the new KV-head-1 section), '
    'not only the 16-head one.</p>\n'
    '<p>The check goes one step beyond your proposal, for two reasons:</p>\n'
    '<ul><li>The PV test double wrote 0 into every row. With that double, <code>v_star == 0</code> holds whichever row a head reads, '
    'so the check could not see which PV row feeds which head. The double now writes a distinct value per row, row + 1. '
    'The check expects that value on the dense path and 0 on the AVX path.</li>'
    '<li>With validity cleared before each call, only the line that sets the state runs. The merge line stays unvisited. '
    'It is the <code>fma</code> line that your comment at self_attention.hpp:1788 changes. '
    'So each round now visits the page a second time without clearing validity. <code>m_star</code> stays 0, so <code>s_star</code> and <code>v_star</code> must double.</li></ul>\n'
    '<p>Your expected values hold for the first visit. The QK fake writes zero scores, so the scale step leaves 0, <code>m_page</code> is 0, every weight is exp(0) = 1 '
    'and the sum is the page\'s token count (64 on a full page, 63 on the partial-page section) [h/tron/models/self_attention.hpp:1766-1785]. '
    'The kv head is then marked valid, since the visit returned relevant tokens and <code>m_star</code> is not -inf [self_attention.hpp:1646-1661].</p>\n'
    '<p>The helper and the PV double:</p>\n'
    f'<pre><code>{esc(I19_HELPER)}</code></pre>\n'
    '<p>The state check and the second visit, in <code>exercise_page</code>:</p>\n'
    f'<pre><code>{esc(I19_CHECK)}</code></pre>\n'
    '<p>The cumulative call count in the stats block is now <code>2 * round + 1</code>, because each round visits the page twice.</p>\n'
    '<p>I will rerun <code>t_amx_dispatch_dtype</code> with <code>TRON_AMX_DISPATCH=ON</code> and refresh the assertion count in the Verification table once, '
    'after all test edits of this round.</p>',
    after='\n<div class="row"><div class="k">Still open</div><div>The check has not run yet. Its first run is on delphi-3b35 (<a href="#todo">Part C</a>). '
          'The value 0 for <code>v_star</code> on the AVX path is a reading of the code until that run.</div></div>')

# --------------------------------------------------------------------------
# H4. I20: the include
# --------------------------------------------------------------------------
rep('The comment above that call is removed, because the alias name says what the comment said [t/t_amx_numerics.cpp:181-182].</p>',
    'The comment above that call is removed, because the alias name says what the comment said [t/t_amx_numerics.cpp:181-182].</p>\n'
    '<p>One side effect: both test files lose their direct include of <code>tron/tensor/kv_cache_fwd.hpp</code>. '
    'The aliases come from the interface header, and nothing else in those files uses that header.</p>')

# --------------------------------------------------------------------------
# H1. I26: the registration
# --------------------------------------------------------------------------
rep('only a direct filtered invocation reaches exit 4. <span class="sub">(claim confirmed)</span>',
    'only a direct filtered invocation reaches exit 4. '
    'Pre-review of 2026-11-19: the first draft passed both labels as one quoted list. That form stops every CMake configure, '
    'because add_catch_test forwards its arguments unquoted. The final form appends the second label with set_property. '
    '<span class="sub">(claim confirmed)</span>')
rep('<p>You are right. Will do: register <code>t_amx_numerics</code> the way <code>t_chat_template</code> is registered, and refresh the registry.</p>',
    '<p>You are right. Done: <code>t_amx_numerics</code> is registered with <code>SKIP_RETURN_CODE 4</code> and carries the label <code>skip_return_code_4</code>. '
    'The registry refresh follows.</p>')
I26_REG = '''# The QK and PV cases SKIP without AMX; a run that selects only them exits
# Catch2's code 4. SKIP_RETURN_CODE + the skip_return_code_4 label report
# that as skipped (ctest and Slice) rather than failed.
add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake
  PROPERTIES SKIP_RETURN_CODE 4 LABELS fake)
set_property(TEST t_amx_numerics APPEND PROPERTY LABELS skip_return_code_4)'''
cut('<p>Proposed registration:</p>', 'LABELS "fake;skip_return_code_4")</code></pre>',
    '<p>The registration:</p>\n'
    f'<pre><code>{esc(I26_REG)}</code></pre>\n'
    '<p>The second label is appended with <code>set_property</code>, the way <code>t_mwaitx_cliff</code> appends its label. '
    'One call cannot carry both labels. <code>add_catch_test</code> forwards its arguments unquoted, so a list such as <code>"fake;skip_return_code_4"</code> splits into two items. '
    '<code>set_tests_properties</code> then gets an odd number of values and stops the configure.</p>',
    must_contain=('add_catch_test(NAME t_amx_numerics LIBRARIES tron pos_fake',))

# --------------------------------------------------------------------------
# Words used here
# --------------------------------------------------------------------------
rep('With it OFF, both AMX test binaries hold one placeholder case that reports SUCCEED. After the I10 edit, t_amx_numerics also holds the transpose case, which needs no AMX.</li>',
    'At the reviewed commit, with it OFF, both AMX test binaries hold one placeholder case that reports SUCCEED. '
    'In the final tree, t_amx_numerics holds the transpose case in place of its placeholder, and t_amx_dispatch_dtype keeps its placeholder.</li>')
rep('<li><strong>tree hash</strong>: git\'s identifier for the exact content of a directory tree. Two trees with the same hash hold the same files.</li>',
    '<li><strong>tree hash</strong>: git\'s identifier for the exact content of a directory tree. Two trees with the same hash hold the same files.</li>\n'
    '<li><strong>pre-review</strong>: a review of the edits of this round by an independent agent, before anything is pushed. '
    'It used the review checklists folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments.</li>')
a = s.index('<h2 id="words">')
b = s.index('</ul></details>', a)
n_terms = s[a:b].count('<li><strong>')
rep('<summary>Open the word list (36 terms)</summary>', f'<summary>Open the word list ({n_terms} terms)</summary>')

# --------------------------------------------------------------------------
# Part C
# --------------------------------------------------------------------------
rep('<p><strong>Status on 2026-11-19 at 19:39 PST.</strong>', '<p><strong>Status on 2026-11-19 at 20:48 PST.</strong>')
rep(OLD_TREE, TREE, count=2)
rep('runs with the option ON and instantiates the AMX branch of <code>apply_page_range</code>, so it covers the I5 and I6 lines.</li>',
    'runs with the option ON and instantiates <code>apply_dense_amx_page</code>, the function that holds the I5 and I6 lines.</li>'
    '<li><strong>Pre-review, about 20:40 PST:</strong> an independent agent reviewed the edits of this round and the draft of the PR description '
    'with the review checklists folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments. '
    'It reported 4 findings to fix before the push and 3 smaller ones. All 7 are applied. '
    'The changes are in cards <a href="#I26">I26</a>, <a href="#I19">I19</a>, <a href="#I10">I10</a>, <a href="#I20">I20</a>, <a href="#I5">I5</a>, '
    '<a href="#T10">T10</a> and <a href="#I13">I13</a>, and in the draft of the PR description.</li>'
    '<li><strong>Local checks after the pre-review, at 20:47 PST:</strong> the syntax check of both AMX test files, with the option ON and with the option OFF, '
    'gave 0 errors and 0 warnings. clang-format was clean, and <code>git diff --check</code> was clean.</li>')
rep('<li><code>t/CMakeLists.txt</code>: line 619 registration with <code>SKIP_RETURN_CODE 4</code> and the label (I26).</li>',
    '<li><code>t/CMakeLists.txt</code>: line 619 registration with <code>SKIP_RETURN_CODE 4</code>, and the label <code>skip_return_code_4</code> appended with <code>set_property</code> (I26).</li>')
rep('new transpose case above <code>#ifdef TRON_AMX_DISPATCH</code> (I10).</li>',
    'new transpose case above <code>#ifdef TRON_AMX_DISPATCH</code>, with the tag <code>[transpose]</code>, and the <code>#else</code> placeholder case removed (I10); '
    'the direct include of <code>tron/tensor/kv_cache_fwd.hpp</code> removed (I20).</li>')
rep('softmax-state block in <code>exercise_page</code> with the <code>kv_head</code> index (I19); two 16-head sections (I21); header comment lines 9-18 updated.</li>',
    'softmax-state check in <code>exercise_page</code> with the <code>kv_head</code> index, a PV double that writes a distinct value per row, and a second visit per round (I19); '
    'two 16-head sections (I21); header comment lines 9-18 updated; the direct include of <code>tron/tensor/kv_cache_fwd.hpp</code> removed (I20).</li>')
rep('<li><code>changelog.d/5022.changed.md</code> (new): one line. It waits for your word (box <a href="#open3">Needs your word</a>, point 1).</li>',
    '<li><code>changelog.d/5022.changed.md</code> (new): one line. You confirmed the wording in the third round (box <a href="#open3">third-round answers</a>, point 1).</li>')
cut('<h4>PR body edits</h4>', '(D2, your answer of 2026-11-19).</li></ul>',
    '<h4>PR body edits: drafted, not posted</h4>\n'
    '<p>The draft is <code>~/workspace/intel-AMX/muse-glimmer/pr5022-body-round2.draft.md</code>. '
    'Its placeholders (head commit, test date, run ids, compare result) are filled in after the runs.</p>\n'
    '<ul><li><strong>Short version:</strong> "the kv_mul-4 pack and QK kernels emit the same instructions as on main". '
    'The PV kernel has one more instruction, as the Verification section says.</li>'
    '<li><strong>Background:</strong> "Main supports only kv_mul 4 on AMX."</li>'
    '<li><strong>Verification, opening:</strong> the tests at the final head run on delphi-3b35. The token and performance measurements ran on delphi-3bda at 5061623a34. '
    'The commit 6198824246 is named "the merge base of the measured commit".</li>'
    '<li><strong>Verification, performance paragraph:</strong> the measurements are not repeated at the head. This PR\'s changes since the measured commit carry a low risk for performance. '
    'The head also contains main up to 3bea58b788, which the nightly systems test measures (T10, D2, D6).</li>'
    '<li><strong>Builds and tests:</strong> one row for the option OFF in the default CI build (<code>gcp-nix.yml</code>), and one row for the option ON in CI '
    '(<code>cmake-single-platform.yml</code>, started by hand) (I16, T5). The assertion and case counts, the per-section Catch2 output and the JUnit report come from the final run on delphi-3b35 (T4).</li>'
    '<li><strong>Performance:</strong> the rule sentence stands in one place, the qwen3-4b cell carries the label "no PR code on path", and the note is one bullet (I13).</li>'
    '<li><strong>Still to fill in:</strong> the object-compare row for 5061623a34 against the final head (T10, D6), '
    'and the re-check of the "same instructions as main" claim after the transpose move (I10).</li></ul>',
    must_contain=('guard-move bullet (I16)', 'Performance rule sentence'))
rep(f'At 19:33 PST the machine had not rebooted: its boot time was still 2026-08-24 16:12:16 {ref(41)}.',
    f'At 20:47 PST the machine had not rebooted: its boot time was still 2026-08-24 16:12:16 {ref(41)}.')

# --------------------------------------------------------------------------
# References
# --------------------------------------------------------------------------
rep('A further check at 19:33 PST read the same boot time.</li>', 'Further checks at 19:33 and 20:47 PST read the same boot time.</li>')
rep('prep.txt</code> of 2026-11-19 19:39 PST.', 'prep.txt</code> of 2026-11-19 20:48 PST.')

# --------------------------------------------------------------------------
# How this was checked
# --------------------------------------------------------------------------
rep('The local checks of Part C were not repeated for this page. Nothing was committed, pushed or posted, and no issue was filed.</p>\n</main></body></html>',
    'The local checks of Part C were not repeated for this page. Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '<p><strong>Update of 2026-11-19, pre-review (20:40 to 20:56 PST).</strong> An independent agent reviewed the edits of this round and the draft of the PR description, '
    'with the review checklists folks-code-review, tron-code-review, cpp-coding-guide and simplify-cpp-comments. It reported 4 findings to fix before the push and 3 smaller ones. '
    f'All 7 are applied in the working tree, whose git tree hash is now <code>{TREE}</code>. '
    'The local checks were repeated after these edits, at 20:47 PST: the syntax check of both AMX test files with the option ON and with the option OFF gave 0 errors and 0 warnings, '
    'clang-format was clean, and <code>git diff --check</code> was clean. '
    'Four statements of the earlier drafts were wrong and are corrected. '
    'First, the I5 reply credited <code>t_llama_unit</code> with real-value coverage of the dense AMX path. That test does not reach the path, because its model has one query head per KV head. '
    'Second, the registration in the I26 reply would have stopped every CMake configure. '
    'Third, the state check of I19 could not see which PV row feeds which head, and it never reached the merge line. '
    'Fourth, the two epilogue edits are in <code>apply_dense_amx_page</code>, not in <code>apply_page_range</code>. '
    'Also changed: the tag of the transpose case and the removed placeholder case (I10), the removed include (I20), '
    'the wording on performance risk (T10 and the combined reply), and the final note on the qwen3-4b row (I13). '
    'Every code block that this update quotes was compared with the working tree, and the I13 texts with the draft of the PR description. '
    'Not done at the time of this update: no build and no test ran at the final head, because delphi-3b35 still had its old boot time at 20:47 PST. '
    'Nothing was committed, pushed or posted, and no issue was filed.</p>\n'
    '</main></body></html>')

# --------------------------------------------------------------------------
# Final checks, then write
# --------------------------------------------------------------------------
for m in re.finditer(r'<div class="reply">', s):
    blk = s[m.start():div_end(m.start())]
    assert '3997' not in blk, 'reply block mentions 3997: ' + blk[:120]
a = s.index('<h2 id="todo">')
b = s.index('<h2 id="refs">')
assert '3997' not in s[a:b], 'Part C mentions 3997'
assert OLD_TREE not in s and s.count(TREE) == 3
for stale in ('real-value coverage is', 'The real-value coverage', 'LABELS "fake;skip_return_code_4")', 'tag <code>[q_pack]</code>, with the sections',
              'Proposed registration', 'Proposed block (untested', 'two new small points', 'It waits for your word', 'Needs your word',
              'in two rounds', 'The changes since that commit', 'The changes since then', '19:33 PST the machine'):
    assert stale not in s, f'stale phrase left: {stale!r}'
# apply_page_range must not be named as the home of the I5 and I6 edits
for m in re.finditer(r'apply_page_range', s):
    ctx = s[max(0, m.start() - 200):m.start() + 200]
    assert 'two edits in' not in ctx and 'I5 and I6 lines' not in ctx, ctx
n_refs = len(re.findall(r'<li id="R\d+">', s))
for n in range(1, n_refs + 1):
    assert s.count(f'id="R{n}"') == 1 and f'href="#R{n}"' in s, f'R{n} missing or uncited'

open(P, 'w', encoding='utf-8').write(s)
open(LAST, 'w').write(md5(P) + '\n')
print(f'{n_rep} replacements; {len(s.encode("utf-8"))} bytes; {s.count(chr(10)) + 1} lines; {n_terms} terms; md5 {md5(P)}')
