#!/usr/bin/env python3
"""Measure sentence and paragraph size in prose (HTML, Markdown, chat text).

Library + CLI.  A "block" is one paragraph, one bullet, one table cell,
one heading or one caption.  Sentences are split inside each block.
"""
import re, sys, json, html
from html.parser import HTMLParser

# ---------- block extraction ----------

SKIP = {'script', 'style', 'svg', 'pre', 'code_block', 'head', 'title', 'noscript', 'template', 'nav'}
BLOCK = {'p', 'li', 'ul', 'ol', 'td', 'th', 'tr', 'table', 'thead', 'tbody', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
         'div', 'section', 'article', 'details', 'summary', 'figcaption', 'figure', 'blockquote', 'dt', 'dd',
         'dl', 'header', 'footer', 'main', 'aside', 'body', 'html', 'caption', 'br', 'hr'}
KIND = {'li': 'bullet', 'td': 'cell', 'th': 'cell', 'h1': 'heading', 'h2': 'heading', 'h3': 'heading',
        'h4': 'heading', 'h5': 'heading', 'h6': 'heading', 'summary': 'caption', 'figcaption': 'caption',
        'caption': 'caption', 'dt': 'cell', 'dd': 'bullet', 'p': 'para', 'blockquote': 'para'}


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.buf = []
        self.out = []
        self.skip = 0

    def kind(self):
        # nearest typed ancestor decides: a <p> inside <li> is a bullet, inside <td> is a cell
        ks = [KIND[t] for t in self.stack if t in KIND]
        for k in ('cell', 'heading', 'caption', 'bullet'):
            if k in ks:
                return k
        return 'para'

    def flush(self):
        t = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
        self.buf = []
        if t:
            self.out.append((self.kind(), t))

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
            return
        if self.skip:
            return
        if tag in BLOCK:
            self.flush()
            if tag not in ('br', 'hr'):
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag in BLOCK and tag not in ('br', 'hr'):
            self.flush()
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass

    def handle_data(self, data):
        if not self.skip:
            self.buf.append(data)


def html_blocks(text):
    p = Blocks()
    p.feed(text)
    p.flush()
    return p.out


def md_inline(s):
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('**', '').replace('__', '').replace('`', '')
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()


LIST = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?')


def md_blocks(text):
    out = []
    text = re.sub(r'^---\n.*?\n---\n', '', text, count=1, flags=re.S)       # frontmatter
    text = re.sub(r'(?ms)^[ \t]*(```|~~~).*?^[ \t]*\1[ \t]*$', '\n\n', text)  # code fences
    cur_kind, cur = None, []

    def flush():
        nonlocal cur_kind, cur
        if cur:
            t = md_inline(' '.join(cur))
            if t:
                out.append((cur_kind, t))
        cur_kind, cur = None, []

    for line in text.split('\n'):
        raw = line.rstrip()
        if not raw.strip():
            flush()
            continue
        s = raw.strip()
        if s.startswith('#'):
            flush()
            out.append(('heading', md_inline(s.lstrip('#'))))
            continue
        if s.startswith('|'):
            flush()
            if not re.match(r'^\|[\s:|-]+\|?$', s):
                for c in s.strip('|').split('|'):
                    c = md_inline(c)
                    if c:
                        out.append(('cell', c))
            continue
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', s):
            flush()
            continue
        if LIST.match(raw):
            flush()
            cur_kind, cur = 'bullet', [LIST.sub('', raw)]
            continue
        s = re.sub(r'^>\s?', '', s)
        if cur_kind is None:
            cur_kind = 'para'
        cur.append(s)
    flush()
    return out


def blocks_of(text, fmt):
    return html_blocks(text) if fmt == 'html' else md_blocks(text)


# ---------- sentences ----------

ABBR = ['e.g.', 'i.e.', 'est.', 'vs.', 'etc.', 'approx.', 'Fig.', 'fig.', 'No.', 'no.', 'cf.', 'Dr.', 'Mr.',
        'Ms.', 'Mrs.', 'St.', 'incl.', 'Ref.', 'ref.', 'Sec.', 'sec.', 'Eq.', 'eq.', 'al.', 'U.S.', 'a.m.', 'p.m.']
DOT = '․'
SPLIT = re.compile(r'(?<=[.!?])["\')\]”’]*\s+(?=["\'`(\[“‘]*[A-Z0-9`])')


def sentences(text):
    t = text
    for a in ABBR:
        # the abbreviation must start a word: "est." must not match inside "test."
        t = re.sub(r'(?<![A-Za-z])' + re.escape(a), a.replace('.', DOT), t)
    t = re.sub(r'(\d)\.(?=\d)', r'\1' + DOT, t)          # decimals
    t = re.sub(r'\b([A-Za-z])\.(?=\s+[a-z])', r'\1' + DOT, t)  # single letter + lowercase next
    parts = SPLIT.split(t)
    return [p.replace(DOT, '.').strip() for p in parts if p.strip()]


WORD = re.compile(r"[A-Za-z0-9]")


def nwords(s):
    return sum(1 for w in s.split() if WORD.search(w))


SUBORD = re.compile(r"\b(because|since|although|though|unless|whereas|while|when|whenever|if|until|after|before|"
                    r"so that|which|who|whose|where|that)\b", re.I)
SUB_STRICT = re.compile(r"\b(because|since|although|though|unless|whereas|while|when|whenever|if|until|"
                        r"so that|which|whose|where)\b", re.I)
JOIN = re.compile(r",\s+(and|or|but|so)\b", re.I)


def features(s):
    return dict(
        words=nwords(s),
        semicolon=';' in s,
        colon=bool(re.search(r':\s', s)),
        paren=len(re.findall(r'\([^)]*\)', s)),
        paren_words=sum(nwords(x) for x in re.findall(r'\([^)]*\)', s)),
        sub=len(SUB_STRICT.findall(s)),
        sub_loose=len(SUBORD.findall(s)),
        join=len(JOIN.findall(s)),
        commas=s.count(','),
        dash=bool(re.search(r'\s[—–-]\s', s)),
    )


def analyse(text, fmt):
    """Return list of dicts: one per block with its sentences."""
    res = []
    for kind, t in blocks_of(text, fmt):
        ss = sentences(t)
        res.append(dict(kind=kind, text=t, words=nwords(t), sents=[dict(text=s, **features(s)) for s in ss]))
    return res


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def quantile(xs, q):
    xs = sorted(xs)
    if not xs:
        return 0
    i = min(len(xs) - 1, int(round(q * (len(xs) - 1))))
    return xs[i]


def summary(blocks, kinds=('para', 'bullet')):
    sel = [b for b in blocks if b['kind'] in kinds]
    sents = [s for b in sel for s in b['sents'] if s['words'] >= 1]
    w = [s['words'] for s in sents]
    n = len(w)
    out = dict(blocks=len(sel), sentences=n, words=sum(w))
    if n:
        out.update(mean=sum(w) / n, median=quantile(w, .5), p90=quantile(w, .9), max=max(w),
                   over20=pct(sum(x > 20 for x in w), n), over25=pct(sum(x > 25 for x in w), n),
                   over30=pct(sum(x > 30 for x in w), n))
    return out


if __name__ == '__main__':
    path = sys.argv[1]
    fmt = 'html' if path.endswith('.html') else 'md'
    bl = analyse(open(path, errors='replace').read(), fmt)
    print(json.dumps(summary(bl), indent=1))
