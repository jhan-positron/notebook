#!/usr/bin/env python3
"""Extract the visible text of an HTML page as one text block per line.

Blocks: p, li, td, th, caption, figcaption, h1-h6, summary, dt, dd, div with direct text,
SVG text elements, SVG <title>, and the attributes title / aria-label / data-tip* (tooltips).
Usage: extract.py page.html > blocks.txt
"""
import re
import sys
from bs4 import BeautifulSoup, NavigableString, Comment

BLOCK = {'p', 'li', 'td', 'th', 'caption', 'figcaption', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
         'summary', 'dt', 'dd', 'text', 'title', 'pre', 'desc', 'button', 'label'}
CONTAINER = {'div', 'section', 'details', 'figure', 'body', 'ul', 'ol', 'table', 'tr', 'tbody',
             'thead', 'svg', 'g', 'main', 'article', 'header', 'footer', 'nav', 'span', 'a'}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def main(path):
    html = open(path, encoding='utf-8').read()
    soup = BeautifulSoup(html, 'html.parser')
    for t in soup(['script', 'style']):
        t.decompose()
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()
    out = []

    def has_block_child(el):
        for d in el.descendants:
            if getattr(d, 'name', None) in BLOCK and d.name not in ('title',):
                return True
        return False

    def walk(el, path):
        name = getattr(el, 'name', None)
        if name is None:
            return
        # attributes that carry text
        for attr, val in el.attrs.items():
            if attr in ('title', 'aria-label', 'alt') or attr.startswith('data-tip') or attr in ('data-title', 'data-label', 'data-note'):
                v = norm(val if isinstance(val, str) else ' '.join(val))
                if v:
                    out.append(f'[{attr}@{name}] {v}')
        if name in BLOCK and not has_block_child(el):
            t = norm(el.get_text(' '))
            if t:
                out.append(f'<{name}> {t}')
            # still walk for attributes of descendants
            for d in el.find_all(True):
                for attr, val in d.attrs.items():
                    if attr in ('title', 'aria-label', 'alt') or attr.startswith('data-tip') or attr in ('data-title', 'data-label', 'data-note'):
                        v = norm(val if isinstance(val, str) else ' '.join(val))
                        if v:
                            out.append(f'[{attr}@{d.name}] {v}')
            return
        # mixed: direct text nodes of a container
        buf = []
        for ch in el.children:
            if isinstance(ch, NavigableString):
                buf.append(str(ch))
            else:
                if ch.name in BLOCK or has_block_child(ch) or ch.name in ('div', 'section', 'details', 'figure', 'ul', 'ol', 'table', 'svg', 'g'):
                    t = norm(' '.join(buf))
                    if t:
                        out.append(f'<{name}:text> {t}')
                    buf = []
                    walk(ch, path + [name])
                else:
                    buf.append(ch.get_text(' '))
                    for d in [ch] + ch.find_all(True):
                        for attr, val in d.attrs.items():
                            if attr in ('title', 'aria-label', 'alt') or attr.startswith('data-tip') or attr in ('data-title', 'data-label', 'data-note'):
                                v = norm(val if isinstance(val, str) else ' '.join(val))
                                if v:
                                    out.append(f'[{attr}@{d.name}] {v}')
        t = norm(' '.join(buf))
        if t:
            out.append(f'<{name}:text> {t}')

    walk(soup, [])
    for line in out:
        print(line)


if __name__ == '__main__':
    main(sys.argv[1])
