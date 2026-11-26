# Render given PDF pages (1-based) to PNG at 110 dpi.
import fitz, sys
d = fitz.open(sys.argv[1])
for pg in sys.argv[3:]:
    d[int(pg)-1].get_pixmap(dpi=110).save("%s/page%04d.png" % (sys.argv[2], int(pg)))
