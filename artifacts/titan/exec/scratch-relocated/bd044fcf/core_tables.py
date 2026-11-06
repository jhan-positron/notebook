    t12 = table(["Row"] + [f"Boot {x}" for x in BOOT_ORDER], [[lab] + [d[x] for x in BOOT_ORDER] for lab, d in FIVE],
                "Each row is the same command on every boot that has it [log.txt, latency-dram-small.csv, latency-dram-small-l3.csv, latency-dram-large.csv, latency-dram-seq.csv, bandwidth-read-prefetch.csv of 005 to 010]. The power status is the box's two reads around the hit-set command.")
    t13a = table(["Chain (CPU 2, TLB set)", "Hops per pass"] + [f"Boot {x}" for x in BOOT_ORDER],
                 [[f"OCM{r}, {s}", f"{BT['A']['TLB'][r][s]['hops']:,}"] + [f"{TLB_PASS[x][(r, s)][0]:.0f} to {TLB_PASS[x][(r, s)][1]:.0f}" for x in BOOT_ORDER] for s in SHAPES for r in range(5)],
                 "L1 data TLB refills (0x05) per pass, lowest to highest pass of the row [latency-ocm-region&lt;r&gt;-&lt;shape&gt;-tlb-cpu2.csv of 005 to 010]. Boots C and D map the OCM in 64 KiB contiguous translations; A, B and E in 4 KiB pages.")
    t13b = table(["Pair", "What the pair compares", "Rows", "Faster on the first", "Ratio, lowest to highest", "Geometric mean"],
                 [[f"{a} / {b}", what, RATIOS[(a, b)]["n"], RATIOS[(a, b)]["faster"], f"{RATIOS[(a, b)]['lo']:.3f} to {RATIOS[(a, b)]['hi']:.3f}", f"{RATIOS[(a, b)]['gm']:.3f}"] for a, b, what in PAIRS],
                 "The 69 core OCM rows of each boot (30 shape cells on CPUs 2 and 8, 4 all-five rows, 15 TLB-set rows, 20 route rows), ratio of best passes; below 1 is faster on the first boot. The walk rows are not among them.")
    t13c = table(["Walk event, row"] + [f"Boot {x}" for x in "CDE"],
                 [["32 MiB stimulus: 0x34 walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: 0x818A page walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk_page']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: 0x8188 block walks per hop"] + [f"{WALK_STIM[x]['emean']['dtlb_walk_block']:.4f}" for x in "CDE"],
                  ["32 MiB stimulus: ns per hop, best"] + [f"{WALK_STIM[x]['best']:.2f}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x34 per hop, lowest to highest pass"] + [f"{WALK_OCM_34[x][0]:.4f} to {WALK_OCM_34[x][1]:.4f}" for x in "CDE"],
                  ["5 OCM sparse rows: passes with a walk, of 35"] + [f"{WALK_OCM_NONZERO[x]}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x818A per hop, highest pass"] + [f"{WALK_OCM_PAGE_MAX[x]:.4f}" for x in "CDE"],
                  ["5 OCM sparse rows: 0x8188 per hop, highest pass"] + [f"{WALK_OCM_BLOCK_MAX[x]:.4f}" for x in "CDE"]],
                 "The walk rows: the TLB-set chains run again with 0x34, 0x8188 and 0x818A [latency-dram-walk-cpu2.csv, latency-ocm-region&lt;r&gt;-walk-cpu2.csv of 007, 008 and 010]. The stimulus is the random 32 MiB chain on 4 KiB DRAM pages (2 passes); each OCM row is the sparse chain of one region (7 passes of 64 hops).")
    t14a = table(["Footprint", "Boot C ns", "Boot E ns", "E / C", "E: L2 hits", "E: L3 hits", "E: outside refills", "C: L2 hits", "C: L3 hits", "C: outside refills"],
                 [[kib(s), fmt(C_L3["best"][s]["ns"], 3), fmt(E_L3["best"][s]["ns"], 3), f"{E_L3['best'][s]['ns'] / C_L3['best'][s]['ns']:.3f}",
                   fmt(E_L3["best"][s]["e"]["l2d_hit_rd"], 4), fmt(E_L3["best"][s]["e"]["l3d_hit_rd"], 4), fmt(E_L3["best"][s]["e"]["l3d_refill_rd"], 4),
                   fmt(C_L3["best"][s]["e"]["l2d_hit_rd"], 4), fmt(C_L3["best"][s]["e"]["l3d_hit_rd"], 4), fmt(C_L3["best"][s]["e"]["l3d_refill_rd"], 4)] for s in L3_SIZES],
                 "The hit set, CPU 2 with CPU 3 offline, best of 3 reps, counts per load of that rep [latency-dram-small-l3.csv of 007 and 010]: 0x81C5 L2 read hits, 0x81C6 L3 read hits, 0xA2 L3 read refills (filled from outside the cluster).")
    t14b = table(["Footprint", "Chase", "Boot C ns", "Boot E ns", "E / C"], [[kib(s), k, fmt(c, 3), fmt(e, 3), f"{e / c:.3f}"] for s, k, c, e in EC_LV],
                 "CPU 2, best rep or best pass [latency-dram-small.csv, -large.csv, -flushed.csv, -seq.csv of 007 and 010].")
    t14c = table(["Read variant", "Footprint"] + [f"Boot {x}, GB/s" for x in RP_BOOTS] + ["E / C"],
                 [[name, kib(s)] + [fmt(EX[x]["rp"][(k, s)]["agg"], 3) for x in RP_BOOTS] + [f"{EX['E']['rp'][(k, s)]['agg'] / EX['C']['rp'][(k, s)]['agg']:.3f}"] for s in RP_SIZES for k, name in RP_KERNELS],
                 "One thread on CPU 2, best of 3 reps, GB = 1e9 bytes [bandwidth-read-prefetch.csv of 006 to 010]. Prefetchers off on B and D, on with the L3 in snoop-filter-only mode on C, on with the L3 on on E.")
    t15 = table(["Boot, form, kernel"] + [f"{kib(s)}, GB/s" for s in G8_SIZES] + ["Fixed cost per pass, ns", "Rate, GB/s", "Largest residual", "Rule (under 2 %)"],
                [[f"{x}, {f}, {k}"] + [fmt(v["rows"][s]["agg"], 3) for s in G8_SIZES] + [fmt(v["a_ns"], 1), fmt(v["rate"], 1), f"{v['resid_pct']:.1f} %", "met" if v["ok"] else "not met"] for x in G8 for (f, k), v in G8[x].items()],
                "Best of 5 reps per size; the fit t_pass = a + bytes / rate through the four best reps [bandwidth-l1-passes.csv, bandwidth-l1-asmpasses.csv of 007 and 010; l1_reader.py]. per-pass = one call of the kernel per pass; asm = all passes inside one assembly call.")
    t15b = table(["Boot, form (read)"] + [f"{kib(s)}: ns per pass above 64 GB/s" for s in G8_SIZES] + ["8 to 16 KiB: added bytes, GB/s"],
                 [[f"{x}, {f}"] + [fmt(G8[x][(f, 'read')]["rows"][s]["above_ideal"], 1) for s in G8_SIZES] + [fmt(G8_MARGINAL[(x, f)], 1)] for x in G8 for f in ("per-pass", "asm")],
                 "The read rows without a fit: each best rep's pass time minus bytes / 64 GB/s (the dual 128-bit read path at 2 GHz), and the rate of the bytes added between the 8 and 16 KiB rows.")
