#!/usr/bin/env python3
"""lbl_main.py - commands of the main session for the line-by-line pages (the writers use lbl.py only).

    index                 write S/code-pages.md, the list of all pages
    sample KEY [N [SEED [A B [own]]]]  print N random rows of KEY (source line and explanation) for a review,
                          with A B only from the lines A to B (0 0 = the whole file), with "own" only rows of the writer
    units                 lines per folder and what is still open
    pages-check           read every built page back: own reader and pandoc
    reseed-all [PREFIX]   run seed again for every seeded key that has rows of its own, in chain order, and check it
    glossary-check        list the definitions in the page files that differ from GLOSSARY.md
"""
import collections
import os
import random
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl  # noqa: E402

INDEX = lbl.S + '/code-pages.md'
LANG_SHORT = {'c': 'C', 'python': 'Python', 'bash': 'Bash', 'make': 'Makefile', 'text': 'text'}


def built(e):
    if not os.path.isfile(e['page']):
        return False
    return e['mode'] != 'section' or os.path.isfile(lbl.BACKUP + '/' + e['key'] + '.md')


def cmd_index():
    m = lbl.manifest()
    folders = collections.OrderedDict()
    for key in sorted(m):
        folders.setdefault(key.split('/')[0], []).append(m[key])
    other = []
    for root, dirs, names in os.walk(lbl.REPO):
        dirs[:] = sorted(d for d in dirs if d != '__pycache__')   # the cache that Python writes beside an imported module
        for name in sorted(names):
            rel = os.path.relpath(os.path.join(root, name), lbl.REPO)
            if rel not in m:
                other.append(rel)
    done = [e for e in m.values() if built(e)]
    out = []
    w = out.append
    w('# Pages that explain the code of `arm-crb/code`, line by line')
    w('')
    w('## Short version')
    w('')
    w('- This page lists one explanation page for each code file of the repo folder `%s`.' % lbl.REPO)
    w('- Each page shows the source of its file in tables: one row per line, with the line number, the line and its explanation.')
    w('- %d of %d pages are written (%d source lines in all). The list was built on %s.'
      % (len(done), len(m), sum(e['lines'] for e in m.values()), lbl.TODAY))
    w('')
    w('## Where the pages are')
    w('')
    w('- Files of the repo folder `%s`: the page of a file lies in this folder, under the name of the file plus `.md` '
      '(for example `go.sh.md`).' % lbl.RERUN)
    w('- Files of every other repo folder: the page lies below the folder `code` of this folder, under the same path as in the repo, '
      'plus `.md` (for example `code/kernels-2026-11-13/bandwidth.c.md`).')
    w('- A page shows the text that the file had in the repo when the page was built. The page gives the sha256 of that text.')
    w('')
    w('## Words used here')
    w('')
    w('- **Repo**: the code repository `/home/jhan/workspace/ai-proj/arm-crb`.')
    w('- **sha256**: a checksum. Two files with the same sha256 have the same content.')
    w('- **Equal file**: a file that has the same sha256 as another file of the repo. Its page holds the same explanation.')
    w('')
    w('## Pages')
    for folder, es in folders.items():
        w('')
        w('### `%s` (%d files, %d lines)' % (folder, len(es), sum(e['lines'] for e in es)))
        w('')
        w('| File | Language | Lines | Page |')
        w('|---|---|---:|---|')
        for e in es:
            rel = os.path.relpath(e['page'], lbl.S)
            name = e['key'][len(folder) + 1:]
            note = ''
            if 'same_as' in e:
                note = ' (equal to `%s`)' % e['same_as']
            page = '[%s](%s)' % (rel, rel) if built(e) else 'not written yet'
            w('| `%s`%s | %s | %d | %s |' % (name, note, LANG_SHORT[e['lang']], e['lines'], page))
    w('')
    w('## Files of the repo folder without a page')
    w('')
    w('These %d files hold data or notes, not code. They have no line-by-line page.' % len(other))
    w('')
    for rel in other:
        w('- `%s`' % rel)
    w('')
    text = '\n'.join(out)
    lbl.pandoc_check(out, None, whole_page=True)
    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write(text)
    print('wrote %s: %d of %d pages listed as written, %d files without a page' % (INDEX, len(done), len(m), len(other)))


def cmd_sample(key, n='25', seed='1', lo='1', hi='0', which='all'):
    errors, warns, d = lbl.check(key, True)
    src, merged = d['src'], d['merged']
    lo, hi = int(lo), int(hi) or len(src)
    lines = [i for i in range(lo, hi + 1) if src[i - 1].strip() and i in merged]
    if which == 'own':          # only the rows that the writer of this key wrote (mark "="), not the rows taken over
        lines = [i for i in lines if i in d['own']]
    rnd = random.Random(int(seed))
    pick = sorted(rnd.sample(lines, min(int(n), len(lines))))
    print('%s: %d rows of %d (seed %s). errors of check: %d' % (key, len(pick), len(lines), seed, len(errors)))
    for i in pick:
        print('%5d | %s' % (i, src[i - 1]))
        print('      %s %s' % ('=' if i in d['own'] else '~', merged[i]))


def cmd_units():
    m = lbl.manifest()
    per = collections.OrderedDict()
    for key in sorted(m):
        e = m[key]
        f = key.split('/')[0]
        p = per.setdefault(f, collections.Counter())
        p['files'] += 1
        p['nonblank'] += e['nonblank']
        if 'same_as' in e:
            p['equal'] += 1
            continue
        errs = []
        own, seed, parts = lbl.load_ann(key, errs)
        src = lbl.source_lines(e['src'])[0]
        need = {i for i in range(1, len(src) + 1) if src[i - 1].strip()}
        p['own'] += len(need & set(own))
        p['seed'] += len((need & set(seed)) - set(own))
        p['open'] += len(need - set(own) - set(seed))
        p['built'] += built(e)
    print('%-24s %5s %8s %8s %8s %8s %6s' % ('folder', 'files', 'lines', 'written', 'seeded', 'open', 'built'))
    tot = collections.Counter()
    for f, p in per.items():
        print('%-24s %5d %8d %8d %8d %8d %6d' % (f, p['files'], p['nonblank'], p['own'], p['seed'], p['open'], p['built']))
        tot.update(p)
    print('%-24s %5d %8d %8d %8d %8d %6d' % ('all', tot['files'], tot['nonblank'], tot['own'], tot['seed'], tot['open'], tot['built']))


def cmd_pages_check():
    """Read each built page back from the disk: the table section must hold the source of today, line for line."""
    m = lbl.manifest()
    ok = bad = 0
    for key in sorted(m):
        e = m[key]
        if not built(e):
            continue
        try:
            src, sha, _ = lbl.source_lines(e['src'])
            page = lbl.read_text(e['page']).split('\n')
            a = page.index(lbl.SECTION)
            b = next((i for i in range(a + 1, len(page)) if page[i].startswith('## ')), len(page))
            got = [(k, s) for k, s, _ in lbl.read_back(page[a:b])]
            want = [(i, src[i - 1]) for i in range(1, len(src) + 1) if src[i - 1].strip()]
            if sha != e['sha256']:
                raise lbl.Stop('the source changed after the manifest was written')
            if got != want:
                raise lbl.Stop('the rows of the page are not the lines of the source')
            if ('`%s`' % sha) not in '\n'.join(page[a:a + 8]):
                raise lbl.Stop('the section does not name the sha256 of the source')
            ok += 1
        except (lbl.Stop, ValueError) as x:
            bad += 1
            print('BAD %s: %s' % (key, x))
    print('%d pages read back equal to their source, %d bad' % (ok, bad))
    return bad


def chain_order():
    """The seeded keys, each after the key that it takes its rows from."""
    out, left = [], dict(lbl.SEED)
    while left:
        ready = sorted(c for c, p in left.items() if p not in left)
        if not ready:
            raise lbl.Stop('the list SEED holds a loop')
        for c in ready:
            out.append(c)
            del left[c]
    return out


def cmd_reseed_all(only=None):
    """Run seed again for every seeded key whose own rows exist, in chain order. Then check each of them."""
    bad = 0
    for child in chain_order():
        if only and not child.startswith(only):
            continue
        errs = []
        own, seed, parts = lbl.load_ann(child, errs)
        if not own:
            print('skipped (no rows of its own yet): %s' % child)
            continue
        perr = lbl.check(lbl.SEED[child], True)[0]
        if perr:
            print('skipped (the file that it takes rows from has %d errors): %s' % (len(perr), child))
            bad += 1
            continue
        before = dict(seed)
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            lbl.cmd_seed(child)
        errs = []
        own2, seed2, _ = lbl.load_ann(child, errs)
        changed = sum(1 for k in seed2 if k not in own2 and before.get(k) != seed2[k])
        lost = sorted(k for k in before if k not in seed2 and k not in own2)
        errors = lbl.check(child, True)[0]
        print('%-45s seed rows in use that changed: %4d, lost: %3d, check: %s' % (
            child, changed, len(lost), 'OK' if not errors else '%d ERRORS' % len(errors)))
        if errors:
            bad += 1
            for x in errors[:6]:
                print('    ' + x[:300])
    return bad


def cmd_glossary_check():
    """Compare the definitions in the page files with GLOSSARY.md, term by term."""
    gl = {}
    for l in lbl.read_text(os.path.join(lbl.HERE, 'GLOSSARY.md')).split('\n'):
        m = re.match(r'^- \*\*([^*]+)\*\*: (.+)$', l)
        if m:
            gl[m.group(1)] = m.group(2)
    diff = collections.defaultdict(list)
    n = 0
    for root, dirs, names in os.walk(lbl.ANN):
        for name in names:
            if not name.endswith('.page.md'):
                continue
            n += 1
            for l in lbl.read_text(os.path.join(root, name)).split('\n'):
                m = re.match(r'^- \*\*([^*]+)\*\*: (.+)$', l)
                if m and m.group(1) in gl and m.group(2) != gl[m.group(1)]:
                    diff[(m.group(1), m.group(2))].append(os.path.relpath(os.path.join(root, name), lbl.ANN))
    print('%d page files, %d glossary terms, %d other wordings of a glossary term' % (n, len(gl), len(diff)))
    for (term, text), files in sorted(diff.items(), key=lambda x: (x[0][0], -len(x[1]))):
        print('%s  [%d files, for example %s]\n    page    : %s\n    glossary: %s' % (term, len(files), files[0], text[:230], gl[term][:230]))


def main(argv):
    cmd, args = (argv[1], argv[2:]) if len(argv) > 1 else ('', [])
    try:
        if cmd == 'index':
            cmd_index()
        elif cmd == 'sample':
            cmd_sample(*args)
        elif cmd == 'units':
            cmd_units()
        elif cmd == 'pages-check':
            return 1 if cmd_pages_check() else 0
        elif cmd == 'reseed-all':
            return 1 if cmd_reseed_all(*args) else 0
        elif cmd == 'glossary-check':
            cmd_glossary_check()
        else:
            print(__doc__)
            return 2
    except lbl.Stop as x:
        print('lbl_main.py: STOP: %s' % x)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
