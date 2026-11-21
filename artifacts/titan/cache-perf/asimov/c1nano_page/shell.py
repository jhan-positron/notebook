"""The page shell: one Page object (called S by the section modules).

It owns the CSS, the numbering (sections, figures, tables), the reference
registry, the "Words used here" registry, the small text blocks, and
render(), which assembles the page and runs a lint over the visible text.

Page order: title, Short version, Contents, the sections, "Words used here"
(second to last), References (last).

Light theme only.  No external resources.  Usage: API.md in this folder.
(A copy of cme_page/shell.py with another lint word list, S.figref, S.tabref
and the lenient mode for partial builds.)
"""
import html
import re
import sys
from html.parser import HTMLParser

try:
    from . import viz as _viz
    _VIZ_CSS = _viz.CSS
except Exception:        # shell.py can be used alone
    _VIZ_CSS = ''

CSS = """
:root{--ink:#1c2024;--ink2:#4a5058;--muted:#6b7280;--rule:#d9dde2;--soft:#f5f6f8;--link:#1f5fae}
*{box-sizing:border-box}
html{background:#fff}
body{margin:0 auto;padding:28px 24px 64px;max-width:1088px;background:#fff;color:var(--ink);
 font:15px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
h1{font-size:28px;line-height:1.2;margin:0 0 4px}
.sub{color:var(--muted);margin:0 0 20px}
h2{font-size:21px;line-height:1.25;margin:44px 0 10px;padding-top:14px;border-top:1px solid var(--rule)}
h3{font-size:16.5px;margin:28px 0 8px}
p{margin:8px 0}
a{color:var(--link);text-decoration:none}
a:hover{text-decoration:underline}
a.ref{font-size:.82em;color:var(--muted);white-space:nowrap}
code{font:0.88em ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--soft);
 padding:1px 4px;border-radius:3px;overflow-wrap:anywhere}
pre{font:13px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;background:var(--soft);
 padding:10px 12px;border-radius:6px;overflow-x:auto}
ul,ol{margin:6px 0;padding-left:22px}
li{margin:3px 0}
li>ul{margin:2px 0}
.short{background:var(--soft);border:1px solid var(--rule);border-radius:8px;padding:14px 18px;margin:16px 0 20px}
.short h2{border:0;margin:0 0 6px;padding:0;font-size:17px}
nav.toc{margin:18px 0 8px;font-size:14px}
nav.toc .t{font-weight:600;margin-bottom:4px}
nav.toc ol{list-style:none;padding-left:0;margin:0;columns:2;column-gap:32px}
nav.toc ol ol{columns:1;padding-left:18px;font-size:13px;color:var(--muted)}
nav.toc li{break-inside:avoid;margin:2px 0}
nav.toc ol ol a{color:var(--ink2)}
figure{margin:18px 0 20px;break-inside:avoid;page-break-inside:avoid}
figcaption{font-size:14px;margin:0 0 8px;color:var(--ink)}
figcaption b,.tcap b{font-weight:650}
.takeaway{font-size:14px;margin:8px 0 0;padding-left:10px;border-left:3px solid var(--ink2);color:var(--ink)}
.tablewrap{margin:14px 0 18px;overflow-x:auto}
.tcap{font-size:14px;margin:0 0 6px}
table{border-collapse:collapse;font-size:13px;line-height:1.35;font-variant-numeric:tabular-nums}
th{font-weight:600;text-align:left;vertical-align:bottom;padding:4px 10px 5px 0;border-bottom:1px solid var(--ink2)}
td{padding:3px 10px 3px 0;vertical-align:top;border-bottom:1px solid #eceef1}
th.r,td.r{text-align:right;padding-left:10px;white-space:nowrap}
th.c,td.c{text-align:center}
tr{break-inside:avoid;page-break-inside:avoid}
tr.hl td{background:#fff6d6}
tr.grp td{font-weight:600;padding-top:9px;border-bottom:1px solid var(--rule)}
.tnote{font-size:12.5px;color:var(--muted);margin:5px 0 0}
.fnote{margin-top:8px}
.block{border:1px solid var(--rule);border-left-width:4px;border-radius:6px;padding:9px 14px;margin:14px 0;
 break-inside:avoid;page-break-inside:avoid}
.block .lab{font-weight:650;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:var(--ink2);margin-bottom:2px}
.block p{margin:4px 0}
.hyp{border-left-color:#8a6fd1;background:#faf8ff}
.insuf{border-left-color:#9aa1ab;background:var(--soft)}
.callout{border-left-color:var(--ink2);background:#fff}
.takeaways{border-left-color:var(--ink);background:var(--soft)}
.block .test{color:var(--ink2)}
.cols{display:flex;gap:24px;flex-wrap:wrap;align-items:flex-start}
.cols>*{flex:1 1 300px;min-width:0}
dl.words{margin:8px 0;display:grid;grid-template-columns:minmax(120px,220px) 1fr;gap:4px 18px;font-size:14px}
dl.words dt{font-weight:600}
dl.words dd{margin:0}
ol.refs{font-size:13.5px;padding-left:0;list-style:none}
ol.refs li{margin:5px 0;padding-left:66px;text-indent:-66px;overflow-wrap:anywhere}
ol.refs .n{display:inline-block;width:66px;text-indent:0;color:var(--muted);white-space:nowrap}
#tip{position:fixed;display:none;z-index:9;pointer-events:none;background:#fff;color:var(--ink);
 border:1px solid #c3c8cf;border-radius:6px;box-shadow:0 3px 12px rgba(0,0,0,.14);padding:6px 9px;
 font-size:12.5px;line-height:1.4;max-width:340px}
#tip div:first-child{font-weight:650}
#tip div+div{color:var(--ink2)}
@media print{
 body{padding:0;max-width:none;font-size:11pt}
 #tip{display:none!important}
 h2,h3,figcaption,.tcap{break-after:avoid;page-break-after:avoid}
 nav.toc ol{columns:1}
 a{color:inherit}
 .tablewrap{overflow:visible}
}
"""

TOOLTIP_JS = """
(function(){
 var t=document.getElementById('tip');
 function hide(){t.style.display='none';}
 document.addEventListener('mousemove',function(e){
  var el=e.target&&e.target.closest?e.target.closest('[data-tip]'):null;
  if(!el){hide();return;}
  var s=el.getAttribute('data-tip');
  if(t.getAttribute('data-s')!==s){
   t.setAttribute('data-s',s);
   while(t.firstChild)t.removeChild(t.firstChild);
   s.split('\\n').forEach(function(l){var d=document.createElement('div');d.textContent=l;t.appendChild(d);});
  }
  t.style.display='block';
  var r=t.getBoundingClientRect(),x=e.clientX+14,y=e.clientY+16;
  if(x+r.width>window.innerWidth-8)x=e.clientX-r.width-14;
  if(y+r.height>window.innerHeight-8)y=e.clientY-r.height-12;
  t.style.left=Math.max(4,x)+'px';t.style.top=Math.max(4,y)+'px';
 });
 document.addEventListener('mouseleave',hide);
 window.addEventListener('scroll',hide,true);
})();
"""

# ------------------------------------------------------------------ lint

# Raise: words the page owner forbids (SPEC hard rules 2 and 6, critic sheet section 9).
# The boot names "boot B", "boot C", "boot D", "boot E", "boot F1" and "boot R3" are allowed.
FORBIDDEN = [
    ('hop', re.compile(r'\bhop(s|ped|ping)?\b', re.I)),
    ('chase', re.compile(r'\bchas(e|es|ed|ing)\b', re.I)),
    ('register control', re.compile(r'\bregister control\b', re.I)),
    ('run N (a boot is named "boot F1", "boot E", ...)',
     re.compile(r'\brun [1-9]\b(?![,.]?\d)(?! (?:pass|passes|rep|reps|core|cores|thread|threads|time|times|'
                r'command|commands|walk|walks|reader|readers|writer|writers|to \d)\b)', re.I)),
    ('round three / round four', re.compile(r'\bround (three|four|3|4)\b', re.I)),
    ('boot A', re.compile(r'\b[Bb]oot A\b')),
    ('sparse', re.compile(r'\bsparse\b', re.I)),
    ('dense', re.compile(r'\bdense\b', re.I)),
    ('asm form', re.compile(r'\basm form\b', re.I)),
    ('previously', re.compile(r'\bpreviously\b', re.I)),
    ('no longer', re.compile(r'\bno longer\b', re.I)),
    ('L3 off (write "the L3 holds no data")', re.compile(r'\bL3 (?:is |was |are |were )?off\b', re.I)),
    ('baseline (write "background control" or "L1 row")', re.compile(r'\bbaselines?\b', re.I)),
    ('dual 128-bit', re.compile(r'\bdual 128[- ]bit\b', re.I)),
    ('validated (write "exploratory" or "checked in two states")', re.compile(r'\bvalidated\b', re.I)),
    ('codex', re.compile(r'\bcodex\b', re.I)),
]
# Warn only: words that are wrong in some uses and right in others.
SUSPECT = [
    ('fresh (not allowed as a noun label)', re.compile(r'\bfresh\b', re.I)),
    ('flushed (not allowed as a noun label)', re.compile(r'\bthe flushed\b|\bflushed (rows?|chains?|kinds?)\b', re.I)),
    ('history word', re.compile(r'\b(earlier|now|changed|settled|was thought|new in|turned out|used to|was fixed|'
                                r'old firmware)\b', re.I)),
    ('2 MiB pages (never for the OCM mapping: "64 KiB translations")', re.compile(r'\b2 MiB pages?\b', re.I)),
    ('lines in flight (needs "est.")', re.compile(r'\blines in flight\b(?! est\.)', re.I)),
    ('takes N cycles (a bandwidth row is "effective cycles per 64 bytes transferred")',
     re.compile(r'\btakes? \d[\d.,]* cycles?\b', re.I)),
    ('served by the L3 (not for the one-line-per-page rows)', re.compile(r'\bserved by the L3\b', re.I)),
    ('DRAM latency (write "DRAM model")', re.compile(r'\bDRAM latency\b', re.I)),
    ('SLC size without "est."', re.compile(r'\b3\.75 MiB\b(?! est\.)', re.I)),
]


class LintError(ValueError):
    """render() found a defect that must be fixed before the page is written."""


class _Vis(HTMLParser):
    """Collects the visible text of a page in three sets:
    words: all visible text outside code and pre (the word lint reads it),
    prose: the same without table cells and SVG (the semicolon lint reads it),
    full:  all visible text, code included (the [RefN] lint reads it)."""
    VOID = {'meta', 'br', 'hr', 'img', 'input', 'link', 'col', 'wbr'}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.stack, self.words, self.prose, self.full = [], [], [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag in self.stack:
            while self.stack and self.stack.pop() != tag:
                pass

    def handle_data(self, data):
        st = set(self.stack)
        if st & {'script', 'style', 'title'}:
            return
        self.full.append(data)
        if st & {'code', 'pre'}:
            self.words.append(' ')
            self.prose.append(' ')
            return
        self.words.append(data)
        self.prose.append(data if not (st & {'td', 'th', 'svg'}) else ' ')


def _ctx(text, m, n=36):
    a, b = max(0, m.start() - n), min(len(text), m.end() + n)
    return '...' + text[a:b].strip() + '...'


def lint(page_html, n_refs=None):
    """Returns (errors, warnings), two lists of text.  render() raises on errors."""
    errors, warnings = [], []
    v = _Vis()
    v.feed(page_html)
    words = re.sub(r'\s+', ' ', ''.join(v.words))
    prose = re.sub(r'\s+', ' ', ''.join(v.prose))
    full = re.sub(r'\s+', ' ', ''.join(v.full))
    for name, rx in FORBIDDEN:
        for m in rx.finditer(words):
            errors.append('forbidden word "%s": %s' % (name, _ctx(words, m)))
    for name, rx in SUSPECT:
        for m in rx.finditer(words):
            warnings.append('check the word %s: %s' % (name, _ctx(words, m)))
    for m in re.finditer(r'<svg\b.*?</svg>', page_html, re.S):
        bad = re.search(r'[^\x00-\x7f]', m.group(0))
        if bad:
            s = m.group(0)
            errors.append('non-ASCII character %r inside <svg>: ...%s...' % (
                bad.group(0), s[max(0, bad.start() - 30):bad.end() + 30]))
    if n_refs is not None:
        for m in re.finditer(r'\[Ref(\d+)\]', full):
            if not 1 <= int(m.group(1)) <= n_refs:
                errors.append('[Ref%s] has no entry in the References: %s' % (m.group(1), _ctx(full, m)))
        for m in re.finditer(r'\[Ref(?!\d+\])[^\]]{0,20}\]?', full):
            errors.append('malformed reference mark: %s' % _ctx(full, m))
    ids = set(re.findall(r'\bid="([^"]+)"', page_html))
    for m in re.finditer(r'href="#([^"]*)"', page_html):
        if m.group(1) not in ids:
            errors.append('link to #%s, which is no id on the page' % m.group(1))
    seen = set()
    for i in re.findall(r'\bid="([^"]+)"', page_html):
        if i in seen:
            errors.append('id %r is used twice' % i)
        seen.add(i)
    for m in re.finditer(r';', prose):
        warnings.append('semicolon in prose: %s' % _ctx(prose, m))
    return errors, warnings


# ------------------------------------------------------------------ page

_NUMERIC = re.compile(
    r'^(?:[+\-]?\d[\d,]*(?:\.\d+)?(?:\s*(?:to|-)\s*[+\-]?\d[\d,]*(?:\.\d+)?)?'
    r'(?:\s*[A-Za-z%/]{1,6}(?:/[A-Za-z]+)?)?(?:\s+est\.)?|-|n/a|)$')


def _plain(cell):
    return html.unescape(re.sub(r'<[^>]+>', '', str(cell))).strip()


def esc(s):
    """Escape a plain text for use in HTML."""
    return html.escape(str(s), quote=False)


_REF_RUN = re.compile(r'(?:<a class="ref" href="#ref-\d+">\[Ref\d+\]</a>[ \n]*){2,}')
_REF_ONE = re.compile(r'<a class="ref" href="#ref-(\d+)">\[Ref\d+\]</a>')


def _dedupe_refs(html_):
    """In a run of [RefN] links, keep each N once and put the run in rising order.  Several
    section keys can name one file, so a caption that cites them in a row would print one link twice."""
    def fix(m):
        seen, out = set(), []
        for r in _REF_ONE.finditer(m.group(0)):
            if r.group(1) not in seen:
                seen.add(r.group(1))
                out.append((int(r.group(1)), r.group(0)))
        tail = m.group(0)[len(m.group(0).rstrip(' \n')):]
        return ' '.join(t for _, t in sorted(out)) + tail
    return _REF_RUN.sub(fix, html_)


def _renumber_refs(html_, new):
    """Rewrites every [RefN] link with the number new[N]."""
    return _REF_ONE.sub(lambda m: '<a class="ref" href="#ref-%d">[Ref%d]</a>' % (
        new[int(m.group(1))], new[int(m.group(1))]), html_)


class Page:
    """The page object.  The section modules receive it as S."""

    def __init__(self, title, subtitle=''):
        self.title = title
        self.subtitle = subtitle
        self.n_fig = 0
        self.n_table = 0
        self._refs = {}        # key -> [number, text]
        self._ref_order = []
        self._terms = {}       # lower-case name -> (name, definition)
        self._ids = set()
        self.warnings = []
        # Set by refs.install(): section key -> canonical keys, and canonical key -> entry text.
        self.ref_resolve = None
        self.ref_text = None
        self.ref_final = None      # canonical key, entry text -> entry text with the cited lines
        self.unmapped_refs = []
        # Set by words.install(): lower-case name -> (name, definition), and section name -> glossary names.
        self.words = None
        self.word_alias = {}
        self.unmapped_terms = []
        # True in a partial build (gen_c1nano_perf.py --only): a cross-reference to a heading, figure
        # or table that is not on the page is written as plain text and does not raise.
        self.lenient = False
        self.unresolved = []

    # ---- headings (numbers are filled in by render) ----
    def _id(self, id_):
        if id_ in self._ids:
            raise ValueError('duplicate id %r' % id_)
        self._ids.add(id_)
        return id_

    def h2(self, id_, title):
        """Section heading.  render() numbers it (2, 3, ...)."""
        return '<h2 id="%s"><!--hnum-->%s</h2>\n' % (self._id(id_), title)

    def h3(self, id_, title):
        """Subsection heading.  render() numbers it (2.1, 2.2, ...)."""
        return '<h3 id="%s"><!--hnum-->%s</h3>\n' % (self._id(id_), title)

    # ---- text blocks ----
    def p(self, text):
        return '<p>%s</p>\n' % text

    def bullets(self, items, ordered=False):
        """items: text, or (text, [sub items]), or a list right after a text (its sub items)."""
        tag = 'ol' if ordered else 'ul'
        out, i = ['<%s>' % tag], 0
        items = list(items)
        while i < len(items):
            it = items[i]
            sub = None
            if isinstance(it, tuple):
                it, sub = it[0], it[1]
            elif i + 1 < len(items) and isinstance(items[i + 1], list):
                sub = items[i + 1]
                i += 1
            if isinstance(it, list):
                raise ValueError('bullets: a nested list must follow a text item')
            out.append('<li>%s%s</li>' % (it, self.bullets(sub) if sub else ''))
            i += 1
        out.append('</%s>\n' % tag)
        return ''.join(out)

    def hyp(self, text, test):
        """A cause that no counter proves, with the measurement that would settle it."""
        if not test:
            raise ValueError('hyp: a hypothesis needs the measurement that would confirm or reject it')
        return ('<div class="block hyp"><div class="lab">Hypothesis</div><p>%s</p>'
                '<p class="test"><b>Measurement that would confirm or reject it:</b> %s</p></div>\n' % (text, test))

    def insufficient(self, text):
        """Something unknown: the text names what would resolve it."""
        return '<div class="block insuf"><div class="lab">Insufficient data</div><p>%s</p></div>\n' % text

    def callout(self, text, title='Note'):
        return '<div class="block callout"><div class="lab">%s</div>%s</div>\n' % (
            title, text if text.lstrip().startswith('<') else '<p>%s</p>' % text)

    def takeaways(self, items, title='Key points'):
        """The list at the top of a section."""
        return '<div class="block takeaways"><div class="lab">%s</div>%s</div>\n' % (title, self.bullets(items))

    def cols(self, *parts):
        """Parts side by side (they wrap under each other on a narrow page)."""
        return '<div class="cols">%s</div>\n' % ''.join('<div>%s</div>' % p for p in parts)

    # ---- figures and tables ----
    def next_fig(self):
        """The number the next fig() call will get (for 'Figure N shows ...')."""
        return self.n_fig + 1

    def next_table(self):
        return self.n_table + 1

    def fig(self, svg, caption, takeaway=None, id_=None, note=None):
        """Figure: caption above, the SVG, a one-line takeaway below, then an optional small
        note (sources, files, simplifications) in the style of a table note.
        id_: the fixed id of IDS.md ('fig-L1'), so that S.figref can name the figure."""
        self.n_fig += 1
        n = self.n_fig
        tk = '<p class="takeaway">%s</p>' % takeaway if takeaway else ''
        nt = '<p class="tnote fnote">%s</p>' % note if note else ''
        return ('<figure id="%s"><figcaption><b>Figure %d.</b> %s</figcaption>%s%s%s</figure>\n' % (
            self._id(id_ or 'fig%d' % n), n, caption, svg, tk, nt))

    def table(self, headers, rows, caption=None, note=None, highlight=None, align=None, id_=None):
        """Table.  Numeric columns are right-aligned (found from the cells, or forced by
        align='lrrc...').  highlight: row indexes, or a function (index, row) -> bool.
        A row given as a plain text is a group heading across all columns."""
        self.n_table += 1
        n = self.n_table
        ncol = len(headers)
        body = [r for r in rows if not isinstance(r, str)]
        for r in body:
            if len(r) != ncol:
                raise ValueError('table %d: a row has %d cells, the header has %d' % (n, len(r), ncol))
        if align is None:
            align = ''
            for c in range(ncol):
                cells = [_plain(r[c]) for r in body]
                numeric = bool(cells) and any(cells) and all(_NUMERIC.match(x) for x in cells)
                # A footprint ("96 KiB") is a row label, not a value: left-aligned in every table.
                if _plain(headers[c]).lower().startswith('footprint'):
                    numeric = False
                align += 'r' if numeric else 'l'
        if len(align) != ncol:
            raise ValueError('table %d: align has %d letters for %d columns' % (n, len(align), ncol))
        cls = [(' class="%s"' % a) if a in 'rc' else '' for a in align]
        out = ['<div class="tablewrap" id="%s" data-n="%d">' % (self._id(id_ or 'table%d' % n), n)]
        if caption:
            out.append('<p class="tcap"><b>Table %d.</b> %s</p>' % (n, caption))
        out.append('<table><thead><tr>%s</tr></thead><tbody>' % ''.join(
            '<th%s>%s</th>' % (cls[i], h) for i, h in enumerate(headers)))
        bi = 0
        for r in rows:
            if isinstance(r, str):
                out.append('<tr class="grp"><td colspan="%d">%s</td></tr>' % (ncol, r))
                continue
            hl = (highlight(bi, r) if callable(highlight) else bi in highlight) if highlight is not None else False
            out.append('<tr%s>%s</tr>' % (' class="hl"' if hl else '', ''.join(
                '<td%s>%s</td>' % (cls[i], '' if c is None else c) for i, c in enumerate(r))))
            bi += 1
        out.append('</tbody></table>')
        if note:
            out.append('<p class="tnote">%s</p>' % note)
        out.append('</div>\n')
        return ''.join(out)

    # ---- cross-references ----
    def xref(self, id_, text=None, cap=False):
        """Link to a section or subsection by its heading id (IDS.md lists them).  render()
        writes the real number: 'section 7' or 'section 7.3' ('Section' with cap=True).  With
        text, the link reads 'section 7 (text)'.  An id with no heading raises at render,
        or is written as plain text when S.lenient is set (a partial build)."""
        return '<a href="#%s"><!--%sref:%s-->%s</a>' % (id_, 'X' if cap else 'x', id_, (' (%s)' % text) if text else '')

    def figref(self, id_, cap=True):
        """Link to a figure by its id.  render() writes the real number: 'Figure 7'
        ('figure 7' with cap=False).  An id that is no figure raises at render."""
        return '<a href="#%s"><!--%sref:%s--></a>' % (id_, 'F' if cap else 'f', id_)

    def tabref(self, id_, cap=True):
        """Link to a table by its id.  render() writes the real number: 'Table 7'."""
        return '<a href="#%s"><!--%sref:%s--></a>' % (id_, 'T' if cap else 't', id_)

    # ---- registries ----
    def ref(self, key, text=None):
        """Returns the link "[RefN]".  N is given at first use.  The same key gives the
        same N.  The text of the entry is given once (the first text wins).

        After refs.install() a section key is mapped to the canonical key or keys of the
        file or document it names, and the canonical entry text is used.  So one file is
        one entry, whichever section cites it.  A key that ends with ":<lines>" adds those
        lines to the entry ("Cited: lines 60 to 62 (text)"): there the text says what the
        lines hold."""
        if self.ref_resolve is not None:
            ckeys = self.ref_resolve(key, text)
            if ckeys is None:
                if key not in self._refs and key not in self.unmapped_refs:
                    self.unmapped_refs.append(key)
                return self._ref1(key, text)
            return ' '.join(self._ref1(k, self.ref_text(k) or text) for k in ckeys)
        return self._ref1(key, text)

    def _ref1(self, key, text):
        if key not in self._refs:
            self._refs[key] = [len(self._ref_order) + 1, None]
            self._ref_order.append(key)
        ent = self._refs[key]
        if text and ent[1] is None:
            ent[1] = text
        return '<a class="ref" href="#ref-%d">[Ref%d]</a>' % (ent[0], ent[0])

    def term(self, name, definition=''):
        """Registers a term for "Words used here" and returns the name.
        After words.install() the definition of the page glossary is used, so every
        section gets the same wording.  Without it the first definition of a name wins."""
        key = name.lower()
        if self.words is not None:
            targets = self.word_alias.get(key, [key])
            for t in targets:
                if t in self.words:
                    self._terms.setdefault(t, self.words[t])
                else:
                    if t not in self.unmapped_terms:
                        self.unmapped_terms.append(t)
                    if definition:
                        self._terms.setdefault(t, (name, definition))
            return name
        if definition:
            self._terms.setdefault(key, (name, definition))
        return name

    # ---- assembly ----
    def render(self, short_version_html, sections, lint_page=True):
        """Returns the whole page.  sections: html strings (each begins with S.h2(...)),
        or (key, title, body_html) tuples.  Raises LintError on a lint error."""
        parts = []
        for s in sections:
            if isinstance(s, (tuple, list)):
                s = self.h2(s[0], s[1]) + s[2]
            parts.append('<section>%s</section>\n' % s)
        missing = [k for k in self._ref_order if not self._refs[k][1]]
        if missing:
            raise LintError('reference key(s) used with no entry text: %s' % ', '.join(missing))
        words = ['<section><h2 id="words"><!--hnum-->Words used here</h2>\n<dl class="words">']
        for _, (name, d) in sorted(self._terms.items(), key=lambda kv: (kv[1][0].lower(), kv[0])):
            words.append('<dt>%s</dt><dd>%s</dd>' % (name, d))
        words.append('</dl></section>\n')
        # References are numbered by first use in reading order: the Short version, then the sections, then the word list.
        # The sections are built before the page is put together, so the numbers given at the
        # S.ref() calls follow the build order.  They are replaced here.
        main = ''.join(parts) + ''.join(words)      # the word list is second to last, before References
        order = []
        for m in _REF_ONE.finditer(short_version_html + main):
            if int(m.group(1)) not in order:
                order.append(int(m.group(1)))
        for k in self._ref_order:                      # an entry that no text cites keeps a place at the end
            if self._refs[k][0] not in order:
                order.append(self._refs[k][0])
        new = {old: i + 1 for i, old in enumerate(order)}
        short_version_html = _dedupe_refs(_renumber_refs(short_version_html, new))
        refs = ['<section><h2 id="references"><!--hnum-->References</h2>\n<ol class="refs">']
        for k in sorted(self._ref_order, key=lambda k: new[self._refs[k][0]]):
            n, text = new[self._refs[k][0]], self._refs[k][1]
            if self.ref_final is not None:
                text = self.ref_final(k, text)
            refs.append('<li id="ref-%d"><span class="n">[Ref%d]</span>%s</li>' % (n, n, text))
        refs.append('</ol></section>\n')
        body = _dedupe_refs(_renumber_refs(main, new)) + ''.join(refs)

        # numbering and table of contents
        toc, state = [], [0, 0]

        def number(m):
            level, id_, title = m.group(1), m.group(2), m.group(3)
            if level == '2':
                state[0] += 1
                state[1] = 0
                num = '%d' % state[0]
                toc.append((num, id_, title, []))
            else:
                state[1] += 1
                num = '%d.%d' % (state[0], state[1])
                toc[-1][3].append((num, id_, title))
            return '<h%s id="%s">%s %s</h%s>' % (level, id_, num, title, level)
        body = re.sub(r'<h([23]) id="([^"]+)"><!--hnum-->(.*?)</h\1>', number, body, flags=re.S)
        nums = {}
        for num, id_, title, subs in toc:
            nums[id_] = num
            for n, i, t in subs:
                nums[i] = n
        fignum = {i: int(n) for i, n in re.findall(
            r'<figure id="([^"]+)"><figcaption><b>Figure (\d+)\.', short_version_html + body)}
        tabnum = {i: int(n) for i, n in re.findall(r'<div class="tablewrap" id="([^"]+)" data-n="(\d+)">', body)}
        bad = []

        def xref(m):
            id_, kind, tail = m.group(1), m.group(2), m.group(4)
            if kind in 'xX':
                found = nums.get(id_)
                word = 'Section' if kind == 'X' else 'section'
            elif kind in 'fF':
                found = fignum.get(id_)
                word = 'Figure' if kind == 'F' else 'figure'
            else:
                found = tabnum.get(id_)
                word = 'Table' if kind == 'T' else 'table'
            if found is not None:
                return '<a href="#%s">%s %s%s</a>' % (id_, word, found, tail)
            if self.lenient:           # partial build: plain text, no link
                if id_ not in self.unresolved:
                    self.unresolved.append(id_)
                return '%s "%s"%s' % (word, id_, tail)
            bad.append(id_)
            return ''
        rx = re.compile(r'<a href="#([^"]+)"><!--([xXfFtT])ref:([^>]+?)-->(.*?)</a>', re.S)
        body = rx.sub(xref, body)
        short_version_html = rx.sub(xref, short_version_html)
        if bad:
            raise LintError('cross-reference to an id that is no heading, figure or table: %s' % ', '.join(sorted(set(bad))))
        nav = ['<nav class="toc"><div class="t">Contents</div><ol>']
        for num, id_, title, subs in toc:
            sub = ''
            if subs:
                sub = '<ol>%s</ol>' % ''.join(
                    '<li><a href="#%s">%s %s</a></li>' % (i, n, re.sub(r'<[^>]+>', '', t)) for n, i, t in subs)
            nav.append('<li><a href="#%s">%s %s</a>%s</li>' % (id_, num, re.sub(r'<[^>]+>', '', title), sub))
        nav.append('</ol></nav>\n')

        page = ''.join([
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n<title>%s</title>\n<meta charset="utf-8">\n' % esc(self.title),
            '<meta name="viewport" content="width=device-width, initial-scale=1">\n',
            '<meta name="color-scheme" content="light">\n',
            '<style>%s%s</style>\n</head>\n<body>\n' % (CSS, _VIZ_CSS),
            '<h1>%s</h1>\n' % esc(self.title),
            ('<p class="sub">%s</p>\n' % self.subtitle) if self.subtitle else '',
            '<div class="short"><h2>Short version</h2>%s</div>\n' % short_version_html,
            ''.join(nav), body,
            '<div id="tip" role="tooltip"></div>\n<script>%s</script>\n</body>\n</html>\n' % TOOLTIP_JS,
        ])
        if lint_page:
            errors, warnings = lint(page, len(self._ref_order))
            self.warnings = warnings
            for w in warnings:
                sys.stderr.write('lint warning: %s\n' % w)
            if errors:
                raise LintError('%d lint error(s):\n  %s' % (len(errors), '\n  '.join(errors)))
        return page
