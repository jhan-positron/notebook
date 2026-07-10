# asimov-spec-study artifacts

Preserved copies of distilled-knowledge pages from the Asimov spec study
(project "Asimov spec study", cwd C:\Users\jibin\Documents\Asimov arch
claude on the local Windows machine DESKTOP-CI2JA7M). The canonical copies
live only on that machine's local disk — these mirrors exist to survive
accidental deletion. Repo copies are mirrors: edit the canonical file, not
these.

All three pages share one template and color convention (blue =
data/commands, copper = metadata, teal = CSRs/status) and read as a set:
SPM (memory access), SAL (command injection), SVL (configure/observe/
consume). All content is spec-cited, and **as of 2026-07-10 the SAL/SVL
pages plus the md model and SVG are RTL-cross-checked** against
`Positron-AI-TSMC/asimov @ main` (two 6-agent verification rounds);
corrections are applied inline with the RTL file named at each claim.

RTL ground truth (source of truth for all record layouts and maps):

- Record layout (`md_t`/`rd_t`/`gd_t`, 368/176/192 b):
  <https://github.com/Positron-AI-TSMC/asimov/blob/main/design/common/packages/mdata_pkg.sv>
  (the copy in `positron-ai/refmod_exp` is STALE — do not use)
- SPM RTL: <https://github.com/Positron-AI-TSMC/asimov/tree/main/design/spm/rtl>
  · registers: [spm.rdl](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/spm/registers/spm.rdl)
  · interface doc: [spm-cmn-if.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/spm/doc/spm-cmn-if.md)
- ACP delivery: [cmn_acp_mgr.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/rtl/cmn_acp_mgr.sv)
  (64 B slots: `{base22, acp_rd_addr, 6'b0}`, gd at +32)
- SPA: [cmn_spa.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/rtl/cmn_spa.sv)
  · [cmn_spa_pkg.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/packages/cmn_spa_pkg.sv)
  · [cmn_spa.rdl](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/registers/cmn_spa.rdl)
  · [cmn-spa-concept.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/docs/cmn-spa-concept.md)
- SAL: [rtl tree](https://github.com/Positron-AI-TSMC/asimov/tree/main/design/sls/sal/rtl)
  · [sal_pkg.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/packages/sal_pkg.sv)
  · [sal_csr.rdl](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/sal/registers/sal_csr.rdl)
  · [sal_cmd.h](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/sal/sw/sal_cmd.h) (SW ABI + builders)
  · [sls_sal_uarch.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/doc/sls_sal_uarch.md)
  · [sls_sal_SW_Programming_Guide.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/doc/sls_sal_SW_Programming_Guide.md)
- SVL: [rtl tree](https://github.com/Positron-AI-TSMC/asimov/tree/main/design/sls/svl/rtl)
  · [svl_pkg.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/packages/svl_pkg.sv)
  · [svl_csr.rdl](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/svl/registers/svl_csr.rdl)
  · [sls_svl_uarch.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/doc/sls_svl_uarch.md)
- SSA (SLS↔SPM adapter): [ssa.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/ssa/rtl/ssa.sv)
  · [spm_mdata_write_adapter.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/ssa/rtl/spm_mdata_write_adapter.sv)
  · [spm_mdata_read_adapter.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/sls/ssa/rtl/spm_mdata_read_adapter.sv)
- FSR: [fsr_concept.md](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/docs/fsr_concept.md)
  · [cmn_fsr_main.rdl](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/css/cmn/registers/cmn_fsr_main.rdl)
- Address map: [hra_addr_map_pkg.sv](https://github.com/Positron-AI-TSMC/asimov/blob/main/design/common/packages/hra_addr_map_pkg.sv)
  (SAL 4 MB @ 0x2040_0000, SVL 4 MB @ 0x2080_0000, SPM 4 KB @ 0x2003_1000
  — the docx "0x233000–0x237000" summarized map is stale)

## spm-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/spm-c1nano-software-view.html
  (also published as claude.ai artifact
  https://claude.ai/code/artifact/7d842ce5-1cc9-43e5-8286-063efa75e69c)
- What it is: the C1-Nano software view of SPM — memory-mapped 16 MiB data
  memory path (CMN 4x AXI4), push-only ACP metadata delivery (RG data =
  Routing + Generated), AXI4-Lite register path, formats and word/address
  sizes, what is transparent to software, and the spec gaps.
- Caveat (2026-07-10): this page predates the RTL cross-check — its
  register-window claim (0x234000) inherits the stale docx map (RTL:
  4 KB @ 0x2003_1000), and its ACP-slot/queue details are refined by the
  md model below. The SAL page carries the correction note.

## sal-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/sal-c1nano-software-view.html
  (artifact https://claude.ai/code/artifact/6c47a9c4-3b1a-4044-940e-b04048f8a75a)
- What it is: the C1-Nano -> CMN -> SAL command path with the SAL Packet
  Assembler (SPA) as centerpiece: 20 single-owner 4 KB partitions, slot
  mechanics (4 x 128 b, slot-3 trigger, template reuse), the real 8-type
  command enum (CPS_ROUT_CMD = bare 176 b rd_t; only CPS_WEIGHTS bypasses
  the queues), HP 4096 / LP 1024 queues, FSR pacing (17 counters + 4
  depth mirrors, preset-and-poll-for-zero idiom). RTL-cross-checked:
  SPA is THE command path (docx 4.4's AXI-Lite = HRA register chain);
  SAL command bit format published (489-bit sal_cmd_t via sal_cmd.h).

## svl-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/svl-c1nano-software-view.html
  (artifact https://claude.ai/code/artifact/567beab8-1167-4e45-8c26-385784864811)
- What it is: C1-Nano's three indirect surfaces onto SVL — configure
  (CSR list now fully published in svl_csr.rdl: topk 7 b @0x20 reset 8,
  LPA/clamp/softcap write-only table windows), observe (FSR SVL Results
  Counter, SAL-sourced mirror), consume (generated data as the +32 ACP
  write). RTL-cross-checked: attention K-pass writes only EMem but the
  V-pass (ATTN_SM_V) DOES write SPM + Σz/max generated data; 14 opmodes;
  SVL→SSA/SPM path has no backpressure; software-contract gotchas
  (0xDEADBEEF write-only windows, silent top-k drop corner) flagged.

## spm-meta-data-model.md + spm-meta-data-structure.svg

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/
- What they are: the GOLD-model data-structure definition of SPM metadata
  (md_t = rd_t 176 b + gd_t 192 b, quoted verbatim from the RTL
  mdata_pkg.sv) with docx↔RTL deltas table and citation list, plus the
  datasheet-style register diagram (rd_t 4-row bitfield, gd_t union,
  64 B ACP slot, queue/memory flow). Both RTL-verified 2026-07-10.

- Related handoff:
  handoffs/claude_20260706-20260710_asimov-c1-nano-spm-architecture.md
