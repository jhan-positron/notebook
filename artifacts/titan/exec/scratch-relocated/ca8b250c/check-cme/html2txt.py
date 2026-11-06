import sys, re, html
src = open(sys.argv[1], encoding='utf-8').read()
# drop style/script
src = re.sub(r'<style.*?</style>', '', src, flags=re.S)
src = re.sub(r'<script.*?</script>', '', src, flags=re.S)
# block separators
src = re.sub(r'</(p|li|tr|h[1-6]|div|figcaption|caption|table|ul|ol|section|svg)>', '\n', src)
src = re.sub(r'<br\s*/?>', '\n', src)
src = re.sub(r'</t[dh]>', ' | ', src)
src = re.sub(r'<text[^>]*>', ' [', src); src = re.sub(r'</text>', '] ', src)
src = re.sub(r'<[^>]+>', '', src)
src = html.unescape(src)
src = re.sub(r'[ \t]+', ' ', src)
src = re.sub(r'\n\s*\n+', '\n', src)
print(src)
