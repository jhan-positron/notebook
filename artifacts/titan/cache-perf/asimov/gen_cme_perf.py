#!/usr/bin/env python3
"""Builds asimov-cme-perf.html ("Asimov CME Memory Performance") from the raw
files of boot F1 and boot F2.

Run from any folder:  python3 gen_cme_perf.py
Standard library only.  The page has no time stamp: two builds give the same bytes.
The parts are in cme_page/ (see cme_page/API.md).
"""
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from cme_page import data, refs, shell, words, viz as V        # noqa: E402
from cme_page import (sec_setup, sec_glance, sec_latency, sec_l3,      # noqa: E402
                      sec_bandwidth, sec_callcost, sec_ocm, sec_open)

OUT = os.path.join(HERE, 'asimov-cme-perf.html')
TITLE = 'Asimov CME Memory Performance'
SUBTITLE = ('Memory latency and bandwidth of the CME (the Arm C1-SME2 matrix engine unit) on %s and %s. '
            'Every measured number is computed from the raw result files when the page is built.')
# Page order (sections 1 to 8; the word list and References follow).  Figure, table and reference
# numbers are given at the call, so the sections must be built in this order.
SECTIONS = [sec_setup, sec_glance, sec_latency, sec_l3, sec_bandwidth, sec_callcost, sec_ocm, sec_open]


def build_page():
    """Returns (page html, page object)."""
    D = data.load()
    S = shell.Page(TITLE, SUBTITLE % (D.boot_name['F1'], D.boot_name['F2']))
    refs.install(S, D)       # one References entry per file or document
    words.install(S, D)      # one definition per term
    short = sec_setup.short_version(D, V, S)
    parts = []
    for m in SECTIONS:
        body = m.build(D, V, S)
        # A module may return its own h2 (sec_l3 does).  The others return the body only.
        parts.append(body if body.lstrip().startswith('<h2') else (m.KEY, m.TITLE, body))
    return S.render(short, parts), S


def main():
    page, S = build_page()
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(page)
    print('wrote %s' % OUT)
    print('size: %d bytes' % len(page.encode('utf-8')))
    print('figures: %d  tables: %d  references: %d  terms: %d  lint warnings: %d' % (
        S.n_fig, S.n_table, len(S._ref_order), len(S._terms), len(S.warnings)))
    for k in S.unmapped_refs:
        print('note: reference key with no canonical entry (kept as the section wrote it): %s' % k)
    for k in S.unmapped_terms:
        print('note: term with no entry in words.py (kept as the section wrote it): %s' % k)


if __name__ == '__main__':
    main()
