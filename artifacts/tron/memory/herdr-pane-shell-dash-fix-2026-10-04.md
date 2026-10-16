---
name: herdr-pane-shell-dash-fix-2026-10-04
description: "herdr panes inside the claude-dev container came up as /bin/sh (dash: no prompt path, Tab inserts a tab) because podman exec gives no SHELL and bash does not export it; fixed 2026-10-04 with default_shell in herdr config.toml plus -e SHELL=/bin/bash on the agentsrv-setup.sh entry line"
metadata:
  type: project
---

herdr (terminal workspace manager, `~/.local/bin/herdr` 0.9.1) picks the pane shell from `[terminal] default_shell`, then `$SHELL`, then `/bin/sh`. `/bin/sh` is dash on the claude-dev image. Dash has no readline, so Tab inserts a literal tab, and its prompt is a bare `$ ` with no folder path.

Why it appeared on 2026-10-03: the new login prompt in `~/agentsrv-setup.sh` enters the container with `podman exec ... bash -lic 'herdr --session "$(hostname)"; ...'`. podman exec passes no host environment, and bash sets SHELL as a shell variable without exporting it (`env -i bash -lic 'env | grep SHELL'` prints nothing). So the `herdr server` for session `claude-agentsrv` had no SHELL and spawned dash. The old setup never hit this because the pane server ran on the HOST from an ssh login, where sshd sets SHELL (see [[herdr-agentsrv-topology-2026-10-03]]).

Fix applied 2026-10-04 (verified on a throwaway session first, then on the live server):
- `~/.config/herdr/config.toml` (shared NFS home, all hosts): `[terminal] default_shell = "/bin/bash"`. Backup at `config.toml.bak-20261004`.
- `herdr --session claude-agentsrv server reload-config` applied it to the running server without a restart. New panes spawn `/bin/bash`; panes opened before the reload stay dash until closed.
- `~/agentsrv-setup.sh`: added `-e SHELL=/bin/bash` to the `podman exec` entry line. Backup at `agentsrv-setup.sh.bak-20261004`.
- `~/claude-container/claude-box` (`~/bin/claude-box` is a symlink to it): added `-e SHELL=/bin/bash` to the `podman run` line (takes effect at the next recreate) and to the `enter` `podman exec` line (takes effect at the next entry). Backup `claude-box.bak-shell-env-20261004T*Z`. Only syntax-checked: podman is not available inside the container.

**How to apply:** If a herdr pane shows a bare `$` prompt or Tab inserts a tab, check `readlink /proc/<pane-shell-pid>/exe` (dash vs bash) and whether the `herdr server` process has SHELL in `/proc/<pid>/environ`. Never restart the `claude-agentsrv` server to fix it: its panes hold live claude sessions. Use `server reload-config` after a config change. Containers created before 2026-10-04 have no SHELL in their base environment; the `claude-box enter` exec line now sets it on entry, and a recreate bakes it in.
