# Lineage inventory: single-K.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `artifacts/intel-amx-single-k/single-k-evidence/build_report.py`
- input: `artifacts/intel-amx-single-k/single-k-evidence/report-results.html`
- input built by: none
- sources: `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/` (3 preserved, 2 proposed preservation).
- regenerate: unavailable; build_report.py has no output-path argument and writes the parent single-K.html unconditionally. The report-results.html input is authored. Source archives at pinned Git revisions are excluded as already in Git.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/build_report.py` | `artifacts/intel-amx-single-k/single-k-evidence/build_report.py`; preserved | 41112 |
| input | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/report-results.html` | `artifacts/intel-amx-single-k/single-k-evidence/report-results.html`; preserved | 4512 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/bill_review.py` | `artifacts/intel-amx-single-k/single-k-evidence/bill_review.py`; preserved | 9394 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/single_k_probe.md` | `artifacts/intel-amx-single-k/single-k-evidence/single_k_probe.md`; preserved | 5724 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/single_k_probe.run.log` | `artifacts/intel-amx-single-k/single-k-evidence/single_k_probe.run.log`; propose preservation | 1159 |
| source | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879-codex/single-k-evidence/single_k_probe.sanitizer-run-no-leak.log` | `artifacts/intel-amx-single-k/single-k-evidence/single_k_probe.sanitizer-run-no-leak.log`; propose preservation | 715 |

Evidence:
- `artifacts/intel-amx-single-k/single-k-evidence/build_report.py:243-248`
- `artifacts/intel-amx-single-k/single-k-evidence/report-results.html:28`
