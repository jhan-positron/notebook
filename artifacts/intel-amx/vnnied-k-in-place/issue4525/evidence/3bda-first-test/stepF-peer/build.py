#!/usr/bin/env python3
"""Compile one harness with the exact flags of t/t_llama_unit.cpp from a tree's
gen/compile_commands.json. Usage: build.py <tree> <harness.cpp> <out.o>
Writes <out.o>.cmd.txt (the command actually run) and <out.o>.build.log."""
import json, os, shlex, subprocess, sys
tree, src, out = sys.argv[1:4]
cc = json.load(open(os.path.join(tree, "gen/compile_commands.json")))
entry = [e for e in cc if e["file"].endswith("/t/t_llama_unit.cpp")]
assert len(entry) == 1, entry
args = shlex.split(entry[0]["command"])
new = []
skip = 0
for i, a in enumerate(args):
    if skip: skip -= 1; continue
    if a in ("-o", "-c"): skip = 1; continue          # replace source / object
    if a in ("-MD", "-MT", "-MF"): skip = 1 if a != "-MD" else 0; continue
    if a == "-fcolor-diagnostics": continue           # plain text log
    new.append(a)
new += ["-I", os.path.dirname(os.path.abspath(src)), "-o", out, "-c", src]
cmd = " ".join(shlex.quote(a) for a in new)
open(out + ".cmd.txt", "w").write("# cwd: %s\n%s\n" % (entry[0]["directory"], cmd))
nix = os.path.expanduser("~/.nix-profile/bin/nix")
inner = "cd %s && %s" % (shlex.quote(entry[0]["directory"]), cmd)
full = ["taskset", "-c", "72-143", "nice", "-n", "10", nix, "develop", "--accept-flake-config",
        "--command", "bash", "--norc", "--noprofile", "-c", inner]
r = subprocess.run(full, cwd=tree, capture_output=True, text=True)
open(out + ".build.log", "w").write(r.stdout + r.stderr)
print("rc=%d out=%s exists=%s" % (r.returncode, out, os.path.exists(out)))
sys.exit(r.returncode)
