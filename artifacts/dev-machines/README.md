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

