# Dev-Machine Artifacts

Preserved tools and configuration from the development-VM comparison and the
claude-dev container migration (alpha -> sw-dev-01 -> agentsrv, 2026-08-27).
Repo copies are mirrors: edit the canonical files first, then refresh these
copies during the next handoff run. All canonicals are on host claude-agentsrv.

- `loadmon/sample.sh` — canonical `claude-agentsrv:/home/jhan/workspace/random/loadmon/sample.sh` — periodic load sampler used for the 24-hour alpha vs sw-dev-01 comparison. (handoff: claude_20260824-20260825_sw-server-1-dev-server-name-lookup.md)
- `loadmon/analyze.py` — canonical `claude-agentsrv:/home/jhan/workspace/random/loadmon/analyze.py` — load-sample analyzer. (handoff: claude_20260824-20260825_sw-server-1-dev-server-name-lookup.md)
- `loadmon/build_report.py` — canonical `claude-agentsrv:/home/jhan/workspace/random/loadmon/build_report.py` — HTML report builder for the load comparison. (handoff: claude_20260824-20260825_sw-server-1-dev-server-name-lookup.md)
- `loadmon/report.html` — canonical `claude-agentsrv:/home/jhan/workspace/random/loadmon/report.html` — the 24-hour load-comparison report (recommendation: stay on alpha). (handoff: claude_20260824-20260825_sw-server-1-dev-server-name-lookup.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/loadmon/report.html
- `sw-dev-01-setup.sh` — canonical `claude-agentsrv:/home/jhan/sw-dev-01-setup.sh` — one-shot setup script for running the claude-dev container on sw-dev-01. (handoff: claude_20260827-20260828_claude-box-container-migration-to-sw-dev-01.md)
- `claude-box` — canonical `claude-agentsrv:/home/jhan/claude-container/claude-box` — wrapper script that starts/enters the claude-dev podman container. (handoff: claude_20260827-20260828_claude-box-container-migration-to-sw-dev-01.md)
- `storage-sw-dev-01.conf` — canonical `claude-agentsrv:/home/jhan/.config/containers/storage-sw-dev-01.conf` — podman storage configuration used for the sw-dev-01 variant. (handoff: claude_20260827-20260828_claude-box-container-migration-to-sw-dev-01.md)

- `copy-container.md` — canonical `claude-agentsrv:/home/jhan/tmp/copy-container.md`
  — verified Markdown guide to separate Codex app-connection startup failures
  from the missing-bubblewrap warning; despite its filename, it is not a
  container-copy recipe. Originally written on claude-alpha on 2026-08-25.
  (handoff: `handoffs/codex_20260819-20260825_can-you-access-my-notion-pages.md`)

- `delphi-3bda-setup.sh` — canonical `claude-agentsrv:/home/jhan/delphi-3bda-setup.sh` — shell setup sourced before using delphi-3bda: sets `SYSTEM_CONFIG="--instance 1,2"` (jhan's half of the FPGA cards) and `GUARD_EXCLUDE_USERS` for the campaign guard. Added by the 2026-09-11 handoff run. (handoff: claude_20260906_delphi-3bda-guard-doc-in-handoffs.md)


## Codex handoff preservation — 2026-09-18

Canonical files remain authoritative. This batch preserves authored documents, scripts, and compact audit results. Raw logs, source archives, binaries, and browser captures stay at their original locations.

HTML pages retain their canonical workspace evidence links. The mirrors preserve the authored pages but do not make the entire source and raw-data tree available offline. Historical installers require their recorded preconditions and paths.

| Preserved file | Canonical location | Purpose and related handoff |
|---|---|---|
| [migrate-codex-home.py](migrate-codex-home.py) | `claude-agentsrv:/home/jhan/claude-container/migrate-codex-home.py` | Container migration and build support. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [CODEX-HOME-MIGRATION.md](CODEX-HOME-MIGRATION.md) | `claude-agentsrv:/home/jhan/claude-container/CODEX-HOME-MIGRATION.md` | Container migration and build support. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [Containerfile](Containerfile) | `claude-agentsrv:/home/jhan/claude-container/Containerfile` | Container migration and build support. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [codex-home-migration/test_migrate_index.py](codex-home-migration/test_migrate_index.py) | `claude-agentsrv:/home/jhan/workspace/random/codex-home-migration/test_migrate_index.py` | Migration test suite and its sibling inputs. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [codex-home-migration/test_launcher.py](codex-home-migration/test_launcher.py) | `claude-agentsrv:/home/jhan/workspace/random/codex-home-migration/test_launcher.py` | Migration test suite and its sibling inputs. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [codex-home-migration/migrate-index.py](codex-home-migration/migrate-index.py) | `claude-agentsrv:/home/jhan/workspace/random/codex-home-migration/migrate-index.py` | Migration test suite and its sibling inputs. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [codex-home-migration/claude-box.proposed](codex-home-migration/claude-box.proposed) | `claude-agentsrv:/home/jhan/workspace/random/codex-home-migration/claude-box.proposed` | Migration test suite and its sibling inputs. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
| [codex-home-migration/README.md](codex-home-migration/README.md) | `claude-agentsrv:/home/jhan/workspace/random/codex-home-migration/README.md` | Migration test suite and its sibling inputs. Related: [codex_20260912-20260913_find-cpp-coding-guide-skill-files.md](../../handoffs/codex_20260912-20260913_find-cpp-coding-guide-skill-files.md). |
- `github-reviewer-removals-scan.sh` — canonical `claude-agentsrv:/home/jhan/workspace/random/exec/workflows/github-reviewer-removals-scan.sh` (workspace canonical after the approved relocation; original scratchpad path recorded below) — paginated GitHub GraphQL scanner for ReviewRequestRemovedEvent across positron-ai/tron PRs. Registered 2026-09-18. (handoffs: claude_20260915_alexey-reviewer-removals-across-prs.md)

## Generated-report lineage backfill (2026-09-20)

These entries record the source inventory and regeneration limits for existing report pages. Canonical files remain authoritative. Companion inventories are repo-primary metadata.

### Source files

| Repo path | Canonical path | Role | Bytes |
|---|---|---|---|
| [`loadmon/alpha.csv`](loadmon/alpha.csv) | `claude-agentsrv:/home/jhan/workspace/random/loadmon/alpha.csv` | source | 25886 |
| [`loadmon/summary.json`](loadmon/summary.json) | `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json` | input | 80188 |
| [`loadmon/sw-dev-01.csv`](loadmon/sw-dev-01.csv) | `claude-agentsrv:/home/jhan/workspace/random/loadmon/sw-dev-01.csv` | source | 28756 |

### loadmon/report.html

- generator: `artifacts/dev-machines/loadmon/build_report.py`
- input: `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json`
- input built by: `artifacts/dev-machines/loadmon/analyze.py`
- sources: `claude-agentsrv:/home/jhan/workspace/random/loadmon/alpha.csv` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/random/loadmon/summary.json` (1 proposed preservation); `claude-agentsrv:/home/jhan/workspace/random/loadmon/sw-dev-01.csv` (1 proposed preservation). Full per-file inventory: [loadmon/report.html.lineage.md](loadmon/report.html.lineage.md).
- regenerate: unavailable; build_report.py has no output-path argument and unconditionally writes a session scratchpad path as well as report.html.

- Session-store relocation: `artifacts/dev-machines/github-reviewer-removals-scan.sh` now points to `claude-agentsrv:/home/jhan/workspace/random/exec/workflows/github-reviewer-removals-scan.sh`; origin `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-random/8fe7ef6d-8594-4265-8524-a6107e65c691/scratchpad/scan.sh`. Bytes unchanged; relocation requires approval.

## 2026-10-16 Codex handoff preservation

This batch preserves the current canonical copies listed below. The related handoffs describe the historical chat results. A later change to a canonical document does not change those historical results. File sizes are bytes.

Standalone report generators with fixed output paths were not executed. Their entries record the reason. Existing reports whose input or generator changed were regenerated in scratch using preserved copies. The four checks matched the proposed or existing report bytes.

Files left behind are enumerated in `logs/codex-handoff-20261016-artifacts.json`. They include source checkouts, binaries, rebuildable caches, review screenshots, scheduler process files, and syntax logs summarized by retained results. The two historical humanize-writing install directories are missing. No mirror is deleted.

- Canonical root mapping: `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/` -> `artifacts/dev-machines/amx-ci-monitor/`.

### Files

- `amx-ci-monitor/README.html` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/README.html` (4081 bytes). NEW. Groups: amx-ci-monitor.
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/amx-ci-monitor/README.html
- `amx-ci-monitor/check.py` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/check.py` (6650 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/config.json` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/config.json` (66 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/fetch-prompt.txt` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/fetch-prompt.txt` (1417 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/fetch-schema.json` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/fetch-schema.json` (382 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/run.sh` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/run.sh` (251 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/schedule.cron` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/schedule.cron` (96 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/send-schema.json` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/send-schema.json` (231 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/start-cron.sh` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/start-cron.sh` (456 bytes). NEW. Groups: amx-ci-monitor.
- `amx-ci-monitor/test_check.py` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/test_check.py` (4393 bytes). NEW. Groups: amx-ci-monitor.
- `claude-box` -> `claude-agentsrv:/home/jhan/claude-container/claude-box` (12543 bytes). REFRESH. Groups: registered-refresh.
- `sw-dev-01-setup.sh` -> `claude-agentsrv:/home/jhan/sw-dev-01-setup.sh` (806 bytes). REFRESH. Groups: registered-refresh.

### Related handoffs by file group

- amx-ci-monitor: [codex_20260925_schedule-daily-amx-monitoring.md](../../handoffs/codex_20260925_schedule-daily-amx-monitoring.md), [codex_20261009_add-amx-alert-expected-ranges.md](../../handoffs/codex_20261009_add-amx-alert-expected-ranges.md).
- registered-refresh: [codex_20261016_follow-codex-handoff-prompt.md](../../handoffs/codex_20261016_follow-codex-handoff-prompt.md).

## Batch: 2026-10-16 SCOPE:auto run (Claude, claude-agentsrv)

Registered by the 2026-10-16 `SCOPE: auto` handoff run of claude-handoff-generation-prompt.md. `claude-agentsrv` is the podman container on the dev server `agentsrv` (same home directory). Repo path -> canonical path (bytes). Canonical -> repo; edit the canonical file first.

New prefix this batch: `herdr-config/` mirrors `claude-agentsrv:/home/jhan/.config/herdr/` (the herdr terminal multiplexer configuration and session records).

- `agentsrv-setup.sh` -> `claude-agentsrv:/home/jhan/agentsrv-setup.sh` (2015 bytes). host login script that enters the claude-box container and starts herdr (2026-10-03 and 2026-10-04 versions). (handoff: [claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md](../../handoffs/claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md))
- `agentsrv-setup.sh.bak-20261003` -> `claude-agentsrv:/home/jhan/agentsrv-setup.sh.bak-20261003` (1055 bytes). host login script that enters the claude-box container and starts herdr (2026-10-03 and 2026-10-04 versions). (handoff: [claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md](../../handoffs/claude_20261003_agentsrv-setup-sh-claude-box-path-and-herdr-conversations.md))
- `agentsrv-setup.sh.bak-20261004` -> `claude-agentsrv:/home/jhan/agentsrv-setup.sh.bak-20261004` (1770 bytes). host login script that enters the claude-box container and starts herdr (2026-10-03 and 2026-10-04 versions). (handoff: [claude_20261004_herdr-shell-prompt-and-tab-completion.md](../../handoffs/claude_20261004_herdr-shell-prompt-and-tab-completion.md))
- `claude-box.bak-shell-env-20261004T183916Z` -> `claude-agentsrv:/home/jhan/claude-container/claude-box.bak-shell-env-20261004T183916Z` (12228 bytes). claude-box wrapper before the `-e SHELL=/bin/bash` change of 2026-10-04. (handoff: [claude_20261004_herdr-shell-prompt-and-tab-completion.md](../../handoffs/claude_20261004_herdr-shell-prompt-and-tab-completion.md))
- `herdr-config/config.toml` -> `claude-agentsrv:/home/jhan/.config/herdr/config.toml` (231 bytes). herdr configuration (shell prompt fix of 2026-10-04). (handoff: [claude_20261004_herdr-shell-prompt-and-tab-completion.md](../../handoffs/claude_20261004_herdr-shell-prompt-and-tab-completion.md))
- `herdr-config/config.toml.bak-20261004` -> `claude-agentsrv:/home/jhan/.config/herdr/config.toml.bak-20261004` (45 bytes). herdr configuration (shell prompt fix of 2026-10-04). (handoff: [claude_20261004_herdr-shell-prompt-and-tab-completion.md](../../handoffs/claude_20261004_herdr-shell-prompt-and-tab-completion.md))
- `herdr-config/session.json` -> `claude-agentsrv:/home/jhan/.config/herdr/session.json` (2943 bytes). herdr session record. (handoff: [claude_20261003_duplicate-herdr-server-processes.md](../../handoffs/claude_20261003_duplicate-herdr-server-processes.md))
- `herdr-config/sessions/claude-agentsrv/session.json` -> `claude-agentsrv:/home/jhan/.config/herdr/sessions/claude-agentsrv/session.json` (10576 bytes). herdr session record. (handoff: [claude_20261003_duplicate-herdr-server-processes.md](../../handoffs/claude_20261003_duplicate-herdr-server-processes.md))

## Codex handoff preservation — 2026-11-02

Prepared from the active Codex home on claude-agentsrv. The review report records the approval decision for this batch. Copied current source files can postdate the historical review conclusions.

This approved topic contains 1 files, 0.015 MiB. The report and companion inventories list every left-behind file. Files above 5 MiB remain at their original locations unless separately approved.

Left behind in this batch:

- `claude-agentsrv:/home/jhan/workspace/intel-AMX/rampup/operand-B.html`: left behind (content conflict: retain repository contents section from 71fc29c pending user decision), 76093 bytes.

- `herdr-config/sessions/claude-agentsrv/session.json` -> `claude-agentsrv:/home/jhan/.config/herdr/sessions/claude-agentsrv/session.json` (15562 bytes). registered artifact.

## Batch: 2026-11-02 SCOPE:auto run (Claude, claude-agentsrv)

Registered by the 2026-11-02 `SCOPE: auto` handoff run of claude-handoff-generation-prompt.md. `claude-agentsrv` is the podman container on the dev server `agentsrv` (same home directory, same files). Repo path -> canonical path (bytes). Canonical -> repo; edit the canonical file first. New prefixes this batch: `scratch-prune-20261020/` mirrors `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/` (the review and deletion records of the 2026-10-20 /scratch/jhan prune; `scratch-prune-20261020/scratchpad/` holds files relocated there from that session's scratchpad under `/tmp/claude-0/`), and `notebook-memory/` mirrors `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-notebook/memory/` (the canonical stays in the session store because Claude Code edits it in place). `herdr-config/sessions/claude-agentsrv/session.json` was refreshed from its canonical in the same run (a live session record; 13 lines changed).

Covers 1 handoff(s) of 2026-10-16 to 2026-11-02 (see "Related" on each entry). Preserved: 36 files, 6.15 MiB in this topic. Left behind by rule 4 of the prompt for the handoffs of this topic, one reason per file (full per-file inventories in the `.lineage.md` companions named under each report page):

- (provenance: raw workflow output): 7 files
- (size): 6 files
- (regenerable: listing of the notebook repository itself): 5 files
- (no value used: empty file): 4 files
- (duplicate (ai-runs/scratch-prune-20261020/tools/breakdown.py)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/tools/build_page.py)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/data/deleted-dirs-20261021.txt)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/data/deleted-pftrace-20261021.txt)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/data/du-top-after-20261021.tsv)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/data/du-top-20261021.tsv)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/data/notebook-mirror-mapping.json)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/tools/match.py)): 1 files
- (duplicate (ai-runs/scratch-prune-20261020/tools/numbers.py)): 1 files
- `no value used` = files under `leaves/` result trees. `scratch directory >60 files` = agent batch trees under session scratchpads. `provenance` = server logs, client streams, .done markers, binaries, raw workflow outputs, subagent journals. `size` = files above 5 MiB. `regenerable: render check PNG` = PNG renders of inline-SVG pages. `scratchpad file not named in the handoff` = files of directory-listed session scratchpads that no handoff names individually. `duplicate` = a copy already held elsewhere (named). `pdftotext extract of a vendor manual`, `text dump of a preserved page`, `directory listing` = rebuilt in minutes from the PDF, the page, or the tree.

### Report pages and their lineage

#### scratch-prune-20261020/scratch-jhan-prune-review.html

- mirror of `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratch-jhan-prune-review.html` (47198 canonical bytes). Related: [claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md](../../handoffs/claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/scratch-prune-20261020/scratch-jhan-prune-review.html
- generator: tools/build_page.py in the output folder (writes page.html, scratch-jhan-prune-review.html, reply-to-mitchell.txt, figures.json); the 22:18 status block and the 22:48 update paragraph were patched in by inline Python in the transcript, not saved as scripts
- input: /tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/data.json
- input built by: tools/numbers.py from the scratchpad listings 3bda-scratch-files.tsv, 3bda-ondisk.tsv, du-top.tsv and the md5 files repo-md5.txt, remote-md5.clean.txt, doccheck-md5.txt, fullcheck-md5.txt (listings kept gzipped under data/)
- sources: `find and du over /scratch/jhan on delphi-3bda`: not a local file (code state, URL or text); `git ls-files and md5sum over /home/jhan/workspace/notebook`: not a local file (code state, URL or text); `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/notebook-mirror-mapping.json`: preserved notebook-mirror-mapping.json; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/scratch-jhan-files-20261021.tsv.gz`: nothing preserved; left behind (size) scratch-jhan-files-20261021.tsv.gz; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/scratch-jhan-ondisk-20261021.tsv.gz`: nothing preserved; left behind (size) scratch-jhan-ondisk-20261021.tsv.gz; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/du-top-20261021.tsv`: preserved du-top-20261021.tsv
- regenerate: python3 -I /home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/numbers.py <SP> <SP>/data.json && python3 -I /home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/build_page.py <SP> /home/jhan/workspace/ai-runs/scratch-prune-20261020 (SP = the scratchpad; rebuilds version 1 only, the two later patches must be reapplied by hand)
- regenerate verified 2026-11-02 (byte-identical from the preserved copies)
- inventory: [scratch-jhan-prune-review.html.lineage.md](scratch-prune-20261020/scratch-jhan-prune-review.html.lineage.md) (5 lines)

#### scratch-prune-20261020/page.html

- mirror of `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/page.html` (47038 canonical bytes). Related: [claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md](../../handoffs/claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/scratch-prune-20261020/page.html
- generator: tools/build_page.py in the output folder (writes page.html, scratch-jhan-prune-review.html, reply-to-mitchell.txt, figures.json); the 22:18 status block and the 22:48 update paragraph were patched in by inline Python in the transcript, not saved as scripts
- input: /tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/data.json
- input built by: tools/numbers.py from the scratchpad listings 3bda-scratch-files.tsv, 3bda-ondisk.tsv, du-top.tsv and the md5 files repo-md5.txt, remote-md5.clean.txt, doccheck-md5.txt, fullcheck-md5.txt (listings kept gzipped under data/)
- sources: `find and du over /scratch/jhan on delphi-3bda`: not a local file (code state, URL or text); `git ls-files and md5sum over /home/jhan/workspace/notebook`: not a local file (code state, URL or text); `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/notebook-mirror-mapping.json`: preserved notebook-mirror-mapping.json; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/scratch-jhan-files-20261021.tsv.gz`: nothing preserved; left behind (size) scratch-jhan-files-20261021.tsv.gz; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/scratch-jhan-ondisk-20261021.tsv.gz`: nothing preserved; left behind (size) scratch-jhan-ondisk-20261021.tsv.gz; `/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/du-top-20261021.tsv`: preserved du-top-20261021.tsv
- regenerate: python3 -I /home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/numbers.py <SP> <SP>/data.json && python3 -I /home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/build_page.py <SP> /home/jhan/workspace/ai-runs/scratch-prune-20261020 (SP = the scratchpad; rebuilds version 1 only, the two later patches must be reapplied by hand); page.html is the same page without the doctype/html/head/body wrapper, published as https://claude.ai/artifact/M8kTS2bFC4HKRiKXFedQqd
- regenerate verified 2026-11-02 (byte-identical from the preserved copies)
- inventory: [page.html.lineage.md](scratch-prune-20261020/page.html.lineage.md) (5 lines)

### All files of this batch

Repo path -> canonical path (bytes). `origin:` = the session-store or scratchpad path a relocated file was copied from (history only, never fetched again).

Related: [claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md](../../handoffs/claude_20261020_scratch-jhan-cleanup-and-archived-notebooks.md)

- `notebook-memory/MEMORY.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-notebook/memory/MEMORY.md` (1051 bytes)
- `notebook-memory/scratch-jhan-prune-review-2026-10.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-notebook/memory/scratch-jhan-prune-review-2026-10.md` (3456 bytes)
- `notebook-memory/tron-worktree-prune-trap.md` -> `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-notebook/memory/tron-worktree-prune-trap.md` (1332 bytes)
- `scratch-prune-20261020/data/deleted-dirs-20261021.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/deleted-dirs-20261021.txt` (1498 bytes)
- `scratch-prune-20261020/data/deleted-pftrace-20261021.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/deleted-pftrace-20261021.txt` (55914 bytes)
- `scratch-prune-20261020/data/du-top-20261021.tsv` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/du-top-20261021.tsv` (4109 bytes)
- `scratch-prune-20261020/data/du-top-after-20261021.tsv` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/du-top-after-20261021.tsv` (3876 bytes)
- `scratch-prune-20261020/data/notebook-mirror-mapping.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/data/notebook-mirror-mapping.json` (4746432 bytes)
- `scratch-prune-20261020/deletion-log-20261021.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/deletion-log-20261021.txt` (4707 bytes)
- `scratch-prune-20261020/figures.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/figures.json` (8629 bytes)
- `scratch-prune-20261020/reply-to-mitchell.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/reply-to-mitchell.txt` (629 bytes)
- `scratch-prune-20261020/scratchpad/3bda-big-files.tsv` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/3bda-big-files.tsv` (189004 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/3bda-big-files.tsv`
- `scratch-prune-20261020/scratchpad/3bda-detail.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/3bda-detail.txt` (8569 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/3bda-detail.txt`
- `scratch-prune-20261020/scratchpad/3bda-overview.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/3bda-overview.txt` (17361 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/3bda-overview.txt`
- `scratch-prune-20261020/scratchpad/breakdown.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/breakdown.txt` (15822 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/breakdown.txt`
- `scratch-prune-20261020/scratchpad/data.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/data.json` (497799 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/data.json`
- `scratch-prune-20261020/scratchpad/delete-set.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/delete-set.json` (59623 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/delete-set.json`
- `scratch-prune-20261020/scratchpad/delete-story2814.log` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/delete-story2814.log` (305 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/delete-story2814.log`
- `scratch-prune-20261020/scratchpad/delete.log` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/delete.log` (4378 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/delete.log`
- `scratch-prune-20261020/scratchpad/delete.sh` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/delete.sh` (1652 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/delete.sh`
- `scratch-prune-20261020/scratchpad/doccheck-md5.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/doccheck-md5.txt` (223563 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/doccheck-md5.txt`
- `scratch-prune-20261020/scratchpad/doccheck-rel.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/doccheck-rel.txt` (144139 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/doccheck-rel.txt`
- `scratch-prune-20261020/scratchpad/doccheck-result.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/doccheck-result.json` (161824 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/doccheck-result.json`
- `scratch-prune-20261020/scratchpad/du-after2.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/du-after2.txt` (23 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/du-after2.txt`
- `scratch-prune-20261020/scratchpad/match-summary.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/match-summary.txt` (11117 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/match-summary.txt`
- `scratch-prune-20261020/scratchpad/mirror-diffs.json` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/mirror-diffs.json` (2 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/mirror-diffs.json`
- `scratch-prune-20261020/scratchpad/remote-md5.clean.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/remote-md5.clean.txt` (61578 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/remote-md5.clean.txt`
- `scratch-prune-20261020/scratchpad/remote-md5.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/remote-md5.txt` (64915 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/remote-md5.txt`
- `scratch-prune-20261020/scratchpad/story2814-copy-list.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/story2814-copy-list.txt` (3726 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/story2814-copy-list.txt`
- `scratch-prune-20261020/scratchpad/story2814-src.md5` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/scratchpad/story2814-src.md5` (5018 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook/ed984320-0dc3-4cf4-9154-84af93c2a407/scratchpad/story2814-src.md5`
- `scratch-prune-20261020/tools/breakdown.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/breakdown.py` (1642 bytes)
- `scratch-prune-20261020/tools/build_page.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/build_page.py` (36945 bytes)
- `scratch-prune-20261020/tools/match.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/match.py` (5634 bytes)
- `scratch-prune-20261020/tools/numbers.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/scratch-prune-20261020/tools/numbers.py` (4320 bytes)


## Batch: 2026-11-06 SCOPE:auto run (Claude, claude-agentsrv)

Registered by the 2026-11-06 `SCOPE: auto` handoff run of claude-handoff-generation-prompt.md. `claude-agentsrv` is the podman container on the dev server `agentsrv` (same home directory, same files). Repo path -> canonical path (bytes). Canonical -> repo; edit the canonical file first. Mappings as before.

Refreshed from their canonical files on 2026-11-06 (registered earlier, content changed since): `herdr-config/sessions/claude-agentsrv/session.json`, `notebook-memory/MEMORY.md`.

## Codex handoff preservation, 2026-11-20

Each path below is relative to this topic. Original files are on claude-agentsrv unless a different host is given.

- `amx-ci-monitor/README.html` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/README.html` (4383 mirror bytes).
  - [Rendered page](https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/amx-ci-monitor/README.html)
- `amx-ci-monitor/check.py` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/check.py` (6650 mirror bytes).
- `amx-ci-monitor/test_check.py` -> `claude-agentsrv:/home/jhan/workspace/random/amx-ci-monitor/test_check.py` (4393 mirror bytes).
- `herdr-config/config.toml` -> `claude-agentsrv:/home/jhan/.config/herdr/config.toml` (440 mirror bytes).
- `herdr-config/sessions/claude-agentsrv/session.json` -> `claude-agentsrv:/home/jhan/.config/herdr/sessions/claude-agentsrv/session.json` (14689 mirror bytes).

### Related handoffs


## Batch: 2026-11-25 SCOPE:auto run (Claude, claude-agentsrv)

Registered by the 2026-11-25 `SCOPE: auto` handoff run of claude-handoff-generation-prompt.md. `claude-agentsrv` is the podman container on the dev server `agentsrv` (same home directory, same files). Repo path -> canonical path (bytes). Canonical -> repo; edit the canonical file first. `herdr-config/` -> `claude-agentsrv:/home/jhan/.config/herdr/`. `ai-runs/handoff-relocated/` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/` (files relocated from sessions whose project has no canonical root; their `origin:` is recorded). New prefixes in this batch: `machines/arm-crb/` -> `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/`, `agent-cpu-guard/` -> `claude-agentsrv:/home/jhan/.config/agent-cpu-guard/`, `claude-config/` -> `claude-agentsrv:/home/jhan/.claude/` (one file, `statusline-command.sh`).

Refreshed from their canonical files on 2026-11-25 (registered earlier, content changed since): `herdr-config/sessions/claude-agentsrv/session.json`.

Covers 6 handoff(s) written or updated on 2026-11-25 (see "Related" on each entry). Preserved: 23 files, 0.26 MiB in this topic. Files of these handoffs that were not copied, one reason per file (the per-file inventories are in the `.lineage.md` companions named under each report page):

- (provenance): 141 files
- held back at the gate (identity capture or raw export, no explicit yes): 49 files
- (no value used: empty file): 34 files
- (private configuration: not copied into a public repository): 8 files
- (on ubuntu: directory or size not recorded, not fetched): 8 files
- (provenance: raw workflow output): 2 files
- (provenance: tool output of the session store): 2 files
- (vendor material: not copied into a public repository): 2 files
- (on delphi-3b35: directory or size not recorded, not fetched): 2 files
- (pre-edit copy of a file preserved at its current state): 2 files
- (on 192.168.2.45: directory or size not recorded, not fetched): 2 files
- (symbolic link to /home/jhan/.codex/skills/inter-agent-review-loop): 1 files
- (duplicate (artifacts/titan/cache-perf/crb/tmp/agent-scratch/bwx13-2026-11-15/ref-bwx12/listing.txt)): 1 files
- (uncommitted file of the git checkout /home/jhan/workspace/ai-proj: that repository preserves it once it is committed): 1 files
- (on the CRB: a login there needs the block check first, not fetched): 1 files

Reason names: `provenance` = logs, compiled binaries, .pyc files, raw workflow outputs and other rule-4 classes of the prompt. `size` = a file above 5 MiB. `regenerable` = a command rebuilds the file. `duplicate (<repo path>)` = the same bytes are already held at that repo path. `vendor material` and `private configuration` = not copied while the repository is public. `held back at the gate` = identity captures of machines (firmware, DMI, sudo rules, process lists) and raw exports of private sources, proposed at the gate and not approved by an explicit yes.

### Report pages and their lineage

#### machines/arm-crb/DIMM-flaky-report.md

- mirror of `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md` (25363 canonical bytes). Related: [claude_20261115-20261117_whole-chip-throughput-drop-with-new-test-kernel.md](../../handoffs/claude_20261115-20261117_whole-chip-throughput-drop-with-new-test-kernel.md)
- generator: none (written with the Write tool, then patched by inline Python and sed commands)
- input: none
- input built by: none
- sources: `/home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117`: nothing preserved; held back at the gate (identity capture or raw export, no explicit yes) dmi16-19.txt, dmi17-062957.txt, h-1.txt, h-10.txt, h-11.txt, h-2.txt ...; `/home/jhan/workspace/titan/cache-perf/crb/results/dimm7200-20261117`: preserved boots.txt, gaps.txt, hwerr-final.txt, lastlines.txt, set.txt, setting-final.txt, try1.txt, try2.txt, try3.txt, try4.txt, try5.txt, try6.txt ...; held back at the gate (identity capture or raw export, no explicit yes) dmi17-7200.txt, dmi2.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/uefisettings-20261117`: nothing preserved; held back at the gate (identity capture or raw export, no explicit yes) identify.txt, ifr.txt, questions.json; left behind (no value used: empty file) ifr.err, questions.err; `/home/jhan/workspace/titan/cache-perf/crb/results/fwtest-20261117`: preserved boot_id.txt, cmdline.txt, gov.txt, hii-get.txt, huge.txt, ip.txt, lsmod.txt, mounts.txt, online.txt, questions.json, services.txt, set.txt ...; held back at the gate (identity capture or raw export, no explicit yes) bios.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/dmidecode-t17-2026-10-30.txt`: preserved dmidecode-t17-2026-10-30.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-R8-20261117T020549Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-BASEd10-20261117T041738Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-X2d12-20261117T040922Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-X1d10-20261117T034916Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-X1d10b-20261117T040407Z`: preserved a6400.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-w120-F72d12-20261117T200231Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-w120-F72d12g-20261117T200504Z`: preserved env.txt, g_asm_asm.m0.csv, g_asm_asm.m1.csv, g_asm_nop256.m0.csv, g_asm_nop256.m1.csv, g_nop256_asm.m0.csv, g_nop256_asm.m1.csv, g_nop256_nop256.m0.csv, g_nop256_nop256.m1.csv, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/gitlab-profile/CHANGELOG.md`: nothing preserved; left behind (vendor material: not copied into a public repository) CHANGELOG.md; `/home/jhan/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf`: nothing preserved; left behind (vendor material: not copied into a public repository) Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf
- regenerate: none
- regenerate unverified (no generator: the page was written or edited directly)
- inventory: [DIMM-flaky-report.md.lineage.md](machines/arm-crb/DIMM-flaky-report.md.lineage.md) (137 lines)

#### machines/arm-crb/arm-support-case-20261117/email-to-arm-support.html

- mirror of `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/arm-support-case-20261117/email-to-arm-support.html` (31839 canonical bytes). Related: [claude_20261117-20261119_arm-support-email-for-dimm-flaky-report-md.md](../../handoffs/claude_20261117-20261119_arm-support-email-for-dimm-flaky-report-md.md)
  Rendered view: https://htmlpreview.github.io/?https://github.com/jhan-positron/notebook/blob/main/artifacts/dev-machines/machines/arm-crb/arm-support-case-20261117/email-to-arm-support.html
- generator: /home/jhan/workspace/machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_email.py
- input: the email text held in the generator, and the 12 kernel logs in /home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117 from which it recomputes the boot table and the record totals
- input built by: the session, by hand, from /home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md; the kernel logs were saved by the peer session of 2026-11-15 to 2026-11-17
- sources: `/home/jhan/workspace/titan/cache-perf/crb/results/dimm-check-20261117`: nothing preserved; held back at the gate (identity capture or raw export, no explicit yes) dmi16-19.txt, dmi17-062957.txt, h-1.txt, h-10.txt, h-11.txt, h-2.txt ...; `/home/jhan/workspace/titan/cache-perf/crb/results/dimm7200-20261117`: preserved boots.txt, gaps.txt, hwerr-final.txt, lastlines.txt, set.txt, setting-final.txt, try1.txt, try2.txt, try3.txt, try4.txt, try5.txt, try6.txt ...; held back at the gate (identity capture or raw export, no explicit yes) dmi17-7200.txt, dmi2.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/uefisettings-20261117`: nothing preserved; held back at the gate (identity capture or raw export, no explicit yes) identify.txt, ifr.txt, questions.json; left behind (no value used: empty file) ifr.err, questions.err; `/home/jhan/workspace/titan/cache-perf/crb/results/dmidecode-t17-2026-10-30.txt`: preserved dmidecode-t17-2026-10-30.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-R8-20261117T020549Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/titan/cache-perf/crb/results/w120-BASEd10-20261117T041738Z`: preserved a0001.csv, a0056.csv, a6400.csv, a6432.csv, a6456.csv, env.txt, launches.txt; left behind (no value used: empty file) stderr.txt; `/home/jhan/workspace/machines/arm-crb/DIMM-flaky-report.md`: preserved DIMM-flaky-report.md; `/home/jhan/workspace/machines/arm-crb/firmware-snapshot-20261117`: nothing preserved; left behind (private configuration: not copied into a public repository) arm-platform-settings.json, decoded-settings.json; left behind (no value used: empty file) settings-questions.err; left behind (provenance) ABPolicy-d1b7431e-bd11-4f47-993a-3238dcfb38a0, ABStatus-4a8dd2d2-8acf-11ef-b864-0242ac120038, ABTelemetry-69571844-cc31-4807-9c10-547038b14c72, APIC.bin, APMT.bin, Boot0000-8be4df61-93ca-11d2-aa0d-00e098032b8c ...; held back at the gate (identity capture or raw export, no explicit yes) SHA256SUMS, decode_hii_offline.py, efibootmgr.txt, extract-db.log, identify.txt, kernel-firmware-lines.txt ...
- regenerate: python3 -I /home/jhan/workspace/machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_email.py <OUT> <OUT>/extra
- regenerate unverified (the rebuild from the canonical files is byte-identical, but the generator reads inputs that are not in the repository: 12 files held back at the gate (identity capture or raw export) (k-1.txt, k-10.txt, k-11.txt, k-2.txt ...; 4717707 bytes))
- inventory: [email-to-arm-support.html.lineage.md](machines/arm-crb/arm-support-case-20261117/email-to-arm-support.html.lineage.md) (186 lines)

### All files of this batch

Repo path -> canonical path (bytes). `origin:` = the session-store or scratchpad path a relocated file was copied from (history only, never fetched again).

Related: [claude_20261110_inter-agent-review-loop-skill-md.md](../../handoffs/claude_20261110_inter-agent-review-loop-skill-md.md)

- `ai-runs/handoff-relocated/exec/scratch-relocated/5f1c66d8/SKILL.md.before` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5f1c66d8/SKILL.md.before` (8088 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-notebook-artifacts-ai-prompts/5f1c66d8-63b1-4e8d-aa07-b93f7101fcf3/scratchpad/SKILL.md.before`
- `ai-runs/handoff-relocated/exec/workflows/review-inter-agent-review-loop-skill-wf_a8019a65-ae6.js` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/workflows/review-inter-agent-review-loop-skill-wf_a8019a65-ae6.js` (7819 bytes). origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-notebook-artifacts-ai-prompts/5f1c66d8-63b1-4e8d-aa07-b93f7101fcf3/workflows/scripts/review-inter-agent-review-loop-skill-wf_a8019a65-ae6.js`

Related: [claude_20261115-20261117_whole-chip-throughput-drop-with-new-test-kernel.md](../../handoffs/claude_20261115-20261117_whole-chip-throughput-drop-with-new-test-kernel.md)


Related: [claude_20261117-20261119_arm-support-email-for-dimm-flaky-report-md.md](../../handoffs/claude_20261117-20261119_arm-support-email-for-dimm-flaky-report-md.md)

- `machines/arm-crb/exec/scratch-relocated/acbf327d/out/email-body-for-gmail.html` -> `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/exec/scratch-relocated/acbf327d/out/email-body-for-gmail.html` (14487 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-machines-arm-crb/acbf327d-4bb3-4a65-988b-dc65afa38bd7/scratchpad/out/email-body-for-gmail.html`
- `machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_bundle.py` -> `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_bundle.py` (2675 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-machines-arm-crb/acbf327d-4bb3-4a65-988b-dc65afa38bd7/scratchpad/scripts/build_bundle.py`
- `machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_email.py` -> `claude-agentsrv:/home/jhan/workspace/machines/arm-crb/exec/scratch-relocated/acbf327d/scripts/build_email.py` (25217 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-machines-arm-crb/acbf327d-4bb3-4a65-988b-dc65afa38bd7/scratchpad/scripts/build_email.py`

Related: [claude_20261120_agents-running-slow-at-agentsrv-md.md](../../handoffs/claude_20261120_agents-running-slow-at-agentsrv-md.md)

- `agent-cpu-guard/guard.sh` -> `claude-agentsrv:/home/jhan/.config/agent-cpu-guard/guard.sh` (1853 bytes)

Related: [claude_20261124-20261125_pr5022-rebase-and-merge.md](../../handoffs/claude_20261124-20261125_pr5022-rebase-and-merge.md)

- `claude-config/statusline-command.sh` -> `claude-agentsrv:/home/jhan/.claude/statusline-command.sh` (1422 bytes)

Related: [claude_20261125_manual-run-sh-for-crb-perf-capture.md](../../handoffs/claude_20261125_manual-run-sh-for-crb-perf-capture.md)

- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/agent-run-2026-11-17-commands.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/agent-run-2026-11-17-commands.txt` (8711 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/agent-run-2026-11-17-commands.txt`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-20261115/rx.sh` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-20261115/rx.sh` (1419 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/crb-asrun/w120-20261115/rx.sh`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-7200-20261117/go.sh` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-7200-20261117/go.sh` (3628 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/crb-asrun/w120-7200-20261117/go.sh`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-7200-20261117/go2.sh` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-asrun/w120-7200-20261117/go2.sh` (2697 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/crb-asrun/w120-7200-20261117/go2.sh`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-run1.sha` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-run1.sha` (4772 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/crb-run1.sha`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-test-run-1.log` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/crb-test-run-1.log` (10908 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/crb-test-run-1.log`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/dump_session.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/dump_session.py` (1730 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/dump_session.py`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/last-run-fixed.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/last-run-fixed.txt` (23083 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/harness/last-run-fixed.txt`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/last-run.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/last-run.txt` (24107 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/harness/last-run.txt`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/run_all.sh` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/run_all.sh` (27633 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/harness/run_all.sh`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/summary.txt` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/harness/summary.txt` (21312 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/harness/summary.txt`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/local-run1.sha` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/local-run1.sha` (4772 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/local-run1.sha`
- `ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/verify-safety/tools/scen.py` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/scratch-relocated/5580b561/verify-safety/tools/scen.py` (6853 bytes). origin: `claude-agentsrv:/tmp/claude-0/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/scratchpad/verify-safety/tools/scen.py`
- `ai-runs/handoff-relocated/exec/workflows/review-manual-run-wf_6eeae9a7-1f0.js` -> `claude-agentsrv:/home/jhan/workspace/ai-runs/handoff-relocated/exec/workflows/review-manual-run-wf_6eeae9a7-1f0.js` (15524 bytes). origin: `claude-agentsrv:/home/jhan/.claude/projects/-home-jhan-workspace-ai-proj-arm-crb/5580b561-5d79-4843-8268-4fd921b91f81/workflows/scripts/review-manual-run-wf_6eeae9a7-1f0.js`

