# sync4424-20261002: machine test of PR 4424 ported onto PR 4557

Words used here: PR 4557 = "Typed KV-cache tensors" (branch jhan-kv-typed-tensors). PR 4424 = "VNNI K" (branch
jhan-amx-vnniK). The synced branch = jhan-amx-vnniK-typed (PR 4424 + merge of PR 4557 + adaptation commits).
delphi-3bda = the Intel AMX host; "our half" = socket 1, cards 90/93/b9/bc.

- chain.sh: runs ON 3bda (see its header for the steps A, B, D, E). launch.sh starts it from claude-box.
- campaign.sh / smoke.sh / summarize.py: forks of exec/i4587-20260924 (three binaries base/head/new).
- Results: exec/results/sync4424-20261002/ (build-*.txt, tests-*.txt, smoke/, chain-steps.txt, chain.done),
  exec/results/sync4424-E-cpu/ and sync4424-E-fpga/ (rt-results.txt, summary.md). Logs: exec/logs/sync4424-20261002*.log.
