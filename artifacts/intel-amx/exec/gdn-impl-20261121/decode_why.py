#!/usr/bin/env python3
"""gdn-impl-20261121: two pieces of GDN/gdn-amx-results.html that gen_report.py does not write itself.

  1. Section 5, "Why decode gains little": the token flow of a prefill pass and of a decode step (an animated
     figure), the split of a decode step into GDN wall, attention wall and other work (an animated lane figure
     and a table), and the parts of the GDN step in decode.
  2. The part of section 3 that compares 8 users with 1 user at prompt 1,024.

gen_report.py calls build(globals(), ...) after its own helpers exist. Every number comes from comparison.json
(the medians per cell and arm) or from the decode class of collected.json (the per-run counters).
Words: decode class = the passes in which every token has a listener; these are the decode steps.
The prose follows the plain-english-experiment rules; gen_report.py's page check covers it.
"""
import json
import statistics as st
from types import SimpleNamespace

ARMS_6 = ("base", "p0", "a", "b", "ab", "a0")
N_LAYERS_32 = 32
ATTN_EVERY_4 = 4      # every 4th layer is an attention layer: GDN operation i is model layer i + i / 3 (Note [GDN path stats])

EXTRA_CSS = """
.ctlrow { display: flex; flex-wrap: wrap; gap: 8px; margin: 10px 0 2px; }
.ctlrow[hidden] { display: none; }
.ctl { font: inherit; font-size: 14px; padding: 5px 12px; border: 1px solid var(--ink-2); border-radius: 4px;
  background: var(--surface); color: var(--ink); cursor: pointer; }
.ctl[aria-pressed="true"] { background: var(--ink); color: #ffffff; }
.ctl:focus-visible { outline: 2px solid var(--gdn); outline-offset: 2px; }
"""


def build(g, fig_users, fig_flow, fig_lanes, fig_step, ref_code):
    """g: the globals of gen_report.py. fig_*: the figure numbers. ref_code: the index of the reference for this
    section.
    Returns a dict of HTML pieces and lists of bullets."""
    G = SimpleNamespace(**g)
    P, C, CMP, D, CELLS = G.P, G.C, G.CMP, G.D, G.CELLS
    f, rng, ul, table, ref, cell_name, tj = G.f, G.rng, G.ul, G.table, G.ref, G.cell_name, G.tj
    runs = list(D["col"]["runs"].values())
    users = lambda c: CMP["cells"][c]["users"]
    prompt = lambda c: CMP["cells"][c]["prompt"]

    def dmed(c, a, group, key):
        """Median over the repetitions of one cell and arm of one decode-class value of collected.json."""
        vals = [r[group]["decode_like"].get(key) for r in runs if r["cell"] == c and r["arm"] == a and r.get(group)]
        vals = [v for v in vals if v is not None]
        return st.median(vals) if vals else None

    n_gdn = {r["gdn"]["summary"]["n_operations"] for r in runs}
    assert n_gdn == {24}, n_gdn
    N_GDN, N_ATTN = 24, N_LAYERS_32 - 24
    assert N_LAYERS_32 // ATTN_EVERY_4 == N_ATTN

    def split(c, a):
        """One decode step: its wall, the GDN wall, the attention wall on attention thread 0, and the other work."""
        step = dmed(c, a, "derived", "forward_wall_ms")
        gdn = dmed(c, a, "gdn_derived", "gdn_wall_ms_per_forward")
        attn = dmed(c, a, "derived", "attn_w0_wall_ms_per_forward")
        return {"step": step, "gdn": gdn, "attn": attn, "rest": step - gdn - attn}

    def dstep(c, a):
        """Parts of one GDN step of a decode step, in us per head token."""
        v = {k: dmed(c, a, "gdn_derived", k) for k in ("step_us", "step_start_us", "step_recurrence_us", "step_write_us")}
        v["other"] = v["step_us"] - v["step_start_us"] - v["step_recurrence_us"]      # write and bookkeeping
        return v

    SP = {c: {a: split(c, a) for a in ("base", "ab", "p0", "b")} for c in CELLS}
    share = lambda c, k, a="base": 100.0 * SP[c][a][k] / SP[c][a]["step"]
    c1 = [c for c in CELLS if users(c) == 1]
    c8 = [c for c in CELLS if users(c) == 8]
    small, large = CELLS[0], CELLS[-1]
    assert users(small) == 1 and prompt(small) == 1024 and users(large) == 8 and prompt(large) == 8192

    # ------------------------------------------------------------ figure: token flow (animated)
    tok_share = [r["gdn_derived"]["decode_like"]["share_token"] for r in runs]
    assert min(tok_share) == 1.0 and max(tok_share) == 1.0, "a decode head token left the token path"
    arms_seen = sorted({r["arm"] for r in runs})
    gdn_dec = [dmed(small, a, "gdn_derived", "gdn_wall_ms_per_forward") for a in ARMS_6]
    per_tok = lambda ms, tokens: 1e3 * ms / N_GDN / tokens
    pf0, pf1 = per_tok(tj(small, "base", "prefill_gdn_wall_ms"), 128), per_tok(tj(small, "ab", "prefill_gdn_wall_ms"), 128)
    dc0, dc1 = per_tok(SP[small]["base"]["gdn"], 1), per_tok(SP[small]["ab"]["gdn"], 1)

    def flow_svg():
        W, H = 960, 484
        blue, ink2 = C["gdn"], C["ink2"]
        bw, bh, yA, yB = 70, 30, 74, 280
        qx, ox, slot = [262, 182, 102, 22], [878, 802, 726, 650], 394
        tx0 = 158
        o = [P.svg_open(W, H, "A prefill pass gives a GDN layer 128 tokens per user, and a decode step gives it one").replace("<svg ", '<svg id="flow-svg" ', 1),
             P.arrow_defs("flarr")]
        T = lambda x, y, s, **k: o.append(P.text(x, y, s, **k))
        arrow = lambda x1, y1, x2, y2: o.append(P.line(x1, y1, x2, y2, stroke=ink2, sw=1.4, marker="flarr"))

        def layer_box(y, kernel_1, kernel_2, sid):
            o.append(P.rect(380, y, 250, 100, C["note"], stroke=blue, rx=6))
            T(392, y + 18, "one key head of a GDN layer", size=12, weight=600)
            o.append(P.rect(390, y + 26, bw + 8, bh + 8, "none", stroke=ink2, dash="4 3", rx=3))
            T(390, y + 80, kernel_1, size=11, fill=ink2)
            T(390, y + 94, kernel_2, size=11, fill=ink2)
            arrow(474, y + 45, 544, y + 45)
            T(509, y + 38, "reads, writes", size=10, fill=ink2, anchor="middle")
            o.append(f'<rect id="{sid}" x="548" y="{y + 22}" width="70" height="46" rx="3" fill="#ffffff" stroke="{blue}" stroke-width="1.4"/>')
            T(583, y + 42, "state", size=11.5, weight=600, anchor="middle")
            T(583, y + 57, "128 KiB", size=10, fill=ink2, anchor="middle")

        def measured(y, v0, v1):
            o.append(f'<text x="22" y="{y}" font-family="{P.FONT}" font-size="11.5" style="fill:{ink2}">'
                     f'Measured GDN wall per layer and token ({P.esc(cell_name(small))}): '
                     f'<tspan font-weight="600" style="fill:{C["ink"]}">{v0:.2f} us in the base run, {v1:.2f} us with all three changes</tspan></text>')

        RET_Y = 400
        # ---- upper part: a prefill pass
        T(20, 24, "Prefill pass: tron knows all 128 tokens of the pass when it starts", size=13.5, weight=600)
        T(22, 62, "one chain of 128 tokens, as 4 blocks of 32", size=11.5, fill=ink2)
        layer_box(44, "block kernel (Part A):", "32 tokens per call", "fl-sa")
        arrow(336, 89, 376, 89)
        arrow(632, 89, 646, 89)
        T(650, 62, "outputs of the 128 tokens", size=11.5, fill=ink2)
        for x in ox:
            o.append(P.rect(x, yA, bw, bh, "none", stroke=C["other"], dash="3 3", rx=2))
        measured(184, pf0, pf1)
        o.append(f'<text id="fl-ca" x="380" y="164" font-family="{P.FONT}" font-size="12" font-weight="600" style="fill:{C["ink"]}">'
                 "4 kernel calls take 128 tokens through this key head</text>")
        for i, x in enumerate(qx):
            o.append(f'<g id="fl-a{i}">' + P.rect(x, yA, bw, bh, blue, rx=2)
                     + P.text(x + bw / 2, yA + 19.5, f"{32 * i + 1} to {32 * i + 32}", size=10.5, weight=600, fill="#ffffff", anchor="middle") + "</g>")
        o.append(P.line(20, 198, 940, 198, stroke=C["line"]))

        # ---- lower part: decode steps
        T(20, 224, "Decode step: the next token exists only after the sampler has picked it", size=13.5, weight=600)
        layer_box(250, "token kernel (base build):", "1 token per call", "fl-sb")
        o.append(P.rect(tx0 - 8, yB - 4, 30, bh + 8, "none", stroke=C["other"], dash="3 3", rx=2))
        arrow(184, 295, 376, 295)
        T(280, 287, "1 token per user", size=10.5, fill=ink2, anchor="middle")
        arrow(632, 295, 660, 295)
        o.append(P.rect(664, 272, 106, 46, "#ffffff", stroke=ink2, rx=4))
        T(717, 291, "the other", size=11.5, anchor="middle")
        T(717, 306, "31 layers", size=11.5, anchor="middle")
        arrow(772, 295, 796, 295)
        o.append(P.rect(800, 272, 100, 46, "#ffffff", stroke=ink2, rx=4))
        T(850, 299, "sampler", size=11.5, anchor="middle")
        o.append(f'<polyline points="850,318 850,{RET_Y} {tx0 + 7},{RET_Y} {tx0 + 7},320" fill="none" stroke="{ink2}" stroke-width="1.4" marker-end="url(#flarr)"/>')
        T(600, RET_Y + 30, "the sampler gives the next token, and then the next decode step starts", size=11, fill=ink2, anchor="middle")
        T(22, 452, "tron uses the chain kernel for chains of 2 or more tokens. The block kernel needs 32 tokens. A decode step has 1 token per user.", size=11.5, weight=600)
        measured(472, dc0, dc1)
        o.append(f'<text id="fl-cb" x="380" y="370" font-family="{P.FONT}" font-size="12" font-weight="600" style="fill:{C["ink"]}">'
                 "4 kernel calls take 4 tokens through this key head</text>")
        o.append(f'<g id="fl-b">' + P.rect(tx0, yB, 14, bh, blue, rx=2) + "</g>")
        o.append("</svg>")
        k = {"q": qx, "o": ox, "slot": slot, "tx0": tx0, "ol": 717 - 7, "sm": 850 - 7, "down": 400 - bh / 2 - yB, "light": "#cfe1f7"}
        return "".join(o), k

    FLOW_JS = """
(function () {
  var svg = document.getElementById('flow-svg');
  if (!svg || !window.requestAnimationFrame) return;
  var K = __K__;
  var A = [0, 1, 2, 3].map(function (i) { return document.getElementById('fl-a' + i); });
  var tok = document.getElementById('fl-b');
  var sa = document.getElementById('fl-sa'), sb = document.getElementById('fl-sb');
  var ca = document.getElementById('fl-ca'), cb = document.getElementById('fl-cb');
  var btn = document.getElementById('fl-btn');
  var CYC = 2.2, N = 4, HOLD = 1.6, TOTAL = CYC * N + HOLD;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var running = !reduce, t = 0, last = null;
  function ease(u) { u = Math.max(0, Math.min(1, u)); return u * u * (3 - 2 * u); }
  function lerp(a, b, u) { return a + (b - a) * ease(u); }
  function draw() {
    var calls = 0, pulseA = false, i, u;
    for (i = 0; i < N; i++) {
      u = t - i * CYC;
      var x = K.q[i];
      if (u >= 2.0) x = K.o[i];
      else if (u >= 1.3) x = lerp(K.slot, K.o[i], (u - 1.3) / 0.7);
      else if (u >= 0.7) x = K.slot;
      else if (u > 0) x = lerp(K.q[i], K.slot, u / 0.7);
      if (u >= 0.7 && u < 1.3) pulseA = true;
      if (u >= 1.3) calls++;
      A[i].setAttribute('transform', 'translate(' + (x - K.q[i]).toFixed(1) + ',0)');
    }
    sa.setAttribute('fill', pulseA ? K.light : '#ffffff');
    ca.textContent = 'kernel calls: ' + calls + ' of 4, tokens through this key head: ' + 32 * calls + ' of 128';
    var j = Math.min(N - 1, Math.floor(t / CYC)), done = j, dx = 0, dy = 0, op = 1, pulseB = false;
    u = t - j * CYC;
    if (t >= CYC * N) { done = N; }
    else if (u < 0.45) dx = lerp(0, K.slot + 4 - K.tx0, u / 0.45);
    else if (u < 0.9) { dx = K.slot + 4 - K.tx0; pulseB = true; }
    else if (u < 1.25) { dx = lerp(K.slot + 4 - K.tx0, K.ol - K.tx0, (u - 0.9) / 0.35); done = j + 1; }
    else if (u < 1.5) { dx = lerp(K.ol - K.tx0, K.sm - K.tx0, (u - 1.25) / 0.25); done = j + 1; }
    else {
      done = j + 1; op = 0.55;
      var v = Math.min(1, (u - 1.5) / 0.6), w = K.sm - K.tx0, len = 2 * K.down + w, d = v * len;
      if (d < K.down) { dx = w; dy = d; }
      else if (d < K.down + w) { dx = w - (d - K.down); dy = K.down; }
      else { dx = 0; dy = K.down - (d - K.down - w); }
    }
    tok.setAttribute('transform', 'translate(' + dx.toFixed(1) + ',' + dy.toFixed(1) + ')');
    tok.setAttribute('opacity', op);
    sb.setAttribute('fill', pulseB ? K.light : '#ffffff');
    cb.textContent = 'kernel calls: ' + done + ', tokens through this key head: ' + done;
  }
  function frame(now) {
    if (last !== null && running) { t += Math.min(0.1, (now - last) / 1000); if (t >= TOTAL) t = 0; draw(); }
    last = now;
    window.requestAnimationFrame(frame);
  }
  btn.textContent = running ? 'Pause' : 'Play';
  btn.onclick = function () { running = !running; btn.textContent = running ? 'Pause' : 'Play'; };
  document.getElementById('fl-ctl').hidden = false;
  window.requestAnimationFrame(frame);
})();
"""

    # ------------------------------------------------------------ figure: wall-clock lanes of one decode step (animated)
    WAIT_FILL = "#fde9e1"
    awork = lambda c, a: tj(c, a, "decode_attn_busy_ms") - tj(c, a, "decode_attn_join_wait_ms")   # mean of the 40 threads, per decode step
    ajoin = lambda c, a: tj(c, a, "decode_attn_join_wait_ms")
    def lanes_svg():
        W, left, right = 960, 200, 124
        pw = W - left - right
        lane_h, lane_gap, panel_h = 18, 8, 196
        lanes = [("gdn", "GDN threads (16)", C["gdn"]), ("attn", "attention threads (40)", C["attn"]), ("rest", "other work", C["other"])]
        H = 30 + 2 * panel_h
        o = [P.svg_open(W, H, "Wall-clock lanes of one decode step, base run and the run with all three changes").replace("<svg ", '<svg id="lanes-svg" ', 1)]
        o.append(f'<text class="ln-s" x="20" y="18" font-family="{P.FONT}" font-size="13" font-weight="600" style="fill:{C["ink"]}" '
                 'data-t0="Shown: the base run" data-t1="Shown: the run with all three changes">Shown: the base run</text>')
        o.append(P.rect(330, 8, 14, 12, C["attn"]))
        o.append(P.text(350, 18.5, "mean busy time without the join wait", size=11.5, fill=C["ink2"]))
        o.append(P.rect(606, 8, 14, 12, WAIT_FILL, stroke=C["attn"], dash="3 2"))
        o.append(P.text(626, 18.5, "rest of the attention wall: waits", size=11.5, fill=C["ink2"]))
        y = 30
        for c in (small, large):
            s0, s1 = SP[c]["base"], SP[c]["ab"]
            scale = pw / max(s0["step"], s1["step"])
            top = y + 30
            o.append(P.text(20, y + 16, f"{cell_name(c)}: one decode step", size=13, weight=600))
            fall = s0["step"] - s1["step"]
            t1 = (f"decode step: {s1['step']:.2f} ms, {fall:.2f} ms shorter" if fall >= 0.05 else f"decode step: {s1['step']:.2f} ms, no change")
            o.append(f'<text class="ln-s" x="{left + pw:.1f}" y="{y + 16}" font-family="{P.FONT}" font-size="12.5" font-weight="600" text-anchor="end" '
                     f'style="fill:{C["ink"]}" data-t0="decode step: {s0["step"]:.2f} ms" data-t1="{t1}">decode step: {s0["step"]:.2f} ms</text>')
            ly = {k: top + i * (lane_h + lane_gap) for i, (k, _, _) in enumerate(lanes)}
            for k, name, col in lanes:
                o.append(P.rect(left, ly[k], pw, lane_h, "#f1f3f6"))
                o.append(P.text(left - 10, ly[k] + 13, name, size=12.5, anchor="end", weight=600))
                t0_, t1_ = (f"{s[k]:.2f} ms, {100 * s[k] / s['step']:.0f} %" for s in (s0, s1))
                o.append(f'<text class="ln-s" x="{left + pw + 8:.1f}" y="{ly[k] + 13}" font-family="{P.FONT}" font-size="12" style="fill:{C["ink"]}" '
                         f'data-t0="{t0_}" data-t1="{t1_}">{t0_}</text>')

            def blocks(s, a):
                """(kind, x, width) per block. An attention block is the wall of the job; attn_work is its busy part."""
                x, out = float(left), []
                work = max(0.0, awork(c, a)) / N_ATTN * scale
                for layer in range(N_LAYERS_32):
                    core = "attn" if layer % ATTN_EVERY_4 == ATTN_EVERY_4 - 1 else "gdn"
                    wr = s["rest"] / N_LAYERS_32 * scale
                    wc = s[core] / (N_ATTN if core == "attn" else N_GDN) * scale
                    out += [("rest", x, wr), (core, x + wr, wc)]
                    if core == "attn":
                        out.append(("attn_work", x + wr, min(work, wc)))
                    x += wr + wc
                return out, x

            b0, end0 = blocks(s0, "base")
            b1, end1 = blocks(s1, "ab")
            col = {k: cc for k, _, cc in lanes}
            for (k, x0, w0), (_, x1, w1) in zip(b0, b1):
                geo = f'data-a="{x0:.2f},{w0:.2f},{x1:.2f},{w1:.2f}"'
                if k == "attn":
                    o.append(f'<rect class="ln-b" x="{x0:.2f}" y="{ly[k] + 0.5}" width="{w0:.2f}" height="{lane_h - 1}" fill="{WAIT_FILL}" stroke="{C["attn"]}" '
                             f'stroke-width="1" stroke-dasharray="3 2" {geo}/>')
                else:
                    kk = "attn" if k == "attn_work" else k
                    o.append(f'<rect class="ln-b" x="{x0:.2f}" y="{ly[kk]}" width="{w0:.2f}" height="{lane_h}" fill="{col[kk]}" {geo}/>')
            bottom = ly["rest"] + lane_h
            o.append(P.line(end0, top - 4, end0, bottom + 4, stroke=C["ink2"], dash="3 3"))
            o.append(f'<rect class="ln-b" x="{end0:.2f}" y="{top - 4}" width="2" height="{bottom - top + 8}" fill="{C["ink"]}" data-a="{end0:.2f},2,{end1:.2f},2"/>')
            ya = bottom + 10
            o.append(P.line(left, ya, left + pw, ya, stroke=C["ink2"]))
            tick = 0.5 if s0["step"] < 6 else 2.0
            v = 0.0
            while v <= max(s0["step"], s1["step"]) + 1e-9:
                o.append(P.line(left + v * scale, ya, left + v * scale, ya + 4, stroke=C["ink2"]))
                o.append(P.text(left + v * scale, ya + 16, f"{v:g}", size=11, fill=C["muted"], anchor="middle"))
                v += tick
            o.append(P.text(left + pw, ya + 32, "milliseconds from the start of the decode step", size=11, fill=C["muted"], anchor="end"))
            note = (f"With all three changes: {s1['step']:.2f} ms. " + ("The attention blocks are shorter." if fall >= 0.05 else "No block changes its length."))
            o.append(P.text(left, ya + 52, note, size=11.5, weight=600))
            y += panel_h
        o.append("</svg>")
        return "".join(o)

    LANES_JS = """
(function () {
  var svg = document.getElementById('lanes-svg');
  if (!svg || !window.requestAnimationFrame) return;
  var rects = [].slice.call(svg.querySelectorAll('.ln-b')), texts = [].slice.call(svg.querySelectorAll('.ln-s'));
  var b0 = document.getElementById('ln-b0'), b1 = document.getElementById('ln-b1'), ba = document.getElementById('ln-auto');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var p = 0, target = 0, timer = null, raf = null;
  var geo = rects.map(function (r) { return r.getAttribute('data-a').split(',').map(Number); });
  function draw() {
    rects.forEach(function (r, i) {
      var a = geo[i];
      r.setAttribute('x', (a[0] + (a[2] - a[0]) * p).toFixed(2));
      r.setAttribute('width', Math.max(0, a[1] + (a[3] - a[1]) * p).toFixed(2));
    });
    var key = p < 0.5 ? 'data-t0' : 'data-t1';
    texts.forEach(function (x) { x.textContent = x.getAttribute(key); });
  }
  function step() {
    var d = target - p;
    if (reduce || Math.abs(d) < 0.01) { p = target; draw(); raf = null; return; }
    p += d * 0.12; draw(); raf = window.requestAnimationFrame(step);
  }
  function go(to) {
    target = to;
    b0.setAttribute('aria-pressed', String(to === 0)); b1.setAttribute('aria-pressed', String(to === 1));
    if (!raf) raf = window.requestAnimationFrame(step);
  }
  function auto(on) {
    if (timer) { window.clearInterval(timer); timer = null; }
    if (on) timer = window.setInterval(function () { go(target ? 0 : 1); }, 2800);
    ba.setAttribute('aria-pressed', String(on));
  }
  b0.onclick = function () { auto(false); go(0); };
  b1.onclick = function () { auto(false); go(1); };
  ba.onclick = function () { auto(!timer); };
  document.getElementById('ln-ctl').hidden = false;
  go(0); auto(!reduce);
})();
"""

    # ------------------------------------------------------------ figure: the GDN step, prefill and decode
    d0, d1 = dstep(small, "base"), dstep(small, "ab")

    def pstep(a):
        """Parts of one GDN step of a prefill pass, in us per head token (the values of the step figure of section 6)."""
        t = CMP["cells"][small]["terms"][a]
        v = {"rec": t["gdn_step_recurrence_us"] or 0.0, "around": (t["gdn_step_pre_us"] or 0.0) + (t["gdn_step_post_us"] or 0.0),
             "start": t["gdn_step_start_us"] or 0.0}
        v["io"] = t["gdn_step_us"] - sum(v.values())
        return v, t["gdn_step_us"]

    (pb, pb_tot), (pa, pa_tot) = pstep("base"), pstep("ab")
    dparts = lambda d: {"rec": d["step_recurrence_us"], "around": 0.0, "start": d["step_start_us"], "io": d["other"]}

    def step_svg():
        parts = [("rec", "recurrence or token step", C["gdn"]), ("around", "before and after it", C["attn"]),
                 ("start", "start of the chain", C["crit"]), ("io", "write, bookkeeping", C["other"])]
        rows = [{"label": "Prefill, base run", "sub": "token kernel, chain of 128 tokens", "values": pb},
                {"label": "Prefill, all three changes", "sub": "block kernel, chain of 128 tokens", "values": pa},
                {"label": "Decode, base run", "sub": "token kernel, chain of 1 token", "values": dparts(d0)},
                {"label": "Decode, all three changes", "sub": "token kernel, chain of 1 token", "values": dparts(d1)}]
        return P.stacked(rows, parts, "us", "Time of one GDN step by part, in a prefill pass and in a decode step", left=230, right=80,
                         xlabel="microseconds per GDN step (one token of one key head), mean of the 16 GDN threads")

    # ------------------------------------------------------------ table: the split of a decode step
    def split_table():
        cellf = lambda v, s: f"{v:.2f} ({100 * v / s:.0f} %)"
        rows = []
        for c in CELLS:
            a, b = SP[c]["base"], SP[c]["ab"]
            rows.append([cell_name(c), f"{a['step']:.2f}", cellf(a["gdn"], a["step"]), cellf(a["attn"], a["step"]), cellf(a["rest"], a["step"]),
                         f"{b['step']:.2f}", f"{b['gdn']:.2f}", f"{b['attn']:.2f}", f"{b['rest']:.2f}", G.srng([100 * (b['step'] - a['step']) / a['step']], 1)])
        return table(["Cell", "Base run: decode step (ms)", "Base run: GDN wall (ms, share of the step)", "Base run: attention wall (ms, share)",
                      "Base run: other work (ms, share)", "All three changes: decode step (ms)", "All three changes: GDN wall (ms)",
                      "All three changes: attention wall (ms)", "All three changes: other work (ms)", "Change of the decode step (%)"],
                     rows, num_cols=range(1, 10))

    # ------------------------------------------------------------ text of section 5
    sh = lambda cells, k: rng([share(c, k) for c in cells], 0)
    big = [c for c in c8 if prompt(c) >= 4096]
    tps_big = [G.arm(c, a)["tps_change_pct"] for c in big for a in ("b", "ab")]
    tps_small = [G.arm(c, a)["tps_change_pct"] for c in CELLS if c not in big for a in ("b", "ab")]
    tps_1u = [G.arm(c, a)["tps_change_pct"] for c in c1 for a in ("b", "ab")]
    s_intro = [
        "Section 4 gives the measured decode speed. This section gives the reasons for it.",
        "A decode step gives every GDN layer one token per user. tron gives a chain of 1 token to step(), which runs the token kernel on the stored state.",
        "So Part 0 and Part A do not run in decode. The chain kernel works on a copy of the state in another layout. For 1 token that would add two copies of 128 KiB.",
        "Part B runs in decode. It changes the attention kernel only.",
        f"With 1 user, {sh(c1, 'rest')} % of a decode step is neither GDN work nor attention work. None of the three changes touches that part.",
        f"So the decode gain is large only where attention is a large part of the step. That is with 8 users and prompts of 4,096 tokens or more: {rng(tps_big, 0)} %. "
        f"In the other {len(CELLS) - len(big)} cells decode changed by {G.srng(tps_small, 1)} %.",
    ]
    s_flow = [
        "A prefill pass holds 128 prompt tokens per user. tron knows all of them when the pass starts.",
        "A GDN layer takes them as one chain. So a kernel can work on many tokens of the chain in one call.",
        "The chain kernel computes the read of the next token while it writes the current token. The block kernel takes 32 tokens per call.",
        "A decode step is different. The model must run all 32 layers for one token before the sampler can pick the next token.",
        "So in a decode step a GDN layer holds one token per user. tron then runs step(), with the token kernel of the base build.",
        "With 8 users a decode step has 8 tokens. They belong to 8 sequences with 8 states, so they are 8 chains of 1 token.",
        f"The counters show the same. In all {len(arms_seen)} arms and all {len(CELLS)} cells, 100 % of the decode head tokens took the token path. "
        "That path is step() with the token kernel.",
        f"With {cell_name(small)} the GDN wall of a decode step is {rng(gdn_dec, 3)} ms in all {len(ARMS_6)} arms.",
        f"In that cell a prefill pass spends {pf0:.2f} us of GDN wall per layer and token in the base run. With all three changes it spends {pf1:.2f} us.",
        f"A decode step spends {dc0:.2f} us per layer and token in the base run and {dc1:.2f} us with all three changes.",
    ]
    a0_, a1_ = SP[large]["base"], SP[large]["ab"]
    same2 = lambda x, y: f"{x:.2f}" == f"{y:.2f}"
    s_split = [
        "The figure and the table split the wall of a decode step into three parts." + ul([
            f"the GDN wall of the {N_GDN} GDN layers", f"the attention wall of the {N_ATTN} attention layers",
            "the other work: matrix multiplies on the FPGA cards, data transfers and the remaining CPU work"]),
        "The attention wall is the time of an attention job on attention thread 0, from its entry to its return. It includes every wait inside the job. "
        "The values sum it over the 8 attention layers.",
        "After the job, thread 0 waits until the other attention threads have finished. That wait is not in the attention wall, so it counts as other work.",
        "The other work is the decode step minus the two walls. The counters do not split it.",
        f"With 1 user the other work is {sh(c1, 'rest')} % of the step. The GDN wall is {sh(c1, 'gdn')} %, and the attention wall is {sh(c1, 'attn')} %.",
        f"With 8 users the other work is {sh(c8, 'rest')} % of the step. The GDN wall is {sh(c8, 'gdn')} %, and the attention wall is {sh(c8, 'attn')} %.",
        f"Take {cell_name(large)}. With all three changes the attention wall fell from {a0_['attn']:.2f} to {a1_['attn']:.2f} ms. "
        f"The decode step fell from {a0_['step']:.2f} to {a1_['step']:.2f} ms.",
        f"In that cell the other work fell by {a0_['rest'] - a1_['rest']:.2f} ms, to {a1_['rest']:.2f} ms. The GDN wall changed by {a1_['gdn'] - a0_['gdn']:+.2f} ms.",
        "Insufficient data for why the other work fell. Hypothesis: thread 0 waits less for the other attention threads after its job. A timer around that wait would test it.",
        (f"With {cell_name(small)} the attention wall is {SP[small]['base']['attn']:.2f} ms in both runs. The decode step is {SP[small]['base']['step']:.2f} ms in both."
         if same2(SP[small]['base']['attn'], SP[small]['ab']['attn']) and same2(SP[small]['base']['step'], SP[small]['ab']['step']) else
         f"With {cell_name(small)} the attention wall is {SP[small]['base']['attn']:.2f} ms in the base run and {SP[small]['ab']['attn']:.2f} ms with all three changes. "
         f"The decode step is {SP[small]['base']['step']:.2f} and {SP[small]['ab']['step']:.2f} ms."),
    ]
    start_share = [100 * dstep(c, "base")["step_start_us"] / dstep(c, "base")["step_us"] for c in CELLS]
    zero_step = lambda c: 100 * SP[c]["base"]["gdn"] * dstep(c, "base")["step_recurrence_us"] / dstep(c, "base")["step_us"] / SP[c]["base"]["step"]
    c8_1k = next(c for c in c8 if prompt(c) == 1024)
    s_gdn = [
        f"In a decode step with {cell_name(small)}, a GDN step takes {d0['step_us']:.1f} us. In a prefill pass of the base run it takes {pb_tot:.2f} us.",
        "The counters split the decode value into three parts." + ul([
            f"the start of the chain: {d0['step_start_us']:.2f} us", f"the token step: {d0['step_recurrence_us']:.2f} us",
            f"the bookkeeping and the time stamps: {d0['other']:.2f} us"]),
        "The token step is the convolution, the normalization, the recurrence, the norm and the output gate of one token.",
        "A chain of 1 token changes the state in place. So no write of the state follows the token step.",
        f"The start prepares the state of one key head for the chain{ref(ref_code)}. It copies the state when the chain writes to another buffer. "
        "It also checks every state value for NaN, a marker of an invalid result.",
        "The state of one key head is 128 KiB, or 131,072 bytes. The counters do not split the start further.",
        f"A chain runs the start once. A prefill chain has one start per 128 tokens: {pb['start']:.2f} us per token in the base run.",
        "In decode every token is its own chain, so every token has a whole start.",
        f"In the {len(CELLS)} cells the start is {rng(start_share, 0)} % of the GDN step in decode (base run). A faster recurrence does not shorten it.",
        f"Suppose the token step took no time. With {cell_name(small)} the decode step would be about {zero_step(small):.0f} % shorter (est.). "
        f"With {cell_name(c8_1k)} it would be about {zero_step(c8_1k):.0f} % shorter (est.).",
        "This estimate assumes that the GDN wall falls in proportion to the GDN step.",
        "Hypothesis: in decode the start reads the state from main memory, not from the cache. A timer around the NaN check alone would test it.",
        "Insufficient data for the chain kernel on chains of 1 token. A stand-alone timing with windows of 1 token would give it.",
    ]
    T4 = G.T4
    wall_fac = lambda cells: [SP[c]["base"]["attn"] / SP[c]["ab"]["attn"] for c in cells]
    busy_share = [100 * tj(c, "base", "decode_attn_busy_ms") / SP[c]["base"]["attn"] for c in c1]
    t4r = lambda regime, decode: [v for r in T4["rows"] if r["regime"] == regime and (r["use"] == "decode") == decode for v in r["ratio"]]
    step_fall = [100 * (SP[c]["base"]["step"] - SP[c]["ab"]["step"]) / SP[c]["base"]["step"] for c in big]
    s_partb = [
        "Part B is the only change that runs in decode. Section 4 gives its effect in every cell.",
        f"With 1 user the attention wall is {sh(c1, 'attn')} % of the step. So a faster attention kernel can shorten the step by at most {sh(c1, 'attn')} % there.",
        f"The attention wall itself got {rng(wall_fac(c1), 2)} times shorter with 1 user. With 8 users it got {rng(wall_fac(c8), 2)} times shorter.",
        f"With 1 user the mean busy time of the attention threads is {rng(busy_share, 0)} % of that wall. The rest of the wall holds the waits.",
        f"In decode the kernel gains less when the pages come from main memory. In the stand-alone test it was {rng(t4r('memory', True), 2)} times faster there{ref(9)}. "
        "Loading the page takes most of the time there.",
        f"For prefill with pages from main memory it was {rng(t4r('memory', False), 2)} times faster. "
        f"With the pages in cache it was {rng(t4r('cache', True), 2)} times faster for decode too.",
        f"With 8 users and prompts of 4,096 tokens or more, the attention wall is {sh(big, 'attn')} % of the step. "
        f"There the decode step got {rng(step_fall, 1)} % shorter, and the decode speed rose by {rng(tps_big, 0)} % (section 4).",
    ]

    svg_flow, k_flow = flow_svg()
    fig_flow_html = (f'<figure id="fig{fig_flow}"><div class="scroll">{svg_flow}</div>'
                     '<div class="ctlrow" id="fl-ctl" hidden><button type="button" class="ctl" id="fl-btn">Pause</button></div>'
                     f'<figcaption><b>Figure {fig_flow}.</b> How a GDN layer gets its tokens in a prefill pass and in a decode step. '
                     + ul(["The animation is a sketch. Its speed does not follow the measured times.",
                           "In the upper part the 128 tokens of a prefill pass enter the layer as 4 blocks of 32. Each block is one kernel call.",
                           "In the lower part one token passes the layer, the other 31 layers and the sampler. Only then does the next token exist.",
                           "After 4 kernel calls the prefill pass has moved 128 tokens through the layer. The decode loop has moved 4 tokens.",
                           "The figure shows one of the 16 key heads of a layer. Each key head has its own state of 128 KiB and its own kernel calls."])
                     + "</figcaption></figure>")
    fall_large = a0_["step"] - a1_["step"]
    fig_lanes_html = (f'<figure id="fig{fig_lanes}"><div class="scroll">{lanes_svg()}</div>'
                      '<div class="ctlrow" id="ln-ctl" hidden>'
                      '<button type="button" class="ctl" id="ln-b0" aria-pressed="true">Base run</button>'
                      '<button type="button" class="ctl" id="ln-b1" aria-pressed="false">All three changes</button>'
                      '<button type="button" class="ctl" id="ln-auto" aria-pressed="false">Alternate</button></div>'
                      f'<figcaption><b>Figure {fig_lanes}.</b> Wall-clock lanes of one decode step, for the smallest and the largest cell. '
                      + ul(["Each block is the total of its lane divided by the number of its layers. The lanes have 24, 8 and 32 layers. Block lengths are to scale inside a panel.",
                            "The counters do not say where in the step the other work falls. Its 32 equal blocks are a sketch.",
                            "The solid part of an attention block is the mean busy time of the 40 threads, without the join wait. The dashed part is the rest of the attention wall. It holds the waits.",
                            "The two panels have different time scales. The layers are in the order of the model: 3 GDN layers, then 1 attention layer.",
                            "Inside a layer the figure draws the other work first. That order is a sketch.",
                            "The buttons switch between the base run and the run with all three changes. The dashed line marks the end of the base run.",
                            f"In the upper panel no block changes. In the lower panel the attention blocks get {a0_['attn'] - a1_['attn']:.2f} ms shorter in total, "
                            f"and the other-work blocks {a0_['rest'] - a1_['rest']:.2f} ms. The step ends {fall_large:.2f} ms earlier.",
                            f"Of the {a0_['attn'] - a1_['attn']:.2f} ms, {ajoin(large, 'base') - ajoin(large, 'ab'):.2f} ms is a shorter join wait.",
                            "Work on the FPGA cards that runs during an attention job counts as attention wall here."])
                      + "</figcaption></figure>")
    fig_step_html = P.figure(step_svg(), f"<b>Figure {fig_step}.</b> Time of one GDN step by part, in a prefill pass and in a decode step ({cell_name(small)}). "
                             + ul(["The values are means over the 16 GDN threads.",
                                   "In the three rows with the token kernel the blue bar is the whole token step. The counters cannot split it.",
                                   "The red part is the start of the chain. Every decode token runs a whole start."]), f"fig{fig_step}")
    sec5 = f"""<div class="col">
{ul(s_intro)}
<h3>One token at a time</h3>
{ul(s_flow)}
</div>
{fig_flow_html}
<div class="col">
<h3>Where the time of a decode step goes</h3>
{ul(s_split)}
</div>
{fig_lanes_html}
{split_table()}
<div class="col">
<h3>Inside the GDN work of a decode step</h3>
{ul(s_gdn)}
</div>
{fig_step_html}
<div class="col">
<h3>What Part B gives in decode</h3>
{ul(s_partb)}
</div>
"""

    # ------------------------------------------------------------ section 3: 8 users against 1 user at prompt 1,024
    cu = {users(c): c for c in CELLS if prompt(c) == 1024}
    u1, u8 = cu[1], cu[8]
    work = lambda c, a: tj(c, a, "prefill_attn_busy_ms") - tj(c, a, "prefill_attn_join_wait_ms")
    join = lambda c, a: tj(c, a, "prefill_attn_join_wait_ms")
    pas = lambda c, a: tj(c, a, "prefill_pass_ms")
    kvwait = lambda c, a: tj(c, a, "prefill_attn_w0_wall_ms") - tj(c, a, "prefill_attn_busy_ms")
    fall_pct = lambda c, a: G.direct(c, a)["measured_fall_pct"]
    pb_alone = {c: x["measured_pct_of_base"] for c, x in G.partb_alone()}
    gshare = lambda c: 100 * tj(c, "base", "prefill_gdn_wall_ms") / pas(c, "base")
    s_users = [
        "At prompt 1,024 the two GDN changes give a little more with 8 users than with 1 user." + ul([
            f"Part 0: {fall_pct(u8, 'p0'):.1f} against {fall_pct(u1, 'p0'):.1f} %", f"Part A: {fall_pct(u8, 'a'):.1f} against {fall_pct(u1, 'a'):.1f} %"]),
        f"With 8 users the GDN wall is {gshare(u8):.0f} % of the prefill pass of the base run. With 1 user it is {gshare(u1):.0f} %.",
        f"With Part B the order is the opposite. Parts A and B give {fall_pct(u8, 'ab'):.1f} % with 8 users and {fall_pct(u1, 'ab'):.1f} % with 1 user.",
        f"The cause is Part B alone. It gives {pb_alone[u8]:.1f} % of the base run with 8 users and {pb_alone[u1]:.1f} % with 1 user.",
        "The kill-switch pair shows where the difference comes from. Its two runs differ in Part B only.",
        f"With 8 users the attention busy time without the join wait got {work(u8, 'p0') / work(u8, 'b'):.2f} times shorter. "
        f"That saves {work(u8, 'p0') - work(u8, 'b'):.1f} ms per prefill pass.",
        f"In the same runs the join wait rose from {join(u8, 'p0'):.1f} to {join(u8, 'b'):.1f} ms. "
        f"So the pass got only {pas(u8, 'p0') - pas(u8, 'b'):.1f} ms shorter, of {pas(u8, 'p0'):.0f} ms.",
        f"With 1 user that busy time got {work(u1, 'p0') / work(u1, 'b'):.2f} times shorter, and the join wait did not rise. "
        f"The pass got {pas(u1, 'p0') - pas(u1, 'b'):.2f} ms shorter, of {pas(u1, 'p0'):.1f} ms.",
        "Insufficient data for why the join wait rose with 8 users. In the join a thread waits until the other threads have finished their scoring. "
        "A time stamp per thread at the end of its scoring would show which threads end late.",
        "The design page reports the same rise on delphi-3bda, another server, with the 128-wide kernel. "
        "There the join wait rose from 4.1 to 12.0 ms with 8 users, prompt 1,024.",
        "The design page lists another wait as an open point. It is the wait for the K and V data of the pass. "
        "tron counts that wait outside the busy time and outside the join wait.",
        f"The attention wall minus the mean busy time holds that wait. With 8 users it changed from {kvwait(u8, 'p0'):.1f} to {kvwait(u8, 'b'):.1f} ms.",
    ]

    def users_svg():
        W, left, right, bar_h, gap = 960, 290, 170, 20, 8
        xmin, xmax = -4.0, 3.0   # percent of the pass wall
        pw = W - left - right
        X = lambda v: left + pw * (v - xmin) / (xmax - xmin)
        rows_per = 3
        H = 40 + 2 * (26 + rows_per * (bar_h + gap)) + 44
        o = [P.svg_open(W, H, "What Part B changed in a prefill pass at prompt 1,024, with 1 user and with 8 users")]
        top = 20
        for t in range(int(xmin), int(xmax) + 1):
            o.append(P.line(X(t), top, X(t), H - 40, stroke=C["ink2"] if t == 0 else C["grid"], dash="3 3" if t == 0 else None))
            o.append(P.text(X(t), H - 24, f"{t:+d} %" if t else "0 %", size=11, fill=C["muted"], anchor="middle"))
        o.append(P.text(left + pw, H - 6, "change from the Part 0 run to the run with Parts 0 and B, percent of the pass wall of the Part 0 run", size=11, fill=C["muted"], anchor="end"))
        y = top + 4
        for c in (u1, u8):
            base = pas(c, "p0")
            o.append(P.text(10, y + 14, f"{cell_name(c)} (pass wall {base:.1f} ms)", size=12.5, weight=600))
            y += 26
            for name, d, col in (("busy time without the join wait", work(c, "b") - work(c, "p0"), C["attn"]),
                                 ("join wait", join(c, "b") - join(c, "p0"), C["crit"]),
                                 ("prefill pass wall", pas(c, "b") - pas(c, "p0"), C["ink2"])):
                pct = 100 * d / base
                x0, x1 = sorted((X(0), X(pct)))
                o.append(P.text(left - 10, y + bar_h * 0.7, name, size=12.5, anchor="end"))
                o.append(P.rect(x0, y, max(x1 - x0, 1.0), bar_h, col, rx=2, title=f"{cell_name(c)}, {name}: {d:+.2f} ms ({pct:+.1f} % of the pass wall)"))
                o.append(P.text(max(x1, X(0)) + 8, y + bar_h * 0.7, f"{d:+.2f} ms ({pct:+.1f} %)", size=12, weight=600))
                y += bar_h + gap
            y += 6
        o.append("</svg>")
        return "".join(o)

    def users_table():
        rows = []
        for c in (u1, u8):
            rows.append([str(users(c)), f"{tj(c, 'p0', 'prefill_attn_busy_ms'):.2f}", f"{tj(c, 'b', 'prefill_attn_busy_ms'):.2f}", f"{join(c, 'p0'):.2f}", f"{join(c, 'b'):.2f}",
                         f"{work(c, 'p0'):.2f}", f"{work(c, 'b'):.2f}", f"{work(c, 'p0') / work(c, 'b'):.2f}", f"{pas(c, 'p0'):.2f}", f"{pas(c, 'b'):.2f}",
                         f"{pas(c, 'p0') - pas(c, 'b'):.2f}", f"{100 * (pas(c, 'p0') - pas(c, 'b')) / pas(c, 'p0'):.1f}"])
        return table(["Users", "Attention busy time, Part 0 run (ms)", "Attention busy time, Parts 0 and B (ms)", "Join wait, Part 0 run (ms)", "Join wait, Parts 0 and B (ms)",
                      "Busy time without the join wait, Part 0 run (ms)", "Busy time without the join wait, Parts 0 and B (ms)", "Times shorter",
                      "Prefill pass wall, Part 0 run (ms)", "Prefill pass wall, Parts 0 and B (ms)", "Fall of the pass wall (ms)", "Fall of the pass wall (%)"],
                     rows, num_cols=range(0, 12))

    fig_users_html = P.figure(users_svg(), f"<b>Figure {fig_users}.</b> What Part B changed in a prefill pass at prompt 1,024, with 1 user and with 8 users. "
                              + ul(["Each bar is the change from the Part 0 run to the run with Parts 0 and B. It is a percent of the pass wall of the Part 0 run.",
                                    f"With 8 users the busy time without the join wait fell more than with 1 user. But the join wait rose by {join(u8, 'b') - join(u8, 'p0'):.2f} ms. "
                                    f"That is {100 * (join(u8, 'b') - join(u8, 'p0')) / (work(u8, 'p0') - work(u8, 'b')):.0f} % of the fall of that busy time."]), f"fig{fig_users}")
    sec3 = f"""<div class="col">
<h3>8 users against 1 user at prompt 1,024</h3>
{ul(s_users)}
</div>
{fig_users_html}
{users_table()}
"""
    open_items = [
        f"With 1 user decode changed by {G.srng(tps_1u, 1)} %. Section 5 gives the reasons for the small gain.",
        f"In decode the start of a chain is {rng(start_share, 0)} % of the GDN step. None of the three changes shortens it there, and the counters do not split it.",
    ]
    script = "<script>" + FLOW_JS.replace("__K__", json.dumps(k_flow)) + LANES_JS + "</script>"
    return {"sec5": sec5, "sec3": sec3, "open_items": open_items, "script": script, "css": EXTRA_CSS}
