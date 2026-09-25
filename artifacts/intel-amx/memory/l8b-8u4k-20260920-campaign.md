---
name: l8b-8u4k-20260920-campaign
description: "DONE 2026-09-20 21:36 UTC: llama-3.1-8b one-cell campaign (8 users per engine = 32 users, prompt 4096; nightly deb vs canonical-AMX deb, CI harness, nightly layout, whole 3bda, 3 interleaved passes) per CI-test/status/llama-3.1-8b-8u-4k-plan.md; result +14.0 %, scripts exec/l8b-8u4k-20260920/, results exec/results/l8b-8u4k-20260920/, report + source I"
metadata: 
  node_type: memory
  type: project
  originSessionId: ff44b63e-7a6a-4b2c-b5a8-a3b5dd9ab60c
  modified: 2026-09-21T02:09:48.375Z
---

Plan: ~/workspace/intel-AMX/CI-test/status/llama-3.1-8b-8u-4k-plan.md (jhan: "Act per" the plan, 2026-09-20 19:3x UTC = approval,
which the plan defines as the order to take Bill's marker). Fills the cell the Saturday grid lacked: 8 users per engine at prompt
4096 (Saturday had 8u x 1024 +10.8 %, 8u x 2048 +14.0 %, 2u x 4096 +8.2 %). Pre-registered band +11 to +21 % (plan section 7).
Section 12 of the plan file = execution notes and two corrections to the plan text (dut.sh OUT is fixed at
/var/tmp/jhan/canon-ci-20260918, not "follows NAME"; the saved nightly.deb already existed).

RESULT (6/6 passes, outcome "campaign done", no failures): base 28.24/28.24/28.26 vs canon 32.20/32.18/32.24 TPS -> +14.01 %
(paired t 338.5, resolved, inside the band, +0.02 points vs the Saturday 8u x 2048 cell). TTFT 19.0 s / 11.5 s. Slowest sample
27.59 / 31.63, p05 27.76 (clean, candidate goal value). AMX-busy 0 vs 30.1-30.2 G cycles. Requests 80/80/80/80 per engine every
pass, 0 anomalous samples, 0 Caddy health events, server prompt tokens exactly 4096, client PSI < 1 %. Cell 13.1 min (base) /
10.6 min (canon); passes 14 / 11 min; whole campaign 19:49-21:36 UTC.
Report: CI-test/status/llama-3.1-8b-8u-4k.html (ASCII, 3 SVG charts checked with cairosvg) = artifact published 2026-09-20 21:4x UTC
(url in the session's final message; republish with the same file path from this session, or url= from another).
CI test-shapes page: PR3879/new-PRs/PR1/CI-AMX-test-shapes.html regenerated with source tag I (v4; i_registry.py in
exec/l8b-8u4k-20260920/ reads summary.json at generation time; I_RES env var points it elsewhere); previous page kept as
CI-AMX-test-shapes.v3-20260919.html. NOT done (jhan decides): filing the shape in systems_test, notebook preservation, Slack.

Scripts exec/l8b-8u4k-20260920/ = copies of exec/l8b-levers-20260919/ with plan section 4 changes: configs.py one cell
(llama_3_1_8b_instruct_good_tp2_32u_p4096), campaign.sh NAME/deadlines/DRIVER_TIMEOUT 2400/CHECK=0, launch.sh paths + md5 list,
prompt_check.py LENGTHS=[4096], analyze.py (one-cell verdict + Saturday reference rows read from l8b-levers summary.json),
gen_report.py (dumbbell with reference rows, per-pass chart, gain-vs-prompt chart with the band). dut.sh, st_ci_perf.py,
talos_stub unchanged.

Pre-launch review (workflow wf_9b29b757-934, 3 lenses, 10 findings, 1 confirmed): with ONE config, a pass failing twice at
request level trips the Saturday "two driver runs with 0 configs" stop (C21) and ends the campaign against plan 2a; FIXED before
launch: zero_runs counts only runs without 'Running round' in driver.log, and the known-failure repeat shortcut is disabled
(systematic=0). TRAP for future one-config forks of the l8b-levers driver: re-apply both. The 50-min 'need' floor makes the
effective last-pass start DRIVER_END_BY - 50 min, whatever PASS_DEADLINE says.
Pre-launch gates: check mode rc 0, prompt check 320 prompts at 4096 0 exceptions deterministic, md5 equal on 3bda, installed
nightly deb 0 AMX tile insns / 0 TRON_AMX_DISABLE strings, canon target 98 insns (my regex; the build's regex gives 86).
Source-I workflow (wf_33e73314-59d): pair-valued registry entries ("a / b") are invisible to gen_ci_shapes.py's audit; register
halves as single keys (i_ttft_base / i_ttft_amx) when a half appears in the text.

COMBINED PAGE (jhan's request 2026-09-20 22:0x UTC, "one file for all the tests"): CI-test/status/llama-3.1-8b.html = generator
exec/l8b-8u4k-20260920/gen_combined.py, which imports BOTH campaign generators as modules (importlib with argv cleared, sun.wrap
monkeypatched to fix the Sunday subtitle) for their tables/charts and adds a TOC, two combined charts (8-cell dumbbell, gain vs
KV with three lever series) and fresh plain-English prose. Reviewed by two workflow rounds (wf_b75ceed4-177: 27 confirmed
factual/completeness + 47 English; wf_472c7acb-fe5: 29 English + 8 numbers), all applied. TRAPS found there: (1) the Saturday
observed_overhead() averages the clipped 4096 runs (value 0) into the server overhead -> 29.0; the correct below-4096 mean is
33.8 tokens (Saturday page still prints 29.0); (2) "N users x prompt" means users per ENGINE in the plan words but users in
TOTAL in the harness names: use "users per engine" everywhere; (3) the Saturday wait for the issue4500 session ended 14:25 UTC,
not 15:00 (Saturday page text is wrong); (4) 1.26 speed ratio gives +21 % only "when attention is most of the step".
jhan's question "best AMX perf = 8 users + 2k and 8 users + 8k?": best = 8 users PER ENGINE at 2048 (+14.0) and 4096 (+14.0);
no 8k cell exists (tokenizer truncation), and 8 users TOTAL (2 per engine) gives +1.5 (2048) / +8.2 (4096).

SECTION 9 of the combined page (jhan 2026-09-20 22:5x UTC: "yes" to proposing the shape): draft message to Rhys (AMX metric test =
row thresholds from AMX-on runs), the four systems_test changes (scripts/perf.py configs dict; testlib/prompt.py concatenation patch;
scripts/system_ci.py get_goal (model, 32) tps/min_tps in the CURRENT THRESHOLD COMPATIBILITY BLOCK = the enforced verdict;
thresholds/system_ci_perf.yaml granite entry users 32 average_tps/p05_tps = comparison mode + Q30 ratchet), the platform-gating
decision (configs are not platform-gated; genoa would run it), proposed thresholds 5 % below AMX (30.6 mean / 30.3 p05 / 30.0 min),
and the binary: 6f37cd2ed9 (jhan-amx-deb-preset) NOT in tron main (head 98bb8cb22f 2026-09-19), no PR -> test with the canon deb
/var/tmp/jhan/canon-ci-20260918/target.deb. Verified by workflow wf_20e43d69-6a0 (16 confirmed + 26 English, applied). Facts learned:
inventory.py:168 skips re-provisioning the same model (place the new dict right after the llama-8b entry); nightly 09-20 = run
35487126137, 03:39-13:08 UTC; gemma-4 placeholder 1.00 lives only in get_goal (no YAML row); the workflow runner label is system-ci.
jhan has NOT sent the message (his step).

SECTION 10 (prefill, jhan 2026-09-20 23:1x UTC): all prefill rates in CI and on our pages are DERIVED from TTFT, never measured
(perf.py:383 prefill_mean = configured prompt_length / rounded mean TTFT; Slack prints "prefill~1.5k tok/s" with a footnote; e.g.
1024/0.664 s = 1542). No server-side prefill timing exists. Page metrics: harness rate, per-request rate and uncached rate as ratios
of sums per pass (sum tokens / sum TTFT), cached share PER ARM (differs up to 3.8 points per cell, 10.5 per pass: Caddy routing),
gains + paired t for harness and uncached. RESULTS: harness prefill gain +65.8 % at 8u x 4096 (215 -> 357 tok/s, TTFT 19.0 -> 11.5 s),
+7.4 % (2u x 1024) to +75.8 % (2u x 4096, n.r. on harness because the cache share differed per pass; uncached +76.7 %, t 23.9);
8u series +8.2 (n.r.; uncached +10.3) / +28.5 / +65.8 %. TRAPS: the Saturday users-lever cells (4u, 8u at 1024) had 29-34 % cached
tokens (same prompts as the 2u cell; one third of requests fully cached, TTFT < 50 ms), not only the long-prompt cells; per-request
TTFT at 8 users/engine includes the queue behind the other users' prompts, so absolute rates are not comparable across user counts.
Verified by workflow wf_f11e32ce-e1e (12 confirmed + 10 English, applied) and a final numbers re-check.

Machine after the run (verified 21:37 UTC): nightly deb 3faba6d0, 4 engines running the on-disk rinzler (serving llama-3.1-8b,
the last provisioned model; before the campaign they served qwen-3-4b), marker /bill-has-instance-0,2 present, flock free,
config.env 0 bytes, no lease, no sleep holders.

**Why:** the plan pre-decides everything; this records the execution, the numbers and the traps for the next one-cell campaign.
**How to apply:** for another single-cell run copy exec/l8b-8u4k-20260920/ (it already carries the one-config fix); see
[[l8b-levers-20260919-campaign]] for the driver's traps and Saturday numbers, [[3bda-shared-with-bill]] for the marker protocol,
[[canon-ci-20260918-campaign]] for the arms, [[ci-amx-test-shapes-recommendation]] for the page that now carries source I.
