# tile.py SRC PREFIX X0 X1 TILE_H [OVERLAP] - cut a tall screenshot into tiles (CSS px at scale 1)
import sys
from PIL import Image
V='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3/shots/'
src,pre=sys.argv[1],sys.argv[2]; x0,x1,th=int(sys.argv[3]),int(sys.argv[4]),int(sys.argv[5])
ov=int(sys.argv[6]) if len(sys.argv)>6 else 0
im=Image.open(V+src).convert('RGB'); W,H=im.size
bg=bytes((252,252,251))
last=next(y for y in range(H-1,0,-1) if im.crop((0,y,W,y+1)).tobytes()!=bg*W)
k=0; y=0
while y<=last:
    im.crop((x0,y,x1,min(y+th,last+20))).save(V+f'{pre}-{k:02d}.png'); print(f'{pre}-{k:02d}.png', y, min(y+th,last+20)); k+=1; y+=th-ov
