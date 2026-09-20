# Lineage inventory: tron-amx-distilled.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/generators/gen_distilled.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/01-amx-rampup.html` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/02-tron-decode-amx-plan.html` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` (1 preserved).
- regenerate: unavailable; generator writes the canonical page unconditionally; no output-path argument

- The generator consumes four authored source pages; their source sets are shared with pr-rampup, the dated AMX status page, and mirror-vs-VNNI-K inventories. Static ISA/code facts are Git or documentation provenance.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/gen_distilled.py` | `artifacts/intel-amx/generators/gen_distilled.py`; preserved | 111222 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/01-amx-rampup.html` | `artifacts/intel-amx/rampup/01-amx-rampup.html`; preserved | 77929 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/02-tron-decode-amx-plan.html` | `artifacts/intel-amx/rampup/02-tron-decode-amx-plan.html`; preserved | 154036 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` | `artifacts/intel-amx/rampup/pr-rampup.html`; preserved | 55209 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` | `artifacts/intel-amx/rampup/2026-08-19-amx-status.html`; preserved | 53116 |

Evidence:
- `artifacts/intel-amx/README.md:940-946`
