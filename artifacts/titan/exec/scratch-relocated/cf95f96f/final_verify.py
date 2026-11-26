# Independent check: left column of every side-by-side companion against the source file.
import json, re, html, hashlib, sys, os
T = sys.argv[1]
files = json.load(open(T + '/manifest.json'))['files']
bad = 0; tot_lines = 0; rows_total = 0; empty_right = 0
for e in files:
    src = e['path']; md = src + '.md'
    raw = open(src, 'rb').read()
    lines = raw.decode('utf-8').split('\n')
    if lines and lines[-1] == '': lines.pop()
    text = open(md, encoding='utf-8').read()
    sha = hashlib.sha256(raw).hexdigest()
    ok_sha = sha in text
    want = []
    for a, b in e['chunks']:
        want += list(range(a, b + 1))
    got = []
    # rows: <tr><td valign="top"><pre ...>LEFT</pre></td><td ...>RIGHT</td></tr>
    rows = re.findall(r'<tr><td valign="top"><pre[^>]*>(.*?)</pre>\s*</td>\s*<td[^>]*>(.*?)</td>\s*</tr>', text, re.S)
    for left, right in rows:
        rows_total += 1
        if not re.sub(r'<[^>]+>|\s', '', right): empty_right += 1
        for ln in left.split('\n'):
            m = re.match(r'^ *(\d+)(?:  (.*))?$', ln, re.S)
            if not m: got.append((None, ln)); continue
            got.append((int(m.group(1)), html.unescape(m.group(2) or '')))
    nums = [n for n, _ in got]
    mism = [(n, c) for n, c in got if n is None or n < 1 or n > len(lines) or lines[n - 1].rstrip('\r') != c] if nums == want else None
    status = 'OK' if (nums == want and not mism and ok_sha and len(lines) == e['lines']) else 'BAD'
    if status == 'BAD':
        bad += 1
        print(status, e['key'], 'numbers equal' if nums == want else 'NUMBERS DIFFER %d/%d' % (len(nums), len(want)), 'sha in page' if ok_sha else 'SHA MISSING', (mism or [])[:2])
    tot_lines += len(want)
print('companions', len(files), 'bad', bad, 'source lines compared', tot_lines, 'table rows', rows_total, 'rows with empty explanation', empty_right)
