import sys
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/brief-language'
src=open(f'{S}/page_estimate.py').read().replace('\nmain()\n','\n')
ns={}; exec(compile(src,'page_estimate','exec'),ns)
C='/home/jhan/workspace/titan/cache-perf/crb'
def first_cap(path):
    p=ns['P'](); p.feed(open(path,encoding='utf-8').read())
    return [b for b in p.blocks if b[0]=='p.cap'][0][1]
after=first_cap(f'{C}/crb-memory-hierarchy-brief.html'); before=first_cap(f'{C}/tmp/crb-memory-hierarchy-brief.before-slc-rename.html')
W=ns['PAGE_W']
print('caption chars: before', len(before), 'after', len(after))
for f in (0.90,1.00,1.10,1.20,1.25,1.30,1.31,1.32,1.35,1.40):
    ns['FACTOR']=f
    lb=ns['wrap'](before, W, 9.5, 400); la=ns['wrap'](after, W, 9.5, 400)
    print(f'factor {f:.2f}: before {len(lb)} lines (single-line width {ns["tw"](before,9.5):.0f} px), after {len(la)} lines (single-line width {ns["tw"](after,9.5):.0f} px), page width {W:.0f} px')
