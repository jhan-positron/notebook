import sys
def expand(spec):
    s=set()
    for tok in spec.split(","):
        if "-" in tok: a,b=tok.split("-"); s.update(range(int(a),int(b)+1))
        else: s.add(int(tok))
    return s
ROLES = {
 "workers":  expand("7-14,24-71,79-86,96-143,151-158,168-215,223-230,240-287"),
 "rinzler":  expand("1,2,73,74,145,146,217,218"),
 "dev":      expand("3-6,75-78,147-150,219-222"),
 "platform": expand("0,72,144,216"),
 "spare":    expand("15-23,87-95,159-167,231-239"),
}
path, togglecpu = sys.argv[1], int(sys.argv[2])
frames=[]; cur=None
for line in open(path):
    p=line.split()
    if len(p)<5: continue
    if p[0]=="-":
        if cur: frames.append(cur)
        cur={}
        continue
    if cur is None or not p[2].isdigit(): continue
    try: cur[int(p[2])]=(float(p[3]), float(p[4]))
    except ValueError: pass
if cur: frames.append(cur)
res={}
for f in frames:
    if len(f)<280: continue
    wb=[f[c][0] for c in ROLES["workers"] if c in f]
    if sum(wb)/len(wb) < 20: continue
    tf=f.get(togglecpu,(0,0))[1]
    arm = "SLOW-2700" if tf<3200 else "FAST-4000"
    for role,cs in ROLES.items():
        xs=[f[c] for c in cs if c in f]
        b=sum(x[0] for x in xs)/len(xs); m=sum(x[1] for x in xs)/len(xs)
        res.setdefault((arm,role),[]).append((b,m))
print(f"{'arm':10s} {'role':9s} {'frames':>6s} {'Busy%':>7s} {'Bzy_MHz':>8s}")
for (arm,role),v in sorted(res.items()):
    print(f"{arm:10s} {role:9s} {len(v):6d} {sum(x[0] for x in v)/len(v):7.1f} {sum(x[1] for x in v)/len(v):8.0f}")
