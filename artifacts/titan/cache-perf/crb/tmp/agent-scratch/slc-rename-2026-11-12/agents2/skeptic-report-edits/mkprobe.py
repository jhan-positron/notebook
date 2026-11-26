import sys
src,dst,width=sys.argv[1],sys.argv[2],sys.argv[3]
t=open(src,encoding='utf-8').read()
head='<meta charset="utf-8">\n<script>window.__errs=[];window.addEventListener("error",function(e){window.__errs.push(String(e.message)+" @line "+e.lineno);});</script>\n'
assert t.startswith('<meta charset="utf-8">\n')
t=head+t[len('<meta charset="utf-8">\n'):]
tail='''
<script>
(function(){
 var r={errs:window.__errs,svgs:{},docScrollW:document.documentElement.scrollWidth,docClientW:document.documentElement.clientWidth,winW:window.innerWidth};
 document.querySelectorAll('svg[id]').forEach(function(s){r.svgs[s.id]=s.querySelectorAll('*').length;});
 r.lattabRows=document.querySelectorAll('#lattab tr').length;
 var main=document.querySelector('main'); r.mainW=main.getBoundingClientRect().width;
 r.pres=[];document.querySelectorAll('pre').forEach(function(p){var b=p.getBoundingClientRect();r.pres.push({w:b.width,sw:p.scrollWidth,cw:p.clientWidth,h:b.height,parent:p.parentElement.tagName,font:getComputedStyle(p).fontFamily,fs:getComputedStyle(p).fontSize});});
 var h=document.getElementById('the-read-loop-compiled-from-c');
 if(!h){h=document.getElementById('what-3-loads-2-stores-of-16-b-per-cycle-means');}
 r.h3={tag:h.tagName,parent:h.parentElement.tagName,text:h.textContent,top:h.getBoundingClientRect().top+window.scrollY};
 // tables after the h3 until next h2
 r.tables=[];var el=h.nextElementSibling;var n=0;
 while(el && el.tagName!=='H2'){ n++; if(el.tagName==='DIV'&&el.classList.contains('tw')){var t=el.querySelector('table');var b=t.getBoundingClientRect();r.tables.push({w:b.width,divW:el.getBoundingClientRect().width,divSW:el.scrollWidth,rows:t.rows.length,cols:t.rows[0].cells.length});} el=el.nextElementSibling;}
 r.sectionElems=n; r.nextH2=el?el.id:null; r.nextH2top=el?el.getBoundingClientRect().top+window.scrollY:null;
 // bad nesting
 r.preInP=document.querySelectorAll('p pre').length; r.ulInP=document.querySelectorAll('p ul').length; r.tableInP=document.querySelectorAll('p table').length; r.hInP=document.querySelectorAll('p h3,p h2').length;
 r.emptyP=[].filter.call(document.querySelectorAll('p'),function(p){return p.textContent.trim()===''&&p.children.length===0;}).length;
 // overflow elements
 var W=document.documentElement.clientWidth; r.over=[];
 document.querySelectorAll('main *').forEach(function(e){var b=e.getBoundingClientRect(); if(b.right>W+0.5 && b.width>0){ // skip elements inside scroll containers
   var p=e.parentElement,inscroll=false; while(p&&p!==document.body){var o=getComputedStyle(p).overflowX; if(o==='auto'||o==='scroll'){inscroll=true;break;} p=p.parentElement;}
   if(!inscroll) r.over.push([e.tagName,Math.round(b.right),e.textContent.slice(0,60)]);}});
 r.toc=[];document.querySelectorAll('nav.toc a').forEach(function(a){var id=a.getAttribute('href').slice(1);var t=document.getElementById(id);r.toc.push([id,a.textContent,t?t.tagName:null,t?t.textContent:null]);});
 r.heads=[];document.querySelectorAll('main h2,main h3').forEach(function(x){r.heads.push([x.tagName,x.id,x.textContent]);});
 var pre=document.createElement('script');pre.type='application/json';pre.id='probe-result';pre.textContent=JSON.stringify(r);document.body.appendChild(pre);
})();
</script>
'''
open(dst,'w',encoding='utf-8').write(t+tail)
