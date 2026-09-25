#!/usr/bin/env python3
"""decide.py: turn the attnstats-20260924 campaign results into decision.json for counter.html
section 13 (generator exec/counter-20260922/gen_counter.py) and print the verdict.

Inputs (all under exec/results/attnstats-20260924/):
  summary.json      written by summarize.py (cells: mean / sd / n of TPS per user and TTFT per arm)
  rt/*.log          one runtron log per run; the head binary prints [attn-stats] lines at exit
  fuse-poll.log     leaf reads taken every 15 s while a head runtron ran (chain.sh poller)
  tests.txt / tests-*.out   unit-test lines of the head build (build2.sh)

Rule (counter.html section 13): the head binary with TRON_ATTN_STATS unset must sit inside the
same-binary band, |base2 - base|, at every cell; a loss beyond the band at both prompt lengths
flips the switch decision to a build option for the per-visit tallies.

Words: TPS = decode tokens per second per user; base/base2 = main binary (66c7bb8db1), variable
unset; head = branch binary, variable unset; headon = branch binary with TRON_ATTN_STATS=1;
headkill = headon with TRON_AMX_DISABLE=1 (the AMX kill switch); sd = sample standard deviation.
"""
import glob
import json
import os
import re
import sys

RES = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser(
    "~/workspace/intel-AMX/exec/results/attnstats-20260924")
OUT = os.path.expanduser("~/workspace/intel-AMX/exec/attnstats-20260924/decision.json")
BASE = "66c7bb8db1"
ARMS = ["base", "base2", "head", "headon", "headkill"]
READING = {
    "base": "reference (main binary)",
    "base2": "same-binary control: |base2 - base| = the band",
    "head": "off-state cost of the always-compiled hooks",
    "headon": "on-state cost (counting, rows, path bits)",
    "headkill": "kill-switch cross-check run (counts only)",
}


def fnum(x, d=2):
    return "-" if x is None else f"{x:.{d}f}"


def load_summary():
    p = os.path.join(RES, "summary.json")
    if not os.path.exists(p):
        return None
    return json.load(open(p))


def attn_stats_lines(pattern):
    """[attn-stats] lines of the runtron logs whose name matches pattern."""
    out = {}
    for f in sorted(glob.glob(os.path.join(RES, "rt", pattern))):
        lines = [l.rstrip("\n") for l in open(f, errors="replace") if l.startswith("[attn-stats]")]
        if lines:
            out[os.path.basename(f)] = lines
    return out


def totals_of(lines, cls):
    """The JSON object after '[attn-stats] <cls> totals: '."""
    for l in lines:
        m = re.match(r"\[attn-stats\] " + re.escape(cls) + r" totals: (\{.*\})$", l)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
    return None


def forwards_of(lines, cls):
    for l in lines:
        m = re.match(r"\[attn-stats\] " + re.escape(cls) + r" forwards: (\{.*\})$", l)
        if m:
            try:
                return json.loads(m.group(1))
            except json.JSONDecodeError:
                return None
    return None


def main():
    d = {"base": BASE, "rows": [], "checks": [], "verdict": ""}
    head_sha = os.environ.get("HEAD_COMMIT")
    if not head_sha:
        # the chain log names it
        logp = os.path.expanduser("~/workspace/intel-AMX/exec/logs/attnstats-20260924-chain.log")
        if os.path.exists(logp):
            m = re.search(r"HEAD_COMMIT=(\w+)", open(logp).read())
            head_sha = m.group(1) if m else None
    d["head"] = head_sha or "?"
    d["pr"] = os.environ.get("PR_TEXT", "draft PR (number pending)")

    s = load_summary()
    verdict_parts = []
    if s:
        cells = {}
        for c in s["cells"]:
            if c.get("attn") != "cpu":
                continue
            cells.setdefault(c["cell"], {})[c["arm"]] = c
        flips = 0
        for cell in sorted(cells):
            arms = cells[cell]
            base = arms.get("base")
            base2 = arms.get("base2")
            # Pre-registered band (counter.html section 13): the largest of the
            # same-binary difference |base2 - base|, twice the largest per-arm sd,
            # and 0.5 % of the base mean (a floor so a tiny sd cannot flip on drift).
            band = None
            host_note = ""
            if base and base2 and base.get("tps_mean") and base2.get("tps_mean"):
                same = abs(base2["tps_mean"] - base["tps_mean"])
                sds = [c.get("tps_sd") or 0 for c in arms.values() if c.get("tps_sd") is not None]
                band = max(same, 2 * max(sds) if sds else 0, 0.005 * base["tps_mean"])
                if same > 2 * max(sds or [0]):
                    host_note = "; host drift: |base2 - base| exceeds 2 x max sd"
            for arm in ARMS:
                c = arms.get(arm)
                if not c:
                    continue
                delta = None
                if base and base.get("tps_mean") and c.get("tps_mean"):
                    delta = 100.0 * (c["tps_mean"] - base["tps_mean"]) / base["tps_mean"]
                note = READING[arm]
                if arm == "head" and band is not None and c.get("tps_mean") and base.get("tps_mean"):
                    diff = c["tps_mean"] - base["tps_mean"]
                    inside = abs(diff) <= band
                    if inside:
                        note += "; inside the band"
                    elif diff > 0:
                        note += "; outside the band on the fast side (no loss; code placement, as seen before on this host)"
                    else:
                        note += "; LOSS beyond the band"
                        flips += 1
                d["rows"].append({
                    "cell": cell, "arm": arm, "n": c.get("n"),
                    "tps": fnum(c.get("tps_mean")), "sd": fnum(c.get("tps_sd")),
                    "delta": "-" if delta is None else f"{delta:+.2f} %",
                    "note": note + (f"; band {band:.2f} TPS ({100*band/base['tps_mean']:.2f} %){host_note}" if arm == "base2" and band is not None else ""),
                })
        n_cells = len(cells)
        if flips == 0:
            verdict_parts.append("the head binary with the variable unset shows no loss beyond the same-binary band at any cell, so the environment variable stays (no build option)")
        elif flips >= n_cells and n_cells >= 2:
            verdict_parts.append(f"the head binary with the variable unset lost more than the band at all {flips} cells: flip to a build option for the per-visit tallies")
        else:
            verdict_parts.append(f"the head binary with the variable unset lost more than the band at {flips} of {n_cells} cells: the rule needs a loss at every cell; repeat before deciding")
    else:
        verdict_parts.append("pending: no summary.json yet")

    # cross-checks from the exit reports
    on = attn_stats_lines("*__headon__*.log")
    kill = attn_stats_lines("*__headkill__*.log")
    off = attn_stats_lines("*__head__*.log") | attn_stats_lines("*__base*.log")
    d["checks"].append(f"exit reports: {len(on)} headon run(s) and {len(kill)} headkill run(s) printed [attn-stats] lines; "
                       f"{len(off)} run(s) with the variable unset printed any (expected 0)")
    def pick(runs, key):
        for name, lines in runs.items():
            if key in name:
                return name, lines
        return (None, None)
    name_on, lines_on = pick(on, "p1024")
    name_kill, lines_kill = pick(kill, "p1024")
    if lines_on and lines_kill:
        for cls in ("decode_like", "prompt_or_mixed"):
            t_on, t_kill = totals_of(lines_on, cls), totals_of(lines_kill, cls)
            if not t_on or not t_kill:
                continue
            amx_on = t_on.get("ready_amx_visits", 0) + t_on.get("pending_amx_visits", 0)
            full_on = t_on.get("ready_avx_full_page_visits", 0) + t_on.get("pending_avx_full_page_visits", 0)
            amx_kill = t_kill.get("ready_amx_visits", 0) + t_kill.get("pending_amx_visits", 0)
            full_kill = t_kill.get("ready_avx_full_page_visits", 0) + t_kill.get("pending_avx_full_page_visits", 0)
            ok = amx_kill == 0 and full_kill == amx_on + full_on
            d["checks"].append(
                f"{cls}, prompt 1024: AMX on: amx visits {amx_on:,}, AVX full-page visits {full_on:,}; kill switch: "
                f"amx visits {amx_kill:,}, AVX full-page visits {full_kill:,} -> identity avx_full(kill) == amx(on) + avx_full(on): "
                f"{'holds' if ok else 'FAILS'}")
            k_on = sum(t_on.get(f"{p}_{q}_k_tokens", 0) for p in ("ready", "pending") for q in ("amx", "avx"))
            k_kill = sum(t_kill.get(f"{p}_{q}_k_tokens", 0) for p in ("ready", "pending") for q in ("amx", "avx"))
            d["checks"].append(f"{cls}, prompt 1024: K tokens scored in software, AMX on {k_on:,} vs kill switch {k_kill:,} "
                               f"({'equal' if k_on == k_kill else 'DIFFER'})")
            if cls == "decode_like":
                # Closed form for qwen-3-4b tp2, 8 users, prompt 1024, 256 generated tokens
                # (255 decode forwards): step t has floor((1023 + t) / 64) full ready pages
                # per (layer, kv head, user); 36 layers x 8 kv heads x 8 users.
                L, H, U = 36, 8, 8
                expected = sum((1023 + t) // 64 for t in range(1, 256)) * L * H * U
                ready_amx = t_on.get("ready_amx_visits", 0)
                d["checks"].append(f"decode_like, prompt 1024, AMX on: ready amx visits {ready_amx:,} vs closed form {expected:,} "
                                   f"({'equal' if ready_amx == expected else 'DIFFER'}); pending amx visits {t_on.get('pending_amx_visits', 0):,} "
                                   f"(= steps whose new page is full x {L * H * U:,})")
            f_on = forwards_of(lines_on, cls)
            if f_on:
                d["checks"].append(f"{cls}, prompt 1024, AMX on: forwards {f_on.get('forwards')}, token jobs {f_on.get('token_jobs')}, "
                                   f"by path set {json.dumps(f_on.get('token_jobs_by_path_set'))}")
    else:
        d["checks"].append("kill-switch identity: pending (headon or headkill exit report missing)")
    # instruction-level comparison of the two binaries (objdump-check.sh)
    for name, label in (("objdump-check.txt", "first commit"), (os.path.join("..", "attnstats-20260924b", "objdump-check-head2.txt"), "final commit")):
        path = os.path.join(RES, name)
        if not os.path.exists(path):
            continue
        txt = open(path, errors="replace").read()
        halves = ("\n" + txt).split("\n## ")
        summ = []
        for h in halves[1:]:
            bname = h.split("\n", 1)[0].rsplit("/", 1)[-1]
            m = re.search(r"instantiations=(\d+) total_bytes=(\d+)", h)
            first = re.search(r"^\s*(\d+) bytes\s+(\d+) insns\s+(\d+) lock\s+(\d+) rdtsc\s+(\d+) xadd", h, re.M)
            job = re.search(r"^\s*(\d+) bytes\s+(\d+) insns\s+(\d+) rdtsc\s+unsigned long", h, re.M)
            if m and first:
                summ.append(f"{bname}: {int(m.group(1))} apply_page_range instantiations, {int(m.group(2)):,} bytes; largest {int(first.group(1)):,} bytes / {int(first.group(2)):,} instructions / {first.group(3)} lock-prefixed / {first.group(4)} rdtsc"
                            + (f"; largest run_attention_job {int(job.group(1)):,} bytes / {int(job.group(2)):,} instructions / {job.group(3)} rdtsc" if job else ""))
        if summ:
            d["checks"].append(f"objdump ({label}): " + " | ".join(summ))
    # confirmation campaign (final commit) rows
    p2 = os.path.join(RES, "..", "attnstats-20260924b", "summary.json")
    if os.path.exists(p2):
        s2 = json.load(open(p2))
        cells2 = {}
        for c in s2["cells"]:
            if c.get("attn") == "cpu":
                cells2.setdefault(c["cell"], {})[c["arm"]] = c
        for cell in sorted(cells2):
            arms = cells2[cell]
            base = arms.get("base3")
            for arm in ("base3", "head2", "headon2"):
                c = arms.get(arm)
                if not c:
                    continue
                delta = None
                if base and base.get("tps_mean") and c.get("tps_mean") and arm != "base3":
                    delta = 100.0 * (c["tps_mean"] - base["tps_mean"]) / base["tps_mean"]
                d["rows"].append({"cell": "confirmation: " + cell, "arm": arm, "n": c.get("n"),
                                  "tps": fnum(c.get("tps_mean")), "sd": fnum(c.get("tps_sd")),
                                  "delta": "-" if delta is None else f"{delta:+.2f} % vs base3",
                                  "note": {"base3": "main binary again (reference of this round)",
                                           "head2": "final commit, switch unset",
                                           "headon2": "final commit, TRON_ATTN_STATS=1"}[arm]})
        sha = open(os.path.expanduser("~/workspace/intel-AMX/exec/attnstats-20260924/head2.sha")).read().strip()
        d["head"] = f"{sha} (measured: {d['head']} in the main round, {sha} in the confirmation round)"
    # live reads
    poll = os.path.join(RES, "fuse-poll.log")
    if os.path.exists(poll):
        n = sum(1 for _ in open(poll, errors="replace"))
        sums = [l for l in open(poll, errors="replace") if "/summary " in l]
        d["checks"].append(f"live FUSE reads while a head runtron ran: {n} leaf lines in fuse-poll.log"
                           + (f"; first summary: {sums[0].split(' ', 2)[2][:300]}" if sums else ""))
    else:
        d["checks"].append("live FUSE reads: fuse-poll.log missing")
    # unit tests of the head build
    for name, label in (("tests-attnhead.txt", "first commit"), (os.path.join("..", "attnstats-20260924b", "tests-attnhead2.txt"), "final commit")):
        tests = os.path.join(RES, name)
        if os.path.exists(tests):
            lines = [re.sub(r" tip=\S+ env=\[\] args=\[\]", "", l.strip()) for l in open(tests) if l.strip()]
            d["checks"].append(f"unit tests with the fake device ({label}, switch unset): " + "; ".join(lines)[:700])
    logp = os.path.expanduser("~/workspace/intel-AMX/exec/logs/attnstats-20260924-chain.log")
    d["final"] = os.path.exists(logp) and "=== chain finished" in open(logp).read()
    if not d["final"]:
        verdict_parts.insert(0, "PRELIMINARY (the campaign is still running)")
    d["verdict"] = "; ".join(verdict_parts)
    json.dump(d, open(OUT, "w"), indent=1)
    print(json.dumps(d, indent=1))


if __name__ == "__main__":
    main()
