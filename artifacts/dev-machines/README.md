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
