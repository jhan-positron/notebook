#!/usr/bin/env python3
"""Reproducibility check of GDN/gdn-amx-design.html. Read-only for the project: every output goes to argv[1].

Runs predict.py and gen_design.py from exec/gdn-20261120/ with their output paths redirected to the folder argv[1],
then compares the two results with the saved predictions.json and with the page. Exit code 0 = both byte-identical.
Use: PYTHONDONTWRITEBYTECODE=1 python3 regen_check.py /some/scratch/folder
"""
import contextlib
import hashlib
import io
import sys

D = "/home/jhan/workspace/intel-AMX/exec/gdn-20261120"
RES = "/home/jhan/workspace/intel-AMX/exec/results/gdn-20261120"
PAGE = "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html"
HERE = sys.argv[1]
sys.path.insert(0, D)
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()


def run(script, swaps):
    src = open(f"{D}/{script}").read()
    for old, new in swaps:
        assert src.count(old) == 1, (script, old)
        src = src.replace(old, new)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sys.argv = [script]
        exec(compile(src, script, "exec"), {"__name__": "__main__"})
    return buf.getvalue()


pred_out, page_out = HERE + "/predictions.regen.json", HERE + "/gdn-amx-design.regen.html"
open(HERE + "/predict.stdout.txt", "w").write(run("predict.py", [('open(RES + "/predictions.json", "w")', "open(%r, \"w\")" % pred_out)]))
run("gen_design.py", [('OUT = "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html"', "OUT = %r" % page_out),
                      ('pred = json.load(open(RES + "/predictions.json"))', "pred = json.load(open(%r))" % pred_out)])
ok = True
for name, saved, regen in (("predictions.json", RES + "/predictions.json", pred_out), ("gdn-amx-design.html", PAGE, page_out)):
    a, b = sha(saved), sha(regen)
    ok = ok and a == b
    print(f"{name}: saved {a}\n{' ' * len(name)}  regen {b}  {'IDENTICAL' if a == b else 'DIFFERENT'}")
sys.exit(0 if ok else 1)
