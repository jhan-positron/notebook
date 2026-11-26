#!/usr/bin/env python3
"""scan_default.py [PREFIX...] - rows of Bash lines with ${X:-value} that say "set" and not "empty" (main session)."""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl
m = lbl.manifest()
pre = sys.argv[1:]
n = 0
for key, e in sorted(m.items()):
    if 'same_as' in e or (pre and not any(key.startswith(p) for p in pre)):
        continue
    errs = []
    own, seed, parts = lbl.load_ann(key, errs)
    merged = dict(seed); merged.update(own)
    src = lbl.source_lines(e['src'])[0]
    for i, l in enumerate(src, 1):
        if re.search(r'\$\{!?\w+:-', l) and i in merged:
            low = merged[i].lower()
            if re.search(r'(has set|is set|was set|sets the variable|set by the caller|caller set|not set|unset|has not set)', low) and 'empty' not in low:
                n += 1
                print('%s|%d|%s|%s' % (key, i, 'own' if i in own else 'seed', merged[i]))
print('%d rows' % n, file=sys.stderr)
