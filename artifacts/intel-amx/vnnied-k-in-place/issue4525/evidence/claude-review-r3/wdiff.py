import re, sys, difflib
def words(p):
    t = open(p, encoding='utf-8').read()
    t = t.replace('’',"'").replace('“','"').replace('”','"').replace('—','-').replace('–','-').replace('·','.')
    t = re.sub(r'<[^>]*>', '', t)  # drop link targets from my converter
    t = re.sub(r'\{#[^}]*\}|\[#[^\]]*\]', '', t)
    t = re.sub(r'[|#\-]{2,}', ' ', t)
    return re.findall(r'\S+', t)
a, b = words(sys.argv[1]), words(sys.argv[2])
sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
n_del = n_ins = 0
for tag, i1, i2, j1, j2 in sm.get_opcodes():
    if tag == 'equal': continue
    old = ' '.join(a[i1:i2]); new = ' '.join(b[j1:j2])
    if tag in ('delete','replace'): n_del += i2-i1
    if tag in ('insert','replace'): n_ins += j2-j1
    ctx = ' '.join(b[max(0,j1-6):j1])
    print('=== %s @old %d / new %d  (...%s)' % (tag.upper(), i1, j1, ctx))
    if old: print('  OLD: ' + old)
    if new: print('  NEW: ' + new)
print('\nTOTAL words: old %d new %d, deleted %d inserted %d' % (len(a), len(b), n_del, n_ins), file=sys.stderr)
