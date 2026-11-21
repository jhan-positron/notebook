#!/usr/bin/env python3
"""Page pass 9 (main session, 2026-11-20, after the go): the instruction census of the 16-head pack and of the QK
store is reproduced from the object of the final head, so the replies I9 and I12 say so. Idempotent."""
p = '/home/jhan/workspace/intel-AMX/muse-glimmer/respond-2-Isaac.html'
s = open(p).read(); orig = s
edits = [
 # I9 reply: the census is reproduced
 ("<li>I have not reproduced the <code>vpextrw</code> census yet. The follow-up starts with that census on the project's clang 19.1.7 build, and it takes the per-call timing on Granite Rapids rather than Zen 4.</li>",
  "<li>Your <code>vpextrw</code> census holds. Built with the project's clang 19.1.7, the 16-head pack has 512 <code>vpextrw</code> stores in 1,285 instructions, and the 4-head pack has none in 509 instructions. The follow-up takes the per-call timing on Granite Rapids rather than Zen 4.</li>"),
 # I12 reply: the shuffle count at the reviewed commit and at the final head
 ("Your 40 vshuff64x2 also matches my earlier object compare (clang 19.1.7, qk_rowmajor_128x4: 0 / 40 lane shuffles for 4 / 16 heads, glimmer-20261016). That compare was made before head 4c4b7b8864; at this head I re-compared only <code>qk&lt;4&gt;</code>.",
  "Your 40 vshuff64x2 also matches the object of the kernel file, at the commit you reviewed and at the final head (clang 19.1.7, <code>qk_rowmajor_128x4</code>: 0 / 40 <code>vshuff64x2</code> for 4 / 16 heads)."),
 # I9 card, row "Checked": dated note
 ("His opcode census and timings are Zen 4 results and are not reproducible here. One refinement:",
  "His opcode census and timings are Zen 4 results and are not reproducible here. Update of 2026-11-20: the census is reproduced on delphi-3b35 with clang 19.1.7 (512 vpextrw in the 16-head pack, at the reviewed commit and at the final head; the listing is <code>objcmp/out-final/amx_attn.dis</code> in the results folder). The timings stay Zen 4 results. One refinement:"),
]
todo = 0
for old, new in edits:
    if old in s:
        assert s.count(old) == 1, ('not unique', old[:60]); s = s.replace(old, new); todo += 1
    else:
        assert new in s, ('neither old nor new text found', old[:60])
if s != orig:
    open(p, 'w').write(s)
print(f'applied {todo} edit(s); page bytes {len(s.encode())}')
