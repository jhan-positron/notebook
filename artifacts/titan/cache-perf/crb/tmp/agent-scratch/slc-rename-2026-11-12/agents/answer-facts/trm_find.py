import fitz, sys, re
p = sys.argv[1]; pat = re.compile(sys.argv[2]); maxhits = int(sys.argv[3]) if len(sys.argv) > 3 else 12
lo = int(sys.argv[4]) if len(sys.argv) > 4 else 1; hi = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9
d = fitz.open(p); hits = 0
for i, pg in enumerate(d, 1):
    if i < lo or i > hi: continue
    t = pg.get_text()
    for m in pat.finditer(t):
        print(f'p{i}:', repr(t[max(0, m.start()-220): m.end()+280]))
        hits += 1
        if hits >= maxhits: sys.exit()
