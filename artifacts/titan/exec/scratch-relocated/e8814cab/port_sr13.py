import io, sys
A = 'ann/'
TRACE = ' With `--trace` these clock reads and this reading also store events in the trace.'
def sub(path, old, new, count=1):
    p = A + path
    t = io.open(p, encoding='utf-8').read()
    n = t.count(old)
    if n != count:
        print('PROBLEM %s: %d matches of %r' % (path, n, old[:60])); return
    io.open(p, 'w', encoding='utf-8').write(t.replace(old, new))
    print('changed %s: %s' % (path, old[:50]))
for v, k in (('11', 'bwx11-2026-11-15/bwx11.c.page.md'), ('13', 'bwx13-2026-11-15/bwx13.c.page.md')):
    sub(k, '- **History comment, marker lines**: each version of the runner puts a comment at the top of the file that lists its additions. Every addition of a version stands between two comment lines, for example `bwx%s+` and `bwx%s-`.' % (v, v),
           '- **History comment, marker lines**: from `bwx10` on, each version of the runner puts a comment at the top of the file that lists its additions. Every addition of such a version stands between two comment lines, for example `bwx%s+` and `bwx%s-`. The additions of `bwx8` have no such lines.' % (v, v))
    sub(k, '- Buffers: one private mapping per thread. The buffer starts at a 2 MiB boundary, and',
           '- Buffers: each buffer is a private mapping of its own, and no two threads share a buffer. A thread has one buffer, or two with `--two-buffers` or with a copy kernel in `--seq`. A buffer starts at a 2 MiB boundary, and')
sub('bwx11-2026-11-15/bwx11.c.page.md',
    'trials of prefix, predecessor and target windows with nothing but clock reads between the windows [Ref7].',
    'trials of prefix, predecessor and target windows [Ref7]. Between two windows lie only the store of the results of the window, the clock reads and, before a target window of a trial with the counter state `read`, one reading of the counter group and of the thread CPU time ({L1607-1610}, {L1587-1589}).' + TRACE)
sub('bwx10-2026-11-15/bwx10.c.page.md', 'one reading of the counter group and of the thread CPU time ({L1542-1545}, {L1522-1524}).',
    'one reading of the counter group and of the thread CPU time ({L1542-1545}, {L1522-1524}).' + TRACE)
sub('bwx8-2026-11-14/bwx8.c.page.md', 'one reading of the counter group and of the thread CPU time ({L1366-1369}, {L1346-1348}).',
    'one reading of the counter group and of the thread CPU time ({L1366-1369}, {L1346-1348}).' + TRACE)
