import glob,re,statistics as st
R="/home/jhan/workspace/titan/cache-perf/crb/results"
def parse(path):
    procs=[];cur=None
    for i,ln in enumerate(open(path),1):
        s=ln.rstrip('\n')
        if s.startswith('-- '):
            cur={'hdr':s,'line':i,'iv':[]}; procs.append(cur); continue
        p=s.split(',')
        if cur is not None and len(p)>=7 and p[3].isdigit() and p[0] in ('read','write','copy','asmread','asmwrite','asmcopy'):
            cur['iv'].append((float(p[6]), int(p[4])//int(p[2])))
    return procs
def show(name,path,sel):
    out={}
    for pr in parse(path):
        k=sel(pr['hdr'])
        if k: out[k]=pr
    return out
def selra(h):
    m=re.match(r'-- binary (\S+) kernel (\S+) .* round (\d) load (\S+) utc (\S+)',h)
    if m and m.group(2)=='read': return (m.group(1),int(m.group(3)))
def selA1(h):
    m=re.match(r'-- step A1 tag (read_old|read_new)-r(\d) binary (\S+)',h)
    if m: return (m.group(3),int(m.group(2)))
allold72=[];
for s in (1,2,3):
    o=show('',glob.glob(R+f'/k120-T72A{s}-*/threads120.csv')[0],selra)
    for rd in (1,2):
        vo=[x[0] for x in o[('bw_old',rd)]['iv']]; vn=[x[0] for x in o[('bw_new',rd)]['iv']]; pn=[x[1] for x in o[('bw_new',rd)]['iv']]
        allold72+=vo
        print(f"7200 s{s} r{rd}: old {vo} med {st.median(vo):.2f} new {vn} med {st.median(vn):.2f} passes {pn} drop {(1-st.median(vn)/st.median(vo))*100:.2f}")
print('part A old 7200 range',min(allold72),max(allold72),len(allold72), 'width',round(max(allold72)-min(allold72),2))
old8=[]
o=show('',R+'/kernels-20261113T181222Z/threads120.csv',selra)
for rd in (1,2):
    vo=[x[0] for x in o[('bw_old',rd)]['iv']]; vn=[x[0] for x in o[('bw_new',rd)]['iv']]; pn=[x[1] for x in o[('bw_new',rd)]['iv']]; old8+=vo
    print(f"A-1 r{rd}: old {vo} med {st.median(vo):.2f} new {vn} med {st.median(vn):.2f} passes {pn} drop {(1-st.median(vn)/st.median(vo))*100:.2f}")
o=show('',R+'/partA-20261113T205055Z/A1.csv',selA1)
def parse2(path):
    procs=[];cur=None
    for i,ln in enumerate(open(path),1):
        s=ln.rstrip('\n')
        if s.startswith('-- '):
            cur={'hdr':s,'line':i,'iv':[]}; procs.append(cur); continue
        p=s.split(',')
        if cur is not None and len(p)>=7 and p[0]=='read' and p[3].isdigit():
            cur['iv'].append((float(p[6]), int(p[4])//int(p[2])))
    return procs
for pr in parse2(R+'/partA-20261113T205055Z/A1.csv'):
    k=selA1(pr['hdr'])
    if k:
        v=[x[0] for x in pr['iv']]; print('A-2',k,v,'med',f"{st.median(v):.2f}",'passes',[x[1] for x in pr['iv']])
        if k[0]=='bw_old': old8+=v
a2={selA1(pr['hdr']):pr for pr in parse2(R+'/partA-20261113T205055Z/A1.csv') if selA1(pr['hdr'])}
for rd in (1,2):
    vo=[x[0] for x in a2[('bw_old',rd)]['iv']]; vn=[x[0] for x in a2[('bw_new',rd)]['iv']]
    print(f"A-2 r{rd} drop {(1-st.median(vn)/st.median(vo))*100:.2f}")
for pr in parse2(R+'/partA-20261113T205055Z/A3.csv'):
    if 'onebuf-ms500-' in pr['hdr']:
        v=[x[0] for x in pr['iv']]; print('A-3',pr['hdr'][11:36],v); old8+=v
print('pool A-1..A-3 old',min(old8),max(old8),len(old8),'width',round(max(old8)-min(old8),2),'pct of lower end',round((max(old8)-min(old8))/min(old8)*100,2))
print('below',sorted(x for x in allold72 if x<min(old8)),'above',sorted(x for x in allold72 if x>max(old8)))
