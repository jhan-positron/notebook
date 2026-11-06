# boots C, D and E figures
BOOT_COL = dict(A=C["muted"], B=C["s2"], C=C["s3"], D=C["s4"], E=C["s1"])
BOOT_NAME = dict(A="boot A (prefetchers on, 4 KiB pages)", B="boot B (prefetchers off)", C="boot C (hint, prefetchers on)", D="boot D (hint, prefetchers off)", E="boot E (L3 on, prefetchers on)")
f_cd_tlb = dotplot([dict(label=f"OCM{r}, {s}", vals=[statistics.mean(TLB_PASS[x][(r, s)]) for x in "ABCD"]) for s in SHAPES for r in range(5)],
                   [BOOT_NAME[x] for x in "ABCD"], [BOOT_COL[x] for x in "ABCD"], unit="L1 TLB refills per pass", xlim=(0, 620))
f_cd_gap = dotplot([dict(label=f"OCM{r} ({dist(2, NODE_OF_REGION[r])} xp)", vals=[GAP[x][r] for x in "ABCD"]) for r in range(5)],
                   [BOOT_NAME[x] for x in "ABCD"], [BOOT_COL[x] for x in "ABCD"], unit="ns (sparse minus dense)", xlim=(0, 5.5))
_hit_rows = []
for s in (196608, 262144, 393216, 524288):
    for x in "CE":
        e = EX[x]["l3"]["best"][s]["e"]
        _hit_rows.append(dict(label=f"boot {x}, {kib(s)} ({EX[x]['l3']['best'][s]['ns']:.1f} ns)", parts=[(e["l2d_hit_rd"], C["s1"], "L2 read hits (0x81C5)"), (e["l3d_hit_rd"], C["s3"], "L3 read hits (0x81C6)"), (e["l3d_refill_rd"], C["s2"], "L3 read refills from outside the cluster (0xA2)")]))
f_e_hits = stacked_h(_hit_rows, L=260, xlim=1.15)
f_e_levels = line_chart([dict(name="boot C: L3 in snoop-filter-only mode (prefetchers on)", color=C["s3"], pts=[(s, c, f"boot C {kib(s)} {k}: {c:.3f} ns") for s, k, c, e in EC_LV if k in ("repeat", "fresh")], short="boot C", dy=14),
                         dict(name="boot E: L3 on (prefetchers on)", color=C["s1"], pts=[(s, e, f"boot E {kib(s)} {k}: {e:.3f} ns") for s, k, c, e in EC_LV if k in ("repeat", "fresh")], short="boot E", dy=-8)],
                        marks=[(131072, "128 KiB: the L2"), (262144, "256 KiB: the L3"), (4194304, "4 MiB: past the SLC")])
f_e_read = dotplot([dict(label=f"{name}, {kib(s)}", vals=[EX[x]["rp"][(k, s)]["agg"] for x in RP_BOOTS]) for s in RP_SIZES for k, name in RP_KERNELS],
                   [BOOT_NAME[x] for x in RP_BOOTS], [BOOT_COL[x] for x in RP_BOOTS], unit="GB/s", xlim=(0, 27))
_g8_names = [f"boot {x}, {f}" for x in G8 for f in ("per-pass", "asm")]; _g8_cols = [C["s3"], C["s7"], C["s1"], C["s2"]]
f_g8 = dotplot([dict(label=f"{kernel}, {kib(s)}", vals=[G8[x][(f, kernel)]["rows"][s]["agg"] for x in G8 for f in ("per-pass", "asm")]) for kernel in ("read", "write") for s in G8_SIZES],
               _g8_names, _g8_cols[:len(_g8_names)], unit="GB/s", xlim=(20, 66))
f_e_cme = line_chart([dict(name="boot C: L3 in snoop-filter-only mode", color=C["s3"], pts=[(d["size"], c["ns"], f"boot C {kib(d['size'])}: {c['ns']:.3f} ns") for d in BT["E"]["CLV"] for c in BT["C"]["CLV"] if c["size"] == d["size"] and c["kind"] == d["kind"] and d["kind"] in ("repeat", "fresh")], short="boot C", dy=14),
                      dict(name="boot E: L3 on", color=C["s1"], pts=[(d["size"], d["ns"], f"boot E {kib(d['size'])}: {d['ns']:.3f} ns") for d in BT["E"]["CLV"] if d["kind"] in ("repeat", "fresh")], short="boot E", dy=-8)],
                     marks=[(65536, "64 KiB: the CME L1"), (262144, "256 KiB: the L3"), (4194304, "4 MiB: past the SLC")], hline=(RT_NS[0], "register control 21.0 ns"))
_cme_io = []
for s in (8192, 16384, 32768, 65536, 131072):
    for x in "CE":
        d = next(d for d in BT[x]["CLV"] if d["kind"] == "repeat" and d["size"] == s)
        _cme_io.append(dict(label=f"boot {x}, {kib(s)} ({d['ns']:.1f} ns)", parts=[(d["emean"]["cme_l1d_refill_inner"], C["s3"], "refills from inside the cluster (0x327D)"), (d["emean"]["cme_l1d_refill_outer"], C["s2"], "refills from outside the cluster (0x327E)")]))
f_e_cme_io = stacked_h(_cme_io, L=240)
f_e_cocm = dotplot([dict(label=f"CPU 2 to OCM{r} through the CME ({dist(2, NODE_OF_REGION[r])} xp)", vals=[BT[x]["COCM"][r]["sparse"]["best"] for x in BOOT_ORDER]) for r in range(5)]
                   + [dict(label="all five, sparse", vals=[BT[x]["CALL5"]["sparse"]["best"] for x in BOOT_ORDER])],
                   [BOOT_NAME[x] for x in BOOT_ORDER], [BOOT_COL[x] for x in BOOT_ORDER], L=300)
E_COCM_OUTER = {s: [BT["E"]["COCM"][r][s]["emean"]["cme_l1d_refill_outer"] for r in range(5)] for s in SHAPES}
C_COCM_OUTER = {s: [BT["C"]["COCM"][r][s]["emean"]["cme_l1d_refill_outer"] for r in range(5)] for s in SHAPES}
COCM_RATIO = {(a, b): {s: [BT[a]["COCM"][r][s]["best"] / BT[b]["COCM"][r][s]["best"] for r in range(5)] for s in SHAPES} for a, b in (("D", "B"), ("C", "A"), ("E", "A"), ("E", "C"))}

