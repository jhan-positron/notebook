# Reader report: the whole-machine nightly-config campaign (exec/pr4424ci-20261009) and what a PR-4 repeat needs

Short version. The 2026-10-09 campaign held the whole of delphi-3bda for 8 h 26 min (13:36:30 to 22:02:45 UTC) and ran 8 driver runs (4 full passes of 106 to 110 min, 4 sw8k cells of 7 to 8 min) with no failure. Its base arm was the nightly deb 2026.10.08-be0d5565 saved as nightly.deb. A PR-4 repeat with a base deb built from main 72308ec90c needs a two-arm fork of build-target.sh (a conditional grep and a conditional preset edit), the knobs EXPECTED_BASE and EXPECTED_BASE_SHA set to the built deb, the built deb placed at $OUT/nightly.deb, a hand-off marker that the PR-4 chain creates BEFORE its lease wait, and new NAME, OUT, result and log names.

## Words used here

- delphi-3bda (also "the DUT", device under test): the Intel Xeon 6 test server shared with the nightly CI and with Bill (a colleague) [exec/pr4424ci-20261009/README.md:9].
- claude-box: the client host where campaign.sh runs and drives delphi-3bda over ssh [README.md:10].
- nightly / System CI: the nightly test job (`uv run system_ci` of the systems_test repository) that installs the newest tron deb on delphi-3bda and runs its phases; the perf phase is what the campaign repeats [README.md:11-13].
- systems_test harness: the checkout ~/workspace/ai-runs/systems_test; scripts/perf.py holds the 14 perf configs [README.md:14-15].
- tron: the inference program; rinzler: its production server binary; deb: tron's Debian package; platformd 0.11: the service that starts the rinzler engines [README.md:16-17].
- base arm / target arm: the two packages compared; "arm" and "binary" mean the same package [README.md:20-21].
- restore target: the deb installed when the campaign starts; saved as restore.deb and reinstalled at the end [README.md:22-23].
- USE_HW_ATTN: a rinzler environment variable; unset = attention on the FPGA cards; USE_HW_ATTN=0 = software attention on the CPU; set through /opt/positron/user/config.env (14 bytes = `USE_HW_ATTN=0`, 0 bytes = unset) [README.md:24-26].
- full pass: the harness's 14 perf configs with config.env empty, tag `<arm>-pass<k>`; sw8k cell: the one extra config with USE_HW_ATTN=0, tag `<arm>-sw8k-pass<k>` [README.md:27-29].
- driver: st_ci_perf.py, the python program that runs the harness's test_performance from claude-box [README.md:150].
- CI lease: the file /run/lock/systems-test-ci.lease on delphi-3bda; "busy" while the nightly holds the machine [README.md:35].
- Bill's marker: the file /bill-has-instance-0,2 on delphi-3bda; present = Bill may use the first half (socket 0) [README.md:36-37].
- campaign flock: /var/tmp/jhan/3bda-campaign.lock, held for the whole run [README.md:38].
- pre-check marker: /var/tmp/jhan/pr4424ci-precheck.running on delphi-3bda, held by the correctness pre-check chain of the same window [README.md:39-41].
- TPS: generated tokens per second per user; TTFT: time to first token in ms; round: one request per user, 10 rounds per config [README.md:32-33].
- paired t: the t statistic of the per-round differences target minus base, pooled over the pass pairs [README.md:34].
- VmRSS, VmHWM, HugetlbPages: lines of /proc/PID/status (resident memory now, its peak since the process started, 1 GiB hugepage mappings) [README.md:35-36 of the Words list].
- PR-3 chain: exec/pr3-20261012/chain2.sh, the delphi-3bda build-and-test script of PR-3, whose whole-machine part (D smokes, E cells, C host suite) is the pattern for PR-4's chain [split-status.md, "PR-3 Step 6"].
- est.: an estimate, not a measurement.

## 1. The 2026-10-09 run: sequence, UTC times, durations

Every time below is UTC. Sources: exec/results/pr4424ci-20261009/status-history.log (the status lines), exec/logs/pr4424ci-20261009.log (the full log, 268 lines), preflight.txt, base-identity.txt, outcome.txt.

| Time | Event | Source |
|---|---|---|
| 2026-10-09 00:15:16 | campaign start on claude-box. Knobs: PASSES="base target target base", PASS_TAGS none, NOT_BEFORE 2026-10-09T13:00:00Z, DEADLINE_START 2026-10-09T19:00:00Z, PASS_DEADLINE 2026-10-10T00:30:00Z, DRIVER_END_BY 2026-10-10T02:05:00Z, HANDOFF up, EXPECTED_BASE 2026.10.08-be0d5565, DRIVER_TIMEOUT 9000, SW8K_TIMEOUT 1800, FULL_CONFIGS harness-list, AMX_PROBE 1, HF_OFFLINE 1 | [status-history.log:1] |
| 00:15:16 to 12:45:16 | NOT_BEFORE sleep, one status line per 30 min (26 lines) | [status-history.log:2-27] |
| 13:00:00 | "NOT_BEFORE passed; waiting for the CI lease next" | [status-history.log:28] |
| 13:00:01 to 13:34:07 | "waiting: CI lease busy (or the DUT did not answer)", 18 polls at 2 min | [status-history.log:29-46] |
| 13:36:08 | "CI lease free" (busy at 13:34:07, free at 13:36:08 as `dut.sh lease-free` with 600 s grace judges it) | [status-history.log:47] |
| 13:36:08 | "pre-check marker absent" | [status-history.log:48] |
| 13:36:08 | "no runtron process on the DUT" | [status-history.log:49] |
| 13:36:08 to 13:36:30 | the campaign flock taken (remote holder pid 3940467) and Bill's marker taken; the take line: "delphi-3bda take: removed /bill-has-instance-0,2; the whole machine is ours" | [.lock.out:1; pr4424ci-20261009.log:50-51] |
| 13:36:30 | preflight (read-only) | [preflight.txt:1] |
| 13:36:36 | installed at preflight = 2026.10.09-26b6df7d (the restore target); base arm = 2026.10.08-be0d5565; restore target differs, so saved as restore.deb | [pr4424ci-20261009.log:52-53] |
| 13:36:36 | nightly.deb already saved (2026.10.08-be0d5565) | [pr4424ci-20261009.log:54] |
| 13:36:38 | restore.deb saved: 145,219,516 bytes | [pr4424ci-20261009.log:55] |
| 13:36:39 | pass tags: base-pass1 base-sw8k-pass1 target-pass1 target-sw8k-pass1 target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2 | [status-history.log:51] |
| 13:36:40 to 13:36:50 | ensure-base: 2026.10.08-be0d5565 reinstalled from nightly.deb and verified (10 s) | [pr4424ci-20261009.log:57-59] |
| 13:37:10 | hwattn-clear (config.env 0 bytes) | [pr4424ci-20261009.log:60] |
| 13:37:11 to 13:40:13 | idle check of serving-down (IDLE_MIN=1), 4 polls of 60 s | [pr4424ci-20261009.log:61-64] |
| 13:40:20 to 13:40:25 | serving down through platformd, 8 slice files removed, 512 hugepages free | [pr4424ci-20261009.log:65-74] |
| 13:40:27 to 13:42:43 | serving up; units_active=2, "idle 2"; verify-env mode unset: 2 pids, 0 wrong | [pr4424ci-20261009.log:75-79] |
| 13:42:46 to 15:32:48 | base-pass1: driver rc=0 in 110 min, 14 configs completed, 54 anomalous-sample lines | [status-history.log:52-53] |
| 15:32:49 to 15:36:26 | hwattn-off (14 bytes), idle check, serving down, serving up, verify-env mode set ok | [pr4424ci-20261009.log:82-100] |
| 15:36:28 to 15:44:42 | base-sw8k-pass1: rc=0 in 8 min, 1 config | [status-history.log:54-55] |
| 15:44:44 to 15:44:54 | ensure-target: 2026.10.09-667b2ce5-jhan-pr4424ci-target installed and verified (10 s) | [pr4424ci-20261009.log:103-104] |
| 15:45:14 to 15:47:15 | hwattn-clear, idle check, serving down, serving up; units_active=4, "idle 4"; verify-env mode unset ok | [pr4424ci-20261009.log:105-124] |
| 15:47:17 to 17:33:55 | target-pass1: rc=0 in 106 min, 14 configs, 2 anomalous-sample lines | [status-history.log:56-57] |
| 17:37:34 to 17:45:28 | target-sw8k-pass1: rc=0 in 7 min | [status-history.log:58-59] |
| 17:48:39 to 19:37:57 | target-pass2: rc=0 in 109 min, 13 anomalous-sample lines | [status-history.log:60-61] |
| 19:41:36 to 19:49:52 | target-sw8k-pass2: rc=0 in 8 min | [status-history.log:62-63] |
| 19:52:28 to 21:41:54 | base-pass2 (after ensure-base and a restart): rc=0 in 109 min, 11 anomalous-sample lines | [status-history.log:64-65] |
| 21:45:33 to 21:53:44 | base-sw8k-pass2: rc=0 in 8 min | [status-history.log:66-67] |
| 21:53:45 | restore: hwattn-clear ok (config.env 0 bytes) | [pr4424ci-20261009.log:238-239] |
| 21:53:46 to 21:53:57 | restore.deb (2026.10.09-26b6df7d) reinstalled and verified: "restore ok" | [status-history.log:68] |
| 21:54:17 to 22:01:46 | idle check (IDLE_MIN=5), 8 polls | [pr4424ci-20261009.log:244-251] |
| 22:01:53 to 22:02:45 | serving down, serving up; units_active=4 "idle 4"; config.env 0 bytes | [pr4424ci-20261009.log:252-264] |
| 22:02:45 | Bill's marker released ("created /bill-has-instance-0,2") | [pr4424ci-20261009.log:265] |
| 22:02:47 | flock released; summary written; "campaign done" | [status-history.log:69; pr4424ci-20261009.log:266-268] |

Outcome: "incomplete passes: none; stop reason: none; problems: none; known systematic failures: none" [outcome.txt:1]; the end marker is .done [results folder listing].

Durations computed from the times above:

- NOT_BEFORE sleep: 12 h 44 min 44 s (00:15:16 to 13:00:00).
- lease wait: 36 min 8 s (13:00:00 to 13:36:08).
- marker test, peer test, flock and Bill's marker take: 22 s (13:36:08 to 13:36:30).
- preflight, deb saves, first package step and first engine restart: 6 min 16 s (13:36:30 to 13:42:46).
- the 8 driver runs: 110 + 8 + 106 + 7 + 109 + 8 + 109 + 8 = 465 min = 7 h 45 min (the per-run minutes of status-history.log lines 53, 55, 57, 59, 61, 63, 65, 67).
- the 7 gaps between driver runs (state change, engine restart, verify-env): 3 min 40 s, 2 min 35 s, 3 min 39 s, 3 min 11 s, 3 min 39 s, 2 min 36 s, 3 min 39 s.
- restore (hwattn-clear, reinstall, 5-min idle check, restart, release): 9 min 3 s (21:53:44 to 22:02:47).
- whole machine held (take to release): 8 h 26 min 15 s (13:36:30 to 22:02:45).
- the campaign process: 21 h 47 min 31 s (00:15:16 to 22:02:47).
- serving was cycled (down then up) 9 times: before every driver run that needed a state change (8) and once at the restore [pr4424ci-20261009.log, the "taking production serving down" lines].

Per-config benchmark time inside base-pass1 (the "Perf test for <model> completed in N mins" lines; these exclude provisioning): llama-3.2-3b 3.84, llama-8b 8u 2.63, llama-8b 32u 13.14, 70b tp2 8u 17.61, 70b tp2 4u 10.24, 70b tp4 9.50, mixtral 4.49, qwen-2.5-32b 8.89, qwen-3-4b tp2 2.66, qwen-3-4b tp4 2.85, gemma-2-9b 4.03, gpt-oss-120b 3.71, gemma-4-31b 9.06, Muse-Glimmer-30B 5.37 min; sum 97.98 min of 110 min; the rest is provisioning [exec/results/pr4424ci-20261009/base-pass1/summary.txt].

The target deb build on delphi-3bda before the run: start 2026-10-08T23:58:09Z, "make deb done in 918 s", package checks at 00:14:45Z, DONE at 00:14:47Z; total 16 min 38 s on socket 1 [exec/logs/pr4424ci-20261009-build-target.log:1,38,42,69]. The README's "about 30-40 min" is an estimate that the measurement undercuts [README.md:55].

The pre-check of the same window (exec/merge4737-20261008/precheck.sh) did NOT run before the campaign as planned. Its marker was created at 13:36:11, 3 s after the campaign tested the marker at 13:36:08 [exec/logs/merge4737-precheck-chain.log:31; status-history.log:48]. Its serving-down then saw the campaign's traffic (remote connections up to 256) and gave up at 13:48:21 [merge4737-precheck-chain.log:33-46]. Its host suite ran at 22:10:28, after the campaign, with serving up (heap_setup failures), and its smokes at 22:17 to 22:22 [merge4737-precheck-chain.log:65-68]. The campaign and the pre-check had waited for the same lease event. This is the origin of the rule "a campaign and a pre-check must not wait for the same lease event (create the hand-off marker before waiting)" [PR3-handoff.md, section 8, "Machine"].

## 2. Every environment knob of campaign.sh and launch.sh; exit codes and abort conditions

campaign.sh knobs (file exec/pr4424ci-20261009/campaign.sh; every knob is read as `${NAME:-default}`):

| Knob | Default | Meaning | Line |
|---|---|---|---|
| EXPECTED_BASE | 2026.10.08-be0d5565 | the base arm's deb version; installed from the saved nightly.deb | 70 |
| EXPECTED_BASE_SHA | aebe98551e873219b7ff8dcf25f2cf9a35ebee01e660d6b71b042f48819cd123 | sha256 of the base arm's /opt/positron/bin/rinzler | 71 |
| NOT_BEFORE | 2026-10-09T13:00:00Z | sleep until this time before the lease wait (empty = no sleep) | 72, 339-346 |
| DEADLINE_START | 2026-10-09T19:00:00Z | every wait (lease, marker, peers, flock, Bill) and the first pass must be done by this time, else abort | 73 |
| PASS_DEADLINE | 2026-10-09T23:30:00Z | no further FULL pass starts after this (sw8k cells may still start) | 74, 457 |
| DRIVER_END_BY | 2026-10-10T02:05:00Z | hard end: a driver run's timeout is cut to the time left; a run with less than 600 s left is not started | 75, 279-280 |
| NO_WAIT | 0 | 1 = skip the lease waits (tests only) | 76, 348, 400, 430 |
| AMX_PROBE | 1 | 20 s EXE.AMX_BUSY sample before the llama-8b and qwen-3-4b tp2 benchmarks (CI_MIMIC_AMX_PROBE) | 76, 290 |
| HANDOFF | up | up = production engines brought up at the end; anything else = left down | 76, 233-243 |
| HF_OFFLINE | 1 | HF_HUB_OFFLINE for the driver (tokenizers from the local cache only) | 76, 288 |
| DRIVER_TIMEOUT | 9000 (s) | timeout per full pass | 77 |
| SW8K_TIMEOUT | 1800 (s) | timeout per sw8k cell | 77 |
| PASSES | "base target target base" | arm order; arm k gives the tags `<arm>-pass<k>` then `<arm>-sw8k-pass<k>` | 78, 441-444 |
| PASS_TAGS | (empty) | resume: run only these tags, in this order | 79, 439 |
| RESUME_OVERWRITE | 0 | 1 = redo a tag whose perf.json exists | 80, 455 |
| IDLE_MIN_SWITCH | 1 (min) | idle minutes the serving-down check needs between passes (5 at the restore) | 81, 154-156, 235 |
| FULL_CONFIGS | (empty) | "" = the harness's own scripts.perf.configs; a json path replaces it | 82, 334 |
| LEASE_CHECK | 1 | CI_MIMIC_LEASE_CHECK for the driver (lease test before every provisioning and cell); undocumented in the header | 292 |
| CAMPAIGN_LIB_ONLY | 0 | 1 = source the functions only (unit tests) | 323 |

launch.sh reads NOT_BEFORE, DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY (date parse and order), EXPECTED_BASE (for the nightly.deb check) and echoes PASSES, PASS_TAGS, DRIVER_TIMEOUT, SW8K_TIMEOUT; every knob reaches campaign.sh through the environment [launch.sh:7-9, 32, 36-45].

Driver environment set by run_pass (campaign.sh:285-293): PYTHONPATH="$H/talos_stub:$ST", OPENAI_HOST=http://delphi-3bda.positron.internal/v1, OPENAI_TOKEN=token-secret, PLATFORMD_PORT=8080, PLATFORM_TYPE=granite_rapids_72_rinzler, SYSTEM_CI_SPECULATION=0, SSH_USER=jhan, SSH_PASS=, HF_HUB_DISABLE_TELEMETRY=1, HF_HUB_OFFLINE=$HF_OFFLINE, TOKENIZERS_PARALLELISM=false, CI_MIMIC_ARM=$tag, CI_MIMIC_OUT=$dir/perf.json, TALOS_STUB_OUT=$dir/talos.json, CI_MIMIC_MODELS="", CI_MIMIC_CONFIGS_JSON="$cfg" ("" for a full pass, sw8k.json for the cell), CI_MIMIC_INSTALLED_SHA=$sha (read from `dut.sh installed` at run time), CI_MIMIC_AMX_PROBE=$AMX_PROBE, CI_MIMIC_REQUIRE_HWATTN0=1 for cpu attention, CI_MIMIC_REQUIRE_HWATTN_UNSET=1 for fpga attention, CI_MIMIC_LEASE_CHECK=${LEASE_CHECK:-1}, CI_MIMIC_DUT_HELPER=$H/dut.sh. The driver's own knob list is in its docstring [st_ci_perf.py:59-66]; CI_MIMIC_CHECK=1 selects the read-only check mode [st_ci_perf.py:463].

Exit codes and abort conditions of campaign.sh (abort_early = status "ABORT", no restore target, Bill's marker released, flock released, outcome.txt "aborted: ...", .done-aborted [campaign.sh:272]):

- rc 2: a date knob does not parse [328]; deadline order wrong (need DEADLINE_START < PASS_DEADLINE < DRIVER_END_BY) [330]; NOT_BEFORE not before DEADLINE_START [331]; DRIVER_END_BY already past [332]; FULL_CONFIGS not a readable file [334]; sw8k.json missing [335]; PASSES carries an unknown arm [442].
- rc 3: the start is more than 8 h before DEADLINE_START with NOT_BEFORE empty [333]; past DEADLINE_START while waiting for the lease [350], the pre-check marker [363], the DUT's answer [365, 378, 404], a peer campaign [376], the flock [385], or before starting [388]; the lease became busy while waiting for Bill's marker [400]; the lease busy or unanswered right before the first package switch [431].
- rc 4: the installed version does not match `2026.*` [414]; the installed version contains "jhan" [415]; the installed rinzler sha is not 64 hex characters [416]; the preflight line "installed rinzler IS the target build's (must be no at preflight): no" is missing [417].
- rc 5: target build status not ok [419]; config.env not 0 bytes [420]; the base deb not saved as nightly.deb and not downloadable [426]; the restore deb not saved [427].
- rc 6: Bill's marker still present at DEADLINE_START (Bill active) [399]; bill-share take returned a code other than 0 or 2 [402]; Bill's marker present at preflight [421].
- rc 130: a TERM, INT or HUP signal: the driver is stopped, the restore path runs, .done-aborted [257-268].
- rc 0: the normal end, with .done (no failure, no problem, no stop reason) or .done-with-failures [507-508]; the script has no final `exit`, so both end with rc 0. stop_safely (exit code as given) is defined at line 306 but never called (grep over the file finds the definition only).
- Per-tag stop reasons that end the pass loop without an abort (the restore then runs and the end is .done-with-failures): bad tag [450]; past DEADLINE_START before the first pass [456]; past PASS_DEADLINE before a full pass [457]; lease busy or unanswered 3 times before a tag [461-462]; not enough time before DRIVER_END_BY (a full pass needs max(6600 s, last measured pass + 600 s); an sw8k cell max(1200 s, last measured + 600 s)) [464-466]; the package or restart step failed [468]; the driver killed by a signal [471, 491]; driver rc 9 (lease became busy) [472, 492]; no time for a repeat [477]; two consecutive driver runs with 0 configs [478, 498]; driver rc 8 in both runs [495].
- Driver return codes: 0 all configs have results; 2 some config has none; 7 an engine runs a stale binary; 8 an engine's USE_HW_ATTN state is wrong; 9 the lease became busy; 124 the timeout fired (no repeat; completed configs stay in perf.json) [st_ci_perf.py:64-65; campaign.sh:476]; 130, 137, 143 = killed [297]. On any other nonzero rc the engines are restarted and the run repeated once; the first attempt's directory is kept as `<tag>-failed1`; cells that failed in both runs become "known systematic failures" and are not repeated again [479-497].

launch.sh exits 1 on: a running campaign.sh [18]; an md5 mismatch between claude-box and delphi-3bda for dut.sh, st_ci_perf.py, talos_stub/talos.py, sw8k.json, campaign.sh, summarize.py, ../lib-guard.sh, ../bill-share.sh (the NFS attribute cache) [19-22]; a python compile error in st_ci_perf.py, summarize.py, configs.py [23]; a bash syntax error in campaign.sh, dut.sh, build-target.sh [24]; st_ci_perf.py newer than the last check-mode run (RESD/check-mode/perf.json) [25-26]; local changes under scripts/ or testlib/ of the harness [28]; platformd not 0.11.x [29]; target build status not ok [30]; target.deb, rinzler.target or manifest.json missing [31]; the saved nightly.deb version not equal to EXPECTED_BASE [32]; a runtron or rinzler process of jhan on the DUT [33-34]; a date knob that does not parse, a wrong deadline order, NOT_BEFORE not before DEADLINE_START, DRIVER_END_BY past [36-43]. A harness checkout not at origin/main prints a NOTE only [27]. On success it prints "launched pid <pid> log <path> (knobs: ...)" [44-45].

## 3. The base deb today, and what changes for a base built from 72308ec90c

How the base deb is chosen, saved and verified today:

- The base arm is EXPECTED_BASE / EXPECTED_BASE_SHA [campaign.sh:70-71, 418]; the file is $OUT/nightly.deb on delphi-3bda, OUT=/var/tmp/jhan/pr4424ci-20261009 [dut.sh:37]. It was saved on 2026-10-08 23:09 (145,229,784 bytes, version 2026.10.08-be0d5565) [preflight.txt:5].
- `dut.sh save-base-deb VERSION [FILE]`: FILE must be nightly.deb or restore.deb [dut.sh:101-102]; when the file exists with that Version field, "already saved", exit 0 [103]; otherwise `apt-get download tron=VERSION`, then the apt cache /var/cache/apt/archives, into a temporary file; the Version field is checked before the file replaces the kept copy [104-111]. The campaign calls it for the base (nightly.deb) and for the restore target (restore.deb) after the preflight [campaign.sh:426-427].
- `dut.sh ensure-base VERSION SHA [FILE]` (FILE default nightly.deb): "already installed" when the installed version and the rinzler sha both match [113-116]; otherwise `apt-get remove -y tron`, then install the saved local copy when its Version field matches [119-122], else `apt-get update` and `apt-get install -y --allow-downgrades tron=VERSION` from the repository [124-127]; then version and sha verified [128-130]. campaign.sh calls `ensure-base "$BASE_VERSION" "$BASE_SHA"` for the base arm (FILE defaults to nightly.deb) [183] and `ensure-base "$RESTORE_VERSION" "$RESTORE_SHA" "$RESTORE_FILE"` at the restore [232].
- The restore target: whatever `dut.sh installed` prints at preflight [412]; RESTORE_FILE is nightly.deb when the installed version equals the base, else restore.deb [423-424]; base-identity.txt holds two lines, "base VERSION SHA nightly.deb" and "restore VERSION SHA FILE" [425; base-identity.txt:1-2].
- The preflight rules that concern versions apply to the INSTALLED package, not to the base deb: `2026.*` [414], no "jhan" [415], a 64-hex sha [416], and the preflight line that the installed rinzler is not the target build's (compared with $OUT/rinzler.target) [417; dut.sh:63-64]. launch.sh checks only that nightly.deb's Version field equals EXPECTED_BASE [launch.sh:32]. The README's resume note restates the installed-package rule: after a crash with our deb installed, "the preflight then requires the nightly's deb to be installed again (it refuses a version that contains 'jhan' and a rinzler that is the target build's)" [README.md:141-142].

How a deb's version string is derived (~/workspace/tron, identical scripts at 72308ec90c, at the probe head and in the working tree: md5 8e1eb30d2130fec4d7c2c308228aa88b for bin/get-version.sh and 93c0d8ba7554347a56c72ea9a774ae16 for bin/get-deb-version.sh):

- `make deb` builds gen-deb/$(DEB_NAME) with DEB_NAME := tron_$(shell bin/get-deb-version.sh)_amd64.deb [GNUmakefile:306, 508-514]; cmake also runs bin/get-deb-version.sh at configure time for CPACK_DEBIAN_PACKAGE_VERSION [cmake/SetVersion.cmake:1-9].
- bin/get-deb-version.sh calls bin/get-version.sh [get-deb-version.sh:9-15], maps -devN/-tcN/-rcN pre-release tags to Debian's "~" form [25-34], and replaces every character outside [A-Za-z0-9.+:~-] by "." [40-43].
- bin/get-version.sh: branch = `git branch --show-current` (empty on a detached HEAD) [13]; verstr = `date +%Y.%m.%d` of the BUILD day, a dash, and `git rev-parse --short=8 HEAD` [14]; the feature-branch path needs TRON_FEATURE_BRANCH_BUILD set, which the campaign's build does not set [17-28]; when HEAD carries a tag exactly, the version is that tag without a leading "v" [31-35]; a branch other than main or release-* appends "-<branch>" [42-44]; "-dirty" is appended when `git describe --dirty` says so [47-49].
- So: a detached worktree gives a nightly-looking version such as 2026.10.09-9d5c7a38; a local branch gives 2026.10.09-667b2ce5-jhan-pr4424ci-target (the 2026-10-09 target: the 8-character sha is the local preset commit 667b2ce5, not the PR commit 9d5c7a389b) [exec/logs/pr4424ci-20261009-build-target.log:4,38; manifest in preflight.txt:9-13]. build-target.sh creates the worktree detached and then `git checkout -q -B jhan-pr4424ci-target` so the version carries the branch name [build-target.sh:14-17, 38-45].
- Tags: 72308ec90c and the PR-3 head 80bce9a08d carry no tag; 0a5334ccb6 carries the local tag pr4424-pre-split-0a5334ccb6 (`git tag --points-at`, run read-only). A deb built exactly at 0a5334ccb6 in a worktree of ~/workspace/tron would be versioned "pr4424-pre-split-0a5334ccb6". PR-4's head is a new commit, so this does not apply to it.

What must change for a base arm built from 72308ec90c:

- Knobs: EXPECTED_BASE = the Version field of the built base deb (`dpkg-deb -f base.deb Version`); EXPECTED_BASE_SHA = the sha256 of its rinzler (`dpkg-deb --fsys-tarfile base.deb | tar -xO ./opt/positron/bin/rinzler | sha256sum`, the extraction build-target.sh uses at line 97). Set both for launch.sh (line 32 reads EXPECTED_BASE) and campaign.sh (lines 70-71), or edit the defaults in the fork.
- File placement: the built base deb must sit at $OUT/nightly.deb, because ensure_state base calls ensure-base with the default FILE nightly.deb [campaign.sh:183; dut.sh:114], save-base-deb accepts only nightly.deb or restore.deb [dut.sh:102], and ensure-base's fallback `apt-get install tron=VERSION` cannot find a locally built version in the repository [dut.sh:126]. With the file in place and EXPECTED_BASE equal to its Version field, save-base-deb prints "deb ... already saved as nightly.deb" and exits 0 [dut.sh:103], and the campaign never downloads. A rename to base.deb is possible but touches dut.sh:59 (preflight line), 102 (the FILE list), 114 (the default), campaign.sh:216 (RESTORE_FILE default), 423-426 and launch.sh:32.
- dut.sh subcommands used for the base: ensure-base (install, verify), save-base-deb (the "already saved" path), installed, preflight (prints the saved nightly deb's version at line 59). ensure-target stays for the target. No new subcommand is needed.
- Preflight acceptance: yes, when the knobs match. campaign.sh's version rules read the installed package only [414-417], and the installed package at preflight is the nightly's (the restore target). The built base is accepted as the base arm whatever its version string. Two consequences: (a) if the campaign dies with the built base installed, a resume is refused by the "jhan" rule until the nightly's deb is reinstalled by hand, exactly as for the target today [README.md:141-142]; (b) the "jhan" rule only works when the base deb's version contains "jhan", so the base must be built on a local branch too (for example jhan-pr4ci-base); a detached build would look like a nightly, and a crash plus resume could then adopt our base as the restore target, since the sha comparison of line 417 knows rinzler.target only.
- The restore target: with a built base the installed package at preflight always differs from the base, so RESTORE_FILE=restore.deb and the installed nightly is downloaded with `apt-get download` [campaign.sh:424, 427]; on 2026-10-09 that path worked (145,219,516 bytes in 2 s) [pr4424ci-20261009.log:55].

The exact edits a fork of build-target.sh needs (line numbers of exec/pr4424ci-20261009/build-target.sh):

- (a) base from 72308ec90c80318403c4575dd9ce4a3bc9af5033 (the merge base of PR-1 [PR3-handoff.md, Words, PR-1]):
  - Lines 23-26: a second worktree and branch (for example WT=/var/tmp/jhan/tron-pr4ci-base, BRANCH=jhan-pr4ci-base) and per-arm output names (base.deb, rinzler.base, manifest-base.json, build-base.status, make-deb-base.log), because target.deb, rinzler.target, manifest.json and build.status are single names [11-12, 93-111]. The repository is the NFS ~/workspace/tron; the commit must be visible there (`git cat-file -e`), and the script fetches origin when it is not [23, 32-36].
  - Line 48: the grep for "Row-major blocks under hardware attention" in h/tron/models/kv_cache.hpp must be conditional on the target arm. At 72308ec90c the file has 0 occurrences (`git show 72308ec90c:h/tron/models/kv_cache.hpp | grep -c`, read-only), so the unconditional grep would `die`. At PR-4's head the Note is at kv_cache.hpp:729 and referenced at 2615 [probe worktree, read-only grep].
  - Lines 50-73: the preset edit must be skipped for the base. main's deb preset at 72308ec90c has "TRON_AMX_DISPATCH": "ON" as its last cacheVariables line (CMakePresets.json:68) and no TRON_K_VNNI anywhere (`git show 72308ec90c:CMakePresets.json | grep`), so the edit would insert the option into the base and the base would no longer be main.
  - Lines 74-79: the preset check must assert `TRON_K_VNNI` absent (or not "ON") for the base and "ON" for the target.
  - Lines 80-83: the commit step then finds nothing to commit for either arm.
  - Line 87-90: the build recipe stays (`taskset -c 72-143,216-287 make TOKENIZER_PYTHON_VERSION=3.12.7 NPROC_BUILD=48 deb`, PATH with /tools/uv/0.9.5 and ~/.ghcup/bin, outside nix).
  - Lines 98-102: the package checks stay for both arms: main's deb preset compiles the AMX kernels since PR #4505 [build-target.sh:6-7], so the TRON_AMX_DISABLE literal >= 1 and the tile-instruction count >= 50 hold for the base; the vnni string count is reported only (4 for the 2026-10-09 target) [manifest in preflight.txt:16-20].
  - Lines 103-110: the manifest's "options" and "note" must say which arm the deb is.
- (b) target from PR-4's head: the probe worktree's CMakePresets.json already has "TRON_K_VNNI": "ON" at line 69 inside the deb preset (lines 57-71), staged by handoff-material/ref/B-preset.diff [B-preset.diff:1-13; probe `git diff --cached -- CMakePresets.json`]. The python block's first branch reads `if '"TRON_K_VNNI": "ON"' in text: print("TRON_K_VNNI already ON somewhere in CMakePresets.json; no edit"); sys.exit(0)` [build-target.sh:54-56], so the edit exits 0 with that message (the exact text is "already ON somewhere ... no edit", not "already ON"); the preset check at line 77 passes; `git diff --quiet -- CMakePresets.json` is true, so no commit is made [80-83]; HEAD_SHA equals COMMIT; the branch jhan-pr4424ci-target is still created by `checkout -B` [45], so the version reads 2026.10.<build day>-<8 chars of PR-4's head>-jhan-pr4424ci-target (or the fork's branch name). The grep at line 48 passes. Note that the substring test at line 54 matches the option anywhere in the file, not only in the deb preset.

Commands the executor runs for the builds today (ON delphi-3bda, not during the nightly's perf phase and not next to another build of ours) [README.md:53-61]:

```text
ssh delphi-3bda bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/build-target.sh <COMMIT>
```

The fork takes the same form twice (or once with an ARM argument): once with the base commit 72308ec90c80318403c4575dd9ce4a3bc9af5033 and once with PR-4's head.

## 4. Waits, locks, the marker rule, and the deadlines

- The CI lease: /run/lock/systems-test-ci.lease is a JSON file with `state` and `expires_at_epoch`; `ci_lease_busy GRACE` returns busy when state == busy and now < expires_at + GRACE; no file = not busy [exec/lib-guard.sh:25-46]. `dut.sh lease-free` uses a 600 s grace [dut.sh:51-53]. campaign.sh polls it every 2 min after NOT_BEFORE [349-352], re-tests it after the waits [430-432] and before every tag [458-463]; the driver tests it before every provisioning and every cell and stops with rc 9 when busy [st_ci_perf.py:65, 221-223; campaign.sh:292, 472].
- The pre-check marker: created by precheck.sh with `touch "$MARKER"` AFTER its own lease wait [exec/merge4737-20261008/precheck.sh:34, 59-60], removed by its EXIT trap [48]; campaign.sh tests `test -e` over ssh every 2 min until DEADLINE_START; an ssh failure (rc other than 0 or 1) means retry, never "absent" [358-368]. The 2026-10-09 race of section 1 shows why the creator must create the marker BEFORE its lease wait. exec/pr3-20261012/chain2.sh creates no such marker (grep over the file finds none); a PR-4 chain fork must add one, and the campaign fork's PRECHECK_MARKER must name the same file.
- Peers: campaign.sh waits while `pgrep -u jhan -f '[r]untron[. ]|[c]ampaign[.]sh'` finds a process on the DUT [372-382]; launch.sh refuses when `pgrep -u jhan -f '[r]inzler --model|[r]untron[. ]'` finds one [33-34]. A PR-3-style chain's D step (smoke.sh runs runtron.<suffix>) and E step (exec/sync4424-20261002/campaign.sh) match the campaign's pattern; its C step (the host suite), serving-down and serving-up do not; so the peer wait alone does not cover a whole chain, which is what the marker is for.
- The campaign flock: a remote `flock -n /var/tmp/jhan/3bda-campaign.lock -c 'echo held pid $$; exec sleep HOLDER_LIFE'` whose pid is recorded in RES/.lock.out [campaign.sh:117-136]; HOLDER_LIFE = DRIVER_END_BY + 7200 s - now, at least 3600 s [383]; the release kills the holder and verifies the lock is free, with a warning when it is not [138-151]. lib-guard.sh's campaign_guard_acquire takes the same file [lib-guard.sh:150-156], and the cell campaign of the chain's E step calls campaign_guard_acquire [exec/sync4424-20261002/campaign.sh:94], so the W campaign and a running E step exclude each other through the flock.
- Bill's marker: campaign.sh calls `bill-share.sh status`, then `take` when the marker is present; rc 0 = taken; rc 2 (Bill active) = re-test the lease and retry every 30 min until DEADLINE_START, then abort 6; any other rc = abort 6 [390-407]. The restore path calls `release` three times at most and reports MARKER-NOT-RELEASED on failure [250-253]. bill-share.sh: "take happens only on jhan's word, never from a campaign script"; "take refuses while Bill is active"; exit 2 = refused [exec/bill-share.sh:12-13, 21, 38-47]. The memory rule: "Whole-machine work only after jhan says so; Claude never removes the marker on its own" [~/.claude/projects/-home-jhan-workspace-intel-AMX/memory/3bda-shared-with-bill.md:89]. How the stack reads this for a campaign launched by an executor: "jhan's order to execute this handoff is the word those texts require, as it was for PR-1 and PR-2. Say so in the checkpoint before the launch (section 7) so that jhan can object" [PR3-handoff.md 5.3]; PR-3's checkpoint said "the chain takes Bill's marker itself after the our-half verdict (jhan's order to execute the handoff is the word bill-share.sh requires)" [split-status.md, "PR-3 Step 6: delphi-3bda chain LAUNCHED"]. The 2026-10-09 campaign's take at 13:36:30 was made by campaign.sh on jhan's launch order in the same sense [pr4424ci-20261009.log:50]. A refusal (rc 2) is reported, never retried past DEADLINE_START, and never resolved by the executor.
- Serving: every state change goes through `dut.sh serving-down` (an idle test over the rinzler journal and `ss` for IDLE_MIN minutes, up to 12 polls of 60 s, then POST /api/inference/down, slice files removed, >= 256 free hugepages required) and `dut.sh serving-up` (POST /api/inference/up, then wait for "idle <configured engines>") [dut.sh:219-271]; platformd 0.11 restarts units stopped with systemctl, so the API is the only way [dut.sh:35].

The deadlines, the 2026-10-09 values and the reasoning:

| Knob | 2026-10-09 value | Reasoning in the files |
|---|---|---|
| NOT_BEFORE | 2026-10-09T13:00:00Z | before the nightly takes the lease (about 03:38 UTC) no lease file exists, so a lease-free test alone would start at once and run into the CI window [campaign.sh:337-338]; the nightly's lease clears about 13:20 [README.md:66] |
| DEADLINE_START | 2026-10-09T19:00:00Z | the first pass must have started; every wait aborts past it [campaign.sh:73, 350-388] |
| PASS_DEADLINE | 2026-10-10T00:30:00Z (the launch overrode the default 23:30) | no further full pass starts after it [status-history.log:1; campaign.sh:74, 457] |
| DRIVER_END_BY | 2026-10-10T02:05:00Z | hard end; the restore takes up to 16 min; the ci-runner-stop timer at 02:45 UTC brings inference up [campaign.sh:75; check-CI.md timeline "02:45 ci-runner-stop timer"]; our rule: long campaigns end before about 02:30 UTC [check-CI.md, "Rules for our own work"] |
| DRIVER_TIMEOUT | 9000 s (150 min) | per full pass; measured 106 to 110 min on 2026-10-09 [README.md:70; status-history.log] |
| SW8K_TIMEOUT | 1800 s (30 min) | per sw8k cell; measured 7 to 8 min [README.md:71; status-history.log] |

The need rule before each tag: a full pass needs max(6600 s, the longest measured pass + 600 s) before DRIVER_END_BY; an sw8k cell max(1200 s, the longest measured cell + 600 s) [campaign.sh:464-466]. With the 2026-10-09 pass length of 110 min the last full pass had to start by about 00:05 UTC, which is stricter than PASS_DEADLINE 00:30.

For a run on a later date D (reasoning, not a measurement): NOT_BEFORE = D T13:00:00Z; DEADLINE_START = D T19:00:00Z; PASS_DEADLINE = D+1 T00:30:00Z (as used) or D+1 T23:30:00Z (the default); DRIVER_END_BY = D+1 T02:05:00Z. launch.sh requires NOT_BEFORE < DEADLINE_START < PASS_DEADLINE < DRIVER_END_BY and DRIVER_END_BY in the future [launch.sh:40-43]; campaign.sh aborts 3 when the launch is more than 8 h before DEADLINE_START with NOT_BEFORE empty [333]. Observed lease-clear times: 2026-10-09 between 13:34 and 13:36 UTC (this log); 2026-10-10 the PR-1 chain's first build started 13:19:41; 2026-10-11 about 13:18; 2026-10-12 the PR-3 chain took the marker at 13:24:25 [PR3-handoff.md 5.3; split-status.md, "PR-3 Step 6, run 2"]. The nightly's cron is 03:30 UTC and GitHub has started it as late as 06:07 UTC, which would push the end past 15:00 UTC (est.) [check-CI.md:53-61, 127-134]. Arithmetic for one window: a campaign that starts at 13:36 ends about 22:03 (8 h 27 min, the 2026-10-09 measurement); if the PR-4 chain's whole-machine part runs first and takes what PR-3's took (13:24:25 to 14:57:14, 93 min [split-status.md, "PR-3 Step 6, run 2"]), the campaign starts about 15:10 and ends about 23:40, and its last full pass (base-pass2) starts about 21:30, inside PASS_DEADLINE 00:30 and inside the need rule; a lease that clears 1 h late moves the end to about 00:40 and the last full pass start to about 22:30, still inside; a 2 h late lease would make the last full pass start about 23:30, 35 min before the need rule's 00:05 limit. The ci-runner-stop timer (02:45) and the nightly's cron (03:30) do not move with the date.

## 5. Memory snapshots, the summary tables, the resolution rule, the sw8k cell

- `dut.sh memsnap` prints one JSON line: per running rinzler pid (pgrep -x rinzler) the unit name from its cgroup and VmRSS, VmHWM, HugetlbPages, VmSize, VmPeak, RssAnon, RssFile, RssShmem in kB from /proc/PID/status (read with sudo -n cat; the units run as positron), the host's MemTotal, MemFree, MemAvailable, Committed_AS, HugePages_Total, HugePages_Free, Hugepagesize, Cached, Shmem from /proc/meminfo, the sums over the pids (sum_VmRSS_kB, sum_VmHWM_kB, sum_HugetlbPages_kB) and the list of unreadable pids; it never fails [dut.sh:167-217]. The driver calls it over ssh after every provisioning and after every benchmark and copies the result into the per-config raw record as mem_after_provision and mem_after_benchmark [st_ci_perf.py:50-55; verified in base-pass1/perf.json, raw[0] keys]. VmHWM is a per-process peak; platformd starts a new process per provisioning, so the peak belongs to the current model, except for two consecutive configs of the same model (70b tp2 8u then 4u) where the 4u peak includes the 8u run [README.md:118-121].
- summarize.py reads every `<arm>-pass<k>/perf.json` and `<arm>-sw8k-pass<k>/perf.json` (repeat directories `<tag>-failed1` ignored) [summarize.py:89-120]; a cell is (model, users, prompt_length) written `model@<users>u-p<prompt_length>` [65-66]; the per-round lists are rebuilt from the flat per-request lists (a round = n_users values) [69-76].
- Output: a title line; "Runs found: <tag> (<cells> cells, <perf_minutes> min, tron <version>)" per run; the resolution-rule paragraph; two tables; "Driver stops:" when a run recorded a stop; "Per-provisioning checks (installed binary mapped by every engine, USE_HW_ATTN state): all ok" or "FAILED for ..."; an optional fidelity table against a nightly log [272-291]. summary.json holds the same rows [293-296].
- Table columns (both tables): cell | base TPS mean (sd over passes) n=<passes> | target TPS (same form) | delta % | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | delta ms (%) t=<t> | TTFT resolved | base VmHWM sum MiB | target VmHWM sum MiB | delta MiB (%) | base RSS sum MiB | target RSS sum MiB | delta MiB [summarize.py:204-221]. Table 1 is "Full passes (the harness's 14 configs, FPGA attention as shipped)"; table 2 is "Extra cell: qwen3-4b tp2, 8 users, prompt 8192, software attention (USE_HW_ATTN=0)" [281-282].
- The resolution rule: resolved = |paired t| >= 2.26 AND |delta| >= 1 % (for TTFT also |delta| >= 1 ms) [36, 188-190]; the paired t pools the per-round differences target minus base (round means) of every complete pass pair (pass1 with pass1, pass2 with pass2; n = 10 rounds per pair, so n = 20 with two pairs); t = mean / (sd / sqrt(n)) [52-62, 173-183]; 2.26 is the two-sided 5 % t for 9 degrees of freedom, conservative for 18 (2.10) [17-18; README.md:224-225]. "base TPS mean (sd over passes)" is the mean of the pass means with their standard deviation [16, 157-158]. Memory = the mean over passes of the sum over engine pids of VmHWM and of VmRSS from mem_after_benchmark, in MiB; hugepages are not in those sums [19-20, 156-162, 278-279]. n/t = no complete pass pair [214, 279].
- The sw8k cell: exec/pr4424ci-20261009/sw8k.json = one config: model ingested-qwen-3-4b-instruct-2507-tp2, nominal_users 8, prompt_length 8192, generate_length 1536, start_capture 896, end_capture 1024 (the TPS window inside the generation), prompt_mode sharegpt, user_sets [], shared_prompt_length 0 [sw8k.json:1-14; configs.py:19-22]. It runs with USE_HW_ATTN=0 written by `dut.sh hwattn-off` (14 bytes), engines restarted, `verify-env` in mode set (every pid exactly one USE_HW_ATTN=0 line), and the driver's own check CI_MIMIC_REQUIRE_HWATTN0=1 (rc 8 otherwise) [campaign.sh:170-175, 190-213, 291]. The 2026-10-09 result: base 59.84 TPS (sd 0.20, n=2), target 64.41 (0.26), +7.6 %, t +39.27 (20), resolved YES; TTFT 12,957 ms to 12,807 ms, -150 ms (-1.2 %), t -8.97, resolved YES; VmHWM +24 MiB (+0.1 %), RSS +41 MiB [summary.md:30].
- The 2026-10-09 full-pass table resolved three cells: llama-3.2-3b 32u -1.4 % TPS (t -16.56), llama-8b 32u prompt 4096 +4.8 % (t +39.40), Muse-Glimmer-30B tp4 +2.4 % (t +24.35) with TTFT -118 ms resolved; every other cell unresolved; every memory delta within 0.3 % [summary.md:11-24]. Per-provisioning checks: all ok [summary.md:32].
- A cosmetic defect: the "Runs found" line prints "tron None" because load_runs reads rec["versions"]["tron"] while the record's versions dict uses the key 'Tron (package)' [summarize.py:118; base-pass1/perf.json versions]. summarize.py also hard-codes the 2026-10-08 nightly in its title strings [summarize.py:2, 272] and RES_DEFAULT [35].

## 6. The recovery and resume procedures, verbatim

From README.md, "Stop, recovery, resume" [README.md:126-142]:

```text
- Stop early: `kill -TERM <pid>` (the pid launch.sh printed; never -9). The trap stops the driver and runs the restore
  path (config.env cleared first, restore.deb, engines down and up, marker released, flock released).
- Recovery after a SIGKILL, OOM or reboot (no trap ran): on delphi-3bda, in this order:

      kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/.lock.out)
      bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh hwattn-clear        # must print 0 bytes
      cat ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/base-identity.txt   # line "restore VERSION SHA FILE"
      bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh ensure-base VERSION SHA FILE
      IDLE_MIN=5 bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh serving-down
      bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh serving-up
      bash ~/workspace/intel-AMX/exec/bill-share.sh release
      stat -c %s /opt/positron/user/config.env                                     # must print 0

- Resume: `PASS_TAGS="<tags>" bash launch.sh` reruns only those tags; tags with a perf.json are skipped unless
  RESUME_OVERWRITE=1. The preflight then requires the nightly's deb to be installed again (it refuses a version that
  contains "jhan" and a rinzler that is the target build's).
```

From the campaign.sh header [campaign.sh:33-43]:

```text
# TO STOP EARLY: kill -TERM <pid of this script> (the pid launch.sh printed; NOT -9). That stops the driver and runs
# the restore + release path (hwattn-clear first). Do NOT pkill st_ci_perf.py alone.
# RECOVERY if this script died without its trap (SIGKILL, OOM, host reboot): on delphi-3bda
#   kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/.lock.out); flock -n /var/tmp/jhan/3bda-campaign.lock true && echo flock free
#   bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh hwattn-clear          (config.env must print 0 bytes)
#   cat ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/base-identity.txt   (line "restore VERSION SHA FILE")
#   bash .../dut.sh ensure-base VERSION SHA FILE
#   IDLE_MIN=5 bash .../dut.sh serving-down && bash .../dut.sh serving-up
#   bash ~/workspace/intel-AMX/exec/bill-share.sh release; stat -c %s /opt/positron/user/config.env   (must print 0)
# RESUME: PASS_TAGS="target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2" bash launch.sh reruns only those tags
# (a tag whose perf.json exists is skipped unless RESUME_OVERWRITE=1).
```

The restore path in code: restore_and_release runs once, on the normal path and on a signal; it waits for the DUT up to 30 min, clears config.env first ("production engines must never start with USE_HW_ATTN=0"), reinstalls RESTORE_VERSION from RESTORE_FILE, cycles serving with IDLE_MIN=5 only when the restore succeeded and config.env is clear (otherwise serving is taken down and left down for jhan), checks config.env is 0 bytes, releases Bill's marker, releases the flock; every failure is appended to `problems` and lands in outcome.txt [campaign.sh:216-256]. The PASS_TAGS example for the resume names the four tags of the second half of the ABBA order [campaign.sh:42].

## 7. The harness checkout and how launch.sh validates it

Requirements recorded in the README's validation record [README.md:146-157]: ~/workspace/ai-runs/systems_test at origin/main 14f0ce4 (moved from e4727d5 by `git merge --ff-only` on 2026-10-08); the one local change (testlib/prompt.py, the short-ShareGPT workaround of 2026-09-19) kept in `stash@{0}` and not applied (upstream replaced it with PromptGenerator.prepare); `uv sync --frozen` after the upstream pyproject.toml change (rebuilt the systems-test package only); harness unit tests `uv run --frozen pytest tests -q -x` = 2006 passed, 0 failed, 51 s; every tokenizer of the 14 configs and of the sw8k cell loads from the local HF cache (HF_HUB_OFFLINE=1), the Muse-Glimmer-30B tokenizer fetched on 2026-10-08 [README.md:165-168]; the talos stub FIRST on PYTHONPATH whenever scripts.perf is imported, because the real talos package registers an "Untitled Session" in the CI database at import (one such session was created by mistake on 2026-10-08 16:14 UTC) [README.md:219-222; configs.py:10-18].

My read-only check (run from this session):

```text
git -C ~/workspace/ai-runs/systems_test log --oneline -1
  -> 14f0ce4 Merge pull request #242 from positron-ai/rhys/discover-rinzler-log-units
git -C ~/workspace/ai-runs/systems_test status --porcelain | head
  -> (empty: no local changes)
git -C ~/workspace/ai-runs/systems_test stash list
  -> stash@{0}: On main: pr4424ci-20261009: prompt.py short-ShareGPT workaround of 2026-09-19 (superseded upstream by 14f0ce4 PromptGenerator.prepare)
```

Also: the local remote-tracking origin/main is 14f0ce4 (no fetch was made; whether GitHub's main has moved since 2026-10-08 is Insufficient data); the commit date of 14f0ce4 is 2026-10-08T12:46:49-07:00; the venv python is ~/workspace/ai-runs/systems_test/.venv/bin/python 3.12.7; uv on claude-box is 0.11.21 at ~/.local/bin/uv (the deb build on delphi-3bda uses /tools/uv/0.9.5 [build-target.sh:87]); ~/.cache/huggingface/hub holds models--meta-models--Muse-Glimmer-30B, models--google--gemma-4-31B-it and models--openai--gpt-oss-120b among others (the full 15-cell check is the README's record, not re-run here).

How launch.sh validates the harness: the venv python must compile st_ci_perf.py, summarize.py, configs.py [launch.sh:23]; HEAD not at origin/main prints a NOTE only ("the driver follows the checkout") [27]; any change under scripts/ or testlib/ (`git status --short -- scripts testlib`) is fatal ("fidelity with the nightly needs a clean checkout") [28]; the stash is not inspected. launch.sh also requires RESD/check-mode/perf.json to be newer than st_ci_perf.py [25-26]; a fork with a new results directory must therefore run the check mode once into that directory. No file records the exact check-mode command; the driver's check branch is `if os.environ.get("CI_MIMIC_CHECK") == "1"` [st_ci_perf.py:463], the recorded check run had arm "check-mode", configs_json "" and the same OPENAI_HOST, PLATFORMD_PORT 8080, SYSTEM_CI_SPECULATION 0, ssh_user jhan as run_pass sets [results/pr4424ci-20261009/check-mode/perf.json]; a reconstruction from run_pass (campaign.sh:285-293) plus those three values is:

```text
cd ~/workspace/ai-runs/systems_test && mkdir -p <RESD>/check-mode && env PYTHONPATH=<H>/talos_stub:$PWD \
  OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 \
  PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= \
  HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false \
  CI_MIMIC_CHECK=1 CI_MIMIC_ARM=check-mode CI_MIMIC_OUT=<RESD>/check-mode/perf.json TALOS_STUB_OUT=<RESD>/check-mode/talos.json \
  CI_MIMIC_MODELS="" CI_MIMIC_CONFIGS_JSON="" CI_MIMIC_LEASE_CHECK=1 CI_MIMIC_DUT_HELPER=<H>/dut.sh \
  .venv/bin/python <H>/st_ci_perf.py > <RESD>/check-mode/driver.log 2>&1
```

(labeled: a reconstruction; the author should have the executor verify it against st_ci_perf.py:389-480 before use). The check mode is read-only against the DUT and prints the CHECK lines of README.md:194-212; "ok=False counts={pid: 0}" is the correct as-shipped state with config.env at 0 bytes [README.md:214-216].

The configs files are regenerated with the talos stub first on PYTHONPATH [configs.py:10-11]:

```text
cd ~/workspace/ai-runs/systems_test && PYTHONPATH=<this dir>/talos_stub:$PWD .venv/bin/python <this dir>/configs.py
```

## 8. Machine-use cost, and the name and content of a PR-4 fork

Cost measured on 2026-10-09: whole machine (Bill's marker held, production serving cycled 9 times) 8 h 26 min 15 s; driver time 7 h 45 min; the target deb build 16 min 38 s on socket 1 next to serving. A PR-4 repeat with two built debs adds a second build of about the same length (est. from the one measurement: 2 x 17 min on our half). The README's planning figure "four arm passes are about 8 h: from a 13:20 start the last pass ends about 21:30" [README.md:76-77] matched the measurement within 35 min.

Name and locations (following the stack's convention `pr<N>-<date>` for exec folders, results and logs [PR3-handoff.md step 6: exec/pr3-<date>/, exec/results/pr3-<date>/, exec/logs/pr3-<date>-chain.log]): the campaign fork could be exec/pr4ci-<date>/ with NAME=pr4ci-<date>, results exec/results/pr4ci-<date>/, log exec/logs/pr4ci-<date>.log, OUT=/var/tmp/jhan/pr4ci-<date>/ on delphi-3bda, worktrees /var/tmp/jhan/tron-pr4ci (target) and /var/tmp/jhan/tron-pr4ci-base (base), local branches jhan-pr4ci-target and jhan-pr4ci-base, and a hand-off marker /var/tmp/jhan/pr4ci-<date>-precheck.running created by the PR-4 chain. These names are a proposal for the author, not a record.

Which files are byte-identical copies and which change (md5 prefixes of the current files: st_ci_perf.py cbe17ef1cc26, talos_stub/talos.py 1d6a172cc04c, nightly_to_arm.py e60ef505caa8, configs.py a6c4eaf9a256, summarize.py 4ec9fbe40b23, dut.sh 888f0acf6d04, campaign.sh dc9ea3d6bb6f, launch.sh bc0e435e57c5, build-target.sh 88883d07375c):

- Byte-identical copies: st_ci_perf.py (its only campaign reference is the docstring at line 47; every path and name comes from the environment), talos_stub/talos.py (identical to the q4b-fpga and ci-mimic copies already), nightly_to_arm.py (identical to ci-mimic's), sw8k.json, configs.py (the docstring names the campaign; it writes next to itself). nightly14.json is a record; regenerate it with configs.py.
- campaign.sh: NAME [61] (H and RES derive from it [62-63]); the defaults of EXPECTED_BASE, EXPECTED_BASE_SHA, NOT_BEFORE, DEADLINE_START, PASS_DEADLINE, DRIVER_END_BY [70-75]; PRECHECK_MARKER [358]; the header's arm description and recovery paths [2-8, 35-41]; the arms stay "base" and "target" (arm_known at 167).
- launch.sh: H, RESD, LOG, OUT [11-15]; the EXPECTED_BASE default in the nightly.deb check [32]; the pgrep pattern derives from H [18].
- dut.sh: OUT [37]; the ensure-target wording if the arm names change; nothing else is campaign-specific.
- build-target.sh: WT, OUT, BRANCH [24-26]; the conditional grep [48]; the conditional preset edit and check [50-79]; per-arm output names [93-97, 103-111]; the manifest's options and note [106-109].
- summarize.py: RES_DEFAULT [35]; the title and docstring strings [2, 272]; optionally the versions key [118].
- README.md: rewritten for the fork.

Exact commands the executor runs today (the fork replaces the folder names):

```text
# 1. build on delphi-3bda (socket 1; not during the nightly's perf phase, not next to another build of ours)
ssh delphi-3bda bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/build-target.sh <COMMIT>
# 2. read-only state of the DUT
ssh delphi-3bda bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/dut.sh preflight
# 3. launch from claude-box (knobs through the environment)
NOT_BEFORE=<D>T13:00:00Z DEADLINE_START=<D>T19:00:00Z PASS_DEADLINE=<D+1>T00:30:00Z DRIVER_END_BY=<D+1>T02:05:00Z \
  bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/launch.sh
# 4. watch
cat ~/workspace/intel-AMX/exec/results/pr4424ci-20261009/.status
tail -f ~/workspace/intel-AMX/exec/logs/pr4424ci-20261009.log
# 5. stop early
kill -TERM <pid printed by launch.sh>
# 6. resume
PASS_TAGS="target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2" bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/launch.sh
# 7. summary by hand, with the nightly's own numbers
cd ~/workspace/ai-runs/systems_test && .venv/bin/python ~/workspace/intel-AMX/exec/pr4424ci-20261009/summarize.py \
    --nightly-log <gh run view --log of the nightly> --nightly-date <D>
```

[README.md:53-85, 126-142]. The 2026-10-09 launch set PASS_DEADLINE to 00:30 of the next day; the README's knob table still shows the default 23:30 [README.md:68; status-history.log:1].

Expected PR-4 claims this campaign backs, from the stack plan: "llama-8b 32 users at prompt 4096 about +5 % TPS, qwen 8k software attention about +8 %, qwen FPGA attention within noise, llama-3.2-3b about -1.4 % = the kv_mul 3 open item, memory within 0.3 %" [split-handoff.md 5.4, PR-4 row]; the 2026-10-09 measurements are +4.8 %, +7.6 %, -0.9 % (unresolved) at tp2 and -0.4 % at tp4, -1.4 %, and every VmHWM delta within 0.3 % [summary.md:11-30].

--- concerns ---
- Base-arm decision conflict: split-handoff.md step 4 (line 201) says the campaign's base is "the nightly deb of the day"; the task says the base is a deb WE build from main 72308ec90c. The handoff must record which one PR-4 uses and why. A built base loses the campaign's fidelity check against the nightly's own numbers (summarize.py --nightly-log compares our base arm with the nightly's deb of the same main).
- The hand-off marker race: on 2026-10-09 the campaign tested the pre-check marker at 13:36:08 and precheck.sh created it at 13:36:11 (3 s later), so the pre-check never ran before the campaign and its host suite ran at 22:10 with serving up. exec/pr3-20261012/chain2.sh creates no marker. The PR-4 chain fork must create the marker BEFORE its lease wait and remove it in its finish handler, and the campaign fork's PRECHECK_MARKER must name the same file.
- A built base deb should carry a branch name with "jhan" (build on a local branch, as build-target.sh does for the target), because campaign.sh:415 tells our debs from nightlies by that substring only and dut.sh:63-64 compares the installed rinzler with rinzler.target only. A detached build would look like a nightly (2026.10.1x-72308ec9) and a crash followed by a resume could adopt it as the restore target.
- EXPECTED_BASE must equal the built deb's Version field exactly and EXPECTED_BASE_SHA its rinzler sha256; otherwise save-base-deb tries an apt download that fails (abort 5) or ensure-base fails at the first package step after Bill's marker was taken and serving was cycled. Verify both with dpkg-deb before the launch.
- launch.sh:25-26 requires RESD/check-mode/perf.json newer than st_ci_perf.py; a fork with a new results directory needs one check-mode run. No file records the exact check-mode command; the report gives a reconstruction from run_pass's environment that the executor must verify against st_ci_perf.py:389-480.
- Harness fidelity: the campaign follows the checkout (14 configs at 14f0ce4, 2026-10-08). Whether GitHub's systems_test main has moved since is Insufficient data (no fetch in this read-only task). Moving the checkout needs uv sync --frozen, the harness unit tests, the offline tokenizer check for any new model (the Muse-Glimmer precedent) and a new check-mode run; launch.sh only prints a NOTE when HEAD differs from origin/main.
- Scheduling: the W campaign (8 h 26 min measured) and the PR-4 chain's whole-machine part (PR-3's took 93 min) and bench --update all need the whole machine. In one window from a 13:36 lease clear the campaign would end about 23:40 UTC; a lease that clears 2 h late leaves 35 min of margin for the last full pass under the need rule. The author must decide one window or two days, and the order (chain before campaign, with the marker).
- The 2026-10-09 run used PASS_DEADLINE=2026-10-10T00:30:00Z (status-history.log:1), not the README table's default 23:30 (README.md:68). The README table is out of date on that row.
- summarize.py prints "tron None" in its Runs found line (it reads versions["tron"], the record has 'Tron (package)') and hard-codes the 2026-10-08 nightly in its title and docstring; cosmetic, but a fork should fix the strings so the summary names PR-4's arms.
- bin/get-version.sh returns an exact tag as the version when HEAD carries one; the local tag pr4424-pre-split-0a5334ccb6 exists in ~/workspace/tron. PR-4's head and 72308ec90c carry no tag, so this does not bite unless a build is made exactly at 0a5334ccb6; worth one sentence in the handoff.
- build-target.sh's preset-edit guard (line 54) tests the substring '"TRON_K_VNNI": "ON"' anywhere in CMakePresets.json, not only in the deb preset; for PR-4's head it exits 0 with the message "TRON_K_VNNI already ON somewhere in CMakePresets.json; no edit" (the exact text, not "already ON"). The fork's base build must skip this block entirely, or the base deb would gain the option.
- Bill's marker: the executor's pre-launch checkpoint must state that campaign.sh takes the marker itself on jhan's order (bill-share.sh:12 and the memory rule forbid a take on a script's own initiative); a take refused with rc 2 (Bill active) is reported, retried only until DEADLINE_START, and never forced.
