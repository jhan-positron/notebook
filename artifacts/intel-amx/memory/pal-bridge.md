---
name: pal-bridge
description: "How to call PAL MCP (gpt-6-astra, gpt-5.6-sol etc.) from this machine, its gotchas, and the local model-registry override for models PAL's bundled registry lacks"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 3a96feab-43b5-493a-97f2-e9a59a459e74
  modified: 2026-09-05T00:36:51.080Z
---

PAL = MCP server bridging to external models. Bridge client: /home/jhan/bin/pal_mcp_client.py
(spawns `uvx --from git+https://github.com/positron-mark/pal-mcp-server.git pal-mcp-server`).
Usage: `PAL_TIMEOUT=1200 python3 ~/bin/pal_mcp_client.py chat - <<'EOF' {json args} EOF`
chat args: prompt, model (e.g. "gpt-5.6-sol"), working_directory_absolute_path (required),
absolute_file_paths (server reads local files), thinking_mode (minimal..max), temperature.
Tools: chat, consensus, thinkdeep, codereview, listmodels, ...

Gotcha: each bridge invocation spawns a FRESH server process, so continuation_id does NOT
survive across calls — always send self-contained prompts and attach prior replies as files.
Run calls with run_in_background (they take 3-8 min at thinking_mode=high).
Configured providers (2026-08): OpenAI (gpt-5.6-sol/terra/luna, 5.5, codex...) and
Anthropic (fable/opus/sonnet). Used for [[amx-tron-softattn-project]] consensus reviews.

Workaround (2026-08-20, during [[claude-box-pid-exhaustion]]): when uvx's git update fails
("cannot fork"), use the patched client scratchpad/pal_client_local.py which points --from at
the newest cached checkout ~/.cache/uv/git-v0/checkouts/28e8dfa9b7e49f81/<newest>/ instead of
git+https. Same usage otherwise. Falls behind upstream until the container is fixed.

gpt-6-astra (2026-09-04): PAL's bundled OpenAI registry (positron-mark fork, head f9170d4 of
2026-07-31; the 5.6 entries are Positron additions, the original BeehiveInnovations registry
stops at gpt-5.2) does not list gpt-6-astra, and PAL rejects model names outside its registry
(providers/openai_compatible.py validate_model_name), although the OpenAI key sees gpt-6-astra
in /v1/models. Fix: local registry copy ~/bin/pal_openai_models.json (= upstream
conf/openai_models.json + a gpt-6-astra entry cloned from gpt-5.6-sol; aliases gpt-6, gpt6, 6,
astra), selected per call with OPENAI_MODELS_CONFIG_PATH=$HOME/bin/pal_openai_models.json.
Verified 2026-09-04: listmodels shows it (105 models), a chat call ran on gpt-6-astra.
The entry's context/output limits are COPIED from gpt-5.6-sol, unverified. Making the client
set that env var by default was proposed to jhan, not applied (classifier blocked the edit).
Re-merge the file when upstream updates the registry.

File budget (2026-09-04): PAL rejects a chat call whose attached files exceed ~268,800 estimated tokens ("code_too_large", 80% threshold of its allocation, independent of the 1.05M context) - a 24-file set of docs + diff + 11 source headers (317K) failed; docs + diff + 6 small sources (19 files) passed. Attach the large headers only when the question needs them.

UPDATE 2026-09-07: helper scripts now in the repo, ~/workspace/intel-AMX/exec/pal/ask.sh <name> <prompt.md> [files...] (detached; output
/var/tmp/jhan/pal-out/<name>.raw) and exec/pal/collect.sh <name> (-> .md). The scratchpad copies were lost in a container restart; keep
helpers in the repo, inputs under /var/tmp/jhan/pal-in/.
Gotcha (2026-09-07): PAL answers "files_required_to_continue ... NO FILES FOUND" when an attached path is not below
working_directory_absolute_path. exec/pal/ask.sh now sets the working directory to the common parent of the prompt and the attachments;
keep them together under one directory (e.g. /var/tmp/jhan/pal-in/<topic>/).
