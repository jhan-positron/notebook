#!/usr/bin/env bash
# render_q1.sh PAGE.html OUTDIR: screenshot of the page with the headless Chrome of the development machine (network blocked),
# cut into pieces of 1500 px. Same command as tmp/agent-scratch/bwx-2026-11-13/render.sh.
set -e
PAGE=$(realpath "$1"); OUT=$(realpath -m "$2"); mkdir -p "$OUT"
A=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13/render
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
rm -rf "$OUT/profile" "$OUT"/page*.png; mkdir -p "$OUT/profile" "$OUT/home" "$OUT/tmp"
env -i PATH=/usr/bin:/bin HOME=$OUT/home XDG_CONFIG_HOME=$OUT/home/.config XDG_CACHE_HOME=$OUT/home/.cache TMPDIR=$OUT/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 180 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$OUT/profile --hide-scrollbars --window-size=1000,${H:-16000} --screenshot=$OUT/page.png "file://$PAGE" >/dev/null 2>&1
python3 - <<P
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS=None
im=Image.open('$OUT/page.png').convert('RGB'); a=np.asarray(im)
rows=np.where((a<250).any(axis=(1,2)))[0]; h=min(int(rows.max())+20, im.size[1]); k=0
for y in range(0,h,1500):
    im.crop((0,y,1000,min(y+1500,h))).save('$OUT/page-%02d.png'%k); k+=1
print('content height', h, 'of window', im.size[1], 'pieces', k)
P
