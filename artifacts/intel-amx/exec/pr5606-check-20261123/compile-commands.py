#!/usr/bin/env python3
"""pr5606-check-20261123: which compile commands of a build tree carry -DTRON_AMX_DISPATCH.

Reads <tree>/gen/compile_commands.json (CMake writes one entry per compiled source file). Prints:
  - how often the define appears in the command of t/t_amx_dispatch_dtype.cpp,
  - how many commands of the library tron (objects under src/tron/CMakeFiles/tron.dir/) carry it,
  - every other target that carries it, with the count of its commands,
  - whether src/tron/kernels/amx_attn.cpp (the AMX kernel file) has a compile command.
Usage: compile-commands.py <tree>
"""
import collections
import json
import re
import shlex
import sys

tree = sys.argv[1]
DEF = "-DTRON_AMX_DISPATCH"
entries = json.load(open(f"{tree}/gen/compile_commands.json"))


def args_of(e):
    return e["arguments"] if "arguments" in e else shlex.split(e["command"])


def output_of(e, args):
    if "output" in e:
        return e["output"]
    return args[args.index("-o") + 1] if "-o" in args else "?"


def target_of(out):
    m = re.search(r"CMakeFiles/([^/]+)\.dir/", out)
    return m.group(1) if m else "?"


rows = []
for e in entries:
    a = args_of(e)
    out = output_of(e, a)
    # the define exactly, not a longer name that starts with it
    n = sum(1 for x in a if x == DEF or x.startswith(DEF + "="))
    rows.append((e["file"], out, target_of(out), n))

print(f"compile commands in gen/compile_commands.json: {len(rows)}")
test = [r for r in rows if r[0].endswith("/t/t_amx_dispatch_dtype.cpp")]
print(f"commands for t/t_amx_dispatch_dtype.cpp: {len(test)}")
for f, out, tgt, n in test:
    print(f"  target {tgt}, object {out}: {DEF} appears {n} time(s)")
lib = [r for r in rows if "src/tron/CMakeFiles/tron.dir/" in r[1]]
print(f"commands of the library tron (objects under src/tron/CMakeFiles/tron.dir/): {len(lib)}; "
      f"with {DEF}: {sum(1 for r in lib if r[3])}")
with_def = collections.Counter(r[2] for r in rows if r[3])
print(f"commands with {DEF} in the whole build: {sum(with_def.values())}, in {len(with_def)} target(s)")
for tgt, c in sorted(with_def.items(), key=lambda kv: (-kv[1], kv[0]))[:40]:
    print(f"  {tgt}: {c}")
if len(with_def) > 40:
    print(f"  ... and {len(with_def) - 40} more targets")
kern = [r for r in rows if r[0].endswith("/src/tron/kernels/amx_attn.cpp")]
print(f"commands for src/tron/kernels/amx_attn.cpp: {len(kern)}")
for f, out, tgt, n in kern:
    print(f"  target {tgt}, object {out}")
# every other object on the link line of the test also matters: the test-support object libraries
for name in ("testfake_objects", "testlog_objects"):
    sub = [r for r in rows if r[2] == name]
    print(f"commands of the object library {name}: {len(sub)}; with {DEF}: {sum(1 for r in sub if r[3])}")
