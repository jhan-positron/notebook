#!/usr/bin/env python3
"""check_start_command.py - the saved start command (new-test-kernel/manual-run/run.sh) against three states of CRB.

No ssh. The text between the single quotes of run.sh is the command line for CRB. This check runs that text
under `bash -c` in fake home folders below work-start. Fake programs take the place of sudo and dmidecode.
Fake files take the place of /proc/meminfo, of the marker file and of the counter device type in that text.
The command starts a copy of go.sh. The fake home holds no rx.sh. So the copy stops at its own line 22.
The first benchmark command of go.sh is in line 41. No benchmark can start.

States of the run folder on CRB:
  asrun   : go.sh as it ran on 2026-11-17 (go.sh.as-run-2026-11-17) + local.sha. This is the state in the last
            record of that folder: line 310 of the session record of 2026-11-17 (22:12:04 UTC), where
            `sha256sum -c local.sha` printed `go.sh: OK`.
  newonly : the edited go.sh copied alone, local.sha unchanged.
  newboth : the edited go.sh + a checksum list with the new go.sh entry.

Usage: python3 check_start_command.py
Python 3 standard library only. Writes only below work-start in the folder of this script.
That folder is removed at the end, also when a check raises an error.
"""
import glob, os, shutil, subprocess, sys
sys.dont_write_bytecode = True
from common import E, S, ASRUN, RUN_SH, MARKER, OLD, NEW, sha, read, listed, line20_is_new, Report

r = Report()
t = read(RUN_SH)
assert t.count("'") == 2, 'run.sh: expected one quoted command line'
head, body, tail = t.split("'")
assert tail.strip() == '' and head.startswith('ssh ') and head.rstrip().endswith('jhan@192.168.2.45')
new_text, asrun_text = read(os.path.join(S, 'go.sh')), read(ASRUN)
r.line(sha(asrun_text) == listed('go.sh') and line20_is_new(new_text) and new_text.replace(NEW, OLD) == asrun_text,
       'the copy go.sh.as-run-2026-11-17 has the sha256 that local.sha lists, and the edited go.sh differs from it in line 20 only')
W = os.path.join(E, 'work-start')
shutil.rmtree(W, ignore_errors=True)
try:
    PMU = '/sys/bus/event_source/devices/armv8_pmuv3_0/type'
    def case(tag, state, speed_lines, mem_text, sudo_ok=True, tamper=False, marker=False):
        base = os.path.join(W, tag); home = os.path.join(base, 'home'); d = os.path.join(home, 'cache-perf', 'w120-7200-20261117'); stub = os.path.join(base, 'bin')
        os.makedirs(d); os.makedirs(os.path.join(home, 'cache-perf', 'results')); os.makedirs(stub)
        for f in ('ra.sh', 'like.spec', 'cfwd.spec', 'crev.spec', 'local.sha'): shutil.copy(os.path.join(S, f), d)
        open(os.path.join(d, 'go.sh'), 'w').write(asrun_text if state == 'asrun' else new_text); os.chmod(os.path.join(d, 'go.sh'), 0o755)
        if state == 'newboth':
            lines = [(sha(new_text) + '  go.sh') if l.endswith('  go.sh') else l for l in read(os.path.join(d, 'local.sha')).split('\n')]
            open(os.path.join(d, 'local.sha'), 'w').write('\n'.join(lines))
        if tamper: open(os.path.join(d, 'ra.sh'), 'a').write('# changed\n')
        open(os.path.join(base, 'meminfo'), 'w').write(mem_text); open(os.path.join(base, 'pmutype'), 'w').write('11\n')
        if marker: open(os.path.join(base, 'RUNNING'), 'w').close()
        open(os.path.join(stub, 'sudo'), 'w').write('#!/bin/bash\n' + ('[ "$1" = -n ] && shift; exec "$@"\n' if sudo_ok else 'echo "sudo: a password is required" >&2; exit 1\n'))
        open(os.path.join(stub, 'dmidecode'), 'w').write('#!/bin/bash\ncat <<X\n' + ''.join('\t%s\n' % l for l in speed_lines) + 'X\n')
        for f in ('sudo', 'dmidecode'): os.chmod(os.path.join(stub, f), 0o755)
        b = body
        for old, new in (('/proc/meminfo', os.path.join(base, 'meminfo')), (MARKER, os.path.join(base, 'RUNNING')), (PMU, os.path.join(base, 'pmutype'))):
            assert b.count(old) == 1, old
            b = b.replace(old, new)
        p = subprocess.run(['bash', '-c', b], env=dict(os.environ, HOME=home, PATH=stub + ':' + os.environ['PATH']), capture_output=True, text=True)
        return p, d, home
    mem = lambda kb: 'MemTotal:       %s kB\nMemFree: 1 kB\n' % kb
    ok12 = ['Configured Memory Speed: 7200 MT/s'] * 12
    last = lambda p: [l for l in p.stdout.strip().split('\n') if l][-1][:70]
    def nostart(tag, state, sp, m, sudo_ok, tamper, marker, want, what):
        p, d, home = case(tag, state, sp, m, sudo_ok, tamper, marker)
        copy = os.path.exists(os.path.join(d, 'go-direct.sh')); logs = glob.glob(os.path.join(home, 'cache-perf', 'results', 'go-T72-*.log'))
        r.line(p.returncode == want and not copy and not logs, '%-16s %s: status %d, nothing started | %s' % (tag, what, p.returncode, last(p)))
    for tag, sp, m, sudo_ok, tamper, marker, want, what in [
            ('asrun-8000', ['Configured Memory Speed: 8000 MT/s'] * 12, mem(395392804), True, False, False, 5, 'memory at 8000 MT/s'),
            ('asrun-10mod', ['Configured Memory Speed: 7200 MT/s'] * 10 + ['Configured Memory Speed: Unknown'] * 2, mem(329000000), True, False, False, 5, '10 memory modules'),
            ('asrun-mixed', ['Configured Memory Speed: 7200 MT/s'] * 6 + ['Configured Memory Speed: 8000 MT/s'] * 6, mem(395392804), True, False, False, 5, 'two memory speeds'),
            ('asrun-lowmem', ok12, mem(329000000), True, False, False, 5, 'MemTotal too low'),
            ('asrun-memtext', ok12, mem('abc'), True, False, False, 5, 'MemTotal not a number'),
            ('asrun-nosudo', ok12, mem(395392804), False, False, False, 5, 'sudo refused'),
            ('asrun-tamper', ok12, mem(395392804), True, True, False, 4, 'ra.sh changed'),
            ('asrun-marker', ok12, mem(395392804), True, False, True, 3, 'marker file present')]:
        nostart(tag, 'asrun', sp, m, sudo_ok, tamper, marker, want, what)
    def started(tag, state, want_line20, what):
        p, d, home = case(tag, state, ok12, mem(395392804))
        df = subprocess.run(['diff', os.path.join(d, 'go.sh'), os.path.join(d, 'go-direct.sh')], capture_output=True, text=True).stdout
        logs = glob.glob(os.path.join(home, 'cache-perf', 'results', 'go-T72-*.log'))
        log = read(logs[0]) if len(logs) == 1 else ''
        copy = read(os.path.join(d, 'go-direct.sh')) if os.path.exists(os.path.join(d, 'go-direct.sh')) else ''
        good = (p.returncode == 1 and df.startswith('26d25\n') and df.count('\n') == 2 and 'boot id is not the boot checked' in df
                and subprocess.run(['bash', '-n', os.path.join(d, 'go-direct.sh')]).returncode == 0
                and 'FAILED: rx.sh is not the script of 2026-11-15' in log and 'boot id is not' not in log and copy.split('\n')[19] + '\n' == want_line20)
        r.line(good, '%-16s %s: go-direct.sh is go.sh without line 26, it starts, and it stops at its test of rx.sh (status %d)' % (tag, what, p.returncode))
    started('asrun-ready', 'asrun', OLD, 'good state, go.sh of 2026-11-17 (line 20 of the started copy is the old line)')
    nostart('newonly', 'newonly', ok12, mem(395392804), True, False, False, 4, 'edited go.sh, old checksum list')
    started('newboth', 'newboth', NEW, 'edited go.sh with a matching checksum list (line 20 of the started copy is the new line)')
finally:
    shutil.rmtree(W, ignore_errors=True)
r.end()
