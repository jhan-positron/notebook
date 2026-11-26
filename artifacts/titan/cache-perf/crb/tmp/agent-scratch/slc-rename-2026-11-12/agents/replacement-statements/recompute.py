#!/usr/bin/env python3
"""Recompute every derived number of section A3 from the raw csv lines. Read only."""
R = "/home/jhan/workspace/titan/cache-perf/crb/results/"
def line(path, n):
    with open(R + path) as f:
        for i, l in enumerate(f, 1):
            if i == n: return l.rstrip("\n")
def gb(path, n):
    l = line(path, n); return float(l.split(",")[6]), l
A = "followup-20261030T194205Z/asm.csv"; P = "followup-20261030T194205Z/pair.csv"; B = "20261030T193108Z/bandwidth.csv"
v = {}
for name, path, n in [
    ("pair read 1G cpus 0,1 (compiled)", P, 66), ("pair read 1G cpus 0,64 (compiled)", P, 72),
    ("main read 1G 1 thread (compiled)", B, 214), ("main read 1G 2 threads (compiled)", B, 228),
    ("main read 1G 4 threads (compiled)", B, 242),
    ("main write 1G 1 thread (compiled)", B, 218), ("main write 1G 2 threads (compiled)", B, 232), ("main write 1G 4 threads (compiled)", B, 246),
    ("asm read 1G 1 thread", A, 165), ("asm read 1G 2 threads", A, 180), ("asm read 1G 4 threads", A, 195),
    ("asm write 1G 1 thread", A, 169), ("asm write 1G 2 threads", A, 184), ("asm write 1G 4 threads", A, 199),
    ("asm read 8M 1 thread cpu0", A, 67), ("asm read 8M 2 threads cpus 0,1", A, 74), ("asm read 8M 4 threads cpus 0-3", A, 81),
    ("asm read 8M 8 threads cpus 0-7", A, 88), ("asm read 8M 14 threads cpus 0-13", A, 95),
    ("asm read 8M 1 thread even", A, 300), ("asm read 8M 2 threads cpus 0,2", A, 307), ("asm read 8M 4 threads even", A, 314),
    ("asm read 8M 8 threads even", A, 321), ("asm read 8M 14 threads even", A, 328),
    ("asm write 8M 1 thread", A, 102), ("asm write 8M 2 threads", A, 109), ("asm write 8M 4 threads", A, 116), ("asm write 8M 8 threads", A, 123),
    ("main read 8M 1 thread (compiled)", B, 118), ("main read 8M 2 threads (compiled)", B, 124),
    ("main write 8M 1 thread (compiled)", B, 154), ("main write 8M 2 threads (compiled)", B, 160),
    ("pair 0,1", P, 6), ("pair 0,2", P, 12), ("pair 0,3", P, 18), ("pair 1,2", P, 24), ("pair 2,3", P, 30),
    ("pair 0,64", P, 36), ("pair 0,119", P, 42), ("pair 4,5", P, 48), ("pair 4,6", P, 54), ("pair 0,1 1M", P, 60),
]:
    v[name], raw = gb(path, n)
    print(f"{name:42s} {v[name]:8.2f}   <- {path.split('/')[-1]}:{n}: {raw}")
print()
d = v["pair read 1G cpus 0,1 (compiled)"] - v["main read 1G 1 thread (compiled)"]
print(f"A3.1 second reader adds (pair.csv 66 - bandwidth.csv 214): {d:.3f}  = {100*d/v['main read 1G 1 thread (compiled)']:.1f} % of one core")
d2 = v["main read 1G 2 threads (compiled)"] - v["main read 1G 1 thread (compiled)"]
print(f"      same run (bandwidth.csv 228 - 214): {d2:.3f}")
d3 = v["asm read 1G 2 threads"] - v["asm read 1G 1 thread"]
print(f"      asm loop (asm.csv 180 - 165): {d3:.3f} = {100*d3/v['asm read 1G 1 thread']:.1f} % of one core")
print(f"      partner pair / 2x single: compiled {v['pair read 1G cpus 0,1 (compiled)']/(2*v['main read 1G 1 thread (compiled)']):.4f}; asm {v['asm read 1G 2 threads']/(2*v['asm read 1G 1 thread']):.4f}; cpus 0,64 {v['pair read 1G cpus 0,64 (compiled)']/(2*v['main read 1G 1 thread (compiled)']):.4f}")
print(f"      0,64 minus 0,1: {v['pair read 1G cpus 0,64 (compiled)']-v['pair read 1G cpus 0,1 (compiled)']:.2f} = {100*(v['pair read 1G cpus 0,64 (compiled)']/v['pair read 1G cpus 0,1 (compiled)']-1):.1f} %")
w = v["asm write 1G 2 threads"] - v["asm write 1G 1 thread"]
print(f"A3.1 second writer adds (asm.csv 184 - 169): {w:.3f} = {100*w/v['asm write 1G 1 thread']:.2f} %;  one/pair = {v['asm write 1G 1 thread']/v['asm write 1G 2 threads']:.4f}")
print(f"      compiled: second writer adds {v['main write 1G 2 threads (compiled)']-v['main write 1G 1 thread (compiled)']:.2f}")
print(f"      second pair adds (asm.csv 199 - 184): {v['asm write 1G 4 threads']-v['asm write 1G 2 threads']:.2f}; per pair with 2 pairs {v['asm write 1G 4 threads']/2:.2f}")
print(f"      reads: 4 threads on 2 pairs asm {v['asm read 1G 4 threads']:.2f} -> per pair {v['asm read 1G 4 threads']/2:.2f}; compiled {v['main read 1G 4 threads (compiled)']/2:.2f}")
print(f"      DRAM pair read as flits per mesh cycle if every line crosses the port (est.): compiled {v['pair read 1G cpus 0,1 (compiled)']/64:.3f}, asm {v['asm read 1G 2 threads']/64:.3f}")
part = [v["asm read 8M 2 threads cpus 0,1"], v["pair 0,1"], v["pair 2,3"], v["pair 4,5"], v["main read 8M 2 threads (compiled)"]]
non = {"0,2": v["pair 0,2"], "0,3": v["pair 0,3"], "1,2": v["pair 1,2"], "0,64": v["pair 0,64"], "0,119": v["pair 0,119"], "4,6": v["pair 4,6"], "asm 0,2": v["asm read 8M 2 threads cpus 0,2"]}
print(f"A3.2 partner best values: {sorted(part)}  non-partner best: {sorted(non.values())}")
print(f"      ratio min {min(non.values())/max(part):.4f} max {max(non.values())/min(part):.4f}")
print(f"      compiled only: min {v['pair 0,3']/v['pair 4,5']:.4f} max {v['pair 0,64']/v['pair 2,3']:.4f}; asm: {v['asm read 8M 2 threads cpus 0,2']/v['asm read 8M 2 threads cpus 0,1']:.4f}")
for t, a, b in [(2, "asm read 8M 2 threads cpus 0,1", "asm read 8M 2 threads cpus 0,2"), (4, "asm read 8M 4 threads cpus 0-3", "asm read 8M 4 threads even"),
                (8, "asm read 8M 8 threads cpus 0-7", "asm read 8M 8 threads even"), (14, "asm read 8M 14 threads cpus 0-13", "asm read 8M 14 threads even")]:
    print(f"      asm, {t:2d} threads: packed {v[a]:.2f}, one per pair {v[b]:.2f}, ratio {v[b]/v[a]:.3f}")
print(f"      78/2.8 = {78/2.8:.2f} B per core cycle; 77.51*0.8265={77.51*0.8265:.2f}, 78.45*0.8265={78.45*0.8265:.2f}")
print(f"A3.3 0.98: 3553584520/1.8094 = {3553584520/1.8094:.4e} per s; /2e9 = {3553584520/1.8094/2e9:.4f}")
print(f"      8M one writer bus writes per mesh cycle: {3020573021/1.8000/2e9:.4f}; with partner CPU 2: {1782823128/1.8000/2e9:.4f}")
print(f"      8M: pair/one loops: {v['asm write 8M 2 threads']/v['asm write 8M 1 thread']:.3f} (2026-10-30); part 5: {81.41/71.34:.3f} to {82.05/70.37:.3f}")
print(f"      per core: 2 ports {121.27/2:.2f}-{122.06/2:.2f}; 4 ports {228.21/4:.2f}-{229.83/4:.2f}; 8 writers 4 pairs {v['asm write 8M 8 threads']:.2f}")
