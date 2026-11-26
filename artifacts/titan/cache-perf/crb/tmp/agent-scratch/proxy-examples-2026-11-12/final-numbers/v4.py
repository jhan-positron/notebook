import csv,collections,math,statistics as S
R='/home/jhan/workspace/titan/cache-perf/crb/results/sudo-20261102T054936Z/'
L=collections.defaultdict(dict)
for r in csv.DictReader(open(R+'full/latency.csv')):
    if r['mesh']=='-1': continue
    c=int(r['core']); k=(int(r['mesh']),int(r['x']),int(r['y']))
    L[k].setdefault(c,[]).append(float(r['ns_median']))
M10={"1,1":"5,4","1,2":"5,5","1,3":"6,3","1,4":"5,1","2,1":"6,4","2,2":"6,5","2,3":"5,3","2,4":"6,1","2,5":"5,2","3,1":"7,4","3,2":"7,3","3,3":"7,2","3,4":"7,1","3,5":"6,2","4,1":"2,3","4,2":"4,4","4,3":"4,3","4,4":"4,2","5,1":"1,4","5,2":"2,5","5,3":"4,1","5,4":"1,1","5,5":"1,2","6,1":"2,4","6,2":"3,5","6,3":"3,2","6,4":"2,1","6,5":"2,2","7,1":"3,4","7,2":"1,3","7,3":"3,3","7,4":"3,1"}
M={tuple(map(int,k.split(','))):tuple(map(int,v.split(','))) for k,v in M10.items()}
inv={v:k for k,v in M.items()}
for agg,name in [(min,'min'),(lambda v:sum(v)/len(v),'mean')]:
  for reader,cores,mp in [(0,range(64),M),(1,range(64,120),inv)]:
    other=1-reader; ok=0; d=[]
    for hx in mp:
        vec=[agg(L[(other,)+hx][c]) for c in cores]
        best=sorted((math.sqrt(sum((a-agg(L[(reader,)+lx][c]))**2 for a,c in zip(vec,cores))/len(vec)),lx) for lx in mp.values())
        ok+= best[0][1]==mp[hx]; d.append(best[0][0])
    print(name,'reader',reader,'raw match equals map',ok,'/32  rms med %.3f max %.3f'%(S.median(d),max(d)))
