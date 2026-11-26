import re,sys,html
b=open('worker/report.before-worker.html').read().split('\n')
a=open('worker/applied.html').read().split('\n')
for n in [int(x) for x in sys.argv[1:]]:
    t=a[n-1]
    if n!=780: t=html.unescape(re.sub(r'<[^>]+>',' ',t)); t=re.sub(r'\s+',' ',t)
    print('=== AFTER',n,len(t)); print(t)
