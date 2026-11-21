#!/usr/bin/env python3
"""levels9.py - level switches of bwx8 trial-mode runs (round 2 of tackle-8mb).

Library and command line. Standard library only.

  levels9.py switches <csv or result folder>... [--periods 1,2,5,6.9,10] [--sizes 4M,8M]
  levels9.py counters <csv or result folder>...
  levels9.py watch    <result folder>... [--near 0.15]
  levels9.py cells    <csv or result folder>...

Words used here
  window   one W row of bwx8: a timed run of whole passes of one kernel over one size.
  rate     bytes / (t_end - t_start) of a window, in GB/s (1 GB = 1e9 bytes).
  level    a rate at which at least MIN_PLATEAU windows of a process sit within TOL GB/s.
  low, high  the two levels of a process. A process whose levels are less than MIN_GAP
           apart, or that has one plateau only, has "one level".
  mixed    a window whose rate lies more than TOL from both level medians, between them.
  off      a window more than TOL outside the range of the levels.
  switch   a change from one level to the other. Its time is an estimate ("est."): for
           mixed windows between two levels, time = start of the first mixed window +
           sum(fraction at the old level x window length). This assumes one abrupt switch.
  excursion  mixed windows with the same level before and after (a visit to the other
           level that is shorter than a window, or no visit at all).
All switch times are seconds since process start (the time origin of the W rows).
"""
import argparse
import cmath
import glob
import math
import os
import random
import re
import sys

TOL = 0.5          # GB/s: a window belongs to a level if it is within TOL of the level median
MIN_GAP = 1.0      # GB/s: smallest distance of two level medians
MIN_PLATEAU = 3    # windows within TOL that a level needs
GAP_S = 0.05       # s: two windows further apart than this are not contiguous
BIN_S = 0.1        # s: histogram bin
NEAR_S = 0.15      # s: half width of the "nearby" interval of the watch command
MIN_SEQ = 8        # windows that a kernel@size sequence needs for a level description


# ------------------------------------------------------------------ small helpers
def median(v):
    v = sorted(v)
    n = len(v)
    if n == 0:
        return None
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def percentile(v, p):
    """Linear interpolation between order statistics; p in 0..100."""
    v = sorted(v)
    if not v:
        return None
    x = (len(v) - 1) * p / 100.0
    lo = int(math.floor(x))
    hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (x - lo)


def size_name(n):
    if n % (1 << 20) == 0:
        return "%dM" % (n >> 20)
    if n % 1024 == 0:
        return "%dK" % (n >> 10)
    return str(n)


def parse_size(s):
    m = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30}
    return int(s[:-1]) * m[s[-1]] if s[-1] in m else int(s)


def num(s):
    if s in ("NA", ""):
        return None
    try:
        return int(s)
    except ValueError:
        return float(s)


def fmt(x, nd=2):
    return "NA" if x is None else "%.*f" % (nd, x)


def fl(v, nd=2):
    return "[" + " ".join(fmt(x, nd) for x in v) + "]"


# ------------------------------------------------------------------ (a) parser
class Window:
    __slots__ = ("trial", "phase", "widx", "kernel", "pass_bytes", "bytes", "t_start", "t_end")

    def __init__(self, trial, phase, widx, kernel, pass_bytes, nbytes, t_start, t_end):
        self.trial, self.phase, self.widx, self.kernel = trial, phase, widx, kernel
        self.pass_bytes, self.bytes, self.t_start, self.t_end = pass_bytes, nbytes, t_start, t_end

    @property
    def rate(self):                     # GB/s
        return self.bytes / float(self.t_end - self.t_start)

    @property
    def ts(self):                       # s since process start
        return self.t_start / 1e9

    @property
    def te(self):
        return self.t_end / 1e9


class Proc:
    def __init__(self, path, header=None):
        self.path = path
        self.folder = os.path.dirname(os.path.abspath(path))
        self.header = header or ""
        self.hdr = {}
        self.M = {}
        self.K = []
        self.S = {}
        self.W = []
        self.C = {}      # (trial, widx) -> dict(enabled_ns, running_ns, cputime_ns, counts=[...])
        self.E = {}
        self.P = []
        self.X = []
        self.ended = None    # 'killed' or 'failed' line
        self.day = 0         # midnights (UTC) between the first launch line of the file and this one
        if header:
            f = header.split()
            for key in ("step", "session", "idx", "tag", "utc", "waited_s"):
                if key in f[:-1]:
                    self.hdr[key] = f[f.index(key) + 1]
            if "loadavg" in f:
                i = f.index("loadavg")
                self.hdr["loadavg"] = " ".join(f[i + 1:i + 4])
            if " args " in header:
                self.hdr["args"] = header.split(" args ", 1)[1]

    # -- identity
    @property
    def idx(self):
        try:
            return int(self.hdr.get("idx", self.M.get("plan.proc", -1)))
        except ValueError:
            return -1

    @property
    def tag(self):
        return self.hdr.get("tag", "-")

    @property
    def step(self):
        return self.hdr.get("step", self.M.get("plan.step", "-"))

    @property
    def session(self):
        return self.hdr.get("session", self.M.get("plan.session", "-"))

    @property
    def cpu(self):
        return self.M.get("cpu", self.M.get("plan.cpu", "-"))

    @property
    def utc(self):
        return self.hdr.get("utc", "-")

    @property
    def launch_s(self):
        """Second of the UTC day of the launch line, or None."""
        m = re.match(r"^(\d\d):(\d\d):(\d\d)$", self.utc)
        if not m:
            return None
        return self.day * 86400 + int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))

    def notes(self):
        """Marks of a process that did not run as planned: a killed or failed line, X rows, a trial with
        W rows and no E row."""
        out = []
        if self.ended:
            out.append(self.ended.lstrip("- ").split(" utc ")[0])
        codes = {}
        for x in self.X:
            c = x[1] if len(x) > 1 else "?"
            codes[c] = codes.get(c, 0) + 1
        out.extend("X row %s x%d" % (c, codes[c]) for c in sorted(codes))
        noe = sorted(set(w.trial for w in self.W) - set(self.E))
        if noe:
            out.append("no E row for trial %s" % ",".join(str(t) for t in noe))
        return out

    @property
    def events(self):
        e = self.M.get("events", "none")
        if e in ("none", ""):
            return []
        return [x.split("=")[0] for x in re.split(r"[;,]", e) if x]

    def main_group(self):
        """(kernel, pass_bytes) of the target windows with the most windows."""
        n = {}
        for w in self.W:
            if w.phase == "target":
                n[(w.kernel, w.pass_bytes)] = n.get((w.kernel, w.pass_bytes), 0) + 1
        if not n:
            return None
        return max(sorted(n), key=lambda k: n[k])

    @property
    def kernel(self):
        g = self.main_group()
        return g[0] if g else self.M.get("plan.kernel", "-")

    @property
    def size(self):
        g = self.main_group()
        return g[1] if g else int(self.M.get("plan.size", 0) or 0)

    @property
    def cond(self):
        s = self.S.get(0)
        return s[0] if s else "-"

    def group_windows(self, group=None):
        """Windows of one kernel@size in time order (every phase)."""
        group = group or self.main_group()
        return sorted([w for w in self.W if (w.kernel, w.pass_bytes) == group], key=lambda w: w.t_start)

    def trial_starts(self):
        """Per trial: (trial, start of its first window, start of its first target window), in s."""
        out = {}
        for w in self.W:
            a = out.setdefault(w.trial, [None, None])
            if a[0] is None or w.ts < a[0]:
                a[0] = w.ts
            if w.phase == "target" and (a[1] is None or w.ts < a[1]):
                a[1] = w.ts
        return [(t, out[t][0], out[t][1]) for t in sorted(out)]

    def label(self):
        return "idx %s %s" % (self.hdr.get("idx", "-"), self.tag)


def parse_csv(path):
    """Returns the list of processes of one csv file of run_bwx8.sh (or of one bare bwx8 output)."""
    procs = []
    cur = None
    day, last = 0, None
    with open(path) as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("-- step"):
                cur = Proc(path, line)
                procs.append(cur)
                # The launch line holds the time of day only. Launches are in time order, so a time that
                # is more than 12 h before the launch above it lies after a midnight.
                sec = cur.launch_s
                if sec is not None:
                    if last is not None and sec < last - 43200:
                        day += 1
                    last = sec
                    cur.day = day
                continue
            if line.startswith("-- "):
                if cur is not None:
                    cur.ended = line
                continue
            if line.startswith("# bwx8 trial mode"):
                if cur is None or cur.M:
                    cur = Proc(path)
                    procs.append(cur)
                continue
            if cur is None or not line or line.startswith("#"):
                continue
            p = line.split(",")
            k = p[0]
            try:
                if k == "M":
                    q = line.split(",", 2)
                    cur.M[q[1]] = q[2] if len(q) > 2 else ""
                elif k == "W":
                    cur.W.append(Window(int(p[1]), p[2], int(p[3]), p[4], int(p[5]), int(p[6]),
                                        int(p[7]), int(p[8])))
                elif k == "S":
                    cur.S[int(p[1])] = p[2:]
                elif k == "C":
                    cur.C[(int(p[1]), int(p[2]))] = {"enabled_ns": num(p[3]), "running_ns": num(p[4]),
                                                     "cputime_ns": num(p[5]),
                                                     "counts": [num(x) for x in p[6:]]}
                elif k == "E":
                    cur.E[int(p[1])] = p[2:]
                elif k == "P":
                    cur.P.append(p[1:])
                elif k == "X":
                    cur.X.append(p[1:])
                elif k == "K":
                    cur.K.append(p[1:])
            except (ValueError, IndexError):
                cur.X.append(["-1", "parse", line])
    return [p for p in procs if p.W or p.M]


def csv_paths(args):
    """A folder stands for every <name>.csv in it."""
    out = []
    for a in args:
        if os.path.isdir(a):
            out.extend(sorted(glob.glob(os.path.join(a, "*.csv"))))
        else:
            out.append(a)
    return out


def load(args):
    procs = []
    for path in csv_paths(args):
        procs.extend(parse_csv(path))
    return procs


# ------------------------------------------------------------------ (b) level segmentation
def find_levels(rates, tol=TOL, min_gap=MIN_GAP, min_plateau=MIN_PLATEAU):
    """Returns (low, high) level medians, or (m, None) for one level at median m.

    Split of the sorted rates that gives the largest between-group variance, then three rounds of
    "median of the rates within tol of the level". Two levels need medians at least min_gap apart and
    min_plateau rates within tol of each median.
    """
    v = sorted(rates)
    n = len(v)
    if n == 0:
        return (None, None)
    one = (median(v), None)
    if n < 2 * min_plateau:
        return one
    pre = [0.0]
    for x in v:
        pre.append(pre[-1] + x)
    best, bk = -1.0, None
    for k in range(1, n):
        m1 = pre[k] / k
        m2 = (pre[n] - pre[k]) / (n - k)
        s = k * (n - k) * (m1 - m2) ** 2
        if s > best:
            best, bk = s, k
    lo, hi = median(v[:bk]), median(v[bk:])
    for _ in range(3):
        a = [x for x in v if abs(x - lo) <= tol and abs(x - lo) <= abs(x - hi)]
        b = [x for x in v if abs(x - hi) <= tol and abs(x - hi) < abs(x - lo)]
        if len(a) < min_plateau or len(b) < min_plateau:
            return one
        lo, hi = median(a), median(b)
    if hi - lo < min_gap:
        return one
    return (lo, hi)


def segment(wins, tol=TOL, min_gap=MIN_GAP, min_plateau=MIN_PLATEAU, gap_s=GAP_S):
    """Two-level description of one window sequence.

    wins: list of (t_start_s, t_end_s, rate_GBps) in time order.
    Returns a dict:
      low, high      level medians (high is None for one level; then low is the median of all)
      labels         per window: 'low', 'high', 'mixed', 'off', or 'one' (one level, within tol)
      switches       list of dicts: kind 'up' or 'down', t (s, est.), t_lo, t_hi (bounds), how
                     ('mixed': from mixed windows, 'boundary': between two adjacent windows,
                      'gap': the windows around it are not contiguous, t is the middle of the bounds)
      excursions     list of dicts: level (the level before and after), t_lo, t_hi, other_s (est. time
                     at the other level, assuming an abrupt there-and-back)
      share_high     est. share of the window time at the high level (mixed windows count by fraction)
    """
    rates = [w[2] for w in wins]
    lo, hi = find_levels(rates, tol, min_gap, min_plateau)
    res = {"low": lo, "high": hi, "labels": [], "switches": [], "excursions": [], "share_high": None,
           "n": len(wins)}
    if lo is None:
        return res
    if hi is None:
        res["labels"] = ["one" if abs(r - lo) <= tol else "mixed" for r in rates]
        # excursions away from the single level
        i = 0
        while i < len(wins):
            if res["labels"][i] == "mixed":
                j = i
                while j + 1 < len(wins) and res["labels"][j + 1] == "mixed":
                    j += 1
                res["excursions"].append({"level": "one", "t_lo": wins[i][0], "t_hi": wins[j][1],
                                          "other_s": None,
                                          "extreme": max((rates[k] for k in range(i, j + 1)),
                                                         key=lambda r: abs(r - lo))})
                i = j + 1
            else:
                i += 1
        return res
    labels = []
    for r in rates:
        if abs(r - lo) <= tol and abs(r - lo) <= abs(r - hi):
            labels.append("low")
        elif abs(r - hi) <= tol:
            labels.append("high")
        elif lo < r < hi:
            labels.append("mixed")
        else:
            labels.append("off")
    res["labels"] = labels
    span = hi - lo

    def frac_high(r):
        return min(1.0, max(0.0, (r - lo) / span))

    tot = sum(w[1] - w[0] for w in wins)
    if tot > 0:
        res["share_high"] = sum((w[1] - w[0]) * frac_high(w[2]) for w in wins) / tot
    prev = None                       # index of the last window that sits on a level
    for i, lab in enumerate(labels):
        if lab not in ("low", "high"):
            continue
        if prev is not None:
            run = range(prev + 1, i)
            # is the stretch prev..i contiguous?
            contiguous = all(wins[k + 1][0] - wins[k][1] <= gap_s for k in range(prev, i))
            t_lo, t_hi = wins[prev][1], wins[i][0]
            old = labels[prev]
            if lab != old:
                kind = "up" if lab == "high" else "down"
                if not contiguous:
                    t, how = 0.5 * (t_lo + t_hi), "gap"
                elif len(run) == 0:
                    t, how = 0.5 * (t_lo + t_hi), "boundary"
                else:
                    t = wins[prev + 1][0]
                    for k in run:
                        f_old = frac_high(rates[k]) if old == "high" else 1.0 - frac_high(rates[k])
                        t += f_old * (wins[k][1] - wins[k][0])
                    how = "mixed"
                res["switches"].append({"kind": kind, "t": t, "t_lo": t_lo, "t_hi": t_hi, "how": how,
                                        "contiguous": contiguous})
            elif len(run) > 0:
                other = 0.0
                for k in run:
                    f_old = frac_high(rates[k]) if old == "high" else 1.0 - frac_high(rates[k])
                    other += (1.0 - f_old) * (wins[k][1] - wins[k][0])
                if other >= 0.03:
                    res["excursions"].append({"level": old, "t_lo": t_lo, "t_hi": t_hi, "other_s": other,
                                              "contiguous": contiguous})
        prev = i
    return res


def segment_proc(proc, group=None):
    """Segmentation of the main kernel@size sequence of a process. Returns (windows, seg) or (windows, None)."""
    ws = proc.group_windows(group)
    if len(ws) < MIN_SEQ:
        return ws, None
    return ws, segment([(w.ts, w.te, w.rate) for w in ws])


def ups(seg):
    return [s["t"] for s in seg["switches"] if s["kind"] == "up"]


def downs(seg):
    return [s["t"] for s in seg["switches"] if s["kind"] == "down"]


# ------------------------------------------------------------------ period fits and circular statistics
def lsq_line(n, t):
    """t = a + p*n by least squares. Returns (a, p, rms of the residuals)."""
    k = len(n)
    mn, mt = sum(n) / float(k), sum(t) / float(k)
    sxx = sum((x - mn) ** 2 for x in n)
    if sxx == 0:
        return None
    p = sum((x - mn) * (y - mt) for x, y in zip(n, t)) / sxx
    a = mt - p * mn
    rms = math.sqrt(sum((y - a - p * x) ** 2 for x, y in zip(n, t)) / k)
    return a, p, rms


def circ(times, period):
    """Resultant length R (0: spread evenly, 1: all at one phase), mean phase (s), circular sd (s)."""
    if not times:
        return None
    z = sum(cmath.exp(2j * math.pi * t / period) for t in times) / len(times)
    r = abs(z)
    ph = (cmath.phase(z) / (2 * math.pi) * period) % period
    sd = math.sqrt(-2.0 * math.log(r)) * period / (2 * math.pi) if 0 < r < 1 else (0.0 if r >= 1 else None)
    return r, ph, sd


def fit_period(times, p0=None):
    """Least-squares period and phase of event times that repeat with one period (cycles may be missing).

    p0: start period; default the median of the consecutive intervals. Each time gets the index
    round((t - phase) / period); a straight line through (index, time) gives period and phase; three rounds.
    Returns dict(period, phase (time of index 0, reduced into [0, period)), rms, n, indices) or None.
    """
    t = sorted(times)
    if len(t) < 3:
        return None
    if p0 is None:
        p0 = median([b - a for a, b in zip(t, t[1:])])
    if not p0 or p0 <= 0:
        return None
    p, a = p0, t[0]
    idx = None
    for _ in range(3):
        idx = [int(round((x - a) / p)) for x in t]
        r = lsq_line(idx, t)
        if r is None:
            return None
        a, p, rms = r
        if p <= 0:
            return None
    shift = int(math.floor(a / p))
    return {"period": p, "phase": a - shift * p, "rms": rms, "n": len(t),
            "indices": [i + shift for i in idx]}


def fit_pooled(per_proc, p0=None):
    """One period and one phase for the event times of several processes (times since process start).

    per_proc: list of lists of times. Returns the dict of fit_period, with 'distinct' = number of distinct
    indices, or None if the times fall on fewer than 3 distinct indices (then no period is fitted).
    """
    allt = [x for ts in per_proc for x in ts]
    if len(allt) < 3:
        return None
    if p0 is None:
        iv = [b - a for ts in per_proc for a, b in zip(sorted(ts), sorted(ts)[1:])]
        p0 = median(iv)
    if not p0 or p0 <= 0:
        return None
    p = p0
    a = circ(allt, p)[1]
    idx = None
    for _ in range(4):
        idx = [int(round((x - a) / p)) for x in allt]
        if len(set(idx)) < 3:
            return None
        a, p, rms = lsq_line(idx, allt)
        if p <= 0:
            return None
    return {"period": p, "phase": a % p, "rms": rms, "n": len(allt), "distinct": len(set(idx)),
            "phase0": a}


def wallclock_test(per_proc, period, rel=0.05, draws=100, seed=9, alias_r=0.5):
    """Are the event times tied to the process start or to the wall clock, for periods near `period`?

    per_proc: list of (launch second of the day, [event times since process start]).
    For every period P of a scan of period*(1 +- rel): R of (time since process start) mod P and R of
    (launch second + time) mod P.
    Aliased periods: if the launch times themselves have one phase modulo P (their R is above alias_r),
    then "since process start" and "wall clock" are the same statement at that P, and the scan of the
    wall-clock value leaves that P out.
    The null of the wall-clock value: the same scan after every process got a random launch offset
    (this keeps the pattern inside each process and removes any common wall-clock phase).
    Returns a dict of the largest R values and the null median and 95th percentile.
    """
    per_proc = [(l, ts) for l, ts in per_proc if ts and l is not None]
    if len(per_proc) < 2:
        return None
    l0 = min(l for l, _ in per_proc)
    span = max(l + max(ts) for l, ts in per_proc) - l0
    step = max(1e-4, 0.03 * period * period / max(span, period))
    nstep = int(min(4000, max(1, math.ceil(rel * period / step))))
    grid = [period + k * step for k in range(-nstep, nstep + 1)]
    launches = [float(l - l0) for l, _ in per_proc]
    aliased = [circ(launches, P)[0] > alias_r for P in grid]

    def r_at(P, offsets):
        w = 2 * math.pi / P
        sr = si = 0.0
        n = 0
        for off, (_, ts) in zip(offsets, per_proc):
            for t in ts:
                sr += math.cos(w * (off + t))
                si += math.sin(w * (off + t))
                n += 1
        return math.hypot(sr, si) / n

    def scan(offsets, skip_aliased):
        best, bp = None, None
        for P, al in zip(grid, aliased):
            if skip_aliased and al:
                continue
            r = r_at(P, offsets)
            if best is None or r > best:
                best, bp = r, P
        return best, bp

    zero = [0.0] * len(per_proc)
    r_rel, p_rel = scan(zero, False)
    r_wall, p_wall = scan(launches, True)
    r_wall_any, p_wall_any = scan(launches, False)
    rng = random.Random(seed)
    null = []
    if r_wall is not None:
        null = sorted(scan([rng.uniform(0, 1000.0 * period) for _ in per_proc], True)[0] for _ in range(draws))
    n_ev = sum(len(ts) for _, ts in per_proc)
    return {"period": period, "scan_lo": grid[0], "scan_hi": grid[-1], "scan_step": step,
            "r_rel": r_rel, "p_rel": p_rel, "r_wall": r_wall, "p_wall": p_wall,
            "r_wall_any": r_wall_any, "p_wall_any": p_wall_any,
            "r_wall_at_rel": r_at(p_rel, launches), "r_launch_at_rel": circ(launches, p_rel)[0],
            "aliased": sum(aliased), "grid_n": len(grid),
            "null_median": median(null), "null_p95": percentile(null, 95), "null_max": null[-1] if null else None,
            "draws": draws, "nproc": len(per_proc), "nevents": n_ev, "seed": seed}


def clusters(per_proc, width=0.15):
    """Groups of event times (since process start) that recur across processes.

    per_proc: list of lists of times. Sorted pooled times are cut wherever two neighbours are more than
    `width` apart. Returns a list of dicts: mean, sd, lo, hi, n (events), nproc (processes with an event)."""
    allt = sorted((t, i) for i, ts in enumerate(per_proc) for t in ts)
    out, cur = [], []
    for t, i in allt:
        if cur and t - cur[-1][0] > width:
            out.append(cur)
            cur = []
        cur.append((t, i))
    if cur:
        out.append(cur)
    res = []
    for c in out:
        ts = [t for t, _ in c]
        m = sum(ts) / len(ts)
        res.append({"mean": m, "sd": math.sqrt(sum((x - m) ** 2 for x in ts) / len(ts)), "lo": ts[0],
                    "hi": ts[-1], "n": len(ts), "nproc": len(set(i for _, i in c))})
    return res


def histogram(times, bin_s=BIN_S):
    h = {}
    for t in times:
        b = int(math.floor(t / bin_s + 1e-9))
        h[b] = h.get(b, 0) + 1
    return h


def print_hist(title, times, out, bin_s=BIN_S):
    out.append("  %s: n=%d" % (title, len(times)))
    h = histogram(times, bin_s)
    for b in sorted(h):
        out.append("    %6.1f s  %3d  %s" % (b * bin_s, h[b], "#" * min(h[b], 60)))


# ------------------------------------------------------------------ (c) switches
def cmd_switches(args):
    out = []
    periods = [float(x) for x in args.periods.split(",") if x]
    sizes = set(parse_size(x) for x in args.sizes.split(",")) if args.sizes else None
    out.append("levels9.py switches. Rates in GB/s (1 GB = 1e9 bytes). Times in s since process start.")
    out.append("Level rule: a level needs %d windows within %.1f GB/s of its median, and the two medians "
               "are at least %.1f GB/s apart." % (MIN_PLATEAU, TOL, MIN_GAP))
    out.append("Every switch time is est.: one abrupt switch inside the mixed windows is assumed. "
               "(b) after a time: the switch sits on a window boundary. (g): the windows around it are "
               "not contiguous.")
    for path in csv_paths(args.paths):
        procs = parse_csv(path)
        out.append("")
        out.append("=" * 100)
        out.append("FILE %s  (%d processes)" % (path, len(procs)))
        out.append("=" * 100)
        rows = []
        for p in procs:
            if sizes is not None and p.size not in sizes:
                continue
            ws, seg = segment_proc(p)
            rows.append((p, ws, seg))
            head = "idx %-3s %-24s K=%-10s S=%-5s cpu=%-3s ses=%s utc=%s" % (
                p.hdr.get("idx", "-"), p.tag, p.kernel, size_name(p.size), p.cpu, p.session, p.utc)
            for note in p.notes():
                out.append("idx %-3s %-24s NOTE: %s" % (p.hdr.get("idx", "-"), p.tag, note))
            if seg is None:
                out.append("%s  too few windows (%d)" % (head, len(ws)))
                continue
            if seg["high"] is None:
                ex = ""
                if seg["excursions"]:
                    ex = "  off-level windows at " + " ".join(
                        "%.1f-%.1f(%.1f)" % (e["t_lo"], e["t_hi"], e["extreme"]) for e in seg["excursions"])
                out.append("%s  one level %.2f%s" % (head, seg["low"], ex))
            else:
                def tt(s):
                    return "%.2f%s" % (s["t"], {"mixed": "", "boundary": "(b)", "gap": "(g)"}[s["how"]])
                u = [tt(s) for s in seg["switches"] if s["kind"] == "up"]
                d = [tt(s) for s in seg["switches"] if s["kind"] == "down"]
                first = next((l for l in seg["labels"] if l in ("low", "high")), "-")
                out.append("%s  low %.2f high %.2f  share high %.3f (est.)  starts %s" % (
                    head, seg["low"], seg["high"], seg["share_high"], first))
                out.append("        up   (est.): %s" % (" ".join(u) or "none"))
                out.append("        down (est.): %s" % (" ".join(d) or "none"))
                if seg["excursions"]:
                    out.append("        excursions (level, from-to, est. s at the other level): %s" % " ".join(
                        "%s:%.1f-%.1f:%.2f" % (e["level"], e["t_lo"], e["t_hi"], e["other_s"])
                        for e in seg["excursions"]))
                f = fit_period(ups(seg))
                if f:
                    out.append("        up fit: period %.3f s, phase %.3f s, rms %.3f s, n=%d, indices %s" % (
                        f["period"], f["phase"], f["rms"], f["n"], f["indices"]))
            tr = p.trial_starts()
            if len(tr) == 1 and tr[0][2] is not None and tr[0][2] - tr[0][1] > GAP_S:
                out.append("        target starts at %.2f s (after the previous activity)" % tr[0][2])
            if len(tr) > 1 and seg is not None and seg["high"] is not None:
                out.append("        trial starts: %s ; target starts: %s" % (
                    " ".join("%.2f" % a for _, a, _ in tr),
                    " ".join("%.2f" % b for _, _, b in tr if b is not None)))
        # ---- pooled per size
        two = [(p, ws, seg) for p, ws, seg in rows if seg is not None and seg["high"] is not None]
        out.append("")
        out.append("-" * 100)
        out.append("POOLED, %s" % path)
        szs = sorted(set(p.size for p, _, _ in rows))
        for sz in szs:
            allp = [(p, seg) for p, ws, seg in rows if p.size == sz and seg is not None]
            grp = [(p, seg) for p, ws, seg in two if p.size == sz]
            out.append("")
            out.append("SIZE %s: %d processes, %d with two levels" % (size_name(sz), len(allp), len(grp)))
            kc = {}
            for p, seg in allp:
                a = kc.setdefault((p.kernel, p.cpu), [0, 0, 0, 0])
                a[0] += 1
                if seg["high"] is not None:
                    a[1] += 1
                    a[2] += len(ups(seg))
                    a[3] += len(downs(seg))
            for (k, c) in sorted(kc):
                a = kc[(k, c)]
                lv = [(seg["low"], seg["high"]) for p, seg in grp if (p.kernel, p.cpu) == (k, c)]
                extra = ""
                if lv:
                    extra = "  median low %.2f, median high %.2f" % (median([x for x, _ in lv]),
                                                                    median([y for _, y in lv]))
                out.append("  %-10s cpu %-3s: %d processes, %d with two levels, %d up, %d down%s" % (
                    k, c, a[0], a[1], a[2], a[3], extra))
            conds = sorted(set(p.cond for p, _ in allp))
            if len(conds) > 1:
                out.append("  first up time per condition and cpu (est.; one value per process, '-' = no up "
                           "switch). 'since first window' = minus the start of the first window of this kernel "
                           "and size (after a previous activity of another kernel or size):")
                for cd in conds:
                    for c in sorted(set(p.cpu for p, _ in allp if p.cond == cd)):
                        a, b = [], []
                        for p, seg in allp:
                            if p.cond != cd or p.cpu != c:
                                continue
                            u = ups(seg) if seg["high"] is not None else []
                            gw = p.group_windows()
                            t0 = gw[0].ts if gw else 0.0
                            a.append(min(u) if u else None)
                            b.append(min(u) - t0 if u else None)
                        va, vb = [x for x in a if x is not None], [x for x in b if x is not None]
                        out.append("    %-34s cpu %-3s since start [%s] median %s ; since first window [%s] median %s" % (
                            cd, c, " ".join("-" if x is None else "%.2f" % x for x in a), fmt(median(va)),
                            " ".join("-" if x is None else "%.2f" % x for x in b), fmt(median(vb))))
            if not grp:
                continue
            U = [t for p, seg in grp for t in ups(seg)]
            D = [t for p, seg in grp for t in downs(seg)]
            print_hist("up times since process start (bin %.1f s)" % BIN_S, U, out)
            print_hist("down times since process start (bin %.1f s)" % BIN_S, D, out)
            for c in sorted(set(p.cpu for p, _ in grp)):
                Uc = [t for p, seg in grp for t in ups(seg) if p.cpu == c]
                Dc = [t for p, seg in grp for t in downs(seg) if p.cpu == c]
                out.append("  cpu %s: up n=%d median %s range %s..%s ; down n=%d median %s range %s..%s" % (
                    c, len(Uc), fmt(median(Uc)), fmt(min(Uc) if Uc else None), fmt(max(Uc) if Uc else None),
                    len(Dc), fmt(median(Dc)), fmt(min(Dc) if Dc else None), fmt(max(Dc) if Dc else None)))
            # dwell times
            lowd, highd, upiv = [], [], []
            for p, seg in grp:
                sw = seg["switches"]
                for a, b in zip(sw, sw[1:]):
                    if a["kind"] == "down" and b["kind"] == "up":
                        lowd.append(b["t"] - a["t"])
                    if a["kind"] == "up" and b["kind"] == "down":
                        highd.append(b["t"] - a["t"])
                u = ups(seg)
                upiv.extend(b - a for a, b in zip(u, u[1:]))
            if upiv:
                out.append("  intervals between consecutive up switches of one process (s): n=%d median %.2f "
                           "p5 %.2f p95 %.2f" % (len(upiv), median(upiv), percentile(upiv, 5),
                                                 percentile(upiv, 95)))
                print_hist("up-to-up intervals (bin %.1f s)" % BIN_S, upiv, out)
            if lowd:
                out.append("  time at low between a down and the next up (s): n=%d median %.2f min %.2f max %.2f"
                           % (len(lowd), median(lowd), min(lowd), max(lowd)))
            if highd:
                out.append("  time at high between an up and the next down (s): n=%d median %.2f min %.2f "
                           "max %.2f" % (len(highd), median(highd), min(highd), max(highd)))
            # pooled fit
            per = [ups(seg) for p, seg in grp]
            f = fit_pooled(per)
            cands = list(periods)
            if f:
                out.append("  pooled fit of the up times (one period and one phase for all processes, time "
                           "since process start): period %.3f s, phase %.3f s, rms %.3f s, n=%d, %d distinct "
                           "indices" % (f["period"], f["phase"], f["rms"], f["n"], f["distinct"]))
                cands = [f["period"]] + cands
            else:
                out.append("  pooled fit of the up times: none (fewer than 3 up times, or fewer than 3 distinct indices)")
                if U:
                    m = sum(U) / len(U)
                    sd = math.sqrt(sum((x - m) ** 2 for x in U) / len(U))
                    out.append("  up times since process start: mean %.3f s, sd %.3f s, n=%d" % (m, sd, len(U)))
            if not U:
                continue
            # modulo table
            out.append("  up times modulo candidate periods. R is the resultant length: 1 = all at one phase, "
                       "about 1/sqrt(n) = no common phase.")
            out.append("  'since start' uses time since process start. 'wall clock' uses launch second (utc of "
                       "the launch line, 1 s resolution) + time.")
            out.append("    %9s  %28s  %28s" % ("period s", "since start: R, phase, sd s", "wall clock: R, phase, sd s"))
            for P in cands:
                a = circ(U, P)
                wl = [p.launch_s + t for p, seg in grp for t in ups(seg) if p.launch_s is not None]
                b = circ(wl, P) if wl else None
                out.append("    %9.3f  %28s  %28s" % (
                    P, "%.3f, %.2f, %s" % (a[0], a[1], fmt(a[2])),
                    "%.3f, %.2f, %s" % (b[0], b[1], fmt(b[2])) if b else "NA"))
            if f:
                P = f["period"]
                out.append("  up times modulo the fitted period %.3f s, per process:" % P)
                for p, seg in grp:
                    u = ups(seg)
                    if u:
                        out.append("    idx %-3s %-22s cpu %-3s utc %s : since start %s ; wall clock %s" % (
                            p.hdr.get("idx", "-"), p.tag, p.cpu, p.utc, fl([t % P for t in u]),
                            fl([(p.launch_s + t) % P for t in u]) if p.launch_s is not None else "NA"))
            for P in cands[:1] if f else cands:
                wt = wallclock_test([(p.launch_s, ups(seg)) for p, seg in grp], P)
                if wt:
                    out.append("  wall-clock test near %.3f s (scan %.3f to %.3f s, step %.4f s; %d processes, "
                               "%d up times):" % (P, wt["scan_lo"], wt["scan_hi"], wt["scan_step"],
                                                  wt["nproc"], wt["nevents"]))
                    out.append("    largest R, time since process start: %.3f at %.3f s. At that period: R of the "
                               "wall clock %.3f, R of the launch times alone %.3f" % (
                                   wt["r_rel"], wt["p_rel"], wt["r_wall_at_rel"], wt["r_launch_at_rel"]))
                    out.append("    aliased periods (the launch times alone have R above 0.5, so wall clock and "
                               "process start cannot be told apart there): %d of %d scan points" % (
                                   wt["aliased"], wt["grid_n"]))
                    if wt["r_wall"] is None:
                        out.append("    largest R, wall clock, periods that are not aliased: none (every scan "
                                   "point is aliased)")
                    else:
                        out.append("    largest R, wall clock, periods that are not aliased: %.3f at %.3f s" % (
                            wt["r_wall"], wt["p_wall"]))
                        out.append("    the same with random launch offsets (%d draws, seed %d): median %.3f, "
                                   "95th percentile %.3f, max %.3f" % (wt["draws"], wt["seed"], wt["null_median"],
                                                                        wt["null_p95"], wt["null_max"]))
                    out.append("    largest R, wall clock, all periods: %.3f at %.3f s" % (
                        wt["r_wall_any"], wt["p_wall_any"]))
            # recurring times
            wl = median([w.te - w.ts for p, seg in grp for w in p.group_windows()])
            for name, fn in (("up", ups), ("down", downs)):
                cl = [c for c in clusters([fn(seg) for p, seg in grp]) if c["nproc"] >= 3]
                out.append("  %s times that recur in at least 3 of the %d processes (pooled times cut at gaps "
                           "above 0.15 s). 'windows' = mean / the median window length %.4f s:" % (
                               name, len(grp), wl))
                if not cl:
                    out.append("    none")
                prev_m = None
                for c in cl:
                    out.append("    mean %7.3f s  sd %.3f s  range %.2f..%.2f  in %2d processes (%d events)  "
                               "windows %7.2f%s" % (c["mean"], c["sd"], c["lo"], c["hi"], c["nproc"], c["n"],
                                                    c["mean"] / wl,
                                                    "" if prev_m is None else "  step from the row above %.2f s"
                                                    % (c["mean"] - prev_m)))
                    prev_m = c["mean"]
            # times since the start of the trial that holds the switch
            if any(len(p.trial_starts()) > 1 for p, seg in grp):
                for name, fn in (("up", ups), ("down", downs)):
                    rel_t = []
                    for p, seg in grp:
                        st = [a for _, a, _ in p.trial_starts()]
                        for t in fn(seg):
                            b = [a for a in st if a <= t]
                            if b:
                                rel_t.append(t - b[-1])
                    print_hist("%s times since the start of the trial that holds them (bin %.1f s)" % (name, BIN_S),
                               rel_t, out)
                ts0 = [a for p, seg in grp for _, a, _ in p.trial_starts()]
                out.append("  trial starts since process start: %s" % " ".join(
                    "%.2f(x%d)" % (c["mean"], c["n"]) for c in clusters([ts0], width=0.05)))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ (d) counters
def counter_windows(proc):
    """Per counted target window of the main sequence: dict with level, rate, bytes, pass_bytes, counts, mux."""
    ws, seg = segment_proc(proc)
    lab = {}
    if seg is not None:
        for w, l in zip(ws, seg["labels"]):
            lab[(w.trial, w.phase, w.widx)] = l
    grp = proc.main_group()
    out = []
    for w in proc.W:
        if w.phase != "target" or (w.kernel, w.pass_bytes) != grp:
            continue
        c = proc.C.get((w.trial, w.widx))
        if c is None:
            continue
        mux = (c["enabled_ns"] is None or c["running_ns"] is None or c["enabled_ns"] != c["running_ns"])
        out.append({"trial": w.trial, "widx": w.widx,
                    "level": lab.get((w.trial, "target", w.widx), "unsplit" if seg is None else "none"),
                    "rate": w.rate, "bytes": w.bytes, "pass_bytes": w.pass_bytes, "counts": c["counts"],
                    "mux": mux, "t": w.ts})
    return out


# 'unsplit': a process with fewer than MIN_SEQ windows; no level description is made for it.
LEVELS = ("low", "high", "one", "unsplit")


def per64(count, nbytes):
    return None if count is None else count * 64.0 / nbytes


def per_pass(count, nbytes, pass_bytes):
    return None if count is None else count * float(pass_bytes) / nbytes


def level_stats(wins, events):
    """Medians over the given windows: per event (per 64 B, per pass), rate, cycles/byte, instructions/byte."""
    res = {"n": len(wins), "rate": median([w["rate"] for w in wins]), "per64": {}, "per_pass": {}}
    for i, e in enumerate(events):
        a = [per64(w["counts"][i], w["bytes"]) for w in wins if i < len(w["counts"]) and w["counts"][i] is not None]
        b = [per_pass(w["counts"][i], w["bytes"], w["pass_bytes"]) for w in wins
             if i < len(w["counts"]) and w["counts"][i] is not None]
        res["per64"][e] = median(a)
        res["per_pass"][e] = median(b)
    for name, key in (("cpu_cycles", "cyc_per_byte"), ("inst_retired", "ins_per_byte")):
        if name in events:
            i = events.index(name)
            a = [w["counts"][i] / float(w["bytes"]) for w in wins
                 if i < len(w["counts"]) and w["counts"][i] is not None]
            res[key] = median(a)
        else:
            res[key] = None
    return res


def counter_table(procs):
    """Cells keyed by (step, events, kernel, size, cpu, session). Each cell: per level pooled stats, per process
    stats, low-minus-high differences per process, and the count of multiplexed windows."""
    cells = {}
    for p in procs:
        ev = p.events
        if not ev or not p.C:
            continue
        wins = counter_windows(p)
        if not wins:
            continue
        key = (p.step, ",".join(ev), p.kernel, p.size, p.cpu, p.session)
        cell = cells.setdefault(key, {"events": ev, "procs": [], "mux": 0, "windows": 0})
        cell["windows"] += len(wins)
        cell["mux"] += sum(1 for w in wins if w["mux"])
        good = [w for w in wins if not w["mux"]]
        per = {}
        for lev in LEVELS:
            sel = [w for w in good if w["level"] == lev]
            if sel:
                per[lev] = level_stats(sel, ev)
        cell["procs"].append({"proc": p, "levels": per, "wins": good,
                              "mixed": sum(1 for w in good if w["level"] in ("mixed", "off", "none"))})
    for cell in cells.values():
        ev = cell["events"]
        cell["pooled"] = {}
        for lev in LEVELS:
            sel = [w for q in cell["procs"] for w in q["wins"] if w["level"] == lev]
            if sel:
                cell["pooled"][lev] = level_stats(sel, ev)
        diffs = {e: [] for e in ev}
        extra = {"rate": [], "cyc_per_byte": [], "ins_per_byte": []}
        for q in cell["procs"]:
            lv = q["levels"]
            if "low" in lv and "high" in lv:
                for e in ev:
                    a, b = lv["low"]["per64"][e], lv["high"]["per64"][e]
                    diffs[e].append((q["proc"], None if a is None or b is None else a - b))
                for k in extra:
                    a, b = lv["low"][k], lv["high"][k]
                    extra[k].append((q["proc"], None if a is None or b is None else a - b))
        cell["diff"] = diffs
        cell["diff_extra"] = extra
    return cells


def g(x):
    return "NA" if x is None else "%.6g" % x


def cmd_counters(args):
    procs = load(args.paths)
    cells = counter_table(procs)
    out = ["levels9.py counters. Medians over target windows. 'per 64 B' = count x 64 / bytes of the window. "
           "'per pass' = count x size / bytes.",
           "A window with enabled_ns != running_ns is multiplexed and left out. Mixed and off-level windows "
           "are left out of every level.",
           "Level 'one' = a process with one level. Level 'unsplit' = a process with fewer than %d windows: "
           "all its windows, no level description." % MIN_SEQ,
           "Event names are the raw names of M,events; no cache "
           "mechanism is assigned to them here."]
    if not cells:
        out.append("no counted windows found")
    for key in sorted(cells):
        step, evs, kernel, size, cpu, ses = key
        cell = cells[key]
        ev = cell["events"]
        out.append("")
        out.append("CELL step=%s K=%s S=%s cpu=%s ses=%s : %d processes, %d counted windows, %d multiplexed "
                   "(left out)" % (step, kernel, size_name(size), cpu, ses, len(cell["procs"]), cell["windows"],
                                   cell["mux"]))
        for lev in LEVELS:
            st = cell["pooled"].get(lev)
            if not st:
                continue
            out.append("  level %-7s: %d windows, rate %.2f GB/s, cycles/byte %s, instructions/byte %s" % (
                lev, st["n"], st["rate"], g(st["cyc_per_byte"]), g(st["ins_per_byte"])))
            for e in ev:
                out.append("      %-22s per 64 B %-12s per pass %-12s" % (e, g(st["per64"][e]), g(st["per_pass"][e])))
        out.append("  per process (median over its windows of the level):")
        for q in cell["procs"]:
            p = q["proc"]
            for lev in LEVELS:
                st = q["levels"].get(lev)
                if st:
                    out.append("    idx %-3s %-20s %-7s n=%-3d rate %.2f cyc/B %s ins/B %s | per 64 B: %s" % (
                        p.hdr.get("idx", "-"), p.tag, lev, st["n"], st["rate"], g(st["cyc_per_byte"]),
                        g(st["ins_per_byte"]), " ".join("%s=%s" % (e, g(st["per64"][e])) for e in ev)))
            for note in p.notes():
                out.append("    idx %-3s %-20s NOTE: %s" % (p.hdr.get("idx", "-"), p.tag, note))
            if q["mixed"]:
                out.append("    idx %-3s %-20s %d mixed or off-level windows left out" % (
                    p.hdr.get("idx", "-"), p.tag, q["mixed"]))
        if any(cell["diff"][e] for e in ev):
            out.append("  low minus high, per process that has both levels (then the median of the process values):")
            for name, lst in (("rate GB/s", cell["diff_extra"]["rate"]),
                              ("cycles/byte", cell["diff_extra"]["cyc_per_byte"]),
                              ("instructions/byte", cell["diff_extra"]["ins_per_byte"])):
                vals = [d for _, d in lst if d is not None]
                if vals:
                    out.append("      %-22s %s  median %s" % (name, "[" + " ".join(g(d) for d in vals) + "]",
                                                            g(median(vals))))
            for e in ev:
                vals = [d for _, d in cell["diff"][e] if d is not None]
                if vals:
                    out.append("      %-22s per 64 B %s  median %s" % (e, "[" + " ".join(g(d) for d in vals) + "]",
                                                                    g(median(vals))))
        else:
            out.append("  low minus high: no process of this cell has both levels")
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ (e) watch
# Sampler file (X/hostwatch.py writes it; only this format is shared with it):
#   header lines start with "#" and hold key=value tokens, among them mono_ns, boot_ns, starttime_ticks,
#   clk_tck, and (hostwatch v1) hz and, in the last line, samples.
#   sample lines: "<t_mono_ns> key=delta key:=state ...". hostwatch v1 writes a line only when something
#   changed, so a sample slot without a line had no change. "<t_mono_ns> ABS key=value ..." lines hold
#   absolute values; they are not changes and are left out here.
# A change that a line reports happened in (t - lookback, t]. lookback is one sample slot (1 / hz), or the
# distance to the line before if the header has no hz. Keys that the sampler reads less often get a longer
# lookback (LOOKBACK below; taken from the text of hostwatch.py).
LOOKBACK = (("irq.", None, 0.5), ("th.", ".new", 2.0))     # (key prefix, key suffix or None, seconds)
TID = re.compile(r"^th\.\d+\.")


def lookback_of(key, slot):
    for pre, suf, sec in LOOKBACK:
        if key.startswith(pre) and (suf is None or key.endswith(suf)):
            return max(sec, slot)
    return slot


def pooled_key(key):
    """Thread ids differ between processes: th.<tid>.<comm>.<f> is pooled as th.*.<comm>.<f>."""
    return TID.sub("th.*.", key)


class Watch:
    """One sampler file: header values, change events, and the sampled span."""

    def __init__(self, path):
        self.path = path
        self.head = {}
        self.lines = []          # (t_mono_ns, [(key, token, is_state)]) of the lines that are not ABS lines
        self.abs_lines = 0
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line.startswith("#"):
                    for tok in line[1:].split():
                        if "=" in tok:
                            k, v = tok.split("=", 1)
                            self.head.setdefault(k, v)
                    continue
                f2 = line.split()
                try:
                    t = int(f2[0])
                except ValueError:
                    continue
                if len(f2) > 1 and f2[1] == "ABS":
                    self.abs_lines += 1
                    self.lines.append((t, None))
                    continue
                d = []
                for tok in f2[1:]:
                    if ":=" in tok:
                        k, v = tok.split(":=", 1)
                        d.append((k, v, True))
                    elif "=" in tok:
                        k, v = tok.split("=", 1)
                        d.append((k, v, False))
                self.lines.append((t, d))
        self.lines.sort(key=lambda x: x[0])

    def start_mono_ns(self):
        """Process start on the monotonic clock, and the size of one clock tick, both in ns.
        start = starttime_ticks / clk_tck (boot-time clock) - (boot_ns - mono_ns)."""
        try:
            tck = float(self.head["clk_tck"])
            start_boot = float(self.head["starttime_ticks"]) / tck * 1e9
            return start_boot - (float(self.head["boot_ns"]) - float(self.head["mono_ns"])), 1e9 / tck
        except (KeyError, ValueError, ZeroDivisionError):
            return None, None

    def slot_s(self):
        """Length of one sample slot in s: 1 / hz of the header, else the median distance of the lines."""
        try:
            hz = float(self.head["hz"])
            if hz > 0:
                return 1.0 / hz, True
        except (KeyError, ValueError):
            pass
        ts = sorted(set(t for t, _ in self.lines))
        d = [(b - a) / 1e9 for a, b in zip(ts, ts[1:])]
        return (median(d) if d else 0.1), False

    def span(self):
        """(first, last) sampled time in s since process start, or None.
        First = the first line. Last = the last line, or first + (samples - 1) slots if the header gives hz and
        samples and that is later (the sampler writes no line for a slot without a change)."""
        s0, _ = self.start_mono_ns()
        if s0 is None or not self.lines:
            return None
        a, b = (self.lines[0][0] - s0) / 1e9, (self.lines[-1][0] - s0) / 1e9
        slot, known = self.slot_s()
        try:
            if known:
                b = max(b, a + (int(self.head["samples"]) - 1) * slot)
        except (KeyError, ValueError):
            pass
        return a, b

    def nslots(self):
        """Number of sample slots: 'samples' of the header's end line, else span / slot, else the lines."""
        try:
            return int(self.head["samples"])
        except (KeyError, ValueError):
            pass
        sp = self.span()
        slot, known = self.slot_s()
        if sp and known:
            return int(round((sp[1] - sp[0]) / slot)) + 1
        return len(set(t for t, _ in self.lines))

    def events(self):
        """Change events: list of (t_from_s, t_to_s, key, numeric delta or None), s since process start.

        A token key=delta is a change if delta is a number other than 0. A token key:=state is a change.
        A token key=text (not a number) is a change if the text differs from the last text of that key."""
        s0, _ = self.start_mono_ns()
        if s0 is None:
            return []
        slot, known = self.slot_s()
        out = []
        last_text = {}
        prev_t = None
        for t, d in self.lines:
            ts = (t - s0) / 1e9
            if d is not None:
                for k, v, is_state in d:
                    if is_state:
                        delta = None
                    else:
                        try:
                            delta = float(v)
                        except ValueError:
                            old = last_text.get(k)
                            last_text[k] = v
                            if old is None or old == v:
                                continue
                            delta = None
                        if delta is not None and delta == 0.0:
                            continue
                    lb = lookback_of(k, slot)
                    if not known and prev_t is not None:
                        lb = max(lb, ts - prev_t) if lb > slot else ts - prev_t
                    out.append((ts - lb, ts, k, delta))
            if prev_t is None or ts > prev_t:
                prev_t = ts
        return out


def watch_stats(events, switch_times, span, nslots, near=NEAR_S, grid=0.05, clip=None):
    """Per key: was there a change within +-near of each switch; base rates.

    events: list of (t_from, t_to, key, delta or None). switch_times: list of (kind, t).
    span: (first, last) sampled time. nslots: number of sample slots. clip: (from, to) of the windows of the
    process; the grid of the base rate stays inside both span and clip.
    Returns dict:
      keys           sorted key names
      per_switch     list of (kind, t, [keys with a change interval that overlaps (t-near, t+near)], covered)
      slots, slot_changed[key]            sample slots, and lines with a change of the key
      grid_n, grid_changed[key]           all intervals (g-near, g+near) for g on a grid of `grid` s: the base
                                          rate that is comparable with the switch shares
      near_sum[kind][key], near_dur[kind] sum of the numeric deltas near covered switches, and 2 x near per switch
      all_sum[key], all_dur               the same over the whole sampled span
    """
    by_key = {}
    for a, b, k, d in events:
        by_key.setdefault(k, []).append((a, b, d))
    keys = sorted(by_key)
    res = {"keys": keys, "per_switch": [], "slots": nslots,
           "slot_changed": {k: len(by_key[k]) for k in keys}, "grid_n": 0, "grid_changed": {k: 0 for k in keys},
           "near_sum": {"up": {k: 0.0 for k in keys}, "down": {k: 0.0 for k in keys}},
           "near_dur": {"up": 0.0, "down": 0.0},
           "all_sum": {k: sum(d for _, _, d in by_key[k] if d is not None) for k in keys},
           "all_dur": (span[1] - span[0]) if span else 0.0}
    if not span:
        for kind, t in switch_times:
            res["per_switch"].append((kind, t, [], False))
        return res
    t0, t1 = span
    for kind, t in switch_times:
        covered = t0 <= t - near and t + near <= t1
        hit = []
        for k in keys:
            tot, any_hit = 0.0, False
            for a, b, d in by_key[k]:
                if a < t + near and b > t - near:
                    any_hit = True
                    if d is not None:
                        tot += d
            if any_hit:
                hit.append(k)
                if covered and kind in res["near_sum"]:
                    res["near_sum"][kind][k] += tot
        res["per_switch"].append((kind, t, hit, covered))
        if covered and kind in res["near_dur"]:
            res["near_dur"][kind] += 2 * near
    lo, hi = t0 + near, t1 - near
    if clip is not None:
        lo, hi = max(lo, clip[0]), min(hi, clip[1])
    n = int(math.floor((hi - lo) / grid + 1e-9)) + 1 if hi >= lo else 0
    res["grid_n"] = n
    if n:
        for k in keys:
            marked = set()
            for a, b, d in by_key[k]:
                # grid points g with g - near < b and g + near > a
                q0 = int(math.floor((a - near - lo) / grid)) + 1
                q1 = int(math.ceil((b + near - lo) / grid)) - 1
                for q in range(max(q0, 0), min(q1, n - 1) + 1):
                    marked.add(q)
            res["grid_changed"][k] = len(marked)
    return res


def pool_watch(stats_list):
    """Pooled table over processes: key -> counts and sums. Only switches whose +-near interval lies fully
    inside the sampled span are counted. Thread ids are pooled (see pooled_key)."""
    n = {"up": 0, "down": 0}
    tab = {}
    slots = grid_n = 0

    def row(k):
        return tab.setdefault(k, {"up": 0, "down": 0, "slot": 0, "grid": 0, "sum_up": 0.0, "sum_down": 0.0,
                                  "sum_all": 0.0})

    for s in stats_list:
        slots += s["slots"]
        grid_n += s["grid_n"]
        for kind, t, ks, covered in s["per_switch"]:
            if covered and kind in n:
                n[kind] += 1
                for pk in set(pooled_key(k) for k in ks):
                    row(pk)[kind] += 1
        per = {}
        for k in s["keys"]:
            pk = pooled_key(k)
            r = row(pk)
            r["slot"] += s["slot_changed"][k]
            a = per.setdefault(pk, 0)
            per[pk] = a + s["grid_changed"][k]
            r["sum_up"] += s["near_sum"]["up"][k]
            r["sum_down"] += s["near_sum"]["down"][k]
            r["sum_all"] += s["all_sum"][k]
        for pk, c in per.items():
            tab[pk]["grid"] += min(c, s["grid_n"])       # several threads pooled: an upper bound of the union
    dur = {"up": sum(s["near_dur"]["up"] for s in stats_list),
           "down": sum(s["near_dur"]["down"] for s in stats_list),
           "all": sum(s["all_dur"] for s in stats_list)}
    return {"keys": sorted(tab), "n": n, "tab": tab, "dur": dur, "slots": slots, "grid_n": grid_n}


def watch_files(folder):
    out = {}
    for f in glob.glob(os.path.join(folder, "watch-*.txt")):
        m = re.match(r"^watch-0*(\d+)\.txt$", os.path.basename(f))
        if m:
            out[int(m.group(1))] = f
    return out


def watch_proc(proc, path, near=NEAR_S):
    """Aligns one sampler file with its process. Returns (Watch, stats or None, windows, switches)."""
    w = Watch(path)
    ws, seg = segment_proc(proc)
    sw = [(s["kind"], s["t"]) for s in seg["switches"]] if seg else []
    if w.start_mono_ns()[0] is None:
        return w, None, ws, sw
    clip = (ws[0].ts, ws[-1].te) if ws else None
    return w, watch_stats(w.events(), sw, w.span(), w.nslots(), near=near, clip=clip), ws, sw


def share(a, b):
    return "  NA " if not b else "%.3f" % (a / float(b))


def cmd_watch(args):
    near = args.near
    out = ["levels9.py watch. Times in s since process start. A key 'changed' if a sampler line reports a delta "
           "other than 0 or a new state (key:=value).",
           "'near' = the change interval of the line overlaps (switch - %.2f s, switch + %.2f s). The change "
           "interval is one sample slot before the line (0.5 s for irq.* keys, 2 s for th.*.new)." % (near, near),
           "Switch times are est. (see 'switches').",
           "Process start = starttime_ticks / clk_tck on the boot-time clock, moved to the monotonic clock with "
           "the mono_ns / boot_ns pair of the header.",
           "Alignment uncertainty: one clock tick (printed per folder), plus the unmeasured time from process "
           "creation to the first clock read of bwx8. ABS lines of the sampler are not used."]
    for folder in args.paths:
        procs = load([folder])
        wf = watch_files(folder)
        out.append("")
        out.append("=" * 100)
        out.append("FOLDER %s : %d processes, %d watch files" % (folder, len(procs), len(wf)))
        stats = []
        ticks = set()
        for p in procs:
            path = wf.get(p.idx)
            if path is None:
                continue
            w, st, ws, sw = watch_proc(p, path, near)
            if st is None:
                out.append("%s: %s has no usable header (needs mono_ns, boot_ns, starttime_ticks, clk_tck)" % (
                    p.label(), os.path.basename(path)))
                continue
            ticks.add(w.start_mono_ns()[1])
            stats.append(st)
            sp = w.span() or (0.0, 0.0)
            slot, known = w.slot_s()
            out.append("%s K=%s S=%s cpu=%s: sampled from %.2f to %.2f s, %d slots of %.3f s%s, %d lines with "
                       "changes, %d switches" % (
                           p.label(), p.kernel, size_name(p.size), p.cpu, sp[0], sp[1], st["slots"], slot,
                           "" if known else " (est. from the line distance: the header has no hz)",
                           sum(1 for _, d in w.lines if d), len(sw)))
            base = {k: (st["grid_changed"][k] / float(st["grid_n"]) if st["grid_n"] else 1.0) for k in st["keys"]}
            for kind, t, ks, covered in st["per_switch"]:
                ks = sorted(ks, key=lambda k: (base.get(k, 1.0), k))
                more = "" if len(ks) <= 30 else " (+%d more)" % (len(ks) - 30)
                out.append("    %-4s %8.2f%s: %s%s" % (kind, t, "" if covered else " (not fully sampled)",
                                                      " ".join(ks[:30]) or "no key changed", more))
        if not stats:
            out.append("no process with a usable watch file")
            continue
        pw = pool_watch(stats)
        out.append("")
        out.append("clock tick: %s ms" % ", ".join("%.1f" % (t / 1e6) for t in sorted(ticks)))
        out.append("POOLED: %d up switches, %d down switches (fully sampled ones only), %d sample slots" % (
            pw["n"]["up"], pw["n"]["down"], pw["slots"]))
        out.append("  share up / share down: share of the switches with a change of the key nearby.")
        out.append("  base(+-%.2f): share of all intervals of the same width, on a 0.05 s grid, with a change. "
                   "Compare the two shares with this column. For th.* keys it is an upper bound." % near)
        out.append("  base(slot): share of all sample slots with a change.")
        out.append("  rate columns: sum of the deltas per second, near up switches, near down switches, overall "
                   "(near: the deltas of the overlapping lines / (2 x %.2f s) per switch, so it is an upper "
                   "estimate)." % near)
        out.append("  %-40s %8s %10s %12s %10s %12s %12s %12s" % (
            "key", "share up", "share down", "base(+-%.2f)" % near, "base(slot)", "rate up", "rate down",
            "rate all"))

        def order(k):
            r = pw["tab"][k]
            b = r["grid"] / float(pw["grid_n"]) if pw["grid_n"] else 0.0
            u = r["up"] / float(pw["n"]["up"]) if pw["n"]["up"] else 0.0
            d = r["down"] / float(pw["n"]["down"]) if pw["n"]["down"] else 0.0
            return (-max(u - b, d - b), k)

        for k in sorted(pw["keys"], key=order):
            r = pw["tab"][k]
            out.append("  %-40s %8s %10s %12s %10s %12s %12s %12s" % (
                k, share(r["up"], pw["n"]["up"]), share(r["down"], pw["n"]["down"]),
                share(r["grid"], pw["grid_n"]), share(r["slot"], pw["slots"]),
                g(r["sum_up"] / pw["dur"]["up"]) if pw["dur"]["up"] else "NA",
                g(r["sum_down"] / pw["dur"]["down"]) if pw["dur"]["down"] else "NA",
                g(r["sum_all"] / pw["dur"]["all"]) if pw["dur"]["all"] else "NA"))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ (f) cells
def proc_cell_values(proc):
    """For one process of an S2-style step: dict(fourth, med_all, p5, p95, n) in GB/s, or None.

    fourth  = median over the trials of the rate of target window 3 (the fourth target window).
    med_all, p5, p95 = median, 5th and 95th percentile of the rates of all windows of the target kernel@size
              (prefix and target windows)."""
    grp = proc.main_group()
    if grp is None:
        return None
    ws = proc.group_windows(grp)
    if not ws:
        return None
    r = [w.rate for w in ws]
    f4 = [w.rate for w in ws if w.phase == "target" and w.widx == 3]
    return {"fourth": median(f4), "nfourth": len(f4), "med_all": median(r), "p5": percentile(r, 5),
            "p95": percentile(r, 95), "n": len(r)}


def cell_table(procs):
    cells = {}
    for p in procs:
        v = proc_cell_values(p)
        if v is None:
            continue
        key = (p.step, p.kernel, p.size, p.cpu, p.session)
        cells.setdefault(key, []).append((p, v))
    return cells


def cmd_cells(args):
    procs = load(args.paths)
    cells = cell_table(procs)
    out = ["levels9.py cells. Rates in GB/s (1 GB = 1e9 bytes). One value per process, in schedule order.",
           "fourth = median over the trials of the fourth target window. all = median of all windows of the "
           "kernel@size (prefix and target). p5, p95 = 5th and 95th percentile of those windows."]

    def cpu_key(k):
        return (k[0], k[2], k[1], int(k[3]) if str(k[3]).isdigit() else 0, k[4])

    for key in sorted(cells, key=cpu_key):
        step, kernel, size, cpu, ses = key
        lst = cells[key]
        out.append("")
        out.append("CELL step=%s K=%s S=%s cpu=%s ses=%s : %d processes (idx %s)" % (
            step, kernel, size_name(size), cpu, ses, len(lst), " ".join(p.hdr.get("idx", "-") for p, _ in lst)))
        for p, _ in lst:
            for note in p.notes():
                out.append("  NOTE idx %s %s: %s" % (p.hdr.get("idx", "-"), p.tag, note))
        for name in ("fourth", "med_all", "p5", "p95"):
            vals = [v[name] for _, v in lst if v[name] is not None]
            if not vals:
                out.append("  %-7s no value" % name)
                continue
            out.append("  %-7s %s  median %.2f  range %.2f (%.2f to %.2f)" % (
                {"med_all": "all"}.get(name, name), fl(vals), median(vals), max(vals) - min(vals), min(vals),
                max(vals)))
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ main
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    a = sub.add_parser("switches", help="levels and switch times per process, pooled timing per folder")
    a.add_argument("paths", nargs="+")
    a.add_argument("--periods", default="1,2,5,6.9,10", help="candidate periods in s for the modulo table")
    a.add_argument("--sizes", default="", help="only these sizes, for example 4M,8M,16M")
    a = sub.add_parser("counters", help="event counts per level for count-read processes")
    a.add_argument("paths", nargs="+")
    a = sub.add_parser("watch", help="sampler keys that change near the switches")
    a.add_argument("paths", nargs="+")
    a.add_argument("--near", type=float, default=NEAR_S)
    a = sub.add_parser("cells", help="per-process rate values of S2-style steps, per cell")
    a.add_argument("paths", nargs="+")
    args = ap.parse_args(argv)
    if not args.cmd:
        ap.print_help()
        return 2
    text = {"switches": cmd_switches, "counters": cmd_counters, "watch": cmd_watch, "cells": cmd_cells}[args.cmd](args)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
