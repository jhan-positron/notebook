import sys,re
from html.parser import HTMLParser
VOID={'area','base','br','col','embed','hr','img','input','link','meta','source','track','wbr'}
SVGVOIDOK=True
class P(HTMLParser):
    def __init__(s):
        super().__init__(convert_charrefs=False)
        s.stack=[];s.errs=[];s.ids={};s.hrefs=[];s.in_script=False
    def handle_starttag(s,tag,attrs):
        line,col=s.getpos()
        d=dict(attrs)
        if 'id' in d:
            s.ids.setdefault(d['id'],[]).append(line)
        if tag=='a' and 'href' in d: s.hrefs.append((d['href'],line))
        # p cannot contain block elements
        if tag in ('pre','ul','ol','table','div','h1','h2','h3','h4','p','figure','dl','nav') and any(t=='p' for t,_ in s.stack):
            s.errs.append((line,col,'<%s> opened while <p> is open (opened at line %d)'%(tag,[l for t,l in s.stack if t=='p'][-1])))
        if tag in VOID: return
        s.stack.append((tag,line))
    def handle_startendtag(s,tag,attrs):
        line,col=s.getpos()
        d=dict(attrs)
        if 'id' in d: s.ids.setdefault(d['id'],[]).append(line)
    def handle_endtag(s,tag):
        line,col=s.getpos()
        if tag in VOID: return
        if not s.stack:
            s.errs.append((line,col,'</%s> with empty stack'%tag)); return
        if s.stack[-1][0]==tag:
            s.stack.pop(); return
        # mismatch
        names=[t for t,_ in s.stack]
        if tag in names:
            # pop until
            while s.stack and s.stack[-1][0]!=tag:
                t,l=s.stack.pop()
                s.errs.append((line,col,'</%s> closes while <%s> (line %d) still open'%(tag,t,l)))
            s.stack.pop()
        else:
            s.errs.append((line,col,'</%s> has no matching open tag (top of stack <%s> line %d)'%(tag,s.stack[-1][0],s.stack[-1][1])))
for path in sys.argv[1:]:
    t=open(path,encoding='utf-8').read()
    p=P(); p.feed(t); p.close()
    print('==',path)
    print('  errors:',len(p.errs))
    for e in p.errs[:40]: print('   ',e)
    print('  unclosed at end:',p.stack)
    dup={k:v for k,v in p.ids.items() if len(v)>1}
    print('  duplicate ids:',dup)
    missing=[(h,l) for h,l in p.hrefs if h.startswith('#') and h[1:] not in p.ids]
    print('  links to missing ids:',missing)
    print('  number of ids:',len(p.ids),'number of # links:',sum(1 for h,l in p.hrefs if h.startswith('#')))
