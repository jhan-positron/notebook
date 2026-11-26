import sys
p=sys.argv[1]; s=open(p).read()
def rep(a,b,count=1):
    global s
    assert s.count(a)>=1, a[:60]
    s=s.replace(a,b) if count==0 else s.replace(a,b,count)
# a) measure the value label, then place the range after it
rep('''    g.appendChild(el("text", {x: padL + w + 7, y: by + 12, "font-size": 13, "font-weight": 600, fill: C("--text-primary")}, r.label));
    if (r.range) g.appendChild(el("text", {x: padL + w + 7 + r.label.length * 7.6 + 5, y: by + 12, "font-size": 11.5, fill: C("--text-secondary")}, r.range));
''','''    const lab = el("text", {x: padL + w + 7, y: by + 12, "font-size": 13, "font-weight": 600, fill: C("--text-primary")}, r.label);
    g.appendChild(lab);
    const rng = r.range ? el("text", {y: by + 12, "font-size": 11.5, fill: C("--text-secondary")}, r.range) : null;
    if (rng) g.appendChild(rng);
''')
rep('''    svg.appendChild(g);
    if (r.note)''','''    svg.appendChild(g);
    if (rng) rng.setAttribute("x", padL + w + 7 + lab.getComputedTextLength() + 6);
    if (r.note)''')
# b) more room for the labels right of the strip charts
rep('const W = 880, H = 190, padL = 34, padR = 96, top = 30, bot = 26;','const W = 880, H = 190, padL = 34, padR = 108, top = 30, bot = 26;')
rep('{x: 880 - 96 - 4, y: 44,','{x: 880 - 108 - 4, y: 44,',0)
# c) exact caption
rep('Before, a burst went above the 8-CPU quota every 5 s. After, no 0.1 s window used more than __AFTER_MAX__ CPUs.',
    'Before, a burst came every 5 s, and __BEFORE_OVER__ of the 600 windows shown were above the 8-CPU quota. After, no window used more than __AFTER_MAX__ CPUs.')
rep('<li>One burst alone was larger than the quota of one period. 84% of the stall time in that sample fell inside the bursts [Ref12].</li>',
    '<li>One burst needed 2.07 CPU-seconds, and the quota allows 0.8 CPU-seconds per 100 ms period. 84% of the stall time in that sample fell inside the bursts [Ref12].</li>')
open(p,'w').write(s); print('template patched')
