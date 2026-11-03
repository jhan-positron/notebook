import os, re, sys
d, arms, n_want = sys.argv[1], sys.argv[2].split(), int(sys.argv[4])
rows = {}
for a in arms:
    p = os.path.join(d, a + ".tokens")
    if os.path.exists(p):
        lines = [l for l in open(p, errors="replace").read().splitlines() if l.strip()]
        if lines: rows[a] = [int(x) for x in re.findall(r"-?\d+", lines[0])]
print("smoke token rows:", {a: len(r) for a, r in rows.items()})
pairs = [("head", "head2"), ("head", "base"), ("headoff", "base"), ("headoff", "head")]
MUST_MATCH = {tuple(p.split(":")) for p in sys.argv[3].split() if ":" in p}
print("must-match pairs:", sorted(MUST_MATCH))
verdict = "ok"
wanted = [p for p in pairs if p[0] in arms and p[1] in arms]
for a in arms:   # every asked arm must have a full row (the pair check below only looks at the common prefix)
    if a not in rows: print(f"{a}: no token row"); verdict = "incomplete"
    elif len(rows[a]) != n_want: print(f"{a}: {len(rows[a])} tokens, expected {n_want}"); verdict = "incomplete"
for a, b in wanted:
    if a not in rows or b not in rows:
        print(f"{a} vs {b}: missing"); verdict = "incomplete" if verdict == "ok" else verdict; continue
    ra, rb = rows[a], rows[b]; n = min(len(ra), len(rb))
    first = next((i for i in range(n) if ra[i] != rb[i]), None)
    tag = "must match" if (a, b) in MUST_MATCH else "informational"
    if first is None: print(f"{a} vs {b}: identical for {n} tokens (lengths {len(ra)} / {len(rb)}) [{tag}]")
    else:
        ndiff = sum(1 for i in range(n) if ra[i] != rb[i])
        print(f"{a} vs {b}: first difference at generated token {first} of {n} ({ra[first]} vs {rb[first]}); agreeing prefix {first} tokens; {ndiff} of {n} positions differ [{tag}]")
        if (a, b) in MUST_MATCH and verdict == "ok": verdict = "differs"
print("SMOKE-VERDICT", verdict if (wanted and len(rows) >= 2) else "incomplete")
