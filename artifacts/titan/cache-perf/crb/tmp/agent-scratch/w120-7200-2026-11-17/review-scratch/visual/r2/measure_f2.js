(function(){
  var out=[];
  document.querySelectorAll('.panels svg').forEach(function(svg,si){
    var sb=svg.getBoundingClientRect();
    svg.querySelectorAll('text').forEach(function(t){
      var b=t.getBoundingClientRect(); var x=b.left-sb.left, r=b.right-sb.left, y=b.top-sb.top;
      if (t.getAttribute('text-anchor')==='start') out.push([si, +r.toFixed(1), +y.toFixed(1), t.textContent]);
    });
  });
  out.sort(function(a,b){return b[1]-a[1];});
  var pre=document.createElement('pre'); pre.id='r2f2'; pre.textContent=JSON.stringify(out.slice(0,400)); document.body.appendChild(pre);
})();
