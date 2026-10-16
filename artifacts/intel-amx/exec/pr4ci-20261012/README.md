# pr4ci-20261012: campaign W of PR-4, the nightly perf phase by hand, base deb (main) against the PR-4 deb

Short version: these scripts re-run three configs of the nightly System CI perf phase on the whole of delphi-3bda
for two Debian packages of tron, the base (main at 72308ec90c) and the target (PR-4's head), in four passes (base,
target, target, base), with memory snapshots. They are a fork of exec/pr4424ci-20261009 (the 2026-10-09 campaign,
which ran all 14 configs plus a software-attention cell) with the changes that PR4-handoff.md section 5.3 ("Campaign
W") asks for and the scope jhan set on 2026-10-12 (three configs, no sw8k cell).

## Scope (jhan, 2026-10-12)

- The cells: llama-3.1-8b-instruct-good-tp2 at 8 users prompt 1024, llama-3.1-8b-instruct-good-tp2 at 32 users
  prompt 4096, and ingested-gpt-oss-120b-tp4 at 8 users prompt 1024. They are the file subset3.json: the three
  entries of nightly14.json, byte for byte (checked on 2026-10-12); nightly14.json stays as the record of the full list.
- The passes: base-pass1, target-pass1, target-pass2, base-pass2 (PASSES = "base target target base"). No sw8k cell:
  the knob SW8K defaults to 0, which leaves the <arm>-sw8k-pass<k> tags out of the tag list (campaign.sh builds the
  tags from PASSES as before; PASS_TAGS and the resume logic are unchanged). SW8K=1 gives the 2026-10-09 behaviour.
- FULL_CONFIGS defaults to subset3.json in launch.sh and campaign.sh (unset = subset3.json; "" = the harness's own
  14-entry list; a path = that file).
- The need rule's floor is the knob NEED_FLOOR_S (default 6600 s = 110 min, the 14-config value; the launch passes
  1800). A full pass starts only when max(the longest measured full pass + 10 min, NEED_FLOOR_S) remains before
  DRIVER_END_BY. The duration of a 3-config pass is Insufficient data until measured (the 14-config pass took 106 to
  110 min on 2026-10-09; the three cells' share of it is not recorded per cell in summary.md).
- summarize.py prints "sw8k cell: not run" under the sw8k heading when no sw8k results exist (checked on 2026-10-12
  against the four full passes of the 2026-10-09 record alone).

The comparison baseline is the 2026-10-09 record exec/results/pr4424ci-20261009/summary.md: the PR 4424 deb
(2026.10.09-667b2ce5-jhan-pr4424ci-target) against the nightly deb of main be0d5565b3 (2026.10.08-be0d5565), two
pass pairs, 10 rounds per pass. Its rows for the three cells (TPS = generated tokens per second per user, mean over
passes with the sd over passes in parentheses; TTFT = time to first token in ms; resolved = |paired t| >= 2.26 and
|delta| >= 1 %):

| cell | base TPS (sd) | target TPS (sd) | TPS delta | paired t (n rounds) | resolved | base TTFT ms | target TTFT ms | TTFT delta | TTFT resolved |
|---|---|---|---|---|---|---|---|---|---|
| llama-3.1-8b-instruct-good-tp2@8u-p1024 | 143.03 (0.55) | 142.58 (0.57) | -0.3 % | -1.35 (20) | no | 586 | 585 | -0 ms (-0.1 %), t = -0.05 | no |
| llama-3.1-8b-instruct-good-tp2@32u-p4096 | 32.62 (0.02) | 34.20 (0.03) | +4.8 % | +39.40 (20) | YES | 11,821 | 11,833 | +12 ms (+0.1 %), t = +0.66 | no |
| ingested-gpt-oss-120b-tp4@8u-p1024 | 122.38 (0.05) | 121.83 (1.34) | -0.5 % | -1.28 (20) | no | 966 | 944 | -22 ms (-2.3 %), t = -1.93 | no |

Memory from the same rows (sum over engines of VmHWM, the peak resident set, in MiB; base / target / delta):
llama-8b 21,926 / 21,930 / +5 (both cells, the engines are kept between them); gpt-oss-120b 128,490 / 128,492 / +2.
In that record only the llama-8b 32-user prompt-4096 cell resolved (+4.8 % TPS for the PR 4424 deb); the other two
cells and every TTFT were noise. PR-4's base and target are different builds (main 72308ec90c and PR-4's head), so
the new numbers are compared cell by cell with these, not subtracted from them.

## Words used here

- tron: the inference program. rinzler: its production server binary (/opt/positron/bin/rinzler). deb: the Debian
  package of tron. platformd 0.11: the service that starts the rinzler engines.
- delphi-3bda ("the DUT", device under test): the Intel Xeon 6 test server. claude-box: the client host where
  campaign.sh runs; it drives delphi-3bda over ssh.
- The chain: exec/pr4-20261012/chain2.sh, the PR-4 build-and-test script on delphi-3bda. Its our-half verdict is the
  file exec/results/pr4-20261012/all.done (ok or a failure string); its end verdict is chain.done in the same folder.
- The nightly (System CI): the nightly test job that installs the newest tron deb on delphi-3bda at about 03:30 UTC
  and holds the CI lease (/run/lock/systems-test-ci.lease) until about 13:20 to 13:36 UTC.
- Hand-off marker: /var/tmp/jhan/pr4424ci-precheck.running on delphi-3bda. The chain writes it at launch and its
  exit handler removes it. W waits, after the lease, until it is gone. The file name is the 2026-10-09 campaign's.
- Bill's marker: /bill-has-instance-0,2 on delphi-3bda; present = Bill (a colleague) may use socket 0. W takes it
  with bill-share.sh take before its passes and re-creates it with release at the end.
- Campaign flock: /var/tmp/jhan/3bda-campaign.lock, held for the whole run so two of our campaigns never overlap.
- base arm: base.deb, built from main at 72308ec90c on the local branch jhan-pr4ci-base; copied to nightly.deb,
  the file name dut.sh expects for the base arm. target arm: target.deb, built from PR-4's head on the local branch
  jhan-pr4ci-target. Both versions carry "jhan" (2026.10.<build day>-<8 chars>-jhan-pr4ci-<arm>).
- EXPECTED_BASE, EXPECTED_BASE_SHA: the base deb's Version field (`dpkg-deb -f base.deb Version`) and the sha256
  of its rinzler; both are in /var/tmp/jhan/pr4ci-20261012/manifest-base.json ("version", "rinzler_sha256").
- restore target: whatever deb is installed when the campaign starts (the nightly's), saved as restore.deb and
  reinstalled at the end.
- USE_HW_ATTN: an environment variable of rinzler. Unset = attention on the FPGA cards (the nightly as shipped);
  USE_HW_ATTN=0 = software attention on the CPU, set through /opt/positron/user/config.env (14 bytes; 0 bytes = unset).
- full pass: the harness's 14 perf configs with config.env empty, tag `<arm>-pass<k>`. sw8k cell: qwen3-4b tp2, 8
  users, prompt length 8192 tokens, 1536 generated tokens, USE_HW_ATTN=0, tag `<arm>-sw8k-pass<k>`.
- recovered pass: a pass whose first driver run failed and whose repeat succeeded. The data is complete; the first
  attempt is kept in `<tag>-failed1`.
- codex points 1 to 3: three defects of the inherited campaign.sh that the handoff's reviewer found (marker release
  without ownership, restore without a lease test, a recovered pass counted as a failure). This fork fixes them.
- Option (a) / option (b): the two schedules of PR4-handoff.md section 5.3 ("The schedule"); see "How to run".

## What changed from exec/pr4424ci-20261009, and why

| file | change | why |
|---|---|---|
| build-deb.sh (new; fork of build-target.sh) | ARM=base or ARM=target from the environment, the commit as the first argument; worktree /var/tmp/jhan/tron-pr4ci-$ARM on the local branch jhan-pr4ci-$ARM; per-arm outputs (base: base.deb + nightly.deb, rinzler.base, manifest-base.json, build-base.status, make-deb-base.log; target: target.deb, rinzler.target, manifest.json, build.status, make-deb.log); no preset edit, a preset CHECK instead (TRON_AMX_DISPATCH ON for both; TRON_K_VNNI absent for the base, ON for the target); the kv_cache.hpp Note grep for the target only; the worktree must be clean; the build head must equal the commit; the Version field must carry the branch name and not "-dirty"; the manifest gains "arm" and "version" | both arms are now builds of ours, from two trees that differ in the deb preset (handoff section 5.3, "The deb recipe"; step 6, edit 11) |
| campaign.sh | NAME, paths and header; EXPECTED_BASE and EXPECTED_BASE_SHA without default (the run refuses when empty); option (a) date defaults; the chain.done gate after "pre-check marker absent"; W_TOOK_MARKER and W_TOOK_MACHINE (codex point 1); the lease re-test before each restore step with restore-deferred.txt (codex point 2); the recovered-pass count and the outcome.txt field "recovered passes:" (codex point 3); the scope knobs FULL_CONFIGS (default subset3.json), SW8K (default 0) and NEED_FLOOR_S (default 6600) | handoff section 5.3, "Campaign W"; the scope of 2026-10-12 |
| launch.sh | paths; build-deb.sh in the syntax check; build-base.status must be ok; EXPECTED_BASE and EXPECTED_BASE_SHA required and compared with nightly.deb's Version field and rinzler.base's sha256 on the DUT; the all.done gate; option (a) date defaults; FULL_CONFIGS defaults to subset3.json and is checked to parse | the same |
| subset3.json (new) | the three cells of the scope, filtered from nightly14.json | the scope of 2026-10-12 |
| dut.sh | OUT; the preflight's process pattern names build-deb | the same |
| summarize.py | the default results folder, the title strings; the "Runs found" line reads the record's key "Tron (package)" (it printed "tron None" on 2026-10-09); "sw8k cell: not run" when no sw8k results exist | the same |
| st_ci_perf.py, talos_stub/talos.py, nightly_to_arm.py, sw8k.json, configs.py | byte-identical copies | unchanged by the handoff |
| nightly14.json | a copy of the 2026-10-09 file, NOT regenerated | regenerating it imports the harness (scripts.perf); the full passes do not read this file (campaign.sh passes CI_MIMIC_CONFIGS_JSON="" and the driver uses the harness list directly), so the copy is a record only. To refresh it: `cd ~/workspace/ai-runs/systems_test && PYTHONPATH=<this dir>/talos_stub:$PWD .venv/bin/python <this dir>/configs.py` (the talos stub first on PYTHONPATH, or the real talos package registers a session in the CI database) |
| w-cleanup-test.sh (new) | the stubbed fixture of the restore path; its record is w-cleanup-test.log | the handoff's acceptance cases for codex points 1 to 3 |

Behaviour that the fork changes on purpose, beyond the edits the handoff lists:

- A SIGTERM or an abort while W still waits (lease, hand-off marker, chain.done gate, peers, flock) makes no
  bill-share.sh call and no dut.sh change. The inherited script released Bill's marker there.
- When Bill's marker is already absent when W reaches it, W does not take it and does not release it at the end
  (the log says so). The inherited script re-created it at the end in that case.
- W_TOOK_MACHINE is set right before the first ensure_state, inside the pass loop. So a run whose pass loop stops
  before any pass (DEADLINE_START passed, lease busy before the first tag, not enough time) restores nothing and
  does not restart production. The inherited script reinstalled the package (a no-op) and restarted the engines.
- A lease reading of "unknown" (the DUT did not answer the lease check three times) before a restore step does not
  defer the restore: the step runs and the problem LEASE-UNKNOWN-BEFORE-<step> is recorded. Only "busy" defers.
- The chain.done read retries an ssh-level failure three times (60 s apart); a missing file aborts at once.
- EXPECTED_BASE_SHA must be a 64-character hex string, not only non-empty (the inherited sha reader uses the same test).

## Files

| file | runs on | what it does |
|---|---|---|
| build-deb.sh | delphi-3bda (the chain's step deb, or by hand) | builds one deb: `ARM=base bash build-deb.sh <MAIN_COMMIT>`, `ARM=target bash build-deb.sh <COMMIT>`; about 17 min each, measured 2026-10-08 |
| dut.sh | delphi-3bda (over ssh) | installed, preflight, ensure-target, ensure-base VERSION SHA [FILE], save-base-deb VERSION [FILE], hwattn-off, hwattn-clear, verify-env, memsnap, lease-free, serving-down (IDLE_MIN), serving-up |
| st_ci_perf.py + talos_stub/talos.py | claude-box | the driver: the harness's perf phase with memory snapshots; the talos stub keeps the reporting calls local |
| campaign.sh | claude-box (detached) | the campaign: waits, gates, locks, marker, preflight, restore.deb, passes, restore, summary |
| launch.sh | claude-box | validates and starts campaign.sh with setsid + nohup |
| summarize.py | claude-box | the tables (summary.md, summary.json) |
| w-cleanup-test.sh | claude-box | the stubbed fixture of the restore path (never against the live machine) |

Results: exec/results/pr4ci-20261012/ (per tag perf.json, driver.log, summary.txt, talos.json; preflight.txt,
base-identity.txt, configs-used*.json, outcome.txt, status-history.log, restore-deferred.txt when the restore was
deferred, summary.md, summary.json, check-mode/). Log: exec/logs/pr4ci-20261012.log. Packages: /var/tmp/jhan/pr4ci-20261012/.

## Knobs (UTC; env variables with their defaults)

| knob | default | meaning |
|---|---|---|
| EXPECTED_BASE | none (required) | the base deb's Version field; launch.sh compares it with nightly.deb on the DUT |
| EXPECTED_BASE_SHA | none (required) | the base deb's rinzler sha256; launch.sh compares it with rinzler.base on the DUT |
| NOT_BEFORE | 2026-10-13T13:05:00Z | option (a): sleep until here before the first lease check (five minutes after the chain's START_NOT_BEFORE) |
| DEADLINE_START | 2026-10-14T01:35:00Z | option (a): the first pass must have started by here, else abort. After the chain's END_BY (01:30), so W never aborts while the chain can still hold the whole machine |
| PASS_DEADLINE | 2026-10-14T01:40:00Z | option (a): no further full pass starts after here (the need rule below is the tighter bound) |
| DRIVER_END_BY | 2026-10-14T02:05:00Z | hard end: every driver run is cut here; the restore takes up to 16 min; the ci-runner-stop timer is at 02:45 |
| DRIVER_TIMEOUT / SW8K_TIMEOUT | 9000 s / 1800 s | per full pass / per sw8k cell |
| PASSES | base target target base | the arm order; each arm pass = one full pass (plus the sw8k cell only with SW8K=1) |
| PASS_TAGS | (empty) | resume: run only these tags (base-pass1 target-pass1 target-pass2 base-pass2 are the four of this scope) |
| FULL_CONFIGS | subset3.json (when unset) | the cells of a full pass; "" = the harness's own 14-entry list; a path = that file |
| SW8K | 0 | 1 = the sw8k cell after every full pass (the 2026-10-09 behaviour) |
| NEED_FLOOR_S | 6600 | the floor of the full-pass need rule in seconds; pass 1800 for this scope |
| RESUME_OVERWRITE, HANDOFF, AMX_PROBE, HF_OFFLINE, NO_WAIT | 0, up, 1, 1, 0 | unchanged from the 2026-10-09 folder |

The need rule: a full pass starts only when at least max(the longest measured full pass + 10 min, 110 min) remains
before DRIVER_END_BY; a sw8k cell needs max(its longest run + 10 min, 20 min).

## How to run

1. The chain's step deb builds both packages on delphi-3bda (the chain calls build-deb.sh twice; the by-hand form is
   in the Files table). Do not run a build while the nightly's perf phase runs, and not next to another build of ours.
   After the builds, read the base identity on delphi-3bda:

       python3 -c 'import json; d=json.load(open("/var/tmp/jhan/pr4ci-20261012/manifest-base.json")); print(d["version"], d["rinzler_sha256"])'

2. Run the driver's check mode once, after the last edit of st_ci_perf.py and while the lease is free (launch.sh
   requires check-mode/perf.json to be newer than st_ci_perf.py). The check is read-only against the DUT. One line:

       H=~/workspace/intel-AMX/exec/pr4ci-20261012; RESD=~/workspace/intel-AMX/exec/results/pr4ci-20261012; ST=~/workspace/ai-runs/systems_test; mkdir -p $RESD/check-mode; (cd $ST && env PYTHONPATH="$H/talos_stub:$ST" OPENAI_HOST=http://delphi-3bda.positron.internal/v1 OPENAI_TOKEN=token-secret PLATFORMD_PORT=8080 PLATFORM_TYPE=granite_rapids_72_rinzler SYSTEM_CI_SPECULATION=0 SSH_USER=jhan SSH_PASS= HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_OFFLINE=1 TOKENIZERS_PARALLELISM=false CI_MIMIC_CHECK=1 CI_MIMIC_ARM=check-mode CI_MIMIC_OUT=$RESD/check-mode/perf.json TALOS_STUB_OUT=$RESD/check-mode/talos.json CI_MIMIC_MODELS= CI_MIMIC_CONFIGS_JSON= CI_MIMIC_AMX_PROBE=0 CI_MIMIC_REQUIRE_HWATTN0=0 CI_MIMIC_REQUIRE_HWATTN_UNSET=0 CI_MIMIC_LEASE_CHECK=1 CI_MIMIC_DUT_HELPER=$H/dut.sh $ST/.venv/bin/python $H/st_ci_perf.py >$RESD/check-mode/driver.log 2>&1); echo rc=$?

   Expected: rc 0 and the line "CHECK ok: <n> supported models" in driver.log. The line "CHECK USE_HW_ATTN=0 per
   engine pid: ok=False ..." is the normal reading with config.env at 0 bytes, not a failure.

3. Launch from claude-box. launch.sh checks the files, the two build status files, the base identity, the chain's
   all.done = ok, platformd 0.11, the harness checkout, the check mode, no peer process, and the knobs, then starts
   campaign.sh detached and prints the pid and the log path.

   Option (a) (the chain's whole-machine run 2 holds until day D+1 13:00 UTC; W waits on the lease and then on the
   hand-off marker; the defaults are the option (a) values):

       EXPECTED_BASE=<version> EXPECTED_BASE_SHA=<sha256> NEED_FLOOR_S=1800 bash ~/workspace/intel-AMX/exec/pr4ci-20261012/launch.sh

   Option (b) (the chain's whole-machine part ran on day D evening; W runs alone on day D+1):

       EXPECTED_BASE=<version> EXPECTED_BASE_SHA=<sha256> NEED_FLOOR_S=1800 NOT_BEFORE=2026-10-13T13:00:00Z DEADLINE_START=2026-10-13T19:00:00Z PASS_DEADLINE=2026-10-14T00:30:00Z DRIVER_END_BY=2026-10-14T02:05:00Z bash ~/workspace/intel-AMX/exec/pr4ci-20261012/launch.sh

   In option (b), launch W before the chain's run 2 starts its smokes or after its chain.done (the peer gate refuses
   while a runtron of ours runs on the DUT). W then sleeps until its NOT_BEFORE.

4. Watch: `cat exec/results/pr4ci-20261012/.status` (one line, the current step), the log, and status-history.log.

5. At the end the campaign restores production (config.env cleared first, restore.deb reinstalled, engines down and
   up, Bill's marker released, flock released; each DUT change preceded by a lease test), writes outcome.txt and a
   .done / .done-with-failures / .done-aborted marker, and runs summarize.py into summary.md and summary.json. With
   SW8K=0 config.env is never written, so the restore has no hwattn-clear step (the first ensure_state clears it once).
   outcome.txt reads `incomplete passes: none; stop reason: none; problems: none; known systematic failures: none;
   recovered passes: <none or the tags>` on a clean run.

## Stop, recovery, resume

- Stop early: `kill -TERM <pid>` (the pid launch.sh printed; never -9). The trap stops the driver and runs the restore
  path. Never stop W, and never let its DEADLINE_START pass, while the chain holds the whole machine (between the
  chain's marker take and its exit handler); the ownership flags make such a stop harmless to the marker, and the
  rule stays as a second layer.
- A deferred restore ("TAKEOVER: restore deferred" in .status; problems contain RESTORE-DEFERRED): the CI lease read
  busy before a restore step. W made no further DUT change and did not release Bill's marker; it released the flock.
  Read exec/results/pr4ci-20261012/restore-deferred.txt (the restore target, the config.env state, whether the marker
  is still taken). After the lease clears (about 13:25 UTC the next day; light work only until then), on delphi-3bda:

      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh hwattn-clear        # when config.env is not 0 bytes
      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh ensure-base VERSION SHA FILE   # from restore-deferred.txt; usually a no-op, the nightly installs its own deb
      IDLE_MIN=5 bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh serving-down
      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh serving-up
      bash ~/workspace/intel-AMX/exec/bill-share.sh release                     # only when restore-deferred.txt says the marker is still taken
      stat -c %s /opt/positron/user/config.env                                  # must print 0

  Record each result in split-status.md (the handoff's section 7 lists this as a stop-and-ask).
- Recovery after a SIGKILL, OOM or reboot (no trap ran): on delphi-3bda, in this order:

      kill $(awk '/^held pid/{print $3}' ~/workspace/intel-AMX/exec/results/pr4ci-20261012/.lock.out)
      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh hwattn-clear        # must print 0 bytes
      cat ~/workspace/intel-AMX/exec/results/pr4ci-20261012/base-identity.txt   # line "restore VERSION SHA FILE"
      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh ensure-base VERSION SHA FILE
      IDLE_MIN=5 bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh serving-down
      bash ~/workspace/intel-AMX/exec/pr4ci-20261012/dut.sh serving-up
      bash ~/workspace/intel-AMX/exec/bill-share.sh release                     # only when the log shows "Bill's marker taken" by this run
      stat -c %s /opt/positron/user/config.env                                  # must print 0

- Resume: `PASS_TAGS="<tags>" bash launch.sh` reruns only those tags; tags with a perf.json are skipped unless
  RESUME_OVERWRITE=1. The preflight requires the nightly's deb to be installed again (it refuses a version that
  contains "jhan" and a rinzler that is the target build's). A pass skipped for "not enough time before DRIVER_END_BY"
  (option (a) with a late lease) is re-run on day D+2 with the knobs moved by one day:

      PASS_TAGS="base-pass2" EXPECTED_BASE=<version> EXPECTED_BASE_SHA=<sha256> NEED_FLOOR_S=1800 NOT_BEFORE=2026-10-14T13:00:00Z DEADLINE_START=2026-10-14T19:00:00Z PASS_DEADLINE=2026-10-15T00:30:00Z DRIVER_END_BY=2026-10-15T02:05:00Z bash ~/workspace/intel-AMX/exec/pr4ci-20261012/launch.sh

## The fixture (w-cleanup-test.sh)

`bash w-cleanup-test.sh` runs campaign.sh against stubs in a temp dir (a stub ssh answers every remote command; a
stub python stands in for the driver and for summarize.py) and never touches delphi-3bda. It covers 21 cases: the
handoff's acceptance cases for codex points 1 to 3 (a stop or an abort in the waits; a normal completion; a stop
after the first pass; a takeover between passes; a driver rc 9; a lease that turns busy between two restore steps;
a free lease; a recovered pass; two failed attempts) plus the chain.done gate, the empty EXPECTED_BASE refusal, an
abort in the preflight after the marker take, the fork's scope (SW8K=0: the four tags, a restore without
hwattn-clear, subset3.json handed to the driver; SW8K=1 gives the eight 2026-10-09 tags) and the NEED_FLOOR_S rule (1800 lets a pass start with 40 min
left; the default 6600 stops it). Cases 3 to 10 run with SW8K=1 on purpose: the sw8k tag drives the config.env path
of the restore. The record of the 2026-10-12 run is w-cleanup-test.log (21 of 21 PASS). The run takes about 4 min:
the campaign's own 20-s wait after each package switch is real.

## Caveats

- The deb preset check of build-deb.sh needs PR-4's commit to carry `"TRON_K_VNNI": "ON"` in the deb preset of
  CMakePresets.json; the check was dry-run on 2026-10-12 against main's file (absent: passes) and against a tree
  without the switch (ON: refused).
- The 2026-10-09 record exec/results/pr4424ci-20261009/ is the reference for every expected log line (check-mode,
  preflight, outcome.txt). The hand-off marker file name is the 2026-10-09 campaign's; the chain writes it.
- summarize.py's paired t pools both pass pairs (n = 20 rounds) but keeps the 9-degree-of-freedom threshold 2.26,
  which is conservative (the 18-df 5 % point is 2.10), as in the 2026-10-09 folder.
- The talos stub must be first on PYTHONPATH whenever scripts.perf is imported (configs.py does this): importing the
  real talos package registers a session in the CI results database.
