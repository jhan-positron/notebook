#!/usr/bin/env bash
# shot.sh WIDTH HEIGHT FILE OUT [extra chrome flags] - offline headless Chrome screenshot
set -u
S=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17
A=$S/render/visual-r1
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
W=$1; H=$2; F=$3; O=$4; shift 4
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
  timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking \
  --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad \
  --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=$W,$H "$@" --screenshot=$O "file://$F" >/dev/null 2>$A/tmp/last-stderr.txt
echo "exit $? -> $O"
