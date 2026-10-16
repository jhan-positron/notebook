---
name: claude-box-pid-exhaustion
description: claude-box container has pids.max 2048 with a sleep-infinity PID 1 that never reaps - zombies accumulate until fork() fails
metadata: 
  node_type: memory
  type: reference
  originSessionId: f8e01291-856b-4fd9-87f9-ea782273c211
  modified: 2026-08-20T23:11:15.611Z
---

claude-box (on alpha) runs `sleep infinity` as PID 1, which never wait()s, so every orphaned
process becomes a PERMANENT zombie. cgroup pids.max = 2048. On 2026-08-20 pids.current hit
2044 (1,723 zombies) and fork() started failing (git/uvx "Resource temporarily unavailable",
PAL bridge FATAL no initialize response). Zombies cannot be reaped from inside (only PID 1
could). RUNTIME CORRECTED 2026-08-20: alpha has NO docker; claude-box is ROOTLESS PODMAN
(container=podman env, /run/.containerenv, uid_map "0 644434775 1" = container root mapped to
the owner's host uid). Host-side fix needs NO sudo, run as the owning user on alpha:
  podman update --pids-limit 8192 claude-box     # immediate relief, no restart (podman >= 4.3)
  # fallback (older podman): CG=$(podman inspect claude-box --format '{{.State.CgroupPath}}')
  #   echo 8192 > /sys/fs/cgroup$CG/pids.max     # rootless cgroup is user-owned
  recreate the container with --init             # real fix: PID 1 reaps zombies; get original
  # cmd via: podman inspect claude-box --format '{{.Config.CreateCommand}}'
Zombie accumulation ~300/day -> a raised limit alone lasts ~2-3 weeks.
NAME CORRECTION (2026-08-20, from jhan's host shell): the podman container is named
"claude-dev" (image localhost/claude-dev:latest), NOT claude-box - "claude-box" is only
jhan's informal name in CLAUDE.md. jhan's podman is old: `podman update` has no --pids-limit.
CgroupPath = /user.slice/user-644434775.slice/user@644434775.service/user.slice/
libpod-7fbadbd43c53...scope; the SCOPE's pids.max is 192949 - the 2048 limit lives on a CHILD
cgroup (likely $CG/container, = the container's cgroup-namespace root). Fix: write 8192 to the
child pids.max that reads 2048.
Mitigation applied 2026-08-20: killed 23 redundant ssh-agents (which broke agent-based ssh;
see [[delphi-3bda-hardware]] - restored via key file + ~/.ssh/config). Watch for: transient
"cannot fork" errors mean the ceiling is hit again.
Still 1982/2048 later on 2026-08-20 (1753 zombies, parent PID 1) - the host fix has NOT been
applied yet. 2026-08-20 22:55Z: 2038/2048, 1809 zombies - two Claude Code session crashes that
day (second at ~22:46Z right after an end_turn) are attributed to this ceiling (hypothesis:
fork() EAGAIN in the client; consistent with the earlier git/uvx EAGAIN evidence). Session state
survives crashes (transcript .jsonl + memory + QUEUE.md); recovery = read transcript tail. Under this pressure avoid parallel agent fan-out (each fork risks EAGAIN); work
sequentially. The [[pal-bridge]] workaround that survives it: pal_client_local.py execs the
cached server binary DIRECTLY (/home/jhan/.cache/uv/archive-v0/uXL0551w1VRkH8c-/bin/pal-mcp-server),
no uvx/git forks; earlier "FATAL: no initialize response" failures were this same fork pressure.
