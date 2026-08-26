# Intel AMX / TRON Decode Artifacts

Preserved copies of the Intel AMX / TRON decode-analysis artifacts generated
in the Codex chat `Follow README instructions`. The canonical copies live in a
mutable local workspace, so these repo copies protect the report and diagram
from workspace cleanup.

Repo copies are mirrors: edit the canonical files first, then refresh these
copies during the next handoff run.

## amx_tron_decode_plan.html

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/intel-amx/amx_tron_decode_plan.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Intel_AMX/from-codex/amx_tron_decode_plan.html
- What it is: self-contained HTML report explaining Intel AMX on Xeon 6,
  TRON/gpt-oss decode pipeline placement, software-attention versus
  Attention-on-FPGA scope, AMX opportunity ranking, testing strategy, and a
  current-head review of https://github.com/positron-ai/tron/pull/2934.
- Related handoff:
  handoffs/codex_2026-07-22-2026-07-23_follow-readme-instructions.md

## transformer_pipeline.svg

- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Intel_AMX/from-codex/transformer_pipeline.svg
- What it is: standalone corrected Archer/TRON forward-pass pipeline diagram.
  It separates CPU software-attention work from FPGA matmul ownership, marks
  AoF as planned scope, labels K/V as host DDR5 DRAM for CPU attention, and
  captures the later spacing/readability fixes.
- Related handoff:
  handoffs/codex_2026-07-22-2026-07-23_follow-readme-instructions.md

## pr2934-perf-20260803/

- Rendered view:
  https://htmlpreview.github.io/?https://raw.githubusercontent.com/jhan-positron/notebook/refs/heads/main/artifacts/intel-amx/pr2934-perf-20260803/pr2934-performance.html
- Canonical:
  DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Intel_AMX/from-codex/pr2934-perf-20260803/
- What it is: compact preserved subset of the Bill PR2934 benchmark:
  fixed-light performance chart, summary CSV, analysis JSON, run-suite script,
  runtron-bin override patch, occupancy-capture script, and source SHA record.
  The raw benchmark result trees and logs remain only at the canonical path.
- Related handoff:
  handoffs/codex_2026-08-02_benchmark-pr-2934-on-3af6.md

## 2026-08-19 preservation batch (claude-alpha handoff run)

Registered by the 2026-08-19 SCOPE:auto handoff run on claude-alpha. Compact
registry format: one bullet per file — repo path, canonical location, what it
is, related handoff. Mirrors follow the canonical->repo rule: edit the
canonical file, refresh here on the next run.
- `exec/lib-guard.sh` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/exec/lib-guard.sh` — CI-lease + campaign-lock guard library for delphi-3bda (v3, dynamic fd). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `exec/QUEUE.md` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/exec/QUEUE.md` — task queue, isolation rules, formulation end-state, rows 1-17 with results. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `rampup/02-tron-decode-amx-plan.html` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/rampup/02-tron-decode-amx-plan.html` — consensus design doc (kernel design, layouts, transpose, precision). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/02-tron-decode-amx-plan.html
- `rampup/2026-08-19-amx-status.html` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` — dated status report with full Gate-5 measured results. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/2026-08-19-amx-status.html
- `rampup/pr-rampup.html` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` — reviewer onboarding doc for PR #3879. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/pr-rampup.html
- `rampup/gptoss-estimate.html` — canonical `claude-alpha:/home/jhan/workspace/intel-AMX/rampup/gptoss-estimate.html` — gpt-oss extension feasibility + payoff estimate. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/gptoss-estimate.html
- `generators/gen_pr_rampup.py` — canonical `claude-alpha:/tmp/claude-0/-home-jhan-workspace-intel-AMX/3a96feab-43b5-493a-97f2-e9a59a459e74/scratchpad/gen_pr_rampup.py` — generator that builds pr-rampup.html (build-time transplant from doc 01). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `generators/gen_pr_walkthrough.py` — canonical `claude-alpha:/tmp/claude-0/-home-jhan-workspace-intel-AMX/3a96feab-43b5-493a-97f2-e9a59a459e74/scratchpad/gen_pr_walkthrough.py` — generator that builds pr-walkthrough.html (9-invariant checklist). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `generators/gen_gptoss_estimate.py` — canonical `claude-alpha:/tmp/claude-0/-home-jhan-workspace-intel-AMX/3a96feab-43b5-493a-97f2-e9a59a459e74/scratchpad/gen_gptoss_estimate.py` — generator that builds gptoss-estimate.html with computed estimate math. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `generators/gen_status_report.py` — canonical `claude-alpha:/tmp/claude-0/-home-jhan-workspace-intel-AMX/3a96feab-43b5-493a-97f2-e9a59a459e74/scratchpad/gen_status_report.py` — generator that builds the daily status report. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)

Note: the four `generators/gen_*.py` canonicals live on a VOLATILE /tmp
scratchpad (session 3a96feab on claude-alpha). Once that scratchpad is
reaped, the repo copies become repo-primary — do not raise the
canonical-missing alarm for them; update this note instead.

## 2026-08-25 archive: doc/intel-amx.md from tron PR #3879

- `intel-amx.md` — canonical: none (repo-primary). The AMX software-attention
  design/measurement write-up that lived in the PR as `doc/intel-amx.md` until
  tron commit a5ef65761; removed from the PR in 234c02bde and kept here.
  Sections: hardware facts (Xeon 6 6962P AMX), throughput reality, numerics,
  where the speedup comes from, measured models, mirror layout, geometry gate.
