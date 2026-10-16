#!/usr/bin/env python3
"""Build one walk-through page per split PR of tron PR 4424.

Usage: build_pr_page.py SPEC.json OUT.html

The page copies the base diagrams (h3 + figure, SVG, legend, caption, box list)
verbatim from the three PR 4424 source pages (blocks extracted under BLOCKS/),
and adds the prose of SPEC.json around them.
"""
import html, json, pathlib, re, sys, datetime

S = pathlib.Path(__file__).resolve().parent.parent
BLOCKS = S / 'blocks'
HEAD = (S / 'src' / 'head-kv_cache.html').read_text()
SRC_REL = '../merge-4737-2-4424/diagramming-code-changes-{}.hpp.html'
SRC_TITLE = {'kv_cache': 'h/tron/models/kv_cache.hpp', 'k_vnni': 'h/tron/tensor/k_vnni.hpp', 'model': 'h/tron/models/model.hpp'}
PR4424_HEAD = '9d5c7a389b'
STACK = [
    (1, 4868, 'jhan-vnnik-1-layout', 'Add the VNNI K layout and its readers'),
    (2, 4887, 'jhan-vnnik-2-amx', 'Use VNNI K layout in AMX attention'),
    (3, 4898, 'jhan-vnnik-3-shared-save', 'Save K in 16-token blocks, shared with idle worker threads'),
    (4, 4901, 'jhan-vnnik-4-tail-block', 'Keep short K writes row-major; enable VNNI K in the deb preset'),
]
PAGE_NAME = 'diagrams-PR{}-{}.html'

EXTRA_CSS = """
.stack{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 0;padding:0;list-style:none}
.stack li{border:1px solid var(--line);border-radius:6px;padding:6px 10px;font-size:13px;background:#fff}
.stack li.here{border:2px solid #2a78d6;background:#eef6ff}
table.plain{border-collapse:collapse;font-size:13.5px;margin:8px 0 14px;max-width:100%}
table.plain th,table.plain td{border:1px solid var(--line);padding:5px 8px;vertical-align:top;text-align:left}
table.plain th{background:var(--soft)}
.badge{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:10px;margin-left:8px;vertical-align:middle}
.badge.core{background:#CFE2F3;color:#0b4a73;border:1px solid #0072B2}
.badge.context{background:#F3F5F8;color:#374151;border:1px solid #9ca3af}
.badge.full{background:#BFE8DA;color:#065f46;border:1px solid #009E73}
.badge.partial{background:#FBE9C4;color:#7c4a00;border:1px solid #E69F00}
.badge.none{background:#fff;color:#6b7280;border:1px solid #d6d9de}
.status{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;margin:8px 0 18px}
.status div{border:1px solid var(--line);border-radius:6px;padding:8px 10px;font-size:13.5px;background:#fff}
.status h5{margin:0 0 6px;font-size:13px}
.status ul{margin:0;padding-left:18px}
.status li{margin:2px 0}
.status .in h5{color:#065f46}.status .in{border-color:#009E73;background:#f3fbf8}
.status .was h5{color:#374151}
.status .later h5{color:#7c4a00}.status .later{border-color:#E69F00;background:#fffaf0}
.status .never h5{color:#b91c1c}
.why{background:#eef6ff;border-left:4px solid #2a78d6;padding:8px 12px;max-width:100ch;margin:6px 0 10px}
.diag{margin-top:34px;padding-top:6px;border-top:1px dashed var(--line)}
details.ev{font-size:12.5px;color:var(--muted);margin:-8px 0 16px}
details.ev ul{margin:4px 0;padding-left:18px}
ol.walk li{margin:6px 0 10px}
dl.words dt{font-weight:600;margin-top:8px}
dl.words dd{margin:0 0 0 1.2em}
.src-note{font-size:13px;color:var(--muted)}
"""

def esc(s):
    return html.escape(str(s), quote=False)

DIAG_LINKS = {}  # diagram id -> href, filled by build()
DIAG_RE = re.compile(r'\b(?:(K_VNNI|KV_CACHE|MODEL)-B(\d+A?)|(k_vnni|kv_cache|model)-b(\d+a?))\b')
TOKEN_RE = re.compile(r"""
 (?P<file>(?:[A-Za-z_][\w.-]*/)*[A-Za-z_][\w.-]*\.(?:hpp|cpp|hs|json|yml|md|txt|py|sh):\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)
 |(?P<name>(?<![\w/#.-])[A-Za-z_]\w*(?:::[A-Za-z_~]\w*)+(?:&lt;[^&]*&gt;)?(?:\([^()\n]{0,60}\))?)
 |(?P<under>(?<![\w/#.-])[A-Za-z]\w*_\w*(?:&lt;[^&]*&gt;)?(?:\([^()\n]{0,60}\))?)
""", re.X)

def code_names(s):
    """Escape s; wrap code names (file:line, a::b, names_with_underscores) in <code>; link diagram references."""
    s = esc(s)
    refs = []
    def hold(m):
        if m.group(1):
            did = f'{m.group(1).lower()}-b{m.group(2).lower()}'; label = m.group(0)
        else:
            did = m.group(0); label = f'{m.group(3).upper()}-B{m.group(4).upper()}'
        href = DIAG_LINKS.get(did, f'#{did}')
        refs.append(f'<a href="{href}">{label}</a>')
        return f'\x00{len(refs) - 1}\x00'
    s = DIAG_RE.sub(hold, s)
    s = TOKEN_RE.sub(lambda m: f'<code>{m.group(0)}</code>', s)
    s = re.sub(r'\x00(\d+)\x00', lambda m: refs[int(m.group(1))], s)
    return s

def pr_label(n):
    for o, num, br, t in STACK:
        if num == n:
            return f'PR-{o} #{num}'
    return f'#{n}'

def diagram_block(did):
    p = BLOCKS / f'{did}.html'
    blk = p.read_text()
    src = did.split('-')[0]
    return blk, src

def diagram_title(did):
    blk, _ = diagram_block(did)
    m = re.search(r'<h3[^>]*>(.*?)</h3>', blk)
    return re.sub(r'<[^>]+>', '', m.group(1))

def short_title(did):
    t = html.unescape(diagram_title(did))
    return t.split('. ', 1)[0]  # e.g. KV_CACHE-B1

def build(spec):
    pr = spec['pr']
    o, n = pr['ordinal'], pr['number']
    title = f"PR-{o} #{n}: {pr['title']}"
    date = datetime.date.today().isoformat()
    roles = {d['id']: d for d in spec['diagrams']}
    order = [d['id'] for d in spec['diagrams']]
    shown = [d for d in spec['diagrams'] if d['role'] != 'not involved']
    hidden = [d for d in spec['diagrams'] if d['role'] == 'not involved']
    n_core = sum(1 for d in shown if d['role'] == 'core')
    DIAG_LINKS.clear()
    for d in spec['diagrams']:
        DIAG_LINKS[d['id']] = f'#{d["id"]}' if d['role'] != 'not involved' else f'{SRC_REL.format(d["id"].split("-")[0])}#{d["id"]}'

    parts = []
    parts.append(HEAD.replace('<title>PR 4424 kv_cache.hpp diagrams</title>', f'<title>{esc(title)}</title>')
                     .replace('content="Diagrams of every logical code change PR 4424 makes to kv_cache.hpp"',
                              f'content="The base diagrams of PR 4424 that introduce the data models and algorithms of {esc(title)}"')
                     .replace('</style>', EXTRA_CSS + '</style>'))
    parts.append('<body><main>')
    parts.append(f'<h1>{esc(title)}: the diagrams for the walk-through</h1>')
    parts.append(f'<p class="meta">tron PR <a href="https://github.com/positron-ai/tron/pull/{n}">#{n}</a> · branch <code>{esc(pr["branch"])}</code> on base <code>{esc(pr["base"])}</code> · head <code>{esc(pr["head"])}</code> · {pr["files"]} files, {pr["added"]} lines added, {pr["removed"]} removed (gh pr diff, {date}) · PR-{o} of the four PRs that split PR <a href="https://github.com/positron-ai/tron/pull/4424">#4424</a>.</p>')
    parts.append('<p class="meta">The diagrams on this page are copied unchanged from the three PR 4424 pages '
                 + ', '.join(f'<a href="{SRC_REL.format(k)}">{esc(v)}</a>' for k, v in SRC_TITLE.items())
                 + f'. The line numbers inside a diagram and in its box list cite the PR 4424 head <code>{PR4424_HEAD}</code>. The line numbers in the prose of this page cite the head of this PR, <code>{esc(pr["head"])}</code>.</p>')
    parts.append('<ul class="stack">' + ''.join(
        f'<li class="{"here" if num == n else ""}"><a href="{PAGE_NAME.format(oo, num)}">PR-{oo} #{num}</a>: {esc(t)}</li>' for oo, num, br, t in STACK) + '</ul>')

    # TOC
    toc = ['<nav id="toc"><h2>Table of contents</h2><ol>',
           '<li><a href="#short">Short version</a></li>',
           '<li><a href="#words">Words used here</a></li>',
           '<li><a href="#lands">1. What this PR adds</a></li>',
           '<li><a href="#walk">2. Walk-through order</a></li>',
           f'<li><a href="#diagrams">3. The base diagrams for this PR ({n_core} core, {len(shown) - n_core} context)</a><ol>']
    for d in shown:
        toc.append(f'<li><a href="#{d["id"]}">{esc(short_title(d["id"]))}</a> ({d["role"]})</li>')
    toc.append('</ol></li>')
    toc.append(f'<li><a href="#notinvolved">4. Base diagrams not involved in this PR ({len(hidden)})</a></li>')
    toc.append('<li><a href="#changes">5. Code-change sections of the source pages that land in this PR</a></li>')
    toc.append('<li><a href="#gaps">6. What the diagrams do not show</a></li>')
    toc.append('<li><a href="#method">7. How this page was made</a></li>')
    toc.append('</ol></nav>')
    parts.append('\n'.join(toc))

    # Short version
    parts.append('<section id="short"><h2>Short version</h2><p class="short">' + ' '.join(code_names(s) for s in spec['short_version']) + '</p></section>')

    # Words
    parts.append('<section id="words"><h2>Words used here</h2><dl class="words">' + ''.join(
        f'<dt>{esc(w["term"])}</dt><dd>{code_names(w["definition"])}</dd>' for w in sorted(spec['words'], key=lambda w: w['term'].lower())) + '</dl></section>')

    # 1. What lands
    rows = []
    for w in spec['what_lands']:
        dl = ', '.join(f'<a href="#{d}">{esc(short_title(d))}</a>' if d in roles else esc(d) for d in w['diagrams'])
        rows.append(f'<tr><td><b>{code_names(w["concept"])}</b></td><td>{esc(w["kind"])}</td><td>{code_names(w["where"])}</td><td>{dl}</td><td>{code_names(w["note"])}</td></tr>')
    parts.append('<section id="lands"><h2>1. What this PR adds</h2><p>The data models, algorithms, protocols and policies this PR adds, in the order to present them. The "where" column cites this PR\'s head.</p>'
                 '<table class="plain"><thead><tr><th>Concept</th><th>Kind</th><th>Where (PR head)</th><th>Diagrams</th><th>What it is</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section>')

    # 2. Walkthrough
    items = []
    for i, st in enumerate(spec['walkthrough'], 1):
        d = st['diagram']
        link = f'<a href="#{d}"><b>{esc(short_title(d))}</b></a>: ' if d in roles and d != 'none' else ''
        items.append(f'<li>{link}{code_names(st["say"])}</li>')
    parts.append('<section id="walk"><h2>2. Walk-through order</h2><p>One step per diagram, in the order that introduces a data model before the algorithm that uses it.</p><ol class="walk">' + ''.join(items) + '</ol></section>')

    # 3. Diagrams
    parts.append(f'<section id="diagrams"><h2>3. The base diagrams for this PR</h2><p>Each diagram is copied unchanged from its source page and draws the final state of the whole stack (PR 4424). The four boxes under a diagram say which of its elements this PR adds, which were already there (from <code>main</code> or an earlier PR of the stack), which land in a later PR, and which no PR of the stack adds in the drawn form.</p>')
    for d in shown:
        blk, src = diagram_block(d['id'])
        parts.append(f'<div class="diag"><p class="src-note">Source: <a href="{SRC_REL.format(src)}#{d["id"]}">{esc(SRC_TITLE[src])} page, {esc(short_title(d["id"]))}</a><span class="badge {d["role"]}">{d["role"]}</span></p>')
        parts.append(f'<p class="why">{code_names(d["why"])}</p>')
        parts.append(blk)
        cols = []
        cols.append('<div class="in"><h5>In this PR</h5>' + ('<ul>' + ''.join(f'<li>{code_names(x)}</li>' for x in d['in_this_pr']) + '</ul>' if d['in_this_pr'] else '<p class="meta">nothing</p>') + '</div>')
        cols.append('<div class="was"><h5>Already there</h5>' + ('<ul>' + ''.join(f'<li>{code_names(x["what"])} <span class="meta">(from {esc(x["from"])})</span></li>' for x in d['already_there']) + '</ul>' if d['already_there'] else '<p class="meta">nothing</p>') + '</div>')
        cols.append('<div class="later"><h5>Lands in a later PR</h5>' + ('<ul>' + ''.join(f'<li>{code_names(x["what"])} <span class="meta">({esc(x["lands_in"])})</span></li>' for x in d['not_yet']) + '</ul>' if d['not_yet'] else '<p class="meta">nothing</p>') + '</div>')
        if d.get('never'):
            cols.append('<div class="never"><h5>Not in the stack in this form</h5><ul>' + ''.join(f'<li>{code_names(x)}</li>' for x in d['never']) + '</ul></div>')
        parts.append('<div class="status">' + ''.join(cols) + '</div>')
        if d.get('evidence'):
            parts.append('<details class="ev"><summary>Evidence (' + str(len(d['evidence'])) + ')</summary><ul>' + ''.join(f'<li>{code_names(x)}</li>' for x in d['evidence']) + '</ul></details>')
        parts.append('</div>')
    parts.append('</section>')

    # 4. Not involved
    parts.append('<section id="notinvolved"><h2>4. Base diagrams not involved in this PR</h2><ul>' + ''.join(
        f'<li><a href="{SRC_REL.format(d["id"].split("-")[0])}#{d["id"]}">{esc(diagram_title(d["id"]))}</a>: {code_names(d["why"])}' +
        (' Lands later: ' + '; '.join(f'{code_names(x["what"])} ({esc(x["lands_in"])})' for x in d['not_yet']) + '.' if d.get('not_yet') else '') + '</li>'
        for d in hidden) + '</ul></section>')

    # 5. Change sections
    heads = {}
    for line in (S / 'src' / 'changes.txt').read_text().splitlines():
        m = re.match(r'== (\w+) ([CKM]\d+): (.*)', line)
        if m:
            heads[m.group(2)] = re.sub(r'^[CKM]\d+\. ', '', m.group(3)).replace('top', '').strip()
    rows = []
    for c in sorted(spec['change_sections'], key=lambda c: (c['id'][0], int(c['id'][1:]))):
        h = heads.get(c['id'], '')
        href = f'{SRC_REL.format(c["source"])}#{c["id"].lower()}'
        rows.append(f'<tr><td><a href="{href}">{esc(c["id"])}</a></td><td>{code_names(h)}</td><td><span class="badge {c["status"]}">{esc(c["status"])}</span></td><td>{code_names(c["note"])}</td></tr>')
    parts.append('<section id="changes"><h2>5. Code-change sections of the source pages that land in this PR</h2><p>The source pages show every logical code change of PR 4424 beside its own diagram. This table says which of those sections this PR carries, in full or in part. The links open the side-by-side section on the source page.</p>'
                 '<table class="plain"><thead><tr><th>Section</th><th>Change</th><th>In this PR</th><th>Note</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table></section>')

    # 6. Gaps
    parts.append('<section id="gaps"><h2>6. What the diagrams do not show</h2>' + ('<ul>' + ''.join(f'<li>{code_names(g)}</li>' for g in spec['gaps']) + '</ul>' if spec['gaps'] else '<p>Nothing: every element this PR adds is drawn on a base diagram above.</p>') + '</section>')

    # 7. Method
    parts.append(f'<section id="method"><h2>7. How this page was made</h2><ul>'
                 f'<li>Generated {date} by <code>build_pr_page.py</code> from a spec written and verified by agents: one mapper per PR, three adversarial verifiers per spec (diff grounding, completeness, prose and facts), one reviser per PR, then a render check of the built page.</li>'
                 f'<li>The diagram blocks (heading, figure, SVG, legend, caption, box list) are byte-for-byte copies of the source pages. Their line numbers cite PR 4424 head <code>{PR4424_HEAD}</code>.</li>'
                 f'<li>The classification of each diagram element (in this PR, already there, later PR) was checked against the four PR diffs (gh pr diff of #4868, #4887, #4898, #4901 on {date}) and the files at the PR heads.</li>'
                 '</ul></section>')
    parts.append('</main></body></html>')
    return '\n'.join(parts)

if __name__ == '__main__':
    spec = json.load(open(sys.argv[1]))
    out = pathlib.Path(sys.argv[2])
    out.write_text(build(spec))
    print(out, out.stat().st_size, 'bytes')
