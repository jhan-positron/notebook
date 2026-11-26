D='/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/proxy-examples-2026-11-12/worker/'
s=open(D+'applied.html').read()
inj='''<script>
window.addEventListener('load',()=>{
 const out=[];
 window.__errs.forEach(e=>out.push('ERR '+e));
 function ov(svg){const ts=[...svg.querySelectorAll('text')];const r=ts.map(t=>t.getBoundingClientRect());const vb=svg.getBoundingClientRect();
  for(let i=0;i<ts.length;i++){ if(r[i].left<vb.left-0.5||r[i].right>vb.right+0.5||r[i].top<vb.top-0.5||r[i].bottom>vb.bottom+0.5) out.push('CLIP '+svg.id+' "'+ts[i].textContent+'" '+[r[i].left-vb.left,r[i].right-vb.left,vb.width,r[i].top-vb.top,r[i].bottom-vb.top,vb.height].map(v=>v.toFixed(1)).join(' '));
   for(let j=i+1;j<ts.length;j++){const a=r[i],b=r[j];const w=Math.min(a.right,b.right)-Math.max(a.left,b.left),h=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top); if(w>1&&h>3) out.push('OVERLAP '+svg.id+' "'+ts[i].textContent+'" | "'+ts[j].textContent+'" w='+w.toFixed(1)+' h='+h.toFixed(1));}}
  return ts.length;}
 document.querySelectorAll('svg').forEach(v=>{const n=ov(v); out.push('SVG '+v.id+' texts='+n+' children='+v.children.length+' w='+v.getBoundingClientRect().width.toFixed(0)+' top='+(v.getBoundingClientRect().top+scrollY).toFixed(0)+' h='+v.getBoundingClientRect().height.toFixed(0));});
 out.push('DOCW '+document.documentElement.scrollWidth+' '+innerWidth);
 const pre=document.createElement('pre');pre.id='PROBE';pre.textContent=out.join('\\n');document.body.appendChild(pre);
});
</script>'''
pre='<script>window.__errs=[];window.addEventListener("error",e=>window.__errs.push(e.message+" @"+e.lineno+":"+e.colno));</script>'
i=-6
s2=s[:i+6]+pre+s[i+6:]
s2=s2+inj
open('probe.html','w').write(s2)
print(i, '</body>' in s)
