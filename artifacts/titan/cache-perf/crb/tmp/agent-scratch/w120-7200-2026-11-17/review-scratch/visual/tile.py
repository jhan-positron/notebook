import sys
from PIL import Image
src, prefix, th = sys.argv[1], sys.argv[2], int(sys.argv[3])
x0 = int(sys.argv[4]) if len(sys.argv) > 4 else 0
x1 = int(sys.argv[5]) if len(sys.argv) > 5 else None
im = Image.open(src).convert('RGB'); W, H = im.size
bg = (252, 252, 251)
last = H - 1
px = im.load()
while last > 0 and all(px[x, last] == bg for x in range(0, W, 7)):
    last -= 1
k = 0
for y0 in range(0, last + 1, th):
    im.crop((x0, y0, x1 or W, min(y0 + th, last + 20))).save(f'{prefix}-{k:02d}.png'); k += 1
print(src, W, H, 'content ends', last, 'tiles', k)
