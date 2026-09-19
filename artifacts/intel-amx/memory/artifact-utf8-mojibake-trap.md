---
name: artifact-utf8-mojibake-trap
description: "2026-09-13: Artifact publish rendered a valid UTF-8 page with Latin-1 mojibake (· -> Â·, ᵀ -> áµ€, × -> Ã—, → -> â†', Σ -> Î£); fix = write pages as pure ASCII with numeric HTML entities, <sup>T</sup>, CSS \\00B7 escapes"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 97fe382e-01e4-49e9-b02b-782618f409a7
  modified: 2026-09-14T00:43:23.908Z
---

jhan (2026-09-13): "There are many messed up symbols" - screenshots of the published artifact
PR3879/baseline-vs-mirror-sketch.html showed every non-ASCII glyph double-decoded (UTF-8 bytes
read as Latin-1). The local file was valid UTF-8 with no double encoding (checked with python
decode + byte counts), so the corruption is in the artifact publishing/serving path, not in
the file.

**Why:** the page relied on the host's charset meta; whatever the cause, a pure-ASCII page
cannot be mis-decoded.
**How to apply:** before publishing any artifact, run a pass that (1) replaces every char with
ord > 127 outside <style> by `&#NNN;`, (2) writes superscripts as <sup>T</sup> in HTML and
<tspan baseline-shift="super" font-size="70%">T</tspan> inside inline SVG, (3) uses CSS
escapes (`"\00B7 "`) for glyphs in <style> strings, then assert the file is ASCII. Keep the
check in the SVG render step ([[svg-render-check]]). Applies to every HTML the user's rule
"HTML is default" produces when it goes through the Artifact tool.

Addendum (same day): inside inline SVG do not use superscript tspans either (baseline-shift and dy variants both mis-render under text-anchor="middle" in cairosvg, and browser support for baseline-shift varies); write S^T as plain text, the notation the tron code comments already use. <sup>T</sup> is fine in HTML text.
