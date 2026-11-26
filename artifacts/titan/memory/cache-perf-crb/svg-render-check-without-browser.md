---
name: svg-render-check-without-browser
description: "cairosvg route to render and measure a static inline SVG figure of a crb/*.html report (scripts check_geometry.py and render.py); a headless Chrome also exists, see headless-chrome-offline-render"
metadata:
  node_type: memory
  type: reference
  originSessionId: 6eb09a16-5942-4cc5-8ed0-249c7d5ab696
  modified: 2026-11-11T21:43:00.371Z
---

Corrected on 2026-11-12: the dev machine does have a headless Chrome ([[headless-chrome-offline-render]]), so figures drawn by script can be rendered too. This note keeps the cairosvg route, which is quicker for one static SVG and has the geometry checker. `cairosvg` 2.9, `PIL` and `fontTools` are installed for python3 (found 2026-11-11). No system fonts are installed and `fc-list` is missing, so cairosvg needs fonts through `FONTCONFIG_FILE`.

- Working scripts and the page font (IBM Plex Sans 400/500/600 TTF, fetched from the Google Fonts CSS that the report links) are in
  `~/workspace/titan/cache-perf/crb/tmp/agent-scratch/spec-row-2026-11-11/`:
  `render.py <html> <out.png>` renders the first `<svg role="img">`, and
  `check_geometry.py <html> [min_padding]` checks text fit, column alignment and viewBox bounds with real font metrics.
- cairosvg mis-places `<tspan>` with a different font-weight inside anchored text. Keep one weight per `<text>`.
- Only static SVG can be rendered this way. For charts drawn by the page's JavaScript use the headless Chrome.
- The local render matched the user's browser screenshot of the same figure, so it is a valid layout check.

Related: [[perf-measurement-tech-doc]] (older note that said layout can only be checked by coordinates; this supersedes that part).
