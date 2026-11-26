// For every dot (g.pt) of every visible chart svg: which element answers at the centre of its visible circle, and at 4 points 2.5 px from the centre?
(function(){
  var out={dpr:window.devicePixelRatio, svgs:[]};
  document.querySelectorAll('.fig svg').forEach(function(svg,si){
    if (getComputedStyle(svg).display==='none') return;
    var rec={i:si, cls:svg.getAttribute('class')||('fig2 '+svg.getAttribute('viewBox')), dots:0, centreWrong:[], nearWrong:0, nearTotal:0};
    var fig=svg.closest('.fig');
    svg.querySelectorAll('g.pt').forEach(function(g){
      var mk=g.querySelector('circle.mk'); var b=mk.getBoundingClientRect();
      // bring into view (page scroll and sideways scroll of the box)
      mk.scrollIntoView({block:'center',inline:'center'});
      b=mk.getBoundingClientRect();
      var cx=(b.left+b.right)/2, cy=(b.top+b.bottom)/2;
      rec.dots++;
      function owner(x,y){ var e=document.elementFromPoint(x,y); var gg=e&&e.closest?e.closest('g'):null; return gg; }
      var o=owner(cx,cy);
      if (o!==g) { var t=g.querySelector('title').textContent, t2=o&&o.querySelector('title')?o.querySelector('title').textContent:'(none)'; rec.centreWrong.push({dot:t.slice(0,140), answers:t2.slice(0,140)}); }
      [[2.5,0],[-2.5,0],[0,2.5],[0,-2.5]].forEach(function(d){ rec.nearTotal++; if (owner(cx+d[0],cy+d[1])!==g) rec.nearWrong++; });
    });
    out.svgs.push(rec);
  });
  var pre=document.createElement('pre'); pre.id='r2hit'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
