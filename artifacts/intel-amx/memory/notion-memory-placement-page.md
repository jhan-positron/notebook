---
name: notion-memory-placement-page
description: "Notion sub-page (2026-08-26) placing TLB/caches/page tables/pages/hugepage pool into core/SRAM/RAM, plus tron's hugepage use; source + generator archived in the workspace"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8553858a-bc1b-4656-abdc-adc2b759702a
  modified: 2026-08-27T01:41:54.571Z
---

Notion page "Where it lives: TLB entries, caches, page tables, pages, hugepages — core / SRAM / RAM":
https://app.notion.com/p/3c9d132d3cfd811f8164e3181f1c2415 — child of "Modern data-load path"
(3c5d132d3cfd8171b572dbbccb08e3b5). Two HTML-embed figures (C: placement; D: tron hugepage lanes).

Source archived at ~/workspace/intel-AMX/tmp/notion-hugepage-page/ (build_figs.py regenerates the
figures; page.md is the page body; 3bda-capture.txt holds the raw measurements).

Facts established while building it (delphi-3bda, 2026-08-26):
- 5-level paging is ACTIVE (la57, CONFIG_X86_5LEVEL=y, mmap hint 2^48 honoured).
- 6962P TLBs (CPUID 0x18): L1 load DTLB 96x4K / 32x2M / 8x1G; store TLB 16 any size; STLB = 1024 (4K/2M) + 1024 (4K/1G).
- Hugepage pool 512x1 GiB (256/node), all held by rinzler's 8 slice files; HugePages_Free counts pages no hugetlbfs FILE holds (pages stay with the file after the process exits).
- tron: KV books, embedding table (q_tokens btensor), DMA buffers live in the pos hugepage heap; quantized weights only pass through to HBM; K-mirror arena is operator new (4 KB pages).

Figure-building method that worked: SVG generator in Python, measure text with PIL + DejaVu (cairosvg's fallback font, wider than system fonts) and fail on overflow; upload HTML via notion-create-file-upload + curl; embed with `<embed src="file-upload://...">caption</embed>`. Related: [[svg-render-check]], [[amx-tron-softattn-project]].
