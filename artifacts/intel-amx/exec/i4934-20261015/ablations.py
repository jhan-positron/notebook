#!/usr/bin/env python3
"""ablations.py apply <a1|a2> <worktree>: apply one perf-only ablation of the issue #4934 fix to the worktree, as an
exact-text replacement that must match exactly once (otherwise exit 2 and change nothing). `ablations.py list` prints
name|file|meaning. The ablations change the generated tokens (a row-major tail row is read as VNNI bytes): they are
timing probes, never a candidate change.
  a1 rows-through-reader: the split after the loop sends every live token to qk_group (vnni_tokens = all ones); the
     per-page block mask is still read. fixoff minus a1off = the cost of the tail-row dotter path.
  a2 constant-mask: apply_page_range passes BLOCKS_PER_PAGE_MASK_0XF instead of reading page::k_vnni_blocks, so no
     per-page mask read and every live token through the reader. a1off minus a2off = the cost of the per-page read;
     a2off minus headoff = everything outside the software loop's split (the store path, the conversion, page state)."""
import os, sys
A = {
    'a1': ('h/tron/models/self_attention.hpp', 'tail rows through the reader, mask read kept',
           '            const uint64_t vnni_tokens = k_vnni::block_token_mask(vnni_blocks);\n',
           '            const uint64_t vnni_tokens = ~uint64_t{0};  // ABLATION a1: every live token through the reader\n'),
    'a2': ('h/tron/models/self_attention.hpp', 'no per-page mask read, tail rows through the reader',
           '            return page.template k_vnni_blocks<geometry.kv>(binding.kv_slot);\n',
           '            return k_vnni::BLOCKS_PER_PAGE_MASK_0XF;  // ABLATION a2: no per-page mask read\n'),
}
cmd = sys.argv[1] if len(sys.argv) > 1 else ''
if cmd == 'list':
    for k, (f, meaning, _, _) in A.items(): print(f'{k}|{f}|{meaning}')
    sys.exit(0)
if cmd != 'apply' or len(sys.argv) != 4 or sys.argv[2] not in A: print(__doc__); sys.exit(64)
f, meaning, old, new = A[sys.argv[2]]
p = os.path.join(sys.argv[3], f)
s = open(p).read()
n = s.count(old)
if n != 1: print(f'{sys.argv[2]}: the old text occurs {n} times in {p}, expected 1: nothing changed'); sys.exit(2)
open(p, 'w').write(s.replace(old, new))
print(f'{sys.argv[2]}: applied to {p} ({meaning})')
