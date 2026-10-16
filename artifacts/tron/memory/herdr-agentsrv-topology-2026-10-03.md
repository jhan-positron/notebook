---
name: herdr-agentsrv-topology-2026-10-03
description: "herdr on agentsrv runs one server on the HOST (pid 4168986, since 2026-09-26) plus container-spawned servers that steal the NFS socket path; how to tell which server holds the agents"
metadata:
  node_type: memory
  type: project
  originSessionId: c7b1e2c1-2bb3-489b-af22-c6a5ac1846a3
  modified: 2026-10-04T04:43:05.434Z
---

herdr (terminal workspace manager, `~/.local/bin/herdr`, state in `~/.config/herdr/` on the NFS home) on agentsrv, as of 2026-10-03:

- The server that holds jhan's real agent panes is a HOST process: pid 4168986, started 2026-09-26 20:58 from an ssh session (cgroup session-70134.scope), NOT inside the claude-dev container. Its 5 panes ran claude (notebook, issue4500 x2, new-counters) and codex (notebook).
- Clients started inside the container (`claude-box` -> `bash -l` -> `herdr`) connected to that host server through the shared socket files (same kernel, same NFS inode).
- Twice (2026-10-02 21:52 PDT and 2026-10-03 20:44 PDT) a client inside the container failed to reach the host server and spawned a NEW server that re-bound `~/.config/herdr/herdr.sock` and `herdr-client.sock`. The host server then kept running on unlinked sockets, unreachable by path, with its agents alive. New `herdr` runs showed the restored space list with empty panes. Cause of the failed connect: unknown.
- Both servers append to the same `herdr-server.log` and write the same `session.json`, so the log is a merge.
- `herdr --session NAME` (what the Codex-added login prompt uses, NAME = container hostname `claude-agentsrv`) is a separate session dir `~/.config/herdr/sessions/NAME/` with its own server; it starts empty by design.
- yama ptrace_scope=1 and no reptyr on agentsrv: an orphaned pane cannot be re-attached. Recovery is `claude --resume <id>` / codex resume from transcripts.

**Why:** On 2026-10-03 I first concluded the agents had died because I only scanned the container cgroup. The host-side server was found by socket peer-inode matching (`ss -xp` inside the container netns vs `/proc/<pid>/fd`).

**How to apply:** When herdr "loses" conversations on agentsrv, check `ps -u jhan -o pid,lstart,args | grep 'herdr server'` on the HOST first, then map clients to servers by socket peer inode before declaring anything dead. Never signal 4168986 (or any `herdr server`) without checking its pane children. Orphaned `bash -l` + `herdr` client pairs inside the container (from closed ssh windows) hold no state; 19 were killed on 2026-10-03 after triple verification. 54 older `bash -l` + `tmux: client` orphans (2026-09-12 to 09-28) still remain, untouched. See [[claude-box-keepalive-pkill-hazard]] for why kill commands inside the container need care.
