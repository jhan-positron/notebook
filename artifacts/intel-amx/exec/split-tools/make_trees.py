#!/usr/bin/env python3
"""Build the pure-subtraction file sets PR1, PR2, PR0 from R (rebased full tree).
No prose rewording here: only region deletion / restoration by concern.
Outputs $SP/sub/{pr1,pr2,pr0}/<path> and prints a report."""
import csv,re,subprocess,collections,os,sys,shutil
SP='/tmp/claude-0/-home-jhan-workspace-intel-AMX/b6bd7e59-21e7-40cc-a2fb-e5a442318192/scratchpad'
REPO=os.path.expanduser('~/workspace/ai-runs/tron-split'); HEAD='jhan-amx-p0'; R='e449b11452'; MAIN='origin/main'
CSV=os.path.join(os.path.dirname(os.path.abspath(__file__)),"concern-map-hunks.csv")
def git(*a): return subprocess.run(['git','-C',REPO,*a],capture_output=True,text=True)
def lines(rev,f):
    p=git('show',f'{rev}:{f}'); return p.stdout.split('\n') if p.returncode==0 else None
rows=list(csv.DictReader(open(CSV)))
def regions(f,concern_re,exclude=()):
    out=[]
    for r in rows:
        if r['file']!=f or not re.search(concern_re,r['concern']): continue
        lo,hi=(r['region'].split('-')+[None])[:2]; lo=int(lo); hi=int(hi) if hi else lo
        if (lo,hi) in exclude: continue
        out.append((lo,hi,r['concern']))
    return sorted(out)
def delete_regions(cur,hl,regs,label):
    """order-aware text match, delete; returns new list. Fails loudly on a miss."""
    cursor=0; found=[]
    for lo,hi,c in sorted(regs):
        block=hl[lo-1:hi]; n=len(block)
        hits=[i for i in range(cursor,len(cur)-n+1) if cur[i:i+n]==block]
        if not hits: raise SystemExit(f'MISSING {label}:{lo}-{hi} {block[0][:60]!r}')
        i=hits[0]; found.append((i,n)); cursor=i+n
    for i,n in sorted(found,reverse=True): del cur[i:i+n]
    return cur
def replace_block(cur,old,new,label,count=1):
    s='\n'.join(cur); 
    if s.count(old)!=count: raise SystemExit(f'ANCHOR {label}: found {s.count(old)} of {old[:50]!r}')
    return s.replace(old,new).split('\n')
def write(tree,f,content_lines):
    p=f'{SP}/sub/{tree}/{f}'; os.makedirs(os.path.dirname(p),exist_ok=True)
    open(p,'w').write('\n'.join(content_lines))
for t in ('pr1','pr2','pr0'): shutil.rmtree(f'{SP}/sub/{t}',ignore_errors=True)
ALL=git('diff','--name-only',MAIN,R).stdout.split()
report=[]
# ---------------- PR1 ----------------
# self_attention.hpp: R minus counters + mirror-kernel
f='h/tron/models/self_attention.hpp'
cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,'counters|mirror-kernel'),f); write('pr1',f,cur)
# amx_attn_iface.hpp, amx_attn.cpp
for f,cre in (('h/tron/kernels/amx_attn_iface.hpp','mirror'),('src/tron/kernels/amx_attn.cpp','mirror')):
    cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,cre),f); write('pr1',f,cur)
# CMake
f='src/tron/CMakeLists.txt'; cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,'mirror'),f); write('pr1',f,cur)
f='t/CMakeLists.txt'; cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,'mirror')+[(189,195,'logit_ab-park')],f); write('pr1',f,cur)
# t_amx_numerics
f='t/t_amx_numerics.cpp'; cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,'mirror'),f); write('pr1',f,cur)
# t_amx_dispatch_dtype: 3-arg ctor
f='t/t_amx_dispatch_dtype.cpp'
cur=replace_block(lines(R,f),"  book_t cache(/*n_pages=*/1, /*storage_slot_count=*/n_layers,\n      /*support_eagle=*/false, /*amx_mirror_eligible=*/true);",
    "  book_t cache(\n      /*n_pages=*/1, /*storage_slot_count=*/n_layers, /*support_eagle=*/false);",f); write('pr1',f,cur)
# t_llama_unit: delete mirror-test regions except the ctor sites, which get main's lines back
f='t/t_llama_unit.cpp'; ctor_sites={(272,273),(536,539),(1220,1223)}
cur=delete_regions(lines(R,f),lines(HEAD,f),regions(f,'mirror',exclude=ctor_sites),f)
ml=lines(MAIN,f)
cur=replace_block(cur,"  book_t cache(/*n_pages=*/1, storage_slots, /*support_eagle=*/true,\n      /*amx_mirror_eligible=*/true);",ml[303],f+':304')
cur=replace_block(cur,"  cache_t destination(/*n_pages=*/2, cache_t::n_slots, /*support_eagle=*/false,\n      /*amx_mirror_eligible=*/true);\n  cache_t source(/*n_pages=*/2, cache_t::n_slots, /*support_eagle=*/false,\n      /*amx_mirror_eligible=*/true);",
    ml[422]+'\n'+ml[423],f+':423')
cur=replace_block(cur,"  cache_t destination(/*n_pages=*/2, storage_slots, /*support_eagle=*/true,\n      /*amx_mirror_eligible=*/true);\n  cache_t source(/*n_pages=*/1, storage_slots, /*support_eagle=*/true,\n      /*amx_mirror_eligible=*/true);",
    ml[1145]+'\n'+ml[1146],f+':1146')
write('pr1',f,cur)
# kv_cache.hpp: main + 5 hunks
f='h/tron/models/kv_cache.hpp'; cur=lines(MAIN,f); rl=lines(R,f)
cur=replace_block(cur,"  bool valid = true;\n};\n\ntemplate <size_t n_slots>\nconsteval kv_slot_offsets<n_slots> make_kv_slot_offsets(",
    "  bool valid = true;\n};\n\n// Planes per kv_block: K and V, each page_size x head_size bf16 values.\ninline constexpr size_t kv_block_planes = 2;\n\ntemplate <size_t n_slots>\nconsteval kv_slot_offsets<n_slots> make_kv_slot_offsets(",f+':planes')
cur=replace_block(cur,"        checked_multiply(2 * size_t{64} * sizeof(bf16), specs[slot].geometry.head_size,\n            block_bytes) &&",
    "        checked_multiply(kv_block_planes * size_t{64} * sizeof(bf16),\n            specs[slot].geometry.head_size, block_bytes) &&",f+':offsets')
cur=replace_block(cur,"        2 * page_size * geometry.head_size * sizeof(bf16);\n    static_assert(sizeof(kv_block_t) == expected_block_bytes);",
    "        detail::kv_block_planes * page_size * geometry.head_size * sizeof(bf16);\n    static_assert(sizeof(kv_block_t) == expected_block_bytes);",f+':static_assert')
hl=lines(HEAD,f); vdata='\n'.join(hl[1599:1609]); vbase='\n'.join(hl[2255:2264])
assert vdata.startswith('  // Raw pair-interleaved V storage') and vbase.startswith('  // Raw base of the (pair-interleaved) V storage'), (vdata[:40],vbase[:40])
cur=replace_block(cur,"    return kv_block<geometry>(slot, kv_head).k_at(i_page);\n  }\n\n  // The actual V data for a token in this page.",
    "    return kv_block<geometry>(slot, kv_head).k_at(i_page);\n  }\n\n"+vdata+"\n\n  // The actual V data for a token in this page.",f+':v_data')
cur=replace_block(cur,"        reinterpret_cast<const bf16*>(k[i_page])};\n  }\n};\n\n}  // namespace detail",
    "        reinterpret_cast<const bf16*>(k[i_page])};\n  }\n\n"+vbase+"\n};\n\n}  // namespace detail",f+':v_base')
write('pr1',f,cur)
# ---------------- PR2 ---------------- R minus counters, minus logit_ab
for f in ALL:
    if f in ('h/tron/kernels/page_share_counters.hpp','t/t_amx_logit_ab.cpp'): continue
    cur=lines(R,f)
    if f=='h/tron/models/self_attention.hpp': cur=delete_regions(cur,lines(HEAD,f),regions(f,'counters'),f)
    if f=='t/CMakeLists.txt': cur=delete_regions(cur,lines(HEAD,f),[(189,195,'logit_ab-park')],f)
    write('pr2',f,cur)
# ---------------- PR0 ---------------- main + counters header + hooks inserted by two-sided anchors
f='h/tron/models/self_attention.hpp'
hl=lines(HEAD,f); ml=lines(MAIN,f)
# added head lines (from the PR diff base->head)
added=set(); new=0
for ln in git('diff','-U0','1407f48ddb',HEAD,'--',f).stdout.split('\n'):
    m=re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@',ln)
    if m: new=int(m.group(1)); continue
    if ln.startswith('+') and not ln.startswith('+++'): added.add(new); new+=1
def insert_hooks(target,regs,skip):
    """insert head regions into target: anchors are located on the PRISTINE target
    (up to 4 non-skipped context lines on each side), then applied bottom-up."""
    plan=[]
    for lo,hi,c in sorted(regs):
        block=hl[lo-1:hi]
        pre=[];i=lo-1
        while i>=1 and len(pre)<4:
            if i not in skip: pre.insert(0,hl[i-1])
            i-=1
        post=[];i=hi+1
        while i<=len(hl) and len(post)<4:
            if i not in skip: post.append(hl[i-1])
            i+=1
        seq=pre+post; n=len(seq)
        hits=[k for k in range(len(target)-n+1) if target[k:k+n]==seq]
        if len(hits)!=1: raise SystemExit(f'HOOK ANCHOR {lo}-{hi}: {len(hits)} hits for {seq}')
        plan.append((hits[0]+len(pre),lo,block))
    out=list(target)
    for idx,lo,block in sorted(plan,reverse=True):
        out[idx:idx]=block
    return out
hooks=regions(f,'counters')
pr0=insert_hooks(ml,hooks,added)  # skip every PR-added line: PR0 sits on main
write('pr0',f,pr0)
write('pr0','h/tron/kernels/page_share_counters.hpp',lines(R,'h/tron/kernels/page_share_counters.hpp'))
# ---------------- checks ----------------
# C1: hooks inserted into PR2's self_attention (skipping only counters lines) must reproduce R exactly
counters_lines=set()
for lo,hi,c in hooks: counters_lines.update(range(lo,hi+1))
pr2_sa=open(f'{SP}/sub/pr2/{f}').read().split('\n')
rebuilt=insert_hooks(pr2_sa,hooks,counters_lines)
print('C1 PR2+hooks == R self_attention.hpp:', rebuilt==lines(R,f))
# C2: forbidden symbols in PR1
bad=re.compile(r'TRON_AMX_K_MIRROR|amx_mirror|k_mirror|mirror_arena|scatter_k_mirror|page_share|PAGE_SHARE|share_counters|logit_ab|mirror_write_ok|qk_mirror|pack_q_rows')
for root,_,files in os.walk(f'{SP}/sub/pr1'):
    for fn in files:
        p=os.path.join(root,fn)
        for i,l in enumerate(open(p),1):
            if bad.search(l): print('C2 PR1 symbol:',p.replace(SP+'/sub/pr1/',''),i,l.strip()[:90])
prose=re.compile(r'[Mm]irror|arena|these two options|Why not replace')
for root,_,files in os.walk(f'{SP}/sub/pr1'):
    for fn in files:
        p=os.path.join(root,fn)
        for i,l in enumerate(open(p),1):
            if prose.search(l): print('C3 PR1 prose:',p.replace(SP+'/sub/pr1/',''),i,l.strip()[:100])
print('files pr1:',sum(len(x[2]) for x in os.walk(f'{SP}/sub/pr1')),'pr2:',sum(len(x[2]) for x in os.walk(f'{SP}/sub/pr2')),'pr0:',sum(len(x[2]) for x in os.walk(f'{SP}/sub/pr0')))
