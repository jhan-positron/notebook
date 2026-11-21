#!/usr/bin/env python3
"""Run 6 (2026-11-06 and 07): boots F1 and F2 on commit 0c190a1, read into tables for gen_perf.py.

  F1  results/membench-jibin-011/results/bootF1/   boot E's firmware (SCP 0.48.0-nopcie-l3.1, TF-A 0.35.0): the L3 on, the
                                                     prefetchers on; cme_test once, then sh run_all.sh (run 3's command set,
                                                     core and CME, plus the run 6 rows: 137 commands)
  F2  results/membench-jibin-012/results/bootF2/   the same SCP with boot B's TF-A 0.35.0-pfoff.1: the L3 on, the data
                                                     prefetchers of the cores and the CMEs off; sh run_cme.sh only (70 commands)

Run 6's --cme rows carry the in-span time next to the bracket time: ns_per_load_span (latency, column 7, before the
counters) and span_s, span_GBps (bandwidth, after per_thread_max_GBps). The readers here take both; gen_run3.lat_rows
already skips the latency span column, so its row dicts are reused and the counters are named from the header.

load_core(R) builds the same tables gen_run3 builds for run 3 (levels, OCM chains, bandwidth, mesh attribution), from
one directory. load_cme(R) builds the CME tables (chains with the split refill events, the L3-event rows, the OCM chains,
the bandwidth sweep with its single-call twins, the four L1 forms with their fits, the call-cost blocks). Nothing is
typed in except the facts quoted from Jesse's two README files (cited where used).
"""
import os, re, glob, statistics, collections
import gen_run3 as g
from gen_run3 import lat_rows, bw_rows, cmn_rows, best, passes, best_pass, dist, NODE_OF_REGION, CPU_DSU

A = os.path.dirname(os.path.abspath(__file__))
RUN = dict(F1=A + "/results/membench-jibin-011/", F2=A + "/results/membench-jibin-012/")
DIR = dict(F1=RUN["F1"] + "results/bootF1/", F2=RUN["F2"] + "results/bootF2/")
RUN_ID = dict(F1="011", F2="012")

# ---------------------------------------------------------------- readers
def counter_names(path):
    """the counter columns of a latency CSV without the _per_load suffix, c1..cN in order (the span column, if any, skipped)"""
    for line in open(path):
        if line.startswith("mem,"):
            cols = line.rstrip("\n").split(","); b = 8 if "ns_per_load_span" in line else 7
            return [c.replace("_per_load", "") for c in cols[b:-1]]
    raise KeyError(path)

def lat(path):
    """gen_run3.lat_rows plus e = {counter name: value} on every measured row (span is already on the --cme rows)"""
    names = counter_names(path); rows = lat_rows(path)
    for d in rows:
        if "c1" in d: d["e"] = {n: d[f"c{i + 1}"] for i, n in enumerate(names)}
    return rows

def bw(path):
    """gen_run3.bw_rows plus span (GB/s inside the streaming span, --cme rows only; None elsewhere)"""
    rows = bw_rows(path); raw = [l.rstrip("\n").split(",") for l in open(path) if not l.startswith("#") and not l.startswith("mem,")]
    assert len(rows) == len(raw)
    for d, f in zip(rows, raw): d["span"] = float(f[11]) if len(f) >= 12 and f[11] not in ("-", "") else None
    return rows

def bw_best(R, f, key="agg", **kw):
    """the best rep's aggregate GB/s (or its span GB/s) of one kernel and footprint"""
    rows = bw(R + f); b = best(rows, **kw)
    if key == "agg": return b["agg"]
    rep = [d for d in rows if d["rep"] != "best" and all(d[k] == v for k, v in kw.items()) and abs(d["agg"] - b["agg"]) < 1e-9][0]
    return rep["span"]

def fit_line(points):
    """least squares t = a + b * x over (x, t): a (ns at 0 bytes), 1 / b (GB/s), the largest |residual| in ns"""
    a, b, resid = __import__("l1_reader").fit(points)
    return dict(a_ns=a, rate=1 / b, resid=resid)

def mean_e(ps, k): return statistics.mean(p["e"][k] for p in ps)
def rng_e(ps, k): return (min(p["e"][k] for p in ps), max(p["e"][k] for p in ps))

# ---------------------------------------------------------------- the boot's record
def facts(x):
    R, RA = RUN[x], DIR[x]
    README = open(R + "README.md").read(); LOG = open(RA + "log.txt").read()
    CMDS = [re.sub(r"\s*\[uptime.*$", "", re.sub(r"/opt/membench/[^ ]*/", "", l[2:].rstrip("\n"))) for l in LOG.splitlines() if l.startswith("+ ")]
    FAILED = int(re.search(r"(\d+) measurement command\(s\) failed", LOG).group(1))
    N_PERF_FLAG = sum(1 for f in glob.glob(RA + "*.csv") for l in open(f) if l.startswith("# perf:"))
    assert FAILED == 0 and N_PERF_FLAG == 0 and "cpu3 online=0" in LOG and "cpu3 online=1" in LOG, x
    chip = re.search(r"MB RUN end status=exit:0 ns=(\d+)", README)
    pwr = re.findall(r"# box clusterpwrstat (?:before|after) cme-l3: (0x[0-9a-f]+)", LOG)   # the box's two comment lines around the first --events cme-l3 command
    date = re.search(r"on (2026-\d\d-\d\d(?: and \d\d)?) \(UTC\)", README).group(1)
    commit = re.search(r"commit `([0-9a-f]{7})", README).group(1)
    tfa = "0.35.0-pfoff.1" if x == "F2" else "0.35.0"   # README: F2 is F1's platform with boot B's TF-A [README of 012, Read first]
    cov = [d["cov"] for f in sorted(glob.glob(RA + "*latency-*.csv")) for d in lat(f) if d.get("cov") is not None]
    assert all(c == 1.0 for c in cov), x
    return dict(boot=x, run_id=RUN_ID[x], dir=f"results/membench-jibin-{RUN_ID[x]}/results/boot{x}/", commit=commit, scp="0.48.0-nopcie-l3.1", tfa=tfa,
                pf_on=x == "F1", l3_on=pwr == ["0x70", "0x70"], pwrstat=pwr, date=date, chip_s=float(chip.group(1)) / 1e9, commands=len(CMDS), cmds=CMDS,
                files=sum(1 for f in os.listdir(RA) if f.endswith(".csv")), cov_rows=len(cov), readme_sha=None)

# ---------------------------------------------------------------- the core tables (F1 only: run 3's command set with the L3 on)
def load_core(R):
    LV = g.levels_of(R)   # size, kind, ns, l1, l2, l3 (the best pass's refills per load), cov
    for d in LV:
        rows = lat(R + ("latency-dram-flushed.csv" if d["kind"] == "flushed" else "latency-dram-large.csv" if d["kind"] == "fresh" else "latency-dram-small.csv"))
        ps = passes(rows, d["size"]); d["emean"] = {k: mean_e(ps, k) for k in ps[0]["e"]}; d["e"] = best_pass(rows, d["size"])["e"]; d["n"] = len(ps)
    OCM, ALL5S, ALL5D, SLC, CTRL = {}, {}, {}, {}, {}
    for c in (2, 4, 6, 8):
        OCM[c] = {}
        for r in range(5):
            rows = lat(f"{R}latency-ocm-region{r}-cpu{c}.csv"); ps = passes(rows, 262144)
            assert rows[0]["lines"] == 64 and rows[0]["loads"] == "64"
            OCM[c][r] = dict(best=best(rows)["ns"], median=statistics.median(p["ns"] for p in ps), dist=dist(c, NODE_OF_REGION[r]),
                             passes=[dict(ns=p["ns"], l1=p["c1"], l2=p["c2"], l3=p["c3"], cyc=p["cyc"]) for p in ps],
                             l3=mean_e(ps, "l3d_refill_rd"), pf=mean_e(ps, "l2d_refill_hwprf"), l2=mean_e(ps, "l2d_refill"))
        rows = lat(f"{R}latency-ocm-all5-cpu{c}.csv"); ps = passes(rows, 1310720)
        ALL5S[c] = dict(best=best(rows)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[p["ns"] for p in ps], l3=[p["c3"] for p in ps], l3_mean=mean_e(ps, "l3d_refill_rd"))
        rows = lat(f"{R}latency-ocm-all5-dense-cpu{c}.csv"); ps = passes(rows, 1310720)
        ALL5D[c] = dict(best=best(rows)["ns"], passes=[p["ns"] for p in ps], l3=[p["c3"] for p in ps], l3_mean=mean_e(ps, "l3d_refill_rd"), l2_mean=mean_e(ps, "l2d_refill"))
        f = "latency-dram-large.csv" if c == 2 else f"latency-dram-slc-cpu{c}.csv"
        rows = lat(R + f); SLC[c] = dict(best=best(rows, size=2097152)["ns"], l3=best_pass(rows, 2097152)["e"]["l3d_refill_rd"])
        CTRL[c] = dict(best=best(lat(f"{R}latency-control-cpu{c}.csv"))["ns"])
    P4K = best_pass(lat(R + "latency-dram-small.csv"), 4096)
    # bandwidth: the one-core sweep, the multi-core rows, writer placement, OCM, the spread control
    one_rows = bw(R + "bandwidth-dram-1core.csv")
    ONE = [dict(size=s, **{k: best(one_rows, kernel=k, bpt=s)["agg"] for k in ("read", "write", "copy")}) for s in sorted({d["bpt"] for d in one_rows})]
    def multi(f):
        rows = bw(R + f)
        def best_rep(d): return [r for r in rows if r["rep"] != "best" and r["kernel"] == d["kernel"] and r["bpt"] == d["bpt"] and abs(r["agg"] - d["agg"]) < 1e-9][0]
        return [dict(kernel=d["kernel"], threads=d["threads"], size=d["bpt"], agg=d["agg"], tmin=float(best_rep(d)["tmin"]), tmax=float(best_rep(d)["tmax"])) for d in rows if d["rep"] == "best"]
    PAIR, PERDSU, ALL8 = multi("bandwidth-pair.csv"), multi("bandwidth-perdsu.csv"), multi("bandwidth-all8.csv")
    PLACE = []
    for cpus in ("2-3", "2-4", "2-8", "2-3-4-5", "2-3-8-9", "2-4-6-8"):
        rows = bw(f"{R}bandwidth-write-cpus{cpus}.csv"); b = best(rows); reps = [d for d in rows if d["rep"] != "best"]
        PLACE.append(dict(cpus=cpus, agg=b["agg"], dsus=sorted({CPU_DSU[int(c)] for c in cpus.split("-")}), tmin=min(float(d["tmin"]) for d in reps), tmax=max(float(d["tmax"]) for d in reps)))
    OCMBW = dict(region=[bw_best(R, f"bandwidth-ocm-region{r}.csv") for r in range(5)], all5=bw_best(R, "bandwidth-ocm-all5.csv"), four=bw_best(R, "bandwidth-ocm-4core.csv"), write=bw_best(R, "bandwidth-ocm-write.csv"),
                 region_reps=[[d["agg"] for d in bw(f"{R}bandwidth-ocm-region{r}.csv") if d["rep"] != "best"] for r in range(5)])
    SPREAD1 = bw_best(R, "bandwidth-dram-spread.csv")
    # mesh counters around the core commands (and the CME commands of the same file)
    CMN = cmn_rows(R + "cmn-counts.csv")
    ATTR = {(c, r): g.attribution(CMN, f"ocm-region{r}-cpu{c}", r) for c in (2, 4, 6, 8) for r in range(5)}
    ATTR_READ = {r: g.attribution(CMN, f"ocm-read-region{r}", r) for r in range(5)}
    ATTR_READ_CME = {r: g.attribution(CMN, f"cme-ocm-read-region{r}", r) for r in range(5)}
    ATTR_CME = {r: g.attribution(CMN, f"cme-ocm-region{r}-cpu2", r) for r in range(5)}
    COST = dict(counted=CMN["control-cpu2"]["helper"], uncounted=CMN["control-nocount-cpu2"]["helper"], child_c=CMN["control-cpu2"]["child"], child_u=CMN["control-nocount-cpu2"]["child"])
    BG = [v for c in (2, 4, 6, 8) for v in CMN[f"control-cpu{c}"]["node"].values()]
    FLUSH_SPREAD = sorted(CMN["cme-dram-flushed-8M-cpu2"]["node"].values())
    return dict(LV=LV, OCM=OCM, ALL5S=ALL5S, ALL5D=ALL5D, SLC=SLC, CTRL=CTRL, P4K=P4K, ONE=ONE, PAIR=PAIR, PERDSU=PERDSU, ALL8=ALL8, PLACE=PLACE, OCMBW=OCMBW, SPREAD1=SPREAD1,
                CMN=CMN, ATTR=ATTR, ATTR_READ=ATTR_READ, ATTR_READ_CME=ATTR_READ_CME, ATTR_CME=ATTR_CME, COST=COST, BG=BG, FLUSH_SPREAD=FLUSH_SPREAD,
                CME_OCM_OWN_RATIO=[ATTR_CME[r]["own"] / ATTR[(2, r)]["own"] for r in range(5)], CME_READ_OWN_RATIO=[ATTR_READ_CME[r]["own"] / ATTR_READ[r]["own"] for r in range(5)])

# ---------------------------------------------------------------- the CME tables (both boots)
FORMS = (("looped", "cme-bandwidth-l1-passes.csv"), ("single", "cme-bandwidth-l1-asmpasses.csv"), ("nofold", "cme-bandwidth-l1-nofold.csv"), ("dsb", "cme-bandwidth-l1-dsb.csv"))
FORM_NAME = dict(looped="looped form (one call per pass)", single="single-call form (every pass of a rep in one call)", nofold="looped read without the end-of-call fold", dsb="looped write with DSB ST before SMSTOP")
L1_SIZES = (4096, 8192, 16384, 24576)

def load_cme(R):
    def chains(files):
        out = []
        for f, kind in files:
            rows = lat(R + f)
            for d in rows:
                if not d["mode"].endswith("best") or "roundtrip" in d["mode"] or "call" in d["mode"]: continue
                ps = passes(rows, d["size"]); bp = best_pass(rows, d["size"])
                out.append(dict(size=d["size"], kind=kind, ns=d["ns"], span=bp["span"], e=bp["e"], emean={k: mean_e(ps, k) for k in bp["e"]}, erng={k: rng_e(ps, k) for k in bp["e"]}, n=len(ps),
                                ns_rng=(min(p["ns"] for p in ps), max(p["ns"] for p in ps)), reps=[(p["ns"], p["span"]) for p in ps]))
        return out
    CLV = chains((("cme-latency-dram-small.csv", "repeat"), ("cme-latency-dram-large.csv", "fresh"), ("cme-latency-dram-flushed.csv", "flushed")))
    CL3 = chains((("cme-latency-dram-small-l3.csv", "repeat"), ("cme-latency-dram-large-l3.csv", "fresh")))   # the exploratory L3 events 0x328E hit, 0x328F miss, 0x3290 refill
    for d in CL3:
        d["hit"] = d["e"]["cme_l3d_hit"]; d["miss"] = d["e"]["cme_l3d_miss"]; d["refill"] = d["e"]["cme_l3d_refill"]
        d["snoop"] = d["miss"] - d["refill"]   # by Jesse's reading of the RTL: refills a core's cache in the cluster supplied (derived, not a counted event)
    RT, CALL = [], []
    for f in sorted(glob.glob(R + "cme-latency-*.csv")):
        for d in lat(f):
            if d["mode"] == "cme-roundtrip": RT.append(d)
            if d["mode"] == "cme-call": CALL.append(d)
    RT_NS = (min(d["ns"] for d in RT), max(d["ns"] for d in RT)); RT_SPAN = (min(d["span"] for d in RT), max(d["span"] for d in RT)); RT_CYC = (min(d["c1"] for d in RT), max(d["c1"] for d in RT))
    CALL_NS = (min(d["ns"] for d in CALL), max(d["ns"] for d in CALL)); CALL_SPAN = (min(d["span"] for d in CALL), max(d["span"] for d in CALL))
    COCM = {}
    for r in range(5):
        rows = lat(f"{R}cme-latency-ocm-region{r}.csv"); ps = passes(rows, 262144)
        COCM[r] = dict(best=best(rows, size=262144)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[(p["ns"], p["e"]["cme_l1d_refill_outer"]) for p in ps], dist=dist(2, NODE_OF_REGION[r]),
                       emean={k: mean_e(ps, k) for k in ps[0]["e"]}, span=best_pass(rows, 262144)["span"])
    def all5(f):
        rows = lat(R + f); ps = passes(rows, 1310720)
        return dict(best=best(rows, size=1310720)["ns"], median=statistics.median(p["ns"] for p in ps), passes=[(p["ns"], p["e"]["cme_l1d_refill_outer"]) for p in ps], emean={k: mean_e(ps, k) for k in ps[0]["e"]})
    CALL5S, CALL5D = all5("cme-latency-ocm-all5.csv"), all5("cme-latency-ocm-all5-dense.csv")
    # the bandwidth sweep (run 3's command lines) with its single-call twins at 48 to 256 KiB
    sweep = bw(R + "cme-bandwidth-dram-1core.csv"); twins = bw(R + "cme-bandwidth-dram-1core-asmpasses.csv")
    def bb(rows, k, s):
        b = best(rows, kernel=k, bpt=s); rep = [d for d in rows if d["rep"] != "best" and d["kernel"] == k and d["bpt"] == s and abs(d["agg"] - b["agg"]) < 1e-9][0]
        return dict(agg=b["agg"], span=rep["span"], reps=[d["agg"] for d in rows if d["rep"] != "best" and d["kernel"] == k and d["bpt"] == s])
    CBW = [dict(size=s, **{k: bb(sweep, "cme-" + k, s) for k in ("read", "write", "copy")}) for s in sorted({d["bpt"] for d in sweep if d["kernel"] == "cme-read"})]
    NARROW = [dict(size=s, **{k: bb(sweep, "cme-" + k, s) for k in ("ldr16", "str16", "read", "write")}) for s in sorted({d["bpt"] for d in sweep if d["kernel"] == "cme-ldr16"})]
    CBW_ASM = [dict(size=s, **{k: bb(twins, "cme-" + k, s) for k in ("read", "write")}) for s in sorted({d["bpt"] for d in twins})]
    # the four L1 forms at 4 to 24 KiB with their fits (ns per pass = bytes / GB/s; a line t = a + bytes / rate, bracket and in span)
    FORM = {}
    for form, f in FORMS:
        rows = bw(R + f)
        for k in sorted({d["kernel"] for d in rows}):
            kern = k.replace("cme-", "")
            per = {s: bb(rows, k, s) for s in L1_SIZES}
            for s, v in per.items(): v["t_pass"] = s / v["agg"]; v["t_span"] = s / v["span"]
            fb = fit_line([(s, per[s]["t_pass"]) for s in L1_SIZES]); fs = fit_line([(s, per[s]["t_span"]) for s in L1_SIZES])
            t_min = min(per[s]["t_pass"] for s in L1_SIZES)
            FORM[(form, kern)] = dict(rows=per, fit=fb, fit_span=fs, ok=fb["resid"] < 0.02 * t_min, file=f)
    # the call-cost blocks: 1 KiB read, 1 to 8 KiB writes (ns per call, bracket and in span, best rep)
    cc = bw(R + "cme-bandwidth-call-cost.csv"); CALLCOST = {}
    for k in sorted({d["kernel"] for d in cc}):
        for s in sorted({d["bpt"] for d in cc if d["kernel"] == k}):
            v = bb(cc, k, s); CALLCOST[(k.replace("cme-", ""), s)] = dict(ns=s / v["agg"], span_ns=s / v["span"], agg=v["agg"], span=v["span"])
    COCMBW = dict(region=[bw_best(R, f"cme-bandwidth-ocm-region{r}.csv") for r in range(5)], all5=bw_best(R, "cme-bandwidth-ocm-all5.csv"), write=bw_best(R, "cme-bandwidth-ocm-write.csv"),
                  region_span=[bw_best(R, f"cme-bandwidth-ocm-region{r}.csv", "span") for r in range(5)], all5_span=bw_best(R, "cme-bandwidth-ocm-all5.csv", "span"), write_span=bw_best(R, "cme-bandwidth-ocm-write.csv", "span"),
                  region_reps=[[d["agg"] for d in bw(f"{R}cme-bandwidth-ocm-region{r}.csv") if d["rep"] != "best"] for r in range(5)])
    N_CHAIN_ROWS = sum(d["n"] for d in CLV); PF_RNG = (min(min(d["erng"]["cme_l1d_refill_hwprf"]) for d in CLV), max(max(d["erng"]["cme_l1d_refill_hwprf"]) for d in CLV))
    return dict(CLV=CLV, CL3=CL3, RT=RT, CALL=CALL, RT_NS=RT_NS, RT_SPAN=RT_SPAN, RT_CYC=RT_CYC, CALL_NS=CALL_NS, CALL_SPAN=CALL_SPAN, COCM=COCM, CALL5S=CALL5S, CALL5D=CALL5D,
                CBW=CBW, NARROW=NARROW, CBW_ASM=CBW_ASM, FORM=FORM, CALLCOST=CALLCOST, COCMBW=COCMBW, N_CHAIN_ROWS=N_CHAIN_ROWS, PF_RNG=PF_RNG,
                W32=next(d for d in CBW if d["size"] == 33554432)["write"]["agg"])

# ---------------------------------------------------------------- the two boots
F1 = dict(facts("F1"), core=load_core(DIR["F1"]), cme=load_cme(DIR["F1"]))
F2 = dict(facts("F2"), cme=load_cme(DIR["F2"]))
BOOTS = dict(F1=F1, F2=F2)
# F2's CME chains with every refill a demand refill: the time of a load served inside the cluster, by the exploratory L3 events
# (a least-squares reading over the 96 to 384 KiB reps, est.: the three columns are near-collinear, so the split is a hypothesis)
def l3_fit():
    import numpy as np
    X, Y = [], []
    for d in F2["cme"]["CL3"]:
        if d["kind"] != "repeat" or d["size"] < 98304: continue
        rows = lat(DIR["F2"] + "cme-latency-dram-small-l3.csv")
        for p in passes(rows, d["size"]):
            X.append([1, p["e"]["cme_l3d_hit"], p["e"]["cme_l3d_miss"] - p["e"]["cme_l3d_refill"], p["e"]["cme_l3d_refill"]]); Y.append(p["ns"])
    X, Y = np.array(X), np.array(Y); co, *_ = np.linalg.lstsq(X, Y, rcond=None)
    return dict(const=co[0], hit=co[1], snoop=co[2], outer=co[3], rms=float(np.sqrt(np.mean((X @ co - Y) ** 2))), n=len(Y))
F2["L3FIT"] = l3_fit()

# sanity: a wrong wiring fails here
assert F1["commit"] == F2["commit"] == "0c190a1" and F1["l3_on"] and F2["l3_on"], (F1["commit"], F1["pwrstat"], F2["pwrstat"])
assert F1["commands"] == 137 and F2["commands"] == 70, (F1["commands"], F2["commands"])
assert F2["cme"]["PF_RNG"] == (0.0, 0.0) and F1["cme"]["PF_RNG"][1] > 10, (F2["cme"]["PF_RNG"], F1["cme"]["PF_RNG"])
assert abs(F1["core"]["P4K"]["ns"] - 2.002) < 0.002 and all(abs(x - 21.005) < 0.002 for b in BOOTS.values() for x in b["cme"]["RT_NS"])

if __name__ == "__main__":
    for x, b in BOOTS.items():
        print(f"{x}: {b['dir']} commit {b['commit']} SCP {b['scp']} TF-A {b['tfa']} L3 {b['pwrstat']} date {b['date']} chip {b['chip_s']:.3f} s, {b['commands']} commands, {b['files']} csv, {b['cov_rows']} counted rows")
        c = b["cme"]; print(f"   round trip {c['RT_NS']} span {c['RT_SPAN']}; cme-call {c['CALL_NS']} span {c['CALL_SPAN']}; chain rows {c['N_CHAIN_ROWS']}, prefetch refills per load {c['PF_RNG']}")
        print("   chains:", ", ".join(f"{g.kib(d['size'])} {d['ns']:.2f}" for d in c["CLV"] if d["kind"] == "repeat"))
        print("   L3 rows:", ", ".join(f"{g.kib(d['size'])} {d['ns']:.1f} hit {d['hit']:.2f} snoop {d['snoop']:.2f} out {d['refill']:.2f}" for d in c["CL3"] if d["kind"] == "repeat" and d["size"] >= 65536))
        print("   OCM:", ", ".join(f"OCM{r} {c['COCM'][r]['best']:.2f}" for r in range(5)), f"all5 {c['CALL5S']['best']:.2f} dense {c['CALL5D']['best']:.2f}")
        print("   sweep read:", ", ".join(f"{g.kib(d['size'])} {d['read']['agg']:.1f} ({d['read']['span']:.1f})" for d in c["CBW"]))
        print("   forms:", ", ".join(f"{f} {k}: a {v['fit']['a_ns']:.1f} ns, {v['fit']['rate']:.1f} GB/s, resid {v['fit']['resid']:.1f} ns, {'ok' if v['ok'] else 'no fit'}" for (f, k), v in c["FORM"].items()))
        print("   call cost:", ", ".join(f"{k} {g.kib(s)} {v['ns']:.1f} ns ({v['span_ns']:.1f})" for (k, s), v in c["CALLCOST"].items()))
    print("F2 L3 fit:", {k: round(v, 2) if isinstance(v, float) else v for k, v in F2["L3FIT"].items()})
    k = F1["core"]; print("F1 core: ONE", [(g.kib(d["size"]), round(d["read"], 1), round(d["write"], 1)) for d in k["ONE"]][:3], "...; PERDSU", [(d["kernel"], g.kib(d["size"]), round(d["agg"], 1)) for d in k["PERDSU"]][:4], "; OCMBW", {q: (round(v, 1) if isinstance(v, float) else [round(x, 1) for x in v]) for q, v in k["OCMBW"].items() if q != "region_reps"})
    print("F1 core chains:", ", ".join(f"{g.kib(d['size'])} {d['ns']:.2f}" for d in k["LV"] if d["size"] in (4096, 131072, 196608, 262144, 393216, 2097152, 33554432)), "; CPU 4/6 OCM best", [round(k["OCM"][c][r]["best"], 2) for c in (4, 6) for r in range(5)])
