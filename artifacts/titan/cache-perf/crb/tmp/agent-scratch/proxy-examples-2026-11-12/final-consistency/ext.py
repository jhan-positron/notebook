import re,sys,html
W='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/'
a=open(W+'applied.html').read().split('\n')
b=open(W+'report.before-worker.html').read().split('\n')
def st(s): return html.unescape(re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',s))).strip()
diff=[i+1 for i in range(max(len(a),len(b))) if (a[i] if i<len(a) else None)!=(b[i] if i<len(b) else None)]
print(len(a),len(b),diff)
open('after.txt','w').write('\n'.join(f'{i+1}: {st(l)}' for i,l in enumerate(a) if st(l)))
open('before.txt','w').write('\n'.join(f'{i+1}: {st(l)}' for i,l in enumerate(b) if st(l)))
for n in [49,232,233,253,356,440,442]:
    print('=====',n,'AFTER'); print(st(a[n-1])); 
