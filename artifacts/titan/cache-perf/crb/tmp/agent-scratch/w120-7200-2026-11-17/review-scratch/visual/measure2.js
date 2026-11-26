(function(){
  function rb(b){return [Math.round(b.x*10)/10,Math.round(b.y*10)/10,Math.round((b.x+b.width)*10)/10,Math.round((b.y+b.height)*10)/10];}
  var out=[];
  [].forEach.call(document.querySelectorAll('.fig svg'),function(s,si){
    var W=parseFloat(s.getAttribute('width')),H=parseFloat(s.getAttribute('height'));
    var texts=[].map.call(s.querySelectorAll('text'),function(t){return {t:t.textContent,b:rb(t.getBBox()),fs:t.getAttribute('font-size'),anchor:t.getAttribute('text-anchor'),halo:!!t.getAttribute('stroke')};});
    var marks=[];
    [].forEach.call(s.querySelectorAll('circle.mk'),function(c){var b=c.getBBox();var sw=parseFloat(c.getAttribute('stroke-width')||0)/2;marks.push({k:'dot',b:[b.x-sw,b.y-sw,b.x+b.width+sw,b.y+b.height+sw],title:(c.parentNode.querySelector('title')||{}).textContent});});
    [].forEach.call(s.querySelectorAll('g > rect'),function(c){var b=c.getBBox();marks.push({k:'band',b:[b.x,b.y,b.x+b.width,b.y+b.height],title:(c.parentNode.querySelector('title')||{}).textContent});});
    var res={svg:si,W:W,H:H,outside:[],textOnMark:[],textText:[],maxRight:0,texts:texts.length};
    texts.forEach(function(a){
      if(a.b[0]<0||a.b[2]>W||a.b[1]<0||a.b[3]>H) res.outside.push(a);
      if(a.b[2]>res.maxRight) res.maxRight=a.b[2];
      marks.forEach(function(m){
        var ox=Math.min(a.b[2],m.b[2])-Math.max(a.b[0],m.b[0]), oy=Math.min(a.b[3],m.b[3])-Math.max(a.b[1],m.b[1]);
        if(ox>0.5&&oy>0.5) res.textOnMark.push({text:a.t,tb:a.b,kind:m.k,mb:m.b.map(function(v){return Math.round(v*10)/10;}),ox:Math.round(ox*10)/10,oy:Math.round(oy*10)/10,mark:(m.title||'').slice(0,70)});
      });
    });
    for(var i=0;i<texts.length;i++)for(var j=i+1;j<texts.length;j++){
      var a=texts[i].b,b=texts[j].b;
      var ox=Math.min(a[2],b[2])-Math.max(a[0],b[0]), oy=Math.min(a[3],b[3])-Math.max(a[1],b[1]);
      if(ox>0.5&&oy>0.5) res.textText.push({a:texts[i].t,b:texts[j].t,ab:a,bb:b,ox:Math.round(ox*10)/10,oy:Math.round(oy*10)/10});
    }
    // dot-dot overlaps (centres closer than diameter)
    var dots=marks.filter(function(m){return m.k=='dot';});
    var dd=0, ddHard=0;
    for(var i=0;i<dots.length;i++)for(var j=i+1;j<dots.length;j++){
      var a=dots[i].b,b=dots[j].b; var ax=(a[0]+a[2])/2, ay=(a[1]+a[3])/2, bx=(b[0]+b[2])/2, by=(b[1]+b[3])/2;
      var d=Math.sqrt((ax-bx)*(ax-bx)+(ay-by)*(ay-by)); var r=(a[2]-a[0])/2+(b[2]-b[0])/2;
      if(d<r){dd++; if(d<r*0.5){ddHard++; res['hard'+ddHard]=[dots[i].title.slice(0,120),dots[j].title.slice(0,120),Math.round(d*10)/10];}}
    }
    res.dotOverlaps=dd; res.dotHardOverlaps=ddHard;
    res.smallFont=texts.filter(function(t){return parseFloat(t.fs)<11;}).length;
    res.fontSizes={}; texts.forEach(function(t){res.fontSizes[t.fs]=(res.fontSizes[t.fs]||0)+1;});
    out.push(res);
  });
  var pre=document.createElement('pre'); pre.id='MEASURE2'; pre.textContent=JSON.stringify(out); document.body.appendChild(pre);
})();
