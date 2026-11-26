(function(){
  function r(b){return [Math.round(b.left*10)/10,Math.round(b.top*10)/10,Math.round(b.right*10)/10,Math.round(b.bottom*10)/10];}
  var out={};
  var de=document.documentElement;
  out.win=[window.innerWidth,window.innerHeight];
  out.doc=[de.scrollWidth,de.scrollHeight,document.body.scrollWidth];
  out.details=[].map.call(document.querySelectorAll('details'),function(d){return {open:d.open,summary:d.querySelector('summary').textContent};});
  // elements wider than viewport
  var wide=[];
  [].forEach.call(document.querySelectorAll('main *'),function(e){
    var b=e.getBoundingClientRect();
    if(b.width>0 && (b.right>window.innerWidth+0.5 || b.left<-0.5)){
      // is it inside a scroll container?
      var p=e.parentElement, inScroll=false;
      while(p){var cs=getComputedStyle(p); if(cs.overflowX=='auto'||cs.overflowX=='scroll'){inScroll=true;break;} p=p.parentElement;}
      if(!inScroll) wide.push([e.tagName,e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className,r(b)]);
    }
  });
  out.wideOutsideScroll=wide.slice(0,40);
  out.scrollers=[].map.call(document.querySelectorAll('.fig,.tw'),function(e){var b=e.getBoundingClientRect();return {cls:e.className,client:e.clientWidth,scroll:e.scrollWidth,box:r(b)};});
  out.svgs=[].map.call(document.querySelectorAll('svg'),function(s,i){var b=s.getBoundingClientRect();return {i:i,w:s.getAttribute('width'),h:s.getAttribute('height'),vb:s.getAttribute('viewBox'),box:r(b),ntext:s.querySelectorAll('text').length,ntitle:s.querySelectorAll('title').length,parent:s.parentElement.className};});
  out.tables=[].map.call(document.querySelectorAll('table'),function(t){var b=t.getBoundingClientRect();return {cls:t.className,box:r(b),parentClient:t.parentElement.clientWidth,parentScroll:t.parentElement.scrollWidth};});
  // text overlaps within each big svg
  var ov=[];
  [].forEach.call(document.querySelectorAll('.fig svg'),function(s,si){
    var ts=[].map.call(s.querySelectorAll('text'),function(t){var b=t.getBoundingClientRect();return {t:t.textContent,b:b,fs:getComputedStyle(t).fontSize,fill:getComputedStyle(t).fill};});
    var sb=s.getBoundingClientRect();
    ts.forEach(function(a){ if(a.b.width>0 && (a.b.left<sb.left-0.5||a.b.right>sb.right+0.5||a.b.top<sb.top-0.5||a.b.bottom>sb.bottom+0.5)) ov.push({svg:si,clipped:a.t,box:r(a.b),svgbox:r(sb)}); });
    for(var i=0;i<ts.length;i++)for(var j=i+1;j<ts.length;j++){
      var a=ts[i].b,b=ts[j].b; if(a.width==0||b.width==0) continue;
      var ox=Math.min(a.right,b.right)-Math.max(a.left,b.left), oy=Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top);
      if(ox>1 && oy>3) ov.push({svg:si,a:ts[i].t,b:ts[j].t,ox:Math.round(ox*10)/10,oy:Math.round(oy*10)/10,abox:r(a),bbox:r(b)});
    }
  });
  out.textOverlaps=ov;
  var pre=document.createElement('pre'); pre.id='MEASURE'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
