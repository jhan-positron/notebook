#!/usr/bin/env python3
"""build_repo.py [--apply] - copy the CRB test code and test data into ai-proj/arm-crb.

Without --apply it only prints the plan (counts and sizes). With --apply it copies,
verifies every copy by sha256, and writes arm-crb/SOURCES.tsv.
It never deletes or changes a source file.
"""
import hashlib, os, re, shutil, sys

P = '/home/jhan/workspace/titan/cache-perf'
B = P + '/bench'
C = P + '/crb'
A = C + '/tmp/agent-scratch'
N = C + '/new-test-kernel'
R = C + '/results'
DST = '/home/jhan/workspace/ai-proj/arm-crb'

plan = {}       # dst (relative to DST) -> src (absolute)
skipped = []    # (reason, src)


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for blk in iter(lambda: f.read(1 << 20), b''):
            h.update(blk)
    return h.hexdigest()


def skip_reason(src):
    name = os.path.basename(src)
    if '__pycache__' in src.split('/') or name.endswith('.pyc'):
        return 'python cache'
    if name.endswith('.md') and os.path.exists(src[:-3]):
        return 'companion explanation file'
    if name.startswith('listing.loaded-latency-asct-'):
        return 'machine-code listing of the vendor binary (ASCT)'
    if os.path.islink(src):
        return 'symbolic link'
    with open(src, 'rb') as f:
        if f.read(4) == b'\x7fELF':
            return 'compiled binary'
    return None


def add(src, dst):
    assert os.path.isfile(src), src
    why = skip_reason(src)
    if why:
        skipped.append((why, src))
        return
    assert dst not in plan, 'two sources for ' + dst
    plan[dst] = src


def add_tree(srcdir, dstdir, prune=()):
    assert os.path.isdir(srcdir), srcdir
    for r, dirs, files in os.walk(srcdir):
        dirs[:] = sorted(d for d in dirs if d not in prune and d != '__pycache__')
        for x in sorted(files):
            s = os.path.join(r, x)
            add(s, os.path.join(dstdir, os.path.relpath(s, srcdir)))


def add_top(srcdir, dstdir, drop=lambda n: False):
    """Top-level regular files of a folder."""
    for x in sorted(os.listdir(srcdir)):
        s = os.path.join(srcdir, x)
        if os.path.isfile(s):
            if drop(x):
                skipped.append(('not code (log, picture or result page)', s))
            else:
                add(s, os.path.join(dstdir, x))


def not_code(n):
    return n.endswith(('.log', '.png', '.html', '.out')) or n == 'ssh-err.txt'


# ---------------------------------------------------------------- code
add_tree(B, 'code/bench')
add_top(A + '/cread-2026-11-12', 'code/cread-2026-11-12',
        drop=lambda n: not_code(n) or n.startswith(('k_cread.', 'probe-cread')))
add_top(A + '/kernels-2026-11-13', 'code/kernels-2026-11-13')
for x in ('run_partA.sh', 'visit.sh', 'session2.sh', 'fetch.sh', 'decide.py'):
    add(N + '/' + x, 'code/new-test-kernel/' + x)
for x in ('analyze_partA.py', 'make_partA_html.py', 'test_partA.py'):
    add(N + '/partA-analysis/' + x, 'code/new-test-kernel/partA-analysis/' + x)
for x in ('make_q1_html.py', 'make_q2_html.py', 'test_q1.py', 'test_q2.py', 'gen_s1.sh',
          'render_q1.sh', 'recount/recount_results_md.py'):
    add(N + '/partBC-analysis/' + x, 'code/new-test-kernel/partBC-analysis/' + x)
for d in ('bwx-2026-11-13', 'bwx8-2026-11-14', 'bwx10-2026-11-15', 'bwx11-2026-11-15',
          'bwx12-2026-11-15', 'bwx13-2026-11-15', 'w120-2026-11-15', 'asct-2026-11-16'):
    add_top(A + '/' + d, 'code/' + d, drop=not_code)
add_tree(A + '/asct-2026-11-16/crb', 'code/asct-2026-11-16/crb')
add_top(A + '/w120-2026-11-15/robsize', 'code/w120-2026-11-15/robsize', drop=not_code)
W = A + '/w120-7200-2026-11-17'
for x in ('go.sh', 'go2.sh', 'ra.sh', 'like.spec', 'cfwd.spec', 'crev.spec', 'stat_k120.py',
          'stat_bwx.py', 'build_facts.py', 'facts_data.py', 'facts_text.py', 'facts_text4.py',
          'make_report.py', 'test_make_report.py'):
    add(W + '/' + x, 'code/w120-7200-2026-11-17/' + x)
add(N + '/manual-run/run.sh', 'code/manual-run/run.sh')

# ---------------------------------------------------------------- tests
GROUPS = [
    ('2026-10-30-memory-hierarchy',
     r'^(20261030T193108Z|followup[23]?-.*|slc-.*|uncore2?-.*|sudo-.*|cmn-map\.txt|'
     r'dmidecode-t17-2026-10-30\.txt|map|map_1|probe-20261111T210017Z\..*)$'),
    ('2026-11-13-cread', r'^cread-'),
    ('2026-11-13-new-read-kernel',
     r'^(kernels-2026.*|partA-.*|SHORT-.*|B\d+[ab]?-2026.*|C\d-2026.*|partBC-.*|partB-s1-analysis.*)$'),
    ('2026-11-15-tackle-8mb', r'^(bwx(8|9|10|11)-.*|h2-.*)$'),
    ('2026-11-15-whole-chip-read-drop', r'^w120-R'),
    ('2026-11-16-asct-cross-check', r'^asct-'),
    ('2026-11-17-firmware-and-dimm',
     r'^(w120-(X1|X2|BASE).*|fwtest-.*|dimm.*|uefisettings-.*|w120-w120-F72.*)$'),
    ('2026-11-17-whole-chip-7200', r'^(go2?-T72-.*|k120-T72.*|w120-T72.*)$'),
]
count = {g: 0 for g, _ in GROUPS}
for e in sorted(os.listdir(R)):
    hit = [g for g, rx in GROUPS if re.search(rx, e)]
    assert len(hit) == 1, (e, hit)
    g = hit[0]
    count[g] += 1
    s = os.path.join(R, e)
    if os.path.isdir(s):
        add_tree(s, 'tests/%s/%s' % (g, e))
    else:
        add(s, 'tests/%s/%s' % (g, e))

T = 'tests/2026-10-30-memory-hierarchy/'
for x in ('crb-memory-hierarchy.html', 'crb-memory-hierarchy-brief.html', 'perf-measurement-tech.html',
          'plan-2026-11-02.md'):
    add(C + '/' + x, T + 'report/' + x)

T = 'tests/2026-11-13-cread/'
for x in ('k_cread.round2.md', 'cread-result.round2.html', 'probe-cread.txt'):
    add(A + '/cread-2026-11-12/' + x, T + 'report/' + x)

T = 'tests/2026-11-13-new-read-kernel/'
for x in ('plan.md', 'handoff.md', 'decisions.md', 'results.md'):
    add(N + '/' + x, T + 'report/' + x)
for x in sorted(os.listdir(N)):
    if re.match(r'^(partA-(short|long)\.log|visit-s[12]-.*\.log|session2\.log|session[12]-folders\.txt)$', x):
        add(N + '/' + x, T + 'logs/' + x)
add_tree(A + '/bwx-2026-11-13/crb-build-1', T + 'build-records/bwx-crb-build-1')
add_tree(A + '/bwx-2026-11-13/crb-build-2', T + 'build-records/bwx-crb-build-2')

T = 'tests/2026-11-15-tackle-8mb/'
for x in ('tackle-8mb.md', 'tackle-8mb-handoff.md', 'tackle-8mb-progress.md', 'tackle-8mb-results.md',
          'tackle-8mb-report.html', 'tackle-8mb-report-easy-read.html'):
    add(N + '/' + x, T + 'report/' + x)
for x in sorted(os.listdir(N)):
    if re.match(r'^visit(8|9|10|11|-h2)-.*\.log$', x):
        add(N + '/' + x, T + 'logs/' + x)
for v in ('bwx8-2026-11-14', 'bwx10-2026-11-15', 'bwx11-2026-11-15'):
    add_tree(A + '/' + v + '/crb-build-1', T + 'build-records/%s-crb-build-1' % v.split('-')[0])

T = 'tests/2026-11-15-whole-chip-read-drop/'
for x in ('whole-chip-read-drop.html', 'whole-chip-read-drop-easy-read.html'):
    add(N + '/' + x, T + 'report/' + x)
for x in sorted(os.listdir(A + '/w120-2026-11-15')):
    if x.endswith('.log'):
        add(A + '/w120-2026-11-15/' + x, T + 'logs/' + x)
add_tree(A + '/w120-2026-11-15/robsize/results', T + 'robsize-results')
add_tree(A + '/bwx13-2026-11-15/crb-build-1', T + 'build-records/bwx13-crb-build-1')

T = 'tests/2026-11-16-asct-cross-check/'
add(N + '/ASCT-cross-check.html', T + 'report/ASCT-cross-check.html')
for x in sorted(os.listdir(A + '/asct-2026-11-16')):
    if x.endswith('.log'):
        add(A + '/asct-2026-11-16/' + x, T + 'logs/' + x)

T = 'tests/2026-11-17-whole-chip-7200/'
for x in ('local.sha', 'go2.sha', 'baselines-and-rules.txt'):
    add(W + '/' + x, T + 'launch-records/' + x)
add_tree(A + '/bwx12-2026-11-15/crb-build-1', T + 'build-records/bwx12-crb-build-1')
for x in ('partA-A1/threads120.csv', 'partA-A3-onebuf500/threads120.csv'):
    add(W + '/base8000/' + x, T + 'baseline-8000/' + x)
for x in ('FACTS.md', 'facts.json'):
    add(W + '/' + x, T + 'report/' + x)
add(N + '/whole-chip-rerun-7200.html', T + 'report/whole-chip-rerun-7200.html')

# ---------------------------------------------------------------- report / apply
def summary():
    by = {}
    for d, s in plan.items():
        k = '/'.join(d.split('/')[:2])
        n, z = by.get(k, (0, 0))
        by[k] = (n + 1, z + os.path.getsize(s))
    tot_n = tot_z = 0
    for k in sorted(by):
        n, z = by[k]
        tot_n += n
        tot_z += z
        print('%6d files %9.2f MB  %s' % (n, z / 1e6, k))
    print('%6d files %9.2f MB  total' % (tot_n, tot_z / 1e6))
    print('result entries per test:', count, 'sum', sum(count.values()))
    why = {}
    for w, s in skipped:
        why[w] = why.get(w, 0) + 1
    print('left out:', why)
    big = max(plan.values(), key=os.path.getsize)
    print('largest file: %.2f MB %s' % (os.path.getsize(big) / 1e6, big))


summary()
if '--skipped' in sys.argv:
    for w, s in skipped:
        if w not in ('companion explanation file', 'python cache'):
            print(w, '|', s.replace(P + '/', ''))
if '--apply' in sys.argv:
    rows = []
    for d in sorted(plan):
        s = plan[d]
        t = os.path.join(DST, d)
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.copy2(s, t)
        a, b = sha(s), sha(t)
        assert a == b, 'copy differs: ' + d
        assert os.stat(s).st_mode & 0o111 == os.stat(t).st_mode & 0o111, 'mode differs: ' + d
        rows.append('%s\t%s\t%d\t%s\n' % (d, s.replace(P + '/', ''), os.path.getsize(t), a))
    with open(os.path.join(DST, 'SOURCES.tsv'), 'w') as f:
        f.write('repo_path\tsource_path\tbytes\tsha256\n')
        f.writelines(rows)
    print('copied and verified:', len(rows), 'files')
