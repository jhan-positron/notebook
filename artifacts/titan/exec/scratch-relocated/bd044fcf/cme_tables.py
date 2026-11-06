    tc3 = table(["Footprint", "Boot C ns", "Boot E ns", "E / C", "C: inner", "C: outer", "E: inner", "E: outer"],
                [[kib(s), fmt(c["ns"], 3), fmt(d["ns"], 3), f"{d['ns'] / c['ns']:.3f}", fmt(c["emean"]["cme_l1d_refill_inner"], 2), fmt(c["emean"]["cme_l1d_refill_outer"], 2), fmt(d["emean"]["cme_l1d_refill_inner"], 2), fmt(d["emean"]["cme_l1d_refill_outer"], 2)] for s, c, d in EC_CLV],
                "CPU 2 in streaming mode, best of 3 reps, CME L1 refills per load as the mean over the reps: inner 0x327D, outer 0x327E [cme-latency-dram-small.csv of 007 and 010].")
    tc4 = table(["Row through the CME"] + [f"Boot {x} ns" for x in BOOT_ORDER],
                [[f"OCM{r}, {s}"] + [fmt(BT[x]["COCM"][r][s]["best"], 2) for x in BOOT_ORDER] for s in SHAPES for r in range(5)]
                + [[f"all five, {s}"] + [fmt(BT[x]["CALL5"][s]["best"], 2) for x in BOOT_ORDER] for s in ("dense", "sparse")],
                "Best pass [cme-latency-ocm-*.csv of 005 to 010]. Dense: 4,096 hops a pass; sparse and vary: 64 hops; all five: the five regions as one chain.")
