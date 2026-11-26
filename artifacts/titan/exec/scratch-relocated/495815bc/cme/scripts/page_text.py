"""Dumps the visible text of asimov-cme-perf.html (SVG replaced by a marker) to ../integ/page.txt,
the glossary to ../integ/terms.txt and the references to ../integ/refs.txt."""
import html, re, sys
src = '/home/jhan/workspace/titan/cache-perf/asimov/asimov-cme-perf.html'
out = '/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-asimov/495815bc-dbda-43cc-9015-e0d1efe06259/scratchpad/cme/integ/'
s = open(src, encoding='utf-8').read()
body = s.split('<body>', 1)[1]
body = re.sub(r'<script.*?</script>', '', body, flags=re.S)
def svgtxt(m):
    t = re.findall(r'<text[^>]*>(.*?)</text>', m.group(0), flags=re.S)
    t = [html.unescape(re.sub(r'<[^>]+>', '', x)).strip() for x in t]
    return '\n[SVG: %s]\n' % ' | '.join(x for x in t if x)
keep_svg = '--svg' in sys.argv
body = re.sub(r'<svg\b.*?</svg>', svgtxt if keep_svg else '\n[SVG]\n', body, flags=re.S)
body = re.sub(r'<a class="ref"[^>]*>\[Ref(\d+)\]</a>', r'[R\1]', body)
body = re.sub(r'</(td|th)>\s*<(td|th)[^>]*>', ' | ', body)
body = re.sub(r'<(h[123])[^>]*>', lambda m: '\n\n' + '#' * int(m.group(1)[1]) + ' ', body)
body = re.sub(r'<li[^>]*>', '\n- ', body)
body = re.sub(r'<(dt)[^>]*>', '\n* ', body)
body = re.sub(r'<dd[^>]*>', ' := ', body)
body = re.sub(r'<div class="lab">(.*?)</div>', r'\n[[\1]] ', body)
body = re.sub(r'</(p|div|tr|figcaption|h[123]|table|ul|ol|figure|section)>', '\n', body)
body = re.sub(r'<p class="takeaway">', '\n=> ', body)
body = re.sub(r'<[^>]+>', '', body)
body = html.unescape(body)
body = re.sub(r'[ \t]+', ' ', body)
body = re.sub(r'\n\s*\n+', '\n', body)
open(out + ('page_svg.txt' if keep_svg else 'page.txt'), 'w', encoding='utf-8').write(body)
i = body.find('# 1 Words used here'); j = body.find('\n## 2 ')
k = body.rfind('References')
print(len(body), 'chars', body.count('\n'), 'lines')
