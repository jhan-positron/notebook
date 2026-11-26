import sys, zipfile, re, os, posixpath
import xml.etree.ElementTree as ET

NS = {
 'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
 'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
 'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
 'rel':'http://schemas.openxmlformats.org/package/2006/relationships',
}
src, outdir = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(src)
names = set(z.namelist())

def rels_for(part):
    d, b = posixpath.split(part)
    rp = posixpath.join(d, '_rels', b + '.rels')
    out = {}
    if rp in names:
        for r in ET.fromstring(z.read(rp)).findall('rel:Relationship', NS):
            out[r.get('Id')] = (r.get('Type').rsplit('/',1)[-1], r.get('Target'), r.get('TargetMode'))
    return out

def resolve(part, target):
    return posixpath.normpath(posixpath.join(posixpath.dirname(part), target))

# slide order
pres = ET.fromstring(z.read('ppt/presentation.xml'))
prels = rels_for('ppt/presentation.xml')
slides = []
for sid in pres.find('p:sldIdLst', NS):
    rid = sid.get('{%s}id' % NS['r'])
    slides.append(resolve('ppt/presentation.xml', prels[rid][1]))

def shape_text(sp, rels):
    """Return list of paragraph strings for a shape; hyperlinks annotated."""
    paras = []
    for p in sp.iter('{%s}p' % NS['a']):
        buf = ''
        lvl = p.find('a:pPr', NS)
        indent = ''
        if lvl is not None and lvl.get('lvl'):
            indent = '  ' * int(lvl.get('lvl'))
        for node in p:
            tag = node.tag.split('}')[1]
            if tag in ('r', 'fld'):
                t = node.find('a:t', NS)
                txt = t.text if t is not None and t.text else ''
                rpr = node.find('a:rPr', NS)
                if rpr is not None:
                    hl = rpr.find('a:hlinkClick', NS)
                    if hl is not None:
                        rid = hl.get('{%s}id' % NS['r'])
                        tgt = rels.get(rid, ('', '?', ''))[1]
                        txt = f'{txt} <<link: {tgt}>>'
                buf += txt
            elif tag == 'br':
                buf += '\n' + indent
        if buf.strip():
            paras.append(indent + buf)
    return paras

def dump_slide(part, idx, kind='slide'):
    rels = rels_for(part)
    root = ET.fromstring(z.read(part))
    out = []
    spTree = root.find('.//p:cSld/p:spTree', NS)
    def walk(container):
        for el in container:
            tag = el.tag.split('}')[1]
            if tag == 'sp':
                nv = el.find('p:nvSpPr/p:cNvPr', NS)
                name = nv.get('name') if nv is not None else ''
                ph = el.find('p:nvSpPr/p:nvPr/p:ph', NS)
                phtype = ph.get('type') if ph is not None else ''
                paras = shape_text(el, rels)
                if paras:
                    out.append(f'  [shape: {name}{" ph="+phtype if phtype else ""}]')
                    out.extend('    ' + x for x in paras)
            elif tag == 'graphicFrame':
                nv = el.find('p:nvGraphicFramePr/p:cNvPr', NS)
                name = nv.get('name') if nv is not None else ''
                tbl = el.find('.//a:tbl', NS)
                if tbl is not None:
                    out.append(f'  [table: {name}]')
                    for tr in tbl.findall('a:tr', NS):
                        cells = []
                        for tc in tr.findall('a:tc', NS):
                            cells.append(' / '.join(shape_text(tc, rels)).replace('\n',' '))
                        out.append('    | ' + ' | '.join(cells) + ' |')
                else:
                    gd = el.find('.//a:graphicData', NS)
                    uri = gd.get('uri') if gd is not None else '?'
                    out.append(f'  [graphicFrame: {name} uri={uri}]')
                    # chart?
                    for c in el.iter():
                        rid = c.get('{%s}id' % NS['r'])
                        if rid and rid in rels:
                            out.append(f'    -> {rels[rid][0]}: {rels[rid][1]}')
            elif tag == 'pic':
                nv = el.find('p:nvPicPr/p:cNvPr', NS)
                name = nv.get('name') if nv is not None else ''
                descr = nv.get('descr') if nv is not None else ''
                blip = el.find('.//a:blip', NS)
                rid = blip.get('{%s}embed' % NS['r']) if blip is not None else None
                tgt = rels.get(rid, ('', '?', ''))[1] if rid else '?'
                # size
                ext = el.find('.//a:ext', NS)
                sz = ''
                if ext is not None:
                    sz = f' {int(ext.get("cx"))/914400:.1f}x{int(ext.get("cy"))/914400:.1f} in'
                out.append(f'  [picture: {name} -> {tgt}{sz}]' + (f' alt="{descr}"' if descr else ''))
                mp = resolve(part, tgt)
                if mp in names:
                    fn = f'{kind}{idx:02d}_' + posixpath.basename(mp)
                    with open(os.path.join(outdir, fn), 'wb') as f:
                        f.write(z.read(mp))
                    out.append(f'    saved {fn}')
            elif tag in ('grpSp',):
                nv = el.find('p:nvGrpSpPr/p:cNvPr', NS)
                out.append(f'  [group: {nv.get("name") if nv is not None else ""}]')
                walk(el)
            elif tag == 'cxnSp':
                pass
    walk(spTree)
    # external hyperlinks on the slide
    for rid, (typ, tgt, mode) in rels.items():
        if typ == 'hyperlink':
            out.append(f'  [hyperlink rel {rid}: {tgt}]')
    return out

for i, part in enumerate(slides, 1):
    print(f'=== SLIDE {i} ({part}) ===')
    for line in dump_slide(part, i):
        print(line)
    # notes
    rels = rels_for(part)
    for rid, (typ, tgt, mode) in rels.items():
        if typ == 'notesSlide':
            np_ = resolve(part, tgt)
            lines = dump_slide(np_, i, 'notes')
            txt = [l for l in lines if not l.startswith('  [shape')]
            body = [l.strip() for l in txt if l.strip() and not re.fullmatch(r'\d+', l.strip())]
            if body:
                print('  --- notes ---')
                for l in body:
                    print('    ' + l)
    print()
print('media files in package:')
for n in sorted(names):
    if n.startswith('ppt/media/'):
        print('  ', n, z.getinfo(n).file_size)
