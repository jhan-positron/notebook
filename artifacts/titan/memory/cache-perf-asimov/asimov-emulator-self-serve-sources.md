---
name: asimov-emulator-self-serve-sources
description: "Where the knowledge for running Asimov Palladium emulation without Jesse lives (own skill asimov-emu-models with the model table, team skill plugin, Jacob's /scratch packages, #emulation posts), how Claude Code and Codex get it on agentsrv, how to reach the Spokane emulator files, and what still blocked a first run on 2026-11-24"
metadata:
  node_type: memory
  type: reference
  originSessionId: c2b16a44-9547-430d-94e1-af6e41e98140
  modified: 2026-11-25T01:32:27.477Z
---

Jeremy asked Jibin (1:1, 2026-11-23) to run the emulator directly instead of through Jesse.

**Read these first, they hold the current facts (do not copy them here):**
- Own skill `asimov-emu-models`: real folder `~/workspace/notebook/skills/asimov-emu-models/` (SKILL.md procedure, `models.md` dated table of releases / models / boot stacks / baselines / check log, `ga13-rules.md`). Linked into `~/.claude/skills` and `~/.codex/skills`. Created 2026-11-24, not committed to the notebook repo (Jibin had not asked for a commit).
- Team skill `palladium-emulation`: plugin from marketplace `aps` (`positron-ai/aps-agent-skills`), installed 2026-11-24 for Claude Code (user scope) and for Codex.
- Global rule `# emulator` in `~/.claude/CLAUDE.md` and `~/.codex/AGENTS.md` (same 14 lines in both).
- `~/dev`: 8 Asimov repo clones plus Jacob's `AGENTS.md` (copied unchanged) and `CLAUDE.md` link. Builds go to `/scratch/jhan/agent-builds`.

**People and sources:**
- Jesse Zhang DM (channel D0AT074U71S), 2026-11-23: default model `hemi_rtws_tlm`; Alexey builds the models and posts releases in Slack #emulation (C0AFU968CQK); no other catalog; unannounced models must be tested by us. Jesse's NDA question was settled by Alexey on 2026-11-24: no NDA for the emulation cloud.
- Jacob Geldbach packages (2026-11-02): `/scratch/jgeldbach/cme-perf-for-jibin/`, `/scratch/jgeldbach/env-setup-general/`. His run package for GA13 request #4045 (boot folder with checksums): `/scratch/jgeldbach/asimov-dpa-stress/palladium/cme-perf-pf2/`.
- GA13 account: Jibin asked Alexey by DM on 2026-11-24; Alexey answered the same afternoon that he had requested access and that the emulation cloud needs no NDA. Earlier requests took 1 to 2 days. The first-login steps (Jibin types the passwords) are in `ga13-rules.md`. The agent needs the GA13 user name from the welcome mail to add the ssh block.

**Environment facts found 2026-11-24:**
- Codex home is per host: `CODEX_HOME=$HOME/codex-home-$HOSTNAME` (set in `~/jibin.bashrc.positron`). Only `skills` is shared (link to `~/.codex/skills`). `AGENTS.md` is linked to `~/.codex/AGENTS.md` only in `codex-home-claude-agentsrv`. A Codex plugin install reaches one host's home only.
- `codex debug prompt-input "<text>"` prints the prompt Codex would send, with no model call. Use it to verify that a skill or rule is loaded.
- The claude-dev container on agentsrv has no `/tools`, `/emu`, `/ice`, `/projects`. Spokane emulator files are readable through `ssh jhan@alpha` (releases `/emu/asimov/`, asimov-os `/scratch/asimov-os/`, queue `/ice/infra/asimov-emu/queue.sqlite3`, Jesse's setup `/home/jzhang/dev/emuMemBenchBox`).
- Jibin's shell profile redefines `cd` to print a listing. Use absolute paths, or `bash --noprofile --norc -c` over ssh.
- `ga13ut01.cadence.com` resolves and answers on port 22 from the container. No login was tried.

- Spokane driver host: `ssh jhan@palladium-94a4` works from the container without a password. It mounts `/home`, `/scratch`, `/emu`, `/tools`, `/ice`.

**First run, state on 2026-11-24 17:30 PST:** prepared, NOT launched; waiting for Jibin's yes for that one launch. It is a Spokane repeat of Jacob's GA13 request #4045 (`cme-perf` row set `pf`). Run tree `/scratch/jhan/agent-builds/asimov-a10181848-pf` (worktree of `~/dev/asimov` at `5645dbfd1`), boot files and reference logs `/scratch/jhan/agent-builds/cme-perf-pf2/`, launch script `launch-spokane-pf.sh` there (run it on `palladium-94a4`). Spokane works again: queue request 1997 finished with exit code 0 on 2026-11-24. The details and the side effect on the release build folder are in `models.md` section 3 and 4. Related: [[verify-other-agents]].
