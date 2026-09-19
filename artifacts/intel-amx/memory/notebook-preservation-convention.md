---
name: notebook-preservation-convention
description: "How jhan's pages get preserved in github.com/jhan-positron/notebook (clone ~/workspace/notebook): copy canonical WS file to artifacts/intel-amx/<area>/, prepend the 'Rendered page' htmlpreview + raw.githack comment block at line 1, add a README batch entry with Rendered view link, commit 'Preserve artifact: ...' and push main"
metadata: 
  node_type: memory
  type: project
  originSessionId: 97fe382e-01e4-49e9-b02b-782618f409a7
  modified: 2026-09-14T02:13:57.641Z
---

jhan (2026-09-13): "update the HTML to https://github.com/jhan-positron/notebook/tree/main/artifacts/intel-amx/pr3879"
and "Make sure to insert rendered page at top, see example .../Bill-claude-review-response.html#L2".

Recipe (verified against commits 08b6e1e, 90f8e55, ca5785f):
1. Edit the CANONICAL file first (WS = ~/workspace/intel-AMX, e.g. WS/PR3879/x.html). Prepend at
   line 1 an HTML comment:
   `<!-- Rendered page (open in browser): https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/intel-amx/pr3879/x.html  Backup renderer: https://raw.githack.com/jhan-positron/notebook/main/artifacts/intel-amx/pr3879/x.html -->`
   (multi-line, same shape as Bill-claude-review-response.html lines 1-6). Keep <title> inside
   the first 8 KB for the Artifact tool.
2. `cp` into ~/workspace/notebook/artifacts/intel-amx/pr3879/ (plain copy, not a symlink;
   WS/PR3879 -> repo pr3879, WS/PR3879/new-PRs/PR0b -> repo pr3879/PR0b).
3. Append an entry to artifacts/intel-amx/README.md under a dated "## YYYY-MM-DD preservation
   batch" section: "- `pr3879/x.html` -> `WS/PR3879/x.html` — one-line description" plus an
   indented "Rendered view: <htmlpreview url>" line for HTML pages.
4. Commit as `Preserve artifact: intel-amx/<what> (<date>)` with the Co-Authored-By line, push
   origin main (jhan asked for the push explicitly this time; ask if not asked).
5. Republish the Artifact from the canonical file so artifact == repo copy.

**Why:** the notebook repo is jhan's durable archive; htmlpreview renders raw GitHub HTML, and
the header comment lets anyone opening the source find the rendered view.
**How to apply:** whenever jhan says "update the HTML to <notebook url>" or "preserve", follow
the five steps. Related: [[artifact-utf8-mojibake-trap]] (pages must be pure ASCII first),
[[workspace-ai-runs-layout]].
