# after-go: records of the steps after jhan's go of 2026-11-24 (tron PR 5022)

Short version: on 2026-11-24 the branch `jhan-amx-kvmul16` was fast-forwarded to `90a9110be5` (the two commits
of Isaac's PR 5606) and pushed at 18:36 UTC. Both CI runs passed. The PR description was saved at 19:24:05 UTC
and the reply was posted at 19:24:15 UTC as conversation comment 7142046348. Times below are UTC.

Words used here:
- Required lane: the CI workflow GCP Nix (`gcp-nix.yml`). It builds with the option `TRON_AMX_DISPATCH` OFF.
- CMake workflow: `cmake-single-platform.yml`, started by hand. It builds with the option ON.
- Attempt: GitHub's number of a run or rerun of a job. Attempt 2 is the first rerun.

| File | What it holds |
|---|---|
| `nix-run-45461355215.json`, `nix-run-45461355215-jobs.tsv` | The run of the required lane at the new head: 15 jobs passed, 2 benchmark jobs skipped, 18:36:27 to 19:14:38. |
| `nix-test-host.log` | Log of its Test host job (runner andoria-09-0). Lines 414-415: the two AMX tests passed. Line 435: 106 passed, 0 skipped, 0 failed. Line 118: checkout of the merge of `90a9110be5` into main `0e37695a12`. `nix-test-host.rest.log` is the same log, fetched while the run was in progress. |
| `cmake-run-45461357302-attempt1-jobs.json`, `cmake-run-45461357302-attempt2-jobs.json`, `cmake-run-45461357302-attempt2.json` | The CMake workflow run, both attempts. |
| `cmake-test-host-attempt1.log` | test-host, attempt 1, on andoria-09-0 (AMD EPYC 9654): 106 passed. |
| `cmake-test-host-attempt2.rest.log` | test-host, attempt 2, on delphi-3bd6-0 (Xeon 6962P, AMX flags in line 88): 106 passed, 19:12:36 to 19:14:52. |
| `cmake-build-attempt1.log` | Build job. Line 4899 holds `-DTRON_AMX_DISPATCH=ON`. |
| `checks-head-90a9110be5.tsv`, `workflow-runs-head-90a9110be5.tsv` | The 48 checks (31 passed, 16 skipped, 1 neutral) and the 6 workflow runs of the commit. 12 skipped checks belong to the run of draft PR 5606 at the same commit. |
| `values.json` | The seven CI values that were filled into the texts. |
| `pr5022-body-live-before-edit.md`, `pr5022-body.draft.md`, `pr5022-body.final.md` | The description before the edit, with the seven replacements, and as saved (1,998 words). |
| `reply.final.md` | The reply as posted. |
| `posted-body.json`, `posted-reply.json`, `posted-reply-rendered.html` | The read-backs from GitHub, and the reply as GitHub renders it. |
| `requested-reviewers-after.json` | The requested reviewers at 19:24. ishapira-positron is on the list. |
| `review-request-events-isaac.tsv`, `requested-reviewers-after-request.json` | On jhan's instruction a fresh review request went to ishapira-positron at 19:46:07. He was on the list since 2026-11-20, and a plain request call changed nothing. So the old request was removed at 19:46:05 and added again. |

Scripts: `/home/jhan/workspace/intel-AMX/muse-glimmer/round2-tools/` (README there). The page with the full
account: `/home/jhan/workspace/intel-AMX/muse-glimmer/round2-respond-2-issac.html`, section "After your go".

Seen on the way, not part of this change: the test-host log of the CMake workflow on delphi-3bd6-0 prints
"benchmark metadata drift detected" for `t_rinzler_proxy` (`skip_return_codes=[4] -> []`). The run of
2026-11-20 at the earlier head printed the same line, and our branch does not change that registry row.
