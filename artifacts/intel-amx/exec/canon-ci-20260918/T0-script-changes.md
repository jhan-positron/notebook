# T0: llama-8b levers campaign with the CI harness in the nightly layout - script changes (not yet made)

Words used here: T0 = test T0 of PR3879/new-PRs/PR1/CI-AMX-test-shapes.html (v2.2, 2026-09-19): the AMX gain on
llama-3.1-8b good tp2 against users per engine (1, 2, 4, 8) and prompt length (1024 to 8192), measured with the nightly's
own client (the CI harness, systems_test scripts/perf.py) against rinzler engines provisioned by platformd in the nightly
layout (4 tp2 engines behind Caddy), on the whole of delphi-3bda. Driver = the exec/canon-ci-20260918/ scripts (campaign.sh,
dut.sh, launch.sh, st_ci_perf.py, talos_stub) that ran data B. jhan's directions (2026-09-19): "do not restrict your plan
about machine, we can use whole 3bda"; "rinzler needs to be the one built with CMakePresets.json otherwise AMX would not
be compiled in". An earlier version of this note described a runtron design on our half; it is superseded.
The executing agent's handoff is CI-test/status/Saturday-plan.md; this note holds the line-level script changes.

## Arms
- clean = the nightly deb 2026.09.18-3faba6d0 (no AMX code). dut.sh ensure-base installs it (save-base-deb first).
- canon = tron_2026.09.18-0594dc54-jhan-ci-canon_amd64.deb, /var/tmp/jhan/canon-ci-20260918/target.deb. dut.sh ensure-canon
  installs it. Built from main 3faba6d0fd + ONLY the CMakePresets.json change 6f37cd2ed9 (TRON_AMX_DISPATCH=ON in the deb
  preset); manifest.json: amx_tile_insns 86, TRON_AMX_DISABLE_literal 1, pr4424_included false. ensure-* verify the
  installed version and the sha256 of /opt/positron/bin/rinzler; the per-config AMX-busy probe then shows which arm ran
  (0 cycles clean, about 30 billion at 2 users per engine canon).
Passes: 3 per arm, interleaved clean, canon, clean, canon, clean, canon. Two arms only, no kill-switch arm (jhan, 2026-09-19). One package switch per pass.

## Engine restart after every package switch (new, required)
apt never restarts engines (campaign.sh line 28). In data B every config changed the model, so platformd re-created the
engines and they picked up the new binary. T0 provisions the SAME model in every pass, so without a restart a pass can run
the previous arm's deleted binary (the canon perf.json 'before' snapshot shows four pids on a '(deleted)' exe after the
package switch). After ensure-base / ensure-canon call dut.sh serving-down (idle test, stop units, remove slice files), then
let the pass's provisioning start the engines. Make the deleted-binary check in st_ci_perf.py (lines 262-264, logs only
today) raise and stop the pass, and require the after-provision snapshot to show every engine pid on the installed rinzler
sha before the first config runs.

## Configs (perf.py dicts, model llama-3.1-8b-instruct-good-tp2, generate_length 1536, start_capture 896, end_capture 1024,
## prompt_mode "sharegpt", user_sets [], shared_prompt_length 0). Names MUST differ per prompt length: perf.py keys the
## Talos summary by f"{name}_tps @ {nominal_users}" (line 434) and the use_case string by model and users only (line 348).
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
(The "_8u_" part of the name is nominal_users 8, that is 2 users per engine.) Same model throughout a pass, so platformd
provisions once per pass (inventory.py line 169). KV arithmetic: users per engine x (prompt + 31 + 960); 31 = data B's
recorded overhead at prompt 1024 (1055 - 1024), assumed at every prompt length (est.).

## Change 1: st_ci_perf.py
- After the CI_MIMIC_MODELS block (lines 186-192): if CI_MIMIC_CONFIGS_JSON names a file, `perf_mod.configs =
  json.load(open(path))` (the dict list above) and skip the CI_MIMIC_MODELS filter. test_performance iterates over the
  module global.
- Raw record (lines 273-280): add config.prompt_length and config.name, and the wall time of each config (time.time()
  around orig_benchmark).
- Deleted-binary check (lines 262-264): raise instead of log.
- Per-engine request counts: before and after each config, count the request lines of each unit's journal
  (`journalctl -u rinzler@N --since <t0>` with the grep dut.sh serving-down uses) and store the four deltas in the record.
  snapshot_layout has no request counter today (it reads the Caddy upstream health gauge, env files, pids, hugepages).
- Keep CI_MIMIC_AMX_PROBE=1 (the probe list already contains llama-3.1-8b-instruct-good-tp2).

## Change 2: testlib/prompt.py in ~/workspace/ai-runs/systems_test (the checkout the driver runs; the nightly is not touched)
generate() (lines 56-75) today inserts the system line into the STORED conversation list in place (convo = self.convos[...]
['conversations']; convo.insert(0, system_prompt)), and the workers of one round share those lists. With concatenation a
worker would append a list another worker already mutated, so copy first:

    base = list(self.convos[seed % len(self.convos)]['conversations'])
    k = 1
    while token_count(system_prompt + base) < prompt_length:            # same tokenizer call prune_convo uses
        base = base + list(self.convos[(seed + k) % len(self.convos)]['conversations'])
        k += 1
    convo = [system_prompt] + base
    prompt = self.prune_convo(convo, prompt_length)

At prompt_length 1024 the loop never runs (every conversation is at least 1531 tokens), so the 1024 cells are unchanged.
Offline check before anything runs on 3bda (in the .venv, HF_HUB_OFFLINE=1, tokenizer
neuralmagic/Meta-Llama-3.1-8B-Instruct-quantized.w4a16): seeds 0-319 at 1024, 2048, 3000, 4096, 7168, 8192: 0 exceptions,
encoded length exactly prompt_length, and the SAME token counts on two runs (determinism). Save the output with the results.

## Change 3: campaign.sh
- NAME=l8b-levers-20260919 (RES, LOG, STATUS follow). ARMS becomes the pass list "base canon base canon base canon".
- Loop: for base, `dut ensure-base "$BASE_VERSION" "$BASE_SHA"` (pattern of exec/ci-mimic-20260918/campaign.sh line 102);
  for canon, `dut ensure-canon`; then `dut serving-down` (engine restart, see above); then run_arm with
  CI_MIMIC_ARM=<arm>-pass<k> CI_MIMIC_CONFIGS_JSON=<file>. DRIVER_TIMEOUT about 3600 s per pass.
- DEADLINE_START / DRIVER_END_BY: the pre-CI hold starts 01:40 UTC, the ci-runner-stop timer 02:45 UTC, the nightly apt
  reinstall about 03:39 UTC; the lease clears about 13:20 UTC (est.). HANDOFF=up at the end.
- restore_and_release: also verify config.env is 0 bytes.

## Change 4: launch.sh
Same md5 checks for every copied file (NFS attribute cache), canon build status ok, `bill-share.sh take` (refuses while Bill
is active, rc 2; jhan's order of 2026-09-19 covers it), then campaign.sh detached. Log exec/logs/l8b-levers-20260919.log.

## Before the first pass
1. One hand-run canon cell at nominal_users 32 and prompt_length 8192 with a short timeout: the hand-written llama plugin has
   never run above prompt 1024 in our records. KV need 8 x 9728 tokens x 128 KiB = 9.5 GiB per engine (128 x 1 GiB hugepages
   per engine); the largest T0 cell needs 3.5 GiB. Its duration is an upper bound for the long-prompt estimates.
2. Arm identity: dpkg-query -W tron; sha256sum /opt/positron/bin/rinzler against the manifest; optional
   `objdump -d /opt/positron/bin/rinzler | grep -cE 'tdpb|tileloadd|tilestored|ldtilecfg'` (about 86 canon, 0 clean; the
   binary is stripped, so objdump and strings, not nm).
3. dut.sh preflight (lease, platformd, config.env bytes, canon build status, installed version).

## Decision rule (pre-registered on the page; do not change after seeing data)
- Per config and comparison: paired t over the 3 passes (pass r pairs with pass r), |t| >= 4.303 (95 % two-sided limit of
  Student's t with 2 degrees of freedom) and |change| >= 1 %.
- Pair at 16K: 2 users x 7168 (16318) against 8 users x 1024 (16120). Within 3 points = one mechanism, a long-prompt shape is
  a peer recommendation. 2-user cell ahead by more than 3 = context lever stronger, the long-prompt shape is the primary
  recommendation. 8-user cell ahead by more than 3 = users lever stronger, the page stands.
- Triple at 8K: 1 user x 7168 (8159, one minibatch), 2 users x 3000 (7982, two minibatches), 4 users x 1024 (8060, two
  minibatches); per minibatch 8.2K, 4.0K, 4.0K. Hiding hypothesis SUPPORTED when the 1-user cell gains more than 3 points
  above both others and those two agree within 3 points; REJECTED when all three agree within 3 points; anything else =
  undecided, named in the report. The nominal_users-4 cell counts only if its per-engine request counts show 10 requests per
  engine (Caddy spread), otherwise it is excluded from the triple.

## Duration (est.)
Per pass 2.5, 3, 3.5, 4, 5.5, 6 (2 users at 1024 .. 8192), 3 (1 user at 7168), 2.5 (4 users at 1024), 4 and 6 (8 users at
1024, 2048) = 40 min of benchmark time, plus about 4 min of probes and snapshots = 44 min. 6 passes 4.4 h + 6 switches x
6 min (apt swap 9 s, 20 s settle, engine stop and start with the idle test, re-provisioning 1-2 min) 0.6 h + the check cell
= about 5.3 h. Anchors: the prompt-1024 2-user config measured 2.52 min in
data B (2.87 and 3.83 min in the two ci-mimic arms); data A 4-user cell 2.41 min, 8-user cells 3.6-4.0 min; no long-prompt
cell has been timed.

## Traps (from the memory notes)
NFS attribute cache on edited scripts; never edit a running script; Monitor tail -F on the NFS copy of a 3bda log delivers
nothing (poll with grep over ssh); config.env must be 0 bytes at handoff; the flock can be held
by another session's campaign; perf_event_paranoid lift 4 -> 0 -> 4 for the probe has jhan's standing approval (log set and
restore); perf -x CSV column 4 is run time, not the count; anchor pgrep -f patterns so the checker does not match itself.
