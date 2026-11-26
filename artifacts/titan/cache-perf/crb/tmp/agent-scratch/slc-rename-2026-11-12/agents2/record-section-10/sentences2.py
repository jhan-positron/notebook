#!/usr/bin/env python3
import re, html, sys
S="/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc"
OLD=open(S+"/report.after-rename.before-fixes.html",encoding="utf-8").read().split("\n")
NEW=open("/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html",encoding="utf-8").read().split("\n")
def plain(line, sep="\x00"):
    t=re.sub(r"</?(p|li|ul|ol|h3|td|th|tr|table|div|pre)[^>]*>",sep,line)
    t=re.sub(r"<[^>]+>","",t)
    return html.unescape(t)
old=" ".join(plain(OLD[n-1]," ") for n in (131,132,133))
old=re.sub(r"\s+"," ",old).strip()
new=" ".join(plain(NEW[n-1]," ") for n in (131,132,133))
new=re.sub(r"\s+"," ",new)
rules={
 "A  stop+space+Capital": r"(?<=[.!?])\s+(?=[A-Z])",
 "B  stop+space": r"(?<=[.!?])\s+",
 "C  stop|colon +space": r"(?<=[.!?:])\s+",
 "D  stop|semicolon +space": r"(?<=[.!?;])\s+",
 "E  stop|colon|semicolon +space": r"(?<=[.!?:;])\s+",
 "F  stop or ']' or ')' then '.'": r"(?<=[.!?])\s+|(?<=\.\))\s*",
 "G  any '. ' or '.)' ": r"\.\s+|\.\)",
 "H  '.' anywhere not between digits": r"(?<!\d)\.(?!\d)\s*",
}
for name,rx in rules.items():
    parts=[p.strip() for p in re.split(rx,old) if p and p.strip()]
    v=sum(1 for p in parts if p in new)
    print(f"{name:40s} old={len(parts):3d} verbatim={v:3d} other={len(parts)-v}")
