---
name: first-ci-amx-row-20260922
description: "2026-09-22: first nightly with the 'AMX benchmark' row (llama-3.1-8b tp2 @32u, prompt 4096, gen 1536) read 28.3 TPS = our no-AMX-kernels base (28.248) to +0.02 %; package 2026.09.18-3faba6d0 has 0 AMX code (PR #4505 open, publish-deb broken 09-19..22, fixed by PR #4510 03:50Z); expected after AMX ships ~32.2 TPS; page CI-test/status/first-CI-AMX-row-20260922.html"
metadata:
  node_type: memory
  type: project
  originSessionId: 23fd8660-e9b4-4144-9475-e2c0f3397e73
  modified: 2026-09-22T17:43:10.060Z
---

Question (jhan 2026-09-22 ~17:30 UTC): does the first CI AMX-benchmark row, `llama-3.1-8b-instruct-good-tp2 @32u per
machine (AMX benchmark): 28.3 TPS`, align with our expectation? Answer: yes, with the expectation for a build WITHOUT the AMX kernels (do not say "AMX-off": that project term means the TRON_AMX_DISABLE kill switch of a build WITH kernels; the old "2-5 points slower" figure came from the retired August K-mirror layout build, and on the canonical-kernel code the kill switch runs at no-kernel speed: 14.745 vs 14.650 tok/s, exec/results/qwen8u8k-pr1-half-20260909T1704.txt).

Verified facts (session 23fd8660, 2026-09-22 17:3x UTC; evidence in exec/first-ci-amx-row-20260922/facts.md):
- Nightly 3bda run = systems_test 35683952944 (03:39Z, head 7327184 = merge of PR #221 at 01:34Z). apt removed and
  reinstalled tron 2026.09.18-3faba6d0 (log line 391; Slack "Tron did NOT update"). Installed rinzler sha256 27e6883c...
  == our l8b-8u4k base-arm binary; strings TRON_AMX_DISABLE 0, objdump AMX tile insns 0 (AMX build: 1 / 86).
- Row config in the log (line 1211): n_users=32, prompt_length=4096, generate_length=1536; merged perf.py entry has
  start_capture 896 / end_capture 1024, benchmark_label "AMX benchmark", placed after the @8u llama-8b entry, so it ran
  on the already-provisioned 4 engines ("already provisioned, verifying engines are healthy"). platformd 0.11.0
  ("provisioning mode: explicit"); ours ran on 0.10.7 legacy posadm.
- Row samples (parse_row.py): 320 Done lines, mean 28.253 TPS, sd 0.163, min 27.79, max 28.73, p05 27.97, TTFT 18.65 s,
  10 rounds 04:10:12-04:22:58Z, running averages 28.21-28.28. Our base 28.236/28.244/28.263 (mean 28.248), TTFT 19.03 s
  -> CI is +0.006 TPS (+0.02 %) above; inside our 0.027 TPS pass spread. Canon (AMX) arm 32.206 mean (+14.01 %), TTFT 11.48 s.
- Genoa (AMD andoria-b1a3) run 35682128668 has the same row: 29.00 TPS (sd 0.455, TTFT 13.3 s); no AMX unit there.
- Timeline: tron PR #4505 (deb preset AMX ON) OPEN, approved by jadams 09-21, checks green, NOT merged. publish-deb.yml
  schedule failed at startup 09-19/20/21/22 (01:35Z); PR #4510 "Declare Debian validation workflow permissions" merged
  2026-09-22T03:50:49Z -> next scheduled deb (09-23 01:35Z) should build from main head, still WITHOUT AMX unless #4505
  merges first. Rhys in #ci-cd-notifications 09:50 PDT: new tron version tomorrow; "This initial run is a baseline with
  no AMX changes present."
- Slack labelled rows print one decimal (28.3); 0.0 TPS would mean a crash (see [[pr221-rhys-amx-benchmark-review]]).

Page: CI-test/status/first-CI-AMX-row-20260922.html = artifact https://claude.ai/artifact/5o5tbk7c5H4VNvmK6tkgGN (published 2026-09-22 ~18:2x UTC; republish with the same file path from this session, or url= from another) (generator exec/first-ci-amx-row-20260922/gen_page.py reads
nightly_rows.json + exec/results/l8b-8u4k-20260920/summary.json; chart.svg rendered with cairosvg; ASCII-only).
Verification workflow wf_b0e651b2-8c4 (6 claims x 3 lenses + critic, 19 agents, 2.8 M tokens): 18/18 verdicts upheld; 12 final
corrections applied to the page (see exec/first-ci-amx-row-20260922/facts.md "Corrections after verification"). TRAPS learned:
(1) the 17:34Z hash was of a rinzler OUR q4b-fpga campaign re-installed at 16:11Z from the saved nightly.deb, not the row-time
process: state binary identity through the package (0 B downloaded, same version) + our base passes' process hashes; (2) the log's
"Running averages" are cumulative, per-round means span 28.16-28.37; (3) the CI TTFT is 2.0 % (388 ms) below ours = 8x our
pass-to-pass TTFT range -> real, cause unresolved; (4) nightly per-engine split is inferred (sd 0.163), not measured; (5) engine-side
monitor/cumulative/anomalous_sessions rose to 75-80 per engine in our base passes (meaning unknown) -> never write "0 anomalies";
(6) PR #4258 (self_attention.hpp, merged 09-18 19:32Z after the 09-18 build) may move the next no-kernel base; (7) a full publish-deb
build is untested since 09-18 (16:43Z run cancelled after 76 s); (8) if #4505 merges before the 01:17Z cron the SAME night's package
carries AMX.

**Why:** every AMX night from now on will be compared with this row; the first reading must be attributed to the
package, not to AMX.
**How to apply:** for each new nightly, first check the package (strings count of TRON_AMX_DISABLE = 1 and PR #4505
merged before that night's publish-deb), then compare: no-kernel build ~28.2-28.3 TPS, kernels-in build ~32.2 TPS est. (band 31.4-34.2 if the base holds; TTFT est. 11.2-11.5 s).
Re-run parse_row.py on `gh run view <id> --log` to get the row statistics. Related: [[l8b-8u4k-20260920-campaign]],
[[ci-enable-20260917-campaign]], [[nightly-amx-check-20260916]], [[pr221-rhys-amx-benchmark-review]].

FOLLOW-UP 2026-09-23: the first night WITH kernels (package 2026.09.23-5cf65b92) read 32.494 TPS; see [[ci-amx-row-20260923]].
