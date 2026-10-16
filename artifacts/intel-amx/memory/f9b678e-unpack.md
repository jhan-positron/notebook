---
name: f9b678e-unpack
description: PR3879 commit f9b678e5d0 (K mirror arena RAM visibility) unpack page + verified facts; nothing in the commit obsolete at head 1d158249e2
metadata: 
  node_type: memory
  type: project
  originSessionId: bb3bc4a6-4892-4bf2-a666-8725f6917ff6
  modified: 2026-08-30T21:46:38.031Z
---

2026-08-30: built PR3879/f9b678e.html (line-by-line plain-English unpack of
commit f9b678e5d0, "K mirror arena: make its RAM visible") against PR head
1d158249e2. Evidence archive: PR3879/f9b678e/ (facts.json, verdicts.json;
119 verdicts: 109 confirmed / 10 partial / 0 refuted).

Durable verified facts:
- No line of f9b678e5d0 was modified by the two later commits; e217f518e0 only
  shifted its t/CMakeLists.txt block 368-375 -> 371-378.
- Comment inaccuracy in the PR (candidate review fix): the comment above
  amx_attn_iface.hpp:182 says k_mirror_arena_live_bytes is "read by the KV
  footprint log line and by the FUSE gauge" - the log line does NOT read it;
  log_kv_footprint keeps its own static total_mirror_bytes (kv_cache.hpp:471-482).
- Pre-existing oddity kept by the commit: last_print_bytes.load(std::memory_order_release)
  at kv_cache.hpp:487 (release is invalid for loads).
- The new leak-test case pins accessor + gauge counter to allocator ground
  truth; the log-line channel is exercised but never asserted (its own comment
  over-claims "the three numbers").
Related: [[amx-iface-comment-flags]], [[amx-tron-softattn-project]].
