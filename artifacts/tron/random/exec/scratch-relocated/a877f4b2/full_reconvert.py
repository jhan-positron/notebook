#!/usr/bin/env python3
import sys, time, fitz, pymupdf4llm
pdf, out = sys.argv[1], sys.argv[2]
t0 = time.time(); doc = fitz.open(pdf)
md = pymupdf4llm.to_markdown(doc, show_progress=False)
open(out, "w", encoding="utf-8").write(md)
print(f"done: pages={doc.page_count} chars={len(md):,} seconds={time.time()-t0:.0f} pymupdf4llm={pymupdf4llm.__version__}")
