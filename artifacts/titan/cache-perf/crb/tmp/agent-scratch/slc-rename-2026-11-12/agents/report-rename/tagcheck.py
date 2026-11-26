import re, collections
pa = '/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html'
pb = '/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html'
A = open(pa, encoding='utf-8').read(); B = open(pb, encoding='utf-8').read()
print("bytes", len(A.encode()), len(B.encode()), "| newline count", A.count('\n'), B.count('\n'), "| ends with newline", A.endswith('\n'), B.endswith('\n'), "| CR", A.count('\r'), B.count('\r'))
def body_only(s):
    # the part outside the <script> and <style> blocks
    return re.sub(r'<(script|style)>.*?</\1>', lambda m: '<%s></%s>' % (m.group(1), m.group(1)), s, flags=re.S)
tag = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9]*)((?:\s+[^<>]*?)?)\s*(/?)>')
def tags(s):
    return [(m.group(1) + m.group(2), m.group(3).strip()) for m in tag.finditer(body_only(s))]
ta, tb = tags(A), tags(B)
print("tags outside script/style:", len(ta), len(tb))
print("tag name sequence identical:", [t[0] for t in ta] == [t[0] for t in tb])
print("tag sequence with attributes identical:", ta == tb)
dif = [(x, y) for x, y in zip(ta, tb) if x != y]
for x, y in dif: print("  ATTR DIFF", x, "->", y)
ca = collections.Counter(t[0] for t in ta); cb = collections.Counter(t[0] for t in tb)
print("tag count diff:", {k: (ca[k], cb[k]) for k in set(ca) | set(cb) if ca[k] != cb[k]})
# balance check on the after file
void = {'meta', 'link', 'br', 'img', 'hr', 'input', 'line', 'rect', 'circle', 'path'}
stack = []; problems = []
for m in tag.finditer(body_only(B)):
    close, name, attrs, selfc = m.group(1), m.group(2), m.group(3), m.group(4)
    line = B.count('\n', 0, m.start()) + 1
    if selfc or name in void: continue
    if not close: stack.append((name, line))
    else:
        if stack and stack[-1][0] == name: stack.pop()
        else: problems.append((name, line, stack[-1] if stack else None))
print("unbalanced after:", problems[:10], "left open:", stack[:10])
# stray angle brackets or entities in changed text
for ch in ['&lt;', '&gt;', '&amp;', '&quot;', '&nbsp;']:
    print(ch, A.count(ch), B.count(ch))
print('raw < count', A.count('<'), B.count('<'), ' raw > count', A.count('>'), B.count('>'), ' double-quote count', A.count('"'), B.count('"'))
# attribute values changed?
attr = re.compile(r'\b([a-zA-Z-]+)="([^"]*)"')
aa = [m.groups() for m in attr.finditer(body_only(A))]; ab = [m.groups() for m in attr.finditer(body_only(B))]
print("attribute pairs outside scripts:", len(aa), len(ab))
for x, y in zip(aa, ab):
    if x != y: print("  attr changed:", x, "->", y)
