#!/usr/bin/env python3
"""Count the sentences of old lines 131-133 (RENAMED) and check which are verbatim in NOW lines 131-133.
Split method: remove tags (block tags become a hard break), then split a block at '.', '?' or '!' that is
followed by white space and an upper-case letter or end of block. A closing bracket/paren after the stop is kept
with the sentence: '[file]. Next' and '(est.). Next'."""
import re, html, sys
S="/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
OLD=open(S+"/report.after-rename.before-fixes.html",encoding="utf-8").read().split("\n")
NEW=open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html",encoding="utf-8").read().split("\n")
def blocks(line):
    # block-level boundaries become \x00
    t=re.sub(r"</?(p|li|ul|ol|h3|td|th|tr|table|div|pre)[^>]*>","\x00",line)
    t=re.sub(r"<[^>]+>","",t)
    t=html.unescape(t)
    return [b.strip() for b in t.split("\x00") if b.strip()]
def split_sent(block):
    parts=re.split(r"(?<=[.!?])\s+(?=[A-Z])",block)
    return [p.strip() for p in parts if p.strip()]
old_s=[]
for n in (131,132,133):
    k=0
    for b in blocks(OLD[n-1]):
        for s in split_sent(b):
            old_s.append((n,s)); k+=1
    print("old line",n,":",k,"sentences")
print("old total:",len(old_s))
newtext={}
allnew=" ".join(" ".join(blocks(NEW[n-1])) for n in (131,132,133))
# new text also as individual blocks
newblocks=[b for n in (131,132,133) for b in blocks(NEW[n-1])]
verb=0; notv=[]
for i,(n,s) in enumerate(old_s,1):
    inblock=any(s in b for b in newblocks)
    if inblock: verb+=1
    else: notv.append((i,n,s))
print("verbatim in one new block:",verb," not verbatim:",len(notv))
for i,n,s in notv: print(f"  #{i} (old line {n}): {s}")
if "-v" in sys.argv:
    for i,(n,s) in enumerate(old_s,1): print(i,n,s)
