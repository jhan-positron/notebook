---
name: html-charset-meta
description: Generated HTML files the user opens from disk need <meta charset="utf-8"> or non-ASCII text (middle dots, micro signs) shows as "Â" sequences
metadata:
  type: feedback
---

Every generated HTML page must start with `<meta charset="utf-8">` right after `<title>`. Prefer ASCII separators (", ") over "·" in SVG labels.

**Why:** On 2026-11-03 the user saw "Â" in asimov-memory-hierarchy.html diagram text. The file was opened from disk, so the browser guessed Latin-1 for the " · " separators. Artifact publishing adds the charset for you, but a file on disk does not.
**How to apply:** gen_hierarchy.py now emits the meta tag and uses commas. Check any new generator the same way. Related: [[asimov-run2-state]].
