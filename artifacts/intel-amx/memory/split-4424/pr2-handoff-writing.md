---
name: pr2-handoff-writing
description: "2026-10-10 ~21:30 UTC: PR2-handoff.md (split-4424 folder) final with Update 1 (codex's 4 review points from PR2-handoff-review.md + two verification runs, 78 + 30 kept findings, all folded in); the reply is PR2-handoff-update1.md; PR-2 itself is not started; a further codex round would be answered the same way"
metadata:
  node_type: memory
  type: project
  originSessionId: dcb9e93c-ce59-4679-b079-a205f5f665ed
  modified: 2026-10-10T20:23:04.490Z
---

State on 2026-10-10 about 21:00 UTC (jhan: "Generate PR2-handoff.md ... PR1 is already landed at PR 4868", then "codex will review PR2-handoff.md and write review comments to PR2-handoff-review.md, please respond to codex's review once it is ready"):

- "Landed" meant opened: PR #4868 is OPEN, review required, head 82d05e94be (main 72308ec90c inside). PR-2 bases on jhan-vnnik-1-layout and opens as a draft.
- Probe facts (scratch worktrees, removed; confirmed by codex and by the verification runs): the patch handoff-material/ref/PR2-diff-76a0..4d3a.patch applies on 82d05e94be with one conflict (the dispatch diagram line of amx_attn_iface.hpp: PR-1's two-line rewrap vs the 84-column line "(VNNI K: qk_vnni_128x4)"); five c3334a079f comment edits must be reverted by exact text; result 10 files +285/-72.
- Deliverables in ~/workspace/intel-AMX/PR3879/new-PRs/split-4424/: PR2-handoff.md (Update 1 version, about 82 KB, same section layout as create-PR1-handoff.md, with a "Deviations from split-handoff.md" list of 5 items: fakes in the kernel commit, A3 build, mutation check, head/headoff arms, A2 dropped), PR2-handoff-update1.md (verdict table on codex's 4 points, the applied changes, section 3 = the 6-lens run's findings grouped), PR2-handoff-review.md (codex's).
- Key corrections learned: the diagram line is 84 columns (not 78); edit 3 is at kernels/k_vnni.hpp lines 45-47 at 82d05e94be; the 2026-10-09 newoff==new record covers one cell only (CPU prompt 1024, PR-4 state); the required and legacy CI jobs share the runner labels [self-hosted, fpga, test, avx512] and the pool has 3 Granite Rapids + 3 AMD hosts; summarize.py needs WEDPERF_ARMS; smoke.sh's verdict ignores token counts and rc; END_BY stays 01:30 UTC with DEADLINE_HHMM=0130; build2.sh is the real build recipe; the chain takes Bill's marker itself under jhan's order (as PR-1 did).
- Second verification workflow (3 lenses + refuters, wf_264c5a7a-836) ran 21:00-21:20 UTC: 30 kept (3 must-fix: marker-take attribution, full CONF_* lines, slice.yml path filter), all folded in; recorded in PR2-handoff-update1.md section 3. Done 21:30 UTC.

**Why:** the handoff is the only input of the PR-2 executor; jhan wants codex's review answered before the executor starts; codex may review again.
**How to apply:** read PR2-handoff.md and PR2-handoff-update1.md first; do not start PR-2 itself; if a new PR2-handoff-review.md round appears, answer it the same way (verdict table, evidence, edits in place, an update section). Related: [[pr1-split-execution]].
