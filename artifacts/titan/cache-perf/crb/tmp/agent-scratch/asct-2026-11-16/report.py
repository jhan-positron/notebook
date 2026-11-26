#!/usr/bin/env python3
"""report.py FACTS.json BASELINE.json NOTES.json OUT.html: build ASCT-cross-check.html.
FACTS comes from facts.py, BASELINE from baseline.py. NOTES holds the text blocks that a person (or the agent)
writes after reading the facts: short version, takeaways, verdict sentences, run notes. Every number in a
NOTES text is checked by check_notes.py against FACTS before the page is delivered."""
import json
import sys

import figs
from svgchart import ASCT, CONTEXT, INK2, NEW, OLD, esc

F = json.load(open(sys.argv[1]))
B = json.load(open(sys.argv[2]))
N = json.load(open(sys.argv[3]))
MI = 1 << 20

CSS = '''
:root{--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1000px;margin:0 auto;padding:28px 16px 80px}
h1{font-size:26px;line-height:1.25;margin:0 0 6px}
h2{font-size:20px;margin:44px 0 10px;padding-top:14px;border-top:1px solid var(--grid)}
h3{font-size:16px;margin:26px 0 8px}
p{margin:8px 0}
ul{margin:8px 0;padding-left:22px}
li{margin:4px 0}
.sub{color:var(--ink2);margin:0 0 18px}
.short{background:var(--surface);border:1px solid var(--grid);border-left:4px solid var(--ink2);border-radius:6px;padding:12px 16px;margin:16px 0}
.short h2{border:0;margin:0 0 6px;padding:0;font-size:16px}
figure{margin:18px 0;background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:12px 12px 10px;overflow-x:auto}
figure svg{min-width:720px;display:block}
figcaption{color:var(--ink2);font-size:13.5px;margin-top:8px}
figcaption b{color:var(--ink)}
.tw{overflow-x:auto;margin:12px 0}
table{border-collapse:collapse;font-size:13px;background:var(--surface);min-width:100%}
th,td{border:1px solid var(--grid);padding:4px 8px;text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
th{background:#f1f0ec;color:var(--ink2);font-weight:600;white-space:normal}
td.l,th.l{text-align:left;white-space:normal}
td.s,th.s{text-align:left}
td.hl{background:#f3f1e6}
caption{caption-side:top;text-align:left;color:var(--ink2);font-size:13px;padding:0 0 6px}
details{background:var(--surface);border:1px solid var(--grid);border-radius:6px;padding:8px 14px;margin:12px 0}
summary{cursor:pointer;font-weight:600}
code,pre{font-family:ui-monospace,"DejaVu Sans Mono",Menlo,monospace;font-size:12.5px}
pre{background:var(--surface);border:1px solid var(--grid);border-radius:6px;padding:10px 12px;overflow-x:auto;line-height:1.4}
.key{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:baseline}
.v{display:inline-block;border-radius:4px;padding:1px 7px;font-size:12.5px;font-weight:600;border:1px solid var(--axis);background:var(--surface)}
.hit{cursor:default;outline:none}
.hit:focus{stroke:var(--ink2);stroke-width:1.5}
#tip{position:fixed;display:none;pointer-events:none;background:#0b0b0b;color:#fff;font-size:12.5px;line-height:1.35;padding:6px 9px;border-radius:5px;max-width:340px;z-index:9}
ol.refs{font-size:13.5px;padding-left:0;list-style:none}
ol.refs li{margin:5px 0}
'''

JS = '''
(function(){var t=document.getElementById('tip');
function show(e,el){t.textContent=el.getAttribute('data-tip');t.style.display='block';
 var x=(e.clientX||el.getBoundingClientRect().left)+14,y=(e.clientY||el.getBoundingClientRect().top)+14;
 if(x+t.offsetWidth>innerWidth-8)x=innerWidth-t.offsetWidth-8;if(y+t.offsetHeight>innerHeight-8)y=y-t.offsetHeight-28;
 t.style.left=x+'px';t.style.top=y+'px';}
document.querySelectorAll('.hit').forEach(function(el){
 el.addEventListener('pointermove',function(e){show(e,el)});el.addEventListener('pointerleave',function(){t.style.display='none'});
 el.addEventListener('focus',function(e){show(e,el)});el.addEventListener('blur',function(){t.style.display='none'});});})();
'''


def lab(b):
    return F['labels'][str(b)]


def cell(v, nd=1):
    return '' if v is None else f'{v:.{nd}f}'


def rng(d, nd=1):
    if not d:
        return '<td></td>'
    return f'<td title="range {d["lo"]:.2f} to {d["hi"]:.2f}, n={d["n"]}">{d["median"]:.{nd}f}</td>'


def table_sizes():
    v0 = dict(B['vendor']['a0_numa2_ddr_7200']['sweep'])
    v1 = dict(B['vendor']['a1_numa2_ddr_8000']['sweep'])
    h = ('<div class="tw"><table><caption>Table 1. Read rate of one core, GB/s (GB = 10<sup>9</sup> bytes). Median of the processes. '
         'Point at a cell to see the range and the count. Empty cell: no run exists.</caption>'
         '<tr><th class="s" rowspan="2">Buffer size</th><th colspan="3">CRB, CPU 2</th><th colspan="3">CRB, CPU 41</th><th colspan="2">ASCT read, Arm reference machines</th></tr>'
         '<tr><th>old read</th><th>new read</th><th>ASCT read</th><th>old read</th><th>new read</th><th>ASCT read</th><th>A0</th><th>A1</th></tr>')
    for b in F['sizes']:
        hl = ' hl' if b == 8 * MI else ''
        row = f'<tr><td class="s{hl}">{lab(b)}</td>'
        for cpu in F['cpus']:
            c = F['one'][str(cpu)]
            new = c['new'].get(str(b)) or c['newc'].get(str(b))
            row += rng(c['old'].get(str(b))) + rng(new) + rng(c['asct'].get(str(b)))
        row += f'<td>{cell(v0.get(b))}</td><td>{cell(v1.get(b))}</td></tr>'
        h += row
    return h + '</table></div>'


CNT_COLS = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l1d_cache_refill', 'L1 refills'), ('l2d_cache_refill', 'L2 refills'),
            ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'), ('ll_cache_miss_rd', 'last-level misses'),
            ('l1d_cache_hwprf', 'L1 hw prefetch'), ('l2d_cache_hwprf', 'L2 hw prefetch'), ('l2d_cache_l1hwprf', 'L2 access by L1 pf'),
            ('l2d_cache_refill_l1hwprf', 'L2 refill by L1 pf'), ('bus_access_rd', 'bus reads'), ('l2d_cache_wb', 'L2 write-backs'),
            ('stall_backend_mem', 'stall cycles, memory'), ('dtlb_walk', 'page-table walks')]


def table_counters(cpu):
    c = F['one'][str(cpu)]['cnt']
    cols = [(n, t) for n, t in CNT_COLS if any(n in c.get(str(b), {}) for b in F['sizes'])]
    h = (f'<div class="tw"><table><caption>Table 2{"a" if cpu == 2 else "b"}. ASCT read loop on CPU {cpu}: core counters per 64-byte line of the measured phase, '
         'user mode. Median of the counted processes.</caption><tr><th class="s">Buffer size</th><th>rate, GB/s</th>' + ''.join(f'<th>{esc(t)}</th>' for _, t in cols) + '</tr>')
    for b in F['sizes']:
        k = c.get(str(b))
        if not k:
            continue
        hl = ' hl' if b == 8 * MI else ''
        h += f'<tr><td class="s{hl}">{lab(b)}</td><td>{k["_rate"]:.1f}</td>' + ''.join(f'<td>{cell(k.get(n), 3)}</td>' for n, _ in cols) + '</tr>'
    return h + '</table></div>'


def table_prefetch_rule():
    names = F.get('RA3_counted', [])
    h = ('<div class="tw"><table><caption>Table 3. Rule R-A3: prefetch counters per line at 6, 8 and 12 MiB. "Different" means that the 8 MiB value lies '
         'outside the range of the two neighbours, extended by 10 % of their mean.</caption>'
         '<tr><th class="l" rowspan="2">Counter</th><th colspan="4">CPU 2</th><th colspan="4">CPU 41</th><th rowspan="2">Different on both CPUs</th></tr>'
         '<tr><th>6 MiB</th><th>8 MiB</th><th>12 MiB</th><th>different</th><th>6 MiB</th><th>8 MiB</th><th>12 MiB</th><th>different</th></tr>')
    for n in names:
        row = f'<tr><td class="l"><code>{n}</code></td>'
        for cpu in F['cpus']:
            p = F['one'][str(cpu)]['prefetch'][n]
            row += f'<td>{p["v6"]:.3f}</td><td class="hl">{p["v8"]:.3f}</td><td>{p["v12"]:.3f}</td><td>{"yes" if p["different"] else "no"}</td>'
        row += f'<td>{"yes" if n in F["RA3_different"] else "no"}</td></tr>'
        h += row
    return h + '</table></div>'


def table_nops():
    ch = F['chip']
    h = ('<div class="tw"><table><caption>Table 5. ASCT read loop at 64+56 threads, 256 MiB per thread: total read rate against injected NOPs, GB/s. '
         'Total and sums: what ASCT prints, median of the processes. Lower bound: all bytes of a process divided by the time of its slowest thread. '
         'Thread: median thread of the mesh. Time: shortest and longest measured phase of a thread, seconds.</caption>'
         '<tr><th>Injected NOPs</th><th>processes</th><th>total</th><th>range of the total</th><th>lower bound</th><th>mesh 0 sum</th><th>mesh 1 sum</th>'
         '<th>thread, mesh 0</th><th>thread, mesh 1</th><th>time of a thread, s</th></tr>')
    for n in sorted(ch['nops'], key=int):
        v = ch['nops'][n]
        h += (f'<tr><td>{n}</td><td>{v["n"]}</td><td>{v["median"]:.1f}</td><td>{v["lo"]:.1f} to {v["hi"]:.1f}</td><td>{v["floor"]:.1f}</td><td>{v["mesh0"]:.1f}</td><td>{v["mesh1"]:.1f}</td>'
              f'<td>{v["thr0"][1]:.2f}</td><td>{v["thr1"][1]:.2f}</td><td>{v["sec"][0]:.2f} to {v["sec"][1]:.2f}</td></tr>')
    return h + '</table></div>'


def table_layouts():
    ch = F['chip']
    names = {'6400': ('64+0', '64+0'), '0056': ('0+56', '0+56'), '5656': ('56+56', '56+56')}
    h = ('<div class="tw"><table><caption>Table 6. Other thread layouts, 256 MiB per thread, total GB/s. ASCT columns: median (range, count of processes). The four right columns are the single intervals of 2026-11-15.</caption>'
         '<tr><th class="l">Layout</th><th>ASCT, 0 NOPs</th><th>ASCT, 20 NOPs</th><th>old read</th><th>new read</th><th>read_nop96</th><th>read_nop128</th></tr>')
    for lay, (nm, key) in names.items():
        a, b = ch['layouts'][lay].get('0'), ch['layouts'][lay].get('20')
        o = B['chip']['layouts'][key]
        h += (f'<tr><td class="l">{nm}</td>' + ''.join(f'<td>{x["median"]:.1f} ({x["lo"]:.1f} to {x["hi"]:.1f}, n={x["n"]})</td>' if x else '<td></td>' for x in (a, b))
              + ''.join(f'<td>{x:.1f}</td>' for x in o) + '</tr>')
    return h + '</table></div>'


CHIP_CNT = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l2d_cache_refill', 'L2 refills'), ('l1d_cache_refill', 'L1 refills'),
            ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'), ('ll_cache_miss_rd', 'last-level misses'),
            ('l2d_cache_hwprf', 'L2 hardware prefetch events'), ('l1d_cache_hwprf', 'L1 hardware prefetch events'),
            ('l2d_cache_l1hwprf', 'L2 accesses caused by the L1 prefetcher'), ('l2d_cache_refill_l1hwprf', 'L2 refills caused by the L1 prefetcher'),
            ('bus_access', 'bus accesses'), ('bus_access_rd', 'bus reads'), ('l2d_cache_wb', 'L2 write-backs'),
            ('l2_chi_cbusy0', 'responses with busy level 0'), ('l2_chi_cbusy1', 'responses with busy level 1'),
            ('l2_chi_cbusy2', 'responses with busy level 2'), ('l2_chi_cbusy3', 'responses with busy level 3'), ('l2_chi_cbusy_mt', 'busy, multi-threaded flag'),
            ('stall_backend_mem', 'stall cycles, memory'), ('stall_backend_l2d', 'stall cycles, L2'), ('stall_backend_l1d', 'stall cycles, L1'),
            ('stall_backend_membound', 'stall cycles, memory bound'), ('dtlb_walk', 'page-table walks'), ('l1d_cache_prfm', 'software prefetches')]


def table_chip_counters():
    cnt = F['chip'].get('cnt', {})
    keys = [k for k in ('6456.n0', '6456.n20', '6400.n0') if k in cnt]
    if not keys:
        return '<p>Insufficient data: no counted whole-chip run exists.</p>'
    names = {'6456.n0': '64+56, 0 NOPs', '6456.n20': '64+56, 20 NOPs', '6400.n0': '64+0, 0 NOPs'}
    h = ('<div class="tw"><table><caption>Table 7. ASCT read loop, whole chip: core counters per 64-byte line, median over the threads of a mesh '
         '(user mode, measured phase). The first row gives the total rate of the counted processes.</caption><tr><th class="l" rowspan="2">Counter (name on CRB)</th>')
    for k in keys:
        h += f'<th colspan="{1 if k == "6400.n0" else 2}">{names[k]}</th>'
    h += '</tr><tr>' + ''.join('<th>mesh 0</th>' + ('' if k == '6400.n0' else '<th>mesh 1</th>') for k in keys) + '</tr>'
    h += '<tr><td class="l">total rate of the counted processes, GB/s</td>'
    for k in keys:
        t = cnt[k]['totals'].values()
        h += f'<td colspan="{1 if k == "6400.n0" else 2}" style="text-align:center">{min(t):.0f} to {max(t):.0f}</td>'
    h += '</tr>'
    for n, title in CHIP_CNT:
        if not any(n in cnt[k]['ev'] for k in keys):
            continue
        row = f'<tr><td class="l">{esc(title)} (<code>{n}</code>)</td>'
        for k in keys:
            e = cnt[k]['ev'].get(n)
            row += f'<td>{cell(e["mesh0"] if e else None, 3)}</td>'
            if k != '6400.n0':
                row += f'<td>{cell(e["mesh1"] if e else None, 3)}</td>'
        h += row + '</tr>'
    return h + '</table></div>'


MESH_ROWS = [('hns_pocq_retry_all', 'home-node request retries'), ('hns_qos_pocq_occupancy_all', 'home-node queue occupancy'),
             ('hns_mc_retries_local_all', 'memory-controller retries'), ('ccra_chidat_stalls', 'gateway data stalls'),
             ('hns_cbusy11_all', 'home-node busy level 3'), ('mxp_e_req_txflit_stall', 'request-link stalls, east'),
             ('mxp_e_dat_txflit_stall', 'data-link stalls, east'), ('mxp_n_dat_txflit_stall', 'data-link stalls, north'),
             ('mxp_s_dat_txflit_stall', 'data-link stalls, south'), ('hns_mc_reqs_local_all', 'memory-controller requests'),
             ('hns_cache_miss_all', 'SLC misses'), ('hns_pocq_reqs_recvd_all', 'home-node requests received')]


def table_mesh_chip():
    tags = [t for t in N.get('mesh_chip_tags', []) if t in F['mesh']]
    if not tags:
        return '<p><b>Insufficient data.</b> ' + esc(N.get('mesh_chip_missing', 'No mesh-counter run of the whole chip exists.')) + '</p>'
    peer = B['chip']['mesh_per_line']
    h = ('<div class="tw"><table><caption>Table 9. Mesh counters per 64-byte line read, sum of both meshes, system-wide (root). '
         'ASCT columns: this work. Right columns: the loops of 2026-11-15 (run w120-RC1).</caption><tr><th class="l">Counter</th>')
    for t in tags:
        m = F['mesh'][t]
        h += f'<th>ASCT, {esc(N["mesh_tag_names"].get(t, t))}<br>{m["rate"]:.0f} GB/s</th>'
    h += '<th>new read<br>299 GB/s</th><th>read_nop96<br>470 GB/s</th><th>old read<br>468 GB/s</th></tr>'
    for n, title in MESH_ROWS:
        if not any(n in F['mesh'][t]['ev'] for t in tags) and n not in peer:
            continue
        row = f'<tr><td class="l">{esc(title)} (<code>{n}</code>)</td>'
        for t in tags:
            e = F['mesh'][t]['ev'].get(n)
            v = (e.get('mesh0', 0) + e.get('mesh1', 0)) if e and ('mesh0' in e or 'mesh1' in e) else None
            row += f'<td>{cell(v, 4)}</td>'
        p = peer.get(n)
        row += ''.join(f'<td>{x:.4g}</td>' for x in p) if p else '<td></td><td></td><td></td>'
        h += row + '</tr>'
    return h + '</table></div>'


SINGLE_MESH = [('hns_slc_sf_cache_access_all', 'SLC lookups'), ('hns_cache_miss_all', 'SLC misses'), ('hns_cache_fill_all', 'SLC fills'),
               ('hns_sf_hit_all', 'snoop-filter hits'), ('hns_pocq_reqs_recvd_all', 'home-node requests received'), ('hns_pocq_retry_all', 'home-node request retries'),
               ('hns_mc_reqs_local_all', 'memory-controller requests'), ('hns_slc_eviction_all_all', 'SLC evictions'), ('hns_seq_hit', 'sequential-stream hits'),
               ('hns_cbusy00_all', 'busy level 0'), ('hns_cbusy01_all', 'busy level 1'), ('hns_cbusy10_all', 'busy level 2'), ('hns_cbusy11_all', 'busy level 3'),
               ('hns_txdat_stall', 'home-node data stalls'), ('mxp_p0_dat_txflit_valid', 'data flits delivered at device port 0'),
               ('mxp_p1_dat_txflit_valid', 'data flits delivered at device port 1'), ('_dat_links', 'data flits forwarded on mesh links (east + west + north + south)'),
               ('_req_links', 'request flits forwarded on mesh links (east + west + north + south)')]


def mesh_val(tag, name):
    ev = F['mesh'][tag]['ev']
    if name in ('_dat_links', '_req_links'):
        kind = 'dat' if name == '_dat_links' else 'req'
        parts = [ev.get(f'mxp_{d}_{kind}_txflit_valid') for d in 'ewns']
        if any(p is None for p in parts):
            return None, None
        return (sum(p.get('mesh0', 0) + p.get('mesh1', 0) for p in parts) if all('mesh0' in p for p in parts) else None,
                sum(p['mesh0_per_s'] + p['mesh1_per_s'] for p in parts))
    e = ev.get(name)
    if not e:
        return None, None
    per_line = (e.get('mesh0', 0) + e.get('mesh1', 0)) if ('mesh0' in e or 'mesh1' in e) else None
    return per_line, e.get('mesh0_per_s', 0) + e.get('mesh1_per_s', 0)


def table_mesh_single():
    tags = [t for t in N.get('mesh_single_tags', []) if t in F['mesh']]
    if not tags:
        return '<p><b>Insufficient data.</b> ' + esc(N.get('mesh_single_missing', 'No mesh-counter run of one core exists.')) + '</p>'
    idle = N.get('mesh_idle_tag')
    h = ('<div class="tw"><table><caption>Table 10. Mesh counters while one core runs the ASCT read loop, sum of both meshes, system-wide (root). '
         'Values are per 64-byte line read by that core. The idle column is in events per second, because no line is read.</caption><tr><th class="l">Counter</th>')
    for t in tags:
        m = F['mesh'][t]
        h += f'<th>{esc(N["mesh_tag_names"].get(t, t))}<br>{m["rate"]:.1f} GB/s</th>'
    if idle in F['mesh']:
        h += '<th>idle,<br>events/s</th>'
    h += '</tr>'
    for n, title in SINGLE_MESH:
        vals = [mesh_val(t, n) for t in tags]
        if all(v[0] is None for v in vals):
            continue
        code = '' if n.startswith('_') else f' (<code>{n}</code>)'
        row = f'<tr><td class="l">{esc(title)}{code}</td>' + ''.join(f'<td>{cell(v[0], 3)}</td>' for v in vals)
        if idle in F['mesh']:
            iv = mesh_val(idle, n)[1]
            row += f'<td>{"" if iv is None else f"{iv:,.0f}"}</td>'
        h += row + '</tr>'
    return h + '</table></div>'


PAD_COLS = [('cpu_cycles', 'cycles'), ('inst_retired', 'instructions'), ('l1d_cache_lmiss_rd', 'L1 long misses'), ('l2d_cache_lmiss_rd', 'L2 long misses'),
            ('l1d_cache_hwprf', 'L1 prefetches'), ('l2d_cache_hwprf', 'L2 prefetches'), ('l2d_cache_l1hwprf', 'L2 accesses by the L1 prefetcher'),
            ('l2d_cache_refill', 'L2 refills'), ('stall_backend_mem', 'stall cycles, memory')]


def table_pad():
    """ASCT loop with 0, 1, 2, 4 injected NOPs at 1 MiB and 8 MiB, with the new read loop of 2026-11-15 beside it."""
    peer = N.get('peer_counters', {})
    h = ('<div class="tw"><table><caption>Table 4. ASCT read loop with injected NOPs on one core: rate and core counters per 64-byte line. '
         'Median of the counted processes. NOPs: injected NOPs. Rows "new read": our loop on 2026-11-15, for the counters that were counted then.</caption>'
         '<tr><th class="s">CPU</th><th class="s">Size</th><th class="l">Loop</th><th>rate, GB/s</th>' + ''.join(f'<th>{esc(t)}</th>' for _, t in PAD_COLS) + '</tr>')
    for cpu in F['cpus']:
        for b, short in ((MI, '1M'), (8 * MI, '8M')):
            for nn in (0, 1, 2, 4):
                k = F['one'][str(cpu)]['cnt'].get(str(b)) if nn == 0 else F.get('padcnt', {}).get(f'{cpu}.{nn}.{b}')
                if not k:
                    continue
                hl = ' class="hl"' if b == 8 * MI and nn in (0, 2) else ''
                h += (f'<tr><td class="s">{cpu}</td><td class="s">{lab(b)}</td><td class="s">ASCT read, {nn} NOPs</td><td{hl}>{k["_rate"]:.1f}</td>'
                      + ''.join(f'<td>{cell(k.get(n), 4 if n == "l2d_cache_lmiss_rd" else 3)}</td>' for n, _ in PAD_COLS) + '</tr>')
            pk = peer.get(f'new.{short}.{cpu}')
            if pk:
                h += (f'<tr><td class="s">{cpu}</td><td class="s">{lab(b)}</td><td class="s">new read, 2026-11-15</td><td>{pk["rate"]:.1f}</td>'
                      + ''.join(f'<td>{cell(pk.get(n), 4 if n == "l2d_cache_lmiss_rd" else 3)}</td>' for n, _ in PAD_COLS) + '</tr>')
    return h + '</table></div>'


def table_mix():
    """ASCT peak-bandwidth traffic types: CRB at 64+56 beside the two vendor runs."""
    mix = F['chip'].get('mix', {})
    names = [('0', 'All Reads'), ('2', '3:1 Reads-Writes'), ('3', '2:1 Reads-Writes'), ('4', '1:1 Reads-Writes'), ('5', '2:1 Rd-Wr (Non-Temporal)')]
    v0, v1 = B['vendor']['a0_numa2_ddr_7200'], B['vendor']['a1_numa2_ddr_8000']
    h = ('<div class="tw"><table><caption>Table 8. The five traffic types of the ASCT benchmark <code>peak-bandwidth</code>, total GB/s. '
         'CRB: 64+56 threads, 0 injected NOPs, median (range). A0 and A1: the vendor runs, all CPUs of the machine.</caption>'
         f'<tr><th class="l">Traffic type (ASCT name)</th><th>CRB, 120 threads</th><th>A0, {v0["cpus"]} CPUs</th><th>A1, {v1["cpus"]} CPUs</th></tr>')
    for t, nm in names:
        d = F['chip']['base'] if t == '0' else mix.get(t)
        c = f'{d["median"]:.1f} ({d["lo"]:.1f} to {d["hi"]:.1f}, n={d["n"]})' if d else ''
        h += f'<tr><td class="l">{esc(nm)}</td><td>{c}</td><td>{v0["peak"][nm][0]:.1f}</td><td>{v1["peak"][nm][0]:.1f}</td></tr>'
    return h + '</table></div>'


def fig(svg, caption):
    return f'<figure>{svg}<figcaption>{caption}</figcaption></figure>' if svg else ''


def bullets(items):
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'


def block(key):
    """A NOTES text block: a list of paragraphs or bullet lists, already HTML."""
    return ''.join(N.get(key, []))


parts = []
parts.append(f'<h1>ASCT cross-check of two open read-throughput questions on CRB</h1><p class="sub">{N["subtitle"]}</p>')
parts.append('<div class="short"><h2>Short version</h2>' + block('short') + '</div>')
parts.append('<details><summary>Words used here</summary>' + block('words') + '</details>')
parts.append('<h2>1. What was asked, and how ASCT was used</h2>' + block('asked'))
parts.append(fig(figs.fig_path(), N['cap_path']))
parts.append(block('how'))
parts.append('<h3>The three read loops</h3>' + fig(figs.fig_loops(), N['cap_loops']) + block('loops'))
parts.append('<h2>2. Question 1: the small gain of the new read loop at 8 MiB</h2>' + block('q1_intro'))
parts.append(fig(figs.fig_size(F, B), N['cap_size']))
parts.append(fig(figs.fig_fall(F, B), N['cap_fall']))
parts.append(block('q1_rates') + table_sizes())
parts.append('<h3>Core counters: cost per line</h3>' + block('q1_cost_intro') + fig(figs.fig_cost(F, B), N['cap_cost']) + block('q1_cost'))
parts.append('<h3>Core counters: the prefetchers</h3>' + block('q1_pf_intro') + fig(figs.fig_prefetch(F), N['cap_prefetch']) + table_prefetch_rule() + block('q1_pf'))
parts.append('<details><summary>Table 2. All core counters per line, by buffer size (CPU 2 and CPU 41)</summary>' + table_counters(2) + table_counters(41) + '</details>')
parts.append('<h3>The ASCT loop with injected NOPs: a test of the prefetch explanation</h3>' + block('q1_pad_intro') + fig(figs.fig_pad(F), N['cap_pad']) + table_pad() + block('q1_pad'))
parts.append('<h3>SLC, mesh and distance</h3>' + block('q1_mesh_intro') + table_mesh_single() + block('q1_mesh'))
parts.append('<h3>Verdict for question 1</h3>' + block('q1_verdict'))
parts.append('<h2>3. Question 2: the low whole-chip read rate</h2>' + block('q2_intro'))
parts.append(fig(figs.fig_chip(F, B), N['cap_chip']))
parts.append(fig(figs.fig_nops(F, B), N['cap_nops']))
parts.append(block('q2_rates') + table_nops())
parts.append(fig(figs.fig_threads(F), N['cap_threads']))
parts.append(table_layouts() + block('q2_layouts'))
parts.append('<h3>Core counters at 64+56</h3>' + block('q2_cnt_intro') + table_chip_counters() + block('q2_cnt'))
parts.append('<h3>Mesh counters at 64+56</h3>' + block('q2_mesh_intro') + table_mesh_chip() + block('q2_mesh'))
parts.append('<h3>Verdict for question 2</h3>' + block('q2_verdict'))
parts.append('<h2>4. What the vendor baseline runs add</h2>' + block('vendor') + table_mix() + block('vendor2'))
parts.append('<h2>5. What ASCT can capture, and what was captured</h2>' + block('capture'))
parts.append('<h2>6. Runs, machine load and deviations</h2>' + block('runs'))
parts.append('<h2>7. Open items</h2>' + block('open'))
parts.append('<h2>References</h2><ol class="refs">' + ''.join(f'<li>{r}</li>' for r in N['refs']) + '</ol>')

page = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>ASCT cross-check</title><style>' + CSS + '</style></head><body><main>' + ''.join(parts)
        + '</main><div id="tip" role="tooltip"></div><script>' + JS + '</script></body></html>')
open(sys.argv[4], 'w').write(page)
print('written', sys.argv[4], len(page), 'bytes')
