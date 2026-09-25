# Plan: llama-3.1-8b at 8 users per engine and prompt 4096, canonical-AMX deb against the nightly deb

Written 2026-09-20 19:4x UTC on jhan's request ("same test setup as Saturday-llama-3.1-8b.html, compare AMX canonical
with pre-AMX at the new config: 8 users per engine at 4096 prompt length"). It is a handoff for the executing agent in
the form of CI-test/status/Saturday-plan.md, and it reuses that campaign's scripts, arms, machine handling and decision
rule. Only the config grid changes: one cell, 32 users in total (8 per engine), prompt length 4096.

## Short version

One campaign measures, with the nightly's own client (the CI harness) against rinzler engines in the exact nightly
layout on the whole of delphi-3bda, the AMX kernel's gain on llama-3.1-8b at 8 users per engine and prompt length 4096,
nightly deb (no AMX code) against canonical-AMX deb, 3 interleaved passes of one cell each per arm. It fills the cell that
the Saturday grid did not have: the Saturday run measured 8 users per engine at prompt 1024 (+10.8 %) and 2048 (+14.0 %),
and 2 users per engine at 4096 (+8.2 %). Expected duration about 2.3 h (est.), pre-registered expectation +11 % to +21 %
(section 7).

## Words used here

- tron = the inference program under test. rinzler = its production server. One running rinzler = one engine. tp2 = two
  FPGA cards per engine (FPGA = field-programmable gate array, the accelerator card that runs the dense part of the model).
- nightly = the systems_test CI (continuous integration) run on delphi-3bda at 03:30 UTC. The perf phase = its decode-speed
  benchmark (scripts/perf.py).
- CI harness = the nightly's client code (systems_test scripts/perf.py, testlib/tps.py), run from the checkout
  /home/jhan/workspace/ai-runs/systems_test with its .venv through the Saturday driver st_ci_perf.py (records every sample,
  replaces the Talos results database with a stub, checks the running binaries, counts requests per engine, probes AMX use).
- nightly layout = 4 tp2 engines provisioned by platformd (the production process manager) behind the Caddy proxy on
  port 80. The harness's user count is spread by Caddy over the 4 engines: 32 users in total = 8 users per engine.
- AMX = Intel Advanced Matrix Extensions. The kernel (PR #3879, merged) is compiled only when the CMake option
  TRON_AMX_DISPATCH is ON. The nightly deb does not set it. The nightly's rinzler therefore has no AMX code ("pre-AMX" in jhan's
  words).
- arm = one installed package (clean or canon). A pass = one run of the cell on one arm. A cell = one benchmark run of one
  config on one arm.
- TPS = decode tokens per second per user, measured by the harness over generated tokens 896 to 1024 of each request.
  TTFT = time to first token. The slowest sample = the lowest single-user TPS of any round. p05 = the 5th percentile of the
  samples.
- KV tokens per engine step = users per engine x context per user at the capture window, the attention work of one decode
  step. Context per user here = 4096 prompt tokens + about 960 generated tokens (section 5).
- paired t = the mean of the per-pass gains divided by its standard error over the 3 passes.

## 1. Arms and their identity (unchanged from Saturday)

| arm | package | AMX code | how to install |
| clean | nightly deb tron 2026.09.18-3faba6d0 (installed on 3bda on 2026-09-20 19:25 UTC, rinzler sha256 27e6883c...) | none (objdump count of AMX tile instructions: 0) | dut.sh ensure-base 2026.09.18-3faba6d0 27e6883c2e8696b861589272470d5f6a4ec5485f6e8cd2ad163ae699f1dc6616 |
| canon | tron_2026.09.18-0594dc54-jhan-ci-canon_amd64.deb at /var/tmp/jhan/canon-ci-20260918/target.deb (present on 3bda, manifest head 0594dc5402) | yes (86 AMX tile instructions, kill-switch literal 1) | dut.sh ensure-canon |

The canon deb was built from main 3faba6d0fd plus only the two-line CMakePresets.json change 6f37cd2ed9
(TRON_AMX_DISPATCH=ON in the deb preset). PR #4424 (the VNNI K layout) is not in it. The two arms therefore differ only in
the AMX kernel being compiled in.

Rules carried over from Saturday:

- The base arm must be the exact package 2026.09.18-3faba6d0, the source commit of the canon deb. At preflight, run
  `dut.sh save-base-deb 2026.09.18-3faba6d0` (it downloads the deb from the repository index or copies it from the apt
  cache). No saved copy exists on 3bda at the time of writing. If the download fails, stop and report: the comparison
  needs this package.
- If the nightly has installed a newer version by the run day, the campaign still installs 3faba6d0 for the clean arm and
  reinstalls the version found at preflight in its restore step. Record both versions in the report.
- REQUIRED after every package switch: restart the engines (dut.sh serving-down, then the pass's provisioning starts them).
  apt never restarts engines, and the legacy provisioning path of platformd v0.10.7 does not restart a same-model engine.
  Without the restart a pass would run the previous arm's deleted binary. The driver stops a pass (rc 7) when a pid runs a
  deleted or foreign binary after provisioning, and the after-provision snapshot must show every engine pid on the
  installed sha.
- Per cell, the AMX-busy probe (20 s of the EXE.AMX_BUSY hardware counter on the four engine pids) confirms which arm ran:
  0 cycles on clean, about 30 billion cycles on canon at this load (the Saturday check cell at 32 users read 30.7 billion).

## 2. Machine, time window, permissions

- Whole machine: the nightly layout needs all 8 FPGA cards, so Bill's marker /bill-has-instance-0,2 must be taken
  (`bash ~/workspace/intel-AMX/exec/bill-share.sh take` on 3bda, which launch.sh runs). Take refuses while Bill is active
  (rc 2). jhan's approval of this plan is the order to take the marker for this run. Interrupting Bill while he is active
  stays jhan's call (section 2a).
- CI lease: /run/lock/systems-test-ci.lease is busy while the nightly runs (started 03:30 UTC, clears about 13:20 UTC).
  Busy only if the file exists AND state == "busy" AND now < expires_at_epoch. The driver waits for it (dut.sh lease-free).
- Campaign flock /var/tmp/jhan/3bda-campaign.lock: the driver takes it for the whole run. Before launching, check
  `flock -n /var/tmp/jhan/3bda-campaign.lock true` and the other sessions' exec/logs/*.status files. At the time of
  writing every campaign has finished (issue4500-m6 2026-09-19 18:40 UTC, q4b-swattn 2026-09-20 18:01 UTC), the flock is
  free, and 4 production engines serve qwen-3-4b (the q4b-swattn restore left them up).
- Hard limits: the pre-CI hold starts 01:40 UTC. The ci-runner-stop timer brings production inference up at 02:45 UTC.
  The nightly apt reinstall runs about 03:39 UTC. The campaign needs about 2.3 h (est., section 8) plus a 16-min restore.
  Deadlines for campaign.sh: DEADLINE_START (campaign start) = 22:00 UTC, PASS_DEADLINE (last pass start) = 00:20 UTC,
  DRIVER_END_BY = 01:00 UTC. On 2026-09-20 the campaign can start any time between now and 22:00 UTC. If it does not
  start by then, the next window opens on 2026-09-21 about 13:20 UTC, when the lease clears.
- Client host: the driver runs detached on the client host (claude-agentsrv), as on Saturday. Check its load before
  launching (the 2026-09-18 ci-mimic run had a CPU-saturated client, which inflated TTFT and stalled samples). The driver
  records client CPU pressure per config. Report it.
- During the CI window only light work (reading, editing scripts, the offline prompt check of section 3).
- At the end: nightly deb reinstalled, production engines up (HANDOFF=up), Bill's marker released, the flock released,
  /opt/positron/user/config.env still 0 bytes (it is 0 bytes now).

## 2a. Running without jhan: what the agent decides alone, and the one point that needs him

Everything below is pre-decided. The agent does not ask jhan during the run.

- Bill's marker: if `bill-share.sh take` refuses, wait and retry every 30 min until DEADLINE_START. If it still refuses,
  stop and report. Only jhan can decide to interrupt Bill. This is the one point that needs him.
- Late start: if the lease, the flock or the marker is still busy at DEADLINE_START, stop and report. Relaunch in the next
  window with the same plan.
- A pass fails (driver rc not 0, or a deleted-binary stop): restart the engines and repeat that pass once. If it fails
  again, continue with the next pass and report the gap. Analysis uses the passes that completed on both arms. Fewer than
  2 pairs = report the numbers without a verdict.
- The decision rule (section 7), the config (section 5) and the arm identities (section 1) are not changed for any
  reason. Never add configs.
- Do not file anything in the systems_test repository, do not post to Slack or GitHub, do not touch the nightly's
  checkout or Bill's half beyond the marker. The output is the results directory and the report (section 9). jhan
  decides filing.
- If anything on the machine looks wrong (lease busy mid-run, platformd down, unexpected installed package), stop safely:
  restore the nightly deb, HANDOFF=up, release Bill's marker and the flock, confirm config.env is 0 bytes, then report.

## 3. Prompt source (already in place, re-check offline before launching)

The Saturday change to PromptGenerator.generate (concatenate the following ShareGPT conversations until the prompt is
long enough, copying the stored lists) is still in the driver's checkout: testlib/prompt.py in
/home/jhan/workspace/ai-runs/systems_test has md5 da8ba0e1a18b..., equal to exec/l8b-levers-20260919/prompt.py.after.
The nightly's own checkout is untouched. The Saturday offline check (exec/results/l8b-levers-20260919/prompt-check/
run1.json and run2.json) ran seeds 0 to 319 at prompt lengths 1024 to 8192 with 0 exceptions and identical token counts on
two runs. 32 users x 10 rounds use exactly seeds 0 to 319.

Before launching, re-run exec/l8b-levers-20260919/prompt_check.py for prompt length 4096 and seeds 0 to 319 in the .venv
with HF_HUB_OFFLINE=1, and record its output in the new results directory. Launch only with 0 exceptions.

Known property of prompt 4096 on this deployment (found on Saturday): the deployed tokenizer.json of
llama-3.1-8b-instruct-good carries a right-truncation at 4096 tokens. The harness sends a 4096-token conversation, the
server adds its system line and chat template (about 34 tokens, measured on Saturday at prompt 1024), and the server then
keeps the first 4096 tokens. So the last tokens of the request (the end of the last user turn and the assistant header)
are dropped, and the server counts exactly 4096 prompt tokens. Decode speed is measured either way. The Saturday cell at
2 users per engine and prompt 4096 ran under the same property. Keeping prompt_length 4096 therefore makes the new cell
comparable with it. Alternative for jhan, not the default: prompt_length 4062 keeps the template intact (4062 + 34 =
4096). jhan decided on 2026-09-19 to do nothing about the truncation itself.

## 4. Driver changes (copy exec/l8b-levers-20260919/ to exec/l8b-8u4k-20260920/, never edit a running script)

1. configs.py: GRID = [(32, 4096, "8 users per engine at prompt 4096, context lever at the recommended load")]. Write
   configs-full.json only (one dict). Name llama_3_1_8b_instruct_good_tp2_32u_p4096 (the harness keys its summary by name
   and user count).
2. campaign.sh: NAME=l8b-8u4k-20260920, results exec/results/l8b-8u4k-20260920/, log exec/logs/l8b-8u4k-20260920.log,
   PASSES="base canon base canon base canon" (unchanged), CHECK=0 (section 6 says why), EXPECTED_BASE=2026.09.18-3faba6d0,
   DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY per section 2, DRIVER_TIMEOUT=2400 s per pass (one cell of about 11 to 13
   min plus provisioning, section 8), HANDOFF=up, AMX_PROBE=1. Everything else unchanged.
3. dut.sh: no change, its OUT directory follows NAME. Run save-base-deb at preflight (section 1).
4. st_ci_perf.py, talos_stub, lib-guard.sh: unchanged copies. launch.sh: update the md5 list to the new file names, keep
   the bill-share take and the prompt-check gate.
5. analyze.py and gen_report.py: adapt to one config, and add the three Saturday cells of section 7 as reference rows
   (read from exec/results/l8b-levers-20260919/summary.json, not retyped). Feed the result into
   exec/canon-ci-20260918/gen_ci_shapes.py as a new source tag (I) so the CI test-shapes page can list the cell.

## 5. Config (one pass = this one cell, llama-3.1-8b-instruct-good-tp2, generate_length 1536, start_capture 896,
## end_capture 1024, prompt_mode "sharegpt", user_sets [], shared_prompt_length 0)

| name | nominal_users | users per engine | prompt_length | KV tokens per engine step (K) | purpose |
| llama_3_1_8b_instruct_good_tp2_32u_p4096 | 32 | 8 | 4096 | 40.4 | context lever at the recommended load (T1 shape with a 4x longer prompt) |

KV arithmetic: 8 x (4096 + 960) = 40448 tokens (40.4K). The server counts 4096 prompt tokens (section 3). The
Saturday overhead of 31 to 34 tokens therefore does not add here. For scale, the Saturday cells were 16.1K (8 users per engine x
1024), 24.3K (8 x 2048) and 10.2K (2 x 4096).

KV memory per engine at the end of a round: 8 users x (4096 + 1536) tokens x 128 KiB per token (32 layers x 8 KV heads x
128 values x K and V x 2 bytes) = 5.5 GiB, against 128 x 1 GiB hugepages per engine. The Saturday check cell already ran
32 users with 4096 server-side prompt tokens and 1536 generated tokens on this deployment without error.

## 6. Before the first pass

1. No hand check cell (CHECK=0). The Saturday check cell ran the canon deb at 32 users with the server counting 4096 prompt
   tokens per request (the harness sent 8192, the server kept 4096): 320 requests, 10.5 min, 32.25 TPS, TTFT 11.5 s, no
   error, requests spread 80/80/80/80 over the engines. The Saturday cell at 2 users per engine and prompt 4096 ran
   prompt_length 4096 through the harness six times without error. Together they show the new cell is feasible on both
   the server and the client side.
2. Arm identity check of section 1 on the installed package (dpkg-query, objdump count, strings count).
3. Preflight via dut.sh preflight (lease, platformd, config.env bytes, canon deb present, installed version), then
   save-base-deb.
4. Offline prompt check of section 3.
5. md5 of every copied file equal on the client host and on 3bda (NFS attribute cache trap).

## 7. Decision rule and pre-registered expectations (do not change after seeing data)

- Canon against clean: paired t over the 3 passes (pass r of one arm pairs with pass r of the other). Resolved at
  |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |change| >= 1 %.
- Report per pass: clean TPS, canon TPS, gain %, TTFT, slowest sample, p05, duration, AMX-busy cycles, requests per engine.
- Reference rows from Saturday (same arms, same driver, same layout), all resolved:

| cell (Saturday) | clean TPS | canon TPS | gain | TTFT clean / canon (ms) | minutes per cell |
| 8 users per engine x 1024 | 67.03 | 74.26 | +10.79 % | 738 / 683 | 5.3 |
| 8 users per engine x 2048 | 45.83 | 52.24 | +13.99 % | 3150 / 2453 | 8.0 |
| 2 users per engine x 4096 | 104.72 | 113.30 | +8.19 % | 3609 / 2083 | 3.1 |

- Expected (est.): canon about 32 TPS (the Saturday check cell measured 32.25 TPS at this server-side shape), clean about
  28 TPS, TTFT about 11 s (canon) and about 14 s (clean, est. from the 2048 ratio). Gain band +11 % to +21 %. Reasoning:
  the 8-users-per-engine series rose from +10.8 % (1024) to +14.0 % (2048). The 2-users series rose from +1.6 % (2048)
  to +8.2 % (4096). The canonical kernel's per-unit speed ratio of about 1.26 puts its ceiling near +21 % when attention
  is most of the step.
- Reading the result: inside the band = the context lever keeps working at 8 users per engine, and the cell is a
  candidate long-prompt CI shape at the recommended load. Below +11 % = the gain saturates with load at this prompt
  length. Report it against the 2048 cell. Above +21 % = more than the kernel's speed ratio explains. Check the data
  quality (requests per engine, anomalous samples, client pressure) before believing it.
- CI relevance: no threshold exists for this shape. Record the clean arm's mean TPS, slowest sample and p05 as the
  candidate goal values, as the Saturday run did for the 32-user prompt-1024 shape (T1).

## 8. Duration (est.) and monitoring

- One cell: the Saturday check cell took 10.5 min on canon. The clean arm decodes slower (about 12 % from the band),
  so allow 11 to 13 min per cell. Plus about 3 min per pass for the AMX-busy probe, snapshots and request counting.
- Package switch and engine restart between passes: about 6 min (apt swap, settle, serving-down with the idle test,
  serving-up and re-provisioning).
- Six passes: 6 x (13 + 3 + 6) = about 2.2 h. With preflight, save-base-deb and the restore about 2.3 h (est.).
- Monitoring: read the .status file and driver.log over ssh with a periodic grep. A Monitor tail -F on the NFS copy of a
  file written on 3bda delivers nothing, and a trailing cut in a Monitor pipeline block-buffers. Run tail over ssh on the writer
  host and end the pipe with stdbuf -oL grep.

## 9. Outputs

- Results under exec/results/l8b-8u4k-20260920/<arm>-pass<k>/ (perf.json, talos.json, driver.log, summary.txt), the
  offline prompt check, the identity checks per pass, the AMX-busy probes, per-engine request counts, client CPU
  pressure, anomalous-sample counts, cell durations.
- summary.json and summary.md from analyze.py: per pass and pooled, with the paired t and the verdict of section 7.
- A report (HTML, light theme, plain English, Short version first) in CI-test/status/llama-3.1-8b-8u-4k.html, with the
  three Saturday reference rows next to the new cell and a chart of gain against prompt length at 8 users per engine
  (1024, 2048, 4096) with the 2-users-per-engine series for scale.
- The cell fed into gen_ci_shapes.py as source tag I.

## 10. Traps (from the Saturday run and this project's memory notes)

- The rinzler journal has no per-request line. The idle test reads the #EVT# SYSTEM_STATS line, and requests per engine
  come from the FUSE counter /var/run/rinzler/N/rinzler/stats/prompts_total.
- Production engines left running hold all 512 hugepages until the driver's serving-down step.
- Bash: `if run_pass; then ...; fi; rc=$?` gives the if-statement's status, never the command's. Capture rc first.
- Bash: helper messages on stdout pollute `$(helper | awk ...)` captures. Send them to stderr and validate captured values.
- pgrep -f patterns must be anchored, and a pgrep inside an ssh `bash -c` matches that bash itself. Exclude "bash -c".
- 3bda runs perf_event_paranoid 4. The probe uses sudo -n perf stat (standing approval). perf -x CSV column 4 is run
  time, not the count.
- NFS attribute cache: compare md5 on both hosts before launching. Never edit a script while it runs.
- Another session's campaign may hold the campaign flock only per run. Also check exec/logs/*.status before launching.

## 11. Sources

- Saturday plan and report: CI-test/status/Saturday-plan.md, CI-test/status/Saturday-llama-3.1-8b.html (generator
  exec/l8b-levers-20260919/gen_report.py, results exec/results/l8b-levers-20260919/).
- Saturday scripts to copy: exec/l8b-levers-20260919/{campaign.sh, dut.sh, launch.sh, st_ci_perf.py, configs.py,
  prompt_check.py, analyze.py, gen_report.py, talos_stub/}.
- Canon deb build: exec/canon-ci-20260918/build-canon.sh, manifest /var/tmp/jhan/canon-ci-20260918/manifest.json, report
  PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html.
- CI test-shapes page: PR3879/new-PRs/PR1/CI-AMX-test-shapes.html, generator exec/canon-ci-20260918/gen_ci_shapes.py.
- Kill-switch measurement of the same load lever on our half (2, 4, 8 users per engine at prompt 1024):
  VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html.

## 12. Execution notes (added 2026-09-20 21:4x UTC by the executing agent; the plan text above is unchanged)

- Run: launched 19:49:25 UTC, six passes 19:53 to 21:25 UTC (base 14 min, canon 11 min per pass), restore done
  21:35:58 UTC, outcome "campaign done" with no failures. Results exec/results/l8b-8u4k-20260920/, report
  CI-test/status/llama-3.1-8b-8u-4k.html, CI test-shapes page regenerated with source tag I (previous version kept as
  PR3879/new-PRs/PR1/CI-AMX-test-shapes.v3-20260919.html).
- Result: +14.01 % (28.25 to 32.21 TPS, paired t 338.5, resolved, inside the +11 to +21 % band, 0.02 points from the
  Saturday 2048 cell). TTFT 19.0 s clean / 11.5 s canon (the plan estimated 14 s / 11 s). AMX-busy 0 / 30.1 to 30.2
  billion cycles. Requests 80/80/80/80 per engine in every pass, 0 anomalous samples, client CPU pressure below 1 %.
- Two corrections to the text above: section 4 item 3 says dut.sh's OUT directory "follows NAME"; it is fixed at
  /var/tmp/jhan/canon-ci-20260918 (where the canon deb and the saved nightly.deb live). Section 1 says no saved copy of
  the nightly deb existed; nightly.deb 2026.09.18-3faba6d0 had been saved there on 2026-09-18 and the restore used it.
- One script change beyond section 4, from the pre-launch review: with one config, the Saturday rule "two consecutive
  driver runs with 0 completed configs stop the campaign" would have ended the campaign after one pass failed twice,
  against section 2a. campaign.sh now counts only runs that never reached the benchmark, and repeats every failed pass
  once (the known-failure shortcut is disabled). Neither path was exercised: no pass failed.
- Section 2 says the last pass may start at 00:20 UTC; the script's 50-min floor before DRIVER_END_BY makes 00:10 UTC
  the effective limit. Not binding tonight (the last pass started 21:14 UTC).
- After the restore the production engines serve llama-3.1-8b (the model the harness last provisioned), not the
  qwen-3-4b they served before the campaign; the plan only requires them up on the nightly deb.
