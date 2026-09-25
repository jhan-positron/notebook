---
name: attn-stats-why-not-fuse
description: "2026-09-24 verified answer to jhan's question 'why a new stats infra in attn_stats.hpp instead of leveraging FUSE stats' (PR #4596): the header DOES publish through the FUSE layer (4 calls, 37 lines); the layer stores one value per file and has no add operation, so the store must be program memory, as in all 11 other publisher families; K6 (unmount-order reason for the stderr summary) was REFUTED; PR-body stale items listed"
metadata:
  node_type: memory
  type: project
  originSessionId: 54307022-5593-4f51-b645-9a5329a5e08b
  modified: 2026-09-24T22:35:04.140Z
---

Question (jhan, 2026-09-24): why create a new stats infra in h/tron/models/attn_stats.hpp instead of
leveraging FUSE stats? Verified by workflow wf_03b9a9a6-d72 (6 readers, 24 refuters, 1 critic) against
worktree ~/workspace/ai-runs/tron-attn-stats @ cbf1bb6c0c; result JSON in
PR3879/new-PRs/new-counters/why-not-fuse-wf_03b9a9a6.json.

Facts that settle it (file:line at cbf1bb6c0c):
- attn_stats.hpp publishes THROUGH the FUSE layer: register_fuse_files :721-757 = is_initialized :723,
  get_file_handle :727 (takeover log), make_file :734, set_read_callback :735; no set_value/get_value in the
  header; no fuse_* source touched by the PR (only README.stats.md).
- The layer is publication only: one value_type per file (fuse_sysfs.hpp:28-29); file_handle API =
  set_value/get_value/callbacks (:348-357); set_value REPLACES the value under a writer guard + clock read +
  buffer swap (fuse_sysfs.cpp:898-925, :917 `buffer.value = value`); get_value takes no writer guard
  (:933-956) so get+set with two writers loses updates; no file removal API; make_file on a known path
  returns the existing handle; make_file asserts an initialized singleton (fuse_stats.hpp:106).
- Precedent: 11 production publisher families, all keep values in program memory (or read hardware);
  only 2 production set_value callers in the tree (model.hpp:1017, :1035, per loaded tensor); 38
  read-callback sites; doc/fuse_stats_design.md:114 recommends read callbacks for live counters/timers.
- Sizes: one-file-per-value would be 42,938 files for qwen-3-4b tp2 (2 x 27 x 36 x 22 fields + 144 + 26);
  the PR registers 131 leaves on / 5 off. Decode run: 10,865,664 visits in about 3.2 s (exit report).
- REFUTED reason (do not use): "stderr summary needed because runtron unmounts before the state dies".
  runtron unmounts at main return (runtron.cpp:485 guard, :520 eval, :527 return), AFTER every batch's
  state died; the summary exists because the rows die with the model state at batch end and the leaves
  then read {} (attn_stats.hpp:736-738). rinzler does unmount before its states die (rinzler.cpp:4806).
- The off-state contract is a hook-site guard (self_attention.hpp:1451, :1616, :1648), not a FUSE argument.
- Attribution: the FUSE ask is ONE sentence by one of two approving reviewers of #4267 (review 5156698046);
  issue #4303 is jhan's own proposal (0 comments); #4596 follows the ask, differs from #4303 details
  (JSON string leaves, registration from the state ctor after stats::start()).
- Casual vs exported (Prometheus) is undecided (#4303 Decision 1); exporting would need descriptors per
  leaf, a fixed relative path family, a .skip marker, and 'layer'/'worker' are not allowed dimension names
  (fuse_tronstats_lint.cpp:66-104).

PR-body stale items found on the way (pr-body.md, not yet fixed): :98 "fuse-poll.log, 99 lines" (file has
154); :62 "The approving reviewers of #4267 asked" (one of two); :62 margin "60x to 400x" rests on the
2026-09-01 per-visit cost, while the final exit report gives 2,631 busy cycles per prefill visit
(0.97 us) -> smaller prefill margin (hook cost unmeasured, A/A is the check). Nothing says what the leaves
do in an ENABLE_FUSE_STATS=OFF build. JSON is hand-rendered with fmt (as expert_stats) with no stated
reason (nlohmann::json exists in h/common/json.hpp).

**Why:** reviewers of #4596 will ask the same question; the refuted K6 reason is tempting and wrong.
**How to apply:** answer with "publication vs store"; cite fuse_sysfs.cpp:917 and the 2-set_value grep;
never cite unmount order for runtron. Related: [[attn-stats-pr-implementation]],
[[attn-path-counters-design]], [[wade-fuse-question-pr4267]].
