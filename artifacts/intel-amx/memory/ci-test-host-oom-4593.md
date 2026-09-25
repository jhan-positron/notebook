---
name: ci-test-host-oom-4593
description: "GCP Nix \"Test host\" + \"Test\" failures = issue #4593 (t_generate_host_2-fast OOM-killed on andoria-02/14 NUMA node 0, runner shutdown); not the PR's fault; how to recognize it"
metadata:
  node_type: memory
  type: reference
  originSessionId: 33f1bd2e-8529-4629-b27e-f29580bd897e
  modified: 2026-09-24T21:37:16.514Z
---

Issue positron-ai/tron #4593 (opened 2026-09-24, labels CI / Flaky test): on runners andoria-02-0 and andoria-14-0,
`t_generate_host_2-fast` (llama-3.1-8b host generation, ~35 GB RSS) is OOM-killed when Slice puts it in slot 0-3
(NUMA node 0, strict hwloc membind). systemd OOMPolicy=stop then stops the runner, so the step shows "cancelled".

How to recognize it in a job log (`gh run view <run> --job <job> --log`, NOT `gh api .../logs`, which returns empty):
- "##[error]The runner has received a shutdown signal" 2-3 s BEFORE "failed t_generate_host_2-fast inst 2,8" (or 3,8)
  at ~25-50 s; then "The operation was canceled"; Test host step conclusion = cancelled.
- The "Test" job fails only as the aggregator: "Dependencies did not succeed: test-host=failure".
- Test logs are not uploaded (upload steps skipped), so the reason is only in the issue's host evidence.
- Same test passes on andoria-09 and delphi runners, and on andoria-02/14 in slot 5 (node 1).

2026-09-24 check for PR #4557 head c73e7fb2f9 (run 36040048427): both failures = this signature (andoria-14, slot 2,
39.4 s); #4557 changes no config/ file; the older head fcdbfff8e4 hit it too, 633cb88896 passed on delphi-3bd6.
Remedy used: `gh run rerun <run> --failed` (runner is random). [[pr4587-alloc-creates-blocks]]
