#!/usr/bin/env python3
"""Patch 2 of round2-respond-2-issac.html: fixes from the confirmation round of the third version.

Each replacement asserts that its old text occurs exactly once. Usage: apply_page_patch2.py PAGE
"""
import sys

p = sys.argv[1]
s = open(p, encoding='utf-8').read()
REF = lambda n: f'<a class="ref" href="#R{n}">[R{n}]</a>'
R = []
def rep(old, new): R.append((old, new))

# word list: one more entry
rep('Open the word list (46 entries)', 'Open the word list (47 entries)')
rep('<dt>Dense page</dt>',
    '<dt>Mask, visible range</dt><dd>The mask splits the tokens into ranges and marks the ranges that a query may read. A marked range is a visible range of that query.</dd>\n<dt>Dense page</dt>')

# section 3
rep('If a later edit shares a model type with the library, the rule breaks without an error message.',
    'If a later edit shares a model type with the library, the one-definition rule is broken without an error message.')

# section 4, claim 17
rep(f'48 of the 49 commits on main that touched the registry since 2026-10-15 changed rows of one class {REF(10)}.</td>',
    f'Since 2026-10-15, 49 commits on main touched the registry, and 48 of them changed rows of one class {REF(10)}.</td>')

# section 5
rep('The CMake workflow sets the same three flags, and the real cases passed there.',
    'The CMake workflow sets three of these flags to the same values, and the real cases passed there.')
rep('<li>Two properties of the Nix build are not yet tested with this code.',
    '<li>Two properties of the Nix build are not yet tested by us with this code.')
rep('<li>Insufficient data on both properties. A verbose build log of the lane would resolve them.</li>',
    '<li>Insufficient data from our own runs on both properties. A verbose build log of the lane would resolve them.</li>\n'
    f'<li>Isaac reports that the test passes in a Nix sandbox build with the option OFF {REF(2)}. We did not repeat that build.</li>')
rep(f'<li>Draft PR 5572 of ours has the same gap, and the two commits do not close it there {REF(24)}. Its dispatch test still has the guard and the placeholder, and its registration line has no define.</li>',
    f'<li>In our draft PR 5572 the dispatch test still compiles to the placeholder with the option OFF {REF(24)}. The two commits do not change that. Its test file still has the guard, and its registration line has no define.</li>')
rep('shows 107 conflict hunks in 16 files. The same trial merge with our head shows the same 107, so the two commits add none.',
    'shows 107 conflicts in 16 files. The same trial merge with our head shows the same 107, so the two commits add none.')

# section 6, steps
rep('<li>Check that the Test host log of the required lane lists <code>t_amx_dispatch_dtype</code> and <code>t_amx_numerics</code> as passed.</li>',
    '<li>Check that the Test host log of the required lane lists <code>t_amx_dispatch_dtype</code> and <code>t_amx_numerics</code> as passed. Check also that no other check of the new head has failed.</li>')
rep('<li>List reviews and threads again. An automated review',
    '<li>List reviews, review threads and conversation comments again. An automated review')
rep('<li>Five steps write to GitHub: steps 2, 3, 6, 9 and 10.</li>',
    '<li>Five steps write to GitHub: steps 2, 3, 6, 9 and 10.</li>\n'
    '<li>The push also starts the workflows Slice tests and Debian smoke. Step 5 looks at their results too.</li>')

# section 6, table of open findings
rep(f'The weekly workflow wrote the current values of both rows of the dispatch test {REF(23)}.</td>',
    f'A weekly workflow, <code>bench-refresh.yml</code>, wrote the current values of both rows of the dispatch test {REF(23)}.</td>')
rep('The header comment needs its own edit, est. 2 lines.',
    'The comment in <code>amx_attn_iface.hpp</code> needs its own edit, est. 2 lines.')
rep('<td>One changed line covers fault m04 alone. Both clauses need one more parameter, a second mask range and two sections, est. 20 lines. Not built and not tested.</td>',
    '<td>One changed test line covers fault m04 alone. A test of both clauses needs one more helper parameter, a second visible range and two sections, est. 20 lines. Not built and not tested.</td>')
rep('<td>In the required lane <code>t_amx_numerics</code> runs 1 of its 5 test cases. Two of the other four',
    '<td>In the required lane <code>t_amx_numerics</code> runs 1 of its 5 test cases, the transpose case. Two of the other four')
rep('A commit that changes only the registry changes no compiled file.',
    'A registry-only commit changes no compiled file.')

# section 6, registry routes
rep(f'<li>Each route refreshes the row of one machine class. The repository asks for no more: its check fails only when a test has data on no class {REF(16)}.</li>',
    f'<li>A refresh of the row of one machine class is enough for the repository. Its check fails only when a test has data on no class {REF(16)}. Routes (a) and (c) refresh one row, and routes (b) and (d) can cover both rows.</li>')
rep(f'<li>48 of the 49 commits on main that touched the registry since 2026-10-15 changed rows of one class {REF(10)}. 16 of the 49 are Isaac\'s.</li>',
    f'<li>Since 2026-10-15, 49 commits on main touched the registry, and 48 of them changed rows of one class {REF(10)}. 16 of the 49 are Isaac\'s.</li>')
rep('<li>Route (a) cannot start today. The command reads the test list of a finished build, and our checkout holds no build. The guide asks for a build inside <code>nix develop</code>, in a checkout that the pool machines see at the same path.</li>',
    f'<li>Route (a) cannot start from this machine as it is. The command reads the test list of a finished build, and our checkout holds no build. This machine also has no <code>nix</code> command and no scheduler client {REF(16)}.</li>\n'
    '<li>The guide <code>doc/distributed-dice-agent-guide.md</code> asks for a build inside <code>nix develop</code>. The pool machines must see the checkout of that build at the same path.</li>')
rep('<li>Insufficient data on whether the pool accepts a job from this account. The section "Preflight From A Dev VM" of <code>doc/distributed-dice-agent-guide.md</code> lists the checks that would resolve it.</li>',
    '<li>Insufficient data on whether the pool accepts a job from this account on a machine that has the scheduler client. The section "Preflight From A Dev VM" of that guide lists the checks that would resolve it.</li>')
rep('1, 2 and 4 slices of the machine.', '1, 2 and 4 slices (eighths of the machine).')
rep('So its first run after the merge of PR 5022 measures the real cases.',
    'So its first run after the merge of PR 5022 is expected to measure the real cases.')
rep('<li>The four earlier pull requests of this kind were merged 2 to 3 days after their runs. These two have waited 35 days. Insufficient data on the reason, and their reviewer could tell it.</li>',
    '<li>The four earlier pull requests of this kind were open for 1 to 16 days before their merge. These two have been open for 35 days, and four weekly runs have updated them.</li>\n'
    '<li>Nobody has requested a review of these two. Insufficient data on the reason, and the people who merged the four earlier ones could tell it.</li>')

# section 6, kernel test candidates
rep(f'<li>Candidate 1 moves the eligibility case above the <code>#ifdef</code> of the test file {REF(25)}. The case holds only compile-time checks of <code>amx_attn_iface.hpp</code>, and that header has no <code>#ifdef</code>. It is est. 40 moved lines and no CMake change.</li>',
    f'<li>Candidate 1 moves the eligibility case above the <code>#ifdef</code> of the test file {REF(25)}. The case holds only compile-time checks, 15 of the 4,111 assertions. It is est. 40 moved lines, with two includes, and no CMake change.</li>\n'
    '<li>The pack case holds the other 4,096 assertions, and candidate 1 cannot move it. The pack function is defined in the kernel file, and the option-OFF build does not compile that file.</li>')
rep('<li>Candidate 2 lets <code>t_amx_numerics</code> compile the kernel file itself and pass the define, as PR 5606 does for the dispatch test. It is est. 10 lines in <code>t/CMakeLists.txt</code>. All five cases are then built in the required lane.</li>\n'
    '<li>With candidate 2 the QK and PV cases execute AMX when the Test host job runs on a Delphi runner. They skip on an Andoria runner.</li>',
    f'<li>Candidate 2 lets <code>t_amx_numerics</code> pass the define, as PR 5606 does for the dispatch test. It also lets the test compile the kernel file itself, as <code>t_memperf</code> compiles a source file from <code>src/</code> {REF(11)}. It is est. 10 lines in <code>t/CMakeLists.txt</code>.</li>\n'
    '<li>With candidate 2 all five cases are built in the required lane. The QK and PV cases then execute AMX when the Test host job runs on a Delphi runner. They skip on an Andoria runner.</li>')

# section 7, reply and notes
rep('test-host passes N_PASS of N_TOTAL tests on RUNNER_NAME. That workflow builds with',
    'test-host passes N_PASS of N_TOTAL tests on RUNNER_NAME, a Granite Rapids runner. That workflow builds with')
rep('<li>The reason of 2026-11-20 was the shared host. It does not answer the <code>--remote</code> route that <code>t/AGENTS.md</code> names, so a pointer to it would leave that route unanswered.</li>\n'
    '<li>If you choose route (a), (b) or (c) first, the last two bullets of the draft change.</li>',
    '<li>The reason of 2026-11-20 was the shared host. That reason does not cover the <code>--remote</code> route that <code>t/AGENTS.md</code> names. So a link to it would not say why that route was not used.</li>\n'
    '<li>Its sixth bullet and its last sentence state facts, and a reader can take them as reasons. Neither says why the <code>--remote</code> route was not used.</li>\n'
    '<li>The weekly refresh puts its rows into PR 5037 and PR 5038, and both are open drafts. So the rows on main change only when a person merges them.</li>\n'
    '<li>A shorter draft ends at the fifth bullet. It then holds no sentence that works as a reason.</li>\n'
    '<li>If you choose route (a), (b) or (c) first, the last two bullets and the last sentence of the draft change.</li>')

# section 8
rep('it is not full, and its range does not cover slot 63.', 'it is not full, and that range does not cover slot 63.')
rep(f'The second also needs a second mask range, because the mask allows no token without a range {REF(12)}.',
    f'The second also needs a second visible range, because the mask allows no token without a range {REF(12)}.')

# section 10
rep('<li>The third group applied your memory note on declined fixes. It found the one-class practice of the registry and the two candidates for the kernel test.</li>',
    '<li>The third group applied the memory note on declined fixes. That note is an agent\'s conclusion of 2026-11-23, and you did not state it as a rule. The group found the one-class practice of the registry and the two candidates for the kernel test.</li>\n'
    '<li>A fourth group of 3 reviewer agents checked the third version and reported 30 points. This text holds those fixes too.</li>')

# references
rep('<li><code>git log --first-parent --since 2026-10-15 origin/main -- config/test-benchmarks.json</code> lists 49 commits.',
    "<li><code>git log --first-parent --since '2026-10-15 00:00' origin/main -- config/test-benchmarks.json</code> lists 49 commits.")
rep('<li><code>t/CMakeLists.txt:612-615</code> registers <code>t_llama_unit</code> with a third define.</li>',
    '<li><code>t/CMakeLists.txt:612-615</code> registers <code>t_llama_unit</code> with a third define.</li>\n'
    '<li><code>t/CMakeLists.txt:228</code> registers <code>t_memperf</code> with the source file <code>../src/pos/memperf.cpp</code>.</li>')
rep('holds the build arguments of the CMake workflow, with the same three model flags.</li>',
    'holds the build arguments of the CMake workflow. Three model flags have the same values there.</li>')
rep('<li><code>bin/dice_lsf.py:66-69</code> maps <code>sku0</code> to genoa96 and <code>sku1</code> to graniterapids72.</li>',
    '<li><code>bin/dice_lsf.py:66-69</code> maps <code>sku0</code> to genoa96 and <code>sku1</code> to graniterapids72.</li>\n'
    '<li>On this machine <code>command -v nix bsub</code> prints nothing, and the folder <code>/tools/openlava/bin</code> does not exist.</li>')
rep('Its reader of the stale text lists the statements of the posted replies.</li>',
    'Its reader of the stale text lists ten statements of the posted replies, and its skeptic adds the eleventh.</li>')
rep('<li><code>wf_c467671d-862/journal.jsonl</code> holds the 5 reviewers of the second version.</li>',
    '<li><code>wf_c467671d-862/journal.jsonl</code> holds the 5 reviewers of the second version, and <code>wf_c4fd1b56-34a/journal.jsonl</code> the 3 reviewers of the third.</li>')
rep('The earlier ones, 4515, 4516, 4672 and 4674, were merged on 2026-09-23, 2026-09-22 and 2026-10-14.</li>',
    'The earlier ones, 4515, 4516, 4672 and 4674, were merged on 2026-09-23, 2026-09-22 and 2026-10-14.</li>\n'
    '<li>The earlier ones were opened on 2026-09-21 (4515, 4516) and on 2026-09-28 (4672, 4674).</li>')
rep('Each output holds 107 conflict hunks.</li>', 'Each output holds 107 conflicts.</li>')
rep('<li>The eligibility case holds <code>STATIC_REQUIRE</code> lines only. The QK case and the PV case skip when AMX is not available.</li>',
    '<li>The eligibility case holds 15 <code>STATIC_REQUIRE</code> lines and nothing else. The QK case and the PV case skip when AMX is not available.</li>\n'
    '<li><code>src/tron/kernels/amx_attn.cpp:126</code> defines the pack function.</li>')

for old, new in R:
    n = s.count(old)
    assert n == 1, f'old text found {n} times: {old[:90]!r}'
    s = s.replace(old, new)
open(p, 'w', encoding='utf-8').write(s)
print(f'{len(R)} replacements applied to {p}')
