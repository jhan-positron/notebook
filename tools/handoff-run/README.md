# tools/handoff-run

Scripts used by the 2026-09-20 `SCOPE: auto` run of `claude-handoff-generation-prompt.md` on claude-agentsrv. They are first-class repo files, not mirrors. Each takes output paths as arguments and writes nothing into the notebook.

- `scan.py OUT_SCAN.json OUT_RECONCILE.json`: reads every handoff header under `handoffs/` and every transcript under `~/.claude/projects/`, converts timestamps to Pacific dates, and reconciles them (update, unchanged, frozen, missing transcript, rename, new).
- `registry2.py OUT.json`: maps every file under `artifacts/<topic>/` to its canonical path (layout rule first for intel-amx, then README pairing with a basename check) and compares contents; one batched `md5sum` over ssh for delphi-3bda paths.
- `lineage.py OUT.json`: parses the `source_files` citations of `mirror-vs-vnni-rows.json`, expands brace lists and sibling shorthand, and classifies each cited file under Step 4b (class, size, measured-line override tested on the cited lines' content, duplicate check on the `[Request N]` payload).
- `gate.py LINEAGE.json OUT_DIR`: writes the `computed-from:` gate text, the inventory `<page>.lineage.md`, and `proposal.json`.

The classifier is specific to the runtron and CI-harness file layout of the intel-AMX project. A new page needs its own citation parser but can reuse the class and duplicate tests.
