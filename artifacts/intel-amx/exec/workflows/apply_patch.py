#!/usr/bin/env python3
"""Apply the 2026-11-19 decisions to respond-2-Isaac.html.
Every edit is anchored on an exact string or an exact line start, and the script stops on the first anchor that does not match."""
import html, re, sys

SP = '/tmp/claude-0/-home-jhan-workspace-intel-AMX-muse-glimmer/78b9fca8-c24b-4ac2-a02d-0236a437cdd6/scratchpad'
SRC = SP + '/respond-2-Isaac.orig.html'          # untouched copy of the page as of 2026-10-30
DST = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
TRON = '/home/jhan/workspace/ai-runs/pr5022-isaac/tron-head'

L = open(SRC, encoding='utf-8').read().split('\n')        # L[i-1] is line i

def line(n, starts):
    assert L[n - 1].startswith(starts), 'line %d starts with %r, expected %r' % (n, L[n - 1][:80], starts)
    return L[n - 1]

def sub(n, old, new, count=1):
    s = L[n - 1]
    assert s.count(old) == count, 'line %d: %d occurrences of %r' % (n, s.count(old), old[:70])
    L[n - 1] = s.replace(old, new)

def esc(s):
    return html.escape(s, quote=False)

# ---------------------------------------------------------------- the clean diff for the I6 reply
src = open(TRON + '/h/tron/models/self_attention.hpp').read().split('\n')
S = lambda n: src[n - 1]
d = ['--- a/h/tron/models/self_attention.hpp', '+++ b/h/tron/models/self_attention.hpp',
     '@@ line 7 @@', '-' + S(7), '@@ lines 1792-1805 @@']
for n in (1792, 1793, 1794): d.append(' ' + S(n))
for n in (1795, 1796, 1797): d.append('-' + S(n))
d.append('+        tron::const_view<float, true, false, tron::seq<operation_head_size>> row{')
d.append('+            amx_o + offset * operation_head_size};')
d.append(' ' + S(1798)); d.append(' ' + S(1799))
d.append('-' + S(1800)); d.append('+' + S(1800).replace('scratch', 'row'))
d.append(' ' + S(1801)); d.append(' ' + S(1802))
d.append('-' + S(1803)); d.append('+' + S(1803).replace('scratch', 'row'))
d.append(' ' + S(1804)); d.append(' ' + S(1805))
assert 'scratch' in S(1800) and 'scratch' in S(1803) and 'memcpy' in S(1796) and S(7) == '#include <cstring>'
clean_diff = '<pre><code>' + esc('\n'.join(d)) + '</code></pre>'

# ---------------------------------------------------------------- top of the page
line(53, '<p class="sub">PR 5022')
sub(53, '&middot; drafts prepared 2026-10-30, nothing posted</p>',
    '&middot; drafts prepared 2026-10-30 &middot; your decisions of 2026-11-19 applied &middot; nothing posted</p>')
sub(54, '<a href="#todo">To-do</a><a href="#prov">How this was checked</a></nav>',
    '<a href="#todo">To-do</a><a href="#refs">References</a><a href="#prov">How this was checked</a></nav>')
line(55, '<div class="short" id="short">')
L[54] = ('<div class="short" id="short"><p><strong>Short version.</strong> Isaac requested changes on PR 5022 with one review body and 26 inline comments, '
         'and every claim he makes about the code checks out at the reviewed commit (4c4b7b8864). You made the six decisions on 2026-11-19, and the drafts below now follow them. '
         'Three points still need your word before anything is posted: two accepted edits now land without a throughput number, one new tracking issue is proposed, '
         'and the test runs at the final head move to the server delphi-3b35.</p></div>')

# ---------------------------------------------------------------- words used here
line(61, '<h2 id="words">Words used here</h2><ul>')
line(72, '<li><strong>delphi-3bda</strong>')
L[71] = ('<li><strong>delphi-3bda</strong>: the Granite Rapids (Intel Xeon 6962P) test host with AMX. The PR\'s own test and benchmark records come from it. '
         'It is no longer available for our own runs. It still runs the nightly systems test.</li>\n'
         '<li><strong>delphi-3b35</strong>: the Granite Rapids (Intel Xeon 6962P) server that is our default test host since 2026-11-12. It has AMX and the same compiler build. '
         'Its throughput numbers cannot stand next to delphi-3bda numbers: TSX is off, no Speed Select setup runs, the deep idle states are on, and another user shares the machine.</li>\n'
         '<li><strong>nightly systems test</strong>: the run that installs the nightly tron package on delphi-3bda every night and reports throughput per model.</li>\n'
         '<li><strong>platformd</strong>: the host management service. It brings a server up after boot and starts rinzler.</li>\n'
         '<li><strong>Intel Speed Select</strong>: a CPU feature that lets chosen cores run with a higher frequency limit than the others.</li>\n'
         '<li><strong>TSX</strong>: Intel transactional memory instructions. The boot argument tsx=on switches them on.</li>\n'
         '<li><strong>object compare</strong>: compile one source file at two commits with the same compiler and flags, then compare the instruction listings function by function.</li>\n'
         '<li><strong>merge queue</strong>: the GitHub feature through which every pull request enters main. In this repository it squashes each pull request into one commit.</li>\n'
         '<li><strong>fake device</strong>: pos_fake, a software stand-in for the FPGA cards that the unit tests link.</li>\n'
         '<li><strong>PDT</strong>: Pacific Daylight Time, 7 hours behind UTC.</li>')
assert L[79] == '</ul>', L[79]
n_terms = sum(x.count('<li><strong>') for x in L[61:79])
L[60] = '<h2 id="words">Words used here</h2><details><summary>Open the word list (%d terms)</summary><ul>' % n_terms
L[79] = '</ul></details>'

# ---------------------------------------------------------------- decisions section (lines 81-87)
line(81, '<h2 id="decisions">Decisions that are yours before posting</h2>')
for n, k in zip(range(82, 88), ('D1', 'D2', 'D3', 'D4', 'D5', 'D6')):
    line(n, '<div class="dec" id="%s">' % k)
dec = open(SP + '/frag_decisions.html', encoding='utf-8').read().rstrip('\n')
assert dec.count('@@I6DIFF@@') == 1
dec = dec.replace('@@I6DIFF@@', open(SP + '/frag_i6diff.html', encoding='utf-8').read())
dec = re.sub(r'\[R(\d+)\]', r'<a class="ref" href="#R\1">[R\1]</a>', dec)
L[80] = dec
for n in range(82, 88):
    L[n - 1] = None

# ---------------------------------------------------------------- Part A cards
line(131, '<div class="row"><div class="k">Checked</div><div>Confirmed that no in-repo record exists.')
sub(131, 'Needs a delphi-3bda run at the final head.', 'Needs a run on an AMX host at the final head. That host is delphi-3b35 since 2026-11-12.')
sub(133, 'from delphi-3bda (a Granite Rapids host with AMX)', 'from delphi-3b35 (a Granite Rapids host with AMX)')
sub(149, 'Real-AMX execution evidence is the delphi-3bda per-section record above.', 'Real-AMX execution evidence is the per-section record above.')

# T8
line(164, '<div class="row"><div class="k">Checked</div><div>Confirmed. No per-kernel timer exists')
sub(164, "so the response is an offer, not a promise he asked for.</div></div>",
    "so the response is an offer, not a promise he asked for. The record files still exist after the loss of delphi-3bda: they are under exec/results/ on shared storage. Decision D6: no new timing in this PR.</div></div>")
line(167, '<p>Two things I can add:</p>')
line(168, '<ol><li>The A/B record files')
line(169, '<p>Say if you want only one of the two.</p></div></div>')
L[166] = '<p>What I can add now:</p>'
L[167] = ('<ul><li>The A/B record files, attached to this PR as a comment: <code>glimmer-20261016/rt-results.txt</code> and <code>attn-stats-compare.md</code>, '
          '<code>glimext-20261018/rt-results.txt</code> and <code>identity.txt</code>, <code>glimci-20261017/summary.md</code>.</li></ul>')
L[168] = ('<p>What I cannot add to this PR: a per-kernel timing on Granite Rapids. delphi-3bda, the host of this PR\'s measurements, is no longer available for my runs. '
          'That timing is the first item of the kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack): ns per call for <code>pack_q_group_128x4</code>, '
          '<code>qk_rowmajor_128x4</code> and <code>weights_times_v_128x4</code>, each at 4 and 16 heads, on a dense 64-token page fixture, median over at least 1,000 calls. '
          'Each of those changes then lands with a before-and-after number. Until then your Zen 4 figures are the only per-kernel numbers, and I do not dispute them.</p></div></div>')

# T9
line(173, '<div class="row"><div class="k">Checked</div><div>Partly confirmed.')
sub(173, "Decision D4; the draft declines the 'add 8 here' branch with the reason.",
    "Decision D4, made 2026-11-19: 8 stays out, the reply gives your reason, and it promises no tracking issue.")
line(177, '<p>Why not add 8 in this PR:')
line(178, '<p>Will do: write the reason into the <code>group_heads_ok</code> comment')
L[176] = ('<p>Why not add 8 in this PR: every group size has to pass the full system tests before it is enabled. For 8 that means its numerics sections on AMX hardware, '
          'plus token identity and 8-user throughput for llama-3.1-70b and qwen-3-32b. None of that has run. This PR is scoped to one shape, Muse Glimmer\'s kv_mul 16, '
          'and its measurements cover 4 and 16 only.</p>')
L[177] = '<p>Will do: write the reason into the <code>group_heads_ok</code> comment (text under Architecture gap 1).</p></div></div>'

# T10
line(182, '<div class="row"><div class="k">Checked</div><div>Confirmed gap.')
L[181] = ('<div class="row"><div class="k">Checked</div><div>Gap confirmed, and measured on 2026-11-19. The object compare of the kernel file between 5061623a34 and 4c4b7b8864 '
          'shows identical listings for 10 of its 11 functions. <code>qk_rowmajor_128x4&lt;16&gt;</code> has the same 207 instructions with two neighbouring counter increments swapped '
          '[exec/results/objcmp5022-20261119/objcmp.txt]. The cause is s + r * TILE_ROWS_16 in place of s + r * 16. The other source changes produce no difference in that file: '
          'comments, two type aliases, an unpacked_tile alias, two static_asserts and the if-constexpr ladder. The call site changed in one hoisted constexpr operation_kv_mul and is not compared. '
          'Decision D6, made 2026-11-19: no rerun.</div></div>')
line(183, '<div class="reply"><div class="lbl">Reply</div><p>Both. The object compare closes the kernel side.')
line(187, '<ol><li>Compile <code>amx_attn.cpp</code> at 5061623a34 and at the final head')
L[182] = ('<div class="reply"><div class="lbl">Reply</div><p>The object compare. I cannot offer the rerun: delphi-3bda, the host of this PR\'s measurements, is no longer available for my runs, '
          'and numbers from another host cannot stand next to them.</p>\n'
          '<p>The compare for the head you reviewed is done. I compiled <code>src/tron/kernels/amx_attn.cpp</code> at 5061623a34 (the measured commit) and at 4c4b7b8864 with the compiler build '
          'of the measured binaries (Ubuntu clang 19.1.7) and the flags CMake uses for this file. Then I compared the instruction listings function by function:</p>\n'
          '<ul><li><code>pack_q_group_128x4&lt;4&gt;</code> and <code>&lt;16&gt;</code>, <code>qk_rowmajor_128x4&lt;4&gt;</code>, <code>weights_times_v_128x4&lt;4&gt;</code> and <code>&lt;16&gt;</code>: '
          'identical listings (509, 1285, 204, 121 and 206 instructions). The five other functions of the file are identical too.</li>'
          '<li><code>qk_rowmajor_128x4&lt;16&gt;</code>: the same 207 instructions. Two neighbouring counter increments at the end of the outer loop changed places '
          '(<code>addq $0x40, %rdx</code> and <code>addq $0x400, %rsi</code>).</li></ul>')
L[183] = ('<p>The cause is one source line: <code>s + r * TILE_ROWS_16</code> replaced <code>s + r * 16</code> [src/tron/kernels/amx_attn.cpp:243]. <code>r</code> is an <code>int</code> and '
          '<code>TILE_ROWS_16</code> is a <code>size_t</code>, so a signed 32-bit multiply became an unsigned 64-bit multiply. The other source changes between the two commits produce no difference in this file:</p>')
line(185, '<ul><li>Two type aliases replace the spelled-out K and V view types')
sub(185, '</li><li>The pack call site reads <code>geometry.kv_mul()</code> into a <code>constexpr</code> local before use [h/tron/models/self_attention.hpp:1693-1696].</li></ul>', '</li></ul>')
L[185] = ('<p>Limits of this compare. It covers one object file without link-time optimization. The thin-LTO bitcode of the two commits differs only in a flag on four shift operations, two in each QK kernel, and all four come from that same source line. '
          'The call site is not covered: between the two commits it changed in one <code>constexpr</code> local that holds <code>geometry.kv_mul()</code> [h/tron/models/self_attention.hpp:1693-1696].</p>\n'
          '<p>Will do:</p>')
L[186] = ('<ol><li>Repeat the compare at the final head of this PR, because this review changes the kernel file again (the transpose moves to a header, and two asserts change). '
          'The result goes into the Verification section as a new row.</li>'
          '<li>Keep the sentence "Benchmarks are not rerun at the current head". Add after it the compare result. Add also that the two epilogue edits from this review '
          '(the <code>s_pages</code> tag and the row view, under your inline comments at self_attention.hpp:1755 and :1788) came after the measurement and have no throughput number.</li></ol></div></div>')

# combined reply
line(219, '<ul><li><strong>CI lane.</strong>')
sub(219, 'Per-section Catch2 output, JUnit report, kill-switch run, host and commit from delphi-3bda at the final head, in the Verification section.',
    'Per-section Catch2 output, JUnit report, kill-switch run, host and commit from a Granite Rapids host (delphi-3b35) at the final head, in the Verification section.')
sub(219, 'No per-kernel number exists; I will attach the A/B record files and offer a per-kernel timing on delphi-3bda as the baseline of a kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack).',
    'No per-kernel number exists. I will attach the A/B record files. A per-kernel timing on Granite Rapids is the first item of a kernel-performance follow-up issue (vectorised pack, stage-3 hoist, lazy pack).')
sub(219, "I still keep 8 out of this PR, because its kernels have never run on AMX hardware and this PR's validation covers 4 and 16; the reason goes into the <code>group_heads_ok</code> comment and a follow-up issue tracks 8.",
    "I still keep 8 out of this PR: every group size has to pass the full system tests before it is enabled, and this PR is scoped to Muse Glimmer's kv_mul 16. The reason goes into the <code>group_heads_ok</code> comment.")
sub(219, 'Object compare of all six instantiations between 5061623a34 and the final head, plus one Glimmer rerun cell and the llama-3.1-8b token-identity cell at the final head, because the epilogue edits you asked for are on that path.',
    'Object compare, no rerun: the host of this PR\'s measurements is no longer available for my runs. Between 5061623a34 and the head you reviewed, five of the six kernel instantiations compile to identical listings, '
    'and <code>qk_rowmajor_128x4&lt;16&gt;</code> has the same 207 instructions with two neighbouring counter increments swapped. I repeat the compare at the final head. '
    'The two epilogue edits you asked for come after the measurement, and the PR body will say so.')

# ---------------------------------------------------------------- Part B table and card heads: hardware tags
for n in (226, 227, 228, 231, 234, 246, 247, 248, 284, 292, 304, 371, 396, 560, 584, 592):
    sub(n, '<span class="tag hw">needs delphi-3bda</span>', '<span class="tag hw">needs an AMX host</span>')
for n in (226, 231, 234, 284, 371, 396):          # I4, I9, I12: nothing runs for them in this PR
    sub(n, '<span class="tag hw">needs an AMX host</span>', '<span class="tag fu">follow-up issue</span>')

# I2, I11, I18: the merge queue squashes
line(266, '<p>I plan to squash-merge this PR, so main gets one commit with the gate change and its comments together.')
L[265] = ('<p>The merge queue of this repository squashes every pull request into one commit. So main gets the gate change and its comments together, '
          'and no intermediate commit of this branch lands.</p></div>')
line(394, '<p>I plan to squash-merge this PR, so the three-step history would not survive on main.')
L[393] = ('<p>The merge queue of this repository squashes this PR into one commit, so a three-step history would not reach main. One note on your step 2: it is a test-reporting change rather than a refactor. '
          'On a host without AMX the Catch2 summary then says 2 skipped instead of 4 passed; the exit code stays 0, because the gate and packer cases still pass [t/t_amx_numerics.cpp:90, :306].</p></div>')
line(475, '<p>I plan to squash-merge, so no intermediate step needs to build on its own.')
L[474] = ('<p>The merge queue of this repository squashes this PR into one commit, so no intermediate step has to build on its own. The queue builds the squashed commit before it lands.</p></div>')

# I4: the alternative is no longer open
line(290, '<div class="reply alt"><div class="lbl">If the alternative is chosen</div>')
L[289] = None

# I5
line(302, '<p>Coverage: <code>t_amx_dispatch_dtype</code> drives this path')
line(303, '</div>')
L[301] = ('<p>Coverage: <code>t_amx_dispatch_dtype</code> drives this path with kernel test doubles that also write every row. The real-value coverage is <code>t_llama_unit</code> with the option on. '
          'I will rerun both at the final head on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch. The change alters no values.</p>\n'
          '<p>One limit. The benchmarks in the PR body were measured before this edit, and I cannot rerun them (see my reply on benchmark provenance). The PR body will say that this edit has no throughput number.</p></div>\n'
          '<div class="reply alt"><div class="lbl">If I5 moves to the performance follow-up (open point 1)</div><p>Agreed that the fill is wasted work. The 2-D tensor default constructor zero-fills '
          'kv_mul x 64 x 4 bytes (4096 bytes at kv_mul 16) [h/tron/tensor/tensor.hpp:40-42, :254-256]. The QK kernel then overwrites every element before the epilogue reads <code>s_pages</code> '
          '[src/tron/kernels/amx_attn.cpp:220-253].</p>\n'
          '<p>I will not change it in this PR. The line is on the path this PR\'s benchmarks measured. It is also on the kv_mul 4 path that llama-3.1-8b uses today. I cannot rerun the benchmarks: '
          'delphi-3bda, the host of this PR\'s measurements, is no longer available for my runs. I will make the change in the kernel-performance follow-up, where it lands with a measurement.</p></div>')

# I6
line(305, "<div class=\"row\"><div class=\"k\">Isaac's point</div><div>Each head's PV row is copied into a stack tensor before fma")
L[304] = ("<div class=\"row\"><div class=\"k\">Isaac's point</div><div>The comment sits on line 1788, the call of the PV kernel, and it is about the code below that call: "
          "\"Just below this call, each head's PV row is copied into a stack tensor before fma\" (16 x 512 B per dense page visit at 16 heads). "
          "An aligned const_view over the row in amx_o satisfies fma and set, so the copy at lines 1795-1797 can go.</div></div>")
line(306, '<div class="row"><div class="k">Checked</div><div>fma takes any expression')
sub(306, 'The AVX-path scratch at :1958 is an output buffer and stays. <span class="sub">(claim confirmed)</span>',
    'The AVX-path scratch at :1958 is an output buffer and stays. Why line 1788: a review comment has to sit on a line of the diff, the changed block covers lines 1781-1791, '
    'and the copy at 1795-1797 is unchanged code outside it. His evidence line names the target: "sed -n 1795,1797p". const_view has a default stride argument, so his four-argument spelling names the type '
    'that tensor::as_view returns [h/tron/tensor/views.hpp:31-36; h/tron/tensor/tensor.hpp:75-76]. The memcpy is the only use of &lt;cstring&gt; in the file, and commit b431585224 added both. '
    'The edit is not compiled yet. <span class="sub">(claim confirmed)</span>')
line(308, '<div class="reply"><div class="lbl">Reply</div><p>Agreed. I will replace the stack copy with an aligned view over the row.</p>')
L[307] = '<div class="reply"><div class="lbl">Reply</div><p>Agreed. I will replace the stack copy just below the PV call with your aligned view over the row.</p>'
line(310, '<p>Proposed edit at lines 1795-1803:</p>')
line(311, '<pre><code>        tron::const_view&lt;float, true, false, tron::seq&lt;operation_head_size&gt;&gt; row{')
line(320, '        }</code></pre>')
line(321, '<p>The memcpy at :1796 was the only one in the file')
line(322, '<p>The AVX-path <code>scratch</code> at line 1958 stays.')
line(323, '</div>')
L[309] = '<p>The edit: lines 1795-1797 become the view, lines 1800 and 1803 read it, and line 7 loses the include.</p>'
L[310] = clean_diff
for n in range(312, 321):
    L[n - 1] = None
L[320] = ('<p>The <code>memcpy</code> at line 1796 was the only use of <code>&lt;cstring&gt;</code> in the file, so the include goes with it. The values read are the same as before, so I expect no numerics change. '
          'I will rerun <code>t_amx_numerics</code>, <code>t_amx_dispatch_dtype</code> and <code>t_llama_unit</code> at the final head on a Granite Rapids host (delphi-3b35), with AMX on and under the kill switch.</p>\n'
          '<p>One limit. The benchmarks in the PR body were measured before this edit, and I cannot rerun them (see my reply on benchmark provenance). I have no timing for the saved 8 KB of copies per page visit, '
          'and the PR body will say so.</p>')
L[321] = ('<p>The AVX-path <code>scratch</code> at line 1958 stays. There it is the output buffer of <code>page::scaled_v</code>, not a copy.</p></div>\n'
          '<div class="reply alt"><div class="lbl">If I6 moves to the performance follow-up (open point 1)</div><p>Agreed that the copy is not needed. <code>fma</code> and <code>set</code> take any expression, '
          'and an aligned <code>const_view</code> over the row in <code>amx_o</code> is sound [h/tron/kernels/expr.hpp:537-542; h/tron/tensor/view.hpp:186-188, :360-362; h/tron/models/self_attention.hpp:1787].</p>\n'
          '<p>I will not change it in this PR. The block is on the path this PR\'s benchmarks measured. It is also on the kv_mul 4 path that llama-3.1-8b uses today. I cannot rerun the benchmarks: '
          'delphi-3bda, the host of this PR\'s measurements, is no longer available for my runs. I will make the change in the kernel-performance follow-up, where it lands with a measurement.</p></div>')

# I7: no new wording on the TODO line that carries the issue link (D5); no review-time wording in a source comment
line(326, '<div class="row"><div class="k">Checked</div><div>Reproduced his grep counts')
sub(326, "the last two runs show test: skipped. <span class=\"sub\">(claim confirmed)</span>",
    "the last two runs show test: skipped. The TODO line with the link to #3997 is on main already [src/tron/CMakeLists.txt:217-218 at 6198824246]; the proposed text leaves those two lines as they are (D5). "
    "<span class=\"sub\">(claim confirmed)</span>")
line(330, '<pre><code># fast-path call sites. No pull-request lane sets the option at this head:')
sub(330, 'No pull-request lane sets the option at this head:', 'No pull-request lane sets the option:')
line(339, '# TODO(jhan): set the option in the required lane and make one real-AMX')
line(340, '# test execution a required check')
line(341, '# (https://github.com/positron-ai/tron/issues/3997).</code></pre>')
L[338] = '# TODO(jhan): make one real-AMX test execution a required CI check'
L[339] = None

# I9, I12, I13
line(377, '<ul><li>The loop is a plain scalar copy')
sub(377, "I will run it on delphi-3bda with the PR's clang 19.1.7 build as the follow-up's baseline, and take the per-call timing on Granite Rapids rather than Zen 4.",
    "The follow-up starts with that census on the project's clang 19.1.7 build, and it takes the per-call timing on Granite Rapids rather than Zen 4.")
sub(403, "the follow-up's per-kernel microbenchmark on delphi-3bda would give it.", "the follow-up's per-kernel timing on Granite Rapids would give it.")
sub(411, 'is the measurement that would size it; I would rather not spend delphi-3bda time on that for this PR.',
    'is the measurement that would size it. I cannot run it for this PR: delphi-3bda, the host of these numbers, is no longer available for my runs.')

# I24, I25, I26
sub(582, 'so I will run <code>t_amx_numerics</code> on delphi-3bda and post the new per-section counts.',
    'so I will run <code>t_amx_numerics</code> on a Granite Rapids host (delphi-3b35) and post the new per-section counts.')
sub(586, 'so a plain build on delphi-3bda would measure the placeholder binary;', 'so a plain build would measure the placeholder binary;')
sub(586, 'its scheduled runs on 2026-10-18 and 2026-10-25 failed. <span class="sub">(claim confirmed)</span>',
    'its scheduled runs on 2026-10-18 and 2026-10-25 failed. The registry block is chosen by the server type, and delphi-3b35 has the same type as delphi-3bda, granite_rapids_6962p [bin/slice:2008-2010]. '
    '<span class="sub">(claim confirmed)</span>')
sub(588, '<code>bin/slice bench --update t_amx_numerics t_amx_dispatch_dtype</code> on delphi-3bda, then', '<code>bin/slice bench --update t_amx_numerics t_amx_dispatch_dtype</code> on delphi-3b35, then')
sub(588, 'delphi-3bda is the <code>granite_rapids_6962p</code> platform, so', 'delphi-3b35 is a <code>granite_rapids_6962p</code> host, so')
sub(605, 'On delphi-3bda the unfiltered run still passes with exit 0.', 'On an AMX host the unfiltered run still passes with exit 0.')

# ---------------------------------------------------------------- Part C
line(608, '<ul><li><code>h/tron/kernels/amx_attn_iface.hpp</code>: lines 14-16')
sub(608, 'lines 1795-1803 row view instead of memcpy, drop <code>&lt;cstring&gt;</code> (I6).', 'lines 1795-1797, 1800 and 1803: row view instead of memcpy, and line 7: drop <code>&lt;cstring&gt;</code> (I6).')
sub(608, '<li><code>src/tron/CMakeLists.txt</code>: lines 214-218 comment (I7 text, which also carries the ctest/Slice sentence from I10).</li>',
    '<li><code>src/tron/CMakeLists.txt</code>: lines 214-216 comment (I7 text, which also carries the ctest/Slice sentence from I10). The TODO at lines 217-218 stays as it is (D5).</li>')
line(610, '<ul><li><code>TRON_AMX_DISPATCH=OFF</code> row and the guard-move bullet (I16).</li>')
L[609] = ('<ul><li><code>TRON_AMX_DISPATCH=OFF</code> row and the guard-move bullet (I16).</li>'
          '<li>Performance rule sentence, the qwen3-4b cell label and the explanatory note (I13).</li>'
          '<li>Verification table: assertion and case counts refreshed once from the final run; per-section Catch2 output and JUnit from delphi-3b35 (T4); CMake-lane dispatch run and job ids (T5); '
          'object-compare row 5061623a34 against the final head (T10, D6); the \'same instructions as main\' claim re-checked after the transpose move (I10).</li>'
          '<li>The opening sentence of Verification, "All runtime results use delphi-3bda", becomes two sentences: the tests at the final head ran on delphi-3b35, and the token and performance measurements ran on delphi-3bda.</li>'
          '<li>After "Benchmarks are not rerun at the current head": the compare result, and one sentence that the I5 and I6 edits came after the measurement and have no throughput number (D2, D6).</li></ul>')
line(611, '<h4>Runs on delphi-3bda (follow the 3bda sharing rules;')
L[610] = '<h4>Runs on delphi-3b35 (compile and unit tests only, no benchmark; our half is <code>--instance 1,2</code>; one build, one test pass, one registry refresh, one body refresh, in that order)</h4>'
line(612, '<ol><li>Build the final head with')
L[611] = ('<ol><li>Build the final head with <code>cmake --preset native -DCMAKE_BUILD_TYPE=RelWithDebInfo -DBUILD_INGEST_MODELS=ON -DTRON_AMX_DISPATCH=ON</code> (the preset alone leaves the option OFF). '
          'Use a new worktree name under <code>/var/tmp/jhan/b35-*</code>, and never run <code>git worktree prune</code> there.</li>'
          '<li><code>gen/t_amx_numerics</code>, <code>gen/t_amx_dispatch_dtype</code>, <code>gen/t_llama_unit</code>, AMX on and with <code>TRON_AMX_DISABLE=1</code>; the four section-filtered runs and the JUnit report (T4); hostname, commit, cpuinfo flags.</li>'
          '<li>Object compare of the kernel file between 5061623a34 and the final head with <code>exec/objcmp5022-20261119</code> (T10), and of <code>qk_rowmajor_128x4&lt;4&gt;</code> against main after the transpose move (I10). '
          'Repeat both on the linked <code>runtron</code>, which that build provides.</li>'
          '<li><code>bin/slice route</code>, <code>bin/slice bench --update t_amx_numerics t_amx_dispatch_dtype</code>, <code>bin/slice bench --check</code> (I25, I26).</li></ol>\n'
          '<p>Not run, by your D6 decision: the Glimmer and llama benchmark cells, and the per-kernel timing (it is the first item of the follow-up issue).</p>\n'
          '<p>Needs your OK (open point 1): if I5 and I6 stay in this PR, one token-identity pair on delphi-3b35, measured commit against final head, for llama-3.1-8b and Glimmer at prompt 1024. '
          'It is a pass or fail check on one machine, and it uses the FPGA cards.</p>')
line(614, '<ul><li><code>gh workflow run cmake-single-platform.yml --ref jhan-amx-kvmul16 -F skip_benchmarks=true</code>')
sub(614, '<li>New issue: AMX attention kernel performance follow-up: vectorised pack (I9), stage-3 hoist (I12), lazy pack and lazy tile region (I4), with the Granite Rapids per-kernel timing as baseline (T8).</li>'
         '<li>New issue: serve kv_mul 8 (llama-70b family, qwen-3-32b), ordered after #5021 (T9).</li>'
         '<li>Edit #5021: add Isaac\'s spelling <code>amx_attn_h128</code> / <code>_128</code> (T12).</li></ul>',
    '<li>New issue, after your review of card N1: AMX attention kernels, performance follow-up: vectorised pack (I9), stage-3 hoist (I12), lazy pack and lazy tile region (I4), with the Granite Rapids per-kernel timing as its first item (T8).</li>'
    '<li>Comment on #5021, after your review of card N1: add Isaac\'s spelling <code>amx_attn_h128</code> / <code>_128</code> (T12).</li></ul>')

# ---------------------------------------------------------------- references, provenance, style
line(615, '<h2 id="prov">How this was checked</h2>')
sub(615, 'Nothing was posted to GitHub and nothing ran on delphi-3bda.</p>',
    'Nothing was posted to GitHub and nothing ran on delphi-3bda.</p>\n'
    '<p><strong>Update of 2026-11-19.</strong> Your decisions were applied to the drafts. Checked again on that day: the review comments with their diff blocks, the state of main (3bea58b788), '
    'issues #3997 and #5021, the merge queue and one month of merge history, your Slack messages with John Mark Wilkinson, and the platformd repository. '
    'The object compare ran on delphi-3b35 as two compiles of one file, pinned to our CPUs; nothing else ran there. The I6 code is still not compiled. '
    'One statement of the first version was wrong and is corrected: the two commits do not differ in spellings only (card T10). '
    'One citation of the first version was beside the point and is removed: pull request 5098 did not merge into main (card D3). Nothing was posted to GitHub, and no issue was filed.</p>')
L[614] = open(SP + '/frag_refs.html', encoding='utf-8').read().rstrip('\n') + '\n' + L[614]

css = '''.decided{display:inline-block;background:#cde2fb;color:#0d366b;font-size:11px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;padding:2px 8px;border-radius:10px;margin-left:8px;vertical-align:middle}
.qa{background:#fff;border:1px solid var(--line);border-radius:6px;padding:10px 14px;margin:10px 0}
.qa .q{font-weight:700;margin-bottom:6px}
.open{background:#fffbeb;border-left:4px solid var(--warn);padding:10px 14px;margin:14px 0}
table.grid th{font-weight:600}
table.grid td.on{background:#cde2fb}
table.grid td.new{background:#86b6ef}
table.grid td.off{background:#f3f4f6;color:#374151}
.cellk{display:block;font-size:11px;font-weight:700;letter-spacing:.02em;text-transform:uppercase;margin-bottom:2px}
table.shape td{font-size:12px;white-space:nowrap;padding:5px 6px}
table.shape th{white-space:nowrap;padding:5px 6px}
table.shape .cellk{white-space:normal}
.scrollx{overflow-x:auto}
.tag.dec{padding:2px 8px;margin:0 0 0 6px;border:0;border-radius:10px}
figure{margin:12px 0}
figcaption{font-size:13px;color:var(--muted);margin-top:4px}
pre.diff code span{display:inline-block;min-width:100%}
pre.diff .del{background:#fee2e2}
pre.diff .add{background:#dcfce7}
.tag.fu{background:#e5e7eb;color:#374151}
a.ref{font-size:12px;text-decoration:none}
ol.refs{list-style:none;margin-left:0;counter-reset:r}
ol.refs li{font-size:13.5px;margin:5px 0}
ol.refs li::before{content:"[R" counter(r) "] ";counter-increment:r;font-weight:700}
details summary{cursor:pointer;color:var(--accent);margin:6px 0}
'''
idx = [i for i, x in enumerate(L) if x is not None and x.startswith('</style></head><body><main>')]
assert len(idx) == 1, idx
L[idx[0]] = css + L[idx[0]]

out = '\n'.join(x for x in L if x is not None)
open(DST, 'w', encoding='utf-8').write(out)
print('written', DST, len(out), 'bytes;', out.count('\n') + 1, 'lines; word-list terms:', n_terms)
left = [m.start() for m in re.finditer('needs delphi-3bda', out)]
print('remaining "needs delphi-3bda":', len(left))
