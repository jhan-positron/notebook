#!/bin/bash
# usage: render.sh <html> <mode args...>
A=$(dirname "$0"); H=$1; shift
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
 timeout 120 /home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile "$@" "file://$H" 
