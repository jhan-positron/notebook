// measure.js - injected into a scratch copy of the page. Writes a JSON record into <pre id="r2measure">.
(function () {
  function r(b) { return { x: +b.left.toFixed(1), y: +b.top.toFixed(1), r: +b.right.toFixed(1), b: +b.bottom.toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) }; }
  function vis(el) { for (var e = el; e && e.nodeType === 1; e = e.parentElement) { var cs = getComputedStyle(e); if (cs.display === 'none' || cs.visibility === 'hidden') return false; } return true; }
  var out = { win: [window.innerWidth, window.innerHeight], doc: { scrollWidth: document.documentElement.scrollWidth, clientWidth: document.documentElement.clientWidth, bodyScrollWidth: document.body.scrollWidth, scrollHeight: document.documentElement.scrollHeight } };
  // page-level overflow: elements whose right edge passes the viewport and that have no scrolling ancestor
  var over = [];
  document.querySelectorAll('main *').forEach(function (el) {
    if (!vis(el)) return;
    var b = el.getBoundingClientRect(); if (b.width === 0) return;
    if (b.right > document.documentElement.clientWidth + 0.5) {
      var sc = false; for (var e = el.parentElement; e; e = e.parentElement) { var o = getComputedStyle(e).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') { sc = true; break; } }
      if (!sc) over.push({ tag: el.tagName, cls: el.className && el.className.baseVal !== undefined ? el.className.baseVal : el.className, right: +b.right.toFixed(1), text: (el.textContent || '').slice(0, 60) });
    }
  });
  out.overflowNoScrollAncestor = over.slice(0, 40);
  // scroll containers
  out.scrollers = [];
  document.querySelectorAll('.fig,.tw,.panels,figure,details,table').forEach(function (el) {
    if (!vis(el)) return;
    out.scrollers.push({ tag: el.tagName, cls: el.className, clientW: el.clientWidth, scrollW: el.scrollWidth, box: r(el.getBoundingClientRect()), ox: getComputedStyle(el).overflowX });
  });
  // svgs
  out.svgs = [];
  document.querySelectorAll('.fig svg').forEach(function (svg, si) {
    if (!vis(svg)) return;
    var sb = svg.getBoundingClientRect();
    var rec = { i: si, cls: svg.getAttribute('class'), viewBox: svg.getAttribute('viewBox'), box: r(sb), texts: [], overl: [], clip: [], markText: [], noTitle: 0, marks: 0 };
    var texts = [].slice.call(svg.querySelectorAll('text'));
    var tb = texts.map(function (t) { var b = t.getBoundingClientRect(); return { t: t.textContent, x: b.left - sb.left, y: b.top - sb.top, r: b.right - sb.left, b: b.bottom - sb.top, fs: parseFloat(getComputedStyle(t).fontSize), anchor: t.getAttribute('text-anchor') }; });
    var sx = sb.width / svg.viewBox.baseVal.width;
    rec.scale = +sx.toFixed(4);
    tb.forEach(function (a, i) {
      if (a.x < -0.5 || a.r > sb.width + 0.5 || a.y < -0.5 || a.b > sb.height + 0.5) rec.clip.push({ t: a.t, x: +a.x.toFixed(1), r: +a.r.toFixed(1), y: +a.y.toFixed(1), b: +a.b.toFixed(1), W: +sb.width.toFixed(1) });
      for (var j = i + 1; j < tb.length; j++) { var c = tb[j];
        var ox = Math.min(a.r, c.r) - Math.max(a.x, c.x), oy = Math.min(a.b, c.b) - Math.max(a.y, c.y);
        // text boxes include line gap: shrink vertical by 22 % of the font size on each side
        var ay0 = a.y + 0.22 * a.fs * sx, ay1 = a.b - 0.22 * a.fs * sx, cy0 = c.y + 0.22 * c.fs * sx, cy1 = c.b - 0.22 * c.fs * sx;
        var oy2 = Math.min(ay1, cy1) - Math.max(ay0, cy0);
        if (ox > 0.5 && oy2 > 0.5) rec.overl.push({ a: a.t, b: c.t, ox: +ox.toFixed(1), oy: +oy2.toFixed(1), ax: [+a.x.toFixed(1), +a.r.toFixed(1), +a.y.toFixed(1), +a.b.toFixed(1)], bx: [+c.x.toFixed(1), +c.r.toFixed(1), +c.y.toFixed(1), +c.b.toFixed(1)] });
      }
    });
    // marks: visible circles with class mk
    var marks = [].slice.call(svg.querySelectorAll('circle.mk'));
    rec.marks = marks.length;
    marks.forEach(function (m) {
      var g = m.closest('g'); var hasT = false; for (var e = m; e && e !== svg; e = e.parentNode) { if (e.querySelector && e.querySelector(':scope > title')) { hasT = true; break; } }
      if (!hasT) rec.noTitle++;
      var b = m.getBoundingClientRect(); var mx = b.left - sb.left, mr = b.right - sb.left, my = b.top - sb.top, mb = b.bottom - sb.top;
      tb.forEach(function (a) { var ay0 = a.y + 0.22 * a.fs * sx, ay1 = a.b - 0.22 * a.fs * sx; var ox = Math.min(a.r, mr) - Math.max(a.x, mx), oy = Math.min(ay1, mb) - Math.max(ay0, my); if (ox > 0.5 && oy > 0.5) rec.markText.push({ t: a.t, ox: +ox.toFixed(1), oy: +oy.toFixed(1), mark: [+mx.toFixed(1), +my.toFixed(1)], tx: [+a.x.toFixed(1), +a.r.toFixed(1), +a.y.toFixed(1), +a.b.toFixed(1)] }); });
      if (mx < -0.5 || mr > sb.width + 0.5) rec.clip.push({ mark: [+mx.toFixed(1), +mr.toFixed(1)], W: +sb.width.toFixed(1) });
    });
    rec.nText = tb.length;
    rec.minFontPx = Math.min.apply(null, tb.map(function (a) { return a.fs * sx; }));
    out.svgs.push(rec);
  });
  // details state
  out.details = [].slice.call(document.querySelectorAll('details')).map(function (d) { return { open: d.open, summary: d.querySelector('summary').textContent }; });
  // tables
  out.tables = [].slice.call(document.querySelectorAll('table')).filter(vis).map(function (t) { var b = t.getBoundingClientRect(); var p = t.parentElement; return { cls: t.className, w: +b.width.toFixed(1), left: +b.left.toFixed(1), right: +b.right.toFixed(1), parent: p.tagName + '.' + p.className, pClientW: p.clientWidth, pScrollW: p.scrollWidth, pox: getComputedStyle(p).overflowX }; });
  out.bg = getComputedStyle(document.body).backgroundColor;
  var pre = document.createElement('pre'); pre.id = 'r2measure'; pre.textContent = JSON.stringify(out); document.body.appendChild(pre);
})();
