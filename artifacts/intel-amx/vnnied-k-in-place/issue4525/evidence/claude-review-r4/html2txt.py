import sys, re
from bs4 import BeautifulSoup, NavigableString, Tag
html = open(sys.argv[1], encoding='utf-8').read()
soup = BeautifulSoup(html, 'html.parser')
for t in soup(['script','style']): t.decompose()
out = []
def walk(node, depth=0):
    for ch in node.children:
        if isinstance(ch, NavigableString):
            s = re.sub(r'\s+', ' ', str(ch))
            if s.strip(): out.append(s)
        elif isinstance(ch, Tag):
            n = ch.name
            if n in ('h1','h2','h3','h4'):
                out.append('\n\n' + '#'*int(n[1]) + ' ' + ch.get_text(' ', strip=True) + (' {#%s}' % ch.get('id') if ch.get('id') else '') + '\n')
            elif n == 'tr':
                cells = [c.get_text(' ', strip=True) for c in ch.find_all(['td','th'], recursive=False)]
                out.append('\n| ' + ' | '.join(cells) + ' |')
            elif n == 'li':
                out.append('\n- '); walk(ch, depth+1)
            elif n in ('p','div','section','ul','ol','table','pre','figure','figcaption','details','summary','blockquote','dt','dd','dl','header','footer','nav','main','article','aside','tbody','thead'):
                if ch.get('id'): out.append('\n[#%s]' % ch.get('id'))
                out.append('\n'); walk(ch, depth+1); out.append('\n')
            elif n == 'br': out.append('\n')
            elif n == 'a':
                href = ch.get('href','')
                txt = ch.get_text(' ', strip=True)
                if href and not href.startswith('#') : out.append('%s <%s>' % (txt, href))
                else: out.append(txt)
            elif n == 'svg':
                out.append('[SVG: ' + ' / '.join(t.get_text(' ', strip=True) for t in ch.find_all('text')) + ']')
            else:
                walk(ch, depth+1)
walk(soup.body or soup)
text = ''.join(out)
text = re.sub(r'\n{3,}', '\n\n', text)
print(text)
