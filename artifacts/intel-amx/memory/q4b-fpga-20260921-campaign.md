---
name: q4b-fpga-20260921-campaign
description: "2026-09-21 campaign exec/q4b-fpga-20260921/ (fork of q4b-swattn): qwen3-4b tp2 prefill/decode vs prompt length with FPGA attention vs CPU attention, arms fpgabase/fpgacanon/canon (+ cold cells, optional vnnik arms), whole 3bda nightly layout, platformd 0.11 named engines; launched 2026-09-21 22:3x UTC for tonight's window (DRIVER_END_BY 02:15Z), remainder after the 09-22 nightly"
metadata: 
  node_type: memory
  type: project
  originSessionId: d431f4bb-1f10-45d3-99fe-097238cabbde
  modified: 2026-09-21T22:31:56.647Z
---

Request (jhan 2026-09-21 ~22:00 UTC): (1) update our harness for Rhys's platformd 0.11.0 upgrade of delphi-3bda (engine
"count" removed; every engine is a named entry default-N with its own ingress port 3000+N), (2) run the measurement of the
FPGA-attention prefill curve above prompt 1024 (section 6 of CI-test/status/qwen3-4b-prefill-amx-vs-fpga.html), (3) update
that page.

Harness update (done 2026-09-21 22:2x UTC):
- systems_test checkout ~/workspace/ai-runs/systems_test fast-forwarded fc27f07 -> e4727d5 (upstream main 09-21; our
  testlib/prompt.py patch kept via stash/pop). Upstream already has explicit provisioning (PLATFORMD_INFERENCE_MODE auto ->
  explicit for platformd >= 0.11.0: PATCH /api/config with named engines default-0..3 + ingress 3000+i, PUT
  /api/internal/proxy/default on port 80, health = every engine running/degraded/stopped; no shared "activity" field).
  123 unit tests pass. posadm CLI is still at /opt/positron/bin/posadm (not on PATH); versions also at
  GET /api/internal/maintenance/versions.
- Our wrappers: exec/q4b-fpga-20260921/dut.sh (engine_count = sum(count,1) over entries; preflight prints the entries and
  the platformd version; ensure-vnnik; VERIFY_HWATTN=set|unset for verify-env; serving-up idle = every engine settled),
  st_ci_perf.py (CI_MIMIC_REQUIRE_HWATTN_UNSET=1 for FPGA arms: rc 8 if any engine pid carries USE_HW_ATTN=0),
  campaign.sh (arms = deb x attention: base/canon/vnnik = USE_HW_ATTN=0 via config.env; fpgabase/fpgacanon/fpgavnnik =
  config.env cleared; switch_to sets the mode then restarts engines; cold tags <arm>-cold-p<len> run one single-cell
  driver run = fresh engines = cold prefix cache; no check cell), launch.sh (default deadlines tonight; TAKE_MARKER=0 so
  campaign.sh takes Bill's marker itself). CHECK mode (CI_MIMIC_CHECK=1) passed against platformd 0.11 at 22:29 UTC.
- The classifier denied the combined "patch + launch" Bash command; the launch alone was allowed.

Machine state at launch: platformd 0.11.0, tron deb 2026.09.18-3faba6d0 installed (= the base arm and the restore
target), 4 llama-3.2-3b tp2 engines left by Rhys (default-0..3, ingress 3000-3003, no port-80 proxy), config.env 0 bytes,
lease free, Bill idle, marker present (campaign takes it), ci-runner-stop timer 02:45 UTC.

Launch 2026-09-21 22:3x UTC: pid 1154400 (claude-agentsrv), log exec/logs/q4b-fpga-20260921.log, results
exec/results/q4b-fpga-20260921/, DEADLINE_START 2026-09-22T00:30Z, PASS_DEADLINE 01:20Z, DRIVER_END_BY 02:15Z,
PASSES "fpgabase fpgacanon canon fpgacanon-cold-p8192 fpgacanon-cold-p4096 fpgabase-cold-p8192 fpgabase-cold-p4096".
jhan 2026-09-22 00:5x UTC: "AMX delivered 2x prefill performance comparing with software attention, 8k prompt length,
qwen3-4b ... include the past test data of software attention. Do not re-test software attention, just use past data."
-> CPU-attention arms in the report = the 2026-09-20 q4b-swattn series (base AVX 15,764 ms vs canon AMX 7,145 ms at 8192 warm
= 2.2x; runtron cold 121.7 s vs 53.3 s = 2.3x) plus tonight's canon-pass1 (already run before the instruction). Second launch
after the 09-22 nightly = FPGA arms ONLY: PASS_TAGS="fpgacanon-pass2 fpgabase-pass2 <the cold tags tonight did not reach>
fpgabase-pass3 fpgacanon-pass3 fpgacanon-cold2-p8192 fpgabase-cold2-p8192" (campaign.sh accepts <arm>-cold<N>-p<len> since
01:0x UTC). Then the page update via exec/prefill-amx-vs-fpga-20260921/{ingest_fpga.py,gen_page.py} (section 5 switches to the
measured curve automatically; fpga_section.py).
Tonight's run DONE 2026-09-22 01:25 UTC (.done, no problems): fpgabase-pass1 rc 0 (36 min), fpgacanon-pass1 rc 0 (31 min),
canon-pass1 rc 0 (39 min), cold cells fpgacanon/fpgabase at 8192 and 4096 (3-4 min each); restore ok (nightly deb, config.env 0,
production 4 qwen tp2 engines up on FPGA attention, marker + flock released). Results: cold 8192 FPGA 6,743 (AMX build) / 6,878
(AVX build) vs CPU AMX 12,743 (09-19 check cell); cold 4096 FPGA 2,932 / 3,063; warm 8192 fpgacanon 3,681, fpgabase 6,662,
canon-pass1 6,283 (09-20 canon passes 6,742-7,352). Every cell 20/20/20/20 engine spread; environment checks all ok.
SECOND LAUNCH DONE 2026-09-22 16:25 UTC (no problems, all 8 tags rc 0; counters recorded; journal hbm-journal-20260922.txt; page update with 3 passes per FPGA arm PENDING as of 16:50 UTC). Was queued 01:4x UTC: pid 4073541 (claude-agentsrv), NOT_BEFORE 13:00Z, DEADLINE_START 19:30Z, PASS_DEADLINE
2026-09-23T00:30Z, DRIVER_END_BY 02:15Z, TAKE_MARKER=0, PASS_TAGS "fpgacanon-pass2 fpgabase-pass2 fpgacanon-cold2-p8192
fpgabase-cold2-p8192 fpgabase-pass3 fpgacanon-pass3 fpgacanon-cold2-p4096 fpgabase-cold2-p4096" (est. 3.8 h from ~13:20 UTC).
After it: ingest_fpga.py + gen_page.py + cairosvg check + republish (artifact T6c2gB9zzJQsCukmC69e51), verify with a workflow.
Page v3/v4 published 2026-09-22 01:4x UTC with tonight's data (section 5 measured; 5 verification agents, findings applied).
HBM EXHAUSTION (found 2026-09-22 06:5x UTC, refined 07:3x UTC): 2,804 "HBM bypass space exhausted ... lose HW attention"
warnings in the engine journal; per cell see [[prefill-amx-vs-fpga-qwen3-4b]] (4096/5120 whole cell, 6144 first 3/4, 7168 none,
8192 from round 7/8; 509 = probe requests in the gaps; none in cold cells / CPU pass / earlier 1024 runs). It is a measured
co-occurrence at 4096-6144, NOT the cause of the AMX-build warm gains (2048, 7168, 8192 rounds 1-6 gain without any fallback).
Page v7 (07:3x UTC) says this in the Short version and sections 3/5/6/8. Files: exec/results/q4b-fpga-20260921/
hbm-journal-20260921.txt, exec/prefill-amx-vs-fpga-20260921/hbm_cells.py (re-run after the second launch with a new journal
pull; the command is in RUNBOOK.md).
FOLLOW-UP q4b-rt8u-20260922 (jhan "let's do it", 2026-09-22 06:4x UTC): runtron on our half, 8 users x 1024/2048/4096/8192 +
2 users x 4096/8192, arms base(pre3879 AVX)/canon(main0916), attn cpu/fpga interleaved, 3 reps, HBM-EXHAUSTION count per run;
DONE 2026-09-22 18:12 UTC (jhan relaunched by hand 16:58 after the classifier denial; first attempt at 16:36 stopped itself: platformd 0.11 restarted the units the guard stopped, see [[platformd-011-restarts-stopped-units]]). 72 runs, 0 HBM warnings; 8u x 8192 batched prefill AVX-CPU 123.1 s / AMX-CPU 53.5 s / FPGA+AVX 29.7 s / FPGA+AMX 29.1 s; decode 14.5/17.1/61.5/61.5 TPS per user; AMX build vs AVX under FPGA: prefill -0.3..-2.0 %, decode within 1.2 %. Results exec/results/q4b-rt8u-20260922/summary.{md,json}; page section 7 (rt8u_section.py).
Incident 23:12-23:36 UTC: my own dut.sh edit (awk -v regex, backslashes re-read) broke the idle test; fixed with an index()
lookup (atomic replace); the first launch ended HANDOFF INCOMPLETE and was relaunched 23:37 UTC (pid 1910785).

**Why:** the prefill AMX-vs-FPGA question was Insufficient data above prompt 1024; this campaign is the measurement the page
proposed, on the new platformd.
**How to apply:** never edit campaign.sh/dut.sh/st_ci_perf.py while a pass runs; stop with kill -TERM <pid> (restore path);
RECOVERY sequence in campaign.sh header. Related: [[prefill-amx-vs-fpga-qwen3-4b]], [[q4b-swattn-20260919-campaign]],
[[3bda-shared-with-bill]], [[3bda-nightly-rinzler-cleanup]].
