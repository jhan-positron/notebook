(function(){
  var s=document.querySelectorAll('.fig svg')[0];
  var names=[],vals=[];
  [].forEach.call(s.querySelectorAll('text'),function(t){var b=t.getBBox();var a=t.getAttribute('text-anchor');var x=parseFloat(t.getAttribute('x'));
    if(a=='start'&&x<=24) names.push([t.textContent,Math.round((b.x+b.width)*10)/10]);
    else if(/^\d{3}\.\d\d$/.test(t.textContent)) vals.push([t.textContent,Math.round(b.x*10)/10,Math.round((b.x+b.width)*10)/10]);});
  names.sort(function(a,b){return b[1]-a[1];}); vals.sort(function(a,b){return a[1]-b[1];});
  var out={longestNames:names.slice(0,3),shortestNameEnd:names[names.length-1],leftmostValueLabel:vals[0],rightmostValueLabel:vals.slice().sort(function(a,b){return b[2]-a[2];})[0]};
  var pre=document.createElement('pre'); pre.id='M3'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
