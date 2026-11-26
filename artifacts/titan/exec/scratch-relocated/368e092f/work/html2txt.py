import sys, html.parser, re
class P(html.parser.HTMLParser):
    def __init__(s):
        super().__init__(); s.out=[]; s.skip=0; s.pre=0
    def handle_starttag(s,t,a):
        if t in('script','style'): s.skip+=1
        if t=='pre': s.pre+=1; s.out.append('\n```\n')
        if t in('h1','h2','h3','h4'): s.out.append('\n\n'+'#'*int(t[1])+' ')
        if t in('p','div','tr','br','ul','ol','table','section'): s.out.append('\n')
        if t=='li': s.out.append('\n- ')
        if t in('td','th'): s.out.append(' | ')
    def handle_endtag(s,t):
        if t in('script','style'): s.skip-=1
        if t=='pre': s.pre-=1; s.out.append('\n```\n')
    def handle_data(s,d):
        if s.skip: return
        s.out.append(d if s.pre else re.sub(r'\s+',' ',d))
p=P(); p.feed(open(sys.argv[1],encoding='utf-8').read())
t=''.join(p.out); t=re.sub(r'\n[ \t]+\n','\n\n',t); t=re.sub(r'\n{3,}','\n\n',t)
open(sys.argv[2],'w',encoding='utf-8').write(t)
