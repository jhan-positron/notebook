import re,sys
D='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/'
b=open(D+'report.before-worker.html').read().split('\n')
a=open(D+'applied.html').read().split('\n')
print(len(a),len(b))
diff=[i+1 for i in range(min(len(a),len(b))) if a[i]!=b[i]]
print(diff)
for n in diff:
    open(f'a{n}.txt','w').write(a[n-1]); open(f'b{n}.txt','w').write(b[n-1])
    print(n,len(b[n-1]),len(a[n-1]))
