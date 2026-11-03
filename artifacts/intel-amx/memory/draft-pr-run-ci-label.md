---
name: draft-pr-run-ci-label
description: "positron-ai/tron CI (2026-10-21): a DRAFT PR runs only lint, machinery and fresh-plan jobs; Build Tron / Test / Test host / Test FPGA show 'skipping' unless the PR carries the label 'Run CI', and a label change takes effect only on the next PR event (push, or close + reopen)"
metadata:
  type: project
---

Note [Draft PR Filtering and Label Override] in .github/workflows/gcp-nix.yml: draft PRs run lint, machinery and fresh-plan checks only. The label `Run CI` enables the product pipeline (Build Tron, Test host, Test, Test FPGA). Label changes take effect on the next PR update, so after adding the label do `gh pr close` + `gh pr reopen` (the reopened event starts a new GCP Nix run) or push. `Skip benchmarks` only skips the benchmark jobs.

**Why:** PR #5098 (2026-10-21) was opened as a draft to get the Build Tron job of PR 5047's branch green, and every build and test job showed "skipping" until the label and the reopen. Drafts #5086/#5087/#5094 have no GitHub build either (they were gated on 3bda).
**How to apply:** when a draft PR needs the GitHub build or tests, add `Run CI` at creation (`gh pr create --label "Run CI"`) or add it and reopen. Related: [[ben-stack-reexpress-20261021]].
