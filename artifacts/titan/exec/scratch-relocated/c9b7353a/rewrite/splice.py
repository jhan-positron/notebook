#!/usr/bin/env python3
"""splice.py - put rewritten methods of class Report into a copy of report_final.py.
  splice.py --trial FRAG        splice one fragment into the BASE generator, write trial/<name>/report_final.py,
                                run it to trial/<name>/out.html, then run fidelity.py against the base page
  splice.py --apply OUT FRAG... splice all fragments into the BASE generator and write OUT
A fragment holds complete methods of class Report at 4-space indentation, with unchanged names."""
import ast, os, subprocess, sys
S = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.join(S, "base", "report_final.py")
A = "/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/tackle-8mb-analysis"

def methods(src, wrap):
    tree = ast.parse(("class Report:\n" + src) if wrap else src)
    cls = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Report"][0]
    off = 1 if wrap else 0
    out = {}
    for n in cls.body:
        if isinstance(n, ast.FunctionDef):
            first = min([n.lineno] + [d.lineno for d in n.decorator_list])
            out[n.name] = (first - off, n.end_lineno - off, ast.unparse(n.args))
        elif wrap:
            sys.exit("fragment holds a statement that is not a method, line %d" % (n.lineno - off))
    return out

def splice(frags):
    base = open(BASE).read().split("\n")
    bm = methods("\n".join(base), False)
    repl, seen = [], {}
    for fp in frags:
        ftxt = open(fp).read().rstrip("\n")
        if "\t" in ftxt:
            sys.exit("%s holds a tab character" % fp)
        fl = ftxt.split("\n")
        for name, (a, b, args) in methods(ftxt, True).items():
            if name not in bm:
                sys.exit("%s: method %s does not exist in class Report" % (fp, name))
            if name in seen:
                sys.exit("method %s is in %s and in %s" % (name, seen[name], fp))
            if args != bm[name][2]:
                sys.exit("%s: signature of %s changed" % (fp, name))
            seen[name] = fp
            repl.append((bm[name][0], bm[name][1], fl[a - 1:b]))
    for a, b, new in sorted(repl, reverse=True):
        base[a - 1:b] = new
    out = "\n".join(base)
    ast.parse(out)
    return out, sorted(seen)

if sys.argv[1] == "--trial":
    fp = sys.argv[2]
    name = os.path.splitext(os.path.basename(fp))[0]
    d = os.path.join(S, "trial", name)
    os.makedirs(d, exist_ok=True)
    out, names = splice([fp])
    open(os.path.join(d, "report_final.py"), "w").write(out)
    print("spliced methods:", ", ".join(names))
    r = subprocess.run([sys.executable, os.path.join(d, "report_final.py"), "--json", os.path.join(A, "final8.json"),
                        "-o", os.path.join(d, "out.html")], capture_output=True, text=True)
    print(r.stdout[-1500:], r.stderr[-3000:])
    if r.returncode:
        sys.exit("generator failed")
    subprocess.run([sys.executable, os.path.join(S, "fidelity.py"), os.path.join(S, "base", "tackle-8mb-report.html"),
                    os.path.join(d, "out.html")])
elif sys.argv[1] == "--apply":
    out, names = splice(sys.argv[3:])
    open(sys.argv[2], "w").write(out)
    print("wrote %s, spliced methods: %s" % (sys.argv[2], ", ".join(names)))
