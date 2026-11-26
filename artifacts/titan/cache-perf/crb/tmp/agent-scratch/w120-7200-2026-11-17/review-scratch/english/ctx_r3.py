import re,sys
b=open('body-r3.txt').read()
words=sys.argv[1:]
for w in words:
    ms=list(re.finditer(re.escape(w),b,flags=re.I))
    print(f'== {w}: {len(ms)}')
    for m in ms[:12]:
        ln=b.count('\n',0,m.start())+1
        print(f'   L{ln}: ...{b[max(0,m.start()-80):m.end()+80]!r}')
