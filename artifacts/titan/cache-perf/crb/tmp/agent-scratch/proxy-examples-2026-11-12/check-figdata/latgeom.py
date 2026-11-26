#!/usr/bin/env python3
"""Geometry of the labels of the latency figure (viewBox units), ymax 180. Text widths are measured in lat.png (1.5 px per unit)."""
import math
K=1024;M=K*K;G=M*K
W,H,L,R,T,B=880,400,56,20,20,48; ymax=180
x0=math.log2(4*K); x1=math.log2(2*G)
X=lambda b: L+(math.log2(b)-x0)/(x1-x0)*(W-L-R)
Y=lambda v: T+(1-v/ymax)*(H-T-B)
fresh=[[256*K,3.66],[512*K,3.73],[M,3.74],[1.5*M,3.76],[2*M,5.79],[3*M,14.95],[4*M,19.21],[6*M,24.24],[8*M,26.09],[12*M,27.99],[16*M,29.09],[24*M,29.74],[32*M,30.18],[40*M,30.40],[48*M,30.54],[56*M,30.67],[64*M,35.86],[80*M,53.84],[96*M,65.81],[128*M,80.49],[192*M,94.74],[256*M,109.31],[512*M,140.87],[G,148.23],[2*G,149.86]]
rep=[[4*K,1.43],[8*K,1.43],[16*K,1.43],[32*K,1.43],[48*K,1.43],[64*K,1.43],[96*K,1.63],[128*K,1.84],[256*K,2.19],[512*K,1.88],[M,3.75],[1.5*M,3.77],[2*M,4.03],[3*M,5.10],[4*M,6.18],[8*M,6.78],[16*M,5.63],[32*M,5.42],[64*M,23.91],[96*M,47.49],[128*M,71.36],[192*M,86.62],[256*M,101.96],[512*M,138.76],[G,148.19],[2*G,150.25]]
ASC,DESC=9.5,3.0   # 12.5 px bold: cap/ascender and descender, viewBox units (est.)
def box(name,x,base,w,anchor):
    xl={'start':x,'middle':x-w/2,'end':x-w}[anchor]; return name,xl,xl+w,base-ASC,base+DESC
def hits(b,series,sname):
    n,xl,xr,yt,yb=b; out=[]
    pts=[(X(p[0]),Y(p[1])) for p in series]
    for (ax,ay),(bx,by) in zip(pts,pts[1:]):
        for i in range(101):
            px=ax+(bx-ax)*i/100; py=ay+(by-ay)*i/100
            if xl<=px<=xr and yt<=py<=yb: out.append((round(px,1),round(py,1))); break
    for px,py in pts:
        if xl-4<=px<=xr+4 and yt-4<=py<=yb+4: out.append(('dot',round(px,1),round(py,1)))
    return out
print('units per ns %.3f; gridlines'%((H-T-B)/ymax),{v:round(Y(v),1) for v in range(0,181,40)},'axis y',H-B,'tick label baseline',H-B+19)
def report(b):
    n,xl,xr,yt,yb=b
    print('%-28s x %.1f..%.1f  y %.1f..%.1f'%(n,xl,xr,yt,yb),'| blue',hits(b,fresh,'f'),'| orange',hits(b,rep,'r'),'| gridlines inside',[v for v in range(0,181,40) if yt<Y(v)<yb], '| crosses axis' if yt<H-B<yb else '')
# widths from lat.png: L1 181 px, L2 209, SLC 187, repeated 385, DRAM 231, gap 74 (px at 1.5 px per unit)
w=lambda px: px/1.5
print('--- draft')
report(box('L1',X(16*K),Y(1.43)-10,w(181),'middle'))
report(box('L2',X(1.2*M),Y(3.75)-12,w(209),'middle'))
report(box('SLC',X(48*M),Y(30.4)-12,w(187),'end'))
report(box('repeated chain',X(32*M),Y(5.42)+20,w(385),'middle'))
report(box('DRAM',X(G),Y(148)-12,w(231),'end'))
report(box('5.6x gap',X(32*M)+8,(Y(30.18)+Y(5.42))/2+4,w(74),'start'))
print(' band label DRAM: baseline',T+14,'top',T+14-9)
print('--- proposed')
report(box('L2 end at X(1.5M)',X(1.5*M),Y(3.75)-12,w(209),'end'))
report(box('SLC -24',X(48*M),Y(30.4)-24,w(187),'end'))
report(box('5.6x gap end, left of dash',X(32*M)-8,(Y(30.18)+Y(5.42))/2+4,w(74),'end'))
report(box('repeated chain above line, end at X(32M)-? ',X(24*M),Y(5.42)-10,w(385),'end'))
report(box('repeated chain start X(40M) y-?',X(8*M),Y(6.78)-10,w(385),'end'))
print('--- proposed set 2 (width of the short label is est.: 385 px * 22/43 characters)')
report(box('repeated chain: 5.4 ns',X(32*M)-8,Y(5.42)-10,w(385*22/43),'end'))
report(box('5.6x gap, end, raised',X(32*M)-8,Y(5.42)-26,w(74),'end'))
report(box('L2 end at X(1.5M)',X(1.5*M),Y(3.75)-12,w(209),'end'))
print('dots near: fresh', [(round(X(a),1),round(Y(b),1)) for a,b in fresh if 460<X(a)<610], 'rep', [(round(X(a),1),round(Y(b),1)) for a,b in rep if 400<X(a)<610])
