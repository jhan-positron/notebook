---
name: review-by-edited-copy
description: "Jibin reviews an HTML report by saving a browser copy named <report>-edited.html with \"Jibin:\" notes inline; regenerate the original source file from those notes"
metadata:
  node_type: memory
  type: feedback
  originSessionId: ed41c79f-3dbe-4ef9-a1dc-1ef6bdcf135e
  modified: 2026-11-01T19:20:11.438Z
---

Jibin reviews a report by opening the published page, inserting notes that start with "Jibin:" (several bullet lines inside one div), and saving the DOM as `<name>-edited.html` next to the source (first seen 2026-11-01 for crb/crb-memory-hierarchy.html).

**Why:** The edited file is a browser DOM dump, not a clean source edit: it adds `<html><head>`, `<tbody>`, `&amp;`, closes void tags, and can mangle SVG text. Only the "Jibin:" notes matter.

**How to apply:** `grep -n "Jibin:"` in the edited copy, treat each bullet as a request, regenerate the real source file (never the edited copy), render it with Playwright's headless Chromium (`~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell --headless --no-sandbox --screenshot=...`) to check diagrams before publishing to the same artifact URL. Requests so far: explain every label in a diagram, add a section with diagrams per concept, confirm hardware claims against Arm documents. See [[crb-hierarchy-findings]].

**Charset:** Jibin opens the local source copy from the Windows W: drive. The source must start with `<meta charset="utf-8">`, or the symbols (×, ≥, –, …) show as "Ã—" (seen 2026-11-01). The published page gets this tag from the artifact skeleton, so the defect only shows in the local file.

**Render hang:** chrome-headless-shell hangs on the Google Fonts request when the network is slow. Add `--host-resolver-rules="MAP * ~NOTFOUND"` (fonts fall back, layout still checkable) and wrap in `timeout`. Never `pkill -f chrome-headless-shell` (it matches the calling shell); use `pgrep -x`.
