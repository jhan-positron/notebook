---
name: i4525-first-3bda-test-campaign
description: "DONE 2026-09-22 22:49 UTC: execution of issue4525/status/first-3bda-test-plan.md (typed KV-cache tensors branch jhan-kv-typed-tensors) on delphi-3bda: Step D 4/4 identical, Step E 12/12 inside band on 682064f8fb (max +0.72 % TPS), Step C 88/0/1 on branch AND main (identical sets), Step F by the peer (rerun on the final code: identical or addressing-only differences); report issue4525/status/first-3bda-test-results.html, scripts exec/i4525-20260922/, 7 traps (short-sha fetch, pgrep self-match, NFS stale handle, lib-guard idle heuristic, ssh nohup stdin, cd listing hook)"
metadata:
  type: project
  originSessionId: d7314eec-6275-458e-8946-af0dec5dd459
  modified: 2026-09-22T22:50:44.049Z
---

jhan (2026-09-22 19:4x UTC): "another agent writes status/first-3bda-test-plan.md ... execute the plan at delphi-3bda before CI
starts today; set up a timer, check every 10 min". The plan (peer session issue4525-e8, written 20:39 UTC) left Steps C
(host suite), D (token identity), E (perf A/B), F (objdump) to me; its author ran Step A/B (build configs, real-AMX proof) itself
and fills the plan's section 7.

Source under test: the branch had no commit, so I snapshotted its working tree into commit 48ab31f7401122f0ba5117f99cdda62d5780cb29
(ref i4525-snap-20260922T2047Z in ~/workspace/tron; recipe: temporary GIT_INDEX_FILE + write-tree + commit-tree + update-ref,
peer's index untouched). Peer commits later: 85084e937c (test-only), 682064f8fb (v_vnni.hpp: hot-path TRON_ASSERT_LT removed
from the bulk route = the only production change after the snapshot), c2efd73ff6 and c3c368d298 (comments/tests; 8-lane-only
chunk() deletion). Step D ran the snapshot binary (numerics identical), Step E the 682064f8fb binary (/var/tmp/jhan/tron-i4525rt2).
Baseline main 0a51385e95 in /var/tmp/jhan/tron-main0922. Both: cross-avx512 preset, BUILD_INGEST_MODELS=ON, TRON_AMX_DISPATCH=ON.
Host-suite trees: /var/tmp/jhan/tron-i4525c (snapshot) and tron-i4525cbase (main), preset native, AVX512=ON, AMX OFF.

FINAL RESULTS (all in exec/results/i4525-20260922/, evidence copy issue4525/evidence/3bda-first-test/, 175 files):
- Step D (1 user, temp 0, pay-for-determinism, seed 1, 256 tokens, qwen3-4b tp2 --instance 2,4): CPU attention p1024/p8192 with
  arms base, head, head A/A, base+kill switch, head+kill switch: every pair identical for 256 tokens (also AMX vs kill switch!);
  FPGA attention p1024/p8192: head == base. 4/4 specs ok.
- Step E (8 users, prompt 1024/2048/8192, 3 reps, arms base/head/baseoff/headoff, CPU attention): 36 runs, 0 failures. head vs
  base TPS +0.20/+0.65/+0.11 %, TTFT -0.18/-0.26/-0.73 %; kill-switch pair -0.44/+0.72/+0.18 % TPS. Per-arm sd <= 0.35 TPS,
  <= 0.23 s. All 12 comparisons inside band (max(2*max sd, 0.4 TPS / 0.15 s)). Absolute: p1024 79.0 TPS (base) / 3.16 s TTFT;
  p2048 52.1 / 7.26 s; p8192 17.0 / 53.1 s; kill switch 71.6 / 45.0 / 14.6 TPS.
- Step C: branch tree make build-test-host rc=0 (669 host targets; t_rinzler is fpga-labelled and NOT among them; its main-branch compile error at
  t/t_rinzler.cpp:5316 needs the gpt-oss-20b ingest model macro, i.e. depends on the ingest-model configuration, not AMX), make test-host 88 passed / 1 skipped (t_proxy_lib) / 0 failed, makespan 110 s; main tree the same
  (build 816 s; identical status set, 89 lines). Reconfigure by make adds BUILD_INGEST/TEST_MODELS=ON, keeps AVX512/AMX flags.
- Step F: peer's harness (/var/tmp/jhan/tron-issue4525-tests/objdump/out, copied to evidence stepF-peer/): 14 constant-token
  wrappers identical; runtime-token wrappers differ only by the snapshot's assert (removed in 682064f8fb); my chain also produced
  full objdump -d -l of both A1 t_llama_unit binaries (1.75 M lines each, /var/tmp/jhan/tron-issue4525-tests/objdump.*.txt).
- Machine: serving down 21:14-22:30 and 22:45-22:48 UTC via dut.sh serving-down/up (platformd API); restored, 4 engines healthy,
  marker present, lease free. Deadline margin: done 22:49 vs END_BY 01:35 UTC.

Traps hit this run: (1) `git fetch <repo> <short sha>` fails ("couldn't find remote ref"); pass full shas, skip the fetch when
the object exists (build2.sh). (2) pgrep -f pattern matched my own ssh `bash -c` (kill killed the launcher; c_group found the
wrong pid) — keep pattern strings out of inspection commands. (3) NFS stale handle: replacing a running script kills it, see
[[nfs-running-script-stale-handle-trap]]. (4) lib-guard rinzler_takeover_if_idle refuses when the 10-min journal window is empty
because the engines' last line is "#EVT# 0 history events", not the SYSTEM_STATS line (idle bursts come every ~57 min after
3 h up); dut.sh serving-down (5-min request-line check) works; TODO fix the heuristic to look at the last SYSTEM_STATS line.
(5) ssh + `nohup ... &` hangs the ssh unless the job gets `</dev/null`; `ssh -n` breaks `bash -s < file`. (6) `cd` on 3bda
prints a directory listing (bashrc hook) that floods tool output; avoid cd in remote commands. (7) chain affinity set by hand
with taskset -pc 72-143,216-287 so late steps (objdump) stay on socket 1. (8) summarize.py HDR regex must accept the
armenv=[...] field (fixed); smoke.sh must set I4525_FUNCTIONS_ONLY=1 before sourcing campaign.sh (fixed) — both caught by the
29-agent review workflow wf_a5e29098-431 before Step D.

Deliverables: report issue4525/status/first-3bda-test-results.html = artifact https://claude.ai/artifact/FfE8Vi3weawiQ5VQnmxCJF
(private, v4 2026-09-22 23:3x UTC: Step E dot plot, Step F rerun verdict, 38 review fixes from two workflows (wf_a5e29098 scripts, wf_4d2cd68a report: 24 confirmed of 50); republish the wrapper-stripped scratchpad copy typed-kv-tensors-3bda-test.artifact.html written by
gen_report.py at the same path; Step E dot plot = delta vs band per comparison), evidence dir, plan section 7 by the peer. Scripts: exec/i4525-20260922/{chain4.sh (driver), build2.sh, smoke.sh,
campaign.sh, summarize.py, stepc-base.sh, gen_report.py, README.md}; chain.sh/chain2/chain3/build.sh/host-suite.sh are the
superseded versions (kept). Related: [[issue4525-design-review]], [[platformd-011-restarts-stopped-units]], [[3bda-shared-with-bill]].
