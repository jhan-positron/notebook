import re
s=open('/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html',encoding='utf-8').read()
i=s.find('>References<')
body, refs = s[:i], s[i:]
used=set(int(x) for x in re.findall(r'\[Ref(\d+)\]',body))
listed=[int(x) for x in re.findall(r'\[Ref(\d+)\]',refs)]
print('used in body',sorted(used))
print('listed',listed)
print('used not listed', sorted(used-set(listed)))
print('listed not used', sorted(set(listed)-used))
print('dup listed',[x for x in set(listed) if listed.count(x)>1])
# anchors
ids=set(re.findall(r'id="ref(\d+)"',s))
hrefs=set(re.findall(r'href="#ref(\d+)"',s))
print('href without id', sorted(hrefs-ids), 'ids', len(ids))
# first-use order in body
order=[]
for x in re.findall(r'\[Ref(\d+)\]',body):
    x=int(x)
    if x not in order: order.append(x)
print('first-use order', order)
# Refs in svg titles?
svgs=re.findall(r'<svg.*?</svg>',s,flags=re.S)
print('refs in svg', sum(len(re.findall(r'\[Ref',x)) for x in svgs))
# refs standing alone: a [Ref] preceded by nothing in its block
txt=open('body.txt').read()
for ln in txt.split('\n'):
    for cell in ln.split(' | '):
        c=cell.strip()
        if re.fullmatch(r'(\[Ref\d+\])+\.?',c): print('STANDALONE',c)
        if re.match(r'^-?\s*(See|see)\b',c): print('SEE:',c[:100])
