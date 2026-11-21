#!/usr/bin/env python3
"""Build kernels-result.html from one-thread.csv and threads120.csv (same folder).

This generator belongs to the run kernels-20261113T181222Z. The charts, the tables and the list
"What the data shows" are computed. The Short version, the two sentences under the charts, the
"Conditions" and the counts of processes and repetitions are typed text for that run: check and
rewrite them before this script is used for another run."""
import html, statistics as st
from summarize import load
one, loads1 = load('one-thread.csv'); many, loads120 = load('threads120.csv')
SIZES = [('32K', '32 KiB', 'fits L1'), ('1M', '1 MiB', 'fits L2'), ('8M', '8 MiB', 'fits the SLC'), ('1G', '1 GiB', 'DRAM')]
KS = [('read', 'asmread'), ('write', 'asmwrite'), ('copy', 'asmcopy')]
C_OLD, C_NEW, C_ASM = '#eb6834', '#2a78d6', '#1baf7a'
def chart(d, rows, xmax, step, label, aria):
    W = 760; L = 170; R = 40; PW = W - L - R; rh = 40; top = 34; H = top + len(rows) * rh + 50
    x = lambda v: L + v / xmax * PW
    o = [f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{aria}">']
    for t in range(0, xmax + 1, step):
        o.append(f'<line x1="{x(t):.1f}" y1="{top-8}" x2="{x(t):.1f}" y2="{H-46}" stroke="#e6e5e0"/>')
        o.append(f'<text x="{x(t):.1f}" y="{H-30}" text-anchor="middle" class="ax">{t}</text>')
    o.append(f'<text x="{L+PW/2}" y="{H-10}" text-anchor="middle" class="ax">{label}</text>')
    for i, (b, name, k, ka, sep) in enumerate(rows):
        y = top + i * rh + rh / 2
        if sep and i: o.append(f'<line x1="10" y1="{y-rh/2:.1f}" x2="{W-R}" y2="{y-rh/2:.1f}" stroke="#c9c8c2"/>')
        vo = max(d[b, k, 'bw_old']); vn = max(d[b, k, 'bw_new']); va = max(d[b, ka, 'bw_new'])
        o.append(f'<text x="{L-10}" y="{y+4:.1f}" text-anchor="end" class="lab">{name}</text>')
        o.append(f'<line x1="{x(vo):.1f}" y1="{y}" x2="{x(vn):.1f}" y2="{y}" stroke="#8a8984" stroke-width="2"/>')
        o.append(f'<path d="M{x(va):.1f},{y-9} l7,9 l-7,9 l-7,-9 Z" fill="none" stroke="{C_ASM}" stroke-width="2"><title>{ka}, {name}: best {va:.2f} GB/s</title></path>')
        o.append(f'<text x="{x(va):.1f}" y="{y-13:.1f}" text-anchor="middle" class="val">asm {va:.1f}</text>')
        o.append(f'<circle cx="{x(vo):.1f}" cy="{y}" r="5" fill="{C_OLD}" stroke="#fcfcfb" stroke-width="2"><title>old {k}, {name}: best {vo:.2f} GB/s</title></circle>')
        o.append(f'<circle cx="{x(vn):.1f}" cy="{y}" r="5" fill="{C_NEW}" stroke="#fcfcfb" stroke-width="2"><title>new {k}, {name}: best {vn:.2f} GB/s</title></circle>')
        lo, hi = sorted((vo, vn))
        if hi - lo > xmax * 0.09:
            o.append(f'<text x="{x(vo) + (-9 if vo < vn else 9):.1f}" y="{y+4:.1f}" text-anchor="{"end" if vo < vn else "start"}" class="val">old {vo:.1f}</text>')
            o.append(f'<text x="{x(vn) + (11 if vo < vn else -11):.1f}" y="{y+4:.1f}" text-anchor="{"start" if vo < vn else "end"}" class="val">new {vn:.1f} ({(vn/vo-1)*100:+.0f} %)</text>')
        else:
            o.append(f'<text x="{x(hi)+11:.1f}" y="{y+4:.1f}" class="val">old {vo:.1f}, new {vn:.1f} ({(vn/vo-1)*100:+.1f} %)</text>')
    o.append(f'<line x1="{L}" y1="{top-8}" x2="{L}" y2="{H-46}" stroke="#52514e"/></svg>')
    return '\n'.join(o)
rows1 = [(b, f'{k}, {name}', k, ka, j == 0) for k, ka in KS for j, (b, name, _) in enumerate(SIZES)]
rows120 = [('256M', f'{k}, 120 threads', k, ka, False) for k, ka in KS]
svg1 = chart(one, rows1, 240, 20, 'rate, GB/s (best of 12 repetitions), one thread', 'Old and new C kernels and asm kernels, one thread')
svg120 = chart(many, rows120, 500, 50, 'total rate of 120 threads, GB/s (best of 6 repetitions), 256 MiB per thread', 'Old and new C kernels and asm kernels, 120 threads')
def table(d, sizes):
    tr = ''
    for k, ka in KS:
        for b, name, _ in sizes:
            o = d[b, k, 'bw_old']; n = d[b, k, 'bw_new']; a = d[b, ka, 'bw_new']; ao = d[b, ka, 'bw_old']
            tr += (f'<tr><td>{k}</td><td>{name}</td><td>{max(o):.2f}</td><td>{st.median(o):.2f}</td><td>{max(n):.2f}</td><td>{st.median(n):.2f}</td>'
                   f'<td>{min(n):.2f}</td><td>{max(a):.2f}</td><td>{st.median(a):.2f}</td><td>{(max(n)/max(o)-1)*100:+.1f} %</td><td>{(max(n)/max(a)-1)*100:+.2f} %</td><td>{(max(a)/max(ao)-1)*100:+.2f} %</td></tr>\n')
    return ('<div class="tw"><table><tr><th>kernel</th><th>buffer</th><th>old C best</th><th>old C median</th><th>new C best</th><th>new C median</th><th>new C lowest</th>'
            '<th>asm best</th><th>asm median</th><th>new C vs old C (best)</th><th>new C vs asm (best)</th><th>asm: new binary vs old binary (best)</th></tr>\n' + tr + '</table></div>')
legend = (f'<span class="lg"><i style="background:{C_OLD}"></i>old C kernel</span><span class="lg"><i style="background:{C_NEW}"></i>new C kernel</span>'
          f'<span class="lg"><i style="border:2px solid {C_ASM};transform:rotate(45deg);border-radius:0;width:8px;height:8px"></i>asm kernel (same binary as the new C kernel)</span>')
page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>New C kernels of bandwidth.c, measured on CRB</title>
<style>
:root{{color-scheme:light}}
body{{background:#fcfcfb;color:#0b0b0b;font:16px/1.5 system-ui,"IBM Plex Sans",sans-serif;max-width:860px;margin:24px auto;padding:0 16px}}
h1{{font-size:24px}} h2{{font-size:18px;margin-top:28px}}
.ax{{font-size:11px;fill:#52514e}} .lab{{font-size:12px;fill:#0b0b0b}} .val{{font-size:11px;fill:#0b0b0b}}
.lg{{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e}} .lg i{{width:12px;height:12px;border-radius:50%;margin-right:7px;display:inline-block;box-sizing:border-box}}
table{{border-collapse:collapse;font-size:13px;margin:8px 0}} td,th{{border-bottom:1px solid #e6e5e0;padding:4px 8px;text-align:right;vertical-align:bottom}} td:nth-child(-n+2),th:nth-child(-n+2){{text-align:left}}
.take{{background:#f1f0ec;padding:10px 14px;border-radius:6px}} code{{font-size:14px}} .tw{{overflow-x:auto}}
</style></head><body>
<h1>New C kernels of bandwidth.c, measured on CRB</h1>
<p class="take"><b>Short version.</b> The three C kernels of <code>bandwidth.c</code> (read, write, copy) now use the same algorithm as the hand-written asm kernels. With one thread, the best rate of each new C kernel differs from the best rate of the asm kernel of the same binary by -2.91 % to +0.41 % over the 12 cells (3 kernels x 4 buffer sizes). With 120 threads and 256 MiB per thread, the best read rate changed from 466.65 GB/s (old C kernel) to 304.05 GB/s (new C kernel).</p>
<h2>Words used here</h2>
<ul>
<li><b>CRB</b>: the Arm Phoenix Reference Server, 128 cores, where all runs were made.</li>
<li><b>Kernel</b>: the timed loop of the benchmark <code>bandwidth.c</code>. It is not the Linux kernel.</li>
<li><b>Old C kernel</b>: <code>k_read</code>, <code>k_write</code> or <code>k_copy</code> as it was before 2026-11-13 (binary <code>bw_old</code>).</li>
<li><b>New C kernel</b>: the same function after the rewrite with NEON intrinsics (binary <code>bw_new</code>). NEON is the 128-bit vector instruction set of AArch64.</li>
<li><b>asm kernel</b>: <code>k_asmread</code>, <code>k_asmwrite</code> or <code>k_asmcopy</code>, written in inline assembly. Their source is the same in both binaries.</li>
<li><b>Rate</b>: bytes moved per second, in GB/s (1 GB = 10<sup>9</sup> bytes). The copy kernels count the bytes read plus the bytes written.</li>
<li><b>Repetition</b>: one timed interval of at least 0.5 s. Each process makes 3 repetitions.</li>
<li><b>Best, median, lowest</b>: the highest, the middle and the lowest rate of the repetitions of one cell.</li>
<li><b>L1, L2, SLC</b>: the three cache levels of a core. SLC is the system-level cache (L3), shared by all cores.</li>
<li><b>DRAM</b>: main memory.</li>
<li><b>Load</b>: the Linux 1-minute load average, the average count of tasks that run or wait to run.</li>
</ul>
<h2>One thread</h2>
<p>{legend}</p>
{svg1}
<p class="take">With one thread, the blue dot (new C kernel) is within 3.0 % of the green diamond (asm kernel of the same binary) in every row. The orange dot (old C kernel) is never above the blue dot.</p>
{table(one, SIZES)}
<h2>120 threads, 256 MiB per thread</h2>
<p>{legend}</p>
{svg120}
<p class="take">With 120 threads the new read kernel is at the asm read kernel, and both are below the old read kernel. This run does not show the cause.</p>
{table(many, [('256M', '256 MiB', '')])}
<h2>What the data shows</h2>
<ul>
<li>One thread, new C kernel against asm kernel: the best rates differ by {min((max(one[b,k,'bw_new'])/max(one[b,ka,'bw_new'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.2f} % to {max((max(one[b,k,'bw_new'])/max(one[b,ka,'bw_new'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.2f} % over the 12 cells.</li>
<li>One thread, new C kernel against old C kernel: the best rate changes by {min((max(one[b,k,'bw_new'])/max(one[b,k,'bw_old'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.1f} % to {max((max(one[b,k,'bw_new'])/max(one[b,k,'bw_old'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.1f} % over the 12 cells.</li>
<li>Control: the asm kernels have the same source in both binaries. With one thread their best rates differ between the binaries by {min((max(one[b,ka,'bw_new'])/max(one[b,ka,'bw_old'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.2f} % to {max((max(one[b,ka,'bw_new'])/max(one[b,ka,'bw_old'])-1)*100 for k,ka in KS for b,_,_ in SIZES):+.2f} %. This run does not establish whether a C-kernel difference of similar size is repeatable.</li>
<li>120 threads: the same control differs by {min((max(many['256M',ka,'bw_new'])/max(many['256M',ka,'bw_old'])-1)*100 for k,ka in KS):+.2f} % to {max((max(many['256M',ka,'bw_new'])/max(many['256M',ka,'bw_old'])-1)*100 for k,ka in KS):+.2f} %. Each 120-thread cell has only 2 processes per binary.</li>
<li>120 threads, read: old C {max(many['256M','read','bw_old']):.2f} GB/s, new C {max(many['256M','read','bw_new']):.2f} GB/s, asm {max(many['256M','asmread','bw_new']):.2f} GB/s (best of 6). The change of {(max(many['256M','read','bw_new'])/max(many['256M','read','bw_old'])-1)*100:+.1f} % is larger than the control difference.</li>
<li>120 threads, write: old C best {max(many['256M','write','bw_old']):.2f} GB/s and median {st.median(many['256M','write','bw_old']):.2f} GB/s. New C best {max(many['256M','write','bw_new']):.2f} GB/s and median {st.median(many['256M','write','bw_new']):.2f} GB/s. The repetitions of the write kernels range from {min(min(many['256M',k,b]) for k in ('write','asmwrite') for b in ('bw_old','bw_new')):.2f} to {max(max(many['256M',k,b]) for k in ('write','asmwrite') for b in ('bw_old','bw_new')):.2f} GB/s.</li>
</ul>
<h2>Limits of this run</h2>
<ul>
<li>Each one-thread cell has 4 processes (2 rounds, CPUs 0 and 2) of 3 repetitions. The 3 repetitions of one process use the same buffer, so they are not independent samples.</li>
<li>Each 120-thread cell has 2 processes of 3 repetitions, at one buffer size.</li>
<li>No hardware counter was read. The run does not show why a rate is what it is.</li>
<li>The page size that each process received was not recorded. Transparent huge pages were set to "always".</li>
<li>The color palette is three slots of the dataviz skill. Its validator script was not run (no <code>node</code> on this machine).</li>
</ul>
<h2>Conditions</h2>
<ul>
<li>Host CRB, gcc 14.2.0, flags <code>-O3 -march=native -fno-tree-loop-distribute-patterns -pthread -Wall -Wextra -std=gnu11</code> [Ref1].</li>
<li>Load before the run: 0.03. No user was logged in [Ref1].</li>
<li>Load at the start of the one-thread processes: {min(loads1):.2f} to {max(loads1):.2f} [Ref2]. Our own processes are part of this load.</li>
<li>Load at the start of the 120-thread processes: {min(loads120):.2f} to {max(loads120):.2f} [Ref3]. Every process after the first one followed a process with 120 threads. Hypothesis: this load comes from our own processes. The process list was recorded only before the run, so no file confirms it.</li>
<li>One process per binary and kernel. Round 2 reversed the order of the binaries and of the kernels [Ref4].</li>
<li>The marker file of Jeremy's runs (<code>/tmp/positron-perf.RUNNING</code>) was checked before every timed process [Ref4]. His block was announced to end at 18:10 UTC in the Slack channel #phoenix-crb (not saved as a file). The run started at 18:12:22 UTC [Ref1].</li>
</ul>
<h2>References</h2>
<ul>
<li>[Ref1] <code>probe.txt</code> in this folder: host, load, compiler, flags, sha256 digests, machine code of all kernels.</li>
<li>[Ref2] <code>one-thread.csv</code> in this folder: 192 processes.</li>
<li>[Ref3] <code>threads120.csv</code> in this folder: 24 processes.</li>
<li>[Ref4] <code>crb/tmp/agent-scratch/kernels-2026-11-13/run_kernels.sh</code>: the run script.</li>
<li>[Ref5] <code>summarize.py</code> and <code>make_html.py</code> in this folder: they compute every rate, every percentage outside the Short version and both process-start load ranges from the two csv files. The numbers in the Short version, the counts of processes and repetitions, the load before the run and the times are typed text in <code>make_html.py</code>.</li>
</ul>
</body></html>'''
open('kernels-result.html', 'w').write(page)
