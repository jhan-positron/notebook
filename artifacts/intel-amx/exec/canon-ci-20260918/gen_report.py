#!/usr/bin/env python3
"""Report generator for the canon-ci campaign (2026-09-18/19): canonical AMX (PR #3879 only) at the CI harness.

Forked from exec/ci-mimic-20260918/gen_report.py (the Friday-morning report). Same helpers, chart functions,
statistics rules, colors and glossary style. New: a third arm (canon), two effects (canon vs base, target vs canon),
a four-series absolute chart, and n/a cells whenever the canon record is missing or incomplete (the page may be
rendered mid-campaign).

Inputs (all JSON unless noted):
  --base      exec/results/ci-mimic-20260918/base-pass1/perf.json     nightly deb of 2026-09-18, no AMX code (st_ci_perf.py record)
  --target    exec/results/ci-mimic-20260918/target-pass1/perf.json   PR #4424 on main 3faba6d0fd + AMX on + VNNI-K on
  --canon     exec/results/canon-ci-20260918/canon/perf.json          main 3faba6d0fd + deb preset TRON_AMX_DISPATCH=ON only
  --nightly   reference/nightly-0918.arm.json                          the 2026-09-18 nightly parsed to the same shape
  --stats     reference/nightly_stats.json                             13-night Slack series per config
  --preflight exec/results/canon-ci-20260918/preflight.txt             text; carries the canon manifest JSON block
  --target-preflight  exec/results/ci-mimic-20260918/preflight.txt     text; carries the target manifest (default path, optional)
  --out       the HTML page
Every number in the page is computed here from those files, the canon campaign log and bill-share.log (marker take and
release times). Hand-typed facts, each named as such on the page: the client-host spot check during the base arm (14:52 UTC,
PSI some 93 %), the base/target marker times of the 2026-09-18 ci-mimic report (01:10 and 17:58 UTC), the 02:45 UTC
ci-runner-stop timer (campaign.sh header) and the 28 application cores per engine (the --app-cores lists in the snapshots).
Pre-registered rules (unchanged from the old report): an effect between two arms is resolved when the paired-by-round
t over the 10 round means has |t| >= 2.262 (p < 0.05 at 9 degrees of freedom), |delta| >= 1 %, and |delta| is at least
the config's 13-night band (2 sd of the Slack series, in percent).
"""
import argparse
import json
import math
import os
import re
import statistics
import time

# ---- the 12 nightly configs in perf.py order, with short names for charts and the per-config reaction note ----
# note = what the canon arm can change (the AMX kernel exists for head size 128 with kv_mul 4 and CPU attention) and what
# the target arm adds (the VNNI-K layout of PR #4424).
ORDER = [
    ("llama-3.2-3b-instruct-fast-tp2", 32, "llama-3.2-3b fast tp2 @32u",
     "CPU attention, kv_mul 3, no AMX kernel. A control for canon. target adds the VNNI-K layout."),
    ("llama-3.1-8b-instruct-good-tp2", 8, "llama-3.1-8b good tp2 @8u",
     "CPU attention, head 128, kv_mul 4: the AMX kernel runs in canon and in target. target adds the VNNI-K layout on top."),
    ("llama-3.3-70b-instruct-good-tp2", 8, "llama-3.3-70b good tp2 @8u",
     "CPU attention, kv_mul 8, no AMX kernel. A control for canon. target adds the VNNI-K layout."),
    ("llama-3.3-70b-instruct-good-tp2", 4, "llama-3.3-70b good tp2 @4u",
     "same engines as the @8u cell (no re-provisioning). A control for canon. target adds the VNNI-K layout."),
    ("llama-3.3-70b-instruct-good-tp4", 4, "llama-3.3-70b good tp4 @4u",
     "CPU attention, kv_mul 8, no AMX kernel. A control for canon. target adds the VNNI-K layout."),
    ("mixtral-8x7b-instruct-v0.1-tp2", 8, "mixtral-8x7b tp2 @8u",
     "CPU attention, head 128, kv_mul 4: the AMX kernel runs in canon and in target. target adds the VNNI-K layout on top."),
    ("qwen-2.5-32b-it-fast-tp2", 8, "qwen-2.5-32b fast tp2 @8u",
     "CPU attention, kv_mul 5, no AMX kernel. A control for canon. target adds the VNNI-K layout."),
    ("ingested-qwen-3-4b-instruct-2507-tp2", 8, "qwen-3-4b tp2 @8u",
     "FPGA attention (nightly default). canon's AMX kernel acts only in the CPU share (positions 0 to 126 of each query and the most recent tokens not yet copied to HBM). target adds the VNNI-K layout to the K cache the FPGA path reads."),
    ("ingested-qwen-3-4b-instruct-2507-tp4", 8, "qwen-3-4b tp4 @8u",
     "FPGA attention, as tp2. Night-to-night noisy (sd 5 TPS)."),
    ("gemma-2-9b-it-fast-tp2", 8, "gemma-2-9b fast tp2 @8u",
     "head 256, no AMX kernel. A control for canon. The 2026-09-18 report treated it as a control for target too (VNNI-K not applied at head 256). That target claim is not re-verified here."),
    ("ingested-gpt-oss-120b-tp4", 8, "gpt-oss-120b tp4 @8u",
     "FPGA attention, head 64, no AMX kernel. A control for canon. Noisy (sd 3 TPS). The 2026-09-18 report treated it as a control for target too. That target claim is not re-verified here."),
    ("ingested-gemma-4-31b-it-tp2", 8, "gemma-4-31b tp2 @8u",
     "head 256, no AMX kernel. A control for canon (and, per the 2026-09-18 report, for target). 3 nights of reference only."),
]
# CURRENT static goals for granite_rapids_72_rinzler (systems_test scripts/system_ci.py get_goal): mean TPS / slowest user TPS
GOALS = {
    ("llama-3.2-3b-instruct-fast-tp2", 32): (191.0, 150.0), ("llama-3.1-8b-instruct-good-tp2", 8): (144.0, 140.0),
    ("llama-3.3-70b-instruct-good-tp2", 4): (27.0, 27.0), ("llama-3.3-70b-instruct-good-tp2", 8): (27.0, 18.0),
    ("llama-3.3-70b-instruct-good-tp4", 4): (27.0, 27.0), ("mixtral-8x7b-instruct-v0.1-tp2", 8): (71.0, 71.0),
    ("qwen-2.5-32b-it-fast-tp2", 8): (35.0, 35.0), ("ingested-qwen-3-4b-instruct-2507-tp2", 8): (175.0, 145.0),
    ("ingested-qwen-3-4b-instruct-2507-tp4", 8): (135.0, 115.0), ("gemma-2-9b-it-fast-tp2", 8): (90.0, 90.0),
    ("ingested-gpt-oss-120b-tp4", 8): (52.0, 40.0), ("ingested-gemma-4-31b-it-tp2", 8): (None, None),
}
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201,
        12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086, 25: 2.060, 30: 2.042}
PCT_FLOOR = 1.0
Z_FLAG = 3.0
T_FLAG = 2.262
N_CONFIGS = len(ORDER)

# palette (dataviz reference instance, light surface): entity colors, never re-assigned.
# canon = categorical slot 3 (aqua) of the dataviz palette (references/palette.md of the bundled dataviz skill; the path
# /home/jhan/.claude/skills/dataviz/references/palette.md named in the task does not exist on this host, the task's
# fallback would have been #2e9e5b). Validated 2026-09-18 with the skill's validate_palette.py: blue, aqua, orange pass
# every hard gate in light mode. Aqua has 2.74:1 contrast on the surface, so every aqua mark carries a direct value label.
C_BASE, C_TARGET, C_CANON, C_NIGHTLY, C_BAND = "#2a78d6", "#eb6834", "#1baf7a", "#898781", "#e1e0d9"
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
ARM_COLORS = {"nightly": C_NIGHTLY, "base": C_BASE, "canon": C_CANON, "target": C_TARGET}
TICK = "#6b6a66"  # axis tick labels: about 5:1 on the surface (the muted gray is 3.5:1, too light for 11 px text)


def haloed_text(x, y, attrs, text):
    """A value label over a surface-colored copy of itself (stroke 3 px), so it stays legible over connectors and the zero
    line. Two elements rather than paint-order="stroke": cairosvg (the project's render check) ignores paint-order."""
    halo_attrs = re.sub(r'\s*fill="[^"]*"', "", attrs)
    return (f'<text x="{x:.1f}" y="{y:.1f}" {halo_attrs} stroke="{SURF}" stroke-width="3" stroke-linejoin="round" fill="{SURF}">{text}</text>'
            f'<text x="{x:.1f}" y="{y:.1f}" {attrs}>{text}</text>')


def clip_marker(x, cy, direction, color, filled):
    """An open triangle at the axis edge, pointing out of the plot (direction -1 = left, +1 = right). filled = the dot
    itself is off scale (not only its whisker end)."""
    tip = x + direction * 9
    fill = color if filled else SURF
    return (f'<path d="M{x:.1f},{cy - 6:.1f} L{tip:.1f},{cy:.1f} L{x:.1f},{cy + 6:.1f} Z" fill="{fill}" stroke="{color}" stroke-width="2" stroke-linejoin="round">'
            f'<title>{"value" if filled else "confidence interval"} beyond the axis edge</title></path>')


def t975(df):
    if df <= 0:
        return float("nan")
    if df in T975:
        return T975[df]
    keys = sorted(T975)
    for k in keys:
        if df < k:
            return T975[k]
    return 1.96


def load(path, what=""):
    """JSON record or None. A missing, empty or half-written file (the driver rewrites it after every config) gives None
    with a note on stderr, never an exception."""
    if not path:
        return None
    if not os.path.exists(path):
        print(f"note: {what or path} not found ({path}); its cells print n/a")
        return None
    try:
        return json.load(open(path))
    except Exception as e:  # noqa: BLE001
        print(f"note: {what or path} not readable ({e}); its cells print n/a")
        return None


def key_of(res):
    c = res["context"]
    return (c["model"], int(c["nominal_users"]))


def rounds_of(raw, n_users):
    """Per-round TPS and TTFT lists. Driver records are flat in round order (each round completes before the
    next starts); nightly records carry explicit rounds."""
    if raw is None:
        return [], []
    if raw.get("rounds"):
        return [r["tps"] for r in raw["rounds"]], [r["ttft_ms"] for r in raw["rounds"]]
    tps, ttft = raw.get("tpss") or [], raw.get("ttfts_ms") or []
    if n_users and len(tps) % n_users == 0 and len(tps) > 0:
        return ([tps[i:i + n_users] for i in range(0, len(tps), n_users)],
                [ttft[i:i + n_users] for i in range(0, len(ttft), n_users)] if len(ttft) == len(tps) else [])
    return [tps] if tps else [], [ttft] if ttft else []


def arm_table(rec):
    """key -> dict(tps_mean, tps_sd, p05, min, ttft_mean, n, round_tps[], round_ttft[], minutes, engines, prov_s)"""
    out = {}
    if not rec:
        return out
    raws = {}
    for r in rec.get("raw") or []:
        try:
            raws.setdefault((r["model"], int(r["n_users"])), r)
        except Exception:  # noqa: BLE001
            pass
    def row(tps, rt, rf, res):
        ttft_all = [x for r in rf for x in r] if rf else []
        s = sorted(tps)
        p05 = None
        if s:
            pos = (len(s) - 1) * 0.05
            lo = int(pos); hi = min(lo + 1, len(s) - 1); p05 = s[lo] + (s[hi] - s[lo]) * (pos - lo)
        return {
            "tps_mean": statistics.mean(tps) if tps else None, "tps_sd": statistics.pstdev(tps) if len(tps) > 1 else 0.0,
            "p05": p05, "min": min(tps) if tps else None, "n": len(tps),
            "ttft_mean": (statistics.mean(ttft_all) if ttft_all else res.get("ttft_mean")),
            "ttft_sd": statistics.pstdev(ttft_all) if len(ttft_all) > 1 else None,
            "round_tps": [statistics.mean(r) for r in rt if r], "round_ttft": [statistics.mean(r) for r in rf if r],
            "minutes": res.get("minutes"), "engines": res.get("engines"), "prov_s": res.get("provision_seconds"),
            "failed": not tps, "from_raw": not res,
        }

    for res in rec.get("results") or []:
        try:
            k = key_of(res)
        except Exception:  # noqa: BLE001
            continue
        tps = res.get("tps_results") or []
        rt, rf = rounds_of(raws.get(k), k[1])
        if not tps and rt:
            tps = [x for r in rt for x in r]
        out[k] = row(tps, rt, rf, res)
    # Mid-campaign shape: the driver appends one 'raw' entry after every config and writes 'results' only after the
    # last config (st_ci_perf.py: benchmark_and_keep, then the loop after test_performance). A config that has raw
    # samples but no result gets its row from the raw samples. Checked on base-pass1 and target-pass1: mean and min
    # of raw.tpss equal the result's tps_mean and min_tps, and mean of raw.ttfts_ms equals ttft_mean within 0.5 ms.
    for k, r in raws.items():
        if k in out:
            continue
        rt, rf = rounds_of(r, k[1])
        out[k] = row([x for rr in rt for x in rr], rt, rf, {})
    return out


def paired(a, b):
    """paired difference b - a over rounds: mean, sd, t, n, ci95 (absolute units)."""
    n = min(len(a), len(b))
    if n < 2:
        return None
    d = [b[i] - a[i] for i in range(n)]
    m = statistics.mean(d); sd = statistics.stdev(d) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else float("nan")
    t = (m / se) if se and se > 0 else (float("inf") if m != 0 else 0.0)
    ci = t975(n - 1) * se if se == se else float("nan")
    return {"mean": m, "sd": sd, "t": t, "n": n, "ci": ci}


def pct(x, ref):
    return (x - ref) / ref * 100.0 if (x is not None and ref) else None


def fmt(x, nd=2, unit=""):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:,.{nd}f}{unit}"


def signed(x, nd=1, unit=" %"):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:+.{nd}f}{unit}"


def tstr(pr):
    """paired t for a table cell."""
    if not pr:
        return "n/a"
    t = pr["t"]
    return "inf" if math.isinf(t) else f"{t:+.1f}"


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def band13(stats, k):
    """13-night Slack series for a config key -> dict(mean, sd, n, ttft_mean, ttft_sd, slowest_mean, slowest_sd, series)"""
    if not stats:
        return None
    name = f"{k[0]} @{k[1]}u"
    s = stats.get(name)
    if not s or not s.get("series"):
        return None
    tps = [r["tps"] for r in s["series"] if r.get("tps") is not None]
    ttft = [r["ttft_ms"] for r in s["series"] if r.get("ttft_ms") is not None]
    slow = [r["slowest"] for r in s["series"] if r.get("slowest") is not None]
    if not tps:
        return None
    return {"n": len(tps), "mean": statistics.mean(tps), "sd": statistics.stdev(tps) if len(tps) > 1 else 0.0,
            "min": min(tps), "max": max(tps),
            "ttft_mean": statistics.mean(ttft) if ttft else None, "ttft_sd": statistics.stdev(ttft) if len(ttft) > 1 else None,
            "slow_mean": statistics.mean(slow) if slow else None, "slow_sd": statistics.stdev(slow) if len(slow) > 1 else None,
            "series": s["series"]}


def snapshot_facts(rec):
    """Pull the evidence lines out of the driver's snapshots."""
    if not rec:
        return {}
    f = {"engine_counts": [], "deleted": 0, "deleted_detail": [], "dut_load": [], "unit_count": None, "env_vars": None, "sst": None,
         "rinzler_sha": None, "tron": None, "exe_checked": 0, "exe_mismatch": 0, "exe_mismatch_tags": [], "exe_snapshots": 0}
    for s in rec.get("snapshots") or []:
        t = s.get("text") or ""
        del_lines = re.findall(r"^(\d+) /\S+ \(deleted\)(?: ([0-9a-f]{16}))?$", t, re.M)  # pid lines only; the header names the word
        if del_lines:
            f["deleted"] += 1
            when = time.strftime("%H:%M:%S", time.gmtime(s["t"])) if s.get("t") else "?"
            f["deleted_detail"].append({"tag": s.get("tag") or "?", "time": when, "pids": len(del_lines),
                                        "exe_shas": sorted({sha for _, sha in del_lines if sha}),
                                        "models": sorted(set(re.findall(r"RZ_MODELS=(\S+)", t)))})
        # The DUT's own 1-minute load average (the 'uptime' line of the snapshot). Idle rinzler engines keep their worker
        # threads spinning, so 4 engines alone give a load near 125 on this 72-core machine.
        m_load = re.search(r"load average: ([0-9.]+), ([0-9.]+), ([0-9.]+)", t)
        if m_load:
            f["dut_load"].append(float(m_load.group(1)))
        # Running-binary identity: every engine pid line carries the first 16 hex of the sha256 of /proc/<pid>/exe.
        # Compare it with the sha256 of /opt/positron/bin/rinzler taken in the SAME snapshot. A mismatch after a
        # provisioning means an engine served a binary other than the arm's package (the deleted-binary trap of
        # 2026-09-18; the driver only logs it). Only after-provision snapshots count: the "before" snapshot may show
        # the previous arm's engines by design.
        if (s.get("tag") or "").startswith("after-provision"):
            m_disk = re.search(r"=== rinzler\n([0-9a-f]{64})", t)
            pid_lines = re.findall(r"^(\d+) (\S+)(?: \(deleted\))? ([0-9a-f]{16})$", t, re.M)
            if m_disk and pid_lines:
                f["exe_snapshots"] += 1
                bad = [pl for pl in pid_lines if pl[2] != m_disk.group(1)[:16]]
                f["exe_checked"] += len(pid_lines)
                f["exe_mismatch"] += len(bad)
                if bad:
                    f["exe_mismatch_tags"].append(s["tag"].split(":", 1)[1])
        m = re.search(r"=== engines\n(\[.*\])\s*\n", t)
        if m and (s.get("tag") or "").startswith("after-provision"):
            try:
                eng = json.loads(m.group(1))
                f["engine_counts"].append((s["tag"].split(":", 1)[1], sum(1 for e in eng if e[1] == "running"), len(eng)))
            except Exception:  # noqa: BLE001
                pass
        m = re.search(r"=== unit\n(\d+)", t)
        if m:
            f["unit_count"] = int(m.group(1))
        m = re.search(r"=== rinzler\n([0-9a-f]{64})", t)
        if m:
            f["rinzler_sha"] = m.group(1)
        m = re.search(r"\nii\s+tron\s+(\S+)", t)
        if m:
            f["tron"] = m.group(1)
        m = re.search(r"Intel Speed Select[^\n]*", t)
        if m:
            f["sst"] = m.group(0)
        m = re.search(r"AMX/HW_ATTN vars \(must be 0\)\n([^\n]*)", t)
        if m:
            f["env_vars"] = m.group(1).strip()
    return f


def psi_avg10(s):
    """'some avg10=98.94 avg60=...' -> 98.94, or None."""
    m = re.search(r"avg10=([0-9.]+)", s or "")
    return float(m.group(1)) if m else None


def client_conditions(rec):
    """Client-host load and CPU pressure over the driver's snapshots.
    -> dict(n, load: (min, max) of the 1-minute load average, psi: (min, max) of PSI some avg10 in percent or None,
            per_config: [(index 1.., model, avg10 or None)], hi: [config indexes with avg10 >= 50])"""
    if not rec:
        return None
    snaps = rec.get("snapshots") or []
    loads = [s["client_load"][0] for s in snaps if s.get("client_load")]
    psis = [psi_avg10(s.get("client_cpu_psi")) for s in snaps if s.get("client_cpu_psi")]
    psis = [p for p in psis if p is not None]
    per = []
    for s in snaps:
        tag = s.get("tag") or ""
        if tag.startswith("after-provision:"):
            per.append((len(per) + 1, tag.split(":", 1)[1], psi_avg10(s.get("client_cpu_psi")) if s.get("client_cpu_psi") else None))
    return {"n": len(snaps), "load": (min(loads), max(loads)) if loads else None,
            "psi": (min(psis), max(psis)) if psis else None, "per_config": per,
            "hi": [i for i, _, p in per if p is not None and p >= 50.0],
            "lo_rest": [p for i, _, p in per if p is not None and p < 50.0]}


def ranges_text(idx):
    """[1,2,3,5] -> 'configs 1 to 3 and 5'."""
    if not idx:
        return "no config"
    idx = sorted(idx)
    groups, start, prev = [], idx[0], idx[0]
    for i in idx[1:]:
        if i == prev + 1:
            prev = i
            continue
        groups.append((start, prev)); start = prev = i
    groups.append((start, prev))
    parts = [f"{a}" if a == b else f"{a} to {b}" for a, b in groups]
    word = "config" if len(idx) == 1 else "configs"
    return word + " " + (parts[0] if len(parts) == 1 else ", ".join(parts[:-1]) + " and " + parts[-1])


def load_text(c):
    if not c or not c.get("load"):
        return "n/a"
    return f"{c['load'][0]:.1f} to {c['load'][1]:.1f} ({c['n']} snapshots)"


def psi_text(c):
    if not c:
        return "n/a"
    if not c.get("psi"):
        return "no PSI record"
    return f"{c['psi'][0]:.0f} to {c['psi'][1]:.0f} %"


def parse_manifest(text):
    """The first JSON object in a preflight text that carries deb_sha256 (nested objects allowed)."""
    dec = json.JSONDecoder()
    for m in re.finditer(r"^\{", text, re.M):
        try:
            obj, _ = dec.raw_decode(text, m.start())
        except Exception:  # noqa: BLE001
            continue
        if isinstance(obj, dict) and "deb_sha256" in obj:
            return obj
    return None


def hhmm(iso):
    """'2026-09-18T13:43:23Z' or '2026-09-18 13:43:23' -> '13:43'."""
    m = re.search(r"(\d\d):(\d\d)(?::\d\d)?", iso or "")
    return f"{m.group(1)}:{m.group(2)}" if m else "?"


def day_of(iso):
    m = re.search(r"\d{4}-(\d\d-\d\d)", iso or "")
    return m.group(1) if m else "?"


def epoch(iso):
    try:
        return time.mktime(time.strptime(iso[:19].replace(" ", "T"), "%Y-%m-%dT%H:%M:%S"))
    except Exception:  # noqa: BLE001
        return None


def window(rec, k_start="started", k_end="finished"):
    """'09-18 22:44 to 23:50', or '09-18 22:44 to 09-19 00:15' when the window crosses midnight."""
    if not rec or not rec.get(k_start):
        return "n/a"
    end = rec.get(k_end)
    if not end:
        return f"{day_of(rec[k_start])} {hhmm(rec[k_start])} to running"
    end_day = f"{day_of(end)} " if day_of(end) != day_of(rec[k_start]) else ""
    return f"{day_of(rec[k_start])} {hhmm(rec[k_start])} to {end_day}{hhmm(end)}"


def main_of_version(v):
    """'2026.09.18-3faba6d0' -> '3faba6d0' (the deb version names its main commit)."""
    m = re.search(r"\d{4}\.\d\d\.\d\d-([0-9a-f]{7,12})", v or "")
    return m.group(1) if m else None


def effect(ref, arm, bd):
    """arm relative to ref (both arm_table rows). None when either side has no TPS mean.
    -> pct, paired, ci_pct, band_pct, flag, ttft_pct, ttft_paired, ttft_ci_pct, ttft_band_pct, ttft_flag."""
    if not (ref and arm and ref.get("tps_mean") and arm.get("tps_mean")):
        return None
    e = {"pct": pct(arm["tps_mean"], ref["tps_mean"])}
    pr = paired(ref["round_tps"], arm["round_tps"])
    e["paired"] = pr
    e["ci_pct"] = (pr["ci"] / ref["tps_mean"] * 100) if pr and pr["ci"] == pr["ci"] else None
    # resolved = paired t significant AND at least 1 % AND at least the 13-night band (2 sd, in percent of the 13-night mean).
    # Calibration: nightlies 09-16 vs 09-17 differ by +4.7 % on qwen-3-4b tp4 with a paired t above 2.26, so the t alone
    # over-calls the noisy configs.
    night_band = (2 * bd["sd"] / bd["mean"] * 100) if bd and bd["mean"] else 0.0
    e["band_pct"] = night_band
    # flag None = not testable: no per-round data, so the paired t does not exist (the delta is still shown)
    e["flag"] = None if pr is None else bool(abs(pr["t"]) >= T_FLAG and abs(e["pct"]) >= max(PCT_FLOOR, night_band))
    if ref.get("ttft_mean") and arm.get("ttft_mean"):
        e["ttft_pct"] = pct(arm["ttft_mean"], ref["ttft_mean"])
        prf = paired(ref["round_ttft"], arm["round_ttft"]) if ref["round_ttft"] and arm["round_ttft"] else None
        e["ttft_paired"] = prf
        e["ttft_ci_pct"] = (prf["ci"] / ref["ttft_mean"] * 100) if prf and prf["ci"] == prf["ci"] else None
        ttft_band = (2 * bd["ttft_sd"] / bd["ttft_mean"] * 100) if bd and bd.get("ttft_sd") and bd.get("ttft_mean") else 0.0
        # the Slack TTFT reference is an integer (ms), so a 1 ms band floor stands in for rounding
        ttft_floor = max(PCT_FLOOR, ttft_band, 1.0 / ref["ttft_mean"] * 100)
        e["ttft_band_pct"] = ttft_band
        e["ttft_flag"] = None if prf is None else bool(abs(prf["t"]) >= T_FLAG and abs(e["ttft_pct"]) >= ttft_floor)
    return e


# ---------------- charts (inline SVG, light surface) ----------------
def chart_pct(rows, title, subtitle, xlabel, color, band_key=None, ci_key="ci_pct", val_key="pct", note=None, clip=None):
    """Horizontal dot chart of percent differences, one row per config. rows: list of dicts with
    label, pct, ci_pct (half-width, may be None), band_pct (half-width of the reference band, may be None), flag(bool).
    clip = largest |percent| the axis shows; a value or whisker beyond it is drawn at the edge and its label says so."""
    sub_lines = wrap(subtitle)
    W, left, right, rowh = 960, 250, 150, 30
    top = 52 + 16 * len(sub_lines)
    n = len(rows)
    H = top + n * rowh + 60 + (16 if note else 0)
    vals = []
    for r in rows:
        if r.get(val_key) is not None:
            vals += [r[val_key] - (r.get(ci_key) or 0), r[val_key] + (r.get(ci_key) or 0)]
        if band_key and r.get(band_key) is not None:
            c = r.get("band_center") or 0.0
            vals += [c - r[band_key], c + r[band_key]]
    lim = max(5.0, max(abs(v) for v in vals) * 1.15) if vals else 5.0
    if clip is not None:
        lim = min(lim, clip)
    lim = math.ceil(lim)
    if clip is not None and any(abs(v) > lim for v in vals):
        right = 230  # room for the "(CI +/-N %, off scale)" label of a clipped row
        pw = W - left - right
    pw = W - left - right
    x0 = left + pw / 2

    def X(v):
        return x0 + (v / lim) * (pw / 2)

    step = 1 if lim <= 6 else (2 if lim <= 14 else (5 if lim <= 40 else 10))
    ticks = [v for v in range(-lim, lim + 1) if v % step == 0]
    out = svg_header(W, H, title, sub_lines)
    for v in ticks:
        out.append(f'<line x1="{X(v):.1f}" y1="{top - 6}" x2="{X(v):.1f}" y2="{top + n * rowh}" stroke="{GRID if v else MUTED}" stroke-width="1"/>')
        out.append(f'<text x="{X(v):.1f}" y="{top + n * rowh + 18}" font-size="11" fill="{TICK}" text-anchor="middle">{v:+d} %</text>')
    out.append(f'<text x="{x0:.1f}" y="{top + n * rowh + 40}" font-size="12" fill="{INK2}" text-anchor="middle">{esc(xlabel)}</text>')
    for i, r in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        out.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="12" fill="{INK2}" text-anchor="end">{esc(r["label"])}</text>')
        if band_key and r.get(band_key) is not None:
            c = r.get("band_center") or 0.0
            lo_b, hi_b = max(-lim, c - r[band_key]), min(lim, c + r[band_key])
            out.append(f'<rect x="{X(lo_b):.1f}" y="{cy - 9:.1f}" width="{max(2.0, X(hi_b) - X(lo_b)):.1f}" height="18" fill="{C_BAND}" rx="2"><title>{esc(r.get("band_title", ""))}</title></rect>')
        v = r.get(val_key)
        if v is None:
            out.append(f'<text x="{x0 + 8:.1f}" y="{cy + 4:.1f}" font-size="11" fill="{MUTED}">no data</text>')
            continue
        v_c = max(-lim, min(lim, v))
        ci = r.get(ci_key)
        has_ci = ci is not None and ci == ci
        lo_clip = v < -lim or (has_ci and v - ci < -lim)   # something is cut off at the left edge
        hi_clip = v > lim or (has_ci and v + ci > lim)     # ... at the right edge
        clipped = lo_clip or hi_clip
        if has_ci:
            out.append(f'<line x1="{X(max(-lim, v - ci)):.1f}" y1="{cy:.1f}" x2="{X(min(lim, v + ci)):.1f}" y2="{cy:.1f}" stroke="{color}" stroke-width="2" stroke-linecap="round"/>')
        # a cut-off dot or whisker end is marked by an open triangle pointing out of the plot at that edge
        if lo_clip:
            out.append(clip_marker(X(-lim), cy, -1, color, filled=v < -lim))
        if hi_clip:
            out.append(clip_marker(X(lim), cy, +1, color, filled=v > lim))
        if abs(v) <= lim:
            out.append(f'<circle cx="{X(v_c):.1f}" cy="{cy:.1f}" r="7" fill="{SURF}"/>')
            out.append(f'<circle cx="{X(v_c):.1f}" cy="{cy:.1f}" r="5" fill="{color}"><title>{esc(r.get("tip", ""))}</title></circle>')
        weight = "600" if r.get("flag") else "400"
        extra = (f" (CI &#177;{ci:.0f} %, off scale)" if (clipped and has_ci) else (" (off scale)" if clipped else ""))
        # label placement: right of the whisker's right end. A value cut off at the left edge gets its label just inside that
        # edge, next to its marker (the halo keeps it legible over the whisker). A value cut off at the right edge gets it
        # left of the right edge, end-anchored.
        anchor = "start"
        if v < -lim:
            lx = X(-lim) + 14
        elif v > lim:
            lx, anchor = X(lim) - 14, "end"
        else:
            lx = X(min(lim, v_c + (ci or 0))) + 10
        out.append(haloed_text(lx, cy + 4, f'font-size="12" font-weight="{weight}" fill="{INK}" text-anchor="{anchor}"', f'{signed(v)}{" *" if r.get("flag") else ""}{extra}'))
    if note:
        for j, l in enumerate(wrap(note, 130)):
            out.append(f'<text x="16" y="{H - 8 - 14 * (len(wrap(note, 130)) - 1 - j)}" font-size="11" fill="{MUTED}">{esc(l)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def chart_abs(rows, title, subtitle, series, connectors, note):
    """Small multiples: one row per config with its own axis. series = [(key, color, name)], one dot per series present in
    the row; connectors = [(key_a, key_b, dasharray or None)] drawn between two dots of the same row; 13-night min-max as a band."""
    sub_lines = wrap(subtitle)
    note_lines = wrap(note, 130)
    W, left, right, rowh = 960, 250, 40, 50  # 50 px rows: the fifth label slot (a second line below) stays inside the row
    top = 52 + 16 * len(sub_lines)
    n = len(rows)
    H = top + n * rowh + 24 + 14 * len(note_lines)
    pw = W - left - right
    colors = {k: c for k, c, _ in series}
    names = {k: nm for k, _, nm in series}
    out = svg_header(W, H, title, sub_lines)
    for i, r in enumerate(rows):
        cy = top + i * rowh + rowh / 2
        pts = [(k, r.get(k)) for k, _, _ in series if r.get(k) is not None]
        vals = [v for _, v in pts] + ([r["band"][0], r["band"][1]] if r.get("band") else [])
        out.append(f'<text x="{left - 10}" y="{cy + 4:.1f}" font-size="12" fill="{INK2}" text-anchor="end">{esc(r["label"])}</text>')
        if not vals:
            out.append(f'<text x="{left + 8}" y="{cy + 4:.1f}" font-size="11" fill="{MUTED}">no data</text>')
            continue
        lo, hi = min(vals), max(vals)
        span = (hi - lo) or (abs(hi) * 0.05 or 1.0)
        lo -= span * 0.35; hi += span * 0.35

        def X(v):
            return left + (v - lo) / (hi - lo) * pw
        out.append(f'<line x1="{left}" y1="{cy:.1f}" x2="{left + pw}" y2="{cy:.1f}" stroke="{GRID}" stroke-width="1"/>')
        if r.get("band"):
            out.append(f'<rect x="{X(r["band"][0]):.1f}" y="{cy - 8:.1f}" width="{max(2.0, X(r["band"][1]) - X(r["band"][0])):.1f}" height="16" fill="{C_BAND}" rx="2"><title>13-night range {fmt(r["band"][0])} to {fmt(r["band"][1])}</title></rect>')
        # The two connectors run in two lanes (solid 4 px above the row line, dashed 4 px below), so a dashed connector that
        # doubles back over a solid one (target on the same side of canon as base) stays visible.
        for j, (ka, kb, dash) in enumerate(connectors):
            if r.get(ka) is not None and r.get(kb) is not None:
                d = f' stroke-dasharray="{dash}"' if dash else ""
                ly = cy - 4 if j == 0 else cy + 4
                out.append(f'<line x1="{X(r[ka]):.1f}" y1="{ly:.1f}" x2="{X(r[kb]):.1f}" y2="{ly:.1f}" stroke="{INK2}" stroke-width="2" stroke-linecap="round"{d}><title>{names[ka]} to {names[kb]}: {signed(pct(r[kb], r[ka]))}</title></line>')
        # Dots whose X differ by less than 10 px (two radii) form one group: nested circles (radius 5, 3, 2) and one shared
        # label that names each member with its value, so near-coincident arms neither hide each other nor collide in the
        # label lanes. The nightly is not a dot: it is a hollow ring drawn after every dot, so it never hides an arm and is
        # never hidden by one (its gray is also too close to the canon green under a deuteranopia simulation).
        groups = []
        for k, v in pts:
            for g in groups:
                if abs(g["x"] - X(v)) < 10.0:
                    g["members"].append((k, v)); break
            else:
                groups.append({"x": X(v), "members": [(k, v)]})
        for g in groups:
            g["x"] = sum(X(v) for _, v in g["members"]) / len(g["members"])
            arms = [(k, v) for k, v in g["members"] if k != "nightly"]
            if arms:
                gx = sum(X(v) for _, v in arms) / len(arms)
                out.append(f'<circle cx="{gx:.1f}" cy="{cy:.1f}" r="7" fill="{SURF}"/>')
                for j, (k, v) in enumerate(arms):
                    out.append(f'<circle cx="{gx:.1f}" cy="{cy:.1f}" r="{max(2, 5 - 2 * j)}" fill="{colors[k]}"><title>{names[k]}: {fmt(v)} {esc(r.get("unit", ""))}</title></circle>')
            if len(g["members"]) == 1:
                g["text"] = fmt(g["members"][0][1], 1 if g["members"][0][1] >= 100 else 2)
            else:
                g["text"] = ", ".join(f"{fmt(v, 1 if v >= 100 else 2)} {k}" for k, v in g["members"])
        for k, v in pts:
            if k == "nightly":
                out.append(f'<circle cx="{X(v):.1f}" cy="{cy:.1f}" r="6" fill="none" stroke="{C_NIGHTLY}" stroke-width="2"><title>{names[k]}: {fmt(v)} {esc(r.get("unit", ""))}</title></circle>')
        gi_of = list(range(len(groups)))
        lab = place_labels([(g["x"], gi) for gi, g in zip(gi_of, groups)], widths={gi: 6.5 * len(g["text"]) + 4 for gi, g in zip(gi_of, groups)})
        for gi, g in zip(gi_of, groups):
            dy, anchor, dx = lab[gi]
            # keep the label inside the drawing: shift a centered label that would cross the right or left edge
            w = 6.5 * len(g["text"]) + 4
            lx = g["x"] + dx
            if anchor == "middle":
                lx = min(max(lx, left + w / 2), W - 8 - w / 2)
            elif anchor == "start":
                lx = min(lx, W - 8 - w)
            out.append(haloed_text(lx, cy + dy, f'font-size="11" fill="{INK2}" text-anchor="{anchor}"', esc(g["text"])))
    for j, l in enumerate(note_lines):
        out.append(f'<text x="16" y="{H - 8 - 14 * (len(note_lines) - 1 - j)}" font-size="11" fill="{MUTED}">{esc(l)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def wrap(text, width=108):
    """Split a subtitle into lines of at most `width` characters at word boundaries."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width and cur:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def svg_header(W, H, title, subtitle_lines):
    out = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" style="max-width:{W}px;font-family:system-ui,-apple-system,\'Segoe UI\',sans-serif;background:{SURF}" role="img" aria-label="{esc(title)}">',
           f'<text x="16" y="24" font-size="16" font-weight="600" fill="{INK}">{esc(title)}</text>']
    for i, l in enumerate(subtitle_lines):
        out.append(f'<text x="16" y="{44 + 16 * i}" font-size="12" fill="{INK2}">{esc(l)}</text>')
    return out


def place_labels(points, label_w=40, widths=None):
    """points: list of (x, key); widths: optional {key: label width in px} (default label_w). Returns
    {key: (dy, anchor, dx)}. Five slots per dot, tried in order: below, above, right of the dot, left of the dot, a
    second line below. A slot is free when the label's horizontal span overlaps no label already placed in that slot's
    lane and, for the right and left slots, covers no other dot."""
    slots = [(17, "middle", 0), (-11, "middle", 0), (4, "start", 13), (4, "end", -13), (29, "middle", 0)]
    lanes = {i: [] for i in range(len(slots))}
    xs = [x for x, _ in points]
    out = {}

    def span(i, x, w):
        dy, anchor, dx = slots[i]
        if anchor == "middle":
            return (x - w / 2, x + w / 2)
        if anchor == "start":
            return (x + dx, x + dx + w)
        return (x + dx - w, x + dx)

    def free(i, x, w):
        lo, hi = span(i, x, w)
        if any(not (hi < a or lo > b) for a, b in lanes[i]):
            return False
        if i >= 2 and any(lo - 8 < px < hi + 8 for px in xs if px != x):  # a dot under an inline label
            return False
        return True

    for x, k in sorted(points):
        w = (widths or {}).get(k, label_w)
        for i in range(len(slots)):
            if free(i, x, w):
                lanes[i].append(span(i, x, w)); out[k] = slots[i]; break
        else:
            out[k] = slots[0]; lanes[0].append(span(0, x, w))  # every slot taken: below, and accept the overlap
    return out


def legend(items):
    """items: (color, text) or (color, text, shape) with shape 'dot' (default), 'rect' (a band) or 'ring' (the nightly)."""
    def sw(c, shape):
        if shape == "rect":
            return f'<i style="background:{c};width:18px;border-radius:2px"></i>'
        if shape == "ring":
            return f'<i style="background:none;border:2px solid {c};width:8px;height:8px"></i>'
        return f'<i style="background:{c}"></i>'
    return '<div class="legend">' + "".join(f'<span>{sw(it[0], it[2] if len(it) > 2 else "dot")}{esc(it[1])}</span>' for it in items) + "</div>"


# ---------------- main ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True); ap.add_argument("--target", required=True); ap.add_argument("--canon")
    ap.add_argument("--nightly"); ap.add_argument("--stats"); ap.add_argument("--preflight", help="the canon preflight.txt (carries the canon manifest)")
    ap.add_argument("--target-preflight", default="/home/jhan/workspace/intel-AMX/exec/results/ci-mimic-20260918/preflight.txt",
                    help="the ci-mimic preflight.txt (carries the target manifest; optional)")
    ap.add_argument("--out", required=True); ap.add_argument("--nightly-run-id", default="")
    ap.add_argument("--caveats", help="HTML fragment (a <ul>) inserted as the caveats section")
    ap.add_argument("--notes", help="HTML fragment inserted after the effect tables (interpretation of the flagged rows)")
    ap.add_argument("--short3", help="third sentence of the Short version (replaces the default one-run sentence)")
    ap.add_argument("--campaign-log", default="/home/jhan/workspace/intel-AMX/exec/logs/canon-ci-20260918.log", help="the canon campaign log (lease and flock lines; optional)")
    ap.add_argument("--bill-log", default="/home/jhan/workspace/intel-AMX/exec/logs/bill-share.log", help="bill-share.sh's log (marker take and release lines; optional)")
    ap.add_argument("--thr-note", help="HTML paragraph inserted under the threshold table")
    ap.add_argument("--title", default="Canonical AMX at the CI harness: the nightly perf phase with PR #3879 only")
    a = ap.parse_args()

    base_rec, tgt_rec, can_rec = load(a.base, "base record"), load(a.target, "target record"), load(a.canon, "canon record")
    ngt_rec, stats = load(a.nightly, "nightly record"), load(a.stats, "13-night statistics")
    pre = open(a.preflight).read() if a.preflight and os.path.exists(a.preflight) else ""
    if a.preflight and not pre:
        print(f"note: canon preflight not found ({a.preflight}); the manifest table prints n/a")
    manifest = parse_manifest(pre) if pre else None
    if pre and manifest is None:
        print(f"note: no manifest JSON block in {a.preflight}; the manifest table prints n/a")
    manifest_na = "n/a (no manifest block in the preflight)" if pre else "n/a (preflight not available)"
    tpre = open(a.target_preflight).read() if a.target_preflight and os.path.exists(a.target_preflight) else ""
    tmanifest = parse_manifest(tpre) if tpre else None

    B, T, C, N = arm_table(base_rec), arm_table(tgt_rec), arm_table(can_rec), arm_table(ngt_rec)
    fb, ft, fc = snapshot_facts(base_rec), snapshot_facts(tgt_rec), snapshot_facts(can_rec)
    cb, ct, cc = client_conditions(base_rec), client_conditions(tgt_rec), client_conditions(can_rec)

    def version_of(rec, facts, fallback="?"):
        return facts.get("tron") or ((rec or {}).get("versions") or {}).get("Tron (package)") or (rec or {}).get("tron_version") or fallback

    base_ver, tgt_ver = version_of(base_rec, fb), version_of(tgt_rec, ft)
    m = re.search(r"canon build:.*?version=(\S+)", pre)
    can_ver = version_of(can_rec, fc, (m.group(1) if m else "not built yet"))
    ngt_ver = (ngt_rec or {}).get("tron_version", "?")
    main_sha = (manifest or {}).get("main_sha") or (tmanifest or {}).get("main_sha") or main_of_version(base_ver) or "?"
    main10 = main_sha[:10]

    rows = []
    for model, users, short, note in ORDER:
        k = (model, users)
        b, t, c, ng, bd = B.get(k), T.get(k), C.get(k), N.get(k), band13(stats, k)
        r = {"key": k, "short": short, "note": note, "b": b, "t": t, "c": c, "n": ng, "band": bd}
        if b and ng and b["tps_mean"] and ng["tps_mean"]:
            r["fid_pct"] = pct(b["tps_mean"], ng["tps_mean"])
        r["A"] = effect(b, c, bd)   # canon vs base
        r["Bt"] = effect(c, t, bd)  # target vs canon
        r["D"] = effect(b, t, bd)   # target vs base (the 2026-09-18 report's effect, for the summary table)
        rows.append(r)

    canon_rows = [r for r in rows if r.get("c") and r["c"]["tps_mean"]]
    n_canon = len(canon_rows)
    canon_partial = 0 < n_canon < N_CONFIGS
    A_rows = [r for r in rows if r.get("A")]
    A_sig = sorted([r for r in A_rows if r["A"]["flag"]], key=lambda r: -abs(r["A"]["pct"]))
    Bt_rows = [r for r in rows if r.get("Bt")]
    Bt_sig = sorted([r for r in Bt_rows if r["Bt"]["flag"]], key=lambda r: -abs(r["Bt"]["pct"]))
    fid = [abs(r["fid_pct"]) for r in rows if r.get("fid_pct") is not None]

    def probe_of(rec, prefix):
        for p in (rec or {}).get("amx_probes") or []:
            if (p.get("model") or "").startswith(prefix):
                return p.get("amx_busy_cycles")
        return None

    def billions(x):
        return f"{x / 1e9:.1f} billion" if x else "0"

    # ---- Short version: three short sentences that answer the two reviewer questions (built after the verdicts below)
    def n_cfg(n):
        return f"{n} config{'s' if n != 1 else ''}"

    def billions(x):
        return f"{x / 1e9:.1f} billion" if x else "0"

    def probe_of(rec, prefix):
        for p in (rec or {}).get("amx_probes") or []:
            if (p.get("model") or "").startswith(prefix):
                return p.get("amx_busy_cycles")
        return None

    sofar = " with canon data so far" if canon_partial else ""
    l8b = next((r for r in rows if r["key"][0].startswith("llama-3.1-8b")), None)
    l8b_c, l8b_b = probe_of(can_rec, "llama-3.1-8b"), probe_of(base_rec, "llama-3.1-8b")
    qwen_rows = [r for r in rows if r["key"][0].startswith("ingested-qwen-3-4b")]

    def tp_of(r):
        return re.search(r"tp\d", r["key"][0]).group(0)

    def res_mark(e):
        return " (resolved)" if e["flag"] else (" (not testable)" if e["flag"] is None else " (unresolved)")

    def short_version(goal_exceptions):
        sv = []
        if n_canon == 0:
            sv.append(f"The canon package (main {main10} plus the deb preset line TRON_AMX_DISPATCH=ON: the canonical AMX kernels of PR #3879, no PR #4424) has no completed config yet, and every canon cell below prints n/a (base and target are the 2026-09-18 ci-mimic arms).")
        else:
            A_loss = [r for r in A_sig if r["A"]["pct"] < 0]
            A_gain = [r for r in A_sig if r["A"]["pct"] > 0]
            if A_loss:
                loss_txt = f"lost TPS (decode tokens per second per user) by a resolved amount on {n_cfg(len(A_loss))} of {len(A_rows)}: " + ", ".join(f"{r['short']} {signed(r['A']['pct'])}" for r in A_loss)
            else:
                loss_txt = f"lost TPS (decode tokens per second per user) by a resolved amount on none of the {n_cfg(len(A_rows))}"
            gains = []
            for r in A_gain:
                g = f"gained {signed(r['A']['pct'])} on {r['short']}"
                if r is l8b and l8b_c:
                    g += f", where the probe counted {billions(l8b_c)} AMX-busy cycles in 20 s ({billions(l8b_b)} on base)"
                gains.append(g)
            gain_txt = (" and " + " and ".join(gains)) if gains else ""
            sv.append(f"Turning on the canonical AMX kernels of PR #3879 in the nightly package (canon against base{sofar}) {loss_txt}{gain_txt}.")
        q_bt = [r for r in qwen_rows if r.get("Bt")]
        q_a = [r for r in qwen_rows if r.get("A")]
        def marked(rs, ekey):
            marks = {res_mark(r[ekey]) for r in rs}
            if len(marks) == 1 and len(rs) > 1:
                return ", ".join(f"{tp_of(r)} {signed(r[ekey]['pct'])}" for r in rs) + f", {'both' if len(rs) == 2 else 'all'}{marks.pop()[:-1].replace(' (', ' ')}"
            return ", ".join(f"{tp_of(r)} {signed(r[ekey]['pct'])}{res_mark(r[ekey])}" for r in rs)
        if q_bt and q_a:
            bt_txt = marked(q_bt, "Bt")
            a_txt = marked(q_a, "A")
            sv.append(f"The qwen-3-4b TPS loss of issue #4500 appears when PR #4424 is added on top of canon (target against canon: {bt_txt}) and not when the canonical kernels alone are turned on (canon against base: {a_txt}).")
        elif not Bt_rows:
            sv.append("The target arm (PR #4424 merged into the same main, built with AMX on and VNNI-K on) against canon, the comparison that isolates what PR #4424 adds on top of canonical AMX, cannot be computed until canon has results.")
        else:
            parts = ", ".join(f"{r['short']} {signed(r['Bt']['pct'])}" for r in Bt_sig) or "none"
            sv.append(f"target (PR #4424 on top of canon) against canon shows a resolved TPS change on {len(Bt_sig)} of {n_cfg(len(Bt_rows))}{sofar}: {parts}.")
        if a.short3:
            sv.append(esc(a.short3))
        else:
            drops = sorted([r for r in A_rows if r["A"]["flag"] is False and r["A"]["pct"] <= -PCT_FLOOR], key=lambda r: r["A"]["pct"])
            cand = [r for r in Bt_sig if r not in qwen_rows and r["Bt"]["pct"] < 0]
            needs = []
            if drops:
                needs.append(f"the {'two' if len(drops) == 2 else len(drops)} unresolved canon drop{'s' if len(drops) != 1 else ''} (" + ", ".join(f"{r['short'].split(' @')[0]} {signed(r['A']['pct'])}" for r in drops) + ")")
            if cand:
                needs.append(f"the resolved target-against-canon loss{'es' if len(cand) != 1 else ''} outside qwen-3-4b (" + ", ".join(f"{r['short'].split(' @')[0]} {signed(r['Bt']['pct'])}" for r in cand) + f", {'candidate PR #4424 regressions' if len(cand) != 1 else 'a candidate PR #4424 regression'}, section 3)")
            if needs:
                sv.append(f"Every arm ran once (10 rounds per config, as in the nightly), and a repeat run is needed before {'these items are' if len(needs) > 1 else 'this item is'} accepted: " + " and ".join(needs) + ".")
            else:
                sv.append("Every arm ran once (10 rounds per config, as in the nightly), and every difference below a config's 13-night band counts as unresolved.")
        return sv

    def short_details(goal_exceptions):
        """the reading aids under the Short version box: package words, the resolved rule, the static-goal verdict, other resolved changes"""
        items = [f"Words: base = the nightly's own package of 2026-09-18 (no AMX code). canon = the same main commit {main10} plus the deb preset line TRON_AMX_DISPATCH=ON, built for this campaign. target = canon plus PR #4424 (the VNNI-K layout of the K cache) with TRON_K_VNNI=ON, from the 2026-09-18 ci-mimic campaign. Every term is defined under Words used here.",
                 "Resolved = a TPS difference that passes three tests (section 2): a paired t test over the 10 rounds with |t| &gt;= 2.26, a size of at least 1 %, and a size of at least the config's 13-night band (2 standard deviations of the last 13 nightlies)."]
        if n_canon and goal_exceptions is not None:
            if goal_exceptions:
                items.append("Static goals (section 5): canon passes every goal the same-day nightly passed, except " + "; ".join(goal_exceptions) + ".")
            else:
                items.append("Static goals (section 5): canon passes every goal the same-day nightly passed.")
        others = [r for r in Bt_sig if r not in qwen_rows and r["Bt"]["pct"] > 0]
        if others:
            items.append("Other resolved target-against-canon changes: " + ", ".join(f"{r['short']} {signed(r['Bt']['pct'])}" for r in others) + " (section 3).")
        return items

    # the start gap between base and canon goes into the pairing caveat of section 1 (one decimal, never rounded up)
    gap_txt = ""
    if base_rec and can_rec and epoch(base_rec.get("started") or "") and epoch(can_rec.get("started") or ""):
        h = (epoch(can_rec["started"]) - epoch(base_rec["started"])) / 3600.0
        gap_txt = f" canon started {h:.1f} hours after base, under a different client-load history."
    caveats_html = open(a.caveats).read() if a.caveats and os.path.exists(a.caveats) else ""
    notes_html = open(a.notes).read() if a.notes and os.path.exists(a.notes) else ""
    # The hand-written notes may carry placeholders for numbers this generator computes.
    ttft_vs_ngt = []
    for r in rows:
        if r.get("c") and r.get("n") and r["c"].get("ttft_mean") and r["n"].get("ttft_mean"):
            ttft_vs_ngt.append((r, pct(r["c"]["ttft_mean"], r["n"]["ttft_mean"])))
    within2 = [x for x in ttft_vs_ngt if abs(x[1]) <= 2.0]
    outside2 = sorted([x for x in ttft_vs_ngt if abs(x[1]) > 2.0], key=lambda x: -abs(x[1]))
    ttft_txt = (f"canon TTFT is within 2 % of the same-day nightly on {len(within2)} of {len(ttft_vs_ngt)} configs."
                + (f" The {n_cfg(len(outside2))} outside: " + ", ".join(f"{r['short'].split(' @')[0]}{' @4u' if r['key'] == ('llama-3.3-70b-instruct-good-tp2', 4) else ''} {signed(d)} ({fmt(r['c']['ttft_mean'], 0)} against {fmt(r['n']['ttft_mean'], 0)} ms)" for r, d in outside2) + "." if outside2 else "")) if ttft_vs_ngt else "n/a"

    def minutes_num(rec, ngt=False):
        if not rec:
            return None
        if ngt:
            st, en = epoch(rec.get("perf_phase_start") or ""), epoch(rec.get("perf_phase_end") or "")
            return (en - st) / 60.0 if st and en else None
        return rec.get("perf_minutes")

    mins = {"canon": minutes_num(can_rec), "base": minutes_num(base_rec), "target": minutes_num(tgt_rec), "nightly": minutes_num(ngt_rec, True)}
    fills = {"{{ttft_vs_nightly}}": ttft_txt,
             "{{canon_minutes}}": fmt(mins["canon"], 1), "{{base_minutes}}": fmt(mins["base"], 1), "{{target_minutes}}": fmt(mins["target"], 1),
             "{{nightly_minutes}}": fmt(mins["nightly"], 1),
             "{{canon_vs_nightly_minutes_pct}}": (f"{pct(mins['canon'], mins['nightly']):.1f}" if mins["canon"] and mins["nightly"] else "n/a"),
             "{{canon_psi_max}}": (f"{cc['psi'][1]:.1f}" if cc and cc.get("psi") else "n/a"),
             "{{canon_psi_min}}": (f"{cc['psi'][0]:.1f}" if cc and cc.get("psi") else "n/a")}
    for k, v in fills.items():
        notes_html = notes_html.replace(k, v)

    # ---- tables
    def tr(cells, cls=""):
        return f'<tr class="{cls}">' + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    def tps_cell(arm):
        if not arm:
            return "n/a"
        return fmt(arm["tps_mean"]) if arm["tps_mean"] else "failed"

    def ttft_cell(arm):
        return fmt(arm["ttft_mean"], 0) if arm and arm.get("ttft_mean") else "n/a"

    def mark(flag, has_value):
        """' *' = resolved, ' (n/t)' = not testable (no paired t), '' otherwise."""
        if not has_value:
            return ""
        return " *" if flag else (" (n/t)" if flag is None else "")

    short_series = [(r["short"].split(" @")[0], r["band"]["n"]) for r in rows if r.get("band") and r["band"]["n"] < 13]
    short_series_txt = (", " + ", ".join(f"{n} nights for {nm}" for nm, n in short_series)) if short_series else ""

    def nights_txt(r):
        return f" ({r['band']['n']} nights)" if r.get("band") and r["band"]["n"] < 13 else ""

    def eff_table(ekey, ref_key, arm_key, ref_name, arm_name):
        h = (f'<table><thead><tr><th>config</th><th>{ref_name} TPS</th><th>{arm_name} TPS</th><th>{arm_name} vs {ref_name}</th>'
             f'<th>95 % interval (paired rounds)</th><th>paired t</th><th>13-night TPS band (2 sd, recomputed from the nightly values{short_series_txt})</th>'
             f'<th>{ref_name} TTFT ms</th><th>{arm_name} TTFT ms</th><th>TTFT delta</th><th>TTFT paired t</th></tr></thead><tbody>')
        out = [h]
        for r in rows:
            e = r.get(ekey) or {}
            out.append(tr([
                esc(r["short"]), tps_cell(r.get(ref_key)), tps_cell(r.get(arm_key)),
                signed(e.get("pct")) + mark(e.get("flag"), e.get("pct") is not None),
                (f"&#177;{e['ci_pct']:.1f} %" if e.get("ci_pct") is not None else "n/a"), tstr(e.get("paired")),
                (f"&#177;{e['band_pct']:.1f} %" + nights_txt(r) if e.get("band_pct") is not None else "n/a"),
                ttft_cell(r.get(ref_key)), ttft_cell(r.get(arm_key)),
                signed(e.get("ttft_pct")) + mark(e.get("ttft_flag"), e.get("ttft_pct") is not None), tstr(e.get("ttft_paired"))],
                "flag" if e.get("flag") else ""))
        out.append("</tbody></table>")
        return "".join(out)

    tableA = eff_table("A", "b", "c", "base", "canon")
    tableB = eff_table("Bt", "c", "t", "canon", "target")

    def cell3(e):
        if not e:
            return "n/a"
        return signed(e["pct"]) + mark(e["flag"], e.get("pct") is not None)

    summary = ['<table><thead><tr><th>config</th><th>canon vs base (effect A)</th><th>target vs base (2026-09-18 report)</th><th>target vs canon (effect B)</th></tr></thead><tbody>']
    for r in rows:
        summary.append(tr([esc(r["short"]), cell3(r.get("A")), cell3(r.get("D")), cell3(r.get("Bt"))],
                          "flag" if (r.get("A") or {}).get("flag") or (r.get("Bt") or {}).get("flag") else ""))
    summary.append("</tbody></table>")

    def verdict(arm, k):
        g = GOALS.get(k, (None, None))
        if not arm or arm.get("tps_mean") is None:
            return "n/a"
        if g[0] is None:
            return "no threshold"
        ok = arm["tps_mean"] >= g[0] and arm["min"] >= g[1]
        why = []
        if arm["tps_mean"] < g[0]:
            why.append(f"mean {fmt(arm['tps_mean'])} &lt; {g[0]:.0f}")
        if arm["min"] < g[1]:
            why.append(f"slowest {fmt(arm['min'])} &lt; {g[1]:.0f}")
        return ("PASS" if ok else "FAIL: " + " and ".join(why))

    thr_table = ['<table><thead><tr><th>config</th><th>goal mean / slowest TPS</th><th>nightly 09-18</th><th>base</th><th>canon</th><th>target</th></tr></thead><tbody>']
    for r in rows:
        g = GOALS.get(r["key"], (None, None))
        thr_table.append(tr([esc(r["short"]), (f"{g[0]:.0f} / {g[1]:.0f}" if g[0] else "placeholder goal (1.00 TPS, no real threshold yet)"),
                             verdict(r["n"], r["key"]), verdict(r["b"], r["key"]), verdict(r["c"], r["key"]), verdict(r["t"], r["key"])]))
    thr_table.append("</tbody></table>")
    goal_exc = []
    for r in rows:
        vn, vc = verdict(r["n"], r["key"]), verdict(r["c"], r["key"])
        if vn == "PASS" and vc.startswith("FAIL"):
            vb = verdict(r["b"], r["key"])
            goal_exc.append(f"{r['short'].split(' @')[0]} ({vc[6:].replace('&lt;', 'against')} TPS" + (f", base {fmt(r['b']['min']) if 'slowest' in vc else fmt(r['b']['tps_mean'])}" if r.get("b") and r["b"].get("tps_mean") else "") + ")")
    sv = short_version(goal_exc if n_canon else None)
    sv_details = short_details(goal_exc if n_canon else None)

    # ---- charts
    def pct_rows(ekey, ref_key, arm_key, ref_name, arm_name, ttft=False):
        out = []
        for r in rows:
            e = r.get(ekey) or {}
            ref, arm = r.get(ref_key), r.get(arm_key)
            if ttft:
                tip = (f"{ref_name} {fmt(ref['ttft_mean'], 0)} ms, {arm_name} {fmt(arm['ttft_mean'], 0)} ms" if ref and arm and ref.get("ttft_mean") and arm.get("ttft_mean") else "")
                out.append({"label": r["short"], "pct": e.get("ttft_pct"), "ci_pct": e.get("ttft_ci_pct"), "flag": e.get("ttft_flag"), "tip": tip})
            else:
                tip = (f"{ref_name} {fmt(ref['tps_mean'])} TPS, {arm_name} {fmt(arm['tps_mean'])} TPS, paired t {tstr(e.get('paired'))}" if e else "")
                out.append({"label": r["short"], "pct": e.get("pct"), "ci_pct": e.get("ci_pct"), "flag": e.get("flag"), "tip": tip})
        return out

    any_nt = any((r.get(k) or {}).get("flag") is None and (r.get(k) or {}).get("pct") is not None for r in rows for k in ("A", "Bt"))
    any_nodata = any(r.get("A") is None or r.get("Bt") is None for r in rows)
    nt_txt = " n/t = not testable (no per-round data)." if any_nt else ""
    nodata_txt = " A row that says no data has no canon result yet." if any_nodata else ""
    rule_txt = f"* = resolved: |t| >= 2.26 over the 10 paired round means, |delta| >= 1 %, and |delta| at least the config's 13-night band (2 sd).{nt_txt}"
    chartA = chart_pct(pct_rows("A", "b", "c", "base", "canon"), "Effect A: canon TPS relative to base",
                       f"Dot = canon (canonical AMX kernels, no PR #4424) against base (no AMX code), in percent. Whisker = 95 % confidence interval from the paired round means. {rule_txt}{nodata_txt}",
                       "canon minus base, percent of base", C_CANON)
    # TTFT rows that involve base are not attributed to the package for the configs whose base TTFT differs from the
    # same-day nightly by more than 5 % (a client stall of tens of ms shows only on short TTFTs; the rule selects the
    # three configs the 2026-09-18 report named: llama-3b, llama-8b, qwen-3-4b tp2).
    TTFT_RULE_PCT = 5.0
    ttft_bad = [r for r in rows if r.get("b") and r.get("n") and r["b"].get("ttft_mean") and r["n"].get("ttft_mean")
                and abs(pct(r["b"]["ttft_mean"], r["n"]["ttft_mean"])) > TTFT_RULE_PCT]
    ttft_bad_names = ", ".join(r["short"].split(" @")[0] for r in ttft_bad) or "no config"
    ttft_rule_txt = f"the {n_cfg(len(ttft_bad))} whose base TTFT differs from the same-day nightly by more than {TTFT_RULE_PCT:.0f} % ({ttft_bad_names})"
    if cc and cc.get("psi") and cc["psi"][1] < 10.0:
        client_txt = f"The base arm ran under a CPU-saturated client host and canon on an idle one (section 1). The rows for {ttft_bad_names} therefore compare unlike client conditions."
    elif cc and cc.get("psi"):
        client_txt = f"The base arm ran under a CPU-saturated client host. The client conditions of canon are in section 1. The rows for {ttft_bad_names} may compare unlike client conditions."
    else:
        client_txt = "The base arm ran under a CPU-saturated client host (section 1). The client conditions of canon are not recorded yet."
    chartA_ttft = chart_pct(pct_rows("A", "b", "c", "base", "canon", ttft=True), "Effect A: canon TTFT relative to base",
                            f"Time to first token, mean over users and rounds. Negative = faster. Whisker = 95 % CI over paired rounds. The axis stops at 25 %. {client_txt}",
                            "canon minus base, percent of base", C_CANON, clip=25)
    chartB = chart_pct(pct_rows("Bt", "c", "t", "canon", "target"), "Effect B: target TPS relative to canon",
                       f"Dot = target (PR #4424 on the same main and preset line) against canon, in percent. The code difference is PR #4424 as a package, plus TRON_K_VNNI=ON in the preset line. Whisker = 95 % confidence interval from the paired round means. {rule_txt}",
                       "target minus canon, percent of canon", C_TARGET)
    tgt_hi_txt = (f" The target arm ran {ranges_text(ct['hi'])} under a CPU-saturated client host (section 1). Those rows therefore compare unlike client conditions." if ct and ct.get("hi") else "")
    chartB_ttft = chart_pct(pct_rows("Bt", "c", "t", "canon", "target", ttft=True), "Effect B: target TTFT relative to canon",
                            f"Time to first token, mean over users and rounds. Negative = faster. Whisker = 95 % CI over paired rounds. The axis stops at 25 %.{tgt_hi_txt}",
                            "target minus canon, percent of canon", C_TARGET, clip=25)
    c4_rows = [{"label": r["short"], "nightly": r["n"]["tps_mean"] if r.get("n") else None, "base": r["b"]["tps_mean"] if r.get("b") else None,
                "canon": r["c"]["tps_mean"] if r.get("c") else None, "target": r["t"]["tps_mean"] if r.get("t") else None,
                "band": (r["band"]["min"], r["band"]["max"]) if r.get("band") else None, "unit": "TPS"} for r in rows]
    chart4 = chart_abs(c4_rows, "Absolute TPS per config: nightly, base, canon, target",
                       "Tokens per second per user, mean over users and rounds. The solid connector (upper lane, base to canon) is the change the canonical AMX package makes. The dashed connector (lower lane, canon to target) is the change PR #4424 adds on top.",
                       [("nightly", C_NIGHTLY, "nightly 09-18"), ("base", C_BASE, "base"), ("canon", C_CANON, "canon"), ("target", C_TARGET, "target")],
                       [("base", "canon", None), ("canon", "target", "5 4")],
                       "Each row has its own scale (units differ 12x between configs). Gray band = 13-night min to max of the nightly (3 nights for gemma-4-31b). Gray ring = the 2026-09-18 nightly, blue = base, green = canon, orange = target. Every dot is labelled with its value.")

    # ---- section 1: the arms table and the pairing caveat
    def opt_text(man, default):
        if man and man.get("options"):
            return ", ".join(f"{k}={v}" for k, v in man["options"].items())
        return default

    def minutes_of(rec, ngt=False):
        if not rec:
            return "n/a"
        if ngt:
            s, e = epoch(rec.get("perf_phase_start") or ""), epoch(rec.get("perf_phase_end") or "")
            return fmt((e - s) / 60.0, 1) if s and e else "n/a"
        return fmt(rec.get("perf_minutes"), 1) if rec.get("perf_minutes") is not None else ("running" if rec.get("started") else "n/a")

    def main_cell(ver):
        """the main commit at one length for every row: the manifest's 10 characters when the deb version names the same commit"""
        mv = main_of_version(ver)
        return main10 if (mv and main_sha.startswith(mv)) else (mv or "n/a")

    if not can_rec:
        can_src = "this campaign, not started"
    elif can_rec.get("started") and not can_rec.get("finished"):
        can_src = f"this campaign, running, {n_canon} of {N_CONFIGS} configs finished"
    else:
        can_src = "this campaign" + (f", {n_canon} of {N_CONFIGS} configs completed" if canon_partial else "")
    arms_table = ['<table><thead><tr><th>arm</th><th>tron package</th><th>main commit</th><th>build options beyond the nightly deb preset</th><th>perf phase window (UTC)</th><th>client host</th><th>client 1-min load, min to max</th><th>client CPU PSI (some, avg10), min to max</th><th>perf minutes</th><th>source</th></tr></thead><tbody>']
    arms_table.append(tr(["nightly (reference)", esc(ngt_ver), esc(main_cell(ngt_ver)), "none (the preset never compiled the AMX kernels)",
                          esc(window(ngt_rec, "perf_phase_start", "perf_phase_end")), "CI runner (no load record)", "n/a", "n/a", minutes_of(ngt_rec, True),
                          esc(f"nightly run {a.nightly_run_id}".strip() if a.nightly_run_id else "the 2026-09-18 nightly log")]))
    arms_table.append(tr(["base", esc(base_ver), esc(main_cell(base_ver)), "none (no AMX code)", esc(window(base_rec)),
                          esc((base_rec or {}).get("client_host", "n/a")), esc(load_text(cb)), esc(psi_text(cb)), minutes_of(base_rec),
                          "2026-09-18 ci-mimic base arm, not re-run"]))
    arms_table.append(tr(["canon", esc(can_ver), esc(main10 if manifest else "n/a"), esc(opt_text(manifest, "TRON_AMX_DISPATCH=ON (from the campaign design, manifest missing)")),
                          esc(window(can_rec)), esc((can_rec or {}).get("client_host", "n/a")), esc(load_text(cc)), esc(psi_text(cc)), minutes_of(can_rec),
                          can_src]))
    arms_table.append(tr(["target", esc(tgt_ver), esc(((tmanifest or {}).get("main_sha") or "")[:10] or "n/a"), esc(opt_text(tmanifest, "TRON_AMX_DISPATCH=ON, TRON_K_VNNI=ON (from the 2026-09-18 report, manifest missing)")),
                          esc(window(tgt_rec)), esc((tgt_rec or {}).get("client_host", "n/a")), esc(load_text(ct)), esc(psi_text(ct)), minutes_of(tgt_rec),
                          "2026-09-18 ci-mimic target arm, not re-run"]))
    arms_table.append("</tbody></table>")

    # the pairing caveat, with the load numbers computed from each record
    def hi_text(c):
        if not c or not c.get("per_config") or c.get("psi") is None:
            return None
        hi = c["hi"]
        if not hi:
            return f"PSI {c['psi'][0]:.0f} to {c['psi'][1]:.0f} % at the start of every config"
        hi_vals = [p for i, _, p in c["per_config"] if i in hi]
        rest = c["lo_rest"]
        txt = f"PSI {min(hi_vals):.0f} to {max(hi_vals):.0f} % at the start of {ranges_text(hi)}"
        if rest:
            txt += f" and {min(rest):.0f} to {max(rest):.0f} % at the start of the others"
        return txt

    def load_sentence(c):
        if not c or not c.get("load"):
            return "Its record has no client load."
        return f"The 1-minute load average at its {c['n']} snapshots was {c['load'][0]:.1f} to {c['load'][1]:.1f} on a 32-CPU host."

    base_cav = ("base ran under a CPU-saturated client host. Its record has no PSI (Pressure Stall Information, the share of time at least one task waited for a CPU). "
                f"A hand-recorded spot check at 14:52 UTC showed PSI some 93 % (the 2026-09-18 ci-mimic caveats). {load_sentence(cb)}")
    tgt_cav = f"target ran under {hi_text(ct) or 'an unrecorded client load'}." if ct else "target has no client record."
    if cc and cc.get("psi"):
        idle = cc["psi"][1] < 10.0
        can_cav = (f"canon ran on an idle client: PSI {cc['psi'][0]:.0f} to {cc['psi'][1]:.0f} %. {load_sentence(cc)}"
                   if idle else f"canon did not run on an idle client: {hi_text(cc)}. {load_sentence(cc)}")
    elif cc:
        can_cav = f"canon's record has no PSI yet. {load_sentence(cc)}"
    else:
        can_cav = "canon has not run yet. Its client conditions are unknown."
    can_cav += gap_txt
    if fid:
        fid_sorted = sorted(((abs(r["fid_pct"]), r["short"]) for r in rows if r.get("fid_pct") is not None), reverse=True)
        fid_cav = f"TPS means were robust to that load. base was within {fid_sorted[0][0]:.1f} % of the same-day nightly on all {len(fid)} configs"
        if len(fid_sorted) > 1:
            fid_cav += f", and within {fid_sorted[1][0]:.1f} % on every config but {fid_sorted[0][1]}"
        fid_cav += "."
    else:
        fid_cav = "The base-vs-nightly TPS check is not available (no nightly record)."
    ttft_cav = f"TTFT (time to first token) is not robust to client load. TTFT comparisons that involve base cannot be attributed to the package for {ttft_rule_txt}."
    pairing = "<p><b>Pairing caveat.</b></p><ul>" + "".join(f"<li>{x}</li>" for x in (base_cav, tgt_cav, can_cav, fid_cav, ttft_cav)) + "</ul>"

    deviations = (can_rec or base_rec or {}).get("deviations") or []
    dev_html = "".join(f"<li>{esc(d)}</li>" for d in deviations)
    dev_src = "canon" if (can_rec or {}).get("deviations") else ("base" if deviations else "no")
    dev_lead = "<p>The items below are the driver's own wording." + (" positron = the user account the nightly's ssh uses." if any("positron" in d for d in deviations) else "") + "</p>"

    # ---- evidence
    def probes(rec):
        return [(p["model"], p.get("amx_busy_cycles")) for p in (rec or {}).get("amx_probes") or []]

    def probe_text(rec):
        if rec is None:
            return "n/a"
        return esc(", ".join(f"{m.split('-instruct')[0]}: {c:,}" if c is not None else f"{m}: n/a" for m, c in probes(rec)) or "no probe")

    short_of = {m: s.split(" @")[0] for m, u, s, n in ORDER}

    def engines_text(f):
        if not f:
            return "n/a"
        return esc(", ".join(f"{short_of.get(m, m)} {x}/{y}" for m, x, y in f.get("engine_counts", [])) or "n/a")

    def cpt_text(rec):
        if not rec:
            return "n/a"
        c = rec.get("client_path_timing") or {}
        return esc(f"{c.get('namelookup_ms_median', 'n/a')} / {c.get('connect_ms_median', 'n/a')} / {c.get('total_ms_median', 'n/a')}")

    def na(f, key):
        return str(f.get(key, "n/a")) if f else "n/a"

    def sha16(f):
        return (esc(f["rinzler_sha"][:16]) + "&#8230;") if f and f.get("rinzler_sha") else "n/a"

    def host_started(rec):
        return esc(f"{rec.get('client_host', '?')} / {rec.get('started', '?')}") if rec else "n/a"

    def psi_per_config(c):
        if not c or not c.get("per_config"):
            return "n/a"
        vals = [f"{p:.0f}" if p is not None else "-" for _, _, p in c["per_config"]]
        psi = f"PSI {psi_text(c)}" if c.get("psi") else "no PSI record"
        return esc(f"load {load_text(c)}, {psi}" + (f", PSI at the start of each config: {' '.join(vals)}" if any(p is not None for _, _, p in c['per_config']) else ""))

    ev = ['<table><thead><tr><th>check</th><th>base</th><th>canon</th><th>target</th></tr></thead><tbody>']
    ev.append(tr(["tron package serving", esc(base_ver), esc(can_ver if can_rec else "n/a"), esc(tgt_ver)]))
    ev.append(tr(["rinzler sha256 on disk", sha16(fb), sha16(fc), sha16(ft)]))
    ev.append(tr(["engines running after each provisioning (running/planned)", engines_text(fb), engines_text(fc), engines_text(ft)]))
    ev.append(tr(["snapshots showing an engine on a deleted (replaced on disk) binary", na(fb, "deleted"), na(fc, "deleted"), na(ft, "deleted")]))
    def exe_cell(f):
        if not f or not f.get("exe_snapshots"):
            return "n/a"
        txt = f"{f['exe_mismatch']} of {f['exe_checked']} engine pids differ ({f['exe_snapshots']} snapshots)"
        if f["exe_mismatch_tags"]:
            txt += ": " + ", ".join(short_of.get(m, m) for m in f["exe_mismatch_tags"])
        return esc(txt)
    ev.append(tr(["engines whose running binary (sha256 of /proc/pid/exe) differs from the package on disk, after provisioning (must be 0)",
                  exe_cell(fb), exe_cell(fc), exe_cell(ft)]))
    ev.append(tr(["AMX-busy cycles in a 20 s probe (EXE.AMX_BUSY, all engine pids)", probe_text(base_rec), probe_text(can_rec), probe_text(tgt_rec)]))
    ev.append(tr(["hand edit in rinzler@.service (--num-expert-replicas count)", na(fb, "unit_count"), na(fc, "unit_count"), na(ft, "unit_count")]))
    ev.append(tr(["USE_HW_ATTN / TRON_AMX_* / TRON_K_VNNI in engine env files (matching lines per file, must be 0)", esc(fb.get("env_vars") or "n/a") if fb else "n/a", esc(fc.get("env_vars") or "n/a") if fc else "n/a", esc(ft.get("env_vars") or "n/a") if ft else "n/a"]))
    def sst_text(f):
        if not f or not f.get("sst"):
            return "n/a"
        m = re.search(r"clos0=(\d+) clos3=(\d+)", f["sst"])
        return esc(f"verified: clos0 = {m.group(1)} cores (high priority), clos3 = {m.group(2)} cores" if m else f["sst"])

    def dut_load_text(f):
        if not f or not f.get("dut_load"):
            return "n/a"
        return f"{min(f['dut_load']):.0f} to {max(f['dut_load']):.0f} ({len(f['dut_load'])} snapshots)"

    ev.append(tr(["Intel Speed Select policy (clos = class of service, a core-priority group, counted in cores)", sst_text(fb), sst_text(fc), sst_text(ft)]))
    ev.append(tr(["DUT 1-min load average across snapshots (4 idle engines alone give about 125: their worker threads spin)", dut_load_text(fb), dut_load_text(fc), dut_load_text(ft)]))
    ev.append(tr(["client to proxy: DNS / connect / full GET, median ms", cpt_text(base_rec), cpt_text(can_rec), cpt_text(tgt_rec)]))
    ev.append(tr(["perf phase wall time, minutes (nightly 09-18: " + minutes_of(ngt_rec, True) + ")", minutes_of(base_rec), minutes_of(can_rec), minutes_of(tgt_rec)]))
    ev.append(tr(["client host / started (UTC)", host_started(base_rec), host_started(can_rec), host_started(tgt_rec)]))
    ev.append(tr(["client 1-min load and CPU PSI (some avg10, %) across snapshots", psi_per_config(cb), psi_per_config(cc), psi_per_config(ct)]))
    ev.append("</tbody></table>")

    def man_table(man):
        return "<table><tbody>" + "".join(f"<tr><td>{esc(k)}</td><td><code>{esc(v if not isinstance(v, dict) else json.dumps(v))}</code></td></tr>" for k, v in man.items()) + "</tbody></table>"

    man_rows = man_table(manifest) if manifest else ""
    tman_rows = man_table(tmanifest) if tmanifest else ""
    man_html = (('<h3>Package manifest of canon (from the campaign preflight)</h3><p>checks = counts the build script found in the packaged rinzler binary '
                 '(literal strings and AMX tile instructions). options = the CMake options the preset line adds. Other keys are the git commits and the package file.</p>'
                 '<div class="tw">' + man_rows + '</div>') if man_rows else f"<p>Package manifest of canon: {manifest_na}.</p>")
    tman_html = (('<h3>Package manifest of target (from the 2026-09-18 ci-mimic preflight)</h3><p>pr_sha = the PR #4424 head that was measured, merge_sha = its merge into main, '
                  'head_sha = the package\'s commit.</p><div class="tw">' + tman_rows + '</div>') if tman_rows else "<p>Package manifest of target: n/a (the ci-mimic preflight was not available).</p>")

    # the deleted-binary snapshots, resolved against the sha of the arm's own rinzler (the exe sha is the first 16 hex of the sha256)
    def deleted_note(name, f, own_sha, other):
        """other = {sha16: package name} of the packages a stale engine could still run."""
        if not f or not f.get("deleted_detail"):
            return None
        parts = []
        for d in f["deleted_detail"]:
            shas = d["exe_shas"]
            what = ", ".join((f"the {other[x]} rinzler" if x in other else (f"the {name} rinzler itself" if own_sha and own_sha.startswith(x) else "an unknown binary")) + f" (sha256 {x}...)" for x in shas) or "no exe sha recorded"
            tag = d["tag"] if d["tag"] != "before" else '"before" (pre-provisioning)'
            models = ", ".join(short_of.get(m, m) for m in d["models"]) or "unknown model"
            parts.append(f"In {name}, the {tag} snapshot at {d['time']} UTC shows {d['pids']} engine pids ({models}) on {what}.")
        return " ".join(parts)

    known = {}
    for nm, f in (("nightly", fb), ("canon", fc), ("target", ft)):
        if f and f.get("rinzler_sha"):
            known[f["rinzler_sha"][:16]] = nm  # base's disk sha is the nightly package's
    del_notes = [x for x in (deleted_note("base", fb, (fb or {}).get("rinzler_sha"), known), deleted_note("canon", fc, (fc or {}).get("rinzler_sha"), known),
                             deleted_note("target", ft, (ft or {}).get("rinzler_sha"), known)) if x]

    def probe_pair(prefix):
        c, t = probe_of(can_rec, prefix), probe_of(tgt_rec, prefix)
        return (c, t, pct(t, c)) if c and t else None

    q_probe = probe_pair("ingested-qwen-3-4b")
    probe_note = ""
    if q_probe and abs(q_probe[2]) >= 10:
        probe_note = (f"<li>target counted {abs(q_probe[2]):.0f} % {'more' if q_probe[2] > 0 else 'fewer'} AMX-busy cycles than canon on qwen-3-4b tp2 ({billions(q_probe[1])} against {billions(q_probe[0])} in 20 s). "
                      "The cause is not measured here. Candidates: the pre-packed K of PR #4424 removes the pack step and the kernel runs more often, or the two probe windows caught different request phases.</li>")

    # machine handling of the canon run, from the campaign log, bill-share.log and the preflight (all optional)
    def first_line(path, pat, after=None, before=None):
        try:
            for l in open(path, errors="replace"):
                ts = l[:20]
                if pat in l and (after is None or ts >= after) and (before is None or ts <= before):
                    return l.rstrip()
        except Exception:
            return None
        return None

    def last_line(path, pat, before=None):
        out = None
        try:
            for l in open(path, errors="replace"):
                if pat in l and (before is None or l[:20] <= before):
                    out = l.rstrip()
        except Exception:
            return None
        return out

    def hhmmss(iso):
        m = re.search(r"(\d\d:\d\d:\d\d)", iso or "")
        return m.group(1) if m else "?"

    can_start = (can_rec or {}).get("started") or ""
    lease_l = first_line(a.campaign_log, "CI lease free") if a.campaign_log else None
    flock_l = first_line(a.campaign_log, "flock released", after=can_start or None) if a.campaign_log else None
    take_l = last_line(a.bill_log, "take:", before=can_start or None) if (a.bill_log and can_start) else None
    rel_l = first_line(a.bill_log, "release:", after=can_start or None) if (a.bill_log and can_start) else None
    pre_time = (re.search(r"== time (\S+)", pre) or [None, None])[1] if pre else None
    pre_marker = (re.search(r"== bill marker: (\S+)", pre) or [None, None])[1] if pre else None
    pre_flock = (re.search(r"== campaign flock: (\S+)", pre) or [None, None])[1] if pre else None
    machine_bits = []
    if lease_l:
        machine_bits.append(f"the CI lease was free at {hhmmss(lease_l[:20])} UTC (the one check the campaign made)")
    if take_l:
        machine_bits.append(f"Bill's marker was taken by launch.sh at {hhmmss(take_l[:20])} UTC on jhan's order (Bill idle, the take step refuses otherwise)")
    if pre_marker and pre_time:
        machine_bits.append(f"the preflight at {hhmmss(pre_time)} UTC recorded the marker {pre_marker}" + (f" and the campaign flock {pre_flock}" if pre_flock else ""))
    if rel_l:
        machine_bits.append(f"the marker was re-created at {hhmmss(rel_l[:20])} UTC")
    if flock_l:
        machine_bits.append(f"the flock was released at {hhmmss(flock_l[:20])} UTC")
    machine_txt = ("canon: " + ", ".join(machine_bits) + ".") if machine_bits else "canon: the campaign log and bill-share.log were not available to this render."
    machine_txt += " base and target (2026-09-18 ci-mimic): the marker was removed at 01:10 UTC and re-created for good at 17:58 UTC, whole machine, details in that report."

    # canon and target identity in prose (from the manifests)
    def sha10(x):
        return (x or "")[:10] or "n/a"

    chk = (manifest or {}).get("checks") or {}
    canon_id = ""
    if manifest:
        canon_id = (f" canon = package {esc(can_ver)}, built {esc((manifest.get('built') or '?')[:16].replace('T', ' '))} UTC from branch {esc(manifest.get('branch') or '?')} at head {sha10(manifest.get('head_sha'))}"
                    f" = main {main10} plus commit {esc(manifest.get('preset_commit') or '?')} (the one-line deb preset change that sets TRON_AMX_DISPATCH=ON, the same commit pushed as branch jhan-amx-deb-preset)."
                    f" The build check found {chk.get('amx_tile_insns', '?')} AMX tile instructions and {chk.get('TRON_K_VNNI_literal', '?')} TRON_K_VNNI string in the packaged rinzler (sha256 {esc((fc or {}).get('rinzler_sha') or '')[:8]}...)."
                    " The nightly's rinzler has 0 AMX tile instructions (the 2026-09-16 check).")
    tchk = (tmanifest or {}).get("checks") or {}
    target_id = ""
    if tmanifest:
        target_id = (f" target adds PR #4424 at its head {sha10(tmanifest.get('pr_sha'))} (merge commit {sha10(tmanifest.get('merge_sha'))}, package head {sha10(tmanifest.get('head_sha'))}) and sets TRON_K_VNNI=ON in the same preset line."
                     f" The packaged rinzler has {tchk.get('amx_tile_insns', '?')} AMX tile instructions against canon's {chk.get('amx_tile_insns', '?')} (the VNNI-K kernels add tile code).")

    caveats_lead = ('<p>Generated for this campaign by exec/canon-ci-20260918/gen_caveats.py from the three run records, the four driver logs, '
                    'the canon campaign log and bill-share.log. It covers base, target and canon. The base and target numbers repeat the 2026-09-18 ci-mimic caveats.</p>')
    per_config_notes = "".join(f"<li><b>{esc(r['short'])}</b>: {esc(r['note'])}</li>" for r in rows)

    now = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Canonical AMX at the CI harness</title>
<style>
:root{{color-scheme:light;--ink:{INK};--ink2:{INK2};--muted:{MUTED};--grid:{GRID};--surf:{SURF};--page:#f9f9f7;--base:{C_BASE};--canon:{C_CANON};--target:{C_TARGET};--nightly:{C_NIGHTLY}}}
html,body{{background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Segoe UI",sans-serif;margin:0}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:24px;margin:0 0 4px}} h2{{font-size:18px;margin:36px 0 8px;border-bottom:1px solid var(--grid);padding-bottom:4px}} h3{{font-size:15px;margin:20px 0 6px}}
p,li{{line-height:1.45;font-size:14px}} .sub{{color:var(--ink2);font-size:13px}}
.short{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:12px 16px;margin:16px 0}}
.short p{{margin:6px 0}}
table{{border-collapse:collapse;font-size:12.5px;margin:8px 0 16px;background:var(--surf)}} th,td{{border:1px solid var(--grid);padding:4px 8px;text-align:left;vertical-align:top}} th{{color:var(--ink2);font-weight:600}}
td:nth-child(n+2){{font-variant-numeric:tabular-nums}} tr.flag td{{background:#fff4ee}}
.fig{{background:var(--surf);border:1px solid var(--grid);border-radius:8px;padding:8px;margin:12px 0}} .fig svg{{width:100%;height:auto;display:block;margin:0 auto}}
.tw{{overflow-x:auto;margin:8px 0 16px}} .tw table{{margin:0}}
.legend{{font-size:12px;color:var(--ink2);margin:4px 0 8px}} .legend span{{margin-right:16px}} .legend i{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px;vertical-align:middle}}
.take{{font-size:13px;color:var(--ink2);margin:4px 0 0 8px}}
code{{font-size:12px;background:#f1f0ec;padding:1px 4px;border-radius:3px}}
.gloss dt{{font-weight:600;font-size:13px;margin-top:6px}} .gloss dd{{margin:0 0 0 16px;font-size:13px;color:var(--ink2)}}
</style></head><body><main>
<h1>{esc(a.title)}</h1>
<p class="sub">delphi-3bda, whole machine, 2026-09-18/19. Generated {now} by exec/canon-ci-20260918/gen_report.py from the run records.</p>

<div class="short"><h2 style="margin-top:0;border:0">Short version</h2>
{"".join(f"<p>{s}</p>" for s in sv)}
</div>
<ul class="take">{"".join(f"<li>{x}</li>" for x in sv_details)}</ul>

<h2>Words used here</h2>
<dl class="gloss">
<dt>nightly, CI, systems_test, CI runner</dt><dd>CI = continuous integration, the automated nightly test job. The nightly is the systems_test job "System CI (Rinzler 72-core Intel system OCI version)" that runs on delphi-3bda (the 72-core Intel Granite Rapids test machine) every night at 03:30 UTC. systems_test is the repository that holds the system tests. The CI runner is the machine that runs the nightly's client code. This page repeats the nightly's perf phase by hand.</dd>
<dt>arm, config</dt><dd>An arm is one package under test (base, canon or target), run once through all configs. A config is one row of the nightly's perf list: a model, its tensor-parallel width and a user count, for example llama-3.1-8b good tp2 @8u.</dd>
<dt>harness</dt><dd>The nightly's client code (systems_test scripts/perf.py and testlib/tps.py). It provisions each model, starts the users' requests, and computes TPS (decode tokens per second per user) and TTFT (time to first token). The same code produced every number here.</dd>
<dt>snapshot</dt><dd>One record of the machine's engine layout, the running binaries and the client load, taken by our driver before the run, after each provisioning and after the run (14 per arm). The per-config client numbers on this page come from the after-provisioning snapshot of that config.</dd>
<dt>good, fast (config labels)</dt><dd>The nightly's own labels for a model's serving profile, part of the model name platformd provisions (for example llama-3.1-8b-instruct-good). What each profile selects is not recorded here.</dd>
<dt>platformd, rinzler@N, engine, Caddy</dt><dd>platformd is the daemon on the machine that writes one env file per engine and starts the rinzler@N systemd units. rinzler is the production tron server (tron = the inference program under test), and one running rinzler is one engine. Caddy is the port-80 proxy in front of the engines. It sends each new user to the engine with the fewest connections.</dd>
<dt>deb, preset, PR, main</dt><dd>The deb is the tron apt package the nightly installs. The preset is the CMake build recipe ("deb") that builds it. PR = pull request. main = the main branch of the tron repository. All three arms are built from main commit {esc(main10)}, the commit of the nightly's deb of 2026-09-18.</dd>
<dt>PR #3879, canonical AMX</dt><dd>PR #3879 added the AMX attention kernels to tron. It was merged into main on 2026-09-15. Its kernels are compiled only when the CMake option TRON_AMX_DISPATCH is ON. The nightly deb preset never sets it. "Canonical" means these kernels as merged, with the K cache in its original layout.</dd>
<dt>PR #4424, VNNI, VNNI-K</dt><dd>VNNI = Vector Neural Network Instructions. The VNNI layout is the pair-interleaved data format those instructions and the AMX tile products read (two consecutive tokens side by side). VNNI-K = the K cache stored in that layout. PR #4424 (branch jhan-amx-vnniK) adds that layout and the CMake option TRON_K_VNNI. It is not merged. It also changes gof::populate (the copy of K to the FPGA) and the dispatch code.</dd>
<dt>issue #4500</dt><dd>The GitHub issue in positron-ai/tron, filed 2026-09-18: qwen-3-4b loses 5 to 11 % TPS with PR #4424 under FPGA attention (tp2 and tp4). This page's effect B on the two qwen-3-4b rows is the same loss.</dd>
<dt>dispatch gate</dt><dd>The run-time check in tron that decides, per model, whether attention takes the AMX kernel (head size, kv_mul, CPU attention). A package effect on a control config could come from this check rather than from the kernel.</dd>
<dt>base</dt><dd>The package the nightly installed on 2026-09-18 ({esc(base_ver)}). Its source contains PR #3879. The deb preset left TRON_AMX_DISPATCH off. The package therefore has no AMX code. Measured in the ci-mimic campaign of 2026-09-18 and not re-run here.</dd>
<dt>canon</dt><dd>Our package {esc(can_ver)}: main {esc(main10)} plus one commit that adds TRON_AMX_DISPATCH=ON to the deb preset. It contains the canonical AMX kernels of PR #3879 and no PR #4424 code. Run in this campaign.</dd>
<dt>target</dt><dd>Our package {esc(tgt_ver)}: PR #4424 (head {esc(((tmanifest or {}).get("pr_sha") or "")[:10] or "n/a")}, merge commit {esc(((tmanifest or {}).get("merge_sha") or "")[:10] or "n/a")}, package head {esc(((tmanifest or {}).get("head_sha") or "")[:10] or "n/a")}) merged into the same main commit, built with the deb preset carrying TRON_AMX_DISPATCH=ON and TRON_K_VNNI=ON. Measured in the ci-mimic campaign of 2026-09-18 and not re-run here.</dd>
<dt>effect A, effect B</dt><dd>Effect A = canon against base: what the canonical AMX kernels change. Effect B = target against canon: what PR #4424 adds on top of them. The 2026-09-18 report measured target against base, the two combined (the percentages compound, and the plain sum is only approximate).</dd>
<dt>AMX, K cache, KV head, kv_mul, head size</dt><dd>AMX = Intel Advanced Matrix Extensions, the tile matrix instructions of Granite Rapids CPUs. The AMX kernel accelerates software attention (attention computed on the CPU) for models with a head size of 128 elements and 4 query heads per KV head (kv_mul = 4). A KV head is one key/value head of attention that several query heads share. The K cache is the stored keys of all earlier tokens.</dd>
<dt>FPGA attention, CPU attention, CPU share, ingested, USE_HW_ATTN, HBM</dt><dd>Ingested models (models converted by tron's ingest compiler) run attention on the FPGA cards (Positron's accelerator cards) by default. Here that is qwen-3-4b and gpt-oss. gemma-4-31b is ingested but has no FPGA attention (head size 256). It therefore runs attention on the CPU. Hand-written models (models coded by hand in tron) run attention on the CPU, where AMX acts. The CPU share is the part of attention the CPU still computes under FPGA attention: positions 0 to 126 of each query and the most recent tokens not yet copied to HBM. USE_HW_ATTN is the environment variable that would force one or the other. It was unset, as in the nightly. HBM = the high-bandwidth memory on the FPGA card.</dd>
<dt>tp2, tp4, @Nu, round, prompt 1024</dt><dd>tp2 and tp4 = tensor-parallel width, the number of FPGA cards one engine uses (2 or 4). The machine's 8 cards therefore give 4 or 2 engines. @Nu = N concurrent users. A round is one pass in which every user sends one request. Every config runs 10 rounds with fixed prompts. Prompt 1024 = a prompt of 1024 tokens (llama-3b uses 800 shared plus 200 own prompt tokens).</dd>
<dt>TPS, TTFT, slowest user, prefill</dt><dd>TPS = decode tokens per second per user, measured between generated token 896 and 1024 (2 and 333 for llama-3b), mean over users and rounds. TTFT = time to first token in ms, measured on the client. Slowest user = the minimum TPS sample of a config. Prefill = processing the prompt before the first token.</dd>
<dt>paired t, 95 % interval, sd, 13-night band, Slack reports, resolved</dt><dd>Paired t = the mean of the 10 per-round differences divided by its standard error. The prompts are fixed. Round r of one run therefore pairs with round r of the other. The 95 % interval is the confidence interval of that mean. sd = standard deviation. The Slack reports are the summary messages the nightly posts to a Slack channel. The 13 reports of 2026-09-05 to 09-17 give each config a mean and sd. The band is 2 sd of those 13 nights, in percent of their mean. It is recomputed here from the 13 values. gemma-4-31b entered the nightly on 2026-09-15, so its band comes from 3 nights. The statistics file rounds sd to 2 decimals, and a check against that rounded field can therefore differ by up to 0.03 percentage points. A change is resolved when |t| &gt;= 2.26, |delta| &gt;= 1 % and |delta| is at least the band.</dd>
<dt>thresholds, granite_rapids_72_rinzler</dt><dd>The static goals are the mean-TPS and slowest-user limits the Slack report applies (from systems_test scripts/system_ci.py for the machine profile named granite_rapids_72_rinzler). The ratchet thresholds are a second set in YAML files that tightens over time. They are not shown in Slack.</dd>
<dt>EXE.AMX_BUSY probe</dt><dd>A 20 s read of the CPU counter EXE.AMX_BUSY, which counts cycles in which the AMX unit was busy, summed over all engine processes while 4 short requests run. It runs before the benchmark of the probed config. It therefore does not touch the measured rounds.</dd>
<dt>PSI, load average, DUT, sha256, ci-mimic, talos</dt><dd>PSI = Pressure Stall Information. Its "some" value is the share of time at least one task waited for a CPU. avg10 = its 10-second average. The load average is the number of runnable tasks, here on a 32-CPU client host. DUT = device under test, delphi-3bda. sha256 = a hash that identifies a file's content. ci-mimic = the 2026-09-18 campaign that produced the base and target arms. talos = the CI's metrics recorder, replaced here by a local stub.</dd>
<dt>marker, flock, lease, handoff, hugepages, ci-runner-stop timer</dt><dd>The marker is the file /bill-has-instance-0,2 on delphi-3bda that reserves the first half of the machine (the cards on socket 0) for Bill. The flock is the host-wide lock file /var/tmp/jhan/3bda-campaign.lock that lets only one of our campaigns run at a time. The lease is /run/lock/systems-test-ci.lease, which the nightly holds while it runs. The handoff is the end state this campaign leaves for the next one (here: production engines down, hugepages free). Hugepages are the 1 GiB memory pages the engines reserve (HugePages_Free = pages not in use). The ci-runner-stop timer is a systemd timer on delphi-3bda that brings production serving back at 02:45 UTC before the nightly (recorded in campaign.sh's header, not verified in this run).</dd>
</dl>

<h2>1. What ran</h2>
<ul>
<li><b>Machine and layout:</b> the whole of delphi-3bda for all three arms. Engines were created by platformd for every config exactly as in the nightly: 4 engines for tp2, 2 for tp4, users spread by Caddy. Machine handling (terms under Words used here): {machine_txt}</li>
<li><b>Client:</b> the harness's own <code>test_performance</code> loop, run by <code>st_ci_perf.py</code> from {esc((can_rec or base_rec or {}).get('client_host', 'the client host'))} (a container on the same network as the CI runner) with the same Python dependency lock file (uv.lock) as the CI runner, through <code>http://delphi-3bda.positron.internal/v1</code>. Speculative decoding (draft-token prediction) was off (SYSTEM_CI_SPECULATION=0), as in the nightly. Each config ran 10 rounds with prompt 1024 and 1536 generated tokens (llama-3b: 800 shared prompt tokens + 200 own prompt tokens, 845 generated tokens).</li>
<li><b>Arms:</b> base and target are the 2026-09-18 ci-mimic arms. They were not re-run. canon is the new arm of this campaign.{canon_id}{target_id} The package swap used the nightly's own sequence (apt-get remove, apt-get install), and the nightly's package was reinstalled at the end.</li>
<li><b>Reference:</b> the 2026-09-18 nightly run {esc(a.nightly_run_id) or ''} (package {esc(ngt_ver)}) and the 13 Slack reports 2026-09-05 to 09-17.</li>
</ul>
<div class="tw">{"".join(arms_table)}</div>
{pairing}
<h3>Deviations from the real nightly (recorded by the driver of the {dev_src} arm)</h3>
{dev_lead}
<ul>{dev_html}
<li>The nightly runs 25 min of functional tests first, then perf, then MMLU Pro (an accuracy benchmark) and a 3 h soak (a long steady-load test). Here the perf phase followed a package swap.</li>
<li>One run per arm, one nightly for the same-day comparison. Effects below a config's 13-night band are therefore not resolved.</li>
</ul>
{("<h3>Caveats and incidents (read before the numbers)</h3>" + caveats_lead + caveats_html) if caveats_html else ""}

<h2>2. Effect A: canon vs base (the canonical AMX kernels alone)</h2>
<p>Test: swap only the package, keep everything else. Observation: the two charts and the table. Meaning: see the rules below.</p>
<ul>
<li>A resolved TPS change (marked *) meets three conditions: its 95 % interval over the 10 paired rounds excludes zero, its size is at least 1 %, and its size is at least the config's 13-night TPS band (2 sd).</li>
<li>The band condition is needed. The nightlies of 2026-09-16 and 09-17, two consecutive packages without AMX, differ by +4.7 % on qwen-3-4b tp4 with a paired t of 4.2. The t test alone would flag too many changes on the noisy configs.</li>
<li>The TTFT * uses the same three conditions: |t| &gt;= 2.26, |delta| at least 1 % and at least 1 ms, and |delta| at least the config's 13-night TTFT band.</li>
<li>TTFT rows that involve base compare unlike client conditions (section 1). Their TTFT marks are not attributed to the package for {ttft_rule_txt}. A client stall of tens of ms is visible only on TTFTs that short.</li>
<li>Only llama-8b and mixtral run the AMX kernel with CPU attention. qwen-3-4b gets it only in the CPU share (the part of attention the CPU still computes under FPGA attention, section 7). Every other config is a control for canon (section 7).</li>
</ul>
{legend([(C_CANON, "canon vs base")])}
<div class="fig">{chartA}</div>
<div class="fig">{chartA_ttft}</div>
<div class="tw">{tableA}</div>

<h2>3. Effect B: target vs canon (what PR #4424 adds on top of canonical AMX)</h2>
<p>Both packages are main {esc(main10)} with TRON_AMX_DISPATCH=ON in the deb preset.{target_id or " target adds PR #4424 and sets TRON_K_VNNI=ON in the same preset line."} Nothing else differs. The same three conditions mark a resolved change.</p>
{legend([(C_TARGET, "target vs canon")])}
<div class="fig">{chartB}</div>
<div class="fig">{chartB_ttft}</div>
<div class="tw">{tableB}</div>
<h3>The three comparisons side by side (TPS, percent, * = resolved{", n/t = not testable" if any_nt else ""})</h3>
<p>canon vs base is effect A. target vs canon is effect B. target vs base is the 2026-09-18 report's effect, the two combined (the percentages compound, and the plain sum is only approximate).</p>
<div class="tw">{"".join(summary)}</div>
{("<h3>Reading the effects</h3>" + notes_html) if notes_html else ""}

<h2>4. Absolute numbers side by side</h2>
{legend([(C_NIGHTLY, "nightly 2026-09-18 (ring)", "ring"), (C_BASE, "base"), (C_CANON, "canon"), (C_TARGET, "target"), (C_BAND, "13-night min to max (3 nights for gemma-4-31b)", "rect")])}
<div class="fig">{chart4}</div>

<h2>5. Threshold verdicts (CURRENT static goals, as the Slack report applies them)</h2>
<p>PASS needs mean TPS at or above the goal AND the slowest user at or above the slowest-user goal. These are the thresholds from systems_test scripts/system_ci.py for granite_rapids_72_rinzler. The ratchet YAML thresholds are a separate, unpublished set.</p>
<div class="tw">{"".join(thr_table)}</div>
{a.thr_note or ""}

<h2>6. Evidence that the right binary served, and that AMX ran</h2>
<div class="tw">{"".join(ev)}</div>
<ul class="take">
<li>Expected on base: 0 AMX-busy cycles. The package has no AMX code.</li>
<li>Expected on canon: a large count for llama-3.1-8b (CPU attention, head 128, kv_mul 4), of the same order as target's. qwen-3-4b tp2 should show a smaller count. Under FPGA attention the CPU computes only positions 0 to 126 of each query and the most recent tokens not yet copied to HBM.</li>
<li>Expected on target: as canon. The VNNI-K layout does not change which model runs the kernel.</li>
<li>A "deleted binary" snapshot means an engine kept running an executable whose file was replaced on disk after it started. The sha of that executable says which package it was. {" ".join(esc(x) for x in del_notes) if del_notes else "No arm shows such a snapshot."} The first provisioning of each arm replaced the engines of the "before" snapshot. Every measured config ran its own arm's package (identity row: 0 engine pids differ after provisioning).</li>
{probe_note}
</ul>
{man_html}
{tman_html}

<h2>7. Which configs can react, and why</h2>
<p>canon has the AMX kernel only for models with head size 128, kv_mul 4 and CPU attention. In the nightly list those are llama-3.1-8b and mixtral-8x7b. qwen-3-4b runs FPGA attention and gets the kernel only in the CPU share. llama-3b, llama-70b, qwen-2.5-32b, gemma-2, gemma-4 and gpt-oss are controls for canon: no kernel effect is expected there. A resolved change on a control has three candidate causes: night-to-night noise, a client-side artifact, or a package effect outside the kernel (for example the dispatch gate). Such a change needs a repeat run before it is accepted. target adds the VNNI-K layout on top of canon.</p>
<ul>{per_config_notes}</ul>

<h2>8. Files</h2>
<ul>
<li>Run record of canon: <code>exec/results/canon-ci-20260918/canon/perf.json</code> (per-request TPS and TTFT, snapshots, probes), <code>preflight.txt</code> (with the package manifest), <code>base-identity.txt</code>.</li>
<li>Records of base and target: <code>exec/results/ci-mimic-20260918/base-pass1/perf.json</code>, <code>target-pass1/perf.json</code>, <code>preflight.txt</code> (target manifest), <code>caveats.html</code>.</li>
<li>Reference: <code>exec/results/ci-mimic-20260918/reference/</code> (nightly logs and <code>nightly_stats.json</code>, the 13-night Slack statistics). The parser <code>nightly_to_arm.py</code> is in <code>exec/canon-ci-20260918/</code>.</li>
<li>Logs: campaign <code>exec/logs/canon-ci-20260918.log</code>, driver <code>exec/results/canon-ci-20260918/canon/driver.log</code>, marker <code>exec/logs/bill-share.log</code>.</li>
<li>Scripts: <code>exec/canon-ci-20260918/</code> (driver <code>st_ci_perf.py</code>, <code>campaign.sh</code>, <code>launch.sh</code>, <code>dut.sh</code>, canon build <code>build-canon.sh</code>, this generator <code>gen_report.py</code>, the caveats generator <code>gen_caveats.py</code>).</li>
<li>Paths are relative to the intel-AMX root unless they start with <code>VNNIed-K-in-place/</code>.</li>
</ul>

<h2>9. Not measured in this run, and what would measure it</h2>
<ul>
<li>AMX engagement on mixtral-8x7b and on qwen-3-4b tp4: no probe ran on them in any arm. One 20 s EXE.AMX_BUSY probe per config resolves it.</li>
<li>Run-to-run noise of our own arms: every arm ran once. A second canon run (about 90 min, whole machine) sets the within-day band.</li>
<li>TTFT effect of the kernel: base ran on a saturated client (121 anomalous samples on llama-3b, no PSI record). A base re-run on an idle client resolves the TTFT rows of {ttft_bad_names}.</li>
<li>gpt-oss-120b tp4 canon vs base -3.9 %: inside its 5.7 % band, and the model has no kernel path. A repeat run decides noise against a dispatch-gate effect.</li>
<li>llama-3.2-3b target vs canon -5.1 %: resolved by the rule, and its stall indicator equals canon's (section 1). One re-run of the target package on llama-3b on an idle client decides whether PR #4424 slows this CPU-attention model.</li>
<li>Client CPU pressure inside a config: PSI is sampled only at the 14 snapshots. The per-config anomalous-tps count (section 1) is the only in-run indicator.</li>
<li>Cause of the qwen-3-4b loss inside PR #4424 (the VNNI-K layout in the K cache, the gof::populate copy of K to the FPGA, or the dispatch changes): effect B isolates the PR as a package. The issue #4500 root-cause campaign measures the parts.</li>
<li>Foreign load on the DUT during base and target: the DUT load row of section 6 shows the engines' own load only (no value far above the idle-engine level). No process list was recorded.</li>
<li>Functional tests, MMLU Pro and the 3 h soak: not run in any arm.</li>
</ul>
</main></body></html>
"""
    data = html.encode("ascii", "xmlcharrefreplace")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    open(a.out, "wb").write(data)
    print(f"wrote {a.out} ({len(data):,} bytes, ASCII only; canon configs with results: {n_canon} of {N_CONFIGS})")
    for s in sv:
        print(" -", re.sub(r"<[^>]+>", "", s))


if __name__ == "__main__":
    main()
