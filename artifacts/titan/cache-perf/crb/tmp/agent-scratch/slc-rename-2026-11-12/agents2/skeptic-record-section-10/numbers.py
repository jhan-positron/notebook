#!/usr/bin/env python3
"""Read-only: compare the numbers of the old passage (RENAMED lines 131-133) with the new passage
(NOW lines 131-133). Listings (<pre>) are left out of the new text."""
import re, html, collections

S = "/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
OLD = open(S + "/report.after-rename.before-fixes.html", encoding="utf-8").read().split("\n")
NEW = open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html", encoding="utf-8").read().split("\n")


def plain(lines, drop_pre):
    t = " ".join(lines)
    if drop_pre:
        t = re.sub(r"<pre>.*?</pre>", " ", t)
    t = re.sub(r"<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t))


old = plain(OLD[130:133], False)
new = plain(NEW[130:133], True)
num = r"(?<![\w.])\d+(?:[.,]\d+)*(?:\s?(?:GB/s|B|KiB|MiB|%|cycles?))?"
co = collections.Counter(re.findall(num, old))
cn = collections.Counter(re.findall(num, new))
print("numbers of the old text that are not in the new text:", sorted(k for k in co if k not in cn))
print("numbers of the new text that are not in the old text:", sorted(k for k in cn if k not in co))
print("numbers with a lower count in the new text:", {k: (co[k], cn[k]) for k in co if cn[k] < co[k]})
words_old = len(old.split())
words_new = len(new.split())
print("words old:", words_old, "words new (listings left out):", words_new)
