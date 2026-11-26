#!/usr/bin/env python3
"""check_facts_build.py - what a new run of build_facts.py does after the edit of go.sh line 20.

build_facts.py finds its folders from its own location. It writes FACTS.md and facts.json into its own folder.
So this check builds a mirror of the path workspace/titan/cache-perf/crb below work-facts.
The folders on the path down to the run folder are real folders. Every other entry of crb, of crb/tmp and of
crb/tmp/agent-scratch is a symbolic link to the real entry. The folder machines beside titan is a link too:
build_facts.py reads machines/arm-crb/DIMM-flaky-report.md, and this check stops when that file is missing.
The run folder of the mirror holds copies of the files of the real run folder, with their file times.
Its subfolders are links to the real subfolders.
The copy of build_facts.py reads the real data through the links. It writes only into the copied run folder.

Run 1: the copy as it is (edited go.sh). Wanted: status 1, the stop message, and no change in the copied run folder.
Run 2: line 20 of the copied go.sh put back to the old text. Wanted: status 0 and "checks: 27, failed: 0".
The FACTS.md and the facts.json of run 2 must equal the stored files once the path of the copy is replaced by the real path.

Usage: python3 check_facts_build.py
Python 3 standard library only. Writes only below work-facts in the folder of this script.
That folder is removed at the end, also when a check raises an error.
"""
import os, shutil, subprocess, sys
sys.dont_write_bytecode = True
from common import E, C, S, OLD, NEW, sha, read, listed, line20_is_new, Report

r = Report()
X = os.path.join(E, 'work-facts')
WS = os.path.normpath(os.path.join(C, '..', '..', '..'))                 # the folder that holds titan and machines
DIMM = os.path.join(WS, 'machines', 'arm-crb', 'DIMM-flaky-report.md')
assert os.path.exists(DIMM), 'build_facts.py needs this file: ' + DIMM
CX = os.path.join(X, 'workspace', os.path.relpath(C, WS))
REL = os.path.relpath(S, C)
SX = os.path.join(CX, REL)
OUT = ('FACTS.md', 'facts.json')
real_state = lambda: {n: (sha(open(os.path.join(S, n), 'rb').read()), os.path.getmtime(os.path.join(S, n))) for n in OUT + ('go.sh', 'local.sha')}
real_before = real_state()
shutil.rmtree(X, ignore_errors=True)
try:
    os.makedirs(os.path.join(CX, 'tmp', 'agent-scratch'))
    os.symlink(os.path.join(WS, 'machines'), os.path.join(X, 'workspace', 'machines'))
    for sub in ('', 'tmp', os.path.join('tmp', 'agent-scratch')):
        for e in os.listdir(os.path.join(C, sub)):
            if os.path.join(sub, e) not in ('tmp', os.path.join('tmp', 'agent-scratch'), REL):
                os.symlink(os.path.join(C, sub, e), os.path.join(CX, sub, e))
    os.makedirs(SX)
    for e in os.listdir(S):
        p = os.path.join(S, e)
        if os.path.isdir(p): os.symlink(p, os.path.join(SX, e))
        else: shutil.copy2(p, os.path.join(SX, e))
    def listing():
        """Name, size, file time and (for a file) sha256 of every entry of the copied run folder."""
        out = {}
        for e in sorted(os.listdir(SX)):
            p = os.path.join(SX, e); st = os.lstat(p)
            out[e] = (st.st_size, st.st_mtime, sha(open(p, 'rb').read()) if os.path.isfile(p) and not os.path.islink(p) else '')
        return out
    def build():
        p = subprocess.run([sys.executable, os.path.join(SX, 'build_facts.py')], capture_output=True, text=True)
        return p.returncode, p.stdout.strip().split('\n')[0], p.stderr.strip()

    r.line(line20_is_new(read(os.path.join(SX, 'go.sh'))), 'go.sh of the copy is the edited text (line 20 of 2026-11-24)')
    before = listing()
    rc, first, err = build()
    print('run 1 (edited go.sh, sha256 %s...): status %d | stdout: %r | stderr: %s' % (sha(read(os.path.join(SX, 'go.sh')))[:8], rc, first, err))
    r.line(rc == 1 and err == 'facts_text.py: the data do not show the pattern of a sentence: all integrity checks pass', 'run 1 ends with status 1 and the stop message')
    r.line(listing() == before, 'run 1 changes nothing in the copied run folder: the same %d entries with the same size, file time and content' % len(before))

    p = os.path.join(SX, 'go.sh'); t = read(p); mt = os.path.getmtime(p)
    open(p, 'w').write(t.replace(NEW, OLD)); os.utime(p, (mt, mt))
    r.line(sha(read(p)) == listed('go.sh'), 'go.sh of the copy with the old line 20 has the sha256 that local.sha lists')
    rc, first, err = build()
    print('run 2 (old line 20): status %d | stdout: %r | stderr: %r' % (rc, first, err))
    r.line(rc == 0 and first == 'checks: 27, failed: 0', 'run 2 ends with status 0 and prints "checks: 27, failed: 0"')
    for n in OUT:
        new = read(os.path.join(SX, n))
        raw = sum(1 for a, b in zip(read(os.path.join(S, n)).split('\n'), new.split('\n')) if a != b)
        r.line(rc == 0 and raw > 0 and new.replace(os.path.join(X, 'workspace'), WS) == read(os.path.join(S, n)),
               'run 2: %s of the copy equals the stored file after the path of the copy is replaced by the real path (%d lines hold that path)' % (n, raw))
    r.line(real_state() == real_before, 'FACTS.md, facts.json, go.sh and local.sha of the real run folder are unchanged (content and file time)')
finally:
    shutil.rmtree(X, ignore_errors=True)
r.end()
