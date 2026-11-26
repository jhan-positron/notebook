import sys, fitz, pymupdf4llm, re
doc = fitz.open(sys.argv[1]); md = pymupdf4llm.to_markdown(doc, pages=[247], show_progress=False)
print("ligature glyphs in local page-248 md:", {ch: md.count(ch) for ch in "ﬁﬂﬀﬃﬄ" if md.count(ch)})
for m in re.finditer(r".{0,50}This .{0,60}", md): print("  ...", repr(m.group(0)))
