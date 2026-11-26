import re
t=open('../worker/draft-full.html').read()
ids=set(re.findall(r'\bid="([^"]+)"',t))
hrefs=re.findall(r'href="#([^"]+)"[^>]*>(.*?)</a>',t)
print('hrefs',len(hrefs),'missing',[h for h in hrefs if h[0] not in ids])
heads={re.sub(r'<[^>]+>','',b).strip():a for a,b in re.findall(r'<h[23][^>]*id="([^"]+)"[^>]*>(.*?)</h[23]>',t)}
for a,txt in hrefs:
    txt=re.sub(r'<[^>]+>','',txt).strip()
    if txt not in heads or heads[txt]!=a: print('TOC text != heading:',a,'|',txt)
# section names quoted in text: section "X"
import html
plain=html.unescape(re.sub(r'<[^>]+>','',t))
for m in set(re.findall(r'section "([^"]+)"',plain))|set(re.findall(r'See "([^"]+)"',plain)):
    ok=any(h.startswith(m) or m in h for h in map(html.unescape,heads))
    if not ok: print('section ref without heading:',m)
dup=[i for i in ids if len(re.findall(r'\bid="%s"'%re.escape(i),t))>1]; print('dup ids',dup)
for i in ('homeex','proxymap','dist','lat'): print(i,len(re.findall(r'id="%s"'%i,t)),len(re.findall(r"getElementById\('%s'\)"%i,t)))
