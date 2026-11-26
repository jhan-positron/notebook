// measure.js - appended to a copy of the page; writes geometry facts into a pre element with id r3m, read with --dump-dom
(function(){
function R(r){return [Math.round(r.left*10)/10,Math.round(r.top*10)/10,Math.round(r.right*10)/10,Math.round(r.bottom*10)/10];}
function vis(e){for(var x=e;x&&x.nodeType===1;x=x.parentNode){var cs=getComputedStyle(x);if(cs.display==='none'||cs.visibility==='hidden')return false;}return true;}
var out={};
var de=document.documentElement;
out.win=[window.innerWidth,window.innerHeight];
out.doc={scrollWidth:de.scrollWidth,clientWidth:de.clientWidth,bodyScrollWidth:document.body.scrollWidth,scrollHeight:de.scrollHeight};
out.bodyBg=getComputedStyle(document.body).backgroundColor;
out.bodyFont=getComputedStyle(document.body).fontFamily;
out.main=R(document.querySelector('main').getBoundingClientRect());
out.figs=[];document.querySelectorAll('.fig').forEach(function(f,i){out.figs.push({i:i,cls:f.className,rect:R(f.getBoundingClientRect()),clientWidth:f.clientWidth,scrollWidth:f.scrollWidth});});
out.tws=[];document.querySelectorAll('.tw').forEach(function(f,i){var t=f.querySelector('table');out.tws.push({i:i,tcls:t?t.className:'',vis:vis(f),rect:R(f.getBoundingClientRect()),clientWidth:f.clientWidth,scrollWidth:f.scrollWidth,tableW:t?Math.round(t.getBoundingClientRect().width):0});});
out.tables=[];document.querySelectorAll('table').forEach(function(t,i){out.tables.push({i:i,cls:t.className,vis:vis(t),rect:R(t.getBoundingClientRect()),inTw:!!t.closest('.tw')});});
out.details=[];document.querySelectorAll('details').forEach(function(d){out.details.push({open:d.open,summary:d.querySelector('summary').textContent.trim(),rect:R(d.getBoundingClientRect())});});
out.hints=[];document.querySelectorAll('.hint').forEach(function(h){out.hints.push({cls:h.className,vis:vis(h),text:h.textContent.trim().slice(0,160)});});
out.wide=[];document.querySelectorAll('main *').forEach(function(e){if(!vis(e))return;if(e.closest('.fig')||e.closest('.tw'))return;var r=e.getBoundingClientRect();if(r.width>0&&r.right>de.clientWidth+0.5)out.wide.push({tag:e.tagName,cls:e.className&&e.className.baseVal!==undefined?e.className.baseVal:e.className,rect:R(r),text:(e.textContent||'').trim().slice(0,60)});});
out.svgs=[];
document.querySelectorAll('.fig svg').forEach(function(s,si){
  var o={i:si,cls:s.getAttribute('class')||'',vis:vis(s),rect:R(s.getBoundingClientRect()),viewBox:s.getAttribute('viewBox'),label:s.getAttribute('aria-label')};
  if(o.vis){
    var texts=[];s.querySelectorAll('text').forEach(function(t,ti){var r=t.getBoundingClientRect();texts.push({ti:ti,s:t.textContent,r:R(r),fs:t.getAttribute('font-size'),fill:t.getAttribute('fill'),anchor:t.getAttribute('text-anchor'),x:t.getAttribute('x'),y:t.getAttribute('y'),fw:t.getAttribute('font-weight')||'',cl:t.getComputedTextLength()});});
    o.texts=texts;
    var marks=[];s.querySelectorAll('circle.mk').forEach(function(c){var g=c.closest('g');var tt=g?g.querySelector(':scope > title'):null;marks.push({cx:+c.getAttribute('cx'),cy:+c.getAttribute('cy'),r:+c.getAttribute('r'),cls:c.getAttribute('class'),fill:c.getAttribute('fill'),stroke:c.getAttribute('stroke')||'',rect:R(c.getBoundingClientRect()),title:tt?tt.textContent:null});});
    o.marks=marks;
    var noTitle=[];s.querySelectorAll('circle,path,line,rect').forEach(function(e){var g=e.closest('g');var tt=g?g.querySelector('title'):null;if(!tt)noTitle.push({tag:e.tagName,cls:e.getAttribute('class')||'',a:[e.getAttribute('x')||e.getAttribute('x1')||e.getAttribute('cx')||'',e.getAttribute('y')||e.getAttribute('y1')||e.getAttribute('cy')||'',e.getAttribute('width')||e.getAttribute('x2')||'',e.getAttribute('height')||e.getAttribute('y2')||''],fill:e.getAttribute('fill')||'',stroke:e.getAttribute('stroke')||'',d:(e.getAttribute('d')||'').slice(0,60),dash:e.getAttribute('stroke-dasharray')||''});});
    o.noTitle=noTitle;
    var rects=[];s.querySelectorAll('rect').forEach(function(e){var g=e.closest('g');var tt=g?g.querySelector('title'):null;rects.push({x:+e.getAttribute('x'),y:+e.getAttribute('y'),w:+e.getAttribute('width'),h:+e.getAttribute('height'),fill:e.getAttribute('fill')||'',op:e.getAttribute('fill-opacity')||'',stroke:e.getAttribute('stroke')||'',title:tt?tt.textContent:null});});
    o.rects=rects;
  }
  out.svgs.push(o);
});
var pre=document.createElement('pre');pre.id='r3m';pre.textContent=JSON.stringify(out);document.body.appendChild(pre);
})();
