---
name: asimov-c1-cme-sources
description: "Where the Arm C1-Nano, C1-DSU and CME (C1-SME2 matrix engine, codename Griffin) RTL, Arm guides, firmware and existing CME measurements live; verified 2026-11-02 by session asimov-be against the repos"
metadata:
  node_type: memory
  type: reference
  originSessionId: bd044fcf-ffae-49bb-9c0e-8a6c06a13687
  modified: 2026-11-02T23:26:13.588Z
---

Verified 2026-11-02 (asimov-be session, read from the repos and PDFs directly):

RTL (GitHub Positron-AI-TSMC/asimov; the emulator image of run 1 is commit 0d9e214eb43b):
- ip/c1/logical/C1_DSU_DynamIQ_Cluster_1/{griffin,nevis,pilatus}: griffin = Arm C1-SME2 unit (the CME) r1p3-00rel0, nevis = C1-Nano complex, pilatus = C1-DSU. Mirror: positron-ai/asimov_arm_ip (c1/).
- pilatus/logical/config/C1_DSU_DynamIQ_Cluster_1.yaml: NUM_CORES 2, NUM_CME 1, FULL_MATMUL FALSE (half matmul), PPU_RST_STATE FALSE, VPU_DATAPATH 2x128, L2 128KB, L3 256KB one slice, NUM_PMU_COUNTERS 20.
- griffin/logical/griffin0_cme_channels/verilog/griffin0_cme_channels_pkg.sv: CME_SVL 512, CME_NUM_CPUS 2, CME_NUM_CMES 1, CME_PMU_CNT_NUM 31.
- Arm testbench programs in griffin/logical/testbench/execution_tb/tests/aarch64/: maxpwr_cme (maxpwr_cme_asm.s: full matmul target 4 FMOPA per cycle... "4 iterations of 4 FMOPA per cycle: target 16 cycles"; half matmul "2 iterations of 4 FMOPA each, each executing in 2 cycles: target 16 cycles"; IMP_CMECFR_EL1 bit 2 = full/half, read via IMP_CMESELR_EL1 = S3_0_C15_C11_1 then S3_0_C15_C11_0, EL1 only), gemm_bf16_sme2, gemm_fp32_sme2, gemm_uint8_sme2 (only Makefile.inc in the tree), cache_miss_cme, wfi_cme, di_dt_*_cme.
- Emulator: hemi_tlm setup_tree.sh swaps the Griffin clock-gate cells, so the hemi image includes the real CME RTL. emu/griffin_cme_arb_tlm is a unit test of the CME register arbitration only.
- Registers: design/css/cmn/registers/cmn_c1_cme_utility.rdl (AMU, RAS, MPMM per CME), cmn_c1_cme_debug.rdl.

Arm documents:
- On disk (copies in ~/workspace/titan/cache-perf/asimov/refs/): C1-Nano Core SOG 109590_0001_04 (public, documentation-service.arm.com/static/68c946f08a337a2bc66460c8; section 2.33 SME: 3 instructions per cycle to the CME, 4 with MOVPRFX fusion, loads/stores 2 per cycle, SMSTART/SMSTOP single issue; 3.12 shared VPU), C1-Pro Core SOG 109879_0102_05 (static/68c2ee168a337a2bc6645d3e; tables 2-45 to 2-47: SME processing throughput 4, SME loads 3, stores 2, latency NA, pipeline C), arm_c1_sme2_iBEP_User_Guide.pdf (109466, physical implementation only, "Griffin 9cpus, half matmul" floorplan).
- Not obtainable by script: C1-SME2 TRM 107831, C1-SME2 CIM 107832, C1-DSU TRM 107804, SME SWOG 111048 (developer.arm.com renders by script). Ask Arm support or the design team.
- Public LLVM model: llvm/lib/Target/AArch64/AArch64SchedC1Nano.td (CME pipes LD, ST, PF, VX0/1 ALU, FPDOT, MUL, PERMF/S, MC, MML0/1, RNMRET; commit ee94bd9a 2026-08-11) and llvm-mca tests Cortex/C1Nano-streaming-sme-only-instructions.s (FMOPA/BFMOPA/SMOPA/UMOPA latency 4 or 2, reciprocal throughput 2.00; vgx2 FMLA/FDOT 1.00; vgx4 2.00; LD1W za 7 cycles, ST1W za 11).

Firmware and OS (all verified in the repos):
- asimovsw-docs architecture/firmware_boot/firmware_boot_spec.md section 7.3.3 (SVE2/SME2 enablement chain: SCP arms CME0 PPU dynamic, TF-A ENABLE_SME_FOR_NS=2 and ENABLE_SME2_FOR_NS=2, kernel CONFIG_ARM64_SME=y) and "CME (SME2 unit) PPU" section: a core issuing streaming SVE against a static/off CME PPU stalls forever.
- SCP asimov-scp-firmware mod_asimov_system.c asimov_system_enable_cme_dynamic (commit 32658a4c 2026-07-06, present in scp-v0.34.0 which run 1 used). asimov-tfa platform.mk ENABLE_SME_FOR_NS 2, ENABLE_SME2_FOR_NS 2. asimov-os kernel.config CONFIG_ARM64_SME=y. Run 1 cpuinfo: CPU part 0xd8a, sme sme2 smei8i32 smei16i32 smef16f32 smeb16f32 smef32f32 smebi32i32.

Existing CME measurements and code (positron-ai/asimov-bench):
- presilicon-perf/asimov-latency/src/asimov_latency/engines/cme.py and presilicon-perf/results/latency-model-and-gaps.md: boots M2/M3 (2026-10-12, RTL 6da3026, hemi_rtws_tlm, SCP 4148207). 4,096 FMOPA FP32 in 4,173 ns on one core (1.02 ns = 2.04 cycles per FMOPA, 251 MAC/ns); BFMOPA 4,174 ns (502 MAC/ns); FMLA vgx4 4,174 ns; two cores of one DSU 8,909 ns for 8,192 (CME shared, no gain). Operands streamed: L1 1.017 ns per product, L2 1.19, L3 1.58, host-model DRAM 1.745. ZA store of 4 tiles 179 ns. SMSTART 0-1 ns, SMSTOP 3 ns. Gaps: two cores with memory operands, SLC/OCM operands, PRFM, DSU2-4, int8, real GEMM.
- dpa/stress (k_cme.S, kernels.h, counters.c, FORMAT.md section 6): Arm maxpwr half-matmul loop ported to EL0; Palladium Spokane requests 1504/1511 (2026-10-14/15): CME_OP_MMDP_ISSUE/CME_CYCLES 0.3455 (verbatim Arm loop, front-end bound at IPC 1.9) and 0.4916 (cme_fmopa_fit, near the 0.5 half-matmul ceiling). Core PMU raw events for the CME: 0x3246 CME_CYCLES, 0x3264 CME_OP_MMDP_ISSUE, 0x3261 CME_OP_MAC_ISSUE, 0x324B/0x324C CME_STALL_FRONTEND_*, 0x3213 CYCLES_CME_ALLOC, 0x835E SME_INST_SPEC, 0x8376 SME_FP_MOPA_SPEC, 0x837E SME_INT_MOPA_SPEC, 0x32A8 SSVE_CONTEXT_SWITCH. Build: `.arch armv9.3-a+sve2+sme+sme2`, GCC 14 of the asimov-os SDK.
- Report of this survey: ~/workspace/titan/cache-perf/asimov/cme-survey.html.

**Why:** The CME was already measured once; new work must extend, not repeat, and the stall-on-unarmed-PPU rule is a hard safety constraint for any SME test.
**How to apply:** Cite boots M2/M3 numbers as the baseline; add int8, SLC/OCM operands, 2-core memory operands, DSU2-4, a real GEMM. Related: [[asimov-run1-facts]], [[asimov-emulator-run-facts]], [[verify-other-agents]].
