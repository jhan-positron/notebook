---
name: svg-render-check
description: Render every inline SVG diagram to PNG (cairosvg is installed in claude-box) and inspect it before delivering an HTML doc; jhan caught clipped gutter labels and overlapping arrow labels in a shipped figure (2026-08-25)
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 5827c364-b93e-4e5c-aa49-89cb6addf5a4
  modified: 2026-08-25T17:46:02.730Z
---

Before handing over an HTML doc with an inline SVG, extract the `<svg>` and render it
(`python3 -c "import cairosvg; cairosvg.svg2png(...)"` works in claude-box; no browser is
available there) and Read the PNG. In the kv_cache-hpp-1199.html figure (PR3879) jhan had to
report: left row labels right-anchored at x=24 were clipped past x<0, arrow labels collided with
row captions placed at the same y, and right-side captions ran past the viewBox.

**Why:** the user views these in a browser/Notion screenshot; layout faults cost a round trip and
make the figure unreadable, which defeats the "present concepts visually" preference.

**How to apply:** reserve a label gutter (>=140 px for two-line labels) instead of anchoring text
at the edge; keep row captions inside the row or in the gutter, never in the arrow corridor;
route crossing arrows orthogonally with labels in empty gaps; set `width="100%"` with a
`max-width` and a viewBox that leaves ~20 px slack on both sides; render and look before
delivering. See [[mirror-naming-convention]] for the lineage note such figures must carry.

**cairosvg recipe traps (2026-09-08, apply_dense_amx_page walk-through):** (1) HTML named
entities (`&rarr;`, `&minus;`, `&times;`, `&Sigma;`) are not XML; convert them to Unicode
(html.unescape, keeping amp/lt/gt) before rendering, or the parse fails. (2) A page-level
`svg text { fill: ... }` rule overrides a `fill="..."` attribute on a `<text>`; colored labels
need `style="fill:..."`. (3) `marker-end` set in a CSS class points at one id for every figure;
give each figure its own marker id and set `marker-end` as an attribute per arrow, or cairosvg
crashes on the figures whose marker id is missing. (4) Inject the page's `svg .class` rules as a
`<style>` inside the extracted SVG, otherwise the render shows unstyled shapes.
