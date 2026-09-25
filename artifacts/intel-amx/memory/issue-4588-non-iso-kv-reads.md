---
name: issue-4588-non-iso-kv-reads
description: "positron-ai/tron issue #4588 (filed 2026-09-24, assignee jhan, label Tech Debt) tracks the three kv_block reads that PR 4587's Note [KV block lifetime] says stay outside ISO C++ (scaled_v_expr, fill_storage_slot, 8-lane V accessors)"
metadata:
  node_type: memory
  type: reference
  originSessionId: d18f08ff-32d9-47e8-84c0-185a34be7295
  modified: 2026-09-24T08:13:19.824Z
---

Issue: https://github.com/positron-ai/tron/issues/4588 "KV cache: three kv_block reads stay outside ISO C++ and
rely on clang (scaled_v_expr, fill_storage_slot, 8-lane V accessors)". Filed 2026-09-24 ~01:10 UTC by Claude on
jhan's request ("Please file a github issue to track the issue as described" + the kv_cache.hpp:1459-1462 comment
at c73e7fb2f9). Label "Tech Debt", assignee jhan-positron, no names in the body (project rule). Body + title saved
at VNNIed-K-in-place/issue4525/status/issue-non-iso-kv-reads.{body.md,title.txt} (28.5 kB, 36-row Words table).

Scope: exactly the three reads the code comment names. The PR 4587 body's other three "Still outside ISO C++"
items (EAGLE x_data casts, intrinsic/AMX tile loads, token_tree.hpp:305-314 discarded placement new) are listed
as "not in this issue" and have no tracker.

Verified facts worth reusing (all at c73e7fb2f9 unless noted):
- Read 1 scaled_v_expr (production, both builds): 16-lane storage is bf16 (v_vnni_tensor::data_), access via
  const bf16s* (__m256i) arithmetic + __m512i loads -> [expr.add]/4,/6 + [basic.lval]/11. On main the types were
  swapped (bf16s storage, same loop text); b951ba9b4c (first commit of #4557) flipped it and added the two
  reinterpret_cast<const bf16s*> (kv_cache.hpp:2326, 2400).
- Read 2 fill_storage_slot (test only, caller book::fill_random, t_llama_unit 1148-1149/2376): one bf16* from
  &block across k then v -> [expr.add]/4, [intro.object]/9. Byte-identical to main:1610-1620.
- Read 3 8-lane V accessors (page::v/v_ptr, copy_storage_slot, page::scaled_v under #else): bf16 access into
  bf16s v[page_size][head_size/chunk_size]; same on main; c73e7fb2f9 removed the same pattern for k only. Callers
  in the 8-lane build are production (model.hpp:2846-2847 V save, full.hpp:2767-2774 v_head_fn -> gof.cpp:213).
- 8-lane build: darwin preset / native on a non-AVX-512 host / -DAVX512=OFF; no CI job; t_llama_unit does not
  compile at 8 lanes (131 errors, none in kv_cache.hpp, 58 in kernels/wide.hpp) at head, 633cb88896 and
  e6c53ba70a (= main for the affected files). Logs: session scratchpad context/lcheck-avx2-*.log (temporary).
- Why it works: clang 19 gives every vector load/store the omnipotent-char TBAA tag (CodeGenTBAA.cpp default case
  "For now"; no __may_alias__ on clang's __m128i/__m256i/__m512i, GCC has it) and lowers the arithmetic to byte
  offsets. Verified on standalone models with the zig-packaged clang 19.1.7 (lcheck env), -O3 -std=gnu++23, no
  -f(no-)strict-aliasing anywhere in the build. Not established: nix-built clang emits the same TBAA.
- Detection: nothing. clang -Wstrict-aliasing groups are empty by design; UBSan has no aliasing check (UBSAN
  CMake option unused by presets/CI); ASan list excludes t_llama_unit; TySan (-fsanitize=type) only from LLVM 20;
  no .clang-tidy.
- Fix precedents: closed draft #4584 (9380012de5) has the const bf16* stepping form for scaled_v_expr
  (2227-2249, 2385-2408) and cast-free 8-lane views; c73e7fb2f9 is the K1 pattern (bf16 k[page_size*head_size]).

2026-09-24 ~01:30 UTC: jhan removes the four-line comment from the code. Issue body rewritten (v5): the issue is now
the record of the three reads, the permalink at c73e7fb2f9 is the only trace of the comment, "keep the code and the
comment" options became "keep the code as is, with this issue as the record". Saved copy updated.

**How to apply:** cite #4588 when the reads are discussed on #4557/#4587; when a fix lands, update the issue, not a
new one. Do not expect the comment in kv_cache.hpp after c73e7fb2f9; line numbers after 1458 shift once it is gone.
Related: [[pr4587-alloc-creates-blocks]], [[issue4525-implementation]], [[no-names-in-github-issues]].
