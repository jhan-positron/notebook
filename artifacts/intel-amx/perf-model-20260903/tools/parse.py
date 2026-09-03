#!/usr/bin/env python3
"""parse.py - turn the raw campaign outputs of run-perf-model.sh into one
medians JSON (exec/results/perf-model-20260903/medians.json).

Every number the report quotes comes from this file, and this file names the
raw file each number came from.
"""
import glob
import json
import os
import re
import statistics
import sys

OUT = os.path.expanduser("~/workspace/intel-AMX/exec/results/perf-model-20260903")
if len(sys.argv) > 1:
    OUT = sys.argv[1]


def med(xs):
    xs = [x for x in xs if x is not None]
    return statistics.median(xs) if xs else None


def parse_m1():
    """memrate aggregate lines -> per_core_GBs by (mode, threads, huge)."""
    res = {}
    path = os.path.join(OUT, "m1-memrate.txt")
    if not os.path.exists(path):
        return res
    for line in open(path):
        m = re.match(r"aggregate mode=(\w+) threads=(\d+) mb=(\d+) seconds=\S+ huge=(\w+) per_core_GBs_mean ([\d.]+) min ([\d.]+) max ([\d.]+) total_GBs ([\d.]+)", line)
        if not m:
            continue
        key = f"{m.group(1)}-t{m.group(2)}-{m.group(4)}"
        res.setdefault(key, {"mode": m.group(1), "threads": int(m.group(2)), "huge": m.group(4), "per_core_mean": [], "per_core_min": [], "total": []})
        res[key]["per_core_mean"].append(float(m.group(5)))
        res[key]["per_core_min"].append(float(m.group(6)))
        res[key]["total"].append(float(m.group(8)))
    for k, v in res.items():
        v["per_core_GBs_median"] = med(v["per_core_mean"])
        v["per_core_GBs_min_median"] = med(v["per_core_min"])
        v["total_GBs_median"] = med(v["total"])
        v["repeats"] = len(v["per_core_mean"])
        v["source"] = "m1-memrate.txt"
    return res


def parse_m2():
    res = {"idle": {}, "loaded": {}, "readers_alive_during_chase": []}
    path = os.path.join(OUT, "m2-latency.txt")
    if not os.path.exists(path):
        return res
    loaded = False
    for line in open(path):
        if line.startswith("## loaded"):
            loaded = True
        m2 = re.search(r"readers still running: (\w+)", line)
        if m2:
            res["readers_alive_during_chase"].append(m2.group(1))
        m = re.match(r"latency cpu (\d+) mb (\d+) huge_requested (\S+) huge_obtained (\S+) anon_huge_mib (\d+) hugetlb_mib (\d+) ns_per_hop ([\d.]+)", line)
        if not m:
            continue
        key = f"mb{m.group(2)}-{m.group(4)}"
        (res["loaded"] if loaded else res["idle"]).setdefault(key, []).append(float(m.group(7)))
    res["idle_ns_median"] = {k: med(v) for k, v in res["idle"].items()}
    res["loaded_ns_median"] = {k: med(v) for k, v in res["loaded"].items()}
    res["source"] = "m2-latency.txt"
    return res


FIELDS = ("unit_ns", "qk_ns", "softmax_ns", "pv_ns", "state_ns", "common_ns", "range_ns_per_unit", "barrier_ns_per_pass", "pass_us")


def parse_m3():
    """unit_bench JSON files -> medians over repeats per configuration."""
    runs = {}
    for f in sorted(glob.glob(os.path.join(OUT, "m3-*.json"))):
        name = os.path.basename(f)[3:-5]  # strip m3- and .json
        cfg = re.sub(r"-r\d+$", "", name)
        try:
            d = json.load(open(f))
        except Exception as e:  # noqa
            print("bad json", f, e, file=sys.stderr)
            continue
        if not d.get("per_thread"):
            continue
        r = runs.setdefault(cfg, {"variant": d["variant"], "pages": d["pages"], "hot": d["hot"], "shuffle": d.get("shuffle", False),
                                  "threads": d["threads"], "huge": d["huge"], "files": [], "w0": [], "all": [],
                                  "units_per_pass": d["per_thread"][0]["units_per_pass"], "passes": d["passes"], "windows": []})
        r["files"].append(os.path.basename(f))
        r["w0"].append(d["worker0"] | {"range_ns_per_unit": d["per_thread"][0].get("range_ns_per_unit")})
        r["all"].append(d["all_median"])
        r["windows"].append((d.get("run_start_epoch"), d.get("run_end_epoch")))
    out = {}
    for cfg, r in runs.items():
        o = {k: r[k] for k in ("variant", "pages", "hot", "shuffle", "threads", "huge", "files", "units_per_pass", "passes", "windows")}
        o["repeats"] = len(r["files"])
        o["timed_phase_s"] = [(w[1] - w[0]) if (w[0] and w[1]) else None for w in r["windows"]]
        for src, key in (("w0", "worker0"), ("all", "all_median")):
            o[key] = {}
            for field in FIELDS:
                vals = [x.get(field) for x in r[src] if x.get(field) is not None]
                if vals:
                    o[key][field] = med(vals)
                    o[key][field + "_spread"] = (max(vals) - min(vals)) / med(vals) if med(vals) else None
        out[cfg] = o
    return out


def turbostat_window(path, t0, t1):
    """median Bzy_MHz over busy cores, samples inside [t0+1, t1] (Time_Of_Day_Seconds column).
    Rows whose field count differs from the header are skipped and counted."""
    mhz, n_all, skipped = [], 0, 0
    cols = None
    for line in open(path):
        parts = line.split()
        if not parts:
            continue
        if "Bzy_MHz" in parts:
            cols = {c: i for i, c in enumerate(parts)}
            continue
        if cols is None:
            continue
        if len(parts) != len(cols):
            skipped += 1
            continue
        try:
            tod = float(parts[cols["Time_Of_Day_Seconds"]]) if "Time_Of_Day_Seconds" in cols else None
            cpu = parts[cols["CPU"]]
            busy = float(parts[cols["Busy%"]])
            f = float(parts[cols["Bzy_MHz"]])
        except (KeyError, ValueError, IndexError):
            skipped += 1
            continue
        if cpu == "-":
            continue
        n_all += 1
        if t0 is not None and t1 is not None and tod is not None and not (t0 + 1.0 <= tod <= t1):
            continue
        if busy > 50:
            mhz.append(f)
    return med(mhz), len(mhz), n_all, skipped


def parse_m4(m3):
    """turbostat files -> median Bzy_MHz over the app cores inside the run window of the matching m3 JSON."""
    res = {}
    for f in sorted(glob.glob(os.path.join(OUT, "m4-turbostat-*.txt"))):
        name = os.path.basename(f)[len("m4-turbostat-"):-4]
        t0 = t1 = None
        jf = os.path.join(OUT, f"m3-{name}.json")
        if os.path.exists(jf):
            try:
                d = json.load(open(jf))
                t0, t1 = d.get("run_start_epoch"), d.get("run_end_epoch")
            except Exception:
                pass
        m, n, n_all, skipped = turbostat_window(f, t0, t1)
        res[name] = {"bzy_mhz_median_busy_cores": m, "samples_in_window": n, "samples_total": n_all, "rows_skipped": skipped, "window": [t0, t1], "source": os.path.basename(f)}
    return res


def parse_m5():
    """one file per loop: m5-<loop>.txt with the loop line, plus m5-turbostat-<loop>.txt."""
    res = {}
    for f in sorted(glob.glob(os.path.join(OUT, "m5-*.txt"))):
        base = os.path.basename(f)
        if base.startswith("m5-turbostat-"):
            continue
        loop = base[3:-4]
        row = {}
        for line in open(f):
            m = re.match(r"(\w+)\s+ns_per_insn ([\d.]+) tsc_ticks_per_insn ([\d.]+)\s+wall_s ([\d.]+)", line)
            if m:
                row = {"ns_per_insn": float(m.group(2)), "tsc_ticks_per_insn": float(m.group(3)), "wall_s": float(m.group(4))}
            if "INSN-FAILED" in line:
                row["failed"] = True
        ts = os.path.join(OUT, f"m5-turbostat-{loop}.txt")
        if os.path.exists(ts):
            mhz, n, n_all, skipped = turbostat_window(ts, None, None)
            row["core_mhz_median"] = mhz
            row["turbostat_samples"] = n
            if mhz and "ns_per_insn" in row:
                row["core_cycles_per_insn"] = row["ns_per_insn"] * mhz / 1000.0
        row["source"] = base
        res[loop] = row
    return res


def parse_m7():
    """fresh Tron AVX-form baseline: m7-phases-disable-c<ctx>.json (extract-sa.py output) -> summary rows like summary.json."""
    res = {}
    for f in sorted(glob.glob(os.path.join(OUT, "m7-phases-disable-c*.json"))):
        ctx = int(re.search(r"c(\d+)\.json", f).group(1))
        try:
            p = json.load(open(f))
        except Exception as e:  # noqa
            print("bad m7 json", f, e, file=sys.stderr)
            continue
        pu = p["per_unit"]
        res[ctx] = {
            "windows": p["windows"], "period_us": p["period_us"], "attn_us": p["attn_us_7605"],
            "sect_us": p["cyc_sections_ready"] + p["cyc_sections_pending"], "joins_us": p["cyc_joins"], "barrier_us": p["cyc_barrier"],
            "range_us": p["cyc_range"], "units": p["units_dotter"], "ranges": p["ranges"],
            "qk_us": pu["dotter_qk"], "common_us": pu["dotter_common"], "pv_us": pu["dotter_pv"], "unit_us": pu["dotter_total"],
            "source": os.path.basename(f),
        }
    # decode speed lines (the 8-token smoke run, rep 0, is kept apart)
    txt = os.path.join(OUT, "m7-tron-avx.txt")
    if os.path.exists(txt):
        cur = None
        for line in open(txt):
            m = re.search(r"ctx=(\d+) len=(\d+) .* rep=(\d+)", line)
            if m:
                cur = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            m = re.search(r"at ([\d.]+) average tok/s, or ([\d.]+) ms/tok", line)
            if m and cur and cur[0] in res:
                key = "tok_s" if (cur[1] >= 256 and cur[2] > 0) else "tok_s_smoke"
                res[cur[0]].setdefault(key, []).append(float(m.group(1)))
    return res


def main():
    m3 = parse_m3()
    out = {"m1_memrate": parse_m1(), "m2_latency": parse_m2(), "m3_unit_bench": m3, "m4_clocks": parse_m4(m3), "m5_insn": parse_m5(), "m7_tron_avx": parse_m7()}
    path = os.path.join(OUT, "medians.json")
    json.dump(out, open(path, "w"), indent=1)
    print("wrote", path)
    for cfg, o in sorted(m3.items()):
        w = o["worker0"]
        print(f"{cfg:26s} reps={o['repeats']} unit {w.get('unit_ns', 0):7.0f} ns = qk {w.get('qk_ns', 0):6.0f} + sm {w.get('softmax_ns', 0):5.0f} + pv {w.get('pv_ns', 0):6.0f} + st {w.get('state_ns', 0):5.0f} + common {w.get('common_ns', 0):5.0f}   all-thread {o['all_median'].get('unit_ns', 0):7.0f}  spread {100 * (w.get('unit_ns_spread') or 0):.1f}%  timed {o['timed_phase_s']}")
    for k, v in sorted(out["m1_memrate"].items()):
        print(f"memrate {k:16s} per-core {v['per_core_GBs_median']:.2f} GB/s (min {v['per_core_GBs_min_median']:.2f})  total {v['total_GBs_median']:.1f}")
    print("latency idle:", out["m2_latency"].get("idle_ns_median"), "loaded:", out["m2_latency"].get("loaded_ns_median"), "readers alive:", out["m2_latency"].get("readers_alive_during_chase"))
    print("clocks:", {k: (v["bzy_mhz_median_busy_cores"], v["samples_in_window"]) for k, v in out["m4_clocks"].items()})
    for k, v in out["m5_insn"].items():
        print(f"insn {k:10s} {v}")
    for ctx, v in sorted(out["m7_tron_avx"].items()):
        print(f"tron avx ctx {ctx}: period {v['period_us']:.0f} attn {v['attn_us']:.0f} sect {v['sect_us']:.0f} joins {v['joins_us']:.0f} barrier {v['barrier_us']:.0f} units {v['units']:.0f} ranges {v['ranges']:.0f} unit {v['unit_us']:.3f} = qk {v['qk_us']:.3f} + common {v['common_us']:.3f} + pv {v['pv_us']:.3f}  tok/s {v.get('tok_s')}")


if __name__ == "__main__":
    main()
