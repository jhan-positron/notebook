import re,html
now=open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html',encoding='utf-8').read().split('\n')
B=open('/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c',encoding='utf-8').read().split('\n')
PR=open('/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt',encoding='utf-8').read().split('\n')
l=now[130]
pres=re.findall(r'<pre><code>(.*?)</code></pre>',l,flags=re.S)
print('number of <pre><code> listings in line 131:',len(pres))
# raw check: nothing but text and entities inside
for k,p in enumerate(pres):
    assert '<' not in p and '>' not in p, 'raw angle bracket in listing %d'%k
    ents=set(re.findall(r'&[#\w]+;',p))
    print('listing',k,'entities used:',sorted(ents),'bare ampersands:',len(re.findall(r'&(?![#\w]+;)',p)))
dec=[html.unescape(p).split('\n') for p in pres]
src1=B[138-1:148]; src2=B[173-1:195]
print('listing0 == bandwidth.c 138..148:',dec[0]==src1,len(dec[0]),len(src1))
print('listing1 == bandwidth.c 173..195:',dec[1]==src2,len(dec[1]),len(src2))
pl=PR[44-1:59]
norm=lambda s:re.sub(r'\s+',' ',s).strip()
print('listing2 == probe 44..59 (white space apart):',[norm(x) for x in dec[2]]==[norm(x) for x in pl],len(dec[2]),len(pl))
# stricter: tokens equal
print('listing2 token-equal:',[x.split() for x in dec[2]]==[x.split() for x in pl])
for a,b in zip(dec[2],pl):
    print('   %-62s | %r'%(a,b))
print('--- context of bandwidth.c around the ranges')
for i in list(range(134,150))+list(range(170,197)):
    print('%4d  %s'%(i,B[i-1]))
