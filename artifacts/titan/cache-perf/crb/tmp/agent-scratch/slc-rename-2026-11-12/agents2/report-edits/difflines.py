import sys,difflib
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc'
now=open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html',encoding='utf-8').read().split('\n')
ren=open(S+'/report.after-rename.before-fixes.html',encoding='utf-8').read().split('\n')
want=[int(x) for x in sys.argv[1:]]
for n in want:
    a=ren[n-1]; b=now[n-1]
    print('=== LINE',n,'len old',len(a),'len new',len(b))
    sm=difflib.SequenceMatcher(None,a,b,autojunk=False)
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal': continue
        ctxa=a[max(0,i1-60):i1]; ctxb=a[i2:i2+60]
        print('  [%s] ...%s' % (tag, ctxa))
        print('     OLD: {%s}' % a[i1:i2])
        print('     NEW: {%s}' % b[j1:j2])
        print('     ...%s' % ctxb)
