// numbers that a line break separates from their unit, in the visible prose and tables (not in svg, not in closed details)
(function(){
  var out=[]; var re=/(\d[\d.,:]*)\s(%|GB\/s|MT\/s|kB|GiB|MiB|px|s\b|min\b|B\b|x\b)/g;
  var w=document.createTreeWalker(document.querySelector('main'),NodeFilter.SHOW_TEXT,null);
  var n;
  while((n=w.nextNode())){
    var p=n.parentElement; if(!p||p.closest('svg')||p.closest('details:not([open])')) continue;
    var s=n.nodeValue, m; re.lastIndex=0;
    while((m=re.exec(s))){
      var a=document.createRange(); a.setStart(n,m.index+m[1].length-1); a.setEnd(n,m.index+m[1].length);
      var b=document.createRange(); var u=m.index+m[0].length-m[2].length; b.setStart(n,u); b.setEnd(n,u+1);
      var ra=a.getBoundingClientRect(), rb=b.getBoundingClientRect();
      if(ra.height>0&&rb.height>0&&Math.abs(ra.top-rb.top)>4){ var sec=p.closest('table')?'table':(p.closest('figcaption')?'figcaption':(p.closest('.short')?'short':'prose')); out.push([sec,m[0],s.slice(Math.max(0,m.index-40),m.index+m[0].length+10)]); }
    }
  }
  var pre=document.createElement('pre'); pre.id='r2split'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
