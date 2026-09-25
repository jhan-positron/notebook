# i4525-20260922: first delphi-3bda test of the issue #4525 typed KV-cache tensors branch

Prepared 2026-09-22 20:0x UTC while the implementing agent (branch jhan-kv-typed-tensors,
worktree ~/workspace/ai-runs/tron-issue4525) writes issue4525/status/first-3bda-test-plan.md.
The plan decides which steps run; these scripts are the generic steps.

- build.sh: check out a commit into /var/tmp/jhan/tron-<name> on 3bda, configure (CONFIGURE_ARGS),
  build TARGETS on our half (cpus 72-143,216-287), run TESTS with the fake device. Marker build-<suffix>.done.
- host-suite.sh: make build-test-host + make test-host in that worktree (waits for lease + flock).
- smoke.sh: greedy 1-user token identity base / head / head2 (A/A) / headoff (TRON_AMX_DISABLE=1).
- campaign.sh + summarize.py: runtron A/B cells (fork of q4b-rt8u-20260922) with RT_BASE / RT_HEAD /
  CELLS_ALL from the environment; idle-serving takeover through platformd; serving restored at the end.

Machine facts checked 2026-09-22 19:50-20:05 UTC: lease free, production 4 qwen-3-4b tp2 engines up
(platformd 0.11.0, tron deb 2026.09.18-3faba6d0), marker /bill-has-instance-0,2 present, Bill idle,
ci-runner-stop timer 02:45 UTC, nightly cron 03:30 UTC (timeout 660 min). Baseline worktree
/var/tmp/jhan/tron-main0922 = origin/main 0a51385e95 created; nix develop on its flake is warm
(clang 19.1.7, cmake 4.1.2, ninja 1.13.1). bin/slice route = local-legacy (8 cards).
- Report: status/first-3bda-test-results.html (gen_report.py) = artifact https://claude.ai/artifact/FfE8Vi3weawiQ5VQnmxCJF (private); evidence issue4525/evidence/3bda-first-test/
