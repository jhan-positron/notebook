#!/usr/bin/env python3
"""asimov-c1nano-perf.html: the C1-Nano core's latency, bandwidth, OCM and mesh numbers, with run 4 boot E
(the DSU L3 on) as the latest data, run 3 and boot C beside it. core_page() returns the HTML string;
gen_perf.main() writes it. Every number comes from gen_perf's data layer (the CSV files through gen_run3
and gen_run4); nothing is typed in except the cited platform facts from Jesse's README files.
The section order is prev/asimov-c1nano-perf.html's (sections 1 to 12)."""
import statistics
import gen_perf as p
from gen_perf import (kib, fmt, pct, table, fig, page, words, line_chart, dumbbell, strip, bars_h, mesh_map, dotplot, stacked_h,
                      hyp, gap, rng, dist, NODES, DSUS, NODE_OF_REGION, CPU_DSU, SLC_BYTES)
g = p.g; r4 = p.r4

# ---------------------------------------------------------------- lookups over the data layer
LV = {(d["size"], d["kind"]): d for d in p.LEVELS}
def lv(size, kind="repeat"): return LV[(size, kind)]
HIT = {h["size"]: h for h in p.HITSET}
L3_EST = statistics.mean(p.L3_HIT_EST.values())            # est. ns of one L3 hit, mean of the 256 and 384 KiB derivations
CORE_GHZ = g.CORE_GHZ                                       # core cycles per ns from the 4 KiB repeated row of run 3
READ_PATH, WRITE_PATH = 32 * CORE_GHZ, 16 * CORE_GHZ        # GB/s of the dual 128-bit read path and the 128-bit write path at that clock
ONE = {d["size"]: d for d in g.ONE}
RV = {(d["kernel"], d["size"]): d for d in p.READ_VARIANTS}
G8R = {(d["form"], d["kernel"], d["size"]): d for d in p.G8_ROWS}
CRB_PASS_NS = 4.2   # the CRB V3AE's per-pass fixed cost, the intercept of the per-pass read fit on CPU 3 (4.2 ns + bytes / 134.2 GB/s, residual 0.5 %) [follow-up-run-plan.md, "CRB check of the two forms", 2026-11-04]
WS = {d["size"]: d for d in p.WRITE_SMALL}
FLUSHED_E = lv(8388608, "flushed")["ns"]
SEQ_E, SEQ_C = p.SEQ_ROW["ns"]["E"], p.SEQ_ROW["ns"]["C"]
SMALL_RATIO = [d["ratio"] for d in p.LEVELS if d["kind"] == "repeat" and d["size"] <= 131072]
L3_SIZES3 = (196608, 262144, 393216)
E_PLAIN = {s: RV[("read", s)]["agg"]["E"] for s in p.RP_SIZES}; C_PLAIN = {s: RV[("read", s)]["agg"]["C"] for s in p.RP_SIZES}
RUN3_PLAIN = {s: RV[("read", s)]["run3"] for s in p.RP_SIZES}
ASM16_24 = [G8R[("asm", "read", s)]["agg"][x] for x in "CE" for s in (16384, 24576)]
MOVED = [d for d in p.REPEAT_E3 if abs(d["pct"]) >= 1.0]
ROUTE_BY_DIST = {}
for d in p.ROUTES: ROUTE_BY_DIST.setdefault(d["dist"], []).append(d)
E_SPARSE_CPU2 = [d for d in p.OCM_SPARSE if d["cpu"] == 2]
SPARSE_MINUS_DENSE_E = [d["E"]["best"] - d["E"]["dense"] for d in p.OCM_SPARSE]
ROUTE_E_VS_A = [d["E"]["best"] - d["A"]["best"] for d in p.ROUTES]
RUN3_LABEL = "run 3 (membench-jibin-004, the L3 off), not repeated with the L3 on"

# ---- section 7.1 and 8: the L1 pass arithmetic and the in-flight lanes
E_ASM = p.G8["E"][("asm", "read")]["rows"]                      # boot E, every pass inside one call: t_pass ns and agg GB/s by size
L1_RATE = p.G8_MARGINAL[("E", "asm")]                           # GB/s of the 8 KiB added between the 8 and 16 KiB passes
PASS_F = E_ASM[16384]["t_pass"] - 16384 / L1_RATE               # ns est. per pass that is not reading, at 16 KiB
E_PP = p.G8["E"][("per-pass", "read")]["rows"]
PASS_F_PP = E_PP[16384]["t_pass"] - 16384 / p.G8_MARGINAL[("E", "per-pass")]   # the same est. for the looped form's read passes
CRB_GHZ = 2.8   # the CRB V3AE clock [follow-up-run-plan.md, run 5c, 'V3AE at 2.8 GHz']
IDEAL = lambda size: size / READ_PATH                            # ns a pass would take at the read path's rate
L1_CHASE = lv(4096)["ns"]                                        # ns per dependent load in L1 (the 4 KiB chain)
IN_FLIGHT = FLUSHED_E / SEQ_E                                    # est. DRAM reads open at once on the sequential chain of boot E
SEQ_B = p.SEQ_ROW["ns"]["B"]
SEQ_GBPS = 64 / SEQ_E
LINE_NS = 64 / READ_PATH                                         # ns per 64-byte line at the read path's rate
def CNT(boot, row):
    """the refill counters of a boot's SEQ or FLUSHED row as table cells: L1 refills, L1 prefetch refills, demand L1 refills (derived), L2 refills, L2 refills for L1 prefetches, L3 read refills"""
    e = r4.BT[boot][row]["e"]
    return [f"{e['l1d_refill']:.4f}", f"{e['l1d_refill_hwprf']:.4f}", f"{e['l1d_refill'] - e['l1d_refill_hwprf']:.4f}", f"{e['l2d_refill']:.4f}", f"{e['l2d_refill_l1dhwprf']:.4f}", f"{e['l3d_refill_rd']:.4f}"]

def pass_fig(w=960):
    """section 7.1: the 8 and 16 KiB passes of boot E's single-call form, to scale, and their difference"""
    L, R, T, rh = 250, 20, 30, 30; tmax = 360.0
    rows = [("8 KiB pass", E_ASM[8192]["t_pass"]), ("16 KiB pass", E_ASM[16384]["t_pass"]), ("difference: the added 8 KiB", None)]
    svg = g.SVG(w, T + rh * 3 + 56); fx = lambda t: L + t / tmax * (w - L - R)
    for tk in range(0, 301, 50):
        svg.line(fx(tk), T - 6, fx(tk), T + rh * 3, g.C["grid"]); svg.text(fx(tk), T - 10, f"{tk}", 10, "middle", g.C["muted"])
    svg.text(w - R, T - 10, "ns", 10, "end", g.C["ink2"])
    seg = 8192 / L1_RATE
    for i, (label, t) in enumerate(rows):
        y = T + rh * i + 4; svg.text(L - 10, y + 15, label, 12, "end")
        if t is not None:
            svg.rect(fx(0), y, fx(PASS_F) - fx(0), rh - 8, g.C["s2"], f"not reading: {PASS_F:.1f} ns est. per pass")
            svg.text(fx(PASS_F / 2), y + 15, "F", 11, "middle", "#fff", "bold")
            n = 1 if label.startswith("8") else 2
            for k in range(n):
                x0 = fx(PASS_F + k * seg); svg.rect(x0 + 1, y, fx(PASS_F + (k + 1) * seg) - x0 - 2, rh - 8, g.C["s1"], f"8 KiB at {L1_RATE:.1f} GB/s: {seg:.1f} ns")
                svg.text((x0 + fx(PASS_F + (k + 1) * seg)) / 2, y + 15, f"8 KiB, {seg:.0f} ns", 11, "middle", "#fff")
            svg.text(fx(t) + 6, y + 15, f"{t:.1f} ns measured", 11, "start", g.C["ink2"])
        else:
            x0 = fx(PASS_F + seg); svg.rect(x0 + 1, y, fx(PASS_F + 2 * seg) - x0 - 2, rh - 8, g.C["s4"], f"{E_ASM[16384]['t_pass'] - E_ASM[8192]['t_pass']:.1f} ns for 8,192 bytes")
            svg.text((x0 + fx(PASS_F + 2 * seg)) / 2, y + 15, f"{E_ASM[16384]['t_pass'] - E_ASM[8192]['t_pass']:.1f} ns", 11, "middle", "#fff")
            svg.text(fx(PASS_F + 2 * seg) + 6, y + 15, f"8,192 B / {E_ASM[16384]['t_pass'] - E_ASM[8192]['t_pass']:.1f} ns = {L1_RATE:.1f} GB/s", 11, "start", g.C["ink2"])
    g.legend(svg, L, T + rh * 3 + 24, [("F: time of a pass that is not reading (est., the same in both passes)", g.C["s2"]), ("reading at the L1's rate", g.C["s1"]), ("the difference", g.C["s4"])], w)
    return svg.out()

def lanes_fig(w=960):
    """section 8: wall-clock lanes, durations to scale over the first 170 ns of each measurement"""
    L, R, T = 262, 20, 30; tmax = 170.0; svg_rows = []
    fx = lambda t: L + t / tmax * (w - L - R)
    lanes = [("random chain, flushed, boot E", "serial", FLUSHED_E, g.C["s2"], f"one DRAM read per load, {FLUSHED_E:.1f} ns. The next address is inside the line"),
             ("sequential chain, prefetchers off, boot B", "serial", SEQ_B, g.C["s2"], f"one DRAM read per load, {SEQ_B:.1f} ns. No prefetch is issued"),
             ("boot E prefetcher: DRAM reads in flight", "waterfall", None, g.C["s3"], f"a new read every {SEQ_E:.2f} ns, each {FLUSHED_E:.1f} ns long (est.), about {IN_FLIGHT:.0f} in flight (est.)"),
             ("sequential chain, boot E: the core loads", "ticks", SEQ_E, g.C["s1"], f"one load per {SEQ_E:.2f} ns, which is {L1_CHASE:.2f} ns of L1 time plus {SEQ_E - L1_CHASE:.2f} ns (derived)"),
             ("4 KiB chain in L1, dependent loads", "serial", L1_CHASE, g.C["s1"], f"one load per {L1_CHASE:.2f} ns ({p.CONTROLS['E']['p4k_cyc']:.2f} cycles). Each waits for the one before"),
             ("L1 read loop, independent loads", "stream", LINE_NS, g.C["s1"], f"computed, not measured: one 64-byte line per {LINE_NS:.1f} ns, two 16-byte loads every cycle")]
    heights = {"serial": 36, "waterfall": 3 * int(round(IN_FLIGHT)) + 18, "ticks": 36, "stream": 36}
    H = T + sum(heights[k] for _, k, _, _, _ in lanes) + 8 * len(lanes) + 20
    svg = g.SVG(w, H)
    for tk in range(0, 171, 25):
        svg.line(fx(tk), T - 6, fx(tk), H - 20, g.C["grid"]); svg.text(fx(tk), T - 10, f"{tk}", 10, "middle", g.C["muted"])
    svg.text(w - R, T - 10, "ns, to scale", 10, "end", g.C["ink2"])
    y = T
    for label, kind, dur, color, note in lanes:
        h = heights[kind]; svg.text(L - 10, y + 15, label, 11, "end")
        if kind == "serial":
            t = 0.0; i = 0
            while t < tmax:
                x0, x1 = fx(t), fx(min(t + dur, tmax)); svg.rect(x0 + 0.5, y + 4, max(x1 - x0 - 1, 1), 16, color, f"load {i + 1}: {dur:.2f} ns")
                if dur > 20 and t + dur <= tmax: svg.text((x0 + x1) / 2, y + 16, f"load {i + 1}, {dur:.1f} ns", 10, "middle", "#fff")
                t += dur; i += 1
        elif kind == "waterfall":
            n = int(round(IN_FLIGHT)); i = 0; t = 0.0
            while t < tmax:
                yy = y + 4 + 3 * (i % n); x0, x1 = fx(t), fx(min(t + FLUSHED_E, tmax))
                svg.rect(x0, yy, max(x1 - x0, 1), 2, color, f"read {i + 1}: issued at {t:.1f} ns, arrives at {t + FLUSHED_E:.1f} ns est.", rx=0)
                t += SEQ_E; i += 1
        elif kind == "ticks":
            t = 0.0; i = 0
            while t < tmax:
                x0 = fx(t); svg.rect(x0, y + 4, max(fx(t + L1_CHASE) - x0 - 0.5, 1), 16, color, f"load {i + 1}: {dur:.2f} ns", rx=0); t += dur; i += 1
        else:
            t = 0.0; i = 0
            while t < tmax:
                x0 = fx(t); svg.rect(x0, y + 4, max(fx(t + dur) - x0 - 0.6, 0.8), 16, color, f"line {i + 1}: {dur:.1f} ns", rx=0); t += dur; i += 1
        svg.text(L + 2, y + h - 2, note, 10, "start", g.C["ink2"])
        y += h + 6
    return svg.out()

def open_(s): return f'<span class="gap">open</span>{s}'
def level_cell(d):
    name = d["level"]
    if d["hit"] and d["size"] in L3_SIZES3: name += f"; {100 * d['hit']['l3_hit']:.0f} % L3 hits"
    return name

def core_page():
    # ---------------------------------------------------------------- 4.1 latency by level
    t1 = table(["Footprint", "Chase", "Boot E ns (L3 on)", "Run 3 ns (L3 off)", "Boot C ns (L3 off)", "E vs run 3", "E / C", "L1 refills", "L2 refills", "L3 read refills", "L3 read hits (hit set)", "Reads from (boot E)"],
               [[kib(d["size"]), d["kind"], fmt(d["ns"], 3), fmt(d["ns3"], 3), fmt(d["nsC"], 3), pct(d["ns"], d["ns3"]) if d["ns3"] else "-", f"{d['ratio']:.3f}",
                 fmt(d["e"]["l1d_refill"], 2), fmt(d["e"]["l2d_refill"], 2), fmt(d["e"]["l3d_refill_rd"], 2), fmt(d["hit"]["l3_hit"], 3) if d["hit"] else "-", level_cell(d)] for d in p.LEVELS],
               f"CPU 2, ns per load of the best pass with that pass's refills per load [latency-dram-small.csv, latency-dram-large.csv, latency-dram-flushed.csv, latency-dram-seq.csv of membench-jibin-010 (boot E), 004 (run 3) and 007 (boot C)]. "
               f"E vs run 3 is (boot E minus run 3) over run 3. E / C is boot E's time over boot C's: the two boots share the commit and the build, so the ratio isolates the L3. "
               f"The L3 read hits column is the hit set's count per load on boot E (another process, latency-dram-small-l3.csv), given where that row exists. The hit set is a repeated chase, so at 512 KiB it walked a repeated list ({HIT[524288]['ns']:.3f} ns) while the level row walked a fresh one. "
               f"Run 3 has no sequential row. Boot E's rows carry an L3 that holds data. The run 3 and boot C rows were measured with the L3 holding no data, so their 192 to 384 KiB rows are L2 hits mixed with reads from the SLC across the mesh.")
    t1b = table(["Footprint", "Boot E ns", "Boot C ns", "E / C", "E: L2 read hits", "E: L3 read hits", "E: L3 read refills", "E: L3 hits, lowest to highest rep", "C: L3 read hits"],
                [[kib(h["size"]), fmt(h["ns"], 3), fmt(h["nsC"], 3), f"{h['ns'] / h['nsC']:.3f}", fmt(h["l2_hit"], 4), fmt(h["l3_hit"], 4), fmt(h["l3_refill"], 4), f"{h['hit_rng'][0]:.4f} to {h['hit_rng'][1]:.4f}", fmt(h["hitC"], 4)] for h in p.HITSET],
                f"The L3 hit set: CPU 2 with CPU 3 offline, the repeated chase, best of 3 reps with that rep's counts per load [latency-dram-small-l3.csv of 010 and 007]. 0x81C5 L2 read hits, 0x81C6 L3 read hits, 0xA2 L3 read refills (lines filled from outside the cluster). "
                f"On boot E, L3 read accesses (0xA0) equal L3 read refills plus L3 read hits within {r4.E_L3['acc_minus_refill_minus_hit']:.4f} per load on every row. On boot C the hits read {r4.C_L3['hit_max']:.4f} in every row.")
    # ---------------------------------------------------------------- 4.2 OCM by region
    def rcell(d):
        return [p.cell_label(d["cpu"], d["region"]), f"{fmt(d['E']['best'], 2)} <span class='d'>(med {fmt(d['E']['median'], 2)})</span>", fmt(d["E"]["l3"], 3), fmt(d["E"]["pf"], 2),
                fmt(d["A"]["best"], 2), fmt(d["A"]["l3"], 3), fmt(d["C"]["best"], 2), fmt(d["B"]["best"], 2), fmt(d["run3_sparse"], 2), fmt(d["run2_dense"], 2), fmt(d["E_dense"], 2) if d["E_dense"] is not None else "-"]
    t2 = table(["Cell (distance)", "Boot E route, ns", "E: L3 read refills per load", "E: L2 prefetch refills per load", "Boot A route, ns (L3 off)", "A: L3 read refills per load", "Boot C route, ns", "Boot B route, ns (prefetchers off)", "Run 3 sparse, ns", "Run 2 dense, ns", "Boot E dense (G2), ns"],
               [rcell(d) for d in p.ROUTES],
               f"ns per load, best of 2 timed passes, with the median in brackets for boot E. A route row is the dense chase of one 256 KiB region (4,096 loads per pass) run under the mesh's crosspoint counters [latency-ocm-region&lt;r&gt;-route-cpu&lt;c&gt;.csv of 010, 005, 007 and 006]. "
               f"The refill columns are means over the two passes: 0xA2 L3 read refills (lines filled from outside the cluster) and 0x81BD L2 refills made by the hardware prefetchers. "
               f"Run 3's rows are its sparse chains (7 passes of 64 loads) and run 2's its dense chains, from their own files [latency-ocm-region&lt;r&gt;-cpu&lt;c&gt;.csv of 004 and 002]. The last column is boot E's dense chase of the same cell without the counters (CPUs 2 and 8 only). "
               f"CPUs 4 and 6 have route rows on run 4 only: their sparse rows, all-five rows, SLC and control rows have not run since run 3.")
    t2b = table(["CPU (DSU)", "Boot E dense (L3 on)", "E: L3 read refills per load (mean of the passes)", "Boot E sparse", "Boot A dense (L3 off)", "Boot C dense", "Boot B dense (prefetchers off)", "Boot D dense", "Run 3 dense", "Run 3 sparse", "Run 2 dense"],
                [[f"CPU {c} (DSU {CPU_DSU[c]})", fmt(p.ALL5[c]["E"]["dense"], 3), fmt(p.ALL5_DENSE_L3[c], 4), fmt(p.ALL5[c]["E"]["sparse"], 3), fmt(p.ALL5[c]["A"]["dense"], 3), fmt(p.ALL5[c]["C"]["dense"], 3), fmt(p.ALL5[c]["B"]["dense"], 3), fmt(p.ALL5[c]["D"]["dense"], 3),
                  fmt(p.ALL5[c]["run3"]["dense"], 3), fmt(p.ALL5[c]["run3"]["sparse"], 3), fmt(p.ALL5[c]["run2"]["dense"], 3)] for c in (2, 8)]
                + [[f"CPU {c} (DSU {CPU_DSU[c]}), run 3 only", "-", "-", "-", "-", "-", "-", "-", fmt(p.ALL5_RUN3_ALL[c]["dense"], 3), fmt(p.ALL5_RUN3_ALL[c]["sparse"], 3), fmt(g.ALL5_2[c]["best"], 3)] for c in (4, 6)],
                f"The all-five chains, ns per load, best pass: dense is run 2's chain over all five regions (20,480 loads, 2 passes), sparse one line per page (320 loads, 7 passes) [latency-ocm-all5-dense-cpu&lt;c&gt;.csv, latency-ocm-all5-cpu&lt;c&gt;.csv of 010, 005, 007, 006, 008, 004 and 002]. "
                f"The ns columns are the best pass. The refill column is the mean over the dense row's 2 passes. The dense all-five row from CPU 2 is the OCM number to quote: on boot E it keeps {p.ALL5_DENSE_L3[2]:.4f} L3 read refills per load (one fill from outside the cluster per load), so none of its loads is an L3 hit.")
    t2c = table(["Distance (crosspoints)", "Cells", "Boot E route, mean ns", "Boot E range ns", "Boot A route, mean ns", "Boot A range ns", "Boot B route, mean ns", "Boot B range ns"],
                [[k, len(v)] + [x for b in "EAB" for x in (fmt(statistics.mean(d[b]["best"] for d in v), 2), f"{fmt(min(d[b]['best'] for d in v), 2)} to {fmt(max(d[b]['best'] for d in v), 2)}")] for k, v in sorted(ROUTE_BY_DIST.items())],
                f"The 20 route cells grouped by the assumed step count (|dx| + |dy| between the DSU's and the node's crosspoints). A range spans different cells, not repeats of one cell. The two cells at 5 crosspoints are both from CPU 8.")
    # ---------------------------------------------------------------- 4.3 one-core bandwidth by footprint
    def e_read(s):
        if s in p.RP_SIZES: return fmt(E_PLAIN[s], 2)
        return fmt(G8R[("per-pass", "read", s)]["agg"]["E"], 2) if ("per-pass", "read", s) in G8R else "-"
    def c_read(s):
        if s in p.RP_SIZES: return fmt(C_PLAIN[s], 2)
        return fmt(G8R[("per-pass", "read", s)]["agg"]["C"], 2) if ("per-pass", "read", s) in G8R else "-"
    def e_write(s): return fmt(WS[s]["agg"]["E"], 2) if s in WS else "-"
    t3 = table(["Buffer", "Run 3 read GB/s", "Run 3 write GB/s", "Run 3 copy GB/s", "Boot E read (L3 on)", "Boot C read (L3 off)", "Boot E write (run 3's program)", "Capacity reading, run 3 (L3 off): read and write; copy", "Capacity reading, boot E (L3 on)"],
               [[kib(d["size"]), fmt(d["read"]), fmt(d["write"]), fmt(d["copy"]), e_read(d["size"]), c_read(d["size"]), e_write(d["size"]), f"{g.bw_level(d['size'])}; {g.bw_level(2 * d['size'])}", p.bw_level_e(d["size"])] for d in g.ONE],
               f"Run 3: one thread on CPU 2, best of 3 reps, GB = 1e9 bytes, the L3 holding no data [bandwidth-dram-1core.csv of 004]. Copy reads one buffer and writes another of the same size, so its working set is twice the buffer size, and it counts bytes read plus written. "
               f"The boot E and C columns give the run 4 rows with the same kernel and buffer. The 16 KiB read is the G8 looped form (one call per pass) [bandwidth-l1-passes.csv of 010 and 007]. The 2 MiB and 32 MiB reads are the plain loop of the read variants [bandwidth-read-prefetch.csv of 010 and 007]. The writes are run 3's program on boot E at run 3's pass counts [bandwidth-write-small.csv of 010]. "
               f"The one-core sweep itself (read, write and copy at every size) is {RUN3_LABEL}. The capacity readings are hypotheses: no bandwidth row carries counters that say which level served it.")
    g8w = {x: p.G8_FITS[(x, "per-pass", "write")] for x in "CE"}
    t3_notes = f"""<ul>
<li><b>The write rows are the full width of the core's write path.</b> The C1-Nano has one 128-bit write path from the core to its L1 memory system [Arm C1-Nano TRM, "Write path"]. That is 16 bytes per cycle. The latency rows put the core at {CORE_GHZ:.1f} GHz ({g._p4k['cyc']:.2f} cycles per {g._p4k['ns']:.3f} ns at 4 KiB), so the path carries {WRITE_PATH:.1f} GB/s. Every run 3 write row from 2 MiB to 32 MiB reads {min(d['write'] for d in g.ONE if d['size'] >= 2097152):.2f} to {max(d['write'] for d in g.ONE):.2f} GB/s. So the store stream runs at the path's width at every footprint, DRAM included, and the memory behind it is not the limit for one core. The G8 write rows of boots C and E fit the same path: {min(v['rate'] for (x, f, k), v in p.G8_FITS.items() if k == 'write'):.1f} to {max(v['rate'] for (x, f, k), v in p.G8_FITS.items() if k == 'write'):.1f} GB/s (section 7).</li>
<li><b>The rows below 2 MiB fall short of the path's width because of the test program, not the core.</b> Each pass of the store kernel carries a fixed cost: the G8 write fits measure it at {g8w['C']['a_ns']:.1f} ns (boot C) and {g8w['E']['a_ns']:.1f} ns (boot E) per pass with one call per pass, and {p.G8_FITS[('C', 'asm', 'write')]['a_ns']:.1f} and {p.G8_FITS[('E', 'asm', 'write')]['a_ns']:.1f} ns with every pass inside one assembly call [bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv of 007 and 010]. A 16 KiB pass lasts {WS[16384]['ns_pass']['E']:.0f} ns on boot E, so that cost is {100 * g8w['E']['a_ns'] / WS[16384]['ns_pass']['E']:.0f} % of it and the row reads {WS[16384]['agg']['E']:.1f} GB/s. A 2 MiB pass lasts {2097152 / ONE[2097152]['write'] / 1000:.0f} us, where the cost is below 0.05 %. The same per-pass cost shapes the copy rows.</li>
<li><b>The read rows are not at the path's width.</b> The read path is dual 128-bit, 32 bytes per cycle or {READ_PATH:.1f} GB/s. Run 3's 16 KiB row, in L1, reads {ONE[16384]['read']:.1f} GB/s ({100 * ONE[16384]['read'] / READ_PATH:.0f} % of the path). The G8 rows of boots C and E show that the shortfall is a cost per pass of the loop, not the L1's rate (section 7). Every larger row is set by the level that serves it: run 3 read {ONE[33554432]['read']:.1f} GB/s from DRAM with the L3 off, and boot E reads {E_PLAIN[33554432]:.1f} GB/s with it on (boot C, same build, L3 off: {C_PLAIN[33554432]:.1f}).</li>
</ul>"""
    # ---------------------------------------------------------------- 4.4 to 4.6: run 3 only
    def one_ref(kernel, size):
        """the run 3 one-core row of the same kernel at the same per-thread buffer, else at the nearest larger one-core footprint"""
        exact = [d for d in g.ONE if d["size"] == size]
        d = exact[0] if exact else min((d for d in g.ONE if d["size"] > size), key=lambda d: d["size"])
        return d[kernel], d["size"]
    def ratio_cell(d):
        v, ref = one_ref(d["kernel"], d["size"])
        return f"{d['run3'] / v:.2f}x" + ("" if ref == d["size"] else f" <span class='d'>(one core at {kib(ref)})</span>")
    def per_core_cell(d):
        v, ref = one_ref(d["kernel"], d["size"])
        return f"{100 * d['run3'] / d['threads'] / v:.0f} %"
    def mrows(rows, label): return [[label, d["kernel"], d["threads"], kib(d["size"]), fmt(d["run2"]), fmt(d["run3"]), pct(d["run3"], d["run2"]), ratio_cell(d), per_core_cell(d)] for d in rows]
    t4 = table(["Cores", "Kernel", "Threads", "Per thread", "Run 2 GB/s", "Run 3 GB/s", "Run 3 vs run 2", "Run 3 / one core", "Per core, of one-core rate"], mrows(g.PAIR, "CPU 2 + 3 (one DSU)") + mrows(g.PERDSU, "CPUs 2, 4, 6, 8") + mrows(g.ALL8, "CPUs 2 to 9"),
               f"{RUN3_LABEL[0].upper() + RUN3_LABEL[1:]}. Best of 3 reps. Aggregate = total bytes over the slowest thread's time [bandwidth-pair.csv, bandwidth-perdsu.csv, bandwidth-all8.csv of 004 and 002]. Both runs on the same firmware. \"Run 3 / one core\" divides the run 3 aggregate by the run 3 one-core bandwidth of the same kernel at the same per-thread buffer (table 4.3); where no one-core row has that size (160 KiB, 16 MiB) the nearest larger one-core footprint is used and named, which serves from the same level. \"Per core, of one-core rate\" is the same ratio divided by the thread count: the share of its one-core rate each core kept. 100 % means the cores add up without interfering. Less means they share a limit.")
    _r4 = [d for d in g.PERDSU if d["kernel"] == "read" and d["size"] == 2097152][0]; _w4 = [d for d in g.PERDSU if d["kernel"] == "write" and d["size"] == 2097152][0]
    _r8 = [d for d in g.ALL8 if d["kernel"] == "read" and d["size"] == 2097152][0]; _one2m = ONE[2097152]
    t4_note = f"""<ul>
<li><b>Why the four-DSU rows keep 100 % on write but {per_core_cell(_r4)} on read (run 3, the L3 off).</b> The two streams hit different limits. A store stream is pinned at the core's own write path, {WRITE_PATH:.1f} GB/s, whatever is behind it: the four writers read {_w4['tmin']:.3f} to {_w4['tmax']:.3f} GB/s each, and 4 times {WRITE_PATH:.0f} is below the DRAM write ceiling that eight writers reach (table 4.4, {max(d['run3'] for d in g.ALL8 if d['kernel'] == 'write'):.0f} GB/s), so nothing shared is saturated. A read stream beyond L2 is bound by latency (a fixed number of lines in flight per core), and the aggregate is defined by the slowest thread: the four readers read {_r4['tmin']:.2f} to {_r4['tmax']:.2f} GB/s each against {_one2m['read']:.2f} for one core alone, so the fastest reader kept {100 * _r4['tmax'] / _one2m['read']:.1f} % of the one-core rate and the slowest {100 * _r4['tmin'] / _one2m['read']:.0f} %. The spread is a per-core property, not interference: with eight readers the per-thread range is {_r8['tmin']:.2f} to {_r8['tmax']:.2f} GB/s, nearly the same, and the aggregate doubles. {hyp(f" The slowest reader is the core farthest from the home nodes: the 2 MiB chase reads {g.SLC[2]['best']:.1f}, {g.SLC[4]['best']:.1f}, {g.SLC[6]['best']:.1f} and {g.SLC[8]['best']:.1f} ns from CPUs 2, 4, 6 and 8 on run 3, an {100 * (g.SLC[8]['best'] / g.SLC[2]['best'] - 1):.0f} % spread that matches the {100 * (_r4['tmax'] / _r4['tmin'] - 1):.0f} % spread in read rate. The program does not record which thread was slowest.")}</li>
<li><b>Where write loses instead.</b> In two groups of rows write keeps less than read: two writers in one DSU at 160 KiB, and eight writers at any size. There the writers share one path. For the pair it is the DSU's one mesh port. For the eight it is the DRAM write ceiling (section 8). A write stream is {WRITE_PATH:.0f} GB/s per core and a read stream beyond L2 was {min(d['read'] for d in g.ONE if d['size'] >= 2097152):.1f} to {max(d['read'] for d in g.ONE if d['size'] >= 2097152):.1f} GB/s on run 3. So writers fill a shared path about three times sooner than readers do. With the L3 on, one core reads {E_PLAIN[32 * 1048576]:.1f} GB/s from DRAM (section 7). How the multi-core rows change with it is Insufficient data (not run).</li>
</ul>"""
    t4b = table(["Writers (CPUs)", "DSUs used", "Run 2 GB/s", "Run 3 GB/s", "Run 3 vs run 2", "Per writer, run 3"],
                [[q["cpus"].replace("-", ", "), ", ".join(str(d) for d in q["dsus"]), fmt(q["run2"]), fmt(q["run3"]), pct(q["run3"], q["run2"]), f"{fmt(q['tmin'])} to {fmt(q['tmax'])}"] for q in g.PLACE],
                f"{RUN3_LABEL[0].upper() + RUN3_LABEL[1:]}. 16 MiB per writer, one pass, best of 2 reps [bandwidth-write-cpus*.csv of 004 and 002].")
    t5 = table(["Row", "Run 3 GB/s", "Run 2 GB/s", "Run 3 vs run 2", "Note"],
               [[f"Read OCM{r} from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", fmt(g.OCMBW["region"][r]), fmt(g.OCMBW["region2"][r]), pct(g.OCMBW["region"][r], g.OCMBW["region2"][r]), "256 KiB, flushed before, one pass"] for r in range(5)]
               + [["Read all five from CPU 2", fmt(g.OCMBW["all5"]), fmt(g.OCMBW["all5_2"]), pct(g.OCMBW["all5"], g.OCMBW["all5_2"]), "1.25 MiB, flushed before, one pass"],
                  ["Read OCM1 to 4 from CPUs 2, 4, 6, 8", fmt(g.OCMBW["four"]), fmt(g.OCMBW["four2"]), pct(g.OCMBW["four"], g.OCMBW["four2"]), "4 threads, one region each"],
                  ["Streaming write, all five, from CPU 2", fmt(g.OCMBW["write"]), fmt(g.OCMBW["write2"]), pct(g.OCMBW["write"], g.OCMBW["write2"]), "8 passes over 1.25 MiB"]],
               f"{RUN3_LABEL[0].upper() + RUN3_LABEL[1:]}. Best of 3 reps [bandwidth-ocm-*.csv of 004 and 002].")
    def _lvrow(size):
        e_r = fmt(E_PLAIN[size], 1) if size in p.RP_SIZES else fmt(G8R[("per-pass", "read", size)]["agg"]["E"], 1) if ("per-pass", "read", size) in G8R else "-"
        return [g.bw_level(size), f"{kib(size)} DRAM-address buffer, warm, {g._passes_one(size)} passes", fmt(ONE[size]["read"]), fmt(ONE[size]["write"]), e_r]
    t5b = table(["Level (capacity reading, hypothesis; run 3, L3 off)", "Row (one core, CPU 2)", "Run 3 read GB/s", "Run 3 write GB/s", "Boot E read GB/s (L3 on)"],
                [["Core, its own load and store paths", f"not a measured row: the TRM's dual 128-bit read path and single 128-bit write path at the {CORE_GHZ:.1f} GHz the latency rows show", f"{READ_PATH:.1f}", f"{WRITE_PATH:.1f}", "-"],
                 _lvrow(16384), _lvrow(49152), _lvrow(98304), _lvrow(262144), _lvrow(2097152),
                 ["OCM, one home node", "256 KiB, one region, flushed before, one pass; the five regions", f"{min(g.OCMBW['region']):.1f} to {max(g.OCMBW['region']):.1f}", "-", "-"],
                 ["OCM, the five home nodes", "1.25 MiB, all five regions, flushed before; read one pass, write 8 passes", fmt(g.OCMBW["all5"]), fmt(g.OCMBW["write"]), "-"],
                 _lvrow(33554432)],
                f"The run 3 columns are {RUN3_LABEL}: best of 3 reps, GB = 1e9 bytes. The first row is the core's own limit, computed from the Arm C1-Nano TRM's path widths (\"Read path: dual 128-bit\", \"Write path: 128-bit\") and the measured clock, not a bandwidth row. The level is read from the capacities, a hypothesis: no bandwidth row carries counters that say which level served it. "
                f"The DRAM-address rows are table 4.3's (many warm passes over one buffer). The OCM rows are table 4.6's (the buffer flushed from the core caches before the timed passes), so the two methods differ. "
                f"The boot E column gives the rows run 4 repeated with the L3 on: the 16 KiB G8 per-pass read and the plain 2 MiB and 32 MiB reads [bandwidth-l1-passes.csv, bandwidth-read-prefetch.csv of 010]. Run 3's 256 KiB read row ({ONE[262144]['read']:.1f} GB/s) was not repeated with the L3 on. Boot E's 256 KiB chase counts {lv(262144)['e']['l3d_refill_rd']:.2f} L3 read refills per load where run 3's counted {next(d['l3'] for d in g.LV4 if d['size'] == 262144):.2f}, so on an L3-on boot that row would be served from the L3 (hypothesis: not measured).")
    # ---------------------------------------------------------------- 4.7 attribution, 4.8 rows that moved
    t6 = table(["Row", "Own node, run 3", "Other four, mean", "Own / others", "Own node, run 2 (dense)", "Run 3 / run 2 own"],
               [[f"OCM{r} chase, CPU {c}", f"{g.ATTR[(c, r)]['own']:,}", f"{g.ATTR[(c, r)]['others_mean']:,.0f}", fmt(g.ATTR[(c, r)]["ratio"], 1), f"{g.ATTR2[(c, r)]['own']:,}", fmt(g.ATTR[(c, r)]["own"] / g.ATTR2[(c, r)]["own"], 2)] for c in (2, 4, 6, 8) for r in range(5)],
               "Run 3, the L3 off (run 4 counted the crosspoints instead, section 11). Requests received per home node (hns_pocq_reqs_recvd_all) over the whole command [cmn-counts.csv of 004 and 002]. A sparse row builds 8 chains, fills the region and flushes 7 times, so most of its requests are not the 448 timed loads.")
    t7 = table(["File", "Row", "Run 3 ns", "Boot E ns", "Boot E vs run 3"],
               [[d["file"], f"{kib(d['size'])} {d['mode'].replace('-best', '').replace('best', 'best')}", fmt(d["run3"], 3), fmt(d["run4"], 3), f"{d['pct']:+.2f} %"] for d in MOVED],
               f"Only the rows that moved 1 % or more are listed ({len(MOVED)} of {len(p.REPEAT_E3)}). The {len(p.REPEAT_E3)} rows are every best row that boot E and run 3 share by file name and footprint, core and CME, the round-trip controls set aside [the latency-*.csv and cme-latency-*.csv files of 010 and 004]. The CPU 2 control row is also set aside: run 3's latency-control-cpu2.csv holds {p.RUN3_CTRL2_BEST} best rows (one per command), so it has no single run 3 value. {p.N_WITHIN_E3[1]} are within 1 %, {p.N_WITHIN_E3[3]} within 3 % and {p.N_WITHIN_E3[5]} within 5 %. "
               f"The largest changes are the L3 rows (192 to 512 KiB) and the per-region OCM rows. Both are caused by the L3. The bandwidth files share no name between the two runs, so no bandwidth row is in this count. "
               f"Boot A against run 3, the same configuration (the L3 off, 4 KiB pages, prefetchers on), is the repeatability pair: of its {len(p.REPEAT_A3)} shared rows {p.N_WITHIN_A3[1]} are within 1 %, {p.N_WITHIN_A3[3]} within 3 % and {p.N_WITHIN_A3[5]} within 5 %, and the largest change is {p.REPEAT_A3[0]['pct']:+.2f} % ({p.REPEAT_A3[0]['file']}, {kib(p.REPEAT_A3[0]['size'])}) [asimov-c1nano-run4.html, section 3.9].")
    # ---------------------------------------------------------------- section 2 tables
    t12 = table(["Row"] + [f"Boot {x}" for x in p.BOOTS], [[lab] + [d[x] for x in p.BOOTS] for lab, d in p.FIVE],
                "Each row is the same command on every boot that has it [log.txt, latency-dram-small.csv, latency-dram-small-l3.csv, latency-dram-large.csv, latency-dram-seq.csv, bandwidth-read-prefetch.csv of 005 to 010]. The power status register is the box's two reads around the hit-set command, which cover CPU 2's cluster only [Jesse's boot E README, Coverage].")
    # ---------------------------------------------------------------- section 11: boot E route counters
    t10 = table(["Cell", "DSU crosspoint", "Data flits out of the DSU's crosspoint, boot E (e / w / n / s)", "Most at", "X-first would be", "Node crosspoint", "Data flits out of the node's crosspoint (e / w / n / s)", "Most at", "X-first would be", "Boot A: most at DSU, node"],
                [[p.cell_label(d["cpu"], d["region"]), f"{DSUS[CPU_DSU[d['cpu']]][0]},{DSUS[CPU_DSU[d['cpu']]][1]}", " / ".join(f"{d['E']['d_dsu'][k]:,}" for k in "ewns"), f"{d['E']['dom_dsu']} ({100 * d['E']['share_dsu']:.0f} %)", d["E"]["exp_dsu"],
                  f"{d['node']} ({NODES[d['node']][0]},{NODES[d['node']][1]})", " / ".join(f"{d['E']['d_node'][k]:,}" for k in "ewns"), f"{d['E']['dom_node']} ({100 * d['E']['share_node']:.0f} %)", d["E"]["exp_node"],
                  f"{d['A']['dom_dsu']} ({100 * d['A']['share_dsu']:.0f} %), {d['A']['dom_node']} ({100 * d['A']['share_node']:.0f} %)"] for d in p.ROUTES],
                f"Boot E's route rows: data flits transmitted in each direction over the whole command (the chain build, the flush, the passes and anything else on that crosspoint) [cmn-counts.csv of 010, labels route-ocm*-cpu*; boot A's from 005]. \"Most at\" is the direction with the most flits and its share of the four. \"X-first would be\" is the first link of a route that takes its X steps before its Y steps, from the two crosspoints' coordinates.")

    # ---------------------------------------------------------------- figures
    f_levels = line_chart([dict(name=f"run 3 ({p.RUN3['commit']}), the L3 off", color=g.C["muted"], pts=[(d["size"], d["ns3"], f"run 3 {kib(d['size'])} {d['kind']}: {d['ns3']:.3f} ns") for d in p.LEVELS if d["kind"] in ("repeat", "fresh")], short="run 3", dy=14),
                           dict(name=f"boot C ({p.PLATFORM['C']['commit']}), the L3 off", color=g.C["s3"], pts=[(d["size"], d["nsC"], f"boot C {kib(d['size'])} {d['kind']}: {d['nsC']:.3f} ns") for d in p.LEVELS if d["kind"] in ("repeat", "fresh")], short="boot C", dy=26, dash="5 4"),
                           dict(name=f"boot E ({p.PLATFORM['E']['commit']}), the L3 on", color=g.C["s1"], pts=[(d["size"], d["ns"], f"boot E {kib(d['size'])} {d['kind']}: {d['ns']:.3f} ns") for d in p.LEVELS if d["kind"] in ("repeat", "fresh")], short="boot E", dy=-8)],
                          marks=((32768, "L1 32 KiB"), (131072, "L2 128 KiB"), (262144, "L3 256 KiB (on, boot E)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 60), ticks_y=[0, 10, 20, 30, 40, 50, 60])
    hit_rows = []
    for s in (196608, 262144, 393216, 524288):
        for x in "CE":
            e = r4.EX[x]["l3"]["best"][s]["e"]
            hit_rows.append(dict(label=f"boot {x}, {kib(s)} ({r4.EX[x]['l3']['best'][s]['ns']:.1f} ns)", parts=[(e["l2d_hit_rd"], g.C["s1"], "L2 read hits (0x81C5)"), (e["l3d_hit_rd"], g.C["s3"], "L3 read hits (0x81C6)"), (e["l3d_refill_rd"], g.C["s2"], "L3 read refills from outside the cluster (0xA2)")]))
    f_hits = stacked_h(hit_rows, L=260, xlim=1.15)
    f_map = mesh_map(left=[("L1, 32 KiB per core", f"{lv(4096)['ns']:.1f} ns (4 KiB chase)", "#e9f1fb"),
                           ("L2, 128 KiB per DSU", f"{lv(131072)['ns']:.1f} ns (128 KiB chase)", "#e9f1fb"),
                           ("L3, 256 KiB per DSU (on, boot E)", f"hit about {L3_EST:.0f} ns est.; {HIT[196608]['ns']:.1f} ns at 192 KiB ({100 * HIT[196608]['l3_hit']:.0f} % hits)", "#e9f1fb"),
                           ("mesh: to the home node that owns the line", "the grid on the right; one step per crosspoint", "#f9f9f7"),
                           (["5 home nodes (HN-S)", "SLC 768 KiB each (12 ways), \"L4\" cache", "OCM 256 KiB each (4 ways), addressable SRAM"], f"{lv(2097152, 'fresh')['ns']:.1f} ns (2 MiB fresh chain, in the SLC)", "#fdeee6"),
                           ("DRAM, behind the home node (emulator)", f"{FLUSHED_E:.1f} ns (8 MiB flushed)", "#f1f1ee")],
                     node_labels={NODE_OF_REGION[r]: [f"CPU 2: {next(d for d in p.ROUTES if d['cpu'] == 2 and d['region'] == r)['E']['best']:.1f} ns"] for r in range(5)},
                     paths=[(1, NODE_OF_REGION[r], g.C["s2"], "") for r in range(5)])
    f_ocm = dumbbell([dict(label=p.cell_label(d["cpu"], d["region"]), a=d["A"]["best"], b=d["E"]["best"]) for d in p.ROUTES], names=("boot A route (L3 off)", "boot E route (L3 on)"), colors=(g.C["muted"], g.C["s1"]))
    f_sparse = dumbbell([dict(label=p.cell_label(d["cpu"], d["region"]), a=d["run3"]["best"], b=d["E"]["best"]) for d in p.OCM_SPARSE], names=("run 3 sparse (L3 off)", "boot E sparse (L3 on)"), colors=(g.C["muted"], g.C["s1"]))
    all5_names = [p.BOOT_SHORT[x] for x in "EACBD"] + ["run 3 (L3 off)"]; all5_cols = [p.BOOT_COL[x] for x in "EACBD"] + [g.C["ink2"]]
    f_all5 = dotplot([dict(label=f"CPU {c}: all five, {s} ({'20,480' if s == 'dense' else '320'} loads)", vals=[p.ALL5[c][x][s] for x in "EACBD"] + [p.ALL5[c]["run3"][s]]) for s in ("dense", "sparse") for c in (2, 8)],
                     all5_names, all5_cols, L=300, xlim=(24, 29))
    e_read_l1 = [(s, G8R[("per-pass", "read", s)]["agg"]["E"], f"boot E read {kib(s)} (G8 per-pass): {G8R[('per-pass', 'read', s)]['agg']['E']:.3f} GB/s") for s in p.G8_SIZES]
    e_read_dram = [(s, E_PLAIN[s], f"boot E plain read {kib(s)}: {E_PLAIN[s]:.3f} GB/s") for s in p.RP_SIZES]
    e_write_pts = [(s, G8R[("per-pass", "write", s)]["agg"]["E"], f"boot E write {kib(s)} (G8 per-pass): {G8R[('per-pass', 'write', s)]['agg']['E']:.3f} GB/s") for s in p.G8_SIZES] + [(d["size"], d["agg"]["E"], f"boot E write {kib(d['size'])} (run 3's program): {d['agg']['E']:.3f} GB/s") for d in p.WRITE_SMALL if d["size"] > 24576]
    f_bw1 = line_chart([dict(name="run 3 read (L3 off)", color=g.C["s1"], pts=[(d["size"], d["read"]) for d in g.ONE], dash="5 4", short="run 3 read", dy=14), dict(name="run 3 write (L3 off)", color=g.C["s2"], pts=[(d["size"], d["write"]) for d in g.ONE], dash="5 4", short="run 3 write", dy=14),
                        dict(name="run 3 copy, read + write bytes (L3 off)", color=g.C["s3"], pts=[(d["size"], d["copy"]) for d in g.ONE], dash="5 4", short="run 3 copy"),
                        dict(name="boot E read (L3 on), G8 L1 rows", color=g.C["s1"], pts=e_read_l1, short="boot E read, L1", dy=-8),
                        dict(name="boot E read (L3 on), plain loop", color=g.C["s1"], pts=e_read_dram, short="boot E read", dy=-8),
                        dict(name="boot E write (L3 on)", color=g.C["s2"], pts=e_write_pts, short="boot E write", dy=-8)],
                       ylabel="GB/s, one thread on CPU 2", marks=((32768, "L1 32 KiB"), (131072, "L2 128 KiB"), (262144, "L3 256 KiB (on, boot E)"), (SLC_BYTES, "SLC 3.75 MiB")), ylim=(0, 65), ticks_y=[0, 10, 20, 30, 40, 50, 60])
    f_read = dotplot([dict(label=f"{name}, {kib(s)}", vals=[RV[(k, s)]["agg"][x] for x in "EC"] + [RV[(k, s)]["run3"]]) for s in p.RP_SIZES for k, name in p.RP_KERNELS],
                     ["boot E (L3 on)", "boot C (L3 off)", "run 3 plain loop (L3 off)"], [g.C["s1"], g.C["s3"], g.C["muted"]], unit="GB/s", xlim=(0, 27))
    g8_names = [f"boot {x}, {f}" for x in "CE" for f in ("per-pass", "asm")]; g8_cols = [g.C["s3"], g.C["s7"], g.C["s1"], g.C["s2"]]
    f_g8 = dotplot([dict(label=f"{k}, {kib(s)}", vals=[G8R[(f, k, s)]["agg"][x] for x in "CE" for f in ("per-pass", "asm")]) for k in ("read", "write") for s in p.G8_SIZES], g8_names, g8_cols, unit="GB/s", xlim=(20, 66))
    wrows = [dict(label=f"{'CPU 2+3' if d['threads'] == 2 else 'CPUs 2,4,6,8' if d['threads'] == 4 else 'CPUs 2 to 9'} write {kib(d['size'])}", a=d["run2"], b=d["run3"]) for d in g.PAIR + g.PERDSU + g.ALL8 if d["kernel"] == "write"]
    wrows += [dict(label=f"writers {q['cpus'].replace('-', ',')} (DSUs {','.join(map(str, q['dsus']))})", a=q["run2"], b=q["run3"]) for q in g.PLACE]
    f_write = dumbbell(wrows, unit="GB/s", names=("run 2 (L3 off)", "run 3 (L3 off)"))
    brows = [dict(label=f"OCM{r} from CPU 2 ({dist(2, NODE_OF_REGION[r])} xp)", v=g.OCMBW["region"][r]) for r in range(5)] + [dict(label="all five from CPU 2", v=g.OCMBW["all5"]), dict(label="OCM1 to 4 from four CPUs", v=g.OCMBW["four"], color=g.C["s3"]), dict(label="streaming write, all five", v=g.OCMBW["write"], color=g.C["s2"])]
    f_ocmbw = bars_h(brows, xlim=70)
    crow = g.CMN4["ocm-region1-cpu2"]
    f_cmn = bars_h([dict(label=f"node {n} (OCM{NODES[n][2]})", v=crow["node"][n], color=g.C["s2"] if n == 160 else g.C["s1"]) for n in NODES], unit="requests")
    ratio_lo, ratio_hi = min(a["ratio"] for a in g.ATTR.values()), max(a["ratio"] for a in g.ATTR.values())

    # ---------------------------------------------------------------- numbers the text quotes
    PE, PC, PA, PB, PD = (p.PLATFORM[x] for x in "ECABD")
    g8_asm_hi = max(ASM16_24); g8_asm_lo = min(ASM16_24)
    read_resid = [v["resid_pct"] for (x, f, k), v in p.G8_FITS.items() if k == "read"]; write_resid = [v["resid_pct"] for (x, f, k), v in p.G8_FITS.items() if k == "write"]
    pf4 = {s: RV[("read-pf4", s)]["agg"] for s in p.RP_SIZES}
    walk_d = p.WALK_RATES["D"]
    gm = {k: v["gm"] for k, v in p.RATIOS.items()}
    n_e_route_below = sum(1 for d in p.ROUTES if d["E"]["l3"] < 0.8)
    g8_4k_spread = {x: 100 * (max(r4.G8[x][("per-pass", "read")]["rows"][4096]["reps"]) / min(r4.G8[x][("per-pass", "read")]["rows"][4096]["reps"]) - 1) for x in "CE"}   # % spread of the 5 reps
    mem_q = "message-to-jesse-round4.md"

    body = f"""
<div class="short"><p><b>Short version.</b> With the DSU L3 on (run 4 boot E), one core reads from its L1 in {lv(4096)['ns']:.1f} ns, from the L2 in {lv(131072)['ns']:.1f} ns, from an L3 hit in about {L3_EST:.0f} ns est., from the SLC in {lv(2097152, 'fresh')['ns']:.1f} ns and from DRAM in {FLUSHED_E:.1f} ns (every line flushed). One core reads DRAM at {E_PLAIN[33554432]:.1f} GB/s with the L3 on, against {C_PLAIN[33554432]:.1f} GB/s with it off (boot C, the same build). The bandwidth set of sections 4.4 to 4.6, 8 and 9 is run 3's, measured with the L3 holding no data.</p></div>
<ul>
<li><b>The L3 step.</b> Runs 1 to 3 and boots A to D measured with the L3 of CPUs 2 to 9 holding no data (register 0x0, 0 L3 hits per load). Boot E's rebuilt SCP turns it on (register {PE['pwrstat'][0]}). The 192, 256 and 384 KiB chases (the hit-set rows) then read {HIT[196608]['ns']:.1f}, {HIT[262144]['ns']:.1f} and {HIT[393216]['ns']:.1f} ns with {100 * HIT[196608]['l3_hit']:.0f}, {100 * HIT[262144]['l3_hit']:.0f} and {100 * HIT[393216]['l3_hit']:.0f} % L3 hits per load, against {HIT[196608]['nsC']:.1f}, {HIT[262144]['nsC']:.1f} and {HIT[393216]['nsC']:.1f} ns on boot C (section 5).</li>
<li><b>Repeatability.</b> Of the {len(p.REPEAT_E3)} rows boot E and run 3 share, {p.N_WITHIN_E3[1]} agree within 1 % and {p.N_WITHIN_E3[5]} within 5 %. The rows that moved most are the L3 rows ({p.REPEAT_E3[0]['pct']:+.1f} % at {kib(p.REPEAT_E3[0]['size'])}) and the per-region OCM rows. Boot A against run 3, the same configuration, agrees within 1 % on {p.N_WITHIN_A3[1]} of {len(p.REPEAT_A3)} rows (section 4.8).</li>
<li><b>OCM.</b> The dense all-five chain from CPU 2 reads {p.ALL5[2]['E']['dense']:.2f} ns on boot E (run 3 {p.ALL5[2]['run3']['dense']:.2f}, boot A {p.ALL5[2]['A']['dense']:.2f}, boot C {p.ALL5[2]['C']['dense']:.2f}) with one L3 read refill per load. That is the OCM number to quote. On boot E only {p.ROUTE_L3_RNG['E'][0]:.2f} to {p.ROUTE_L3_RNG['E'][1]:.2f} of the loads in the per-region route rows are read from the mesh (L3 read refills per load). The other loads are served by the L3, so those rows are below the true OCM latency (section 6).</li>
<li><b>Bandwidth.</b> One core reads DRAM at {E_PLAIN[2097152]:.1f} GB/s (2 MiB) and {E_PLAIN[33554432]:.1f} GB/s (32 MiB) with the L3 on. In one assembly call the L1 reads {g8_asm_lo:.1f} to {g8_asm_hi:.1f} GB/s at 16 and 24 KiB, {100 * g8_asm_hi / READ_PATH:.0f} % of the {READ_PATH:.0f} GB/s read path, and writes fit the {WRITE_PATH:.0f} GB/s write path (section 7). Eight cores wrote {max(d['run3'] for d in g.ALL8 if d['kernel'] == 'write'):.0f} GB/s and one core read OCM at {min(g.OCMBW['region']):.1f} to {max(g.OCMBW['region']):.1f} GB/s per region on run 3, the L3 off (sections 9 and 10).</li>
</ul>

<h2 id="words">1. Words used here</h2>
{words(p.words_core())}

<h2 id="run">2. The run and the platform</h2>
<ul>
<li><b>Where and when.</b> Run 4 boot E ran on one emulated Asimov hemisphere on the GA13 Palladium (image hemi_rtws_tlm, RTL 0d9e214, release a10280100) on {PE['date']} UTC as one job: run_followup.sh at cache-mem-perf commit {PE['commit']}. {PE['chip_s']:.3f} s of chip time, {PE['commands']} commands, all exit 0 ({p.E['FAILED']} failed), 113 files back with matching checksums [Jesse's boot E README, Read first and The run].</li>
<li><b>Platform.</b> Boot A's, with one change: the SCP rebuilt as {PE['scp']} to stage the full-L3 operating mode (all slices, the whole L3 RAM open) for the clusters of CPUs 2 to 9 before they power on. The stock SCP stages it for cluster 0 only, so on runs 1 to 3 and boots A to D the L3 of CPUs 2 to 9 held no data. TF-A {PE['tfa']}, Linux 6.18.36, 256 huge pages of 2 MiB, /dev/ocm in 4 KiB pages ({len(p.E['MAPS'])} mappings, none with the contiguous hint), CPUs 2 to 9 isolated, CPU 3 offline for the whole script, the data prefetchers on. IMP_CLUSTERPWRSTAT_EL1 read {PE['pwrstat'][0]} before and {PE['pwrstat'][1]} after the hit-set command: the full-RAM encoding. That reading covers CPU 2's cluster only [Jesse's boot E README, The SCP and L3 power]. DRAM is an emulator memory, not LPDDR5X, so no DRAM number is silicon-like [the same README, DRAM caveat].</li>
<li><b>Counters.</b> The PMU driver reports {p.E['PMU_COUNTERS']} counters, so no group of six events was multiplexed: every counted row reads perf_cov 1.0000 ({len(p.E['COV_ROWS'])} latency rows and {p.BW_COV_ROWS_E} bandwidth rows) and no row carries a "# perf:" flag.</li>
<li><b>Controls.</b> The 4 KiB repeated chase reads {p.CONTROLS['E']['p4k']:.3f} ns ({p.CONTROLS['E']['p4k_cyc']:.2f} cycles) on boot E, {p.CONTROLS['run3']['p4k']:.3f} on run 3 and {min(p.CONTROLS[x]['p4k'] for x in p.BOOTS):.3f} to {max(p.CONTROLS[x]['p4k'] for x in p.BOOTS):.3f} on the five boots. The CME round trip reads {min(p.CONTROLS[x]['rt'][0] for x in p.BOOTS):.3f} to {max(p.CONTROLS[x]['rt'][1] for x in p.BOOTS):.3f} ns on every boot (run 3: {p.CONTROLS['run3']['rt'][0]:.3f} to {p.CONTROLS['run3']['rt'][1]:.3f}). The two uncounted 4 KiB controls read {p.CONTROLS['E']['ctrl'][2]:.3f} ns (CPU 2) and {p.CONTROLS['E']['ctrl'][8]:.3f} ns (CPU 8) on boot E [latency-dram-small.csv, cme-latency-*.csv, latency-control-cpu*.csv].</li>
<li><b>Run 3,</b> whose rows stay on this page where run 4 did not repeat them: membench-jibin-{p.RUN3['run_id']}, commit {p.RUN3['commit']}, SCP {p.RUN3['scp']}, TF-A {p.RUN3['tfa']}, {p.RUN3['date']}, {p.RUN3['chip_s']:.3f} s of chip time, {p.RUN3['commands']} commands, {p.RUN3['files']} CSV files, the L3 holding no data [Jesse's run 3 README].</li>
</ul>
<p><b>The five boots of run 4.</b> Each boot is one job with one firmware and program configuration. Boot C is the comparison that isolates the L3: the same commit and build as E with the L3 off. Boot A is the configuration closest to run 3. Boots B and D have the data prefetchers off.</p>
{t12}

<h3 id="changes">2.1 What changed from run 3 to run 4 boot E</h3>
<ul>
<li><b>The code</b> went from commit {p.RUN3['commit']} to {PE['commit']}. The latency program gained the prefetch, TLB, walk and hit events, the sequential chain, the route rows and the vary chain. The bandwidth program gained the read variants and the G8 rows. The flags of every repeated row are unchanged, so a repeated row's numbers compare [Jesse's boot E README, Against boot C; follow-up-run-plan.md].</li>
<li><b>The firmware.</b> One firmware component changed: the SCP, rebuilt to stage the full L3 for the clusters of CPUs 2 to 9. TF-A, the kernel and the OCM mapping are run 3's. So the L3 is the one platform difference between run 3's rows and boot E's, beside the run-to-run noise that boot A against run 3 measures (section 4.8).</li>
<li><b>Rows dropped.</b> The bandwidth set (the one-core sweep, multi-core DRAM, writer placement, OCM bandwidth) and the OCM, SLC and control rows of CPUs 4 and 6 did not run on run 4. Their numbers on this page are run 3's and are labelled so.</li>
<li><b>Rows added.</b> The L3 hit set (64 KiB to 512 KiB), the sequential 8 MiB chain, the one-core read variants at 2 MiB and 32 MiB, the G8 L1 rows, the TLB-set and walk rows of CPU 2, and the 20 route rows under the crosspoint counters.</li>
<li><b>Size.</b> Run 3 ran {p.RUN3['commands']} commands in {p.RUN3['chip_s']:.3f} s of chip time. Boot E ran {PE['commands']} commands in {PE['chip_s']:.3f} s [Jesse's READMEs of 004 and 010].</li>
</ul>

<h2 id="map">3. The hemisphere map</h2>
<p>The left column is the path one load takes from CPU 2 outward (cluster caches, then the mesh to the home node, with DRAM behind it), with boot E's chase time at the footprint that reads from each level. The grid is the mesh as the kernel's debugfs map prints it [sysinfo.txt, "arm-cmn mesh map"], with the five home nodes and the five DSU ports on their crosspoints. The dashed paths run from CPU 2's port to each OCM home node, horizontal first (a simplification: the real route is the mesh's choice). The label under each home node is CPU 2's best dense chase of that region on boot E (the route row, table 4.2).</p>
{fig(f_map, f"From CPU 2 on boot E, a dense OCM chase reads {min(d['E']['best'] for d in p.ROUTES if d['cpu'] == 2):.1f} to {max(d['E']['best'] for d in p.ROUTES if d['cpu'] == 2):.1f} ns by region, the SLC {lv(2097152, 'fresh')['ns']:.1f} ns and flushed DRAM {FLUSHED_E:.1f} ns.", f"The L3 box is new on this boot: on runs 1 to 3 it held no data. Hover a box or a dot for its details. The crosspoint of each box comes from the node ids and was checked against the map text by this script [sysinfo.txt].")}

<h2 id="tables">4. Summary tables</h2>
<h3 id="t41">4.1 Latency by level, CPU 2, boot E against run 3 and boot C</h3>{t1}
<p><b>The hit set.</b> The same chases from 64 KiB to 512 KiB run again with the hit events beside the refill events.</p>{t1b}
<h3 id="t42">4.2 OCM latency by region, from four CPUs</h3>{t2}{t2b}{t2c}
<h3 id="t43">4.3 One-core bandwidth by footprint, CPU 2</h3>{t3}{t3_notes}
<h3 id="t44">4.4 Multi-core DRAM bandwidth</h3>{t4}{t4_note}
<h3 id="t45">4.5 Writer placement</h3>{t4b}
<h3 id="t46">4.6 OCM bandwidth</h3>{t5}
<h3 id="t461">4.6.1 One core, read and write by level (tables 4.3 and 4.6 combined)</h3>{t5b}
<h3 id="t47">4.7 Home-node attribution of the 20 sparse per-region rows</h3>{t6}
<p>Boot E's route rows count the two crosspoints' outgoing directions instead of the home nodes' requests (section 11). The data flits leave along the X direction first at the DSU in {p.XFIRST['E'][0]} of 20 cells and at the node in {p.XFIRST['E'][1]} of 20 on boot E, as on boot A ({p.XFIRST['A'][0]} and {p.XFIRST['A'][1]} of 20) [cmn-counts.csv of 010 and 005].</p>
<h3 id="t48">4.8 Every row that moved 1 % or more between run 3 and boot E</h3>{t7}

<h2 id="f-levels">5. Latency by level, CPU 2</h2>
{fig(f_levels, f"The L3 step appears on boot E: the 192, 256 and 384 KiB chases read {min(d['ratio'] for d in p.LEVELS if d['size'] in L3_SIZES3):.2f} to {max(d['ratio'] for d in p.LEVELS if d['size'] in L3_SIZES3):.2f} times boot C's, while the 4 to 128 KiB chases read {min(SMALL_RATIO):.3f} to {max(SMALL_RATIO):.3f} times.", f"Steps at 48 KiB (past L1), 192 KiB (past L2) and 4 to 16 MiB (past the SLC) [table 4.1]. Run 3 and boot C agree within {100 * max(abs(d['ns3'] / d['nsC'] - 1) for d in p.LEVELS if d['ns3']):.1f} % at every footprint: their 192 to 384 KiB rows are L2 hits mixed with reads from the SLC across the mesh. The 8 MiB flushed row, not drawn, reads {FLUSHED_E:.1f} ns on boot E and {lv(8388608, 'flushed')['nsC']:.1f} on boot C, the DRAM load-to-use time with every cache missed.")}
{fig(f_hits, f"With the L3 on, the 192 to 384 KiB chases are served {100 * min(HIT[s]['l3_hit'] for s in L3_SIZES3):.0f} to {100 * max(HIT[s]['l3_hit'] for s in L3_SIZES3):.0f} % from the L3 and read {HIT[196608]['ns']:.1f} to {HIT[393216]['ns']:.1f} ns, against {HIT[196608]['nsC']:.1f} to {HIT[393216]['nsC']:.1f} ns on boot C, where the same reads came from the mesh.", f"Per load of the best rep, boots C and E [latency-dram-small-l3.csv of 007 and 010; table 4.1, the hit set]. At 512 KiB the L3 holds part of the set: {100 * HIT[524288]['l3_hit']:.0f} % L3 hits and {100 * HIT[524288]['l3_refill']:.0f} % outside refills per load.")}
<ul>
<li><b>An L3 hit costs about {L3_EST:.1f} ns (est.).</b> The number is derived, not measured: {p.L3_HIT_EST_HOW}. The 256 KiB row gives {p.L3_HIT_EST[262144]:.1f} ns and the 384 KiB row {p.L3_HIT_EST[393216]:.1f} ns [latency-dram-small-l3.csv of 010 and 007]. The 192 KiB row gives {p.L3_HIT_EST_192:.1f} ns est. by the same recipe. It is left out of the range because under half of its loads hit the L3 ({100 * p.L3_HIT_192_SHARE:.0f} %), so the subtracted L2 term is as large as the L3 term there. asimov-bench's chase of a 192 KiB set on an older RTL read 15.16 ns per load and took it as a lower bound on an L3 hit. Boot E's 192 KiB row reads {HIT[196608]['ns']:.3f} ns with {100 * HIT[196608]['l3_hit']:.0f} % L3 hits [Jesse's boot E README, Against asimov-bench].</li>
<li><b>The SLC and DRAM rows stayed.</b> 2 MiB reads {lv(2097152, 'fresh')['ns']:.3f} ns on E against {lv(2097152, 'fresh')['nsC']:.3f} on C. The 8 MiB flushed row reads {FLUSHED_E:.3f} against {lv(8388608, 'flushed')['nsC']:.3f} ns. At 16 and 32 MiB E reads {p.EC_DELTA[16777216]:.2f} and {p.EC_DELTA[33554432]:.2f} ns more than C ({lv(33554432, 'fresh')['ns']:.3f} against {lv(33554432, 'fresh')['nsC']:.3f} ns at 32 MiB), with one outside refill per load on both boots. Boots A, B and D read {p.L32M['A']:.3f}, {p.L32M['B']:.3f} and {p.L32M['D']:.3f} ns at 32 MiB, and run 3 {p.L32M['run3']:.3f}. {hyp(f" The extra time is translation walks: the 16 and 32 MiB chains span more 4 KiB pages than the L2 TLB covers, and boot E's 32 MiB walk row counts {p.WALK_RATES['E']['walk_row']:.2f} walks per load. A walk-counted 32 MiB row on E and C in one process would test it.")}</li>
<li><b>The {FLUSHED_E:.1f} ns DRAM data read is a fixed-delay memory model.</b> On boot B an address-order 8 MiB chain (the sequential chain, prefetchers off) reads {p.DRAM_MODEL['seq_B']:.3f} ns and a random one {p.DRAM_MODEL['random_B']:.3f} ns [latency-dram-seq.csv, latency-dram-flushed.csv of 006]. So the memory behind the home node answers in a fixed time whatever the address order. Of the {p.DRAM_MODEL['flushed_E']:.1f} ns, {p.DRAM_MODEL['home_hop']:.1f} ns is the home-node round trip (the 2 MiB SLC row) and the rest, about {p.DRAM_MODEL['rest_est']:.0f} ns est., is the model's delay. The model's configured delay was asked of Jesse and is unanswered [{mem_q}].</li>
<li><b>The sequential chain fell to {SEQ_E:.3f} ns</b> on E against {SEQ_C:.3f} on C and {p.SEQ_ROW['ns']['A']:.3f} on A, with {p.SEQ_ROW['l1pf']['E']:.4f} L1 prefetch refills per load on E and {p.SEQ_ROW['l1pf']['C']:.4f} on C. With the prefetchers off (boots B and D) the same chain reads {p.SEQ_ROW['ns']['B']:.3f} and {p.SEQ_ROW['ns']['D']:.3f} ns, the DRAM time [latency-dram-seq.csv of 005 to 010]. {hyp(" With the L3 holding data the prefetcher's stream drains into the L3 and the L2 refills complete sooner. The sequential row with the prefetchers off and the L3 on (not run) would show how much of the difference is the prefetcher's.")}</li>
</ul>

<h2 id="f-ocm">6. OCM latency by region: boot E against the L3-off boots</h2>
<p>Run 3's per-region rows walked sparse chains (one line per 4 KiB page) with the L3 holding no data. Run 4 ran each cell's dense chain under the crosspoint counters (the route rows) on five boots, and on boot E the L3 holds data. The rows are grouped by CPU and ordered by distance within each CPU.</p>
{fig(f_ocm, f"Boot E's route rows read {min(ROUTE_E_VS_A):+.2f} to {max(ROUTE_E_VS_A):+.2f} ns against boot A's ({sum(1 for x in ROUTE_E_VS_A if x < 0)} of 20 cells faster), and count {p.ROUTE_L3_RNG['E'][0]:.2f} to {p.ROUTE_L3_RNG['E'][1]:.2f} L3 read refills per load against A's {p.ROUTE_L3_RNG['A'][0]:.2f} to {p.ROUTE_L3_RNG['A'][1]:.2f}.", f"Best of 2 passes [latency-ocm-region&lt;r&gt;-route-cpu&lt;c&gt;.csv of 005 and 010; table 4.2]. On boot E part of each pass's lines were still in the L3 from the pass before ({n_e_route_below} of 20 cells below 0.8 refills per load), so the E rows are not OCM latency alone. Boot C's route rows count {p.ROUTE_L3_RNG['C'][0]:.2f} to {p.ROUTE_L3_RNG['C'][1]:.2f} per load.")}
{fig(f_sparse, f"Boot E's sparse rows read {min(d['E']['best'] - d['run3']['best'] for d in p.OCM_SPARSE):+.2f} to {max(d['E']['best'] - d['run3']['best'] for d in p.OCM_SPARSE):+.2f} ns against run 3's on the same ten cells.", f"Best of 7 passes of 64 loads [latency-ocm-region&lt;r&gt;-cpu&lt;c&gt;.csv of 010 and 004]. CPU 2's sparse rows count {p.SPARSE_L3_RNG_CPU2['E'][0]:.2f} to {p.SPARSE_L3_RNG_CPU2['E'][1]:.2f} L3 read refills per load on boot E against {p.SPARSE_L3_RNG_CPU2['A'][0]:.2f} to {p.SPARSE_L3_RNG_CPU2['A'][1]:.2f} on A and {p.SPARSE_L3_RNG_CPU2['C'][0]:.2f} to {p.SPARSE_L3_RNG_CPU2['C'][1]:.2f} on C (pass means), so on E {1 - p.SPARSE_L3_RNG_CPU2['E'][1]:.2f} to {1 - p.SPARSE_L3_RNG_CPU2['E'][0]:.2f} of a sparse pass's loads take no refill from outside the cluster.")}
{fig(f_all5, f"The dense all-five chain from CPU 2 reads {p.ALL5[2]['E']['dense']:.2f} ns on boot E with {p.ALL5_DENSE_L3[2]:.4f} L3 read refills per load (mean of its 2 passes): no L3 hits, so this row is the OCM number on the L3-on boot too.", f"Best pass [latency-ocm-all5-dense-cpu&lt;c&gt;.csv, latency-ocm-all5-cpu&lt;c&gt;.csv of 005 to 010 and 004; table 4.2]. The five boots and run 3 span {min(p.ALL5[2][x]['dense'] for x in list(p.BOOTS) + ['run3']):.2f} to {max(p.ALL5[2][x]['dense'] for x in list(p.BOOTS) + ['run3']):.2f} ns on CPU 2's dense row. Boot E's sparse all-five rows read below its dense ones ({p.ALL5[2]['E']['sparse']:.2f} and {p.ALL5[8]['E']['sparse']:.2f} ns) and count {p.E['SPLIT_ALL5'][(2, 'sparse')]['l3']:.2f} and {p.E['SPLIT_ALL5'][(8, 'sparse')]['l3']:.2f} L3 read refills per load (means of their 7 passes). The other loads are served by the L3, so those rows are below the true OCM latency.")}
<ul>
<li><b>Distance.</b> With the prefetchers off (boot B) the 20 route cells fit the assumed step counts within {p.ROUTE_FIT['B']['rms']:.2f} ns rms: {p.ROUTE_FIT['B']['a']:.2f} ns + {p.ROUTE_FIT['B']['bx']:.2f} ns per X step + {p.ROUTE_FIT['B']['by']:.2f} ns per Y step. Boot D repeats it ({p.ROUTE_FIT['D']['bx']:.2f}, {p.ROUTE_FIT['D']['by']:.2f}, {p.ROUTE_FIT['D']['rms']:.2f} ns rms). With the prefetchers on the residual is {p.ROUTE_FIT['A']['rms']:.2f} ns on A and {p.ROUTE_FIT['C']['rms']:.2f} on C, so most of the within-distance spread of the earlier runs was the prefetchers'. On E the fit is not usable ({p.ROUTE_FIT['E']['rms']:.2f} ns rms). Part of the route rows' loads are served by the L3 [asimov-c1nano-run4.html, sections 11 and 14.4].</li>
<li><b>The contiguous hint</b> (boots C and D, the OCM in 64 KiB translations) lowers the per-region rows. Over the 69 core OCM rows, D reads {gm[('D', 'B')]:.3f} times B by geometric mean (the hint alone, prefetchers off on both) and C {gm[('C', 'A')]:.3f} times A (the hint with the prefetchers on). The L1 data TLB refills per pass fall from {p.TLB_PASS_RNG['A'][0]:.0f} to {p.TLB_PASS_RNG['A'][1]:.0f} on A to {p.TLB_PASS_RNG['C'][0]:.0f} to {max(p.TLB_PASS_RNG['C'][1], p.TLB_PASS_RNG['D'][1]):.0f} on C and D. Boot E, back on 4 KiB pages, reads {p.TLB_PASS_RNG['E'][0]:.0f} to {p.TLB_PASS_RNG['E'][1]:.0f} [latency-ocm-region&lt;r&gt;-&lt;shape&gt;-tlb-cpu2.csv of 005 to 010]. The prefetchers cost more than the hint: C reads {gm[('C', 'D')]:.3f} times D (the prefetchers, both with the hint).</li>
<li><b>The sparse rows' excess over the dense ones</b> is TLB refills plus prefetch fills. On CPU 2 the mean gap falls from {p.GAP_MEAN['A']:.1f} ns (boot A) to {p.GAP_MEAN['B']:.1f} ns with the prefetchers off (B), {p.GAP_MEAN['C']:.1f} ns with the hint (C) and {p.GAP_MEAN['D']:.1f} ns with both (D). On E it is {p.GAP_MEAN['E']:.1f} ns [asimov-c1nano-run4.html, section 13.2]. A sparse-chain load on E takes {min(p.E['H3_L1']):.2f} to {max(p.E['H3_L1']):.2f} L1 data TLB refills and {min(p.E['H3_WALK']):.2f} to {max(p.E['H3_WALK']):.2f} table walks (pass means) [latency-ocm-region&lt;r&gt;-tlb-cpu2.csv of 010].</li>
<li>{gap(f" The walk rate on the 32 MiB stimulus differs between two processes of one boot: on boot D the TLB-set row counts {walk_d['tlb_set']:.3f} walks per load and the walk row {walk_d['walk_row']:.3f} (E: {p.WALK_RATES['E']['tlb_set']:.3f} and {p.WALK_RATES['E']['walk_row']:.3f}) [latency-dram-tlb-cpu2.csv, latency-dram-walk-cpu2.csv of 008 and 010]. So D's {walk_d['tlb_set']:.3f} is not the hint's effect (the hint does not reach DRAM pages), and the cause is Insufficient data: the same chain run in several processes of one boot, each walk-counted, would show whether the rate is the process's placement.")}</li>
</ul>

<h2 id="f-bw1">7. One-core bandwidth by level</h2>
{fig(f_bw1, f"With the L3 on one core reads {E_PLAIN[2097152]:.1f} GB/s at 2 MiB and {E_PLAIN[33554432]:.1f} GB/s at 32 MiB, against run 3's {ONE[2097152]['read']:.1f} and {ONE[33554432]['read']:.1f} with the L3 off. Write holds {min(d['write'] for d in g.ONE):.1f} to {max(d['write'] for d in g.ONE):.1f} GB/s at every footprint.", f"The dashed series are run 3's one-core sweep (the L3 off) [bandwidth-dram-1core.csv of 004]. The solid series are boot E's rows: the G8 per-pass rows at 4 to 24 KiB, run 3's program at 48 to 256 KiB (write) and the plain read loop at 2 and 32 MiB [bandwidth-l1-passes.csv, bandwidth-write-small.csv, bandwidth-read-prefetch.csv of 010]. The 48 to 256 KiB read rows and the copy rows were not repeated with the L3 on.")}
{fig(f_read, f"The plain read loop reads {E_PLAIN[2097152] / C_PLAIN[2097152]:.2f} times boot C's rate at 2 MiB and {E_PLAIN[33554432] / C_PLAIN[33554432]:.2f} times at 32 MiB with the L3 on. The PRFM variants read below the plain loop on E ({pf4[2097152]['E']:.1f} and {pf4[33554432]['E']:.1f} GB/s with PRFM 4 lines ahead).", f"One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-read-prefetch.csv of 010 and 007; run 3's plain loop from bandwidth-dram-1core.csv of 004]. On boot C the PRFM hint adds little: {pf4[2097152]['C']:.2f} against {C_PLAIN[2097152]:.2f} GB/s at 2 MiB. What inside the DSU raises the plain loop's rate is Insufficient data: per line, E's L1, L2 and prefetch refill counts are about C's [Jesse's boot E README, G7].")}
{fig(f_g8, f"In one assembly call the core reads {g8_asm_lo:.1f} to {g8_asm_hi:.1f} GB/s at 16 and 24 KiB, {100 * g8_asm_hi / READ_PATH:.0f} % of the {READ_PATH:.0f} GB/s read path, and the write rows fit {min(v['rate'] for (x, f, k), v in p.G8_FITS.items() if k == 'write'):.1f} to {max(v['rate'] for (x, f, k), v in p.G8_FITS.items() if k == 'write'):.1f} GB/s, the write path.", f"The G8 rows, best of 5 reps, GB = 1e9 bytes [bandwidth-l1-passes.csv (one call per pass) and bandwidth-l1-asmpasses.csv (every pass inside one assembly call) of 007 and 010, read by l1_reader.py]. L1 refills are at most {r4.G8_L1_MAX:.4f} per line on every row, so every row is an L1 row.")}
<ul>
<li><b>The L1 read shortfall is a per-pass cost, not the L1's rate.</b> Run 3's 16 KiB read of {ONE[16384]['read']:.1f} GB/s is {100 * ONE[16384]['read'] / READ_PATH:.0f} % of the path. Between the 8 and 16 KiB G8 rows the added bytes move at {min(p.G8_MARGINAL.values()):.1f} to {max(p.G8_MARGINAL.values()):.1f} GB/s on every form and boot, the path's rate. A straight line t_pass = a + bytes / rate fits the write rows (residuals {min(write_resid):.1f} to {max(write_resid):.1f} %, under the 2 % rule) with a fixed cost of {p.G8_FITS[('C', 'per-pass', 'write')]['a_ns']:.1f} to {p.G8_FITS[('E', 'per-pass', 'write')]['a_ns']:.1f} ns per pass in the looped form and {p.G8_FITS[('C', 'asm', 'write')]['a_ns']:.1f} to {p.G8_FITS[('E', 'asm', 'write')]['a_ns']:.1f} ns in the single-call form. The read fits fail the rule (residuals {min(read_resid):.1f} to {max(read_resid):.1f} %), so no single per-pass cost exists for reads [asimov-c1nano-run4.html, section 15]. The C1-Nano is an in-order core, and that is why the per-pass cost shows. Its TRM lists an "in-order pipeline with direct and indirect branch prediction" [Arm C1-Nano Core TRM r0p2, document 107753_0002_06_en, section 1.1 "C1-Nano core features"]. In an in-order core the work at a pass boundary (the loop exit, the return, the register save and restore, the next call) must finish before the first load of the next pass can issue. That time adds to every pass. An out-of-order core issues the next pass's loads while that work is still in flight. The CRB (the Arm reference server used as the comparison machine) has Neoverse V3AE cores, which are out of order. On the same program the V3AE adds {CRB_PASS_NS:.1f} ns per pass in the looped form, and its single-call form reads the same rate at every size [follow-up-run-plan.md, "CRB check of the two forms", from bandwidth-l1-read21-cpu3-passes.csv and -asmpasses.csv under ai-runs/run5c-crb-sample]. The out-of-order claim for the V3AE comes from Arm's public Neoverse V3 description, and no copy of that document is in the local vendor folder, so it is not cited by page.</li>
<li><b>Unexplained.</b> Boot E's 4 KiB per-pass read reads {G8R[('per-pass', 'read', 4096)]['agg']['E']:.2f} GB/s against boot C's {G8R[('per-pass', 'read', 4096)]['agg']['C']:.2f}. The five reps of that row spread {g8_4k_spread['E']:.1f} % on E and {g8_4k_spread['C']:.1f} % on C, so the gap is not rep noise. The other 15 G8 rows read {min(G8R[(f, k, s)]['agg']['E'] / G8R[(f, k, s)]['agg']['C'] for (f, k, s) in G8R if (f, k, s) != ('per-pass', 'read', 4096)):.3f} to {max(G8R[(f, k, s)]['agg']['E'] / G8R[(f, k, s)]['agg']['C'] for (f, k, s) in G8R if (f, k, s) != ('per-pass', 'read', 4096)):.3f} times C's. {gap(" These files do not show why.")}</li>
<li><b>The small write rows' per-pass cost is the program's.</b> On one boot (A) run 3's program takes {min(d['delta']['A'] for d in p.WRITE_SMALL):.1f} to {max(d['delta']['A'] for d in p.WRITE_SMALL):.1f} ns more per pass than run 2's at 16 to 256 KiB, against the {min(d['delta_orig'] for d in p.WRITE_SMALL):.1f} to {max(d['delta_orig'] for d in p.WRITE_SMALL):.1f} ns seen across the two runs [bandwidth-write-small.csv, bandwidth-write-small-r2prog.csv of 005]. On boot E, with the b79dffa build, the 16 KiB row no longer shows it ({p.WRITE_SMALL[0]['delta']['E']:+.1f} ns) while the 48 to 256 KiB rows do ({min(d['delta']['E'] for d in p.WRITE_SMALL[1:]):.1f} to {max(d['delta']['E'] for d in p.WRITE_SMALL[1:]):.1f} ns) [asimov-c1nano-run4.html, section 13.2].</li>
</ul>

<h3 id="l1calc">7.1 How the L1 read rows are read</h3>
<p>Each pass has two parts. One part is the bytes, read at the L1's rate. The other is a fixed time F that does not depend on the bytes. F is the work between the last load of one pass and the first load of the next. A row reports bytes over the whole pass time, F included. So F lowers every row. Subtracting two passes cancels F and leaves the L1's rate.</p>
{table(["Pass", "Measured time per pass (boot E, single-call form)", f"Time at the read path's {READ_PATH:.1f} GB/s", "Rate the row reports"],
                [[f"{kib(s)}", f"{E_ASM[s]['t_pass']:.1f} ns", f"{IDEAL(s):.0f} ns", f"{E_ASM[s]['agg']:.1f} GB/s"] for s in (4096, 8192, 16384, 24576)],
                "Time per pass = total bytes / (GB/s x 1e9) / passes from the best rep of each size [bandwidth-l1-asmpasses.csv of 010].")}
{fig(pass_fig(), f"The 16 KiB pass takes {E_ASM[16384]['t_pass'] - E_ASM[8192]['t_pass']:.1f} ns longer than the 8 KiB pass. That difference is the time of the added 8 KiB alone. 8,192 bytes in {E_ASM[16384]['t_pass'] - E_ASM[8192]['t_pass']:.1f} ns is {L1_RATE:.1f} GB/s (derived), {100 * L1_RATE / READ_PATH:.0f} % of the {READ_PATH:.0f} GB/s read path.", f"Boot E, every pass inside one call, best rep [bandwidth-l1-asmpasses.csv of 010]. F is derived. The 16 KiB pass time less 16,384 bytes at {L1_RATE:.1f} GB/s gives {PASS_F:.1f} ns est. Check: {16384 / L1_RATE:.1f} ns of reading plus {PASS_F:.1f} ns of F is {E_ASM[16384]['t_pass']:.1f} ns, and 16,384 bytes over that time is the row's {E_ASM[16384]['agg']:.1f} GB/s. The same subtraction gives {min(p.G8_MARGINAL.values()):.1f} to {max(p.G8_MARGINAL.values()):.1f} GB/s on both boots and both forms (derived). So every L1 read row is below {READ_PATH:.0f} GB/s by F. The L1 itself reads at the path's rate within {100 * (1 - min(p.G8_MARGINAL.values()) / READ_PATH):.0f} % (derived).")}
<ul>
<li><b>What F is.</b> In the looped form (one kernel call per pass) F holds the loop exit, the return, the restore and save of the vector registers d8 to d15 (the registers the Arm calling convention makes a called function preserve), the C loop's step and the next call. The write fits put it at {p.G8_FITS[('C', 'per-pass', 'write')]['a_ns']:.0f} to {p.G8_FITS[('E', 'per-pass', 'write')]['a_ns']:.0f} ns per pass. In the single-call form (every pass of a rep inside one assembly call) only the inner loop's exit, the pointer reset and the pass count remain. The write fits put that at {p.G8_FITS[('C', 'asm', 'write')]['a_ns']:.0f} to {p.G8_FITS[('E', 'asm', 'write')]['a_ns']:.0f} ns, and the read passes above at {PASS_F:.1f} ns est. The single-call form moves the program's work out of each pass. That is why its rows read higher.</li>
<li><b>Why F shows at all.</b> The C1-Nano is in order (section 7 above). The loads of the next pass cannot issue until the work at the boundary has run. On the out-of-order V3AE the same program keeps {CRB_PASS_NS:.1f} ns per pass in the looped form and none in the single-call form.</li>
</ul>
<h2 id="f-pf">8. Prefetching, in-flight reads and dependent loads</h2>
<p>Words used here: in flight means issued and not yet returned. A dependent load is one whose address comes from the load before it, so it cannot issue until that load returns. A pointer chase is a chain of dependent loads. The hardware prefetcher is the part of the core that notices an address pattern and issues reads for the next lines before any load asks for them.</p>
{fig(lanes_fig(), f"One DRAM read takes about {FLUSHED_E:.0f} ns. The sequential chain of boot E still takes only {SEQ_E:.2f} ns per load. The prefetcher keeps about {IN_FLIGHT:.0f} reads in flight (est.), so the DRAM time of one line overlaps the DRAM time of the next {IN_FLIGHT - 1:.0f}.", f"Durations to scale, the first 170 ns of each measurement [latency-dram-flushed.csv of 010 (flushed 8 MiB chain, {FLUSHED_E:.3f} ns), latency-dram-seq.csv of 006 and 010 ({SEQ_B:.3f} and {SEQ_E:.3f} ns), latency-dram-small.csv of 010 (4 KiB chain, {L1_CHASE:.3f} ns)]. The prefetcher lane is schematic. Each read is drawn {FLUSHED_E:.1f} ns long, the flushed random chain's time per load, and the count in flight is that time over the {SEQ_E:.2f} ns per load, both est. The last lane is computed from the read path's width (32 bytes per cycle at 2 GHz), not measured. The measured L1 rows are in section 7.1.")}
<ul>
<li><b>A dependent chain cannot be helped by anything that runs ahead.</b> The random chain's next address is inside the line being read. So one DRAM read must finish before the next can start, {FLUSHED_E:.1f} ns per load. The sequential chain's addresses are predictable. With the prefetchers off (boot B) nothing predicts them, and the chain takes the same {SEQ_B:.1f} ns per load.</li>
<li><b>With the prefetchers on the same DRAM reads overlap.</b> Boot E's sequential chain still reads every line from DRAM once (1.00 L2 refills per load, the lines flushed first). Its loads take {SEQ_E:.2f} ns each. The prefetcher issues reads ahead of the loads, about {IN_FLIGHT:.0f} at a time (est.). The lines arrive in L1 ({p.SEQ_ROW['l1pf']['E']:.2f} L1 prefetch refills per load) before or while the load waits for them. The time per load is close to the L1 chase's {L1_CHASE:.2f} ns. The stream runs at 64 bytes per {SEQ_E:.2f} ns, {SEQ_GBPS:.1f} GB/s (derived), about the plain one-core DRAM read of the same boot ({E_PLAIN[33554432]:.1f} GB/s at 32 MiB, measured). On boot C, the L3 off, the same chain takes {SEQ_C:.2f} ns per load and the plain read moves {C_PLAIN[33554432]:.1f} GB/s. By the same arithmetic boot C keeps about {SEQ_C / SEQ_E:.1f} times fewer reads in flight (est.). What the L3 changes in how far ahead the prefetcher runs is Insufficient data (section 7).</li>
<li><b>Two counters tell the prefetcher's fills from the loads' own.</b> Event 0x03 (L1D_CACHE_REFILL) counts every line that enters L1, whoever asked for it. Event 0x81BC (L1D_CACHE_REFILL_HWPRF) counts only the lines the hardware prefetcher asked for [Arm C1-Nano Core TRM r0p2, section 17.1 Common PMU Events]. The difference is the lines the loads fetched for themselves (demand refills, derived). The L2 has the same pair: 0x17 (L2D_CACHE_REFILL) and 0x0111 (IMP_L2D_CACHE_REFILL_L1DHWPRF, L2 refills for the L1 prefetcher's requests) [the same TRM, sections 17.1 and 17.2]. Per load, best pass:
{table(["Chain, boot", "ns per load", "L1 refills (0x03)", "of which prefetch (0x81BC)", "demand L1 refills (derived)", "L2 refills (0x17)", "of which for L1 prefetches (0x0111)", "L3 read refills (0xA2)"],
       [[f"sequential, prefetchers off (B)", f"{SEQ_B:.2f}"] + CNT("B", "SEQ"), [f"sequential, prefetchers on (E)", f"{SEQ_E:.2f}"] + CNT("E", "SEQ"), [f"random, flushed (E)", f"{FLUSHED_E:.2f}"] + CNT("E", "FLUSHED")],
       "Boot B [latency-dram-seq.csv of 006]. Boot E [latency-dram-seq.csv, latency-dram-flushed.csv of 010]. Event numbers from the counter columns of the files [gen_run4.py, the event table].")}
Every row refills L1 once per load. So the refill count alone cannot tell the three rows apart. The prefetch counter can. On the random chain and on boot B it reads 0 per load, so every refill was a load waiting for its own line. On boot E's sequential chain it reads {p.SEQ_ROW['l1pf']['E']:.4f} per load, so the loads fetched almost nothing themselves. The L3 column shows that the prefetched lines did not pass through the L3 ({r4.BT['E']['SEQ']['e']['l3d_refill_rd']:.4f} L3 read refills per load, against {r4.BT['E']['FLUSHED']['e']['l3d_refill_rd']:.4f} on the random chain). Where inside the DSU the L2 prefetch fills come from is Insufficient data.</li>
<li><b>Inside L1 the same rule holds.</b> The 4 KiB chain's loads are dependent. They take {L1_CHASE:.2f} ns each ({p.CONTROLS['E']['p4k_cyc']:.2f} cycles), the L1 load-to-use time. The read loop's loads are independent. The core can issue two 16-byte loads every cycle, so a 64-byte line leaves the L1 every {LINE_NS:.1f} ns, {READ_PATH:.0f} GB/s (computed from the path width). The chase moves {64 / L1_CHASE:.1f} GB/s from the same cache (derived from its time per load), {READ_PATH / (64 / L1_CHASE):.0f} times less. The chase measures latency and the loop measures bandwidth. The gap between them is how many loads are in flight.</li>
<li><b>The {SEQ_E - L1_CHASE:.2f} ns above the L1 time</b> is derived (the sequential chain's {SEQ_E:.3f} ns less the 4 KiB chain's {L1_CHASE:.3f} ns) and is not explained. In cycles it is {(SEQ_E - L1_CHASE) * CORE_GHZ:.2f}: the sequential chain takes {SEQ_E * CORE_GHZ:.2f} cycles per load against the L1 chain's {L1_CHASE * CORE_GHZ:.2f}, one cycle more. <span class="hyp">hypothesis</span> A whole cycle per load points at a cost inside the core, such as the prefetched line's write into L1 taking the cache for one cycle per line, rather than at a wait for a late line, which would not average to a whole cycle. A sequential chain with two members per line (32-byte stride) would test it: a per-line cost would halve per load, a per-load cost would not. The counters give refills, not hits, so they do not say whether a load waited for a line that had not yet arrived. A sequential-chain row under the L1 hit counters would show that part.</li>
</ul>
<h2 id="f-write">9. Multi-core DRAM writes and writer placement</h2>
{fig(f_write, f"Every multi-core write row repeats run 2 within {max(abs(d['pct']) for d in g.BW_SAME if 'write' in d['what'] and d['run3'] > 40):.2f} %, on the same firmware, both runs with the L3 off.", f"{RUN3_LABEL[0].upper() + RUN3_LABEL[1:]}. One DSU with two writers gives {g.PAIR_W:.1f} GB/s, four DSUs {max(d['run3'] for d in g.PERDSU if d['kernel'] == 'write'):.1f} GB/s and eight cores {max(d['run3'] for d in g.ALL8 if d['kernel'] == 'write'):.1f} GB/s [tables 4.4 and 4.5]. The firmware dependence of these rows was shown by run 2's control run (SCP 0.34.0 gave 87 to 89 GB/s for the multi-DSU rows). Whether the L3 changes them is open (section 12).")}

<h2 id="f-ocmbw">10. OCM bandwidth</h2>
{fig(f_ocmbw, f"One core reads an OCM region at {min(g.OCMBW['region']):.1f} to {max(g.OCMBW['region']):.1f} GB/s and writes all five at {g.OCMBW['write']:.1f} GB/s. Four cores on four regions read {g.OCMBW['four']:.1f} GB/s together.", f"{RUN3_LABEL[0].upper() + RUN3_LABEL[1:]}. The three-crosspoint regions (OCM3, OCM4) read lowest from CPU 2. All rows within {max(abs(d['pct']) for d in g.BW_SAME if 'ocm' in d['file']):.2f} % of run 2 [table 4.6].")}

<h2 id="f-cmn">11. Mesh counters</h2>
{fig(f_cmn, f"A sparse region row lands on one home node: OCM1's row from CPU 2 put {g.ATTR[(2, 1)]['own']:,} requests on node 160 and {g.ATTR[(2, 1)]['others_mean']:,.0f} on average on each other node (run 3).", f"Run 3, the L3 off. All 20 sparse rows pass this test (own node {ratio_lo:.1f} to {ratio_hi:.1f} times the others) [table 4.7]. The own-node counts are {min(g.own_ratio_vs_run2):.2f} to {max(g.own_ratio_vs_run2):.2f} times run 2's dense rows and the other nodes {min(g.oth_ratio_vs_run2):.2f} to {max(g.oth_ratio_vs_run2):.2f} times, so the sparse rows' counts are not comparable with run 2's under the same labels: a sparse row fills its 4,096 lines once but flushes them 7 times for 448 timed loads. The dense all-five controls repeat run 2's all-five counts node for node within {100 * min(g.dense_nodes_vs_run2):+.1f} % to {100 * max(g.dense_nodes_vs_run2):+.1f} %.")}
<p><b>Background and the counters' cost (run 3).</b> Each control row (a 4 KiB chase on 4 KiB pages) put {min(g.BG):,} to {max(g.BG):,} requests on each node, the run's background traffic. CPU 2's counted and uncounted control commands' helper times differ by {g.COST['counted'] - g.COST['uncounted']:,} ns (run 2: {g.COST['counted2'] - g.COST['uncounted2']:,} ns), which is the cost of the counter helper, mostly its own sysfs work. The counted command itself lived {g.COST['child_c'] - g.COST['child_u']:,} ns longer [cmn-counts.csv of 004 and 002].</p>
<p><b>Boot E's route counters.</b> Run 4 counted the mesh's crosspoint PMU instead of the home nodes: the data flits transmitted in each direction (e, w, n, s) at the DSU's crosspoint and at the home node's, over the whole command. On boot E the direction with the most flits is the X-first direction at both ends in {p.XFIRST['E'][0]} and {p.XFIRST['E'][1]} of 20 cells, as on boot A ({p.XFIRST['A'][0]} and {p.XFIRST['A'][1]}). The dominant direction's share is at least {100 * min(min(d['E']['share_dsu'], d['E']['share_node']) for d in p.ROUTES):.0f} % of the four on every cell. These events do not identify the read-request route or the response's last link, so the step counts of table 4.2 stay coordinate assumptions.</p>
{t10}

<h2 id="open">12. Open items</h2>
<ul>
<li>{open_(f" The memory model's configured delay behind the home node. The chases put it at about {p.DRAM_MODEL['rest_est']:.0f} ns est. (section 5). A configured value from the emulator's setup would replace the estimate. The question is with Jesse, unanswered [{mem_q}].")}</li>
<li>{open_(f" Why the L3 makes the one-core read loop faster. With the L3 on the plain loop reads {E_PLAIN[33554432]:.1f} GB/s at 32 MiB against {C_PLAIN[33554432]:.1f} on boot C, the same build (section 7). The refill counters per line are the same on both boots (L1 {RV[('read', 33554432)]['e']['E']['l1d_refill']:.2f} and {RV[('read', 33554432)]['e']['C']['l1d_refill']:.2f}, L2 {RV[('read', 33554432)]['e']['E']['l2d_refill']:.2f} and {RV[('read', 33554432)]['e']['C']['l2d_refill']:.2f}, L1 prefetch {RV[('read', 33554432)]['e']['E']['l1d_refill_hwprf']:.2f} and {RV[('read', 33554432)]['e']['C']['l1d_refill_hwprf']:.2f}), and every line is still fetched into the L2 from a 32 MiB buffer that no cache holds. The L3 is not refilled on the way ({RV[('read', 33554432)]['e']['E']['l3d_refill_rd']:.2f} L3 read refills per line, as on the sequential chain of section 8). So the L3 does not serve the lines. The only counted change is the cycles per line, {RV[('read', 33554432)]['e']['C']['cycles']:.1f} on C to {RV[('read', 33554432)]['e']['E']['cycles']:.1f} on E, so the fills run further ahead or return sooner with the L3 on. Which part of the DSU does that is Insufficient data. A read row with the L3 hit-set counters, or the DSU's L3 and prefetcher events per line on both boots, would resolve it. The program rejects the read-plus-hit-set combination today [bandwidth-read-prefetch.csv of 007 and 010].")}</li>
<li>{open_(f" The bandwidth set has not run with the L3 on: the one-core sweep (table 4.3), multi-core DRAM (4.4), writer placement (4.5), OCM bandwidth (4.6) and every CME bandwidth row are run 3's, measured with the L3 holding no data. Running run 3's bandwidth commands on an L3-on boot would update them.")}</li>
<li>{open_(f" Boot E's 4 KiB per-pass L1 read reads {G8R[('per-pass', 'read', 4096)]['agg']['E']:.1f} GB/s against boot C's {G8R[('per-pass', 'read', 4096)]['agg']['C']:.1f}, with the other 15 G8 rows within 3 %. Insufficient data: the G8 rows with the perf columns on a second L3-on boot would show whether the row repeats [bandwidth-l1-passes.csv of 010 and 007].")}</li>
<li>{open_(f" The walk rate on the 32 MiB stimulus differs {walk_d['walk_row'] / walk_d['tlb_set']:.0f} times between two processes of one boot (D: {walk_d['tlb_set']:.3f} against {walk_d['walk_row']:.3f} walks per load). Insufficient data: the same chain in several walk-counted processes of one boot would show whether the rate is the process's placement [latency-dram-tlb-cpu2.csv, latency-dram-walk-cpu2.csv of 008].")}</li>
<li>{open_(f" The G8 read fits fail the 2 % residual rule (residuals {min(read_resid):.1f} to {max(read_resid):.1f} %), so no single per-pass cost exists for reads. More sizes between 4 and 24 KiB, or the perf columns per pass, would show the shape of the cost [bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv of 007 and 010].")}</li>
<li>{open_(f" The single-call form still keeps a per-pass cost: {p.G8_FITS[('C', 'asm', 'write')]['a_ns']:.0f} to {p.G8_FITS[('E', 'asm', 'write')]['a_ns']:.0f} ns on the write fits and {PASS_F:.1f} ns est. on the read passes (section 7.1). Only the inner loop's exit, the pointer reset and the pass count run between its passes. Whether that remainder is the core's or the program's is Insufficient data. A form with the passes written out one after another with no loop, or a per-pass cycle count from the PMU, would separate them. The CRB's V3AE (at {CRB_GHZ:.1f} GHz) keeps {CRB_PASS_NS:.1f} ns per pass in the looped form and none in the single-call form, on its read rows. The C1-Nano's call-per-pass read passes keep {PASS_F_PP:.1f} ns est., {PASS_F_PP / CRB_PASS_NS:.0f} times more (est.), against a clock ratio of {CRB_GHZ / CORE_GHZ:.1f}. Why is also Insufficient data [bandwidth-l1-passes.csv and bandwidth-l1-asmpasses.csv of 007 and 010, follow-up-run-plan.md, CRB check].")}</li>
<li>{hyp(f" The {p.EC_DELTA[33554432]:.1f} ns at 32 MiB and {p.EC_DELTA[16777216]:.1f} ns at 16 MiB that boot E reads above boot C are translation walks. A walk-counted 32 MiB row on E and C in one process would test it [latency-dram-large.csv of 010 and 007; section 5].")}</li>
<li>{open_(f" The L3 state of the clusters of CPUs 4 to 9 on boot E was not read: the register reading and the hit counter cover CPU 2's cluster only, and the other clusters rest on the SCP's staging lines [Jesse's boot E README, Coverage]. A hit-set row from CPU 4, 6 and 8 on an L3-on boot would settle it.")}</li>
<li>{open_(f" The CPU 4 and 6 OCM, SLC and control rows have not run since run 3 (table 4.2's run 3 columns). Running them on an L3-on boot would update them. Run 4 has their route rows only.")}</li>
<li>{open_(f" The multi-core rows with the L3 on: whether eight writers still reach {max(d['run3'] for d in g.ALL8 if d['kernel'] == 'write'):.0f} GB/s and how the four-DSU readers change from {_r4['run3']:.1f} GB/s is Insufficient data (not run) [bandwidth-perdsu.csv, bandwidth-all8.csv of 004].")}</li>
<li>{open_(" The scratchpad memory (SPM) phase is still postponed (no /dev/asimov-spm on this image).")}</li>
</ul>

<h2 id="sources">13. Sources</h2>
<ul>
{"".join(f"<li><a href='{path}'>{path}</a>: {what}</li>" for path, what in p.SOURCES)}
<li>Jesse's README files of membench-jibin-010 (boot E), 007 (boot C), 005 (boot A), 006 (boot B), 008 (boot D) and 004 (run 3): platform facts, chip time, firmware, the SCP rebuild, the L3 power reading and its coverage, the DRAM caveat.</li>
<li><a href="{mem_q}">{mem_q}</a>: the open question on the memory model's delay.</li>
<li>The companion page <a href="asimov-cme-perf.html">asimov-cme-perf.html</a>: the same loads and stores through the CME.</li>
</ul>
"""
    toc = [("words", "1. Words used here"), ("run", "2. The run and the platform", [("changes", "2.1 What changed from run 3 to run 4 boot E")]), ("map", "3. The hemisphere map"),
           ("tables", "4. Summary tables", [("t41", "4.1 Latency by level"), ("t42", "4.2 OCM latency by region"), ("t43", "4.3 One-core bandwidth by footprint"), ("t44", "4.4 Multi-core DRAM bandwidth"),
                                             ("t45", "4.5 Writer placement"), ("t46", "4.6 OCM bandwidth"), ("t461", "4.6.1 One core, read and write by level"), ("t47", "4.7 Home-node attribution"), ("t48", "4.8 Rows that moved 1 % or more")]),
           ("f-levels", "5. Latency by level, CPU 2"), ("f-ocm", "6. OCM latency by region: boot E against the L3-off boots"),
           ("f-bw1", "7. One-core bandwidth by level", [("l1calc", "7.1 How the L1 read rows are read")]), ("f-pf", "8. Prefetching, in-flight reads and dependent loads"), ("f-write", "9. Multi-core DRAM writes and writer placement"), ("f-ocmbw", "10. OCM bandwidth"), ("f-cmn", "11. Mesh counters"), ("open", "12. Open items"), ("sources", "13. Sources")]
    return page("Asimov C1-Nano Memory Performance", p.META + " Generated by gen_perf_core.py through gen_perf.py.", toc, body)

if __name__ == "__main__":
    open(p.OUT["core"], "w").write(core_page())
    print("wrote", p.OUT["core"])
