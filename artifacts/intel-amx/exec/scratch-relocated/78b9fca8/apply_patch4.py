#!/usr/bin/env python3
"""Page pass 4 (2026-11-19, about 19:55 PST): jhan's third-round answers and the simpler wording about
performance evidence. Applies on top of the page as apply_patch3.py left it (plus one sentence edit of 19:50).
Idempotent: a second run finds the new texts and changes nothing."""
import sys
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p, encoding='utf-8').read()
MARK = '<!-- pass4 -->'
if MARK in s:
    print('already applied'); sys.exit(0)
def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (s.count(old), old[:90])
    s = s.replace(old, new)

# 1. open3: the two points are answered
a = s.index('<div class="open" id="open3">'); b = s.index('</ol></div>', a) + len('</ol></div>')
s = s[:a] + '''<div class="open" id="open3">''' + MARK + '''<p><strong>Answered on 2026-11-19, third round (about 19:50 PST).</strong> Nothing is open for you now. I ask once for the go to commit, push and post, when the tests at the final head are in.</p>
<ol>
<li><strong>The changelog fragment.</strong> Your answer: "wording is good". The file <code>changelog.d/5022.changed.md</code> stays in the working tree with this line <a class="ref" href="#R44">[R44]</a>:
<pre><code>- runtime: Speed up Muse Glimmer 30B attention with AMX on Intel hosts. (#5022)</code></pre></li>
<li><strong>The test policy and CI.</strong> Your answer: "We are going to run CI as part of this PR process, as you checked how to do it from Hannah announcement, correct?" Yes. After the push the default CI runs by itself with the option OFF, and I start the legacy CMake workflow by hand with the option ON (card <a href="#CI">CI</a>). So every new test executes in CI at the final head. Two limits against the exact words of the policy <a class="ref" href="#R43">[R43]</a>:
<ul>
<li>It is a single run. The legacy workflow is not among the required checks, so later pull requests do not rerun these tests.</li>
<li>The two kernel cases need an Intel runner, and GitHub picks the runner. If the test job lands on an AMD runner, I rerun that job. A rerun executes the tests again (<code>github.run_attempt &gt; 1</code> in <code>cmake-single-platform.yml:385-389</code>).</li>
</ul></li>
<li><strong>The final head.</strong> Your answer: "good".</li>
<li><strong>Performance evidence.</strong> Your words: "All the perf data captured at this PR were performed at delphi-3bda which is *the* CI machine. The code changes being done right now carry low risk of perf degradation. So I accept the risk that the PR perf numbers were not tested from latest CI." The replies in cards <a href="#T10">T10</a>, <a href="#I5">I5</a> and <a href="#I6">I6</a>, the combined reply and the PR description draft now say this in plain words.</li>
</ol></div>''' + s[b:]

# 2. T10: short reply
a = s.index('id="T10"'); b = s.index('id="T11"')
card = s[a:b]
ra = card.index('<div class="reply"><div class="lbl">Reply</div>'); rb = card.rindex('</div></div>')
new_reply = '''<div class="reply"><div class="lbl">Reply</div><p>No rerun. The performance numbers of this PR were measured on delphi-3bda, the machine of the nightly systems test, at 5061623a34. The changes since that commit carry a low risk for performance, so I accept that the numbers are not repeated at the final head.</p>
<ul><li>The kernel file compiles to the same instructions. An object compare with the compiler build and the flags of the measured binaries shows identical listings for 10 of its 11 functions between 5061623a34 and the final head. <code>qk_rowmajor_128x4&lt;16&gt;</code> has the same 207 instructions, with two neighbouring counter increments swapped. The record is in the Verification section.</li><li>The two edits in <code>apply_page_range</code> that you asked for remove work: one zero fill of the score buffer and one copy of each PV output row (your comments at self_attention.hpp:1755 and :1788).</li><li>The rest of this round is comments, tests and documentation.</li></ul>
<p>The nightly systems test measures Muse Glimmer and llama-3.1-8b throughput after the merge.</p></div>
<div class="row"><div class="k">Before posting</div><div>The first bullet states the compare at the final head. It is measured for the reviewed commit 4c4b7b8864 (10 of 11 identical, 2026-11-19). For the final tree, the local compare with clang 19.1.7 shows all 10 functions identical to 4c4b7b8864. The compare with the product flags on delphi-3b35 is pending, and the bullet is corrected if it shows anything else.</div></div>
<div class="row"><div class="k">Your decision</div><div>2026-11-19, third round: the performance data come from delphi-3bda, the CI machine, the edits of this round carry a low risk, and you accept that the numbers are not measured again at the final head.</div></div>'''
card = card[:ra] + new_reply + card[rb + len('</div>'):]
s = s[:a] + card + s[b:]

# 3. I5 and I6: the limit paragraphs
rep('<p>One limit. The benchmarks in the PR body predate this edit, and I cannot rerun them (see my reply on benchmark provenance). The PR body will say so.</p>',
    '<p>The performance numbers in the PR body predate this edit. The edit removes a zero fill, so its risk for performance is low, and I do not repeat the measurement (see my reply on benchmark provenance).</p>')
rep('<p>One limit. The benchmarks in the PR body predate this edit, and I cannot rerun them (see my reply on benchmark provenance). I have no timing for the saved 8 KB of copies per page visit. The PR body will say that the benchmarks predate this edit.</p>',
    '<p>The performance numbers in the PR body predate this edit. The edit removes a copy of 8 KB per page visit at 16 heads, so its risk for performance is low, and I do not repeat the measurement (see my reply on benchmark provenance).</p>')

# 4. combined reply: the benchmark bullet
a = s.index('<li><strong>Benchmark provenance.</strong>'); b = s.index('</li>', a) + len('</li>')
s = s[:a] + '<li><strong>Benchmark provenance.</strong> No rerun. The numbers were measured on delphi-3bda, the machine of the nightly systems test, at 5061623a34. The changes since then carry a low risk for performance: the kernel file compiles to the same instructions (object compare in the Verification section), and the two epilogue edits you asked for remove work. The nightly systems test measures Muse Glimmer and llama-3.1-8b throughput after the merge.</li>' + s[b:]

open(p, 'w', encoding='utf-8').write(s)
print('applied; bytes', len(s.encode('utf-8')))
