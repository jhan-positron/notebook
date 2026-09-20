# Lineage inventory: perf-round.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/perf-round-20260830-report.py`
- input: none
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/` (1 preserved); `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/` (2 preserved).
- regenerate: unavailable; generator has no output-path argument and writes the canonical output under Path.home().

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/perf-round-20260830-report.py` | `artifacts/intel-amx/exec/perf-round-20260830-report.py`; preserved | 18221 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/perf-round.txt` | `artifacts/intel-amx/exec/results/perf-round-20260830/perf-round.txt`; preserved | 134951 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260825/perf-round.txt` | `artifacts/intel-amx/exec/results/perf-round-20260825/perf-round.txt`; preserved | 82837 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/perf-round-20260830/perf-round-ext.txt` | `artifacts/intel-amx/exec/results/perf-round-20260830/perf-round-ext.txt`; preserved | 89641 |

Evidence:
- `artifacts/intel-amx/exec/perf-round-20260830-report.py:5-23`
