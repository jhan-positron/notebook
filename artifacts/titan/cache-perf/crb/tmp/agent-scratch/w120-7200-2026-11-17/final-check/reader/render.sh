#!/usr/bin/env bash
# render.sh - reader-lens screenshots of the report at widths 1280 and 420 (full page, cut into tiles).
set -eu
A=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/final-check/reader
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
P=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html
chrome() { prof=$1; shift; env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/$prof "$@"; }
chrome profile1280 --hide-scrollbars --window-size=1280,16000 --screenshot=$A/shots/full1280.png "file://$P" >/dev/null 2>$A/tmp/err1280.txt || true
chrome profile420 --hide-scrollbars --window-size=420,16000 --screenshot=$A/shots/full420.png "file://$P" >/dev/null 2>$A/tmp/err420.txt || true
ls -la $A/shots
