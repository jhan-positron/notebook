def sec_f1_vs_run3():
    """2.3: boot F1 against run 3. The setup facts are Jesse's F1 README's (Core rows against round three);
    every ratio is computed here from both folders' CSV files."""
    R3 = {(d["size"], d["kind"]): d for d in g.LV4}; R1 = {(d["size"], d["kind"]): d for d in K1["LV"]}
    sizes = lambda kind, lo, hi: [(sz, kind) for sz in sorted({k[0] for k in R1 if k[1] == kind}) if lo <= sz <= hi]
    lat = lambda keys: [R3[k]["ns"] / R1[k]["ns"] for k in keys]                        # above 1 = faster on F1
    ONE3 = {d["size"]: d for d in g.ONE}; big = sorted(sz for sz in ONE1 if sz > 16384)
    m3 = lambda k, sz, n: next(d for d in g.PAIR + g.PERDSU + g.ALL8 if d["kernel"] == k and d["size"] == sz and d["threads"] == n)["run3"]
    multi = lambda k, szs, n: [M1[(k, sz, n)]["agg"] / m3(k, sz, n) for sz in szs]
    KK = ("read", "write", "copy")
    groups = [
        ("Chains 4 to 128 KiB (L1, L2)", lat(sizes("repeat", 0, 131072))),
        ("Chains 192 to 384 KiB (the L3's sizes)", lat(sizes("repeat", 196608, 393216))),
        ("Fresh chains 512 KiB to 1 MiB", lat(sizes("fresh", 524288, 1048576))),
        ("Fresh chains 1.5 to 4 MiB (the SLC)", lat(sizes("fresh", 1572864, 4194304))),
        ("Fresh chains 6 to 32 MiB (DRAM)", lat(sizes("fresh", 6291456, 33554432))),
        ("Flushed 8 MiB chain", lat([(8388608, "flushed")])),
        ("4 KiB controls, CPUs 2, 4, 6, 8", [g.CTRL[c]["best"] / K1["CTRL"][c]["best"] for c in (2, 4, 6, 8)]),
        ("OCM, one line per page, per region, CPUs 2 to 8 (20 rows)", [g.OCM[c][r]["best"] / K1["OCM"][c][r]["best"] for c in K1["OCM"] for r in K1["OCM"][c]]),
        ("OCM, one line per page, all five regions, CPUs 2 to 8", [g.ALL5S[c]["best"] / K1["ALL5S"][c]["best"] for c in K1["ALL5S"]]),
        ("OCM, every line, all five regions, CPUs 2 to 8", [g.ALL5D[c]["best"] / K1["ALL5D"][c]["best"] for c in K1["ALL5D"]]),
        ("2 MiB SLC chains, CPUs 4, 6, 8", [g.SLC[c]["best"] / K1["SLC"][c]["best"] for c in (4, 6, 8)]),
        ("One core, 16 KiB: read, write, copy", [ONE1[16384][k] / ONE3[16384][k] for k in KK]),
        ("One core read, 48 KiB to 32 MiB", [ONE1[sz]["read"] / ONE3[sz]["read"] for sz in big]),
        ("One core write, 48 KiB to 32 MiB", [ONE1[sz]["write"] / ONE3[sz]["write"] for sz in big]),
        ("One core copy, 48 KiB to 32 MiB", [ONE1[sz]["copy"] / ONE3[sz]["copy"] for sz in big]),
        ("OCM read, one core, per region and all five", [OCMBW1["region"][r] / g.OCMBW["region"][r] for r in range(5)] + [OCMBW1["all5"] / g.OCMBW["all5"]]),
        ("OCM read, four cores", [OCMBW1["four"] / g.OCMBW["four"]]),
        ("OCM write, one core", [OCMBW1["write"] / g.OCMBW["write"]]),
        ("Pair (CPUs 2, 3), 16 KiB: read, write, copy", [M1[(k, 16384, 2)]["agg"] / m3(k, 16384, 2) for k in KK]),
        ("Pair, 48 and 160 KiB: read", multi("read", (49152, 163840), 2)),
        ("Pair, 48 and 160 KiB: write", multi("write", (49152, 163840), 2)),
        ("Pair, 48 and 160 KiB: copy", multi("copy", (49152, 163840), 2)),
        ("One core per cluster, 2 and 16 MiB: read", multi("read", (2097152, 16777216), 4)),
        ("One core per cluster, 2 and 16 MiB: write", multi("write", (2097152, 16777216), 4)),
        ("One core per cluster, 2 and 16 MiB: copy", multi("copy", (2097152, 16777216), 4)),
        ("All eight cores, 2 and 16 MiB: read", multi("read", (2097152, 16777216), 8)),
        ("All eight cores, 2 and 16 MiB: write", multi("write", (2097152, 16777216), 8)),
        ("All eight cores, 2 and 16 MiB: copy", multi("copy", (2097152, 16777216), 8)),
        ("Writer placement, six rows", [PLACE1[q]["agg"] / next(d["run3"] for d in g.PLACE if d["cpus"] == q) for q in PLACE1]),
    ]
    n_rows = sum(len(v) for _, v in groups)
    f_ratio = dotplot([dict(label=f"{name}" + ("" if "rows)" in name else f" ({len(v)})"), vals=[min(v), max(v)]) for name, v in groups],
                      ["lowest row of the group", "highest row of the group"], [g.C["muted"], g.C["s1"]], unit="ratio", xlim=(0.5, 3.0), rh=19, L=400)
    t_ratio = table(["Row group", "Rows", "Speed ratio, F1 over run 3", "Reading"],
                    [[name, len(v), f"{min(v):.2f}" if len(v) == 1 else f"{min(v):.2f} to {max(v):.2f}",
                      "unchanged" if max(abs(x - 1) for x in v) < 0.05 else "faster on F1" if min(v) > 1 else "slower on F1" if max(v) < 1 else "mixed"] for name, v in groups],
                    note=f"{n_rows} rows. Latency rows: run 3's best ns per load over F1's. Bandwidth rows: F1's best aggregate GB/s over run 3's. So above 1 is faster on F1 in every row. 'Unchanged' means every row of the group within 5 % [the CSV files of 011 and 004].")
    # the counter evidence
    l3s = (196608, 262144, 393216)
    l2_3 = [R3[(sz, "repeat")]["l2"] for sz in l3s]; l2_1 = [R1[(sz, "repeat")]["l2"] for sz in l3s]
    a2_3 = [R3[(sz, "repeat")]["l3"] for sz in l3s]; a2_1 = [R1[(sz, "repeat")]["l3"] for sz in l3s]
    sp_a2_3 = [q["l3"] for c in g.OCM for r in g.OCM[c] for q in g.OCM[c][r]["passes"]]; sp_a2_1 = [q["l3"] for c in K1["OCM"] for r in K1["OCM"][c] for q in K1["OCM"][c][r]["passes"]]
    sp_l2_3 = [q["l2"] for c in g.OCM for r in g.OCM[c] for q in g.OCM[c][r]["passes"]]; sp_l2_1 = [q["l2"] for c in K1["OCM"] for r in K1["OCM"][c] for q in K1["OCM"][c][r]["passes"]]
    c1, c3 = K1["CMN"]["dram-read-2M-cpu2"], g.CMN4["dram-read-2M-cpu2"]
    req_ratio = sum(c1["node"].values()) / sum(c3["node"].values()); life_ratio = c1["child"] / c3["child"]
    ctl_life = [K1["CMN"][f"control-cpu{c}"]["child"] / g.CMN4[f"control-cpu{c}"]["child"] for c in (2, 4, 6, 8)]
    e32, c32 = RV[("read", 33554432)]["e"]["E"], RV[("read", 33554432)]["e"]["C"]
    rd4 = M1[("read", 16777216, 4)]; rd8 = M1[("read", 16777216, 8)]
    per4 = (rd4["tmin"] / ONE1[33554432]["read"], rd4["tmax"] / ONE1[33554432]["read"])
    e_over_c = {sz: E_PLAIN[sz] / C_PLAIN[sz] for sz in (2097152, 33554432)}
    bd32 = (RV[("read", 33554432)]["agg"]["B"], RV[("read", 33554432)]["agg"]["D"])
    ratio = lambda name: next(v for n, v in groups if n == name)
    rd1 = ratio("One core read, 48 KiB to 32 MiB"); wr1 = ratio("One core write, 48 KiB to 32 MiB"); ch = ratio("Fresh chains 1.5 to 4 MiB (the SLC)") + ratio("Fresh chains 6 to 32 MiB (DRAM)")
    return f"""
<h3 id="f1vs3">2.3 Boot F1 against run 3: what differed, what moved, and the hypotheses</h3>
<p><b>Short version.</b> Boot F1 ran run 3's 67 core command lines in run 3's order, on boot E's firmware, where the one platform change that matters is the L3 of CPUs 2 to 9 in full mode. Every stream of independent reads got faster (1.2 to 2.9 times), while the dependent chains beyond the L3 (within 4 %), the one-core writes, the writer-placement rows and the controls (within 0.3 %) repeated run 3. The counters show the same number of refills per line and the same number of mesh requests per command, so the reads overlap more of their time rather than skipping the mesh, and the mechanism is a hypothesis with a test, not a measurement.</p>
<ul>
<li><b>What differed in the setup.</b> The table lists every difference between the two boots that Jesse's README names, and what was the same [Jesse's F1 README, Core rows against round three; Jesse's run 3 README, Platform facts].</li>
</ul>
{table(["Item", "Run 3 (membench-jibin-004)", "Boot F1 (membench-jibin-011)", "Can it move a core row?"], [
    ["Date, emulator boards", "2026-11-03, ga13pd02 boards 6 to 9", "2026-11-06, boards 18 to 21", "Same private image copy (membench-img-001); run-to-run noise only (section 4.8, boot A against run 3)"],
    ["SCP firmware (stages each cluster's L3 mode before its cores power on)", "0.48.0-nopcie.1: full L3 for cluster 0 only; the L3 of CPUs 2 to 9 snoop-filter-only, no lookup, no allocation", "0.48.0-nopcie-l3.1: full L3 for clusters 1 to 4 too; IMP_CLUSTERPWRSTAT_EL1 read 0x70 on CPU 2's cluster (not read on run 3)", "Yes: the one platform change. The register reading covers CPU 2's cluster only; clusters of CPUs 4 to 9 rest on the SCP's staging lines"],
    ["TF-A, kernel, OS image, device tree, huge pages, CPU layout", "TF-A 0.35.0, Linux 6.18.36, 256 huge pages of 2 MiB, CPUs 2 to 9 isolated, data prefetchers on", "the same files byte for byte (kernel Image sha256 equal)", "No"],
    ["cache-mem-perf commit and build", "ba834c0", "0c190a1 (five commits on b79dffa). chase: the same 34 instructions; k_read, k_write, k_copy byte for byte the same; pass and worker differ (new --asm-passes, --perf and CME paths). chase's 48 B loop sits inside one 64 B line on F1, across two on run 3", "The kernels are the same code. The pass and worker changes could move an L1-sized row by a few percent (the 16 KiB rows below). Boot E against boot C, one build, shows the read rise on its own"],
    ["Command lines", "run_asimov.sh and run_all.sh", "the same files byte for byte (sha256 equal): phases A, B, D and E are run 3's 67 command lines in the same order", "No"],
    ["Counter columns on the core latency rows", "cycles and L1, L2, L3 refills", "three more events (0x81BC, 0x81BD, 0x0111: the prefetch set, opened by default since the run 3 follow-up); the PMU has 21 counters, so nothing is multiplexed", "No (perf_cov 1.0000 on every row)"],
    ["/dev/ocm module", "an earlier build, no map lines, no clusterpwrstat file", "asimov-os 89cfd32's build: the same 4 KiB mapping, plus debug map lines and the clusterpwrstat file", "OCM rows only, through page placement"],
    ["Physical page placement", "unknown (no map lines)", "printed for each OCM process", "Each command is its own process on both boots, so its buffers need not sit on the same physical pages. The sparse OCM rows spread up to 60 % between passes inside one boot"],
    ["What ran before the core rows", "run_all.sh started directly", "the box's wrapper ran cme_test once on CPU 2 (about 0.012 s, exit 0), then run_all.sh; CPU 3 was online and idle during cme_test and went offline after the sysinfo step on both boots", "No: cme_test finished before any row, and both scripts ran on CPU 2 under SCHED_FIFO 10 (a fixed real-time priority) with RT throttling off"],
    ["Extra commands", "100 commands, 2.918 s of chip time", f"{F1['commands']} commands, {F1['chip_s']:.3f} s: run_cme.sh adds 37 CME commands after the core phases", "No: they ran after phases A to E"],
], note="Every cell is quoted from Jesse's two README files; nothing in this table is measured by this page.")}
<ul>
<li><b>How the commands ran.</b> With the folder names and the clock stamps set aside, F1's log.txt equals run 3's except for the 39 lines run_cme.sh adds, by diff. Under the mesh counters (which run for each whole command, chain build, flushes and unmap included), F1's core latency commands lived longer: the four counted 4 KiB controls {min(ctl_life):.2f} to {max(ctl_life):.2f} times run 3's lifetime, the 20 sparse OCM rows 1.24 to 1.60 times, while the counted 2 MiB read lived {life_ratio:.3f} times. These files do not show which part of each command grew; the timed passes inside them repeated run 3 (the controls) or got faster (the read) [cmn-counts.csv of 011 and 004; Jesse's F1 README, Mesh counts].</li>
<li><b>What moved.</b> The figure puts every row of the two boots into {len(groups)} groups and shows each group's lowest and highest speed ratio. A dot at 1.0 is a row that repeated run 3.</li>
</ul>
{fig(f_ratio, f"Every stream of independent reads got faster on F1, by {min(rd1):.2f} to {max(rd1):.2f} times for one core and up to {max(ratio('One core per cluster, 2 and 16 MiB: read')):.2f} times for four cores on four clusters; the L3-sized chains got faster (the L3 now serves them); every write, every control and every chain beyond the L3 repeated run 3.",
      f"Speed ratio of boot F1 over run 3 per row (latency rows: run 3's ns over F1's; bandwidth rows: F1's GB/s over run 3's), the lowest and the highest row of each group, best rows [the CSV files of 011 and 004]. The grid line at 1.0 is no change.")}
{t_ratio}
<ul>
<li><b>What the counters say about the L3-sized chains.</b> At 192 to 384 KiB the L2 refills per load are the same on both boots ({min(l2_3):.2f} to {max(l2_3):.2f} on run 3, {min(l2_1):.2f} to {max(l2_1):.2f} on F1), and the L3 read refills from outside the cluster (event 0xA2: a line that the L3 had to fetch from the mesh) fall from {min(a2_3):.2f} to {max(a2_3):.2f} per load to {min(a2_1):.2f} to {max(a2_1):.2f}. So the L2's misses are served inside the cluster on F1. That is the L3 holding the chain, a measurement [latency-dram-small.csv of 011 and 004].</li>
<li><b>What the counters say about the read streams.</b> Boot E against boot C (one build, the L3 the one change) read {e_over_c[2097152]:.2f} times at 2 MiB and {e_over_c[33554432]:.2f} at 32 MiB with the same refills per line (32 MiB: L1 {e32['l1d_refill']:.2f} and {c32['l1d_refill']:.2f}, L2 {e32['l2d_refill']:.2f} and {c32['l2d_refill']:.2f}, L2 refills caused by the L1 prefetcher {e32['l2d_refill_l1dhwprf']:.2f} and {c32['l2d_refill_l1dhwprf']:.2f}, L3 read refills {e32['l3d_refill_rd']:.4f} and {c32['l3d_refill_rd']:.4f}). On F1 the counted 2 MiB read put {req_ratio:.3f} times run 3's requests on the five home nodes while the command lived {life_ratio:.3f} times as long. So the L3 did not take these reads off the mesh: the same lines were fetched, by the same number of requests, in less time [bandwidth-read-prefetch.csv of 010 and 007; cmn-counts.csv of 011 and 004].</li>
<li><b>What the counters say about the OCM rows.</b> The sparse OCM passes count {statistics.mean(sp_a2_3):.2f} 0xA2 refills per load on run 3 and {statistics.mean(sp_a2_1):.2f} on F1 (means over the 140 passes of each boot), with the same L2 refills ({statistics.mean(sp_l2_3):.2f} and {statistics.mean(sp_l2_1):.2f}). So on F1 part of the OCM lines came from the L3, not from the region's home node. OCM is Normal write-back memory, so the L3 may hold its lines [latency-ocm-region&lt;r&gt;-cpu&lt;c&gt;.csv of 011 and 004].</li>
<li><b>What the multi-core rows add.</b> Four readers on four clusters each keep {per4[0] * 100:.0f} to {per4[1] * 100:.0f} % of F1's one-core rate at 16 MiB ({rd4['tmin']:.1f} to {rd4['tmax']:.1f} GB/s against {ONE1[33554432]['read']:.1f}), so four clusters do not share the limit. Eight readers, two per cluster, read {rd8['agg']:.1f} GB/s together, {rd8['agg'] / 8:.1f} each, so two readers in one cluster share about {rd8['agg'] / 4:.0f} GB/s est. per cluster, near one reader's rate [bandwidth-perdsu.csv, bandwidth-all8.csv of 011].</li>
</ul>
<ul>
<li><b>Hypotheses.</b> Each one names what supports it, what it has to explain, and the measurement that would confirm or reject it.</li>
<li>{hyp(" More reads in flight per cluster.")} With the L3 in full mode the cluster's miss handling goes through the L3 (the snoop-filter-only mode of run 3 passes every L2 miss to the mesh without an L3 lookup). If that path keeps more read requests open at once (in flight: issued and not yet returned), a stream of independent reads overlaps more of its DRAM time, while a chain of dependent loads has one load open and gains nothing, and a store stream is posted (the core does not wait for a store) and already overlaps. Fits: the same refills per line, the same mesh requests, chains beyond the L3 within 4 %, the one-core writes and the placement rows within 0.3 % (the multi-core writes of 2 MiB and above within 7 %), and the per-cluster limit the eight-reader row shows. The test: a count of the requests in flight at the DSU's mesh port around the same one-core read on an L3-on and an L3-off boot, if the mesh PMU offers such an event (to be checked in the CMN-S3 event list). The data on disk do not count requests in flight.</li>
<li>{hyp(" The prefetcher's requests are the ones that overlap more.")} The L2 refills caused by the L1 prefetcher are {e32['l2d_refill_l1dhwprf']:.2f} per line on E and {c32['l2d_refill_l1dhwprf']:.2f} on C, so the prefetcher issues the same number of requests per line on both; the counters do not say how many it keeps open at once. With the prefetchers off and the L3 off, boots B and D read {bd32[0]:.2f} and {bd32[1]:.2f} GB/s at 32 MiB, one line per DRAM latency. The test: run 3's one-core read lines with the prefetchers off on an L3-on boot (boot F2's firmware, which ran run_cme.sh only). A rate near {bd32[0]:.1f} GB/s would say the rise needs the prefetcher; a rate above it would say the L3 path overlaps demand misses on its own.</li>
<li>{hyp(" A per-cluster limit, not a per-core one.")} Four readers on four clusters scale one for one with one reader, and eight readers (two per cluster) get {rd8['agg'] / 4:.0f} GB/s est. per cluster. The test: two readers on two clusters against two readers in one cluster at 16 MiB, the same command otherwise; the pair row at 160 KiB ({M1[('read', 163840, 2)]['agg']:.1f} GB/s on F1 against {m3('read', 163840, 2):.1f} on run 3) is the nearest row on disk and sits in the L2 and L3, not DRAM.</li>
<li><span class="gap">ruled out</span> <b>The build.</b> k_read, k_write and k_copy are byte for byte the same in both builds, and boot E against boot C, one build, shows the read rise ({e_over_c[2097152]:.2f} and {e_over_c[33554432]:.2f} times) with the L3 as the one change. What the build may have moved: the 16 KiB rows, whose buffers fit the L1 (one core read {ratio('One core, 16 KiB: read, write, copy')[0]:.3f} times, write {ratio('One core, 16 KiB: read, write, copy')[1]:.3f}, the pair read {ratio('Pair (CPUs 2, 3), 16 KiB: read, write, copy')[0]:.3f}); run 3's README tied its own 16 KiB write shift to a rebuilt bandwidth, and pass differs again. Insufficient data: these files do not show why the 16 KiB rows moved [Jesse's F1 README, Core rows against round three; Jesse's run 3 README].</li>
<li><span class="gap">ruled out</span> <b>Boards or run-to-run noise.</b> The controls repeat within 0.3 %, the writes from 48 KiB on within {max(abs(x - 1) for x in wr1) * 100:.1f} %, the chains from 1.5 MiB on within {max(abs(x - 1) for x in ch) * 100:.1f} %, and the reps of the one-core read rows spread 1.8 % or less inside each boot. Boot E and boot C ran on other boards and show the same ratio.</li>
<li><span class="gap">partly</span> <b>Page placement on the OCM rows.</b> The /dev/ocm module differs and every process draws its own pages, so a single sparse cell (0.69 to 0.95 times) is within its own spread (up to 60 % between passes of one row). What placement cannot explain: all 20 cells faster, and the 0xA2 fall with the same L2 refills, which says the L3 served part of the loads. The test: the sparse rows with the L3 hit event (the hit set of boot E, section 5) on an L3-on boot.</li>
</ul>
"""
