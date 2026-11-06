#!/usr/bin/env python3
"""Two-page briefs of the performance reports for a reader who knows the chip but only wants the
results: asimov-c1nano-perf-brief.html and asimov-cme-perf-brief.html. Every number comes from
gen_perf.py's data layer (run 4 boot E as the latest, run 3 and boots A to D beside it, all read from
the CSV files); nothing is typed in. Print check: chrome --print-to-pdf, then count pages (2 A4 pages
each at most). gen_perf.main() writes both briefs; the __main__ block here writes them alone."""
import os, sys
A = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, A)
import gen_perf as p
from gen_perf import kib, fmt, table, line_chart, bars_h, SLC_BYTES
g = p.g
C = g.C   # the chart colours (gen_perf.C is boot C's table)

CSS = r"""
:root { --bg:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --grid:#e1e0d9; --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a;
  --font:system-ui,-apple-system,"Segoe UI",sans-serif; color-scheme:light; }
@page { size: A4; margin: 11mm 12mm; }
html, body { background:var(--bg); color:var(--ink); font-family:var(--font); font-size:10.5px; line-height:1.38; margin:0; }
main { max-width:188mm; margin:0 auto; padding:8px 12px; }
h1 { font-size:19px; margin:0 0 2px; line-height:1.2; }
h2 { font-size:12.5px; margin:9px 0 3px; border-top:1px solid var(--grid); padding-top:5px; }
p { margin:3px 0; } ul { margin:2px 0 4px; padding-left:16px; } li { margin:1px 0; }
.meta { color:var(--ink2); font-size:9.5px; }
.short { border-left:3px solid var(--s1); padding:5px 9px; margin:6px 0; background:#f6f8fb; }
figure { margin:5px 0 2px; break-inside:avoid; page-break-inside:avoid; }
figure svg { width:100%; height:auto; display:block; }
figcaption { font-size:9.5px; color:var(--ink2); margin:2px 0 0; }
.take { font-weight:600; color:var(--ink); }
.tbl { break-inside:avoid; page-break-inside:avoid; margin:3px 0; }
table { border-collapse:collapse; font-size:9.5px; font-variant-numeric:tabular-nums; width:100%; }
th, td { text-align:left; padding:2px 5px; border-bottom:1px solid var(--grid); vertical-align:top; }
th { color:var(--ink2); font-weight:600; }
td:nth-child(n+2), th:nth-child(n+2) { text-align:right; }
td:last-child, th:last-child { text-align:left; }
.note { color:var(--ink2); font-size:9px; margin:1px 0 0; }
dl { display:grid; grid-template-columns:max-content 1fr; gap:1px 8px; font-size:9.5px; margin:2px 0; }
dt { font-weight:600; } dd { margin:0; }
.hyp { font-size:9px; padding:0 5px; border-radius:8px; background:#fbe9e2; color:#8a3a1c; margin-right:4px; }
.gap { font-size:9px; padding:0 5px; border-radius:8px; background:#eef0f3; color:#3b3f46; margin-right:4px; }
svg text { font-family:var(--font); }
"""

def page(title, meta, body):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title><style>{CSS}</style></head><body><main><h1>{title}</h1><p class="meta">{meta}</p>{body}</main></body></html>"""

def fig(svg, take, rest=""):
    return f'<figure>{svg}<figcaption><span class="take">{take}</span> {rest}</figcaption></figure>'

def bars_compact(rows, w=900, unit="GB/s", color=None, xlim=None, rh=17, L=330):
    """gen_run3.bars_h with a row height and label width that fit the brief's two pages"""
    color = color or C["s1"]; Rr, T, B = 95, 26, 10; h = T + B + rh * len(rows)
    svg = g.SVG(w, h); x1 = xlim or max(r["v"] for r in rows) * 1.05
    fx = lambda v: L + v / x1 * (w - L - Rr)
    for tk in [i * x1 / 5 for i in range(6)]:
        svg.line(fx(tk), T - 6, fx(tk), h - B, C["grid"]); svg.text(fx(tk), T - 10, f"{tk:.0f}", 10, "middle", C["muted"])
    svg.text(w - Rr + 30, T - 10, unit, 10, "start", C["ink2"])
    for i, r in enumerate(rows):
        y = T + rh * i + 2
        svg.text(L - 10, y + 11, r["label"], 11, "end")
        svg.rect(L, y, fx(r["v"]) - L, rh - 4, r.get("color", color), f"{r['label']}: {r['v']:,.1f} {unit}", rx=2)
        svg.text(fx(r["v"]) + 6, y + 11, f"{r['v']:,.1f}", 10, "start", C["ink2"])
    return svg.out()

# figure heights (SVG units at w=900 or w=1150, scaled to the page width): set so each brief prints on 2 A4 pages
F1_H, BAR_RH, CF1_H, CF2_H = 170, 15, 250, 190
PE, R3 = p.PLATFORM["E"], p.RUN3
META = (f"Latest: run 4 boot E (membench-jibin-{PE['run_id']}, {PE['date']}, commit {PE['commit']}, SCP {PE['scp']} (the system control firmware), TF-A {PE['tfa']} (the Arm Trusted Firmware)) on the GA13 Palladium (one Asimov hemisphere), "
        f"the first boot with the DSU L3 in use as a cache (IMP_CLUSTERPWRSTAT_EL1 {PE['pwrstat'][0]} on CPU 2's cluster, Jesse's README). Beside it: run 3 (membench-jibin-{R3['run_id']}, {R3['date']}) and run 4 "
        f"boots A to D (005 to 008), all measured with the L3 of CPUs 2 to 9 holding no data (register 0x0, 0 L3 hits). One C1-Nano core on CPU 2 unless stated. DRAM is an emulator memory, not LPDDR5X. "
        f"Full reports: asimov-c1nano-perf.html, asimov-cme-perf.html. Every number here is read from the CSV files by gen_brief.py through gen_perf.py.")

# the level map of boot E, by (size, kind); the L3 hit set by size
LV = {(d["size"], d["kind"]): d for d in p.LEVELS}
HIT = {h["size"]: h for h in p.HITSET}
def lv(size, kind="repeat", boot=None): return LV[(size, kind)]["ns"] if boot is None else LV[(size, kind)]["ns_boot"][boot]
def lv3(size, kind="repeat"): return LV[(size, kind)]["ns3"]
FL_E, FL_3 = lv(8388608, "flushed"), lv3(8388608, "flushed")
one = {d["size"]: d for d in g.ONE}
rv = {(d["kernel"], d["size"]): d for d in p.READ_VARIANTS}
g8 = {(d["form"], d["kernel"], d["size"]): d for d in p.G8_ROWS}
L3_LO, L3_HI = min(p.L3_HIT_EST.values()), max(p.L3_HIT_EST.values())
SPARSE2 = [d for d in p.OCM_SPARSE if d["cpu"] == 2]
ALL5_3 = p.ALL5_RUN3_ALL
PCTS = lambda s: 100 * HIT[s]["l3_hit"]
SHARE = lambda s: f"{100 * HIT[s]['l2_hit']:.0f} / {100 * HIT[s]['l3_hit']:.0f} / {100 * HIT[s]['l3_refill']:.0f} %"   # per load, from the hit-set counters
SEQ_DEMAND_E = p.SEQ_ROW["l1_refill"]["E"] - p.SEQ_ROW["l1pf"]["E"]   # L1 refills not made by the prefetcher: the demand misses per load
SEQ_GBPS_E = 64 / p.SEQ_ROW["ns"]["E"]   # one line per load: the stream rate in GB/s (1e9 bytes)
A8 = {(d["kernel"], d["size"]): d["run3"] for d in g.ALL8}; PD = {(d["kernel"], d["size"]): d["run3"] for d in g.PERDSU}
W8 = max(v for (k, s), v in A8.items() if k == "write"); R8 = max(v for (k, s), v in A8.items() if k == "read")
READ_LIMIT, WRITE_LIMIT = 32 * g.CORE_GHZ, 16 * g.CORE_GHZ

# ======================================================================= core brief
def core_brief():
    pts_e = [(d["size"], d["ns"], f"{kib(d['size'])} {d['kind']}, boot E: {d['ns']:.3f} ns") for d in p.LEVELS if d["kind"] in ("repeat", "fresh")]
    pts_3 = [(d["size"], d["ns3"], f"{kib(d['size'])} {d['kind']}, run 3: {d['ns3']:.3f} ns") for d in p.LEVELS if d["kind"] in ("repeat", "fresh")]
    f1 = line_chart([dict(name="boot E, the L3 on", color=C["s1"], pts=pts_e, short="boot E"),
                     dict(name="run 3, the L3 holding no data", color=C["muted"], pts=pts_3, dash="5 4", short="run 3", dy=14)],
                    w=900, h=F1_H, marks=((32768, "L1 32 KiB"), (131072, "L2 128 KiB"), (262144, "L3 256 KiB (on, boot E)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 60), ticks_y=[0, 15, 30, 45, 60])
    t1 = table(["Level", "Boot E (L3 on), ns per load", "Run 3 (L3 off), ns", "How it was measured", "Note"],
               [["L1 (32 KiB per core)", fmt(lv(4096), 1), fmt(lv3(4096), 1), "4 KiB chain walked repeatedly", f"{p.CONTROLS['E']['p4k_cyc']:.2f} cycles at 2 GHz, the same on every boot"],
                ["L2 (128 KiB per DSU)", fmt(lv(131072), 1), fmt(lv3(131072), 1), "128 KiB chain walked repeatedly", f"every load misses L1, {HIT[131072]['l2_hit']:.2f} L2 read hits per load"],
                ["L3 (256 KiB per DSU), first measured on boot E", f"{HIT[196608]['ns']:.1f} / {HIT[262144]['ns']:.1f} / {HIT[393216]['ns']:.1f}", f"{lv3(196608):.1f} / {lv3(262144):.1f} / {lv3(393216):.1f}", "192 / 256 / 384 KiB chains walked repeatedly",
                 f"every load misses L1. Share of loads served by L2 / L3 / mesh: {SHARE(196608)} at 192 KiB, {SHARE(262144)} at 256 KiB, {SHARE(393216)} at 384 KiB. One L3 hit costs about {L3_LO:.1f} to {L3_HI:.1f} ns est. (derived below)"],
                ["SLC (3.75 MiB over five home nodes)", fmt(lv(2097152, "fresh"), 1), fmt(lv3(2097152, "fresh"), 1), "2 MiB chain walked once", "the 2 MiB buffer is DRAM memory. Its lines are cached in the SLC, each address at one of the five home nodes, chosen by a hash of the address"],
                ["OCM region, from CPU 2 (sparse chain)", f"{min(d['E']['best'] for d in SPARSE2):.1f} to {max(d['E']['best'] for d in SPARSE2):.1f}", f"{min(d['run3']['best'] for d in SPARSE2):.1f} to {max(d['run3']['best'] for d in SPARSE2):.1f}", "256 KiB sparse chain, every line flushed first, best of 7 passes",
                 f"On boot E only {p.SPARSE_L3_RNG_CPU2['E'][0]:.2f} to {p.SPARSE_L3_RNG_CPU2['E'][1]:.2f} of the loads in these rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so these values are below the true OCM latency"],
                ["OCM, all five regions, dense chain", f"{p.ALL5[2]['E']['dense']:.1f} (CPU 2), {p.ALL5[8]['E']['dense']:.1f} (CPU 8)", f"{min(ALL5_3[c]['dense'] for c in ALL5_3):.1f} to {max(ALL5_3[c]['dense'] for c in ALL5_3):.1f} (CPUs 2, 4, 6, 8)", "1.25 MiB dense chain, flushed, best of 2 passes",
                 f"the OCM number to quote: on E every load of this row is read from the mesh ({p.ALL5_DENSE_L3[2]:.2f} L3 read refills per load), so none is served by the L3 (derived, the L3 hit counter was not run on this row)"],
                ["DRAM (emulator memory model, fixed delay)", fmt(FL_E, 1), fmt(FL_3, 1), "8 MiB random chain, every line flushed from all caches", f"a 32 MiB chain walked once: {lv(33554432, 'fresh'):.1f} ns on E, {lv3(33554432, 'fresh'):.1f} on run 3"],
                ["DRAM (emulator memory model, fixed delay)", fmt(p.SEQ_ROW['ns']['E'], 1), "not run", "8 MiB sequential chain in address order, every line flushed first", f"the hardware prefetcher brought every load's line into L1 before or while the load waited for it ({p.SEQ_ROW['l1pf']['E']:.2f} L1 prefetch refills per load, {SEQ_DEMAND_E:.4f} demand refills per load). The loads run at the prefetch stream's rate: 64 B per {p.SEQ_ROW['ns']['E']:.2f} ns is {SEQ_GBPS_E:.1f} GB/s, about the one-core plain DRAM read on E ({rv[('read', 33554432)]['agg']['E']:.1f} GB/s). {p.SEQ_ROW['ns']['C']:.1f} ns with the L3 off (boot C), {p.SEQ_ROW['ns']['B']:.1f} with the prefetchers off (boot B)"]],
               f"Best pass of each row [latency-dram-*.csv, latency-dram-small-l3.csv, latency-ocm-*.csv]. The L3 hit cost is derived over the 256 and 384 KiB rows: {p.L3_HIT_EST_HOW}. The 192 KiB row gives {p.L3_HIT_EST_192:.1f} ns est. the same way and is left out: under half its loads hit the L3 ({PCTS(196608):.0f} %), so the subtracted L2 term is as large as the L3 term.")
    bw = [dict(label="1 core read path limit (dual 128-bit, computed)", v=READ_LIMIT, color=C["muted"]), dict(label="1 core write path limit (128-bit, computed)", v=WRITE_LIMIT, color=C["muted"]),
          dict(label="1 core read 16 KiB (L1) (run 3, L3 off)", v=one[16384]["read"]), dict(label="1 core read 24 KiB (L1), single-call form (boot E, L3 on)", v=g8[("asm", "read", 24576)]["agg"]["E"]),
          dict(label="1 core read, L1 rate from the 8 and 16 KiB passes, single-call form (boot E, L3 on, derived)", v=p.G8_MARGINAL[("E", "asm")], color=C["s4"]),
          dict(label="1 core read 32 MiB (DRAM) (run 3, L3 off)", v=one[33554432]["read"]), dict(label="1 core read 32 MiB (DRAM) (boot E, L3 on)", v=rv[("read", 33554432)]["agg"]["E"]),
          dict(label="1 core write 32 MiB (run 3, L3 off)", v=one[33554432]["write"], color=C["s2"]), dict(label="1 core copy 32 MiB, read + write bytes (run 3, L3 off)", v=one[33554432]["copy"], color=C["s3"]),
          dict(label="2 cores of one DSU write 16 MiB (run 3, L3 off)", v=g.PAIR_W, color=C["s2"]), dict(label="4 cores, one per DSU, write 16 MiB (run 3, L3 off)", v=PD[("write", 16777216)], color=C["s2"]),
          dict(label="8 cores write 16 MiB each (run 3, L3 off)", v=A8[("write", 16777216)], color=C["s2"]), dict(label="8 cores read 16 MiB each (run 3, L3 off)", v=A8[("read", 16777216)]),
          dict(label="1 core reads one OCM region (run 3, L3 off)", v=max(g.OCMBW["region"])), dict(label="4 cores read four OCM regions (run 3, L3 off)", v=g.OCMBW["four"]), dict(label="1 core streaming write to OCM (run 3, L3 off)", v=g.OCMBW["write"], color=C["s2"])]
    f2 = bars_compact(bw, w=1150, xlim=170, rh=BAR_RH)
    read_x = rv[("read", 33554432)]["agg"]["E"] / one[33554432]["read"]
    w1_lo, w1_hi = min(d["write"] for d in g.ONE), max(d["write"] for d in g.ONE)   # run 3's one-core write at 16 KiB to 32 MiB
    e_sparse_lo, e_sparse_hi = min(d["E"]["best"] for d in SPARSE2), max(d["E"]["best"] for d in SPARSE2)
    e2m, c2m = rv[("read", 2097152)]["e"]["E"], rv[("read", 2097152)]["e"]["C"]   # the plain 2 MiB read's counters per line
    body = f"""

<h2>Words used here</h2>
<dl>
<dt>run, boot</dt><dd>A run is one job on the emulator (run 3 = membench-jibin-004). Run 4 is five boots: A as run 3, B the data prefetchers off, C the 64 KiB contiguous hint on the OCM mapping, D both, E the L3 on.</dd>
<dt>chase, hit set</dt><dd>A random pointer chain, one load per 64-byte line. Fresh: walked once. Flushed: every line cleaned and invalidated from the caches first. Hit set: the 64 KiB to 512 KiB chases with the L2 and L3 hit events.</dd>
<dt>sparse chain, dense chain</dt><dd>Dense chain: every 64-byte line of the buffer is a member of the chain. Sparse chain: one member line per 4 KiB page, so a line the prefetcher fetches next to a member is never a member.</dd>
</dl>
<h2>1. Latency by level</h2>
{fig(f1, f"Steps at 48 KiB (past L1), 192 KiB (past L2: {lv(196608):.1f} ns on boot E with the L3 on, {lv3(196608):.1f} ns on run 3 with the L3 holding no data) and 4 to 16 MiB (past the SLC).", "Latency test (a dependent chase): each load's address is the value the previous load returned. Loads cannot overlap. Up to 384 KiB the same list is walked repeatedly, from 512 KiB a random list is walked once. Dashed: run 3 (membench-jibin-004).")}
{t1}

<h2>2. Bandwidth</h2>
{fig(f2, f"With the L3 on, one core reads {rv[('read', 33554432)]['agg']['E']:.1f} GB/s from DRAM, {read_x:.1f} times run 3's {one[33554432]['read']:.1f} GB/s. The other rows are run 3's with the L3 off: reads scale with cores ({one[33554432]['read']:.1f} GB/s for one at 32 MiB, {A8[('read', 2097152)]:.1f} for eight at 2 MiB each), writes are limited per DSU ({w1_lo:.1f} to {w1_hi:.1f} GB/s for one core at 16 KiB to 32 MiB, {g.PAIR_W:.0f} for two of one DSU) and reach {A8[('write', 2097152)]:.0f} with eight at 2 MiB each (the bars: the 16 MiB rows, {A8[('read', 16777216)]:.1f} and {A8[('write', 16777216)]:.1f}).", f"GB = 1e9 bytes, best rep [bandwidth-*.csv]. The grey rows are computed: the Arm C1-Nano TRM's dual 128-bit read path and single 128-bit write path at the {g.CORE_GHZ:.1f} GHz the latency rows show. One core's L1 reads reach {100 * g8[('asm', 'read', 24576)]['agg']['E'] / READ_LIMIT:.0f} % of the read limit in the single-call form (every pass inside one assembly call).")}

<h2>3. What else the runs showed</h2>
<ul>
<li><b>The L3 is on for the first time.</b> On runs 1 to 3 and boots A to D the L3 of CPUs 2 to 9 held no data (register 0x0, {HIT[262144]['hitC']:.0f} L3 hits per load on boot C). Boot E's rebuilt SCP stages the full L3 before the clusters power on. Its hit set counts {PCTS(196608):.0f}, {PCTS(262144):.0f} and {PCTS(393216):.0f} % L3 read hits per load at 192, 256 and 384 KiB, and the data read fell from {HIT[196608]['nsC']:.1f}, {HIT[262144]['nsC']:.1f} and {HIT[393216]['nsC']:.1f} ns on boot C to {HIT[196608]['ns']:.1f}, {HIT[262144]['ns']:.1f} and {HIT[393216]['ns']:.1f} ns [latency-dram-small-l3.csv, Jesse's boot E README].</li>
<li><b>The 52 ns DRAM data read is a fixed-delay memory model.</b> On boot B an address-order 8 MiB chain reads {p.DRAM_MODEL['seq_B']:.3f} ns per load and a random one {p.DRAM_MODEL['random_B']:.3f} ns. The model answers in a fixed time. {p.DRAM_MODEL['home_hop']:.1f} ns of it is the home-node load (the 2 MiB SLC data read), and the rest, about {p.DRAM_MODEL['rest_est']:.1f} ns est., is the model's delay. The L3 does not change it ({p.DRAM_MODEL['flushed_E']:.3f} ns flushed on E, {p.DRAM_MODEL['flushed_C']:.3f} on C) [latency-dram-seq.csv, latency-dram-flushed.csv, boots B, C, E].</li>
<li><b>One core reads {read_x:.1f} times more from DRAM with the L3 on.</b> The plain read loop reads 32 MiB at {one[33554432]['read']:.1f} GB/s on run 3 and {rv[('read', 33554432)]['agg']['C']:.1f} GB/s on boot C, both with the L3 off. On boot E, with the L3 on, the same loop reads {rv[('read', 33554432)]['agg']['E']:.1f} GB/s. Adding a software prefetch hint (PRFM, the Arm prefetch instruction, issued 4 lines ahead) does not help. It changes boot C by {100 * (rv[('read-pf4', 33554432)]['agg']['C'] / rv[('read', 33554432)]['agg']['C'] - 1):+.0f} % and lowers boot E to {rv[('read-pf4', 33554432)]['agg']['E']:.1f} GB/s. Why the L3 makes the loop faster is <span class="gap">Insufficient data</span>. The refill counters per line are about the same on both boots (L1 {e2m['l1d_refill']:.2f} and {c2m['l1d_refill']:.2f}, L2 {e2m['l2d_refill']:.2f} and {c2m['l2d_refill']:.2f}, L1 prefetch {e2m['l1d_refill_hwprf']:.2f} and {c2m['l1d_refill_hwprf']:.2f} at 2 MiB), so they do not show the mechanism [bandwidth-read-prefetch.csv].</li>
</ul>

<h2>4. Caveats</h2>
<ul>
<li>DRAM on this emulator image is a memory model, not LPDDR5X, so the DRAM latency and multi-core bandwidth rows are not silicon numbers. Its configured delay is an open question to Jesse.</li>
<li>The bandwidth set (one-core sweep, multi-core, writer placement, OCM bandwidth) has not run with the L3 on.</li>
<li><span class="hyp">hypothesis</span> Boot E reads {p.EC_DELTA[33554432]:+.2f} ns at 32 MiB and {p.EC_DELTA[16777216]:+.2f} ns at 16 MiB above boot C (same commit): translation walks. A walk-counted 32 MiB row on E and C in one process would test it.</li>
</ul>

"""
    return page("Asimov C1-Nano memory performance: brief", META, body)

# ======================================================================= CME brief
def cme_brief():
    c = {(d["size"], d["kind"]): d for d in p.CME_LEVELS}
    cb = dict(p.CME_B)
    rt, rt_cyc = p.CONTROLS["E"]["rt"][0], g.RT_CYC[0]
    CBW, COCMBW, OCMBW, CALLB = g.CBW, g.COCMBW, g.OCMBW, g.CALLB
    chase = [d for d in p.CME_LEVELS if d["kind"] in ("repeat", "fresh")]
    f1 = line_chart([dict(name="C1-Nano core, CPU 2, boot E", color=C["s1"], pts=[(d["size"], d["core"]) for d in chase], short="core", dy=14),
                     dict(name="through the CME, boot E (L3 on)", color=C["s2"], pts=[(d["size"], d["ns"], f"CME {kib(d['size'])}, boot E: {d['ns']:.3f} ns") for d in chase], short="CME E"),
                     dict(name="through the CME, run 3 (L3 off)", color=C["muted"], pts=[(d["size"], d["ns3"]) for d in chase], dash="5 4", short="CME run 3", dy=14),
                     dict(name="through the CME, boot B (CME prefetcher off)", color=C["s3"], pts=[(d["size"], d["nsB"]) for d in chase], dash="2 3", short="CME B", dy=-10)],
                    w=900, h=CF1_H, marks=((32768, "core L1 32 KiB"), (65536, "CME L1 64 KiB"), (262144, "L3 256 KiB (on, boot E)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 75), ticks_y=[0, 15, 30, 45, 60, 75],
                    hline=(rt, f"register control {rt:.1f} ns, no memory access"))
    f2 = line_chart([dict(name="core read (run 3, L3 off)", color=C["s1"], pts=[(d["size"], d["core_read"]) for d in CBW if d["core_read"]], dash="5 4", short="core read", dy=14),
                     dict(name="CME read (run 3, L3 off)", color=C["s1"], pts=[(d["size"], d["read"]) for d in CBW], short="CME read"),
                     dict(name="core write (run 3, L3 off)", color=C["s2"], pts=[(d["size"], d["core_write"]) for d in CBW if d["core_write"]], dash="5 4", short="core write", dy=14),
                     dict(name="CME write (run 3, L3 off)", color=C["s2"], pts=[(d["size"], d["write"]) for d in CBW], short="CME write")],
                    w=900, h=CF2_H, ylabel="GB/s, one thread on CPU 2, run 3 with the L3 off (dashed: core, solid: CME)", marks=((65536, "CME L1 64 KiB"), (262144, "L3 (off on run 3)"), (SLC_BYTES, "SLC")), ylim=(0, 110), ticks_y=[0, 25, 50, 75, 100])
    big = [d for d in CBW if d["size"] >= 163840]
    b48 = [d for d in CBW if d["size"] == 49152][0]; b32m = [d for d in CBW if d["size"] == 33554432][0]
    co = p.CME_OCM; e_sp = [d["E"]["sparse"] for d in co]; r3_sp = [d["run3"]["best"] for d in co]
    fastest = min(co, key=lambda d: d["E"]["sparse"])   # the region with the lowest sparse best through the CME on boot E, as gen_perf_cme.py's E_FASTEST
    core_sp = [d["E"]["best"] for d in p.OCM_SPARSE if d["cpu"] == 2]
    k8, k16 = c[(8192, "repeat")], c[(16384, "repeat")]
    WAKE_US = (0.1, 0.3)   # Jesse's run 3 README bounds on a fixed cost per timed span, us: not a measured row
    b16 = [d for d in CBW if d["size"] == 16384][0]
    copy_small = (min(b16["copy"], b48["copy"]), max(b16["copy"], b48["copy"])); copy_big = (min(d["copy"] for d in big), max(d["copy"] for d in big))
    t1 = table(["Row", "Core", "CME", "Source", "Note"],
               [["Dependent load, 4 KiB chain", f"{c[(4096, 'repeat')]['core']:.1f} ns", f"{c[(4096, 'repeat')]['ns']:.1f} ns", "boot E", f"register control (DUP, LASTB, no load) {rt:.1f} ns = {rt_cyc:.0f} CME cycles, chase minus control {c[(4096, 'repeat')]['ns'] - rt:.2f} ns (derived). Run 3 {c[(4096, 'repeat')]['ns3']:.1f} ns"],
                ["8 KiB / 16 KiB / 64 KiB", f"{k8['core']:.1f} / {k16['core']:.1f} / {c[(65536, 'repeat')]['core']:.1f} ns", f"{k8['ns']:.1f} / {k16['ns']:.1f} / {c[(65536, 'repeat')]['ns']:.1f} ns", "boot E", f"run 3: {k8['ns3']:.1f} / {k16['ns3']:.1f} / {c[(65536, 'repeat')]['ns3']:.1f} ns. Boot B (CME prefetcher off): {cb[8192]:.1f} / {cb[16384]:.1f} / {cb[65536]:.1f} ns"],
                ["2 MiB chain walked once (SLC on the core)", f"{c[(2097152, 'fresh')]['core']:.1f} ns", f"{c[(2097152, 'fresh')]['ns']:.1f} ns", "boot E", f"run 3 {c[(2097152, 'fresh')]['ns3']:.1f} ns"],
                ["DRAM (emulator memory model, fixed delay), 8 MiB random chain, every line flushed from all caches", f"{c[(8388608, 'flushed')]['core']:.1f} ns", f"{c[(8388608, 'flushed')]['ns']:.1f} ns", "boot E", f"run 3 {c[(8388608, 'flushed')]['ns3']:.1f} ns, boot C {c[(8388608, 'flushed')]['nsC']:.1f}"],
                ["DRAM (emulator memory model, fixed delay), 8 MiB sequential chain in address order, every line flushed first", f"{c[(8388608, 'seq')]['core']:.1f} ns", f"{c[(8388608, 'seq')]['ns']:.1f} ns", "boot E", f"every CME refill a prefetch ({c[(8388608, 'seq')]['e']['cme_l1d_refill_hwprf']:.2f} per load). The same {p.CME_SEQ['A']:.1f} ns on boots A and C, {p.CME_SEQ['B']:.1f} ns with the prefetcher off (boot B). How a prefetch stream overlaps the reads of a chain is drawn in asimov-c1nano-perf.html, section 8"],
                ["OCM, one region, 1 to 3 crosspoints", f"{min(core_sp):.1f} to {max(core_sp):.1f} ns", f"{min(e_sp):.1f} to {max(e_sp):.1f} ns", "boot E", f"sparse chain, best of 7 passes of 64 loads. Run 3 CME {min(r3_sp):.1f} to {max(r3_sp):.1f} ns. On boot E only {p.SPARSE_L3_RNG_CPU2['E'][0]:.2f} to {p.SPARSE_L3_RNG_CPU2['E'][1]:.2f} of the core's loads in this row are read from the mesh (L3 read refills per load). The other loads are served by the L3, so the core values are below the true OCM latency"],
                ["OCM, all five regions, dense chain", f"{p.ALL5[2]['E']['dense']:.1f} ns", f"{p.CME_ALL5['E']['dense']:.1f} ns", "boot E", f"20,480 loads a pass. Run 3 CME {p.CME_ALL5['run3']['dense']:.1f} ns"],
                ["Read bandwidth, 48 KiB buffer", f"{b48['core_read']:.1f} GB/s", f"{b48['read']:.1f} GB/s", "run 3, L3 off", f"the CME's peak. Up to about {100 * CALLB['read'] / g.PASS16:.0f} % of its 16 KiB row is per-call cost"],
                ["Read bandwidth, 160 KiB to 32 MiB", f"{b32m['core_read']:.1f} GB/s at 32 MiB", f"{min(d['read'] for d in big):.1f} to {max(d['read'] for d in big):.1f} GB/s", "run 3, L3 off", f"{b32m['read'] / b32m['core_read']:.1f} times the core at 32 MiB"],
                ["Write bandwidth, 16 KiB to 32 MiB", f"{min(d['core_write'] for d in CBW if d['core_write']):.1f} to {max(d['core_write'] for d in CBW if d['core_write']):.1f} GB/s", f"{min(d['write'] for d in CBW):.1f} to {max(d['write'] for d in CBW):.1f} GB/s", "run 3, L3 off", "32 bytes per cycle through the CME at every footprint"],
                ["OCM read / streaming write, all five", f"{OCMBW['all5']:.1f} / {OCMBW['write']:.1f} GB/s", f"{COCMBW['all5']:.1f} / {COCMBW['write']:.1f} GB/s", "run 3, L3 off", ""],
                ["Per-call cost (1 KiB per call, 4,096 calls)", "", f"read {CALLB['read']:.0f} ns, write {CALLB['write']:.0f} ns", "run 3, L3 off", "a bound: includes SMSTART, register save, 1 KiB of data, SMSTOP"]],
               "CPU 2 with CPU 3 offline, so the DSU's CME serves one core. Best rep or best pass of each row [cme-latency-*.csv of boot E, run 3 and boot B, cme-bandwidth-*.csv of run 3, and the same run's core rows]. GB = 1e9 bytes. No CME bandwidth row has run with the L3 on.")
    cme_add = c[(4096, "repeat")]["ns"] - c[(4096, "repeat")]["core"]; dram_add = c[(8388608, "flushed")]["ns"] - c[(8388608, "flushed")]["core"]
    rep_sizes = [d["size"] for d in p.CME_LEVELS if d["kind"] == "repeat" and d["size"] >= 49152]
    body = f"""
<h2>Words used here</h2>
<dl>
<dt>CME</dt><dd>The Compute Matrix Engine, Arm's C1-SME2 unit: one per two-core cluster (DSU), runs the cores' streaming-mode (SME) instructions, with its own 64 KiB L1 data cache, TLB and hardware prefetcher. Its path to memory is CME L1, DSU L3 (in use on boot E only), then the mesh. The core's L1 and L2 are not on it.</dd>
<dt>run, boot</dt><dd>A run is one job on the emulator (run 3 = membench-jibin-004). Run 4 is five boots, A to E: A as run 3, B the prefetchers off (the CME's too), C and D the OCM mapped with a 64 KiB hint (D with the prefetchers off), E the L3 on.</dd>
<dt>streaming mode</dt><dd>The CPU state (SMSTART to SMSTOP) in which SVE instructions execute on the CME. The vector length here is 64 bytes, one cache line.</dd>
<dt>register control</dt><dd>The same chase loop with the load replaced by a register move (DUP then LASTB): the cost of the core-to-CME-to-core round trip with no memory access.</dd>
<dt>chase, fresh, flushed, sparse, dense, sequential</dt><dd>A random pointer chain, one load per line. Fresh: walked once. Flushed: every line cleaned and invalidated from the caches first. Sparse: one member line per 4 KiB page. Dense: every line of the buffer is a member. Sequential: the lines in address order.</dd>
</dl>
<h2>1. Latency: core against CME</h2>
{fig(f1, f"The CME has no clear step at its 64 KiB L1 on boot E: the climb starts at 8 KiB ({k8['ns'] - c[(4096, 'repeat')]['ns']:+.1f} ns) and the 64 to 96 KiB step is {c[(98304, 'repeat')]['ns'] - c[(65536, 'repeat')]['ns']:+.1f} ns. With the CME prefetcher off (boot B) the chase stays at {cb[4096]:.1f} to {cb[65536]:.1f} ns to 64 KiB and steps by {cb[98304] - cb[65536]:+.1f} ns at 96 KiB. The core steps at 48 KiB, 192 KiB ({c[(196608, 'repeat')]['core']:.1f} ns, the L3) and 4 to 16 MiB.", f"Latency test (a dependent chase): each load's address is the value the previous load returned. Loads cannot overlap. Up to 384 KiB the same list is walked repeatedly, from 512 KiB a random list is walked once. The horizontal line is the register control: a value moved into a vector register and back, {rt_cyc:.0f} CME cycles. The chase replaces one of its two instructions with a load, so chase minus control is a derived number, not a memory latency.")}

<h2>2. Bandwidth: core against CME (run 3, the L3 off)</h2>
{fig(f2, f"The CME reads {b48['read']:.0f} GB/s at 48 KiB and about {sum(d['read'] for d in big) / len(big):.0f} GB/s from 160 KiB on. It writes {min(d['write'] for d in CBW):.0f} to {max(d['write'] for d in CBW):.0f} GB/s at every footprint, where the core writes {max(d['core_write'] for d in CBW if d['core_write']):.0f}.", f"Run 3 (membench-jibin-004), the L3 holding no data. No CME bandwidth row has run with the L3 on. One thread, 256 bytes per instruction (four 64-byte vectors), best of 3 reps. Copy, not drawn, holds {copy_small[0]:.1f} to {copy_small[1]:.1f} GB/s (read plus write bytes) at 16 and 48 KiB and {copy_big[0]:.1f} to {copy_big[1]:.1f} GB/s from 160 KiB.")}

<h2>3. The numbers side by side</h2>
{t1}

<h2>4. What it means, and what it does not</h2>
<ul>
<li><b>A single load through the CME is slow, a stream is fast.</b> The CME path (core to CME to core, with the CME's own L1 and the DSU L3 behind it) adds {cme_add:.1f} ns to a dependent load and {dram_add:.1f} ns to a flushed DRAM load on boot E. A 256-byte load per instruction with no dependency gives {b32m['read'] / b32m['core_read']:.0f} times the core's read rate and {b32m['write'] / b32m['core_write']:.0f} times its write rate (run 3, L3 off).</li>
<li><b>Writes through one CME exceed what two cores write together (run 3, L3 off).</b> One CME writes a 32 MiB buffer at {g.W32:.1f} GB/s through the cluster's mesh port, {g.W32 / g.PAIR_W:.2f} times the {g.PAIR_W:.1f} GB/s CPUs 2 and 3 write together. <span class="hyp">hypothesis</span> The two-core write limit of the cluster is on the cores' side. A two-core write row with one core in streaming mode (through its CME) would test it.</li>
<li><b>The CME prefetcher explains the climb from 8 KiB.</b> With the prefetcher off (boot B) the chase reads {cb[4096]:.2f} to {cb[65536]:.2f} ns from 4 to 64 KiB and {cb[98304]:.2f} ns at 96 KiB [cme-latency-dram-small.csv, boot B]. That is the L1 step the other boots hide. With the L3 on (boot E) the prefetcher's fills at 8 to 24 KiB come from inside the cluster. They are {100 * p.CME_INNER_SHARE['E'][8192]:.0f} to {100 * min(p.CME_INNER_SHARE['E'][s] for s in (8192, 16384, 24576)):.0f} % of the CME's L1 refills, against {100 * max(p.CME_INNER_SHARE['C'][s] for s in (8192, 16384, 24576)):.0f} % or less on boot C. The pass-mean outside-cluster refills per load fall from {k8['emeanC']['cme_l1d_refill_outer']:.2f} and {k16['emeanC']['cme_l1d_refill_outer']:.2f} on C to {k8['emean']['cme_l1d_refill_outer']:.2f} and {k16['emean']['cme_l1d_refill_outer']:.2f} on E at 8 and 16 KiB. The time does not fall. E over C is {k8['ratio']:.3f} at 8 KiB, {k16['ratio']:.3f} at 16 KiB and {min(c[(s, 'repeat')]['ratio'] for s in rep_sizes):.3f} to {max(c[(s, 'repeat')]['ratio'] for s in rep_sizes):.3f} from 48 to 384 KiB. The prefetcher sets the time, so the source of a refill does not change it. Through the CME no row gives an L3 hit number. No CME event names the level that served a load.</li>
<li><b>OCM through the CME costs more per load than from the core.</b> On boot E the dense all-five chain reads {p.CME_ALL5['E']['dense']:.1f} ns through the CME, {p.CME_ALL5['E']['dense'] - p.ALL5[2]['E']['dense']:.1f} ns above the core's {p.ALL5[2]['E']['dense']:.1f} ns [cme-latency-ocm-*.csv]. The per-region rows through the CME do not order by mesh distance. The fastest is OCM{fastest['region']}, {fastest['dist']} crosspoint{'s' if fastest['dist'] != 1 else ''} away, at {fastest['E']['sparse']:.1f} ns. The CME streams OCM at {min(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.1f} to {max(COCMBW['region'][r] / OCMBW['region'][r] for r in range(5)):.1f} times the core's rate (run 3, L3 off).</li>
<li><b>Not measured.</b> <span class="gap">Insufficient data</span> Two cores of one DSU in streaming mode at once. The CME is shared, and no two-core CME row has run. A CME matmul with its operands in an OCM region has not run either. <span class="hyp">hypothesis</span> Each 64-load OCM pass carries a fixed wake-up cost of {WAKE_US[0]:.1f} to {WAKE_US[1]:.1f} us est. (the CME is powered down at the start of a timed span, Jesse's run 3 README bounds). A per-pass timestamp on those passes would test it.</li>
</ul>

"""
    return page("Asimov CME memory performance: brief", META, body)

if __name__ == "__main__":
    open(p.OUT["core_brief"], "w").write(core_brief())
    open(p.OUT["cme_brief"], "w").write(cme_brief())
    print("wrote both briefs")
