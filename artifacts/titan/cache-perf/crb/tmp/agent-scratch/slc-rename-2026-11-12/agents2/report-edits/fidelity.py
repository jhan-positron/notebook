import re,html,difflib,json
S='/tmp/claude-0/-home-jhan-workspace-titan-cache-perf-crb/6eb09a16-5942-4cc5-8ed0-249c7d5ab696/scratchpad/rename_slc'
now=open('/home/jhan/workspace/titan/cache-perf/crb/crb-memory-hierarchy.html',encoding='utf-8').read().split('\n')
ren=open(S+'/report.after-rename.before-fixes.html',encoding='utf-8').read().split('\n')
def strip(t, drop_pre=False):
    if drop_pre:
        t=re.sub(r'<pre>.*?</pre>',' [[LISTING]] ',t,flags=re.S)
    # block boundaries -> sentence breaks
    t=re.sub(r'</(p|li|h3|td|th|tr|ul|table|div)>',' ¶ ',t)
    t=re.sub(r'<[^>]+>','',t)
    t=html.unescape(t)
    return re.sub(r'[ \t]+',' ',t).strip()
def sents(t):
    # split on sentence end followed by space+capital / bracket / ¶
    parts=[]
    for blk in t.split('¶'):
        blk=blk.strip()
        if not blk: continue
        # protect brackets
        out=[];cur='';depth=0
        i=0
        while i<len(blk):
            c=blk[i]
            cur+=c
            if c=='[': depth+=1
            if c==']': depth=max(0,depth-1)
            if c in '.:' and depth==0 and c=='.':
                nxt=blk[i+1:i+3]
                if nxt[:1]==' ' and (nxt[1:2].isupper() or nxt[1:2] in '[("'):
                    # attach a following citation bracket
                    rest=blk[i+1:].lstrip()
                    if rest.startswith('['):
                        j=blk.index(']',i)+1
                        cur+=blk[i+1:j]
                        i=j-1
                        # consume trailing period
                        if blk[i+1:i+2]=='.':
                            cur+='.'; i+=1
                    out.append(cur.strip()); cur=''
            i+=1
        if cur.strip(): out.append(cur.strip())
        parts+=out
    return parts
old=' '.join(strip(ren[i]) for i in (130,131,132))
new=' '.join(strip(now[i],drop_pre=True) for i in (130,131,132))
so=sents(old); sn=sents(new)
json.dump({'old':so,'new':sn},open(S+'/agents2/report-edits/sents.json','w'),ensure_ascii=False,indent=1)
print('OLD sentences',len(so),'NEW sentences',len(sn))
used=set()
for k,s in enumerate(so):
    best=max(range(len(sn)),key=lambda j:difflib.SequenceMatcher(None,s,sn[j],autojunk=False).ratio())
    r=difflib.SequenceMatcher(None,s,sn[best],autojunk=False).ratio()
    used.add(best)
    flag='EXACT' if s==sn[best] else ('~%.2f'%r)
    print('O%02d %s -> N%02d'%(k,flag,best))
    print('   OLD:',s)
    if s!=sn[best]: print('   NEW:',sn[best])
print()
print('NEW sentences with no old sentence mapped to them:')
for j,s in enumerate(sn):
    if j not in used: print('N%02d: %s'%(j,s))
