import sys, importlib.util
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/brief-language'
src=open(f'{S}/page_estimate.py').read().replace('\nmain()\n','\n')
ns={}; exec(compile(src,'page_estimate','exec'),ns)
from PIL import ImageFont
F=ns['FONTS']
path=sys.argv[1]
p=ns['P'](); p.feed(open(path,encoding='utf-8').read())
tw=ns['tw']; wrap=ns['wrap']
W=ns['PAGE_W']
print('page width px', W)
# kerning effect and check against PIL basic layout
s="DRAM write collapses only with heavy writers on both meshes: 64 writers on one mesh 394 GB/s, 32 on each mesh 173 GB/s."
f6=ImageFont.truetype(f'{F}/IBMPlexSans-600.ttf', 1000)
face=ns['FACE'][600]
nok=sum(face.hmtx[face.cmap[ord(c)]][0] for c in s)/1000*10.5
print('600 weight sample: PIL basic %.2f  hmtx-only %.2f  with kerning %.2f  chars %d'%(f6.getlength(s)/1000*10.5, nok, tw(s,10.5,600), len(s)))
for kind,payload in p.blocks:
    if kind=='ul':
        for cls,t in payload:
            wgt=600 if cls=='take' else 400
            ls=wrap(t, W-18, 10.5, wgt)
            print(f'-- li {cls or "-"} chars {len(t)} lines {len(ls)}')
            for l in ls: print(f'     {tw(l,10.5,wgt):6.1f} | {l}')
    if kind in('p.cap','p.sub'):
        size=9.5 if kind=='p.cap' else 10.5
        ls=wrap(payload, W, size, 400)
        print(f'-- {kind} chars {len(payload)} lines {len(ls)}')
        for l in ls: print(f'     {tw(l,size,400):6.1f} | {l}')
    if kind=='pagebreak': break
