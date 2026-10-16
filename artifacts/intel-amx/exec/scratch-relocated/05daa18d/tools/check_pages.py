#!/usr/bin/env python3
"""Structural checks of the built walk-through pages: figures match the spec, diagram blocks are verbatim copies,
anchors and cross-page links resolve, tags balance, spec invariants hold."""
import re, pathlib, json, sys
S = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path('/home/jhan/workspace/intel-AMX/PR3879/new-PRs/merge-4737-2-4424')
OUT = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else S / 'out'
src_ids = {k: set(re.findall(r'id="([^"]+)"', (SRC / f'diagramming-code-changes-{k}.hpp.html').read_text())) for k in ['kv_cache', 'k_vnni', 'model']}
blocks = {p.stem: p.read_text() for p in (S / 'blocks').glob('*-b*.html')}
TAGS = ['figure', 'details', 'section', 'div', 'ul', 'ol', 'table', 'p', 'li', 'svg', 'span', 'a', 'dl', 'h3', 'h2', 'h5', 'nav', 'main', 'code', 'tr', 'td', 'th', 'summary', 'figcaption', 'b', 'dt', 'dd']
ok = True
for p in sorted(OUT.glob('diagrams-PR*.html')):
    h = p.read_text()
    spec = json.load(open(S / 'spec' / (p.stem.replace('diagrams-PR', 'pr').lower() + '.json')))
    roles = [d['role'] for d in spec['diagrams']]
    order_ok = roles == sorted(roles, key=lambda r: ['core', 'context', 'not involved'].index(r))
    shown = [d['id'] for d in spec['diagrams'] if d['role'] != 'not involved']
    figs = re.findall(r'<figure><svg id="([^"]+)"', h)
    ids = set(re.findall(r'id="([^"]+)"', h))
    bad_anchor = [a for a in re.findall(r'href="#([^"]+)"', h) if a not in ids]
    bad_x = [(k, a) for k, a in re.findall(r'href="\.\./merge-4737-2-4424/diagramming-code-changes-(\w+)\.hpp\.html(?:#([^"]+))?"', h) if a and a not in src_ids[k]]
    sib = [x for x in re.findall(r'href="(diagrams-PR\d-\d+\.html)"', h) if not (OUT / x).exists()]
    verbatim = all(blocks[d] in h for d in shown)
    bal = [(tag, o, c) for tag in TAGS for o, c in [(len(re.findall(r'<' + tag + r'\b[^>]*(?<!/)>', h)), h.count('</' + tag + '>'))] if o != c]
    txt = re.sub(r'<[^>]+>', ' ', re.sub(r'<figure>.*?</figure>', '', h, flags=re.S))
    cids = {c['id'] for c in spec['change_sections']}; dids = {d['id'] for d in spec['diagrams']}
    sv = len(spec['short_version'])
    good = figs == shown and verbatim and not bad_anchor and not bad_x and not sib and not bal and order_ok and 2 <= sv <= 3 and len(dids) == 16 and len(cids) == 29
    ok &= good
    print(f"{p.name}: {p.stat().st_size/1e3:.0f} KB | figures {len(figs)} of {len(shown)} shown, order match={figs==shown}, verbatim={verbatim} | bad anchors {len(bad_anchor)} | bad cross-links {len(bad_x)} | missing siblings {sib} | tags {bal or 'balanced'} | roles ordered {order_ok} | ids 16/29 {len(dids)==16 and len(cids)==29} | short version {sv} sentences | words {len(spec['words'])} | new prose {len(txt.split())} words | {'OK' if good else 'PROBLEM'}")
print('ALL OK' if ok else 'PROBLEMS')
sys.exit(0 if ok else 1)
