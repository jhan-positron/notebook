---
name: scratch-jhan-prune-review-2026-10
description: Mitchell asked on 2026-10-20 to prune /scratch/jhan (268 GiB on the filer); review and deletion done 2026-10-21 (211 GiB freed, 57 GiB left) in ~/workspace/ai-runs/scratch-prune-20261020/; open decisions are kvwait.bin 41 GiB, the small unarchived doc sets, and 5 root-owned traces needing sudo rm on delphi-3bda
metadata:
  type: project
---

On 2026-10-20 Mitchell asked whether /scratch/jhan (268 GiB on disk, unchanged since 2026-08-28) can be pruned. The review of 2026-10-21 lives in /home/jhan/workspace/ai-runs/scratch-prune-20261020/ (scratch-jhan-prune-review.html, reply-to-mitchell.txt, figures.json, data/ with the gzipped file listings and du totals, tools/ with the scripts).

Findings (on-disk GiB, measured on delphi-3bda while the CI lease was busy, read-only):
- .pftrace: 133.1 GiB (691 files), user said these can go.
- rebuildable from git (pr3244 37.2, workspace/story2814 20.3, tron-pr3070 8.4, pdjn-wt 2.6, install-* runtron copies): 78.2 GiB.
- raw campaign data not in the notebook: 53.7 GiB, of which kvwait.bin dumps under perf-fluctuation 41.1 GiB (never fully mined per intra-pass CONTEXT.md) and perf.script, perf.data and vtune files about 4.8 GiB.
- personal: laptop-bkup 2.5, claude-dev-migrate 1.1.
- Notebook archives: 536 explicit mirrors, all byte-identical (md5 both sides); pdjn-wt diff snapshot identical to live git diff; flat_freq_tests README and 12 scripts identical.
- Not archived small sets (2,531 files, 166 MiB of content, the pdjn mine outputs being 120 MiB of that): flat_freq_tests/from-claude (41 docs), story2814 notes and PR2906 patches, ab-kit orchestrator scripts, ef720667-inv, f3kit, from-claude-mining, tron-perfetto v1/v2 tools, documents/ARM/md, p43/blocks, pdjn mine outputs, simlot, legacy-adjudicated.

Deletion done 2026-10-21 05:06 to 05:15 UTC from claude-agentsrv over the NFS mount (delphi-3bda not touched, CI lease was busy): 686 of 691 .pftrace, pr3244, tron-pr3070, pdjn-wt, tron-src, systest-b2, symbols, frozen, the two tron-perfetto install dirs, pdjn/install-* and runtron-* and the 19 perf-fluctuation/deep-dive/install-* dirs. /scratch/jhan: 267.9 -> 77.8 GiB on disk, 743,078 -> 334,028 files. Log and lists in the review folder (deletion-log-20261021.txt, data/deleted-*.txt). Left: 5 .pftrace under flat_freq_tests/20260720-* owned by nobody:nogroup (sudo capture); the auto-mode classifier denied `sudo -n rm` over ssh, so the user has to run it. The pdjn-wt entry was removed from ~/workspace/tron/.git/worktrees (see [[tron-worktree-prune-trap]]).

Second step 2026-10-21 05:44 to 05:47 UTC: workspace/story2814 (21 GiB) deleted after its 38 notes, queries, logs and PR2906 files were copied to notebook artifacts/tron/story2814-scratch/ (md5-verified, committed as 2159889 with a README section, NOT pushed). /scratch/jhan is now 56.8 GiB (perf-fluctuation 45.9), 163,421 files.

**Why:** the user must decide on kvwait.bin, the personal folders and the small sets before anything beyond pftrace and build trees is deleted.
**How to apply:** if asked to prune or to archive, start from figures.json and the listings in data/ instead of re-walking the NFS share (the walk took about 5 min per pass). Archive the small sets into the notebook first (a handoff-run style batch, see [[handoff-run-gotchas]]), then delete. Never delete on delphi-3bda while the CI lease is busy without the user's explicit go-ahead.
