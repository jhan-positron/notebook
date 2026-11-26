#!/usr/bin/env python3
"""Extract the visible text of the report page into three files:
body-r3.txt   - text outside <svg>, <style>, <script>
svg-r3.txt    - text elements inside svg (labels), without <title>
titles-r3.txt - distinct <title> tooltip texts
"""
import sys, re, html
from html.parser import HTMLParser

SRC = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html"
OUT = "/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/english/"

BLOCK = {"p","div","li","h1","h2","h3","h4","tr","table","figcaption","figure","summary","details","ul","ol","section","dt","dd","caption","thead","tbody","br","header","footer"}
CELL = {"td","th"}

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.body=[]
        self.svg=[]
        self.titles=[]
        self.in_svg=0
        self.in_title=0
        self.skip=0
        self.cur_title=[]
        self.cur_text=[]
        self.in_text=0
    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if tag in ("style","script"): self.skip+=1
        if tag=="svg":
            self.in_svg+=1
            self.body.append("\n[SVG]\n")
            a=dict(attrs)
            if a.get("aria-label"): self.svg.append("ARIA: "+a["aria-label"])
        if self.in_svg and tag=="title":
            self.in_title+=1; self.cur_title=[]
        if self.in_svg and tag=="text":
            self.in_text+=1; self.cur_text=[]
        if not self.in_svg:
            if tag in BLOCK: self.body.append("\n")
            if tag in CELL: self.body.append(" | ")
            if tag=="li": self.body.append("- ")
            if tag in ("h1","h2","h3","h4"): self.body.append("\n## ")
    def handle_endtag(self, tag):
        if self.stack and self.stack[-1]==tag: self.stack.pop()
        if tag in ("style","script"): self.skip-=1
        if self.in_svg and tag=="title":
            self.in_title-=1
            self.titles.append("".join(self.cur_title).strip())
        if self.in_svg and tag=="text":
            self.in_text-=1
            self.svg.append("".join(self.cur_text).strip())
        if tag=="svg":
            self.in_svg-=1
        if not self.in_svg and tag in BLOCK: self.body.append("\n")
    def handle_data(self, data):
        if self.skip: return
        if self.in_svg:
            if self.in_title: self.cur_title.append(data)
            elif self.in_text: self.cur_text.append(data)
            return
        self.body.append(data)

p=P()
src=open(SRC,encoding="utf-8").read()
p.feed(src)
body="".join(p.body)
body=re.sub(r"[ \t]+"," ",body)
body=re.sub(r"\n\s*\n+","\n",body)
open(OUT+"body-r3.txt","w").write(body)
open(OUT+"svg-r3.txt","w").write("\n".join(p.svg))
seen=[];s=set()
for t in p.titles:
    if t not in s: s.add(t); seen.append(t)
open(OUT+"titles-r3.txt","w").write("\n---\n".join(seen))
print(len(body), len(p.svg), len(p.titles), len(seen))
