"""Source I for exec/canon-ci-20260918/gen_ci_shapes.py: the l8b-8u4k campaign of 2026-09-20 (llama-3.1-8b at 8 users
per engine = 32 users in total, prompt 4096, nightly deb against the canonical-AMX deb, 3 interleaved passes, same driver
and layout as the Saturday l8b-levers campaign; plan CI-test/status/llama-3.1-8b-8u-4k-plan.md, section 4 item 5 and
section 9).

register(R, res=RES) reads <res>/summary.json (written by exec/l8b-8u4k-20260920/analyze.py) and adds registry entries
with tag "I" so that every number the page shows from this campaign carries its source. RES defaults to
exec/results/l8b-8u4k-20260920; the environment variable I_RES overrides it (for a stand-in summary.json while the
campaign runs). Keys:
  i_gain (% gain), i_t (paired t), i_res (resolved / not resolved), i_base, i_canon (TPS mean, nightly / canonical-AMX deb),
  i_min (slowest sample TPS, nightly / AMX), i_p05 (TPS, nightly / AMX), i_ttft (ms, nightly / AMX), i_ttft_base, i_ttft_amx
  (the two halves as single values, for the audit), i_wall (min per cell),
  i_passes (paired passes), i_band_lo, i_band_hi (the pre-registered gain band, %), i_inside (inside / outside the band),
  i_reading (verdict text from analyze.py), i_diff2048 (points against the Saturday 8-users prompt-2048 gain),
  i_goal_tps, i_goal_min, i_goal_p05 (the clean arm's candidate goal values, TPS),
  i_kv (K KV tokens per engine step, derived here), i_date, i_stamp, i_report (identifiers).
Every value the summary does not carry (no summary.json yet, or no paired pass) becomes "n/a" so the page renders while
the campaign is still running.
"""
import json
import os

RES = os.environ.get("I_RES", "/home/jhan/workspace/intel-AMX/exec/results/l8b-8u4k-20260920")
CELL = "llama_3_1_8b_instruct_good_tp2_32u_p4096"
UPE, PROMPT, WINDOW_MID = 8, 4096, 960     # users per engine, prompt tokens the server keeps, middle of the TPS window
SHAPE = f"{UPE} users per engine x prompt {PROMPT}"


def _f(x, nd=1, sign=False):
    if x is None:
        return "n/a"
    return f"{x:+.{nd}f}" if sign else f"{x:.{nd}f}"


def _pair(a, b, nd):
    """'nightly / AMX' text; n/a when neither arm has a value."""
    if a is None and b is None:
        return "n/a"
    return f"{_f(a, nd)} / {_f(b, nd)}"


def register(R, res=RES):
    path = os.path.join(res, "summary.json")
    try:
        s = json.load(open(path))
    except (OSError, ValueError):
        s = {}
    e = (s.get("configs") or {}).get(CELL) or {}
    n = e.get("n_pairs") or 0
    over = f"mean over {n} passes" if n else "no paired pass yet"
    R.add("i_gain", _f(e.get("gain_pct"), 1, True), "I", f"% gain of the canonical-AMX deb over the nightly deb, {SHAPE}, {over}")
    t = e.get("paired_t")
    R.add("i_t", "inf" if t is not None and t == float("inf") else _f(t, 2), "I", f"paired t over {n} passes, {SHAPE}")
    R.add("i_res", ("resolved" if e.get("resolved") else "not resolved") if n else "n/a", "I", f"|t| >= {e.get('t_limit_95', 'n/a')} and |gain| >= 1 %, {SHAPE}")
    R.add("i_base", _f(e.get("base_tps_mean"), 2), "I", f"TPS mean, nightly deb, {SHAPE}, {over}")
    R.add("i_canon", _f(e.get("canon_tps_mean"), 2), "I", f"TPS mean, canonical-AMX deb, {SHAPE}, {over}")
    R.add("i_min", _pair(e.get("base_min_tps"), e.get("canon_min_tps"), 2), "I", f"slowest sample TPS over the passes, nightly / AMX, {SHAPE}")
    R.add("i_p05", _pair(e.get("base_p05_mean"), e.get("canon_p05_mean"), 2), "I", f"p05 TPS (mean of the per-pass p05), nightly / AMX, {SHAPE}")
    R.add("i_ttft", _pair(e.get("base_ttft_ms_mean"), e.get("canon_ttft_ms_mean"), 0), "I", f"TTFT ms, nightly / AMX, {SHAPE}")
    R.add("i_ttft_base", _f(e.get("base_ttft_ms_mean"), 0), "I", f"TTFT ms, nightly deb, {SHAPE}")
    R.add("i_ttft_amx", _f(e.get("canon_ttft_ms_mean"), 0), "I", f"TTFT ms, canonical-AMX deb, {SHAPE}")
    wall = e.get("wall_s_mean")
    R.add("i_wall", _f(wall / 60, 1) if wall else "n/a", "I", f"minutes per cell (10 rounds), {SHAPE}, mean over the passes and arms")
    R.add("i_passes", str(n) if s else "n/a", "I", f"paired interleaved passes, {SHAPE}")
    v = (s.get("verdicts") or {}).get("cell") or {}
    band = v.get("band_pct") or [None, None]
    R.add("i_band_lo", _f(band[0], 0, True), "I", "% lower edge of the pre-registered gain band (plan section 7), read from summary.json")
    R.add("i_band_hi", _f(band[1], 0, True), "I", "% upper edge of the pre-registered gain band (plan section 7), read from summary.json")
    inside = v.get("inside_band")
    R.add("i_inside", "inside" if inside else ("outside" if inside is False else "n/a"), "I", f"{SHAPE} gain against the pre-registered band")
    R.add("i_reading", v.get("reading") or "n/a", "I", "verdict text of analyze.py for the one cell (plan section 7 rule)")
    a2 = (s.get("verdicts") or {}).get("against_2048") or {}
    R.add("i_diff2048", _f(a2.get("diff_points"), 1, True), "I", "percentage points: the data I gain minus the Saturday 8-users prompt-2048 gain (analyze.py against_2048)")
    goals = v.get("candidate_goal_values_clean") or {}
    R.add("i_goal_tps", _f(goals.get("tps_mean"), 2), "I", f"TPS mean of the nightly deb, {SHAPE}: candidate goal value")
    R.add("i_goal_min", _f(goals.get("slowest_sample_tps"), 2), "I", f"slowest sample TPS of the nightly deb, {SHAPE}: candidate goal value")
    R.add("i_goal_p05", _f(goals.get("p05_tps_mean"), 2), "I", f"p05 TPS of the nightly deb (mean of the per-pass p05), {SHAPE}: candidate goal value")
    kv = UPE * (PROMPT + WINDOW_MID) / 1000
    R.add("i_kv", f"{kv:.1f}", "derived", f"K KV tokens per engine step of the data I cell: {UPE} x ({PROMPT} + {WINDOW_MID}) / 1000 = {kv:.3f} (the server keeps exactly {PROMPT} prompt tokens because of the tokenizer truncation, so no server overhead is added; {WINDOW_MID} = the middle of the TPS window)")
    R.add("i_date", "2026-09-20", "id", "date of the l8b-8u4k campaign (source I)")
    R.add("i_stamp", "20260920", "id", "date stamp in the results and scripts directory names of source I (exec/results/l8b-8u4k-20260920/, exec/l8b-8u4k-20260920/)")
    R.add("i_report", "CI-test/status/llama-3.1-8b-8u-4k.html", "id", "report page of data I")
    return s


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
        print(f"{k:12s} [{tag}] {t}")
