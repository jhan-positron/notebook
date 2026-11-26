#!/bin/bash
# compat.sh - checks that make_report.py (not edited by this correction) still accepts the rebuilt FACTS.md and facts.json.
# It runs a copy of make_report.py whose output path points into this folder, compares the page with the existing
# report page byte by byte, and removes the copy and the page again. The real report page is not written.
set -u
S=/home/jhan/workspace/titan/cache-perf/crb/tmp/agent-scratch/w120-7200-2026-11-17
V=$S/verify-vfix-r3
REAL=/home/jhan/workspace/titan/cache-perf/crb/new-test-kernel/whole-chip-rerun-7200.html
before=$(sha256sum "$REAL" | cut -d' ' -f1)
python3 - <<PY
S = "$S"
src = open(S + "/make_report.py").read()
old = 'OUT = "$REAL"'
assert src.count(old) == 1
open(S + "/verify-vfix-r3/compat_make_report.py", "w").write(src.replace(old, 'OUT = "%s/verify-vfix-r3/compat-out.html"' % S))
PY
python3 -B "$V/compat_make_report.py" > "$V/compat-output.txt" 2>&1
echo "exit status of the copy: $?"
grep -n "FAIL\|STOP\|NOT WRITTEN\|checks pass" "$V/compat-output.txt"
if cmp -s "$REAL" "$V/compat-out.html"; then echo "page of the copy: byte-identical to the existing report page"; else echo "page of the copy: DIFFERS from the existing report page"; fi
after=$(sha256sum "$REAL" | cut -d' ' -f1)
[ "$before" = "$after" ] && echo "existing report page untouched ($after)" || echo "EXISTING REPORT PAGE CHANGED"
rm -f "$V/compat_make_report.py" "$V/compat-out.html"
