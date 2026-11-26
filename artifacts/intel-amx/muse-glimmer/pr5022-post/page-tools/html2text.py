import sys, re, html
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.pre = 0
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ('style', 'script'):
            self.skip += 1
        elif tag in ('h1','h2','h3','h4','h5'):
            self.out.append('\n\n' + '#' * int(tag[1]) + ' ')
        elif tag in ('p','div','section','details','table','ul','ol','blockquote'):
            self.out.append('\n')
            if a.get('id'): self.out.append('[id=%s] ' % a['id'])
            if a.get('class'): self.out.append('{%s} ' % a['class'])
        elif tag == 'summary':
            self.out.append('\n[summary] ')
        elif tag == 'li':
            self.out.append('\n- ')
        elif tag == 'tr':
            self.out.append('\n| ')
        elif tag in ('td','th'):
            self.out.append(' | ')
        elif tag == 'br':
            self.out.append('\n')
        elif tag == 'pre':
            self.pre += 1
            self.out.append('\n```\n')
        elif tag == 'code' and not self.pre:
            self.out.append('`')
        elif tag == 'a':
            self.href = a.get('href')
    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip -= 1
        elif tag == 'pre':
            self.pre -= 1
            self.out.append('\n```\n')
        elif tag == 'code' and not self.pre:
            self.out.append('`')
        elif tag == 'a':
            h = getattr(self, 'href', None)
            if h and not h.startswith('#'):
                self.out.append(' <%s>' % h)
            elif h:
                self.out.append(' <%s>' % h)
        elif tag in ('p','div','section','details','table','ul','ol','h1','h2','h3','h4','blockquote'):
            self.out.append('\n')
    def handle_data(self, data):
        if self.skip: return
        if self.pre:
            self.out.append(data)
        else:
            self.out.append(re.sub(r'\s+', ' ', data))

p = P()
p.feed(open(sys.argv[1], encoding='utf-8').read())
t = ''.join(p.out)
t = re.sub(r'\n[ \t]+\n', '\n\n', t)
t = re.sub(r'\n{3,}', '\n\n', t)
open(sys.argv[2], 'w', encoding='utf-8').write(t)
print(len(t), t.count('\n'))
