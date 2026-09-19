---
name: rinzler-unit-expert-replicas-750
description: "2026-09-17 Rhys hand-edited /etc/systemd/system/rinzler@.service on delphi-3bda to add --num-expert-replicas 750 (gpt-oss-120b perf); NOT persistent (tron .deb regular file, nightly apt remove+install at ~03:39 UTC reverts it); bare form breaks any multi-model rinzler at startup; what the flag does (FPGA expert weight copies), how to keep it, how to verify"
metadata: 
  node_type: memory
  type: project
  originSessionId: d50b7d5d-95f2-4e9a-b8c7-b233039eada3
  modified: 2026-09-17T23:54:51.965Z
---

# Rhys's manual edit: `--num-expert-replicas 750` in the rinzler systemd unit (delphi-3bda)

Words used here: rinzler = the production tron server; platformd = the daemon
that writes /etc/rinzler/instance-N.env (RZ_CLI_ARGS, CPUAFFINITY) and starts
rinzler@N units over D-Bus; nightly = the systems_test System CI job for
delphi-3bda (.github/workflows/system_ci_granite_rapids_72_rinzler_OCI.yaml,
cron 03:30 UTC); MoE = mixture of experts; expert = one per-layer feed-forward
block that the router picks per token; replica = an extra whole copy of an
expert's weight tensors on another FPGA card.

## What changed (facts verified 2026-09-17 23:35-23:55 UTC, read-only)

- Rhys (Slack DM to jhan, 2026-09-17) edited `/etc/systemd/system/rinzler@.service`
  on delphi-3bda at 23:27:55 UTC (root, mode 0654) so ExecStart reads:
  `ExecStart=/usr/bin/taskset -c ${CPUAFFINITY} /opt/positron/bin/rinzler --num-expert-replicas 750 $RZ_CLI_ARGS`
  Reason he gave: "evidence that --num-expert-replicas 750 has good performance
  effects on gpt-oss-120b", and no good way to pass it to the nightly. The size
  of the effect: Insufficient data (ask Rhys for his numbers).
- He restarted platformd at 23:28:10 UTC but ran no `systemctl daemon-reload`.
  The running rinzler@1 (pid 806124, Bill's half: --instance 0,2, cards
  38/3b/10/13, started 10:13:06 UTC, FOUR --model args incl.
  ingested-gpt-oss-120b-tp4) still has the OLD ExecStart and no flag
  (NeedDaemonReload=yes). Not-yet-loaded units rinzler@0/2/3 read the edited
  file on their next start (a fresh template load needs no daemon-reload).
  A stop followed by a separate start also re-reads it (unit is disabled +
  CollectMode=inactive, so it unloads on stop); only `systemctl restart`
  keeps the old line.

## Persistence verdict: NOT persistent across the nightly (high confidence)

- The unit file is a REGULAR file of the tron .deb, not a dpkg conffile:
  `dpkg -S` -> tron; no /var/lib/dpkg/info/tron.conffiles; `dpkg -V tron` shows
  `??5??????   /etc/systemd/system/rinzler@.service`. Source:
  CMakeLists.txt:796 `install(FILES packaging/systemd/rinzler@.service DESTINATION /etc/systemd/system)`;
  CPACK_DEBIAN_PACKAGE_CONTROL_EXTRA = preinst;postinst;prerm only.
- The nightly's first DUT step is `apt-get remove -y tron || true && apt-get update
  && apt-get install -y tron && apt-get upgrade -y`, then `uv run system_ci`.
  Observed 2026-09-17: remove 03:39:28 (deletes the edited file), install
  03:39:42-45 (pristine unit), tron.postinst `systemctl daemon-reload` 03:39:45,
  platformd started the engines at 10:13 UTC. Same daily pair since 2026-08-23,
  03:35-03:48 UTC (outliers 08-27 05:17, 08-28 06:07); it reinstalls even when
  the version is unchanged (08-29, 09-15). So the edit is gone before the
  nightly starts any rinzler: the nightly NEVER sees the flag this way.
- The edit DOES survive a reboot (ext4 root) and survives daemon-reload.
- Manual `scripts/cfgdut.py` (configure_dut) also does remove+install and
  bounces inference via platformd -> also reverts the edit.
- Nothing else rewrites the unit (no cron/timer, nomad disabled, cloud-init
  never ran, unattended-upgrades cannot pull positron origins, platformd only
  ships the shadowed /usr/lib/systemd/system/rinzler@.service, 560 B). A remote
  Ansible push cannot be excluded from the machine alone.

## TRAP: the bare form breaks every multi-model rinzler (medium-high confidence, code + packaged strings)

- `--num-expert-replicas 750` WITHOUT `:<public-name>` is accepted only when the
  instance registers exactly one model group (--model/--model-path). With N>1
  rinzler prints to stderr (journal):
  `Error: --num-expert-replicas without ':<public-name>' requires exactly one model (got N); use <count>:<public-name>`
  and exits 1 during argument resolution, before any model load
  [h/rinzler/rinzler-cli.hpp:160-167, src/rinzler.cpp:4423-4456, test
  t/t_rinzler_tokens.cpp:19038-19047; string present in the packaged rinzler
  2026.09.17-31b80a18]. The FUSE stats mount is created before the check; the
  unit's fusermount3 -u lines clean it up.
- Restart=on-failure fires, but StartLimitBurst=5 / StartLimitIntervalUSec=10s
  end the loop: after 5 failures within 10 s the unit sits in failed state
  (result start-limit-hit) until a manual start / reset-failed / platformd
  StartUnit after the interval. Check with
  `systemctl show rinzler@N -p NRestarts -p Result -p ActiveState`
  (journal needs sudo: `sudo journalctl -u rinzler@N`; plain jhan cannot read it).
- Platformd instances are multi-model by design: rinzler@1 today has 4 models;
  the nightly functional loads are groups of 6 and 2 models, soak 3
  (systems_test scripts/system_ci.py:28-40, clone 470aca1 of 2026-08-28).
  So the CURRENT edit would fail any platformd-started instance that loads it
  (rinzler@0/2/3 now, rinzler@1 after daemon-reload+restart or stop+start).
- Form for several models: `--num-expert-replicas 750:ingested-gpt-oss-120b-tp4`
  (public name = exactly the --model value; repeatable; later entries override
  for the same model; all aliases of that model get it). SECOND TRAP: this form
  fails on any instance that does NOT load that model:
  `Error: --num-expert-replicas public name 'ingested-gpt-oss-120b-tp4' is not a loaded model`
  [h/rinzler/rinzler-cli.hpp:172-176]. So NO form is safe in the shared unit
  template unless every instance it starts serves gpt-oss-120b; the only clean
  place is per-instance RZ_CLI_ARGS (platformd), which Rhys says has no knob. Dense models (llama)
  silently ignore the flag (no error, no effect; wrap is `if constexpr (plugin_t::moe)`);
  a nonzero count with `--expert-placement none` is rejected at parse time.
- Not yet observed live: NRestarts=0 on rinzler@1 as of 23:55 UTC 2026-09-17.

## What the flag does (mechanism, tron 30c4ac82cb = main 2026-09-16)

- Meaning: a global BUDGET of at most N ADDITIONAL whole copies of expert weight
  tensors for ONE MoE model, spread over the instance's FPGA devices
  (`current_device_mask & get_devices()` = the --devices list; the device table
  has no CPU entry). Default 0. Requires load-aware placement
  (`--expert-placement load`, the default) [h/tron/models/config.hpp:156-190
  Note [MoE expert placement and routing configuration]].
- Planner (src/tron/hardware/expert_placement_plan.cpp Note [Expert placement
  planning]): L[x] = load share x top-k; greedy copy counts by marginal gain
  L/(c(c+1)); per-expert cap = device_count copies (tp4: max 3 extra);
  zero-load experts never copied; nothing copied on 1 device; then LPT packing
  per router. Memory is NOT checked ("the caller must ensure the plan fits").
- Load profile: `<weights dir>/expert_load.json` (JSON 36 rows x 128 floats,
  row-normalised on load; `--expert-load-profile <path>[:<public-name>]`
  overrides; invalid -> "Ignoring expert-load profile" + uniform fallback).
  Present on 3bda for the deployed gpt-oss-120b weights
  (/opt/positron/weights/huggingface/positron-ai/openai--gpt-oss-120b-ingest-best-gptq--2026-04-09/,
  owner bgamari, 2026-06-02; max share per router 0.037-0.114 vs uniform 0.0078).
  config.json there: num_local_experts 128, experts_per_token 4,
  num_hidden_layers 36 -> 4608 experts; 750 = 16.3% extra copies.
  est. (Python re-implementation of choose_expert_copy_counts, not a tron run):
  measured profile -> 681 distinct experts get copies (619 x2, 55 x3, 7 x4);
  uniform fallback -> 750 experts, all in routers 29-35 (ties go to high IDs).
- Runtime effect: per router call, active experts are scheduled over their copy
  devices (mixture_of_experts.hpp -> expert_matmul_schedule, unit-cost jobs).
  Changes WHICH FPGA card runs each expert matmul and FPGA weight memory use.
  Does NOT change routing, token outputs, the CPU attention path or any AMX
  kernel (no file under h/ or src/ mentioning AMX reads num_expert_replicas or
  the plan). Cache key includes the count (h/tron/models/cache.hpp:33): a run
  with a different count never reuses another count's cached model.
- Log lines to confirm it engaged: parse time `Expert replicas: <raw arg>`;
  load time `Placing experts by measured load` or
  `Planning up to N additional expert replicas with uniform loads`, then
  `Using ExpertsByPlan placement strategy with device_count={}, n_moe_routers={}`.
- runtron: `--num-expert-replicas NUM` (single value, no per-model suffix, no
  parse-time log line) [src/runtron.cpp:685-690].

## Effect on OUR work

- None of our campaign scripts (intel-AMX/exec, VNNIed-K-in-place/exec) start
  rinzler via systemd or platformd; none runs the installed
  /opt/positron/bin/rinzler. They stop/wait on rinzler@0-3 and exec our own
  built binaries (/var/tmp/jhan/tron-*/gen/rinzler.*, runtron.*) or a
  dpkg-deb-extracted one, with placement args hard-coded from hand-copied
  platformd files. So the edit reaches none of our measurements unless we add
  the flag ourselves. All gpt-oss-120b cells so far ([[wedperf-20260916-campaign]],
  [[p0perf-20260913-campaign]], [[more-testing-round1]]) ran WITHOUT it.
- Future gpt-oss-120b cells: decide explicitly, and pass the SAME flag to base
  and target binaries. Any comparison with a Rhys/nightly number must state
  whether that run had the flag (check its journal for "Expert replicas").
- The edit reaches Bill's half only if his platformd instance is restarted
  after a daemon-reload or stopped+started, and then the bare form fails
  (see TRAP). jhan should tell Rhys about the `:<public-name>` form.

## How to keep it if we ever need it (not applied; Rhys owns the edit)

- Drop-in survives the nightly reinstall (verified in a dpkg sandbox; the .deb
  ships no .d dir): `/etc/systemd/system/rinzler@.service.d/expert-replicas.conf`
  with `[Service]`, an empty `ExecStart=` line (Type=simple allows exactly one
  command), then the full new ExecStart using `750:ingested-gpt-oss-120b-tp4`.
  Needs one daemon-reload before the next engine start (the nightly postinst
  gives one daily). Still a machine-wide change on a shared box -> Rhys/jhan decide.
- RZ_CLI_ARGS in /etc/rinzler/instance-N.env is platformd-owned (0600,
  rewritten on every provision) -> not a stable place. /opt/positron/user/config.env
  is read AFTER the instance env, so setting RZ_CLI_ARGS there would REPLACE
  platformd's model list -> do not.
- Proper fix = a platformd/systems_test knob; Rhys said none exists (2026-09-17).

Provenance: exec/results/expert-replicas-20260917/ (verifier-verdicts.json,
4 adversarial agents, workflow wf_4d6dee24-618). Related: [[3bda-nightly-rinzler-cleanup]],
[[3bda-shared-with-bill]], [[amx-router-project]] (Note [Expert matmuls],
worker-0 expert dispatch), [[nightly-vs-ours-tps-context]], [[nightly-amx-check-20260916]].
