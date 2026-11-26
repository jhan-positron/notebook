import re,html
b=open('worker/report.before-worker.html').read().split('\n')
a=open('worker/applied.html').read().split('\n')
def st(t): return re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>',' ',t)))
for n in [232,233,253,440,442,779]:
    print('=== BEFORE',n); print(st(b[n-1]))
    nb=set(re.findall(r'\d[\d,.]*',st(b[n-1]))); na=set(re.findall(r'\d[\d,.]*',st(a[n-1])))
    print('NEW NUMS',sorted(na-nb))
for n in range(770,779): print(n,a[n-1][:1500])
