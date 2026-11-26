#!/usr/bin/env bash
# render_parts.sh - the page is taller than one 16000 px screenshot, so render it in parts from temporary copies (under final-check/reader/work) that hide the other sections.
set -eu
A=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/final-check/reader
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
P=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html
chrome() { env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile1280 "$@"; }
sed "s|</style>|main>#q2,main>#q2~*{display:none!important}</style>|" $P > $A/work/part1.html
sed "s|</style>|main>*{display:none!important}main>#q2,main>#q2~*{display:revert!important}main>#open,main>#open~*{display:none!important}</style>|" $P > $A/work/part2.html
sed "s|</style>|main>*{display:none!important}main>#open,main>#open~*{display:revert!important}main>#refs,main>#refs~*{display:none!important}</style>|" $P > $A/work/part3.html
sed "s|</style>|main>*{display:none!important}main>#refs,main>#refs~*{display:revert!important}</style>|" $P > $A/work/part4.html
for w in 1280 420; do for k in 1 2 3 4; do
  chrome --hide-scrollbars --window-size=$w,16000 --screenshot=$A/shots/w$w-part$k.png "file://$A/work/part$k.html" >/dev/null 2>>$A/tmp/err.txt || echo fail $w $k
done; done
ls -la $A/shots/*part*.png
