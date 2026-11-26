#!/usr/bin/env python3
"""companion_tool.py - builds the companion file "<source>.md" of a source file.

The companion holds the source text at the left and the explanation at the right.
The source text is copied by this script, never typed by a person or a model.
The explanations come from annotation files (JSON) in the folder ann/ next to this script.

Commands:
  split PATH [TARGET_LINES]   print chunk ranges for a large file (boundaries at blank lines before low-indent lines)
  check-ann FILE.json         check one annotation file: every line of its range is in exactly one segment
  check-overview FILE.json    check one overview file: required fields, function lines name the function
  build KEY                   write <source>.md from manifest.json, ann/KEY.overview.json and ann/KEY.cNN.json
  verify KEY                  read <source>.md back and compare its left column with the source, line by line
  build-all / verify-all      the same for every key of manifest.json

Annotation file ann/KEY.cNN.json:
  {"file": "<absolute path>", "start": 1, "end": 48,
   "segments": [{"start": 1, "end": 8, "text": "explanation", "heading": "optional row title"}, ...]}
Overview file ann/KEY.overview.json:
  {"file": "<absolute path>", "role": "...", "purpose": "...", "main_flow": [{"step": "...", "lines": "40-45"}],
   "words": [{"term": "...", "def": "..."}], "functions": [{"name": "main", "line": 339, "end": 463, "what": "...",
   "calls": ["worker"], "timed_path": true}], "behavior_notes": ["..."], "refs": [{"id": "Ref1", "path": "...", "what": "..."}]}

Text markup allowed in "text": `code`, **bold**, and lines that start with "- " (a bullet list).
Python 3 standard library only.
"""
import hashlib
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.join(HERE, 'ann')
MANIFEST = os.path.join(HERE, 'manifest.json')
MAX_SEG = 80      # a segment with an explanation may not span more lines than this (source code)
MAX_SEG_TEXT = 400  # the same limit for a text or listing file (a run of 256 nop lines is one segment)
WARN_SEG = 40


def die(msg):
    sys.exit('companion_tool.py: ERROR: ' + msg)


def manifest():
    with open(MANIFEST) as f:
        return json.load(f)['files']


def entry(key):
    for e in manifest():
        if e['key'] == key:
            return e
    die('no key %r in manifest.json' % key)


def source_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if b'\r' in raw:
        die('%s holds a carriage return; the tool expects Unix line ends' % path)
    text = raw.decode('utf-8')
    lines = text.split('\n')
    if lines and lines[-1] == '':
        lines.pop()          # the file ends with a line end
    return lines, hashlib.sha256(raw).hexdigest(), len(raw)


# ----------------------------------------------------------------------------- split

def split(path, target):
    lines, _, _ = source_lines(path)
    n = len(lines)
    if n <= target * 1.25:
        return [[1, n]]
    parts = max(2, round(n / target))
    size = n / parts
    cuts = []
    for k in range(1, parts):
        want = int(round(k * size))
        lo, hi = int(want - size * 0.2), int(want + size * 0.2)
        best = None
        for i in range(max(2, lo), min(n, hi) + 1):          # i = first line of the next chunk (1-based)
            cur, prev = lines[i - 1], lines[i - 2]
            if not cur.strip() or prev.strip():
                continue
            indent = len(cur) - len(cur.lstrip(' '))
            score = (indent, abs(i - want))
            if best is None or score < best[0]:
                best = (score, i)
        if best is None:
            die('no blank-line boundary near line %d of %s' % (want, path))
        cuts.append(best[1])
    starts = [1] + cuts
    ends = [c - 1 for c in cuts] + [n]
    return [[a, b] for a, b in zip(starts, ends)]


# ----------------------------------------------------------------------------- checks

def check_ann(path, quiet=False):
    with open(path) as f:
        a = json.load(f)
    for k in ('file', 'start', 'end', 'segments'):
        if k not in a:
            die('%s: missing field %r' % (path, k))
    lines, _, _ = source_lines(a['file'])
    n = len(lines)
    if not (1 <= a['start'] <= a['end'] <= n):
        die('%s: range %s-%s is outside the file (1-%d)' % (path, a['start'], a['end'], n))
    want = a['start']
    warns = []
    if not a['segments']:
        die('%s: no segments' % path)
    for i, s in enumerate(a['segments']):
        for k in ('start', 'end', 'text'):
            if k not in s:
                die('%s: segment %d: missing field %r' % (path, i, k))
        if not isinstance(s['start'], int) or not isinstance(s['end'], int) or not isinstance(s['text'], str):
            die('%s: segment %d: start and end must be integers, text a string' % (path, i))
        if s['start'] != want:
            die('%s: segment %d starts at line %d, expected %d (segments must be in order, with no gap and no overlap)'
                % (path, i, s['start'], want))
        if s['end'] < s['start']:
            die('%s: segment %d: end %d is before start %d' % (path, i, s['end'], s['start']))
        span = s['end'] - s['start'] + 1
        body = lines[s['start'] - 1:s['end']]
        has_code = any(l.strip() for l in body)
        limit = MAX_SEG_TEXT if a.get('kind') == 'text' else MAX_SEG
        if s['text'].strip() and span > limit:
            die('%s: segment %d (lines %d-%d) spans %d lines; the limit is %d. Split it.'
                % (path, i, s['start'], s['end'], span, limit))
        if span > WARN_SEG:
            warns.append('segment lines %d-%d spans %d lines' % (s['start'], s['end'], span))
        if has_code and not s['text'].strip() and span > 6:
            warns.append('segment lines %d-%d has source text but no explanation' % (s['start'], s['end']))
        if 'heading' in s and not isinstance(s['heading'], str):
            die('%s: segment %d: heading must be a string' % (path, i))
        if '\t' in s['text']:
            die('%s: segment %d: the text holds a tab character' % (path, i))
        want = s['end'] + 1
    if want != a['end'] + 1:
        die('%s: the segments end at line %d, the range ends at line %d' % (path, want - 1, a['end']))
    if not quiet:
        print('OK %s: lines %d-%d, %d segments' % (os.path.basename(path), a['start'], a['end'], len(a['segments'])))
        for w in warns:
            print('  warning: ' + w)
    return a


OV_FIELDS = ('file', 'role', 'purpose', 'main_flow', 'words', 'functions')


def check_overview(path, quiet=False):
    with open(path) as f:
        o = json.load(f)
    for k in OV_FIELDS:
        if k not in o:
            die('%s: missing field %r' % (path, k))
    lines, _, _ = source_lines(o['file'])
    n = len(lines)
    if not isinstance(o['purpose'], str) or not o['purpose'].strip():
        die('%s: purpose is empty' % path)
    if len(o['role'].split()) > 14:
        die('%s: role has %d words; the limit is 14' % (path, len(o['role'].split())))
    for i, st in enumerate(o['main_flow']):
        if not isinstance(st, dict) or 'step' not in st:
            die('%s: main_flow[%d] must be an object with "step" (and optional "lines")' % (path, i))
        if st.get('lines'):
            m = re.fullmatch(r'(\d+)(?:-(\d+))?', st['lines'])
            if not m or not (1 <= int(m[1]) <= int(m[2] or m[1]) <= n):
                die('%s: main_flow[%d]: bad line range %r' % (path, i, st['lines']))
    for i, w in enumerate(o['words']):
        if not isinstance(w, dict) or 'term' not in w or 'def' not in w:
            die('%s: words[%d] must be an object with "term" and "def"' % (path, i))
    for i, fn in enumerate(o['functions']):
        for k in ('name', 'line', 'what'):
            if k not in fn:
                die('%s: functions[%d]: missing field %r' % (path, i, k))
        if not (1 <= fn['line'] <= n):
            die('%s: functions[%d] %s: line %d is outside the file' % (path, i, fn['name'], fn['line']))
        base = re.sub(r'\(.*$', '', fn['name']).strip()
        window = '\n'.join(lines[fn['line'] - 1:min(n, fn['line'] + 2)])
        if base and base not in window:
            die('%s: functions[%d]: the name %r is not on lines %d-%d of the source'
                % (path, i, base, fn['line'], min(n, fn['line'] + 2)))
        if 'end' in fn and not (fn['line'] <= fn['end'] <= n):
            die('%s: functions[%d] %s: bad end line %r' % (path, i, fn['name'], fn['end']))
        if len(fn['what'].split()) > 25:
            die('%s: functions[%d] %s: "what" has more than 25 words' % (path, i, fn['name']))
    for i, c in enumerate(o.get('call_sequence', [])):
        if not isinstance(c, dict) or not isinstance(c.get('depth'), int) or 'name' not in c or 'note' not in c:
            die('%s: call_sequence[%d] must be an object with "depth" (integer), "name", "note" (and optional "line")' % (path, i))
        if len(c['note'].split()) > 14:
            die('%s: call_sequence[%d] %s: the note has %d words; the limit is 14' % (path, i, c['name'], len(c['note'].split())))
        if c.get('line') is not None and not (1 <= c['line'] <= n):
            die('%s: call_sequence[%d] %s: line %r is outside the file' % (path, i, c['name'], c['line']))
    for i, r in enumerate(o.get('refs', [])):
        if not isinstance(r, dict) or 'id' not in r or 'what' not in r:
            die('%s: refs[%d] must be an object with "id", "what" (and "path")' % (path, i))
    if not quiet:
        print('OK %s: %d flow steps, %d words, %d functions' % (os.path.basename(path), len(o['main_flow']),
                                                                  len(o['words']), len(o['functions'])))
    return o


# ----------------------------------------------------------------------------- markup

def inline(text):
    """`code` and **bold** to HTML; everything else escaped."""
    out = []
    for i, part in enumerate(re.split(r'`([^`\n]+)`', text)):
        if i % 2:
            out.append('<code>' + html.escape(part, quote=False) + '</code>')
        else:
            p = html.escape(part, quote=False)
            p = re.sub(r'\*\*([^*\n]+)\*\*', r'<b>\1</b>', p)
            out.append(p)
    return ''.join(out)


def cell(text):
    """Explanation text to one HTML line (no line end: a blank line would end the HTML block of the table)."""
    text = text.strip()
    if not text:
        return ''
    out, items, paras = [], [], []

    def flush_items():
        if items:
            out.append('<ul>' + ''.join('<li>%s</li>' % inline(x) for x in items) + '</ul>')
            del items[:]

    def flush_paras():
        if paras:
            out.append('<br>'.join(inline(x) for x in paras))
            del paras[:]

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.startswith('- '):
            flush_paras()
            items.append(line[2:])
        else:
            flush_items()
            paras.append(line)
    flush_items()
    flush_paras()
    return ''.join(out)


LANG_NAME = {'bash': 'Bash script', 'c': 'C source', 'python': 'Python script', 'text': 'text file'}


def build(key):
    e = entry(key)
    path = e['path']
    lines, sha, nbytes = source_lines(path)
    n = len(lines)
    width = len(str(n))
    ov = check_overview(os.path.join(ANN, key + '.overview.json'), quiet=True)
    if os.path.abspath(ov['file']) != os.path.abspath(path):
        die('%s: overview names another file: %s' % (key, ov['file']))
    segs = []
    want = 1
    for ci, (a, b) in enumerate(e['chunks'], 1):
        ann = check_ann(os.path.join(ANN, '%s.c%02d.json' % (key, ci)), quiet=True)
        if os.path.abspath(ann['file']) != os.path.abspath(path):
            die('%s chunk %d: annotation names another file: %s' % (key, ci, ann['file']))
        if [ann['start'], ann['end']] != [a, b]:
            die('%s chunk %d: annotation covers %d-%d, manifest says %d-%d' % (key, ci, ann['start'], ann['end'], a, b))
        if a != want and not e.get('partial'):
            die('%s: chunk %d starts at %d, expected %d' % (key, ci, a, want))
        if a < want:
            die('%s: chunk %d starts at %d, before the end of the chunk before it' % (key, ci, a))
        if a > want:
            segs.append(dict(gap=(want, a - 1)))
        segs += ann['segments']
        want = b + 1
    if want != n + 1:
        if not e.get('partial'):
            die('%s: the chunks end at line %d, the file has %d lines' % (key, want - 1, n))
        segs.append(dict(gap=(want, n)))

    name = os.path.basename(path)
    out = []
    w = out.append
    w('# `%s` explained' % name)
    w('')
    w('- Source file: `%s` in this folder (%s, %d lines, %d bytes).' % (name, LANG_NAME[e['lang']], n, nbytes))
    w('- sha256 of the source when this page was built: `%s`.' % sha)
    w('- Role in the whole-chip test: %s' % ov['role'].strip())
    w('- The left column of the table below is a copy of the source, made by a script. Its line numbers are the line numbers of the source.')
    if e.get('partial'):
        w('- The table shows only the parts of the file that the whole-chip test uses. A row says which lines are left out.')
    w('')
    w('## Short version: purpose')
    w('')
    w(ov['purpose'].strip())
    w('')
    if ov['words']:
        w('<details>')
        w('<summary>Words used here</summary>')
        w('')
        for x in ov['words']:
            w('- **%s**: %s' % (x['term'].strip(), x['def'].strip()))
        w('')
        w('</details>')
        w('')
    w('## How to read this file' if e['lang'] == 'text' else '## Main flow')
    w('')
    for i, st in enumerate(ov['main_flow'], 1):
        step = st['step'].strip()
        if st.get('lines'):
            where = ' (line%s %s)' % ('s' if '-' in st['lines'] else '', st['lines'])
            step = step[:-1] + where + '.' if step.endswith('.') else step + where
        w('%d. %s' % (i, step))
    w('')
    if ov.get('behavior_notes'):
        w('## Behavior a reader must know')
        w('')
        for x in ov['behavior_notes']:
            w('- ' + x.strip())
        w('')
    if ov.get('call_sequence'):
        w('## Call sequence in the whole-chip test')
        w('')
        for c in ov['call_sequence']:
            where = ' (line %d)' % c['line'] if c.get('line') else ''
            w('%s- `%s`%s: %s' % ('  ' * c['depth'], c['name'], where, c['note'].strip()))
        w('')
    if ov['functions']:
        w('## Functions')
        w('')
        w('| Function | Lines | What it does | Calls | On the timed path |')
        w('|---|---|---|---|---|')
        for fn in ov['functions']:
            rng = '%d-%d' % (fn['line'], fn['end']) if fn.get('end') else str(fn['line'])
            calls = ', '.join('`%s`' % c for c in fn.get('calls', [])) or '-'
            tp = {True: 'yes', False: 'no', None: '-'}[fn.get('timed_path')]
            w('| `%s` | %s | %s | %s | %s |' % (fn['name'].replace('|', '\\|'), rng, fn['what'].strip().replace('|', '\\|'), calls, tp))
        w('')
    w('## Source and explanation, side by side')
    w('')
    # The style attributes keep both columns on the screen: fixed column widths, and long source lines wrap inside
    # their cell. A viewer that drops style attributes shows the same table with a horizontal scroll bar.
    w('<table style="table-layout:fixed;width:100%">')
    w('<colgroup><col style="width:56%"><col style="width:44%"></colgroup>')
    w('<tr><th align="left">Source (line number, then the line)</th><th align="left">Explanation</th></tr>')
    for s in segs:
        if 'gap' in s:
            w('<tr><td colspan="2"><i>Lines %d to %d of the file are not shown here.</i></td></tr>' % s['gap'])
            continue
        if s.get('heading', '').strip():
            w('<tr><td colspan="2"><b>%s</b></td></tr>' % inline(s['heading'].strip()))
        body = []
        for ln in range(s['start'], s['end'] + 1):
            code = lines[ln - 1]
            num = str(ln).rjust(width)
            body.append(num + ('  ' + html.escape(code, quote=False) if code != '' else ''))
        w('<tr><td valign="top"><pre style="white-space:pre-wrap;overflow-wrap:anywhere;margin:0">' + '\n'.join(body)
          + '</pre></td><td valign="top">' + cell(s['text']) + '</td></tr>')
    w('</table>')
    w('')
    if ov.get('refs'):
        w('## References')
        w('')
        for r in ov['refs']:
            p = ' `%s`:' % r['path'] if r.get('path') else ''
            w('- [%s]%s %s' % (r['id'], p, r['what'].strip()))
        w('')
    dest = path + '.md'
    text = '\n'.join(out)
    with open(dest, 'w') as f:
        f.write(text)
    return dest, n, sum('gap' not in x for x in segs), len(text)


def verify(key):
    e = entry(key)
    path = e['path']
    lines, _, _ = source_lines(path)
    width = len(str(len(lines)))
    with open(path + '.md') as f:
        md = f.read()
    a, b = md.index('<table style='), md.index('</table>')
    block = md[a:b + len('</table>')]
    if '\n\n' in block or re.search(r'\n[ \t]+\n', block):
        die('%s.md: a blank line inside the table would end the HTML block' % path)
    shown = []
    for pre in re.findall(r'<pre[^>]*>(.*?)</pre>', block, re.S):
        for row in html.unescape(pre).split('\n'):
            num, rest = row[:width], row[width:]
            if rest == '':
                shown.append((int(num), ''))
            elif rest.startswith('  '):
                shown.append((int(num), rest[2:]))
            else:
                die('%s.md: bad row %r' % (path, row))
    want = set()
    for a, b in e['chunks']:
        want.update(range(a, b + 1))
    if [x[0] for x in shown] != sorted(want):
        die('%s.md: the line numbers of the table are not the lines of the manifest (%d shown, %d expected)'
            % (path, len(shown), len(want)))
    for num, text in shown:
        if lines[num - 1] != text:
            die('%s.md: line %d differs from the source' % (path, num))
    return len(shown)


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd = argv[1]
    if cmd == 'split':
        print(json.dumps(split(argv[2], int(argv[3]) if len(argv) > 3 else 600)))
    elif cmd == 'check-ann':
        for p in argv[2:]:
            check_ann(p)
    elif cmd == 'check-overview':
        for p in argv[2:]:
            check_overview(p)
    elif cmd in ('build', 'build-all'):
        for key in ([x['key'] for x in manifest()] if cmd == 'build-all' else argv[2:]):
            dest, n, nseg, size = build(key)
            v = verify(key)
            print('built %s: %d source lines, %d rows, %d bytes; left column equals the source (%d lines)' % (dest, n, nseg, size, v))
    elif cmd in ('verify', 'verify-all'):
        for key in ([x['key'] for x in manifest()] if cmd == 'verify-all' else argv[2:]):
            print('verified %s.md: left column equals the source (%d lines)' % (entry(key)['path'], verify(key)))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main(sys.argv)
