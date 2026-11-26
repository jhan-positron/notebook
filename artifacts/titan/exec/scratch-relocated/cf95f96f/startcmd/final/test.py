# Local dry test of the two command texts. No ssh: the text between the single quotes runs under bash -c
# with a fake HOME, a stub sudo and a fake meminfo file. go.sh is never run: command 2 is tested with a stub driver.
import os, re, subprocess, shutil, sys
SP, S = sys.argv[1], sys.argv[2]
def remote(name):
    t = open(f'{SP}/final/{name}').read()
    assert t.count("'") == 2, (name, t.count("'"))
    head, body, tail = t.split("'")
    assert tail.strip() == '' and head.startswith('ssh ') and head.rstrip().endswith('jhan@192.168.2.45')
    return body
def case(tag, speed_lines, memkb, sudo_ok=True, tamper=False):
    home = f'{SP}/final/{tag}/home'; d = f'{home}/cache-perf/w120-7200-20261117'; stub = f'{SP}/final/{tag}/bin'
    if os.path.exists(f'{SP}/final/{tag}'): raise SystemExit('test folder exists: ' + tag)
    os.makedirs(d); os.makedirs(f'{home}/cache-perf/results'); os.makedirs(stub)
    for f in ('go.sh', 'ra.sh', 'like.spec', 'cfwd.spec', 'crev.spec', 'local.sha'): shutil.copy(f'{S}/{f}', d)
    if tamper: open(f'{d}/ra.sh', 'a').write('# changed\n')
    open(f'{SP}/final/{tag}/meminfo', 'w').write('MemTotal:       %d kB\nMemFree: 1 kB\n' % memkb)
    open(f'{stub}/sudo', 'w').write('#!/bin/bash\n' + ('[ "$1" = -n ] && shift; exec "$@"\n' if sudo_ok else 'echo "sudo: a password is required" >&2; exit 1\n'))
    open(f'{stub}/dmidecode', 'w').write('#!/bin/bash\ncat <<X\n' + ''.join('\t%s\n' % l for l in speed_lines) + 'X\n')
    for f in ('sudo', 'dmidecode'): os.chmod(f'{stub}/{f}', 0o755)
    body = remote('cmd1.txt').replace('/proc/meminfo', f'{SP}/final/{tag}/meminfo')
    r = subprocess.run(['bash', '-c', body], env=dict(os.environ, HOME=home, PATH=stub + ':' + os.environ['PATH']), capture_output=True, text=True)
    made = os.path.exists(f'{d}/go-thisboot.sh')
    return r, made, home, d
ok12 = ['Configured Memory Speed: 7200 MT/s'] * 12
tests = [('A-ready', ok12, 395392804, True, False, 0, True),
         ('B-8000', ['Configured Memory Speed: 8000 MT/s'] * 12, 395392804, True, False, 5, False),
         ('C-10mod', ['Configured Memory Speed: 7200 MT/s'] * 10 + ['Configured Memory Speed: Unknown'] * 2, 329000000, True, False, 5, False),
         ('D-lowmem', ok12, 329000000, True, False, 5, False),
         ('E-nosudo', ok12, 395392804, False, False, 5, False),
         ('F-tamper', ok12, 395392804, True, True, 4, False)]
allok = True
for tag, sp, mem, sudo_ok, tamper, want, want_made in tests:
    r, made, home, d = case(tag, sp, mem, sudo_ok, tamper)
    good = (r.returncode == want and made == want_made)
    allok &= good
    last = [l for l in r.stdout.strip().split('\n') if l][-1][:110]
    print(('PASS' if good else 'FAIL'), tag, 'status', r.returncode, 'copy written', made, '|', last)
    if tag == 'A-ready':
        print('--- full output of case A'); print(r.stdout[-1500:]); print('stderr:', r.stderr[:300])
        print('syntax of the copy:', subprocess.run(['bash', '-n', f'{d}/go-thisboot.sh']).returncode, '| go.sh still equals local.sha:', subprocess.run('cd %s && sha256sum -c local.sha >/dev/null 2>&1; echo $?' % d, shell=True, capture_output=True, text=True).stdout.strip())
        # command 2 with a stub driver (never the real go.sh text)
        for rc in (0, 1):
            open(f'{d}/go-thisboot.sh', 'w').write('#!/bin/bash\necho "go.sh pid $$ (stub)"; sleep 1; %s\n' % ('echo ALLDONE; exit 0' if rc == 0 else 'echo "FAILED: stub"; exit 1'))
            r2 = subprocess.run(['bash', '-c', remote('cmd2.txt')], env=dict(os.environ, HOME=home), capture_output=True, text=True)
            lines = r2.stdout.strip().split('\n')
            pid_line = re.search(r'pid (\d+)$', lines[0]).group(1); pid_log = re.search(r'go.sh pid (\d+)', r2.stdout).group(1)
            good2 = (r2.returncode == rc and pid_line == pid_log and ('go.sh exit status %d' % rc) in lines[1])
            allok &= good2
            print(('PASS' if good2 else 'FAIL'), 'command 2, stub driver ends with', rc, '| status of the whole command', r2.returncode, '| pids equal', pid_line == pid_log, '|', lines[1], '|', lines[-1])
print('ALL PASS' if allok else 'SOME FAILED')
