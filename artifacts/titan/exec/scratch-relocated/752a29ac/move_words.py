"""Move the "Words used here" section of crb-memory-hierarchy.html to just after "Open items".

Moves the lines unchanged, moves the matching contents entry, and turns the three
"below" pointers inside the section into "above". Stops on any unexpected layout.
"""
import os
import shutil

BASE = '/home/jhan/workspace/titan/cache-perf/crb'
P = f'{BASE}/crb-memory-hierarchy.html'
BAK = f'{BASE}/tmp/crb-memory-hierarchy.before-move-words.html'

raw = open(P, 'rb').read()
lines = raw.decode('utf-8').split('\n')


def one(needle):
    hits = [i for i, l in enumerate(lines) if l == needle]
    assert len(hits) == 1, (needle, hits)
    return hits[0]


# 1. The section: heading, <dl>, one <dt>/<dd> row per line, </dl>, then one blank line.
h = one('<h2 id="words-used-here">Words used here</h2>')
end = one('</dl>')
assert lines[h - 1] == '' and lines[h + 1] == '<dl>' and end > h and lines[end + 1] == ''
block = lines[h:end + 1]
assert all(l.startswith('<dt>') and l.endswith('</dd>') for l in block[2:-1]), 'unexpected row in the list'

# 2. Pointers that say "below": the sections they name sit above the list after the move.
FIX = [
    ('Cycle counts below are ns multiplied by 2.8.', 'Cycle counts above are ns multiplied by 2.8.'),
    ('See "Cache ways" below.', 'See "Cache ways" above.'),
    ('See "The mesh cache and the pair port" below.', 'See "The mesh cache and the pair port" above.'),
]
joined = '\n'.join(block)
assert joined.count('below') == len(FIX), joined.count('below')
for old, new in FIX:
    assert joined.count(old) == 1, old
    joined = joined.replace(old, new)
assert 'below' not in joined
block = joined.split('\n')

# 3. Cut the section and its trailing blank line from the top.
del lines[h:end + 2]
assert lines[h - 1] == '' and lines[h].startswith('<h2 id="the-hierarchy-at-a-glance">')

# 4. Paste it between the end of "Open items" and the next heading.
nxt = one('<h2 id="when-the-runs-happened">When the runs happened</h2>')
oi = one('<h2 id="open-items">Open items</h2>')
assert lines[nxt - 1] == '' and lines[nxt - 2] == '</ul>' and oi < nxt
assert not any(l.startswith('<h2') for l in lines[oi + 1:nxt]), 'another section sits between'
lines[nxt:nxt] = block + ['']

# 5. Contents list: same move.
toc = one('<li><a href="#words-used-here">Words used here</a></li>')
entry = lines.pop(toc)
toc_oi = one('<li><a href="#open-items">Open items</a></li>')
assert lines[toc_oi + 1] == '<li><a href="#when-the-runs-happened">When the runs happened</a></li>'
lines.insert(toc_oi + 1, entry)

out = '\n'.join(lines).encode('utf-8')
assert len(out) == len(raw), (len(out), len(raw))  # "below" and "above" have the same length

assert not os.path.exists(BAK), 'backup name already taken'
shutil.copy2(P, BAK)
assert open(BAK, 'rb').read() == raw
with open(P, 'wb') as f:  # in place: keeps owner and mode
    f.write(out)
print('moved; backup at', BAK)
