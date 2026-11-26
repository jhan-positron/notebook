import sys
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc'
F={'now':'/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html','ren':S+'/report.after-rename.before-fixes.html','rev':'/home/jhan/workspace/titan/cache-perf/crb/tmp/crb-memory-hierarchy.before-slc-rename.html'}
which=sys.argv[1].split(',')
for n in sys.argv[2:]:
    if '-' in n:
        a,b=n.split('-'); rng=range(int(a),int(b)+1)
    else: rng=[int(n)]
    for i in rng:
        for w in which:
            L=open(F[w],encoding='utf-8').read().split('\n')
            print('--- %s L%d ---'%(w,i)); print(L[i-1])
