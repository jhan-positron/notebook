---
name: asimov-emulator-run-facts
description: Jesse Zhang's 2026-10-30 answers on the Asimov emulator image (clock, slowdown, caches, OCM regions and /dev/ocm, cores, toolchain, DRAM)
metadata:
  type: project
---

From Jesse Zhang's Slack DM reply, 2026-10-30 18:59 PDT (from RTL/firmware/kernel sources, not yet measured):
- Clock: 2,000 MHz core, CNTFRQ 1 GHz, so 1 CNTVCT tick = 1 ns = 2 cycles. clock_gettime gives chip time. Cycle-exact emulator, no DVFS noise.
- Slowdown: 1 s chip time = about 46 min wall (1 ms = 2.8 s), plus about 25 min boot. No run-length cap.
- Caches: per core 32 KiB L1I + 32 KiB L1D; per DSU 128 KiB L2 (shared by 2 cores) + 256 KiB L3; 64 B lines. CMN SLC 5 MiB, of which 4 of 16 ways are locked as OCM.
- OCM (CMN): 5 regions × 256 KiB (1.25 MiB) at PA 0xE0000000, 0xE0100000, 0xE0200000, 0xE0300000, 0xE0400000 (only first 256 KiB of each 1 MiB slot is backed). One region per CMN home node. Must be mapped Normal write-back; ECC, no reset init: write before read. Jesse will add /dev/ocm: mmap(NULL, 0x40000, PROT_READ|PROT_WRITE, MAP_SHARED, fd, <region PA>), one mmap per region. SPM (scratchpad) is a different thing with different rules.
- Linux: device tree boot, /proc/config.gz present, 4 KiB pages, NO THP and no hugetlbfs. /dev/mem is STRICT_DEVMEM. Program runs as a plain process under a minimal init with /proc, /sys, /dev mounted. Output captured to a file.
- Cores: kernel on CPUs 0-1 (DSU 0). Test on CPU 2 (DSU 1), isolated, partner CPU 3 offline by default; can bring CPU 3 online (isolated) for a shared-L2 test; CPUs 4, 6, 8 likewise. Jesse wants to know which test needs which cores.
- Build: asimov-os SDK, GCC 14.2 (Arm GNU Toolchain 14.2.Rel1), glibc, `-O2 -mcpu=cortex-a520 -static`. Jesse said "don't worry about the build, just hand me the branch".
- DRAM: just under 2 GiB at PA 0xC000000000; emulator DRAM is a host memory model, not LPDDR5X, so DRAM numbers are not silicon-like. Can give more if needed.
- PMU cycle counter from user space can be enabled on request.

**Why:** Sizes the emulator sweep (loads per size) and fixes the OCM access method.
**How to apply:** Size runs so chip time stays in the low seconds. Related: [[asimov-cache-topology-conflict]].

Second reply, 2026-10-30 20:50 PDT:
- Cores: CPUs 2-9 can all be online and isolated in one run; idle isolated cores do not touch caches. Program runs as root and may offline/online CPU 3 via /sys/devices/system/cpu/cpu3/online (outside timed sections). CPUs 2 and 3 also share the L2 TLB and one vector unit.
- PMU: PERF_EVENTS + ARM_PMUV3 present, perf_event_open works as root. Refill raw events: 0x03 L1D, 0x17 L2D, 0x2A L3D. perf_user_access=1 and EL0 PMU access enabled. arm_cmn mesh PMU also in kernel. Jesse asks which read method we use (read() on fd chosen).
- SPM: /dev/asimov-spm, Normal non-cacheable, only aligned 8/16/32-byte loads/stores (else bus error; no memcpy/memset). Jesse: the architecture spec's "On-Chip Memory" means all on-chip SRAMs incl. the 16 MB scratchpad, suggests adding a scratchpad pass.
- Huge pages: kernel will be built with THP and hugetlbfs; madvise(MADV_HUGEPAGE) or MAP_HUGETLB; tell them how many 2 MiB pages to reserve.
- Chip time: 5 s fine, no cap; model hemi_rtws_tlm is lightweight. Keep output compact.
- OCM: Jibin's per-DSU picture matches the March 2026 architecture spec v1.7 (home node on each DSU crosspoint); current RTL has 5 HN-S home nodes shared by all cores. DSU n's port is one crosspoint from the home node holding OCMn: CPU 2 (DSU 1) is one hop from OCM1 at 0xE0100000. Firmware can lock W = 1,2,4,8,12 ways (max 768 KiB/region); stock W=4. SLC-to-DRAM step expected near 3.75 MiB. DRAM is an embedded emulator memory (correction), still not LPDDR5X.
- Specs: asimovsw-docs firmware_boot_spec.md 7.1.5 "OCM cold-boot policy"; CMN_uArch_Spec v0.10 (Google doc 1QErHoAreoEQ7S9J9Tk8mtatuulwolT4dRHA9j5d5gzI); RTL cmns3_12_1.yml L648-720 (DSU ports at crosspoints 12,23,32,43,52; home nodes 13,24,33,44,53); cmn_hns_l3_tagpipe.sv L13864-13880 (lock decoder).

Third reply, 2026-10-30 23:24 PDT: L3 refill raw event is 0xA2 (L3D_CACHE_REFILL_RD); 0x2A opens but reads 0 on C1-Nano. OCM: flush before every timed pass incl. repeats; /dev/ocm maps 4 KiB pages, do an untimed pass first. SPM: driver maps 4 KiB pages on first touch, MAP_SHARED only (MAP_PRIVATE refused), mapping is write-combining (store bandwidth = merged bursts), a wrong-size access revokes the mapping and later accesses SIGBUS, so run SPM last with volatile/asm accesses. Code lives at https://github.com/jhan-positron/asimov (public), folder cache-mem-perf, local clone ~/workspace/ai-runs/asimov-repo.
