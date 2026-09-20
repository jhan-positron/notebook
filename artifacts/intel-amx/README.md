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
  Lineage labels of `tron-amx-distilled.html` (regenerate: unavailable): see the 2026-09-20 batch below.
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

## 2026-09-18 preservation batch (claude-agentsrv handoff run)

Registered by the 2026-09-18 SCOPE:auto handoff run on claude-agentsrv. Same rules as the earlier batches: canonical -> repo mirrors, edit the canonical file first. `WS` = `claude-agentsrv:/home/jhan/workspace/intel-AMX` (shared NFS home, not a git repository). Repo path -> canonical path. New sub-directory `vnnied-k-in-place/` mirrors `WS/VNNIed-K-in-place/`. `memory/` mirrors Claude Code project memory notes from `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/` (one note from the `-home-jhan-workspace-tron` project). `exec/workflows/` holds two Workflow scripts from session directories under `~/.claude/projects/`.


### campaign, build and generator scripts (exec/)

- `exec/bill-share.sh` -> `WS/exec/bill-share.sh`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)
- `exec/canon-ci-20260918/build-canon.sh` -> `WS/exec/canon-ci-20260918/build-canon.sh`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/campaign.sh` -> `WS/exec/canon-ci-20260918/campaign.sh`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/dut.sh` -> `WS/exec/canon-ci-20260918/dut.sh`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/gen_caveats.py` -> `WS/exec/canon-ci-20260918/gen_caveats.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/gen_ci_shapes.py` -> `WS/exec/canon-ci-20260918/gen_ci_shapes.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/gen_report.py` -> `WS/exec/canon-ci-20260918/gen_report.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/launch.sh` -> `WS/exec/canon-ci-20260918/launch.sh`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/nightly_to_arm.py` -> `WS/exec/canon-ci-20260918/nightly_to_arm.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/st_ci_perf.py` -> `WS/exec/canon-ci-20260918/st_ci_perf.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/canon-ci-20260918/talos_stub/talos.py` -> `WS/exec/canon-ci-20260918/talos_stub/talos.py`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/ci-enable-20260917/amxspin.c` -> `WS/exec/ci-enable-20260917/amxspin.c`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `exec/ci-enable-20260917/runtime-check.sh` -> `WS/exec/ci-enable-20260917/runtime-check.sh`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `exec/ci-mimic-20260918/build-target.sh` -> `WS/exec/ci-mimic-20260918/build-target.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/campaign.sh` -> `WS/exec/ci-mimic-20260918/campaign.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/dut.sh` -> `WS/exec/ci-mimic-20260918/dut.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/gen_report.py` -> `WS/exec/ci-mimic-20260918/gen_report.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/launch.sh` -> `WS/exec/ci-mimic-20260918/launch.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/nightly_to_arm.py` -> `WS/exec/ci-mimic-20260918/nightly_to_arm.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/st_ci_perf.py` -> `WS/exec/ci-mimic-20260918/st_ci_perf.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/talos_stub/talos.py` -> `WS/exec/ci-mimic-20260918/talos_stub/talos.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/ci-mimic-20260918/wait-and-build.sh` -> `WS/exec/ci-mimic-20260918/wait-and-build.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/issue4500-20260918/bench/bench_k_vnni.cpp` -> `WS/exec/issue4500-20260918/bench/bench_k_vnni.cpp`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/bench/run.sh` -> `WS/exec/issue4500-20260918/bench/run.sh`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/campaign.sh` -> `WS/exec/issue4500-20260918/campaign.sh`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/gen_design.py` -> `WS/exec/issue4500-20260918/gen_design.py`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/launch.sh` -> `WS/exec/issue4500-20260918/launch.sh`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/summarize.py` -> `WS/exec/issue4500-20260918/summarize.py`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/issue4500-20260918/trace_analyze.py` -> `WS/exec/issue4500-20260918/trace_analyze.py`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/l8bload-20260918/campaign.sh` -> `WS/exec/l8bload-20260918/campaign.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/l8bload-20260918/gen_report.py` -> `WS/exec/l8bload-20260918/gen_report.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/l8bload-20260918/launch.sh` -> `WS/exec/l8bload-20260918/launch.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/l8bload-20260918/rz.sh` -> `WS/exec/l8bload-20260918/rz.sh`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/l8bload-20260918/summarize.py` -> `WS/exec/l8bload-20260918/summarize.py`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/lib-guard-tests/test-bill-share.sh` -> `WS/exec/lib-guard-tests/test-bill-share.sh`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)
- `exec/lib-guard-tests/test-takeover.sh` -> `WS/exec/lib-guard-tests/test-takeover.sh`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)
- `exec/lib-guard-tests/test-wait-clear.sh` -> `WS/exec/lib-guard-tests/test-wait-clear.sh`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)
- `exec/nightly-amx-check-20260916/gen_page.py` -> `WS/exec/nightly-amx-check-20260916/gen_page.py`
  (handoffs: claude_20260916-20260917_tron-amx-dispatch-in-ci-builds-after-pr3879.md)
- `exec/nightly-amx-check-20260916/slack-reports.tsv` -> `WS/exec/nightly-amx-check-20260916/slack-reports.tsv`
  (handoffs: claude_20260916-20260917_tron-amx-dispatch-in-ci-builds-after-pr3879.md)
- `exec/p0perf-20260913/campaign.sh` -> `WS/exec/p0perf-20260913/campaign.sh`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/p0perf-20260913/combine.py` -> `WS/exec/p0perf-20260913/combine.py`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/p0perf-20260913/gen_report.py` -> `WS/exec/p0perf-20260913/gen_report.py`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/p0perf-20260913/launch.sh` -> `WS/exec/p0perf-20260913/launch.sh`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/p0perf-20260913/rz.sh` -> `WS/exec/p0perf-20260913/rz.sh`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/p0perf-20260913/summarize.py` -> `WS/exec/p0perf-20260913/summarize.py`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/pr1-rebase-20260915/build-test.sh` -> `WS/exec/pr1-rebase-20260915/build-test.sh`
  (handoffs: claude_20260915_pr3879-branch-rebase.md)
- `exec/results/canon-ci-20260918/notes.html` -> `WS/exec/results/canon-ci-20260918/notes.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/canon-ci-20260918/notes.html
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/results/canon-ci-20260918/render.sh` -> `WS/exec/results/canon-ci-20260918/render.sh`
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `exec/results/ci-enable-20260917/counter-validation.txt` -> `WS/exec/results/ci-enable-20260917/counter-validation.txt`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `exec/results/ci-enable-20260917/package-checks.txt` -> `WS/exec/results/ci-enable-20260917/package-checks.txt`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `exec/results/ci-mimic-20260918/caveats.html` -> `WS/exec/results/ci-mimic-20260918/caveats.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/ci-mimic-20260918/caveats.html
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/results/ci-mimic-20260918/notes3.html` -> `WS/exec/results/ci-mimic-20260918/notes3.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/ci-mimic-20260918/notes3.html
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `exec/results/expert-replicas-20260917/README.md` -> `WS/exec/results/expert-replicas-20260917/README.md`
  (handoffs: claude_20260917_num-expert-replicas-flag-on-delphi-3bda.md)
- `exec/results/p0perf-20260913/platformd-instance-1.env.txt` -> `WS/exec/results/p0perf-20260913/platformd-instance-1.env.txt`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/results/p0perf-20260913/summary.md` -> `WS/exec/results/p0perf-20260913/summary.md`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `exec/tilec-20260917/build.sh` -> `WS/exec/tilec-20260917/build.sh`
  (handoffs: claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md)
- `exec/vnnik-20260914/campaign.sh` -> `WS/exec/vnnik-20260914/campaign.sh`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/compare_tokens.py` -> `WS/exec/vnnik-20260914/compare_tokens.py`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/gen_compare.py` -> `WS/exec/vnnik-20260914/gen_compare.py`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/gen_report.py` -> `WS/exec/vnnik-20260914/gen_report.py`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/launch.sh` -> `WS/exec/vnnik-20260914/launch.sh`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/pretest-light.sh` -> `WS/exec/vnnik-20260914/pretest-light.sh`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/summarize.py` -> `WS/exec/vnnik-20260914/summarize.py`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-20260914/syn-check-vnni.sh` -> `WS/exec/vnnik-20260914/syn-check-vnni.sh`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/vnnik-trace-20260914/analyze.py` -> `WS/exec/vnnik-trace-20260914/analyze.py`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik-trace-20260914/lanes.py` -> `WS/exec/vnnik-trace-20260914/lanes.py`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik-trace-20260914/trace.sh` -> `WS/exec/vnnik-trace-20260914/trace.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/build.sh` -> `WS/exec/vnnik2-20260915/build.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/campaign.sh` -> `WS/exec/vnnik2-20260915/campaign.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md, claude_20260915_draft-reply-to-rhys.md)
- `exec/vnnik2-20260915/compare_tokens.py` -> `WS/exec/vnnik2-20260915/compare_tokens.py`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/confirm.sh` -> `WS/exec/vnnik2-20260915/confirm.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/confirm2.sh` -> `WS/exec/vnnik2-20260915/confirm2.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/gen_report.py` -> `WS/exec/vnnik2-20260915/gen_report.py`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md, claude_20260916-20260918_block-store-transpose-animation.md)
- `exec/vnnik2-20260915/precheck.sh` -> `WS/exec/vnnik2-20260915/precheck.sh`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/summarize.py` -> `WS/exec/vnnik2-20260915/summarize.py`
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `exec/vnnik2-20260915/takeover-hook-20260915.patch` -> `WS/exec/vnnik2-20260915/takeover-hook-20260915.patch`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)
- `exec/vnnik4-20260915/chain.sh` -> `WS/exec/vnnik4-20260915/chain.sh`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md)
- `exec/vnnik4-20260915/models.sh` -> `WS/exec/vnnik4-20260915/models.sh`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md)
- `exec/vnnik4-20260915/precheck.sh` -> `WS/exec/vnnik4-20260915/precheck.sh`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md)
- `exec/vnnik4-20260915/verify.sh` -> `WS/exec/vnnik4-20260915/verify.sh`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md)
- `exec/vnnik5-20260916/build.sh` -> `WS/exec/vnnik5-20260916/build.sh`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `exec/vnnik5-20260916/final-head.sh` -> `WS/exec/vnnik5-20260916/final-head.sh`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `exec/vnnik5-20260916/format-check.sh` -> `WS/exec/vnnik5-20260916/format-check.sh`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `exec/vnnik5-20260916/host-suite.sh` -> `WS/exec/vnnik5-20260916/host-suite.sh`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `exec/vnnik6-20260916/PLAN.md` -> `WS/exec/vnnik6-20260916/PLAN.md`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/analyze.py` -> `WS/exec/vnnik6-20260916/analyze.py`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/build.sh` -> `WS/exec/vnnik6-20260916/build.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/campaign.sh` -> `WS/exec/vnnik6-20260916/campaign.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/chain.sh` -> `WS/exec/vnnik6-20260916/chain.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/compare_tokens.py` -> `WS/exec/vnnik6-20260916/compare_tokens.py`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/extra-oldbase.sh` -> `WS/exec/vnnik6-20260916/extra-oldbase.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/extra2-trace8192.sh` -> `WS/exec/vnnik6-20260916/extra2-trace8192.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/extra3-trace2048.sh` -> `WS/exec/vnnik6-20260916/extra3-trace2048.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/gen_report.py` -> `WS/exec/vnnik6-20260916/gen_report.py`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/launch.sh` -> `WS/exec/vnnik6-20260916/launch.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/sections/notes.html` -> `WS/exec/vnnik6-20260916/sections/notes.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/vnnik6-20260916/sections/notes.html
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/sections/recommendation.html` -> `WS/exec/vnnik6-20260916/sections/recommendation.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/vnnik6-20260916/sections/recommendation.html
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/sections/remedies.html` -> `WS/exec/vnnik6-20260916/sections/remedies.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/vnnik6-20260916/sections/remedies.html
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/summarize.py` -> `WS/exec/vnnik6-20260916/summarize.py`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik6-20260916/trace.sh` -> `WS/exec/vnnik6-20260916/trace.sh`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `exec/vnnik7-20260916/build.sh` -> `WS/exec/vnnik7-20260916/build.sh`
  (handoffs: claude_20260916_k-vnni-hpp-rebuild.md)
- `exec/wedperf-20260916/build-chain.sh` -> `WS/exec/wedperf-20260916/build-chain.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/build.sh` -> `WS/exec/wedperf-20260916/build.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/campaign-attr.sh` -> `WS/exec/wedperf-20260916/campaign-attr.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/campaign-attr2.sh` -> `WS/exec/wedperf-20260916/campaign-attr2.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/campaign-gen.sh` -> `WS/exec/wedperf-20260916/campaign-gen.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/campaign.sh` -> `WS/exec/wedperf-20260916/campaign.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/compare_tokens.py` -> `WS/exec/wedperf-20260916/compare_tokens.py`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/gen_report.py` -> `WS/exec/wedperf-20260916/gen_report.py`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-attr-more.sh` -> `WS/exec/wedperf-20260916/launch-attr-more.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-attr.sh` -> `WS/exec/wedperf-20260916/launch-attr.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-attr2.sh` -> `WS/exec/wedperf-20260916/launch-attr2.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-builds.sh` -> `WS/exec/wedperf-20260916/launch-builds.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-campaign.sh` -> `WS/exec/wedperf-20260916/launch-campaign.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/launch-gen1536.sh` -> `WS/exec/wedperf-20260916/launch-gen1536.sh`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/make_artifact_copy.py` -> `WS/exec/wedperf-20260916/make_artifact_copy.py`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/wedperf-20260916/summarize.py` -> `WS/exec/wedperf-20260916/summarize.py`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `exec/workflows/amx-128x4-ci-models-wf_e1d04f3e-7a3.js` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/5435bd53-a7f6-440c-894a-f90c35d3546e/workflows/scripts/amx-128x4-ci-models-wf_e1d04f3e-7a3.js`
  (handoffs: claude_20260918_amx-compatible-128x4-models-in-nightly-ci.md)
- `exec/workflows/review-rinzler-takeover-wf_1ca7399d-b54.js` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/workflows/scripts/review-rinzler-takeover-wf_1ca7399d-b54.js`
  (handoffs: claude_20260915_draft-reply-to-rhys.md)

### VNNIed K in place: status pages, design, animations, issue 4500 (vnnied-k-in-place/)

- `vnnied-k-in-place/codex/design/root-cause-tracing.html` -> `WS/VNNIed-K-in-place/codex/design/root-cause-tracing.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/codex/design/root-cause-tracing.html
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `vnnied-k-in-place/design/claude-VNNIed-K.html` -> `WS/VNNIed-K-in-place/design/claude-VNNIed-K.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/design/claude-VNNIed-K.html
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `vnnied-k-in-place/exec/block-store-animation/build-gt.sh` -> `WS/VNNIed-K-in-place/exec/block-store-animation/build-gt.sh`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/exec/block-store-animation/gen_page.py` -> `WS/VNNIed-K-in-place/exec/block-store-animation/gen_page.py`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/exec/block-store-animation/gt.cpp` -> `WS/VNNIed-K-in-place/exec/block-store-animation/gt.cpp`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/exec/block-store-animation/shim/common/numerics/bf16.hpp` -> `WS/VNNIed-K-in-place/exec/block-store-animation/shim/common/numerics/bf16.hpp`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/exec/block-store-animation/shim/common/numerics/fp16.hpp` -> `WS/VNNIed-K-in-place/exec/block-store-animation/shim/common/numerics/fp16.hpp`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/exec/gen_fpga_page.py` -> `WS/VNNIed-K-in-place/exec/gen_fpga_page.py`
  (handoffs: claude_20260916-20260917_pr4424-vnni-k-layout-and-fpga-attention.md)
- `vnnied-k-in-place/exec/shared-save-animation/context_sections.py` -> `WS/VNNIed-K-in-place/exec/shared-save-animation/context_sections.py`
  (handoffs: claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/exec/shared-save-animation/cut_units.py` -> `WS/VNNIed-K-in-place/exec/shared-save-animation/cut_units.py`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md, claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/exec/shared-save-animation/gen_page.py` -> `WS/VNNIed-K-in-place/exec/shared-save-animation/gen_page.py`
  (handoffs: claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/exec/shared-save-animation/savek_spans.py` -> `WS/VNNIed-K-in-place/exec/shared-save-animation/savek_spans.py`
  (handoffs: claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/exec/shared-save-animation/window_layout.cpp` -> `WS/VNNIed-K-in-place/exec/shared-save-animation/window_layout.cpp`
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md, claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/input-2-ai/to-claude.md` -> `WS/VNNIed-K-in-place/input-2-ai/to-claude.md`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `vnnied-k-in-place/issue4500/root-cause-debug.html` -> `WS/VNNIed-K-in-place/issue4500/root-cause-debug.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/issue4500/root-cause-debug.html
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `vnnied-k-in-place/status/Friday-morning-CI-run-report.html` -> `WS/VNNIed-K-in-place/status/Friday-morning-CI-run-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/Friday-morning-CI-run-report.html
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `vnnied-k-in-place/status/Monday-morning-report.html` -> `WS/VNNIed-K-in-place/status/Monday-morning-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/Monday-morning-report.html
  Lineage labels (regenerate: unavailable): see the 2026-09-20 batch below.
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `vnnied-k-in-place/status/VNNI-K-FPGA-ATTN.html` -> `WS/VNNIed-K-in-place/status/VNNI-K-FPGA-ATTN.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/VNNI-K-FPGA-ATTN.html
  (handoffs: claude_20260916-20260917_pr4424-vnni-k-layout-and-fpga-attention.md)
- `vnnied-k-in-place/status/Wednesday-morning-report.html` -> `WS/VNNIed-K-in-place/status/Wednesday-morning-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/Wednesday-morning-report.html
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `vnnied-k-in-place/status/Wednesday-perf-test.html` -> `WS/VNNIed-K-in-place/status/Wednesday-perf-test.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/Wednesday-perf-test.html
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)
- `vnnied-k-in-place/status/amx-options-page/page.md` -> `WS/VNNIed-K-in-place/status/amx-options-page/page.md`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `vnnied-k-in-place/status/amx-tree-hw-attn.html` -> `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/150fe5cd-91f2-4ba4-a357-dc1a80c785c9/scratchpad/amx-tree-hw-attn.html` (volatile session scratchpad, the repo copy is the durable one)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/amx-tree-hw-attn.html
  (handoffs: claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md)
- `vnnied-k-in-place/status/block-store-animation.html` -> `WS/VNNIed-K-in-place/status/block-store-animation.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/block-store-animation.html
  (handoffs: claude_20260916-20260918_block-store-transpose-animation.md)
- `vnnied-k-in-place/status/handoff-store-remedies.md` -> `WS/VNNIed-K-in-place/status/handoff-store-remedies.md`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md, claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md)
- `vnnied-k-in-place/status/issue-fpga-attention-vnni-k-tps.body.md` -> `WS/VNNIed-K-in-place/status/issue-fpga-attention-vnni-k-tps.body.md`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `vnnied-k-in-place/status/llama8b-AMX-gain-vs-load.html` -> `WS/VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/llama8b-AMX-gain-vs-load.html
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `vnnied-k-in-place/status/main-rebase-20260915/issue-divergence-body.md` -> `WS/VNNIed-K-in-place/status/main-rebase-20260915/issue-divergence-body.md`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `vnnied-k-in-place/status/main-rebase-20260915/pr-body.before.md` -> `WS/VNNIed-K-in-place/status/main-rebase-20260915/pr-body.before.md`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `vnnied-k-in-place/status/main-rebase-20260915/rebase-report.html` -> `WS/VNNIed-K-in-place/status/main-rebase-20260915/rebase-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/main-rebase-20260915/rebase-report.html
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `vnnied-k-in-place/status/mirror-vs-VNNI-K.html` -> `WS/VNNIed-K-in-place/status/mirror-vs-VNNI-K.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/mirror-vs-VNNI-K.html
  Lineage labels, regenerate command (verified 2026-09-20) and inventory: see the 2026-09-20 batch below.
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `vnnied-k-in-place/status/pr-body-draft.md` -> `WS/VNNIed-K-in-place/status/pr-body-draft.md`
  (handoffs: claude_20260914-20260915_jhan-amx-vnnik-draft-pr-to-jhan-amx-p0.md, claude_20260915_striped-block-store-naming-alternatives.md)
- `vnnied-k-in-place/status/shared-save-animation.html` -> `WS/VNNIed-K-in-place/status/shared-save-animation.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/shared-save-animation.html
  (handoffs: claude_20260918_shared-save-context-in-shared-save-animation-html.md)
- `vnnied-k-in-place/status/store-remedies-report.html` -> `WS/VNNIed-K-in-place/status/store-remedies-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/vnnied-k-in-place/status/store-remedies-report.html
  (handoffs: claude_20260914_save-k-vnni-perfetto-trace-and-block-transpose.md, claude_20260916-20260918_block-store-transpose-animation.md)

### PR1 and CI-enable reports (pr3879/)

- `pr3879/CI-enable/Thursday-report.md` -> `WS/PR3879/new-PRs/CI-enable/Thursday-report.md`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `pr3879/CI-enable/for-Rhys-andoria-AMD-test.md` -> `WS/PR3879/new-PRs/CI-enable/for-Rhys-andoria-AMD-test.md`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `pr3879/PR1/CI-AMX-test-shapes.html` -> `WS/PR3879/new-PRs/PR1/CI-AMX-test-shapes.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/CI-AMX-test-shapes.html
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `pr3879/PR1/Sunday-CI-layout-results.html` -> `WS/PR3879/new-PRs/PR1/Sunday-CI-layout-results.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/Sunday-CI-layout-results.html
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `pr3879/PR1/canonical-AMX-CI-run-report.html` -> `WS/PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/canonical-AMX-CI-run-report.html
  (handoffs: claude_20260918_pr3879-amx-ci-harness-run.md)
- `pr3879/PR1/nightly-amx-check-20260916.html` -> `WS/PR3879/new-PRs/PR1/nightly-amx-check-20260916.html`
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/nightly-amx-check-20260916.html
  (handoffs: claude_20260916-20260917_tron-amx-dispatch-in-ci-builds-after-pr3879.md)
- `pr3879/amx-shape-ci.html` -> `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-random/5435bd53-a7f6-440c-894a-f90c35d3546e/scratchpad/amx-shape-ci.html` (volatile session scratchpad, the repo copy is the durable one)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/amx-shape-ci.html
  (handoffs: claude_20260918_amx-compatible-128x4-models-in-nightly-ci.md)
- `pr3879/gen_sec2.py` -> `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX/d5572a41-5bae-4bce-87ed-3285768e6e77/scratchpad/gen_sec2.py` (volatile session scratchpad, the repo copy is the durable one)
  (handoffs: claude_20260914_baseline-vs-mirror-sketch-html-matrix-dimensions.md)

### project memory notes (memory/)

- `memory/3bda-nightly-rinzler-cleanup.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-nightly-rinzler-cleanup.md`
  (handoffs: claude_20260915_striped-block-store-naming-alternatives.md)
- `memory/amx-busy-perf-counter.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/amx-busy-perf-counter.md`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `memory/amx-options-notion-page.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/amx-options-notion-page.md`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `memory/amx-vnni-pseudocode-check-page.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/amx-vnni-pseudocode-check-page.md`
  (handoffs: claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md)
- `memory/artifact-utf8-mojibake-trap.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/artifact-utf8-mojibake-trap.md`
  (handoffs: claude_20260913_amx-baseline-vs-mirror-sketch.md)
- `memory/baseline-vs-mirror-sketch.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/baseline-vs-mirror-sketch.md`
  (handoffs: claude_20260913_amx-baseline-vs-mirror-sketch.md, claude_20260914_baseline-vs-mirror-sketch-html-matrix-dimensions.md)
- `memory/ci-enable-20260917-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/ci-enable-20260917-campaign.md`
  (handoffs: claude_20260917_amx-in-nightly-ci-on-delphi-3bda.md)
- `memory/ci-mimic-20260918-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/ci-mimic-20260918-campaign.md`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `memory/claude-box-tron-build-env.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/claude-box-tron-build-env.md`
  (handoffs: claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md)
- `memory/fpga-path-under-vnni-k.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/fpga-path-under-vnni-k.md`
  (handoffs: claude_20260916-20260917_pr4424-vnni-k-layout-and-fpga-attention.md)
- `memory/issue-4500-root-cause-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/issue-4500-root-cause-campaign.md`
  (handoffs: claude_20260918_tron-4500-fpga-attention-decode-tps-loss.md)
- `memory/l8bload-20260918-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/l8bload-20260918-campaign.md`
  (handoffs: claude_20260917-20260918_nightly-ci-mimic-with-amx-and-vnni-k.md)
- `memory/nightly-vs-ours-tps-context.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/nightly-vs-ours-tps-context.md`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `memory/notebook-preservation-convention.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/notebook-preservation-convention.md`
  (handoffs: claude_20260913_amx-baseline-vs-mirror-sketch.md)
- `memory/p0perf-20260913-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/p0perf-20260913-campaign.md`
  (handoffs: claude_20260912-20260913_tps-discrepancy-vs-nightly-ci.md)
- `memory/pr-item-register.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/pr-item-register.md`
  (handoffs: claude_20260915_vnni-branch-rebase-onto-main-for-pr4424.md)
- `memory/pr4424-description-on-github.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/pr4424-description-on-github.md`
  (handoffs: claude_20260915_striped-block-store-naming-alternatives.md)
- `memory/rinzler-unit-expert-replicas-750.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/rinzler-unit-expert-replicas-750.md`
  (handoffs: claude_20260917_num-expert-replicas-flag-on-delphi-3bda.md)
- `memory/vnni-k-terminology.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/vnni-k-terminology.md`
  (handoffs: claude_20260915_striped-block-store-naming-alternatives.md, claude_20260916-20260917_amx-and-vnni-k-dispatch-flags.md)
- `memory/vnnied-k-in-place-project.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/vnnied-k-in-place-project.md`
  (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `memory/vnnik-branch-build-convention.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-tron/memory/vnnik-branch-build-convention.md`
  (handoffs: claude_20260916_k-vnni-hpp-rebuild.md)
- `memory/vnnik6-kvmul8-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/vnnik6-kvmul8-campaign.md`
  (handoffs: claude_20260915-20260916_pr4424-vnni-layout-gate-for-kv-mul-8.md)
- `memory/wedperf-20260916-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/wedperf-20260916-campaign.md`
  (handoffs: claude_20260916-20260917_pr4424-vs-pre-pr3879-perf-test.md)


## 2026-09-20 preservation batch (claude-agentsrv handoff run, first run under the 2026-09-19 prompt)

Registered by the 2026-09-20 `SCOPE: auto` run on claude-agentsrv. Canonical -> repo mirrors, edit the canonical file first. `WS` = `claude-agentsrv:/home/jhan/workspace/intel-AMX`. This batch is the first lineage backfill under the amended prompt (Step 4b, "Computed-from files"): the files a preserved report page is computed from are mirrored beside it, at `artifacts/intel-amx/<path relative to WS>`. Files left behind are listed with their reason in each page's inventory file.

### Lineage of `vnnied-k-in-place/status/mirror-vs-VNNI-K.html` (registered 2026-09-18, labels added 2026-09-20)

- generator: `exec/vnnik-20260914/gen_compare.py` (mirrored)
- input: `exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` -> `WS/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json` (545679 bytes; hand-edited after build)
- input built by: `exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` -> `WS/exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (Claude Workflow script, relocated 2026-09-20; origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js`)
- sources: 292 files preserved, 261 left behind. Per directory (preserved kinds; left behind by reason):
  - `../ai-runs/systems_test/testlib/`: preserved none; left behind (in git): tps.py
  - `PR3879/more-testing/round-1/`: preserved status.md
  - `exec/`: preserved none; left behind (duplicate (already mirrored)): p2-cap-over.sh, p2-cap-sweep.sh, p2-inc3-arena.sh, p2-t4-morning.sh, p2-t4-power.sh, p2-t4-reps.sh, p2-t4-shapes.sh
  - `exec/ctxfill-20260901/`: preserved none; left behind (duplicate (already mirrored)): run-ctxfill.sh, run-ctxfill2.sh
  - `exec/fence-20260831/`: preserved none; left behind (duplicate (already mirrored)): run-fence3.sh
  - `exec/g1-20260908/`: preserved none; left behind (duplicate (already mirrored)): g1-campaign.sh, rz.sh
  - `exec/logs/`: preserved none; left behind (provenance): *.log
  - `exec/more-testing-r1/`: preserved none; left behind (duplicate (already mirrored)): run_cell.sh, rz.sh, st_perf.py
  - `exec/p0perf-20260911/`: preserved none; left behind (duplicate (already mirrored)): campaign.sh, rz.sh, summarize.py
  - `exec/p0perf-20260913/`: preserved none; left behind (duplicate (already mirrored)): campaign.sh, rz.sh, summarize.py
  - `exec/perfstat-20260831/`: preserved none; left behind (duplicate (already mirrored)): run-perfstat3.sh
  - `exec/results/`: preserved *.txt x4
  - `exec/results/ctxfill-20260901/`: preserved *.log; left behind (duplicate (already mirrored)): *.txt, curve.json
  - `exec/results/ctxfill2-20260901/`: preserved *.log; left behind (duplicate (already mirrored)): *.txt, curve2.json
  - `exec/results/fence3-20260901/`: preserved *.log; left behind (duplicate (already mirrored)): *.txt
  - `exec/results/g1-20260908/`: preserved *.log x2, *.txt, summary.json, summary.md, summary.txt; left behind (duplicate (held by compact text)): *.log x10
  - `exec/results/g1-20260908/cells/*/`: preserved meta.json x37, perf*.json x29, perf*.log x2, proof.txt x29; left behind (provenance): perf*.log x35, rinzler.log x8
  - `exec/results/more-testing-r1/`: preserved notes.md
  - `exec/results/more-testing-r1/cells/*/`: preserved *.log x10, meta.json x13, perf*.json x13; left behind (provenance): functional.xml x13, rinzler.log x14
  - `exec/results/p0perf-20260911/`: preserved *.txt, build.txt, ci-reference-20260911.json, summary.json, summary.md; left behind (size): *.log
  - `exec/results/p0perf-20260911/cells/*/`: preserved meta.json x8, perf*.json x8, proof.txt x8; left behind (provenance): perf*.log x8
  - `exec/results/p0perf-20260911/rt/`: preserved none; left behind (duplicate (held by compact text)): *.log x24
  - `exec/results/p0perf-20260913/`: preserved *.txt, build.txt, summary.json; left behind (duplicate (already mirrored)): *.txt, summary.md
  - `exec/results/p0perf-20260913/cells/*/`: preserved meta.json x18, perf*.json x45, proof.txt x18; left behind (provenance): perf*.log x27
  - `exec/results/p0perf-20260913/rt/`: preserved none; left behind (duplicate (held by compact text)): *.log x24
  - `exec/results/perf-round-20260825/`: preserved none; left behind (duplicate (already mirrored)): *.txt
  - `exec/results/perf-round-20260830/`: preserved none; left behind (duplicate (already mirrored)): *.txt x2
  - `exec/results/perfstat3-20260901/`: preserved none; left behind (provenance): *.log x3
  - `exec/results/t4/`: preserved *.log x18, *.txt x7
  - `exec/results/vnnik-20260914/`: preserved *.txt, build.txt, mirror-vs-vnni-rows.json, summary.json, summary.md, tests.txt
  - `exec/results/vnnik-20260914/rt/`: preserved none; left behind (duplicate (held by compact text)): *.log x60
- regenerate: `run on claude-agentsrv: python3 /home/jhan/workspace/intel-AMX/exec/vnnik-20260914/gen_compare.py /home/jhan/workspace/intel-AMX/exec/results/vnnik-20260914/mirror-vs-vnni-rows.json <OUT>`. Lines expected to differ: the one "Pulled from the existing result files on <timestamp>" sentence, plus the 6-line rendered-view comment above the doctype in the repo copy. regenerate verified 2026-09-20 (0 differing lines after masking that sentence).
- inventory: `vnnied-k-in-place/status/mirror-vs-VNNI-K.html.lineage.md` (one line per cited file with the decision).

### Lineage of `vnnied-k-in-place/status/Monday-morning-report.html` (registered 2026-09-18, labels added 2026-09-20)

- generator: `exec/vnnik-20260914/gen_report.py` (mirrored)
- input: none (the generator reads the result directory `WS/exec/results/vnnik-20260914/` directly)
- input built by: none
- sources: `exec/results/vnnik-20260914/{rt-results.txt,summary.json,summary.md,build.txt,tests.txt,smoke/smoke.txt}` and `exec/results/vnnik-20260914/prewindow/*.out` plus `prewindow/pretest-p3.summary.txt` (preserved, shared with the page above where the same file is cited). Left behind (provenance): `exec/logs/vnnik-20260914.{status,done,log}`; left behind (unavailable): `/var/tmp/jhan/vnni-syn-c1.out`, `vnni-syn-c3.out`, `vnni-pretest-p3.out` on delphi-3bda, and the live git history of the `tron-VNNIed-K` worktree.
- regenerate: unavailable (the generator reads live git history of the worktree and files under /var/tmp on delphi-3bda; it takes an output path as its second argument, but the output depends on those live inputs). regeneration check: not run.

### Lineage of `tron-amx-distilled.html` (registered 2026-08-24, labels added 2026-09-20)

- generator: `generators/gen_distilled.py` -> `WS/exec/gen_distilled.py` (mirrored)
- input: none (the generator reads the rampup corpus directly)
- input built by: none
- sources: `rampup/01-amx-rampup.html`, `rampup/02-tron-decode-amx-plan.html`, `rampup/pr-rampup.html`, `rampup/2026-08-19-amx-status.html` (all mirrored under `artifacts/intel-amx/rampup/`).
- regenerate: unavailable (the generator has no output-path argument and writes the canonical page `WS/tron-amx-distilled.html` unconditionally [exec/gen_distilled.py:1420]). regeneration check: not run (generator has no output argument).

### Relocated Workflow scripts (Step 4b, Session-store files)

- `exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` -> `WS/exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (8981 bytes). origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js`. The Workflow that extracted the 239 rows of rows.json from eight result sets on 2026-09-14. (handoffs: claude_20260913-20260914_input-2-ai-to-claude-md-instructions.md)
- `exec/workflows/amx-128x4-ci-models-wf_e1d04f3e-7a3.js` -> `WS/exec/workflows/amx-128x4-ci-models-wf_e1d04f3e-7a3.js` (canonical path changed 2026-09-20; origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/5435bd53-a7f6-440c-894a-f90c35d3546e/workflows/scripts/amx-128x4-ci-models-wf_e1d04f3e-7a3.js`). (handoffs: claude_20260918_amx-compatible-128x4-models-in-nightly-ci.md)
- `exec/workflows/review-rinzler-takeover-wf_1ca7399d-b54.js` -> `WS/exec/workflows/review-rinzler-takeover-wf_1ca7399d-b54.js` (canonical path changed 2026-09-20; origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/workflows/scripts/review-rinzler-takeover-wf_1ca7399d-b54.js`). (handoffs: claude_20260915_draft-reply-to-rhys.md)

### Refreshed mirrors (canonical grew in place)

- `exec/canon-ci-20260918/gen_ci_shapes.py` refreshed from `claude-agentsrv:/home/jhan/workspace/intel-AMX/exec/canon-ci-20260918/gen_ci_shapes.py` (153460 bytes; generator v3 of the CI test-shapes page, 2026-09-19).
- `pr3879/PR1/CI-AMX-test-shapes.html` refreshed from `claude-agentsrv:/home/jhan/workspace/intel-AMX/PR3879/new-PRs/PR1/CI-AMX-test-shapes.html` (111558 bytes; page regenerated 2026-09-19 17:43 UTC (v2.2)).
- `vnnied-k-in-place/issue4500/root-cause-debug.html` refreshed from `claude-agentsrv:/home/jhan/workspace/intel-AMX/VNNIed-K-in-place/issue4500/root-cause-debug.html` (123000 bytes; page grew 2026-09-19 (campaign results)).
- `memory/issue-4500-root-cause-campaign.md` refreshed from `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/issue-4500-root-cause-campaign.md` (11121 bytes; memory note appended).

### Relocated files (Step 4b, Session-store files): copied from the Claude session store or a session scratchpad into the canonical folder, then mirrored

- `exec/canon-ci-20260918/amx-lever-sweep-wf_6f881b28-494.js` -> `WS/exec/canon-ci-20260918/amx-lever-sweep-wf_6f881b28-494.js` (25108 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/6767cb7e-e22e-4c52-9d1f-d0aa98d8d702/workflows/scripts/amx-lever-sweep-wf_6f881b28-494.js. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/canon-ci-20260918/ci-shapes-v2-verify-wf_4eca41e2-c18.js` -> `WS/exec/canon-ci-20260918/ci-shapes-v2-verify-wf_4eca41e2-c18.js` (10486 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/6767cb7e-e22e-4c52-9d1f-d0aa98d8d702/workflows/scripts/ci-shapes-v2-verify-wf_4eca41e2-c18.js. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/canon-ci-20260918/ci-shapes-v22-verify-wf_9171df83-570.js` -> `WS/exec/canon-ci-20260918/ci-shapes-v22-verify-wf_9171df83-570.js` (8229 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/6767cb7e-e22e-4c52-9d1f-d0aa98d8d702/workflows/scripts/ci-shapes-v22-verify-wf_9171df83-570.js. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/issue4500-20260918/issue4500-design-review-wf_902344a4-aef.js` -> `WS/exec/issue4500-20260918/issue4500-design-review-wf_902344a4-aef.js` (5162 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/65d0ce4e-a16a-4f49-ace2-6f1e986914d2/workflows/scripts/issue4500-design-review-wf_902344a4-aef.js. (handoffs: claude_20260918-20260919_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/l8b-levers-20260919/review-l8b-levers-campaign-wf_c9eeb463-a76.js` -> `WS/exec/l8b-levers-20260919/review-l8b-levers-campaign-wf_c9eeb463-a76.js` (16495 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-CI-test/d663273f-b92f-4151-8123-4162a86b1dbe/workflows/scripts/review-l8b-levers-campaign-wf_c9eeb463-a76.js. (handoffs: claude_20260919_status-saturday-plan-md-post-ci-actions.md)
- `exec/l8b-levers-20260919/review2-l8b-levers-campaign-wf_8d97315d-7a6.js` -> `WS/exec/l8b-levers-20260919/review2-l8b-levers-campaign-wf_8d97315d-7a6.js` (10351 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-CI-test/d663273f-b92f-4151-8123-4162a86b1dbe/workflows/scripts/review2-l8b-levers-campaign-wf_8d97315d-7a6.js. (handoffs: claude_20260919_status-saturday-plan-md-post-ci-actions.md)
- `exec/q4b-swattn-20260919/review-q4b-swattn-driver-wf_d1f46dc2-250.js` -> `WS/exec/q4b-swattn-20260919/review-q4b-swattn-driver-wf_d1f46dc2-250.js` (10521 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-CI-test/97995714-bbf8-40ca-9ece-8fe0b5083329/workflows/scripts/review-q4b-swattn-driver-wf_d1f46dc2-250.js. (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md)
- `exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` -> `WS/exec/vnnik-20260914/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js` (8981 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/80bfb407-086b-42a0-a4b7-cb11b85eb459/workflows/scripts/pull-mirror-vs-vnni-data-wf_9b0f456d-293.js. (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)
- `exec/workflows/amx-128x4-ci-models-wf_e1d04f3e-7a3.js` -> `WS/exec/workflows/amx-128x4-ci-models-wf_e1d04f3e-7a3.js` (11777 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/5435bd53-a7f6-440c-894a-f90c35d3546e/workflows/scripts/amx-128x4-ci-models-wf_e1d04f3e-7a3.js. (handoffs: see the 2026-09-20 handoffs)
- `exec/workflows/review-rinzler-takeover-wf_1ca7399d-b54.js` -> `WS/exec/workflows/review-rinzler-takeover-wf_1ca7399d-b54.js` (9855 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-random/2c293dfd-07a3-4dc2-a1b4-4fffea2824de/workflows/scripts/review-rinzler-takeover-wf_1ca7399d-b54.js. (handoffs: see the 2026-09-20 handoffs)
- `pr3879/PR1/data-p/prune_probe.py` -> `WS/PR3879/new-PRs/PR1/data-p/prune_probe.py` (1267 bytes). origin: claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/dd4de50a-6f7d-4ba7-a8e0-5e5d231289ac/scratchpad/prune_probe.py (session scratchpad). (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `pr3879/PR1/data-p/prune_probe_2048.py` -> `WS/PR3879/new-PRs/PR1/data-p/prune_probe_2048.py` (973 bytes). origin: claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/6767cb7e-e22e-4c52-9d1f-d0aa98d8d702/scratchpad/prune_probe_2048.py (session scratchpad). (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `pr3879/PR1/data-p/sharegpt_tok_lens.json` -> `WS/PR3879/new-PRs/PR1/data-p/sharegpt_tok_lens.json` (6004 bytes). origin: claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-PR3879-new-PRs-PR1/6767cb7e-e22e-4c52-9d1f-d0aa98d8d702/scratchpad/sharegpt_tok_lens.json (session scratchpad). (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `vnnied-k-in-place/status/data-preservation-check/check_paths.py` -> `WS/VNNIed-K-in-place/status/data-preservation-check/check_paths.py` (3801 bytes). origin: claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/7596a88a-3461-481f-a00c-3da8664482fd/scratchpad/check_paths.py (session scratchpad). (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)
- `vnnied-k-in-place/status/data-preservation-check/classify_rows.py` -> `WS/VNNIed-K-in-place/status/data-preservation-check/classify_rows.py` (2365 bytes). origin: claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/7596a88a-3461-481f-a00c-3da8664482fd/scratchpad/classify_rows.py (session scratchpad). (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)
- `vnnied-k-in-place/status/verify-notebook-crosscheck-wf_bd2e3fcc-9e4.js` -> `WS/VNNIed-K-in-place/status/verify-notebook-crosscheck-wf_bd2e3fcc-9e4.js` (7700 bytes). origin: claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX-VNNIed-K-in-place/7596a88a-3461-481f-a00c-3da8664482fd/workflows/scripts/verify-notebook-crosscheck-wf_bd2e3fcc-9e4.js. (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)

### New mirrors from the 2026-09-20 handoffs (campaign scripts, pages, documents, inputs, compact records, and the CI harness per-request samples)

- `CI-test/` -> `WS/CI-test/` — 4 files, 146 KiB: `status/Saturday-llama-3.1-8b.html`, `status/Saturday-plan.md`, `status/Saturday-qwen3-4b.html`, `status/qwen3-4b-Saturday-plan.md`. (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md, claude_20260919_status-saturday-plan-md-post-ci-actions.md)
  Rendered view of `Saturday-qwen3-4b.html`: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/CI-test/status/Saturday-qwen3-4b.html
  Rendered view of `Saturday-llama-3.1-8b.html`: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/CI-test/status/Saturday-llama-3.1-8b.html
- `exec/canon-ci-20260918/` -> `WS/exec/canon-ci-20260918/` — 2 files, 87 KiB: `T0-script-changes.md`, `gen_ci_shapes.py.v1-20260919`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/issue4500-20260918/` -> `WS/exec/issue4500-20260918/` — 2 files, 16 KiB: `m6.sh`, `m6_summarize.py`. (handoffs: claude_20260918-20260919_tron-4500-fpga-attention-decode-tps-loss.md)
- `exec/l8b-levers-20260919/` -> `WS/exec/l8b-levers-20260919/` — 14 files, 206 KiB: `analyze.py`, `campaign.sh`, `configs-no7168.json`, `configs.py`, `dut.sh`, `gen_report.py`, `h_registry.py`, `launch.sh`, `prompt.py.patch`, `prompt_check.py`, `review-findings.txt`, `review2-findings.txt`, `st_ci_perf.py`, `talos_stub/talos.py`. (handoffs: claude_20260919_status-saturday-plan-md-post-ci-actions.md)
- `exec/q4b-swattn-20260919/` -> `WS/exec/q4b-swattn-20260919/` — 20 files, 461 KiB: `analyze.py`, `campaign.sh`, `check-8u-p7168.json`, `check-8u-p8192.json`, `configs-full.json`, `configs-no7168.json`, `configs-no8192.json`, `configs.py`, `dut.sh`, `gen_report.py`, `launch.sh`, `prompt.py.after`, `prompt.py.before`, `prompt.py.patch`, and 6 more. (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md)
- `exec/results/canon-ci-20260918/` -> `WS/exec/results/canon-ci-20260918/` — 1 files, 3798 KiB: `canon/perf.json`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
  `canon/perf.json`: 3889505 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
- `exec/results/ci-mimic-20260918/` -> `WS/exec/results/ci-mimic-20260918/` — 2 files, 3828 KiB: `base-pass1/perf.json`, `reference/nightly_stats.json`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
  `base-pass1/perf.json`: 3889486 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
- `exec/results/fence3-20260901/` -> `WS/exec/results/fence3-20260901/` — 1 files, 5 KiB: `medians-7605.json`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/results/issue4500-20260918/` -> `WS/exec/results/issue4500-20260918/` — 129 files, 2550 KiB: `bench/bench.txt`, `m6/cells/tp2__2u__base__rep1/STATUS`, `m6/cells/tp2__2u__base__rep1/amx_busy.txt`, `m6/cells/tp2__2u__base__rep1/meta.json`, `m6/cells/tp2__2u__base__rep1/perf-e0.json`, `m6/cells/tp2__2u__base__rep1/perf.json`, `m6/cells/tp2__2u__base__rep1/proof.txt`, `m6/cells/tp2__2u__base__rep2/STATUS`, `m6/cells/tp2__2u__base__rep2/amx_busy.txt`, `m6/cells/tp2__2u__base__rep2/meta.json`, `m6/cells/tp2__2u__base__rep2/perf-e0.json`, `m6/cells/tp2__2u__base__rep2/perf.json`, `m6/cells/tp2__2u__base__rep2/proof.txt`, `m6/cells/tp2__2u__baseminb1__rep1/STATUS`, and 115 more. (handoffs: claude_20260918-20260919_tron-4500-fpga-attention-decode-tps-loss.md)
  Rendered view of `reading.html`: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/exec/results/issue4500-20260918/reading.html
  `traces/analysis.json`: 1641465 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
- `exec/results/l8b-levers-20260919/` -> `WS/exec/results/l8b-levers-20260919/` — 22 files, 17720 KiB: `base-identity.txt`, `base-pass1/perf.json`, `base-pass1/summary.txt`, `base-pass2/perf.json`, `base-pass2/summary.txt`, `base-pass3/perf.json`, `base-pass3/summary.txt`, `canon-pass1/perf.json`, `canon-pass1/summary.txt`, `canon-pass2/perf.json`, `canon-pass2/summary.txt`, `canon-pass3/perf.json`, `canon-pass3/summary.txt`, `check-32u-p8192/perf.json`, and 8 more. (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md, claude_20260919_status-saturday-plan-md-post-ci-actions.md)
  `base-pass1/perf.json`: 2848736 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `base-pass2/perf.json`: 2849788 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `base-pass3/perf.json`: 2848618 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass1/perf.json`: 2848602 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass2/perf.json`: 2848611 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass3/perf.json`: 2848955 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
- `exec/results/l8bload-20260918/` -> `WS/exec/results/l8bload-20260918/` — 2 files, 10 KiB: `summary.json`, `summary.md`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/results/q4b-swattn-20260919/` -> `WS/exec/results/q4b-swattn-20260919/` — 32 files, 12027 KiB: `RUNBOOK.md`, `base-identity.txt`, `base-pass1/perf.json`, `base-pass1/summary.txt`, `base-pass2/perf.json`, `base-pass2/summary.txt`, `base-pass3/perf.json`, `base-pass3/summary.txt`, `canon-pass1/perf.json`, `canon-pass1/summary.txt`, `canon-pass2/perf.json`, `canon-pass2/summary.txt`, `canon-pass3/perf.json`, `canon-pass3/summary.txt`, and 18 more. (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md)
  `base-pass1/perf.json`: 1919321 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `base-pass2/perf.json`: 1921359 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `base-pass3/perf.json`: 1919298 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass1/perf.json`: 1916732 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass2/perf.json`: 1914902 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
  `canon-pass3/perf.json`: 1917541 bytes, CI harness per-request samples, below the 5 MiB single-file threshold; the page's numbers are computed from it.
- `exec/results/wedperf-20260916/` -> `WS/exec/results/wedperf-20260916/` — 1 files, 6 KiB: `summary.md`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/results/wedperf-attr-20260916/` -> `WS/exec/results/wedperf-attr-20260916/` — 1 files, 6 KiB: `summary.md`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `exec/results/wedperf-gen1536-20260916/` -> `WS/exec/results/wedperf-gen1536-20260916/` — 1 files, 5 KiB: `summary.md`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `memory/` -> `WS/../` — 5 files, 27 KiB: `ci-amx-test-shapes-recommendation.md`, `l8b-levers-20260919-campaign.md`, `mirror-vs-vnnik-page-data-provenance.md`, `q4b-swattn-20260919-campaign.md`, `q4b-swattn-20260919-plan.md`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md, claude_20260919-20260920_qwen3-4b-saturday-plan-md.md, claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md, claude_20260919_status-saturday-plan-md-post-ci-actions.md)
- `pr3879/PR1/` -> `WS/PR3879/new-PRs/` — 1 files, 54 KiB: `CI-AMX-test-shapes.v1-20260919.html`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
  Rendered view of `CI-AMX-test-shapes.v1-20260919.html`: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/PR1/CI-AMX-test-shapes.v1-20260919.html
- `pr3879/more-testing/` -> `WS/PR3879/more-testing/` — 1 files, 70 KiB: `round-1/results.html`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
  Rendered view of `results.html`: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/more-testing/round-1/results.html
- `tmp/` -> `WS/tmp/` — 3 files, 59 KiB: `amx-raw-data/amx-summary.csv`, `amx-raw-data/chart-check.csv`, `amx-raw-data/t4-suite.txt`. (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `vnnied-k-in-place/status/` -> `WS/VNNIed-K-in-place/status/` — 1 files, 13 KiB: `mirror-vs-VNNI-K-data-preservation.md`. (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)

### memory/ additions (Claude Code project memory notes; the canonical stays in the session store because Claude Code edits these files in place)

- `memory/ci-amx-test-shapes-recommendation.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/ci-amx-test-shapes-recommendation.md` (7494 bytes). (handoffs: claude_20260918-20260919_amx-perf-claims-for-llama3-1-8b-vs-qwen3-4b.md)
- `memory/l8b-levers-20260919-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/l8b-levers-20260919-campaign.md` (8051 bytes). (handoffs: claude_20260919_status-saturday-plan-md-post-ci-actions.md)
- `memory/mirror-vs-vnnik-page-data-provenance.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/mirror-vs-vnnik-page-data-provenance.md` (2192 bytes). (handoffs: claude_20260919_mirror-vs-vnni-k-test-data-in-notebook-repo.md)
- `memory/q4b-swattn-20260919-campaign.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/q4b-swattn-20260919-campaign.md` (6725 bytes). (handoffs: claude_20260919-20260920_qwen3-4b-saturday-plan-md.md)
- `memory/q4b-swattn-20260919-plan.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-intel-AMX/memory/q4b-swattn-20260919-plan.md` (3008 bytes). (handoffs: claude_20260919_status-saturday-plan-md-post-ci-actions.md)

### Computed-from files of the two VNNI-K pages (D1, D2, E of the 2026-09-20 gate; full list with decisions in the inventory file)

- `exec/results/ctxfill-20260901` -> `WS/exec/results/ctxfill-20260901` — 1 files, 23 KiB.
- `exec/results/ctxfill2-20260901` -> `WS/exec/results/ctxfill2-20260901` — 1 files, 22 KiB.
- `exec/results/fence3-20260901` -> `WS/exec/results/fence3-20260901` — 1 files, 23 KiB.
- `exec/results/g1-20260908` -> `WS/exec/results/g1-20260908` — 103 files, 281 KiB.
- `exec/results/gptoss120b-pr1-half-20260909T1706.txt` -> `WS/exec/results/gptoss120b-pr1-half-20260909T1706.txt` — 1 files, 35 KiB.
- `exec/results/more-testing-r1` -> `WS/exec/results/more-testing-r1` — 37 files, 76 KiB.
- `exec/results/p0perf-20260911` -> `WS/exec/results/p0perf-20260911` — 29 files, 152 KiB.
- `exec/results/p0perf-20260913` -> `WS/exec/results/p0perf-20260913` — 84 files, 242 KiB.
- `exec/results/qwen8u8k-pr1-20260907T1904.txt` -> `WS/exec/results/qwen8u8k-pr1-20260907T1904.txt` — 1 files, 18 KiB.
- `exec/results/qwen8u8k-pr1-half-20260907T1904.txt` -> `WS/exec/results/qwen8u8k-pr1-half-20260907T1904.txt` — 1 files, 18 KiB.
- `exec/results/qwen8u8k-pr1-half-20260909T1704.txt` -> `WS/exec/results/qwen8u8k-pr1-half-20260909T1704.txt` — 1 files, 18 KiB.
- `exec/results/t4` -> `WS/exec/results/t4` — 25 files, 3680 KiB.
- `exec/results/vnnik-20260914` -> `WS/exec/results/vnnik-20260914` — 15 files, 835 KiB.
- `pr3879/more-testing` -> `WS/pr3879/more-testing` — 1 files, 41 KiB.
