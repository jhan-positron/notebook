---
name: amx-mirror-aware-cache-unpack
description: "2026-08-28 verified facts behind the amx_mirror_aware_cache / create_sequence_cache comment (kv_cache.hpp:1433-1461, PR3879 commit 840106b44a); unpack page + probes archived in PR3879/unpack-amx-mirror-aware-cache*"
metadata: 
  node_type: memory
  type: project
  originSessionId: cbbd0d6f-9d0b-440d-9553-602e42905f72
  modified: 2026-08-28T19:39:38.833Z
---

Unpacked 2026-08-28 for jhan (page: PR3879/unpack-amx-mirror-aware-cache.html, artifact
https://claude.ai/code/artifact/831d8c6e-6808-4c36-9823-aa2f775a801d; claims, 9-agent verdicts and
two g++ probe files in PR3879/unpack-amx-mirror-aware-cache/). Facts verified at tron-amx e217f518e0:

- Only `book` defines try_create / owns a mirror arena in h/ and src/; every production cache_t
  (llama.hpp:188, mock.hpp:110, heterogeneous_kv_cache.hpp, 15 gen plugins) is a book, so the
  3-argument else-branch of create_sequence_cache is compiled but never run in production; the
  only non-book sequence_cache is the test type three_argument_sequence_cache (t_llama_unit.cpp:460).
- The pre-840106b44a "custom cache no longer compiled" was an inference (codex P2), never an
  observed build failure.
- Concept checks call shape only: 4th param int/double/bool& pass, bool&&/std::string fail;
  same_as is exact (shared_ptr<Derived>, shared_ptr<T>&, const shared_ptr<T>, unique_ptr<T> fail);
  noexcept not checked. Maintenance trap: a default on the 4-arg book::try_create's last parameter
  makes the 3-arg call ambiguous and sequence_cache<book> false (probe X4).
- "every mirror consumer null-checks" = every dereference site (fill_storage_slot 1368,
  set_k_mirror 1632, copy_storage_slot 1969, self_attention.hpp:1574); mirror() 1321 and
  k_mirror_data() 1618 forward nullptr unchecked by design; save_k (model.hpp:2796-2800) relies
  on set_k_mirror. Note [K mirror parallel arena] is kv_cache.hpp:555-591 and its own overcommit
  caveat (577-580) qualifies "never fatal".
- Four gates before an arena exists: compile-time amx_mirror_eligible (bf16 + head 128 + kv_mul 4),
  runtime amx_attn::available(), nothrow new, and TRON_AMX_K_MIRROR (CMake default OFF; flag then
  [[maybe_unused]]). EAGLE speculator schedulers inherit the main root's bool (full.hpp:1448-1450).

The comment was replaced on 2026-08-28 by a 7-line "why"-only question-form version (tron
1d158249e2, pushed to jhan-amx-p0); jhan rejected describing what the code does in the comment.

**Why:** if a reviewer questions the new comment, these are the checked facts behind it; plain rewording re-generalized 5 of my 20 first-draft
claims (C9, C10, C11, C12, L7 in the verdicts file). **How to apply:** re-check line numbers
against the current tree before quoting; reuse the probe files for any concept change. Related:
[[plain-words-comment-register]], [[amx-iface-comment-flags]], [[codex-review-loop]].
