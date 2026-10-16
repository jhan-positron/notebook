# pr4424ci-20261009: the nightly perf phase by hand, base deb against the PR 4424 deb, with memory

Short version: these scripts re-run the nightly System CI perf phase on the whole of delphi-3bda after the
2026-10-09 nightly ends, once per package arm and pass (base, target, target, base), plus one extra prompt-8192 cell
per pass with software attention. Every config also gets a memory snapshot of the engines. Build the target deb on
delphi-3bda first, then start the campaign from claude-box with launch.sh.

## Words used here

- delphi-3bda: the Intel Xeon 6 test server (ssh alias `delphi-3bda`, user jhan). "DUT" = device under test = this machine.
- claude-box: the client host where campaign.sh runs; it drives delphi-3bda over ssh.
- nightly / System CI: the nightly test job (`uv run system_ci` of the systems_test repository) that installs the newest
  tron deb on delphi-3bda and runs functional, perf, MMLU Pro and soak phases. The perf phase is what we repeat.
- systems_test harness: the checkout ~/workspace/ai-runs/systems_test (origin/main 14f0ce4 since 2026-10-08). Its
  scripts/perf.py holds the 14 perf configs; testlib/tps.py runs the users; posadm/platformd provision the engines.
- tron: the inference program; rinzler: its production server binary (/opt/positron/bin/rinzler); deb: the Debian
  package of tron; platformd 0.11: the service that starts the rinzler engines (named entries default-0 .. default-3).
- PR 4424: the "VNNI K in place" pull request of tron (branch jhan-amx-vnniK). AMX and VNNI are CPU instruction sets;
  TRON_AMX_DISPATCH and TRON_K_VNNI are the build switches that compile the AMX kernels and the VNNI K layout.
- base arm: the nightly deb 2026.10.08-be0d5565 (tron main be0d5565b3), saved as nightly.deb. target arm: the PR 4424
  deb built by build-target.sh. "arm" and "binary" mean the same package in the reports.
- restore target: whatever deb is installed when the campaign starts (tonight's nightly installs a newer one); it is
  saved as restore.deb and reinstalled at the end.
- USE_HW_ATTN: an environment variable of rinzler. Unset (the nightly as shipped) = attention runs on the FPGA cards.
  USE_HW_ATTN=0 = software attention on the CPU. The campaign sets it through /opt/positron/user/config.env (14 bytes
  = `USE_HW_ATTN=0`, 0 bytes = unset); engines read the file at start only.
- full pass: the harness's own 14 perf configs with config.env empty, tag `<arm>-pass<k>`.
- sw8k cell: ingested-qwen-3-4b-instruct-2507-tp2, 8 users, prompt length 8192 tokens, 1536 generated tokens, ShareGPT
  prompts, with USE_HW_ATTN=0; tag `<arm>-sw8k-pass<k>`.
- cell: one config, identified as `<model>@<users>u-p<prompt_length>` (the harness NAMES repeat: llama-8b at 8u/1024
  and at 32u/4096 share the name llama_3_1_8b_instruct_good_tp2; the 70b tp2 8u and 4u rows share theirs).
- TPS: generated tokens per second per user; TTFT: time to first token in ms. A round = one request per user; the
  harness runs 10 rounds per config.
- paired t: the t statistic of the per-round differences target minus base (round means), pooled over the pass pairs.
- VmRSS, VmHWM, HugetlbPages: lines of /proc/PID/status. VmRSS = resident memory now; VmHWM = the peak of VmRSS since
  the process started; HugetlbPages = memory mapped from 1 GiB hugepages (the weights and the K/V arena).
- CI lease: /run/lock/systems-test-ci.lease on delphi-3bda; "busy" while the nightly holds the machine.
- Bill's marker: the file /bill-has-instance-0,2 on delphi-3bda; present = Bill may use the first half of the machine.
  The campaign takes it (bill-share.sh take, refused while Bill is active) and releases it at the end.
- campaign flock: /var/tmp/jhan/3bda-campaign.lock, held for the whole run so two of our campaigns never overlap.
- pre-check marker: /var/tmp/jhan/pr4424ci-precheck.running on delphi-3bda, held by the correctness pre-check of the same
  window (exec/merge4737-20261008/precheck.sh: host suite, token-identity smokes, runtron perf cells). campaign.sh waits
  after the CI lease until the marker is gone (an ssh failure means wait and retry).
- NFS attribute cache: delphi-3bda and claude-box share the home directory over NFS; a file edited on one host can be
  read stale on the other for about a minute. launch.sh compares md5 sums on both hosts before starting.

## How to run

1. Build the target deb ON delphi-3bda (about 30-40 min; pinned to socket 1, our half of the machine). COMMIT is the
   PR 4424 head to test (it must be in the NFS repo ~/workspace/tron; the script fetches origin when it is not):

       ssh delphi-3bda bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/build-target.sh <COMMIT>

   Output: /var/tmp/jhan/pr4424ci-20261009/{target.deb, rinzler.target, manifest.json, build.status (= ok), make-deb.log}.
   Do not run it while the nightly perf phase runs (it would disturb the nightly's numbers) and not while another
   build of ours runs on delphi-3bda (at 23:34 UTC on 2026-10-08 a `cmake --preset native` build of another session
   was running there; preflight prints such processes under "other campaigns of ours").

2. Start the campaign from claude-box. It sleeps until NOT_BEFORE, then waits in this order: the CI lease free, the
   pre-check marker absent, no runtron or campaign.sh peer on the DUT, the campaign flock, Bill's marker. The pre-check
   marker is the file /var/tmp/jhan/pr4424ci-precheck.running on delphi-3bda: the correctness pre-check chain
   (exec/merge4737-20261008/precheck.sh: host test suite plus runtron token-identity smokes) runs in the same
   whole-machine window before our passes and holds that file while it runs; it brings production serving back up when
   it ends. campaign.sh polls the file every 2 min (an ssh failure means "retry", never "absent"); DEADLINE_START
   applies to this wait as to every other.

       bash ~/workspace/intel-AMX/exec/pr4424ci-20261009/launch.sh

   launch.sh validates (syntax, compile, NFS identity of the files, target build ok, saved base deb version, platformd
   0.11, no local harness changes, the check mode newer than the driver, no peer processes, knob sanity) and prints the
   pid and the log path exec/logs/pr4424ci-20261009.log.

3. Watch: `cat exec/results/pr4424ci-20261009/.status` (one line, the current step) and the log. Per tag the results are
   in exec/results/pr4424ci-20261009/<tag>/{perf.json, driver.log, summary.txt, talos.json}.

4. At the end the campaign restores production (config.env cleared first, restore.deb reinstalled, engines down and up,
   marker released, flock released), writes outcome.txt and a .done / .done-with-failures / .done-aborted marker, and
   runs summarize.py into summary.md and summary.json. Re-run the summary by hand, with the nightly's own numbers:

       cd ~/workspace/ai-runs/systems_test && .venv/bin/python ~/workspace/intel-AMX/exec/pr4424ci-20261009/summarize.py \
           --nightly-log <gh run view --log of the 2026-10-09 nightly> --nightly-date 2026-10-09

## Timeline and deadlines (UTC, env knobs with their defaults)

| knob | default | meaning |
|---|---|---|
| NOT_BEFORE | 2026-10-09T13:00:00Z | sleep until here before the first lease check (the nightly's lease clears about 13:20) |
| DEADLINE_START | 2026-10-09T19:00:00Z | the first pass must have started by here, else abort (marker and flock given back) |
| PASS_DEADLINE | 2026-10-09T23:30:00Z | no further full pass starts after here (sw8k cells may still start) |
| DRIVER_END_BY | 2026-10-10T02:05:00Z | hard end: every driver run is cut here; the restore takes up to 16 min; ci-runner-stop timer 02:45 |
| DRIVER_TIMEOUT | 9000 s | per full pass (the 2026-09-18 12-config pass took 104 min; 14 configs are estimated at 2 h) |
| SW8K_TIMEOUT | 1800 s | per sw8k cell (about 8 min measured in the q4b campaigns) |
| PASSES | base target target base | arm order; each arm pass = full pass then sw8k cell |
| PASS_TAGS | (empty) | resume: run only these tags, e.g. `target-pass2 target-sw8k-pass2 base-pass2 base-sw8k-pass2` |
| RESUME_OVERWRITE | 0 | 1 = redo a tag whose perf.json exists |
| HANDOFF | up | up = production engines brought up at the end; down = left down |
| AMX_PROBE | 1 | 20 s EXE.AMX_BUSY sample before the llama-8b and qwen-3-4b tp2 benchmarks (informational, before the measured rounds) |
| FULL_CONFIGS | (empty) | empty = the harness's own list; a configs json replaces it (nightly14.json is the dumped list) |
| HF_OFFLINE | 1 | the driver loads tokenizers from the local cache only (all 15 cells checked 2026-10-08) |
| NO_WAIT | 0 | 1 = skip the lease wait (tests only) |
| EXPECTED_BASE / EXPECTED_BASE_SHA | 2026.10.08-be0d5565 / aebe9855... | the base arm's version and rinzler sha |

A full arm pass is estimated at 2 h (14 configs about 105-120 min, the sw8k cell about 8 min, two engine restarts).
Four arm passes are about 8 h: from a 13:20 start the last pass ends about 21:30, inside the deadlines above.

## What happens per tag

1. ensure_state: the package step when the arm changes (dut.sh ensure-base or ensure-target; apt never restarts the
   engines), then config.env for the attention mode (hwattn-clear for a full pass, hwattn-off for the sw8k cell), then
   an engine restart through platformd (serving-down after a 1 min idle check, serving-up), then verify-env (every
   rinzler pid's environment must match: 0 or exactly 1 line USE_HW_ATTN=0). Attention changes are lazy: after a sw8k
   cell config.env stays at 14 bytes until the next tag needs the other mode (or the restore clears it); every pass
   boundary costs one restart instead of two.
2. run_pass: the driver st_ci_perf.py runs the harness's test_performance against the proxy with the same client code
   as the nightly. It checks the CI lease before every provisioning and every cell (stop with rc 9 if busy), that every
   engine pid maps the installed binary (rc 7), and the USE_HW_ATTN state (rc 8). After every provisioning and after
   every benchmark it runs `dut.sh memsnap` and keeps the result in the per-config raw record (mem_after_provision,
   mem_after_benchmark).
3. On a driver failure (rc not 0, 9, 124) the engines are restarted and the run repeated once; cells that failed in
   both runs are known systematic failures and are not repeated again.

## Memory measurement

The driver, not campaign.sh, takes the snapshots: `dut.sh memsnap` prints one JSON line with, per running rinzler pid,
VmRSS, VmHWM, HugetlbPages, VmSize, VmPeak, RssAnon, RssFile, RssShmem (sudo -n cat /proc/PID/status; the units run as
positron) and the host's MemTotal, MemFree, MemAvailable, Committed_AS, HugePages_Total, HugePages_Free, Cached, Shmem
from /proc/meminfo, plus sums over the pids. The driver calls it over ssh, because only the driver knows the config
boundaries (campaign.sh sees one driver run per pass). summarize.py prints per cell the mean over passes of the sum over
engines of VmHWM and of VmRSS (MiB) for base and target and the delta. VmHWM is a per-process peak: platformd starts a
new rinzler process per provisioning, so the peak belongs to the current model, except for two consecutive configs of
the same model (70b tp2 8u then 4u), where the engines are kept and the 4u peak includes the 8u run.

## Files

| file | runs on | what it does |
|---|---|---|
| build-target.sh COMMIT | delphi-3bda | detached worktree /var/tmp/jhan/tron-pr4424ci at COMMIT; local branch jhan-pr4424ci-target for the deb version marker; adds `"TRON_K_VNNI": "ON"` after `"TRON_AMX_DISPATCH": "ON"` in the deb preset (one local commit, never pushed); checks the merged issue-4500 fix is in kv_cache.hpp; `make deb` outside nix (uv 0.9.5, ghcup, 48 jobs on socket 1); package checks (TRON_AMX_DISABLE literal >= 1, AMX tile instructions >= 50, vnni strings); writes target.deb, rinzler.target, manifest.json, build.status |
| dut.sh | delphi-3bda (over ssh) | installed, preflight, ensure-target, ensure-base VERSION SHA [FILE], save-base-deb VERSION [FILE], hwattn-off, hwattn-clear, verify-env (VERIFY_HWATTN=set or unset), memsnap, lease-free, serving-down (IDLE_MIN), serving-up |
| st_ci_perf.py + talos_stub/talos.py | claude-box | the driver: runs scripts/perf.py test_performance with the harness provisioning; records per-request TPS and TTFT, engine counters, layout snapshots, memory snapshots; the talos stub keeps the harness's reporting calls local (nothing reaches the CI database) |
| configs.py | claude-box | writes sw8k.json (the extra cell) and nightly14.json (the harness list, a record only) |
| campaign.sh | claude-box (detached) | the campaign: waits, locks, marker, preflight, restore.deb, passes, restore, summary |
| launch.sh | claude-box | validates and starts campaign.sh with setsid + nohup |
| summarize.py | claude-box | the tables: full passes, the sw8k cell, optional fidelity against the nightly log (nightly_to_arm.py); writes summary.json |
| nightly_to_arm.py | claude-box | copied from exec/ci-mimic-20260918: turns a nightly run log into the driver's record shape |

Results: exec/results/pr4424ci-20261009/ (per tag perf.json, driver.log, summary.txt, talos.json; preflight.txt,
base-identity.txt, configs-used*.json, outcome.txt, status-history.log, summary.md, summary.json, check-mode/).

## Stop, recovery, resume

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

## Validation record (2026-10-08, before any pass)

Harness update: ~/workspace/ai-runs/systems_test moved from e4727d5 (2026-09-21) to origin/main 14f0ce4 by
`git merge --ff-only`. The one local change (testlib/prompt.py, the short-ShareGPT workaround of 2026-09-19) is kept in
`stash@{0}` "pr4424ci-20261009: prompt.py short-ShareGPT workaround ..." and not applied: upstream replaced it with
PromptGenerator.prepare (eligible conversations). pyproject.toml changed upstream (new mcc_workload package and
package data; uv.lock unchanged), so `uv sync --frozen` ran: it rebuilt only the systems-test package itself.
Harness unit tests: `uv run --frozen pytest tests -q -x` = 2006 passed, 0 failed, 3 warnings, 51 s.

Driver port (st_ci_perf.py from exec/q4b-fpga-20260921): the hooked harness functions kept their signatures
(test_performance, benchmark_tps, Andoria.provision_model, BenchmarkResult fields). One hook changed: the provisioning
retry reset now also clears `dut._provisioned_result` (new field; the "already provisioned" branch dereferences it).
New: cell ids (model@users-pLEN) next to the repeating harness names, CI_MIMIC_CONFIGS_JSON="" = the harness list, the
memsnap hook, an extra CHECK line.

Offline prompt check (no DUT): every tokenizer of the 14 harness configs and of the sw8k cell loads from the local HF
cache, and PromptGenerator.prepare finds eligible ShareGPT conversations for every cell (1320 of 1320 at prompt 1024,
332 at 4096, 163 at 8192 for 80 requests). The Muse-Glimmer-30B tokenizer (meta-models/Muse-Glimmer-30B) was fetched
into the cache on 2026-10-08; before that HF_HUB_OFFLINE=1 would have failed that config in both arms.

Shell and python checks: `bash -n` on build-target.sh, dut.sh, campaign.sh, launch.sh (shellcheck is not installed on
claude-box or delphi-3bda); `python -m py_compile` on st_ci_perf.py, summarize.py, configs.py, nightly_to_arm.py,
talos_stub/talos.py; the preset edit of build-target.sh dry-run on a copy of the PR branch's CMakePresets.json gives
exactly one added line in the deb preset; summarize.py checked on synthetic results (a +5 % cell resolves, a 0 % cell
does not); dut.sh memsnap, installed, lease-free and preflight run read-only on delphi-3bda.

CHECK mode of the driver (CI_MIMIC_CHECK=1, read-only against the DUT, 2026-10-08 23:34 UTC, rc 0; the whole
driver.log, 10 lines, long lines cut):

```
[08/Oct/2026 23:33:57 UTC] INFO [ci_mimic.main:408] CI_MIMIC_CONFIGS_JSON empty: the harness's own perf config list (14 entries)
[08/Oct/2026 23:33:57 UTC] INFO [ci_mimic.main:415] arm=check-mode configs=['llama-3.2-3b-instruct-fast-tp2@32u-p200', 'llama-3.1-8b-instruct-good-tp2@8u-p1024', 'llama-3.1-8b-instruct-good-tp2@32u-p4096', 'llama-3.3-70b-instruct-good-tp2@8u-p1024', 'llama-3.3-70b-instruct-good-tp2@4u-p1024', 'llama-3.3-70b-instruct-good-tp4@4u-p1024', 'mixtral-8x7b-instruct-v0.1-tp2@8u-p1024', 'qwen-2.5-32b-it-fast-tp2@8u-p1024', 'ingested-qwen-3-4b-instruct-2507-tp2@8u-p1024', 'ingested-qwen-3-4b-instruct-2507-tp4@8u-p1024', 'gemma-2-9b-it-fast-tp2@8u-p1024', 'ingested-gpt-oss-120b-tp4@8u-p1024', 'ingested-gemma-4-31b-it-tp2@8u-p1024', 'ingested-meta-models--Muse-Glimmer-30B-tp4@8u-p1024']
[08/Oct/2026 23:33:59 UTC] INFO [ci_mimic.main:457] DUT versions: {'Meta-Package': 'not installed', 'Tron (package)': 'v2026.10.08-be0d5565', 'Platformd': 'v0.11.0+sst.88b2d3da', 'Service': 'not installed', 'Tronpost': 'not installed'}
[08/Oct/2026 23:34:03 UTC] INFO [ci_mimic.main:460] client path timing: {'n': 20, 'namelookup_ms_median': 1.17, 'connect_ms_median': 1.429, 'total_ms_median': 2.075, 'total_ms_max': 17.394}
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:467] CHECK ok: 53 supported models, capabilities=['base'], layout snapshot 3468 bytes
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:470] CHECK configs not in supported list: []
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:473] CHECK engine counters rc=0 prompts_total={0: 0, 1: 0, 2: None, 3: None}; binary check ok=True bad=[] want16=aebe98551e873219
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:476] CHECK caddy health events in the last hour: 0
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:478] CHECK USE_HW_ATTN=0 per engine pid: ok=False counts={2978224: 0, 2978233: 0}; FUSE limits: {0: {'max_prompt_tokens': 131072, 'max_total_tokens': 131072}, 1: {'max_prompt_tokens': 131072, 'max_total_tokens': 131072}, 2: {...None}, 3: {...None}}
[08/Oct/2026 23:34:04 UTC] INFO [ci_mimic.main:480] CHECK memsnap: pids=2 sum VmRSS=5872 MiB sum VmHWM=129274 MiB sum Hugetlb=524288 MiB; host MemAvailable=915834 MiB MemFree=114587 MiB HugePages_Free=0 Committed_AS=621816 MiB
```

"ok=False counts={...: 0}" is the CPU-attention reading of the check (every pid should carry USE_HW_ATTN=0 once); with
config.env at 0 bytes the count 0 per pid is the correct as-shipped state, which the full passes require
(CI_MIMIC_REQUIRE_HWATTN_UNSET=1). The machine at check time: 2 tp4 engines (the soak layout), no lease file, Bill's
marker present, config.env 0 bytes, no restore.deb yet, target build not built yet (build.status missing).

## Caveats

- The deb version of the target carries the branch name (2026.10.0x-<sha>-jhan-pr4424ci-target): the worktree is
  created detached at COMMIT and then put on a local branch, so the preflight's "no jhan in the installed version" rule
  can tell the target from a nightly. The preflight also compares the installed rinzler's sha with rinzler.target.
- AMX_PROBE=1 sends 4 short streaming requests for 20 s after provisioning llama-8b and qwen-3-4b tp2, before the
  measured rounds (as the 2026-09-18 ci-mimic campaign did). Set AMX_PROBE=0 for a run with no extra traffic at all.
- The talos stub must be first on PYTHONPATH whenever scripts.perf is imported (configs.py does this): importing the
  real talos package registers an "Untitled Session" in the CI results database. One such session was created by
  mistake on 2026-10-08 16:14 UTC (session 012d733e-c36e-11f1-9160-7dc18ea6a739) during the harness import check.
- summarize.py's paired t pools both pass pairs (n = 20 rounds) but keeps the 9-degree-of-freedom threshold 2.26, which
  is conservative (the 18-df 5 % point is 2.10).
