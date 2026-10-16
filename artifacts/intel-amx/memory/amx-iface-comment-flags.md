---
name: amx-iface-comment-flags
description: "2026-08-27 verified inaccuracies in amx_attn_iface.hpp notes (numerics contract + Note [Mirror orientation]) and the benchmark-record facts behind \"1250 vs 686\"; unpack page in scratch/out"
metadata: 
  node_type: memory
  type: project
  originSessionId: 66af9ece-93ab-4d58-bf40-c2d27863bbe0
  modified: 2026-08-27T20:02:33.614Z
---

Verified 2026-08-27 while unpacking two comment blocks in
~/workspace/tron-amx/h/tron/kernels/amx_attn_iface.hpp (branch jhan-amx-p0):

- Numerics contract (lines 38-47): "bit-parity with AVX" over-promises - a truncating
  P->bf16 variant removes only the rounding-mode delta; fp32 add-order delta stays (PV and
  the QK scores feeding P). "RNE is kept deliberately" has no recorded reason
  (intel-AMX/amx-design.md decision D3 still "planned"). The caller's QK dotter is
  dotter<bf16,128> (VDPBF16PS, dotter.hpp:176-226), NOT the dotter<float,128> widen+fma
  code at :44-133 - both paths hard-wire DAZ/FTZ, so "non-subnormal" is scope, not a
  documented divergence.
- Note [Mirror orientation] (lines 150-169): the "1250 vs 686 ns" record is
  intel-AMX/exec/results/slot1/fused-sweep-v2.txt (header 2026-08-18T18:34Z = 11:34 PDT;
  comment says 2026-08-19, likely the decision date). Bench source src/amx_fused_bench.cpp
  was removed in tron-amx ff7269a9f (recover: git show ff7269a9f^:src/amx_fused_bench.cpp).
  At pages=1 the amx44 column includes a per-page scalar Q pack the amxqk column lacks;
  amortized (pages=512/16384) the gap is 501/494 ns. "anywhere else the arena RAM is
  wasted" is wrong: maybe_allocate_mirror_arena (kv_cache.hpp:1057) returns before
  allocating when amx_attn::available() is false; sentence (275fa89a0d, 08-25) postdates
  the gate (31150553cc, 08-19). Under TRON_AMX_K_MIRROR a null arena falls back to the AVX
  dotter loop, not to qk_canonical_128x4.
- Intel opt manual 248966-050 s20.15 local text:
  ~/workspace/intel-vs-amd/enable-SNC3/claude-workspace.6.mode-common.1/refs/opt-manual-v1-rev050-248966.txt
  (lines 32752-32784).

**Why:** jhan asked for plain-words unpacks of these notes; the flags are candidate comment
fixes not yet applied. **How to apply:** if asked to edit either note, re-check these facts
against the current tree first, then fix the flagged sentences. Rewrites in the plain
register are in the published page "amx_attn_iface Notes, Unpacked" (2026-08-27).
Related: [[plain-words-comment-register]], [[mirror-naming-convention]].
