#!/usr/bin/env python3
"""Builds asimov-c1nano-perf.html ("Asimov C1-Nano Memory Performance") from the raw
result files of boot F1 and of the supplementary boots E, B, C, D and R3.

Run from any folder:
  python3 gen_c1nano_perf.py                       writes asimov-c1nano-perf.html beside this file
  python3 gen_c1nano_perf.py --out PATH            writes PATH
  python3 gen_c1nano_perf.py --only latency,ocm    builds only these sections (a partial build)

Standard library only.  The page has no time stamp: two builds give the same bytes.
The parts are in c1nano_page/ (see c1nano_page/API.md and c1nano_page/IDS.md).

A partial build is a build with --only, or a build in which a section module does not
exist yet.  In a partial build a cross-reference to a heading, figure or table that is
not on the page is written as plain text.  In a full build it raises.
"""
import argparse
import importlib
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from c1nano_page import ids, refs, shell, words, viz as V        # noqa: E402

OUT = os.path.join(HERE, 'asimov-c1nano-perf.html')
TITLE = 'Asimov C1-Nano Memory Performance'
SUBTITLE = ('Measured by the cache-mem-perf benchmark on the emulated Asimov chip. Every measured number is '
            'computed from the raw result files when the page is built.')
# Page order (sections 1 to 8; "Words used here" and References follow).  Figure, table and
# reference numbers are given at the call, so the sections are built in this order.
SECTIONS = ['sec_setup', 'sec_glance', 'sec_latency', 'sec_bandwidth', 'sec_multicore', 'sec_ocm', 'sec_mesh',
            'sec_open']
KEYS = [name[4:] for name in SECTIONS]


def _module(name):
    """The module c1nano_page.<name>, or None when its file does not exist yet."""
    full = 'c1nano_page.' + name
    try:
        return importlib.import_module(full)
    except ModuleNotFoundError as e:
        if e.name == full:
            return None
        raise


def _visible_words(html_):
    v = shell._Vis()
    v.feed(html_)
    return len(''.join(v.full).split())


def build_page(only=None):
    """Returns (page html, page object, notes).  only: section keys to build, or None for all."""
    notes = []
    data = _module('data')
    if data is None:
        notes.append('the data layer c1nano_page/data.py does not exist yet: the sections get D = None')
        D = None
    else:
        D = data.load()
    S = shell.Page(TITLE, SUBTITLE)
    S.lenient = bool(only)
    refs.install(S, D)       # one References entry per file or document
    words.install(S, D)      # one definition per term
    mods = []
    for name in SECTIONS:
        key = name[4:]
        if only and key not in only:
            continue
        m = _module(name)
        if m is None:
            notes.append('section module c1nano_page/%s.py does not exist yet: skipped' % name)
            S.lenient = True
            continue
        mods.append((key, m))
    short = None
    for key, m in mods:
        if key == 'setup' and hasattr(m, 'short_version'):
            short = m.short_version(D, V, S)
    if short is None:
        short = ('<p>Partial build. The Short version and its headline figure are written by '
                 '<code>sec_setup.short_version(D, V, S)</code>.</p>')
        if not S.lenient:
            raise SystemExit('sec_setup has no short_version(D, V, S)')
    parts = []
    for key, m in mods:
        if getattr(m, 'KEY', key) != key:
            raise SystemExit('c1nano_page/sec_%s.py: KEY must be %r' % (key, key))
        body = m.build(D, V, S)
        used = re.findall(r'<h3 id="([^"]+)">', body)
        for i in used:
            if i not in ids.H3[key]:
                notes.append('section %s: subsection id %r is not in IDS.md' % (key, i))
        for i in ids.H3[key]:
            if i not in used:
                notes.append('section %s: subsection id %r of IDS.md is not on the page' % (key, i))
        notes.append('section %s: %d words of visible text' % (key, _visible_words(body)))
        # A module may return its own h2.  The others return the body only.
        parts.append(body if body.lstrip().startswith('<h2') else (key, m.TITLE, body))
    page = S.render(short, parts)
    for i in S.unresolved:
        notes.append('partial build: cross-reference to %r is written as plain text' % i)
    return page, S, notes


def main():
    ap = argparse.ArgumentParser(description='Build the page "%s".' % TITLE)
    ap.add_argument('--out', default=OUT, help='file to write (default: %s)' % OUT)
    ap.add_argument('--only', default='', help='section keys to build, with commas: %s' % ','.join(KEYS))
    a = ap.parse_args()
    only = [k.strip() for k in a.only.split(',') if k.strip()]
    for k in only:
        if k not in KEYS:
            raise SystemExit('--only: unknown section key %r (the keys are %s)' % (k, ', '.join(KEYS)))
    page, S, notes = build_page(only or None)
    out = os.path.abspath(a.out)
    with open(out, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print('wrote %s' % out)
    print('size: %d bytes  visible words: %d' % (len(page.encode('utf-8')), _visible_words(page)))
    print('figures: %d  tables: %d  references: %d  terms: %d  lint warnings: %d' % (
        S.n_fig, S.n_table, len(S._ref_order), len(S._terms), len(S.warnings)))
    for n in notes:
        print('note: %s' % n)
    for k in S.unmapped_refs:
        print('note: reference key with no canonical entry (kept as the section wrote it): %s' % k)
    for k in S.unmapped_terms:
        print('note: term with no entry in words.py (kept as the section wrote it): %s' % k)


if __name__ == '__main__':
    main()
