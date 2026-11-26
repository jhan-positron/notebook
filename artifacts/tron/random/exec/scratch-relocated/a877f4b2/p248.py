import sys, fitz, pymupdf4llm
doc = fitz.open(sys.argv[1]); md = pymupdf4llm.to_markdown(doc, pages=[247], show_progress=False)
print(md)
