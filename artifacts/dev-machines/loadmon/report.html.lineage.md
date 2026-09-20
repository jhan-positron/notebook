# Lineage inventory: report.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/dev-machines/loadmon/build_report.py`
- input: `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json`
- input built by: `artifacts/dev-machines/loadmon/analyze.py`
- sources: `claude-agentsrv:/home/jhan/workspace/random/loadmon/alpha.csv` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/random/loadmon/sw-dev-01.csv` (1 proposed preservation).
- regenerate: unavailable; build_report.py has no output-path argument and unconditionally writes a session scratchpad path as well as report.html.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/random/loadmon/build_report.py` | `artifacts/dev-machines/loadmon/build_report.py`; preserved | 29433 |
| input builder | `claude-agentsrv:/home/jhan/workspace/random/loadmon/analyze.py` | `artifacts/dev-machines/loadmon/analyze.py`; preserved | 3542 |
| input | `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json` | `artifacts/dev-machines/loadmon/summary.json`; propose preservation | 80188 |
| source | `claude-agentsrv:/home/jhan/workspace/random/loadmon/alpha.csv` | `artifacts/dev-machines/loadmon/alpha.csv`; propose preservation | 25886 |
| source | `claude-agentsrv:/home/jhan/workspace/random/loadmon/sw-dev-01.csv` | `artifacts/dev-machines/loadmon/sw-dev-01.csv`; propose preservation | 28756 |

Evidence:
- `artifacts/dev-machines/README.md:8-11`
- `artifacts/dev-machines/loadmon/build_report.py:369-370`
