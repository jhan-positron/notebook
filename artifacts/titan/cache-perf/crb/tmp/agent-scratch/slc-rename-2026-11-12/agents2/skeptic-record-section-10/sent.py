#!/usr/bin/env python3
# Independent recount of the sentences of the old passage (RENAMED lines 131-133)
# and of how many are in the new passage (NOW lines 131-133) word for word.
import re, html, sys
S="/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
OLD=open(S+"/report.after-rename.before-fixes.html",encoding="utf-8").read().split("\n")
NEW=open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html",encoding="utf-8").read().split("\n")
def text(line, blocksep):
    t=re.sub(r"</?(p|li|ul|ol|h3|td|th|tr|table|div|pre)[^>]*>",blocksep,line)
    t=re.sub(r"<[^>]+>","",t)
    return html.unescape(t)
def norm(s): return re.sub(r"\s+"," ",s).strip()
# method 1: manual-style split: each <p> is a block; inside split at ". " + capital
old_blocks=[norm(b) for n in (131,132,133) for b in text(OLD[n-1],"\x00").split("\x00") if norm(b)]
new_blocks=[norm(b) for n in (131,132,133) for b in text(NEW[n-1],"\x00").split("\x00") if norm(b)]
new_all=norm(" ".join(text(NEW[n-1]," ") for n in (131,132,133)))
def split(b): return [x for x in re.split(r"(?<=[.])\s+(?=[A-Z])",b) if x.strip()]
olds=[s for b in old_blocks for s in split(b)]
print("old blocks:",len(old_blocks),"old sentences:",len(olds))
in_block=[s for s in olds if any(s in nb for nb in new_blocks)]
in_all=[s for s in olds if s in new_all]
print("verbatim inside one new block:",len(in_block)," verbatim in joined new text:",len(in_all))
for s in olds:
    if not any(s in nb for nb in new_blocks): print("  NOT:",s)
# method 2: naive per-line split that keeps empty trailing piece
for name,rx,keep_empty in [("split on '. ' keep empties",r"\.\s+",True),("lookbehind stop then \\s* keep empties",r"(?<=\.)\s*(?=[A-Z<]|$)",True)]:
    tot=0;v=0
    for n in (131,132,133):
        t=norm(text(OLD[n-1]," "))
        parts=re.split(rx,t)
        if not keep_empty: parts=[p for p in parts if p.strip()]
        tot+=len(parts); v+=sum(1 for p in parts if p.strip()=="" or p.strip() in new_all)
    print(name,"-> old",tot,"verbatim",v)
# method 3: count per <p> paragraph
for n in (131,132,133):
    ps=re.findall(r"<p>(.*?)</p>",OLD[n-1])
    print("line",n,"paragraphs",len(ps),[len(split(norm(html.unescape(re.sub(r'<[^>]+>','',p))))) for p in ps])
