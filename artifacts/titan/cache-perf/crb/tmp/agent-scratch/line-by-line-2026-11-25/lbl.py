#!/usr/bin/env python3
"""lbl.py - line-by-line explanation pages for the code of ~/workspace/ai-proj/arm-crb/code.

One page per source file. A page holds one table row per source line:
    | Line | Source | Explanation |
The source column is copied from the file by this script. The explanations come
from annotation files under ann/ (format: see BRIEF.md).

Commands for writers:
    info KEY            paths, mode, references that may be cited, older explanations
    show KEY [A [B]]    source lines A..B with the explanation that each line has now
    old KEY [A B]       the explanations of the older page (groups of lines), when one exists
    seed KEY            write ann/KEY.seed from the finished explanations of the file named in the manifest
    check KEY [A B]     test the annotation of KEY (with A B: only the lines A to B). Prints OK or the errors.

Commands for the main session:
    manifest            write manifest.json from the repo
    status              one line per file
    build KEY | build-all [--only-ready]
    index               write the index page
"""
import collections
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = '/home/jhan/workspace/ai-proj/arm-crb/code'
CRB = '/home/jhan/workspace/titan/cache-perf/crb'
AS = CRB + '/tmp/agent-scratch'
S = AS + '/w120-7200-2026-11-17'
OLDT = AS + '/code-data-list-2026-11-21'
ANN = os.environ.get('LBL_ANN', HERE + '/ann')    # LBL_ANN: another annotation folder, for tests of the tool
MAN = HERE + '/manifest.json'
BACKUP = HERE + '/backup'
RERUN = 'w120-7200-2026-11-17'
TODAY = '2026-11-25'
SECTION = '## Source and explanation, line by line'
OLD_SECTION_RE = re.compile(r'^## Source and explanation, (side by side|line by line)$')
TABLE_HEAD = '| Line | Source | Explanation |'
TABLE_RULE = '|---:|---|---|'

LANG = {'.c': 'c', '.py': 'python', '.sh': 'bash', '.spec': 'text', '.txt': 'text', '.sha': 'text'}
LANG_NAME = {'c': 'C source', 'python': 'Python script', 'bash': 'Bash script', 'make': 'Makefile',
             'text': 'text file'}

# child: parent. The child takes over the explanation of every line that is equal in both files.
SEED = {
    'bwx13-2026-11-15/bwx13.c': 'bwx12-2026-11-15/bwx12.c',
    'bwx11-2026-11-15/bwx11.c': 'bwx12-2026-11-15/bwx12.c',
    'bwx10-2026-11-15/bwx10.c': 'bwx11-2026-11-15/bwx11.c',
    'bwx8-2026-11-14/bwx8.c': 'bwx10-2026-11-15/bwx10.c',
    'bwx-2026-11-13/bwx.c': 'bwx8-2026-11-14/bwx8.c',
    'bwx13-2026-11-15/bwx13_selftest.c': 'bwx12-2026-11-15/bwx12_selftest.c',
    'bwx11-2026-11-15/bwx11_selftest.c': 'bwx12-2026-11-15/bwx12_selftest.c',
    'bwx10-2026-11-15/bwx10_selftest.c': 'bwx11-2026-11-15/bwx11_selftest.c',
    'bwx8-2026-11-14/bwx8_selftest.c': 'bwx10-2026-11-15/bwx10_selftest.c',
    'bwx-2026-11-13/bwx_selftest.c': 'bwx8-2026-11-14/bwx8_selftest.c',
    'bwx13-2026-11-15/check_listing13.py': 'bwx12-2026-11-15/check_listing12.py',
    'bwx11-2026-11-15/check_listing11.py': 'bwx12-2026-11-15/check_listing12.py',
    'bwx10-2026-11-15/check_listing10.py': 'bwx11-2026-11-15/check_listing11.py',
    'bwx8-2026-11-14/check_listing8.py': 'bwx10-2026-11-15/check_listing10.py',
    'bwx-2026-11-13/check_listing.py': 'bwx8-2026-11-14/check_listing8.py',
    'bwx13-2026-11-15/build13.sh': 'bwx12-2026-11-15/build12.sh',
    'bwx11-2026-11-15/build11.sh': 'bwx12-2026-11-15/build12.sh',
    'bwx10-2026-11-15/build10.sh': 'bwx11-2026-11-15/build11.sh',
    'bwx8-2026-11-14/build8.sh': 'bwx10-2026-11-15/build10.sh',
    'bwx-2026-11-13/build.sh': 'bwx8-2026-11-14/build8.sh',
    'bwx10-2026-11-15/run_bwx10.sh': 'bwx11-2026-11-15/run_bwx11.sh',
    'bwx8-2026-11-14/run_bwx9.sh': 'bwx10-2026-11-15/run_bwx10.sh',
    'bwx8-2026-11-14/run_bwx8.sh': 'bwx8-2026-11-14/run_bwx9.sh',
    'bwx8-2026-11-14/run_h2.sh': 'bwx8-2026-11-14/run_bwx8.sh',
    'bwx-2026-11-13/run_bwx.sh': 'bwx8-2026-11-14/run_bwx8.sh',
    'bwx10-2026-11-15/schedule10.py': 'bwx11-2026-11-15/schedule11.py',
    'bwx8-2026-11-14/schedule9.py': 'bwx10-2026-11-15/schedule10.py',
    'bwx8-2026-11-14/schedule8.py': 'bwx8-2026-11-14/schedule9.py',
    'bwx10-2026-11-15/test_schedule10.py': 'bwx11-2026-11-15/test_schedule11.py',
    'bwx8-2026-11-14/test_schedule9.py': 'bwx10-2026-11-15/test_schedule10.py',
    'bwx8-2026-11-14/test_schedule8.py': 'bwx8-2026-11-14/test_schedule9.py',
    'bwx10-2026-11-15/test_runner10.py': 'bwx11-2026-11-15/test_runner11.py',
    'bwx8-2026-11-14/test_runner8.py': 'bwx10-2026-11-15/test_runner10.py',
    'bwx10-2026-11-15/visit10.sh': 'bwx11-2026-11-15/visit11.sh',
    'bwx8-2026-11-14/visit9.sh': 'bwx10-2026-11-15/visit10.sh',
    'bwx8-2026-11-14/visit8.sh': 'bwx8-2026-11-14/visit9.sh',
    'bwx8-2026-11-14/visit_h2.sh': 'bwx8-2026-11-14/visit9.sh',
    'kernels-2026-11-13/bandwidth.c': 'kernels-2026-11-13/bandwidth.orig.c',
    'cread-2026-11-12/bandwidth_cread.c': 'kernels-2026-11-13/bandwidth.c',
    'w120-2026-11-15/rc2.sh': 'w120-2026-11-15/rc.sh',
    'w120-2026-11-15/rgc.sh': 'w120-2026-11-15/rg.sh',
    'w120-7200-2026-11-17/go2.sh': 'w120-7200-2026-11-17/go.sh',
}

# Extra entries whose text is not in the repo: the two checksum lists of the launch.
EXTRA = ['local.sha', 'go2.sha']


class Stop(Exception):
    pass


def die(msg):
    raise Stop(msg)


# ----------------------------------------------------------------------------- files

def source_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if b'\r' in raw:
        die(path + ': the file holds a carriage return')
    lines = raw.decode('utf-8').split('\n')
    if lines and lines[-1] == '':
        lines.pop()
    return lines, hashlib.sha256(raw).hexdigest(), len(raw)


def read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def manifest():
    with open(MAN) as f:
        return {e['key']: e for e in json.load(f)['files']}


def entry(key):
    m = manifest()
    if key not in m:
        close = [k for k in m if k.endswith('/' + key) or os.path.basename(k) == key]
        die('unknown key %r. %s' % (key, ('Did you mean: ' + ', '.join(close)) if close else 'See manifest.json.'))
    return m[key]


def cmd_manifest():
    files = []
    for root, dirs, names in os.walk(REPO):
        dirs.sort()
        for name in sorted(names):
            ext = os.path.splitext(name)[1]
            if name == 'Makefile':
                lang = 'make'
            elif ext in LANG:
                lang = LANG[ext]
            else:
                continue                      # data (.json) and notes (.md) are not code
            path = os.path.join(root, name)
            files.append((os.path.relpath(path, REPO), path, lang, True))
    for name in EXTRA:
        files.append((RERUN + '/' + name, S + '/' + name, 'text', False))
    files.sort()
    out = []
    by_sha = collections.defaultdict(list)
    for key, path, lang, in_repo in files:
        lines, sha, nbytes = source_lines(path)
        folder, name = os.path.split(key)
        e = {'key': key, 'src': path, 'in_repo': in_repo, 'lang': lang, 'lines': len(lines), 'bytes': nbytes,
             'nonblank': sum(1 for l in lines if l.strip()), 'sha256': sha}
        if folder == RERUN:
            e['page'] = S + '/' + name + '.md'
            if not os.path.isfile(e['page']) and not os.path.isfile(BACKUP + '/' + key + '.md'):
                die('no page for ' + key)
            e['mode'] = 'section'
            e['old_page'] = e['page']
            e['old_src'] = S + '/' + name
        else:
            e['page'] = S + '/code/' + key + '.md'
            if os.path.isfile(AS + '/' + key + '.md'):
                e['mode'] = 'copy'
                e['old_page'] = AS + '/' + key + '.md'
                e['old_src'] = AS + '/' + key
            else:
                e['mode'] = 'new'
        if 'old_src' in e:
            ol, osha, ob = source_lines(e['old_src'])
            e['old_lines'], e['old_sha256'], e['old_bytes'] = len(ol), osha, ob
        e['seed_from'] = SEED.get(key)
        by_sha[sha].append(e)
        out.append(e)
    for sha, group in by_sha.items():
        if len(group) > 1:
            canon = sorted(group, key=lambda e: (e['mode'] == 'new', e['key']))[0]
            for e in group:
                if e is not canon:
                    e['same_as'] = canon['key']
    keys = {e['key'] for e in out}
    for child, parent in SEED.items():
        if child not in keys or parent not in keys:
            die('SEED names an unknown file: %s <- %s' % (child, parent))
    with open(MAN, 'w') as f:
        json.dump({'repo': REPO, 'built': TODAY, 'files': out}, f, indent=1)
    c = collections.Counter(e['mode'] for e in out)
    print('manifest.json: %d files, %d lines (%d not blank). modes: %s. equal to another file: %d. seeded: %d' % (
        len(out), sum(e['lines'] for e in out), sum(e['nonblank'] for e in out), dict(c),
        sum(1 for e in out if 'same_as' in e), sum(1 for e in out if e['seed_from'])))


# ----------------------------------------------------------------------------- annotation files

LINE_RE = re.compile(r'^(\d+): (.*)$')
PART_RE = re.compile(r'^@part (\d+)-(\d+) (.+)$')
TOKEN_RE = re.compile(r'\{L(\d+)(?:-(\d+))?\}')
REF_RE = re.compile(r'\[Ref(\d+)\]')


def akey(e):
    """The key whose annotation files this entry uses."""
    return e.get('same_as', e['key'])


def ann_paths(key):
    base = os.path.join(ANN, key)
    out = []
    if os.path.isfile(base + '.ann'):
        out.append(base + '.ann')
    if os.path.isdir(base + '.ann.d'):
        out += sorted(os.path.join(base + '.ann.d', f) for f in os.listdir(base + '.ann.d') if f.endswith('.ann'))
    return out


def parse_ann(path, lines_only, errors):
    own, parts = {}, []
    for n, raw in enumerate(read_text(path).split('\n'), 1):
        if raw.strip() == '':
            continue
        m = PART_RE.match(raw)
        if m and not lines_only:
            parts.append((int(m.group(1)), int(m.group(2)), m.group(3).strip(), '%s:%d' % (path, n)))
            continue
        m = LINE_RE.match(raw)
        if not m:
            errors.append('%s:%d: the line is not "N: text" and not "@part A-B title": %s' % (path, n, raw[:60]))
            continue
        k = int(m.group(1))
        if k in own:
            errors.append('%s:%d: line %d has two explanations in this file' % (path, n, k))
        own[k] = m.group(2)
    return own, parts


def load_ann(key, errors):
    """(own explanations, seed explanations, parts) of the annotation files of key."""
    own, parts, where = {}, [], {}
    for p in ann_paths(key):
        o, ps = parse_ann(p, False, errors)
        for k, t in o.items():
            if k in own:
                errors.append('%s: line %d is explained in two files (also %s)' % (p, k, where[k]))
            own[k], where[k] = t, p
        parts += ps
    seed = {}
    sp = os.path.join(ANN, key + '.seed')
    if os.path.isfile(sp):
        seed, _ = parse_ann(sp, True, errors)
    return own, seed, sorted(parts)


def spans(text):
    """Split text into ('text', s) and ('code', content, raw) pieces. None when a backtick has no partner."""
    out, buf, i, n = [], '', 0, len(text)
    while i < n:
        if text[i] != '`':
            buf += text[i]
            i += 1
            continue
        j = i
        while j < n and text[j] == '`':
            j += 1
        run, k = j - i, j
        while True:
            k = text.find('`', k)
            if k < 0:
                return None
            m = k
            while m < n and text[m] == '`':
                m += 1
            if m - k == run:
                break
            k = m
        out.append(('text', buf))
        buf = ''
        out.append(('code', text[j:k], text[i:m]))
        i = m
    out.append(('text', buf))
    return out


BANNED = ['e.g.', 'i.e.', 'etc.', ' via ', 'a.k.a', ' aka ', 'under the hood', 'boilerplate', 'sanity check',
          'on the fly', 'out of the box', 'kicks off', 'kick off', 'bails out', 'bail out', 'noise floor',
          'low-hanging', 'moving parts', 'in a nutshell', 'rule of thumb', 'ballpark', 'leverage', 'utilize',
          ' bumps ', ' bump ', 'for free', 'at a glance']
BAD_CHARS = set('|<>*_~$\\^&;@')
SOFT_WORDS = [' because ', ' since ', ' which means ', ' so that ']


def lint_text(text, where, nlines, blank, refs, errors, warns, allow_bspipe=False, kind='line'):
    if text != text.strip() or text == '':
        errors.append('%s: the text is empty or has a space at an end' % where)
        return
    if '\t' in text:
        errors.append('%s: the text holds a tab' % where)
    sp = spans(text)
    if sp is None:
        errors.append('%s: a backtick has no partner (code spans need the same number of backticks at both ends)' % where)
        return
    for piece in sp:
        if piece[0] == 'code':
            c = piece[1]
            if c.strip() == '':
                errors.append('%s: an empty code span' % where)
            if '\\|' in c and not allow_bspipe:
                errors.append('%s: a code span holds a backslash directly before "|". A table cell cannot show this pair. '
                              'Describe it in words' % where)
            continue
        t = piece[1]
        rest = TOKEN_RE.sub('', t)
        rest = REF_RE.sub('', rest)
        if kind == 'ref':
            rest = re.sub(r'https?://\S+', '', rest)
        bad = sorted(set(rest) & BAD_CHARS)
        if bad:
            errors.append('%s: outside a code span the text holds %s. Put code in backticks, or use words'
                          % (where, ' '.join(repr(b) for b in bad)))
        if '[' in rest or ']' in rest or '{' in rest or '}' in rest:
            errors.append('%s: outside a code span the text holds a bracket or a brace that is not [RefN] and not {LN}' % where)
        if any(ord(ch) > 126 or ord(ch) < 32 for ch in rest):
            errors.append('%s: outside a code span the text holds a character that is not plain ASCII' % where)
        if kind != 'ref' and re.search(r'https?:|www\.', rest):
            errors.append('%s: a web address outside the references' % where)
        if re.search(r'\b[Ll]ines? \d', rest):
            errors.append('%s: a line number in plain text. Write {L12} or {L12-15} for lines of this file. '
                          'For another file, name the file without a line number' % where)
        low = ' ' + rest.lower() + ' '
        for b in BANNED:
            if b in low:
                errors.append('%s: the phrase %r is not plain English (idiom or abbreviation)' % (where, b.strip()))
        for b in SOFT_WORDS:
            if b in low:
                warns.append('%s: %r: try to split the sentence' % (where, b.strip()))
    for m in TOKEN_RE.finditer(''.join(p[1] for p in sp if p[0] == 'text')):
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) else a
        if not (1 <= a <= b <= nlines) or (m.group(2) and a == b):
            errors.append('%s: %s names a line that the file does not have (%d lines)' % (where, m.group(0), nlines))
        elif a in blank or b in blank:
            errors.append('%s: %s starts or ends at a blank line' % (where, m.group(0)))
    if refs is not None:
        for m in REF_RE.finditer(text):
            if int(m.group(1)) not in refs:
                errors.append('%s: [Ref%s] is not in the references of the page' % (where, m.group(1)))
    if len(text) > 1500:
        errors.append('%s: the text has %d characters (limit 1500)' % (where, len(text)))
    elif len(text) > 700:
        warns.append('%s: the text has %d characters. Shorter is better' % (where, len(text)))


def render(text, in_table):
    """Replace the {L..} tokens outside code spans. In a table cell, write each | as \\|."""
    out = ''
    for piece in spans(text):
        if piece[0] == 'code':
            out += piece[2]
            continue

        def rep(m, s=piece[1], done=out):
            a, b = m.group(1), m.group(2)
            before = (done + s[:m.start()])
            cap = before == '' or before.endswith('. ')
            word = ('Line' if cap else 'line') if not b else ('Lines' if cap else 'lines')
            return '%s %s' % (word, a) if not b else '%s %s to %s' % (word, a, b)
        out += TOKEN_RE.sub(rep, piece[1])
    return out.replace('|', '\\|') if in_table else out


def old_refs(page_text):
    """The numbers of the [RefN] entries that the section "References" of a page lists."""
    lines = page_text.split('\n')
    if '## References' not in lines:
        return {}
    out = {}
    for l in lines[lines.index('## References') + 1:]:
        if l.startswith('## '):
            break
        m = re.match(r'^- \[Ref(\d+)\] ?(.*)$', l)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


PAGE_HEADS = ['Short version: purpose', 'Words used here', 'Main flow', 'Behavior a reader must know', 'References']


def load_page(key, errors):
    """The sections of ann/KEY.page.md as {heading: [lines]}."""
    path = os.path.join(ANN, key + '.page.md')
    if not os.path.isfile(path):
        errors.append('%s is missing (the page sections of a new page)' % path)
        return {}
    sec, cur = collections.OrderedDict(), None
    for n, l in enumerate(read_text(path).split('\n'), 1):
        if l.startswith('## '):
            cur = l[3:].strip()
            if cur not in PAGE_HEADS:
                errors.append('%s:%d: unknown heading %r. Allowed: %s' % (path, n, cur, ', '.join(PAGE_HEADS)))
            if cur in sec:
                errors.append('%s:%d: heading %r twice' % (path, n, cur))
            sec[cur] = []
        elif l.startswith('#'):
            errors.append('%s:%d: only "## " headings are allowed' % (path, n))
        elif cur is None:
            if l.strip():
                errors.append('%s:%d: text before the first heading' % (path, n))
        else:
            sec[cur].append(l)
    for h in PAGE_HEADS[:3]:
        if h not in sec:
            errors.append('%s: the section "## %s" is missing' % (path, h))
    order = [h for h in PAGE_HEADS if h in sec]
    if list(sec) != order:
        errors.append('%s: the sections must stand in this order: %s' % (path, ', '.join(PAGE_HEADS)))
    for h in sec:
        while sec[h] and sec[h][-1].strip() == '':
            sec[h].pop()
        while sec[h] and sec[h][0].strip() == '':
            sec[h].pop(0)
    return sec


def lint_page(key, sec, nlines, blank, errors, warns):
    path = os.path.join(ANN, key + '.page.md')
    refs = {}
    for l in sec.get('References', []):
        m = re.match(r'^- \[Ref(\d+)\] (.+)$', l)
        if m:
            refs[int(m.group(1))] = m.group(2)
        elif l.strip():
            errors.append('%s: a line of "References" is not "- [RefN] text": %s' % (path, l[:60]))
    for h, lines in sec.items():
        if not lines:
            errors.append('%s: the section "## %s" is empty' % (path, h))
        for l in lines:
            if l.strip() == '':
                continue
            where = '%s, section "%s", "%s..."' % (os.path.basename(path), h, l[:40])
            if h == 'Short version: purpose':
                body, kind = l, 'line'
            elif h == 'Words used here':
                m = re.match(r'^- \*\*([^*]+)\*\*: (.+)$', l)
                if not m:
                    errors.append('%s: a line of "Words used here" must be "- **Term**: definition"' % where)
                    continue
                lint_text(m.group(1), where + ' (term)', nlines, blank, refs, errors, warns, allow_bspipe=True)
                body, kind = m.group(2), 'line'
            elif h == 'Main flow':
                m = re.match(r'^\d+\. (.+)$', l)
                if not m:
                    errors.append('%s: a line of "Main flow" must be "N. step"' % where)
                    continue
                body, kind = m.group(1), 'line'
            elif h == 'Behavior a reader must know':
                m = re.match(r'^(?:  )?- (.+)$', l)
                if not m:
                    errors.append('%s: a line of this section must be "- text" (or "  - text" one level below)' % where)
                    continue
                body, kind = m.group(1), 'line'
            else:
                m = re.match(r'^- \[Ref\d+\] (.+)$', l)
                if not m:
                    continue
                body, kind = m.group(1), 'ref'
            lint_text(body, where, nlines, blank, refs, errors, warns, allow_bspipe=True, kind=kind)
    short = ' '.join(sec.get('Short version: purpose', []))
    if len(re.findall(r'[.!?](?: |$)', short)) > 3:
        errors.append('%s: "Short version: purpose" has more than three sentences' % path)
    return refs


def check(key, quiet=False, lo=None, hi=None):
    """Test the annotation of key. Returns (errors, warnings, data). With lo and hi: only the lines lo to hi."""
    e = entry(key)
    if 'same_as' in e:
        errs, warns, data = check(e['same_as'], True)
        return errs, warns, data
    if lo is not None:
        return check_range(key, lo, hi)
    src, sha, nbytes = source_lines(e['src'])
    errors, warns = [], []
    if sha != e['sha256']:
        errors.append('%s changed after the manifest was written. Tell the main session.' % e['src'])
    n = len(src)
    blank = {i for i in range(1, n + 1) if src[i - 1].strip() == ''}
    own, seed, parts = load_ann(key, errors)
    if e['mode'] == 'new':
        sec = load_page(key, errors)
        refs = lint_page(key, sec, n, blank, errors, warns)
    else:
        sec = {}
        refs = old_refs(read_text(backup_or_page(e)))
    merged = dict(seed)
    merged.update(own)
    for k in sorted(own):
        if k < 1 or k > n:
            errors.append('line %d: the file has %d lines' % (k, n))
        elif k in blank:
            errors.append('line %d is blank in the source. A blank line gets no explanation' % k)
    for k in sorted(merged):
        if 1 <= k <= n and k not in blank:
            bsp = '\\|' in src[k - 1]
            lint_text(merged[k], 'line %d%s' % (k, '' if k in own else ' (seed)'), n, blank, refs, errors, warns,
                      allow_bspipe=bsp)
    missing = [k for k in range(1, n + 1) if k not in blank and k not in merged]
    if missing:
        runs, a = [], missing[0]
        for x, y in zip(missing, missing[1:] + [None]):
            if y != x + 1:
                runs.append('%d' % a if a == x else '%d-%d' % (a, x))
                a = y
        errors.append('%d lines have no explanation: %s%s' % (len(missing), ', '.join(runs[:40]),
                                                            ' ...' if len(runs) > 40 else ''))
    if parts:
        want = 1
        for a, b, title, where in parts:
            if a != want:
                errors.append('%s: this part starts at line %d. The part before it ends at line %d' % (where, a, want - 1))
            if b < a or b > n:
                errors.append('%s: the part ends at line %d (file: %d lines)' % (where, b, n))
            if b - a + 1 > 200:
                errors.append('%s: the part has %d lines (limit 200). Split it' % (where, b - a + 1))
            lint_text(title, where + ' (title)', n, blank, None, errors, warns)
            if len(title) > 90:
                errors.append('%s: the title has more than 90 characters' % where)
            if all(i in blank for i in range(a, min(b, n) + 1)):
                errors.append('%s: the part holds blank lines only' % where)
            want = b + 1
        if want != n + 1:
            errors.append('the parts end at line %d. The file has %d lines' % (want - 1, n))
    elif n > 80:
        errors.append('a file with more than 80 lines needs "@part A-B title" lines that cover lines 1 to %d' % n)
    data = {'entry': e, 'src': src, 'own': own, 'seed': seed, 'merged': merged, 'parts': parts, 'sec': sec,
            'refs': refs, 'blank': blank}
    if not quiet:
        for w in warns[:15]:
            print('warning: ' + w)
        if len(warns) > 15:
            print('... %d more warnings' % (len(warns) - 15))
        for x in errors[:80]:
            print('ERROR: ' + x)
        if len(errors) > 80:
            print('... %d more errors' % (len(errors) - 80))
        print('%s: %d lines, %d not blank, %d explained (%d from the seed), %d parts. %s' % (
            key, n, n - len(blank), len([k for k in merged if 1 <= k <= n and k not in blank]),
            len([k for k in merged if k not in own]), len(parts), 'OK' if not errors else '%d ERRORS' % len(errors)))
    return errors, warns, data


def check_range(key, lo, hi):
    """The test of check() for the lines lo to hi only. Used while two writers share one large file."""
    e = entry(key)
    src, sha, nbytes = source_lines(e['src'])
    n = len(src)
    if not (1 <= lo <= hi <= n):
        die('the file has %d lines' % n)
    errors, warns = [], []
    blank = {i for i in range(1, n + 1) if src[i - 1].strip() == ''}
    own, seed, parts = load_ann(key, errors)
    refs = old_refs(read_text(backup_or_page(e))) if e['mode'] != 'new' else None
    merged = dict(seed)
    merged.update(own)
    for k in sorted(own):
        if lo <= k <= hi and k in blank:
            errors.append('line %d is blank in the source. A blank line gets no explanation' % k)
    for k in sorted(merged):
        if lo <= k <= hi and k not in blank:
            lint_text(merged[k], 'line %d' % k, n, blank, refs, errors, warns, allow_bspipe='\\|' in src[k - 1])
    missing = [k for k in range(lo, hi + 1) if k not in blank and k not in merged]
    if missing:
        runs, a = [], missing[0]
        for x, y in zip(missing, missing[1:] + [None]):
            if y != x + 1:
                runs.append('%d' % a if a == x else '%d-%d' % (a, x))
                a = y
        errors.append('%d lines have no explanation: %s%s' % (len(missing), ', '.join(runs[:40]),
                                                            ' ...' if len(runs) > 40 else ''))
    mine = [p for p in parts if lo <= p[0] <= hi or lo <= p[1] <= hi]
    want = lo
    for a, b, title, where in mine:
        if a != want:
            errors.append('%s: this part starts at line %d. Wanted: line %d' % (where, a, want))
        if b < a or b > hi:
            errors.append('%s: the part ends at line %d (your range ends at line %d)' % (where, b, hi))
        if b - a + 1 > 200:
            errors.append('%s: the part has %d lines (limit 200). Split it' % (where, b - a + 1))
        lint_text(title, where + ' (title)', n, blank, None, errors, warns)
        if len(title) > 90:
            errors.append('%s: the title has more than 90 characters' % where)
        want = b + 1
    if want != hi + 1:
        errors.append('your parts end at line %d. Your range ends at line %d' % (want - 1, hi))
    for w in warns[:15]:
        print('warning: ' + w)
    for x in errors[:80]:
        print('ERROR: ' + x)
    if len(errors) > 80:
        print('... %d more errors' % (len(errors) - 80))
    print('%s, lines %d to %d: %d not blank, %d explained, %d parts. %s' % (
        key, lo, hi, len([k for k in range(lo, hi + 1) if k not in blank]),
        len([k for k in merged if lo <= k <= hi and k not in blank]), len(mine),
        'OK' if not errors else '%d ERRORS' % len(errors)))
    return errors, warns, None


# ----------------------------------------------------------------------------- page text

def code_span(s):
    longest = max([len(r) for r in re.findall(r'`+', s)] or [0])
    pad = ' ' if (s.startswith('`') or s.endswith('`') or (s.startswith(' ') and s.endswith(' '))) else ''
    return '`' * (longest + 1) + pad + s + pad + '`' * (longest + 1)


def span_text(cell):
    """The content of a code span as a Markdown reader gives it."""
    n = len(cell) - len(cell.lstrip('`'))
    if n == 0 or not cell.endswith('`' * n) or len(cell) < 2 * n + 1:
        return None
    c = cell[n:-n]
    if c.startswith(' ') and c.endswith(' ') and c.strip() != '':
        c = c[1:-1]
    return c


def ranges(a, b):
    return 'line %d' % a if a == b else 'lines %d to %d' % (a, b)


def line_map(old, new):
    rows = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, old, new, autojunk=False).get_opcodes():
        o = ranges(i1 + 1, i2) if i2 > i1 else '(none)'
        n = ranges(j1 + 1, j2) if j2 > j1 else '(none)'
        what = {'equal': 'equal', 'insert': 'added', 'delete': 'removed', 'replace': 'changed'}[tag]
        rows.append('| %s | %s | %s |' % (o, n, what))
    return rows


def backup_or_page(e):
    """The page as it was before this tool changed it."""
    if e['mode'] == 'section':
        b = BACKUP + '/' + e['key'] + '.md'
        return b if os.path.isfile(b) else e['page']
    return e['old_page']


def fence(line):
    return '~~~~' if '```' in line else '```'


def section_lines(e, d, own_e=None):
    """The lines of the section "Source and explanation, line by line"."""
    own_e = own_e or e
    src, merged, parts = d['src'], d['merged'], d['parts']
    n = len(src)
    out = [SECTION, '']
    w = out.append
    if own_e['mode'] in ('section', 'copy'):
        heads = [OLD_SECTION_RE.match(l) for l in read_text(backup_or_page(e)).split('\n')]
        by_line = any(m and m.group(1) == 'line by line' for m in heads)
        w('- This section was written on %s. It replaces an earlier table that %s.'
          % (TODAY, 'also had one row per line' if by_line else 'explained the source in groups of lines'))
    if own_e['in_repo']:
        w('- Text shown: the file `%s` of the code repo `%s` (%d lines, %d bytes, sha256 `%s`).'
          % (own_e['key'], REPO, n, own_e['bytes'], own_e['sha256']))
    else:
        w('- Text shown: the file `%s` in this folder (%d lines, %d bytes, sha256 `%s`). The code repo `%s` holds no copy of it.'
          % (os.path.basename(own_e['key']), n, own_e['bytes'], own_e['sha256'], REPO))
    differs = False
    if 'old_src' in e and own_e['in_repo']:
        differs = e['old_sha256'] != e['sha256']
        if not differs:
            w('- The other sections of this page were written for the file `%s`. It has the same sha256. '
              'So the line numbers in those sections fit the tables below.' % e['old_src'])
        else:
            w('- The other sections of this page describe an older text of the file: `%s` (%d lines, sha256 `%s`). '
              'Their line numbers are line numbers of the older text. The first table below maps them to the lines shown here.'
              % (e['old_src'], e['old_lines'], e['old_sha256']))
    w('- Each row of a source table holds one line of the source: the line number, the line itself (copied by a script) '
      'and its explanation. A blank line of the source has no row.')
    w('- In the raw text of this page, each `|` of the source is written `\\|`. A plain `|` would end the table cell. '
      'A Markdown viewer shows `|`.')
    bsp = [i for i in range(1, n + 1) if '\\|' in src[i - 1]]
    if bsp:
        w('- %s a backslash directly before a `|`: %s. Markdown readers do not agree on how to read this pair in a table cell. '
          'So such a line stands in a code block between two tables, with its explanation below it.'
          % ('One line holds' if len(bsp) == 1 else '%d lines hold' % len(bsp), ', '.join(ranges(i, i) for i in bsp)))
    w('')
    if differs:
        old, _, _ = source_lines(e['old_src'])
        w('Line numbers of the older text and of the text shown here:')
        w('')
        w('| Older text | Text shown here | Change |')
        w('|---|---|---|')
        out.extend(line_map(old, src))
        w('')
    plist = parts or [(1, n, None, '')]
    for a, b, title, _ in plist:
        if title is not None:
            w('### %s (%s)' % (render(title, False), ranges(a, b)))
            w('')
        open_table = False
        for i in range(a, b + 1):
            line = src[i - 1]
            if line.strip() == '':
                continue
            if '\\|' in line:
                if open_table:
                    w('')
                    open_table = False
                f = fence(line)
                w('Line %d holds a backslash directly before a `|`. It stands outside the table:' % i)
                w('')
                w(f + 'text')
                w(line)
                w(f)
                w('')
                w('Explanation of line %d: %s' % (i, render(merged[i], False)))
                w('')
                continue
            if not open_table:
                w(TABLE_HEAD)
                w(TABLE_RULE)
                open_table = True
            w('| %d | %s | %s |' % (i, code_span(line).replace('|', '\\|'), render(merged[i], True)))
        if open_table:
            w('')
    while out and out[-1] == '':
        out.pop()
    return out


def read_back(lines):
    """(line number, source line, explanation) of every source row and code block of a section, as written."""
    out, i = [], 0
    while i < len(lines):
        l = lines[i]
        m = re.match(r'^Line (\d+) holds a backslash directly before a `\|`\. It stands outside the table:$', l)
        if m:
            k = int(m.group(1))
            f = lines[i + 2][:-4]
            if lines[i + 1] != '' or lines[i + 2] not in ('```text', '~~~~text') or lines[i + 4] != f or lines[i + 5] != '':
                die('read back: the code block of line %d is not as written' % k)
            pre = 'Explanation of line %d: ' % k
            if not lines[i + 6].startswith(pre):
                die('read back: the explanation of line %d is missing' % k)
            out.append((k, lines[i + 3], lines[i + 6][len(pre):]))
            i += 7
            continue
        if l.startswith('| ') and re.match(r'^\| \d+ \| ', l):
            cells = re.split(r'(?<!\\)\|', l)
            if len(cells) != 5 or cells[0] != '' or cells[4] != '':
                die('read back: a table row does not have three cells: ' + l[:80])
            num, code, text = (c[1:-1] for c in cells[1:4])
            s = span_text(code)
            if s is None:
                die('read back: the source cell is not one code span: ' + l[:80])
            out.append((int(num), s.replace('\\|', '|'), text))
        i += 1
    return out


def inline_text(inlines, where):
    out = ''
    for x in inlines:
        t = x['t']
        if t == 'Str':
            out += x['c']
        elif t in ('Space', 'SoftBreak'):
            out += ' '
        elif t == 'Code':
            out += '\x01' + x['c'][1] + '\x02'
        else:
            die('pandoc: %s holds an element of the kind %s. Only text and code spans are allowed' % (where, t))
    return out


def plain_norm(text):
    """The rendered explanation with code spans marked the same way as inline_text marks them."""
    out = ''
    for piece in spans(text):
        if piece[0] == 'code':
            c = piece[1]
            if c.startswith(' ') and c.endswith(' ') and c.strip() != '':
                c = c[1:-1]
            out += '\x01' + c + '\x02'
        else:
            out += piece[1]
    return re.sub(r' +', ' ', out).strip()


def pandoc_check(md_lines, expect, whole_page=False):
    """Read the text with pandoc (reader gfm). Test that it holds no HTML and that every source row is exact."""
    exe = shutil.which('pandoc')
    if not exe:
        die('the program pandoc was not found')
    with tempfile.NamedTemporaryFile('w', suffix='.md', delete=False, encoding='utf-8') as f:
        f.write('\n'.join(md_lines) + '\n')
        tmp = f.name
    try:
        ast_text = subprocess.run([exe, '-f', 'gfm', '-t', 'json', '--preserve-tabs', '--wrap=none', tmp], check=True,
                                  stdout=subprocess.PIPE, universal_newlines=True).stdout
    finally:
        os.remove(tmp)
    if '"t":"RawBlock"' in ast_text or '"t":"RawInline"' in ast_text:
        die('pandoc finds an HTML element in the text')
    ast = json.loads(ast_text)
    if ast['pandoc-api-version'][:2] != [1, 20]:
        die('this check was written for pandoc-types 1.20 (pandoc 2.9). Found %s' % ast['pandoc-api-version'])
    if whole_page:
        return 0
    got, pending = [], None
    for blk in ast['blocks']:
        t = blk['t']
        if t == 'Table':
            head = [inline_text(c[0]['c'], 'a table head') if c else '' for c in blk['c'][3]]
            if head == ['Older text', 'Text shown here', 'Change']:
                continue
            if head != ['Line', 'Source', 'Explanation']:
                die('pandoc: a table has the head %s' % head)
            for row in blk['c'][4]:
                if len(row) != 3 or any(len(c) != 1 or c[0]['t'] != 'Plain' for c in row):
                    die('pandoc: a row does not have three plain cells')
                num = inline_text(row[0][0]['c'], 'a line number cell')
                code = row[1][0]['c']
                if len(code) != 1 or code[0]['t'] != 'Code':
                    die('pandoc: the source cell of line %s is not one code span' % num)
                got.append((int(num), code[0]['c'][1], inline_text(row[2][0]['c'], 'the explanation of line ' + num)))
        elif t == 'CodeBlock':
            pending = blk['c'][1]
            if pending.endswith('\n'):       # the reader gfm of pandoc 2.9 keeps the line end of a fenced block
                pending = pending[:-1]
        elif t == 'Para':
            txt = inline_text(blk['c'], 'a paragraph')
            m = re.match(r'^Explanation of line (\d+): (.*)$', txt, re.S)
            if m:
                if pending is None:
                    die('pandoc: the explanation of line %s has no code block before it' % m.group(1))
                got.append((int(m.group(1)), pending, m.group(2)))
                pending = None
        elif t not in ('Header', 'BulletList', 'Plain', 'OrderedList'):
            die('pandoc: the section holds a block of the kind %s' % t)
    want = [(k, s, plain_norm(x)) for k, s, x in expect]
    got = [(k, s, re.sub(r' +', ' ', x).strip()) for k, s, x in got]
    if got != want:
        for g, x in zip(got, want):
            if g != x:
                die('pandoc reads line %d differently:\n  page  : %r\n  wanted: %r' % (x[0], g, x))
        die('pandoc reads %d source rows. The source has %d lines that are not blank' % (len(got), len(want)))
    return len(got)


def page_sections_new(d):
    out = []
    for h in PAGE_HEADS[:4]:
        if h in d['sec']:
            out += ['## ' + h, ''] + [render(l, False) if l.strip() else l for l in d['sec'][h]] + ['']
    refs = []
    if 'References' in d['sec']:
        refs = ['', '## References', ''] + [render(l, False) for l in d['sec']['References']]
    return out, refs


def build(key, quiet=False):
    e = entry(key)
    errors, warns, d = check(key, True)
    if errors:
        die('%s: %d errors in the annotation. Run: check %s' % (key, len(errors), akey(e)))
    canon = d['entry']
    src = d['src']
    name = os.path.basename(key)
    eff = dict(canon)
    eff.update({'key': e['key'], 'bytes': e['bytes'], 'sha256': e['sha256'], 'in_repo': e['in_repo'],
                'mode': canon['mode'] if 'same_as' in e else e['mode']})
    sect = section_lines(canon, d, eff)
    expect = [(i, src[i - 1], render(d['merged'][i], '\\|' not in src[i - 1]))
              for i in range(1, len(src) + 1) if src[i - 1].strip()]
    if read_back(sect) != expect:
        got = read_back(sect)
        for g, x in zip(got, expect):
            if g != x:
                die('%s: read back differs at line %d:\n  page  : %r\n  wanted: %r' % (key, x[0], g, x))
        die('%s: read back gives %d rows, wanted %d' % (key, len(got), len(expect)))
    expect_plain = [(i, src[i - 1], render(d['merged'][i], False)) for i in range(1, len(src) + 1) if src[i - 1].strip()]
    nrows = pandoc_check(sect, expect_plain)
    mode = eff['mode']
    equal_note = ('- This file is equal to `%s` of the same repo (same sha256). Both pages hold the same explanation.'
                  % canon['key']) if 'same_as' in e else None
    if mode == 'section':
        if 'same_as' in e:
            die('%s: a page of the rerun folder cannot take its text from another file' % key)
        bpath = BACKUP + '/' + key + '.md'
        if not os.path.isfile(bpath):
            os.makedirs(os.path.dirname(bpath), exist_ok=True)
            shutil.copyfile(e['page'], bpath)
        old = read_text(bpath).split('\n')
        heads = [i for i, l in enumerate(old) if OLD_SECTION_RE.match(l)]
        if len(heads) != 1:
            die('%s: the older page has %d table sections' % (key, len(heads)))
        a = heads[0]
        b = next((i for i in range(a + 1, len(old)) if old[i].startswith('## ')), len(old))
        if b == len(old) or old[b] != '## References':
            die('%s: the section after the table section is not "## References"' % key)
        page = old[:a] + sect + [''] + old[b:]
        if page[:a] != old[:a] or page[len(page) - (len(old) - b):] != old[b:]:
            die('%s: a part of the page outside the table section would change' % key)
    elif mode == 'copy':
        old = read_text(canon['old_page']).split('\n')
        heads = [i for i, l in enumerate(old) if OLD_SECTION_RE.match(l)]
        first = next(i for i, l in enumerate(old) if l.startswith('## '))
        if len(heads) != 1:
            die('%s: the older page has %d table sections' % (key, len(heads)))
        a = heads[0]
        b = next((i for i in range(a + 1, len(old)) if old[i].startswith('## ')), len(old))
        if b == len(old) or old[b] != '## References':
            die('%s: the section after the table section is not "## References"' % key)
        role = [l for l in old[:first] if l.startswith('- Role in the whole-chip test:')]
        pre = ['# `%s` explained' % name, '',
               '- Source file: `%s` in the code repo `%s` (%s, %d lines, %d bytes).' % (key, REPO, LANG_NAME[e['lang']], len(src), e['bytes']),
               '- sha256 of the source when this page was built: `%s`.' % e['sha256']] + role
        if equal_note:
            pre.append(equal_note)
        pre += ['- This page was built on %s from an older page: `%s`. Every section except "Source and explanation, line by line" '
                'is a copy of a section of that page.' % (TODAY, canon['old_page']), '']
        page = pre + old[first:a] + sect + [''] + old[b:]
    else:
        body, refs = page_sections_new(d)
        pre = ['# `%s` explained, line by line' % name, '',
               '- Source file: `%s` in the code repo `%s` (%s, %d lines, %d bytes).' % (key, REPO, LANG_NAME[e['lang']], len(src), e['bytes']),
               '- sha256 of the source when this page was built: `%s`.' % e['sha256']]
        if equal_note:
            pre.append(equal_note)
        page = pre + [''] + body + sect + refs
        pandoc_check(page, None, whole_page=True)
    while page and page[-1] == '':
        page.pop()
    text = '\n'.join(page) + '\n'
    os.makedirs(os.path.dirname(e['page']), exist_ok=True)
    with open(e['page'], 'w', encoding='utf-8') as f:
        f.write(text)
    if not quiet:
        print('wrote %s: %d bytes, %d source rows. Own reader and pandoc (reader gfm) read every row equal to the source. '
              'pandoc finds no HTML element in the %s.' % (e['page'], len(text.encode()), nrows,
                                                        'page' if mode == 'new' else 'table section'))
    return nrows


# ----------------------------------------------------------------------------- commands

def cmd_show(key, a=None, b=None):
    e = entry(key)
    errors = []
    src, _, _ = source_lines(e['src'])
    own, seed, parts = load_ann(akey(e), errors)
    aside = {}
    ap = os.path.join(ANN, akey(e) + '.seed-aside')
    if os.path.isfile(ap):
        aside, _ = parse_ann(ap, True, errors)
    a = int(a) if a else 1
    b = min(int(b) if b else len(src), len(src))
    starts = {p[0]: p for p in parts}
    for i in range(a, b + 1):
        if i in starts:
            print('@part %d-%d %s' % starts[i][:3])
        print('%5d | %s' % (i, src[i - 1]))
        if src[i - 1].strip() == '':
            continue
        if i in own:
            print('      = %s' % own[i])
        elif i in seed:
            print('      ~ %s' % seed[i])
        else:
            print('      ? (no explanation yet)')
            if i in aside:
                print('      ! text of the other version, NOT taken over (adapt it): %s' % aside[i])


def old_key_map():
    with open(OLDT + '/manifest.json') as f:
        return {x['path']: x for x in json.load(f)['files']}


def cmd_old(key, lo=None, hi=None):
    lo = int(lo) if lo else 1
    hi = int(hi) if hi else 10 ** 9
    e = entry(key)
    if e['mode'] == 'new' and 'same_as' not in e:
        print('%s has no older page.' % key)
        return
    if 'same_as' in e:
        e = entry(e['same_as'])
    om = old_key_map().get(e['old_src'])
    if not om:
        print('no older annotation files for %s' % e['old_src'])
        return
    if e['old_sha256'] != e['sha256']:
        old, _, _ = source_lines(e['old_src'])
        new, _, _ = source_lines(e['src'])
        print('CAUTION: the older explanations were written for an older text (%d lines). Line numbers below are numbers '
              'of the OLDER text. Map:' % len(old))
        for r in line_map(old, new):
            print('   ' + r)
    if om['key'] == 'go':
        print('The page of go.sh was rewritten on 2026-11-24, one row per line. Read the rows in: ' + backup_or_page(e))
        return
    i = 1
    while os.path.isfile('%s/ann/%s.c%02d.json' % (OLDT, om['key'], i)):
        with open('%s/ann/%s.c%02d.json' % (OLDT, om['key'], i)) as f:
            for s in json.load(f)['segments']:
                if s['end'] < lo or s['start'] > hi:
                    continue
                print('--- older lines %d-%d%s' % (s['start'], s['end'], ('  [%s]' % s['heading']) if s.get('heading') else ''))
                print(s.get('text', ''))
        i += 1
    print('Overview of the older page (purpose, main flow, behavior notes, words, references): %s/ann/%s.overview.json'
          % (OLDT, om['key']))


def cmd_info(key):
    e = entry(key)
    for k in ('key', 'src', 'lang', 'lines', 'nonblank', 'bytes', 'sha256', 'mode', 'page', 'old_page', 'old_src',
              'same_as', 'seed_from'):
        if e.get(k) is not None:
            print('%-10s %s' % (k, e[k]))
    k = akey(e)
    print('annotation %s.ann  or  %s.ann.d/NN.ann' % (os.path.join(ANN, k), os.path.join(ANN, k)))
    if entry(k)['mode'] == 'new':
        print('page file  %s.page.md (sections of the new page)' % os.path.join(ANN, k))
    else:
        c = entry(k)
        refs = old_refs(read_text(backup_or_page(c)))
        print('This page keeps its other sections. Only these references may be cited in an explanation:')
        for r in sorted(refs):
            print('  [Ref%d] %s' % (r, refs[r][:260]))
        if not refs:
            print('  (none: cite nothing)')
    if 'same_as' in e:
        print('This file is equal to %s. It needs no annotation of its own.' % e['same_as'])


def cmd_seed(key):
    e = entry(key)
    parent = e.get('seed_from')
    if not parent:
        die('%s has no seed file in the manifest' % key)
    perr, _, pd = check(parent, True)
    if perr:
        die('the annotation of %s is not finished (%d errors). Finish it first.' % (parent, len(perr)))
    A, B = pd['src'], source_lines(e['src'])[0]
    amap = {}
    for i, j, n in difflib.SequenceMatcher(None, A, B, autojunk=False).get_matching_blocks():
        for k in range(n):
            amap[i + k + 1] = j + k + 1

    def neighbours_ok(a):
        """A short line (a closing brace, fi, done) is taken over only when the lines around it are equal too."""
        p = a - 1
        while p >= 1 and A[p - 1].strip() == '':
            p -= 1
        q = a + 1
        while q <= len(A) and A[q - 1].strip() == '':
            q += 1
        return (p < 1 or p in amap) and (q > len(A) or q in amap)

    # Names that belong to the other version only: its own file, the files of its folder, its runner name.
    def stems(k):
        folder = os.path.dirname(k)
        out = {os.path.splitext(os.path.basename(x))[0] for x in manifest() if os.path.dirname(x) == folder}
        first = folder.split('/')[0].split('-')[0]
        if first.startswith('bwx'):
            out.add(first)
        return out
    stale = (stems(parent) - stems(key)) | {os.path.splitext(os.path.basename(parent))[0]}
    stale_re = re.compile(r'(?<![A-Za-z0-9_])(?:%s)(?![A-Za-z0-9_])' % '|'.join(sorted(re.escape(x) for x in stale)))

    out, dropped, kept_aside = {}, 0, {}
    for a, b in sorted(amap.items()):
        if A[a - 1].strip() == '' or a not in pd['merged']:
            continue
        text = pd['merged'][a]
        if any(x not in B[b - 1] for x in set(stale_re.findall(text))):
            dropped += 1
            kept_aside[b] = text          # shown by "show" with the mark "!", as a text to adapt
            continue
        if REF_RE.search(text) or (len(A[a - 1].strip()) <= 4 and not neighbours_ok(a)):
            dropped += 1
            if REF_RE.search(text):
                kept_aside[b] = text
            continue
        ok = True

        def rep(m):
            nonlocal ok
            x = int(m.group(1))
            y = int(m.group(2)) if m.group(2) else None
            if x not in amap or (y is not None and (y not in amap or amap[y] - amap[x] != y - x)):
                ok = False
                return m.group(0)
            return '{L%d}' % amap[x] if y is None else '{L%d-%d}' % (amap[x], amap[y])
        new = ''
        for piece in spans(text):
            new += piece[2] if piece[0] == 'code' else TOKEN_RE.sub(rep, piece[1])
        if ok:
            out[b] = new
        else:
            dropped += 1
    path = os.path.join(ANN, key + '.seed')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for b in sorted(out):
            f.write('%d: %s\n' % (b, out[b]))
    def move_tokens(text):
        """The line tokens of a text that was set aside, moved to the lines of this file. {L?} = no equal line here."""
        def rep2(m):
            x = int(m.group(1))
            y = int(m.group(2)) if m.group(2) else None
            if x not in amap or (y is not None and (y not in amap or amap[y] - amap[x] != y - x)):
                return '{L?}'
            return '{L%d}' % amap[x] if y is None else '{L%d-%d}' % (amap[x], amap[y])
        return ''.join(pc[2] if pc[0] == 'code' else TOKEN_RE.sub(rep2, pc[1]) for pc in spans(text))

    with open(os.path.join(ANN, key + '.seed-aside'), 'w', encoding='utf-8') as f:
        for b in sorted(kept_aside):
            f.write('%d: %s\n' % (b, move_tokens(kept_aside[b])))
    # A proposal for the parts: each part of the other file starts at the first line of it that this file also has.
    starts = []
    for a, b2, title, _ in pd['parts']:
        got = [amap[x] for x in range(a, b2 + 1) if x in amap]
        if got and (not starts or min(got) > starts[-1][0]) and not TOKEN_RE.search(title):
            starts.append((min(got), title))
    if starts:
        starts[0] = (1, starts[0][1])
        with open(os.path.join(ANN, key + '.parts-proposal'), 'w', encoding='utf-8') as f:
            for (a, title), nxt in zip(starts, starts[1:] + [(len(B) + 1, '')]):
                f.write('@part %d-%d %s\n' % (a, nxt[0] - 1, title))
    nb = sum(1 for l in B if l.strip())
    print('%s: %d of %d lines that are not blank take over the explanation of the equal line of %s. '
          '%d equal lines got no seed (the text names the other version, a line reference or a citation did not carry over, '
          'or a short line in a changed place). %d lines need a new explanation. For %d of them "show" prints the text of '
          'the other file with the mark "!": adapt it, do not copy it blindly.'
          % (path, len(out), nb, parent, dropped, nb - len(out), len(kept_aside)))


def cmd_status():
    m = manifest()
    tot = collections.Counter()
    for key in sorted(m):
        e = m[key]
        if 'same_as' in e:
            state, done = 'equal to ' + e['same_as'], None
        else:
            errs = []
            own, seed, parts = load_ann(key, errs)
            src = source_lines(e['src'])[0]
            need = {i for i in range(1, len(src) + 1) if src[i - 1].strip()}
            done = len(need & (set(own) | set(seed)))
            if done == 0 and not own:
                state = 'not started' + (' (seed ready)' if seed else '')
            else:
                errors, _, _ = check(key, True)
                state = 'ready' if not errors else '%d errors' % len(errors)
            tot['need'] += len(need)
            tot['done'] += done
        built = os.path.isfile(e['page']) and (e['mode'] != 'section' or os.path.isfile(BACKUP + '/' + key + '.md'))
        tot['files'] += 1
        tot['built'] += built
        print('%-52s %-7s %5d %-22s %s' % (key, e['mode'], e['nonblank'], state, 'built' if built else ''))
    print('%d files, %d pages built. %d of %d lines explained.' % (tot['files'], tot['built'], tot['done'], tot['need']))


def cmd_build_all(only_ready):
    m = manifest()
    ok = bad = 0
    for key in sorted(m):
        try:
            if only_ready and check(key, True)[0]:
                continue
            build(key, True)
            ok += 1
        except Stop as x:
            bad += 1
            print('NOT BUILT %s: %s' % (key, x))
    print('%d pages built, %d not built' % (ok, bad))
    return bad


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd, args = argv[1], argv[2:]
    try:
        if cmd == 'manifest':
            cmd_manifest()
        elif cmd == 'check':
            if len(args) == 3:
                return 1 if check(args[0], False, int(args[1]), int(args[2]))[0] else 0
            return 1 if check(args[0])[0] else 0
        elif cmd == 'show':
            cmd_show(*args)
        elif cmd == 'old':
            cmd_old(*args)
        elif cmd == 'info':
            cmd_info(args[0])
        elif cmd == 'seed':
            cmd_seed(args[0])
        elif cmd == 'status':
            cmd_status()
        elif cmd == 'build':
            build(args[0])
        elif cmd == 'build-all':
            return 1 if cmd_build_all('--only-ready' in args) else 0
        else:
            print(__doc__)
            return 2
    except Stop as x:
        print('lbl.py: STOP: %s' % x)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
