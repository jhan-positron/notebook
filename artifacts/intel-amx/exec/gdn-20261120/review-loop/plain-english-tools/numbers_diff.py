#!/usr/bin/env python3
"""Compare the numbers of two versions of the page (text outside figures and styles).
Use: python3 numbers_diff.py <old.html> <new.html>
Prints every numeric token whose count differs between the two versions. A plain-English rewrite must not change a number,
so every printed line needs a reason (for example: a number repeated because one sentence became two)."""
import collections, html, re, sys


def nums(path):
    s = open(path).read()
    s = re.sub(r"<(svg|style)\b.*?</\1>", " ", s, flags=re.S)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return collections.Counter(re.findall(r"(?<![A-Za-z_])[-+]?\d[\d,]*(?:\.\d+)?(?:e[-+]?\d+)?", s))


a, b = nums(sys.argv[1]), nums(sys.argv[2])
diff = sorted((k for k in set(a) | set(b) if a[k] != b[k]), key=lambda k: (len(k), k))
for k in diff:
    print(f"{k!r}: {a[k]} -> {b[k]}")
print(f"{len(diff)} numeric tokens differ in count ({sum(a.values())} -> {sum(b.values())} tokens)")
