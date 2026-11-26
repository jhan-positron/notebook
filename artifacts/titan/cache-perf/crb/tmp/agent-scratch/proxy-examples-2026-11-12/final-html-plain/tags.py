import re,sys,collections
from html.parser import HTMLParser
D='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/'
src=open(D+'applied.html').read()
a=src.split('\n')
VOID={'br','img','hr','meta','link','input','col','wbr'}
PCLOSE={'ul','ol','table','div','p','figure','h1','h2','h3','h4','pre','section','details','figcaption','li'}
class P(HTMLParser):
    def __init__(s,name):
        super().__init__(convert_charrefs=True); s.st=[]; s.name=name; s.err=[]
    def handle_starttag(s,t,at):
        if t in VOID: return
        if 'p' in s.st and t in PCLOSE: s.err.append(f'{t} opened inside p at {s.getpos()}')
        if t=='li' and (not s.st or s.st[-1] not in('ul','ol')): s.err.append(f'li outside list {s.getpos()} stack {s.st[-3:]}')
        if s.st and s.st[-1] in ('ul','ol') and t!='li': s.err.append(f'{t} direct child of list {s.getpos()}')
        if s.st and s.st[-1] in('table',) and t not in('tr','thead','tbody','caption','colgroup'): s.err.append(f'{t} in table')
        if s.st and s.st[-1]=='tr' and t not in('td','th'): s.err.append(f'{t} in tr')
        s.st.append(t)
    def handle_endtag(s,t):
        if t in VOID: return
        if not s.st or s.st[-1]!=t: s.err.append(f'close {t} but stack {s.st[-4:]} at {s.getpos()}'); 
        if t in s.st:
            while s.st.pop()!=t: pass
for n in (49,232,233,253,356,440,442):
    p=P(n); p.feed(a[n-1]); p.close()
    print(n,'unclosed:',p.st,'errors:',p.err)
# whole-file
p=P('all'); p.feed(src); p.close(); print('ALL unclosed',p.st,'nerr',len(p.err)); print(p.err[:20])
ids=re.findall(r'\bid="([^"]+)"',src); c=collections.Counter(ids); print('dup ids',[k for k,v in c.items() if v>1]); print('homeex',c['homeex'],'proxymap',c['proxymap'])
for n in (230,231,234,235,251,252,254,439,441,48,50):
    print(n, a[n-1][:160], '...', a[n-1][-80:])
# stray & < in text
for n in (49,232,233,253,356,440,442):
    t=a[n-1]
    print(n,'bare &:',re.findall(r'&(?![a-z]+;|#\d+;).{0,20}',t)[:5], 'nonascii:',sorted(set(ch for ch in t if ord(ch)>127)))
