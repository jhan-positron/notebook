// measure.js - injected into a scratch copy of the page; writes layout measurements into a <pre id="rdrmeasure">.
window.addEventListener('load', function () {
  var out = [];
  var de = document.documentElement;
  out.push('innerWidth=' + window.innerWidth + ' docScrollWidth=' + de.scrollWidth + ' bodyScrollWidth=' + document.body.scrollWidth + ' docScrollHeight=' + de.scrollHeight);
  // elements that extend past the viewport width and are not inside a scroll container
  var all = document.querySelectorAll('main *');
  var n = 0;
  for (var i = 0; i < all.length; i++) {
    var e = all[i]; var r = e.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (r.right > window.innerWidth + 0.5 || r.left < -0.5) {
      var p = e, inScroll = false;
      while (p && p !== document.body) { var cs = getComputedStyle(p); if (p !== e && (cs.overflowX === 'auto' || cs.overflowX === 'scroll' || cs.overflowX === 'hidden')) { inScroll = true; break; } p = p.parentElement; }
      if (!inScroll && n < 30) { out.push('OVERFLOW ' + e.tagName + '.' + (e.getAttribute('class') || '') + ' left=' + r.left.toFixed(1) + ' right=' + r.right.toFixed(1) + ' text=' + (e.textContent || '').slice(0, 60).replace(/\s+/g, ' ')); n++; }
    }
  }
  // which figure-1 svg variants are displayed
  ['f1w', 'f1m', 'f1n'].forEach(function (c) { var s = document.querySelector('svg.' + c); if (s) { var r = s.getBoundingClientRect(); out.push('svg.' + c + ' display=' + getComputedStyle(s).display + ' w=' + r.width.toFixed(1) + ' h=' + r.height.toFixed(1) + ' left=' + r.left.toFixed(1) + ' right=' + r.right.toFixed(1)); } });
  // scroll containers: client vs scroll width
  var tw = document.querySelectorAll('.tw, .fig');
  for (var j = 0; j < tw.length; j++) { var t = tw[j]; var rr = t.getBoundingClientRect(); if (rr.width === 0) continue; out.push((t.className) + ' client=' + t.clientWidth + ' scroll=' + t.scrollWidth + ' overflowX=' + getComputedStyle(t).overflowX + ' top=' + (rr.top + window.scrollY).toFixed(0) + (t.querySelector('table') ? ' table.' + t.querySelector('table').className : '')); }
  // hint paragraphs shown?
  var h = document.querySelectorAll('p.hint.ht'); var shown = 0; for (var k = 0; k < h.length; k++) { if (getComputedStyle(h[k]).display !== 'none') shown++; } out.push('hint paragraphs=' + h.length + ' shown=' + shown);
  // svg text overlap check within each visible svg: pairs of <text> whose boxes intersect
  var svgs = document.querySelectorAll('figure svg');
  for (var s2 = 0; s2 < svgs.length; s2++) {
    var sv = svgs[s2]; if (getComputedStyle(sv).display === 'none' || sv.getBoundingClientRect().width < 100) continue;
    var ts = sv.querySelectorAll('text'); var boxes = [];
    for (var a = 0; a < ts.length; a++) { var b = ts[a].getBoundingClientRect(); if (b.width > 0) boxes.push([b, ts[a].textContent]); }
    var cnt = 0; var sr = sv.getBoundingClientRect(); var clip = 0;
    for (var a2 = 0; a2 < boxes.length; a2++) {
      var ba = boxes[a2][0];
      if (ba.left < sr.left - 0.5 || ba.right > sr.right + 0.5) { clip++; out.push('SVGTEXT OUTSIDE svg#' + s2 + ' "' + boxes[a2][1] + '" left=' + ba.left.toFixed(1) + ' right=' + ba.right.toFixed(1) + ' svg ' + sr.left.toFixed(1) + '..' + sr.right.toFixed(1)); }
      for (var c2 = a2 + 1; c2 < boxes.length; c2++) { var bb = boxes[c2][0];
        var ox = Math.min(ba.right, bb.right) - Math.max(ba.left, bb.left); var oy = Math.min(ba.bottom, bb.bottom) - Math.max(ba.top, bb.top);
        if (ox > 1 && oy > 3) { cnt++; if (cnt <= 12) out.push('SVGTEXT OVERLAP svg#' + s2 + ' "' + boxes[a2][1] + '" x "' + boxes[c2][1] + '" ox=' + ox.toFixed(1) + ' oy=' + oy.toFixed(1)); } }
    }
    out.push('svg#' + s2 + ' class=' + (sv.getAttribute('class') || '') + ' texts=' + boxes.length + ' overlaps=' + cnt + ' outside=' + clip + ' width=' + sr.width.toFixed(0));
  }
  var pre = document.createElement('pre'); pre.id = 'rdrmeasure'; pre.textContent = out.join('\n'); document.body.appendChild(pre);
});
