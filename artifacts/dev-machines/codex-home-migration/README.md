The migration is prepared for the existing `claude-dev` container.

The container path changes from `/home/codex-home-claude-agentsrv` to
`/home/jhan/codex-home-claude-agentsrv`. The complete directory stays on the
same host storage at `/var/tmp/jhan/persist/codex-home`. No data copy is needed.
The new container receives `USER=jhan` and `LOGNAME=jhan`. Its process identity
remains root inside the existing rootless container configuration.

Run the final migration from a host shell after saving work in the container:

```bash
ssh agentsrv
claude-box migrate-home
claude-box
printf 'USER=%s LOGNAME=%s HOME=%s CODEX_HOME=%s\n' "$USER" "$LOGNAME" "$HOME" "$CODEX_HOME"
```

`migrate-home` stops all sessions in the existing container, including the
session used to prepare this change. It preserves the current image and every
existing volume source. It checks the source mount, destination directory, and
database before stopping. It removes the stopped container before changing
indexed paths, then creates and verifies the replacement container.

The migration helper backs up the session index before updating its absolute
rollout paths. It also backs up and updates cached shell snapshots. It leaves
session history files unchanged because other database records use byte offsets
into those files. Backups remain in the persistent Codex directory.

The launcher and shell startup file are shared across hosts. Existing containers
on `alpha` and `sw-dev-01` continue using their original mounts until each host
runs `claude-box migrate-home`. The temporary startup fallback is used only when
the old mount is present and the new mount is absent. After migration, the old
path is no longer mounted or used as the active Codex home.

If migration fails, do not manually start an old container against the changed
index. Read the reported error and rerun `claude-box migrate-home` after fixing
it. A failed creation retains the original image ID for retry. The script refuses
to start the new container if data migration fails. It retains all backing data
and migration backups.

Podman can stop the container but report a timeout while collecting a dead
command session's exit status. The launcher now checks the same container's
state and process ID before retrying that specific cleanup failure once. It
continues only after cleanup succeeds and the container is confirmed stopped.
Ordinary `claude-box` entry reports an unfinished migration instead of silently
restarting the old setup without explanation.

The launcher keeps its serialization lock only in the managing shell. Podman
commands and the interactive shell receive no lock descriptor, so a detached
container monitor cannot keep later `claude-box` commands waiting after a
successful migration or start.

The initial audit found 117 valid session-index paths to migrate on `agentsrv`.
There are also 67 pre-existing references to missing `claude-alpha` session files.
Those unrelated references are left unchanged. Counts can increase while other
Codex sessions remain active.

Tests use temporary databases and fake Podman commands. A read-only dry run on
the live database checks its actual schema and source files. The final mount and
environment checks run automatically after container recreation.
