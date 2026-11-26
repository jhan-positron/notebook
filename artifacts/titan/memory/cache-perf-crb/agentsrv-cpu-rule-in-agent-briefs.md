---
name: agentsrv-cpu-rule-in-agent-briefs
description: "On agentsrv, put the CPU pin rule (no widening with taskset, numactl, sched_setaffinity; 6 busy processes at most) into every subagent brief; three agents ran programs outside the pin on 2026-11-25 when the brief lacked it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: e8814cab-99b1-4798-9af9-6536ce08ea6e
  modified: 2026-11-26T02:09:15.513Z
---

When I start subagents on agentsrv, the brief must hold the CPU rule of the user's global CLAUDE.md in its own words: every shell command is pinned to the CPUs 26 to 31, do not widen the pin (`taskset`, `numactl`, `os.sched_setaffinity`), keep 6 busy processes at most, size worker pools from `nproc`.

For a job with many agents I add a stricter job rule: no `taskset` at all, also not for a short experiment. This stricter rule is mine. The user's rule forbids only widening the pin.

**Why:** In the line-by-line job of 2026-11-25 ([[crb-line-by-line-pages-2026-11-25]]) my briefs did not hold the rule. Three agents each ran one short program outside the pin as a shell experiment (`taskset -c 0 nproc`, `taskset -c 0 readlink ...`, a script of 4 lines under `taskset -c 0-5`). I found this only by a scan of the session records, and I had to report it to the user. This is my own lesson, not a message of the user.

**How to apply:**

- Put the rule into the brief file and into the first prompt of each agent, before the first agent starts.
- Some scripts of `ai-proj/arm-crb/code` restart themselves under `taskset -c 0-119`: the `run_bwx*.sh` scripts, `run_h2.sh` and the `build*.sh` scripts. The tests `test_schedule*.py` start a copy of a run script unless `--no-run` is given. On agentsrv such a start widens the pin. Do not run them there. Report the result as "not tested" and name the test that would show it.
- To check a finished job: `python3 scan_commands.py` in `crb/tmp/agent-scratch/line-by-line-2026-11-25` lists every program that the session or its agents started under `taskset`. It reads the session records. The session id is a fixed value in the script.
