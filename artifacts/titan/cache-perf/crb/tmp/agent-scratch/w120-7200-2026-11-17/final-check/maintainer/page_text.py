#!/usr/bin/env python3
"""page_text.py - visible text of the report page, one block per line (svg titles kept apart). Usage: page_text.py page.html > out.txt"""
import html, re, sys
t = open(sys.argv[1], encoding="utf-8").read()
t = re.sub(r"<style>.*?</style>", "", t, flags=re.S)
t = re.sub(r"<title>(.*?)</title>", lambda m: "\n[tooltip] " + m.group(1) + "\n", t, flags=re.S)
t = re.sub(r"</(p|li|h1|h2|h3|tr|dd|dt|figcaption|summary|text|div)>", "\n", t)
t = html.unescape(re.sub(r"<[^>]+>", " ", t))
for l in t.split("\n"):
    l = re.sub(r"\s+", " ", l).strip()
    if l:
        print(l)
