#!/usr/bin/env python3
"""Generate the page from a COPY of the generator scripts. Nothing under /home/jhan/workspace is written.
Use: PYTHONDONTWRITEBYTECODE=1 python3 regen_from.py <folder with the copied *.py files> <output folder>
Writes <output folder>/page.html and <output folder>/predictions.json. Exit code 1 with a traceback if the generator fails."""
import contextlib, io, os, sys
GEN, OUT = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, GEN)


def run(script, swaps):
    src = open(f"{GEN}/{script}").read()
    for old, new in swaps:
        assert src.count(old) == 1, (script, old)
        src = src.replace(old, new)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sys.argv = [script]
        exec(compile(src, f"{GEN}/{script}", "exec"), {"__name__": "__main__"})


run("predict.py", [('open(RES + "/predictions.json", "w")', "open(%r, \"w\")" % (OUT + "/predictions.json"))])
run("gen_design.py", [('OUT = "/home/jhan/workspace/intel-AMX/GDN/gdn-amx-design.html"', "OUT = %r" % (OUT + "/page.html")),
                      ('pred = json.load(open(RES + "/predictions.json"))', "pred = json.load(open(%r))" % (OUT + "/predictions.json"))])
print("wrote", OUT + "/page.html", os.path.getsize(OUT + "/page.html"), "bytes")
