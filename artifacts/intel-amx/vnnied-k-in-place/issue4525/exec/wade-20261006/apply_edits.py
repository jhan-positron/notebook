# Apply exact string replacements (JSON list of {old,new}) to a file; report misses and multi-hits.
import json, sys
fn, ed = sys.argv[1], json.load(open(sys.argv[2]))
t = open(fn).read(); miss = []; multi = []
for e in ed:
    n = t.count(e['old'])
    if n == 0: miss.append(e['old'][:70]); continue
    if n > 1: multi.append((n, e['old'][:60]))
    t = t.replace(e['old'], e['new'], 1)
open(fn, 'w').write(t)
print(f"{fn}: applied {len(ed)-len(miss)} of {len(ed)}; missed {miss}; multi {multi}")
