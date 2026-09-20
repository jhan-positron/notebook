# Lineage inventory: alexey-review-4.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/review-pipeline/gen_review4.py` (preserved)
- input: `artifacts/intel-amx/exec/review-pipeline/r4/` (preserved authored inputs and collected records). The generator also reads the live reviewed tron worktree.
- input built by: `exec/review-pipeline/r4/build_status.py` combines the review workflow journal with `r4/round3_comments.json`. `r4/round4_data.py` is authored content.
- sources: `exec/review-pipeline/r4/`: preserved authored status, comments, round data, and collected records. Raw review journal/agent transcripts: left behind (provenance). These authored reviews are not deterministic benchmark runs.
- regenerate: unavailable (The generator reads a live tron worktree at d176c88b3 plus an uncommitted document. r4/round4_data.py also uses a missing absolute scratch path. The pipeline README says later response blocks were inserted by hand.). regenerate unverified (fixed output paths and historical live-worktree requirements).

Coverage: The generator reads a live tron worktree at d176c88b3 plus an uncommitted document. r4/round4_data.py also uses a missing absolute scratch path. The pipeline README says later response blocks were inserted by hand.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/gen_review4.py` | `artifacts/intel-amx/exec/review-pipeline/gen_review4.py`; preserved | 24004 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/build_status.py` | `artifacts/intel-amx/exec/review-pipeline/r4/build_status.py`; preserved | 2639 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/changed_items.json` | `artifacts/intel-amx/exec/review-pipeline/r4/changed_items.json`; preserved | 10909 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/delta.diff` | `artifacts/intel-amx/exec/review-pipeline/r4/delta.diff`; preserved | 9008 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/round3_comments.json` | `artifacts/intel-amx/exec/review-pipeline/r4/round3_comments.json`; preserved | 53220 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/round3_data.py` | `artifacts/intel-amx/exec/review-pipeline/r4/round3_data.py`; preserved | 32723 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/round4_data.py` | `artifacts/intel-amx/exec/review-pipeline/r4/round4_data.py`; preserved | 12548 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/status.json` | `artifacts/intel-amx/exec/review-pipeline/r4/status.json`; preserved | 27079 |
| authored review input, collected code, or review verification record | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/workflow_out.json` | `artifacts/intel-amx/exec/review-pipeline/r4/workflow_out.json`; preserved | 88107 |
| source review workflow journal | `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/5827c364-b93e-4e5c-aa49-89cb6addf5a4/subagents/workflows/wf_06ebd45f-af6/journal.jsonl` | left behind (provenance) | 73825 |
| hardcoded dependency path; a relocated copy exists in r4/round3_data.py | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX/5827c364-b93e-4e5c-aa49-89cb6addf5a4/scratchpad/pr3879/r4/round3_data.py` | left behind (missing on 2026-09-20) | unavailable |

Evidence:
- `/home/jhan/workspace/intel-AMX/exec/review-pipeline/gen_review4.py:11`
- `/home/jhan/workspace/intel-AMX/exec/review-pipeline/r4/build_status.py:1`
- `/home/jhan/workspace/intel-AMX/exec/review-pipeline/README.md:23`
