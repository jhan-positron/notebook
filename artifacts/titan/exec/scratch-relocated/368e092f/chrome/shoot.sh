#!/usr/bin/env bash
# shoot.sh HEIGHT: screenshot of the opened-details copy of the report, cut into parts of 1400 px
A=/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb-new-test-kernel/368e092f-68c9-444b-98e6-22b5a4799cfe/scratchpad/chrome; B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
cp /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/ASCT-cross-check.html $A/page.html
python3 -c "p='$A/page.html'; s=open(p).read().replace('<details>','<details open>'); open(p,'w').write(s)"
rm -rf $A/profile $A/part*.png; mkdir -p $A/home $A/profile $A/tmp
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf \
  timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking \
  --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad \
  --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=1040,$1 --screenshot=$A/shot.png "file://$A/page.html" 2>&1 | grep "written"
python3 - <<PY
from PIL import Image
import numpy as np
Image.MAX_IMAGE_PIXELS=None
im=Image.open('$A/shot.png')
a=np.asarray(im.convert('RGB')); bg=a[-1,0]
rows=np.where((a!=bg).any(axis=(1,2)))[0]; h=int(rows.max())+20
print('size',im.size,'content height',h)
n=0
for y in range(0,h,1400):
    im.crop((0,y,1040,min(y+1400,h))).save(f'$A/part{n:02d}.png'); n+=1
print(n,'parts')
PY
