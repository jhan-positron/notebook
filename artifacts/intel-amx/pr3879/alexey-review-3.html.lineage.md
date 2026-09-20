# Lineage inventory: alexey-review-3.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `/tmp/claude-0/-home-jhan-workspace-intel-AMX/c79e32fa-b9aa-4cba-959e-87718cfed503/scratchpad/pr3879/gen_review3.py` — left behind (missing on 2026-09-20)
- input: Round-authored review data and code snippets from the reviewed tron tree. The known scratch input paths are missing. Insufficient data: the full input list cannot be read from the missing generator.
- input built by: Claude review workflow plus `collect.py` in the session scratch directory. The generator and collection script are missing.
- sources: Known generator/data files: left behind (missing on 2026-09-20). The recorded reviewed commit was `96b5a6c72`. The existing HTML remains the archived review.
- regenerate: unavailable (historical generator and authored inputs are missing). regenerate unverified (missing inputs).

Coverage: The original scratch directory was checked and is absent. A later r4/round3_data.py copy is preserved, but equality to the historical round-3 input was not established. No substitute generator is proposed.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX/c79e32fa-b9aa-4cba-959e-87718cfed503/scratchpad/pr3879/gen_review3.py` | left behind (missing on 2026-09-20) | unavailable |
| input collection builder | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX/c79e32fa-b9aa-4cba-959e-87718cfed503/scratchpad/pr3879/collect.py` | left behind (missing on 2026-09-20) | unavailable |
| authored review input | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX/c79e32fa-b9aa-4cba-959e-87718cfed503/scratchpad/pr3879/round3_data.py` | left behind (missing on 2026-09-20) | unavailable |

Evidence:
- `handoffs/claude_20260824-20260825_pr3879-review-as-alexey-md.md:106`
- `handoffs/claude_20260824-20260825_pr3879-review-as-alexey-md.md:114`
