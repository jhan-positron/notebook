# Closer edits, round 9: the Insufficient-data block of 3.1 names the rows, not the place of the line.
import io
P = '/home/jhan/workspace/titan/cache-perf/asimov/cme_page/sec_glance.py'
s = io.open(P, encoding='utf-8').read()
old = ' from the CME L1 on {F2N}) '
new = ' in the CME L1 rows of {F2N}) '
assert s.count(old) == 1
io.open(P, 'w', encoding='utf-8').write(s.replace(old, new))
print('applied 1')
