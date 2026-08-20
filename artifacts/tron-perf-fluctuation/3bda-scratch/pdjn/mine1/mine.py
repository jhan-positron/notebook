import csv, glob, os, re, subprocess, statistics, sys

CAMPAIGNS = [
  "/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-qwen3-4b-20260809T1626Z",
  "/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-gptoss20b-20260809T1752Z",
  "/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-20260807T0143Z",
  "/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-20260807T0206Z",
  "/scratch/jhan/perf-fluctuation/tron-perfetto-5cat-20b-20260807T0306Z",
  "/scratch/jhan/tron-perfetto-5cat-20260806T2145Z",
]
OUT = "/scratch/jhan/pdjn/mine1"
SQL = os.path.join(OUT, "dump.sql")

def gen_map(camp):
    m = {}
    jl = os.path.join(camp, "journal.log")
    if os.path.exists(jl):
        for line in open(jl):
            mm = re.search(r"(draw_\d+|smoke) OK generate=([0-9.]+|None)", line)
            if mm and mm.group(2) != "None":
                m[mm.group(1)] = float(mm.group(2))
    return m

def pctl(v, p):
    if not v: return 0
    s = sorted(v); k = min(len(s)-1, int(round(p/100.0*(len(s)-1))))
    return s[k]

SEL = [int(x) for x in sys.argv[1:]] or list(range(len(CAMPAIGNS)))
rows = []
for ci, camp in enumerate(CAMPAIGNS):
    if ci not in SEL: continue
    gens = gen_map(camp)
    for draw_dir in sorted(glob.glob(os.path.join(camp, "results", "draw_*"))):
        draw = os.path.basename(draw_dir)
        if "smoke" in draw: continue
        tr = os.path.join(draw_dir, "trace.pftrace")
        if not os.path.exists(tr): continue
        raw = os.path.join(OUT, "raw_%s_%s.csv" % (os.path.basename(camp), draw))
        if not os.path.exists(raw) or os.path.getsize(raw) == 0:
            try:
                out = subprocess.run(["trace_processor", "-q", SQL, tr],
                    capture_output=True, text=True, timeout=900).stdout
            except Exception as e:
                print("FAIL", camp, draw, e, flush=True); continue
            with open(raw, "w") as f: f.write(out)
        flb, wfl = [], []
        with open(raw) as f:
            for line in f:
                if line.startswith('"fill_logits_buffer"') or line.startswith('"waiting_for_logits"'):
                    parts = line.strip().split(",")
                    try: dur = int(parts[2])
                    except Exception: continue
                    (flb if "fill_logits" in parts[0] else wfl).append(dur/1000.0)
        if not flb:
            print("NOSLICE", camp, draw, flush=True); continue
        rows.append({
            "campaign": os.path.basename(camp), "draw": draw,
            "gen": gens.get(draw, ""),
            "flb_n": len(flb),
            "flb_mean_us": round(statistics.mean(flb),1),
            "flb_med_us": round(statistics.median(flb),1),
            "flb_p90_us": round(pctl(flb,90),1),
            "flb_max_us": round(max(flb),1),
            "flb_frac_ge300": round(sum(1 for x in flb if x>=300)/len(flb),4),
            "flb_sum_ms": round(sum(flb)/1000.0,1),
            "wfl_n": len(wfl),
            "wfl_mean_us": round(statistics.mean(wfl),1) if wfl else 0,
            "wfl_sum_ms": round(sum(wfl)/1000.0,1) if wfl else 0,
        })
        print("OK", os.path.basename(camp), draw, rows[-1]["flb_mean_us"], flush=True)

if rows:
    with open(os.path.join(OUT, "summary_%s.csv" % "_".join(map(str,SEL))), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
print("DONE", len(rows), flush=True)
