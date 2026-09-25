# Facts collected 2026-09-22 17:3x UTC for: "does the first CI AMX-benchmark row (28.3 TPS) align with our expectation?"

## The CI row
- Slack #ci-cd-notifications (C06S8PNDBQA), talos bot, GRANITE_RAPIDS_72_RINZLER DUT delphi-3bda, Nightly Report 2026-09-22, posted 06:20:34 PDT:
  ":exclamation: Tron did NOT update: v2026.09.18-3faba6d0 | Platformd v0.11.0"
  ":memo: llama-3.1-8b-instruct-good-tp2 @32u per machine (AMX benchmark): 28.3 TPS"
  also ":x: llama-3.1-8b-instruct-good-tp2 @8u per machine: 141.08 TPS / 144.00 threshold"
- Rhys Jordan in the same channel 09:50:27 PDT: "Tron did not update again, the fix in PR #4510 merged after the publish deb workflow started ... we will see a new tron version tomorrow. Platformd updated from 0.10.7 to 0.11.0. New TPS test was added, llama-3.1-8b-instruct-good-tp2 @32u per machine with prompt length of 4k and generation length of 1.5k to test the effects of AMX. This initial run is a baseline with no AMX changes present."
- GitHub run: systems_test run 35683952944 "System CI (Rinzler 72-core Intel system OCI version)", schedule, created 2026-09-22T03:39:22Z, head 7327184352f5 (= merge commit of systems_test PR #221), conclusion failure (the usual threshold failures, not a crash).
- Log (scratchpad/nightly-35683952944.log, 84686 lines): line 391 "Removing tron (2026.09.18-3faba6d0)" then apt-get install -y tron reinstalls the same version (no newer package in unstable).
- Row config in the log (line 1211-1220): n_users=32, model='llama-3.1-8b-instruct-good-tp2', tokenizer neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16, shared_prompt_length=0, prompt_length=4096, generate_length=1536.
- Before the row (04:10:04 UTC): "Model llama-3.1-8b-instruct-good-tp2 already provisioned, verifying engines are healthy", "All 4 inference engines are running", "All 4 Caddy upstreams are healthy". Provisioning mode for llama-8b at 04:07:25: "Selected platformd inference provisioning mode: explicit" (platformd 0.11.0 path).
- Parsed samples (scratchpad/nightly_rows.json, parse_row.py): 320 Done lines (10 rounds x 32 users), TPS mean 28.253, population sd 0.163, min 27.79, max 28.73, p05 27.97; TTFT mean 18646 ms (min 8280, max 21824); rounds 04:10:12 -> 04:22:58 UTC (12.8 min). Running averages per round: 28.25, 28.21, 28.25, 28.28, 28.26, 28.25, 28.27, 28.26, 28.25, 28.25.
- Genoa (AMD, andoria-b1a3) run 35682128668 same night: same row 29.0 TPS (320 samples, mean 29.00, sd 0.455, min 28.25, p05 28.38, TTFT 13266 ms). AMD has no AMX; the kernels take the AVX path there (memory amd-amx-fallback-test).

## The binary that ran
- On delphi-3bda at 17:34 UTC 2026-09-22 (ssh, read-only): dpkg tron Version 2026.09.18-3faba6d0, Status install ok installed; /opt/positron/bin/rinzler 232,667,936 bytes, mtime Sep 18 01:55, sha256 27e6883c2e8696b861589272470d5f6a4ec5485f6e8cd2ad163ae699f1dc6616; `strings rinzler | grep -c -x TRON_AMX_DISABLE` = 0; objdump AMX tile instruction count (tdpbf16ps|tileloadd|tilestored|ldtilecfg|tilerelease) = 0; /etc/rinzler/instance-*.env contain no TRON_AMX* / USE_HW_ATTN; apt cache holds tron_2026.09.16-f46e48ba, 09.17-31b80a18, 09.18-3faba6d0 only. Marker /bill-has-instance-0,2 present, no CI lease, load avg 8.8.
- Controls from memory (nightly-amx-check-20260916 / ci-enable-20260917): an AMX-enabled build gives strings count 1 and 86 (canon) or 126 (AMX+VNNI) tile instructions; the nightly packages give 0/0.
- tron PR #4505 (deb preset TRON_AMX_DISPATCH ON, branch jhan-amx-deb-preset, head a92a312249): state OPEN, reviewDecision APPROVED (jadams-positron 2026-09-21T16:07Z), checks green. Not merged => even a working publish-deb tonight ships a package WITHOUT AMX.
- tron publish-deb.yml scheduled runs: 09-18 success (3faba6d0), 09-19/20/21/22 startup_failure (09-22 run 35676322727 at 01:35:27Z, head 98bb8cb22f); 09-22 16:43Z workflow_dispatch run 35755947149 cancelled. PR #4510 "ci: Declare Debian validation workflow permissions" MERGED 2026-09-22T03:50:49Z (after the 01:35Z schedule) = the fix Rhys mentions.

## Our measurement of the same cell (memory l8b-8u4k-20260920-campaign; exec/results/l8b-8u4k-20260920/summary.json)
- Campaign 2026-09-20 19:49-21:36 UTC, whole delphi-3bda, CI harness (scripts.perf.test_performance via st_ci_perf.py from claude-agentsrv), nightly layout (4 engines behind Caddy, 8 users per engine = 32 users), 3 interleaved passes per arm, 320 samples per pass.
- Config (exec/l8b-8u4k-20260920/configs.py): model llama-3.1-8b-instruct-good-tp2, nominal_users 32, prompt_length 4096, generate_length 1536, start_capture 896, end_capture 1024, prompt_mode sharegpt, shared_prompt_length 0. Prompt SOURCE differs: ours = concatenated ShareGPT conversations (exec/l8b-levers-20260919/prompt.py.patch); Rhys's merged PR #221 = 320 appended long ShareGPT records; both exactly 4096 tokens (server prompt_tokens 4096 in our runs; PR review verified 320 distinct 4096-token prompts).
- Base arm = installed nightly deb 2026.09.18-3faba6d0, rinzler sha256 27e6883c... (identical to today's installed binary), AMX-busy perf counter 0 in every pass. TPS 28.236 / 28.244 / 28.263 (mean 28.248), per-pass sd 0.24-0.27, min 27.66/27.66/27.59, p05 27.76/27.75/27.77, TTFT 19010/19058/19036 ms, cache-hit 0.8 %, 80 requests per engine, 0 Caddy events, 0 anomalous samples, wall 787-788 s per pass.
- Canon arm = tron_2026.09.18-0594dc54-jhan-ci-canon (main 3faba6d0 + deb preset AMX ON; canonical AMX kernels; sha256 b273a2e1...), AMX-busy 30.1-30.9 G cycles per pass. TPS 32.199 / 32.181 / 32.239 (mean 32.206), min 31.63-31.77, p05 31.86-31.94, TTFT 11472-11486 ms.
- Gain +14.01 % (per pass +14.03 / +13.94 / +14.07), paired t 338.5 (n=3 pairs), pre-registered band +11..+21 % (plan CI-test/status/llama-3.1-8b-8u-4k-plan.md section 7) -> inside.
- Platformd during our campaign: v0.10.7 (legacy posadm provisioning path). Nightly 09-22: platformd 0.11.0 (explicit provisioning mode).
- Section 9.4 of CI-test/status/llama-3.1-8b.html proposed thresholds 5 % below the AMX value: mean 30.6 / p05 30.3 / min 30.0 TPS (for after AMX lands).

## Merged systems_test config (origin/main scripts/perf.py lines 73-86)
- name llama_3_1_8b_instruct_good_tp2, model llama-3.1-8b-instruct-good-tp2, nominal_users 32, benchmark_label "AMX benchmark", user_sets [], shared_prompt_length 0, prompt_length 4096, generate_length 1536, start_capture 896, end_capture 1024, prompt_mode sharegpt. Placed directly after the @8u llama-8b entry (inventory skips re-provisioning the same model).

## Comparison
- CI 28.253 vs our base 28.248: +0.005 TPS (+0.02 %). Slack rounds to 28.3 (1 decimal for labelled rows).
- CI TTFT 18.65 s vs our base 19.03 s (-2.0 %). CI sd 0.163 vs ours 0.24-0.27 (CI tighter). CI min 27.79 vs ours 27.59-27.66.
- Expected value once the nightly deb carries AMX (PR #4505 merged AND publish-deb succeeds): about 32.2 TPS (+14 %), TTFT about 11.5 s.
- Nightly llama-8b @8u row 141.08 TPS (3bda) = the known no-AMX level (139.8-141.1 over 09-16..09-22); with AMX at 2 users per engine we measured only +0.2..+0.8 %.
