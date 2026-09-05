import re,sys
from PIL import ImageFont
MD=sys.argv[1]; PT=float(sys.argv[2]); DIAG=int(sys.argv[3])   # font pt, diagram px
DPI=96; px=lambda pt: pt*DPI/72
W=int((210-2*18)/25.4*DPI); H=int((297-2*18)/25.4*DPI)   # printable px at 18 mm margins
def font(path,pt):
    return ImageFont.truetype(path,int(round(px(pt))))
try:
    F=font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',PT)
    FB=font('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',PT)
    FM=font('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',PT*0.85)
    FT=font('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',PT*0.92)
except Exception as e:
    print('font load failed',e); sys.exit(1)
LH=px(PT)*1.45
def wrap_lines(text,f,width):
    words=text.split(); lines=1; cur=''
    for w in words:
        t=(cur+' '+w).strip()
        if f.getlength(t)>width and cur:
            lines+=1; cur=w
        else: cur=t
    return lines
src=open(MD).read().splitlines()
total=0; i=0; log=[]
def add(h,what): 
    global total; total+=h; log.append((round(h),what))
while i<len(src):
    ln=src[i]
    if ln.startswith('<callout'):
        body=[]; i+=1
        while not src[i].startswith('</callout>'): body.append(src[i].strip()); i+=1
        i+=1
        txt=re.sub(r'\*\*','',' '.join(body))
        n=wrap_lines(txt,F,W-40-24)   # padding + icon
        add(n*LH+16,f'callout {n} lines'); continue
    if ln.startswith('```'):
        lang=ln[3:].strip(); body=[]; i+=1
        while not src[i].startswith('```'): body.append(src[i]); i+=1
        i+=1
        if lang=='mermaid': add(DIAG+8,'mermaid diagram'); continue
        n=sum(max(1,wrap_lines(b,FM,W-16)) if b.strip() else 1 for b in body)
        add(n*px(PT*0.85)*1.3+12,f'code {n} lines'); continue
    if ln.startswith('<table'):
        rows=[]; i+=1
        while not src[i].startswith('</table>'):
            if src[i].strip().startswith('<tr>'):
                cells=[]; i+=1
                while not src[i].strip().startswith('</tr>'):
                    cells.append(re.sub(r'</?td>','',src[i].strip())); i+=1
                rows.append(cells)
            i+=1
        i+=1
        ncol=len(rows[0])
        # column widths proportional to longest cell text, min 15%
        lens=[max(FT.getlength(r[c]) for r in rows) or 1 for c in range(ncol)]
        tot=sum(lens); widths=[max(0.15*W,(l/tot)*W) for l in lens]
        s=sum(widths); widths=[w*W/s for w in widths]
        h=0
        for r in rows:
            n=max(wrap_lines(c,FT,widths[k]-10) if c else 1 for k,c in enumerate(r))
            h+=n*px(PT*0.92)*1.35+6
        add(h+6,f'table {len(rows)} rows'); continue
    if ln.startswith("### ") or ln.startswith("# "):
        add(px(PT*1.25)*1.3+10,'heading'); i+=1; continue
    if ln.startswith('- '):
        txt=re.sub(r'\*\*','',ln[2:]); n=wrap_lines(txt,F,W-28)
        add(n*LH+2,f'bullet {n} lines'); i+=1; continue
    if ln.strip()=='FIGURE_PLACEHOLDER':
        add(DIAG+8,'figure'); i+=1; continue
    if ln.strip():
        txt=re.sub(r'\*\*','',ln); n=wrap_lines(txt,F,W); add(n*LH+4,f'para {n} lines')
    i+=1
for h,w in log: print(f'{h:5d}px  {w}')
print(f'TOTAL {total:.0f}px of {H}px printable ({total/H*100:.0f}% of one A4) at {PT}pt, diagram {DIAG}px, 18 mm margins')
