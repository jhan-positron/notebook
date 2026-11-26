#!/usr/bin/env bash
# shot.sh W H file.html out.png  - offline headless screenshot (reviewer scratch)
D=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/reader/r2; A=$D/chrome
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=$1,$2 --screenshot=$4 "file://$3" >/dev/null 2>&1
