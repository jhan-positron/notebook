#!/usr/bin/env bash
# dump.sh WIDTH HEIGHT FILE OUT - dump DOM after scripts
S=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17
A=$S/render/visual-r1
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
  timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking \
  --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad \
  --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=$1,$2 --dump-dom "file://$3" >$4 2>$A/tmp/last-stderr.txt
echo "exit $?"
