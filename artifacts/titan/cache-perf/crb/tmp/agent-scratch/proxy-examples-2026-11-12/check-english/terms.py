import re,html,sys
src=open('../worker/draft-full.html').read()
lines=src.split('\n')
def txt(s):
    s=re.sub(r'<script.*?</script>','',s,flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>',' ',s))
# locate subsections
for i,l in enumerate(lines,1):
    if 'served by a local proxy' in l or 'costs 85 ns' in l or 'id="homeex"' in l or "getElementById('homeex')" in l:
        print('LOC',i,txt(l)[:120].strip())
terms=['mesh 0','two meshes','home node','crosspoint','proxy','TRM','CMN','CRB','root run','chunk','XOR','physical address','PA ','virtual address','RMS','fitted','core-positions','cache-state check','verify','asmread','subtract.py','LCN','LCC','builder','walker','chain','Bill','other domain','DRAM','L2','slice','hop','chiplet','SLC','boot','occupancy','home line','proxy line','local slice','read stream','accesses for each','load','Effective capacity is 64 MiB','kernel','candidates','node id','take','median']
for t in terms:
    hits=[i for i,l in enumerate(lines,1) if t in txt(l)]
    first=hits[0] if hits else None
    ctx=''
    if first:
        tl=txt(lines[first-1]); k=tl.find(t); ctx=tl[max(0,k-90):k+110].replace('\n',' ')
    print(f'{t!r}: first line {first}, n={len(hits)} :: {ctx}')
