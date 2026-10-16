---
name: wade-fuse-question-pr4267
description: "2026-09-09 Wade APPROVED PR0 #4267 (page_share counters, head ef13273ba9) and asked whether the counters could use the in-tree FUSE stats tree with env-var opt-in; tracked as issue #4303 (created 2026-09-09, no names/mentions); PR not updated"
metadata: 
  node_type: memory
  type: project
  originSessionId: 3871cb5b-18f1-405d-bdc2-868e876c877d
  modified: 2026-09-09T17:52:56.953Z
---

Wade (Wado-posi) approved PR #4267 at head ef13273ba9 on 2026-09-09 (review 5156698046) with one
question: use FUSE (tron's tronstats stats tree) for the page-share counters, collection opt-in via
env var, so they can be read live and differenced over intervals. jhan asked for the answer in chat,
NOT on the PR. Deliverables: PR3879/new-PRs/PR0/respond-2-Wade-PR0.html (jhan asked for it 2026-09-09; light theme, 2 SVG
diagrams, glossary, section 6 'value' from the AMX and the general perspective, draft reply) and the earlier
wade-fuse-question-20260909.md (first two verification passes).

Verified facts that shape the answer (value-section corrections 2026-09-09: perf-model's own memory time is
2.494 us at 13.14 GB/s (2.06 us at 15.9 GB/s is the Notion recipe); PR 3879 canonical unit 2.89 us, mirror
2.66; pending_visits is an UPPER bound on non-AMX decode visits (decode-only window, no sliding window), not a
lower bound; counters see only software-required visits when hardware attention is on; Wade's #3879 objection
was a Claude review he relayed):
- tron already has a default-on FUSE stats tree (README.stats.md, h/system/fuse_stats.hpp); runtron
  and rinzler mount it in main() before stats::start(); casual leaves need no manifest descriptor,
  exported ones (Prometheus via platformd) do plus a .skip marker.
- Closest precedent: h/tron/models/expert_stats.hpp (Ben, 2026-05) = cumulative counter + JSON
  histogram leaves via make_file + set_read_callback. Wade himself added FUSE leaves on 2026-09-04
  (HBM thermal, commit 2e8de30219).
- Exit summary must stay if FUSE is added: rinzler calls stats::unmount() before app().quit()/return,
  runtron's unmount_guard unmounts on return from main, both before static destructors run.
- Runtime gate shape: function-local static bool from getenv at hook site (apply_page_range is a
  member template), gate on block 3 only; record_page_visit/flush already no-op at zero, so
  t_page_share_counters passes unchanged. Cost when off = one branch per (page, query) pair, UNMEASURED.

Recommendation given: merge #4267 as approved, FUSE version as a follow-up (~10 files est.) after an
A/A benchmark of the gated-off build. Decisions left to jhan/Wade: casual vs exported leaves; whether
"intervals" means differencing reads (no reset leaf) or something else.

**Why:** Wade's earlier #3879 objection was "compiled by nobody"; the FUSE variant flips that to
"compiled by everybody, including the .deb rinzler", which is a different trade he has not accepted.
**How to apply:** if jhan asks to post the reply, use the draft in the .md file; if jhan chooses the
rework, start from the sketch (section 4) and run the A/A control first. Related: [[pr3879-split-progress]],
[[wade-fold-question-pr4265]].

UPDATE 2026-09-09 (later): jhan asked for a tracking issue before merging #4267. Created
https://github.com/positron-ai/tron/issues/4303 "page_share_counters: publish as FUSE stats with
env-var opt-in (follow-up to #4267)", labels "Type: enhancement" + "stats", assignee jhan-positron.
Body record: PR3879/new-PRs/PR0/issue-4303-body.md. Per jhan, no @-mentions and no personal names
in the issue ([[no-names-in-github-issues]]); Wade is "the approving reviewer". Body was verified by
two workflow rounds (6 + 3 agents) against main c0251042c5 and PR head ef13273ba9. Design points
that changed from the assessment: the getenv static must be in a non-template function (apply_page_range
is a template); four comments describe the compile-time gate (header, test file, t/CMakeLists.txt,
include line); the monotonic-counter rule applies only to exported leaves; Decision 4 = one leaf per
value vs one summary JSON leaf. Nothing posted on the PR itself.
