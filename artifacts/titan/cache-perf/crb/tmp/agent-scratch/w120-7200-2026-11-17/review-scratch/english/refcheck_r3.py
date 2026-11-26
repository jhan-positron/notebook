import re
s=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
i=s.find('>References<')
body, refs = s[:i], s[i:]
used_body=[int(x) for x in re.findall(r'\[Ref(\d+)\]',body)]
used=set(used_body)
# in the refs section: intro paragraph cites refs too; list entries are <li ... id="refN">
ids=[int(x) for x in re.findall(r'id="ref(\d+)"',s)]
print('ids count',len(ids),'min',min(ids),'max',max(ids),'dups',[x for x in set(ids) if ids.count(x)>1])
print('missing ids', sorted(set(range(1,max(ids)+1))-set(ids)))
# refs intro paragraph
txt=open('body-r3.txt').read()
k=txt.find('## References')
intro=txt[k:].split('\n')[1]
intro_used=set(int(x) for x in re.findall(r'\[Ref(\d+)\]',intro))
print('intro uses',sorted(intro_used))
allused=used|intro_used
print('used not listed', sorted(allused-set(ids)))
print('listed not used anywhere', sorted(set(ids)-allused))
print('listed, used only in refs intro', sorted(intro_used-used))
hrefs=set(int(x) for x in re.findall(r'href="#ref(\d+)"',s))
print('href without id', sorted(hrefs-set(ids)))
order=[]
for x in used_body:
    if x not in order: order.append(x)
print('first-use order', order)
print('monotone first use:', order==sorted(order))
svgs=re.findall(r'<svg.*?</svg>',s,flags=re.S)
print('refs in svg', sum(len(re.findall(r'\[Ref',x)) for x in svgs))
for ln in txt[:k].split('\n'):
    for cell in ln.split(' | '):
        c=cell.strip()
        if re.fullmatch(r'-?\s*(\[Ref\d+\])+\.?',c): print('STANDALONE',c)
        if re.search(r'\b(See|see)\b',c): print('SEE:',c[:160])
# refs placed before the period or after?
for m in re.finditer(r'[^.\n]{0,60}(\[Ref\d+\])+[^\n]{0,20}', txt[:k]):
    pass
# cases where [Ref] is not directly preceded by a sentence end (i.e. mid-sentence citations)
mid=0
for m in re.finditer(r'(.{0,50})((?:\[Ref\d+\])+)(.{0,25})', txt[:k]):
    pre,refs_,post=m.groups()
    if not re.search(r'[A-Za-z0-9\)"%]\s$', pre):
        print('ODD PRE:',repr(pre[-30:]),refs_,repr(post[:15]))
    if post and not re.match(r'^(\.|\s*$|\s*\||\n)', post):
        mid+=1
        print('MID:',repr(pre[-40:]),refs_,repr(post[:25]))
print('mid count',mid)
