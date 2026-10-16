---
name: value-suffix-names-shared-files
description: "jhan 2026-10-06 (Wade nit on PR 4557): value-suffixed constants (NAME_<value>) stay in AMX-owned files only; shared files keep their local idiom (bare literal or lower_snake constexpr, masks as literal-plus-named-local); inventory in issue4525/status/code-style-at-shared-files.md"
metadata:
  type: feedback
---

Wade's PR 4557 comment (issuecomment-6021333114, 2026-10-06): value-suffixed names are fine in
the AMX kernel files (amx_attn.cpp, amx_attn_iface.hpp), but shared code should keep local
consistency, e.g. masks spelled `const __m512i hi_16_of_32 = _mm512_set1_epi32(0xffff0000);`
as kv_cache.hpp does. jhan: "I do want to respect consistency, so we will revert the code style
changes at shared files."

**Why:** the C++ guide's named-value rule was applied across every PR file on 2026-09-23. In
files other code owns (v_vnni.hpp, t_llama_unit.cpp, t_heap_v2.cpp) that made moved code differ
from its unchanged siblings. Consistency with the surrounding file wins there.

**How to apply:**
- New constants in AMX-owned files: keep the guide's NAME_<value> form.
- New or moved code in shared files: match the file's existing spelling (literal, lower_snake
  constexpr, or literal-plus-named-local for SIMD masks). Do not add NAME_<value> constants.
- Inventory of the 24 names to revert (6 v_vnni.hpp, 2 t_heap_v2.cpp, 16 t_llama_unit.cpp):
  issue4525/status/code-style-at-shared-files.md. V_PAIR_TOKENS_2: definition MOVES into
  amx_attn.cpp (kernel keeps the name), header and tests use literal 2 (jhan 2026-10-06).
- Term: say "AMX kernel files" (Wade's phrase) vs "shared files"; jhan asked for an alternative
  to "own file" (2026-10-06).
- Main already holds 90 such constants outside AMX files from earlier merged PRs (attn_stats,
  heterogeneous_scheduler_compile, t_attn_stats ...); the revert is scoped to PR 4557 only.

Related: [[cpp-guide-literals-include-bools]], [[wade-pr4557-review-response]].

STATUS 2026-10-06: revert IMPLEMENTED as draft PR #4775 (branch jhan-kv-typed-tensors-plain-names,
425a0e8239, base jhan-kv-typed-tensors); libtron.a disassembly identical, 4 tests green on 3bda;
worktrees ai-runs/tron-i4525-style (claude-box) and /var/tmp/jhan/tron-i4525-style (3bda).
Trap: `bin/lint-notes` with no file args exits 1 (usage); the hook runs `make lint-notes`.
