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

## 2026-09-04 preservation batch (claude-agentsrv handoff run)

Registered by the 2026-09-04 SCOPE:auto handoff run on claude-agentsrv. Same
rules as the earlier batches: canonical -> repo mirrors, edit the canonical
file first. `WS` = `claude-agentsrv:/home/jhan/workspace/intel-AMX` (shared NFS
home, not a git repository). Repo path -> canonical path.

### PR #3879 pages (group A)

- `pr3879/make-sense-amx-vs-avx.html` -> `WS/PR3879/make-sense-amx-vs-avx.html` — the AMX-vs-AVX decode-boost analysis page (Q1/Q2, seven campaigns, sections 1-7.7)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/make-sense-amx-vs-avx.html
- `pr3879/make-sense-amx-vs-avx/bench-map-report.md` -> `WS/PR3879/make-sense-amx-vs-avx/bench-map-report.md`
- `pr3879/make-sense-amx-vs-avx/draft.md` -> `WS/PR3879/make-sense-amx-vs-avx/draft.md`
- `pr3879/make-sense-amx-vs-avx/figA.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figA.svg`
- `pr3879/make-sense-amx-vs-avx/figB.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figB.svg`
- `pr3879/make-sense-amx-vs-avx/figC.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figC.svg`
- `pr3879/make-sense-amx-vs-avx/figD.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figD.svg`
- `pr3879/make-sense-amx-vs-avx/figE.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figE.svg`
- `pr3879/make-sense-amx-vs-avx/figF.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figF.svg`
- `pr3879/make-sense-amx-vs-avx/figG-single-attn.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figG-single-attn.svg`
- `pr3879/make-sense-amx-vs-avx/figH-single-attn-phases.svg` -> `WS/PR3879/make-sense-amx-vs-avx/figH-single-attn-phases.svg`
- `pr3879/make-sense-amx-vs-avx/review-brief.md` -> `WS/PR3879/make-sense-amx-vs-avx/review-brief.md`
- `pr3879/make-sense-amx-vs-avx/sol-reply.md` -> `WS/PR3879/make-sense-amx-vs-avx/sol-reply.md`
- `pr3879/make-sense-amx-vs-avx/sol-review-campaigns.md` -> `WS/PR3879/make-sense-amx-vs-avx/sol-review-campaigns.md`
- `pr3879/f9b678e.html` -> `WS/PR3879/f9b678e.html` — line-by-line unpack of PR #3879 commit f9b678e5d0 (K mirror arena RAM visibility)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/f9b678e.html
- `pr3879/f9b678e/README.md` -> `WS/PR3879/f9b678e/README.md`
- `pr3879/jeremy_comments.html` -> `WS/PR3879/jeremy_comments.html` — verdicts, measurements and posted replies for Jeremy's two review comments
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/jeremy_comments.html
- `pr3879/jeremy_comments/README.md` -> `WS/PR3879/jeremy_comments/README.md`
- `pr3879/unpack-mirror-write-ok/fig3.svg` -> `WS/PR3879/unpack-mirror-write-ok/fig3.svg` — scope diagram added 2026-08-30 to the mirror_write_ok unpack page
- `pr3879/response-Ben-breaking-up-PR.md` -> `WS/PR3879/response-Ben-breaking-up-PR.md` — response to Ben's request to split PR #3879 (not posted)
- `pr3879/more-testing/test-plan.md` -> `WS/PR3879/more-testing/test-plan.md` — test plan of the more-testing round 1 (nightly CI tests against PR #3879 rinzler)
  (handoffs: claude_20260828-20260901_tron-pr3879-amx-k-mirror-comment.md, claude_20260830-20260831_tron-pr-3879-commit-walkthrough.md, claude_20260904_pr3879-breakup-request-from-ben.md, claude_20260904_input-2-ai-more-testing-md-instructions.md, claude_20260901_single-attention-avx-vs-amx-boost-in-pr3879.md)

### campaign, bench and harness scripts (group B)

- `exec/fence-20260831/run-fallback.sh` -> `WS/exec/fence-20260831/run-fallback.sh`
- `exec/fence-20260831/run-fence.sh` -> `WS/exec/fence-20260831/run-fence.sh`
- `exec/fence-20260831/run-fence2.sh` -> `WS/exec/fence-20260831/run-fence2.sh`
- `exec/fence-20260831/run-fence3.sh` -> `WS/exec/fence-20260831/run-fence3.sh`
- `exec/fence-20260831/run-thp.sh` -> `WS/exec/fence-20260831/run-thp.sh`
- `exec/fence-20260831/extract.py` -> `WS/exec/fence-20260831/extract.py`
- `exec/fence-20260831/extract7605.py` -> `WS/exec/fence-20260831/extract7605.py`
- `exec/fence-20260831/patch-gen-stamps.py` -> `WS/exec/fence-20260831/patch-gen-stamps.py`
- `exec/perfstat-20260831/chain-ps3-fence3.sh` -> `WS/exec/perfstat-20260831/chain-ps3-fence3.sh`
- `exec/perfstat-20260831/run-perfstat.sh` -> `WS/exec/perfstat-20260831/run-perfstat.sh`
- `exec/perfstat-20260831/run-perfstat2.sh` -> `WS/exec/perfstat-20260831/run-perfstat2.sh`
- `exec/perfstat-20260831/run-perfstat3.sh` -> `WS/exec/perfstat-20260831/run-perfstat3.sh`
- `exec/ctxfill-20260901/run-ctxfill.sh` -> `WS/exec/ctxfill-20260901/run-ctxfill.sh`
- `exec/ctxfill-20260901/run-ctxfill2.sh` -> `WS/exec/ctxfill-20260901/run-ctxfill2.sh`
- `exec/more-testing-r1/run_cell.sh` -> `WS/exec/more-testing-r1/run_cell.sh`
- `exec/more-testing-r1/rz.sh` -> `WS/exec/more-testing-r1/rz.sh`
- `exec/more-testing-r1/smoke.sh` -> `WS/exec/more-testing-r1/smoke.sh`
- `exec/more-testing-r1/soak_cell.sh` -> `WS/exec/more-testing-r1/soak_cell.sh`
- `exec/more-testing-r1/ci_reference.py` -> `WS/exec/more-testing-r1/ci_reference.py`
- `exec/more-testing-r1/gen_status.py` -> `WS/exec/more-testing-r1/gen_status.py`
- `exec/more-testing-r1/mmlu_diff.py` -> `WS/exec/more-testing-r1/mmlu_diff.py`
- `exec/more-testing-r1/st_perf.py` -> `WS/exec/more-testing-r1/st_perf.py`
- `exec/dd/dd-campaign-v3.sh` -> `WS/exec/dd/dd-campaign-v3.sh`
- `exec/dd/dd-campaign.sh` -> `WS/exec/dd/dd-campaign.sh`
- `exec/dd/dd-inc1b-check.sh` -> `WS/exec/dd/dd-inc1b-check.sh`
- `exec/dd/dd-phase3-hf.sh` -> `WS/exec/dd/dd-phase3-hf.sh`
- `exec/dd/dd_bin_score.py` -> `WS/exec/dd/dd_bin_score.py`
- `exec/dd/dd_first_divergence.py` -> `WS/exec/dd/dd_first_divergence.py`
- `exec/dd/dd_intermediates.py` -> `WS/exec/dd/dd_intermediates.py`
- `exec/dd/dd_logits_step.py` -> `WS/exec/dd/dd_logits_step.py`
- `exec/dd/dd_report.py` -> `WS/exec/dd/dd_report.py`
- `exec/dd/dd_tokens.py` -> `WS/exec/dd/dd_tokens.py`
- `exec/more-testing-r1/talos_stub/talos.py` -> `WS/exec/more-testing-r1/talos_stub/talos.py`
- `exec/jeremy-measure-20260831.sh` -> `WS/exec/jeremy-measure-20260831.sh`
- `exec/bench_qpack.cpp` -> `WS/exec/bench_qpack.cpp`
- `exec/bench_qk_align.cpp` -> `WS/exec/bench_qk_align.cpp`
- `exec/p2-perf-round-20260830-ext.sh` -> `WS/exec/p2-perf-round-20260830-ext.sh`
- `exec/more-testing-r1.sh` -> `WS/exec/more-testing-r1.sh`
- `exec/more-testing-r1-build.sh` -> `WS/exec/more-testing-r1-build.sh`
- `exec/more-testing-r1-extra.sh` -> `WS/exec/more-testing-r1-extra.sh`
- `exec/more-testing-r1-extra2.sh` -> `WS/exec/more-testing-r1-extra2.sh`
  (handoffs: claude_20260828-20260901_tron-pr3879-amx-k-mirror-comment.md, claude_20260830-20260831_tron-pr-3879-commit-walkthrough.md, claude_20260830_amx-perf-regression-tests-for-pr3879.md, claude_20260904_input-2-ai-more-testing-md-instructions.md, claude_20260829-20260830_definitive-decode-md-brainstorm.md)

### key result texts and reports (group C; bulk logs, JSON layer dumps and record files stay at the canonical path)

- `exec/results/perf-round-20260830/diag-gptoss-mirror.txt` -> `WS/exec/results/perf-round-20260830/diag-gptoss-mirror.txt`
- `exec/results/perf-round-20260830/diag-qwen-mirror.txt` -> `WS/exec/results/perf-round-20260830/diag-qwen-mirror.txt`
- `exec/results/perf-round-20260830/perf-round-ext.txt` -> `WS/exec/results/perf-round-20260830/perf-round-ext.txt`
- `exec/results/perf-round-20260830/perf-round.html` -> `WS/exec/results/perf-round-20260830/perf-round.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/perf-round-20260830/perf-round.html
- `exec/results/perf-round-20260830/perf-round.txt` -> `WS/exec/results/perf-round-20260830/perf-round.txt`
- `exec/results/perf-round-20260830/pr-summary.md` -> `WS/exec/results/perf-round-20260830/pr-summary.md`
- `exec/results/jeremy-measure-20260831/bench-qk-align.txt` -> `WS/exec/results/jeremy-measure-20260831/bench-qk-align.txt`
- `exec/results/jeremy-measure-20260831/bench-qpack.txt` -> `WS/exec/results/jeremy-measure-20260831/bench-qpack.txt`
- `exec/results/jeremy-measure-20260831/counter-qwen-ctx2048-u1.txt` -> `WS/exec/results/jeremy-measure-20260831/counter-qwen-ctx2048-u1.txt`
- `exec/results/jeremy-measure-20260831/counter-qwen-ctx2048-u8.txt` -> `WS/exec/results/jeremy-measure-20260831/counter-qwen-ctx2048-u8.txt`
- `exec/results/jeremy-measure-20260831/counter-qwen-ctx32-u1-OFFGRID.txt` -> `WS/exec/results/jeremy-measure-20260831/counter-qwen-ctx32-u1-OFFGRID.txt`
- `exec/results/jeremy-measure-20260831/counter-qwen-ctx8192-u8.txt` -> `WS/exec/results/jeremy-measure-20260831/counter-qwen-ctx8192-u8.txt`
- `exec/results/jeremy-measure-20260831/counter-summary.txt` -> `WS/exec/results/jeremy-measure-20260831/counter-summary.txt`
- `exec/results/jeremy-measure-20260831/tests-summary.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-summary.txt`
- `exec/results/jeremy-measure-20260831/tests-t_amx_arena_leak.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-t_amx_arena_leak.txt`
- `exec/results/jeremy-measure-20260831/tests-t_amx_dispatch_dtype.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-t_amx_dispatch_dtype.txt`
- `exec/results/jeremy-measure-20260831/tests-t_amx_mirror.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-t_amx_mirror.txt`
- `exec/results/jeremy-measure-20260831/tests-t_amx_numerics.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-t_amx_numerics.txt`
- `exec/results/jeremy-measure-20260831/tests-t_llama_unit.txt` -> `WS/exec/results/jeremy-measure-20260831/tests-t_llama_unit.txt`
- `exec/results/dd/build-record.txt` -> `WS/exec/results/dd/build-record.txt`
- `exec/results/dd/campaign.txt` -> `WS/exec/results/dd/campaign.txt`
- `exec/results/dd/verdict.html` -> `WS/exec/results/dd/verdict.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/dd/verdict.html
- `exec/results/dd/verdict-technical.html` -> `WS/exec/results/dd/verdict-technical.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/dd/verdict-technical.html
- `exec/results/dd/codex-response.html` -> `WS/exec/results/dd/codex-response.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/dd/codex-response.html
  (handoffs: claude_20260830_amx-perf-regression-tests-for-pr3879.md, claude_20260830-20260831_tron-pr-3879-commit-walkthrough.md, claude_20260829-20260830_definitive-decode-md-brainstorm.md)

### one-page primer generators (group D)

- `perf-model-20260903/primer/README.md` -> `WS/perf-model/primer/README.md`
- `perf-model-20260903/primer/a4sim.py` -> `WS/perf-model/primer/a4sim.py`
- `perf-model-20260903/primer/fig-setup.py` -> `WS/perf-model/primer/fig-setup.py`
- `perf-model-20260903/primer/fig-setup.svg` -> `WS/perf-model/primer/fig-setup.svg`
- `perf-model-20260903/primer/fig.py` -> `WS/perf-model/primer/fig.py`
- `perf-model-20260903/primer/fig.svg` -> `WS/perf-model/primer/fig.svg`
- `perf-model-20260903/primer/final.md` -> `WS/perf-model/primer/final.md`
  (handoffs: claude_20260903_notion-generate-primer-doc.md)

### definitive-decode pages (group E)

- `definitive-decode/index.html` -> `WS/definitive-decode/index.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/definitive-decode/index.html
- `definitive-decode/debug-plan.html` -> `WS/definitive-decode/debug-plan.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/definitive-decode/debug-plan.html
- `definitive-decode/token30-results.html` -> `WS/definitive-decode/token30-results.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/definitive-decode/token30-results.html
- `definitive-decode/HANDOFF.md` -> `WS/definitive-decode/HANDOFF.md`
  (handoffs: claude_20260829-20260830_definitive-decode-md-brainstorm.md)

### user-written instruction docs (group F)

- `input-2-ai/code-review.md` -> `WS/input-2-ai/code-review.md`
- `input-2-ai/definitive_decode.md` -> `WS/input-2-ai/definitive_decode.md`
- `input-2-ai/generate-design.md` -> `WS/input-2-ai/generate-design.md`
- `input-2-ai/make-sense-amx-vs-avx.md` -> `WS/input-2-ai/make-sense-amx-vs-avx.md`
- `input-2-ai/more-testing.md` -> `WS/input-2-ai/more-testing.md`
- `input-2-ai/perf-model.md` -> `WS/input-2-ai/perf-model.md`
- `input-2-ai/rampup.md` -> `WS/input-2-ai/rampup.md`
- `input-2-ai/router-amx.md` -> `WS/input-2-ai/router-amx.md`
  (handoffs: claude_20260828-20260901_tron-pr3879-amx-k-mirror-comment.md, claude_20260902-20260903_perf-model-md-instructions.md, claude_20260904_input-2-ai-more-testing-md-instructions.md, claude_20260829-20260830_definitive-decode-md-brainstorm.md, claude_20260823-20260824_router-amx-md-instructions.md, claude_20260816-20260820_list-available-models-with-pal.md)
