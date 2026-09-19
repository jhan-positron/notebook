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

## 2026-09-11 archive: doc/amx_software_attention.md from tron PR #3879

- `amx_software_attention.md` — canonical: none (repo-primary). The AMX
  software-attention page that lived in PR #3879 as
  `doc/amx_software_attention.md` until tron commit 4290402491; removed from
  the PR in 47f6f2dceb at Ben's request (TRON environment variables go into one
  document, tron issue #4338) and kept here with a provenance note.
  Sections: what it is, build configuration, runtime disable contract
  (`TRON_AMX_DISABLE`), continuous integration, tests, measurements.

## Codex handoff preservation — 2026-09-11

Canonical files remain authoritative. Refresh canonical → mirror; do not hand-edit mirrors. This batch is related to [codex_20260909_resolve-tron-issue-4303.md](../../handoffs/codex_20260909_resolve-tron-issue-4303.md), [codex_20260911_check-amx-ci-after-pr3879.md](../../handoffs/codex_20260911_check-amx-ci-after-pr3879.md), [codex_20260911_follow-handoff-generation-prompt.md](../../handoffs/codex_20260911_follow-handoff-generation-prompt.md).

| Preserved file | Canonical location | Purpose / related handoff |
|---|---|---|
| [pr3879/page-share-fuse/IMPLEMENTATION.md](pr3879/page-share-fuse/IMPLEMENTATION.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR0-FUSE/IMPLEMENTATION.md` | Implementation decisions and exact completed/pending validation for uncommitted FUSE change Related: [codex_20260909_resolve-tron-issue-4303.md](../../handoffs/codex_20260909_resolve-tron-issue-4303.md). |
| [pr3879/page-share-fuse/issue-4303.patch](pr3879/page-share-fuse/issue-4303.patch) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR0-FUSE/issue-4303.patch` | Portable complete implementation diff; code remained uncommitted in a mutable clone Related: [codex_20260909_resolve-tron-issue-4303.md](../../handoffs/codex_20260909_resolve-tron-issue-4303.md). |
| [pr3879/page-share-fuse/validation/build-focused-test.sh](pr3879/page-share-fuse/validation/build-focused-test.sh) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR0-FUSE/validation/build-focused-test.sh` | Exact focused real-code validation recipe with cached dependency locations Related: [codex_20260909_resolve-tron-issue-4303.md](../../handoffs/codex_20260909_resolve-tron-issue-4303.md). |
| [pr3879/PR1/Hannah-AMX-CI-codex.md](pr3879/PR1/Hannah-AMX-CI-codex.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/Hannah-AMX-CI-codex.md` | New detailed cross-repository nightly AMX implementation checklist Related: [codex_20260911_check-amx-ci-after-pr3879.md](../../handoffs/codex_20260911_check-amx-ci-after-pr3879.md). |
| [pr3879/PR1/Hannah-AMX-CI.html](pr3879/PR1/Hannah-AMX-CI.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/Hannah-AMX-CI.html` | Pre-existing detailed CI/build/runner analysis required by the checklist Related: [codex_20260911_check-amx-ci-after-pr3879.md](../../handoffs/codex_20260911_check-amx-ci-after-pr3879.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/Hannah-AMX-CI.html). |
| [pr3879/PR1/Friday-morning-CI-results.html](pr3879/PR1/Friday-morning-CI-results.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/Friday-morning-CI-results.html` | Pre-existing Qwen measurement and CI interpretation report Related: [codex_20260911_check-amx-ci-after-pr3879.md](../../handoffs/codex_20260911_check-amx-ci-after-pr3879.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/Friday-morning-CI-results.html). |
| [exec/more-testing-r1/resultlib.py](exec/more-testing-r1/resultlib.py) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/more-testing-r1/resultlib.py` | Required shared result parser imported by the refreshed gen_status.py. Related: [codex_20260911_follow-handoff-generation-prompt.md](../../handoffs/codex_20260911_follow-handoff-generation-prompt.md). |


## 2026-09-11 preservation batch (claude-agentsrv handoff run)

Registered by the 2026-09-11 SCOPE:auto handoff run on claude-agentsrv. Same
rules as the earlier batches: canonical -> repo mirrors, edit the canonical
file first. `WS` = `claude-agentsrv:/home/jhan/workspace/intel-AMX` (shared NFS
home, not a git repository). Repo path -> canonical path. Mirrors of
`WS/PR3879/new-PRs/PR0|PR0b|PR1/...` live under `pr3879/PR0|PR0b|PR1/...`
(the layout the 2026-09-11 Codex batch above started); the top-level
`new-PRs/*.md|html` planning docs live under `pr3879/new-PRs/`.

### split planning docs (group A)

- `pr3879/breakup-PR3879.html` -> `WS/PR3879/breakup-PR3879.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/breakup-PR3879.html
- `input-2-ai/breakup-PR3879.md` -> `WS/input-2-ai/breakup-PR3879.md`
- `pr3879/new-PRs/handoff-Saturday.md` -> `WS/PR3879/new-PRs/handoff-Saturday.md`
- `pr3879/new-PRs/handoff-Sunday.md` -> `WS/PR3879/new-PRs/handoff-Sunday.md`
- `pr3879/new-PRs/Monday-handoff.md` -> `WS/PR3879/new-PRs/Monday-handoff.md`
- `pr3879/new-PRs/report-20260906.md` -> `WS/PR3879/new-PRs/report-20260906.md`
- `pr3879/new-PRs/report-20260906-figures/fig1-timeline.svg` -> `WS/PR3879/new-PRs/report-20260906-figures/fig1-timeline.svg`
- `pr3879/new-PRs/report-20260906-figures/fig2-bench.svg` -> `WS/PR3879/new-PRs/report-20260906-figures/fig2-bench.svg`
- `pr3879/new-PRs/report-20260906-figures/fig3-branches.svg` -> `WS/PR3879/new-PRs/report-20260906-figures/fig3-branches.svg`
- `pr3879/new-PRs/Tuesday-plan.html` -> `WS/PR3879/new-PRs/Tuesday-plan.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/new-PRs/Tuesday-plan.html
- `pr3879/new-PRs/Tuesday-morning-status.html` -> `WS/PR3879/new-PRs/Tuesday-morning-status.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/new-PRs/Tuesday-morning-status.html
- `pr3879/PR0/pr-body.md` -> `WS/PR3879/new-PRs/PR0/pr-body.md`
- `pr3879/PR0b/pr-body.md` -> `WS/PR3879/new-PRs/PR0b/pr-body.md`
- `pr3879/PR1/pr-body.md` -> `WS/PR3879/new-PRs/PR1/pr-body.md`
- `pr3879/PR1/thread-map.md` -> `WS/PR3879/new-PRs/PR1/thread-map.md`
  (handoffs: claude_20260904_breakup-pr3829-md-instructions.md, claude_20260904-20260905_breakup-pr3879-md-instructions.md, claude_20260905-20260906_handoff-saturday-md-plan-after-ci.md, claude_20260906-20260907_pr3879-sunday-handoff.md, claude_20260907-20260908_post-ci-test-scope-beyond-pr0b.md, claude_20260907_pr-4267-page-share-counters-review.md, claude_20260908-20260909_pr-3879-description-wording.md)

### review and response pages (group B)

- `pr3879/PR-open-comments.html` -> `WS/PR3879/PR-open-comments.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR-open-comments.html
- `pr3879/Bill-claude-review-response.html` -> `WS/PR3879/Bill-claude-review-response.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/Bill-claude-review-response.html
- `pr3879/Bill-claude-review-response/gen.py` -> `WS/PR3879/Bill-claude-review-response/gen.py`
- `pr3879/Bill-claude-review-response/apply_claimcheck.py` -> `WS/PR3879/Bill-claude-review-response/apply_claimcheck.py`
- `pr3879/Bill-claude-review-response/apply_update_0911.py` -> `WS/PR3879/Bill-claude-review-response/apply_update_0911.py`
- `pr3879/Bill-claude-review-response/build_f10_extra.py` -> `WS/PR3879/Bill-claude-review-response/build_f10_extra.py`
- `pr3879/Bill-claude-review-response/build_data.py` -> `WS/PR3879/Bill-claude-review-response/build_data.py`
- `pr3879/Bill-claude-review-response/f10_extra.html` -> `WS/PR3879/Bill-claude-review-response/f10_extra.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/Bill-claude-review-response/f10_extra.html
- `pr3879/Bill-claude-review-response/issue-finding10-body.md` -> `WS/PR3879/Bill-claude-review-response/issue-finding10-body.md`
- `pr3879/PR0/Monday-report.html` -> `WS/PR3879/new-PRs/PR0/Monday-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR0/Monday-report.html
- `pr3879/PR0/respond-2-Wade-PR0.html` -> `WS/PR3879/new-PRs/PR0/respond-2-Wade-PR0.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR0/respond-2-Wade-PR0.html
- `pr3879/PR0/codex-benchmark-artifact.html` -> `WS/PR3879/new-PRs/PR0/codex-benchmark-artifact.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR0/codex-benchmark-artifact.html
- `pr3879/PR0/wade-fuse-question-20260909.md` -> `WS/PR3879/new-PRs/PR0/wade-fuse-question-20260909.md`
- `pr3879/PR0/issue-4303-body.md` -> `WS/PR3879/new-PRs/PR0/issue-4303-body.md`
- `pr3879/PR0b/ub-guard.html` -> `WS/PR3879/new-PRs/PR0b/ub-guard.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR0b/ub-guard.html
- `pr3879/PR0b/wade-reply.md` -> `WS/PR3879/new-PRs/PR0b/wade-reply.md`
- `pr3879/PR0b/pr-body.v3-move.md` -> `WS/PR3879/new-PRs/PR0b/pr-body.v3-move.md`
- `pr3879/PR1/try_apply_dense_amx_page.html` -> `WS/PR3879/new-PRs/PR1/try_apply_dense_amx_page.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/try_apply_dense_amx_page.html
- `pr3879/PR1/reviews/self_attention-hpp.html` -> `WS/PR3879/new-PRs/PR1/reviews/self_attention-hpp.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/reviews/self_attention-hpp.html
- `pr3879/PR1/reviews/amx_qpack-2-attn_accum.html` -> `WS/PR3879/new-PRs/PR1/reviews/amx_qpack-2-attn_accum.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/reviews/amx_qpack-2-attn_accum.html
- `pr3879/PR1/reviews/amx_qpack-2-attn_accum.figs.py` -> `WS/PR3879/new-PRs/PR1/reviews/amx_qpack-2-attn_accum.figs.py`
- `pr3879/PR1/reviews/amx_qpack-reply.post.md` -> `WS/PR3879/new-PRs/PR1/reviews/amx_qpack-reply.post.md`
- `pr3879/PR1/reviews/range_hint.html` -> `WS/PR3879/new-PRs/PR1/reviews/range_hint.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/reviews/range_hint.html
- `pr3879/PR1/andoria-AMD-machine-test.md` -> `WS/PR3879/new-PRs/PR1/andoria-AMD-machine-test.md`
  (handoffs: claude_20260907_pr-4267-page-share-counters-review.md, claude_20260908_try-apply-dense-amx-page-walkthrough-diagrams.md, claude_20260909_tron-pr-4267-review-comment.md, claude_20260909_fuse-integration-issue-for-pr-4267.md, claude_20260909_wade-review-comment-on-tron-pr-4265.md, claude_20260910_amx-qpack-vs-attn-accum-in-tron-pr-3879.md, claude_20260910_range-hint-handling-in-tron-pr-3879.md, claude_20260910_pr-3879-open-comment-responses.md, claude_20260910_pr3879-amx-review-findings-response.md, claude_20260911_andoria-09-vs-andoria-06-idle-status.md)

### campaign and tool scripts (group C)

- `exec/people-check.sh` -> `WS/exec/people-check.sh`
- `exec/split-verify3.sh` -> `WS/exec/split-verify3.sh`
- `exec/syn-check.sh` -> `WS/exec/syn-check.sh`
- `exec/gptoss120b-pr1-half.sh` -> `WS/exec/gptoss120b-pr1-half.sh`
- `exec/wade-exp-20260909.sh` -> `WS/exec/wade-exp-20260909.sh`
- `exec/wade-exp-inner-20260909.sh` -> `WS/exec/wade-exp-inner-20260909.sh`
- `exec/sunday-killer-20260906.sh` -> `WS/exec/sunday-killer-20260906.sh`
- `exec/morning-launch-20260907.sh` -> `WS/exec/morning-launch-20260907.sh`
- `exec/split-relaunch.sh` -> `WS/exec/split-relaunch.sh`
- `exec/split-relaunch3.sh` -> `WS/exec/split-relaunch3.sh`
- `exec/split-relaunch3b.sh` -> `WS/exec/split-relaunch3b.sh`
- `exec/split-relaunch3c.sh` -> `WS/exec/split-relaunch3c.sh`
- `exec/split-relaunch3d.sh` -> `WS/exec/split-relaunch3d.sh`
- `exec/split-relaunch3e.sh` -> `WS/exec/split-relaunch3e.sh`
- `exec/split-tools/make_trees.py` -> `WS/exec/split-tools/make_trees.py`
- `exec/split-tools/subtract.py` -> `WS/exec/split-tools/subtract.py`
- `exec/split-tools/threadmap_lines.sh` -> `WS/exec/split-tools/threadmap_lines.sh`
- `exec/split-tools/chain_results.sh` -> `WS/exec/split-tools/chain_results.sh`
- `exec/split-tools/make_topical.sh` -> `WS/exec/split-tools/make_topical.sh`
- `exec/g1-20260908/launch.sh` -> `WS/exec/g1-20260908/launch.sh`
- `exec/g1-20260908/g1-campaign.sh` -> `WS/exec/g1-20260908/g1-campaign.sh`
- `exec/g1-20260908/rz.sh` -> `WS/exec/g1-20260908/rz.sh`
- `exec/g1-20260908/g1-summary.py` -> `WS/exec/g1-20260908/g1-summary.py`
- `exec/g1-20260908/g3-lite.sh` -> `WS/exec/g1-20260908/g3-lite.sh`
- `exec/g1-20260908/g3-lite-waiter.sh` -> `WS/exec/g1-20260908/g3-lite-waiter.sh`
- `exec/p0perf-20260911/campaign.sh` -> `WS/exec/p0perf-20260911/campaign.sh`
- `exec/p0perf-20260911/rz.sh` -> `WS/exec/p0perf-20260911/rz.sh`
- `exec/p0perf-20260911/launch.sh` -> `WS/exec/p0perf-20260911/launch.sh`
- `exec/p0perf-20260911/summarize.py` -> `WS/exec/p0perf-20260911/summarize.py`
- `exec/p0perf-20260911/gen_report.py` -> `WS/exec/p0perf-20260911/gen_report.py`
- `exec/amd-amx-20260911/amxprobe.c` -> `WS/exec/amd-amx-20260911/amxprobe.c`
- `exec/amd-amx-20260911/run-andoria06.sh` -> `WS/exec/amd-amx-20260911/run-andoria06.sh`
- `exec/pr1-rebase-20260911/build-test.sh` -> `WS/exec/pr1-rebase-20260911/build-test.sh`
- `pr3879/PR0b/ub-guard/CLAIMS.md` -> `WS/PR3879/new-PRs/PR0b/ub-guard/CLAIMS.md`
- `pr3879/PR0b/ub-guard/matrix.sh` -> `WS/PR3879/new-PRs/PR0b/ub-guard/matrix.sh`
- `pr3879/PR0b/ub-guard/run5.sh` -> `WS/PR3879/new-PRs/PR0b/ub-guard/run5.sh`
- `pr3879/PR0b/ub-guard/probe3.sh` -> `WS/PR3879/new-PRs/PR0b/ub-guard/probe3.sh`
- `pr3879/PR0b/ub-guard/probe4.sh` -> `WS/PR3879/new-PRs/PR0b/ub-guard/probe4.sh`
- `pr3879/PR0b/ub-guard/probe5.sh` -> `WS/PR3879/new-PRs/PR0b/ub-guard/probe5.sh`
- `pr3879/PR0b/ub-guard/probe.cpp` -> `WS/PR3879/new-PRs/PR0b/ub-guard/probe.cpp`
- `pr3879/PR0b/ub-guard/repro.cpp` -> `WS/PR3879/new-PRs/PR0b/ub-guard/repro.cpp`
- `pr3879/PR0b/ub-guard/t_kv_footprint_memorder.cpp` -> `WS/PR3879/new-PRs/PR0b/ub-guard/t_kv_footprint_memorder.cpp`
  (handoffs: claude_20260904_breakup-pr3829-md-instructions.md, claude_20260905_delphi-3bda-machine-contention-handoff-doc.md, claude_20260906-20260907_pr3879-sunday-handoff.md, claude_20260907-20260908_post-ci-test-scope-beyond-pr0b.md, claude_20260907-20260908_pr0b-vs-pr1-separation.md, claude_20260908-20260909_pr-3879-description-wording.md, claude_20260909_wade-review-comment-on-tron-pr-4265.md, claude_20260910-20260911_amx-perf-test-on-jhan-amx-p0.md, claude_20260911_andoria-09-vs-andoria-06-idle-status.md, claude_20260911_pr3879-merge-conflicts.md)

## 2026-09-13 preservation batch

Same rules as the earlier batches: canonical -> repo mirror, edit the canonical
file first. `WS` = `/home/jhan/workspace/intel-AMX`.

### PR #3879 pages

- `pr3879/baseline-vs-mirror-sketch.html` -> `WS/PR3879/baseline-vs-mirror-sketch.html` — jhan's hand sketch contrasting the baseline (canonical-K) and mirror (K*) AMX attention paths, read step by step against tron 60d66d9c04, with the measured costs (single-attention phases, TTFT, arena RAM) and a corrected redraw; pure-ASCII HTML (entities) after the artifact-host mojibake
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/baseline-vs-mirror-sketch.html

## 2026-09-14 preservation batch

Same rules as the earlier batches: canonical -> repo mirror, edit the canonical
file first. `WS` = `/home/jhan/workspace/intel-AMX`.

### PR #3879 pages

- `pr3879/baseline-vs-mirror-sketch.html` (updated) -> `WS/PR3879/baseline-vs-mirror-sketch.html` — the section 2 side-by-side diagram now lists the matrix shapes in every box (Q group, the 4 Q_packed panels, K and K* tiles, S^T and S, s_pages, P, V_page, O, v*/s*/m*, out) plus a legend paragraph; every shape line verified by two adversarial agent rounds against tron 60d66d9c04 (v* is bf16 in memory and truncated to bf16 on store, Q_packed is 4 panels of 1 KB, not a 16 x 128 matrix)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/baseline-vs-mirror-sketch.html

## 2026-09-15 preservation batch

- `amx_software_attention.md` (updated) — canonical: none (repo-primary). New addendum
  for tron PR #4424 (K stored in the VNNI layout): the build option `TRON_K_VNNI`
  (default OFF, requires `TRON_AMX_DISPATCH`), the amended runtime disable contract
  (`TRON_AMX_DISABLE=1` keeps the VNNI layout and runs the AVX-512 reader; no rollback to
  row-major numerics), the numerics tests, the CI lane flags, a verification recipe and
  the prompt-1024 / 8192 measurements. The PR #3879 body of the page is unchanged.


## Codex handoff preservation — 2026-09-18

Canonical files remain authoritative. This batch preserves authored documents, scripts, and compact audit results. Raw logs, source archives, binaries, and browser captures stay at their original locations.

HTML pages retain their canonical workspace evidence links. The mirrors preserve the authored pages but do not make the entire source and raw-data tree available offline. Historical installers require their recorded preconditions and paths.

| Preserved file | Canonical location | Purpose and related handoff |
|---|---|---|
| [rampup/operand-B.html](rampup/operand-B.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/operand-B.html` | Interactive operand layout tutorial. Related: [codex_20260912-20260913_illustrate-amx-operand-b.md](../../handoffs/codex_20260912-20260913_illustrate-amx-operand-b.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/rampup/operand-B.html). |
| [pr3879/amx-mirror-corrected-sketch.html](pr3879/amx-mirror-corrected-sketch.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/amx-mirror-corrected-sketch.html` | Corrected attention sketch. Related: [codex_20260913_review-amx-and-mirror-sketch.md](../../handoffs/codex_20260913_review-amx-and-mirror-sketch.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/amx-mirror-corrected-sketch.html). |
| [VNNIed-K-in-place/input-2-ai/to-codex.md](VNNIed-K-in-place/input-2-ai/to-codex.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/input-2-ai/to-codex.md` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/design/codex-VNNIed-K.html](VNNIed-K-in-place/design/codex-VNNIed-K.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/design/codex-VNNIed-K.html` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/design/codex-VNNIed-K.html). |
| [VNNIed-K-in-place/design/codex-review-claude.html](VNNIed-K-in-place/design/codex-review-claude.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/design/codex-review-claude.html` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/design/codex-review-claude.html). |
| [VNNIed-K-in-place/design/codex-TP2-TP4-analysis.html](VNNIed-K-in-place/design/codex-TP2-TP4-analysis.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/design/codex-TP2-TP4-analysis.html` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/design/codex-TP2-TP4-analysis.html). |
| [VNNIed-K-in-place/design/codex-TTFT-plan-review.html](VNNIed-K-in-place/design/codex-TTFT-plan-review.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/design/codex-TTFT-plan-review.html` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/design/codex-TTFT-plan-review.html). |
| [VNNIed-K-in-place/status/codex-perf-audit.py](VNNIed-K-in-place/status/codex-perf-audit.py) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.py` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-perf-audit.json](VNNIed-K-in-place/status/codex-perf-audit.json) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.json` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-perf-audit.md](VNNIed-K-in-place/status/codex-perf-audit.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-perf-audit.md` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-tp-scaling-data.json](VNNIed-K-in-place/status/codex-tp-scaling-data.json) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-tp-scaling-data.json` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-layout-check.py](VNNIed-K-in-place/status/codex-layout-check.py) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-layout-check.py` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-baseline-audit.md](VNNIed-K-in-place/status/codex-baseline-audit.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-baseline-audit.md` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-bill-source-audit.md](VNNIed-K-in-place/status/codex-bill-source-audit.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-bill-source-audit.md` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-claude-code-audit.md](VNNIed-K-in-place/status/codex-claude-code-audit.md) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-claude-code-audit.md` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-review-evidence/manifest.json](VNNIed-K-in-place/status/codex-review-evidence/manifest.json) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-evidence/manifest.json` | Independent packed-key design, source review, or distilled measurement evidence. Related: [codex_20260913-20260914_follow-input-2-ai-to-codex-md.md](../../handoffs/codex_20260913-20260914_follow-input-2-ai-to-codex-md.md). |
| [VNNIed-K-in-place/status/codex-review-PR4424.html](VNNIed-K-in-place/status/codex-review-PR4424.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-PR4424.html` | Follow-up code-review evidence. Related: [codex_20260915_review-pr4424-code.md](../../handoffs/codex_20260915_review-pr4424-code.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/status/codex-review-PR4424.html). |
| [VNNIed-K-in-place/status/codex-review-PR4424-evidence/checks.json](VNNIed-K-in-place/status/codex-review-PR4424-evidence/checks.json) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-PR4424-evidence/checks.json` | Follow-up code-review evidence. Related: [codex_20260915_review-pr4424-code.md](../../handoffs/codex_20260915_review-pr4424-code.md). |
| [VNNIed-K-in-place/status/codex-review-PR4424-evidence/accepted-geometry.cpp](VNNIed-K-in-place/status/codex-review-PR4424-evidence/accepted-geometry.cpp) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-PR4424-evidence/accepted-geometry.cpp` | Follow-up code-review evidence. Related: [codex_20260915_review-pr4424-code.md](../../handoffs/codex_20260915_review-pr4424-code.md). |
| [VNNIed-K-in-place/status/codex-review-PR4424-evidence/reader-limit.cpp](VNNIed-K-in-place/status/codex-review-PR4424-evidence/reader-limit.cpp) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-PR4424-evidence/reader-limit.cpp` | Follow-up code-review evidence. Related: [codex_20260915_review-pr4424-code.md](../../handoffs/codex_20260915_review-pr4424-code.md). |
| [VNNIed-K-in-place/status/codex-review-PR4424-evidence/pr-metadata.json](VNNIed-K-in-place/status/codex-review-PR4424-evidence/pr-metadata.json) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/codex-review-PR4424-evidence/pr-metadata.json` | Follow-up code-review evidence. Related: [codex_20260915_review-pr4424-code.md](../../handoffs/codex_20260915_review-pr4424-code.md). |
| [VNNIed-K-in-place/initial-review/checks.json](VNNIed-K-in-place/initial-review/checks.json) | `claude-agentsrv:/tmp/codex-pr4424-review/checks.json` | Initial isolated-review evidence; report later overwritten. Related: [codex_20260915_review-pr-4424.md](../../handoffs/codex_20260915_review-pr-4424.md). |
| [VNNIed-K-in-place/initial-review/transpose.cpp](VNNIed-K-in-place/initial-review/transpose.cpp) | `claude-agentsrv:/tmp/codex-pr4424-review/transpose.cpp` | Initial isolated-review evidence; report later overwritten. Related: [codex_20260915_review-pr-4424.md](../../handoffs/codex_20260915_review-pr-4424.md). |
| [VNNIed-K-in-place/codex/design/root-cause-tracing.html](VNNIed-K-in-place/codex/design/root-cause-tracing.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/codex/design/root-cause-tracing.html` | Tracing design or necessary historical comparison report. Related: [codex_20260918_trace-fpga-decode-tps-loss.md](../../handoffs/codex_20260918_trace-fpga-decode-tps-loss.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/codex/design/root-cause-tracing.html). |
| [VNNIed-K-in-place/status/Friday-morning-CI-run-report.html](VNNIed-K-in-place/status/Friday-morning-CI-run-report.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Friday-morning-CI-run-report.html` | Tracing design or necessary historical comparison report. Related: [codex_20260918_trace-fpga-decode-tps-loss.md](../../handoffs/codex_20260918_trace-fpga-decode-tps-loss.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/status/Friday-morning-CI-run-report.html). |
| [VNNIed-K-in-place/status/Wednesday-perf-test.html](VNNIed-K-in-place/status/Wednesday-perf-test.html) | `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Wednesday-perf-test.html` | Tracing design or necessary historical comparison report. Related: [codex_20260918_trace-fpga-decode-tps-loss.md](../../handoffs/codex_20260918_trace-fpga-decode-tps-loss.md). [Rendered view](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/VNNIed-K-in-place/status/Wednesday-perf-test.html). |
