# Install herdr-reviewr (agentsrv, session claude-agentsrv)

Written 2026-11-08. Every value below was read from the machine or from the herdr docs on that day. Updated 2026-11-09 after the steps were run: step 5 gained `TAR_OPTIONS=--no-same-owner`, steps 3 to 8 carry their results, and the pane counts from 2026-11-08 are explained at the end.

## Short version

All eight steps were done and verified on 2026-11-09, and the plugin shows a diff in a test workspace. The prefix+f toggle key and both agent integrations are in place. The rest of this page records each step's commands and results, and the pane-count question at the end is resolved.

## Words used here

- **herdr**: the terminal workspace manager for AI coding agents. One server process per session owns the panes. A client is the view you attach to it.
- **session `claude-agentsrv`**: the named herdr session inside the agentsrv container (its hostname is claude-agentsrv). The sw-dev-01 container has `claude-sw-dev-01`.
- **pane**: one terminal inside herdr. An agent pane is a pane running Claude Code or Codex.
- **live handoff**: herdr's experimental way to replace a running server with a new binary while every pane process keeps running.
- **herdr-reviewr** (plugin id `persiyanov.reviewr`): a herdr plugin. It shows the agent's diff in a pane, lets you comment on lines, and sends the comments to the agent's input.
- **prefix**: your herdr prefix key, ctrl+q.

## State on 2026-11-08

| Item | Value |
|---|---|
| Binary `~/.local/bin/herdr` | 0.9.5, written 12:49 PST. The home directory is NFS, so agentsrv and sw-dev-01 share this file. |
| Server of session `claude-agentsrv` | 0.9.1, pid 484465, running since 2026-10-03. `herdr status` reports `server_binary_stale: yes`. |
| Panes in that session | Recorded as 29 panes, 23 of them agent panes, on 2026-11-08. Not reconciled: at the handoff on 2026-11-09 the old server exported 1 pane [session server log: `handoff import ready panes=1`], the step 2 backup of `session.json` (08:45 PST) holds that one pane, and the server log has no pane-exit lines after 2026-10-23. Resolved: you closed many panes between that count and the handoff. See "Pane count discrepancy" at the end. |
| herdr integrations for claude and codex | Not installed. Without them a server restart cannot resume agent conversations. |
| reviewr needs | herdr 0.9.3 or newer, git (present, 2.34.1), a terminal with 24-bit color. |

What survives each action, from the herdr docs page "Session state and restore":

- Detach: everything keeps running.
- Live handoff that succeeds: every pane process keeps running. Screen contents stay.
- Server restart: layout, tabs, and each pane's directory come back from `session.json`. Every process ends. Agent panes come back as empty shells, because no session ids are stored here.

## Step 1. Get a shell outside any pane

1. In the attached herdr window press **ctrl+q, then q**. The server keeps running. You land in a plain bash prompt.
2. Check that this shell is not inside a pane:

```bash
echo "${HERDR_ENV:-outside}"      # must print: outside
```

Every herdr command from this shell needs `--session claude-agentsrv`. Without it the CLI looks at the empty default session and reports "not running".

## Step 2. Record the state before the handoff

```bash
H="herdr --session claude-agentsrv"
$H status
$H pane list  | grep -o '"pane_id"' | wc -l     # number of panes (1 at 08:53 PST on 2026-11-09; see the discrepancy note)
$H agent list | grep -o '"pane_id"' | wc -l     # number of agent panes (1)
pgrep -c -x claude; pgrep -c -x codex           # agent processes
pgrep -f -l 'herdr server'                      # server pid (484465 on 2026-11-08)
B=~/workspace/ai-runs/herdr-backup-$(date +%Y%m%d); mkdir -p "$B"
cp -p ~/.config/herdr/sessions/claude-agentsrv/session.json ~/.config/herdr/config.toml "$B/"
```

Expected from `status`: client 0.9.5, server 0.9.1, `server_binary_stale: yes`. Write the four counts down. Step 4 compares against them.

## Step 3. Hand the live server over to 0.9.5

```bash
$H server live-handoff --import-exe ~/.local/bin/herdr --expected-version 0.9.5 --expected-protocol 22
```

Result on 2026-11-09: the new server, pid 1497791, started at 08:55:28 PST with `--handoff-import` from server 484465 and imported 1 pane [session server log]. The shell in that pane kept running. Its parent is now pid 1, which shows that the old server exited while the shell lived on.

What happens: a new server starts from that binary. The old server transfers every pane's terminal and process to it, then exits [herdr docs, Session state and restore]. This takes seconds. Attached herdr windows may show a disconnect. In each such window run `herdr --session claude-agentsrv` again.

Why this command and not `herdr update --handoff` again: the binary is already current, and herdr describes the flag as "try live handoff after installing". The explicit command performs only the handoff. Trying `$H update --handoff` first is harmless. If it reports nothing to install and performs no handoff, run the explicit command.

If the command returns an error (for example a JSON object with `"code":"handoff_failed"`), the old server keeps running with all panes. herdr rolls back on a refused handoff [herdr issue 3393]. Go to "If something goes wrong".

Conditions that were checked for this server:

- Both versions use private protocol 22. The handoff uses that protocol [herdr docs, Socket API].
- 29 panes is below the 64-pane limit of a 0.9.1 sending server [herdr release notes 0.9.1].
- The server is not under systemd. The one known failure that kills panes happens only under systemd [herdr issue 4972].
- A user reported a 0.8.0 to 0.9.5 handoff where all pane processes survived [herdr issue 5443].

## Step 4. Verify

```bash
$H status                                       # server: 0.9.5, server_binary_stale: no
$H pane list  | grep -o '"pane_id"' | wc -l     # same as step 2
$H agent list | grep -o '"pane_id"' | wc -l     # same as step 2
pgrep -c -x claude; pgrep -c -x codex           # same as step 2
pgrep -f -l 'herdr server'                      # a new pid
```

Then attach with `herdr --session claude-agentsrv`, open a Claude pane, and press Enter. It should redraw and respond.

Result on 2026-11-09: `status` shows server 0.9.5 and `server_binary_stale: no`. One pane and one agent pane, the same as before the handoff.

Known after-effect: typing in some pane shows fragments like `a;1:3u`. That pane kept stale keyboard-protocol flags across the handoff [herdr issue 5291]. Run `printf '\033[=0u'` in that pane, or quit and restart the app in it.

## Step 5. Install the plugin

Done 2026-11-09 09:07 PST. `herdr plugin list` shows `persiyanov.reviewr (reviewr) enabled` at commit aede179, and the action list shows close, open, toggle.

Run this once. The registry and the install directory are under your home directory, which both machines share.

```bash
TAR_OPTIONS=--no-same-owner herdr plugin install persiyanov/herdr-reviewr
```

Why `TAR_OPTIONS` (added 2026-11-09). The plain command failed on agentsrv with this error:

```
tar: herdr-reviewr: Cannot change ownership to uid 1001, gid 1001: Invalid argument
```

- The install script unpacks the release archive with `tar -xzf` [herdr/install.sh:67 at commit aede179].
- The archive records its one file as owned by uid 1001, gid 1001 (the GitHub build runner account). `tar --numeric-owner -tvzf` on the archive shows it.
- Your shell in the container is root. GNU tar running as root restores the recorded owner by default (the `--same-owner` default for the superuser).
- The container runs in a user namespace (a kernel feature that remaps user ids) that maps only uid 0. `/proc/self/uid_map` has one line, `0 644434775 1`, and so does `gid_map`. A chown to any other id fails with "Invalid argument". This is not an NFS limit. The same chown fails on a file in `/tmp`, which is the container overlay.
- tar exits with status 2, and `set -e` in the script stops it before the `install` step.
- `TAR_OPTIONS` is an environment variable that GNU tar reads as extra command-line options. `--no-same-owner` keeps the extracted file owned by the extracting user, which is what the script needs. herdr build commands inherit your environment [herdr docs, Plugins: "Its build and runtime commands run as your user, inherit your environment"].

A failed attempt leaves nothing installed. `herdr plugin list` prints "No plugins installed." and herdr removes the checkout directory. Retrying is safe.

herdr prints a preview of the manifest and the build command `bash herdr/install.sh`, then asks to confirm. I read that script. It downloads `herdr-reviewr-x86_64-unknown-linux-musl.tar.gz` and its `.sha256` file from the GitHub release v0.52.1, checks the checksum, installs `bin/herdr-reviewr` inside the plugin directory, and links it into `~/.local/state/herdr/plugins/persiyanov.reviewr/bin/` and `~/.local/bin/herdr-reviewr`.

On success herdr prints only two lines: `Installed persiyanov.reviewr from persiyanov/herdr-reviewr.` and `Config: ~/.config/herdr/plugins/config/persiyanov.reviewr` (an empty directory for your own plugin settings). The script's `reviewr:` lines (downloading, verifying checksum, installed, linked) are shown only when the build fails. Verified 2026-11-09.

Check:

```bash
$H plugin list
$H plugin action list --plugin persiyanov.reviewr      # actions: toggle, open, close
```

The plugin id must be spelled exactly `persiyanov.reviewr`. For an unknown id herdr prints an empty list, `{"actions":[]}`, not an error.

To remove it later: `herdr plugin uninstall persiyanov.reviewr`.

## Step 6. Open reviewr in a workspace

- reviewr opens by itself when herdr creates a worktree workspace.
- For an existing workspace: attach, go to the workspace, press prefix+c for a new tab (a shell pane), and run:

```bash
herdr plugin action invoke open --plugin persiyanov.reviewr
```

The action runs against the workspace that has focus in the herdr window, not against the shell that typed the command. Both are the same when you type it in that workspace. If the focused workspace is not a git repository, the action exits with status 1 and no pane opens. `herdr plugin log list` then shows `reviewr: no repo to review: '<dir>' (not a git repo)`.

It opens as a split pane beside the chat. Keys: `j`/`k` pick a file, `Tab` focuses the diff, `v` selects lines, `c` adds a comment, `s` sends every comment to the agent's input, `?` lists all keys. Diff scopes: uncommitted, branch, last turn, commits.

Verified 2026-11-09 in a scratch repository with one uncommitted change. The pane shows the tabs `1 Changes  2 Files  3 PR`, the line `[uncommitted] 1 changed +5`, the file `calc.py`, and the five added lines marked in the diff. The footer reads `? · tab diff · e edit file · z hide`. The test workspace `reviewr-test` (id w1B, directory `~/workspace/ai-runs/reviewr-test-20261109`) was left open so you can try the keys. Remove it with `herdr workspace close w1B` and `rm -rf ~/workspace/ai-runs/reviewr-test-20261109`.

## Step 7 (optional). A toggle key

prefix+r is herdr's resize key. prefix+f is free in the default bindings (free letters: a, d, f, i, m, t, u, y). Append to `~/.config/herdr/config.toml`:

```toml
[[keys.command]]
key = "prefix+f"
type = "plugin_action"
command = "persiyanov.reviewr.toggle"
description = "reviewr: toggle pane"
```

Then run `$H server reload-config`, or press prefix+shift+r. No restart. The config file is shared by all sessions and both machines.

Done 2026-11-09 09:19 PST: block appended, `herdr config check` prints `config: ok`, and the reload returned `status: applied` with no diagnostics. Verified 09:55 PST: two presses of ctrl+q, f closed and reopened the reviewr pane, and `herdr plugin log list` shows two successful `toggle` actions.

## Step 8 (optional, recommended). Let future restarts resume agents

```bash
herdr integration install claude
herdr integration install codex
herdr integration status
```

The claude integration adds a hook to `~/.claude/settings.json`. The codex one writes to the Codex home (`~/codex-home-claude-agentsrv/`). With them, agents report their session ids to herdr, and a later server restart runs `claude --resume <id>` or `codex resume <id>` in each pane. Agents already running were started without the hook. They still cannot be auto-resumed. Start new sessions when convenient.

Status 2026-11-09:

- codex: done at 09:19 PST. herdr wrote `~/codex-home-claude-agentsrv/herdr-agent-state.sh` (integration version 10) and `hooks.json`, and added `[features] hooks = true` to that home's `config.toml`. The script exits 0 at once unless `HERDR_ENV=1`, `HERDR_SOCKET_PATH`, and `HERDR_PANE_ID` are set, so Codex runs outside herdr are not affected. Backup of the previous config: `~/workspace/ai-runs/herdr-backup-20261109/codex-config.toml.before-herdr-integration`.
- claude: done at 09:53 PST, run by you from a plain shell, because Claude Code's auto mode refused to run `herdr integration install claude` from inside a Claude session (the command edits Claude Code's own `~/.claude/settings.json`). herdr wrote `~/.claude/hooks/herdr-agent-state.sh` (integration version 11) and added one `SessionStart` hook to `settings.json`. The hook matches the events startup, resume, clear, compact, and fork, runs the script with the argument `session`, and has a 10 s timeout. The script exits 0 at once unless `HERDR_ENV=1`, `HERDR_SOCKET_PATH`, and `HERDR_PANE_ID` are set, so sessions outside a herdr pane are not affected. That settings file is on NFS and shared by every machine, so the hook runs in every Claude Code session everywhere. A copy of `settings.json` from before the change is at `~/workspace/ai-runs/herdr-backup-20261109/settings.json.before-herdr-integration`.

sw-dev-01: run `herdr --session claude-sw-dev-01 status` there. If the server shows 0.9.1, repeat step 3 with that session name.

## If something goes wrong

**The handoff is refused.** The old server keeps running. Read the error. Either retry once, or plan a full restart:

```bash
herdr session stop claude-agentsrv      # ends every pane process
herdr --session claude-agentsrv         # new 0.9.5 server, layout restored
```

After a full restart each agent pane is a shell in its saved directory. Recover a conversation with `claude --resume` (opens a picker) or `codex resume` in that pane.

**The server died during the handoff and the panes are gone.** Run `herdr --session claude-agentsrv`. A fresh server restores the layout from `session.json`. Continue as after a full restart. If the layout is wrong, stop the session, copy the backup `session.json` from step 2 over `~/.config/herdr/sessions/claude-agentsrv/session.json`, and start again.

**Roll the binary back to 0.9.1.** A running 0.9.5 server is not affected by replacing the file.

```bash
curl -fsSL -o ~/.local/bin/herdr.0.9.1 https://github.com/herdrdev/herdr/releases/download/v0.9.1/herdr-linux-x86_64
chmod +x ~/.local/bin/herdr.0.9.1
sha256sum ~/.local/bin/herdr.0.9.1
# the 0.9.1 binary installed here had 2a02fed16beb651ef006e1d43f048f652ca4dc58ad053cd2d44450563d5c54b7
mv ~/.local/bin/herdr.0.9.1 ~/.local/bin/herdr
```

## Pane count discrepancy (resolved)

On 2026-11-08 this page recorded 29 panes and 23 agent panes for session `claude-agentsrv`. On 2026-11-09 the evidence shows one pane:

- The old server exported one pane at the handoff [`~/.config/herdr/sessions/claude-agentsrv/herdr-server.log`, 2026-11-09T16:55:28Z: `handoff import ready panes=1`].
- The step 2 backup `session.json`, written at 08:45 PST, holds one workspace with one pane (internal pane number 142).
- The same server log has 81 pane-exit lines, all before 2026-10-23, and none between 2026-10-23 and the handoff.
- Inside the container, the only agent processes besides this session are four `claude` and one `codex` process from September and October. All five run under tmux (server pid 274), not under herdr.

So the handoff lost nothing that the server held. Resolution, 2026-11-09: you confirmed that you closed many panes between the 2026-11-08 count and the handoff. The session server log holds no pane-exit lines for those closes, so on herdr 0.9.1 that log is not a record of pane closes.

## Sources

- herdr docs, Session state and restore: https://herdr.dev/tui/docs/session-state/
- herdr docs, Install and update: https://herdr.dev/tui/docs/install/#update
- herdr docs, Plugins: https://herdr.dev/tui/docs/plugins/
- herdr issues 3393, 4972, 5291, 5443: https://github.com/herdrdev/herdr/issues/<number>
- herdr-reviewr: https://github.com/persiyanov/herdr-reviewr (manifest version 0.52.1, min_herdr_version 0.9.3, MIT)
