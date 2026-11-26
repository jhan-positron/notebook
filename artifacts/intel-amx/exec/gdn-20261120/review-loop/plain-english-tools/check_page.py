#!/usr/bin/env python3
"""Run the length check of the plain-english-experiment skill on a page, twice:
  1. on the page as it is (paragraphs and bullets);
  2. on a copy in which table cells and figure captions are turned into paragraphs, so that their prose is counted too.
Use: python3 check_page.py <page.html> [text that must occur in a reported line ...]
Prints the violations of both runs (the second run only where it adds lines). With filter words, only matching lines.
Exit code 0 when nothing is printed."""
import os, re, subprocess, sys, tempfile
CK = "/home/jhan/.claude/skills/plain-english-experiment/scripts/check_lengths.py"
page, filters = sys.argv[1], sys.argv[2:]
s = open(page).read()
t = re.sub(r"<(/?)(td|th|figcaption)\b[^>]*>", lambda m: f"<{m.group(1)}p>", s)
t = re.sub(r"</?(table|thead|tbody|tr)\b[^>]*>", "", t)
tmp = tempfile.NamedTemporaryFile("w", suffix=".html", delete=False)
tmp.write(t); tmp.close()
strip = lambda out: [re.sub(r"^[^:]*:\d+: ", "", l) for l in out.splitlines()]
a = strip(subprocess.run([sys.executable, CK, page], capture_output=True, text=True).stdout)
b = strip(subprocess.run([sys.executable, CK, tmp.name], capture_output=True, text=True).stdout)
os.unlink(tmp.name)
rows = [("text", l) for l in a] + [("cell or caption", l) for l in b if l not in a]
rows = [r for r in rows if not filters or any(f.lower() in r[1].lower() for f in filters)]
for where, l in rows:
    print(f"[{where}] {l}")
print(f"{len(rows)} violations" + (" (filtered)" if filters else ""))
sys.exit(1 if rows else 0)
