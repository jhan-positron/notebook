"""Independent verifier, finding 5: per-text effective font size via getScreenCTM.
usage: v5_measure.py PAGE.html OUTDIR WIDTH..."""
import json, os, re, subprocess, sys, html
CHROME='/home/jhan/.cache/ms-playwright/chromium_headless_shell-1243/chrome-headless-shell-linux64/chrome-headless-shell'
JS=r"""<script>
window.addEventListener('load',function(){
 var de=document.documentElement;
 var out={vw:de.clientWidth,iw:window.innerWidth,sw:de.scrollWidth,bsw:document.body.scrollWidth,svgs:[],wide:[]};
 var all=document.querySelectorAll('svg');
 for(var i=0;i<all.length;i++){var s=all[i];var r=s.getBoundingClientRect();var vb=s.viewBox.baseVal;
  var ts=s.querySelectorAll('text');var mn=1e9,mx=0,mntxt='',n=0,clipped=0;
  for(var j=0;j<ts.length;j++){var t=ts[j];if(!t.textContent.trim())continue;var m=t.getScreenCTM();
   var sc=Math.sqrt(Math.abs(m.a*m.d-m.b*m.c));var e=parseFloat(getComputedStyle(t).fontSize)*sc;n++;
   if(e<mn){mn=e;mntxt=t.textContent.trim().slice(0,40);} if(e>mx)mx=e;
   var b=t.getBoundingClientRect(); if(b.left<r.left-1||b.right>r.right+1)clipped++;}
  var p=s.parentElement;var cs=getComputedStyle(p);var f=s.closest('figure');
  out.svgs.push({i:i,fig:f?f.id:'',cls:s.getAttribute('class')||'',vbw:vb?vb.width:null,w:+r.width.toFixed(1),
   scale:vb&&vb.width?+(r.width/vb.width).toFixed(4):null,n:n,emin:n?+mn.toFixed(2):null,emax:n?+mx.toFixed(2):null,mintxt:mntxt,
   pcls:p.className||p.tagName,pox:cs.overflowX,pcw:p.clientWidth,psw:p.scrollWidth,clipped:clipped,
   label:(s.getAttribute('aria-label')||'').slice(0,60)});}
 var els=document.body.querySelectorAll('*');
 for(var k=0;k<els.length;k++){var el=els[k];if(el.closest('svg')&&el.tagName.toLowerCase()!='svg')continue;
  var rr=el.getBoundingClientRect();
  if(rr.right>de.clientWidth+1){var a=el,sc2=false;while(a&&a!==document.body){var o=getComputedStyle(a).overflowX;
    if(a!==el&&(o=='auto'||o=='scroll'||o=='hidden')){sc2=true;break;}a=a.parentElement;}
   if(!sc2)out.wide.push({tag:el.tagName,cls:el.className&&el.className.baseVal!==undefined?el.className.baseVal:el.className,id:el.id,right:+rr.right.toFixed(1)});}}
 var pre=document.createElement('pre');pre.id='MEASURE';pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
});
</script>"""
page,outdir=sys.argv[1],sys.argv[2]
src=open(page,encoding='utf-8').read()
tmp=os.path.join(outdir,'_measure.html')
open(tmp,'w',encoding='utf-8').write(src.replace('</body>',JS+'</body>'))
for w in sys.argv[3:]:
    dom=subprocess.run([CHROME,'--no-sandbox','--in-process-gpu','--headless','--window-size=%s,3000'%w,
        '--virtual-time-budget=3000','--dump-dom','file://'+tmp],capture_output=True,text=True).stdout
    m=re.search(r'<pre id="MEASURE">(.*?)</pre>',dom,re.S)
    d=json.loads(html.unescape(m.group(1)))
    json.dump(d,open(os.path.join(outdir,'measure_%s.json'%w),'w'))
    sv=d['svgs']; tx=[s for s in sv if s['n']]
    print('== width',w,'clientWidth',d['vw'],'innerWidth',d['iw'],'docScrollWidth',d['sw'],'bodyScrollWidth',d['bsw'])
    print(' svgs',len(sv),'with text',len(tx),'unwrapped-not-figwrap',sum(1 for s in sv if 'figwrap' not in s['pcls']))
    print(' smallest effective font',min(s['emin'] for s in tx),'max of per-svg min',max(s['emin'] for s in tx))
    print(' svgs with emin<9:',[(s['i'],s['fig'],s['emin'],s['mintxt']) for s in tx if s['emin']<9])
    print(' svgs scrolling in wrapper:',sum(1 for s in sv if s['psw']>s['pcw']+1),' parent overflow kinds',sorted(set(s['pox'] for s in sv)))
    print(' text outside svg box:',[(s['i'],s['fig'],s['clipped']) for s in sv if s['clipped']])
    print(' elements past viewport w/o scrolling ancestor:',d['wide'][:10],len(d['wide']))
    print(' not in figwrap:',[(s['i'],s['fig'],s['pcls'],s['w'],s['vbw'],s['emin']) for s in sv if 'figwrap' not in s['pcls']][:10])
    for s in sv[:3]: print('  ',s)
os.unlink(tmp)
