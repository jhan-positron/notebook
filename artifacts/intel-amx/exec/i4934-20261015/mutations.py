#!/usr/bin/env python3
"""mutations.py apply <m1|m2|m3> <worktree>: apply one deliberate break of the issue #4934 fix to the worktree, as an
exact-text replacement that must match exactly once (otherwise exit 2 and change nothing). The worktree's git checkout
restores the file afterwards (mutate-fix.sh). `mutations.py list` prints name, file, expected failing test and a name
fragment that the test binary's failure output must contain.
  m1 rows-through-reader: the split after the loop sends every live token to qk_group (vnni_tokens = all ones), so a
     row-major row is read as VNNI bytes. Expected: t_amx_dispatch_dtype "the software loop scores row-major rows with
     the dotter and VNNI blocks with the reader" fails (m_star differs from the dotter's value).
  m2 completion-twice: note_k_row_saved reports a completion again for a row saved again into a complete, unconverted
     block (the form before this fix). Expected: t_k_vnni_layout "page K blocks turn VNNI at the 16th saved row and
     back when a row is forgotten" fails (its page-state block requires false on the re-save).
  m3 half-queue: convert_pending_k_blocks converts only the first half of a queue of k_convert_parallel_min or more
     blocks. Expected: t_llama_unit SECTION "the forward end converts a queue of many blocks on the pool" fails (a
     block bit stays clear)."""
import os, sys
M = {
    'm1': ('h/tron/models/self_attention.hpp', 't_amx_dispatch_dtype', 'scores row-major rows with the dotter',
           '            const uint64_t vnni_tokens = k_vnni::block_token_mask(vnni_blocks);\n',
           '            const uint64_t vnni_tokens = ~uint64_t{0};  // MUTATION m1: every live token through the reader\n'),
    'm2': ('h/tron/models/kv_cache.hpp', 't_k_vnni_layout', 'blocks turn VNNI at the 16th saved row',
           '    if ((saved.load(std::memory_order_relaxed) & bit) != 0) {\n'
           '      return false;  // saved again: its completion was reported\n'
           '    }\n'
           '    const uint64_t before = saved.fetch_or(bit, std::memory_order_acq_rel);\n',
           '    uint64_t before = saved.load(std::memory_order_relaxed);  // MUTATION m2: a re-saved row reports again\n'
           '    if ((before & bit) == 0) before = saved.fetch_or(bit, std::memory_order_acq_rel);\n'),
    'm3': ('h/tron/models/model.hpp', 't_llama_unit', 'converts a queue of many blocks on the pool',
           '        parallel_for_or_serial(app_pool(), size_t{0}, n_blocks, convert);\n',
           '        parallel_for_or_serial(app_pool(), size_t{0}, n_blocks / 2, convert);  // MUTATION m3: half the queue\n'),
}
cmd = sys.argv[1] if len(sys.argv) > 1 else ''
if cmd == 'list':
    for k, (f, t, frag, _, _) in M.items(): print(f'{k}|{f}|{t}|{frag}')
    sys.exit(0)
if cmd != 'apply' or len(sys.argv) != 4 or sys.argv[2] not in M: print(__doc__); sys.exit(64)
f, t, frag, old, new = M[sys.argv[2]]
p = os.path.join(sys.argv[3], f)
s = open(p).read()
n = s.count(old)
if n != 1: print(f'{sys.argv[2]}: the old text occurs {n} times in {p}, expected 1: nothing changed'); sys.exit(2)
open(p, 'w').write(s.replace(old, new))
print(f'{sys.argv[2]}: applied to {p} (expected failing test: {t}, name fragment: {frag})')
