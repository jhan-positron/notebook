## Short version

PR #5015 makes the AMX attention kernels serve kv_mul 16 (Muse Glimmer 30B) next to kv_mul 4 (llama-3.1-8b) through a `group_heads` template parameter, but the namespace and the kernel names still say "4 query heads per KV head" (`amx_attn_h128g4`, `pack_q_group_128x4`, `qk_rowmajor_128x4`, `weights_times_v_128x4`). This issue tracks the follow-up PR that renames them. That PR has one requirement beyond the rename: more shapes will follow, so it must look for implementation changes that make the code change for a new shape as small as possible.

## Words used here

- AMX = the Intel tile-matrix instructions. The AMX attention kernel scores one dense 64-token KV page per call (`src/amx_attn.cpp`, interface `h/tron/amx_attn_iface.hpp`).
- kv_mul = query heads per KV head. llama-3.1-8b has 4, Muse Glimmer 30B has 16. The kernels take it as the template parameter `group_heads`.
- shape = head size x kv_mul. The kernels serve head size 128 with kv_mul 4 and 16 after PR #5015. A "new shape" is another kv_mul at head size 128, or later another head size.
- `group_heads_ok` = the compile-time gate that lists the served kv_mul values; `shape_ok` = the run-time gate (head size 128 and `group_heads_ok(kv_mul)`).

## Why a separate PR

PR #5015 was written under a minimum-change requirement: keep the names, keep the structure, so that the review stays on the kernel generalization. Renaming was deferred to here on purpose.

## What the follow-up PR does

1. Renames the namespace and the three kernels so that the names describe the shape family (head size 128, `group_heads` as a parameter) instead of one kv_mul value, and updates the header comment that today says the names record the first shape. Call sites, tests and the `Note` comments follow.

2. Requirement: before or with the rename, look for implementation improvements so that adding a shape is a minimal change. Today a new kv_mul touches at least: `group_heads_ok`, the explicit instantiations at the end of `amx_attn.cpp`, the `if constexpr (group_heads == 16)` lanes of the transposing store in the QK kernel, the P-conversion loop of the PV kernel, the `KERNEL_KV_MULS`-style lists in the tests (`t_amx_numerics`, `t_amx_dispatch_dtype`, `t_llama_unit` probes), and the buffer sizing assumptions at the call sites. Candidates to evaluate, not a prescription:
   - one declared list of served group sizes from which the gate, the instantiations and the test shape lists are generated;
   - the transposing store and the P-conversion loop written over `group_heads / 4` lanes instead of per-value branches;
   - call sites that take the geometry object instead of shape constants;
   - a static check that every served size has a numerics test section.
   The PR description states, for a hypothetical third group size, which files and lines would change after the PR (the count is the measure of this requirement).

3. Out of scope: adding a shape, changing kernel performance, changing numerics.

## Acceptance

- Numerics unchanged: `t_amx_numerics`, `t_amx_dispatch_dtype` and `t_llama_unit` pass with AMX on and under the kill switch (`TRON_AMX_DISABLE=1`), and the `<4>` and `<16>` instantiations compile to the same instructions as at the PR #5015 head (disassembly compare after address stripping, the method of PR #5015's "object compare").
- The PR description lists the places a new group size would touch, before and after.
- No throughput change on llama-3.1-8b and Muse Glimmer 30B (same runtron cells as PR #5015, inside the band).

## Related

- PR #5015 (kv_mul 16 support; keeps the old names on purpose).
- Issue #4444 (token divergence between the AMX and AVX paths; unrelated to the names, listed because every kernel PR references it).
