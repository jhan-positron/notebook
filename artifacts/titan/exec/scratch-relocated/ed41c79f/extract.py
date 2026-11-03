import sys, fitz
for f in sys.argv[1:]:
    doc = fitz.open(f)
    with open(f.rsplit('.',1)[0] + '.txt', 'w') as out:
        for i, p in enumerate(doc):
            out.write(f"\n=== PAGE {i+1} ===\n" + p.get_text())
    print(f, len(doc), 'pages')
