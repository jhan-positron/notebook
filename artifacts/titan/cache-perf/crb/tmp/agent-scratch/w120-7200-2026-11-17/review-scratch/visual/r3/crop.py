# crop.py SRC OUT X0 Y0 X1 Y1 [SCALE] - crop in CSS px from a screenshot taken at device scale factor SCALE (default 2)
import sys
from PIL import Image
V='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17/review-scratch/visual/r3/shots/'
src,out=sys.argv[1],sys.argv[2]; x0,y0,x1,y1=[float(a) for a in sys.argv[3:7]]; s=float(sys.argv[7]) if len(sys.argv)>7 else 2
im=Image.open(V+src); im.crop((int(x0*s),int(y0*s),int(x1*s),int(y1*s))).save(V+out); print(out, (int((x1-x0)*s),int((y1-y0)*s)))
