# Saturday plan (2026-09-19): T0, the llama-8b levers campaign on the whole of delphi-3bda

Handoff for the executing agent. Written 2026-09-19 by the review session of PR3879/new-PRs/PR1/CI-AMX-test-shapes.html
(v2). jhan's orders in that session: "do not restrict your plan about machine, we can use whole 3bda" and "rinzler needs to
be the one built with CMakePresets.json otherwise AMX would not be compiled in".

## Short version

One campaign measures, with the nightly's own client (the CI harness) against rinzler engines in the exact nightly layout,
how the AMX attention kernel's gain on llama-3.1-8b depends on users per engine (1, 2, 4, 8) and on prompt length
(1024 to 8192), nightly deb against canonical-AMX deb, 3 interleaved passes, 10 configs per pass, about 5.3 h (est.). Two arms only, no kill-switch arm (jhan, 2026-09-19).
Its 32-user prompt-1024 cells give the reference values for the recommended CI config (the page's T1), and its
2-users-per-engine long-prompt cells measure a long-prompt CI shape directly (the page's T2). The pre-registered decision
rule (section 7) says which shape the page recommends afterwards; jhan decides filing. The agent runs the whole campaign
without jhan; section 2a lists its standing decisions and the one point (Bill active) that needs him.

## Words used here

- tron = the inference program under test; rinzler = its production server; one running rinzler = one engine.
- nightly = the systems_test CI run on delphi-3bda at 03:30 UTC; the perf phase = its decode-speed benchmark (scripts/perf.py).
- CI harness = the nightly's client code (systems_test scripts/perf.py, testlib/tps.py). Here it runs from the checkout
  /home/jhan/workspace/ai-runs/systems_test with its .venv, through exec/canon-ci-20260918/st_ci_perf.py (a wrapper that
  records every sample and replaces the Talos results database with a stub).
- nightly layout = 4 tp2 engines (tp2 = two FPGA cards per engine) provisioned by platformd behind the Caddy proxy on port 80.
- AMX = Intel Advanced Matrix Extensions. The kernel (PR #3879, merged) is compiled only when the CMake option
  TRON_AMX_DISPATCH is ON. The nightly deb does not set it, so the nightly's rinzler has no AMX code.
- KV tokens per engine step = users per engine x context per user; the attention work of one decode step. The harness
  measures TPS in the window of generated tokens 896 to 1024, so the context per user is about prompt + 31 + 960 (31 =
  tokens the server counts around the prompt, from data A).
- pass = one run of all 10 configs on one arm; arm = one installed package (clean or canonical).
- lever = one of the two ways to raise attention work: more users per engine, or a longer prompt per user.

## 1. Arms and their identity (jhan's reminder applies here)

| arm | package | AMX code | how to install |
| clean | nightly deb tron 2026.09.18-3faba6d0 (installed on 3bda now; the driver saves a copy with dut.sh save-base-deb) | none | dut.sh ensure-base |
| canon | tron_2026.09.18-0594dc54-jhan-ci-canon_amd64.deb, /var/tmp/jhan/canon-ci-20260918/target.deb | yes | dut.sh ensure-canon |

The canon deb was built from main 3faba6d0fd plus ONLY the two-line CMakePresets.json change 6f37cd2ed9 (TRON_AMX_DISPATCH=ON
in the deb preset); PR #4424 is not in it. Its manifest (/var/tmp/jhan/canon-ci-20260918/manifest.json) records
amx_tile_insns 86 and TRON_AMX_DISABLE_literal 1 in the packaged rinzler, counted at build time. A rinzler built without that
preset change has no AMX code whatever its source commit. Per pass, dut.sh ensure-base / ensure-canon verify the installed
version and the sha256 of /opt/positron/bin/rinzler; the per-config AMX-busy probe then confirms which arm ran (0 cycles on
the clean arm, about 30 billion cycles at 2 users per engine on canon). Optional extra check on the installed binary (it is
stripped, so use objdump and strings, not nm):

    objdump -d /opt/positron/bin/rinzler | grep -cE 'tdpb|tileloadd|tilestored|ldtilecfg'   # canon: about 86; clean: 0
    strings /opt/positron/bin/rinzler | grep -c TRON_AMX_DISABLE                              # canon: 1; clean: 0
    dpkg-query -W tron                                                                        # the installed version

REQUIRED after every package switch: restart the engines (dut.sh serving-down, then the pass's provisioning starts them).
apt never restarts engines, and T0 provisions the same model in every pass, so without the restart a pass would run the
previous arm's deleted binary (the data-B 'before' snapshot shows exactly that after a switch). The driver must stop a pass
when an engine runs a deleted binary, and the after-provision snapshot must show every engine pid on the installed sha.


## 2. Machine, time window, permissions

- Whole machine: jhan's order of 2026-09-19. Bill's marker /bill-has-instance-0,2 must be taken with
  `bash ~/workspace/intel-AMX/exec/bill-share.sh take` on 3bda; launch.sh does this and refuses while Bill is active
  (rc 2). Release at the end (the campaign's restore step does it).
- CI lease: /run/lock/systems-test-ci.lease is busy while the nightly runs (started 03:30 UTC; clears about 13:20 UTC).
  Busy only if the file exists AND state == "busy" AND now < expires_at_epoch. The driver waits for it (dut.sh lease-free).
- Campaign flock /var/tmp/jhan/3bda-campaign.lock: the driver takes it for the whole run; check `flock -n ... true` and other
  sessions' exec/logs/*.status before launching.
- Hard limits: the pre-CI hold starts 01:40 UTC; the ci-runner-stop timer brings production inference up at 02:45 UTC;
  the nightly apt reinstall runs about 03:39 UTC. Set DEADLINE_START and DRIVER_END_BY in campaign.sh accordingly
  (about 12 h available from 13:20 UTC).
- During the CI window only light work (reading, editing scripts, the offline prompt check of section 3).
- At the end: restore the nightly deb, production engines up (HANDOFF=up), Bill's marker released, the flock released,
  /opt/positron/user/config.env back to 0 bytes.

## 2a. Running without jhan: what the agent decides alone, and the one point that needs him

Everything below is pre-decided; the agent does not ask jhan during the run. The campaign script runs detached on the client
host (setsid nohup, as launch.sh does), so the agent's own session may end while the passes run.

- Bill's marker: jhan's order of 2026-09-19 covers taking it. `bill-share.sh take` refuses while Bill is active (rc 2). If it
  refuses, wait and retry every 30 min until the latest start time below; if it still refuses, stop and report. Only jhan can
  decide to interrupt Bill. This is the one point that needs him.
- Latest start: the two-arm campaign needs about 5.3 h (est.) plus margin before the 01:40 UTC pre-CI hold, so do not start a
  pass after 19:30 UTC; set DEADLINE_START accordingly. If the lease or the flock is still busy at 19:30 UTC, stop and report.
- The hand check at 32 users and prompt 8192 fails (engine error, timeout, no output): drop the prompt-8192 cells and retry the
  check at prompt 7168. If 7168 also fails, drop the 7168 cells too (the 16K pair is then lost, say so in the report) and run
  the remaining configs. Never add configs.
- The offline prompt check (section 3) fails for some seeds at a prompt length: fix the concatenation until it passes; if it
  cannot pass for 8192, drop those cells as above. Do not run a cell whose prompts the check has not passed.
- A pass fails (driver rc not 0, or a deleted-binary stop): restart the engines and repeat that pass once; if it fails again,
  continue with the next pass and report the gap. Analysis uses only configs with all 3 passes on both arms; others are
  reported as incomplete.
- The decision rule (section 7), the config grid (section 5) and the arm identities (section 1) are not changed for any
  reason other than dropping failed cells.
- Do not file anything in the systems_test repository, do not post to Slack or GitHub, do not touch the nightly's checkout or
  Bill's half beyond the marker. The output is the results directory and the report (section 9); jhan decides filing.
- If anything on the machine looks wrong (lease busy mid-run, platformd down, unexpected installed package), stop safely:
  restore the nightly deb, HANDOFF=up, release Bill's marker and the flock, confirm config.env is 0 bytes, then report.

## 3. Step 0, the prompt source (do this first, offline, during the CI window)

The harness builds prompts from ShareGPT conversations and raises "Prompt length ... too short" when a conversation is
shorter than prompt_length (testlib/prompt.py prune_convo, lines 32-52). Of the 80 default seeds (seeds 0-79 = 10 rounds x
8 users), 39 fail at prompt 2048, 78 at 4096, 80 at 8192 (data P of the page). Change PromptGenerator.generate
(testlib/prompt.py lines 56-75) in /home/jhan/workspace/ai-runs/systems_test, the checkout the driver runs (the nightly
is not touched):

    base = list(self.convos[seed % len(self.convos)]['conversations'])     # COPY: today's code mutates the stored list
    k = 1
    while token_count(system_prompt + base) < prompt_length:                # same tokenizer call prune_convo uses
        base = base + list(self.convos[(seed + k) % len(self.convos)]['conversations'])
        k += 1
    convo = [system_prompt] + base
    prompt = self.prune_convo(convo, prompt_length)

The copy matters: generate() today inserts the system line into the stored list in place, and the workers of one round
share those lists, so concatenation without copies would make a seed's prompt depend on thread timing. Deterministic per
seed; prompts stay unique through the timestamp system line. At prompt 1024 the loop never runs (every conversation is at
least 1531 tokens), so the prompt-1024 cells stay identical to the nightly's.

Check offline before anything runs on 3bda: in the .venv with HF_HUB_OFFLINE=1 and the tokenizer of llama-3.1-8b good
(neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16, testlib/hf_models.py), call generate(prompt_length, seed) for
seeds 0 to 319 at prompt_length 1024, 2048, 3000, 4096, 7168, 8192 and confirm 0 exceptions, an encoded length of
exactly prompt_length each time, and the same token counts on two runs. Record the check output in the results directory.

## 4. Driver changes (copy exec/canon-ci-20260918/ to exec/l8b-levers-20260919/; never edit a running script)

Line-level details are in exec/canon-ci-20260918/T0-script-changes.md. In short:
1. st_ci_perf.py: CI_MIMIC_CONFIGS_JSON replaces perf_mod.configs with the dict list of section 5 (distinct names per prompt
   length); add prompt_length, name and wall time to every raw record; make the deleted-binary check (lines 262-264) stop
   the pass; count per-engine requests from each unit's journal before and after every config (the Caddy spread; nothing
   records it today). Keep CI_MIMIC_AMX_PROBE=1.
2. campaign.sh: NAME=l8b-levers-20260919; ARMS = "base canon base canon base canon"; per pass ensure-base or ensure-canon,
   then dut.sh serving-down (engine restart), then run_arm; DRIVER_TIMEOUT about 3600 s per pass; DEADLINE_START and
   DRIVER_END_BY per section 2; HANDOFF=up; the restore step verifies config.env is 0 bytes.
3. dut.sh: no change expected (ensure-base needs the saved nightly deb).
4. launch.sh: md5 checks for every copied file, canon build status ok, bill-share take, campaign.sh detached; log
   exec/logs/l8b-levers-20260919.log.


## 5. Configs (one pass = these 10, in this order; all llama-3.1-8b-instruct-good-tp2, generate_length 1536,
## start_capture 896, end_capture 1024, prompt_mode "sharegpt", user_sets [], shared_prompt_length 0)

| name | nominal_users | users per engine | prompt_length | KV tokens per engine step (K) | purpose |
| llama_3_1_8b_instruct_good_tp2_8u_p1024 | 8 | 2 | 1024 | 4.0 | today's nightly config (reference) |
| llama_3_1_8b_instruct_good_tp2_8u_p2048 | 8 | 2 | 2048 | 6.1 | context lever |
| llama_3_1_8b_instruct_good_tp2_8u_p3000 | 8 | 2 | 3000 | 8.0 | 8K triple, two minibatches |
| llama_3_1_8b_instruct_good_tp2_8u_p4096 | 8 | 2 | 4096 | 10.2 | context lever; long-prompt shape at today's load (T2) |
| llama_3_1_8b_instruct_good_tp2_8u_p7168 | 8 | 2 | 7168 | 16.3 | 16K pair partner of 32 x 1024 |
| llama_3_1_8b_instruct_good_tp2_8u_p8192 | 8 | 2 | 8192 | 18.4 | context lever (T2) |
| llama_3_1_8b_instruct_good_tp2_4u_p7168 | 4 | 1 | 7168 | 8.2 | 8K triple, one minibatch |
| llama_3_1_8b_instruct_good_tp2_16u_p1024 | 16 | 4 | 1024 | 8.1 | users lever; 8K triple |
| llama_3_1_8b_instruct_good_tp2_32u_p1024 | 32 | 8 | 1024 | 16.1 | users lever; the recommended shape (T1) |
| llama_3_1_8b_instruct_good_tp2_32u_p2048 | 32 | 8 | 2048 | 24.3 | context lever at 8 users per engine |

Names must differ per prompt length: the harness keys its summary by name and user count only (scripts/perf.py lines 348
and 434). Same model throughout a pass, so platformd provisions once per pass (testlib/inventory.py line 169). KV
arithmetic: users per engine x (prompt + 31 + 960); 31 = data B's recorded overhead at prompt 1024, assumed at every prompt
length (est.); for example 2 x 8159 = 16318 (16.3K) against 8 x 2015 = 16120 (16.1K).


## 6. Before the first pass

1. One hand-run canon cell at nominal_users 32 and prompt_length 8192 with a short timeout: no record shows the hand-written
   llama plugin above prompt 1024. It is heavier than every T0 cell: KV need 8 x 9728 tokens x 128 KiB = 9.5 GiB per engine
   (128 x 1 GiB hugepages per engine; the largest T0 cell, 32 users at prompt 2048, needs 3.5 GiB). Its duration is an upper
   bound for the long-prompt estimates of section 8.
2. Arm identity check of section 1 on the installed package.
3. Preflight via dut.sh preflight (lease, platformd, config.env bytes, canon build status ok, installed version).


## 7. Decision rule (pre-registered on the page; do not change it after seeing data)

- Per config, canon against clean: paired t over the 3 passes (pass r
  of one arm pairs with pass r of the other); resolved at |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2
  degrees of freedom) and |change| >= 1 %.
- Pair at 16K: gain(2 users x 7168) against gain(8 users x 1024). Within 3 percentage points = the two levers are one
  mechanism and a long-prompt shape is a peer recommendation. 2-user cell ahead by more than 3 points = context lever
  stronger, the long-prompt shape becomes the primary recommendation. 8-user cell ahead by more than 3 points = users lever
  stronger, the page stands.
- Triple at 8K: gain(1 user x 7168), gain(2 users x 3000), gain(4 users x 1024). Per minibatch their loads are 8.2K, 4.0K and
  4.0K (the 1-user step is one minibatch, the others two). The hiding hypothesis of the page's section 1.1 is SUPPORTED when
  the 1-user cell gains more than 3 points above both other cells and those two agree within 3 points. It is REJECTED when
  all three agree within 3 points. Any other pattern is recorded as undecided and named in the report. The nominal_users-4
  cell counts only if its per-engine request counts show 10 requests per engine; otherwise it is excluded from the triple.
- Expected: +0.2 % to +1.2 % at 2 users and prompt 1024 (data A, B); about +12.9 % at 8 users and prompt 1024 (data A;
  acceptance band 9.9 % to 15.9 % as the page's T1 pre-registered); a rising prompt axis at 2 users (hypothesis for llama
  from the qwen 1-user curve, data F).


## 8. Duration (est.) and monitoring

Per pass about 40 min of benchmark time: 2 users at 1024 / 2048 / 3000 / 4096 / 7168 / 8192 about 2.5, 3, 3.5, 4, 5.5,
6 min; 1 user at 7168 about 3; 4 users at 1024 about 2.5; 8 users at 1024 / 2048 about 4 and 6. Plus about 4 min of AMX-busy
probes and snapshots = 44 min per pass. Six passes 4.4 h, six package switches about 6 min each (apt swap 9 s, 20 s settle,
engine stop and start with the idle test, re-provisioning 1 to 2 min), plus the section-6 cell: about 5.3 h. Anchors: the prompt-1024 2-user config measured 2.52 min in data B (2.87 and 3.83 min in the two ci-mimic arms); data
A 4-user cell 2.41 min, 8-user cells 3.6 to 4.0 min; no long-prompt cell has been timed.
Monitoring: read the .status file and driver.log over ssh with a periodic grep (a Monitor tail -F on the NFS copy of a
file written on 3bda delivers nothing; a trailing cut block-buffers).


## 9. Outputs

- Results under exec/results/l8b-levers-20260919/<arm>-pass<k>/ (perf.json, talos.json, driver.log, summary.txt), the
  offline prompt check, the pre-flight cell, the identity checks per pass, the AMX-busy probes, per-engine request counts
  (Caddy spread) from the rinzler journals, client CPU pressure, anomalous-sample counts, cell durations.
- A summary table per config: clean TPS, canon TPS, gain %, paired t, resolved yes/no, TTFT, slowest sample, p05, duration;
  the 16K pair and the 8K triple verdicts by section 7.
- A report (HTML, light theme, plain English, Short version first) in status/Saturday-llama-3.1-8b.html, and the results fed into
  exec/canon-ci-20260918/gen_ci_shapes.py as a new source tag (H) so the page's section 4 and 5 can be re-ranked. The
  32-user prompt-1024 cells are the T1 reference values for the CI team's goals (mean TPS, slowest sample, p05).

## 10. Traps (from the memory notes of this project)

NFS attribute cache (compare md5 on both hosts before launching; never edit a script while it runs); production engines
left running after the nightly hold all 512 hugepages until the driver's serving-down step; config.env must be 0 bytes at
handoff; the flock can be held by another session's campaign (the guard alternates); 3bda runs perf_event_paranoid 4
(the probe uses sudo -n perf stat; the sysctl lift 4 -> 0 -> 4 has jhan's standing approval, log set and restore lines);
perf -x CSV column 4 is run time, not the count; pgrep -f patterns must be anchored so the checker does not match itself.

## 11. Sources

- Page: PR3879/new-PRs/PR1/CI-AMX-test-shapes.html (v2), generator exec/canon-ci-20260918/gen_ci_shapes.py, artifact
  https://claude.ai/artifact/TzLCwdhTW1pv6gm8S51RZT.
- Script-change note: exec/canon-ci-20260918/T0-script-changes.md.
- Precedent campaign (same driver, whole machine, nightly layout): exec/canon-ci-20260918/ and its report
  PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html; results exec/results/canon-ci-20260918/.
- Data A method (rinzler + harness, kill switch, our half): exec/l8bload-20260918/, VNNIed-K-in-place/status/llama8b-AMX-gain-vs-load.html.
