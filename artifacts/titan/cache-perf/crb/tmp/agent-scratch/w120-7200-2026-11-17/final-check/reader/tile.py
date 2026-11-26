# tile.py - cut a tall screenshot into tiles; report where the content ends.
import sys
from PIL import Image
src, w, th, prefix = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
im = Image.open(src).convert('RGB'); W, H = im.size
bg = im.getpixel((W - 2, H - 2))
last = H - 1
for y in range(H - 1, 0, -1):
    row = im.crop((0, y, W, y + 1)).tobytes()
    if row != bytes(bg) * W:
        last = y; break
print(src, 'size', W, H, 'bg', bg, 'content ends at row', last)
k = 0
for y0 in range(0, last + 1, th):
    im.crop((0, y0, W, min(y0 + th, last + 20, H))).save(f'{prefix}-{k:02d}.png'); k += 1
print(k, 'tiles')
