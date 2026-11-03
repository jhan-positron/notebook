---
name: glimci-20261017-campaign
description: "DONE 2026-10-17 19:41 UTC (9/9 passes): CI-config round for the Glimmer kv_mul-16 PR: the nightly's Glimmer tp4 @8u cell (2 tp4 engines via platformd 0.11 + proxy, prompt 1024 sharegpt, 1536 gen, 10 rounds) on the whole 3bda, arms base (nightly deb 2026.10.17-3751511d) / amxoff (branch deb + TRON_AMX_DISABLE=1 via config.env) / amxon, 3 passes each; scripts exec/glimci-20261017/, results exec/results/glimci-20261017/; nightly reference 78.69 TPS, TTFT 3697 ms"
metadata:
  node_type: memory
  type: project
  originSessionId: 2286d13f-0c9b-4afd-a521-f1f97342a0e9
  modified: 2026-10-17T18:06:53.866Z
---

jhan 2026-10-17 ~17:55 UTC: "Here is CI test of the model, ingested-meta-models--Muse-Glimmer-30B-tp4 @8u per machine:
78.7 TPS (placeholder threshold), prefill~277 tok/s, TTFT 3697ms (@1k prompt) ... do another round of test and this time
use identical CI config (with and without AMX). We expect similar decode/prefill/TTFT results as CI when AMX is not used,
and we will see the AMX boost at CI config. Note that 1k prompt in CI might mean 1.5k, please double check. Add the test
result to PR description and muse-glimmer-amx-results.html".

Facts verified 2026-10-17:
- Nightly run 38999609242 (systems_test main 740dc31, 03:39-13:13 UTC, failure overall but the Glimmer perf cell ran
  05:28-05:33 UTC): 2 engines default-0/1 (tp4, 4 users each behind the test proxy), Config prompt_length=1024
  generate_length=1536 n_rounds=10 capture 896-1024 sharegpt; 80 samples: TPS 78.69 (sd 0.48), TTFT 3697 ms (sd 188);
  "prefill 277 tok/s" = 1024 / TTFT (testlib/tps.py _ttft_sample_metrics proxy), not a measured prefill rate.
- "1k prompt" = the harness target 1024 incl. chat template: offline with the Glimmer tokenizer (HF cache) the 80 prompts
  are 925-1023 tokens (mean 992) after apply_chat_template; raw content 842-996. Not 1.5k. The server's usage.prompt_tokens
  per request is recorded by the driver (perf.json raw[0].prompt_tokens) and the engine journal gives "Request with N tokens in".
- Installed on 3bda: tron 2026.10.17-3751511d (rinzler sha 899a10d38a42...), platformd 0.11.1, 2 production tp4 engines
  (llama 3b/8b/70b + gpt-oss), Bill marker present but Bill idle, lease free (Saturday), td sessions done (4 probe markers).
- Deb build of the branch on 3bda outside nix: exec/glimci-20261017/build-deb.sh (make TOKENIZER_PYTHON_VERSION=3.12.7
  NPROC_BUILD=48 deb in /var/tmp/jhan/tron-g16, deb preset already has TRON_AMX_DISPATCH=ON) -> /var/tmp/jhan/glimci-20261017/
  target.deb; started 17:58 UTC. `nix develop` in that worktree now tries to rebuild a huge dev shell (LLVM 21, haskell) -> do
  not use nix on 3bda for this worktree; the clang-format check is left to CI.
- Driver = exec/q4b-fpga-20260921 fork (campaign.sh, dut.sh with ensure-target / amx-off / amx-clear / verify-env VERIFY_AMX /
  journal-prompts, st_ci_perf.py unchanged, configs-glimmer.json = the perf.py entry verbatim, launch.sh, summarize.py).
  Check mode passed 18:05 UTC. systems_test checkout fast-forwarded 14f0ce4 -> 740dc31 (= the nightly's commit).
  Deadlines: DEADLINE_START 23:30Z, PASS_DEADLINE 00:50Z, DRIVER_END_BY 01:20Z (pre-CI hold 01:40Z). PASSES base amxoff amxon x3.

**Why:** the PR body needs the measurement at the exact CI configuration (reviewers compare with the nightly's row).
**How to apply:** after .done: python3 exec/glimci-20261017/summarize.py -> summary.md; put the arm table into the PR body
section "Performance at the CI configuration" (exec/glimmer-20261016/pr-body.md, placeholder PENDING_CI_SECTION) and into
muse-glimmer/muse-glimmer-amx-results.html (gen_page.py). Related: [[glimmer-kvmul16-implementation]],
[[ci-mimic-20260918-campaign]], [[q4b-fpga-20260921-campaign]], [[3bda-shared-with-bill]].

RESULT (2026-10-17 18:15-19:41 UTC, 9/9 passes rc 0, restore pending at the time of writing): mean over 3 passes, TPS per user:
base 78.69 (sd 0.13; nightly's own row 78.69), amxoff 78.60 (-0.1 %, t -0.4), amxon 82.27 (+4.6 % vs base, paired t 33.1;
+4.7 % vs amxoff, t 13.1). TTFT 3780 / 3781 / 3651 ms (-3.4 %). Prefill proxy 270.9 / 270.8 / 280.5 tok/s. Server prompt
tokens 992 mean (925-1023) in every pass = the offline count. AMX busy probe: amxon 5.5-5.6 G cycles, others 0. Summary:
exec/results/glimci-20261017/summary.{md,json}; PR body section "Performance at the CI configuration" and results page
section 9 written from it.


Former index hook (moved from MEMORY.md on 2026-10-21 to keep the index under its size limit): 2026-10-17 nightly harness on whole 3bda, arms base/amxoff/amxon x3; nightly ref 78.69 TPS / 3697 ms; "1k" = 925-1023 tokens
