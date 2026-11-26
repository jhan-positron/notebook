import re
B = open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html', encoding='utf-8').read()
def tokenize(js):
    toks = []; i = 0; n = len(js); line = 0
    while i < n:
        c = js[i]
        if c == '/' and i + 1 < n and js[i+1] == '/':
            j = js.find('\n', i); j = n if j < 0 else j
            toks.append(('lcom', js[i:j], line)); i = j; continue
        if c in '\'"`':
            q = c; j = i + 1
            while j < n and js[j] != q:
                if js[j] == '\\': j += 1
                j += 1
            toks.append(('str', js[i:j+1], line)); line += js.count('\n', i, j+1); i = j + 1; continue
        if c == '\n': line += 1
        i += 1
    return toks
for m in re.finditer(r'<script>(.*?)</script>', B, flags=re.S):
    start = B.count('\n', 0, m.start(1)) + 1
    for kind, text, off in tokenize(m.group(1)):
        if kind == 'str':
            body = text[1:-1]
            # keep strings that look like visible text: contain a space or a capital word, exclude pure attribute names/colours
            if re.fullmatch(r'[#\w.,:%() -]*', body) and not re.search(r'[A-Za-z]{3,} [A-Za-z]|[A-Z]{2,}|slice|cache|mesh|port|core|chiplet|read|write|copy', body):
                continue
            if re.fullmatch(r'(font-size|font-weight|text-anchor|stroke-width|stroke-dasharray|stroke-linejoin|font-family|marker-end|http://www.w3.org/2000/svg|middle|end|start|none|round|text|line|rect|circle|path|title|defs|marker|url\(#ar\)|rotate\(-90 14 |rotate\(-90 10 |hsl\(213 65% |auto|read|write|idle|prov|pass|maybe)', body):
                continue
            print(f"{start + off:4d} str  {body}")
        else:
            print(f"{start + off:4d} com  {text}")
