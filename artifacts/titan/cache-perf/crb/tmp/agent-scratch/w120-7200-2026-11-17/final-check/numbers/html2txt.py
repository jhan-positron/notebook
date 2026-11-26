#!/usr/bin/env python3
"""Dump the report as text, with markers for structure. Own code, no generator import."""
import sys, re, html
from html.parser import HTMLParser

class P(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip = 0
        self.stack = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.stack.append(tag)
        if tag in ('style', 'script'):
            self.skip += 1
        if tag in ('p', 'li', 'tr', 'h1', 'h2', 'h3', 'h4', 'div', 'details', 'summary', 'table', 'figure', 'figcaption', 'svg', 'section', 'caption', 'ul', 'ol', 'br'):
            self.out.append('\n')
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.out.append('#' * int(tag[1]) + ' ')
        if tag == 'li':
            self.out.append('- ')
        if tag in ('td', 'th'):
            self.out.append(' | ')
        if tag == 'details':
            self.out.append('[DETAILS%s] ' % (' open' if 'open' in a else ''))
        if tag == 'summary':
            self.out.append('[SUMMARY] ')
        if tag == 'svg':
            self.out.append('[SVG %s] ' % ' '.join('%s=%s' % kv for kv in attrs if kv[0] in ('viewBox', 'width', 'height', 'id', 'aria-label', 'role')))
        if tag == 'title' and 'svg' in self.stack:
            self.out.append('\n  <title> ')
        if tag == 'text' and 'svg' in self.stack:
            self.out.append('\n  <text x=%s y=%s> ' % (a.get('x'), a.get('y')))
        if tag in ('circle',):
            self.out.append('\n  <circle cx=%s cy=%s r=%s class=%s fill=%s> ' % (a.get('cx'), a.get('cy'), a.get('r'), a.get('class'), a.get('fill')))
        if tag in ('line',):
            self.out.append('\n  <line x1=%s y1=%s x2=%s y2=%s class=%s> ' % (a.get('x1'), a.get('y1'), a.get('x2'), a.get('y2'), a.get('class')))
        if tag in ('rect',):
            self.out.append('\n  <rect x=%s y=%s w=%s h=%s class=%s> ' % (a.get('x'), a.get('y'), a.get('width'), a.get('height'), a.get('class')))
        if tag in ('path', 'polygon', 'polyline'):
            self.out.append('\n  <%s d=%s points=%s class=%s> ' % (tag, a.get('d'), a.get('points'), a.get('class')))
        if tag == 'a':
            self.out.append('[A href=%s]' % a.get('href'))
        if 'id' in a and tag not in ('svg',):
            self.out.append('{#%s}' % a['id'])
    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip -= 1
        while self.stack and self.stack[-1] != tag:
            self.stack.pop()
        if self.stack:
            self.stack.pop()
        if tag == 'a':
            self.out.append('[/A]')
        if tag in ('details',):
            self.out.append('\n[/DETAILS]\n')
        if tag == 'svg':
            self.out.append('\n[/SVG]\n')
    def handle_data(self, d):
        if self.skip:
            return
        self.out.append(re.sub(r'\s+', ' ', d))

p = P()
p.feed(open(sys.argv[1]).read())
t = ''.join(p.out)
t = re.sub(r'\n[ \t]*\n+', '\n', t)
sys.stdout.write(t)
