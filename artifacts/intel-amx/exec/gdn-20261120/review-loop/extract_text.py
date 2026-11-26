#!/usr/bin/env python3
"""Plain-text extraction of the page: argv[1] = html, argv[2] = output text file. Figures become [SVG: ...] / [SVG-TEXT: ...] lines."""
import html, re, sys
s = open(sys.argv[1], encoding="utf-8").read()
def svgrep(m):
    block = m.group(0)
    texts = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<text[^>]*>(.*?)</text>", block, re.S)]
    a = re.search(r'aria-label="([^"]*)"', block)
    return "\n[SVG: %s]\n[SVG-TEXT: %s]\n" % ((a.group(1) if a else ""), " ; ".join(x for x in texts if x))
b = re.sub(r"<style\b.*?</style>", "", s, flags=re.S)
b = re.sub(r"<svg\b.*?</svg>", svgrep, b, flags=re.S)
b = re.sub(r"<(h[1-6])[^>]*>", lambda m: "\n\n" + "#" * int(m.group(1)[1]) + " ", b)
b = re.sub(r"</(p|div|li|tr|h[1-6]|summary|details|table|ul|ol|figcaption|figure|section|pre)>", "\n", b)
b = re.sub(r"<li[^>]*>", "- ", b); b = re.sub(r"</t[dh]>", " | ", b); b = re.sub(r"<[^>]+>", "", b)
b = html.unescape(b); b = re.sub(r"[ \t]+", " ", b); b = re.sub(r"\n\s*\n+", "\n\n", b)
open(sys.argv[2], "w").write(b)
print(len(b), "chars,", b.count("\n"), "lines")
