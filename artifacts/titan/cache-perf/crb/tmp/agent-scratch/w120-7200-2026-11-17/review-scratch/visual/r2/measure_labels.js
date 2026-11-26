// right edges of start-anchored texts in every visible chart svg, in svg user units
(function(){
  var out=[];
  document.querySelectorAll('.fig svg').forEach(function(svg,si){
    var cs=getComputedStyle(svg); if(cs.display==='none') return;
    var sb=svg.getBoundingClientRect(); var k=svg.viewBox.baseVal.width/sb.width;
    svg.querySelectorAll('text').forEach(function(t){
      if (t.getAttribute('text-anchor')!=='start') return;
      var b=t.getBoundingClientRect();
      out.push([si, svg.getAttribute('class')||'fig2', +((b.right-sb.left)*k).toFixed(1), +t.getAttribute('y'), t.getAttribute('font-size'), t.textContent, +t.getComputedTextLength().toFixed(1)]);
    });
  });
  var pre=document.createElement('pre'); pre.id='r2lab'; pre.textContent=JSON.stringify({dpr:window.devicePixelRatio,rows:out}); document.body.appendChild(pre);
})();
