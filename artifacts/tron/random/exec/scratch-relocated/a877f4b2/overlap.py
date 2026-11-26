#!/usr/bin/env python3
"""Word 8-gram coverage of each txt file against each md file (and the md union)."""
import sys, re, unicodedata, glob, os

N = 8

def norm_words(path):
    s = open(path, encoding="utf-8", errors="replace").read()
    s = unicodedata.normalize("NFKC", s)          # fold ligatures (ﬁ -> fi, ﬀ -> ff)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)  # md header comments
    s = re.sub(r"==> picture.*?<==", " ", s)
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)             # drop punctuation, md markup, table pipes
    return s.split()

def shingles(words):
    return set(tuple(words[i:i+N]) for i in range(len(words) - N + 1))

root = sys.argv[1]
txts = sorted(glob.glob(os.path.join(root, "arm-txt", "*.txt")))
mds  = sorted(glob.glob(os.path.join(root, "ARM", "md", "*.md")))

md_sh = {}
for m in mds:
    md_sh[os.path.basename(m)] = shingles(norm_words(m))
union = set().union(*md_sh.values())

print(f"{N}-word shingle coverage: fraction of each txt file's shingles found in md")
print()
hdr = f"{'txt file':26} {'shingles':>9} {'in ANY md':>10}  best single md (coverage)"
print(hdr)
for t in txts:
    w = norm_words(t); sh = shingles(w)
    if not sh: continue
    any_cov = len(sh & union) / len(sh)
    best = max(md_sh.items(), key=lambda kv: len(sh & kv[1]))
    best_cov = len(sh & best[1]) / len(sh)
    print(f"{os.path.basename(t):26} {len(sh):>9,} {any_cov:>9.1%}  {best[0]} ({best_cov:.1%})")

# reverse direction for the Nano pair: how much of the md is in the txt
nano_txt = shingles(norm_words(os.path.join(root, "arm-txt", "c1-nano-trm.txt")))
nano_md  = md_sh["Arm-C1-Nano-TRM-r0p2.md"]
print()
print(f"Nano pair, reverse: md shingles found in txt = {len(nano_md & nano_txt)/len(nano_md):.1%} of {len(nano_md):,}")
print(f"Nano pair, forward: txt shingles found in md = {len(nano_txt & nano_md)/len(nano_txt):.1%} of {len(nano_txt):,}")
