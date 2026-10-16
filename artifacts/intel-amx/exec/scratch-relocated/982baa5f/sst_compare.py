import json, re, os, glob, subprocess, datetime
from collections import Counter

V7 = "/tmp/platformd-sst-validation-20261007T183541Z"
V8 = "/tmp/platformd-sst-core-power-20261008"
DASH = "-"
SEP_CLOS3 = set()
for r in "0-6 15-23 72-78 87-95 144-150 159-167 216-222 231-239".split():
    a, b = map(int, r.split("-"))
    SEP_CLOS3 |= set(range(a, b + 1))

def parse_assoc_text(txt):
    i = txt.find("{")
    d = json.loads(txt[i:])
    m = {}
    def walk(o, cpu=None):
        if isinstance(o, dict):
            for k, v in o.items():
                mm = re.search(r"cpu-(\d+)$", k)
                if mm:
                    walk(v, int(mm.group(1)))
                elif k == "clos" and cpu is not None:
                    m[cpu] = int(v)
                else:
                    walk(v, cpu)
    walk(d)
    return m

def rng(s):
    s = sorted(s); out = []
    for c in s:
        if out and c == out[-1][1] + 1:
            out[-1][1] = c
        else:
            out.append([c, c])
    return " ".join(f"{a}-{b}" if a != b else f"{a}" for a, b in out) or DASH

def status_text(t):
    c = Counter(re.findall(r"\"(enable-status|priority-type)\": \"([a-z]+)\"", t))
    return {f"{k[0]}={k[1]}": n for k, n in sorted(c.items())}

def ts(path):
    return datetime.datetime.utcfromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")

def report(name, when, cp_text, assoc_text):
    print(f"- {name} (captured {when} UTC): core-power {status_text(cp_text)}")
    if assoc_text is None:
        print("    (no association capture)"); return
    m = parse_assoc_text(assoc_text)
    c3 = {k for k, v in m.items() if v == 3}
    print(f"    assoc n={len(m)} per-clos={dict(sorted(Counter(m.values()).items()))}")
    print(f"    clos3 == September policy: {c3 == SEP_CLOS3}  extra={rng(c3 - SEP_CLOS3)}  missing={rng(SEP_CLOS3 - c3)}")
    if c3 != SEP_CLOS3:
        print(f"    clos3 = {rng(c3)}")

print("== Oct 7 phases ==")
for d in sorted(glob.glob(V7 + "/*/")):
    name = os.path.basename(d.rstrip("/"))
    cp = d + "core-power-info.stderr"; a = d + "associations.stderr"
    if not os.path.exists(cp):
        print(f"- {name}: files={sorted(os.listdir(d))[:8]}"); continue
    report(name, ts(cp), open(cp).read(), open(a).read() if os.path.exists(a) else None)
for small in ("install-start.txt", "full-start.txt"):
    p = os.path.join(V7, small)
    if os.path.exists(p):
        print(f"  {small}: {open(p).read().strip()[:200]}")
print("== Oct 8 phases ==")
for name in ("before", "after"):
    d = os.path.join(V8, name) + "/"
    report("1008-" + name, ts(d + "core-power-info.stderr"), open(d + "core-power-info.stderr").read(), open(d + "associations.stderr").read())
print("== now ==")
cp = subprocess.run(["/usr/bin/intel-speed-select", "--format", "json", "--cpu", "0,24,48,72,96,120", "core-power", "info"], capture_output=True, text=True)
asc = subprocess.run(["/usr/bin/intel-speed-select", "--format", "json", "--cpu", "0-287", "core-power", "get-assoc"], capture_output=True, text=True)
report("now", datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"), cp.stdout + cp.stderr, asc.stdout + asc.stderr)
