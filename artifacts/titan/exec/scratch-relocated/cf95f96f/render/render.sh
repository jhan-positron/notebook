#!/usr/bin/env bash
# render.sh MD OUT.png [WIDTH] [HEIGHT] - Markdown (GFM) to HTML with pandoc, then a screenshot with headless Chrome. Network blocked.
set -euo pipefail
A=$(cd "$(dirname "$0")" && pwd); md=$1; png=$2; W=${3:-1400}; H=${4:-2600}
html=$A/$(basename "$md").html
{ echo '<!doctype html><meta charset="utf-8"><style>body{font:14px/1.45 sans-serif;margin:20px;background:#fff;color:#111}
table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px 8px}pre,code{font:12px/1.4 monospace}code{background:#f3f3f1}</style>';
  pandoc -f gfm -t html "$md"; } > "$html"
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
  timeout 120 /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run \
  --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad \
  --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=$W,$H --screenshot="$png" "file://$html" 2>/dev/null
ls -la "$png"
