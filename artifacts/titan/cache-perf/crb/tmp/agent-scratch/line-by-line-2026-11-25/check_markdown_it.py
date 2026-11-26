#!/usr/bin/env python3
"""check_markdown_it.py - second reading of the built pages with markdown-it-py (CommonMark rules plus the table rule).

Needs the Python package markdown-it-py (not installed on the agent server by default):
    python3 -m venv /some/scratch/venv ; /some/scratch/venv/bin/pip install markdown-it-py
    /some/scratch/venv/bin/python check_markdown_it.py

For every built page: the section "Source and explanation, line by line" must give back every
non-blank source line, in order, as a code span in column 2 of a table row (or as a fenced block
for a line that stands outside the table), and the section must hold no HTML token."""
import os, re, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lbl
from markdown_it import MarkdownIt

md = MarkdownIt('commonmark').enable('table')

def section(page):
    a = page.index(lbl.SECTION)
    b = next((i for i in range(a + 1, len(page)) if page[i].startswith('## ')), len(page))
    return page[a:b]

def check(e):
    src, sha, _ = lbl.source_lines(e['src'])
    page = lbl.read_text(e['page']).split('\n')
    sec = section(page)
    toks = md.parse('\n'.join(sec))
    got, html, bad = [], 0, []
    pending = None      # line number announced by "Line N holds a backslash ..."
    i = 0
    cells = None
    in_body = False
    for t in toks:
        if t.type in ('html_block',):
            html += 1
        if t.type == 'inline':
            for c in t.children or []:
                if c.type == 'html_inline':
                    html += 1
        if t.type == 'tbody_open':
            in_body = True
        elif t.type == 'tbody_close':
            in_body = False
        elif t.type == 'tr_open' and in_body:
            cells = []
        elif t.type == 'inline' and cells is not None:
            cells.append(t)
        elif t.type == 'tr_close' and in_body and cells is not None:
            if len(cells) != 3:
                bad.append('row with %d cells' % len(cells))
            else:
                num = cells[0].content.strip()
                ch = [c for c in (cells[1].children or [])]
                if len(ch) == 1 and ch[0].type == 'code_inline' and num.isdigit():
                    got.append((int(num), ch[0].content))
                elif num.isdigit():
                    bad.append('line %s: column 2 is not one code span (%s)' % (num, [c.type for c in ch][:5]))
                # other tables (the line map) have no number in column 1 or no code span: checked below by count
            cells = None
        elif t.type == 'inline' and cells is None:
            m = re.match(r'^Line (\d+) holds a backslash', t.content)
            if m:
                pending = int(m.group(1))
        elif t.type == 'fence' and pending is not None:
            got.append((pending, t.content[:-1] if t.content.endswith('\n') else t.content))
            pending = None
    want = [(n, src[n - 1]) for n in range(1, len(src) + 1) if src[n - 1].strip()]
    # the line-map table of five pages has rows "old | new | change" with text cells: they are not in `got`
    got_src = [g for g in got]
    ok = (got_src == want) and not html and not bad
    return ok, len(want), len(got_src), html, bad, [(a, b) for a, b in zip(got_src, want) if a != b][:3]

def main():
    m = lbl.manifest()
    n_ok = n_bad = rows = 0
    for key in sorted(m):
        e = m[key]
        if not os.path.isfile(e['page']):
            continue
        if e['mode'] == 'section' and not os.path.isfile(lbl.BACKUP + '/' + key + '.md'):
            continue
        try:
            ok, nw, ng, html, bad, diff = check(e)
        except Exception as x:
            ok, nw, ng, html, bad, diff = False, 0, 0, 0, [repr(x)], []
        rows += ng
        if ok:
            n_ok += 1
        else:
            n_bad += 1
            print('BAD %s: want %d rows, got %d, html tokens %d, %s %s' % (key, nw, ng, html, bad[:3], diff))
    print('markdown-it-py: %d pages give back every source line (%d rows), %d bad' % (n_ok, rows, n_bad))

if __name__ == '__main__':
    main()
