# Lineage inventory: gptoss-estimate.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/generators/gen_gptoss_estimate.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` (1 preserved).
- regenerate: unavailable; repo-primary generator has no output-path argument and writes rampup/gptoss-estimate.html relative to cwd. Estimates are arithmetic in the generator; measured comparisons cite the two preserved pages.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/notebook/artifacts/intel-amx/generators/gen_gptoss_estimate.py` | `artifacts/intel-amx/generators/gen_gptoss_estimate.py`; preserved (repo-primary) | 21891 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` | `artifacts/intel-amx/rampup/pr-rampup.html`; preserved | 55209 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` | `artifacts/intel-amx/rampup/2026-08-19-amx-status.html`; preserved | 53116 |

Evidence:
- `artifacts/intel-amx/README.md:66`
- `artifacts/intel-amx/generators/gen_gptoss_estimate.py:330`
