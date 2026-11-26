# tile.py NAME WIDTH TILE_HEIGHT - cut a tall screenshot into tiles; report where content ends and the right-gutter paint
import sys
from PIL import Image
d = '/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r2/shots/'
name, w, th = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
im = Image.open(d + name).convert('RGB'); W, H = im.size
bg = bytes((252, 252, 251))
last = next((y for y in range(H - 1, 0, -1) if im.crop((0, y, W, y + 1)).tobytes() != bg * W), 0)
k = 0
for y0 in range(0, last + 1, th):
    im.crop((0, y0, W, min(y0 + th, last + 20))).save(d + name.replace('-full', '').replace('.png', f'-{k:02d}.png')); k += 1
print(f'{name}: size {W}x{H}; content ends at row {last}; {k} tiles')
