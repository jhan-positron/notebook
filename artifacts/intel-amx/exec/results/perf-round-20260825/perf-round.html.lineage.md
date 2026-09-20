# Lineage inventory: perf-round.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/perf-round-report.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-models/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/` (2 preserved).
- regenerate: unavailable; generator has no output-path argument and writes the canonical output under Path.home().

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/perf-round-report.py` | `artifacts/intel-amx/exec/perf-round-report.py`; preserved | 11187 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/perf-round.txt` | `artifacts/intel-amx/exec/results/perf-round-20260825/perf-round.txt`; preserved | 82837 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-suite.txt` | `artifacts/intel-amx/exec/results/t4/t4-suite.txt`; preserved | 52580 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/t4/t4-shapes.txt` | `artifacts/intel-amx/exec/results/t4/t4-shapes.txt`; preserved | 23355 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/ci-models/mixtral-ab.txt` | `artifacts/intel-amx/exec/results/ci-models/mixtral-ab.txt`; preserved | 45094 |

Evidence:
- `artifacts/intel-amx/exec/perf-round-report.py:5-23`
