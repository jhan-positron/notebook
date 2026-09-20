# Lineage inventory: weights-bytes-gpt-oss-120b.html

Short version: This inventory records identified generator inputs and upstream measurement sources. Each row states whether the exact file is preserved, proposed, or left behind. Sizes are in bytes.

- generator: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gen_weights_pages.py` — left behind (missing on 2026-09-20)
- input: `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gptoss-{config,index,tensors}.json` and `/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/tpl-gptoss.html` — left behind (missing on 2026-09-20)
- input built by: Inline Python in the recorded session downloaded the checkpoint headers and wrote the tensor JSON. The exact command is recorded at `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:269`. No separate builder file was created by that command.
- sources: Downloaded config, index, and tensor-header records: left behind (missing on 2026-09-20). The public model URLs used `main`, without a pinned revision. These are checkpoint storage counts, not runtime benchmark measurements.
- regenerate: unavailable (generator, template, and downloaded input records are missing; the page also received later direct edits). regenerate unverified (missing inputs).

Coverage: The complete scratch directory was checked and does not exist. Do not substitute new downloads for the 2026-08-23 input version. The generator reads both models, so either single-page rebuild would also require the other model inputs.

| Role | Canonical path | Repo path or reason | Bytes |
|---|---|---|---|
| generator | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gen_weights_pages.py` | left behind (missing on 2026-09-20) | unavailable |
| HTML template | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/tpl-gptoss.html` | left behind (missing on 2026-09-20) | unavailable |
| model configuration | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gptoss-config.json` | left behind (missing on 2026-09-20) | unavailable |
| checkpoint byte total and tensor/shard index | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gptoss-index.json` | left behind (missing on 2026-09-20) | unavailable |
| tensor shapes, dtypes, and byte sizes read from checkpoint headers | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/gptoss-tensors.json` | left behind (missing on 2026-09-20) | unavailable |
| HTML template | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/tpl-qwen.html` | left behind (missing on 2026-09-20) | unavailable |
| model configuration | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/qwen-config.json` | left behind (missing on 2026-09-20) | unavailable |
| checkpoint byte total and tensor/shard index | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/qwen-index.json` | left behind (missing on 2026-09-20) | unavailable |
| tensor shapes, dtypes, and byte sizes read from checkpoint headers | `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f/scratchpad/qwen-tensors.json` | left behind (missing on 2026-09-20) | unavailable |

Evidence:
- `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:259`
- `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:269`
- `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:270`
- `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:377`
- `/home/jhan/.claude/projects/-home-jhan-workspace-notebook/d476fbee-fdd0-4d28-aa39-5857b37fed9f.jsonl:407`
