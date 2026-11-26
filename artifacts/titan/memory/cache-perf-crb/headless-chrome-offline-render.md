---
name: headless-chrome-offline-render
description: This dev machine has a headless Chrome (playwright cache) that renders local HTML offline - screenshots, DOM after scripts, PDF print; exact command and font setup
metadata:
  type: reference
---

A headless browser exists on the dev machine (found on 2026-11-12 by a checker agent, after two older notes had said there was none):
`/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell` (Chrome for Testing 153).

Command that works, with the network blocked (replace `$A` by a scratch folder and create `$A/home $A/profile $A/tmp` first):

```
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
  timeout 120 <binary> --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking \
  --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad \
  --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile <mode> "file:///abs/path.html"
```

Modes: `--hide-scrollbars --window-size=1000,6400 --screenshot=out.png` (viewport only, so use a tall window and crop), `--dump-dom` (the page after its scripts ran; grep the stderr of `--enable-logging=stderr --v=0` for script errors), `--no-pdf-header-footer --print-to-pdf=out.pdf` (print layout, measure with PyMuPDF).

Fonts: the machine has only DejaVu in `/usr/share/fonts` and no `fc-list`. Write a `fonts.conf` with `<dir>` entries for a folder with the page font (IBM Plex Sans TTFs are in `crb/tmp/agent-scratch/spec-row-2026-11-11/fonts/`) and for `/usr/share/fonts`, plus `<alias><family>monospace</family><prefer><family>DejaVu Sans Mono</family></prefer></alias>`. Without that alias, code listings render in a proportional font. Web fonts do not load (network blocked), so IBM Plex Mono is never shown.

Each concurrent run needs its own `--user-data-dir`. The inotify "Too many open files" messages on stderr are harmless.

Use it for: the print layout of the brief ([[crb-brief-generator]]), figures that the report draws by script, and any new section of an HTML report. It supersedes the "no browser" statements in [[svg-render-check-without-browser]] and [[perf-measurement-tech-doc]].
