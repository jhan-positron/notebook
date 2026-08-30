#!/usr/bin/env python3
"""P1a Phase M analysis (pre-registered: P1A-preregistration.md).

Part 1: tok/s A/B from p1a-ab.txt REP lines.
  Per config/arm: mean, sd, n; delta% (on vs off) with Welch t-based 95% CI.
  Verdict per pre-reg: PROCEED-criterion met iff delta lower bound > 0 and
  point estimate >= +1% (upper-bound framing: CI excluding zero AND >=1%).
Part 2 (--traces): boundary attribution from the traced reps: driving-thread
  slice-duration means for cpu-compute / logits-read / topk-output-read /
  wait-indices, helper first-wait, per arm.
"""
import argparse
import math
import re
import statistics
import sys

OUT = "/home/jhan/workspace/intel-AMX/exec/results/router"
CONFIGS = [(1, 2048), (1, 8192), (8, 2048), (8, 8192)]
# t.975 quantiles for small df
T975 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
        7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228}


def parse_reps():
    reps = {}
    pat = re.compile(r"REP u=(\d+) ctx=(\d+) rep=\d+ arm=(\w+) .*?at ([0-9.]+) average tok/s")
    for line in open(OUT + "/p1a-ab.txt"):
        m = pat.search(line)
        if m:
            u, ctx, arm, v = int(m.group(1)), int(m.group(2)), m.group(3), float(m.group(4))
            reps.setdefault((u, ctx, arm), []).append(v)
    return reps


def welch(a, b):
    """delta = mean(b)-mean(a) with Welch 95% CI (b=on, a=off)."""
    ma, mb = statistics.mean(a), statistics.mean(b)
    va, vb = statistics.variance(a), statistics.variance(b)
    na, nb = len(a), len(b)
    se = math.sqrt(va / na + vb / nb)
    if se == 0:
        return mb - ma, 0.0, 0
    df_num = (va / na + vb / nb) ** 2
    df_den = (va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)
    df = max(1, int(df_num / df_den))
    t = T975.get(df, 1.96)
    return mb - ma, t * se, df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--traces", action="store_true")
    args = ap.parse_args()

    reps = parse_reps()
    print("== P1a A/B decode tok/s (per-user) ==")
    any_pass = False
    for U, CTX in CONFIGS:
        off = reps.get((U, CTX, "off"), [])
        on = reps.get((U, CTX, "on"), [])
        if len(off) < 2 or len(on) < 2:
            print("u%d/ctx%-5d insufficient reps (off=%d on=%d)" % (U, CTX, len(off), len(on)))
            continue
        d, hw, df = welch(off, on)
        base = statistics.mean(off)
        pct, pct_hw = 100 * d / base, 100 * hw / base
        lo, hi = pct - pct_hw, pct + pct_hw
        verdict = "PASS(+1%,CI>0)" if (lo > 0 and pct >= 1.0) else "no"
        if verdict.startswith("PASS"):
            any_pass = True
        print("u%d/ctx%-5d off=%.2f (sd %.3f, n=%d)  on=%.2f (sd %.3f, n=%d)  "
              "delta=%+.2f%% CI95=[%+.2f%%, %+.2f%%] df=%d  -> %s"
              % (U, CTX, base, statistics.stdev(off), len(off),
                 statistics.mean(on), statistics.stdev(on), len(on),
                 pct, lo, hi, df, verdict))
    print("G-B criterion met in at least one config: %s" % any_pass)
    try:
        print("numerics verdict: %s" % open(OUT + "/p1a-numerics-verdict.txt").read().strip())
    except FileNotFoundError:
        print("numerics verdict: MISSING")

    if not args.traces:
        return
    from perfetto.trace_processor import TraceProcessor
    print("\n== boundary attribution (driving-thread slice means, us) ==")
    NAMES = ["cpu router compute", "start_reading linear_channel_5",
             "start_reading topk_snd_channel", "wait indices topk_snd",
             "await deps mlp_router_weight_launcher"]
    for U, CTX in [(1, 2048), (8, 2048)]:
        for arm in ("off", "on"):
            f = "%s/p1a-u%d-ctx%d-%s.perfetto-trace" % (OUT, U, CTX, arm)
            try:
                tp = TraceProcessor(trace=f)
            except Exception as e:
                print("u%d/%s %s: trace unavailable (%s)" % (U, CTX, arm, e))
                continue
            row = ["u%d/ctx%d %s:" % (U, CTX, arm)]
            for nm in NAMES:
                r = list(tp.query(
                    "SELECT AVG(dur) a, COUNT(*) c FROM slice WHERE name = '%s' AND dur >= 0" % nm))
                if r and r[0].c:
                    row.append("%s=%.2f(n=%d)" % (nm.split()[0] if nm.startswith("cpu")
                                                  else nm.replace("start_reading ", "rd:")
                                                        .replace("wait indices ", "wi:")
                                                        .replace("await deps ", "await:"),
                                                  (r[0].a or 0) / 1000.0, r[0].c))
            fw = list(tp.query(
                "SELECT AVG(dur) a, COUNT(*) c FROM slice WHERE name GLOB "
                "'kernel_add_topk_softmax* first wait' AND dur >= 0"))
            if fw and fw[0].c:
                row.append("helper_fw=%.2f(n=%d)" % ((fw[0].a or 0) / 1000.0, fw[0].c))
            print("  " + "  ".join(row))
            tp.close()


if __name__ == "__main__":
    main()
