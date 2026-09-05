# Figure: three measurements, two comparisons, two supplies. Canvas is 2x; displayed at ~700 px wide.
from PIL import ImageFont
import cairosvg, html
W,H=1400,470
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'; FONTB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def width(txt,size,bold=False): return ImageFont.truetype(FONTB if bold else FONT,size).getlength(txt)
out=[]; overflow=[]
def text(x,y,txt,size=24,bold=False,fill='#222',maxw=None,anchor='middle'):
    w=width(txt,size,bold)
    if maxw and w>maxw: overflow.append((txt,round(w),maxw))
    st=f"font-family:'DejaVu Sans',Arial,sans-serif;font-size:{size}px;{'font-weight:bold;' if bold else ''}fill:{fill}"
    out.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{st}">{html.escape(txt)}</text>')
def box(x,y,w,h,fill,stroke,rx=14,dash=None,sw=3):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>')
def line(x1,y1,x2,y2,stroke='#666',sw=3,dash=None,marker='gray',both=True):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    m=f' marker-end="url(#a-{marker})"'+(f' marker-start="url(#a-{marker})"' if both else '')
    out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}"{d}{m}/>')
def path(d,stroke,marker,sw=4):
    out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" marker-end="url(#a-{marker})"/>')

BLUE,BLUED='#2f6db3','#1d4f8a'; AMB,AMBD='#b7791f','#7a4f0a'; GRN,GRND='#2e7d4f','#1f6a3d'
# Tron box
TX,TY,TW,TH=20,85,300,215; box(TX,TY,TW,TH,'#e8f0fb',BLUE); cx=TX+TW/2
text(cx,TY+40,'Tron with AMX off',27,True,maxw=TW-16)
text(cx,TY+74,'the real program',21,maxw=TW-16)
text(cx,TY+100,'real language model',21,maxw=TW-16)
text(cx,TY+126,'FPGA (accelerator) cards',21,maxw=TW-16)
text(cx,TY+176,'AVX unit 3.527 µs',26,True,fill=BLUED,maxw=TW-16)
# unit_bench container
UX,UY,UW,UH=530,32,480,318; box(UX,UY,UW,UH,'#fbf6ea',AMB,rx=18,dash='10,8'); ucx=UX+UW/2
text(ucx,UY+34,'unit_bench: one program',28,True,fill=AMBD,maxw=UW-16)
text(ucx,UY+60,'two code paths, copied per-unit code',20,fill=AMBD,maxw=UW-16)
text(ucx,UY+84,'synthetic pages; no model, no FPGA, no joins',20,fill=AMBD,maxw=UW-16)
BX,BY,BW,BH=545,130,200,150; box(BX,BY,BW,BH,'#ffffff',AMB); bcx=BX+BW/2
text(bcx,BY+40,'AVX path',28,True,maxw=BW-12)
text(bcx,BY+72,'AVX code copy',22,maxw=BW-12)
text(bcx,BY+118,'3.193 µs',26,True,fill=AMBD,maxw=BW-12)
MX,MY,MW,MH=785,130,200,150; box(MX,MY,MW,MH,'#ffffff',AMB); mcx=MX+MW/2
text(mcx,MY+40,'AMX path',28,True,maxw=MW-12)
text(mcx,MY+72,'AMX code copy',22,maxw=MW-12)
text(mcx,MY+118,'2.727 µs',26,True,fill=AMBD,maxw=MW-12)
# B <-> M: same program, other code path
line(BX+BW+3,BY+BH/2,MX-3,BY+BH/2,marker='gray')
text(ucx,UY+UH-38,'same program, other code path',22,True,fill='#444',maxw=UW-20)
text(ucx,UY+UH-12,'AMX effect 0.47 µs per unit',22,fill='#444',maxw=UW-20)
# Result box
CX,CY,CW,CH=1180,140,200,120; box(CX,CY,CW,CH,'#eaf6ec',GRN); ccx=CX+CW/2
text(ccx,CY+46,'Result',26,True,maxw=CW-12)
text(ccx,CY+90,'est. +14.4%',27,True,fill=GRND,maxw=CW-12)
# T <-> B: same work, copied code (dashed), label in the gutter
gy=205; line(TX+TW+3,gy,BX-3,gy,dash='9,7',marker='gray')
gcx=(TX+TW+BX)/2; gw=BX-(TX+TW)-12
text(gcx,gy-52,'same work,',22,True,fill='#444',maxw=gw)
text(gcx,gy-26,'copied code',22,True,fill='#444',maxw=gw)
text(gcx,gy+40,'gap 9.5%',22,fill='#b3261e',maxw=gw)
# unit_bench -> result: the covered unit plus the tile extras
ay=MY+MH/2; path(f'M {UX+UW} {ay} L {CX-6} {ay}',GRN,'grn')
acx=(UX+UW+CX)/2; aw=CX-(UX+UW)-12
text(acx,ay-16,'covered unit',21,True,fill=GRND,maxw=aw)
text(acx,ay+30,'+ tile extras',19,fill=GRND,maxw=aw)
# Tron -> result: every other measured term, routed along the bottom
by=H-22; path(f'M {cx} {TY+TH} L {cx} {by} L {ccx} {by} L {ccx} {CY+CH+6}',BLUE,'blue')
text((cx+ccx)/2,by-12,'every other measured term (other work, joins, barrier, untimed rest, page-loop overhead)',21,True,fill=BLUED,maxw=ccx-cx-20)
def marker(mid,fill):
    return f'<marker id="a-{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="4.5" markerHeight="4.5" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{fill}"/></marker>'
svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>{marker('gray','#666')}{marker('grn',GRN)}{marker('blue',BLUE)}</defs>
<rect width="{W}" height="{H}" fill="#ffffff"/>
{chr(10).join(out)}
</svg>'''
open('fig.svg','w').write(svg)
cairosvg.svg2png(bytestring=svg.encode(),write_to='fig.png',output_width=W)
cairosvg.svg2png(bytestring=svg.encode(),write_to='fig-display.png',output_width=700)
print('overflow:',overflow if overflow else 'none')
