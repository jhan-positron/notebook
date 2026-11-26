#!/usr/bin/env python3
"""textdump.py PAGE.html - print the prose of the report as plain text: headings, paragraphs, bullets,
figure takeaways, table captions and notes. Charts and table bodies are replaced by one marker line."""
import html, re, sys
p = open(sys.argv[1]).read()
p = re.sub(r"<style.*?</style>", "", p, flags=re.S)
p = re.sub(r"<svg.*?</svg>", "\n[chart]\n", p, flags=re.S)
def tbl(m):
    t = m.group(0)
    cap = " ".join(re.findall(r"<caption.*?</caption>", t, flags=re.S))
    txt = re.findall(r"<td[^>]*class=['\"][^'\"]*\btxt\b[^>]*>(.*?)</td>", t, flags=re.S)
    return "\n[table] " + cap + "".join("\n   text cell: " + x for x in txt) + "\n"
p = re.sub(r"<table.*?</table>", tbl, p, flags=re.S)
p = re.sub(r"<h([1-4])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)) + " ", p)
p = re.sub(r"<li[^>]*>", "\n  - ", p)
p = re.sub(r"<(p|figcaption|div|section|ul|ol)\b[^>]*>", "\n", p)
p = html.unescape(re.sub(r"<[^>]+>", "", p))
print(re.sub(r"\n\s*\n+", "\n\n", p))
