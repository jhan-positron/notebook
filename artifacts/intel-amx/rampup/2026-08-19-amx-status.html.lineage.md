# Lineage inventory: 2026-08-19-amx-status.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/generators/gen_status_report.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/` (2 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/fused-sweep.html` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p0-baseline.html` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p2-inc1b.html` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p2-inc2.html` (1 proposed preservation).
- regenerate: unavailable; preserved historical generator has no output-path argument and writes status-reports/2026-08-19-amx-status.html; registered current page is the later rampup version. Historical generator does not establish a reproducible build of the later page.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/notebook/artifacts/intel-amx/generators/gen_status_report.py` | `artifacts/intel-amx/generators/gen_status_report.py`; preserved (repo-primary) | 11251 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p2-inc1b.html` | `artifacts/intel-amx/rampup/p2-inc1b.html`; propose preservation | 13015 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p2-inc2.html` | `artifacts/intel-amx/rampup/p2-inc2.html`; propose preservation | 19362 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/fused-sweep.html` | `artifacts/intel-amx/rampup/fused-sweep.html`; propose preservation | 8982 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/p0-baseline.html` | `artifacts/intel-amx/rampup/p0-baseline.html`; propose preservation | 8139 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-suite.txt` | `artifacts/intel-amx/exec/results/t4/t4-suite.txt`; preserved | 52580 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-shapes.txt` | `artifacts/intel-amx/exec/results/t4/t4-shapes.txt`; preserved | 23355 |

Evidence:
- `artifacts/intel-amx/README.md:58-67`
- `artifacts/intel-amx/generators/gen_status_report.py:146-164`
