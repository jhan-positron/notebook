# Lineage inventory: Saturday-llama-3.1-8b.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx/exec/l8b-levers-20260919/gen_report.py`
- input: `artifacts/intel-amx/exec/results/l8b-levers-20260919/summary.json`
- input built by: `artifacts/intel-amx/exec/l8b-levers-20260919/analyze.py`
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/` (13 preserved).
- regenerate: `python3 artifacts/intel-amx/exec/l8b-levers-20260919/gen_report.py artifacts/intel-amx/exec/results/l8b-levers-20260919 <OUT>`; verified 2026-09-20; identical after removing renderer comment, replacing the generated timestamp, and normalizing the printed input-directory path Scratch preparation preview verified 2026-09-20; normalizations: renderer comment, Generated timestamp, printed input directory.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/gen_report.py` | `artifacts/intel-amx/exec/l8b-levers-20260919/gen_report.py`; preserved | 39720 |
| input builder | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/l8b-levers-20260919/analyze.py` | `artifacts/intel-amx/exec/l8b-levers-20260919/analyze.py`; preserved | 14874 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/summary.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/summary.json`; preserved | 46444 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass2/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass2/perf.json`; preserved | 2849788 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass3/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass3/perf.json`; preserved | 2848955 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass1/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass1/perf.json`; preserved | 2848736 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass2/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass2/perf.json`; preserved | 2848611 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/base-pass3/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/base-pass3/perf.json`; preserved | 2848618 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/canon-pass1/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/canon-pass1/perf.json`; preserved | 2848602 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/check-mode/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/check-mode/perf.json`; preserved | 13349 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/check-32u-p8192/perf.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/check-32u-p8192/perf.json`; preserved | 809113 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/prompt-check/run1.json` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/prompt-check/run1.json`; preserved | 141193 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/outcome.txt` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/outcome.txt`; preserved | 92 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/status-history.log` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/status-history.log`; preserved | 13176 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919/configs-used.txt` | `artifacts/intel-amx/exec/results/l8b-levers-20260919/configs-used.txt`; preserved | 76 |

Evidence:
- `handoffs/claude_20260919_status-saturday-plan-md-post-ci-actions.md:98-104`
