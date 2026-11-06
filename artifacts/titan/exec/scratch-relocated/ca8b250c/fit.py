import sys, re
path = sys.argv[1]
passes = None; tb = None
best = {}
for line in open(path):
    line = line.strip()
    if line.startswith('# bandwidth'):
        passes = int(re.search(r'passes=(\d+)', line).group(1))
        bpt = int(re.search(r'bytes_per_thread=(\d+)', line).group(1))
        continue
    if line.startswith('#') or line.startswith('mem,') or not line:
        continue
    f = line.split(',')
    if f[4] == 'best':
        size = int(f[3]); gbps = float(f[7])
        best[size] = (gbps, passes, bpt)
    elif f[4].isdigit():
        tb = int(f[5])
        assert tb == int(f[3]) * passes, (tb, f[3], passes)
xs = []; ys = []
for size in sorted(best):
    gbps, p, bpt = best[size]
    total = size * p
    t = total / (gbps * 1e9) / p
    xs.append(size); ys.append(t * 1e9)
    print(f"{size:6d} B passes={p:5d} best={gbps:.3f} GB/s  t_pass={t*1e9:.3f} ns")
n = len(xs); mx = sum(xs)/n; my = sum(ys)/n
b = sum((x-mx)*(y-my) for x, y in zip(xs, ys)) / sum((x-mx)**2 for x in xs)
a = my - b*mx
print(f"intercept a = {a:.3f} ns, slope = {1/b:.1f} GB/s (1/b with x in B, y in ns -> {1/b:.4f} B/ns = GB/s)")
for x, y in zip(xs, ys):
    r = a + b*x
    print(f"  {x:6d}: fit {r:.3f} ns, meas {y:.3f}, resid {100*(y-r)/ys[0]:.2f} % of smallest pass time")
