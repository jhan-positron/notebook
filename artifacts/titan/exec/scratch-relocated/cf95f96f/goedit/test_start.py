# Regression test of the one-command start (startcmd/direct/cmd.txt) after the edit of go.sh line 20 (2026-11-24).
# No ssh: the text between the single quotes runs under bash -c with a fake HOME, a stub sudo and dmidecode, and fake
# files for meminfo, the marker and the counter device type. The real go.sh text only ever reaches its own line 22
# (no rx.sh in the fake HOME), so no benchmark can start.
# Three states of the copy on CRB are tested:
#   asrun : go.sh as it ran on 2026-11-17 (local text with line 20 put back) + local.sha   -> the state CRB is in on record
#   newonly: the edited go.sh copied alone, local.sha unchanged
#   newboth: the edited go.sh + a checksum list with the new go.sh entry
import os, re, subprocess, shutil, sys, glob, hashlib
SP, S, G = sys.argv[1], sys.argv[2], sys.argv[3]
W = f'{G}/run-start'
NEW = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present, Jeremy or someone else is using CRB"\n'
OLD = '[ -e /tmp/positron-perf.RUNNING ] && fail "RUNNING file present"\n'
t = open(f'{SP}/startcmd/direct/cmd.txt').read()
assert t.count("'") == 2
head, body, tail = t.split("'")
assert tail.strip() == '' and head.startswith('ssh ') and head.rstrip().endswith('jhan@192.168.2.45')
new_text = open(f'{S}/go.sh').read()
assert new_text.count(NEW) == 1
asrun_text = new_text.replace(NEW, OLD)
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
listed = dict(reversed(l.split()) for l in open(f'{S}/local.sha'))
assert sha(asrun_text) == listed['go.sh'], 'the reversed text is not the text of local.sha'
print('as-run text rebuilt from the local go.sh: sha256 equals the local.sha entry', listed['go.sh'][:8] + '...')
def case(tag, state, speed_lines, mem_text, sudo_ok=True, tamper=False, marker=False):
    base = f'{W}/{tag}'; home = f'{base}/home'; d = f'{home}/cache-perf/w120-7200-20261117'; stub = f'{base}/bin'
    os.makedirs(d); os.makedirs(f'{home}/cache-perf/results'); os.makedirs(stub)
    for f in ('ra.sh', 'like.spec', 'cfwd.spec', 'crev.spec', 'local.sha'): shutil.copy(f'{S}/{f}', d)
    open(f'{d}/go.sh', 'w').write(asrun_text if state == 'asrun' else new_text); os.chmod(f'{d}/go.sh', 0o755)
    if state == 'newboth':
        lines = open(f'{d}/local.sha').read().split('\n')
        lines = [(sha(new_text) + '  go.sh') if l.endswith('  go.sh') else l for l in lines]
        open(f'{d}/local.sha', 'w').write('\n'.join(lines))
    if tamper: open(f'{d}/ra.sh', 'a').write('# changed\n')
    open(f'{base}/meminfo', 'w').write(mem_text); open(f'{base}/pmutype', 'w').write('11\n')
    if marker: open(f'{base}/RUNNING', 'w').write('')
    open(f'{stub}/sudo', 'w').write('#!/bin/bash\n' + ('[ "$1" = -n ] && shift; exec "$@"\n' if sudo_ok else 'echo "sudo: a password is required" >&2; exit 1\n'))
    open(f'{stub}/dmidecode', 'w').write('#!/bin/bash\ncat <<X\n' + ''.join('\t%s\n' % l for l in speed_lines) + 'X\n')
    for f in ('sudo', 'dmidecode'): os.chmod(f'{stub}/{f}', 0o755)
    b = body
    for old, new in (('/proc/meminfo', f'{base}/meminfo'), ('/tmp/positron-perf.RUNNING', f'{base}/RUNNING'), ('/sys/bus/event_source/devices/armv8_pmuv3_0/type', f'{base}/pmutype')):
        assert b.count(old) == 1, old
        b = b.replace(old, new)
    r = subprocess.run(['bash', '-c', b], env=dict(os.environ, HOME=home, PATH=stub + ':' + os.environ['PATH']), capture_output=True, text=True)
    return r, d, home
def mem(kb): return 'MemTotal:       %s kB\nMemFree: 1 kB\n' % kb
ok12 = ['Configured Memory Speed: 7200 MT/s'] * 12
if os.path.exists(W): shutil.rmtree(W)
allok = True
def report(good, tag, r, extra=''):
    global allok
    allok &= bool(good)
    last = [l for l in r.stdout.strip().split('\n') if l][-1][:95]
    print(('PASS' if good else 'FAIL'), tag, '| status', r.returncode, '|', extra, '|', last)
def nostart(tag, state, sp, m, sudo_ok, tamper, marker, want):
    r, d, home = case(tag, state, sp, m, sudo_ok, tamper, marker)
    copy = os.path.exists(f'{d}/go-direct.sh'); logs = glob.glob(f'{home}/cache-perf/results/go-T72-*.log')
    report(r.returncode == want and not copy and not logs, tag, r, 'copy written %s, log files %d' % (copy, len(logs)))
for tag, sp, m, sudo_ok, tamper, marker, want in [
        ('B-8000', ['Configured Memory Speed: 8000 MT/s'] * 12, mem(395392804), True, False, False, 5),
        ('C-10mod', ['Configured Memory Speed: 7200 MT/s'] * 10 + ['Configured Memory Speed: Unknown'] * 2, mem(329000000), True, False, False, 5),
        ('C2-mixed', ['Configured Memory Speed: 7200 MT/s'] * 6 + ['Configured Memory Speed: 8000 MT/s'] * 6, mem(395392804), True, False, False, 5),
        ('D-lowmem', ok12, mem(329000000), True, False, False, 5),
        ('D2-memtext', ok12, mem('abc'), True, False, False, 5),
        ('E-nosudo', ok12, mem(395392804), False, False, False, 5),
        ('F-tamper', ok12, mem(395392804), True, True, False, 4),
        ('H-marker', ok12, mem(395392804), True, False, True, 3)]:
    nostart('asrun/' + tag, 'asrun', sp, m, sudo_ok, tamper, marker, want)
def started(tag, state, want_line20):
    r, d, home = case(tag, state, ok12, mem(395392804))
    df = subprocess.run(['diff', f'{d}/go.sh', f'{d}/go-direct.sh'], capture_output=True, text=True).stdout
    log = open(glob.glob(f'{home}/cache-perf/results/go-T72-*.log')[0]).read()
    syn = subprocess.run(['bash', '-n', f'{d}/go-direct.sh']).returncode
    line20 = open(f'{d}/go-direct.sh').read().split('\n')[19] + '\n'
    good = (r.returncode == 1 and df.startswith('26d25\n') and df.count('\n') == 2 and 'boot id is not the boot checked' in df and syn == 0
            and 'FAILED: rx.sh is not the script of 2026-11-15' in log and 'boot id is not' not in log and line20 == want_line20)
    report(good, tag, r, 'diff to the copy: %s, syntax %d, line 20 of the copy is the %s text' % (df.split('\n')[0], syn, 'new' if line20 == NEW else 'old' if line20 == OLD else '?'))
started('asrun/A-real', 'asrun', OLD)
nostart('newonly/N1', 'newonly', ok12, mem(395392804), True, False, False, 4)
started('newboth/N2', 'newboth', NEW)
print('ALL PASS' if allok else 'SOME FAILED')
