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
