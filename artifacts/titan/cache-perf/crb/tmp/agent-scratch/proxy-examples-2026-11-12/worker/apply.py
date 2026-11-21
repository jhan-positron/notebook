#!/usr/bin/env python3
"""Apply the worker edits to crb-memory-hierarchy.html. Every edit stays on its physical line.
usage: apply.py <in.html> <out.html>"""
import sys, re, os
D = os.path.dirname(os.path.abspath(__file__))
src = open(sys.argv[1]).read().split('\n')
out = list(src)
def one(pred, what):
    hits = [i for i, l in enumerate(out) if pred(l)]
    assert len(hits) == 1, (what, hits)
    return hits[0]
def flat(name):
    t = open(os.path.join(D, name)).read()
    return ''.join(l.strip('\n') for l in t.split('\n'))
def js(name):
    ls = [l.strip() for l in open(os.path.join(D, name)).read().split('\n') if l.strip()]
    # line comments must become block comments, since the script goes on one physical line
    ls = ['/* ' + l[2:].strip() + ' */' if l.startswith('//') else l for l in ls]
    assert not any('//' in l.split('*/')[-1].replace('://', '') for l in ls), 'inline // comment'
    return ' '.join(ls)
# 1. proxy section, body paragraph (line after the h3)
h = one(lambda l: l.startswith('<h3 id="lines-homed-on-the-other-mesh-are-served-by-a-local-proxy">'), 'proxy h3')
assert out[h + 1].startswith('<p>The home node of a line is fixed by the address hash'), out[h + 1][:80]
out[h + 1] = flat('sec232.html')
assert out[h + 2].startswith('<p class="take"><b>So all of a core'), out[h + 2][:80]
out[h + 2] = flat('sec233.html')
# 2. cross-chiplet paragraph
h = one(lambda l: l.startswith('<h3 id="a-first-read-of-lines-cached-on-the-other-chiplet-costs-85-ns">'), 'cross h3')
assert out[h + 1].startswith('<p>Corrected on 2026-11-02'), out[h + 1][:80]
out[h + 1] = flat('sec253.html')
# 3. latency figure: head room above the DRAM label, and the other labels moved clear of the lines
def sub(old, new, what):
    i = one(lambda l: old in l, what)
    assert out[i].count(old) == 1, what
    out[i] = out[i].replace(old, new)
sub("const x0 = Math.log2(4*K), x1 = Math.log2(2*G), ymax = 160;", "const x0 = Math.log2(4*K), x1 = Math.log2(2*G), ymax = 180;", 'ymax')
sub("lab(X(1.2*M), Y(3.75) - 12, 'L2: 3.75 ns (10.5 cycles)', INK, 'middle');", "lab(X(1.5*M), Y(3.75) - 12, 'L2: 3.75 ns (10.5 cycles)', INK, 'end');", 'l2 label')
sub("lab(X(32*M), Y(30.4) - 12, 'SLC: 30 ns (85 cycles)', S1, 'middle');", "lab(X(48*M), Y(30.4) - 24, 'SLC: 30 ns (85 cycles)', S1, 'end');", 'slc label')
sub("lab(X(32*M), Y(5.42) + 20, 'repeated chain: 5.4 ns, every load misses L2', S2, 'middle');", "lab(X(32*M) - 4, Y(5.42) - 10, 'repeated chain: 5.4 ns', S2, 'end');", 'repeated label')
sub("lab(X(32*M) + 8, (Y(30.18) + Y(5.42)) / 2 + 4, '5.6x gap', '#c8373a');", "lab(X(32*M) - 8, Y(5.42) - 26, '5.6x gap', '#c8373a', 'end');", 'gap label')
# 4. data-path boxes (wording given by the user)
sub("'mesh: 64 slices of 1 MiB'", "'64 SLC (System Level Cache) of 1 MiB'", 'box label')
# 5. distance figure: the foot line named the wrong column for the proxies
sub("'Other mesh: the same range, lowest near column 5, which is where the proxies of those homes sit on this mesh.'", "'Other mesh: the same range. The lowest cell is (5,5) at 19.1 ns. Its proxy is at (1,2) of mesh 0, the crosspoint of CPU 0.'", 'dist footer')
# 6. new figure script, appended to the line that ends the distance-map script
i = one(lambda l: "Other mesh: the same range." in l, 'dist footer 2')
assert out[i + 1] == '})();', out[i + 1]
out[i + 1] = '})();' + ' ' + js('fig.js')
# 7. statements elsewhere that the new text would contradict
sub("A chain is built and walked once on one core, so every line sits in that core's chiplet.", "A chain is built and walked once on one core. After that walk the lines are expected to be in that core's chiplet.", 'five cases a')
sub("The first walk from the other chiplet pays the trip across; the second walk finds the lines in the reader's own-mesh slices.", "The first walk from the other chiplet is 56 to 59 ns slower for each load. The second walk is close to the walks of the controls, where one core builds and walks. The run did not count where the lines are before each walk. So the slice columns of rows 3 and 4 give the expected state.", 'five cases b')
sub("The 85 to 88 ns first walk mixes lines held in the other chiplet's slices with lines still in the builder's L2 (about one eighth), and mixes the two home cases (proxy miss with the data at the remote home, and own-home miss with the data in the remote proxy).", "The 85 to 88 ns first walk is expected to mix lines held in the other chiplet's slices with lines still in the builder's L2 (about one eighth, not counted). It is also expected to mix the two home cases. Hypothesis: a proxy miss with the data at the remote home, and an own-home miss with the data in the remote proxy.", 'open item first walk')
sub("The 2.6 to 4 ns residual of the second walk is also unexplained.</li>", "The 2.6 to 4.1 ns residual of the second walk is also unexplained. The builder writes every line. So the test covers modified lines only.</li>", 'open item residual')
i = one(lambda l: l.startswith('<li><b>Slice occupancy limits.</b>'), 'open item occupancy')
assert out[i].endswith('</li>')
out[i] += flat('openitem.html')
i = one(lambda l: l.startswith('<div class="sub">Latency and bandwidth of L1, L2, the SLC'), 'change record')
assert out[i].endswith('</div>')
out[i] = out[i][:-len('</div>')] + flat('record.html') + '</div>'
assert len(out) == len(src)
open(sys.argv[2], 'w').write('\n'.join(out))
print('lines', len(out), 'changed', [k + 1 for k in range(len(out)) if out[k] != src[k]])
