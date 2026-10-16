---
name: canon-ci-20260918-campaign
description: "DONE 2026-09-19 00:22 UTC (jhan, ultracode): nightly CI perf phase by hand on the WHOLE of delphi-3bda, ONE arm = canonical-AMX deb (main 3faba6d0fd + deb preset TRON_AMX_DISPATCH=ON, commit 6f37cd2ed9, NO PR 4424); compared against the ci-mimic 09-18 base and target arms (not re-run); handoff to the issue4500 session; scripts exec/canon-ci-20260918/, report PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html"
metadata:
  type: project
---

Request (jhan 2026-09-18 21:5x UTC): "how would PR3879, the canonical AMX solution, perform at CI harness" after the
ci-mimic run (PR 4424 + AMX + VNNI-K) showed qwen-3-4b losses. Same 12 CI configs, no base re-run, product WITHOUT
PR 4424 but WITH the CMakePresets.json deb-preset change so rinzler compiles AMX. Decisions (jhan 22:0x UTC):
coordinate with session 65d0ce4e (= peer name vnnied-k-in-place-c3, issue4500-20260918 campaign) -> we go first,
handoff at our end; base commit and arm reuse = my call (3faba6d0fd, reuse both 09-18 arms); report path as proposed.

Build: exec/canon-ci-20260918/build-canon.sh on 3bda, worktree /var/tmp/jhan/tron-ci-canon (branch jhan-ci-canon),
head 0594dc5402 = 3faba6d0fd + cherry-pick 6f37cd2ed9 (2 lines in CMakePresets.json). Output
/var/tmp/jhan/canon-ci-20260918/{target.deb,manifest.json,rinzler.target,build.status}. Built 22:11:49-22:25:50 UTC: deb tron_2026.09.18-0594dc54-jhan-ci-canon (86 AMX tile insns, kill-switch literal 1, TRON_K_VNNI literal 0 [vacuous check: that string is compile-time only; VNNI-K absence rests on the git checks]).

Campaign: exec/canon-ci-20260918/{campaign.sh,dut.sh,launch.sh} forked from ci-mimic; st_ci_perf.py + talos_stub copied
unchanged. Flow: lease-free -> flock (held whole run) -> bill-share take -> preflight -> ensure-canon -> 12 configs ->
ensure-base (nightly 2026.09.18-3faba6d0) -> serving-down (5-min idle test, POST /api/inference/down, rm positron slice
files, >= 256 free hugepages) -> marker release -> flock release. HANDOFF=down is the peer's start condition.
Results exec/results/canon-ci-20260918/canon/perf.json; .status; log exec/logs/canon-ci-20260918.log.
LAUNCHED 22:43:44 UTC (launch.sh: md5 sync + build ok + bill-share take, then campaign.sh detached); canon deb installed 22:44:10.
Review workflow wf_4103248e-350 (38 findings, 23 stood): fixed before launch = TERM/INT/HUP trap runs restore+release (driver
in background + wait), hold_lock polls while ssh alive + kills orphan holders, release_lock verifies flock free (3 tries),
deadline checks inside both wait loops, marker take moved to launch.sh (bill-share rule), release rc checked, restore/handoff
failures in the final status + .done-with-failures, HANDOFF=up skips up when down failed, ServerAlive + timeouts on DUT steps,
save-base-deb local copy for the restore (repo index may drop 09-18 after the 09-19 publish-deb), SYSTEM_STATS busy signal in the
idle test, DEADLINE_START 23:30Z, driver timeout capped by DRIVER_END_BY 02:05Z. NOT changed: st_ci_perf.py (deleted-binary
check is log-only; report must assert exe sha == canon rinzler sha b273a2e1... per after-provision snapshot).
Hard limits: DEADLINE_START 23:59 UTC, DRIVER_TIMEOUT 8400 s; must be over before 02:45 UTC (ci-runner-stop timer
POSTs /api/inference/up) and 03:39 UTC (nightly apt reinstall).

Expectation (config notes of gen_report.py): only llama-8b, mixtral (CPU attention, kernel-eligible) and qwen-3-4b
(FPGA attention, AMX in the CPU share) can move; the other 8 configs are controls. Comparisons: canon vs base = the
canonical-AMX effect; canon vs target = the PR 4424 delta (same main, same preset line, only the PR diff).

Caveat accepted by jhan: the 09-18 base arm ran under a saturated client host (PSI 93-99 % on configs 1-5); TPS means
robust, TTFT unattributable for llama-3b, llama-8b, qwen-3-4b tp2. Client container idle tonight (load 4 / 32 CPUs).

Report generator (workflow wf_6f800a14-712, 1124+ lines, verified 0 numeric mismatches on stand-ins): exec/canon-ci-20260918/gen_report.py
--base --target --canon --nightly --stats --preflight (canon preflight = manifest) [--target-preflight --caveats --notes --short3
--thr-note --title --nightly-run-id] --out; handles a mid-campaign record (raw-only rows), missing canon, missing manifest;
canon color aqua #1baf7a (dataviz slot 3); evidence row "running binary sha vs on-disk rinzler sha per after-provision snapshot"
added by hand (base 0/42, target 0/42 pids differ). Render command used live:
python3 gen_report.py --base exec/results/ci-mimic-20260918/base-pass1/perf.json --target .../target-pass1/perf.json
--canon exec/results/canon-ci-20260918/canon/perf.json --nightly .../reference/nightly-0918.arm.json --stats .../reference/nightly_stats.json
--preflight exec/results/canon-ci-20260918/preflight.txt --nightly-run-id 35303980268 --out <html>.
**How to apply:** final report = PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html (+ caveats fragment written after the run from
the canon record's client PSI/load and the handoff log).
Never touch 3bda after the handoff line until the peer session says it is done. Related: [[ci-mimic-20260918-campaign]],
[[ci-enable-20260917-campaign]], [[issue-4500-root-cause-campaign]], [[3bda-shared-with-bill]].

RESULT (canon arm 22:44-00:15 UTC, 12/12, perf 90.6 min, client PSI <= 1.8 %, AMX probes llama-8b 30.2 G / qwen tp2 10.5 G cycles):
| config | base | canon | target | canon/base (t) | target/canon (t) |
| llama-3b @32u | 194.54 | 197.36 | 187.26 | +1.5 % (0.9) | -5.1 % (-19, target client-affected) |
| llama-8b @8u | 139.40 | 141.03 | 140.53 | +1.2 % (+2.8) RESOLVED | -0.4 % |
| 70b tp2 @8u/@4u | 16.57/27.98 | 16.59/27.97 | 16.60/28.30 | 0 | +0.1 / +1.2 % (+18) |
| 70b tp4 @4u | 29.92 | 30.47 | 30.41 | +1.8 % (1.8) | -0.2 % |
| mixtral | 79.21 | 78.75 | 79.01 | -0.6 % (-2.2) | +0.3 % |
| qwen-2.5 | 35.21 | 35.24 | 35.19 | +0.1 % | -0.1 % |
| qwen-3-4b tp2 | 186.13 | 186.25 | 176.75 | +0.1 % (0.1) | -5.1 % (-7.4) RESOLVED |
| qwen-3-4b tp4 | 149.94 | 146.05 | 133.44 | -2.6 % (-3.7, inside 7 % band) | -8.6 % (-7.3) RESOLVED; canon passes goal 135 |
| gemma-2 | 101.93 | 101.70 | 102.11 | -0.2 % | +0.4 % |
| gpt-oss tp4 | 106.51 | 102.33 | 106.16 | -3.9 % (-2.6, inside 5.7 % band; nightly 101.16) | +3.7 % |
| gemma-4 | 38.06 | 37.96 | 37.94 | -0.3 % | 0 |
VERDICT: canonical AMX alone costs nothing resolved on any CI config and gains +1.2 % on llama-8b; the issue-#4500 qwen loss is
PR 4424's layout (target vs canon -5.1/-8.6 %), not the kernel. Handoff worked: peer campaign took the flock 00:22:16 UTC.
Report v1 PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html (+ caveats.html, notes.html, render.sh in exec/results/canon-ci-20260918/);
verification workflow launched 00:3x UTC. TRAPS: Monitor tail -F on the NFS results dir delivered nothing after the first batch
(use a 60-s grep poll); ${Version} inside a single-quoted ssh command expands remotely (empty).

FINAL 2026-09-19 01:0x UTC: report v2 = PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html (129 KB, ASCII, 5 SVG charts checked with
cairosvg) = artifact https://claude.ai/artifact/JDNqh1dxA5DeATovyCFkCP (private; republish with the same file path from this session, or
url= from another). Copy exec/results/canon-ci-20260918/report-v2.html. Verification workflow wf_290b2b3c-d43 (4 lenses, 69 findings)
applied by a fix agent: notes.html now templated ({{canon_minutes}}, {{ttft_vs_nightly}}), caveats generated from all records + bill-share.log,
section 9 "Not measured", per-config anomalous-tps counts (client-stall indicator: nightly 3 / base 154 / target 53 / canon 4),
deleted-binary snapshot explained (canon "before" = the 4 idle gemma-4 engines on the nightly rinzler), target manifest, DUT load row.
Short version (final): canon loses nothing resolved on 12 configs, +1.2 % llama-8b (probe 30.2 G cycles); the #4500 qwen loss appears only
when PR 4424 is added (target vs canon -5.1/-8.6 %); repeat run needed for gpt-oss -3.9 %, qwen tp4 -2.6 % (unresolved) and llama-3b
target-vs-canon -5.1 % (candidate PR 4424 regression, target ran at client PSI 99 % but only 3 anomalous samples).
NOT done: notebook preservation (github notebook), PR/issue comments, repeat run, mixtral probe. Bill's half taken 22:43:44 by launch.sh
(Bill idle, take refuses otherwise), marker re-created 00:22:02; jhan was told in the final summary.
