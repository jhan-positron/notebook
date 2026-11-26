#!/usr/bin/env python3
"""Score the boundary task T4: which passages a skill version keeps whole, splits, or turns into a list.

Each reply holds 10 rewritten passages. Expected outcome per passage:
  keep   one sentence, no list        (passages 1, 3, 9; passage 8 is recorded only)
  split  two or more sentences, no list (passages 4, 7)
  list   three or more list items     (passages 2, 5, 6, 10)
Labels: a list item that starts with an added label such as "Benefit:" is counted.

Usage: score_boundary.py [--show ARM REP]
"""
import collections, glob, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT + '/proposed/scripts')
import check_lengths as C

EXPECT = {1: 'keep', 2: 'list', 3: 'keep', 4: 'split', 5: 'list', 6: 'list', 7: 'split', 8: 'record',
          9: 'keep', 10: 'list'}
NAMES = {1: 'cache sentence, 14 words', 2: 'developed cache paragraph', 3: 'short sequence, 10 words',
         4: 'clause inside a clause', 5: 'three values in 45 words', 6: 'five steps in 35 words',
         7: 'two claims, two parentheses', 8: 'short "because" sentence', 9: 'short ", so" sentence',
         10: 'done / not done / checked'}
MARK = re.compile(r'(?mi)^[ \t>*#\-]*passage[ \t]+(\d+)\b[^\n]*$')
LABEL = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(?:\*\*[^*]{1,40}\*\*\s*[:.]|\*\*[^*]{1,40}[:.]\*\*|[A-Z][A-Za-z ]{1,24}:\s)')


def segments(text):
    text = re.sub(r'(?m)^[ \t]*(```|~~~)[^\n]*\n?', '', text)
    ms = [m for m in MARK.finditer(text)]
    seg = {}
    for i, m in enumerate(ms):
        n = int(m.group(1))
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        if 1 <= n <= 10 and n not in seg:
            body = text[m.end():end]
            body = re.split(r'(?m)^(?:#{1,6} |\*\*(?:Notes?|Words used|Terms|Changes|What I changed)[^\n]*$)', body)[0]
            seg[n] = body.strip()
    return seg


def measure(body):
    bl = C.analyse(body, 'md')
    prose = [b for b in bl if b['kind'] in ('para', 'bullet')]
    sents = [s for b in prose for s in b['sents'] if s['words']]
    items = [b for b in prose if b['kind'] == 'bullet']
    labels = sum(1 for line in body.split('\n') if LABEL.match(line))
    return dict(sentences=len(sents), items=len(items), labels=labels,
                longest=max([s['words'] for s in sents] or [0]))


def verdict(n, m):
    e = EXPECT[n]
    if e == 'keep':
        return 'ok' if m['sentences'] == 1 and m['items'] == 0 else ('LIST' if m['items'] else 'SPLIT')
    if e == 'split':
        if m['items']:
            return 'LIST'
        return 'ok' if m['sentences'] >= 2 and m['longest'] <= 25 else 'WHOLE'
    if e == 'list':
        return 'ok' if m['items'] >= 3 else 'PROSE'
    return 'whole' if m['sentences'] == 1 and m['items'] == 0 else ('list' if m['items'] else 'split')


runs = collections.defaultdict(dict)
for p in sorted(glob.glob(ROOT + '/experiment/out/T4_boundary_*.json')):
    arm, rep = os.path.basename(p)[:-5].split('_')[2:4]
    d = json.load(open(p))
    seg = segments(d['result'])
    runs[arm][rep] = (seg, d['result'])

if '--show' in sys.argv:
    arm, rep = sys.argv[sys.argv.index('--show') + 1:][:2]
    seg, raw = runs[arm][rep]
    for n in range(1, 11):
        print(f'--- passage {n} ({NAMES[n]}; expect {EXPECT[n]}): {measure(seg.get(n, ""))}')
        print(seg.get(n, '<<missing>>'))
    sys.exit(0)

arms = [a for a in ('CUR', 'NEW2', 'CODEX', 'V3', 'SKILL', 'SKILLSLASH') if a in runs]
print('Boundary task: verdict per run. ok = the expected form. SKILL = the installed plain-english-experiment skill,\n'
      'invoked by name in the normal mode of the command line, with the current skill also in context.')
print(f"{'passage':34s} {'expect':7s} " + ' '.join(f'{a:22s}' for a in arms))
score = collections.Counter()
labels = collections.Counter()
missing = 0
for n in range(1, 11):
    cells = []
    for a in arms:
        vs = []
        for rep in sorted(runs[a]):
            seg, _ = runs[a][rep]
            if n not in seg:
                vs.append('?')
                missing += 1
                continue
            m = measure(seg[n])
            v = verdict(n, m)
            vs.append(v)
            labels[a] += m['labels']
            if EXPECT[n] != 'record':
                score[(a, v == 'ok')] += 1
        cells.append(' '.join(vs))
    print(f"{str(n) + ' ' + NAMES[n]:34s} {EXPECT[n]:7s} " + ' '.join(f'{c:22s}' for c in cells))
print()
for a in arms:
    ok, bad = score[(a, True)], score[(a, False)]
    print(f"{a:6s} expected form in {ok} of {ok + bad} scored passages; list items with an added label: {labels[a]}")
print('passages not found by the parser:', missing)
