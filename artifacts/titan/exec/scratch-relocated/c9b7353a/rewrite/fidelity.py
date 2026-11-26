#!/usr/bin/env python3
"""fidelity.py OLD.html NEW.html - compare the numbers of two versions of the report.
Prints: numbers of table cells (not text cells) and of charts that differ (must be none), numbers that the
old prose holds and the new prose does not, numbers that the new prose holds and the old page nowhere holds,
reference markers [RefN] lost, and sentence length figures of the new prose."""
import collections, html, re, sys
NUM = re.compile(r"(?<![A-Za-z0-9_.])-?\d[\d,]*(?:\.\d+)?")
def strip(t): return html.unescape(re.sub(r"<[^>]+>", " ", t))
def nums(t): return collections.Counter(NUM.findall(strip(t)))
def parts(page):
    page = re.sub(r"<style.*?</style>", "", page, flags=re.S)
    svgs = re.findall(r"<svg.*?</svg>", page, flags=re.S)
    rest = re.sub(r"<svg.*?</svg>", " ", page, flags=re.S)
    cells, prose_cells = [], []
    def cell(m):
        (prose_cells if re.search(r"class=['\"][^'\"]*\btxt\b", m.group(1)) else cells).append(m.group(2))
        return " "
    def tbl(m):
        t = m.group(0)
        cap = " ".join(re.findall(r"<caption.*?</caption>", t, flags=re.S))
        re.sub(r"<t[dh]([^>]*)>(.*?)</t[dh]>", cell, t, flags=re.S)
        return " " + cap + " "
    rest = re.sub(r"<table.*?</table>", tbl, rest, flags=re.S)
    svgtext = " ".join(" ".join(re.findall(r"<text[^>]*>(.*?)</text>", s, flags=re.S)) for s in svgs)
    return " ".join(cells), svgtext, rest + " " + " ".join(prose_cells)
def diff(name, a, b):
    d1, d2 = a - b, b - a
    print("%s: %s" % (name, "identical" if not d1 and not d2 else "DIFFERENT"))
    if d1: print("   only in OLD:", dict(d1))
    if d2: print("   only in NEW:", dict(d2))
old, new = open(sys.argv[1]).read(), open(sys.argv[2]).read()
oc, osv, op = parts(old); nc, nsv, np_ = parts(new)
diff("numbers in table cells (text cells left out)", nums(oc), nums(nc))
diff("numbers in chart texts", nums(osv), nums(nsv))
allold = set(nums(old))
lost = sorted(set(nums(op)) - set(nums(np_)))
added = sorted(set(nums(np_)) - allold)
print("numbers in OLD prose that NEW prose lacks (%d): %s" % (len(lost), " ".join(lost)))
print("numbers in NEW prose that the OLD page nowhere holds (%d): %s" % (len(added), " ".join(added)))
orefs = collections.Counter(re.findall(r"\[Ref\d+\]", strip(op))); nrefs = collections.Counter(re.findall(r"\[Ref\d+\]", strip(np_)))
print("reference markers: OLD %d, NEW %d; lost keys: %s" % (sum(orefs.values()), sum(nrefs.values()), sorted(set(orefs) - set(nrefs))))
print("tables OLD %d NEW %d; charts OLD %d NEW %d; figures OLD %d NEW %d" % (old.count("<table"), new.count("<table"), old.count("<svg"), new.count("<svg"), old.count("<figure"), new.count("<figure")))
blocks = re.findall(r"<(p|li|figcaption|caption)\b[^>]*>(.*?)</\1>", re.sub(r"<svg.*?</svg>", " ", new, flags=re.S), flags=re.S)
long_ = []
for tag, b in blocks:
    t = re.sub(r"\s+", " ", strip(b)).strip()
    for s in re.split(r"(?<=[.!?])\s+(?=[A-Z(])", t):
        n = len(s.split())
        if n > 25: long_.append((n, tag, s))
ps = [b for t, b in blocks if t == "p"]
print("NEW prose: %d p, %d li; p elements with more than 2 sentences: %d; sentences over 25 words: %d" % (
    len(ps), sum(1 for t, _ in blocks if t == "li"),
    sum(1 for b in ps if len(re.findall(r"[.!?](?:\s|$)", strip(b))) > 2), len(long_)))
for n, tag, s in sorted(long_, reverse=True)[:40]:
    print("   %d words <%s>: %s" % (n, tag, s[:260]))
