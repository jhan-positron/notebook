# Reminder: where the speed-select scripts and their usage notes live

Written by Claude Code on 2026-09-17. Every path below was checked on that day (ls, file headers, diff of the
mirror copies against the canonical files).

## Short version

The two scripts you remember are `flat_freq_utils.sh` (bash, sourceable library: apply, revert, status,
check, 3-tier apply) and `gen_tron_flatfreq.py` (python: turns a resource-map.yaml into the exact
intel-speed-select command sequence). Both live in
`~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/` (NFS, same path on delphi-3bda and delphi-3af6)
and are mirrored with a README in the notebook repo under `artifacts/delphi-flat-freq/`. The usage notes are
the script headers themselves, the notebook README, and `/scratch/jhan/flat_freq_tests/README.md` on the DUT.
This project folder itself now lives at `~/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect/`
(moved on 2026-09-17 from `~/workspace/intel-speed-select-recollect`).

## Words used here

- isst, intel-speed-select: Intel's command-line tool for Speed Select (SST). It sets the frequency class
  (CLOS) of each cpu and the turbo-freq (SST-TF) state. On delphi-3bda the NOPASSWD copy is
  `/opt/intel-speed-select/intel-speed-select`.
- CLOS0 / CLOS3: the fast class (2.7 to 4.4 GHz allowed) and the capped class (2.7 GHz ceiling).
- flat freq, flat-high: the project's name for "the busy tron cores run at the top flat frequency
  (about 4.1 GHz) instead of the boot default, where most cores sit at 2.7 GHz".
- DUT: delphi-3bda. NFS: `/home/jhan` is one network share, so the same path works on claude-box,
  delphi-3bda and delphi-3af6. `/scratch/jhan` is a second share that is visible on the delphi hosts.

## The scripts

| file | what it is | canonical path | mirror |
|---|---|---|---|
| `flat_freq_utils.sh` (v3, 2026-07-06, 27 KB) | bash library. `source` it, then `flat_freq_apply` (all cores fast), `flat_freq_apply "<cpulist>"` (listed cores + HT siblings fast, rest capped), `flat_freq_apply_tiers "<fast>" "<mid>"` (3 tiers: ~4100 / <=3900 / <=2700), `flat_freq_revert` (boot default), `flat_freq_status`, `flat_freq_check`. Auto-detects the NOPASSWD isst binary per host. Leaves turbo-freq enabled (the v2 finding: +200 MHz over the old disable recipe). | `~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh` | `~/workspace/notebook/artifacts/delphi-flat-freq/flat_freq_utils.sh` (byte-identical) |
| `flat_freq_utils_v2.sh` (2026-07-02) | the previous version of the same library, kept next to it. Use v3 unless you need to reproduce a July 2 to 5 run exactly. | same directory | none |
| `gen_tron_flatfreq.py` (2026-07-09) | python. `gen_tron_flatfreq.py <resource-map.yaml> [--section granite_rapids_6962p] [--isst PATH] [--also-boost dev,rinzler,platform] [--revert] [--emit out.sh]`. Prints or writes the isst command sequence that puts the map's tron_cores + peer_cores (+ HT siblings) in CLOS0 and everything else in CLOS3. | `~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/gen_tron_flatfreq.py` | `~/workspace/notebook/artifacts/delphi-flat-freq/gen_tron_flatfreq.py` (byte-identical) |

Both scripts carry their full usage text in the first 45 lines of the file. Frequency state set by them does
not survive a reboot (the BIOS re-deals the boot partition).

The tool binaries the scripts call (both are patched builds of the Linux v6.8 `intel-speed-select` source: the
root-only guard removed, the topology cache moved to `/tmp/isst_cpu_topology.dat`):

| binary | notes |
|---|---|
| `~/workspace/intel-vs-amd/speed-select/workspace/flat_freq/20260623_codex_preserved_tmp/intel-speed-select-v6.8/intel-speed-select` (2026-06-22, 384 KB) | the June build; rebuild recipe `rebuild_intel_speed_select.sh` next to it (gcc, no libnl); build notes in `speed_select_BUILD_NOTES.md`, the patch is described in `workspace/flat_freq/SYSTEM_CHANGE_LOG.md` lines 63-65. In the NOPASSWD sudoers list on delphi-3bda. |
| `~/workspace/intel-vs-amd/speed-select/workspace/intel-speed-select/intel-speed-select` (2026-07-01, 415 KB) | the later build; the same size as the copy installed at `/opt/intel-speed-select/intel-speed-select` on delphi-3bda, which `flat_freq_utils.sh` auto-detects there. |

The shipped production equivalent is not one of ours: `/usr/local/sbin/intel-speed-select-state` on
delphi-3bda (Hannah's Ansible role, `apply | restore-baseline | readback | verify`, config in
`/etc/default/intel-speed-select-state`). It is what runs at boot today.

## What delphi-3bda runs at every boot to set up the flat frequency

Verified live on 2026-09-17 against the unit file, the config file, the script, and the journal of the current
boot (machine up since 2026-09-15 23:53 UTC). Two boot steps run, in this order.

1. `systemd-modules-load.service` loads the three Speed Select kernel modules listed in
   `/etc/modules-load.d/intel-sst.conf`: `isst_if_mbox_pci`, `isst_if_mmio`, `isst_tpmi`. They create
   `/dev/isst_interface`. The tool refuses to run without that device.
2. `intel-speed-select-state.service` (`/etc/systemd/system/intel-speed-select-state.service`, enabled,
   `Type=oneshot` = runs once and then shows "active (exited)", ordered `After=systemd-modules-load.service
   local-fs.target`, `WantedBy=multi-user.target`) runs exactly one command:

   ```bash
   INTEL_SPEED_SELECT_CONFIG=/etc/default/intel-speed-select-state /usr/local/sbin/intel-speed-select-state apply
   ```

The config file it reads (the header says "Managed by the intel-speed-select Ansible role"):

```bash
ISST=/opt/intel-speed-select/intel-speed-select
EXPECTED_LOGICAL_CPUS=288
MODEL_PATTERNS=6962P
ANCHOR_CPUS='0 24 48 72 96 120'
FAST_CORE_RANGES='7-14 24-71 79-86 96-143'
BOOT_CLOS0_RANGES='0-1 18-19 36-37 54-55 72-73 90-91 108-109 126-127 144-145 162-163 180-181 198-199 216-217 234-235 252-253 270-271'
BOOT_CLOS3_RANGES='2-17 20-35 38-53 56-71 74-89 92-107 110-125 128-143 146-161 164-179 182-197 200-215 218-233 236-251 254-269 272-287'
```

`apply` first checks that the tool is executable, `/dev/isst_interface` exists, `nproc` is 288 and the cpu model
name contains `6962P`. It then expands `FAST_CORE_RANGES`, adds each cpu's hyper-thread sibling (read from
`/sys/devices/system/cpu/cpuN/topology/thread_siblings_list`; on this machine cpu N pairs with cpu N+144), and
issues these `intel-speed-select` commands in this order. "Anchor cpu" is the script's name for the six cpus in
`ANCHOR_CPUS`. The turbo-freq, core-power and config commands are issued once per anchor, not per cpu.

```bash
ISST=/opt/intel-speed-select/intel-speed-select
# step 1: per anchor, in anchor order 0 24 48 72 96 120
$ISST --cpu $A turbo-freq enable
$ISST --cpu $A core-power disable
# step 2: per anchor, same order
$ISST --cpu $A core-power config --clos 0 --weight 0 --min 2700 --max 4400
$ISST --cpu $A core-power config --clos 3 --weight 0 --min 800 --max 2700
# step 3: the capped set (64 cpus) into CLOS3, one command per segment
$ISST --cpu 0-6     core-power assoc --clos 3
$ISST --cpu 15-23   core-power assoc --clos 3
$ISST --cpu 72-78   core-power assoc --clos 3
$ISST --cpu 87-95   core-power assoc --clos 3
$ISST --cpu 144-150 core-power assoc --clos 3
$ISST --cpu 159-167 core-power assoc --clos 3
$ISST --cpu 216-222 core-power assoc --clos 3
$ISST --cpu 231-239 core-power assoc --clos 3
# step 4: the fast set (224 cpus) into CLOS0, one command per segment
$ISST --cpu 7-14    core-power assoc --clos 0
$ISST --cpu 24-71   core-power assoc --clos 0
$ISST --cpu 79-86   core-power assoc --clos 0
$ISST --cpu 96-143  core-power assoc --clos 0
$ISST --cpu 151-158 core-power assoc --clos 0
$ISST --cpu 168-215 core-power assoc --clos 0
$ISST --cpu 223-230 core-power assoc --clos 0
$ISST --cpu 240-287 core-power assoc --clos 0
# step 5: read-only self-check. Per anchor: perf-profile info, core-power get-config --clos 0,
#         core-power get-config --clos 3. Then core-power get-assoc over 0-287.
```

Every write command's output is checked for its success marker (`enable:success`, `disable:success`,
`config:success`, or one `assoc:success` per cpu in the segment) and for the absence of the words "fail" and
"error". The service exits 0 only if the self-check passes: turbo-freq enabled on each anchor, CLOS0 at
2700-4400 MHz, CLOS3 at 800-2700 MHz, association counts clos0=224 and clos3=64, and the first fast cpu in CLOS0.

Journal of the current boot (the whole run took 2 s):

```
2026-09-15T23:54:22Z Applying Intel Speed Select two-tier flat-frequency policy.
                     CLOS0 fast CPUs: 7-14 24-71 79-86 96-143 151-158 168-215 223-230 240-287
                     CLOS3 capped CPUs: 0-6 15-23 72-78 87-95 144-150 159-167 216-222 231-239
2026-09-15T23:54:24Z Intel Speed Select two-tier policy verified: clos0=224 clos3=64.
```

A read-only re-check on 2026-09-17 18:33 UTC gave the same result: `intel-speed-select-state verify` passed and
`get-assoc` over 0-287 counted 224 cpus in CLOS0 and 64 in CLOS3.

Other facts checked the same day:

- Nothing else at boot touches Speed Select. Only one file under `/etc/systemd` mentions `intel-speed-select`.
  `positron-configure.service` runs `/usr/bin/positron-config.sh`, which has no speed-select, isst or CLOS
  reference. `/etc/rc.local`, `/etc/init.d`, `/etc/cron.d` and `/etc/positron` have none either.
- The script's other subcommands: `restore-baseline` (turbo-freq enable, core-power disable, CLOS0 2700-4400,
  CLOS1 and CLOS2 0-25500, CLOS3 800-2700, then the `BOOT_CLOS3_RANGES` into CLOS3 and the `BOOT_CLOS0_RANGES`
  into CLOS0 = the BIOS boot partition, 32 fast cpus), `readback` (alias `status`, prints the anchor configs
  and the association counts) and `verify` (the self-check alone, read-only).
- Useful hand commands on the DUT (all NOPASSWD for jhan):

  ```bash
  sudo -n systemctl restart intel-speed-select-state              # re-apply the shipped policy
  sudo -n /usr/local/sbin/intel-speed-select-state readback        # current anchor configs + counts
  sudo -n /usr/local/sbin/intel-speed-select-state verify          # pass/fail against the config
  sudo -n journalctl -b -u intel-speed-select-state --no-pager     # what the boot run printed
  ```

- To change the policy, change `FAST_CORE_RANGES` in the defaults of Hannah's intel-speed-select Ansible role
  and let Ansible re-render `/etc/default/intel-speed-select-state`. A hand edit on the host is overwritten on
  the next Ansible run. The role's source repository was not found under `~/workspace` in a bounded search on
  2026-09-17; ask Hannah for its location.

## The markdown files that describe how to use them

| file | what it covers |
|---|---|
| `~/workspace/notebook/artifacts/delphi-flat-freq/README.md` (2026-08-30) | one section per preserved tool: what `flat_freq_utils.sh` and `gen_tron_flatfreq.py` do, their canonical paths, which experiments used them, the related handoffs. Start here. |
| `/scratch/jhan/flat_freq_tests/README.md` on delphi-3bda (2026-07-24; mirrored as `notebook/artifacts/delphi-flat-freq/docs/flat_freq_tests-README.md`) | the benchmark series: layout of the run folders, the frequency-shape glossary (boot-default-clamped, flat-freq v1, universal flat v2, tron80, tron88, tier3, tron112), the "How to run these tests manually" recipe with the exact `source ...; flat_freq_apply` lines, and the per-run results. |
| `~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/ALLCORE_CEILING_HETERO_CLAUDE_20260702.md` (mirrored in `notebook/.../docs/`) | the measured grant rules the scripts encode: 4400 MHz only when every other core is <=2700, otherwise 4100, no 4200 rung; why turbo-freq stays enabled. |
| `~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/HANDOFF.md`, `HANDOFF_BOTH_SYSTEMS.md`, `ROOT_CAUSE_CLOS_PARTITION_CLAUDE_20260701.md` | the debugging story that led to the scripts: readback looked right but the CLOS partition clamped the tron cores at 2700 MHz. |
| `~/workspace/intel-vs-amd/speed-select/workspace/flat_freq/{TRON_RUNBOOK.md,HANDOFF.md,ACTION_PLAN.md,SYSTEM_CHANGE_LOG.md,highlight.md}` (2026-06-22 to 25) | the first (delphi-3af6, "base vs flat") phase: runbook, change log, result highlights. Older than the debug_3bda scripts. |
| `~/workspace/intel-vs-amd/speed-select/distilled_knowledge.md` and `input-2-ai/*.md` | distilled background on SST features written for AI sessions. |
| `~/workspace/notebook/handoffs/claude_20260702-20260703_debug-3bda-explore-best-freq-combo.md`, `claude_20260702-20260729_debug-3bda-flat-freq-run-ci-tests.md`, `codex_2026-06-22-2026-06-30_configure-xeon-6-core-speeds.md` | session handoffs: the first created v2 of the library, the second used it for the July benchmark campaigns, the third documents the June "flat policy" recipe. |

## Other script collections that call the tool (for completeness)

- The June (delphi-3af6, "base vs flat") library, before `flat_freq_utils.sh` existed:
  `~/workspace/intel-vs-amd/speed-select/workspace/flat_freq/runs/20260625_061253_delphi-3af6_base_candidate_3model_sweep/scripts/sst_ci_domains.sh`
  (`sst_ci_domains.sh readback|baseline|candidate RUN_DIR [label]`; baseline = turbo-freq enable + core-power
  disable, candidate = core-power disable + turbo-freq disable, on anchors 0 24 48 72 96 120), driven by
  `matrix_control.sh` and `run_one_with_policy_gate.sh` in the same directory. Documented in
  `runs/20260625_015655_delphi-3af6_instruction_6_24/summaries/investigation_report.md`, the run's
  `summaries/pre_run_handoff.md`, the "Base And flat_freq Commands" section of `distilled_knowledge.md`, and the
  CI-team install note `runs/20260624_003701_delphi-3af6_ci_sst_round2/summaries/ci_team_handoff.md`.
  Byte-identical copies of `sst_ci_domains.sh` sit in three other run folders.
- The July debug harnesses next to the library: `debug_3bda/test_flat_freq_function_3bda_closfix.sh` and
  `test_flat_freq_function_3bd6.sh` (apply, load, sample, classify, revert), `test_allcore_ceiling_3bda.sh` +
  `summarize_allcore.py` (the grant-ladder measurements), documented in `ROOT_CAUSE_CLOS_PARTITION_CLAUDE_20260701.md`
  ("Experimental confirmation") and `ALLCORE_CEILING_HETERO_CLAUDE_20260702.md` (section 1).

- Benchmark runners on the DUT: `/scratch/jhan/flat_freq_tests/scripts/run_*.sh` (24h sweep, tron80/tron88/tier3
  rounds, PR-3070 ladder, `ci_workload_profile.sh`); mirrored in `notebook/artifacts/delphi-flat-freq/test-scripts/`.
- July experiment kits: `/scratch/jhan/ab22 ... ab59/orchestrator*.sh` (each toggles CLOS for one A/B) and
  `/scratch/jhan/tools/{power_capture.sh,sysconfig_snapshot.sh}`.
- Earlier phases: `~/workspace/intel-vs-amd/speed-select/workspace/flat_freq/runs/*/scripts/` (June, 3af6:
  `apply_no_sst_tf_instance_0_4.sh`, `restore_original_sst_tf_instance_0_4.sh`, `sst_ci_domains.sh`) and
  `workspace/core-power_experiment/*/scripts/` (the core-power probes: `run_synthetic_matrix.sh`, `run_gate_a_probe.sh`,
  `run_sst_tf_matrix.sh`; documented in `core-power_experiment/test_data_scope.md` and `final_report.md`). A patched tool build lives in
  `workspace/intel-speed-select/intel-speed-select` with the rebuild recipe
  `workspace/flat_freq/20260623_codex_preserved_tmp/rebuild_intel_speed_select.sh`.
- This week's campaign harness: `~/workspace/intel-vs-amd/speed-select/intel-speed-select-recollect/exec/sst-ab-20260917/campaign.sh`
  (socket-1-only CLOS A/B with half-takeover and restore; results in `results/sst-ab-20260917/`).
  The three arms of that campaign (from `campaign.sh` lines 68-73 and its header; every arm changes only the
  CLOS association of socket-1 cpus, socket 0 = Bill's half is never touched):

  | arm | meaning | socket-1 CLOS0 (fast) | socket-1 CLOS3 (2.7 GHz cap) | cpus fast / capped |
  |---|---|---|---|---|
  | `boot` | the BIOS boot default = the machine without the boot service. Only the "PCT" cpus stay fast (the campaign's name for the 8 physical core pairs per socket that the BIOS puts in CLOS0 at boot; the acronym is not expanded in the project docs). Same set as `intel-speed-select-state restore-baseline` restricted to socket 1. | 72-73 90-91 108-109 126-127 216-217 234-235 252-253 270-271 | 74-89 92-107 110-125 128-143 218-233 236-251 254-269 272-287 | 16 / 128 |
  | `tuned` | the shipped policy exactly as the boot service applies it (the set in "What delphi-3bda runs at every boot"), restricted to socket 1: the 56 tron app cores fast, everything else capped. | 79-86 96-143 223-230 240-287 | 72-78 87-95 216-222 231-239 | 112 / 32 |
  | `tunedplus` | `tuned` plus cpus 72-78 and their siblings 216-222 fast: platform core 72, front-end (rinzler) cores 73-74, dev cores 75-78. This is the July 2026 "front-end un-clamp" ship candidate (which adds only 73-74 and 1-2) extended to the platform and dev cores. | 72-86 96-143 216-230 240-287 | 87-95 231-239 | 126 / 18 |

  Each arm is checked after it is applied with three probe cpus: 96 (tron app core), 73 (front-end core), 126
  (app core that is also a boot PCT core). Expected classes: boot [3 0 0], tuned [0 3 0], tunedplus [0 0 0].
  Measured outcome (decode tokens per second, 6 pairs per model, 95 % confidence interval): `tunedplus` vs
  `tuned` is +0.15 +/- 1.01 % (llama-3.1-8b), -0.53 +/- 0.41 % (qwen-3-4b), +0.03 +/- 0.31 % (mixtral-8x7b),
  +0.13 +/- 0.11 % (qwen-2.5-32b). So making 72-78 fast adds nothing for runtron. The front-end un-clamp can
  only show in the serving path, where rinzler runs [results/sst-ab-20260917/summary.md, lines 25-35].

## Quickest way back in

```bash
# on delphi-3bda (or 3af6), after checking the CI lease and the campaign flock:
source ~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/flat_freq_utils.sh
flat_freq_status                      # read-only: current CLOS / turbo-freq state
flat_freq_apply "<cpulist>"           # or flat_freq_apply_tiers "<fast>" "<mid>"
flat_freq_revert                      # boot default when done
# or generate the command list from a map without touching the machine:
python3 ~/workspace/intel-vs-amd/speed-select/workspace/debug_3bda/gen_tron_flatfreq.py \
    ~/workspace/tron/config/resource-map.yaml --section granite_rapids_6962p --emit /tmp/flat.sh
```

Note for the current machine: the shipped policy already keeps the tron app cores fast. A `flat_freq_revert`
returns the machine to the BIOS boot default, not to the shipped policy; to get the shipped policy back run
`sudo -n systemctl restart intel-speed-select-state`.

## Housekeeping notes (2026-09-17)

- Section "What delphi-3bda runs at every boot" added later on 2026-09-17 from a live read of the unit file,
  config, script and boot journal on delphi-3bda, plus a read-only `verify` and `get-assoc` count.
- Older project memory from the June work is under `~/.claude/projects/-home-jhan-workspace-tron/memory/delphi-3af6-sst-config.md`.
- This project's Claude memory was copied to the key of the new location
  (`~/.claude/projects/-home-jhan-workspace-intel-vs-amd-speed-select-intel-speed-select-recollect/memory/`), so a
  Claude Code session started in the new folder finds it. The copy under the old key was left in place.
- Verification: a 47-agent read-only sweep on 2026-09-17 checked every primary path and usage claim above against
  the files; the only corrections it raised concern dates inside two documents, not the paths.
