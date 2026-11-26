#!/usr/bin/env python3
"""verify_raw.py - own recomputation of the numbers behind the findings, from the raw csv files only (read only).
bwx rate of an interval = sum over its 120 thread rows of bytes / elapsed_s, in GB/s (GB = 1e9 bytes).
Part A rate = column aggregate_GBps of the csv."""
import glob, re, statistics
R = "/home/jhan/workspace/titan/cache-perf/crb/results"

def bwx(path):
    """-> list of dicts (round, pos, kernel, rate, before) for one bwx csv with ONE process; several processes: list per '-- step' header."""
    procs, cur, iv = [], None, None
    for ln, l in enumerate(open(path), 1):
        if l.startswith("-- ") or (l.startswith("# bwx:") and cur is None):
            if l.startswith("-- "):
                cur = dict(head=l.strip(), iv=[]); procs.append(cur)
            elif cur is None:
                cur = dict(head="(one process)", iv=[]); procs.append(cur)
        if l.startswith("# bwx:") and cur is not None:
            cur["seq"] = re.search(r"seq=(\S+)", l).group(1)
        if l.startswith("I,"):
            p = l.split(",")
            iv = dict(round=int(p[1]), pos=int(p[2]), kernel=p[3], line=ln, s=0.0, n=0)
            cur["iv"].append(iv)
        elif l.startswith("T,"):
            p = l.split(",")
            iv["s"] += float(p[6]) / float(p[7]) / 1e9; iv["n"] += 1
    for pr in procs:
        for i, x in enumerate(pr["iv"]):
            assert x["n"] == 120, (path, x)
            x["rate"] = x["s"]
            x["before"] = pr["iv"][i - 1]["kernel"] if i else None
    return procs

def k120(path, a1=False):
    """Part A csv -> list of (binary, kernel, round, [rates])"""
    out, cur = [], None
    for l in open(path):
        if l.startswith("-- "):
            if a1:
                m = re.search(r"tag (\S+)-r([12]) binary (\S+) .*--kernel (\S+)", l)
                cur = (m.group(3), m.group(4), int(m.group(2)), []) if m else None
                if "tag onebuf-ms500" in l:
                    m = re.search(r"binary (\S+) .*--kernel (\S+)", l); cur = (m.group(1), m.group(2), 0, [])
                elif not m:
                    cur = None
            else:
                m = re.search(r"binary (\S+) kernel (\S+) .* round (\d)", l)
                cur = (m.group(1), m.group(2), int(m.group(3)), [])
            if cur: out.append(cur)
        elif cur and re.match(r"^\w+,120,\d+,[0-9]+,", l):
            cur[3].append(float(l.split(",")[6]))
    return out

def rg(v): return f"{min(v):.2f} to {max(v):.2f} (n {len(v)}, median {statistics.median(v):.3f})"
one = lambda pat: (lambda g: g[0] if len(g) == 1 else (_ for _ in ()).throw(SystemExit(f"{pat}: {g}")))(glob.glob(R + "/" + pat))

# ---------------- 8000 MT/s pool L-1 to L-4 (bwx12): oldread at position 0, asmread at position 1
pool_files = [one("w120-R8-20261117T020549Z/a6456.csv")] + [one(f"w120-R1-20261115T185140Z/{x}.csv") for x in ("p1nop", "p2add")] + [one("w120-R5-20261115T203152Z/thp.csv")] + [one(f"w120-R6-20261115T203438Z/{x}.csv") for x in ("st1", "st2", "st3")]
pool_old, pool_asm = [], []
for f in pool_files:
    for pr in bwx(f):
        pool_old += [x["rate"] for x in pr["iv"] if x["kernel"] == "oldread" and x["pos"] == 0]
        pool_asm += [x["rate"] for x in pr["iv"] if x["kernel"] == "asmread" and x["pos"] == 1]
print("pool L-1..L-4 oldread pos 0:", rg(pool_old), "| processes", len(pool_files))
print("pool L-1..L-4 asmread pos 1:", rg(pool_asm))

def line_l(pats):
    o, a, d = [], [], []
    for p in pats:
        for pr in bwx(one(p)):
            by = {(x["round"], x["kernel"]): x["rate"] for x in pr["iv"]}
            o += [x["rate"] for x in pr["iv"] if x["kernel"] == "oldread"]; a += [x["rate"] for x in pr["iv"] if x["kernel"] == "asmread"]
            d += [(1 - by[(r, "asmread")] / by[(r, "oldread")]) * 100 for r in (0, 1)]
    return o, a, d
L_old, L_asm, L_d = line_l([f"w120-T72L{i}-*/a6456.csv" for i in (1, 2, 3)])
I_old, I_asm, I_d = line_l([f"w120-T72I{i}-*/a6456.csv" for i in (1, 2)])
F_old, F_asm, F_d = line_l(["w120-w120-F72d12-20261117T200231Z/a6456.csv"])
for nm, o, a in (("part L", L_old, L_asm), ("control I", I_old, I_asm), ("F72d12", F_old, F_asm)):
    print(f"{nm}: oldread {rg(o)} | asmread {rg(a)}")
    print(f"   oldread overlaps pool: {not (max(o) < min(pool_old) or min(o) > max(pool_old))}; asmread overlaps pool: {not (max(a) < min(pool_asm) or min(a) > max(pool_asm))}; asmread above pool by {min(a) - max(pool_asm):+.2f} (nearest ends)")
near = min(pool_old) - max(L_old); med = statistics.median(pool_old) - statistics.median(L_old); far = max(pool_old) - min(L_old)
print(f"part L oldread below pool: nearest ends {near:.3f} GB/s = {near / min(pool_old) * 100:.3f} % of {min(pool_old):.2f}; medians {med:.3f} GB/s = {med / statistics.median(pool_old) * 100:.3f} % of {statistics.median(pool_old):.2f}; farthest ends {far:.3f} GB/s = {far / min(pool_old) * 100:.3f} %")
print(f"F72d12 asmread below part L, nearest ends: {min(L_asm) - max(F_asm):.2f} GB/s")

# ---------------- part C
C = {}
for i in (1, 2, 3, 4):
    f = glob.glob(R + f"/w120-T72C{i}-*/c*.csv"); assert len(f) == 1
    pr = bwx(f[0]); assert len(pr) == 1
    C[i] = (f[0].split("/")[-1], pr[0])
    print(f"T72C{i}: {f[0].split('/')[-1]} seq={pr[0]['seq']}")
c_ao, c_aa, c_old, c_asm_ao, c_read_ao, c_read_aa = [], [], [], [], [], []
for i, (fn, pr) in C.items():
    by = {(x["round"], x["kernel"]): x for x in pr["iv"]}
    for r in (0, 1):
        rd, od = by[(r, "read")], by[(r, "oldread")]
        d = (1 - rd["rate"] / od["rate"]) * 100
        (c_ao if rd["before"] == "oldread" else c_aa).append(d)
        (c_read_ao if rd["before"] == "oldread" else c_read_aa).append(rd["rate"])
        c_old.append(od["rate"])
        if by[(r, "asmread")]["before"] == "oldread": c_asm_ao.append(by[(r, "asmread")]["rate"])
print(f"part C drops, read after oldread: {min(c_ao):.2f} to {max(c_ao):.2f} % (n {len(c_ao)}); read after asmread: {min(c_aa):.2f} to {max(c_aa):.2f} % (n {len(c_aa)}); all: {min(c_ao + c_aa):.2f} to {max(c_ao + c_aa):.2f} % (n {len(c_ao + c_aa)})")
print("part C oldread:", rg(c_old), "overlaps pool:", not (max(c_old) < min(pool_old) or min(c_old) > max(pool_old)))
print("part C asmread directly after oldread:", rg(c_asm_ao), f"above pool by {min(c_asm_ao) - max(pool_asm):+.2f}")
print("part C read after oldread:", rg(c_read_ao), "| after asmread:", rg(c_read_aa))

# ---------------- part A
def pa(rows, binary, kernel, rnd=None): return [v for b, k, r, vs in rows for v in vs if b == binary and k == kernel and (rnd is None or r == rnd)]
A1 = k120(R + "/kernels-20261113T181222Z/threads120.csv")
A2 = k120(R + "/partA-20261113T205055Z/A1.csv", a1=True)
A3 = [x for x in k120(R + "/partA-20261113T205055Z/A3.csv", a1=True) if x[2] == 0]
T = {s: k120(one(f"k120-T72A{s}-*/threads120.csv")) for s in (1, 2, 3)}
o8 = pa(A1, "bw_old", "read") + pa(A2, "bw_old", "read"); o8p = o8 + pa(A3, "bw_old", "read")
print("A-1 old read:", rg(pa(A1, "bw_old", "read")), "| A-2 old read:", rg(pa(A2, "bw_old", "read")), "| A-1 and A-2:", rg(o8), "| processes:", sum(1 for x in A1 + A2 if x[0] == "bw_old" and x[1] == "read"))
print("pool A-1..A-3 old read:", rg(o8p))
o7 = [v for s in (1, 2, 3) for v in pa(T[s], "bw_old", "read")]
print("part A old read 7200:", rg(o7), "overlaps:", not (max(o7) < min(o8p) or min(o7) > max(o8p)))
for rnd in (1, 2):
    n7 = pa(T[1], "bw_new", "read", rnd); n8 = pa(A1, "bw_new", "read", rnd) + pa(A2, "bw_new", "read", rnd)
    print(f"part A session 1 round {rnd}, bw_new read: {rg(n7)} against A-1 and A-2 round {rnd}: {rg(n8)}; above by {min(n7) - max(n8):+.2f}")

# ---------------- runner bwx, tags common-6000-*: kernel sequence
seqs, nproc = {}, 0
for f in [R + "/B7-20261113T232859Z/B7.csv", R + "/B7-20261114T024352Z/B7.csv"] + glob.glob(R + "/C3-20261114T022708Z/*.csv") + glob.glob(R + "/C3-20261114T054116Z/*.csv"):
    take = False
    for l in open(f):
        if l.startswith("-- "):
            take = "tag common-6000-" in l
        elif take and l.startswith("# bwx:"):
            m = re.search(r"seq=(\S+) rounds=(\d+)", l); seqs[(m.group(1), m.group(2))] = seqs.get((m.group(1), m.group(2)), 0) + 1; nproc += 1; take = False
print("runner bwx, tags common-6000-*: processes", nproc, "sequences (seq, rounds):", seqs)
