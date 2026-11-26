import sys; sys.exit('OUTDATED since 2026-11-24: go.sh line 20 was edited and no longer matches local.sha. Use goedit/test_start.py (it rebuilds the as-run text).')
# Local dry test of the one-command text. No ssh: the text between the single quotes runs under bash -c
# with a fake HOME, a stub sudo and dmidecode, and fake files for meminfo, the marker and the counter device type.
# Case A uses the real go.sh text: in the fake HOME it must stop at its own line 22 (no rx.sh), so no benchmark can start.
import os, re, subprocess, shutil, sys, glob, hashlib
SP, S = sys.argv[1], sys.argv[2]
W = f'{SP}/direct/run'
t = open(f'{SP}/direct/cmd.txt').read()
assert t.count("'") == 2
head, body, tail = t.split("'")
assert tail.strip() == '' and head.startswith('ssh ') and head.rstrip().endswith('jhan@192.168.2.45')
STUB_GO = '#!/bin/bash\nBOOT=old\necho "go.sh pid $$ (stub)"\n[ "$(cat /proc/sys/kernel/random/boot_id)" = "$BOOT" ] || { echo "FAILED: boot id is not the boot checked (the line was not removed)"; exit 9; }\nsleep 1; %s\n'
def case(tag, speed_lines, mem_text, sudo_ok=True, tamper=False, marker=False, stub_rc=None):
    base = f'{W}/{tag}'; home = f'{base}/home'; d = f'{home}/cache-perf/w120-7200-20261117'; stub = f'{base}/bin'
    os.makedirs(d); os.makedirs(f'{home}/cache-perf/results'); os.makedirs(stub)
    for f in ('go.sh', 'ra.sh', 'like.spec', 'cfwd.spec', 'crev.spec', 'local.sha'): shutil.copy(f'{S}/{f}', d)
    if stub_rc is not None:
        open(f'{d}/go.sh', 'w').write(STUB_GO % ('echo ALLDONE; exit 0' if stub_rc == 0 else 'echo "FAILED: stub"; exit 1'))
        subprocess.run('cd %s && sha256sum go.sh ra.sh like.spec cfwd.spec crev.spec > local.sha' % d, shell=True, check=True)
    if tamper: open(f'{d}/ra.sh', 'a').write('# changed\n')
    open(f'{base}/meminfo', 'w').write(mem_text)
    open(f'{base}/pmutype', 'w').write('11\n')
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
    allok &= good
    last = [l for l in r.stdout.strip().split('\n') if l][-1][:100]
    print(('PASS' if good else 'FAIL'), tag, '| status', r.returncode, '|', extra, '|', last)
# cases that must not start anything
for tag, sp, m, sudo_ok, tamper, marker, want in [
        ('B-8000', ['Configured Memory Speed: 8000 MT/s'] * 12, mem(395392804), True, False, False, 5),
        ('C-10mod', ['Configured Memory Speed: 7200 MT/s'] * 10 + ['Configured Memory Speed: Unknown'] * 2, mem(329000000), True, False, False, 5),
        ('C2-mixed', ['Configured Memory Speed: 7200 MT/s'] * 6 + ['Configured Memory Speed: 8000 MT/s'] * 6, mem(395392804), True, False, False, 5),
        ('D-lowmem', ok12, mem(329000000), True, False, False, 5),
        ('D2-memtext', ok12, mem('abc'), True, False, False, 5),
        ('E-nosudo', ok12, mem(395392804), False, False, False, 5),
        ('F-tamper', ok12, mem(395392804), True, True, False, 4),
        ('H-marker', ok12, mem(395392804), True, False, True, 3)]:
    r, d, home = case(tag, sp, m, sudo_ok, tamper, marker)
    copy = os.path.exists(f'{d}/go-direct.sh'); logs = glob.glob(f'{home}/cache-perf/results/go-T72-*.log')
    report(r.returncode == want and not copy and not logs, tag, r, 'copy written %s, log files %d' % (copy, len(logs)))
# case A: real go.sh text
r, d, home = case('A-real', ok12, mem(395392804))
df = subprocess.run(['diff', f'{d}/go.sh', f'{d}/go-direct.sh'], capture_output=True, text=True).stdout
log = open(glob.glob(f'{home}/cache-perf/results/go-T72-*.log')[0]).read()
rec = open(glob.glob(f'{home}/cache-perf/results/memcheck-*.txt')[0]).read()
syn = subprocess.run(['bash', '-n', f'{d}/go-direct.sh']).returncode
sha = subprocess.run('cd %s && sha256sum -c local.sha >/dev/null 2>&1; echo $?' % d, shell=True, capture_output=True, text=True).stdout.strip()
same = hashlib.sha256(open(f'{d}/go.sh','rb').read()).hexdigest() == hashlib.sha256(open(f'{S}/go.sh','rb').read()).hexdigest()
goodA = (r.returncode == 1 and df.startswith('26d25\n') and df.count('\n') == 2 and 'boot id is not the boot checked' in df and syn == 0 and sha == '0' and same
         and 'FAILED: rx.sh is not the script of 2026-11-15' in log and 'boot id is not' not in log and '12 \tConfigured Memory Speed: 7200 MT/s' in rec)
report(goodA, 'A-real', r, 'syntax %d, go.sh equals local.sha %s, go.sh unchanged %s' % (syn, sha == '0', same))
print('--- diff go.sh go-direct.sh'); print(df.rstrip()); print('--- memory record'); print(rec.rstrip()); print('--- log of the copy (first 2 lines)'); print('\n'.join(l[:150] for l in log.split('\n')[:2]))
# cases G: stub go.sh that holds the boot-id line; the start half of the command
for rc in (0, 1):
    r, d, home = case('G-stub%d' % rc, ok12, mem(395392804), stub_rc=rc)
    out = r.stdout
    m1 = re.search(r'^log \S+ pid (\d+)$', out, re.M); m2 = re.search(r'go.sh pid (\d+)', out)
    good = (r.returncode == rc and m1 and m2 and m1.group(1) == m2.group(1) and ('go.sh exit status %d' % rc) in out and 'line was not removed' not in out and (('ALLDONE' in out) == (rc == 0)))
    report(bool(good), 'G-stub%d' % rc, r, 'pids equal %s' % bool(m1 and m2 and m1.group(1) == m2.group(1)))
print('ALL PASS' if allok else 'SOME FAILED')
