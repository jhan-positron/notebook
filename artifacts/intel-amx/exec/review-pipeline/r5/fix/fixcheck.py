#!/usr/bin/env python3
"""Run a recorded -fsyntax-only command; on "fatal error: 'X' file not found", locate X under /nix/store and retry with -isystem."""
import subprocess, sys, re, os, glob
cmdfile, log = sys.argv[1], sys.argv[2]
S = os.path.dirname(os.path.abspath(cmdfile))
extra_file = os.path.join(S, "extra_isystem.txt")
extra = open(extra_file).read().split() if os.path.exists(extra_file) else []
base = open(cmdfile).read().strip()
for attempt in range(12):
    cmd = base + " -fno-color-diagnostics " + " ".join(f"-isystem {d}" for d in extra)
    r = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)
    out = re.sub(r"\x1b\[[0-9;]*m", "", r.stdout + r.stderr)
    open(log, "w").write(out)
    m = re.search(r"fatal error: '([^']+)' file not found", out)
    if r.returncode == 0 or not m:
        print(f"attempt {attempt}: rc={r.returncode}; extra -isystem: {extra}")
        sys.exit(r.returncode)
    hdr = m.group(1)
    hits = subprocess.run(["bash", "-c", f"find /nix/store -maxdepth 6 -path '*/include/{hdr}' 2>/dev/null | head -3"], capture_output=True, text=True).stdout.split()
    if not hits:
        print(f"attempt {attempt}: missing header {hdr}: not found in /nix/store"); sys.exit(2)
    inc = hits[0][: hits[0].index("/include/") + len("/include")]
    print(f"attempt {attempt}: {hdr} -> {inc}")
    extra.append(inc)
    open(extra_file, "w").write("\n".join(extra))
