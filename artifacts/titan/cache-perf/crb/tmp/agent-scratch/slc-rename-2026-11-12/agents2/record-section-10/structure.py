#!/usr/bin/env python3
import re, sys, collections
from html.parser import HTMLParser
C="/home/jhan/workspace/titan/cache-perf/crb"
files={"REVIEWED":C+"/tmp/crb-memory-hierarchy.before-slc-rename.html",
       "RENAMED":"/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/report.after-rename.before-fixes.html",
       "NOW":C+"/crb-memory-hierarchy.html"}
VOID={"meta","link","br","hr","img","input","path","rect","circle","line","stop","use","polygon","polyline","ellipse"}
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=True)
        s.ids=[]; s.hrefs=[]; s.stack=[]; s.mism=[]; s.tags=collections.Counter()
    def handle_starttag(s,tag,attrs):
        d=dict(attrs)
        s.tags[tag]+=1
        if "id" in d: s.ids.append(d["id"])
        if "href" in d: s.hrefs.append((tag,d["href"]))
        if tag not in VOID: s.stack.append((tag,s.getpos()))
    def handle_startendtag(s,tag,attrs):
        d=dict(attrs)
        s.tags[tag]+=1
        if "id" in d: s.ids.append(d["id"])
        if "href" in d: s.hrefs.append((tag,d["href"]))
    def handle_endtag(s,tag):
        if tag in VOID: return
        if s.stack and s.stack[-1][0]==tag: s.stack.pop()
        else: s.mism.append((tag,s.getpos(), s.stack[-1] if s.stack else None))
res={}
for name,f in files.items():
    t=open(f,encoding="utf-8").read()
    p=P(); p.feed(t); p.close()
    res[name]=p
    dup=[i for i,c in collections.Counter(p.ids).items() if c>1]
    inpage=[h for tag,h in p.hrefs if h.startswith("#")]
    other=[(tag,h) for tag,h in p.hrefs if not h.startswith("#")]
    missing=[h for h in inpage if h[1:] not in p.ids]
    print(f"{name}: lines={t.count(chr(10))+1} ids={len(p.ids)} distinct={len(set(p.ids))} dup={dup} hrefs={len(p.hrefs)} inpage={len(inpage)} distinct_inpage={len(set(inpage))} other={other} missing_targets={missing} tag_mismatch={len(p.mism)} unclosed={len(p.stack)} pre={p.tags['pre']} h3={p.tags['h3']} table={p.tags['table']} script={p.tags['script']} style={p.tags['style']}")
    if p.mism: print("  mism:",p.mism[:5])
    if p.stack: print("  unclosed:",p.stack[:5])
a=res["REVIEWED"]; b=res["NOW"]
print("new ids:",sorted(set(b.ids)-set(a.ids)),"removed ids:",sorted(set(a.ids)-set(b.ids)))
print("new hrefs:",sorted(set(b.hrefs)-set(a.hrefs)),"removed hrefs:",sorted(set(a.hrefs)-set(b.hrefs)))
print("ids with mesh-cache:",[i for i in b.ids if "mesh-cache" in i])
print("hrefs with mesh-cache:",[h for t,h in b.hrefs if "mesh-cache" in h])
