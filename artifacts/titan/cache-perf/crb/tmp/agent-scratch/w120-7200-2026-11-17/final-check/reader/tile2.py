# tile2.py - cut the part screenshots into tiles; report where the content ends and whether anything is painted in the right gutter.
import sys, glob, os
from PIL import Image
d = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/final-check/reader/shots/'
bg = bytes((252, 252, 251))
for w, th in ((1280, 1100), (420, 1400)):
    for k in (1, 2, 3, 4):
        name = f'w{w}-part{k}.png'
        im = Image.open(d + name).convert('RGB'); W, H = im.size
        last = 0
        for y in range(H - 1, 0, -1):
            if im.crop((0, y, W, y + 1)).tobytes() != bg * W:
                last = y; break
        n = 0
        for y0 in range(0, last + 1, th):
            im.crop((0, y0, W, min(y0 + th, last + 20, H))).save(d + f'p{w}-{k}-{n:02d}.png'); n += 1
        print(name, 'size', W, H, 'content ends at row', last, 'tiles', n)
