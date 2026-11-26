import re,html
a=open('../worker/applied.html').read().split('\n')
def strip(t): return html.unescape(re.sub(r'<[^>]+>',' ',t))
txt=[strip(l) if not (475<=i+1<=977) else l for i,l in enumerate(a)]
terms=['crosspoint','home node','proxy','XOR','PA\\b','physical address','VA\\b','virtual address','HN-S','Super Home','LCN','LCC','RMS','TRM','CMN','root run','map file','chunk','slice','chain','homelat','CAP_SYS_ADMIN','\\bhop','chiplet','builder','walker','Root security','\\bperf\\b','node id','frame number','self-test','probe','hash','lookup table','fitted','fit\\b','MiB','GiB','home line','proxy line','occupancy','Bill','evidence','median','homed','one-to-one','read off','pushed','mesh configuration','controls','L3, other domain','read stream','asmread','cache fill','CPU 0','kernel','timed load','mesh 0','mesh rule','SLC','Words used','in flight','candidate']
for t in terms:
    occ=[i+1 for i,l in enumerate(txt) if i+1<475 and re.search(t,l)]
    first=occ[0] if occ else None
    ctx=''
    if first:
        m=re.search(t,txt[first-1]); ctx=txt[first-1][max(0,m.start()-70):m.end()+90].replace('\n',' ')
    print(f'{t:20} first={first} n={len(occ)} first5={occ[:6]} :: {ctx}')
