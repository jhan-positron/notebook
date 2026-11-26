---
name: arm-welcome-kit-crb-resources
description: "Where Arm's CRB support kit is and what it holds for memory-bandwidth questions (firmware 0.9.0 notes on CBusy, Arm's reference read rates, uefisettings tool, core CBusy PMU events)"
metadata:
  node_type: memory
  type: reference
  originSessionId: 4a6b911c-1987-43f1-be61-e96fcfc7261d
  modified: 2026-11-17T01:36:56.382Z
---

Arm's support kit for CRB is at `~/workspace/vendor-resources/ARM/agi-cpu-welcome-kit/` (12 GB, read-only use). Searched on 2026-11-16 for [[crb-whole-chip-read-drop-2026-11-15]].

Useful for memory-bandwidth work:
- `svk-release/docs/Arm_AGI_CPU_CRB_SVK_UserGuide_3.0.pdf`: firmware 0.9.0 notes. Page 7: "initial tuning of DMC CBusy thresholds and CPU CBusy sampling defaults". Page 8: "Fixed CMN CCG CBusy response selection for remote memory accesses when MPAM is enabled". Page 14: MPAM limits. Mesh clock 2.0 GHz.
- `tools/asct/reports/`: Arm's reference runs. All-reads peak 587.4 GB/s (128 CPUs, DDR5-7200, firmware 0.9.0, 2 NUMA nodes); 293.5 GB/s per node local; 170-178 GB/s cross-node.
- `svk-release/phx-soc-utils/tools/uefisettings/`: static binary that lists and changes UEFI settings from Linux (needs root and /dev/mem).
- Kit kernel source `svk-release/linux/...source.tar.gz`: perf event table for Neoverse V3 has core events L2_CHI_CBUSY0..3 (0x198-0x19B) and prefetch events (0x1B8, 0x1B9). No tool or patch reads the core control registers (IMP_CPUECTLR).
- Power and telemetry (found 2026-11-24, see [[crb-hw-record-2026-11-24]]): `tools/arm-telemetrix` (the program atx with its guide), `svk-release/phx-soc-utils/scripts/power_management` (Arm's `scmi_telemetry.sh` with the program `stlm`, a debugger script with the rail names, `cpufreq_ctl.sh`), `tools/sysdiag/Arm_Sys_Diag_Tool_2.0.pdf` pages 34 to 36 (Arm's power stress tests: about 150 W on one VCPU rail), SVK user guide page 11 (regulator current limits per rail). No kit file names the rail that feeds the mesh.
- Not in the kit, named by it: "Arm AGI CPU Tuning Guide", "ARM AGI CPU SoC BIOS User Guide", the ASCT tool itself (download).
- Support route: a case at support.arm.com, or the Arm FAE.

CRB state read on 2026-11-17 01:35 UTC: firmware AGI-CPU-CRB-v0.7.2 (kit is v0.9.0), kernel 7.1.3-arm-agi-20260916-v0.7.2, 4 KiB pages, one NUMA node (UMA mode), Secure Boot off, no lockdown, kernel headers and gcc 14.2 present. This state can change; read it again before use.

PDF tools (pdftotext) are not installed on the dev machine; agents extracted PDF text with a small Python script.

Added 2026-11-17 (user approved the two steps for that task only): `uefisettings hii list-questions` was run on CRB with sudo, list only. Output is in `crb/results/uefisettings-20261117/`. Firmware 0.7.2 has a form with "Enable MPAM" = 0, "DMC CBusy Thresholds" 25/75/100, and "CPU TXREQ Throttle" (TXREQ Max = Full L2 TQ, Limit Increment 16 "when CBusy is less than 2", Limit Decrement 8 "when CBusy is 3", CBusy Filter Threshold 1/4, Filter Window 128, TXREQ Min 1/32 L2 TQ). Not known: whether the throttle is active with MPAM off. "ACTLR_EL3 ECTLREN" = 0, "CFG_CTL NS Access Override" = 0, "NUMA Domain" = UMA, "DIMM Frequency" = 8000 MT/s. No visible prefetch setting; 886 of 1490 answers are unreadable. Core busy-level counts (events 0x198-0x19C) for slow and fast states are in `crb/results/w120-R8-20261117T020549Z` and `w120-R8g-20261117T020823Z`; script `an8.py` in the w120 scratch folder.
