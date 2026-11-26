import sys
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc/agents/brief-language'
src=open(f'{S}/page_estimate.py').read().replace('\nmain()\n','\n')
ns={}; exec(compile(src,'page_estimate','exec'),ns)
path=sys.argv[1]; factor=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
ns['FACTOR']=factor
p=ns['P'](); p.feed(open(path,encoding='utf-8').read())
tw=ns['tw']; wrap=ns['wrap']; W=ns['PAGE_W']
for kind,payload in p.blocks:
    if kind=='table':
        total, cols, detail, (smin,smax) = ns['table_layout'](payload, W, 'standards')
        print(f'table: height {total:.1f}; sum min {smin:.1f}; sum max {smax:.1f}; t={(W-smin)/(smax-smin):.3f}')
        print('  columns', [round(c,1) for c in cols])
        for r in payload:
            for j,(k,t) in enumerate(r):
                size,wgt,ls=(9.5,600,0.19) if k=='th' else (10.0,400,0.0)
                tt=' '.join(t.split()); tt=tt.upper() if k=='th' else tt
                lines=wrap(tt, cols[j]-12, size, wgt, ls)
                print(f'   col {j} avail {cols[j]-12:6.1f}  full {tw(tt,size,wgt,ls):6.1f}  lines {len(lines)}: ' + ' | '.join(f'{l} ({tw(l,size,wgt,ls):.1f})' for l in lines))
            print('   --')
        break
