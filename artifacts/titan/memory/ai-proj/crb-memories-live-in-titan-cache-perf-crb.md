---
name: crb-memories-live-in-titan-cache-perf-crb
description: "Where the memories and session records of the CRB work are (another project folder), and the rules to read there before any CRB login from ai-proj/arm-crb"
metadata:
  node_type: memory
  type: reference
  originSessionId: 5580b561-5d79-4843-8268-4fd921b91f81
  modified: 2026-11-26T01:10:12.803Z
---

Work in `~/workspace/ai-proj/arm-crb` (CRB = Arm reference server, `jhan@192.168.2.45`) has almost no memory of its own. The CRB sessions ran in other folders, and their memories are there:

- Memories: `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/memory/` (start with its `MEMORY.md`). Older ones: `.../-home-jhan-workspace-titan-cache-perf/memory/`.
- Session records with the ssh commands of the agent-driven runs: `/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/*.jsonl`. The whole-chip rerun of 2026-11-17 is `405492c8-...jsonl`, record lines 309 to 377.

Read before a CRB login: `crb-ssh-login-first-command.md` (ssh form with `-i /home/jhan/.ssh/id_ed25519`, read Slack `#phoenix-crb`, id C0C1R7XEVU6, for a block of Jeremy first, then the marker file `/tmp/positron-perf.RUNNING`), `crb-check-dimm-count-every-use.md` (12 modules at 7200 MT/s), `crb-hw-record-2026-11-24.md` (root steps for power telemetry wait for the user's message to Jeremy).

User decisions of 2026-11-25 for `arm-crb/manual-run.sh` (asked through a question dialog): it runs the as-run script copies that are on CRB (checked against `local.sha` and `go2.sha`), not the newer repo scripts, and it runs both `go.sh` and `go2.sh`. The repo scripts with the hardware record were not on CRB on that day.
