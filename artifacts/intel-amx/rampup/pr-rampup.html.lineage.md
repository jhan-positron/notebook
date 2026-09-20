# Lineage inventory: pr-rampup.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/generators/gen_pr_rampup.py`
- input: `artifacts/intel-amx/rampup/01-amx-rampup.html`
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/01-amx-rampup.html` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` (1 preserved).
- regenerate: unavailable; generator has no output-path argument and writes rampup/pr-rampup.html relative to cwd.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/gen_pr_rampup.py` | `artifacts/intel-amx/generators/gen_pr_rampup.py`; preserved | 38851 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/01-amx-rampup.html` | `artifacts/intel-amx/rampup/01-amx-rampup.html`; preserved | 77929 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` | `artifacts/intel-amx/rampup/2026-08-19-amx-status.html`; preserved | 53116 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-suite.txt` | `artifacts/intel-amx/exec/results/t4/t4-suite.txt`; preserved | 52580 |

Evidence:
- `artifacts/intel-amx/README.md:64`
- `artifacts/intel-amx/generators/gen_pr_rampup.py:144,572`
