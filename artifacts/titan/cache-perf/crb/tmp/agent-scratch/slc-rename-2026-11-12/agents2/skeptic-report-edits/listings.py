import re,html,hashlib
NOW='/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html'
B='/home/jhan/workspace/titan/cache-perf/bench/bandwidth.c'
P='/home/jhan/workspace/titan/cache-perf/crb/results/probe-20261111T210017Z.txt'
L=open(NOW,encoding='utf-8').read().split('\n')
line=L[130]
pres=re.findall(r'<pre><code>(.*?)</code></pre>',line,flags=re.S)
print('pre blocks in line 131:',len(pres))
allpre=[(i+1,len(re.findall(r'<pre',x))) for i,x in enumerate(L) if '<pre' in x]
print('lines with <pre:',allpre)
src=open(B,encoding='utf-8').read().split('\n')
probe=open(P,encoding='utf-8').read().split('\n')
dec=[html.unescape(x).split('\n') for x in pres]
print('listing line counts',[len(d) for d in dec])
print('listing1 == bandwidth.c 138-148:',dec[0]==src[137:148])
print('listing2 == bandwidth.c 173-195:',dec[1]==src[172:195])
norm=lambda s:re.sub(r'\s+',' ',s).strip()
print('listing3 == probe 44-59 (ws normalised):',[norm(x) for x in dec[2]]==[norm(x) for x in probe[43:59]])
for x,y in zip(dec[2],probe[43:59]):
    if norm(x)!=norm(y): print('DIFF',repr(x),repr(y))
print('--- probe 36..62')
for i in range(30,64): print(i+1,repr(probe[i]))
print('sha256 bandwidth.c',hashlib.sha256(open(B,'rb').read()).hexdigest())
print('--- probe head')
for i in range(0,30): print(i+1,repr(probe[i]))
# raw entity check: any '&' in pre that is not &#10; &lt; &gt; &amp;
for k,x in enumerate(pres,1):
    ents=set(re.findall(r'&[^;\s]{1,8};',x))
    print('listing',k,'entities',ents,'bare & count',len(re.findall(r'&(?!#10;|lt;|gt;|amp;)',x)),'tabs',x.count('\t'))
print('--- bandwidth.c 130..200')
for i in range(129,200): print(i+1,src[i])
