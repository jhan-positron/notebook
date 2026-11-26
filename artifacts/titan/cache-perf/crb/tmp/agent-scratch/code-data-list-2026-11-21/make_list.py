#!/usr/bin/env python3
"""make_list.py - writes crb/new-test-kernel/whole-chip-test-code-data-list.md.

The list names every code file, function and data file of the whole-chip rerun of 2026-11-17, in calling order.
Function names, line numbers and call sequences are read from the checked overview files in ann/ (never typed here).
The script stops when a listed file or its companion does not exist, when a function is not in its overview,
when an introduction has 15 words or more, or when a line of the text diagram is longer than 70 columns.

Usage: python3 make_list.py [--check]      --check: build and test, write nothing
Python 3 standard library only.
"""
import glob
import json
import os
import re
import sys

sys.dont_write_bytecode = True
T = os.path.dirname(os.path.abspath(__file__))
C = os.path.normpath(os.path.join(T, '..', '..', '..'))
OUT = os.path.join(C, 'new-test-kernel', 'whole-chip-test-code-data-list.md')
OUTDIR = os.path.dirname(OUT)
R = os.path.join(C, 'results')
S = os.path.join(C, 'tmp', 'agent-scratch', 'w120-7200-2026-11-17')
K13 = os.path.join(C, 'tmp', 'agent-scratch', 'kernels-2026-11-13')
BWX12 = os.path.join(C, 'tmp', 'agent-scratch', 'bwx12-2026-11-15')
W15 = os.path.join(C, 'tmp', 'agent-scratch', 'w120-2026-11-15')
RECORD = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/405492c8-bb52-418d-ab08-c4ac8ac9980e.jsonl'

RECORD13 = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb/7663f0d2-7d09-4571-b80c-92526358fa86.jsonl'
RECORD24 = '/home/jhan/.claude/projects/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/cf95f96f-fe0e-4464-9ebe-3b1a78f78771.jsonl'
GOEDIT = os.path.join(C, 'tmp', 'agent-scratch', 'go-edit-2026-11-24')
# The message edit of 2026-11-24 (line 2245 of RECORD24, instruction of the user in line 2153; file time of go.sh 20:35:43 UTC):
# line 20 of go.sh, GO_OLD_LINE20 became GO_NEW_LINE20. LOCAL_SHA_SHA256 is the sha256 of the unchanged file local.sha.
GO_OLD_LINE20 = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"'
GO_NEW_LINE20 = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"'
LOCAL_SHA_SHA256 = 'dce73e4e22dd068e78806142d3a0a1b4bb54eaf4ba5e5b7012fdb0d6a9c2ab26'
# The comment edit of 2026-11-13 18:32:07 UTC (line 1000 of RECORD13): BW_OLD_COMMENT became BW_NEW_COMMENT.
BW_OLD_COMMENT = """ * In k_copy it keeps all 16 loads ahead of the 16 stores. The statement adds
 * no instruction.
"""
BW_NEW_COMMENT = """ * The statement adds no instruction. It does not fix the order of the loads
 * and the stores of k_copy: gcc may move code across it. Observed with gcc
 * 14.2.0 and the Makefile flags: with the statement, k_copy has its 8 ldp
 * ahead of its 8 stp, as k_asmcopy has; without it, loads and stores
 * alternate.
"""

MAN = {e['key']: e for e in json.load(open(os.path.join(T, 'manifest.json')))['files']}
OV = {k: json.load(open(os.path.join(T, 'ann', k + '.overview.json'))) for k in MAN}
STATS = dict(files=0, companions=0, intros=0, functions=0)


def die(msg):
    sys.exit('make_list.py: ERROR: ' + msg)


def crb(path):
    return os.path.relpath(path, C)


def href(path):
    return os.path.relpath(path, OUTDIR)


def words(text):
    return len(re.sub(r'[`*]', '', text).split())


def intro(text):
    if words(text) >= 15:
        die('introduction with %d words (limit: fewer than 15): %s' % (words(text), text))
    STATS['intros'] += 1
    return text


def item(path, text, show=None, companion=True):
    """One list entry: link to the file, link to its companion, introduction."""
    if not os.path.exists(path):
        die('missing file ' + path)
    STATS['files'] += 1
    comp = ''
    if companion:
        if not os.path.isfile(path + '.md'):
            die('missing companion ' + path + '.md')
        STATS['companions'] += 1
        comp = ' ([explained](%s))' % href(path + '.md')
    return '[`%s`](%s)%s: %s' % (show or crb(path), href(path), comp, intro(text))


def code(key, show=None):
    """Entry of a code or listing file of the manifest. The introduction is the checked "role" of its overview."""
    return item(MAN[key]['path'], OV[key]['role'].strip().rstrip('.') + '.', show)


def fline(key, name):
    """Line of the definition of a function, from the overview of key: its function table first, then its call sequence."""
    hits = [f['line'] for f in OV[key]['functions'] if f['name'] == name or f['name'].endswith(': function ' + name)]
    if not hits:
        hits = sorted({c['line'] for c in OV[key].get('call_sequence', []) if c['name'] == name and c.get('line')})
    if len(hits) != 1:
        die('function %s: %d matches in the overview of %s' % (name, len(hits), key))
    src = open(MAN[key]['path']).read().split('\n')
    if name not in '\n'.join(src[hits[0] - 1:hits[0] + 2]) and name[2:] not in src[hits[0] - 1]:
        die('line %d of %s does not show %s' % (hits[0], MAN[key]['path'], name))
    return hits[0]


def fn(key, name):
    """`name` (line N) of a function of the overview of key."""
    STATS['functions'] += 1
    return '`%s` (line %d)' % (name, fline(key, name))


def callseq(key, indent='  ', maxdepth=None):
    """The checked call sequence of the overview, as a nested list."""
    out = []
    for c in OV[key].get('call_sequence', []):
        if maxdepth is not None and c['depth'] > maxdepth:
            continue
        where = ' (line %d)' % c['line'] if c.get('line') else ''
        out.append('%s%s- `%s`%s: %s' % (indent, '  ' * c['depth'], c['name'], where, intro(c['note'].strip())))
        STATS['functions'] += 1
    if not out:
        die('no call sequence in the overview of ' + key)
    return out


def folded(summary, lines, pad='  '):
    return [pad + '<details>', pad + '<summary>%s</summary>' % summary, ''] + lines + ['', pad + '</details>', '']


def srcline(path, n):
    """Line n of a source file (1-based), without the line end."""
    return open(path).read().split('\n')[n - 1]


def need(path, n, text):
    """Stop unless line n of the file holds the text. Guards the line numbers that are typed in this script."""
    if text not in srcline(path, n):
        die('%s line %d does not hold %r' % (path, n, text))
    return n


def find_line(path, text, nth=1):
    """Number of the nth line of the file that starts with the text."""
    hits = [i for i, l in enumerate(open(path).read().split('\n'), 1) if l.startswith(text)]
    if len(hits) < nth:
        die('%s: no line %d that starts with %r' % (path, nth, text))
    return hits[nth - 1]


def check_two_texts():
    """The two texts of bandwidth.c: stop unless the local text with the comment edit reversed has the recorded sha256."""
    import hashlib
    path = MAN['bandwidth']['path']
    src = open(path).read()
    if src.count(BW_NEW_COMMENT) != 1:
        die('bandwidth.c: the comment lines of the edit of 2026-11-13 are not in the local text')
    first = src[:src.index(BW_NEW_COMMENT)].count('\n') + 1
    if (first, first + 4) != (178, 182):
        die('bandwidth.c: the edited comment lines are %d to %d' % (first, first + 4))
    old = hashlib.sha256(src.replace(BW_NEW_COMMENT, BW_OLD_COMMENT).encode()).hexdigest()
    rec = srcline(os.path.join(R, 'kernels-20261113T181222Z', 'probe.txt'), 15).split()[0]
    if old != rec or not rec.startswith('c1406e02') or not hashlib.sha256(src.encode()).hexdigest().startswith('f1985072'):
        die('bandwidth.c: the reversed text has sha256 %s, the record of the first test has %s' % (old, rec))
    if 'In k_copy it keeps all 16 loads ahead of the 16 stores' not in open(RECORD13).read():
        die('the session record of 2026-11-13 does not hold the comment edit')


def check_two_texts_go():
    """The two texts of go.sh: stop when a tested statement of the open point "Two texts of go.sh" no longer holds.

    Tested: the text of line 20, both sha256 values, the file local.sha, go2.sh against go2.sha, the lines of the two
    session records, the lines of the notes about Jeremy, the place of check 20 in build_facts.py and in facts.json,
    and the stored output of the two tests of [Ref9]. Not tested: the copy on CRB. The tests of [Ref9] are not run here.
    """
    import hashlib
    sha = lambda b: hashlib.sha256(b).hexdigest()
    src = open(MAN['go']['path'], 'rb').read().decode()
    if src.split('\n')[19] != GO_NEW_LINE20 or src.count(GO_NEW_LINE20) != 1:
        die('go.sh: line 20 is not the line of the edit of 2026-11-24')
    raw = open(MAN['local_sha']['path'], 'rb').read()
    if sha(raw) != LOCAL_SHA_SHA256:
        die('local.sha is not the list of 2026-11-17 any more')
    listed = [l.split()[0] for l in raw.decode().splitlines() if l.split()[1:] == ['go.sh']]
    old = sha(src.replace(GO_NEW_LINE20, GO_OLD_LINE20).encode())
    if listed != [old] or not old.startswith('75bc50b0') or not sha(src.encode()).startswith('d68cf6c0'):
        die('go.sh: with the old line 20 put back the sha256 is %s, local.sha lists %s' % (old, listed))
    # session record of 2026-11-17: line 295 wrote go.sh (the text that local.sha lists), line 310 shows the test on CRB
    rec = open(RECORD).read().split('\n')
    cmd = [c['input']['command'] for c in json.loads(rec[294])['message']['content'] if c.get('type') == 'tool_use'][0]
    m = re.search(r"cat > go\.sh <<'EOF'\n(.*?\n)EOF\n", cmd, re.S)
    if not m or sha(m.group(1).encode()) != old:
        die('line 295 of the session record of 2026-11-17 does not hold the go.sh text that local.sha lists')
    if 'go.sh: OK' not in rec[309]:
        die('line 310 of the session record of 2026-11-17 does not hold "go.sh: OK"')
    # session record of the edit: line 2153 is the instruction of the user, line 2245 is the edit
    rec = open(RECORD24).read().split('\n')
    ask, edit = json.loads(rec[2152]), json.loads(rec[2244])
    said = ask['message']['content'] if ask.get('type') == 'user' else ''
    if not (isinstance(said, str) and said.startswith('`%s` in go.sh changes to `%s`' % (GO_OLD_LINE20, GO_NEW_LINE20))):
        die('line 2153 of the session record of the edit does not hold the instruction of the user')
    calls = [c['input'] for c in edit['message']['content'] if isinstance(c, dict) and c.get('type') == 'tool_use' and c.get('name') == 'Edit']
    if [(c['file_path'], c['old_string'], c['new_string']) for c in calls] != [(MAN['go']['path'], GO_OLD_LINE20, GO_NEW_LINE20)]:
        die('line 2245 of the session record of the edit does not hold the edit of go.sh line 20')
    # go2.sh was not edited: it has the sha256 of go2.sha, and lines 16 and 25 hold the old message
    g2 = open(os.path.join(S, 'go2.sha')).read().split()
    if g2[1:] != ['go2.sh'] or sha(open(MAN['go2']['path'], 'rb').read()) != g2[0] or not g2[0].startswith('38edfa54'):
        die('go2.sh does not have the sha256 that go2.sha lists')
    need(MAN['go2']['path'], 16, 'fail "RUNNING file present"')
    need(MAN['go2']['path'], 25, 'fail "RUNNING file present"')
    # the notes about Jeremy [Ref8]
    notes = os.path.join(C, 'jeremy-plan-constraints-2026-10-30.md')
    need(notes, 12, 'a reserved whole-host window in which Jeremy runs measurements')
    need(notes, 13, '`/tmp/positron-perf.RUNNING`, present for the whole block')
    # check 20 of the facts sheet is the check with the key sha-local (build_facts.py lines 772 to 780)
    bf = MAN['build_facts']['path']
    need(bf, 773, "for f in ('local.sha', 'go2.sha'):")
    need(bf, 777, "bad = [n for n, h in listed.items() if fd.sha256(os.path.join(S, n)) != h]")
    need(bf, 778, "chk('sha-local'")
    if [c['key'] for c in json.load(open(os.path.join(S, 'facts.json')))['meta']['checks']].index('sha-local') + 1 != 20:
        die('facts.json: the check sha-local is not check 20')
    # the kept tests of the edit [Ref9]: the scripts, the copy of the older text, and the stored output of two tests
    for name in ('common.py', 'check_line20.py', 'check_facts_build.py'):
        if not os.path.isfile(os.path.join(GOEDIT, name)):
            die('go-edit-2026-11-24/%s is missing' % name)
    if sha(open(os.path.join(GOEDIT, 'go.sh.as-run-2026-11-17'), 'rb').read()) != old:
        die('go-edit-2026-11-24/go.sh.as-run-2026-11-17 does not have the sha256 that local.sha lists')
    wanted = {'check_line20.out': ['PASS with the old line 20 put back in memory, the text of the local go.sh has the listed sha256'],
              'check_facts_build.out': ['PASS run 1 ends with status 1 and the stop message', 'PASS run 1 changes nothing in the copied run folder',
                                        'PASS run 2 ends with status 0 and prints "checks: 27, failed: 0"']}
    for name, lines in wanted.items():
        out = open(os.path.join(GOEDIT, name)).read().strip().split('\n')
        if out[-1] != 'ALL PASS' or any(l.startswith('FAIL') for l in out) or not all(any(l.startswith(w) for l in out) for w in lines):
            die('go-edit-2026-11-24/%s: the stored output of the test is not a pass' % name)


def one(pattern):
    hits = sorted(glob.glob(pattern))
    if len(hits) != 1:
        die('%d matches for %s' % (len(hits), pattern))
    return hits[0]


def count(path, regex):
    rx = re.compile(regex)
    with open(path) as f:
        return sum(1 for l in f if rx.search(l))


def diagram(lines):
    for l in lines:
        if len(l) > 70:
            die('diagram line longer than 70 columns: ' + l)
    return ['```text'] + lines + ['```']


def result_tables():
    """Section 6: the final rates. Computed from facts.json and compared with the raw csv files.

    Part A: one row per session and round (rule V3 of baselines-and-rules.txt: no pooled range for bw_new read).
    Part C: the kernel `read` is grouped by the kernel that ran directly before it (rule V2).
    The script stops when a value from the records of facts.json differs from the value that the raw csv gives.
    """
    import statistics
    sys.path.insert(0, S)
    import stat_bwx
    import stat_k120
    facts = json.load(open(os.path.join(S, 'facts.json')))
    iv = facts['intervals']
    parts = facts['verdicts']['q1_parts']

    def q1(part, group=None):
        q = [x for x in parts if x['part'].split(' ')[0] == part and x['group'] == group]
        if len(q) != 1:
            die('result table: %d rows of q1_parts for part %s group %s' % (len(q), part, group))
        return q[0]

    def drop(part, group=None):
        q = q1(part, group)
        return '%.1f to %.1f (%s)' % (q['smallest_drop_pct'], q['largest_drop_pct'], q['n'].split(':')[0])

    # ---- part A: medians per process
    raw = {}
    for folder in sorted(glob.glob(os.path.join(R, 'k120-T72A[123]-*'))):
        session = int(re.search(r'k120-T72A(\d)-', folder).group(1))
        for pr in stat_k120.load(folder):
            if pr['kernel'] == 'read':
                key = (session, pr['round'], pr['binary'])
                if key in raw:
                    die('result table: two processes for ' + str(key))
                raw[key] = [x[0] for x in pr['iv']]
    ta = ['| Session | Round | `bw_old`, kernel `read`: median, GB/s | `bw_new`, kernel `read`: median, GB/s | New below old, % |', '|---|---|---|---|---|']
    drops = []
    for session in (1, 2, 3):
        for rnd in (1, 2):
            med = {}
            for binary in ('bw_old', 'bw_new'):
                v = [x['GBps'] for x in iv if x['dataset'] == 'rerun-A' and x['kernel'] == 'read' and x['binary'] == binary
                     and x['session'] == session and x['round'] == rnd]
                r = raw.get((session, rnd, binary), [])
                if len(v) != 3 or sorted(round(x, 2) for x in v) != sorted(round(x, 2) for x in r):
                    die('result table: part A session %d round %d %s: facts.json %s, raw csv %s' % (session, rnd, binary, v, r))
                med[binary] = statistics.median(v)
                STATS['checked'] = STATS.get('checked', 0) + 1
            d = (1 - med['bw_new'] / med['bw_old']) * 100
            drops.append(d)
            ta.append('| %d | %d | %.2f | %.2f | %.1f |' % (session, rnd, med['bw_old'], med['bw_new'], d))
    qa = q1('A')
    if abs(min(drops) - qa['smallest_drop_pct']) > 0.011 or abs(max(drops) - qa['largest_drop_pct']) > 0.011:
        die('result table: part A drops %.3f to %.3f, facts.json %s to %s' % (min(drops), max(drops), qa['smallest_drop_pct'], qa['largest_drop_pct']))

    # ---- bwx12 parts
    def rng(ds, tags, kernel, pattern, before=None):
        recs = [x for x in iv if x['dataset'] == ds and x['kernel'] == kernel and x['binary'] == 'bwx12' and (tags is None or x['tag'] in tags)]
        if before and any(x['kernel_before'] != before for x in recs):
            die('result table: %s %s: a record is not directly after %s' % (ds, kernel, before))
        v = [x['GBps'] for x in recs]
        r = []
        for folder in sorted(glob.glob(os.path.join(R, pattern))):
            r += [x['total'] for x in stat_bwx.interval_rows(folder) if x['kernel'] == kernel]
        if not v or (round(min(v), 2), round(max(v), 2), len(v)) != (round(min(r), 2), round(max(r), 2), len(r)):
            die('result table: %s %s %s: facts.json and the raw csv differ' % (ds, tags, kernel))
        STATS['checked'] = STATS.get('checked', 0) + 1
        return '%.2f to %.2f (%d intervals)' % (min(v), max(v), len(v))

    used = '`asmread`, used in place of the new read kernel: '
    tb = ['| Part | Group | Old read kernel (`oldread`): total rate, GB/s | New read kernel: total rate, GB/s | Below `oldread`, % |', '|---|---|---|---|---|']
    tb.append('| C | `read` directly after `oldread` (`cfwd.spec`: T72C1, T72C3) | %s | `read`: %s | %s |' % (
        rng('rerun-C', ('T72C1', 'T72C3'), 'oldread', 'w120-T72C[13]-*'),
        rng('rerun-C', ('T72C1', 'T72C3'), 'read', 'w120-T72C[13]-*', 'oldread'), drop('C', 'read after oldread')))
    tb.append('| C | `read` directly after `asmread` (`crev.spec`: T72C2, T72C4) | %s | `read`: %s | %s |' % (
        rng('rerun-C', ('T72C2', 'T72C4'), 'oldread', 'w120-T72C[24]-*'),
        rng('rerun-C', ('T72C2', 'T72C4'), 'read', 'w120-T72C[24]-*', 'asmread'), drop('C', 'read after asmread')))
    tb.append('| L | all 3 processes | %s | %s%s | %s |' % (
        rng('rerun-L', None, 'oldread', 'w120-T72L[123]-*'), used, rng('rerun-L', None, 'asmread', 'w120-T72L[123]-*'), drop('L')))
    tb.append('| Control I | both processes | %s | %s%s | %s |' % (
        rng('control-I', None, 'oldread', 'w120-T72I[12]-*'), used, rng('control-I', None, 'asmread', 'w120-T72I[12]-*'), drop('I')))
    return ta, tb, '%.1f to %.1f (%s)' % (qa['smallest_drop_pct'], qa['largest_drop_pct'], qa['n'].split(':')[0])


def main():
    o = []
    w = o.append

    w('# Whole-chip read test at 7200 MT/s: list of test code and test data')
    w('')
    w('## Short version')
    w('')
    w('- This list names the source files, the functions of the call sequences and the data files of the whole-chip read test that ran on CRB (an Arm reference server with 128 CPUs) on 2026-11-17, in calling order.')
    w('- Each linked file has a companion file that explains it: the same name plus `.md`, in the same folder.')
    w('- The old read kernel (the old inner loop of the benchmark that reads memory) is the function `k_read` in `bandwidth.orig.c` and `k_oldread` in `bwx12.c`, and the new read kernel is `k_read` in `bandwidth.c` and `k_read` in `bwx12.c`.')
    w('')
    w('<details>')
    w('<summary>Words used here</summary>')
    w('')
    for term, text in WORDS:
        w('- **%s**: %s' % (term, text))
    w('')
    w('</details>')
    w('')

    w('## 1. How to read this list')
    w('')
    w('- Every path of a listed file is relative to the folder `crb`, which is `/home/jhan/workspace/titan/cache-perf/crb`. A path that starts with `~/cache-perf/` is a path on CRB. Three files lie outside `crb`: the session records [Ref3], [Ref6] and [Ref7].')
    w('- A path is a link to the file. The word "explained" after it is a link to the companion file.')
    w('- The companion of a code file shows the source at the left and the explanation at the right.')
    w('- The companion of a data file explains its rows and columns.')
    w('- The number after a function name is the line of its definition in the source file. For an entry that is a script, a command of a script (for example `sha256sum -c`) or a block of statements (for example `main: rate loop`), it is the line where that script, command or block starts.')
    w('- A note that starts with "line N:" or "Lines N to M:" gives the lines of the calls in the same source file.')
    w('- The call sequences and the line numbers are those of the sections "Call sequence in the whole-chip test" and "Functions" of each companion. The script `%s` copied them into this list from the same checked data. For `ra.sh` and `rx.sh` this list shows the first two levels only. The deeper levels are in the two companions and in the sections of the C files.' % crb(os.path.join(T, 'make_list.py')))
    kb, ko, bx = MAN['bandwidth']['path'], MAN['bandwidth_orig']['path'], MAN['bwx12']['path']
    for path, lines in ((ko, (177, 201, 225)), (kb, (301, 325, 349)), (bx, (622, 992))):
        for n in lines:
            need(path, n, '__asm__ volatile(')
    need(kb, 205, '__asm__ volatile(""')
    need(bx, 522, '__asm__ volatile(""')
    w('- No separate assembly file exists. The hand-written loops are inline assembly (`__asm__` statements) inside the C files: `k_asmread`, `k_asmwrite` and `k_asmcopy` in `bandwidth.orig.c` and in `bandwidth.c`, and in `bwx12.c` the macro `DEF_ASMREAD` (kernels `asmread`, `read_nop96`, `read_nop256`) and the function `k_read_1pl`.')
    w('- The old and the new read kernel are C text. `k_read` of `bandwidth.c` (line 205) and of `bwx12.c` (line 522) holds one `__asm__` statement with an empty instruction text. It adds no instruction to the loop.')
    w('- The test ran on CRB under `~/cache-perf/`. The table gives the folder on CRB for each local folder.')
    w('')
    w('| Local folder (below `crb/`) | Folder on CRB (below `~/cache-perf/`) | What it holds |')
    w('|---|---|---|')
    w('| `tmp/agent-scratch/w120-7200-2026-11-17` | `w120-7200-20261117` | run scripts and spec files of the rerun (copied to CRB, section 3.1), and the analysis scripts (they ran on the agent server) |')
    w('| `tmp/agent-scratch/kernels-2026-11-13` | `scratch-kernels-20261113` | old and new benchmark source. On CRB also the binaries `bw_old` and `bw_new` |')
    w('| `tmp/agent-scratch/bwx12-2026-11-15` | `bwx12-20261115` | source and build script of the runner `bwx12`. On CRB also the binary `bwx12` and the build records |')
    w('| `tmp/agent-scratch/bwx12-2026-11-15/crb-build-1` | `bwx12-20261115` (no sub-folder on CRB) | copies of the build records that `build12.sh` wrote on CRB |')
    w('| `tmp/agent-scratch/w120-2026-11-15` | `w120-20261115` | the runner script `rx.sh` |')
    w('| `results` | `results` | result folders, copied back after the run |')
    w('')
    w('- The folders on CRB are named in `go.sh`, `ra.sh` and the copy commands of section 3.1 [Ref3].')
    w('- The three binaries are not in the local folders. Their sha256 values are in the records of section 4.8.')
    w('')

    w('## 2. Calling sequence in one diagram')
    w('')
    for l in diagram(DIAGRAM):
        w(l)
    w('')
    w('- The diagram is schematic. Section 3 gives the files and functions of each step.')
    w('- "old" marks the code of the old read kernel. "new" marks the code of the new read kernel.')
    w('- The `bwx12` lines of the diagram do not name every kernel. Part C also runs `k_asmread`. Part L and control I also run three test loops (section 3.4).')
    w('- `<s>` is the session number, 1 to 3. `<i>` is 1 or 2.')
    w('- `T72A<s>`, `T72L<s>`, `T72C<s>` and `T72I<i>` are the names of the steps. Each result folder carries the name of its step and its start time (UTC), for example `k120-T72A1-20261117T221209Z`.')
    w('- Part C uses `cfwd.spec` in sessions 1 and 3. It uses `crev.spec` in session 2 and in the extra process `T72C4`.')
    w('')

    w('## 3. Test code, in calling order')
    w('')
    w('### 3.1 Commands of the agent server (no script file)')
    w('')
    w('No script holds these commands. The record of the Claude Code session of 2026-11-17 holds them [Ref3]. That record lies outside the project folder.')
    w('')
    w('1. Line 309 of the record writes `local.sha` on the agent server. It copies `go.sh`, `ra.sh`, the three spec files and `local.sha` to CRB with `tar` over `ssh`. On CRB, `sha256sum -c local.sha` checks the copied files.')
    w('   - This step did not copy `rx.sh` or the three binaries. They were already on CRB.')
    w('   - `go.sh` checks `rx.sh` and `bwx12` by sha256 before use (lines %d and %d). `ra.sh` checks `bw_old` and `bw_new` (lines 16 to 20).' % (
        need(MAN['go']['path'], 22, 'sha256sum'), need(MAN['go']['path'], 23, 'sha256sum')))
    need(MAN['ra']['path'], 16, 'sha256sum -c')
    w('   - The local `go.sh` is not the copied text any more. The message of its line 20 was changed on 2026-11-24 (section 7). In the local folder, `sha256sum -c local.sha` now prints `go.sh: FAILED`.')
    w('2. Line 313 starts the driver on CRB: `nohup setsid ~/cache-perf/w120-7200-20261117/go.sh > $L 2>&1 < /dev/null &`. `L` is the log file `~/cache-perf/results/go-T72-<time>.log`. The companion of `go.sh` explains each part of this command (section "Behavior a reader must know").')
    w('3. Line 339 copies the log and the result folders of parts A, L and C back with `tar` over `ssh`.')
    w('4. Line 353 writes `go2.sh` and `go2.sha`. It copies both to CRB. On CRB, `sha256sum -c go2.sha` checks the copy.')
    w('5. Line 365 starts `go2.sh` in the same way, with the log `go2-T72-<time>.log`.')
    w('6. Line 377 copies the log of `go2.sh` and the two result folders of control I back.')
    w('')

    w('### 3.2 The driver `go.sh`')
    w('')
    w('- ' + code('go'))
    w('  - The local file and its companion show the text of 2026-11-24. It differs from the text that ran in the message of line 20 only (section 7).')
    w('  - Call sequence:')
    for l in callseq('go', '    '):
        w(l)
    w('')

    w('### 3.3 Part A: `ra.sh`, then `bw_old` (old code) and `bw_new` (new code)')
    w('')
    w('- ' + code('ra'))
    w('  - Call sequence:')
    for l in callseq('ra', '    ', maxdepth=1):
        w(l)
    w('- Old code: ' + code('bandwidth_orig'))
    w('  - Call sequence of one `bw_old` process:')
    for l in callseq('bandwidth_orig', '    '):
        w(l)
    w('- New code: ' + code('bandwidth'))
    w('  - Call sequence of one `bw_new` process:')
    for l in callseq('bandwidth', '    '):
        w(l)
    w('')
    w('Old code and new code of part A, step by step:')
    w('')
    w('| Step | Old code | New code |')
    w('|---|---|---|')
    w('| Binary | `bw_old` | `bw_new` |')
    w('| Source file | `bandwidth.orig.c` | `bandwidth.c` |')
    for label, name in (('Entry point', 'main'), ('One thread', 'worker'), ('First touch of the buffer', 'k_write'),
                        ('One pass over the buffer', 'pass'), ('Read kernel (kernel name `read`)', 'k_read'),
                        ('Hand-written loop (kernel name `asmread`)', 'k_asmread')):
        w('| %s | %s | %s |' % (label, fn('bandwidth_orig', name), fn('bandwidth', name)))
    pr = MAN['kprobe']['path']
    heads = [i for i, l in enumerate(open(pr).read().split('\n'), 1) if l.startswith('=== ')]

    def psec(name):
        a = find_line(pr, '=== %s ===' % name)
        return 'section `%s`, lines %d to %d' % (name, a, heads[heads.index(a) + 1] - 1)
    w('| Machine code of `k_read` in `probe.txt` (section 4.8) | %s | %s |' % (psec('bw_old k_read'), psec('bw_new k_read')))
    w('')
    for n, text in ((136, '/*'), (137, 'History: k_read, k_write and k_copy'), (166, '*/'), (381, '/*'), (382, 'History: pass()'), (415, '*/')):
        need(kb, n, text)
    w('- `bandwidth.c` also holds the old `k_read`, `k_write` and `k_copy` (lines 136 to 166) and the old `pass` (lines 381 to 415). These lines are comments that start with the word "History". gcc does not compile them. `bw_new` runs the functions that the table names.')
    w('')

    w('### 3.4 Parts L and C: `rx.sh`, then `bwx12`')
    w('')
    w('- ' + code('rx'))
    w('  - Call sequence:')
    for l in callseq('rx', '    ', maxdepth=1):
        w(l)
    w('- Input of `rx.sh`, one argument line each:')
    w('  - ' + code('like_spec'))
    w('  - ' + code('cfwd_spec'))
    w('  - ' + code('crev_spec'))
    w('- ' + code('bwx12'))
    w('  - Call sequence of one `bwx12` process with these argument lines:')
    for l in callseq('bwx12', '    '):
        w(l)
    w('')
    w('Old code and new code inside `bwx12.c`:')
    w('')
    w('| Step | Old code | New code | Hand-written loop |')
    w('|---|---|---|---|')
    w('| Kernel name in `--seq` | `oldread` | `read` | `asmread` |')
    w('| Kernel function | %s | %s | %s |' % (fn('bwx12', 'k_oldread'), fn('bwx12', 'k_read'), fn('bwx12', 'k_asmread')))
    d_old = find_line(bx, '#define DEF_OLDREAD(name)')
    c_old = need(bx, fline('bwx12', 'k_oldread'), 'DEF_OLDREAD(oldread)')
    d_asm = find_line(bx, '#define DEF_ASMREAD(name, nops)')
    d_asm2 = find_line(bx, '#define DEF_ASMREAD(name, nops)', 2)
    c_asm = need(bx, fline('bwx12', 'k_asmread'), 'DEF_ASMREAD(asmread, 0)')
    c_n96 = need(bx, fline('bwx12', 'k_read_nop96'), 'DEF_ASMREAD(read_nop96, 96)')
    c_n256 = need(bx, fline('bwx12', 'k_read_nop256'), 'DEF_ASMREAD(read_nop256, 256)')
    r_start = fline('bwx12', 'k_read')
    r_end = min(i for i, l in enumerate(open(bx).read().split('\n'), 1) if i > r_start and l == '}')
    if not (d_old < c_old and d_asm < c_asm < d_asm2):
        die('bwx12.c: unexpected order of the macro lines')
    w('| Source text of the loop | macro `DEF_OLDREAD(name)`, lines %d to %d | body of `k_read`, lines %d to %d | macro `DEF_ASMREAD(name, nops)`, lines %d to %d |' % (
        d_old, c_old - 1, r_start, r_end, d_asm, c_asm - 1))
    w('| Called by | %s | %s | %s |' % ((fn('bwx12', 'call'),) * 3))
    w('| Runs in | parts L and C, control I | part C | parts L and C, control I |')
    w('| Machine code in `listing.txt` (section 4.8) | lines 133 to 205 | lines 1 to 16 | lines 59 to 82 |')
    w('')
    w('- Lines %d, %d, %d and %d are macro calls. Each call creates one kernel function. The loop text is in the macro.' % (c_old, c_asm, c_n96, c_n256))
    w('- Part L and control I also run three test loops: %s and %s, both made by the macro `DEF_ASMREAD`, and %s.' % (
        fn('bwx12', 'k_read_nop96'), fn('bwx12', 'k_read_nop256'), fn('bwx12', 'k_read_1pl')))
    for n, text in ((491, '#if defined(__aarch64__)'), (851, '#else'), (880, 'DEF_ASMREAD(read, 0)'), (881, 'DEF_ASMWRITE(write)'),
                    (883, 'DEF_ASMREAD(asmread, 0)'), (897, '#endif'), (1005, '#else'), (1014, 'k_read_1pl('), (1022, '#endif')):
        need(bx, n, text)
    if d_asm2 != 858:
        die('bwx12.c: second DEF_ASMREAD at line %d' % d_asm2)
    w('- `bwx12.c` also holds a second, plain C text of these loops for a machine that is not AArch64: a second macro `DEF_ASMREAD` (line 858), a second `k_read`, `k_write` and `k_asmread` (lines 880, 881 and 883) and a second `k_read_1pl` (line 1014). They are in the `#else` branches of lines 851 to 897 and 1005 to 1022. The CRB binary does not hold them. Line 2 of each of the 9 csv files that `bwx12` wrote in the test (sections 4.4 to 4.6) says `kernels=aarch64`.')
    bwx_csv = sorted(glob.glob(os.path.join(R, 'w120-T72[LCI]?-*', '*.csv')))
    if len(bwx_csv) != 9:
        die('%d csv files of bwx12' % len(bwx_csv))
    for f in bwx_csv:
        need(f, 2, 'kernels=aarch64')
    w('- The thread function of every kernel is %s. The entry point is %s.' % (fn('bwx12', 'worker'), fn('bwx12', 'main')))
    w('')

    w('### 3.5 Control I: `go2.sh`')
    w('')
    w('- ' + code('go2'))
    w('  - Call sequence:')
    for l in callseq('go2', '    '):
        w(l)
    w('')

    w('### 3.6 Build of the binaries (ran before the rerun)')
    w('')
    w('The rerun built nothing. These files built and tested the three binaries on 2026-11-13 and 2026-11-15.')
    w('')
    w('- Build of `bw_old` and `bw_new` (2026-11-13):')
    w('  - ' + code('run_kernels'))
    for l in folded('Call sequence of <code>run_kernels.sh</code>', callseq('run_kernels', '      '), pad='    '):
        w(l)
    recs = [('181210', '18:12:10', 'probe'), ('181222', '18:12:22', 'all'), ('183218', '18:32:18', 'probe')]
    for tag, hms, mode in recs:
        f = os.path.join(R, 'kernels-20261113T%sZ' % tag, 'probe.txt')
        need(f, 1, 'utc=2026-11-13T%sZ' % hms)
        need(f, 1, 'mode=' + mode)
        need(f, 20, 'fd7c14df')
        need(f, 15, 'f1985072' if tag == '183218' else 'c1406e02')
    need(MAN['run_kernels']['path'], 31, 'bw_old')
    need(MAN['run_kernels']['path'], 32, 'bw_new')
    need(MAN['ra']['path'], 18, 'fd7c14df')
    w('  - The folder `results` holds three records of `run_kernels.sh` of 2026-11-13: 18:12:10 UTC (mode `probe`), 18:12:22 UTC (mode `all`, the first test) and 18:32:18 UTC (mode `probe`). In mode `probe` the script builds the binaries, writes the machine code of the kernels to `probe.txt` and runs the self-test. It times nothing. In mode `all` it does the same and then runs the timed processes. Each run compiled `bw_old` and `bw_new` again (lines 31 and 32). The run of 18:32:18 UTC compiled the local text of `bandwidth.c` (sha256 `f1985072...`). It recorded the sha256 value `fd7c14df...` for `bw_new`. `ra.sh` checks this value before part A [Ref4].')
    w('  - ' + code('selftest'))
    w('  - ' + code('probe'))
    w('- Build of `bwx12` (2026-11-15):')
    w('  - ' + code('build12'))
    for l in folded('Call sequence of <code>build12.sh</code>', callseq('build12', '      '), pad='    '):
        w(l)
    w('  - ' + code('bwx12_selftest'))
    w('  - ' + code('check_listing12'))
    w('  - ' + code('test_kernels12'))
    w('')

    # ------------------------------------------------------------------ data
    w('## 4. Test data')
    w('')
    w('### 4.1 Where the old and the new read kernel are in the data')
    w('')
    w('| Part | File | Rows of the old read kernel | Rows of the new read kernel | Rate |')
    w('|---|---|---|---|---|')
    w('| A | `threads120.csv` | interval rows after a line `-- binary bw_old kernel read` | interval rows after a line `-- binary bw_new kernel read` | column `aggregate_GBps`: bytes of all threads / longest thread time / 1e9, in GB/s |')
    w('| L, control I | `a6456.csv` | rows with the kernel name `oldread` | no row. `asmread` is used in place of it [Ref2] | sum over the 120 T rows of one interval of (bytes / elapsed_s / 1e9), in GB/s |')
    w('| C | `cfwd.csv`, `crev.csv` | rows with the kernel name `oldread` | rows with the kernel name `read` | the same sum over the T rows |')
    w('')
    w('- GB = 1e9 bytes.')
    w('- No csv file of sections 4.3 to 4.6 holds the rows of one kernel only.')
    w('- Part A: each `threads120.csv` holds the 24 processes of one session. The old and the new read kernel run in separate processes (`bw_old` and `bw_new`). Each process starts with its own header line.')
    w('- Part C: the old and the new read kernel run in the same process.')
    w('- Part L and control I: the file holds rows of the old read kernel and of `asmread`. It holds no row of the new read kernel.')
    w('- One listed csv file holds one kernel only: `base8000/partA-A3-onebuf500/threads120.csv` (section 4.9) holds 3 processes of `bw_old`, kernel `read`.')
    w('- The companion of each csv file lists its intervals with the kernel and the rate.')
    w('')

    w('### 4.2 Logs of the two driver scripts')
    w('')
    w('- Folder: `results`')
    w('  - ' + code('go_log', 'go-T72-20261117T221209Z.log'))
    w('  - ' + code('go2_log', 'go2-T72-20261117T222335Z.log'))
    w('')

    sections = [('4.3 Part A: three sessions of `ra.sh`', 'k120', ['T72A1', 'T72A2', 'T72A3']),
                ('4.4 Part L: three sessions of `rx.sh` with `like.spec`', 'w120', ['T72L1', 'T72L2', 'T72L3']),
                ('4.5 Part C: four processes of `rx.sh` with `cfwd.spec` or `crev.spec`', 'w120', ['T72C1', 'T72C2', 'T72C3', 'T72C4']),
                ('4.6 Control I: two processes of `go2.sh`', 'w120', ['T72I1', 'T72I2'])]
    for title, prefix, tags in sections:
        w('### ' + title)
        w('')
        for tag in tags:
            folder = one(os.path.join(R, '%s-%s-*' % (prefix, tag)))
            w('- Folder: `%s`' % crb(folder))
            if prefix == 'k120':
                csv = os.path.join(folder, 'threads120.csv')
                np, ni = count(csv, r'^-- binary '), count(csv, r'^[a-z]+,\d+,\d+,\d+,')
                w('  - ' + item(csv, '%d processes of `bw_old` and `bw_new`, %d interval rows with rates.' % (np, ni), 'threads120.csv'))
                w('  - ' + item(os.path.join(folder, 'probe.txt'), 'Machine state before and after the session, sha256 of both binaries.', 'probe.txt'))
            else:
                csv = one(os.path.join(folder, '*.csv'))
                ni, nt = count(csv, r'^I,'), count(csv, r'^T,')
                seq = re.search(r'seq=(\S+)', open(csv).read(4000)).group(1)
                w('  - ' + item(csv, 'One `bwx12` process: %d intervals, %d thread rows, kernels `%s`.' % (ni, nt, seq), os.path.basename(csv)))
                w('  - ' + item(os.path.join(folder, 'env.txt'), 'Machine state before the process, sha256 of `bwx12`.', 'env.txt'))
                w('  - ' + item(os.path.join(folder, 'launches.txt'), 'Launch line with load and arguments, then the rc line.', 'launches.txt'))
                w('  - ' + item(os.path.join(folder, 'stderr.txt'), 'Error output of `bwx12`. Empty: 0 bytes.' if os.path.getsize(os.path.join(folder, 'stderr.txt')) == 0
                                 else 'Error output of `bwx12`. Not empty.', 'stderr.txt'))
        w('')

    w('### 4.7 Input files, rules and launch records')
    w('')
    w('- Folder: `%s`' % crb(S))
    w('  - The three spec files are listed in section 3.4.')
    w('  - ' + code('local_sha', 'local.sha'))
    w('    - The `go.sh` entry is the sha256 value of the text that ran. The local `go.sh` has another value since 2026-11-24 (section 7).')
    w('  - ' + code('go2_sha', 'go2.sha'))
    w('  - ' + item(os.path.join(S, 'baselines-and-rules.txt'), 'List of 8000 MT/s baselines and comparison rules, written before the run.', 'baselines-and-rules.txt'))
    w('')

    w('### 4.8 Records of the builds: compiler flags and machine code of the kernels')
    w('')
    w('- Folder: `%s`' % crb(os.path.dirname(MAN['kprobe']['path'])))
    w('  - ' + code('kprobe', 'probe.txt'))
    w('- Folder: `%s`' % crb(os.path.dirname(MAN['bwx12_listing']['path'])))
    w('  - ' + code('bwx12_buildtxt', 'build.txt'))
    w('  - ' + code('bwx12_listing', 'listing.txt'))
    w('  - ' + code('bwx12_offsets', 'offsets.tsv'))
    w('')

    w('### 4.9 Earlier data that the analysis compares with (8000 MT/s, and one 7200 MT/s sample)')
    w('')
    w('This test did not generate these files. They have no companion, except the two converted copies. The fixed list of baselines is in `baselines-and-rules.txt` (section 4.7). The facts sheet lists every file that the analysis opened [Ref1].')
    w('')
    w('| Row name | Folder below `results/` | What it is |')
    w('|---|---|---|')
    for row, folder, text in BASELINES:
        if not os.path.isdir(os.path.join(R, folder)):
            die('missing baseline folder ' + folder)
        for other in re.findall(r'folder: `([^`]+)`', text):
            if not os.path.isdir(os.path.join(R, other)):
                die('missing baseline folder ' + other)
        w('| %s | `%s` | %s |' % (row, folder, intro(text)))
    w('')
    seqs = []
    for pat in ('w120-R1-*/p1nop.csv', 'w120-R1-*/p2add.csv', 'w120-R5-*/thp.csv', 'w120-R6-*/st?.csv', 'w120-R0-2*/p?.csv', 'w120-R0b-*/c?.csv',
                'w120-X1d10-*/a6456.csv', 'w120-X1d10b-*/a6456.csv', 'w120-BASEd10-*/a6456.csv'):
        hits = sorted(glob.glob(os.path.join(R, pat)))
        if not hits:
            die('no file for ' + pat)
        for f in hits:
            seqs.append(len(re.search(r'seq=(\S+)', open(f).read(4000)).group(1).split(',')))
    w('- In rows L-2, L-3, L-4, R0, R0b, X1d10, X1d10b and BASEd10 the analysis uses only `oldread` at position 0 and `asmread` at position 1. These files hold more kernels (%d to %d per sequence).' % (min(seqs), max(seqs)))
    for pat, n_all, n_used in (('B7-*/B7.csv', 48, 8), ('C3-*/C3.csv', 18, 4), ('B5-*/B5.csv', 4, 4)):
        hits = sorted(glob.glob(os.path.join(R, pat)))
        if len(hits) != 2:
            die('%d files for %s' % (len(hits), pat))
        for f in hits:
            used = count(f, r'^-- step \S+ tag (common-6000-|b5-fwd-|b5-rev-)') if 'B5' in pat else count(f, r'^-- step \S+ tag common-6000-')
            if (count(f, r'^-- step '), used) != (n_all, n_used):
                die('%s: %d processes, %d used' % (f, count(f, r'^-- step '), used))
    w('- In rows B7a, B7b, C3a and C3b the analysis uses only the processes with a tag `common-6000-*`: 8 of the 48 processes of each `B7.csv` and 4 of the 18 processes of each `C3.csv`. The four B5 rows use all 4 processes of each `B5.csv`. In all eight rows the analysis keeps only the kernels `oldread`, `read` and `asmread`.')
    w('- Converted copies of rows A-2 and A-3. Their header lines have the format of `threads120.csv`:')
    p = os.path.join(S, 'base8000', 'partA-A1', 'threads120.csv')
    w('  - ' + item(p, '8000 MT/s data of 2026-11-13 (`A1.csv`) with rewritten header lines, %d processes.' % count(p, r'^-- binary ')))
    p = os.path.join(S, 'base8000', 'partA-A3-onebuf500', 'threads120.csv')
    if count(p, r'^-- binary ') != 3 or count(p, r'^-- binary bw_old kernel read ') != 3:
        die('partA-A3-onebuf500: not 3 processes of bw_old read')
    w('  - ' + item(p, 'The 3 `onebuf-ms500` processes of `A3.csv` (8000 MT/s, 2026-11-13) with rewritten header lines.'))
    rules = os.path.join(S, 'baselines-and-rules.txt')
    need(rules, 47, 'B=')
    need(rules, 50, 'sed -E')
    need(rules, 51, 'awk')
    need(rules, 53, 'grep -c')
    w('  - The `sed` and `awk` commands that wrote the two copies are in `baselines-and-rules.txt`, lines 47 to 53 (section 4.7). No script file holds them. The analysis reads the copies only for the cross-check with `stat_k120.py`. It takes the rates of rows A-2 and A-3 from the raw files `A1.csv` and `A3.csv`.')
    w('')

    # ------------------------------------------------------------------ analysis
    w('## 5. Analysis code: from the raw rows to the final throughput')
    w('')
    w('### 5.1 The path of one number')
    w('')
    w('Part A (binaries `bw_old` and `bw_new`):')
    w('')
    w('1. The binary computes the rate of one interval: bytes of all threads / longest thread time / 1e9. The code is in `main` of `bandwidth.orig.c` and of `bandwidth.c` (section 3.3). It prints the rate in the column `aggregate_GBps`.')
    w('2. `facts_data.py`: %s reads the interval rows.' % fn('facts_data', 'read_k120'))
    w('3. `build_facts.py`: %s makes one record per interval row.' % fn('build_facts', 'add_k120'))
    w('4. `facts_text.py`: %s pairs the old and the new process of the same session and round. %s takes the median of the 3 intervals of one process. `analyse` computes the drop of each pair as (1 - new median / old median) x 100.' % (fn('facts_text', 'analyse'), fn('facts_text', 'med')))
    w('5. `build_facts.py`: %s writes the records and the verdicts to `facts.json`. The verdicts hold the smallest and the largest drop of each part.' % fn('build_facts', 'write_json'))
    w('6. `make_report.py` reads `facts.json`. %s checks each record against its csv row. %s computes the drop between two process medians a second time. %s compares the smallest and the largest drop with section 3.4 of `FACTS.md`.' % (
        fn('make_report', 'file_process'), fn('make_report', 'a_pair'), fn('make_report', 'xc_drops')))
    w('')
    w('Parts L and C and control I (runner `bwx12`):')
    w('')
    w('1. `bwx12.c`: %s prints one I row per interval and one T row per thread (bytes and elapsed time of the thread).' % fn('bwx12', 'main'))
    w('2. `facts_data.py`: %s reads the rows. %s sums bytes / elapsed_s / 1e9 over the T rows of each interval.' % (fn('facts_data', 'read_bwx'), fn('facts_data', 'bwx_intervals')))
    w('3. `build_facts.py`: %s makes one record per interval with this sum as its rate.' % fn('build_facts', 'add_bwx'))
    w('4. `facts_text.py`: %s pairs the old-kernel interval and the load-only interval of one process and round. It computes the drop of each pair as (1 - new / old) x 100.' % fn('facts_text', 'pairs'))
    w('5. `build_facts.py`: %s writes the records and the verdicts to `facts.json`.' % fn('build_facts', 'write_json'))
    w('6. `make_report.py`: %s sums the T rows of the raw csv again. %s computes each drop a second time. %s compares the smallest and the largest drop with section 3.4 of `FACTS.md`.' % (
        fn('make_report', 'val'), fn('make_report', 'drop'), fn('make_report', 'xc_drops')))
    w('')
    w('Both paths:')
    w('')
    w('- `facts_data.py`: %s gives the lowest, the highest and the median rate of a group of records.' % fn('facts_data', 'rng'))
    w('- `facts_text.py`: %s compares a 7200 MT/s range with an 8000 MT/s range.' % fn('facts_text', 'compare'))
    w('- `make_report.py`: the class %s holds the range of one group of records on the report page.' % fn('make_report', 'Rg'))
    w('')

    w('### 5.2 Quick statistics tools (also used as a cross-check)')
    w('')
    for key in ('stat_k120', 'stat_bwx'):
        w('- ' + code(key))
        w('  - Call sequence:')
        for l in callseq(key, '    '):
            w(l)
    w('')

    w('### 5.3 The facts sheet: `build_facts.py` and its modules')
    w('')
    for key in ('build_facts', 'facts_data', 'facts_text', 'facts_text4'):
        w('- ' + code(key))
        n = len(OV[key]['call_sequence'])
        for l in folded('Call sequence of <code>%s</code> (%d entries)' % (os.path.basename(MAN[key]['path']), n), callseq(key, '    ')):
            w(l)
    w('')

    w('### 5.4 The report page: `make_report.py` and its test')
    w('')
    for key in ('make_report', 'test_make_report'):
        w('- ' + code(key))
        n = len(OV[key]['call_sequence'])
        for l in folded('Call sequence of <code>%s</code> (%d entries)' % (os.path.basename(MAN[key]['path']), n), callseq(key, '    ')):
            w(l)
    w('')

    w('## 6. Results of the analysis')
    w('')
    w('- Folder: `%s`' % crb(S))
    w('  - ' + item(os.path.join(S, 'facts.json'), 'Every interval as one record, plus run facts and verdicts.', 'facts.json'))
    w('  - ' + item(os.path.join(S, 'FACTS.md'), 'The facts sheet: all tables and verdicts of the rerun.', 'FACTS.md'))
    w('- Folder: `%s`' % crb(OUTDIR))
    w('  - ' + item(os.path.join(OUTDIR, 'whole-chip-rerun-7200.html'), 'The report page with the final old-against-new throughput.', 'whole-chip-rerun-7200.html'))
    w('')
    ta, tb, drop_a = result_tables()
    w('The final total rates of the 120 threads at 7200 MT/s [Ref5]. All values come from 1 boot of CRB.')
    w('')
    w('Part A (binaries `bw_old` and `bw_new`, whole-pass stop, 0.5 s). One row per session and round. Each rate is the median of the 3 intervals of one process:')
    w('')
    for l in ta:
        w(l)
    w('')
    w('- The facts sheet gives the drop range of part A as %s.' % drop_a.replace(' (', ' % ('))
    w('- The comparison rules of the test allow no pooled range of `bw_new` over rounds or sessions (rule V3 of `baselines-and-rules.txt`). So the table has one row per pair of processes.')
    w('- Limit of part A: with the whole-pass stop the pass count moves in steps, and the rate moves with it. So the percent values of part A are less exact than those of parts L and C (section 3.1 of `FACTS.md`). Rule V3 says to take the main percent value from parts L and C.')
    w('- The facts sheet gives the 3 interval rates and the pass counts of each process (section 3.1 of `FACTS.md`).')
    w('')
    w('Parts L and C and control I (runner `bwx12`, common stop, 6 s):')
    w('')
    for l in tb:
        w(l)
    w('')
    w('- A rate range gives the lowest and the highest interval rate of the group.')
    w('- The column "Below `oldread`" is the drop: (1 - new / old) x 100, computed per pair of intervals of the same process and round. The range gives the smallest and the largest drop of the group.')
    w('- Part C keeps the two kernel orders apart for `read`. Rule V2 of `baselines-and-rules.txt` asks for this. In each part C row, the `oldread` range comes from the two processes that the column "Group" names.')
    w('- The facts sheet gives three more groups of part C, for `asmread` (section 3.3 of `FACTS.md`).')
    w('- Part L and control I did not run the new read kernel. `asmread` is used in place of it there [Ref2].')
    w('')
    w('How these numbers were made:')
    w('')
    w('- Part A and the `bwx12` parts compute the total rate of one interval in two ways. Section 5.1 gives both formulas: step 1 of the part A path and step 2 of the bwx12 path.')
    w('- The script `%s` wrote this list. Its function `result_tables` computed the medians and the rate ranges from the interval records of `facts.json`. It read the same intervals again from the raw csv files with the parsers of `stat_k120.py` and `stat_bwx.py`. Part A: the 3 interval rates of each of the 12 processes of the table are the same in both sources after rounding to 0.01 GB/s. `bwx12` parts: the lowest rate and the highest rate of each rate range are the same in both sources after rounding to 0.01 GB/s, and the interval count is the same.' % crb(os.path.join(T, 'make_list.py')))
    w('- The percent ranges are the fields `smallest_drop_pct` and `largest_drop_pct` of `verdicts.q1_parts` in `facts.json`.')
    w('- The percent values of the part A table were computed by `make_list.py` from the medians. Their smallest and their largest value agree with `verdicts.q1_parts`.')
    w('')

    w('## 7. Findings and open points of this list')
    w('')
    check_two_texts()
    check_two_texts_go()
    bf, ft4, mr = MAN['build_facts']['path'], MAN['facts_text4']['path'], MAN['make_report']['path']
    need(bf, 689, "chk('logins'")
    need(bf, 701, "chk('A-shape'")
    need(ft4, 1461, "need(all(k['ok'] for k in D['checks'])")
    need(mr, 863, 'len(ST_GO) == 12 and len(ST_GO2) == 6')
    for f in (bf, MAN['facts_text']['path'], ft4):
        if any('state' in l and re.search(r'[=!]= *(12|6)\b', l) for l in open(f).read().split('\n')):
            die('%s: a line compares state lines with 12 or 6' % f)
    need(MAN['kprobe']['path'], 331, '=== probe.o copy_barrier ===')
    need(MAN['kprobe']['path'], 404, 'chase ===')
    ft = MAN['facts_text']['path']
    need(ft, 5, 'The templates below hold words only')
    need(ft, 886, '== {1}')
    need(ft, 191, '12 state lines')
    need(ft, 194, '24 processes, 72 interval rows')
    need(ft, 833, '0 logins')
    need(ft, 887, '1 task was runnable')
    need(ft, 255, 'ended 8 s before the first process of row A-2')
    need(ft, 1011, 'a2gap = ')
    need(ft, 1014, '0 < a2gap < 60')
    tm = MAN['test_make_report']['path']
    need(tm, 5, 'it must not write a page')
    tm_print = [i for i, l in enumerate(open(tm).read().split('\n'), 1) if 'output file written' in l]
    tm_ok = find_line(tm, 'ok = res[')
    if len(tm_print) != 1:
        die('test_make_report.py: %d lines with "output file written"' % len(tm_print))
    for t in OPEN_POINTS:
        w('- ' + t.replace('@TM_PRINT@', str(tm_print[0])).replace('@TM_OK@', str(tm_ok)))
    w('')

    w('## 8. Left out of this list')
    w('')
    n_other = len(os.listdir(W15)) - 2
    for f in ('rx.sh', 'rx.sh.md', 'r0.sh', 'FINDINGS.md', 'r8.spec', 'r1.spec', 'r5.spec', 'r6.spec', 'r0b.spec'):
        if not os.path.isfile(os.path.join(W15, f)):
            die('missing ' + f)
    for d in (os.path.join(BWX12, 'ref-bwx11'), os.path.join(C, 'tmp', 'agent-scratch', 'bwx11-2026-11-15'), os.path.join(C, 'tmp', 'agent-scratch', 'bwx-2026-11-13'),
              os.path.join(S, 'render'), os.path.join(S, 'test-tmp')):
        if not os.path.isdir(d):
            die('missing folder ' + d)
    for f in (os.path.join(OUTDIR, 'run_partA.sh'), os.path.join(K13, 'README.orig.md'), os.path.join(S, 'review-w1.json'), os.path.join(S, 'review-w2.json')):
        if not os.path.isfile(f):
            die('missing ' + f)
    need(MAN['go']['path'], 21, 'go-T72.lock')
    need(MAN['go2']['path'], 17, 'go-T72.lock')
    names = {f['name'] for f in OV['make_report']['functions']}
    called = {c['name'] for c in OV['make_report']['call_sequence']}
    for h in ('esc', 'plural', 'f1', 'f2'):
        if h not in names or h in called:
            die('make_report: helper %s is not a left-out helper any more' % h)
    kern = sorted(c['name'] for c in OV['bwx12']['call_sequence'] if c['name'].startswith('k_'))
    if sorted(set(kern)) != ['k_asmread', 'k_oldread', 'k_read', 'k_read_1pl', 'k_read_nop256', 'k_read_nop96', 'k_write']:
        die('bwx12: unexpected kernels in the call sequence: %s' % kern)
    lst = MAN['bwx12_listing']['path']
    need(lst, 17, '=== bwx12 write ===')
    for t in LEFT_OUT:
        w('- ' + t.replace('@N_OTHER@', str(n_other)))
    w('')

    w('## References')
    w('')
    for t in REFS:
        w('- ' + t)
    w('')

    text = '\n'.join(o)
    used = set(re.findall(r'\[Ref(\d+)\]', text.split('## References')[0]))
    defined = set(re.findall(r'^- \[Ref(\d+)\]', text.split('## References')[1], re.M))
    if used != defined:
        die('references used %s, defined %s' % (sorted(used), sorted(defined)))
    for m in re.finditer(r'\]\(([^)]+)\)', text):
        if not os.path.exists(os.path.join(OUTDIR, m.group(1))):
            die('broken link ' + m.group(1))
    if '--check' not in sys.argv:
        with open(OUT, 'w') as f:
            f.write(text)
    print('%s %s: %d bytes, %d lines' % ('checked' if '--check' in sys.argv else 'wrote', OUT, len(text), text.count('\n') + 1))
    print('files listed with a link: %(files)d, companions linked: %(companions)d, introductions tested (fewer than 15 words): %(intros)d, '
          'function entries from the overviews: %(functions)d' % STATS)


# Entries marked F are word for word from the word list of FACTS.md (lines 38 to 96), with "this list" in place of "this sheet".
WORDS = [
    ('CRB', 'the Arm reference server under test. It has 128 CPUs.'),
    ('Rerun', 'the whole-chip read test of 2026-11-17, run after the memory speed was lowered from 8000 MT/s to 7200 MT/s.'),
    ('Mesh 0, mesh 1', 'the two halves of the chip. CPUs 0-63 sit on mesh 0. CPUs 64-127 sit on mesh 1.'),
    ('Whole chip, 120 threads, 64+56', 'our runs use CPUs 0-119 only: 64 threads on mesh 0 plus 56 threads on mesh 1. Each thread reads its own buffer of 256 MiB from memory.'),
    ('MT/s', 'million transfers per second, the unit of memory speed.'),
    ('Memory module', 'one DIMM. CRB has 12 slots.'),
    ('Read kernel', 'the inner loop of the benchmark that reads memory. In this list "kernel" means this loop. The operating system kernel is always written "Linux kernel".'),
    ('Old read kernel', 'portable C code with 16 running sums. Each load is followed by an add. Its name is `read` in the binary bw_old and `oldread` in the runner bwx12.'),
    ('New read kernel', 'NEON intrinsics (C functions that map to Arm vector instructions), loads only. Its name is `read` in the binary bw_new and `read` in bwx12.'),
    ('asmread', 'a hand-written load-only loop. It has the same 8 "ldp q" loads per 256 B as the new read kernel. "ldp q" is the Arm instruction that loads two 16-byte vector registers.'),
    ('Load-only loop', 'the new read kernel or asmread.'),
    ('bw_old, bw_new', 'the two binaries of 2026-11-13. bw_old was built from the old source `bandwidth.orig.c`, bw_new from the new source `bandwidth.c`.'),
    ('bwx12, bwx11, bwx', 'later runner programs for the same loops. They print one row per thread. bwx12 is the runner of the 2026-11-15 investigation. bwx11 and bwx are older versions.'),
    ('Process, interval, round, position', 'a process is one start of a benchmark binary. An interval is one timed measurement inside a process. bwx12 times a sequence of kernels and repeats the sequence: each repeat is a round (counted from 0), and the position is the place of a kernel in the sequence (counted from 0). In part A the round (1 or 2) is the round of the script: round 2 runs the processes in the reverse order.'),
    ('Session', 'one pass of go.sh through part A, part L and part C.'),
    ('Part A', 'the 120-thread part of the test of 2026-11-13, repeated with the same two binaries.'),
    ('Part L', 'one bwx12 process with the kernel sequence oldread, asmread, read_nop96, read_nop256, read_1pl.'),
    ('Part C', 'one bwx12 process with the sequence oldread, read, asmread (cfwd) or asmread, read, oldread (crev).'),
    ('Control I', 'the part L line, started from an idle machine, twice. It was added after the first numbers were seen. It is not part of the plan fixed before the run.'),
    ('Line, argument line', 'the arguments of one bwx12 process, as a spec file holds them. "The same line" means a process with the same arguments.'),
    ('Spec file', 'a file with one line "tag|arguments" per process. `rx.sh` reads each line, names the csv file after the tag, and passes the arguments to the binary (bwx12 in this test). Each of the three spec files of this test holds one line.'),
    ('Idle start', 'a launch at a 1-minute load average below 1.0.'),
    ('Visit', 'one time at which the same line was run. A later visit is the same line run again at a later time.'),
    ('State line', 'a line that go.sh or go2.sh prints with the time, the boot id, MemTotal, the load, the logins and the processes per user.'),
    ('I, T, P, C rows', 'the row kinds of a bwx csv file: one I row per interval, one T row per thread and interval, one P row per thread before the first interval and after each interval (it holds the page state of the buffer), and one C row per thread and interval with counter values.'),
    ('Whole-pass stop', 'the stop rule of bandwidth.c: after the minimum time (0.5 s here) each thread finishes the pass over its buffer that it is in. The threads stop at different times.'),
    ('Common stop', 'the stop rule used with bwx12 here: all threads stop at the same time (after 6 s).'),
    ('Total rate, throughput', 'the read rate of all 120 threads together in one interval, in GB/s. The request of the user calls it aggregation throughput. Part A: the column aggregate_GBps that bandwidth.c prints. bwx runners: the sum over the threads of bytes / elapsed time.'),
    ('Drop', 'how far the rate of the new read kernel (or of asmread) lies below the rate of the old read kernel, in percent: (1 - new / old) x 100.'),
    ('First touch', 'the first write to a buffer by its own thread, before any timing.'),
    ('Marker file', '`/tmp/positron-perf.RUNNING`. Another user creates it during a performance test. Our scripts stop when it exists.'),
    ('rc, rc line', 'rc is the exit status of a process. 0 means success. The rc line is the line `rc <status> <tag> utc <time>` that `rx.sh` appends to launches.txt when a process ends.'),
    ('sha256', 'a checksum. Two files with the same sha256 have the same content.'),
    ('Baseline', 'an earlier 8000 MT/s run with 12 modules that used the same binary and method as a part of the rerun. The list was fixed before the run.'),
    ('Pool', 'the intervals of several rows taken together as one range.'),
    ('X2d12', 'one earlier process with the part L line, run on 2026-11-17 at 8000 MT/s with 12 modules, in another boot and with a firmware test setting. The rules file lists it as not a baseline.'),
    ('Facts sheet', 'the file `FACTS.md`. The script `build_facts.py` writes it. It holds all tables and verdicts of the rerun.'),
    ('Rules V1 to V4, F1, F2', 'the comparison rules in `baselines-and-rules.txt`.'),
    ('Q1', 'at 7200 MT/s with 12 memory modules, is the whole-chip read rate of the new read kernel still below that of the old read kernel, and by how much.'),
    ('Q2', "did either kernel's rate differ from the earlier runs with 12 modules at 8000 MT/s."),
    ('Journal', 'the log store of Linux. It keeps the Linux kernel log of earlier boots.'),
    ('Hardware error record', 'a message that the firmware passes to Linux when hardware reports an error.'),
    ('Companion', 'the explanation file of a listed file. It has the same name plus `.md` and lies in the same folder.'),
    ('Call sequence', 'the functions that run, in the order in which they are called. A deeper list level is a call made by the entry above it. Where the two entries are in different files, the call can pass through functions that the section of the called file lists. Example: `ra.sh:one` starts a process, and `main`, `worker` and `pass` of that process run before `k_read`. The kernels below one `pass` or `call` entry are alternatives: each process or interval runs one of them. An entry marked "NOT called" names a function that does not run in this test.'),
    ('Agent server', 'the Linux server on which Claude Code ran. Claude Code is the AI coding agent that sent the commands of section 3.1 to CRB with ssh.'),
    ('Session record', 'a file that records one working session of Claude Code. This list uses three of them [Ref3] [Ref6] [Ref7]. In this term "session" does not mean a session of go.sh.'),
    ('GB', '1e9 bytes.'),
]

DIAGRAM = [
    'agent server (commands of section 3.1)',
    '  |  copy scripts, then: ssh CRB nohup setsid go.sh > log',
    '  v',
    'CRB, CPUs 0-119, no root',
    '  go.sh                           driver: 3 sessions, then 1 more C',
    '   |- ra.sh T72A<s>               part A: 24 processes',
    '   |    |- bw_old                 old: bandwidth.orig.c, k_read',
    '   |    `- bw_new                 new: bandwidth.c, k_read',
    '   |- rx.sh T72L<s> < like.spec   part L: 1 process',
    '   |    `- bwx12                  old: k_oldread, also k_asmread',
    '   `- rx.sh T72C<s> < cfwd.spec   part C: 1 process (or crev.spec)',
    '        `- bwx12                  old: k_oldread, new: k_read',
    '  go2.sh                          control I: 2 processes',
    '   `- rx.sh T72I<i> < like.spec',
    '        `- bwx12                  old: k_oldread, also k_asmread',
    '  |',
    '  v  copy results back',
    'agent server',
    '  build_facts.py  -> FACTS.md, facts.json',
    '  make_report.py  -> whole-chip-rerun-7200.html',
]

BASELINES = [
    ('A-1', 'kernels-20261113T181222Z', 'The first whole-chip test of 2026-11-13: `threads120.csv`, same process order as `ra.sh`.'),
    ('A-2', 'partA-20261113T205055Z', '`A1.csv`: same binaries, other process order. Arguments differ by `--per-thread` and the `--cpus` spelling.'),
    ('A-3', 'partA-20261113T205055Z', '`A3.csv`, only the 3 processes with tags `onebuf-ms500-1` to `-3`: `bw_old`, kernel `read`.'),
    ('L-1', 'w120-R8-20261117T020549Z', '`a6456.csv` with the argument line of `like.spec`, at 8000 MT/s.'),
    ('L-2', 'w120-R1-20261115T185140Z', '`p1nop.csv`, `p2add.csv`: bwx12, 4 s intervals.'),
    ('L-3', 'w120-R5-20261115T203152Z', '`thp.csv`: bwx12, 4 s intervals.'),
    ('L-4', 'w120-R6-20261115T203438Z', '`st1.csv`, `st2.csv`, `st3.csv`: bwx12, 4 s intervals.'),
    ('R0', 'w120-R0-20261115T165608Z', '`p1.csv`, `p2.csv`: the older runner bwx11, 6 s intervals.'),
    ('R0b', 'w120-R0b-20261115T170342Z', '`cA.csv`, `cB.csv`, `cC.csv`: the older runner bwx11, 4 s intervals.'),
    ('F72d12', 'w120-w120-F72d12-20261117T200231Z', '`a6456.csv`: a 7200 MT/s sample of the same boot, run before the rerun.'),
    ('B7a, B7b', 'B7-20261113T232859Z', 'First runner bwx, `B7.csv`: nearest 8000 MT/s data for kernel `read`. Second folder: `B7-20261114T024352Z`.'),
    ('C3a, C3b', 'C3-20261114T022708Z', 'First runner bwx, `C3.csv`: pooled with B7a and B7b. Second folder: `C3-20261114T054116Z`.'),
    ('B5a, B5b, B5a-rev, B5b-rev', 'B5-20261114T011723Z', 'First runner bwx, `B5.csv`: forward and reverse kernel order. Second folder: `B5-20261114T043213Z`.'),
    ('X2d12', 'w120-X2d12-20261117T040922Z', '`a6456.csv`: 8000 MT/s, 12 modules, firmware test setting. Not a baseline.'),
    ('X1d10', 'w120-X1d10-20261117T034916Z', '`a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline.'),
    ('X1d10b', 'w120-X1d10b-20261117T040407Z', '`a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline.'),
    ('BASEd10', 'w120-BASEd10-20261117T041738Z', '`a6456.csv`: 8000 MT/s boot with 10 memory modules. Not a baseline.'),
]

OPEN_POINTS = [
    '**Two texts of `bandwidth.c`: they differ in comment lines only.** The local `bandwidth.c` has the sha256 value `f1985072...`. The run of 18:12:22 UTC on 2026-11-13 (mode `all`, the first test) recorded `c1406e02...` for its `bandwidth.c`. The run of 18:12:10 UTC (mode `probe`) recorded the same value. All three build records of that day give the same sha256 value for the binary `bw_new` (`fd7c14df...`), and `ra.sh` checks that value. So the machine code that ran is not in doubt [Ref4]. The record of 18:32:18 UTC holds the sha256 value of the local `bandwidth.c` and the same sha256 value of `bw_new`. So the local text compiles to the binary that ran. An edit of 2026-11-13 18:32:07 UTC replaced 2 comment lines above `k_read` with the 5 comment lines 178 to 182 of the local text [Ref6]. With this edit reversed, the local text has the sha256 value `c1406e02...` of the first test. No code line differs.',
    '**Two texts of `go.sh`: they differ in the message of line 20 only.** The run of 2026-11-17 used the text with the sha256 value `75bc50b0...`. This value is the `go.sh` entry of `local.sha`. The session record of 2026-11-17 shows that `sha256sum -c local.sha` printed `OK` for `go.sh` on CRB before the start [Ref3]. Line 295 of the record holds the last command that wrote `go.sh` before the copy to CRB. The script text in that command has the same sha256 value [Ref3]. On 2026-11-24 the message of line 20 was changed on the instruction of the user. `RUNNING file present` became `RUNNING file present, Jeremy or someone else is using CRB` [Ref7]. Jeremy is another user of CRB [Ref8]. The local `go.sh` now has the sha256 value `d68cf6c0...`. With this edit reversed, the local text has the value `75bc50b0...` again [Ref9]. `local.sha` was not changed. So `sha256sum -c local.sha` in the local folder now prints `go.sh: FAILED`. Check 20 of `build_facts.py` makes the same comparison (line 778, key `sha-local`). So a new run of `build_facts.py` fails check 20. It then stops and writes no file. With the edit reversed it passes [Ref9]. The edit was made in the local file only. `go2.sh` was not edited. It keeps the old message in lines 16 and 25.',
    '**The binaries are not local.** `bw_old`, `bw_new` and `bwx12` are in no local folder. They were on CRB on 2026-11-17. `ra.sh` checked the sha256 values of `bw_old` and `bw_new` at the start of each session. `rx.sh` checked the sha256 value of `bwx12` before each process. Insufficient data: whether the binaries are still on CRB today. A listing of the three paths on CRB would resolve it.',
    '**The machine code of the timing functions is not recorded.** The objdump records of section 4.8 do not hold `worker`, `pass` or `call`. `listing.txt` holds the 55 kernels of `bwx12`. `probe.txt` holds the 6 kernels of each part A binary, 3 functions of `probe.o` and the function `chase` of two other programs. Insufficient data: the machine code of `worker`, `pass` and `call`, and whether gcc placed `call` inside `worker`. An objdump of these functions on CRB would resolve it.',
    '**The top-level commands are in no script.** The commands of section 3.1 are only in the session record [Ref3]. That file lies outside the project folder.',
    '**The CPU list of the shell of `go2.sh` is not recorded.** `go.sh` prints the CPU list of its shell (line 38), and its log shows `0-119`. `go2.sh` has no such line. Neither start command holds a `taskset` [Ref3]. Hypothesis: the shell of `go2.sh` had the same list `0-119`. It started in the same way, about 11 min later, in the same boot. The companion of `go.sh` names the source of that list (section "Behavior a reader must know"). `rx.sh` starts `bwx12` under `taskset -c 0-119` (line 17). So the CPUs of the benchmark threads are known. Insufficient data: a direct record of the CPU list of the shell of `go2.sh`, and so of the wait loop of `rx.sh` during control I. A line `taskset -cp $$` in `go2.sh` would resolve it for a later run.',
    '**The text templates of the analysis hold numbers that the script does not compute.** A text template is a piece of the text of `FACTS.md` that is written in the script. The first lines of `facts_text.py` say that the templates hold words only. Five numbers that are written in the templates of that file: "12 state lines" (line 191), "24 processes, 72 interval rows" (line 194), "0 logins" (line 833), "1 task was runnable" (line 887) and "ended 8 s before the first process of row A-2" (line 255). Three of the five have a test. The check `A-shape` of `build_facts.py` (line 701) tests the text of line 194: 24 processes with 3 intervals each. The check `logins` of `build_facts.py` (line 689) tests the text of line 833. `facts_text4.py` stops the script when a check fails (line 1461). The `need` test in line 886 stops the script when the data do not show the value of line 887. Two of the five have no test in the scripts that write `FACTS.md`. No line of `build_facts.py`, `facts_text.py` or `facts_text4.py` compares the number of state lines with 12. `make_report.py` tests this number for the report page (line 863). For line 255, line 1011 computes the gap from the data, and the test of line 1014 accepts any gap between 0 s and 60 s. Both texts agree with the data today. The log of `go.sh` holds 12 state lines. The gap that the script computes is 8 s (item 11 of section 1.5 of `FACTS.md`). Insufficient data: the full list of such numbers in `facts_text.py`, `facts_text4.py` and `make_report.py`, and which of them a test checks. A reading of the string literals of these scripts that hold a digit would resolve it.',
    '**The test of the report generator checks the exit status only.** The first lines of `test_make_report.py` say that a damaged case must not write a page. The script prints whether the output file was written (line @TM_PRINT@). Its verdict uses only the exit statuses of the 11 runs (line @TM_OK@). So a damaged case that writes a page and ends with status 1 passes the test.',
    '**Part A does not record the page size of the buffers.** `bw_old` and `bw_new` ask Linux for 2 MiB pages and print the request only. They do not check the result. `bwx12` records the page state in its P rows. Insufficient data: whether the part A buffers lay on 2 MiB pages. The field AnonHugePages in `/proc/PID/smaps` of a running part A process would resolve it.',
]

LEFT_OUT = [
    'The files of the earlier runs of section 4.9 have no companion, except the two converted copies. This test did not generate them. The analysis reads them with the same two parsers as the files of sections 4.3 to 4.6 (`read_k120` and `read_bwx` of `facts_data.py`). Their layout differs in these points. `A1.csv`, `A3.csv`, `B7.csv`, `C3.csv` and `B5.csv` start each process with a line `-- step ...`. `A1.csv` and `A3.csv` also hold one row `thread,...` per thread and interval. Each `B7.csv`, `C3.csv` and `B5.csv` holds several processes in one file (48, 18 and 4). `B7.csv` and `B5.csv` hold no C rows. The C rows of `C3.csv` and of the files of rows L-2, L-3, L-4, R0 and R0b hold another list of counters than the C rows of sections 4.4 to 4.6. `C3.csv` holds 5 counters per C row, not 6.',
    'The code of the earlier runs of section 4.9 is not listed. The rerun did not start it. Examples: `new-test-kernel/run_partA.sh` (rows A-2 and A-3), `tmp/agent-scratch/w120-2026-11-15/r0.sh` (row R0), the spec files `r8.spec`, `r1.spec`, `r5.spec` and `r6.spec` of that folder (rows L-1 to L-4) and `r0b.spec` (row R0b), and the sources of the older runners in `tmp/agent-scratch/bwx11-2026-11-15` and `tmp/agent-scratch/bwx-2026-11-13`. The line of `like.spec` is the line with the tag `a6456` of `r8.spec`.',
    'The other @N_OTHER@ entries of `tmp/agent-scratch/w120-2026-11-15` (spec files, logs and scripts of the investigation of 2026-11-15) are not listed. The analysis reads two of them: `r0.sh`, for the sha256 value of bwx11, and `FINDINGS.md`. The facts sheet lists both [Ref1].',
    'The other machine records that the analysis reads (memory module records, saved Linux kernel logs, firmware settings) are not listed. The facts sheet lists them [Ref1].',
    'The scripts under `tmp/agent-scratch/w120-7200-2026-11-17/render` are not listed. They take screenshots of the report page, measure its layout and test the hover areas of Figure 2, all in a headless Chrome. They compute no rate.',
    'The backup, review and test folders and files of that scratch folder (`bak-*`, `r1fix-work`, `r2fix-work`, `r3fix-work`, `final-check`, `review-scratch`, `verify-*`, `review-w1.json`, `review-w2.json`, the empty folder `test-tmp`) are not listed.',
    'Two more build records of 2026-11-13 are not listed and have no companion: `results/kernels-20261113T181210Z/probe.txt` and `results/kernels-20261113T183218Z/probe.txt` [Ref4]. The record of 18:32:18 UTC is the one that holds the sha256 value of the local `bandwidth.c`.',
    '`README.orig.md` of `tmp/agent-scratch/kernels-2026-11-13` is not listed. No listed script reads it.',
    'The other build records in `tmp/agent-scratch/bwx12-2026-11-15/crb-build-1` are not listed: `build.out`, `selftest-bwx12.txt`, `seq-listing.txt`, `smoke12.txt`, `check_listing12.out`.',
    '`tmp/agent-scratch/bwx12-2026-11-15/ref-bwx11` (`build.txt`, `listing.txt` and `offsets.tsv` of the older runner bwx11) is not listed. `check_listing12.py` and `test_kernels12.py` compare with it.',
    'Files on CRB that the two build scripts only read are not listed. `build12.sh` read the binaries of the earlier runners bwx8, bwx10 and bwx11 with `nm`, for the placement lines of `build.txt`. `run_kernels.sh` read `bench/bandwidth.c`, `bench/latency` and `bench/homelat` below `~/cache-perf/`, for one sha256 line and two objdump sections of `probe.txt`.',
    'The lock file `~/cache-perf/results/go-T72.lock` on CRB is not listed. `go.sh` (line 21) and `go2.sh` (line 17) create it and lock it. Only one of the two scripts can run at a time. No command writes to it. The copy commands of section 3.1 did not copy it back.',
    'In `listing.txt` the companion shows the six timed kernels of the test. The other 49 kernels of `bwx12` are left out there. One of the 49 runs in the test: `k_write` (lines 17 to 32 of `listing.txt`) fills each buffer once before the first interval. It is not timed.',
    'Not every function is named in a call sequence. The call sequences name the functions on the path of the test. Small helper functions of the analysis scripts are left out, for example `esc`, `plural`, `f1` and `f2` of `make_report.py`. The table "Functions" of the companion of `make_report.py` lists these four. Most functions that the test never calls are left out too, for example `usage` in the three C programs and the kernels of `bwx12.c` that the argument lines do not select. Three entries are exceptions. `trial_main` of `bwx12.c` is named and marked "NOT called". `fail` of `go.sh` and `fail` of `go2.sh` are named. `fail` runs only when a check fails, and no check failed in the rerun.',
]

REFS = [
    '[Ref1] `tmp/agent-scratch/w120-7200-2026-11-17/FACTS.md`: section 7 "Files" lists every raw file and script that the analysis used.',
    '[Ref2] `tmp/agent-scratch/w120-7200-2026-11-17/baselines-and-rules.txt`, line 36: "In part L, asmread stands in for the new read kernel (same loop: 8 ldp q per 256 B)".',
    '[Ref3] `%s`: record of the Claude Code session of 2026-11-17. Lines 309, 313, 339, 353, 365 and 377 hold the commands of section 3.1. Line 310 holds the output of the copy command, with `go.sh: OK`. Line 295 holds the last command that wrote `go.sh` before the copy.' % RECORD,
    '[Ref4] `results/kernels-20261113T181210Z/probe.txt`, `results/kernels-20261113T181222Z/probe.txt`, `results/kernels-20261113T183218Z/probe.txt`: line 15 (sha256 of `bandwidth.c`) and line 20 (sha256 of `bw_new`) of the three build records. `tmp/agent-scratch/w120-7200-2026-11-17/ra.sh`, lines 16 to 20: the check of the two binaries.',
    '[Ref5] `tmp/agent-scratch/w120-7200-2026-11-17/facts.json`: the list `intervals` (one record per interval, field `GBps`) and the list `verdicts.q1_parts` (one entry per compared group).',
    '[Ref6] `%s`, line 1000: record of the Claude Code session of 2026-11-13. It holds the edit of `bandwidth.c` between the runs of 18:12:22 UTC and 18:32:18 UTC. The file lies outside the project folder.' % RECORD13,
    '[Ref7] `%s`, lines 2153 and 2245: record of the Claude Code session in which line 20 of `go.sh` was changed. The session began on 2026-11-22. Line 2153 holds the instruction of the user (2026-11-24, 20:27:54 UTC). Line 2245 holds the edit. The file lies outside the project folder.' % RECORD24,
    '[Ref8] `jeremy-plan-constraints-2026-10-30.md`, lines 12 and 13: notes of 2026-10-30 about the tests of Jeremy on CRB. The file `/tmp/positron-perf.RUNNING` is present for the whole of each time window that is reserved for these tests.',
    '[Ref9] `tmp/agent-scratch/go-edit-2026-11-24`: tests of 2026-11-24 for the edit of `go.sh` line 20, with their output in the files that end with `.out`. `check_line20.py` puts the old line back in a copy of the text of `go.sh` and compares the sha256 value. It does not change `go.sh`. `check_facts_build.py` runs `build_facts.py` in a copy of the run folder, with the edited text and with the old line. `go.sh.as-run-2026-11-17` is a copy of `go.sh` from before the edit.',
]


if __name__ == '__main__':
    main()
