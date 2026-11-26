#!/usr/bin/env python3
"""Per-page comparison of the C1-Nano txt vs md, plus per-page overlap of the other txts vs all md."""
import sys, re, unicodedata, os, glob
from collections import Counter

root = sys.argv[1]
N = 8

def norm(s):
    s = unicodedata.normalize("NFKC", s)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"==> picture.*?<==", " ", s)
    s = re.sub(r"<br>", " ", s)
    s = s.lower()
    return re.sub(r"[^a-z0-9]+", " ", s).split()

def shingles(w): return set(tuple(w[i:i+N]) for i in range(len(w)-N+1))

def txt_pages(path):
    raw = open(path, encoding="utf-8", errors="replace").read()
    return raw.split("\f")            # page i (1-based) = pages[i-1]

def md_pages(path, total):
    raw = open(path, encoding="utf-8", errors="replace").read()
    pat = re.compile(r"Page \*\*(\d+)\*\* of \*\*%d\*\*" % total)
    pages = {}
    pos = 0; last = 1
    for m in pat.finditer(raw):
        n = int(m.group(1))
        pages[n] = pages.get(n, "") + raw[pos:m.start()]
        pos = m.end()
    pages[total+1] = raw[pos:]        # trailing text after last marker
    return pages, [n for n in range(2, total+1) if n not in pages]

# ---------- Nano pair ----------
tp = txt_pages(os.path.join(root, "arm-txt", "c1-nano-trm.txt"))
mp, missing_markers = md_pages(os.path.join(root, "ARM", "md", "Arm-C1-Nano-TRM-r0p2.md"), 914)
print(f"Nano: txt pages={len([p for p in tp if p.strip()])}  md page markers missing for pages: {missing_markers}")

tot_txt = tot_miss = tot_md = tot_miss_rev = 0
rows = []
for n in range(1, 915):
    tw = Counter(norm(tp[n-1])) if n-1 < len(tp) else Counter()
    mw = Counter(norm(mp.get(n, "")))
    # footer/header words appear on every page in both; keep them, they cancel out
    miss = sum((tw - mw).values()); miss_rev = sum((mw - tw).values())
    tot_txt += sum(tw.values()); tot_miss += miss
    tot_md += sum(mw.values()); tot_miss_rev += miss_rev
    rows.append((n, sum(tw.values()), sum(mw.values()), miss, miss_rev))

print(f"Nano bag-of-words, per page then summed:")
print(f"  txt word occurrences not found on the same md page: {tot_miss:,} of {tot_txt:,} ({tot_miss/tot_txt:.1%})")
print(f"  md  word occurrences not found on the same txt page: {tot_miss_rev:,} of {tot_md:,} ({tot_miss_rev/tot_md:.1%})")

# whole-document bag of words (page-insensitive)
TW = Counter(norm(open(os.path.join(root,"arm-txt","c1-nano-trm.txt"),encoding="utf-8",errors="replace").read()))
MW = Counter(norm(open(os.path.join(root,"ARM","md","Arm-C1-Nano-TRM-r0p2.md"),encoding="utf-8",errors="replace").read()))
print(f"Nano bag-of-words, whole document:")
print(f"  txt occurrences absent from md: {sum((TW-MW).values()):,} of {sum(TW.values()):,} ({sum((TW-MW).values())/sum(TW.values()):.1%})")
print(f"  md occurrences absent from txt: {sum((MW-TW).values()):,} of {sum(MW.values()):,} ({sum((MW-TW).values())/sum(MW.values()):.1%})")
print("  top 25 words over-represented in txt vs md:", (TW-MW).most_common(25))
print("  top 25 words over-represented in md vs txt:", (MW-TW).most_common(25))

# histogram of per-page txt-missing fraction
import math
buckets = Counter()
for n, t, m, miss, mr in rows:
    if t == 0: continue
    f = miss / t
    b = "0-2%" if f < .02 else "2-5%" if f < .05 else "5-10%" if f < .10 else "10-25%" if f < .25 else "25-50%" if f < .5 else ">=50%"
    buckets[b] += 1
print("  pages by fraction of txt words missing from md page:", dict(buckets))
print("  worst 15 pages (page, txt words, md words, txt-missing, md-missing):")
for r in sorted(rows, key=lambda r: -r[3])[:15]:
    print("   ", r)

# sample dropped prose lines: txt lines with >=8 words whose first 8-gram is not in the md at all
MDSH = shingles(norm(open(os.path.join(root,"ARM","md","Arm-C1-Nano-TRM-r0p2.md"),encoding="utf-8",errors="replace").read()))
print("\n  sample txt lines (>=8 words) whose first 8-gram is nowhere in md:")
shown = 0; total_lines = 0; miss_lines = 0
for n, page in enumerate(tp, 1):
    for line in page.splitlines():
        w = norm(line)
        if len(w) < 8: continue
        total_lines += 1
        if tuple(w[:8]) not in MDSH:
            miss_lines += 1
            if shown < 30 and not re.search(r"\.{5,}", line):   # skip TOC dot leaders
                print(f"    p{n}: {line.strip()[:110]}")
                shown += 1
print(f"  lines >=8 words: {total_lines:,}; first-8-gram missing from md: {miss_lines:,} ({miss_lines/total_lines:.1%})")
# same, but only lines with no run of 3+ spaces inside (i.e., not table/column layout)
total2 = miss2 = 0
for n, page in enumerate(tp, 1):
    for line in page.splitlines():
        s = line.strip()
        if re.search(r"\S {3,}\S", s) or re.search(r"\.{5,}", s): continue
        w = norm(s)
        if len(w) < 8: continue
        total2 += 1
        if tuple(w[:8]) not in MDSH: miss2 += 1
print(f"  single-column prose lines only: {total2:,}; first-8-gram missing from md: {miss2:,} ({miss2/total2:.1%})")

# ---------- other txts: which pages overlap the md set ----------
union = set()
for m in glob.glob(os.path.join(root, "ARM", "md", "*.md")):
    union |= shingles(norm(open(m, encoding="utf-8", errors="replace").read()))
for name in ["c1-dsu-trm.txt", "c1-sme2-trm.txt", "c1-sme2-telemetry.txt"]:
    pages = txt_pages(os.path.join(root, "arm-txt", name))
    hi = []
    for n, page in enumerate(pages, 1):
        sh = shingles(norm(page))
        if len(sh) < 30: continue
        cov = len(sh & union) / len(sh)
        if cov >= 0.5:
            title = next((l.strip() for l in page.splitlines()[3:] if len(l.strip()) > 15), "")[:70]
            hi.append((n, round(cov, 2), title))
    print(f"\n{name}: pages with >=50% of their 8-grams found somewhere in ARM/md: {len(hi)} of {len(pages)}")
    for h in hi[:40]: print("   ", h)
    if len(hi) > 40: print(f"    ... and {len(hi)-40} more")
