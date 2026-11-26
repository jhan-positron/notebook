import sys
sys.path.append(sys.argv[1])
import fitz, re
d = fitz.open(sys.argv[2])
for i in (30, 31):
    t = d[i].get_text()
    for m in re.finditer(r'ways|SLC|[Ss]ystem [Ll]evel [Cc]ache', t):
        a = max(0, m.start()-160); b = min(len(t), m.end()+200)
        print(f"--- index {i} (printed page {i+1}) ---\n{t[a:b]!r}\n")
