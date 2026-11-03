# 05: Docs and specs

## Which Asimov documents govern

The **Asimov Architecture Spec** and the documents linked in its **section 1.2, "Links to Related
Asimov Content"**, are the governing Asimov documents. They win over any other document, including
copies, archive, "Retired", "DRAFT" and Bronze versions of the same doc, which you should ignore. The
live Google Doc is the true version. The local snapshot under `/home/jgeldbach/dev/docs/asimov/` is a
2026-10-06 export and may be stale. The live section 1.2 is the master list; this table was copied
on 2026-10-06.

| Document | Live | Local snapshot under `/home/jgeldbach/dev/docs/asimov/` |
|---|---|---|
| Asimov Architecture Spec | https://docs.google.com/document/d/173ihNJW6B-BSV5m1v4pxQd6IZq42MC7_YOlDmTkTU7Q | `Asimov_Arch_Spec.docx` |
| Asimov Interface Spec | https://docs.google.com/document/d/15RZfIG3BqMtV8X-jhO1CDf4qoJGwxTYHVUp8wdB9nCw | `Asimov_Interface_Spec.docx` |
| Asimov Power, Timing, Clock & Reset Spec | https://docs.google.com/document/d/1LaT_9sDoiIJ29x6jAWUHYLpELNPGIlehz4i6DkPR3vw | `PTCR/AsimovPowerTimingClockAndResetSpecificationSilver.docx` |
| Asimov Drawings (Asimov-Arch tab) | https://lucid.app/lucidchart/20fdcbdb-2e19-4b4e-a3d2-d3e189b64a65/edit | none |
| **CMN: Arm Coherent Mesh Network (most relevant)** | https://docs.google.com/document/d/1QErHoAreoEQ7S9J9Tk8mtatuulwolT4dRHA9j5d5gzI | `CMN/CMN_uArch_Spec.docx` |
| CPS: Command Processing Subsystem | https://docs.google.com/document/d/1jF94xS4DphyhIlv9VB2vNgEUFCZzcJFnmV4Mc0urN7Y | `CPS/Command Processing Subsystem Micro‑Architecture Specification.docx` |
| TWS: TransWarp Subsystem | https://docs.google.com/document/d/1H4Squ4RuLJmVJim4vqgv75FmJBSVA0Jo4WF2BOy00mM | `TransWarp/TWS Microarchitecture.docx` |
| XMS: External Memory Subsystem | https://docs.google.com/document/d/10tp-vufzxLopq9CKg6SnaSkIWLd5Xm5I8OdTpMm9TcY | `XMS/External Memory Subsystem Microarch.docx` |
| SLS: Streaming Logic Subsystem | https://drive.google.com/file/d/1zAOeu_O6xXx1GGxyiHdZDGcH-WkIJoJz | `SLS/streaming_logic_subsystem_uarchitecture.docx` |
| SPM: Scratch Pad Memory | https://docs.google.com/document/d/195P6Qy00LKtRAV8opFuzimRsDPFiXBJqefABWBXn7JM | `SPM (Scratch Pad Memory Manager)/SPM Subsystem Micro‑Architecture Specification.docx` |
| C2C: Chip-to-Chip Subsystem | https://docs.google.com/document/d/1Xv5vaSmzH1m-9XAlPXAOrgvMAN4ACnFkFT_9gEmeduE | `C2C/C2C_uArch_Spec.docx` |
| PCIe Wrapper Microarchitecture Spec | https://docs.google.com/document/d/1DtVr8dqgk4IquMNBssPXCoMQxW3A0MXjv6oC_Cqs4ME | none |
| PLL control uArch (car_top) | https://docs.google.com/document/d/1taZ4llrEl_iHwlRiPAryFnor9B81g9kHMK9s9zMncWc | `PTCR/PLL control uArch.docx` |
| Asimov Corners Specification | https://docs.google.com/document/d/17lTDCeBh9Fj5A8vQdgRWe4XUojYay0xuVHa7p2hPNCM | `Corners/Asimov Corners Specification.docx` |

**In the CMN uArch spec, read** §3.3.4 "CME Coprocessing Support" (how the CMEs use the mesh) and
§6.1.2 "Nodes within the Mesh" (SLC and OCM in the five HN-S nodes). Those section numbers are from
the 2026-10-06 copy. Check them against the live doc.

**What section 1.2 doesn't cover** (as far as we found): the CME PMU events, `RPRFM`, the CME
prefetcher, the OCM window layout and locked SLC ways, and the boot. For those we used the Arm TRMs
below, asimov-scp-firmware `scp-v0.40.0`, asimov-address-map 0.6.0 (`profiles/sam_map.yaml`) and the
RTL in Positron-AI-TSMC/asimov. When the RTL and a doc disagree, report both sides.

## Arm references

All under `/home/jgeldbach/dev/docs/ARM/ARM_IP/`. That's on the shared `/home`, readable from
agentsrv, sw-dev-01 and alpha. Read PDFs with `pdftotext -layout <file> -`. Page numbers below are
the manual's own.

| Manual (file under `ARM_IP/`) | Sections that matter for CME performance |
|---|---|
| **Arm C1-SME2 TRM** 107831 issue 0103_07 — `C1/arm_c1_scalable_matrix_extension_2_technical_reference_manual_107831_0103_07_en.pdf` (use this issue; `..._0102_06_en.pdf` is older) | Technical overview, "L1 data memory system" (p.26-27: 64 KB L1D, prefetcher with 128 training streams); §6.3 Data prefetching (p.44-45: `RPRFM` up to 1024 B; `PRFM`/`PRFB..PRFD` are NOPs in streaming mode; the hardware prefetcher fills L1 and L3); ch.12 PMU events (§12.1 p.65, §12.2 IMPLEMENTATION DEFINED events p.73: `0x3246` `CME_CYCLES`, `0x3266`/`0x3268` bus reads, `0x3274`, `0x32AD`, `0x32B1`, `0x32B2`); appendix A.1.5 `IMP_CMECFG_EL1` (p.102-105: `PF_DISABLE` [28], `SW_PF_ADV` [33:32], arbitration fields, `ACTLR_EL3.CMEEN` access rule) |
| **Arm C1-SME2 Telemetry Specification** 109821 — `C1/arm_c1_scalable_matrix_extension_2_telemetry_specification_109821_0400_04_en.pdf` | §5.10 CME_Bus_Effectiveness (p.56), §5.11 CME_LL_Cache_Effectiveness (p.57), §5.13 CME_IQ_Effectiveness (p.68), **§5.15 CME_Prefetcher_Effectiveness** (p.73: accuracy, coverage, timeliness formulas) |
| **Arm C1 DynamIQ Shared Unit TRM** 107804 — `C1/arm_c1_dynamiq_shared_unit_technical_reference_manual_107804_0003_06_en.pdf` | ch.16 PMU (§16.2 PMU events, p.244); A.1.5 `IMP_CLUSTERECTLR_EL1` (p.269-271: `DCC` [45:44], `DSFP` [42], `PFMTCH` [10:8]); A.2 cluster PMU registers (p.311 on); the CHI transaction tables (`Evict`, `WriteEvictOrEvict`, `PrefetchTgt`) |
| **Arm C1-Nano core TRM** 107753 — `C1/arm_c1_nano_core_technical_reference_manual_107753_0002_06_en.pdf` | §7.6 Data prefetching (p.82, the core's own); ch.17 PMU (p.122-166); A.4.23 `ACTLR_EL3` (p.328, where `CMEEN` is set); A.4.10 `IMP_CPUECTLR_EL1` (p.287) |
| **Arm Neoverse CMN-S3(AE) TRM** 107858 — `CMN-S3/arm_neoverse_cmn_s3(ae)_coherent_mesh_network_technical_reference_manual_107858_0203_05_en.pdf` | §3.1.8 memory region locking and §3.1.9 software-configurable On-Chip Memory (p.~291-292: how OCM is made from SLC ways); §4.8 HN-S POCQ Resource Allocation (p.337); §7.3 HN-F/HN-S PMU (§7.3.1 cache performance p.386, §7.3.6 event summary p.390); §7.6.3 SBSX PMU events (p.403); §7.12 occupancy and lifetime from PMU events (p.417); §8.3.9 HN-S registers (p.1006 on), §8.3.9.7 `cmn_hns_cfg_ctl` (bit 47 `rd_migrate_on_sfmiss`, p.~1019) |
| Arm CMN-S3(AE) Configuration and Integration Manual 107859 — `CMN-S3/arm_neoverse_cmn_s3ae_coherent_mesh_network_configuration_and_integration_manual_107859_0203_05_en.pdf` | Integration options, when you need them |
| Arm CoreLink DMA-350 TRM 102482 — `DMAcontrollers/arm_corelink_dma-350_controller_technical_reference_manual_102482_0000_04_en.pdf` | Only if you work on the DMA side of OCM-fed runs |
| Arm CME slides for Positron — `C1/Arm Compute Matrix  Engine (CME) Overview - Positron.pdf`, `C1/Arm_CME_Introduction - Positron.pdf` | A readable introduction before the TRM |
| Learn the Architecture: SME overview 109974 — `C1/learn_the_architecture_sme_overview_109974_0100_01_en.pdf` | SME/SME2 programming model (streaming mode, ZA) |

Notes:
- Arm's Q&A on the C1-SME2 (January 2026) is in `C1/ARM C1_SME2 Questions - Jan_*.docx`.
- `ARM_IP/DSU-120/` is the previous DSU generation, not the C1 DSU. Use 107804.
- Other folders under `/home/jgeldbach/dev/docs/ARM/` (Finance, Invoices, PO, Royalty, contracts)
  are confidential business documents and not needed for this work.

## Other useful Positron notes (lower precedence than section 1.2)

| Doc | What |
|---|---|
| `/scratch/jgeldbach/gdn-cme-datapath-2026-10-23.md` | GDN-on-CME data path notes: kernels, prefetch, DMA into OCM |
| `/scratch/jgeldbach/spm-ocm-dma.md` | Running log of the SPM/OCM DMA and OCM-fed GDN investigations |
| `/scratch/jgeldbach/gdn-cme-results-2026-10-23/README.md` | E3/E7/E9 and per-instruction CME results with raw logs |
| `/scratch/jgeldbach/env-setup-general/02-docs-and-rtl.md` | Where the RTL and docs are, and how to read them |
