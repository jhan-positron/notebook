#!/usr/bin/env python3
# Strip the report page to reading text. SVG text kept and marked; <title> tooltips dropped unless --titles.
import sys, re, html
from html.parser import HTMLParser
src = open(sys.argv[1], encoding='utf-8').read()
show_titles = '--titles' in sys.argv
class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out=[]; self.stack=[]; self.skip=0
    def handle_starttag(self, tag, attrs):
        self.stack.append(tag)
        if tag in ('style','script'): self.skip+=1
        if tag=='title' and 'svg' in self.stack and not show_titles: self.skip+=1
        if tag in ('p','li','h1','h2','h3','tr','div','figcaption','details','summary','svg','br','table','dt','dd','ul','ol'):
            self.out.append('\n')
        if tag=='svg': self.out.append('[SVG]\n')
        if tag in ('td','th'): self.out.append(' | ')
        if tag=='text': self.out.append('\n  <t> ')
        if tag=='h2': self.out.append('## ')
        if tag=='h3': self.out.append('### ')
        if tag=='h1': self.out.append('# ')
        if tag=='li': self.out.append('- ')
        if tag=='title' and 'svg' in self.stack and show_titles: self.out.append('\n   {tip} ')
    def handle_endtag(self, tag):
        if tag in ('style','script'): self.skip-=1
        if tag=='title' and 'svg' in self.stack[:-1] and not show_titles: self.skip-=1
        if tag=='svg': self.out.append('\n[/SVG]\n')
        while self.stack and self.stack[-1]!=tag: self.stack.pop()
        if self.stack: self.stack.pop()
    def handle_data(self, d):
        if self.skip: return
        self.out.append(d)
p=P(); p.feed(src)
t=''.join(p.out)
t=re.sub(r'[ \t]+',' ',t); t=re.sub(r'\n\s*\n+','\n',t)
print(t)
