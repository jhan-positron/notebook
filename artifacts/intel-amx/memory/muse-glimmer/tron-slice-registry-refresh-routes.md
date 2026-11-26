---
name: tron-slice-registry-refresh-routes
description: "tron config/test-benchmarks.json (Slice cost data, 'registry'): one machine class per refresh is enough; four routes to refresh a row (remote bench, branch dry run of bench-refresh.yml, hand edit, weekly refresh) with preconditions and measured costs; checked 2026-11-24 for PR 5022"
metadata:
  node_type: memory
  type: reference
  originSessionId: db5d90b8-2c02-4aa1-b9df-6b564487154c
  modified: 2026-11-24T18:20:36.565Z
---

Checked on 2026-11-24 at tron commit 90a9110be5, for the second reply to Isaac on PR 5022 (page `muse-glimmer/round2-respond-2-issac.html`). A reviewer asked twice for `bin/slice bench --update` after a test change, and my first drafts argued that a measurement was not possible. That was the mistake of [[declined-fix-leaves-finding-open]].

Facts:
- One run of `bin/slice bench --update <test>` rewrites the row of the machine class it runs on. One class is enough: `bin/slice bench --check` fails only when a test has data on no class (`bin/slice:2114-2125`). Of the 49 commits on main that touched the file from 2026-10-15 to 2026-11-21, 48 changed rows of one class.
- A row holds one value per run size: 1, 2 and 4 slices. A slice is an eighth of the machine on class granite_rapids_6962p. `SYSTEM_CONFIG="--instance 1,2"` is the 4-slice size. `max_rss_mb` holds whole MiB (`peak KiB // 1024`).
- Slice uses the rows to plan the schedule and to budget memory at admission. It sets no time limit and no memory limit from them, and its drift warnings compare times only.
- Weekly refresh: `.github/workflows/bench-refresh.yml`, Sunday 05:00 UTC, measures main on genoa96 (`2x96core`) and granite_rapids_6962p (`2x72core`), est. 43 to 62 minutes per class. It puts changed rows into rolling pull requests of github-actions[bot] (5037 and 5038, open drafts since 2026-10-20). A person must merge them. A memory change counts when it is above 16 MB and above 10%.
- Branch dry run: `gh workflow run bench-refresh.yml --ref <branch> -f runner_class=<2x96core|2x72core|all> -f dry_run=true`, after a manual `gcp-nix.yml` run on the same branch head. It measures and opens no pull request. Example: run 42279891295 on the branch of PR 5278, 56 minutes.
- Remote bench: `bin/slice bench --remote --remote-sku sku0|sku1 --update <test>` (`sku0` = genoa96, `sku1` = graniterapids72). It needs a finished build made inside `nix develop`, in a checkout that the pool machines see at the same path, and the scheduler client `bsub`. The agent machine claude-agentsrv has no `nix` and no `bsub` (checked 2026-11-24). `bin/slice route` answers `distributed-dice` there.
- A local bench on delphi-3b35 is not allowed: [[delphi-3b35-no-slice-bench]].

**How to apply:** when a tron reviewer asks for a registry refresh, state the open finding plainly (recorded value against measured value), do not write that a measurement is impossible, and show jhan these routes with their costs. Routes that use pool machines or CI benchmark runners need jhan's approval.

Related: [[changes-need-system-tests]], [[review-replies-keep-simple]].
