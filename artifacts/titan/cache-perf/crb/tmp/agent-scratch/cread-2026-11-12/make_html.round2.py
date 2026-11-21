#!/usr/bin/env python3
"""Build cread-result.html from cread.csv (same folder)."""
import re, statistics as st, html
rows=[];ctx=None;loads=[]
for l in open('cread.csv'):
    l=l.strip()
    m=re.match(r'-- round (\d) cpu (\d+) bytes (\S+) load (\S+)',l)
    if m: ctx=m.groups(); loads.append(float(ctx[3])); continue
    p=l.split(',')
    if p[0] in('read','asmread','cread') and p[3]!='best':
        rows.append((ctx[2],p[0],float(p[6])))
SIZES=[('32K','32 KiB','fits L1'),('1M','1 MiB','fits L2'),('8M','8 MiB','fits the SLC'),('1G','1 GiB','DRAM')]
K=[('asmread','asm loop (k_asmread)','#2a78d6'),('cread','C loop, loads only (k_cread)','#eb6834'),('read','C loop with 16 sums (k_read)','#1baf7a')]
S={(b,k):[r[2] for r in rows if r[0]==b and r[1]==k] for b,_,_ in SIZES for k,_,_ in K}
assert all(len(v)==12 for v in S.values())
W=760;L=150;R=70;PW=W-L-R;XMAX=140;bh=14;gap=4;gh=3*(bh+gap)+22
H=40+len(SIZES)*gh+46
x=lambda v:L+v/XMAX*PW
o=[f'<svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="Read rate of three loops at four buffer sizes">']
for t in range(0,141,20):
    o.append(f'<line x1="{x(t):.1f}" y1="30" x2="{x(t):.1f}" y2="{H-44}" stroke="#e6e5e0" stroke-width="1"/>')
    o.append(f'<text x="{x(t):.1f}" y="{H-28}" text-anchor="middle" class="ax">{t}</text>')
o.append(f'<text x="{L+PW/2}" y="{H-8}" text-anchor="middle" class="ax">read rate, GB/s (best of 12 repetitions), one thread</text>')
lim=134.4
o.append(f'<line x1="{x(lim):.1f}" y1="22" x2="{x(lim):.1f}" y2="{H-44}" stroke="#52514e" stroke-width="1" stroke-dasharray="4 3"/>')
o.append(f'<text x="{x(lim)-4:.1f}" y="18" text-anchor="end" class="ax">3 loads of 16 B per cycle = 134.4 GB/s (est., assuming 2.8 GHz)</text>')
y=40
for b,name,lvl in SIZES:
    o.append(f'<text x="{L-10}" y="{y+bh+gap+4}" text-anchor="end" class="lab">{name}</text>')
    o.append(f'<text x="{L-10}" y="{y+bh+gap+20}" text-anchor="end" class="ax">{lvl}</text>')
    for i,(k,kn,c) in enumerate(K):
        v=max(S[b,k]);yy=y+i*(bh+gap)
        o.append(f'<path d="M{L},{yy} H{x(v)-4:.1f} a4,4 0 0 1 4,4 v{bh-8} a4,4 0 0 1 -4,4 H{L} Z" fill="{c}"><title>{html.escape(kn)}, {name}: best {v:.2f} GB/s, median {st.median(S[b,k]):.2f}, lowest {min(S[b,k]):.2f}</title></path>')
        o.append(f'<text x="{x(v)+6:.1f}" y="{yy+bh-3}" class="val">{v:.1f}</text>')
    y+=gh
o.append(f'<line x1="{L}" y1="30" x2="{L}" y2="{H-44}" stroke="#52514e" stroke-width="1"/></svg>')
svg='\n'.join(o)
legend=''.join(f'<span class="lg"><i style="background:{c}"></i>{html.escape(kn)}</span>' for _,kn,c in K)
tr=''
for b,name,lvl in SIZES:
    for k,kn,_ in K:
        v=S[b,k];mx=max(v)
        tr+=f'<tr><td>{name}</td><td>{html.escape(kn)}</td><td>{mx:.2f}</td><td>{st.median(v):.2f}</td><td>{min(v):.2f}</td><td>{mx/2.8/16:.2f}</td></tr>\n'
ratio=''.join(f'<tr><td>{name}</td><td>{max(S[b,"cread"])/max(S[b,"asmread"]):.4f}</td><td>{st.median(S[b,"cread"])/st.median(S[b,"asmread"]):.4f}</td></tr>' for b,name,_ in SIZES)
page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>C loop that only loads, measured on CRB</title>
<style>
:root{{color-scheme:light}}
body{{background:#fcfcfb;color:#0b0b0b;font:16px/1.5 system-ui,"IBM Plex Sans",sans-serif;max-width:820px;margin:24px auto;padding:0 16px}}
h1{{font-size:24px}} h2{{font-size:18px;margin-top:28px}}
.ax{{font-size:11px;fill:#52514e}} .lab{{font-size:13px;fill:#0b0b0b;font-weight:600}} .val{{font-size:12px;fill:#0b0b0b}}
.lg{{display:inline-flex;align-items:center;margin-right:18px;font-size:13px;color:#52514e}} .lg i{{width:12px;height:12px;border-radius:3px;margin-right:6px;display:inline-block}}
table{{border-collapse:collapse;font-size:14px;margin:8px 0}} td,th{{border-bottom:1px solid #e6e5e0;padding:4px 10px;text-align:right}} td:nth-child(-n+2),th:nth-child(-n+2){{text-align:left}}
.take{{background:#f1f0ec;padding:10px 14px;border-radius:6px}} code{{font-size:14px}} .tw{{overflow-x:auto}}
</style></head><body>
<h1>C loop that only loads, measured on CRB</h1>
<p class="take"><b>Short version.</b> A read loop written in C that only loads (<code>k_cread</code>) reads at nearly the same rate as the hand-written asm loop (<code>k_asmread</code>) at all four buffer sizes. The best rates differ by less than 0.7 %. The old C loop with 16 sums (<code>k_read</code>) reaches about half of that rate at 32 KiB.</p>
<h2>Words used here</h2>
<ul>
<li><b>CRB</b>: the Arm Phoenix Reference Server, 128 cores, where all runs were made.</li>
<li><b>k_asmread</b>: the read loop written by hand in assembly. One pass runs 8 <code>ldp q</code> instructions (16 loads of 16 B, 256 B), one add, one compare and one branch.</li>
<li><b>k_cread</b>: the new loop in C. It loads 16 values of 16 B and names them in an empty asm statement. In the measured binary gcc 14.2 compiles one pass to 11 instructions of the same kinds and counts as k_asmread [Ref2].</li>
<li><b>k_read</b>: the old loop in C. It adds every 8 B word into one of 16 sums. One pass of 128 B runs 4 <code>ldp q</code> and 8 vector adds [Ref2].</li>
<li><b>SLC</b>: system level cache, the cache that all cores share. Linux lists it as L3.</li>
<li><b>GB</b>: 10<sup>9</sup> bytes. <b>KiB, MiB, GiB</b>: 2<sup>10</sup>, 2<sup>20</sup>, 2<sup>30</sup> bytes.</li>
</ul>
<h2>Result</h2>
<div>{legend}</div>
{svg}
<p class="take">The blue bar and the orange bar have nearly the same length in every group (the rates differ by less than 0.7 %). The green bar (the loop with sums) is shorter in every group.</p>
<div class="tw"><table><tr><th>Buffer</th><th>Loop</th><th>Best, GB/s</th><th>Median, GB/s</th><th>Lowest, GB/s</th><th>Loads of 16 B per cycle (est., from the best rate, assuming 2.8 GHz)</th></tr>
{tr}</table></div>
<p>Each row has 12 repetitions: 2 CPUs (0 and 2), 2 rounds, 3 repetitions of at least 0.5 s [Ref1].</p>
<div class="tw"><table><tr><th>Buffer</th><th>k_cread / k_asmread, best</th><th>k_cread / k_asmread, median</th></tr>{ratio}</table></div>
<h2>What the data shows</h2>
<ul>
<li><b>At 32 KiB the best rates of both loops that only load are 133.2 to 133.3 GB/s, which is 2.97 loads of 16 B per cycle (est., assuming 2.8 GHz).</b> This run measured neither the clock nor cycles. The best rate of the loop with sums is 66.76 GB/s, which is 1.49 (est., assuming 2.8 GHz) [Ref1].</li>
<li><b>At 1 MiB and 8 MiB the rates of the two loops that only load are still nearly equal (they differ by less than 0.2 %).</b> The loop with sums stays at about 67 GB/s at 32 KiB, 1 MiB and 8 MiB [Ref1]. So up to 8 MiB its rate does not depend on the buffer size.</li>
<li><b>At 1 GiB the best rate of the loop with sums (28.73 GB/s) is 7.1 % below the best rate of k_cread (30.93 GB/s) and 6.5 % below that of k_asmread (30.74 GB/s)</b> [Ref1].</li>
<li><b>At 32 KiB this run gives rates close to those of the report.</b> The report gives 132.7 GB/s for the asm loop and 66.8 GB/s for the loop with sums, measured on 2026-10-30 with an earlier build [Ref3]. In this run the best of 12 repetitions was 133.21 and 66.76 GB/s [Ref1].</li>
</ul>
<h2>Limits of this run</h2>
<ul>
<li><b>Order.</b> In every process the loops ran in the order k_read, k_asmread, k_cread. At 1 GiB the best rate of k_cread was 0.26 % to 0.81 % above the best rate of k_asmread in each of the four processes [Ref1]. An effect of the order is not excluded. A run with the order reversed would resolve it.</li>
<li><b>Low repetitions.</b> At 32 KiB the three repetitions of k_cread in the first process (CPU 0, round 1) gave 131.84 to 131.95 GB/s, about 1 % below the other nine. At 8 MiB on CPU 2, round 1, the six repetitions of the two loops that only load gave 67.85 to 68.31 GB/s, against 69.75 to 71.15 GB/s in the other three processes. At 8 MiB the first repetition of k_asmread was also low in two more processes (70.01 and 69.75 GB/s). The cause was not examined.</li>
<li><b>One thread only.</b> No run with several threads was made.</li>
<li><b>The loop start addresses differ.</b> The loop of k_cread starts at 0x1e24 and the loop of k_asmread at 0x1d1c [Ref2]. The rates are still nearly equal in this run.</li>
<li><b>Not a test of hypotheses A and B of the report.</b> k_cread has no vector adds. The loop with loads and adds in a 3:2 ratio is still not run.</li>
</ul>
<h2>Conditions</h2>
<ul>
<li>Host load (1-minute load average of Linux) before the run: {loads[0]:.2f}, with no logins [Ref2]. The highest load recorded before a process was {max(loads):.2f} [Ref1]. This benchmark ran one busy thread during that time. No file shows what else ran.</li>
<li>The run script stops if the file <code>/tmp/positron-perf.RUNNING</code> exists, and it checks before every process [Ref4].</li>
<li>A check by hand in the login before the run (06:04 UTC) showed no process of the account positron-perf. Its output was not saved, so no file holds this observation.</li>
<li>Run started 2026-11-13 06:05:10 UTC and ended 06:06:25 UTC [Ref2].</li>
<li>gcc 14.2.0, flags <code>-O3 -march=native -fno-tree-loop-distribute-patterns -pthread</code>, the flags of <code>bench/Makefile</code> [Ref2].</li>
<li>The binary is a scratch copy of <code>bench/bandwidth.c</code> with the kernel <code>cread</code> added. <code>bench/bandwidth.c</code> was not changed [Ref4].</li>
<li>The color palette is the first three slots of the dataviz skill. Its validator script could not be run here (no <code>node</code> on this machine).</li>
</ul>
<h2>References</h2>
<ul>
<li>[Ref1] <code>crb/results/cread-20261113T060510Z/cread.csv</code></li>
<li>[Ref2] <code>crb/results/cread-20261113T060510Z/probe.txt</code> (load, compiler, checksums, objdump of the three loops in the measured binary)</li>
<li>[Ref3] <code>crb/crb-memory-hierarchy.html</code>, section "The read loop compiled from C: 1.5 loads per cycle"</li>
<li>[Ref4] <code>crb/tmp/agent-scratch/cread-2026-11-12/bandwidth_cread.c</code> and <code>run_cread.sh</code></li>
</ul>
</body></html>'''
open('cread-result.html','w').write(page)
print('ok',len(page))
