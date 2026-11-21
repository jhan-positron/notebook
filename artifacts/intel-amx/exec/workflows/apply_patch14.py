#!/usr/bin/env python3
"""Page pass 14 (main session, 2026-11-20): jhan found "legacy workflow only" in draft reply B2 unnecessarily harsh.
The draft now says where the sections run, without "only" and without "I accept". Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p, encoding='utf-8').read(); orig = s
edits = [
 # B2 reply, paragraph 1
 ("<p>The facts are right. No workflow that a pull request triggers builds with <code>TRON_AMX_DISPATCH</code>, so these sections run only in the legacy workflow. The thread at src/tron/CMakeLists.txt:216 has the same point, and my reason for keeping the flag out of this PR: with it ON, every eligible model test",
  "<p>The facts are right: no workflow that a pull request triggers builds with <code>TRON_AMX_DISPATCH</code>. The thread at src/tron/CMakeLists.txt:216 has the same point, and my reason for keeping the flag out of this PR. With it ON, every eligible model test"),
 # B2 reply, paragraph 2
 ("(threads at t/t_amx_dispatch_dtype.cpp:143, :209 and :305). I accept for this PR that they run in the legacy workflow only.</p>",
  "(threads at t/t_amx_dispatch_dtype.cpp:143, :209 and :305). They run in the CMake workflow (<code>cmake-single-platform.yml</code>), which builds with the option ON. README.ci.md describes its manual run on the final commit of a PR.</p>"),
 # B2 reply, first bullet
 ("<ul><li>The legacy workflow, which builds with the option ON: run <a href=\"https://github.com/positron-ai/tron/actions/runs/44777748892\">44777748892</a>. Its test-host job passes all 106 host tests on an AMD runner (attempt 1) and on a Granite Rapids runner (attempt 2). <code>t_amx_dispatch_dtype</code> is one of them.</li>",
  "<ul><li>That workflow: run <a href=\"https://github.com/positron-ai/tron/actions/runs/44777748892\">44777748892</a>. Its test-host job passes all 106 host tests on an AMD runner (attempt 1) and on a Granite Rapids runner (attempt 2). <code>t_amx_dispatch_dtype</code> is one of them.</li>"),
 # B2 card, row "Checked": what the draft says now
 ("The draft states that as your position. The test file was behind the guard before this PR.",
  "The draft gives your reason for keeping the flag out, and it says where the sections run. It was reworded on 2026-11-20 after your note that \"legacy workflow only\" reads unnecessarily harsh: it no longer says \"only\" or \"I accept\". The test file was behind the guard before this PR."),
]
todo = 0
for old, new in edits:
    if new in s: continue
    assert s.count(old) == 1, ('not found exactly once', old[:70], s.count(old)); s = s.replace(old, new); todo += 1
if s != orig:
    open(p, 'w', encoding='utf-8').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
