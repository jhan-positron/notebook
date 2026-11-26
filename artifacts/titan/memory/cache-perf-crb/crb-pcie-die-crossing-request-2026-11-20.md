---
name: crb-pcie-die-crossing-request-2026-11-20
description: "adam's request of 2026-11-20 to measure PCIe latency across the two dies of the CRB chip; where the request lives in Slack, which PCIe devices and slots the CRB has, what is known and not known about the die of each device"
metadata:
  node_type: memory
  type: project
  originSessionId: b662db86-cbfe-4b4a-a59a-37f11dacb0e7
  modified: 2026-11-20T23:29:25.358Z
---

On 2026-11-20 adam asked (group DM with William Baumann and Jibin, Slack id C0CKJHWGF19) for the PCIe port latency on CRB when the path crosses to the other die. Work folder: `crb/pcie/` (empty on that day). No PCIe or IO latency number for CRB existed in the project, in Slack or in public sources on that day.

State of the thread at 15:28 PST on 2026-11-20:
- 12:11 adam: no fix from Arm for the card power problem; suggests "some onboard peripheral" for the "NUMA-crossing" test.
- 12:30 adam: "I got a workaround ... can we power down the CRB and try agian?" My reading (inference from his DM of 2026-11-06 with the same wording): he wants the card installed again.
- 12:52 Jibin asked which test adam wants after the power cycle.
- 13:44 adam: "Initially just seeking permission to power the CRV down and try the Arm suggestion for workaround." So he asked for neither test at that point, only for permission to power down. Not answered in Slack at 15:28 PST. No shutdown notice was in #phoenix-crb at 15:28 PST.
- Open, only adam can say: which path he needs (a core's register access to the device, or device DMA to memory), and a date.

Card power problem: 2026-11-06 to 11-09 adam tried two ConnectX-7 cards and one ConnectX-4 card in both card slots; the motherboard lost all power about 45 s after power-on (#phoenix-crb, id C0C1R7XEVU6, 2026-11-09). Arm knew it on 2026-11-10.

Hardware facts checked against files on 2026-11-20 (no CRB login was made; newest saved inventory is 2026-11-17 20:27 UTC):
- Two chips, 64 enabled cores each (70 physical), joined by a die-to-die UCIe link. Kernel log: CPUs 0-63 "chip number 0", CPUs 64-127 "chip number 1" (`crb/results/dimm-check-20261117/k0.txt:315,529`). 3 PCIe subsystems (PSS) per chip.
- Installed PCI devices, same in 12 saved boots: NVMe nvme0 0000:01:00.0 (root file system, x1 link), NVMe nvme1 000b:01:00.0 (may hold a CentOS install; read-only tests only), Broadcom BCM57508 network card 0007:01:00.0/.1 (OCP slot; port 0 carries SSH), ASPEED BMC graphics 0005:02:00.0, TI USB controller 0010:01:00.0.
- Card slots (SMBIOS, `~/workspace/machines/arm-crb/firmware-snapshot-20261117/smbios-dmidecode.txt:188-320`): HHHL x16 on segment 0002 (PSS0), FHHL x16 on segment 0017 (PSS4). Empty in all 12 saved boots.
- Die of each device: inference only. Segments 0000-000e go with chip 0 and 0010-001e with chip 1 (SMMU, ITS and GIC addresses of chip 1 are offset by 0x10_0000_0000; Arm's guide states only "Chip 0 PSS0"). So the USB controller is the only installed device on chip 1 and the two card slots are on different chips. A boot in PER_CHIPLET_NUMA mode, or Arm's board guide RS113021S-D (not in the kit), would confirm.
- Firmware "NUMA Domain" was UMA on 2026-11-17 (one NUMA node; every PCI bus "on NUMA node 0"). Options: UMA, PER_CHIPLET_NUMA, PER_SOCKET_NUMA. In the one-node mode a test can choose the die of the core by CPU number, and Linux cannot place memory on one die. The per-chiplet mode was never run on this board.
- Slack shows no CRB IO measurement by Jacob Geldbach; his DMA numbers are from Asimov in emulation.

Full fact lists with sources: workflow journals `~/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-pcie/b662db86-cbfe-4b4a-a59a-37f11dacb0e7/subagents/workflows/wf_92765189-1c1/journal.jsonl` (240 facts) and `.../wf_36ec045e-021/journal.jsonl` (checks).

**Why:** the facts took two workflows to gather and are the starting point of any PCIe test on CRB.

**How to apply:** before a PCIe test, re-read the Slack thread for adam's answer, then re-read the device list and the NUMA mode on CRB (a card install and a power cycle were pending). CRB rules still hold: [[crb-check-dimm-count-every-use]], root needs approval per task, never pin to CPUs 126-127, announce a shutdown in #phoenix-crb. Related: [[arm-welcome-kit-crb-resources]], [[crb-whole-chip-read-drop-2026-11-15]].

Lesson from this task (my own): a Slack thread can move on while a long task runs. Re-read the thread just before I hand over a reply draft, and count the words of a length-limited draft with a script before the first review, not after.
