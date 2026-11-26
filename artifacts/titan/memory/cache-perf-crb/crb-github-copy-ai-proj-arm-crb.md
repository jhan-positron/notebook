---
name: crb-github-copy-ai-proj-arm-crb
description: "Where the GitHub copy of the CRB test code and test data lives (private repo jhan-positron/ai-proj, folder arm-crb), how it was built, what it leaves out, and what must be updated when a source file changes"
metadata:
  node_type: memory
  type: reference
  originSessionId: cf95f96f-fe0e-4464-9ebe-3b1a78f78771
  modified: 2026-11-24T23:30:44.991Z
---

On 2026-11-24 the user asked to put the CRB test code and test data on GitHub.

- Repo: `jhan-positron/ai-proj` (private). Local clone: `~/workspace/ai-proj`. Project folder: `arm-crb/` with `code/` and `tests/` (the user created both folders).
- First copy: commit `5062a35` on branch `arm-crb-code-and-tests`, pull request 1 (https://github.com/jhan-positron/ai-proj/pull/1). The user said "go ahead merge it" on the same day, and it was merged into `main` as commit `a8eca79` (2026-11-24 23:30 UTC). I committed on a branch first because of the rule of the harness about the default branch.
- Copy script: `crb/tmp/agent-scratch/ai-proj-copy-2026-11-24/build_repo.py` (`--apply` copies and verifies by sha256, and writes `arm-crb/SOURCES.tsv`). Without `--apply` it prints the plan only.
- Layout: `code/<project code folder>/` (latest text of sources and scripts) and `tests/<date>-<test>/<result folder>/` (8 tests: every entry of `crb/results`, grouped by name pattern), plus `report/`, `logs/`, `build-records/` per test. `arm-crb/README.md` describes it.
- Left out: compiled binaries, companion `.md` files, the code-and-data list, the folders `sched*`, `ref-*`, `render`, review notes, and 6 machine-code listings of the ASCT binary (my caution about vendor material, not a user decision).

The copy was a snapshot of 2026-11-24. Since the same day the user makes code changes in the repo itself ("Let's make changes at code repo workspace/ai-proj/arm-crb/code"). So do NOT run `build_repo.py --apply` again without checking: it would write the scratch texts over files that were changed in the repo (`go.sh`, `go2.sh`, `ra.sh`, `rx.sh`, `run_kernels.sh` as of 2026-11-24) and rewrite `SOURCES.tsv`. The README of the repo lists the files that differ from their `SOURCES.tsv` line. New work there: [[crb-hw-record-2026-11-24]]. The user wants a handoff note in `arm-crb/status/` for each change, for a review by another agent.

User wording of that day, for later requests: "our tests at CRB", "the test code used in CRB test", "the new kernel code and tests". I read this as all CRB tests (my interpretation). "Jesse" in the first message was a slip. Jesse Zhang runs the Asimov emulator tests, whose data are in `titan/cache-perf/asimov/results/` and are not in this repo.

Related: [[crb-whole-chip-code-data-list-2026-11-21]], [[crb-whole-chip-rerun-7200-2026-11-17]].
