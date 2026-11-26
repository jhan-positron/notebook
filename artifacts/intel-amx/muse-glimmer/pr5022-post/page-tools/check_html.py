#!/usr/bin/env python3
"""Structure check of an HTML page: tag balance, duplicate ids, local anchors."""
import sys, re, collections
from html.parser import HTMLParser
VOID = {'meta','br','hr','img','input','link','source','wbr','col','area','base','embed','param','track'}
class C(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]; self.err=[]; self.ids=collections.Counter(); self.hrefs=[]; self.n=collections.Counter()
    def handle_starttag(self, tag, attrs):
        self.n[tag]+=1
        d=dict(attrs)
        if 'id' in d: self.ids[d['id']]+=1
        if tag=='a' and d.get('href','').startswith('#'): self.hrefs.append((d['href'][1:], self.getpos()[0]))
        if tag not in VOID: self.stack.append((tag,self.getpos()[0]))
    def handle_startendtag(self, tag, attrs):
        d=dict(attrs)
        if 'id' in d: self.ids[d['id']]+=1
    def handle_endtag(self, tag):
        if tag in VOID: return
        if not self.stack: self.err.append(f'line {self.getpos()[0]}: </{tag}> with empty stack'); return
        # li/p may be implicitly closed; everything else must match exactly
        if self.stack[-1][0]==tag: self.stack.pop(); return
        self.err.append(f'line {self.getpos()[0]}: </{tag}> closes <{self.stack[-1][0]}> opened at line {self.stack[-1][1]}')
        for i in range(len(self.stack)-1,-1,-1):
            if self.stack[i][0]==tag: del self.stack[i:]; break
p=sys.argv[1]; s=open(p,encoding='utf-8').read()
c=C(); c.feed(s); c.close()
dup=[k for k,v in c.ids.items() if v>1]
missing=sorted({(h,l) for h,l in c.hrefs if h not in c.ids})
print('bytes',len(s.encode()),'lines',s.count('\n')+1,'tags',sum(c.n.values()),'ids',len(c.ids),'local hrefs',len(c.hrefs))
print('unclosed at end:',[t for t in c.stack])
print('mismatches:',c.err[:10])
print('duplicate ids:',dup)
print('unresolved hrefs:',missing[:10])
# reference marks: every [R#] mark links to an existing id and shows the same number
bad=[m.group(0) for m in re.finditer(r'<a class="ref" href="#R(\d+)">\[R(\d+)\]</a>',s) if m.group(1)!=m.group(2)]
print('ref marks with mismatching number:',bad[:5])
print('ref ids in order:',[int(x) for x in re.findall(r'<li id="R(\d+)">',s)]==list(range(1,len(re.findall(r'<li id="R(\d+)">',s))+1)), len(re.findall(r'<li id="R(\d+)">',s)))
uncited=[n for n in range(1,len(re.findall(r'<li id="R(\d+)">',s))+1) if f'href="#R{n}"' not in s]
print('uncited refs:',uncited)
ok = not c.stack and not c.err and not dup and not missing and not bad
print('STRUCTURE OK' if ok else 'STRUCTURE PROBLEMS'); sys.exit(0 if ok else 1)
