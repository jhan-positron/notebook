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
- `exec/lib-guard.sh` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/lib-guard.sh` — CI-lease + campaign-lock guard library for delphi-3bda (v3, dynamic fd). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `exec/QUEUE.md` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/QUEUE.md` — task queue, isolation rules, formulation end-state, rows 1-17 with results. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
- `rampup/02-tron-decode-amx-plan.html` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/02-tron-decode-amx-plan.html` — consensus design doc (kernel design, layouts, transpose, precision). (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/02-tron-decode-amx-plan.html
- `rampup/2026-08-19-amx-status.html` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/2026-08-19-amx-status.html` — dated status report with full Gate-5 measured results. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/2026-08-19-amx-status.html
- `rampup/pr-rampup.html` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/pr-rampup.html` — reviewer onboarding doc for PR #3879. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/pr-rampup.html
- `rampup/gptoss-estimate.html` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/gptoss-estimate.html` — gpt-oss extension feasibility + payoff estimate. (handoff: claude_20260816-20260819_list-available-models-with-pal.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/gptoss-estimate.html
- `generators/gen_pr_rampup.py` — canonical `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/gen_pr_rampup.py` — generator that builds pr-rampup.html (build-time transplant from doc 01). Canonical re-pointed 2026-08-30: the original /tmp scratchpad copy was reaped in the 2026-08-27 container move; a newer live copy exists in the workspace, and the repo copy was refreshed from it. (handoff: claude_20260816-20260820_list-available-models-with-pal.md)
- `generators/gen_pr_walkthrough.py` — REPO-PRIMARY (as of 2026-08-30) — generator that builds pr-walkthrough.html (9-invariant checklist). (handoff: claude_20260816-20260820_list-available-models-with-pal.md)
- `generators/gen_gptoss_estimate.py` — REPO-PRIMARY (as of 2026-08-30) — generator that builds gptoss-estimate.html with computed estimate math. (handoff: claude_20260816-20260820_list-available-models-with-pal.md)
- `generators/gen_status_report.py` — REPO-PRIMARY (as of 2026-08-30) — generator that builds the daily status report. (handoff: claude_20260816-20260820_list-available-models-with-pal.md)

Note (updated 2026-08-30, per user decision): the /tmp scratchpad that held
the four `generators/gen_*.py` canonicals was reaped in the 2026-08-27
container move. `gen_pr_rampup.py` was re-pointed to its surviving workspace
copy (above); the other three are now REPO-PRIMARY — edit them here, no
canonical-missing alarm applies.

## 2026-08-25 archive: doc/intel-amx.md from tron PR #3879

- `intel-amx.md` — canonical: none (repo-primary). The AMX software-attention
  design/measurement write-up that lived in the PR as `doc/intel-amx.md` until
  tron commit a5ef65761; removed from the PR in 234c02bde and kept here.
  Sections: hardware facts (Xeon 6 6962P AMX), throughput reality, numerics,
  where the speedup comes from, measured models, mirror layout, geometry gate.

## 2026-08-30 preservation batch (claude-agentsrv handoff run)

Registered by the 2026-08-30 SCOPE:auto handoff run on claude-agentsrv. The
workspace `/home/jhan/workspace/intel-AMX` is NOT a git repository, so these
mirrors are the only git-protected copies. Compact registry format: one bullet
per file or directory — repo path, canonical location, what it is, related
handoff. Mirrors follow the canonical->repo rule. All canonicals below are on
host claude-agentsrv unless stated; `WS` = `/home/jhan/workspace/intel-AMX`.

Design and ramp-up documents:
- `tron-amx-distilled.html` — canonical `WS/tron-amx-distilled.html` — distilled AMX software-attention knowledge page (regenerated by `generators/gen_distilled.py`). (handoffs: claude_20260820-20260823_repeated-crashes-today.md, claude_20260823-20260824_k-transpose-in-fpga-vs-amx-attention.md)
- `generators/gen_distilled.py` — canonical `WS/exec/gen_distilled.py` — generator that builds tron-amx-distilled.html. (handoff: claude_20260823-20260824_k-transpose-in-fpga-vs-amx-attention.md)
- `amx-design.md` — canonical `WS/amx-design.md` — AMX design write-up regenerated alongside the distilled page. (handoff: claude_20260820-20260823_repeated-crashes-today.md)
- `rampup/01-amx-rampup.html` — canonical `WS/rampup/01-amx-rampup.html` — doc-01 AMX ramp-up (B-operand layout, AMX/AVX-512 core sharing sections). (handoff: claude_20260816-20260820_list-available-models-with-pal.md)
- `input-2-ai/add-comments.md` — canonical `WS/input-2-ai/add-comments.md` — user instruction doc for the comment-unpacking sessions. (handoff: claude_20260828-20260829_tron-pr3879-amx-k-mirror-comment.md)

MoE-router option-(c) track (closed 2026-08-24 on a measured negative):
- `router/01-router-amx-rampup.html` — canonical `WS/router/01-router-amx-rampup.html` — router-on-AMX ramp-up doc. (handoff: claude_20260823-20260824_router-amx-md-instructions.md)
- `router/02-option-c-plan.md` — canonical `WS/router/02-option-c-plan.md` — the option-(c) execution plan. (handoff: claude_20260823-20260824_router-amx-md-instructions.md)
- `router/G0-decision-package.md`, `router/P1A-decision-package.md` — canonical `WS/router/` — gate decision packages (G0 gate variables, P1a CPU-router spike verdict). (handoffs: claude_20260823-20260824_router-amx-md-instructions.md, claude_20260823-20260824_option-c-plan-execution-on-delphi-3bda.md)
- `router/bench_router_kernel.cpp` — canonical `WS/router/bench_router_kernel.cpp` — router-kernel microbenchmark source. (handoff: claude_20260823-20260824_option-c-plan-execution-on-delphi-3bda.md)
- `router/p0-trace.html`, `router/p1a-spike.html`, `router/status-report/index.html` — canonical `WS/router/` — P0 trace-marker report, P1a spike report, router status report. (handoff: claude_20260823-20260824_option-c-plan-execution-on-delphi-3bda.md)
- `exec/results/router/{G0-preregistration.md,P1A-preregistration.md,p0b-microbench.txt,sol-deviation-review.md,sol-p1a-review.md,ingested_gpt_oss_20b.hpp.pristine}` — canonical `WS/exec/results/router/` — preregistrations, microbench summary, Sol reviews, pristine model header. Bulk per-run result texts stay at the canonical path only. (handoff: claude_20260823-20260824_option-c-plan-execution-on-delphi-3bda.md)

PR #3879 review record (https://github.com/positron-ai/tron/pull/3879):
- `pr3879/` — canonical `WS/PR3879/` — the Alexey-persona review rounds (alexey-review*.md/.html), `triage.json` review-decision state, the kv_cache-hpp-1199 and comment-unpack pages, and the two `unpack-*/` evidence directories. (handoffs: claude_20260824-20260825_pr3879-review-as-alexey-md.md, claude_20260825-20260827_pr3879-review-as-alexey.md, claude_20260825_kv-cache-hpp-mirror-eagle-view-review-comment.md, claude_20260828-20260829_tron-pr3879-amx-k-mirror-comment.md)
- `pr3879-codex/{claude-report.md,verify-codex-p1.html}` — canonical `WS/PR3879-codex/` — verification of codex's Q-scalar finding and the fix report. (handoff: claude_20260827-20260829_pr3879-codex-tron-amx-numerics-regression-test.md)
- `exec/review-pipeline/` — canonical `WS/exec/review-pipeline/` — review-round generators (gen_review4/5/6.py), per-round inputs r4/r5/r6, README. (handoffs: claude_20260824-20260825_pr3879-review-as-alexey-md.md, claude_20260825-20260827_pr3879-review-as-alexey.md)
- `reviewers/alexey.md` — canonical `claude-agentsrv:/home/jhan/workspace/ai-runs/reviewers/alexey.md` — reviewer-persona spec distilled from Alexey Radul's 2024-2026 review corpus (1,132 lines, 120 verbatim-verified quotes). (handoff: claude_20260824_alexey-pr-review-patterns.md)

Campaign scripts and key results (delphi-3bda measurement campaigns; bulk
result trees stay on the canonical storage):
- `exec/*.sh`, `exec/*.py`, `exec/*.cpp` — canonical `WS/exec/` — p0/p1/p2/p3/r0/optA campaign and analysis scripts, lease tools, `bench_amx_overhead.cpp`, `bench_scatter.cpp`, report generators. (handoffs: claude_20260824-20260825_tron-amx-pr3879-review-suggestions.md, claude_20260827-20260829_pr3879-codex-tron-amx-numerics-regression-test.md, claude_20260829-20260830_definitive-decode-md-brainstorm.md, claude_20260820-20260823_repeated-crashes-today.md)
- `exec/results/amx-overhead-20260821.txt` — canonical `WS/exec/results/amx-overhead-20260821.txt` — AMX runtime-overhead measurement summary (for Bill). (handoff: claude_20260820-20260823_repeated-crashes-today.md)
- `exec/results/bench-scatter-20260824.txt` — canonical `WS/exec/results/bench-scatter-20260824.txt` — scatter-store microbench summary. (handoff: claude_20260824-20260825_tron-amx-pr3879-review-suggestions.md)
- `exec/results/ci-models/mixtral-ab.txt` — canonical `WS/exec/results/ci-models/mixtral-ab.txt` — mixtral-8x7b kill-switch A/B results (QUEUE.md row 18). (handoff: claude_20260820-20260823_repeated-crashes-today.md)
- `exec/results/perf-round-20260825/perf-round.{txt,html}` — canonical `WS/exec/results/perf-round-20260825/` — 48/48 perf-round summary after review-feedback commits. (handoff: claude_20260824-20260825_tron-amx-pr3879-review-suggestions.md)
- `exec/results/slot1/fused-sweep-v2.txt` — canonical `WS/exec/results/slot1/fused-sweep-v2.txt` — fused-kernel sweep record (sole surviving benchmark record for that sweep). (handoff: claude_20260828-20260829_tron-pr3879-amx-k-mirror-comment.md)
