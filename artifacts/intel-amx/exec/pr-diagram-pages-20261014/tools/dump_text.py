import re, sys, html, pathlib
src = pathlib.Path(sys.argv[1]); out = pathlib.Path(sys.argv[2])
s = src.read_text()
# replace each <svg ...>...</svg> with a placeholder carrying its id and size
def rep(m):
    blk = m.group(0)
    mid = re.search(r'<svg[^>]*\sid="([^"]+)"', blk)
    return f'\n[SVG id={mid.group(1) if mid else "?"} bytes={len(blk)}]\n'
t = re.sub(r'<svg\b.*?</svg>', rep, s, flags=re.S)
t = re.sub(r'<style>.*?</style>', '[STYLE]', t, flags=re.S)
t = re.sub(r'<script>.*?</script>', '[SCRIPT]', t, flags=re.S)
# keep structure: convert headings/paragraph tags to text with markers
t = re.sub(r'<(h[1-4])([^>]*)>', lambda m: f'\n\n<{m.group(1)}{m.group(2)}> ', t)
t = re.sub(r'</h[1-4]>', '\n', t)
t = re.sub(r'<pre class="diff">.*?</pre>', '[DIFF BLOCK]', t, flags=re.S)
t = re.sub(r'<(p|li|figcaption|div|figure|section|details|summary|tr)\b[^>]*>', lambda m: '\n' if m.group(1) not in ('figcaption','figure','details','summary') else f'\n<{m.group(1)}> ', t)
t = re.sub(r'<[^>]+>', '', t)
t = html.unescape(t)
t = re.sub(r'\n{3,}', '\n\n', t)
out.write_text(t)
print(src.name, '->', out, len(s), '->', len(t))
