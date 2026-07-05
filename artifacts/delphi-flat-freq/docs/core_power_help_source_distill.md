# Intel Speed Select Core-Power Help And Source Distill

Date: 2026-06-29  
Fresh run directory: `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power`

## Source Commands Captured

The fresh run captured help and platform state from the locally preserved `intel-speed-select` binary:

```text
intel-speed-select --help
intel-speed-select core-power --help
intel-speed-select perf-profile --help
intel-speed-select turbo-freq --help
intel-speed-select --cpu 24 core-power info
intel-speed-select --cpu 24 perf-profile info
```

Raw captures:

- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_help.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_core_power_help.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_perf_profile_help.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_turbo_freq_help.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_cpu24_core_power_info.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_183548_fresh_core_power/raw/isst_cpu24_perf_profile_info.txt`

## Capability Summary

CPU24's power domain reports `core-power` as supported with proportional priority:

```text
core-power
  support-status:supported
  enable-status:disabled
  clos-enable-status:disabled
  priority-type:proportional
```

The platform reports Speed Select Turbo Frequency enabled, Speed Select Base Frequency unsupported, and Speed Select Core Power disabled at baseline.

The core frequency facts that matter for this project:

- cpufreq max policy: 4400 MHz.
- base frequency: 2700 MHz.
- level-0 turbo table includes 3 active cores at 4400 MHz.
- level-0 turbo table includes 24 active cores at 3900 MHz.
- SST-TF properties advertise 8 high-priority cores at 4400 MHz and a level-0 low-priority clip of 2700 MHz.

## What Core-Power CLOS Appears To Do

`core-power` exposes CLOS configuration: association of CPUs to CLOS classes plus per-CLOS fields such as EPP, proportional priority, min, max, and desired frequency.

In this run, CLOS max behaved as a real cap/permission. With two active cores, one core allowed up to 4400 MHz and one core capped at 3900 MHz separated by about 460 MHz Bzy_MHz.

However, CLOS max did not act as a hard per-core frequency setter. Under 24 active physical cores, the selected CLOS0 workers stayed around 3900 MHz even with `clos-max=4400`.

The best working model from the fresh measurements is:

```text
achieved frequency ~= min(CLOS max, active-core turbo-ratio limit, power/thermal budget)
```

## Implication For TRON-Shaped Work

The tested qwen TP2 style synthetic shape used 24 active physical cores on one power domain. That activates the 24-core turbo-ratio limit, which is 3900 MHz. Because selected workers are already bounded by that platform limit, `core-power` did not raise them above the common active cores.

For a goal like "keep up to 5 selected worker threads faster while background threads stay active," the platform's SST-TF properties are the better match. The follow-up SST-TF run confirmed this: selected workers measured 4400 MHz, common active cores were clipped to 2700 MHz, and same-session barrier FPS improved by +7.08% to +7.25% versus base.

SST-TF follow-up artifacts:

- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_213113_sst_tf_followup/results/pilot_gate.txt`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_213113_sst_tf_followup/summaries/sst_tf_joined_summary.csv`
- `/home/jhan/workspace/intel-vs-amd/speed-select/workspace/core-power_experiment/runs/20260629_213113_sst_tf_followup/summaries/sst_tf_deltas_vs_base.csv`

## Operational Notes

Host context is mandatory for reliable ISST work. The default sandbox can hide `/dev/isst_interface`, producing false "drivers not loaded" conclusions.

For measurement, test the actual privileged command that will be used:

```text
sudo -n turbostat ...
```

Do not use `sudo -n true` as the project-level sudo check. It does not prove whether the real turbostat path is usable, and it previously created unnecessary confusion.

Every run that mutates ISST policy should:

1. Capture a baseline readback.
2. Register cleanup before mutation.
3. Restore turbo-freq/core-power/CLOS associations after interruption or failure.
4. Capture a final readback.

The fresh run did this, and the final state was restored to core-power disabled, CLOS disabled, turbo-freq enabled, and all tested CPUs associated to CLOS0.
