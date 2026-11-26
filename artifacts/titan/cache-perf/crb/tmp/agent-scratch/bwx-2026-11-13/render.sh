#!/usr/bin/env bash
# render.sh: test, then screenshots of the three synthetic pages with the headless Chrome of the development machine (network blocked)
set -e
S=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/bwx-2026-11-13; A=$S/render
B=/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell
cd /home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/partA-analysis && python3 test_partA.py --keep $S/partA-synthetic | tail -1
rm -f $A/set*.png
for n in 1 2 3; do rm -rf $A/profile; mkdir -p $A/profile
env -i PATH=/usr/bin:/bin HOME=$A/home XDG_CONFIG_HOME=$A/home/.config XDG_CACHE_HOME=$A/home/.cache TMPDIR=$A/tmp FONTCONFIG_FILE=$A/fontconfig/fonts.conf timeout 120 $B --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --no-first-run --disable-background-networking --disable-component-update --disable-sync --disable-extensions --disable-crash-reporter --disable-breakpad --host-resolver-rules="MAP * ~NOTFOUND" --user-data-dir=$A/profile --hide-scrollbars --window-size=1000,${H:-15500} --screenshot=$A/set$n.png "file://$S/partA-synthetic/set$n/partA-result.html" >/dev/null 2>&1; done
python3 - <<P
from PIL import Image
import numpy as np
for n in (1,2,3):
    im=Image.open('$A/set%d.png'%n).convert('RGB'); a=np.asarray(im)
    rows=np.where((a<250).any(axis=(1,2)))[0]; h=min(int(rows.max())+20, im.size[1])
    k=0
    for y in range(0,h,1500):
        im.crop((0,y,1000,min(y+1500,h))).save('$A/set%d-%02d.png'%(n,k)); k+=1
    print(n, 'content height', h, 'pieces', k)
P
