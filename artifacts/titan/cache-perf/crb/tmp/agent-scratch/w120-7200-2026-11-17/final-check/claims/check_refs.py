#!/usr/bin/env python3
"""Reference check of the page: every cited [RefN] has an entry, every anchor resolves, every path exists,
and every cited line number exists in its file. Prints the cited lines for reading."""
import os
import re
import sys
from bs4 import BeautifulSoup

PAGE = sys.argv[1] if len(sys.argv) > 1 else '/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html'
R = '/home/jhan/workspace/titan/cache-perf/crb/results'
S = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17'
SHOW = '--show' in sys.argv

soup = BeautifulSoup(open(PAGE, encoding='utf-8').read(), 'html.parser')
ids = set(t['id'] for t in soup.find_all(id=True))
hrefs = [a['href'] for a in soup.find_all('a', href=True)]
internal = [h for h in hrefs if h.startswith('#')]
broken = sorted(set(h for h in internal if h[1:] not in ids))
print('internal links: %d, distinct targets: %d, broken: %s' % (len(internal), len(set(internal)), broken))
external = sorted(set(h for h in hrefs if not h.startswith('#')))
print('non-anchor hrefs:', external[:20])

# reference entries
entries = {}
for li in soup.find_all('li', id=re.compile(r'^ref\d+$')):
    n = int(li['id'][3:])
    entries[n] = re.sub(r'\s+', ' ', li.get_text(' ')).strip()
print('reference entries: %d (Ref%d to Ref%d), gaps: %s' % (len(entries), min(entries), max(entries), sorted(set(range(1, max(entries) + 1)) - set(entries))))
cited = {}
for a in soup.find_all('a', href=re.compile(r'^#ref\d+$')):
    n = int(a['href'][4:])
    txt = a.get_text().strip()
    if txt != '[Ref%d]' % n:
        print('LABEL MISMATCH: link text %r points to ref%d' % (txt, n))
    cited[n] = cited.get(n, 0) + 1
print('cited but not listed:', sorted(set(cited) - set(entries)))
print('listed but never cited:', sorted(set(entries) - set(cited)))
# order of first citation
first = []
body_refs = [int(a['href'][4:]) for a in soup.find_all('a', href=re.compile(r'^#ref\d+$'))]
for n in body_refs:
    if n not in first:
        first.append(n)
print('order of first citation is ascending:', first == sorted(first), '' if first == sorted(first) else first)
# visible "[RefN]" text that is not a link
text = soup.get_text(' ')
plain = re.findall(r'\[Ref(\d+)\]', text)
print('"[RefN]" strings in text: %d; links: %d + %d list labels' % (len(plain), len(body_refs), len(entries)))

for n in sorted(entries):
    e = entries[n]
    m = re.match(r'\[Ref%d\]\s+(\S+)\s*(\(([^)]*)\))?\s*:' % n, e)
    if not m:
        print('Ref%d: CANNOT PARSE: %s' % (n, e[:120]))
        continue
    path = m.group(1)
    full = path.replace('R/', R + '/', 1) if path.startswith('R/') else path.replace('S/', S + '/', 1) if path.startswith('S/') else path
    ok = os.path.exists(full)
    lines = []
    if m.group(3):
        for a, b in re.findall(r'(\d+)(?: to (\d+))?', m.group(3)):
            if b:
                lines += list(range(int(a), int(b) + 1))
            else:
                lines.append(int(a))
    nl = None
    if ok and os.path.isfile(full):
        with open(full, errors='replace') as fh:
            content = fh.read().split('\n')
        nl = len(content) - (1 if content and content[-1] == '' else 0)
    bad = [x for x in lines if nl is not None and x > nl]
    print('Ref%d: %s exists=%s lines_in_file=%s cited_lines=%s %s cited %dx' % (n, path, ok, nl, lines if lines else '-', 'BAD LINES %s' % bad if bad else '', cited.get(n, 0)))
    if SHOW and ok and lines and os.path.isfile(full):
        for x in lines:
            if x <= nl:
                print('      %6d| %s' % (x, content[x - 1][:230]))
