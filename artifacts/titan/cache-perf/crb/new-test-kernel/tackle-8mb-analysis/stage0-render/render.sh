#!/usr/bin/env bash
# render.sh: screenshot of stage0.html with the headless Chrome of the development machine (network blocked), cut into pieces.
A=$(dirname "$(realpath "$0")"); PAGE=$(realpath "$A/../stage0.html")
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
rm -rf "$A/profile" "$A"/page*.png; mkdir -p "$A/profile"
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 180 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=1000,${H:-16000} --screenshot=$A/page.png "file://$PAGE" >/dev/null 2>&1
python3 - "$A" <<P
import sys
from PIL import Image
Image.MAX_IMAGE_PIXELS = None
A = sys.argv[1]
im = Image.open(A + '/page.png').convert('RGB')
w, h = im.size
bbox = Image.eval(im, lambda v: 255 - v).getbbox()
hh = min(bbox[3] + 20, h)
k = 0
for y in range(0, hh, 1400):
    im.crop((0, y, w, min(y + 1400, hh))).save(A + '/page-%02d.png' % k); k += 1
print('content height', hh, 'of window', h, 'pieces', k)
P
