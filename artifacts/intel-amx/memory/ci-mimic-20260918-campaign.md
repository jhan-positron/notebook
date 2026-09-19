---
name: ci-mimic-20260918-campaign
description: "2026-09-18 campaign (jhan, ultracode): run the nightly System CI perf phase by hand on the WHOLE of delphi-3bda after the nightly ends, base = today's nightly deb (no AMX) vs target = PR #4424 + deb preset AMX+VNNI-K ON, same harness/platformd/Caddy path, USE_HW_ATTN untouched; report Friday-morning-CI-run-report.html; state, design, blockers, reference numbers"
metadata: 
  node_type: memory
  type: project
  originSessionId: cfafa211-4409-4b46-a9f5-c701b81efeba
  modified: 2026-09-18T04:57:01.158Z
---

Request (jhan 2026-09-18 01:0x UTC = Thu 18:0x PDT): schedule a run after the CI window: same CI tests,
identical nightly config (whole 3bda, no USE_HW_ATTN=0), base = AMX not in product, target = AMX + VNNI-K
enabled; CI harness through rinzler + Caddy (not runtron) with our rinzler built from the updated
CMakePresets.json; nightly load shape; the 12 perf.py configs; expect base TPS/TTFT == nightly; confirm
achievability first; report Friday-morning-CI-run-report.html. Bill pinged; marker removed 01:10:49 UTC
(exec/bill-share.sh take; release after the campaign).

Design (exec/ci-mimic-20260918/; no README: the classifier refused it, see the dut.sh bullet):
- Client = st_ci_perf.py in ~/workspace/ai-runs/systems_test/.venv (uv sync from the CI lockfile, Python
  3.12.7) on claude-agentsrv; calls scripts.perf.test_performance (the nightly's own loop: legacy posadm
  provisioning per config, 8//tp engines, 10 rounds, Caddy :80). posadm.RemoteContext patched to ssh as
  jhan (key) with login() no-op (never touches the positron account); talos = recording stub. Snapshots
  /etc/rinzler/instance-*.env + /proc/<pid>/exe after each provisioning; optional EXE.AMX_BUSY probe.
  CHECK mode ran clean 01:29 UTC (versions, 52 supported models, capabilities base).
- Target deb: wait-and-build.sh (launched 01:19 UTC on 3bda) waits for publish-deb 2026-09-18 (started
  01:34:32 UTC from main 3faba6d0fd) then build-target.sh: worktree /var/tmp/jhan/tron-ci-mimic =
  origin/jhan-amx-vnniK (30c4ac82cb) merged with that main (merge-tree clean) + preset AMX+VNNI ON, make
  deb outside nix (PATH /tools/uv/0.9.5 + ghcup, NPROC_BUILD=48, socket 1), output
  /var/tmp/jhan/ci-mimic-20260918/{target.deb,manifest.json,rinzler.target,build.status}.
  BUILT 02:12 UTC (status ok): tron_2026.09.18-29a8a547-jhan-ci-mimic-target_amd64.deb, main 3faba6d0fd
  (= the 09-18 nightly deb's commit), merge 0f086eecc2, head 29a8a54740; packaged rinzler: TRON_AMX_DISABLE
  literal 1, 126 AMX tile insns (AMX-only build had 86), 3 vnni strings; sha256 e08da458...ea17.
- dut.sh / campaign.sh / launch.sh: first BLOCKED by the auto-mode classifier ("Modify Shared Resources";
  a README with their text was refused as "Auto-Mode Bypass"). jhan approved 2026-09-18 ~04:50 UTC
  (swap+restore+marker yes, PASSES=1, AMX probe keep, smoke "your call" -> skipped: the nightly was already
  running) and added permission rules (Write exec/ci-mimic-20260918/*, Bash ssh delphi-3bda); scripts
  written 04:55 UTC, preflight clean (installed tron 2026.09.18-3faba6d0 = target's main; unit pristine;
  marker absent; nightly perf phase running, lease busy run 35303980268). LAUNCHED 04:57 UTC with PASSES=1:
  campaign.sh waits for the lease
  (600 s grace), holds the campaign flock via ssh, preflight, base arm, ensure-target (apt remove +
  apt install ./target.deb), target arm, restore (apt install tron=<nightly version>), marker release.

Facts (research workflow wf_fb10498d-fbf, 8 readers + synth + 3 verifiers):
- Nightly perf phase = 78-79 min for the 12 configs incl. per-config provisioning (09-16/17 logs);
  order = perf.py list; 70b tp2 @4u reuses @8u engines. Nightly timeline: apt 03:39, functional
  03:40-04:05, perf 04:05-05:24, MMLU -10:12, soak -13:16, end ~13:18 UTC.
- 13-night reference (Slack, 09-05..09-17): TPS CV <= 0.73% for 10/12 configs; noisy: qwen-3-4b tp4
  145.2 +/- 5.1, gpt-oss tp4 104.7 +/- 3.0; TTFT stable except 70b tp2 @4u bimodal (3418-4418 ms).
  Reference logs in scratchpad nightly-35178969541.log / nightly-reference-final.json (session cfafa211).
- apt/dpkg never restart engines (postinst comment); platformd restarts units on config PATCH (env
  change) -> the first provisioning of each arm re-execs the new binary; verify /proc/<pid>/exe not
  "(deleted)". Legacy posadm mode because platformd 0.10.7 < 0.11.0. Caddy least_conn.
- Client host: container 192.168.2.136 same /22 as system-ci-runner 192.168.2.75; RTT equal (0.13 ms);
  HTTP to proxy 1.4-2.1 ms; TTFT effect <= 1-2 ms (visible only on llama-3b, 56 +/- 0.3 ms).
- Hand edit --num-expert-replicas 750 in the unit file is reverted by the nightly's reinstall; preflight
  counts it. dpkg: target version (date-sha8-branch) sorts ABOVE the nightly -> restore needs
  --allow-downgrades tron=<version>.

**Why:** reviewers of PR #4424 and Rhys/Hannah need CI-identical numbers, and the nightly cannot show AMX
until the deb preset change lands.
**How to apply:** after jhan launches: watch exec/results/ci-mimic-20260918/.status; compare base with the
09-18 nightly run log (gh run list -R positron-ai/systems_test) + 13-night band; write the report with a
generator forked from exec/wedperf-20260916/gen_report.py. Related: [[ci-enable-20260917-campaign]],
[[nightly-vs-ours-tps-context]], [[p0perf-20260913-campaign]], [[wedperf-20260916-campaign]],
[[3bda-shared-with-bill]], [[rinzler-unit-expert-replicas-750]].

Verifier deltas (wf_fb10498d-fbf, 3 lenses, 2026-09-18 02:0x UTC) folded into the driver / to keep in mind:
- perf.py: a provisioning failure of config 1 raises UnboundLocalError (use_case unset) -> whole phase aborts;
  later pre-benchmark failures append a zero row with the PREVIOUS use_case -> key rows on context.model +
  nominal_users. post_provision_health_check only WARNS -> driver raises on wrong engine count (retry path).
- PerfResult keeps only ttft_mean -> driver wraps scripts.perf.benchmark_tps to keep per-request ttfts/tpss/
  prompt/cached tokens (record["raw"]). Rich "Done (TTFT=..)" rows DO render into the log file.
- Statistics for the report: paired-by-round differences (n=10 round means; round 3 of llama-8b is slow on
  both nights = prompt-driven), not per-sample Welch t; 24 tests at 2 sd give ~1 false flag -> flag |z|>3;
  70b tp2 @8u sd 0.01 is Slack 2-decimal quantization; llama-3b TTFT reference is int-truncated (56 vs 57).
- Client path: each request does a DNS lookup (container 0.8 ms median vs 0.3 ms on systemd-resolved) ->
  record curl time_namelookup per arm; only llama-3b TTFT (56 +/- 0.3 ms) can see it.
- Pre-arm checks added to snapshots: Intel Speed Select CLOS (intel-speed-select-state verify, read-only),
  hugepages per NUMA node (256 x 1 GiB each), /opt/positron/user/config.env must be 0 bytes.
- platformd restarts ALL units on every PATCH (not only on env change) -> first provisioning re-execs the
  new binary. 02:45 UTC ci-runner-stop timer -> POST /api/inference/up -> StartUnit rinzler@0 from the
  edited unit (bare --num-expert-replicas 750 + 4 models -> exits) -> healed by the nightly's 03:40 restart.
- Real talos with LOCAL=1 still writes OpenSearch logs + a Mongo testrun row -> stub FIRST on PYTHONPATH always.

Report tooling (2026-09-18 05:0x UTC, ready before the data): exec/ci-mimic-20260918/nightly_to_arm.py turns a
nightly run log into the driver's record shape (rounds grouped by the "Running averages" lines; matches the
readers' numbers); gen_report.py builds status/Friday-morning-CI-run-report.html (inline SVG, light theme,
ASCII only, dataviz palette: base blue #2a78d6, target orange #eb6834, nightly gray, band #e1e0d9; charts:
fidelity % with 2-sd band, effect % with paired-round 95% CI, TTFT effect, absolute small multiples).
Pre-registered rules in the generator: fidelity flag = |z|>3 AND |delta|>=1%; effect flag = paired |t|>=2.26
AND |delta|>=1% AND |delta| > the config's 13-night 2-sd band (TTFT: also >= 1 ms). CALIBRATION: stand-in
run with nightly 09-16 as "base" and 09-17 as "target" (same package) -> 0 resolved effects, all 12 configs
inside the band (qwen-3-4b tp4 differs +4.7% between those two nights, t>2.26 -> the band criterion is needed).
Reference data preserved in exec/results/ci-mimic-20260918/reference/ (both nightly logs, nightly_stats.json,
arm jsons). Cron wake-ups in this session: 06:27 / 07:52 / 09:17 / 10:33 PDT 09-18 (campaign checks + report).
Report path: /home/jhan/workspace/intel-AMX/VNNIed-K-in-place/status/Friday-morning-CI-run-report.html.

2026-09-18 13:19:59 UTC: first launch ABORTED right after the lease cleared: `${SMOKE:+-smoke}` expands for SMOKE=0
too (bash :+ tests set-and-non-null, and "0" is non-null), so preflight went to preflight-smoke.txt and the
"target build ok" grep on preflight.txt failed (exit 5). TRAP for future scripts: never use ${VAR:+x} with a 0/1
flag; test [ "$VAR" = 1 ]. Fixed and relaunched 13:2x UTC (preflight of 13:19:55 was clean: tron 2026.09.18-3faba6d0,
2 tp4 engines from the soak, unit pristine, marker absent, SST verified). Nightly run 35303980268 completed 13:19:05 UTC.
13:35 UTC relaunch: both arms crashed in 5 s: asyncssh "Task ... attached to a different loop". Cause: the driver
called dut.get_versions() in its own event loop (opened dut.conn there); scripts.perf.test_performance creates
ITS OWN asyncio loop and reuses dut.conn -> RuntimeError on the first posadm ssh command -> 3 provisioning
retries -> perf.py's UnboundLocalError (use_case). CHECK mode never showed it (single loop). Fix: versions via a
subprocess ssh (posadm info); the harness must be the first to touch dut.conn. The campaign's failure path
worked as designed (target installed, failed, base restored, marker re-created); marker taken again 13:38 UTC.
TRAP 2: campaign.sh's remote flock holder (`ssh ... flock -c "echo held; exec sleep 50000"`) survives the local
ssh kill -> next launch sees "flock HELD"; fixed by printing the remote pid and killing it in cleanup.
SMOKE 13:38-13:41 UTC (fixed driver, base deb, qwen-3-4b tp2 @8u through platformd+Caddy from claude-agentsrv):
provisioning 47 s, 4 engines, 4 Caddy upstreams healthy; TPS 186.02 (sd 7.21, min 174.89; 13-night 185.67 +/- 0.74),
TTFT 549 ms (nightly 507-526; 13-night 509.5 +/- 7.2 -> +8 %, open: client-side?), AMX-busy 0 cycles (control),
harness minutes 1.69, wall 2.87 incl. probe. Results exec/results/ci-mimic-20260918/smoke/. Relaunch 13:42 UTC.
CHECK 2 (14:52 UTC): base arm 6/12 configs done, ~35 min behind the nightly's pace. TPS fidelity vs the same-day
nightly (2026.09.18-3faba6d0, run 35303980268): llama-3b -1.6 %, llama-8b -0.9 %, 70b tp2 @8u 0.0, @4u +0.2,
70b tp4 -0.7, mixtral -0.1 % (all inside or at the edge of the 13-night band). TTFT: llama-3b 119 vs 56 ms
(+111 %) = CLIENT-SIDE artifact; llama-8b -8 %, others within 2 %. Cause: the client host (claude-agentsrv) is
CPU-saturated by OTHER containers: %Cpu 95 us / 0 idle, PSI cpu some=93 %, procs_running 114, load 126-147 on
32 CPUs, swap full; our driver + 8 workers use ~20 %. Effects: per-round wall 42 s vs 7 s (llama-3b), client
stalls lower some samples (llama-3b round 7 mean 166 vs ~197; llama-8b min 108.6 vs 136.3; 70b tp4 min 23.0 vs
29.6) and inflate short TTFTs. TPS MEANS are robust (<= 1.6 %). renice cannot help (contention is across
cgroups). Decision: let base+target finish under the same client conditions (fair pairing), report the caveat;
offer a repeat with the client on the DUT (pinned spare cores) if TTFT fidelity matters. Driver now records
/proc/pressure/cpu per snapshot (target arm onward). Nightly 09-18 vs 09-17: qwen-3-4b tp4 148.8 (153.1),
gpt-oss 101.2 (106.9) = the known noisy configs.
BASE ARM DONE 15:27 UTC (12/12, harness 103.8 min vs nightly 79): TPS vs same-day nightly within -1.6..+0.8 % on 11
configs, gpt-oss +5.3 % (z13 +0.6, noisy config); TTFT within 2.3 % except llama-3b +111 % (client), llama-8b -8 %,
qwen-3-4b tp2 +5.4 %; AMX probes 0 (control). TARGET ARM CRASHED 15:29 UTC: NameError 're' (my 14:55 edit used
re.match without importing re; the target process loaded the edited file) -> campaign restored base + released
marker. Fixed (import re), marker re-taken 16:03, relaunched 16:0x UTC with ARMS=target (new campaign.sh knob).
TRAP: never edit the driver mid-campaign without py_compile + an import check; the next arm runs the edited file.

DONE 2026-09-18 17:57:58 UTC: target arm 12/12 (16:14-17:57), nightly deb 2026.09.18-3faba6d0 restored, Bill marker
re-created, flock free. Report written 18:2x UTC: VNNIed-K-in-place/status/Friday-morning-CI-run-report.html (gen_report.py
+ caveats.html + notes3.html + --thr-note in exec/results/ci-mimic-20260918/; copy report-v1.html). RESULTS:
- Fidelity (base vs same-day nightly, TPS means): within -1.6..+0.8 % on 11 configs, gpt-oss +5.3 % (z13 +0.6); 12/12 inside
  the 13-night band by the rule (|z|>3 AND >=1 % off both references). TTFT within 2.3 % on 9; llama-3b 119 vs 56 ms (client),
  llama-8b -8 %, qwen-3-4b tp2 +5.4 %.
- Effect (target = PR #4424 + AMX + VNNI-K preset vs base): resolved qwen-3-4b tp4 -11.0 % (t -10.2), qwen-3-4b tp2 -5.0 %
  (t -7.5), llama-70b tp2 @4u +1.1 % (t +10), llama-3b -3.7 % (t -2.5, client-affected, not trusted). llama-8b only +0.8 %
  (t +3.0) although AMX ran (probe 30.1 G cycles vs 0 base): 2 users per engine in the nightly layout, not 8 on one engine.
  qwen-3-4b tp2 probe 13.7 G cycles (FPGA attention, CPU share). TTFT: llama-8b -5.3 %, qwen-3-4b tp2 -9.4 %, mixtral -1.8 %.
- Thresholds (CURRENT static goals): target FAILs qwen-3-4b tp4 on the mean (133.44 < 135) and llama-3b mean (187.3 < 191,
  client-affected); base slowest-user FAILs on llama-3b/llama-8b/70b tp4 = client stalls.
- Client host claude-agentsrv was CPU-saturated by other containers (PSI 93-99 %, load 41-147) -> 5x longer rounds, arms 104 min
  vs nightly 79, inflated short TTFTs, a few stalled samples; TPS means robust. Next time: run the client from an idle host
  (or the DUT's spare cores) and never edit the driver mid-campaign.
- Verification workflow wf_90f0ffcb-de4 (6 lenses) launched 18:3x UTC.
RESIDUAL STATE TRAP (fixed 18:38 UTC): after the campaign's restore (apt remove + install of the nightly deb) the 4 engines of the last
target config kept running the TARGET binary (deleted inode, exe sha 3ee9c8f0) because apt never restarts engines; anyone using the
machine would have hit AMX+VNNI-K engines until platformd re-provisioned. Fixed with POST /api/inference/down then /up (cfgdut recipe)
-> engines restarted on the on-disk nightly binary (exe sha 27e6883c). Next time: campaign.sh restore step must end with down/up (or a
config PATCH) and verify /proc/<pid>/exe. Report v1 verification (wf_90f0ffcb-de4, 6 lenses): tables numerically clean (0 mismatches
in 108 fidelity cells + effect table); fixed in v2: chart-1 band now centred at (mean13-nightly)/nightly; caveats rewritten (PSI/load
per arm and config: base load 4.5-147, target PSI 96-99 % for configs 1-5 then 0-45 %; rounds up to 11x; base llama-3b round-7 stall
= the whole -1.6 % gap; 09-18 nightly failed 2 thresholds and PASSED qwen-2.5 for the first time); notes3 rewritten (70b @4u fast
requests 6/5/12 of 40; wedperf tp2 mismatch; llama-8b TTFT attribution not isolated; 2-users-per-engine = hypothesis); glossary
expanded; "same package" calibration wording fixed. v2 verification wf_13c788b7-73a running.
v2 verification (wf_13c788b7-73a): chart-1 band centre correct; fixed in v3/v4: band half-width now 2 sd / nightly (axis unit);
threshold note = THREE verdict flips vs the 09-18 nightly (qwen-3-4b tp4 mean, llama-3b mean [client], qwen-2.5-32b slowest
32.53 [historic]); "1 min per config overhead" claim was wrong -> our pre-round path adds 0.7 min over 7 configs, rounds
themselves 34.3 vs 28.5 min (20 % longer at equal TPS even at PSI 0-4 %); "nearly idle client for configs 6-12" -> 5 of 7
(qwen-3-4b tp2/tp4 at PSI 27-48 %); TTFT flags "cannot be attributed" (not "do not show"); gemma-4 is ingested but CPU
attention; arm/config/CI-runner/clos/HBM/asyncio defined; ", so"/semicolon joins split. Report v4 = final.
FOLLOW-UP 2026-09-18 (jhan asked whether AMX ran for llama-8b and whether to set USE_HW_ATTN=0 for it):
- AMX ran on the benchmark engines: probe 30,132,776,756 EXE.AMX_BUSY cycles (20 s, 4 streaming users) on pids
  2535365/2535374/2535384/2535393 = the engines that loaded llama-3.1-8b at 16:28 UTC with Version
  2026.09.18-29a8a547-jhan-ci-mimic-target (sudo journalctl -u 'rinzler@*'); no engine restart 16:29-16:32:55; perf test
  completed 16:32:53. Base probe = 0. Instance env: TRON_AMX_DISABLE absent, USE_HW_ATTN absent, TRON_USE_SPECULATION=0.
- llama-3.1-8b ALREADY runs CPU attention in the nightly: journal line "HW attention disabled for model
  'llama-3.1-8b-instruct-good-tp2': default off for this model". Rule (h/tron/models/hw_attn_config.hpp): USE_HW_ATTN unset =
  enabled only for INGESTED models, disabled for hand-written plugins (llama, mixtral, qwen-2.5, gemma-2); USE_HW_ATTN=0 disables
  all; USE_HW_ATTN=N>0 enables all eligible (N = engagement point). => USE_HW_ATTN=0 is a NO-OP for llama-8b; the +0.8 % (paired
  t 2.96, 95 % CI +/-0.62 %) IS the whole AMX effect at 2 users per 28-CPU engine.
- Why small: same kernel, same 28-CPU placement (runtron 09-16 used "instance 2,4"): 1 user/128 tok 204.6 -> 204.6 (0 %),
  8 users/256 tok 110.1 -> 112.3 (+2.0 %), 8 users/1536 tok 83.3 -> 97.5 (+17 %). Gain tracks attention work per step
  (users x context); nightly = 2 users/engine -> below the +2.0 % cell. qwen-3-4b in the same per-engine load (p0perf-20260913
  CI cells, 2 users/engine, CPU attention): 140.6 -> 152.6 (+8.4 %) because its dense part is half the size.
- Levers that could show AMX in the nightly llama-8b number are CI-config levers (users per engine, context), not USE_HW_ATTN.
  Untested: llama-8b CI-harness cells on our half, AMX on vs TRON_AMX_DISABLE=1, at 2 and 4 users per engine.

FOLLOW-UP campaign l8bload-20260918 (same day, 19:55-21:08 UTC) tested the 2-users-per-engine hypothesis: AMX gain +0.2 % at 2, +3.9 % at 4, +12.9 % at 8 users per engine -> confirmed; see [[l8bload-20260918-campaign]].
