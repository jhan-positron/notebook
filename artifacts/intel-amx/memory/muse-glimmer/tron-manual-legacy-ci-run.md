---
name: tron-manual-legacy-ci-run
description: "positron-ai/tron: the documented way to run CI on a PR's final commit before merging is a manual dispatch of the legacy CMake pipeline; it is the only CI pipeline that builds with TRON_AMX_DISPATCH=ON"
metadata:
  type: reference
---

Command (README.ci.md on main, section "CMake and CTest (`cmake-single-platform.yml`)"):

    gh workflow run cmake-single-platform.yml --ref YOUR_BRANCH -F skip_benchmarks=true

Source: Hannah Van Eenoo wrote the section on 2026-09-11 (commit 2f1ee29982, "ci: Retain manual legacy checks for the GCP Nix cutover"): "run it on the final PR commit and wait for both pipelines before merging". Her #software announcement of 2026-09-11 09:27 PDT is "Required jobs for tron repo merge are changing TODAY". jhan remembered it on 2026-11-19 as "a process to run CI before merging PR" and asked to use it for PR 5022.

Facts checked on 2026-11-19 at main 3bea58b788:
- The build step configures with `--preset native ... -DTRON_AMX_DISPATCH=ON` (cmake-single-platform.yml:353-355). No other CI pipeline sets the option; the required GCP Nix pipeline leaves it OFF.
- Jobs run on `[self-hosted, fpga, test, avx512]`: 4 AMD runners (andoria-02, -09, -14, -ee10) and 3 Intel Granite Rapids runners (delphi-17cf, -3af6, -3bd6). GitHub picks. AMX kernel test cases execute only on a Delphi runner; on AMD they are reported as skipped and the job still passes. Not delphi-3bda, not delphi-3b35.
- A passing log shows one line per test binary. Slice uploads a test's own output only on failure.
- The workflow's benchmark matrix has only the AMD class active (the Intel class is commented out), so keep `skip_benchmarks=true`.
- `workflow_dispatch` uses the workflow file of the given ref.
- Last manual run: 2026-09-11 (run 34633703482). The same pipeline passed through `publish-deb.yml` on tags v2.0.0-rc1 (2026-11-03) and v2.0.0-rc2 (2026-11-13).
- No process runs the nightly systems test on an unmerged PR: `FEATURE_TESTING_PUBLISH: "0"` in publish-deb.yml.
- Labels: `Run CI` only matters for draft PRs; `Skip benchmarks` skips the per-PR benchmark, which uses the GCP Nix build (no AMX code) anyway.

Run of 2026-11-20 on PR 5022 (run 44777748892, head ddf843ad97, `-F skip_benchmarks=true`):
- Durations: lint and ci-machinery-tests 3 minutes, build 28 minutes, test-host 2 minutes, test-fpga 10 minutes. The default GCP Nix run on the same head took 33 minutes.
- The build flags are a fixed `-m` list, not `-march=native`, so an artifact built on an AMD runner runs on a Delphi runner.
- test-host landed on an AMD runner first (andoria-ee10-0, EPYC 9654). `gh run rerun <run> --job <test-host job id>` reruns only that job as attempt 2, with the build artifact of attempt 1. Attempt 2 landed on delphi-3bd6-0 (Xeon 6962P) and passed 106 of 106 host tests with the option ON. GitHub picks the runner, so a rerun may need repeating.
- A passing test-host log shows `106 passed, 0 skipped, 0 failed` and one line per test executable. It cannot show whether a Catch2 case inside an executable was skipped.
- The two release-candidate tag runs before it (2026-11-03, 2026-11-13) ran test-host on AMD runners only.

Run of 2026-11-24 on PR 5022 (run 45461357302, head 90a9110be5, same command):
- Durations: the CMake workflow 35 minutes, the GCP Nix run of the same push (45461355215) 38 minutes.
- test-host landed on andoria-09-0 first. One rerun put attempt 2 on delphi-3bd6-0: 106 of 106 tests in 2.3 minutes.
- `gh run view <run> --job <id> --log` refuses while the run is in progress. For a finished job of such a run use `gh api --allow-escape-sequences repos/positron-ai/tron/actions/jobs/<id>/logs`.
- The runner of a job in progress: `gh api repos/positron-ai/tron/actions/jobs/<id> --jq .runner_name`. Jobs of one attempt: `.../actions/runs/<run>/attempts/<n>/jobs`.
- A `pull_request` run of GCP Nix checks out `refs/remotes/pull/<n>/merge`, so it builds the merge of the head with main. The CMake workflow started by hand builds the branch head itself.

Run of 2026-11-25 on PR 5022 (run 45524884960, head e863b27272):
- test-host landed on AMD runners in attempts 1 and 2 (andoria-02-0, andoria-09-0) and on delphi-3af6-0 in attempt 3. Loop: wait until the run is completed, `gh run rerun <run> --job <test-host job id of the latest attempt>`, read `.runner_name`.
- The job log prints `Model name: Intel(R) Xeon(R) 6962P`, which proves the CPU of the runner.
- A test without a registry row on the runner's machine class is listed as `passed [new]  <name>` in the Slice log. Match the name with an optional `[new]`.

Related: [[isaac-reviews-are-agent-pipeline]], [[tron-main-merge-queue-squash]], [[tron-pr-push-triggers-bot-review]].
