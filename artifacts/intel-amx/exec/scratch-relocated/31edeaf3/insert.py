import sys, re, html.parser
page_path, frag_path, out_path = sys.argv[1:4]
page = open(page_path, encoding='utf-8').read()
frag = open(frag_path, encoding='utf-8').read()
anchor = '<h2>3. Corrections this Q&amp;A implies for attn-stats-compare.md</h2>'
assert page.count(anchor) == 1, page.count(anchor)
assert '<h2>3. Under FPGA attention' not in page, 'already inserted'
new = page.replace(anchor, frag.rstrip() + '\n\n' + anchor.replace('<h2>3.', '<h2>4.'))
# the footer cite line lists the cited code files; add the new ones
old_cite = 'Code cited at tron origin/main dd0f942c75 (self_attention.hpp, amx_attn_iface.hpp, gof.hpp, shard.hpp).'
assert new.count(old_cite) == 1
new = new.replace(old_cite, 'Code cited at tron origin/main dd0f942c75 (self_attention.hpp, amx_attn_iface.hpp, gof.hpp, shard.hpp, scheduler/full.hpp, pos/config.hpp, libtron.hpp).')
bad = [(i, c) for i, c in enumerate(new) if ord(c) > 126]
assert not bad, bad[:5]
# tag balance check for the inserted fragment
class P(html.parser.HTMLParser):
    def __init__(s): super().__init__(); s.stack=[]; s.err=[]
    def handle_starttag(s,t,a):
        if t not in ('br','img','meta','link','rect','line','text','input'): s.stack.append(t)
    def handle_endtag(s,t):
        if s.stack and s.stack[-1]==t: s.stack.pop()
        else: s.err.append((t, list(s.stack[-3:]), s.getpos()))
p = P(); p.feed(frag); assert not p.err and not p.stack, (p.err, p.stack)
open(out_path, 'w', encoding='utf-8').write(new)
print('ok', len(page), '->', len(new), 'bytes; headings:'); print('\n'.join(re.findall(r'<h2>[^<]*</h2>', new)))
