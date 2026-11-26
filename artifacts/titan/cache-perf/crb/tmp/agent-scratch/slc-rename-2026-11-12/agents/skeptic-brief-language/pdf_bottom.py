#!/usr/bin/env python3
"""Bottom of the real content of each page of a printed brief PDF (text and small drawings only). Usage: pdf_bottom.py <pdf>..."""
import sys, fitz
MM = 25.4 / 72
for path in sys.argv[1:]:
    d = fitz.open(path)
    print(path.split('/')[-1], '| pages:', len(d))
    for i, p in enumerate(d):
        words = p.get_text('words')
        tb = max(w[3] for w in words)
        last = [w for w in words if abs(w[3] - tb) < 2]
        dr = [x['rect'] for x in p.get_drawings() if x['rect'].height < 0.8 * p.rect.height]
        db = max((r.y1 for r in dr), default=0)
        bottom = max(tb, db)
        usable_bottom = p.rect.height - 11 / MM
        print(f'  page {i + 1}: last text bottom {tb * MM:.1f} mm ("{" ".join(w[4] for w in sorted(last, key=lambda w: w[0]))[:70]}"); last drawing bottom {db * MM:.1f} mm; '
              f'usable area ends at {usable_bottom * MM:.1f} mm; free {(usable_bottom - bottom) * MM:.1f} mm = {(usable_bottom - bottom) * MM / 25.4 * 96:.0f} px')
