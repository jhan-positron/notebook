#!/usr/bin/env python3
"""check_line20.py - the two texts of go.sh, and what the edited line 20 does.

Part 1 compares checksums and texts. It reads the local go.sh and never changes it. It puts the old line 20
back in a copy of the text in memory. That text must have the sha256 that local.sha lists for go.sh.
The copy go.sh.as-run-2026-11-17 must have the same value. The script text in line 295 of the session record of
2026-11-17 must have it too. That record lies outside the project folder (common.py names it), and this check
stops with an error when the record is missing. Part 1 also lets `bash -n` read the local go.sh. This is a
syntax test that runs no command.

Part 2 runs a COPY of the local go.sh. In the copy the path of the marker file is replaced by a path in the
work folder. HOME is a folder in the work folder. That HOME holds no rx.sh. So the copy stops at its line 22.
The first benchmark command of go.sh is in line 41. No benchmark can start.
The copy runs once with the marker file and once without it.

Usage: python3 check_line20.py
Python 3 standard library only. Writes only below work-line20 in the folder of this script.
That folder is removed at the end, also when a check raises an error.
"""
import json, os, re, shutil, subprocess, sys
sys.dont_write_bytecode = True
from common import E, S, ASRUN, RECORD17, MARKER, OLD, NEW, sha, read, listed, line20_is_new, Report

r = Report()
go = read(os.path.join(S, 'go.sh'))
want = listed('go.sh')
print('sha256 that local.sha lists for go.sh:', want)
print('sha256 of the local go.sh:            ', sha(go))
r.line(line20_is_new(go), 'line 20 of the local go.sh is the line of 2026-11-24')
r.line(sha(go.replace(NEW, OLD)) == want, 'with the old line 20 put back in memory, the text of the local go.sh has the listed sha256')
old_lines, new_lines = read(ASRUN).split('\n'), go.split('\n')
diff = [i + 1 for i, (a, b) in enumerate(zip(old_lines, new_lines)) if a != b]
r.line(sha(read(ASRUN)) == want, 'the copy go.sh.as-run-2026-11-17 has the listed sha256')
r.line(len(old_lines) == len(new_lines) == 49 and diff == [20], 'the copy and the local go.sh have 48 lines each and differ in line 20 only (different lines: %s)' % diff)
assert os.path.exists(RECORD17), 'this check needs the session record of 2026-11-17: ' + RECORD17
cmd = [c['input']['command'] for c in json.loads(read(RECORD17).split('\n')[294])['message']['content'] if c.get('type') == 'tool_use'][0]
m = re.search(r"cat > go\.sh <<'EOF'\n(.*?\n)EOF\n", cmd, re.S)
r.line(bool(m) and sha(m.group(1)) == want, 'the go.sh text in line 295 of the session record of 2026-11-17 has the listed sha256')
r.line(subprocess.run(['bash', '-n', os.path.join(S, 'go.sh')]).returncode == 0, 'bash -n accepts the local go.sh')

W = os.path.join(E, 'work-line20')
shutil.rmtree(W, ignore_errors=True)
try:
    os.makedirs(os.path.join(W, 'home', 'cache-perf', 'results'))
    fake = os.path.join(W, 'RUNNING')
    assert go.count(MARKER) == 3
    open(os.path.join(W, 'go-copy.sh'), 'w').write(go.replace(MARKER, fake))
    def run():
        p = subprocess.run(['bash', os.path.join(W, 'go-copy.sh')], env=dict(os.environ, HOME=os.path.join(W, 'home')), capture_output=True, text=True)
        return p.returncode, [l for l in (p.stdout + p.stderr).split('\n') if l]
    open(fake, 'w').close()
    rc, out = run()
    out3 = (out + ['', '', ''])[:3]
    print('with the marker file:    status %d | %s | %s | %s' % (rc, out3[0][:40], out3[1], out3[2][:30]))
    r.line(rc == 1 and len(out) == 3 and out[0].startswith('go.sh pid ') and out[1] == 'FAILED: RUNNING file present, Jeremy or someone else is using CRB'
           and out[2].startswith('== abort utc ') and ' marker present ' in out[2],
           'with the marker file the copy prints its pid line, the new message and one state line, and ends with status 1')
    r.line(os.listdir(os.path.join(W, 'home', 'cache-perf', 'results')) == [], 'with the marker file the copy creates no lock file')
    os.remove(fake)
    rc, out = run()
    print('without the marker file: status %d | %s' % (rc, [l for l in out if l.startswith('FAILED')]))
    r.line(rc == 1 and 'FAILED: rx.sh is not the script of 2026-11-15' in out and not any('RUNNING file present' in l for l in out),
           'without the marker file the copy passes line 20 and stops at its test of rx.sh (line 22)')
finally:
    shutil.rmtree(W, ignore_errors=True)
r.end()
