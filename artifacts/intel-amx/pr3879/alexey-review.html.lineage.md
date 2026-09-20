# Lineage inventory: alexey-review.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/review-pipeline/gen_review6.py`
- input: `artifacts/intel-amx/exec/review-pipeline/r6/round5_comments.json`, `artifacts/intel-amx/exec/review-pipeline/r6/status.json`, `artifacts/intel-amx/exec/review-pipeline/r6/carry.json`, `artifacts/intel-amx/exec/review-pipeline/r6/round6_data.py`, `artifacts/intel-amx/pr3879/triage.json`
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r6/` (4 preserved).
- regenerate: unavailable; generator has no output-path argument and requires a clean live tron-amx worktree at 3fa11d911cbb3741db9d94c9953c3b51b53f740f. Code snippets already in Git are not mirrored.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/gen_review6.py` | `artifacts/intel-amx/exec/review-pipeline/gen_review6.py`; preserved | 39211 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r6/round5_comments.json` | `artifacts/intel-amx/exec/review-pipeline/r6/round5_comments.json`; preserved | 71966 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r6/status.json` | `artifacts/intel-amx/exec/review-pipeline/r6/status.json`; preserved | 88724 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r6/carry.json` | `artifacts/intel-amx/exec/review-pipeline/r6/carry.json`; preserved | 20042 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r6/round6_data.py` | `artifacts/intel-amx/exec/review-pipeline/r6/round6_data.py`; preserved | 36486 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/triage.json` | `artifacts/intel-amx/pr3879/triage.json`; preserved | 9304 |

Evidence:
- `artifacts/intel-amx/exec/review-pipeline/gen_review6.py:2-29,507-529`
