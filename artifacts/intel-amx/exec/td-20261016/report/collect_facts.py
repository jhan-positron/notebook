#!/usr/bin/env python3
"""Collect every number of the issue #4444 root-cause report into one place.

  python3 collect_facts.py            # writes facts.json and facts.md next to this script

Reads the result files of the td-20261016 campaign (and the earlier p83-20261013
record) and writes
  facts.json : nested dict; every leaf is {"value", "unit", "source"} where source
               is "<file path> :: <json field path | line N | regex>".
               A file that does not exist yet gives {"status": "pending", "source": path}.
  facts.md   : one section per source group (A..G); one table per source file.
Read-only on every input. Re-run when the campaign has produced more files.
"""
import csv
import glob
import json
import os
import re
import statistics
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
IA = "/home/jhan/workspace/intel-AMX"
EXEC = f"{IA}/exec"
RES_TD = f"{EXEC}/results/td-20261016"
RES_TD2 = f"{EXEC}/results/td2-20261016"
RES_TD3 = f"{EXEC}/results/td3-20261016"
RES_P83 = f"{EXEC}/results/p83-20261013"
TIE = f"{EXEC}/td-20261016/tiestats/tie_stats.json"
KTEST = f"{EXEC}/td-20261016/ktest/results.txt"
REPLAY_DIR = f"{EXEC}/td-20261016/replay"
LOGS = f"{EXEC}/logs"
PRED = f"{IA}/token-divergence-4444/predictions.md"
TREES = {"poc": "/home/jhan/workspace/ai-runs/tron-td-poc", "trunc": "/home/jhan/workspace/ai-runs/tron-td-trunc"}

LAYER_PAIRS = ["base-vs-poc", "base-vs-new", "new-vs-newoff", "newoff-vs-trunc", "new-vs-trunc",
               "baseoff-vs-base", "baseoff-vs-newoff", "baseoff-vs-pocoff", "clean-vs-baseoff", "clean-vs-new"]
STEP_PAIRS_TD = ["base-vs-poc", "baseoff-vs-pocoff", "clean-vs-baseoff", "base-vs-new", "new-vs-newoff",
                 "newoff-vs-trunc", "new-vs-trunc", "baseoff-vs-base", "baseoff-vs-newoff", "clean-vs-new"]
STEP_PAIRS_TD2 = ["base-vs-new", "new-vs-newoff", "base-vs-poc"]
TD3_ARMS = ["base63", "base64", "new63", "new64", "poc64"]
LABELS_A = ["WO", "Logits", "WQ", "WK", "WV"]
PAGE_END_TOKENS = [1087, 1151, 1215, 1279]

# ----------------------------------------------------------------------------- helpers


def leaf(value, unit, source):
  return {"value": value, "unit": unit, "source": source}


def pending(path, note=None):
  d = {"status": "pending", "source": path}
  if note:
    d["note"] = note
  return d


def is_pending(d):
  return isinstance(d, dict) and d.get("status") == "pending"


def load_json(path):
  with open(path) as f:
    return json.load(f)


def read_text(path):
  with open(path, errors="replace") as f:
    return f.read()


def fnum(s):
  """int if it looks like one, else float; 'None'/'null' -> None."""
  if s is None:
    return None
  s = s.strip()
  if s in ("None", "null", ""):
    return None
  if re.fullmatch(r"[-+]?\d+", s):
    return int(s)
  try:
    return float(s)
  except ValueError:
    return s


def median(xs):
  return float(statistics.median(xs)) if xs else None


# ----------------------------------------------------------------------------- A. per-layer records

UNIT_BY_FIELD = {"n_keys_compared": "count", "n_over_threshold": "count", "min_token_over": "token index",
                 "n_missing_in_off": "count", "n_missing_in_on": "count", "off_duplicate_keys": "count",
                 "rel_l2": "ratio (relative L2)", "frac_changed": "fraction", "max_ulps": "bf16 ulps",
                 "max_abs": "value units", "n": "count", "n_over": "count", "first_token_over": "token index",
                 "first_layer_over": "layer index", "max_rel": "ratio (relative L2)", "token": "token index",
                 "layer": "layer index", "len": "count"}


def wo_layer0_stats(rows, lo, hi, src):
  """rows: list of (token, rel_l2, frac_changed) for label WO layer 0; token range [lo, hi]."""
  sel = [(t, r, fc) for (t, r, fc) in rows if lo <= t <= hi]
  diff = [(t, r, fc) for (t, r, fc) in sel if not (r <= 0.0)]  # nan counts as differing (dd rule)
  finite = [(t, r, fc) for (t, r, fc) in diff if r == r and r != float("inf")]
  s = f"{src} :: rows label=WO,layer=0,token in [{lo},{hi}]"
  return {
    "tokens_present": leaf(len(sel), "count", s),
    "tokens_differing": leaf(len(diff), "count", s + ", rel_l2 > 0"),
    "first_5_differing_tokens": leaf([t for (t, _, _) in diff[:5]], "token index", s),
    "median_rel_l2_of_differing": leaf(median([r for (_, r, _) in finite]), "ratio (relative L2)", s),
    "max_rel_l2_of_differing": leaf(max((r for (_, r, _) in finite), default=None), "ratio (relative L2)", s),
    "median_frac_changed_of_differing": leaf(median([fc for (_, _, fc) in finite]), "fraction", s),
    "max_frac_changed_of_differing": leaf(max((fc for (_, _, fc) in finite), default=None), "fraction", s),
  }


def section_a():
  out = {}
  for pair in LAYER_PAIRS:
    jpath = f"{RES_TD}/layers-{pair}.json"
    cpath = f"{RES_TD}/layers-{pair}.csv"
    if not os.path.exists(jpath):
      out[pair] = pending(jpath)
      continue
    d = load_json(jpath)
    s = d["summary"]
    rec = {"summary": {}, "by_label": {}, "wo_layer0": {}}
    for k in ("n_keys_compared", "n_over_threshold", "min_token_over", "n_missing_in_off", "n_missing_in_on"):
      rec["summary"][k] = leaf(s.get(k), UNIT_BY_FIELD[k], f"{jpath} :: summary.{k}")
    fo = s.get("first_over")
    if fo:
      rec["summary"]["first_over"] = {k: leaf(fo[k], UNIT_BY_FIELD.get(k, "text"), f"{jpath} :: summary.first_over.{k}")
                                      for k in ("key", "token", "layer", "rel_l2", "frac_changed", "max_ulps")}
    else:
      rec["summary"]["first_over"] = leaf(None, "none (no record differs)", f"{jpath} :: summary.first_over")
    for lab in LABELS_A:
      b = d["by_label"].get(lab)
      if b is None:
        rec["by_label"][lab] = leaf(None, "label absent", f"{jpath} :: by_label.{lab}")
        continue
      rec["by_label"][lab] = {k: leaf(b.get(k), UNIT_BY_FIELD[k], f"{jpath} :: by_label.{lab}.{k}")
                              for k in ("n", "n_over", "first_token_over", "first_layer_over", "max_rel")}
    if not os.path.exists(cpath):
      rec["wo_layer0"] = pending(cpath)
      out[pair] = rec
      continue
    wo_l0 = []
    wo_all = []  # (token, layer, differs) for all WO rows
    with open(cpath, newline="") as f:
      rd = csv.DictReader(f)
      for r in rd:
        if r["label"] != "WO":
          continue
        tok = int(r["token"]) if r["token"] not in ("", "None") else None
        lay = int(r["layer"]) if r["layer"] not in ("", "None") else None
        rel = float(r["rel_l2"])
        differs = not (rel <= 0.0)
        wo_all.append((tok, lay, differs))
        if lay == 0 and tok is not None:
          wo_l0.append((tok, rel, float(r["frac_changed"])))
    wo_l0.sort()
    rec["wo_layer0"]["all_tokens_0_1278"] = wo_layer0_stats(wo_l0, 0, 1278, cpath)
    rec["wo_layer0"]["prompt_tokens_0_1023"] = wo_layer0_stats(wo_l0, 0, 1023, cpath)
    rec["wo_layer0"]["decode_tokens_1024_1278"] = wo_layer0_stats(wo_l0, 1024, 1278, cpath)
    rec["wo_layer0"]["prefill_pass2_tokens_128_191"] = wo_layer0_stats(wo_l0, 128, 191, cpath)
    pe = {}
    by_tok = {t: (r, fc) for (t, r, fc) in wo_l0}
    for t in PAGE_END_TOKENS:
      if t in by_tok:
        pe[f"token_{t}"] = {"rel_l2": leaf(by_tok[t][0], "ratio (relative L2)", f"{cpath} :: row label=WO,layer=0,token={t} rel_l2"),
                            "frac_changed": leaf(by_tok[t][1], "fraction", f"{cpath} :: row label=WO,layer=0,token={t} frac_changed")}
      else:
        pe[f"token_{t}"] = leaf(None, "token absent from the log (log holds tokens 0..1278)", f"{cpath} :: row label=WO,layer=0,token={t}")
    rec["wo_layer0"]["page_end_decode_tokens"] = pe
    if pair == "base-vs-new":
      diffs = sorted((t, l) for (t, l, dif) in wo_all if dif and t is not None)
      first = diffs[0] if diffs else (None, None)
      rec["wo_any_layer"] = {
        "first_token_any_layer_wo_differs": leaf(first[0], "token index", f"{cpath} :: min token over rows label=WO, rel_l2 > 0"),
        "layer_at_first_token": leaf(first[1], "layer index", f"{cpath} :: layer of that first row (lowest layer at that token)"),
        "layers_differing_at_first_token": leaf(sorted(l for (t, l) in diffs if t == first[0]), "layer index", f"{cpath} :: rows label=WO, token={first[0]}, rel_l2 > 0"),
        "wo_cells_differing_tokens_0_127": leaf(sum(1 for (t, l) in diffs if 0 <= t <= 127), "count of (token, layer) cells", f"{cpath} :: rows label=WO, token in [0,127], rel_l2 > 0"),
        "wo_cells_total_tokens_0_127": leaf(sum(1 for (t, l, _) in wo_all if t is not None and 0 <= t <= 127), "count of (token, layer) cells", f"{cpath} :: rows label=WO, token in [0,127]"),
        "tokens_0_127_with_any_wo_difference": leaf(len({t for (t, l) in diffs if 0 <= t <= 127}), "count of tokens", f"{cpath} :: distinct tokens in [0,127] with a WO row rel_l2 > 0"),
      }
    out[pair] = rec
  return out


# ----------------------------------------------------------------------------- B. per-step logits

STEP_SUMMARY_FIELDS = {
  "n_steps": "count", "n_with_logits": "count", "n_identical_steps": "count", "flip_steps": "step index (1-based)",
  "first_flip": "step index (1-based)", "nonflip_median_abs_delta_pair": "logit units", "nonflip_p95_abs_delta_pair": "logit units",
  "nonflip_median_mean_abs_delta": "logit units", "nonflip_p95_mean_abs_delta": "logit units",
  "nonflip_median_frac_changed": "fraction", "max_tvd": "TVD (0..1)", "max_max_abs_delta": "logit units",
  "median_margin_off": "logit units", "prompt_len": "tokens",
}
MARK_FIELDS = {
  "step": "step index (1-based)", "N": "token index of the Logits line", "forced_id": "token id", "off_top1": "token id",
  "off_top2": "token id", "on_top1": "token id", "on_top2": "token id", "same_top1": "bool", "margin_off": "logit units",
  "ulp_top1_off": "logit units (one bf16 ulp of the top-1 logit)", "margin_off_ulps": "bf16 ulps", "margin_on_same_pair": "logit units",
  "delta_top1": "logit units", "delta_top2": "logit units", "delta_pair": "logit units", "forced_rank_off": "rank (1 = top)",
  "forced_rank_on": "rank (1 = top)", "max_abs_delta": "logit units", "mean_abs_delta": "logit units", "frac_changed": "fraction",
  "argmax_abs_delta": "token id", "tvd": "TVD (0..1)", "off_top1_logit": "logit units", "on_top1_logit": "logit units",
  "off_sparse_top1": "token id", "on_sparse_top1": "token id",
}


def steps_record(path):
  if not os.path.exists(path):
    return pending(path)
  d = load_json(path)
  s = d["summary"]
  rec = {"summary": {k: leaf(s.get(k), u, f"{path} :: summary.{k}") for k, u in STEP_SUMMARY_FIELDS.items() if k in s}}
  m = s.get("marked_step")
  if m:
    rec["marked_step"] = {k: leaf(m.get(k), u, f"{path} :: summary.marked_step.{k}") for k, u in MARK_FIELDS.items() if k in m}
  else:
    rec["marked_step"] = leaf(None, "marked step absent", f"{path} :: summary.marked_step")
  return rec


def section_b():
  out = {"td-20261016": {}, "p83-20261013": {}}
  for pair in STEP_PAIRS_TD:
    out["td-20261016"][pair] = steps_record(f"{RES_TD}/steps-{pair}.json")
  vpath = f"{RES_TD}/verdict.txt"
  out["td-20261016"]["verdict_txt"] = leaf(read_text(vpath), "text", vpath) if os.path.exists(vpath) else pending(vpath)
  for p in sorted(glob.glob(f"{RES_P83}/steps-*.json")):
    name = os.path.basename(p)[len("steps-"):-len(".json")]
    out["p83-20261013"][name] = steps_record(p)
  if not out["p83-20261013"]:
    out["p83-20261013"] = pending(f"{RES_P83}/steps-*.json")
  return out


# ----------------------------------------------------------------------------- C. near-tie statistics


def section_c():
  if not os.path.exists(TIE):
    return pending(TIE)
  d = load_json(TIE)
  out = {"pairs": {}, "prediction": {}, "pools": {}, "totals": {}}
  for pair, p in d["pairs"].items():
    S = f"{TIE} :: pairs.{pair}"
    r = {
      "file": leaf(p.get("file"), "path of the steps json", f"{S}.file"),
      "arms": leaf(f"OFF = {p.get('off_arm')}; ON = {p.get('on_arm')}; {p.get('note')}", "text", f"{S}.off_arm/on_arm/note"),
      "n_steps": leaf(p["n_steps"], "count", f"{S}.n_steps"),
      "observed_flips": leaf(p["observed_flips"], "step index (1-based)", f"{S}.observed_flips"),
      "margin_logit": {k: leaf(p["margin_logit"][k], "logit units", f"{S}.margin_logit.{k}") for k in ("median", "p10", "p05", "min")},
      "margin_ulps": {k: leaf(p["margin_ulps"][k], "bf16 ulps", f"{S}.margin_ulps.{k}") for k in ("median", "p10", "p05", "min")},
      "margin_counts": {k: leaf(p["margin_counts"][k], "steps", f"{S}.margin_counts.{k}") for k in ("eq_0", "le_1ulp", "le_2ulp", "le_4ulp")},
      "abs_delta_pair_logit": {k: leaf(p["abs_delta_pair_logit"][k], "logit units", f"{S}.abs_delta_pair_logit.{k}") for k in ("median", "p95", "max")},
      "abs_delta_pair_ulps": {k: leaf(p["abs_delta_pair_ulps"][k], "bf16 ulps", f"{S}.abs_delta_pair_ulps.{k}") for k in ("median", "p95", "max")},
      "delta_pair_signed_counts": {k: leaf(p["delta_pair_signed_counts"][k], "steps", f"{S}.delta_pair_signed_counts.{k}") for k in ("neg", "zero", "pos")},
      "model_flips": leaf(p["model_flips"], "step index (1-based)", f"{S}.model_flips"),
      "model_reproduces_observed": leaf(p["model_reproduces_observed"], "bool", f"{S}.model_reproduces_observed"),
      "at_risk": {k: leaf(p["at_risk"][k], ("steps" if k.startswith("steps_") else ("bf16 ulps" if k.endswith("_ulps") else "logit units")), f"{S}.at_risk.{k}")
                  for k in p["at_risk"]},
      "flip_steps": {},
    }
    for fd in p.get("flip_steps_detail", []):
      st = fd["step"]
      r["flip_steps"][f"step_{st}"] = {
        "margin_logit": leaf(fd["margin_logit"], "logit units", f"{S}.flip_steps_detail[step={st}].margin_logit"),
        "margin_ulps": leaf(fd["margin_ulps"], "bf16 ulps", f"{S}.flip_steps_detail[step={st}].margin_ulps"),
        "delta_pair_logit": leaf(fd["delta_pair"], "logit units", f"{S}.flip_steps_detail[step={st}].delta_pair"),
        "delta_pair_ulps": leaf(fd["delta_pair_ulps"], "bf16 ulps", f"{S}.flip_steps_detail[step={st}].delta_pair_ulps"),
        "rank_by_margin_logit": leaf(fd["rank_logit_1_is_smallest"], "rank of 256 (1 = smallest margin)", f"{S}.flip_steps_detail[step={st}].rank_logit_1_is_smallest"),
        "rank_by_margin_ulps": leaf(fd["rank_ulps_1_is_smallest"], "rank of 256 (1 = smallest margin)", f"{S}.flip_steps_detail[step={st}].rank_ulps_1_is_smallest"),
        "off_top1_id": leaf(fd["off_top1"], "token id", f"{S}.flip_steps_detail[step={st}].off_top1"),
        "off_top2_id": leaf(fd["off_top2"], "token id", f"{S}.flip_steps_detail[step={st}].off_top2"),
        "on_top1_id": leaf(fd["on_top1"], "token id", f"{S}.flip_steps_detail[step={st}].on_top1"),
      }
    out["pairs"][pair] = r
  for pair, p in d["prediction"].items():
    S = f"{TIE} :: prediction.{pair}"
    r = {"observed": leaf(p["observed"], "flips", f"{S}.observed"), "n_steps": leaf(p["n_steps"], "count", f"{S}.n_steps")}
    for form in ("own_logit", "own_ulps", "pooled_p83_logit", "pooled_p83_ulps", "pooled_all_logit", "pooled_all_ulps"):
      q = p[form]
      r[form] = {
        "pool_size": leaf(q["pool_size"], "delta_pair samples", f"{S}.{form}.pool_size"),
        "expected_flips": leaf(q["expected_flips"], "flips per 256 steps", f"{S}.{form}.expected_flips"),
        "p_at_least_one": leaf(q["p_at_least_one"], "probability", f"{S}.{form}.p_at_least_one"),
        "p_ge_observed": leaf(q["p_ge_observed"], "probability", f"{S}.{form}.p_ge_observed"),
        "steps_with_nonzero_p": leaf(q["steps_with_nonzero_p"], "steps", f"{S}.{form}.steps_with_nonzero_p"),
        "top_step_by_p": leaf(q["top5_steps_by_p"][0] if q["top5_steps_by_p"] else None, "{step, p, margin}", f"{S}.{form}.top5_steps_by_p[0]"),
      }
    out["prediction"][pair] = r
  for pool, p in d["pools"].items():
    S = f"{TIE} :: pools.{pool}"
    out["pools"][pool] = {
      "members": leaf(p["members"], "pair names", f"{S}.members"), "n": leaf(p["n"], "delta_pair samples", f"{S}.n"),
      "abs_delta_pair_logit": {k: leaf(p["abs_delta_pair_logit"][k], "logit units", f"{S}.abs_delta_pair_logit.{k}") for k in ("median", "p95", "max")},
      "abs_delta_pair_ulps": {k: leaf(p["abs_delta_pair_ulps"][k], "bf16 ulps", f"{S}.abs_delta_pair_ulps.{k}") for k in ("median", "p95", "max")},
    }
  t = d["totals"]
  for k, v in t.items():
    out["totals"][k] = leaf(v, "pair names" if k == "pairs" else ("steps" if k == "steps_total" else "flips"), f"{TIE} :: totals.{k}")
  return out


# ----------------------------------------------------------------------------- D. kernel tests

CMP_RE = re.compile(r"identical=(yes|no) n=(\d+) diff=(\d+) \(([\d.]+)%\)(?: max_abs=(\S+) mean_abs=(\S+) max_rel=(\S+) max_fp32ulps=(\S+) max_bf16ulps=(\S+))?")


def parse_cmp(line, src):
  m = CMP_RE.search(line)
  if not m:
    return leaf(line.strip(), "unparsed line", src)
  r = {"identical": leaf(m.group(1) == "yes", "bool", src), "n": leaf(int(m.group(2)), "scores or elements compared", src),
       "diff_count": leaf(int(m.group(3)), "count", src), "diff_percent": leaf(float(m.group(4)), "%", src)}
  if m.group(5):
    r.update({"max_abs": leaf(float(m.group(5)), "value units", src), "mean_abs": leaf(float(m.group(6)), "value units", src),
              "max_rel": leaf(float(m.group(7)), "ratio", src), "max_fp32ulps": leaf(float(m.group(8)), "fp32 ulps", src),
              "max_bf16ulps": leaf(float(m.group(9)), "bf16 ulps", src)})
  return r


def parse_ref(line, src):
  """T7/T8 'o_xxx vs fp64' line."""
  m = re.search(r"n=(\d+) incl=(\d+) exact_match=(\d+) mean_signed_rel\(bias\)=(\S+) mass_weighted_bias=(\S+) rms_rel=(\S+) max_rel=(\S+)", line)
  if not m:
    return leaf(line.strip(), "unparsed line", src)
  return {"n": leaf(int(m.group(1)), "elements", src), "included": leaf(int(m.group(2)), "elements (|exact| above the floor)", src),
          "exact_match": leaf(int(m.group(3)), "elements", src), "mean_signed_rel_bias": leaf(float(m.group(4)), "ratio", src),
          "mass_weighted_bias": leaf(float(m.group(5)), "ratio", src), "rms_rel": leaf(float(m.group(6)), "ratio", src),
          "max_rel": leaf(float(m.group(7)), "ratio", src)}


def section_d():
  if not os.path.exists(KTEST):
    return pending(KTEST)
  lines = read_text(KTEST).splitlines()
  L = {i + 1: ln for i, ln in enumerate(lines)}

  def find(prefix, contains=None, nth=0):
    hits = [(i, ln) for i, ln in L.items() if ln.startswith(prefix) and (contains is None or contains in ln)]
    return hits[nth] if len(hits) > nth else (None, None)

  out = {}
  for i, ln in L.items():
    if ln.startswith("seed="):
      m = re.search(r"seed=(\d+) qk_instances=(\d+) pv_instances=(\d+)", ln)
      if m:
        out["setup"] = {"seed": leaf(int(m.group(1)), "seed", f"{KTEST} :: line {i}"), "qk_instances": leaf(int(m.group(2)), "count", f"{KTEST} :: line {i}"),
                        "pv_instances": leaf(int(m.group(3)), "count", f"{KTEST} :: line {i}")}
      break
  # T0: lane semantics, two MXCSR settings
  out["T0_lane_semantics"] = {}
  for i, ln in L.items():
    if ln.startswith("T0 "):
      m = re.search(r"\((MXCSR [^)]*)\) n=(\d+): s1:\(acc\+pe\)\+po=(\d+)\(([\d.]+)%\) s2:\(acc\+po\)\+pe=(\d+)\(([\d.]+)%\) s3:acc\+\(pe\+po\)=(\d+)\(([\d.]+)%\) sg:round1\(acc\+pe\+po\)=(\d+)\(([\d.]+)%\)", ln)
      if m:
        src = f"{KTEST} :: line {i}"
        out["T0_lane_semantics"][m.group(1).replace(" ", "_").replace("/", "_").replace("=", "")] = {
          "n": leaf(int(m.group(2)), "cases", src),
          "s1_(acc+pe)+po_match": leaf(int(m.group(3)), "cases", src), "s1_percent": leaf(float(m.group(4)), "%", src),
          "s2_(acc+po)+pe_match": leaf(int(m.group(5)), "cases", src), "s2_percent": leaf(float(m.group(6)), "%", src),
          "s3_acc+(pe+po)_match": leaf(int(m.group(7)), "cases", src), "s3_percent": leaf(float(m.group(8)), "%", src),
          "sg_round1_match": leaf(int(m.group(9)), "cases", src), "sg_percent": leaf(float(m.group(10)), "%", src)}
  for key, prefix in (("T1_amx_qk_vs_vnni_reader", "T1 "), ("T1b_rowmajor_amx_vs_vnni_amx", "T1b "), ("T2_avx_dotter_vs_amx_qk", "T2 "),
                      ("T6a_amx_pv_vs_avx_pv_bf16_exact_P", "T6a "), ("T6b_amx_pv_rne_vs_avx_pv_truncated_P", "T6b "),
                      ("T6c_amx_pv_vs_avx_pv_fed_rne_P", "T6c "), ("T9a_avx512_amx_order_qk_vs_amx_qk", "T9a "),
                      ("T9b_avx512_amx_order_pv_vs_amx_pv", "T9b ")):
    i, ln = find(prefix)
    out[key] = parse_cmp(ln, f"{KTEST} :: line {i}") if ln else pending(KTEST, f"line '{prefix}' absent")
  # T3 / T4 bit-identical lines
  for key, prefix in (("T3_dotter_bit_identical_model", "T3 "), ("T4_vnni_reader_bit_identical_model", "T4 ")):
    i, ln = find(prefix, contains="bit-identical")
    if ln:
      m = re.search(r"T\d\s+(.*?) match=(\d+) \(([\d.]+)%\)", ln)
      out[key] = {"model": leaf(m.group(1).strip(), "text", f"{KTEST} :: line {i}"), "match": leaf(int(m.group(2)), "scores", f"{KTEST} :: line {i}"),
                  "match_percent": leaf(float(m.group(3)), "%", f"{KTEST} :: line {i}")}
    else:
      out[key] = pending(KTEST, f"'{prefix}' bit-identical line absent")
  i, ln = find("T5 best candidate")
  if ln:
    out["T5_best_simple_candidate"] = leaf(ln.split(":", 1)[1].strip(), "model name", f"{KTEST} :: line {i}")
  i, ln = find("T5 residual")
  if ln:
    out["T5_residual_best_simple_candidate_vs_hardware"] = parse_cmp(ln, f"{KTEST} :: line {i}")
  for key, contains in (("T5m_amx_qk_vs_even_odd_chain_model_identical", "identical=yes"),):
    i, ln = find("T5m ", contains=contains)
    if ln:
      r = parse_cmp(ln, f"{KTEST} :: line {i}")
      m = re.search(r"combine=([^:]+):", ln)
      r["combine"] = leaf(m.group(1) if m else None, "model name", f"{KTEST} :: line {i}")
      out[key] = r
    else:
      out[key] = pending(KTEST, "T5m identical=yes line absent")
  i, ln = find("T6d ", contains="identical=yes")
  if ln:
    r = parse_cmp(ln, f"{KTEST} :: line {i}")
    m = re.search(r"combine=([^:]+):", ln)
    r["combine"] = leaf(m.group(1) if m else None, "model name", f"{KTEST} :: line {i}")
    out["T6d_amx_pv_vs_even_odd_chain_model_identical"] = r
  # T7a/b, T8a/b
  for tag in ("T7a", "T7b", "T8a", "T8b"):
    i0, hdr = find(tag + " tokens=")
    if not hdr:
      out[tag] = pending(KTEST, f"{tag} header absent")
      continue
    m = re.search(r"tokens=(\d+) V~(\S+) instances=(\d+)", hdr)
    r = {"tokens": leaf(int(m.group(1)), "attended tokens", f"{KTEST} :: line {i0}"), "V_distribution": leaf(m.group(2), "text", f"{KTEST} :: line {i0}"),
         "instances": leaf(int(m.group(3)), "count", f"{KTEST} :: line {i0}")}
    i, ln = find(tag + " o_trunc")
    r["o_trunc_avx_path_vs_fp64"] = parse_ref(ln, f"{KTEST} :: line {i}")
    i, ln = find(tag + " o_rne")
    r["o_rne_amx_kernel_vs_fp64"] = parse_ref(ln, f"{KTEST} :: line {i}")
    i, ln = find(tag + " rms_ratio")
    m = re.search(r"rms_ratio trunc/rne=([\d.]+)", ln or "")
    r["rms_ratio_trunc_over_rne"] = leaf(float(m.group(1)) if m else None, "ratio", f"{KTEST} :: line {i}")
    i, ln = find(tag + " weight-mass")
    m = re.search(r"sum\(bf16_trunc\(P\)\)/sum\(P\)-1=(\S+)\s+sum\(bf16_rne\(P\)\)/sum\(P\)-1=(\S+) \(mean over (\d+) rows\)", ln or "")
    if m:
      r["weight_mass_ratio_minus1_trunc"] = leaf(float(m.group(1)), "ratio", f"{KTEST} :: line {i}")
      r["weight_mass_ratio_minus1_rne"] = leaf(float(m.group(2)), "ratio", f"{KTEST} :: line {i}")
      r["weight_mass_rows"] = leaf(int(m.group(3)), "rows (instances x heads)", f"{KTEST} :: line {i}")
    out[tag] = r
  # T9c timings
  t9 = {}
  for i, ln in L.items():
    if ln.startswith("T9c   "):
      m = re.search(r"T9c\s+(QK|PV)\s+(.*?)\s{2,}([\d.]+) ns(?:\s+\(kernel only ([\d.]+) ns\))?(?:\s+ratio vs \S+(?: \S+)? ([\d.]+)x)?", ln)
      if not m:
        continue
      name = m.group(2).strip()
      key = re.sub(r"[^A-Za-z0-9]+", "_", f"{m.group(1)}_{name}").strip("_")
      ent = {"description": leaf(name, "text", f"{KTEST} :: line {i}"), "ns_per_call": leaf(float(m.group(3)), "ns per (query group of 4 heads, 64-token page)", f"{KTEST} :: line {i}")}
      if m.group(4):
        ent["kernel_only_ns"] = leaf(float(m.group(4)), "ns", f"{KTEST} :: line {i}")
      if m.group(5):
        ent["ratio_vs_current"] = leaf(float(m.group(5)), "ratio (x)", f"{KTEST} :: line {i}")
      t9[key] = ent
    elif ln.startswith("T9c cost per") or ln.startswith("T9c timing cpu"):
      t9.setdefault("conditions", {})[f"line_{i}"] = leaf(ln[4:].strip(), "text", f"{KTEST} :: line {i}")
  out["T9c_timings"] = t9 if t9 else pending(KTEST, "T9c lines absent")
  i, ln = find("done in")
  if ln:
    m = re.search(r"done in ([\d.]+) s", ln)
    out["total_wall"] = leaf(float(m.group(1)) if m else None, "s", f"{KTEST} :: line {i}")
  return out


# ----------------------------------------------------------------------------- E. offline replay

CLASSES = ["all", "pass0_0-127", "pass1_128-191", "decode"]


def section_e():
  rpath = f"{REPLAY_DIR}/results.json"
  out = {}
  if not os.path.exists(rpath):
    out["results"] = pending(rpath)
  else:
    d = load_json(rpath)
    P = d["params"]
    out["params"] = {
      "layer": leaf(P["layer"], "layer index", f"{rpath} :: params.layer"),
      "amx_model": leaf(P["amx_model"], "model name", f"{rpath} :: params.amx_model"),
      "within_pair_order": leaf(P["within_pair_order"], "text", f"{rpath} :: params.within_pair_order"),
      "n_sampled_tokens": leaf(len(P["tokens"]), "tokens", f"{rpath} :: len(params.tokens)"),
      "decode_tokens_sampled": leaf([t for t in P["tokens"] if t >= 1024], "token index", f"{rpath} :: params.tokens (>= 1024)"),
      "n_tokens_logged": leaf(P["n_tokens_logged"], "tokens", f"{rpath} :: params.n_tokens_logged"),
      "values_not_decimal_exact": leaf(P["values_not_decimal_exact"], "values", f"{rpath} :: params.values_not_decimal_exact"),
      "values_total": leaf(P["values_total"], "values", f"{rpath} :: params.values_total"),
      "wall_s": leaf(P.get("wall_s"), "s", f"{rpath} :: params.wall_s"),
    }
    out["qkv_identity_vs_base"] = {arm: {t: leaf(v[t]["values_differ"], f"values differing of {v[t]['tokens_compared']} tokens", f"{rpath} :: qkv_identity.{arm}.{t}.values_differ")
                                         for t in ("Q", "K", "V")} for arm, v in d["qkv_identity"].items()}
    m1 = {}
    for pair, v in d["M1"].items():
      if pair == "within_pair_order_sensitivity":
        m1[pair] = {order: {path: leaf(cnt, f"scores changed of {vv['n']}", f"{rpath} :: M1.within_pair_order_sensitivity.{order}.{path}")
                            for path, cnt in vv.items() if path != "n"} for order, vv in v.items()}
        continue
      m1[pair] = {}
      for cls in CLASSES:
        c = v[cls]
        S = f"{rpath} :: M1.{pair}.{cls}"
        m1[pair][cls] = {
          "tokens": leaf(c["tokens"], "tokens", f"{S}.tokens"), "scores": leaf(c["scores"], "scores", f"{S}.scores"),
          "frac_differ_pooled": leaf(c["frac_differ_pooled"], "fraction", f"{S}.frac_differ_pooled"),
          "median_rel_of_differing": leaf(c["median_over_tokens_of_median_rel_of_differing"], "ratio", f"{S}.median_over_tokens_of_median_rel_of_differing"),
          "median_ulp_of_differing": leaf(c["median_over_tokens_of_median_ulp_of_differing"], "fp32 ulps", f"{S}.median_over_tokens_of_median_ulp_of_differing"),
          "max_rel": leaf(c["max_rel"], "ratio", f"{S}.max_rel"), "max_ulp": leaf(c["max_ulp"], "fp32 ulps", f"{S}.max_ulp"),
        }
    out["M1_scores"] = m1
    m2 = {}
    pt = d["per_token"]
    for pair, v in d["M2"].items():
      if pair == "amx_model_seq":
        m2[pair] = {}
        for p2, vv in v.items():
          m2[pair][p2] = {cls: leaf(vv[cls]["frac_bf16_differ_pooled"], "fraction", f"{rpath} :: M2.amx_model_seq.{p2}.{cls}.frac_bf16_differ_pooled") for cls in CLASSES}
        continue
      m2[pair] = {}
      for cls in CLASSES:
        c = v[cls]
        S = f"{rpath} :: M2.{pair}.{cls}"
        m2[pair][cls] = {
          "tokens": leaf(c["tokens"], "tokens", f"{S}.tokens"), "elements": leaf(c["elements"], "bf16 elements", f"{S}.elements"),
          "frac_bf16_differ_pooled": leaf(c["frac_bf16_differ_pooled"], "fraction", f"{S}.frac_bf16_differ_pooled"),
          "median_over_tokens_frac_bf16_differ": leaf(c["median_over_tokens_frac_bf16_differ"], "fraction", f"{S}.median_over_tokens_frac_bf16_differ"),
          "max_frac_bf16_differ": leaf(c["max_frac_bf16_differ"], "fraction", f"{S}.max_frac_bf16_differ"),
          "median_rel32": leaf(c["median_over_tokens_median_rel32"], "ratio (fp32 output)", f"{S}.median_over_tokens_median_rel32"),
          "max_abs32_over_rms": leaf(c["max_abs32_over_rms"], "ratio (max |diff| / rms of output)", f"{S}.max_abs32_over_rms"),
        }
      toks_any = sorted(int(t) for t, r in pt.items() if r["M2"].get(pair, {}).get("n_bf16_differ", 0) > 0)
      toks_one = sorted(int(t) for t, r in pt.items() if r["M2"].get(pair, {}).get("n_bf16_differ", 0) == 1)
      m2[pair]["tokens_with_any_bf16_difference"] = leaf(len(toks_any), f"tokens of {len(pt)}", f"{rpath} :: per_token.*.M2.{pair}.n_bf16_differ > 0")
      m2[pair]["tokens_with_exactly_one_element"] = leaf(len(toks_one), "tokens", f"{rpath} :: per_token.*.M2.{pair}.n_bf16_differ == 1")
      m2[pair]["first_token_with_difference"] = leaf(toks_any[0] if toks_any else None, "token index", f"{rpath} :: min per_token.*.M2.{pair}.n_bf16_differ > 0")
      t1087 = pt.get("1087", {}).get("M2", {}).get(pair)
      if t1087:
        m2[pair]["token_1087_frac_bf16_differ"] = leaf(t1087["frac_bf16_differ"], "fraction", f"{rpath} :: per_token.1087.M2.{pair}.frac_bf16_differ")
    out["M2_attention_output"] = m2
    m3 = {"fp32_output": {}, "bf16_output": {}, "weight_mass": {}, "bias_vs_attended": {}}
    for kind in ("fp32_output", "bf16_output"):
      for model, v in d["M3"][kind].items():
        m3[kind][model] = {}
        for cls in CLASSES:
          c = v[cls]
          S = f"{rpath} :: M3.{kind}.{model}.{cls}"
          m3[kind][model][cls] = {
            "mean_mass_bias": leaf(c["mean_mass_bias"], "ratio (mass-weighted bias)", f"{S}.mean_mass_bias"),
            "min_mass_bias": leaf(c["min_mass_bias"], "ratio", f"{S}.min_mass_bias"), "max_mass_bias": leaf(c["max_mass_bias"], "ratio", f"{S}.max_mass_bias"),
            "rms_rel_l2": leaf(c["rms_rel_l2"], "ratio (relative L2)", f"{S}.rms_rel_l2"), "median_rel_l2": leaf(c["median_rel_l2"], "ratio (relative L2)", f"{S}.median_rel_l2"),
          }
    for cls in CLASSES:
      c = d["M3"]["weight_mass"][cls]
      S = f"{rpath} :: M3.weight_mass.{cls}"
      m3["weight_mass"][cls] = {k: leaf(c[k], "ratio (sum(bf16(P))/sum(P) - 1)" if k != "tokens" else "tokens", f"{S}.{k}") for k in c}
    for e in d["M3"]["bias_vs_attended"]:
      tk = e["token"]
      S = f"{rpath} :: M3.bias_vs_attended[token={tk}]"
      m3["bias_vs_attended"][f"token_{tk}"] = {k: leaf(v, "attended tokens" if k == "attended" else "ratio", f"{S}.{k}") for k, v in e.items() if k != "token"}
    out["M3_vs_exact"] = m3
    out["M4_token0"] = {k: leaf(v, "bool", f"{rpath} :: M4.{k}") for k, v in d["M4"].items()}
  apath = f"{REPLAY_DIR}/arms_wo-L0.json"
  if not os.path.exists(apath):
    out["M4_logged_wo"] = pending(apath)
  else:
    a = load_json(apath)
    r = {"arms": leaf(a["arms"], "arm names", f"{apath} :: arms"), "pairs": {}, "set_overlap": {}}
    for pair, v in a["pairs"].items():
      r["pairs"][pair] = {}
      for cls, c in v.items():
        S = f"{apath} :: pairs.{pair}.{cls}"
        r["pairs"][pair][cls] = {
          "tokens": leaf(c["tokens"], "tokens", f"{S}.tokens"),
          "tokens_with_any_WO_difference": leaf(c["tokens_with_any_WO_difference"], "tokens", f"{S}.tokens_with_any_WO_difference"),
          "first_differing_token": leaf(c["first_differing_token"], "token index", f"{S}.first_differing_token"),
          "median_frac_elements_differing_when_differing": leaf(c["median_frac_elements_differing_when_differing"], "fraction", f"{S}.median_frac_elements_differing_when_differing"),
          "median_rel_l2_when_differing": leaf(c["median_rel_l2_when_differing"], "ratio (relative L2)", f"{S}.median_rel_l2_when_differing"),
          "max_rel_l2": leaf(c["max_rel_l2"], "ratio (relative L2)", f"{S}.max_rel_l2"),
        }
    for pair, v in a.get("set_overlap", {}).items():
      S = f"{apath} :: set_overlap.{pair}"
      r["set_overlap"][pair] = {k: leaf(v[k], "token index" if k.startswith("first_") else "tokens", f"{S}.{k}")
                                for k in v if k not in ("logged_differing", "predicted_differing")}
    out["M4_logged_wo"] = r
  wc = {}
  for wpath in sorted(glob.glob(f"{REPLAY_DIR}/wo_check-*-L0.json")):
    w = load_json(wpath)
    name = os.path.basename(wpath)[len("wo_check-"):-len("-L0.json")]
    wc[name] = {"model": leaf(w.get("model"), "replay model", f"{wpath} :: model"), "tokens": {}}
    for tk, v in w["tokens"].items():
      S = f"{wpath} :: tokens.{tk}"
      wc[name]["tokens"][f"token_{tk}"] = {
        "replay_bf16_rel_l2": leaf(v["replay_bf16"]["rel_l2"], "ratio (relative L2 vs logged WO)", f"{S}.replay_bf16.rel_l2"),
        "exact_fp64_rel_l2": leaf(v["exact_fp64"]["rel_l2"], "ratio (relative L2 vs logged WO)", f"{S}.exact_fp64.rel_l2"),
        "wrong_head_order_rel_l2": leaf(v["wrong_head_order"]["rel_l2"], "ratio (control)", f"{S}.wrong_head_order.rel_l2"),
        "replay_bf16_frac_bf16_equal": leaf(v["replay_bf16"]["frac_bf16_equal"], "fraction", f"{S}.replay_bf16.frac_bf16_equal"),
      }
  out["M4_wo_check"] = wc if wc else pending(f"{REPLAY_DIR}/wo_check-*-L0.json")
  return out


# ----------------------------------------------------------------------------- F. campaign record

RUN_HDR = re.compile(r"^### (\S+) bin=(\S+) env=\[([^\]]*)\]( attn=\S+)?( prompt=\S+)?( tokens=\S+)? forced=(\S+) (\S+) (.*)$")
RUN_RES = re.compile(r"^run (\S+) (reused:|rc=(\d+)) ?(?:wall=(\d+)s)? ?(?:tokens=(\d*))? ?(?:logits-lines=(\d*))? ?(?:stats-lines=(\d*))? ?(?:full=(\d+)|bytes=(\d+))?(.*)$")


def parse_runs(path):
  if not os.path.exists(path):
    return pending(path)
  out = {}
  for i, ln in enumerate(read_text(path).splitlines(), 1):
    m = RUN_HDR.match(ln)
    if m:
      name = m.group(1)
      out[name] = {"binary": leaf(m.group(2), "path on delphi-3bda", f"{path} :: line {i}"), "env": leaf(m.group(3), "text", f"{path} :: line {i}"),
                   "forced_file": leaf(m.group(7), "path", f"{path} :: line {i}"), "started_utc": leaf(m.group(8), "ISO time", f"{path} :: line {i}"),
                   "machine_line": leaf(m.group(9), "text", f"{path} :: line {i}")}
      if m.group(5):
        out[name]["prompt"] = leaf(fnum(m.group(5).split("=")[1]), "tokens", f"{path} :: line {i}")
      if m.group(6):
        out[name]["generated_tokens_requested"] = leaf(fnum(m.group(6).split("=")[1]), "tokens", f"{path} :: line {i}")
      continue
    m = RUN_RES.match(ln)
    if m:
      name = m.group(1)
      r = out.setdefault(name, {})
      S = f"{path} :: line {i}"
      if m.group(2) == "reused:":
        r["reused"] = leaf(True, "bool", S)
      else:
        r["rc"] = leaf(int(m.group(3)), "exit code", S)
      if m.group(4):
        r["wall"] = leaf(int(m.group(4)), "s", S)
      if m.group(5):
        r["tokens"] = leaf(int(m.group(5)), "tokens generated", S)
      if m.group(6):
        r["logits_lines"] = leaf(int(m.group(6)), "lines", S)
      if m.group(7):
        r["stats_lines"] = leaf(int(m.group(7)), "lines", S)
      if m.group(8) or m.group(9):
        r["full_bytes" if m.group(8) else "log_bytes"] = leaf(int(m.group(8) or m.group(9)), "bytes", S)
      mv = re.search(r"Version: (\S+) hash: ([0-9a-f]+)", ln)
      if mv:
        r["version"] = leaf(mv.group(1), "tron version string", S)
        r["hash"] = leaf(mv.group(2), "git commit", S)
      continue
    if ln.startswith("RUN-STOPPED"):
      out.setdefault("_notes", {})[f"line_{i}"] = leaf(ln, "text", f"{path} :: line {i}")
  return out


def parse_tokens_txt(path):
  if not os.path.exists(path):
    return pending(path)
  out = {}
  for i, ln in enumerate(read_text(path).splitlines(), 1):
    m = re.match(r"^(\S+) vs (\S+): (.*)$", ln)
    if m:
      out[m.group(1)] = leaf(m.group(3), f"token check vs {m.group(2)}", f"{path} :: line {i}")
    elif ln.startswith("#"):
      out["_header"] = leaf(ln, "text", f"{path} :: line {i}")
  return out


def text_or_pending(path):
  return leaf(read_text(path).strip(), "text", path) if os.path.exists(path) else pending(path)


def parse_stats(path):
  if not os.path.exists(path):
    return pending(path)
  t = read_text(path)
  m = re.search(r"\[attn-stats\] (decode_like\S*) k_tokens per layer \(amx/avx/fpga\): (.*)", t)
  if not m:
    return pending(path, "file exists but has no decode_like k_tokens line yet")
  layers = {}
  for tok in m.group(2).split():
    l, v = tok.split("=", 1)
    a, b, c = (int(x) for x in v.split("/"))
    layers[int(l)] = (a, b, c)
  return {"line_label": leaf(m.group(1), "attn-stats bucket", f"{path} :: regex 'decode_like... k_tokens per layer'"),
          "n_layers": leaf(len(layers), "layers", path),
          "k_tokens_per_layer_amx_avx_fpga": {str(l): leaf(list(v), "k_tokens (amx, avx, fpga)", f"{path} :: decode_like line, layer {l}") for l, v in sorted(layers.items())}}


def section_f():
  out = {}
  out["td-20261016"] = {"runs": parse_runs(f"{RES_TD}/runs.txt"), "tokens": parse_tokens_txt(f"{RES_TD}/tokens.txt"),
                        "probe_done": text_or_pending(f"{RES_TD}/probe.done")}
  out["td2-20261016"] = {"runs": parse_runs(f"{RES_TD2}/runs.txt"), "tokens": parse_tokens_txt(f"{RES_TD2}/tokens.txt"),
                         "verdict": text_or_pending(f"{RES_TD2}/verdict.txt"), "probe_done": text_or_pending(f"{RES_TD2}/probe.done"),
                         "steps": {pair: steps_record(f"{RES_TD2}/steps-{pair}.json") for pair in STEP_PAIRS_TD2}}
  td3 = {"runs": parse_runs(f"{RES_TD3}/runs.txt"), "verdict": text_or_pending(f"{RES_TD3}/verdict.txt"),
         "probe_done": text_or_pending(f"{RES_TD3}/probe.done"), "stats": {}, "deltas_64_minus_63": {}}
  for arm in TD3_ARMS:
    td3["stats"][arm] = parse_stats(f"{RES_TD3}/stats-{arm}.txt")
  for arm in ("base", "new"):
    s63, s64 = td3["stats"][arm + "63"], td3["stats"][arm + "64"]
    if is_pending(s63) or is_pending(s64):
      td3["deltas_64_minus_63"][arm] = pending(f"{RES_TD3}/stats-{arm}63.txt and stats-{arm}64.txt")
      continue
    l63 = {int(k): v["value"] for k, v in s63["k_tokens_per_layer_amx_avx_fpga"].items()}
    l64 = {int(k): v["value"] for k, v in s64["k_tokens_per_layer_amx_avx_fpga"].items()}
    dl = {l: [l64[l][0] - l63[l][0], l64[l][1] - l63[l][1], l64[l][2] - l63[l][2]] for l in sorted(l64) if l in l63}
    distinct = sorted({tuple(v) for v in dl.values()})
    td3["deltas_64_minus_63"][arm] = {
      "per_layer": {str(l): leaf(v, "k_tokens added by step 64 (amx, avx, fpga)", f"{RES_TD3}/stats-{arm}64.txt minus stats-{arm}63.txt, layer {l}") for l, v in dl.items()},
      "distinct_values": leaf([list(v) for v in distinct], "k_tokens (amx, avx, fpga)", f"{RES_TD3}/stats-{arm}64.txt minus stats-{arm}63.txt"),
      "n_layers": leaf(len(dl), "layers", f"{RES_TD3}/stats-{arm}6[34].txt"),
    }
  out["td3-20261016"] = td3
  return out


# ----------------------------------------------------------------------------- G. builds and commits


def parse_build_log(path):
  if not os.path.exists(path):
    return pending(path)
  lines = read_text(path).splitlines()
  r = {}
  for i, ln in enumerate(lines, 1):
    S = f"{path} :: line {i}"
    m = re.match(r"^=== build-\S+ (\S+ )?started (\S+) on (\S+)(?: sha=([0-9a-f]+))?(?: conf=\[(.*)\])? ===", ln)
    if m:
      r["started_utc"] = leaf(m.group(2), "ISO time", S)
      r["host"] = leaf(m.group(3), "host", S)
      if m.group(4):
        r["sha_requested"] = leaf(m.group(4), "git commit", S)
      if m.group(5) is not None:
        r["configure_args"] = leaf(m.group(5), "text", S)
      continue
    m = re.match(r"^HEAD is now at ([0-9a-f]+) (.*)$", ln)
    if m:
      r["head_short"] = leaf(m.group(1), "git commit (short)", S)
      r["head_subject"] = leaf(m.group(2), "commit subject", S)
      continue
    m = re.match(r"^build rc=(\d+)", ln)
    if m:
      r["build_rc"] = leaf(int(m.group(1)), "exit code", S)
      continue
    m = re.search(r"build wall=(\d+)s", ln)
    if m:
      r["build_wall"] = leaf(int(m.group(1)), "s", S)
      continue
    m = re.match(r"^([0-9a-f]{64})\s+(\S+)$", ln)
    if m:
      r["binary"] = leaf(m.group(2), "path (relative to the worktree)", S)
      r["sha256"] = leaf(m.group(1), "sha256 of the binary", S)
      continue
    if ln.startswith("TRON_"):
      r["tron_options"] = leaf(ln.strip(), "CMake cache entries", S)
      continue
    if re.fullmatch(r"\d+", ln.strip()) and "sha256" in r and "tron_options" not in r:
      # build-clean.sh:28 prints grep -c "TRON_AMX_DISPATCH:BOOL=OFF" gen/CMakeCache.txt right after the sha256 line
      r["tron_options"] = leaf(f"TRON_AMX_DISPATCH:BOOL=OFF (matching CMakeCache lines: {ln.strip()})", "CMake cache entries (count from build-clean.sh:28)", S)
      continue
    m = re.match(r"^\S+ ok (\S+)$", ln)
    if m:
      r["smoke_ok_binary"] = leaf(m.group(1), "binary name", S)
    m = re.match(r"^=== build-\S+ (\S+ )?finished (\S+) ===", ln)
    if m:
      r["finished_utc"] = leaf(m.group(2), "ISO time", S)
  return r


def section_g():
  out = {"builds": {}, "commits": {}}
  for v in ("clean", "poc", "trunc"):
    out["builds"][v] = parse_build_log(f"{LOGS}/td-build-{v}.log")
  # the clean build log does not echo its configure line; it is the CONF= line of build-clean.sh
  bc = f"{EXEC}/td-20261016/build-clean.sh"
  if not is_pending(out["builds"]["clean"]) and "configure_args" not in out["builds"]["clean"] and os.path.exists(bc):
    for i, ln in enumerate(read_text(bc).splitlines(), 1):
      m = re.match(r"^CONF='(.*)'", ln)
      if m:
        out["builds"]["clean"]["configure_args"] = leaf(m.group(1), "text", f"{bc} :: line {i}")
        break
  for name, tree in TREES.items():
    try:
      txt = subprocess.run(["git", "-C", tree, "log", "-1", "--format=%H%n%s"], capture_output=True, text=True, timeout=60)
      if txt.returncode != 0:
        out["commits"][name] = pending(tree, f"git failed: {txt.stderr.strip()[:200]}")
        continue
      h, s = (txt.stdout.strip().split("\n") + [""])[:2]
      out["commits"][name] = {"hash": leaf(h, "git commit", f"git -C {tree} log -1 --format=%H"), "subject": leaf(s, "commit subject", f"git -C {tree} log -1 --format=%s")}
    except Exception as e:  # noqa: BLE001
      out["commits"][name] = pending(tree, f"git error: {e}")
  out["predictions_md"] = leaf(read_text(PRED), "text (verbatim)", PRED) if os.path.exists(PRED) else pending(PRED)
  return out


# ----------------------------------------------------------------------------- markdown


def fmt(v):
  if v is None:
    return "None"
  if isinstance(v, bool):
    return "yes" if v else "no"
  if isinstance(v, int):
    return str(v)
  if isinstance(v, float):
    if v != v:
      return "nan"
    if v in (float("inf"), float("-inf")):
      return "inf" if v > 0 else "-inf"
    if v == 0:
      return "0"
    if float(v).is_integer() and abs(v) < 1e6:
      return str(int(v))
    return f"{v:.3g}"
  if isinstance(v, (list, tuple)):
    if len(v) > 40:
      return "[" + ", ".join(fmt(x) for x in v[:40]) + f", ... ({len(v)} items)]"
    return "[" + ", ".join(fmt(x) for x in v) + "]"
  if isinstance(v, dict):
    return "{" + ", ".join(f"{k}: {fmt(x)}" for k, x in v.items()) + "}"
  s = str(v).replace("|", "\\|").replace("\n", " ")
  return s if len(s) <= 160 else s[:157] + "..."


def is_leaf(d):
  return isinstance(d, dict) and set(d.keys()) >= {"value", "unit", "source"} and len(d) == 3


def flatten(d, prefix=""):
  """yield (name, leaf-or-pending) rows."""
  if is_leaf(d) or is_pending(d):
    yield prefix.rstrip("."), d
    return
  if isinstance(d, dict):
    for k, v in d.items():
      yield from flatten(v, f"{prefix}{k}.")
  else:
    yield prefix.rstrip("."), leaf(d, "", "")


def split_source(src):
  if " :: " in src:
    f, fld = src.split(" :: ", 1)
    return f, fld
  return src, ""


def table(rows, title, level=3, max_long_text=False):
  """rows: list of (name, leaf/pending). One table per source file."""
  lines = []
  if not rows:
    return lines
  files = []
  for _, r in rows:
    f, _ = split_source(r["source"])
    if f not in files:
      files.append(f)
  lines.append("#" * level + " " + title)
  lines.append("")
  if len(files) == 1:
    lines.append(f"Source file: `{files[0]}`")
    lines.append("")
    lines.append("| name | value | unit | field / line |")
    lines.append("|---|---|---|---|")
    for name, r in rows:
      if is_pending(r):
        lines.append(f"| {name} | pending | - | {r.get('note', 'file not present yet')} |")
      else:
        _, fld = split_source(r["source"])
        lines.append(f"| {name} | {fmt(r['value'])} | {r['unit']} | {fld} |")
  else:
    lines.append("Source files:")
    lines.append("")
    for n, f in enumerate(files, 1):
      lines.append(f"- [{n}] `{f}`")
    lines.append("")
    lines.append("| name | value | unit | source: [file] field / line |")
    lines.append("|---|---|---|---|")
    for name, r in rows:
      f, fld = split_source(r["source"])
      tag = f"[{files.index(f) + 1}]"
      if is_pending(r):
        lines.append(f"| {name} | pending | - | {tag} {r.get('note', 'file not present yet')} |")
      else:
        lines.append(f"| {name} | {fmt(r['value'])} | {r['unit']} | {tag} {fld} |")
  lines.append("")
  return lines


def md_group(d, title, level=2):
  """One table per second-level key (file or pair); pending entries as one-line notes."""
  lines = ["#" * level + " " + title, ""]
  if is_pending(d):
    lines.append(f"pending: `{d['source']}` ({d.get('note', 'file not present yet')})")
    lines.append("")
    return lines
  for k, v in d.items():
    if is_pending(v):
      lines.append(f"- {k}: pending (`{v['source']}`{', ' + v['note'] if v.get('note') else ''})")
      lines.append("")
      continue
    if is_leaf(v):
      lines += table([(k, v)], k, level + 1)
      continue
    rows = list(flatten(v))
    lines += table(rows, k, level + 1)
  return lines


def write_md(F, path):
  L = ["# Facts for the issue #4444 root-cause report", "",
       f"Generated by `{os.path.abspath(__file__)}`. Every number carries its unit and its source (file path plus JSON field or line number). "
       "Values are shown with at most 3 significant digits here; facts.json holds full precision. "
       "Entries marked pending come from files the running campaign has not produced yet; re-run the script to fill them.", ""]
  # Words used here
  L += ["## Words used here", "",
        "- arm: one runtron run (binary plus environment). base = main 72308ec9 with AMX on; new = PR #4959 head ea94e95a (VNNI K + AMX); poc = new with VNNI blocks unpacked and scored by the row-major dotter; trunc = new with the AMX PV weights truncated; *off = the same binary with TRON_AMX_DISABLE=1 (the kill switch); clean = main built without AMX.",
        "- pair X-vs-Y: the comparison tool was given X as the --off (reference) log and Y as the --on log.",
        "- rel_l2: relative L2 error ||on - off|| / ||off|| of one logged record. frac_changed: fraction of the record's elements that differ. max_ulps: the largest element change in bf16 ulps (one ulp = one bf16 notch of the reference value).",
        "- step k: the k-th generated token (1-based). margin: top-1 minus top-2 logit of the OFF arm at that step. delta_pair: how far the ON arm moves that margin. flip: the ON arm's top-1 id differs from the OFF arm's.",
        "- TVD: total variation distance between the two arms' softmax distributions (0 = identical, 1 = disjoint).",
        "- D / R / A: the three score paths of the replay (row-major AVX dotter, VNNI reader, AMX tile kernel). P: softmax weights. RNE: round to nearest even. trunc: truncation toward zero.",
        "- k_tokens: key tokens visited per layer by the attention paths (amx / avx / fpga) as counted by TRON_ATTN_STATS.", ""]
  L += md_group(F["A_layer_records"], "A. Per-layer record comparisons (dd_first_divergence.py)")
  L += ["## B. Per-step logits comparisons (dd_logits_step.py)", ""]
  for camp, d in F["B_step_logits"].items():
    L += md_group(d, f"B.{camp}", 3)
  L += ["## C. Near-tie statistics (tie_stats.py)", ""]
  for k, d in F["C_tie_stats"].items() if not is_pending(F["C_tie_stats"]) else []:
    L += md_group(d, f"C.{k}", 3)
  if is_pending(F["C_tie_stats"]):
    L.append(f"pending: `{F['C_tie_stats']['source']}`")
  L += md_group(F["D_kernel_tests"], "D. Kernel tests (ktest/results.txt)")
  L += ["## E. Offline replay (replay/results.json and companions)", ""]
  for k, d in F["E_replay"].items():
    L += md_group(d, f"E.{k}", 3) if not (is_leaf(d) or is_pending(d)) else md_group({k: d}, f"E.{k}", 3)
  L += ["## F. Campaign record (runs.txt, tokens.txt, probe.done, second and third rounds)", ""]
  for camp, d in F["F_campaign"].items():
    L += ["### F." + camp, ""]
    for k, v in d.items():
      if is_pending(v) or is_leaf(v):
        L += md_group({k: v}, f"F.{camp}.{k}", 4)
      else:
        L += md_group(v, f"F.{camp}.{k}", 4)
  L += ["## G. Builds and commits", ""]
  L += md_group(F["G_builds"]["builds"], "G.builds", 3)
  L += md_group(F["G_builds"]["commits"], "G.commits", 3)
  p = F["G_builds"]["predictions_md"]
  L += ["### G.predictions_md", ""]
  if is_pending(p):
    L.append(f"pending: `{p['source']}`")
  else:
    L.append(f"Source file: `{p['source']}` (verbatim)")
    L.append("")
    L.append("```")
    L += p["value"].rstrip("\n").splitlines()
    L.append("```")
  L.append("")
  with open(path, "w") as f:
    f.write("\n".join(L))


def count_status(d, acc):
  if is_pending(d):
    acc["pending"] += 1
  elif is_leaf(d):
    acc["leaves"] += 1
  elif isinstance(d, dict):
    for v in d.values():
      count_status(v, acc)


def main():
  F = {
    "A_layer_records": section_a(),
    "B_step_logits": section_b(),
    "C_tie_stats": section_c(),
    "D_kernel_tests": section_d(),
    "E_replay": section_e(),
    "F_campaign": section_f(),
    "G_builds": section_g(),
  }
  jpath = os.path.join(HERE, "facts.json")
  mpath = os.path.join(HERE, "facts.md")
  with open(jpath, "w") as f:
    json.dump(F, f, indent=1)
  write_md(F, mpath)
  acc = {"leaves": 0, "pending": 0}
  count_status(F, acc)
  print(f"wrote {jpath} and {mpath}: {acc['leaves']} leaf values, {acc['pending']} pending entries", file=sys.stderr)
  return 0


if __name__ == "__main__":
  sys.exit(main())
