#!/usr/bin/env python3
"""Structure check of a report file: number of lines, balance of tags, ids, link targets.
Usage: structure_check.py <report.html> [reference.html]
With a reference file it also lists the ids and link targets that differ."""
import re, sys
from html.parser import HTMLParser
VOID = {"meta", "link", "br", "img", "hr", "input", "rect", "line", "path", "circle", "stop", "use"}


class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []; self.err = []; self.ids = []; self.hrefs = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d: self.ids.append(d["id"])
        if "href" in d: self.hrefs.append(d["href"])
        if tag not in VOID: self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if "id" in d: self.ids.append(d["id"])

    def handle_endtag(self, tag):
        if tag in VOID: return
        if not self.stack or self.stack[-1][0] != tag:
            self.err.append((tag, self.getpos()[0], self.stack[-1] if self.stack else None))
            # recover: pop to the matching tag if there is one
            for k in range(len(self.stack) - 1, -1, -1):
                if self.stack[k][0] == tag:
                    del self.stack[k:]; break
        else:
            self.stack.pop()


def check(path):
    s = open(path, encoding="utf-8").read()
    # the two script blocks are not HTML: blank them, keep the line breaks
    body = re.sub(r"(<script>)(.*?)(</script>)", lambda m: m.group(1) + re.sub(r"[^\n]", " ", m.group(2)) + m.group(3), s, flags=re.S)
    p = P(); p.feed(body); p.close()
    lines = s.split("\n")
    n = len(lines) - 1 if lines[-1] == "" else len(lines)
    dup = sorted({i for i in p.ids if p.ids.count(i) > 1})
    inpage = [h for h in p.hrefs if h.startswith("#")]
    missing = [h for h in inpage if h[1:] not in p.ids]
    print(f"{path}\n  lines {n}; tag mismatches {len(p.err)}; open at end {[t for t, _ in p.stack]}; ids {len(p.ids)} (twice: {dup}); "
          f"href {len(p.hrefs)}, in-page {len(inpage)}, without target {missing}")
    for e in p.err[:10]: print("   mismatch", e)
    return p


a = check(sys.argv[1])
if len(sys.argv) > 2:
    b = check(sys.argv[2])
    print("  ids only in first:", sorted(set(a.ids) - set(b.ids)), " only in second:", sorted(set(b.ids) - set(a.ids)))
    print("  hrefs only in first:", sorted(set(a.hrefs) - set(b.hrefs)), " only in second:", sorted(set(b.hrefs) - set(a.hrefs)))
