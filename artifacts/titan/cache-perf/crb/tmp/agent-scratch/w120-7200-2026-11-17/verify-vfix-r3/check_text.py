#!/usr/bin/env python3
"""check_text.py - compares every number of the sentences that this correction added to FACTS.md with values computed
here from the raw files (own parser raw.py, no import of the generator). Prints PASS or FAIL per item. Reads only."""
import datetime as dt, os, re, sys
from decimal import Decimal, ROUND_HALF_UP
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from raw import R, ivs, one
S = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = open(S + "/FACTS.md").read()
q = lambda x: str(Decimal(repr(round(x, 6))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
sg = lambda x: "0.00" if float(q(x)) == 0 else (q(x) if x < 0 else "+" + q(x))
res = []
def chk(ok, what):
    res.append(ok); print("PASS" if ok else "FAIL", what)
def has(text, what=None):
    chk(text in MD, (what or "sentence present") + ": " + text[:150])
refs = dict(re.findall(r"^- \[(Ref\d+)\] `([^`]+)`", MD, re.M))

# ------------------------------------------------------------------ defect 3: records against every interval
recs = []
for i, l in enumerate(open(R + "/dimm-check-20261117/h-5.txt", errors="replace"), 1):
    m = re.match(r"(\S+?)\+00:00 \S+ kernel: \{(\d+)\}\[Hardware Error\]: Hardware error from APEI", l)
    if m: recs.append((dt.datetime.strptime(m[1], "%Y-%m-%dT%H:%M:%S"), i))
procs = [("L-1", "w120-R8", "a6456"), ("L-2", "w120-R1", "p1nop"), ("L-2", "w120-R1", "p2add"), ("L-3", "w120-R5", "thp"),
         ("L-4", "w120-R6", "st1"), ("L-4", "w120-R6", "st2"), ("L-4", "w120-R6", "st3"), ("R0", "w120-R0", "p1"),
         ("R0", "w120-R0", "p2"), ("R0b", "w120-R0b", "cA"), ("R0b", "w120-R0b", "cB"), ("R0b", "w120-R0b", "cC")]
rows, border, clean, n_all = [], [], [], 0
for row, pre, tag in procs:
    d = one(pre); day = re.search(r"(\d{8})T", os.path.basename(d))[1]
    for l in open(d + "/launches.txt"):
        p = l.split()
        if p[0] == "launch" and p[1] == tag: A = dt.datetime.strptime(day + p[3], "%Y%m%d%H:%M:%S")
        if p[0] == "rc" and p[2] == tag: B = dt.datetime.strptime(day + p[4], "%Y%m%d%H:%M:%S")
    iv = ivs(d + "/%s.csv" % tag)
    hits = [((t - A).total_seconds(), i) for t, i in recs if A <= t <= B]
    n_all += len(hits)
    if not hits: continue
    touch = {}
    for off, i in hits:
        t = [(("inside" if x["ts"] <= off - 1 and off + 1 <= x["te"] else "possible"), x) for x in iv
             if (x["ts"] <= off - 1 and off + 1 <= x["te"]) or (off - 1 < x["te"] and x["ts"] < off + 1)]
        touch[i] = (off, t)
    marked = {id(x) for off, t in touch.values() for _, x in t}
    oth = lambda x, iv=iv: next(y for y in iv if y["pos"] == x["pos"] and y["k"] == x["k"] and y["r"] != x["r"])
    own = {}
    for i, (off, t) in sorted(touch.items()):
        if len(t) == 1:
            own.setdefault(id(t[0][1]), (t[0][1], t[0][0], []))[2].append(i)
        else:
            border.append((row, tag, i, off, [x for _, x in t], oth))
    for x, kind, lines in own.values():
        rows.append(dict(row=row, tag=tag, x=x, where="inside" if kind == "inside" else "before or inside", lines=lines,
                         o=oth(x), o_marked=id(oth(x)) in marked, file=os.path.relpath(d, R) + "/%s.csv" % tag))
    for pos in sorted({x["pos"] for x in iv}):
        a, b = sorted((x for x in iv if x["pos"] == pos), key=lambda x: x["r"])
        if id(a) not in marked and id(b) not in marked: clean.append((row, tag, pos, a["k"], b["tot"] - a["tot"]))
chk(n_all == 18, "records in the 12 process windows: %d (sheet: 18)" % n_all)
tab = re.search(r"\| Row \| Process \| Interval with records .*?\n\|[-|]+\|\n((?:\|.*\n)+)", MD)
trs = [[c.strip() for c in l.strip().strip("|").split("|")] for l in tab[1].strip().split("\n")]
chk(len(trs) == len(rows) == 8, "table of intervals with records: %d rows in the sheet, %d computed" % (len(trs), len(rows)))
for t, r in zip(trs, rows):
    x, o = r["x"], r["o"]
    mine = [r["row"], r["tag"], "%s, round %d, position %d" % (x["k"], x["r"], x["pos"]), str(x["line"]),
            ", ".join(map(str, r["lines"])), r["where"], q(x["tot"]), "%s (%d)" % (q(o["tot"]), o["line"]), sg(x["tot"] - o["tot"]),
            "yes" if (x["k"], x["pos"]) in (("oldread", 0), ("asmread", 1)) else "no"]
    rf = t[10].split()
    ok = t[:10] == mine and not r["o_marked"] and refs[rf[0].strip("[]")] == "R/" + r["file"] and refs[rf[1].strip("[]")] == "R/dimm-check-20261117/h-5.txt"
    chk(ok, "table row %s %s %s: %s" % (r["row"], r["tag"], mine[2], " | ".join(mine[6:9])))
d8 = [r["x"]["tot"] - r["o"]["tot"] for r in rows]
low = sorted(d for d in d8 if d < -1); rest = [d for d in d8 if not d < -1]
n_more = sum(len(r["lines"]) for r in rows if (r["x"]["k"], r["x"]["pos"]) not in (("oldread", 0), ("asmread", 1)))
bl = sorted({b[2] for b in border})
bint = {id(x): (x, b[5]) for b in border for x in b[4]}
bd = [x["tot"] - o(x)["tot"] for x, o in bint.values()]
has("Of the 14 records outside the used intervals, %d fall inside the %d intervals of this table that the sheet does not use. The other %d lie at the border of two intervals."
    % (n_more, len(rows) - 2, len(bl)))
chk(n_all - 4 == 14 == n_more + len(bl), "14 = 18 records - 2 (L-1) - 2 (p2add asmread) = %d inside other intervals + %d at a border" % (n_more, len(bl)))
has("1 record of L-2 p1nop, 46 s after the launch line (journal line 7142), between read_nop128 and read_nop160 of round 0, and 2 records of L-2 p2add, 90 s after the launch line (journal lines 7288 and 7316), between read_iadd16 and read_sparse of round 1.")
chk([(b[0], b[1], b[2], b[3], [(x["k"], x["r"]) for x in b[4]]) for b in border] ==
    [("L-2", "p1nop", 7142, 46.0, [("read_nop128", 0), ("read_nop160", 0)]), ("L-2", "p2add", 7288, 90.0, [("read_iadd16", 1), ("read_sparse", 1)]),
     ("L-2", "p2add", 7316, 90.0, [("read_iadd16", 1), ("read_sparse", 1)])], "border records computed from the raw files: lines %s" % bl)
has("These %d intervals differ from their other round by %s to %s GB/s." % (len(bint), sg(min(bd)), sg(max(bd))))
has("What fits: %d of the %d intervals of the table are more than 1 GB/s below their other round (%s, %s and %s GB/s)."
    % (len(low), len(rows), q(-low[2]), q(-low[1]), q(-low[0])))
has("The largest difference belongs to the asmread interval of p2add (288.54 GB/s), the lowest asmread value of the pool L-1 to L-4. No interval of the table is more than 1 GB/s above its other round.")
chk(max(d8) < 1 and min(d8) == rows[3]["x"]["tot"] - rows[3]["o"]["tot"] and rows[3]["tag"] == "p2add" and q(rows[3]["x"]["tot"]) == "288.54",
    "no interval more than 1 GB/s above its other round; the lowest difference is asmread of p2add")
has("What does not fit: the other %d intervals differ from their other round by less than 1 GB/s (%s to %s GB/s)." % (len(rest), sg(min(rest)), sg(max(rest))))
chk(all(abs(d) < 1 for d in rest), "the other %d differences are below 1 GB/s" % len(rest))
has("One of them is oldread, round 0 of row L-1. It gave %s GB/s with records before or inside it. Round 1, without records, gave %s GB/s."
    % (q(rows[0]["x"]["tot"]), q(rows[0]["o"]["tot"])))
big = [c for c in clean if abs(c[4]) > 1]; mx = max(clean, key=lambda c: abs(c[4]))
has("These %d processes have %d positions at which neither round has a record inside it or at its border. At %d of them the two rounds differ by more than 1 GB/s. The largest difference is %s GB/s (%s of %s, lower in round 1, directly after the asmread interval with records)."
    % (len({(r["row"], r["tag"]) for r in rows}), len(clean), len(big), q(abs(mx[4])), mx[3], mx[1]))
chk(mx[:3] == ("L-2", "p2add", 2) and mx[4] < 0, "largest difference without records: %s %s position %d, round 1 minus round 0 = %+.2f" % (mx[0], mx[1], mx[2], mx[4]))
inn = [d for d in low if abs(d) < abs(mx[4])]
has("So %d of the %d lower intervals of the table (%s and %s GB/s) are within the differences seen without records, and 1 (%s GB/s) is above them."
    % (len(inn), len(low), q(-inn[1]), q(-inn[0]), q(-low[0])))
has("11. Insufficient data: whether a corrected hardware error record lowers the rate of an interval (hypothesis in section 4.1). The processes of rows L-1 to L-4, R0 and R0b hold %d intervals to which records can be assigned (all kernels and positions, view added after the numbers were seen). %d of them are more than 1 GB/s below the same kernel at the same position in the other round of their process (%s, %s and %s GB/s). The other %d differ from it by less than 1 GB/s (%s to %s GB/s). Without records the two rounds of the same processes differ by up to %s GB/s."
    % (len(rows), len(low), q(-low[2]), q(-low[1]), q(-low[0]), len(rest), sg(min(rest)), sg(max(rest)), q(abs(mx[4]))))

# ------------------------------------------------------------------ defect 2: per mesh
def old(prefix, f, pos=None):
    d = one(prefix)
    f = f or [n for n in os.listdir(d) if n.endswith(".csv")][0]
    return [x for x in ivs(d + "/" + f) if x["k"] == "oldread" and (pos is None or x["pos"] == pos)]
Lr = [x for t in ("T72L1", "T72L2", "T72L3") for x in old("w120-" + t, "a6456.csv", 0)]
Cr = [x for t in ("T72C1", "T72C2", "T72C3", "T72C4") for x in old("w120-" + t, None)]
Ir = [x for t in ("T72I1", "T72I2") for x in old("w120-" + t, "a6456.csv", 0)]
Fr = old("w120-w120-F72d12", "a6456.csv", 0)
B = [x for pre, f in (("w120-R8", "a6456.csv"), ("w120-R1", "p1nop.csv"), ("w120-R1", "p2add.csv"), ("w120-R5", "thp.csv"),
                      ("w120-R6", "st1.csv"), ("w120-R6", "st2.csv"), ("w120-R6", "st3.csv"), ("w120-R0", "p1.csv"),
                      ("w120-R0", "p2.csv"), ("w120-R0b", "cA.csv"), ("w120-R0b", "cB.csv"), ("w120-R0b", "cC.csv")) for x in old(pre, f, 0)]
rg = lambda L_, k: "%s to %s" % (q(min(x[k] for x in L_)), q(max(x[k] for x in L_)))
ADDED = "added after the first numbers were seen"
has("- oldread, all %d intervals at 7200 MT/s (F72d12, parts L and C, and control I, which was %s): mesh 1 gave %s GB/s and mesh 0 gave %s GB/s"
    % (len(Lr + Cr + Ir + Fr), ADDED, rg(Lr + Cr + Ir + Fr, "m1"), rg(Lr + Cr + Ir + Fr, "m0")))
has("the %d oldread intervals of part L, of control I (%s) and of F72d12, the earlier run of the same boot, gave %s GB/s on mesh 1 and %s GB/s on mesh 0."
    % (len(Lr + Ir + Fr), ADDED, rg(Lr + Ir + Fr, "m1"), rg(Lr + Ir + Fr, "m0")))
has("- The same without part C and without control I: the %d oldread intervals of part L and of F72d12 gave %s GB/s on mesh 1 and %s GB/s on mesh 0. Against the same 8000 MT/s rows mesh 1 is higher and mesh 0 is lower in every one of these intervals too. So the result does not rest on control I."
    % (len(Lr + Fr), rg(Lr + Fr, "m1"), rg(Lr + Fr, "m0")))
for name, L_ in (("all", Lr + Cr + Ir + Fr), ("without part C", Lr + Ir + Fr), ("without part C and control I", Lr + Fr)):
    chk(min(x["m1"] for x in L_) > max(x["m1"] for x in B) and max(x["m0"] for x in L_) < min(x["m0"] for x in B),
        "7200 MT/s %s: mesh 1 higher and mesh 0 lower than the %d intervals of bwx12 and bwx11 at 8000 MT/s (mesh 1 %s, mesh 0 %s)" % (name, len(B), rg(B, "m1"), rg(B, "m0")))
has("This holds with part C (%d intervals) and without part C (%d intervals of part L, of control I (%s) and of F72d12, the earlier run of the same boot). It also holds without part C and without control I (%d intervals of part L and of F72d12)."
    % (len(Lr + Cr + Ir + Fr), len(Lr + Ir + Fr), ADDED, len(Lr + Fr)))
f72 = one("w120-w120-F72d12"); t72 = one("w120-T72L1")
chk(re.search(r"(\d{8})T(\d{6})", os.path.basename(f72))[0] < re.search(r"(\d{8})T(\d{6})", os.path.basename(t72))[0],
    "F72d12 is the earlier run: folder %s before %s" % (os.path.basename(f72), os.path.basename(t72)))

# ------------------------------------------------------------------ defect 1: view by start state
pool = [("w120-R8", "a6456"), ("w120-R1", "p1nop"), ("w120-R1", "p2add"), ("w120-R5", "thp"), ("w120-R6", "st1"), ("w120-R6", "st2"), ("w120-R6", "st3")]
busy = []
for pre, tag in pool:
    d = one(pre)
    load = next(float(l.split()[5]) for l in open(d + "/launches.txt") if l.startswith("launch %s " % tag))
    if load >= 1.0: busy.append([x["tot"] for x in old(pre, tag + ".csv", 0)])
nb = sum(map(len, busy)); lo_b = min(v for b in busy for v in b); hi_b = max(v for b in busy for v in b)
has("- So in this view both 7200 MT/s parts that started after 120-thread work lie below the %d bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (%d intervals / %d processes against %d intervals / %d processes, no overlap). For part C this holds against these %d processes only (see the limit below)."
    % (len(busy), len(Lr + Cr), 7, nb, len(busy), len(busy)))
chk(max(x["tot"] for x in Lr + Cr) < lo_b, "highest oldread value of parts L and C (%s) below the lowest of the %d bwx12 processes (%s)" % (q(max(x["tot"] for x in Lr + Cr)), len(busy), q(lo_b)))
b11 = [x["tot"] for pre, f in (("w120-R0", "p2.csv"), ("w120-R0b", "cB.csv"), ("w120-R0b", "cC.csv")) for x in old(pre, f, 0)]
chk(min(b11) <= max(x["tot"] for x in Cr), "part C overlaps the bwx11 processes after 120-thread work (%s to %s GB/s; part C highest %s)" % (q(min(b11)), q(max(b11)), q(max(x["tot"] for x in Cr))))
has("In that view part C lies below the bwx12 processes of the pool that started after 120-thread work too. Against the other-binary processes with that kind of start state part C overlaps (limit in the view).")
has("all %d intervals of part C lie below the %d bwx12 processes of the pool L-1 to L-4 that started after 120-thread work (%s to %s GB/s), by %s GB/s at the nearest ends. Against the other-binary processes with that kind of start state part C overlaps (limit in that view)."
    % (len(Cr), len(busy), q(lo_b), q(hi_b), q(lo_b - max(x["tot"] for x in Cr))))
chk("the 8000 MT/s processes that started after 120-thread work" not in MD and "8000 MT/s group of its start state" not in MD
    and "the 8000 MT/s group that started after 120-thread work" not in MD, "the three phrases without the scope are gone from the sheet")

# ------------------------------------------------------------------ defect 4: section 7 entries against the uses
k5 = open(R + "/dimm-check-20261117/k-5.txt", errors="replace").read().splitlines()
chk("kernel: Memory: 395280872K/402090256K available" in k5[761], "k-5.txt line 762 holds the line Memory: ... available")
has("- [Ref140] `R/dimm-check-20261117/k-5.txt`: saved kernel log of the same boot: its last line and the line \"Memory: ... available\" (line 762)")
qj = open(R + "/uefisettings-20261117/questions.json").read()
chk(all('"name":"%s"' % n in qj for n in ("DIMM Frequency", "TXREQ Max", "TXREQ Min")), "questions.json holds the three settings")
has("- [Ref141] `R/uefisettings-20261117/questions.json`: firmware settings list (file time 2026-11-17 02:09 UTC): the entry counts and the settings \"DIMM Frequency\", \"TXREQ Max\" and \"TXREQ Min\"")
gp = open(R + "/dimm7200-20261117/gaps.txt").read().splitlines()
chk(gp[6].startswith("0 first=") and "hwerr=0" in gp[6] and " up " in gp[7] and gp[8].startswith("USER") and len(gp) == 12,
    "gaps.txt: row 0 in line 7 with hwerr=0, time line in line 8, process list to line 12")
has("- [Ref136] `R/dimm7200-20261117/gaps.txt`: first and last kernel log time of the boots of the 7200 MT/s reboot test (row 0 is the boot of the rerun), the field hwerr of row 0, and the time line and the process list after the rows (lines 8 to 12)")
print()
print("%d of %d items pass" % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)
