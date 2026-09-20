"""Source H for exec/canon-ci-20260918/gen_ci_shapes.py: the l8b-levers campaign of 2026-09-19 (test T0).

register(R) reads exec/results/l8b-levers-20260919/summary.json (written by analyze.py) and the check-cell record, and
adds registry entries with tag "H" so that every number the page shows from this campaign carries its source. Keys:
  h_gain_<cell>, h_t_<cell>, h_res_<cell> (yes/no), h_base_<cell>, h_canon_<cell>, h_min_<cell> (slowest sample nightly/AMX),
  h_p05_<cell>, h_ttft_<cell>, h_wall_<cell> (min per config) for cell in 2u1024 2u2048 2u3000 2u4096 4u1024 8u1024 8u2048;
  h_passes, h_configs, h_n_resolved, h_n_complete, h_ovh (measured server overhead), h_trunc (4096), h_trunc70 (8192),
  h_pair (verdict text), h_triple (verdict text), h_triple_ok (the 1-user spread rule), h_check_* (the 32u x 8192 check cell),
  h_date, h_start, h_end, h_kv_<cell> (K KV tokens per engine step from the measured overhead), h_band2 / h_band8 (inside?).
Cells not in the summary get "n/a" so the page still renders.
"""
import glob
import json
import os
import re

RES = "/home/jhan/workspace/intel-AMX/exec/results/l8b-levers-20260919"
CELLS = {"2u1024": "llama_3_1_8b_instruct_good_tp2_8u_p1024", "2u2048": "llama_3_1_8b_instruct_good_tp2_8u_p2048",
         "2u3000": "llama_3_1_8b_instruct_good_tp2_8u_p3000", "2u4096": "llama_3_1_8b_instruct_good_tp2_8u_p4096",
         "4u1024": "llama_3_1_8b_instruct_good_tp2_16u_p1024", "8u1024": "llama_3_1_8b_instruct_good_tp2_32u_p1024",
         "8u2048": "llama_3_1_8b_instruct_good_tp2_32u_p2048"}
UPE = {"2u": 2, "4u": 4, "8u": 8}


def _f(x, nd=1, sign=False):
    if x is None:
        return "n/a"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def register(R, res=RES):
    s = json.load(open(os.path.join(res, "summary.json")))
    cfg = s["configs"]
    # measured server overhead (prompt tokens counted by the server minus prompt_length), mean over all pass records
    ovh_vals = []
    for n, e in cfg.items():
        p = int(re.search(r"_p(\d+)$", n).group(1))
        for pv in e.get("per_pass", {}).values():
            if pv.get("prompt_tokens_mean") and p < 4096:   # the 4096 cell is clipped to 4096 by the tokenizer, so it carries no overhead
                ovh_vals.append(pv["prompt_tokens_mean"] - p)
    ovh = sum(ovh_vals) / len(ovh_vals) if ovh_vals else None
    R.add("h_ovh", _f(ovh, 1), "H", "tokens the server counted around prompt_length in the l8b-levers cells below 4096 (mean over pass records)")
    for short, name in CELLS.items():
        e = cfg.get(name, {})
        n = e.get("n_pairs", 0)
        upe = UPE[short[:2]]
        p = int(short[2:])
        kv = upe * (min(p, 4096) + (ovh or 31) + 960) / 1000
        R.add(f"h_kv_{short}", f"{kv:.1f}", "derived", f"K KV tokens per engine step of the {short} cell: {upe} x (prompt {min(p, 4096)} + {_f(ovh, 1)} + 960)")
        if n:
            R.add(f"h_gain_{short}", _f(e["gain_pct"], 1, True), "H", f"% gain of the canonical-AMX deb over the nightly deb, {short}, mean over {n} passes")
            t = e.get("paired_t")
            R.add(f"h_t_{short}", "inf" if t is not None and t == float("inf") else _f(t, 2), "H", f"paired t over {n} passes, {short}")
            R.add(f"h_res_{short}", "resolved" if e.get("resolved") else "not resolved", "H", f"|t| >= 4.303 and |gain| >= 1 %, {short}")
            R.add(f"h_base_{short}", _f(e["base_tps_mean"], 2), "H", f"TPS mean, nightly deb, {short}, mean of {n} passes")
            R.add(f"h_canon_{short}", _f(e["canon_tps_mean"], 2), "H", f"TPS mean, canonical-AMX deb, {short}, mean of {n} passes")
            R.add(f"h_min_{short}", f"{_f(e['base_min_tps'], 2)} / {_f(e['canon_min_tps'], 2)}", "H", f"slowest sample TPS over the passes, nightly / AMX, {short}")
            R.add(f"h_p05_{short}", f"{_f(e['base_p05_mean'], 2)} / {_f(e['canon_p05_mean'], 2)}", "H", f"p05 TPS (mean of the per-pass p05), nightly / AMX, {short}")
            R.add(f"h_ttft_{short}", f"{_f(e['base_ttft_ms_mean'], 0)} / {_f(e['canon_ttft_ms_mean'], 0)}", "H", f"TTFT ms, nightly / AMX, {short}")
            R.add(f"h_wall_{short}", _f((e.get("wall_s_mean") or 0) / 60, 1), "H", f"minutes per config (10 rounds), {short}, mean over the passes")
            R.add(f"h_n_{short}", str(n), "H", f"paired passes for {short}")
        else:
            for k in ("gain", "t", "res", "base", "canon", "min", "p05", "ttft", "wall", "n"):
                R.add(f"h_{k}_{short}", "n/a", "H", f"{short}: no paired pass")
    complete = [n for n, e in cfg.items() if e.get("n_pairs") == 3]
    resolved = [n for n, e in cfg.items() if e.get("resolved")]
    R.add("h_n_complete", str(len(complete)), "H", "configs with all 3 passes on both arms")
    R.add("h_n_resolved", str(len(resolved)), "H", "configs resolved by the pre-registered rule")
    R.add("h_configs", str(len(cfg)), "H", "configs per pass in the campaign as run (7168 and 8192 dropped)")
    R.add("h_passes", str(max((e.get("n_pairs", 0) for e in cfg.values()), default=0)), "H", "interleaved passes per arm")
    v = s["verdicts"]
    R.add("h_pair", "lost: the server truncates prompts above 4096 tokens, so the 2-users-per-engine prompt-7168 cell could not be measured", "H",
          "16K pair verdict (plan section 7); the prompt-7168 and prompt-8192 cells were dropped before the first pass")
    R.add("h_triple", v["triple_8k"]["verdict"], "H", "8K triple verdict text from analyze.py (plan section 7 rule)")
    R.add("h_triple_ok", str(v["triple_8k"].get("spread_1u_ok")), "H", "the 1-user cell had 10 requests per engine in every run (Caddy spread rule)")
    R.add("h_band2", "inside" if v["expected_2u_p1024"].get("inside") else ("outside" if v["expected_2u_p1024"].get("inside") is False else "n/a"), "H", "2 users x 1024 against the +0.2 to +1.2 % band")
    R.add("h_band8", "inside" if v["expected_8u_p1024_T1"].get("inside") else ("outside" if v["expected_8u_p1024_T1"].get("inside") is False else "n/a"), "H", "8 users x 1024 against the 9.9 to 15.9 % band")
    R.add("h_trunc", "4096", "H", "prompt tokens kept by the deployed llama-3.1-8b w4a16 tokenizer.json (truncation block, upstream revision of 2024-08-13, fixed upstream 2024-09-30)")
    R.add("h_trunc70", "8192", "H", "the same block in the llama-3.1-70b w4a16 tokenizer.json on the machine")
    R.add("h_date", "2026-09-19", "id", "date of the l8b-levers campaign (source H)")
    # the check cell
    chk = glob.glob(os.path.join(res, "check-32u-p8192", "perf.json"))
    if chk:
        d = json.load(open(chk[0]))
        raw = d["raw"][0] if d.get("raw") else {}
        t = raw.get("tpss") or []
        pt = raw.get("prompt_tokens") or []
        R.add("h_check_tps", _f(sum(t) / len(t), 2) if t else "n/a", "H", "TPS mean of the check cell, 32 users x prompt_length 8192, canonical deb")
        R.add("h_check_min", _f((raw.get("wall_seconds") or 0) / 60, 1), "H", "minutes of the check cell (10 rounds)")
        R.add("h_check_ttft", _f(sum(raw.get("ttfts_ms") or [0]) / max(1, len(raw.get("ttfts_ms") or [0])), 0), "H", "TTFT ms of the check cell")
        R.add("h_check_pt", f"{min(pt)} to {max(pt)}" if pt else "n/a", "H", "prompt tokens the server counted in the check cell (the harness sent 8192)")
    else:
        for k in ("tps", "min", "ttft", "pt"):
            R.add(f"h_check_{k}", "n/a", "H", "check cell record missing")
    return ovh


if __name__ == "__main__":
    class _R:
        def __init__(self):
            self.items = {}

        def add(self, k, text, tag, note=""):
            if k in self.items:
                raise KeyError(k)
            self.items[k] = (text, tag, note)
    r = _R()
    register(r)
    for k, (t, tag, note) in r.items.items():
        print(f"{k:16s} [{tag}] {t}")
