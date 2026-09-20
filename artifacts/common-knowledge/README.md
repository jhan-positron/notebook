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
