#!/usr/bin/env python3
"""Page pass 10 (main session, 2026-11-20, after the push): five replies stated the place of the new text with the
line numbers of the reviewed commit. They now give the line numbers of the pushed head ddf843ad97. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 ("Done: lines 14-16 now read</p>", "Done: lines 14-17 now read</p>"),                                    # I1
 ("<p>The text of lines 100-105 now:</p>", "<p>The text, now at lines 101-107:</p>"),                      # I3
 ("<p>The text at line 269 now:</p>", "<p>The comment, now at amx_attn.cpp:195-197:</p>"),                 # I15
 ("// t/t_amx_dispatch_dtype.cpp:272\n", "// t/t_amx_dispatch_dtype.cpp:335\n"),                           # I20
 ("// t/t_amx_dispatch_dtype.cpp:282\n", "// t/t_amx_dispatch_dtype.cpp:343\n"),                           # I20
 ("// t/t_amx_numerics.cpp:183\n", "// t/t_amx_numerics.cpp:236\n"),                                       # I20
 ("<p>New text at t/t_amx_numerics.cpp:117-119:</p>", "<p>New text, now at t/t_amx_numerics.cpp:175-177:</p>"),  # I23
]
todo = 0
for old, new in edits:
    if old in s:
        assert s.count(old) == 1, ('not unique', old[:60], s.count(old)); s = s.replace(old, new); todo += 1
    else:
        assert s.count(new) == 1, ('neither old nor new text found', old[:60])
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
