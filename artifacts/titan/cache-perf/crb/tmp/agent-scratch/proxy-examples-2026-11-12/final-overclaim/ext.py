import re,sys,html
b=open('worker/report.before-worker.html').read().split('\n')
a=open('worker/applied.html').read().split('\n')
def strip(s):
    s=re.sub(r'<[^>]+>',' ',s); s=html.unescape(s); return re.sub(r'\s+',' ',s).strip()
for n in [int(x) for x in sys.argv[1:]]:
    print('=====',n,'BEFORE'); print(strip(b[n-1]))
    print('=====',n,'AFTER'); print(strip(a[n-1]))
