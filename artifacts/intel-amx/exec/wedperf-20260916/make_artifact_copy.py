#!/usr/bin/env python3
"""Make the publish copy of status/Wednesday-perf-test.html for the Artifact tool: the tool wraps the
file in its own <!doctype html>...<head>...<body> skeleton, so the copy keeps only <title>, the
description meta and <style> at the top, followed by the body content. Pure ASCII is asserted.
Usage: make_artifact_copy.py SRC_HTML OUT_HTML
"""
import re
import sys

src, out = sys.argv[1], sys.argv[2]
t = open(src).read()
title = re.search(r"<title>.*?</title>", t, flags=re.S).group(0)
desc = re.search(r'<meta name="description"[^>]*>', t).group(0)
style = re.search(r"<style>.*?</style>", t, flags=re.S).group(0)
body = re.search(r"<body>(.*)</body>", t, flags=re.S).group(1)
page = f"{title}\n{desc}\n{style}\n{body}"
assert all(ord(c) < 128 for c in page), "non-ASCII character"
open(out, "w").write(page)
print(f"wrote {out} ({len(page)} bytes)")
