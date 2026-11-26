#!/usr/bin/env python3
"""Count sentence and paragraph sizes in an HTML or Markdown file.

Prints one line for each of these, and exits with status 1 when it printed any:
  - a sentence of more than MAX_WORDS words               (plain-english Rule 3)
  - a sentence of more than SOFT_WORDS words that holds a join, a list,
    or a colon followed by more text                      (Rule 3, 21 to 25 words)
  - a paragraph or bullet of more than MAX_SENTENCES sentences   (Rule 4)
  - a parenthesis of more than MAX_PAREN words            (Rules 6 and 8)
  - a semicolon in prose                                  (Rule 3)

Usage:  check_lengths.py FILE [--max-words 25] [--soft-words 20] [--max-sentences 3] [--max-paren 8]
        check_lengths.py FILE --stats        (print the size distribution only)

A join is ", and", ", or", ", but" or ", so". A list is three or more commas.
The script cannot see a clause inside another clause. Check that by reading.

What it reads: paragraphs and list items. It skips code blocks, tables, headings,
captions, scripts, styles and SVG text.

Known limits:
  - A word is a token that holds a letter or a digit, so "2.8 GHz" is two words.
  - Text that an HTML page builds with JavaScript is not seen.
  - Chart legends written as plain <div> text can look like one long sentence.
"""
import html
import re
import sys
from html.parser import HTMLParser

# ---------- blocks: (kind, text, line) ----------

SKIP = {'script', 'style', 'svg', 'pre', 'head', 'title', 'noscript', 'template', 'nav'}
BLOCK = {'p', 'li', 'ul', 'ol', 'td', 'th', 'tr', 'table', 'thead', 'tbody', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
         'div', 'section', 'article', 'details', 'summary', 'figcaption', 'figure', 'blockquote', 'dt', 'dd',
         'dl', 'header', 'footer', 'main', 'aside', 'body', 'html', 'caption', 'br', 'hr'}
KIND = {'li': 'bullet', 'td': 'cell', 'th': 'cell', 'h1': 'heading', 'h2': 'heading', 'h3': 'heading',
        'h4': 'heading', 'h5': 'heading', 'h6': 'heading', 'summary': 'caption', 'figcaption': 'caption',
        'caption': 'caption', 'dt': 'cell', 'dd': 'bullet', 'p': 'para', 'blockquote': 'quote'}


class _Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.buf, self.out = [], [], []
        self.skip = 0
        self.line = None
        self.bold = None        # text of a <b>/<strong> that opens the block
        self.label = ''

    def kind(self):
        if any(q for _, q in self.stack):
            return 'quote'                      # text inside an element with class="...quote..."
        ks = [KIND[t] for t, _ in self.stack if t in KIND]
        for k in ('quote', 'cell', 'heading', 'caption', 'bullet'):
            if k in ks:
                return k
        return 'para'

    def flush(self):
        if self.bold is not None:               # unclosed bold: keep its text
            self.buf.append(self.bold)
        t = re.sub(r'\s+', ' ', ''.join(self.buf)).strip()
        if t:
            self.out.append((self.kind(), t, self.line or 0, self.label))
        self.buf, self.line, self.bold, self.label = [], None, None, ''

    def handle_starttag(self, tag, attrs):
        if tag in SKIP:
            self.skip += 1
        elif not self.skip and tag in ('b', 'strong') and not ''.join(self.buf).strip() and not self.label:
            self.bold = ''
        elif not self.skip and tag in BLOCK:
            self.flush()
            if tag not in ('br', 'hr'):
                self.stack.append((tag, 'quote' in (dict(attrs).get('class') or '')))

    def handle_endtag(self, tag):
        if tag in SKIP:
            self.skip = max(0, self.skip - 1)
        elif not self.skip and tag in ('b', 'strong') and self.bold is not None:
            lab, self.bold = self.bold.strip(), None
            if _is_label(lab):
                self.label = lab
            else:
                self.buf.append(lab)
        elif not self.skip and tag in BLOCK and tag not in ('br', 'hr'):
            self.flush()
            if any(t == tag for t, _ in self.stack):
                while self.stack and self.stack.pop()[0] != tag:
                    pass

    def handle_data(self, data):
        if not self.skip:
            if self.line is None and data.strip():
                self.line = self.getpos()[0]
            if self.bold is not None:
                self.bold += data
            else:
                self.buf.append(data)


def _is_label(t):
    """A bold run-in of at most 6 words that ends with a full stop or a colon: "Small reach." or "Not done:"."""
    return 0 < len(t.split()) <= 6 and t.rstrip()[-1:] in '.:'


def html_blocks(text):
    p = _Blocks()
    p.feed(text)
    p.flush()
    return p.out


def _inline(s):
    s = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('**', '').replace('__', '').replace('`', '')
    return html.unescape(re.sub(r'\s+', ' ', s)).strip()


_LIST = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?')


def md_blocks(text):
    out = []
    lines = text.split('\n')
    start = 0
    if lines and lines[0].strip() == '---':                     # frontmatter
        for i in range(1, len(lines)):
            if lines[i].strip() == '---':
                start = i + 1
                break
    kind, cur, line0, fence = None, [], 0, None

    def flush():
        nonlocal kind, cur
        if cur:
            raw_text = ' '.join(cur)
            label = ''
            m2 = re.match(r'^\s*\*\*([^*]{1,80})\*\*([.:]?)\s+(?=\S)', raw_text)
            if m2 and _is_label(m2.group(1).strip() + m2.group(2)):
                label, raw_text = m2.group(1).strip() + m2.group(2), raw_text[m2.end():]
            t = _inline(raw_text)
            if t:
                out.append((kind, t, line0, label))
        kind, cur = None, []

    for n in range(start, len(lines)):
        raw = lines[n].rstrip()
        s = raw.strip()
        m = re.match(r'^(```|~~~)', s)
        if fence:
            if m and m.group(1) == fence:
                fence = None
            continue
        if m:
            flush()
            fence = m.group(1)
            continue
        if not s:
            flush()
            continue
        if s.startswith('#'):
            flush()
            out.append(('heading', _inline(s.lstrip('#')), n + 1, ''))
            continue
        if s.startswith('|'):
            flush()
            if not re.match(r'^\|[\s:|-]+\|?$', s):
                for c in s.strip('|').split('|'):
                    c = _inline(c)
                    if c:
                        out.append(('cell', c, n + 1, ''))
            continue
        if re.match(r'^(-{3,}|\*{3,}|_{3,})$', s):
            flush()
            continue
        if _LIST.match(raw):
            flush()
            kind, cur, line0 = 'bullet', [_LIST.sub('', raw)], n + 1
            continue
        if s.startswith('>'):
            if kind != 'quote':
                flush()
                kind, line0 = 'quote', n + 1
            cur.append(re.sub(r'^>\s?', '', s))
            continue
        if kind is None:
            kind, line0 = 'para', n + 1
        cur.append(s)
    flush()
    return out


def blocks_of(text, fmt):
    return html_blocks(text) if fmt == 'html' else md_blocks(text)


# ---------- sentences ----------

ABBR = ['e.g.', 'i.e.', 'est.', 'vs.', 'etc.', 'approx.', 'Fig.', 'fig.', 'No.', 'no.', 'cf.', 'Dr.', 'Mr.',
        'Ms.', 'Mrs.', 'St.', 'incl.', 'Ref.', 'ref.', 'Sec.', 'sec.', 'Eq.', 'eq.', 'al.', 'U.S.', 'a.m.', 'p.m.',
        'min.', 'max.', 'avg.', 'resp.']
_DOT = '․'
# a full stop, then a capital letter, a digit, a quote or a code span
_SPLIT = re.compile(r'(?<=[.!?])["\')\]”’]*\s+(?=["\'`(\[“‘]*[A-Z0-9`])')
# a full stop after a whole word, then a lower-case start (a code name such as "ctest" or "t_amx_numerics")
_SPLIT_LC = re.compile(r'(?<=[A-Za-z0-9)\]/%]{3}\.)\s+(?=[a-z_])')


def sentences(text):
    t = text
    for a in ABBR:
        t = re.sub(r'(?<![A-Za-z])' + re.escape(a), a.replace('.', _DOT), t)   # "est." but not "test."
    t = re.sub(r'(\d)\.(?=\d)', r'\1' + _DOT, t)                               # decimals
    t = re.sub(r'\b([A-Za-z])\.(?=\s+[a-z])', r'\1' + _DOT, t)                 # single letter
    parts = []
    for p in _SPLIT.split(t):
        parts.extend(_SPLIT_LC.split(p))
    return [p.replace(_DOT, '.').strip() for p in parts if p.strip()]


_WORD = re.compile(r'[A-Za-z0-9]')


def nwords(s):
    return sum(1 for w in s.split() if _WORD.search(w))


SUB_STRICT = re.compile(r"\b(because|since|although|though|unless|whereas|while|when|whenever|if|until|"
                        r"so that|which|whose|where)\b", re.I)
JOIN = re.compile(r",\s+(and|or|but|so)\b", re.I)


def features(s):
    par = re.findall(r'\([^)]*\)', s)
    return dict(words=nwords(s), semicolon=';' in s, colon=bool(re.search(r':\s', s)), paren=len(par),
                paren_words=sum(nwords(x) for x in par), paren_max=max([nwords(x) for x in par] or [0]),
                sub=len(SUB_STRICT.findall(s)), join=len(JOIN.findall(s)), commas=s.count(','))


def analyse(text, fmt):
    res = []
    for kind, t, line, label in blocks_of(text, fmt):
        # a bold label that opens a block is counted in the words, not as a sentence
        res.append(dict(kind=kind, text=(label + ' ' + t).strip(), line=line, words=nwords(t) + nwords(label),
                        label=label, sents=[dict(text=s, **features(s)) for s in sentences(t)]))
    return res


def pct(n, d):
    return 100.0 * n / d if d else 0.0


def quantile(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else 0


def stats(blocks):
    """Size distribution of the prose (paragraphs and bullets)."""
    paras = [b for b in blocks if b['kind'] == 'para']
    buls = [b for b in blocks if b['kind'] == 'bullet']
    w = [s['words'] for b in paras + buls for s in b['sents'] if s['words']]
    n = len(w)
    ps, bs = [len(b['sents']) for b in paras], [len(b['sents']) for b in buls]
    pw, bw = sum(b['words'] for b in paras), sum(b['words'] for b in buls)
    return dict(words=sum(w), sentences=n, mean=sum(w) / n if n else 0, median=quantile(w, .5), p90=quantile(w, .9),
                max=max(w) if w else 0, over20=pct(sum(x > 20 for x in w), n), over25=pct(sum(x > 25 for x in w), n),
                over30=pct(sum(x > 30 for x in w), n), n_over20=sum(x > 20 for x in w),
                paras=len(paras), para_over3=pct(sum(x > 3 for x in ps), len(ps)),
                para_ge3=pct(sum(x >= 3 for x in ps), len(ps)), n_para_over3=sum(x > 3 for x in ps),
                bullets=len(buls), bullet_over3=pct(sum(x > 3 for x in bs), len(bs)),
                bullet_ge3=pct(sum(x >= 3 for x in bs), len(bs)), n_bullet_over3=sum(x > 3 for x in bs),
                bullet_word_share=pct(bw, pw + bw))


def violations(blocks, max_words=25, max_sentences=3, max_paren=8, soft_words=20):
    out = []
    for b in blocks:
        if b['kind'] not in ('para', 'bullet'):
            continue
        head = ' '.join(b['text'].split()[:8])
        if len(b['sents']) > max_sentences:
            what = 'paragraph' if b['kind'] == 'para' else 'bullet'
            out.append((b['line'], f"{what} of {len(b['sents'])} sentences (limit {max_sentences}): \"{head} ...\""))
        for s in b['sents']:
            sh = ' '.join(s['text'].split()[:8])
            if s['words'] > max_words:
                out.append((b['line'], f"sentence of {s['words']} words (limit {max_words}): \"{sh} ...\""))
            elif s['words'] > soft_words and (s['join'] or s['commas'] >= 3 or s['colon']):
                why = 'a join' if s['join'] else ('a list' if s['commas'] >= 3 else 'a colon')
                out.append((b['line'], f"sentence of {s['words']} words with {why} "
                                       f"(limit {soft_words} for such sentences): \"{sh} ...\""))
            if s['paren_max'] > max_paren:
                out.append((b['line'], f"parenthesis of {s['paren_max']} words (limit {max_paren}): \"{sh} ...\""))
            if s['semicolon']:
                out.append((b['line'], f"semicolon: \"{sh} ...\""))
    return out


def main(argv):
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 2
    path = argv[1]

    def opt(name, default):
        return int(argv[argv.index(name) + 1]) if name in argv else default

    fmt = 'html' if path.lower().endswith(('.html', '.htm')) else 'md'
    blocks = analyse(open(path, errors='replace').read(), fmt)
    if '--stats' in argv:
        s = stats(blocks)
        print(f"{path}: {s['sentences']} sentences, mean {s['mean']:.1f} words, longest {s['max']} words, "
              f"{s['over20']:.1f}% over 20 words, {s['over25']:.1f}% over 25 words. "
              f"{s['paras']} paragraphs, {s['para_over3']:.1f}% over 3 sentences. "
              f"{s['bullets']} bullets, {s['bullet_over3']:.1f}% over 3 sentences.")
        return 0
    v = violations(blocks, opt('--max-words', 25), opt('--max-sentences', 3), opt('--max-paren', 8),
                   opt('--soft-words', 20))
    for line, msg in v:
        print(f"{path}:{line}: {msg}")
    return 1 if v else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
