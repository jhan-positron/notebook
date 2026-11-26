# Extract text of every page of the CMN S3 TRM to pages/pNNNN.txt (1-based PDF page index).
import fitz, sys, os
pdf, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
d = fitz.open(pdf)
for i, p in enumerate(d):
    open(os.path.join(out, "p%04d.txt" % (i+1)), "w").write(p.get_text())
print("pages", len(d))
