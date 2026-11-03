# Common-Knowledge Artifacts

Standalone explainer pages authored directly in this repo. These are
REPO-PRIMARY (no external canonical): edit them here.

- `coefficient-of-variation.html` — CV = sigma/mean explainer with measured example data.
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/coefficient-of-variation.html
- `kv-head-vs-query-head.html` — LLM query heads vs KV heads (MHA/GQA/MQA) with worked examples.
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/kv-head-vs-query-head.html
  (handoff: claude_20260819-20260823_kv-head-and-query-head-explainer-html.md)
- `weights-bytes-gpt-oss-120b.html` — parameters-to-bytes walkthrough for
  openai/gpt-oss-120b (numbers generated from the model's config.json).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/weights-bytes-gpt-oss-120b.html
  (handoff: claude_20260823_kv-head-vs-query-head-token-axis-dimensions.md)
- `weights-bytes-qwen2.5-32b.html` — parameters-to-bytes walkthrough for
  Qwen/Qwen2.5-32B (numbers generated from the model's config.json).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/weights-bytes-qwen2.5-32b.html
  (handoff: claude_20260823_kv-head-vs-query-head-token-axis-dimensions.md)
- `tron-book-page-token-kv.html` — Tron KV-cache concepts book / page / token /
  K / V and how they relate, with Qwen3-4B-Instruct-2507 byte arithmetic
  (computed from the source's size formulas, not measured).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/tron-book-page-token-kv.html

## Generated-report lineage backfill (2026-09-20)

These entries record the source inventory and regeneration limits for existing report pages. Canonical files remain authoritative. Companion inventories are repo-primary metadata.

### weights-bytes-gpt-oss-120b.html

- generator: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gen_weights_pages.py` — left behind (missing on 2026-09-20)
- input: `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gptoss-{config,index,tensors}.json` and `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/tpl-gptoss.html` — left behind (missing on 2026-09-20)
- input built by: Inline Python in the recorded session downloaded the checkpoint headers and wrote the tensor JSON. The exact command is recorded at `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:269`. No separate builder file was created by that command.
- sources: Downloaded config, index, and tensor-header records: left behind (missing on 2026-09-20). The public model URLs used `main`, without a pinned revision. These are checkpoint storage counts, not runtime benchmark measurements. Full per-file inventory: [weights-bytes-gpt-oss-120b.html.lineage.md](weights-bytes-gpt-oss-120b.html.lineage.md).
- regenerate: unavailable (generator, template, and downloaded input records are missing; the page also received later direct edits). regenerate unverified (missing inputs).

### weights-bytes-qwen2.5-32b.html

- generator: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gen_weights_pages.py` — left behind (missing on 2026-09-20)
- input: `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/qwen-{config,index,tensors}.json` and `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/tpl-qwen.html` — left behind (missing on 2026-09-20)
- input built by: Inline Python in the recorded session downloaded the checkpoint headers and wrote the tensor JSON. The exact command is recorded at `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:269`. No separate builder file was created by that command.
- sources: Downloaded config, index, and tensor-header records: left behind (missing on 2026-09-20). The public model URLs used `main`, without a pinned revision. These are checkpoint storage counts, not runtime benchmark measurements. Full per-file inventory: [weights-bytes-qwen2.5-32b.html.lineage.md](weights-bytes-qwen2.5-32b.html.lineage.md).
- regenerate: unavailable (generator, template, and downloaded input records are missing; the page also received later direct edits). regenerate unverified (missing inputs).

## 2026-10-16 Codex handoff preservation

This batch preserves the current canonical copies listed below. The related handoffs describe the historical chat results. A later change to a canonical document does not change those historical results. File sizes are bytes.

Standalone report generators with fixed output paths were not executed. Their entries record the reason. Existing reports whose input or generator changed were regenerated in scratch using preserved copies. The four checks matched the proposed or existing report bytes.

Files left behind are enumerated in `logs/codex-handoff-20261016-artifacts.json`. They include source checkouts, binaries, rebuildable caches, review screenshots, scheduler process files, and syntax logs summarized by retained results. The two historical humanize-writing install directories are missing. No mirror is deleted.

- Canonical root mapping: `claude-agentsrv:/home/jhan/workspace/random/` -> `artifacts/common-knowledge/random/`.

### Files

- `random/how-to-use-humafia.html` -> `claude-agentsrv:/home/jhan/workspace/random/how-to-use-humafia.html` (156994 bytes). NEW. Groups: humanfia-guide.
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/random/how-to-use-humafia.html

### random/how-to-use-humafia.html

- generator: none
- input: none
- input built by: none
- sources: none (no runtime measurement source). Per-file decisions: `artifacts/common-knowledge/random/how-to-use-humafia.html.lineage.md`.
- regenerate: none
- regenerate unverified (authored research guide; no benchmark measurements)

### Related handoffs by file group


- humanfia-guide: [codex_20261007-20261008_assess-humanfia-for-pr-4424.md](../../handoffs/codex_20261007-20261008_assess-humanfia-for-pr-4424.md).

## Codex handoff preservation — 2026-11-02

Prepared from the active Codex home on claude-agentsrv. The review report records the approval decision for this batch. Copied current source files can postdate the historical review conclusions.

This approved topic contains 8 files, 0.091 MiB. The report and companion inventories list every left-behind file. Files above 5 MiB remain at their original locations unless separately approved.

- `random/html-editor.html` -> `claude-agentsrv:/home/jhan/workspace/random/html-editor.html` (33264 bytes). application / browser test.
  Related handoffs: [codex_20261030_build-browser-html-editor.md](../../handoffs/codex_20261030_build-browser-html-editor.md).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/random/html-editor.html
- `random/html-editor/tests/test_editor.py` -> `claude-agentsrv:/home/jhan/workspace/random/html-editor/tests/test_editor.py` (16370 bytes). application / browser test.
  Related handoffs: [codex_20261030_build-browser-html-editor.md](../../handoffs/codex_20261030_build-browser-html-editor.md).
- `random/phoenix-crb-action-plan.html` -> `claude-agentsrv:/home/jhan/workspace/random/phoenix-crb-action-plan.html` (33825 bytes). report.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md), [codex_20261030_build-browser-html-editor.md](../../handoffs/codex_20261030_build-browser-html-editor.md).
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/common-knowledge/random/phoenix-crb-action-plan.html
  - generator: none
  - input: none
  - input built by: none
  - sources: `claude-agentsrv:/tmp/jeremy-tasks-20261021/snapshot.json` (preservation decisions in companion inventory). Inventory: `artifacts/common-knowledge/random/phoenix-crb-action-plan.html.lineage.md`.
  - regenerate: none
  - regenerate unverified (agent-authored plan; inspection values, no performance measurements)
  - `sources:` per-file status: 8 preserved.
- `random/phoenix-positron-perf-setup.sh` -> `claude-agentsrv:/home/jhan/workspace/random/phoenix-positron-perf-setup.sh` (3652 bytes). access script.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md).
- `random/setup-phoenix-access.ps1` -> `claude-agentsrv:/home/jhan/workspace/random/setup-phoenix-access.ps1` (2870 bytes). access script.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md).
- `random/setup-phoenix-access.sh` -> `claude-agentsrv:/home/jhan/workspace/random/setup-phoenix-access.sh` (2311 bytes). access script.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md).
- `random/verify-phoenix-access.ps1` -> `claude-agentsrv:/home/jhan/workspace/random/verify-phoenix-access.ps1` (1291 bytes). access script.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md).
- `random/verify-phoenix-access.sh` -> `claude-agentsrv:/home/jhan/workspace/random/verify-phoenix-access.sh` (1002 bytes). access script.
  Related handoffs: [codex_20261020-20261021_plan-phoenix-crb-testing.md](../../handoffs/codex_20261020-20261021_plan-phoenix-crb-testing.md).
