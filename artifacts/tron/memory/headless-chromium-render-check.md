---
name: headless-chromium-render-check
description: How to render and screenshot generated HTML pages from the claude-dev container (Playwright in a venv + Chromium runtime libs installed 2026-09-19)
metadata: 
  node_type: memory
  type: reference
  originSessionId: fcd18152-9ade-458a-935d-031499cd5ec4
  modified: 2026-09-19T21:09:24.739Z
---

The claude-dev container (Ubuntu 22.04, root, no node/browser preinstalled) can render HTML for visual QA:

- `python3 -m venv pwenv && pwenv/bin/pip install playwright && PLAYWRIGHT_BROWSERS_PATH=<dir> pwenv/bin/playwright install chromium` (network to pypi and the Playwright CDN works).
- The Chromium headless shell needs 13 apt libs that were missing; installed on 2026-09-19 with `apt-get install libnspr4 libnss3 libatk1.0-0 libatk-bridge2.0-0 libatspi2.0-0 libdbus-1-3 libgbm1 libasound2 libxcomposite1 libxdamage1 libxfixes3 libxkbcommon0 libxrandr2`. They persist in the container overlay; the venv lived in the session scratchpad and may be gone.
- Useful checks: `document.documentElement.scrollWidth` vs viewport at 360/420/768/1200 px to catch horizontal overflow; `page.on('pageerror')` for script errors; `element.screenshot()` per figure (full-page screenshots of 20k px tall pages are unreadable when downscaled); dispatch `input` events on range sliders to drive them.

**Why:** the user's house rule is HTML output with charts, and the dataviz skill requires looking at the rendered result; without this the only check was reading the code.
**How to apply:** reuse the apt libs (already present), recreate the venv if the scratchpad is gone, and screenshot per figure. Related: [[tron-concepts-page-2026-09-19]].
