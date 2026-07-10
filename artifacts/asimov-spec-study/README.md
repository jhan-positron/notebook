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
consume). All content is spec-cited; each page carries its own open-items
/ spec-gaps list.

## spm-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/spm-c1nano-software-view.html
  (also published as claude.ai artifact
  https://claude.ai/code/artifact/7d842ce5-1cc9-43e5-8286-063efa75e69c)
- What it is: the C1-Nano software view of SPM — memory-mapped 16 MiB data
  memory path (CMN 4x AXI4), push-only ACP metadata delivery (RG data =
  Routing + Generated), AXI4-Lite register path, formats and word/address
  sizes, what is transparent to software, and the spec gaps (record
  packing placeholders, endianness unstated).

## sal-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/sal-c1nano-software-view.html
  (artifact https://claude.ai/code/artifact/6c47a9c4-3b1a-4044-940e-b04048f8a75a)
- What it is: the C1-Nano -> CMN -> SAL command path with the SAL Packet
  Assembler (SPA) as centerpiece: 20 single-owner 4 KB partitions, slot
  mechanics (4 x 128 b, slot-3 trigger, template reuse), the three command
  families, CPS half-slots, HP/LP queues, FSR pacing; flags the CMN spec
  4.4-vs-12 command-path contradiction.

## svl-c1nano-software-view.html

- Canonical: DESKTOP-CI2JA7M:C:/Users/jibin/Documents/Asimov arch claude/svl-c1nano-software-view.html
  (artifact https://claude.ai/code/artifact/567beab8-1167-4e45-8c26-385784864811)
- What it is: C1-Nano's three indirect surfaces onto SVL — configure (CSRs
  at HRA 0x237000, top-k k <= 8), observe (FSR SVL Results Counter),
  consume (generated data as the +32 ACP write, topk_gd_t/attn_gd_t
  bit-exact from refmod_exp mdata_pkg.sv); notes the attention/EMem blind
  spot and the unpublished SVL CSR list.

- Related handoff:
  handoffs/claude_20260706-20260710_asimov-c1-nano-spm-architecture.md.
  Companion (not preserved here): spm-meta-data-model.md and
  spm-meta-data-structure.svg in the same canonical folder.
