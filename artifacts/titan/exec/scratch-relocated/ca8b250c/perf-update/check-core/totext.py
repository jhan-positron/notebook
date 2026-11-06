import sys, re, html
src = open(sys.argv[1], encoding='utf-8').read()
# drop style and script
src = re.sub(r'<style.*?</style>', '', src, flags=re.S)
src = re.sub(r'<script.*?</script>', '', src, flags=re.S)
# svg: keep text nodes with marker
src = re.sub(r'<svg(.*?)</svg>', lambda m: '[SVG: ' + ' | '.join(re.findall(r'<text[^>]*>(.*?)</text>', m.group(1), flags=re.S)) + ']\n', src, flags=re.S)
src = re.sub(r'</(tr|p|li|h[1-6]|div|figcaption|caption|table)>', '\n', src)
src = re.sub(r'</t[dh]>', ' | ', src)
src = re.sub(r'<br\s*/?>', '\n', src)
src = re.sub(r'<[^>]+>', '', src)
src = html.unescape(src)
lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in src.split('\n')]
out = '\n'.join(l for l in lines if l)
open(sys.argv[2], 'w').write(out)
print(len(out.split('\n')), 'lines')
