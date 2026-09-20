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
