# Saturday plan (2026-09-19): qwen3-4b tp2, AMX gain with software attention forced on both arms, whole delphi-3bda

Handoff for the executing agent. Written 2026-09-19 18:5x UTC by the session that ran the llama-3.1-8b campaign of the
same day (status/Saturday-plan.md, results in status/Saturday-llama-3.1-8b.html). jhan's order: "similar to how
llama-3.1-8b is tested", model qwen3-4b tp2, USE_HW_ATTN=0 on both arms, PROMPT lengths 1.5k to 8k (jhan, 2026-09-19:
"I meant prompt length, not generate length"), the CI's generation length 1536 for every cell, 2 users per engine,
report to status/Saturday-qwen3-4b.html.

## Short version

One campaign measures, with the nightly's own client (the CI harness) against rinzler engines in the exact nightly layout,
how much the AMX attention kernel speeds up qwen3-4b tp2 when both arms run software (CPU) attention, from prompt 1024 to
prompt 8192 at the nightly's load of 2 users per engine. Arms: the nightly deb (no AMX code) against the canonical-AMX deb,
both with USE_HW_ATTN=0, 3 interleaved passes of 9 cells, about 4.1 h (est.). Every cell generates 1536 tokens per
request (the CI's generate_length); only the prompt length varies. The agent runs the whole campaign without
jhan; section 2a lists its standing decisions and the one point (Bill active) that needs him.

## Two corrections to the order, decided here (jhan can override before launch)

1. The nightly's qwen3-4b tp2 PROMPT is 1024 tokens, not 1.5k. The perf config
   ingested_qwen_3_4b_instruct_2507_tp2 has prompt_length 1024 and generate_length 1536 [systems_test scripts/perf.py:139-150
   at fc27f07, which is upstream main today]. jhan's list (1.5k, 2k, ... 8k) names PROMPT lengths (his clarification of
   2026-09-19). The grid below keeps the requested prompt-1536 cell AND adds prompt 1024 as the true nightly reference
   cell: 9 cells instead of 8. Every cell generates 1536 tokens per request, the CI's generate_length; it is never varied.
2. The absolute TPS of this campaign will be far below the nightly's number for this model. The nightly runs qwen3-4b
   with FPGA attention (about 186 TPS, canon-ci run of 2026-09-18). With USE_HW_ATTN=0 the same load ran at 141 TPS
   without AMX and 152 TPS with AMX in the p0perf-20260913 campaign (our half, prompt 1024). The report must say this in
   its Short version so nobody reads the level as a regression.

## Words used here

- tron = the inference program under test; rinzler = its production server; one running rinzler = one engine.
- qwen3-4b = the ingested model ingested-qwen-3-4b-instruct-2507-tp2 (Qwen/Qwen3-4B-Instruct-2507, GPTQ, 36 layers,
  8 KV heads of 128, so 144 KiB of KV cache per token in bf16). tp2 = two FPGA cards per engine.
- nightly = the systems_test CI run on delphi-3bda at 03:30 UTC; the perf phase = its decode-speed benchmark
  (scripts/perf.py). nightly layout = 4 tp2 engines provisioned by platformd behind the Caddy proxy on port 80; the
  8 users of the config spread 2 per engine.
- CI harness = the nightly's client code (systems_test scripts/perf.py, testlib/tps.py), run from the checkout
  /home/jhan/workspace/ai-runs/systems_test with its .venv through exec/l8b-levers-20260919/st_ci_perf.py (records every
  sample, replaces the Talos results database with a stub, probes AMX use, snapshots engine pids and counters).
- AMX = Intel Advanced Matrix Extensions. The kernel (PR #3879, merged) is compiled only when the CMake option
  TRON_AMX_DISPATCH is ON. The nightly deb does not set it, so the nightly's rinzler has no AMX code.
- software attention = attention computed on the CPU (AVX or AMX); hardware attention = attention computed on the FPGA.
  USE_HW_ATTN is the environment variable that selects it: unset = hardware attention for ingested models (qwen3-4b is
  one) from query position 127 on; USE_HW_ATTN=0 = software attention for every model [tron h/tron/models/hw_attn_config.hpp:12-14].
  Software attention is where the AMX kernel runs, so this campaign measures the kernel's own effect. With FPGA attention
  the kernel only touches the CPU share (positions 0 to 126), and the nightly's number moves +0.1 % (canon-ci 2026-09-18).
- KV tokens per engine step = users per engine x context per user; the attention work of one decode step. The harness
  measures TPS in the window of generated tokens 896 to 1024, so the context per user is about prompt + overhead + 960.
- pass = one run of all 9 cells on one arm; arm = one installed package (base or canon); cell = one config.
- config.env = /opt/positron/user/config.env, an environment file the rinzler unit reads last (EnvironmentFile=-, so its
  keys win over the unit's own Environment= lines and over /etc/rinzler/instance-N.env) [systemctl cat rinzler@.service
  on 3bda, line 44]. Empty (0 bytes) in production. It is the sanctioned place to set USE_HW_ATTN=0 for every engine.

## 1. Arms and their identity

| arm | package | AMX code | attention | how to install |
| base | nightly deb tron 2026.09.18-3faba6d0, saved copy /var/tmp/jhan/canon-ci-20260918/nightly.deb (137,845,288 bytes) | none | software (USE_HW_ATTN=0), AVX path | dut.sh ensure-base 2026.09.18-3faba6d0 SHA |
| canon | tron_2026.09.18-0594dc54-jhan-ci-canon_amd64.deb = /var/tmp/jhan/canon-ci-20260918/target.deb | yes | software (USE_HW_ATTN=0), AMX path | dut.sh ensure-canon |

Both debs come from main 3faba6d0fd; canon adds ONLY the two-line CMakePresets.json change 6f37cd2ed9 (TRON_AMX_DISPATCH=ON
in the deb preset). Same source, same attention mode, so the difference is the AMX kernel alone. Identity checks per pass
(unchanged from the llama campaign): dut.sh ensure-* verifies the installed version and the sha256 of
/opt/positron/bin/rinzler; the after-provision snapshot must show every engine pid on the installed sha; the per-cell
AMX-busy probe (perf stat EXE.AMX_BUSY on the engine pids) must read 0 cycles on base and billions on canon. Reference:
under FPGA attention the canon qwen tp2 cell showed 10.5 G cycles (CPU share only, canon-ci); with software attention
expect more, and at least 10 G per cell.

REQUIRED after every package switch: restart the engines (dut.sh serving-down, then the pass's provisioning starts them).
apt never restarts engines, and the legacy platformd path never restarts a same-model engine, so without the restart a
pass would run the previous arm's deleted binary (verified 2026-09-19 on the llama campaign).

Base arm against restore target: if the campaign runs after another nightly (section 2), the installed package at
preflight is a newer nightly deb. The base ARM stays 2026.09.18-3faba6d0 (same source as canon). The RESTORE target is
the package found installed at preflight: save it with dut.sh save-base-deb VERSION into a separate file (restore.deb),
and reinstall that one at the end. Tonight both are the same deb.

## 2. Machine, time window, permissions

- Whole machine: jhan's order of 2026-09-19 ("we can use whole 3bda") applies again. Bill's marker /bill-has-instance-0,2
  is taken with `bash ~/workspace/intel-AMX/exec/bill-share.sh take` on 3bda; release it at the end.
- Peer campaign: another session ran issue-4500 block m6 on our half (exec/logs/issue4500-m6.log; finished 18:40 UTC,
  .done marker present). It held the marker and the campaign flock; confirm both are released. Gate on its marker file
  exec/logs/issue4500-m6.done AND `pgrep -u jhan -f '[r]inzler --model|[r]untron[. ]|[i]ssue4500'` empty, then take the marker.
- CI lease: /run/lock/systems-test-ci.lease is busy while the nightly runs (started 03:30 UTC; clears about 13:20 UTC).
  Busy only if the file exists AND state == "busy" AND now < expires_at_epoch. dut.sh lease-free waits for it.
- Campaign flock /var/tmp/jhan/3bda-campaign.lock: the driver holds it for the whole run.
- Hard limits: pre-CI hold 01:40 UTC; ci-runner-stop brings production inference up 02:45 UTC; the nightly apt reinstall
  runs about 03:39 UTC. DRIVER_END_BY = 01:00 UTC (the restore needs up to 16 min).
- Two windows. Tonight: the campaign needs about 4.1 h (est.) plus margin, so the first pass must start by 20:30 UTC
  (DEADLINE_START); PASS_DEADLINE 23:45 UTC. Otherwise Sunday 2026-09-20 after the nightly clears (about 13:20 UTC), with
  DEADLINE_START 19:30 UTC, PASS_DEADLINE 23:45 UTC, DRIVER_END_BY 2026-09-21T01:00Z, and the restore-target rule of section 1.
- During the CI window only light work (reading, editing scripts, the offline prompt check of section 3).
- End state: the restore-target deb installed, production engines up (HANDOFF=up) with config.env back to 0 bytes BEFORE
  they start (so production runs FPGA attention again), Bill's marker released, the flock released.

## 2a. Running without jhan: what the agent decides alone, and the one point that needs him

Everything below is pre-decided; the agent does not ask jhan during the run. The campaign script runs detached on the
client host (setsid nohup, as launch.sh does), so the agent's own session may end while the passes run.

- Bill's marker: `bill-share.sh take` refuses while Bill is active (rc 2). If it refuses, wait and retry every 30 min until
  DEADLINE_START; if it still refuses, stop and report. Only jhan can decide to interrupt Bill. This is the one point that
  needs him.
- Latest start: DEADLINE_START of section 2. If the lease, the flock, the peer campaign or the marker still blocks at that
  time, stop and report (tonight: report and re-plan for Sunday).
- The check cell (section 6, 8 users at prompt 8192 on canon) fails (engine error, timeout, no output, server-counted prompt
  tokens far from 8192): drop the prompt-8192 cell and retry the check at 7168. If 7168 also fails, drop it too and run the
  remaining cells. Never add cells. Report every dropped cell.
- The offline prompt check (section 3) fails for some seeds at a prompt length: fix the concatenation until it passes; if it
  cannot pass, drop those cells as above. Do not run a cell whose prompts the check has not passed.
- A pass fails (driver rc not 0, or a deleted-binary stop): restart the engines and repeat that pass once; if it fails again,
  continue with the next pass and report the gap. Analysis uses only cells with all 3 passes on both arms; others are
  reported as incomplete.
- Every engine must carry USE_HW_ATTN=0 in its environment after each provisioning (section 4, step 3). If any engine lacks
  it, stop the pass, restart the engines once, re-check; if it is still missing, stop the campaign safely and report.
- The decision rule (section 7), the grid (section 5) and the arm identities (section 1) are not changed for any reason
  other than dropping failed cells.
- Do not file anything in the systems_test repository, do not post to Slack or GitHub, do not touch the nightly's checkout
  or Bill's half beyond the marker. The output is the results directory and the report (section 9); jhan decides filing.
- If anything on the machine looks wrong (lease busy mid-run, platformd down, unexpected installed package, engines
  without USE_HW_ATTN=0), stop safely: clear config.env, restore the target deb, HANDOFF=up, release Bill's marker and
  the flock, confirm config.env is 0 bytes, then report.

## 3. Step 0, the prompt source (offline, first)

The concatenation change to PromptGenerator.generate is already in place, uncommitted, in
/home/jhan/workspace/ai-runs/systems_test/testlib/prompt.py (patch exec/l8b-levers-20260919/prompt.py.patch). It copies the
stored conversation list and appends following conversations until the count reaches prompt_length. Nothing to change.

Two model-specific facts, both fidelity-neutral (the nightly runs the same code for this model):
- The harness counts tokens with the llama header string `<|start_header_id|>role<|end_header_id|>` and drops the first
  token of each part [testlib/prompt.py prune_convo]. The qwen tokenizer adds no BOS token, so the first real token is
  dropped, and the server applies the qwen chat template. The server-counted prompt tokens (usage prompt_tokens) will
  therefore differ from prompt_length by a per-part overhead that is not llama's 34 tokens. Record it per cell and report
  it as the measured overhead; it enters the KV arithmetic of section 5.
- The harness tokenizer is Qwen/Qwen3-4B-Instruct-2507 [testlib/hf_models.py:40, the "-tp2" suffix is stripped at
  hf_models.py:107-108]; it is in the local HF cache (~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507), so
  HF_HUB_OFFLINE=1 works.

Run a copy of exec/l8b-levers-20260919/prompt_check.py with TOKENIZER = "Qwen/Qwen3-4B-Instruct-2507" and LENGTHS = the
9 prompt lengths of section 5, seeds 0 to 319, in the .venv with HF_HUB_OFFLINE=1. Required: 0 exceptions, identical
prompt hashes on two runs, stored conversation lists unchanged. The re-encoded length column is informational for this
tokenizer (see the BOS note). Record the output in the results directory.

No truncation trap for this model: both ingested weight directories on 3bda
(/opt/positron/weights_cache/cached/positron-ai/Qwen--Qwen3-4B-Instruct-2507-ingest-best-gptq and -v1) have
tokenizer.json truncation = null and max_position_embeddings 262144 (checked 2026-09-19 18:4x UTC). The llama campaign
lost its 7168 and 8192 cells to a tokenizer truncation block at 4096; that block does not exist here. Still confirm at the
check cell that the server counts about 8192 prompt tokens.

## 4. Driver changes (copy exec/l8b-levers-20260919/ to exec/q4b-swattn-20260919/; never edit a running script)

1. configs.py: MODEL = "ingested-qwen-3-4b-instruct-2507-tp2"; GRID = section 5; names
   ingested_qwen_3_4b_instruct_2507_tp2_8u_p<len>; write configs-full.json, configs-no8192.json, configs-no7168.json,
   check-8u-p8192.json, check-8u-p7168.json.
2. dut.sh, three new actions:
   - hwattn-off: `printf 'USE_HW_ATTN=0\n' | sudo -n tee /opt/positron/user/config.env`, then print its bytes (must be 14).
   - hwattn-clear: `sudo -n truncate -s 0 /opt/positron/user/config.env`, then print its bytes (must be 0).
   - verify-env: for every running rinzler pid, `sudo -n tr '\0' '\n' </proc/PID/environ | grep -c '^USE_HW_ATTN=0$'`
     must print 1; print pid, model and the result; rc 1 if any engine lacks it.
   Preflight keeps "config.env bytes (must be 0)" as the START condition. The instance-N.env check stays (platformd
   writes those files; they must carry no AMX or HW_ATTN keys).
3. campaign.sh: NAME=q4b-swattn-20260919; EXPECTED_BASE stays 2026.09.18-3faba6d0 (the base ARM); add RESTORE_VERSION =
   the version found installed at preflight (saved as restore.deb, section 1). Sequence per campaign: preflight,
   save-base-deb (both files), hwattn-off, check cell, passes `base canon base canon base canon` (each: ensure-*,
   serving-down, provisioning by the harness, verify-env, run the cells), then restore: hwattn-clear FIRST, then
   ensure-restore-target, serving-down, serving-up, marker release, flock release, final `stat -c %s config.env` = 0.
   Every abort path (abort_early, restore_and_release) calls hwattn-clear before any serving-up. DRIVER_TIMEOUT 3600 s per
   pass (est. 33 min); CHECK_TIMEOUT 1200 s; deadlines per section 2.
4. st_ci_perf.py: no model change needed. CI_MIMIC_AMX_MODELS already lists ingested-qwen-3-4b-instruct-2507-tp2
   [st_ci_perf.py:305], so the AMX-busy probe runs. The engine-count check expects 8 // tp = 4 engines [st_ci_perf.py:396].
   Add to every raw record the server-counted prompt tokens (already recorded as prompt_tokens) and, at the check cell, the
   FUSE config values max_prompt_tokens and max_total_tokens (/var/run/rinzler/N/rinzler/config/) for this model.
5. launch.sh: md5 checks for every copied file, the prompt.py cmp against the saved patch, py_compile, bash -n, the peer
   gate of section 2, TAKE_MARKER=1.
6. analyze.py: per-cell paired t as before; replace the llama verdict blocks (pair_16k, triple_8k, expected_*) with the
   section-7 blocks: band_p1024, curve (monotone test), and the crossing (first prompt length whose gain is resolved
   and at least +10 %).
7. gen_report.py: model name, cell names, the two charts of section 9, the corrections of this plan's second section.

## 5. Cells (one pass = these 9, in this order; all ingested-qwen-3-4b-instruct-2507-tp2, nominal_users 8 = 2 users per
## engine, generate_length 1536, start_capture 896, end_capture 1024, prompt_mode "sharegpt", user_sets [], shared_prompt_length 0)

| name suffix | prompt_length | KV tokens per engine step (K, est. with overhead 0) | purpose |
| _8u_p1024 | 1024 | 4.0 | the nightly's own config (prompt 1024); reference cell, band of section 7 |
| _8u_p1536 | 1536 | 5.0 | jhan's "1.5k" prompt cell |
| _8u_p2048 | 2048 | 6.0 | context lever |
| _8u_p3000 | 3000 | 7.9 | context lever (same length as the llama grid, for the cross-model chart) |
| _8u_p4096 | 4096 | 10.1 | context lever |
| _8u_p5120 | 5120 | 12.2 | context lever |
| _8u_p6144 | 6144 | 14.2 | context lever |
| _8u_p7168 | 7168 | 16.3 | context lever |
| _8u_p8192 | 8192 | 18.3 | context lever, longest cell |

All lengths in the table are PROMPT lengths (harness prompt_length). The generation length is 1536 tokens in every
cell, the nightly's generate_length; TPS is measured between generated tokens 896 and 1024 as in the nightly.
"5k, 6k, 7k, 8k" are written as 5120, 6144, 7168, 8192 (multiples of the 64-token KV page). Names must differ per prompt
length because the harness keys its summary by name and user count only [scripts/perf.py:348, 434]. Same model throughout a
pass, so platformd provisions once per pass. KV arithmetic: 2 x (prompt + overhead + 960); the overhead is measured per
cell (section 3) and the report recomputes the column with it. Memory per engine at the longest cell: 2 users x about
9.8K tokens x 144 KiB = about 2.7 GiB of the 128 GiB of hugepages per engine, so no capacity risk.

## 6. Before the first pass

1. Preflight via dut.sh preflight (lease, platformd, config.env 0 bytes, instance env clean, canon build status ok,
   installed version). Record the installed version as RESTORE_VERSION and save that deb.
2. Arm identity check of section 1 on the canon deb (objdump tile-instruction count about 86; strings TRON_AMX_DISABLE 1).
3. hwattn-off, then the check cell: one canon run of _8u_p8192 with CHECK_TIMEOUT 1200 s. Required: rc 0, verify-env
   passes on all 4 engines, server-counted prompt tokens about 8192 (within 8192 to 8400), AMX-busy above 10 G cycles,
   FUSE max_prompt_tokens and max_total_tokens recorded and above 9800. Its duration is the upper bound for the section-8
   estimates. On failure apply the drop rule of section 2a.

## 7. Decision rule (pre-registered; do not change it after seeing data)

- Per cell, canon against base: paired t over the 3 passes (pass r of one arm pairs with pass r of the other); resolved at
  |t| >= 4.303 (the 95 % two-sided limit of Student's t with 2 degrees of freedom) and |change| >= 1 %.
- Band at prompt 1024 (fidelity check against the one earlier measurement of this exact load): the p0perf-20260913 campaign
  measured 140.61 against 152.46 TPS, +8.4 %, with the CI harness at 2 users per engine, USE_HW_ATTN=0, kill switch
  against AMX on, same binary, on our half of the machine. Pre-registered band: +5.4 % to +11.4 % (+8.4 plus or minus
  3 points). Inside = the whole-machine, two-deb setup reproduces the earlier result. Outside = report it; the two
  campaigns differ in binary (one build with a kill switch there, two debs here) and in machine half.
- Curve: the gain against prompt length is expected to rise and then flatten (hypothesis from data F: runtron qwen3-4b,
  8 users on one engine, +19.0 % at prompt 2048 and +17.5 % at 8192; 1 user +3.8 % at 2048 and +15.2 % at 8192). Test:
  the gain of every resolved cell is at least the gain of the resolved cell before it minus 2 points ("monotone within
  2 points"). PASS = the context lever holds for this model. FAIL = name the cells that break it; no interpretation beyond
  that in the report.
- Crossing: the shortest prompt length whose gain is resolved and at least +10 % (the size of gain the CI team can
  see above run-to-run noise of about 0.7 % CV). Reported as a number, for jhan's decision on a CI shape. No
  recommendation is made in this campaign's report; that is the page's job.
- TTFT (time to first token) per cell, both arms, reported alongside; no rule on it.

## 8. Duration (est.) and monitoring

Anchors: the llama 2-users-per-engine cells measured 124, 137, 155 and 188 s at prompt 1024, 2048, 3000 and 4096 (mean of
6 runs each; summary.json wall_s_mean), a straight line of about 103 s + 0.021 s per prompt token. qwen3-4b tp2 decodes at
about the same TPS under software attention (141 against llama's 140 at prompt 1024), so the same line is used:
1024 124 s, 1536 135, 2048 146, 3000 165, 4096 188, 5120 210, 6144 231, 7168 252, 8192 273 s (est.), 29 min per pass, plus
about 4 min of probes and snapshots = 33 min (est.). Six passes 3.3 h, six package switches about 6 min each (apt swap,
settle, engine stop and start with the idle test, provisioning), the check cell about 6 min: about 4.1 h (est.). Prefill of
an 8192-token prompt at 2 users is untimed for this model; the llama 4096 cell had TTFT 3.6 s, so expect about 8 to 10 s
(est.), which the harness tolerates.

Monitoring: read the .status file and driver.log over ssh with a periodic grep (a Monitor tail -F on the NFS copy of a
file written on 3bda delivers nothing; a trailing cut block-buffers). Milestones: check cell done, each pass done, restore
done, .done marker.

## 9. Outputs

- Results under exec/results/q4b-swattn-20260919/<arm>-pass<k>/ (perf.json, talos.json, driver.log, summary.txt), the
  offline prompt check, the check cell, the identity checks per pass, verify-env output per pass, the AMX-busy probes,
  per-engine request counts (Caddy spread, FUSE prompts_total), client CPU pressure, anomalous-sample counts, cell
  durations, server-counted prompt tokens per cell, FUSE max_prompt_tokens and max_total_tokens.
- summary.json / summary.txt per cell: base TPS, canon TPS, gain %, paired t, resolved yes/no, TTFT both arms, slowest
  sample, p05, duration, measured overhead; the band, curve and crossing verdicts of section 7.
- A report (HTML, light theme, ASCII only, plain English, Short version first) in status/Saturday-qwen3-4b.html with:
  (1) a dumbbell chart, one row per prompt length, base and canon TPS as the two dots, the gain written on each row;
  (2) a line chart of gain against prompt length with the llama 2-users-per-engine curve (status/Saturday-llama-3.1-8b.html
  data: +0.2, +1.6, +7.3, +8.2 % at 1024, 2048, 3000, 4096) and the data-F runtron points drawn as context in grey;
  (3) the record table; (4) the second section of this plan (why the level is below the nightly's 186 TPS); (5) a
  glossary; (6) deviations from the plan, if any. Render check with cairosvg before delivery; publish as a private artifact.
- Optional, NOT part of this campaign: feeding the results into exec/canon-ci-20260918/gen_ci_shapes.py as a new source
  tag. jhan decides.

## 10. Traps (from the two campaigns of 2026-09-18/19)

- config.env is read only at engine start. Setting it without restarting the engines changes nothing; clearing it without
  restarting leaves production engines on software attention. Always: write or clear, then serving-down, then start.
- The legacy platformd path never restarts a same-model engine; restart after every package switch (dut.sh serving-down).
- NFS attribute cache: compare md5 on both hosts before launching; never edit a script while it runs.
- Production engines left running hold all 512 hugepages until the driver's serving-down step.
- The flock can be held by another session's campaign per runtron run; gate on the peer's .done marker and pgrep, not on
  `flock -n` alone; anchor pgrep patterns so the checker does not match itself.
- 3bda runs perf_event_paranoid 4; the probe uses sudo -n perf stat (the sysctl lift 4 -> 0 -> 4 has jhan's standing
  approval; log the set and restore lines). perf -x CSV column 4 is run time, not the count.
- Bash: `rc=$?` after `if cmd; then ...; fi` reads the if-statement's status; capture rc first. A retry helper that prints to
  stdout pollutes `$(...)` captures; print to stderr and validate captured values.
- The rinzler journal has no per-request line; per-engine request counts come from /var/run/rinzler/N/rinzler/stats/prompts_total.
- After a failed cell the harness's ProcessPool workers block forever; the driver exits with os._exit after killing
  multiprocessing.active_children() (already in st_ci_perf.py).

## 11. Sources

- Precedent campaign (same driver, whole machine, nightly layout, same two debs): exec/l8b-levers-20260919/, plan
  status/Saturday-plan.md, report status/Saturday-llama-3.1-8b.html, results exec/results/l8b-levers-20260919/.
- Only earlier measurement of this exact load with software attention: exec/p0perf-20260913/, report
  PR3879/new-PRs/PR1/Sunday-CI-layout-results.html (CI layout tp2, off 140.61 / on 152.46 / fpga 192.11 TPS).
- Nightly-level qwen tp2 numbers with FPGA attention: exec/canon-ci-20260918/, report
  PR3879/new-PRs/PR1/canonical-AMX-CI-run-report.html (186.13 base / 186.25 canon TPS, AMX probe 10.5 G cycles).
- Data F (runtron qwen3-4b prompt series): exec/canon-ci-20260918/gen_ci_shapes.py lines 159-161 and 276-292.
- USE_HW_ATTN rule: tron h/tron/models/hw_attn_config.hpp (worktree ~/workspace/ai-runs/tron-main-ro).
- Nightly perf config: systems_test scripts/perf.py:139-150 (fc27f07 = upstream main on 2026-09-19).
